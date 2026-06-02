#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
QLIB_PIPELINE = ROOT / "qlib_pipeline"
SIGNAL_ROOT = QLIB_PIPELINE / "data_tw/experiments/option_c_daily_signal"
PROVIDER_CALENDAR = QLIB_PIPELINE / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
NORMALIZED_150 = QLIB_PIPELINE / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
RECORDER = QLIB_PIPELINE / "mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a"


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None, required: bool = True) -> dict:
    print("[run]", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(cwd), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    payload = {"cmd": cmd, "cwd": str(cwd), "returncode": result.returncode, "ok": result.returncode == 0}
    if required and result.returncode != 0:
        raise SystemExit(result.returncode)
    return payload


def _latest_date() -> str | None:
    if not PROVIDER_CALENDAR.exists():
        return None
    rows = [line.strip() for line in PROVIDER_CALENDAR.read_text(encoding="utf-8").splitlines() if line.strip()]
    return max(rows) if rows else None


def _count_csv() -> int:
    return len(list(NORMALIZED_150.glob("TW*.csv")))


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{BACKEND}:{QLIB_PIPELINE}:{env.get('PYTHONPATH', '')}"
    env["QLIB_TW_OPTION_C_ROOT"] = str(SIGNAL_ROOT)
    env["TW_QLIB_OPTION_C_CWD"] = str(QLIB_PIPELINE)
    env["TW_QLIB_OPTION_C_PROVIDER_CALENDAR"] = str(PROVIDER_CALENDAR)

    preflight = {
        "signal_root_exists": SIGNAL_ROOT.exists(),
        "latest_signal_exists": (SIGNAL_ROOT / "latest_signal.json").exists(),
        "provider_calendar_exists": PROVIDER_CALENDAR.exists(),
        "provider_calendar_latest": _latest_date(),
        "option_c_150_normalized_count": _count_csv(),
        "recorder_exists": RECORDER.exists(),
        "params_pkl_exists": (RECORDER / "artifacts/params.pkl").exists(),
        "pred_pkl_exists": (RECORDER / "artifacts/pred.pkl").exists(),
    }
    missing = [key for key, value in preflight.items() if value in {False, 0, None}]
    if missing:
        print(json.dumps({"ok": False, "stage": "preflight", "missing": missing, "preflight": preflight}, ensure_ascii=False, indent=2))
        return 1

    reader_code = """
import json
from datetime import datetime, timezone
from app.services.tw_stock_qlib_option_c import QlibOptionCSignalReader
reader = QlibOptionCSignalReader()
latest = reader.latest(bucket='all')
health = reader.health(now=datetime(2026, 6, 2, tzinfo=timezone.utc))
assert latest['ok'] is True
assert latest['status'] == 'accepted'
assert latest['top30_count'] == 30
assert latest['top50_count'] == 50
assert health['latest']['accepted_validated'] is True
print(json.dumps({
  'ok': True,
  'asof': latest['asof'],
  'target_date': latest.get('target_date'),
  'run_id': latest['run_id'],
  'top30_first': latest['top30'][0],
  'health_status': health['status'],
  'research_signal_not_order': latest['trading']['research_signal_not_order'],
}, ensure_ascii=False, indent=2))
"""
    checks = [_run([sys.executable, "-c", reader_code], cwd=BACKEND, env=env)]

    asof = preflight["provider_calendar_latest"]
    qlib_dry_run = _run([
        sys.executable,
        "examples/tw/run_option_c_daily_signal_option_c_provider.py",
        "--asof",
        str(asof),
        "--dry-run",
    ], cwd=QLIB_PIPELINE, env=env, required=False)
    checks.append(qlib_dry_run)

    payload = {
        "ok": all(item["ok"] for item in checks[:1]),
        "mode": "full_production_assets_local",
        "preflight": preflight,
        "checks": checks,
        "notes": [
            "backend accepted latest reader passed against repo-local copied production artifacts",
            "qlib dry-run check is reported separately because it depends on local qlib runtime dependencies",
            "data/model assets are ignored by git and should be shipped as release artifacts or regenerated",
        ],
    }
    report = ROOT / "docs" / "FULL_PRODUCTION_LOOP_VALIDATION_CN.json"
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
