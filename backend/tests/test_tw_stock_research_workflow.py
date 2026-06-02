"""Static checks for TWStock research GitHub Actions workflow."""
from __future__ import annotations

from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "tw-stock-research.yml"


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_tw_stock_research_workflow_runs_one_click_verifier():
    text = _text()

    assert "python backend/scripts/verify_tw_stock_research_stack.py" in text
    command_line = "python backend/scripts/verify_tw_stock_research_stack.py"
    assert "--with-page-smoke" not in command_line
    assert "workflow_dispatch" in text


def test_tw_stock_research_workflow_keeps_live_and_workers_disabled():
    text = _text()

    assert "AGENT_LIVE_TRADING_ENABLED: 'false'" in text
    assert "ENABLE_PENDING_ORDER_WORKER: 'false'" in text
    assert "ENABLE_PORTFOLIO_MONITOR: 'false'" in text
    assert "ENABLE_TW_STOCK_MONITOR_WORKER: 'false'" in text


def test_tw_stock_research_workflow_does_not_install_browsers_or_start_services():
    text = _text().lower()

    assert "playwright install" not in text
    assert "docker compose up" not in text
    assert "uvicorn" not in text
    assert "gunicorn" not in text


def test_tw_stock_research_workflow_triggers_on_safety_checklist_files():
    text = _text()

    assert ".github/PULL_REQUEST_TEMPLATE.md" in text
    assert "backend/tests/test_pr_template_safety_checklist.py" in text
    assert "backend/tests/test_tw_stock_research_workflow.py" in text


def test_tw_stock_research_workflow_keeps_frontend_e2e_out_of_offline_ci():
    text = _text().lower()

    forbidden = [
        "actions/setup-node",
        "npm ",
        "pnpm ",
        "yarn ",
        "playwright install",
        "--with-page-smoke",
        "quantdinger-vue",
        "frontend",
    ]
    for pattern in forbidden:
        assert pattern not in text
