"""Capacity arithmetic, payload packing and the full stego container."""
import numpy as np
import pytest

from facelock import crypto, lsb, stego
from facelock.payload import SecretPayload, pack, unpack


@pytest.mark.parametrize("w,h", [(64, 64), (512, 512), (768, 512), (1920, 1080)])
def test_capacity_formula(w, h):
    shape = (h, w, 3)
    assert lsb.capacity_bytes(shape) == w * h * 3 // 8
    assert stego.payload_capacity(shape) == w * h * 3 // 8 - 38 - 16


def test_header_size():
    assert stego.HEADER_LEN == 38 and stego.OVERHEAD == 54


def test_pack_text_and_file():
    t = unpack(pack(SecretPayload.from_text("héllo " * 100)))
    assert t.is_text and t.text() == "héllo " * 100
    f = unpack(pack(SecretPayload.from_file("a.pdf", b"%PDF" + bytes(range(256)), "application/pdf")))
    assert f.name == "a.pdf" and f.mime == "application/pdf" and f.data.startswith(b"%PDF")


def test_compression_only_when_smaller():
    rnd = np.random.default_rng(0).integers(0, 256, 5000, dtype=np.uint8).tobytes()
    assert len(pack(SecretPayload.from_file("r.bin", rnd, None))) < 5000 + 64
    assert len(pack(SecretPayload.from_text("a" * 5000))) < 200


def test_exact_fit_and_one_byte_over():
    cover = np.full((40, 40, 3), 128, np.uint8)         # 600 bytes raw capacity
    dek = crypto.random_key()
    rnd = np.random.default_rng(1).integers(0, 256, 1000, dtype=np.uint8).tobytes()
    overhead = len(pack(SecretPayload.from_file("x", b"", None)))
    fit = 600 - stego.OVERHEAD - overhead
    res = stego.hide(cover, SecretPayload.from_file("x", rnd[:fit], None), dek)
    assert res.embedded_bytes == 600
    assert stego.reveal(res.stego_rgb, dek).data == rnd[:fit]
    with pytest.raises(lsb.CapacityError):
        stego.hide(cover, SecretPayload.from_file("x", rnd[:fit + 1], None), dek)


def test_stego_roundtrip_and_wrong_key(cover):
    dek = crypto.random_key()
    res = stego.hide(cover, SecretPayload.from_text("meet at 9"), dek)
    assert stego.reveal(res.stego_rgb, dek).text() == "meet at 9"
    with pytest.raises(stego.StegoError):
        stego.reveal(res.stego_rgb, crypto.random_key())


def test_png_survives_and_jpeg_destroys(cover):
    from PIL import Image
    import io
    dek = crypto.random_key()
    res = stego.hide(cover, SecretPayload.from_text("lossless only"), dek)
    arr, fmt = stego.load_image(stego.to_png_bytes(res.stego_rgb))
    assert fmt == "PNG" and stego.reveal(arr, dek).text() == "lossless only"
    buf = io.BytesIO()
    Image.fromarray(res.stego_rgb).save(buf, "JPEG", quality=95)
    jarr, _ = stego.load_image(buf.getvalue())
    with pytest.raises(stego.StegoError):
        stego.reveal(jarr, dek)


def test_single_bit_flip_detected(cover):
    dek = crypto.random_key()
    res = stego.hide(cover, SecretPayload.from_text("integrity"), dek)
    pos = lsb.keyed_positions(stego.lsb_seed(dek), lsb.slot_count(cover.shape), (38 + 30) * 8)
    tampered = res.stego_rgb.copy()
    tampered.reshape(-1)[pos[-1]] ^= 1                  # flip one ciphertext bit
    with pytest.raises(stego.StegoError):
        stego.reveal(tampered, dek)
