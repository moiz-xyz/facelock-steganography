"""Server-side liveness detection from a short burst of webcam frames.

Two independent signals, both computed from MediaPipe Face Landmarker
(478 3-D landmarks) on the **server**:

1. **Blink detection - Eye Aspect Ratio (EAR)** (Soukupova & Cech, 2016)::

        EAR = (|p2 - p6| + |p3 - p5|) / (2 |p1 - p4|)

   EAR is ~0.25-0.30 for an open eye and drops below ~0.15 during a blink.
   We use an *adaptive* threshold: a frame is "closed" when its EAR is below
   ``blink_ratio x`` the open-eye baseline (80th percentile of the burst).
   A blink is an open -> closed -> open transition.

2. **Head-turn challenge - nose position ratio**::

        r = (x_nose - x_leftmost_cheek) / (x_rightmost_cheek - x_leftmost_cheek)

   r ~ 0.5 for a frontal face. Frames are raw (un-mirrored) camera images, so
   when the user turns to *their* left the nose moves to the image's right and
   r increases.

3. **MediaPipe blink blendshape** (``eyeBlinkLeft/Right``, 0..1) as a second,
   pose-tolerant blink signal. With glasses or when the user looks down at the
   screen, the open-eye EAR is already low and a blink changes it only a little;
   the blendshape score still rises clearly. A frame counts as *closed* if EITHER
   signal says so, each relative to the user's own baseline in this burst.

A printed photo or a photo on a phone screen has a constant EAR and constant r,
so it can satisfy neither a blink nor a randomly chosen turn direction.
"""
from __future__ import annotations

import secrets
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .face_engine import ensure_model

LEFT_EYE = [33, 160, 158, 133, 153, 144]     # p1..p6 for the EAR formula
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
NOSE_TIP, CHEEK_A, CHEEK_B = 1, 234, 454

CHALLENGES = {
    "blink_twice": "Blink twice",
    "turn_left": "Slowly turn your head to your LEFT, then back",
    "turn_right": "Slowly turn your head to your RIGHT, then back",
}


@dataclass
class FrameObs:
    faces: int
    ear: float | None = None
    yaw: float | None = None
    blink: float | None = None      # mean MediaPipe eyeBlink blendshape score (0 = open, 1 = closed)


@dataclass
class LivenessResult:
    passed: bool
    reason: str
    challenge: str
    blinks: int
    turn_peak: float
    frames: int
    face_frames: int
    ear_series: list[float | None] = field(default_factory=list)
    yaw_series: list[float | None] = field(default_factory=list)
    blink_series: list[float | None] = field(default_factory=list)
    ear_baseline: float = 0.0
    yaw_baseline: float = 0.0
    blink_baseline: float = 0.0

    def public(self) -> dict:
        r = lambda v: None if v is None else round(float(v), 4)  # noqa: E731
        return {"passed": self.passed, "reason": self.reason, "challenge": self.challenge,
                "blinks": self.blinks, "turn_peak": round(self.turn_peak, 4), "frames": self.frames,
                "face_frames": self.face_frames, "ear_baseline": round(self.ear_baseline, 4),
                "yaw_baseline": round(self.yaw_baseline, 4),
                "ear_series": [r(v) for v in self.ear_series], "yaw_series": [r(v) for v in self.yaw_series],
                "blink_series": [r(v) for v in self.blink_series], "blink_baseline": round(self.blink_baseline, 4)}


def eye_aspect_ratio(pts: np.ndarray, idx: list[int]) -> float:
    p = pts[idx]
    v = np.linalg.norm(p[1] - p[5]) + np.linalg.norm(p[2] - p[4])
    h = 2.0 * np.linalg.norm(p[0] - p[3])
    return float(v / h) if h > 0 else 0.0


class LandmarkAnalyzer:
    def __init__(self, models_dir: Path):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        self._mp = mp
        path = ensure_model(models_dir, "face_landmarker.task")
        opts = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(path)),
                                            num_faces=2, min_face_detection_confidence=0.5,
                                            output_face_blendshapes=True)
        self._lm = vision.FaceLandmarker.create_from_options(opts)
        self._lock = threading.Lock()

    def observe(self, bgr: np.ndarray) -> FrameObs:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        with self._lock:
            res = self._lm.detect(self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb))
        n = len(res.face_landmarks)
        if n != 1:
            return FrameObs(faces=n)
        h, w = bgr.shape[:2]
        pts = np.array([[p.x * w, p.y * h] for p in res.face_landmarks[0]], dtype=np.float64)
        ear = (eye_aspect_ratio(pts, LEFT_EYE) + eye_aspect_ratio(pts, RIGHT_EYE)) / 2
        xa, xb = sorted((pts[CHEEK_A, 0], pts[CHEEK_B, 0]))
        yaw = (pts[NOSE_TIP, 0] - xa) / (xb - xa) if xb > xa else 0.5
        blink = None
        if res.face_blendshapes:
            d = {b.category_name: b.score for b in res.face_blendshapes[0]}
            blink = (d.get("eyeBlinkLeft", 0.0) + d.get("eyeBlinkRight", 0.0)) / 2
        return FrameObs(faces=1, ear=ear, yaw=float(yaw), blink=blink)


BLINK_RISE = 0.15     # blendshape score must rise this much above the user's own baseline ...
BLINK_MIN = 0.35      # ... and reach at least this value to count as "closed"


def count_blinks(ears: list[float | None], baseline: float, ratio: float,
                 scores: list[float | None] | None = None, score_baseline: float = 0.0) -> int:
    """Count open -> closed -> open transitions.

    A frame is *closed* if its EAR is below ``ratio`` x the open-eye baseline OR its
    blink blendshape score rose clearly above the user's baseline; it is *open* if the
    EAR is back near the baseline and the blink score is back near its baseline.
    """
    scores = scores or [None] * len(ears)
    closed_thr, open_thr = baseline * ratio, baseline * 0.85
    state, blinks, seen_open = "unknown", 0, False
    for e, b in zip(ears, scores):
        if e is None:
            continue
        b_closed = b is not None and b >= max(BLINK_MIN, score_baseline + BLINK_RISE)
        b_open = b is None or b < score_baseline + BLINK_RISE / 2
        if e >= open_thr and b_open:
            if state == "closed" and seen_open:
                blinks += 1
            state, seen_open = "open", True
        elif (e < closed_thr or b_closed) and state == "open":
            state = "closed"
    return blinks


def evaluate(obs: list[FrameObs], challenge: str, min_frames: int = 12,
             blink_ratio: float = 0.62, turn_delta: float = 0.10) -> LivenessResult:
    ears = [o.ear if o.faces == 1 else None for o in obs]
    yaws = [o.yaw if o.faces == 1 else None for o in obs]
    scores = [o.blink if o.faces == 1 else None for o in obs]
    good = [o for o in obs if o.faces == 1]
    res = LivenessResult(False, "", challenge, 0, 0.0, len(obs), len(good), ears, yaws, scores)

    if any(o.faces > 1 for o in obs):
        res.reason = "more than one face appeared during the scan"
        return res
    if len(good) < max(min_frames, int(0.6 * len(obs))):
        res.reason = f"face visible in only {len(good)}/{len(obs)} frames"
        return res

    ev = np.array([o.ear for o in good])
    yv = np.array([o.yaw for o in good])
    res.ear_baseline = float(np.percentile(ev, 80))
    res.yaw_baseline = float(np.median(yv[: max(3, len(yv) // 6)]))
    bv = [o.blink for o in good if o.blink is not None]
    res.blink_baseline = float(np.median(bv)) if bv else 0.0
    res.blinks = count_blinks(ears, res.ear_baseline, blink_ratio, scores, res.blink_baseline)
    dev = yv - res.yaw_baseline
    res.turn_peak = float(dev.max() if challenge == "turn_left" else -dev.min() if challenge == "turn_right"
                          else np.abs(dev).max())

    if np.std(ev) < 0.006 and np.std(yv) < 0.006:
        res.reason = "no natural motion detected (static photo or screen replay suspected)"
        return res
    if res.ear_baseline < 0.15:
        res.reason = "eyes not clearly visible (remove sunglasses / improve lighting)"
        return res
    if res.blinks < 1:
        res.reason = "no eye blink detected"
        return res
    if challenge == "blink_twice" and res.blinks < 2:
        res.reason = f"challenge failed: asked for 2 blinks, saw {res.blinks}"
        return res
    if challenge in ("turn_left", "turn_right") and res.turn_peak < turn_delta:
        side = "left" if challenge == "turn_left" else "right"
        res.reason = f"challenge failed: no head turn to the {side} detected"
        return res
    res.passed, res.reason = True, "live person confirmed"
    return res


class ChallengeBook:
    """Single-use, time-limited random challenges issued by the server."""

    def __init__(self, ttl_s: int = 120):
        self.ttl = ttl_s
        self._items: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    def issue(self) -> dict:
        cid = uuid.uuid4().hex
        kind = secrets.choice(list(CHALLENGES))
        with self._lock:
            now = time.time()
            self._items = {k: v for k, v in self._items.items() if now - v[1] < self.ttl}
            self._items[cid] = (kind, now)
        return {"challenge_id": cid, "type": kind, "instruction": CHALLENGES[kind], "ttl": self.ttl}

    def consume(self, cid: str) -> str | None:
        with self._lock:
            item = self._items.pop(cid, None)
        if not item or time.time() - item[1] > self.ttl:
            return None
        return item[0]
