"""Static checks for repository PR template safety checklist."""
from __future__ import annotations

from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2] / ".github" / "PULL_REQUEST_TEMPLATE.md"


def test_pr_template_mentions_twstock_research_verifier_and_safety_boundary():
    text = TEMPLATE.read_text(encoding="utf-8")

    assert "TWStock Research Safety" in text
    assert "verify_tw_stock_research_stack.py" in text
    assert "AGENT_LIVE_TRADING_ENABLED" in text
    assert "broker" in text.lower()
    assert "IBKR" in text
    assert "quick-trade" in text
    assert "paper/live order" in text
    assert "dry-run/preflight" in text
