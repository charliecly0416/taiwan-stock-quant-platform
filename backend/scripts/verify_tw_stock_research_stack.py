#!/usr/bin/env python3
"""Run the TWStock research-stack verification suite.

This is an offline-first acceptance runner. By default it runs the pytest
coverage for the read-only TWStock monitor/research path. Use --with-page-smoke
to also run the Playwright screenshot smoke. It never writes production data,
submits orders, or connects to broker clients.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "tw-stock-research-verify")
os.environ.setdefault("ADMIN_USER", "verify")
os.environ.setdefault("ADMIN_PASSWORD", "verifypass")
os.environ.setdefault("AGENT_LIVE_TRADING_ENABLED", "false")
os.environ.setdefault("ENABLE_PENDING_ORDER_WORKER", "false")
os.environ.setdefault("ENABLE_PORTFOLIO_MONITOR", "false")
os.environ.setdefault("ENABLE_TW_STOCK_MONITOR_WORKER", "false")

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

DEFAULT_TESTS = [
    "tests/test_tw_stock_monitor_safety_audit.py",
    "tests/test_pr_template_safety_checklist.py",
    "tests/test_tw_stock_monitor_page_e2e_script.py",
    "tests/test_tw_stock_trend_api.py",
    "tests/test_tw_stock_monitor_worker.py",
    "tests/test_run_tw_stock_monitor_scan.py",
    "tests/test_tw_stock_monitor_service.py",
    "tests/test_cleanup_tw_stock_monitor_history.py",
    "tests/test_build_tw_stock_universe.py",
    "tests/test_import_tw_stock_monitor_config.py",
    "tests/test_preflight_tw_stock_monitor_config.py",
    "tests/test_build_tw_stock_data_quality_report.py",
    "tests/test_report_tw_stock_monitor_health.py",
    "tests/test_report_tw_stock_alert_review.py",
    "tests/test_tw_stock_frontend_contract_docs.py",
    "tests/test_tw_stock_backtest_plan_docs.py",
    "tests/test_tw_stock_backtest.py",
]



def _backend_env() -> Dict[str, str]:
    env = dict(os.environ)
    backend_path = str(BACKEND_ROOT)
    env["PYTHONPATH"] = backend_path if not env.get("PYTHONPATH") else f"{backend_path}:{env['PYTHONPATH']}"
    return env

def _run_command(cmd: Sequence[str], *, env: Dict[str, str] | None = None) -> Dict[str, Any]:
    started = time.monotonic()
    proc = subprocess.run(list(cmd), text=True, capture_output=True, env=env)
    return {
        "cmd": list(cmd),
        "returncode": proc.returncode,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def run_verification(*, with_page_smoke: bool = False, screenshot: str = "/tmp/tw_stock_monitor_phase7a.png", tests: Sequence[str] | None = None) -> Dict[str, Any]:
    selected_tests = list(tests or DEFAULT_TESTS)
    steps: List[Dict[str, Any]] = []
    normalized_tests = [str((BACKEND_ROOT / item).resolve()) if not str(item).startswith("/") else str(item) for item in selected_tests]
    pytest_cmd = [sys.executable, "-m", "pytest", *normalized_tests, "-q"]
    steps.append({"name": "pytest", **_run_command(pytest_cmd, env=_backend_env())})

    if with_page_smoke:
        env = _backend_env()
        page_cmd = [
            sys.executable,
            str(BACKEND_ROOT / "scripts/check_tw_stock_monitor_page_e2e.py"),
            "--screenshot",
            screenshot,
        ]
        steps.append({"name": "page_smoke", **_run_command(page_cmd, env=env)})

    ok = all(step["returncode"] == 0 for step in steps)
    return {
        "ok": ok,
        "with_page_smoke": bool(with_page_smoke),
        "test_count": len(selected_tests),
        "steps": steps,
        "orders_enabled": False,
        "writes_production_data": False,
        "connects_to_broker": False,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run TWStock research-stack verification.")
    parser.add_argument("--with-page-smoke", action="store_true", help="Also run Playwright screenshot smoke.")
    parser.add_argument("--screenshot", default="/tmp/tw_stock_monitor_phase7a.png")
    parser.add_argument("--test", action="append", default=[], help="Override pytest paths. Can be repeated.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    report = run_verification(
        with_page_smoke=bool(args.with_page_smoke),
        screenshot=args.screenshot,
        tests=args.test or None,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
