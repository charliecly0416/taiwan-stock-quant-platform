from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "scripts/validate_tw_readonly_replay_window_artifact.py"
RUNNER_PATH = ROOT / "scripts/run_tw_modular_order_intent_replay_parity.py"


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_module("wf2a_validator", VALIDATOR_PATH)
runner = load_module("wf2a_runner", RUNNER_PATH)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def refresh_checksum(manifest_path: Path, *targets: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checksum_path = Path(manifest["checksum_manifest"])
    checksum = json.loads(checksum_path.read_text(encoding="utf-8"))
    by_path = {row["path"]: row for row in checksum["files"]}
    for target in targets:
        row = by_path[str(target)]
        row["sha256"] = sha256(target)
        row["bytes"] = target.stat().st_size
    write_json(checksum_path, checksum)


def build_fixture(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    root = tmp_path / "fixture"
    root.mkdir()
    training_manifest = root / "training_manifest.json"
    training_report = root / "training_report.md"
    model = root / "model.pkl"
    raw_score = root / "raw_score.csv"
    signal_manifest = root / "signal_manifest.json"
    full_rank_manifest = root / "full_rank_manifest.json"
    for path, content in (
        (training_manifest, "{}\n"),
        (training_report, "# training trace\n"),
        (model, "frozen-model"),
        (raw_score, "date,instrument,score\n2026-01-02,TW0001,1\n"),
        (signal_manifest, "{}\n"),
        (full_rank_manifest, "{}\n"),
    ):
        path.write_text(content, encoding="utf-8")

    registry = root / "registry.yaml"
    registry.write_text(
        yaml.safe_dump(
            {
                "production_models": {
                    "deprecated": {
                        "frozen_qlib_2018_2022": {
                            "reason": "legacy id replaced by e4_frozen_qlib_2018_2022"
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    prices = root / "prices.csv"
    write_csv(
        prices,
        [
            {
                "price_date": "2026-01-02",
                "instrument": "TW0001",
                "open": 9.0,
                "close": 9.5,
                "tradable_flag": True,
                "halt_flag": False,
                "next_day_execution_availability": True,
                "next_day_execution_status": "available",
            },
            {
                "price_date": "2026-01-05",
                "instrument": "TW0001",
                "open": 10.0,
                "close": 11.0,
                "tradable_flag": True,
                "halt_flag": False,
                "next_day_execution_availability": False,
                "next_day_execution_status": "latest_pending",
            },
        ],
    )
    price_manifest = root / "price_manifest.json"
    write_json(
        price_manifest,
        {
            "artifact_type": "price_store",
            "readonly_only": True,
            "no_provider_publish": True,
            "no_accepted_latest_switch": True,
            "prices_path": str(prices),
            "checksum": sha256(prices),
        },
    )
    order_intents = root / "order_intents.csv"
    write_csv(
        order_intents,
        [
            {
                "order_intent_row_id": "intent-1",
                "signal_date": "2026-01-02",
                "instrument": "TW0001",
                "intent_action": "buy",
                "intent_reason": "fixture_buy",
            }
        ],
    )
    order_manifest = root / "order_manifest.json"
    write_json(
        order_manifest,
        {
            "artifact_type": "order_intent",
            "generation_source": "strategy_decision_engine",
            "not_generated_from_replay_actions": True,
            "not_generated_from_replay_snapshots": True,
            "output_files": {"order_intents": str(order_intents)},
        },
    )
    summary = root / "summary.csv"
    write_csv(
        summary,
        [
            {
                "window": "fixture",
                "model_name": "e4_frozen_qlib_2018_2022",
                "model_family": "e1_frozen_qlib_baseline",
                "strategy_rule": "top50_exit_one_worst_sell",
                "start_date": "2026-01-02",
                "end_date": "2026-01-05",
                "initial_cash": 1000.0,
                "final_equity": 1000.99,
                "total_return": 0.00099,
                "max_drawdown": 0.0,
                "action_count": 1,
                "buy_count": 1,
                "sell_count": 0,
                "skipped_action_count": 0,
                "max_holding_count": 1,
                "duplicate_position_count": 0,
                "negative_cash_count": 0,
                "missing_price_count": 0,
                "diagnostic_only": False,
            }
        ],
    )
    actions = root / "actions.csv"
    write_csv(
        actions,
        [
            {
                "signal_date": "2026-01-02",
                "execution_date": "2026-01-05",
                "instrument": "TW0001",
                "action": "historical_add",
                "quantity": 1,
                "execution_price": 10.0,
                "commission": 0.01,
                "tax": 0.0,
                "cash_after": 989.99,
                "position_after": 1,
                "intent_reason": "fixture_buy",
                "reason": "fixture_buy",
                "strategy_rule": "top50_exit_one_worst_sell",
                "model_name": "e4_frozen_qlib_2018_2022",
                "order_intent_artifact": str(order_manifest),
                "order_intent_row_id": "intent-1",
            }
        ],
    )
    nav = root / "daily_nav.csv"
    write_csv(
        nav,
        [
            {
                "date": "2026-01-02",
                "cash": 1000.0,
                "market_value": 0.0,
                "equity": 1000.0,
                "daily_return": 0.0,
                "holding_count": 0,
                "missing_price_count": 0,
            },
            {
                "date": "2026-01-05",
                "cash": 989.99,
                "market_value": 11.0,
                "equity": 1000.99,
                "daily_return": 0.00099,
                "holding_count": 1,
                "missing_price_count": 0,
            },
        ],
    )
    snapshots = root / "position_snapshots.csv"
    write_csv(
        snapshots,
        [
            {
                "date": "2026-01-05",
                "instrument": "TW0001",
                "quantity": 1,
                "cost_basis": 10.01,
                "mark_price": 11.0,
                "market_value": 11.0,
                "unrealized_pnl": 0.99,
                "strategy_rule": "top50_exit_one_worst_sell",
                "model_name": "e4_frozen_qlib_2018_2022",
            }
        ],
    )
    audit_paths: dict[str, Path] = {}
    audit_columns = {
        "coverage_audit": {
            "audit_name": "coverage",
            "requested_start_date": "2026-01-02",
            "requested_end_date": "2026-01-05",
            "actual_start_date": "2026-01-02",
            "actual_end_date": "2026-01-05",
            "trading_day_count": 2,
            "signal_day_count": 2,
            "price_day_count": 2,
            "missing_signal_day_count": 0,
            "missing_price_day_count": 0,
            "status": "pass",
            "details": "fixture",
        },
        "position_integrity_audit": {
            "audit_name": "integrity",
            "date": "",
            "instrument": "",
            "status": "pass",
            "value": 1,
            "threshold": 1,
            "details": "fixture",
        },
        "forbidden_field_audit": {
            "audit_name": "forbidden",
            "artifact": "replay",
            "field_name": "",
            "field_category": "forbidden",
            "present": False,
            "used_for_ranking": False,
            "status": "pass",
            "details": "fixture",
        },
        "execution_audit": {
            "audit_name": "execution",
            "status": "pass",
            "value": "next_open",
            "threshold": "next_open",
            "details": "fixture",
        },
    }
    for key, row in audit_columns.items():
        path = root / f"{key}.csv"
        write_csv(path, [row])
        audit_paths[key] = path
    for key in (
        "decision_source_audit",
        "forbidden_scope_audit",
        "action_lineage_audit",
    ):
        path = root / f"{key}.csv"
        write_csv(path, [{"status": "pass"}])
        audit_paths[key] = path
    forbidden_action = root / "forbidden_action_audit.json"
    write_json(
        forbidden_action,
        {
            "status": "pass",
            "no_training": True,
            "no_tuning": True,
            "no_score_recompute": True,
            "no_strategy_intent_mutation": True,
            "no_default_switch": True,
            "no_provider_publish": True,
            "no_accepted_latest_switch": True,
            "no_monitor_write": True,
            "no_broker_order": True,
        },
    )
    source_audit = root / "source_identity_audit.json"
    write_json(source_audit, {"status": "pass"})
    artifacts = {
        "summary": summary,
        "daily_nav": nav,
        "actions": actions,
        "snapshots": snapshots,
        **audit_paths,
        "forbidden_action_audit": forbidden_action,
        "source_identity_audit": source_audit,
    }
    source_identity = {
        "canonical_model_id": "e4_frozen_qlib_2018_2022",
        "source_key": "frozen_qlib_2018_2022",
        "identity_adaptation": "explicit_registry_replacement_with_shared_e1_lineage",
        "canonical_training_manifest": str(training_manifest),
        "canonical_model_artifact": str(model),
        "canonical_model_sha256": sha256(model),
        "raw_oos_score": str(raw_score),
        "raw_oos_score_sha256": sha256(raw_score),
        "signal_manifest": str(signal_manifest),
        "signal_manifest_sha256": sha256(signal_manifest),
        "full_rank_manifest": str(full_rank_manifest),
        "full_rank_manifest_sha256": sha256(full_rank_manifest),
    }
    manifest_path = root / "manifest.json"
    checksum_path = root / "checksum_manifest.json"
    required_files = [
        manifest_path,
        registry,
        price_manifest,
        prices,
        order_manifest,
        order_intents,
        training_manifest,
        training_report,
        model,
        raw_score,
        signal_manifest,
        full_rank_manifest,
        *artifacts.values(),
    ]
    manifest = {
        "artifact_type": "replay_result",
        "schema_version": "readonly_replay_result_wf2a_v1",
        "run_id": "wf2a_fixture000000000000000",
        "status": "CANDIDATE_HOLD",
        "asof": "2026-01-05",
        "window_start": "2026-01-02",
        "window_end": "2026-01-05",
        "model_id": "e4_frozen_qlib_2018_2022",
        "readonly_only": True,
        "simulation_only": True,
        "not_order": True,
        "no_order_action": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor_broker_order": True,
        "no_training": True,
        "no_score_recompute": True,
        "production_trade_enabled": False,
        "product_index_admission": False,
        "generated_by": "replay_execution_engine",
        "execution_input_source": "order_intent_artifact",
        "decision_source": "order_intent_artifact",
        "not_copied_from_legacy_replay": True,
        "execution_price_mode": "next_open",
        "replay_window_policy_validation": {
            "ok": True,
            "model_training_windows_traceable": True,
            "training_overlap_rejected": True,
            "source_manifest": str(training_manifest),
            "source_training_report": str(training_report),
        },
        "order_intent_artifacts": [str(order_manifest)],
        "canonical_price_store_manifest": str(price_manifest),
        "price_store_identity": {
            "manifest_sha256": sha256(price_manifest),
            "prices_sha256": sha256(prices),
            "execution_price_field": "open",
            "mark_price_field": "close",
            "missing_execution_price_policy": "skip_without_close_fallback",
        },
        "model_source_identity": source_identity,
        "model_registry": str(registry),
        "artifacts": {key: str(path) for key, path in artifacts.items()},
        "checksum_manifest": str(checksum_path),
        "checksum_required_files": sorted(str(path) for path in required_files),
    }
    write_json(manifest_path, manifest)
    checksum = {
        "artifact_type": "readonly_replay_checksum_manifest",
        "schema_version": "readonly_replay_checksum_wf2a_v1",
        "run_id": manifest["run_id"],
        "files": [
            {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}
            for path in required_files
        ],
    }
    write_json(checksum_path, checksum)
    return manifest_path, {
        "actions": actions,
        "coverage_audit": audit_paths["coverage_audit"],
        "daily_nav": nav,
        "summary": summary,
        "snapshots": snapshots,
        "forbidden_field_audit": audit_paths["forbidden_field_audit"],
        "forbidden_action_audit": forbidden_action,
        "prices": prices,
        "price_manifest": price_manifest,
    }


def statuses(result: dict[str, Any]) -> dict[str, str]:
    return {row["name"]: row["status"] for row in result["checks"]}


def mutate_csv(path: Path, mutate: Callable[[pd.DataFrame], pd.DataFrame]) -> None:
    frame = pd.read_csv(path)
    mutate(frame).to_csv(path, index=False)


def test_static_complete_replay_fixture_passes(tmp_path: Path) -> None:
    manifest, _paths = build_fixture(tmp_path)
    result = validator.validate_artifact(manifest)
    assert result["ok"] is True


@pytest.mark.parametrize(
    ("column", "value", "failed_check"),
    [
        ("quantity", 0, "active_quantity_positive"),
        ("cash_after", 900.0, "action_cash_and_position_recomputed"),
        ("execution_price", 11.0, "next_open_execution_from_tradable_price_store"),
        ("order_intent_row_id", "missing", "order_intent_lineage"),
    ],
)
def test_validator_rejects_mutated_actions(
    tmp_path: Path, column: str, value: Any, failed_check: str
) -> None:
    manifest, paths = build_fixture(tmp_path)
    mutate_csv(paths["actions"], lambda frame: frame.assign(**{column: value}))
    refresh_checksum(manifest, paths["actions"])
    result = validator.validate_artifact(manifest)
    assert result["ok"] is False
    assert statuses(result)[failed_check] == "fail"


def test_validator_rejects_duplicate_position(tmp_path: Path) -> None:
    manifest, paths = build_fixture(tmp_path)
    mutate_csv(paths["snapshots"], lambda frame: pd.concat([frame, frame]))
    refresh_checksum(manifest, paths["snapshots"])
    result = validator.validate_artifact(manifest)
    assert result["ok"] is False
    assert statuses(result)["duplicate_position_count_zero"] == "fail"


def test_validator_rejects_self_consistent_snapshot_position_forgery(
    tmp_path: Path,
) -> None:
    manifest, paths = build_fixture(tmp_path)
    mutate_csv(
        paths["snapshots"],
        lambda frame: frame.assign(
            quantity=2,
            market_value=22.0,
            unrealized_pnl=1.98,
        ),
    )

    def forge_nav(frame: pd.DataFrame) -> pd.DataFrame:
        mask = frame["date"].astype(str) == "2026-01-05"
        frame.loc[mask, "market_value"] = 22.0
        frame.loc[mask, "equity"] = 1011.99
        frame.loc[mask, "daily_return"] = 0.01199
        return frame

    mutate_csv(paths["daily_nav"], forge_nav)
    mutate_csv(
        paths["summary"],
        lambda frame: frame.assign(final_equity=1011.99, total_return=0.01199),
    )
    refresh_checksum(
        manifest,
        paths["snapshots"],
        paths["daily_nav"],
        paths["summary"],
    )
    result = validator.validate_artifact(manifest)
    assert result["ok"] is False
    assert statuses(result)["snapshots_match_action_positions"] == "fail"


def test_validator_rejects_forbidden_output_field(tmp_path: Path) -> None:
    manifest, paths = build_fixture(tmp_path)
    mutate_csv(
        paths["actions"], lambda frame: frame.assign(broker_order_id="forbidden")
    )
    refresh_checksum(manifest, paths["actions"])
    result = validator.validate_artifact(manifest)
    assert result["ok"] is False
    assert statuses(result)["forbidden_output_fields_absent"] == "fail"


def test_validator_rejects_failed_audit_and_training_trace(tmp_path: Path) -> None:
    manifest, paths = build_fixture(tmp_path)
    mutate_csv(
        paths["forbidden_field_audit"], lambda frame: frame.assign(status="fail")
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["replay_window_policy_validation"]["model_training_windows_traceable"] = (
        False
    )
    write_json(manifest, payload)
    refresh_checksum(manifest, paths["forbidden_field_audit"], manifest)
    result = validator.validate_artifact(manifest)
    assert result["ok"] is False
    assert statuses(result)["required_audits_pass"] == "fail"
    assert statuses(result)["training_trace"] == "fail"


def test_validator_rejects_unchecksummed_mutation(tmp_path: Path) -> None:
    manifest, paths = build_fixture(tmp_path)
    paths["actions"].write_text("corrupt\n", encoding="utf-8")
    result = validator.validate_artifact(manifest)
    assert result["ok"] is False
    assert statuses(result)["checksum_all_required_files"] == "fail"


def test_validator_rejects_forged_coverage_with_valid_checksum(tmp_path: Path) -> None:
    manifest, paths = build_fixture(tmp_path)
    mutate_csv(
        paths["coverage_audit"],
        lambda frame: frame.assign(trading_day_count=99, actual_end_date="2026-01-04"),
    )
    refresh_checksum(manifest, paths["coverage_audit"])
    result = validator.validate_artifact(manifest)
    assert result["ok"] is False
    assert statuses(result)["coverage_recomputed"] == "fail"


def test_validator_rejects_missing_required_column_with_valid_checksum(
    tmp_path: Path,
) -> None:
    manifest, paths = build_fixture(tmp_path)
    mutate_csv(paths["daily_nav"], lambda frame: frame.drop(columns=["daily_return"]))
    refresh_checksum(manifest, paths["daily_nav"])
    result = validator.validate_artifact(manifest)
    assert result["ok"] is False
    assert statuses(result)["required_columns"] == "fail"


def test_validator_rejects_same_day_execution_with_valid_checksum(
    tmp_path: Path,
) -> None:
    manifest, paths = build_fixture(tmp_path)
    mutate_csv(
        paths["actions"],
        lambda frame: frame.assign(execution_date="2026-01-02"),
    )
    refresh_checksum(manifest, paths["actions"])
    result = validator.validate_artifact(manifest)
    assert result["ok"] is False
    assert statuses(result)["execution_after_signal"] == "fail"


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("tradable_flag", False, "next_day_not_tradable"),
        ("halt_flag", True, "next_day_halted"),
        ("open", None, "missing_next_open"),
    ],
)
def test_canonical_price_store_never_falls_back_to_close(
    tmp_path: Path, field: str, value: Any, reason: str
) -> None:
    _manifest, paths = build_fixture(tmp_path)
    prices = pd.read_csv(paths["prices"])
    prices.loc[prices["price_date"] == "2026-01-05", field] = value
    prices.to_csv(paths["prices"], index=False)
    price_manifest = json.loads(paths["price_manifest"].read_text(encoding="utf-8"))
    price_manifest["checksum"] = sha256(paths["prices"])
    write_json(paths["price_manifest"], price_manifest)

    store = runner.CanonicalPriceStore(
        paths["price_manifest"], {"TW0001"}, execution_price_mode="next_open"
    )
    assert store.next_after("TW0001", "2026-01-02") is None
    assert store.execution_skip_reason("TW0001", "2026-01-02") == reason


def test_replay_policy_training_reports_exist_for_both_models() -> None:
    policy = yaml.safe_load((ROOT / "configs/tw_replay_window_policy.yaml").read_text())
    for model_id in (
        "e4_frozen_qlib_2018_2022",
        "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025",
    ):
        model = policy["models"][model_id]
        assert (ROOT / model["source_manifest"]).is_file()
        assert (ROOT / model["source_training_report"]).is_file()
