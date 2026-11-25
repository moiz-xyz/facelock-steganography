"""Least-Significant-Bit embedding with key-driven random slot selection.

An RGB image of ``W x H`` pixels offers ``N = W*H*3`` *slots* (one LSB per
colour channel). Alpha channels are never touched.

Random selection
----------------
The order in which slots are used is a keyed pseudo-random permutation:

1. A 32-byte seed (derived from the data key, never stored in the image) keys
   AES-256-CTR, producing a deterministic keystream of ``N`` 64-bit words.
2. Each word's low 26 bits are replaced by the slot index, which makes every
   sort key unique (so ordering is fully deterministic, no ties).
3. The slots with the ``k`` smallest keys, in ascending key order, are the
   positions used. ``argpartition`` makes this O(N + k log k) and the result is
   *prefix-consistent*: the first 38 bytes' positions (the header) are exactly
   the first positions of the full payload, so the header can be read first.

Without the seed an attacker does not know which slots carry data or in which
order, and the changes are spread uniformly over the whole image instead of
being concentrated in the first rows (see ``steganalysis.py``).
"""
from __future__ import annotations

import numpy as np
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

INDEX_BITS = 26                      # supports up to 2**26 = 67M slots (~22 MP RGB)
MAX_SLOTS = 1 << INDEX_BITS


class CapacityError(ValueError):
    """The payload does not fit in the cover image."""


def to_carrier(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray | None]:
    """Split an HxWxC uint8 array into an RGB carrier and optional alpha plane."""
    if arr.dtype != np.uint8:
        raise ValueError("image must be 8-bit")
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    if arr.shape[2] == 4:
        return np.ascontiguousarray(arr[..., :3]), arr[..., 3].copy()
    return np.ascontiguousarray(arr[..., :3]), None


def slot_count(shape: tuple[int, ...]) -> int:
    h, w = shape[:2]
    return h * w * 3


def capacity_bytes(shape: tuple[int, ...]) -> int:
    """Raw byte capacity at 1 bit per colour channel."""
    return slot_count(shape) // 8


def keyed_positions(seed: bytes, n_slots: int, k: int) -> np.ndarray:
    """Return ``k`` distinct slot indices in key-dependent pseudo-random order."""
    if k > n_slots:
        raise CapacityError(f"need {k} bits but image only has {n_slots} slots")
    if n_slots > MAX_SLOTS:
        raise CapacityError("image too large for the position generator")
    if k == 0:
        return np.empty(0, dtype=np.int64)
    enc = Cipher(algorithms.AES(seed), modes.CTR(b"\x00" * 16)).encryptor()
    stream = enc.update(b"\x00" * (8 * n_slots)) + enc.finalize()
    keys = np.frombuffer(stream, dtype=">u8").astype(np.uint64)
    keys = (keys >> np.uint64(INDEX_BITS)) << np.uint64(INDEX_BITS)
    keys |= np.arange(n_slots, dtype=np.uint64)                 # unique keys -> no ties
    if k < n_slots:
        chosen = np.argpartition(keys, k - 1)[:k]
    else:
        chosen = np.arange(n_slots)
    order = np.argsort(keys[chosen], kind="stable")
    return chosen[order].astype(np.int64)


def sequential_positions(n_slots: int, k: int) -> np.ndarray:
    """Classic naive LSB: slots in raster order (used only as a baseline)."""
    if k > n_slots:
        raise CapacityError(f"need {k} bits but image only has {n_slots} slots")
    return np.arange(k, dtype=np.int64)


def bytes_to_bits(data: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def bits_to_bytes(bits: np.ndarray) -> bytes:
    return np.packbits(bits.astype(np.uint8)).tobytes()


def embed_bits(rgb: np.ndarray, positions: np.ndarray, bits: np.ndarray) -> np.ndarray:
    """Return a copy of ``rgb`` whose LSBs at ``positions`` equal ``bits``."""
    if len(positions) != len(bits):
        raise ValueError("positions/bits length mismatch")
    out = rgb.copy()
    flat = out.reshape(-1)
    flat[positions] = (flat[positions] & np.uint8(0xFE)) | bits.astype(np.uint8)
    return out


def read_bits(rgb: np.ndarray, positions: np.ndarray) -> np.ndarray:
    return rgb.reshape(-1)[positions] & np.uint8(1)


def embed_bytes(rgb: np.ndarray, data: bytes, seed: bytes | None) -> np.ndarray:
    """Embed ``data``; ``seed=None`` selects sequential (baseline) mode."""
    bits = bytes_to_bits(data)
    n = slot_count(rgb.shape)
    pos = sequential_positions(n, len(bits)) if seed is None else keyed_positions(seed, n, len(bits))
    return embed_bits(rgb, pos, bits)


def extract_bytes(rgb: np.ndarray, n_bytes: int, seed: bytes | None) -> bytes:
    n = slot_count(rgb.shape)
    k = n_bytes * 8
    pos = sequential_positions(n, k) if seed is None else keyed_positions(seed, n, k)
    return bits_to_bytes(read_bits(rgb, pos))
