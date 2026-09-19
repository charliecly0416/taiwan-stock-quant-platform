#!/usr/bin/env python3
from __future__ import annotations

import difflib
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SIGNAL_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal"
TARGET_ASOF = "2026-08-07"
TARGET_RUN_ID = "option_c_daily_signal_20260807_fpale2_candidate_20260808T035113Z"
QLIB_ACCEPTED_LATEST = SIGNAL_ROOT / "latest_signal.json"
EVIDENCE_ROOT = ROOT / "data_tw/experiments/formal_provider_accepted_latest_exact_enablement"
PROTECTED_LATEST = {
    "qlib_accepted_latest": QLIB_ACCEPTED_LATEST,
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


def latest_payload(created_at: str) -> dict[str, Any]:
    return {
        "asof": TARGET_ASOF,
        "created_at": created_at,
        "diagnostic_only": True,
        "research_signal_not_order": True,
        "run_dir": f"data_tw/experiments/option_c_daily_signal/{TARGET_RUN_ID}",
        "status": "accepted",
        "top30_signals": f"data_tw/experiments/option_c_daily_signal/{TARGET_RUN_ID}/top30_signals.csv",
        "top50_signals": f"data_tw/experiments/option_c_daily_signal/{TARGET_RUN_ID}/top50_signals.csv",
    }


def validate_candidate() -> dict[str, Any]:
    sys.path.insert(0, str(BACKEND))
    from app.services.tw_stock_qlib_option_c import QlibOptionCSignalReader

    reader = QlibOptionCSignalReader(str(SIGNAL_ROOT))
    detail = reader.run_detail(TARGET_RUN_ID, bucket="all", enrich_trend=False)
    return {
        "candidate_dir_exists": (SIGNAL_ROOT / TARGET_RUN_ID).exists(),
        "candidate_file_list": sorted(p.name for p in (SIGNAL_ROOT / TARGET_RUN_ID).iterdir()),
        "reader": {
            "ok": detail.get("ok"),
            "status": detail.get("status"),
            "asof": detail.get("asof"),
            "run_id": detail.get("run_id"),
            "top30_count": detail.get("top30_count"),
            "top50_count": detail.get("top50_count"),
            "warnings": detail.get("warnings"),
            "trading": detail.get("trading"),
        },
    }


def validate_after_switch() -> dict[str, Any]:
    sys.path.insert(0, str(BACKEND))
    from app.services.tw_stock_qlib_option_c import QlibOptionCSignalReader

    reader = QlibOptionCSignalReader(str(SIGNAL_ROOT))
    latest_all = reader.latest(bucket="all", enrich_trend=False)
    latest_top30 = reader.latest(bucket="top30", enrich_trend=False)
    latest_top50 = reader.latest(bucket="top50", enrich_trend=False)
    detail = reader.run_detail(TARGET_RUN_ID, bucket="all", enrich_trend=False)
    return {
        "latest_all": {
            "ok": latest_all.get("ok"),
            "status": latest_all.get("status"),
            "asof": latest_all.get("asof"),
            "run_id": latest_all.get("run_id"),
            "top30_count": latest_all.get("top30_count"),
            "top50_count": latest_all.get("top50_count"),
            "warnings": latest_all.get("warnings"),
            "trading": latest_all.get("trading"),
        },
        "latest_top30": {
            "ok": latest_top30.get("ok"),
            "status": latest_top30.get("status"),
            "asof": latest_top30.get("asof"),
            "run_id": latest_top30.get("run_id"),
            "signals_count": len(latest_top30.get("signals") or []),
            "warnings": latest_top30.get("warnings"),
        },
        "latest_top50": {
            "ok": latest_top50.get("ok"),
            "status": latest_top50.get("status"),
            "asof": latest_top50.get("asof"),
            "run_id": latest_top50.get("run_id"),
            "signals_count": len(latest_top50.get("signals") or []),
            "warnings": latest_top50.get("warnings"),
        },
        "run_detail": {
            "ok": detail.get("ok"),
            "status": detail.get("status"),
            "asof": detail.get("asof"),
            "run_id": detail.get("run_id"),
            "top30_count": detail.get("top30_count"),
            "top50_count": detail.get("top50_count"),
            "warnings": detail.get("warnings"),
            "trading": detail.get("trading"),
        },
    }


def diff_payload(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    before_text = json.dumps(before, ensure_ascii=False, indent=2, sort_keys=True).splitlines()
    after_text = json.dumps(after, ensure_ascii=False, indent=2, sort_keys=True).splitlines()
    return list(difflib.unified_diff(before_text, after_text, fromfile="before/latest_signal.json", tofile="after/latest_signal.json", lineterm=""))


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    job_dir = EVIDENCE_ROOT / f"fpale4_actual_accepted_latest_switch_{stamp}"
    reports = job_dir / "reports"
    rollback_dir = job_dir / "rollback"
    reports.mkdir(parents=True, exist_ok=False)
    rollback_dir.mkdir(parents=True, exist_ok=False)

    candidate = validate_candidate()
    before = fingerprints()
    if before["qlib_accepted_latest"].get("asof") != "2026-08-06":
        summary = {
            "schema_version": "fpale4.actual_accepted_latest_pointer_switch.v1",
            "status": "blocked_unexpected_current_latest",
            "target_asof": TARGET_ASOF,
            "target_run_id": TARGET_RUN_ID,
            "candidate": candidate,
            "before_fingerprints": before,
        }
        write_json(reports / "execution_summary.json", summary)
        raise SystemExit(1)
    if candidate["reader"].get("ok") is not True or candidate["reader"].get("asof") != TARGET_ASOF:
        summary = {
            "schema_version": "fpale4.actual_accepted_latest_pointer_switch.v1",
            "status": "blocked_candidate_invalid",
            "target_asof": TARGET_ASOF,
            "target_run_id": TARGET_RUN_ID,
            "candidate": candidate,
            "before_fingerprints": before,
        }
        write_json(reports / "execution_summary.json", summary)
        raise SystemExit(1)

    rollback_path = rollback_dir / "latest_signal.before_fpale4.json"
    shutil.copy2(QLIB_ACCEPTED_LATEST, rollback_path)
    rollback = {
        "path": rel(rollback_path),
        "sha256": sha256_file(rollback_path),
        "matches_before": sha256_file(rollback_path) == before["qlib_accepted_latest"].get("sha256"),
    }
    if not rollback["matches_before"]:
        summary = {
            "schema_version": "fpale4.actual_accepted_latest_pointer_switch.v1",
            "status": "blocked_rollback_mismatch",
            "target_asof": TARGET_ASOF,
            "target_run_id": TARGET_RUN_ID,
            "candidate": candidate,
            "before_fingerprints": before,
            "rollback": rollback,
        }
        write_json(reports / "execution_summary.json", summary)
        raise SystemExit(1)

    created_at = utc_now()
    before_payload = load_json(QLIB_ACCEPTED_LATEST)
    after_payload = latest_payload(created_at)
    write_json(QLIB_ACCEPTED_LATEST, after_payload)
    after = fingerprints()
    switch_diff = diff_payload(before_payload, after_payload)
    validation = validate_after_switch()
    validations_ok = (
        validation["latest_all"].get("ok") is True
        and validation["latest_all"].get("asof") == TARGET_ASOF
        and validation["latest_all"].get("run_id") == TARGET_RUN_ID
        and validation["latest_top30"].get("signals_count") == 30
        and validation["latest_top50"].get("signals_count") == 50
        and validation["run_detail"].get("ok") is True
        and validation["run_detail"].get("asof") == TARGET_ASOF
        and validation["run_detail"].get("run_id") == TARGET_RUN_ID
    )
    protected_changes = {
        name: {"before": before[name], "after": after[name]}
        for name in before
        if before[name].get("sha256") != after[name].get("sha256")
    }
    if not validations_ok:
        shutil.copy2(rollback_path, QLIB_ACCEPTED_LATEST)
        after_rollback = fingerprints()
        summary = {
            "schema_version": "fpale4.actual_accepted_latest_pointer_switch.v1",
            "status": "failed_rolled_back",
            "target_asof": TARGET_ASOF,
            "target_run_id": TARGET_RUN_ID,
            "candidate": candidate,
            "before_fingerprints": before,
            "after_fingerprints": after_rollback,
            "rollback": rollback,
            "validation": validation,
            "diff": switch_diff,
            "protected_changes": protected_changes,
        }
        write_json(reports / "execution_summary.json", summary)
        raise SystemExit(1)

    summary = {
        "schema_version": "fpale4.actual_accepted_latest_pointer_switch.v1",
        "status": "pass",
        "created_at": created_at,
        "target_asof": TARGET_ASOF,
        "target_run_id": TARGET_RUN_ID,
        "candidate": candidate,
        "before_fingerprints": before,
        "after_fingerprints": after,
        "rollback": rollback,
        "validation": validation,
        "diff": switch_diff,
        "protected_changes": protected_changes,
        "forbidden_scope_audit": {
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
        },
    }
    write_json(reports / "execution_summary.json", summary)
    write_json(reports / "candidate_run_precheck.json", candidate)
    write_json(reports / "before_fingerprints.json", before)
    write_json(reports / "after_fingerprints.json", after)
    write_json(reports / "rollback.json", rollback)
    write_json(reports / "validation.json", validation)
    write_json(reports / "switch_diff.json", {"diff": switch_diff})
    write_json(reports / "forbidden_scope_audit.json", summary["forbidden_scope_audit"])
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
