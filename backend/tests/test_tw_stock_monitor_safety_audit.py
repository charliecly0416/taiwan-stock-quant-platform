"""Safety boundary audit for TWStock monitor research paths."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MONITOR_FILES = [
    "app/routes/tw_stock.py",
    "app/services/tw_stock_monitor.py",
    "app/services/tw_stock_monitor_worker.py",
    "scripts/run_tw_stock_monitor_scan.py",
    "scripts/check_tw_stock_monitor_page_e2e.py",
    "scripts/build_tw_stock_universe.py",
    "scripts/import_tw_stock_monitor_config.py",
    "scripts/preflight_tw_stock_monitor_config.py",
    "scripts/report_tw_stock_monitor_health.py",
    "scripts/report_tw_stock_alert_review.py",
    "scripts/cleanup_tw_stock_monitor_history.py",
]

FORBIDDEN_PATTERNS = [
    "from app.routes.agent_v1 import quick_trade",
    "from app.routes import quick_trade",
    "import quick_trade",
    "from app.services.ibkr_trading",
    "import app.services.ibkr_trading",
    "from app.services.live_trading",
    "import app.services.live_trading",
    "TradingExecutor(",
    "submit_order(",
    "place_order(",
    "_record_paper_order(",
    "run_tw_stock_paper_pipeline",
    "submit_tw_stock_paper_orders",
    "preview_tw_stock_paper_orders",
    "verify_tw_stock_paper_orders",
]


def _source(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_tw_stock_monitor_paths_do_not_import_or_call_trading_layers():
    offenders = []
    for rel_path in MONITOR_FILES:
        src = _source(rel_path)
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in src:
                offenders.append(f"{rel_path}: {pattern}")

    assert offenders == []


def test_tw_stock_monitor_outputs_keep_orders_disabled_contract():
    required_files = [
        "app/routes/tw_stock.py",
        "app/services/tw_stock_monitor.py",
        "scripts/build_tw_stock_universe.py",
        "scripts/import_tw_stock_monitor_config.py",
        "scripts/preflight_tw_stock_monitor_config.py",
        "scripts/report_tw_stock_monitor_health.py",
        "scripts/report_tw_stock_alert_review.py",
        "scripts/cleanup_tw_stock_monitor_history.py",
        "scripts/run_tw_stock_monitor_scan.py",
    ]
    missing = []
    for rel_path in required_files:
        src = _source(rel_path)
        if "orders_enabled" not in src or "False" not in src:
            missing.append(rel_path)

    assert missing == []


def test_tw_stock_monitor_worker_imports_only_route_compatibility_wrapper():
    src = _source("app/services/tw_stock_monitor_worker.py")

    assert "from app.routes.tw_stock import run_tw_stock_monitor_scan_all" in src
    assert "quick_trade" not in src.lower()
    assert "ibkr" not in src.lower()
    assert "brokers" in src.lower()
