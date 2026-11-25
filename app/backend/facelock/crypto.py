"""Cryptographic primitives used across FaceLock Stego.

* AES-256-GCM (authenticated encryption) from the ``cryptography`` package.
* HKDF-SHA256 for deriving purpose-specific sub-keys.
* Argon2id for the backup password (verification hash + key derivation).

Nothing in this module invents its own crypto; it only wraps vetted primitives.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError, InvalidHashError
from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

KEY_LEN = 32      # AES-256
NONCE_LEN = 12    # 96-bit GCM nonce (NIST SP 800-38D recommendation)
TAG_LEN = 16      # GCM authentication tag
SALT_LEN = 16


class DecryptionError(Exception):
    """Raised when authenticated decryption fails (wrong key or tampered data)."""


def random_key() -> bytes:
    return secrets.token_bytes(KEY_LEN)


def random_bytes(n: int) -> bytes:
    return os.urandom(n)


def hkdf(ikm: bytes, salt: bytes, info: bytes, length: int = KEY_LEN) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(ikm)


def aes_gcm_encrypt(key: bytes, plaintext: bytes, aad: bytes | None = None,
                    nonce: bytes | None = None) -> tuple[bytes, bytes]:
    """Encrypt and return ``(nonce, ciphertext||tag)``."""
    if len(key) != KEY_LEN:
        raise ValueError("AES-256 key must be 32 bytes")
    nonce = nonce or os.urandom(NONCE_LEN)
    return nonce, AESGCM(key).encrypt(nonce, plaintext, aad)


def aes_gcm_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes | None = None) -> bytes:
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:  # wrong key, wrong AAD, or modified ciphertext
        raise DecryptionError("authentication tag mismatch") from exc


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


# --------------------------------------------------------------------------- Argon2id
class PasswordKDF:
    """Argon2id helper: one hash for verification, an independent salt for key derivation."""

    def __init__(self, time_cost: int = 3, memory_kib: int = 65536, parallelism: int = 2):
        self.time_cost = time_cost
        self.memory_kib = memory_kib
        self.parallelism = parallelism
        self._hasher = PasswordHasher(time_cost=time_cost, memory_cost=memory_kib,
                                      parallelism=parallelism, type=Type.ID)

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, phc_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(phc_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def derive_key(self, password: str, salt: bytes) -> bytes:
        return hash_secret_raw(password.encode("utf-8"), salt, time_cost=self.time_cost,
                               memory_cost=self.memory_kib, parallelism=self.parallelism,
                               hash_len=KEY_LEN, type=Type.ID)

    def params(self) -> dict:
        return {"alg": "argon2id", "t": self.time_cost, "m": self.memory_kib, "p": self.parallelism}
