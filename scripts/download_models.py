"""Download the three model files (YuNet, SFace, MediaPipe Face Landmarker) into app/backend/models."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "app" / "backend"
sys.path.insert(0, str(BACKEND))
from facelock.face_engine import MODEL_URLS, ensure_model  # noqa: E402

for name in MODEL_URLS:
    p = ensure_model(BACKEND / "models", name)
    print(f"  {name:40s} {p.stat().st_size / 1e6:6.1f} MB")
