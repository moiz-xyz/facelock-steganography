# FaceLock Stego

**Face-Recognition Protected Image Steganography System**: an Information Security final-year project.

A secret message or file is encrypted with AES-256-GCM, then hidden in the least significant bits of a PNG image at
key-selected **random** pixel positions. The key is **not** stored in the image: it lives in a separate *Face Vault*
(`.vault`) that the server opens only after a **live** face check (blink detection + random challenge) matches an
enrolled person. Up to three people can be authorised, a backup password (Argon2id) is optional, every attempt is
logged with an intruder photo, and three failures lock the vault.

## Run the demo in 3 commands

Requirements: **Python 3.10-3.12**, **Node.js 18+**, a webcam (optional: Demo Mode works without one).

```bash
cd FaceLockStego
bash scripts/setup.sh          # Windows: scripts\setup.bat   (venv, packages, models, frontend build)
bash scripts/run.sh            # Windows: scripts\run.bat     (API :8000 + web app :3000)
```

Then open **http://localhost:3000**. API docs: http://localhost:8000/docs.
If port 3000 is taken, use `FRONT_PORT=3100 bash scripts/run.sh` (the API accepts any localhost port).

## What is in the folder

| Path | Contents |
|---|---|
| `app/backend/` | FastAPI service. `facelock/` holds crypto, LSB, stego container, vault, face engine, liveness, security log, metrics and steganalysis modules; `tests/` holds 56 pytest tests |
| `app/frontend/` | Next.js 14 + TypeScript + Tailwind + Framer Motion + Recharts web app (8 pages) |
| `dataset/` | 41 cover images, 5 payloads, `results.csv` (205 runs) and the other experiment results. See `dataset/README.md` |
| `docs/` | `Proposal.docx/.pdf`, `Report.docx/.pdf` (69 pages), `figures/` (charts, diagrams, real UI screenshots) |
| `presentation/` | `FaceLockStego.pptx` (15 slides, speaker notes on every slide) |
| `scripts/` | setup/run (`.sh` + `.bat`), dataset builder, benchmarks, charts, diagrams, browser E2E test, document and slide generators, `run_all.sh` |
| `project.config.json` | **Your personal details.** Edit once, then run `python scripts/build_docs.py` and `python scripts/build_ppt.py` |

## Pages

Home · **Enroll Face** (guided 5-sample capture) · **Hide Data** (drag-and-drop, live capacity meter, faces + password)
· **Extract Data** (live scan, random challenge, ACCESS GRANTED / DENIED) · **Analysis** (slider, heatmap, bit planes,
PSNR/MSE/SSIM, histograms) · **Security Log** (attempts + intruder photos) · **Attack Lab** (chi-square steganalysis,
sequential vs random LSB) · **How It Works** (animated walkthrough). Toggle **Demo Mode** in the sidebar to preload
sample covers and a password-protected demo pair (password `FaceLock-Demo-2026`).

## Security design (short)

1. `DEK` = 32 random bytes. Message key = HKDF(DEK, salt). The payload is encrypted with AES-256-GCM; the 38-byte header (magic, version, length, salt, nonce) is authenticated as AAD.
2. LSB seed = HKDF(DEK). An AES-CTR keystream ranks every R/G/B slot; the bitstream goes into the top-ranked slots, so positions are secret and spread uniformly.
3. The vault stores the DEK wrapped (AES-GCM) once per authorised face, using a key derived from the **device key** and that face's template, inside a record sealed with the device key. The vault is bound to the SHA-256 of the stego pixels. An optional password slot uses Argon2id (t=3, 64 MiB, p=2).
4. Extraction (server-side, in order): lockout check, image/vault binding, single-use random challenge, liveness (MediaPipe 478-point mesh: eye-aspect-ratio blinks + head-turn ratio), SFace match (cosine ≥ 0.40, configurable), same-face consistency, then key unwrap, LSB read and GCM-verified decryption.

## Measured results (from `dataset/results`)

* 205 image×payload runs on 41 covers: **199/199 that fitted recovered bit-exactly**; 6 oversize runs correctly rejected.
* PSNR **53.96 dB minimum**, 79.8 dB mean at 100 B, 62.4 dB at 10 KB; SSIM ≥ 0.9979.
* Chi-square attack at 50 % payload: **42.4 %** of the image flagged for sequential LSB vs **1.7 %** for keyed random LSB (both detected at 100 %).
* Liveness: **72/72** correct decisions on synthetic faces (all photo attacks rejected). 56 pytest tests and 19 browser E2E checks pass.

Re-create everything with `DEV=1 bash scripts/setup.sh` and then `bash scripts/run_all.sh` (add `UI=1` for the browser test).

## Honest limitations

* **The face check is a server-side policy gate, not a cryptographic binding.** Templates are stored (encrypted with the device key) in the vault. Anyone who has *both* `app/backend/data/device.key` and the vault can unwrap the key without a face. A fuzzy extractor is the proper fix (future work).
* **The vault lives on the owner's device.** Face unlocking works only on the machine that created the vault. The password slot is portable.
* **LSB is fragile.** JPEG, resizing, cropping or filters destroy the payload (it is detected, never silently wrong). Send stego images as files, not through apps that recompress photos.
* **LSB replacement is detectable at high payload** by RS / sample-pair / ML steganalysis, whatever the ordering. Keep payloads well under 50 % of capacity.
* **Liveness is basic.** It stops photos, screens and simple replays, not real-time deepfakes or 3-D masks. It has not been certified (ISO/IEC 30107-3).
* **Face accuracy was measured on synthetic StyleGAN faces**, which validates the pipeline but not real-world FAR/FRR.
* DeepFace is wired in as an automatic fallback, but it is not installed by default (TensorFlow is large). The fallback logic is unit-tested.
* The backend is meant to run locally for one owner: it has no user accounts or TLS.

## Configuration

`FACELOCK_FACE_THRESHOLD` (0.40), `FACELOCK_FACE_ENGINE` (auto|sface|deepface), `FACELOCK_MAX_FAILURES` (3),
`FACELOCK_LOCKOUT_SECONDS` (60), `FACELOCK_DATA_DIR`, `NEXT_PUBLIC_API_URL` (frontend). `app/backend/data/` holds the
device key, encrypted profiles, log and jobs. **Back up `device.key`**: without it face-locked vaults cannot be opened.

## Troubleshooting

* *Camera permission denied*: allow the camera for `localhost`, or use Demo Mode + password.
* *"Backend offline" in the sidebar*: check the API window; first start downloads ~43 MB of models if missing.
* *Liveness keeps failing*: face the light, remove glasses with strong reflections, keep the whole face in the oval, blink clearly and turn about 30°.
* *pip cannot find mediapipe*: use Python 3.10-3.12 (64-bit).
