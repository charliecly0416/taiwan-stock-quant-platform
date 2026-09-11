from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.tw_daily_runtime_stages import (
    build_authorized_readonly_publish_terminal,
    RuntimeDescriptorError,
    build_legacy_observation_terminal,
    build_stage_terminal_contract,
    build_stage_facade,
    load_runtime_descriptor,
    run_stage_orchestrator,
    runtime_truth,
)


def _publish_terminal_fixture(*, noop: bool = False, drift: str | None = None) -> tuple[dict, dict, dict]:
    before = {
        name: {"exists": True, "size": 1, "sha256": f"before-{name}"}
        for name in (
            "readonly_snapshot_latest",
            "agent_prompt_latest",
            "provider_accepted_latest",
            "legacy_option_c_latest",
        )
    }
    after = {name: dict(value) for name, value in before.items()}
    if not noop:
        after["readonly_snapshot_latest"]["sha256"] = "after-readonly"
        after["agent_prompt_latest"]["sha256"] = "after-agent"
    if drift:
        after[drift]["sha256"] = f"drift-{drift}"
    status = "auto_publish_idempotent_noop_already_current" if noop else "auto_publish_chain_completed"
    chain_status = "idempotent_noop" if noop else "pass"
    orchestration = {
        "ok": True,
        "status": status,
        "authorization_gate": {"allowed": True, "authorization_id_present": True},
        "auto_publish_chain": {"ok": True, "status": chain_status},
        "product_latest_state_after": {"all_product_latest_match_target": True, "target_asof": "2026-09-10"},
        "forbidden_protected_paths_unchanged": True,
        "forbidden_actions_all_false": True,
    }
    return orchestration, before, after


def test_authorized_readonly_publish_terminal_accepts_success_and_noop() -> None:
    for noop in (False, True):
        orchestration, before, after = _publish_terminal_fixture(noop=noop)
        result = build_authorized_readonly_publish_terminal(
            asof="2026-09-10",
            job_id="dapr18",
            orchestration=orchestration,
            protected_before=before,
            protected_after=after,
            trading={"orders_enabled": False, "connects_to_broker": False, "research_signal_not_order": True},
        )
        assert result["ok"] is True
        assert result["publish_allowed"] is True
        assert result["resolution_status"] in {"authorized_publish_completed", "idempotent_noop_already_current"}
        assert result["protected_fingerprint_audit"]["provider_accepted_latest_unchanged"] is True
        assert result["protected_fingerprint_audit"]["legacy_option_c_latest_unchanged"] is True
        assert result["artifact_publish_calls"] == (0 if noop else 1)


def test_authorized_readonly_publish_terminal_rejects_forbidden_drift() -> None:
    orchestration, before, after = _publish_terminal_fixture(drift="provider_accepted_latest")
    result = build_authorized_readonly_publish_terminal(
        asof="2026-09-10",
        job_id="dapr18",
        orchestration=orchestration,
        protected_before=before,
        protected_after=after,
        trading={"orders_enabled": False, "connects_to_broker": False, "research_signal_not_order": True},
    )
    assert result["ok"] is False
    assert result["status"] == "authorized_readonly_product_publish_audit_failed"
    assert "provider_accepted_latest" in result["protected_fingerprint_audit"]["unexpected_changes"]


def test_stage_terminal_contract_normalizes_observation_only_result() -> None:
    result = build_stage_terminal_contract(
        {
            "ok": False,
            "status": "publish_precondition_blocked",
            "failed_stage": "artifact_publish",
            "publish_allowed": False,
            "stage_calls": {
                "acquisition": 1,
                "readiness": 1,
                "signal": 1,
                "strategy": 1,
                "artifact_publish": 0,
                "ops_status": 0,
            },
            "stages": [{"name": name} for name in ("acquisition", "readiness", "signal", "strategy")],
        },
        asof="2026-09-04",
        job_id="parity",
    )
    assert result["schema_version"] == "arch5.runtime_stage_terminal.v1"
    assert result["status"] == "publish_precondition_blocked"
    assert result["failed_stage"] == "artifact_publish"
    assert result["stage_order"] == ["acquisition", "readiness", "signal", "strategy"]
    assert result["artifact_publish_calls"] == 0
    assert result["ops_status_calls"] == 0


def test_legacy_observation_terminal_matches_fail_closed_publish_boundary(tmp_path: Path) -> None:
    protected = tmp_path / "latest.json"
    protected.write_text("before", encoding="utf-8")
    snapshot = {"latest": {"path": str(protected), "exists": True, "size": 6, "sha256": "same"}}
    result = build_legacy_observation_terminal(
        asof="2026-09-04",
        job_id="legacy",
        protected_before=snapshot,
        protected_after=snapshot,
    )
    assert result["status"] == "publish_precondition_blocked"
    assert result["failed_stage"] == "artifact_publish"
    assert result["publish_allowed"] is False
    assert result["stage_calls"]["artifact_publish"] == 0
    assert result["stage_calls"]["ops_status"] == 0
    assert result["protected_fingerprint_audit"]["ok"] is True
    assert result["legacy_top_level_status"] == "daily_auto_update_passed"


def test_runtime_defaults_are_descriptor_backed() -> None:
    defaults = runtime_truth().defaults()
    assert defaults == {
        "model_id": "e4_frozen_qlib_2018_2022",
        "strategy_rule": "top50_exit_one_worst_sell",
        "execution_price_mode": "next_open",
        "shadow_model_id": "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025",
    }


@pytest.mark.parametrize(
    "mutator",
    [
        lambda p: p.update({"unknown": True}),
        lambda p: p["shadow_models"][0]["artifacts"]["canonical_model"].update({"sha256": "bad"}),
        lambda p: p["shadow_models"][0]["allowed_consumers"].append("production"),
        lambda p: p["shadow_models"][0]["artifacts"]["canonical_model"].pop("path"),
    ],
)
def test_descriptor_mutations_fail_closed(tmp_path: Path, mutator) -> None:
    descriptor = load_runtime_descriptor()
    mutator(descriptor)
    path = tmp_path / "descriptor.yaml"
    path.write_text(yaml.safe_dump(descriptor, sort_keys=False), encoding="utf-8")
    with pytest.raises(RuntimeDescriptorError):
        load_runtime_descriptor(descriptor_path=path)


def test_orchestrator_preserves_order_and_audits_actual_callbacks(tmp_path: Path) -> None:
    order: list[str] = []
    protected = tmp_path / "latest.json"
    protected.write_text("{}", encoding="utf-8")

    def callback(name: str):
        def run(context):
            order.append(name)
            return {"ok": True, "stage": name, "context": context}
        return run

    stages = build_stage_facade(**{name: callback(name) for name in ("acquisition", "readiness", "signal", "strategy", "artifact_publish", "ops_status")})
    result = run_stage_orchestrator(
        stages,
        protected_paths={"latest": protected},
        root=tmp_path,
        publish_precondition=lambda context: {"ok": True, "reason": "test_explicit_gate"},
    )
    assert result["ok"] is True
    assert order == ["acquisition", "readiness", "signal", "strategy", "artifact_publish", "ops_status"]
    assert result["protected_fingerprint_audit"]["ok"] is True


def test_orchestrator_requires_publish_precondition() -> None:
    called: list[str] = []
    stages = build_stage_facade(
        acquisition=lambda context: {"ok": True},
        readiness=lambda context: {"ok": True},
        signal=lambda context: {"ok": True},
        strategy=lambda context: {"ok": True},
        artifact_publish=lambda context: called.append("publish") or {"ok": True},
        ops_status=lambda context: called.append("ops") or {"ok": True},
    )
    result = run_stage_orchestrator(stages)
    assert result["ok"] is False
    assert result["status"] == "publish_precondition_missing"
    assert result["publish_allowed"] is False
    assert called == []


def test_orchestrator_blocks_on_stage_failure() -> None:
    order: list[str] = []

    def fail(context):
        order.append("readiness")
        return {"ok": False, "status": "blocked"}

    stages = build_stage_facade(
        acquisition=lambda context: order.append("acquisition") or {"ok": True},
        readiness=fail,
        signal=lambda context: order.append("signal") or {"ok": True},
    )
    result = run_stage_orchestrator(stages)
    assert result["ok"] is False
    assert result["failed_stage"] == "readiness"
    assert order == ["acquisition", "readiness"]


def test_orchestrator_recaptures_paths_from_serialized_before(tmp_path: Path) -> None:
    protected = tmp_path / "latest.json"
    protected.write_text("before", encoding="utf-8")
    before = {"latest": {"path": str(protected), "exists": True, "size": 6, "sha256": "stale"}}

    def mutate(context):
        protected.write_text("after", encoding="utf-8")
        return {"ok": True}

    stages = build_stage_facade(
        acquisition=lambda context: {"ok": True},
        readiness=lambda context: {"ok": True},
        signal=lambda context: {"ok": True},
        strategy=lambda context: {"ok": True},
        artifact_publish=mutate,
        ops_status=lambda context: {"ok": True},
    )
    result = run_stage_orchestrator(
        stages,
        protected_before=before,
        root=tmp_path,
        publish_precondition=lambda context: {"ok": True, "reason": "test_explicit_gate"},
    )
    assert result["ok"] is False
    assert result["status"] == "protected_path_changed"
    assert result["protected_fingerprint_audit"]["comparison"]["latest"] is False


def test_publish_precondition_blocks_callback_and_ops_status(tmp_path: Path) -> None:
    protected = tmp_path / "latest.json"
    protected.write_text("before", encoding="utf-8")
    called: list[str] = []

    def publish(context):
        called.append("publish")
        protected.write_text("should-not-happen", encoding="utf-8")
        return {"ok": True}

    def ops(context):
        called.append("ops")
        return {"ok": True}

    stages = build_stage_facade(
        acquisition=lambda context: {"ok": True},
        readiness=lambda context: {"ok": True},
        signal=lambda context: {"ok": True},
        strategy=lambda context: {"ok": True},
        artifact_publish=publish,
        ops_status=ops,
    )
    result = run_stage_orchestrator(
        stages,
        protected_paths={"latest": protected},
        root=tmp_path,
        publish_precondition=lambda context: {"ok": False, "reason": "no_publish_mode"},
    )
    assert result["ok"] is False
    assert result["status"] == "publish_precondition_blocked"
    assert result["publish_allowed"] is False
    assert called == []
    assert protected.read_text(encoding="utf-8") == "before"
