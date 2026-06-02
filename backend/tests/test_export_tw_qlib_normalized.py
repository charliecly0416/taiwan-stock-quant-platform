"""Offline tests for TWStock Qlib normalized CSV exporter."""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "export_tw_qlib_normalized.py"
SPEC = importlib.util.spec_from_file_location("export_tw_qlib_normalized", SCRIPT_PATH)
export_tw_qlib_normalized = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["export_tw_qlib_normalized"] = export_tw_qlib_normalized
SPEC.loader.exec_module(export_tw_qlib_normalized)


def _rows():
    return [
        {
            "date": "2026-05-21",
            "stock_id": "2330",
            "Trading_Volume": 24929331,
            "Trading_money": 55826019099,
            "open": 2240.0,
            "max": 2255.0,
            "min": 2230.0,
            "close": 2230.0,
        },
        {
            "date": "2026-05-22",
            "stock_id": "2330",
            "Trading_Volume": 26823133,
            "Trading_money": 60188140377,
            "open": 2245.0,
            "max": 2260.0,
            "min": 2225.0,
            "close": 2255.0,
        },
    ]


def test_normalize_output_symbol_and_query_symbol():
    assert export_tw_qlib_normalized.normalize_output_symbol("2330") == "TW2330"
    assert export_tw_qlib_normalized.normalize_output_symbol("TW2330") == "TW2330"
    assert export_tw_qlib_normalized.normalize_output_symbol("2330.TW") == "TW2330"
    assert export_tw_qlib_normalized.normalize_output_symbol("TAIEX") == "TWII"
    assert export_tw_qlib_normalized.query_symbol_for_output("TWII") == "TAIEX"
    assert export_tw_qlib_normalized.query_symbol_for_output("TW2330") == "2330"


def test_parse_symbols_from_data_spec(tmp_path):
    spec = tmp_path / "data.txt"
    spec.write_text(
        "最低建议先准备这些：\n\nTWII    # 加权指数\nTW2330\n2330\nTW2317\n",
        encoding="utf-8",
    )

    symbols = export_tw_qlib_normalized.parse_symbols_from_data_spec(spec)

    assert symbols == ["TWII", "TW2330", "TW2317"]


def test_parse_qlib_rows_uses_trading_money_vwap():
    rows, flags = export_tw_qlib_normalized.parse_qlib_rows(_rows(), "TW2330")

    assert flags == []
    assert len(rows) == 2
    assert rows[0].symbol == "TW2330"
    assert rows[0].date == "2026-05-21"
    assert rows[0].open == 2240.0
    assert rows[0].high == 2255.0
    assert rows[0].low == 2230.0
    assert rows[0].close == 2230.0
    assert rows[0].volume == 24929331
    assert rows[0].vwap == round(55826019099 / 24929331, 6)
    assert rows[0].factor == 1.0


def test_parse_qlib_rows_falls_back_to_ohlc4_vwap():
    raw = [{"date": "2026-05-22", "open": 10, "max": 14, "min": 8, "close": 12, "Trading_Volume": 0}]

    rows, flags = export_tw_qlib_normalized.parse_qlib_rows(raw, "2330")

    assert rows[0].vwap == 11.0
    assert flags == ["fallback_vwap"]


def test_write_csv_uses_required_columns(tmp_path):
    rows, _ = export_tw_qlib_normalized.parse_qlib_rows(_rows()[:1], "2330")
    path = tmp_path / "TW2330.csv"

    export_tw_qlib_normalized.write_csv(path, rows)

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == export_tw_qlib_normalized.OUTPUT_COLUMNS
        first = next(reader)
    assert first["symbol"] == "TW2330"
    assert first["date"] == "2026-05-21"
    assert first["factor"] == "1.0"


def test_export_symbol_fetches_and_writes_csv(monkeypatch, tmp_path):
    monkeypatch.setattr(export_tw_qlib_normalized, "fetch_finmind_rows", lambda query_symbol, start, end: _rows())

    item = export_tw_qlib_normalized.export_symbol("TW2330", "2026-05-21", "2026-05-22", tmp_path)

    assert item.symbol == "TW2330"
    assert item.query_symbol == "2330"
    assert item.rows == 2
    assert item.date_min == "2026-05-21"
    assert item.date_max == "2026-05-22"
    assert Path(item.output_file).name == "TW2330.csv"
    assert Path(item.output_file).exists()


def test_main_returns_one_when_any_symbol_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(export_tw_qlib_normalized, "fetch_finmind_rows", lambda query_symbol, start, end: [] if query_symbol == "2317" else _rows())

    exit_code = export_tw_qlib_normalized.main([
        "--symbol",
        "TW2330,TW2317",
        "--start",
        "2026-05-21",
        "--end",
        "2026-05-22",
        "--output-dir",
        str(tmp_path),
    ])

    assert exit_code == 1
    assert (tmp_path / "TW2330.csv").exists()
    assert (tmp_path / "TW2317.csv").exists()


def test_parse_qlib_rows_uses_ohlc4_for_index_when_money_vwap_disabled():
    rows, flags = export_tw_qlib_normalized.parse_qlib_rows(
        [{
            "date": "2026-05-22",
            "open": 41447.92,
            "max": 42357.6,
            "min": 41447.92,
            "close": 42267.97,
            "Trading_Volume": 14518650616,
            "Trading_money": 1236957101206,
        }],
        "TWII",
        prefer_money_vwap=False,
    )

    assert flags == []
    assert rows[0].vwap == round((41447.92 + 42357.6 + 41447.92 + 42267.97) / 4, 6)


def test_export_symbol_continue_on_error_writes_empty_csv(monkeypatch, tmp_path):
    monkeypatch.setattr(
        export_tw_qlib_normalized,
        "fetch_finmind_rows",
        lambda query_symbol, start, end: (_ for _ in ()).throw(ConnectionError("reset")),
    )

    item = export_tw_qlib_normalized.export_symbol(
        "TW2330",
        "2026-05-21",
        "2026-05-22",
        tmp_path,
        continue_on_error=True,
    )

    assert item.rows == 0
    assert item.flags == ["fetch_error"]
    assert "reset" in item.error
    assert (tmp_path / "TW2330.csv").read_text(encoding="utf-8").splitlines()[0] == ",".join(export_tw_qlib_normalized.OUTPUT_COLUMNS)
