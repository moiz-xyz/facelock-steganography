"""Synthetic webcam bursts for automated tests (no camera, no real people).

From a single still face this module renders short "videos" (lists of BGR
frames) that imitate what the browser sends during a liveness scan:

* ``live_burst``  - natural jitter + eye blinks (+ a head turn for turn challenges)
* ``photo_burst`` - a still photo held in front of the camera (hand-shake only)

Eye closure is painted with skin colour over the MediaPipe eye contour; a
head turn is approximated with a perspective warp. Both are crude but they
move the exact landmark signals (EAR, nose ratio) the liveness module reads.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

FIXTURES = Path(__file__).parent / "fixtures" / "synthetic_faces"
MODELS = Path(__file__).resolve().parent.parent / "models"
EYE_L = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
EYE_R = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]


def face(i: int) -> np.ndarray:
    img = cv2.imread(str(FIXTURES / f"gan_{i}.jpg"))
    canvas = np.full((480, 640, 3), 40, np.uint8)
    f = cv2.resize(img, (440, 440))
    canvas[20:460, 100:540] = f
    return canvas


@lru_cache(maxsize=1)
def _landmarker():
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision
    opts = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(MODELS / "face_landmarker.task")))
    return mp, vision.FaceLandmarker.create_from_options(opts)


def landmarks(img: np.ndarray) -> np.ndarray:
    mp, lm = _landmarker()
    r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
    h, w = img.shape[:2]
    return np.array([[p.x * w, p.y * h] for p in r.face_landmarks[0]])


def close_eyes(img: np.ndarray, pts: np.ndarray) -> np.ndarray:
    out = img.astype(np.float64)
    for eye in (EYE_L, EYE_R):
        poly = pts[eye]
        c = poly.mean(0)
        hgt = np.ptp(poly[:, 1])
        hull = cv2.convexHull(poly.astype(np.int32))
        big = ((hull - c) * 1.35 + c).astype(np.int32)
        y0, x0 = int(c[1] + hgt * 1.6), int(c[0])
        skin = img[y0:y0 + max(2, int(hgt * 0.6)), x0 - 10:x0 + 10].reshape(-1, 3).mean(0)
        mask = np.zeros(img.shape[:2], np.uint8)
        cv2.fillPoly(mask, [big], 255)
        m = (cv2.GaussianBlur(mask, (9, 9), 0) / 255.0)[..., None]
        out = out * (1 - m) + skin * m
        res = out.astype(np.uint8)
        xs = poly[:, 0]
        cv2.line(res, (int(xs.min()), int(c[1] + hgt * 0.2)), (int(xs.max()), int(c[1] + hgt * 0.2)), (40, 30, 30), 2)
        out = res.astype(np.float64)
    return out.astype(np.uint8)


def turn(img: np.ndarray, direction: int, k: float) -> np.ndarray:
    """Rotate the head like a cylinder about the vertical axis by ``k * 35`` degrees.

    direction=+1 imitates the subject turning to *their* left (nose -> image right).
    """
    h, w = img.shape[:2]
    cx, R = w / 2, w * 0.36                       # face ~ cylinder of radius R around the image centre
    theta = np.deg2rad(35 * k) * direction
    xs = np.arange(w, dtype=np.float32)
    u = np.clip((xs - cx) / R, -1, 1)
    phi = np.arcsin(u) - theta                    # angle on the cylinder seen at output column x
    src_x = np.where(np.abs(phi) < np.pi / 2, cx + R * np.sin(phi), xs).astype(np.float32)
    inside = np.abs(xs - cx) < R
    map_x = np.tile(np.where(inside, src_x, xs), (h, 1)).astype(np.float32)
    map_y = np.tile(np.arange(h, dtype=np.float32)[:, None], (1, w))
    return cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def jitter(img: np.ndarray, rng: np.random.Generator, amount: float = 1.0) -> np.ndarray:
    dx, dy = rng.normal(0, 2 * amount, 2)
    ang = rng.normal(0, 0.8 * amount)
    M = cv2.getRotationMatrix2D((img.shape[1] / 2, img.shape[0] / 2), ang, 1 + rng.normal(0, 0.01 * amount))
    M[:, 2] += (dx, dy)
    out = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), borderMode=cv2.BORDER_REPLICATE).astype(np.float64)
    out = out * (1 + rng.normal(0, 0.03 * amount)) + rng.normal(0, 2.0, out.shape)
    return np.clip(out, 0, 255).astype(np.uint8)


def live_burst(i: int, challenge: str, n: int = 40, seed: int = 0) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    base = face(i)
    pts = landmarks(base)
    closed = close_eyes(base, pts)
    blinks = {9, 10, 22, 23} if challenge == "blink_twice" else {7, 8}
    frames = []
    for t in range(n):
        f = closed if t in blinks else base
        if challenge in ("turn_left", "turn_right") and 14 <= t <= 32:
            phase = np.sin(np.pi * (t - 14) / 18)          # 0 -> 1 -> 0
            f = turn(f, +1 if challenge == "turn_left" else -1, 1.0 * phase)   # peak 35 degrees
        frames.append(jitter(f, rng))
    return frames


def photo_burst(i: int, n: int = 40, seed: int = 1) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    base = face(i)
    return [jitter(base, rng, 0.6) for _ in range(n)]


def enrollment_samples(i: int, n: int = 5, seed: int = 2) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    base = face(i)
    return [jitter(base, rng, 2.0) for _ in range(n)]


def jpeg(img: np.ndarray) -> bytes:
    return cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()
