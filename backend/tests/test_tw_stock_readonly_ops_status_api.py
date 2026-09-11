"""Tests for DAOV1 readonly ops status API/service."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.services.tw_stock_daily_auto_update_status import TWStockDailyAutoUpdateStatusService
from app.services.tw_stock_readonly_ops_status import TWStockReadonlyOpsStatusService


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _make_service(tmp_path: Path) -> TWStockReadonlyOpsStatusService:
    ops_root = tmp_path / "data_tw/ops/daily_auto_update"
    qlib_latest = tmp_path / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
    controlled_latest = tmp_path / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json"
    snapshot_latest = tmp_path / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
    agent_latest = tmp_path / "data_tw/artifacts/agent_daily_prompt/latest.json"
    legacy_latest = tmp_path / "data_tw/experiments/option_c_daily_signal/latest_signal.json"
    daily_service = TWStockDailyAutoUpdateStatusService(signal_root=qlib_latest.parent, ops_root=ops_root)

    _write_json(
        qlib_latest,
        {
            "asof": "2026-07-08",
            "created_at": "2026-07-17T04:50:50Z",
            "diagnostic_only": True,
            "research_signal_not_order": True,
            "run_dir": "data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260708_fixture",
            "status": "accepted",
        },
    )
    _write_json(
        controlled_latest,
        {
            "artifact_type": "controlled_model_signal_latest_pointer",
            "asof": "2026-07-17",
            "signal_asof": "2026-07-17",
            "run_id": "dapr8_modela_20260717_contained",
            "readonly_only": True,
            "production_trade_enabled": False,
            "provider_publish": False,
            "qlib_accepted_latest_switch": False,
        },
    )
    _write_json(
        snapshot_latest,
        {
            "artifact_type": "readonly_strategy_snapshot_latest_pointer",
            "asof": "2026-07-17",
            "signal_asof": "2026-07-17",
            "target_date": "2026-07-17",
            "planned_manifest_payload_sha256": "snapshot-manifest-sha",
            "candidate_only": True,
            "not_provider_accepted_latest": True,
            "not_trade_target_latest": True,
            "production_trade_enabled": False,
            "readonly_only": True,
        },
    )
    _write_json(
        agent_latest,
        {
            "artifact_type": "tw_agent_daily_prompt_latest",
            "checksum": "sha256:agent-fixture",
            "manifest": "data_tw/artifacts/agent_daily_prompt/2026-07-17/manifest.json",
            "production_trade_enabled": False,
            "readonly_only": True,
            "signal_asof": "2026-07-17",
            "target_date": "2026-07-17",
        },
    )
    _write_json(legacy_latest, {"asof": "2026-06-01", "status": "accepted"})

    job_dir = ops_root / "daily_tw_stock_auto_update_20260720_20260720T144501Z"
    _write_json(
        job_dir / "job.json",
        {
            "job_id": "daily_tw_stock_auto_update_20260720_20260720T144501Z",
            "status": "daily_auto_update_passed",
            "asof": "2026-07-20",
            "started_at": "2026-07-20T14:45:01+00:00",
            "finished_at": "2026-07-20T14:46:34+00:00",
            "dapr18_controlled_latest_orchestration_enabled": True,
            "dapr18_controlled_latest_dry_run": True,
            "dapr18_build_candidates": False,
            "dapr18_publish_controlled_signal_latest": False,
            "dapr18_publish_readonly_snapshot_latest": False,
            "dapr18_publish_agent_prompt_latest": False,
            "dapr18_exact_authorization_present": False,
            "provider_publish_triggered": False,
            "latest_signal_updated": False,
            "trading": {
                "orders_enabled": False,
                "connects_to_broker": False,
                "research_signal_not_order": True,
            },
        },
    )
    _write_json(
        job_dir / "daily_chain_status.json",
        {
            "asof": "2026-07-20",
            "job_id": "daily_tw_stock_auto_update_20260720_20260720T144501Z",
            "state": "RAW_READY_PROVIDER_STALE",
            "raw_status": "READY",
            "blocked_at": "qlib_provider_view_or_formal_calendar",
            "blocker_reason": "formal qlib provider calendar is stale",
            "next_retry_hint": "retry_after_provider_view_refresh_or_canonical_bridge",
            "next_required_action": "refresh_formal_qlib_provider_view_or_build_validated_canonical_bridge_then_run_model_a_score",
            "lineage_evidence": {
                "formal_calendar_max": "2026-06-25",
                "raw_evidence_paths": ["data_tw/ops/daily_auto_update/fixture/finmind_stdout.txt"],
                "raw_detail": {
                    "source": "current_job",
                    "source_max_date": "2026-07-20",
                    "row_count": "25650",
                    "symbol_count": "150",
                },
            },
            "forbidden_actions": {
                "all_false": True,
                "actions": {
                    "provider_refresh_triggered": False,
                    "provider_publish_triggered": False,
                    "accepted_latest_switch_triggered": False,
                    "target_position_or_weight_generated": False,
                },
            },
        },
    )
    _write_json(
        job_dir / "dapr18_controlled_latest_orchestration_summary.json",
        {
            "created_at": "2026-07-20T14:46:34+00:00",
            "enabled": True,
            "attempted": True,
            "ok": True,
            "status": "dry_run_plan_recorded",
            "dry_run": True,
            "build_candidates": False,
            "publish_controlled_signal_latest": False,
            "publish_readonly_snapshot_latest": False,
            "publish_agent_prompt_latest": False,
            "exact_authorization_present": False,
            "latest_pointer_write_performed": False,
            "source_readiness_state": "BLOCKED_WITH_REASON",
            "blockers": [
                "controlled_signal_latest_asof_mismatch_or_missing",
                "readonly_snapshot_latest_asof_mismatch_or_missing",
            ],
            "protected_paths_unchanged": True,
            "forbidden_actions_all_false": True,
            "evidence_paths": {
                "summary": str(job_dir / "dapr18_controlled_latest_orchestration_summary.json"),
            },
        },
    )
    _write_json(
        job_dir / "dapr18_controlled_latest_readiness.json",
        {
            "asof": "2026-07-20",
            "job_id": "daily_tw_stock_auto_update_20260720_20260720T144501Z",
            "readiness_state": "BLOCKED_WITH_REASON",
            "blockers": ["controlled_signal_latest_asof_mismatch_or_missing"],
        },
    )
    _write_json(
        job_dir / "dapr18_forbidden_action_audit.json",
        {
            "all_false": True,
            "actions": {
                "provider_or_network_pull": False,
                "provider_publish": False,
                "formal_qlib_refresh": False,
                "accepted_latest_switch": False,
                "controlled_signal_latest_write": False,
                "readonly_snapshot_latest_write": False,
                "agent_prompt_latest_write": False,
                "openai_call": False,
                "db_write": False,
                "monitor_or_broker_or_order_path": False,
                "target_position_or_weight_output": False,
            },
        },
    )
    _write_json(
        job_dir / "dapr18_protected_paths_fingerprint.json",
        {
            "all_protected_paths_unchanged": True,
            "unchanged": {"all_protected_paths_unchanged": True},
        },
    )
    return TWStockReadonlyOpsStatusService(
        repo_root=tmp_path,
        ops_root=ops_root,
        qlib_accepted_latest_path=qlib_latest,
        controlled_signal_latest_path=controlled_latest,
        readonly_snapshot_latest_path=snapshot_latest,
        agent_prompt_latest_path=agent_latest,
        legacy_option_c_latest_path=legacy_latest,
        daily_status_service=daily_service,
    )


def _configure_persistent_publish(service: TWStockReadonlyOpsStatusService) -> Path:
    target = "2026-07-20"
    for path in (
        service.controlled_signal_latest_path,
        service.readonly_snapshot_latest_path,
        service.agent_prompt_latest_path,
    ):
        payload = _read_json(path)
        payload["asof"] = target
        payload["signal_asof"] = target
        payload["target_date"] = target
        payload["readonly_only"] = True
        payload["production_trade_enabled"] = False
        _write_json(path, payload)

    job_dir = next(service.ops_root.glob("daily_tw_stock_auto_update_*"))
    summary_path = job_dir / "dapr18_controlled_latest_orchestration_summary.json"
    summary = _read_json(summary_path)
    summary.update(
        {
            "ok": True,
            "status": "auto_publish_chain_completed",
            "dry_run": False,
            "publish_controlled_signal_latest": True,
            "publish_readonly_snapshot_latest": True,
            "publish_agent_prompt_latest": True,
            "exact_authorization_present": True,
            "latest_pointer_write_performed": True,
            "controlled_signal_latest_write_performed": True,
            "readonly_snapshot_latest_write_performed": True,
            "agent_prompt_latest_write_performed": True,
            "source_readiness_state": "BLOCKED_WITH_REASON",
            "blockers": [
                "controlled_signal_latest_asof_mismatch_or_missing",
                "readonly_snapshot_latest_asof_mismatch_or_missing",
                "agent_prompt_latest_asof_mismatch_or_missing",
            ],
            "product_latest_state_after": {
                "target_asof": target,
                "controlled_signal_latest_asof": target,
                "readonly_snapshot_latest_asof": target,
                "agent_prompt_latest_asof": target,
                "all_product_latest_match_target": True,
            },
        }
    )
    _write_json(summary_path, summary)

    audit_path = job_dir / "dapr18_forbidden_action_audit.json"
    audit = _read_json(audit_path)
    audit["all_false"] = False
    audit["actions"].update(
        {
            "controlled_signal_latest_write": True,
            "readonly_snapshot_latest_write": True,
            "agent_prompt_latest_write": True,
        }
    )
    _write_json(audit_path, audit)
    return job_dir


def test_readonly_ops_status_service_returns_daov1_contract(tmp_path):
    payload = _make_service(tmp_path).status()

    assert payload["ok"] is True
    assert payload["schema_version"] == "daov1.readonly_ops_status.v1"
    assert payload["readonly_only"] is True
    assert payload["provider_raw_latest"]["source_max_date"] == "2026-07-20"
    assert payload["provider_raw_latest"]["raw_status"] == "READY"
    assert payload["qlib_accepted_latest"]["asof"] == "2026-07-08"
    assert payload["qlib_accepted_latest"]["separate_from_controlled_signal_latest"] is True
    assert payload["controlled_signal_latest"]["signal_asof"] == "2026-07-17"
    assert payload["readonly_strategy_snapshot_latest"]["target_date"] == "2026-07-17"
    assert payload["agent_prompt_latest"]["checksum"] == "sha256:agent-fixture"
    assert payload["latest_natural_cron_job"]["daily_chain_state"] == "RAW_READY_PROVIDER_STALE"
    assert payload["latest_dapr18_evidence_job"]["asof"] == "2026-07-20"
    assert payload["latest_dapr18_evidence_job"]["dapr18_status"] == "dry_run_plan_recorded"
    assert payload["dapr18_controls"]["dry_run"] is True
    assert payload["dapr18_controls"]["publish_controlled_signal_latest"] is False
    assert payload["dapr18_controls"]["publish_readonly_snapshot_latest"] is False
    assert payload["dapr18_controls"]["publish_agent_prompt_latest"] is False
    assert payload["protected_pointers"]["all_unchanged"] is True
    assert payload["forbidden_actions"]["all_false"] is True
    assert "qlib_provider_view_or_formal_calendar" in payload["next_action_hint"]
    assert "refresh_formal_qlib_provider_view_or_build_validated_canonical_bridge_then_run_model_a_score" in payload["next_action_hint"]
    assert payload["trading"]["orders_enabled"] is False
    assert payload["all_readonly_guards"] is True


def test_persistent_publish_success_overrides_historical_readiness_blockers(tmp_path):
    service = _make_service(tmp_path)
    _configure_persistent_publish(service)

    payload = service.status()

    assert payload["latest_natural_cron_job"]["status"] == "daily_auto_update_passed"
    assert payload["latest_natural_cron_job"]["daily_chain_state"] == "auto_publish_chain_completed"
    assert payload["latest_natural_cron_job"]["blocker"] == {
        "status": "auto_publish_chain_completed",
        "blockers": [],
        "blocked_at": "",
        "reason": "",
    }
    assert "DNG17" not in payload["latest_natural_cron_job"]["next_retry_hint"]
    assert payload["latest_dapr18_evidence_job"]["readiness_state"] == "PUBLISHED"
    assert payload["latest_dapr18_evidence_job"]["blockers"] == []
    assert payload["latest_dapr18_evidence_job"]["product_latest_publish_success"] is True
    assert payload["dapr18_controls"]["product_latest_publish_success"] is True
    assert payload["dapr18_controls"]["latest_pointer_write_performed"] is True
    assert payload["dapr18_controls"]["publish_controlled_signal_latest"] is True
    assert payload["dapr18_controls"]["publish_readonly_snapshot_latest"] is True
    assert payload["dapr18_controls"]["publish_agent_prompt_latest"] is True
    assert "阻塞" not in payload["next_action_hint"]
    assert "DNG17" not in payload["next_action_hint"]
    assert "formal qlib accepted latest 保持独立" in payload["next_action_hint"]
    assert payload["qlib_accepted_latest"]["asof"] == "2026-07-08"
    assert payload["controlled_signal_latest"]["signal_asof"] == "2026-07-20"
    assert payload["qlib_accepted_latest"]["separate_from_controlled_signal_latest"] is True
    assert payload["forbidden_actions"]["all_false"] is False
    assert payload["all_readonly_guards"] is True


def test_publish_summary_does_not_override_blocker_when_current_pointer_mismatches(tmp_path):
    service = _make_service(tmp_path)
    _configure_persistent_publish(service)
    agent = _read_json(service.agent_prompt_latest_path)
    agent["signal_asof"] = "2026-07-19"
    _write_json(service.agent_prompt_latest_path, agent)

    payload = service.status()

    assert payload["latest_dapr18_evidence_job"]["product_latest_publish_success"] is False
    assert payload["latest_natural_cron_job"]["blocker"]["status"] == "BLOCKED_WITH_REASON"
    assert payload["latest_dapr18_evidence_job"]["blockers"]
    assert "阻塞" in payload["next_action_hint"]


def test_detached_older_success_dapr18_evidence_does_not_override_new_natural_job(tmp_path):
    service = _make_service(tmp_path)
    old_dir = _configure_persistent_publish(service)
    fresh_dir = service.ops_root / "daily_tw_stock_auto_update_20260721_20260721T144501Z"
    _write_json(
        fresh_dir / "job.json",
        {
            "job_id": "daily_tw_stock_auto_update_20260721_20260721T144501Z",
            "status": "today_data_window_wait",
            "asof": "2026-07-21",
            "started_at": "2026-07-21T14:45:01+00:00",
            "finished_at": "2026-07-21T14:46:34+00:00",
        },
    )
    _write_json(
        fresh_dir / "daily_chain_status.json",
        {
            "asof": "2026-07-21",
            "job_id": "daily_tw_stock_auto_update_20260721_20260721T144501Z",
            "state": "FRESH_DATA_WAIT",
            "blocked_at": "source_window",
            "blocker_reason": "fresh data window not complete",
            "next_retry_hint": "retry after next data window",
        },
    )

    payload = service.status()

    assert old_dir != fresh_dir
    assert payload["latest_dapr18_evidence_job"]["product_latest_publish_success"] is True
    assert payload["dapr18_controls"]["evidence_bound_to_latest_natural_job"] is False
    assert payload["latest_natural_cron_job"]["job_id"] == "daily_tw_stock_auto_update_20260721_20260721T144501Z"
    assert payload["latest_natural_cron_job"]["daily_chain_state"] == "FRESH_DATA_WAIT"
    assert payload["latest_natural_cron_job"]["blocker"]["status"] == "FRESH_DATA_WAIT"
    assert payload["latest_natural_cron_job"]["blocker"]["blockers"] == []


def test_same_directory_dapr18_job_conflict_does_not_override_natural_job(tmp_path):
    service = _make_service(tmp_path)
    job_dir = _configure_persistent_publish(service)
    job_path = job_dir / "job.json"
    job = _read_json(job_path)
    job["job_id"] = "natural-job-id"
    _write_json(job_path, job)
    summary_path = job_dir / "dapr18_controlled_latest_orchestration_summary.json"
    summary = _read_json(summary_path)
    summary["job_id"] = "different-evidence-id"
    _write_json(summary_path, summary)

    payload = service.status()

    assert payload["latest_dapr18_evidence_job"]["product_latest_publish_success"] is True
    assert payload["dapr18_controls"]["evidence_bound_to_latest_natural_job"] is False
    assert payload["latest_natural_cron_job"]["blocker"]["status"] == "RAW_READY_PROVIDER_STALE"


@pytest.mark.parametrize(
    "summary_update",
    [
        {"dry_run": True},
        {"attempted": False},
        {"exact_authorization_present": False},
        {"publish_controlled_signal_latest": False},
        {"publish_readonly_snapshot_latest": False},
        {"publish_agent_prompt_latest": False},
        {"latest_pointer_write_performed": False},
    ],
)
def test_publish_completion_requires_strict_summary_controls(tmp_path, summary_update):
    service = _make_service(tmp_path)
    job_dir = _configure_persistent_publish(service)
    summary_path = job_dir / "dapr18_controlled_latest_orchestration_summary.json"
    summary = _read_json(summary_path)
    summary.update(summary_update)
    _write_json(summary_path, summary)

    payload = service.status()

    assert payload["latest_dapr18_evidence_job"]["product_latest_publish_success"] is False
    assert payload["latest_natural_cron_job"]["blocker"]["status"] == "BLOCKED_WITH_REASON"


@pytest.mark.parametrize(
    "pointer, field, value",
    [
        ("controlled_signal_latest", "provider_publish", True),
        ("controlled_signal_latest", "qlib_accepted_latest_switch", True),
    ],
)
def test_readonly_guard_fails_for_controlled_pointer_safety_flags(tmp_path, pointer, field, value):
    service = _make_service(tmp_path)
    _configure_persistent_publish(service)
    payload = service.status()
    payload[pointer][field] = value
    assert service._all_readonly_guards(payload) is False


def test_readonly_guard_fails_when_snapshot_is_trade_target_latest(tmp_path):
    service = _make_service(tmp_path)
    _configure_persistent_publish(service)
    payload = service.status()
    payload["readonly_strategy_snapshot_latest"]["validation"]["not_trade_target_latest"] = False
    assert service._all_readonly_guards(payload) is False


@pytest.mark.parametrize(
    "pointer, field, conflicting_field",
    [
        ("controlled_signal_latest", "signal_asof", "asof"),
        ("readonly_strategy_snapshot_latest", "signal_asof", "target_date"),
        ("agent_prompt_latest", "signal_asof", "target_date"),
    ],
)
def test_publish_completion_rejects_conflicting_pointer_dates(tmp_path, pointer, field, conflicting_field):
    service = _make_service(tmp_path)
    _configure_persistent_publish(service)
    path = {
        "controlled_signal_latest": service.controlled_signal_latest_path,
        "readonly_strategy_snapshot_latest": service.readonly_snapshot_latest_path,
        "agent_prompt_latest": service.agent_prompt_latest_path,
    }[pointer]
    doc = _read_json(path)
    doc[field] = "2026-07-19"
    doc[conflicting_field] = "2026-07-20"
    _write_json(path, doc)

    payload = service.status()

    assert payload["latest_dapr18_evidence_job"]["product_latest_publish_success"] is False


@pytest.mark.parametrize(
    "summary_update",
    [
        {"exact_authorization_present": False},
        {"dry_run": True},
        {"ok": False, "status": "failed"},
    ],
)
def test_pointer_write_audit_actions_are_not_exempt_without_authorized_completion(tmp_path, summary_update):
    service = _make_service(tmp_path)
    job_dir = _configure_persistent_publish(service)
    summary_path = job_dir / "dapr18_controlled_latest_orchestration_summary.json"
    summary = _read_json(summary_path)
    summary.update(summary_update)
    _write_json(summary_path, summary)

    payload = service.status()

    assert payload["forbidden_actions"]["actions"]["controlled_signal_latest_write"] is True
    assert payload["all_readonly_guards"] is False


@pytest.mark.parametrize(
    "unsafe_action",
    [
        "provider_or_network_pull",
        "provider_publish",
        "formal_qlib_refresh",
        "accepted_latest_switch",
        "legacy_latest_switch",
        "openai_call",
        "db_write",
        "strategy_replay",
        "monitor_or_broker_or_order_path",
        "order_intent_generation",
        "target_position_or_weight_output",
        "cron_or_daily_automation_default_switch",
        "frontend_api_production_default_switch",
    ],
)
def test_readonly_guard_fails_for_every_non_authorized_action(tmp_path, unsafe_action):
    service = _make_service(tmp_path)
    job_dir = _configure_persistent_publish(service)
    audit_path = job_dir / "dapr18_forbidden_action_audit.json"
    audit = _read_json(audit_path)
    audit["actions"][unsafe_action] = True
    _write_json(audit_path, audit)

    assert service.status()["all_readonly_guards"] is False


def test_readonly_guard_fails_for_unsafe_artifact_or_trading_flags(tmp_path):
    service = _make_service(tmp_path)
    _configure_persistent_publish(service)
    payload = service.status()
    assert payload["all_readonly_guards"] is True

    unsafe_controlled = deepcopy(payload)
    unsafe_controlled["controlled_signal_latest"]["production_trade_enabled"] = True
    assert service._all_readonly_guards(unsafe_controlled) is False

    unsafe_snapshot = deepcopy(payload)
    unsafe_snapshot["readonly_strategy_snapshot_latest"]["validation"]["not_provider_accepted_latest"] = False
    assert service._all_readonly_guards(unsafe_snapshot) is False

    unsafe_agent = deepcopy(payload)
    unsafe_agent["agent_prompt_latest"]["validation"]["readonly_only"] = False
    assert service._all_readonly_guards(unsafe_agent) is False

    unsafe_trading = deepcopy(payload)
    unsafe_trading["trading"]["orders_enabled"] = True
    assert service._all_readonly_guards(unsafe_trading) is False


def test_readonly_ops_status_api_returns_standard_wrapper(client, monkeypatch, tmp_path):
    service = _make_service(tmp_path)
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "readonly_ops_status_service", service)

    resp = client.get("/api/tw-stock/quant/ops/readonly-status")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    assert payload["msg"] == "success"
    data = payload["data"]
    assert data["provider_raw_latest"]["source_max_date"] == "2026-07-20"
    assert data["latest_natural_cron_job"]["job_id"] == "daily_tw_stock_auto_update_20260720_20260720T144501Z"
    assert data["latest_dapr18_evidence_job"]["job_id"] == "daily_tw_stock_auto_update_20260720_20260720T144501Z"
    assert data["forbidden_actions"]["all_false"] is True


def test_readonly_ops_status_static_safety_contract():
    service_source = Path("backend/app/services/tw_stock_readonly_ops_status.py").read_text(encoding="utf-8")
    route_source = Path("backend/app/routes/tw_stock.py").read_text(encoding="utf-8")
    route_slice = route_source.split('@tw_stock_bp.route("/quant/ops/readonly-status"', 1)[1].split(
        '@tw_stock_bp.route("/quant/ops/option-c/scheduler"', 1
    )[0]

    assert 'methods=["GET"]' in route_slice
    assert "readonly_ops_status_service.status()" in route_slice
    assert "TWStockReadonlyOpsStatusService" in route_source
    forbidden_tokens = [
        "run_daily_tw_stock_auto_update",
        "refresh_provider",
        "provider_publish(",
        "accepted_latest_scheduler.tick",
        "OpenAI(",
        "get_db_connection(",
        "monitor_service.save",
    ]
    for token in forbidden_tokens:
        assert token not in service_source
        assert token not in route_slice
    assert "target_position/target_weight" in service_source
    assert "target_position" not in route_slice
    assert "target_weight" not in route_slice
