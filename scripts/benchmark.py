"""Run every FaceLock Stego experiment and write CSV results to dataset/results/.

    python scripts/benchmark.py            # all experiments
    python scripts/benchmark.py --only stego

Experiments
-----------
stego         every cover image x every payload -> results.csv (also copied to dataset/results.csv)
steganalysis  chi-square attack, sequential vs keyed-random LSB at 10/25/50/100% payload
robustness    what survives (lossless re-save) and what breaks (JPEG, resize, crop, bit flip)
face          genuine vs impostor similarity on the synthetic faces -> FAR/FRR by threshold
liveness      every challenge, wrong responses and photo attacks on the synthetic faces

Notes: the stego benchmark embeds payloads *uncompressed* so that payload size
maps directly to embedded bits (the app compresses text when it helps). Times
are the median of 3 runs on this machine (see machine.json).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app" / "backend"))
os.environ.setdefault("GLOG_minloglevel", "2")

from facelock import crypto, lsb, metrics, stego, steganalysis  # noqa: E402
from facelock.payload import SecretPayload  # noqa: E402

DS = ROOT / "dataset"
OUT = DS / "results"
PAYLOADS = [("100B", "payload_100B.txt"), ("1KB", "payload_1KB.txt"), ("10KB", "payload_10KB.txt"),
            ("50KB", "payload_50KB.txt"), ("PDF", "sample_memo.pdf")]


def covers() -> list[dict]:
    with open(DS / "manifest.csv") as fh:
        return list(csv.DictReader(fh))


def load(rel: str) -> np.ndarray:
    return np.asarray(Image.open(DS / rel).convert("RGB"), dtype=np.uint8)


def write_csv(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {OUT / name} ({len(rows)} rows)")


# --------------------------------------------------------------------------- stego
def exp_stego() -> None:
    rows = []
    for c in covers():
        img = load(c["file"])
        cap = stego.payload_capacity(img.shape)
        for label, fname in PAYLOADS:
            data = (DS / "payloads" / fname).read_bytes()
            p = SecretPayload.from_file(fname, data, "application/pdf" if fname.endswith(".pdf") else "text/plain")
            row = {"image": Path(c["file"]).name, "source": c["source"].split(" (")[0], "category": c["category"],
                   "width": img.shape[1], "height": img.shape[0], "resolution": f"{img.shape[1]}x{img.shape[0]}",
                   "megapixels": round(img.shape[0] * img.shape[1] / 1e6, 3), "payload": label,
                   "payload_bytes": len(data), "capacity_bytes": cap}
            embed_t, extract_t, ok, note, res, dek = [], [], False, "", None, None
            try:
                for _ in range(3):
                    dek = crypto.random_key()
                    t0 = time.perf_counter()
                    res = stego.hide(img, p, dek, compress=False)
                    embed_t.append(time.perf_counter() - t0)
                    png = stego.to_png_bytes(res.stego_rgb)            # real file round trip
                    arr, _ = stego.load_image(png, 10**9)
                    t0 = time.perf_counter()
                    out = stego.reveal(arr, dek)
                    extract_t.append(time.perf_counter() - t0)
                    ok = out.data == data
                q = metrics.quality(img, res.stego_rgb)
                row.update(embedded_bytes=res.embedded_bytes,
                           utilization_pct=round(100 * res.embedded_bytes / lsb.capacity_bytes(img.shape), 3),
                           embed_ms=round(1000 * statistics.median(embed_t), 2),
                           extract_ms=round(1000 * statistics.median(extract_t), 2),
                           psnr_db=q["psnr"], mse=q["mse"], ssim=q["ssim"],
                           changed_pixels_pct=round(100 * q["changed_pixels"] / q["total_pixels"], 3),
                           png_bytes=len(png), success=ok, note="")
            except lsb.CapacityError:
                row.update(embedded_bytes=len(data) + stego.OVERHEAD + 14, utilization_pct="", embed_ms="",
                           extract_ms="", psnr_db="", mse="", ssim="", changed_pixels_pct="", png_bytes="",
                           success=False, note="payload exceeds capacity")
            rows.append(row)
        print(f"  {c['file']:48s} done")
    write_csv("results.csv", rows)
    (DS / "results.csv").write_text((OUT / "results.csv").read_text())


# ------------------------------------------------------------------- steganalysis
def exp_steganalysis() -> None:
    rows = []
    for c in covers():
        img = load(c["file"])
        clean = steganalysis.detection_summary(steganalysis.prefix_scan(img))
        n = lsb.capacity_bytes(img.shape)
        for fill in (0.10, 0.25, 0.50, 1.00):
            data = np.random.default_rng(7).integers(0, 256, int(n * fill), dtype=np.uint8).tobytes()
            seq = steganalysis.detection_summary(steganalysis.prefix_scan(lsb.embed_bytes(img, data, None)))
            rnd = steganalysis.detection_summary(
                steganalysis.prefix_scan(lsb.embed_bytes(img, data, crypto.random_key())))
            rows.append({"image": Path(c["file"]).name, "category": c["category"], "fill_pct": int(fill * 100),
                         "clean_flagged_pct": clean["flagged_prefix_pct"], "clean_mean_p": clean["mean_p"],
                         "sequential_flagged_pct": seq["flagged_prefix_pct"], "sequential_mean_p": seq["mean_p"],
                         "random_flagged_pct": rnd["flagged_prefix_pct"], "random_mean_p": rnd["mean_p"],
                         "random_any_flag": rnd["flagged_any"]})
    write_csv("steganalysis_results.csv", rows)
    # one full curve for the figure
    img = load("covers/kodak/kodim23.png")
    data = np.random.default_rng(7).integers(0, 256, lsb.capacity_bytes(img.shape) // 2, dtype=np.uint8).tobytes()
    curves = {"cover": steganalysis.prefix_scan(img),
              "sequential": steganalysis.prefix_scan(lsb.embed_bytes(img, data, None)),
              "random": steganalysis.prefix_scan(lsb.embed_bytes(img, data, crypto.random_key()))}
    (OUT / "chi_square_curve_kodim23_50pct.json").write_text(json.dumps(curves))


# ---------------------------------------------------------------------- robustness
def exp_robustness() -> None:
    def jpeg(a, q):
        b = io.BytesIO(); Image.fromarray(a).save(b, "JPEG", quality=q); return np.asarray(Image.open(b))

    def flip(a):
        b = a.copy(); b.reshape(-1)[b.size // 2] ^= 1; return b

    attacks = {
        "none (original PNG)": lambda a: a,
        "lossless re-save (PNG, max compression)": lambda a: np.asarray(Image.open(io.BytesIO(
            stego.to_png_bytes(a))).convert("RGB")),
        "convert to BMP and back": lambda a: np.asarray(Image.open(io.BytesIO(_save(a, "BMP")))),
        "JPEG quality 95": lambda a: jpeg(a, 95),
        "JPEG quality 75": lambda a: jpeg(a, 75),
        "resize 99% and back": lambda a: np.asarray(Image.fromarray(a).resize(
            (int(a.shape[1] * .99), int(a.shape[0] * .99))).resize((a.shape[1], a.shape[0]))),
        "crop 1 pixel row": lambda a: np.ascontiguousarray(a[1:]),
        "one LSB flip at an arbitrary pixel (centre)": flip,
        "brightness +1": lambda a: np.clip(a.astype(int) + 1, 0, 255).astype(np.uint8),
    }
    rows = []
    for rel in ("covers/kodak/kodim23.png", "covers/kodak/kodim04.png", "covers/sipi/sipi_4_2_03.png",
                "covers/synthetic/syn_text_document.png", "covers/synthetic/syn_flat_lowdetail.png"):
        img = load(rel)
        dek = crypto.random_key()
        st = stego.hide(img, SecretPayload.from_file("p.txt", (DS / "payloads/payload_10KB.txt").read_bytes(), None),
                        dek).stego_rgb
        pos = lsb.keyed_positions(stego.lsb_seed(dek), lsb.slot_count(st.shape), 400 * 8)
        def flip_payload(a, p=int(pos[-1])):
            b = a.copy(); b.reshape(-1)[p] ^= 1; return b
        attacks["one LSB flip on a payload bit (targeted)"] = flip_payload
        for name, fn in attacks.items():
            try:
                stego.reveal(fn(st), dek)
                ok, err = True, ""
            except Exception as exc:  # noqa: BLE001
                ok, err = False, str(exc)[:80]
            rows.append({"image": Path(rel).name, "operation": name, "extracted": ok, "error": err})
    write_csv("robustness_results.csv", rows)


def _save(a, fmt):
    b = io.BytesIO(); Image.fromarray(a).save(b, fmt); return b.getvalue()


# ---------------------------------------------------------------------------- face
def exp_face() -> None:
    from facelock.face_engine import FaceEngine, cosine, l2n
    from tests import synth
    eng = FaceEngine(ROOT / "app/backend/models")
    ids = range(1, 9)
    templates = {i: l2n(np.mean([eng.single_face_embedding(s)[0] for s in synth.enrollment_samples(i)], 0)) for i in ids}
    rows, t_emb = [], []
    for probe in ids:
        for k, ch in enumerate(("blink_twice", "turn_left", "turn_right")):
            frames = synth.live_burst(probe, ch, n=40, seed=100 + 10 * probe + k)
            pick = frames[:6] + frames[34:40]             # frontal frames, as the server selects
            t0 = time.perf_counter()
            live = l2n(np.mean([eng.single_face_embedding(f)[0] for f in pick], 0))
            t_emb.append((time.perf_counter() - t0) / len(pick))
            for enrolled in ids:
                rows.append({"probe_face": f"gan_{probe}", "probe_session": ch, "enrolled_face": f"gan_{enrolled}",
                             "genuine": probe == enrolled, "cosine_similarity": round(cosine(live, templates[enrolled]), 4)})
    write_csv("face_similarity.csv", rows)
    gen = np.array([r["cosine_similarity"] for r in rows if r["genuine"]])
    imp = np.array([r["cosine_similarity"] for r in rows if not r["genuine"]])
    thr_rows = []
    for t in np.round(np.arange(0.20, 0.96, 0.05), 2):
        thr_rows.append({"threshold": t, "FAR_pct": round(100 * (imp >= t).mean(), 2),
                         "FRR_pct": round(100 * (gen < t).mean(), 2), "genuine_trials": len(gen),
                         "impostor_trials": len(imp)})
    write_csv("face_far_frr.csv", thr_rows)
    (OUT / "face_summary.json").write_text(json.dumps({
        "genuine_mean": round(float(gen.mean()), 4), "genuine_min": round(float(gen.min()), 4),
        "impostor_mean": round(float(imp.mean()), 4), "impostor_max": round(float(imp.max()), 4),
        "embedding_ms_per_frame": round(1000 * float(np.median(t_emb)), 2),
        "genuine_trials": int(len(gen)), "impostor_trials": int(len(imp)), "engine": eng.name}, indent=2))


# ------------------------------------------------------------------------ liveness
def exp_liveness() -> None:
    from facelock.liveness import LandmarkAnalyzer, evaluate
    from tests import synth
    la = LandmarkAnalyzer(ROOT / "app/backend/models")
    rows, t_frame = [], []

    def run(face, scenario, challenge, frames, expect_pass):
        t0 = time.perf_counter()
        obs = [la.observe(f) for f in frames]
        t_frame.append((time.perf_counter() - t0) / len(frames))
        r = evaluate(obs, challenge)
        rows.append({"face": f"gan_{face}", "scenario": scenario, "challenge": challenge, "expected": "pass" if expect_pass else "fail",
                     "result": "pass" if r.passed else "fail", "correct": r.passed == expect_pass, "blinks": r.blinks,
                     "turn_peak": round(r.turn_peak, 4), "reason": r.reason})

    for f in range(1, 9):
        for ch in ("blink_twice", "turn_left", "turn_right"):
            run(f, "live user, correct response", ch, synth.live_burst(f, ch, n=50, seed=f), True)
        run(f, "live user, wrong direction", "turn_right", synth.live_burst(f, "turn_left", n=50, seed=f), False)
        run(f, "live user, wrong direction", "turn_left", synth.live_burst(f, "turn_right", n=50, seed=f), False)
        run(f, "live user, one blink only", "blink_twice", synth.live_burst(f, "turn_left", n=50, seed=f)[:12]
            + [synth.face(f)] * 38, False)
        for ch in ("blink_twice", "turn_left", "turn_right"):
            run(f, "printed/phone photo (static)", ch, synth.photo_burst(f, n=50, seed=f), False)
    write_csv("liveness_results.csv", rows)
    (OUT / "liveness_summary.json").write_text(json.dumps({
        "trials": len(rows), "correct": sum(r["correct"] for r in rows),
        "landmark_ms_per_frame": round(1000 * float(np.median(t_frame)), 2)}, indent=2))


def machine_info() -> None:
    import cv2, mediapipe  # noqa: E401
    info = {"platform": platform.platform(), "python": platform.python_version(), "processor": platform.processor(),
            "cpu_count": os.cpu_count(), "numpy": np.__version__, "opencv": cv2.__version__,
            "mediapipe": mediapipe.__version__, "date": time.strftime("%Y-%m-%d")}
    try:
        info["cpu_model"] = next(l.split(":")[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name"))
    except (OSError, StopIteration):
        pass
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "machine.json").write_text(json.dumps(info, indent=2))


EXPS = {"stego": exp_stego, "steganalysis": exp_steganalysis, "robustness": exp_robustness,
        "face": exp_face, "liveness": exp_liveness}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(EXPS))
    a = ap.parse_args()
    machine_info()
    for name, fn in EXPS.items():
        if a.only and name != a.only:
            continue
        print(f"[{name}]")
        t0 = time.time()
        fn()
        print(f"  {time.time() - t0:.1f}s")
