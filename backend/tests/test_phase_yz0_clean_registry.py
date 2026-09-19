from __future__ import annotations

from pathlib import Path

import yaml

from app.services.readonly_replay_window import ReadonlyReplayWindowError, default_replay_model_id, default_replay_strategy_rule, load_readonly_replay_window

ROOT = Path(__file__).resolve().parents[2]


def _yaml(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8")) or {}


def test_yz0_registry_keeps_model_b_out_of_production_selection():
    registry = _yaml("configs/tw_modular_registry.yaml")
    production = set((registry["production_models"]["production_selectable"] or {}).keys())
    assert production == {"e4_frozen_qlib_2018_2022"}
    research = registry["production_models"]["research_only"]
    model_b = research["e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"]
    assert model_b["frontend_selectable"] is False
    assert model_b["production_default"] is False
    assert model_b["production_allowed"] is False
    assert model_b["research_only"] is True
    forbidden = " ".join(production).lower()
    for token in ["p3", "o4", "fresh", "bridge", "2023_2025_ltr"]:
        assert token not in forbidden


def test_yz0_product_artifact_registry_centralizes_current_model_paths():
    product = _yaml("configs/tw_product_artifact_registry.yaml")
    assert product["schema_version"] == "tw_product_artifact_registry_v1"
    assert product["models"] == {
        "base_model_id": "e4_frozen_qlib_2018_2022",
        "treatment_model_id": "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025",
        "treatment_display_model_id": "e4_frozen_qlib_2023_2025_ltr",
    }
    assert product["strategies"]["default_strategy_rule"] == "top50_exit_one_worst_sell"
    assert product["artifacts"]["signal_root"] == "data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals"
    assert product["artifacts"]["readonly_strategy_latest"] == "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
    assert product["rebuild_sources"]["e3_ltr_model"].endswith("phasee3_ltr_model.pkl")
    assert product["safety"]["no_provider_publish"] is True
    assert product["safety"]["no_accepted_latest_switch"] is True
    assert product["safety"]["no_broker_order"] is True


def test_yz0_strategy_layers_remove_origin_and_neutralize_buggy():
    registry = _yaml("configs/tw_modular_registry.yaml")
    strategies = registry["strategies"]
    production = set(strategies["production_selectable"].keys())
    research = strategies["research_only"]
    deprecated = set(strategies["deprecated"].keys())
    assert production == {"top50_exit_one_worst_sell"}
    assert "original" not in production and "origin" not in production
    assert {"original", "origin"}.issubset(deprecated)
    assert "one_sell_one_buy_buggy_e8r" in research
    assert research["one_sell_one_buy_buggy_e8r"]["display_name"] == "单换手异常候选（研究）"
    assert "buggy" not in research["one_sell_one_buy_buggy_e8r"]["display_name"].lower()
    assert research["one_sell_one_buy_buggy_e8r"]["production_default"] is False


def test_yz0_replay_policy_and_route_defaults_are_clean():
    policy = _yaml("configs/tw_replay_window_policy.yaml")
    assert set(policy["models"].keys()) == {
        "e4_frozen_qlib_2018_2022",
        "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025",
    }
    assert policy["default_model_id"] == "e4_frozen_qlib_2018_2022"
    assert policy["default_strategy_rule"] == "top50_exit_one_worst_sell"
    assert default_replay_model_id() == policy["default_model_id"]
    assert default_replay_strategy_rule() == policy["default_strategy_rule"]
    route_source = (ROOT / "backend/app/routes/readonly_replay_window.py").read_text(encoding="utf-8")
    assert "e4_frozen_qlib_2023_2025_ltr" not in route_source
    assert "default_replay_model_id" in route_source
    assert "default_replay_strategy_rule" in route_source


def test_yz0_replay_window_rejects_old_deprecated_and_research_only_inputs():
    cases = [
        ("e4_frozen_qlib_2023_2025_ltr", "top50_exit_one_worst_sell", "deprecated_model_id"),
        ("e4_frozen_qlib_2018_2022", "original", "deprecated_strategy_rule"),
        ("e4_frozen_qlib_2018_2022", "one_sell_one_buy_buggy_e8r", "research_only_strategy_not_valid_strategy_evidence"),
    ]
    for model_id, rule, expected in cases:
        try:
            load_readonly_replay_window(model_id=model_id, strategy_rule=rule, start="2026-01-01", end="2026-05-07")
        except ReadonlyReplayWindowError as exc:
            assert exc.status == expected
        else:
            raise AssertionError(f"{model_id}/{rule} should be rejected")


def test_yz0_replay_window_service_has_no_hardcoded_valid_rules_set():
    source = (ROOT / "backend/app/services/readonly_replay_window.py").read_text(encoding="utf-8")
    assert "VALID_RULES" not in source
    assert "_validate_strategy_rule_from_registry" in source
    assert "configs/tw_modular_registry.yaml" in source
