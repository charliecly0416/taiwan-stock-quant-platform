#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix"
DEFAULT_OUT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix_windowed"


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


def build_windowed(source_dir: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    created_at = now()
    summary_path = source_dir / "formal_replay_summary.csv"
    actions_path = source_dir / "formal_replay_actions.csv"
    daily_path = source_dir / "formal_replay_daily_nav.csv"
    summary = pd.read_csv(summary_path)
    actions = pd.read_csv(actions_path)
    windowed_parts: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []
    cursor = 0
    for idx, row in summary.reset_index(drop=True).iterrows():
        count = int(pd.to_numeric(row.get("action_count", 0), errors="coerce") + pd.to_numeric(row.get("skipped_trade_count", 0), errors="coerce"))
        part = actions.iloc[cursor:cursor + count].copy()
        part.insert(len(part.columns), "window", row["window"])
        part.insert(len(part.columns), "source_action_row_index", range(cursor, cursor + len(part)))
        windowed_parts.append(part)
        audit_rows.append({
            "summary_row_index": int(idx),
            "window": row["window"],
            "method": row["method"],
            "rule": row["rule"],
            "expected_action_rows": count,
            "assigned_action_rows": int(len(part)),
            "source_start_row_index": int(cursor),
            "source_end_row_index_exclusive": int(cursor + len(part)),
            "status": "pass" if len(part) == count else "fail",
        })
        cursor += count
    assigned = pd.concat(windowed_parts, ignore_index=True) if windowed_parts else actions.copy()
    total_status = "pass" if cursor == len(actions) and all(row["status"] == "pass" for row in audit_rows) else "fail"
    assigned.to_csv(out_dir / "formal_replay_actions.csv", index=False)
    shutil.copyfile(summary_path, out_dir / "formal_replay_summary.csv")
    shutil.copyfile(daily_path, out_dir / "formal_replay_daily_nav.csv")
    write_csv(out_dir / "action_window_assignment_audit.csv", audit_rows, list(audit_rows[0].keys()) if audit_rows else ["status"])
    manifest = {
        "artifact_type": "baseline_windowed_actions",
        "schema_version": "baseline_action_window_r10_v1",
        "created_at": created_at,
        "created_by": "scripts/build_formal_replay_baseline_action_window_adapter.py",
        "source_dir": rel(source_dir),
        "source_actions": rel(actions_path),
        "source_summary": rel(summary_path),
        "out_dir": rel(out_dir),
        "assignment_policy": "summary_order_action_count_plus_skipped_count_to_window_field",
        "source_actions_unchanged": True,
        "windowed_action_rows": int(len(assigned)),
        "source_action_rows": int(len(actions)),
        "assigned_action_rows": int(cursor),
        "quality_status": total_status,
        "outputs": {
            "summary": rel(out_dir / "formal_replay_summary.csv"),
            "daily_nav": rel(out_dir / "formal_replay_daily_nav.csv"),
            "actions": rel(out_dir / "formal_replay_actions.csv"),
            "assignment_audit": rel(out_dir / "action_window_assignment_audit.csv"),
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
    write_json(out_dir / "manifest.json", manifest)
    return {"ok": total_status == "pass", "manifest": rel(out_dir / "manifest.json"), "windowed_action_rows": int(len(assigned)), "source_action_rows": int(len(actions))}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build windowed baseline actions without modifying the original baseline replay output.")
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    source = Path(args.source_dir)
    out = Path(args.out_dir)
    if not source.is_absolute():
        source = ROOT / source
    if not out.is_absolute():
        out = ROOT / out
    result = build_windowed(source, out)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']} manifest={result['manifest']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
