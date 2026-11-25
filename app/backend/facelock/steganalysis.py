"""Chi-square steganalysis (Westfeld & Pfitzmann, 1999).

LSB *replacement* tends to equalise the frequencies of each "pair of values"
(2i, 2i+1) because it only ever toggles between them. For a sample of channel
values we compute::

    chi2 = sum_i (n_{2i} - E_i)^2 / E_i,     E_i = (n_{2i} + n_{2i+1}) / 2

and the probability of embedding ``p = 1 - CDF_chi2(chi2, k - 1)``.
p ~ 1 means "the pairs look equalised -> embedding very likely".

The classic attack scans the image in raster order and evaluates growing
prefixes (1%, 2%, ..., 100%). Sequential LSB lights up p ~ 1 for exactly the
embedded prefix. Keyed-random embedding spreads the same changes thinly over
the whole image, so every prefix carries only a fraction of modified samples.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import chi2 as chi2_dist


def chi_square_p(values: np.ndarray) -> float:
    hist = np.bincount(values, minlength=256).astype(np.float64)
    even, odd = hist[0::2], hist[1::2]
    expected = (even + odd) / 2.0
    mask = expected > 4                       # standard validity rule for chi-square
    if mask.sum() < 2:
        return 0.0
    stat = float(np.sum((even[mask] - expected[mask]) ** 2 / expected[mask]))
    return float(chi2_dist.sf(stat, int(mask.sum()) - 1))


def prefix_scan(img: np.ndarray, steps: int = 50) -> list[dict]:
    """p-value of the chi-square attack over growing raster-order prefixes."""
    flat = img[..., :3].reshape(-1)
    n = flat.size
    out = []
    for i in range(1, steps + 1):
        k = int(n * i / steps)
        out.append({"pct": round(100 * i / steps, 1), "p": round(chi_square_p(flat[:k]), 6)})
    return out


def detection_summary(scan: list[dict], threshold: float = 0.95) -> dict:
    """How much of the image 'looks embedded' and the mean p-value over the scan."""
    ps = np.array([s["p"] for s in scan])
    above = ps >= threshold
    # length of the leading run of prefixes flagged as embedded
    lead = int(np.argmin(above)) if not above.all() else len(above)
    return {"mean_p": round(float(ps.mean()), 4), "max_p": round(float(ps.max()), 4),
            "flagged_prefix_pct": round(100 * lead / len(ps), 1),
            "flagged_any": bool(above.any())}
