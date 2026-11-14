#!/usr/bin/env bash
# Run each service's tests in a separate process so `catalog.py` / `main.py`
# on the two sys.path roots do not shadow each other.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="${ROOT}/.venv/bin/python"
"$PY" -m pytest -q "${ROOT}/planetary/tests"
"$PY" -m pytest -q "${ROOT}/earth/tests"
"$PY" -m pytest -q "${ROOT}/../db/tests"
