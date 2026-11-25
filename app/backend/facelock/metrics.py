"""Image-quality metrics and visual analysis helpers (PSNR, MSE, SSIM, heatmaps, bit planes)."""
from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity


def mse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    """Peak signal-to-noise ratio in dB; ``inf`` for identical images."""
    m = mse(a, b)
    return float("inf") if m == 0 else float(10 * np.log10(255.0 ** 2 / m))


def ssim(a: np.ndarray, b: np.ndarray) -> float:
    a3, b3 = a[..., :3], b[..., :3]
    win = min(7, min(a3.shape[:2]) // 2 * 2 - 1)
    return float(structural_similarity(a3, b3, channel_axis=2, data_range=255, win_size=win))


def quality(cover: np.ndarray, stego: np.ndarray) -> dict:
    c, s = cover[..., :3], stego[..., :3]
    changed = np.any(c != s, axis=2)
    p = psnr(c, s)
    return {"psnr": None if p == float("inf") else round(p, 3), "mse": round(mse(c, s), 6),
            "ssim": round(ssim(c, s), 6), "changed_pixels": int(changed.sum()),
            "changed_channel_values": int((c != s).sum()), "total_pixels": int(changed.size),
            "max_abs_diff": int(np.abs(c.astype(int) - s.astype(int)).max())}


def png_bytes(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def diff_heatmap(cover: np.ndarray, stego: np.ndarray, enlarge: bool = True) -> np.ndarray:
    """Changed LSBs per pixel (0..3, INFERNO colours) over a dimmed grey copy of the cover.

    With random embedding only a small, scattered fraction of pixels changes, so for
    display each changed pixel is dilated to 3x3 (``enlarge``); the counts are exact.
    """
    d = (cover[..., :3] != stego[..., :3]).sum(axis=2).astype(np.uint8)
    if enlarge:
        d = cv2.dilate(d, np.ones((3, 3), np.uint8))
    colour = cv2.cvtColor(cv2.applyColorMap((d * 85).astype(np.uint8), cv2.COLORMAP_INFERNO), cv2.COLOR_BGR2RGB)
    grey = cv2.cvtColor(cover[..., :3], cv2.COLOR_RGB2GRAY)
    base = np.repeat((grey * 0.22).astype(np.uint8)[..., None], 3, axis=2)
    return np.where(d[..., None] > 0, colour, base).astype(np.uint8)


def bit_plane(img: np.ndarray, channel: int, bit: int) -> np.ndarray:
    return (((img[..., channel] >> bit) & 1) * 255).astype(np.uint8)


def histograms(cover: np.ndarray, stego: np.ndarray) -> list[dict]:
    out = []
    hc = [np.bincount(cover[..., c].ravel(), minlength=256) for c in range(3)]
    hs = [np.bincount(stego[..., c].ravel(), minlength=256) for c in range(3)]
    for v in range(256):
        out.append({"v": v, "coverR": int(hc[0][v]), "stegoR": int(hs[0][v]),
                    "coverG": int(hc[1][v]), "stegoG": int(hs[1][v]),
                    "coverB": int(hc[2][v]), "stegoB": int(hs[2][v])})
    return out


def thumbnail(arr: np.ndarray, max_side: int = 900) -> np.ndarray:
    h, w = arr.shape[:2]
    s = max_side / max(h, w)
    if s >= 1:
        return arr
    return cv2.resize(arr, (int(w * s), int(h * s)), interpolation=cv2.INTER_NEAREST)
