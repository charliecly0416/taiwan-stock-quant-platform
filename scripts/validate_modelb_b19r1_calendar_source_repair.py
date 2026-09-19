#!/usr/bin/env python3
"""Independently recompute B19R1 mechanical checks and protected triples."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r1_calendar_source_repair_20260916"
B19 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19_reconstructed_pit_holdout_feasibility_20260916"
REVIEW = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19_preflight_independent_review_20260916/B19_PREFLIGHT_FINAL_INDEPENDENT_REVIEW.json"
OUT = RUN / "B19R1_POSTCHECK.json"
PROTECTED = (
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
)


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_protected(value: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        key: {"exists": item["exists"], "sha256": item["sha256"]}
        for key, item in value.items()
    }


def main() -> int:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite postcheck: {OUT}")
    manifest = load(RUN / "B19R1_MANIFEST.json")
    validator = load(RUN / "B19R1_VALIDATOR.json")
    review = load(REVIEW)
    calendar = list(csv.DictReader((RUN / "FROZEN_ACTUAL_MARKET_CALENDAR.csv").open(encoding="utf-8")))
    maturity = list(csv.DictReader((RUN / "MATURITY_AUDIT.csv").open(encoding="utf-8")))
    source = list(csv.DictReader((RUN / "SOURCE_CAPACITY_AUDIT.csv").open(encoding="utf-8")))
    dates = [row["date"] for row in calendar]
    mature = [row for row in maturity if row["maturity_class"] == "MATURE"]
    tail = [row for row in maturity if row["maturity_class"] == "IMMATURE_TAIL"]
    mature_sources = [row for row in source if row["maturity_class"] == "MATURE"]
    july_13 = next(row for row in source if row["signal_date"] == "2026-07-13")
    september_15 = next(row for row in source if row["signal_date"] == "2026-09-15")

    b19_protected_before = normalize_protected(load(B19 / "protected_before.json"))
    b19_protected_after = normalize_protected(load(B19 / "protected_after.json"))
    b19r1_before = normalize_protected(load(RUN / "protected_before.json"))
    b19r1_after = normalize_protected(load(RUN / "protected_after.json"))
    current = {
        str(path.relative_to(ROOT)): {"exists": path.is_file(), "sha256": sha256(path)}
        for path in PROTECTED
    }
    bound = review["bound_artifacts"]
    bound_paths = {
        "manifest_sha256": B19 / "B19_MANIFEST.json",
        "validator_sha256": B19 / "B19_VALIDATOR.json",
        "daily_feasibility_sha256": B19 / "B19_DAILY_FEASIBILITY.csv",
        "executor_errata_sha256": B19 / "B19_EXECUTOR_ERRATA.json",
        "executor_errata_cn_sha256": B19 / "B19_EXECUTOR_ERRATA_CN.md",
    }

    checks = {
        "executor_validator_all_checks_true": all(validator["checks"].values()),
        "executor_validator_pass_repair_only": validator["verdict"] == "PASS_REPAIR_ONLY",
        "calendar_hash_matches_manifest": sha256(RUN / "FROZEN_ACTUAL_MARKET_CALENDAR.csv") == manifest["calendar"]["sha256"],
        "calendar_90_unique_strict_dates": len(dates) == 90 and dates == sorted(set(dates)),
        "calendar_bounds_and_placeholder": dates[0] == "2026-05-11" and dates[-1] == "2026-09-15" and "2026-07-10" not in dates,
        "maturity_80_and_tail_10": len(mature) == 80 and len(tail) == 10,
        "maturity_bounds": mature[0]["signal_date"] == "2026-05-11" and mature[-1]["signal_date"] == "2026-09-01",
        "july_13_t_minus_1_and_sources_closed": july_13["orthogonal_trade_date"] == "2026-07-09" and july_13["source_capacity_closed"] == "True",
        "all_80_mature_capacity_closed": len(mature_sources) == 80 and all(int(row["eligible_capacity_after_exclusions"]) >= 50 and row["source_capacity_closed"] == "True" for row in mature_sources),
        "september_15_tail_only": september_15["maturity_class"] == "IMMATURE_TAIL" and september_15["twii_same_day_present"] == "False",
        "b19_bound_hashes_still_match_final_review": all(sha256(path) == bound[key] for key, path in bound_paths.items()),
        "protected_b19_before_after_b19r1_before_after_current_equal": b19_protected_before == b19_protected_after == b19r1_before == b19r1_after == current,
        "forbidden_operations_all_false": not any([
            manifest["model_a_predict_called"], manifest["model_b_predict_called"], manifest["training_performed"],
            manifest["tuning_performed"], manifest["replay_performed"], manifest["label_read"],
            manifest["outcome_or_return_value_read"], manifest["production_write_performed"],
        ]),
    }
    payload = {
        "schema_version": "modelb.b19r1.calendar_source_repair.postcheck.v1",
        "checks": checks,
        "verdict": "PASS_REPAIR_ONLY" if all(checks.values()) else "FAIL",
        "training_go_no_go": "NO_GO_TRAINING",
        "protected_triple": {
            "b19_before": b19_protected_before,
            "b19_after": b19_protected_after,
            "b19r1_before": b19r1_before,
            "b19r1_after": b19r1_after,
            "current": current,
        },
        "recomputed": {
            "actual_market_days": len(dates),
            "mature_days": len(mature),
            "immature_tail_days": len(tail),
            "mature_min_eligible_capacity": min(int(row["eligible_capacity_after_exclusions"]) for row in mature_sources),
            "july_13_t_minus_1": july_13["orthogonal_trade_date"],
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": payload["verdict"], **payload["recomputed"]}, ensure_ascii=False))
    return 0 if payload["verdict"] == "PASS_REPAIR_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
