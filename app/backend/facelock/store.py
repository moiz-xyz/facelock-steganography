"""Device key and encrypted face-profile storage (owner's device)."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import crypto
from .config import Settings


def load_or_create_device_key(path: Path) -> bytes:
    """32 random bytes generated once per installation; never leaves this machine."""
    if path.exists():
        key = path.read_bytes()
        if len(key) != crypto.KEY_LEN:
            raise RuntimeError(f"{path} is corrupt (expected 32 bytes)")
        return key
    path.parent.mkdir(parents=True, exist_ok=True)
    key = crypto.random_key()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(key)
    return key


class ProfileStore:
    """Enrolled face templates, each file AES-GCM encrypted with the device key."""

    def __init__(self, settings: Settings, device_key: bytes):
        self.dir = settings.profiles_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self._key = crypto.hkdf(device_key, b"", b"facelock/profiles/v1")

    def _path(self, pid: str) -> Path:
        if not pid.isalnum():
            raise KeyError(pid)
        return self.dir / f"{pid}.prof"

    def save(self, label: str, template: np.ndarray, engine: str, quality: dict) -> dict:
        pid = uuid.uuid4().hex[:12]
        rec = {"id": pid, "label": label, "engine": engine, "quality": quality,
               "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "template": crypto.b64e(np.asarray(template, dtype="<f4").tobytes())}
        nonce, ct = crypto.aes_gcm_encrypt(self._key, json.dumps(rec).encode(), pid.encode())
        self._path(pid).write_bytes(nonce + ct)
        return self._public(rec)

    def _read(self, pid: str) -> dict:
        blob = self._path(pid).read_bytes()
        rec = json.loads(crypto.aes_gcm_decrypt(self._key, blob[:12], blob[12:], pid.encode()))
        rec["template_np"] = np.frombuffer(crypto.b64d(rec["template"]), dtype="<f4").astype(np.float32)
        return rec

    def get(self, pid: str) -> dict:
        try:
            return self._read(pid)
        except FileNotFoundError as exc:
            raise KeyError(pid) from exc

    @staticmethod
    def _public(rec: dict) -> dict:
        return {k: rec[k] for k in ("id", "label", "engine", "created_at", "quality")}

    def list(self) -> list[dict]:
        out = []
        for p in sorted(self.dir.glob("*.prof"), key=lambda p: p.stat().st_mtime):
            try:
                out.append(self._public(self._read(p.stem)))
            except Exception:   # unreadable (other device key) -> skip
                continue
        return out

    def delete(self, pid: str) -> None:
        self._path(pid).unlink(missing_ok=False)
