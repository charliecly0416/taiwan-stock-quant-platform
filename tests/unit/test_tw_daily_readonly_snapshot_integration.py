from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import run_daily_tw_stock_auto_update as daily


def write_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def command_result(stdout_path: Path, payload: dict, *, ok: bool = True) -> dict:
    write_payload(stdout_path, payload)
    return {
        "ok": ok,
        "returncode": 0 if ok else 2,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stdout_path.with_suffix(".stderr")),
    }


def test_switch_off_does_not_call_writer(tmp_path: Path) -> None:
    calls = []

    def runner(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("writer must not be called when switch is off")

    result = daily.run_readonly_strategy_snapshot_publish(
        asof="2026-06-16",
        job_dir=tmp_path,
        enabled=False,
        command_runner=runner,
    )

    assert result["enabled"] is False
    assert result["attempted"] is False
    assert result["ok"] is True
    assert calls == []


def test_success_dry_run_calls_writer_and_validator_without_latest_update(tmp_path: Path) -> None:
    calls = []
    manifest = tmp_path / "snapshot" / "manifest.json"
    write_payload(manifest, {"asof": "2026-06-16"})

    def runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        calls.append(argv)
        if "--manifest" in argv:
            return command_result(stdout_path, {"ok": True})
        return command_result(stdout_path, {"ok": True, "manifest": str(manifest)})

    result = daily.run_readonly_strategy_snapshot_publish(
        asof="2026-06-16",
        job_dir=tmp_path / "job",
        enabled=True,
        dry_run=True,
        command_runner=runner,
    )

    assert result["ok"] is True
    assert result["attempted"] is True
    assert result["validator_ok"] is True
    assert result["latest_updated"] is False
    assert len(calls) == 2
    assert "--no-latest" in calls[0]
    assert "--manifest" in calls[1]


def test_success_non_dry_run_updates_latest_after_manifest_validator(monkeypatch, tmp_path: Path) -> None:
    calls = []
    latest_written = []
    manifest = tmp_path / "snapshot" / "manifest.json"
    out_root = tmp_path / "readonly_root"
    write_payload(manifest, {"asof": "2026-06-16"})

    def fake_write_latest(manifest_path: Path, *, out_root: Path):
        latest_written.append((manifest_path, out_root))
        latest = out_root / "latest.json"
        write_payload(latest, {"snapshot_manifest": str(manifest_path)})
        return latest

    def runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        calls.append(argv)
        if "--latest" in argv:
            return command_result(stdout_path, {"ok": True})
        if "--manifest" in argv:
            assert latest_written == []
            return command_result(stdout_path, {"ok": True})
        return command_result(stdout_path, {"ok": True, "manifest": str(manifest)})

    monkeypatch.setattr(daily, "write_readonly_snapshot_latest_pointer", fake_write_latest)
    result = daily.run_readonly_strategy_snapshot_publish(
        asof="2026-06-16",
        job_dir=tmp_path / "job",
        enabled=True,
        dry_run=False,
        out_root=out_root,
        command_runner=runner,
    )

    assert result["ok"] is True
    assert result["latest_updated"] is True
    assert latest_written == [(manifest, out_root)]
    assert "--latest" in calls[-1]


def test_writer_failure_is_isolated_and_skips_validator(tmp_path: Path) -> None:
    calls = []

    def runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        calls.append(argv)
        return command_result(stdout_path, {"ok": False}, ok=False)

    result = daily.run_readonly_strategy_snapshot_publish(
        asof="2026-06-16",
        job_dir=tmp_path,
        enabled=True,
        dry_run=False,
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["error"] == "readonly snapshot writer failed"
    assert result["latest_updated"] is False
    assert len(calls) == 1


def test_validator_failure_does_not_update_latest(monkeypatch, tmp_path: Path) -> None:
    manifest = tmp_path / "snapshot" / "manifest.json"
    write_payload(manifest, {"asof": "2026-06-16"})

    def fail_if_latest_written(*args, **kwargs):
        raise AssertionError("latest pointer must not be updated after validator failure")

    def runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        if "--manifest" in argv:
            return command_result(stdout_path, {"ok": False}, ok=False)
        return command_result(stdout_path, {"ok": True, "manifest": str(manifest)})

    monkeypatch.setattr(daily, "write_readonly_snapshot_latest_pointer", fail_if_latest_written)
    result = daily.run_readonly_strategy_snapshot_publish(
        asof="2026-06-16",
        job_dir=tmp_path / "job",
        enabled=True,
        dry_run=False,
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["error"] == "readonly snapshot validator failed"
    assert result["validator_ok"] is False
    assert result["latest_updated"] is False


def test_r16_added_daily_integration_static_scan() -> None:
    source = (ROOT / "scripts/run_daily_tw_stock_auto_update.py").read_text(encoding="utf-8")
    start = source.index("def run_readonly_strategy_snapshot_publish")
    end = source.index("def run_strict_e4_readonly_chain")
    block = source[start:end]

    required = [
        "ENABLE_TW_READONLY_STRATEGY_SNAPSHOT_PUBLISH",
        "TW_READONLY_STRATEGY_SNAPSHOT_DRY_RUN",
        "READONLY_PUBLISH_SCRIPT",
        "READONLY_VALIDATE_SCRIPT",
        "--no-latest",
        "write_readonly_snapshot_latest_pointer",
    ]
    forbidden = [
        "quick-trade",
        "quickTrade",
        "/api/broker/",
        "submitOrder",
        "placeOrder",
        "connectBroker",
        "order_action",
        "target_position",
        "target_weight",
        "provider_publish",
        "provider refresh",
        "accepted_latest_switch",
        "saveTwStockMonitorConfig",
        "scanTwStockMonitor",
        "updateTwStockAlert",
    ]

    assert all(marker in source for marker in required)
    assert not [pattern for pattern in forbidden if pattern in block]


def write_ador_latest_inputs(tmp_path: Path, *, asof: str = "2026-07-08") -> dict[str, Path]:
    readonly_manifest = tmp_path / "readonly" / asof / "manifest.json"
    agent_manifest = tmp_path / "agent" / asof / "manifest.json"
    readonly_latest = tmp_path / "readonly" / "latest.json"
    agent_latest = tmp_path / "agent" / "latest.json"
    provider_latest = tmp_path / "provider_latest.json"
    legacy_latest = tmp_path / "legacy_latest.json"
    write_payload(readonly_manifest, {"asof": asof})
    write_payload(agent_manifest, {"signal_asof": asof})
    write_payload(
        readonly_latest,
        {
            "signal_asof": asof,
            "snapshot_manifest": str(readonly_manifest),
            "readonly_only": True,
            "production_trade_enabled": False,
        },
    )
    write_payload(
        agent_latest,
        {
            "signal_asof": asof,
            "manifest": str(agent_manifest),
            "source_readonly_snapshot_latest": daily.rel_path(readonly_latest),
            "readonly_only": True,
            "production_trade_enabled": False,
        },
    )
    write_payload(provider_latest, {"asof": asof})
    write_payload(legacy_latest, {"asof": asof})
    return {
        "readonly_latest": readonly_latest,
        "agent_latest": agent_latest,
        "provider_latest": provider_latest,
        "legacy_latest": legacy_latest,
    }


def test_ador_default_disabled_does_not_write_evidence_or_latest(tmp_path: Path) -> None:
    paths = write_ador_latest_inputs(tmp_path)
    before_readonly = daily.file_fingerprint(paths["readonly_latest"])
    before_agent = daily.file_fingerprint(paths["agent_latest"])
    job_dir = tmp_path / "job"

    result = daily.run_ador_no_publish_orchestration_dry_run(
        asof="2026-07-08",
        job_dir=job_dir,
        job_id="unit",
        enabled=False,
        readonly_latest_path=paths["readonly_latest"],
        agent_latest_path=paths["agent_latest"],
        provider_latest_path=paths["provider_latest"],
        legacy_latest_path=paths["legacy_latest"],
    )

    assert result["enabled"] is False
    assert result["attempted"] is False
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert not (job_dir / "ador_no_publish_orchestration_summary.json").exists()
    assert daily.file_fingerprint(paths["readonly_latest"])["sha256"] == before_readonly["sha256"]
    assert daily.file_fingerprint(paths["agent_latest"])["sha256"] == before_agent["sha256"]


def test_ador_explicit_dry_run_writes_only_job_dir_evidence(tmp_path: Path) -> None:
    paths = write_ador_latest_inputs(tmp_path)
    before = {
        "readonly": daily.file_fingerprint(paths["readonly_latest"])["sha256"],
        "agent": daily.file_fingerprint(paths["agent_latest"])["sha256"],
    }
    job_dir = tmp_path / "job"

    result = daily.run_ador_no_publish_orchestration_dry_run(
        asof="2026-07-08",
        job_dir=job_dir,
        job_id="unit",
        job={"job_id": "unit", "asof": "2026-07-08"},
        enabled=True,
        dry_run=True,
        readonly_latest_path=paths["readonly_latest"],
        agent_latest_path=paths["agent_latest"],
        provider_latest_path=paths["provider_latest"],
        legacy_latest_path=paths["legacy_latest"],
    )

    assert result["enabled"] is True
    assert result["attempted"] is True
    assert result["ok"] is True
    assert result["job_dir_only_evidence"] is True
    assert result["latest_pointer_write_performed"] is False
    assert result["source_readiness_state"] == "READY_FOR_NO_WRITE_PLAN"
    for evidence_path in result["evidence_paths"].values():
        assert Path(evidence_path).exists()
        assert str(Path(evidence_path)).startswith(str(job_dir))
    assert daily.file_fingerprint(paths["readonly_latest"])["sha256"] == before["readonly"]
    assert daily.file_fingerprint(paths["agent_latest"])["sha256"] == before["agent"]


def test_ador_records_protected_path_fingerprints_before_after(tmp_path: Path) -> None:
    paths = write_ador_latest_inputs(tmp_path)
    job_dir = tmp_path / "job"

    result = daily.run_ador_no_publish_orchestration_dry_run(
        asof="2026-07-08",
        job_dir=job_dir,
        job_id="unit",
        enabled=True,
        readonly_latest_path=paths["readonly_latest"],
        agent_latest_path=paths["agent_latest"],
        provider_latest_path=paths["provider_latest"],
        legacy_latest_path=paths["legacy_latest"],
    )
    fingerprint_path = Path(result["evidence_paths"]["protected_paths_fingerprint"])
    payload = json.loads(fingerprint_path.read_text(encoding="utf-8"))

    assert payload["readonly_snapshot_latest_unchanged"] is True
    assert payload["agent_prompt_latest_unchanged"] is True
    assert payload["unchanged"]["all_protected_paths_unchanged"] is True
    assert payload["before"]["readonly_snapshot_latest"]["sha256"] == payload["after"]["readonly_snapshot_latest"]["sha256"]
    assert payload["before"]["agent_prompt_latest"]["sha256"] == payload["after"]["agent_prompt_latest"]["sha256"]


def test_ador_forbidden_action_audit_all_false(tmp_path: Path) -> None:
    paths = write_ador_latest_inputs(tmp_path)
    result = daily.run_ador_no_publish_orchestration_dry_run(
        asof="2026-07-08",
        job_dir=tmp_path / "job",
        job_id="unit",
        enabled=True,
        readonly_latest_path=paths["readonly_latest"],
        agent_latest_path=paths["agent_latest"],
        provider_latest_path=paths["provider_latest"],
        legacy_latest_path=paths["legacy_latest"],
    )
    audit = json.loads(Path(result["evidence_paths"]["forbidden_action_audit"]).read_text(encoding="utf-8"))

    assert result["forbidden_actions_all_false"] is True
    assert audit["all_false"] is True
    assert not any(audit["actions"].values())


def write_dapr18_latest_inputs(tmp_path: Path, *, asof: str = "2026-07-17") -> dict[str, Path]:
    controlled_manifest = tmp_path / "signals" / "manifest.json"
    readonly_manifest = tmp_path / "readonly" / asof / "manifest.json"
    agent_manifest = tmp_path / "agent" / asof / "manifest.json"
    controlled_latest = tmp_path / "signals" / "latest.json"
    readonly_latest = tmp_path / "readonly" / "latest.json"
    agent_latest = tmp_path / "agent" / "latest.json"
    provider_latest = tmp_path / "provider_latest.json"
    legacy_latest = tmp_path / "legacy_latest.json"
    write_payload(controlled_manifest, {"signal_asof": asof})
    write_payload(readonly_manifest, {"signal_asof": asof})
    write_payload(agent_manifest, {"signal_asof": asof})
    write_payload(
        controlled_latest,
        {
            "signal_asof": asof,
            "run_id": "unit_modela",
            "canonical_manifest": str(controlled_manifest),
            "readonly_only": True,
            "production_trade_enabled": False,
        },
    )
    write_payload(
        readonly_latest,
        {
            "signal_asof": asof,
            "snapshot_manifest": str(readonly_manifest),
            "readonly_only": True,
            "production_trade_enabled": False,
        },
    )
    write_payload(
        agent_latest,
        {
            "signal_asof": asof,
            "manifest": str(agent_manifest),
            "readonly_only": True,
            "production_trade_enabled": False,
        },
    )
    write_payload(provider_latest, {"asof": "2026-07-08"})
    write_payload(legacy_latest, {"asof": "2026-07-08"})
    return {
        "controlled_latest": controlled_latest,
        "readonly_latest": readonly_latest,
        "agent_latest": agent_latest,
        "provider_latest": provider_latest,
        "legacy_latest": legacy_latest,
    }


def test_dapr18_default_disabled_does_not_write_evidence_or_latest(tmp_path: Path) -> None:
    paths = write_dapr18_latest_inputs(tmp_path)
    before = {
        name: daily.file_fingerprint(path)["sha256"]
        for name, path in paths.items()
        if name.endswith("latest")
    }
    job_dir = tmp_path / "job"

    result = daily.run_dapr18_controlled_latest_orchestration(
        asof="2026-07-17",
        job_dir=job_dir,
        job_id="unit",
        enabled=False,
        controlled_signal_latest_path=paths["controlled_latest"],
        readonly_latest_path=paths["readonly_latest"],
        agent_latest_path=paths["agent_latest"],
        provider_latest_path=paths["provider_latest"],
        legacy_latest_path=paths["legacy_latest"],
    )

    assert result["enabled"] is False
    assert result["attempted"] is False
    assert result["ok"] is True
    assert result["status"] == "disabled_by_default"
    assert not (job_dir / "dapr18_controlled_latest_orchestration_summary.json").exists()
    for name, sha256 in before.items():
        assert daily.file_fingerprint(paths[name])["sha256"] == sha256


def test_dapr18_explicit_dry_run_writes_only_job_dir_evidence(tmp_path: Path) -> None:
    paths = write_dapr18_latest_inputs(tmp_path)
    before = {
        name: daily.file_fingerprint(path)["sha256"]
        for name, path in paths.items()
        if name.endswith("latest")
    }
    job_dir = tmp_path / "job"
    write_payload(
        job_dir / "daily_full_capture_accounting.json",
        {
            "rows": [
                {
                    "dataset_category": "finmind_raw_daily_price",
                    "source_boundary": "unit",
                    "source_max_date": "2026-07-17",
                    "row_count": "150",
                    "symbol_count": "150",
                    "status": "captured",
                    "status_reason": "unit",
                    "retry_hint": "",
                }
            ]
        },
    )

    result = daily.run_dapr18_controlled_latest_orchestration(
        asof="2026-07-17",
        job_dir=job_dir,
        job_id="unit",
        job={"job_id": "unit", "asof": "2026-07-17"},
        enabled=True,
        dry_run=True,
        controlled_signal_latest_path=paths["controlled_latest"],
        readonly_latest_path=paths["readonly_latest"],
        agent_latest_path=paths["agent_latest"],
        provider_latest_path=paths["provider_latest"],
        legacy_latest_path=paths["legacy_latest"],
    )

    assert result["enabled"] is True
    assert result["attempted"] is True
    assert result["ok"] is True
    assert result["status"] == "dry_run_plan_recorded"
    assert result["job_dir_only_evidence"] is True
    assert result["latest_pointer_write_performed"] is False
    assert result["protected_paths_unchanged"] is True
    assert result["source_readiness_state"] == "READY_EXISTING_CONTROLLED_LATESTS"
    for evidence_path in result["evidence_paths"].values():
        assert Path(evidence_path).exists()
        assert str(Path(evidence_path)).startswith(str(job_dir))
    fingerprint = json.loads(Path(result["evidence_paths"]["protected_paths_fingerprint"]).read_text(encoding="utf-8"))
    assert fingerprint["all_protected_paths_unchanged"] is True
    for name, sha256 in before.items():
        assert daily.file_fingerprint(paths[name])["sha256"] == sha256


def test_dapr18_publish_flag_is_blocked_while_dry_run_without_latest_write(tmp_path: Path) -> None:
    paths = write_dapr18_latest_inputs(tmp_path)
    before = daily.file_fingerprint(paths["controlled_latest"])["sha256"]
    job_dir = tmp_path / "job"

    result = daily.run_dapr18_controlled_latest_orchestration(
        asof="2026-07-17",
        job_dir=job_dir,
        job_id="unit",
        enabled=True,
        dry_run=True,
        publish_controlled_signal_latest=True,
        controlled_signal_latest_path=paths["controlled_latest"],
        readonly_latest_path=paths["readonly_latest"],
        agent_latest_path=paths["agent_latest"],
        provider_latest_path=paths["provider_latest"],
        legacy_latest_path=paths["legacy_latest"],
    )
    failure = json.loads(Path(result["evidence_paths"]["failure_ledger"]).read_text(encoding="utf-8"))

    assert result["ok"] is False
    assert result["status"] == "blocked_by_dapr18p1_auto_publish_control"
    assert "controlled_signal_latest_publish_blocked_while_dry_run_true" in result["blocked_controls"]
    assert "dry_run_true_blocks_actual_auto_publish" in result["blocked_controls"]
    assert failure["blocked"] is True
    assert failure["final_status"] == "blocked_by_dapr18p1_auto_publish_control"
    assert failure["resolution_status"] == "blocked_fail_closed"
    assert failure["historical_pre_publish_readiness"]["historical"] is True
    assert result["latest_pointer_write_performed"] is False
    assert daily.file_fingerprint(paths["controlled_latest"])["sha256"] == before


def write_dapr18_model_signal_source(tmp_path: Path, *, asof: str = "2026-07-17", run_id: str = "unit_modela") -> Path:
    signal_dir = tmp_path / "model_signal" / run_id
    write_payload(
        signal_dir / "manifest.json",
        {
            "artifact_type": "ModelSignalArtifact",
            "model_id": daily.MODELA_MODEL_ID,
            "model_name": daily.MODELA_MODEL_ID,
            "status": "READY",
            "asof": asof,
            "signal_asof": asof,
            "run_id": run_id,
            "row_count": 150,
            "production_allowed": False,
            "not_published_latest": True,
            "no_latest": True,
            "forbidden_actions": {"provider_publish_triggered": False, "accepted_latest_switch": False},
        },
    )
    write_payload(signal_dir / "schema.json", {"schema_version": "unit"})
    write_payload(signal_dir / "validator_report.json", {"ok": True, "status": "PASS", "signal_rows": 150})
    (signal_dir / "coverage_audit.csv").parent.mkdir(parents=True, exist_ok=True)
    (signal_dir / "coverage_audit.csv").write_text("status\npass\n", encoding="utf-8")
    (signal_dir / "forbidden_field_audit.csv").write_text("field,status\nnone,pass\n", encoding="utf-8")
    rows = ["date,instrument,model_name,candidate_rank,buy_score,raw_score,score_rank,full_qlib_rank,signal_asof"]
    for idx in range(1, 151):
        rows.append(f"{asof},TW{idx:04d},{daily.MODELA_MODEL_ID},{idx},0.1,0.1,{idx},{idx},{asof}")
    (signal_dir / "signals.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return signal_dir


@pytest.mark.parametrize("wrong_model", [daily.MODELB_LTR_MODEL_ID, "unknown_model"])
def test_dapr18_model_signal_source_rejects_non_active_manifest_identity(
    tmp_path: Path,
    wrong_model: str,
) -> None:
    signal_dir = write_dapr18_model_signal_source(tmp_path)
    manifest_path = signal_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["model_id"] = wrong_model
    manifest["model_name"] = wrong_model
    write_payload(manifest_path, manifest)

    validation = daily.validate_dapr18_model_signal_source(asof="2026-07-17", signal_dir=signal_dir)

    assert validation["ok"] is False
    assert validation["checks"]["manifest_model_id_active_modela"] is False
    assert validation["checks"]["manifest_model_name_active_modela"] is False
    assert validation["signal_model_names"] == [daily.MODELA_MODEL_ID]


def test_dapr18_model_signal_source_rejects_non_active_signal_row_identity(tmp_path: Path) -> None:
    signal_dir = write_dapr18_model_signal_source(tmp_path)
    signals_path = signal_dir / "signals.csv"
    signals_path.write_text(
        signals_path.read_text(encoding="utf-8").replace(daily.MODELA_MODEL_ID, daily.MODELB_LTR_MODEL_ID),
        encoding="utf-8",
    )

    validation = daily.validate_dapr18_model_signal_source(asof="2026-07-17", signal_dir=signal_dir)

    assert validation["ok"] is False
    assert validation["checks"]["manifest_model_id_active_modela"] is True
    assert validation["checks"]["signals_model_name_active_modela_when_present"] is False
    assert validation["signal_model_names"] == [daily.MODELB_LTR_MODEL_ID]


def test_dapr18_auto_publish_requires_exact_authorization_and_complete_scope(tmp_path: Path) -> None:
    paths = write_dapr18_latest_inputs(tmp_path, asof="2026-07-17")
    before = daily.file_fingerprint(paths["controlled_latest"])["sha256"]

    result = daily.run_dapr18_controlled_latest_orchestration(
        asof="2026-07-17",
        job_dir=tmp_path / "job",
        job_id="unit",
        enabled=True,
        dry_run=False,
        publish_controlled_signal_latest=True,
        publish_readonly_snapshot_latest=False,
        publish_agent_prompt_latest=True,
        exact_authorization_id="DAPR18_AUTO_PUBLISH_CHAIN_UNIT",
        controlled_signal_latest_path=paths["controlled_latest"],
        readonly_latest_path=paths["readonly_latest"],
        agent_latest_path=paths["agent_latest"],
        provider_latest_path=paths["provider_latest"],
        legacy_latest_path=paths["legacy_latest"],
    )

    assert result["ok"] is False
    assert "dapr18_auto_publish_requires_all_three_product_latest_flags" in result["blocked_controls"]
    assert result["latest_pointer_write_performed"] is False
    assert daily.file_fingerprint(paths["controlled_latest"])["sha256"] == before


def test_dapr18_auto_publish_chain_uses_stubbed_dapr9_to_dapr17_and_marks_success(tmp_path: Path, monkeypatch) -> None:
    asof = "2026-07-17"
    run_id = "unit_modela"
    paths = write_dapr18_latest_inputs(tmp_path, asof="2026-07-08")
    monkeypatch.setattr(daily, "CONTROLLED_MODEL_SIGNAL_ROOT", tmp_path / "model_signal")
    source_dir = write_dapr18_model_signal_source(tmp_path, asof=asof, run_id=run_id)
    calls: list[dict] = []
    expected_status = {
        "build_tw_dapr9_controlled_latest_publish_preflight_or_stop.py": {
            "status": "pass",
            "ready_for_future_exact_authorization_gate": True,
        },
        "build_tw_dapr10_actual_controlled_signal_latest_publish.py": {"status": "pass"},
        "build_tw_dapr11_downstream_readonly_snapshot_agent_preflight_or_stop.py": {
            "status": "pass",
            "ready_for_dapr12_no_publish_snapshot_dry_run": True,
        },
        "build_tw_dapr12_candidate_only_readonly_snapshot_dry_run_no_publish.py": {
            "status": "pass",
            "ready_for_dapr13_exact_authorization_gate": True,
        },
        "build_tw_dapr13_actual_readonly_snapshot_publish.py": {"status": "pass"},
        "build_tw_dapr14_agent_prompt_latest_preflight_or_stop.py": {
            "status": "pass",
            "ready_for_dapr15_candidate_only_agent_prompt_dry_run": True,
        },
        "build_tw_dapr15_candidate_only_agent_prompt_dry_run_no_publish.py": {
            "status": "pass",
            "ready_for_dapr16_agent_prompt_publish_preflight_gate": True,
        },
        "build_tw_dapr16_controlled_agent_prompt_publish_preflight_or_stop.py": {
            "status": "pass",
            "ready_for_dapr17_exact_authorization_gate": True,
        },
        "build_tw_dapr17_actual_controlled_agent_prompt_publish.py": {"status": "pass"},
    }

    def stub_runner(argv, *, cwd, stdout_path, stderr_path, timeout, env=None):
        script_name = Path(argv[1]).name
        calls.append({"script": script_name, "env": env or {}})
        if script_name == "build_tw_dapr10_actual_controlled_signal_latest_publish.py":
            write_payload(paths["controlled_latest"], {"asof": asof, "signal_asof": asof, "run_id": run_id, "canonical_manifest": str(source_dir / "manifest.json")})
        elif script_name == "build_tw_dapr13_actual_readonly_snapshot_publish.py":
            manifest = tmp_path / "readonly" / asof / "manifest.json"
            write_payload(manifest, {"signal_asof": asof})
            write_payload(paths["readonly_latest"], {"signal_asof": asof, "snapshot_manifest": str(manifest)})
        elif script_name == "build_tw_dapr17_actual_controlled_agent_prompt_publish.py":
            manifest = tmp_path / "agent" / asof / "manifest.json"
            write_payload(manifest, {"signal_asof": asof})
            write_payload(paths["agent_latest"], {"signal_asof": asof, "target_date": asof, "manifest": str(manifest)})
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(json.dumps(expected_status[script_name]), encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "argv": argv,
            "cwd": str(cwd),
            "env_keys": sorted((env or {}).keys()),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "stdout_tail": "",
            "stderr_tail": "",
        }

    result = daily.run_dapr18_controlled_latest_orchestration(
        asof=asof,
        job_dir=tmp_path / "job",
        job_id="unit",
        job={
            "job_id": "unit",
            "asof": asof,
            "model_signal_gate": {
                "summary": {"model_a_signal_path": str(source_dir)},
            },
        },
        enabled=True,
        dry_run=False,
        publish_controlled_signal_latest=True,
        publish_readonly_snapshot_latest=True,
        publish_agent_prompt_latest=True,
        exact_authorization_id="DAPR18_AUTO_PUBLISH_CHAIN_UNIT",
        controlled_signal_latest_path=paths["controlled_latest"],
        readonly_latest_path=paths["readonly_latest"],
        agent_latest_path=paths["agent_latest"],
        provider_latest_path=paths["provider_latest"],
        legacy_latest_path=paths["legacy_latest"],
        command_runner=stub_runner,
    )

    assert result["ok"] is True
    assert result["status"] == "auto_publish_chain_completed"
    assert result["latest_pointer_write_performed"] is True
    assert result["controlled_signal_latest_write_performed"] is True
    assert result["readonly_snapshot_latest_write_performed"] is True
    assert result["agent_prompt_latest_write_performed"] is True
    assert result["forbidden_protected_paths_unchanged"] is True
    assert [call["script"] for call in calls] == list(expected_status)
    assert calls[0]["env"]["DAPR9_TARGET_ASOF"] == asof
    assert calls[0]["env"]["DAPR9_RUN_ID"] == run_id
    assert calls[0]["env"]["DAPR9_SOURCE_SIGNAL_DIR"] == str(source_dir)
    assert calls[0]["env"]["DAPR9_SOURCE_RUNTIME_AUDIT"].endswith("dapr18p1_source_bridge/runtime_path_audit.json")
    runtime_audit = Path(calls[0]["env"]["DAPR9_SOURCE_RUNTIME_AUDIT"])
    assert runtime_audit.is_file()
    runtime_payload = json.loads(runtime_audit.read_text(encoding="utf-8"))
    assert runtime_payload["status"] == "pass"
    assert runtime_payload["schema_version"] == "dapr18p1.source_bridge_runtime_path_audit.v1"
    assert calls[-1]["env"]["TW_DAPR17_TARGET_ASOF"] == asof
    success_ledger = json.loads(Path(result["evidence_paths"]["failure_ledger"]).read_text(encoding="utf-8"))
    assert success_ledger["blocked"] is False
    assert success_ledger["blockers"] == []
    assert success_ledger["resolution_status"] == "resolved_authorized_publish_completed"
    assert success_ledger["next_required_action"] == ""
    assert success_ledger["historical_pre_publish_readiness"]["historical"] is True


def dapr18_success_payloads() -> dict[str, dict]:
    return {
        "build_tw_dapr9_controlled_latest_publish_preflight_or_stop.py": {
            "status": "pass",
            "ready_for_future_exact_authorization_gate": True,
        },
        "build_tw_dapr10_actual_controlled_signal_latest_publish.py": {"status": "pass"},
        "build_tw_dapr11_downstream_readonly_snapshot_agent_preflight_or_stop.py": {
            "status": "pass",
            "ready_for_dapr12_no_publish_snapshot_dry_run": True,
        },
        "build_tw_dapr12_candidate_only_readonly_snapshot_dry_run_no_publish.py": {
            "status": "pass",
            "ready_for_dapr13_exact_authorization_gate": True,
        },
        "build_tw_dapr13_actual_readonly_snapshot_publish.py": {"status": "pass"},
        "build_tw_dapr14_agent_prompt_latest_preflight_or_stop.py": {
            "status": "pass",
            "ready_for_dapr15_candidate_only_agent_prompt_dry_run": True,
        },
        "build_tw_dapr15_candidate_only_agent_prompt_dry_run_no_publish.py": {
            "status": "pass",
            "ready_for_dapr16_agent_prompt_publish_preflight_gate": True,
        },
        "build_tw_dapr16_controlled_agent_prompt_publish_preflight_or_stop.py": {
            "status": "pass",
            "ready_for_dapr17_exact_authorization_gate": True,
        },
        "build_tw_dapr17_actual_controlled_agent_prompt_publish.py": {"status": "pass"},
    }


def make_dapr18_stub_runner(
    *,
    paths: dict[str, Path],
    source_dir: Path,
    asof: str,
    run_id: str,
    calls: list[str],
    fail_script: str = "",
):
    success_payloads = dapr18_success_payloads()

    def stub_runner(argv, *, cwd, stdout_path, stderr_path, timeout, env=None):
        script_name = Path(argv[1]).name
        calls.append(script_name)
        if script_name == fail_script:
            return command_result(stdout_path, {"status": "fail"}, ok=False)
        if script_name == "build_tw_dapr10_actual_controlled_signal_latest_publish.py":
            write_payload(
                paths["controlled_latest"],
                {
                    "asof": asof,
                    "signal_asof": asof,
                    "run_id": run_id,
                    "canonical_manifest": str(source_dir / "manifest.json"),
                },
            )
        elif script_name == "build_tw_dapr13_actual_readonly_snapshot_publish.py":
            manifest = paths["readonly_latest"].parent / asof / "manifest.json"
            write_payload(manifest, {"signal_asof": asof})
            write_payload(paths["readonly_latest"], {"signal_asof": asof, "snapshot_manifest": str(manifest)})
        elif script_name == "build_tw_dapr17_actual_controlled_agent_prompt_publish.py":
            manifest = paths["agent_latest"].parent / asof / "manifest.json"
            write_payload(manifest, {"signal_asof": asof})
            write_payload(
                paths["agent_latest"],
                {"signal_asof": asof, "target_date": asof, "manifest": str(manifest)},
            )
        return command_result(stdout_path, success_payloads[script_name])

    return stub_runner


def run_dapr18_stubbed_chain(
    *,
    tmp_path: Path,
    monkeypatch,
    paths: dict[str, Path],
    source_dir: Path,
    job_dir_name: str,
    command_runner,
    asof: str,
    run_id: str,
) -> dict:
    monkeypatch.setattr(daily, "CONTROLLED_MODEL_SIGNAL_ROOT", tmp_path / "model_signal")
    return daily.run_dapr18_controlled_latest_orchestration(
        asof=asof,
        job_dir=tmp_path / job_dir_name,
        job_id=job_dir_name,
        job={
            "job_id": job_dir_name,
            "asof": asof,
            "model_signal_gate": {"summary": {"model_a_signal_path": str(source_dir)}},
        },
        enabled=True,
        dry_run=False,
        publish_controlled_signal_latest=True,
        publish_readonly_snapshot_latest=True,
        publish_agent_prompt_latest=True,
        exact_authorization_id="DAPR18_AUTO_PUBLISH_CHAIN_UNIT",
        controlled_signal_latest_path=paths["controlled_latest"],
        readonly_latest_path=paths["readonly_latest"],
        agent_latest_path=paths["agent_latest"],
        provider_latest_path=paths["provider_latest"],
        legacy_latest_path=paths["legacy_latest"],
        command_runner=command_runner,
    )


def test_dapr18_dapr13_failure_stops_after_five_steps_without_completed_status(tmp_path: Path, monkeypatch) -> None:
    asof = "2026-07-17"
    run_id = "unit_modela"
    paths = write_dapr18_latest_inputs(tmp_path, asof="2026-07-08")
    source_dir = write_dapr18_model_signal_source(tmp_path, asof=asof, run_id=run_id)
    calls: list[str] = []
    forbidden_before = {
        name: daily.file_fingerprint(paths[name])["sha256"]
        for name in ("provider_latest", "legacy_latest")
    }
    runner = make_dapr18_stub_runner(
        paths=paths,
        source_dir=source_dir,
        asof=asof,
        run_id=run_id,
        calls=calls,
        fail_script="build_tw_dapr13_actual_readonly_snapshot_publish.py",
    )

    result = run_dapr18_stubbed_chain(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        paths=paths,
        source_dir=source_dir,
        job_dir_name="job-dapr13-failure",
        command_runner=runner,
        asof=asof,
        run_id=run_id,
    )

    chain = result["auto_publish_chain"]
    assert result["ok"] is False
    assert result["status"] == "blocked_by_dapr18p1_auto_publish_control"
    assert result["status"] != "auto_publish_chain_completed"
    assert chain["status"] == "blocked"
    assert chain["step_count"] == 5
    assert chain["steps"][-1]["name"] == "dapr13_actual_readonly_snapshot_publish"
    assert chain["steps"][-1]["ok"] is False
    assert calls == list(dapr18_success_payloads())[:5]
    assert not any(f"dapr{number}" in " ".join(calls) for number in range(14, 18))
    assert result["forbidden_protected_paths_unchanged"] is True
    for name, digest in forbidden_before.items():
        assert daily.file_fingerprint(paths[name])["sha256"] == digest


def test_dapr18_dapr17_failure_is_blocked_without_completed_status(tmp_path: Path, monkeypatch) -> None:
    asof = "2026-07-17"
    run_id = "unit_modela"
    paths = write_dapr18_latest_inputs(tmp_path, asof="2026-07-08")
    source_dir = write_dapr18_model_signal_source(tmp_path, asof=asof, run_id=run_id)
    calls: list[str] = []
    forbidden_before = {
        name: daily.file_fingerprint(paths[name])["sha256"]
        for name in ("provider_latest", "legacy_latest")
    }
    runner = make_dapr18_stub_runner(
        paths=paths,
        source_dir=source_dir,
        asof=asof,
        run_id=run_id,
        calls=calls,
        fail_script="build_tw_dapr17_actual_controlled_agent_prompt_publish.py",
    )

    result = run_dapr18_stubbed_chain(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        paths=paths,
        source_dir=source_dir,
        job_dir_name="job-dapr17-failure",
        command_runner=runner,
        asof=asof,
        run_id=run_id,
    )

    chain = result["auto_publish_chain"]
    assert result["ok"] is False
    assert result["status"] == "blocked_by_dapr18p1_auto_publish_control"
    assert result["status"] != "auto_publish_chain_completed"
    assert chain["status"] == "blocked"
    assert chain["step_count"] == 9
    assert chain["steps"][-1]["name"] == "dapr17_actual_controlled_agent_prompt_publish"
    assert chain["steps"][-1]["ok"] is False
    assert calls == list(dapr18_success_payloads())
    assert result["forbidden_protected_paths_unchanged"] is True
    for name, digest in forbidden_before.items():
        assert daily.file_fingerprint(paths[name])["sha256"] == digest


def test_dapr18_retry_after_failure_converges_then_is_idempotent_noop(tmp_path: Path, monkeypatch) -> None:
    asof = "2026-07-17"
    run_id = "unit_modela"
    paths = write_dapr18_latest_inputs(tmp_path, asof="2026-07-08")
    source_dir = write_dapr18_model_signal_source(tmp_path, asof=asof, run_id=run_id)
    forbidden_before = {
        name: daily.file_fingerprint(paths[name])["sha256"]
        for name in ("provider_latest", "legacy_latest")
    }
    failed_calls: list[str] = []
    failed_runner = make_dapr18_stub_runner(
        paths=paths,
        source_dir=source_dir,
        asof=asof,
        run_id=run_id,
        calls=failed_calls,
        fail_script="build_tw_dapr17_actual_controlled_agent_prompt_publish.py",
    )
    failed = run_dapr18_stubbed_chain(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        paths=paths,
        source_dir=source_dir,
        job_dir_name="job-retry-initial-failure",
        command_runner=failed_runner,
        asof=asof,
        run_id=run_id,
    )
    assert failed["ok"] is False
    assert failed["auto_publish_chain"]["step_count"] == 9

    retry_calls: list[str] = []
    retry_runner = make_dapr18_stub_runner(
        paths=paths,
        source_dir=source_dir,
        asof=asof,
        run_id=run_id,
        calls=retry_calls,
    )
    retry = run_dapr18_stubbed_chain(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        paths=paths,
        source_dir=source_dir,
        job_dir_name="job-retry-success",
        command_runner=retry_runner,
        asof=asof,
        run_id=run_id,
    )

    assert retry["ok"] is True
    assert retry["status"] == "auto_publish_chain_completed"
    assert retry["auto_publish_chain"]["step_count"] == 9
    assert retry["product_latest_state_after"]["all_product_latest_match_target"] is True
    assert retry_calls == list(dapr18_success_payloads())
    for name in ("controlled_latest", "readonly_latest", "agent_latest"):
        assert daily.payload_signal_asof(json.loads(paths[name].read_text(encoding="utf-8"))) == asof

    product_before_noop = {
        name: daily.file_fingerprint(paths[name])["sha256"]
        for name in ("controlled_latest", "readonly_latest", "agent_latest")
    }

    def fail_if_called(*args, **kwargs):
        raise AssertionError("idempotent retry must not invoke DAPR9-17")

    noop = run_dapr18_stubbed_chain(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        paths=paths,
        source_dir=source_dir,
        job_dir_name="job-idempotent-noop",
        command_runner=fail_if_called,
        asof=asof,
        run_id=run_id,
    )

    assert noop["ok"] is True
    assert noop["status"] == "auto_publish_idempotent_noop_already_current"
    assert noop["auto_publish_chain"]["status"] == "idempotent_noop"
    assert noop["auto_publish_chain"]["step_count"] == 0
    assert noop["latest_pointer_write_performed"] is False
    noop_ledger = json.loads(Path(noop["evidence_paths"]["failure_ledger"]).read_text(encoding="utf-8"))
    assert noop_ledger["blocked"] is False
    assert noop_ledger["blockers"] == []
    assert noop_ledger["resolution_status"] == "resolved_idempotent_noop_already_current"
    assert noop_ledger["next_required_action"] == ""
    for name, digest in product_before_noop.items():
        assert daily.file_fingerprint(paths[name])["sha256"] == digest
    for name, digest in forbidden_before.items():
        assert daily.file_fingerprint(paths[name])["sha256"] == digest


def test_dapr18_publish_failure_is_terminal_and_keeps_asof_pending(monkeypatch, tmp_path: Path) -> None:
    asof = "2026-07-17"
    job = {"job_id": "unit", "asof": asof}
    pending_calls: list[tuple[str, str, str]] = []
    finalize_calls: list[dict] = []

    def fake_set_pending(pending_asof: str, *, reason: str, job_id: str) -> None:
        pending_calls.append((pending_asof, reason, job_id))

    def fake_finalize(final_job: dict, *, job_dir: Path, asof: str, args) -> None:
        finalize_calls.append({"job": dict(final_job), "job_dir": job_dir, "asof": asof, "args": args})

    monkeypatch.setattr(daily, "set_pending_asof", fake_set_pending)
    monkeypatch.setattr(daily, "finalize_job", fake_finalize)
    monkeypatch.setattr(daily, "latest_asof", lambda: "2026-07-16")
    orchestration = {
        "attempted": True,
        "publish_requested": True,
        "authorization_gate": {"allowed": True},
        "ok": False,
        "status": "blocked_by_dapr18p1_auto_publish_control",
        "blocked_controls": ["dapr13_actual_readonly_snapshot_publish_failed_or_stdout_gate_not_pass"],
        "auto_publish_chain": {
            "status": "blocked",
            "blocker": "dapr13_actual_readonly_snapshot_publish_failed_or_stdout_gate_not_pass",
        },
    }

    terminal = daily.finalize_dapr18_publish_failure(
        job=job,
        orchestration=orchestration,
        asof=asof,
        job_id="unit",
        job_dir=tmp_path / "job",
        args=object(),
    )

    assert terminal is True
    assert pending_calls == [(asof, "dapr18_auto_publish_failed", "unit")]
    assert job["status"] == "dapr18_auto_publish_failed"
    assert job["pending_asof_set"] == asof
    assert job["latest_after"] == "2026-07-16"
    assert "dapr13_actual_readonly_snapshot_publish" in job["dapr18_terminal_blocker"]
    assert len(finalize_calls) == 1
    assert finalize_calls[0]["job"]["status"] != "daily_auto_update_passed"

    source = (ROOT / "scripts/run_daily_tw_stock_auto_update.py").read_text(encoding="utf-8")
    main_start = source.index("def main() -> int:")
    dapr_assignment = source.index('job["dapr18_controlled_latest_orchestration"]', main_start)
    terminal_call = source.index("if finalize_dapr18_publish_failure(", dapr_assignment)
    terminal_return = source.index("return 2", terminal_call)
    legacy_readonly = source.index("run_readonly_strategy_snapshot_publish(", terminal_call)
    assert dapr_assignment < terminal_call < terminal_return < legacy_readonly
    assert "clear_pending_asof(" not in source[terminal_call:legacy_readonly]
    assert "daily_auto_update_passed" not in source[terminal_call:legacy_readonly]


def test_dapr18_missing_exact_authorization_is_terminal_when_publish_requested(monkeypatch, tmp_path: Path) -> None:
    asof = "2026-07-17"
    job = {"job_id": "unit-missing-auth", "asof": asof}
    pending_calls: list[tuple[str, str, str]] = []
    finalize_calls: list[str] = []

    monkeypatch.setattr(
        daily,
        "set_pending_asof",
        lambda pending_asof, *, reason, job_id: pending_calls.append((pending_asof, reason, job_id)),
    )
    monkeypatch.setattr(
        daily,
        "finalize_job",
        lambda final_job, *, job_dir, asof, args: finalize_calls.append(final_job["status"]),
    )
    monkeypatch.setattr(daily, "latest_asof", lambda: "2026-07-16")
    orchestration = {
        "attempted": True,
        "publish_requested": True,
        "authorization_gate": {
            "allowed": False,
            "blockers": ["dapr18_auto_publish_requires_exact_authorization_id"],
        },
        "ok": False,
        "status": "blocked_by_dapr18p1_auto_publish_control",
        "blocked_controls": ["dapr18_auto_publish_requires_exact_authorization_id"],
        "auto_publish_chain": {},
    }

    terminal = daily.finalize_dapr18_publish_failure(
        job=job,
        orchestration=orchestration,
        asof=asof,
        job_id="unit-missing-auth",
        job_dir=tmp_path / "job-missing-auth",
        args=object(),
    )

    assert terminal is True
    assert pending_calls == [(asof, "dapr18_auto_publish_failed", "unit-missing-auth")]
    assert finalize_calls == ["dapr18_auto_publish_failed"]
    assert job["status"] == "dapr18_auto_publish_failed"
    assert job["pending_asof_set"] == asof
    assert job["dapr18_terminal_blocker"] == "dapr18_auto_publish_requires_exact_authorization_id"


def test_dapr18_failed_observation_without_publish_request_is_not_terminal(monkeypatch, tmp_path: Path) -> None:
    def forbidden_side_effect(*args, **kwargs):
        raise AssertionError("no-publish observation must not enter publish-failure terminalization")

    monkeypatch.setattr(daily, "set_pending_asof", forbidden_side_effect)
    monkeypatch.setattr(daily, "finalize_job", forbidden_side_effect)
    job = {"job_id": "unit-observation", "asof": "2026-07-17"}

    terminal = daily.finalize_dapr18_publish_failure(
        job=job,
        orchestration={
            "attempted": True,
            "publish_requested": False,
            "authorization_gate": {"allowed": False},
            "ok": False,
            "status": "blocked_observation",
        },
        asof="2026-07-17",
        job_id="unit-observation",
        job_dir=tmp_path / "job-observation",
        args=object(),
    )

    assert terminal is False
    assert job == {"job_id": "unit-observation", "asof": "2026-07-17"}
