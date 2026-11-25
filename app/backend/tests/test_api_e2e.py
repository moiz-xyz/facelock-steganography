"""End-to-end API tests with the real face + liveness models and synthetic (GAN) faces.

Scenario: Alice enrols, hides a secret for herself; we then try every access path:
genuine live user, printed-photo attack, impostor, lockout after 3 failures,
password fallback, wrong image/vault pairing and a recompressed JPEG.
"""
import io
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import main
from facelock.config import Settings
from facelock.service import FaceLockService
from tests import synth


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    main.svc = FaceLockService(Settings(data_dir=d, lockout_seconds=8, argon2_memory_kib=8192, argon2_time_cost=1))
    main.svc.warmup()
    return TestClient(main.app)


def png(arr):
    b = io.BytesIO(); Image.fromarray(arr).save(b, "PNG"); return b.getvalue()


@pytest.fixture(scope="module")
def cover():
    rng = np.random.default_rng(5)
    y, x = np.mgrid[0:300, 0:400]
    base = np.stack([x * .6, y * .8, (x + y) * .3], -1) + rng.normal(0, 8, (300, 400, 3))
    return np.clip(base, 0, 255).astype(np.uint8)


def enroll(client, label, face_id):
    files = [("samples", (f"s{i}.jpg", synth.jpeg(f), "image/jpeg"))
             for i, f in enumerate(synth.enrollment_samples(face_id))]
    r = client.post("/api/enroll", data={"label": label}, files=files)
    assert r.status_code == 200, r.text
    return r.json()


def hide(client, cover, profile_ids, password=None, text="The vault code is 4-8-15-16-23-42"):
    data = {"message": text, "profile_ids": ",".join(profile_ids)}
    if password:
        data["password"] = password
    r = client.post("/api/hide", data=data, files={"cover": ("cover.png", png(cover), "image/png")})
    assert r.status_code == 200, r.text
    job = r.json()
    stego = client.get(f"/api/jobs/{job['job_id']}/stego").content
    vault = client.get(f"/api/jobs/{job['job_id']}/vault").content
    return job, stego, vault


def face_attempt(client, stego, vault, frames_fn):
    ch = client.post("/api/challenge").json()
    frames = frames_fn(ch["type"])
    files = [("stego_image", ("s.png", stego, "image/png")), ("vault_file", ("v.vault", vault, "application/json"))]
    files += [("frames", (f"f{i}.jpg", synth.jpeg(f), "image/jpeg")) for i, f in enumerate(frames)]
    return client.post("/api/extract/face", data={"challenge_id": ch["challenge_id"]}, files=files)


def test_health(client):
    h = client.get("/api/health").json()
    assert h["face_engine"] == "sface" and h["liveness_required"]


def test_full_flow(client, cover):
    alice = enroll(client, "Alice", 1)
    bob = enroll(client, "Bob", 3)
    assert {p["label"] for p in client.get("/api/profiles").json()} == {"Alice", "Bob"}
    job, stego, vault = hide(client, cover, [alice["id"], bob["id"]], password="correct-horse-9")
    assert job["metrics"]["psnr"] > 60 and job["metrics"]["ssim"] > 0.999
    assert b"4-8-15" not in stego and b"4-8-15" not in vault

    # 1. genuine live user (Alice) - every challenge type is answered correctly
    r = face_attempt(client, stego, vault, lambda t: synth.live_burst(1, t))
    body = r.json()
    assert r.status_code == 200 and body["granted"], body
    assert body["secret"]["text"] == "The vault code is 4-8-15-16-23-42"
    assert body["matched_label"] == "Alice"

    # 2. second authorised person (Bob) also works
    r = face_attempt(client, stego, vault, lambda t: synth.live_burst(3, t, seed=7))
    assert r.json()["granted"] and r.json()["matched_label"] == "Bob"

    # 3. printed-photo / phone-screen attack with Alice's face -> liveness fails, intruder photo stored
    r = face_attempt(client, stego, vault, lambda t: synth.photo_burst(1))
    body = r.json()
    assert not body["granted"] and "Liveness" in body["reason"]
    assert body["lock"]["failures"] == 1

    # 4. impostor (a live, blinking stranger) -> face not recognised
    r = face_attempt(client, stego, vault, lambda t: synth.live_burst(5, t))
    body = r.json()
    assert not body["granted"] and body["best_similarity"] < 0.4
    assert body["lock"]["failures"] == 2

    # 5. wrong challenge answer (turns left when asked to blink twice / turn right)
    def wrong(t):
        return synth.live_burst(1, "turn_left" if t != "turn_left" else "turn_right")
    r = face_attempt(client, stego, vault, wrong)
    body = r.json()
    assert not body["granted"] and body["lock"]["locked"]

    # 6. locked out -> even the right face and the right password are refused for now
    r = face_attempt(client, stego, vault, lambda t: synth.live_burst(1, t))
    assert r.status_code == 423
    r = client.post("/api/extract/password", data={"password": "correct-horse-9"},
                    files={"stego_image": ("s.png", stego), "vault_file": ("v.vault", vault)})
    assert r.status_code == 423

    import time; time.sleep(8.2)
    # 7. after lockout: password fallback works, wrong password counted
    r = client.post("/api/extract/password", data={"password": "wrong-password"},
                    files={"stego_image": ("s.png", stego), "vault_file": ("v.vault", vault)})
    assert not r.json()["granted"]
    r = client.post("/api/extract/password", data={"password": "correct-horse-9"},
                    files={"stego_image": ("s.png", stego), "vault_file": ("v.vault", vault)})
    assert r.json()["granted"] and "4-8-15" in r.json()["secret"]["text"]

    # 8. security log has intruder photos for failed face attempts
    logs = client.get("/api/logs").json()["items"]
    denied_face = [l for l in logs if l["result"] == "denied" and l["method"] == "face"]
    assert len(denied_face) == 3 and all(l["photo"] for l in denied_face)
    assert client.get(f"/api/logs/{denied_face[0]['id']}/photo").headers["content-type"] == "image/jpeg"
    assert any(l["result"] == "locked" for l in logs)


def test_file_payload_and_mismatch(client, cover):
    carol = enroll(client, "Carol", 2)
    pdf = b"%PDF-1.4\n" + bytes(np.random.default_rng(3).integers(0, 256, 3000, dtype=np.uint8))
    r = client.post("/api/hide", data={"profile_ids": carol["id"]},
                    files={"cover": ("c.jpg", png(cover), "image/png"),
                           "secret_file": ("plan.pdf", pdf, "application/pdf")})
    job = r.json()
    stego = client.get(f"/api/jobs/{job['job_id']}/stego").content
    vault = client.get(f"/api/jobs/{job['job_id']}/vault").content
    r = face_attempt(client, stego, vault, lambda t: synth.live_burst(2, t, seed=11))
    body = r.json()
    assert body["granted"] and body["secret"]["name"] == "plan.pdf"
    import base64
    assert base64.b64decode(body["secret"]["data_b64"]) == pdf

    # image from a different hide + this vault -> rejected before any face work
    _, other_stego, _ = hide(client, cover, [carol["id"]])
    r = client.post("/api/extract/password", data={"password": "x" * 8},
                    files={"stego_image": ("s.png", other_stego), "vault_file": ("v.vault", vault)})
    assert r.status_code == 400 and "does not belong" in r.json()["detail"]

    # recompressed as JPEG -> refused with an explanation
    arr = np.asarray(Image.open(io.BytesIO(stego)).convert("RGB"))
    b = io.BytesIO(); Image.fromarray(arr).save(b, "JPEG", quality=98)
    r = client.post("/api/extract/password", data={"password": "x" * 8},
                    files={"stego_image": ("s.jpg", b.getvalue()), "vault_file": ("v.vault", vault)})
    assert r.status_code == 400 and "lossy" in r.json()["detail"]


def test_capacity_and_validation(client, cover):
    r = client.post("/api/capacity", files={"cover": ("c.png", png(cover), "image/png")})
    assert r.json()["capacity_bytes"] == 400 * 300 * 3 // 8 - 54
    r = client.post("/api/hide", data={"message": "x" * 50_000, "password": "longenough1"},
                    files={"cover": ("c.png", png(cover[:40, :40]), "image/png")})
    assert r.status_code == 200 or "holds" in r.json()["detail"]     # compressible text may fit
    rnd = bytes(np.random.default_rng(9).integers(0, 256, 2000, dtype=np.uint8))
    r = client.post("/api/hide", data={"password": "longenough1"},
                    files={"cover": ("c.png", png(cover[:40, :40]), "image/png"),
                           "secret_file": ("r.bin", rnd, "application/octet-stream")})
    assert r.status_code == 400 and "holds" in r.json()["detail"]
    r = client.post("/api/hide", data={"message": "hi"}, files={"cover": ("c.png", png(cover), "image/png")})
    assert r.status_code == 400


def test_analysis_and_attack_lab(client, cover):
    job, _, _ = hide(client, cover, [], password="longenough1")
    a = client.get(f"/api/analyze/{job['job_id']}").json()
    assert a["metrics"]["psnr"] > 50 and len(a["histogram"]) == 256 and a["heatmap"].startswith("data:image/png")
    assert client.get(f"/api/bitplane/{job['job_id']}?which=stego&channel=1&bit=0").status_code == 200
    r = client.post("/api/attack", data={"fill": "0.5"}, files={"cover": ("c.png", png(cover), "image/png")})
    s = r.json()["summary"]
    assert s["sequential"]["flagged_prefix_pct"] >= s["random"]["flagged_prefix_pct"]
