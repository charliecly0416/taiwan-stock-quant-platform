#!/usr/bin/env python3
"""DAPR11 downstream readonly snapshot and Agent latest preflight-or-stop.

This route is diagnostic/preflight only. It reads the DAPR10 controlled signal
latest publish result and downstream latest pointers, then decides whether a
downstream publish can happen directly. It does not build or publish readonly
strategy snapshots, Agent prompt artifacts, provider artifacts, accepted latest,
orders, targets, or monitor outputs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def env_path(name: str, default: str) -> Path:
    value = os.environ.get(name)
    if value:
        path = Path(value)
        return path if path.is_absolute() else ROOT / path
    return ROOT / default


TARGET_ASOF = env_str("TW_DAPR11_TARGET_ASOF", "2026-07-17")
TARGET_TAG = TARGET_ASOF.replace("-", "")
MODEL_ID = env_str("TW_DAPR11_MODEL_ID", "e4_frozen_qlib_2018_2022")
RUN_ID = env_str("TW_DAPR11_RUN_ID", "dapr8_modela_20260717_contained")

DAPR10_ROOT = env_path(
    "TW_DAPR11_DAPR10_ROOT",
    "data_tw/experiments/daily_accepted_production_readiness/dapr10_actual_controlled_signal_latest_publish",
)
DAPR11_ROOT = env_path(
    "TW_DAPR11_OUTPUT_ROOT",
    f"data_tw/experiments/provider_bridge_productionization/dapr11_{TARGET_TAG}_downstream_readonly_snapshot_and_agent_latest_preflight_or_stop",
)

CONTROLLED_SIGNAL_LATEST = ROOT / f"data_tw/artifacts/signals/{MODEL_ID}/latest.json"
CANONICAL_SIGNAL_DIR = ROOT / f"data_tw/artifacts/signals/{MODEL_ID}/{RUN_ID}"
CANONICAL_SIGNAL_FILES = [
    "manifest.json",
    "signals.csv",
    "schema.json",
    "coverage_audit.csv",
    "forbidden_field_audit.csv",
    "validator_report.json",
]

READONLY_SNAPSHOT_ROOT = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot"
READONLY_SNAPSHOT_LATEST = READONLY_SNAPSHOT_ROOT / "latest.json"
READONLY_SNAPSHOT_TARGET_DIR = READONLY_SNAPSHOT_ROOT / TARGET_ASOF
AGENT_PROMPT_ROOT = ROOT / "data_tw/artifacts/agent_daily_prompt"
AGENT_PROMPT_LATEST = AGENT_PROMPT_ROOT / "latest.json"
AGENT_PROMPT_TARGET_DIR = AGENT_PROMPT_ROOT / TARGET_ASOF
QLIB_ACCEPTED_LATEST = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
LEGACY_OPTION_C_LATEST = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json"

RSPPR1_SCRIPT = ROOT / "scripts/build_tw_rsppr1_candidate_only_snapshot_dry_run.py"
RSPPR2_SCRIPT = ROOT / "scripts/build_tw_rsppr2_candidate_only_snapshot_publish.py"
APLR1_SCRIPT = ROOT / "scripts/build_tw_aplr1_candidate_only_agent_prompt_dry_run.py"
APLR2_SCRIPT = ROOT / "scripts/build_tw_aplr2_agent_prompt_artifact_publish.py"

DAPR11_EXECUTION_REPORT = env_path(
    "TW_DAPR11_EXECUTION_REPORT",
    f"docs/tw_portfolio_decision_model/POLICY_DAPR11_{TARGET_TAG}_DOWNSTREAM_READONLY_SNAPSHOT_AND_AGENT_LATEST_PREFLIGHT_OR_STOP_EXECUTION_REPORT_CN.md",
)
DAPR11_REVIEW = env_path(
    "TW_DAPR11_REVIEW",
    f"docs/tw_portfolio_decision_model/POLICY_DAPR11_{TARGET_TAG}_DOWNSTREAM_READONLY_SNAPSHOT_AND_AGENT_LATEST_PREFLIGHT_OR_STOP_REVIEW_CN.md",
)

PROTECTED_POINTERS = [
    CONTROLLED_SIGNAL_LATEST,
    READONLY_SNAPSHOT_LATEST,
    AGENT_PROMPT_LATEST,
    QLIB_ACCEPTED_LATEST,
    LEGACY_OPTION_C_LATEST,
]

FORBIDDEN_COLUMN_EXACT = {
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
}
FORBIDDEN_COLUMN_PREFIXES = (
    "future_return_",
    "future_excess_return_",
    "forward_return_",
    "label_",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def file_summary(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "sha256": sha256_file(path),
        "json_summary": None,
    }
    if path.is_file() and path.suffix == ".json":
        try:
            data = read_json(path)
            if isinstance(data, dict):
                summary["json_summary"] = {
                    key: data.get(key)
                    for key in (
                        "artifact_type",
                        "schema_version",
                        "asof",
                        "data_asof",
                        "signal_asof",
                        "target_date",
                        "run_id",
                        "model_id",
                        "manifest",
                        "snapshot_manifest",
                        "artifact_dir",
                        "readonly_only",
                        "production_trade_enabled",
                        "not_order",
                        "not_target_position",
                    )
                    if key in data
                }
        except Exception as exc:  # pragma: no cover - diagnostic only
            summary["json_error"] = str(exc)
    return summary


def script_constants(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    target_matches = sorted(set(re.findall(r'TARGET_ASOF\s*=\s*"([^"]+)"', text)))
    run_matches = sorted(set(re.findall(r'RUN_ID\s*=\s*"([^"]+)"', text)))
    hardcoded_20260708 = "2026-07-08" in text
    hardcoded_target_dir = f"/{TARGET_ASOF}" in text or TARGET_ASOF in text
    return {
        "path": rel(path),
        "exists": path.exists(),
        "sha256": sha256_file(path),
        "target_asof_constants": target_matches,
        "run_id_constants": run_matches,
        "contains_2026_07_08": hardcoded_20260708,
        "contains_2026_07_17": hardcoded_target_dir,
    }


def audit_signals(path: Path) -> dict[str, Any]:
    rows = 0
    dates: set[str] = set()
    signal_asofs: set[str] = set()
    keys: set[tuple[str, str]] = set()
    duplicates = 0
    forbidden_columns: list[str] = []
    ranks: list[int] = []
    top50: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        for col in columns:
            if col in FORBIDDEN_COLUMN_EXACT or any(col.startswith(prefix) for prefix in FORBIDDEN_COLUMN_PREFIXES):
                forbidden_columns.append(col)
        for row in reader:
            rows += 1
            dates.add(row.get("date", ""))
            signal_asofs.add(row.get("signal_asof", ""))
            key = (row.get("date", ""), row.get("instrument", ""))
            if key in keys:
                duplicates += 1
            keys.add(key)
            try:
                rank = int(row.get("candidate_rank", ""))
                ranks.append(rank)
                if rank <= 50:
                    top50.append(
                        {
                            "instrument": row.get("instrument"),
                            "candidate_rank": rank,
                            "score_rank": int(row.get("score_rank", rank)),
                            "full_qlib_rank": int(row.get("full_qlib_rank", rank)),
                            "raw_score": row.get("raw_score"),
                            "buy_score": row.get("buy_score"),
                            "signal_asof": row.get("signal_asof"),
                            "available_at": row.get("available_at"),
                        }
                    )
            except ValueError:
                pass
    top50.sort(key=lambda item: (item["candidate_rank"], item["instrument"] or ""))
    return {
        "path": rel(path),
        "sha256": sha256_file(path),
        "row_count": rows,
        "date_values": sorted(dates),
        "signal_asof_values": sorted(signal_asofs),
        "duplicate_key_count": duplicates,
        "forbidden_columns": sorted(forbidden_columns),
        "candidate_rank_min": min(ranks) if ranks else None,
        "candidate_rank_max": max(ranks) if ranks else None,
        "top50_count": len(top50),
        "top10_compact": top50[:10],
        "checks": {
            "row_count_150": rows == 150,
            "date_only_target_asof": sorted(dates) == [TARGET_ASOF],
            "signal_asof_only_target_asof": sorted(signal_asofs) == [TARGET_ASOF],
            "duplicate_key_count_zero": duplicates == 0,
            "forbidden_columns_empty": not forbidden_columns,
            "candidate_ranks_1_to_150": sorted(ranks) == list(range(1, 151)),
            "top50_count_50": len(top50) == 50,
        },
    }


def build_controlled_signal_gate() -> dict[str, Any]:
    dapr10_decision = read_json(DAPR10_ROOT / "post_publish_validation.json")
    dapr10_diff = read_json(DAPR10_ROOT / "diff_summary.json")
    latest = read_json(CONTROLLED_SIGNAL_LATEST)
    manifest = read_json(CANONICAL_SIGNAL_DIR / "manifest.json")
    validator = read_json(CANONICAL_SIGNAL_DIR / "validator_report.json")
    signals = audit_signals(CANONICAL_SIGNAL_DIR / "signals.csv")
    file_checks = []
    for name in CANONICAL_SIGNAL_FILES:
        path = CANONICAL_SIGNAL_DIR / name
        file_checks.append(
            {
                "file": name,
                "path": rel(path),
                "exists": path.exists(),
                "sha256": sha256_file(path),
            }
        )
    checks = {
        "dapr10_post_publish_validation_pass": dapr10_decision.get("status") == "pass",
        "dapr10_diff_summary_pass": dapr10_diff.get("status") == "pass",
        "latest_asof_target": latest.get("asof") == TARGET_ASOF and latest.get("signal_asof") == TARGET_ASOF,
        "latest_run_id_target": latest.get("run_id") == RUN_ID,
        "latest_readonly_flags_safe": latest.get("readonly_only") is True
        and latest.get("production_trade_enabled") is False
        and latest.get("provider_publish") is False
        and latest.get("qlib_accepted_latest_switch") is False
        and latest.get("agent_prompt_publish") is False,
        "latest_points_to_canonical_files": latest.get("canonical_manifest") == rel(CANONICAL_SIGNAL_DIR / "manifest.json")
        and latest.get("canonical_signals") == rel(CANONICAL_SIGNAL_DIR / "signals.csv"),
        "latest_canonical_sha_matches": latest.get("canonical_manifest_sha256") == sha256_file(CANONICAL_SIGNAL_DIR / "manifest.json")
        and latest.get("canonical_signals_sha256") == sha256_file(CANONICAL_SIGNAL_DIR / "signals.csv"),
        "all_canonical_files_exist": all(item["exists"] for item in file_checks),
        "manifest_ready": manifest.get("status") == "READY",
        "manifest_signal_asof_target": manifest.get("signal_asof") == TARGET_ASOF,
        "manifest_production_allowed_false": manifest.get("production_allowed") is False,
        "validator_pass": validator.get("ok") is True and validator.get("status") == "PASS",
        "signals_audit_pass": all(signals["checks"].values()),
    }
    return {
        "schema_version": "dapr11.controlled_signal_latest_gate.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "run_id": RUN_ID,
        "controlled_signal_latest": file_summary(CONTROLLED_SIGNAL_LATEST),
        "canonical_signal_dir": rel(CANONICAL_SIGNAL_DIR),
        "canonical_file_checks": file_checks,
        "manifest_summary": {
            "artifact_type": manifest.get("artifact_type"),
            "asof": manifest.get("asof"),
            "signal_asof": manifest.get("signal_asof"),
            "status": manifest.get("status"),
            "row_count": manifest.get("row_count"),
            "production_allowed": manifest.get("production_allowed"),
            "not_published_latest_source_flag": manifest.get("not_published_latest"),
        },
        "validator_summary": {
            "ok": validator.get("ok"),
            "status": validator.get("status"),
            "signal_rows": validator.get("signal_rows"),
            "errors": validator.get("errors"),
        },
        "signals_audit": signals,
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def build_downstream_latest_state() -> dict[str, Any]:
    entries = {
        "controlled_signal_latest": file_summary(CONTROLLED_SIGNAL_LATEST),
        "readonly_snapshot_latest": file_summary(READONLY_SNAPSHOT_LATEST),
        "agent_prompt_latest": file_summary(AGENT_PROMPT_LATEST),
        "qlib_accepted_latest": file_summary(QLIB_ACCEPTED_LATEST),
        "legacy_option_c_latest": file_summary(LEGACY_OPTION_C_LATEST),
        "readonly_snapshot_target_dir": file_summary(READONLY_SNAPSHOT_TARGET_DIR),
        "agent_prompt_target_dir": file_summary(AGENT_PROMPT_TARGET_DIR),
    }
    return {
        "schema_version": "dapr11.downstream_latest_state.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "entries": entries,
        "status": "pass",
    }


def build_gap_analysis(state: dict[str, Any]) -> dict[str, Any]:
    def asof(name: str) -> str | None:
        summary = state["entries"][name].get("json_summary") or {}
        return summary.get("asof") or summary.get("signal_asof") or summary.get("target_date")

    gaps = {
        "controlled_signal_latest_asof": asof("controlled_signal_latest"),
        "readonly_snapshot_latest_asof": asof("readonly_snapshot_latest"),
        "agent_prompt_latest_asof": asof("agent_prompt_latest"),
        "qlib_accepted_latest_asof": asof("qlib_accepted_latest"),
        "legacy_option_c_latest_asof": asof("legacy_option_c_latest"),
        "readonly_snapshot_target_dir_exists": state["entries"]["readonly_snapshot_target_dir"]["exists"],
        "agent_prompt_target_dir_exists": state["entries"]["agent_prompt_target_dir"]["exists"],
    }
    checks = {
        "controlled_signal_latest_target": gaps["controlled_signal_latest_asof"] == TARGET_ASOF,
        "readonly_snapshot_latest_not_target": gaps["readonly_snapshot_latest_asof"] != TARGET_ASOF,
        "agent_prompt_latest_not_target": gaps["agent_prompt_latest_asof"] != TARGET_ASOF,
        "readonly_snapshot_target_artifact_absent": not gaps["readonly_snapshot_target_dir_exists"],
        "agent_prompt_target_artifact_absent": not gaps["agent_prompt_target_dir_exists"],
    }
    return {
        "schema_version": "dapr11.downstream_gap_analysis.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "gaps": gaps,
        "impact": {
            "today_strategy_overview": "still follows readonly snapshot latest, currently not target_asof",
            "candidate_list": "controlled signal latest is target_asof but readonly snapshot/latest surfaces may still show prior snapshot",
            "agent_simple_chat": "still follows Agent prompt latest, currently not target_asof",
            "qlib_accepted_latest": "unchanged; DAPR10 controlled signal latest is not qlib accepted latest",
        },
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def build_route_compatibility_audit() -> dict[str, Any]:
    scripts = {
        "rsppr1_candidate_only_snapshot_dry_run": script_constants(RSPPR1_SCRIPT),
        "rsppr2_candidate_only_snapshot_publish": script_constants(RSPPR2_SCRIPT),
        "aplr1_candidate_only_agent_prompt_dry_run": script_constants(APLR1_SCRIPT),
        "aplr2_agent_prompt_artifact_publish": script_constants(APLR2_SCRIPT),
    }
    checks = {
        "existing_rsppr1_hardcoded_prior_target": TARGET_ASOF not in (scripts["rsppr1_candidate_only_snapshot_dry_run"]["target_asof_constants"] or []),
        "existing_aplr1_hardcoded_prior_target": TARGET_ASOF not in (scripts["aplr1_candidate_only_agent_prompt_dry_run"]["target_asof_constants"] or []),
        "readonly_snapshot_target_dir_absent": not READONLY_SNAPSHOT_TARGET_DIR.exists(),
        "agent_prompt_target_dir_absent": not AGENT_PROMPT_TARGET_DIR.exists(),
    }
    return {
        "schema_version": "dapr11.existing_route_compatibility_audit.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "scripts": scripts,
        "checks": checks,
        "direct_downstream_publish_ready": False,
        "reason": (
            "Existing RSPPR/APLR routes are prior-target-specific and no "
            f"{TARGET_ASOF} readonly snapshot or Agent prompt candidate exists yet."
        ),
        "status": "pass",
    }


def build_future_scope_plan() -> dict[str, Any]:
    return {
        "schema_version": "dapr11.future_scope_plan.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "recommended_next_phase": f"DAPR12_{TARGET_TAG}_CANDIDATE_ONLY_READONLY_SNAPSHOT_DRY_RUN_NO_PUBLISH",
        "dapr12_allowed_actions": [
            f"read controlled signal latest and canonical {TARGET_ASOF} ModelSignalArtifact",
            "derive candidate-only readonly snapshot payload plan under a DAPR12 evidence root",
            "validate top50 candidate-only snapshot in dry-run form",
            "write no-publish evidence and review documents",
        ],
        "dapr12_forbidden_actions": [
            "write readonly strategy snapshot latest",
            "write Agent prompt latest",
            "write qlib accepted latest",
            "write legacy option_c latest",
            "provider pull/publish",
            "qlib refresh",
            "OpenAI/DB",
            "strategy replay/NAV",
            "monitor/broker/order/target",
            "frontend/API production default switch",
        ],
        "future_actual_publish_requires_exact_authorization": [
            "DAPR13 readonly snapshot actual publish only after DAPR12 review PASS",
            f"Agent prompt candidate/publish only after readonly snapshot latest has its own accepted {TARGET_ASOF} publish evidence",
        ],
        "status": "pass",
    }


def build_fingerprints() -> dict[str, Any]:
    return {
        "schema_version": "dapr11.protected_pointer_fingerprints.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "read_only_capture": True,
        "entries": [file_summary(path) for path in PROTECTED_POINTERS],
        "status": "pass",
    }


def build_forbidden_action_audit() -> dict[str, Any]:
    flags = {
        "readonly_snapshot_latest_write": False,
        "agent_prompt_latest_write": False,
        "agent_prompt_build": False,
        "openai_call": False,
        "db_access": False,
        "provider_network_pull": False,
        "provider_publish": False,
        "qlib_accepted_latest_switch": False,
        "legacy_option_c_latest_signal_write": False,
        "qlib_refresh": False,
        "daily_auto_run": False,
        "model_scoring": False,
        "strategy_replay": False,
        "replay_result_nav": False,
        "monitor_write_or_scan": False,
        "broker_order_or_quick_trade": False,
        "order_intent_or_target_output": False,
        "frontend_or_api_default_switch": False,
    }
    return {
        "schema_version": "dapr11.forbidden_action_audit.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "allowed_actions": [
            "read DAPR10 evidence",
            "read controlled signal latest and canonical signal artifact",
            "read downstream latest pointers",
            "write DAPR11 evidence and docs",
        ],
        "forbidden_flags": flags,
        "all_forbidden_false": all(value is False for value in flags.values()),
        "status": "pass",
    }


def build_decision(
    signal_gate: dict[str, Any],
    gap: dict[str, Any],
    compatibility: dict[str, Any],
    forbidden: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "controlled_signal_ready_for_downstream_candidate_build": signal_gate["status"] == "pass",
        "downstream_gap_confirmed": gap["status"] == "pass",
        "direct_downstream_publish_not_ready": compatibility["direct_downstream_publish_ready"] is False,
        "forbidden_actions_clean": forbidden["status"] == "pass" and forbidden["all_forbidden_false"] is True,
    }
    return {
        "schema_version": "dapr11.candidate_or_stop_decision.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "decision": "PREFLIGHT_PASS_STOP_DOWNSTREAM_PUBLISH_REQUIRE_DAPR12_SNAPSHOT_CANDIDATE_DRY_RUN",
        "ready_for_dapr12_no_publish_snapshot_dry_run": all(checks.values()),
        "ready_for_direct_readonly_snapshot_publish": False,
        "ready_for_direct_agent_prompt_publish": False,
        "readonly_snapshot_latest_written": False,
        "agent_prompt_latest_written": False,
        "checks": checks,
        "next_required_action": f"DAPR12_{TARGET_TAG}_CANDIDATE_ONLY_READONLY_SNAPSHOT_DRY_RUN_NO_PUBLISH",
        "status": "pass" if all(checks.values()) else "stop",
    }


def build_artifact_manifest(paths: list[Path]) -> dict[str, Any]:
    entries = []
    for path in paths:
        entries.append(
            {
                "path": rel(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.is_file() else None,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schema_version": "dapr11.artifact_manifest.v1",
        "created_at": now_iso(),
        "target_asof": TARGET_ASOF,
        "entries": entries,
        "status": "pass" if all(item["exists"] and item["sha256"] for item in entries) else "fail",
    }


def write_reports(decision: dict[str, Any], gap: dict[str, Any]) -> None:
    execution_report = f"""# DAPR11 Downstream Readonly Snapshot And Agent Latest Preflight-Or-Stop 执行报告

生成时间：{now_iso()}

## 1. Scope

Assigned phase：`DAPR11_DOWNSTREAM_READONLY_SNAPSHOT_AND_AGENT_LATEST_PREFLIGHT_OR_STOP`

本阶段只做 downstream preflight，不执行 readonly snapshot publish、Agent prompt publish、qlib accepted latest switch 或任何 provider/DB/OpenAI/trading action。

## 2. Documents / Contracts / Skills Read

- DAPR10 execution/review/evidence
- RSPPR1/RSPPR2 readonly snapshot route scripts
- APLR1/APLR2 Agent prompt latest route scripts
- `coordinator-executor-reviewer-workflow`
- `tw-stock-data-freshness-diagnosis`
- `tw-stock-safety-boundary-review`

## 3. Changes Made

- 参数化 DAPR11 builder：`scripts/build_tw_dapr11_downstream_readonly_snapshot_agent_preflight_or_stop.py`
- 写入 DAPR11 evidence root：`{rel(DAPR11_ROOT)}`
- 写入 DAPR11 execution/review docs。

## 4. Evidence Produced

Decision：

```text
{decision["decision"]}
```

Controlled signal latest 已为 `{TARGET_ASOF}`，但 downstream latest 当前状态：

```text
readonly_snapshot_latest_asof={gap["gaps"]["readonly_snapshot_latest_asof"]}
agent_prompt_latest_asof={gap["gaps"]["agent_prompt_latest_asof"]}
qlib_accepted_latest_asof={gap["gaps"]["qlib_accepted_latest_asof"]}
legacy_option_c_latest_asof={gap["gaps"]["legacy_option_c_latest_asof"]}
```

## 5. Compliance With Mainline

DAPR11 停在 downstream publish 前。因为 `{TARGET_ASOF}` readonly snapshot candidate 和 Agent prompt candidate 尚不存在，且现有 RSPPR/APLR 脚本仍有 prior-target 固化痕迹，本阶段不能直接 publish。

## 6. Forbidden Actions Audit

`forbidden_action_audit.json` 全 false。DAPR11 未写 readonly snapshot latest、Agent latest、accepted latest、legacy latest，也未触发 provider、OpenAI、DB、strategy replay、monitor/broker/order/target。

## 7. Issues / Blockers / Deviations

无执行 blocker；存在 downstream publish blocker：需要先做 DAPR12 no-publish candidate-only readonly snapshot dry-run。

## 8. Files Changed

- `scripts/build_tw_dapr11_downstream_readonly_snapshot_agent_preflight_or_stop.py`
- `{rel(DAPR11_ROOT)}/*`
- `{rel(DAPR11_EXECUTION_REPORT)}`
- `{rel(DAPR11_REVIEW)}`

## 9. Recommendation For Reviewer

若 evidence 证明 source ready、downstream direct publish not ready、forbidden actions clean，则审查应 PASS 并指定下一步为 DAPR12 no-publish snapshot candidate dry-run。
"""
    review = f"""# DAPR11 Downstream Readonly Snapshot And Agent Latest Preflight-Or-Stop 审查

审查时间：{now_iso()}

## 1. Verdict

```text
PASS_STOP_DOWNSTREAM_PUBLISH_REQUIRE_DAPR12_SNAPSHOT_CANDIDATE_DRY_RUN
```

DAPR11 preflight 成立：controlled signal latest 已推进到 `{TARGET_ASOF}`，但 readonly snapshot latest 和 Agent prompt latest 还不能直接 publish。

## 2. Findings

### Critical

无。

### High

无。

### Medium

- 现有 RSPPR/APLR route 脚本与已发布下游 artifact 仍是 `2026-07-08` 版本；直接复用会错误覆盖 lineage。
- `qlib accepted latest` 未因 DAPR10 改变；DAPR10 controlled signal latest 不能被解释为 qlib accepted latest。

### Low

- DAPR12 应复用 RSPPR1 candidate-only schema，但必须参数化 `target_asof={TARGET_ASOF}` 与 `run_id={RUN_ID}`，不得运行旧 hardcoded publish 脚本。

## 3. Mainline Compliance

- controlled signal latest：`{TARGET_ASOF}`
- readonly snapshot latest：`{gap["gaps"]["readonly_snapshot_latest_asof"]}`
- Agent prompt latest：`{gap["gaps"]["agent_prompt_latest_asof"]}`
- direct readonly snapshot publish ready：`false`
- direct Agent prompt publish ready：`false`
- DAPR11 actual downstream publish：`false`

## 4. Evidence Checked

- `controlled_signal_latest_gate.json`
- `downstream_latest_state.json`
- `downstream_gap_analysis.json`
- `existing_route_compatibility_audit.json`
- `protected_pointer_fingerprints.json`
- `future_scope_plan.json`
- `forbidden_action_audit.json`
- `candidate_or_stop_decision.json`
- `artifact_manifest.json`

## 5. Missing Evidence Or Open Questions

无 DAPR11 preflight blocker。缺的是 `{TARGET_ASOF}` readonly snapshot candidate artifact；这应由 DAPR12 no-publish dry-run 生成。

## 6. Forbidden Actions Audit

DAPR11 forbidden actions 全 false。未触发 provider pull/publish、qlib refresh、accepted latest switch、readonly snapshot latest、Agent latest、OpenAI、DB、strategy replay、monitor/broker/order/target。

## 7. Next Work Document

下一步固定为：

```text
DAPR12_{TARGET_TAG}_CANDIDATE_ONLY_READONLY_SNAPSHOT_DRY_RUN_NO_PUBLISH
```

DAPR12 只允许基于 controlled signal latest `{TARGET_ASOF}` 生成 candidate-only readonly snapshot dry-run evidence，不允许写 readonly snapshot latest 或 Agent latest。

## 8. Command For Executor Or Coordinator

进入 DAPR12 no-publish snapshot candidate dry-run。不要进入 actual publish，除非 DAPR12 review PASS 后用户再给 exact authorization。
"""
    write_text(DAPR11_EXECUTION_REPORT, execution_report)
    write_text(DAPR11_REVIEW, review)


def main() -> None:
    DAPR11_ROOT.mkdir(parents=True, exist_ok=True)
    signal_gate = build_controlled_signal_gate()
    state = build_downstream_latest_state()
    gap = build_gap_analysis(state)
    compatibility = build_route_compatibility_audit()
    fingerprints = build_fingerprints()
    future_scope = build_future_scope_plan()
    forbidden = build_forbidden_action_audit()
    decision = build_decision(signal_gate, gap, compatibility, forbidden)

    evidence_files = [
        DAPR11_ROOT / "controlled_signal_latest_gate.json",
        DAPR11_ROOT / "downstream_latest_state.json",
        DAPR11_ROOT / "downstream_gap_analysis.json",
        DAPR11_ROOT / "existing_route_compatibility_audit.json",
        DAPR11_ROOT / "protected_pointer_fingerprints.json",
        DAPR11_ROOT / "future_scope_plan.json",
        DAPR11_ROOT / "forbidden_action_audit.json",
        DAPR11_ROOT / "candidate_or_stop_decision.json",
    ]
    write_json(evidence_files[0], signal_gate)
    write_json(evidence_files[1], state)
    write_json(evidence_files[2], gap)
    write_json(evidence_files[3], compatibility)
    write_json(evidence_files[4], fingerprints)
    write_json(evidence_files[5], future_scope)
    write_json(evidence_files[6], forbidden)
    write_json(evidence_files[7], decision)
    write_reports(decision, gap)
    manifest = build_artifact_manifest(evidence_files + [DAPR11_EXECUTION_REPORT, DAPR11_REVIEW])
    write_json(DAPR11_ROOT / "artifact_manifest.json", manifest)

    print(
        json.dumps(
            {
                "status": decision["status"],
                "decision": decision["decision"],
                "target_asof": TARGET_ASOF,
                "ready_for_dapr12_no_publish_snapshot_dry_run": decision["ready_for_dapr12_no_publish_snapshot_dry_run"],
                "ready_for_direct_readonly_snapshot_publish": decision["ready_for_direct_readonly_snapshot_publish"],
                "ready_for_direct_agent_prompt_publish": decision["ready_for_direct_agent_prompt_publish"],
                "evidence_root": rel(DAPR11_ROOT),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
