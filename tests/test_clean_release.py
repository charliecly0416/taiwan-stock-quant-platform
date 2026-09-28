"""A failed or repeated daily job must not damage the serving release."""
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml
from backend.app import create_app

from clean_product.agent import simple_chat
from clean_product.artifacts import sha256
from clean_product.config import env_config, load_config
from clean_product.orchestrator import run_daily
from clean_product.service import ProductService


@pytest.fixture
def release_config(tmp_path, monkeypatch):
    provider = tmp_path / "provider"
    (provider / "calendars").mkdir(parents=True)
    (provider / "calendars/day.txt").write_text("2026-09-23\n2026-09-24\n")
    model = tmp_path / "model.pkl"
    model.write_bytes(b"frozen-test-model")
    cfg = {"data_root": str(tmp_path / "data"), "artifact_root": str(tmp_path / "artifacts"),
           "product": {"default_model": "model_a"}, "strategy": "top50_exit_one_worst_sell",
           "execution": "next_open", "agent": {"build_daily_prompt": True},
           "datasets": {}, "universe_file": str(tmp_path / "all.txt"),
           "model_stages": {"model_a_frozen": {"model_path": str(model), "model_sha256": sha256(model),
               "provider_uri": str(provider), "selection_prices": str(tmp_path / "normalized"),
               "selection_universe": str(tmp_path / "selection.txt")}},
           "models": {"model_a": {"role": "baseline", "canonical_id": "canonical-test",
               "production_allowed": True, "stages": ["model_a_frozen"]}}}
    cfg["datasets"]["prices"] = {"source": "qlib_provider", "endpoint": "prices", "params": {"provider_uri": str(provider)}}
    target = tmp_path / "product.yaml"
    target.write_text(yaml.safe_dump(cfg))
    monkeypatch.setattr("clean_product.models._model_a_frozen", lambda *a, asof, **k: pd.DataFrame([
        {"date": asof, "instrument": "TW2330", "score": .25, "rank": 1}]))
    return cfg, target


def test_publish_repeat_is_immutable_and_readable_after_process_reload(release_config):
    cfg, target = release_config
    first = run_daily("2026-09-24", config_path=target, local_only=True, publish=True)
    assert first["status"] == "READY" and first["latest_pointer_written"]
    effective = env_config(load_config(target))
    previous = {p: p.read_bytes() for p in effective["artifact_root"].rglob("*") if p.is_file()}
    assert ProductService(cfg).readiness()["ready"]
    assert simple_chat(effective, "排名第一是谁？", "2026-09-24")["status"] == "READY"
    second = run_daily("2026-09-24", config_path=target, local_only=True, publish=True)
    assert second["status"] == "READY" and second["run_id"] != first["run_id"]
    assert all(p.read_bytes() == content for p, content in previous.items())
    assert ProductService(cfg).readiness()["ready"]
    assert simple_chat(env_config(load_config(target)), "排名第一是谁？", "2026-09-24")["status"] == "READY"
    resolved = env_config(load_config(target))
    assert Path(resolved["model_stages"]["model_a_frozen"]["selection_universe"]) == Path(
        resolved["model_stages"]["model_a_frozen"]["provider_uri"]) / "instruments/all.txt"
    client = create_app({"PRODUCT_CONFIG": cfg, "AGENT_REMOTE_DISABLED": True}).test_client()
    response = client.post("/api/tw-stock/agent/simple-chat", json={"question": "排名第一是谁？"})
    assert response.status_code == 200 and response.json["status"] == "READY"
    assert response.json["context_digest"]["signal_asof"] == "2026-09-24"


def test_failed_prompt_retains_previous_release(release_config, monkeypatch):
    cfg, target = release_config
    run_daily("2026-09-24", config_path=target, local_only=True, publish=True)
    pointer = Path(cfg["artifact_root"]) / "active.json"
    before = pointer.read_bytes()
    monkeypatch.setattr("clean_product.agent_builder.build_prompt", lambda *a: (_ for _ in ()).throw(OSError("failure")))
    failed = run_daily("2026-09-24", config_path=target, local_only=True, publish=True)
    assert failed["status"] == "BLOCKED" and not failed["latest_pointer_written"]
    assert pointer.read_bytes() == before and ProductService(cfg).readiness()["ready"]


def test_dry_run_cannot_publish(release_config):
    _, target = release_config
    with pytest.raises(ValueError, match="FIXTURE_PUBLICATION_FORBIDDEN"):
        run_daily("2026-09-24", config_path=target, dry_run=True, publish=True)


def test_retroactive_release_cannot_move_current_date_backwards(release_config):
    _, target = release_config
    run_daily("2026-09-24", config_path=target, local_only=True, publish=True)
    with pytest.raises(ValueError, match="DATE_REGRESSION"):
        run_daily("2026-09-23", config_path=target, local_only=True, publish=True)


def test_no_new_session_skips_refresh_and_preserves_active_release(release_config, monkeypatch):
    cfg, target = release_config
    run_daily("2026-09-24", config_path=target, local_only=True, publish=True)
    pointer = Path(cfg["artifact_root"]) / "active.json"
    previous = pointer.read_bytes()
    monkeypatch.setattr("clean_product.provider_refresh.market_asof", lambda *a: "2026-09-24")
    def forbidden(*args, **kwargs):
        raise AssertionError("no new market session must not refresh prices")
    monkeypatch.setattr("clean_product.provider_refresh.refresh_yahoo_provider", forbidden)
    result = run_daily(config_path=target, publish=True, trigger_reason="scheduled")
    assert result["status"] == "READY" and result["reason"] == "NO_NEW_MARKET_SESSION"
    assert result["trigger_reason"] == "scheduled" and not result["latest_pointer_written"]
    assert pointer.read_bytes() == previous
    status = json.loads((pointer.parent / "scheduler_status.json").read_text())
    assert status == result
