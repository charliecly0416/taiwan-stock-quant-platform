from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_tw_modular_readonly_snapshot import validate_snapshot


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_snapshot_tree(tmp_path: Path, *, source_manifest: Path) -> Path:
    snapshot_dir = tmp_path / "readonly" / "2026-08-12"
    manifest = {
        "artifact_type": "readonly_strategy_snapshot",
        "schema_version": "readonly_strategy_snapshot_r13_v1",
        "readonly_only": True,
        "production_trade_enabled": False,
        "no_order_action": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "is_production_trading_default": False,
        "display_role": "primary_readonly_candidate",
        "model_id": "e4_frozen_qlib_2018_2022",
        "strategy_rule": "candidate_only_no_strategy_replay",
        "ranking_source": "qlib_rank_controlled_signal",
        "candidate_boundary": "qlib_top50",
        "source_signal_manifest": str(source_manifest),
        "snapshot": "strategy_snapshot.json",
        "forbidden_scope_audit": "forbidden_scope_audit.json",
        "checksum_manifest": "checksum_manifest.json",
    }
    snapshot = {
        "readonly_only": True,
        "no_order_action": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "is_production_trading_default": False,
        "display_role": "primary_readonly_candidate",
        "model_id": "e4_frozen_qlib_2018_2022",
        "strategy_rule": "candidate_only_no_strategy_replay",
        "ranking_source": "qlib_rank_controlled_signal",
        "candidate_boundary": "qlib_top50",
    }
    forbidden_scope = {
        "status": "pass",
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor_broker_order": True,
    }
    write_json(snapshot_dir / "manifest.json", manifest)
    write_json(snapshot_dir / "strategy_snapshot.json", snapshot)
    write_json(snapshot_dir / "forbidden_scope_audit.json", forbidden_scope)
    write_json(
        snapshot_dir / "checksum_manifest.json",
        {
            "validation": {"ok": True},
            "files": [
                {"path": "manifest.json", "sha256": sha256_file(snapshot_dir / "manifest.json")},
                {"path": "strategy_snapshot.json", "sha256": sha256_file(snapshot_dir / "strategy_snapshot.json")},
                {
                    "path": "forbidden_scope_audit.json",
                    "sha256": sha256_file(snapshot_dir / "forbidden_scope_audit.json"),
                },
            ],
        },
    )
    return snapshot_dir / "manifest.json"


def sha256_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_model_signal_manifest(path: Path, *, forbidden_actions: dict | None = None) -> None:
    write_json(
        path,
        {
            "artifact_type": "ModelSignalArtifact",
            "model_id": "e4_frozen_qlib_2018_2022",
            "status": "READY",
            "run_id": "dng9_daily_auto_modela_20260812_20260812T103001Z",
            "row_count": 150,
            "production_allowed": False,
            "not_published_latest": True,
            "no_latest": True,
            "forbidden_actions": forbidden_actions
            if forbidden_actions is not None
            else {
                "provider_publish_triggered": False,
                "qlib_accepted_latest_switched": False,
                "broker_order_quick_trade_triggered": False,
                "target_position_or_weight_generated": False,
            },
        },
    )


def test_validator_accepts_rolling_controlled_model_signal_manifest(tmp_path: Path) -> None:
    source = tmp_path / "signals" / "e4_frozen_qlib_2018_2022" / "daily_run" / "manifest.json"
    write_model_signal_manifest(source)
    manifest = write_snapshot_tree(tmp_path, source_manifest=source)

    result = validate_snapshot(manifest)

    assert result["ok"] is True


def test_validator_rejects_rolling_model_signal_without_forbidden_action_audit(tmp_path: Path) -> None:
    source = tmp_path / "signals" / "e4_frozen_qlib_2018_2022" / "daily_run" / "manifest.json"
    write_model_signal_manifest(source, forbidden_actions={})
    manifest = write_snapshot_tree(tmp_path, source_manifest=source)

    result = validate_snapshot(manifest)
    failed = {row["name"] for row in result["checks"] if row["status"] == "fail"}

    assert result["ok"] is False
    assert {"known_readonly_contract", "source_signal_manifest"} <= failed
