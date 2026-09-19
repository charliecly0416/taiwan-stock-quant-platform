#!/usr/bin/env bash
set -uo pipefail

ROOT=${TW_STOCK_PLATFORM_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
PY=${TW_STOCK_PYTHON:-}
NGROK=${NGROK_BIN:-ngrok}
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
for required_command in curl flock ss setsid; do
  if ! command -v "$required_command" >/dev/null 2>&1; then
    echo "$(date -Is) required command not found: $required_command" >> "$LOG_DIR/service_watchdog.log"
    exit 1
  fi
done
if [ -z "$PY" ]; then
  PY=$(command -v python3 || command -v python || true)
fi
if [ -z "$PY" ]; then
  echo "$(date -Is) python interpreter not found" >> "$LOG_DIR/service_watchdog.log"
  exit 1
fi

BACKEND_PORT=${TW_STOCK_BACKEND_PORT:-5000}
FRONTEND_PORT=${TW_STOCK_FRONTEND_PORT:-8000}
NGROK_PORT=${TW_STOCK_NGROK_PORT:-4040}
BACKEND_HOST=${TW_STOCK_BACKEND_HOST:-0.0.0.0}
FRONTEND_HOST=${TW_STOCK_FRONTEND_HOST:-0.0.0.0}
BACKEND_URL=http://127.0.0.1:$BACKEND_PORT
FRONTEND_URL=http://127.0.0.1:$FRONTEND_PORT
FRONTEND_HEALTH_URL=$FRONTEND_URL/api/health
NGROK_STATUS_URL=http://127.0.0.1:$NGROK_PORT/api/tunnels
WATCHDOG_LOCK=${TW_STOCK_WATCHDOG_LOCK:-$ROOT/logs/service_watchdog.lock}
exec 9>"$WATCHDOG_LOCK"
flock -n 9 || exit 0

for service_port in "$BACKEND_PORT" "$FRONTEND_PORT" "$NGROK_PORT"; do
  if ! [[ "$service_port" =~ ^[0-9]+$ ]] || [ "$service_port" -lt 1 ] || [ "$service_port" -gt 65535 ]; then
    echo "$(date -Is) invalid service port" >> "$LOG_DIR/service_watchdog.log"
    exit 1
  fi
done

cleanup_started_service() {
  local child_pid=$1
  local service_name=$2
  kill -TERM -- "-$child_pid" 2>/dev/null || kill -TERM "$child_pid" 2>/dev/null || true
  local attempts=5
  while kill -0 "$child_pid" 2>/dev/null && [ "$attempts" -gt 0 ]; do
    sleep 1
    attempts=$((attempts - 1))
  done
  if kill -0 "$child_pid" 2>/dev/null; then
    kill -KILL -- "-$child_pid" 2>/dev/null || kill -KILL "$child_pid" 2>/dev/null || true
  fi
  wait "$child_pid" 2>/dev/null || true
  echo "$(date -Is) $service_name startup probe failed; cleaned new process group" >> "$LOG_DIR/service_watchdog.log"
}

is_listening() {
  ss -ltn 2>/dev/null | awk "{print \$4}" | grep -Eq "(^|:)${1}$"
}

http_ok() {
  curl --fail --silent --show-error --max-time "${TW_STOCK_HEALTH_TIMEOUT:-5}" "$1" >/dev/null 2>&1
}

backend_live() {
  curl --fail --silent --show-error --max-time "${TW_STOCK_HEALTH_TIMEOUT:-5}" "$1/api/health" 2>/dev/null \
    | grep -Eq '"status"[[:space:]]*:[[:space:]]*"healthy"'
}

frontend_live() {
  curl --fail --silent --show-error --max-time "${TW_STOCK_HEALTH_TIMEOUT:-5}" "$FRONTEND_HEALTH_URL" 2>/dev/null \
    | grep -Eq '"status"[[:space:]]*:[[:space:]]*"healthy"'
}

wait_http() {
  url=$1
  attempts=${TW_STOCK_HEALTH_START_ATTEMPTS:-10}
  while [ "$attempts" -gt 0 ]; do
    http_ok "$url" && return 0
    attempts=$((attempts - 1))
    sleep 1
  done
  return 1
}

wait_backend() {
  attempts=${TW_STOCK_HEALTH_START_ATTEMPTS:-10}
  while [ "$attempts" -gt 0 ]; do
    backend_live "$BACKEND_URL" && return 0
    attempts=$((attempts - 1))
    sleep 1
  done
  return 1
}

wait_frontend() {
  attempts=${TW_STOCK_HEALTH_START_ATTEMPTS:-10}
  while [ "$attempts" -gt 0 ]; do
    frontend_live && return 0
    attempts=$((attempts - 1))
    sleep 1
  done
  return 1
}

start_backend() {
  if backend_live "$BACKEND_URL"; then
    return 0
  fi
  if is_listening "$BACKEND_PORT"; then
    echo "$(date -Is) backend:$BACKEND_PORT listener failed HTTP liveness; refusing duplicate start" >> "$LOG_DIR/service_watchdog.log"
    return 1
  fi
  cd "$ROOT" || exit 1
  setsid env \
    AGENT_LIVE_TRADING_ENABLED=false \
    ENABLE_PENDING_ORDER_WORKER=false \
    ENABLE_PORTFOLIO_MONITOR=false \
    ENABLE_TW_STOCK_MONITOR_WORKER=false \
    DISABLE_RESTORE_RUNNING_STRATEGIES=true \
    POSITION_SYNC_ENABLED=false \
    ENABLE_REFLECTION_WORKER=false \
    ENABLE_OFFLINE_AI_CALIBRATION=false \
    USDT_PAY_ENABLED=false \
    PYTHON_API_HOST="$BACKEND_HOST" \
    PYTHON_API_PORT="$BACKEND_PORT" \
    PYTHONPATH="$ROOT:$ROOT/backend${PYTHONPATH:+:$PYTHONPATH}" \
    GUNICORN_WORKERS=1 \
    GUNICORN_THREADS="${TW_STOCK_BACKEND_THREADS:-4}" \
    PYTHONUNBUFFERED=1 \
    "$PY" -m gunicorn --config "$ROOT/backend/gunicorn_config.py" \
    --chdir "$ROOT/backend" "run:app" >> "$LOG_DIR/backend_${BACKEND_PORT}.log" 2>&1 < /dev/null 9>&- &
  local child_pid=$!
  echo "$(date -Is) started backend:$BACKEND_PORT using Gunicorn" >> "$LOG_DIR/service_watchdog.log"
  if ! wait_backend; then
    cleanup_started_service "$child_pid" backend
    return 1
  fi
}

start_frontend() {
  if frontend_live; then
    return 0
  fi
  if is_listening "$FRONTEND_PORT"; then
    echo "$(date -Is) frontend:$FRONTEND_PORT listener failed HTTP probe; refusing duplicate start" >> "$LOG_DIR/service_watchdog.log"
    return 1
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
    FRONTEND_HOST="$FRONTEND_HOST" \
    FRONTEND_PORT="$FRONTEND_PORT" \
    FRONTEND_DIST="$ROOT/frontend/dist" \
    BACKEND_URL="$BACKEND_URL" \
    "$PY" "$ROOT/scripts/serve_frontend_static_proxy.py" >> "$LOG_DIR/frontend_${FRONTEND_PORT}.log" 2>&1 < /dev/null 9>&- &
  local child_pid=$!
  echo "$(date -Is) started frontend:$FRONTEND_PORT" >> "$LOG_DIR/service_watchdog.log"
  if ! wait_frontend; then
    cleanup_started_service "$child_pid" frontend
    return 1
  fi
}

start_ngrok() {
  if [ "${TW_STOCK_ENABLE_NGROK:-false}" != "true" ]; then
    return 0
  fi
  if http_ok "$NGROK_STATUS_URL"; then
    return 0
  fi
  if is_listening "$NGROK_PORT"; then
    echo "$(date -Is) ngrok:$NGROK_PORT listener failed HTTP probe; refusing duplicate start" >> "$LOG_DIR/service_watchdog.log"
    return 1
  fi
  cd "$ROOT" || exit 1
  setsid "$NGROK" http "$FRONTEND_URL" --web-addr "127.0.0.1:$NGROK_PORT" --log=stdout \
    >> "$LOG_DIR/ngrok_${FRONTEND_PORT}.log" 2>&1 < /dev/null 9>&- &
  local child_pid=$!
  echo "$(date -Is) started ngrok for frontend:$FRONTEND_PORT" >> "$LOG_DIR/service_watchdog.log"
  if ! wait_http "$NGROK_STATUS_URL"; then
    cleanup_started_service "$child_pid" ngrok
    return 1
  fi
}

status=0
start_backend || status=1
if backend_live "$BACKEND_URL" && ! http_ok "$BACKEND_URL/api/ready"; then
  echo "$(date -Is) backend liveness passed but readiness is degraded" >> "$LOG_DIR/service_watchdog.log"
  status=1
fi
start_frontend || status=1
start_ngrok || status=1
exit "$status"
