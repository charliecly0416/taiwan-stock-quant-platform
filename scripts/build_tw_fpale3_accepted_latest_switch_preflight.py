#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SIGNAL_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal"
EVIDENCE_ROOT = ROOT / "data_tw/experiments/formal_provider_accepted_latest_exact_enablement"
DEFAULT_TARGET_ASOF = "2026-08-07"
DEFAULT_TARGET_RUN_ID = "option_c_daily_signal_20260807_fpale2_candidate_20260808T035113Z"
PROTECTED_LATEST = {
    "qlib_accepted_latest": ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "legacy_latest": ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "dapr18_signal_latest": ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    "readonly_snapshot_latest": ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    "agent_prompt_latest": ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fingerprints() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, path in PROTECTED_LATEST.items():
        item: dict[str, Any] = {"path": rel(path), "exists": path.exists(), "sha256": sha256_file(path)}
        if path.exists() and path.suffix == ".json":
            try:
                payload = load_json(path)
                item["asof"] = payload.get("asof") or payload.get("signal_asof") or payload.get("target_asof")
                item["run_id"] = payload.get("run_id") or Path(str(payload.get("run_dir") or "")).name
            except Exception as exc:
                item["json_error"] = str(exc)
        out[name] = item
    return out


def validate_candidate(target_asof: str, target_run_id: str) -> dict[str, Any]:
    run_dir = SIGNAL_ROOT / target_run_id
    sys.path.insert(0, str(BACKEND))
    from app.services.tw_stock_qlib_option_c import QlibOptionCSignalReader

    reader = QlibOptionCSignalReader(str(SIGNAL_ROOT))
    payload = reader.run_detail(target_run_id, bucket="all", enrich_trend=False)
    future_latest_payload = {
        "asof": target_asof,
        "created_at": utc_now(),
        "diagnostic_only": True,
        "research_signal_not_order": True,
        "run_dir": f"data_tw/experiments/option_c_daily_signal/{target_run_id}",
        "status": "accepted",
        "top30_signals": f"data_tw/experiments/option_c_daily_signal/{target_run_id}/top30_signals.csv",
        "top50_signals": f"data_tw/experiments/option_c_daily_signal/{target_run_id}/top50_signals.csv",
    }
    return {
        "candidate_dir_exists": run_dir.exists(),
        "candidate_file_list": sorted(p.name for p in run_dir.iterdir()) if run_dir.exists() else [],
        "target_asof": target_asof,
        "target_run_id": target_run_id,
        "reader": {
            "ok": payload.get("ok"),
            "status": payload.get("status"),
            "asof": payload.get("asof"),
            "run_id": payload.get("run_id"),
            "top30_count": payload.get("top30_count"),
            "top50_count": payload.get("top50_count"),
            "warnings": payload.get("warnings"),
            "trading": payload.get("trading"),
        },
        "future_latest_payload": future_latest_payload,
    }


def exact_authorization_text(target_asof: str, target_run_id: str) -> str:
    return (
        f"我确认执行 FPALE4 actual accepted latest pointer switch：target_asof={target_asof}；"
        f"target_run_id={target_run_id}；"
        "唯一允许写入 qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json；"
        "写前创建 rollback copy 和 before fingerprints；写后执行 after fingerprints、diff、"
        "QlibOptionCSignalReader latest/run_detail validation、latest payload validation 和 post-write review；"
        "保持 legacy latest、DAPR18 signal latest、readonly snapshot latest、Agent prompt latest 不动；"
        "不授权 provider pull/publish、formal provider mutation、qlib refresh、daily auto、cron、OpenAI、DB、"
        "strategy replay、monitor/broker/order/target、frontend/API default switch；"
        "FPALE2 candidate 仅为本次一次性输入，不授权后续自动 latest switch。"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FPALE3 accepted latest switch preflight; no pointer writes.")
    parser.add_argument("--target-asof", default=DEFAULT_TARGET_ASOF)
    parser.add_argument("--target-run-id", default=DEFAULT_TARGET_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_asof = str(args.target_asof)
    target_run_id = str(args.target_run_id)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    job_dir = EVIDENCE_ROOT / f"fpale3_accepted_latest_switch_preflight_{target_asof.replace('-', '')}_{stamp}"
    reports = job_dir / "reports"
    reports.mkdir(parents=True, exist_ok=False)

    candidate = validate_candidate(target_asof, target_run_id)
    before = fingerprints()
    current_accepted = before["qlib_accepted_latest"]
    rollback_plan = {
        "actual_switch_pre_write_steps": [
            "recapture protected latest before fingerprints",
            "copy qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json to rollback file",
            "verify rollback sha256 equals before fingerprint",
        ],
        "actual_switch_write_steps": [
            "write only qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
            "payload must point to target_run_id and target_asof",
        ],
        "actual_switch_post_write_steps": [
            "capture after fingerprints",
            "diff before/after latest payload",
            "validate QlibOptionCSignalReader.latest(bucket=all/top30/top50)",
            "validate QlibOptionCSignalReader.run_detail(target_run_id, bucket=all)",
            "validate protected pointers except qlib accepted latest unchanged",
            "write post-write review",
        ],
    }
    future_scope = {
        "phase": "FPALE4_ACTUAL_ACCEPTED_LATEST_SWITCH_OR_STOP",
        "actual_switch_executed": False,
        "target_asof": target_asof,
        "target_run_id": target_run_id,
        "only_future_write_path": "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
        "keep_unchanged": [
            "data_tw/experiments/option_c_daily_signal/latest_signal.json",
            "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
            "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
            "data_tw/artifacts/agent_daily_prompt/latest.json",
        ],
        "requires_user_exact_authorization_before_write": True,
        "future_automatic_latest_switch_authorized": False,
    }
    forbidden = {
        "actual_pointer_switch_executed": False,
        "accepted_latest_pointer_write": False,
        "legacy_latest_write": False,
        "provider_pull_or_refresh": False,
        "formal_provider_mutation": False,
        "qlib_refresh": False,
        "daily_auto_manual_run": False,
        "cron_changed": False,
        "dapr18_product_latest_publish": False,
        "readonly_snapshot_latest_publish": False,
        "agent_prompt_latest_publish": False,
        "openai_call": False,
        "db_access_or_write": False,
        "strategy_replay": False,
        "monitor_broker_order_target": False,
        "frontend_api_default_switch": False,
        "future_automatic_latest_switch_authorized": False,
    }
    checks = {
        "candidate_dir_exists": candidate["candidate_dir_exists"] is True,
        "reader_ok": candidate["reader"].get("ok") is True,
        "reader_asof_matches_target": candidate["reader"].get("asof") == target_asof,
        "reader_run_id_matches_target": candidate["reader"].get("run_id") == target_run_id,
        "top30_count_30": candidate["reader"].get("top30_count") == 30,
        "top50_count_50": candidate["reader"].get("top50_count") == 50,
        "current_accepted_latest_still_previous_asof": current_accepted.get("asof") != target_asof,
        "current_accepted_latest_pointer_exists": current_accepted.get("exists") is True,
        "no_pointer_write_in_preflight": True,
        "exact_authorization_required": True,
    }
    authorization = exact_authorization_text(target_asof, target_run_id)
    summary = {
        "schema_version": "fpale3.accepted_latest_switch_preflight.v1",
        "status": "pass" if all(checks.values()) else "fail",
        "created_at": utc_now(),
        "target_asof": target_asof,
        "target_run_id": target_run_id,
        "actual_switch_executed": False,
        "checks": checks,
        "candidate": candidate,
        "protected_latest_before": before,
        "future_scope": future_scope,
        "rollback_and_validation_plan": rollback_plan,
        "forbidden_scope_audit": forbidden,
        "authorization_template": authorization,
        "next_gate": "FPALE4_ACTUAL_ACCEPTED_LATEST_SWITCH_OR_STOP",
    }
    write_json(reports / "candidate_run_precheck.json", candidate)
    write_json(reports / "protected_pointer_before_fingerprints.json", before)
    write_json(reports / "future_switch_scope.json", future_scope)
    write_json(reports / "rollback_and_validation_plan.json", rollback_plan)
    write_json(reports / "forbidden_scope_audit.json", forbidden)
    (reports / "future_exact_authorization_template.txt").write_text(authorization + "\n", encoding="utf-8")
    write_json(reports / "execution_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
