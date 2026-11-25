#!/usr/bin/env bash
# Reproduce every artefact from scratch: tests -> dataset -> benchmarks -> charts -> diagrams
# -> (optional browser E2E + screenshots) -> proposal/report -> presentation.
# Requires DEV=1 setup (pytest, matplotlib, playwright) and, for documents, LibreOffice + poppler.
#   bash scripts/run_all.sh            # everything except the browser test
#   UI=1 bash scripts/run_all.sh       # also run the browser E2E test (starts servers itself)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/app/backend/.venv/bin/python"
export GLOG_minloglevel=2
cd "$ROOT"
echo "==> unit + API tests";     (cd app/backend && "$PY" -m pytest -q -p no:warnings --junitxml="$ROOT/dataset/results/pytest.xml" tests)
echo "==> dataset";              "$PY" scripts/build_dataset.py
echo "==> demo assets";          "$PY" scripts/make_demo_assets.py
echo "==> benchmarks";           "$PY" scripts/benchmark.py
echo "==> charts";               "$PY" scripts/make_charts.py
echo "==> diagrams";             "$PY" scripts/make_diagrams.py
if [ "${UI:-0}" = "1" ]; then
  echo "==> browser E2E (port 3100)"
  (cd app/backend && .venv/bin/uvicorn main:app --port 8000 >/dev/null 2>&1 &) ; (cd app/frontend && npx next start -p 3100 >/dev/null 2>&1 &)
  sleep 8; "$PY" scripts/ui_e2e.py --front http://localhost:3100 || true
fi
echo "==> documents";            (cd scripts/doctools && npm install --no-audit --no-fund >/dev/null); "$PY" scripts/build_docs.py
echo "==> presentation";         "$PY" scripts/build_ppt.py
echo "All artefacts rebuilt."
