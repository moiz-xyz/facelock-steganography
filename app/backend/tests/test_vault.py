"""Face Vault: key wrapping, binding to the image, password fallback, tamper detection."""
import json

import numpy as np
import pytest

from facelock import crypto, vault

KDF = crypto.PasswordKDF(time_cost=1, memory_kib=8192, parallelism=1)


def _tmpl(seed):
    v = np.random.default_rng(seed).normal(size=128).astype(np.float32)
    return v / np.linalg.norm(v)


@pytest.fixture
def setup():
    dek, dev = crypto.random_key(), crypto.random_key()
    faces = [vault.FaceSlot("alice", "p1", _tmpl(1), "sface"), vault.FaceSlot("bob", "p2", _tmpl(2), "sface")]
    v = vault.create_vault(dek, "ab" * 32, dev, faces, 0.4, "backup-pass", KDF)
    return dek, dev, v


def test_dek_not_in_plaintext(setup):
    dek, _, v = setup
    raw = vault.dumps(v)
    assert crypto.b64e(dek).encode() not in raw and dek.hex().encode() not in raw
    assert b"alice" not in raw                          # labels are inside the sealed record


def test_face_slots_unwrap(setup):
    dek, dev, v = setup
    v2 = vault.loads(vault.dumps(v))
    thr, slots = vault.open_face_lock(v2, dev)
    assert thr == 0.4 and [s["label"] for s in slots] == ["alice", "bob"]
    assert all(vault.unwrap_face_slot(v2, dev, s) == dek for s in slots)


def test_other_device_cannot_open(setup):
    _, _, v = setup
    with pytest.raises(vault.VaultError):
        vault.open_face_lock(v, crypto.random_key())


def test_slot_key_bound_to_template(setup):
    _, dev, v = setup
    _, slots = vault.open_face_lock(v, dev)
    slots[0]["template_np"] = _tmpl(99)                 # someone else's face template
    with pytest.raises(vault.VaultError):
        vault.unwrap_face_slot(v, dev, slots[0])


def test_header_tamper_detected(setup):
    _, dev, v = setup
    v2 = json.loads(vault.dumps(v))
    v2["image_sha256"] = "cd" * 32                      # re-point vault at another image
    with pytest.raises(vault.VaultError):
        vault.open_face_lock(v2, dev)
    with pytest.raises(vault.VaultError):
        vault.open_password_lock(v2, "backup-pass", KDF)


def test_password_fallback(setup):
    dek, _, v = setup
    assert vault.open_password_lock(v, "backup-pass", KDF) == dek
    with pytest.raises(vault.VaultError, match="wrong password"):
        vault.open_password_lock(v, "nope", KDF)


def test_requires_some_lock():
    with pytest.raises(vault.VaultError):
        vault.create_vault(crypto.random_key(), "00" * 32, crypto.random_key(), [], 0.4, None)


def test_rejects_garbage():
    with pytest.raises(vault.VaultError):
        vault.loads(b"not json")
    with pytest.raises(vault.VaultError):
        vault.loads(b'{"format":"Other"}')
