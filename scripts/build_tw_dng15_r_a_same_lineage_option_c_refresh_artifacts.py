#!/usr/bin/env python3
"""Build DNG15_R-A same-lineage Option C refresh evidence artifacts."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ASOF = "2026-06-26"
MODEL_ID = "e4_frozen_qlib_2018_2022"
OPS_ROOT = ROOT / "data_tw/experiments/dng15_r_a_option_c_ops"
PROXY_JOB = OPS_ROOT / "dng15_r_a_option_c_yahoo_scrapling_refresh_20260626"
NOPROXY_JOB = OPS_ROOT / "dng15_r_a_option_c_yahoo_scrapling_refresh_20260626_noproxy"
DECISION_PATH = ROOT / "data_tw/catalog/dng15_r_a_same_lineage_option_c_refresh_decision.json"
READINESS_PATH = ROOT / "data_tw/catalog/dng15_r_a_modela_20260626_candidate_readiness.json"
REPORT_PATH = ROOT / "docs/tw_data_governance/DNG15_R_A_SAME_LINEAGE_OPTION_C_REFRESH_EXECUTION_REPORT_CN.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path | str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def attempt_summary(job_dir: Path, label: str) -> dict[str, Any]:
    summary = read_json(job_dir / "reports/execution_summary.json")
    fetch = read_json(job_dir / "reports/fetch_report.json")
    validation = read_json(job_dir / "reports/normalized_validation.json")
    return {
        "label": label,
        "job_dir": rel(job_dir),
        "execution_status": summary.get("status", "missing"),
        "fetch_status": fetch.get("status", "missing"),
        "proxy_used": fetch.get("proxy_used"),
        "proxy": fetch.get("proxy", ""),
        "symbols_expected": fetch.get("symbols_expected", 0),
        "symbols_success": fetch.get("symbols_success", 0),
        "symbols_empty_count": len(fetch.get("symbols_empty") or []),
        "http_status_counts": fetch.get("http_status_counts", {}),
        "normalized_validation_status": validation.get("status", "missing"),
        "symbols_with_asof": validation.get("symbols_with_asof", 0),
        "files_found": validation.get("files_found", 0),
        "errors": summary.get("errors", []),
        "formal_provider_mutated": summary.get("formal_provider_mutated", False),
        "formal_normalized_mutated": summary.get("formal_normalized_mutated", False),
        "latest_signal_updated": summary.get("latest_signal_updated", False),
    }


def classify_blocker(primary: dict[str, Any]) -> str:
    counts = {str(k): int(v) for k, v in (primary.get("http_status_counts") or {}).items()}
    if counts.get("403", 0) > 0:
        return "yahoo_scrapling_fetch_failed_http_403"
    if primary.get("symbols_success", 0) == 0:
        return "yahoo_scrapling_fetch_failed"
    return "normalized_validation_failed"


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    generated_at = utc_now()
    proxy_attempt = attempt_summary(PROXY_JOB, "proxy_http_127_0_0_1_7890")
    noproxy_attempt = attempt_summary(NOPROXY_JOB, "noproxy_real_network")
    primary = noproxy_attempt
    blocker = classify_blocker(primary)
    summary = read_json(NOPROXY_JOB / "reports/execution_summary.json")
    fetch = read_json(NOPROXY_JOB / "reports/fetch_report.json")
    validation = read_json(NOPROXY_JOB / "reports/normalized_validation.json")
    provider = read_json(NOPROXY_JOB / "reports/provider_validation.json")
    smoke = read_json(NOPROXY_JOB / "reports/model_smoke.json")

    forbidden_actions = {
        "formal_publish": False,
        "accepted_latest_switch": False,
        "latest_signal_update": False,
        "readonly_latest_publish": False,
        "agent_latest_publish": False,
        "production_switch": False,
        "trading": False,
        "target_position_or_target_weight": False,
        "finmind_fallback": False,
        "mixed_provider_bridge": False,
        "model_training_or_tuning": False,
    }

    decision = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "asof": ASOF,
        "route": "DNG15_R-A_same_lineage_yahoo_scrapling_option_c_staged_refresh",
        "decision": "NO_STAGED_CANDIDATE_FETCH_BLOCKED",
        "status": "blocked",
        "blocker": blocker,
        "job_dir": rel(NOPROXY_JOB),
        "candidate_normalized_path": rel(summary.get("candidate_dir") or (NOPROXY_JOB / "candidate_normalized")),
        "staged_provider_path": rel(summary.get("staged_provider") or (NOPROXY_JOB / "staged_qlib_bin")),
        "fetch_status": fetch.get("status", "missing"),
        "normalized_validation_status": validation.get("status", "missing"),
        "provider_validation_status": provider.get("status", "not_run"),
        "model_smoke_status": smoke.get("status", "not_run"),
        "symbols_expected": fetch.get("symbols_expected", 150),
        "symbols_success": fetch.get("symbols_success", 0),
        "symbols_with_asof": validation.get("symbols_with_asof", 0),
        "calendar_has_asof": bool(provider.get("calendar_has_asof", False)),
        "prediction_rows": int(smoke.get("prediction_rows", 0) or 0),
        "finite_prediction_share": float(smoke.get("finite_prediction_share", 0.0) or 0.0),
        "production_allowed": False,
        "publish_latest_authorized": False,
        "formal_provider_mutated": bool(summary.get("formal_provider_mutated", False)),
        "formal_normalized_mutated": bool(summary.get("formal_normalized_mutated", False)),
        "latest_signal_updated": bool(summary.get("latest_signal_updated", False)),
        "forbidden_actions": forbidden_actions,
        "attempts": [proxy_attempt, noproxy_attempt],
        "notes": [
            "Proxy attempt failed because http://127.0.0.1:7890 was unavailable.",
            "Sandbox no-proxy attempt hit DNS resolution failure before the escalated real-network retry.",
            "Escalated no-proxy retry reached Yahoo chart API but received HTTP 403 for all 150 symbols.",
            "No dry-run-publish was run because staged refresh did not become ready.",
        ],
        "next_recommended_route": "DNG15_R_A_REPAIR_OR_COORDINATOR_DECISION_FOR_PROXY_RETRY",
    }

    readiness = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "asof": ASOF,
        "model_id": MODEL_ID,
        "candidate_input_status": "BLOCKED_CANDIDATE_NORMALIZED_NOT_READY",
        "staged_provider_calendar_max": provider.get("calendar_max"),
        "staged_provider_calendar_has_asof": bool(provider.get("calendar_has_asof", False)),
        "candidate_normalized_symbols_with_asof": validation.get("symbols_with_asof", 0),
        "candidate_model_smoke_status": smoke.get("status", "not_run"),
        "score_generated": False,
        "formal_provider_unchanged": decision["formal_provider_mutated"] is False,
        "latest_signal_unchanged": decision["latest_signal_updated"] is False,
        "production_allowed": False,
        "publish_latest_authorized": False,
        "blockers": [blocker, "candidate_normalized_symbols_success_0_of_150"],
        "source_attempts": [proxy_attempt, noproxy_attempt],
        "artifacts": {
            "execution_summary": rel(NOPROXY_JOB / "reports/execution_summary.json"),
            "fetch_report": rel(NOPROXY_JOB / "reports/fetch_report.json"),
            "normalized_validation": rel(NOPROXY_JOB / "reports/normalized_validation.json"),
            "staged_refresh_report": rel(NOPROXY_JOB / "reports/staged_refresh_report.md"),
        },
    }
    return decision, readiness


def write_report(decision: dict[str, Any], readiness: dict[str, Any]) -> None:
    proxy_attempt, noproxy_attempt = decision["attempts"]
    lines = [
        "# DNG15_R-A Same-Lineage Option C Refresh 执行报告",
        "",
        f"生成时间：{decision['generated_at']}",
        "",
        "## 1. Scope",
        "",
        "- Assigned phase：`DNG15_R-A same-lineage Yahoo/Scrapling Option C staged refresh`",
        "- Mainline document：`docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`",
        "- Work document：`docs/tw_data_governance/DNG15_R_A_SAME_LINEAGE_OPTION_C_REFRESH_WORK_CN.md`",
        f"- Target asof：`{ASOF}`",
        "- Model：`e4_frozen_qlib_2018_2022`",
        "",
        "非目标确认：未 formal publish、未切 accepted latest、未更新 latest_signal、未 publish readonly/Agent latest、未生产切换、未交易、未生成 target_position/target_weight、未使用 FinMind fallback 或 mixed-provider bridge。",
        "",
        "## 2. Documents / Contracts / Skills Read",
        "",
        "- `docs/tw_data_governance/DNG15_R_A_SAME_LINEAGE_OPTION_C_REFRESH_WORK_CN.md`",
        "- `docs/tw_data_governance/DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR_EXECUTION_REPORT_CN.md`",
        "- `docs/tw_data_governance/DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR_REVIEW_CN.md`",
        "- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`",
        "- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`（工作区 `.agents/skills/...` 路径不存在，已读取同名技能实际路径）",
        "",
        "## 3. Changes Made",
        "",
        "- 新增 `scripts/build_tw_dng15_r_a_same_lineage_option_c_refresh_artifacts.py`。",
        "- 生成 `data_tw/catalog/dng15_r_a_same_lineage_option_c_refresh_decision.json`。",
        "- 生成 `data_tw/catalog/dng15_r_a_modela_20260626_candidate_readiness.json`。",
        "- 生成本执行报告。",
        "",
        "## 4. Evidence Produced",
        "",
        "### 4.1 Proxy staged refresh",
        "",
        f"- job_dir：`{proxy_attempt['job_dir']}`",
        f"- execution_status：`{proxy_attempt['execution_status']}`",
        f"- fetch_status：`{proxy_attempt['fetch_status']}`",
        f"- symbols_success：`{proxy_attempt['symbols_success']}/{proxy_attempt['symbols_expected']}`",
        f"- proxy_used：`{proxy_attempt['proxy_used']}`",
        f"- http_status_counts：`{proxy_attempt['http_status_counts']}`",
        "",
        "结论：`http://127.0.0.1:7890` 不可用，Scrapling 报 connection refused；未产生 candidate normalized 文件。",
        "",
        "### 4.2 No-proxy real-network staged refresh",
        "",
        f"- job_dir：`{noproxy_attempt['job_dir']}`",
        f"- execution_status：`{noproxy_attempt['execution_status']}`",
        f"- fetch_status：`{noproxy_attempt['fetch_status']}`",
        f"- symbols_success：`{noproxy_attempt['symbols_success']}/{noproxy_attempt['symbols_expected']}`",
        f"- symbols_with_asof：`{noproxy_attempt['symbols_with_asof']}/{noproxy_attempt['symbols_expected']}`",
        f"- http_status_counts：`{noproxy_attempt['http_status_counts']}`",
        "",
        "结论：升级网络后 Yahoo chart API 可达，但 150 支标的的 `.TW`/`.TWO` 请求均返回 HTTP 403；未产生 staged qlib provider 或 Model A smoke。",
        "",
        "### 4.3 Required artifacts",
        "",
        f"- Decision：`{rel(DECISION_PATH)}`",
        f"- Candidate readiness：`{rel(READINESS_PATH)}`",
        f"- Refresh report：`docs/tw_data_governance/DNG15_R_A_OPTION_C_STAGED_REFRESH_REPORT_CN.md`",
        "",
        "## 5. Compliance With Mainline",
        "",
        f"- decision：`{decision['decision']}`",
        f"- blocker：`{decision['blocker']}`",
        f"- candidate_normalized symbols_success：`{decision['symbols_success']}/{decision['symbols_expected']}`",
        f"- candidate_normalized symbols_with_asof：`{decision['symbols_with_asof']}/{decision['symbols_expected']}`",
        f"- staged calendar_has_asof：`{decision['calendar_has_asof']}`",
        f"- model_smoke_status：`{decision['model_smoke_status']}`",
        f"- production_allowed：`{decision['production_allowed']}`",
        "",
        "## 6. Forbidden Actions Audit",
        "",
        "- `formal_provider_mutated=false`",
        "- `formal_normalized_mutated=false`",
        "- `latest_signal_updated=false`",
        "- `publish_latest_authorized=false`",
        "- `production_allowed=false`",
        "- 未运行 `--mode publish`，未运行 dry-run-publish，因为 staged refresh 未 ready。",
        "- 未使用 FinMind fallback 或 mixed-provider bridge。",
        "- 未触发交易、订单、target_position 或 target_weight。",
        "",
        "## 7. Issues / Blockers / Deviations",
        "",
        f"- `blocker={decision['blocker']}`：Yahoo/Scrapling same-lineage fetch 在真实网络下被 Yahoo 403 拒绝。",
        "- 工作区指定的 `.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md` 不存在；已读取 `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`。",
        "",
        "## 8. Files Changed",
        "",
        "- `scripts/build_tw_dng15_r_a_same_lineage_option_c_refresh_artifacts.py`",
        "- `docs/tw_data_governance/DNG15_R_A_OPTION_C_STAGED_REFRESH_REPORT_CN.md`",
        "- `docs/tw_data_governance/DNG15_R_A_SAME_LINEAGE_OPTION_C_REFRESH_EXECUTION_REPORT_CN.md`",
        "- `data_tw/catalog/dng15_r_a_same_lineage_option_c_refresh_decision.json`",
        "- `data_tw/catalog/dng15_r_a_modela_20260626_candidate_readiness.json`",
        "- `data_tw/experiments/dng15_r_a_option_c_ops/dng15_r_a_option_c_yahoo_scrapling_refresh_20260626*/reports/*`",
        "",
        "## 9. Recommendation For Reviewer",
        "",
        "不建议进入 DNG15_R-B。当前缺少 2026-06-26 same-lineage candidate normalized 和 staged provider candidate；建议先由统筹决定更换可用 proxy / 增加 Yahoo fetch 方案 / 或授权新的 repair 路线。",
        "",
        "## 10. Readiness Snapshot",
        "",
        "```json",
        json.dumps(readiness, ensure_ascii=False, indent=2, default=str),
        "```",
        "",
    ]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    decision, readiness = build()
    write_json(DECISION_PATH, decision)
    write_json(READINESS_PATH, readiness)
    write_report(decision, readiness)
    print(json.dumps({"decision": decision["decision"], "blocker": decision["blocker"], "report": rel(REPORT_PATH)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
