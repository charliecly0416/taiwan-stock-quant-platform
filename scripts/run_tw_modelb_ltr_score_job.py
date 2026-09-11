#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tw_modelb_ltr_score_common import (
    BLOCKED_STATUS,
    CATALOG_VALIDATION_PATH,
    DEFAULT_RUN_ID,
    DNG7_MODELA_SIGNAL_DIR,
    EXECUTION_REPORT_PATH,
    FALLBACK_ALLOWED,
    FORBIDDEN_ACTIONS_FALSE,
    INPUT_BASE,
    LTR_MODEL_ARTIFACT,
    MODEL_ID,
    SCORE_BASE,
    TARGET_ASOF,
    file_entry,
    read_json,
    rel,
    utc_now,
    write_json,
)
from validate_tw_modelb_ltr_score_job import validate


def write_execution_report(
    run_id: str,
    asof: str,
    input_dir: Path,
    score_dir: Path,
    input_manifest: dict[str, Any],
    input_readiness: dict[str, Any],
    validator_report: dict[str, Any],
) -> None:
    blocking = input_readiness.get("blocking_datasets", [])
    lines = [
        "# DNG8 Model B LTR Score Pipeline 执行报告",
        "",
        f"生成时间：{utc_now()}",
        "",
        "## 1. 结论",
        "",
        f"- run_id：`{run_id}`",
        f"- 目标 asof：`{asof}`",
        f"- score_status：`{BLOCKED_STATUS}`",
        "- LTR 是否 ready：`NO`",
        "- 是否生成 Model B LTR signal：`NO`",
        "- validator：`{}`".format(validator_report.get("status")),
        "",
        "DNG8 已建立 Model B LTR inference/ScoreJob gate，但未生成 LTR signal。原因是 DNG3 明确记录 `can_continue_to_model_b_ltr=false`，且必需正交数据未齐备。",
        "",
        "## 2. Blocker 证据",
        "",
        f"- blocking_datasets：`{', '.join(blocking)}`",
        f"- input blocker：`{rel(input_dir / 'blocker_input_readiness.json')}`",
        f"- DNG3 readiness：`{input_readiness.get('input_dependencies', {}).get('orthogonal_feature_store', {}).get('readiness_matrix_path', '')}`",
        f"- input manifest：`{rel(input_dir / 'manifest.json')}`",
        f"- score manifest：`{rel(score_dir / 'manifest.json')}`",
        "",
        "阻断语义：`corporate_actions`、`monthly_revenue`、`valuation` 仍未作为完整 PIT-safe canonical orthogonal feature family 放行；因此 LTR 特征 schema 与当前 DNG3 store 不能证明齐备。",
        "",
        "## 3. Fallback 语义",
        "",
        f"- fallback_allowed：`{FALLBACK_ALLOWED}`",
        f"- fallback 只能引用：`{rel(DNG7_MODELA_SIGNAL_DIR)}`",
        "- fallback 不是 Model B LTR score；不得用 qlib score 冒充 LTR `buy_score/raw_score/score_rank`。",
        "- 下游只有在 strategy dependency/contract 显式允许 qlib-only fallback 时，才能消费 DNG7 Model A。",
        "",
        "## 4. LTR Top50 合同",
        "",
        "- LTR 若未来放行，只能在 DNG7 Model A qlib top50 内 rerank。",
        "- `candidate_rank` 与 `full_qlib_rank` 必须来自 DNG7 Model A。",
        "- `buy_score` 与 `score_rank` 才能来自 LTR；本轮没有生成这些 LTR 字段。",
        "",
        "## 5. Validator 输出",
        "",
        f"- status：`{validator_report.get('status')}`",
        f"- ok：`{validator_report.get('ok')}`",
        f"- errors：`{validator_report.get('errors')}`",
        f"- catalog validation：`{rel(CATALOG_VALIDATION_PATH)}`",
        "",
        "## 6. Forbidden Action Audit",
        "",
        "- 未模型训练、未调参、未 LTR inference、未 LTR score 生成。",
        "- 未真实抓数、未 provider refresh/publish、未 qlib accepted latest switch。",
        "- 未 readonly/Agent publish。",
        "- 未策略收益回放、未 ReplayResult/NAV。",
        "- 未 broker/order/quick-trade，未生成 target_position/target_weight。",
        "",
        "## 7. DNG9 建议",
        "",
        "不建议进入会自动生成 Model B LTR signal 的 DNG9。可以进入 DNG9 daily auto model-signal gate integration 的前提是：只集成 gate/blocker 语义，并在 DNG3 仍为 blocked 时继续输出 `BLOCKED_INPUT_NOT_READY`；若要生成真实 LTR signal，必须先完成外部数据修复并重新通过 DNG3。",
        "",
    ]
    EXECUTION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXECUTION_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def run(asof: str, run_id: str, input_dir: Path) -> dict[str, Any]:
    score_dir = SCORE_BASE / run_id
    score_dir.mkdir(parents=True, exist_ok=True)

    input_manifest = read_json(input_dir / "manifest.json")
    input_readiness = read_json(input_dir / "blocker_input_readiness.json")
    if input_manifest.get("score_status") != BLOCKED_STATUS:
        raise RuntimeError("DNG8 runner currently only supports blocked gate artifacts unless full LTR readiness is proven")

    manifest = {
        "artifact_type": "ScoreJob",
        "schema_version": "dng8.modelb_ltr_score_job.v1",
        "model_id": MODEL_ID,
        "model_name": MODEL_ID,
        "model_family": "ltr",
        "run_id": run_id,
        "created_at": utc_now(),
        "created_by": "scripts/run_tw_modelb_ltr_score_job.py",
        "asof": asof,
        "status": BLOCKED_STATUS,
        "score_status": BLOCKED_STATUS,
        "model_b_ltr_ready": False,
        "fallback_allowed": FALLBACK_ALLOWED,
        "fallback_signal_artifact": rel(DNG7_MODELA_SIGNAL_DIR),
        "inference_input": rel(input_dir),
        "blocking_datasets": input_readiness.get("blocking_datasets", []),
        "blocker_reasons": input_readiness.get("blocker_reasons", []),
        "row_count": 0,
        "signal_artifact": None,
        "ltr_signal_generated": False,
        "qlib_score_used_as_ltr_score": False,
        "do_not_substitute_qlib_score_as_ltr_score": True,
        "source_model_artifact": rel(LTR_MODEL_ARTIFACT),
        "files": {
            "manifest": "manifest.json",
            "input_readiness": "input_readiness.json",
            "validator_report": "validator_report.json",
        },
        "omitted_files": {
            "raw_scores": "not generated because score_status=BLOCKED_INPUT_NOT_READY",
            "signals": "not generated because LTR input readiness is blocked",
            "rank_audit": "not generated because no LTR score exists",
        },
        "required_file_entries": [
            file_entry(input_dir / "manifest.json", "input_manifest"),
            file_entry(input_dir / "blocker_input_readiness.json", "blocker_input_readiness"),
            file_entry(input_dir / "source_readiness.json", "source_readiness"),
            file_entry(input_dir / "feature_lineage.json", "feature_lineage"),
            file_entry(input_dir / "pit_audit.csv", "pit_audit"),
            file_entry(LTR_MODEL_ARTIFACT, "ltr_model_artifact"),
            file_entry(DNG7_MODELA_SIGNAL_DIR / "manifest.json", "fallback_dng7_modela_manifest"),
            file_entry(DNG7_MODELA_SIGNAL_DIR / "signals.csv", "fallback_dng7_modela_signals"),
        ],
        "forbidden_actions": FORBIDDEN_ACTIONS_FALSE,
        "production_allowed": False,
        "not_published_latest": True,
    }
    write_json(score_dir / "manifest.json", manifest)

    score_input_readiness = {
        "status": BLOCKED_STATUS,
        "score_status": BLOCKED_STATUS,
        "model_id": MODEL_ID,
        "run_id": run_id,
        "asof": asof,
        "model_b_ltr_ready": False,
        "fallback_allowed": FALLBACK_ALLOWED,
        "fallback_signal_artifact": rel(DNG7_MODELA_SIGNAL_DIR),
        "blocking_datasets": input_readiness.get("blocking_datasets", []),
        "blocker_reasons": input_readiness.get("blocker_reasons", []),
        "do_not_substitute_qlib_score_as_ltr_score": True,
        "input_readiness_artifact": rel(input_dir / "blocker_input_readiness.json"),
        "input_dependencies": input_readiness.get("input_dependencies", {}),
        "forbidden_actions": FORBIDDEN_ACTIONS_FALSE,
    }
    write_json(score_dir / "input_readiness.json", score_input_readiness)

    validator_report = validate(score_dir, input_dir=input_dir, target_asof=asof, write_report=True)
    catalog = {
        "generated_at": utc_now(),
        "run_id": run_id,
        "asof": asof,
        "model_id": MODEL_ID,
        "pipeline_status": BLOCKED_STATUS,
        "score_status": BLOCKED_STATUS,
        "model_b_ltr_ready": False,
        "fallback_allowed": FALLBACK_ALLOWED,
        "fallback_signal_artifact": rel(DNG7_MODELA_SIGNAL_DIR),
        "model_b_signal_generated": False,
        "qlib_score_used_as_ltr_score": False,
        "mode": "BLOCKER_ARTIFACT_NO_INFERENCE",
        "validator": validator_report,
        "artifacts": {
            "model_inference_input": rel(input_dir),
            "score_job": rel(score_dir),
            "model_signal": None,
            "fallback_modela_signal": rel(DNG7_MODELA_SIGNAL_DIR),
        },
        "blocking_datasets": input_readiness.get("blocking_datasets", []),
        "blockers": input_readiness.get("blocker_reasons", []),
        "forbidden_actions": FORBIDDEN_ACTIONS_FALSE,
        "recommendation": "gate_only_go_dng9; external_source_repair_required_before_ltr_signal",
    }
    write_json(CATALOG_VALIDATION_PATH, catalog)
    write_execution_report(run_id, asof, input_dir, score_dir, input_manifest, input_readiness, validator_report)
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DNG8 Model B LTR ScoreJob gate or blocker artifact.")
    parser.add_argument("--asof", default=TARGET_ASOF)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--input-dir", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    input_dir = Path(args.input_dir) if args.input_dir else INPUT_BASE / args.run_id
    result = run(args.asof, args.run_id, input_dir)
    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print(f"{result['pipeline_status']} {result['artifacts']['score_job']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
