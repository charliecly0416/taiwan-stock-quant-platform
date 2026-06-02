"""Static checks for TWStock frontend API contract docs."""
from __future__ import annotations

from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs" / "TW_STOCK_FRONTEND_PHASE12A_API_CONTRACT_CN.md"
HANDOFF = Path(__file__).resolve().parents[2] / "docs" / "TAIWAN_STOCK_HANDOFF_PHASE1_8_CN.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_frontend_contract_lists_required_twstock_apis():
    text = _text()

    required = [
        "/api/tw-stock/trend",
        "/api/tw-stock/trends",
        "/api/tw-stock/monitor/config",
        "/api/tw-stock/monitor/alerts",
        "/api/tw-stock/monitor/history",
        "/api/tw-stock/monitor/scan-all",
        "/api/tw-stock/monitor/scan-logs",
    ]
    for endpoint in required:
        assert endpoint in text


def test_frontend_contract_keeps_research_only_safety_fields():
    text = _text().lower()

    assert "orders_enabled=false" in text
    assert "writes_production_data=false" in text
    assert "connects_to_broker=false" in text
    assert "不调用 quick-trade" in text
    assert "不展示自动买入" in text
    assert "不根据趋势标签自动生成订单" in text


def test_frontend_contract_requires_independent_frontend_workflow():
    text = _text().lower()

    assert "quantdinger-vue" in text
    assert "独立 frontend/e2e workflow" in text
    assert "tw-stock-research.yml" in text
    assert "不安装 node/npm" in text
    assert "不构建前端" in text


def test_handoff_records_phase12_frontend_boundary():
    text = HANDOFF.read_text(encoding="utf-8").lower()

    assert "phase 10-12" in text
    assert "quantdinger-vue" in text
    assert "tw-stock-monitor-frontend.yml" in text
    assert "tw_stock_phase12f_acceptance_cn.md" in text
    assert "不安装 node/npm/pnpm" in text
    assert "不构建 vue 前端" in text
    assert "不连接 broker" in text
    assert "不启用 live" in text
