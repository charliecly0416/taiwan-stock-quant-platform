#!/usr/bin/env bash
set -u
ROOT=${TW_STOCK_PLATFORM_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
INTERVAL=${TW_STOCK_SERVICE_WATCH_INTERVAL:-60}
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
echo "$(date -Is) watch_tw_stock_services started interval=${INTERVAL}" >> "$LOG_DIR/service_watchdog_loop.log"
while true; do
  "$ROOT/scripts/ensure_tw_stock_services.sh" >> "$LOG_DIR/service_watchdog_loop.log" 2>&1 || true
  sleep "$INTERVAL"
done
