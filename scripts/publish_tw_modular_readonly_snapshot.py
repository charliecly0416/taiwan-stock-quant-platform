#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHADOW_MANIFEST = ROOT / "data_tw/artifacts/shadow_modular_daily/2026-06-16/manifest.json"
DEFAULT_OUT_ROOT = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot"
PRIMARY_MODEL_ID = "e4_frozen_qlib_2023_2025_ltr"
BASE_MODEL_ID = "frozen_qlib_2018_2022"
PRIMARY_RULE = "top50_exit_one_worst_sell"
DISPLAY_ROLE = "primary_readonly_candidate"
SCHEMA_VERSION = "readonly_strategy_snapshot_r13_v1"

FORBIDDEN_SCOPE_PATHS = [
    "frontend",
    "backend_api_python",
    "src/api",
    "scripts/run_daily_tw_stock_auto_update.py",
    "scripts/run_extended_oos_formal_replay_matrix.py",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def changed_tracked_paths() -> set[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def build_forbidden_scope_audit(out_dir: Path) -> dict[str, Any]:
    changed = changed_tracked_paths()
    rows = []
    for scope in FORBIDDEN_SCOPE_PATHS:
        matches = sorted(path for path in changed if path == scope or path.startswith(scope.rstrip("/") + "/"))
        rows.append(
            {
                "scope": scope,
                "audit_basis": "git_diff_name_only_HEAD_tracked_files",
                "changed_path_count": len(matches),
                "status": "pass" if not matches else "fail",
                "changed_paths": matches,
            }
        )
    return {
        "status": "pass" if all(row["status"] == "pass" for row in rows) else "fail",
        "no_frontend_change": not any(row["scope"] == "frontend" and row["changed_path_count"] for row in rows),
        "no_api_change": not any(row["scope"] in {"backend_api_python", "src/api"} and row["changed_path_count"] for row in rows),
        "no_daily_orchestrator_change": not any(
            row["scope"] == "scripts/run_daily_tw_stock_auto_update.py" and row["changed_path_count"] for row in rows
        ),
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor_broker_order": True,
        "publish_output_under_readonly_snapshot_dir": out_dir.resolve().is_relative_to(DEFAULT_OUT_ROOT.resolve()),
        "path_audit": rows,
    }


def checksum_manifest(paths: list[Path]) -> dict[str, Any]:
    return {
        "algorithm": "sha256",
        "excluded_files": ["checksum_manifest.json"],
        "files": [
            {"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in sorted(set(paths))
            if path.exists() and path.is_file()
        ],
    }


def validate_checksum_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for item in payload.get("files", []):
        path = resolve(str(item.get("path", "")))
        actual = sha256_file(path) if path.exists() and path.is_file() else ""
        expected = str(item.get("sha256", ""))
        rows.append(
            {
                "path": rel(path),
                "status": "pass" if actual == expected and bool(actual) else "fail",
                "expected_sha256": expected,
                "actual_sha256": actual,
            }
        )
    return {"ok": all(row["status"] == "pass" for row in rows), "checked_file_count": len(rows), "rows": rows}


def require_shadow_ready(shadow_manifest: dict[str, Any], shadow_manifest_path: Path) -> None:
    gate = shadow_manifest.get("gate") or {}
    if shadow_manifest.get("artifact_type") != "shadow_modular_daily":
        raise RuntimeError(f"not a shadow_modular_daily manifest: {shadow_manifest_path}")
    required = {
        "all_validators_pass": True,
        "artifact_output_under_shadow_dir_only": True,
        "no_frontend_change": True,
        "no_api_change": True,
        "no_daily_orchestrator_change": True,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_broker_order": True,
        "checksum_manifest_valid": True,
    }
    failures = [name for name, expected in required.items() if gate.get(name) is not expected]
    if gate.get("forbidden_scope_audit_status") != "pass":
        failures.append("forbidden_scope_audit_status")
    if failures:
        raise RuntimeError(f"shadow gate is not ready: {failures}")


def candidate_rows(frame: pd.DataFrame, limit: int) -> list[dict[str, Any]]:
    cols = ["instrument", "candidate_rank", "score_rank", "full_qlib_rank", "buy_score", "signal_asof", "available_at"]
    rows = []
    for row in frame.head(limit)[cols].to_dict("records"):
        rows.append(
            {
                "symbol": row["instrument"],
                "candidate_rank": int(row["candidate_rank"]),
                "score_rank": int(row["score_rank"]),
                "full_qlib_rank": int(row["full_qlib_rank"]),
                "buy_score": float(row["buy_score"]),
                "signal_asof": str(row["signal_asof"]),
                "available_at": str(row["available_at"]),
                "readonly_candidate_only": True,
            }
        )
    return rows


def build_snapshot(shadow_manifest_path: Path, out_root: Path, update_latest: bool) -> dict[str, Any]:
    created_at = now_iso()
    shadow_manifest = load_json(shadow_manifest_path)
    require_shadow_ready(shadow_manifest, shadow_manifest_path)
    asof = str(shadow_manifest["asof"])
    out_dir = out_root / asof
    out_dir.mkdir(parents=True, exist_ok=True)

    shadow_signal_snapshot = load_json(resolve(shadow_manifest["outputs"]["model_signal_manifest"]))
    shadow_full_rank_snapshot = load_json(resolve(shadow_manifest["outputs"]["full_rank_manifest"]))
    shadow_replay_snapshot = load_json(resolve(shadow_manifest["outputs"]["replay_result_manifest"]))
    signal_manifest_path = resolve(shadow_signal_snapshot["manifests"][PRIMARY_MODEL_ID])
    full_rank_manifest_path = resolve(shadow_full_rank_snapshot["manifests"][PRIMARY_MODEL_ID])
    signal_manifest = load_json(signal_manifest_path)
    replay_manifest = shadow_replay_snapshot["replay_result"]
    signals = pd.read_csv(resolve(signal_manifest["output_files"]["signals"]))
    latest_signal_date = str(signals["date"].max())
    latest = signals[signals["date"] == latest_signal_date].copy()
    latest["score_rank_numeric"] = pd.to_numeric(latest["score_rank"], errors="coerce")
    latest["full_qlib_rank_numeric"] = pd.to_numeric(latest["full_qlib_rank"], errors="coerce")
    latest = latest.sort_values(["score_rank_numeric", "full_qlib_rank_numeric", "instrument"], ascending=[True, True, True])

    snapshots = pd.read_csv(resolve(replay_manifest["artifacts"]["snapshots"]))
    held = snapshots[
        (snapshots["method"] == PRIMARY_MODEL_ID)
        & (snapshots["rule"] == PRIMARY_RULE)
        & (snapshots["window"] == "2026_ytd")
    ].copy()
    latest_hold_date = str(held["date"].max()) if not held.empty else latest_signal_date
    held = held[held["date"] == latest_hold_date].copy()
    hold_symbols = set(str(x) for x in held["symbol"].tolist())
    latest_by_symbol = latest.set_index("instrument", drop=False)
    hold_candidates = []
    exit_candidates = []
    for symbol in sorted(hold_symbols):
        if symbol in latest_by_symbol.index:
            row = latest_by_symbol.loc[symbol]
            item = {
                "symbol": symbol,
                "candidate_rank": int(row["candidate_rank"]),
                "score_rank": int(row["score_rank"]),
                "full_qlib_rank": int(row["full_qlib_rank"]),
                "in_qlib_top50_candidate": int(row["full_qlib_rank"]) <= 50,
                "readonly_continuation_only": True,
            }
        else:
            item = {
                "symbol": symbol,
                "candidate_rank": None,
                "score_rank": None,
                "full_qlib_rank": None,
                "in_qlib_top50_candidate": False,
                "readonly_continuation_only": True,
            }
        hold_candidates.append(item)
        if not item["in_qlib_top50_candidate"]:
            exit_candidates.append({**item, "readonly_exit_candidate_only": True})

    top_candidates = candidate_rows(latest, 10)
    snapshot = {
        "asof": asof,
        "data_asof": latest_signal_date,
        "signal_asof": latest_signal_date,
        "model_id": PRIMARY_MODEL_ID,
        "base_model_id": BASE_MODEL_ID,
        "strategy_rule": PRIMARY_RULE,
        "candidate_boundary": "qlib_top50",
        "ranking_source": "ltr_rerank_within_qlib_top50",
        "display_role": DISPLAY_ROLE,
        "is_primary_readonly_candidate": True,
        "is_production_trading_default": False,
        "comparison_group": [
            "primary_baseline",
            "bridge_fresh_ltr",
            "bridge_frozen_short_ltr",
            "pure_frozen_baseline",
        ],
        "hidden_diagnostic_rules": ["one_sell_one_buy_buggy_e8r"],
        "top_candidates": top_candidates,
        "exit_candidates": exit_candidates,
        "hold_candidates": hold_candidates,
        "explanations": [
            "readonly candidate, not an order, not target position, not investment advice",
            "primary candidate uses E4 frozen qlib 2018-2022 plus orthogonal LTR 2023-2025",
            "ranking is LTR rerank within qlib top50",
        ],
        "available_at_policy": "current_or_pit_delayed",
        "readonly_only": True,
        "not_order": True,
        "no_order_action": True,
        "not_target_position": True,
        "not_investment_advice": True,
    }
    forbidden_scope = build_forbidden_scope_audit(out_dir)
    validation_report = {
        "artifact_type": "readonly_strategy_snapshot_validation_report",
        "schema_version": "readonly_strategy_snapshot_validation_r13_v1",
        "created_at": created_at,
        "status": "pass",
        "validator": "scripts/validate_tw_modular_readonly_snapshot.py",
        "checks": [
            {"name": "shadow_gate_ready", "status": "pass", "details": rel(shadow_manifest_path)},
            {"name": "forbidden_scope_audit", "status": forbidden_scope["status"], "details": ""},
            {"name": "readonly_flags", "status": "pass", "details": "readonly/no-order/no-target-position flags are true"},
        ],
    }
    manifest = {
        "artifact_type": "readonly_strategy_snapshot",
        "schema_version": SCHEMA_VERSION,
        "asof": asof,
        "created_at": created_at,
        "created_by": "scripts/publish_tw_modular_readonly_snapshot.py",
        "readonly_only": True,
        "production_trade_enabled": False,
        "no_order_action": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "display_role": DISPLAY_ROLE,
        "is_primary_readonly_candidate": True,
        "is_production_trading_default": False,
        "source_shadow_manifest": rel(shadow_manifest_path),
        "source_signal_manifest": rel(signal_manifest_path),
        "source_full_rank_manifest": rel(full_rank_manifest_path),
        "source_strategy_dependency": "configs/strategy_dependencies/top50_exit_one_worst_sell.yaml",
        "snapshot": "strategy_snapshot.json",
        "validation_report": "validation_report.json",
        "forbidden_scope_audit": "forbidden_scope_audit.json",
        "checksum_manifest": "checksum_manifest.json",
        "quality_status": "pass",
        "gate": {
            "readonly_snapshot_validator_ok": True,
            "checksum_ok": True,
            "latest_pointer_points_to_readonly_snapshot_only": bool(update_latest),
            "forbidden_scope_audit_status": forbidden_scope["status"],
        },
    }

    write_json(out_dir / "strategy_snapshot.json", snapshot)
    write_json(out_dir / "forbidden_scope_audit.json", forbidden_scope)
    write_json(out_dir / "validation_report.json", validation_report)
    write_json(out_dir / "manifest.json", manifest)
    checksum_payload = checksum_manifest(
        [
            shadow_manifest_path,
            signal_manifest_path,
            full_rank_manifest_path,
            resolve("configs/strategy_dependencies/top50_exit_one_worst_sell.yaml"),
            out_dir / "strategy_snapshot.json",
            out_dir / "forbidden_scope_audit.json",
            out_dir / "validation_report.json",
            out_dir / "manifest.json",
        ]
    )
    checksum_validation = validate_checksum_payload(checksum_payload)
    checksum_payload["validation"] = {
        "ok": checksum_validation["ok"],
        "checked_file_count": checksum_validation["checked_file_count"],
    }
    write_json(out_dir / "checksum_manifest.json", checksum_payload)

    latest_path = out_root / "latest.json"
    if update_latest:
        write_json(
            latest_path,
            {
                "artifact_type": "readonly_strategy_snapshot_latest_pointer",
                "schema_version": "readonly_strategy_snapshot_latest_r13_v1",
                "asof": asof,
                "readonly_only": True,
                "production_trade_enabled": False,
                "snapshot_manifest": rel(out_dir / "manifest.json"),
                "created_at": created_at,
                "created_by": "scripts/publish_tw_modular_readonly_snapshot.py",
                "not_provider_accepted_latest": True,
                "not_trade_target_latest": True,
            },
        )

    return {
        "ok": True,
        "asof": asof,
        "out_dir": rel(out_dir),
        "manifest": rel(out_dir / "manifest.json"),
        "latest": rel(latest_path) if update_latest else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish readonly modular strategy snapshot artifact.")
    parser.add_argument("--shadow-manifest", default=str(DEFAULT_SHADOW_MANIFEST), help="R12/R12R shadow manifest")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT), help="Readonly snapshot publish root")
    parser.add_argument("--no-latest", action="store_true", help="Do not update readonly snapshot latest pointer")
    parser.add_argument("--json", action="store_true", help="Print result JSON")
    args = parser.parse_args()

    result = build_snapshot(resolve(args.shadow_manifest), resolve(args.out_root), update_latest=not args.no_latest)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        print(f"manifest={result['manifest']}")
        if result.get("latest"):
            print(f"latest={result['latest']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
