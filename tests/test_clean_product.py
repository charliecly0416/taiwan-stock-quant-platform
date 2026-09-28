from pathlib import Path

import pandas as pd

from clean_product.config import datasets, models
from clean_product.data import DataCatalog
from clean_product.models import ModelRunner, SignalResult
from clean_product.replay import replay
from clean_product.service import ProductService, _technical
from clean_product.strategy import top50_exit_one_worst_sell


def config(tmp_path: Path):
    return {
        "data_root": tmp_path / "data", "artifact_root": tmp_path / "artifacts",
        "universe": ["0001", "0002", "0003"], "strategy": "top50_exit_one_worst_sell",
        "simulation": {"initial_cash": 1000000, "max_positions": 3, "buy_cost_rate": 0, "sell_cost_rate": 0, "min_cost": 0},
        "datasets": {"prices": {"endpoint": "fixture", "date_field": "date", "fields": ["stock_id", "date", "close"]}},
        "model_stages": {"model_a_frozen": {}, "b19r2r_frozen": {}},
        "models": {
            "model_a": {"role": "baseline", "stages": ["model_a_frozen"], "production_allowed": True},
            "model_a_plus_b": {"role": "shadow", "stages": ["model_a_frozen", "b19r2r_frozen"], "production_allowed": False},
        },
    }


def prices():
    return pd.DataFrame([
        {"stock_id": symbol, "instrument": symbol, "date": day, "open": value, "close": value}
        for day, shift in [("2026-09-24", 0), ("2026-09-25", 1)]
        for symbol, value in [("0001", 10 + shift), ("0002", 20 + shift), ("0003", 15 + shift)]
    ])


def test_models_are_equal_pipelines_with_roles(tmp_path):
    cfg = config(tmp_path)
    specs = models(cfg)
    assert specs["model_a"].role == "baseline"
    assert specs["model_a_plus_b"].role == "shadow"
    runner = ModelRunner(cfg)
    data = {"prices": prices()}
    assert runner.run("model_a", "2026-09-25", data=data, fixture=True).rows.iloc[0].instrument == "TW0002"
    assert runner.run("model_a_plus_b", "2026-09-25", data=data, fixture=True).rows.iloc[0].instrument == "TW0002"


def test_data_catalog_has_one_store_query_path(tmp_path):
    cfg = config(tmp_path)
    catalog = DataCatalog(cfg)
    spec = datasets(cfg)["prices"]
    catalog.store(spec, prices().drop(columns="instrument"), "2026-09-25", "fixture")
    assert len(catalog.query("prices", "2026-09-25", "2026-09-25")) == 3


def test_new_dataset_uses_registered_source_and_shared_governance(tmp_path):
    cfg = config(tmp_path)
    cfg["datasets"]["valuation"] = {
        "source": "test_source",
        "endpoint": "valuation",
        "date_field": "asof",
        "symbols_field": "symbol",
        "fields": ["symbol", "asof", "pe"],
        "required": ["symbol", "asof", "pe"],
        "numeric": ["pe"],
    }

    class TestSource:
        def fetch(self, spec, *, asof, start, config):
            return [{"symbol": "1", "asof": asof, "pe": "12.5"}]

    catalog = DataCatalog(cfg)
    catalog.register_source("test_source", TestSource())
    manifest = catalog.fetch(datasets(cfg)["valuation"], "2026-09-25")
    result = catalog.query("valuation", end="2026-09-25")
    assert manifest["source"] == "test_source"
    assert result.iloc[0].symbol == "0001"
    assert result.iloc[0].pe == 12.5


def test_strategy_and_replay(tmp_path):
    cfg = config(tmp_path)
    signals = ModelRunner(cfg).run("model_a", "2026-09-25", data={"prices": prices()}, fixture=True).rows
    actions = top50_exit_one_worst_sell(signals, {"9999"})
    assert "sell" in set(actions.action)
    result = replay(cfg, {"prices": prices()}, "model_a", "2026-09-24", "2026-09-25", fixture=True)
    assert result["status"] == "READY" and result["trading_days"] == 2
    assert result["trade_count"] == 3
    assert result["account"]["mode"] == "simulation_only" and result["total_fees"] == 0


def test_clean_workbench_technical_context_is_deterministic():
    frame = prices().drop(columns="stock_id").rename(columns={"instrument": "stock_id"})
    result = _technical(frame)
    assert {"ma5", "ma20", "rsi14", "ret5", "ret20", "volume_ratio20"}.issubset(result.columns)
    latest = result[result.date == "2026-09-25"]
    assert len(latest) == 3 and latest.rsi14.notna().all()
    assert set(latest.instrument) == {"TW0001", "TW0002", "TW0003"}


def test_cross_analysis_joins_rankings_to_technical_context(tmp_path):
    cfg = config(tmp_path)
    service = ProductService(cfg)
    signal = ModelRunner(cfg).run("model_a", "2026-09-25", data={"prices": prices()}, fixture=True)
    service.signal = lambda model, asof=None: SignalResult(model, "2026-09-25", signal.rows)
    service._model_data = lambda asof, start=None: {"prices": prices().drop(columns="instrument")}
    result = service.cross_analysis("model_a", "2026-09-25", limit=2)
    assert result["status"] == "READY"
    assert len(result["rows"]) == 2
    assert all(row["instrument"].startswith("TW") for row in result["rows"])
    assert all(pd.notna(row["ma20"]) and pd.notna(row["rsi14"]) for row in result["rows"])
