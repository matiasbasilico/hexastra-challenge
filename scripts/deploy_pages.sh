#!/usr/bin/env bash
# Publish the static front (index.html, css/, js/, data/) to Cloudflare Pages.
# Every branch gets its own preview URL and every deploy its own immutable URL,
# so each version can be tried and shared.
#
#   ./scripts/deploy_pages.sh                 # deploys the current git branch
#   ./scripts/deploy_pages.sh main            # production (main) deployment
#
# Needs a Cloudflare login once: npx wrangler@3 login
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PAGES_CONFIG="${HEXASTRA_PAGES_CONFIG:-${ROOT}/pages/wrangler.production.toml}"
[[ "$PAGES_CONFIG" = /* ]] || PAGES_CONFIG="${ROOT}/${PAGES_CONFIG}"
[[ -f "$PAGES_CONFIG" ]] || { echo "No existe la configuración de Pages: $PAGES_CONFIG" >&2; exit 1; }
PROJECT="${HEXASTRA_PAGES_PROJECT:-$(sed -n 's/^name = "\(.*\)"/\1/p' "$PAGES_CONFIG" | head -1)}"
[[ -n "$PROJECT" ]] || { echo "Falta el nombre del proyecto de Pages." >&2; exit 1; }
BRANCH="${1:-$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)}"
COMMIT="$(git -C "$ROOT" rev-parse --short HEAD)"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/hexastra-pages.XXXXXX")"
DIST="$STAGE/dist"
mkdir -p "$DIST"
WRANGLER=(npx --yes wrangler@3)

if ! git -C "$ROOT" diff --quiet -- index.html css js data; then
  echo "Aviso: hay cambios sin commitear en el front; se publican igual (commit base ${COMMIT})." >&2
fi

cp "$ROOT/index.html" "$DIST/"
if [[ -f "$ROOT/classic.html" ]]; then cp "$ROOT/classic.html" "$DIST/"; fi
# assets/ lleva el logo y los favicons de la marca (docs/marca.md).
cp -R "$ROOT/css" "$ROOT/js" "$ROOT/data" "$ROOT/assets" "$DIST/"
printf '%s\n' "${COMMIT}" > "$DIST/version.txt"
cat > "$DIST/_headers" <<'EOF'
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=()
/js/*
  Cache-Control: no-cache
/data/*
  Cache-Control: no-cache
EOF

if ! "${WRANGLER[@]}" pages project list 2>/dev/null | grep -q "\b${PROJECT}\b"; then
  "${WRANGLER[@]}" pages project create "$PROJECT" --production-branch main
fi

# Pages Functions and shared runtime (standalone by default; optional legacy proxy).
cp -R "$ROOT/pages/functions" "$STAGE/functions"
cp -R "$ROOT/pages/lib" "$STAGE/lib"
cp "$PAGES_CONFIG" "$STAGE/wrangler.toml"
cd "$STAGE"

"${WRANGLER[@]}" pages deploy "$DIST" \
  --project-name "$PROJECT" \
  --branch "$BRANCH" \
  --commit-hash "$(git -C "$ROOT" rev-parse HEAD)" \
  --commit-message "$(git -C "$ROOT" log -1 --pretty=%s)"
