#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "data_tw/artifacts/full_universe_provider_audit"
FULL_AUDIT = OUT_ROOT / "w0_20260617_full_universe_audit/full_universe_provider_audit.json"
V5_MATRIX = ROOT / "data_tw/artifacts/provider_staging/phasev5_external_provider_all_ready_codex_v2_provider_staging/model_strategy_availability_matrix.json"
SIGNAL_ROOT = ROOT / "data_tw/artifacts/signals"

MODEL_IDS = [
    "e4_frozen_qlib_2023_2025_ltr",
    "fresh_qlib_2025_ltr",
    "fresh_qlib_adaptive",
    "frozen_qlib_2018_2022",
    "frozen_qlib_2025_ltr",
]
LTR_MODELS = {"e4_frozen_qlib_2023_2025_ltr", "fresh_qlib_2025_ltr", "frozen_qlib_2025_ltr"}
STRATEGIES = [
    "original",
    "top50_exit_all",
    "top50_exit_one_worst_sell",
    "one_sell_one_buy_correct",
    "one_sell_one_buy_buggy_e8r",
    "sector_extension_analysis_smoke",
    "dummy_new_strategy_dependency_smoke",
]
DEFAULT_MODEL_ID = "e4_frozen_qlib_2023_2025_ltr"
DEFAULT_STRATEGY_RULE_ID = "top50_exit_one_worst_sell"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def model_status(model_id: str, full: dict[str, Any]) -> dict[str, Any]:
    model_type = "ltr" if model_id in LTR_MODELS else "qlib"
    manifest = SIGNAL_ROOT / model_id / "r1_legacy_signal_adapter_20260616/manifest.json"
    reasons: list[str] = []
    if not manifest.exists():
        reasons.append("信号清单缺失")
    if full["model_signal"].get("latest_signal_asof") != full.get("target_asof"):
        reasons.append("最新信号日期不一致")
    if int(full["model_signal"].get("prediction_rows") or 0) < 150:
        reasons.append("模型预测未覆盖 150 支")
    if model_type == "ltr":
        ortho = full.get("orthogonal_and_v5_sample_boundary") or {}
        if ortho.get("orthogonal_status") != "ready" or ortho.get("orthogonal_actual_latest_asof") != full.get("target_asof"):
            reasons.append("正交特征未就绪")
        if ortho.get("p3_status") != "ready" or ortho.get("p3_pit_pass") is not True:
            reasons.append("LTR 正交 P3 审计未通过")
    status = "ready" if not reasons else "unavailable"
    return {
        "model_id": model_id,
        "model_type": model_type,
        "status": status,
        "user_reason": "可用于今日只读查询。" if status == "ready" else "；".join(reasons),
        "signal_manifest": rel(manifest),
        "signal_manifest_exists": manifest.exists(),
        "default_model": model_id == DEFAULT_MODEL_ID,
        "readonly_only": True,
    }


def strategy_status(strategy_id: str, model_ready: bool) -> dict[str, Any]:
    if strategy_id == "one_sell_one_buy_buggy_e8r":
        return {"strategy_rule_id": strategy_id, "status": "unsupported", "user_reason": "诊断策略，不提供生产只读选择。", "production_selectable": False, "default_strategy": False, "readonly_only": True}
    if strategy_id in {"sector_extension_analysis_smoke", "dummy_new_strategy_dependency_smoke"}:
        return {"strategy_rule_id": strategy_id, "status": "unsupported", "user_reason": "烟测策略，仅用于合同回归。", "production_selectable": False, "default_strategy": False, "readonly_only": True}
    if not model_ready:
        return {"strategy_rule_id": strategy_id, "status": "unavailable", "user_reason": "没有可用模型输入。", "production_selectable": True, "default_strategy": strategy_id == DEFAULT_STRATEGY_RULE_ID, "readonly_only": True}
    return {"strategy_rule_id": strategy_id, "status": "ready", "user_reason": "可用于今日只读查询。", "production_selectable": True, "default_strategy": strategy_id == DEFAULT_STRATEGY_RULE_ID, "readonly_only": True}


def build(out_dir: Path) -> dict[str, Any]:
    full = read_json(FULL_AUDIT)
    v5_matrix = read_json(V5_MATRIX) if V5_MATRIX.exists() else {}
    models = [model_status(model_id, full) for model_id in MODEL_IDS]
    any_model_ready = any(row["status"] == "ready" for row in models)
    strategies = [strategy_status(strategy_id, any_model_ready) for strategy_id in STRATEGIES]
    combinations = []
    for model in models:
        for strategy in strategies:
            if model["status"] != "ready":
                status = "unavailable"; reason = model["user_reason"]
            elif strategy["status"] != "ready":
                status = strategy["status"]; reason = strategy["user_reason"]
            else:
                status = "ready"; reason = "可用于今日只读查询。"
            combinations.append({
                "model_id": model["model_id"],
                "strategy_rule_id": strategy["strategy_rule_id"],
                "status": status,
                "user_reason": reason,
                "is_default_combination": model["model_id"] == DEFAULT_MODEL_ID and strategy["strategy_rule_id"] == DEFAULT_STRATEGY_RULE_ID,
                "does_not_fallback_to_default": True,
                "readonly_only": True,
            })
    audit = {
        "schema_version": "w0.model_strategy_matrix_audit.v1",
        "artifact_type": "model_strategy_matrix_audit",
        "created_at": now(),
        "target_asof": full.get("target_asof"),
        "readonly_audit_only": True,
        "default_model_id": DEFAULT_MODEL_ID,
        "default_strategy_rule_id": DEFAULT_STRATEGY_RULE_ID,
        "source_artifacts": {"full_universe_provider_audit": rel(FULL_AUDIT), "v5_model_strategy_matrix": rel(V5_MATRIX)},
        "models": models,
        "strategies": strategies,
        "combinations": combinations,
        "allowed_statuses": ["ready", "unavailable", "unsupported"],
        "default_ready_does_not_imply_other_ready": True,
        "frontend_must_not_silently_fallback_to_default": True,
        "v5_matrix_gate_status": v5_matrix.get("target_asof"),
        "forbidden_action_audit": {"actions": {"training_triggered": False, "model_tuning_triggered": False, "default_model_switched": False, "default_strategy_switched": False, "provider_publish_triggered": False, "accepted_latest_switched": False, "orders_created_or_sent": False}},
    }
    write_json(out_dir / "model_strategy_matrix_audit.json", audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description="W0 readonly model/strategy matrix audit.")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    out_dir = Path(args.out_dir) if args.out_dir else OUT_ROOT / "w0_20260617_full_universe_audit"
    if not out_dir.is_absolute(): out_dir = ROOT / out_dir
    result = build(out_dir)
    output = {"ok": True, "status": "passed", "audit": rel(out_dir / "model_strategy_matrix_audit.json"), "model_count": len(result["models"]), "strategy_count": len(result["strategies"]), "combination_count": len(result["combinations"])}
    print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output["audit"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
