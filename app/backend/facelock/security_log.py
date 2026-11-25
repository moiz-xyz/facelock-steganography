"""Persistent security audit log and brute-force lockout (SQLite)."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


class SecurityLog:
    def __init__(self, db_path: Path, max_failures: int = 3, lockout_seconds: int = 60):
        self.max_failures = max_failures
        self.lockout_seconds = lockout_seconds
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS attempts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL, action TEXT NOT NULL, method TEXT, vault_id TEXT,
                result TEXT NOT NULL, reason TEXT, score REAL, matched_label TEXT,
                client TEXT, photo TEXT, details TEXT);
            CREATE TABLE IF NOT EXISTS lockouts(
                key TEXT PRIMARY KEY, failures INTEGER NOT NULL DEFAULT 0,
                locked_until REAL NOT NULL DEFAULT 0);
        """)
        self._db.commit()

    # ------------------------------------------------------------------ attempts
    def record(self, action: str, result: str, reason: str = "", method: str | None = None,
               vault_id: str | None = None, score: float | None = None, matched_label: str | None = None,
               client: str | None = None, photo: str | None = None, details: dict | None = None) -> int:
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO attempts(ts,action,method,vault_id,result,reason,score,matched_label,client,photo,details)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(timespec="seconds"), action, method, vault_id, result,
                 reason, score, matched_label, client, photo, json.dumps(details) if details else None))
            self._db.commit()
            return int(cur.lastrowid)

    def set_photo(self, attempt_id: int, photo: str) -> None:
        with self._lock:
            self._db.execute("UPDATE attempts SET photo=? WHERE id=?", (photo, attempt_id))
            self._db.commit()

    def list(self, limit: int = 200) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT * FROM attempts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["details"] = json.loads(d["details"]) if d["details"] else None
            out.append(d)
        return out

    def get(self, attempt_id: int) -> dict | None:
        with self._lock:
            r = self._db.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
        return dict(r) if r else None

    def stats(self) -> dict:
        with self._lock:
            rows = self._db.execute("SELECT result, COUNT(*) c FROM attempts GROUP BY result").fetchall()
        return {r["result"]: r["c"] for r in rows}

    def clear(self) -> None:
        with self._lock:
            self._db.execute("DELETE FROM attempts")
            self._db.execute("DELETE FROM lockouts")
            self._db.commit()

    # ------------------------------------------------------------------- lockout
    def lock_status(self, key: str) -> dict:
        with self._lock:
            r = self._db.execute("SELECT failures, locked_until FROM lockouts WHERE key=?", (key,)).fetchone()
        now = time.time()
        if not r:
            return {"locked": False, "failures": 0, "remaining_s": 0, "max_failures": self.max_failures}
        remaining = max(0, int(round(r["locked_until"] - now)))
        failures = r["failures"]
        if r["locked_until"] and remaining == 0 and failures >= self.max_failures:
            failures = 0   # lockout served -> fresh start
        return {"locked": remaining > 0, "failures": failures, "remaining_s": remaining,
                "max_failures": self.max_failures}

    def register_failure(self, key: str) -> dict:
        with self._lock:
            r = self._db.execute("SELECT failures, locked_until FROM lockouts WHERE key=?", (key,)).fetchone()
            now = time.time()
            failures = 0 if not r else r["failures"]
            if r and r["locked_until"] and r["locked_until"] <= now and failures >= self.max_failures:
                failures = 0
            failures += 1
            locked_until = now + self.lockout_seconds if failures >= self.max_failures else 0
            self._db.execute("INSERT INTO lockouts(key,failures,locked_until) VALUES(?,?,?) "
                             "ON CONFLICT(key) DO UPDATE SET failures=excluded.failures, "
                             "locked_until=excluded.locked_until", (key, failures, locked_until))
            self._db.commit()
        return self.lock_status(key)

    def register_success(self, key: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM lockouts WHERE key=?", (key,))
            self._db.commit()
