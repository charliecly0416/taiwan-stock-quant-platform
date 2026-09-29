import json
import sys

import pandas as pd
import pytest
import yaml

from clean_product import cli
from clean_product.data import DataCatalog, DataError, FinMindAdapter
from clean_product.models import ModelRunner, SignalResult
from clean_product.orchestrator import run_daily
from clean_product.config import datasets
from clean_product.service import ProductService
from pathlib import Path


def config(tmp_path):
    cfg = {"data_root": str(tmp_path / "data"), "artifact_root": str(tmp_path / "artifacts"),
           "strategy": "top50_exit_one_worst_sell", "execution": "next_open",
           "datasets": {"prices": {"source": "fixture", "endpoint": "fixture",
                                   "fields": ["stock_id", "date", "close"]},
                        "institutional": {"source": "fixture", "endpoint": "missing_fixture",
                                         "fields": ["stock_id", "date", "buy"]}},
           "model_stages": {"test": {}},
           "models": {"model_a": {"role": "baseline", "stages": ["test"],
                                   "required_datasets": ["prices"]},
                      "b": {"role": "shadow", "stages": ["test"],
                             "required_datasets": ["prices", "institutional"]}}}
    target = tmp_path / "product.yaml"; target.write_text(yaml.safe_dump(cfg))
    return cfg, target


def fake_signal(self, model, asof, **kwargs):
    rows = pd.DataFrame([{"date": asof, "instrument": "TW2330", "score": .5, "rank": 1}])
    return SignalResult(model, asof, rows)


def test_shadow_data_failure_does_not_block_baseline(tmp_path, monkeypatch):
    cfg, target = config(tmp_path)
    monkeypatch.setattr(ModelRunner, "run", fake_signal)
    result = run_daily("2026-09-25", config_path=target)
    assert result["status"] == "READY"
    tracks = {item["model"]: item for item in result["models"]}
    baseline, shadow = tracks["model_a"], tracks["b"]
    assert baseline["status"] == "READY"
    assert shadow["status"] == "BLOCKED" and shadow["mainline_blocking"] is False
    assert shadow["reason"] == "REQUIRED_DATASET_UNAVAILABLE: institutional"
    assert result["trigger_reason"] == "manual" and result["latest_pointer_written"] is False


def test_baseline_data_failure_is_blocking_and_does_not_execute_model(tmp_path, monkeypatch):
    cfg, target = config(tmp_path)
    monkeypatch.setattr(DataCatalog, "fetch", lambda *args, **kwargs: (_ for _ in ()).throw(DataError("missing")))
    monkeypatch.setattr(ModelRunner, "run", lambda *args, **kwargs: pytest.fail("missing data reached model"))
    result = run_daily("2026-09-25", config_path=target)
    tracks = {item["model"]: item for item in result["models"]}
    assert result["status"] == "BLOCKED" and tracks["model_a"]["mainline_blocking"] is True
    assert result["keep_previous_latest_on_failure"] is True


def test_shadow_execution_exception_is_recorded_without_aborting_baseline(tmp_path, monkeypatch):
    cfg, target = config(tmp_path); cfg["models"]["b"]["required_datasets"] = ["prices"]
    target.write_text(yaml.safe_dump(cfg))
    def signal(self, model, asof, **kwargs):
        if model == "b": raise RuntimeError("missing frozen asset")
        return fake_signal(self, model, asof, **kwargs)
    monkeypatch.setattr(ModelRunner, "run", signal)
    result = run_daily("2026-09-25", config_path=target)
    assert result["status"] == "READY"
    assert next(item for item in result["models"] if item["model"] == "b")["reason"] == "MODEL_EXECUTION_FAILED: RuntimeError"


def test_enabled_shadow_lane_builds_features_after_baseline(tmp_path, monkeypatch):
    cfg, target = config(tmp_path)
    cfg["daily"] = {"include_shadow": True}
    cfg["models"]["b"]["required_datasets"] = ["prices"]
    target.write_text(yaml.safe_dump(cfg))
    calls = []

    def feature_step(**kwargs):
        calls.append(kwargs["model_a"])
        return {"path": str(tmp_path / "FEATURE_ARTIFACT_DELTA.parquet"), "sha256": "abc", "rows": 1, "status": "READY"}

    monkeypatch.setattr("clean_product.orchestrator._prepare_shadow_features", feature_step)
    monkeypatch.setattr(ModelRunner, "run", fake_signal)
    result = run_daily("2026-09-25", config_path=target)
    shadow = next(item for item in result["models"] if item["model"] == "b")
    assert result["status"] == "READY" and shadow["status"] == "READY"
    assert shadow["feature_artifact"]["status"] == "READY" and calls


def test_cli_preserves_blocked_exit_status(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["product", "daily", "--dry-run"])
    monkeypatch.setattr(cli, "run_daily", lambda *args, **kwargs: {"status": "BLOCKED"})
    assert cli.main() == 1
    assert json.loads(capsys.readouterr().out)["status"] == "BLOCKED"


def test_manual_retry_keeps_scheduled_run_evidence(tmp_path, monkeypatch):
    cfg, target = config(tmp_path)
    monkeypatch.setattr(ModelRunner, 'run', fake_signal)
    scheduled = run_daily('2026-09-25', config_path=target, trigger_reason='scheduled')
    before = list((Path(cfg['artifact_root']) / 'daily').glob('*/*/run.json'))
    original = before[0].read_bytes()
    manual = run_daily('2026-09-25', config_path=target, trigger_reason='manual')
    assert scheduled['run_id'] != manual['run_id']
    assert before[0].read_bytes() == original
    state = ProductService(cfg).operations()
    assert state['latest_scheduled']['run_id'] == scheduled['run_id']
    assert state['latest_manual']['run_id'] == manual['run_id']


def test_http_failure_never_exposes_query_token(tmp_path, monkeypatch):
    import requests
    cfg, _ = config(tmp_path); cfg["universe"] = ["TW2330"]
    monkeypatch.setenv("FINMIND_TOKEN", "fixture-token-only")
    def fail(*args, **kwargs):
        raise requests.HTTPError("https://example.invalid?token=fixture-token-only")
    monkeypatch.setattr("clean_product.data.requests.get", fail)
    with pytest.raises(DataError) as error:
        FinMindAdapter().fetch(datasets(cfg)["prices"], asof="2026-09-25", start="2026-09-24", config=cfg)
    assert "fixture-token-only" not in str(error.value) and "HTTPError" in str(error.value)


def test_local_candidate_never_fetches_and_agent_failure_is_nonblocking(tmp_path, monkeypatch):
    cfg, target = config(tmp_path); cfg['agent'] = {'build_daily_prompt': True}
    target.write_text(yaml.safe_dump(cfg))
    monkeypatch.setattr(DataCatalog, 'fetch', lambda *a, **k: pytest.fail('local candidate fetched data'))
    monkeypatch.setattr(ModelRunner, 'run', fake_signal)
    monkeypatch.setattr('clean_product.agent_builder.build_prompt', lambda *a, **k: (_ for _ in ()).throw(ValueError('missing artifact')))
    result = run_daily('2026-09-24', config_path=target, local_only=True)
    assert result['local_only'] and result['datasets'] == []
    assert result['status'] == 'READY'
    assert result['agent_prompt']['status'] == 'BLOCKED' and not result['agent_prompt']['mainline_blocking']
    assert not list(Path(cfg['artifact_root']).rglob('latest.json'))
