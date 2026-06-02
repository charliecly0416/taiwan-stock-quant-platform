#!/usr/bin/env python3
"""Run the daily TWStock archive + official validation workflow.

This is the operational wrapper for Phase 2. It is dry-run by default. With
--apply it writes FinMind daily bars to qd_tw_stock_daily_bars and then updates
TWSE official validation fields for matching archived rows.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "update-tw-stock-daily")
os.environ.setdefault("ADMIN_USER", "update")
os.environ.setdefault("ADMIN_PASSWORD", "updatepass")

from scripts.archive_tw_stock_daily import (  # noqa: E402
    DailyBarRecord,
    fetch_finmind_rows,
    parse_finmind_rows,
    summarize as summarize_archive,
    upsert_records,
)
from scripts.archive_tw_stock_corporate_actions import (  # noqa: E402
    archive_symbols as archive_corporate_action_symbols,
    summarize as summarize_corporate_actions,
    upsert_records as upsert_corporate_actions,
)
from scripts.archive_tw_stock_institutional_trades import (  # noqa: E402
    archive_symbols as archive_institutional_symbols,
    summarize as summarize_institutional_trades,
    upsert_records as upsert_institutional_trades,
)
from scripts.archive_tw_stock_margin_trading import (  # noqa: E402
    archive_symbols as archive_margin_symbols,
    summarize as summarize_margin_trading,
    upsert_records as upsert_margin_trading,
)
from scripts.archive_tw_stock_monthly_revenue import (  # noqa: E402
    archive_symbols as archive_monthly_revenue_symbols,
    summarize as summarize_monthly_revenue,
    upsert_records as upsert_monthly_revenue,
)
from scripts.archive_tw_stock_valuation import (  # noqa: E402
    archive_symbols as archive_valuation_symbols,
    summarize as summarize_valuation,
    upsert_records as upsert_valuation,
)
from scripts.validate_tw_stock_daily import (  # noqa: E402
    compare_record_to_official,
    fetch_twse_rows,
    latest_records_by_symbol,
    summarize as summarize_validation,
    update_archive_validation,
)

DEFAULT_SYMBOLS = ("2330", "0050", "0056", "00878")


def parse_symbols(raw_symbols: Sequence[str]) -> List[str]:
    out: List[str] = []
    for raw in raw_symbols or []:
        for part in str(raw or "").replace("\n", ",").split(","):
            symbol = part.strip()
            if symbol and symbol not in out:
                out.append(symbol)
    return out


def load_symbols_from_file(path: str) -> List[str]:
    if not path:
        return []
    symbols = []
    for line in open(path, "r", encoding="utf-8"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        symbols.extend(parse_symbols([stripped]))
    return symbols


def archive_symbols(symbols: Sequence[str], start: str, end: str) -> List[DailyBarRecord]:
    records: List[DailyBarRecord] = []
    for symbol in symbols:
        rows = fetch_finmind_rows(symbol, start, end)
        records.extend(parse_finmind_rows(rows, symbol=symbol))
    return records


def validate_latest(records: Sequence[DailyBarRecord]) -> List[Any]:
    official_by_symbol = fetch_twse_rows()
    latest = latest_records_by_symbol(records)
    results = []
    for symbol in sorted(latest):
        results.append(compare_record_to_official(latest[symbol], official_by_symbol.get(symbol)))
    return results


def run_workflow(
    *,
    symbols: Sequence[str],
    start: str,
    end: str,
    apply: bool = False,
    validate: bool = True,
    corporate_actions: bool = True,
    institutional: bool = True,
    margin: bool = True,
    monthly_revenue: bool = True,
    valuation: bool = True,
) -> Dict[str, Any]:
    records = archive_symbols(symbols, start, end)
    archive_summary = summarize_archive(records)
    archived_count = upsert_records(records) if apply and records else 0

    validation_results = validate_latest(records) if validate and records else []
    validation_summary = summarize_validation(validation_results)
    updated_count = update_archive_validation(validation_results) if apply and validation_results else 0

    corporate_action_records = archive_corporate_action_symbols(symbols, start, end) if corporate_actions else []
    corporate_action_summary = summarize_corporate_actions(corporate_action_records)
    corporate_action_archived_count = upsert_corporate_actions(corporate_action_records) if apply and corporate_action_records else 0

    institutional_records = archive_institutional_symbols(symbols, start, end) if institutional else []
    institutional_summary = summarize_institutional_trades(institutional_records)
    institutional_archived_count = upsert_institutional_trades(institutional_records) if apply and institutional_records else 0

    margin_records = archive_margin_symbols(symbols, start, end) if margin else []
    margin_summary = summarize_margin_trading(margin_records)
    margin_archived_count = upsert_margin_trading(margin_records) if apply and margin_records else 0

    monthly_revenue_records = archive_monthly_revenue_symbols(symbols, start, end) if monthly_revenue else []
    monthly_revenue_summary = summarize_monthly_revenue(monthly_revenue_records)
    monthly_revenue_archived_count = upsert_monthly_revenue(monthly_revenue_records) if apply and monthly_revenue_records else 0

    valuation_records = archive_valuation_symbols(symbols, start, end) if valuation else []
    valuation_summary = summarize_valuation(valuation_records)
    valuation_archived_count = upsert_valuation(valuation_records) if apply and valuation_records else 0

    return {
        "symbols": list(symbols),
        "start": start,
        "end": end,
        "apply": bool(apply),
        "archive": archive_summary,
        "archived_count": archived_count,
        "validation": validation_summary,
        "validation_updated_count": updated_count,
        "corporate_actions": corporate_action_summary,
        "corporate_actions_archived_count": corporate_action_archived_count,
        "institutional_trades": institutional_summary,
        "institutional_trades_archived_count": institutional_archived_count,
        "margin_trading": margin_summary,
        "margin_trading_archived_count": margin_archived_count,
        "monthly_revenue": monthly_revenue_summary,
        "monthly_revenue_archived_count": monthly_revenue_archived_count,
        "valuation": valuation_summary,
        "valuation_archived_count": valuation_archived_count,
    }


def _default_start() -> str:
    return (date.today() - timedelta(days=10)).isoformat()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Daily TWStock archive + TWSE validation workflow.")
    parser.add_argument("--symbol", action="append", default=[], help="Taiwan stock code or comma-separated codes. Can be repeated.")
    parser.add_argument("--symbols-file", default="", help="Optional text file with one or comma-separated symbols per line.")
    parser.add_argument("--start", default=_default_start(), help="Start date YYYY-MM-DD. Default: today-10d.")
    parser.add_argument("--end", default=date.today().isoformat(), help="End date YYYY-MM-DD. Default: today.")
    parser.add_argument("--apply", action="store_true", help="Write archive and validation results to PostgreSQL.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write DB. This is the default unless --apply is set.")
    parser.add_argument("--no-validate", action="store_true", help="Skip TWSE official validation step.")
    parser.add_argument("--no-corporate-actions", action="store_true", help="Skip FinMind dividend/ex-right archive step.")
    parser.add_argument("--no-institutional", action="store_true", help="Skip FinMind institutional buy/sell archive step.")
    parser.add_argument("--no-margin", action="store_true", help="Skip FinMind margin purchase/short sale archive step.")
    parser.add_argument("--no-monthly-revenue", action="store_true", help="Skip FinMind monthly revenue archive step.")
    parser.add_argument("--no-valuation", action="store_true", help="Skip FinMind valuation archive step.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    symbols = parse_symbols(args.symbol)
    symbols.extend(s for s in load_symbols_from_file(args.symbols_file) if s not in symbols)
    if not symbols:
        symbols = list(DEFAULT_SYMBOLS)
    apply_changes = bool(args.apply and not args.dry_run)
    report = run_workflow(
        symbols=symbols,
        start=args.start,
        end=args.end,
        apply=apply_changes,
        validate=not args.no_validate,
        corporate_actions=not args.no_corporate_actions,
        institutional=not args.no_institutional,
        margin=not args.no_margin,
        monthly_revenue=not args.no_monthly_revenue,
        valuation=not args.no_valuation,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    archive_count = int((report.get("archive") or {}).get("count") or 0)
    validation = report.get("validation") or {}
    mismatched = int(validation.get("mismatched") or 0)
    unchecked = int(validation.get("unchecked") or 0)
    if archive_count <= 0:
        return 2
    if not args.no_validate and (mismatched > 0 or unchecked > 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
