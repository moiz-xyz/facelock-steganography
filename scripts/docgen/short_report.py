"""Short project report (~15 pages): docs/Report.docx + .pdf.

Same real data as the full report (docs/Report_Full.*), condensed to the essentials.
"""
from __future__ import annotations

from common import DIAG, FIG, SHOT, Doc, cfg
from report import REFS, R, f1, f2

SHORT_REFS = ["johnson", "cheddad", "chan", "f5", "dwt", "chisq", "rs", "sface", "yunet", "mediapipe", "ear",
              "fuzzyext", "gcm", "hkdf", "argon2", "ssim", "kodak", "sipi"]
L = {k: i + 1 for i, k in enumerate(SHORT_REFS)}


def c(*k) -> str:
    return "[" + "], [".join(str(L[x]) for x in k) + "]"


def build_short_report(F: dict) -> Doc:
    C = cfg()
    d = Doc()
    P, S, pt = F["pay"], F["stega"], F["pytest"]
    lv = F["live_summary"]
    members = C.get("group_members") or [{"name": C["student_name"], "roll_no": C["roll_no"]}]

    # ---------------------------------------------------------------- cover
    d.section("none")
    d.add(t="spacer", n=3)
    d.add(t="center", text="PROJECT REPORT", size=13, bold=True, color="555555")
    d.add(t="spacer", n=1)
    d.add(t="center", text=C["project_title"], size=28, bold=True, color="1F2A44")
    d.add(t="center", text=C["project_subtitle"], size=15, italic=True)
    d.add(t="spacer", n=1)
    d.add(t="center", text="Information Security", size=12)
    d.add(t="spacer", n=3)
    d.add(t="center", text="GROUP MEMBERS", size=12, bold=True, color="555555")
    for m in members:
        d.add(t="center", text=f'{m["name"]}   ({m["roll_no"]})', size=14, bold=True, after=60)
    d.add(t="spacer", n=4)
    d.add(t="center", text=C["submission_date"], size=12)

    # ------------------------------------------------------------- abstract
    d.section("roman")
    d.front_heading("Abstract")
    d.p("FaceLock Stego hides a secret text or file inside an ordinary PNG image so that only a registered person, verified "
        "live in front of a webcam, can recover it. The secret is encrypted with AES-256-GCM under a random key and embedded "
        "in the least significant bits (LSB) of the image at pseudo-random positions derived from that key. The key is never "
        "stored in the image: it is kept in a separate Face Vault file that the server opens only after a liveness check "
        "(eye blinks and a random head-turn or double-blink challenge, using MediaPipe face landmarks) and a face match "
        "(OpenCV SFace embeddings). Failed attempts are logged with an intruder photo and three failures lock the vault; an "
        "optional Argon2id-protected backup password is supported.")
    d.p(f'On {F["images"]} cover images and five payloads, all {F["ok_runs"]} embeddings that fitted were recovered exactly. '
        f'PSNR never fell below {f2(F["min_psnr_all"])} dB and SSIM never below {F["min_ssim_all"]:.4f}. At 50 % payload the '
        f'chi-square attack flagged {f1(S["50"]["seq"])} % of the image for sequential LSB but only {f1(S["50"]["rnd"])} % for our '
        f'random LSB. Liveness made {lv["correct"]}/{lv["trials"]} correct decisions on synthetic faces, rejecting every photo '
        f'attack, and {pt["tests"]} automated tests plus {len(F["ui"])} browser checks pass.')
    d.p("**Keywords:** steganography, LSB, AES-GCM, face recognition, liveness detection, steganalysis.", align="left")
    toc_pos = len(d.sections[-1]["blocks"])

    # ------------------------------------------------------------ chapter 1
    d.section("decimal")
    d.chapter_heading("Introduction")
    d.p(f"Cryptography hides the meaning of a message; steganography hides its existence {c('johnson', 'cheddad')}. The "
        f"simplest image method, LSB substitution {c('chan')}, changes each colour value by at most one level, which the eye "
        f"cannot see. However, naive LSB is easy to detect statistically {c('chisq', 'rs')}, and whoever holds the password or "
        "key can read the secret. Face biometrics tie access to a person who is physically present.")
    d.h2("1.1", "Problem Statement")
    d.p("Typical tools embed sequentially from the first pixel, often without encryption, protect the secret with a single "
        "shareable password, and keep no record of failed attempts. The problem is to hide a secret in an image so that only "
        "an authorised, live person can recover it, while the image stays visually unchanged and statistically hard to flag.")
    d.h2("1.2", "Objectives")
    d.numbers(["Hide AES-256-GCM-encrypted data in PNG images using LSB at key-selected random positions.",
               "Keep the key out of the image, in a Face Vault opened only after server-side verification.",
               "Verify liveness (blinks + random challenge) and identity (face match) on the server.",
               "Support up to three authorised faces, a backup password, intruder photos and lockout.",
               "Build a web application and measure quality, speed and detectability on a real dataset."], ref="sobj")

    # ------------------------------------------------------------ chapter 2
    d.chapter_heading("Literature Review")
    d.p(f"Spatial-domain methods such as LSB modify pixel values directly and offer the highest capacity {c('chan')}. Transform "
        f"methods embed in DCT coefficients (e.g. F5 {c('f5')}) or wavelet sub-bands {c('dwt')}; they survive compression but "
        f"carry less. The chi-square attack {c('chisq')} detects LSB replacement because it equalises the counts of value pairs "
        f"(2i, 2i+1); RS analysis {c('rs')} estimates the payload. Modern face recognition maps a face to an embedding vector: "
        f"SFace {c('sface')} with the YuNet detector {c('yunet')} runs on a CPU without compilers. Liveness can be checked with "
        f"the eye aspect ratio (EAR) {c('ear')} computed from MediaPipe landmarks {c('mediapipe')}. Fuzzy extractors "
        f"{c('fuzzyext')} can bind a key to a noisy biometric and are left as future work.")
    d.table("Comparison of image steganography techniques", ["Technique", "Capacity", "Survives JPEG", "Detectability", "Complexity"],
            [["Sequential LSB", "Very high", "No", "High", "Very low"], ["Random-order LSB (ours)", "Very high", "No", "Low below 50 % load", "Low"],
             ["DCT (F5, OutGuess)", "Low-medium", "Yes", "Medium", "Medium"], ["DWT", "Medium", "Partly", "Medium", "Medium-high"]],
            widths=[1.8, 1.1, 1.1, 1.5, 1.1], small=True)

    # ------------------------------------------------------------ chapter 3
    d.chapter_heading("System Design")
    d.p(f"{d.next_fig()} shows the architecture. The browser only captures files and camera frames; every security decision "
        "is made by the FastAPI backend, which calls separate modules for cryptography, LSB embedding, the vault, face "
        "recognition, liveness and the security log.")
    d.figure(DIAG / "fig_architecture.png", "System architecture", width=6.0)
    d.h2("3.1", "Hiding")
    d.numbers(["Generate a random 256-bit data key (DEK) and encrypt the payload with AES-256-GCM.",
               "Derive a seed from the DEK; an AES-CTR keystream ranks every R, G and B value of the image.",
               "Write a 38-byte header (length, salt, nonce) and the ciphertext into the LSBs of the top-ranked values; save as PNG.",
               "Create the .vault: wrap the DEK once per authorised face (keys derived from the device key and the face "
               "template) and optionally under an Argon2id password key; bind the vault to the SHA-256 of the stego pixels."], ref="shide")
    d.figure(DIAG / "fig_vault_design.png", "Key hierarchy of the Face Vault", width=6.0)
    d.h2("3.2", "Extraction and Face Verification")
    d.numbers(["Check that the vault is not locked and that the image belongs to the vault.",
               "Issue a random, single-use challenge: blink twice, turn left or turn right.",
               "The browser records 5 seconds at 15 frames per second and uploads the frames.",
               "Liveness: MediaPipe places 478 landmarks per frame. Blinks are detected from the eye aspect ratio and MediaPipe's "
               "blink score, each relative to the user's own baseline; head turns from the nose position between the cheeks. "
               "A static photo or screen shows no change and is rejected.",
               "Identity: SFace embeddings of frontal frames are compared with each authorised template by cosine similarity "
               "(≥ 0.40), and the same face must appear throughout the scan.",
               "Only then is the DEK unwrapped, the LSBs read and the message decrypted; GCM verifies integrity. Any failure is "
               "logged with a photo; three failures lock the vault for 60 seconds."], ref="sext")

    # ------------------------------------------------------------ chapter 4
    d.chapter_heading("Implementation")
    d.table("Technology stack", ["Layer", "Technology"],
            [["Backend", "Python 3.12, FastAPI, cryptography (AES-GCM, HKDF), argon2-cffi, NumPy, Pillow"],
             ["Face and liveness", "OpenCV YuNet + SFace (DeepFace fallback), MediaPipe Face Landmarker"],
             ["Storage", "SQLite audit log, AES-encrypted face profiles, device key"],
             ["Frontend", "Next.js 14, TypeScript, Tailwind CSS, Framer Motion, Recharts (light theme)"],
             ["Testing", "pytest (unit + API), Playwright browser test with a simulated camera"]], widths=[1.4, 4.4], small=True)
    d.p("The web application has eight pages: Home, Enroll Face (guided five-sample capture), Hide Data (drag-and-drop, live "
        "capacity meter), Extract Data (live scan with ACCESS GRANTED / DENIED), Analysis (comparison slider, heatmap, bit "
        "planes, PSNR/SSIM), Security Log (attempts with intruder photos), Attack Lab (chi-square steganalysis) and How It "
        "Works. Demo Mode preloads sample images and a password-protected demo pair.")
    d.figure(SHOT / "06_access_granted.png", "Extract page after a successful live scan", width=5.2, max_height=5.0)

    # ------------------------------------------------------------ chapter 5
    d.chapter_heading("Testing and Results")
    d.p(f'The dataset contains {F["images"]} cover images (24 Kodak {c("kodak")}, {F["by_source"]["USC-SIPI"]} USC-SIPI '
        f'{c("sipi")} and {F["by_source"]["Generated"]} synthetic, 256×256 to 1920×1080) and five payloads (100 B, 1 KB, '
        f'10 KB, 50 KB text and a {P["PDF"]["bytes"]:,}-byte PDF). Each of the {F["runs"]} combinations was embedded, saved, '
        f'reloaded and extracted. All {F["ok_runs"]} runs that fitted were recovered exactly; {len(F["cap_fail"])} were correctly '
        "rejected as too large for 256×256 images. Face tests use AI-generated faces of people who do not exist.")
    d.table("Image quality by payload", ["Payload", "PSNR mean (min) dB", "SSIM mean", "Embed ms", "Extract ms"],
            [[p, f'{f2(P[p]["psnr_mean"])} ({f2(P[p]["psnr_min"])})', f'{P[p]["ssim_mean"]:.5f}', f1(P[p]["embed_med"]),
              f1(P[p]["extract_med"])] for p in ("100B", "1KB", "10KB", "PDF", "50KB")],
            widths=[1.0, 1.7, 1.2, 1.0, 1.0], align=["l", "r", "r", "r", "r"], small=True)
    d.figure(FIG / "fig_quality_vs_payload.png", f"PSNR and SSIM for all {F['ok_runs']} successful runs", width=6.0)
    d.p(f'PSNR stayed far above the 40 dB imperceptibility level (worst case {f2(F["min_psnr_all"])} dB). Against the chi-square '
        "attack, random positions sharply reduce detection at moderate payloads; at 100 % payload every LSB is overwritten and "
        "both schemes are detected.")
    d.table("Chi-square detection (% of image flagged, mean of 41 images)", ["Payload", "Sequential LSB", "Random LSB (ours)"],
            [[f"{k} %", f1(S[k]["seq"]), f1(S[k]["rnd"])] for k in ("10", "25", "50", "100")],
            widths=[1.5, 2.1, 2.1], align=["l", "r", "r"], small=True)
    d.figure(FIG / "fig_steganalysis_curve.png", "Chi-square attack on kodim23 with a 50 % payload", width=5.6)
    rows = [[s, n, f"{ok}/{n}"] for s, n, ok, _ in F["live"]]
    d.table("Liveness tests on synthetic faces", ["Scenario", "Trials", "Correct"], rows, widths=[3.4, 1.0, 1.2], small=True)
    fs = F["face"]
    d.p(f'Face matching gave genuine similarity of about {fs["genuine_mean"]:.2f} and impostor similarity of at most '
        f'{fs["impostor_max"]:.2f}, so at the 0.40 threshold there were no false accepts or rejects on the synthetic set; '
        "real-world accuracy still needs testing with real users. Lossless re-saving (PNG, BMP) preserves the secret, while "
        "JPEG, resizing, cropping or editing destroy it and are always detected by the integrity check. The browser test "
        "confirmed that a photo attack, an impostor and a wrong challenge are denied, that the third failure locks the vault, "
        "and that intruder photos are stored.")

    # ------------------------------------------------------------ chapter 6
    d.chapter_heading("Limitations and Future Work")
    d.bullets(["The face check is enforced by the server, not bound into the key: someone holding both the device key and the vault could bypass it.",
               "The vault opens by face only on the computer that created it; the password slot is portable.",
               "JPEG compression or editing (e.g. sending through WhatsApp) destroys the hidden data; files must be sent as documents.",
               "At full capacity any LSB replacement is detectable; stronger detectors can estimate the payload.",
               "Liveness stops photos and simple replays, not real-time deepfakes or masks; face accuracy was tested on synthetic faces."])
    d.p("**Future work:** a fuzzy extractor so that the key is derived from the face itself; DCT or DWT embedding with error "
        "correction to survive compression; adaptive embedding against stronger steganalysis; passive anti-spoofing; and a "
        "user study with real volunteers.")

    # ------------------------------------------------------------ chapter 7
    d.chapter_heading("Conclusion")
    d.p("FaceLock Stego combines encryption, random-order LSB steganography and live face verification so that a hidden secret "
        "is confidential, visually undetectable, and recoverable only by an authorised person who is physically present. "
        "Every result in this report was measured on the project dataset. The most valuable next step is to bind the key "
        "cryptographically to the face with a fuzzy extractor.")

    d.unnumbered_heading("References")
    for i, k in enumerate(SHORT_REFS, 1):
        d.add(t="p", text=f"[{i}]  {REFS[R[k] - 1]}", align="left", line=276, after=80)
    d.toc_pos = toc_pos
    return d


def short_lists(d: Doc, pages: dict) -> list[dict]:
    secs = [dict(s, blocks=list(s["blocks"])) for s in d.sections]
    front = secs[1]["blocks"]
    ins = [{"t": "h", "level": 1, "text": "TABLE OF CONTENTS", "center": True, "newPage": True},
           {"t": "toc", "entries": [{"text": e["text"], "level": e["level"], "page": pages.get(e["key"], "00"),
                                     "plain": e.get("plain", False)} for e in d.toc]}]
    secs[1]["blocks"] = front[:d.toc_pos] + ins + front[d.toc_pos:]
    return secs
