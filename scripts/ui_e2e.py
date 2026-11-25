"""Headless browser end-to-end test of the full web app + real screenshots.

    python scripts/ui_e2e.py [--front http://localhost:3000] [--api http://localhost:8000]

Requires both servers running. Uses the installed Google Chrome through
Playwright. The webcam is replaced by a scripted *fake camera* (a canvas
stream) that plays synthetic frames of StyleGAN faces (not real people):

1. enrol two synthetic users        5. impostor (different live face)  -> DENIED
2. hide a secret for one of them    6. wrong challenge response         -> DENIED + LOCKOUT
3. genuine live scan     -> GRANTED 7. password fallback after lockout  -> GRANTED
4. photo attack (static) -> DENIED  8. analysis, log, attack lab, how-it-works pages

Screenshots go to docs/figures/screenshots/. Exit code 0 only if every check passes.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app" / "backend"))
from tests import synth  # noqa: E402

from playwright.sync_api import Page, expect, sync_playwright  # noqa: E402

SHOTS = ROOT / "docs" / "figures" / "screenshots"
COVER = ROOT / "dataset" / "covers" / "kodak" / "kodim23.png"
SECRET = "Project Nightingale: server room access code is 7391-ALPHA. Rotate on 1 Dec."
PASSWORD = "Backup-Pass-2026"

FAKE_CAM = """
(() => {
  const canvas = document.createElement('canvas'); canvas.width = 640; canvas.height = 480;
  const ctx = canvas.getContext('2d');
  const st = { imgs: [], idx: 0, loop: true };
  window.__cam = {
    async set(urls, loop) {
      const imgs = await Promise.all(urls.map(u => new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = u; })));
      st.imgs = imgs; st.idx = 0; st.loop = loop;
    }
  };
  setInterval(() => {
    if (!st.imgs.length) { ctx.fillStyle = '#222'; ctx.fillRect(0, 0, 640, 480); return; }
    ctx.drawImage(st.imgs[Math.min(st.idx, st.imgs.length - 1)], 0, 0, 640, 480);
    st.idx++; if (st.loop && st.idx >= st.imgs.length) st.idx = 0;
  }, 100);
  navigator.mediaDevices.getUserMedia = async () => canvas.captureStream(30);
})();
"""

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)


def urls(frames) -> list[str]:
    return ["data:image/jpeg;base64," + base64.b64encode(synth.jpeg(f)).decode() for f in frames]


def cam(page: Page, frames, loop=True) -> None:
    page.evaluate("([u, l]) => window.__cam.set(u, l)", [urls(frames), loop])


def shot(page: Page, name: str, full=True) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.wait_for_timeout(700)
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=full)


def api(base: str, path: str, method="GET"):
    req = urllib.request.Request(base + path, method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"null")


def enroll(page: Page, front: str, face_id: int, label: str, screenshot: str | None) -> None:
    page.goto(f"{front}/enroll")
    page.get_by_role("button", name="Start camera").click()
    cam(page, synth.enrollment_samples(face_id, n=10, seed=face_id))
    page.wait_for_timeout(500)
    page.get_by_role("button", name="Start guided capture").click()
    expect(page.get_by_text("All samples captured")).to_be_visible(timeout=30000)
    page.get_by_placeholder("Name for this profile").fill(label)
    if screenshot:
        shot(page, screenshot + "_capture", full=False)
    page.get_by_role("button", name="Save face profile").click()
    expect(page.get_by_text("enrolled. Sample consistency")).to_be_visible(timeout=30000)
    check(f"enrol {label}", True)
    if screenshot:
        shot(page, screenshot)


def scan(page: Page, frames_for, label: str, face_id: int) -> str:
    """Run one live scan; frames_for(challenge_type) returns the frames to play.

    Before the scan the camera shows the same person idling in front of it,
    exactly like a real user waiting for the challenge.
    """
    cam(page, synth.photo_burst(face_id, n=20, seed=9))
    try_again = page.get_by_role("button", name="Try again")
    if try_again.count():
        try_again.click()
    btn = page.get_by_role("button", name="Start live face scan")
    expect(btn).to_be_enabled(timeout=15000)
    with page.expect_response("**/api/challenge") as resp:
        btn.click()
    ch = resp.value.json()
    cam(page, frames_for(ch["type"]), loop=False)
    expect(page.get_by_text("ACCESS GRANTED").or_(page.get_by_text("ACCESS DENIED"))).to_be_visible(timeout=60000)
    outcome = "granted" if page.get_by_text("ACCESS GRANTED").count() else "denied"
    print(f"   {label}: challenge={ch['type']} -> {outcome}")
    return outcome


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--front", default="http://localhost:3000")
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--headed", action="store_true")
    a = ap.parse_args()

    # clean slate: remove previous profiles and log entries
    for p in api(a.api, "/api/profiles"):
        api(a.api, f"/api/profiles/{p['id']}", "DELETE")
    api(a.api, "/api/logs", "DELETE")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=not a.headed)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5,
                                  accept_downloads=True)
        ctx.add_init_script(FAKE_CAM)
        page = ctx.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        # ---------------------------------------------------------------- home
        page.goto(a.front)
        expect(page.get_by_text("Backend online")).to_be_visible(timeout=20000)
        check("home page + backend online", True)
        shot(page, "01_home", full=False)

        # -------------------------------------------------------------- enroll
        enroll(page, a.front, 1, "Alex (synthetic)", "02_enroll")
        enroll(page, a.front, 3, "Sam (synthetic)", None)
        check("two profiles stored", len(api(a.api, "/api/profiles")) == 2)

        # ---------------------------------------------------------------- hide
        page.goto(f"{a.front}/hide")
        page.locator("input[type=file]").first.set_input_files(str(COVER))
        page.get_by_placeholder("Type the secret message").fill(SECRET)
        page.get_by_role("button", name="Alex (synthetic)").click()
        page.get_by_text("Backup password (Argon2id)").click()
        page.get_by_placeholder("At least 8 characters").fill(PASSWORD)
        shot(page, "03_hide_form")
        with page.expect_response("**/api/hide") as resp:
            page.get_by_role("button", name="Hide secret in image").click()
        job = resp.value.json()
        expect(page.get_by_text("Secret hidden successfully")).to_be_visible(timeout=30000)
        check("hide via UI", job["metrics"]["psnr"] > 60, f"PSNR {job['metrics']['psnr']} dB")
        shot(page, "04_hide_result")
        work = ROOT / "dataset" / "_e2e"
        work.mkdir(parents=True, exist_ok=True)
        stego, vault = work / "e2e_stego.png", work / "e2e.vault"
        urllib.request.urlretrieve(f"{a.api}/api/jobs/{job['job_id']}/stego", stego)
        urllib.request.urlretrieve(f"{a.api}/api/jobs/{job['job_id']}/vault", vault)

        # ------------------------------------------------------------- extract
        page.goto(f"{a.front}/extract")
        files = page.locator("input[type=file]")
        files.nth(0).set_input_files(str(stego))
        files.nth(1).set_input_files(str(vault))
        expect(page.get_by_text("1 face slot")).to_be_visible(timeout=10000)
        page.get_by_role("button", name="Start camera").click()
        cam(page, synth.photo_burst(1, n=20, seed=3))
        page.wait_for_timeout(400)
        shot(page, "05_extract_ready", full=False)

        out = scan(page, lambda t: synth.live_burst(1, t, n=60, seed=21), "genuine", 1)
        check("genuine user granted", out == "granted")
        expect(page.get_by_text(SECRET)).to_be_visible()
        check("secret text displayed", True)
        shot(page, "06_access_granted")

        out = scan(page, lambda t: synth.photo_burst(1, n=60, seed=4), "photo attack", 1)
        check("photo attack denied", out == "denied" and page.get_by_text("Liveness check failed").count() > 0)
        shot(page, "07_access_denied_photo")

        out = scan(page, lambda t: synth.live_burst(5, t, n=60, seed=5), "impostor", 5)
        check("impostor denied", out == "denied" and page.get_by_text("Face not recognised").count() > 0)
        shot(page, "08_access_denied_impostor")

        wrong = lambda t: synth.live_burst(1, "turn_right" if t == "turn_left" else "turn_left", n=60, seed=6)  # noqa: E731
        out = scan(page, wrong, "wrong challenge", 1)
        check("wrong challenge denied", out == "denied")
        expect(page.get_by_text("Temporarily locked")).to_be_visible(timeout=5000)
        check("lockout after 3 failures", True)
        shot(page, "09_lockout")

        lock = api(a.api, "/api/logs")["items"]
        check("intruder photos stored", sum(1 for i in lock if i["photo"]) == 3)

        # password fallback works once lockout expires (60 s default)
        remaining = json.loads(urllib.request.urlopen(urllib.request.Request(
            f"{a.api}/api/health")).read())["lockout_seconds"]
        print(f"   waiting {remaining}s for lockout to expire…", flush=True)
        time.sleep(remaining + 1)
        page.reload()
        files = page.locator("input[type=file]")
        files.nth(0).set_input_files(str(stego))
        files.nth(1).set_input_files(str(vault))
        expect(page.get_by_text("1 face slot")).to_be_visible(timeout=10000)
        page.get_by_role("button", name="Password").click()
        page.get_by_placeholder("Backup password").fill(PASSWORD)
        page.get_by_role("button", name="Unlock with password").click()
        expect(page.get_by_text("ACCESS GRANTED")).to_be_visible(timeout=30000)
        check("password fallback granted", page.get_by_text(SECRET).count() > 0)

        # --------------------------------------------------------- analysis
        page.goto(f"{a.front}/analysis?job={job['job_id']}")
        expect(page.get_by_text("Difference heatmap")).to_be_visible(timeout=30000)
        page.wait_for_timeout(1500)
        check("analysis dashboard", True)
        shot(page, "10_analysis")

        # -------------------------------------------------------------- log
        page.goto(f"{a.front}/log")
        expect(page.get_by_text("Attempts", exact=True)).to_be_visible(timeout=10000)
        page.wait_for_timeout(1500)
        check("security log shows intruders", page.locator("img[alt=intruder]").count() >= 3)
        shot(page, "11_security_log")

        # -------------------------------------------------------- attack lab
        page.goto(f"{a.front}/attack-lab")
        page.locator("button img[alt='kodim23.png']").click()
        page.get_by_role("button", name="Run chi-square attack").click()
        expect(page.get_by_text("What the attacker sees")).to_be_visible(timeout=60000)
        page.wait_for_timeout(1500)
        check("attack lab", True)
        shot(page, "12_attack_lab")

        # ----------------------------------------------------- how it works
        page.goto(f"{a.front}/how-it-works")
        page.wait_for_timeout(2500)
        shot(page, "13_how_it_works", full=False)

        # ------------------------------------------------------- demo mode
        page.goto(f"{a.front}/extract")
        page.get_by_text("Demo Mode").first.click()
        page.get_by_role("button", name="Load demo pair").click()
        page.get_by_text("Use demo password").click()
        page.get_by_role("button", name="Unlock with password").click()
        expect(page.get_by_text("ACCESS GRANTED")).to_be_visible(timeout=30000)
        check("demo mode pair unlocks", page.get_by_text("Operation Blue Heron").count() > 0)
        shot(page, "14_demo_mode", full=False)
        page.get_by_text("Demo Mode").first.click()

        # ------------------------------------------------------- responsive
        m = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        mp = m.new_page()
        mp.goto(f"{a.front}/hide")
        mp.wait_for_timeout(1200)
        overflow = mp.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
        check("mobile layout has no horizontal overflow", not overflow)
        shot(mp, "15_mobile_hide", full=False)

        check("no uncaught page errors", not errors, "; ".join(errors[:3]))
        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} UI checks passed")
    (ROOT / "dataset" / "results").mkdir(parents=True, exist_ok=True)
    with open(ROOT / "dataset" / "results" / "ui_e2e_results.json", "w") as fh:
        json.dump([{"check": n, "passed": ok, "detail": d} for n, ok, d in results], fh, indent=2)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
