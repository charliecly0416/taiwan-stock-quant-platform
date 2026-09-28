import json
from pathlib import Path

import pandas as pd
import pytest

from clean_product.artifacts import sha256
from clean_product.models import ModelRunner, _archive_prediction
from clean_product.service import ProductService
from clean_product.strategy import top50_exit_one_worst_sell


def config(tmp_path):
    return {"data_root": str(tmp_path / "data"), "artifact_root": str(tmp_path / "artifacts"),
            "model_stages": {"test_stage": {}},
            "models": {"model_a": {"stages": ["test_stage"], "canonical_id": "test-baseline"}}}


def frame():
    return pd.DataFrame([{"date": "2026-09-24", "instrument": "TW2330", "score": .1, "rank": 1}])


@pytest.mark.parametrize("fault", ["checksum", "asof", "count", "identity", "config", "duplicate", "missing_csv", "missing_manifest"])
def test_corrupt_signal_is_blocked_without_silent_recomputation(tmp_path, monkeypatch, fault):
    cfg = config(tmp_path); runner = ModelRunner(cfg)
    runner.stages.register("test_stage", lambda *args, **kwargs: frame())
    signal = runner.run("model_a", "2026-09-24")
    directory = signal.artifact_dir; manifest = directory / "manifest.json"; csv = directory / "signals.csv"
    payload = json.loads(manifest.read_text())
    if fault in ("checksum", "duplicate"):
        pd.concat([pd.read_csv(csv)] * 2).to_csv(csv, index=False)
        if fault == "duplicate":
            payload["files"]["signals"]["sha256"] = sha256(csv); payload["row_count"] = 2
    elif fault == "asof": payload["asof"] = "2026-09-23"
    elif fault == "count": payload["row_count"] = 99
    elif fault == "identity": payload["canonical_id"] = "another-model"
    else: cfg["model_stages"]["test_stage"]["source"] = "changed"
    manifest.write_text(json.dumps(payload))
    if fault == "missing_csv": csv.unlink()
    if fault == "missing_manifest": manifest.unlink()
    service = ProductService(cfg)
    monkeypatch.setattr(service.runner, "run", lambda *args, **kwargs: pytest.fail("invalid artifact was bypassed"))
    result = service.signal("model_a", "2026-09-24")
    assert result.status == "BLOCKED" and result.rows.empty
    assert "SIGNAL_ARTIFACT_INVALID" in result.reason


def test_valid_signal_roundtrip_preserves_scores(tmp_path):
    cfg = config(tmp_path); runner = ModelRunner(cfg)
    runner.stages.register("test_stage", lambda *args, **kwargs: frame())
    runner.run("model_a", "2026-09-24")
    result = ProductService(cfg).signal("model_a", "2026-09-24")
    assert result.status == "READY" and result.rows.iloc[0].score == .1


def test_wrong_frozen_model_is_rejected_before_stage_execution(tmp_path):
    cfg = config(tmp_path); model = tmp_path / "model.pkl"; model.write_bytes(b"wrong-model")
    cfg["model_stages"]["test_stage"] = {"model_path": str(model), "model_sha256": "0" * 64}
    runner = ModelRunner(cfg)
    runner.stages.register("test_stage", lambda *args, **kwargs: pytest.fail("unverified model executed"))
    result = runner.run("model_a", "2026-09-24", write=False)
    assert result.status == "BLOCKED" and "CHECKSUM_MISMATCH" in result.reason
    assert result.artifact_dir is None


def test_empty_pipeline_cannot_report_ready(tmp_path):
    cfg = config(tmp_path); cfg["models"]["model_a"]["stages"] = []
    assert ModelRunner(cfg).run("model_a", "2026-09-24", write=False).status == "BLOCKED"


def test_failed_retry_cannot_replace_a_valid_signal(tmp_path):
    cfg = config(tmp_path); runner = ModelRunner(cfg)
    runner.stages.register('test_stage', lambda *args, **kwargs: frame())
    good = runner.run('model_a', '2026-09-24')
    original = (good.artifact_dir / 'manifest.json').read_bytes()
    runner.stages.register('test_stage', lambda *args, **kwargs: pd.DataFrame())
    failed = runner.run('model_a', '2026-09-24')
    assert failed.status == 'BLOCKED' and failed.artifact_dir != good.artifact_dir
    assert (good.artifact_dir / 'manifest.json').read_bytes() == original
    assert ProductService(cfg).signal('model_a', '2026-09-24').status == 'READY'


def test_archive_uses_verified_original_score_and_rank_without_refiltering(tmp_path):
    target = tmp_path / "archive.csv"
    pd.DataFrame([{"date": "2025-06-23", "instrument": "TW9999", "original_score": -.2, "original_rank": 2},
                  {"date": "2025-06-23", "instrument": "TW2330", "original_score": .5, "original_rank": 1}]).to_csv(target, index=False)
    stage = {"prediction_archive": str(target), "prediction_archive_sha256": sha256(target),
             "archive_score_column": "original_score", "archive_rank_column": "original_rank"}
    result = _archive_prediction(stage, "2025-06-23")
    assert result.instrument.tolist() == ["TW2330", "TW9999"]
    assert result.score.tolist() == [.5, -.2]
    target.write_text("changed")
    with pytest.raises(ValueError, match="CHECKSUM_MISMATCH"):
        _archive_prediction(stage, "2025-06-23")


def test_candidate_rank_and_full_cross_section_rank_remain_distinct(tmp_path):
    cfg = config(tmp_path)
    cfg['models']['model_a']['stages'] = ['model_a_frozen']
    cfg['model_stages'] = {'model_a_frozen': {}}
    runner = ModelRunner(cfg)
    rows = frame()
    rows.attrs['full_qlib_ranks'] = {'TW2317': 1, 'TW2330': 2, 'TW2303': 3}
    runner.stages.register('model_a_frozen', lambda *args, **kwargs: rows.copy())
    result = runner.run('model_a', '2026-09-24')
    assert result.rows.iloc[0].candidate_rank == 1
    assert result.rows.iloc[0].full_qlib_rank == 2
    loaded = ProductService(cfg).signal('model_a', '2026-09-24')
    assert loaded.status == 'READY' and loaded.full_ranks['TW2303'] == 3


def test_rerank_exit_uses_full_baseline_rank_for_fallen_holdings():
    signals = frame().assign(candidate_rank=1, full_qlib_rank=1)
    result = top50_exit_one_worst_sell(signals, {"TW0080", "TW0090"},
                                      full_ranks={"TW0080": 60, "TW0090": 100, "TW2330": 1})
    assert result[result.action.eq("sell")].instrument.tolist() == ["TW0090"]


def test_b19_fixture_excludes_7769_without_replacement(tmp_path):
    cfg = config(tmp_path)
    cfg["model_stages"] = {"model_a_frozen": {}, "b19r2r_frozen": {"exclude": ["TW7769"]}}
    cfg["models"]["b"] = {"stages": ["model_a_frozen", "b19r2r_frozen"]}
    symbols = ["7769"] + [str(i).zfill(4) for i in range(1, 51)]
    prices = pd.DataFrame({"stock_id": symbols, "date": "2026-09-24", "close": range(51, 0, -1)})
    result = ModelRunner(cfg).run("b", "2026-09-24", data={"prices": prices}, fixture=True, write=False)
    assert result.status == "READY" and len(result.rows) == 49
    assert "TW7769" not in set(result.rows.instrument) and "TW0050" not in set(result.rows.instrument)
    assert result.full_ranks["TW0050"] == 51


def test_fixture_rerank_cannot_read_future_prices(tmp_path):
    cfg = config(tmp_path)
    cfg["model_stages"] = {"model_a_frozen": {}, "b19r2r_frozen": {"exclude": ["TW7769"]}}
    cfg["models"]["b"] = {"stages": ["model_a_frozen", "b19r2r_frozen"]}
    prices = pd.DataFrame([{"stock_id": symbol, "date": day, "close": close}
                           for day in ("2026-09-23", "2026-09-24")
                           for symbol, close in (("2330", 100), ("2317", 99))])
    future = pd.DataFrame([{"stock_id": "2317", "date": "2026-09-25", "close": 999999}])
    runner = ModelRunner(cfg)
    before = runner.run("b", "2026-09-24", data={"prices": prices}, fixture=True, write=False)
    after = runner.run("b", "2026-09-24", data={"prices": pd.concat([prices, future])}, fixture=True, write=False)
    pd.testing.assert_frame_equal(before.rows, after.rows)
