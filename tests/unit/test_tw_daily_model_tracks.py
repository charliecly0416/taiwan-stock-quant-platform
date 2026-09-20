from __future__ import annotations

import threading
from pathlib import Path

import pytest
import yaml

from scripts.tw_daily_model_tracks import DailyModelTrackError, run_daily_model_tracks


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/readonly_model_tracks.yaml"
RUNTIME_CONFIG = ROOT / "configs/daily_model_tracks.yaml"


def ready_dependencies() -> dict[str, dict[str, object]]:
    return {
        "qlib_provider": {"ready": True, "path": "/fixture/qlib"},
        "qlib_normalized": {"ready": True, "path": "/fixture/normalized"},
        "source_acquisition": {"ready": True, "value": "acquisition.fixture"},
        "decision_cutoff": {"ready": True, "value": "2026-09-18T10:00:00+00:00"},
        "orthogonal_handoff": {"ready": True, "path": "/fixture/handoff.json"},
        "provider_snapshot": {"ready": True, "path": "/fixture/provider_snapshot"},
        "next_session_open": {"ready": True, "value": "2026-09-21T01:00:00+00:00"},
        "twii_snapshot": {
            "ready": True,
            "value": {
                "twii_csv": "/fixture/TWII_NORMALIZED.csv",
                "twii_manifest": "/fixture/TWII_CAPTURE_MANIFEST.json",
            },
        },
    }


def test_two_tracks_run_as_peers_and_composite_reruns_model_a(tmp_path: Path) -> None:
    model_a_requests: list[dict[str, object]] = []
    rerank_requests: list[dict[str, object]] = []
    model_a_fan_out = threading.Barrier(2, timeout=2)

    def score_model_a(request):
        request = dict(request)
        model_a_requests.append(request)
        model_a_fan_out.wait()
        return {
            "ok": True,
            "status": "SCORED_ASOF_TARGET",
            "model_signal_artifact": f"{request['output_root']}/model_signal",
        }

    def rerank(request):
        request = dict(request)
        rerank_requests.append(request)
        return {
            "ok": True,
            "status": "READY_RESEARCH_SHADOW",
            "model_signal_artifact": f"{request['output_root']}/model_signal",
        }

    result = run_daily_model_tracks(
        asof="2026-09-18",
        batch_run_id="daily_fixture",
        output_root=tmp_path,
        dependency_states=ready_dependencies(),
        services={"model_a_scorer": score_model_a, "b19r2r_reranker": rerank},
    )

    assert result["ok"] is True
    assert result["status"] == "READY"
    assert len(model_a_requests) == 2
    requests_by_track = {request["track_id"]: request for request in model_a_requests}
    baseline_request = requests_by_track["model_a_only"]
    composite_request = requests_by_track["model_a_plus_b_b19r2r"]
    assert baseline_request["track_id"] == "model_a_only"
    assert composite_request["track_id"] == "model_a_plus_b_b19r2r"
    assert baseline_request["model_id"] == composite_request["model_id"]
    assert baseline_request["model_id"] == "e4_frozen_qlib_2018_2022"
    assert baseline_request["output_root"] != composite_request["output_root"]
    assert all(request["no_publish"] and request["no_latest"] for request in model_a_requests)
    assert rerank_requests[0]["model_a_signal_artifact"] == (
        f"{composite_request['output_root']}/model_signal"
    )
    assert rerank_requests[0]["model_a_source"] == "internal_same_track_score"
    assert rerank_requests[0]["model_id"] == "modelb_b19r2r_lambdarank_exact50_78f_v2"
    assert rerank_requests[0]["decision_cutoff"] == composite_request["decision_cutoff"]
    assert rerank_requests[0]["twii_snapshot"]["twii_csv"].endswith("TWII_NORMALIZED.csv")
    assert (
        result["tracks"]["model_a_plus_b_b19r2r"][
            "internal_model_a_signal_artifact"
        ]
        == rerank_requests[0]["model_a_signal_artifact"]
    )
    assert result["dependency_mode"] == "independent"
    assert result["execution_mode"] == "concurrent_fan_out"


def test_nonblocking_dependency_failure_does_not_block_required_track(tmp_path: Path) -> None:
    dependencies = ready_dependencies()
    dependencies["orthogonal_handoff"] = {"ready": False, "detail": "full data pending"}
    calls: list[str] = []

    def score_model_a(request):
        calls.append(str(request["track_id"]))
        return {"ok": True, "status": "READY", "model_signal_artifact": "/fixture/model_a"}

    result = run_daily_model_tracks(
        asof="2026-09-18",
        batch_run_id="daily_fixture",
        output_root=tmp_path,
        dependency_states=dependencies,
        services={"model_a_scorer": score_model_a},
    )

    assert result["ok"] is True
    assert result["status"] == "READY_WITH_NONBLOCKING_FAILURES"
    assert calls == ["model_a_only"]
    challenger = result["tracks"]["model_a_plus_b_b19r2r"]
    assert challenger["attempted"] is False
    assert challenger["status"] == "BLOCKED_DEPENDENCY_NOT_READY"
    assert challenger["missing_dependencies"] == ["orthogonal_handoff"]


def test_required_dependency_failure_blocks_batch_without_running_services(tmp_path: Path) -> None:
    dependencies = ready_dependencies()
    dependencies["qlib_provider"] = False

    def unexpected(_request):
        raise AssertionError("a blocked dependency must prevent scoring")

    result = run_daily_model_tracks(
        asof="2026-09-18",
        batch_run_id="daily_fixture",
        output_root=tmp_path,
        dependency_states=dependencies,
        services={"model_a_scorer": unexpected, "b19r2r_reranker": unexpected},
    )

    assert result["ok"] is False
    assert result["status"] == "BLOCKED_REQUIRED_TRACK"
    assert result["tracks"]["model_a_only"]["attempted"] is False
    assert result["tracks"]["model_a_plus_b_b19r2r"]["attempted"] is False


def test_challenger_failure_keeps_baseline_and_account_boundary(tmp_path: Path) -> None:
    def score_model_a(request):
        return {
            "ok": True,
            "status": "READY",
            "model_signal_artifact": f"{request['output_root']}/model_signal",
        }

    def blocked_rerank(_request):
        return {"ok": False, "status": "B19R2R_BLOCKED_TWII_CAPTURE"}

    result = run_daily_model_tracks(
        asof="2026-09-18",
        batch_run_id="daily_fixture",
        output_root=tmp_path,
        dependency_states=ready_dependencies(),
        services={"model_a_scorer": score_model_a, "b19r2r_reranker": blocked_rerank},
    )

    assert result["ok"] is True
    assert result["status"] == "READY_WITH_NONBLOCKING_FAILURES"
    assert result["default_track_id"] == "model_a_only"
    assert result["virtual_account_allowed_track_ids"] == ["model_a_only"]
    assert result["tracks"]["model_a_only"]["ok"] is True
    assert result["tracks"]["model_a_plus_b_b19r2r"]["ok"] is False
    assert result["tracks"]["model_a_plus_b_b19r2r"]["blocking"] is False
    assert result["tracks"]["model_a_plus_b_b19r2r"]["artifact_type"] == "ModelSignalArtifact"
    assert result["tracks"]["model_a_plus_b_b19r2r"]["production_allowed"] is False
    assert result["tracks"]["model_a_plus_b_b19r2r"]["source_snapshot_id"] == "acquisition.fixture"


def test_runtime_config_declares_no_cross_track_consumption() -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    runtime = yaml.safe_load(RUNTIME_CONFIG.read_text(encoding="utf-8"))
    runtime_tracks = runtime["tracks"]

    assert set(runtime_tracks) == set(config["tracks"])
    assert all(value["consumes_track_outputs"] == [] for value in runtime_tracks.values())
    assert runtime_tracks["model_a_plus_b_b19r2r"]["internal_stages"] == [
        "model_a_score",
        "b19r2r_rerank",
    ]
    assert runtime["dependency_mode"] == "independent"
    assert runtime["default_max_workers"] == 2


def test_runtime_config_rejects_cross_track_adapter_swap(tmp_path: Path) -> None:
    runtime = yaml.safe_load(RUNTIME_CONFIG.read_text(encoding="utf-8"))
    runtime["tracks"]["model_a_plus_b_b19r2r"][
        "runtime_adapter_id"
    ] = "daily_model_a_v1"
    mutated = tmp_path / "daily_model_tracks.yaml"
    mutated.write_text(yaml.safe_dump(runtime, sort_keys=False), encoding="utf-8")

    with pytest.raises(DailyModelTrackError, match="adapter identity mismatch"):
        run_daily_model_tracks(
            asof="2026-09-18",
            batch_run_id="daily_fixture",
            output_root=tmp_path / "out",
            dependency_states=ready_dependencies(),
            services={},
            runtime_config_path=mutated,
        )
