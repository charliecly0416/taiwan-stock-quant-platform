#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "data_tw/artifacts/full_universe_provider_audit"
ALLOWED_STATUSES = {"ready", "unavailable", "unsupported"}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def err(code: str, message: str, path: Path, field: str = "") -> dict[str, str]:
    return {"code": code, "message": message, "path": rel(path), "field": field}


def write_frontend_contract(out_dir: Path, full: dict[str, Any], matrix: dict[str, Any]) -> dict[str, Any]:
    contract = {
        "schema_version": "w0.frontend_state_contract.v1",
        "artifact_type": "frontend_state_contract",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "readonly_only": True,
        "target_asof": full.get("target_asof"),
        "main_states": [
            {"state": "already_latest", "label": "已是最新", "message": "已是最新，继续展示当前只读结果。"},
            {"state": "triggerable", "label": "可更新", "message": "可拉取最新数据并生成只读结果。"},
            {"state": "checking", "label": "检查中", "message": "正在检查数据状态。"},
            {"state": "unavailable", "label": "不可用", "message": "显示模型、策略或数据源的短原因。"},
        ],
        "forbidden_display_patterns": [
            "legacy readiness label followed by a bare dash",
            "5-symbol sample described as full-universe coverage",
            "fallback source displayed as primary source",
        ],
        "coverage_language_policy": "5-symbol V5 staging sample must be labeled sample; 150-symbol daily auto update evidence may be labeled full universe.",
        "fallback_language_policy": "fallback used must be explicitly shown; never present fallback as primary source.",
        "matrix_display_policy": "Every model/strategy combination must show ready/unavailable/unsupported and user_reason; no silent fallback to default.",
        "default_combination": {"model_id": matrix.get("default_model_id"), "strategy_rule_id": matrix.get("default_strategy_rule_id")},
        "full_universe_summary": {
            "target_asof": full.get("target_asof"),
            "universe_size": (full.get("full_universe") or {}).get("size"),
            "qlib_provider_active_universe_count": (full.get("yahoo_scrapling_provider") or {}).get("provider_active_universe_count"),
            "finmind_daily_symbols_on_target_asof": (full.get("finmind_daily_raw") or {}).get("symbols_on_target_asof"),
            "v5_staging_is_sample": (full.get("orthogonal_and_v5_sample_boundary") or {}).get("v5_staging_is_sample"),
        },
        "forbidden_action_audit": {"actions": {"provider_publish_triggered": False, "accepted_latest_switched": False, "monitor_config_written": False, "orders_created_or_sent": False}},
    }
    write_json(out_dir / "frontend_state_contract.json", contract)
    return contract


def validate(out_dir: Path) -> dict[str, Any]:
    full_path = out_dir / "full_universe_provider_audit.json"
    matrix_path = out_dir / "model_strategy_matrix_audit.json"
    frontend_path = out_dir / "frontend_state_contract.json"
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    if not full_path.exists():
        return {"ok": False, "status": "failed", "errors": [err("full_audit_missing", "full universe provider audit missing", full_path)], "warnings": warnings}
    if not matrix_path.exists():
        return {"ok": False, "status": "failed", "errors": [err("matrix_audit_missing", "model strategy matrix audit missing", matrix_path)], "warnings": warnings}
    full = read_json(full_path)
    matrix = read_json(matrix_path)
    frontend = write_frontend_contract(out_dir, full, matrix)
    target = str(full.get("target_asof") or "")
    if int((full.get("full_universe") or {}).get("size") or 0) < 150:
        errors.append(err("full_universe_size_too_small", "full universe size must be >=150", full_path, "full_universe.size"))
    yahoo = full.get("yahoo_scrapling_provider") or {}
    if str(yahoo.get("provider_calendar_max") or "") < target:
        errors.append(err("qlib_calendar_stale", "qlib provider calendar max must cover target_asof", full_path, "yahoo_scrapling_provider.provider_calendar_max"))
    if int(yahoo.get("provider_active_universe_count") or 0) < 150:
        errors.append(err("qlib_active_universe_too_small", "qlib active universe count must be >=150", full_path, "yahoo_scrapling_provider.provider_active_universe_count"))
    if int((full.get("model_signal") or {}).get("prediction_rows") or 0) < 150:
        errors.append(err("prediction_rows_too_small", "model signal prediction rows must be >=150", full_path, "model_signal.prediction_rows"))
    if str((full.get("model_signal") or {}).get("latest_signal_asof") or "") != target:
        errors.append(err("latest_signal_asof_mismatch", "latest_signal_asof must equal target_asof", full_path, "model_signal.latest_signal_asof"))
    actions = ((full.get("forbidden_action_audit") or {}).get("actions") or {})
    for key, val in actions.items():
        if val is True:
            errors.append(err("w0_forbidden_action_triggered", f"{key} must be false", full_path, f"forbidden_action_audit.actions.{key}"))
    if (full.get("orthogonal_and_v5_sample_boundary") or {}).get("v5_staging_is_sample") is not True:
        errors.append(err("sample_boundary_missing", "V5 staging sample boundary must be explicit", full_path, "orthogonal_and_v5_sample_boundary.v5_staging_is_sample"))
    combo = matrix.get("combinations") or []
    if not combo:
        errors.append(err("matrix_combinations_missing", "matrix combinations required", matrix_path, "combinations"))
    for idx, row in enumerate(combo):
        if row.get("status") not in ALLOWED_STATUSES:
            errors.append(err("matrix_status_invalid", "status must be ready/unavailable/unsupported", matrix_path, f"combinations[{idx}].status"))
        if row.get("status") != "ready" and not row.get("user_reason"):
            errors.append(err("matrix_user_reason_missing", "unavailable/unsupported must have user_reason", matrix_path, f"combinations[{idx}].user_reason"))
        if row.get("does_not_fallback_to_default") is not True:
            errors.append(err("matrix_fallback_boundary_missing", "combination must not silently fallback to default", matrix_path, f"combinations[{idx}].does_not_fallback_to_default"))
    if matrix.get("default_ready_does_not_imply_other_ready") is not True:
        errors.append(err("default_matrix_boundary_missing", "default ready must not imply others ready", matrix_path, "default_ready_does_not_imply_other_ready"))
    texts = json.dumps(frontend, ensure_ascii=False)
    if "数据就绪状态 -" in texts:
        errors.append(err("frontend_forbidden_text", "frontend contract must not contain 数据就绪状态 -", frontend_path, "forbidden_text"))
    if not frontend.get("coverage_language_policy"):
        errors.append(err("frontend_coverage_policy_missing", "frontend coverage policy required", frontend_path, "coverage_language_policy"))
    ok = not errors
    return {"ok": ok, "status": "passed" if ok else "failed", "schema_version": "w0.full_universe_provider_audit_validator.v1", "artifact_dir": rel(out_dir), "errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate W0 full universe provider and matrix audit artifacts.")
    parser.add_argument("--artifact-dir", default=str(OUT_ROOT / "w0_20260617_full_universe_audit"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    out_dir = Path(args.artifact_dir)
    if not out_dir.is_absolute(): out_dir = ROOT / out_dir
    result = validate(out_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"ok={result['ok']}\nstatus={result['status']}")
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
