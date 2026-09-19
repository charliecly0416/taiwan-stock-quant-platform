#!/usr/bin/env bash
set -euo pipefail

ROOT=${TW_STOCK_PLATFORM_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
ENV_FILE=${TW_SECRET_ENV_FILE:-$ROOT/backend/.env}
PY=${TW_STOCK_PYTHON:-}

if [ -z "$PY" ]; then
  PY=$(command -v python3 || command -v python || true)
fi
if [ -z "$PY" ]; then
  echo "Python 3 is required to generate SECRET_KEY" >&2
  exit 1
fi

export TW_SECRET_ENV_FILE="$ENV_FILE"
"$PY" - <<'PY'
import os
import secrets
import stat
from pathlib import Path

path = Path(os.environ["TW_SECRET_ENV_FILE"])
if not path.is_file() or path.is_symlink():
    raise SystemExit(f"environment file is missing or unsafe: {path}")

secret_line = f"SECRET_KEY={secrets.token_hex(32)}\n"
output = []
found = False
for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
    if line.startswith("SECRET_KEY="):
        if not found:
            output.append(secret_line)
            found = True
        continue
    output.append(line)
if not found:
    if output and not output[-1].endswith(("\n", "\r")):
        output[-1] += "\n"
    output.append(secret_line)

mode = stat.S_IMODE(path.stat().st_mode)
temporary = path.with_name(f".{path.name}.secret-key.{os.getpid()}")
try:
    temporary.write_text("".join(output), encoding="utf-8")
    temporary.chmod(mode)
    temporary.replace(path)
finally:
    temporary.unlink(missing_ok=True)

print(f"Updated SECRET_KEY in {path}")
PY
