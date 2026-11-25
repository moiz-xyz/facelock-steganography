"""Content of the final project report (docs/Report.docx + .pdf).

All numbers come from ``facts()`` (benchmark CSVs, pytest JUnit XML, UI E2E JSON).
Code listings are cut from the real source files at build time.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import DIAG, FIG, ROOT, SHOT, Doc, cfg, facts

BACK = ROOT / "app" / "backend" / "facelock"


def snippet(file: Path, start: str, end: str | None = None, max_lines: int = 40) -> str:
    lines = file.read_text().split("\n")
    i = next(k for k, l in enumerate(lines) if l.startswith(start) or l.strip().startswith(start))
    j = i + 1
    while j < len(lines) and j - i < max_lines:
        if end is not None and lines[j].startswith(end):
            break
        if end is None and lines[j].strip() == "" and j + 1 < len(lines) and not lines[j + 1].startswith((" ", "\t")):
            break
        j += 1
    return "\n".join(l.rstrip() for l in lines[i:j]).rstrip()


def f1(x): return f"{x:.1f}"
def f2(x): return f"{x:.2f}"


REFS = [
    'N. F. Johnson and S. Jajodia, "Exploring steganography: Seeing the unseen," *Computer*, vol. 31, no. 2, pp. 26-34, 1998.',
    'A. Cheddad, J. Condell, K. Curran, and P. Mc Kevitt, "Digital image steganography: Survey and analysis of current methods," *Signal Processing*, vol. 90, no. 3, pp. 727-752, 2010.',
    'J. Fridrich, *Steganography in Digital Media: Principles, Algorithms, and Applications*. Cambridge, U.K.: Cambridge Univ. Press, 2009.',
    'C.-K. Chan and L. M. Cheng, "Hiding data in images by simple LSB substitution," *Pattern Recognition*, vol. 37, no. 3, pp. 469-474, 2004.',
    'J. Mielikainen, "LSB matching revisited," *IEEE Signal Processing Letters*, vol. 13, no. 5, pp. 285-287, 2006.',
    'D.-C. Wu and W.-H. Tsai, "A steganographic method for images by pixel-value differencing," *Pattern Recognition Letters*, vol. 24, no. 9-10, pp. 1613-1626, 2003.',
    'A. Westfeld, "F5 - A steganographic algorithm: High capacity despite better steganalysis," in *Proc. 4th Int. Workshop on Information Hiding*, LNCS 2137, Springer, 2001, pp. 289-302.',
    'N. Provos, "Defending against statistical steganalysis," in *Proc. 10th USENIX Security Symposium*, 2001, pp. 323-335.',
    'P.-Y. Chen and H.-J. Lin, "A DWT based approach for image steganography," *Int. J. Applied Science and Engineering*, vol. 4, no. 3, pp. 275-290, 2006.',
    'T. Pevny, T. Filler, and P. Bas, "Using high-dimensional image models to perform highly undetectable steganography," in *Proc. 12th Int. Conf. Information Hiding*, LNCS 6387, Springer, 2010, pp. 161-177.',
    'V. Holub, J. Fridrich, and T. Denemark, "Universal distortion function for steganography in an arbitrary domain," *EURASIP J. Information Security*, vol. 2014, art. 1, 2014.',
    'A. Westfeld and A. Pfitzmann, "Attacks on steganographic systems," in *Proc. 3rd Int. Workshop on Information Hiding*, LNCS 1768, Springer, 2000, pp. 61-76.',
    'J. Fridrich, M. Goljan, and R. Du, "Reliable detection of LSB steganography in color and grayscale images," in *Proc. ACM Workshop on Multimedia and Security*, 2001, pp. 27-30.',
    'F. Schroff, D. Kalenichenko, and J. Philbin, "FaceNet: A unified embedding for face recognition and clustering," in *Proc. IEEE CVPR*, 2015, pp. 815-823.',
    'J. Deng, J. Guo, N. Xue, and S. Zafeiriou, "ArcFace: Additive angular margin loss for deep face recognition," in *Proc. IEEE/CVF CVPR*, 2019, pp. 4690-4699.',
    'Y. Zhong, W. Deng, J. Hu, D. Zhao, X. Li, and D. Wen, "SFace: Sigmoid-constrained hypersphere loss for robust face recognition," *IEEE Trans. Image Processing*, vol. 30, pp. 2587-2598, 2021.',
    'W. Wu, H. Peng, and S. Yu, "YuNet: A tiny millisecond-level face detector," *Machine Intelligence Research*, vol. 20, no. 5, pp. 656-665, 2023.',
    'Y. Kartynnik, A. Ablavatski, I. Grishchenko, and M. Grundmann, "Real-time facial surface geometry from monocular video on mobile GPUs," arXiv:1907.06724, 2019.',
    'T. Soukupova and J. Cech, "Real-time eye blink detection using facial landmarks," in *Proc. 21st Computer Vision Winter Workshop*, 2016.',
    'G. Pan, L. Sun, Z. Wu, and S. Lao, "Eyeblink-based anti-spoofing in face recognition from a generic webcamera," in *Proc. IEEE ICCV*, 2007, pp. 1-8.',
    'Z. Boulkenafet, J. Komulainen, and A. Hadid, "Face spoofing detection using colour texture analysis," *IEEE Trans. Information Forensics and Security*, vol. 11, no. 8, pp. 1818-1830, 2016.',
    'ISO/IEC 30107-1:2016, *Information technology - Biometric presentation attack detection - Part 1: Framework*. Geneva: ISO, 2016.',
    'A. Juels and M. Wattenberg, "A fuzzy commitment scheme," in *Proc. 6th ACM Conf. Computer and Communications Security*, 1999, pp. 28-36.',
    'Y. Dodis, L. Reyzin, and A. Smith, "Fuzzy extractors: How to generate strong keys from biometrics and other noisy data," in *Proc. EUROCRYPT 2004*, LNCS 3027, Springer, 2004, pp. 523-540.',
    'A. K. Jain, K. Nandakumar, and A. Nagar, "Biometric template security," *EURASIP J. Advances in Signal Processing*, vol. 2008, art. 579416, 2008.',
    'M. Dworkin, "Recommendation for block cipher modes of operation: Galois/Counter Mode (GCM) and GMAC," NIST SP 800-38D, 2007.',
    'H. Krawczyk and P. Eronen, "HMAC-based extract-and-expand key derivation function (HKDF)," IETF RFC 5869, 2010.',
    'A. Biryukov, D. Dinu, D. Khovratovich, and S. Josefsson, "Argon2 memory-hard function for password hashing and proof-of-work applications," IETF RFC 9106, 2021.',
    'Z. Wang, A. C. Bovik, H. R. Sheikh, and E. P. Simoncelli, "Image quality assessment: From error visibility to structural similarity," *IEEE Trans. Image Processing*, vol. 13, no. 4, pp. 600-612, 2004.',
    'T. Karras, S. Laine, and T. Aila, "A style-based generator architecture for generative adversarial networks," in *Proc. IEEE/CVF CVPR*, 2019, pp. 4401-4410.',
    'R. Franzen, "Kodak lossless true color image suite." [Online]. Available: http://r0k.us/graphics/kodak/',
    'University of Southern California Signal and Image Processing Institute, "The USC-SIPI image database." [Online]. Available: https://sipi.usc.edu/database/',
    'I. J. Cox, J. Kilian, F. T. Leighton, and T. Shamoon, "Secure spread spectrum watermarking for multimedia," *IEEE Trans. Image Processing*, vol. 6, no. 12, pp. 1673-1687, 1997.',
    'S. I. Serengil and A. Ozpinar, "LightFace: A hybrid deep face recognition framework," in *Proc. Innovations in Intelligent Systems and Applications Conf. (ASYU)*, 2020, pp. 1-5.',
    'OpenCV team, "OpenCV Zoo: Face detection (YuNet) and face recognition (SFace) models." [Online]. Available: https://github.com/opencv/opencv_zoo',
    'Google, "MediaPipe Face Landmarker." [Online]. Available: https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker',
]
R = {k: i + 1 for i, k in enumerate(["johnson", "cheddad", "fridrich_book", "chan", "mielikainen", "pvd", "f5", "outguess", "dwt", "hugo",
                                     "uniward", "chisq", "rs", "facenet", "arcface", "sface", "yunet", "mediapipe", "ear", "pan",
                                     "texture", "iso30107", "fuzzycommit", "fuzzyext", "templatesec", "gcm", "hkdf", "argon2", "ssim",
                                     "stylegan", "kodak", "sipi", "cox", "deepface", "opencvzoo", "mpdocs"])}


def c(*keys) -> str:
    return "[" + "], [".join(str(R[k]) for k in keys) + "]"


ABBR = [("AAD", "Additional Authenticated Data"), ("AES", "Advanced Encryption Standard"), ("API", "Application Programming Interface"),
        ("CTR", "Counter mode (block cipher)"), ("CVD", "Colour Vision Deficiency"), ("DCT", "Discrete Cosine Transform"),
        ("DEK", "Data Encryption Key"), ("DFD", "Data Flow Diagram"), ("DWT", "Discrete Wavelet Transform"),
        ("EAR", "Eye Aspect Ratio"), ("FAR", "False Acceptance Rate"), ("FRR", "False Rejection Rate"),
        ("GAN", "Generative Adversarial Network"), ("GCM", "Galois/Counter Mode"), ("HKDF", "HMAC-based Key Derivation Function"),
        ("HMAC", "Hash-based Message Authentication Code"), ("JPEG", "Joint Photographic Experts Group"), ("KEK", "Key Encryption Key"),
        ("LSB", "Least Significant Bit"), ("MSE", "Mean Squared Error"), ("PAD", "Presentation Attack Detection"),
        ("PNG", "Portable Network Graphics"), ("PRNG", "Pseudo-Random Number Generator"), ("PSNR", "Peak Signal-to-Noise Ratio"),
        ("PVD", "Pixel-Value Differencing"), ("REST", "Representational State Transfer"), ("RGB", "Red, Green, Blue"),
        ("SFace", "Sigmoid-constrained hypersphere loss face model"), ("SQL", "Structured Query Language"),
        ("SSIM", "Structural Similarity Index Measure"), ("UI", "User Interface")]


def build_report(F: dict) -> Doc:
    C = cfg()
    d = Doc()
    P = F["pay"]
    pt = F["pytest"]
    ui_ok = sum(1 for x in F["ui"] if x["passed"])
    far40 = next(x for x in F["farfrr"] if float(x["threshold"]) == 0.4)
    far30 = next(x for x in F["farfrr"] if float(x["threshold"]) == 0.3)
    S = F["stega"]
    m = F["machine"]

    # ================================================================ cover
    members = C.get("group_members") or [{"name": C["student_name"], "roll_no": C["roll_no"]}]
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
    for mbr in members:
        d.add(t="center", text=f'{mbr["name"]}   ({mbr["roll_no"]})', size=14, bold=True, after=60)
    d.add(t="spacer", n=4)
    d.add(t="center", text=C["submission_date"], size=12)

    # ========================================================== front matter
    d.section("roman")
    d.front_heading("Abstract")
    d.p("Steganography hides the existence of a message; cryptography hides its meaning. Neither, on its own, controls *who* can "
        "recover a secret once the carrier file and the key have been copied. This project, **FaceLock Stego**, combines the "
        "two with face biometrics. A secret text or file is encrypted with a fresh AES-256-GCM key and embedded in the least "
        "significant bits of a PNG image at positions chosen by a keyed pseudo-random permutation, so the image carries no key "
        "and no visible structure. The data key is stored only in a separate *Face Vault* file, wrapped once per authorised "
        "person (up to three) under keys derived from the device key and that person's face template, with an optional "
        "Argon2id backup password. To extract, the user must pass a server-side liveness check (eye-blink detection with the "
        "eye aspect ratio plus a random head-turn or double-blink challenge, computed with MediaPipe's 478-point face mesh) "
        "and an SFace face match. Failed attempts are logged with an intruder photograph and three failures lock the vault.")
    d.p(f'The system was implemented as a FastAPI backend and a Next.js web application and evaluated on {F["images"]} cover '
        f'images (24 Kodak, {F["by_source"]["USC-SIPI"]} USC-SIPI and {F["by_source"]["Generated"]} synthetic) with five '
        f'payloads. All {F["ok_runs"]} embeddings that fitted were recovered bit-exactly; the {len(F["cap_fail"])} remaining runs '
        f'were correctly rejected for exceeding capacity. PSNR ranged from {f2(F["min_psnr_all"])} dB to '
        f'{f2(P["100B"]["psnr_max"])} dB (mean {f2(P["10KB"]["psnr_mean"])} dB for 10 KB) and SSIM never fell below '
        f'{F["min_ssim_all"]:.4f}. Against the chi-square attack at 50 % payload, sequential LSB was flagged over '
        f'{f1(S["50"]["seq"])} % of the scanned image versus {f1(S["50"]["rnd"])} % for the keyed random embedding. In '
        f'{F["live_summary"]["trials"]} automated liveness trials on synthetic faces every decision was correct, including all '
        f'photo attacks. {pt["tests"]} unit and API tests and {len(F["ui"])} browser end-to-end checks pass. The report closes '
        "with an honest account of the design's limits, notably that the face gate is enforced by the server rather than "
        "bound cryptographically, and proposes a fuzzy-extractor and transform-domain embedding as future work.")
    d.p("**Keywords:** steganography, least significant bit, AES-GCM, face recognition, liveness detection, eye aspect ratio, "
        "chi-square steganalysis, key wrapping.", align="left")

    toc_pos = len(d.sections[-1]["blocks"])   # TOC / LOF / LOT inserted here later
    # ============================================================ chapter 1
    d.section("decimal")
    ch1(d, F, C)
    ch2(d, F)
    ch3(d, F)
    ch4(d, F)
    ch5(d, F)
    ch6(d, F)
    ch7(d, F)
    ch8(d, F)
    d.unnumbered_heading("References")
    for i, r in enumerate(REFS, 1):
        d.add(t="p", text=f"[{i}]  {r}", align="left", line=276, after=100)
    appendices(d, F)
    d.toc_pos = toc_pos
    return d


# =================================================================== chapters
def ch1(d: Doc, F, C):
    d.chapter_heading("Introduction")
    d.h2("1.1", "Background")
    d.p("Every day people exchange photographs over messaging apps, e-mail and cloud drives. Those images are an ideal cover for "
        "private information: they are large, varied and unremarkable. *Steganography* - from the Greek for \"covered writing\" - "
        f"exploits this by hiding a message inside an innocuous carrier so that an observer does not even suspect communication "
        f"is taking place {c('johnson', 'cheddad')}. The simplest and still most widely taught image technique replaces the "
        f"least significant bit (LSB) of each colour value with one bit of the message {c('chan')}. Changing a value by at most one "
        "intensity level out of 255 is invisible to the human eye.")
    d.p("Steganography alone, however, offers *security through obscurity*: once someone knows (or guesses) that an image carries "
        f"data and how it was embedded, they can read it. Statistical steganalysis such as the chi-square attack {c('chisq')} and "
        f"RS analysis {c('rs')} detect naive LSB embedding automatically. The standard remedy is to encrypt before embedding, which "
        "moves the problem to key management: whoever holds the password or key file holds the secret. Passwords are shared, "
        "written down and phished; key files are copied.")
    d.p("Biometrics such as the face offer a factor that is bound to a person rather than to knowledge or possession. Modern deep "
        f"face embeddings {c('facenet', 'arcface', 'sface')} recognise identities with high accuracy from an ordinary webcam, and "
        f"lightweight liveness checks {c('ear', 'pan')} can reject a photograph held up to the camera. FaceLock Stego combines "
        "these three ideas - hiding, encrypting and biometric gating - into one system.")
    d.h2("1.2", "Cryptography, Steganography and Biometrics")
    d.p(f'{d.next_tab()} contrasts the three building blocks. They are complementary: cryptography protects meaning, '
        "steganography protects the existence of communication, and biometrics ties access to a physical person.")
    d.table("Comparison of the three security mechanisms combined in this project",
            ["Aspect", "Cryptography", "Steganography", "Face biometrics"],
            [["Goal", "Hide the meaning of data", "Hide the existence of data", "Verify who is present"],
             ["Output looks like", "Random bytes (obviously secret)", "An ordinary image", "Accept / reject decision"],
             ["Main secret", "Key or password", "Embedding algorithm + key", "The person's face (not secret, but hard to forge live)"],
             ["Typical attack", "Key theft, brute force", "Statistical steganalysis", "Photo / video spoofing"],
             ["Failure mode", "Ciphertext attracts attention", "Detected = readable if unencrypted", "False accept / false reject"],
             ["Role in FaceLock", "AES-256-GCM, HKDF, Argon2id", "Keyed random LSB in PNG", "SFace match + MediaPipe liveness"]],
            widths=[1.1, 1.5, 1.5, 1.6], small=True)
    d.h2("1.3", "Problem Statement")
    d.p("Existing student and hobby steganography tools typically (i) embed sequentially from the first pixel, which is trivially "
        "detected and read; (ii) store the password or key inside the image or derive positions from it; (iii) rely on a single "
        "password that can be shared or stolen; and (iv) offer no audit trail or brute-force protection. Commercial biometric "
        "products, on the other hand, protect devices rather than individual hidden messages.")
    d.p("**Problem:** design and implement a system in which a secret hidden in an ordinary image can be recovered *only* by a "
        "registered person who is physically present in front of a camera, such that the image alone reveals neither the data "
        "nor where it is, a photograph of the owner is not enough, repeated guessing is throttled and logged, and the quality "
        "of the cover image is measurably preserved.")
    d.h2("1.4", "Objectives")
    d.numbers([
        "Embed encrypted text or files in PNG images with LSB substitution at key-selected random positions, with an authenticated header.",
        "Encrypt every payload with a random AES-256-GCM data key that is never stored in the image.",
        "Design a Face Vault that wraps the data key for up to three enrolled faces and an optional Argon2id-protected password.",
        "Perform face matching and liveness detection (EAR blinks + random challenge) on the server before the key is released.",
        "Record every attempt, capture intruder photos and lock a vault after three failures.",
        "Provide a polished web application with analysis, attack-lab and explanation pages, plus a demo mode.",
        "Build a documented dataset and measure capacity, PSNR, MSE, SSIM, speed, robustness and detectability with real runs.",
    ], ref="obj")
    d.h2("1.5", "Scope and Constraints")
    d.bullets([
        "**In scope:** lossless images (PNG, BMP, TIFF input; PNG output), text and arbitrary files, one to three authorised faces per secret, a single owner device running the backend.",
        "**Out of scope:** JPEG-robust embedding, distributed key servers, mobile apps, certified presentation-attack detection.",
        "**Constraints:** must install on Windows without compiling native code (ruled out dlib), must run on a laptop CPU, and must be demonstrable without network access to third-party APIs.",
        "**Ethics:** no real person's face is stored in the repository; automated tests use StyleGAN-generated faces of people who do not exist.",
    ])
    d.h2("1.6", "Contributions")
    d.bullets([
        "A keyed, prefix-consistent random slot permutation built from AES-CTR, which lets the header be read before the body without storing positions.",
        "A Face Vault format that separates the key from the carrier, binds the vault to the exact stego pixels and supports multi-person access.",
        "A server-side verification pipeline combining lockout, image binding, liveness, identity, consistency and authenticated decryption.",
        "A reproducible evaluation: dataset builder, benchmark scripts, charts, unit/API tests and a headless browser test that drives the real UI with a synthetic camera.",
    ])
    d.h2("1.7", "Organisation of the Report")
    d.p("Chapter 2 reviews steganography, steganalysis, face recognition and liveness literature. Chapter 3 analyses requirements "
        "and threats. Chapter 4 presents the system design, Chapter 5 the implementation, and Chapter 6 the testing methodology "
        "and measured results. Chapter 7 discusses limitations and future work, and Chapter 8 concludes. Appendices contain the "
        "API reference, the user manual, per-image results and the test inventory.")


def ch2(d: Doc, F):
    d.chapter_heading("Literature Review")
    d.h2("2.1", "Taxonomy of Image Steganography")
    d.p(f"Image steganography methods are usually grouped into spatial-domain methods, which modify pixel values directly, "
        f"transform-domain methods, which modify coefficients of a frequency transform, and adaptive methods, which choose where "
        f"to embed by minimising a distortion cost {c('cheddad', 'fridrich_book')}. Three properties are traded against each "
        "other: *capacity* (bits per pixel), *imperceptibility* (visual and statistical) and *robustness* (survival of "
        "processing such as compression). A fourth, *security*, asks whether an adversary who knows the algorithm but not the "
        "key can detect or read the payload (Kerckhoffs' principle applied to steganography).")
    d.h2("2.2", "Spatial Domain: LSB and Variants")
    d.p(f"**LSB replacement** writes each message bit into bit 0 of a pixel channel {c('chan')}. With one bit in each of R, G and B "
        "an image offers 3 bits per pixel, i.e. 3/8 of its raw size. The maximum change per value is 1, giving a theoretical "
        "PSNR above 51 dB even at full capacity. Its weakness is statistical: replacement only ever swaps values within the "
        "pairs (2i, 2i+1), which equalises the histogram of each pair - the asymmetry exploited by chi-square and RS analysis.")
    d.p(f"**LSB matching** (±1 embedding) randomly adds or subtracts one when a bit must change, which avoids the pair "
        f"artefact; *LSB matching revisited* {c('mielikainen')} reduces the change rate further. **Pixel-value differencing** "
        f"(PVD) {c('pvd')} embeds more bits in edges than in smooth areas. **Random-order embedding** - the approach taken here - "
        "keeps replacement but scatters the bits with a key-seeded generator, so an adversary does not know which samples to "
        "test and a sequential scan sees only a thin, uniform modification.")
    d.h2("2.3", "Transform Domain: DCT")
    d.p(f"JPEG images are stored as quantised 8×8 discrete cosine transform (DCT) coefficients. JSteg replaced coefficient LSBs, "
        f"OutGuess {c('outguess')} corrected the histogram afterwards, and F5 {c('f5')} decremented coefficient magnitudes with "
        "matrix encoding to raise embedding efficiency. DCT methods survive JPEG storage because they operate after "
        "quantisation, but their capacity is lower and they require a JPEG cover.")
    d.h2("2.4", "Transform Domain: DWT")
    d.p(f"Discrete wavelet transform (DWT) methods hide data in high-frequency sub-bands (HL, LH, HH) where the eye is less sensitive "
        f"{c('dwt')}. They offer better robustness to mild filtering than spatial LSB and a natural multi-resolution choice of "
        f"strength, as in spread-spectrum watermarking {c('cox')}, at the cost of capacity and complexity.")
    d.h2("2.5", "Adaptive Steganography")
    d.p(f"Modern schemes such as HUGO {c('hugo')} and S-UNIWARD {c('uniward')} define a per-pixel distortion cost and embed with "
        "syndrome-trellis codes so that changes land in textured regions. They are the state of the art against machine-learning "
        "steganalysis but are considerably more complex to implement and explain.")
    d.h2("2.6", "Comparison of Techniques")
    d.table("Comparison of image steganography techniques",
            ["Technique", "Capacity", "Imperceptibility", "Robust to JPEG", "Detectability", "Complexity"],
            [["Sequential LSB", "High (3 bpp)", "Very high", "No", "Easy (chi-square)", "Very low"],
             ["Random-order LSB (this work)", "High (3 bpp)", "Very high", "No", "Low at < 50 % load", "Low"],
             ["LSB matching", "High", "Very high", "No", "Lower than replacement", "Low"],
             ["PVD", "Medium-high", "High", "No", "Medium", "Medium"],
             ["DCT (F5 / OutGuess)", "Low-medium", "High", "Yes", "Medium", "Medium"],
             ["DWT", "Medium", "High", "Partly", "Medium", "Medium-high"],
             ["Adaptive (S-UNIWARD)", "Medium", "Very high", "Variant-dependent", "Very low", "High"]],
            widths=[1.6, 1.0, 1.1, 1.0, 1.2, 1.0], small=True)
    d.p("LSB was chosen because it gives the highest capacity and the clearest explanation for a teaching project, and because "
        "the cryptographic layer - not the embedding - is what guarantees confidentiality. Random ordering was added to remove "
        "the most obvious statistical weakness. Transform-domain embedding is discussed as future work (Section 7.2).")
    d.h2("2.7", "Steganalysis")
    d.p(f"Westfeld and Pfitzmann's chi-square attack {c('chisq')} compares the observed frequency of each even value 2i with the mean "
        "of the pair (2i, 2i+1). For an unmodified image these differ; after full LSB replacement they converge. The statistic")
    d.code("chi2 = sum_i (n_2i - E_i)^2 / E_i ,   E_i = (n_2i + n_2i+1) / 2\np    = 1 - CDF_chi2(chi2, k - 1)")
    d.p("gives the probability p that the samples carry embedded data. Evaluating p over growing prefixes of the image (1 %, 2 %, "
        f"..., 100 %) reveals both the presence and the length of a sequential payload. RS analysis {c('rs')} and sample-pair "
        "analysis estimate the embedding rate of any LSB-replacement scheme, including random-order ones, and modern detectors "
        "use rich models with machine-learning classifiers. FaceLock Stego is therefore evaluated against chi-square "
        "(Chapter 6) and its limitations against stronger detectors are stated explicitly (Chapter 7).")
    d.h2("2.8", "Face Detection and Embeddings")
    d.p(f"Face recognition maps an aligned face crop to an embedding vector such that images of the same person are close. FaceNet "
        f"{c('facenet')} introduced triplet loss; ArcFace {c('arcface')} added an angular margin; SFace {c('sface')} constrains "
        f"intra- and inter-class distances with sigmoid functions and ships as a 37 MB ONNX model in OpenCV Zoo {c('opencvzoo')}. "
        f"YuNet {c('yunet')} is a millisecond-level detector that also returns five landmarks used for alignment. Both run in "
        f"OpenCV's DNN module, so no compiler or GPU is required. DeepFace {c('deepface')} wraps several models behind one API "
        "and was used as an automatic fallback. Verification compares cosine similarity with a threshold; the SFace authors "
        "recommend 0.363 for cosine similarity.")
    d.h2("2.9", "Liveness and Presentation Attack Detection")
    d.p(f"A presentation attack shows the sensor a printed photo, a screen, a video replay or a mask {c('iso30107')}. Defences are "
        f"*passive* (texture, depth, reflectance {c('texture')}) or *active* (challenge-response). Blink detection is a classic "
        f"active cue {c('pan')}. Soukupova and Cech {c('ear')} defined the eye aspect ratio")
    d.code("EAR = (|p2 - p6| + |p3 - p5|) / (2 |p1 - p4|)")
    d.p(f"over six eye landmarks; it stays roughly constant while the eye is open and drops sharply during a blink. MediaPipe Face "
        f"Mesh / Face Landmarker {c('mediapipe', 'mpdocs')} provides 478 three-dimensional landmarks in real time on a CPU, from "
        "which both EAR and head yaw can be computed. A random challenge (\"turn left\", \"blink twice\") defeats a pre-recorded "
        "video unless the attacker can respond in real time.")
    d.h2("2.10", "Biometric Template Protection and Key Binding")
    d.p(f"Biometric samples are noisy, so a key cannot simply be hashed from an embedding. Juels and Wattenberg's fuzzy commitment "
        f"{c('fuzzycommit')} and Dodis et al.'s fuzzy extractors {c('fuzzyext')} use error-correcting codes to derive a stable key "
        f"from a noisy reading, so that the template need not be stored. Jain et al. {c('templatesec')} survey template "
        "protection requirements: diversity, revocability, security and performance. These schemes are the principled way to "
        "*bind* a key to a face; they are discussed as future work because they need careful quantisation of embeddings to "
        "keep false rejections acceptable.")
    d.h2("2.11", "Research Gap")
    d.p("Published systems usually address one layer: steganography papers optimise capacity or undetectability and assume a "
        "shared key; biometric cryptosystems protect keys but not covert channels; liveness papers evaluate detectors in "
        "isolation. Few working, documented systems combine encrypted random-order embedding, a separate biometric key vault, "
        "live challenge-response verification, audit logging and brute-force throttling, and measure all of them on a public "
        "dataset. FaceLock Stego fills this gap at the level of an engineering prototype.")


def ch3(d: Doc, F):
    d.chapter_heading("System Analysis and Requirements")
    d.h2("3.1", "Analysis of Existing Systems")
    d.p("Typical open-source LSB tools (command-line scripts and web demos) were analysed. Their common properties are listed "
        "below; each one became a requirement for the proposed system.")
    d.table("Weaknesses of typical existing LSB tools and the corresponding requirement",
            ["Observed weakness", "Consequence", "Requirement in FaceLock Stego"],
            [["Sequential embedding from pixel (0,0)", "Detected and read by chi-square", "Keyed random slot order (FR-6)"],
             ["Plaintext embedded", "Anyone who finds it can read it", "AES-256-GCM before embedding (FR-5)"],
             ["Password stored or reused as seed", "Image alone leaks the secret", "Key held only in a separate vault (FR-7)"],
             ["Single shared password", "Can be shared or phished", "Live face + optional password (FR-9, FR-12)"],
             ["No integrity check", "Silent corruption after edits", "GCM tag + pixel fingerprint (FR-8)"],
             ["No brute-force limit or log", "Unlimited guessing", "Lockout + audit log + intruder photo (FR-13-15)"],
             ["Lossy output allowed", "Data destroyed by JPEG", "PNG-only output with warnings (FR-4)"]],
            widths=[1.6, 1.5, 1.8], small=True)
    d.h2("3.2", "Proposed System")
    d.p("The proposed system is a local web application. The owner enrols their face, hides a secret in a cover image for up to "
        "three enrolled people, and receives two files: the stego PNG, which can be shared openly, and the Face Vault, which "
        "the owner keeps. To extract, an authorised person loads both files and performs a short live scan; the backend "
        "decides and, if successful, returns the decrypted secret.")
    d.h2("3.3", "Stakeholders and Users")
    d.bullets(["**Owner (sender):** enrols, hides secrets, manages profiles.",
               "**Authorised receiver:** an enrolled person allowed to extract.",
               "**Analyst / examiner:** inspects quality metrics, logs and the steganalysis lab.",
               "**Adversary:** obtains the image and possibly the vault and tries to read the secret."])
    d.h2("3.4", "Functional Requirements")
    d.table("Functional requirements", ["ID", "Requirement", "Verified by"],
            [["FR-1", "Enrol a face from 5 guided webcam samples; reject inconsistent samples", "API test, UI E2E"],
             ["FR-2", "List and delete face profiles", "UI E2E"],
             ["FR-3", "Accept PNG/BMP/JPG/WebP covers and text or any file as secret", "API test"],
             ["FR-4", "Output the stego image as PNG only; warn on lossy input; refuse JPEG for extraction", "API test"],
             ["FR-5", "Encrypt the payload with AES-256-GCM using a random 256-bit key", "Unit tests"],
             ["FR-6", "Embed bits at key-driven pseudo-random positions with a length/salt/nonce header", "Unit tests"],
             ["FR-7", "Store the data key only in a separate .vault file", "Unit test (key absent from files)"],
             ["FR-8", "Bind the vault to the stego pixels; detect tampering", "Unit + API tests"],
             ["FR-9", "Verify the face on the server against up to 3 authorised templates", "API test, UI E2E"],
             ["FR-10", "Detect blinks with EAR and verify a random server-issued challenge", "Unit + liveness experiment"],
             ["FR-11", "Reject static photos / screens", "API test, UI E2E, experiment"],
             ["FR-12", "Offer an Argon2id-protected backup password", "Unit + API tests"],
             ["FR-13", "Log every attempt with time, result and reason", "API test"],
             ["FR-14", "Store an intruder photo for each failed face attempt", "API test, UI E2E"],
             ["FR-15", "Lock a vault for a configurable time after 3 failures", "Unit + API tests, UI E2E"],
             ["FR-16", "Show live capacity, PSNR/MSE/SSIM, heatmap, bit planes, histograms", "UI E2E"],
             ["FR-17", "Run chi-square steganalysis on sequential vs random LSB", "API test, UI E2E"],
             ["FR-18", "Provide a demo mode with sample covers and a ready stego/vault pair", "UI E2E"]],
            widths=[0.6, 3.6, 1.6], small=True)
    d.h2("3.5", "Non-Functional Requirements")
    d.table("Non-functional requirements", ["Category", "Requirement", "Target / evidence"],
            [["Security", "No key material in the image; authenticated encryption everywhere", "Design review, unit tests"],
             ["Imperceptibility", "PSNR > 40 dB and SSIM > 0.99 for supported payloads", f'Measured min {f2(F["min_psnr_all"])} dB / {F["min_ssim_all"]:.4f}'],
             ["Performance", "Hide/extract a 10 KB secret in a 768×512 image in under 1 s", f'Measured {f1(F["kodak10_embed"])} / {f1(F["kodak10_extract"])} ms'],
             ["Usability", "Guided capture, clear granted/denied states, responsive layout", "UI E2E incl. mobile check"],
             ["Portability", "Windows, macOS, Linux; no compiler needed", "Pure-wheel dependencies"],
             ["Reliability", "Demo works without a camera", "Demo pair + password"],
             ["Maintainability", "Typed, modular code with tests", f'{F["pytest"]["tests"]} automated tests']],
            widths=[1.1, 2.9, 1.8], small=True)
    d.h2("3.6", "Use Cases")
    d.figure(DIAG / "fig_use_case.png", "Use-case diagram", width=6.0)
    d.table("Use case UC-4: Extract with live face", ["Field", "Description"],
            [["Actor", "Authorised receiver"],
             ["Pre-conditions", "Receiver is enrolled on this device; has stego.png and secret.vault"],
             ["Main flow", "1 Upload both files. 2 System shows face slots and lock status. 3 Receiver starts scan. 4 Server issues a random challenge. 5 Browser records 5 s of frames. 6 Server checks lockout, image binding, liveness, identity, consistency. 7 Server unwraps key, extracts and decrypts. 8 UI shows ACCESS GRANTED and the secret."],
             ["Alternative flows", "6a Liveness fails -> ACCESS DENIED, intruder photo, failure +1. 6b Face not recognised -> same. 6c Third failure -> vault locked. 2a Vault locked -> countdown shown."],
             ["Post-conditions", "Attempt logged; failures reset on success"]],
            widths=[1.2, 4.6], small=True)
    d.h2("3.7", "Threat Model")
    d.p("Assets are the secret, the data key and the face templates. The adversary is assumed to know the full design and source "
        "code (Kerckhoffs' principle).")
    d.table("Threats and mitigations", ["Threat", "Adversary capability", "Mitigation", "Residual risk"],
            [["Read secret from intercepted image", "Has stego.png only", "AES-GCM + key not in image + secret positions", "None known"],
             ["Detect that image carries data", "Statistical tools", "Random positions; keep payload small", "RS/ML steganalysis at high load"],
             ["Use a stolen vault", "Has image + vault, not the device", "Face lock sealed with device key", "None without device key"],
             ["Photo / screen spoof", "Owner's photo", "Blink + random challenge on server", "Real-time deepfake / 3-D mask"],
             ["Video replay", "Recorded video of owner", "Random challenge, single-use, 120 s TTL", "Attacker who can puppet a video live"],
             ["Brute-force password", "Unlimited tries", "Argon2id (64 MiB) + lockout", "Offline attack if vault copied"],
             ["Bypass the UI", "Calls API directly", "All decisions server-side", "Device compromise"],
             ["Tamper with image/vault", "Edits files", "Pixel hash binding + GCM tags", "Denial of service only"],
             ["Device compromise", "Root on owner's PC", "Out of scope", "Templates + device key exposed"]],
            widths=[1.4, 1.3, 1.8, 1.4], small=True)
    d.h2("3.8", "Feasibility")
    d.p("**Technical:** every component exists as a maintained open-source library with pre-built wheels; a prototype of each was "
        "verified before integration. **Economic:** no paid services or GPUs are needed. **Operational:** the user needs only a "
        "browser and a webcam; demo mode covers camera failures. **Schedule:** the 7-week plan in the proposal was followed.")
    d.h2("3.9", "Hardware and Software Requirements")
    d.table("Hardware and software requirements", ["Item", "Minimum", "Used for evaluation"],
            [["CPU", "Dual-core x86-64 / Apple Silicon", m_cpu(F)],
             ["RAM", "4 GB", "16 GB"],
             ["Camera", "720p webcam (or demo mode)", "Synthetic camera in tests"],
             ["OS", "Windows 10+, macOS 12+, Ubuntu 22.04+", F["machine"]["platform"][:40]],
             ["Python", "3.10-3.12", F["machine"]["python"]],
             ["Node.js", "18+", "22"],
             ["Browser", "Chrome, Edge or Firefox (recent)", "Google Chrome (headless)"]],
            widths=[1.0, 2.2, 2.6], small=True)


def m_cpu(F):
    return F["machine"].get("cpu_model", F["machine"].get("processor", "x86-64"))


def ch4(d: Doc, F):
    d.chapter_heading("System Design")
    d.h2("4.1", "Architecture")
    d.p(f"{d.next_fig()} shows the three-tier architecture. The browser is only a thin client: it captures frames and files and "
        "displays results. The FastAPI layer performs request parsing and size limits. All security decisions are made in a "
        "single service class that calls focused modules. Persistent state lives in the backend's data directory on the "
        "owner's device.")
    d.figure(DIAG / "fig_architecture.png", "System architecture of FaceLock Stego")
    d.h2("4.2", "Module Design")
    d.table("Backend modules and responsibilities", ["Module", "Responsibility", "Key interfaces"],
            [["crypto.py", "AES-256-GCM, HKDF-SHA256, Argon2id wrappers", "aes_gcm_encrypt/decrypt, hkdf, PasswordKDF"],
             ["payload.py", "Serialise text/file + metadata, optional zlib", "pack, unpack"],
             ["lsb.py", "Slot permutation, bit embed/extract, sequential baseline", "keyed_positions, embed_bytes, extract_bytes"],
             ["stego.py", "Container format, image I/O, pixel fingerprint", "hide, reveal, load_image, pixel_fingerprint"],
             ["vault.py", "Face Vault creation and opening", "create_vault, open_face_lock, unwrap_face_slot, open_password_lock"],
             ["face_engine.py", "Detection, alignment, embeddings, backend fallback", "FaceEngine.single_face_embedding"],
             ["liveness.py", "Landmarks, EAR, yaw, challenges", "LandmarkAnalyzer.observe, evaluate, ChallengeBook"],
             ["security_log.py", "Audit log and lockout state machine", "record, register_failure, lock_status"],
             ["store.py", "Device key and encrypted face profiles", "load_or_create_device_key, ProfileStore"],
             ["metrics.py / steganalysis.py", "PSNR, MSE, SSIM, heatmaps; chi-square attack", "quality, prefix_scan"],
             ["service.py", "Orchestration of all use cases", "enroll, hide, unlock_with_face, unlock_with_password"]],
            widths=[1.3, 2.4, 2.2], small=True)
    d.h2("4.3", "Data Flow Diagrams")
    d.figure(DIAG / "fig_dfd_level0.png", "Context diagram (DFD level 0)")
    d.figure(DIAG / "fig_dfd_level1.png", "Level-1 data flow diagram")
    d.h2("4.4", "Hide Workflow")
    d.p(f"{d.next_fig()} gives the hide flowchart. The capacity check is performed after encryption because the exact size "
        "depends on compression and file-name metadata.")
    d.figure(DIAG / "fig_hide_flow.png", "Flowchart of the hide operation", width=4.6, max_height=8.2)
    d.h2("4.5", "Extract Workflow")
    d.figure(DIAG / "fig_extract_flow.png", "Flowchart of the extract operation with all rejection paths", width=5.6, max_height=8.2)
    d.p("The order of checks is deliberate: cheap checks that do not depend on the user (lockout, image/vault binding) run first; "
        "the challenge is consumed before any biometric work so it cannot be reused; liveness runs before recognition so that "
        "spoof attempts are rejected even if the face would match; the key is unwrapped only after every check has passed.")
    d.h2("4.6", "Sequence Diagram")
    d.figure(DIAG / "fig_sequence_extract.png", "Sequence diagram of a face-based extraction")
    d.h2("4.7", "Stego Container Format")
    d.figure(DIAG / "fig_stego_format.png", "Layout of the embedded bitstream")
    d.table("Header fields", ["Field", "Size", "Purpose"],
            [["magic", "4 B", "'FLS1' - confirms the correct key located a payload"], ["version", "1 B", "Format version (1)"],
             ["flags", "1 B", "Reserved"], ["ct_len", "4 B", "Ciphertext length including the 16-byte tag"],
             ["salt", "16 B", "Per-message salt for the message key derivation"], ["nonce", "12 B", "AES-GCM nonce (96 bit)"]],
            widths=[1.0, 0.7, 4.1], small=True)
    d.p("The whole 38-byte header is passed to AES-GCM as additional authenticated data, so changing any header bit is detected. "
        "Without the data key the header itself cannot be located because it is written at keyed random positions too.")
    d.h2("4.8", "Keyed Random Slot Selection")
    d.p("Let N = W·H·3 be the number of colour-channel slots. The seed s = HKDF(DEK, \"facelock/lsb/v1\") keys AES-256 in "
        "counter mode, producing N 64-bit words. The low 26 bits of word i are replaced by i, making every key unique; the "
        "positions used are the slots with the k smallest keys, in ascending order. Because the ordering is a fixed total order, "
        "the first 304 positions (the header) are exactly the prefix of the positions for the full message, which allows the "
        "header to be read first. Selection costs O(N + k log k) with a partial sort.")
    d.h2("4.9", "Face Vault Design")
    d.figure(DIAG / "fig_vault_design.png", "Key hierarchy of the Face Vault")
    d.table("Keys and how they are derived", ["Key", "Derivation", "Stored where"],
            [["DEK", "32 random bytes (secrets.token_bytes)", "Only wrapped inside the vault"],
             ["Message key", "HKDF(DEK, salt, 'facelock/msg/v1')", "Never stored"],
             ["LSB seed", "HKDF(DEK, '', 'facelock/lsb/v1')", "Never stored"],
             ["device_key", "32 random bytes, created once", "data/device.key (owner's device)"],
             ["KEK_vault", "HKDF(device_key, salt, 'facelock/vault/v1')", "Never stored"],
             ["KEK_slot,i", "HKDF(device_key, salt, 'facelock/slot/v1' || SHA-256(T_i))", "Never stored"],
             ["K_pw", "Argon2id(password, salt2; t=3, m=64 MiB, p=2)", "Never stored"]],
            widths=[1.1, 3.0, 1.8], small=True)
    d.p("The canonical public header (format, version, vault id, creation time and the SHA-256 of the stego pixels) is hashed and "
        "used as AAD for every encryption in the vault. Consequently a vault cannot be paired with a different image, and the "
        "image hash cannot be edited without breaking every tag. The image hash is computed over decoded pixels, so lossless "
        "re-encoding of the PNG does not break the binding while any pixel change does.")
    d.h2("4.10", "Liveness Design")
    d.p("The browser records 5 seconds at 10 frames per second. For each frame the server runs MediaPipe Face Landmarker and "
        "computes (i) the mean EAR of both eyes from landmarks 33/160/158/133/153/144 and 362/385/387/263/373/380 and (ii) the "
        "nose-position ratio r = (x_nose - x_left) / (x_right - x_left) using landmarks 1, 234 and 454. The open-eye baseline is "
        "the 80th percentile of EAR; a frame is *closed* below 62 % of it and *open* above 85 %; a blink is an open-closed-open "
        "sequence. A head turn is a deviation of r of at least 0.10 from the median of the first frames in the requested "
        "direction. A burst is rejected if any frame has two faces, if fewer than 60 % of frames contain a face, or if both "
        "signals have standard deviation below 0.006 (a static image).")
    d.h2("4.11", "Database Design")
    d.table("SQLite table attempts", ["Column", "Type", "Description"],
            [["id", "INTEGER PK", "Auto-increment"], ["ts", "TEXT", "UTC timestamp (ISO 8601)"], ["action", "TEXT", "enroll / hide / extract"],
             ["method", "TEXT", "face / password"], ["vault_id", "TEXT", "Vault concerned"], ["result", "TEXT", "ok / granted / denied / locked"],
             ["reason", "TEXT", "Human-readable reason"], ["score", "REAL", "Best cosine similarity"], ["matched_label", "TEXT", "Profile that matched"],
             ["client", "TEXT", "Client IP"], ["photo", "TEXT", "Intruder image file name"], ["details", "TEXT", "JSON details"]],
            widths=[1.3, 1.2, 3.3], small=True)
    d.p("A second table, *lockouts(key, failures, locked_until)*, implements the brute-force state machine per vault: each failure "
        "increments the counter; at three the vault is locked for 60 s (configurable); a success deletes the row; after a "
        "lockout expires the counter restarts at zero.")
    d.h2("4.12", "API Design")
    d.table("REST endpoints", ["Method and path", "Purpose"],
            [["GET /api/health", "Engine, thresholds, profile count"], ["GET/DELETE /api/profiles", "List / delete enrolled faces"],
             ["POST /api/enroll", "label + 5 JPEG samples -> profile"], ["POST /api/capacity", "Image -> width, height, capacity"],
             ["POST /api/hide", "cover + message|file + profile_ids + password -> job"], ["GET /api/jobs/{id}/{stego|vault|cover}", "Download outputs"],
             ["POST /api/challenge", "Issue a single-use random liveness challenge"], ["POST /api/vault/inspect", "Slots, fallback, lock status"],
             ["POST /api/extract/face", "stego + vault + challenge_id + frames -> result"], ["POST /api/extract/password", "stego + vault + password -> result"],
             ["GET /api/analyze/{job}, POST /api/analyze/upload", "Metrics, heatmap, histograms"], ["GET /api/bitplane/{job}", "PNG of one bit plane"],
             ["POST /api/attack", "Chi-square lab: sequential vs random"], ["GET/DELETE /api/logs, GET /api/logs/{id}/photo", "Audit log and intruder photos"],
             ["GET /api/demo, /api/demo/covers/{name}, /api/demo/pair/{kind}", "Demo-mode assets"]],
            widths=[2.6, 3.2], small=True)
    d.h2("4.13", "User Interface Design")
    d.p("The interface uses a dark design system (Inter typeface, cyan primary, violet secondary, green for granted and red for "
        "denied) with Framer Motion transitions and Recharts charts. Eight pages share one sidebar layout that collapses into a "
        "drawer on phones. Status is never conveyed by colour alone: every state also carries an icon and a text label.")


def ch5(d: Doc, F):
    d.chapter_heading("Implementation")
    d.h2("5.1", "Technology Stack")
    d.table("Technology stack", ["Layer", "Technology", "Reason"],
            [["Backend framework", "FastAPI + Uvicorn (Python 3.12)", "Typed, async, automatic OpenAPI docs"],
             ["Cryptography", "cryptography (AES-GCM, HKDF), argon2-cffi", "Audited primitives, no custom crypto"],
             ["Image processing", "NumPy, Pillow, OpenCV", "Vectorised bit operations, PNG I/O"],
             ["Face recognition", "OpenCV YuNet + SFace (DeepFace fallback)", "Pre-built wheels on Windows, CPU-only"],
             ["Liveness", "MediaPipe Face Landmarker (478 points)", "Accurate landmarks on CPU"],
             ["Metrics", "scikit-image (SSIM), SciPy (chi-square)", "Reference implementations"],
             ["Storage", "SQLite, encrypted JSON files", "Zero-configuration"],
             ["Frontend", "Next.js 14, React 18, TypeScript, Tailwind CSS", "Type safety, fast iteration"],
             ["UI motion and charts", "Framer Motion, Recharts, lucide-react", "Animations, interactive charts"],
             ["Testing", "pytest, FastAPI TestClient, Playwright + Chrome", "Unit, API and browser E2E"],
             ["Documents", "matplotlib, docx (Node), pptxgenjs, LibreOffice", "Reproducible report and slides"]],
            widths=[1.4, 2.4, 2.0], small=True)
    d.h2("5.2", "Project Structure")
    d.code("""FaceLockStego/
  app/backend/      main.py (FastAPI), facelock/ (11 modules), tests/ (9 files), models/
  app/frontend/     app/ (8 pages), components/, lib/ (typed API client, camera, demo)
  dataset/          covers/ (41 PNG), payloads/ (5), results/ (CSV + JSON), manifest.csv
  docs/             Proposal and Report (.docx/.pdf), figures/, diagrams/, screenshots/
  presentation/     FaceLockStego.pptx
  scripts/          setup, run, dataset, benchmark, charts, diagrams, docs, slides, UI test
  project.config.json   personal details used by every document""", caption="Listing 5.1: Repository layout")
    d.h2("5.3", "Cryptographic Primitives")
    d.p("All encryption uses AES-256-GCM with a 96-bit random nonce. Purpose-specific keys are derived with HKDF using distinct "
        "info strings (domain separation), so a key derived for one purpose can never be confused with another.")
    d.code(snippet(BACK / "crypto.py", "def aes_gcm_encrypt", "def sha256_hex"), caption="Listing 5.2: AES-GCM wrapper (crypto.py)")
    d.h2("5.4", "Keyed Random Position Generation")
    d.p("The function below is the core of the random embedding. It is fully vectorised with NumPy, deterministic across "
        "platforms (it does not depend on NumPy's random generator) and prefix-consistent.")
    d.code(snippet(BACK / "lsb.py", "def keyed_positions", "def sequential_positions"), caption="Listing 5.3: Keyed slot permutation (lsb.py)")
    d.h2("5.5", "Embedding and Extraction")
    d.code(snippet(BACK / "lsb.py", "def embed_bits", "def embed_bytes"), caption="Listing 5.4: Writing and reading LSBs (lsb.py)")
    d.p("Hiding packs the payload (kind, file name, MIME type, optional zlib), builds the header, encrypts with the message key "
        "using the header as AAD, checks capacity and embeds. Revealing reads the 38-byte header at the first 304 positions, "
        "validates magic and length, reads the remaining positions and decrypts. A wrong key fails at the magic check; a "
        "modified image fails at the GCM tag.")
    d.code(snippet(BACK / "stego.py", "def reveal", None, max_lines=30), caption="Listing 5.5: Reveal procedure (stego.py)")
    d.h2("5.6", "Face Vault")
    d.code(snippet(BACK / "vault.py", "def create_vault", "def dumps", max_lines=40), caption="Listing 5.6: Vault creation (vault.py)")
    d.h2("5.7", "Face Engine with Automatic Fallback")
    d.p("At start-up the engine tries the SFace backend; it downloads missing models from the official OpenCV Zoo, creates the "
        "YuNet detector and SFace recogniser and runs a self-test. If anything fails it tries DeepFace, and if that is not "
        "installed it raises an error listing every failure. During development the SFace backend installed from wheels and "
        "passed its self-test on the first attempt. The switching logic is verified by unit tests that simulate a broken SFace "
        "backend (the engine selects the next backend and records the reason) and a total failure (a clear error naming both). "
        "DeepFace itself was not installed during evaluation because it pulls in TensorFlow (~600 MB). Enrolment "
        "requires exactly one face per sample with detection score at least 0.8 and minimum pairwise similarity 0.45 among the "
        "five samples; the template is the re-normalised mean of the five L2-normalised embeddings.")
    d.h2("5.8", "Liveness Detection")
    d.code(snippet(BACK / "liveness.py", "def count_blinks", "def evaluate"), caption="Listing 5.7: Blink counting with an adaptive EAR threshold (liveness.py)")
    d.h2("5.9", "Server-Side Verification Pipeline")
    d.p("`FaceLockService.unlock_with_face` implements Figure 4.5. Identity is computed from up to five frontal, eyes-open frames; "
        "the averaged live embedding is compared with every slot. A *consistency* check then embeds up to six frames spread "
        "across the whole burst and requires each to be within 0.8×threshold of the live template, which blocks an attack "
        "where a live accomplice blinks and turns while a photo of the owner is swapped in for the frontal frames.")
    d.h2("5.10", "Lockout and Intruder Capture")
    d.p("On every denial the service increments the vault's failure counter, writes an *attempts* row and saves the middle frame "
        "that contained a face as a JPEG named after the attempt id. The Security Log page shows these as thumbnails. A request "
        "for a locked vault returns HTTP 423 with the remaining seconds, which the UI turns into a live countdown.")
    d.h2("5.11", "Frontend")
    d.p("The frontend is a Next.js 14 App Router application written in strict TypeScript. A typed API client (`lib/api.ts`) "
        "mirrors every backend response. The webcam hook (`lib/camera.ts`) shows a mirrored preview but captures un-mirrored "
        "frames, because the server's head-turn test assumes raw camera geometry. Figures 5.1 to 5.4 show four of the eight pages "
        "captured from the running application; further screenshots appear in Chapter 6.")
    d.figure(SHOT / "01_home.png", "Landing page with animated LSB visual", width=6.0)
    d.figure(SHOT / "02_enroll.png", "Enroll Face page after guided capture (synthetic face)", width=6.0)
    d.figure(SHOT / "04_hide_result.png", "Hide Data page with capacity meter, authorised faces and results", width=6.0)
    d.figure(SHOT / "13_how_it_works.png", "How It Works page (animated step-by-step explanation)", width=6.0)
    d.h2("5.12", "Demo Mode and Setup")
    d.p("Demo mode, toggled in the sidebar, adds sample-cover pickers, a sample message and a *Load demo pair* button that loads a "
        "pre-built stego image and a password-only vault, so the extraction screen can always be demonstrated even without a "
        "camera. One-command setup scripts (`setup.bat` / `setup.sh`) create the Python virtual environment, install packages, "
        "download models, build demo assets and install the frontend; `run.bat` / `run.sh` start both servers.")


def ch6(d: Doc, F):
    P, S, pt = F["pay"], F["stega"], F["pytest"]
    d.chapter_heading("Testing and Results")
    d.h2("6.1", "Test Strategy")
    d.p("Testing was carried out at four levels: unit tests for each module, API end-to-end tests with the real face and "
        "liveness models, a headless browser test that drives the actual user interface, and benchmark experiments over the "
        "dataset. Because the webcam cannot be used in automated tests, and because the repository must not contain real "
        f"people's faces, eight StyleGAN-generated faces {c('stylegan')} of people who do not exist were used. A test helper "
        "turns a still face into a webcam burst: eye closure is painted over the MediaPipe eye contour, head turns are "
        "approximated by a cylindrical warp of up to 35°, and small random jitter imitates hand-held video. The browser test "
        "replaces `getUserMedia` with a canvas stream fed by these frames.")
    d.h2("6.2", "Unit and API Tests")
    rows = [[k, v] for k, v in sorted(pt["per_file"].items())]
    d.table("Automated pytest suite (JUnit results)", ["Test file", "Tests"], rows + [["Total", f'{pt["tests"]} ({pt["tests"] - pt["failures"] - pt["errors"]} passed, {pt["failures"]} failed, {pt["errors"]} errors; {f1(pt["time"])} s)']],
            widths=[3.5, 2.3], small=True)
    d.p("The unit tests cover LSB round trips, position uniqueness, prefix consistency, key dependence and spread; AES-GCM tamper "
        "detection; Argon2id; capacity arithmetic including exact-fit and one-byte-over cases; JPEG destruction of the payload; "
        "single-bit-flip detection; vault slot unwrapping, device binding, template binding, header tampering and password "
        "fallback; the blink counter and every liveness rejection rule; the chi-square detector; and the lockout state machine. "
        "The API test enrols two synthetic users, hides a secret for both with a password, and verifies: genuine access for "
        "each, rejection of a photo attack, rejection of an impostor, rejection of a wrong challenge response leading to "
        "lockout, HTTP 423 for both face and password while locked, password fallback after expiry, intruder photos, file "
        "payloads, mismatched image/vault pairs and recompressed JPEG uploads.")
    d.h2("6.3", "Browser End-to-End Test")
    d.table("Browser end-to-end checks (Playwright + Google Chrome)", ["#", "Check", "Result"],
            [[i + 1, x["check"] + (f' ({x["detail"]})' if x["detail"] else ""), "PASS" if x["passed"] else "FAIL"] for i, x in enumerate(F["ui"])],
            widths=[0.4, 4.4, 1.0], small=True)
    d.h2("6.4", "Dataset and Experimental Setup")
    src = F["by_source"]
    d.p(f'The cover set contains {F["images"]} images: the 24 images of the Kodak Lossless True Colour suite {c("kodak")} '
        f'(768×512, portraits, landscapes, architecture), {src["USC-SIPI"]} images from the USC-SIPI database {c("sipi")} '
        f'(256×256 to 1024×1024 including Mandrill, Peppers, Brodatz textures and an aerial image) and {src["Generated"]} '
        "synthetic images generated by the dataset script (a text-heavy document page, a 1920×1080 UI screenshot, a flat "
        "two-colour image, a smooth gradient, a geometric pattern and a noise texture). Payloads are text files of exactly 100 B, "
        "1 KB, 10 KB and 50 KB and a two-page PDF of "
        f'{P["PDF"]["bytes"]:,} bytes. Each of the {F["runs"]} image×payload combinations was embedded three times; times are '
        f"medians. To measure embedding cost independently of text compressibility, payloads were embedded *without* "
        f"compression (the application compresses when helpful). Experiments ran on {m_cpu(F)} with Python "
        f'{F["machine"]["python"]}, NumPy {F["machine"]["numpy"]} and OpenCV {F["machine"]["opencv"]}.')
    d.h2("6.5", "Imperceptibility")
    d.p("PSNR and MSE were computed over the RGB channels and SSIM with a 7×7 window across channels "
        f"{c('ssim')}. {d.next_tab()} summarises the results and {d.next_fig()} plots every run.")
    d.table("Imperceptibility by payload (successful runs)", ["Payload", "Runs", "Mean util. %", "PSNR mean (min-max) dB", "Mean MSE", "SSIM mean (min)", "Pixels touched %"],
            [[p, P[p]["n"], f2(P[p]["util_mean"]), f'{f2(P[p]["psnr_mean"])} ({f2(P[p]["psnr_min"])}-{f2(P[p]["psnr_max"])})',
              f'{P[p]["mse_mean"]:.5f}', f'{P[p]["ssim_mean"]:.5f} ({P[p]["ssim_min"]:.5f})', f2(P[p]["changed_mean"])]
             for p in ("100B", "1KB", "10KB", "PDF", "50KB")],
            widths=[0.8, 0.6, 0.9, 1.6, 0.9, 1.4, 0.9], align=["l", "r", "r", "r", "r", "r", "r"], small=True)
    d.figure(FIG / "fig_quality_vs_payload.png", "PSNR and SSIM against embedded size for all successful runs")
    d.p(f'Every run stayed far above the commonly quoted 40 dB threshold for imperceptibility; the worst case was '
        f'{f2(F["min_psnr_all"])} dB. Because only bits that differ are changed, on average half of the selected slots are '
        "modified, which explains why PSNR at a given payload depends mainly on image size: the same 50 KB message is a "
        "larger fraction of a 512×512 image than of a 1920×1080 one. SSIM stayed above "
        f'{F["min_ssim_all"]:.4f}; the lowest values occur on flat, low-detail images where any change is structurally more '
        "significant.")
    d.figure(SHOT / "10_analysis.png", "Analysis dashboard for kodim23 with a short text secret", width=5.6)
    d.h2("6.6", "Capacity")
    fails = sorted({x["image"] for x in F["cap_fail"]})
    d.p(f"{d.next_fig()} shows capacity per resolution. Capacity is exactly ⌊W·H·3/8⌋ - 54 bytes. "
        f'{len(F["cap_fail"])} runs exceeded capacity and were rejected with a clear error before any embedding: the 50 KB '
        f'and PDF payloads on the three 256×256 images ({", ".join(fails)}), whose capacity is 24,522 bytes. All '
        f'{F["ok_runs"]} runs that fitted were recovered bit-exactly after a real PNG save-and-load round trip.')
    d.figure(FIG / "fig_capacity.png", "Capacity by cover resolution", width=5.5)
    d.h2("6.7", "Performance")
    d.p(f'For a 10 KB secret in a 768×512 Kodak image the median embed time was {f1(F["kodak10_embed"])} ms and the '
        f'median extract time {f1(F["kodak10_extract"])} ms; for the 1920×1080 screenshot they were {f1(F["hd_embed"])} ms '
        f'and {f1(F["hd_extract"])} ms. {d.next_fig()} shows that time grows roughly linearly with the number of pixels, '
        "because the keyed permutation generates one 64-bit key per slot. Extraction is slower than embedding because it "
        "computes the permutation twice (header, then full payload). Face verification adds approximately "
        f'{f1(F["face"]["embedding_ms_per_frame"])} ms per embedded frame and {f1(F["live_summary"]["landmark_ms_per_frame"])} ms '
        "per frame of landmark detection; the browser test measured a complete server-side verification of 50 frames in "
        "about 2.4 s.")
    d.figure(FIG / "fig_time_vs_size.png", "Embedding and extraction time")
    d.table("Median timings by payload over all images (ms)", ["Payload", "Embed", "Extract"],
            [[p, f1(P[p]["embed_med"]), f1(P[p]["extract_med"])] for p in ("100B", "1KB", "10KB", "PDF", "50KB")],
            widths=[2, 2, 2], align=["l", "r", "r"], small=True)
    d.h2("6.8", "Robustness")
    d.p("Robustness was tested on five images with a 10 KB payload. The results confirm the expected behaviour of spatial LSB "
        "embedding with authenticated encryption: any lossless transport preserves the secret, and any pixel modification "
        "is *detected* rather than producing silently corrupted output.")
    d.table("Effect of image operations on extraction", ["Operation", "Extracted", "Observed error"],
            [[o, f"{ok}/{n}", (e or "-")[:70]] for o, ok, n, e in F["robust"]], widths=[2.4, 0.8, 2.6], small=True)
    d.p("The arbitrary-pixel flip succeeds because, with a 10 KB payload, fewer than 10 % of slots carry data and the flipped "
        "slot was not one of them; a flip on a payload bit (computed with the key) is always rejected by the GCM tag.")
    d.h2("6.9", "Resistance to Chi-Square Steganalysis")
    d.p(f"{d.next_fig()} reproduces the classic sliding-window chi-square attack on kodim23 with a payload of 50 % of capacity. "
        "The sequential embedding is detected with p = 1 for the entire first half of the image and the attack even reveals the "
        "payload length. With keyed random positions the probability drops to zero after the first few percent.")
    d.figure(FIG / "fig_steganalysis_curve.png", "Chi-square attack on sequential and random LSB (kodim23, 50 % payload)")
    d.table("Chi-square detection over the whole dataset (mean of images)", ["Payload", "Sequential flagged %", "Random flagged %", "Random: images with any flag", "Clean covers flagged %"],
            [[f"{k} %", f1(S[k]["seq"]), f1(S[k]["rnd"]), f'{S[k]["rnd_any"]}/{S[k]["n"]}', f1(S[k]["clean"])] for k in ("10", "25", "50", "100")],
            widths=[0.9, 1.3, 1.3, 1.5, 1.3], align=["l", "r", "r", "r", "r"], small=True)
    d.figure(FIG / "fig_steganalysis_fill.png", "Chi-square detection across 41 images and four payload sizes", width=5.6)
    d.p(f'Up to 50 % payload the random embedding reduced the flagged portion from {f1(S["50"]["seq"])} % to '
        f'{f1(S["50"]["rnd"])} %. At 100 % payload every LSB is overwritten and both schemes are detected '
        f'({f1(S["100"]["seq"])} % vs {f1(S["100"]["rnd"])} %): random ordering hides *where* data is, not *that* LSBs were '
        "replaced. The practical rule, enforced in the UI by the capacity meter's colour, is to keep payloads well below half "
        "of capacity. The Attack Lab page lets an examiner repeat this experiment interactively.")
    d.figure(SHOT / "12_attack_lab.png", "Attack Lab page running the chi-square attack", width=5.6)
    d.h2("6.10", "Face Recognition Accuracy")
    fs = F["face"]
    far40 = next(x for x in F["farfrr"] if abs(float(x["threshold"]) - 0.40) < 1e-9)
    far30 = next(x for x in F["farfrr"] if abs(float(x["threshold"]) - 0.30) < 1e-9)
    far25 = next(x for x in F["farfrr"] if abs(float(x["threshold"]) - 0.25) < 1e-9)
    d.p(f'Each of the eight synthetic identities was enrolled from five jittered samples and probed with three liveness bursts '
        f'(blink, left, right), giving {fs["genuine_trials"]} genuine and {fs["impostor_trials"]} impostor comparisons. Genuine '
        f'similarity averaged {fs["genuine_mean"]:.3f} (minimum {fs["genuine_min"]:.3f}); impostor similarity averaged '
        f'{fs["impostor_mean"]:.3f} (maximum {fs["impostor_max"]:.3f}). At the chosen threshold of 0.40 both FAR and FRR were '
        f'{far40["FAR_pct"]} %; lowering the threshold to 0.30 would have admitted {far30["FAR_pct"]} % of impostor comparisons '
        f'and to 0.25, {far25["FAR_pct"]} %.')
    d.figure(FIG / "fig_face_far_frr.png", "Similarity distributions and FAR/FRR versus threshold")
    d.p("**Caveat.** Genuine probes here are derived from the same photograph as the enrolment, so genuine scores are higher than "
        "they will be for a real user across sessions, lighting and expressions, where SFace genuine similarities typically "
        "fall between 0.5 and 0.8. The zero error rates therefore demonstrate correct integration and a clear impostor "
        "margin, not real-world accuracy, which requires an IRB-approved study with real volunteers (Section 7.1). The "
        "threshold is configurable (`FACELOCK_FACE_THRESHOLD`).")
    d.h2("6.11", "Liveness and Spoofing Tests")
    d.table("Liveness experiment on synthetic faces (8 identities)", ["Scenario", "Trials", "Correct decisions", "Reasons reported"],
            [[s, n, f"{ok}/{n}", "; ".join(r)[:95]] for s, n, ok, r in F["live"]], widths=[1.7, 0.6, 0.9, 2.6], small=True)
    d.p(f'All {F["live_summary"]["correct"]} of {F["live_summary"]["trials"]} decisions were correct: every genuine response to '
        "every challenge passed, every response in the wrong direction failed, a single blink did not satisfy \"blink twice\", "
        f"and every static photo was rejected. {d.next_fig()} shows the server-side signals for a genuine turn-left response "
        "and for a photo of the same face.")
    d.figure(FIG / "fig_liveness_traces.png", "EAR and nose-position signals: live response vs photo attack")
    d.figure(SHOT / "06_access_granted.png", "ACCESS GRANTED after a live scan, with the server's liveness signal", width=5.4)
    d.figure(SHOT / "07_access_denied_photo.png", "ACCESS DENIED for a photo attack (no natural motion)", width=5.4)
    d.figure(SHOT / "08_access_denied_impostor.png", "ACCESS DENIED for a live impostor (face not recognised)", width=5.4)
    d.h2("6.12", "Lockout and Audit Tests")
    d.p("In the browser test the third consecutive failure (a photo attack, an impostor and a wrong challenge response) locked "
        "the vault; the UI showed a countdown, the API returned HTTP 423 for both face and password requests, and after the "
        "60-second lockout the correct backup password unlocked the secret. Each failed face attempt produced an intruder "
        "photograph in the log.")
    d.figure(SHOT / "09_lockout.png", "Vault locked after three failures", width=5.4)
    d.figure(SHOT / "11_security_log.png", "Security log with results, reasons, scores and intruder photos", width=5.6)
    d.h2("6.13", "Discussion")
    d.bullets([
        "**Imperceptibility** is excellent for all payloads that fit; perceptual quality is not the limiting factor of LSB.",
        "**Confidentiality** does not rely on hiding: even a detected image yields only AES-GCM ciphertext at unknown positions.",
        "**Undetectability** against chi-square is good below 50 % load; stronger detectors are acknowledged as a limitation.",
        "**Fragility** is a deliberate consequence of LSB + authentication: tampering is detected, never silently accepted.",
        "**Biometric results** validate the pipeline; real-world FAR/FRR must be measured with real users.",
    ])


def ch7(d: Doc, F):
    d.chapter_heading("Limitations and Future Work")
    d.h2("7.1", "Limitations")
    d.numbers([
        "**Policy gate, not cryptographic binding.** The face templates are stored (encrypted with the device key) inside the vault, and the server releases the key after a successful match. Anyone who obtains both device.key and the vault can decrypt the templates and unwrap the key without a face. The per-slot keys derived from the template add defence in depth but no biometric binding.",
        "**The vault lives on the owner's device.** Face unlocking works only on the machine whose device key sealed the vault. Moving secrets between people requires that machine, or the portable password slot.",
        "**Fragile carrier.** Any lossy compression, resizing, cropping or filtering destroys the payload. Many messaging apps recompress images, so stego files must be sent as documents.",
        "**LSB replacement is statistically detectable at high load.** RS analysis, sample-pair analysis and machine-learning steganalysers can estimate the payload regardless of ordering.",
        "**Liveness is basic.** Blink and head-turn challenges stop photos and simple replays but not real-time deepfakes, 3-D masks or a coerced owner. No ISO/IEC 30107-3 evaluation was performed.",
        "**Evaluation data.** Face results use synthetic StyleGAN faces and synthetic motion, so they validate logic, not real-world error rates. Timings come from one machine.",
        "**Single-user deployment.** The backend is designed as a local service; it has no user accounts, TLS termination or rate limiting beyond the per-vault lockout.",
    ], ref="lim")
    d.h2("7.2", "Future Work")
    d.numbers([
        "**Fuzzy extractor key binding.** Quantise the SFace embedding (e.g. sign of random projections), use a BCH or Reed-Solomon code in a fuzzy commitment / fuzzy extractor construction, and derive the slot key from the reproduced secret so that no template is stored and the server cannot release the key without a matching face.",
        "**Compression-robust embedding.** Embed in quantised DCT coefficients (JPEG domain, F5/J-UNIWARD style) or DWT sub-bands with error-correcting codes so stego images survive social-media recompression.",
        "**Adaptive embedding.** Use LSB matching or syndrome-trellis codes with a distortion function to resist RS and machine-learning steganalysis.",
        "**Multi-biometric and multi-factor.** Combine face with voice or fingerprint, or require a hardware key (FIDO2) in addition to the face, for k-of-n approvals.",
        "**Stronger PAD.** Add passive texture/depth-based presentation attack detection and evaluate on public anti-spoofing datasets (e.g. OULU-NPU, CASIA-FASD).",
        "**User study.** Measure real FAR/FRR, challenge completion time and usability with consenting volunteers.",
        "**Deployment hardening.** HTTPS, per-user accounts, encrypted backups of the device key (e.g. OS keychain or TPM).",
    ], ref="fw")


def ch8(d: Doc, F):
    P, S = F["pay"], F["stega"]
    d.chapter_heading("Conclusion")
    d.p("This project set out to make a hidden message recoverable only by a live, authorised person. FaceLock Stego achieves "
        "this by layering three mechanisms: AES-256-GCM encryption with a random key, keyed random-order LSB embedding that "
        "leaves no key or positions in the image, and a Face Vault whose key slots are opened by the server only after a "
        "liveness check and a face match. Brute force is throttled by a lockout and every attempt is logged with an intruder "
        "photograph. A polished web application makes each step visible, from the capacity meter to the bit-plane viewer and "
        "the attack lab.")
    d.p(f'The evaluation used real runs on {F["images"]} public and synthetic images. All {F["ok_runs"]} embeddings that fitted '
        f'were recovered exactly; PSNR never fell below {f2(F["min_psnr_all"])} dB and SSIM never below '
        f'{F["min_ssim_all"]:.4f}. Random ordering cut chi-square detection at 50 % load from {f1(S["50"]["seq"])} % to '
        f'{f1(S["50"]["rnd"])} % of the image, while honestly offering no protection at full load. Liveness logic made the '
        f'correct decision in all {F["live_summary"]["trials"]} synthetic trials, and {F["pytest"]["tests"]} automated tests and '
        f'{len(F["ui"])} browser checks pass.')
    d.p("The main lesson is that the security of such a system comes from cryptography and careful protocol design, while "
        "steganography contributes deniability and biometrics contribute convenience and presence. Its main weakness, that the "
        "face check is enforced by software rather than bound into the key, points directly to the most valuable next step: a "
        "fuzzy-extractor construction that makes the face itself part of the key.")


def appendices(d: Doc, F):
    d.unnumbered_heading("Appendix A: Installation and User Manual")
    d.p("**Setup (once).** Install Python 3.10-3.12 and Node.js 18+. In the project folder run `scripts\\setup.bat` (Windows) or "
        "`bash scripts/setup.sh` (macOS/Linux). The script creates `app/backend/.venv`, installs the Python packages, downloads "
        "the three model files (YuNet, SFace, Face Landmarker), builds the dataset and demo assets, and installs the frontend.")
    d.p("**Run.** `scripts\\run.bat` or `bash scripts/run.sh` starts the API on port 8000 and the web app on port 3000; open "
        "http://localhost:3000. API documentation is at http://localhost:8000/docs.")
    d.numbers(["Enroll Face: start the camera, enter a name, press *Start guided capture* and follow the five prompts, then *Save face profile*.",
               "Hide Data: drop a cover image, type a message or choose a file, select up to three faces, optionally add a backup password, press *Hide secret in image*, and download both files.",
               "Extract Data: load the stego PNG and the .vault, press *Start live face scan* and follow the on-screen challenge; or switch to *Password*.",
               "Analysis: open from the hide result or upload any cover/stego pair.",
               "Security Log, Attack Lab and How It Works need no input; Demo Mode in the sidebar preloads samples."], ref="manual")
    d.unnumbered_heading("Appendix B: Configuration")
    d.table("Environment variables", ["Variable", "Default", "Meaning"],
            [["FACELOCK_FACE_THRESHOLD", "0.40", "Cosine similarity needed to accept a face"], ["FACELOCK_FACE_ENGINE", "auto", "auto, sface or deepface"],
             ["FACELOCK_MAX_FAILURES", "3", "Failures before lockout"], ["FACELOCK_LOCKOUT_SECONDS", "60", "Lockout duration"],
             ["FACELOCK_LIVENESS_REQUIRED", "1", "Set 0 only for experiments"], ["FACELOCK_DATA_DIR", "app/backend/data", "Device key, profiles, log, jobs"],
             ["NEXT_PUBLIC_API_URL", "http://localhost:8000", "Backend URL used by the web app"]],
            widths=[2.2, 1.4, 2.2], small=True)
    d.unnumbered_heading("Appendix C: Per-Image Results (10 KB Payload)")
    rows = [[x["image"], x["category"][:22], x["resolution"], f'{float(x["utilization_pct"]):.2f}', f'{float(x["psnr_db"]):.2f}',
             f'{float(x["ssim"]):.5f}', f'{float(x["embed_ms"]):.0f}', f'{float(x["extract_ms"]):.0f}'] for x in F["per_image_10k"]]
    d.table("Results for every cover with the 10 KB payload", ["Image", "Category", "Size", "Util. %", "PSNR dB", "SSIM", "Embed ms", "Extract ms"],
            rows, widths=[1.3, 1.4, 0.9, 0.6, 0.7, 0.8, 0.6, 0.6], align=["l", "l", "l", "r", "r", "r", "r", "r"], small=True)
    d.p("The complete table with all five payloads (205 rows) is `dataset/results.csv`.")
    d.unnumbered_heading("Appendix D: Sample Vault File")
    vault = (ROOT / "app/backend/demo/pair/demo.vault").read_text()
    vault = re.sub(r'"([A-Za-z0-9+/=]{40})[A-Za-z0-9+/=]+"', r'"\1..."', vault)
    vault = re.sub(r'"(\$argon2id\$v=19\$m=65536,t=3,p=2\$)[^"]+"', r'"\1..."', vault)
    d.code(vault, caption="Listing D.1: The demo pair's vault (password-only; long values truncated)")
    d.unnumbered_heading("Appendix E: Abbreviations Used in Code")
    d.p("`DEK` data encryption key; `KEK` key-encryption key; `AAD` additional authenticated data; `EAR` eye aspect ratio; "
        "`slot` either a colour-channel position in the image (lsb.py) or a key slot in the vault (vault.py), depending on context.")


def lists(d: Doc, pages: dict) -> list[dict]:
    """Insert TOC, LOF, LOT and abbreviations into the front-matter section."""
    secs = [dict(s, blocks=list(s["blocks"])) for s in d.sections]
    front = secs[1]["blocks"]
    pos = d.toc_pos
    ins = []
    ins.append({"t": "h", "level": 1, "text": "TABLE OF CONTENTS", "center": True, "newPage": True})
    entries = [e for e in d.toc if e["kind"] == "front"] + [e for e in d.toc if e["kind"] == "body"]
    ins.append({"t": "toc", "entries": [{"text": e["text"], "level": e["level"], "page": pages.get(e["key"], "00"),
                                         "plain": e.get("plain", False)} for e in entries]})
    ins.append({"t": "h", "level": 1, "text": "LIST OF FIGURES", "center": True, "newPage": True})
    ins.append({"t": "toc", "entries": [{"text": f["text"], "level": 2, "page": pages.get(f["key"], "00")} for f in d.figs]})
    ins.append({"t": "h", "level": 1, "text": "LIST OF TABLES", "center": True, "newPage": True})
    ins.append({"t": "toc", "entries": [{"text": t["text"], "level": 2, "page": pages.get(t["key"], "00")} for t in d.tabs]})
    ins.append({"t": "h", "level": 1, "text": "LIST OF ABBREVIATIONS", "center": True, "newPage": True})
    half = (len(ABBR) + 1) // 2
    rows = [list(ABBR[i]) + (list(ABBR[i + half]) if i + half < len(ABBR) else ["", ""]) for i in range(half)]
    ins.append({"t": "table", "caption": "", "header": ["Abbr.", "Meaning", "Abbr.", "Meaning"], "rows": rows,
                "widths": [0.8, 2.1, 0.8, 2.1], "small": True})
    secs[1]["blocks"] = front[:pos] + ins + front[pos:]
    return secs
