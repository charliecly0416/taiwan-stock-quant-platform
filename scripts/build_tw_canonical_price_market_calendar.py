#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PRICE_SOURCE_DIR = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
DEFAULT_FORMAL_TWII_SOURCE = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv"
DEFAULT_REPAIR_TWII_BRIDGE_SOURCE = (
    ROOT
    / "data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/twii_bridge.csv"
)
DEFAULT_CALENDAR_SOURCE = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
DEFAULT_INSTRUMENT_SOURCE = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt"

PRICE_REQUIRED_FIELDS = [
    "price_date",
    "instrument",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "adj_factor",
    "tradable_flag",
    "halt_flag",
    "halt_flag_source",
    "next_day_execution_availability",
    "next_day_execution_status",
    "price_source",
    "adjustment_policy",
]

TWII_REQUIRED_FIELDS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "return_1d",
    "ma_5",
    "ma_20",
    "ma_60",
    "market_trend_state",
    "source",
]

FORBIDDEN_ACTION_FLAGS = {
    "real_data_fetch_triggered": False,
    "provider_refresh_triggered": False,
    "provider_publish_triggered": False,
    "qlib_accepted_latest_switched": False,
    "readonly_latest_published": False,
    "agent_prompt_published": False,
    "model_training_triggered": False,
    "model_inference_triggered": False,
    "strategy_replay_triggered": False,
    "broker_order_quick_trade_triggered": False,
    "target_position_or_weight_generated": False,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_paths(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda p: rel(p)):
        digest.update(rel(path).encode("utf-8"))
        digest.update(str(path.stat().st_size).encode("utf-8"))
    return digest.hexdigest()


def read_calendar(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_instruments(path: Path) -> list[str]:
    instruments: list[str] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.reader(f, delimiter="\t"):
            if row:
                instruments.append(row[0].strip())
    return instruments


def non_empty(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def safe_float(value: Any) -> float | None:
    if not non_empty(value):
        return None
    try:
        return float(str(value))
    except ValueError:
        return None


def format_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.10g}"


def load_price_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def derive_tradable(row: dict[str, str]) -> str:
    numeric_fields = ["open", "high", "low", "close"]
    prices_ok = all((safe_float(row.get(field)) or 0) > 0 for field in numeric_fields)
    volume = safe_float(row.get("volume"))
    return "true" if prices_ok and volume is not None and volume > 0 else "false"


def derive_halt_flag(row: dict[str, str], tradable_flag: str) -> str:
    required_fields = ["open", "high", "low", "close", "volume"]
    missing_required = any(not non_empty(row.get(field)) for field in required_fields)
    return "false" if not missing_required and tradable_flag == "true" else "true"


def source_date_range(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "source_path": rel(path),
            "source_exists": False,
            "date_min": "",
            "date_max": "",
            "rows": 0,
            "status": "MISSING",
        }
    rows = load_price_rows(path)
    dates = sorted(row.get("date", "") for row in rows if row.get("date"))
    return {
        "source_path": rel(path),
        "source_exists": True,
        "date_min": dates[0] if dates else "",
        "date_max": dates[-1] if dates else "",
        "rows": len(rows),
        "status": "READY" if dates else "MISSING",
    }


def discover_twii_source(target_asof: str) -> tuple[Path, list[dict[str, Any]], bool]:
    candidates = [
        {
            "source_label": "formal_normalized_nonempty",
            "source_type": "local_csv",
            "source_path": DEFAULT_FORMAL_TWII_SOURCE,
            "lineage_note": "formal local normalized TWII source",
        },
        {
            "source_label": "rcpt15_r3_t_isolated_twii_bridge",
            "source_type": "local_csv_existing_isolated_bridge",
            "source_path": DEFAULT_REPAIR_TWII_BRIDGE_SOURCE,
            "lineage_note": "existing local bridge artifact from prior isolated TWII repair; no network is used by this DNG2_R run",
        },
    ]
    inventory: list[dict[str, Any]] = []
    for candidate in candidates:
        summary = source_date_range(candidate["source_path"])
        summary.update(
            {
                "source_label": candidate["source_label"],
                "source_type": candidate["source_type"],
                "lineage_note": candidate["lineage_note"],
                "fresh_enough_for_target_asof": bool(summary["date_max"] and summary["date_max"] >= target_asof),
            }
        )
        inventory.append(summary)

    available = [row for row in inventory if row["source_exists"] and row["date_max"]]
    if not available:
        return DEFAULT_FORMAL_TWII_SOURCE, inventory, True
    best = max(available, key=lambda row: (row["date_max"], row["rows"]))
    external_required = not bool(best["date_max"] and best["date_max"] >= target_asof)
    return ROOT / best["source_path"], inventory, external_required


def build_price_store(
    price_source_dir: Path,
    calendar: list[str],
    instruments: list[str],
    out_dir: Path,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    price_files = sorted(price_source_dir.glob("TW*.csv"))
    calendar_set = set(calendar)
    source_symbols = [p.stem for p in price_files]
    expected_symbols = instruments or source_symbols
    expected_symbol_set = set(expected_symbols)

    price_path = out_dir / "prices.csv"
    coverage_rows: list[dict[str, Any]] = []
    execution_rows: list[dict[str, Any]] = []
    halt_rows: list[dict[str, Any]] = []
    all_dates: set[str] = set()
    row_count = 0
    missing_required_source_fields: set[str] = set()
    field_non_empty = Counter()
    latest_complete_symbols = 0
    status = "READY"
    status_reasons: list[str] = []

    with price_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PRICE_REQUIRED_FIELDS)
        writer.writeheader()
        for source_path in price_files:
            instrument = source_path.stem
            source_rows = load_price_rows(source_path)
            dates = [row.get("date", "") for row in source_rows if row.get("date")]
            date_set = set(dates)
            all_dates.update(date_set)
            if calendar:
                missing_dates = sorted(calendar_set - date_set)
                extra_dates = sorted(date_set - calendar_set)
                expected_count = len(calendar)
            else:
                missing_dates = []
                extra_dates = []
                expected_count = len(date_set)

            if dates and dates[-1] == (calendar[-1] if calendar else dates[-1]):
                latest_complete_symbols += 1

            sorted_dates = sorted(date_set)
            available_execution_date_count = 0
            pending_execution_date_count = 0
            blocked_execution_date_count = 0
            halt_true_count = 0
            halt_false_count = 0
            for row in source_rows:
                for field in ["symbol", "date", "open", "high", "low", "close", "volume", "factor"]:
                    if field not in row:
                        missing_required_source_fields.add(field)
                date = row.get("date", "")
                next_idx = sorted_dates.index(date) + 1 if date in date_set else -1
                next_available = "true" if 0 <= next_idx < len(sorted_dates) else "false"
                next_status = "available" if next_available == "true" else "pending_next_trade_date"
                tradable_flag = derive_tradable(row)
                halt_flag = derive_halt_flag(row, tradable_flag)
                if halt_flag == "true":
                    halt_true_count += 1
                    if next_available == "false":
                        blocked_execution_date_count += 1
                else:
                    halt_false_count += 1
                    if next_available == "true":
                        available_execution_date_count += 1
                    else:
                        pending_execution_date_count += 1
                output = {
                    "price_date": date,
                    "instrument": instrument,
                    "open": row.get("open", ""),
                    "high": row.get("high", ""),
                    "low": row.get("low", ""),
                    "close": row.get("close", ""),
                    "volume": row.get("volume", ""),
                    "adj_factor": row.get("factor", ""),
                    "tradable_flag": tradable_flag,
                    "halt_flag": halt_flag,
                    "halt_flag_source": "derived_from_price_presence",
                    "next_day_execution_availability": next_available,
                    "next_day_execution_status": next_status,
                    "price_source": "yahoo_adjusted_primary.option_c_150_normalized",
                    "adjustment_policy": "source_adjusted_ohlcv_with_factor_column",
                }
                writer.writerow(output)
                row_count += 1
                for key, value in output.items():
                    if non_empty(value):
                        field_non_empty[key] += 1

            coverage_ratio = (len(date_set & calendar_set) / len(calendar_set)) if calendar_set else 1.0
            coverage_rows.append(
                {
                    "instrument": instrument,
                    "date_min": min(dates) if dates else "",
                    "date_max": max(dates) if dates else "",
                    "row_count": len(source_rows),
                    "expected_calendar_count": expected_count,
                    "calendar_covered_count": len(date_set & calendar_set) if calendar_set else len(date_set),
                    "coverage_ratio": f"{coverage_ratio:.6f}",
                    "missing_date_count": len(missing_dates),
                    "extra_date_count": len(extra_dates),
                    "missing_dates_sample": "|".join(missing_dates[:20]),
                    "extra_dates_sample": "|".join(extra_dates[:20]),
                    "status": "READY" if coverage_ratio == 1.0 else "PARTIAL_READY",
                }
            )
            execution_rows.append(
                {
                    "instrument": instrument,
                    "date_max": max(dates) if dates else "",
                    "has_next_day_execution_after_date_max": "false",
                    "last_row_next_day_execution_availability": "false",
                    "last_row_next_day_execution_status": "pending_next_trade_date" if source_rows else "missing_price_rows",
                    "available_execution_date_count": available_execution_date_count,
                    "pending_next_trade_date_count": pending_execution_date_count,
                    "blocked_execution_date_count": blocked_execution_date_count,
                    "historical_execution_ready": "true" if blocked_execution_date_count == 0 else "false",
                    "latest_next_day_execution_pending": "true" if source_rows else "false",
                    "policy": "historical rows require next local same-instrument row; latest asof without next row is pending_next_trade_date, not a whole-store failure",
                }
            )
            halt_rows.append(
                {
                    "instrument": instrument,
                    "date_min": min(dates) if dates else "",
                    "date_max": max(dates) if dates else "",
                    "row_count": len(source_rows),
                    "halt_true_count": halt_true_count,
                    "halt_false_count": halt_false_count,
                    "halt_flag_source": "derived_from_price_presence",
                    "policy": "halt_flag=true when required OHLCV or volume is missing; halt_flag=false only when OHLCV row exists and tradable_flag=true",
                    "status": "READY",
                }
            )

    missing_symbols = sorted(expected_symbol_set - set(source_symbols))
    extra_symbols = sorted(set(source_symbols) - expected_symbol_set)
    if missing_symbols:
        status = "BLOCKED_COVERAGE"
        status_reasons.append(f"missing expected instrument files: {len(missing_symbols)}")
    if missing_required_source_fields:
        status = "BLOCKED_SCHEMA"
        status_reasons.append("source missing fields: " + ",".join(sorted(missing_required_source_fields)))
    if any(row["status"] != "READY" for row in coverage_rows):
        status = "PARTIAL_READY" if status == "READY" else status
        status_reasons.append("one or more instruments do not fully cover provider calendar")
    if field_non_empty["halt_flag"] != row_count:
        status = "PARTIAL_READY" if status == "READY" else status
        status_reasons.append("halt_flag derivation coverage is incomplete")

    coverage_path = out_dir / "coverage_audit.csv"
    with coverage_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(coverage_rows[0].keys()) if coverage_rows else [])
        if coverage_rows:
            writer.writeheader()
            writer.writerows(coverage_rows)

    execution_path = out_dir / "execution_availability_audit.csv"
    with execution_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(execution_rows[0].keys()) if execution_rows else [])
        if execution_rows:
            writer.writeheader()
            writer.writerows(execution_rows)

    halt_path = out_dir / "halt_suspension_audit.json"
    halt_payload = {
        "halt_suspension_policy": "conservative_derived_from_price_presence",
        "halt_flag_source": "derived_from_price_presence",
        "authoritative_halt_suspension_source_available": False,
        "authoritative_halt_suspension_source_status_reason": (
            "No formal local halt/suspension source was found in DNG2_R scope; derived flags are conservative price-presence evidence."
        ),
        "derivation_rules": [
            "halt_flag=true when required OHLCV or volume is missing for an expected trading row",
            "halt_flag=false only when OHLCV row exists and tradable_flag=true",
        ],
        "audit_rows": halt_rows,
    }
    write_json(halt_path, halt_payload)

    adjustment_path = out_dir / "adjustment_audit.json"
    adjustment_payload = {
        "adjustment_policy": "source_adjusted_ohlcv_with_factor_column",
        "source_factor_field": "factor",
        "canonical_adj_factor_field": "adj_factor",
        "unadjusted_prices_available": False,
        "unadjusted_prices_status_reason": "Source files expose adjusted OHLCV plus factor; unadjusted OHLCV was not present and was not reconstructed.",
        "source_path": rel(price_source_dir),
        "halt_suspension_audit": rel(halt_path),
    }
    write_json(adjustment_path, adjustment_payload)

    schema_path = out_dir / "schema.json"
    schema_payload = {
        "schema_version": "v1.tw_canonical_price_store.dng2",
        "artifact_type": "price_store",
        "required_fields": PRICE_REQUIRED_FIELDS,
        "fields": {
            "price_date": {"type": "date", "source_field": "date", "required": True},
            "instrument": {"type": "string", "source_field": "symbol/file_stem", "required": True},
            "open": {"type": "float", "source_field": "open", "required": True},
            "high": {"type": "float", "source_field": "high", "required": True},
            "low": {"type": "float", "source_field": "low", "required": True},
            "close": {"type": "float", "source_field": "close", "required": True},
            "volume": {"type": "float", "source_field": "volume", "required": True},
            "adj_factor": {"type": "float", "source_field": "factor", "required": True},
            "tradable_flag": {"type": "boolean", "source_field": "derived_from_positive_ohlcv", "required": True},
            "halt_flag": {"type": "boolean", "source_field": "derived_from_price_presence", "required": True, "availability": "derived_conservative"},
            "halt_flag_source": {"type": "string", "source_field": "constant_derivation_policy", "required": True},
            "next_day_execution_availability": {"type": "boolean", "source_field": "derived_from_next_local_row", "required": True},
            "next_day_execution_status": {"type": "string", "source_field": "derived_from_next_local_row_or_latest_pending", "required": True},
            "price_source": {"type": "string", "source_field": "constant_local_source_id", "required": True},
            "adjustment_policy": {"type": "string", "source_field": "constant_policy", "required": True},
        },
        "forbidden_fields": [
            "future_return_*",
            "forward_return_*",
            "label_*",
            "strategy_action",
            "target_position",
            "target_weight",
            "order_qty",
            "broker_order_id",
            "portfolio_equity",
        ],
    }
    write_json(schema_path, schema_payload)

    date_min = min(all_dates) if all_dates else ""
    date_max = max(all_dates) if all_dates else ""
    if not status_reasons:
        status_reasons.append("price source files converted to canonical CSV")

    return {
        "artifact_type": "price_store",
        "price_store_id": "tw_equity_daily",
        "status": status,
        "status_reason": "; ".join(status_reasons),
        "date_min": date_min,
        "date_max": date_max,
        "asof": date_max,
        "symbol_count": len(source_symbols),
        "expected_symbol_count": len(expected_symbols),
        "missing_symbols": missing_symbols,
        "extra_symbols": extra_symbols,
        "row_count": row_count,
        "latest_complete_symbol_count": latest_complete_symbols,
        "paths": {
            "prices": rel(price_path),
            "schema": rel(schema_path),
            "coverage_audit": rel(coverage_path),
            "adjustment_audit": rel(adjustment_path),
            "execution_availability_audit": rel(execution_path),
            "halt_suspension_audit": rel(halt_path),
        },
        "field_coverage": {
            field: {
                "non_empty_count": field_non_empty[field],
                "row_count": row_count,
                "coverage_ratio": (field_non_empty[field] / row_count) if row_count else 0.0,
            }
            for field in PRICE_REQUIRED_FIELDS
        },
        "checksum": sha256_file(price_path),
        "source_checksum": sha256_paths(price_files),
    }


def trend_state(close: float | None, ma20: float | None, ma60: float | None) -> str:
    if close is None or ma20 is None or ma60 is None:
        return ""
    if close >= ma20 >= ma60:
        return "bullish"
    if close <= ma20 <= ma60:
        return "bearish"
    return "mixed"


def moving_average(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def build_twii_store(
    twii_source: Path,
    calendar: list[str],
    out_dir: Path,
    source_inventory: list[dict[str, Any]],
    external_source_repair_required: bool,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    with twii_source.open("r", encoding="utf-8", newline="") as f:
        source_rows = list(csv.DictReader(f))

    out_path = out_dir / "twii.csv"
    coverage_path = out_dir / "coverage_audit.csv"
    schema_path = out_dir / "schema.json"

    closes: list[float] = []
    prev_close: float | None = None
    field_non_empty = Counter()
    output_rows: list[dict[str, str]] = []
    for row in source_rows:
        close = safe_float(row.get("close"))
        close_values_for_ma = closes + ([close] if close is not None else [])
        ma5 = moving_average(close_values_for_ma, 5)
        ma20 = moving_average(close_values_for_ma, 20)
        ma60 = moving_average(close_values_for_ma, 60)
        ret = ((close / prev_close) - 1.0) if close is not None and prev_close not in (None, 0) else None
        output = {
            "date": row.get("date", ""),
            "open": row.get("open", ""),
            "high": row.get("high", ""),
            "low": row.get("low", ""),
            "close": row.get("close", ""),
            "volume": row.get("volume", ""),
            "return_1d": format_float(ret),
            "ma_5": format_float(ma5),
            "ma_20": format_float(ma20),
            "ma_60": format_float(ma60),
            "market_trend_state": trend_state(close, ma20, ma60),
            "source": "local_twii_bridge" if twii_source == DEFAULT_REPAIR_TWII_BRIDGE_SOURCE else "yahoo_adjusted_primary.normalized_nonempty.TWII",
        }
        output_rows.append(output)
        for key, value in output.items():
            if non_empty(value):
                field_non_empty[key] += 1
        if close is not None:
            closes.append(close)
            prev_close = close

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TWII_REQUIRED_FIELDS)
        writer.writeheader()
        writer.writerows(output_rows)

    date_set = {row["date"] for row in output_rows if row.get("date")}
    calendar_set = set(calendar)
    missing_dates = sorted(calendar_set - date_set)
    extra_dates = sorted(date_set - calendar_set)
    date_min = min(date_set) if date_set else ""
    date_max = max(date_set) if date_set else ""
    calendar_date_max = max(calendar_set) if calendar_set else ""
    coverage_ratio = (len(date_set & calendar_set) / len(calendar_set)) if calendar_set else 1.0
    if date_max == calendar_date_max and coverage_ratio == 1.0:
        status = "READY"
        status_reason = "TWII covers full provider calendar"
    elif date_max == calendar_date_max:
        status = "PARTIAL_READY_WITH_DECLARED_GAP"
        status_reason = (
            f"TWII covers target asof={calendar_date_max}; declared historical calendar gaps={len(missing_dates)}; "
            "no external source repair required for target asof"
        )
    else:
        status = "BLOCKED_COVERAGE"
        status_reason = (
            f"TWII date_max={date_max} does not cover calendar date_max={calendar_date_max}; "
            f"missing calendar dates={len(missing_dates)}; external source repair required"
        )

    inventory_path = out_dir / "twii_local_source_inventory.json"
    write_json(
        inventory_path,
        {
            "target_asof": calendar_date_max,
            "selected_source": rel(twii_source),
            "external_source_repair_required": external_source_repair_required,
            "external_source_repair_status": (
                "external source repair required"
                if external_source_repair_required
                else "not required; selected local source covers target asof"
            ),
            "inventory": source_inventory,
        },
    )

    coverage_rows = [
        {
            "dataset_id": "twii_daily",
            "date_min": date_min,
            "date_max": date_max,
            "row_count": len(output_rows),
            "expected_calendar_count": len(calendar_set),
            "calendar_covered_count": len(date_set & calendar_set),
            "coverage_ratio": f"{coverage_ratio:.6f}",
            "missing_date_count": len(missing_dates),
            "extra_date_count": len(extra_dates),
            "missing_dates_sample": "|".join(missing_dates[:40]),
            "extra_dates_sample": "|".join(extra_dates[:20]),
            "status": status,
        }
    ]
    with coverage_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(coverage_rows[0].keys()))
        writer.writeheader()
        writer.writerows(coverage_rows)

    schema_payload = {
        "schema_version": "v1.tw_canonical_market_feature_store.twii_daily.dng2",
        "artifact_type": "market_feature_store",
        "feature_set_id": "twii_daily",
        "required_fields": TWII_REQUIRED_FIELDS,
        "fields": {
            "date": {"type": "date", "source_field": "date", "required": True},
            "open": {"type": "float", "source_field": "open", "required": True},
            "high": {"type": "float", "source_field": "high", "required": True},
            "low": {"type": "float", "source_field": "low", "required": True},
            "close": {"type": "float", "source_field": "close", "required": True},
            "volume": {"type": "float", "source_field": "volume", "required": True},
            "return_1d": {"type": "float_or_empty", "source_field": "derived_from_close", "required": True},
            "ma_5": {"type": "float_or_empty", "source_field": "derived_from_close", "required": True},
            "ma_20": {"type": "float_or_empty", "source_field": "derived_from_close", "required": True},
            "ma_60": {"type": "float_or_empty", "source_field": "derived_from_close", "required": True},
            "market_trend_state": {"type": "string_or_empty", "source_field": "derived_from_close_ma20_ma60", "required": True},
            "source": {"type": "string", "source_field": "constant_local_source_id", "required": True},
        },
    }
    write_json(schema_path, schema_payload)

    return {
        "artifact_type": "market_feature_store",
        "feature_set_id": "twii_daily",
        "status": status,
        "status_reason": status_reason,
        "date_min": date_min,
        "date_max": date_max,
        "asof": date_max,
        "row_count": len(output_rows),
        "paths": {
            "twii": rel(out_path),
            "schema": rel(schema_path),
            "coverage_audit": rel(coverage_path),
            "twii_local_source_inventory": rel(inventory_path),
        },
        "field_coverage": {
            field: {
                "non_empty_count": field_non_empty[field],
                "row_count": len(output_rows),
                "coverage_ratio": (field_non_empty[field] / len(output_rows)) if output_rows else 0.0,
            }
            for field in TWII_REQUIRED_FIELDS
        },
        "missing_calendar_dates": missing_dates,
        "external_source_repair_required": external_source_repair_required,
        "source_inventory": source_inventory,
        "checksum": sha256_file(out_path),
        "source_checksum": sha256_file(twii_source),
    }


def build_lineage(
    out_path: Path,
    artifact_type: str,
    run_id: str,
    source_paths: list[Path],
    generated_at: str,
    extra_payload: dict[str, Any] | None = None,
) -> None:
    payload = {
        "artifact_type": artifact_type,
        "run_id": run_id,
        "generated_at": generated_at,
        "lineage_type": "local_canonicalization_no_fetch",
        "source_paths": [rel(path) for path in source_paths],
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
        "notes": [
            "DNG2 builder only read local files under data_tw/ and qlib_pipeline/data_tw/.",
            "No provider refresh, publish, accepted latest switch, model inference, replay, or trading action was invoked.",
        ],
    }
    if extra_payload:
        payload.update(extra_payload)
    write_json(out_path, payload)


def readiness_status(
    price_summary: dict[str, Any],
    twii_summary: dict[str, Any],
    calendar: list[str],
    calendar_source: Path,
) -> tuple[str, dict[str, bool], list[dict[str, Any]], str]:
    asof = max(calendar) if calendar else ""
    price_to_asof = price_summary["date_max"] == asof and price_summary["status"] in {"READY", "PARTIAL_READY"}
    twii_ready_for_dng3 = twii_summary["status"] in {"READY", "PARTIAL_READY_WITH_DECLARED_GAP"}
    calendar_ready = bool(calendar)
    mtm_ready = price_summary["field_coverage"]["close"]["coverage_ratio"] == 1.0
    latest_next_day_pending = price_to_asof
    gate_status = {
        "can_continue_to_model_score": price_to_asof and calendar_ready and mtm_ready,
        "can_continue_to_replay": price_to_asof and calendar_ready and twii_summary["status"] == "READY" and not latest_next_day_pending,
        "can_continue_to_shadow_execution": price_to_asof and calendar_ready and twii_summary["status"] == "READY" and not latest_next_day_pending,
        "can_continue_to_dng3": price_to_asof and calendar_ready and twii_ready_for_dng3,
    }
    rows = [
        {
            "route_id": "price_market_calendar",
            "asof": asof,
            "dependency_name": "price_coverage",
            "required_layer": "canonical_price_store",
            "required_dataset_id": "tw_equity_daily",
            "required_date_min": price_summary["date_min"],
            "required_date_max": asof,
            "required_symbols_scope": "option_c_150",
            "required_fields": PRICE_REQUIRED_FIELDS,
            "required_pit_policy": "point_in_time_by_price_date; no future return or label fields",
            "source_artifact": price_summary["paths"]["prices"],
            "catalog_status": price_summary["status"],
            "coverage_status": "READY" if price_summary["date_max"] == asof else "BLOCKED_COVERAGE",
            "schema_status": "READY",
            "pit_status": "READY",
            "latest_status": "not_published; canonical artifact only",
            "can_continue": price_summary["status"] in {"READY", "PARTIAL_READY"} and price_summary["date_max"] == asof,
            "applies_to_gates": ["model_score", "replay", "shadow_execution", "dng3"],
            "blocker_reason": "" if price_summary["date_max"] == asof else f"price date_max={price_summary['date_max']} < asof={asof}",
            "repair_recommendation": "" if price_summary["date_max"] == asof else "repair local normalized price source before downstream route",
        },
        {
            "route_id": "price_market_calendar",
            "asof": asof,
            "dependency_name": "twii_coverage",
            "required_layer": "canonical_market_feature_store",
            "required_dataset_id": "twii_daily",
            "required_date_min": twii_summary["date_min"],
            "required_date_max": asof,
            "required_symbols_scope": "TWII",
            "required_fields": TWII_REQUIRED_FIELDS,
            "required_pit_policy": "point_in_time_by_index_date; rolling features use current/past closes only",
            "source_artifact": twii_summary["paths"]["twii"],
            "catalog_status": twii_summary["status"],
            "coverage_status": twii_summary["status"],
            "schema_status": "READY",
            "pit_status": "READY",
            "latest_status": "not_published; canonical artifact only",
            "can_continue": twii_summary["status"] in {"READY", "PARTIAL_READY_WITH_DECLARED_GAP"},
            "applies_to_gates": ["replay", "shadow_execution", "dng3"],
            "blocker_reason": "" if twii_summary["status"] in {"READY", "PARTIAL_READY_WITH_DECLARED_GAP"} else twii_summary["status_reason"],
            "repair_recommendation": (
                ""
                if twii_summary["status"] in {"READY", "PARTIAL_READY_WITH_DECLARED_GAP"}
                else "repair local TWII normalized source to cover provider calendar/asof"
            ),
        },
        {
            "route_id": "price_market_calendar",
            "asof": asof,
            "dependency_name": "calendar_coverage",
            "required_layer": "provider_calendar_evidence",
            "required_dataset_id": "formal_option_c_provider_calendar",
            "required_date_min": min(calendar) if calendar else "",
            "required_date_max": asof,
            "required_symbols_scope": "market_calendar",
            "required_fields": ["date"],
            "required_pit_policy": "calendar evidence only; no accepted latest switch",
            "source_artifact": rel(calendar_source),
            "catalog_status": "PARTIAL_READY",
            "coverage_status": "READY" if calendar else "MISSING",
            "schema_status": "READY",
            "pit_status": "READY",
            "latest_status": "provider calendar evidence; not qlib accepted latest",
            "can_continue": bool(calendar),
            "applies_to_gates": ["model_score", "replay", "shadow_execution", "dng3"],
            "blocker_reason": "" if calendar else "calendar source missing or empty",
            "repair_recommendation": "" if calendar else "repair local provider calendar evidence",
        },
        {
            "route_id": "price_market_calendar",
            "asof": asof,
            "dependency_name": "next_day_execution_availability",
            "required_layer": "canonical_price_store",
            "required_dataset_id": "tw_equity_daily",
            "required_date_min": price_summary["date_min"],
            "required_date_max": asof,
            "required_symbols_scope": "option_c_150",
            "required_fields": ["next_day_execution_availability", "tradable_flag", "halt_flag"],
            "required_pit_policy": "historical rows derive from local same-instrument next row; latest asof without next row is pending_next_trade_date",
            "source_artifact": price_summary["paths"]["execution_availability_audit"],
            "catalog_status": price_summary["status"],
            "coverage_status": "PARTIAL_READY",
            "schema_status": "READY",
            "pit_status": "READY",
            "latest_status": "not_published; canonical artifact only",
            "can_continue": True,
            "can_continue_to_model_score": True,
            "can_continue_to_replay": False,
            "can_continue_to_shadow_execution": False,
            "can_continue_to_dng3": True,
            "applies_to_gates": ["replay", "shadow_execution"],
            "blocker_reason": "latest asof has pending_next_trade_date because no next local trading row exists; this blocks replay/shadow next-open semantics but not same-day model score or DNG3 base data normalization",
            "repair_recommendation": "rebuild after next local trading row is available before replay or real next-open shadow execution",
        },
        {
            "route_id": "price_market_calendar",
            "asof": asof,
            "dependency_name": "halt_suspension_evidence",
            "required_layer": "canonical_price_store",
            "required_dataset_id": "tw_equity_daily",
            "required_date_min": price_summary["date_min"],
            "required_date_max": asof,
            "required_symbols_scope": "option_c_150",
            "required_fields": ["halt_flag", "halt_flag_source"],
            "required_pit_policy": "derived only from same-row price presence and tradable flag; no future data",
            "source_artifact": price_summary["paths"]["halt_suspension_audit"],
            "catalog_status": "READY",
            "coverage_status": "READY" if price_summary["field_coverage"]["halt_flag"]["coverage_ratio"] == 1.0 else "PARTIAL_READY",
            "schema_status": "READY",
            "pit_status": "READY",
            "latest_status": "not_published; canonical artifact only",
            "can_continue": price_summary["field_coverage"]["halt_flag"]["coverage_ratio"] == 1.0,
            "applies_to_gates": ["model_score", "replay", "shadow_execution", "dng3"],
            "blocker_reason": "" if price_summary["field_coverage"]["halt_flag"]["coverage_ratio"] == 1.0 else "halt_flag derivation coverage incomplete",
            "repair_recommendation": "" if price_summary["field_coverage"]["halt_flag"]["coverage_ratio"] == 1.0 else "repair price presence coverage or authoritative halt source",
        },
        {
            "route_id": "price_market_calendar",
            "asof": asof,
            "dependency_name": "mark_to_market_close_coverage",
            "required_layer": "canonical_price_store",
            "required_dataset_id": "tw_equity_daily",
            "required_date_min": price_summary["date_min"],
            "required_date_max": asof,
            "required_symbols_scope": "option_c_150",
            "required_fields": ["close"],
            "required_pit_policy": "close is same-day mark-to-market only; no forward label fields",
            "source_artifact": price_summary["paths"]["prices"],
            "catalog_status": price_summary["status"],
            "coverage_status": "READY" if price_summary["field_coverage"]["close"]["coverage_ratio"] == 1.0 else "BLOCKED_COVERAGE",
            "schema_status": "READY",
            "pit_status": "READY",
            "latest_status": "not_published; canonical artifact only",
            "can_continue": price_summary["field_coverage"]["close"]["coverage_ratio"] == 1.0,
            "applies_to_gates": ["model_score", "replay", "shadow_execution", "dng3"],
            "blocker_reason": "" if price_summary["field_coverage"]["close"]["coverage_ratio"] == 1.0 else "close has missing values",
            "repair_recommendation": "" if price_summary["field_coverage"]["close"]["coverage_ratio"] == 1.0 else "repair normalized close coverage",
        },
        {
            "route_id": "price_market_calendar",
            "asof": asof,
            "dependency_name": "holiday_or_no_data_evidence",
            "required_layer": "provider_calendar_evidence",
            "required_dataset_id": "formal_option_c_provider_calendar",
            "required_date_min": min(calendar) if calendar else "",
            "required_date_max": asof,
            "required_symbols_scope": "market_calendar",
            "required_fields": ["date"],
            "required_pit_policy": "calendar gaps are non-trading/no-data evidence only",
            "source_artifact": rel(calendar_source),
            "catalog_status": "PARTIAL_READY",
            "coverage_status": "READY" if calendar else "MISSING",
            "schema_status": "READY",
            "pit_status": "READY",
            "latest_status": "not_published; canonical artifact only",
            "can_continue": bool(calendar),
            "applies_to_gates": ["model_score", "replay", "shadow_execution", "dng3"],
            "blocker_reason": "" if calendar else "calendar evidence unavailable",
            "repair_recommendation": "" if calendar else "repair local provider calendar evidence",
        },
    ]
    if all(gate_status.values()):
        return "READY", gate_status, rows, "all DNG2_R route gates are ready"
    if gate_status["can_continue_to_dng3"] or gate_status["can_continue_to_model_score"]:
        return "PARTIAL_READY", gate_status, rows, "DNG2_R base data can continue for selected routes; replay/shadow may remain blocked by latest next-day pending"
    if any(row["coverage_status"] == "BLOCKED_COVERAGE" or row["catalog_status"] == "BLOCKED_COVERAGE" for row in rows):
        return "BLOCKED_COVERAGE", gate_status, rows, "one or more DNG2_R coverage dependencies block DNG3"
    return "PARTIAL_READY", gate_status, rows, "one or more DNG2_R dependencies are partial"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DNG2 canonical PriceStore/TWII/calendar artifacts from local sources only.")
    parser.add_argument("--run-id", default="", help="Run id. Defaults to dng2_price_market_calendar_<asof>.")
    parser.add_argument("--asof", default="", help="Target asof. Defaults to max provider calendar date.")
    parser.add_argument("--price-source-dir", default=str(DEFAULT_PRICE_SOURCE_DIR))
    parser.add_argument("--twii-source", default="", help="Optional TWII source. Defaults to best local source discovered for target asof.")
    parser.add_argument("--calendar-source", default=str(DEFAULT_CALENDAR_SOURCE))
    parser.add_argument("--instrument-source", default=str(DEFAULT_INSTRUMENT_SOURCE))
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    generated_at = utc_now()
    price_source_dir = Path(args.price_source_dir)
    calendar_source = Path(args.calendar_source)
    instrument_source = Path(args.instrument_source)
    for path in [price_source_dir, calendar_source, instrument_source]:
        if not path.exists():
            raise FileNotFoundError(path)

    calendar = read_calendar(calendar_source)
    instruments = read_instruments(instrument_source)
    asof = args.asof or (max(calendar) if calendar else "")
    if not asof:
        raise ValueError("Unable to resolve asof from args or calendar.")
    if args.twii_source:
        twii_source = Path(args.twii_source)
        if not twii_source.exists():
            raise FileNotFoundError(twii_source)
        source_inventory = [source_date_range(twii_source) | {"source_label": "cli_override", "source_type": "local_csv"}]
        external_source_repair_required = not bool(source_inventory[0]["date_max"] and source_inventory[0]["date_max"] >= asof)
    else:
        twii_source, source_inventory, external_source_repair_required = discover_twii_source(asof)
        if not twii_source.exists():
            raise FileNotFoundError(twii_source)
    run_id = args.run_id or f"dng2_price_market_calendar_{asof.replace('-', '')}"

    price_out_dir = ROOT / "data_tw/canonical/price_store/tw_equity_daily" / run_id
    twii_out_dir = ROOT / "data_tw/canonical/market_feature_store/twii_daily" / run_id

    price_summary = build_price_store(price_source_dir, calendar, instruments, price_out_dir)
    twii_summary = build_twii_store(
        twii_source,
        calendar,
        twii_out_dir,
        source_inventory,
        external_source_repair_required,
    )

    build_lineage(
        price_out_dir / "lineage.json",
        "price_store",
        run_id,
        [price_source_dir, calendar_source, instrument_source],
        generated_at,
    )
    build_lineage(
        twii_out_dir / "lineage.json",
        "market_feature_store",
        run_id,
        [twii_source, calendar_source],
        generated_at,
        {
            "twii_local_source_inventory": source_inventory,
            "selected_twii_source": rel(twii_source),
            "external_source_repair_required": external_source_repair_required,
            "external_source_repair_status": (
                "external source repair required"
                if external_source_repair_required
                else "not required; selected local source covers target asof"
            ),
            "repair_notes": [
                "DNG2_R selected the freshest local TWII source available in the workspace.",
                "If selected source is rcpt15_r3_t isolated bridge, DNG2_R consumes it as an existing local artifact and does not repeat its historical network repair.",
            ],
        },
    )
    price_summary["paths"]["lineage"] = rel(price_out_dir / "lineage.json")
    twii_summary["paths"]["lineage"] = rel(twii_out_dir / "lineage.json")

    readiness_overall, gate_status, readiness_rows, readiness_reason = readiness_status(
        price_summary, twii_summary, calendar, calendar_source
    )
    readiness_dir = ROOT / "data_tw/catalog/readiness_matrix" / asof
    readiness_path = readiness_dir / "price_market_calendar.json"
    readiness_payload = {
        "route_id": "price_market_calendar",
        "asof": asof,
        "run_id": run_id,
        "generated_at": generated_at,
        "status": readiness_overall,
        "can_continue": all(gate_status.values()),
        "can_continue_to_model_score": gate_status["can_continue_to_model_score"],
        "can_continue_to_replay": gate_status["can_continue_to_replay"],
        "can_continue_to_shadow_execution": gate_status["can_continue_to_shadow_execution"],
        "can_continue_to_dng3": gate_status["can_continue_to_dng3"],
        "status_reason": readiness_reason,
        "dependencies": readiness_rows,
        "source_paths": {
            "price_source_dir": rel(price_source_dir),
            "twii_source": rel(twii_source),
            "calendar_source": rel(calendar_source),
            "instrument_source": rel(instrument_source),
        },
        "twii_local_source_inventory": source_inventory,
        "external_source_repair_required": external_source_repair_required,
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
    }
    write_json(readiness_path, readiness_payload)

    price_manifest = {
        "artifact_type": "price_store",
        "price_store_id": "tw_equity_daily",
        "run_id": run_id,
        "generated_at": generated_at,
        "asof": price_summary["asof"],
        "date_min": price_summary["date_min"],
        "date_max": price_summary["date_max"],
        "symbol_count": price_summary["symbol_count"],
        "row_count": price_summary["row_count"],
        "status": price_summary["status"],
        "status_reason": price_summary["status_reason"],
        "source_data_artifact": rel(price_source_dir),
        "source_calendar_artifact": rel(calendar_source),
        "source_instrument_artifact": rel(instrument_source),
        "adjustment_policy": "source_adjusted_ohlcv_with_factor_column",
        "execution_availability_audit": price_summary["paths"]["execution_availability_audit"],
        "halt_suspension_audit": price_summary["paths"]["halt_suspension_audit"],
        "coverage_audit": price_summary["paths"]["coverage_audit"],
        "schema_path": price_summary["paths"]["schema"],
        "lineage_path": price_summary["paths"]["lineage"],
        "prices_path": price_summary["paths"]["prices"],
        "checksum": price_summary["checksum"],
        "field_coverage": price_summary["field_coverage"],
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "readonly_only": True,
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
    }
    write_json(price_out_dir / "manifest.json", price_manifest)

    twii_manifest = {
        "artifact_type": "market_feature_store",
        "feature_set_id": "twii_daily",
        "run_id": run_id,
        "generated_at": generated_at,
        "asof": twii_summary["asof"],
        "date_min": twii_summary["date_min"],
        "date_max": twii_summary["date_max"],
        "row_count": twii_summary["row_count"],
        "status": twii_summary["status"],
        "status_reason": twii_summary["status_reason"],
        "source_data_artifact": rel(twii_source),
        "source_calendar_artifact": rel(calendar_source),
        "twii_local_source_inventory": twii_summary["paths"]["twii_local_source_inventory"],
        "external_source_repair_required": external_source_repair_required,
        "external_source_repair_status": (
            "external source repair required"
            if external_source_repair_required
            else "not required; selected local source covers target asof"
        ),
        "coverage_audit": twii_summary["paths"]["coverage_audit"],
        "schema_path": twii_summary["paths"]["schema"],
        "lineage_path": twii_summary["paths"]["lineage"],
        "twii_path": twii_summary["paths"]["twii"],
        "checksum": twii_summary["checksum"],
        "field_coverage": twii_summary["field_coverage"],
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "readonly_only": True,
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
    }
    write_json(twii_out_dir / "manifest.json", twii_manifest)

    summary = {
        "ok": True,
        "run_id": run_id,
        "asof": asof,
        "generated_at": generated_at,
        "price_store": price_summary,
        "twii": twii_summary,
        "readiness_matrix_path": rel(readiness_path),
        "readiness_status": readiness_overall,
        "can_continue": all(gate_status.values()),
        "can_continue_to_model_score": gate_status["can_continue_to_model_score"],
        "can_continue_to_replay": gate_status["can_continue_to_replay"],
        "can_continue_to_shadow_execution": gate_status["can_continue_to_shadow_execution"],
        "can_continue_to_dng3": gate_status["can_continue_to_dng3"],
        "external_source_repair_required": external_source_repair_required,
        "forbidden_action_flags": FORBIDDEN_ACTION_FLAGS,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"built run_id={run_id} asof={asof} readiness={readiness_overall} "
            f"dng3={gate_status['can_continue_to_dng3']} replay={gate_status['can_continue_to_replay']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
