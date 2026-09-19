from __future__ import annotations

import json
import hashlib
from pathlib import Path

import yaml

from app.services import research_readiness as readiness


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    registry = {
        "schema_version": "tw_product_artifact_registry_v1", "readonly_only": True,
        "models": {"base_model_id": "model_a"},
        "strategies": {"default_strategy_rule": "top50"},
    }
    registry_path = root / readiness.CONTROL_FILES["artifact_registry"]
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    model_dir = root / "data_tw/artifacts/signals/model_a/run"
    _write_json(model_dir / "manifest.json", {
        "artifact_type": "ModelSignalArtifact", "model_id": "model_a",
        "status": "READY", "asof": "2026-09-18",
    })
    (model_dir / "signals.csv").write_text("instrument\nTW2330\n", encoding="utf-8")
    manifest_sha = hashlib.sha256((model_dir / "manifest.json").read_bytes()).hexdigest()
    signals_sha = hashlib.sha256((model_dir / "signals.csv").read_bytes()).hexdigest()
    _write_json(root / readiness.CONTROL_FILES["model_a_latest"], {
        "artifact_type": "controlled_model_signal_latest_pointer", "readonly_only": True,
        "production_trade_enabled": False, "model_id": "model_a", "signal_asof": "2026-09-18",
        "canonical_artifact_dir": "data_tw/artifacts/signals/model_a/run",
        "canonical_manifest": "data_tw/artifacts/signals/model_a/run/manifest.json",
        "canonical_signals": "data_tw/artifacts/signals/model_a/run/signals.csv",
        "canonical_manifest_sha256": manifest_sha, "canonical_signals_sha256": signals_sha,
    })
    snapshot_manifest = root / "data_tw/artifacts/publish/readonly_strategy_snapshot/2026-09-18/manifest.json"
    snapshot_dir = snapshot_manifest.parent
    snapshot_payload = snapshot_dir / "strategy_snapshot.json"
    snapshot_validation = snapshot_dir / "validation_report.json"
    snapshot_forbidden = snapshot_dir / "forbidden_scope_audit.json"
    _write_json(snapshot_payload, {"readonly_only": True})
    _write_json(snapshot_validation, {
        "status": "pass", "readonly_snapshot_validator_ok": True, "checksum_ok": True,
    })
    _write_json(snapshot_forbidden, {"status": "pass", "all_forbidden_false": True})
    snapshot_manifest_payload = {
        "artifact_type": "readonly_strategy_snapshot", "readonly_only": True,
        "production_trade_enabled": False, "no_order_action": True, "signal_asof": "2026-09-18",
        "source_signal_latest": readiness.CONTROL_FILES["model_a_latest"],
        "checksum_manifest": "checksum_manifest.json", "snapshot": snapshot_payload.name,
        "validation_report": snapshot_validation.name, "forbidden_scope_audit": snapshot_forbidden.name,
    }
    _write_json(snapshot_manifest, snapshot_manifest_payload)
    _write_json(snapshot_dir / "checksum_manifest.json", {
        "files": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (snapshot_manifest, snapshot_payload, snapshot_validation, snapshot_forbidden)
        },
    })
    snapshot_manifest_sha = hashlib.sha256(snapshot_manifest.read_bytes()).hexdigest()
    model_pointer = root / readiness.CONTROL_FILES["model_a_latest"]
    model_pointer_sha = hashlib.sha256(model_pointer.read_bytes()).hexdigest()
    _write_json(root / readiness.CONTROL_FILES["readonly_snapshot_latest"], {
        "artifact_type": "readonly_strategy_snapshot_latest_pointer", "readonly_only": True,
        "production_trade_enabled": False, "not_trade_target_latest": True,
        "signal_asof": "2026-09-18",
        "snapshot_manifest": "data_tw/artifacts/publish/readonly_strategy_snapshot/2026-09-18/manifest.json",
        "planned_manifest_payload_sha256": snapshot_manifest_sha,
        "source_signal_latest": readiness.CONTROL_FILES["model_a_latest"],
        "source_signal_latest_sha256": model_pointer_sha,
    })
    agent_manifest = root / "data_tw/artifacts/agent_daily_prompt/2026-09-18/manifest.json"
    prompt_context = agent_manifest.parent / "prompt_context.json"
    prompt_text = agent_manifest.parent / "prompt_text.md"
    _write_json(prompt_context, {"signal_asof": "2026-09-18"})
    prompt_text.write_text("readonly fixture\n", encoding="utf-8")
    checksum = "sha256:" + hashlib.sha256(prompt_context.read_bytes() + b"\n" + prompt_text.read_bytes()).hexdigest()
    _write_json(agent_manifest, {
        "artifact_type": "tw_agent_daily_prompt", "readonly_only": True,
        "not_order": True, "not_target_position": True, "production_trade_enabled": False,
        "signal_asof": "2026-09-18", "checksum": checksum,
        "validation": {
            "ok": True, "asof_alignment": "pass",
            "forbidden_action_audit": "pass", "source_gate": "pass",
        },
    })
    _write_json(root / readiness.CONTROL_FILES["agent_prompt_latest"], {
        "artifact_type": "tw_agent_daily_prompt_latest", "readonly_only": True,
        "production_trade_enabled": False, "signal_asof": "2026-09-18",
        "artifact_dir": "data_tw/artifacts/agent_daily_prompt/2026-09-18",
        "manifest": "data_tw/artifacts/agent_daily_prompt/2026-09-18/manifest.json",
        "checksum": checksum,
        "source_readonly_snapshot_latest": readiness.CONTROL_FILES["readonly_snapshot_latest"],
    })
    return root


def test_readiness_accepts_same_day_readonly_chain(tmp_path):
    root = _fixture(tmp_path)
    before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    result = readiness.research_readiness(repo_root=root)
    after = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert result["ready"] is True
    assert result["status"] == "ready"
    assert result["signal_asof"] == "2026-09-18"
    assert result["external_dependencies_checked"] is False
    assert result["side_effects"] == "none"
    assert all(check["ready"] for check in result["checks"])
    assert after == before


def test_readiness_fails_closed_without_exposing_paths_or_exception_text(tmp_path):
    root = _fixture(tmp_path)
    snapshot = root / readiness.CONTROL_FILES["readonly_snapshot_latest"]
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    payload["signal_asof"] = "2026-09-17"
    payload["snapshot_manifest"] = "/private/secret/location.json"
    _write_json(snapshot, payload)
    result = readiness.research_readiness(repo_root=root)
    assert result["ready"] is False
    assert result["signal_asof"] is None
    serialized = json.dumps(result)
    assert str(root) not in serialized
    assert "/private/secret" not in serialized
    snapshot_check = next(check for check in result["checks"] if check["name"] == "snapshot_contract")
    assert snapshot_check == {"name": "snapshot_contract", "ready": False, "code": "snapshot_pointer_contract_failed"}


def test_readiness_rejects_pointer_target_escape(tmp_path):
    root = _fixture(tmp_path)
    pointer = root / readiness.CONTROL_FILES["agent_prompt_latest"]
    payload = json.loads(pointer.read_text(encoding="utf-8"))
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    payload["manifest"] = str(outside)
    _write_json(pointer, payload)
    result = readiness.research_readiness(repo_root=root)
    check = next(item for item in result["checks"] if item["name"] == "agent_contract")
    assert check["ready"] is False
    assert check["code"] == "target_outside_repository"


def test_readiness_rejects_model_a_checksum_drift(tmp_path):
    root = _fixture(tmp_path)
    (root / "data_tw/artifacts/signals/model_a/run/signals.csv").write_text("drifted", encoding="utf-8")
    result = readiness.research_readiness(repo_root=root)
    check = next(item for item in result["checks"] if item["name"] == "model_a_contract")
    assert check == {"name": "model_a_contract", "ready": False, "code": "target_checksum_failed"}


def test_readiness_rejects_snapshot_payload_checksum_drift(tmp_path):
    root = _fixture(tmp_path)
    snapshot = root / "data_tw/artifacts/publish/readonly_strategy_snapshot/2026-09-18/strategy_snapshot.json"
    snapshot.write_text('{"readonly_only": false}', encoding="utf-8")
    result = readiness.research_readiness(repo_root=root)
    check = next(item for item in result["checks"] if item["name"] == "snapshot_contract")
    assert check == {"name": "snapshot_contract", "ready": False, "code": "target_checksum_failed"}


def test_readiness_rejects_agent_prompt_checksum_drift(tmp_path):
    root = _fixture(tmp_path)
    prompt = root / "data_tw/artifacts/agent_daily_prompt/2026-09-18/prompt_text.md"
    prompt.write_text("tampered\n", encoding="utf-8")
    result = readiness.research_readiness(repo_root=root)
    check = next(item for item in result["checks"] if item["name"] == "agent_contract")
    assert check == {"name": "agent_contract", "ready": False, "code": "agent_manifest_contract_failed"}


def test_readiness_malformed_registry_is_a_controlled_failure(tmp_path):
    root = _fixture(tmp_path)
    registry = root / readiness.CONTROL_FILES["artifact_registry"]
    registry.write_text("schema_version: tw_product_artifact_registry_v1\nreadonly_only: true\nmodels: []\n", encoding="utf-8")
    result = readiness.research_readiness(repo_root=root)
    assert result["ready"] is False
    check = next(item for item in result["checks"] if item["name"] == "registry_contract")
    assert check["code"] == "registry_contract_failed"


def test_runtime_safety_fails_when_any_write_or_trading_worker_is_enabled(monkeypatch):
    for name in readiness.UNSAFE_RESEARCH_RUNTIME_FLAGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("DISABLE_RESTORE_RUNNING_STRATEGIES", raising=False)
    assert readiness.research_runtime_safety() == {
        "ready": True, "code": "ok", "mode": "readonly_research",
    }
    monkeypatch.setenv("ENABLE_PENDING_ORDER_WORKER", "true")
    assert readiness.research_runtime_safety() == {
        "ready": False, "code": "readonly_runtime_boundary_failed", "mode": "readonly_research",
    }


def test_runtime_safety_fails_when_strategy_restore_is_enabled(monkeypatch):
    for name in readiness.UNSAFE_RESEARCH_RUNTIME_FLAGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DISABLE_RESTORE_RUNNING_STRATEGIES", "false")
    assert readiness.research_runtime_safety()["ready"] is False


def test_ready_endpoint_uses_503_for_local_contract_failure(client, monkeypatch):
    from app.routes import health

    monkeypatch.setattr(health, "is_postgres_available", lambda: True)
    monkeypatch.setattr(health, "research_runtime_safety", lambda: {"ready": True, "code": "ok"})
    monkeypatch.setattr(health, "research_readiness", lambda: {
        "ready": False, "status": "not_ready", "checked_at": "2026-09-18T00:00:00Z",
        "signal_asof": None, "checks": [], "side_effects": "none",
    })
    response = client.get("/api/ready")
    assert response.status_code == 503
    assert response.get_json()["ready"] is False


def test_ready_endpoint_is_get_only(client, monkeypatch):
    from app.routes import health

    monkeypatch.setattr(health, "is_postgres_available", lambda: True)
    monkeypatch.setattr(health, "research_runtime_safety", lambda: {"ready": True, "code": "ok"})
    monkeypatch.setattr(health, "research_readiness", lambda: {
        "ready": True, "status": "ready", "checked_at": "2026-09-18T00:00:00Z",
        "signal_asof": "2026-09-18", "checks": [], "side_effects": "none",
    })
    assert client.get("/api/ready").status_code == 200
    assert client.get("/ready").status_code == 200
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/api/ready").status_code == 405


def test_ready_endpoint_rejects_unsafe_runtime(client, monkeypatch):
    from app.routes import health

    monkeypatch.setattr(health, "is_postgres_available", lambda: True)
    monkeypatch.setattr(health, "research_readiness", lambda: {
        "ready": True, "status": "ready", "checked_at": "2026-09-18T00:00:00Z",
        "signal_asof": "2026-09-18", "checks": [], "side_effects": "none",
    })
    monkeypatch.setattr(health, "research_runtime_safety", lambda: {
        "ready": False, "code": "readonly_runtime_boundary_failed", "mode": "readonly_research",
    })
    response = client.get("/api/ready")
    assert response.status_code == 503
    assert response.get_json()["checks"]["readonly_runtime_boundary"]["ready"] is False
