#!/usr/bin/env python3
"""Daily unattended Taiwan stock data + qlib Option C update.

This single entrypoint is meant for cron/systemd:
1. Pick the asof date automatically in Asia/Taipei.
2. Update QuantDinger raw Taiwan stock archives from FinMind.
3. In the default M3 contract path, skip legacy Yahoo/Scrapling provider refresh/publish.
4. Optionally run legacy provider publish/latest only behind an explicit non-default gate.

Research-only: no broker connection, no order generation, no positions.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import traceback
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_tw_model_b_hsa8_isolated_handoff_wiring as hsa8
import finmind_logical_acquisition as logical_acquisition
from tw_hsa8_downstream_gate import (
    DOWNSTREAM_KINDS,
    HSA8_FAILURE_SCENARIOS,
    DownstreamCallRecorder,
    run_hsa8_downstream_orchestration,
    run_hsa8_validated_downstream_orchestration,
    run_hsa8_failure_scenario,
)
from tw_daily_runtime_stages import (
    build_authorized_readonly_publish_terminal,
    build_legacy_observation_terminal,
    build_stage_terminal_contract,
    build_stage_facade,
    no_publish_fingerprint_audit,
    run_stage_orchestrator,
    runtime_truth,
)
from tw_daily_stage_adapters import build_named_stage_adapters, stage_contract_summary
from tw_daily_model_a_signal_shadow import run_daily_model_a_signal_shadow
from tw_daily_model_tracks import run_daily_model_tracks
from tw_daily_model_track_services import (
    build_model_track_services,
    capture_b19_twii_snapshot,
)
from tw_daily_readonly_snapshot_shadow import run_daily_readonly_snapshot_shadow
from tw_daily_workflow_readonly_shadow import run_daily_workflow_readonly_shadow
from tw_research_data_history import materialize_daily_research_history

# ARCH-2: the descriptor is the single source for runtime model identity and
# baseline policy.  Legacy orchestration functions below remain unchanged and
# continue to own ordering/failure behavior during the incremental migration.
RUNTIME_TRUTH = runtime_truth()

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
QLIB = ROOT / "qlib_pipeline"
OPS_ROOT = ROOT / "data_tw/ops/daily_auto_update"
FINMIND_SEGMENT_CACHE_ROOT = OPS_ROOT / "finmind_segment_cache"
FINMIND_ORTHOGONAL_BATCH_STATE_ROOT = OPS_ROOT / "finmind_orthogonal_batch_state"
FINMIND_LOGICAL_ACQUISITION_ROOT = OPS_ROOT / "finmind_logical_acquisition_runs"
UNIVERSE = QLIB / "data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt"
LATEST = QLIB / "data_tw/experiments/option_c_daily_signal/latest_signal.json"
CALENDAR = QLIB / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
INSTRUMENTS = QLIB / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt"
PENDING_ASOF = OPS_ROOT / "pending_asof.json"
TERMINAL_PENDING_QUARANTINE_ROOT = OPS_ROOT / "terminal_pending_quarantine"
WORKFLOW_READONLY_SHADOW_SPEC = ROOT / "configs/workflows/replay_window_observation.yaml"
WORKFLOW_READONLY_SHADOW_RUNNER = ROOT / "scripts/run_tw_stock_workflow.py"
WORKFLOW_MODELA_SIGNAL_SHADOW_SPEC = (
    ROOT / "configs/workflows/research_history_observation.yaml"
)
WORKFLOW_MODELA_SIGNAL_SHADOW_RUNNER = ROOT / "scripts/run_tw_stock_workflow.py"
WORKFLOW_READONLY_SNAPSHOT_SHADOW_SPEC = (
    ROOT / "configs/workflows/readonly_strategy_snapshot_observation.yaml"
)
WORKFLOW_READONLY_SNAPSHOT_SHADOW_RUNNER = ROOT / "scripts/run_tw_stock_workflow.py"
INSTALLED_DAILY_CRON = OPS_ROOT / "tw-daily-auto-update.installed.cron"
READONLY_SNAPSHOT_ROOT = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot"
READONLY_SNAPSHOT_LATEST = READONLY_SNAPSHOT_ROOT / "latest.json"
AGENT_DAILY_PROMPT_ROOT = ROOT / "data_tw/artifacts/agent_daily_prompt"
AGENT_DAILY_PROMPT_LATEST = AGENT_DAILY_PROMPT_ROOT / "latest.json"
CONTROLLED_MODEL_SIGNAL_ROOT = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022"
CONTROLLED_MODEL_SIGNAL_LATEST = CONTROLLED_MODEL_SIGNAL_ROOT / "latest.json"
READONLY_DAILY_INTEGRATION_AUDIT = READONLY_SNAPSHOT_ROOT / "daily_integration_audit.json"
READONLY_PUBLISH_SCRIPT = ROOT / "scripts/publish_tw_modular_readonly_snapshot.py"
READONLY_VALIDATE_SCRIPT = ROOT / "scripts/validate_tw_modular_readonly_snapshot.py"
AGENT_DAILY_PROMPT_BUILD_SCRIPT = ROOT / "scripts/build_tw_agent_daily_prompt_artifact.py"
AGENT_DAILY_PROMPT_VALIDATE_SCRIPT = ROOT / "scripts/validate_tw_agent_daily_prompt_artifact.py"
QALD_ACCEPTED_LATEST_CANDIDATE_BUILDER_SCRIPT = ROOT / "scripts/build_tw_fpale2_accepted_latest_candidate.py"
READONLY_DEFAULT_TIMEOUT_SECONDS = 300
DATA_CATALOG_DASHBOARD_BUILD_SCRIPT = ROOT / "scripts/build_tw_daily_readiness_dashboard.py"
DATA_CATALOG_DASHBOARD_VALIDATE_SCRIPT = ROOT / "scripts/validate_tw_daily_readiness_dashboard.py"
DATA_CATALOG_DASHBOARD = ROOT / "data_tw/catalog/daily_readiness_dashboard.json"
DNG6_DATA_CATALOG_DASHBOARD_VALIDATION = ROOT / "data_tw/catalog/dng6_daily_readiness_dashboard_validation.json"
MODELA_INPUT_BUILD_SCRIPT = ROOT / "scripts/build_tw_model_inference_input.py"
MODELA_SCORE_JOB_SCRIPT = ROOT / "scripts/run_tw_model_score_job.py"
DNG15_R_B_ISOLATED_MODELA_SCORE_BUILD_SCRIPT = ROOT / "scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py"
MODELB_LTR_INPUT_BUILD_SCRIPT = ROOT / "scripts/build_tw_modelb_ltr_inference_input.py"
MODELB_LTR_SCORE_JOB_SCRIPT = ROOT / "scripts/run_tw_modelb_ltr_score_job.py"
DAPR9_CONTROLLED_LATEST_PREFLIGHT_SCRIPT = ROOT / "scripts/build_tw_dapr9_controlled_latest_publish_preflight_or_stop.py"
DAPR10_CONTROLLED_SIGNAL_LATEST_PUBLISH_SCRIPT = ROOT / "scripts/build_tw_dapr10_actual_controlled_signal_latest_publish.py"
DAPR11_DOWNSTREAM_PREFLIGHT_SCRIPT = ROOT / "scripts/build_tw_dapr11_downstream_readonly_snapshot_agent_preflight_or_stop.py"
DAPR12_READONLY_SNAPSHOT_CANDIDATE_SCRIPT = ROOT / "scripts/build_tw_dapr12_candidate_only_readonly_snapshot_dry_run_no_publish.py"
DAPR13_READONLY_SNAPSHOT_PUBLISH_SCRIPT = ROOT / "scripts/build_tw_dapr13_actual_readonly_snapshot_publish.py"
DAPR14_AGENT_PROMPT_PREFLIGHT_SCRIPT = ROOT / "scripts/build_tw_dapr14_agent_prompt_latest_preflight_or_stop.py"
DAPR15_AGENT_PROMPT_CANDIDATE_SCRIPT = ROOT / "scripts/build_tw_dapr15_candidate_only_agent_prompt_dry_run_no_publish.py"
DAPR16_AGENT_PROMPT_PUBLISH_PREFLIGHT_SCRIPT = ROOT / "scripts/build_tw_dapr16_controlled_agent_prompt_publish_preflight_or_stop.py"
DAPR17_AGENT_PROMPT_PUBLISH_SCRIPT = ROOT / "scripts/build_tw_dapr17_actual_controlled_agent_prompt_publish.py"
MODEL_SIGNAL_GATE_DRY_RUN_DIR = OPS_ROOT / "dng9_model_signal_gate_dry_run"
MODEL_SIGNAL_GATE_DRY_RUN_SUMMARY = MODEL_SIGNAL_GATE_DRY_RUN_DIR / "model_signal_gate_summary.json"
DNG9_MODEL_SIGNAL_GATE_VALIDATION = ROOT / "data_tw/catalog/dng9_model_signal_gate_validation.json"
DNG15_R_A_R_READINESS = ROOT / "data_tw/catalog/dng15_r_a_r_modela_20260626_candidate_readiness.json"
DNG15_R_A_R_DECISION = ROOT / "data_tw/catalog/dng15_r_a_r_yahoo_access_repair_decision.json"
DNG15_R_B_ISOLATED_MODELA_VALIDATION = ROOT / "data_tw/catalog/dng15_r_b_isolated_modela_score_integration_validation.json"
DNG16_DAILY_AUTO_MODELA_VALIDATION = ROOT / "data_tw/catalog/dng16_daily_auto_model_score_integration_design_validation.json"
DNG16_DAILY_AUTO_MODELA_EXECUTION_REPORT = ROOT / "docs/tw_data_governance/DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN_EXECUTION_REPORT_CN.md"
DNG15_R_A_R_ARTIFACT_BUILD_SCRIPT = ROOT / "scripts/build_tw_dng15_r_a_r_yahoo_access_repair_artifacts.py"
DNG17_PROVIDER_CANDIDATE_REFRESH_SCRIPT = QLIB / "examples/tw/run_option_c_yahoo_scrapling_refresh.py"
DNG17_PROVIDER_CANDIDATE_ROOT = QLIB / "data_tw/experiments/daily_auto_provider_candidates"
DAPR18_MBCDS3_DAILY_SHADOW_ADAPTER = ROOT / "scripts/run_tw_mbcds3_daily_shadow_accumulation.py"
MBCDS3_DAILY_SHADOW_ACCUMULATOR_BUILDER = ROOT / "scripts/build_tw_mbcds3_shadow_accumulator.py"
MBCDS3_DAILY_SHADOW_ROOT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow"
MBCDS3_DAILY_SHADOW_DEFAULT_ACCUMULATOR = MBCDS3_DAILY_SHADOW_ROOT / "mbcds3_daily_auto_accumulator"
MBCDS3_DAILY_SHADOW_DEFAULT_INVENTORY_NAME = "mbcds3_compatibility_inventory.csv"
B19R2R_DAILY_SHADOW_RUNNER = ROOT / "scripts/run_modelb_b19r2r_daily_shadow.py"
B19R2R_TWII_CAPTURE_RUNNER = ROOT / "scripts/capture_modelb_b19r2r_twii_yahoo_v2.py"
MBCDS35_FEATURE_BUILDER = ROOT / "scripts/build_tw_mbcds2_isolated_feature_input.py"
MBCDS35_FROZEN_SCORER = ROOT / "scripts/run_tw_mbcds35_compatibility_frozen_scorer.py"
MBCDS35_LEDGER = ROOT / "scripts/build_tw_mbcds35_prospective_oos_ledger.py"
MBCDS35_OUTCOME_BUILDER = ROOT / "scripts/build_tw_mbcds35_outcome_candidate.py"
MBCDS35_DEFAULT_LEDGER = MBCDS3_DAILY_SHADOW_ROOT / "mbcds35_prospective_oos_ledger"
O4_NONBLOCKING_ADAPTER = ROOT / "scripts/run_modelb_o4_prospective_shadow_nonblocking.py"
O4_PROSPECTIVE_LEDGER = ROOT / "data_tw/experiments/project_runtime_convergence/o4_prospective_shadow_ledger/observations.csv"
FPALA_OUTPUT_ROOT = ROOT / "data_tw/experiments/formal_provider_accepted_latest_automation_alignment"
MODELA_MODEL_ID = RUNTIME_TRUTH.active_model_id
MODELB_LTR_MODEL_ID = str((RUNTIME_TRUTH.shadow() or {}).get("canonical_id") or "")
STRATEGY_RULE = RUNTIME_TRUTH.strategy_rule
EXECUTION_PRICE_MODE = RUNTIME_TRUTH.execution_price_mode
MODELB_LEGACY_COMPATIBILITY = {
    "model_id": MODELB_LTR_MODEL_ID,
    "status": "AVAILABLE_READONLY",
    "evidence_class": "legacy_exploratory",
    "usage": "readonly_comparison",
    "formal_oos_eligible": False,
    "production_default_eligible": False,
    "strict_retrain_or_new_scoring_eligible": False,
}
STRICT_E4_SIGNAL_ROOT = ROOT / "data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals"
STRICT_E4_YZ2_BUILD_SCRIPT = ROOT / "scripts/build_phase_yz2_orthogonal_package.py"
STRICT_E4_YZ2R_BUILD_SCRIPT = ROOT / "scripts/build_phase_yz2r_execution_price_readiness.py"
STRICT_E4_MODEL_B_SUBDIR = "model_b_yz2"
STRICT_E4_DEFAULT_TIMEOUT_SECONDS = 600
MODEL_SIGNAL_GATE_DEFAULT_TIMEOUT_SECONDS = 1800
MODEL_SIGNAL_GATE_SCHEMA_VERSION = "dng9.model_signal_gate_summary.v1"
MODEL_SIGNAL_GATE_FORBIDDEN_ACTIONS_FALSE = {
    "real_data_fetch_triggered": False,
    "provider_refresh_triggered": False,
    "provider_publish_triggered": False,
    "publish_latest_gate": False,
    "accepted_latest_switch_triggered": False,
    "qlib_accepted_latest_switched": False,
    "latest_signal_updated": False,
    "readonly_latest_published": False,
    "agent_prompt_published": False,
    "production_default_model_or_strategy_switched": False,
    "model_training_triggered": False,
    "model_tuning_triggered": False,
    "strategy_replay_triggered": False,
    "replay_result_nav_generated": False,
    "broker_order_quick_trade_triggered": False,
    "target_position_or_weight_generated": False,
    "finmind_fallback": False,
    "mixed_provider_bridge": False,
}
DAILY_FULL_CAPTURE_ACCOUNTING_SCHEMA_VERSION = "daily_full_capture_accounting_v1"
DAILY_FULL_CAPTURE_CATEGORIES = [
    "stock_ohlcv_adjusted_price",
    "twii_market_index",
    "finmind_raw_daily_price",
    "institutional_flow",
    "margin_short",
    "orthogonal_raw_archive",
    "daily_ltr_source_freshness",
    "readonly_price_twii_calendar_bridge",
    "execution_price_readiness",
    "schema_coverage_holiday_pending_evidence",
]
DAILY_FULL_CAPTURE_FIELDS = [
    "target_asof",
    "dataset_category",
    "source_boundary",
    "source_max_date",
    "available_at",
    "fetched_at",
    "row_count",
    "symbol_count",
    "checksum",
    "schema_version",
    "market_calendar_status",
    "holiday_name",
    "pending_reason",
    "retry_hint",
    "status",
    "status_reason",
    "requires_credentials",
    "requires_network",
    "requires_provider_refresh",
    "requires_formal_write",
    "requires_latest_switch",
]
DNG13_DAILY_CHAIN_STATUS_SCHEMA_VERSION = "dng13.daily_chain_status.v1"
DNG13_SKIPPED_ASOF_LEDGER_SCHEMA_VERSION = "dng13.skipped_asof_ledger.v1"
PBPR0_DAILY_CHAIN_REQUIRED_INPUTS = [
    "raw_daily_source_inventory",
    "formal_qlib_calendar_or_validated_provider_bridge",
    "model_inference_input",
    "score_job",
    "model_signal_artifact",
]
PBPR0_REFINED_PROVIDER_BLOCKER = {
    "blocked_at": "validated_provider_candidate_or_existing_isolated_modela_artifact",
    "reason": "no_validated_target_asof_provider_candidate_or_bridge_or_modela_artifact",
}
DNG13_REQUIRED_CHAIN_FIELDS = [
    "asof",
    "job_id",
    "state",
    "required_inputs",
    "refined_blocker",
    "provider_bridge_readiness_state",
    "is_trading_day",
    "data_window_status",
    "raw_status",
    "normalized_status",
    "price_store_status",
    "market_feature_status",
    "orthogonal_feature_status",
    "qlib_provider_view_status",
    "model_a_inference_input_status",
    "model_a_score_status",
    "model_a_signal_status",
    "model_b_ltr_status",
    "strategy_input_bundle_status",
    "replay_input_bundle_status",
    "readonly_source_context_status",
    "agent_source_context_status",
    "frontend_payload_status",
    "publish_latest_gate_status",
    "pending_asof_status",
    "next_retry_hint",
    "blocked_at",
    "blocker_reason",
    "next_required_action",
    "forbidden_actions",
]


def load_local_env() -> None:
    """Load root/backend .env for cron without overriding explicit env."""
    for env_path in (ROOT / ".env", BACKEND / ".env"):
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            os.environ[key] = value


load_local_env()
PYTHON = os.getenv("TW_DAILY_AUTO_PYTHON", sys.executable)
TAIPEI = ZoneInfo("Asia/Taipei")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def taipei_today() -> str:
    return taipei_now().date().isoformat()


def taipei_now() -> datetime:
    return datetime.now(TAIPEI).replace(microsecond=0)


def parse_hhmm(raw: str) -> time:
    try:
        parsed = datetime.strptime(raw.strip(), "%H:%M")
    except ValueError as exc:
        raise ValueError(f"Invalid HH:MM time: {raw!r}") from exc
    return parsed.time()


def should_wait_before_pull(
    *,
    asof: str,
    asof_source: str,
    now_taipei: datetime,
    today_earliest_time: time,
    force: bool,
) -> tuple[bool, str]:
    if force:
        return False, ""
    if asof_source not in {"taipei_today", "terminal_pending_catchup"}:
        return False, ""
    today = now_taipei.date()
    if asof != today.isoformat():
        return False, ""
    if today.weekday() >= 5:
        return True, "weekend_no_pending_wait"
    if now_taipei.time() < today_earliest_time:
        return True, "today_data_window_wait"
    return False, ""


def resolve_asof(explicit_asof: str) -> tuple[str, str]:
    if explicit_asof.strip():
        return explicit_asof.strip(), "explicit"
    pending = read_json(PENDING_ASOF)
    pending_asof = str(pending.get("asof") or "").strip()
    if pending_asof:
        return pending_asof, "pending"
    return taipei_today(), "taipei_today"


def next_weekday_after(raw: str) -> str:
    value = date.fromisoformat(raw) + timedelta(days=1)
    while value.weekday() >= 5:
        value += timedelta(days=1)
    return value.isoformat()


def classify_terminal_pending(pending: dict[str, Any]) -> dict[str, Any]:
    """Classify only completed evidence failures as terminal."""
    result = {"terminal": False, "reason": "retryable_or_unproven"}
    if str(pending.get("reason") or "") != "same_run_handoff_failed":
        return result
    job_id = str(pending.get("job_id") or "").strip()
    if not job_id or Path(job_id).name != job_id:
        return {"terminal": False, "reason": "invalid_job_id"}
    job_path = OPS_ROOT / job_id / "job.json"
    job = read_json(job_path)
    if str(job.get("status") or "") != "same_run_handoff_failed":
        return {"terminal": False, "reason": "job_status_not_terminal_handoff"}
    handoff = job.get("same_run_handoff") if isinstance(job.get("same_run_handoff"), dict) else {}
    error = str(handoff.get("error") or "")
    if not any(marker in error for marker in ("validator_not_PASS", "pit_status_not_PASS")):
        return {"terminal": False, "reason": "handoff_error_retryable", "handoff_error": error}
    state_raw = str(job.get("logical_acquisition_state_path") or "").strip()
    state_path = resolve_path(state_raw) if state_raw else Path()
    state = read_json(state_path) if state_raw else {}
    if state.get("status") != "COMPLETE" or state.get("handoff_allowed") is not True:
        return {"terminal": False, "reason": "logical_acquisition_not_complete", "handoff_error": error}
    return {
        "terminal": True,
        "reason": "complete_capture_evidence_gate_terminal",
        "handoff_error": error,
        "job_id": job_id,
        "job_path": rel_path(job_path),
        "logical_state_path": rel_path(state_path),
    }


def quarantine_terminal_pending(pending: dict[str, Any], decision: dict[str, Any], *, now_taipei: datetime) -> dict[str, Any]:
    asof = str(pending.get("asof") or "").strip()
    job_id = str(pending.get("job_id") or "").strip()
    if not asof or not job_id or not decision.get("terminal"):
        raise ValueError("terminal pending quarantine requires an exact terminal decision")
    TERMINAL_PENDING_QUARANTINE_ROOT.mkdir(parents=True, exist_ok=True)
    archived = TERMINAL_PENDING_QUARANTINE_ROOT / f"{asof}_{job_id}.pending.json"
    review = TERMINAL_PENDING_QUARANTINE_ROOT / f"{asof}_{job_id}.quarantine.json"
    if archived.exists() or review.exists():
        raise FileExistsError(f"terminal pending quarantine already exists: {archived}")
    os.replace(PENDING_ASOF, archived)
    quarantined_at = utc_now()
    payload = {
        "schema_version": "tw_daily_auto_terminal_pending_quarantine.v1",
        "status": "quarantined_terminal_evidence_blocker",
        "asof": asof,
        "job_id": job_id,
        "quarantined_at": quarantined_at,
        "original_pending_path": rel_path(archived),
        "decision": decision,
        "protected_latest_changed": False,
    }
    write_json(review, payload)
    catchup = next_weekday_after(asof)
    if catchup <= now_taipei.date().isoformat():
        write_json(PENDING_ASOF, {
            "asof": catchup,
            "reason": "terminal_pending_catchup",
            "job_id": job_id,
            "updated_at": quarantined_at,
            "quarantined_asof": asof,
            "quarantine_record": rel_path(review),
        })
        payload["catchup_asof"] = catchup
    return payload


def resolve_asof_with_terminal_quarantine(explicit_asof: str, *, now_taipei: datetime) -> tuple[str, str, dict[str, Any]]:
    if explicit_asof.strip():
        return explicit_asof.strip(), "explicit", {}
    pending = read_json(PENDING_ASOF)
    pending_asof = str(pending.get("asof") or "").strip()
    if not pending_asof:
        return now_taipei.date().isoformat(), "taipei_today", {}
    decision = classify_terminal_pending(pending)
    if not decision.get("terminal"):
        return pending_asof, "pending", {"pending_decision": decision}
    quarantine = quarantine_terminal_pending(pending, decision, now_taipei=now_taipei)
    catchup = str(quarantine.get("catchup_asof") or "")
    if catchup:
        return catchup, "terminal_pending_catchup", {"terminal_pending_quarantine": quarantine}
    return now_taipei.date().isoformat(), "taipei_today", {"terminal_pending_quarantine": quarantine}


def set_pending_asof(asof: str, *, reason: str, job_id: str) -> None:
    write_json(PENDING_ASOF, {
        "asof": asof,
        "reason": reason,
        "job_id": job_id,
        "updated_at": utc_now(),
    })


def clear_pending_asof(asof: str) -> None:
    pending = read_json(PENDING_ASOF)
    if str(pending.get("asof") or "") == asof:
        try:
            PENDING_ASOF.unlink()
        except FileNotFoundError:
            pass


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def file_fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {"exists": False, "path": rel_path(path), "size": 0, "sha256": "", "mtime": ""}
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "exists": True,
        "path": rel_path(path),
        "size": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat(),
    }


def calendar_tail(path: Path, limit: int = 5) -> list[str]:
    if not path.exists():
        return []
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows[-limit:]


def calendar_max_date(path: Path) -> str:
    tail = calendar_tail(path, limit=1)
    return tail[-1] if tail else ""


def instrument_count(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if raw and not raw.startswith("#"):
            count += 1
    return count


def parse_stdout_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except Exception:
        return []


def is_iso_date_like(value: str) -> bool:
    try:
        datetime.strptime(str(value or ""), "%Y-%m-%d")
    except ValueError:
        return False
    return True


def latest_existing_job_for_asof(asof: str, *, exclude_job_id: str = "") -> Path | None:
    if not OPS_ROOT.exists():
        return None
    prefix = f"daily_tw_stock_auto_update_{asof.replace('-', '')}_"
    candidates = [
        path
        for path in OPS_ROOT.glob(f"{prefix}*/job.json")
        if path.parent.name != exclude_job_id
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]


def source_inventory_for_chain(job: dict[str, Any], *, job_dir: Path) -> dict[str, dict[str, Any]]:
    inventory = job.get("daily_source_inventory") if isinstance(job.get("daily_source_inventory"), dict) else {}
    if inventory:
        return inventory
    inventory_payload = read_json(job_dir / "daily_source_inventory.json")
    sources = inventory_payload.get("sources") if isinstance(inventory_payload.get("sources"), dict) else {}
    return sources


def accounting_rows_for_chain(job: dict[str, Any], *, job_dir: Path) -> list[dict[str, str]]:
    accounting = job.get("daily_full_capture_accounting") if isinstance(job.get("daily_full_capture_accounting"), dict) else {}
    json_path = resolve_path(str(accounting.get("json_path") or job_dir / "daily_full_capture_accounting.json"))
    payload = read_json(json_path)
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    if rows:
        return [row for row in rows if isinstance(row, dict)]
    csv_path = resolve_path(str(accounting.get("csv_path") or job_dir / "daily_full_capture_accounting.csv"))
    return accounting_rows_for_chain_from_csv(csv_path)


def accounting_rows_for_chain_from_csv(path: Path) -> list[dict[str, str]]:
    return read_csv_dicts(path)


def accounting_row_by_category(rows: list[dict[str, str]], category: str) -> dict[str, str]:
    for row in rows:
        if row.get("dataset_category") == category:
            return row
    return {}


def raw_evidence_from_prior_job(asof: str, *, exclude_job_id: str = "") -> dict[str, Any]:
    if not OPS_ROOT.exists():
        return {}
    prefix = f"daily_tw_stock_auto_update_{asof.replace('-', '')}_"
    candidates = [
        path
        for path in OPS_ROOT.glob(f"{prefix}*/job.json")
        if path.parent.name != exclude_job_id
    ]
    for prior_job_path in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
        prior_job = read_json(prior_job_path)
        prior_dir = prior_job_path.parent
        sources = source_inventory_for_chain(prior_job, job_dir=prior_dir)
        raw_source = sources.get("finmind_raw_daily_price") if isinstance(sources.get("finmind_raw_daily_price"), dict) else {}
        if str(raw_source.get("source_max_date") or "") >= asof and int(raw_source.get("row_count") or 0) > 0:
            return {
                "status": "RAW_READY_FROM_PRIOR_JOB",
                "source_max_date": str(raw_source.get("source_max_date") or ""),
                "row_count": raw_source.get("row_count", 0),
                "symbol_count": raw_source.get("symbol_count", 0),
                "evidence_path": rel_path(prior_job_path),
                "source_inventory_path": rel_path(prior_dir / "daily_source_inventory.json"),
            }
    return {}


def infer_raw_status_for_chain(
    *,
    asof: str,
    job: dict[str, Any],
    job_dir: Path,
    source_inventory: dict[str, dict[str, Any]],
    accounting_rows: list[dict[str, str]],
    args: argparse.Namespace,
) -> tuple[str, list[str], dict[str, Any]]:
    raw_source = source_inventory.get("finmind_raw_daily_price") if isinstance(source_inventory.get("finmind_raw_daily_price"), dict) else {}
    raw_row = accounting_row_by_category(accounting_rows, "finmind_raw_daily_price")
    evidence_paths: list[str] = []
    if raw_source.get("evidence_path"):
        evidence_paths.append(str(raw_source.get("evidence_path")))
    if raw_row.get("status") == "captured" and str(raw_row.get("source_max_date") or "") >= asof:
        return "READY", evidence_paths, {
            "source": "current_job",
            "source_max_date": raw_row.get("source_max_date", ""),
            "row_count": raw_row.get("row_count", ""),
            "symbol_count": raw_row.get("symbol_count", ""),
        }
    if str(raw_source.get("source_max_date") or "") >= asof and int(raw_source.get("row_count") or 0) > 0:
        return "READY", evidence_paths, {
            "source": "current_job_inventory",
            "source_max_date": raw_source.get("source_max_date", ""),
            "row_count": raw_source.get("row_count", 0),
            "symbol_count": raw_source.get("symbol_count", 0),
        }
    prior = raw_evidence_from_prior_job(asof, exclude_job_id=str(job.get("job_id") or ""))
    if prior:
        return "READY_FROM_PRIOR_JOB", [prior["evidence_path"], prior["source_inventory_path"]], prior
    if getattr(args, "skip_finmind", False):
        return "DISABLED_BY_SKIP_FINMIND", evidence_paths, {"source": "current_job", "reason": "--skip-finmind"}
    if job.get("status") in {"today_data_window_wait", "weekend_no_pending_wait"}:
        return "NOT_ATTEMPTED_DATA_WINDOW_OR_NON_TRADING_DAY", evidence_paths, {"source": "current_job", "reason": str(job.get("status") or "")}
    return "MISSING_OR_INCOMPLETE", evidence_paths, {"source": "current_job", "reason": str(raw_row.get("status") or "no_raw_inventory")}


def artifact_manifest_for_asof(root: Path, asof: str) -> Path | None:
    if not root.exists():
        return None
    manifests: list[Path] = []
    for path in root.glob("*/manifest.json"):
        payload = read_json(path)
        if str(payload.get("asof") or payload.get("signal_asof") or payload.get("target_asof") or "") == asof:
            manifests.append(path)
    if not manifests:
        return None
    return sorted(manifests, key=lambda p: p.stat().st_mtime)[-1]


def model_a_manifest_paths(asof: str) -> dict[str, str]:
    inference_manifest = artifact_manifest_for_asof(ROOT / "data_tw/canonical/model_inference_input" / MODELA_MODEL_ID, asof)
    score_manifest = artifact_manifest_for_asof(ROOT / "data_tw/artifacts/score_jobs" / MODELA_MODEL_ID, asof)
    signal_manifest = artifact_manifest_for_asof(ROOT / "data_tw/artifacts/signals" / MODELA_MODEL_ID, asof)
    return {
        "inference_input_manifest": rel_path(inference_manifest) if inference_manifest else "",
        "score_job_manifest": rel_path(score_manifest) if score_manifest else "",
        "signal_manifest": rel_path(signal_manifest) if signal_manifest else "",
    }


def daily_auto_provider_candidate_job_dirs(asof: str, *, exclude_job_id: str = "") -> list[Path]:
    if not DNG17_PROVIDER_CANDIDATE_ROOT.exists():
        return []
    prefix = f"daily_auto_provider_candidate_{asof.replace('-', '')}_"
    candidates = [
        path
        for path in DNG17_PROVIDER_CANDIDATE_ROOT.glob(f"{prefix}*")
        if path.is_dir() and path.name != exclude_job_id
    ]
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)


def provider_candidate_forbidden_actions() -> dict[str, bool]:
    return {
        "formal_publish": False,
        "formal_provider_mutated": False,
        "formal_normalized_mutated": False,
        "accepted_latest_switch": False,
        "latest_signal_updated": False,
        "readonly_latest_published": False,
        "agent_prompt_latest_published": False,
        "production_default_model_or_strategy_switched": False,
        "strategy_replay_or_nav_triggered": False,
        "broker_order_quick_trade_triggered": False,
        "target_position_or_weight_generated": False,
        "finmind_fallback": False,
        "mixed_provider_bridge": False,
        "model_training_or_tuning": False,
    }


def validate_isolated_provider_candidate(
    *,
    asof: str,
    readiness_path: Path,
    decision_path: Path,
    candidate_source: str,
) -> dict[str, Any]:
    readiness = read_json(readiness_path)
    decision = read_json(decision_path)
    errors: list[str] = []
    if readiness.get("asof") != asof or decision.get("asof") != asof:
        errors.append("asof_mismatch")
    if readiness.get("candidate_input_status") != "READY_STAGED_YAHOO_SCRAPLING_PROXY_CANDIDATE":
        errors.append("candidate_input_status_not_ready")
    if decision.get("decision") != "PASS_GO_DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION":
        errors.append("decision_not_pass_go")
    if int(readiness.get("candidate_normalized_symbols_with_asof") or 0) != 150:
        errors.append("candidate_normalized_symbols_with_asof_not_150")
    if readiness.get("staged_provider_calendar_has_asof") is not True:
        errors.append("staged_provider_calendar_missing_asof")
    if readiness.get("staged_provider_validation_status") != "pass" or decision.get("provider_validation_status") != "pass":
        errors.append("staged_provider_validation_not_pass")
    if readiness.get("candidate_model_smoke_status") != "pass" or decision.get("model_smoke_status") != "pass":
        errors.append("model_a_staged_smoke_not_pass")
    for key in ("production_allowed", "publish_latest_authorized", "finmind_fallback", "mixed_provider_bridge"):
        if bool(readiness.get(key)) or bool(decision.get(key)):
            errors.append(f"{key}_must_be_false")
    for source_name, payload in (("readiness", readiness), ("decision", decision)):
        forbidden = payload.get("forbidden_actions") if isinstance(payload.get("forbidden_actions"), dict) else {}
        for key, value in forbidden.items():
            if bool(value):
                errors.append(f"{source_name}_forbidden_action_true:{key}")
    artifacts = readiness.get("artifacts") if isinstance(readiness.get("artifacts"), dict) else {}
    staged_provider = resolve_path(str(artifacts.get("staged_qlib_bin") or decision.get("staged_provider_path") or ""))
    candidate_normalized = resolve_path(str(artifacts.get("candidate_normalized") or decision.get("candidate_normalized_path") or ""))
    if not staged_provider.exists():
        errors.append("staged_provider_path_missing")
    if not candidate_normalized.exists():
        errors.append("candidate_normalized_path_missing")
    return {
        "ok": not errors,
        "status": "READY_ISOLATED_PROVIDER_CANDIDATE" if not errors else "BLOCKED_ISOLATED_PROVIDER_CANDIDATE",
        "asof": asof,
        "candidate_source": candidate_source,
        "readiness_path": rel_path(readiness_path),
        "decision_path": rel_path(decision_path),
        "candidate_job_dir": str(readiness.get("candidate_job_dir") or decision.get("candidate_job_dir") or readiness.get("job_dir") or decision.get("job_dir") or ""),
        "staged_provider_path": rel_path(staged_provider),
        "candidate_normalized_path": rel_path(candidate_normalized),
        "candidate_normalized_symbols_with_asof": readiness.get("candidate_normalized_symbols_with_asof", 0),
        "staged_provider_calendar_has_asof": bool(readiness.get("staged_provider_calendar_has_asof")),
        "staged_provider_calendar_max": str(readiness.get("staged_provider_calendar_max") or ""),
        "staged_provider_validation_status": str(readiness.get("staged_provider_validation_status") or ""),
        "candidate_model_smoke_status": str(readiness.get("candidate_model_smoke_status") or ""),
        "fetch_status": str(decision.get("fetch_status") or ""),
        "symbols_expected": int(decision.get("symbols_expected") or readiness.get("candidate_normalized_symbols_expected") or 0),
        "symbols_success": int(decision.get("symbols_success") or readiness.get("candidate_normalized_symbols_success") or 0),
        "calendar_has_asof": bool(decision.get("calendar_has_asof") or readiness.get("staged_provider_calendar_has_asof")),
        "calendar_max": str((decision.get("provider_summary") or {}).get("calendar_max") or readiness.get("staged_provider_calendar_max") or ""),
        "model_smoke_status": str(decision.get("model_smoke_status") or readiness.get("candidate_model_smoke_status") or ""),
        "prediction_rows": int(decision.get("prediction_rows") or readiness.get("prediction_rows") or 0),
        "finite_prediction_share": float(decision.get("finite_prediction_share") or readiness.get("finite_prediction_share") or 0.0),
        "forbidden_actions": readiness.get("forbidden_actions") if isinstance(readiness.get("forbidden_actions"), dict) else {},
        "errors": errors,
    }


def find_validated_isolated_provider_candidate(
    asof: str,
    *,
    current_job_dir: Path | None = None,
    exclude_candidate_job_id: str = "",
    include_prior_daily_auto: bool = True,
    include_dng15_fixture: bool = True,
) -> dict[str, Any]:
    if current_job_dir is not None:
        current = validate_isolated_provider_candidate(
            asof=asof,
            readiness_path=current_job_dir / "provider_candidate_readiness.json",
            decision_path=current_job_dir / "provider_candidate_refresh_decision.json",
            candidate_source="current_job_dng17",
        )
        if current.get("ok"):
            return current
    if include_prior_daily_auto:
        for candidate_job_dir in daily_auto_provider_candidate_job_dirs(asof, exclude_job_id=exclude_candidate_job_id):
            prior = validate_isolated_provider_candidate(
                asof=asof,
                readiness_path=candidate_job_dir / "provider_candidate_readiness.json",
                decision_path=candidate_job_dir / "provider_candidate_refresh_decision.json",
                candidate_source="prior_daily_auto_dng17",
            )
            if prior.get("ok"):
                return prior
    if not include_dng15_fixture:
        return {
            "ok": False,
            "status": "BLOCKED_ISOLATED_PROVIDER_CANDIDATE",
            "asof": asof,
            "candidate_source": "none",
            "errors": ["no_daily_auto_dng17_candidate_ready"],
        }
    fixture = validate_isolated_provider_candidate(
        asof=asof,
        readiness_path=DNG15_R_A_R_READINESS,
        decision_path=DNG15_R_A_R_DECISION,
        candidate_source="dng15_r_a_r_fixture",
    )
    if fixture.get("ok"):
        return fixture
    fixture["candidate_source"] = "none"
    return fixture


def isolated_modela_catalog_candidates() -> list[Path]:
    candidates = [DNG15_R_B_ISOLATED_MODELA_VALIDATION]
    candidates.extend(sorted((ROOT / "data_tw/catalog").glob("dng15_r_b_isolated_modela_score_integration_validation_*.json")))
    unique: dict[str, Path] = {}
    for path in candidates:
        unique[str(path)] = path
    return sorted(unique.values(), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)


def validate_isolated_modela_catalog(asof: str, catalog_path: Path) -> dict[str, Any]:
    catalog = read_json(catalog_path)
    errors: list[str] = []
    if catalog.get("asof") != asof:
        errors.append("asof_mismatch")
    if catalog.get("status") != "PASS_GO_DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN":
        errors.append("catalog_status_not_pass_go")
    if catalog.get("pipeline_status") != "SCORED_ASOF_TARGET" or catalog.get("score_status") != "SCORED_ASOF_TARGET":
        errors.append("score_status_not_scored_asof_target")
    if catalog.get("model_inference_input_status") != "READY":
        errors.append("model_inference_input_not_ready")
    if catalog.get("model_signal_status") != "READY":
        errors.append("model_signal_not_ready")
    if int(catalog.get("signals_rows") or 0) != 150 or int(catalog.get("raw_scores_rows") or 0) != 150:
        errors.append("score_or_signal_rows_not_150")
    if catalog.get("signal_asof") != asof or catalog.get("available_at") != asof:
        errors.append("signal_asof_or_available_at_mismatch")
    for validator_key in ("model_inference_input_validator", "score_job_validator", "model_signal_validator"):
        validator = catalog.get(validator_key) if isinstance(catalog.get(validator_key), dict) else {}
        if validator.get("ok") is not True or validator.get("status") != "PASS":
            errors.append(f"{validator_key}_not_pass")
    for key, value in (catalog.get("forbidden_actions") if isinstance(catalog.get("forbidden_actions"), dict) else {}).items():
        if bool(value):
            errors.append(f"forbidden_action_true:{key}")
    for key in ("production_allowed", "publish_latest_authorized"):
        if bool(catalog.get(key)):
            errors.append(f"{key}_must_be_false")
    if catalog.get("not_published_latest") is not True:
        errors.append("not_published_latest_must_be_true")
    artifacts = catalog.get("artifacts") if isinstance(catalog.get("artifacts"), dict) else {}
    for artifact_key in ("model_inference_input", "score_job", "model_signal"):
        path = resolve_path(str(artifacts.get(artifact_key) or ""))
        if not path.exists():
            errors.append(f"{artifact_key}_path_missing")
    return {
        "ok": not errors,
        "status": "READY_EXISTING_ISOLATED_ARTIFACT" if not errors else "BLOCKED_EXISTING_ISOLATED_ARTIFACT",
        "asof": asof,
        "catalog_path": rel_path(catalog_path),
        "run_id": str(catalog.get("run_id") or ""),
        "pipeline_status": str(catalog.get("pipeline_status") or ""),
        "score_status": str(catalog.get("score_status") or ""),
        "model_inference_input_status": str(catalog.get("model_inference_input_status") or ""),
        "model_signal_status": str(catalog.get("model_signal_status") or ""),
        "raw_scores_rows": int(catalog.get("raw_scores_rows") or 0),
        "signals_rows": int(catalog.get("signals_rows") or 0),
        "source_feature_artifact": str(catalog.get("source_feature_artifact") or ""),
        "source_normalized_artifact": str(catalog.get("source_normalized_artifact") or ""),
        "source_model_artifact": str(catalog.get("source_model_artifact") or ""),
        "artifacts": artifacts,
        "catalog": catalog if not errors else {},
        "errors": errors,
    }


def find_validated_isolated_modela_artifact(asof: str) -> dict[str, Any]:
    last_result: dict[str, Any] | None = None
    for catalog_path in isolated_modela_catalog_candidates():
        result = validate_isolated_modela_catalog(asof, catalog_path)
        if result.get("ok"):
            return result
        last_result = result
    if last_result is not None:
        return last_result
    return {
        "ok": False,
        "status": "BLOCKED_EXISTING_ISOLATED_ARTIFACT",
        "asof": asof,
        "catalog_path": "",
        "run_id": "",
        "pipeline_status": "",
        "score_status": "",
        "model_inference_input_status": "",
        "model_signal_status": "",
        "raw_scores_rows": 0,
        "signals_rows": 0,
        "source_feature_artifact": "",
        "source_normalized_artifact": "",
        "source_model_artifact": "",
        "artifacts": {},
        "catalog": {},
        "errors": ["no_isolated_modela_catalog_found"],
    }


def latest_option_c_daily_signal_run_for_asof(asof: str) -> Path | None:
    root = QLIB / "data_tw/experiments/option_c_daily_signal"
    if not root.exists():
        return None
    pattern = f"option_c_daily_signal_{asof.replace('-', '')}_*"
    candidates = [path for path in root.glob(pattern) if path.is_dir()]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]


def downstream_context_paths(asof: str) -> dict[str, str]:
    strategy_manifest = artifact_manifest_for_asof(ROOT / f"data_tw/artifacts/strategy_input_bundles/{STRATEGY_RULE}_dng10_modela", asof)
    replay_manifest = artifact_manifest_for_asof(ROOT / f"data_tw/artifacts/replay_input_bundles/{STRATEGY_RULE}_dng4_contract", asof)
    readonly_manifest = artifact_manifest_for_asof(ROOT / "data_tw/artifacts/readonly_source_context", asof)
    agent_manifest = artifact_manifest_for_asof(ROOT / "data_tw/artifacts/agent_daily_prompt_source_context", asof)
    return {
        "strategy_input_bundle_manifest": rel_path(strategy_manifest) if strategy_manifest else "",
        "replay_input_bundle_manifest": rel_path(replay_manifest) if replay_manifest else "",
        "readonly_source_context_manifest": rel_path(readonly_manifest) if readonly_manifest else "",
        "agent_source_context_manifest": rel_path(agent_manifest) if agent_manifest else "",
    }


def publish_latest_gate_status(job: dict[str, Any]) -> str:
    if job.get("provider_publish_triggered") or job.get("latest_signal_updated"):
        return "EXPLICIT_LEGACY_GATE_TRIGGERED"
    readonly_snapshot = job.get("readonly_snapshot") if isinstance(job.get("readonly_snapshot"), dict) else {}
    if readonly_snapshot.get("latest_updated"):
        return "READONLY_LATEST_UPDATED_BY_EXPLICIT_GATE"
    return "DISABLED_BY_DEFAULT"


def is_weekend_asof(asof: str) -> bool:
    try:
        return datetime.strptime(asof, "%Y-%m-%d").date().weekday() >= 5
    except ValueError:
        return False


def build_forbidden_actions_snapshot(job: dict[str, Any]) -> dict[str, Any]:
    readonly_snapshot = job.get("readonly_snapshot") if isinstance(job.get("readonly_snapshot"), dict) else {}
    actions = {
        "provider_refresh_triggered": bool(job.get("yahoo_refresh_triggered")),
        "provider_publish_triggered": bool(job.get("provider_publish_triggered")),
        "accepted_latest_switch_triggered": bool(job.get("latest_signal_updated")),
        "qlib_accepted_latest_switched": bool(job.get("latest_signal_updated")),
        "readonly_latest_published": bool(readonly_snapshot.get("latest_updated")),
        "agent_prompt_published": False,
        "production_default_model_or_strategy_switched": False,
        "broker_order_quick_trade_triggered": False,
        "target_position_or_weight_generated": False,
    }
    return {"all_false": not any(actions.values()), "actions": actions}


def build_pbpr0_daily_chain_decision_fields(
    *,
    raw_status: str,
    formal_calendar_covers: bool,
    model_a_inference_status: str,
    model_a_score_status: str,
    model_a_signal_status: str,
    blocked_at: str,
    blocker_reason: str,
) -> dict[str, Any]:
    required_inputs = list(PBPR0_DAILY_CHAIN_REQUIRED_INPUTS)
    raw_ready = raw_status.startswith("READY")
    provider_stale = raw_ready and not formal_calendar_covers
    if provider_stale:
        return {
            "state": "RAW_READY_PROVIDER_STALE",
            "required_inputs": required_inputs,
            "refined_blocker": dict(PBPR0_REFINED_PROVIDER_BLOCKER),
            "provider_bridge_readiness_state": "BLOCKED_NEEDS_TARGET_ASOF_PROVIDER_OR_BRIDGE",
        }
    if not raw_ready:
        return {
            "state": "RAW_NOT_READY",
            "required_inputs": required_inputs,
            "refined_blocker": {
                "blocked_at": blocked_at or "raw_daily_source_inventory",
                "reason": blocker_reason or "raw_daily_source_inventory_not_ready",
            },
            "provider_bridge_readiness_state": "NOT_EVALUATED_RAW_NOT_READY",
        }
    if model_a_signal_status == "READY":
        return {
            "state": "SIGNAL_READY_READONLY_CONTEXT_PENDING",
            "required_inputs": required_inputs,
            "refined_blocker": {
                "blocked_at": blocked_at or "",
                "reason": blocker_reason or "none",
            },
            "provider_bridge_readiness_state": "PROVIDER_OR_SIGNAL_ARTIFACT_READY",
        }
    if model_a_score_status == "READY":
        state = "SCORE_READY_SIGNAL_VALIDATION_PENDING"
    elif model_a_inference_status == "READY":
        state = "MODEL_INPUT_READY_SCORE_PENDING"
    else:
        state = "PROVIDER_READY_MODEL_INPUT_PENDING"
    return {
        "state": state,
        "required_inputs": required_inputs,
        "refined_blocker": {
            "blocked_at": blocked_at or "model_a_input_score_or_signal_artifact",
            "reason": blocker_reason or "model_a_artifact_not_ready",
        },
        "provider_bridge_readiness_state": "READY_OR_FORMAL_PROVIDER_COVERS_TARGET_ASOF",
    }


def build_daily_chain_status_payload(
    job: dict[str, Any],
    *,
    job_dir: Path,
    asof: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    source_inventory = source_inventory_for_chain(job, job_dir=job_dir)
    accounting_rows = accounting_rows_for_chain(job, job_dir=job_dir)
    raw_status, raw_evidence_paths, raw_detail = infer_raw_status_for_chain(
        asof=asof,
        job=job,
        job_dir=job_dir,
        source_inventory=source_inventory,
        accounting_rows=accounting_rows,
        args=args,
    )
    formal_calendar_max = calendar_max_date(CALENDAR)
    formal_calendar_covers = bool(formal_calendar_max >= asof)
    model_paths = model_a_manifest_paths(asof)
    signal_run = latest_option_c_daily_signal_run_for_asof(asof)
    context_paths = downstream_context_paths(asof)
    latest_signal_asof = latest_asof()
    weekend = is_weekend_asof(asof)
    data_window_status = str(job.get("status") or "")
    if job.get("status") == "today_data_window_wait":
        data_window_status = "WAITING_FOR_TAIPEI_DATA_WINDOW"
    elif job.get("status") == "weekend_no_pending_wait" or weekend:
        data_window_status = "NON_TRADING_DAY_OR_WEEKEND"
    elif raw_status.startswith("READY"):
        data_window_status = "DATA_WINDOW_OBSERVED"

    if weekend:
        is_trading_day: bool | str = False
    elif formal_calendar_covers or raw_status.startswith("READY"):
        is_trading_day = True
    else:
        is_trading_day = "UNKNOWN"

    qlib_status = "READY" if formal_calendar_covers else "BLOCKED_PROVIDER_VIEW_STALE"
    model_a_inference_status = "READY" if model_paths["inference_input_manifest"] else ("BLOCKED_PROVIDER_VIEW_STALE" if not formal_calendar_covers else "MISSING")
    model_a_score_status = "READY" if model_paths["score_job_manifest"] else ("BLOCKED_PROVIDER_VIEW_STALE" if not formal_calendar_covers else "MISSING")
    model_a_signal_status = "READY" if model_paths["signal_manifest"] else ("BLOCKED_PROVIDER_VIEW_STALE" if not formal_calendar_covers else "MISSING")
    if not model_paths["score_job_manifest"] and signal_run:
        model_a_score_status = "SOURCE_RUN_EXISTS_BUT_STANDARD_SCORE_ARTIFACT_MISSING"
    model_signal_gate = job.get("model_signal_gate") if isinstance(job.get("model_signal_gate"), dict) else {}
    provider_candidate_refresh = job.get("provider_candidate_refresh_gate") if isinstance(job.get("provider_candidate_refresh_gate"), dict) else {}
    provider_candidate = provider_candidate_refresh.get("candidate") if isinstance(provider_candidate_refresh.get("candidate"), dict) else {}
    isolated_artifact = model_signal_gate.get("isolated_existing_artifact") if isinstance(model_signal_gate.get("isolated_existing_artifact"), dict) else {}
    isolated_artifacts = isolated_artifact.get("artifacts") if isinstance(isolated_artifact.get("artifacts"), dict) else {}
    isolated_ready = bool(model_signal_gate.get("ok") and isolated_artifact.get("ok"))
    isolated_status = str(model_signal_gate.get("model_a_readiness_status") or "")
    if not isolated_ready and not bool(getattr(args, "enable_model_signal_gate", False)):
        existing_isolated = find_validated_isolated_modela_artifact(asof)
        if existing_isolated.get("ok"):
            isolated_ready = True
            isolated_status = "READY_EXISTING_ISOLATED_ARTIFACT"
            isolated_artifact = existing_isolated
            isolated_artifacts = existing_isolated.get("artifacts") if isinstance(existing_isolated.get("artifacts"), dict) else {}
    if isolated_ready and isolated_status in {"READY_ISOLATED_CANDIDATE", "READY_EXISTING_ISOLATED_ARTIFACT"}:
        model_a_inference_status = isolated_status
        model_a_score_status = isolated_status
        model_a_signal_status = isolated_status
    if bool(getattr(args, "enable_model_signal_gate", False)) and model_signal_gate.get("attempted") and not model_signal_gate.get("ok"):
        if provider_candidate_refresh.get("status") in {"BLOCKED_YAHOO_STAGED_REFRESH_FAILED", "BLOCKED_PROVIDER_CANDIDATE_REFRESH"}:
            model_a_inference_status = "BLOCKED_PROVIDER_CANDIDATE_REFRESH"
            model_a_score_status = "BLOCKED_PROVIDER_CANDIDATE_REFRESH"
            model_a_signal_status = "BLOCKED_PROVIDER_CANDIDATE_REFRESH"
        else:
            model_a_inference_status = "FAILED_MODEL_SIGNAL_GATE"
            model_a_score_status = "FAILED_MODEL_SIGNAL_GATE"
            model_a_signal_status = "FAILED_MODEL_SIGNAL_GATE"

    model_b_ltr_status = "BLOCKED_INPUT_NOT_READY"
    if model_signal_gate.get("model_b_status"):
        model_b_ltr_status = str(model_signal_gate.get("model_b_status"))
    elif not bool(getattr(args, "enable_model_signal_gate", False)):
        model_b_ltr_status = "DISABLED_BY_DEFAULT_BLOCKED_UNTIL_ORTHOGONAL_READY"

    blocked_at = ""
    blocker_reason = ""
    next_required_action = "wait_next_daily_auto_run"
    next_retry_hint = ""
    if weekend:
        blocked_at = "market_calendar"
        blocker_reason = "weekend_or_non_trading_day"
        next_required_action = "skip_holiday_or_weekend_and_wait_next_trading_day"
    elif isolated_ready and not formal_calendar_covers:
        blocked_at = "qlib_provider_view_or_formal_calendar"
        blocker_reason = "formal qlib provider calendar remains stale; isolated Model A score is ready but does not authorize formal provider/latest publish"
        next_required_action = "review_DNG16_then_continue_to_DNG17_daily_auto_provider_candidate_refresh_integration"
        next_retry_hint = "manual_review_or_DNG17"
    elif model_paths["signal_manifest"] and formal_calendar_covers:
        blocker_reason = "none"
        next_required_action = "observe_next_trade_day"
    elif not formal_calendar_covers:
        blocked_at = "qlib_provider_view_or_formal_calendar"
        if raw_status.startswith("READY"):
            blocker_reason = "FinMind raw/ops evidence covers target asof but formal qlib provider calendar does not; Model A score cannot be generated without provider view or validated canonical bridge"
            next_required_action = "refresh_formal_qlib_provider_view_or_build_validated_canonical_bridge_then_run_model_a_score"
            next_retry_hint = "retry_after_provider_view_refresh_or_canonical_bridge"
        else:
            blocker_reason = f"formal qlib provider calendar does not cover target asof and raw status is {raw_status}"
            next_required_action = "retry_raw_provider_then_refresh_formal_qlib_provider_view_or_validated_canonical_bridge"
            next_retry_hint = "retry_next_scheduled_daily_auto_run"
    elif not raw_status.startswith("READY") and not getattr(args, "skip_finmind", False):
        blocked_at = "raw_or_data_window"
        blocker_reason = raw_status
        next_required_action = "retry_raw_provider_or_wait_data_window"
        next_retry_hint = "retry_next_scheduled_daily_auto_run"
    elif not model_paths["signal_manifest"]:
        blocked_at = "model_a_score_or_signal"
        blocker_reason = "formal provider calendar covers asof but standard Model A signal artifact is missing"
        next_required_action = "run_model_signal_gate_or_model_a_score_builder_with_publish_gate_disabled"
        next_retry_hint = "retry_model_signal_gate"
    elif not context_paths["strategy_input_bundle_manifest"]:
        blocked_at = "strategy_input_bundle"
        blocker_reason = "Model A signal is ready but StrategyInputBundle is missing"
        next_required_action = "build_strategy_input_bundle_and_readonly_source_context_with_latest_publish_disabled"
    else:
        blocker_reason = "none"
        next_required_action = "observe_next_trade_day"

    pending_status = "NONE"
    pending = read_json(PENDING_ASOF)
    if str(pending.get("asof") or "") == asof:
        pending_status = str(pending.get("reason") or "PENDING")
    elif blocked_at:
        pending_status = blocked_at

    pbpr0_decision_fields = build_pbpr0_daily_chain_decision_fields(
        raw_status=raw_status,
        formal_calendar_covers=formal_calendar_covers,
        model_a_inference_status=model_a_inference_status,
        model_a_score_status=model_a_score_status,
        model_a_signal_status=model_a_signal_status,
        blocked_at=blocked_at,
        blocker_reason=blocker_reason,
    )
    payload = {
        "schema_version": DNG13_DAILY_CHAIN_STATUS_SCHEMA_VERSION,
        "created_at": utc_now(),
        "asof": asof,
        "job_id": str(job.get("job_id") or ""),
        **pbpr0_decision_fields,
        "is_trading_day": is_trading_day,
        "data_window_status": data_window_status,
        "raw_status": raw_status,
        "normalized_status": "OBSERVED_VIA_DAILY_SOURCE_INVENTORY_OR_ACCOUNTING" if source_inventory else "MISSING_SOURCE_INVENTORY",
        "price_store_status": "READY_OR_FORMAL_PROVIDER_COVERS_ASOF" if formal_calendar_covers else "BLOCKED_PROVIDER_VIEW_STALE",
        "market_feature_status": "READY_OR_FORMAL_PROVIDER_COVERS_ASOF" if formal_calendar_covers else "BLOCKED_PROVIDER_VIEW_STALE",
        "orthogonal_feature_status": "BLOCKED_INPUT_NOT_READY",
        "qlib_provider_view_status": qlib_status,
        "model_a_inference_input_status": model_a_inference_status,
        "model_a_score_status": model_a_score_status,
        "model_a_signal_status": model_a_signal_status,
        "model_b_ltr_status": model_b_ltr_status,
        "strict_model_b_generation_status": model_b_ltr_status,
        "legacy_compatible_model_b_status": MODELB_LEGACY_COMPATIBILITY["status"],
        "legacy_compatible_model_b": dict(MODELB_LEGACY_COMPATIBILITY),
        "strategy_input_bundle_status": "READY" if context_paths["strategy_input_bundle_manifest"] else ("BLOCKED_MODEL_A_SIGNAL" if not model_paths["signal_manifest"] else "MISSING"),
        "replay_input_bundle_status": "READY" if context_paths["replay_input_bundle_manifest"] else "NOT_BUILT_OR_NOT_REQUIRED_BY_DAILY_CHAIN",
        "readonly_source_context_status": "READY" if context_paths["readonly_source_context_manifest"] else ("BLOCKED_MODEL_A_SIGNAL" if not model_paths["signal_manifest"] else "MISSING"),
        "agent_source_context_status": "READY" if context_paths["agent_source_context_manifest"] else ("BLOCKED_MODEL_A_SIGNAL" if not model_paths["signal_manifest"] else "MISSING"),
        "frontend_payload_status": "READONLY_SOURCE_CONTEXT_READY_NOT_PUBLISHED" if context_paths["readonly_source_context_manifest"] else "BLOCKED_READONLY_SOURCE_CONTEXT",
        "publish_latest_gate_status": publish_latest_gate_status(job),
        "pending_asof_status": pending_status,
        "next_retry_hint": next_retry_hint,
        "blocked_at": blocked_at,
        "blocker_reason": blocker_reason,
        "next_required_action": next_required_action,
        "forbidden_actions": build_forbidden_actions_snapshot(job),
        "lineage_evidence": {
            "formal_calendar_path": rel_path(CALENDAR),
            "formal_calendar_max": formal_calendar_max,
            "latest_signal_path": rel_path(LATEST),
            "latest_signal_asof": latest_signal_asof,
            "raw_evidence_paths": raw_evidence_paths,
            "raw_detail": raw_detail,
            "option_c_daily_signal_source_run": rel_path(signal_run) if signal_run else "",
            **model_paths,
            "isolated_model_inference_input": str(isolated_artifacts.get("model_inference_input") or ""),
            "isolated_score_job": str(isolated_artifacts.get("score_job") or ""),
            "isolated_model_signal": str(isolated_artifacts.get("model_signal") or ""),
            "isolated_catalog_validation": str(isolated_artifact.get("catalog_path") or ""),
            "model_signal_gate_summary": str(model_signal_gate.get("summary_path") or ""),
            "provider_candidate_refresh_decision": str(provider_candidate_refresh.get("decision_path") or ""),
            "provider_candidate_readiness": str(provider_candidate_refresh.get("readiness_path") or ""),
            "provider_candidate_source": str(provider_candidate.get("candidate_source") or provider_candidate_refresh.get("candidate_source") or ""),
            "provider_candidate_job_dir": str(provider_candidate.get("candidate_job_dir") or provider_candidate_refresh.get("candidate_job_dir") or ""),
            "provider_candidate_normalized": str(provider_candidate.get("candidate_normalized_path") or ""),
            "provider_candidate_staged_provider": str(provider_candidate.get("staged_provider_path") or ""),
            **context_paths,
        },
        "gate_status": {
            "raw_normalized_gate": "enabled_unless_skip_finmind" if not getattr(args, "skip_finmind", False) else "disabled_by_skip_finmind",
            "canonical_feature_gate": "observed_only_in_dng13",
            "model_signal_gate": "enabled" if bool(getattr(args, "enable_model_signal_gate", False)) else "disabled_by_default",
            "provider_candidate_refresh_gate": "enabled" if bool(getattr(args, "enable_provider_candidate_refresh", False)) else "disabled_by_default",
            "provider_candidate_refresh_status": str(provider_candidate_refresh.get("status") or ""),
            "strategy_context_gate": "observed_only_in_dng13",
            "publish_latest_gate": "disabled_by_default",
        },
        "required_fields_present": all(field in {
            **{key: True for key in DNG13_REQUIRED_CHAIN_FIELDS},
        } for field in DNG13_REQUIRED_CHAIN_FIELDS),
        "research_only": True,
        "production_trade_enabled": False,
    }
    payload["required_fields_present"] = all(field in payload for field in DNG13_REQUIRED_CHAIN_FIELDS)
    return payload


def build_skipped_asof_ledger_payload(chain_status: dict[str, Any]) -> dict[str, Any]:
    asof = str(chain_status.get("asof") or "")
    blocked_at = str(chain_status.get("blocked_at") or "")
    if blocked_at:
        skip_or_block_status = "BLOCKED"
    elif chain_status.get("model_a_signal_status") == "READY":
        skip_or_block_status = "NOT_SKIPPED_MODEL_A_READY"
    else:
        skip_or_block_status = "UNKNOWN"
    if str(chain_status.get("data_window_status") or "") == "NON_TRADING_DAY_OR_WEEKEND":
        candidate_reason = "calendar_weekend_or_non_trading_day"
        skip_or_block_status = "SKIPPED_NON_TRADING_DAY"
    elif str(chain_status.get("model_a_signal_status") or "") in {"READY_ISOLATED_CANDIDATE", "READY_EXISTING_ISOLATED_ARTIFACT"}:
        candidate_reason = "formal_provider_stale_but_isolated_model_a_ready"
        skip_or_block_status = "BLOCKED_FORMAL_PROVIDER_STALE_WITH_ISOLATED_MODEL_A_READY" if blocked_at else "NOT_SKIPPED_ISOLATED_MODEL_A_READY"
    elif str(chain_status.get("raw_status") or "").startswith("READY") and chain_status.get("qlib_provider_view_status") == "BLOCKED_PROVIDER_VIEW_STALE":
        candidate_reason = "raw_ready_but_formal_provider_view_stale"
    elif chain_status.get("model_a_signal_status") == "READY":
        candidate_reason = "model_a_signal_ready"
    else:
        candidate_reason = "daily_auto_candidate_asof"

    row = {
        "asof": asof,
        "candidate_reason": candidate_reason,
        "is_trading_day": chain_status.get("is_trading_day"),
        "skip_or_block_status": skip_or_block_status,
        "state": chain_status.get("state", ""),
        "raw_status": chain_status.get("raw_status", ""),
        "formal_calendar_status": chain_status.get("qlib_provider_view_status", ""),
        "qlib_provider_view_status": chain_status.get("qlib_provider_view_status", ""),
        "score_status": chain_status.get("model_a_score_status", ""),
        "strategy_context_status": chain_status.get("strategy_input_bundle_status", ""),
        "skip_reason": chain_status.get("blocker_reason", "") if blocked_at else "",
        "refined_blocker": chain_status.get("refined_blocker", {}),
        "provider_bridge_readiness_state": chain_status.get("provider_bridge_readiness_state", ""),
        "retry_policy": chain_status.get("next_retry_hint", "") or ("none" if not blocked_at else "manual_or_next_daily_auto"),
        "next_required_action": chain_status.get("next_required_action", ""),
        "evidence_paths": {
            "daily_chain_status": "",
            "formal_calendar": (chain_status.get("lineage_evidence") or {}).get("formal_calendar_path", ""),
            "latest_signal": (chain_status.get("lineage_evidence") or {}).get("latest_signal_path", ""),
            "raw_evidence_paths": (chain_status.get("lineage_evidence") or {}).get("raw_evidence_paths", []),
            "model_a_signal_manifest": (chain_status.get("lineage_evidence") or {}).get("signal_manifest", ""),
            "isolated_model_signal": (chain_status.get("lineage_evidence") or {}).get("isolated_model_signal", ""),
            "model_signal_gate_summary": (chain_status.get("lineage_evidence") or {}).get("model_signal_gate_summary", ""),
            "provider_candidate_refresh_decision": (chain_status.get("lineage_evidence") or {}).get("provider_candidate_refresh_decision", ""),
            "provider_candidate_readiness": (chain_status.get("lineage_evidence") or {}).get("provider_candidate_readiness", ""),
        },
    }
    return {
        "schema_version": DNG13_SKIPPED_ASOF_LEDGER_SCHEMA_VERSION,
        "created_at": utc_now(),
        "job_id": chain_status.get("job_id", ""),
        "asof": asof,
        "ledger_rows": [row],
        "row_count": 1,
        "lineage_gap_detected": bool(candidate_reason == "raw_ready_but_formal_provider_view_stale"),
        "state": chain_status.get("state", ""),
        "refined_blocker": chain_status.get("refined_blocker", {}),
        "provider_bridge_readiness_state": chain_status.get("provider_bridge_readiness_state", ""),
        "forbidden_actions": chain_status.get("forbidden_actions", {}),
        "research_only": True,
        "production_trade_enabled": False,
    }


def write_dng13_daily_chain_artifacts(job: dict[str, Any], *, job_dir: Path, asof: str, args: argparse.Namespace) -> dict[str, Any]:
    chain_status = build_daily_chain_status_payload(job, job_dir=job_dir, asof=asof, args=args)
    status_path = job_dir / "daily_chain_status.json"
    write_json(status_path, chain_status)
    ledger = build_skipped_asof_ledger_payload(chain_status)
    ledger["ledger_rows"][0]["evidence_paths"]["daily_chain_status"] = rel_path(status_path)
    ledger_path = job_dir / "skipped_asof_ledger.json"
    write_json(ledger_path, ledger)
    job["daily_chain_status"] = {
        "schema_version": DNG13_DAILY_CHAIN_STATUS_SCHEMA_VERSION,
        "path": rel_path(status_path),
        "asof": asof,
        "state": chain_status.get("state", ""),
        "refined_blocker": chain_status.get("refined_blocker", {}),
        "provider_bridge_readiness_state": chain_status.get("provider_bridge_readiness_state", ""),
        "blocked_at": chain_status.get("blocked_at", ""),
        "blocker_reason": chain_status.get("blocker_reason", ""),
        "raw_status": chain_status.get("raw_status", ""),
        "qlib_provider_view_status": chain_status.get("qlib_provider_view_status", ""),
        "model_a_score_status": chain_status.get("model_a_score_status", ""),
        "forbidden_actions_all_false": bool((chain_status.get("forbidden_actions") or {}).get("all_false")),
    }
    job["skipped_asof_ledger"] = {
        "schema_version": DNG13_SKIPPED_ASOF_LEDGER_SCHEMA_VERSION,
        "path": rel_path(ledger_path),
        "row_count": ledger.get("row_count", 0),
        "lineage_gap_detected": bool(ledger.get("lineage_gap_detected")),
    }
    return {"daily_chain_status": chain_status, "skipped_asof_ledger": ledger}


def summarize_finmind_stdout(stdout_path: Path) -> dict[str, dict[str, Any]]:
    payload = parse_stdout_json(stdout_path)
    if not payload:
        return {}

    def row_from_summary(category: str, source_id: str, summary_key: str, archived_key: str) -> dict[str, Any]:
        summary = payload.get(summary_key) if isinstance(payload.get(summary_key), dict) else {}
        symbols = summary.get("symbols") if isinstance(summary.get("symbols"), list) else []
        return {
            "dataset_category": category,
            "source_id": source_id,
            "source_boundary": "backend/scripts/update_tw_stock_daily.py FinMind workflow stdout",
            "source_max_date": str(summary.get("date_max") or ""),
            "source_min_date": str(summary.get("date_min") or ""),
            "row_count": int(summary.get("count") or 0),
            "symbol_count": len(symbols),
            "archived_count": int(payload.get(archived_key) or 0),
            "evidence_path": rel_path(stdout_path),
            "checksum": str(file_fingerprint(stdout_path).get("sha256") or ""),
        }

    return {
        "finmind_raw_daily_price": row_from_summary("finmind_raw_daily_price", "finmind_daily_price", "archive", "archived_count"),
        "institutional_flow": row_from_summary("institutional_flow", "finmind_institutional_flow", "institutional_trades", "institutional_trades_archived_count"),
        "margin_short": row_from_summary("margin_short", "finmind_margin_short", "margin_trading", "margin_trading_archived_count"),
    }


def load_orthogonal_batch_control(job: dict[str, Any]) -> dict[str, Any]:
    direct = job.get("finmind_orthogonal_batch_update") if isinstance(job.get("finmind_orthogonal_batch_update"), dict) else {}
    summary = direct.get("summary") if isinstance(direct.get("summary"), dict) else {}
    if summary:
        return summary
    stdout_path = str(direct.get("stdout_path") or "")
    payload = parse_stdout_json(resolve_path(stdout_path)) if stdout_path else {}
    return payload.get("orthogonal_batch_control") if isinstance(payload.get("orthogonal_batch_control"), dict) else {}


def build_daily_source_inventory(job: dict[str, Any], *, job_dir: Path, asof: str) -> dict[str, dict[str, Any]]:
    calendar_fp = file_fingerprint(CALENDAR)
    instruments_fp = file_fingerprint(INSTRUMENTS)
    latest_fp = file_fingerprint(LATEST)
    inventory: dict[str, dict[str, Any]] = {
        "stock_ohlcv_adjusted_price": {
            "dataset_category": "stock_ohlcv_adjusted_price",
            "source_id": "formal_option_c_provider",
            "source_boundary": "formal Option C qlib provider calendar/instruments",
            "source_max_date": calendar_max_date(CALENDAR),
            "row_count": "",
            "symbol_count": instrument_count(INSTRUMENTS),
            "evidence_path": rel_path(CALENDAR),
            "checksum": str(calendar_fp.get("sha256") or ""),
            "secondary_evidence_path": rel_path(INSTRUMENTS),
            "secondary_checksum": str(instruments_fp.get("sha256") or ""),
        },
        "twii_market_index": {
            "dataset_category": "twii_market_index",
            "source_id": "formal_provider_or_readonly_twii_bridge",
            "source_boundary": "formal provider calendar or strict E4 readonly bridge",
            "source_max_date": calendar_max_date(CALENDAR),
            "row_count": "",
            "symbol_count": instrument_count(INSTRUMENTS),
            "evidence_path": rel_path(CALENDAR),
            "checksum": str(calendar_fp.get("sha256") or ""),
        },
        "daily_ltr_source_freshness": {
            "dataset_category": "daily_ltr_source_freshness",
            "source_id": "latest_signal_pointer",
            "source_boundary": "latest_signal.json accepted pointer",
            "source_max_date": str(read_json(LATEST).get("asof") or ""),
            "row_count": "",
            "symbol_count": "",
            "evidence_path": rel_path(LATEST),
            "checksum": str(latest_fp.get("sha256") or ""),
        },
    }
    finmind_result = job.get("finmind_update") if isinstance(job.get("finmind_update"), dict) else {}
    stdout_path = Path(str(finmind_result.get("stdout_path") or job_dir / "finmind_stdout.txt"))
    inventory.update(summarize_finmind_stdout(stdout_path))
    for category, source_id in (
        ("finmind_raw_daily_price", "finmind_daily_price"),
        ("institutional_flow", "finmind_institutional_flow"),
        ("margin_short", "finmind_margin_short"),
    ):
        inventory.setdefault(
            category,
            {
                "dataset_category": category,
                "source_id": source_id,
                "source_boundary": "backend/scripts/update_tw_stock_daily.py FinMind workflow stdout",
                "source_max_date": "",
                "source_min_date": "",
                "row_count": 0,
                "symbol_count": 0,
                "archived_count": 0,
                "evidence_path": rel_path(stdout_path) if stdout_path.exists() else "",
                "checksum": str(file_fingerprint(stdout_path).get("sha256") or "") if stdout_path.exists() else "",
            },
        )
    strict_e4 = job.get("strict_e4_readonly_chain") if isinstance(job.get("strict_e4_readonly_chain"), dict) else {}
    yz2_payload = strict_e4.get("yz2_payload") if isinstance(strict_e4.get("yz2_payload"), dict) else {}
    yz2r_payload = strict_e4.get("yz2r_payload") if isinstance(strict_e4.get("yz2r_payload"), dict) else {}
    inventory["orthogonal_raw_archive"] = {
        "dataset_category": "orthogonal_raw_archive",
        "source_id": "strict_e4_yz2_or_finmind_full_scope",
        "source_boundary": "YZ2 orthogonal package manifest / FinMind full-scope stdout",
        "source_max_date": asof if (strict_e4.get("attempted") and strict_e4.get("ok")) else "",
        "row_count": "",
        "symbol_count": "",
        "evidence_path": str(strict_e4.get("model_b_manifest") or yz2_payload.get("model_b_manifest") or ""),
        "checksum": "",
    }
    inventory["readonly_price_twii_calendar_bridge"] = {
        "dataset_category": "readonly_price_twii_calendar_bridge",
        "source_id": "strict_e4_readonly_bridge",
        "source_boundary": "strict E4 readonly price/TWII bridge usage flags",
        "source_max_date": asof if job.get("strict_e4_readonly_bridge_validator_ok") else "",
        "row_count": "",
        "symbol_count": "",
        "evidence_path": str(strict_e4.get("readonly_price_bridge_dir") or strict_e4.get("readonly_twii_bridge") or ""),
        "checksum": "",
    }
    inventory["execution_price_readiness"] = {
        "dataset_category": "execution_price_readiness",
        "source_id": "strict_e4_yz2r_execution_readiness",
        "source_boundary": "YZ2R next-open/close readiness payload",
        "source_max_date": asof if (strict_e4.get("attempted") and strict_e4.get("ok")) else "",
        "row_count": yz2r_payload.get("rows", ""),
        "symbol_count": yz2r_payload.get("symbol_count", ""),
        "evidence_path": str(yz2r_payload.get("manifest") or ""),
        "checksum": "",
    }
    return inventory


def rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve_path(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def bool_cell(value: bool) -> str:
    return "true" if value else "false"


def accounting_row(
    *,
    asof: str,
    category: str,
    source_boundary: str,
    status: str,
    status_reason: str,
    source_max_date: str = "",
    available_at: str = "",
    fetched_at: str = "",
    row_count: str | int = "",
    symbol_count: str | int = "",
    checksum: str = "",
    market_calendar_status: str = "",
    holiday_name: str = "",
    pending_reason: str = "",
    retry_hint: str = "",
    requires_credentials: bool = False,
    requires_network: bool = False,
    requires_provider_refresh: bool = False,
    requires_formal_write: bool = False,
    requires_latest_switch: bool = False,
) -> dict[str, str]:
    return {
        "target_asof": asof,
        "dataset_category": category,
        "source_boundary": source_boundary,
        "source_max_date": source_max_date,
        "available_at": available_at,
        "fetched_at": fetched_at,
        "row_count": str(row_count),
        "symbol_count": str(symbol_count),
        "checksum": checksum,
        "schema_version": DAILY_FULL_CAPTURE_ACCOUNTING_SCHEMA_VERSION,
        "market_calendar_status": market_calendar_status,
        "holiday_name": holiday_name,
        "pending_reason": pending_reason,
        "retry_hint": retry_hint,
        "status": status,
        "status_reason": status_reason,
        "requires_credentials": bool_cell(requires_credentials),
        "requires_network": bool_cell(requires_network),
        "requires_provider_refresh": bool_cell(requires_provider_refresh),
        "requires_formal_write": bool_cell(requires_formal_write),
        "requires_latest_switch": bool_cell(requires_latest_switch),
    }


def infer_market_calendar_status(job: dict[str, Any], asof: str) -> tuple[str, str, str]:
    if job.get("status") == "weekend_no_pending_wait":
        return "non_trading_day_or_weekend", "weekend", "no pull started; next scheduled run should resolve a trading day or pending asof"
    if str(job.get("status") or "") in {"today_data_window_wait", "fresh_data_wait"}:
        return "pending_or_source_delay", "", "retry same asof on next scheduled run"
    formal_tail = calendar_tail(CALENDAR)
    if asof in formal_tail or calendar_max_date(CALENDAR) >= asof:
        return "formal_calendar_covers_asof", "", ""
    return "formal_calendar_missing_asof_or_not_refreshed", "", "run explicitly reviewed provider refresh/publish or readonly bridge route"


def build_daily_full_capture_accounting(job: dict[str, Any], *, asof: str, args: argparse.Namespace) -> tuple[list[dict[str, str]], dict[str, Any]]:
    source_inventory = job.get("daily_source_inventory") if isinstance(job.get("daily_source_inventory"), dict) else {}
    formal_calendar_max = calendar_max_date(CALENDAR)
    latest_payload = read_json(LATEST)
    latest_signal_asof = str(latest_payload.get("asof") or "")
    calendar_status, holiday_name, retry_hint = infer_market_calendar_status(job, asof)
    pending_reason = str(job.get("pending_asof_set") or job.get("qlib_legacy_provider_skip_reason") or "")
    finmind_update = job.get("finmind_update") if isinstance(job.get("finmind_update"), dict) else {}
    strict_e4 = job.get("strict_e4_readonly_chain") if isinstance(job.get("strict_e4_readonly_chain"), dict) else {}
    readonly_snapshot = job.get("readonly_snapshot") if isinstance(job.get("readonly_snapshot"), dict) else {}
    formal_calendar_fp = file_fingerprint(CALENDAR)
    latest_fp = file_fingerprint(LATEST)

    legacy_provider_enabled = bool(job.get("legacy_provider_publish_enabled"))
    provider_published = bool(job.get("provider_publish_triggered") and (job.get("provider_publish") or {}).get("ok"))
    latest_switched = bool(job.get("latest_signal_updated"))
    finmind_attempted = bool(job.get("finmind_update_triggered"))
    finmind_ok = bool(finmind_update.get("ok")) if finmind_update else False
    finmind_full_scope = str(getattr(args, "finmind_scope", "full")) == "full" or bool(job.get("finmind_scope_overridden_for_strict_e4"))
    strict_e4_attempted = bool(strict_e4.get("attempted"))
    strict_e4_ok = bool(strict_e4_attempted and strict_e4.get("ok"))
    bridge_ok = bool(job.get("strict_e4_readonly_bridge_validator_ok"))
    price_inv = source_inventory.get("stock_ohlcv_adjusted_price") if isinstance(source_inventory.get("stock_ohlcv_adjusted_price"), dict) else {}
    twii_inv = source_inventory.get("twii_market_index") if isinstance(source_inventory.get("twii_market_index"), dict) else {}
    finmind_inv = source_inventory.get("finmind_raw_daily_price") if isinstance(source_inventory.get("finmind_raw_daily_price"), dict) else {}
    institutional_inv = source_inventory.get("institutional_flow") if isinstance(source_inventory.get("institutional_flow"), dict) else {}
    margin_inv = source_inventory.get("margin_short") if isinstance(source_inventory.get("margin_short"), dict) else {}
    orthogonal_inv = source_inventory.get("orthogonal_raw_archive") if isinstance(source_inventory.get("orthogonal_raw_archive"), dict) else {}
    ltr_inv = source_inventory.get("daily_ltr_source_freshness") if isinstance(source_inventory.get("daily_ltr_source_freshness"), dict) else {}
    bridge_inv = source_inventory.get("readonly_price_twii_calendar_bridge") if isinstance(source_inventory.get("readonly_price_twii_calendar_bridge"), dict) else {}
    execution_inv = source_inventory.get("execution_price_readiness") if isinstance(source_inventory.get("execution_price_readiness"), dict) else {}
    finmind_date = str(finmind_inv.get("source_max_date") or "")
    institutional_date = str(institutional_inv.get("source_max_date") or "")
    margin_date = str(margin_inv.get("source_max_date") or "")
    finmind_captured = finmind_ok and bool(finmind_inv.get("row_count", 0)) and finmind_date >= asof
    orthogonal_batch = load_orthogonal_batch_control(job)
    orthogonal_batch_status = str(orthogonal_batch.get("status") or "")
    orthogonal_batch_coverage = orthogonal_batch.get("coverage") if isinstance(orthogonal_batch.get("coverage"), dict) else {}
    institutional_batch = orthogonal_batch_coverage.get("institutional") if isinstance(orthogonal_batch_coverage.get("institutional"), dict) else {}
    margin_batch = orthogonal_batch_coverage.get("margin") if isinstance(orthogonal_batch_coverage.get("margin"), dict) else {}
    institutional_batch_complete = bool(
        institutional_batch.get("total_symbol_count")
        and int(institutional_batch.get("done_symbol_count") or 0) >= int(institutional_batch.get("total_symbol_count") or 0)
    )
    margin_batch_complete = bool(
        margin_batch.get("total_symbol_count")
        and int(margin_batch.get("done_symbol_count") or 0) >= int(margin_batch.get("total_symbol_count") or 0)
    )
    institutional_captured = (finmind_ok and finmind_full_scope and bool(institutional_inv.get("row_count", 0)) and institutional_date >= asof) or institutional_batch_complete
    margin_captured = (finmind_ok and finmind_full_scope and bool(margin_inv.get("row_count", 0)) and margin_date >= asof) or margin_batch_complete

    price_status = "captured" if formal_calendar_max >= asof else "needs_explicit_provider_publish_or_bridge"
    if provider_published:
        price_status = "captured_by_explicit_legacy_provider_gate"
    rows = [
        accounting_row(
            asof=asof,
            category="stock_ohlcv_adjusted_price",
            source_boundary="formal_option_c_yahoo_scrapling_provider_calendar",
            source_max_date=str(price_inv.get("source_max_date") or formal_calendar_max),
            row_count=price_inv.get("row_count", ""),
            symbol_count=price_inv.get("symbol_count", ""),
            checksum=str(price_inv.get("checksum") or formal_calendar_fp.get("sha256") or ""),
            market_calendar_status=calendar_status,
            holiday_name=holiday_name,
            pending_reason=pending_reason,
            retry_hint=retry_hint,
            status=price_status,
            status_reason="formal qlib calendar/provider evidence covers target asof" if formal_calendar_max >= asof else "default daily auto does not publish formal qlib provider; explicit gate or bridge required",
            requires_network=not bool(formal_calendar_max >= asof),
            requires_provider_refresh=not bool(formal_calendar_max >= asof),
            requires_formal_write=not bool(formal_calendar_max >= asof),
            requires_latest_switch=False,
        ),
        accounting_row(
            asof=asof,
            category="twii_market_index",
            source_boundary="formal_provider_or_readonly_twii_bridge",
            source_max_date=str(twii_inv.get("source_max_date") or formal_calendar_max),
            row_count=twii_inv.get("row_count", ""),
            symbol_count=twii_inv.get("symbol_count", ""),
            checksum=str(twii_inv.get("checksum") or formal_calendar_fp.get("sha256") or ""),
            market_calendar_status=calendar_status,
            holiday_name=holiday_name,
            pending_reason=pending_reason,
            retry_hint=retry_hint,
            status="captured_or_bridge_available" if (formal_calendar_max >= asof or bridge_ok) else "needs_explicit_provider_publish_or_bridge",
            status_reason="formal calendar or strict E4 readonly TWII bridge is available" if (formal_calendar_max >= asof or bridge_ok) else "TWII freshness is not guaranteed by default FinMind daily raw update",
            requires_network=not bool(formal_calendar_max >= asof or bridge_ok),
            requires_provider_refresh=not bool(formal_calendar_max >= asof or bridge_ok),
            requires_formal_write=False,
            requires_latest_switch=False,
        ),
        accounting_row(
            asof=asof,
            category="finmind_raw_daily_price",
            source_boundary="QuantDinger FinMind raw daily stock archive",
            source_max_date=finmind_date,
            fetched_at=str(job.get("finished_at") or job.get("started_at") or ""),
            row_count=finmind_inv.get("row_count", ""),
            symbol_count=finmind_inv.get("symbol_count", ""),
            checksum=str(finmind_inv.get("checksum") or ""),
            status="captured" if finmind_captured else ("skipped_by_contract" if getattr(args, "skip_finmind", False) else "provider_error_or_incomplete"),
            status_reason="FinMind daily updater returned ok and stdout inventory covers target asof" if finmind_captured else ("--skip-finmind was set" if getattr(args, "skip_finmind", False) else "FinMind updater failed, returned zero rows, or stdout inventory does not cover target asof"),
            requires_network=not getattr(args, "skip_finmind", False),
        ),
        accounting_row(
            asof=asof,
            category="institutional_flow",
            source_boundary="FinMind institutional flow raw/archive source",
            source_max_date=institutional_date,
            fetched_at=str(job.get("finished_at") or job.get("started_at") or ""),
            row_count=institutional_inv.get("row_count", ""),
            symbol_count=institutional_inv.get("symbol_count", ""),
            checksum=str(institutional_inv.get("checksum") or ""),
            status="captured" if institutional_captured else ("skipped_by_contract" if getattr(args, "skip_finmind", False) else (orthogonal_batch_status or ("skipped_by_daily_scope" if str(getattr(args, "finmind_scope", "")) == "daily" else "provider_error_or_missing_evidence"))),
            status_reason="FinMind full scope or quota-aware orthogonal batch covers target asof for institutional flow" if institutional_captured else ("--skip-finmind was set" if getattr(args, "skip_finmind", False) else f"orthogonal_batch_status={orthogonal_batch_status or 'none'}; daily scope or partial batch may need future scheduled runs"),
            requires_network=not getattr(args, "skip_finmind", False),
            requires_provider_refresh=False,
            requires_formal_write=False,
            requires_latest_switch=False,
        ),
        accounting_row(
            asof=asof,
            category="margin_short",
            source_boundary="FinMind margin/short raw/archive source",
            source_max_date=margin_date,
            fetched_at=str(job.get("finished_at") or job.get("started_at") or ""),
            row_count=margin_inv.get("row_count", ""),
            symbol_count=margin_inv.get("symbol_count", ""),
            checksum=str(margin_inv.get("checksum") or ""),
            status="captured" if margin_captured else ("skipped_by_contract" if getattr(args, "skip_finmind", False) else (orthogonal_batch_status or ("skipped_by_daily_scope" if str(getattr(args, "finmind_scope", "")) == "daily" else "provider_error_or_missing_evidence"))),
            status_reason="FinMind full scope or quota-aware orthogonal batch covers target asof for margin/short" if margin_captured else ("--skip-finmind was set" if getattr(args, "skip_finmind", False) else f"orthogonal_batch_status={orthogonal_batch_status or 'none'}; daily scope or partial batch may need future scheduled runs"),
            requires_network=not getattr(args, "skip_finmind", False),
            requires_provider_refresh=False,
            requires_formal_write=False,
            requires_latest_switch=False,
        ),
        accounting_row(
            asof=asof,
            category="orthogonal_raw_archive",
            source_boundary="YZ2 orthogonal package source inputs",
            source_max_date=str(orthogonal_inv.get("source_max_date") or ""),
            row_count=orthogonal_inv.get("row_count", ""),
            symbol_count=orthogonal_inv.get("symbol_count", ""),
            checksum=str(orthogonal_inv.get("checksum") or ""),
            status="captured" if (strict_e4_ok or (institutional_captured and margin_captured)) else (orthogonal_batch_status or "needs_separate_contract"),
            status_reason="strict E4 chain or FinMind institutional/margin inventory provided orthogonal-source evidence" if (strict_e4_ok or (institutional_captured and margin_captured)) else f"quota-aware orthogonal batch is not complete yet; status={orthogonal_batch_status or 'none'}",
            requires_network=not bool(strict_e4_ok),
            requires_provider_refresh=False,
            requires_formal_write=False,
            requires_latest_switch=False,
        ),
        accounting_row(
            asof=asof,
            category="daily_ltr_source_freshness",
            source_boundary="latest_signal.json / model signal artifact pointer",
            source_max_date=str(ltr_inv.get("source_max_date") or latest_signal_asof),
            checksum=str(ltr_inv.get("checksum") or latest_fp.get("sha256") or ""),
            status="captured" if latest_signal_asof >= asof else ("updated_by_explicit_legacy_gate" if latest_switched else "latest_pointer_not_advanced"),
            status_reason="accepted latest signal pointer covers target asof" if latest_signal_asof >= asof else "default path does not switch qlib/LTR accepted latest; signal freshness may lag raw data",
            requires_network=False,
            requires_provider_refresh=False,
            requires_formal_write=False,
            requires_latest_switch=not bool(latest_signal_asof >= asof),
        ),
        accounting_row(
            asof=asof,
            category="readonly_price_twii_calendar_bridge",
            source_boundary="strict E4 readonly bridge inputs",
            source_max_date=str(bridge_inv.get("source_max_date") or ""),
            row_count=bridge_inv.get("row_count", ""),
            symbol_count=bridge_inv.get("symbol_count", ""),
            checksum=str(bridge_inv.get("checksum") or ""),
            status="captured" if bridge_ok else ("skipped_by_contract" if not strict_e4_attempted else "bridge_contract_failed"),
            status_reason="strict E4 readonly bridge validator passed" if bridge_ok else "strict E4 readonly bridge is optional and disabled by default",
            requires_network=False,
            requires_provider_refresh=False,
            requires_formal_write=False,
            requires_latest_switch=False,
        ),
        accounting_row(
            asof=asof,
            category="execution_price_readiness",
            source_boundary="YZ2R next-open/close readiness",
            source_max_date=str(execution_inv.get("source_max_date") or ""),
            row_count=execution_inv.get("row_count", ""),
            symbol_count=execution_inv.get("symbol_count", ""),
            checksum=str(execution_inv.get("checksum") or ""),
            status="captured" if strict_e4_ok else ("skipped_by_contract" if not strict_e4_attempted else "yz2r_failed_or_incomplete"),
            status_reason="strict E4 YZ2R readiness chain passed" if strict_e4_ok else "execution readiness is optional and disabled by default",
            requires_network=False,
            requires_provider_refresh=False,
            requires_formal_write=False,
            requires_latest_switch=False,
        ),
        accounting_row(
            asof=asof,
            category="schema_coverage_holiday_pending_evidence",
            source_boundary="daily orchestrator job + pending_asof + market-calendar heuristics",
            source_max_date=formal_calendar_max,
            checksum=str(formal_calendar_fp.get("sha256") or ""),
            market_calendar_status=calendar_status,
            holiday_name=holiday_name,
            pending_reason=pending_reason,
            retry_hint=retry_hint,
            status="captured",
            status_reason=f"job status={job.get('status')}; readonly_snapshot_attempted={bool(readonly_snapshot.get('attempted'))}",
            requires_network=False,
            requires_provider_refresh=False,
            requires_formal_write=False,
            requires_latest_switch=False,
        ),
    ]
    summary = {
        "schema_version": DAILY_FULL_CAPTURE_ACCOUNTING_SCHEMA_VERSION,
        "target_asof": asof,
        "created_at": utc_now(),
        "required_categories": DAILY_FULL_CAPTURE_CATEGORIES,
        "category_count": len(rows),
        "captured_count": sum(1 for row in rows if row["status"].startswith("captured") or row["status"].startswith("updated")),
        "needs_action_count": sum(
            1
            for row in rows
            if not (
                row["status"].startswith("captured")
                or row["status"].startswith("updated")
                or row["status"] == "skipped_by_contract"
            )
        ),
        "formal_calendar_max": formal_calendar_max,
        "latest_signal_asof": latest_signal_asof,
        "legacy_provider_publish_enabled": legacy_provider_enabled,
        "strict_e4_readonly_chain_enabled": bool(job.get("strict_e4_readonly_chain_enabled")),
        "provider_publish_triggered": bool(job.get("provider_publish_triggered")),
            "accepted_latest_switch_triggered": latest_switched,
            "daily_source_inventory_present": bool(source_inventory),
            "production_trade_enabled": False,
        "research_only": True,
    }
    return rows, summary


def write_daily_full_capture_accounting(job: dict[str, Any], *, job_dir: Path, asof: str, args: argparse.Namespace) -> dict[str, Any]:
    rows, summary = build_daily_full_capture_accounting(job, asof=asof, args=args)
    csv_path = job_dir / "daily_full_capture_accounting.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DAILY_FULL_CAPTURE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    json_path = job_dir / "daily_full_capture_accounting.json"
    payload = {**summary, "rows": rows}
    write_json(json_path, payload)
    job["daily_full_capture_accounting"] = {
        "schema_version": DAILY_FULL_CAPTURE_ACCOUNTING_SCHEMA_VERSION,
        "csv_path": rel_path(csv_path),
        "json_path": rel_path(json_path),
        "category_count": len(rows),
        "required_categories": DAILY_FULL_CAPTURE_CATEGORIES,
        "captured_count": summary["captured_count"],
        "needs_action_count": summary["needs_action_count"],
        "provider_publish_triggered": bool(job.get("provider_publish_triggered")),
        "accepted_latest_switch_triggered": bool(job.get("latest_signal_updated")),
        "production_trade_enabled": False,
        "research_only": True,
    }
    return job["daily_full_capture_accounting"]


def write_daily_source_inventory(job: dict[str, Any], *, job_dir: Path, asof: str) -> dict[str, Any]:
    inventory = build_daily_source_inventory(job, job_dir=job_dir, asof=asof)
    payload = {
        "schema_version": "daily_source_inventory_v1",
        "target_asof": asof,
        "created_at": utc_now(),
        "source_count": len(inventory),
        "sources": inventory,
        "provider_publish_triggered": bool(job.get("provider_publish_triggered")),
        "accepted_latest_switch_triggered": bool(job.get("latest_signal_updated")),
        "production_trade_enabled": False,
        "research_only": True,
    }
    inventory_path = job_dir / "daily_source_inventory.json"
    write_json(inventory_path, payload)
    job["daily_source_inventory"] = inventory
    job["daily_source_inventory_path"] = rel_path(inventory_path)
    return payload


def finalize_job(job: dict[str, Any], *, job_dir: Path, asof: str, args: argparse.Namespace) -> None:
    write_daily_source_inventory(job, job_dir=job_dir, asof=asof)
    write_daily_full_capture_accounting(job, job_dir=job_dir, asof=asof, args=args)
    if bool(getattr(args, "disable_research_data_history", False)):
        job["research_data_history"] = {
            "enabled": False,
            "attempted": False,
            "ok": True,
            "status": "DISABLED_EXPLICITLY",
            "mainline_blocking": False,
            "production_allowed": False,
            "no_apply": True,
        }
    else:
        try:
            job["research_data_history"] = materialize_daily_research_history(
                repo_root=ROOT,
                asof=asof,
                job_id=str(job.get("job_id") or job_dir.name),
                job=job,
                job_dir=job_dir,
            )
        except Exception as exc:
            job["research_data_history"] = {
                "enabled": True,
                "attempted": True,
                "ok": False,
                "status": "ERROR_NONBLOCKING",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "mainline_blocking": False,
                "production_allowed": False,
                "no_apply": True,
            }
    workflow_protected_paths = {
        "formal_provider_calendar": CALENDAR,
        "qlib_accepted_latest": LATEST,
        "legacy_option_c_latest": ROOT
        / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
        "controlled_model_signal_latest": CONTROLLED_MODEL_SIGNAL_LATEST,
        "readonly_snapshot_latest": READONLY_SNAPSHOT_LATEST,
        "agent_prompt_latest": AGENT_DAILY_PROMPT_LATEST,
    }
    job["workflow_model_a_signal_shadow"] = run_daily_model_a_signal_shadow(
        job=job,
        job_dir=job_dir,
        asof=asof,
        enabled=bool(
            getattr(args, "enable_workflow_model_a_signal_shadow", False)
        ),
        repo_root=ROOT,
        python_executable=PYTHON,
        workflow_runner_path=WORKFLOW_MODELA_SIGNAL_SHADOW_RUNNER,
        spec_path=WORKFLOW_MODELA_SIGNAL_SHADOW_SPEC,
        expected_model_id=MODELA_MODEL_ID,
        protected_paths=workflow_protected_paths,
        pending_path=PENDING_ASOF,
        installed_cron_path=INSTALLED_DAILY_CRON,
        command_runner=run_cmd,
    )
    job["workflow_readonly_snapshot_shadow"] = run_daily_readonly_snapshot_shadow(
        job=job,
        job_dir=job_dir,
        asof=asof,
        enabled=bool(
            getattr(args, "enable_workflow_readonly_snapshot_shadow", False)
        ),
        repo_root=ROOT,
        python_executable=PYTHON,
        workflow_runner_path=WORKFLOW_READONLY_SNAPSHOT_SHADOW_RUNNER,
        spec_path=WORKFLOW_READONLY_SNAPSHOT_SHADOW_SPEC,
        expected_model_id=MODELA_MODEL_ID,
        protected_paths=workflow_protected_paths,
        pending_path=PENDING_ASOF,
        installed_cron_path=INSTALLED_DAILY_CRON,
        command_runner=run_cmd,
    )
    job["workflow_readonly_shadow"] = run_daily_workflow_readonly_shadow(
        job=job,
        job_dir=job_dir,
        asof=asof,
        enabled=bool(getattr(args, "enable_workflow_readonly_shadow", False)),
        repo_root=ROOT,
        python_executable=PYTHON,
        workflow_runner_path=WORKFLOW_READONLY_SHADOW_RUNNER,
        spec_path=WORKFLOW_READONLY_SHADOW_SPEC,
        expected_model_id=MODELA_MODEL_ID,
        expected_strategy_rule=STRATEGY_RULE,
        protected_paths=workflow_protected_paths,
        pending_path=PENDING_ASOF,
        installed_cron_path=INSTALLED_DAILY_CRON,
        command_runner=run_cmd,
    )
    write_json(job_dir / "job.json", job)
    attach_daily_readiness_dashboard(job, job_dir=job_dir, asof=asof, args=args)
    write_dng13_daily_chain_artifacts(job, job_dir=job_dir, asof=asof, args=args)
    write_json(job_dir / "job.json", job)


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def parse_json_stdout(command_result: dict[str, Any]) -> dict[str, Any]:
    raw_path = str(command_result.get("stdout_path") or "").strip()
    if not raw_path:
        return {}
    stdout_path = Path(raw_path)
    if not stdout_path.exists():
        return {}
    try:
        return json.loads(stdout_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def next_session_open_for_asof(asof: str, *, calendar_path: Path = CALENDAR) -> str:
    """Return the next known Taiwan session open as an RFC3339 UTC value."""
    target = date.fromisoformat(str(asof))
    dates: list[date] = []
    try:
        for raw in calendar_path.read_text(encoding="utf-8").splitlines():
            value = raw.strip()[:10]
            if value:
                try:
                    parsed = date.fromisoformat(value)
                except ValueError:
                    continue
                if parsed > target:
                    dates.append(parsed)
    except OSError:
        dates = []
    if dates:
        next_day = min(dates)
    else:
        next_day = target + timedelta(days=1)
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
    # Taiwan cash-session open is 09:00 Asia/Taipei = 01:00 UTC.
    return f"{next_day.isoformat()}T01:00:00+00:00"


def protected_latest_fingerprints(
    *,
    readonly_latest_path: Path = READONLY_SNAPSHOT_LATEST,
    agent_latest_path: Path = AGENT_DAILY_PROMPT_LATEST,
    provider_latest_path: Path = LATEST,
    legacy_latest_path: Path = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
) -> dict[str, Any]:
    return {
        "readonly_snapshot_latest": file_fingerprint(readonly_latest_path),
        "agent_prompt_latest": file_fingerprint(agent_latest_path),
        "provider_accepted_latest": file_fingerprint(provider_latest_path),
        "legacy_option_c_latest": file_fingerprint(legacy_latest_path),
    }


def full_orthogonal_protected_fingerprints() -> dict[str, Any]:
    return {
        **protected_latest_fingerprints(),
        "controlled_model_signal_latest": file_fingerprint(CONTROLLED_MODEL_SIGNAL_LATEST),
    }


def should_run_full_orthogonal_refresh(
    *,
    latest_before: str,
    asof: str,
    force: bool,
    skip_finmind: bool,
    finmind_scope: str,
) -> bool:
    return bool(
        latest_before == asof
        and not force
        and not skip_finmind
        and finmind_scope == "full"
    )


def discover_daily_model_track_sources(
    *,
    job: dict[str, Any],
    asof: str,
    include_prior_jobs: bool,
) -> dict[str, Any]:
    """Resolve one immutable qlib provider/normalized pair for both tracks."""
    source_run_id = str(job.get("acquisition_logical_run_id") or "")
    candidates: list[dict[str, Any]] = [job]
    if include_prior_jobs:
        for path in sorted(OPS_ROOT.glob("*/job.json"), reverse=True):
            previous = read_json(path)
            if previous.get("asof") != asof:
                continue
            if previous.get("latest_after") != asof:
                continue
            if previous.get("acquisition_logical_run_id") != source_run_id:
                continue
            candidates.append(previous)

    errors: list[str] = []
    for candidate in candidates:
        refresh_id = str(candidate.get("refresh_job_id") or "")
        publish_id = str(candidate.get("publish_job_id") or "")
        if not refresh_id or Path(refresh_id).name != refresh_id:
            errors.append("refresh_job_id_missing_or_invalid")
            continue
        if not publish_id or Path(publish_id).name != publish_id:
            errors.append("publish_job_id_missing_or_invalid")
            continue
        normalized = QLIB / "data_tw/experiments/option_c_ops" / refresh_id / "candidate_normalized"
        provider = QLIB / "data_tw/experiments/option_c_ops" / publish_id / "tmp/formal_provider_rebuild"
        if not normalized.is_dir() or not provider.is_dir():
            errors.append(f"immutable_source_paths_missing:{candidate.get('job_id') or ''}")
            continue
        return {
            "ok": True,
            "status": "READY",
            "origin_job_id": str(candidate.get("job_id") or ""),
            "refresh_job_id": refresh_id,
            "publish_job_id": publish_id,
            "qlib_normalized": rel_path(normalized),
            "qlib_provider": rel_path(provider),
            "source_acquisition_run_id": source_run_id,
        }
    return {
        "ok": False,
        "status": "BLOCKED_IMMUTABLE_QLIB_SOURCE_NOT_FOUND",
        "source_acquisition_run_id": source_run_id,
        "errors": sorted(set(errors)),
    }


def run_daily_model_track_batch(
    *,
    job: dict[str, Any],
    job_dir: Path,
    asof: str,
    include_prior_jobs: bool,
    timeout_seconds: int,
    command_runner=None,
) -> dict[str, Any]:
    """Run configured model tracks from one source batch with no cross-track input."""
    runner = command_runner or run_cmd
    sources = discover_daily_model_track_sources(
        job=job,
        asof=asof,
        include_prior_jobs=include_prior_jobs,
    )
    source_run_id = str(job.get("acquisition_logical_run_id") or "")
    handoff_path = job_dir / "same_run_handoff_validation.json"
    next_open = next_session_open_for_asof(asof)
    shared_root = job_dir / "daily_model_tracks" / "_shared"
    twii_capture: dict[str, Any] = {
        "ok": False,
        "status": "SKIPPED_SOURCE_NOT_READY",
        "twii_csv": "",
        "twii_manifest": "",
    }
    if sources.get("ok") and source_run_id and handoff_path.is_file():
        twii_capture = capture_b19_twii_snapshot(
            asof=asof,
            source_acquisition_run_id=source_run_id,
            next_session_open=next_open,
            output_dir=shared_root / "b19r2r_twii_capture",
            root=ROOT,
            python=PYTHON,
            capture_runner=B19R2R_TWII_CAPTURE_RUNNER,
            command_runner=runner,
        )
    # All source files, including TWII when available, now precede this one
    # cutoff. Both independent Model A runs and B19R2R bind to this value.
    decision_cutoff = datetime.now(timezone.utc).isoformat()
    provider = resolve_path(str(sources.get("qlib_provider") or ""))
    normalized = resolve_path(str(sources.get("qlib_normalized") or ""))
    dependency_states = {
        "qlib_provider": {
            "ready": bool(sources.get("ok") and provider.is_dir()),
            "path": str(provider),
            "detail": str(sources.get("status") or ""),
        },
        "qlib_normalized": {
            "ready": bool(sources.get("ok") and normalized.is_dir()),
            "path": str(normalized),
            "detail": str(sources.get("status") or ""),
        },
        "source_acquisition": {
            "ready": bool(source_run_id),
            "value": source_run_id,
        },
        "decision_cutoff": {"ready": True, "value": decision_cutoff},
        "orthogonal_handoff": {
            "ready": handoff_path.is_file(),
            "path": str(handoff_path),
        },
        "provider_snapshot": {
            "ready": bool(sources.get("ok") and provider.is_dir()),
            "path": str(provider),
        },
        "next_session_open": {"ready": bool(next_open), "value": next_open},
        "twii_snapshot": {
            "ready": twii_capture.get("ok") is True,
            "value": {
                "twii_csv": str(twii_capture.get("twii_csv") or ""),
                "twii_manifest": str(twii_capture.get("twii_manifest") or ""),
            },
            "detail": str(twii_capture.get("status") or ""),
        },
    }
    services = build_model_track_services(
        root=ROOT,
        python=PYTHON,
        model_a_model_id=MODELA_MODEL_ID,
        model_a_input_builder=MODELA_INPUT_BUILD_SCRIPT,
        model_a_score_runner=MODELA_SCORE_JOB_SCRIPT,
        b19r2r_runner=B19R2R_DAILY_SHADOW_RUNNER,
        command_runner=runner,
        parse_json_stdout=parse_json_stdout,
        timeout=timeout_seconds,
    )
    result = run_daily_model_tracks(
        asof=asof,
        batch_run_id=str(job.get("job_id") or f"daily_{asof}"),
        output_root=job_dir / "daily_model_tracks",
        dependency_states=dependency_states,
        services=services,
    )
    result["source_bundle"] = sources
    result["twii_capture"] = twii_capture
    result["decision_cutoff"] = decision_cutoff
    result["mainline_blocking"] = result.get("ok") is not True
    result["nonblocking_track_failed"] = any(
        track.get("workflow_policy") == "nonblocking" and track.get("ok") is not True
        for track in (result.get("tracks") or {}).values()
    )
    return result


def observed_target_scope_from_capture(capture: dict[str, Any], *, asof: str) -> set[str]:
    observed: set[str] = set()
    for raw_path in capture.get("normalized_paths", []) or []:
        path = resolve_path(str(raw_path))
        payload = read_json(path)
        records = payload.get("records") if isinstance(payload.get("records"), list) else []
        for record in records:
            if not isinstance(record, dict):
                continue
            trade_date = str(record.get("trade_date") or record.get("date") or "")
            symbol = normalize_symbol_code(str(record.get("symbol") or record.get("stock_id") or ""))
            if trade_date == asof and symbol:
                observed.add(symbol)
    return observed


def build_full_orthogonal_refresh_evidence(
    *,
    job: dict[str, Any],
    job_dir: Path,
    asof: str,
    expected_symbol_count: int,
    protected_before: dict[str, Any],
) -> dict[str, Any]:
    finmind = job.get("finmind_update") if isinstance(job.get("finmind_update"), dict) else {}
    captures = finmind.get("hsa8_capture") if isinstance(finmind.get("hsa8_capture"), dict) else {}
    segment_results = finmind.get("segment_results") if isinstance(finmind.get("segment_results"), dict) else {}
    logical_run = finmind.get("logical_acquisition") if isinstance(finmind.get("logical_acquisition"), dict) else {}
    source_rows = summarize_finmind_stdout(job_dir / "finmind_stdout.txt")
    checks: dict[str, Any] = {}
    for segment, category in (("institutional", "institutional_flow"), ("margin", "margin_short")):
        capture = captures.get(segment) if isinstance(captures.get(segment), dict) else {}
        source = source_rows.get(category) if isinstance(source_rows.get(category), dict) else {}
        segment_result = segment_results.get(segment) if isinstance(segment_results.get(segment), dict) else {}
        expected_scope = {str(item) for item in capture.get("expected_scope", [])}
        returned_scope = {str(item) for item in capture.get("returned_scope", [])}
        absent_scope = {str(item) for item in capture.get("absent_scope", [])}
        unknown_scope = {str(item) for item in capture.get("unknown_scope", [])}
        authoritative_scope_closed = bool(
            len(expected_scope) == expected_symbol_count
            and expected_scope == returned_scope | absent_scope
            and not returned_scope & absent_scope
            and not unknown_scope
        )
        observed_target_scope = observed_target_scope_from_capture(capture, asof=asof)
        observed_missing_scope = expected_scope - observed_target_scope
        observed_unexpected_scope = observed_target_scope - expected_scope
        research_scope_complete = bool(
            len(expected_scope) == expected_symbol_count
            and observed_target_scope == expected_scope
        )
        covers_asof = bool(str(source.get("source_max_date") or "") >= asof)
        command_ok = bool(segment_result.get("ok")) if segment_result else False
        checks[category] = {
            "ok": bool(command_ok and research_scope_complete and covers_asof and int(source.get("row_count") or 0) > 0),
            "source_max_date": str(source.get("source_max_date") or ""),
            "row_count": int(source.get("row_count") or 0),
            "expected_scope_count": len(expected_scope),
            "returned_scope_count": len(returned_scope),
            "absent_scope_count": len(absent_scope),
            "unknown_scope_count": len(unknown_scope),
            "authoritative_scope_closed": authoritative_scope_closed,
            "research_observed_scope_count": len(observed_target_scope),
            "research_missing_scope_count": len(observed_missing_scope),
            "research_unexpected_scope_count": len(observed_unexpected_scope),
            "research_scope_complete": research_scope_complete,
            "research_scope_authoritative": False,
            "covers_target_asof": covers_asof,
            "capture_status": str(capture.get("status") or ""),
            "capture_validator_status": str(capture.get("validator_status") or ""),
            "capture_pit_status": str(capture.get("pit_status") or ""),
            "segment_command_observed": bool(segment_result),
            "segment_command_ok": bool(segment_result.get("ok")) if segment_result else None,
            "segment_command_returncode": segment_result.get("returncode") if segment_result else None,
            "segment_command_cached": bool(segment_result.get("cached")) if segment_result else False,
            "segment_provider_error": str(segment_result.get("provider_error") or ""),
        }
    protected_after = full_orthogonal_protected_fingerprints()
    protected_unchanged = protected_latest_unchanged(protected_before, protected_after)
    ok = bool(
        finmind.get("ok")
        and checks
        and all(item.get("ok") for item in checks.values())
        and protected_unchanged["all_protected_paths_unchanged"]
    )
    strict_hsa8_ready = bool(
        checks
        and all(
            item.get("authoritative_scope_closed")
            and item.get("capture_validator_status") == "PASS"
            and item.get("capture_pit_status") == "PASS"
            for item in checks.values()
        )
    )
    return {
        "schema_version": "full_orthogonal_research_refresh.v1",
        "created_at": utc_now(),
        "target_asof": asof,
        "status": "FULL_ORTHOGONAL_REFRESH_PASSED" if ok else "FULL_ORTHOGONAL_REFRESH_INCOMPLETE",
        "ok": ok,
        "research_capture_only": True,
        "research_observed_scope_is_not_authoritative": True,
        "strict_pit_or_formal_oos_claimed": False,
        "strict_hsa8_ready": strict_hsa8_ready,
        "strict_hsa8_blocked": not strict_hsa8_ready,
        "strict_model_b_generation_triggered": False,
        "legacy_compatible_model_b_status": MODELB_LEGACY_COMPATIBILITY["status"],
        "required_source_checks": checks,
        "segmented_acquisition_ok": bool(finmind.get("ok")),
        "logical_acquisition": {
            "logical_run_id": str(logical_run.get("logical_run_id") or ""),
            "status": str(logical_run.get("status") or ""),
            "handoff_allowed": bool(logical_run.get("handoff_allowed")),
        },
        "orthogonal_batch_triggered": bool(job.get("finmind_orthogonal_batch_update_triggered")),
        "orthogonal_batch_skipped_reason": str(job.get("finmind_orthogonal_batch_skipped_reason") or ""),
        "protected_latest_before": protected_before,
        "protected_latest_after": protected_after,
        "protected_latest_unchanged": protected_unchanged,
        "provider_publish_triggered": False,
        "accepted_latest_switch_triggered": False,
        "controlled_signal_latest_write": False,
        "readonly_snapshot_latest_write": False,
        "agent_prompt_latest_write": False,
    }


def fingerprint_same(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return all(
        before.get(key) == after.get(key)
        for key in ("exists", "size", "sha256")
    )


def protected_latest_unchanged(before: dict[str, Any], after: dict[str, Any]) -> dict[str, bool]:
    checks = {
        name: fingerprint_same(
            before.get(name) if isinstance(before.get(name), dict) else {},
            after.get(name) if isinstance(after.get(name), dict) else {},
        )
        for name in sorted(set(before) | set(after))
    }
    checks["all_protected_paths_unchanged"] = all(checks.values()) if checks else True
    return checks


def ador_forbidden_action_audit() -> dict[str, Any]:
    actions = {
        "provider_or_network_pull": False,
        "provider_publish": False,
        "accepted_latest_switch": False,
        "legacy_latest_switch": False,
        "model_scoring_or_training": False,
        "strategy_replay": False,
        "intent_artifact_generation": False,
        "replay_or_nav_generation": False,
        "openai_call": False,
        "daily_automation_default_switch": False,
        "monitor_or_broker_or_order_path": False,
        "trade_size_or_allocation_output": False,
        "readonly_snapshot_latest_write": False,
        "agent_prompt_latest_write": False,
    }
    return {
        "schema_version": "ador2.forbidden_action_audit.v1",
        "created_at": utc_now(),
        "all_false": not any(actions.values()),
        "actions": actions,
    }


def latest_manifest_exists(latest_payload: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        value = str(latest_payload.get(key) or "").strip()
        if value and resolve_path(value).exists():
            return True
    return False


def build_ador_source_readiness_observation(
    *,
    asof: str,
    job_id: str,
    job_dir: Path,
    job: dict[str, Any],
    readonly_latest_path: Path,
    agent_latest_path: Path,
    before_fingerprints: dict[str, Any],
) -> dict[str, Any]:
    readonly_latest = read_json(readonly_latest_path)
    agent_latest = read_json(agent_latest_path)
    chain_status = read_json(job_dir / "daily_chain_status.json")
    source_inventory = source_inventory_for_chain(job, job_dir=job_dir)
    accounting = read_json(job_dir / "daily_full_capture_accounting.json")
    blockers: list[str] = []

    readonly_asof = str(readonly_latest.get("signal_asof") or readonly_latest.get("asof") or readonly_latest.get("data_asof") or "")
    agent_asof = str(agent_latest.get("signal_asof") or agent_latest.get("asof") or "")
    if readonly_asof != asof:
        blockers.append("readonly_snapshot_latest_asof_mismatch_or_missing")
    if agent_asof != asof:
        blockers.append("agent_prompt_latest_asof_mismatch_or_missing")
    if not latest_manifest_exists(readonly_latest, "snapshot_manifest", "manifest"):
        blockers.append("readonly_snapshot_manifest_missing")
    if not latest_manifest_exists(agent_latest, "manifest"):
        blockers.append("agent_prompt_manifest_missing")
    if str(agent_latest.get("source_readonly_snapshot_latest") or "") not in {"", rel_path(readonly_latest_path)}:
        blockers.append("agent_prompt_source_readonly_latest_mismatch")

    return {
        "schema_version": "ador2.source_readiness_observation.v1",
        "created_at": utc_now(),
        "asof": asof,
        "job_id": job_id,
        "job_dir": rel_path(job_dir),
        "observation_mode": "no_publish_dry_run",
        "source_readiness_state": "READY_FOR_NO_WRITE_PLAN" if not blockers else "BLOCKED_WITH_REASON",
        "blockers": blockers,
        "daily_chain_state": str(chain_status.get("state") or ""),
        "raw_status": str(chain_status.get("raw_status") or ""),
        "model_signal_status": str(chain_status.get("model_a_signal_status") or ""),
        "source_inventory_path": rel_path(job_dir / "daily_source_inventory.json") if source_inventory else "",
        "capture_accounting_path": rel_path(job_dir / "daily_full_capture_accounting.json") if accounting else "",
        "readonly_latest": {
            "path": rel_path(readonly_latest_path),
            "signal_asof": readonly_asof,
            "manifest": str(readonly_latest.get("snapshot_manifest") or readonly_latest.get("manifest") or ""),
            "fingerprint": before_fingerprints.get("readonly_snapshot_latest", {}),
        },
        "agent_latest": {
            "path": rel_path(agent_latest_path),
            "signal_asof": agent_asof,
            "manifest": str(agent_latest.get("manifest") or ""),
            "fingerprint": before_fingerprints.get("agent_prompt_latest", {}),
        },
        "forbidden_actions": ador_forbidden_action_audit(),
    }


def build_ador_readonly_no_write_plan(asof: str, observation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "ador2.readonly_snapshot_no_write_plan.v1",
        "created_at": utc_now(),
        "asof": asof,
        "plan_mode": "no_publish_dry_run",
        "execution_performed": False,
        "latest_pointer_write_planned": False,
        "latest_pointer_write_performed": False,
        "source_readiness_state": observation.get("source_readiness_state"),
        "blockers": observation.get("blockers", []),
        "planned_command_schema": [
            PYTHON,
            rel_path(READONLY_PUBLISH_SCRIPT),
            "--out-root",
            rel_path(READONLY_SNAPSHOT_ROOT),
            "--no-latest",
            "--json",
        ],
        "planned_validator_schema": [
            PYTHON,
            rel_path(READONLY_VALIDATE_SCRIPT),
            "--manifest",
            "<staged_manifest>",
            "--json",
        ],
    }


def build_ador_agent_prompt_no_write_plan(asof: str, observation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "ador2.agent_prompt_no_write_plan.v1",
        "created_at": utc_now(),
        "asof": asof,
        "plan_mode": "no_publish_dry_run",
        "execution_performed": False,
        "latest_pointer_write_planned": False,
        "latest_pointer_write_performed": False,
        "source_readiness_state": observation.get("source_readiness_state"),
        "blockers": observation.get("blockers", []),
        "planned_builder_schema": [
            PYTHON,
            rel_path(AGENT_DAILY_PROMPT_BUILD_SCRIPT),
            "--source-dir",
            "<artifact_backed_source_dir>",
            "--out-dir",
            "<job_dir_only_staging_dir>",
            "--json",
        ],
        "planned_validator_schema": [
            PYTHON,
            rel_path(AGENT_DAILY_PROMPT_VALIDATE_SCRIPT),
            "<job_dir_only_staging_dir>",
            "--json",
        ],
    }


def run_ador_no_publish_orchestration_dry_run(
    *,
    asof: str,
    job_dir: Path,
    job_id: str = "",
    job: dict[str, Any] | None = None,
    enabled: bool | None = None,
    dry_run: bool | None = None,
    agent_prompt_dry_run: bool | None = None,
    agent_prompt_publish_enabled: bool | None = None,
    agent_prompt_publish_latest: bool | None = None,
    readonly_latest_path: Path = READONLY_SNAPSHOT_LATEST,
    agent_latest_path: Path = AGENT_DAILY_PROMPT_LATEST,
    provider_latest_path: Path = LATEST,
    legacy_latest_path: Path = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    command_runner=None,
) -> dict[str, Any]:
    enabled = env_flag("ENABLE_TW_ADOR_NO_PUBLISH_ORCHESTRATION_DRY_RUN", False) if enabled is None else enabled
    dry_run = env_flag("TW_ADOR_NO_PUBLISH_ORCHESTRATION_DRY_RUN", True) if dry_run is None else dry_run
    agent_prompt_dry_run = env_flag("TW_AGENT_DAILY_PROMPT_DRY_RUN", True) if agent_prompt_dry_run is None else agent_prompt_dry_run
    agent_prompt_publish_enabled = env_flag("ENABLE_TW_AGENT_DAILY_PROMPT_PUBLISH", False) if agent_prompt_publish_enabled is None else agent_prompt_publish_enabled
    agent_prompt_publish_latest = env_flag("TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST", False) if agent_prompt_publish_latest is None else agent_prompt_publish_latest

    result: dict[str, Any] = {
        "schema_version": "ador2.no_publish_orchestration.summary.v1",
        "created_at": utc_now(),
        "enabled": bool(enabled),
        "attempted": False,
        "ok": True,
        "status": "disabled_by_default",
        "dry_run": bool(dry_run),
        "agent_prompt_dry_run": bool(agent_prompt_dry_run),
        "agent_prompt_publish_enabled": bool(agent_prompt_publish_enabled),
        "agent_prompt_publish_latest": bool(agent_prompt_publish_latest),
        "latest_pointer_write_performed": False,
        "job_dir_only_evidence": False,
        "evidence_paths": {},
    }
    if not enabled:
        return result

    result["attempted"] = True
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "same_run_handoff_artifacts").mkdir(mode=0o750, exist_ok=True)
    before = protected_latest_fingerprints(
        readonly_latest_path=readonly_latest_path,
        agent_latest_path=agent_latest_path,
        provider_latest_path=provider_latest_path,
        legacy_latest_path=legacy_latest_path,
    )
    observation = build_ador_source_readiness_observation(
        asof=asof,
        job_id=job_id,
        job_dir=job_dir,
        job=job or {},
        readonly_latest_path=readonly_latest_path,
        agent_latest_path=agent_latest_path,
        before_fingerprints=before,
    )
    readonly_plan = build_ador_readonly_no_write_plan(asof, observation)
    agent_plan = build_ador_agent_prompt_no_write_plan(asof, observation)
    forbidden = ador_forbidden_action_audit()

    # ARCH-5: exercise the same six-stage boundary used by the converged
    # runtime. Every callback is a no-write plan marker; the publish gate is
    # deliberately fail-closed so artifact_publish and ops_status cannot run.
    stage_order: list[str] = []
    stage_calls = {name: 0 for name in ("acquisition", "readiness", "signal", "strategy", "artifact_publish", "ops_status")}

    def _plan_stage(name: str):
        def callback(context):
            stage_order.append(name)
            stage_calls[name] += 1
            return {"ok": True, "status": "planned_no_write", "stage": name, "asof": asof, "job_id": job_id}
        return callback

    named_adapters = build_named_stage_adapters(
        acquisition=_plan_stage("acquisition"),
        readiness=_plan_stage("readiness"),
        model_a_signal=_plan_stage("signal"),
        model_b_shadow=_plan_stage("model_b_shadow"),
        strategy=_plan_stage("strategy"),
        artifact_publish=_plan_stage("artifact_publish"),
        ops_status=_plan_stage("ops_status"),
    )
    # Keep the existing six-stage order/failure behavior while making each
    # ownership boundary explicit for the incremental migration.
    stage_facade = {name: named_adapters[name] for name in stage_calls}
    stage_result = run_stage_orchestrator(
        stage_facade,
        context={"asof": asof, "job_id": job_id, "mode": "no_publish_dry_run"},
        protected_paths={
            "readonly_snapshot_latest": readonly_latest_path,
            "agent_prompt_latest": agent_latest_path,
            "provider_latest": provider_latest_path,
            "legacy_latest": legacy_latest_path,
        },
        publish_precondition=lambda context: {"ok": False, "reason": "no_publish_dry_run"},
        root=job_dir,
    )
    stage_result.update({"stage_order": stage_order, "stage_calls": stage_calls,
                         "provider_calls": 0, "publish_calls": stage_calls["artifact_publish"],
                         "order_calls": 0, "latest_parity": bool(stage_result.get("protected_fingerprint_audit", {}).get("ok")),
                         "named_stage_contracts": stage_contract_summary(named_adapters)})
    after = protected_latest_fingerprints(
        readonly_latest_path=readonly_latest_path,
        agent_latest_path=agent_latest_path,
        provider_latest_path=provider_latest_path,
        legacy_latest_path=legacy_latest_path,
    )
    unchanged = protected_latest_unchanged(before, after)
    # ARCH-2 shared audit helper records the same real before/after values;
    # publishing remains disabled for this orchestration path.
    shared_audit = no_publish_fingerprint_audit(before, after)
    protected_payload = {
        "schema_version": "ador2.protected_paths_fingerprint.v1",
        "created_at": utc_now(),
        "before": before,
        "after": after,
        "unchanged": unchanged,
        "readonly_snapshot_latest_unchanged": bool(unchanged.get("readonly_snapshot_latest")),
        "agent_prompt_latest_unchanged": bool(unchanged.get("agent_prompt_latest")),
    }

    blocked_controls = []
    if not dry_run:
        blocked_controls.append("ador_dry_run_disabled")
    if not agent_prompt_dry_run:
        blocked_controls.append("agent_prompt_dry_run_disabled")
    if agent_prompt_publish_enabled:
        blocked_controls.append("agent_prompt_publish_gate_enabled")
    if agent_prompt_publish_latest:
        blocked_controls.append("agent_prompt_publish_latest_enabled")

    result.update({
        "status": "no_write_plan_recorded" if not blocked_controls else "blocked_by_non_dry_run_or_publish_control",
        "ok": bool(forbidden.get("all_false") and unchanged.get("all_protected_paths_unchanged") and not blocked_controls),
        "source_readiness_state": observation.get("source_readiness_state"),
        "blockers": observation.get("blockers", []),
        "blocked_controls": blocked_controls,
        "protected_paths_unchanged": bool(unchanged.get("all_protected_paths_unchanged")),
        "shared_fingerprint_audit": shared_audit,
        "readonly_snapshot_latest_unchanged": bool(unchanged.get("readonly_snapshot_latest")),
        "agent_prompt_latest_unchanged": bool(unchanged.get("agent_prompt_latest")),
        "forbidden_actions_all_false": bool(forbidden.get("all_false")),
        "job_dir_only_evidence": True,
        "stage_adapter": stage_result,
    })

    evidence = {
        "source_readiness_observation": job_dir / "ador_source_readiness_observation.json",
        "readonly_snapshot_no_write_plan": job_dir / "ador_readonly_snapshot_no_write_plan.json",
        "agent_prompt_no_write_plan": job_dir / "ador_agent_prompt_no_write_plan.json",
        "protected_paths_fingerprint": job_dir / "ador_protected_paths_fingerprint.json",
        "forbidden_action_audit": job_dir / "ador_forbidden_action_audit.json",
        "stage_adapter": job_dir / "ador_six_stage_adapter.json",
        "summary": job_dir / "ador_no_publish_orchestration_summary.json",
    }
    write_json(evidence["source_readiness_observation"], observation)
    write_json(evidence["readonly_snapshot_no_write_plan"], readonly_plan)
    write_json(evidence["agent_prompt_no_write_plan"], agent_plan)
    write_json(evidence["protected_paths_fingerprint"], protected_payload)
    write_json(evidence["forbidden_action_audit"], forbidden)
    write_json(evidence["stage_adapter"], stage_result)
    result["evidence_paths"] = {name: rel_path(path) for name, path in evidence.items()}
    write_json(evidence["summary"], result)
    return result


def fpala_candidate_dir_from_provider_gate(provider_candidate_gate: dict[str, Any] | None) -> Path | None:
    gate = provider_candidate_gate if isinstance(provider_candidate_gate, dict) else {}
    for key in ("readiness_path", "decision_path"):
        raw = str(gate.get(key) or "").strip()
        if raw:
            path = resolve_path(raw)
            if path.exists():
                return path.parent
    candidate = gate.get("candidate") if isinstance(gate.get("candidate"), dict) else {}
    for key in ("readiness_path", "decision_path"):
        raw = str(candidate.get(key) or "").strip()
        if raw:
            path = resolve_path(raw)
            if path.exists():
                return path.parent
    raw_dir = str(gate.get("candidate_job_dir") or candidate.get("candidate_job_dir") or "").strip()
    if raw_dir:
        path = resolve_path(raw_dir)
        if path.exists():
            return path
    return None


def fpala_protected_fingerprints(
    *,
    formal_provider_calendar_path: Path = CALENDAR,
    qlib_accepted_latest_path: Path = LATEST,
    legacy_latest_path: Path = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    dapr18_signal_latest_path: Path = CONTROLLED_MODEL_SIGNAL_LATEST,
    readonly_snapshot_latest_path: Path = READONLY_SNAPSHOT_LATEST,
    agent_prompt_latest_path: Path = AGENT_DAILY_PROMPT_LATEST,
    installed_cron_path: Path = OPS_ROOT / "tw-daily-auto-update.installed.cron",
) -> dict[str, Any]:
    return {
        "formal_provider_calendar": file_fingerprint(formal_provider_calendar_path),
        "qlib_accepted_latest": file_fingerprint(qlib_accepted_latest_path),
        "legacy_latest": file_fingerprint(legacy_latest_path),
        "dapr18_signal_latest": file_fingerprint(dapr18_signal_latest_path),
        "readonly_snapshot_latest": file_fingerprint(readonly_snapshot_latest_path),
        "agent_prompt_latest": file_fingerprint(agent_prompt_latest_path),
        "installed_cron": file_fingerprint(installed_cron_path),
    }


def qald_protected_latest_fingerprints(
    *,
    qlib_accepted_latest_path: Path = LATEST,
    legacy_latest_path: Path = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    dapr18_signal_latest_path: Path = CONTROLLED_MODEL_SIGNAL_LATEST,
    readonly_snapshot_latest_path: Path = READONLY_SNAPSHOT_LATEST,
    agent_prompt_latest_path: Path = AGENT_DAILY_PROMPT_LATEST,
) -> dict[str, Any]:
    return {
        "qlib_accepted_latest": file_fingerprint(qlib_accepted_latest_path),
        "legacy_latest": file_fingerprint(legacy_latest_path),
        "dapr18_signal_latest": file_fingerprint(dapr18_signal_latest_path),
        "readonly_snapshot_latest": file_fingerprint(readonly_snapshot_latest_path),
        "agent_prompt_latest": file_fingerprint(agent_prompt_latest_path),
    }


def qald_forbidden_scope_audit(*, protected_changed: bool = False) -> dict[str, Any]:
    actions = {
        "provider_pull_or_refresh": False,
        "provider_publish": False,
        "formal_provider_mutation": False,
        "qlib_refresh": False,
        "accepted_latest_pointer_write": False,
        "legacy_latest_write": False,
        "dapr18_signal_latest_write": False,
        "readonly_snapshot_latest_write": False,
        "agent_prompt_latest_write": False,
        "daily_auto_manual_run": False,
        "cron_changed": False,
        "openai_call": False,
        "db_access_or_write": False,
        "strategy_replay": False,
        "monitor_broker_order_target": False,
        "frontend_api_default_switch": False,
        "protected_latest_changed": bool(protected_changed),
    }
    return {
        "schema_version": "qald2r.forbidden_scope_audit.v1",
        "created_at": utc_now(),
        "all_false": not any(actions.values()),
        "actions": actions,
    }


def qald_candidate_root_from_provider_gate(provider_candidate_gate: dict[str, Any] | None) -> Path | None:
    gate = provider_candidate_gate if isinstance(provider_candidate_gate, dict) else {}
    candidate = gate.get("candidate") if isinstance(gate.get("candidate"), dict) else {}
    for raw in (
        gate.get("candidate_job_dir"),
        candidate.get("candidate_job_dir"),
    ):
        path = resolve_path(str(raw or "").strip())
        if str(raw or "").strip() and path.exists():
            return path
    for key in ("candidate_job_readiness_path", "candidate_job_decision_path", "reused_readiness_path", "reused_decision_path", "readiness_path", "decision_path"):
        raw = str(gate.get(key) or candidate.get(key) or "").strip()
        if not raw:
            continue
        path = resolve_path(raw)
        if path.exists():
            parent = path.parent
            if (parent / "reports/staged_prediction.csv").exists():
                return parent
            payload = read_json(path)
            raw_dir = str(payload.get("candidate_job_dir") or payload.get("job_dir") or "").strip()
            candidate_dir = resolve_path(raw_dir) if raw_dir else Path("")
            if raw_dir and candidate_dir.exists():
                return candidate_dir
    return None


def qald_reader_validation_from_builder_summary(summary: dict[str, Any]) -> dict[str, Any]:
    validation = summary.get("reader_validation") if isinstance(summary.get("reader_validation"), dict) else {}
    return {
        "ok": validation.get("ok") is True,
        "asof": validation.get("asof"),
        "run_id": validation.get("run_id"),
        "top30_count": validation.get("top30_count"),
        "top50_count": validation.get("top50_count"),
        "status": validation.get("status"),
    }


def run_qald_accepted_latest_candidate_builder_no_publish(
    *,
    asof: str,
    job_id: str,
    job_dir: Path,
    provider_candidate_gate: dict[str, Any] | None = None,
    model_signal_gate: dict[str, Any] | None = None,
    fpala_gate: dict[str, Any] | None = None,
    enabled: bool | None = None,
    no_pointer: bool | None = None,
    allow_pointer_write: bool | None = None,
    exact_authorization_id: str | None = None,
    target_asof_override: str | None = None,
    source_root_override: str | None = None,
    fpala_exact_authorization_id: str = "",
    dapr18_exact_authorization_id: str = "",
    timeout_seconds: int = 1200,
    builder_script: Path = QALD_ACCEPTED_LATEST_CANDIDATE_BUILDER_SCRIPT,
    qlib_accepted_latest_path: Path = LATEST,
    legacy_latest_path: Path = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    dapr18_signal_latest_path: Path = CONTROLLED_MODEL_SIGNAL_LATEST,
    readonly_snapshot_latest_path: Path = READONLY_SNAPSHOT_LATEST,
    agent_prompt_latest_path: Path = AGENT_DAILY_PROMPT_LATEST,
    skip_reason: str = "",
    command_runner=None,
) -> dict[str, Any]:
    command_runner = command_runner or run_cmd
    enabled = env_flag("ENABLE_TW_QALD_ACCEPTED_LATEST_CANDIDATE_BUILDER", False) if enabled is None else enabled
    no_pointer = env_flag("TW_QALD_ACCEPTED_LATEST_CANDIDATE_NO_POINTER", True) if no_pointer is None else no_pointer
    allow_pointer_write = env_flag("TW_QALD_ACCEPTED_LATEST_CANDIDATE_ALLOW_POINTER_WRITE", False) if allow_pointer_write is None else allow_pointer_write
    exact_authorization_id = os.getenv("TW_QALD_ACCEPTED_LATEST_CANDIDATE_EXACT_AUTHORIZATION_ID", "") if exact_authorization_id is None else exact_authorization_id
    target_asof = str(target_asof_override or os.getenv("TW_QALD_ACCEPTED_LATEST_CANDIDATE_TARGET_ASOF", "") or asof).strip()
    source_root_raw = str(source_root_override or os.getenv("TW_QALD_ACCEPTED_LATEST_CANDIDATE_SOURCE_ROOT", "") or "").strip()
    evidence_path = job_dir / "qald2r_accepted_latest_candidate_preflight.json"
    before = qald_protected_latest_fingerprints(
        qlib_accepted_latest_path=qlib_accepted_latest_path,
        legacy_latest_path=legacy_latest_path,
        dapr18_signal_latest_path=dapr18_signal_latest_path,
        readonly_snapshot_latest_path=readonly_snapshot_latest_path,
        agent_prompt_latest_path=agent_prompt_latest_path,
    )
    result: dict[str, Any] = {
        "schema_version": "qald2r.accepted_latest_candidate_preflight.v1",
        "created_at": utc_now(),
        "target_asof": target_asof,
        "job_id": job_id,
        "enabled": bool(enabled),
        "attempted": False,
        "ok": True,
        "status": "disabled_by_default",
        "run_id": "",
        "source_candidate_root": "",
        "builder_stdout_path": "",
        "builder_stderr_path": "",
        "builder_execution_summary_path": "",
        "reader_validation": {"ok": False, "asof": None, "run_id": None, "top30_count": None, "top50_count": None},
        "protected_pointer_before_fingerprints": before,
        "protected_pointer_after_fingerprints": {},
        "protected_pointer_unchanged": True,
        "forbidden_scope_audit": qald_forbidden_scope_audit(),
        "accepted_latest_switch_authorization_required": True,
        "latest_signal_updated": False,
        "no_pointer": bool(no_pointer),
        "allow_pointer_write": bool(allow_pointer_write),
        "exact_authorization_present": bool(str(exact_authorization_id or "").strip()),
        "provider_publish_triggered": False,
        "provider_pull_or_refresh_triggered": False,
        "qlib_refresh_triggered": False,
        "accepted_latest_switch_triggered": False,
        "legacy_latest_switch_triggered": False,
    }
    if not enabled:
        result["protected_pointer_after_fingerprints"] = before
        write_json(evidence_path, result)
        return result
    if skip_reason:
        result.update({
            "ok": True,
            "status": f"skipped_by_{skip_reason}",
            "protected_pointer_after_fingerprints": before,
        })
        write_json(evidence_path, result)
        return result

    result["attempted"] = True
    blocked_controls: list[str] = []
    if not no_pointer:
        blocked_controls.append("qald_no_pointer_false")
    if allow_pointer_write:
        blocked_controls.append("qald_allow_pointer_write_true")
    auth = str(exact_authorization_id or "").strip()
    if auth and auth in {str(fpala_exact_authorization_id or "").strip(), str(dapr18_exact_authorization_id or "").strip()}:
        blocked_controls.append("qald_auth_must_not_reuse_fpala_or_dapr18_authorization")
    if target_asof != asof and not is_iso_date_like(target_asof):
        blocked_controls.append("qald_target_asof_not_iso_date")
    provider_ok = bool((provider_candidate_gate or {}).get("ok"))
    model_ok = bool((model_signal_gate or {}).get("ok"))
    fpala_ok = True if not fpala_gate else bool(fpala_gate.get("ok"))
    if not provider_ok:
        blocked_controls.append("provider_candidate_gate_not_ready")
    if not model_ok:
        blocked_controls.append("model_signal_gate_not_ready")
    if not fpala_ok:
        blocked_controls.append("fpala_gate_not_ready")

    source_root = resolve_path(source_root_raw) if source_root_raw else qald_candidate_root_from_provider_gate(provider_candidate_gate)
    if source_root is None:
        blocked_controls.append("source_candidate_root_unresolved")
    elif not source_root.exists():
        blocked_controls.append("source_candidate_root_missing")
    elif not (source_root / "reports/staged_prediction.csv").exists():
        blocked_controls.append("source_candidate_root_missing_staged_prediction")
    else:
        result["source_candidate_root"] = rel_path(source_root)

    if blocked_controls:
        after = qald_protected_latest_fingerprints(
            qlib_accepted_latest_path=qlib_accepted_latest_path,
            legacy_latest_path=legacy_latest_path,
            dapr18_signal_latest_path=dapr18_signal_latest_path,
            readonly_snapshot_latest_path=readonly_snapshot_latest_path,
            agent_prompt_latest_path=agent_prompt_latest_path,
        )
        unchanged = protected_latest_unchanged(before, after)
        result.update({
            "ok": False,
            "status": "blocked_by_qald2r_preflight_controls",
            "blocked_controls": blocked_controls,
            "protected_pointer_after_fingerprints": after,
            "protected_pointer_unchanged": bool(unchanged.get("all_protected_paths_unchanged")),
            "forbidden_scope_audit": qald_forbidden_scope_audit(protected_changed=not bool(unchanged.get("all_protected_paths_unchanged"))),
        })
        write_json(evidence_path, result)
        return result

    run_id = f"option_c_daily_signal_{target_asof.replace('-', '')}_qald2r_candidate_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    job_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = job_dir / "qald2r_accepted_latest_candidate_builder_stdout.json"
    stderr_path = job_dir / "qald2r_accepted_latest_candidate_builder_stderr.txt"
    builder = command_runner(
        [
            PYTHON,
            str(builder_script.relative_to(ROOT) if builder_script.is_absolute() and ROOT in builder_script.parents else builder_script),
            "--target-asof",
            target_asof,
            "--source-candidate-root",
            rel_path(source_root),
            "--run-id",
            run_id,
        ],
        cwd=ROOT,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        timeout=timeout_seconds,
    )
    builder_summary = parse_json_stdout(builder)
    builder_job_dir = resolve_path(str(builder_summary.get("job_dir") or ""))
    execution_summary_path = builder_job_dir / "reports/execution_summary.json" if str(builder_summary.get("job_dir") or "").strip() else Path("")
    reader_validation = qald_reader_validation_from_builder_summary(builder_summary)
    after = qald_protected_latest_fingerprints(
        qlib_accepted_latest_path=qlib_accepted_latest_path,
        legacy_latest_path=legacy_latest_path,
        dapr18_signal_latest_path=dapr18_signal_latest_path,
        readonly_snapshot_latest_path=readonly_snapshot_latest_path,
        agent_prompt_latest_path=agent_prompt_latest_path,
    )
    unchanged = protected_latest_unchanged(before, after)
    protected_unchanged = bool(unchanged.get("all_protected_paths_unchanged"))
    result.update({
        "ok": bool(builder.get("ok") and reader_validation.get("ok") and reader_validation.get("top30_count") == 30 and reader_validation.get("top50_count") == 50 and protected_unchanged),
        "status": "candidate_built_no_pointer" if builder.get("ok") and protected_unchanged else "blocked_by_candidate_builder_or_protected_fingerprint",
        "run_id": run_id,
        "builder": builder,
        "builder_stdout_path": rel_path(stdout_path),
        "builder_stderr_path": rel_path(stderr_path),
        "builder_execution_summary_path": rel_path(execution_summary_path) if execution_summary_path else "",
        "reader_validation": reader_validation,
        "protected_pointer_after_fingerprints": after,
        "protected_pointer_unchanged": protected_unchanged,
        "forbidden_scope_audit": qald_forbidden_scope_audit(protected_changed=not protected_unchanged),
    })
    if not result["ok"] and builder.get("ok"):
        result["status"] = "blocked_by_reader_validation_or_protected_fingerprint"
    write_json(evidence_path, result)
    return result


def attach_qald_accepted_latest_candidate_preflight(
    job: dict[str, Any],
    *,
    asof: str,
    job_id: str,
    job_dir: Path,
    args: argparse.Namespace,
    provider_candidate_gate: dict[str, Any] | None = None,
    model_signal_gate: dict[str, Any] | None = None,
    fpala_gate: dict[str, Any] | None = None,
    skip_reason: str = "",
) -> dict[str, Any]:
    result = run_qald_accepted_latest_candidate_builder_no_publish(
        asof=asof,
        job_id=job_id,
        job_dir=job_dir,
        provider_candidate_gate=provider_candidate_gate,
        model_signal_gate=model_signal_gate,
        fpala_gate=fpala_gate,
        enabled=bool(args.enable_qald_accepted_latest_candidate_builder),
        no_pointer=bool(args.qald_accepted_latest_candidate_no_pointer),
        allow_pointer_write=bool(args.qald_accepted_latest_candidate_allow_pointer_write),
        exact_authorization_id=args.qald_accepted_latest_candidate_exact_authorization_id,
        target_asof_override=args.qald_accepted_latest_candidate_target_asof,
        source_root_override=args.qald_accepted_latest_candidate_source_root,
        fpala_exact_authorization_id=args.fpala_exact_authorization_id,
        dapr18_exact_authorization_id=args.dapr18_exact_authorization_id,
        timeout_seconds=int(args.timeout_seconds),
        skip_reason=skip_reason,
    )
    job["qald_accepted_latest_candidate"] = result
    if result.get("attempted") and not result.get("ok"):
        job["qald_accepted_latest_candidate_warning"] = result.get("status") or "qald accepted latest candidate no-publish gate blocked"
    write_json(job_dir / "job.json", job)
    return result


def run_fpala_formal_accepted_latest_no_publish_preflight(
    *,
    asof: str,
    job_id: str,
    job_dir: Path,
    job: dict[str, Any] | None = None,
    args: argparse.Namespace | None = None,
    provider_candidate_gate: dict[str, Any] | None = None,
    enabled: bool | None = None,
    no_publish: bool | None = None,
    allow_formal_provider_publish: bool | None = None,
    allow_accepted_latest_switch: bool | None = None,
    exact_authorization_id: str | None = None,
    output_root: Path = FPALA_OUTPUT_ROOT,
    candidate_root: Path = DNG17_PROVIDER_CANDIDATE_ROOT,
    formal_provider_calendar_path: Path = CALENDAR,
    qlib_accepted_latest_path: Path = LATEST,
    legacy_latest_path: Path = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    dapr18_signal_latest_path: Path = CONTROLLED_MODEL_SIGNAL_LATEST,
    readonly_snapshot_latest_path: Path = READONLY_SNAPSHOT_LATEST,
    agent_prompt_latest_path: Path = AGENT_DAILY_PROMPT_LATEST,
    installed_cron_path: Path = OPS_ROOT / "tw-daily-auto-update.installed.cron",
    pending_asof_path: Path = PENDING_ASOF,
) -> dict[str, Any]:
    enabled = env_flag("ENABLE_TW_FPALA_FORMAL_ACCEPTED_LATEST_AUTOMATION", False) if enabled is None else enabled
    no_publish = env_flag("TW_FPALA_NO_PUBLISH", True) if no_publish is None else no_publish
    allow_formal_provider_publish = env_flag("TW_FPALA_ALLOW_FORMAL_PROVIDER_PUBLISH", False) if allow_formal_provider_publish is None else allow_formal_provider_publish
    allow_accepted_latest_switch = env_flag("TW_FPALA_ALLOW_ACCEPTED_LATEST_SWITCH", False) if allow_accepted_latest_switch is None else allow_accepted_latest_switch
    exact_authorization_id = os.getenv("TW_FPALA_EXACT_AUTHORIZATION_ID", "") if exact_authorization_id is None else exact_authorization_id
    result: dict[str, Any] = {
        "schema_version": "fpala4.daily_auto_no_publish_preflight.summary.v1",
        "created_at": utc_now(),
        "target_asof": asof,
        "job_id": job_id,
        "enabled": bool(enabled),
        "attempted": False,
        "ok": True,
        "status": "disabled_by_default",
        "no_publish": bool(no_publish),
        "allow_formal_provider_publish": bool(allow_formal_provider_publish),
        "allow_accepted_latest_switch": bool(allow_accepted_latest_switch),
        "exact_authorization_present": bool(str(exact_authorization_id or "").strip()),
        "provider_publish_triggered": False,
        "formal_provider_mutated": False,
        "qlib_refresh_triggered": False,
        "accepted_latest_switch_triggered": False,
        "latest_signal_updated": False,
        "legacy_latest_switch_triggered": False,
        "dapr18_publish_triggered": False,
        "readonly_snapshot_latest_published": False,
        "agent_prompt_build_or_publish_triggered": False,
        "job_dir_only_evidence": False,
        "evidence_paths": {},
    }
    if not enabled:
        return result

    result["attempted"] = True
    job_dir.mkdir(parents=True, exist_ok=True)
    fpala_job_id = f"fpala4_daily_auto_no_publish_{asof.replace('-', '')}_{job_id}"
    fpala_evidence_dir = output_root / fpala_job_id
    if not no_publish:
        fingerprints = fpala_protected_fingerprints(
            formal_provider_calendar_path=formal_provider_calendar_path,
            qlib_accepted_latest_path=qlib_accepted_latest_path,
            legacy_latest_path=legacy_latest_path,
            dapr18_signal_latest_path=dapr18_signal_latest_path,
            readonly_snapshot_latest_path=readonly_snapshot_latest_path,
            agent_prompt_latest_path=agent_prompt_latest_path,
            installed_cron_path=installed_cron_path,
        )
        report = {
            "schema_version": "fpala4.blocked_non_no_publish_control.v1",
            "created_at": utc_now(),
            "target_asof": asof,
            "ok": False,
            "status": "blocked_by_non_no_publish_control",
            "blockers": ["tw_fpala_no_publish_false_is_not_allowed_in_fpala4"],
            "protected_pointer_fingerprints": fingerprints,
        }
        blocked_path = fpala_evidence_dir / "fpala_blocked_non_no_publish_control.json"
        write_json(blocked_path, report)
        result.update({
            "ok": False,
            "status": "blocked_by_non_no_publish_control",
            "blocked_controls": report["blockers"],
            "evidence_paths": {"blocked_control_report": rel_path(blocked_path)},
            "job_dir_only_evidence": False,
        })
        return result

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.build_tw_fpala2_no_publish_orchestrator_precheck import (  # noqa: WPS433
        FPALAFlags,
        FPALAPaths,
        build_decision,
    )
    from scripts.validate_tw_fpala_no_publish_decision import validate_decision  # noqa: WPS433

    before = fpala_protected_fingerprints(
        formal_provider_calendar_path=formal_provider_calendar_path,
        qlib_accepted_latest_path=qlib_accepted_latest_path,
        legacy_latest_path=legacy_latest_path,
        dapr18_signal_latest_path=dapr18_signal_latest_path,
        readonly_snapshot_latest_path=readonly_snapshot_latest_path,
        agent_prompt_latest_path=agent_prompt_latest_path,
        installed_cron_path=installed_cron_path,
    )
    candidate_dir = fpala_candidate_dir_from_provider_gate(provider_candidate_gate)
    paths = FPALAPaths(
        root=ROOT,
        output_root=output_root,
        candidate_root=candidate_root,
        formal_provider_calendar=formal_provider_calendar_path,
        qlib_accepted_latest=qlib_accepted_latest_path,
        legacy_latest=legacy_latest_path,
        dapr18_signal_latest=dapr18_signal_latest_path,
        readonly_snapshot_latest=readonly_snapshot_latest_path,
        agent_prompt_latest=agent_prompt_latest_path,
        installed_cron=installed_cron_path,
        pending_asof=pending_asof_path,
        candidate_dir=candidate_dir,
    )
    flags = FPALAFlags(
        enabled=True,
        no_publish=True,
        allow_formal_provider_publish=bool(allow_formal_provider_publish),
        allow_accepted_latest_switch=bool(allow_accepted_latest_switch),
        exact_authorization_id=str(exact_authorization_id or ""),
        legacy_provider_publish_enabled=bool((job or {}).get("legacy_provider_publish_enabled")),
        dapr18_authorization_present=bool(str(getattr(args, "dapr18_exact_authorization_id", "") if args is not None else "").strip()),
    )
    decision = build_decision(
        target_asof=asof,
        job_id=fpala_job_id,
        paths=paths,
        flags=flags,
        asof_source="daily_auto_runtime",
        today_wait=bool((job or {}).get("status") == "today_data_window_wait"),
    )
    decision.setdefault("status_evidence", {})
    decision["status_evidence"].update({
        "daily_auto_job_id": job_id,
        "provider_candidate_gate_status": str((provider_candidate_gate or {}).get("status") or ""),
        "provider_candidate_gate_enabled": bool((provider_candidate_gate or {}).get("enabled")),
        "provider_candidate_gate_attempted": bool((provider_candidate_gate or {}).get("attempted")),
    })
    validation = validate_decision(decision, target_asof=asof)
    after = fpala_protected_fingerprints(
        formal_provider_calendar_path=formal_provider_calendar_path,
        qlib_accepted_latest_path=qlib_accepted_latest_path,
        legacy_latest_path=legacy_latest_path,
        dapr18_signal_latest_path=dapr18_signal_latest_path,
        readonly_snapshot_latest_path=readonly_snapshot_latest_path,
        agent_prompt_latest_path=agent_prompt_latest_path,
        installed_cron_path=installed_cron_path,
    )
    unchanged = protected_latest_unchanged(before, after)
    protected_payload = {
        "schema_version": "fpala4.protected_paths_fingerprint.v1",
        "created_at": utc_now(),
        "target_asof": asof,
        "before": before,
        "after": after,
        "unchanged": unchanged,
        "all_protected_paths_unchanged": bool(unchanged.get("all_protected_paths_unchanged")),
    }
    evidence = {
        "decision": fpala_evidence_dir / "decision.json",
        "validation_report": fpala_evidence_dir / "validation_report.json",
        "protected_paths_fingerprint": fpala_evidence_dir / "protected_paths_fingerprint.json",
        "summary": fpala_evidence_dir / "summary.json",
    }
    result.update({
        "status": "no_publish_decision_validated" if validation.get("ok") and unchanged.get("all_protected_paths_unchanged") else "blocked_by_fpala_validation_or_protected_fingerprint",
        "ok": bool(validation.get("ok") and unchanged.get("all_protected_paths_unchanged")),
        "decision_status": str(decision.get("status") or ""),
        "decision_ok": bool(decision.get("ok")),
        "validation_ok": bool(validation.get("ok")),
        "validation_error_count": int(validation.get("error_count") or 0),
        "protected_paths_unchanged": bool(unchanged.get("all_protected_paths_unchanged")),
        "candidate_dir": rel_path(candidate_dir) if candidate_dir else "",
        "job_dir_only_evidence": False,
        "fpala_evidence_dir": rel_path(fpala_evidence_dir),
    })
    result["evidence_paths"] = {name: rel_path(path) for name, path in evidence.items()}
    write_json(evidence["decision"], decision)
    write_json(evidence["validation_report"], validation)
    write_json(evidence["protected_paths_fingerprint"], protected_payload)
    write_json(evidence["summary"], result)
    return result


def attach_fpala_formal_accepted_latest_preflight(
    job: dict[str, Any],
    *,
    asof: str,
    job_id: str,
    job_dir: Path,
    args: argparse.Namespace,
    provider_candidate_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = run_fpala_formal_accepted_latest_no_publish_preflight(
        asof=asof,
        job_id=job_id,
        job_dir=job_dir,
        job=job,
        args=args,
        provider_candidate_gate=provider_candidate_gate,
        enabled=bool(args.enable_fpala_formal_accepted_latest_automation),
        no_publish=bool(args.fpala_no_publish),
        allow_formal_provider_publish=bool(args.fpala_allow_formal_provider_publish),
        allow_accepted_latest_switch=bool(args.fpala_allow_accepted_latest_switch),
        exact_authorization_id=args.fpala_exact_authorization_id,
    )
    job["fpala_formal_accepted_latest_automation"] = result
    if result.get("attempted") and not result.get("ok"):
        job["fpala_formal_accepted_latest_automation_warning"] = (
            result.get("status") or "fpala formal provider / accepted latest no-publish gate blocked"
        )
    write_json(job_dir / "job.json", job)
    return result


def dapr18_forbidden_action_audit() -> dict[str, Any]:
    actions = {
        "provider_or_network_pull": False,
        "provider_publish": False,
        "formal_qlib_refresh": False,
        "accepted_latest_switch": False,
        "legacy_latest_switch": False,
        "controlled_signal_latest_write": False,
        "readonly_snapshot_latest_write": False,
        "agent_prompt_latest_write": False,
        "openai_call": False,
        "db_write": False,
        "model_training_or_tuning": False,
        "strategy_replay": False,
        "monitor_or_broker_or_order_path": False,
        "order_intent_generation": False,
        "target_position_or_weight_output": False,
        "frontend_api_production_default_switch": False,
        "cron_or_daily_automation_default_switch": False,
    }
    return {
        "schema_version": "dapr18c.forbidden_action_audit.v1",
        "created_at": utc_now(),
        "all_false": not any(actions.values()),
        "actions": actions,
    }


def dapr18_protected_latest_fingerprints(
    *,
    controlled_signal_latest_path: Path = CONTROLLED_MODEL_SIGNAL_LATEST,
    readonly_latest_path: Path = READONLY_SNAPSHOT_LATEST,
    agent_latest_path: Path = AGENT_DAILY_PROMPT_LATEST,
    provider_latest_path: Path = LATEST,
    legacy_latest_path: Path = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
) -> dict[str, Any]:
    return {
        "controlled_signal_latest": file_fingerprint(controlled_signal_latest_path),
        "readonly_snapshot_latest": file_fingerprint(readonly_latest_path),
        "agent_prompt_latest": file_fingerprint(agent_latest_path),
        "provider_accepted_latest": file_fingerprint(provider_latest_path),
        "legacy_option_c_latest": file_fingerprint(legacy_latest_path),
    }


def payload_signal_asof(payload: dict[str, Any]) -> str:
    return str(payload.get("signal_asof") or payload.get("asof") or payload.get("data_asof") or payload.get("target_date") or "")


def build_dapr18_controlled_latest_readiness(
    *,
    asof: str,
    job_id: str,
    job_dir: Path,
    job: dict[str, Any],
    controlled_signal_latest_path: Path,
    readonly_latest_path: Path,
    agent_latest_path: Path,
    provider_latest_path: Path,
    legacy_latest_path: Path,
    before_fingerprints: dict[str, Any],
) -> dict[str, Any]:
    controlled_signal_latest = read_json(controlled_signal_latest_path)
    readonly_latest = read_json(readonly_latest_path)
    agent_latest = read_json(agent_latest_path)
    provider_latest = read_json(provider_latest_path)
    legacy_latest = read_json(legacy_latest_path)
    chain_status = job.get("daily_chain_status") if isinstance(job.get("daily_chain_status"), dict) else read_json(job_dir / "daily_chain_status.json")

    controlled_asof = payload_signal_asof(controlled_signal_latest)
    readonly_asof = payload_signal_asof(readonly_latest)
    agent_asof = payload_signal_asof(agent_latest)
    provider_asof = payload_signal_asof(provider_latest)
    legacy_asof = payload_signal_asof(legacy_latest)
    blockers: list[str] = []
    if controlled_asof != asof:
        blockers.append("controlled_signal_latest_asof_mismatch_or_missing")
    if readonly_asof != asof:
        blockers.append("readonly_snapshot_latest_asof_mismatch_or_missing")
    if agent_asof != asof:
        blockers.append("agent_prompt_latest_asof_mismatch_or_missing")
    if not latest_manifest_exists(controlled_signal_latest, "canonical_manifest", "manifest"):
        blockers.append("controlled_signal_manifest_missing")
    if not latest_manifest_exists(readonly_latest, "snapshot_manifest", "manifest"):
        blockers.append("readonly_snapshot_manifest_missing")
    if not latest_manifest_exists(agent_latest, "manifest"):
        blockers.append("agent_prompt_manifest_missing")

    accepted_latest_lagging = bool(provider_asof and provider_asof != asof)
    return {
        "schema_version": "dapr18c.controlled_latest_readiness.v1",
        "created_at": utc_now(),
        "asof": asof,
        "job_id": job_id,
        "job_dir": rel_path(job_dir),
        "mode": "default_off_or_dry_run",
        "readiness_state": "READY_EXISTING_CONTROLLED_LATESTS" if not blockers else "BLOCKED_WITH_REASON",
        "blockers": blockers,
        "accepted_latest_lagging": accepted_latest_lagging,
        "daily_chain_state": str(chain_status.get("state") or ""),
        "daily_chain_blocked_at": str(chain_status.get("blocked_at") or ""),
        "daily_chain_blocker_reason": str(chain_status.get("blocker_reason") or ""),
        "controlled_signal_latest": {
            "path": rel_path(controlled_signal_latest_path),
            "signal_asof": controlled_asof,
            "run_id": str(controlled_signal_latest.get("run_id") or ""),
            "manifest": str(controlled_signal_latest.get("canonical_manifest") or controlled_signal_latest.get("manifest") or ""),
            "fingerprint": before_fingerprints.get("controlled_signal_latest", {}),
        },
        "readonly_snapshot_latest": {
            "path": rel_path(readonly_latest_path),
            "signal_asof": readonly_asof,
            "manifest": str(readonly_latest.get("snapshot_manifest") or readonly_latest.get("manifest") or ""),
            "fingerprint": before_fingerprints.get("readonly_snapshot_latest", {}),
        },
        "agent_prompt_latest": {
            "path": rel_path(agent_latest_path),
            "signal_asof": agent_asof,
            "manifest": str(agent_latest.get("manifest") or ""),
            "fingerprint": before_fingerprints.get("agent_prompt_latest", {}),
        },
        "qlib_accepted_latest": {
            "path": rel_path(provider_latest_path),
            "asof": provider_asof,
            "fingerprint": before_fingerprints.get("provider_accepted_latest", {}),
            "separate_from_controlled_signal_latest": True,
        },
        "legacy_option_c_latest": {
            "path": rel_path(legacy_latest_path),
            "asof": legacy_asof,
            "fingerprint": before_fingerprints.get("legacy_option_c_latest", {}),
            "must_remain_unchanged": True,
        },
        "forbidden_actions": dapr18_forbidden_action_audit(),
    }


def build_dapr18_candidate_plan(
    *,
    asof: str,
    readiness: dict[str, Any],
    build_candidates: bool,
) -> dict[str, Any]:
    ready = readiness.get("readiness_state") == "READY_EXISTING_CONTROLLED_LATESTS"
    return {
        "schema_version": "dapr18c.candidate_plan.v1",
        "created_at": utc_now(),
        "asof": asof,
        "plan_mode": "candidate_planning_only",
        "build_candidates_requested": bool(build_candidates),
        "candidate_artifact_write_performed": False,
        "latest_pointer_write_planned": False,
        "latest_pointer_write_performed": False,
        "source_readiness_state": readiness.get("readiness_state"),
        "blockers": readiness.get("blockers", []),
        "controlled_signal_latest_publish": {
            "eligible_for_later_preflight": ready,
            "actual_write_allowed": False,
            "requires_phase": "DAPR18F_ACTUAL_CONTROLLED_PUBLISH_AFTER_EXACT_AUTHORIZATION",
        },
        "readonly_snapshot_candidate": {
            "eligible_for_later_candidate_build": ready,
            "actual_write_allowed": False,
            "requires_phase": "DAPR18C_or_later_candidate_only_when_explicitly_enabled",
        },
        "agent_prompt_candidate": {
            "eligible_for_later_candidate_build": ready,
            "actual_write_allowed": False,
            "requires_phase": "DAPR18C_or_later_candidate_only_when_explicitly_enabled",
            "openai_required": False,
        },
    }


def normalize_dapr18_dataset_status(row: dict[str, str]) -> str:
    status = str(row.get("status") or "")
    if status == "captured":
        return "captured"
    if status.startswith("skipped"):
        return "skipped_by_calendar_or_contract"
    if status == "success_partial":
        return "success_partial"
    if str(row.get("retry_hint") or ""):
        return "pending_with_retry_hint"
    return "blocked_with_next_required_action"


def build_dapr18_future_dataset_ledger(
    *,
    asof: str,
    job: dict[str, Any],
    job_dir: Path,
    args: argparse.Namespace | None = None,
) -> dict[str, Any]:
    if args is not None:
        rows, _summary = build_daily_full_capture_accounting(job, asof=asof, args=args)
    else:
        rows = accounting_rows_for_chain(job, job_dir=job_dir)
    orthogonal_batch = load_orthogonal_batch_control(job)
    coverage = orthogonal_batch.get("coverage") if isinstance(orthogonal_batch.get("coverage"), dict) else {}
    ledger_rows: list[dict[str, Any]] = []
    for row in rows:
        category = str(row.get("dataset_category") or "")
        dataset_coverage = coverage.get("institutional" if category == "institutional_flow" else "margin" if category == "margin_short" else "")
        dataset_coverage = dataset_coverage if isinstance(dataset_coverage, dict) else {}
        source_max_date = str(row.get("source_max_date") or "")
        normalized_status = normalize_dapr18_dataset_status(row)
        next_required_action = str(row.get("retry_hint") or "")
        if source_max_date and source_max_date < asof and normalized_status not in {"skipped_by_calendar_or_contract", "captured"}:
            next_required_action = next_required_action or "refresh_or_repair_dataset_source_before_using_for_target_asof"
        elif normalized_status == "blocked_with_next_required_action":
            next_required_action = next_required_action or "repair_dataset_source_or_classify_skip_contract"
        ledger_rows.append({
            "target_asof": asof,
            "dataset_category": category,
            "source_boundary": str(row.get("source_boundary") or ""),
            "source_max_date": source_max_date,
            "row_count": str(row.get("row_count") or ""),
            "symbol_count": str(row.get("symbol_count") or ""),
            "coverage_done_count": dataset_coverage.get("done_symbol_count", ""),
            "coverage_total_count": dataset_coverage.get("total_symbol_count", ""),
            "status": normalized_status,
            "original_status": str(row.get("status") or ""),
            "status_reason": str(row.get("status_reason") or ""),
            "retry_hint": str(row.get("retry_hint") or ""),
            "next_required_action": next_required_action,
        })
    return {
        "schema_version": "dapr18c.future_dataset_ledger.v1",
        "created_at": utc_now(),
        "asof": asof,
        "row_count": len(ledger_rows),
        "rows": ledger_rows,
        "silent_stale_categories": [
            row["dataset_category"]
            for row in ledger_rows
            if row["source_max_date"] and row["source_max_date"] < asof
            and row["status"] not in {"skipped_by_calendar_or_contract"}
            and not row["next_required_action"]
        ],
        "production_trade_enabled": False,
        "research_only": True,
    }


def build_dapr18_failure_ledger(
    *,
    asof: str,
    job_id: str,
    readiness: dict[str, Any],
    blocked_controls: list[str],
    final_status: str,
    auto_publish_success: bool,
    idempotent_noop: bool,
) -> dict[str, Any]:
    readiness_blockers = readiness.get("blockers") if isinstance(readiness.get("blockers"), list) else []
    all_blockers = [str(item) for item in readiness_blockers] + list(blocked_controls)
    historical_readiness = {
        "historical": True,
        "readiness_state": readiness.get("readiness_state"),
        "blockers": [str(item) for item in readiness_blockers],
    }
    if auto_publish_success:
        all_blockers = []
        blocked_at = ""
        blocker_reason = "none"
        next_required_action = ""
        retry_hint = ""
        resolution_status = (
            "resolved_idempotent_noop_already_current"
            if idempotent_noop
            else "resolved_authorized_publish_completed"
        )
    elif blocked_controls:
        blocked_at = "dapr18_controlled_publish_controls"
        blocker_reason = ",".join(blocked_controls)
        next_required_action = "keep_dry_run_or_wait_for_later_exact_authorization_phase"
        retry_hint = "DAPR18E_or_DAPR18F"
        resolution_status = "blocked_fail_closed"
    elif readiness_blockers:
        blocked_at = "dapr18_controlled_latest_readiness"
        blocker_reason = ",".join(str(item) for item in readiness_blockers)
        next_required_action = "produce_validated_target_asof_controlled_latest_candidates"
        retry_hint = "retry_after_provider_bridge_and_model_signal_readiness"
        resolution_status = "blocked_fail_closed"
    else:
        blocked_at = ""
        blocker_reason = "none"
        next_required_action = "eligible_for_later_preflight_or_observation"
        retry_hint = "observe_next_daily_auto_run"
        resolution_status = "not_blocked_observation_only"
    return {
        "schema_version": "dapr18c.failure_ledger.v1",
        "created_at": utc_now(),
        "target_asof": asof,
        "job_id": job_id,
        "final_status": final_status,
        "resolution_status": resolution_status,
        "blocked": bool(all_blockers),
        "blocked_at": blocked_at,
        "blocker_reason": blocker_reason,
        "blockers": all_blockers,
        "next_required_action": next_required_action,
        "retry_hint": retry_hint,
        "historical_pre_publish_readiness": historical_readiness,
        "source_evidence_paths": {
            "daily_chain_status": readiness.get("daily_chain_state", ""),
            "controlled_signal_latest": (readiness.get("controlled_signal_latest") or {}).get("path", ""),
            "readonly_snapshot_latest": (readiness.get("readonly_snapshot_latest") or {}).get("path", ""),
            "agent_prompt_latest": (readiness.get("agent_prompt_latest") or {}).get("path", ""),
        },
        "forbidden_actions_all_false": bool((readiness.get("forbidden_actions") or {}).get("all_false")),
    }


def dapr18_exact_authorization_allows_auto_publish(
    *,
    exact_authorization_id: str,
    dry_run: bool,
    publish_controlled_signal_latest: bool,
    publish_readonly_snapshot_latest: bool,
    publish_agent_prompt_latest: bool,
) -> dict[str, Any]:
    auth_id = str(exact_authorization_id or "").strip()
    publish_flags = {
        "controlled_signal_latest": bool(publish_controlled_signal_latest),
        "readonly_snapshot_latest": bool(publish_readonly_snapshot_latest),
        "agent_prompt_latest": bool(publish_agent_prompt_latest),
    }
    blockers: list[str] = []
    if dry_run:
        blockers.append("dry_run_true_blocks_actual_auto_publish")
    if not auth_id:
        blockers.append("missing_tw_dapr18_exact_authorization_id")
    elif not re.match(r"^DAPR18_AUTO_PUBLISH_CHAIN_[A-Za-z0-9_:-]+$", auth_id):
        blockers.append("tw_dapr18_exact_authorization_id_format_invalid")
    if not all(publish_flags.values()):
        blockers.append("dapr18_auto_publish_requires_all_three_product_latest_flags")
    return {
        "schema_version": "dapr18p1.auto_publish_authorization_gate.v1",
        "created_at": utc_now(),
        "authorization_id_present": bool(auth_id),
        "authorization_id": auth_id,
        "dry_run": bool(dry_run),
        "publish_flags": publish_flags,
        "allowed": not blockers,
        "blockers": blockers,
        "scope": {
            "allowed_latest_pointers": [
                rel_path(CONTROLLED_MODEL_SIGNAL_LATEST),
                rel_path(READONLY_SNAPSHOT_LATEST),
                rel_path(AGENT_DAILY_PROMPT_LATEST),
            ],
            "forbidden": [
                "provider_pull_or_publish",
                "qlib_refresh",
                "qlib_or_legacy_accepted_latest_switch",
                "OpenAI",
                "DB",
                "strategy_replay",
                "monitor/broker/order/target",
                "frontend_api_production_default_switch",
                "cron_install",
            ],
        },
    }


def dapr18_signal_source_candidates(*, asof: str, job: dict[str, Any]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    model_signal_gate = job.get("model_signal_gate") if isinstance(job.get("model_signal_gate"), dict) else {}
    summary = model_signal_gate.get("summary") if isinstance(model_signal_gate.get("summary"), dict) else {}
    summary_path = str(summary.get("model_a_signal_path") or "")
    if summary_path:
        candidates.append({"source": "model_signal_gate.summary.model_a_signal_path", "path": summary_path})

    isolated = model_signal_gate.get("isolated_existing_artifact") if isinstance(model_signal_gate.get("isolated_existing_artifact"), dict) else {}
    artifacts = isolated.get("artifacts") if isinstance(isolated.get("artifacts"), dict) else {}
    isolated_path = str(artifacts.get("model_signal") or "")
    if isolated_path:
        candidates.append({"source": "model_signal_gate.isolated_existing_artifact.artifacts.model_signal", "path": isolated_path})

    chain_status = job.get("daily_chain_status") if isinstance(job.get("daily_chain_status"), dict) else {}
    lineage = chain_status.get("lineage_evidence") if isinstance(chain_status.get("lineage_evidence"), dict) else {}
    for source_name in ("signal_manifest", "isolated_model_signal"):
        value = str(lineage.get(source_name) or "")
        if value:
            candidates.append({"source": f"daily_chain_status.lineage_evidence.{source_name}", "path": value})

    manifest_path = model_a_manifest_paths(asof).get("signal_manifest") or ""
    if manifest_path:
        candidates.append({"source": "artifact_manifest_for_asof.model_a_signal_manifest", "path": str(Path(manifest_path).parent)})

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in candidates:
        resolved = resolve_path(item["path"])
        signal_dir = resolved.parent if resolved.name == "manifest.json" else resolved
        key = str(signal_dir.resolve()) if signal_dir.exists() else str(signal_dir)
        if key in seen:
            continue
        seen.add(key)
        unique.append({"source": item["source"], "path": rel_path(signal_dir)})
    return unique


def validate_dapr18_model_signal_source(*, asof: str, signal_dir: Path) -> dict[str, Any]:
    required_files = [
        "manifest.json",
        "signals.csv",
        "schema.json",
        "coverage_audit.csv",
        "forbidden_field_audit.csv",
        "validator_report.json",
    ]
    file_checks = [
        {
            "file": name,
            "path": rel_path(signal_dir / name),
            "exists": (signal_dir / name).is_file(),
            "sha256": file_fingerprint(signal_dir / name).get("sha256", ""),
        }
        for name in required_files
    ]
    errors = [f"missing_file:{item['file']}" for item in file_checks if not item["exists"]]
    manifest = read_json(signal_dir / "manifest.json")
    validator = read_json(signal_dir / "validator_report.json")
    rows: list[dict[str, str]] = []
    if (signal_dir / "signals.csv").is_file():
        try:
            with (signal_dir / "signals.csv").open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
        except Exception as exc:
            errors.append(f"signals_csv_read_failed:{exc}")
    dates = sorted({str(row.get("date") or "") for row in rows if str(row.get("date") or "")})
    signal_asofs = sorted({str(row.get("signal_asof") or "") for row in rows if str(row.get("signal_asof") or "")})
    signal_model_names = sorted({str(row.get("model_name") or "") for row in rows if str(row.get("model_name") or "")})
    signal_model_ids = sorted({str(row.get("model_id") or "") for row in rows if str(row.get("model_id") or "")})
    signal_columns = set(rows[0].keys()) if rows else set()
    instruments = [(row.get("date"), row.get("instrument")) for row in rows]
    duplicate_count = len(instruments) - len(set(instruments))
    forbidden_columns = sorted(
        col for col in (rows[0].keys() if rows else []) if col in {"action", "position", "target_position", "target_weight", "order_qty"}
    )
    ranks: list[int] = []
    for row in rows:
        try:
            ranks.append(int(str(row.get("candidate_rank") or "")))
        except ValueError:
            pass
    manifest_forbidden = manifest.get("forbidden_actions") if isinstance(manifest.get("forbidden_actions"), dict) else {}
    forbidden_true = sorted(key for key, value in manifest_forbidden.items() if bool(value))
    checks = {
        "signal_dir_exists": signal_dir.is_dir(),
        "all_six_files_exist": all(item["exists"] for item in file_checks),
        "manifest_artifact_type_model_signal": manifest.get("artifact_type") == "ModelSignalArtifact",
        "manifest_model_id_active_modela": manifest.get("model_id") == MODELA_MODEL_ID,
        "manifest_model_name_active_modela": manifest.get("model_name") == MODELA_MODEL_ID,
        "manifest_status_ready": manifest.get("status") == "READY",
        "manifest_asof_target": manifest.get("asof") == asof and manifest.get("signal_asof") == asof,
        "manifest_row_count_150": int(manifest.get("row_count") or 0) == 150,
        "manifest_production_allowed_false": manifest.get("production_allowed") is False,
        "manifest_not_published_latest_true": manifest.get("not_published_latest") is True,
        "manifest_no_latest_true": manifest.get("no_latest") is True,
        "validator_pass": validator.get("ok") is True and validator.get("status") == "PASS",
        "validator_rows_150": int(validator.get("signal_rows") or 0) == 150,
        "signals_row_count_150": len(rows) == 150,
        "signals_date_only_target_asof": dates == [asof],
        "signals_signal_asof_only_target_asof": signal_asofs == [asof],
        "signals_model_name_active_modela_when_present": (
            "model_name" not in signal_columns or signal_model_names == [MODELA_MODEL_ID]
        ),
        "signals_model_id_active_modela_when_present": (
            "model_id" not in signal_columns or signal_model_ids == [MODELA_MODEL_ID]
        ),
        "signals_duplicate_count_zero": duplicate_count == 0,
        "signals_forbidden_columns_empty": not forbidden_columns,
        "signals_candidate_rank_1_to_150": sorted(ranks) == list(range(1, 151)),
        "manifest_forbidden_actions_all_false": not forbidden_true,
    }
    errors.extend([key for key, passed in checks.items() if not passed])
    return {
        "schema_version": "dapr18p1.model_signal_source_validation.v1",
        "created_at": utc_now(),
        "target_asof": asof,
        "signal_dir": rel_path(signal_dir),
        "run_id": str(manifest.get("run_id") or signal_dir.name),
        "file_checks": file_checks,
        "checks": checks,
        "row_count": len(rows),
        "dates": dates,
        "signal_asofs": signal_asofs,
        "signal_model_names": signal_model_names,
        "signal_model_ids": signal_model_ids,
        "duplicate_count": duplicate_count,
        "forbidden_columns": forbidden_columns,
        "manifest_forbidden_true": forbidden_true,
        "ok": not errors,
        "status": "pass" if not errors else "blocked",
        "errors": errors,
    }


def build_dapr18_source_bridge_runtime_path_audit(
    *,
    source_root: Path,
    source_signal_dir: Path,
    summary_path: Path,
    forbidden_path: Path,
    runtime_audit_path: Path,
    asof: str,
    run_id: str,
) -> dict[str, Any]:
    allowed_readonly_source_roots = [
        CONTROLLED_MODEL_SIGNAL_ROOT,
        ROOT / "data_tw/canonical/model_inference_input",
        ROOT / "data_tw/artifacts/score_jobs",
        DNG17_PROVIDER_CANDIDATE_ROOT,
    ]
    forbidden_parts = {
        "latest",
        "accepted_latest",
        "monitor",
        "broker",
        "order",
        "target_position",
        "target_weight",
        "target_output",
    }
    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    def under(child: Path, parent: Path) -> bool:
        try:
            child.resolve(strict=False).relative_to(parent.resolve(strict=False))
            return True
        except ValueError:
            return False

    for role, path in {
        "source_root": source_root,
        "source_summary": summary_path,
        "source_forbidden_audit": forbidden_path,
        "source_signal_dir": source_signal_dir,
    }.items():
        resolved = path.resolve(strict=False)
        under_source_root = under(path, source_root)
        allowed_readonly_source = any(under(path, root) for root in allowed_readonly_source_roots)
        parts = {part.lower() for part in resolved.parts}
        forbidden = sorted(parts & forbidden_parts)
        if not under_source_root and not allowed_readonly_source:
            errors.append(f"{role}:not_under_source_bridge_or_allowed_readonly_source")
        if forbidden:
            errors.append(f"{role}:forbidden_path_part:{','.join(forbidden)}")
        rows.append({
            "role": role,
            "path": rel_path(path),
            "exists": path.exists(),
            "under_source_bridge_root": under_source_root,
            "allowed_readonly_source": allowed_readonly_source,
            "forbidden_parts": forbidden,
        })

    return {
        "schema_version": "dapr18p1.source_bridge_runtime_path_audit.v1",
        "created_at": utc_now(),
        "target_asof": asof,
        "run_id": run_id,
        "status": "pass" if not errors else "fail",
        "source_root": rel_path(source_root),
        "allowed_readonly_source_roots": [rel_path(path) for path in allowed_readonly_source_roots],
        "paths": rows,
        "errors": errors,
        "production_trade_enabled": False,
        "research_only": True,
    }


def discover_dapr18_model_signal_source(*, asof: str, job: dict[str, Any], job_dir: Path) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for candidate in dapr18_signal_source_candidates(asof=asof, job=job):
        signal_dir = resolve_path(candidate["path"])
        validation = validate_dapr18_model_signal_source(asof=asof, signal_dir=signal_dir)
        attempts.append({**candidate, "validation": validation})
        if validation.get("ok"):
            source_root = job_dir / "dapr18p1_source_bridge"
            summary_path = source_root / "modela_no_publish_dry_run_summary.json"
            forbidden_path = source_root / "forbidden_action_audit.json"
            runtime_audit_path = source_root / "runtime_path_audit.json"
            source_root.mkdir(parents=True, exist_ok=True)
            run_id = str(validation.get("run_id") or signal_dir.name)
            summary = {
                "schema_version": "dapr18p1.modela_source_summary.v1",
                "created_at": utc_now(),
                "status": "pass",
                "verdict": "MODELA_NO_PUBLISH_DRY_RUN_PASS",
                "decision": "MODELA_NO_PUBLISH_DRY_RUN_PASS",
                "ready_for_controlled_latest_publish_preflight": True,
                "ready_for_latest_switch": False,
                "ready_for_provider_publish": False,
                "target_asof": asof,
                "run_id": run_id,
                "source_signal_dir": rel_path(signal_dir),
                "source": candidate["source"],
                "production_trade_enabled": False,
                "research_only": True,
            }
            forbidden = {
                "schema_version": "dapr18p1.source_forbidden_action_audit.v1",
                "created_at": utc_now(),
                "all_false": True,
                "all_forbidden_false": True,
                "actions": {
                    "provider_pull": False,
                    "provider_publish": False,
                    "qlib_refresh": False,
                    "accepted_latest_switch": False,
                    "legacy_latest_switch": False,
                    "OpenAI": False,
                    "DB": False,
                    "strategy_replay": False,
                    "monitor/broker/order/target": False,
                    "frontend_api_production_default_switch": False,
                },
            }
            write_json(summary_path, summary)
            write_json(forbidden_path, forbidden)
            runtime_audit = build_dapr18_source_bridge_runtime_path_audit(
                source_root=source_root,
                source_signal_dir=signal_dir,
                summary_path=summary_path,
                forbidden_path=forbidden_path,
                runtime_audit_path=runtime_audit_path,
                asof=asof,
                run_id=run_id,
            )
            write_json(runtime_audit_path, runtime_audit)
            return {
                "schema_version": "dapr18p1.model_signal_source_discovery.v1",
                "created_at": utc_now(),
                "target_asof": asof,
                "ok": True,
                "status": "pass",
                "source": candidate["source"],
                "run_id": run_id,
                "source_signal_dir": rel_path(signal_dir),
                "source_root": rel_path(source_root),
                "source_summary": rel_path(summary_path),
                "source_forbidden_audit": rel_path(forbidden_path),
                "source_runtime_audit": rel_path(runtime_audit_path),
                "attempts": attempts,
            }
    return {
        "schema_version": "dapr18p1.model_signal_source_discovery.v1",
        "created_at": utc_now(),
        "target_asof": asof,
        "ok": False,
        "status": "blocked",
        "run_id": "",
        "source_signal_dir": "",
        "source_root": "",
        "source_summary": "",
        "source_forbidden_audit": "",
        "attempts": attempts,
        "blockers": ["no_validated_target_asof_model_signal_artifact_for_auto_publish"],
    }


def dapr18_latest_product_state(
    *,
    asof: str,
    controlled_signal_latest_path: Path,
    readonly_latest_path: Path,
    agent_latest_path: Path,
) -> dict[str, Any]:
    controlled = read_json(controlled_signal_latest_path)
    readonly = read_json(readonly_latest_path)
    agent = read_json(agent_latest_path)
    state = {
        "schema_version": "dapr18p1.product_latest_state.v1",
        "created_at": utc_now(),
        "target_asof": asof,
        "controlled_signal_latest_asof": payload_signal_asof(controlled),
        "readonly_snapshot_latest_asof": payload_signal_asof(readonly),
        "agent_prompt_latest_asof": payload_signal_asof(agent),
        "controlled_signal_run_id": str(controlled.get("run_id") or ""),
        "readonly_snapshot_manifest": str(readonly.get("snapshot_manifest") or readonly.get("manifest") or ""),
        "agent_prompt_manifest": str(agent.get("manifest") or ""),
    }
    state["all_product_latest_match_target"] = (
        state["controlled_signal_latest_asof"] == asof
        and state["readonly_snapshot_latest_asof"] == asof
        and state["agent_prompt_latest_asof"] == asof
    )
    return state


def dapr18_step_output_roots(*, job_dir: Path, asof: str, run_id: str) -> dict[str, Path]:
    tag = asof.replace("-", "")
    chain_root = job_dir / "dapr18p1_controlled_auto_publish_chain"
    return {
        "chain_root": chain_root,
        "reports": chain_root / "reports",
        "dapr9": chain_root / f"dapr9_{tag}_controlled_latest_publish_preflight_or_stop",
        "dapr10": chain_root / f"dapr10_{tag}_actual_controlled_signal_latest_publish_{run_id}",
        "dapr11": chain_root / f"dapr11_{tag}_downstream_readonly_snapshot_agent_preflight_or_stop",
        "dapr12": chain_root / f"dapr12_{tag}_candidate_only_readonly_snapshot_dry_run_no_publish",
        "dapr13": chain_root / f"dapr13_{tag}_actual_readonly_snapshot_publish",
        "dapr14": chain_root / f"dapr14_{tag}_agent_prompt_latest_preflight_or_stop",
        "dapr15": chain_root / f"dapr15_{tag}_candidate_only_agent_prompt_dry_run_no_publish",
        "dapr16": chain_root / f"dapr16_{tag}_controlled_agent_prompt_publish_preflight_or_stop",
        "dapr17": chain_root / f"dapr17_{tag}_actual_controlled_agent_prompt_publish",
    }


def dapr18_step_specs(*, asof: str, run_id: str, source: dict[str, Any], roots: dict[str, Path]) -> list[dict[str, Any]]:
    reports = roots["reports"]
    tag = asof.replace("-", "")
    return [
        {
            "name": "dapr9_controlled_latest_publish_preflight_or_stop",
            "script": DAPR9_CONTROLLED_LATEST_PREFLIGHT_SCRIPT,
            "root": roots["dapr9"],
            "env": {
                "DAPR9_TARGET_ASOF": asof,
                "DAPR9_RUN_ID": run_id,
                "DAPR9_SOURCE_LABEL": "DAPR18P1 daily auto validated ModelSignalArtifact",
                "DAPR9_SOURCE_ROOT": source["source_root"],
                "DAPR9_SOURCE_SIGNAL_DIR": source["source_signal_dir"],
                "DAPR9_SOURCE_SUMMARY": source["source_summary"],
                "DAPR9_SOURCE_FORBIDDEN_AUDIT": source["source_forbidden_audit"],
                "DAPR9_SOURCE_RUNTIME_AUDIT": source.get("source_runtime_audit", ""),
                "DAPR9_OUTPUT_ROOT": rel_path(roots["dapr9"]),
                "DAPR9_EXECUTION_REPORT": rel_path(reports / f"POLICY_DAPR18P1_DAPR9_{tag}_EXECUTION_REPORT_CN.md"),
                "DAPR9_REVIEW": rel_path(reports / f"POLICY_DAPR18P1_DAPR9_{tag}_REVIEW_CN.md"),
            },
            "required_stdout": {"status": "pass", "ready_for_future_exact_authorization_gate": True},
        },
        {
            "name": "dapr10_actual_controlled_signal_latest_publish",
            "script": DAPR10_CONTROLLED_SIGNAL_LATEST_PUBLISH_SCRIPT,
            "root": roots["dapr10"],
            "env": {
                "DAPR10_TARGET_ASOF": asof,
                "DAPR10_RUN_ID": run_id,
                "DAPR10_SOURCE_LABEL": "DAPR18P1 daily auto validated ModelSignalArtifact",
                "DAPR10_DAPR9_ROOT": rel_path(roots["dapr9"]),
                "DAPR10_OUTPUT_ROOT": rel_path(roots["dapr10"]),
                "DAPR10_EXECUTION_REPORT": rel_path(reports / f"POLICY_DAPR18P1_DAPR10_{tag}_EXECUTION_REPORT_CN.md"),
                "DAPR10_REVIEW": rel_path(reports / f"POLICY_DAPR18P1_DAPR10_{tag}_REVIEW_CN.md"),
            },
            "required_stdout": {"status": "pass"},
        },
        {
            "name": "dapr11_downstream_readonly_snapshot_agent_preflight_or_stop",
            "script": DAPR11_DOWNSTREAM_PREFLIGHT_SCRIPT,
            "root": roots["dapr11"],
            "env": {
                "TW_DAPR11_TARGET_ASOF": asof,
                "TW_DAPR11_RUN_ID": run_id,
                "TW_DAPR11_DAPR10_ROOT": rel_path(roots["dapr10"]),
                "TW_DAPR11_OUTPUT_ROOT": rel_path(roots["dapr11"]),
                "TW_DAPR11_EXECUTION_REPORT": rel_path(reports / f"POLICY_DAPR18P1_DAPR11_{tag}_EXECUTION_REPORT_CN.md"),
                "TW_DAPR11_REVIEW": rel_path(reports / f"POLICY_DAPR18P1_DAPR11_{tag}_REVIEW_CN.md"),
            },
            "required_stdout": {"status": "pass", "ready_for_dapr12_no_publish_snapshot_dry_run": True},
        },
        {
            "name": "dapr12_candidate_only_readonly_snapshot_dry_run_no_publish",
            "script": DAPR12_READONLY_SNAPSHOT_CANDIDATE_SCRIPT,
            "root": roots["dapr12"],
            "env": {
                "TW_DAPR12_TARGET_ASOF": asof,
                "TW_DAPR12_RUN_ID": run_id,
                "TW_DAPR12_DAPR11_ROOT": rel_path(roots["dapr11"]),
                "TW_DAPR12_OUTPUT_ROOT": rel_path(roots["dapr12"]),
                "TW_DAPR12_EXECUTION_REPORT": rel_path(reports / f"POLICY_DAPR18P1_DAPR12_{tag}_EXECUTION_REPORT_CN.md"),
                "TW_DAPR12_REVIEW": rel_path(reports / f"POLICY_DAPR18P1_DAPR12_{tag}_REVIEW_CN.md"),
            },
            "required_stdout": {"status": "pass", "ready_for_dapr13_exact_authorization_gate": True},
        },
        {
            "name": "dapr13_actual_readonly_snapshot_publish",
            "script": DAPR13_READONLY_SNAPSHOT_PUBLISH_SCRIPT,
            "root": roots["dapr13"],
            "env": {
                "TW_DAPR13_TARGET_ASOF": asof,
                "TW_DAPR13_DAPR12_ROOT": rel_path(roots["dapr12"]),
                "TW_DAPR13_DAPR12_REVIEW": rel_path(reports / f"POLICY_DAPR18P1_DAPR12_{tag}_REVIEW_CN.md"),
                "TW_DAPR13_OUTPUT_ROOT": rel_path(roots["dapr13"]),
                "TW_DAPR13_EXECUTION_REPORT": rel_path(reports / f"POLICY_DAPR18P1_DAPR13_{tag}_EXECUTION_REPORT_CN.md"),
                "TW_DAPR13_REVIEW": rel_path(reports / f"POLICY_DAPR18P1_DAPR13_{tag}_REVIEW_CN.md"),
            },
            "required_stdout": {"status": "pass"},
        },
        {
            "name": "dapr14_agent_prompt_latest_preflight_or_stop",
            "script": DAPR14_AGENT_PROMPT_PREFLIGHT_SCRIPT,
            "root": roots["dapr14"],
            "env": {
                "TW_DAPR14_TARGET_ASOF": asof,
                "TW_DAPR14_DAPR13_ROOT": rel_path(roots["dapr13"]),
                "TW_DAPR14_DAPR13_REVIEW": rel_path(reports / f"POLICY_DAPR18P1_DAPR13_{tag}_REVIEW_CN.md"),
                "TW_DAPR14_OUTPUT_ROOT": rel_path(roots["dapr14"]),
                "TW_DAPR14_EXECUTION_REPORT": rel_path(reports / f"POLICY_DAPR18P1_DAPR14_{tag}_EXECUTION_REPORT_CN.md"),
                "TW_DAPR14_REVIEW": rel_path(reports / f"POLICY_DAPR18P1_DAPR14_{tag}_REVIEW_CN.md"),
            },
            "required_stdout": {"status": "pass", "ready_for_dapr15_candidate_only_agent_prompt_dry_run": True},
        },
        {
            "name": "dapr15_candidate_only_agent_prompt_dry_run_no_publish",
            "script": DAPR15_AGENT_PROMPT_CANDIDATE_SCRIPT,
            "root": roots["dapr15"],
            "env": {
                "TW_DAPR15_TARGET_ASOF": asof,
                "TW_DAPR15_DAPR14_ROOT": rel_path(roots["dapr14"]),
                "TW_DAPR15_OUTPUT_ROOT": rel_path(roots["dapr15"]),
                "TW_DAPR15_EXECUTION_REPORT": rel_path(reports / f"POLICY_DAPR18P1_DAPR15_{tag}_EXECUTION_REPORT_CN.md"),
                "TW_DAPR15_REVIEW": rel_path(reports / f"POLICY_DAPR18P1_DAPR15_{tag}_REVIEW_CN.md"),
            },
            "required_stdout": {"status": "pass", "ready_for_dapr16_agent_prompt_publish_preflight_gate": True},
        },
        {
            "name": "dapr16_controlled_agent_prompt_publish_preflight_or_stop",
            "script": DAPR16_AGENT_PROMPT_PUBLISH_PREFLIGHT_SCRIPT,
            "root": roots["dapr16"],
            "env": {
                "TW_DAPR16_TARGET_ASOF": asof,
                "TW_DAPR16_DAPR15_ROOT": rel_path(roots["dapr15"]),
                "TW_DAPR16_OUTPUT_ROOT": rel_path(roots["dapr16"]),
                "TW_DAPR16_EXECUTION_REPORT": rel_path(reports / f"POLICY_DAPR18P1_DAPR16_{tag}_EXECUTION_REPORT_CN.md"),
                "TW_DAPR16_REVIEW": rel_path(reports / f"POLICY_DAPR18P1_DAPR16_{tag}_REVIEW_CN.md"),
            },
            "required_stdout": {"status": "pass", "ready_for_dapr17_exact_authorization_gate": True},
        },
        {
            "name": "dapr17_actual_controlled_agent_prompt_publish",
            "script": DAPR17_AGENT_PROMPT_PUBLISH_SCRIPT,
            "root": roots["dapr17"],
            "env": {
                "TW_DAPR17_TARGET_ASOF": asof,
                "TW_DAPR17_DAPR15_ROOT": rel_path(roots["dapr15"]),
                "TW_DAPR17_DAPR16_ROOT": rel_path(roots["dapr16"]),
                "TW_DAPR17_OUTPUT_ROOT": rel_path(roots["dapr17"]),
                "TW_DAPR17_EXECUTION_REPORT": rel_path(reports / f"POLICY_DAPR18P1_DAPR17_{tag}_EXECUTION_REPORT_CN.md"),
                "TW_DAPR17_REVIEW": rel_path(reports / f"POLICY_DAPR18P1_DAPR17_{tag}_REVIEW_CN.md"),
            },
            "required_stdout": {"status": "pass"},
        },
    ]


def dapr18_step_stdout_satisfies(payload: dict[str, Any], required: dict[str, Any]) -> bool:
    for key, expected in required.items():
        if payload.get(key) != expected:
            return False
    return True


def run_dapr18_auto_publish_chain(
    *,
    asof: str,
    job_dir: Path,
    source: dict[str, Any],
    timeout_seconds: int,
    command_runner=None,
) -> dict[str, Any]:
    command_runner = command_runner or run_cmd
    run_id = str(source.get("run_id") or "")
    roots = dapr18_step_output_roots(job_dir=job_dir, asof=asof, run_id=run_id)
    roots["reports"].mkdir(parents=True, exist_ok=True)
    chain_root = roots["chain_root"]
    steps: list[dict[str, Any]] = []
    ok = True
    blocker = ""
    for spec in dapr18_step_specs(asof=asof, run_id=run_id, source=source, roots=roots):
        stdout_path = chain_root / f"{spec['name']}_stdout.json"
        stderr_path = chain_root / f"{spec['name']}_stderr.txt"
        command = command_runner(
            [PYTHON, str(spec["script"].relative_to(ROOT))],
            cwd=ROOT,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            timeout=timeout_seconds,
            env=spec["env"],
        )
        stdout_payload = parse_json_stdout(command)
        step_ok = bool(command.get("ok")) and dapr18_step_stdout_satisfies(stdout_payload, spec["required_stdout"])
        step = {
            "name": spec["name"],
            "script": rel_path(spec["script"]),
            "output_root": rel_path(spec["root"]),
            "command": command,
            "stdout_payload": stdout_payload,
            "required_stdout": spec["required_stdout"],
            "ok": step_ok,
        }
        steps.append(step)
        if not step_ok:
            ok = False
            blocker = f"{spec['name']}_failed_or_stdout_gate_not_pass"
            break
    result = {
        "schema_version": "dapr18p1.auto_publish_chain.v1",
        "created_at": utc_now(),
        "target_asof": asof,
        "run_id": run_id,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "blocker": blocker,
        "chain_root": rel_path(chain_root),
        "steps": steps,
        "step_count": len(steps),
        "expected_step_count": 9,
        "stop_on_fail": True,
    }
    write_json(chain_root / "dapr18_auto_publish_chain.json", result)
    return result


def run_dapr18_controlled_latest_orchestration(
    *,
    asof: str,
    job_dir: Path,
    job_id: str = "",
    job: dict[str, Any] | None = None,
    args: argparse.Namespace | None = None,
    enabled: bool | None = None,
    dry_run: bool | None = None,
    build_candidates: bool | None = None,
    publish_controlled_signal_latest: bool | None = None,
    publish_readonly_snapshot_latest: bool | None = None,
    publish_agent_prompt_latest: bool | None = None,
    exact_authorization_id: str | None = None,
    controlled_signal_latest_path: Path = CONTROLLED_MODEL_SIGNAL_LATEST,
    readonly_latest_path: Path = READONLY_SNAPSHOT_LATEST,
    agent_latest_path: Path = AGENT_DAILY_PROMPT_LATEST,
    provider_latest_path: Path = LATEST,
    legacy_latest_path: Path = ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    command_runner=None,
) -> dict[str, Any]:
    enabled = env_flag("ENABLE_TW_DAPR18_CONTROLLED_LATEST_ORCHESTRATION", False) if enabled is None else enabled
    dry_run = env_flag("TW_DAPR18_CONTROLLED_LATEST_DRY_RUN", True) if dry_run is None else dry_run
    build_candidates = env_flag("TW_DAPR18_BUILD_CANDIDATES", False) if build_candidates is None else build_candidates
    publish_controlled_signal_latest = env_flag("TW_DAPR18_PUBLISH_CONTROLLED_SIGNAL_LATEST", False) if publish_controlled_signal_latest is None else publish_controlled_signal_latest
    publish_readonly_snapshot_latest = env_flag("TW_DAPR18_PUBLISH_READONLY_SNAPSHOT_LATEST", False) if publish_readonly_snapshot_latest is None else publish_readonly_snapshot_latest
    publish_agent_prompt_latest = env_flag("TW_DAPR18_PUBLISH_AGENT_PROMPT_LATEST", False) if publish_agent_prompt_latest is None else publish_agent_prompt_latest
    exact_authorization_id = os.getenv("TW_DAPR18_EXACT_AUTHORIZATION_ID", "") if exact_authorization_id is None else exact_authorization_id
    result: dict[str, Any] = {
        "schema_version": "dapr18c.controlled_latest_orchestration.summary.v1",
        "created_at": utc_now(),
        "enabled": bool(enabled),
        "attempted": False,
        "ok": True,
        "status": "disabled_by_default",
        "dry_run": bool(dry_run),
        "build_candidates": bool(build_candidates),
        "publish_controlled_signal_latest": bool(publish_controlled_signal_latest),
        "publish_readonly_snapshot_latest": bool(publish_readonly_snapshot_latest),
        "publish_agent_prompt_latest": bool(publish_agent_prompt_latest),
        "exact_authorization_present": bool(str(exact_authorization_id or "").strip()),
        "latest_pointer_write_performed": False,
        "controlled_signal_latest_write_performed": False,
        "readonly_snapshot_latest_write_performed": False,
        "agent_prompt_latest_write_performed": False,
        "job_dir_only_evidence": False,
        "evidence_paths": {},
    }
    if not enabled:
        return result

    result["attempted"] = True
    job = job or {}
    job_dir.mkdir(parents=True, exist_ok=True)
    before = dapr18_protected_latest_fingerprints(
        controlled_signal_latest_path=controlled_signal_latest_path,
        readonly_latest_path=readonly_latest_path,
        agent_latest_path=agent_latest_path,
        provider_latest_path=provider_latest_path,
        legacy_latest_path=legacy_latest_path,
    )
    readiness = build_dapr18_controlled_latest_readiness(
        asof=asof,
        job_id=job_id,
        job_dir=job_dir,
        job=job,
        controlled_signal_latest_path=controlled_signal_latest_path,
        readonly_latest_path=readonly_latest_path,
        agent_latest_path=agent_latest_path,
        provider_latest_path=provider_latest_path,
        legacy_latest_path=legacy_latest_path,
        before_fingerprints=before,
    )
    candidate_plan = build_dapr18_candidate_plan(asof=asof, readiness=readiness, build_candidates=bool(build_candidates))
    future_ledger = build_dapr18_future_dataset_ledger(asof=asof, job=job, job_dir=job_dir, args=args)
    forbidden = dapr18_forbidden_action_audit()
    product_state_before = dapr18_latest_product_state(
        asof=asof,
        controlled_signal_latest_path=controlled_signal_latest_path,
        readonly_latest_path=readonly_latest_path,
        agent_latest_path=agent_latest_path,
    )
    publish_requested = any(
        [publish_controlled_signal_latest, publish_readonly_snapshot_latest, publish_agent_prompt_latest]
    )
    auth_gate = dapr18_exact_authorization_allows_auto_publish(
        exact_authorization_id=str(exact_authorization_id or ""),
        dry_run=bool(dry_run),
        publish_controlled_signal_latest=bool(publish_controlled_signal_latest),
        publish_readonly_snapshot_latest=bool(publish_readonly_snapshot_latest),
        publish_agent_prompt_latest=bool(publish_agent_prompt_latest),
    )
    blocked_controls: list[str] = []
    source_discovery: dict[str, Any] = {}
    auto_publish_chain: dict[str, Any] = {}
    product_state_after: dict[str, Any] = {}
    timeout_seconds = int(getattr(args, "timeout_seconds", 1200)) if args is not None else int(os.getenv("TW_DAPR18_AUTO_PUBLISH_TIMEOUT_SECONDS", "1200"))

    if publish_requested:
        if dry_run and publish_controlled_signal_latest:
            blocked_controls.append("controlled_signal_latest_publish_blocked_while_dry_run_true")
        if dry_run and publish_readonly_snapshot_latest:
            blocked_controls.append("readonly_snapshot_latest_publish_blocked_while_dry_run_true")
        if dry_run and publish_agent_prompt_latest:
            blocked_controls.append("agent_prompt_latest_publish_blocked_while_dry_run_true")
        blocked_controls.extend(str(item) for item in auth_gate.get("blockers", []))
        if auth_gate.get("allowed") and product_state_before.get("all_product_latest_match_target"):
            auto_publish_chain = {
                "schema_version": "dapr18p1.auto_publish_chain.v1",
                "created_at": utc_now(),
                "target_asof": asof,
                "ok": True,
                "status": "idempotent_noop",
                "reason": "all_product_latest_already_match_target_asof",
                "steps": [],
                "step_count": 0,
                "expected_step_count": 9,
            }
        elif auth_gate.get("allowed"):
            source_discovery = discover_dapr18_model_signal_source(asof=asof, job=job, job_dir=job_dir)
            if not source_discovery.get("ok"):
                blocked_controls.extend(str(item) for item in source_discovery.get("blockers", []))
            else:
                auto_publish_chain = run_dapr18_auto_publish_chain(
                    asof=asof,
                    job_dir=job_dir,
                    source=source_discovery,
                    timeout_seconds=timeout_seconds,
                    command_runner=command_runner,
                )
                if not auto_publish_chain.get("ok"):
                    blocked_controls.append(str(auto_publish_chain.get("blocker") or "dapr18_auto_publish_chain_failed"))
    elif not dry_run:
        blocked_controls.append("dapr18_dry_run_disabled_without_complete_auto_publish_scope")
    if str(exact_authorization_id or "").strip() and not any(
        [publish_controlled_signal_latest, publish_readonly_snapshot_latest, publish_agent_prompt_latest]
    ):
        blocked_controls.append("exact_authorization_id_present_without_publish_scope")

    after = dapr18_protected_latest_fingerprints(
        controlled_signal_latest_path=controlled_signal_latest_path,
        readonly_latest_path=readonly_latest_path,
        agent_latest_path=agent_latest_path,
        provider_latest_path=provider_latest_path,
        legacy_latest_path=legacy_latest_path,
    )
    unchanged = protected_latest_unchanged(before, after)
    product_state_after = dapr18_latest_product_state(
        asof=asof,
        controlled_signal_latest_path=controlled_signal_latest_path,
        readonly_latest_path=readonly_latest_path,
        agent_latest_path=agent_latest_path,
    )
    forbidden_protected_unchanged = bool(
        unchanged.get("provider_accepted_latest")
        and unchanged.get("legacy_option_c_latest")
    )
    protected_payload = {
        "schema_version": "dapr18p1.protected_paths_fingerprint.v1",
        "created_at": utc_now(),
        "before": before,
        "after": after,
        "unchanged": unchanged,
        "all_protected_paths_unchanged": bool(unchanged.get("all_protected_paths_unchanged")),
        "forbidden_protected_paths_unchanged": forbidden_protected_unchanged,
        "allowed_product_latest_paths": [
            rel_path(controlled_signal_latest_path),
            rel_path(readonly_latest_path),
            rel_path(agent_latest_path),
        ],
    }
    if publish_requested and auth_gate.get("allowed") and auto_publish_chain.get("ok"):
        if not product_state_after.get("all_product_latest_match_target"):
            blocked_controls.append("dapr18_product_latest_state_after_mismatch")
        if not forbidden_protected_unchanged:
            blocked_controls.append("dapr18_provider_or_legacy_protected_pointer_changed")
        if not forbidden.get("all_false"):
            blocked_controls.append("dapr18_forbidden_action_audit_failed")
    auto_publish_success = bool(
        publish_requested
        and auth_gate.get("allowed")
        and not blocked_controls
        and auto_publish_chain.get("ok")
        and product_state_after.get("all_product_latest_match_target")
        and forbidden_protected_unchanged
        and forbidden.get("all_false")
    )
    idempotent_noop = auto_publish_chain.get("status") == "idempotent_noop"
    dry_run_success = bool(
        not publish_requested
        and dry_run
        and forbidden.get("all_false")
        and unchanged.get("all_protected_paths_unchanged")
        and not blocked_controls
    )
    status = "dry_run_plan_recorded"
    if auto_publish_success and idempotent_noop:
        status = "auto_publish_idempotent_noop_already_current"
    elif auto_publish_success:
        status = "auto_publish_chain_completed"
    elif blocked_controls:
        status = "blocked_by_dapr18p1_auto_publish_control"
    failure_ledger = build_dapr18_failure_ledger(
        asof=asof,
        job_id=job_id,
        readiness=readiness,
        blocked_controls=blocked_controls,
        final_status=status,
        auto_publish_success=auto_publish_success,
        idempotent_noop=idempotent_noop,
    )

    result.update({
        "schema_version": "dapr18p1.controlled_latest_orchestration.summary.v1",
        "status": status,
        "ok": bool(auto_publish_success or dry_run_success),
        "source_readiness_state": readiness.get("readiness_state"),
        "blockers": [] if auto_publish_success else readiness.get("blockers", []),
        "historical_pre_publish_readiness": failure_ledger["historical_pre_publish_readiness"],
        "blocked_controls": blocked_controls,
        "publish_requested": publish_requested,
        "authorization_gate": auth_gate,
        "product_latest_state_before": product_state_before,
        "product_latest_state_after": product_state_after,
        "source_discovery": source_discovery,
        "auto_publish_chain": auto_publish_chain,
        "future_dataset_silent_stale_categories": future_ledger.get("silent_stale_categories", []),
        "protected_paths_unchanged": bool(unchanged.get("all_protected_paths_unchanged")),
        "forbidden_protected_paths_unchanged": forbidden_protected_unchanged,
        "forbidden_actions_all_false": bool(forbidden.get("all_false")),
        "job_dir_only_evidence": not (auto_publish_success and not idempotent_noop),
    })
    if auto_publish_success and not idempotent_noop:
        result["latest_pointer_write_performed"] = True
        result["controlled_signal_latest_write_performed"] = True
        result["readonly_snapshot_latest_write_performed"] = True
        result["agent_prompt_latest_write_performed"] = True
    evidence = {
        "readiness": job_dir / "dapr18_controlled_latest_readiness.json",
        "candidate_plan": job_dir / "dapr18_candidate_plan.json",
        "authorization_gate": job_dir / "dapr18_authorization_gate.json",
        "product_latest_state_before": job_dir / "dapr18_product_latest_state_before.json",
        "source_discovery": job_dir / "dapr18_model_signal_source_discovery.json",
        "auto_publish_chain": job_dir / "dapr18_auto_publish_chain.json",
        "product_latest_state_after": job_dir / "dapr18_product_latest_state_after.json",
        "protected_paths_fingerprint": job_dir / "dapr18_protected_paths_fingerprint.json",
        "forbidden_action_audit": job_dir / "dapr18_forbidden_action_audit.json",
        "failure_ledger": job_dir / "dapr18_failure_ledger.json",
        "future_dataset_ledger": job_dir / "dapr18_future_dataset_ledger.json",
        "summary": job_dir / "dapr18_controlled_latest_orchestration_summary.json",
    }
    write_json(evidence["readiness"], readiness)
    write_json(evidence["candidate_plan"], candidate_plan)
    write_json(evidence["authorization_gate"], auth_gate)
    write_json(evidence["product_latest_state_before"], product_state_before)
    write_json(evidence["source_discovery"], source_discovery)
    write_json(evidence["auto_publish_chain"], auto_publish_chain)
    write_json(evidence["product_latest_state_after"], product_state_after)
    write_json(evidence["protected_paths_fingerprint"], protected_payload)
    write_json(evidence["forbidden_action_audit"], forbidden)
    write_json(evidence["failure_ledger"], failure_ledger)
    write_json(evidence["future_dataset_ledger"], future_ledger)
    result["evidence_paths"] = {name: rel_path(path) for name, path in evidence.items()}
    write_json(evidence["summary"], result)
    return result


def finalize_dapr18_publish_failure(
    *,
    job: dict[str, Any],
    orchestration: dict[str, Any],
    asof: str,
    job_id: str,
    job_dir: Path,
    args: argparse.Namespace,
) -> bool:
    if not (
        orchestration.get("attempted")
        and orchestration.get("publish_requested")
        and not orchestration.get("ok")
    ):
        return False

    chain = orchestration.get("auto_publish_chain") or {}
    blocker = str(
        chain.get("blocker")
        or ",".join(str(item) for item in orchestration.get("blocked_controls", []))
        or orchestration.get("status")
        or "dapr18_auto_publish_failed"
    )
    set_pending_asof(asof, reason="dapr18_auto_publish_failed", job_id=job_id)
    job.update(
        {
            "status": "dapr18_auto_publish_failed",
            "message": f"Requested DAPR18 publish failed at {blocker}; target remains pending for retry.",
            "finished_at": utc_now(),
            "latest_after": latest_asof(),
            "pending_asof_set": asof,
            "dapr18_terminal_blocker": blocker,
        }
    )
    finalize_job(job, job_dir=job_dir, asof=asof, args=args)
    return True


def redact_secret_text(text: str) -> str:
    redacted = re.sub(r"([?&]token=)[^&>\s]+", r"\1[REDACTED_TOKEN]", str(text or ""))
    redacted = re.sub(r"(Authorization:\s*Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED_TOKEN]", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"(Bearer\s+)[A-Za-z0-9._~+/=-]{24,}", r"\1[REDACTED_TOKEN]", redacted, flags=re.IGNORECASE)
    return redacted


def run_cmd(
    argv: list[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    timeout: int,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    started_at = utc_now()
    command_env = os.environ.copy()
    if env:
        command_env.update({str(key): str(value) for key, value in env.items()})
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            env=command_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        returncode = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        stderr = f"{stderr}\nTimeoutExpired: command exceeded {timeout} seconds".strip()
        returncode = 124
    stdout = redact_secret_text(stdout)
    stderr = redact_secret_text(stderr)
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    return {
        "ok": returncode == 0,
        "returncode": returncode,
        "argv": argv,
        "cwd": str(cwd),
        "env_keys": sorted(env.keys()) if env else [],
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "stdout_tail": stdout[-3000:],
        "stderr_tail": stderr[-3000:],
        "started_at": started_at,
        "finished_at": utc_now(),
    }


def attach_daily_readiness_dashboard(job: dict[str, Any], *, job_dir: Path, asof: str, args: argparse.Namespace) -> None:
    enabled = bool(getattr(args, "enable_data_catalog_dashboard", False))
    result: dict[str, Any] = {
        "enabled": enabled,
        "attempted": False,
        "ok": True,
        "dashboard_path": rel_path(DATA_CATALOG_DASHBOARD),
        "validation_path": rel_path(DNG6_DATA_CATALOG_DASHBOARD_VALIDATION),
        "builder_returncode": None,
        "validator_returncode": None,
        "safe_static_only": True,
        "provider_publish_triggered": False,
        "accepted_latest_switch_triggered": False,
        "model_score_generation_triggered": False,
        "strategy_replay_triggered": False,
        "broker_order_quick_trade_triggered": False,
    }
    job["data_catalog_dashboard"] = result
    if not enabled:
        return

    result["attempted"] = True
    build_result = run_cmd(
        [
            PYTHON,
            str(DATA_CATALOG_DASHBOARD_BUILD_SCRIPT.relative_to(ROOT)),
            "--asof",
            asof,
            "--job-json",
            rel_path(job_dir / "job.json"),
            "--output",
            rel_path(DATA_CATALOG_DASHBOARD),
            "--json",
        ],
        cwd=ROOT,
        stdout_path=job_dir / "daily_readiness_dashboard_build_stdout.json",
        stderr_path=job_dir / "daily_readiness_dashboard_build_stderr.txt",
        timeout=min(int(getattr(args, "timeout_seconds", 1200)), 120),
    )
    result["builder"] = build_result
    result["builder_returncode"] = build_result.get("returncode")
    dashboard_payload = parse_json_stdout(build_result)
    result["dashboard_status"] = str(dashboard_payload.get("dashboard_status") or "")
    result["dashboard_asof"] = str(dashboard_payload.get("asof") or "")
    result["production_ready"] = bool(dashboard_payload.get("production_ready"))
    result["forbidden_actions_all_false"] = bool((dashboard_payload.get("forbidden_actions_audit") or {}).get("all_false"))
    if not build_result.get("ok"):
        result["ok"] = False
        result["error"] = "daily readiness dashboard builder failed"
        return

    validate_result = run_cmd(
        [
            PYTHON,
            str(DATA_CATALOG_DASHBOARD_VALIDATE_SCRIPT.relative_to(ROOT)),
            "--dashboard",
            rel_path(DATA_CATALOG_DASHBOARD),
            "--output",
            rel_path(DNG6_DATA_CATALOG_DASHBOARD_VALIDATION),
            "--json",
        ],
        cwd=ROOT,
        stdout_path=job_dir / "daily_readiness_dashboard_validate_stdout.json",
        stderr_path=job_dir / "daily_readiness_dashboard_validate_stderr.txt",
        timeout=min(int(getattr(args, "timeout_seconds", 1200)), 120),
    )
    result["validator"] = validate_result
    result["validator_returncode"] = validate_result.get("returncode")
    validator_payload = parse_json_stdout(validate_result)
    result["validator_ok"] = bool(validator_payload.get("ok"))
    result["validator_status"] = str(validator_payload.get("status") or "")
    result["validator_error_count"] = int(validator_payload.get("error_count") or 0)
    result["validator_warning_count"] = int(validator_payload.get("warning_count") or 0)
    result["ok"] = bool(validate_result.get("ok") and validator_payload.get("ok"))
    if not result["ok"]:
        result["error"] = "daily readiness dashboard validator failed"


def write_model_signal_gate_summary(summary: dict[str, Any], *, output_path: Path = MODEL_SIGNAL_GATE_DRY_RUN_SUMMARY) -> dict[str, Any]:
    write_json(output_path, summary)
    validation = validate_model_signal_gate_summary_payload(summary, summary_path=output_path)
    write_json(DNG9_MODEL_SIGNAL_GATE_VALIDATION, validation)
    return validation


def build_model_signal_gate_summary(
    *,
    asof: str,
    gate_enabled: bool,
    mode: str,
    job_id: str = "",
    model_a_result: dict[str, Any] | None = None,
    model_b_result: dict[str, Any] | None = None,
    provider_selection: dict[str, Any] | None = None,
    validation_status: str = "",
) -> dict[str, Any]:
    model_a_result = model_a_result or {}
    model_b_result = model_b_result or {}
    provider_selection = provider_selection or {}
    model_a_artifacts = model_a_result.get("artifacts") if isinstance(model_a_result.get("artifacts"), dict) else {}
    model_b_artifacts = model_b_result.get("artifacts") if isinstance(model_b_result.get("artifacts"), dict) else {}
    model_b_blockers = model_b_result.get("blockers") or model_b_result.get("blocking_datasets") or []
    if not gate_enabled:
        model_a_status = "DISABLED_BY_DEFAULT"
        model_b_status = "DISABLED_BY_DEFAULT"
        model_b_blockers = ["model_signal_gate_disabled"]
    else:
        model_a_status = str(model_a_result.get("pipeline_status") or model_a_result.get("status") or "NOT_RUN")
        model_b_status = str(model_b_result.get("pipeline_status") or model_b_result.get("score_status") or "NOT_RUN")
    summary = {
        "schema_version": MODEL_SIGNAL_GATE_SCHEMA_VERSION,
        "created_at": utc_now(),
        "asof": asof,
        "job_id": job_id,
        "mode": mode,
        "gate_enabled": bool(gate_enabled),
        "provider_selection_mode": str(provider_selection.get("provider_selection_mode") or "not_selected"),
        "formal_provider_calendar_covers_asof": bool(provider_selection.get("formal_provider_calendar_covers_asof")),
        "formal_provider_calendar_max": str(provider_selection.get("formal_provider_calendar_max") or ""),
        "isolated_candidate_used": bool(provider_selection.get("isolated_candidate_used")),
        "isolated_candidate_readiness_path": str(provider_selection.get("isolated_candidate_readiness_path") or ""),
        "isolated_score_builder": str(provider_selection.get("isolated_score_builder") or ""),
        "reused_existing_model_a_artifact": bool(provider_selection.get("reused_existing_model_a_artifact")),
        "model_a_score_job": bool(gate_enabled and mode.startswith("daily_auto_gate") and not provider_selection.get("reused_existing_model_a_artifact") and model_a_artifacts.get("score_job")),
        "model_b_ltr_score_job": bool(gate_enabled and model_b_result and mode.startswith("daily_auto_gate") and model_b_artifacts.get("score_job")),
        "model_a_status": model_a_status,
        "model_a_inference_input_path": str(model_a_artifacts.get("model_inference_input") or model_a_artifacts.get("inference_input") or ""),
        "model_a_signal_path": str(model_a_artifacts.get("model_signal") or ""),
        "model_a_score_job_path": str(model_a_artifacts.get("score_job") or ""),
        "model_b_status": model_b_status,
        # model_b_status remains the strict prospective generation gate. The
        # frozen historical model uses a separate readonly compatibility lane.
        "strict_model_b_status": model_b_status,
        "legacy_compatible_model_b": dict(MODELB_LEGACY_COMPATIBILITY),
        "legacy_compatible_model_b_status": MODELB_LEGACY_COMPATIBILITY["status"],
        "legacy_model_b_blocked_by_hsa8": False,
        "model_b_blockers": model_b_blockers,
        "model_b_signal_path": str(model_b_artifacts.get("model_signal") or ""),
        "model_b_score_job_path": str(model_b_artifacts.get("score_job") or ""),
        "model_b_fallback_modela_signal": str(model_b_artifacts.get("fallback_modela_signal") or model_b_result.get("fallback_signal_artifact") or ""),
        "fallback_policy": "model_b_qlib_only_fallback_requires_explicit_strategy_contract",
        "publish_latest_gate": False,
        "accepted_latest_switch": False,
        "readonly_latest_publish": False,
        "agent_prompt_publish": False,
        "production_allowed": False,
        "research_only": True,
        "dng3_external_source_repair_required_before_true_model_b_ltr_signal": True,
        "forbidden_actions_audit": {
            "all_false": all(value is False for value in MODEL_SIGNAL_GATE_FORBIDDEN_ACTIONS_FALSE.values()),
            "actions": MODEL_SIGNAL_GATE_FORBIDDEN_ACTIONS_FALSE,
        },
        "validation_status": validation_status,
        "notes": [
            "DNG9 integrates explicit daily auto model_signal_gate only.",
            "Default gate is disabled; dry-run summary does not invoke daily auto provider refresh or publish.",
            "Strict prospective Model B generation must remain BLOCKED_INPUT_NOT_READY until its PIT/source-lineage gate passes.",
            "Frozen historical Model B remains available for legacy_exploratory readonly comparison and is not promoted to formal OOS or production default.",
        ],
    }
    return summary


def validate_model_signal_gate_summary_payload(summary: dict[str, Any], *, summary_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    required = [
        "schema_version",
        "created_at",
        "asof",
        "gate_enabled",
        "model_a_status",
        "model_a_signal_path",
        "model_b_status",
        "strict_model_b_status",
        "legacy_compatible_model_b",
        "legacy_compatible_model_b_status",
        "legacy_model_b_blocked_by_hsa8",
        "model_b_blockers",
        "fallback_policy",
        "provider_selection_mode",
        "formal_provider_calendar_covers_asof",
        "formal_provider_calendar_max",
        "isolated_candidate_used",
        "isolated_score_builder",
        "reused_existing_model_a_artifact",
        "model_a_inference_input_path",
        "publish_latest_gate",
        "accepted_latest_switch",
        "forbidden_actions_audit",
    ]
    for field in required:
        if field not in summary:
            errors.append(f"missing_required_field:{field}")
    if summary.get("schema_version") != MODEL_SIGNAL_GATE_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if bool(summary.get("publish_latest_gate")):
        errors.append("publish_latest_gate_must_be_false")
    if bool(summary.get("accepted_latest_switch")):
        errors.append("accepted_latest_switch_must_be_false")
    if bool(summary.get("readonly_latest_publish")):
        errors.append("readonly_latest_publish_must_be_false")
    if bool(summary.get("agent_prompt_publish")):
        errors.append("agent_prompt_publish_must_be_false")
    audit = summary.get("forbidden_actions_audit") if isinstance(summary.get("forbidden_actions_audit"), dict) else {}
    actions = audit.get("actions") if isinstance(audit.get("actions"), dict) else {}
    for key in MODEL_SIGNAL_GATE_FORBIDDEN_ACTIONS_FALSE:
        if bool(actions.get(key)):
            errors.append(f"forbidden_action_true:{key}")
    if (
        bool(summary.get("gate_enabled"))
        and (summary.get("model_b_ltr_score_job") or summary.get("mode") == "dry_run_static_enabled")
        and summary.get("model_b_status") != "BLOCKED_INPUT_NOT_READY"
    ):
        errors.append("model_b_must_remain_blocked_until_dng3_external_source_repair")
    if summary.get("model_b_signal_path"):
        errors.append("model_b_signal_path_must_be_empty_before_dng3_repair")
    legacy_model_b = summary.get("legacy_compatible_model_b") if isinstance(summary.get("legacy_compatible_model_b"), dict) else {}
    if summary.get("strict_model_b_status") != summary.get("model_b_status"):
        errors.append("strict_model_b_status_must_match_model_b_status_alias")
    if summary.get("legacy_compatible_model_b_status") != "AVAILABLE_READONLY":
        errors.append("legacy_compatible_model_b_must_remain_available_readonly")
    if bool(summary.get("legacy_model_b_blocked_by_hsa8")):
        errors.append("hsa8_must_not_block_legacy_readonly_model_b")
    if legacy_model_b.get("evidence_class") != "legacy_exploratory":
        errors.append("legacy_model_b_evidence_class_must_remain_legacy_exploratory")
    if legacy_model_b.get("usage") != "readonly_comparison":
        errors.append("legacy_model_b_usage_must_remain_readonly_comparison")
    for field in ("formal_oos_eligible", "production_default_eligible", "strict_retrain_or_new_scoring_eligible"):
        if bool(legacy_model_b.get(field)):
            errors.append(f"legacy_model_b_{field}_must_be_false")
    validation = {
        "schema_version": "dng9.model_signal_gate_validation.v1",
        "generated_at": utc_now(),
        "ok": not errors,
        "status": "PASS" if not errors else "FAIL",
        "summary_path": rel_path(summary_path),
        "asof": summary.get("asof", ""),
        "gate_enabled": bool(summary.get("gate_enabled")),
        "model_a_status": summary.get("model_a_status", ""),
        "provider_selection_mode": summary.get("provider_selection_mode", ""),
        "isolated_candidate_used": bool(summary.get("isolated_candidate_used")),
        "reused_existing_model_a_artifact": bool(summary.get("reused_existing_model_a_artifact")),
        "model_b_status": summary.get("model_b_status", ""),
        "strict_model_b_status": summary.get("strict_model_b_status", ""),
        "legacy_compatible_model_b_status": summary.get("legacy_compatible_model_b_status", ""),
        "default_disabled": not bool(summary.get("gate_enabled")) if summary.get("mode") == "dry_run_static_default" else None,
        "publish_latest_gate": bool(summary.get("publish_latest_gate")),
        "accepted_latest_switch": bool(summary.get("accepted_latest_switch")),
        "forbidden_actions_all_false": bool(audit.get("all_false")) and not any(bool(value) for value in actions.values()),
        "model_b_true_ltr_signal_generated": bool(summary.get("model_b_signal_path")),
        "errors": errors,
        "recommendation": "GO_DNG10_GATE_ONLY" if not errors else "DO_NOT_GO_DNG10",
    }
    return validation


def isolated_model_a_payload_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    catalog = artifact.get("catalog") if isinstance(artifact.get("catalog"), dict) else read_json(DNG15_R_B_ISOLATED_MODELA_VALIDATION)
    artifacts = catalog.get("artifacts") if isinstance(catalog.get("artifacts"), dict) else {}
    catalog_path = str(artifact.get("catalog_path") or artifacts.get("catalog_validation") or rel_path(DNG15_R_B_ISOLATED_MODELA_VALIDATION))
    return {
        "status": "READY_EXISTING_ISOLATED_ARTIFACT",
        "pipeline_status": str(catalog.get("pipeline_status") or artifact.get("pipeline_status") or "SCORED_ASOF_TARGET"),
        "score_status": str(catalog.get("score_status") or artifact.get("score_status") or "SCORED_ASOF_TARGET"),
        "run_id": str(catalog.get("run_id") or artifact.get("run_id") or ""),
        "asof": str(catalog.get("asof") or artifact.get("asof") or ""),
        "raw_scores_rows": int(catalog.get("raw_scores_rows") or artifact.get("raw_scores_rows") or 0),
        "signals_rows": int(catalog.get("signals_rows") or artifact.get("signals_rows") or 0),
        "artifacts": {
            "model_inference_input": str(artifacts.get("model_inference_input") or ""),
            "score_job": str(artifacts.get("score_job") or ""),
            "model_signal": str(artifacts.get("model_signal") or ""),
            "catalog_validation": catalog_path,
        },
    }


def isolated_provider_selection(
    *,
    asof: str,
    formal_calendar_max: str,
    existing_artifact: dict[str, Any] | None = None,
    candidate: dict[str, Any] | None = None,
    reused_existing: bool = False,
    mode: str = "",
) -> dict[str, Any]:
    return {
        "provider_selection_mode": mode,
        "formal_provider_calendar_covers_asof": bool(formal_calendar_max >= asof),
        "formal_provider_calendar_max": formal_calendar_max,
        "isolated_candidate_used": bool(candidate and candidate.get("ok")),
        "isolated_candidate_source": str((candidate or {}).get("candidate_source") or ""),
        "isolated_candidate_readiness_path": str((candidate or {}).get("readiness_path") or ""),
        "isolated_candidate_decision_path": str((candidate or {}).get("decision_path") or ""),
        "isolated_candidate_job_dir": str((candidate or {}).get("candidate_job_dir") or ""),
        "isolated_score_builder": rel_path(DNG15_R_B_ISOLATED_MODELA_SCORE_BUILD_SCRIPT),
        "reused_existing_model_a_artifact": bool(reused_existing),
        "existing_isolated_artifact_catalog": str((existing_artifact or {}).get("catalog_path") or ""),
    }


def dng17_reuse_candidate_artifacts(
    *,
    asof: str,
    job_id: str,
    job_dir: Path,
    candidate: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    source_decision = read_json(resolve_path(str(candidate.get("decision_path") or "")))
    source_readiness = read_json(resolve_path(str(candidate.get("readiness_path") or "")))
    candidate_job_dir = str(candidate.get("candidate_job_dir") or source_decision.get("candidate_job_dir") or source_decision.get("job_dir") or "")
    decision = {
        **source_decision,
        "schema_version": "dng17.provider_candidate_refresh_decision.v1",
        "generated_at": utc_now(),
        "asof": asof,
        "job_id": job_id,
        "candidate_job_dir": candidate_job_dir,
        "candidate_source": str(candidate.get("candidate_source") or ""),
        "provider_candidate_refresh_status": status,
        "provider_candidate_refresh_triggered": False,
        "provider_candidate_reused_existing": True,
        "reused_decision_path": str(candidate.get("decision_path") or ""),
        "reused_readiness_path": str(candidate.get("readiness_path") or ""),
        "source_provider": source_readiness.get("source_provider") or "Yahoo",
        "source_client": source_readiness.get("source_client") or "Scrapling",
        "proxy_used": bool((source_decision.get("fetch_summary") or {}).get("proxy_used")),
        "formal_provider_mutated": False,
        "formal_normalized_mutated": False,
        "latest_signal_updated": False,
        "production_allowed": False,
        "publish_latest_authorized": False,
        "finmind_fallback": False,
        "mixed_provider_bridge": False,
        "forbidden_actions": provider_candidate_forbidden_actions(),
    }
    readiness = {
        **source_readiness,
        "schema_version": "dng17.provider_candidate_readiness.v1",
        "generated_at": utc_now(),
        "asof": asof,
        "job_id": job_id,
        "candidate_job_dir": candidate_job_dir,
        "candidate_source": str(candidate.get("candidate_source") or ""),
        "provider_candidate_refresh_status": status,
        "provider_candidate_refresh_triggered": False,
        "provider_candidate_reused_existing": True,
        "reused_decision_path": str(candidate.get("decision_path") or ""),
        "reused_readiness_path": str(candidate.get("readiness_path") or ""),
        "candidate_normalized_path": str(candidate.get("candidate_normalized_path") or source_decision.get("candidate_normalized_path") or ""),
        "staged_provider_path": str(candidate.get("staged_provider_path") or source_decision.get("staged_provider_path") or ""),
        "fetch_status": str(candidate.get("fetch_status") or source_decision.get("fetch_status") or ""),
        "symbols_expected": int(candidate.get("symbols_expected") or source_decision.get("symbols_expected") or source_readiness.get("candidate_normalized_symbols_expected") or 0),
        "symbols_success": int(candidate.get("symbols_success") or source_decision.get("symbols_success") or source_readiness.get("candidate_normalized_symbols_success") or 0),
        "symbols_with_asof": int(candidate.get("candidate_normalized_symbols_with_asof") or source_decision.get("symbols_with_asof") or source_readiness.get("candidate_normalized_symbols_with_asof") or 0),
        "provider_validation_status": str(candidate.get("staged_provider_validation_status") or source_decision.get("provider_validation_status") or source_readiness.get("staged_provider_validation_status") or ""),
        "calendar_has_asof": bool(candidate.get("calendar_has_asof") or source_decision.get("calendar_has_asof") or source_readiness.get("staged_provider_calendar_has_asof")),
        "calendar_max": str(candidate.get("calendar_max") or (source_decision.get("provider_summary") or {}).get("calendar_max") or source_readiness.get("staged_provider_calendar_max") or ""),
        "model_smoke_status": str(candidate.get("model_smoke_status") or source_decision.get("model_smoke_status") or source_readiness.get("candidate_model_smoke_status") or ""),
        "proxy_used": bool((source_decision.get("fetch_summary") or {}).get("proxy_used")),
        "formal_provider_mutated": False,
        "formal_normalized_mutated": False,
        "latest_signal_updated": False,
        "production_allowed": False,
        "publish_latest_authorized": False,
        "finmind_fallback": False,
        "mixed_provider_bridge": False,
        "forbidden_actions": provider_candidate_forbidden_actions(),
    }
    decision_path = job_dir / "provider_candidate_refresh_decision.json"
    readiness_path = job_dir / "provider_candidate_readiness.json"
    write_json(decision_path, decision)
    write_json(readiness_path, readiness)
    return {
        "ok": True,
        "enabled": True,
        "attempted": True,
        "status": status,
        "candidate_source": str(candidate.get("candidate_source") or ""),
        "provider_candidate_refresh_triggered": False,
        "provider_candidate_reused_existing": True,
        "decision_path": rel_path(decision_path),
        "readiness_path": rel_path(readiness_path),
        "reused_decision_path": str(candidate.get("decision_path") or ""),
        "reused_readiness_path": str(candidate.get("readiness_path") or ""),
        "candidate": find_validated_isolated_provider_candidate(asof, current_job_dir=job_dir),
    }


def enrich_dng17_generated_candidate_artifacts(
    *,
    asof: str,
    job_id: str,
    candidate_job_dir: Path,
    ops_job_dir: Path,
) -> dict[str, Any]:
    decision_path = candidate_job_dir / "provider_candidate_refresh_decision.json"
    readiness_path = candidate_job_dir / "provider_candidate_readiness.json"
    decision = read_json(decision_path)
    readiness = read_json(readiness_path)
    fetch_summary = decision.get("fetch_summary") if isinstance(decision.get("fetch_summary"), dict) else {}
    provider_summary = decision.get("provider_summary") if isinstance(decision.get("provider_summary"), dict) else {}
    for payload in (decision, readiness):
        payload["generated_at"] = utc_now()
        payload["asof"] = asof
        payload["job_id"] = job_id
        payload["candidate_job_dir"] = rel_path(candidate_job_dir)
        payload["candidate_source"] = "current_job_dng17"
        payload["provider_candidate_refresh_status"] = "READY_GENERATED_DNG17_PROVIDER_CANDIDATE"
        payload["provider_candidate_refresh_triggered"] = True
        payload["provider_candidate_reused_existing"] = False
        payload["source_provider"] = payload.get("source_provider") or "Yahoo"
        payload["source_client"] = payload.get("source_client") or "Scrapling"
        payload["proxy_used"] = bool(fetch_summary.get("proxy_used"))
        payload["fetch_status"] = str(decision.get("fetch_status") or "")
        payload["symbols_expected"] = int(decision.get("symbols_expected") or readiness.get("candidate_normalized_symbols_expected") or 0)
        payload["symbols_success"] = int(decision.get("symbols_success") or readiness.get("candidate_normalized_symbols_success") or 0)
        payload["symbols_with_asof"] = int(decision.get("symbols_with_asof") or readiness.get("candidate_normalized_symbols_with_asof") or 0)
        payload["provider_validation_status"] = str(decision.get("provider_validation_status") or readiness.get("staged_provider_validation_status") or "")
        payload["calendar_has_asof"] = bool(decision.get("calendar_has_asof") or readiness.get("staged_provider_calendar_has_asof"))
        payload["calendar_max"] = str(provider_summary.get("calendar_max") or readiness.get("staged_provider_calendar_max") or "")
        payload["model_smoke_status"] = str(decision.get("model_smoke_status") or readiness.get("candidate_model_smoke_status") or "")
        payload["formal_provider_mutated"] = False
        payload["formal_normalized_mutated"] = False
        payload["latest_signal_updated"] = False
        payload["production_allowed"] = False
        payload["publish_latest_authorized"] = False
        payload["finmind_fallback"] = False
        payload["mixed_provider_bridge"] = False
        payload["forbidden_actions"] = provider_candidate_forbidden_actions()
    decision["schema_version"] = "dng17.provider_candidate_refresh_decision.v1"
    readiness["schema_version"] = "dng17.provider_candidate_readiness.v1"
    write_json(decision_path, decision)
    write_json(readiness_path, readiness)
    write_json(ops_job_dir / "provider_candidate_refresh_decision.json", decision)
    write_json(ops_job_dir / "provider_candidate_readiness.json", readiness)
    candidate = find_validated_isolated_provider_candidate(asof, current_job_dir=ops_job_dir)
    return {
        "ok": bool(candidate.get("ok")),
        "status": "READY_GENERATED_DNG17_PROVIDER_CANDIDATE" if candidate.get("ok") else "BLOCKED_GENERATED_DNG17_PROVIDER_CANDIDATE",
        "candidate": candidate,
        "decision_path": rel_path(ops_job_dir / "provider_candidate_refresh_decision.json"),
        "readiness_path": rel_path(ops_job_dir / "provider_candidate_readiness.json"),
        "candidate_job_decision_path": rel_path(decision_path),
        "candidate_job_readiness_path": rel_path(readiness_path),
    }


def run_provider_candidate_refresh_gate(
    *,
    asof: str,
    job_id: str,
    job_dir: Path,
    enabled: bool,
    model_signal_gate_enabled: bool,
    args: argparse.Namespace,
    timeout_seconds: int,
    command_runner=run_cmd,
) -> dict[str, Any]:
    formal_calendar_max = calendar_max_date(CALENDAR)
    formal_provider_covers_asof = bool(formal_calendar_max >= asof)
    result: dict[str, Any] = {
        "enabled": bool(enabled),
        "attempted": False,
        "ok": True,
        "status": "NOT_REQUIRED_FORMAL_PROVIDER_COVERS_ASOF" if formal_provider_covers_asof else "DISABLED_BY_DEFAULT",
        "formal_provider_calendar_covers_asof": formal_provider_covers_asof,
        "formal_provider_calendar_max": formal_calendar_max,
        "provider_candidate_refresh_triggered": False,
        "provider_candidate_reused_existing": False,
        "provider_publish_triggered": False,
        "formal_provider_mutated": False,
        "formal_normalized_mutated": False,
        "latest_signal_updated": False,
        "production_allowed": False,
        "publish_latest_authorized": False,
        "finmind_fallback": False,
        "mixed_provider_bridge": False,
        "forbidden_actions": provider_candidate_forbidden_actions(),
    }
    if not model_signal_gate_enabled:
        result["status"] = "DISABLED_MODEL_SIGNAL_GATE_NOT_ENABLED"
        return result
    if formal_provider_covers_asof:
        return result
    if not enabled:
        result["status"] = "DISABLED_BY_DEFAULT"
        return result

    dng18_disable_provider_candidate_fallbacks = bool(getattr(args, "dng18_disable_provider_candidate_fallbacks", False))
    prior = find_validated_isolated_provider_candidate(
        asof,
        exclude_candidate_job_id="",
        include_prior_daily_auto=not dng18_disable_provider_candidate_fallbacks,
        include_dng15_fixture=not dng18_disable_provider_candidate_fallbacks,
    )
    if prior.get("ok"):
        result.update(dng17_reuse_candidate_artifacts(asof=asof, job_id=job_id, job_dir=job_dir, candidate=prior, status="READY_REUSED_VALIDATED_PROVIDER_CANDIDATE"))
        return result

    result["attempted"] = True
    candidate_job_id = f"daily_auto_provider_candidate_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    candidate_job_dir = DNG17_PROVIDER_CANDIDATE_ROOT / candidate_job_id
    refresh_argv = [
        PYTHON,
        "examples/tw/run_option_c_yahoo_scrapling_refresh.py",
        "--asof",
        asof,
        "--start",
        "2015-01-01",
        "--universe",
        "option_c_accepted_150",
        "--output-root",
        "data_tw/experiments/daily_auto_provider_candidates",
        "--job-id",
        candidate_job_id,
        "--timeout",
        str(args.refresh_timeout),
        "--retries",
        str(args.refresh_retries),
        "--sleep-seconds",
        str(args.refresh_sleep_seconds),
        "--continue-on-error",
        "--suffix",
        "auto",
        "--max-workers",
        str(args.max_workers),
        "--report-path",
        str(job_dir / "provider_candidate_refresh_report.md"),
    ]
    if args.proxy.strip():
        idx = refresh_argv.index("--timeout")
        refresh_argv[idx:idx] = ["--proxy", args.proxy.strip()]
    refresh = command_runner(
        refresh_argv,
        cwd=QLIB,
        stdout_path=job_dir / "provider_candidate_refresh_stdout.json",
        stderr_path=job_dir / "provider_candidate_refresh_stderr.txt",
        timeout=timeout_seconds,
    )
    result["provider_candidate_refresh"] = refresh
    result["provider_candidate_refresh_triggered"] = True
    refresh_summary = read_json(candidate_job_dir / "reports/execution_summary.json")
    result["refresh_summary_path"] = rel_path(candidate_job_dir / "reports/execution_summary.json")
    result["refresh_summary_status"] = str(refresh_summary.get("status") or "")
    if not refresh.get("ok") or refresh_summary.get("status") != "staged_refresh_complete_waiting_for_review":
        result.update({
            "ok": False,
            "status": "BLOCKED_YAHOO_STAGED_REFRESH_FAILED",
            "error": "Yahoo/Scrapling staged provider candidate refresh failed",
            "candidate": {"ok": False, "status": "BLOCKED_PROVIDER_CANDIDATE_REFRESH", "asof": asof, "candidate_source": "none"},
        })
        return result

    artifact_build = command_runner(
        [
            PYTHON,
            str(DNG15_R_A_R_ARTIFACT_BUILD_SCRIPT.relative_to(ROOT)),
            "--asof",
            asof,
            "--job-dir",
            rel_path(candidate_job_dir),
            "--decision-path",
            rel_path(candidate_job_dir / "provider_candidate_refresh_decision.json"),
            "--readiness-path",
            rel_path(candidate_job_dir / "provider_candidate_readiness.json"),
            "--report-path",
            rel_path(candidate_job_dir / "reports/provider_candidate_refresh_artifact_report.md"),
        ],
        cwd=ROOT,
        stdout_path=job_dir / "provider_candidate_artifact_builder_stdout.json",
        stderr_path=job_dir / "provider_candidate_artifact_builder_stderr.txt",
        timeout=min(timeout_seconds, 600),
    )
    result["provider_candidate_artifact_builder"] = artifact_build
    if not artifact_build.get("ok"):
        result.update({
            "ok": False,
            "status": "BLOCKED_PROVIDER_CANDIDATE_ARTIFACT_BUILD_FAILED",
            "error": "DNG15_R-A-R artifact builder failed for DNG17 candidate",
        })
        return result
    enriched = enrich_dng17_generated_candidate_artifacts(asof=asof, job_id=job_id, candidate_job_dir=candidate_job_dir, ops_job_dir=job_dir)
    result.update(enriched)
    result["provider_candidate_refresh_triggered"] = True
    result["provider_candidate_reused_existing"] = False
    result["candidate_job_id"] = candidate_job_id
    result["candidate_job_dir"] = rel_path(candidate_job_dir)
    if not result.get("ok"):
        result["error"] = "generated provider candidate did not pass DNG17 validator"
    return result


def validate_model_signal_decision_cutoff(value: str) -> str:
    """Require an explicit timezone-aware RFC3339 cutoff for formal scoring."""
    if not str(value or "").strip():
        raise ValueError("decision_cutoff is required for formal Model A scoring")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"decision_cutoff is not RFC3339: {value}") from exc
    if parsed.tzinfo is None:
        raise ValueError("decision_cutoff must include timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def run_model_signal_gate(
    *,
    asof: str,
    job_id: str,
    job_dir: Path,
    enabled: bool | None = None,
    args: argparse.Namespace | None = None,
    timeout_seconds: int | None = None,
    model_b_enabled: bool = False,
    model_b_hsa8_ready: bool = True,
    source_acquisition_run_id: str = "",
    decision_cutoff: str = "",
    command_runner=run_cmd,
) -> dict[str, Any]:
    enabled = env_flag("TW_DAILY_AUTO_ENABLE_MODEL_SIGNAL_GATE", False) if enabled is None else enabled
    result: dict[str, Any] = {
        "enabled": bool(enabled),
        "attempted": False,
        "ok": True,
        "summary_path": rel_path(MODEL_SIGNAL_GATE_DRY_RUN_SUMMARY),
        "validation_path": rel_path(DNG9_MODEL_SIGNAL_GATE_VALIDATION),
        "model_a_score_job_triggered": False,
        "model_b_ltr_score_job_triggered": False,
        "publish_latest_gate": False,
        "accepted_latest_switch": False,
        "provider_refresh_triggered": False,
        "provider_publish_triggered": False,
        "readonly_latest_published": False,
        "agent_prompt_published": False,
        "strategy_replay_triggered": False,
        "broker_order_quick_trade_triggered": False,
        "target_position_or_weight_generated": False,
    }
    if not enabled:
        summary = build_model_signal_gate_summary(
            asof=asof,
            gate_enabled=False,
            mode="daily_auto_default_disabled",
            job_id=job_id,
        )
        validation = write_model_signal_gate_summary(summary)
        result["validation"] = validation
        result["ok"] = bool(validation.get("ok"))
        return result

    result["attempted"] = True
    timeout = int(timeout_seconds or os.getenv("TW_DAILY_AUTO_MODEL_SIGNAL_GATE_TIMEOUT_SECONDS", str(MODEL_SIGNAL_GATE_DEFAULT_TIMEOUT_SECONDS)))
    formal_calendar_max = calendar_max_date(CALENDAR)
    formal_provider_covers_asof = bool(formal_calendar_max >= asof)
    dng18_disable_provider_candidate_fallbacks = bool(getattr(args, "dng18_disable_provider_candidate_fallbacks", False)) if args is not None else False
    dng18_disable_existing_isolated_modela_reuse = bool(getattr(args, "dng18_disable_existing_isolated_modela_reuse", False)) if args is not None else False
    if dng18_disable_existing_isolated_modela_reuse:
        existing_isolated = {
            "ok": False,
            "status": "DISABLED_DNG18_EXISTING_ISOLATED_MODELA_REUSE",
            "asof": asof,
            "catalog_path": rel_path(DNG15_R_B_ISOLATED_MODELA_VALIDATION),
            "errors": ["dng18_disable_existing_isolated_modela_reuse"],
        }
    else:
        existing_isolated = find_validated_isolated_modela_artifact(asof)
    candidate = find_validated_isolated_provider_candidate(
        asof,
        current_job_dir=None if dng18_disable_provider_candidate_fallbacks else job_dir,
        include_prior_daily_auto=not dng18_disable_provider_candidate_fallbacks,
        include_dng15_fixture=not dng18_disable_provider_candidate_fallbacks,
    )

    if existing_isolated.get("ok"):
        model_a_payload = isolated_model_a_payload_from_artifact(existing_isolated)
        provider_selection = isolated_provider_selection(
            asof=asof,
            formal_calendar_max=formal_calendar_max,
            existing_artifact=existing_isolated,
            candidate=candidate if candidate.get("ok") else None,
            reused_existing=True,
            mode="validated_isolated_provider_candidate",
        )
        summary = build_model_signal_gate_summary(
            asof=asof,
            gate_enabled=True,
            mode="daily_auto_gate_reused_existing_isolated",
            job_id=job_id,
            model_a_result=model_a_payload,
            model_b_result={"pipeline_status": "BLOCKED_INPUT_NOT_READY", "blocking_datasets": ["corporate_actions", "monthly_revenue", "valuation"]},
            provider_selection=provider_selection,
        )
        validation = write_model_signal_gate_summary(summary)
        result.update({
            "ok": bool(validation.get("ok")),
            "mode": "daily_auto_gate_reused_existing_isolated",
            "provider_selection_mode": provider_selection["provider_selection_mode"],
            "formal_provider_calendar_covers_asof": formal_provider_covers_asof,
            "formal_provider_calendar_max": formal_calendar_max,
            "isolated_candidate_used": bool(provider_selection["isolated_candidate_used"]),
            "isolated_candidate": candidate,
            "isolated_existing_artifact": existing_isolated,
            "reused_existing_model_a_artifact": True,
            "model_a_status": summary.get("model_a_status"),
            "model_a_readiness_status": "READY_EXISTING_ISOLATED_ARTIFACT",
            "model_b_status": summary.get("model_b_status"),
            "summary": summary,
            "validation": validation,
        })
        return result

    if not formal_provider_covers_asof:
        provider_selection = isolated_provider_selection(
            asof=asof,
            formal_calendar_max=formal_calendar_max,
            existing_artifact=existing_isolated,
            candidate=candidate if candidate.get("ok") else None,
            reused_existing=False,
            mode="validated_isolated_provider_candidate" if candidate.get("ok") else "blocked_no_validated_provider",
        )
        if not candidate.get("ok"):
            result.update({
                "ok": False,
                "error": "formal provider stale and no validated isolated provider candidate is ready",
                "provider_selection_mode": provider_selection["provider_selection_mode"],
                "formal_provider_calendar_covers_asof": formal_provider_covers_asof,
                "formal_provider_calendar_max": formal_calendar_max,
                "isolated_candidate": candidate,
                "isolated_existing_artifact": existing_isolated,
            })
            summary = build_model_signal_gate_summary(
                asof=asof,
                gate_enabled=True,
                mode="daily_auto_gate_failed",
                job_id=job_id,
                model_a_result={"pipeline_status": "BLOCKED_ISOLATED_PROVIDER_CANDIDATE", "artifacts": {}},
                model_b_result={"pipeline_status": "BLOCKED_INPUT_NOT_READY", "blocking_datasets": ["corporate_actions", "monthly_revenue", "valuation"]},
                provider_selection=provider_selection,
            )
            result["summary"] = summary
            result["validation"] = write_model_signal_gate_summary(summary)
            result["ok"] = False
            return result

        isolated_run_suffix = job_id.rsplit("_", 1)[-1] if "_" in job_id else datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        isolated_run_id = f"dng9_daily_auto_modela_{asof.replace('-', '')}_{isolated_run_suffix}"
        isolated_build = command_runner(
            [
                PYTHON,
                str(DNG15_R_B_ISOLATED_MODELA_SCORE_BUILD_SCRIPT.relative_to(ROOT)),
                "--decision-path",
                str(candidate.get("decision_path") or rel_path(DNG15_R_A_R_DECISION)),
                "--readiness-path",
                str(candidate.get("readiness_path") or rel_path(DNG15_R_A_R_READINESS)),
                "--target-asof",
                asof,
                "--run-id",
                isolated_run_id,
                "--json",
            ],
            cwd=ROOT,
            stdout_path=job_dir / "model_signal_gate_isolated_modela_score_stdout.json",
            stderr_path=job_dir / "model_signal_gate_isolated_modela_score_stderr.txt",
            timeout=timeout,
        )
        result["isolated_model_a_score_builder"] = isolated_build
        result["model_a_score_job_triggered"] = True
        rebuilt_isolated = find_validated_isolated_modela_artifact(asof)
        model_a_payload = parse_json_stdout(isolated_build) if isolated_build.get("ok") else {}
        if rebuilt_isolated.get("ok"):
            model_a_payload = isolated_model_a_payload_from_artifact(rebuilt_isolated)
            model_a_payload["status"] = "READY_ISOLATED_CANDIDATE"
        if not isolated_build.get("ok") or not rebuilt_isolated.get("ok"):
            result.update({"ok": False, "error": "isolated Model A score builder failed or validator did not pass"})
            summary = build_model_signal_gate_summary(
                asof=asof,
                gate_enabled=True,
                mode="daily_auto_gate_failed",
                job_id=job_id,
                model_a_result=model_a_payload,
                model_b_result={"pipeline_status": "BLOCKED_INPUT_NOT_READY", "blocking_datasets": ["corporate_actions", "monthly_revenue", "valuation"]},
                provider_selection=provider_selection,
            )
            result["summary"] = summary
            result["validation"] = write_model_signal_gate_summary(summary)
            return result

        summary = build_model_signal_gate_summary(
            asof=asof,
            gate_enabled=True,
            mode="daily_auto_gate_generated_isolated",
            job_id=job_id,
            model_a_result=model_a_payload,
            model_b_result={"pipeline_status": "BLOCKED_INPUT_NOT_READY", "blocking_datasets": ["corporate_actions", "monthly_revenue", "valuation"]},
            provider_selection=provider_selection,
        )
        validation = write_model_signal_gate_summary(summary)
        result.update({
            "ok": bool(validation.get("ok")),
            "mode": "daily_auto_gate_generated_isolated",
            "provider_selection_mode": provider_selection["provider_selection_mode"],
            "formal_provider_calendar_covers_asof": formal_provider_covers_asof,
            "formal_provider_calendar_max": formal_calendar_max,
            "isolated_candidate_used": True,
            "isolated_candidate": candidate,
            "isolated_existing_artifact": rebuilt_isolated,
            "reused_existing_model_a_artifact": False,
            "model_a_status": summary.get("model_a_status"),
            "model_a_readiness_status": "READY_ISOLATED_CANDIDATE",
            "model_b_status": summary.get("model_b_status"),
            "summary": summary,
            "validation": validation,
        })
        if not result["ok"]:
            result["error"] = "Model signal gate validation failed"
        return result

    run_id = f"dng9_daily_auto_model_signal_gate_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    try:
        decision_cutoff = validate_model_signal_decision_cutoff(decision_cutoff)
    except ValueError as exc:
        result.update({"ok": False, "error": str(exc)})
        return result
    modela_input_dir = ROOT / "data_tw/canonical/model_inference_input" / MODELA_MODEL_ID / run_id
    modelb_input_dir = ROOT / "data_tw/canonical/model_inference_input" / MODELB_LTR_MODEL_ID / run_id

    modela_input = command_runner(
        [PYTHON, str(MODELA_INPUT_BUILD_SCRIPT.relative_to(ROOT)), "--asof", asof, "--run-id", run_id, "--json"],
        cwd=ROOT,
        stdout_path=job_dir / "model_signal_gate_modela_input_stdout.json",
        stderr_path=job_dir / "model_signal_gate_modela_input_stderr.txt",
        timeout=timeout,
    )
    result["model_a_input_builder"] = modela_input
    if not modela_input.get("ok"):
        result.update({"ok": False, "error": "Model A inference input builder failed"})
        summary = build_model_signal_gate_summary(asof=asof, gate_enabled=True, mode="daily_auto_gate_failed", job_id=job_id)
        result["validation"] = write_model_signal_gate_summary(summary)
        return result

    modela_score = command_runner(
        [
            PYTHON,
            str(MODELA_SCORE_JOB_SCRIPT.relative_to(ROOT)),
            "--asof",
            asof,
            "--run-id",
            run_id,
            "--input-dir",
            rel_path(modela_input_dir),
            "--source-acquisition-run-id",
            source_acquisition_run_id,
            "--decision-cutoff",
            decision_cutoff,
            "--json",
        ],
        cwd=ROOT,
        stdout_path=job_dir / "model_signal_gate_modela_score_stdout.json",
        stderr_path=job_dir / "model_signal_gate_modela_score_stderr.txt",
        timeout=timeout,
    )
    result["model_a_score_job"] = modela_score
    result["model_a_score_job_triggered"] = True
    model_a_payload = parse_json_stdout(modela_score)
    if not modela_score.get("ok"):
        result.update({"ok": False, "error": "Model A score job failed"})
        summary = build_model_signal_gate_summary(
            asof=asof,
            gate_enabled=True,
            mode="daily_auto_gate_failed",
            job_id=job_id,
            model_a_result=model_a_payload,
        )
        result["validation"] = write_model_signal_gate_summary(summary)
        return result

    if not model_b_enabled or not model_b_hsa8_ready:
        model_b_blocker = (
            "model_b_disabled_for_modela_only_baseline"
            if not model_b_enabled
            else "same_run_hsa8_adjusted_price_twii_or_orthogonal_not_ready"
        )
        model_b_payload = {
            "pipeline_status": "BLOCKED_INPUT_NOT_READY",
            "blocking_datasets": [model_b_blocker],
            "artifacts": {},
        }
        summary = build_model_signal_gate_summary(
            asof=asof,
            gate_enabled=True,
            mode=(
                "daily_auto_gate_modela_only_model_b_disabled"
                if not model_b_enabled
                else "daily_auto_gate_modela_only_hsa8_blocked"
            ),
            job_id=job_id,
            model_a_result=model_a_payload,
            model_b_result=model_b_payload,
        )
        validation = write_model_signal_gate_summary(summary)
        result.update({
            "ok": bool(validation.get("ok")),
            "model_a_status": summary.get("model_a_status"),
            "model_b_status": summary.get("model_b_status"),
            "model_b_enabled": bool(model_b_enabled),
            "model_b_hsa8_ready": bool(model_b_hsa8_ready),
            "model_b_blockers": model_b_payload["blocking_datasets"],
            "summary": summary,
            "validation": validation,
        })
        return result

    modelb_input = command_runner(
        [PYTHON, str(MODELB_LTR_INPUT_BUILD_SCRIPT.relative_to(ROOT)), "--asof", asof, "--run-id", run_id, "--json"],
        cwd=ROOT,
        stdout_path=job_dir / "model_signal_gate_modelb_input_stdout.json",
        stderr_path=job_dir / "model_signal_gate_modelb_input_stderr.txt",
        timeout=timeout,
    )
    result["model_b_input_builder"] = modelb_input
    if not modelb_input.get("ok"):
        result.update({"ok": False, "error": "Model B blocker input builder failed"})
        summary = build_model_signal_gate_summary(
            asof=asof,
            gate_enabled=True,
            mode="daily_auto_gate_failed",
            job_id=job_id,
            model_a_result=model_a_payload,
        )
        result["validation"] = write_model_signal_gate_summary(summary)
        return result

    modelb_score = command_runner(
        [
            PYTHON,
            str(MODELB_LTR_SCORE_JOB_SCRIPT.relative_to(ROOT)),
            "--asof",
            asof,
            "--run-id",
            run_id,
            "--input-dir",
            rel_path(modelb_input_dir),
            "--json",
        ],
        cwd=ROOT,
        stdout_path=job_dir / "model_signal_gate_modelb_score_stdout.json",
        stderr_path=job_dir / "model_signal_gate_modelb_score_stderr.txt",
        timeout=timeout,
    )
    result["model_b_ltr_score_job"] = modelb_score
    result["model_b_ltr_score_job_triggered"] = True
    model_b_payload = parse_json_stdout(modelb_score)
    summary = build_model_signal_gate_summary(
        asof=asof,
        gate_enabled=True,
        mode="daily_auto_gate_enabled",
        job_id=job_id,
        model_a_result=model_a_payload,
        model_b_result=model_b_payload,
    )
    validation = write_model_signal_gate_summary(summary)
    result["validation"] = validation
    result["ok"] = bool(modelb_score.get("ok") and validation.get("ok"))
    result["model_a_status"] = summary.get("model_a_status")
    result["model_b_status"] = summary.get("model_b_status")
    if not result["ok"]:
        result["error"] = "Model signal gate validation failed"
    return result


def run_mbcds3_daily_shadow_accumulation(
    *,
    asof: str,
    job_id: str,
    job_dir: Path,
    enabled: bool,
    inventory_path: str = "",
    accumulator_dir: str = "",
    command_runner=run_cmd,
) -> dict[str, Any]:
    """Append one daily Model B compatibility input without affecting baseline."""
    result: dict[str, Any] = {
        "enabled": bool(enabled),
        "attempted": False,
        "ok": True,
        "status": "DISABLED_BY_DEFAULT" if not enabled else "NOT_STARTED",
        "production_wiring": True,
        "production_allowed": False,
        "model_b_scoring": False,
        "training": False,
        "latest_modified": False,
        "provider_modified": False,
        "cron_modified": False,
    }
    if not enabled:
        return result

    result["attempted"] = True
    out = Path(accumulator_dir).expanduser() if accumulator_dir.strip() else MBCDS3_DAILY_SHADOW_DEFAULT_ACCUMULATOR
    if not out.is_absolute():
        out = ROOT / out
    inventory = Path(inventory_path).expanduser() if inventory_path.strip() else job_dir / MBCDS3_DAILY_SHADOW_DEFAULT_INVENTORY_NAME
    if not inventory.is_absolute():
        inventory = ROOT / inventory
    inventory_resolved = inventory.resolve()
    same_run_inventory = inventory_resolved == (job_dir / MBCDS3_DAILY_SHADOW_DEFAULT_INVENTORY_NAME).resolve()
    isolated_inventory = inventory_resolved.is_relative_to(MBCDS3_DAILY_SHADOW_ROOT)
    if not out.resolve().is_relative_to(MBCDS3_DAILY_SHADOW_ROOT) or not (same_run_inventory or isolated_inventory):
        result.update({"ok": False, "status": "BLOCKED_MBCDS3_PATH_OUTSIDE_ALLOWED_ROOT", "error": "output must remain isolated and inventory must be exact same-run or isolated evidence"})
        write_json(job_dir / "mbcds3_daily_shadow.json", result)
        return result

    if not (out / "accumulator.csv").is_file():
        bootstrap = command_runner(
            [PYTHON, str(MBCDS3_DAILY_SHADOW_ACCUMULATOR_BUILDER.relative_to(ROOT)), "--out", str(out)],
            cwd=ROOT,
            stdout_path=job_dir / "mbcds3_bootstrap_stdout.json",
            stderr_path=job_dir / "mbcds3_bootstrap_stderr.txt",
            timeout=300,
        )
        result["bootstrap"] = bootstrap
        if not bootstrap.get("ok") or not (out / "accumulator.csv").is_file():
            result.update({"ok": False, "status": "BLOCKED_MBCDS3_ACCUMULATOR_BOOTSTRAP_FAILED", "error": "isolated accumulator bootstrap failed"})
            write_json(job_dir / "mbcds3_daily_shadow.json", result)
            return result

    if not inventory.is_file():
        result.update({
            "ok": True,
            "status": "BLOCKED_MBCDS3_DAILY_INVENTORY_MISSING",
            "error": "same-run compatibility inventory is not available; baseline continues",
            "inventory": rel_path(inventory),
            "accumulator": rel_path(out),
        })
        write_json(job_dir / "mbcds3_daily_shadow.json", result)
        return result

    try:
        with inventory.open(encoding="utf-8-sig", newline="") as stream:
            inventory_rows = list(csv.DictReader(stream))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        result.update({"ok": False, "status": "BLOCKED_MBCDS3_DAILY_INVENTORY_UNREADABLE", "error": str(exc)})
        write_json(job_dir / "mbcds3_daily_shadow.json", result)
        return result
    target_rows = [row for row in inventory_rows if str(row.get("required_date") or row.get("date") or "") == asof]
    target_ready = bool(
        len(target_rows) == 1
        and target_rows[0].get("status") == "PASS"
        and target_rows[0].get("inventory_validation") == "PASS"
        and target_rows[0].get("lineage_gate") == "True"
        and target_rows[0].get("lineage_metadata") == "COMPLETE"
        and target_rows[0].get("pit_metadata") == "PRESENT"
        and target_rows[0].get("lineage_complete") == "True"
    )
    if not target_ready:
        result.update({
            "ok": True,
            "status": "BLOCKED_MBCDS3_DAILY_INVENTORY_NOT_ACCEPTED",
            "error": "same-run input is incomplete; attempt remains in the job audit and does not occupy the canonical accumulator date",
            "inventory": rel_path(inventory),
            "accumulator": rel_path(out),
        })
        write_json(job_dir / "mbcds3_daily_shadow.json", result)
        return result

    command = [
        PYTHON, str(DAPR18_MBCDS3_DAILY_SHADOW_ADAPTER.relative_to(ROOT)),
        "--inventory", str(inventory), "--target-asof", asof, "--out", str(out),
    ]
    invocation = command_runner(
        command,
        cwd=ROOT,
        stdout_path=job_dir / "mbcds3_daily_shadow_stdout.json",
        stderr_path=job_dir / "mbcds3_daily_shadow_stderr.txt",
        timeout=300,
    )
    result.update({
        "status": "APPEND_ACCEPTED" if invocation.get("ok") else "APPEND_REJECTED_OR_BLOCKED",
        "ok": bool(invocation.get("ok")),
        "inventory": rel_path(inventory),
        "accumulator": rel_path(out),
        "invocation": invocation,
    })
    write_json(job_dir / "mbcds3_daily_shadow.json", result)
    return result


def run_o4_prospective_shadow_nonblocking(
    *, asof: str, job_id: str, job_dir: Path, source_run_id: str, decision_cutoff: str,
    enabled: bool, command_runner=run_cmd,
) -> dict[str, Any]:
    """Invoke the isolated 78-D O4 adapter without entering publish paths."""
    result: dict[str, Any] = {"enabled": bool(enabled), "attempted": False, "ok": True, "status": "DISABLED"}
    if not enabled:
        return result
    result["attempted"] = True
    argv = [
        PYTHON, str(O4_NONBLOCKING_ADAPTER.relative_to(ROOT)), "--asof", asof,
        "--source-run-id", source_run_id, "--decision-cutoff", decision_cutoff,
        "--job-dir", str(job_dir), "--ledger", str(O4_PROSPECTIVE_LEDGER), "--json",
    ]
    env_paths = {
        "TW_O4_DAILY_PRICE_ADAPTER": "--daily-price-adapter",
        "TW_O4_INSTITUTIONAL_ADAPTER": "--institutional-adapter",
        "TW_O4_MARGIN_ADAPTER": "--margin-adapter",
        "TW_O4_TWII_RAW": "--twii-raw",
        "TW_O4_TWII_CAPTURE": "--twii-capture",
        "TW_O4_CALENDAR": "--calendar",
        "TW_O4_OUTPUT_DIR": "--output-dir",
    }
    for env_name, flag in env_paths.items():
        value = os.getenv(env_name, "").strip()
        if value:
            argv.extend([flag, value])
    for signal in [item.strip() for item in os.getenv("TW_O4_MODEL_A_SIGNALS", "").split(",") if item.strip()]:
        argv.extend(["--model-a-signals", signal])
    invocation = command_runner(
        argv, cwd=ROOT, stdout_path=job_dir / "o4_prospective_shadow_stdout.json",
        stderr_path=job_dir / "o4_prospective_shadow_stderr.txt", timeout=900,
    )
    result["invocation"] = invocation
    result["status_path"] = rel_path(job_dir / "o4_prospective_shadow_status.json")
    result["status"] = "NONBLOCKING_ADAPTER_COMPLETED" if invocation.get("ok") else "NONBLOCKING_ADAPTER_INVOCATION_FAILED"
    # Adapter failures are terminal shadow evidence, never Model A/daily failure.
    result["ok"] = True
    return result


def run_mbcds35_prospective_shadow(
    *, asof: str, job_id: str, job_dir: Path, enabled: bool, accumulator_dir: str,
    inventory_path: str, source_ledger: Path, command_runner=run_cmd,
) -> dict[str, Any]:
    """Run the isolated Model B shadow path; every failure is non-blocking for Model A."""
    result: dict[str, Any] = {
        "enabled": bool(enabled), "attempted": False, "ok": True,
        "status": "DISABLED" if not enabled else "WAITING_FOR_WARMUP",
        "model_a_non_blocking": True, "production_allowed": False, "published": False,
    }
    if not enabled:
        return result
    accumulator = resolve_path(accumulator_dir) if accumulator_dir else MBCDS3_DAILY_SHADOW_DEFAULT_ACCUMULATOR
    run_root = MBCDS3_DAILY_SHADOW_ROOT / "mbcds35_daily_runs" / job_id
    feature_dir, score_dir = run_root / "features", run_root / "score"
    steps: list[dict[str, Any]] = []

    def invoke(name: str, command: list[str], timeout: int = 600) -> dict[str, Any]:
        try:
            call = command_runner(command, cwd=ROOT, stdout_path=job_dir / f"mbcds35_{name}_stdout.json",
                                  stderr_path=job_dir / f"mbcds35_{name}_stderr.txt", timeout=timeout)
        except Exception as exc:
            call = {"ok": False, "error": f"{type(exc).__name__}:{exc}"}
        steps.append({"name": name, "result": call})
        return call

    def settle_pending(excluded: set[str] | None = None) -> list[dict[str, Any]]:
        excluded = excluded or set()
        summary_path = MBCDS35_DEFAULT_LEDGER / "comparison_summary.json"
        events_path = MBCDS35_DEFAULT_LEDGER / "events.jsonl"
        if not summary_path.is_file() or not events_path.is_file() or not source_ledger.is_file():
            return []
        try:
            pending = list(read_json(summary_path).get("pending_outcome_days") or [])
            signal_sources: dict[str, Path] = {}
            for line in events_path.read_text(encoding="utf-8").splitlines():
                event = json.loads(line)
                if event.get("event_type") == "SIGNAL_REGISTERED":
                    signal_sources[str(event.get("asof"))] = resolve_path(str(event.get("model_a_signals") or ""))
        except (OSError, ValueError, json.JSONDecodeError):
            result["ledger_read_warning"] = "ledger_unreadable_settlement_deferred"
            return []
        attempts = []
        for signal_day in pending:
            if signal_day in excluded or signal_day not in signal_sources:
                continue
            outcome_dir = run_root / "outcomes" / signal_day
            built = invoke(f"outcome_{signal_day}", [PYTHON, str(MBCDS35_OUTCOME_BUILDER.relative_to(ROOT)),
                "--signal-asof", signal_day, "--source-ledger", str(source_ledger), "--trading-calendar", str(CALENDAR),
                "--symbols-file", str(signal_sources[signal_day]), "--out", str(outcome_dir)])
            settled = None
            if built.get("ok"):
                settled = invoke(f"settle_{signal_day}", [PYTHON, str(MBCDS35_LEDGER.relative_to(ROOT)), "--out", str(MBCDS35_DEFAULT_LEDGER),
                    "settle-outcome", "--asof", signal_day, "--outcomes", str(outcome_dir / "outcomes.csv"),
                    "--outcome-manifest", str(outcome_dir / "manifest.json"), "--trading-calendar", str(CALENDAR)])
            attempts.append({"asof": signal_day, "candidate_ready": bool(built.get("ok")), "settled": bool(settled and settled.get("ok"))})
        return attempts

    # Settlement consumes only prior immutable signals and is deliberately
    # independent from today's feature/scoring success.
    settlement_attempts = settle_pending()
    readiness_path = accumulator / "warmup_readiness.json"
    if not readiness_path.is_file():
        result.update({"reason": "warmup_readiness_missing", "steps": steps, "settlement_attempts": settlement_attempts})
        return result
    readiness = read_json(readiness_path)
    result["warmup"] = readiness
    if not bool(readiness.get("can_shadow_score")) or int(readiness.get("valid_input_days", 0)) < 20:
        result.update({"reason": "valid_input_days_below_20", "steps": steps, "settlement_attempts": settlement_attempts})
        return result
    result["attempted"] = True
    inventory = resolve_path(inventory_path)
    try:
        rows = read_csv_dicts(inventory)
        target = [row for row in rows if str(row.get("required_date") or row.get("date") or "") == asof]
        if len(target) != 1:
            raise ValueError("same_run_inventory_target_cardinality")
        model_a = resolve_path(str(target[0].get("path") or target[0].get("compatible_paths") or ""))
        model_a_manifest = model_a.parent / "manifest.json"
        if not model_a.is_file() or not model_a_manifest.is_file() or not source_ledger.is_file():
            raise ValueError("explicit_model_a_manifest_or_source_ledger_missing")
    except (OSError, ValueError, csv.Error) as exc:
        result.update({"status": "BLOCKED_INPUT_BINDING", "reason": str(exc), "steps": steps, "settlement_attempts": settlement_attempts})
        return result

    feature = invoke("feature", [PYTHON, str(MBCDS35_FEATURE_BUILDER.relative_to(ROOT)), "--asof", asof,
        "--model-a-signals", str(model_a), "--source-ledger", str(source_ledger),
        "--accepted-accumulator", str(accumulator / "accumulator.csv"), "--out", str(feature_dir)])
    if not feature.get("ok"):
        result.update({"status": "BLOCKED_FEATURES_NONBLOCKING", "steps": steps, "settlement_attempts": settlement_attempts})
        return result
    scoring = invoke("score", [PYTHON, str(MBCDS35_FROZEN_SCORER.relative_to(ROOT)), "--asof", asof,
        "--feature-frame", str(feature_dir / "feature_frame.csv"), "--feature-manifest", str(feature_dir / "manifest.json"),
        "--model-a-signals", str(model_a), "--source-ledger", str(source_ledger), "--out", str(score_dir)])
    if not scoring.get("ok"):
        result.update({"status": "BLOCKED_SCORER_NONBLOCKING", "steps": steps, "settlement_attempts": settlement_attempts})
        return result
    record = invoke("record", [PYTHON, str(MBCDS35_LEDGER.relative_to(ROOT)), "--out", str(MBCDS35_DEFAULT_LEDGER),
        "record-signal", "--asof", asof, "--valid-day-inventory", str(accumulator / "accumulator.csv"),
        "--model-a-signals", str(model_a), "--model-a-manifest", str(model_a_manifest),
        "--model-b-signals", str(score_dir / "model_b_shadow_signals.csv"), "--model-b-manifest", str(score_dir / "manifest.json")])
    if not record.get("ok"):
        result.update({"status": "BLOCKED_RECORD_NONBLOCKING", "steps": steps, "settlement_attempts": settlement_attempts})
        return result
    settlement_attempts.extend(settle_pending({item["asof"] for item in settlement_attempts}))
    result.update({"status": "SHADOW_RECORDED", "model_b_scoring": True, "steps": steps,
                   "settlement_attempts": settlement_attempts, "pending_is_nonblocking": True})
    return result


def build_mbcds3_source_availability_ledger(
    *,
    asof: str,
    job: dict[str, Any],
    job_dir: Path,
    decision_cutoff: str,
) -> dict[str, Any]:
    """Freeze source availability evidence from the same-run HSA8 handoff."""
    handoff = job.get("same_run_handoff") if isinstance(job.get("same_run_handoff"), dict) else {}
    sources = handoff.get("sources") if isinstance(handoff.get("sources"), list) else []
    run_id = str(handoff.get("acquisition_run_id") or job.get("acquisition_logical_run_id") or "")
    errors: list[str] = []
    times: list[tuple[str, datetime, datetime]] = []
    artifact_checksums: dict[str, str] = {}
    for source in sources:
        family = str(source.get("source_family") or "unknown")
        if str(source.get("target_asof") or "") != asof or str(source.get("acquisition_run_id") or "") != run_id:
            errors.append(f"{family}:run_or_asof_mismatch")
            continue
        try:
            available = datetime.fromisoformat(str(source.get("available_at")).replace("Z", "+00:00"))
            fetched = datetime.fromisoformat(str(source.get("fetched_at")).replace("Z", "+00:00"))
            cutoff = datetime.fromisoformat(decision_cutoff.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            errors.append(f"{family}:invalid_availability_timestamp")
            continue
        if available.tzinfo is None or fetched.tzinfo is None or cutoff.tzinfo is None:
            errors.append(f"{family}:timestamp_must_be_timezone_aware")
            continue
        if not available <= fetched <= cutoff:
            errors.append(f"{family}:availability_order_invalid")
            continue
        artifacts = source.get("artifacts") if isinstance(source.get("artifacts"), list) else []
        if not artifacts:
            errors.append(f"{family}:artifact_checksums_missing")
        for artifact in artifacts:
            if not isinstance(artifact, dict) or not artifact.get("path") or not artifact.get("sha256"):
                errors.append(f"{family}:artifact_checksum_entry_invalid")
                continue
            artifact_path = resolve_path(str(artifact["path"]))
            expected_sha = str(artifact["sha256"])
            if not artifact_path.is_file() or str(file_fingerprint(artifact_path).get("sha256") or "") != expected_sha:
                errors.append(f"{family}:artifact_checksum_mismatch")
            else:
                artifact_checksums[str(artifact["path"])] = expected_sha
        times.append((family, available, fetched))
    status = "PASS" if sources and not errors and len(times) == len(sources) else "BLOCKED_SOURCE_AVAILABILITY"
    ledger = {
        "schema_version": "mbcds3.source_availability_ledger.v1",
        "status": status,
        "asof": asof,
        "acquisition_run_id": run_id,
        "decision_cutoff": decision_cutoff,
        "source_count": len(sources),
        "source_families": [item[0] for item in times],
        "artifact_checksums": artifact_checksums,
        "combined_available_at": max((item[1] for item in times), default=None).isoformat() if times else "",
        "combined_fetched_at": max((item[2] for item in times), default=None).isoformat() if times else "",
        "errors": errors,
        "same_run_handoff_status": handoff.get("handoff_kind") or handoff.get("status") or "",
        "production_allowed": False,
        "writes_protected_latest": False,
    }
    write_json(job_dir / "mbcds3_source_availability_ledger.json", ledger)
    return ledger


def build_mbcds3_daily_inventory_bridge(
    *,
    asof: str,
    job_dir: Path,
    model_signal_gate: dict[str, Any],
    availability_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Materialize a same-run MBCDS3 inventory without inventing PIT metadata."""
    bridge: dict[str, Any] = {
        "schema_version": "mbcds3.daily_same_run_inventory_bridge.v1",
        "status": "BLOCKED_MODEL_SIGNAL_NOT_READY",
        "ok": False,
        "asof": asof,
        "inventory_path": "",
        "pit_metadata_complete": False,
        "pit_missing_fields": ["available_at", "decision_cutoff"],
        "same_run_binding": False,
        "rows": 0,
        "reason": "model signal gate did not produce a validated same-run Model A artifact",
    }
    summary = model_signal_gate.get("summary") if isinstance(model_signal_gate.get("summary"), dict) else {}
    availability_ledger = availability_ledger if isinstance(availability_ledger, dict) else {}
    artifacts = summary.get("artifacts") if isinstance(summary.get("artifacts"), dict) else {}
    score_dir = resolve_path(str(artifacts.get("score_job") or ""))
    score_manifest_path = score_dir / "manifest.json"
    if not score_manifest_path.is_file() or summary.get("model_signal_status") != "READY":
        path = job_dir / "mbcds3_compatibility_inventory.csv"
        bridge["inventory_path"] = rel_path(path)
        bridge["reason"] = "validated Model A signal artifact unavailable"
        write_json(job_dir / "mbcds3_inventory_bridge.json", bridge)
        return bridge

    score_manifest = read_json(score_manifest_path)
    if str(score_manifest.get("asof") or "") != asof:
        bridge.update({
            "status": "BLOCKED_MODEL_SIGNAL_ASOF_MISMATCH",
            "reason": "validated Model A score manifest asof does not match the current daily target",
            "source_asof": str(score_manifest.get("asof") or ""),
        })
        write_json(job_dir / "mbcds3_inventory_bridge.json", bridge)
        return bridge
    raw_entry = next((item for item in score_manifest.get("required_file_entries", []) if item.get("key") == "raw_scores"), {})
    model_entry = next((item for item in score_manifest.get("required_file_entries", []) if item.get("key") == "source_model_artifact"), {})
    raw_scores = resolve_path(str(raw_entry.get("path") or score_dir / "raw_scores.csv"))
    model_path = resolve_path(str(model_entry.get("path") or score_manifest.get("source_model_artifact") or ""))
    qlib_source = score_manifest.get("qlib_source_run") if isinstance(score_manifest.get("qlib_source_run"), dict) else {}
    source_run_dir = resolve_path(str(qlib_source.get("run_dir") or ""))
    source_run_id = str(qlib_source.get("run_id") or score_manifest.get("run_id") or "")
    score_acquisition_run_id = str(score_manifest.get("source_acquisition_run_id") or "")
    feature_path = str(score_manifest.get("source_feature_artifact") or "")
    fields = [
        "required_date", "date", "path", "compatible_paths", "status", "inventory_validation",
        "lineage_gate", "lineage_metadata", "pit_metadata", "lineage_complete", "available_at",
        "decision_cutoff", "model_id", "source_model_artifact", "source_model_artifact_sha256",
        "source_feature_artifact", "provider_uri", "source_run_id", "qlib_source_run_id", "qlib_source_run_dir",
    ]
    ledger_pass = availability_ledger.get("status") == "PASS"
    ledger_run_id = str(availability_ledger.get("acquisition_run_id") or "")
    qlib_run_bound = bool(ledger_pass and ledger_run_id and ledger_run_id == score_acquisition_run_id)
    pit_available_at = str(availability_ledger.get("combined_available_at") or "") if qlib_run_bound else ""
    pit_decision_cutoff = str(availability_ledger.get("decision_cutoff") or "") if qlib_run_bound else ""
    pit_complete = bool(qlib_run_bound and pit_available_at and pit_decision_cutoff)
    row = {
        "required_date": asof,
        "date": asof,
        "path": rel_path(raw_scores) if raw_scores.is_file() else "",
        "compatible_paths": rel_path(raw_scores) if raw_scores.is_file() else "",
        "status": "PASS" if raw_scores.is_file() and model_path.is_file() else "BLOCKED",
        "inventory_validation": "PASS" if raw_scores.is_file() else "BLOCKED",
        "lineage_gate": "True" if source_run_id and source_run_dir.is_dir() else "False",
        "lineage_metadata": "COMPLETE" if qlib_run_bound else "INCOMPLETE",
        "pit_metadata": "PRESENT" if pit_complete else "INCOMPLETE",
        "lineage_complete": "True" if qlib_run_bound else "False",
        "available_at": pit_available_at,
        "decision_cutoff": pit_decision_cutoff,
        "model_id": str(score_manifest.get("model_id") or ""),
        "source_model_artifact": rel_path(model_path) if model_path.is_file() else "",
        "source_model_artifact_sha256": str(model_entry.get("sha256") or ""),
        "source_feature_artifact": feature_path,
        "provider_uri": feature_path,
        "source_run_id": ledger_run_id,
        "qlib_source_run_id": source_run_id,
        "qlib_source_run_dir": rel_path(source_run_dir) if source_run_dir.is_dir() else "",
    }
    path = job_dir / "mbcds3_compatibility_inventory.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)
    bridge.update({
        "status": "BRIDGED_WITH_PIT_METADATA_BLOCKER",
        "ok": True,
        "inventory_path": rel_path(path),
        "rows": 1,
        "same_run_binding": qlib_run_bound,
        "pit_metadata_complete": pit_complete,
        "pit_missing_fields": [] if pit_complete else ["available_at", "decision_cutoff", "score_source_run_binding"],
        "reason": "same-run PIT metadata bound" if pit_complete else "Model A artifact is bridged, but source availability timestamps or score-source run binding are absent and must remain quarantined",
        "source_run_id": source_run_id,
        "raw_scores_path": rel_path(raw_scores) if raw_scores.is_file() else "",
    })
    write_json(job_dir / "mbcds3_inventory_bridge.json", bridge)
    return bridge


def empty_finmind_report(*, symbols: list[str], start: str, end: str, apply: bool = True) -> dict[str, Any]:
    return {
        "symbols": symbols,
        "start": start,
        "end": end,
        "apply": bool(apply),
        "archive": {"count": 0, "symbols": [], "date_min": None, "date_max": None},
        "archived_count": 0,
        "validation": {},
        "validation_updated_count": 0,
        "corporate_actions": {"count": 0, "symbols": [], "date_min": None, "date_max": None},
        "corporate_actions_archived_count": 0,
        "institutional_trades": {"count": 0, "symbols": [], "date_min": None, "date_max": None},
        "institutional_trades_archived_count": 0,
        "margin_trading": {"count": 0, "symbols": [], "date_min": None, "date_max": None},
        "margin_trading_archived_count": 0,
        "monthly_revenue": {"count": 0, "symbols": [], "date_min": None, "date_max": None},
        "monthly_revenue_archived_count": 0,
        "valuation": {"count": 0, "symbols": [], "date_min": None, "date_max": None},
        "valuation_archived_count": 0,
    }


def merge_finmind_segment_payloads(
    segment_results: dict[str, dict[str, Any]],
    *,
    symbols: list[str],
    start: str,
    end: str,
) -> dict[str, Any]:
    merged = empty_finmind_report(symbols=symbols, start=start, end=end)
    for segment, result in segment_results.items():
        payload = parse_json_stdout(result)
        if not payload:
            continue
        if isinstance(payload.get("hsa8_capture"), dict):
            capture = merged.setdefault("hsa8_capture", {})
            for capture_name, capture_value in payload["hsa8_capture"].items():
                if isinstance(capture_value, dict) and capture_value.get("status") == "captured":
                    capture[capture_name] = capture_value
                elif capture_name not in capture:
                    capture[capture_name] = capture_value
        if segment == "daily_price":
            for key in ("archive", "archived_count", "validation", "validation_updated_count"):
                merged[key] = payload.get(key, merged[key])
        elif segment == "corporate_actions":
            for key in ("corporate_actions", "corporate_actions_archived_count"):
                merged[key] = payload.get(key, merged[key])
        elif segment == "institutional":
            for key in ("institutional_trades", "institutional_trades_archived_count"):
                merged[key] = payload.get(key, merged[key])
        elif segment == "margin":
            for key in ("margin_trading", "margin_trading_archived_count"):
                merged[key] = payload.get(key, merged[key])
        elif segment == "monthly_revenue":
            for key in ("monthly_revenue", "monthly_revenue_archived_count"):
                merged[key] = payload.get(key, merged[key])
        elif segment == "valuation":
            for key in ("valuation", "valuation_archived_count"):
                merged[key] = payload.get(key, merged[key])
    merged["segment_status"] = {
        segment: {
            "ok": bool(result.get("ok")),
            "returncode": result.get("returncode"),
            "cached": bool(result.get("cached")),
            "provider_error": str(result.get("provider_error") or classify_finmind_provider_error(result)),
            "cooldown_until": str(result.get("cooldown_until") or ""),
            "stdout_path": rel_path(resolve_path(str(result.get("stdout_path") or ""))) if result.get("stdout_path") else "",
            "stderr_path": rel_path(resolve_path(str(result.get("stderr_path") or ""))) if result.get("stderr_path") else "",
        }
        for segment, result in segment_results.items()
    }
    return merged


def status_from_finmind_result(result: dict[str, Any]) -> str:
    if result.get("ok"):
        return "success"
    provider_error = str(result.get("provider_error") or classify_finmind_provider_error(result))
    if provider_error in {"provider_402_quota_or_payment_required", "provider_rate_limited"}:
        return "quota_exhausted_retry_next_day"
    if provider_error == "provider_timeout":
        return "provider_timeout"
    text = f"{result.get('stderr_tail') or ''}\n{result.get('stdout_tail') or ''}".lower()
    if "401" in text or "403" in text or "permission" in text or "unauthorized" in text:
        return "permission_denied"
    return "provider_error"


def finmind_orthogonal_state_path(*, asof: str) -> Path:
    return FINMIND_ORTHOGONAL_BATCH_STATE_ROOT / f"{asof}_institutional_margin.json"


def normalize_symbol_code(raw: str) -> str:
    text = str(raw or "").strip().upper()
    return text[2:] if text.startswith("TW") else text


def latest_compatible_finmind_orthogonal_state(*, before_asof: str, symbols: list[str]) -> tuple[dict[str, Any], Path | None]:
    symbol_set = {normalize_symbol_code(symbol) for symbol in symbols if normalize_symbol_code(symbol)}
    if not FINMIND_ORTHOGONAL_BATCH_STATE_ROOT.exists():
        return {}, None
    candidates: list[tuple[str, Path]] = []
    for path in FINMIND_ORTHOGONAL_BATCH_STATE_ROOT.glob("*_institutional_margin.json"):
        checkpoint_asof = path.name.removesuffix("_institutional_margin.json")
        if checkpoint_asof < before_asof:
            candidates.append((checkpoint_asof, path))
    for _, path in sorted(candidates, reverse=True):
        previous = read_json(path)
        if previous.get("schema_version") != "finmind_orthogonal_batch_state_v1":
            continue
        previous_symbols = {normalize_symbol_code(symbol) for symbol in previous.get("symbols", []) if normalize_symbol_code(symbol)}
        if symbol_set and previous_symbols and not symbol_set.intersection(previous_symbols):
            continue
        return previous, path
    return {}, None


def sanitize_orthogonal_dataset_row(row: dict[str, Any], *, symbol_set: set[str]) -> dict[str, Any]:
    done_symbols = sorted({normalize_symbol_code(x) for x in row.get("done_symbols", []) if normalize_symbol_code(x) in symbol_set})
    failed_symbols = sorted({normalize_symbol_code(x) for x in row.get("failed_symbols", []) if normalize_symbol_code(x) in symbol_set})
    return {
        **row,
        "done_symbols": done_symbols,
        "failed_symbols": failed_symbols,
        "cursor": len(done_symbols),
    }


def load_finmind_orthogonal_state(*, asof: str, symbols: list[str]) -> dict[str, Any]:
    path = finmind_orthogonal_state_path(asof=asof)
    state = read_json(path)
    normalized_symbols = [normalize_symbol_code(symbol) for symbol in symbols if normalize_symbol_code(symbol)]
    symbol_set = set(normalized_symbols)
    if state.get("schema_version") != "finmind_orthogonal_batch_state_v1" or state.get("asof") != asof:
        previous, previous_path = latest_compatible_finmind_orthogonal_state(before_asof=asof, symbols=normalized_symbols)
        previous_datasets = previous.get("datasets") if isinstance(previous.get("datasets"), dict) else {}
        inherited_datasets: dict[str, dict[str, Any]] = {}
        for dataset in ("institutional", "margin"):
            previous_row = previous_datasets.get(dataset) if isinstance(previous_datasets.get(dataset), dict) else {}
            inherited_datasets[dataset] = sanitize_orthogonal_dataset_row(previous_row, symbol_set=symbol_set)
            inherited_datasets[dataset]["failed_symbols"] = []
            inherited_datasets[dataset]["last_status"] = str(previous_row.get("last_status") or "")
            inherited_datasets[dataset].pop("last_attempted_symbols", None)
            inherited_datasets[dataset].pop("last_attempted_at", None)
        historical_provider_error = str(previous.get("historical_last_provider_error") or previous.get("last_provider_error") or "")
        state = {
            "schema_version": "finmind_orthogonal_batch_state_v1",
            "asof": asof,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "symbols": normalized_symbols,
            "datasets": inherited_datasets,
            "cooldown_until": "",
            "last_provider_error": historical_provider_error,
            "historical_last_provider_error": historical_provider_error,
            "last_run_provider_error": "",
            "current_provider_blocker": "",
            "inherited_from_checkpoint": rel_path(previous_path) if previous_path else "",
        }
    else:
        state["symbols"] = normalized_symbols
        datasets = state.setdefault("datasets", {})
        for dataset in ("institutional", "margin"):
            row = datasets.setdefault(dataset, {"done_symbols": [], "failed_symbols": [], "cursor": 0, "last_status": ""})
            datasets[dataset] = sanitize_orthogonal_dataset_row(row, symbol_set=symbol_set)
        state.setdefault("historical_last_provider_error", str(state.get("last_provider_error") or ""))
        state.setdefault("last_run_provider_error", "")
        state.setdefault("current_provider_blocker", "")
    return state


def write_finmind_orthogonal_state(state: dict[str, Any], *, asof: str) -> Path:
    state["updated_at"] = utc_now()
    path = finmind_orthogonal_state_path(asof=asof)
    write_json(path, state)
    return path


def is_finmind_orthogonal_cooling_down(state: dict[str, Any]) -> bool:
    cooldown_until = str(state.get("cooldown_until") or "")
    if not cooldown_until:
        return False
    try:
        return datetime.fromisoformat(cooldown_until) > datetime.now(timezone.utc)
    except ValueError:
        return False


def select_orthogonal_batch_symbols(state: dict[str, Any], *, batch_size: int) -> list[str]:
    symbols = [normalize_symbol_code(x) for x in state.get("symbols", []) if normalize_symbol_code(x)]
    datasets = state.get("datasets") if isinstance(state.get("datasets"), dict) else {}
    done_sets: list[set[str]] = []
    for dataset in ("institutional", "margin"):
        row = datasets.get(dataset) if isinstance(datasets.get(dataset), dict) else {}
        done_sets.append({normalize_symbol_code(x) for x in row.get("done_symbols", []) if normalize_symbol_code(x)})
    fully_done = set.intersection(*done_sets) if done_sets else set()
    pending = [symbol for symbol in symbols if symbol not in fully_done]
    if not pending:
        return []
    return pending[: max(1, int(batch_size))]


def write_symbols_file(path: Path, symbols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(normalize_symbol_code(x) for x in symbols if normalize_symbol_code(x)) + "\n", encoding="utf-8")


def apply_orthogonal_batch_result_to_state(
    state: dict[str, Any],
    *,
    selected_symbols: list[str],
    dataset: str,
    result: dict[str, Any],
    cooldown_hours: float,
) -> str:
    status = status_from_finmind_result(result)
    datasets = state.setdefault("datasets", {})
    row = datasets.setdefault(dataset, {"done_symbols": [], "failed_symbols": [], "cursor": 0, "last_status": ""})
    selected = [normalize_symbol_code(x) for x in selected_symbols if normalize_symbol_code(x)]
    done = set(normalize_symbol_code(x) for x in row.get("done_symbols", []) if normalize_symbol_code(x))
    failed = set(normalize_symbol_code(x) for x in row.get("failed_symbols", []) if normalize_symbol_code(x))
    if status == "success":
        done.update(selected)
        failed.difference_update(selected)
        state["last_run_provider_error"] = ""
        state["current_provider_blocker"] = ""
    else:
        failed.update(selected)
        provider_error = str(result.get("provider_error") or classify_finmind_provider_error(result))
        state["last_provider_error"] = provider_error
        state["historical_last_provider_error"] = provider_error
        state["last_run_provider_error"] = provider_error
        state["current_provider_blocker"] = provider_error
        if status == "quota_exhausted_retry_next_day":
            state["cooldown_until"] = (datetime.now(timezone.utc) + timedelta(hours=cooldown_hours)).replace(microsecond=0).isoformat()
    row["done_symbols"] = sorted(done)
    row["failed_symbols"] = sorted(failed)
    row["cursor"] = len(row["done_symbols"])
    row["last_status"] = status
    row["last_attempted_symbols"] = selected
    row["last_attempted_at"] = utc_now()
    return status


def build_orthogonal_batch_summary(
    state: dict[str, Any],
    *,
    asof: str,
    selected_symbols: list[str],
    state_path: Path,
    batch_size: int,
    lookback_days: int,
    dataset_status: dict[str, str],
    skipped_reason: str = "",
) -> dict[str, Any]:
    total_symbols = len(state.get("symbols", []) or [])
    datasets = state.get("datasets") if isinstance(state.get("datasets"), dict) else {}
    coverage: dict[str, Any] = {}
    complete = True
    partial = False
    quota_status = False
    for dataset in ("institutional", "margin"):
        row = datasets.get(dataset) if isinstance(datasets.get(dataset), dict) else {}
        done_count = len(row.get("done_symbols", []) or [])
        failed_count = len(row.get("failed_symbols", []) or [])
        status = dataset_status.get(dataset) or str(row.get("last_status") or "")
        coverage[dataset] = {
            "done_symbol_count": done_count,
            "failed_symbol_count": failed_count,
            "total_symbol_count": total_symbols,
            "last_status": status,
        }
        complete = complete and total_symbols > 0 and done_count >= total_symbols
        partial = partial or done_count > 0
        quota_status = quota_status or status == "quota_exhausted_retry_next_day"
    if skipped_reason:
        status = "quota_exhausted_retry_next_day" if skipped_reason == "cooldown_active" else "skipped"
    elif complete:
        status = "success"
    elif quota_status:
        status = "quota_exhausted_retry_next_day"
    elif partial:
        status = "success_partial"
    else:
        statuses = {value for value in dataset_status.values() if value}
        status = sorted(statuses)[0] if statuses else "success_partial"
    return {
        "schema_version": "finmind_orthogonal_batch_control_v1",
        "asof": asof,
        "status": status,
        "batch_size": int(batch_size),
        "lookback_days": int(lookback_days),
        "selected_symbols": [normalize_symbol_code(x) for x in selected_symbols],
        "selected_symbol_count": len(selected_symbols),
        "selection_partial_reason": "remaining_symbols_below_batch_size" if 0 < len(selected_symbols) < int(batch_size) else "",
        "checkpoint_path": rel_path(state_path),
        "cooldown_until": str(state.get("cooldown_until") or ""),
        "last_provider_error": str(state.get("last_provider_error") or ""),
        "historical_last_provider_error": str(state.get("historical_last_provider_error") or state.get("last_provider_error") or ""),
        "last_run_provider_error": str(state.get("last_run_provider_error") or ""),
        "current_provider_blocker": str(state.get("current_provider_blocker") or ""),
        "inherited_from_checkpoint": str(state.get("inherited_from_checkpoint") or ""),
        "coverage": coverage,
        "next_retry_hint": "retry_next_scheduled_daily_auto_run" if status != "success" else "",
        "skipped_reason": skipped_reason,
    }


def run_finmind_orthogonal_batch_update(
    *,
    symbols_file: Path,
    job_dir: Path,
    asof: str,
    timeout_seconds: int,
    batch_size: int,
    lookback_days: int,
    cooldown_hours: float,
    command_runner=run_cmd,
) -> dict[str, Any]:
    job_dir.mkdir(parents=True, exist_ok=True)
    symbols = [line.strip() for line in symbols_file.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    state = load_finmind_orthogonal_state(asof=asof, symbols=symbols)
    state_path = write_finmind_orthogonal_state(state, asof=asof)
    selected_symbols = select_orthogonal_batch_symbols(state, batch_size=batch_size)
    if is_finmind_orthogonal_cooling_down(state):
        state["current_provider_blocker"] = "cooldown_active"
        stdout_path = job_dir / "finmind_orthogonal_batch_stdout.txt"
        stderr_path = job_dir / "finmind_orthogonal_batch_stderr.txt"
        summary = build_orthogonal_batch_summary(
            state,
            asof=asof,
            selected_symbols=[],
            state_path=state_path,
            batch_size=batch_size,
            lookback_days=lookback_days,
            dataset_status={},
            skipped_reason="cooldown_active",
        )
        stdout_path.write_text(json.dumps({"orthogonal_batch_control": summary}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return {
            "ok": False,
            "returncode": 1,
            "orthogonal_batch": True,
            "status": summary["status"],
            "summary": summary,
            "argv": ["finmind_orthogonal_batch_cooldown"],
            "cwd": str(ROOT),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "stdout_tail": stdout_path.read_text(encoding="utf-8")[-3000:],
            "stderr_tail": "",
        }
    if not selected_symbols:
        stdout_path = job_dir / "finmind_orthogonal_batch_stdout.txt"
        stderr_path = job_dir / "finmind_orthogonal_batch_stderr.txt"
        summary = build_orthogonal_batch_summary(
            state,
            asof=asof,
            selected_symbols=[],
            state_path=state_path,
            batch_size=batch_size,
            lookback_days=lookback_days,
            dataset_status={"institutional": "success", "margin": "success"},
        )
        stdout_path.write_text(json.dumps({"orthogonal_batch_control": summary}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "orthogonal_batch": True,
            "status": "success",
            "summary": summary,
            "argv": ["finmind_orthogonal_batch_already_complete"],
            "cwd": str(ROOT),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "stdout_tail": stdout_path.read_text(encoding="utf-8")[-3000:],
            "stderr_tail": "",
        }

    batch_symbols_file = job_dir / "finmind_orthogonal_batch_symbols.txt"
    write_symbols_file(batch_symbols_file, selected_symbols)
    start = (datetime.strptime(asof, "%Y-%m-%d").date() - timedelta(days=max(1, int(lookback_days)))).isoformat()
    base_argv = [
        PYTHON,
        "backend/scripts/update_tw_stock_daily.py",
        "--symbols-file",
        str(batch_symbols_file),
        "--start",
        start,
        "--end",
        asof,
        "--apply",
        "--no-validate",
    ]
    dataset_flags = {
        "institutional": ["--no-daily-price", "--no-corporate-actions", "--no-margin", "--no-monthly-revenue", "--no-valuation"],
        "margin": ["--no-daily-price", "--no-corporate-actions", "--no-institutional", "--no-monthly-revenue", "--no-valuation"],
    }
    dataset_results: dict[str, dict[str, Any]] = {}
    dataset_status: dict[str, str] = {}
    for dataset in ("institutional", "margin"):
        if is_finmind_orthogonal_cooling_down(state):
            dataset_status[dataset] = "quota_exhausted_retry_next_day"
            continue
        result = command_runner(
            [*base_argv, *dataset_flags[dataset]],
            cwd=ROOT,
            stdout_path=job_dir / f"finmind_orthogonal_{dataset}_stdout.txt",
            stderr_path=job_dir / f"finmind_orthogonal_{dataset}_stderr.txt",
            timeout=timeout_seconds,
        )
        dataset_results[dataset] = result
        status = apply_orthogonal_batch_result_to_state(
            state,
            selected_symbols=selected_symbols,
            dataset=dataset,
            result=result,
            cooldown_hours=cooldown_hours,
        )
        dataset_status[dataset] = status
        if status == "quota_exhausted_retry_next_day":
            break
    state_path = write_finmind_orthogonal_state(state, asof=asof)
    summary = build_orthogonal_batch_summary(
        state,
        asof=asof,
        selected_symbols=selected_symbols,
        state_path=state_path,
        batch_size=batch_size,
        lookback_days=lookback_days,
        dataset_status=dataset_status,
    )
    stdout_path = job_dir / "finmind_orthogonal_batch_stdout.txt"
    stderr_path = job_dir / "finmind_orthogonal_batch_stderr.txt"
    stdout_path.write_text(
        json.dumps(
            {
                "orthogonal_batch_control": summary,
                "dataset_status": dataset_status,
                "dataset_results": {
                    dataset: {
                        "ok": bool(result.get("ok")),
                        "returncode": result.get("returncode"),
                        "provider_error": classify_finmind_provider_error(result),
                        "stdout_path": rel_path(resolve_path(str(result.get("stdout_path") or ""))) if result.get("stdout_path") else "",
                        "stderr_path": rel_path(resolve_path(str(result.get("stderr_path") or ""))) if result.get("stderr_path") else "",
                    }
                    for dataset, result in dataset_results.items()
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    stderr_path.write_text(
        "\n\n".join(
            f"===== {dataset} stderr =====\n{Path(str(result.get('stderr_path'))).read_text(encoding='utf-8') if result.get('stderr_path') and Path(str(result.get('stderr_path'))).exists() else ''}"
            for dataset, result in dataset_results.items()
        ),
        encoding="utf-8",
    )
    return {
        "ok": summary["status"] == "success",
        "returncode": 0 if summary["status"] == "success" else 1,
        "orthogonal_batch": True,
        "status": summary["status"],
        "summary": summary,
        "dataset_results": dataset_results,
        "argv": [*base_argv, "--orthogonal-batch-by-daily-auto"],
        "cwd": str(ROOT),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "stdout_tail": stdout_path.read_text(encoding="utf-8")[-3000:],
        "stderr_tail": stderr_path.read_text(encoding="utf-8")[-3000:],
    }


def attach_orthogonal_batch_to_finmind_stdout(job_dir: Path, summary: dict[str, Any]) -> None:
    stdout_path = job_dir / "finmind_stdout.txt"
    payload = parse_stdout_json(stdout_path)
    if not isinstance(payload, dict):
        payload = {}
    payload["orthogonal_batch_control"] = summary
    stdout_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def finmind_segment_cache_key(*, segment: str, end: str) -> str:
    return f"{end}_{segment}"


def finmind_segment_cache_path(*, segment: str, end: str) -> Path:
    return FINMIND_SEGMENT_CACHE_ROOT / f"{finmind_segment_cache_key(segment=segment, end=end)}.json"


def finmind_segment_cache_origin_issue(cache: dict[str, Any]) -> str:
    for key in ("stdout_path", "stderr_path"):
        raw = str(cache.get(key) or "").strip()
        if not raw:
            return f"missing_{key}"
        source = resolve_path(raw).resolve()
        try:
            source.relative_to(ROOT.resolve())
        except ValueError:
            return f"{key}_outside_repo"
        try:
            source.relative_to(OPS_ROOT.resolve())
        except ValueError:
            return f"{key}_outside_daily_auto_ops"
        if not source.exists() or not source.is_file():
            return f"{key}_missing"
    return ""


def classify_finmind_provider_error(result: dict[str, Any]) -> str:
    # A successful payload can contain arbitrary numbers and checksums. Never
    # infer an HTTP/provider failure from stdout when the command succeeded.
    if result.get("ok"):
        return ""
    text = f"{result.get('stderr_tail') or ''}\n{result.get('stdout_tail') or ''}".lower()
    if "402" in text or "payment required" in text:
        return "provider_402_quota_or_payment_required"
    if "429" in text or "too many requests" in text or "rate limit" in text:
        return "provider_rate_limited"
    if "read timed out" in text or "readtimeout" in text or "timeout" in text:
        return "provider_timeout"
    return "provider_error"


def segment_payload_covers_asof(segment: str, payload: dict[str, Any], *, end: str) -> bool:
    section_by_segment = {
        "daily_price": "archive",
        "corporate_actions": "corporate_actions",
        "institutional": "institutional_trades",
        "margin": "margin_trading",
        "monthly_revenue": "monthly_revenue",
        "valuation": "valuation",
    }
    section = payload.get(section_by_segment.get(segment, "")) if isinstance(payload.get(section_by_segment.get(segment, "")), dict) else {}
    if int(section.get("count") or 0) <= 0:
        return False
    if segment == "monthly_revenue":
        return bool(section.get("period_max"))
    return str(section.get("date_max") or "") >= end


def write_finmind_segment_cache(
    *,
    segment: str,
    end: str,
    result: dict[str, Any],
    cooldown_hours: float,
) -> dict[str, Any]:
    payload = parse_json_stdout(result)
    provider_error = classify_finmind_provider_error(result)
    covered = bool(result.get("ok") and segment_payload_covers_asof(segment, payload, end=end))
    cache = {
        "schema_version": "finmind_segment_cache_v1",
        "segment": segment,
        "asof": end,
        "updated_at": utc_now(),
        "ok": bool(result.get("ok")),
        "covered": covered,
        "provider_error": provider_error,
        "cooldown_until": (datetime.now(timezone.utc) + timedelta(hours=cooldown_hours)).replace(microsecond=0).isoformat() if provider_error in {"provider_402_quota_or_payment_required", "provider_rate_limited"} else "",
        "stdout_path": rel_path(resolve_path(str(result.get("stdout_path") or ""))) if result.get("stdout_path") else "",
        "stderr_path": rel_path(resolve_path(str(result.get("stderr_path") or ""))) if result.get("stderr_path") else "",
        "returncode": result.get("returncode"),
    }
    cache_path = finmind_segment_cache_path(segment=segment, end=end)
    write_json(cache_path, cache)
    return cache


def load_finmind_segment_cache(*, segment: str, end: str) -> dict[str, Any]:
    return read_json(finmind_segment_cache_path(segment=segment, end=end))


def cache_result_for_segment(cache: dict[str, Any], *, job_dir: Path, segment: str) -> dict[str, Any]:
    origin_issue = finmind_segment_cache_origin_issue(cache)
    if origin_issue:
        raise ValueError(f"invalid FinMind segment cache origin for {segment}: {origin_issue}")
    stdout_src = resolve_path(str(cache.get("stdout_path") or ""))
    stderr_src = resolve_path(str(cache.get("stderr_path") or ""))
    stdout_dst = job_dir / f"finmind_{segment}_stdout.txt"
    stderr_dst = job_dir / f"finmind_{segment}_stderr.txt"
    if stdout_src.exists():
        stdout_dst.write_text(redact_secret_text(stdout_src.read_text(encoding="utf-8")), encoding="utf-8")
    else:
        stdout_dst.write_text("", encoding="utf-8")
    if stderr_src.exists():
        stderr_dst.write_text(redact_secret_text(stderr_src.read_text(encoding="utf-8")), encoding="utf-8")
    else:
        stderr_dst.write_text("", encoding="utf-8")
    provider_error = str(cache.get("provider_error") or "")
    return {
        "ok": bool(cache.get("ok") and cache.get("covered")),
        "returncode": 0 if cache.get("ok") and cache.get("covered") else 1,
        "cached": True,
        "provider_error": provider_error,
        "cooldown_until": str(cache.get("cooldown_until") or ""),
        "argv": ["cached_finmind_segment", segment],
        "cwd": str(ROOT),
        "stdout_path": str(stdout_dst),
        "stderr_path": str(stderr_dst),
        "stdout_tail": stdout_dst.read_text(encoding="utf-8")[-3000:],
        "stderr_tail": stderr_dst.read_text(encoding="utf-8")[-3000:],
    }


def should_reuse_finmind_segment_cache(cache: dict[str, Any], *, reuse_success: bool) -> bool:
    # The CLI switch is named --disable-finmind-segment-cache.  It must bypass
    # both successful-result reuse and provider-error cooldown reuse; otherwise
    # a manual recovery run still points at an older job's failed evidence.
    if not reuse_success:
        return False
    if not cache:
        return False
    if finmind_segment_cache_origin_issue(cache):
        return False
    if reuse_success and cache.get("ok") and cache.get("covered"):
        return True
    cooldown_until = str(cache.get("cooldown_until") or "")
    if not cooldown_until:
        return False
    try:
        return datetime.fromisoformat(cooldown_until) > datetime.now(timezone.utc)
    except ValueError:
        return False


def run_finmind_segmented_update(
    *,
    symbols_file: Path,
    job_dir: Path,
    start: str,
    end: str,
    timeout_seconds: int,
    skip_validate: bool,
    full_scope: bool,
    include_orthogonal_segments: bool = True,
    include_optional_segments: bool = True,
    reuse_success_cache: bool = True,
    cooldown_hours: float = 6.0,
    command_runner=run_cmd,
    acquisition_run_id: str = "",
    logical_state_path: Path | None = None,
) -> dict[str, Any]:
    job_dir.mkdir(parents=True, exist_ok=True)
    # Backend HSA8 capture uses this directory for same-run raw, normalized,
    # and adapter artifacts. Create it here so every segmented invocation has
    # the same path contract as the top-level runner.
    handoff_artifact_dir = job_dir / "same_run_handoff_artifacts"
    handoff_artifact_dir.mkdir(mode=0o750, exist_ok=True)
    symbols = [line.strip() for line in symbols_file.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    base_argv = [
        PYTHON,
        "backend/scripts/update_tw_stock_daily.py",
        "--symbols-file",
        str(symbols_file),
        "--start",
        start,
        "--end",
        end,
        "--apply",
    ]
    if acquisition_run_id:
        base_argv.extend(["--acquisition-run-id", acquisition_run_id])
    if skip_validate:
        base_argv.append("--no-validate")

    segment_skip_flags = {
        "daily_price": ["--no-corporate-actions", "--no-institutional", "--no-margin", "--no-monthly-revenue", "--no-valuation"],
        "corporate_actions": ["--no-daily-price", "--no-institutional", "--no-margin", "--no-monthly-revenue", "--no-valuation"],
        "institutional": ["--no-daily-price", "--no-corporate-actions", "--no-margin", "--no-monthly-revenue", "--no-valuation"],
        "margin": ["--no-daily-price", "--no-corporate-actions", "--no-institutional", "--no-monthly-revenue", "--no-valuation"],
        "monthly_revenue": ["--no-daily-price", "--no-corporate-actions", "--no-institutional", "--no-margin", "--no-valuation"],
        "valuation": ["--no-daily-price", "--no-corporate-actions", "--no-institutional", "--no-margin", "--no-monthly-revenue"],
    }
    if not full_scope:
        ordered_segments = ["daily_price"]
    else:
        # Required HSA8 families get the provider budget first. Optional
        # archives must never prevent a resumable required acquisition.
        ordered_segments = ["daily_price"]
        if include_orthogonal_segments:
            ordered_segments.extend(["institutional", "margin"])
        if include_optional_segments:
            ordered_segments.extend(["corporate_actions", "monthly_revenue", "valuation"])
    logical_state = None
    if logical_state_path is not None:
        logical_state = logical_acquisition.load_state(logical_state_path, target_asof=end, symbols=symbols)
        # A successful cache is not current logical-run evidence.  Only state
        # entries with an explicit capture reference may be resumed.
        completed = {
            name for name, item in (logical_state.get("segments") or {}).items()
            if isinstance(item, dict)
            and item.get("ok") is True
            and item.get("evidence_path")
            and isinstance(item.get("capture"), dict)
            and item["capture"].get("validator_status") == "PASS"
            and item["capture"].get("pit_status") == "PASS"
        }
        ordered_segments = [segment for segment in ordered_segments if segment not in completed]
    segment_results: dict[str, dict[str, Any]] = {}
    cache_events: dict[str, dict[str, Any]] = {}
    for segment in ordered_segments:
        cache = load_finmind_segment_cache(segment=segment, end=end)
        cache_origin_issue = finmind_segment_cache_origin_issue(cache) if cache else ""
        if logical_state is not None:
            # Cached stdout belongs to another job and cannot satisfy the
            # same-run lineage.  A failed cooldown may still be observed, but
            # no cached success is reused in logical recovery mode.
            reuse_cache = should_reuse_finmind_segment_cache(cache, reuse_success=False)
        else:
            reuse_cache = should_reuse_finmind_segment_cache(cache, reuse_success=reuse_success_cache)
        if reuse_cache:
            result = cache_result_for_segment(cache, job_dir=job_dir, segment=segment)
            cache_events[segment] = {"action": "reused", "cache": cache}
        else:
            segment_handoff_dir = handoff_artifact_dir / segment
            segment_handoff_dir.mkdir(mode=0o750, exist_ok=True)
            result = command_runner(
                [*base_argv, *segment_skip_flags[segment], "--handoff-output-dir", str(segment_handoff_dir)],
                cwd=ROOT,
                stdout_path=job_dir / f"finmind_{segment}_stdout.txt",
                stderr_path=job_dir / f"finmind_{segment}_stderr.txt",
                timeout=timeout_seconds,
            )
            action = "ignored_invalid_origin_then_refreshed" if cache_origin_issue else "refreshed"
            cache_events[segment] = {
                "action": action,
                "cache_origin_issue": cache_origin_issue,
                "cache": write_finmind_segment_cache(segment=segment, end=end, result=result, cooldown_hours=cooldown_hours),
            }
        segment_results[segment] = result
        if logical_state is not None:
            payload = parse_json_stdout(result)
            captures = payload.get("hsa8_capture") if isinstance(payload.get("hsa8_capture"), dict) else {}
            for captured_name, capture in captures.items():
                # Each backend invocation also observes TWII.  Only the
                # requested FinMind segment may update its logical slot;
                # otherwise a later segment could overwrite a valid TWII
                # capture with a duplicate or blocked observation.
                if captured_name != segment and not (captured_name == "twii" and segment == "daily_price"):
                    continue
                if not isinstance(capture, dict) or capture.get("status") != "captured":
                    continue
                evidence_path = str(capture.get("adapter_output_path") or "")
                evidence_sha = file_fingerprint(resolve_path(evidence_path)).get("sha256", "") if evidence_path and resolve_path(evidence_path).exists() else ""
                capture_ready = bool(
                    capture.get("validator_status") == "PASS"
                    and capture.get("pit_status") == "PASS"
                )
                item = {
                    # Process success only proves that bytes were captured.
                    # Logical completion requires the HSA8 source gates too.
                    "ok": bool(result.get("ok")) and bool(evidence_sha) and capture_ready,
                    "evidence_path": evidence_path,
                    "evidence_sha256": evidence_sha,
                    "capture": capture,
                }
                logical_state = logical_acquisition.record_segment(
                    logical_state,
                    segment=captured_name,
                    job_id=str(result.get("job_id") or f"{acquisition_run_id}:{segment}:{job_dir.name}"),
                    evidence=item,
                )
            logical_acquisition.write_state(logical_state_path, logical_state)

    merged_payload = merge_finmind_segment_payloads(segment_results, symbols=symbols, start=start, end=end)
    if logical_state is not None:
        merged_payload["logical_acquisition"] = {
            "logical_run_id": logical_state["logical_run_id"],
            "state_path": rel_path(logical_state_path),
            "status": logical_state.get("status"),
            "handoff_allowed": bool(logical_state.get("handoff_allowed")),
        }
        merged_payload["hsa8_capture"] = {
            name: item["capture"]
            for name, item in (logical_state.get("segments") or {}).items()
            if isinstance(item, dict) and isinstance(item.get("capture"), dict)
        }
    merged_payload["quota_control"] = {
        "schema_version": "finmind_quota_scope_control_v1",
        "reuse_success_cache": bool(reuse_success_cache),
        "cooldown_hours": float(cooldown_hours),
        "cache_events": cache_events,
    }
    merged_stdout = job_dir / "finmind_stdout.txt"
    merged_stdout.write_text(json.dumps(merged_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    merged_stderr = job_dir / "finmind_stderr.txt"
    merged_stderr.write_text(
        "\n\n".join(
            f"===== {segment} stderr =====\n{Path(str(result.get('stderr_path'))).read_text(encoding='utf-8') if result.get('stderr_path') and Path(str(result.get('stderr_path'))).exists() else ''}"
            for segment, result in segment_results.items()
        ),
        encoding="utf-8",
    )
    return {
        "ok": all(bool(result.get("ok")) for result in segment_results.values()),
        "returncode": 0 if all(bool(result.get("ok")) for result in segment_results.values()) else 1,
        "segmented": True,
        "quota_scope_control": merged_payload["quota_control"],
        "segment_results": segment_results,
        "hsa8_capture": merged_payload.get("hsa8_capture", {}),
        "logical_acquisition": merged_payload.get("logical_acquisition", {}),
        "argv": [*base_argv, "--segmented-by-daily-auto"],
        "cwd": str(ROOT),
        "stdout_path": str(merged_stdout),
        "stderr_path": str(merged_stderr),
        "stdout_tail": merged_stdout.read_text(encoding="utf-8")[-3000:],
        "stderr_tail": merged_stderr.read_text(encoding="utf-8")[-3000:],
    }


def build_real_same_run_handoff(*, job: dict[str, Any], job_dir: Path, symbols: list[str]) -> dict[str, Any]:
    """Bridge only artifacts emitted by this acquisition run into HSA8 strict validation."""
    run_id = str(job.get("acquisition_logical_run_id") or job.get("job_id") or "")
    asof = str(job.get("asof") or "")
    artifact_root = job_dir / "same_run_handoff_artifacts"
    finmind = job.get("finmind_update") if isinstance(job.get("finmind_update"), dict) else {}
    segment_results = finmind.get("segment_results") if isinstance(finmind.get("segment_results"), dict) else {}
    capture = finmind.get("hsa8_capture") if isinstance(finmind.get("hsa8_capture"), dict) else {}
    family_segment = {
        "adjusted_price": "daily_price",
        "institutional_flow": "institutional",
        "margin_short": "margin",
    }

    def artifact_records(paths: list[Path], roles: list[str]) -> list[dict[str, Any]]:
        """Expose the same path/checksum contract consumed by MBCDS3."""
        records: list[dict[str, Any]] = []
        for path, role in zip(paths, roles, strict=False):
            fingerprint = file_fingerprint(path)
            records.append({
                "path": str(path),
                "role": role,
                "sha256": str(fingerprint.get("sha256") or ""),
            })
        return records

    sources: list[dict[str, Any]] = []
    for family, segment in family_segment.items():
        result = segment_results.get(segment) if isinstance(segment_results.get(segment), dict) else {}
        segment_capture = capture.get(segment) if isinstance(capture.get(segment), dict) else {}
        raw_paths = [resolve_path(str(item)) for item in segment_capture.get("raw_paths", []) if str(item).strip()]
        normalized_paths = [resolve_path(str(item)) for item in segment_capture.get("normalized_paths", []) if str(item).strip()]
        raw = raw_paths[0] if raw_paths else artifact_root / f"{segment}.raw.json"
        normalized = normalized_paths[0] if normalized_paths else artifact_root / f"{segment}.normalized.json"
        try:
            normalized_payload = json.loads(normalized.read_text(encoding="utf-8")) if normalized.exists() else {}
        except (OSError, json.JSONDecodeError):
            normalized_payload = {}
        # Adapter metadata is authoritative.  Do not normalize missing values or
        # infer status/scope from records; HSA8 must reject incomplete captures.
        expected = segment_capture.get("expected_scope")
        returned = segment_capture.get("returned_scope")
        absent = segment_capture.get("absent_scope")
        unknown = segment_capture.get("unknown_scope")
        fetched_at = segment_capture.get("fetched_at")
        sources.append({
            "source_family": family,
            "source_id": segment_capture.get("source_id"),
            "acquisition_run_id": run_id,
            "target_asof": asof,
            "provider": segment_capture.get("provider"),
            "source_endpoint_version": segment_capture.get("endpoint_version"),
            "parser_version": segment_capture.get("parser_version"),
            "schema_version": segment_capture.get("schema_version"),
            "request_parameters": segment_capture.get("request_parameters"),
            "http_status": segment_capture.get("http_status"),
            "transport_identity": segment_capture.get("transport_identity"),
            "source_published_at": segment_capture.get("source_published_at"),
            "available_at": segment_capture.get("available_at"),
            "fetched_at": fetched_at,
            "pit_status": segment_capture.get("pit_status"),
            "trade_date": segment_capture.get("trade_date"),
            "source_validator_status": segment_capture.get("validator_status"),
            "adapter_output_path": segment_capture.get("adapter_output_path"),
            "adapter_output_files": [str(resolve_path(str(segment_capture.get("adapter_output_path"))))] if segment_capture.get("adapter_output_path") else [],
            "expected_scope": expected,
            "returned_scope": returned,
            "absent_scope": absent,
            "unknown_scope": unknown,
            # HSA8 receives the adapter's canonical path lists here.  Roles
            # are added by the handoff builder; passing objects at this layer
            # makes the strict override comparison fail before PIT validation.
            "raw_files": [str(path) for path in raw_paths],
            "normalized_files": [str(path) for path in normalized_paths],
            "artifacts": artifact_records(
                [*raw_paths, *normalized_paths, *([resolve_path(str(segment_capture.get("adapter_output_path")))] if segment_capture.get("adapter_output_path") else [])],
                [*("provider_raw_response" for _ in raw_paths), *("provider_normalized_payload" for _ in normalized_paths), *( ["adapter_output"] if segment_capture.get("adapter_output_path") else [])],
            ),
        })
    # TWII is deliberately explicit: no calendar, cache, inventory, or stdout substitution.
    sources.append({
        "source_family": "twii",
        "source_id": (capture.get("twii", {}) or {}).get("source_id"),
        "acquisition_run_id": run_id,
        "target_asof": asof,
        "provider": (capture.get("twii", {}) or {}).get("provider"),
        "source_endpoint_version": (capture.get("twii", {}) or {}).get("endpoint_version"),
        "parser_version": (capture.get("twii", {}) or {}).get("parser_version"),
        "schema_version": (capture.get("twii", {}) or {}).get("schema_version"),
        "request_parameters": (capture.get("twii", {}) or {}).get("request_parameters"),
        "http_status": (capture.get("twii", {}) or {}).get("http_status"),
        "transport_identity": (capture.get("twii", {}) or {}).get("transport_identity"),
        "source_published_at": (capture.get("twii", {}) or {}).get("source_published_at"),
        "available_at": (capture.get("twii", {}) or {}).get("available_at"),
        "fetched_at": (capture.get("twii", {}) or {}).get("fetched_at"),
        "pit_status": (capture.get("twii", {}) or {}).get("pit_status"),
        "trade_date": (capture.get("twii", {}) or {}).get("trade_date"),
        "source_validator_status": (capture.get("twii", {}) or {}).get("validator_status"),
        "expected_scope": (capture.get("twii", {}) or {}).get("expected_scope"),
        "returned_scope": (capture.get("twii", {}) or {}).get("returned_scope"),
        "absent_scope": (capture.get("twii", {}) or {}).get("absent_scope"),
        "unknown_scope": (capture.get("twii", {}) or {}).get("unknown_scope"),
        "adapter_output_path": (capture.get("twii", {}) or {}).get("adapter_output_path"),
        "adapter_output_files": [str(resolve_path(str((capture.get("twii", {}) or {}).get("adapter_output_path"))))] if (capture.get("twii", {}) or {}).get("adapter_output_path") else [],
        "raw_files": [str(resolve_path(str(item))) for item in (capture.get("twii", {}) or {}).get("raw_paths", [])],
        "normalized_files": [str(resolve_path(str(item))) for item in (capture.get("twii", {}) or {}).get("normalized_paths", [])],
        "artifacts": artifact_records(
            [*([resolve_path(str(item)) for item in (capture.get("twii", {}) or {}).get("raw_paths", [])]),
             *([resolve_path(str(item)) for item in (capture.get("twii", {}) or {}).get("normalized_paths", [])]),
             *([resolve_path(str((capture.get("twii", {}) or {}).get("adapter_output_path")))] if (capture.get("twii", {}) or {}).get("adapter_output_path") else [])],
            [*("provider_raw_response" for _ in (capture.get("twii", {}) or {}).get("raw_paths", [])), *("provider_normalized_payload" for _ in (capture.get("twii", {}) or {}).get("normalized_paths", [])), *( ["adapter_output"] if (capture.get("twii", {}) or {}).get("adapter_output_path") else [])],
        ),
    })
    report = {"ok": False, "status": "STOP", "reason": "handoff_not_built", "job_id": run_id, "target_asof": asof, "sources": sources}
    try:
        # A resumable logical run may span several daily job directories.  All
        # evidence remains beneath the daily-auto ops root and is still bound
        # by exact SHA256/lineage checks in HSA8; use that common containment
        # root only for logical-run handoffs, never for ordinary jobs.
        validation_root = OPS_ROOT if job.get("acquisition_logical_run_id") else job_dir
        manifest = hsa8.build_runtime_handoff(validation_root, run_id, asof, sources, job_dir / "same_run_handoff")
        report.update({"ok": True, "status": "PASS", "manifest_path": rel_path(manifest)})
    except Exception as exc:
        report.update({"error": f"{type(exc).__name__}:{exc}"})
    write_json(job_dir / "same_run_handoff_validation.json", report)
    return report


def latest_asof() -> str:
    latest = read_json(LATEST)
    if latest.get("status") == "accepted":
        return str(latest.get("asof") or "")
    return ""


def write_readonly_snapshot_latest_pointer(manifest_path: Path, *, out_root: Path = READONLY_SNAPSHOT_ROOT) -> Path:
    manifest = read_json(manifest_path)
    latest_path = out_root / "latest.json"
    write_json(
        latest_path,
        {
            "artifact_type": "readonly_strategy_snapshot_latest_pointer",
            "schema_version": "readonly_strategy_snapshot_latest_r13_v1",
            "asof": str(manifest.get("asof") or ""),
            "readonly_only": True,
            "production_trade_enabled": False,
            "snapshot_manifest": rel_path(manifest_path),
            "created_at": utc_now(),
            "created_by": "scripts/run_daily_tw_stock_auto_update.py",
            "not_provider_accepted_latest": True,
            "not_trade_target_latest": True,
        },
    )
    return latest_path


def run_readonly_strategy_snapshot_publish(
    *,
    asof: str,
    job_dir: Path,
    enabled: bool | None = None,
    dry_run: bool | None = None,
    out_root: Path = READONLY_SNAPSHOT_ROOT,
    timeout_seconds: int | None = None,
    command_runner=run_cmd,
) -> dict[str, Any]:
    enabled = env_flag("ENABLE_TW_READONLY_STRATEGY_SNAPSHOT_PUBLISH", False) if enabled is None else enabled
    dry_run = env_flag("TW_READONLY_STRATEGY_SNAPSHOT_DRY_RUN", True) if dry_run is None else dry_run
    result: dict[str, Any] = {
        "enabled": bool(enabled),
        "attempted": False,
        "ok": True,
        "dry_run": bool(dry_run),
        "manifest": "",
        "latest_updated": False,
        "validator_ok": False,
        "error": "",
    }
    if not enabled:
        return result

    result["attempted"] = True
    timeout = int(timeout_seconds or os.getenv("TW_READONLY_STRATEGY_SNAPSHOT_TIMEOUT_SECONDS", str(READONLY_DEFAULT_TIMEOUT_SECONDS)))
    publish_stdout = job_dir / "readonly_snapshot_publish_stdout.txt"
    publish_stderr = job_dir / "readonly_snapshot_publish_stderr.txt"
    publish_argv = [
        PYTHON,
        str(READONLY_PUBLISH_SCRIPT.relative_to(ROOT)),
        "--out-root",
        str(out_root),
        "--no-latest",
        "--json",
    ]
    publish_result = command_runner(
        publish_argv,
        cwd=ROOT,
        stdout_path=publish_stdout,
        stderr_path=publish_stderr,
        timeout=timeout,
    )
    result["publish"] = publish_result
    publish_payload = parse_json_stdout(publish_result)
    result["publish_payload"] = publish_payload
    manifest = str(publish_payload.get("manifest") or "")
    result["manifest"] = manifest
    if not publish_result.get("ok") or not publish_payload.get("ok") or not manifest:
        result.update({"ok": False, "error": "readonly snapshot writer failed"})
        return result

    validate_stdout = job_dir / "readonly_snapshot_validate_stdout.txt"
    validate_stderr = job_dir / "readonly_snapshot_validate_stderr.txt"
    validate_argv = [
        PYTHON,
        str(READONLY_VALIDATE_SCRIPT.relative_to(ROOT)),
        "--manifest",
        manifest,
        "--json",
    ]
    validate_result = command_runner(
        validate_argv,
        cwd=ROOT,
        stdout_path=validate_stdout,
        stderr_path=validate_stderr,
        timeout=timeout,
    )
    validate_payload = parse_json_stdout(validate_result)
    result["validator"] = validate_result
    result["validator_payload"] = validate_payload
    result["validator_ok"] = bool(validate_result.get("ok") and validate_payload.get("ok"))
    if not result["validator_ok"]:
        result.update({"ok": False, "error": "readonly snapshot validator failed"})
        return result

    if dry_run:
        return result

    latest_path = write_readonly_snapshot_latest_pointer(resolve_path(manifest), out_root=out_root)
    result["latest"] = rel_path(latest_path)
    result["latest_updated"] = True
    latest_stdout = job_dir / "readonly_snapshot_latest_validate_stdout.txt"
    latest_stderr = job_dir / "readonly_snapshot_latest_validate_stderr.txt"
    latest_validate_result = command_runner(
        [PYTHON, str(READONLY_VALIDATE_SCRIPT.relative_to(ROOT)), "--latest", "--json"],
        cwd=ROOT,
        stdout_path=latest_stdout,
        stderr_path=latest_stderr,
        timeout=timeout,
    )
    result["latest_validator"] = latest_validate_result
    result["latest_validator_payload"] = parse_json_stdout(latest_validate_result)
    if not latest_validate_result.get("ok"):
        result.update({"ok": False, "error": "readonly snapshot latest pointer validation failed"})
    return result


def run_strict_e4_readonly_chain(
    *,
    asof: str,
    job_dir: Path,
    enabled: bool | None = None,
    readonly_price_bridge_dir: str = "",
    readonly_twii_bridge: str = "",
    timeout_seconds: int | None = None,
    command_runner=run_cmd,
) -> dict[str, Any]:
    enabled = env_flag("TW_DAILY_AUTO_ENABLE_STRICT_E4_READONLY_CHAIN", False) if enabled is None else enabled
    price_bridge = readonly_price_bridge_dir.strip()
    twii_bridge = readonly_twii_bridge.strip()
    result: dict[str, Any] = {
        "enabled": bool(enabled),
        "attempted": False,
        "ok": True,
        "status": "disabled",
        "orthogonal_source_required": True,
        "model_a_manifest": rel_path(STRICT_E4_SIGNAL_ROOT / asof / "model_a/manifest.json"),
        "model_b_manifest": "",
        "yz2_build_triggered": False,
        "yz2r_build_triggered": False,
        "model_b_yz2_validator_ok": False,
        "readonly_price_bridge_dir": price_bridge if enabled else "",
        "readonly_twii_bridge": twii_bridge if enabled else "",
        "readonly_price_bridge_used_by_yz2": False,
        "readonly_twii_bridge_used_by_yz2": False,
        "readonly_price_bridge_used_by_yz2r": False,
        "formal_normalized_nonempty_used_for_price_or_twii": bool(enabled and not (price_bridge and twii_bridge)),
        "readonly_snapshot_latest_updated": False,
        "provider_publish_triggered": False,
        "accepted_latest_switch_triggered": False,
        "qlib_accepted_latest_switch_triggered": False,
        "error": "",
    }
    if not enabled:
        return result

    result["attempted"] = True
    result["status"] = "running"
    timeout = int(timeout_seconds or os.getenv("TW_DAILY_AUTO_STRICT_E4_TIMEOUT_SECONDS", str(STRICT_E4_DEFAULT_TIMEOUT_SECONDS)))
    if bool(price_bridge) != bool(twii_bridge):
        result.update({
            "ok": False,
            "status": "blocked_incomplete_readonly_bridge",
            "error": "strict E4 readonly bridge contract requires both price bridge dir and TWII bridge file, or neither",
        })
        return result
    model_a_manifest = STRICT_E4_SIGNAL_ROOT / asof / "model_a/manifest.json"
    if not model_a_manifest.exists():
        result.update({
            "ok": False,
            "status": "blocked_missing_model_a",
            "error": "strict E4 chain requires pre-existing YZ1 model_a signal for the asof; daily auto does not synthesize qlib base signals in this readonly gate",
        })
        return result
    if price_bridge and not resolve_path(price_bridge).is_dir():
        result.update({
            "ok": False,
            "status": "blocked_missing_readonly_price_bridge",
            "error": f"strict E4 readonly price bridge dir does not exist: {price_bridge}",
        })
        return result
    if twii_bridge and not resolve_path(twii_bridge).is_file():
        result.update({
            "ok": False,
            "status": "blocked_missing_readonly_twii_bridge",
            "error": f"strict E4 readonly TWII bridge file does not exist: {twii_bridge}",
        })
        return result

    yz2_stdout = job_dir / "strict_e4_yz2_stdout.txt"
    yz2_stderr = job_dir / "strict_e4_yz2_stderr.txt"
    yz2_argv = [
        PYTHON,
        str(STRICT_E4_YZ2_BUILD_SCRIPT.relative_to(ROOT)),
        "--signal-asof",
        asof,
        "--json",
    ]
    if price_bridge:
        yz2_argv.extend(["--readonly-price-bridge-dir", price_bridge])
    if twii_bridge:
        yz2_argv.extend(["--readonly-twii-bridge", twii_bridge])
    yz2_result = command_runner(
        yz2_argv,
        cwd=ROOT,
        stdout_path=yz2_stdout,
        stderr_path=yz2_stderr,
        timeout=timeout,
    )
    yz2_payload = parse_json_stdout(yz2_result)
    result["yz2_build_triggered"] = True
    result["yz2_build"] = yz2_result
    result["yz2_payload"] = yz2_payload
    result["readonly_price_bridge_used_by_yz2"] = bool(yz2_payload.get("readonly_price_bridge_used"))
    result["readonly_twii_bridge_used_by_yz2"] = bool(yz2_payload.get("readonly_twii_bridge_used"))
    model_b_manifest = str(yz2_payload.get("model_b_manifest") or rel_path(STRICT_E4_SIGNAL_ROOT / asof / STRICT_E4_MODEL_B_SUBDIR / "manifest.json"))
    result["model_b_manifest"] = model_b_manifest
    if not yz2_result.get("ok") or not yz2_payload.get("ok"):
        result.update({"ok": False, "status": "yz2_build_failed", "error": "strict E4 YZ2 orthogonal package/model_b build failed"})
        return result

    yz2r_stdout = job_dir / "strict_e4_yz2r_stdout.txt"
    yz2r_stderr = job_dir / "strict_e4_yz2r_stderr.txt"
    yz2r_argv = [
        PYTHON,
        str(STRICT_E4_YZ2R_BUILD_SCRIPT.relative_to(ROOT)),
        "--signal-asof",
        asof,
        "--json",
    ]
    if price_bridge:
        yz2r_argv.extend(["--readonly-price-bridge-dir", price_bridge])
    yz2r_result = command_runner(
        yz2r_argv,
        cwd=ROOT,
        stdout_path=yz2r_stdout,
        stderr_path=yz2r_stderr,
        timeout=timeout,
    )
    result["yz2r_build_triggered"] = True
    result["yz2r_build"] = yz2r_result
    result["yz2r_payload"] = parse_json_stdout(yz2r_result)
    result["readonly_price_bridge_used_by_yz2r"] = bool(result["yz2r_payload"].get("readonly_price_bridge_used"))
    result["formal_normalized_nonempty_used_for_price_or_twii"] = bool(
        result["yz2_payload"].get("formal_normalized_nonempty_used_for_price_or_twii")
        or result["yz2r_payload"].get("formal_normalized_nonempty_used_for_price")
    )
    if not yz2r_result.get("ok"):
        result.update({"ok": False, "status": "yz2r_build_failed", "error": "strict E4 YZ2R execution price readiness failed"})
        return result

    result["model_b_yz2_validator_ok"] = (STRICT_E4_SIGNAL_ROOT / asof / STRICT_E4_MODEL_B_SUBDIR / "manifest.json").exists()
    result["status"] = "passed" if result["model_b_yz2_validator_ok"] else "model_b_manifest_missing"
    result["ok"] = bool(result["model_b_yz2_validator_ok"])
    return result


def materialize_symbols(job_dir: Path) -> Path:
    symbols: list[str] = []
    if UNIVERSE.exists():
        for line in UNIVERSE.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            code = raw.removeprefix("TW").strip()
            if code and code not in symbols:
                symbols.append(code)
    if not symbols:
        symbols = ["2330", "0050"]
    path = job_dir / "finmind_symbols.txt"
    path.write_text("\n".join(symbols) + "\n", encoding="utf-8")
    return path


def publish_accepted_latest(asof: str) -> dict[str, Any]:
    sys.path.insert(0, str(BACKEND))
    os.environ.setdefault("ENABLE_TW_QLIB_OPTION_C_SCHEDULER", "true")
    os.environ.setdefault("TW_QLIB_OPTION_C_SCHEDULER_MODE", "dry-run-only")
    os.environ.setdefault("ENABLE_TW_QLIB_OPTION_C_NORMAL_PUBLISH", "true")
    os.environ.setdefault("TW_QLIB_OPTION_C_NORMAL_PUBLISH_MODE", "accepted-latest-publish-review")
    os.environ.setdefault("ENABLE_TW_QLIB_OPTION_C_ACCEPTED_LATEST_SCHEDULER", "true")
    os.environ.setdefault("TW_QLIB_OPTION_C_ACCEPTED_LATEST_SCHEDULER_MODE", "accepted-latest-scheduler-review")
    os.environ.setdefault("TW_OPTION_C_OPS_ROOT", str(ROOT / "data_tw/ops/option_c_jobs"))
    os.environ.setdefault("QLIB_TW_OPTION_C_CWD", str(QLIB))
    os.environ.setdefault("TW_QLIB_OPTION_C_CWD", str(QLIB))
    os.environ.setdefault("QLIB_TW_OPTION_C_ROOT", str(QLIB / "data_tw/experiments/option_c_daily_signal"))
    os.environ.setdefault("QLIB_TW_OPTION_C_LATEST_SIGNAL", str(LATEST))
    os.environ.setdefault("TW_QLIB_OPTION_C_LATEST_SIGNAL", str(LATEST))
    os.environ.setdefault("TW_QLIB_OPTION_C_PROVIDER_CALENDAR", str(CALENDAR))
    os.environ.setdefault("TW_QLIB_OPTION_C_EXPECTED_UNIVERSE", str(UNIVERSE))
    os.environ.setdefault("TW_QLIB_OPTION_C_PYTHON", PYTHON)

    from app.services.tw_stock_qlib_option_c_accepted_latest_scheduler import (  # noqa: WPS433
        OptionCAcceptedLatestSchedulerConfig,
        QlibOptionCAcceptedLatestScheduler,
    )
    from app.services.tw_stock_qlib_option_c_normal_publish import (  # noqa: WPS433
        OptionCNormalPublishConfig,
        QlibOptionCNormalPublishGate,
    )
    from app.services.tw_stock_qlib_option_c_scheduler import (  # noqa: WPS433
        OptionCSchedulerConfig,
        QlibOptionCDryRunScheduler,
    )

    scheduler = QlibOptionCAcceptedLatestScheduler(
        config=OptionCAcceptedLatestSchedulerConfig.from_env(),
        dry_run_scheduler=QlibOptionCDryRunScheduler(config=OptionCSchedulerConfig.from_env()),
        normal_publish_gate=QlibOptionCNormalPublishGate(config=OptionCNormalPublishConfig.from_env()),
    )
    return scheduler.tick({"asof": asof, "confirm_accepted_latest_scheduler": True})


def main() -> int:
    parser = argparse.ArgumentParser(description="Run unattended daily TW stock FinMind + Yahoo/Scrapling + qlib update.")
    parser.add_argument("--asof", default="", help="YYYY-MM-DD. Default: Asia/Taipei today.")
    parser.add_argument("--force", action="store_true", help="Run even when latest_signal already has target asof.")
    parser.add_argument("--skip-finmind", action="store_true")
    parser.add_argument("--skip-qlib", action="store_true")
    parser.add_argument(
        "--enable-legacy-provider-publish",
        action="store_true",
        default=env_flag("TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH", False),
        help="Explicit non-default legacy gate for Yahoo/Scrapling refresh, provider publish, and accepted latest switching.",
    )
    parser.add_argument("--finmind-scope", choices=["full", "daily"], default=os.getenv("TW_DAILY_AUTO_FINMIND_SCOPE", "full"))
    parser.add_argument(
        "--enable-strict-e4-readonly-chain",
        action="store_true",
        default=env_flag("TW_DAILY_AUTO_ENABLE_STRICT_E4_READONLY_CHAIN", False),
        help="Explicit non-default readonly gate to build strict E4 orthogonal YZ2/YZ2R artifacts when YZ1 model_a already exists.",
    )
    parser.add_argument(
        "--strict-e4-readonly-price-bridge-dir",
        default=os.getenv("TW_DAILY_AUTO_STRICT_E4_READONLY_PRICE_BRIDGE_DIR", ""),
        help="Explicit readonly stock price bridge dir for strict E4 chain. Default empty keeps existing strict E4 source behavior.",
    )
    parser.add_argument(
        "--strict-e4-readonly-twii-bridge",
        default=os.getenv("TW_DAILY_AUTO_STRICT_E4_READONLY_TWII_BRIDGE", ""),
        help="Explicit readonly TWII bridge CSV for strict E4 chain. Default empty keeps existing strict E4 source behavior.",
    )
    parser.add_argument("--finmind-lookback-days", type=int, default=int(os.getenv("TW_DAILY_AUTO_FINMIND_LOOKBACK_DAYS", "260")), help="FinMind TaiwanStockPrice archive lookback. Default 260d to keep qlib Top30/50 trend samples above 120 daily bars.")
    parser.add_argument("--finmind-orthogonal-batch-size", type=int, default=int(os.getenv("TW_DAILY_AUTO_FINMIND_ORTHOGONAL_BATCH_SIZE", "5")), help="Quota-aware institutional/margin symbols per daily auto run.")
    parser.add_argument("--finmind-orthogonal-lookback-days", type=int, default=int(os.getenv("TW_DAILY_AUTO_FINMIND_ORTHOGONAL_LOOKBACK_DAYS", "7")), help="Short incremental institutional/margin lookback for quota-aware orthogonal batch.")
    parser.add_argument("--disable-finmind-orthogonal-batch", action="store_true", default=os.getenv("TW_DAILY_AUTO_DISABLE_FINMIND_ORTHOGONAL_BATCH", "false").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--finmind-logical-required-only", action="store_true", help="Logical recovery: request required segments only; do not fetch optional archives.")
    parser.add_argument("--skip-finmind-validate", action="store_true", default=os.getenv("TW_DAILY_AUTO_SKIP_FINMIND_VALIDATE", "true").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--disable-finmind-segment-cache", action="store_true", default=os.getenv("TW_DAILY_AUTO_DISABLE_FINMIND_SEGMENT_CACHE", "false").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--finmind-provider-error-cooldown-hours", type=float, default=float(os.getenv("TW_DAILY_AUTO_FINMIND_PROVIDER_ERROR_COOLDOWN_HOURS", "6")))
    parser.add_argument("--refresh-timeout", type=float, default=float(os.getenv("TW_DAILY_AUTO_YAHOO_TIMEOUT", "30")))
    parser.add_argument("--refresh-retries", type=int, default=int(os.getenv("TW_DAILY_AUTO_YAHOO_RETRIES", "1")))
    parser.add_argument("--refresh-sleep-seconds", type=float, default=float(os.getenv("TW_DAILY_AUTO_YAHOO_SLEEP_SECONDS", "0.5")))
    parser.add_argument("--max-workers", type=int, default=int(os.getenv("TW_DAILY_AUTO_MAX_WORKERS", "4")))
    parser.add_argument("--proxy", default=os.getenv("TW_DAILY_AUTO_YAHOO_PROXY", ""))
    parser.add_argument("--timeout-seconds", type=int, default=int(os.getenv("TW_DAILY_AUTO_TIMEOUT_SECONDS", "1200")))
    parser.add_argument(
        "--enable-data-catalog-dashboard",
        action="store_true",
        default=env_flag("TW_DAILY_AUTO_ENABLE_DATA_CATALOG_DASHBOARD", False),
        help="Build and validate the DNG6 catalog/readiness dashboard as a static finalize-step observation.",
    )
    parser.add_argument(
        "--disable-research-data-history",
        action="store_true",
        default=env_flag("TW_DAILY_AUTO_DISABLE_RESEARCH_DATA_HISTORY", False),
        help="Incident-isolation switch for the default-on, non-blocking research history finalize step.",
    )
    parser.add_argument(
        "--enable-workflow-readonly-shadow",
        action="store_true",
        default=env_flag("TW_DAILY_AUTO_ENABLE_WORKFLOW_READONLY_SHADOW", False),
        help="Explicit non-default WF-3 gate for the readonly replay-window observation DAG.",
    )
    parser.add_argument(
        "--enable-workflow-model-a-signal-shadow",
        action="store_true",
        default=env_flag(
            "TW_DAILY_AUTO_ENABLE_WORKFLOW_MODELA_SIGNAL_SHADOW", False
        ),
        help="Explicit non-default WF-4A gate for readonly Model A input/signal observation.",
    )
    parser.add_argument(
        "--enable-workflow-readonly-snapshot-shadow",
        action="store_true",
        default=env_flag(
            "TW_DAILY_AUTO_ENABLE_WORKFLOW_READONLY_SNAPSHOT_SHADOW", False
        ),
        help="Explicit non-default WF-4B gate for readonly Model A product snapshot observation.",
    )
    parser.add_argument(
        "--enable-model-signal-gate",
        action="store_true",
        default=env_flag("TW_DAILY_AUTO_ENABLE_MODEL_SIGNAL_GATE", False),
        help="Explicit non-default DNG9 gate for readonly Model A score and Model B blocker pipelines.",
    )
    parser.add_argument(
        "--enable-mbcds3-daily-shadow",
        action="store_true",
        default=env_flag("ENABLE_TW_MBCDS3_DAILY_SHADOW", False),
        help="Explicit non-default MBCDS3 isolated daily append gate; never changes production/latest.",
    )
    parser.add_argument(
        "--enable-b19r2r-shadow",
        action="store_true",
        default=env_flag("TW_DAILY_AUTO_ENABLE_B19R2R_SHADOW", False),
        help="Explicit non-default B19R2R research shadow gate; failures never block the daily mainline.",
    )
    parser.add_argument(
        "--mbcds3-daily-shadow-inventory",
        default=os.getenv("TW_MBCDS3_DAILY_SHADOW_INVENTORY", ""),
        help="Optional isolated same-run compatibility inventory; default is <job_dir>/mbcds3_compatibility_inventory.csv.",
    )
    parser.add_argument(
        "--mbcds3-daily-shadow-accumulator-dir",
        default=os.getenv("TW_MBCDS3_DAILY_SHADOW_ACCUMULATOR_DIR", ""),
        help="Optional isolated accumulator directory under data_tw/experiments/model_b_compatibility_daily_shadow.",
    )
    parser.add_argument(
        "--enable-provider-candidate-refresh",
        action="store_true",
        default=env_flag("TW_DAILY_AUTO_ENABLE_PROVIDER_CANDIDATE_REFRESH", False),
        help="Explicit non-default DNG17 gate for isolated Yahoo/Scrapling staged provider candidate refresh. Does not publish formal providers or latest pointers.",
    )
    parser.add_argument(
        "--enable-fpala-formal-accepted-latest-automation",
        action="store_true",
        default=env_flag("ENABLE_TW_FPALA_FORMAL_ACCEPTED_LATEST_AUTOMATION", False),
        help="Explicit non-default FPALA gate for formal provider / qlib accepted latest no-publish decision evidence.",
    )
    parser.add_argument(
        "--fpala-no-publish",
        dest="fpala_no_publish",
        action="store_true",
        default=env_flag("TW_FPALA_NO_PUBLISH", True),
        help="Keep FPALA daily-auto gate in no-publish mode. Default true.",
    )
    parser.add_argument(
        "--disable-fpala-no-publish",
        dest="fpala_no_publish",
        action="store_false",
        help="Blocked in FPALA4; actual formal provider / accepted latest writes require a later exact authorization route.",
    )
    parser.add_argument(
        "--fpala-allow-formal-provider-publish",
        action="store_true",
        default=env_flag("TW_FPALA_ALLOW_FORMAL_PROVIDER_PUBLISH", False),
        help="Recorded as FPALA preflight intent only; FPALA4 performs no formal provider writes.",
    )
    parser.add_argument(
        "--fpala-allow-accepted-latest-switch",
        action="store_true",
        default=env_flag("TW_FPALA_ALLOW_ACCEPTED_LATEST_SWITCH", False),
        help="Recorded as FPALA preflight intent only; FPALA4 performs no accepted latest switch.",
    )
    parser.add_argument(
        "--fpala-exact-authorization-id",
        default=os.getenv("TW_FPALA_EXACT_AUTHORIZATION_ID", ""),
        help="FPALA authorization marker for future exact routes. FPALA4 records it but still performs no writes.",
    )
    parser.add_argument(
        "--enable-qald-accepted-latest-candidate-builder",
        action="store_true",
        default=env_flag("ENABLE_TW_QALD_ACCEPTED_LATEST_CANDIDATE_BUILDER", False),
        help="Explicit non-default QALD gate for qlib accepted-latest candidate generation. Writes no latest pointer.",
    )
    parser.add_argument(
        "--qald-accepted-latest-candidate-no-pointer",
        dest="qald_accepted_latest_candidate_no_pointer",
        action="store_true",
        default=env_flag("TW_QALD_ACCEPTED_LATEST_CANDIDATE_NO_POINTER", True),
        help="Keep QALD accepted-latest candidate gate in no-pointer mode. Default true.",
    )
    parser.add_argument(
        "--disable-qald-accepted-latest-candidate-no-pointer",
        dest="qald_accepted_latest_candidate_no_pointer",
        action="store_false",
        help="Blocked in QALD2R; accepted latest pointer writes require a later exact route.",
    )
    parser.add_argument(
        "--qald-accepted-latest-candidate-allow-pointer-write",
        action="store_true",
        default=env_flag("TW_QALD_ACCEPTED_LATEST_CANDIDATE_ALLOW_POINTER_WRITE", False),
        help="Blocked in QALD2R; recorded as forbidden control evidence only.",
    )
    parser.add_argument(
        "--qald-accepted-latest-candidate-exact-authorization-id",
        default=os.getenv("TW_QALD_ACCEPTED_LATEST_CANDIDATE_EXACT_AUTHORIZATION_ID", ""),
        help="QALD authorization marker for future exact routes. QALD2R records it but performs no pointer writes.",
    )
    parser.add_argument(
        "--qald-accepted-latest-candidate-target-asof",
        default=os.getenv("TW_QALD_ACCEPTED_LATEST_CANDIDATE_TARGET_ASOF", ""),
        help="Optional QALD target-asof override. Cron path normally uses the daily-auto runtime asof.",
    )
    parser.add_argument(
        "--qald-accepted-latest-candidate-source-root",
        default=os.getenv("TW_QALD_ACCEPTED_LATEST_CANDIDATE_SOURCE_ROOT", ""),
        help="Optional QALD source candidate root override. Cron path normally uses validated provider candidate evidence.",
    )
    parser.add_argument(
        "--enable-ador-no-publish-orchestration-dry-run",
        action="store_true",
        default=env_flag("ENABLE_TW_ADOR_NO_PUBLISH_ORCHESTRATION_DRY_RUN", False),
        help="Explicit non-default ADOR2 gate. Writes no-publish orchestration dry-run evidence only.",
    )
    parser.add_argument(
        "--ador-no-publish-orchestration-dry-run",
        dest="ador_no_publish_orchestration_dry_run",
        action="store_true",
        default=env_flag("TW_ADOR_NO_PUBLISH_ORCHESTRATION_DRY_RUN", True),
        help="Keep ADOR2 no-publish orchestration in dry-run mode. Default true.",
    )
    parser.add_argument(
        "--disable-ador-no-publish-orchestration-dry-run",
        dest="ador_no_publish_orchestration_dry_run",
        action="store_false",
        help="Record a blocked ADOR2 control state; ADOR2 still performs no latest writes.",
    )
    parser.add_argument(
        "--enable-dapr18-controlled-latest-orchestration",
        action="store_true",
        default=env_flag("ENABLE_TW_DAPR18_CONTROLLED_LATEST_ORCHESTRATION", False),
        help="Explicit non-default DAPR18 gate. Writes controlled latest dry-run evidence only by default.",
    )
    parser.add_argument(
        "--dapr18-controlled-latest-dry-run",
        dest="dapr18_controlled_latest_dry_run",
        action="store_true",
        default=env_flag("TW_DAPR18_CONTROLLED_LATEST_DRY_RUN", True),
        help="Keep DAPR18 controlled latest orchestration in dry-run mode. Default true.",
    )
    parser.add_argument(
        "--disable-dapr18-controlled-latest-dry-run",
        dest="dapr18_controlled_latest_dry_run",
        action="store_false",
        help="Record a blocked DAPR18 control state; DAPR18C still performs no latest writes.",
    )
    parser.add_argument(
        "--dapr18-build-candidates",
        action="store_true",
        default=env_flag("TW_DAPR18_BUILD_CANDIDATES", False),
        help="DAPR18 candidate planning flag. DAPR18C records plans only and writes no protected latest pointers.",
    )
    parser.add_argument(
        "--dapr18-publish-controlled-signal-latest",
        action="store_true",
        default=env_flag("TW_DAPR18_PUBLISH_CONTROLLED_SIGNAL_LATEST", False),
        help="Blocked in DAPR18C; actual writes require a later DAPR18F exact authorization phase.",
    )
    parser.add_argument(
        "--dapr18-publish-readonly-snapshot-latest",
        action="store_true",
        default=env_flag("TW_DAPR18_PUBLISH_READONLY_SNAPSHOT_LATEST", False),
        help="Blocked in DAPR18C; actual writes require a later DAPR18F exact authorization phase.",
    )
    parser.add_argument(
        "--dapr18-publish-agent-prompt-latest",
        action="store_true",
        default=env_flag("TW_DAPR18_PUBLISH_AGENT_PROMPT_LATEST", False),
        help="Blocked in DAPR18C; actual writes require a later DAPR18F exact authorization phase.",
    )
    parser.add_argument(
        "--dapr18-exact-authorization-id",
        default=os.getenv("TW_DAPR18_EXACT_AUTHORIZATION_ID", ""),
        help="DAPR18 authorization marker. DAPR18C records it as control evidence only and performs no latest writes.",
    )
    parser.add_argument(
        "--dng18-disable-provider-candidate-fallbacks",
        action="store_true",
        default=env_flag("TW_DAILY_AUTO_DNG18_DISABLE_PROVIDER_CANDIDATE_FALLBACKS", False),
        help="DNG18 probe-only switch: hide prior daily-auto and DNG15_R-A-R provider candidate fallbacks. Default false.",
    )
    parser.add_argument(
        "--dng18-disable-existing-isolated-modela-reuse",
        action="store_true",
        default=env_flag("TW_DAILY_AUTO_DNG18_DISABLE_EXISTING_ISOLATED_MODELA_REUSE", False),
        help="DNG18 probe-only switch: hide existing isolated Model A score reuse. Default false.",
    )
    parser.add_argument(
        "--dng9-model-signal-gate-dry-run-summary",
        action="store_true",
        help="Write the DNG9 model_signal_gate dry-run summary/catalog validation and exit before any daily provider update.",
    )
    parser.add_argument(
        "--today-earliest-time",
        default=os.getenv("TW_DAILY_AUTO_TODAY_EARLIEST_TIME", "18:00"),
        help="Earliest Asia/Taipei HH:MM time to pull same-day data when no pending asof exists.",
    )
    args = parser.parse_args()

    today_earliest_time = parse_hhmm(args.today_earliest_time)
    now_taipei = taipei_now()
    asof, asof_source, asof_resolution = resolve_asof_with_terminal_quarantine(args.asof, now_taipei=now_taipei)
    if args.dng9_model_signal_gate_dry_run_summary:
        summary = build_model_signal_gate_summary(
            asof=asof,
            gate_enabled=bool(args.enable_model_signal_gate),
            mode="dry_run_static_enabled" if args.enable_model_signal_gate else "dry_run_static_default",
            job_id="dng9_model_signal_gate_dry_run",
            model_b_result={"pipeline_status": "BLOCKED_INPUT_NOT_READY", "blocking_datasets": ["corporate_actions", "monthly_revenue", "valuation"]} if args.enable_model_signal_gate else None,
        )
        validation = write_model_signal_gate_summary(summary)
        payload = {"ok": validation.get("ok"), "summary": summary, "validation": validation}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if validation.get("ok") else 2

    latest_before = latest_asof()
    full_orthogonal_refresh_mode = should_run_full_orthogonal_refresh(
        latest_before=latest_before,
        asof=asof,
        force=bool(args.force),
        skip_finmind=bool(args.skip_finmind),
        finmind_scope=args.finmind_scope,
    )
    job_id = f"daily_tw_stock_auto_update_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    job_dir = OPS_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    job: dict[str, Any] = {
        "job_id": job_id,
        "status": "running",
        "asof": asof,
        "asof_source": asof_source,
        "asof_resolution": asof_resolution,
        "finmind_scope": args.finmind_scope,
        "started_at": utc_now(),
        "research_only": True,
        "trading": {"orders_enabled": False, "connects_to_broker": False, "research_signal_not_order": True},
        "latest_before": latest_before,
        "python_executable": PYTHON,
        "taipei_now": now_taipei.isoformat(),
        "today_earliest_time": today_earliest_time.strftime("%H:%M"),
        "finmind_update_triggered": False,
        "finmind_orthogonal_batch_update_triggered": False,
        "finmind_lookback_days": int(args.finmind_lookback_days),
        "finmind_orthogonal_batch_enabled": not bool(args.disable_finmind_orthogonal_batch),
        "finmind_orthogonal_batch_size": int(args.finmind_orthogonal_batch_size),
        "finmind_orthogonal_lookback_days": int(args.finmind_orthogonal_lookback_days),
        "finmind_history_goal": "cover option_c_accepted_150 with enough daily bars for 120-bar cross-analysis trend samples",
        "yahoo_refresh_triggered": False,
        "provider_publish_triggered": False,
        "latest_signal_updated": False,
        "m3_contract_mode": "legacy_provider_publish_enabled" if args.enable_legacy_provider_publish else "readonly_orchestrator_default",
        "legacy_provider_publish_enabled": bool(args.enable_legacy_provider_publish),
        "strict_e4_readonly_chain_enabled": bool(args.enable_strict_e4_readonly_chain),
        "strict_e4_readonly_price_bridge_enabled": bool(args.enable_strict_e4_readonly_chain and args.strict_e4_readonly_price_bridge_dir.strip()),
        "strict_e4_readonly_price_bridge_dir": args.strict_e4_readonly_price_bridge_dir.strip() if args.enable_strict_e4_readonly_chain else "",
        "strict_e4_readonly_twii_bridge": args.strict_e4_readonly_twii_bridge.strip() if args.enable_strict_e4_readonly_chain else "",
        "strict_e4_readonly_bridge_contract_triggered": False,
        "strict_e4_readonly_bridge_validator_ok": False,
        "strict_e4_readonly_bridge_warning": "",
        "orthogonal_source_refresh_required": bool(args.enable_strict_e4_readonly_chain),
        "orthogonal_source_refresh_triggered": False,
        "full_orthogonal_refresh_mode": full_orthogonal_refresh_mode,
        "full_orthogonal_refresh_required": full_orthogonal_refresh_mode,
        "full_orthogonal_refresh_triggered": False,
        "strict_e4_chain_triggered": False,
        "data_catalog_dashboard_enabled": bool(args.enable_data_catalog_dashboard),
        "data_catalog_dashboard_path": rel_path(DATA_CATALOG_DASHBOARD),
        "data_catalog_dashboard_validation_path": rel_path(DNG6_DATA_CATALOG_DASHBOARD_VALIDATION),
        "research_data_history_enabled": not bool(args.disable_research_data_history),
        "workflow_readonly_shadow_enabled": bool(args.enable_workflow_readonly_shadow),
        "workflow_readonly_shadow": {
            "schema_version": "daily.workflow_readonly_shadow.v1",
            "enabled": bool(args.enable_workflow_readonly_shadow),
            "attempted": False,
            "ok": not bool(args.enable_workflow_readonly_shadow),
            "status": (
                "NOT_ATTEMPTED"
                if args.enable_workflow_readonly_shadow
                else "DISABLED_BY_DEFAULT"
            ),
            "mainline_blocking": False,
            "production_allowed": False,
            "no_apply": True,
        },
        "workflow_model_a_signal_shadow_enabled": bool(
            args.enable_workflow_model_a_signal_shadow
        ),
        "workflow_model_a_signal_shadow": {
            "schema_version": "daily.workflow_model_a_signal_shadow.v1",
            "enabled": bool(args.enable_workflow_model_a_signal_shadow),
            "attempted": False,
            "ok": not bool(args.enable_workflow_model_a_signal_shadow),
            "status": (
                "NOT_ATTEMPTED"
                if args.enable_workflow_model_a_signal_shadow
                else "DISABLED_BY_DEFAULT"
            ),
            "mainline_blocking": False,
            "production_allowed": False,
            "no_apply": True,
        },
        "workflow_readonly_snapshot_shadow_enabled": bool(
            args.enable_workflow_readonly_snapshot_shadow
        ),
        "workflow_readonly_snapshot_shadow": {
            "schema_version": "daily.workflow_readonly_snapshot_shadow.v1",
            "enabled": bool(args.enable_workflow_readonly_snapshot_shadow),
            "attempted": False,
            "ok": not bool(args.enable_workflow_readonly_snapshot_shadow),
            "status": (
                "NOT_ATTEMPTED"
                if args.enable_workflow_readonly_snapshot_shadow
                else "DISABLED_BY_DEFAULT"
            ),
            "mainline_blocking": False,
            "production_allowed": False,
            "no_apply": True,
        },
        "model_signal_gate_enabled": bool(args.enable_model_signal_gate),
        "mbcds3_daily_shadow_enabled": bool(args.enable_mbcds3_daily_shadow),
        "mbcds3_daily_shadow_attempted": False,
        "mbcds3_daily_shadow_status": "DISABLED_BY_DEFAULT",
        "b19r2r_daily_shadow": {
            "enabled": bool(args.enable_b19r2r_shadow),
            "attempted": False,
            "ok": True,
            "shadow_ok": False,
            "status": "DISABLED_BY_DEFAULT" if not args.enable_b19r2r_shadow else "NOT_ATTEMPTED",
            "mainline_blocking": False,
            "production_allowed": False,
            "no_apply": True,
            "pending_asof_set": False,
        },
        "provider_candidate_refresh_gate_enabled": bool(args.enable_provider_candidate_refresh),
        "fpala_formal_accepted_latest_automation_enabled": bool(args.enable_fpala_formal_accepted_latest_automation),
        "fpala_no_publish": bool(args.fpala_no_publish),
        "fpala_allow_formal_provider_publish": bool(args.fpala_allow_formal_provider_publish),
        "fpala_allow_accepted_latest_switch": bool(args.fpala_allow_accepted_latest_switch),
        "fpala_exact_authorization_present": bool(args.fpala_exact_authorization_id.strip()),
        "qald_accepted_latest_candidate_builder_enabled": bool(args.enable_qald_accepted_latest_candidate_builder),
        "qald_accepted_latest_candidate_no_pointer": bool(args.qald_accepted_latest_candidate_no_pointer),
        "qald_accepted_latest_candidate_allow_pointer_write": bool(args.qald_accepted_latest_candidate_allow_pointer_write),
        "qald_accepted_latest_candidate_exact_authorization_present": bool(args.qald_accepted_latest_candidate_exact_authorization_id.strip()),
        "qald_accepted_latest_candidate_target_asof_override": args.qald_accepted_latest_candidate_target_asof.strip(),
        "qald_accepted_latest_candidate_source_root_override": args.qald_accepted_latest_candidate_source_root.strip(),
        "ador_no_publish_orchestration_gate_enabled": bool(args.enable_ador_no_publish_orchestration_dry_run),
        "ador_no_publish_orchestration_dry_run": bool(args.ador_no_publish_orchestration_dry_run),
        "dapr18_controlled_latest_orchestration_enabled": bool(args.enable_dapr18_controlled_latest_orchestration),
        "dapr18_controlled_latest_dry_run": bool(args.dapr18_controlled_latest_dry_run),
        "dapr18_build_candidates": bool(args.dapr18_build_candidates),
        "dapr18_publish_controlled_signal_latest": bool(args.dapr18_publish_controlled_signal_latest),
        "dapr18_publish_readonly_snapshot_latest": bool(args.dapr18_publish_readonly_snapshot_latest),
        "dapr18_publish_agent_prompt_latest": bool(args.dapr18_publish_agent_prompt_latest),
        "dapr18_exact_authorization_present": bool(args.dapr18_exact_authorization_id.strip()),
        "agent_daily_prompt_dry_run": env_flag("TW_AGENT_DAILY_PROMPT_DRY_RUN", True),
        "agent_daily_prompt_publish_enabled": env_flag("ENABLE_TW_AGENT_DAILY_PROMPT_PUBLISH", False),
        "agent_daily_prompt_publish_latest": env_flag("TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST", False),
        "dng18_disable_provider_candidate_fallbacks": bool(args.dng18_disable_provider_candidate_fallbacks),
        "dng18_disable_existing_isolated_modela_reuse": bool(args.dng18_disable_existing_isolated_modela_reuse),
        "provider_candidate_refresh_default_reachable": False,
        "model_signal_gate_default_reachable": False,
        "model_signal_gate_summary_path": rel_path(MODEL_SIGNAL_GATE_DRY_RUN_SUMMARY),
        "model_signal_gate_validation_path": rel_path(DNG9_MODEL_SIGNAL_GATE_VALIDATION),
        "model_a_score_job_triggered": False,
        "model_b_ltr_score_job_triggered": False,
        "legacy_provider_refresh_default_reachable": False,
        "legacy_provider_publish_default_reachable": False,
        "legacy_accepted_latest_default_reachable": False,
    }
    # Capture the real protected latest state before the legacy path runs so
    # its normalized observation-only terminal can be audited against the
    # six-stage adapter without changing the historical operator status.
    runtime_protected_before = protected_latest_fingerprints(
        readonly_latest_path=READONLY_SNAPSHOT_LATEST,
        agent_latest_path=AGENT_DAILY_PROMPT_LATEST,
        provider_latest_path=LATEST,
        legacy_latest_path=ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    )
    job["runtime_protected_before"] = runtime_protected_before
    if full_orthogonal_refresh_mode:
        job["full_orthogonal_protected_latest_before"] = full_orthogonal_protected_fingerprints()
    write_json(job_dir / "job.json", job)

    if job["latest_before"] == asof and not args.force and not full_orthogonal_refresh_mode:
        clear_pending_asof(asof)
        job.update({"status": "already_up_to_date", "finished_at": utc_now(), "latest_after": job["latest_before"], "pending_asof_cleared": True})
        fpala_gate = attach_fpala_formal_accepted_latest_preflight(job, asof=asof, job_id=job_id, job_dir=job_dir, args=args)
        attach_qald_accepted_latest_candidate_preflight(
            job,
            asof=asof,
            job_id=job_id,
            job_dir=job_dir,
            args=args,
            fpala_gate=fpala_gate,
            skip_reason="already_up_to_date",
        )
        finalize_job(job, job_dir=job_dir, asof=asof, args=args)
        print(json.dumps(job, ensure_ascii=False, indent=2))
        return 0

    should_wait, wait_status = should_wait_before_pull(
        asof=asof,
        asof_source=asof_source,
        now_taipei=now_taipei,
        today_earliest_time=today_earliest_time,
        force=args.force,
    )
    if should_wait:
        message = (
            "No pending asof exists and the resolved target is today; same-day data pulls wait until the configured Asia/Taipei data window."
            if wait_status == "today_data_window_wait"
            else "No pending asof exists and the resolved target is a weekend date; no data pull was started."
        )
        job.update({
            "status": wait_status,
            "message": message,
            "finished_at": utc_now(),
            "latest_after": job["latest_before"],
            "today_data_window_open": False,
        })
        fpala_gate = attach_fpala_formal_accepted_latest_preflight(job, asof=asof, job_id=job_id, job_dir=job_dir, args=args)
        attach_qald_accepted_latest_candidate_preflight(
            job,
            asof=asof,
            job_id=job_id,
            job_dir=job_dir,
            args=args,
            fpala_gate=fpala_gate,
            skip_reason=wait_status,
        )
        finalize_job(job, job_dir=job_dir, asof=asof, args=args)
        print(json.dumps(job, ensure_ascii=False, indent=2))
        return 0

    job["today_data_window_open"] = True
    write_json(job_dir / "job.json", job)

    symbols_file = materialize_symbols(job_dir)
    if not args.skip_finmind:
        start = (datetime.strptime(asof, "%Y-%m-%d").date() - timedelta(days=max(1, args.finmind_lookback_days))).isoformat()
        if args.finmind_scope == "daily" and args.enable_strict_e4_readonly_chain:
            job["finmind_scope_overridden_for_strict_e4"] = "daily_scope_would_skip_institutional_margin; using full orthogonal source refresh"
        symbols = [line.strip() for line in symbols_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        logical_state_path = FINMIND_LOGICAL_ACQUISITION_ROOT / f"{logical_acquisition.logical_run_id(target_asof=asof, symbols_sha256=logical_acquisition.symbols_checksum(symbols))}.json"
        logical_state = logical_acquisition.load_state(logical_state_path, target_asof=asof, symbols=symbols)
        job["acquisition_logical_run_id"] = logical_state["logical_run_id"]
        job["logical_acquisition_state_path"] = rel_path(logical_state_path)
        job["finmind_update"] = run_finmind_segmented_update(
            symbols_file=symbols_file,
            job_dir=job_dir,
            start=start,
            end=asof,
            timeout_seconds=args.timeout_seconds,
            skip_validate=bool(args.skip_finmind_validate),
            full_scope=bool(
                args.finmind_scope == "full"
                or args.enable_strict_e4_readonly_chain
            ),
            # A full-scope run must capture every HSA8 required family in this
            # acquisition run. The quota-aware orthogonal checkpoint is useful
            # for background coverage, but cannot substitute for same-run
            # institutional/margin evidence in the strict handoff.
            include_orthogonal_segments=bool(
                args.disable_finmind_orthogonal_batch
                or args.enable_strict_e4_readonly_chain
                or args.finmind_scope == "full"
            ),
            include_optional_segments=bool(args.disable_finmind_orthogonal_batch and not args.finmind_logical_required_only),
            reuse_success_cache=not bool(args.disable_finmind_segment_cache),
            cooldown_hours=float(args.finmind_provider_error_cooldown_hours),
            acquisition_run_id=logical_state["logical_run_id"],
            logical_state_path=logical_state_path,
        )
        job["finmind_start"] = start
        job["finmind_update_triggered"] = True
        if args.finmind_scope == "full":
            # Full segmented acquisition already requests institutional and
            # margin for the complete universe. A second quota-aware batch
            # would duplicate provider calls and blur same-run evidence.
            job["finmind_orthogonal_batch_skipped_reason"] = "full_segmented_capture_supersedes_batch"
        elif not args.disable_finmind_orthogonal_batch and not args.enable_strict_e4_readonly_chain:
            job["finmind_orthogonal_batch_update"] = run_finmind_orthogonal_batch_update(
                symbols_file=symbols_file,
                job_dir=job_dir,
                asof=asof,
                timeout_seconds=args.timeout_seconds,
                batch_size=max(1, int(args.finmind_orthogonal_batch_size)),
                lookback_days=max(1, int(args.finmind_orthogonal_lookback_days)),
                cooldown_hours=float(args.finmind_provider_error_cooldown_hours),
            )
            job["finmind_orthogonal_batch_update_triggered"] = True
            job["finmind_orthogonal_batch_status"] = str(job["finmind_orthogonal_batch_update"].get("status") or "")
            attach_orthogonal_batch_to_finmind_stdout(job_dir, job["finmind_orthogonal_batch_update"].get("summary") or {})
        if full_orthogonal_refresh_mode:
            evidence = build_full_orthogonal_refresh_evidence(
                job=job,
                job_dir=job_dir,
                asof=asof,
                expected_symbol_count=len(symbols),
                protected_before=job["full_orthogonal_protected_latest_before"],
            )
            evidence_path = job_dir / "full_orthogonal_refresh_evidence.json"
            write_json(evidence_path, evidence)
            job["full_orthogonal_refresh"] = evidence
            job["full_orthogonal_refresh_evidence_path"] = rel_path(evidence_path)
            job["full_orthogonal_refresh_triggered"] = True
            job["orthogonal_source_refresh_triggered"] = True
            job["o4_prospective_shadow"] = run_o4_prospective_shadow_nonblocking(
                asof=asof,
                job_id=job_id,
                job_dir=job_dir,
                source_run_id=str(job.get("acquisition_logical_run_id") or ""),
                decision_cutoff=utc_now(),
                enabled=bool(args.enable_mbcds3_daily_shadow),
            )
            write_json(job_dir / "job.json", job)
            if (
                args.enable_b19r2r_shadow
                and not args.enable_strict_e4_readonly_chain
                and evidence["protected_latest_unchanged"]["all_protected_paths_unchanged"]
            ):
                # A is already accepted for this day. Full acquisition is now
                # a shadow-only concern, including incomplete source coverage.
                # B's own Exact-50/TW7769/PIT gate decides readiness; do not
                # republish A/provider or put research failures into A pending.
                if args.enable_model_signal_gate:
                    job["same_run_handoff"] = build_real_same_run_handoff(
                        job=job,
                        job_dir=job_dir,
                        symbols=symbols,
                    )
                    daily_tracks = run_daily_model_track_batch(
                        job=job,
                        job_dir=job_dir,
                        asof=asof,
                        include_prior_jobs=True,
                        timeout_seconds=args.timeout_seconds,
                    )
                    job["daily_model_tracks"] = daily_tracks
                    challenger = (daily_tracks.get("tracks") or {}).get(
                        "model_a_plus_b_b19r2r", {}
                    )
                    shadow = {
                        **challenger,
                        "enabled": True,
                        "shadow_ok": challenger.get("ok") is True,
                        "mainline_blocking": False,
                        "production_allowed": False,
                        "no_apply": True,
                        "pending_asof_set": False,
                    }
                else:
                    shadow = {
                        "enabled": True, "attempted": False, "ok": True,
                        "shadow_ok": False, "status": "BLOCKED_MODEL_A_GATE_DISABLED",
                        "mainline_blocking": False, "production_allowed": False,
                        "no_apply": True, "pending_asof_set": False,
                    }
                job["b19r2r_daily_shadow"] = shadow
                job["full_orthogonal_refresh_status"] = evidence["status"]
                job["accepted_day_shadow_only"] = True
                job.update({
                    "status": "accepted_day_model_tracks_ready" if shadow.get("shadow_ok") else "accepted_day_model_tracks_blocked",
                    "finished_at": utc_now(),
                    "latest_after": latest_asof(),
                })
                if not shadow.get("shadow_ok"):
                    job["b19r2r_daily_shadow_warning"] = shadow.get("warning") or shadow.get("status")
                finalize_job(job, job_dir=job_dir, asof=asof, args=args)
                print(json.dumps(job, ensure_ascii=False, indent=2))
                return 0
            if not evidence["ok"]:
                # An incomplete full-scope capture is retryable acquisition
                # failure. Keep the target pending so the next cron run can
                # resume the same asof instead of silently advancing.
                set_pending_asof(asof, reason="full_orthogonal_refresh_incomplete", job_id=job_id)
                job.update({
                    "status": "full_orthogonal_refresh_incomplete",
                    "message": "Full orthogonal research sources were incomplete; downstream signal/strategy/artifact stages were not entered.",
                    "finished_at": utc_now(),
                    "latest_after": latest_asof(),
                    "pending_asof_set": asof,
                })
                finalize_job(job, job_dir=job_dir, asof=asof, args=args)
                print(json.dumps(job, ensure_ascii=False, indent=2))
                return 2
            # A successful full capture is the acquisition/readiness portion
            # of the same daily run. Continue through the shared handoff,
            # signal, strategy, and downstream gates instead of terminating
            # before the product chain can observe the new asof.
            job["full_orthogonal_refresh_status"] = "PASSED_CONTINUE_DOWNSTREAM"
            job["full_orthogonal_refresh_downstream_continued"] = True
        # HSA8 is a four-source Model B contract. The high-frequency daily
        # scope intentionally captures adjusted prices only, so it cannot
        # produce a complete HSA8 handoff. Keep that scope non-blocking for
        # the active Model A-only lane; full scope remains the Model B check.
        if args.finmind_scope == "daily" and not args.enable_strict_e4_readonly_chain:
            handoff = {
                "ok": False,
                "status": "WAIT_FULL_SCOPE",
                "reason": "model_b_hsa8_requires_full_scope_capture",
                "job_id": str(job.get("acquisition_logical_run_id") or job_id),
                "target_asof": asof,
                "sources": [],
                "model_b_nonblocking": True,
            }
        else:
            handoff = build_real_same_run_handoff(job=job, job_dir=job_dir, symbols=symbols)
        job["same_run_handoff"] = handoff
        # Observation-only Model A can use the validated candidate/isolated
        # artifact lane without enabling legacy provider publish.
        modela_observation_lane_enabled = bool(
            not args.skip_qlib
            and args.enable_model_signal_gate
            and not args.enable_strict_e4_readonly_chain
        )
        independent_modela_baseline_enabled = bool(
            not args.skip_qlib
            and (args.enable_legacy_provider_publish or modela_observation_lane_enabled)
        )
        hsa8_status = "PASS" if handoff.get("ok") else (
            "WAIT_FULL_SCOPE" if handoff.get("status") == "WAIT_FULL_SCOPE" else "BLOCKED_MODEL_B_ONLY"
        )
        job["model_b_hsa8_gate"] = {
            "status": hsa8_status,
            "blocks_strict_model_b_generation": not bool(handoff.get("ok")),
            "blocks_legacy_readonly_model_b": False,
            "legacy_compatible_model_b_status": MODELB_LEGACY_COMPATIBILITY["status"],
            "blocks_yahoo_adjusted_model_a_baseline": bool(
                not handoff.get("ok") and not independent_modela_baseline_enabled
            ),
            "model_a_only_nonblocking": bool(independent_modela_baseline_enabled),
            "independent_yahoo_adjusted_modela_baseline_enabled": independent_modela_baseline_enabled,
            "reason": "" if handoff.get("ok") else str(handoff.get("error") or handoff.get("reason") or "same_run_handoff_failed"),
        }
        write_json(job_dir / "job.json", job)
        if not handoff.get("ok"):
            if args.enable_strict_e4_readonly_chain:
                set_pending_asof(asof, reason="same_run_handoff_failed", job_id=job_id)
                job.update({
                    "status": "same_run_handoff_failed",
                    "message": "Same-run HSA8 failed and no independently validated Yahoo-adjusted Model A baseline was enabled; no downstream gates were entered.",
                    "finished_at": utc_now(),
                    "latest_after": latest_asof(),
                    "pending_asof_set": asof,
                })
                finalize_job(job, job_dir=job_dir, asof=asof, args=args)
                print(json.dumps(job, ensure_ascii=False, indent=2))
                return 2
            job["same_run_handoff_warning"] = (
                "Model B HSA8 is not ready for this run; Model A-only observation continues without provider/latest publish."
            )
            job["same_run_handoff_nonblocking_for_modela_baseline"] = True
        job["orthogonal_source_refresh_triggered"] = bool(args.enable_strict_e4_readonly_chain)
        if not job["finmind_update"].get("ok"):
            job["finmind_update_warning"] = "FinMind/QuantDinger segmented raw archive did not fully pass; successful segments remain captured in merged stdout and Yahoo/qlib update continues."
        write_json(job_dir / "job.json", job)

    if args.skip_finmind:
        handoff = build_real_same_run_handoff(job=job, job_dir=job_dir, symbols=[
            line.strip() for line in symbols_file.read_text(encoding="utf-8").splitlines() if line.strip()
        ])
        job["same_run_handoff"] = handoff
        job.update({
            "status": "same_run_handoff_failed",
            "message": "--skip-finmind cannot bypass the required same-run acquisition handoff gate.",
            "finished_at": utc_now(),
            "latest_after": latest_asof(),
        })
        write_json(job_dir / "job.json", job)
        set_pending_asof(asof, reason="same_run_handoff_failed", job_id=job_id)
        finalize_job(job, job_dir=job_dir, asof=asof, args=args)
        print(json.dumps(job, ensure_ascii=False, indent=2))
        return 2

    if not args.skip_qlib and not args.enable_legacy_provider_publish:
        job["qlib_legacy_provider_path_skipped"] = True
        job["qlib_legacy_provider_skip_reason"] = "m3_readonly_orchestrator_default_requires_explicit_enable_legacy_provider_publish"
        write_json(job_dir / "job.json", job)

    if not args.skip_qlib and args.enable_legacy_provider_publish:
        refresh_job_id = f"option_c_yahoo_scrapling_refresh_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_daily_auto"
        refresh_argv = [
            PYTHON,
            "examples/tw/run_option_c_yahoo_scrapling_refresh.py",
            "--asof",
            asof,
            "--start",
            "2015-01-01",
            "--universe",
            "option_c_accepted_150",
            "--output-root",
            "data_tw/experiments/option_c_ops",
            "--job-id",
            refresh_job_id,
            "--timeout",
            str(args.refresh_timeout),
            "--retries",
            str(args.refresh_retries),
            "--sleep-seconds",
            str(args.refresh_sleep_seconds),
            "--continue-on-error",
            "--suffix",
            "auto",
            "--max-workers",
            str(args.max_workers),
            "--report-path",
            str(job_dir / "refresh_report.md"),
        ]
        if args.proxy.strip():
            idx = refresh_argv.index("--timeout")
            refresh_argv[idx:idx] = ["--proxy", args.proxy.strip()]
        job["refresh_job_id"] = refresh_job_id
        job["yahoo_refresh"] = run_cmd(refresh_argv, cwd=QLIB, stdout_path=job_dir / "refresh_stdout.txt", stderr_path=job_dir / "refresh_stderr.txt", timeout=args.timeout_seconds)
        job["yahoo_refresh_triggered"] = True
        refresh_summary = read_json(QLIB / "data_tw/experiments/option_c_ops" / refresh_job_id / "reports/execution_summary.json")
        job["refresh_summary"] = refresh_summary
        write_json(job_dir / "job.json", job)
        if not job["yahoo_refresh"].get("ok") or refresh_summary.get("status") != "staged_refresh_complete_waiting_for_review":
            set_pending_asof(asof, reason="fresh_data_wait", job_id=job_id)
            job.update({"status": "fresh_data_wait", "message": "Yahoo/Scrapling did not produce complete asof data yet; next scheduled run should retry this same asof even after midnight.", "finished_at": utc_now(), "latest_after": latest_asof(), "pending_asof_set": asof})
            finalize_job(job, job_dir=job_dir, asof=asof, args=args)
            print(json.dumps(job, ensure_ascii=False, indent=2))
            return 2

        publish_job_id = f"option_c_yahoo_scrapling_publish_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_daily_auto"
        publish_argv = [
            PYTHON,
            "examples/tw/publish_option_c_yahoo_scrapling_refresh.py",
            "--job-dir",
            f"data_tw/experiments/option_c_ops/{refresh_job_id}",
            "--asof",
            asof,
            "--mode",
            "publish",
            "--provider-scope",
            "option_c_150",
            "--publish-job-id",
            publish_job_id,
            "--max-workers",
            str(args.max_workers),
            "--report-path",
            str(job_dir / "publish_report.md"),
        ]
        job["publish_job_id"] = publish_job_id
        job["provider_publish"] = run_cmd(publish_argv, cwd=QLIB, stdout_path=job_dir / "publish_stdout.txt", stderr_path=job_dir / "publish_stderr.txt", timeout=args.timeout_seconds)
        job["provider_publish_triggered"] = True
        publish_summary = read_json(QLIB / "data_tw/experiments/option_c_ops" / publish_job_id / "reports/publish_execution_summary.json")
        job["publish_summary"] = publish_summary
        write_json(job_dir / "job.json", job)
        if not job["provider_publish"].get("ok") or publish_summary.get("status") != "publish_complete_waiting_for_review":
            set_pending_asof(asof, reason="provider_publish_failed", job_id=job_id)
            job.update({"status": "provider_publish_failed", "message": "Formal qlib provider publish failed; latest_signal was not updated.", "finished_at": utc_now(), "latest_after": latest_asof(), "pending_asof_set": asof})
            finalize_job(job, job_dir=job_dir, asof=asof, args=args)
            print(json.dumps(job, ensure_ascii=False, indent=2))
            return 3

        # The immutable provider snapshot now exists, while accepted/latest
        # pointers still reference the previous validated day. Run the full
        # model fan-out here so a required-track failure cannot publish first.
        if args.enable_b19r2r_shadow and args.enable_model_signal_gate:
            daily_tracks = run_daily_model_track_batch(
                job=job,
                job_dir=job_dir,
                asof=asof,
                include_prior_jobs=False,
                timeout_seconds=args.timeout_seconds,
            )
            job["daily_model_tracks"] = daily_tracks
            job["b19r2r_decision_cutoff"] = str(daily_tracks.get("decision_cutoff") or "")
            challenger = (daily_tracks.get("tracks") or {}).get(
                "model_a_plus_b_b19r2r", {}
            )
            job["b19r2r_daily_shadow"] = {
                **challenger,
                "enabled": True,
                "shadow_ok": challenger.get("ok") is True,
                "mainline_blocking": False,
                "production_allowed": False,
                "no_apply": True,
                "pending_asof_set": False,
            }
            if challenger.get("attempted") and challenger.get("ok") is not True:
                job["b19r2r_daily_shadow_warning"] = (
                    challenger.get("error") or challenger.get("status")
                )
            write_json(job_dir / "job.json", job)
            if not daily_tracks.get("ok"):
                set_pending_asof(
                    asof,
                    reason="daily_model_required_track_failed",
                    job_id=job_id,
                )
                job.update({
                    "status": "daily_model_required_track_failed",
                    "message": "The required daily model track did not produce a valid ModelSignalArtifact.",
                    "finished_at": utc_now(),
                    "latest_after": latest_asof(),
                    "pending_asof_set": asof,
                })
                finalize_job(job, job_dir=job_dir, asof=asof, args=args)
                print(json.dumps(job, ensure_ascii=False, indent=2))
                return 2

        try:
            accepted = publish_accepted_latest(asof)
        except Exception as exc:  # Keep the target asof retryable if the final accepted-latest stage crashes.
            set_pending_asof(asof, reason="accepted_latest_exception", job_id=job_id)
            job["accepted_latest_exception"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback_tail": traceback.format_exc()[-4000:],
            }
            job.update({
                "status": "accepted_latest_exception",
                "message": str(exc),
                "finished_at": utc_now(),
                "latest_after": latest_asof(),
                "pending_asof_set": asof,
            })
            finalize_job(job, job_dir=job_dir, asof=asof, args=args)
            print(json.dumps(job, ensure_ascii=False, indent=2))
            return 4
        job["accepted_latest"] = accepted
        job["latest_signal_updated"] = bool(accepted.get("latest_signal_updated"))
        if not accepted.get("ok"):
            set_pending_asof(asof, reason="accepted_latest_failed", job_id=job_id)
            job.update({"status": "accepted_latest_failed", "message": accepted.get("message") or accepted.get("status"), "finished_at": utc_now(), "latest_after": latest_asof(), "pending_asof_set": asof})
            finalize_job(job, job_dir=job_dir, asof=asof, args=args)
            print(json.dumps(job, ensure_ascii=False, indent=2))
            return 4

    provider_candidate_refresh_gate = run_provider_candidate_refresh_gate(
        asof=asof,
        job_id=job_id,
        job_dir=job_dir,
        enabled=bool(args.enable_provider_candidate_refresh),
        model_signal_gate_enabled=bool(args.enable_model_signal_gate),
        args=args,
        timeout_seconds=args.timeout_seconds,
    )
    job["provider_candidate_refresh_gate"] = provider_candidate_refresh_gate
    job["provider_candidate_refresh_triggered"] = bool(provider_candidate_refresh_gate.get("provider_candidate_refresh_triggered"))
    job["provider_candidate_reused_existing"] = bool(provider_candidate_refresh_gate.get("provider_candidate_reused_existing"))
    job["provider_candidate_refresh_status"] = str(provider_candidate_refresh_gate.get("status") or "")
    if provider_candidate_refresh_gate.get("attempted") and not provider_candidate_refresh_gate.get("ok"):
        job["provider_candidate_refresh_warning"] = provider_candidate_refresh_gate.get("error") or provider_candidate_refresh_gate.get("status")
    write_json(job_dir / "job.json", job)

    fpala_gate = attach_fpala_formal_accepted_latest_preflight(
        job,
        asof=asof,
        job_id=job_id,
        job_dir=job_dir,
        args=args,
        provider_candidate_gate=provider_candidate_refresh_gate,
    )

    job["mbcds3_decision_cutoff"] = utc_now()
    model_signal_gate = run_model_signal_gate(
        asof=asof,
        job_id=job_id,
        job_dir=job_dir,
        enabled=args.enable_model_signal_gate,
        args=args,
        timeout_seconds=args.timeout_seconds,
        model_b_enabled=bool(args.enable_mbcds3_daily_shadow),
        model_b_hsa8_ready=bool(
            args.enable_mbcds3_daily_shadow
            and (job.get("same_run_handoff") or {}).get("ok")
        ),
        source_acquisition_run_id=str(job.get("acquisition_logical_run_id") or ""),
        decision_cutoff=str(job.get("mbcds3_decision_cutoff") or ""),
    )
    job["model_signal_gate"] = model_signal_gate
    job["model_a_score_job_triggered"] = bool(model_signal_gate.get("model_a_score_job_triggered"))
    job["model_b_ltr_score_job_triggered"] = bool(model_signal_gate.get("model_b_ltr_score_job_triggered"))
    if model_signal_gate.get("attempted") and not model_signal_gate.get("ok"):
        job["model_signal_gate_warning"] = model_signal_gate.get("error") or "model signal gate failed"
    write_json(job_dir / "job.json", job)

    # HSA8 is Model B-only. A failed Model A gate is the actual operational
    # blocker and must remain pending for the next automatic retry.
    if args.enable_model_signal_gate and not model_signal_gate.get("ok"):
        set_pending_asof(asof, reason="model_signal_gate_failed", job_id=job_id)
        job.update({
            "status": "model_signal_gate_failed",
            "message": str(model_signal_gate.get("error") or "validated Model A signal gate failed"),
            "finished_at": utc_now(),
            "latest_after": latest_asof(),
            "pending_asof_set": asof,
        })
        finalize_job(job, job_dir=job_dir, asof=asof, args=args)
        print(json.dumps(job, ensure_ascii=False, indent=2))
        return 2

    if args.enable_b19r2r_shadow and not args.enable_model_signal_gate:
        job["b19r2r_daily_shadow"] = {
            "enabled": True,
            "attempted": False,
            "ok": True,
            "shadow_ok": False,
            "status": "BLOCKED_MODEL_A_GATE_DISABLED",
            "warning": "Daily model tracks require the model signal gate",
            "mainline_blocking": False,
            "production_allowed": False,
            "no_apply": True,
            "pending_asof_set": False,
        }
        write_json(job_dir / "job.json", job)

    mbcds3_source_availability_ledger = build_mbcds3_source_availability_ledger(
        asof=asof,
        job=job,
        job_dir=job_dir,
        decision_cutoff=str(job.get("mbcds3_decision_cutoff") or utc_now()),
    )
    job["mbcds3_source_availability_ledger"] = mbcds3_source_availability_ledger
    write_json(job_dir / "job.json", job)

    mbcds3_inventory_bridge = build_mbcds3_daily_inventory_bridge(
        asof=asof,
        job_dir=job_dir,
        model_signal_gate=model_signal_gate,
        availability_ledger=mbcds3_source_availability_ledger,
    )
    job["mbcds3_inventory_bridge"] = mbcds3_inventory_bridge
    write_json(job_dir / "job.json", job)

    mbcds3_daily_shadow = run_mbcds3_daily_shadow_accumulation(
        asof=asof,
        job_id=job_id,
        job_dir=job_dir,
        enabled=bool(args.enable_mbcds3_daily_shadow),
        inventory_path=args.mbcds3_daily_shadow_inventory or mbcds3_inventory_bridge.get("inventory_path", ""),
        accumulator_dir=args.mbcds3_daily_shadow_accumulator_dir,
    )
    job["mbcds3_daily_shadow"] = mbcds3_daily_shadow
    job["mbcds3_daily_shadow_attempted"] = bool(mbcds3_daily_shadow.get("attempted"))
    job["mbcds3_daily_shadow_status"] = str(mbcds3_daily_shadow.get("status") or "")
    if mbcds3_daily_shadow.get("status", "").startswith("BLOCKED_") and not mbcds3_daily_shadow.get("ok", True):
        job["mbcds3_daily_shadow_warning"] = mbcds3_daily_shadow.get("error") or mbcds3_daily_shadow.get("status")
    write_json(job_dir / "job.json", job)

    mbcds35_shadow = run_mbcds35_prospective_shadow(
        asof=asof, job_id=job_id, job_dir=job_dir,
        enabled=bool(args.enable_mbcds3_daily_shadow),
        accumulator_dir=args.mbcds3_daily_shadow_accumulator_dir,
        inventory_path=args.mbcds3_daily_shadow_inventory or mbcds3_inventory_bridge.get("inventory_path", ""),
        source_ledger=job_dir / "mbcds3_source_availability_ledger.json",
    )
    job["mbcds35_prospective_shadow"] = mbcds35_shadow
    write_json(job_dir / "mbcds35_prospective_shadow.json", mbcds35_shadow)
    write_json(job_dir / "job.json", job)

    attach_qald_accepted_latest_candidate_preflight(
        job,
        asof=asof,
        job_id=job_id,
        job_dir=job_dir,
        args=args,
        provider_candidate_gate=provider_candidate_refresh_gate,
        model_signal_gate=model_signal_gate,
        fpala_gate=fpala_gate,
    )

    strict_e4_chain = run_strict_e4_readonly_chain(
        asof=asof,
        job_dir=job_dir,
        enabled=args.enable_strict_e4_readonly_chain,
        readonly_price_bridge_dir=args.strict_e4_readonly_price_bridge_dir if args.enable_strict_e4_readonly_chain else "",
        readonly_twii_bridge=args.strict_e4_readonly_twii_bridge if args.enable_strict_e4_readonly_chain else "",
        timeout_seconds=args.timeout_seconds,
    )
    job["strict_e4_readonly_chain"] = strict_e4_chain
    job["strict_e4_chain_triggered"] = bool(strict_e4_chain.get("attempted"))
    job["strict_e4_readonly_bridge_contract_triggered"] = bool(
        strict_e4_chain.get("attempted")
        and (strict_e4_chain.get("readonly_price_bridge_dir") or strict_e4_chain.get("readonly_twii_bridge"))
    )
    job["strict_e4_readonly_bridge_validator_ok"] = bool(
        strict_e4_chain.get("ok")
        and strict_e4_chain.get("readonly_price_bridge_used_by_yz2")
        and strict_e4_chain.get("readonly_twii_bridge_used_by_yz2")
        and strict_e4_chain.get("readonly_price_bridge_used_by_yz2r")
        and not strict_e4_chain.get("formal_normalized_nonempty_used_for_price_or_twii")
    )
    job["model_b_yz2_validator_ok"] = bool(strict_e4_chain.get("model_b_yz2_validator_ok"))
    if strict_e4_chain.get("attempted") and not strict_e4_chain.get("ok"):
        job["strict_e4_readonly_chain_warning"] = strict_e4_chain.get("error") or strict_e4_chain.get("status")
        job["strict_e4_readonly_bridge_warning"] = job["strict_e4_readonly_chain_warning"]
    elif job["strict_e4_readonly_bridge_contract_triggered"] and not job["strict_e4_readonly_bridge_validator_ok"]:
        job["strict_e4_readonly_bridge_warning"] = "strict E4 readonly bridge requested but YZ2/YZ2R bridge usage contract did not fully pass"

    ador_no_publish = run_ador_no_publish_orchestration_dry_run(
        asof=asof,
        job_id=job_id,
        job_dir=job_dir,
        job=job,
        enabled=bool(args.enable_ador_no_publish_orchestration_dry_run),
        dry_run=bool(args.ador_no_publish_orchestration_dry_run),
    )
    job["ador_no_publish_orchestration"] = ador_no_publish
    if ador_no_publish.get("attempted") and not ador_no_publish.get("ok"):
        job["ador_no_publish_orchestration_warning"] = ador_no_publish.get("status") or "ador no-publish orchestration gate blocked"
    write_json(job_dir / "job.json", job)

    dapr18_controlled_latest = run_dapr18_controlled_latest_orchestration(
        asof=asof,
        job_id=job_id,
        job_dir=job_dir,
        job=job,
        args=args,
        enabled=bool(args.enable_dapr18_controlled_latest_orchestration),
        dry_run=bool(args.dapr18_controlled_latest_dry_run),
        build_candidates=bool(args.dapr18_build_candidates),
        publish_controlled_signal_latest=bool(args.dapr18_publish_controlled_signal_latest),
        publish_readonly_snapshot_latest=bool(args.dapr18_publish_readonly_snapshot_latest),
        publish_agent_prompt_latest=bool(args.dapr18_publish_agent_prompt_latest),
        exact_authorization_id=args.dapr18_exact_authorization_id,
    )
    job["dapr18_controlled_latest_orchestration"] = dapr18_controlled_latest
    if dapr18_controlled_latest.get("attempted") and not dapr18_controlled_latest.get("ok"):
        job["dapr18_controlled_latest_orchestration_warning"] = (
            dapr18_controlled_latest.get("status") or "dapr18 controlled latest orchestration gate blocked"
        )
    write_json(job_dir / "job.json", job)
    if finalize_dapr18_publish_failure(
        job=job,
        orchestration=dapr18_controlled_latest,
        asof=asof,
        job_id=job_id,
        job_dir=job_dir,
        args=args,
    ):
        print(json.dumps(job, ensure_ascii=False, indent=2))
        return 2

    readonly_snapshot = run_readonly_strategy_snapshot_publish(asof=asof, job_dir=job_dir)
    job["readonly_snapshot"] = readonly_snapshot
    if readonly_snapshot.get("attempted"):
        write_json(READONLY_DAILY_INTEGRATION_AUDIT, {"job_id": job_id, "asof": asof, "created_at": utc_now(), **readonly_snapshot})
    if readonly_snapshot.get("attempted") and not readonly_snapshot.get("ok"):
        job["readonly_snapshot_warning"] = readonly_snapshot.get("error") or "readonly snapshot publish failed"

    if not args.enable_legacy_provider_publish:
        runtime_protected_after = protected_latest_fingerprints(
            readonly_latest_path=READONLY_SNAPSHOT_LATEST,
            agent_latest_path=AGENT_DAILY_PROMPT_LATEST,
            provider_latest_path=LATEST,
            legacy_latest_path=ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
        )
        if (
            dapr18_controlled_latest.get("ok") is True
            and dapr18_controlled_latest.get("status") in {
                "auto_publish_chain_completed",
                "auto_publish_idempotent_noop_already_current",
            }
        ):
            job["runtime_stage_terminal"] = build_authorized_readonly_publish_terminal(
                asof=asof,
                job_id=job_id,
                orchestration=dapr18_controlled_latest,
                protected_before=runtime_protected_before,
                protected_after=runtime_protected_after,
                trading=job.get("trading") or {},
            )
        else:
            job["runtime_stage_terminal"] = build_legacy_observation_terminal(
                asof=asof,
                job_id=job_id,
                protected_before=runtime_protected_before,
                protected_after=runtime_protected_after,
            )
        job["runtime_protected_after"] = runtime_protected_after

    # Legacy provider publish is an explicitly authorized write path too. Keep
    # the same post-run fingerprints at the top level so its provider/latest
    # mutation is auditable without relying on nested child artifacts.
    if "runtime_protected_after" not in job:
        job["runtime_protected_after"] = protected_latest_fingerprints(
            readonly_latest_path=READONLY_SNAPSHOT_LATEST,
            agent_latest_path=AGENT_DAILY_PROMPT_LATEST,
            provider_latest_path=LATEST,
            legacy_latest_path=ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
        )

    clear_pending_asof(asof)
    job.update({"status": "daily_auto_update_passed", "finished_at": utc_now(), "latest_after": latest_asof(), "pending_asof_cleared": True})
    finalize_job(job, job_dir=job_dir, asof=asof, args=args)
    print(json.dumps(job, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
