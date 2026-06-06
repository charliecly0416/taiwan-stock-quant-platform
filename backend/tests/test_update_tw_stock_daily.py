"""Offline tests for the daily TWStock archive + validation workflow."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from scripts.archive_tw_stock_daily import DailyBarRecord
from scripts.validate_tw_stock_daily import OfficialTwseRow, ValidationResult


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "update_tw_stock_daily.py"
SPEC = importlib.util.spec_from_file_location("update_tw_stock_daily", SCRIPT_PATH)
update_tw_stock_daily = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["update_tw_stock_daily"] = update_tw_stock_daily
SPEC.loader.exec_module(update_tw_stock_daily)


def _record(symbol: str = "2330", trade_date: str = "2026-05-22") -> DailyBarRecord:
    return DailyBarRecord(
        symbol=symbol,
        exchange="TWSE",
        instrument_type="stock" if symbol != "0050" else "etf",
        trade_date=trade_date,
        open=2245.0,
        high=2260.0,
        low=2225.0,
        close=2255.0,
        volume=26823133,
        trading_money=60188140377.0,
        trading_turnover=95365,
        spread=25.0,
        source="finmind",
        official_checked=0,
        official_match=0,
        quality_flags="",
        raw_json="{}",
    )


def _validation(symbol: str = "2330", *, match: bool = True, checked: bool = True) -> ValidationResult:
    return ValidationResult(
        symbol=symbol,
        trade_date="2026-05-22",
        source="finmind",
        official_checked=1 if checked else 0,
        official_match=1 if match else 0,
        quality_flags="" if match and checked else "official_missing",
        local_close=2255.0,
        official_close=2255.0 if match else 0.0,
        local_volume=26823133,
        official_volume=26823133 if match else 0,
    )


def test_parse_symbols_splits_commas_newlines_normalizes_and_dedupes():
    symbols = update_tw_stock_daily.parse_symbols(["TW2330, 0050.TW", "TWSE:2330\nTPEX:6488", "", " 00878 "])

    assert symbols == ["2330", "0050", "6488", "00878"]


def test_load_symbols_from_file_skips_blanks_comments_and_dedupes_lines(tmp_path):
    path = tmp_path / "symbols.txt"
    path.write_text("\n# comment\n2330,0050\n0056\n", encoding="utf-8")

    symbols = update_tw_stock_daily.load_symbols_from_file(str(path))

    assert symbols == ["2330", "0050", "0056"]


def test_validate_latest_compares_each_latest_record_to_twse_official(monkeypatch):
    official = {
        "2330": OfficialTwseRow("2330", "台積電", "2026-05-22", 2255.0, 26823133, "{}"),
        "0050": OfficialTwseRow("0050", "元大台灣50", "2026-05-22", 2255.0, 26823133, "{}"),
    }
    monkeypatch.setattr(update_tw_stock_daily, "fetch_twse_rows", lambda: official)

    results = update_tw_stock_daily.validate_latest(
        [_record("0050", "2026-05-21"), _record("2330"), _record("0050", "2026-05-22")]
    )

    assert [item.symbol for item in results] == ["0050", "2330"]
    assert all(item.official_match for item in results)


def test_run_workflow_dry_run_does_not_write_archive_or_validation(monkeypatch):
    calls = []
    monkeypatch.setattr(update_tw_stock_daily, "archive_symbols", lambda symbols, start, end: [_record("2330")])
    monkeypatch.setattr(update_tw_stock_daily, "validate_latest", lambda records: [_validation("2330")])
    monkeypatch.setattr(update_tw_stock_daily, "archive_corporate_action_symbols", lambda symbols, start, end: [object()])
    monkeypatch.setattr(update_tw_stock_daily, "summarize_corporate_actions", lambda records: {"count": len(records)})
    monkeypatch.setattr(update_tw_stock_daily, "archive_institutional_symbols", lambda symbols, start, end: [object(), object()])
    monkeypatch.setattr(update_tw_stock_daily, "summarize_institutional_trades", lambda records: {"count": len(records)})
    monkeypatch.setattr(update_tw_stock_daily, "archive_margin_symbols", lambda symbols, start, end: [object(), object(), object()])
    monkeypatch.setattr(update_tw_stock_daily, "summarize_margin_trading", lambda records: {"count": len(records)})
    monkeypatch.setattr(update_tw_stock_daily, "archive_monthly_revenue_symbols", lambda symbols, start, end: [object(), object(), object(), object()])
    monkeypatch.setattr(update_tw_stock_daily, "summarize_monthly_revenue", lambda records: {"count": len(records)})
    monkeypatch.setattr(update_tw_stock_daily, "archive_valuation_symbols", lambda symbols, start, end: [object(), object(), object(), object(), object()])
    monkeypatch.setattr(update_tw_stock_daily, "summarize_valuation", lambda records: {"count": len(records)})
    monkeypatch.setattr(update_tw_stock_daily, "upsert_records", lambda records: calls.append("upsert") or len(records))
    monkeypatch.setattr(
        update_tw_stock_daily,
        "update_archive_validation",
        lambda results: calls.append("update_validation") or len(results),
    )
    monkeypatch.setattr(update_tw_stock_daily, "upsert_corporate_actions", lambda records: calls.append("upsert_ca") or len(records))
    monkeypatch.setattr(update_tw_stock_daily, "upsert_institutional_trades", lambda records: calls.append("upsert_inst") or len(records))
    monkeypatch.setattr(update_tw_stock_daily, "upsert_margin_trading", lambda records: calls.append("upsert_margin") or len(records))
    monkeypatch.setattr(update_tw_stock_daily, "upsert_monthly_revenue", lambda records: calls.append("upsert_revenue") or len(records))
    monkeypatch.setattr(update_tw_stock_daily, "upsert_valuation", lambda records: calls.append("upsert_valuation") or len(records))

    report = update_tw_stock_daily.run_workflow(symbols=["2330"], start="2026-05-20", end="2026-05-22")

    assert report["apply"] is False
    assert report["archive"]["count"] == 1
    assert report["archived_count"] == 0
    assert report["validation"]["matched"] == 1
    assert report["validation_updated_count"] == 0
    assert report["corporate_actions"]["count"] == 1
    assert report["corporate_actions_archived_count"] == 0
    assert report["institutional_trades"]["count"] == 2
    assert report["institutional_trades_archived_count"] == 0
    assert report["margin_trading"]["count"] == 3
    assert report["margin_trading_archived_count"] == 0
    assert report["monthly_revenue"]["count"] == 4
    assert report["monthly_revenue_archived_count"] == 0
    assert report["valuation"]["count"] == 5
    assert report["valuation_archived_count"] == 0
    assert calls == []


def test_run_workflow_apply_writes_archive_and_validation(monkeypatch):
    calls = []
    monkeypatch.setattr(update_tw_stock_daily, "archive_symbols", lambda symbols, start, end: [_record("2330")])
    monkeypatch.setattr(update_tw_stock_daily, "validate_latest", lambda records: [_validation("2330")])
    monkeypatch.setattr(update_tw_stock_daily, "archive_corporate_action_symbols", lambda symbols, start, end: [object()])
    monkeypatch.setattr(update_tw_stock_daily, "summarize_corporate_actions", lambda records: {"count": len(records)})
    monkeypatch.setattr(update_tw_stock_daily, "archive_institutional_symbols", lambda symbols, start, end: [object(), object()])
    monkeypatch.setattr(update_tw_stock_daily, "summarize_institutional_trades", lambda records: {"count": len(records)})
    monkeypatch.setattr(update_tw_stock_daily, "archive_margin_symbols", lambda symbols, start, end: [object(), object(), object()])
    monkeypatch.setattr(update_tw_stock_daily, "summarize_margin_trading", lambda records: {"count": len(records)})
    monkeypatch.setattr(update_tw_stock_daily, "archive_monthly_revenue_symbols", lambda symbols, start, end: [object(), object(), object(), object()])
    monkeypatch.setattr(update_tw_stock_daily, "summarize_monthly_revenue", lambda records: {"count": len(records)})
    monkeypatch.setattr(update_tw_stock_daily, "archive_valuation_symbols", lambda symbols, start, end: [object(), object(), object(), object(), object()])
    monkeypatch.setattr(update_tw_stock_daily, "summarize_valuation", lambda records: {"count": len(records)})
    monkeypatch.setattr(update_tw_stock_daily, "upsert_records", lambda records: calls.append(("upsert", len(records))) or len(records))
    monkeypatch.setattr(
        update_tw_stock_daily,
        "update_archive_validation",
        lambda results: calls.append(("update_validation", len(results))) or len(results),
    )
    monkeypatch.setattr(
        update_tw_stock_daily,
        "upsert_corporate_actions",
        lambda records: calls.append(("upsert_ca", len(records))) or len(records),
    )
    monkeypatch.setattr(
        update_tw_stock_daily,
        "upsert_institutional_trades",
        lambda records: calls.append(("upsert_inst", len(records))) or len(records),
    )
    monkeypatch.setattr(
        update_tw_stock_daily,
        "upsert_margin_trading",
        lambda records: calls.append(("upsert_margin", len(records))) or len(records),
    )
    monkeypatch.setattr(
        update_tw_stock_daily,
        "upsert_monthly_revenue",
        lambda records: calls.append(("upsert_revenue", len(records))) or len(records),
    )
    monkeypatch.setattr(
        update_tw_stock_daily,
        "upsert_valuation",
        lambda records: calls.append(("upsert_valuation", len(records))) or len(records),
    )

    report = update_tw_stock_daily.run_workflow(
        symbols=["2330"],
        start="2026-05-20",
        end="2026-05-22",
        apply=True,
    )

    assert report["archived_count"] == 1
    assert report["validation_updated_count"] == 1
    assert report["corporate_actions_archived_count"] == 1
    assert report["institutional_trades_archived_count"] == 2
    assert report["margin_trading_archived_count"] == 3
    assert report["monthly_revenue_archived_count"] == 4
    assert report["valuation_archived_count"] == 5
    assert calls == [("upsert", 1), ("update_validation", 1), ("upsert_ca", 1), ("upsert_inst", 2), ("upsert_margin", 3), ("upsert_revenue", 4), ("upsert_valuation", 5)]


def test_main_returns_success_for_matched_dry_run(monkeypatch, capsys):
    monkeypatch.setattr(
        update_tw_stock_daily,
        "run_workflow",
        lambda **kwargs: {
            "symbols": kwargs["symbols"],
            "start": kwargs["start"],
            "end": kwargs["end"],
            "apply": kwargs["apply"],
            "archive": {"count": 1},
            "archived_count": 0,
            "validation": {"mismatched": 0, "unchecked": 0},
            "validation_updated_count": 0,
        },
    )

    exit_code = update_tw_stock_daily.main(["--symbol", "2330,0050", "--start", "2026-05-20", "--end", "2026-05-22"])

    assert exit_code == 0
    assert '"symbols": [' in capsys.readouterr().out


def test_main_returns_one_for_validation_mismatch(monkeypatch):
    monkeypatch.setattr(
        update_tw_stock_daily,
        "run_workflow",
        lambda **kwargs: {"archive": {"count": 1}, "validation": {"mismatched": 1, "unchecked": 0}},
    )

    assert update_tw_stock_daily.main(["--symbol", "2330"]) == 1


def test_main_returns_two_when_no_archive_records(monkeypatch):
    monkeypatch.setattr(
        update_tw_stock_daily,
        "run_workflow",
        lambda **kwargs: {"archive": {"count": 0}, "validation": {"mismatched": 0, "unchecked": 0}},
    )

    assert update_tw_stock_daily.main(["--symbol", "2330"]) == 2


def test_run_workflow_can_skip_corporate_actions(monkeypatch):
    monkeypatch.setattr(update_tw_stock_daily, "archive_symbols", lambda symbols, start, end: [_record("2330")])
    monkeypatch.setattr(update_tw_stock_daily, "validate_latest", lambda records: [])
    monkeypatch.setattr(
        update_tw_stock_daily,
        "archive_corporate_action_symbols",
        lambda symbols, start, end: (_ for _ in ()).throw(AssertionError("corporate actions should not run")),
    )
    monkeypatch.setattr(update_tw_stock_daily, "archive_institutional_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_margin_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_monthly_revenue_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_valuation_symbols", lambda symbols, start, end: [])

    report = update_tw_stock_daily.run_workflow(
        symbols=["2330"],
        start="2026-05-20",
        end="2026-05-22",
        corporate_actions=False,
    )

    assert report["corporate_actions"]["count"] == 0
    assert report["corporate_actions_archived_count"] == 0


def test_run_workflow_can_skip_institutional_trades(monkeypatch):
    monkeypatch.setattr(update_tw_stock_daily, "archive_symbols", lambda symbols, start, end: [_record("2330")])
    monkeypatch.setattr(update_tw_stock_daily, "validate_latest", lambda records: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_corporate_action_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(
        update_tw_stock_daily,
        "archive_institutional_symbols",
        lambda symbols, start, end: (_ for _ in ()).throw(AssertionError("institutional should not run")),
    )
    monkeypatch.setattr(update_tw_stock_daily, "archive_margin_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_monthly_revenue_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_valuation_symbols", lambda symbols, start, end: [])

    report = update_tw_stock_daily.run_workflow(
        symbols=["2330"],
        start="2026-05-20",
        end="2026-05-22",
        institutional=False,
    )

    assert report["institutional_trades"]["count"] == 0
    assert report["institutional_trades_archived_count"] == 0


def test_run_workflow_can_skip_margin_trading(monkeypatch):
    monkeypatch.setattr(update_tw_stock_daily, "archive_symbols", lambda symbols, start, end: [_record("2330")])
    monkeypatch.setattr(update_tw_stock_daily, "validate_latest", lambda records: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_corporate_action_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_institutional_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(
        update_tw_stock_daily,
        "archive_margin_symbols",
        lambda symbols, start, end: (_ for _ in ()).throw(AssertionError("margin should not run")),
    )
    monkeypatch.setattr(update_tw_stock_daily, "archive_monthly_revenue_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_valuation_symbols", lambda symbols, start, end: [])

    report = update_tw_stock_daily.run_workflow(
        symbols=["2330"],
        start="2026-05-20",
        end="2026-05-22",
        margin=False,
    )

    assert report["margin_trading"]["count"] == 0
    assert report["margin_trading_archived_count"] == 0


def test_run_workflow_can_skip_monthly_revenue(monkeypatch):
    monkeypatch.setattr(update_tw_stock_daily, "archive_symbols", lambda symbols, start, end: [_record("2330")])
    monkeypatch.setattr(update_tw_stock_daily, "validate_latest", lambda records: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_corporate_action_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_institutional_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_margin_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(
        update_tw_stock_daily,
        "archive_monthly_revenue_symbols",
        lambda symbols, start, end: (_ for _ in ()).throw(AssertionError("monthly revenue should not run")),
    )
    monkeypatch.setattr(update_tw_stock_daily, "archive_valuation_symbols", lambda symbols, start, end: [])

    report = update_tw_stock_daily.run_workflow(
        symbols=["2330"],
        start="2026-05-20",
        end="2026-05-22",
        monthly_revenue=False,
    )

    assert report["monthly_revenue"]["count"] == 0
    assert report["monthly_revenue_archived_count"] == 0


def test_run_workflow_can_skip_valuation(monkeypatch):
    monkeypatch.setattr(update_tw_stock_daily, "archive_symbols", lambda symbols, start, end: [_record("2330")])
    monkeypatch.setattr(update_tw_stock_daily, "validate_latest", lambda records: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_corporate_action_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_institutional_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_margin_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_monthly_revenue_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(
        update_tw_stock_daily,
        "archive_valuation_symbols",
        lambda symbols, start, end: (_ for _ in ()).throw(AssertionError("valuation should not run")),
    )

    report = update_tw_stock_daily.run_workflow(
        symbols=["2330"],
        start="2026-05-20",
        end="2026-05-22",
        valuation=False,
    )

    assert report["valuation"]["count"] == 0
    assert report["valuation_archived_count"] == 0
