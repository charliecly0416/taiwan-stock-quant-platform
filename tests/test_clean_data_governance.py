from pathlib import Path

import pandas as pd
import pytest

from clean_product.config import datasets
from clean_product.data import DataCatalog, DataError, FinMindAdapter
from clean_product.data import QlibProviderAdapter
import numpy as np


def config(tmp_path):
    return {"data_root": tmp_path / "data", "artifact_root": tmp_path / "artifacts",
            "universe": ["TW2330"], "datasets": {
                "prices": {"source": "finmind", "endpoint": "TaiwanStockPrice",
                           "fields": ["stock_id", "date", "close"],
                           "required": ["stock_id", "date", "close"], "numeric": ["close"]},
                "institutional": {"source": "finmind", "endpoint": "flow",
                                  "fields": ["stock_id", "date", "name", "buy"],
                                  "primary_key": ["stock_id", "date", "name"],
                                  "numeric": ["buy"]}}}


def test_readonly_catalog_construction_does_not_create_data_directory(tmp_path):
    cfg = config(tmp_path)
    catalog = DataCatalog(cfg)
    assert not cfg["data_root"].exists()
    with pytest.raises(DataError):
        catalog.query("prices")
    assert not cfg["data_root"].exists()


def test_price_correction_replaces_same_key_instead_of_duplicating_history(tmp_path):
    cfg = config(tmp_path); catalog = DataCatalog(cfg); spec = datasets(cfg)["prices"]
    for close in (10, 12):
        catalog.store(spec, pd.DataFrame([{"stock_id": "2330", "date": "2026-09-24", "close": close}]),
                      "2026-09-24", "fixture")
    result = catalog.query("prices")
    assert len(result) == 1 and result.iloc[0].close == 12


def test_composite_key_preserves_institution_categories_and_revises_one(tmp_path):
    cfg = config(tmp_path); catalog = DataCatalog(cfg); spec = datasets(cfg)["institutional"]
    base = {"stock_id": "2330", "date": "2026-09-24"}
    catalog.store(spec, pd.DataFrame([{**base, "name": "Foreign", "buy": 10},
                                    {**base, "name": "Trust", "buy": 30}]), "2026-09-24", "fixture")
    catalog.store(spec, pd.DataFrame([{**base, "name": "Foreign", "buy": 20}]),
                  "2026-09-24", "fixture")
    rows = catalog.query("institutional").set_index("name")
    assert len(rows) == 2 and rows.loc["Foreign", "buy"] == 20 and rows.loc["Trust", "buy"] == 30


def test_unregistered_dataset_cannot_read_an_existing_csv(tmp_path):
    cfg = config(tmp_path); cfg["data_root"].mkdir()
    (cfg["data_root"] / "private.csv").write_text("date,value\n2026-09-24,123\n")
    with pytest.raises(DataError, match="not registered"):
        DataCatalog(cfg).query("private")


@pytest.mark.parametrize('field,value', [('date', None), ('stock_id', None), ('date', '2026-02-30'), ('date', 'not-a-date')])
def test_null_keys_and_invalid_dates_cannot_become_literal_strings(tmp_path, field, value):
    cfg = config(tmp_path)
    row = {'stock_id': '2330', 'date': '2026-09-24', 'close': 100, field: value}
    with pytest.raises(DataError):
        DataCatalog(cfg).normalize(datasets(cfg)['prices'], [row])


@pytest.mark.parametrize("symbol,expected", [("TW2330", "2330"), ("TWII", "TWII")])
def test_provider_symbol_mapping_keeps_index_identifiers(tmp_path, monkeypatch, symbol, expected):
    cfg = config(tmp_path); cfg["universe"] = [symbol]
    monkeypatch.setenv("FINMIND_TOKEN", "fixture-only")
    called = []
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"msg": "success", "data": []}
    def get(url, *, params, timeout):
        called.append(params["data_id"]); return Response()
    monkeypatch.setattr("clean_product.data.requests.get", get)
    FinMindAdapter().fetch(datasets(cfg)["prices"], asof="2026-09-24", start="2026-09-23", config=cfg)
    assert called == [expected]


def test_provider_status_counts_actual_prices_and_detects_missing_fields(tmp_path):
    cfg = config(tmp_path)
    provider = tmp_path / 'provider'; calendar = provider / 'calendars'
    calendar.mkdir(parents=True); (calendar / 'day.txt').write_text('2026-09-23\n2026-09-24\n')
    folder = provider / 'features/tw2330'; folder.mkdir(parents=True)
    for field in ('open', 'high', 'low', 'close', 'volume', 'vwap'):
        np.array([0, 100, np.nan], dtype='<f4').tofile(folder / f'{field}.day.bin')
    cfg['datasets'] = {'prices': {'source': 'qlib_provider', 'endpoint': 'prices',
                                 'params': {'provider_uri': str(provider)}}}
    status = DataCatalog(cfg).status()[0]
    assert status['rows'] == 1 and status['latest_asof'] == '2026-09-23'
    assert status['calendar_latest'] == '2026-09-24'
    (folder / 'open.day.bin').unlink()
    assert DataCatalog(cfg).status()[0]['status'] == 'BLOCKED'


@pytest.mark.parametrize('values', [[-1, 1], [2, 1], [.5, 1], [np.nan, 1]])
def test_invalid_provider_offsets_are_rejected(tmp_path, values):
    target = tmp_path / 'close.day.bin'
    np.array(values, dtype='<f4').tofile(target)
    with pytest.raises(DataError):
        QlibProviderAdapter._decode(target, 2)
