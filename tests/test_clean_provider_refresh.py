from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from clean_product.provider_refresh import COLUMNS, _write_provider, refresh_yahoo_provider


def prices(symbol, dates, factor=1):
    return pd.DataFrame([dict(symbol=symbol, date=day, open=10*factor, high=12*factor,
        low=9*factor, close=11*factor, volume=100, vwap=10.5*factor, factor=factor) for day in dates])


def config(tmp_path):
    source = tmp_path / "source"; source.mkdir()
    return {"artifact_root": str(tmp_path / "artifacts"), "model_stages": {"model_a_frozen": {}},
            "provider_refresh": {"source_dir": str(source), "minimum_coverage": .5, "workers": 2, "proxy": ""}}


def test_runtime_contract_includes_scheduled_yahoo_fetcher():
    requirements = (Path(__file__).parents[1] / "backend" / "requirements.txt").read_text()
    constraints = (Path(__file__).parents[1] / "backend" / "requirements-runtime.lock").read_text()
    assert "scrapling[fetchers]==0.4.8" in requirements
    assert "scrapling==0.4.8" in constraints


def test_provider_binary_offsets_preserve_missing_days(tmp_path):
    source = tmp_path / "source"; source.mkdir()
    prices("TW2330", ["2026-09-21", "2026-09-23"]).to_csv(source / "TW2330.csv", index=False)
    prices("TW2317", ["2026-09-22", "2026-09-23"]).to_csv(source / "TW2317.csv", index=False)
    output = tmp_path / "provider"
    assert _write_provider(source, output)["symbols"] == 2
    assert np.fromfile(output / "features/tw2317/close.day.bin", dtype="<f4").tolist() == [1, 11, 11]
    values = np.fromfile(output / "features/tw2330/close.day.bin", dtype="<f4")
    assert values[0] == 0 and np.isnan(values[2]) and values[3] == 11


def test_refresh_uses_incremental_overlap_and_tolerates_one_failed_symbol(tmp_path, monkeypatch):
    cfg = config(tmp_path); source = Path(cfg["provider_refresh"]["source_dir"])
    for symbol in ("TW2330", "TW2317"):
        prices(symbol, ["2026-09-23"]).to_csv(source / (symbol + ".csv"), index=False)
    calls = []
    def fetch(symbol, start, asof, proxy):
        calls.append((symbol, start))
        if symbol == "TW2317": raise TimeoutError("do not expose transport details")
        return prices(symbol, ["2026-09-23", asof])
    monkeypatch.setattr("clean_product.provider_refresh._fetch", fetch)
    result = refresh_yahoo_provider(cfg, "2026-09-24", "test")
    assert result["coverage"] == .5 and result["symbols"] == 2
    assert result["fetch_errors"] == {"TW2317": "TimeoutError"}
    assert {start for _, start in calls} == {"2026-08-10"}


def test_adjustment_change_refreshes_whole_history(tmp_path, monkeypatch):
    cfg = config(tmp_path); source = Path(cfg["provider_refresh"]["source_dir"])
    prices("TW2330", ["2018-01-02", "2026-09-23"]).to_csv(source / "TW2330.csv", index=False)
    calls = []
    def fetch(symbol, start, asof, proxy):
        calls.append(start)
        return prices(symbol, ["2018-01-02", "2026-09-23", asof] if start == "2015-01-01" else ["2026-09-23", asof], .5)
    monkeypatch.setattr("clean_product.provider_refresh._fetch", fetch)
    result = refresh_yahoo_provider(cfg, "2026-09-24", "test")
    rows = pd.read_csv(Path(result["selection_prices"]) / "TW2330.csv")
    assert calls == ["2026-08-10", "2015-01-01"]
    assert rows.close.tolist() == [5.5, 5.5, 5.5]


def test_insufficient_coverage_is_not_ready(tmp_path, monkeypatch):
    cfg = config(tmp_path); source = Path(cfg["provider_refresh"]["source_dir"])
    prices("TW2330", ["2026-09-23"]).to_csv(source / "TW2330.csv", index=False)
    monkeypatch.setattr("clean_product.provider_refresh._fetch", lambda *a: pd.DataFrame(columns=COLUMNS))
    with pytest.raises(RuntimeError, match="coverage"):
        refresh_yahoo_provider(cfg, "2026-09-24", "test")
