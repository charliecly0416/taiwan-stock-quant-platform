"""Readiness proves a materialized signal; health only proves the server lives."""
import json

import pandas as pd
import pytest

from backend.app import create_app
from clean_product.artifacts import sha256
from clean_product.models import ModelRunner
from clean_product.service import ProductService


def configured(tmp_path):
    provider = tmp_path / "provider"
    (provider / "calendars").mkdir(parents=True)
    (provider / "calendars/day.txt").write_text("2026-09-24\n")
    model = tmp_path / "frozen.pkl"; model.write_bytes(b"isolated-test-model")
    return {"artifact_root": str(tmp_path / "artifacts"), "data_root": str(tmp_path / "data"),
            "product": {"default_model": "model_a"},
            "models": {"model_a": {"role": "baseline", "production_allowed": True,
                                       "stages": ["model_a_frozen"]}},
            "model_stages": {"model_a_frozen": {"provider_uri": str(provider),
                                                  "model_path": str(model), "model_sha256": sha256(model)}}}


def materialize(cfg):
    runner = ModelRunner(cfg)
    runner.stages.register("model_a_frozen", lambda *args, **kwargs: pd.DataFrame([
        {"date": "2026-09-24", "instrument": "TW2330", "rank": 1, "score": .5}]))
    result = runner.run("model_a", "2026-09-24")
    assert result.status == "READY"
    return result.artifact_dir


@pytest.mark.parametrize("fault", [None, "missing", "checksum", "full_ranks", "candidate_rank", "model"])
def test_readiness_validates_current_signal_without_scoring(tmp_path, monkeypatch, fault):
    cfg = configured(tmp_path)
    if fault != "missing":
        root = materialize(cfg)
        manifest = root / "manifest.json"; payload = json.loads(manifest.read_text())
        if fault == "full_ranks":
            payload["full_qlib_ranks"] = {"TW2330": 2}
        if fault in ("checksum", "candidate_rank"):
            rows = pd.read_csv(root / "signals.csv"); rows["candidate_rank"] = 99
            rows.to_csv(root / "signals.csv", index=False)
            if fault == "candidate_rank": payload["files"]["signals"]["sha256"] = sha256(root / "signals.csv")
        manifest.write_text(json.dumps(payload))
    if fault == "model":
        (tmp_path / "frozen.pkl").write_bytes(b"wrong-model")
    service = ProductService(cfg)
    monkeypatch.setattr("clean_product.service.ProductService", lambda: service)
    monkeypatch.setattr(service.runner, "run", lambda *args, **kwargs: pytest.fail("readiness ran a model"))
    client = create_app().test_client()
    result = client.get("/api/ready")
    assert result.status_code == (200 if fault is None else 503)
    assert result.json["ready"] is (fault is None)
    assert client.get("/api/health").status_code == 200


def test_market_empty_window_is_blocked(tmp_path, monkeypatch):
    service = ProductService(configured(tmp_path))
    monkeypatch.setattr(service.catalog, "query_local_source", lambda *args: pd.DataFrame(
        columns=["stock_id", "date", "close"]))
    result = service.market("2330", "2026-09-23", "2026-09-24")
    assert result["status"] == "BLOCKED" and result["reason"] == "MARKET_DATA_UNAVAILABLE"
