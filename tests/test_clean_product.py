from pathlib import Path

import pandas as pd

from clean_product.config import datasets, models
from clean_product.data import DataCatalog
from clean_product.models import ModelRunner
from clean_product.replay import replay
from clean_product.strategy import top50_exit_one_worst_sell


def config(tmp_path: Path):
    return {
        "data_root": tmp_path / "data", "artifact_root": tmp_path / "artifacts",
        "universe": ["0001", "0002", "0003"], "strategy": "top50_exit_one_worst_sell",
        "datasets": {"prices": {"endpoint": "fixture", "date_field": "date", "fields": ["stock_id", "date", "close"]}},
        "models": {
            "model_a": {"role": "baseline", "stages": ["model_a_score"], "production_allowed": True},
            "model_a_plus_b": {"role": "shadow", "stages": ["model_a_score", "model_b_rerank"], "production_allowed": False},
        },
    }


def prices():
    return pd.DataFrame([
        {"stock_id": symbol, "instrument": symbol, "date": day, "close": value}
        for day, shift in [("2026-09-24", 0), ("2026-09-25", 1)]
        for symbol, value in [("0001", 10 + shift), ("0002", 20 + shift), ("0003", 15 + shift)]
    ])


def test_models_are_equal_pipelines_with_roles(tmp_path):
    cfg = config(tmp_path)
    specs = models(cfg)
    assert specs["model_a"].role == "baseline"
    assert specs["model_a_plus_b"].role == "shadow"
    runner = ModelRunner(cfg)
    assert runner.run("model_a", prices(), "2026-09-25").rows.iloc[0].instrument == "0002"
    assert runner.run("model_a_plus_b", prices(), "2026-09-25").rows.iloc[0].instrument == "0002"


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
    signals = ModelRunner(cfg).run("model_a", prices(), "2026-09-25").rows
    actions = top50_exit_one_worst_sell(signals, {"9999"})
    assert "sell" in set(actions.action)
    result = replay(cfg, prices(), "model_a", "2026-09-24", "2026-09-25")
    assert result["status"] == "READY" and result["days"] == 2
