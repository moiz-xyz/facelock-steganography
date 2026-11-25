"""Runtime configuration.

Every tunable value can be overridden with an environment variable prefixed with
``FACELOCK_`` (for example ``FACELOCK_FACE_THRESHOLD=0.45``). Values are read once
at import time; tests construct their own ``Settings`` objects when needed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _env(name: str, default: str) -> str:
    return os.environ.get(f"FACELOCK_{name}", default)


@dataclass(frozen=True)
class Settings:
    # Storage -----------------------------------------------------------------
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", str(BACKEND_DIR / "data"))))
    models_dir: Path = field(default_factory=lambda: Path(_env("MODELS_DIR", str(BACKEND_DIR / "models"))))
    demo_dir: Path = field(default_factory=lambda: Path(_env("DEMO_DIR", str(BACKEND_DIR / "demo"))))

    # Face recognition ----------------------------------------------------------
    face_engine: str = field(default_factory=lambda: _env("FACE_ENGINE", "auto"))  # auto | sface | deepface
    # Cosine similarity: SFace authors recommend 0.363; we default slightly stricter.
    face_threshold: float = field(default_factory=lambda: float(_env("FACE_THRESHOLD", "0.40")))
    enroll_samples: int = field(default_factory=lambda: int(_env("ENROLL_SAMPLES", "5")))
    max_authorized_faces: int = 3

    # Liveness ------------------------------------------------------------------
    liveness_required: bool = field(default_factory=lambda: _env("LIVENESS_REQUIRED", "1") == "1")
    min_liveness_frames: int = 12
    blink_ratio: float = 0.62          # EAR must fall below this fraction of the open-eye baseline
    turn_delta: float = 0.10           # required change of the nose-position ratio for a head turn
    challenge_ttl_s: int = 120

    # Lockout -------------------------------------------------------------------
    max_failures: int = field(default_factory=lambda: int(_env("MAX_FAILURES", "3")))
    lockout_seconds: int = field(default_factory=lambda: int(_env("LOCKOUT_SECONDS", "60")))

    # Limits --------------------------------------------------------------------
    max_image_pixels: int = 16_000_000
    max_upload_mb: int = 40

    # Argon2id parameters for the backup password (OWASP 2024 baseline or stronger)
    argon2_time_cost: int = 3
    argon2_memory_kib: int = 65536
    argon2_parallelism: int = 2

    @property
    def profiles_dir(self) -> Path:
        return self.data_dir / "profiles"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def intruders_dir(self) -> Path:
        return self.data_dir / "intruders"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "security.db"

    @property
    def device_key_path(self) -> Path:
        return self.data_dir / "device.key"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.profiles_dir, self.jobs_dir, self.intruders_dir):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
