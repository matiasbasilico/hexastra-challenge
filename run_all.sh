#!/usr/bin/env bash
# Start planetary-service (:8766), earth-service (:8767) and the static front (:8765).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="${ROOT}/services/.venv/bin/python"
PIP="${ROOT}/services/.venv/bin/pip"
UVICORN="${ROOT}/services/.venv/bin/uvicorn"

if [ ! -x "$PY" ]; then
  python3 -m venv "${ROOT}/services/.venv"
  PY="${ROOT}/services/.venv/bin/python"
  PIP="${ROOT}/services/.venv/bin/pip"
  UVICORN="${ROOT}/services/.venv/bin/uvicorn"
  "$PIP" install -U pip
  "$PIP" install -r "${ROOT}/services/planetary/requirements.txt"
  "$PIP" install -r "${ROOT}/services/earth/requirements.txt"
fi

# Make sure both requirement sets are present (earth needs numpy).
"$PY" -c "import fastapi,uvicorn,httpx,numpy" 2>/dev/null || {
  "$PIP" install -r "${ROOT}/services/planetary/requirements.txt"
  "$PIP" install -r "${ROOT}/services/earth/requirements.txt"
}

export PLANETARY_URL="${PLANETARY_URL:-http://127.0.0.1:8766}"

PIDS=()
cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

cd "${ROOT}/services/planetary"
"$UVICORN" main:app --host 127.0.0.1 --port 8766 &
PIDS+=($!)

cd "${ROOT}/services/earth"
"$UVICORN" main:app --host 127.0.0.1 --port 8767 &
PIDS+=($!)

cd "${ROOT}"
"$PY" -m http.server 8765 --bind 127.0.0.1 &
PIDS+=($!)

echo
echo "planetary-service  http://127.0.0.1:8766/docs"
echo "earth-service      http://127.0.0.1:8767/docs"
echo "front              http://127.0.0.1:8765/"
echo "Ctrl+C detiene los tres."
echo

wait
