#!/usr/bin/env bash
set -euo pipefail

ROOT=${TW_STOCK_PLATFORM_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
FRONTEND_DIR="$ROOT/frontend"
PORT=${TW_PRODUCT_FIXTURE_PORT:-18014}
BASE_URL="http://127.0.0.1:${PORT}"
ARTIFACT_ROOT=${TW_PRODUCT_FIXTURE_ARTIFACT_ROOT:-"$ROOT/tmp/product_fixture_acceptance"}
SERVER_LOG="$ARTIFACT_ROOT/vite.log"
PYTHON=${TW_STOCK_PYTHON:-$(command -v python3 || command -v python || true)}

mkdir -p "$ARTIFACT_ROOT"

if ! "$FRONTEND_DIR/node_modules/.bin/playwright" --version >/dev/null 2>&1; then
  echo "Playwright is missing. Run: cd frontend && corepack pnpm install" >&2
  exit 2
fi
if [[ -z "$PYTHON" ]]; then
  echo "Python is required to serve the built fixture frontend." >&2
  exit 2
fi
if ! (
  cd "$FRONTEND_DIR"
  node -e "import('node:fs').then(fs => import('playwright').then(({ chromium }) => fs.accessSync(chromium.executablePath())))"
) >/dev/null 2>&1; then
  echo "Playwright Chromium is missing. Run: cd frontend && corepack pnpm exec playwright install chromium" >&2
  exit 2
fi

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

(
  cd "$FRONTEND_DIR"
  corepack pnpm build
) >"$ARTIFACT_ROOT/build.log" 2>&1

(
  cd "$FRONTEND_DIR/dist"
  exec "$PYTHON" -m http.server "$PORT" --bind 127.0.0.1
) >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!

for _ in $(seq 1 60); do
  if curl -fsS "$BASE_URL/" >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Fixture server exited before becoming ready. See $SERVER_LOG" >&2
    exit 1
  fi
  sleep 0.25
done
curl -fsS "$BASE_URL/" >/dev/null

cd "$FRONTEND_DIR"
TW_STOCK_MONITOR_BASE_URL="$BASE_URL" \
TW_UI2D_WORKBENCH_ARTIFACT_DIR="$ARTIFACT_ROOT/healthy" \
  node tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs \
  >"$ARTIFACT_ROOT/healthy.stdout.json"

TW_STOCK_MONITOR_BASE_URL="$BASE_URL" \
TW_UI2D_FAULT_ISOLATION=true \
TW_UI2D_WORKBENCH_ARTIFACT_DIR="$ARTIFACT_ROOT/fault" \
  node tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs \
  >"$ARTIFACT_ROOT/fault.stdout.json"

echo "Product fixture acceptance passed: $ARTIFACT_ROOT"
