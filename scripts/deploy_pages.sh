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
PROJECT="${HEXASTRA_PAGES_PROJECT:-hexastra-analogos}"
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
cp -R "$ROOT/css" "$ROOT/js" "$ROOT/data" "$DIST/"
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

# Pages Functions (same-origin proxy to the tunnels) and their KV binding.
cp -R "$ROOT/pages/functions" "$STAGE/functions"
cp "$ROOT/pages/wrangler.toml" "$STAGE/wrangler.toml"
cd "$STAGE"

"${WRANGLER[@]}" pages deploy "$DIST" \
  --project-name "$PROJECT" \
  --branch "$BRANCH" \
  --commit-hash "$(git -C "$ROOT" rev-parse HEAD)" \
  --commit-message "$(git -C "$ROOT" log -1 --pretty=%s)"
