from __future__ import annotations

import pytest

from tw_stock_workflow.data_pipeline import (
    DataPipeline,
    DataPipelineError,
    DataPipelineRequest,
)


def test_data_pipeline_runs_stages_in_order_and_keeps_outputs() -> None:
    calls: list[str] = []

    def acquire(request: DataPipelineRequest) -> dict[str, object]:
        calls.append(f"acquire:{request.asof}")
        return {"status": "READY", "run_id": "source-1"}

    def normalize(request: DataPipelineRequest, source: dict[str, object]) -> dict[str, object]:
        calls.append(f"normalize:{source['run_id']}")
        return {"status": "READY", "run_id": "normalized-1", "source_run_id": source["run_id"]}

    def store(request: DataPipelineRequest, normalized: dict[str, object]) -> dict[str, object]:
        calls.append(f"store:{normalized['run_id']}")
        return {"status": "READY", "provider_path": "provider/run-1"}

    result = DataPipeline(acquire=acquire, normalize=normalize, store=store).run(
        DataPipelineRequest(asof="2026-09-18", symbols=("tw2330", "tw2317"))
    )

    assert result.status == "READY"
    assert result.stopped_at is None
    assert calls == ["acquire:2026-09-18", "normalize:source-1", "store:normalized-1"]
    assert result.request.symbols == ("TW2330", "TW2317")
    assert result.to_dict()["stages"]["storage"]["provider_path"] == "provider/run-1"


def test_data_pipeline_stops_before_downstream_on_blocked_source() -> None:
    calls: list[str] = []

    def acquire(request: DataPipelineRequest) -> dict[str, str]:
        calls.append("acquire")
        return {"status": "BLOCKED", "reason": "provider_missing_target_asof"}

    def normalize(request: DataPipelineRequest, source: dict[str, str]) -> dict[str, str]:
        calls.append("normalize")
        return {"status": "READY"}

    def store(request: DataPipelineRequest, normalized: dict[str, str]) -> dict[str, str]:
        calls.append("store")
        return {"status": "READY"}

    result = DataPipeline(acquire=acquire, normalize=normalize, store=store).run(
        DataPipelineRequest(asof="2026-09-18")
    )

    assert result.status == "BLOCKED"
    assert result.stopped_at == "acquisition"
    assert calls == ["acquire"]
    assert result.stages["acquisition"]["reason"] == "provider_missing_target_asof"


def test_data_pipeline_rejects_invalid_stage_payload_and_request() -> None:
    with pytest.raises(DataPipelineError, match="invalid canonical asof"):
        DataPipelineRequest(asof="2026/09/18")

    pipeline = DataPipeline(
        acquire=lambda request: {"status": "READY"},
        normalize=lambda request, source: {"status": "READY"},
        store=lambda request, normalized: {"artifact_path": "missing-status"},
    )
    with pytest.raises(DataPipelineError, match="storage stage must return status"):
        pipeline.run(DataPipelineRequest(asof="2026-09-18"))
