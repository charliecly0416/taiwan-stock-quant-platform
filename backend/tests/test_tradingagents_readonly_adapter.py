from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RUN_SCRIPT = ROOT / "scripts" / "run_tradingagents_readonly_analysis.py"
FIXTURE = ROOT / "data_tw/golden_samples/tradingagents_readonly_analysis/pass_minimal/mock_raw_state.json"
FIXTURE_DIR = FIXTURE.parent


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


from backend.app.services.tradingagents_readonly_adapter import (  # noqa: E402
    ENABLE_REAL_RUN_ENV,
    LOCAL_MARKET_DATA_VENDOR,
    REAL_RUN_CONFIRM_ENV,
    REAL_RUN_CONFIRM_VALUE,
    build_real_run_config,
    real_run_enabled,
    run_tradingagents_readonly_analysis,
)
from backend.app.services import tradingagents_quantdinger_data_provider as provider  # noqa: E402
from backend.app.services.tradingagents_quantdinger_data_provider import (  # noqa: E402
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_global_news,
    get_income_statement,
    get_insider_transactions,
    get_macro_indicators,
    get_news,
    get_prediction_markets,
    get_stock_data,
    install_tradingagents_local_data_provider,
    load_local_ohlcv,
    resolve_local_instrument_identity,
)


def test_dry_run_adapter_builds_valid_artifact_from_fixture_file(tmp_path: Path, monkeypatch):
    monkeypatch.delenv(ENABLE_REAL_RUN_ENV, raising=False)
    out_dir = tmp_path / "artifact"

    result = run_tradingagents_readonly_analysis(
        fixture=FIXTURE,
        output_dir=out_dir,
        dry_run=True,
        run_id="adapter_pytest",
    )

    assert result["ok"] is True, result
    assert result["mode"] == "dry_run"
    assert result["real_run_enabled"] is False
    assert result["validation"]["ok"] is True
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == "adapter_pytest"
    assert manifest["no_openai_call"] is True
    assert manifest["no_network_call"] is True
    assert manifest["no_tradingagents_graph_call"] is True
    assert manifest["no_accepted_latest_switch"] is True


def test_dry_run_adapter_accepts_fixture_directory(tmp_path: Path):
    out_dir = tmp_path / "artifact_from_dir"

    result = run_tradingagents_readonly_analysis(
        fixture=FIXTURE_DIR,
        output_dir=out_dir,
        dry_run=True,
    )

    assert result["ok"] is True, result
    assert result["fixture"].endswith("mock_raw_state.json")
    assert (out_dir / "sanitized_report.json").exists()


def test_enable_real_run_env_does_not_override_explicit_dry_run(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(ENABLE_REAL_RUN_ENV, "true")
    out_dir = tmp_path / "dry_even_when_env_enabled"

    result = run_tradingagents_readonly_analysis(
        fixture=FIXTURE,
        output_dir=out_dir,
        dry_run=True,
        run_id="dry_env_true",
    )

    assert real_run_enabled() is True
    assert result["ok"] is True, result
    assert result["mode"] == "dry_run"
    assert result["safety"]["no_tradingagents_graph_call"] is True
    assert (out_dir / "manifest.json").exists()


def test_real_run_request_is_blocked_when_env_disabled(tmp_path: Path, monkeypatch):
    monkeypatch.delenv(ENABLE_REAL_RUN_ENV, raising=False)
    out_dir = tmp_path / "blocked"

    result = run_tradingagents_readonly_analysis(
        fixture=FIXTURE,
        output_dir=out_dir,
        dry_run=False,
        symbol="2330.TW",
        trade_date="2026-06-30",
    )

    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert result["reason"] == "real_run_disabled"
    assert result["mode"] == "disabled_real_request"
    assert result["safety"]["no_tradingagents_graph_call"] is True
    assert not out_dir.exists()


def test_real_run_request_requires_confirmation_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(ENABLE_REAL_RUN_ENV, "true")
    monkeypatch.delenv(REAL_RUN_CONFIRM_ENV, raising=False)
    out_dir = tmp_path / "blocked"

    result = run_tradingagents_readonly_analysis(
        fixture=FIXTURE,
        output_dir=out_dir,
        dry_run=False,
        symbol="2330.TW",
        trade_date="2026-06-30",
    )

    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert result["reason"] == "real_run_confirmation_missing"
    assert result["mode"] == "real_requested"
    assert not out_dir.exists()


def test_controlled_real_run_config_routes_market_data_to_local_provider():
    config = build_real_run_config(run_id="pytest_local_provider_config")

    assert config["tool_vendors"]["get_stock_data"] == LOCAL_MARKET_DATA_VENDOR
    assert config["tool_vendors"]["get_indicators"] == LOCAL_MARKET_DATA_VENDOR
    assert config["tool_vendors"]["get_news"] == LOCAL_MARKET_DATA_VENDOR
    assert config["tool_vendors"]["get_global_news"] == LOCAL_MARKET_DATA_VENDOR
    assert config["tool_vendors"]["get_insider_transactions"] == LOCAL_MARKET_DATA_VENDOR
    assert config["tool_vendors"]["get_fundamentals"] == LOCAL_MARKET_DATA_VENDOR
    assert config["tool_vendors"]["get_balance_sheet"] == LOCAL_MARKET_DATA_VENDOR
    assert config["tool_vendors"]["get_cashflow"] == LOCAL_MARKET_DATA_VENDOR
    assert config["tool_vendors"]["get_income_statement"] == LOCAL_MARKET_DATA_VENDOR
    assert config["tool_vendors"]["get_macro_indicators"] == LOCAL_MARKET_DATA_VENDOR
    assert config["tool_vendors"]["get_prediction_markets"] == LOCAL_MARKET_DATA_VENDOR
    assert config["data_vendors"]["core_stock_apis"] == LOCAL_MARKET_DATA_VENDOR
    assert config["data_vendors"]["technical_indicators"] == LOCAL_MARKET_DATA_VENDOR
    assert config["data_vendors"]["news_data"] == LOCAL_MARKET_DATA_VENDOR
    assert config["data_vendors"]["fundamental_data"] == LOCAL_MARKET_DATA_VENDOR
    assert config["data_vendors"]["macro_data"] == LOCAL_MARKET_DATA_VENDOR
    assert config["data_vendors"]["prediction_markets"] == LOCAL_MARKET_DATA_VENDOR
    assert config["backend_url"] == "https://chat.pku.edu.cn/v1"


def test_quantdinger_unapproved_source_hooks_fail_closed():
    outputs = [
        get_news("2330.TW", "2026-06-01", "2026-06-03"),
        get_global_news("2026-06-03", look_back_days=7, limit=3),
        get_insider_transactions("2330.TW"),
        get_fundamentals("2330.TW", "2026-06-03"),
        get_balance_sheet("2330.TW", "quarterly", "2026-06-03"),
        get_cashflow("2330.TW", "quarterly", "2026-06-03"),
        get_income_statement("2330.TW", "quarterly", "2026-06-03"),
        get_macro_indicators("fed_funds_rate", "2026-06-03", look_back_days=30),
        get_prediction_markets("Fed rate cut", limit=2),
    ]

    for output in outputs:
        assert "NO_GROUNDED_LOCAL_SOURCE_AVAILABLE" in output
        assert "fail-closed source-grounding sentinel" in output
        assert "Do not infer, fabricate" in output


def test_quantdinger_news_uses_approved_source_packet_store_for_2454():
    output = get_news("2454.TW", "2026-06-01", "2026-06-10")

    assert "Approved company/exchange/news source packets" in output
    assert "tadr8-packet-2454-2026-06-03-mediatek-ai-aqm" in output
    assert "MediaTek AI-Powered AQM" in output
    assert "Approved excerpt:" in output
    assert "NO_GROUNDED_LOCAL_SOURCE_AVAILABLE" not in output
    assert "Do not treat this as trading advice" in output


def test_quantdinger_news_packet_store_respects_symbol_and_date_window():
    wrong_symbol = get_news("2330.TW", "2026-06-01", "2026-06-10")
    wrong_window = get_news("2454.TW", "2026-06-04", "2026-06-10")
    fundamentals_without_filing = get_fundamentals("2454.TW", "2026-06-10")

    assert "NO_GROUNDED_LOCAL_SOURCE_AVAILABLE" in wrong_symbol
    assert "NO_GROUNDED_LOCAL_SOURCE_AVAILABLE" in wrong_window
    assert "NO_GROUNDED_LOCAL_SOURCE_AVAILABLE" in fundamentals_without_filing


def test_quantdinger_instrument_identity_maps_2454_to_mediatek():
    identity = resolve_local_instrument_identity("2454.TW")

    assert identity["company_name"] == "聯發科 / MediaTek Inc."
    assert identity["sector"] == "Technology"
    assert identity["industry"] == "Semiconductors"
    assert "旺宏" not in identity["company_name"]


def test_quantdinger_local_provider_reads_yahoo_scrapling_normalized_csv():
    output = get_stock_data("2330.TW", "2026-05-20", "2026-06-01")

    assert "Data source: QuantDinger local Yahoo/Scrapling normalized artifact" in output
    assert "Date,Open,High,Low,Close,Adj Close,Volume" in output
    assert "2026-06-01" in output
    assert "yfinance" not in output.lower()


def test_quantdinger_provider_uses_scrapling_yahoo_chart_when_local_data_is_stale(tmp_path: Path, monkeypatch):
    class FakePage:
        status = 200

        @staticmethod
        def json():
            return {
                "chart": {
                    "result": [{
                        "timestamp": [1782691200, 1782777600],
                        "indicators": {
                            "quote": [{
                                "open": [2300.0, 2310.0],
                                "high": [2320.0, 2330.0],
                                "low": [2290.0, 2300.0],
                                "close": [2315.0, 2325.0],
                                "volume": [1000, 1200],
                            }],
                            "adjclose": [{"adjclose": [2315.0, 2325.0]}],
                        },
                    }],
                    "error": None,
                },
            }

    class FakeFetcher:
        calls = []

        @classmethod
        def get(cls, url, **kwargs):
            cls.calls.append({"url": url, "kwargs": kwargs})
            return FakePage()

    monkeypatch.setattr(provider, "SCRAPLING_CACHE_DIR", tmp_path)
    monkeypatch.setattr(provider, "_import_scrapling_fetcher", lambda: FakeFetcher)

    output = get_stock_data("2330.TW", "2026-06-01", "2026-06-30")

    assert FakeFetcher.calls
    assert "query1.finance.yahoo.com/v8/finance/chart/2330.TW" in FakeFetcher.calls[0]["url"]
    assert "Data source: Yahoo chart via Scrapling runtime cache" in output
    assert "2026-06-30" in output
    assert "yfinance" not in output.lower()


def test_quantdinger_provider_installs_tradingagents_hooks(monkeypatch):
    if importlib.util.find_spec("stockstats") is None:
        import pytest

        pytest.skip("stockstats is available in the TradingAgents conda env, not the base test env")
    vendor_root = ROOT / "third_party/tradingagents"
    if str(vendor_root) not in sys.path:
        sys.path.insert(0, str(vendor_root))

    result = install_tradingagents_local_data_provider()

    import tradingagents.dataflows.interface as interface  # type: ignore
    import tradingagents.dataflows.market_data_validator as market_data_validator  # type: ignore
    import tradingagents.dataflows.stockstats_utils as stockstats_utils  # type: ignore
    import tradingagents.graph.trading_graph as trading_graph  # type: ignore

    assert result["vendor"] == LOCAL_MARKET_DATA_VENDOR
    assert interface.VENDOR_METHODS["get_stock_data"][LOCAL_MARKET_DATA_VENDOR] is get_stock_data
    assert interface.VENDOR_METHODS["get_indicators"][LOCAL_MARKET_DATA_VENDOR]
    assert interface.VENDOR_METHODS["get_news"][LOCAL_MARKET_DATA_VENDOR] is get_news
    assert interface.VENDOR_METHODS["get_global_news"][LOCAL_MARKET_DATA_VENDOR] is get_global_news
    assert interface.VENDOR_METHODS["get_insider_transactions"][LOCAL_MARKET_DATA_VENDOR] is get_insider_transactions
    assert interface.VENDOR_METHODS["get_macro_indicators"][LOCAL_MARKET_DATA_VENDOR] is get_macro_indicators
    assert interface.VENDOR_METHODS["get_prediction_markets"][LOCAL_MARKET_DATA_VENDOR] is get_prediction_markets
    assert interface.VENDOR_METHODS["get_fundamentals"][LOCAL_MARKET_DATA_VENDOR] is get_fundamentals
    assert interface.VENDOR_METHODS["get_balance_sheet"][LOCAL_MARKET_DATA_VENDOR] is get_balance_sheet
    assert interface.VENDOR_METHODS["get_cashflow"][LOCAL_MARKET_DATA_VENDOR] is get_cashflow
    assert interface.VENDOR_METHODS["get_income_statement"][LOCAL_MARKET_DATA_VENDOR] is get_income_statement
    assert stockstats_utils.load_ohlcv is load_local_ohlcv
    assert market_data_validator.load_ohlcv is load_local_ohlcv
    assert trading_graph.get_verified_market_snapshot is provider.get_verified_market_snapshot


def test_quantdinger_local_fetch_returns_skips_when_benchmark_unavailable(monkeypatch):
    prices = pd.DataFrame({
        "Date": ["2026-06-03", "2026-06-04", "2026-06-05"],
        "Open": [100.0, 101.0, 102.0],
        "High": [101.0, 102.0, 103.0],
        "Low": [99.0, 100.0, 101.0],
        "Close": [100.0, 102.0, 103.0],
        "Volume": [1000, 1100, 1200],
    })

    def fake_local_ohlcv(symbol, **kwargs):
        if symbol == "2330.TW":
            return prices
        raise ValueError("benchmark unavailable")

    monkeypatch.setattr(provider, "_local_ohlcv", fake_local_ohlcv)

    raw, alpha, days = provider._local_fetch_returns(
        object(),
        "2330.TW",
        "2026-06-03",
        holding_days=1,
        benchmark="SPY",
    )

    assert (raw, alpha, days) == (None, None, None)


def test_quantdinger_local_fetch_returns_computes_alpha_when_benchmark_available(monkeypatch):
    stock_prices = pd.DataFrame({
        "Date": ["2026-06-03", "2026-06-04", "2026-06-05"],
        "Open": [100.0, 101.0, 102.0],
        "High": [101.0, 102.0, 103.0],
        "Low": [99.0, 100.0, 101.0],
        "Close": [100.0, 102.0, 103.0],
        "Volume": [1000, 1100, 1200],
    })
    benchmark_prices = pd.DataFrame({
        "Date": ["2026-06-03", "2026-06-04", "2026-06-05"],
        "Open": [200.0, 200.5, 201.0],
        "High": [201.0, 202.0, 203.0],
        "Low": [199.0, 199.5, 200.0],
        "Close": [200.0, 201.0, 202.0],
        "Volume": [2000, 2100, 2200],
    })

    def fake_local_ohlcv(symbol, **kwargs):
        return benchmark_prices if symbol == "9999.TW" else stock_prices

    monkeypatch.setattr(provider, "_local_ohlcv", fake_local_ohlcv)

    raw, alpha, days = provider._local_fetch_returns(
        object(),
        "2330.TW",
        "2026-06-03",
        holding_days=1,
        benchmark="9999.TW",
    )

    assert round(raw, 8) == 0.02
    assert round(alpha, 8) == 0.015
    assert days == 1


def test_controlled_real_run_with_fake_graph_builds_valid_sanitized_artifact(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(ENABLE_REAL_RUN_ENV, "true")
    monkeypatch.setenv(REAL_RUN_CONFIRM_ENV, REAL_RUN_CONFIRM_VALUE)
    out_dir = ROOT / "data_tw/artifacts/analysis/tradingagents_readonly/pytest_fake_real_run"
    shutil.rmtree(out_dir, ignore_errors=True)

    def fake_graph_runner(**kwargs):
        assert kwargs["symbol"] == "2330.TW"
        assert kwargs["trade_date"] == "2026-06-30"
        assert kwargs["selected_analysts"] == ("market", "news")
        assert kwargs["config"]["backend_url"] == "https://chat.pku.edu.cn/v1"
        return {
            "market_report": "TW2330 market report says demand needs review.",
            "news_report": "News report says AI demand is supportive.",
            "fundamentals_report": "",
            "sentiment_report": "",
            "investment_debate_state": {
                "bull_history": "先进制程需求仍是支持线索。",
                "bear_history": "汇率与库存变化是压力线索。",
            },
            "risk_debate_state": {"history": "事件风险需要人工复核。"},
            "final_trade_decision": "Rating: Buy\nPrice target and stop loss were in raw output.",
        }, "Buy"

    try:
        result = run_tradingagents_readonly_analysis(
            output_dir=out_dir,
            run_id="pytest_fake_real_run",
            dry_run=False,
            symbol="2330",
            trade_date="2026-06-30",
            selected_analysts=["market", "news"],
            llm_base_url="https://chat.pku.edu.cn/v1",
            graph_runner=fake_graph_runner,
        )

        assert result["ok"] is True, result
        assert result["mode"] == "controlled_real_run"
        assert result["real_run_enabled"] is True
        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        report = json.loads((out_dir / "sanitized_report.json").read_text(encoding="utf-8"))
        assert manifest["run_mode"] == "controlled_real_run"
        assert manifest["manual_run_only"] is True
        assert manifest["no_latest_pointer_update"] is True
        assert manifest["no_openai_call"] is False
        assert manifest["no_network_call"] is False
        assert manifest["no_tradingagents_graph_call"] is False
        assert manifest["runtime_paths"]["results_dir"].endswith("_raw_runs/pytest_fake_real_run")
        blob = json.dumps(report, ensure_ascii=False)
        assert "Buy" not in blob
        assert "Price target" not in blob
        assert "stop loss" not in blob
        assert report["symbols"][0]["symbol"] == "2330"
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def test_controlled_real_run_exception_returns_structured_failure(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(ENABLE_REAL_RUN_ENV, "true")
    monkeypatch.setenv(REAL_RUN_CONFIRM_ENV, REAL_RUN_CONFIRM_VALUE)
    out_dir = ROOT / "data_tw/artifacts/analysis/tradingagents_readonly/pytest_failed_real_run"
    shutil.rmtree(out_dir, ignore_errors=True)

    def failing_graph_runner(**kwargs):
        raise RuntimeError("vendor_rate_limited")

    result = run_tradingagents_readonly_analysis(
        output_dir=out_dir,
        run_id="pytest_failed_real_run",
        dry_run=False,
        symbol="2330.TW",
        trade_date="2026-06-30",
        selected_analysts=["market"],
        graph_runner=failing_graph_runner,
    )

    assert result["ok"] is False
    assert result["status"] == "failed"
    assert result["reason"] == "controlled_real_run_failed"
    assert result["error_type"] == "RuntimeError"
    assert result["safety"]["artifact_created"] is False
    assert not out_dir.exists()


def test_runner_cli_json_dry_run(tmp_path: Path, capsys):
    runner = _load_module("run_tradingagents_readonly_analysis", RUN_SCRIPT)
    out_dir = tmp_path / "cli_artifact"

    assert runner.main(
        [
            "--fixture",
            str(FIXTURE),
            "--dry-run",
            "--output-dir",
            str(out_dir),
            "--run-id",
            "adapter_cli_pytest",
            "--json",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True, payload
    assert payload["mode"] == "dry_run"
    assert payload["validation"]["ok"] is True
    assert (out_dir / "manifest.json").exists()


def test_runner_cli_real_run_returns_blocked(tmp_path: Path, capsys, monkeypatch):
    monkeypatch.setenv(ENABLE_REAL_RUN_ENV, "true")
    monkeypatch.delenv(REAL_RUN_CONFIRM_ENV, raising=False)
    runner = _load_module("run_tradingagents_readonly_analysis_blocked", RUN_SCRIPT)
    out_dir = tmp_path / "cli_blocked"

    assert runner.main([
        "--fixture",
        str(FIXTURE),
        "--output-dir",
        str(out_dir),
        "--real-run",
        "--symbol",
        "2330.TW",
        "--trade-date",
        "2026-06-30",
        "--json",
    ]) == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is False
    assert payload["status"] == "blocked"
    assert payload["reason"] == "real_run_confirmation_missing"
    assert not out_dir.exists()
