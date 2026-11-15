#!/usr/bin/env bash
# Run each service's tests in a separate process so `catalog.py` / `main.py`
# on the two sys.path roots do not shadow each other.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="${ROOT}/.venv/bin/python"
"$PY" -m pytest -q "${ROOT}/planetary/tests"
"$PY" -m pytest -q "${ROOT}/earth/tests"
"$PY" -m pytest -q "${ROOT}/../db/tests"
# Tests del front (js/explain.js y contrato de ids de index.html), si hay Node.
if command -v node >/dev/null 2>&1; then
  node --test "${ROOT}"/../js/tests/*.test.mjs "${ROOT}"/../pages/tests/*.test.mjs
else
  echo "node no está instalado: se saltean los tests del front (js/tests)."
fi
