#!/usr/bin/env bash
# Start backend (port 8000) and frontend (port 3000, or FRONT_PORT).  Ctrl+C stops both.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONT_PORT="${FRONT_PORT:-3000}"
cd "$ROOT/app/backend"
GLOG_minloglevel=2 .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 &
BACK=$!
trap 'kill $BACK 2>/dev/null' EXIT
cd "$ROOT/app/frontend"
echo "FaceLock Stego: open http://localhost:$FRONT_PORT   (API docs: http://localhost:8000/docs)"
npx next start -p "$FRONT_PORT"
