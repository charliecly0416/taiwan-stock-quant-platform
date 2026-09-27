#!/usr/bin/env python3
"""Validate B19R2/R2R pretraining materialization without reading outcomes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
R2R = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916"
SCORER = ROOT / "scripts/modelb_b19r2r_label_free_modela.py"
BUILDER = ROOT / "scripts/build_modelb_b19r2_pretraining_materialization.py"
FEATURE_SCHEMA = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json"
B2_RAW = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_ARTIFACT_RAW.parquet"
B2_CALENDAR = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b01_feature_input_contract_repair_20260913/CANONICAL_CALENDAR_THROUGH_TARGET.csv"
B19_CALENDAR = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r1_calendar_source_repair_20260916/FROZEN_ACTUAL_MARKET_CALENDAR.csv"
AMENDMENT_03 = R2R / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_03.json"
AMENDMENT_04 = R2R / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_04.json"
AMENDMENT_05 = R2R / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_05.json"
ATTEMPT_FAILURE_01 = R2R / "B19R2R_MATERIALIZATION_ATTEMPT_FAILURE_01.json"
ATTEMPT_FAILURE_01_ERRATA = R2R / "B19R2R_MATERIALIZATION_ATTEMPT_FAILURE_01_ERRATA.json"
ROLLOVER_OBSERVATION_01 = R2R / "B19R2R_EXTERNAL_DAILY_ROLLOVER_OBSERVATION_01.json"
EFFECTIVE_SPLIT = R2R / "NESTED_WALK_FORWARD_SPLIT_AMENDMENT_03.csv"
SOURCE_PROVIDER = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
ISOLATED_PROVIDER = R2R / "isolated_model_a_provider_no_nontrading_placeholders"
FORMAL_EFFECTIVE_START = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b1_same_run_handoff_20260913/FORMAL_UNIVERSE_EFFECTIVE_START_AUDIT.csv"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def provider_entries(provider: Path) -> list[dict[str, Any]]:
    entries = []
    feature_root = provider / "features"
    for path in sorted(feature_root.glob("*/*.day.bin")):
        raw = path.read_bytes()
        entries.append({
            "path": path.relative_to(provider).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        })
    return entries


def provider_tree_hash(entries: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for entry in sorted(entries, key=lambda item: item["path"]):
        digest.update(f'{entry["path"]}\0{entry["sha256"]}\0{entry["bytes"]}\n'.encode("ascii"))
    return digest.hexdigest()


def isolated_provider_checks(binding: dict[str, Any]) -> dict[str, bool]:
    manifest_path = ISOLATED_PROVIDER / "B19R2R_ISOLATED_PROVIDER_MANIFEST.json"
    if not manifest_path.is_file():
        return {"isolated_provider_manifest_exists": False}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    calendar_path = ISOLATED_PROVIDER / "calendars/day.txt"
    calendar = [line for line in calendar_path.read_text(encoding="utf-8").splitlines() if line]
    entries = provider_entries(ISOLATED_PROVIDER)
    actual = {entry["path"]: entry for entry in entries}
    mapping = {entry["path"]: entry for entry in manifest.get("file_mapping", [])}
    instruments = sorted(
        line.split("\t", 1)[0].strip().upper()
        for line in (ISOLATED_PROVIDER / "instruments/all.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    fields = ["open", "high", "low", "close", "volume", "vwap", "factor"]
    expected_paths = {f"features/{symbol.lower()}/{field}.day.bin" for symbol in instruments for field in fields}
    binary_alignment = True
    for path_key, entry in actual.items():
        values = np.frombuffer((ISOLATED_PROVIDER / path_key).read_bytes(), dtype="<f4")
        start = int(values[0]) if len(values) else -1
        binary_alignment = binary_alignment and len(values) >= 2 and 0 <= start < len(calendar) and start + len(values) - 1 <= len(calendar)
        mapped = mapping.get(path_key, {})
        binary_alignment = binary_alignment and mapped.get("clean_sha256") == entry["sha256"] and mapped.get("clean_bytes") == entry["bytes"]
    sample = np.fromfile(ISOLATED_PROVIDER / "features/tw2330/close.day.bin", dtype="<f4")
    sample_start = int(sample[0])
    sample_index = calendar.index("2026-09-01") - sample_start + 1
    return {
        "isolated_provider_manifest_exists": True,
        "isolated_provider_1050_exact_paths": len(entries) == len(mapping) == len(expected_paths) == 1050 and set(actual) == set(mapping) == expected_paths,
        "isolated_provider_tree_matches_amendment04": provider_tree_hash(entries) == binding.get("expected_clean_feature_tree_sha256") == manifest.get("clean_feature_tree_sha256"),
        "isolated_provider_calendar_matches_amendment04": len(calendar) == binding.get("expected_clean_calendar_rows") == 2846 and sha(calendar_path) == binding.get("expected_clean_calendar_sha256") == manifest.get("clean_calendar_sha256") and "2026-07-10" not in calendar,
        "isolated_provider_per_file_mapping_and_index_alignment": bool(binary_alignment),
        "isolated_provider_instruments_150": len(instruments) == len(set(instruments)) == 150,
        "isolated_provider_frozen_value_sample": 0 < sample_index < len(sample) and float(sample[sample_index]) == 2440.0,
        "isolated_provider_removed_only_placeholder": manifest.get("removed_provider_only_dates") == ["2026-07-10"],
    }


def b2_price_overlap_parity() -> bool:
    from build_modelb_b19r2_pretraining_materialization import price_grid

    columns = [
        "MA5", "MA10", "MA20", "MA60", "RSI14", "MACD", "Bollinger_position", "ret20",
        "volatility20", "volume_ratio20", "avg_trading_value_20d", "volume_stability20",
        "missing_rate20", "suspension_proxy", "slippage_proxy",
    ]
    decoded, _ = price_grid(ISOLATED_PROVIDER, "2026-05-07")
    canonical = pd.read_parquet(B2_RAW, columns=["date", "instrument", *columns])
    canonical["date"] = pd.to_datetime(canonical.date).dt.strftime("%Y-%m-%d")
    canonical = canonical[canonical.date.le("2026-05-07")]
    joined = decoded[["date", "instrument", *columns]].merge(
        canonical, on=["date", "instrument"], suffixes=("_decoded", "_b2"), validate="one_to_one"
    )
    if len(joined) != len(canonical) or joined.date.min() != "2023-01-03" or joined.date.max() != "2026-05-07":
        return False
    for column in columns:
        actual = joined[f"{column}_decoded"].to_numpy(dtype=float)
        expected = joined[f"{column}_b2"].to_numpy(dtype=float)
        if not np.array_equal(np.isfinite(actual), np.isfinite(expected)):
            return False
        finite = np.isfinite(actual)
        if not np.allclose(actual[finite], expected[finite], rtol=1e-5, atol=1e-3):
            return False
    tw7769 = joined[(joined.instrument == "TW7769") & (joined.date == "2026-03-04")]
    return len(tw7769) == 1 and float(tw7769.MACD_decoded.iloc[0]) == float(tw7769.MACD_b2.iloc[0])


def validate(run: Path) -> dict[str, Any]:
    freeze = run / "B19R2R_PREOUTCOME_FREEZE.json"
    source = SCORER.read_text(encoding="utf-8")
    builder_source = BUILDER.read_text(encoding="utf-8")
    payload: dict[str, Any] = {"schema_version": "modelb.b19r2r.pretraining_materialization.validator.v1", "checks": {}}
    checks = payload["checks"]
    checks["freeze_exists"] = freeze.is_file()
    checks["freeze_closed_before_outcome"] = False
    checks["scorer_has_only_feature_group"] = '"config": {"feature": (feature_fields, feature_names)}' in source and '"label"' not in source
    checks["scorer_learn_processors_empty"] = "learn_processors=[]" in source
    checks["scorer_infer_processors_empty"] = "infer_processors=[]" in source
    checks["scorer_no_dropna_label"] = "DropnaLabel" not in source
    checks["scorer_no_label_expression"] = "Ref($close" not in source and "get_label_config" not in source
    checks["scorer_static_alpha158dl_only"] = (
        "from qlib.contrib.data.loader import Alpha158DL" in source
        and "Alpha158DL.get_feature_config()" in source
        and "Alpha158(" not in source
        and "len(feature_fields) != 158 or len(feature_names) != 158" in source
        and "05943b7d14e82ab604fe76938465589014c6e89b51f09116a2805c59080678a3" in source
        and "d5f52c2d75ea900ab29f4742eeb59d9692254ba7307ad36a807012db7d680e13" in source
    )
    checks["rsi_exact_b2_ready_semantics"] = (
        "ready = delta.rolling(14, min_periods=14).count().eq(14) & close.notna()" in builder_source
        and "value = value.mask(ready & loss.eq(0), 50.0).where(ready)" in builder_source
        and 'if not bool(base.iloc[index]["_rsi_ready"]) and "RSI14" not in missing' in builder_source
    )
    checks["price_and_universe_use_isolated_provider_only"] = (
        "def decode_provider_field(provider_root: Path" in builder_source
        and "def price_grid(provider_root: Path" in builder_source
        and "provider_symbols(isolated_provider)" in builder_source
        and "option_c_150_normalized" not in builder_source
    )
    checks["actual_calendar_and_effective_start_filter_before_stock_rolling"] = (
        "raw = raw[raw.date.isin(actual_dates) & raw.date.ge(effective_start[symbol])]" in builder_source
        and builder_source.index("raw = raw[raw.date.isin(actual_dates) & raw.date.ge(effective_start[symbol])]") < builder_source.index('raw[f"MA{window}"]')
    )
    checks["actual_calendar_filter_before_twii_rolling"] = "twii = twii[twii.date.isin(actual_dates)]" in builder_source
    checks["isolated_provider_built_before_model_a"] = "build_isolated_model_a_provider(run_dir)" in builder_source
    checks["builder_split_plan_reads_only_amendment03_csv"] = (
        "return pd.read_csv(EFFECTIVE_SPLIT, dtype=str).fillna(\"\").to_dict(orient=\"records\")" in builder_source
        and "2026-02-13" not in builder_source
        and "2026-03-09\",\n            \"validation_end\"" not in builder_source
    )
    checks["feature_schema_78"] = json.loads(FEATURE_SCHEMA.read_text(encoding="utf-8")).get("feature_count", 78) == 78 and len(json.loads(FEATURE_SCHEMA.read_text(encoding="utf-8"))["feature_order"]) == 78
    effective_start = pd.read_csv(FORMAL_EFFECTIVE_START, dtype=str)
    checks["formal_effective_start_frozen_and_applied_before_rolling"] = (
        sha(FORMAL_EFFECTIVE_START) == "dedba30e110a5e7fe9cdeecd35f7471065120c8924b599785205f7e640a3127e"
        and len(effective_start) == 150
        and effective_start.set_index("instrument").loc["TW7769", "effective_start"] == "2025-11-27"
        and "raw.date.ge(effective_start[symbol])" in builder_source
    )
    checks["isolated_price_15_feature_b2_overlap_parity"] = b2_price_overlap_parity()
    if freeze.is_file():
        frozen = json.loads(freeze.read_text(encoding="utf-8"))
        checks["freeze_closed_before_outcome"] = str(frozen.get("status", "")).startswith("CLOSED_BEFORE_ANY")
        checks["identity_is_new"] = frozen.get("new_model_identity", {}).get("new_identity_not_b9_or_failed_b19r2") is True
        checks["training_false"] = frozen.get("safety", {}).get("training_authorized") is False
        checks["confirmation_deny_default"] = frozen.get("sealed_confirmation_policy", {}).get("access") == "DENY_BY_DEFAULT"
        checks["fourty_ten_thirty_roles"] = (
            frozen.get("date_roles", {}).get("POST_B18_RESEARCH_DEVELOPMENT", {}).get("actual_trading_days") == 40
            and frozen.get("date_roles", {}).get("PURGE_EMBARGO_NO_OUTCOME_USE", {}).get("actual_trading_days") == 10
            and frozen.get("date_roles", {}).get("SEALED_CONFIRMATION", {}).get("actual_trading_days") == 30
        )
        checks["tie_rule_frozen"] = frozen.get("candidate_contract", {}).get("model_b_tie_rule") == "b_score desc, instrument asc"
        checks["all_numeric_gates_joint"] = frozen.get("preregistered_numeric_quality_gates", {}).get("all_gates_jointly_required") is True
    amendment3 = run / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_03.json"
    checks["amendment03_exists"] = amendment3.is_file()
    if amendment3.is_file():
        amended = json.loads(amendment3.read_text(encoding="utf-8"))
        checks["amendment03_retained_as_evidence"] = amended.get("status") == "ADDITIVE_CLOSED_BEFORE_ANY_B19R2R_MODEL_A_SCORE_OR_OUTCOME_READ"
        inner2 = amended.get("corrected_nested_walk_forward", {}).get("inner_2", {})
        checks["inner2_exact_ten_day_purge"] = len(inner2.get("purge_actual_dates", [])) == 10 and inner2.get("purge_actual_dates", [])[-1:] == ["2026-03-09"] and inner2.get("validation_start") == "2026-03-10"
        outer1 = amended.get("corrected_nested_walk_forward", {}).get("outer_1", {})
        checks["outer1_extra_unused_gap_declared"] = outer1.get("extra_unused_actual_dates_after_purge") == ["2026-05-08"] and outer1.get("validation_start") == "2026-05-11"
        checks["action_and_top1_gates_frozen"] = amended.get("additional_numeric_gates", {}).get("minimum_executed_buys_each_track") == 10 and amended.get("additional_numeric_gates", {}).get("top1_abs_contribution_share_max") == 0.20
    checks["amendment04_exists"] = AMENDMENT_04.is_file()
    if AMENDMENT_04.is_file():
        amended4 = json.loads(AMENDMENT_04.read_text(encoding="utf-8"))
        checks["amendment04_retained_as_evidence"] = amended4.get("status") == "ADDITIVE_CLOSED_BEFORE_ANY_B19R2R_MODEL_A_SCORE_OR_OUTCOME_READ"
        split = amended4.get("effective_future_training_split", {})
        checks["amendment03_split_is_unique_effective_split"] = (
            split.get("path") == rel(EFFECTIVE_SPLIT)
            and split.get("sha256") == sha(EFFECTIVE_SPLIT)
            and split.get("base_split_consumption_allowed") is False
            and split.get("only_effective_split_for_future_training") is True
        )
        gates = amended4.get("additional_numeric_gates", {})
        checks["action_count_inflation_gates_frozen"] = (
            gates.get("minimum_executed_buys_each_track") == 10
            and gates.get("executed_buy_count_ratio_b_over_a_max") == 1.25
            and gates.get("executed_sell_count_ratio_b_over_a_max") == 1.25
            and gates.get("executed_total_action_count_ratio_b_over_a_max") == 1.25
            and gates.get("executed_total_action_count_absolute_delta_b_minus_a_max") == 5
            and gates.get("zero_denominator_policy") == "FAIL_GATE"
        )
        provider_binding = amended4.get("isolated_provider_binding", {})
        checks.update(isolated_provider_checks(provider_binding))
    checks["attempt_failure01_exists"] = ATTEMPT_FAILURE_01.is_file()
    if ATTEMPT_FAILURE_01.is_file():
        failure = json.loads(ATTEMPT_FAILURE_01.read_text(encoding="utf-8"))
        checks["attempt_failure01_is_pre_score_no_outcome"] = (
            failure.get("status") == "FAILED_CLOSED_BEFORE_MODEL_A_SCORE_OR_OUTCOME_READ"
            and failure.get("failure", {}).get("model_pickle_loaded") is False
            and failure.get("failure", {}).get("model_predict_called") is False
            and failure.get("failure", {}).get("model_a_scores_generated") is False
            and failure.get("forbidden_activity_absence", {}).get("label_or_next_open_or_next_close_read_or_generated") is False
            and failure.get("partial_footprint", {}).get("materialization_state_exists") is False
        )
    checks["attempt_failure01_errata_exists"] = ATTEMPT_FAILURE_01_ERRATA.is_file()
    if ATTEMPT_FAILURE_01_ERRATA.is_file():
        errata = json.loads(ATTEMPT_FAILURE_01_ERRATA.read_text(encoding="utf-8"))
        checks["attempt_failure01_errata_discloses_rewrite"] = (
            errata.get("original_write", {}).get("sha256") == "f470be5e4399ee0fdc0e7a4990ce88c8a0ff3f2192921a97faac008d58d6fa4a"
            and errata.get("corrected_write", {}).get("sha256") == sha(ATTEMPT_FAILURE_01)
            and errata.get("original_write", {}).get("byte_copy_retained") is False
            and errata.get("future_rewrite_allowed") is False
        )
    checks["rollover_observation01_exists"] = ROLLOVER_OBSERVATION_01.is_file()
    checks["amendment05_exists"] = AMENDMENT_05.is_file()
    if AMENDMENT_05.is_file():
        amended5 = json.loads(AMENDMENT_05.read_text(encoding="utf-8"))
        bindings = amended5.get("implementation_bindings", {})
        checks["amendment05_builder_hash"] = bindings.get("input_builder", {}).get("sha256") == sha(BUILDER)
        checks["amendment05_validator_hash"] = bindings.get("validator", {}).get("sha256") == sha(Path(__file__))
        checks["amendment05_scorer_hash"] = bindings.get("label_free_model_a_scorer", {}).get("sha256") == sha(SCORER)
        checks["amendment05_prior_and_evidence_bindings"] = (
            amended5.get("amendment_04_sha256") == sha(AMENDMENT_04)
            and amended5.get("failed_attempt_binding", {}).get("sha256") == sha(ATTEMPT_FAILURE_01)
            and amended5.get("failed_attempt_errata_binding", {}).get("sha256") == sha(ATTEMPT_FAILURE_01_ERRATA)
            and amended5.get("rollover_observation_binding", {}).get("sha256") == sha(ROLLOVER_OBSERVATION_01)
        )
        checks["amendment05_isolated_provider_binding"] = amended5.get("isolated_provider_binding", {}).get("expected_clean_feature_tree_sha256") == "1bc340f039ab3504c8be6350cd44a5c4783d1ce69daf78e83db5f7f37cd9ba35"

    artifact_names = ["MODEL_A_FULL_CROSS_SECTION.parquet", "FEATURE_ARTIFACT_78_RAW.parquet", "EXACT50_KEYSETS.csv", "FEATURE_COVERAGE_AUDIT.csv", "PIT_AUDIT.csv", "TIE_AWARE_RANK_FIXTURE.csv"]
    state_path = run / "B19R2R_INPUT_MATERIALIZATION_STATE.json"
    footprint_exists = ISOLATED_PROVIDER.exists() or state_path.exists() or any((run / name).exists() for name in artifact_names)
    materialization_complete = state_path.is_file() and all((run / name).is_file() for name in artifact_names)
    checks["materialization_complete_if_any_footprint"] = not footprint_exists or materialization_complete
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        checks["state_outcome_false"] = state.get("outcome_values_read_or_generated") is False
        checks["state_model_b_false"] = state.get("model_b_or_b9_inference_performed") is False
        checks["state_training_false"] = state.get("training_performed") is False
        checks["state_source_scorer_hash_matches"] = state.get("label_free_scorer_source", {}).get("sha256") == sha(SCORER)
        checks["state_no_placeholder_lookback"] = state.get("non_trading_placeholder_20260710_removed_before_all_rolling") is True
        binding = json.loads(AMENDMENT_04.read_text(encoding="utf-8"))["isolated_provider_binding"]
        checks["state_binds_clean_provider_tree"] = state.get("scorer_provider_root") == rel(ISOLATED_PROVIDER) and state.get("scorer_provider_feature_tree_sha256") == binding["expected_clean_feature_tree_sha256"]
        for name in artifact_names:
            checks[f"artifact_exists_{name}"] = (run / name).is_file()
        if (run / "MODEL_A_FULL_CROSS_SECTION.parquet").is_file():
            a = pd.read_parquet(run / "MODEL_A_FULL_CROSS_SECTION.parquet", columns=["date", "instrument", "source_provider", "source_provider_calendar_sha256"])
            checks["model_a_150_each_date"] = bool((a.groupby("date").size() == 150).all())
            checks["model_a_no_duplicate_keys"] = not a.duplicated(["date", "instrument"]).any()
            checks["model_a_bound_to_isolated_provider"] = (
                a.source_provider.nunique() == 1
                and a.source_provider.iloc[0] == rel(run / "isolated_model_a_provider_no_nontrading_placeholders")
                and a.source_provider_calendar_sha256.nunique() == 1
                and a.source_provider_calendar_sha256.iloc[0] == sha(run / "isolated_model_a_provider_no_nontrading_placeholders/calendars/day.txt")
            )
        if (run / "FEATURE_ARTIFACT_78_RAW.parquet").is_file():
            f = pd.read_parquet(run / "FEATURE_ARTIFACT_78_RAW.parquet", columns=["date", "instrument", "available_at", "feature_raw_complete_78"])
            checks["feature_no_duplicate_keys"] = not f.duplicated(["date", "instrument"]).any()
            checks["feature_available_at_lte_date"] = bool((pd.to_datetime(f.available_at) <= pd.to_datetime(f.date)).all())
    protocol_checks = {key: value for key, value in checks.items() if key != "materialization_complete_if_any_footprint"}
    payload["protocol_precheck_verdict"] = "PASS" if all(protocol_checks.values()) else "HOLD"
    payload["verdict"] = "PASS" if all(checks.values()) else "HOLD"
    payload["hold_reason"] = "PARTIAL_MATERIALIZATION_FOOTPRINT" if footprint_exists and not materialization_complete else None
    payload["training_go_no_go"] = "NO_GO_TRAINING"
    payload["run"] = rel(run)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=R2R)
    args = parser.parse_args()
    result = validate(args.run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
