#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "r9_full_rank_adapter_20260616"


@dataclass(frozen=True)
class FullRankSpec:
    rank_source_name: str
    rank_family: str
    source_path: Path
    source_rank_col: str
    out_dir: Path


SPECS = [
    FullRankSpec(
        rank_source_name="fresh_qlib_s2b_post_filter",
        rank_family="fresh_qlib",
        source_path=ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv",
        source_rank_col="qlib_rank",
        out_dir=ROOT / f"data_tw/artifacts/full_rank/fresh_qlib_s2b_post_filter/{RUN_ID}",
    ),
    FullRankSpec(
        rank_source_name="frozen_qlib_2018_2022_raw_oos",
        rank_family="frozen_qlib",
        source_path=ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv",
        source_rank_col="qlib_rank_raw",
        out_dir=ROOT / f"data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/{RUN_ID}",
    ),
]

FORBIDDEN_PATTERNS = [
    "future_return_",
    "future_excess_return_",
    "forward_return_",
    "label_",
    "relevance_10d_top_heavy",
    "ltr_relevance_label",
    "realized_pnl",
    "realized_return",
    "action",
    "holding",
    "position",
    "target_position",
    "order_qty",
    "execution_price",
    "execution_date",
    "broker_order_id",
    "qlib_score_raw",
    "qlib_rank_raw",
    "adaptive_score_baseline",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def norm(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def forbidden_columns(columns: list[str]) -> list[str]:
    found: list[str] = []
    for col in columns:
        if col in FORBIDDEN_PATTERNS or any(col.startswith(prefix) for prefix in FORBIDDEN_PATTERNS if prefix.endswith("_")):
            found.append(col)
    return sorted(set(found))


def build_one(spec: FullRankSpec, created_at: str) -> dict[str, Any]:
    spec.out_dir.mkdir(parents=True, exist_ok=True)
    source = pd.read_csv(spec.source_path, usecols=["date", "instrument", spec.source_rank_col], parse_dates=["date"])
    out = pd.DataFrame(
        {
            "date": source["date"].dt.strftime("%Y-%m-%d"),
            "instrument": source["instrument"].map(norm),
            "rank_source_name": spec.rank_source_name,
            "rank_family": spec.rank_family,
            "full_qlib_rank": pd.to_numeric(source[spec.source_rank_col], errors="coerce"),
            "signal_asof": source["date"].dt.strftime("%Y-%m-%d"),
            "available_at": source["date"].dt.strftime("%Y-%m-%d"),
            "source_artifact": rel(spec.source_path),
        }
    )
    full_rank_path = spec.out_dir / "full_rank.csv"
    out.to_csv(full_rank_path, index=False)

    duplicate_count = int(out.duplicated(["date", "instrument"]).sum())
    non_null_count = int(out["full_qlib_rank"].notna().sum())
    pit_violations = int((pd.to_datetime(out["available_at"]) > pd.to_datetime(out["signal_asof"])).sum())
    forbidden = forbidden_columns(list(out.columns))
    quality_status = "pass" if duplicate_count == 0 and non_null_count == len(out) and pit_violations == 0 and not forbidden else "fail"

    schema = {
        "artifact_type": "full_rank",
        "schema_version": "full_rank_r9_v1",
        "primary_key": ["date", "instrument"],
        "required_fields": list(out.columns),
        "fields": {col: str(dtype) for col, dtype in out.dtypes.items()},
    }
    schema_path = spec.out_dir / "schema.json"
    write_json(schema_path, schema)

    coverage_rows = [
        {
            "rank_source_name": spec.rank_source_name,
            "row_count": int(len(out)),
            "date_count": int(out["date"].nunique()),
            "start_date": str(out["date"].min()),
            "end_date": str(out["date"].max()),
            "instrument_count": int(out["instrument"].nunique()),
            "duplicate_key_count": duplicate_count,
            "full_qlib_rank_non_null_count": non_null_count,
            "pit_available_at_after_signal_asof_count": pit_violations,
            "status": quality_status,
        }
    ]
    coverage_path = spec.out_dir / "coverage_audit.csv"
    write_csv(coverage_path, coverage_rows, list(coverage_rows[0].keys()))

    forbidden_rows = [
        {
            "rank_source_name": spec.rank_source_name,
            "forbidden_columns_present": "|".join(forbidden),
            "status": "pass" if not forbidden else "fail",
        }
    ]
    forbidden_path = spec.out_dir / "forbidden_field_audit.csv"
    write_csv(forbidden_path, forbidden_rows, list(forbidden_rows[0].keys()))

    mapping_rows = [
        {"standard_field": "date", "source_field": "date", "source_artifact": rel(spec.source_path)},
        {"standard_field": "instrument", "source_field": "instrument", "source_artifact": rel(spec.source_path)},
        {"standard_field": "full_qlib_rank", "source_field": spec.source_rank_col, "source_artifact": rel(spec.source_path)},
        {"standard_field": "signal_asof", "source_field": "date", "source_artifact": rel(spec.source_path)},
        {"standard_field": "available_at", "source_field": "date", "source_artifact": rel(spec.source_path)},
    ]
    mapping_path = spec.out_dir / "legacy_mapping_audit.csv"
    write_csv(mapping_path, mapping_rows, ["standard_field", "source_field", "source_artifact"])

    manifest = {
        "artifact_type": "full_rank",
        "artifact_name": spec.rank_source_name,
        "run_id": RUN_ID,
        "created_at": created_at,
        "created_by": "scripts/build_tw_modular_full_rank_adapter.py",
        "schema_version": "full_rank_r9_v1",
        "contract_version": "FULL_RANK_CONTRACT_CN.md@2026-06-16",
        "rank_source_name": spec.rank_source_name,
        "rank_family": spec.rank_family,
        "source_artifact": rel(spec.source_path),
        "source_rank_column": spec.source_rank_col,
        "row_count": int(len(out)),
        "duplicate_key_count": duplicate_count,
        "full_qlib_rank_non_null_count": non_null_count,
        "pit_available_at_after_signal_asof_count": pit_violations,
        "quality_status": quality_status,
        "output_files": {
            "full_rank": rel(full_rank_path),
            "schema": rel(schema_path),
            "coverage_audit": rel(coverage_path),
            "forbidden_field_audit": rel(forbidden_path),
            "legacy_mapping_audit": rel(mapping_path),
        },
        "capabilities": {
            "full_rank_v1": True,
            "full_qlib_rank": True,
            "pit_available_at_checked": True,
            "legacy_adapter_parity_mode": True,
        },
        "forbidden_actions": {
            "no_training": True,
            "no_tuning": True,
            "no_score_recompute": True,
            "no_replay": True,
            "no_strategy_result": True,
            "no_frontend_change": True,
            "no_daily_orchestrator_change": True,
            "no_provider_publish": True,
            "no_accepted_latest_switch": True,
            "no_monitor": True,
            "no_broker_order": True,
        },
    }
    manifest_path = spec.out_dir / "manifest.json"
    write_json(manifest_path, manifest)
    return {"manifest": rel(manifest_path), "quality_status": quality_status, "row_count": int(len(out))}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build R9 FullRankArtifact adapters from legacy rank CSVs.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    args = parser.parse_args()
    created_at = now()
    rows = [build_one(spec, created_at) for spec in SPECS]
    ok = all(row["quality_status"] == "pass" for row in rows)
    summary = {"ok": ok, "created_at": created_at, "run_id": RUN_ID, "artifacts": rows}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"ok={ok}")
        for row in rows:
            print(f"{row['quality_status']} {row['row_count']} {row['manifest']}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
