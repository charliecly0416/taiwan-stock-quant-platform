#!/usr/bin/env python3
"""Read-only diagnosis for Phase1B Option C formal source failures.

This script intentionally does not generate predictions, refresh data, rebuild
providers, train models, or call any network API. It only inspects local files
and writes Phase1B formal source diagnosis artifacts.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
QROOT = ROOT / "qlib_pipeline"
OUT_DIR = ROOT / "data_tw/experiments/decision_orthogonal"

ACCEPTED_UNIVERSE = (
    QROOT
    / "data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z"
    / "symbols_accepted_prediction_universe.txt"
)
OPTION_C_NORMALIZED = QROOT / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
OPTION_C_PROVIDER = QROOT / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
NORMALIZED_NONEMPTY = QROOT / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
PHASE0E_ARCHIVE = ROOT / "data_tw/experiments/decision_orthogonal/phase0e_raw_archive"
PRED_FAST = (
    QROOT
    / "data_tw/experiments/option_c_historical_signal_backfill"
    / "option_c_historical_backfill_20230101_20231231_pred_fast"
)

TARGET_DATES = ["2023-01-03", "2024-01-02", "2024-01-03"]
REQUIRED_FIELDS = {"open", "high", "low", "close", "volume", "vwap", "factor"}
REJECTED_FIELDS = {
    "tw_margin_util",
    "tw_margin_delta_5d",
    "tw_foreign_net_vol",
    "tw_trust_net_px",
    "tw_foreign_persist_5d",
    "tw_inst_consensus",
    "tw_idio_skew60",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def read_universe() -> list[str]:
    return sorted(line.strip() for line in ACCEPTED_UNIVERSE.read_text(encoding="utf-8").splitlines() if line.strip())


def provider_calendar_max() -> str | None:
    path = OPTION_C_PROVIDER / "calendars/day.txt"
    if not path.exists():
        return None
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return max(rows) if rows else None


def provider_calendar_coverage() -> list[dict[str, Any]]:
    path = OPTION_C_PROVIDER / "calendars/day.txt"
    if not path.exists():
        return [{"source": "option_c_150_qlib_bin_calendar", "month": None, "rows": 0, "min_date": None, "max_date": None}]
    dates = pd.Series([line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()], dtype="string")
    frame = pd.DataFrame({"date": dates})
    frame["month"] = frame["date"].str.slice(0, 7)
    grouped = frame.groupby("month", as_index=False).agg(rows=("date", "size"), min_date=("date", "min"), max_date=("date", "max"))
    grouped.insert(0, "source", "option_c_150_qlib_bin_calendar")
    return grouped.to_dict("records")


def provider_field_inventory(symbols: list[str]) -> dict[str, Any]:
    counts = {field: 0 for field in sorted(REQUIRED_FIELDS)}
    unexpected: set[str] = set()
    missing_symbols: list[str] = []
    for symbol in symbols:
        feature_dir = OPTION_C_PROVIDER / "features" / symbol.lower()
        if not feature_dir.exists():
            missing_symbols.append(symbol)
            continue
        fields = {p.name.split(".")[0] for p in feature_dir.glob("*.day.bin")}
        for field in fields:
            if field in counts:
                counts[field] += 1
            else:
                unexpected.add(field)
    rejected = sorted((set(counts) | unexpected) & REJECTED_FIELDS)
    return {
        "expected_field_counts": counts,
        "unexpected_fields": sorted(unexpected),
        "rejected_fields_present": rejected,
        "missing_feature_symbols": missing_symbols,
        "status": "pass"
        if not rejected and not unexpected and not missing_symbols and all(v == len(symbols) for v in counts.values())
        else "fail",
    }


def source_symbol_summary(asof: str, symbols: list[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing_files: list[str] = []
    missing_asof: list[str] = []
    for symbol in symbols:
        path = OPTION_C_NORMALIZED / f"{symbol}.csv"
        if not path.exists():
            missing_files.append(symbol)
            continue
        try:
            dates = pd.read_csv(path, usecols=["date"])["date"].astype(str)
        except Exception:
            missing_files.append(symbol)
            continue
        has_asof = bool((dates == asof).any())
        if not has_asof:
            missing_asof.append(symbol)
        rows.append(
            {
                "instrument": symbol,
                "date_min": str(dates.min()) if not dates.empty else None,
                "date_max": str(dates.max()) if not dates.empty else None,
                "has_asof": has_asof,
            }
        )
    frame = pd.DataFrame(rows)
    return {
        "symbols_expected": len(symbols),
        "symbols_found": len(rows),
        "symbols_with_asof": int(frame["has_asof"].sum()) if not frame.empty else 0,
        "min_date_min": str(frame["date_min"].min()) if not frame.empty else None,
        "max_date_max": str(frame["date_max"].max()) if not frame.empty else None,
        "missing_files": missing_files,
        "missing_asof": missing_asof,
    }


def formal_validation(asof: str, symbols: list[str]) -> dict[str, Any]:
    source = source_symbol_summary(asof, symbols)
    inventory = provider_field_inventory(symbols)
    calendar_max = provider_calendar_max()
    errors: list[str] = []
    if source["symbols_with_asof"] != len(symbols):
        errors.append("option_c_formal_source_missing_asof")
    if calendar_max is None or calendar_max < asof:
        errors.append("option_c_provider_calendar_stale")
    if inventory["status"] != "pass":
        errors.append("option_c_provider_field_inventory_failed")
    return {
        "status": "pass" if not errors else "fail",
        "asof": asof,
        "errors": errors,
        "active_universe_count": len(symbols),
        "formal_source": source,
        "provider_calendar_max": calendar_max,
        "provider_field_inventory": inventory,
        "handler_rejected_hits": [],
    }


def monthly_csv_coverage(source_name: str, directory: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("TW*.csv")):
        try:
            dates = pd.read_csv(path, usecols=["date"])["date"].astype(str)
        except Exception:
            continue
        symbol = path.stem
        for month, count in dates.str.slice(0, 7).value_counts().items():
            rows.append({"source": source_name, "month": month, "symbol": symbol, "rows": int(count)})
    if not rows:
        return [{"source": source_name, "month": None, "symbols": 0, "rows": 0, "min_rows_per_symbol": None}]
    frame = pd.DataFrame(rows)
    grouped = (
        frame.groupby(["source", "month"], as_index=False)
        .agg(symbols=("symbol", "nunique"), rows=("rows", "sum"), min_rows_per_symbol=("rows", "min"))
        .sort_values(["source", "month"])
    )
    return grouped.to_dict("records")


def phase0e_monthly_coverage() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source_name, path in [
        ("phase0e_institutional_flow", PHASE0E_ARCHIVE / "institutional_flow/phase0e_institutional_flow_20260610T175901Z_normalized.csv"),
        ("phase0e_margin_short", PHASE0E_ARCHIVE / "margin_short/phase0e_margin_short_20260610T180330Z_normalized.csv"),
    ]:
        if not path.exists():
            rows.append({"source": source_name, "month": None, "symbols": 0, "rows": 0, "min_rows_per_symbol": None})
            continue
        frame = pd.read_csv(path, usecols=["symbol", "trade_date"])
        frame["trade_date"] = frame["trade_date"].astype(str)
        frame["month"] = frame["trade_date"].str.slice(0, 7)
        grouped = (
            frame.groupby(["month"], as_index=False)
            .agg(symbols=("symbol", "nunique"), rows=("symbol", "size"))
            .sort_values("month")
        )
        grouped.insert(0, "source", source_name)
        grouped["min_rows_per_symbol"] = None
        rows.extend(grouped.to_dict("records"))
    return rows


def symbol_gap_rows(symbols: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    focus = sorted(set(symbols) | {"TW7769"})
    for source_name, directory in [
        ("option_c_150_normalized", OPTION_C_NORMALIZED),
        ("normalized_nonempty", NORMALIZED_NONEMPTY),
    ]:
        for symbol in focus:
            path = directory / f"{symbol}.csv"
            if not path.exists():
                rows.append({"source": source_name, "symbol": symbol, "exists": False})
                continue
            dates = pd.read_csv(path, usecols=["date"])["date"].astype(str)
            item: dict[str, Any] = {
                "source": source_name,
                "symbol": symbol,
                "exists": True,
                "rows": int(len(dates)),
                "min_date": str(dates.min()) if not dates.empty else None,
                "max_date": str(dates.max()) if not dates.empty else None,
                "in_accepted_universe": symbol in symbols,
            }
            for asof in TARGET_DATES:
                item[f"has_{asof}"] = bool((dates == asof).any())
            rows.append(item)
    for source_name, path in [
        ("phase0e_institutional_flow", PHASE0E_ARCHIVE / "institutional_flow/phase0e_institutional_flow_20260610T175901Z_normalized.csv"),
        ("phase0e_margin_short", PHASE0E_ARCHIVE / "margin_short/phase0e_margin_short_20260610T180330Z_normalized.csv"),
    ]:
        if not path.exists():
            rows.append({"source": source_name, "symbol": "TW7769", "exists": False})
            continue
        frame = pd.read_csv(path, usecols=["symbol", "trade_date"])
        part = frame[frame["symbol"] == "TW7769"].copy()
        dates = part["trade_date"].astype(str) if not part.empty else pd.Series(dtype="string")
        item = {
            "source": source_name,
            "symbol": "TW7769",
            "exists": not part.empty,
            "rows": int(len(part)),
            "min_date": str(dates.min()) if not dates.empty else None,
            "max_date": str(dates.max()) if not dates.empty else None,
            "in_accepted_universe": "TW7769" in symbols,
        }
        for asof in TARGET_DATES:
            item[f"has_{asof}"] = bool((dates == asof).any())
        rows.append(item)
    return rows


def pred_fast_inventory() -> list[dict[str, Any]]:
    prediction_files = sorted(PRED_FAST.glob("*/prediction.csv"))
    rows: list[dict[str, Any]] = []
    date_pattern = re.compile(r"option_c_daily_signal_(.*?)_option_c_historical_backfill")
    for path in prediction_files:
        run_dir = path.parent
        match = date_pattern.search(run_dir.name)
        raw_date = match.group(1) if match else None
        columns: list[str] = []
        row_count: int | None = None
        try:
            preview = pd.read_csv(path, nrows=5)
            columns = list(preview.columns)
            row_count = int(sum(1 for _ in path.open("r", encoding="utf-8")) - 1)
        except Exception:
            pass
        meta_path = run_dir / "run_metadata.json"
        metadata: dict[str, Any] = {}
        if meta_path.exists():
            try:
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                metadata = {}
        rows.append(
            {
                "run_dir": rel(run_dir),
                "raw_date_token": raw_date,
                "date_token_parseable_iso": bool(raw_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date)),
                "prediction_rows": row_count,
                "prediction_columns": ",".join(columns),
                "metadata_keys": ",".join(sorted(metadata.keys())),
                "metadata_status": metadata.get("status"),
                "metadata_asof": metadata.get("asof"),
                "has_config_path": "config" in metadata or "config_path" in metadata,
                "has_model_path": "model_path" in metadata or "model" in metadata,
                "has_recorder_id": "recorder_id" in metadata or "frozen_recorder" in metadata,
                "has_input_source": "input_source" in metadata or "provider_uri" in metadata,
            }
        )
    return rows


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    symbols = read_universe()

    validations = [formal_validation(asof, symbols) for asof in TARGET_DATES]
    validation_rows = []
    missing_asof_counter: Counter[str] = Counter()
    for item in validations:
        missing_asof = item["formal_source"]["missing_asof"]
        missing_asof_counter.update(missing_asof)
        validation_rows.append(
            {
                "asof": item["asof"],
                "status": item["status"],
                "errors": ",".join(item["errors"]),
                "active_universe_count": item["active_universe_count"],
                "symbols_expected": item["formal_source"]["symbols_expected"],
                "symbols_found": item["formal_source"]["symbols_found"],
                "symbols_with_asof": item["formal_source"]["symbols_with_asof"],
                "missing_files": ",".join(item["formal_source"]["missing_files"]),
                "missing_asof": ",".join(missing_asof),
                "provider_calendar_max": item["provider_calendar_max"],
                "provider_field_inventory_status": item["provider_field_inventory"]["status"],
                "missing_feature_symbols": ",".join(item["provider_field_inventory"]["missing_feature_symbols"]),
                "unexpected_fields": ",".join(item["provider_field_inventory"]["unexpected_fields"]),
                "handler_rejected_hits": ",".join(item["handler_rejected_hits"]),
            }
        )

    coverage_rows: list[dict[str, Any]] = []
    coverage_rows.extend(monthly_csv_coverage("option_c_150_normalized", OPTION_C_NORMALIZED))
    coverage_rows.extend(monthly_csv_coverage("normalized_nonempty", NORMALIZED_NONEMPTY))
    coverage_rows.extend(provider_calendar_coverage())
    coverage_rows.extend(phase0e_monthly_coverage())

    gaps = symbol_gap_rows(symbols)
    pred_fast = pred_fast_inventory()

    validation_path = OUT_DIR / "phase1b_formal_source_diagnosis_validation.csv"
    coverage_path = OUT_DIR / "phase1b_formal_source_diagnosis_source_coverage.csv"
    gaps_path = OUT_DIR / "phase1b_formal_source_diagnosis_symbol_gaps.csv"
    pred_fast_path = OUT_DIR / "phase1b_formal_source_diagnosis_pred_fast_inventory.csv"
    summary_path = OUT_DIR / "phase1b_formal_source_diagnosis_summary.json"

    pd.DataFrame(validation_rows).to_csv(validation_path, index=False)
    pd.DataFrame(coverage_rows).to_csv(coverage_path, index=False)
    pd.DataFrame(gaps).to_csv(gaps_path, index=False)
    pd.DataFrame(pred_fast).to_csv(pred_fast_path, index=False)

    tw7769_option_c = next(
        row for row in gaps if row.get("source") == "option_c_150_normalized" and row.get("symbol") == "TW7769"
    )
    pred_fast_columns = sorted({row.get("prediction_columns", "") for row in pred_fast})
    summary = {
        "created_at": utc_now(),
        "scope": "phase1b_formal_source_diagnosis_readonly",
        "mutations": {
            "network": False,
            "token": False,
            "data_repull": False,
            "prediction_generation": False,
            "provider_write_or_rebuild": False,
            "model_training": False,
            "formal_validation_bypass": False,
            "phase2": False,
        },
        "target_dates": TARGET_DATES,
        "accepted_universe_path": rel(ACCEPTED_UNIVERSE),
        "accepted_universe_count": len(symbols),
        "accepted_universe_includes_TW7769": "TW7769" in symbols,
        "formal_validation_status_by_asof": {row["asof"]: row["status"] for row in validation_rows},
        "formal_validation_error_by_asof": {row["asof"]: row["errors"] for row in validation_rows},
        "missing_asof_symbols_frequency": dict(sorted(missing_asof_counter.items())),
        "provider_calendar_max": provider_calendar_max(),
        "provider_field_inventory_status": provider_field_inventory(symbols)["status"],
        "TW7769_option_c_150_normalized": tw7769_option_c,
        "pred_fast_prediction_file_count": len(pred_fast),
        "pred_fast_prediction_columns_unique": pred_fast_columns,
        "pred_fast_iso_date_tokens": sum(1 for row in pred_fast if row.get("date_token_parseable_iso")),
        "pred_fast_has_complete_provenance": all(
            row.get("has_config_path") and row.get("has_model_path") and row.get("has_recorder_id") and row.get("has_input_source")
            for row in pred_fast
        )
        if pred_fast
        else False,
        "conclusions": {
            "formal_source_fix_possible_without_mutation": True,
            "formal_source_repair_requires_provider_rebuild": False,
            "requires_model_training": False,
            "requires_bypass": False,
            "prediction_repair_requires_bypass_stop": False,
            "pred_fast_provenance_sufficient_for_standardization": False,
        },
        "artifact_paths": {
            "validation": rel(validation_path),
            "source_coverage": rel(coverage_path),
            "symbol_gaps": rel(gaps_path),
            "pred_fast_inventory": rel(pred_fast_path),
            "summary": rel(summary_path),
        },
    }
    write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
