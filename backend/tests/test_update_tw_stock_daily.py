"""Offline tests for the daily TWStock archive + validation workflow."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

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


def test_twii_schema_validator_rejects_ambiguous_rows_and_accepts_schema_only():
    assert update_tw_stock_daily.validate_twii_response_rows([], target_asof="2026-08-27")["ok"] is False
    assert update_tw_stock_daily.validate_twii_response_rows([{"日期": "2026-08-27"}], target_asof="2026-08-27")["ok"] is False
    valid = {"日期": "2026-08-27", "收盤指數": "22000", "指數名稱": "發行量加權股價指數"}
    result = update_tw_stock_daily.validate_twii_response_rows([valid], target_asof="2026-08-27")
    assert result["ok"] is True
    assert "returned_scope" not in result
    assert "unknown_scope" not in result
    assert update_tw_stock_daily.validate_twii_response_rows([valid], target_asof="2026-08-26")["ok"] is False


def test_twii_schema_validator_normalizes_twse_roc_date():
    valid = {"日期": "1150828", "收盤指數": "22000", "指數名稱": "發行量加權股價指數"}
    assert update_tw_stock_daily.validate_twii_response_rows(valid and [valid], target_asof="2026-08-28")["ok"] is True
    assert update_tw_stock_daily.validate_twii_response_rows([valid], target_asof="2026-08-31")["errors"] == ["target_date_mismatch"]


def test_twii_schema_validator_excludes_total_return_index_from_twii_identity():
    rows = [
        {"日期": "1150831", "收盤指數": "22000", "指數": "發行量加權股價指數"},
        {"日期": "1150831", "收盤指數": "23000", "指數": "發行量加權股價報酬指數"},
    ]
    assert update_tw_stock_daily.validate_twii_response_rows(rows, target_asof="2026-08-31")["ok"] is True


def test_twii_schema_failure_uses_same_run_yahoo_fallback_and_preserves_twse_evidence(tmp_path, monkeypatch):
    class FakeResponse:
        status_code = 200
        content = json.dumps([{"日期": "1150916", "收盤指數": "22000", "指數名稱": "發行量加權股價指數"}]).encode()
        headers = {"Date": "Thu, 17 Sep 2026 10:33:41 GMT"}

        def raise_for_status(self):
            return None

        def json(self):
            return json.loads(self.content)

    monkeypatch.setitem(sys.modules, "requests", SimpleNamespace(get=lambda *args, **kwargs: FakeResponse()))

    def fake_run(command, *, cwd, env, text, capture_output, timeout, check):
        output = Path(command[command.index("--output") + 1])
        output.mkdir(parents=True)
        (output / "twii_daily_raw.json").write_text("{}", encoding="utf-8")
        (output / "twii_intraday_1m_raw.json").write_text("{}", encoding="utf-8")
        (output / "TWII_NORMALIZED.csv").write_text(
            "date,open,high,low,close,volume,vwap,factor,source\n"
            "2026-09-16,1,1,1,1,1,1,1,yahoo\n"
            "2026-09-17,2,2,2,2,2,2,1,yahoo\n",
            encoding="utf-8",
        )
        (output / "TWII_CAPTURE_MANIFEST.json").write_text(json.dumps({
            "schema_version": "modelb.test.yahoo.v1",
            "target_asof": "2026-09-17",
            "acquisition_run_id": "daily_tw_stock_auto_update_20260917_20260917T103002Z",
            "endpoint": "https://query1.finance.yahoo.com/v8/finance/chart/%5ETWII",
            "requests": {"daily": {}, "intraday": {}},
            "server_date_utc": {},
            "fetched_at": "2026-09-17T10:35:00+00:00",
            "available_at": "2026-09-17T10:35:00+00:00",
            "pit_status": "PASS",
            "validator_status": "PASS_CANDIDATE_AWAITING_INDEPENDENT_REVIEW",
        }), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(update_tw_stock_daily.subprocess, "run", fake_run)
    run_id = "daily_tw_stock_auto_update_20260917_20260917T103002Z"
    capture = update_tw_stock_daily._real_hsa8_twii_capture(
        start="2026-09-16", end="2026-09-17", output_dir=str(tmp_path), acquisition_run_id=run_id,
    )

    assert capture["provider"] == "Yahoo Finance"
    assert capture["acquisition_run_id"] == run_id
    assert capture["target_asof"] == "2026-09-17"
    assert capture["validator_status"] == "PASS_CANDIDATE_AWAITING_INDEPENDENT_REVIEW"
    assert capture["fallback"]["status"] == "PASS_CANDIDATE"
    assert Path(capture["fallback"]["rejected_twse_adapter"]).is_file()
    assert json.loads((tmp_path / "twii.twse_failure.adapter_output.json").read_text())["validator_status"] == "BLOCKED_PROVIDER_SCHEMA"
    assert all(Path(item).is_file() for item in capture["raw_paths"] + capture["normalized_paths"])


def test_finmind_hsa8_capture_derives_only_explicit_target_date_scope():
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert '"validator_status": "PASS" if records' not in source
    assert 'str(record.trade_date) == end' in source
    assert '"returned_scope": returned_scope' in source
    assert '"unknown_scope": unknown_scope' in source
    assert '"validator_status": "PASS" if scope_complete else "BLOCKED_SOURCE_SCOPE_OR_VALIDATOR_UNPROVEN"' in source


def test_finmind_hsa8_capture_binds_real_run_id_across_raw_normalized_and_adapter(tmp_path, monkeypatch):
    run_id = "daily_tw_stock_auto_update_20260827_20260827T163001Z"

    class FakeResponse:
        status_code = 200
        content = b'{"status":200,"data":[]}'
        headers = {}

        def raise_for_status(self):
            return None

        def json(self):
            return {"status": 200, "data": []}

    monkeypatch.setitem(sys.modules, "requests", SimpleNamespace(get=lambda *args, **kwargs: FakeResponse()))
    monkeypatch.setattr(update_tw_stock_daily, "parse_finmind_rows", lambda rows, symbol: [])

    _records, capture = update_tw_stock_daily._real_hsa8_finmind_capture(
        segment="daily_price",
        symbols=["2330"],
        start="2026-08-27",
        end="2026-08-27",
        output_dir=str(tmp_path),
        acquisition_run_id=run_id,
    )
    assert capture["source_family"] == "adjusted_price"

    adapter = json.loads((tmp_path / "daily_price.adapter_output.json").read_text(encoding="utf-8"))
    assert capture["acquisition_run_id"] == run_id
    assert adapter["acquisition_run_id"] == run_id
    assert capture["raw_paths"] == [str(tmp_path / "daily_price.2330.http.raw")]
    assert capture["normalized_paths"] == [str(tmp_path / "daily_price.normalized.json")]
    assert adapter["raw_files"][0]["path"] == capture["raw_paths"][0]
    assert adapter["normalized_files"][0]["path"] == capture["normalized_paths"][0]
    assert adapter["raw_files"][0]["sha256"] == update_tw_stock_daily._file_sha256(Path(adapter["raw_files"][0]["path"]))
    assert adapter["normalized_files"][0]["sha256"] == update_tw_stock_daily._file_sha256(Path(adapter["normalized_files"][0]["path"]))


def test_orthogonal_segment_does_not_repeat_twii_capture(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        update_tw_stock_daily,
        "_real_hsa8_finmind_capture",
        lambda **kwargs: ([], {"status": "captured", "source_family": kwargs["segment"]}),
    )
    monkeypatch.setattr(
        update_tw_stock_daily,
        "_real_hsa8_twii_capture",
        lambda **kwargs: calls.append(kwargs) or {"status": "captured"},
    )

    report = update_tw_stock_daily.run_workflow(
        symbols=["2330"],
        start="2026-09-01",
        end="2026-09-01",
        daily_price=False,
        corporate_actions=False,
        institutional=True,
        margin=False,
        monthly_revenue=False,
        valuation=False,
        handoff_output_dir=str(tmp_path),
    )

    assert calls == []
    assert report["hsa8_capture"]["twii"] == {"status": "not_requested"}


def test_finmind_get_retries_rate_limit_with_bounded_backoff(monkeypatch):
    class FakeResponse:
        def __init__(self, status_code):
            self.status_code = status_code
            self.content = b"{}"

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    responses = iter([FakeResponse(402), FakeResponse(200)])
    calls = []
    sleeps = []
    fake_requests = SimpleNamespace(get=lambda *args, **kwargs: (calls.append(kwargs) or next(responses)))
    monkeypatch.setenv("FINMIND_MIN_REQUEST_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("FINMIND_TRANSIENT_RETRIES", "1")
    monkeypatch.setenv("FINMIND_RETRY_BACKOFF_SECONDS", "0")
    monkeypatch.setattr(update_tw_stock_daily.time, "sleep", lambda seconds: sleeps.append(seconds))

    response, _last_request_at, request_count = update_tw_stock_daily._finmind_get(
        fake_requests,
        {"dataset": "test"},
        last_request_at=0.0,
    )

    assert response.status_code == 200
    assert request_count == 2
    assert len(calls) == 2


def test_hsa8_capture_writer_rejects_symlink_and_existing_destination(tmp_path):
    parent = tmp_path / "capture"
    parent.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    link = parent / "link"
    link.symlink_to(outside)
    with pytest.raises(OSError):
        update_tw_stock_daily._atomic_bytes(link, b"no")
    final = parent / "final"
    final.write_bytes(b"original")
    with pytest.raises(FileExistsError):
        update_tw_stock_daily._atomic_bytes(final, b"replace")
    assert final.read_bytes() == b"original"


def test_hsa8_capture_writer_rejects_parent_locator_race(tmp_path, monkeypatch):
    parent = tmp_path / "capture"
    parent.mkdir()
    real_lstat = os.lstat
    calls = {"parent": 0}

    def racing_lstat(path):
        info = real_lstat(path)
        if Path(path) == parent:
            calls["parent"] += 1
            if calls["parent"] >= 2:
                from types import SimpleNamespace
                return SimpleNamespace(st_mode=info.st_mode, st_dev=info.st_dev, st_ino=info.st_ino + 1)
        return info

    monkeypatch.setattr(update_tw_stock_daily.os, "lstat", racing_lstat)
    with pytest.raises(OSError, match="parent locator"):
        update_tw_stock_daily._atomic_bytes(parent / "artifact", b"race")


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


def test_run_workflow_can_skip_daily_price_and_run_institutional_only(monkeypatch):
    monkeypatch.setattr(
        update_tw_stock_daily,
        "archive_symbols",
        lambda symbols, start, end: (_ for _ in ()).throw(AssertionError("daily price should not run")),
    )
    monkeypatch.setattr(update_tw_stock_daily, "validate_latest", lambda records: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_corporate_action_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_institutional_symbols", lambda symbols, start, end: [object(), object()])
    monkeypatch.setattr(update_tw_stock_daily, "summarize_institutional_trades", lambda records: {"count": len(records)})
    monkeypatch.setattr(update_tw_stock_daily, "archive_margin_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_monthly_revenue_symbols", lambda symbols, start, end: [])
    monkeypatch.setattr(update_tw_stock_daily, "archive_valuation_symbols", lambda symbols, start, end: [])

    report = update_tw_stock_daily.run_workflow(
        symbols=["2330"],
        start="2026-05-20",
        end="2026-05-22",
        daily_price=False,
        corporate_actions=False,
        margin=False,
        monthly_revenue=False,
        valuation=False,
    )

    assert report["archive"]["count"] == 0
    assert report["institutional_trades"]["count"] == 2


def test_main_success_when_daily_price_skipped_but_institutional_has_rows(monkeypatch):
    def fake_workflow(**kwargs):
        assert kwargs["daily_price"] is False
        assert kwargs["institutional"] is True
        return {
            "archive": {"count": 0},
            "validation": {"mismatched": 0, "unchecked": 0},
            "corporate_actions": {"count": 0},
            "institutional_trades": {"count": 2},
            "margin_trading": {"count": 0},
            "monthly_revenue": {"count": 0},
            "valuation": {"count": 0},
        }

    monkeypatch.setattr(update_tw_stock_daily, "run_workflow", fake_workflow)

    assert update_tw_stock_daily.main([
        "--symbol",
        "2330",
        "--no-daily-price",
        "--no-corporate-actions",
        "--no-margin",
        "--no-monthly-revenue",
        "--no-valuation",
        "--no-validate",
    ]) == 0


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


def test_archive_daily_fetch_uses_tw_stock_data_source_http_get(monkeypatch):
    from scripts import archive_tw_stock_daily

    calls = []
    original_normalize_symbol = archive_tw_stock_daily.TWStockDataSource.normalize_symbol

    class FakeSource:
        def __init__(self, base_url):
            calls.append(("init", base_url))

        @staticmethod
        def normalize_symbol(symbol):
            return original_normalize_symbol(symbol)

        def _http_get(self, params):
            calls.append(("http", params))
            return {"status": 200, "data": [{"date": "2026-05-22", "stock_id": "2330", "open": 1, "max": 2, "min": 1, "close": 2, "Trading_Volume": 10}]}

    monkeypatch.setattr(archive_tw_stock_daily, "TWStockDataSource", FakeSource)
    monkeypatch.setenv("FINMIND_TOKEN", "test_token")

    rows = archive_tw_stock_daily.fetch_finmind_rows("2330", "2026-05-20", "2026-05-22", base_url="https://example.test")

    assert rows[0]["stock_id"] == "2330"
    assert calls[0] == ("init", "https://example.test")
    assert calls[1][0] == "http"
    assert calls[1][1]["data_id"] == "2330"
    assert calls[1][1]["token"] == "test_token"
