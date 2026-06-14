#!/usr/bin/env bash
set -u

ROOT=${TW_STOCK_PLATFORM_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
PY=${TW_STOCK_PYTHON:-python}
NGROK=${NGROK_BIN:-ngrok}
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

is_listening() {
  ss -ltn 2>/dev/null | awk "{print \$4}" | grep -Eq "(^|:)${1}$"
}

start_backend() {
  if is_listening 5000; then
    return 0
  fi
  cd "$ROOT" || exit 1
  setsid env \
    ${DATABASE_URL:+DATABASE_URL="$DATABASE_URL"} \
    AGENT_LIVE_TRADING_ENABLED=false \
    ENABLE_PENDING_ORDER_WORKER=false \
    ENABLE_PORTFOLIO_MONITOR=false \
    ENABLE_TW_STOCK_MONITOR_WORKER=false \
    PYTHON_API_HOST=0.0.0.0 \
    PYTHON_API_PORT=5000 \
    PYTHONUNBUFFERED=1 \
    "$PY" backend/run.py >> "$LOG_DIR/backend_5000.log" 2>&1 < /dev/null &
  echo "$(date -Is) started backend:5000" >> "$LOG_DIR/service_watchdog.log"
}

start_frontend() {
  if is_listening 8000; then
    return 0
  fi
  cd "$ROOT" || exit 1
  if [ ! -f "$ROOT/frontend/dist/index.html" ]; then
    (
      cd "$ROOT/frontend" || exit 1
      corepack pnpm build >> "$LOG_DIR/frontend_build.log" 2>&1
    ) || {
      echo "$(date -Is) frontend build failed" >> "$LOG_DIR/service_watchdog.log"
      return 1
    }
  fi
  setsid env \
    FRONTEND_HOST=0.0.0.0 \
    FRONTEND_PORT=8000 \
    FRONTEND_DIST="$ROOT/frontend/dist" \
    BACKEND_URL=http://127.0.0.1:5000 \
    "$PY" "$ROOT/scripts/serve_frontend_static_proxy.py" >> "$LOG_DIR/frontend_8000.log" 2>&1 < /dev/null &
  echo "$(date -Is) started frontend:8000" >> "$LOG_DIR/service_watchdog.log"
}

start_ngrok() {
  if is_listening 4040; then
    return 0
  fi
  cd "$ROOT" || exit 1
  setsid "$NGROK" http 8000 --log=stdout >> "$LOG_DIR/ngrok_8000.log" 2>&1 < /dev/null &
  echo "$(date -Is) started ngrok:8000" >> "$LOG_DIR/service_watchdog.log"
}

start_backend
start_frontend
start_ngrok
