"""FaceLock Stego - FastAPI backend.

Run:  uvicorn main:app --port 8000
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from facelock import stego
from facelock import vault as vlt
from facelock.config import settings
from facelock.service import FaceLockService, Locked, UserError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
os.environ.setdefault("GLOG_minloglevel", "2")

svc: FaceLockService | None = None
MAX_BYTES = settings.max_upload_mb * 1024 * 1024
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    global svc
    svc = FaceLockService(settings)
    svc.warmup()
    yield


app = FastAPI(title="FaceLock Stego API", version="1.0.0", lifespan=lifespan)
# Local demo: any port on localhost may call the API. Override with FACELOCK_CORS_REGEX for a deployment.
app.add_middleware(CORSMiddleware,
                   allow_origin_regex=os.environ.get("FACELOCK_CORS_REGEX", r"http://(localhost|127\.0\.0\.1)(:\d+)?"),
                   allow_methods=["*"], allow_headers=["*"])


def S() -> FaceLockService:
    assert svc is not None
    return svc


@app.exception_handler(UserError)
async def user_error(_: Request, exc: UserError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Locked)
async def locked_error(_: Request, exc: Locked):
    return JSONResponse(status_code=423, content={"detail": f"Too many failed attempts. Try again in "
                                                            f"{exc.status['remaining_s']} s.", "lock": exc.status})


async def read_upload(f: UploadFile | None, what: str) -> bytes:
    if f is None:
        raise UserError(f"{what} is required")
    data = await f.read()
    if not data:
        raise UserError(f"{what} is empty")
    if len(data) > MAX_BYTES:
        raise UserError(f"{what} exceeds {settings.max_upload_mb} MB")
    return data


def client_of(req: Request) -> str:
    return req.client.host if req.client else "unknown"


# --------------------------------------------------------------------------- system
@app.get("/api/health")
def health():
    return S().health()


# ------------------------------------------------------------------------- profiles
@app.get("/api/profiles")
def list_profiles():
    return S().profiles.list()


@app.post("/api/enroll")
async def enroll(label: str = Form(...), samples: list[UploadFile] = File(...)):
    imgs = [await read_upload(s, "face sample") for s in samples]
    return S().enroll(label, imgs)


@app.delete("/api/profiles/{pid}")
def delete_profile(pid: str):
    try:
        S().profiles.delete(pid)
    except (KeyError, FileNotFoundError):
        raise HTTPException(404, "profile not found")
    return {"deleted": pid}


# ----------------------------------------------------------------------------- hide
@app.post("/api/capacity")
async def capacity(cover: UploadFile = File(...)):
    arr, fmt = stego.load_image(await read_upload(cover, "cover image"), settings.max_image_pixels)
    return {"width": arr.shape[1], "height": arr.shape[0], "format": fmt,
            "capacity_bytes": stego.payload_capacity(arr.shape), "has_alpha": arr.shape[2] == 4}


@app.post("/api/hide")
async def hide(cover: UploadFile = File(...), message: str | None = Form(None),
               secret_file: UploadFile | None = File(None), profile_ids: str = Form(""),
               password: str | None = Form(None)):
    cover_bytes = await read_upload(cover, "cover image")
    fbytes = await read_upload(secret_file, "secret file") if secret_file is not None and secret_file.filename else None
    return S().hide(cover_bytes, cover.filename or "cover", message, fbytes,
                    secret_file.filename if fbytes else None, secret_file.content_type if fbytes else None,
                    [p.strip() for p in profile_ids.split(",")], password)


@app.get("/api/jobs/{job_id}/{kind}")
def job_file(job_id: str, kind: str):
    d = S().job_dir(job_id)
    meta = json.loads((d / "meta.json").read_text())
    files = {"stego": ("stego.png", "image/png", meta.get("stego_name", "stego.png")),
             "cover": ("cover.png", "image/png", "cover.png"),
             "vault": ("secret.vault", "application/octet-stream", meta.get("vault_name", "secret.vault"))}
    if kind not in files or not (d / files[kind][0]).exists():
        raise HTTPException(404, "file not found")
    fname, mime, dl = files[kind]
    return FileResponse(d / fname, media_type=mime, filename=dl)


# -------------------------------------------------------------------------- extract
@app.post("/api/challenge")
def challenge():
    return S().challenges.issue()


@app.post("/api/extract/face")
async def extract_face(request: Request, stego_image: UploadFile = File(...), vault_file: UploadFile = File(...),
                       challenge_id: str = Form(...), frames: list[UploadFile] = File(...)):
    sb = await read_upload(stego_image, "stego image")
    vb = await read_upload(vault_file, "vault file")
    fr = [await f.read() for f in frames]
    out = S().unlock_with_face(sb, vb, challenge_id, fr, client_of(request))
    return {"granted": out.granted, "reason": out.reason, **out.body}


@app.post("/api/extract/password")
async def extract_password(request: Request, stego_image: UploadFile = File(...),
                           vault_file: UploadFile = File(...), password: str = Form(...)):
    sb = await read_upload(stego_image, "stego image")
    vb = await read_upload(vault_file, "vault file")
    out = S().unlock_with_password(sb, vb, password, client_of(request))
    return {"granted": out.granted, "reason": out.reason, **out.body}


@app.post("/api/vault/inspect")
async def inspect_vault(vault_file: UploadFile = File(...)):
    try:
        v = vlt.loads(await read_upload(vault_file, "vault file"))
    except vlt.VaultError as exc:
        raise UserError(str(exc)) from exc
    return {"vault_id": v["vault_id"], "created_at": v["created_at"],
            "face_slots": (v.get("face_lock") or {}).get("slots", 0),
            "password_fallback": bool(v.get("password_lock")),
            "lock": S().log.lock_status(f"vault:{v['vault_id']}")}


# ------------------------------------------------------------------------- analysis
@app.post("/api/analyze/upload")
async def analyze_upload(cover: UploadFile = File(...), stego_image: UploadFile = File(...)):
    jid = S().create_analysis_job(await read_upload(cover, "cover"), await read_upload(stego_image, "stego"))
    return S().analyze(jid)


@app.get("/api/analyze/{job_id}")
def analyze(job_id: str):
    return S().analyze(job_id)


@app.get("/api/bitplane/{job_id}")
def bitplane(job_id: str, which: str = "stego", channel: int = 0, bit: int = 0):
    return Response(S().bit_plane_png(job_id, which, channel, bit), media_type="image/png")


@app.post("/api/attack")
async def attack(fill: float = Form(0.5), cover: UploadFile | None = File(None), sample: str | None = Form(None)):
    if cover is not None and cover.filename:
        data = await read_upload(cover, "cover")
    elif sample:
        data = demo_path(sample).read_bytes()
    else:
        raise UserError("choose a cover image or a demo sample")
    arr, _ = stego.load_image(data, 4_000_000)
    return S().attack_lab(arr, fill)


# --------------------------------------------------------------------------- logs
@app.get("/api/logs")
def logs(limit: int = 200):
    return {"items": S().log.list(limit), "stats": S().log.stats()}


@app.get("/api/logs/{attempt_id}/photo")
def log_photo(attempt_id: int):
    rec = S().log.get(attempt_id)
    if not rec or not rec.get("photo"):
        raise HTTPException(404, "no photo")
    return FileResponse(S().s.intruders_dir / Path(rec["photo"]).name, media_type="image/jpeg")


@app.delete("/api/logs")
def clear_logs():
    S().log.clear()
    return {"cleared": True}


# --------------------------------------------------------------------------- demo
def demo_path(name: str) -> Path:
    p = (settings.demo_dir / "covers" / Path(name).name)
    if p.suffix.lower() not in IMAGE_EXT or not p.exists():
        raise HTTPException(404, "demo sample not found")
    return p


@app.get("/api/demo")
def demo_index():
    covers = sorted(p.name for p in (settings.demo_dir / "covers").glob("*") if p.suffix.lower() in IMAGE_EXT)
    pair = settings.demo_dir / "pair"
    return {"covers": covers, "pair": json.loads((pair / "info.json").read_text()) if (pair / "info.json").exists() else None}


@app.get("/api/demo/covers/{name}")
def demo_cover(name: str):
    return FileResponse(demo_path(name))


@app.get("/api/demo/pair/{kind}")
def demo_pair(kind: str):
    files = {"stego": ("demo_stego.png", "image/png"), "vault": ("demo.vault", "application/octet-stream"),
             "cover": ("demo_cover.png", "image/png")}
    if kind not in files:
        raise HTTPException(404)
    p = settings.demo_dir / "pair" / files[kind][0]
    if not p.exists():
        raise HTTPException(404, "demo pair not generated - run scripts/make_demo_assets.py")
    return FileResponse(p, media_type=files[kind][1], filename=files[kind][0])
