#!/usr/bin/env bash
set -euo pipefail

ROOT=${TW_STOCK_PLATFORM_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
ENV_FILE=${TW_STOCK_CRON_ENV_FILE:-$ROOT/backend/.env}

if [ ! -f "$ENV_FILE" ] || [ -L "$ENV_FILE" ]; then
  echo "cron environment file is missing or is a symlink" >&2
  exit 1
fi
if find "$ENV_FILE" -maxdepth 0 -perm /077 -print -quit | grep -q .; then
  echo "cron environment file must not be accessible by group or others" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is missing from cron environment file" >&2
  exit 1
fi

exec "$@"
