"""API tests for Phase5 LTR readonly explanation integration."""
from __future__ import annotations

from pathlib import Path


def test_ltr_readonly_explanation_get_returns_phase4b_product_view(client):
    resp = client.get("/api/tw-stock/ltr-readonly-explanation")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert data["ok"] is True
    assert data["schema_version"] == "phase5_product_readonly_view_v1"
    assert data["payload_source"] == "phase3c_readonly_explanation_payload"
    assert data["research_only"] is True
    assert data["readonly_disclaimer"] == "仅供只读研究复盘，不构成操作建议，不会产生任何真实执行动作。"
    assert len(data["methods"]) == 6
    assert data["no_write_guarantees"]["read_only_http_method"] is True
    assert data["no_write_guarantees"]["reads_static_payload_only"] is True

    method = data["methods"][0]
    assert set(method).issuperset({
        "method_key",
        "method_label",
        "research_role_label",
        "why_no_action",
        "tradeoff_summary",
        "readonly_disclaimer",
        "detail",
    })
    assert "source_trace" not in str(data)
    assert "summary_notes" not in str(data)
    assert method["why_no_action"].startswith("今天不动作的主要原因：")
    assert method["tradeoff_summary"].startswith("历史回放取舍：")
    detail = method["detail"]
    for key in ["net_return_summary", "drawdown_summary", "action_count_summary", "turnover_summary"]:
        assert detail[key]
    assert "必须和动作、换手、回撤取舍一起阅读" in detail["detail_disclaimer"]


def test_ltr_readonly_explanation_route_has_no_write_methods(client):
    for method in ["post", "put", "patch", "delete"]:
        resp = getattr(client, method)("/api/tw-stock/ltr-readonly-explanation")
        assert resp.status_code == 405


def test_ltr_readonly_explanation_api_does_not_call_mutating_services(client, monkeypatch):
    from app.routes import tw_stock as tw_stock_route

    def forbidden(*args, **kwargs):
        raise AssertionError("mutating service should not be called")

    monkeypatch.setattr(tw_stock_route.monitor_service, "scan_symbol", forbidden, raising=False)
    monkeypatch.setattr(tw_stock_route.option_c_ops_runner, "run", forbidden, raising=False)
    monkeypatch.setattr(tw_stock_route.option_c_normal_publish_gate, "run", forbidden, raising=False)
    monkeypatch.setattr(tw_stock_route.option_c_accepted_latest_scheduler, "tick", forbidden, raising=False)

    resp = client.get("/api/tw-stock/ltr-readonly-explanation")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["research_only"] is True


def test_ltr_readonly_explanation_route_source_is_get_only_and_readonly():
    source = Path("backend/app/routes/tw_stock.py").read_text(encoding="utf-8")
    assert '@tw_stock_bp.route("/ltr-readonly-explanation", methods=["GET"])' in source
    route_slice = source.split('@tw_stock_bp.route("/ltr-readonly-explanation"', 1)[1].split('@tw_stock_bp.route("/cross-analysis/symbol', 1)[0]
    forbidden = ["methods=[\"POST\"]", "scan_symbol", "normal_publish", "accepted_latest", "monitor/config", "portfolio_replay_service", "tw_stock_sim_account_service"]
    for item in forbidden:
        assert item not in route_slice



def test_ltr_optional_sim_strategies_get_returns_phaseb2_readonly_payload(client):
    resp = client.get("/api/tw-stock/ltr-optional-sim-strategies")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert data["ok"] is True
    assert data["schema_version"] == "phaseb2_ltr_simple_default_readonly_product_view_v1"
    assert data["payload_source"] == "phaseb1_conservative_replay_artifacts"
    assert data["default_method_key"] == "phase1c_ltr_simple_daily"
    assert data["boundary_text"] == "仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。"
    assert data["selection_policy"]["default_selected"] is True
    assert data["selection_policy"]["ltr_auto_enabled"] is False
    assert data["selection_policy"]["ltr_simple_default"] is True
    assert data["selection_policy"]["top50_adaptive_reference_only"] is True
    assert data["research_only"] is True
    assert data["no_write_guarantees"]["read_only_http_method"] is True
    assert data["no_write_guarantees"]["reads_static_artifacts_only"] is True
    assert data["no_write_guarantees"]["does_not_touch_monitor_or_execution_paths"] is True
    assert data["no_write_guarantees"]["does_not_touch_broker_or_orders"] is True

    strategies = data["strategies"]
    assert [item["method_key"] for item in strategies] == [
        "phase1c_ltr_simple_daily",
        "rank_rotate_top50_adaptive_score",
        "phase1c_ltr_conservative_top30_2day_confirm_daily",
        "phase1c_ltr_conservative_top20_entry_2day_exit_daily",
    ]
    assert [item["display_name"] for item in strategies] == [
        "LTR simple 默认主策略",
        "Top50 自适应规则参考",
        "LTR Top30 连续确认",
        "LTR Top20 严格入选",
    ]
    assert strategies[0]["role"] == "default_main_strategy"
    assert strategies[0]["is_default_main_strategy"] is True
    assert strategies[0]["status_label"] == "默认 / 独立测试较强 / 动作较多"
    assert strategies[1]["role"] == "rule_based_reference"
    for item in strategies[2:]:
        assert item["role"] == "conservative_reference"
        assert item["is_optional_ltr"] is True
    for item in strategies:
        assert item["metrics"]["period"] == "phase1c_independent_test_range"
        assert item["primary_evidence_period"] == "phase1c_independent_test_range"
        assert item["full_range_metrics"]["period"] == "common_full_range_shared_by_all_compared_methods"
        assert "混合历史复盘" in item["split_purity_note"]
        assert item["period_results"]
        assert item["walk_forward"]
        assert set(item["metrics"]).issuperset({
            "fee_tax_adjusted_net_return",
            "max_drawdown",
            "action_count",
            "turnover_proxy_by_notional_over_avg_equity",
        })
        assert item["rolling_summary"]["detail_layer_only"] is True


def test_ltr_optional_sim_strategies_route_has_no_write_methods(client):
    for method in ["post", "put", "patch", "delete"]:
        resp = getattr(client, method)("/api/tw-stock/ltr-optional-sim-strategies")
        assert resp.status_code == 405


def test_ltr_optional_sim_strategies_api_does_not_call_mutating_services(client, monkeypatch):
    from app.routes import tw_stock as tw_stock_route

    def forbidden(*args, **kwargs):
        raise AssertionError("mutating service should not be called")

    monkeypatch.setattr(tw_stock_route.monitor_service, "scan_symbol", forbidden, raising=False)
    monkeypatch.setattr(tw_stock_route.option_c_ops_runner, "run", forbidden, raising=False)
    monkeypatch.setattr(tw_stock_route.option_c_normal_publish_gate, "run", forbidden, raising=False)
    monkeypatch.setattr(tw_stock_route.option_c_accepted_latest_scheduler, "tick", forbidden, raising=False)

    resp = client.get("/api/tw-stock/ltr-optional-sim-strategies")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["research_only"] is True


def test_ltr_optional_sim_strategies_route_source_is_get_only_and_readonly():
    source = Path("backend/app/routes/tw_stock.py").read_text(encoding="utf-8")
    assert '@tw_stock_bp.route("/ltr-optional-sim-strategies", methods=["GET"])' in source
    route_slice = source.split('@tw_stock_bp.route("/ltr-optional-sim-strategies"', 1)[1].split('@tw_stock_bp.route("/cross-analysis/symbol', 1)[0]
    forbidden = [
        'methods=["POST"]',
        "scan_symbol",
        "normal_publish",
        "accepted_latest",
        "monitor/config",
        "portfolio_replay_service",
        "tw_stock_sim_account_service",
        "broker",
        "orders",
    ]
    for item in forbidden:
        assert item not in route_slice
