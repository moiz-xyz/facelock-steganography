"""Application service: orchestrates enrolment, hiding, verification and analysis.

The FastAPI layer (``main.py``) only does HTTP plumbing; every security decision
is made here, on the server.
"""
from __future__ import annotations

import base64
import json
import logging
import mimetypes
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from . import crypto, lsb, metrics, stego, steganalysis, vault
from .config import Settings
from .face_engine import FaceEngine, FaceError, cosine, decode_jpeg, l2n, resize_max
from .liveness import ChallengeBook, LandmarkAnalyzer, evaluate
from .payload import SecretPayload
from .security_log import SecurityLog
from .store import ProfileStore, load_or_create_device_key

log = logging.getLogger("facelock.service")
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class UserError(Exception):
    """Problem the user can fix; mapped to HTTP 400."""


class Locked(Exception):
    def __init__(self, status: dict):
        super().__init__(f"locked for {status['remaining_s']} s")
        self.status = status


@dataclass
class UnlockOutcome:
    granted: bool
    reason: str
    body: dict


def safe_filename(name: str, default: str = "file") -> str:
    name = SAFE_NAME.sub("_", Path(name or default).name).strip("._") or default
    return name[:80]


class FaceLockService:
    def __init__(self, settings: Settings):
        self.s = settings
        settings.ensure_dirs()
        self.device_key = load_or_create_device_key(settings.device_key_path)
        self.profiles = ProfileStore(settings, self.device_key)
        self.log = SecurityLog(settings.db_path, settings.max_failures, settings.lockout_seconds)
        self.challenges = ChallengeBook(settings.challenge_ttl_s)
        self.kdf = crypto.PasswordKDF(settings.argon2_time_cost, settings.argon2_memory_kib,
                                      settings.argon2_parallelism)
        self._engine: FaceEngine | None = None
        self._landmarks: LandmarkAnalyzer | None = None

    # ------------------------------------------------------------------ models
    @property
    def engine(self) -> FaceEngine:
        if self._engine is None:
            self._engine = FaceEngine(self.s.models_dir, self.s.face_engine)
        return self._engine

    @property
    def landmarks(self) -> LandmarkAnalyzer:
        if self._landmarks is None:
            self._landmarks = LandmarkAnalyzer(self.s.models_dir)
        return self._landmarks

    def warmup(self) -> None:
        _ = self.engine, self.landmarks

    def health(self) -> dict:
        return {"status": "ok", "face_engine": self.engine.name, "face_threshold": self.s.face_threshold,
                "liveness": "mediapipe-face-landmarker", "liveness_required": self.s.liveness_required,
                "enroll_samples": self.s.enroll_samples, "max_authorized_faces": self.s.max_authorized_faces,
                "max_failures": self.s.max_failures, "lockout_seconds": self.s.lockout_seconds,
                "profiles": len(self.profiles.list()), "fallback_errors": self.engine.fallback_errors}

    # --------------------------------------------------------------- enrolment
    def enroll(self, label: str, images: list[bytes]) -> dict:
        label = label.strip()[:40]
        if not label:
            raise UserError("please enter a name for this face profile")
        if len(images) < self.s.enroll_samples:
            raise UserError(f"{self.s.enroll_samples} face samples are required, got {len(images)}")
        embs, scores = [], []
        for i, data in enumerate(images, 1):
            try:
                e, f = self.engine.single_face_embedding(decode_jpeg(data))
            except FaceError as exc:
                raise UserError(f"sample {i}: {exc}") from exc
            embs.append(e)
            scores.append(f.score)
        sims = [cosine(embs[i], embs[j]) for i in range(len(embs)) for j in range(i + 1, len(embs))]
        if min(sims) < 0.45:
            raise UserError("samples look like different people or are very blurry - please retake")
        template = l2n(np.mean(embs, axis=0))
        quality = {"samples": len(embs), "min_pair_similarity": round(min(sims), 4),
                   "mean_pair_similarity": round(float(np.mean(sims)), 4),
                   "mean_detection_score": round(float(np.mean(scores)), 4)}
        prof = self.profiles.save(label, template, self.engine.name, quality)
        self.log.record("enroll", "ok", f"profile '{label}' enrolled", method="face")
        return prof

    # -------------------------------------------------------------------- hide
    def hide(self, cover_bytes: bytes, cover_name: str, text: str | None, file_bytes: bytes | None,
             file_name: str | None, file_mime: str | None, profile_ids: list[str],
             password: str | None) -> dict:
        warnings = []
        try:
            cover, fmt = stego.load_image(cover_bytes, self.s.max_image_pixels)
        except stego.StegoError as exc:
            raise UserError(str(exc)) from exc
        if fmt in ("JPEG", "JPG", "WEBP"):
            warnings.append(f"Your cover was {fmt}. The stego image is saved as lossless PNG. Never convert "
                            "it to JPG or send it through apps that recompress images - that destroys the hidden data.")
        if file_bytes is not None:
            payload = SecretPayload.from_file(safe_filename(file_name or "secret.bin"), file_bytes,
                                              file_mime or mimetypes.guess_type(file_name or "")[0])
        elif text:
            payload = SecretPayload.from_text(text)
        else:
            raise UserError("enter a secret message or choose a file to hide")

        profile_ids = list(dict.fromkeys(p for p in profile_ids if p))
        if len(profile_ids) > self.s.max_authorized_faces:
            raise UserError(f"at most {self.s.max_authorized_faces} people can be authorised")
        if password is not None and password != "" and len(password) < 8:
            raise UserError("backup password must be at least 8 characters")
        faces = []
        for pid in profile_ids:
            try:
                p = self.profiles.get(pid)
            except KeyError as exc:
                raise UserError(f"unknown face profile {pid}") from exc
            if p["engine"] != self.engine.name:
                raise UserError(f"profile '{p['label']}' was enrolled with a different face engine")
            faces.append(vault.FaceSlot(p["label"], p["id"], p["template_np"], p["engine"]))
        if not faces and not password:
            raise UserError("select at least one enrolled face (or set a backup password)")

        dek = crypto.random_key()
        try:
            res = stego.hide(cover, payload, dek)
        except lsb.CapacityError as exc:
            raise UserError(str(exc)) from exc
        stego_arr = res.stego_rgb if res.alpha is None else np.dstack([res.stego_rgb, res.alpha])
        stego_png = stego.to_png_bytes(res.stego_rgb, res.alpha)
        t0 = time.perf_counter()
        v = vault.create_vault(dek, stego.pixel_fingerprint(stego_arr), self.device_key, faces,
                               self.s.face_threshold, password or None, self.kdf)
        vault_seconds = time.perf_counter() - t0
        quality = metrics.quality(cover, stego_arr)

        job_id = uuid.uuid4().hex[:16]
        jdir = self.s.jobs_dir / job_id
        jdir.mkdir(parents=True)
        base = safe_filename(Path(cover_name or "cover").stem, "cover")
        (jdir / "cover.png").write_bytes(stego.to_png_bytes(*lsb.to_carrier(cover)))
        (jdir / "stego.png").write_bytes(stego_png)
        (jdir / "secret.vault").write_bytes(vault.dumps(v))
        meta = {"job_id": job_id, "base": base, "vault_id": v["vault_id"], "width": cover.shape[1],
                "height": cover.shape[0], "capacity_bytes": res.capacity_bytes,
                "embedded_bytes": res.embedded_bytes,
                "usage_pct": round(100 * res.embedded_bytes / res.capacity_bytes, 3),
                "payload": {"kind": "text" if payload.is_text else "file", "size": len(payload.data),
                            "name": payload.name},
                "embed_seconds": round(res.embed_seconds, 4), "vault_seconds": round(vault_seconds, 4),
                "metrics": quality, "authorized": [f.label for f in faces],
                "password_fallback": bool(password), "warnings": warnings,
                "stego_name": f"{base}_stego.png", "vault_name": f"{base}.vault"}
        (jdir / "meta.json").write_text(json.dumps(meta, indent=2))
        self.log.record("hide", "ok", f"{meta['payload']['kind']} of {meta['payload']['size']} B hidden",
                        vault_id=v["vault_id"], details={"authorized": meta["authorized"],
                                                         "password": bool(password)})
        return meta

    def job_dir(self, job_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{16}", job_id or ""):
            raise UserError("invalid job id")
        d = self.s.jobs_dir / job_id
        if not d.exists():
            raise UserError("job not found (it may have been cleaned up)")
        return d

    # ------------------------------------------------------------------ unlock
    def _common_prechecks(self, stego_bytes: bytes, vault_bytes: bytes) -> tuple[dict, np.ndarray, str]:
        try:
            v = vault.loads(vault_bytes)
        except vault.VaultError as exc:
            raise UserError(str(exc)) from exc
        lock_key = f"vault:{v['vault_id']}"
        st = self.log.lock_status(lock_key)
        if st["locked"]:
            self.log.record("extract", "locked", f"locked out ({st['remaining_s']} s remaining)",
                            vault_id=v["vault_id"])
            raise Locked(st)
        try:
            arr, fmt = stego.load_image(stego_bytes, self.s.max_image_pixels)
        except stego.StegoError as exc:
            raise UserError(str(exc)) from exc
        if fmt not in ("PNG", "BMP", "TIFF"):
            raise UserError(f"stego image is {fmt}: lossy formats destroy LSB data - upload the original PNG")
        if stego.pixel_fingerprint(arr) != v["image_sha256"]:
            raise UserError("this image does not belong to this vault (or it was modified after hiding)")
        return v, arr, lock_key

    def _reveal(self, arr: np.ndarray, dek: bytes) -> dict:
        t0 = time.perf_counter()
        try:
            p = stego.reveal(arr, dek)
        except stego.StegoError as exc:
            raise UserError(str(exc)) from exc
        out = {"kind": "text" if p.is_text else "file", "size": len(p.data), "name": p.name, "mime": p.mime,
               "extract_seconds": round(time.perf_counter() - t0, 4)}
        if p.is_text:
            out["text"] = p.text()
        else:
            out["data_b64"] = base64.b64encode(p.data).decode()
        return out

    def _deny(self, v: dict, lock_key: str, method: str, reason: str, client: str | None,
              score: float | None = None, frame: np.ndarray | None = None, details: dict | None = None) -> dict:
        st = self.log.register_failure(lock_key)
        aid = self.log.record("extract", "denied", reason, method=method, vault_id=v["vault_id"], score=score,
                              client=client, details=details)
        if frame is not None:
            name = f"{aid}.jpg"
            cv2.imwrite(str(self.s.intruders_dir / name), resize_max(frame, 480), [cv2.IMWRITE_JPEG_QUALITY, 85])
            self.log.set_photo(aid, name)
        return st

    def unlock_with_face(self, stego_bytes: bytes, vault_bytes: bytes, challenge_id: str,
                         frames: list[bytes], client: str | None) -> UnlockOutcome:
        t_start = time.perf_counter()
        v, arr, lock_key = self._common_prechecks(stego_bytes, vault_bytes)
        challenge = self.challenges.consume(challenge_id)
        if challenge is None:
            raise UserError("liveness challenge expired or already used - start a new scan")
        try:
            threshold, slots = vault.open_face_lock(v, self.device_key)
        except vault.VaultError as exc:
            raise UserError(str(exc)) from exc
        if len(frames) < self.s.min_liveness_frames:
            raise UserError(f"camera sent only {len(frames)} frames; at least {self.s.min_liveness_frames} needed")

        imgs = []
        for f in frames[:120]:
            try:
                imgs.append(resize_max(decode_jpeg(f)))
            except FaceError:
                continue
        obs = [self.landmarks.observe(im) for im in imgs]
        live = evaluate(obs, challenge, self.s.min_liveness_frames, self.s.blink_ratio, self.s.turn_delta)
        face_idx = [i for i, o in enumerate(obs) if o.faces == 1]
        evidence = imgs[face_idx[len(face_idx) // 2]] if face_idx else (imgs[len(imgs) // 2] if imgs else None)
        body = {"liveness": live.public(), "threshold": threshold, "challenge": challenge}

        if self.s.liveness_required and not live.passed:
            st = self._deny(v, lock_key, "face", f"liveness failed: {live.reason}", client, frame=evidence,
                            details={"challenge": challenge, "blinks": live.blinks})
            return UnlockOutcome(False, f"Liveness check failed: {live.reason}", dict(body, lock=st))

        # ---- identity: frontal, eyes-open frames --------------------------------------------
        frontal = [i for i in face_idx
                   if obs[i].ear >= 0.8 * live.ear_baseline and abs(obs[i].yaw - live.yaw_baseline) < 0.06]
        pick = frontal[:: max(1, len(frontal) // 5)][:5] or face_idx[:5]
        live_embs = []
        for i in pick:
            try:
                live_embs.append(self.engine.single_face_embedding(imgs[i], min_size=50, min_score=0.7)[0])
            except FaceError:
                continue
        if not live_embs:
            st = self._deny(v, lock_key, "face", "no usable face for recognition", client, frame=evidence)
            return UnlockOutcome(False, "No usable face found for recognition", dict(body, lock=st))
        live_t = l2n(np.mean(live_embs, axis=0))
        scored = sorted(((cosine(live_t, s["template_np"]), s) for s in slots), key=lambda t: -t[0])
        best_score, best_slot = scored[0]
        body["scores"] = [{"label": s["label"], "similarity": round(sc, 4)} for sc, s in scored]
        body["best_similarity"] = round(best_score, 4)

        # ---- consistency: the same person must be present throughout the burst -------------
        spread = face_idx[:: max(1, len(face_idx) // 6)][:6]
        cons = []
        for i in spread:
            try:
                cons.append(cosine(live_t, self.engine.single_face_embedding(imgs[i], 50, 0.7)[0]))
            except FaceError:
                continue
        body["consistency_min"] = round(min(cons), 4) if cons else None
        if cons and min(cons) < 0.8 * threshold:
            st = self._deny(v, lock_key, "face", "face changed during the scan (possible swap attack)", client,
                            score=best_score, frame=evidence)
            return UnlockOutcome(False, "Different faces detected during the scan", dict(body, lock=st))

        if best_score < threshold:
            st = self._deny(v, lock_key, "face", f"face not recognised (similarity {best_score:.3f} < {threshold})",
                            client, score=best_score, frame=evidence)
            return UnlockOutcome(False, "Face not recognised", dict(body, lock=st))

        dek = vault.unwrap_face_slot(v, self.device_key, best_slot)
        secret = self._reveal(arr, dek)
        self.log.register_success(lock_key)
        self.log.record("extract", "granted", f"face matched '{best_slot['label']}'", method="face",
                        vault_id=v["vault_id"], score=best_score, matched_label=best_slot["label"], client=client)
        body.update(secret=secret, matched_label=best_slot["label"],
                    total_seconds=round(time.perf_counter() - t_start, 3))
        return UnlockOutcome(True, f"Welcome, {best_slot['label']}", body)

    def unlock_with_password(self, stego_bytes: bytes, vault_bytes: bytes, password: str,
                             client: str | None) -> UnlockOutcome:
        v, arr, lock_key = self._common_prechecks(stego_bytes, vault_bytes)
        try:
            dek = vault.open_password_lock(v, password or "", None)
        except vault.VaultError as exc:
            if "no backup password" in str(exc):
                raise UserError(str(exc)) from exc
            st = self._deny(v, lock_key, "password", str(exc), client)
            return UnlockOutcome(False, "Wrong backup password", {"lock": st})
        secret = self._reveal(arr, dek)
        self.log.register_success(lock_key)
        self.log.record("extract", "granted", "backup password accepted", method="password",
                        vault_id=v["vault_id"], client=client)
        return UnlockOutcome(True, "Backup password accepted", {"secret": secret})

    # ---------------------------------------------------------------- analysis
    def create_analysis_job(self, cover_bytes: bytes, stego_bytes: bytes) -> str:
        try:
            c, _ = stego.load_image(cover_bytes, self.s.max_image_pixels)
            s, _ = stego.load_image(stego_bytes, self.s.max_image_pixels)
        except stego.StegoError as exc:
            raise UserError(str(exc)) from exc
        if c.shape[:2] != s.shape[:2]:
            raise UserError("cover and stego images must have the same dimensions")
        job_id = uuid.uuid4().hex[:16]
        d = self.s.jobs_dir / job_id
        d.mkdir(parents=True)
        (d / "cover.png").write_bytes(stego.to_png_bytes(*lsb.to_carrier(c)))
        (d / "stego.png").write_bytes(stego.to_png_bytes(*lsb.to_carrier(s)))
        (d / "meta.json").write_text(json.dumps({"job_id": job_id, "analysis_only": True,
                                                 "width": c.shape[1], "height": c.shape[0]}))
        return job_id

    def _job_images(self, job_id: str) -> tuple[np.ndarray, np.ndarray, dict]:
        d = self.job_dir(job_id)
        c, _ = stego.load_image((d / "cover.png").read_bytes(), 10**9)
        s, _ = stego.load_image((d / "stego.png").read_bytes(), 10**9)
        return c[..., :3], s[..., :3], json.loads((d / "meta.json").read_text())

    def analyze(self, job_id: str) -> dict:
        c, s, meta = self._job_images(job_id)
        b64 = lambda a: "data:image/png;base64," + base64.b64encode(metrics.png_bytes(a)).decode()  # noqa: E731
        q = metrics.quality(c, s)
        per_channel = [{"channel": n, "psnr": None if (p := metrics.psnr(c[..., i], s[..., i])) == float("inf")
                        else round(p, 3), "changed": int((c[..., i] != s[..., i]).sum())}
                       for i, n in enumerate("RGB")]
        return {"job_id": job_id, "meta": meta, "metrics": q, "per_channel": per_channel,
                "cover": b64(metrics.thumbnail(c)), "stego": b64(metrics.thumbnail(s)),
                "heatmap": b64(metrics.thumbnail(metrics.diff_heatmap(c, s))),
                "histogram": metrics.histograms(c, s)}

    def bit_plane_png(self, job_id: str, which: str, channel: int, bit: int) -> bytes:
        if which not in ("cover", "stego") or channel not in (0, 1, 2) or not 0 <= bit <= 7:
            raise UserError("invalid bit-plane request")
        c, s, _ = self._job_images(job_id)
        return metrics.png_bytes(metrics.thumbnail(metrics.bit_plane(c if which == "cover" else s, channel, bit)))

    # -------------------------------------------------------------- attack lab
    def attack_lab(self, cover: np.ndarray, fill: float) -> dict:
        fill = float(min(1.0, max(0.02, fill)))
        rgb, _ = lsb.to_carrier(cover)
        n_bytes = int(lsb.capacity_bytes(rgb.shape) * fill)
        data = crypto.random_bytes(n_bytes)             # ciphertext is indistinguishable from random
        seq = lsb.embed_bytes(rgb, data, None)
        rnd = lsb.embed_bytes(rgb, data, crypto.random_key())
        scans = {name: steganalysis.prefix_scan(img) for name, img in
                 (("cover", rgb), ("sequential", seq), ("random", rnd))}
        b64 = lambda a: "data:image/png;base64," + base64.b64encode(metrics.png_bytes(  # noqa: E731
            metrics.thumbnail(a, 520))).decode()
        series = [{"pct": scans["cover"][i]["pct"], "cover": scans["cover"][i]["p"],
                   "sequential": scans["sequential"][i]["p"], "random": scans["random"][i]["p"]}
                  for i in range(len(scans["cover"]))]
        return {"fill": fill, "payload_bytes": n_bytes, "width": rgb.shape[1], "height": rgb.shape[0],
                "series": series,
                "summary": {k: steganalysis.detection_summary(v) for k, v in scans.items()},
                "psnr": {"sequential": round(metrics.psnr(rgb, seq), 3), "random": round(metrics.psnr(rgb, rnd), 3)},
                "lsb_planes": {"cover": b64(metrics.bit_plane(rgb, 0, 0)),
                               "sequential": b64(metrics.bit_plane(seq, 0, 0)),
                               "random": b64(metrics.bit_plane(rnd, 0, 0))}}
