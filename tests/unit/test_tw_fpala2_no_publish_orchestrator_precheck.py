from __future__ import annotations

import json
from pathlib import Path

from scripts.build_tw_fpala2_no_publish_orchestrator_precheck import (
    FPALAFlags,
    FPALAPaths,
    build_decision,
    compute_today_wait,
    parse_hhmm,
    parse_taipei_datetime,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_calendar(path: Path, max_asof: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"2026-08-01\n{max_asof}\n", encoding="utf-8")


def base_flags(**kwargs) -> FPALAFlags:
    values = {
        "enabled": True,
        "no_publish": True,
        "allow_formal_provider_publish": False,
        "allow_accepted_latest_switch": False,
        "exact_authorization_id": "",
    }
    values.update(kwargs)
    return FPALAFlags(**values)


def candidate_payload(**kwargs) -> dict:
    payload = {
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
        "forbidden_actions": {"accepted_latest_switch": False, "formal_publish": False},
    }
    payload.update(kwargs)
    return payload


def make_paths(tmp_path: Path, *, calendar_max: str = "2026-08-07", accepted_asof: str = "2026-08-07", with_candidate: bool = True, candidate: dict | None = None, accepted_payload: bool = False) -> FPALAPaths:
    write_calendar(tmp_path / "formal/calendars/day.txt", calendar_max)
    write_json(tmp_path / "qlib_latest.json", {"asof": accepted_asof, "run_dir": f"run_{accepted_asof}"})
    write_json(tmp_path / "legacy_latest.json", {"asof": "2026-06-01"})
    write_json(tmp_path / "signal_latest.json", {"asof": "2026-08-06", "signal_asof": "2026-08-06"})
    write_json(tmp_path / "snapshot_latest.json", {"asof": "2026-08-06", "signal_asof": "2026-08-06"})
    write_json(tmp_path / "agent_latest.json", {"signal_asof": "2026-08-06"})
    (tmp_path / "cron").write_text("SHELL=/bin/bash\n", encoding="utf-8")
    candidate_root = tmp_path / "candidates"
    if with_candidate:
        cdir = candidate_root / "daily_auto_provider_candidate_20260807_test"
        write_json(cdir / "provider_candidate_readiness.json", candidate or candidate_payload())
    accepted_payload_path = tmp_path / "accepted_payload/run_2026-08-07"
    if accepted_payload:
        accepted_payload_path.mkdir(parents=True)
    return FPALAPaths(
        root=tmp_path,
        output_root=tmp_path / "out",
        candidate_root=candidate_root,
        formal_provider_calendar=tmp_path / "formal/calendars/day.txt",
        qlib_accepted_latest=tmp_path / "qlib_latest.json",
        legacy_latest=tmp_path / "legacy_latest.json",
        dapr18_signal_latest=tmp_path / "signal_latest.json",
        readonly_snapshot_latest=tmp_path / "snapshot_latest.json",
        agent_prompt_latest=tmp_path / "agent_latest.json",
        installed_cron=tmp_path / "cron",
        pending_asof=tmp_path / "pending_asof.json",
        accepted_payload_path=accepted_payload_path if accepted_payload else None,
    )


def status(tmp_path: Path, *, paths: FPALAPaths | None = None, flags: FPALAFlags | None = None, target: str = "2026-08-07") -> str:
    decision = build_decision(
        target_asof=target,
        job_id="test",
        paths=paths or make_paths(tmp_path),
        flags=flags or base_flags(),
    )
    return str(decision["status"])


def test_disabled_flag_returns_disabled_by_default(tmp_path: Path) -> None:
    assert status(tmp_path, flags=base_flags(enabled=False)) == "disabled_by_default"


def test_aligned_formal_provider_and_accepted_latest_returns_idempotent(tmp_path: Path) -> None:
    assert status(tmp_path) == "already_aligned_idempotent_noop"


def test_valid_candidate_stale_formal_provider_returns_candidate_ready_no_publish_alias(tmp_path: Path) -> None:
    paths = make_paths(tmp_path, calendar_max="2026-08-06", accepted_asof="2026-08-06")
    decision = build_decision(target_asof="2026-08-07", job_id="test", paths=paths, flags=base_flags())
    assert decision["candidate_contract"]["validation"]["ok"] is True
    assert decision["status"] == "candidate_ready_no_publish"
    assert decision["formal_provider_contract"]["would_publish_if_authorized"] is True


def test_valid_candidate_stale_formal_provider_provider_preflight_ready_no_publish(tmp_path: Path) -> None:
    paths = make_paths(tmp_path, calendar_max="2026-08-06", accepted_asof="2026-08-06")
    flags = base_flags(allow_formal_provider_publish=True, exact_authorization_id="FPALA_TEST_AUTH")
    assert status(tmp_path, paths=paths, flags=flags) == "provider_publish_preflight_ready_no_publish"


def test_formal_provider_stale_blocks_accepted_latest_preflight(tmp_path: Path) -> None:
    paths = make_paths(tmp_path, calendar_max="2026-08-06", accepted_asof="2026-08-06", accepted_payload=True)
    decision = build_decision(target_asof="2026-08-07", job_id="test", paths=paths, flags=base_flags())
    assert decision["accepted_latest_contract"]["switch_preflight_status"] == "blocked_formal_provider_not_ready"


def test_formal_provider_ready_accepted_latest_stale_payload_missing(tmp_path: Path) -> None:
    paths = make_paths(tmp_path, calendar_max="2026-08-07", accepted_asof="2026-08-06", accepted_payload=False)
    assert status(tmp_path, paths=paths) == "blocked_accepted_payload_missing"


def test_accepted_latest_preflight_ready_but_switch_not_authorized(tmp_path: Path) -> None:
    paths = make_paths(tmp_path, calendar_max="2026-08-07", accepted_asof="2026-08-06", accepted_payload=True)
    assert status(tmp_path, paths=paths) == "accepted_latest_preflight_ready_no_publish"


def test_mutation_requested_without_exact_authorization_blocks(tmp_path: Path) -> None:
    paths = make_paths(tmp_path, calendar_max="2026-08-07", accepted_asof="2026-08-06", accepted_payload=True)
    assert status(tmp_path, paths=paths, flags=base_flags(allow_accepted_latest_switch=True)) == "blocked_requires_exact_authorization"


def test_missing_candidate_blocks(tmp_path: Path) -> None:
    paths = make_paths(tmp_path, calendar_max="2026-08-06", accepted_asof="2026-08-06", with_candidate=False)
    assert status(tmp_path, paths=paths) == "blocked_candidate_missing"


def test_already_aligned_does_not_require_provider_candidate(tmp_path: Path) -> None:
    paths = make_paths(tmp_path, with_candidate=False)
    assert status(tmp_path, paths=paths) == "already_aligned_idempotent_noop"


def test_invalid_candidate_coverage_blocks(tmp_path: Path) -> None:
    paths = make_paths(tmp_path, calendar_max="2026-08-06", accepted_asof="2026-08-06", candidate=candidate_payload(candidate_normalized_symbols_success=149))
    assert status(tmp_path, paths=paths) == "blocked_candidate_invalid"


def test_candidate_asof_mismatch_blocks(tmp_path: Path) -> None:
    paths = make_paths(tmp_path, calendar_max="2026-08-06", accepted_asof="2026-08-06", candidate=candidate_payload(candidate_asof="2026-08-06"))
    decision = build_decision(target_asof="2026-08-07", job_id="test", paths=paths, flags=base_flags())
    assert decision["status"] == "blocked_candidate_invalid"
    assert "candidate_asof_mismatch" in decision["candidate_contract"]["validation"]["errors"]


def test_staged_provider_calendar_missing_target_asof_blocks(tmp_path: Path) -> None:
    paths = make_paths(tmp_path, calendar_max="2026-08-06", accepted_asof="2026-08-06", candidate=candidate_payload(staged_provider_calendar_has_asof=False))
    decision = build_decision(target_asof="2026-08-07", job_id="test", paths=paths, flags=base_flags())
    assert decision["status"] == "blocked_candidate_invalid"
    assert "staged_provider_calendar_missing_target_asof" in decision["candidate_contract"]["validation"]["errors"]


def test_forbidden_action_true_blocks(tmp_path: Path) -> None:
    paths = make_paths(tmp_path, candidate=candidate_payload(forbidden_actions={"accepted_latest_switch": True}))
    assert status(tmp_path, paths=paths) == "blocked_forbidden_scope_violation"


def test_pending_asof_returns_pending_retry_wait(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    write_json(tmp_path / "pending_asof.json", {"pending_asof": "2026-08-07", "reason": "fresh_data_wait"})
    assert status(tmp_path, paths=paths) == "pending_retry_wait"


def test_today_data_window_wait_direct_flag(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    decision = build_decision(target_asof="2026-08-07", job_id="test", paths=paths, flags=base_flags(), today_wait=True)
    assert decision["status"] == "today_data_window_wait"


def test_today_data_window_wait_time_calculation() -> None:
    taipei_now = parse_taipei_datetime("2026-08-07T19:30:00+08:00")
    assert compute_today_wait("2026-08-07", taipei_now=taipei_now, wait_until=parse_hhmm("20:30"), enabled=True) is True
    assert compute_today_wait("2026-08-06", taipei_now=taipei_now, wait_until=parse_hhmm("20:30"), enabled=True) is False
    assert compute_today_wait("2026-08-07", taipei_now=taipei_now, wait_until=parse_hhmm("18:00"), enabled=True) is False
