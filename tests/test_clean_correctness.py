"""Numerical counterexamples: a successful HTTP response is insufficient."""
from pathlib import Path

import pandas as pd
import pytest

from clean_product.models import ModelRunner, SignalResult
from clean_product.replay import replay
from clean_product.service import ProductService, _technical


@pytest.fixture
def config(tmp_path: Path):
    return {
        "data_root": tmp_path / "data", "artifact_root": tmp_path / "artifacts",
        "execution": "next_open", "strategy": "top50_exit_one_worst_sell",
        "simulation": {"initial_cash": 1000, "max_positions": 1,
                       "buy_cost_rate": 0, "sell_cost_rate": 0, "min_cost": 0},
        "model_stages": {"model_a_frozen": {}},
        "models": {"model_a": {"stages": ["model_a_frozen"]}},
    }


def prices():
    return pd.DataFrame([
        {"stock_id": "2330", "date": "2026-09-23", "open": 10., "close": 10.},
        {"stock_id": "2330", "date": "2026-09-24", "open": 10., "close": 9.},
    ])


@pytest.fixture
def provider_calendar(config):
    def install(days):
        provider = config["data_root"].parent / "provider"
        (provider / "calendars").mkdir(parents=True)
        (provider / "calendars/day.txt").write_text("\n".join(days) + "\n")
        config["model_stages"]["model_a_frozen"]["provider_uri"] = str(provider)
    return install


def test_first_execution_loss_counts_towards_drawdown(config):
    result = replay(config, {"prices": prices()}, "model_a", "2026-09-23", "2026-09-24", fixture=True)
    assert result["status"] == "READY"
    assert result["final_nav"] == 900
    assert result["cumulative_return"] == pytest.approx(-.1)
    assert result["max_drawdown"] == pytest.approx(-.1)
    assert result["nav"][0]["nav"] == 1000
    trade = result["trades"][0]
    assert (trade["signal_date"], trade["execute_date"], trade["price"], trade["quantity"]) == (
        "2026-09-23", "2026-09-24", 10, 100)


@pytest.mark.parametrize("field,value", [("open", 0), ("open", -1), ("open", float("nan")),
                                         ("close", float("nan")), ("close", 0)])
def test_invalid_execution_or_valuation_never_returns_ready(config, field, value):
    data = prices()
    data.loc[1, field] = value
    result = replay(config, {"prices": data}, "model_a", "2026-09-23", "2026-09-24", fixture=True)
    assert result["status"] == "BLOCKED"
    assert field in result["reason"]
    assert result["blocked_on"] == "2026-09-24"
    assert "final_nav" not in result


def test_holding_missing_close_is_not_valued_as_zero(config):
    data = pd.concat([prices(), pd.DataFrame([
        {"stock_id": "0050", "date": "2026-09-25", "open": 2., "close": 2.},
    ])], ignore_index=True)
    result = replay(config, {"prices": data}, "model_a", "2026-09-23", "2026-09-25", fixture=True)
    assert result["status"] == "BLOCKED"
    assert "close" in result["reason"] and "TW2330" in result["reason"]


def test_top50_changes_detect_boundary_swap(config, monkeypatch):
    service = ProductService(config)
    days = ["2026-09-23", "2026-09-24"]
    old = [f"TW{i:04d}" for i in range(1, 52)]
    new = old.copy()
    new[49], new[50] = new[50], new[49]

    def signal(model, asof):
        return SignalResult(model, asof, pd.DataFrame({
            "instrument": old if asof == days[0] else new,
            "rank": range(1, 52), "score": range(51, 0, -1), "date": asof,
        }))

    monkeypatch.setattr(service, "signal", signal)
    monkeypatch.setattr(service, "trading_days", lambda: days)
    result = service.ranking_changes("model_a", days[-1])
    assert result["entered"] == [{"instrument": "TW0051", "rank": 50}]
    assert result["exited"] == [{"instrument": "TW0050", "rank": 50}]
    assert len(result["stayed"]) == 49


@pytest.mark.parametrize("values,expected", [(range(1, 21), 100), (range(20, 0, -1), 0), ([10] * 20, 50)])
def test_rsi_zero_loss_and_flat_cases(values, expected):
    data = pd.DataFrame({"stock_id": "2330", "date": pd.date_range("2026-08-01", periods=20).astype(str), "close": values})
    assert _technical(data).iloc[-1].rsi14 == expected


def test_smoke_gate_rejects_http422_even_with_readonly_marker():
    from scripts.verify_clean_product import validate_response
    assert validate_response("/api/tw-stock/rankings", 422, {"readonly": True, "status": "BLOCKED"})


def test_smoke_gate_rejects_null_technical_values_even_when_ready():
    from scripts.verify_clean_product import validate_response
    errors = validate_response("/api/tw-stock/cross-analysis", 200, {
        "readonly": True, "status": "READY", "rows": [{"instrument": "TW2330", "rank": 1,
                                                       "close": None, "ma20": None, "rsi14": None}],
    })
    assert any("technical context" in error for error in errors)


def test_short_market_display_keeps_full_indicator_history(config, monkeypatch):
    service = ProductService(config)
    days = pd.bdate_range("2026-08-03", periods=40).strftime("%Y-%m-%d")
    data = pd.DataFrame({"stock_id": "2330", "date": days, "close": range(1, 41)})
    monkeypatch.setattr(service.catalog, "query_local_source",
                        lambda name, start, end: data[data.date.between(start, end)])
    short = service.market("2330", days[-2], days[-1])
    long = service.market("2330", days[0], days[-1])
    assert len(short["rows"]) == 2
    assert short["summary"]["ma20"] == 30.5
    assert short["summary"]["ma20"] == long["summary"]["ma20"]
    assert short["summary"]["ret20"] == 1


@pytest.mark.parametrize("rate,minimum,quantity,fee", [(0, 20, 98, 20), (.01, 20, 98, 20), (.01, 0, 99, 9.9)])
def test_minimum_commission_is_reserved_before_sizing_purchase(config, rate, minimum, quantity, fee):
    config["simulation"].update(buy_cost_rate=rate, min_cost=minimum)
    result = replay(config, {"prices": prices()}, "model_a", "2026-09-23", "2026-09-24", fixture=True)
    assert result["status"] == "READY"
    assert result["trade_count"] == 1
    assert result["trades"][0]["quantity"] == quantity
    assert result["total_fees"] == pytest.approx(fee)
    assert result["final_nav"] == pytest.approx(1000 - quantity - fee)
    assert result["account"]["cash"] == pytest.approx(1000 - quantity * 10 - fee)


@pytest.mark.parametrize("role,allowed", [("shadow", False), ("shadow", True), ("baseline", False)])
def test_paper_account_blocks_models_without_baseline_admission(config, role, allowed, monkeypatch):
    config["models"]["model_a_plus_b"] = {"role": role, "production_allowed": allowed,
                                            "stages": ["model_a_frozen"]}
    service = ProductService(config)
    monkeypatch.setattr(service, "latest_asof", lambda: pytest.fail("blocked model loaded market state"))
    result = service.paper_state("model_a_plus_b", "2026-09-24")
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "MODEL_NOT_ADMITTED_FOR_PAPER_ACCOUNT"
    assert result["readonly"] is True and result["simulation_only"] is True
    assert "nav" not in result and "positions" not in result


def test_baseline_paper_state_remains_explicitly_unpersisted(config):
    config["models"]["model_a"].update(role="baseline", production_allowed=True)
    result = ProductService(config).paper_state("model_a", "2026-09-24")
    assert result["status"] == "READY"
    assert result["persisted"] is False
    assert result["nav"] == 1000 and result["positions"] == []


@pytest.mark.parametrize("asof,lookback", [("2026-09-23", 1), ("2026-09-24", 2)])
def test_rank_changes_never_shortens_requested_history(config, monkeypatch, asof, lookback):
    service = ProductService(config)
    monkeypatch.setattr(service, "trading_days", lambda: ["2026-09-23", "2026-09-24"])
    monkeypatch.setattr(service, "signal", lambda *args: pytest.fail("insufficient history reached scoring"))
    result = service.ranking_changes("model_a", asof, lookback)
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "RANKING_HISTORY_INSUFFICIENT"
    assert result["lookback"] == lookback
    assert "stayed" not in result


@pytest.mark.parametrize("symbol", ["2330", "TW2330"])
def test_explanation_matches_full_stock_code(config, monkeypatch, symbol):
    service = ProductService(config)
    monkeypatch.setattr(service, "rankings", lambda *args: {
        "status": "READY", "asof": "2026-09-24", "label": "Model A",
        "rows": [{"instrument": "TW12330", "rank": 1, "score": .8},
                 {"instrument": "TW2330", "rank": 2, "score": .5}],
    })
    result = service.explain(symbol, asof="2026-09-24")
    assert result["evidence"][0]["rank"] == 2
    assert result["evidence"][0]["score"] == .5


@pytest.mark.parametrize("symbol", ["abc2330", "23-30", "2330.5", "", "1234567"])
def test_invalid_stock_codes_never_load_research_data(config, monkeypatch, symbol):
    service = ProductService(config)
    monkeypatch.setattr(service.catalog, "query_local_source",
                        lambda *args: pytest.fail("invalid stock reached data loading"))
    monkeypatch.setattr(service, "rankings", lambda *args: pytest.fail("invalid stock reached scoring"))
    with pytest.raises(ValueError, match="stock code"):
        service.explain(symbol, asof="2026-09-24")
    with pytest.raises(ValueError, match="stock code"):
        service.market(symbol, "2026-09-23", "2026-09-24")


@pytest.mark.parametrize("close", [float("nan"), float("inf"), 0, -1])
def test_market_invalid_latest_close_never_returns_ready(config, monkeypatch, close):
    service = ProductService(config)
    frame = prices()
    frame.loc[1, "close"] = close
    monkeypatch.setattr(service.catalog, "query_local_source", lambda *args: frame)
    result = service.market("2330", "2026-09-23", "2026-09-24")
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "MARKET_LATEST_CLOSE_INVALID"
    assert result["summary"] == {}


def test_replay_does_not_skip_missing_provider_trading_day(config, monkeypatch, provider_calendar):
    provider_calendar(["2026-09-23", "2026-09-24", "2026-09-25"])
    service = ProductService(config)
    frame = prices()
    frame.loc[1, "date"] = "2026-09-25"
    monkeypatch.setattr(service, "_model_data", lambda *args: {"prices": frame})
    monkeypatch.setattr(ModelRunner, "precompute", lambda *args, **kwargs: pytest.fail("incomplete prices reached scoring"))
    result = service.run_replay("model_a", "2026-09-23", "2026-09-25")
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "REPLAY_PRICE_DATES_MISSING"
    assert result["missing_dates"] == ["2026-09-24"]
    assert "final_nav" not in result


def test_replay_accepts_nontrading_gaps_in_provider_calendar(config, monkeypatch, provider_calendar):
    provider_calendar(["2026-09-23", "2026-09-25"])
    service = ProductService(config)
    frame = prices()
    frame.loc[1, "date"] = "2026-09-25"
    monkeypatch.setattr(service, "_model_data", lambda *args: {"prices": frame})
    monkeypatch.setattr(ModelRunner, "precompute", lambda *args, **kwargs: None)
    monkeypatch.setattr(ModelRunner, "run", lambda self, model, asof, **kwargs: SignalResult(
        model, asof, pd.DataFrame([{"date": asof, "instrument": "TW2330", "rank": 1, "score": .5}])))
    result = service.run_replay("model_a", "2026-09-23", "2026-09-25")
    assert result["status"] == "READY"
    assert result["trades"][0]["execute_date"] == "2026-09-25"


def test_replay_never_trades_on_dates_outside_provider_calendar(config, monkeypatch, provider_calendar):
    provider_calendar(["2026-09-23", "2026-09-25"])
    service = ProductService(config)
    monkeypatch.setattr(service, "_model_data", lambda *args: {"prices": prices()})
    monkeypatch.setattr(ModelRunner, "precompute", lambda *args, **kwargs: pytest.fail("invalid dates reached scoring"))
    result = service.run_replay("model_a", "2026-09-23", "2026-09-24")
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "REPLAY_PRICE_DATES_OUTSIDE_CALENDAR"
    assert result["unexpected_dates"] == ["2026-09-24"]


def test_replay_missing_calendar_blocks_before_scoring(config, monkeypatch):
    service = ProductService(config)
    monkeypatch.setattr(service, "_model_data", lambda *args: {"prices": prices()})
    monkeypatch.setattr(ModelRunner, "precompute", lambda *args, **kwargs: pytest.fail("missing calendar reached scoring"))
    result = service.run_replay("model_a", "2026-09-23", "2026-09-24")
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "PROVIDER_CALENDAR_UNAVAILABLE"
