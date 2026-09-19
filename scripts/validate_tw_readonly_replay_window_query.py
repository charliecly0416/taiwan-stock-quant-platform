#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.services import readonly_replay_window_index as replay_index  # noqa: E402
from app.services.readonly_replay_window import ReadonlyReplayWindowError, load_readonly_replay_window  # noqa: E402

MODEL_A = "e4_frozen_qlib_2018_2022"
MODEL_B = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
LEGACY_MODEL = "e4_frozen_qlib_2023_2025_ltr"
STRATEGY = "top50_exit_one_worst_sell"


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def expect_error(name: str, expected: set[str], **kwargs: str) -> dict[str, Any]:
    try:
        load_readonly_replay_window(**kwargs)
    except ReadonlyReplayWindowError as exc:
        return check(name, exc.status in expected, exc.status)
    return check(name, False, "accepted unexpectedly")


def validate() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    try:
        payload = load_readonly_replay_window(
            model_id=MODEL_A,
            strategy_rule=STRATEGY,
            start="2026-01-01",
            end="2026-05-07",
        )
        checks.extend([
            check("valid_standard_window_ok", payload.get("ok") is True),
            check("readonly_only", payload.get("readonly_only") is True and payload.get("production_trade_enabled") is False),
            check("backend_window_validator_exists", (payload.get("validation") or {}).get("backend_window_validator_exists") is True),
            check("model_training_windows_traceable", (payload.get("validation") or {}).get("model_training_windows_traceable") is True),
            check("replay_result_source_order_intent", payload.get("generated_by") == "replay_execution_engine" and payload.get("decision_source") == "order_intent_artifact" and payload.get("execution_input_source") == "order_intent_artifact"),
            check("checksum_ok", (payload.get("checksum") or {}).get("ok") is True),
            check("no_on_demand_generation", (payload.get("no_write_guarantees") or {}).get("does_not_generate_replay_on_demand") is True),
            check("fixed_standard_window_reads_indexed_artifact", (payload.get("window_index") or {}).get("window_type") in {"fixed_standard", "generated_readonly"} and (payload.get("no_write_guarantees") or {}).get("does_not_generate_replay_on_demand") is True),
            check("query_response_window_index_matches_index_entry", (payload.get("sources") or {}).get("window_index_manifest") == (replay_index.load_readonly_replay_window_index().get("sources") or {}).get("manifest")),
        ])
    except ReadonlyReplayWindowError as exc:
        checks.append(check("valid_standard_window_ok", False, exc.status))
    checks.append(expect_error(
        "illegal_training_window_rejected_by_backend",
        {"requested_window_before_allowed_replay_start", "requested_window_overlaps_ltr_training_window", "requested_window_overlaps_qlib_training_window"},
        model_id=MODEL_A,
        strategy_rule=STRATEGY,
        start="2025-01-01",
        end="2025-12-31",
    ))
    checks.append(expect_error(
        "future_beyond_signal_rejected_by_backend",
        {"requested_window_beyond_latest_signal"},
        model_id=MODEL_A,
        strategy_rule=STRATEGY,
        start="2026-01-01",
        end="2026-06-01",
    ))
    checks.append(expect_error(
        "diagnostic_rule_not_valid_strategy_evidence",
        {"diagnostic_rule_not_valid_strategy_evidence", "research_only_strategy_not_valid_strategy_evidence"},
        model_id=MODEL_A,
        strategy_rule="one_sell_one_buy_buggy_e8r",
        start="2026-01-01",
        end="2026-05-07",
    ))

    original_latest = replay_index.LATEST_PATH
    try:
        replay_index.LATEST_PATH = ROOT / "data_tw/artifacts/readonly_replay_windows/d7/__missing_latest_for_validator__.json"
        try:
            load_readonly_replay_window(
                model_id=MODEL_A,
                strategy_rule=STRATEGY,
                start="2026-01-01",
                end="2026-05-07",
            )
            checks.append(check("fixed_standard_window_fails_when_d7_latest_missing", False, "accepted unexpectedly"))
        except ReadonlyReplayWindowError as exc:
            checks.append(check("fixed_standard_window_fails_when_d7_latest_missing", exc.status == "missing_artifact", exc.status))
    finally:
        replay_index.LATEST_PATH = original_latest

    try:
        generated = load_readonly_replay_window(
            model_id=MODEL_A,
            strategy_rule=STRATEGY,
            start="2026-01-01",
            end="2026-05-07",
        )
        checks.append(check("generated_non_fixed_window_readable", generated.get("schema_version") == "readonly_replay_window_api_d7r_v1" and (generated.get("checksum") or {}).get("ok") is True))
        checks.append(check("generated_window_reads_indexed_artifact", (generated.get("window_index") or {}).get("window_type") == "generated_readonly" and (generated.get("sources") or {}).get("window_index_manifest") == (replay_index.load_readonly_replay_window_index().get("sources") or {}).get("manifest")))
        checks.append(check("generated_non_fixed_window_not_on_demand", (generated.get("no_write_guarantees") or {}).get("reads_indexed_audited_artifact_only") is True and (generated.get("no_write_guarantees") or {}).get("does_not_generate_replay_on_demand") is True))
    except ReadonlyReplayWindowError as exc:
        checks.append(check("generated_non_fixed_window_readable", False, exc.status))
    checks.append(expect_error(
        "model_b_shadow_request_rejected",
        {"deprecated_model_id"},
        model_id=MODEL_B,
        strategy_rule=STRATEGY,
        start="2026-01-01",
        end="2026-05-07",
    ))
    checks.append(expect_error(
        "legacy_model_request_rejected",
        {"deprecated_model_id"},
        model_id=LEGACY_MODEL,
        strategy_rule=STRATEGY,
        start="2026-01-01",
        end="2026-05-07",
    ))
    return {"ok": all(row["status"] == "pass" for row in checks), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate D5 readonly replay window query gates.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
