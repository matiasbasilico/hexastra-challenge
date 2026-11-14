#!/usr/bin/env bash
# Expose this checkout's planetary-service and earth-service through two
# Cloudflare quick tunnels and print a share link for the front on Cloudflare Pages.
#
#   ./scripts/share.sh                                  # front: https://hexastra-analogos.pages.dev
#   ./scripts/share.sh https://feat-x.hexastra-analogos.pages.dev   # a branch preview
#
# The link works only while this script (and the Mac) keeps running.
# Quick-tunnel URLs change every run: share the new link each time.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONT_URL="${1:-${HEXASTRA_PAGES_URL:-https://hexastra-analogos.pages.dev}}"
PLANETARY_PORT="${PLANETARY_PORT:-18766}"
EARTH_PORT="${EARTH_PORT:-18767}"
UVICORN="${ROOT}/services/.venv/bin/uvicorn"
LOGDIR="$(mktemp -d "${TMPDIR:-/tmp}/hexastra-share.XXXXXX")"

command -v cloudflared >/dev/null || { echo "Falta cloudflared (brew install cloudflared)." >&2; exit 1; }
[ -x "$UVICORN" ] || { echo "Falta el venv: corré ./run_all.sh una vez o creá services/.venv." >&2; exit 1; }
for port in "$PLANETARY_PORT" "$EARTH_PORT"; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "El puerto $port ya está en uso. Elegí otro con PLANETARY_PORT / EARTH_PORT." >&2
    exit 1
  fi
done

PIDS=()
cleanup() {
  for pid in "${PIDS[@]:-}"; do kill "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM

(cd "${ROOT}/services/planetary" && exec "$UVICORN" main:app --host 127.0.0.1 --port "$PLANETARY_PORT" >"${LOGDIR}/planetary.log" 2>&1) &
PIDS+=($!)
(cd "${ROOT}/services/earth" && PLANETARY_URL="http://127.0.0.1:${PLANETARY_PORT}" exec "$UVICORN" main:app --host 127.0.0.1 --port "$EARTH_PORT" >"${LOGDIR}/earth.log" 2>&1) &
PIDS+=($!)

wait_for() {  # url, tries
  local i
  for i in $(seq 1 "$2"); do
    curl -sf -m 5 "$1" >/dev/null 2>&1 && return 0
    sleep 1
  done
  return 1
}
wait_for "http://127.0.0.1:${PLANETARY_PORT}/health" 30 || { echo "planetary-service no arrancó; ver ${LOGDIR}/planetary.log" >&2; exit 1; }
wait_for "http://127.0.0.1:${EARTH_PORT}/health" 30 || { echo "earth-service no arrancó; ver ${LOGDIR}/earth.log" >&2; exit 1; }

start_tunnel() {  # name, port
  cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:$2" >"${LOGDIR}/tunnel-$1.log" 2>&1 &
  PIDS+=($!)
}
tunnel_url() {  # name
  local i url
  for i in $(seq 1 60); do
    url="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "${LOGDIR}/tunnel-$1.log" | head -1 || true)"
    [ -n "$url" ] && { echo "$url"; return 0; }
    sleep 1
  done
  return 1
}
start_tunnel planetary "$PLANETARY_PORT"
start_tunnel earth "$EARTH_PORT"
P_URL="$(tunnel_url planetary)" || { echo "No obtuve la URL del túnel de planetary; ver ${LOGDIR}" >&2; exit 1; }
E_URL="$(tunnel_url earth)" || { echo "No obtuve la URL del túnel de earth; ver ${LOGDIR}" >&2; exit 1; }

wait_for "${P_URL}/health" 60 || echo "Aviso: ${P_URL}/health todavía no responde desde esta Mac (suele ser la caché DNS local; desde afuera normalmente ya anda)." >&2
wait_for "${E_URL}/health" 60 || echo "Aviso: ${E_URL}/health todavía no responde desde esta Mac (suele ser la caché DNS local; desde afuera normalmente ya anda)." >&2

echo
echo "planetary-service  ${P_URL}"
echo "earth-service      ${E_URL}"
echo
echo "Link para compartir:"
echo "  ${FRONT_URL%/}/?planetary=${P_URL}&earth=${E_URL}"
echo
echo "Logs en ${LOGDIR}. Ctrl+C corta los servicios y los túneles."
wait
