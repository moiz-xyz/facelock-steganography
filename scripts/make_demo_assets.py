"""Create the Demo Mode assets used by the web app.

    python scripts/make_demo_assets.py

* Copies 8 varied cover images from dataset/covers into app/backend/demo/covers.
* Builds a ready-made stego image + vault ("demo pair") protected by the backup
  password below, so the Extract page can always be demonstrated even if the
  webcam fails. The pair has no face slots because face slots are bound to the
  device key of the machine that created them (by design).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "app" / "backend"
sys.path.insert(0, str(BACKEND))

from facelock import crypto, stego, vault  # noqa: E402
from facelock.payload import SecretPayload  # noqa: E402

DEMO = BACKEND / "demo"
PASSWORD = "FaceLock-Demo-2026"
MESSAGE = ("Operation Blue Heron is confirmed for Friday 21:00.\n"
           "Meeting point: north gate of the old library.\n"
           "Bring the signed authorisation form. - FaceLock Stego demo")
COVERS = ["kodak/kodim23.png", "kodak/kodim04.png", "kodak/kodim21.png", "kodak/kodim08.png",
          "sipi/sipi_4_2_03.png", "sipi/sipi_4_2_07.png", "synthetic/syn_text_document.png",
          "synthetic/syn_flat_lowdetail.png"]


def main() -> int:
    (DEMO / "covers").mkdir(parents=True, exist_ok=True)
    for rel in COVERS:
        shutil.copy(ROOT / "dataset" / "covers" / rel, DEMO / "covers" / Path(rel).name)

    pair = DEMO / "pair"
    pair.mkdir(exist_ok=True)
    cover, _ = stego.load_image((ROOT / "dataset/covers/kodak/kodim23.png").read_bytes())
    dek = crypto.random_key()
    res = stego.hide(cover, SecretPayload.from_text(MESSAGE), dek)
    stego_png = stego.to_png_bytes(res.stego_rgb, res.alpha)
    v = vault.create_vault(dek, stego.pixel_fingerprint(res.stego_rgb), crypto.random_key(), [], 0.4, PASSWORD)
    (pair / "demo_stego.png").write_bytes(stego_png)
    (pair / "demo.vault").write_bytes(vault.dumps(v))
    shutil.copy(ROOT / "dataset/covers/kodak/kodim23.png", pair / "demo_cover.png")
    (pair / "info.json").write_text(json.dumps({"password": PASSWORD, "cover": "kodim23.png",
                                                "note": "Password-only demo pair (works on any machine)."}, indent=2))
    print("demo assets written to", DEMO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
