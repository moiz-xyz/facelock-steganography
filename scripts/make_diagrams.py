"""Draw the system-design diagrams used in the report and presentation (docs/figures/diagrams/).

    python scripts/make_diagrams.py

Pure matplotlib (no Graphviz needed) so it runs anywhere the backend runs.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Ellipse  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "figures" / "diagrams"
INK, INK2 = "#1d1d1b", "#52514e"
P = {  # fill, edge
    "blue": ("#e8f1fc", "#2a78d6"), "orange": ("#fdeee6", "#eb6834"), "green": ("#e3f6ef", "#1baf7a"),
    "violet": ("#eeecfb", "#6250d6"), "gray": ("#f3f3f1", "#8a8984"), "red": ("#fde9e9", "#e34948"),
    "yellow": ("#fdf4dc", "#c98500"),
}
plt.rcParams.update({"font.family": "DejaVu Sans", "savefig.dpi": 200, "savefig.bbox": "tight"})


def canvas(w=12, h=7, xmax=100, ymax=60):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, color="blue", size=9, bold=False, r=1.2, title=None, align="center"):
    fc, ec = P[color]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=1.6))
    if title:
        ax.text(x + 1.2, y + h - 1.4, title, fontsize=size + 1, fontweight="bold", color=ec, va="top")
    if text:
        tx = x + w / 2 if align == "center" else x + 1.5
        ax.text(tx, y + h / 2 - (1.2 if title else 0), text, ha=align, va="center", fontsize=size, color=INK,
                fontweight="bold" if bold else "normal", linespacing=1.35)
    return (x, y, w, h)


def diamond(ax, cx, cy, w, h, text, color="yellow", size=8.5):
    fc, ec = P[color]
    ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)], closed=True,
                         fc=fc, ec=ec, lw=1.6))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=size, color=INK, linespacing=1.25)


def arrow(ax, p1, p2, text=None, color=INK2, style="-|>", ls="-", size=8, offset=(0, 0.9), rad=0.0):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=13, color=color, lw=1.4, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0))
    if text:
        mx, my = (p1[0] + p2[0]) / 2 + offset[0], (p1[1] + p2[1]) / 2 + offset[1]
        ax.text(mx, my, text, ha="center", va="bottom", fontsize=size, color=INK2,
                bbox=dict(fc="white", ec="none", pad=0.6))


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, facecolor="white")
    plt.close(fig)
    print("  ", OUT / name)


# ------------------------------------------------------------------------ architecture
def architecture():
    fig, ax = canvas(13, 7.6, 100, 62)
    box(ax, 1, 44, 28, 16, "", "blue", title="Browser: Next.js 14 + TS")
    for i, t in enumerate(["Home · Enroll · Hide · Extract", "Analysis · Security Log", "Attack Lab · How It Works",
                           "getUserMedia webcam (raw frames)"]):
        ax.text(3, 54.5 - i * 2.9, "• " + t, fontsize=8.5, color=INK)
    arrow(ax, (29, 52), (35, 52))
    ax.text(32, 41.6, "JSON + multipart:\nimages, frames, vault", fontsize=7.2, color=INK2, ha="center")
    box(ax, 35, 44, 23, 16, "", "violet", title="FastAPI REST layer")
    for i, t in enumerate(["/api/enroll  /api/hide", "/api/challenge", "/api/extract/face|password", "/api/analyze  /api/attack",
                           "/api/logs  /api/demo"]):
        ax.text(36.5, 55 - i * 2.4, t, fontsize=7.8, family="monospace", color=INK)
    arrow(ax, (46.5, 44), (46.5, 39.5))
    box(ax, 1, 30, 98, 9.5, "FaceLockService - orchestrates every security decision on the server\n"
                             "(lockout check → image/vault binding → liveness → face match → unwrap DEK → reveal)",
        "gray", size=9)
    mods = [("crypto.py", "AES-256-GCM\nHKDF-SHA256\nArgon2id", "orange"),
            ("lsb.py / stego.py", "keyed random LSB\n38-B header\nPNG I/O", "orange"),
            ("vault.py", "Face Vault\nkey wrapping\nimage binding", "violet"),
            ("face_engine.py", "YuNet detector\nSFace 128-D\n(DeepFace fallback)", "green"),
            ("liveness.py", "MediaPipe mesh\nEAR blinks · yaw\nrandom challenge", "green"),
            ("security_log.py", "SQLite audit log\n3-strike lockout\nintruder photos", "red")]
    for i, (t, d, c) in enumerate(mods):
        x = 1 + i * 16.5
        box(ax, x, 13.5, 15.2, 12, d, c, size=8, title=t)
        arrow(ax, (x + 7.6, 30), (x + 7.6, 25.5))
    box(ax, 1, 0.5, 98, 10.5, "", "gray", title="Owner's device storage  (app/backend/data/)")
    for i, t in enumerate(["device.key (32 random bytes)", "profiles/*.prof (encrypted templates)", "security.db (log + lockouts)",
                           "intruders/*.jpg (failed attempts)", "jobs/ (cover, stego, .vault)"]):
        ax.text(3 + (i % 3) * 32, 5.6 - (i // 3) * 3.2, "• " + t, fontsize=8, color=INK)
    box(ax, 66, 44, 33, 16, "", "yellow", title="User keeps / shares")
    ax.text(68, 54, "stego.png  - can travel publicly\n(looks like an ordinary photo)", fontsize=8.5, va="top")
    ax.text(68, 48.5, "secret.vault - kept by the owner\n(useless without device + live face)", fontsize=8.5, va="top")
    arrow(ax, (58, 52), (66, 52))
    save(fig, "fig_architecture.png")


# --------------------------------------------------------------------------- flows
def hide_flow():
    fig, ax = canvas(8.5, 13.5, 60, 124)
    steps = [("Start: user opens Hide Data", "gray"), ("Upload cover image\n(PNG/BMP/JPG → decoded to RGB)", "blue"),
             ("Enter text or choose a file\n(live capacity meter)", "blue"), ("Select up to 3 enrolled faces\n(+ optional backup password)", "blue")]
    y = 116
    for i, (t, c) in enumerate(steps):
        box(ax, 12, y, 36, 6.5, t, c, size=8.5)
        if i < len(steps) - 1:
            arrow(ax, (30, y), (30, y - 3))
        y -= 9.5
    diamond(ax, 30, y + 2.2, 30, 8, "payload + 54 B\n≤ capacity?")
    arrow(ax, (30, y + 6.5 + 2.3), (30, y + 6.3))
    arrow(ax, (45, y + 2.2), (52, y + 2.2), "no")
    box(ax, 50, y - 2, 9.5, 8.5, "Error:\nuse larger\ncover", "red", size=7.5)
    arrow(ax, (30, y - 1.8), (30, y - 5.5), "yes", offset=(3, -1))
    y -= 12.5
    for i, (t, c) in enumerate([("Generate random 256-bit DEK", "orange"),
                                ("Encrypt payload: AES-256-GCM\nkey = HKDF(DEK, salt), AAD = header", "orange"),
                                ("seed = HKDF(DEK) → AES-CTR keystream\n→ rank all R,G,B slots → pick first k", "orange"),
                                ("Write header + ciphertext bits into\nthe LSBs of the chosen slots", "orange"),
                                ("Save stego as PNG; fingerprint pixels (SHA-256)", "green"),
                                ("Build Face Vault: wrap DEK per face slot\n(+ Argon2id password slot), bind to fingerprint", "violet"),
                                ("Download stego.png + secret.vault\nlog event · show PSNR/SSIM", "green")]):
        box(ax, 8, y, 44, 6.5, t, c, size=8.2)
        if i < 6:
            arrow(ax, (30, y), (30, y - 3))
        y -= 9.5
    save(fig, "fig_hide_flow.png")


def extract_flow():
    fig, ax = canvas(11, 12.5, 80, 110)
    box(ax, 22, 102, 36, 6, "Upload stego.png + secret.vault", "blue", size=8.5)
    arrow(ax, (40, 102), (40, 99))
    diamond(ax, 40, 94.5, 26, 9, "Vault locked out?\n(3 recent failures)")
    arrow(ax, (53, 94.5), (62, 94.5), "yes")
    box(ax, 62, 91, 16, 7, "HTTP 423\nwait N seconds", "red", size=8)
    arrow(ax, (40, 90), (40, 86.5), "no", offset=(2.5, -1))
    diamond(ax, 40, 82, 26, 9, "Pixel SHA-256 ==\nvault.image_sha256?")
    arrow(ax, (53, 82), (62, 82), "no")
    box(ax, 62, 78.5, 16, 7, "Reject:\nwrong pair / edited\n/ recompressed", "red", size=7.5)
    arrow(ax, (40, 77.5), (40, 74), "yes", offset=(2.5, -1))
    box(ax, 18, 67.5, 44, 6.5, "Server issues random challenge (single-use, 120 s)\nblink twice | turn left | turn right", "violet", size=8)
    arrow(ax, (40, 67.5), (40, 64.5))
    box(ax, 18, 58, 44, 6.5, "Browser records 5 s of raw frames (10 fps)\nand uploads them with challenge id", "blue", size=8)
    arrow(ax, (40, 58), (40, 55))
    diamond(ax, 40, 50, 30, 10, "Liveness OK?\n≥1 blink (EAR) + challenge\n+ natural motion, 1 face")
    arrow(ax, (55, 50), (62, 50), "no")
    box(ax, 62, 43, 16, 14, "DENY\n• failure count +1\n• intruder photo\n• audit log\n• 3rd → lockout", "red", size=7.5)
    arrow(ax, (40, 45), (40, 41.5), "yes", offset=(2.5, -1))
    box(ax, 18, 35, 44, 6.5, "SFace embeddings of frontal frames → live template\ncosine vs each authorised slot (sealed in vault)", "green", size=8)
    arrow(ax, (40, 35), (40, 32))
    diamond(ax, 40, 27, 30, 10, "best ≥ threshold (0.40)\nand same face\nthroughout scan?")
    arrow(ax, (55, 27), (70, 27), "no")
    arrow(ax, (70, 27), (70, 43), color=P["red"][1])
    arrow(ax, (40, 22), (40, 18.5), "yes", offset=(2.5, -1))
    box(ax, 18, 12, 44, 6.5, "Unwrap DEK from the matched slot\nseed = HKDF(DEK) → read random LSBs", "orange", size=8)
    arrow(ax, (40, 12), (40, 9))
    box(ax, 18, 2, 44, 7, "AES-GCM decrypt + verify tag → ACCESS GRANTED\nshow text / download file · reset failures · log", "green", size=8, bold=True)
    box(ax, 0.5, 52, 14, 18, "Fallback:\nbackup password\n(Argon2id verify\n→ unwrap DEK)\nsame lockout\nrules apply", "yellow", size=7.5)
    save(fig, "fig_extract_flow.png")


# --------------------------------------------------------------------------- DFDs
def dfd():
    fig, ax = canvas(12, 5.2, 100, 44)
    ax.add_patch(Ellipse((50, 22), 26, 18, fc=P["violet"][0], ec=P["violet"][1], lw=1.8))
    ax.text(50, 22, "0\nFaceLock Stego\nSystem", ha="center", va="center", fontsize=10, fontweight="bold")
    box(ax, 2, 30, 18, 9, "Owner\n(sender)", "blue", size=9, bold=True)
    box(ax, 2, 5, 18, 9, "Authorised\nreceiver", "blue", size=9, bold=True)
    box(ax, 80, 30, 18, 9, "Attacker /\nintruder", "red", size=9, bold=True)
    box(ax, 80, 5, 18, 9, "Webcam", "gray", size=9, bold=True)
    arrow(ax, (20, 36), (38, 27), "face samples, cover,\nsecret, password", size=7.5, offset=(-2, 1))
    arrow(ax, (37, 21), (20, 32), "stego.png, .vault,\nmetrics", size=7.5, offset=(-1, -4), rad=0.15)
    arrow(ax, (20, 10), (38, 17), "stego + vault\n+ live frames", size=7.5, offset=(-1, -4))
    arrow(ax, (39, 15), (20, 6), "secret / denial", size=7.5, offset=(3, -3.2), rad=-0.15)
    arrow(ax, (80, 34), (63, 26), "stolen image/vault,\nphoto spoof", size=7.5, offset=(1, 1))
    arrow(ax, (63, 24), (80, 31), "ACCESS DENIED,\nlockout", size=7.5, offset=(3, -4.5), rad=-0.2)
    arrow(ax, (80, 10), (63, 17), "video frames", size=7.5, offset=(1, -3))
    ax.text(50, 42, "Context diagram (DFD level 0)", ha="center", fontsize=11, fontweight="bold")
    save(fig, "fig_dfd_level0.png")

    fig, ax = canvas(13, 8.4, 100, 66)
    procs = [(14, 50, "1.0\nEnroll face"), (40, 50, "2.0\nHide secret"), (66, 50, "3.0\nVerify\nliveness"),
             (66, 24, "4.0\nMatch face\n& unwrap key"), (40, 24, "5.0\nReveal &\ndecrypt"), (88, 50, "6.0\nAudit &\nlockout")]
    for x, y, t in procs:
        ax.add_patch(Ellipse((x, y), 17, 12, fc=P["violet"][0], ec=P["violet"][1], lw=1.6))
        ax.text(x, y, t, ha="center", va="center", fontsize=8.5, fontweight="bold")
    stores = [(4, 34, "D1 Face profiles (encrypted)"), (30, 34, "D2 Jobs: cover / stego / vault"),
              (56, 6, "D3 device.key"), (78, 34, "D4 security.db + intruders/")]
    for x, y, t in stores:
        ax.plot([x, x + 22], [y + 4, y + 4], color=INK2, lw=1.4)
        ax.plot([x, x + 22], [y, y], color=INK2, lw=1.4)
        ax.plot([x, x], [y, y + 4], color=INK2, lw=1.4)
        ax.text(x + 1, y + 2, t, va="center", fontsize=8)
    box(ax, 4, 59, 20, 5.5, "Owner (webcam)", "blue", size=8.5, bold=True)
    box(ax, 30, 59, 20, 5.5, "Owner (files)", "blue", size=8.5, bold=True)
    box(ax, 56, 59, 20, 5.5, "Receiver (webcam)", "blue", size=8.5, bold=True)
    box(ax, 30, 6, 20, 5.5, "Receiver (secret)", "green", size=8.5, bold=True)
    arrow(ax, (14, 59), (14, 56), "5 samples", size=7)
    arrow(ax, (14, 44), (14, 38), "template", size=7)
    arrow(ax, (40, 59), (40, 56), "cover, secret", size=7)
    arrow(ax, (26, 36), (34, 46), "templates", size=7, offset=(-3, 0))
    arrow(ax, (40, 44), (40, 38), "stego, vault", size=7)
    arrow(ax, (66, 59), (66, 56), "frames", size=7)
    arrow(ax, (66, 44), (66, 30), "live frames OK", size=7)
    arrow(ax, (74.5, 50), (79.5, 50))
    arrow(ax, (72, 28), (82, 44), "failures", size=7, offset=(3, -2))
    arrow(ax, (88, 44), (88, 38), "events, photos", size=7)
    arrow(ax, (60, 10), (63, 18.5), "device key", size=7, offset=(-5, 0))
    arrow(ax, (57.5, 24), (48.5, 24), "DEK", size=7)
    arrow(ax, (40, 18), (40, 11.5), "plaintext", size=7)
    arrow(ax, (45, 34), (61, 28), "vault", size=7, offset=(0, -0.5))
    ax.text(50, 65.5, "Level-1 data flow diagram", ha="center", fontsize=11, fontweight="bold")
    save(fig, "fig_dfd_level1.png")


def sequence():
    fig, ax = canvas(13, 9, 100, 74)
    actors = [("User", 8), ("Browser UI", 28), ("FastAPI", 48), ("Liveness\n(MediaPipe)", 66), ("Face engine\n(SFace)", 81), ("Vault / Stego", 95)]
    for name, x in actors:
        box(ax, x - 7, 66, 14, 6, name, "violet" if x > 40 else "blue", size=8.5, bold=True)
        ax.plot([x, x], [2, 66], color="#b9b8b3", lw=1.2, ls="--")
    msgs = [(8, 28, "upload stego + vault, click Scan"), (28, 48, "POST /api/vault/inspect"), (48, 28, "slots, lock status", True),
            (28, 48, "POST /api/challenge"), (48, 28, "{id, 'turn left'}", True), (28, 8, "show instruction"),
            (8, 28, "performs challenge (5 s)"), (28, 48, "POST /api/extract/face (≈50 JPEG frames)"),
            (48, 95, "check lockout · pixel hash"), (48, 66, "landmarks per frame"), (66, 48, "EAR, yaw → pass/fail", True),
            (48, 81, "embed frontal frames"), (81, 48, "cosine vs slots", True), (48, 95, "unwrap DEK · read LSBs · decrypt"),
            (95, 48, "plaintext (GCM verified)", True), (48, 28, "granted + secret + signals", True), (28, 8, "ACCESS GRANTED")]
    y = 62
    for m in msgs:
        a, b, t = m[0], m[1], m[2]
        ret = len(m) > 3
        arrow(ax, (a, y), (b, y), color=P["green"][1] if ret else INK2, ls="--" if ret else "-")
        ax.text((a + b) / 2, y + 0.5, t, ha="center", va="bottom", fontsize=7.5, color=INK)
        y -= 3.5
    ax.text(50, 73.5, "Sequence diagram: face-based extraction", ha="center", fontsize=11, fontweight="bold")
    save(fig, "fig_sequence_extract.png")


def vault_design():
    fig, ax = canvas(13, 7.2, 100, 58)
    box(ax, 38, 47, 24, 8, "DEK\n256-bit random data key", "orange", size=9, bold=True)
    box(ax, 2, 47, 26, 8, "Message key = HKDF(DEK, salt,\n'facelock/msg/v1')\nLSB seed = HKDF(DEK, 'facelock/lsb/v1')", "orange", size=7.8)
    arrow(ax, (38, 51), (28, 51))
    box(ax, 2, 31, 26, 11, "stego.png\nheader + AES-GCM ciphertext\nat keyed random LSB positions\n(no key material inside)", "blue", size=8)
    arrow(ax, (15, 47), (15, 42))
    box(ax, 33, 1, 64, 42, "", "violet", title="secret.vault (JSON)")
    ax.text(35, 38.5, "public header: format · version · vault_id · created_at · image_sha256\n→ SHA-256 of canonical header = AAD for every AES-GCM below",
            fontsize=8, va="top", color=INK)
    box(ax, 35, 2.5, 36, 29.5, "", "green", title="face_lock (sealed)")
    ax.text(36.5, 28.4, "KEK_vault = HKDF(device_key, salt, 'vault/v1')\nAES-GCM(KEK_vault) seals:", fontsize=7.2, va="top", family="monospace")
    ax.text(36.5, 22.6, "per slot i: KEK_slot = HKDF(device_key,\n  salt, 'slot/v1' ‖ SHA-256(T_i))", fontsize=7.2, family="monospace", va="top")
    for i in range(3):
        box(ax, 36.5 + i * 11.3, 4, 10.5, 11, f"slot {i + 1}\ntemplate T{i + 1}\nwrap(DEK)", "gray", size=7)
    box(ax, 73, 2.5, 22, 29.5, "", "yellow", title="password_lock")
    ax.text(74.3, 27.5, "argon2id PHC hash\n(t=3, m=64 MiB, p=2)\n\nK_pw = Argon2id(pw,\n           salt2)\nwrapped_dek =\n  AES-GCM(K_pw, DEK)\n\noptional · portable", fontsize=7.5, va="top")
    arrow(ax, (50, 47), (50, 43), "wrapped, never stored in clear", size=7.5, offset=(13, -1.4))
    box(ax, 2, 3, 26, 22, "Release rule (server):\n1 not locked out\n2 image hash matches\n3 liveness passed\n4 cosine(live, T_i) ≥ 0.40\n5 same face all scan\n→ unwrap slot i only", "red", size=8, align="left")
    box(ax, 66, 47, 32, 8, "device.key: 32 random bytes on the\nowner's machine (never uploaded)", "gray", size=8)
    arrow(ax, (80, 47), (55, 31), color=P["violet"][1])
    save(fig, "fig_vault_design.png")


def lsb_example():
    fig, ax = canvas(12, 4.6, 100, 38)
    vals = [(154, 201, 87), (152, 199, 90)]
    bits = [1, 0, 0, 1, 1, 0]
    ax.text(50, 36, "Hiding 6 secret bits 1 0 0 1 1 0 in two pixels", ha="center", fontsize=11, fontweight="bold")
    k = 0
    for p, (r, g, b) in enumerate(vals):
        y0 = 22 - p * 15
        ax.add_patch(FancyBboxPatch((1, y0), 8, 9, boxstyle="round,pad=0,rounding_size=1", fc=f"#{r:02x}{g:02x}{b:02x}", ec="#888"))
        ax.text(5, y0 - 1.5, f"pixel {p + 1}", ha="center", fontsize=8, color=INK2)
        for c, v in enumerate((r, g, b)):
            nv = (v & 0xFE) | bits[k]
            x0 = 13 + c * 29
            ax.text(x0, y0 + 7, f"{'RGB'[c]} = {v}", fontsize=9, color=INK2)
            bs, ns = format(v, "08b"), format(nv, "08b")
            ax.text(x0, y0 + 3.6, bs[:7], fontsize=11, family="monospace", color=INK)
            ax.text(x0 + 9.3, y0 + 3.6, bs[7], fontsize=11, family="monospace", color=P["blue"][1], fontweight="bold")
            ax.text(x0 + 11.3, y0 + 3.6, "→", fontsize=11)
            changed = bs[7] != ns[7]
            ax.text(x0 + 13.5, y0 + 3.6, ns[:7], fontsize=11, family="monospace", color=INK)
            ax.text(x0 + 22.8, y0 + 3.6, ns[7], fontsize=11, family="monospace",
                    color=P["orange"][1] if changed else P["green"][1], fontweight="bold")
            ax.text(x0 + 13.5, y0 + 0.4, f"= {nv}  ({'changed by 1' if changed else 'unchanged'})", fontsize=8,
                    color=P["orange"][1] if changed else P["green"][1])
            k += 1
    save(fig, "fig_lsb_example.png")


def use_case():
    fig, ax = canvas(12, 7.2, 100, 60)
    ax.add_patch(FancyBboxPatch((24, 2), 52, 54, boxstyle="round,pad=0,rounding_size=2", fc="#fbfbfa", ec=INK2, lw=1.4))
    ax.text(50, 53.5, "FaceLock Stego", ha="center", fontsize=11, fontweight="bold")
    ucs = ["Enroll face (5 samples)", "Hide text / file in image", "Set backup password", "Extract with live face",
           "Extract with password", "Analyse stego quality", "View security log", "Run steganalysis lab", "Manage face profiles"]
    for i, t in enumerate(ucs):
        cy = 48 - i * 5.1
        ax.add_patch(Ellipse((50, cy), 34, 4.2, fc=P["violet"][0], ec=P["violet"][1], lw=1.3))
        ax.text(50, cy, t, ha="center", va="center", fontsize=8.5)

    def actor(x, y, name):
        ax.add_patch(plt.Circle((x, y + 6), 1.6, fc="white", ec=INK, lw=1.4))
        ax.plot([x, x], [y + 4.4, y], color=INK, lw=1.4)
        ax.plot([x - 2.5, x + 2.5], [y + 3, y + 3], color=INK, lw=1.4)
        ax.plot([x, x - 2], [y, y - 3], color=INK, lw=1.4)
        ax.plot([x, x + 2], [y, y + -3], color=INK, lw=1.4)
        ax.text(x, y - 5, name, ha="center", fontsize=9, fontweight="bold")

    actor(9, 38, "Owner")
    actor(9, 12, "Authorised\nreceiver")
    actor(91, 38, "Examiner /\nanalyst")
    actor(91, 10, "Intruder")
    for i in (0, 1, 2, 8):
        ax.plot([11.5, 33], [41, 48 - i * 5.1], color=INK2, lw=0.9)
    for i in (3, 4):
        ax.plot([11.5, 33], [15, 48 - i * 5.1], color=INK2, lw=0.9)
    for i in (5, 6, 7):
        ax.plot([88.5, 67], [41, 48 - i * 5.1], color=INK2, lw=0.9)
    ax.plot([88.5, 67], [13, 48 - 3 * 5.1], color=P["red"][1], lw=1.1, ls="--")
    ax.text(84, 25, "attempts (denied,\nphotographed)", fontsize=7.5, color=P["red"][1], ha="center")
    save(fig, "fig_use_case.png")


def stego_format():
    fig, ax = canvas(12, 2.8, 100, 20)
    parts = [("magic\n'FLS1'", 4, "gray"), ("ver", 1, "gray"), ("flags", 1, "gray"), ("ct_len", 4, "gray"),
             ("salt", 16, "yellow"), ("nonce", 12, "yellow"), ("ciphertext (packed payload)", 30, "orange"), ("GCM tag", 16, "red")]
    widths = [7, 5, 5, 6, 12, 11, 34, 16]          # display widths (not to scale for tiny fields)
    x = 2
    for (name, n, c), w in zip(parts, widths):
        box(ax, x, 6, w, 8, f"{name}\n{n if 'cipher' not in name else 'N'} B", c, size=7.5, r=0.4)
        x += w
    hdr = sum(widths[:6])
    ax.plot([2, 2 + hdr], [4.5, 4.5], color=INK2, lw=1)
    ax.text(2 + hdr / 2, 1.2, "38-byte header (authenticated as AAD)", ha="center", fontsize=8, color=INK2)
    ax.text(50, 17.5, "Bitstream written into keyed random LSB positions", ha="center", fontsize=10, fontweight="bold")
    save(fig, "fig_stego_format.png")


if __name__ == "__main__":
    for fn in (architecture, hide_flow, extract_flow, dfd, sequence, vault_design, lsb_example, use_case, stego_format):
        fn()
