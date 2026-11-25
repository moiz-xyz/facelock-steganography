"""Face engine: real SFace backend on a synthetic face, and the automatic fallback logic."""
from pathlib import Path

import numpy as np
import pytest

from facelock import face_engine
from facelock.face_engine import FaceEngine, FaceError, cosine
from tests import synth

MODELS = Path(__file__).resolve().parent.parent / "models"


def test_sface_embeds_and_separates_people():
    eng = FaceEngine(MODELS, "sface")
    assert eng.name == "sface"
    a1, _ = eng.single_face_embedding(synth.enrollment_samples(1)[0])
    a2, _ = eng.single_face_embedding(synth.enrollment_samples(1)[1])
    b, _ = eng.single_face_embedding(synth.face(4))
    assert a1.shape == (128,) and abs(np.linalg.norm(a1) - 1) < 1e-4
    assert cosine(a1, a2) > 0.8 and cosine(a1, b) < 0.4


def test_no_face_raises():
    eng = FaceEngine(MODELS, "sface")
    with pytest.raises(FaceError):
        eng.single_face_embedding(np.full((480, 640, 3), 90, np.uint8))


def test_auto_falls_back_when_primary_fails(monkeypatch):
    class Broken:
        def __init__(self, _):
            raise RuntimeError("model file corrupt")

    class Fake:
        name = "deepface"

        def __init__(self, _):
            pass

        def detect(self, img):
            return []

    monkeypatch.setattr(face_engine, "SFaceBackend", Broken)
    monkeypatch.setattr(face_engine, "DeepFaceBackend", Fake)
    eng = FaceEngine(MODELS, "auto")
    assert eng.name == "deepface" and "sface: model file corrupt" in eng.fallback_errors[0]


def test_all_backends_failing_gives_clear_error(monkeypatch):
    class Broken:
        def __init__(self, _):
            raise RuntimeError("unavailable")

    monkeypatch.setattr(face_engine, "SFaceBackend", Broken)
    monkeypatch.setattr(face_engine, "DeepFaceBackend", Broken)
    with pytest.raises(RuntimeError, match="no face-recognition backend available.*sface.*deepface"):
        FaceEngine(MODELS, "auto")
