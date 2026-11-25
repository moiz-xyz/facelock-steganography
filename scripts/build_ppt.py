"""Build presentation/FaceLockStego.pptx from real results.

    python scripts/build_ppt.py

Exports the numbers the slides need (from dataset/results) to JSON, then runs
scripts/doctools/build_ppt.js (pptxgenjs).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "docgen"))
from common import ROOT, TOOLS, cfg, facts  # noqa: E402


def main() -> int:
    F = facts()
    P, S = F["pay"], F["stega"]
    data = {
        "cfg": cfg(),
        "images": F["images"], "runs": F["runs"], "ok_runs": F["ok_runs"], "cap_fail": len(F["cap_fail"]),
        "by_source": F["by_source"],
        "psnr": [{"payload": p, "mean": round(P[p]["psnr_mean"], 2), "min": round(P[p]["psnr_min"], 2),
                  "ssim": round(P[p]["ssim_mean"], 5)} for p in ("100B", "1KB", "10KB", "PDF", "50KB")],
        "min_psnr": round(F["min_psnr_all"], 2), "min_ssim": round(F["min_ssim_all"], 4),
        "stega": [{"fill": f"{k}%", "seq": round(S[k]["seq"], 1), "rnd": round(S[k]["rnd"], 1)} for k in ("10", "25", "50", "100")],
        "kodak10_embed": round(F["kodak10_embed"], 1), "kodak10_extract": round(F["kodak10_extract"], 1),
        "live": F["live_summary"], "face": F["face"], "tests": F["pytest"]["tests"], "ui": len(F["ui"]),
        "ui_ok": sum(1 for x in F["ui"] if x["passed"]),
        "root": str(ROOT),
    }
    out = ROOT / "presentation"
    out.mkdir(exist_ok=True)
    jp = TOOLS / "ppt_data.json"
    jp.write_text(json.dumps(data, indent=2))
    subprocess.run(["node", str(TOOLS / "build_ppt.js"), str(jp), str(out / "FaceLockStego.pptx")], check=True, cwd=TOOLS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
