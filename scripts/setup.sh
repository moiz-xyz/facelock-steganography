#!/usr/bin/env bash
# One-command setup for macOS / Linux.  Usage:  bash scripts/setup.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"

echo "==> Checking tools"
command -v "$PY" >/dev/null || { echo "Python 3.10-3.12 is required"; exit 1; }
command -v node >/dev/null || { echo "Node.js 18+ is required (https://nodejs.org)"; exit 1; }
"$PY" -c 'import sys; assert (3,10) <= sys.version_info[:2] <= (3,12), "Python 3.10-3.12 required (MediaPipe wheels)"'

echo "==> Backend: virtual environment + packages"
cd "$ROOT/app/backend"
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip -q
.venv/bin/python -m pip install -q -r requirements.txt
if [ "${DEV:-0}" = "1" ]; then .venv/bin/python -m pip install -q -r requirements-dev.txt; fi

echo "==> Models (YuNet, SFace, MediaPipe Face Landmarker)"
.venv/bin/python "$ROOT/scripts/download_models.py"

echo "==> Demo assets"
[ -f demo/pair/demo.vault ] || .venv/bin/python "$ROOT/scripts/make_demo_assets.py"

echo "==> Frontend: packages + production build"
cd "$ROOT/app/frontend"
[ -f .env.local ] || cp .env.example .env.local
npm install --no-audit --no-fund
npm run build

echo
echo "Setup complete. Start the demo with:  bash scripts/run.sh"
