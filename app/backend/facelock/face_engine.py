"""Face detection + embedding with automatic backend selection.

Primary backend: **OpenCV YuNet (detector) + SFace (128-D embedding)**. Both ship
inside ``opencv-contrib-python`` wheels, so there is nothing to compile on
Windows/macOS/Linux (no dlib, no CMake). Model files (~39 MB) are downloaded
from the official OpenCV Zoo by ``scripts/setup`` or on first use.

Fallback backend: **DeepFace (Facenet512)**, used automatically if OpenCV's
face module is unavailable or the SFace models cannot be loaded and the
``deepface`` package is installed.
"""
from __future__ import annotations

import logging
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger("facelock.face")

MODEL_URLS = {
    "face_detection_yunet_2023mar.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
    "face_landmarker.task":
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
}


class FaceError(Exception):
    """User-facing problem with a face image (no face, several faces, too small...)."""


@dataclass
class DetectedFace:
    box: tuple[int, int, int, int]   # x, y, w, h
    score: float
    raw: object                      # backend-specific detection record


def ensure_model(models_dir: Path, name: str) -> Path:
    path = models_dir / name
    if not path.exists():
        models_dir.mkdir(parents=True, exist_ok=True)
        log.warning("downloading missing model %s", name)
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(MODEL_URLS[name], tmp)
        tmp.rename(path)
    return path


def l2n(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32).reshape(-1)
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(l2n(a), l2n(b)))


def resize_max(img: np.ndarray, max_side: int = 640) -> np.ndarray:
    h, w = img.shape[:2]
    s = max_side / max(h, w)
    return cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA) if s < 1 else img


class SFaceBackend:
    name = "sface"
    dim = 128

    def __init__(self, models_dir: Path):
        det = ensure_model(models_dir, "face_detection_yunet_2023mar.onnx")
        rec = ensure_model(models_dir, "face_recognition_sface_2021dec.onnx")
        self._det = cv2.FaceDetectorYN.create(str(det), "", (320, 320), 0.75, 0.3, 50)
        self._rec = cv2.FaceRecognizerSF.create(str(rec), "")
        self._lock = threading.Lock()

    def detect(self, bgr: np.ndarray) -> list[DetectedFace]:
        h, w = bgr.shape[:2]
        with self._lock:
            self._det.setInputSize((w, h))
            _, faces = self._det.detect(bgr)
        if faces is None:
            return []
        return [DetectedFace(tuple(int(v) for v in f[:4]), float(f[-1]), f) for f in faces]

    def embed(self, bgr: np.ndarray, face: DetectedFace) -> np.ndarray:
        with self._lock:
            aligned = self._rec.alignCrop(bgr, face.raw)
            return l2n(self._rec.feature(aligned))


class DeepFaceBackend:
    name = "deepface"
    dim = 512

    def __init__(self, models_dir: Path):  # noqa: ARG002 - same signature as SFace
        from deepface import DeepFace  # heavy import, only when needed
        self._df = DeepFace
        self._lock = threading.Lock()

    def detect(self, bgr: np.ndarray) -> list[DetectedFace]:
        with self._lock:
            objs = self._df.extract_faces(bgr, detector_backend="opencv", enforce_detection=False)
        out = []
        for o in objs:
            a = o["facial_area"]
            if o.get("confidence", 0) > 0:
                out.append(DetectedFace((a["x"], a["y"], a["w"], a["h"]), float(o["confidence"]), o))
        return out

    def embed(self, bgr: np.ndarray, face: DetectedFace) -> np.ndarray:
        x, y, w, h = face.box
        crop = bgr[max(0, y):y + h, max(0, x):x + w]
        with self._lock:
            rep = self._df.represent(crop, model_name="Facenet512", detector_backend="skip")
        return l2n(rep[0]["embedding"])


class FaceEngine:
    """Facade used by the rest of the app; picks a working backend at start-up."""

    def __init__(self, models_dir: Path, preference: str = "auto"):
        order = {"auto": ["sface", "deepface"], "sface": ["sface"], "deepface": ["deepface"]}[preference]
        errors = []
        self.backend = None
        for name in order:
            try:
                self.backend = (SFaceBackend if name == "sface" else DeepFaceBackend)(models_dir)
                self._self_test()
                break
            except Exception as exc:  # noqa: BLE001 - we want to try the next backend
                errors.append(f"{name}: {exc}")
                log.warning("face backend %s unavailable: %s", name, exc)
                self.backend = None
        if self.backend is None:
            raise RuntimeError("no face-recognition backend available -> " + "; ".join(errors))
        self.fallback_errors = errors
        log.info("face backend: %s", self.backend.name)

    def _self_test(self) -> None:
        blank = np.zeros((240, 320, 3), np.uint8)
        self.backend.detect(blank)   # must run without raising

    @property
    def name(self) -> str:
        return self.backend.name

    def faces(self, bgr: np.ndarray) -> list[DetectedFace]:
        return self.backend.detect(bgr)

    def single_face_embedding(self, bgr: np.ndarray, min_size: int = 60, min_score: float = 0.8
                              ) -> tuple[np.ndarray, DetectedFace]:
        img = resize_max(bgr)
        faces = [f for f in self.backend.detect(img) if f.score >= min_score]
        if not faces:
            raise FaceError("no face detected")
        if len(faces) > 1:
            raise FaceError(f"{len(faces)} faces detected - only one person may be in view")
        f = faces[0]
        if min(f.box[2], f.box[3]) < min_size:
            raise FaceError("face too small - move closer to the camera")
        return self.backend.embed(img, f), f


def decode_jpeg(data: bytes) -> np.ndarray:
    arr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        raise FaceError("could not decode camera frame")
    return arr
