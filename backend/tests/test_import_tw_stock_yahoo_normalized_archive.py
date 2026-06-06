"""Offline tests for local Yahoo/Scrapling normalized TWStock archive import."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "import_tw_stock_yahoo_normalized_archive.py"
SPEC = importlib.util.spec_from_file_location("import_tw_stock_yahoo_normalized_archive", SCRIPT_PATH)
import_tw_stock_yahoo_normalized_archive = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["import_tw_stock_yahoo_normalized_archive"] = import_tw_stock_yahoo_normalized_archive
SPEC.loader.exec_module(import_tw_stock_yahoo_normalized_archive)


def test_parse_symbols_normalizes_top_universe_formats():
    symbols = import_tw_stock_yahoo_normalized_archive.parse_symbols([
        "TW2330, 0050.TW",
        "TWSE:2330\nTPEX:6488",
        "TW6290",
    ])

    assert symbols == ["2330", "0050", "6488", "6290"]


def test_iter_rows_filters_dates_and_bad_prices(tmp_path):
    csv_path = tmp_path / "TW2330.csv"
    csv_path.write_text(
        "date,open,high,low,close,volume,vwap,factor\n"
        "2025-09-17,100,105,99,104,1000,102,1\n"
        "2025-09-18,104,108,103,107,1200,106,1\n"
        "2025-09-19,0,108,103,107,1200,106,1\n"
        "2025-09-22,108,110,106,109,1500,109,1\n",
        encoding="utf-8",
    )

    rows = list(import_tw_stock_yahoo_normalized_archive.iter_rows(
        csv_path,
        symbol="2330",
        start="2025-09-18",
        end="2025-09-21",
    ))

    assert len(rows) == 1
    assert rows[0]["symbol"] == "2330"
    assert rows[0]["trade_date"] == "2025-09-18"
    assert rows[0]["source"] == "yahoo_adjusted"
    assert rows[0]["close"] == 107.0
    assert rows[0]["volume"] == 1200


def test_main_dry_run_reports_rows_without_writing(tmp_path, monkeypatch, capsys):
    normalized_dir = tmp_path / "normalized"
    normalized_dir.mkdir()
    (normalized_dir / "TW2330.csv").write_text(
        "date,open,high,low,close,volume,vwap,factor\n"
        "2025-09-18,104,108,103,107,1200,106,1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        import_tw_stock_yahoo_normalized_archive,
        "upsert",
        lambda rows: (_ for _ in ()).throw(AssertionError("dry run should not write")),
    )

    exit_code = import_tw_stock_yahoo_normalized_archive.main([
        "--symbol", "TW2330, TW9999",
        "--normalized-dir", str(normalized_dir),
        "--start", "2025-09-18",
        "--end", "2025-09-21",
    ])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert '"row_count": 1' in out
    assert '"written_count": 0' in out
    assert '"9999"' in out
