"""Content of the project proposal (docs/Proposal.docx + .pdf), 5-8 pages."""
from __future__ import annotations

from common import DIAG, Doc, cfg
from report import REFS, R


def cite(*k):
    return "[" + "], [".join(str(R[x]) for x in k) + "]"


PROPOSAL_REFS = ["johnson", "cheddad", "chan", "chisq", "f5", "dwt", "sface", "yunet", "mediapipe", "ear", "fuzzyext", "gcm", "argon2", "ssim", "kodak", "sipi"]


def build_proposal() -> Doc:
    C = cfg()
    d = Doc()
    # renumber references locally (only those cited in the proposal)
    local = {k: i + 1 for i, k in enumerate(PROPOSAL_REFS)}

    def c(*k):
        return "[" + "], [".join(str(local[x]) for x in k) + "]"

    d.section("none")
    d.add(t="spacer", n=2)
    d.add(t="center", text=C["university"].upper(), size=16, bold=True)
    d.add(t="center", text=C["department"], size=13)
    d.add(t="spacer", n=3)
    d.add(t="center", text="PROJECT PROPOSAL", size=13, bold=True, color="555555")
    d.add(t="spacer", n=1)
    d.add(t="center", text=C["project_title"], size=28, bold=True, color="1F2A44")
    d.add(t="center", text=C["project_subtitle"], size=15, italic=True)
    d.add(t="spacer", n=3)
    d.add(t="center", text=f'Submitted by: {C["student_name"]} ({C["roll_no"]})', size=13, bold=True)
    d.add(t="center", text=f'Supervisor: {C["supervisor"]}', size=13)
    d.add(t="center", text=C["course"], size=12)
    d.add(t="spacer", n=3)
    d.add(t="center", text=C["submission_date"], size=12)

    d.section("decimal")
    d.add(t="h", level=1, text="Abstract")
    d.p("This proposal describes FaceLock Stego, a system that hides encrypted messages and files inside ordinary PNG images and "
        "allows only a registered person, verified live in front of a webcam, to extract them. The secret is encrypted with "
        "AES-256-GCM using a random key and embedded with least-significant-bit (LSB) substitution at key-selected random "
        "pixel positions. The key is not stored in the image but in a separate Face Vault that the server opens only after a "
        "face match and a liveness check (eye blinks plus a random head-movement challenge). The project will deliver a "
        "working web application, a documented image dataset with benchmark results, a report and a presentation.")
    d.add(t="h", level=1, text="1. Introduction")
    d.p(f"Steganography conceals the very existence of a message inside a cover medium {c('johnson', 'cheddad')}. LSB substitution in "
        f"lossless images is simple and offers high capacity with imperceptible distortion {c('chan')}, but naive sequential "
        f"embedding is easily detected by statistical attacks such as the chi-square test {c('chisq')}, and once detected an "
        "unencrypted payload can be read. Encrypting first solves confidentiality but introduces a key that can be shared or "
        "stolen. Face biometrics can bind access to a physical person instead of a password.")
    d.add(t="h", level=1, text="2. Problem Statement")
    d.p("Common steganography tools embed sequentially, often without encryption, and protect secrets with a single reusable "
        "password. They provide no proof that the person extracting the data is the intended recipient, no protection against "
        "repeated guessing, and no audit trail. The problem is to design a system in which a secret hidden in an image can be "
        "recovered only by an authorised person who is physically present, while the image remains visually unchanged and "
        "statistically hard to flag.")
    d.add(t="h", level=1, text="3. Objectives")
    d.numbers(["Implement encrypted LSB steganography with key-based random pixel selection and an authenticated header.",
               "Keep the AES-256 key out of the image, in a Face Vault opened only after server-side face verification.",
               "Detect liveness with the eye aspect ratio and a random challenge so that photos are rejected.",
               "Support up to three authorised faces, a hashed backup password, intruder capture and lockout.",
               "Build a polished web application with analysis and steganalysis dashboards and a demo mode.",
               "Evaluate capacity, PSNR, MSE, SSIM, speed, robustness and detectability on a public dataset."], ref="pobj")
    d.add(t="h", level=1, text="4. Scope")
    d.bullets(["**Included:** PNG output, text and file payloads, webcam enrolment and verification, local deployment on the owner's device, Windows/macOS/Linux support.",
               "**Excluded:** JPEG-robust embedding, mobile apps, cloud key escrow, certified anti-spoofing."])
    d.add(t="h", level=1, text="5. Literature Review Summary")
    d.table("Summary of related techniques", ["Area", "Representative work", "Relevance"],
            [["Spatial LSB", f"Chan and Cheng {c('chan')}", "High capacity, simple; chosen embedding"],
             ["Transform domain", f"F5 (DCT) {c('f5')}, DWT {c('dwt')}", "Robust to compression; future work"],
             ["Steganalysis", f"Chi-square attack {c('chisq')}", "Evaluation of detectability"],
             ["Face recognition", f"SFace {c('sface')}, YuNet {c('yunet')}", "CPU-friendly, installs without compilers"],
             ["Liveness", f"EAR blink detection {c('ear')}, MediaPipe mesh {c('mediapipe')}", "Anti-spoofing"],
             ["Key binding", f"Fuzzy extractors {c('fuzzyext')}", "Stronger biometric key binding (future)"],
             ["Cryptography", f"AES-GCM {c('gcm')}, Argon2 {c('argon2')}", "Confidentiality, integrity, password hashing"]],
            widths=[1.3, 2.4, 2.2], small=True)
    d.add(t="h", level=1, text="6. Proposed Methodology")
    d.numbers(["**Enrolment:** capture five webcam samples, compute SFace embeddings, average them and store the template encrypted with a device key.",
               "**Hiding:** generate a random data key (DEK); encrypt the payload with AES-256-GCM; derive a seed from the DEK to rank all colour-channel slots with an AES-CTR keystream; write a 38-byte header (length, salt, nonce) and the ciphertext into the LSBs of the top-ranked slots; save as PNG.",
               "**Vault:** wrap the DEK once per authorised face and optionally under an Argon2id-derived password key; bind the vault to a SHA-256 hash of the stego pixels.",
               "**Extraction:** the server checks lockout and binding, issues a random challenge, analyses about 50 frames for blinks and head movement, matches the face by cosine similarity, unwraps the DEK, reads the random LSBs and decrypts.",
               f"**Evaluation:** benchmark every image×payload pair for PSNR, MSE, SSIM {c('ssim')} and time; run the chi-square attack on sequential vs random embedding; test spoofing and lockout scenarios."],
              ref="meth")
    d.add(t="h", level=1, text="7. System Architecture")
    d.figure(DIAG / "fig_architecture.png", "Proposed system architecture", width=6.0)
    d.add(t="h", level=1, text="8. Tools and Technologies")
    d.table("Tools and technologies", ["Purpose", "Tool"],
            [["Backend", "Python 3.12, FastAPI, Uvicorn"], ["Cryptography", "cryptography (AES-GCM, HKDF), argon2-cffi"],
             ["Image processing", "NumPy, Pillow, OpenCV, scikit-image"], ["Face and liveness", "OpenCV YuNet + SFace, MediaPipe Face Landmarker"],
             ["Frontend", "Next.js, TypeScript, Tailwind CSS, Framer Motion, Recharts"], ["Storage", "SQLite, encrypted files"],
             ["Testing", "pytest, Playwright (Chrome)"], ["Dataset", f"Kodak {c('kodak')}, USC-SIPI {c('sipi')}, synthetic images"]],
            widths=[1.6, 4.2], small=True)
    d.add(t="h", level=1, text="9. Expected Outcomes")
    d.bullets(["A working, demonstrable web application covering enrolment, hiding, extraction, analysis, logging and an attack lab.",
               "Stego images with PSNR above 50 dB and SSIM above 0.99 for typical payloads.",
               "Measurably lower chi-square detectability for random than for sequential embedding at moderate payloads.",
               "Rejection of photo attacks and impostors, with lockout after three failures.",
               "A dataset of 30+ images with a benchmark CSV, charts, a full report and a presentation."])
    d.add(t="h", level=1, text="10. Timeline")
    weeks = ["W1", "W2", "W3", "W4", "W5", "W6", "W7"]
    plan = [("Literature review, requirements, design", [1, 1, 0, 0, 0, 0, 0]),
            ("Crypto, LSB, vault modules + unit tests", [0, 1, 1, 0, 0, 0, 0]),
            ("Face recognition and liveness", [0, 0, 1, 1, 0, 0, 0]),
            ("Web application (8 pages)", [0, 0, 0, 1, 1, 0, 0]),
            ("Integration and end-to-end testing", [0, 0, 0, 0, 1, 1, 0]),
            ("Dataset, benchmarks, charts", [0, 0, 0, 0, 0, 1, 0]),
            ("Report, presentation, demo rehearsal", [0, 0, 0, 0, 0, 1, 1])]
    d.table("Seven-week Gantt chart (■ = active week)", ["Activity"] + weeks,
            [[a] + ["■■" if w else "" for w in ws] for a, ws in plan],
            widths=[2.8] + [0.45] * 7, align=["l"] + ["c"] * 7, small=True)
    d.add(t="h", level=1, text="11. Risks and Mitigation")
    d.table("Risks and mitigation", ["Risk", "Impact", "Mitigation"],
            [["Face library fails to install on Windows (dlib)", "High", "Use OpenCV SFace (pre-built wheels) with automatic DeepFace fallback"],
             ["Webcam unavailable during viva", "High", "Demo mode with preloaded pair and backup password"],
             ["Liveness too strict / too lenient", "Medium", "Adaptive EAR threshold, configurable parameters, tests with synthetic bursts"],
             ["Stego image recompressed by apps", "Medium", "PNG-only output, warnings, integrity check detects damage"],
             ["Privacy of test faces", "Medium", "Use GAN-generated faces of non-existent people; no real faces in the repository"],
             ["Schedule slip", "Medium", "Weekly milestones; core security first, UI polish later"]],
            widths=[2.2, 0.8, 2.8], small=True)
    d.add(t="h", level=1, text="References")
    for i, k in enumerate(PROPOSAL_REFS, 1):
        d.add(t="p", text=f"[{i}]  {REFS[R[k] - 1]}", align="left", line=276, after=80)
    return d
