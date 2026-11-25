"""The Face Vault (``.vault``): the only place the message's data key (DEK) lives.

File format (JSON, UTF-8)::

    {
      "format": "FaceLockVault", "version": 1,
      "vault_id": "...", "created_at": "...",
      "image_sha256": "<fingerprint of stego pixels>",
      "face_lock":     {"salt", "nonce", "ciphertext"}          | null,
      "password_lock": {"argon2", "kdf", "salt", "nonce", "wrapped_dek"} | null
    }

Key hierarchy
-------------
* ``AAD`` = SHA-256 of the canonical public header (format, version, id, time,
  image hash). Every AES-GCM operation authenticates it, so the vault cannot be
  re-pointed at another image and its header cannot be edited.
* **Face lock.** ``KEK_vault = HKDF(device_key, salt, "facelock/vault/v1")``
  encrypts a sealed record holding, for each authorised person (max 3), the
  averaged face template and a *slot*. Each slot wraps the DEK under
  ``KEK_slot = HKDF(device_key, salt, "facelock/slot/v1" || SHA-256(template))``,
  i.e. a key derived from that person's face-embedding secret.
  The server opens a slot only after a live face scan passes liveness and
  matches that slot's template (cosine similarity >= threshold).
* **Password lock (optional fallback).** Argon2id PHC hash for verification and
  an independent Argon2id-derived key wrapping the DEK. Portable: does not need
  the device key.

Honest limitation: the face match is enforced by the server (a policy gate),
not by the mathematics. Anyone holding *both* ``device.key`` and the vault could
read the template and unwrap the DEK without a face. A fuzzy extractor would
turn this into a true cryptographic binding (see the report, Chapter 7).
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from . import crypto

FORMAT = "FaceLockVault"
VERSION = 1


class VaultError(Exception):
    pass


@dataclass
class FaceSlot:
    label: str
    profile_id: str
    template: np.ndarray   # L2-normalised embedding
    engine: str


def _template_bytes(t: np.ndarray) -> bytes:
    return np.asarray(t, dtype="<f4").tobytes()


def _aad(header: dict) -> bytes:
    canon = {k: header[k] for k in ("format", "version", "vault_id", "created_at", "image_sha256")}
    return crypto.sha256_hex(json.dumps(canon, sort_keys=True, separators=(",", ":")).encode()).encode()


def _slot_key(device_key: bytes, salt: bytes, template: np.ndarray) -> bytes:
    info = b"facelock/slot/v1" + bytes.fromhex(crypto.sha256_hex(_template_bytes(template)))
    return crypto.hkdf(device_key, salt, info)


def create_vault(dek: bytes, image_sha256: str, device_key: bytes, faces: list[FaceSlot],
                 threshold: float, password: str | None = None,
                 kdf: crypto.PasswordKDF | None = None) -> dict:
    if not faces and not password:
        raise VaultError("a vault needs at least one enrolled face or a backup password")
    header = {
        "format": FORMAT, "version": VERSION, "vault_id": uuid.uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "image_sha256": image_sha256,
    }
    aad = _aad(header)
    vault = dict(header, face_lock=None, password_lock=None)

    if faces:
        salt = crypto.random_bytes(crypto.SALT_LEN)
        slots = []
        for f in faces:
            nonce, wrapped = crypto.aes_gcm_encrypt(_slot_key(device_key, salt, f.template), dek, aad)
            slots.append({"label": f.label, "profile_id": f.profile_id, "engine": f.engine,
                          "template": crypto.b64e(_template_bytes(f.template)),
                          "nonce": crypto.b64e(nonce), "wrapped_dek": crypto.b64e(wrapped)})
        sealed = json.dumps({"threshold": threshold, "slots": slots}).encode()
        kek = crypto.hkdf(device_key, salt, b"facelock/vault/v1")
        nonce, ct = crypto.aes_gcm_encrypt(kek, sealed, aad)
        vault["face_lock"] = {"salt": crypto.b64e(salt), "nonce": crypto.b64e(nonce),
                              "ciphertext": crypto.b64e(ct), "slots": len(faces)}

    if password:
        kdf = kdf or crypto.PasswordKDF()
        salt = crypto.random_bytes(crypto.SALT_LEN)
        nonce, wrapped = crypto.aes_gcm_encrypt(kdf.derive_key(password, salt), dek, aad)
        vault["password_lock"] = {"argon2": kdf.hash(password), "kdf": kdf.params(),
                                  "salt": crypto.b64e(salt), "nonce": crypto.b64e(nonce),
                                  "wrapped_dek": crypto.b64e(wrapped)}
    return vault


def dumps(vault: dict) -> bytes:
    return json.dumps(vault, indent=2).encode("utf-8")


def loads(data: bytes) -> dict:
    try:
        v = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VaultError("not a valid .vault file") from exc
    if not isinstance(v, dict) or v.get("format") != FORMAT:
        raise VaultError("not a FaceLock vault")
    if v.get("version") != VERSION:
        raise VaultError(f"unsupported vault version {v.get('version')}")
    for k in ("vault_id", "created_at", "image_sha256"):
        if not isinstance(v.get(k), str):
            raise VaultError(f"vault field '{k}' missing")
    return v


def open_face_lock(vault: dict, device_key: bytes) -> tuple[float, list[dict]]:
    """Decrypt the sealed face record -> (threshold, slots with numpy templates).

    Called only inside the server's verification pipeline; templates never
    leave the backend.
    """
    fl = vault.get("face_lock")
    if not fl:
        raise VaultError("this vault has no face lock (use the backup password)")
    kek = crypto.hkdf(device_key, crypto.b64d(fl["salt"]), b"facelock/vault/v1")
    try:
        sealed = crypto.aes_gcm_decrypt(kek, crypto.b64d(fl["nonce"]), crypto.b64d(fl["ciphertext"]), _aad(vault))
    except crypto.DecryptionError as exc:
        raise VaultError("vault was created on a different device or has been tampered with") from exc
    rec = json.loads(sealed)
    for s in rec["slots"]:
        s["template_np"] = np.frombuffer(crypto.b64d(s["template"]), dtype="<f4").astype(np.float32)
    return float(rec["threshold"]), rec["slots"]


def unwrap_face_slot(vault: dict, device_key: bytes, slot: dict) -> bytes:
    salt = crypto.b64d(vault["face_lock"]["salt"])
    key = _slot_key(device_key, salt, slot["template_np"])
    try:
        return crypto.aes_gcm_decrypt(key, crypto.b64d(slot["nonce"]), crypto.b64d(slot["wrapped_dek"]), _aad(vault))
    except crypto.DecryptionError as exc:
        raise VaultError("face slot could not be unwrapped") from exc


def open_password_lock(vault: dict, password: str, kdf: crypto.PasswordKDF | None = None) -> bytes:
    pl = vault.get("password_lock")
    if not pl:
        raise VaultError("this vault has no backup password")
    p = pl.get("kdf", {})
    kdf = kdf or crypto.PasswordKDF(p.get("t", 3), p.get("m", 65536), p.get("p", 2))
    if not kdf.verify(pl["argon2"], password):
        raise VaultError("wrong password")
    try:
        return crypto.aes_gcm_decrypt(kdf.derive_key(password, crypto.b64d(pl["salt"])),
                                      crypto.b64d(pl["nonce"]), crypto.b64d(pl["wrapped_dek"]), _aad(vault))
    except crypto.DecryptionError as exc:
        raise VaultError("vault password slot is corrupt or tampered") from exc
