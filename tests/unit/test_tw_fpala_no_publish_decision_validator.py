from __future__ import annotations

from scripts.validate_tw_fpala_no_publish_decision import validate_decision


def valid_decision(**overrides):
    payload = {
        "schema_version": "fpala.formal_accepted_latest_automation_decision.v1",
        "created_at": "2026-08-07T00:00:00+00:00",
        "job_id": "unit",
        "target_asof": "2026-08-07",
        "status": "already_aligned_idempotent_noop",
        "ok": True,
        "message": "aligned",
        "next_retry_hint": "",
        "recommended_next_action": "no_action",
        "flags": {
            "enabled": True,
            "no_publish": True,
            "allow_formal_provider_publish": False,
            "allow_accepted_latest_switch": False,
            "exact_authorization_present": False,
            "exact_authorization_id": "",
            "legacy_provider_publish_enabled": False,
            "dapr18_authorization_present": False,
        },
        "candidate_contract": {
            "candidate_dir": "qlib_pipeline/data_tw/experiments/daily_auto_provider_candidates/daily_auto_provider_candidate_20260807_unit",
            "candidate_asof": "2026-08-07",
            "staged_provider_calendar_max": "2026-08-07",
            "staged_provider_calendar_has_asof": True,
            "candidate_normalized_symbols_expected": 150,
            "candidate_normalized_symbols_success": 150,
            "candidate_normalized_symbols_with_asof": 150,
            "staged_provider_validation_status": "pass",
            "candidate_model_smoke_status": "pass",
            "production_allowed": False,
            "publish_latest_authorized": False,
            "formal_provider_mutated": False,
            "formal_normalized_mutated": False,
            "latest_signal_updated": False,
            "forbidden_actions": {"formal_publish": False, "accepted_latest_switch": False},
            "validation": {
                "ok": True,
                "missing": False,
                "invalid": False,
                "forbidden_violation": False,
                "errors": [],
            },
        },
        "formal_provider_contract": {
            "formal_provider_path": "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin",
            "calendar_path": "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt",
            "calendar_max_before": "2026-08-07",
            "calendar_hash_before": "abc",
            "expected_target_asof": "2026-08-07",
            "formal_provider_covers_target": True,
            "publish_preflight_status": "not_required_already_covers_target",
            "publish_allowed_by_flags": False,
            "would_publish_if_authorized": False,
        },
        "accepted_latest_contract": {
            "accepted_latest_pointer_path": "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
            "current_asof": "2026-08-07",
            "current_run_id": "run_20260807",
            "current_hash": "def",
            "target_asof": "2026-08-07",
            "target_run_id": "",
            "candidate_payload_path": "",
            "candidate_payload_exists": False,
            "formal_provider_covers_target": True,
            "switch_preflight_status": "not_required_already_aligned",
            "switch_allowed_by_flags": False,
            "would_switch_if_authorized": False,
        },
        "protected_pointer_fingerprints": {
            "formal_provider_calendar": {"exists": True, "sha256": "1"},
            "qlib_accepted_latest": {"exists": True, "sha256": "2"},
            "legacy_latest": {"exists": True, "sha256": "3"},
            "dapr18_signal_latest": {"exists": True, "sha256": "4"},
            "readonly_snapshot_latest": {"exists": True, "sha256": "5"},
            "agent_prompt_latest": {"exists": True, "sha256": "6"},
            "installed_cron": {"exists": True, "sha256": "7"},
        },
        "forbidden_scope_audit": {
            "all_false": True,
            "actions": {"provider_publish": False, "qlib_accepted_latest_switch": False},
        },
        "status_evidence": {
            "current_accepted_latest_asof": "2026-08-07",
            "formal_provider_calendar_max": "2026-08-07",
            "candidate_validation_errors": [],
            "pending_asof": "",
            "today_wait": False,
        },
    }
    for key, value in overrides.items():
        payload[key] = value
    return payload


def assert_invalid(payload, code: str) -> None:
    report = validate_decision(payload)
    assert report["ok"] is False
    assert code in {item["code"] for item in report["errors"]}


def test_valid_enabled_no_publish_aligned_decision_passes() -> None:
    report = validate_decision(valid_decision(), target_asof="2026-08-07", expect_status="already_aligned_idempotent_noop")
    assert report["ok"] is True


def test_valid_default_disabled_decision_passes() -> None:
    payload = valid_decision(status="disabled_by_default")
    payload["flags"]["enabled"] = False
    report = validate_decision(payload, expect_status="disabled_by_default")
    assert report["ok"] is True


def test_missing_required_field_fails() -> None:
    payload = valid_decision()
    payload.pop("candidate_contract")
    assert_invalid(payload, "missing_top_level_fields")


def test_forbidden_audit_false_violation_fails() -> None:
    payload = valid_decision()
    payload["forbidden_scope_audit"]["all_false"] = False
    payload["forbidden_scope_audit"]["actions"]["provider_publish"] = True
    assert_invalid(payload, "forbidden_scope_audit_not_all_false")
    assert_invalid(payload, "forbidden_scope_action_true")


def test_publish_allowed_without_exact_authorization_fails() -> None:
    payload = valid_decision()
    payload["flags"]["allow_formal_provider_publish"] = True
    assert_invalid(payload, "mutation_flag_without_exact_authorization")


def test_unknown_status_fails() -> None:
    assert_invalid(valid_decision(status="invented_status"), "unknown_status")


def test_missing_protected_pointer_fingerprint_fails() -> None:
    payload = valid_decision()
    payload["protected_pointer_fingerprints"].pop("installed_cron")
    assert_invalid(payload, "missing_protected_pointer_fingerprints")


def test_candidate_asof_mismatch_fails() -> None:
    payload = valid_decision()
    payload["candidate_contract"]["candidate_asof"] = "2026-08-06"
    assert_invalid(payload, "candidate_asof_mismatch")


def test_candidate_calendar_has_asof_false_fails_when_candidate_valid() -> None:
    payload = valid_decision()
    payload["candidate_contract"]["staged_provider_calendar_has_asof"] = False
    assert_invalid(payload, "candidate_calendar_missing_target_asof")


def test_dapr18_authorization_id_cannot_be_used_as_fpala_exact_auth() -> None:
    payload = valid_decision()
    payload["flags"]["allow_accepted_latest_switch"] = True
    payload["flags"]["exact_authorization_present"] = True
    payload["flags"]["exact_authorization_id"] = "DAPR18_AUTO_PUBLISH_CHAIN_CRON_20260728"
    assert_invalid(payload, "dapr18_authorization_misused_for_fpala")
