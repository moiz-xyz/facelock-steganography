"""AES-256-GCM, HKDF and Argon2id wrappers."""
import pytest

from facelock import crypto


def test_aes_gcm_roundtrip():
    k = crypto.random_key()
    n, ct = crypto.aes_gcm_encrypt(k, b"hello", b"aad")
    assert len(n) == 12 and len(ct) == 5 + 16
    assert crypto.aes_gcm_decrypt(k, n, ct, b"aad") == b"hello"


def test_aes_gcm_detects_tamper():
    k = crypto.random_key()
    n, ct = crypto.aes_gcm_encrypt(k, b"hello world")
    bad = bytes([ct[0] ^ 1]) + ct[1:]
    with pytest.raises(crypto.DecryptionError):
        crypto.aes_gcm_decrypt(k, n, bad)


def test_aes_gcm_wrong_key_and_aad():
    k = crypto.random_key()
    n, ct = crypto.aes_gcm_encrypt(k, b"x", b"a")
    with pytest.raises(crypto.DecryptionError):
        crypto.aes_gcm_decrypt(crypto.random_key(), n, ct, b"a")
    with pytest.raises(crypto.DecryptionError):
        crypto.aes_gcm_decrypt(k, n, ct, b"b")


def test_rejects_short_key():
    with pytest.raises(ValueError):
        crypto.aes_gcm_encrypt(b"short", b"x")


def test_hkdf_domain_separation():
    ikm = b"k" * 32
    assert crypto.hkdf(ikm, b"s", b"a") != crypto.hkdf(ikm, b"s", b"b")
    assert crypto.hkdf(ikm, b"s", b"a") == crypto.hkdf(ikm, b"s", b"a")


def test_argon2_password():
    kdf = crypto.PasswordKDF(time_cost=1, memory_kib=8192, parallelism=1)
    h = kdf.hash("correct horse")
    assert h.startswith("$argon2id$")
    assert kdf.verify(h, "correct horse") and not kdf.verify(h, "wrong")
    s = b"\x00" * 16
    assert kdf.derive_key("pw", s) == kdf.derive_key("pw", s) != kdf.derive_key("pw2", s)
