"""LSB embedding and keyed random slot selection."""
import numpy as np
import pytest

from facelock import lsb


def test_roundtrip_random(cover):
    data = b"FaceLock" * 50
    seed = b"\x01" * 32
    st = lsb.embed_bytes(cover, data, seed)
    assert lsb.extract_bytes(st, len(data), seed) == data


def test_roundtrip_sequential(cover):
    data = bytes(range(256))
    st = lsb.embed_bytes(cover, data, None)
    assert lsb.extract_bytes(st, len(data), None) == data


def test_only_lsb_changes(cover):
    st = lsb.embed_bytes(cover, b"\xff" * 2000, b"\x02" * 32)
    diff = np.abs(st.astype(int) - cover.astype(int))
    assert diff.max() <= 1


def test_positions_distinct_and_in_range():
    pos = lsb.keyed_positions(b"\x03" * 32, 10_000, 9_000)
    assert len(set(pos.tolist())) == 9_000
    assert pos.min() >= 0 and pos.max() < 10_000


def test_positions_prefix_consistent():
    seed = b"\x04" * 32
    a = lsb.keyed_positions(seed, 50_000, 304)
    b = lsb.keyed_positions(seed, 50_000, 20_000)
    assert np.array_equal(a, b[:304])


def test_positions_depend_on_key():
    a = lsb.keyed_positions(b"\x05" * 32, 50_000, 1000)
    b = lsb.keyed_positions(b"\x06" * 32, 50_000, 1000)
    assert not np.array_equal(a, b)
    assert len(np.intersect1d(a, b)) < 100          # ~20 expected by chance


def test_positions_are_spread_not_sequential():
    pos = lsb.keyed_positions(b"\x07" * 32, 100_000, 10_000)
    # sequential would put everything in the first 10% of the image
    assert (pos > 50_000).mean() == pytest.approx(0.5, abs=0.05)


def test_wrong_key_reads_garbage(cover):
    data = b"top secret message " * 10
    st = lsb.embed_bytes(cover, data, b"\x08" * 32)
    assert lsb.extract_bytes(st, len(data), b"\x09" * 32) != data


def test_full_capacity(cover):
    cap = lsb.capacity_bytes(cover.shape)
    data = np.random.default_rng(0).integers(0, 256, cap, dtype=np.uint8).tobytes()
    seed = b"\x0a" * 32
    assert lsb.extract_bytes(lsb.embed_bytes(cover, data, seed), cap, seed) == data


def test_over_capacity_raises(cover):
    with pytest.raises(lsb.CapacityError):
        lsb.embed_bytes(cover, b"x" * (lsb.capacity_bytes(cover.shape) + 1), b"\x0b" * 32)


def test_alpha_is_split_off():
    rgba = np.zeros((10, 10, 4), np.uint8)
    rgba[..., 3] = 200
    rgb, alpha = lsb.to_carrier(rgba)
    assert rgb.shape == (10, 10, 3) and alpha is not None and alpha.max() == 200
