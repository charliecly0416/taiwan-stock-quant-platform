from __future__ import annotations

import json
from pathlib import Path

from scripts.run_daily_tw_stock_auto_update import parse_json_stdout, publish_latest_gate_status


def test_parse_json_stdout_accepts_qlib_logs_before_json(tmp_path: Path) -> None:
    stdout = tmp_path / "stdout.txt"
    stdout.write_text(
        "ModuleNotFoundError: optional dependency\n"
        + json.dumps(
            {
                "pipeline_status": "SCORED_ASOF_TARGET",
                "artifacts": {"model_signal": "fixture"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = parse_json_stdout({"stdout_path": str(stdout)})

    assert payload["pipeline_status"] == "SCORED_ASOF_TARGET"
    assert payload["artifacts"]["model_signal"] == "fixture"


def test_parse_json_stdout_rejects_output_without_complete_json(tmp_path: Path) -> None:
    stdout = tmp_path / "stdout.txt"
    stdout.write_text("INFO {\"pipeline_status\":", encoding="utf-8")

    assert parse_json_stdout({"stdout_path": str(stdout)}) == {}


def test_parse_json_stdout_rejects_top_level_json_array(tmp_path: Path) -> None:
    stdout = tmp_path / "stdout.txt"
    stdout.write_text('[{"pipeline_status": "SCORED_ASOF_TARGET"}]', encoding="utf-8")

    assert parse_json_stdout({"stdout_path": str(stdout)}) == {}


def test_publish_latest_gate_status_observes_completed_dapr18_product_chain() -> None:
    job = {
        "dapr18_controlled_latest_orchestration": {
            "status": "auto_publish_chain_completed",
            "product_latest_state_after": {
                "target_asof": "2026-09-22",
                "all_product_latest_match_target": True,
            },
        }
    }

    assert publish_latest_gate_status(job) == "READONLY_LATEST_UPDATED_BY_EXPLICIT_GATE"


def test_publish_latest_gate_status_does_not_infer_publish_from_partial_dapr18_evidence() -> None:
    job = {
        "dapr18_controlled_latest_orchestration": {
            "status": "auto_publish_chain_completed",
            "product_latest_state_after": {
                "target_asof": "2026-09-22",
                "all_product_latest_match_target": False,
            },
        }
    }

    assert publish_latest_gate_status(job) == "DISABLED_BY_DEFAULT"
