#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SIGNAL_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal"
TARGET_ASOF = "2026-08-06"
TARGET_RUN_ID = "option_c_daily_signal_20260806_fpal4a_adapter_20260807T022328Z"
RUN_DIR = SIGNAL_ROOT / TARGET_RUN_ID
EVIDENCE_ROOT = ROOT / "data_tw/experiments/formal_provider_accepted_latest_productionization/fpal5_accepted_latest_pointer_switch_preflight_or_stop"
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


def validate_candidate() -> dict[str, Any]:
    sys.path.insert(0, str(BACKEND))
    from app.services.tw_stock_qlib_option_c import QlibOptionCSignalReader

    reader = QlibOptionCSignalReader(str(SIGNAL_ROOT))
    payload = reader.run_detail(TARGET_RUN_ID, bucket="all", enrich_trend=False)
    latest_doc = {
        "asof": TARGET_ASOF,
        "created_at": utc_now(),
        "diagnostic_only": True,
        "research_signal_not_order": True,
        "run_dir": f"data_tw/experiments/option_c_daily_signal/{TARGET_RUN_ID}",
        "status": "accepted",
        "top30_signals": f"data_tw/experiments/option_c_daily_signal/{TARGET_RUN_ID}/top30_signals.csv",
        "top50_signals": f"data_tw/experiments/option_c_daily_signal/{TARGET_RUN_ID}/top50_signals.csv",
    }
    return {
        "candidate_dir_exists": RUN_DIR.exists(),
        "candidate_file_list": sorted(p.name for p in RUN_DIR.iterdir()) if RUN_DIR.exists() else [],
        "target_asof": TARGET_ASOF,
        "target_run_id": TARGET_RUN_ID,
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
        "future_latest_payload": latest_doc,
    }


def main() -> int:
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    candidate = validate_candidate()
    before = fingerprints()
    future_scope = {
        "phase": "FPAL5_ACCEPTED_LATEST_POINTER_SWITCH_PREFLIGHT_OR_STOP",
        "actual_switch_executed": False,
        "target_asof": TARGET_ASOF,
        "target_run_id": TARGET_RUN_ID,
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
    rollback_plan = {
        "actual_switch_pre_write_steps": [
            "recapture qlib accepted latest before fingerprint",
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
    forbidden = {
        "actual_pointer_switch_executed": False,
        "accepted_latest_pointer_write": False,
        "legacy_latest_write": False,
        "provider_pull_or_refresh": False,
        "provider_publish": False,
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
    authorization = (
        "我确认执行 FPAL5 actual accepted latest pointer switch：target_asof=2026-08-06；"
        "target_run_id=option_c_daily_signal_20260806_fpal4a_adapter_20260807T022328Z；"
        "唯一允许写入 qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json；"
        "写前创建 rollback copy 和 before fingerprints；写后执行 after fingerprints、diff、"
        "QlibOptionCSignalReader latest/run_detail validation、latest payload validation 和 post-write review；"
        "保持 legacy latest、DAPR18 signal latest、readonly snapshot latest、Agent prompt latest 不动；"
        "不授权 provider pull/publish、qlib refresh、daily auto、accepted auto switch、OpenAI、DB、"
        "strategy replay、monitor/broker/order/target、frontend/API default switch；"
        "FPAL4A candidate 仅为本次一次性输入，不授权后续自动 latest switch。"
    )
    summary = {
        "schema_version": "fpal5.accepted_latest_pointer_switch_preflight.v1",
        "status": "pass" if candidate["reader"].get("ok") is True and candidate["reader"].get("asof") == TARGET_ASOF else "fail",
        "created_at": utc_now(),
        "target_asof": TARGET_ASOF,
        "target_run_id": TARGET_RUN_ID,
        "actual_switch_executed": False,
        "candidate": candidate,
        "protected_latest_before": before,
        "future_scope": future_scope,
        "rollback_and_validation_plan": rollback_plan,
        "forbidden_scope_audit": forbidden,
        "authorization_template": authorization,
    }
    write_json(EVIDENCE_ROOT / "candidate_run_precheck.json", candidate)
    write_json(EVIDENCE_ROOT / "protected_pointer_before_fingerprints.json", before)
    write_json(EVIDENCE_ROOT / "future_switch_scope.json", future_scope)
    write_json(EVIDENCE_ROOT / "rollback_and_validation_plan.json", rollback_plan)
    write_json(EVIDENCE_ROOT / "forbidden_scope_audit.json", forbidden)
    (EVIDENCE_ROOT / "future_exact_authorization_template.txt").write_text(authorization + "\n", encoding="utf-8")
    write_json(EVIDENCE_ROOT / "execution_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
