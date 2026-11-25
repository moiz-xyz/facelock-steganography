"""Generate result charts (PNG, 200 dpi) from dataset/results/*.csv into docs/figures/.

    python scripts/make_charts.py

Every number plotted is read from the benchmark output; nothing is typed in by hand.
Palette: validated categorical slots (blue, orange, aqua) on a white print surface.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "dataset" / "results"
FIG = ROOT / "docs" / "figures"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#b9b8b3", "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 11,
    "axes.titlecolor": INK, "legend.frameon": False, "lines.linewidth": 2, "savefig.dpi": 200,
    "savefig.bbox": "tight", "figure.facecolor": "white",
})


def rows(name: str) -> list[dict]:
    with open(RES / name) as fh:
        return list(csv.DictReader(fh))


def save(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name)
    plt.close(fig)
    print("  ", FIG / name)


PAY_ORDER = ["100B", "1KB", "10KB", "PDF", "50KB"]


def quality_vs_payload() -> None:
    r = [x for x in rows("results.csv") if x["success"] == "True"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for ax, key, label in ((axes[0], "psnr_db", "PSNR (dB)"), (axes[1], "ssim", "SSIM")):
        xs = np.array([float(x["embedded_bytes"]) for x in r])
        ys = np.array([float(x[key]) for x in r])
        ax.scatter(xs, ys, s=14, color=BLUE, alpha=0.45, edgecolors="none", label="one image (41 covers)")
        med = []
        for p in PAY_ORDER:
            sel = [x for x in r if x["payload"] == p]
            med.append((np.median([float(x["embedded_bytes"]) for x in sel]), np.median([float(x[key]) for x in sel])))
        med.sort()
        ax.plot(*zip(*med), color=ORANGE, marker="o", markersize=6, label="median per payload")
        ax.set_xscale("log")
        ax.set_xlabel("Embedded bytes (payload + 54 B header/tag), log scale")
        ax.set_ylabel(label)
        if key == "psnr_db":
            ax.axhline(40, color=INK2, linestyle="--", linewidth=1)
            ax.text(xs.max(), 41.5, "40 dB imperceptibility bound", fontsize=8, color=INK2, ha="right")
            ax.set_title("PSNR falls as payload grows, but stays far above 40 dB")
        else:
            ax.set_title("Structural similarity stays ≈ 1")
            ax.ticklabel_format(axis="y", useOffset=False)
        ax.legend(loc="upper right" if key == "psnr_db" else "lower left", fontsize=8)
    save(fig, "fig_quality_vs_payload.png")


def timing() -> None:
    r = [x for x in rows("results.csv") if x["success"] == "True"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    sel = [x for x in r if x["payload"] == "10KB"]
    mp = np.array([float(x["megapixels"]) for x in sel])
    order = np.argsort(mp)
    for key, col, lab in (("embed_ms", BLUE, "Embed (encrypt + select + write)"), ("extract_ms", ORANGE, "Extract (select + read + decrypt)")):
        axes[0].scatter(mp, [float(x[key]) for x in sel], s=22, color=col, label=lab, edgecolors="none")
    axes[0].set_xlabel("Cover size (megapixels)")
    axes[0].set_ylabel("Time (ms, median of 3)")
    axes[0].set_title("Time grows with image size (10 KB payload)")
    axes[0].legend(fontsize=8)
    kod = [x for x in r if x["resolution"] in ("768x512", "512x768")]
    for key, col, lab in (("embed_ms", BLUE, "Embed"), ("extract_ms", ORANGE, "Extract")):
        pts = sorted((float(np.median([float(x["embedded_bytes"]) for x in kod if x["payload"] == p])),
                      float(np.median([float(x[key]) for x in kod if x["payload"] == p]))) for p in PAY_ORDER)
        axes[1].plot(*zip(*pts), marker="o", markersize=6, color=col, label=lab)
    axes[1].set_xscale("log")
    axes[1].set_xlabel("Embedded bytes, log scale")
    axes[1].set_ylabel("Time (ms, median over 24 Kodak images)")
    axes[1].set_title("Payload size matters little at 768×512")
    axes[1].legend(fontsize=8)
    save(fig, "fig_time_vs_size.png")


def capacity() -> None:
    r = rows("results.csv")
    seen = {}
    for x in r:
        seen[x["resolution"]] = int(x["capacity_bytes"])
    items = sorted(seen.items(), key=lambda kv: kv[1])
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.barh([k for k, _ in items], [v / 1024 for _, v in items], color=BLUE, height=0.6)
    for i, (_, v) in enumerate(items):
        ax.text(v / 1024 + 8, i, f"{v / 1024:,.0f} KB", va="center", fontsize=8, color=INK2)
    ax.set_xlabel("Capacity (KB) at 1 bit per colour channel, minus 54 B overhead")
    ax.set_title("Capacity by cover resolution in the dataset")
    ax.grid(axis="y", visible=False)
    save(fig, "fig_capacity.png")


def steganalysis_curve() -> None:
    c = json.loads((RES / "chi_square_curve_kodim23_50pct.json").read_text())
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for key, col, lab, ls in (("sequential", ORANGE, "Sequential LSB", "-"), ("random", AQUA, "FaceLock keyed-random LSB", "-"),
                              ("cover", BLUE, "Clean cover", "--")):
        ax.plot([p["pct"] for p in c[key]], [p["p"] for p in c[key]], color=col, label=lab, linestyle=ls)
    ax.axvline(50, color=INK2, linestyle=":", linewidth=1)
    ax.text(49, 0.5, "end of sequential payload", fontsize=8, color=INK2, ha="right")
    ax.set_xlabel("Portion of image scanned in raster order (%)")
    ax.set_ylabel("p-value (probability of embedding)")
    ax.set_title("Chi-square attack on kodim23 with a 50 % payload")
    ax.set_ylim(-0.03, 1.05)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3, fontsize=8)
    save(fig, "fig_steganalysis_curve.png")


def steganalysis_bars() -> None:
    r = rows("steganalysis_results.csv")
    fills = ["10", "25", "50", "100"]
    seq = [np.mean([float(x["sequential_flagged_pct"]) for x in r if x["fill_pct"] == f]) for f in fills]
    rnd = [np.mean([float(x["random_flagged_pct"]) for x in r if x["fill_pct"] == f]) for f in fills]
    x = np.arange(len(fills))
    fig, ax = plt.subplots(figsize=(8, 3.8))
    b1 = ax.bar(x - 0.19, seq, 0.36, color=ORANGE, label="Sequential LSB")
    b2 = ax.bar(x + 0.19, rnd, 0.36, color=AQUA, label="FaceLock keyed-random LSB")
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, f"{b.get_height():.1f}", ha="center", fontsize=8, color=INK2)
    ax.set_xticks(x, [f"{f}% of capacity" for f in fills])
    ax.set_ylabel("Image flagged as stego (%), mean of 41")
    ax.set_title("Chi-square detection across the whole dataset")
    ax.legend(fontsize=8)
    ax.grid(axis="x", visible=False)
    save(fig, "fig_steganalysis_fill.png")


def face() -> None:
    r = rows("face_similarity.csv")
    gen = [float(x["cosine_similarity"]) for x in r if x["genuine"] == "True"]
    imp = [float(x["cosine_similarity"]) for x in r if x["genuine"] == "False"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    bins = np.linspace(-0.1, 1.0, 45)
    axes[0].hist(imp, bins=bins, color=BLUE, label=f"Impostor pairs (n={len(imp)})")
    axes[0].hist(gen, bins=bins, color=ORANGE, label=f"Genuine pairs (n={len(gen)})")
    axes[0].axvline(0.40, color=INK, linestyle="--", linewidth=1)
    axes[0].text(0.42, axes[0].get_ylim()[1] * 0.45, "threshold 0.40", fontsize=8)
    axes[0].set_xlabel("Cosine similarity (SFace)")
    axes[0].set_ylabel("Count")
    axes[0].set_title("Score distributions (synthetic faces)")
    axes[0].legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2)
    t = rows("face_far_frr.csv")
    th = [float(x["threshold"]) for x in t]
    axes[1].plot(th, [float(x["FAR_pct"]) for x in t], color=BLUE, marker="o", markersize=4, label="FAR (impostor accepted)")
    axes[1].plot(th, [float(x["FRR_pct"]) for x in t], color=ORANGE, marker="o", markersize=4, label="FRR (genuine rejected)")
    axes[1].axvline(0.40, color=INK, linestyle="--", linewidth=1)
    axes[1].set_xlabel("Decision threshold")
    axes[1].set_ylabel("Error rate (%)")
    axes[1].set_title("FAR / FRR vs threshold")
    axes[1].legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2)
    save(fig, "fig_face_far_frr.png")


def liveness_traces() -> None:
    sys.path.insert(0, str(ROOT / "app" / "backend"))
    os.environ.setdefault("GLOG_minloglevel", "2")
    from facelock.liveness import LandmarkAnalyzer, evaluate
    from tests import synth
    la = LandmarkAnalyzer(ROOT / "app/backend/models")
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for ax, frames, ch, title in ((axes[0], synth.live_burst(1, "turn_left", n=50, seed=1), "turn_left", "Live user: challenge 'turn left'"),
                                  (axes[1], synth.photo_burst(1, n=50, seed=1), "turn_left", "Photo attack: same face, static")):
        obs = [la.observe(f) for f in frames]
        r = evaluate(obs, ch)
        t = np.arange(len(obs)) / 10
        ax.plot(t, [o.ear for o in obs], color=BLUE, label="Eye aspect ratio (EAR)")
        ax.plot(t, [o.yaw for o in obs], color=ORANGE, label="Nose position ratio (yaw)")
        ax.axhline(r.ear_baseline * 0.62, color=INK2, linestyle="--", linewidth=1)
        ax.set_title(f"{title}\nserver result: {'PASS' if r.passed else 'FAIL'}" + ("" if r.passed else " (no motion: static image)"), fontsize=9)
        ax.set_xlabel("Time (s) at 10 frames/s")
        ax.set_ylim(0, 1)
    axes[0].set_ylabel("Signal value")
    axes[0].legend(fontsize=8, loc="upper center", bbox_to_anchor=(1.05, -0.17), ncol=2)
    save(fig, "fig_liveness_traces.png")


if __name__ == "__main__":
    for fn in (quality_vs_payload, timing, capacity, steganalysis_curve, steganalysis_bars, face, liveness_traces):
        fn()
