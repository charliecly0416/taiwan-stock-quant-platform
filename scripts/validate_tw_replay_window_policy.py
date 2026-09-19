#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "configs/tw_replay_window_policy.yaml"
MODEL_A = "e4_frozen_qlib_2018_2022"
MODEL_B = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
REQUIRED_MODELS = {MODEL_A, MODEL_B}
EXPECTED_POLICY_VERSION = "replay_window_policy_yz0_clean_v1"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    return date.fromisoformat(str(value))


def overlaps(
    start: date, end: date, other_start: date | None, other_end: date | None
) -> bool:
    if other_start is None or other_end is None:
        return False
    return start <= other_end and other_start <= end


def validate_policy(policy_path: Path) -> dict[str, Any]:
    policy = load_yaml(policy_path)
    checks: list[dict[str, Any]] = []
    fixed = policy.get("fixed_window") or {}
    fixed_start = parse_date(fixed.get("start"))
    fixed_end = parse_date(fixed.get("end"))
    latest = parse_date(policy.get("latest_available_signal_date"))
    allowed_min = parse_date(policy.get("allowed_replay_start_min"))
    models = policy.get("models") or {}
    policy_version = str(policy.get("policy_version") or "")
    checks.append(
        check(
            "policy_version", policy_version == EXPECTED_POLICY_VERSION, policy_version
        )
    )
    checks.append(check("fixed_window_only", policy.get("fixed_window_only") is True))
    checks.append(
        check(
            "user_selectable_range_disabled",
            policy.get("user_selectable_range_enabled") is False,
        )
    )
    checks.append(
        check(
            "available_window_metadata_only",
            policy.get("available_window_metadata_only") is True,
        )
    )
    checks.append(
        check(
            "fixed_window_2026_ytd",
            fixed.get("name") == "2026_ytd"
            and fixed.get("start") == "2026-01-01"
            and fixed.get("end") == "2026-05-07",
            str(fixed),
        )
    )
    checks.append(
        check(
            "latest_available_signal_date_bounds_fixed_window",
            fixed_end is not None and latest is not None and fixed_end <= latest,
            f"fixed_end={fixed.get('end')} latest={policy.get('latest_available_signal_date')}",
        )
    )
    checks.append(
        check(
            "allowed_replay_start_min_bounds_fixed_window",
            fixed_start is not None
            and allowed_min is not None
            and fixed_start >= allowed_min,
            f"fixed_start={fixed.get('start')} allowed_min={policy.get('allowed_replay_start_min')}",
        )
    )
    checks.append(
        check(
            "disallow_training_overlap", policy.get("disallow_training_overlap") is True
        )
    )
    checks.append(
        check(
            "disallow_future_beyond_signal",
            policy.get("disallow_future_beyond_signal") is True,
        )
    )
    checks.append(
        check(
            "required_models_present",
            REQUIRED_MODELS.issubset(set(models)),
            sorted(models).__repr__(),
        )
    )
    model_a = models.get(MODEL_A) or {}
    model_b = models.get(MODEL_B) or {}
    checks.append(
        check(
            "canonical_default_model",
            str(policy.get("default_model_id")) == MODEL_A,
            str(policy.get("default_model_id")),
        )
    )
    checks.append(
        check(
            "model_a_production_selectable",
            model_a.get("production_selectable") is True,
        )
    )
    checks.append(
        check(
            "model_b_research_shadow_only",
            model_b.get("production_selectable") is False
            and model_b.get("frontend_selectable") is False
            and model_b.get("production_default") is False
            and model_b.get("research_only") is True
            and model_b.get("diagnostic_only") is True
            and model_b.get("eligible_for_baseline") is False,
        )
    )
    checks.append(
        check(
            "production_model_set_is_model_a_only",
            {
                key
                for key, value in models.items()
                if (value or {}).get("production_selectable") is True
            }
            == {MODEL_A},
        )
    )
    model_traceable = True
    model_window_ok = True
    overlap_bad: list[str] = []
    for model_id, meta in models.items():
        source_manifest = str(meta.get("source_manifest") or "")
        source_training_report = str(meta.get("source_training_report") or "")
        if (
            not source_manifest
            or not source_training_report
            or not resolve(source_manifest).is_file()
            or not resolve(source_training_report).is_file()
        ):
            model_traceable = False
        model_allowed_min = parse_date(meta.get("allowed_replay_start_min"))
        q_start = parse_date(meta.get("qlib_train_start"))
        q_end = parse_date(meta.get("qlib_train_end"))
        l_start = parse_date(meta.get("ltr_train_start"))
        l_end = parse_date(meta.get("ltr_train_end"))
        if (
            fixed_start is None
            or fixed_end is None
            or model_allowed_min is None
            or fixed_start < model_allowed_min
        ):
            model_window_ok = False
        if fixed_start is not None and fixed_end is not None:
            if overlaps(fixed_start, fixed_end, q_start, q_end) or overlaps(
                fixed_start, fixed_end, l_start, l_end
            ):
                overlap_bad.append(str(model_id))
    checks.append(check("model_training_windows_traceable", model_traceable))
    checks.append(check("fixed_window_respects_model_allowed_min", model_window_ok))
    checks.append(
        check(
            "fixed_window_does_not_overlap_training_windows",
            not overlap_bad,
            "|".join(overlap_bad),
        )
    )
    diagnostic = (policy.get("diagnostic_rules") or {}).get(
        "one_sell_one_buy_buggy_e8r"
    ) or {}
    checks.append(
        check(
            "diagnostic_rule_not_valid_strategy_evidence",
            diagnostic.get("diagnostic_only") is True
            and diagnostic.get("not_valid_strategy_evidence") is True,
        )
    )
    allowed_windows = policy.get("allowed_windows") or []
    checks.append(
        check(
            "allowed_windows_fixed_only",
            len(allowed_windows) == 1 and allowed_windows[0].get("name") == "2026_ytd",
        )
    )
    return {
        "ok": all(row["status"] == "pass" for row in checks),
        "policy": rel(policy_path),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate D4 ReplayWindowPolicy metadata."
    )
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate_policy(resolve(args.policy))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
