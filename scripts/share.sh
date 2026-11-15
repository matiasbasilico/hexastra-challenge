#!/usr/bin/env bash
# Expose this checkout's planetary-service and earth-service through two
# Cloudflare quick tunnels and print a share link for the front on Cloudflare Pages.
#
#   ./scripts/share.sh                                  # front: https://hexastra-analogos.pages.dev
#   USE_RUNNING=1 PLANETARY_PORT=8766 EARTH_PORT=8767 ./scripts/share.sh   # túnel a servicios ya levantados
#   ./scripts/share.sh https://feat-x.hexastra-analogos.pages.dev   # a branch preview
#
# The link works only while this script (and the Mac) keeps running.
# Quick-tunnel URLs change every run: share the new link each time.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PAGES_CONFIG="${HEXASTRA_PAGES_CONFIG:-${ROOT}/pages/wrangler.toml}"
[[ "$PAGES_CONFIG" = /* ]] || PAGES_CONFIG="${ROOT}/${PAGES_CONFIG}"
[[ -f "$PAGES_CONFIG" ]] || { echo "No existe la configuración de Pages: $PAGES_CONFIG" >&2; exit 1; }
FRONT_URL="${1:-${HEXASTRA_PAGES_URL:-https://hexastra-analogos.pages.dev}}"
PLANETARY_PORT="${PLANETARY_PORT:-18766}"
EARTH_PORT="${EARTH_PORT:-18767}"
UVICORN="${ROOT}/services/.venv/bin/uvicorn"
LOGDIR="$(mktemp -d "${TMPDIR:-/tmp}/hexastra-share.XXXXXX")"

command -v cloudflared >/dev/null || { echo "Falta cloudflared (brew install cloudflared)." >&2; exit 1; }
[ -x "$UVICORN" ] || { echo "Falta el venv: corré ./run_all.sh una vez o creá services/.venv." >&2; exit 1; }
for port in "$PLANETARY_PORT" "$EARTH_PORT"; do
  [ "${USE_RUNNING:-0}" = "1" ] && break
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

if [ "${USE_RUNNING:-0}" != "1" ]; then
  (cd "${ROOT}/services/planetary" && exec "$UVICORN" main:app --host 127.0.0.1 --port "$PLANETARY_PORT" >"${LOGDIR}/planetary.log" 2>&1) &
  PIDS+=($!)
  (cd "${ROOT}/services/earth" && PLANETARY_URL="http://127.0.0.1:${PLANETARY_PORT}" exec "$UVICORN" main:app --host 127.0.0.1 --port "$EARTH_PORT" >"${LOGDIR}/earth.log" 2>&1) &
  PIDS+=($!)
fi

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

KV_ID="$(sed -n 's/^id = "\(.*\)"/\1/p' "$PAGES_CONFIG" | head -1)"
if [ -n "$KV_ID" ] && [ "${SKIP_KV:-0}" != "1" ]; then
  if npx --yes wrangler@3 kv key put --namespace-id="$KV_ID" planetary "$P_URL" >/dev/null 2>&1 \
     && npx --yes wrangler@3 kv key put --namespace-id="$KV_ID" earth "$E_URL" >/dev/null 2>&1; then
    echo "Proxy de Pages actualizado: /api/planetary y /api/earth apuntan a estos túneles."
  else
    echo "Aviso: no pude escribir las URLs en Cloudflare KV (¿npx wrangler@3 login?). El proxy de Pages no las va a ver." >&2
  fi
fi

echo
echo "planetary-service  ${P_URL}"
echo "earth-service      ${E_URL}"
echo
echo "Link para compartir (usa el proxy de Pages, no cambia):"
echo "  ${FRONT_URL%/}/"
echo "Link directo a estos túneles (cambia en cada corrida):"
echo "  ${FRONT_URL%/}/?planetary=${P_URL}&earth=${E_URL}"
echo
echo "Logs en ${LOGDIR}. Ctrl+C corta los servicios y los túneles."
wait
