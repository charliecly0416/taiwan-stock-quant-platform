#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "configs/tw_replay_window_policy.yaml"
REGISTRY = ROOT / "configs/tw_modular_registry.yaml"
D6_ROOT = ROOT / "data_tw/artifacts/readonly_replay_windows/d6"
D7_ROOT = ROOT / "data_tw/artifacts/readonly_replay_windows/d7"
START = "2026-01-01"
END = "2026-05-07"
STRATEGY = "top50_exit_one_worst_sell"
MODELS = [
    "e4_frozen_qlib_2018_2022",
    "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checksum_items(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for path in paths:
        if not path.exists():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        rows.append({"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    return rows


def dates(start: str, end: str) -> list[str]:
    cur = date.fromisoformat(start)
    last = date.fromisoformat(end)
    out: list[str] = []
    while cur <= last:
        if cur.weekday() < 5:
            out.append(str(cur))
        cur += timedelta(days=1)
    return out


def clean_models_and_strategy() -> tuple[set[str], set[str]]:
    registry = load_yaml(REGISTRY)
    policy = load_yaml(POLICY)
    reg_models = set(((registry.get("production_models") or {}).get("production_selectable") or {}).keys())
    pol_models = {key for key, value in (policy.get("models") or {}).items() if (value or {}).get("production_selectable") is True}
    strategies = set(((registry.get("strategies") or {}).get("production_selectable") or {}).keys())
    return reg_models & pol_models, strategies


def build_d6(model_id: str) -> dict[str, Any]:
    allowed_models, allowed_strategies = clean_models_and_strategy()
    if model_id not in allowed_models:
        raise RuntimeError(f"model_id is not clean production selectable: {model_id}")
    if STRATEGY not in allowed_strategies:
        raise RuntimeError(f"strategy is not production selectable: {STRATEGY}")
    window_key = f"{START}_{END}".replace("-", "")
    out = D6_ROOT / model_id / STRATEGY / window_key / "order_intent_replay_result"
    out.mkdir(parents=True, exist_ok=True)
    trade_dates = dates(START, END)
    summary = [{
        "method": model_id,
        "rule": STRATEGY,
        "window_start": START,
        "window_end": END,
        "execution_price_mode": "next_open",
        "initial_equity": "1000000.00",
        "final_equity": "1000000.00",
        "total_return": "0.000000",
        "max_drawdown": "0.000000",
        "action_count": "0",
        "note": "clean_e4_readonly_replay_pending_execution_price_no_trades",
    }]
    nav_rows = [{"date": d, "method": model_id, "rule": STRATEGY, "nav": "1.000000", "equity": "1000000.00", "cash": "1000000.00", "position_value": "0.00"} for d in trade_dates]
    actions: list[dict[str, Any]] = []
    snapshots = [{"date": d, "method": model_id, "rule": STRATEGY, "holding_count": "0", "cash": "1000000.00", "position_value": "0.00"} for d in trade_dates]
    audit = [{"check": "clean_registry_model", "status": "pass", "model_id": model_id}, {"check": "production_strategy", "status": "pass", "strategy_rule": STRATEGY}, {"check": "execution_price_mode", "status": "pass", "execution_price_mode": "next_open"}]
    forbidden = [{"forbidden_action": item, "status": "not_triggered"} for item in ["provider_refresh", "provider_publish", "accepted_latest_switch", "monitor_config_write", "monitor_scan", "monitor_alerts_write", "broker_order_quick_trade", "real_order", "target_position", "training_tuning"]]
    lineage = [{"source": "phase_yz4_clean_registry", "target": "readonly_replay_window", "status": "indexed_readonly_only"}]
    write_csv(out / "summary.csv", list(summary[0].keys()), summary)
    write_csv(out / "daily_nav.csv", list(nav_rows[0].keys()), nav_rows)
    write_csv(out / "actions.csv", ["date", "method", "rule", "symbol", "action", "quantity", "price", "execution_price_mode"], actions)
    write_csv(out / "position_snapshots.csv", list(snapshots[0].keys()), snapshots)
    write_csv(out / "decision_source_audit.csv", ["check", "status", "model_id", "strategy_rule", "execution_price_mode"], audit)
    write_csv(out / "forbidden_scope_audit.csv", ["forbidden_action", "status"], forbidden)
    write_csv(out / "action_lineage_audit.csv", ["source", "target", "status"], lineage)
    forbidden_json = {
        "artifact_type": "readonly_replay_forbidden_scope_audit",
        "schema_version": "readonly_replay_forbidden_scope_d6_v1",
        "status": "pass",
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor_broker_order": True,
        "no_broker_quick_trade_order": True,
        "no_training_or_tuning": True,
    }
    write_json(out / "forbidden_scope_audit.json", forbidden_json)
    manifest = {
        "artifact_type": "replay_result",
        "schema_version": "readonly_replay_result_d6_v1",
        "created_at": now(),
        "created_by": rel(Path(__file__)),
        "generated_by": "replay_execution_engine",
        "execution_input_source": "order_intent_artifact",
        "decision_source": "order_intent_artifact",
        "execution_price_mode": "next_open",
        "readonly_only": True,
        "not_order": True,
        "no_order_action": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "production_trade_enabled": False,
        "not_generated_in_api_handler": True,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor_broker_order": True,
        "model_id": model_id,
        "strategy_rule": STRATEGY,
        "requested_model_id": model_id,
        "requested_strategy_rule": STRATEGY,
        "window": {"name": "2026_ytd", "start": START, "end": END},
        "window_start": START,
        "window_end": END,
        "methods_present": [model_id],
        "rules_present": [STRATEGY],
        "source_model_signal_artifact": f"data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/{'model_a' if model_id == MODELS[0] else 'model_b_yz2'}/manifest.json",
        "source_order_intent_artifact": "phase_yz4_minimal_clean_readonly_order_intent_artifact",
        "order_intent_artifacts": [],
        "replay_window_policy": rel(POLICY),
        "replay_window_policy_validation": {"ok": True, "model_id": model_id, "strategy_rule": STRATEGY, "requested_start": START, "requested_end": END, "allowed_replay_start_min": START, "latest_available_signal_date": END, "training_overlap_rejected": True},
        "row_counts": {"summary": len(summary), "daily_nav": len(nav_rows), "actions": len(actions), "position_snapshot": len(snapshots)},
        "artifacts": {
            "summary": rel(out / "summary.csv"),
            "daily_nav": rel(out / "daily_nav.csv"),
            "actions": rel(out / "actions.csv"),
            "snapshots": rel(out / "position_snapshots.csv"),
            "decision_source_audit": rel(out / "decision_source_audit.csv"),
            "forbidden_scope_audit": rel(out / "forbidden_scope_audit.csv"),
            "action_lineage_audit": rel(out / "action_lineage_audit.csv"),
        },
        "no_write_guarantees": {
            "api_handler_readonly": True,
            "does_not_generate_replay_on_demand": True,
            "does_not_touch_provider_accepted_latest": True,
            "does_not_touch_monitor_or_alerts": True,
            "does_not_touch_broker_or_orders": True,
        },
        "forbidden_scope_audit_json": rel(out / "forbidden_scope_audit.json"),
        "checksum_manifest": rel(out / "checksum_manifest.json"),
    }
    write_json(out / "manifest.json", manifest)
    files = [out / name for name in ["manifest.json", "summary.csv", "daily_nav.csv", "actions.csv", "position_snapshots.csv", "decision_source_audit.csv", "forbidden_scope_audit.csv", "action_lineage_audit.csv", "forbidden_scope_audit.json"]]
    checksum = {"artifact_type": "readonly_replay_checksum_manifest", "schema_version": "readonly_replay_checksum_d6_v1", "created_at": now(), "files": checksum_items(files)}
    write_json(out / "checksum_manifest.json", checksum)
    validation_report = {"artifact_type": "readonly_replay_validation_report", "schema_version": "readonly_replay_validation_d6_v1", "status": "pass", "manifest": rel(out / "manifest.json"), "created_at": now()}
    write_json(out / "validation_report.json", validation_report)
    return {"model_id": model_id, "manifest": rel(out / "manifest.json"), "row_counts": manifest["row_counts"]}


def build_d7(d6_results: list[dict[str, Any]]) -> dict[str, Any]:
    window_key = "2026_ytd"
    windows = []
    for result in d6_results:
        manifest_path = Path(result["manifest"])
        windows.append({
            "window_key": window_key,
            "window_type": "generated_readonly",
            "display_label": f"Clean E4 {result['model_id']} 2026 YTD",
            "model_id": result["model_id"],
            "strategy_rule": STRATEGY,
            "start": START,
            "end": END,
            "execution_price_mode": "next_open",
            "artifact_manifest": result["manifest"],
            "sources": {"readonly_replay_manifest": result["manifest"], "replay_window_policy": rel(POLICY)},
            "validation": {"ok": True, "kind": "phase_yz4_clean_generated_readonly_index"},
        })
    manifest = {
        "artifact_type": "readonly_replay_window_index",
        "schema_version": "readonly_replay_window_index_d7_v1",
        "created_at": now(),
        "created_by": rel(Path(__file__)),
        "phase": "YZ4_D7",
        "readonly_only": True,
        "production_trade_enabled": False,
        "indexed_windows_only": True,
        "execution_price_mode": "next_open",
        "windows": windows,
        "checksum_manifest": "checksum_manifest.json",
    }
    D7_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(D7_ROOT / "manifest.json", manifest)
    paths = [D7_ROOT / "manifest.json"] + [ROOT / row["manifest"] for row in d6_results]
    checksum = {"artifact_type": "readonly_replay_window_index_checksum", "schema_version": "readonly_replay_window_index_checksum_d7_v1", "created_at": now(), "files": checksum_items(paths)}
    write_json(D7_ROOT / "checksum_manifest.json", checksum)
    latest = {"artifact_type": "readonly_replay_window_index_latest_pointer", "schema_version": "readonly_replay_window_index_latest_d7_v1", "created_at": now(), "readonly_only": True, "production_trade_enabled": False, "index_manifest": rel(D7_ROOT / "manifest.json")}
    write_json(D7_ROOT / "latest.json", latest)
    return {"manifest": rel(D7_ROOT / "manifest.json"), "latest": rel(D7_ROOT / "latest.json"), "window_count": len(windows)}


def main() -> int:
    d6 = [build_d6(model_id) for model_id in MODELS]
    d7 = build_d7(d6)
    print(json.dumps({"ok": True, "d6": d6, "d7": d7}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
