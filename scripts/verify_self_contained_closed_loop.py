#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DATA_ROOT = ROOT / "data_tw" / "self_contained_demo"
NORMALIZED_DIR = DATA_ROOT / "normalized"
SIGNAL_ROOT = ROOT / "data_tw" / "experiments" / "option_c_daily_signal"
ASOF = "2026-06-01"


def _write_demo_csv(symbol: str, idx: int) -> None:
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    start = date(2025, 10, 1)
    path = NORMALIZED_DIR / f"TW{symbol}.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["symbol", "date", "open", "high", "low", "close", "volume", "vwap", "factor"])
        writer.writeheader()
        base = 35.0 + idx * 0.7
        drift = 0.0007 + (idx % 17) * 0.00008
        for day_idx in range(180):
            current = start + timedelta(days=day_idx)
            if current.weekday() >= 5:
                continue
            seasonal = math.sin(day_idx / 9.0 + idx / 5.0) * 0.012
            close = base * (1 + drift) ** day_idx * (1 + seasonal)
            open_ = close * (1 - 0.004 + (idx % 5) * 0.001)
            high = max(open_, close) * 1.012
            low = min(open_, close) * 0.988
            volume = int(800_000 + idx * 7000 + day_idx * 250)
            writer.writerow({
                "symbol": f"TW{symbol}",
                "date": current.isoformat(),
                "open": f"{open_:.4f}",
                "high": f"{high:.4f}",
                "low": f"{low:.4f}",
                "close": f"{close:.4f}",
                "volume": volume,
                "vwap": f"{((open_ + high + low + close) / 4):.4f}",
                "factor": "1.0",
            })


def _prepare_fixture() -> None:
    for idx in range(150):
        symbol = f"{2001 + idx}"
        if idx == 0:
            symbol = "2330"
        elif idx == 1:
            symbol = "2317"
        elif idx == 2:
            symbol = "2454"
        _write_demo_csv(symbol, idx)


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print("[run]", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(cwd or ROOT), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return result


def main() -> int:
    _prepare_fixture()
    _run([
        sys.executable,
        str(ROOT / "qlib_pipeline" / "option_c" / "build_self_contained_option_c_signal.py"),
        "--normalized-dir",
        str(NORMALIZED_DIR),
        "--signal-root",
        str(SIGNAL_ROOT),
        "--asof",
        ASOF,
        "--run-id",
        "option_c_daily_signal_20260601_20260602T000000Z_self_contained_demo",
    ])

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    env["QLIB_TW_OPTION_C_ROOT"] = str(SIGNAL_ROOT)
    code = """
import json
from app.services.tw_stock_qlib_option_c import QlibOptionCSignalReader
reader = QlibOptionCSignalReader()
latest = reader.latest(bucket='all')
health = reader.health(now=__import__('datetime').datetime(2026, 6, 2, tzinfo=__import__('datetime').timezone.utc))
assert latest['ok'] is True
assert latest['top30_count'] == 30
assert latest['top50_count'] == 50
assert latest['trading']['orders_enabled'] is False
assert health['latest']['accepted_validated'] is True
print(json.dumps({
    'ok': True,
    'asof': latest['asof'],
    'target_date': latest['target_date'],
    'run_id': latest['run_id'],
    'top30_first': latest['top30'][0],
    'top30_count': latest['top30_count'],
    'top50_count': latest['top50_count'],
    'health_status': health['status'],
    'research_signal_not_order': latest['trading']['research_signal_not_order'],
}, ensure_ascii=False, indent=2))
"""
    _run([sys.executable, "-c", code], cwd=BACKEND, env=env)
    report = {
        "ok": True,
        "mode": "self_contained_demo",
        "normalized_dir": str(NORMALIZED_DIR),
        "signal_root": str(SIGNAL_ROOT),
        "latest_signal": str(SIGNAL_ROOT / "latest_signal.json"),
        "closed_loop": "fixture normalized CSV -> Option C style accepted artifact -> backend reader latest/top30/top50/health",
        "limitations": [
            "demo uses deterministic local fixture data, not live Yahoo/Scrapling network fetch",
            "demo ranking is momentum/liquidity style and is not a replacement for production qlib LightGBM training",
        ],
    }
    report_path = ROOT / "docs" / "SELF_CONTAINED_CLOSED_LOOP_REPORT_CN.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
