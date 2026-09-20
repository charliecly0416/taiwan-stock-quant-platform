from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

from tw_stock_strategy import CANONICAL_CONFIG, StrategyContractError, decide_for_model
from tw_stock_workflow import dual_track
from tw_stock_workflow.dual_track import _load_frames, _track_config, _track_input_ref
from tw_stock_workflow.types import WorkflowError
from tw_stock_workflow.spec import WorkflowSpec
from scripts.validate_tw_modular_m_contracts import validate_golden_sample


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/tw_stock_strategy/wf5a_model_a_20260106.csv"


def _signals() -> list[dict[str, object]]:
    with FIXTURE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for field in ("candidate_rank", "score_rank", "full_qlib_rank"):
            row[field] = int(row[field])
        for field in ("buy_score", "raw_score"):
            row[field] = float(row[field])
        row["model_name"] = "example_registered_model"
        row["model_family"] = "ltr"
    by_full_rank = {int(row["full_qlib_rank"]): row for row in rows}
    by_full_rank[50]["candidate_rank"] = 51
    by_full_rank[51]["candidate_rank"] = 50
    return rows


def test_registered_model_uses_same_strategy_with_separate_candidate_and_full_ranks() -> None:
    decision = decide_for_model(
        _signals(),
        [],
        CANONICAL_CONFIG,
        model_id="example_registered_model",
        model_family="ltr",
        candidate_rank_policy="frozen_eligible_exact50",
    )
    assert decision.model_name == "example_registered_model"
    assert decision.strategy_rule == "top50_exit_one_worst_sell"
    assert len(decision.buy) == 1
    assert decision.max_buy_count == decision.max_sell_count == 1


def test_registered_model_identity_still_fails_closed() -> None:
    with pytest.raises(StrategyContractError, match="authorized model identity"):
        decide_for_model(
            _signals(),
            [],
            CANONICAL_CONFIG,
            model_id="different_model",
            model_family="ltr",
            candidate_rank_policy="frozen_eligible_exact50",
        )


def test_track_registry_separates_framework_role_from_governance() -> None:
    registry = yaml.safe_load((ROOT / "configs/readonly_model_tracks.yaml").read_text(encoding="utf-8"))
    tracks = registry["tracks"]
    assert registry["default_track_id"] == "model_a_only"
    assert {track["framework_role"] for track in tracks.values()} == {"model_track"}
    assert tracks["model_a_only"]["workflow_policy"] == "required"
    assert tracks["model_a_plus_b_b19r2r"]["workflow_policy"] == "nonblocking"
    assert tracks["model_a_only"]["adapter_id"] == "model_a_passthrough_v1"
    assert tracks["model_a_plus_b_b19r2r"]["adapter_id"] == "b19r2r_lambdarank_78f_v1"
    assert registry["virtual_account_policy"]["allowed_track_ids"] == ["model_a_only"]
    assert tracks["model_a_only"]["candidate_rank_policy"] == "full_rank"
    assert tracks["model_a_plus_b_b19r2r"]["candidate_rank_policy"] == "original_top50_exclude_tw7769_no_replacement"
    assert _track_config(ROOT, "model_a_only")["production_default"] is True
    with pytest.raises(Exception, match="unknown readonly model track"):
        _track_config(ROOT, "unknown")


def test_unknown_future_model_adapter_fails_before_loading_model_a(monkeypatch, tmp_path) -> None:
    registry = yaml.safe_load((ROOT / "configs/readonly_model_tracks.yaml").read_text(encoding="utf-8"))
    registry["tracks"]["future_model"] = {
        **registry["tracks"]["model_a_only"],
        "adapter_id": "unknown_adapter_v1",
        "display_name": "Future model",
        "model_id": "future_model_v1",
        "governance_status": "research_candidate",
        "workflow_policy": "nonblocking",
        "virtual_account_eligible": False,
        "production_default": False,
    }
    registry_path = tmp_path / "readonly_model_tracks.yaml"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(dual_track, "TRACK_CONFIG", registry_path)
    monkeypatch.setattr(
        dual_track.pd,
        "read_parquet",
        lambda *args, **kwargs: pytest.fail("unknown adapter must fail before reading model data"),
    )

    with pytest.raises(WorkflowError, match="unknown readonly model track adapter: unknown_adapter_v1"):
        _load_frames(ROOT, "future_model")


def test_known_model_a_adapter_rejects_future_model_identity_before_data_read(monkeypatch, tmp_path) -> None:
    registry = yaml.safe_load((ROOT / "configs/readonly_model_tracks.yaml").read_text(encoding="utf-8"))
    registry["tracks"]["future_model"] = {
        **registry["tracks"]["model_a_only"],
        "display_name": "Future model",
        "model_id": "future_model_v1",
        "governance_status": "research_candidate",
        "workflow_policy": "nonblocking",
        "virtual_account_eligible": False,
        "production_default": False,
    }
    registry_path = tmp_path / "readonly_model_tracks.yaml"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(dual_track, "TRACK_CONFIG", registry_path)
    monkeypatch.setattr(
        dual_track.pd,
        "read_parquet",
        lambda *args, **kwargs: pytest.fail("adapter identity mismatch must fail before reading model data"),
    )

    with pytest.raises(WorkflowError, match="readonly model track adapter identity mismatch: model_a_passthrough_v1"):
        _load_frames(ROOT, "future_model")


def test_track_input_refs_are_adapter_specific_and_keep_model_a_independent_from_b19_inputs() -> None:
    model_a_ref = _track_input_ref(ROOT, "model_a_only")
    model_b_ref = _track_input_ref(ROOT, "model_a_plus_b_b19r2r")

    assert model_a_ref.adapter_id == "readonly_model_track.model_a_passthrough_v1"
    assert model_a_ref.model_id == "e4_frozen_qlib_2018_2022"
    assert model_a_ref.run_id == "model_a_frozen_complete_20260813_20260901"
    assert model_a_ref.manifest_path.endswith("model_a_passthrough_v1.json")
    assert not any(
        marker in path
        for path in model_a_ref.metadata
        for marker in ("FEATURE_ARTIFACT_78_RAW", "training_output_v1", "B19R2R_INPUT_MATERIALIZATION_STATE")
    )

    assert model_b_ref.adapter_id == "readonly_model_track.b19r2r_lambdarank_78f_v1"
    assert model_b_ref.model_id == "modelb_b19r2r_lambdarank_exact50_78f_v2"
    assert model_b_ref.run_id == "b19r2r_retrospective_complete_20260813_20260901"
    assert model_b_ref.manifest_path.endswith("b19r2r_lambdarank_78f_v1.json")
    assert any("FEATURE_ARTIFACT_78_RAW" in path for path in model_b_ref.metadata)
    assert any("training_output_v1" in path for path in model_b_ref.metadata)
    assert any("B19R2R_INPUT_MATERIALIZATION_STATE" in path for path in model_b_ref.metadata)


def test_workflow_keeps_a_required_and_challenger_nonblocking() -> None:
    spec = WorkflowSpec.load(ROOT / "configs/workflows/readonly_dual_model_track_comparison.yaml")
    nodes = {node.node_id: node for node in spec.nodes}
    assert nodes["model_a"].policy == "required"
    assert nodes["model_a_plus_b"].policy == "nonblocking"
    assert nodes["model_a_catalog"].policy == "required"
    assert nodes["model_a_catalog"].needs == ("model_a",)
    assert nodes["comparison"].policy == "nonblocking"
    assert nodes["comparison"].needs == ("model_a", "model_a_plus_b", "model_a_catalog")


def test_no_replacement_policy_allows_missing_original_top50_rank_but_never_promotes_rank_51() -> None:
    rows = _signals()
    by_full_rank = {int(row["full_qlib_rank"]): row for row in rows}
    by_full_rank[50]["candidate_rank"] = 200
    by_full_rank[51]["candidate_rank"] = 51
    decision = decide_for_model(
        rows,
        [],
        CANONICAL_CONFIG,
        model_id="example_registered_model",
        model_family="ltr",
        candidate_rank_policy="original_top50_exclude_tw7769_no_replacement",
    )
    assert by_full_rank[51]["instrument"] not in decision.buy

    by_full_rank[51]["candidate_rank"] = 50
    with pytest.raises(StrategyContractError, match="cannot replace"):
        decide_for_model(
            rows,
            [],
            CANONICAL_CONFIG,
            model_id="example_registered_model",
            model_family="ltr",
            candidate_rank_policy="original_top50_exclude_tw7769_no_replacement",
        )


def test_dual_track_module_has_no_publish_or_account_write_calls() -> None:
    source = (ROOT / "tw_stock_workflow/dual_track.py").read_text(encoding="utf-8")
    for forbidden in (
        "provider_publish",
        "accepted_latest_switch",
        "paper_portfolio.save",
        "broker.place_order",
        "requests.post",
        ".fit(",
        ".train(",
    ):
        assert forbidden not in source


def test_readonly_historical_track_registry_golden_samples() -> None:
    root = ROOT / "tests/fixtures/tw_modular_contracts/model_signal"
    passed = validate_golden_sample(root / "pass_readonly_historical_track_adapter")
    rejected = validate_golden_sample(root / "fail_readonly_historical_track_provider_write")
    assert passed["ok"] is True and passed["expectation_ok"] is True
    assert rejected["ok"] is False and rejected["expectation_ok"] is True
    assert rejected["actual_error_codes"] == ["required_flag_false"]
