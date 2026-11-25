import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def rng():
    return np.random.default_rng(1234)


@pytest.fixture
def cover(rng):
    """Natural-ish 200x160 test image: smooth gradient plus noise."""
    y, x = np.mgrid[0:160, 0:200]
    base = np.stack([x * 1.2, y * 1.5, (x + y) * 0.7], axis=-1)
    return np.clip(base + rng.normal(0, 6, base.shape), 0, 255).astype(np.uint8)
