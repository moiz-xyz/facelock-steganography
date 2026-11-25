"""Chi-square attack behaviour and the lockout state machine."""
import time

import numpy as np

from facelock import lsb, steganalysis
from facelock.security_log import SecurityLog


def test_chi_square_flags_full_embedding(cover):
    big = np.repeat(np.repeat(cover, 3, 0), 3, 1)
    p_clean = steganalysis.chi_square_p(big.reshape(-1))
    data = np.random.default_rng(0).integers(0, 256, lsb.capacity_bytes(big.shape), dtype=np.uint8).tobytes()
    p_full = steganalysis.chi_square_p(lsb.embed_bytes(big, data, None).reshape(-1))
    assert p_full > 0.9 and p_full > p_clean


def test_lockout_after_three(tmp_path):
    log = SecurityLog(tmp_path / "s.db", max_failures=3, lockout_seconds=1)
    assert not log.register_failure("v")["locked"]
    assert not log.register_failure("v")["locked"]
    st = log.register_failure("v")
    assert st["locked"] and st["failures"] == 3
    time.sleep(1.1)
    assert not log.lock_status("v")["locked"]
    assert log.register_failure("v")["failures"] == 1      # counter restarts after lockout


def test_success_resets(tmp_path):
    log = SecurityLog(tmp_path / "s.db", 3, 60)
    log.register_failure("v"); log.register_failure("v")
    log.register_success("v")
    assert log.lock_status("v")["failures"] == 0


def test_log_records(tmp_path):
    log = SecurityLog(tmp_path / "s.db")
    i = log.record("extract", "denied", "liveness failed", method="face", details={"x": 1})
    log.set_photo(i, "1.jpg")
    items = log.list()
    assert items[0]["photo"] == "1.jpg" and items[0]["details"] == {"x": 1}
