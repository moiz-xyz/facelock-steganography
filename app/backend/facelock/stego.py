r"""Stego container: encrypt a payload with the data key and hide it in a PNG.

Embedded bitstream (all at keyed random positions)::

    +-------+-----+-------+---------+--------+--------+-----------------------+
    | magic | ver | flags | ct_len  | salt   | nonce  | ciphertext || GCM tag  |
    |  4 B  | 1 B |  1 B  |  4 B    | 16 B   | 12 B   | ct_len bytes          |
    +-------+-----+-------+---------+--------+--------+-----------------------+
    \_______________ header: 38 bytes, used as GCM AAD ____/

* ``msg_key  = HKDF(DEK, salt, "facelock/msg/v1")``  - encrypts the payload
* ``seed     = HKDF(DEK, "",   "facelock/lsb/v1")``  - drives slot selection

The DEK (data encryption key) is random per message and lives only in the
Face Vault, so the image on its own reveals neither the positions nor the data.
"""
from __future__ import annotations

import io
import struct
import time
from dataclasses import dataclass

import numpy as np
from PIL import Image

from . import crypto, lsb
from .payload import SecretPayload, pack, unpack

MAGIC = b"FLS1"
VERSION = 1
HEADER_FMT = ">4sBBI16s12s"
HEADER_LEN = struct.calcsize(HEADER_FMT)   # 38
OVERHEAD = HEADER_LEN + crypto.TAG_LEN     # fixed bytes added around the packed payload


class StegoError(Exception):
    """Generic failure while hiding or revealing."""


@dataclass
class HideResult:
    stego_rgb: np.ndarray
    alpha: np.ndarray | None
    embedded_bytes: int
    capacity_bytes: int
    embed_seconds: float


def lsb_seed(dek: bytes) -> bytes:
    return crypto.hkdf(dek, b"", b"facelock/lsb/v1")


def load_image(data: bytes, max_pixels: int = 16_000_000) -> tuple[np.ndarray, str]:
    """Decode an uploaded image to an 8-bit RGB(A) array. Returns (array, original format)."""
    try:
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or "").upper()
        img.load()
    except Exception as exc:  # PIL raises many different types
        raise StegoError(f"unreadable image: {exc}") from exc
    if img.width * img.height > max_pixels:
        raise StegoError(f"image too large ({img.width}x{img.height}); limit is {max_pixels:,} pixels")
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if ("A" in img.mode or "transparency" in img.info) else "RGB")
    return np.asarray(img, dtype=np.uint8).copy(), fmt


def to_png_bytes(rgb: np.ndarray, alpha: np.ndarray | None = None) -> bytes:
    arr = rgb if alpha is None else np.dstack([rgb, alpha])
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG", optimize=False, compress_level=6)
    return buf.getvalue()


def pixel_fingerprint(arr: np.ndarray) -> str:
    """SHA-256 over decoded pixels (independent of PNG compression settings)."""
    return crypto.sha256_hex(struct.pack(">III", *arr.shape[:2], arr.shape[2] if arr.ndim == 3 else 1)
                             + arr.tobytes())


def payload_capacity(shape: tuple[int, ...]) -> int:
    """Max size of the *packed* payload (before encryption) that fits."""
    return max(0, lsb.capacity_bytes(shape) - OVERHEAD)


def encrypt_payload(payload: SecretPayload, dek: bytes, compress: bool = True) -> bytes:
    packed = pack(payload, compress)
    salt = crypto.random_bytes(crypto.SALT_LEN)
    nonce = crypto.random_bytes(crypto.NONCE_LEN)
    ct_len = len(packed) + crypto.TAG_LEN
    header = struct.pack(HEADER_FMT, MAGIC, VERSION, 0, ct_len, salt, nonce)
    key = crypto.hkdf(dek, salt, b"facelock/msg/v1")
    _, ct = crypto.aes_gcm_encrypt(key, packed, aad=header, nonce=nonce)
    return header + ct


def hide(cover: np.ndarray, payload: SecretPayload, dek: bytes, random_positions: bool = True,
         compress: bool = True) -> HideResult:
    rgb, alpha = lsb.to_carrier(cover)
    blob = encrypt_payload(payload, dek, compress)
    cap = lsb.capacity_bytes(rgb.shape)
    if len(blob) > cap:
        raise lsb.CapacityError(
            f"payload needs {len(blob):,} bytes after encryption but the image holds {cap:,} bytes")
    t0 = time.perf_counter()
    stego = lsb.embed_bytes(rgb, blob, lsb_seed(dek) if random_positions else None)
    return HideResult(stego, alpha, len(blob), cap, time.perf_counter() - t0)


def reveal(stego: np.ndarray, dek: bytes, random_positions: bool = True) -> SecretPayload:
    rgb, _ = lsb.to_carrier(stego)
    n_slots = lsb.slot_count(rgb.shape)
    seed = lsb_seed(dek) if random_positions else None
    # One permutation serves both header and body (it is prefix-consistent).
    max_k = (n_slots // 8) * 8
    if seed is not None:
        hdr_pos = lsb.keyed_positions(seed, n_slots, HEADER_LEN * 8)
    else:
        hdr_pos = lsb.sequential_positions(n_slots, HEADER_LEN * 8)
    header = lsb.bits_to_bytes(lsb.read_bits(rgb, hdr_pos))
    magic, ver, _flags, ct_len, salt, nonce = struct.unpack(HEADER_FMT, header)
    if magic != MAGIC or ver != VERSION:
        raise StegoError("no FaceLock payload found with this key (wrong vault or image)")
    total_bits = (HEADER_LEN + ct_len) * 8
    if total_bits > max_k:
        raise StegoError("header length field is invalid")
    pos = (lsb.keyed_positions(seed, n_slots, total_bits) if seed is not None
           else lsb.sequential_positions(n_slots, total_bits))
    blob = lsb.bits_to_bytes(lsb.read_bits(rgb, pos))
    key = crypto.hkdf(dek, salt, b"facelock/msg/v1")
    try:
        packed = crypto.aes_gcm_decrypt(key, nonce, blob[HEADER_LEN:], aad=blob[:HEADER_LEN])
    except crypto.DecryptionError as exc:
        raise StegoError("integrity check failed: image was modified or recompressed") from exc
    return unpack(packed)
