#!/usr/bin/env python3
"""Build the isolated B18 fixed-model historical PIT paired replay evidence."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b18r2_historical_pit_paired_replay_20260916"
B2 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913"
B3 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b3_frozen_modela_oos_score_20260913"
B9 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b9_canonical_label_retrain_20260914"
PROTOCOL = (
    ROOT
    / "data_tw/experiments/project_runtime_convergence/modelb_b18_historical_pit_protocol_20260916"
    / "B18_PROTOCOL_FREEZE.json"
)
FEATURES = B2 / "FEATURE_ARTIFACT_RAW.parquet"
PIT_AUDIT = B2 / "PIT_AND_SOURCE_STATUS_AUDIT.parquet"
MODEL_A = B3 / "MODEL_A_FROZEN_OOS_SCORE.parquet"
MODEL_B = B9 / "MODEL_B_CANONICAL_LGBM_RANKER.pkl"
LABELS = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_canonical_labels_20260914/CANONICAL_LABEL_ARTIFACT.csv"
STRATEGY_DEPENDENCY = ROOT / "configs/strategy_dependencies/top50_exit_one_worst_sell.yaml"
STRATEGY_DECISION_IMPL = ROOT / "scripts/build_tw_modular_order_intent_artifact.py"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"

START = "2025-01-02"
END = "2026-05-07"
TOP50 = 50
TARGET_HOLDINGS = 10
INITIAL_EQUITY = 1_000_000.0
FEE_RATE = 0.001425
SELL_TAX_RATE = 0.003
LOT_SIZE = 10
EXCLUDED_SYMBOLS = {"TW7769", "TW6919"}
EVIDENCE_STRATA = (
    ("development_validation", "2025-01-02", "2025-12-31"),
    ("frozen_model_retrospective_oos_previously_observed", "2026-01-02", "2026-04-22"),
    ("post_declared_test_tail_retrospective_holdout", "2026-04-23", "2026-05-07"),
)
PROTECTED = (
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def fingerprint(path: Path) -> dict[str, Any]:
    return {"path": relative(path), "exists": path.is_file(), "sha256": sha256(path)}


def protected_fingerprints() -> dict[str, dict[str, Any]]:
    return {relative(path): fingerprint(path) for path in PROTECTED}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def feature_order_hash(feature_order: list[str]) -> str:
    payload = json.dumps(feature_order, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def price_root_inventory() -> dict[str, Any]:
    files = sorted(PRICE_ROOT.glob("TW*.csv"))
    payload = "\n".join(f"{path.name},{sha256(path)}" for path in files)
    return {
        "root": relative(PRICE_ROOT),
        "file_count": len(files),
        "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }


def evidence_stratum(day: str) -> str:
    for name, start, end in EVIDENCE_STRATA:
        if start <= day <= end:
            return name
    raise RuntimeError(f"date outside frozen B18 evidence strata: {day}")


class PriceStore:
    def __init__(self, symbols: set[str]):
        self.rows: dict[str, pd.DataFrame] = {}
        self.price_hashes: dict[str, str] = {}
        for symbol in sorted(symbols):
            path = PRICE_ROOT / f"{symbol}.csv"
            if not path.is_file():
                raise RuntimeError(f"missing price file: {relative(path)}")
            frame = pd.read_csv(path, usecols=["date", "open", "close"], dtype={"date": str})
            frame["date"] = frame.date.str[:10]
            frame["open"] = pd.to_numeric(frame.open, errors="coerce")
            frame["close"] = pd.to_numeric(frame.close, errors="coerce")
            frame = frame.sort_values("date").drop_duplicates("date", keep="last")
            self.rows[symbol] = frame
            self.price_hashes[symbol] = sha256(path) or ""

    def next_open(self, symbol: str, day: str) -> tuple[str, float] | None:
        frame = self.rows[symbol]
        eligible = frame[(frame.date > day) & frame.open.notna() & (frame.open > 0)]
        if eligible.empty:
            return None
        row = eligible.iloc[0]
        return str(row.date), float(row.open)

    def close(self, symbol: str, day: str) -> float | None:
        frame = self.rows[symbol]
        eligible = frame[(frame.date <= day) & frame.close.notna() & (frame.close > 0)]
        if eligible.empty:
            return None
        return float(eligible.iloc[-1].close)

    def calendar(self, end: str) -> list[str]:
        days: set[str] = set()
        for frame in self.rows.values():
            days.update(frame.loc[(frame.date >= START) & (frame.date <= end), "date"].astype(str))
        return sorted(days)

    def inventory_hash(self) -> str:
        payload = "\n".join(f"{symbol},{digest}" for symbol, digest in sorted(self.price_hashes.items()))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def preregister_freeze() -> dict[str, Any]:
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError(f"B18 output already exists and is non-empty: {relative(OUT)}")
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol.get("status") != "FROZEN_BEFORE_OUTCOME_READ":
        raise RuntimeError("B18 protocol is not frozen before outcome read")
    expected = protocol["frozen_inputs"]
    actual_hashes = {
        "model_b": sha256(MODEL_B),
        "model_b_freeze": sha256(B9 / "B9_CANONICAL_RETRAIN_RUN_FREEZE.json"),
        "feature_artifact": sha256(FEATURES),
        "model_a_scores": sha256(MODEL_A),
    }
    for key, actual in actual_hashes.items():
        if actual != expected[key]["sha256"]:
            raise RuntimeError(f"B18 protocol frozen hash mismatch: {key}")
    dependency = yaml.safe_load(STRATEGY_DEPENDENCY.read_text(encoding="utf-8"))
    if dependency.get("strategy_rule") != "top50_exit_one_worst_sell":
        raise RuntimeError("strategy dependency rule drift")
    if dependency.get("max_buy_count") != 1 or dependency.get("max_sell_count") != 1:
        raise RuntimeError("strategy dependency max buy/sell drift")
    price_inventory = price_root_inventory()
    if price_inventory["file_count"] != 150:
        raise RuntimeError(f"expected 150 frozen price files, got {price_inventory['file_count']}")
    freeze = {
        "schema_version": "modelb.b18.historical_pit_paired_replay.freeze.v1",
        "status": "PREREGISTERED_BEFORE_SCORING_AND_REPLAY",
        "created_at": utc_now(),
        "run_id": OUT.name,
        "protocol_path": relative(PROTOCOL),
        "protocol_sha256": sha256(PROTOCOL),
        "protocol_frozen_at": protocol["frozen_at"],
        "model_b_frozen": relative(MODEL_B),
        "model_b_sha256": sha256(MODEL_B),
        "feature_artifact": relative(FEATURES),
        "feature_artifact_sha256": sha256(FEATURES),
        "pit_audit_sha256": sha256(PIT_AUDIT),
        "model_a_artifact": relative(MODEL_A),
        "model_a_artifact_sha256": sha256(MODEL_A),
        "evidence_strata": [
            {"name": name, "start": start, "end": end, "untouched": False}
            for name, start, end in EVIDENCE_STRATA
        ],
        "fit_window_excluded": ["2023-01-10", "2024-12-17"],
        "embargo_window_excluded": ["2024-12-18", "2024-12-31"],
        "candidate_policy": (
            "complete Model A cross-section -> exclude TW7769 and TW6919 -> exclude rows without all 78 "
            "raw PIT features -> sort original qlib_rank then instrument -> take 50"
        ),
        "experiment_rank_policy": (
            "eligible_candidate_rank is an experiment-only 1..50 ordinal; preserve original Model A rank as "
            "full_qlib_rank; output is not a ModelSignalArtifact"
        ),
        "rank_lineage_policy": (
            "B3 original qlib_rank controls candidate ordering and full-rank exit; B2 qlib_rank must equal "
            "B3 dynamic_qlib_rank and remains only a frozen B9 feature"
        ),
        "strategy_rule": "top50_exit_one_worst_sell",
        "strategy_dependency_path": relative(STRATEGY_DEPENDENCY),
        "strategy_dependency_sha256": sha256(STRATEGY_DEPENDENCY),
        "strategy_decision_impl_path": relative(STRATEGY_DECISION_IMPL),
        "strategy_decision_impl_sha256": sha256(STRATEGY_DECISION_IMPL),
        "max_buy_count_per_signal_day": 1,
        "max_sell_count_per_signal_day": 1,
        "target_holdings": TARGET_HOLDINGS,
        "execution_price_mode": "next_open",
        "missing_execution_price_policy": "block; no fallback",
        "zero_quantity_policy": "record explicit affordability skip; do not substitute a lower-ranked candidate",
        "initial_equity": INITIAL_EQUITY,
        "fee_rate": FEE_RATE,
        "sell_tax_rate": SELL_TAX_RATE,
        "lot_size": LOT_SIZE,
        "price_inventory": price_inventory,
        "regime_policy": "TWII_ret20 >= 0: NONNEGATIVE_20D; TWII_ret20 < 0: NEGATIVE_20D",
        "availability_policy": (
            "reconstructed_available_at is a conservative B2 PIT-rule assumption, not source-native historical "
            "publication or actual historical artifact visibility"
        ),
        "no_training": True,
        "no_tuning": True,
        "no_result_based_model_or_rule_selection": True,
        "no_baseline_admission": True,
        "production_allowed": False,
        "script_sha256": sha256(Path(__file__)),
    }
    write_json(OUT / "B18_RUN_FREEZE.json", freeze)
    return freeze


def load_and_score() -> tuple[pd.DataFrame, pd.DataFrame, list[str], dict[str, Any], dict[str, dict[str, int]]]:
    b2_manifest = json.loads((B2 / "B2_FEATURE_ARTIFACT_MANIFEST.json").read_text(encoding="utf-8"))
    b2_review = json.loads((B2 / "B2_INDEPENDENT_REVIEW.json").read_text(encoding="utf-8"))
    b9_freeze = json.loads((B9 / "B9_CANONICAL_RETRAIN_RUN_FREEZE.json").read_text(encoding="utf-8"))
    b9_review = json.loads((B9 / "B9_CANONICAL_RETRAIN_INDEPENDENT_REVIEW.json").read_text(encoding="utf-8"))
    if b2_manifest.get("status") != "PASS" or b2_review.get("verdict") != "PASS":
        raise RuntimeError("B2 final manifest/review does not pass")
    if b9_review.get("verdict") not in {"PASS", "PASS_WITH_CONDITIONS"}:
        raise RuntimeError("B9 independent review does not permit research scoring")

    model = joblib.load(MODEL_B)
    feature_order = list(model.booster_.feature_name())
    if len(feature_order) != 78:
        raise RuntimeError(f"B9 feature count drift: {len(feature_order)}")
    order_hash = feature_order_hash(feature_order)
    if order_hash != b9_freeze.get("feature_order_sha256"):
        raise RuntimeError("B9 model feature order hash drift")

    features = pd.read_parquet(FEATURES)
    model_a = pd.read_parquet(MODEL_A)
    pit = pd.read_parquet(PIT_AUDIT)
    for frame in (features, model_a, pit):
        frame["date"] = frame.date.astype(str).str[:10]
        frame["instrument"] = frame.instrument.astype(str).str.upper()
    features = features[(features.date >= START) & (features.date <= END)].copy()
    model_a = model_a[(model_a.date >= START) & (model_a.date <= END)].copy()
    pit = pit[(pit.date >= START) & (pit.date <= END)].copy()
    if features.duplicated(["date", "instrument"]).any() or model_a.duplicated(["date", "instrument"]).any():
        raise RuntimeError("duplicate feature or Model A key")

    feature_subset = features[["date", "instrument", "feature_raw_complete_78", *feature_order]].copy()
    model_a_merge = model_a[
        ["date", "instrument", "raw_score", "qlib_rank", "dynamic_qlib_rank", "dynamic_eligible"]
    ].rename(
        columns={
            "raw_score": "model_a_raw_score",
            "qlib_rank": "original_model_a_rank",
            "dynamic_qlib_rank": "model_a_dynamic_qlib_rank",
            "dynamic_eligible": "model_a_dynamic_eligible",
        }
    )
    model_a_feature_name_collisions = sorted(set(model_a_merge.columns) & set(feature_order))
    if model_a_feature_name_collisions:
        raise RuntimeError(f"Model A provenance columns collide with B9 feature order: {model_a_feature_name_collisions}")
    merged = model_a_merge.merge(
        feature_subset, on=["date", "instrument"], how="left", validate="one_to_one"
    )
    merged["original_model_a_rank"] = pd.to_numeric(merged.original_model_a_rank, errors="coerce")
    merged["model_a_dynamic_qlib_rank"] = pd.to_numeric(
        merged.model_a_dynamic_qlib_rank, errors="coerce"
    )
    merged["model_a_raw_score"] = pd.to_numeric(merged.model_a_raw_score, errors="coerce")
    merged["qlib_rank"] = pd.to_numeric(merged.qlib_rank, errors="coerce")
    merged["qlib_score_raw"] = pd.to_numeric(merged.qlib_score_raw, errors="coerce")
    key_present = merged.qlib_rank.notna() & merged.qlib_score_raw.notna()
    merged["dynamic_rank_mismatch"] = key_present & ~np.isclose(
        merged.model_a_dynamic_qlib_rank, merged.qlib_rank, rtol=0.0, atol=0.0
    )
    merged["score_mismatch"] = key_present & ~np.isclose(
        merged.model_a_raw_score, merged.qlib_score_raw, rtol=1e-12, atol=1e-12
    )
    parity_audit = merged.groupby("date", as_index=False).agg(
        model_a_rows=("instrument", "size"),
        feature_key_rows=("qlib_rank", "count"),
        dynamic_rank_mismatch_rows=("dynamic_rank_mismatch", "sum"),
        score_mismatch_rows=("score_mismatch", "sum"),
        dynamic_ineligible_common_rows=(
            "model_a_dynamic_eligible",
            lambda values: int((~values.fillna(False).astype(bool)).sum()),
        ),
    )
    parity_audit["missing_feature_key_rows"] = parity_audit.model_a_rows - parity_audit.feature_key_rows
    missing_feature_keys = merged.loc[~key_present, ["date", "instrument"]].copy()
    missing_feature_symbols = sorted(missing_feature_keys.instrument.unique())
    # Missing B2 keys are handled separately; all common B2/B3 keys must be dynamically eligible.
    dynamic_ineligible_common = int(
        ((~merged.model_a_dynamic_eligible.fillna(False).astype(bool)) & key_present).sum()
    )
    if int(parity_audit.dynamic_rank_mismatch_rows.sum()) or int(parity_audit.score_mismatch_rows.sum()):
        raise RuntimeError("B2/B3 dynamic qlib rank or raw score parity mismatch")
    if dynamic_ineligible_common:
        raise RuntimeError("B2/B3 common key includes dynamic_eligible=false rows")
    if missing_feature_symbols != ["TW7769"]:
        raise RuntimeError(f"unexpected B3 keys missing from B2: {missing_feature_symbols}")
    complete = merged.feature_raw_complete_78.eq(True)
    finite = np.isfinite(merged[feature_order].to_numpy(dtype=float)).all(axis=1)
    merged["structurally_excluded"] = merged.instrument.isin(EXCLUDED_SYMBOLS)
    merged["eligible_for_b18_scoring"] = complete & finite & ~merged.structurally_excluded

    selected_frames: list[pd.DataFrame] = []
    coverage_rows: list[dict[str, Any]] = []
    for day, group in merged.groupby("date", sort=True):
        eligible = group[group.eligible_for_b18_scoring].copy()
        eligible = eligible.sort_values(["original_model_a_rank", "instrument"], ascending=[True, True])
        selected = eligible.head(TOP50).copy()
        selected["eligible_candidate_rank"] = np.arange(1, len(selected) + 1)
        selected["full_qlib_rank"] = selected.original_model_a_rank.astype(int)
        selected["evidence_stratum"] = evidence_stratum(day)
        coverage_rows.append(
            {
                "date": day,
                "evidence_stratum": evidence_stratum(day),
                "model_a_cross_section_rows": int(len(group)),
                "tw7769_rows_excluded_before_top50": int(group.instrument.eq("TW7769").sum()),
                "tw6919_rows_excluded_before_top50": int(group.instrument.eq("TW6919").sum()),
                "structural_exclusion_rows_before_top50": int(group.structurally_excluded.sum()),
                "raw_feature_incomplete_rows_before_top50": int((~complete.loc[group.index]).sum()),
                "nonstructural_feature_incomplete_rows_excluded_before_top50": int(
                    ((~complete.loc[group.index]) & (~group.structurally_excluded)).sum()
                ),
                "eligible_rows_before_top50": int(len(eligible)),
                "selected_rows": int(len(selected)),
                "eligible_candidate_rank_min": int(selected.eligible_candidate_rank.min()) if len(selected) else None,
                "eligible_candidate_rank_max": int(selected.eligible_candidate_rank.max()) if len(selected) else None,
                "full_qlib_rank_max": int(selected.full_qlib_rank.max()) if len(selected) else None,
                "exact_50": len(selected) == TOP50,
                "tw7769_selected": bool(selected.instrument.eq("TW7769").any()),
                "tw6919_selected": bool(selected.instrument.eq("TW6919").any()),
                "all_78_finite": bool(np.isfinite(selected[feature_order].to_numpy(dtype=float)).all()),
            }
        )
        if len(selected) != TOP50:
            raise RuntimeError(f"date {day} cannot form exact eligible Top50: {len(selected)}")
        selected_frames.append(selected)

    signals = pd.concat(selected_frames, ignore_index=True)
    signals["b_score"] = model.predict(signals[feature_order])
    signals["a_score"] = signals.model_a_raw_score.astype(float)
    signals["a_buy_rank"] = signals.groupby("date").a_score.rank(method="first", ascending=False).astype(int)
    signals["b_buy_rank"] = signals.groupby("date").b_score.rank(method="first", ascending=False).astype(int)
    signals["signal_asof"] = signals.date
    signals["reconstructed_available_at"] = signals.date + "T18:00:00+08:00"
    signals["market_regime"] = np.where(signals.TWII_ret20 >= 0, "NONNEGATIVE_20D", "NEGATIVE_20D")
    if signals.groupby("date").market_regime.nunique().max() != 1:
        raise RuntimeError("TWII market regime is not date-level stable")

    pit_columns = [
        "date",
        "instrument",
        "institutional_available_at",
        "institutional_rebuilt_available_at",
        "institutional_used_available_at_gt_sample_date",
        "institutional_rebuilt_used_available_at_gt_sample_date",
        "margin_available_at",
        "margin_rebuilt_available_at",
        "margin_used_available_at_gt_sample_date",
        "margin_rebuilt_used_available_at_gt_sample_date",
    ]
    selected_pit = signals[["date", "instrument"]].merge(
        pit[pit_columns], on=["date", "instrument"], how="left", validate="one_to_one"
    )
    future_flag_cols = [column for column in pit_columns if column.endswith("gt_sample_date")]
    available_cols = [column for column in pit_columns if column.endswith("available_at")]
    selected_pit["future_flag_any"] = selected_pit[future_flag_cols].fillna(False).astype(bool).any(axis=1)
    for column in available_cols:
        selected_pit[f"{column}_lte_signal_asof"] = (
            selected_pit[column].notna() & (selected_pit[column].astype(str).str[:10] <= selected_pit.date)
        )
    selected_pit["all_source_available_at_lte_signal_asof"] = selected_pit[
        [f"{column}_lte_signal_asof" for column in available_cols]
    ].all(axis=1)
    if selected_pit.future_flag_any.any() or not selected_pit.all_source_available_at_lte_signal_asof.all():
        raise RuntimeError("selected B18 rows fail PIT available_at audit")

    output_columns = [
        "date",
        "instrument",
        "evidence_stratum",
        "eligible_candidate_rank",
        "full_qlib_rank",
        "a_score",
        "b_score",
        "a_buy_rank",
        "b_buy_rank",
        "signal_asof",
        "reconstructed_available_at",
        "market_regime",
    ]
    signals_out = signals[output_columns].sort_values(["date", "eligible_candidate_rank", "instrument"]).copy()
    coverage = pd.DataFrame(coverage_rows)
    metadata = {
        "feature_count": len(feature_order),
        "feature_order_sha256": order_hash,
        "dates": int(signals_out.date.nunique()),
        "rows": int(len(signals_out)),
        "date_min": str(signals_out.date.min()),
        "date_max": str(signals_out.date.max()),
        "max_original_full_qlib_rank": int(signals_out.full_qlib_rank.max()),
        "dates_requiring_replenishment_beyond_original_rank_50": int(
            signals_out.groupby("date").full_qlib_rank.max().gt(50).sum()
        ),
        "pit_future_flag_rows": int(selected_pit.future_flag_any.sum()),
        "pit_available_at_fail_rows": int((~selected_pit.all_source_available_at_lte_signal_asof).sum()),
        "b2_b3_dynamic_rank_parity_mismatch_rows": int(
            parity_audit.dynamic_rank_mismatch_rows.sum()
        ),
        "b2_b3_score_parity_mismatch_rows": int(parity_audit.score_mismatch_rows.sum()),
        "b3_keys_missing_from_b2": int(len(missing_feature_keys)),
        "b3_keys_missing_from_b2_symbols": missing_feature_symbols,
        "b2_b3_common_dynamic_ineligible_rows": dynamic_ineligible_common,
        "model_a_feature_name_collisions": model_a_feature_name_collisions,
        "selected_rows_missing_feature_key": int(signals.qlib_rank.isna().sum()),
        "selected_dynamic_rank_parity_mismatch_rows": int(signals.dynamic_rank_mismatch.sum()),
        "selected_score_parity_mismatch_rows": int(signals.score_mismatch.sum()),
    }
    full_rank_lookup = {
        day: {
            str(row.instrument): int(row.qlib_rank)
            for row in group.dropna(subset=["qlib_rank"]).itertuples(index=False)
        }
        for day, group in model_a.groupby("date")
    }
    return signals_out, coverage, feature_order, {
        "metadata": metadata,
        "pit": selected_pit,
        "model_a_feature_parity": parity_audit,
        "missing_feature_keys": missing_feature_keys,
    }, full_rank_lookup


def replay(
    signals: pd.DataFrame,
    prices: PriceStore,
    score_column: str,
    method: str,
    full_rank_lookup: dict[str, dict[str, int]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    by_day = {day: group.copy() for day, group in signals.groupby("date")}
    last_signal = str(signals.date.max())
    settlement_quotes = [prices.next_open(symbol, last_signal) for symbol in sorted(set(signals.instrument))]
    if any(quote is None for quote in settlement_quotes):
        raise RuntimeError("missing post-window next_open; no fallback permitted")
    settlement_end = max(str(quote[0]) for quote in settlement_quotes if quote is not None)
    calendar = prices.calendar(settlement_end)
    holdings: dict[str, int] = {}
    cost_basis: dict[str, float] = {}
    pending: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cash = INITIAL_EQUITY
    commission_total = 0.0
    tax_total = 0.0
    actions: list[dict[str, Any]] = []
    nav: list[dict[str, Any]] = []
    price_audit: list[dict[str, Any]] = []
    pending_duplicate_observations = 0

    for day in calendar:
        for order in pending.pop(day, []):
            symbol = str(order["instrument"])
            price = float(order["scheduled_next_open"])
            direct_quote = prices.next_open(symbol, str(order["signal_date"]))
            exact_next_open = bool(direct_quote and direct_quote[0] == day and math.isclose(direct_quote[1], price))
            if not exact_next_open:
                raise RuntimeError(f"next_open lineage mismatch for {method} {symbol} {order['signal_date']}")
            if order["action"] == "sell":
                quantity = int(holdings.pop(symbol))
                basis = float(cost_basis.pop(symbol))
                commission = quantity * price * FEE_RATE
                tax = quantity * price * SELL_TAX_RATE
                cash += quantity * price - commission - tax
                commission_total += commission
                tax_total += tax
                actions.append(
                    {
                        **order,
                        "method": method,
                        "execution_date": day,
                        "execution_price": price,
                        "quantity": quantity,
                        "commission": commission,
                        "sell_tax": tax,
                        "gross_pnl": quantity * price - basis,
                        "net_pnl": quantity * price - basis - commission - tax,
                        "status": "EXECUTED",
                    }
                )
            else:
                if order.get("quantity_mode") == "fill_available_slot_at_execution":
                    allocation = cash / max(1, TARGET_HOLDINGS - len(holdings))
                    quantity = int(allocation // (price * (1 + FEE_RATE) * LOT_SIZE)) * LOT_SIZE
                else:
                    quantity = int(order["quantity"])
                total_cash = quantity * price * (1 + FEE_RATE)
                if quantity <= 0 or total_cash > cash:
                    actions.append(
                        {
                            **order,
                            "method": method,
                            "execution_date": day,
                            "execution_price": price,
                            "quantity": 0,
                            "commission": 0.0,
                            "sell_tax": 0.0,
                            "status": "SKIPPED_ZERO_OR_INSUFFICIENT_CASH",
                        }
                    )
                else:
                    commission = quantity * price * FEE_RATE
                    cash -= total_cash
                    commission_total += commission
                    holdings[symbol] = holdings.get(symbol, 0) + quantity
                    cost_basis[symbol] = cost_basis.get(symbol, 0.0) + quantity * price
                    actions.append(
                        {
                            **order,
                            "method": method,
                            "execution_date": day,
                            "execution_price": price,
                            "quantity": quantity,
                            "commission": commission,
                            "sell_tax": 0.0,
                            "gross_pnl": 0.0,
                            "net_pnl": -commission,
                            "status": "EXECUTED",
                        }
                    )
            price_audit.append(
                {
                    "method": method,
                    "signal_date": order["signal_date"],
                    "instrument": symbol,
                    "action": order["action"],
                    "execution_date": day,
                    "exact_first_available_next_open": exact_next_open,
                    "fallback_used": False,
                }
            )

        market_value = 0.0
        missing_close = 0
        for symbol, quantity in holdings.items():
            close = prices.close(symbol, day)
            if close is None:
                missing_close += 1
            else:
                market_value += quantity * close
        nav.append(
            {
                "date": day,
                "method": method,
                "evidence_stratum": evidence_stratum(day) if START <= day <= END else "post_window_settlement",
                "cash": cash,
                "market_value": market_value,
                "equity": cash + market_value,
                "holding_count": len(holdings),
                "missing_close_count": missing_close,
                "pending_count": sum(len(value) for value in pending.values()),
            }
        )
        if day not in by_day:
            continue

        group = by_day[day]
        top50 = set(group.instrument)
        pending_pairs = {
            (str(order["instrument"]), str(order["action"]))
            for orders in pending.values()
            for order in orders
        }
        outside = [symbol for symbol in holdings if symbol not in top50]
        if outside:
            rank_lookup = full_rank_lookup.get(day, {})
            worst = max(outside, key=lambda symbol: (rank_lookup.get(symbol, 10**9), symbol))
            if (worst, "sell") not in pending_pairs:
                quote = prices.next_open(worst, day)
                if quote is None:
                    raise RuntimeError(f"missing next_open sell price: {method} {day} {worst}")
                pending[quote[0]].append(
                    {
                        "signal_date": day,
                        "instrument": worst,
                        "action": "sell",
                        "quantity": holdings[worst],
                        "reason": "top50_exit_one_worst_sell",
                        "scheduled_next_open": quote[1],
                    }
                )

        pending_sell_count = sum(
            1 for orders in pending.values() for order in orders if order["action"] == "sell"
        )
        pending_buy_count = sum(
            1 for orders in pending.values() for order in orders if order["action"] == "buy"
        )
        projected_holdings = len(holdings) - pending_sell_count + pending_buy_count
        if projected_holdings < TARGET_HOLDINGS:
            ranked = group.sort_values([score_column, "instrument"], ascending=[False, True])
            pending_buy_symbols = {
                str(order["instrument"])
                for orders in pending.values()
                for order in orders
                if order["action"] == "buy"
            }
            for row in ranked.itertuples(index=False):
                if row.instrument in holdings or row.instrument in pending_buy_symbols:
                    continue
                quote = prices.next_open(row.instrument, day)
                if quote is None:
                    raise RuntimeError(f"missing next_open buy price: {method} {day} {row.instrument}")
                pending_sell_dates = {
                    execution_day
                    for execution_day, orders in pending.items()
                    for order in orders
                    if order["action"] == "sell"
                }
                if pending_sell_dates and quote[0] not in pending_sell_dates:
                    raise RuntimeError(
                        f"paired sell/buy next_open date mismatch: {method} {day} {sorted(pending_sell_dates)} {quote[0]}"
                    )
                pending[quote[0]].append(
                    {
                        "signal_date": day,
                        "instrument": row.instrument,
                        "action": "buy",
                        "quantity": -1,
                        "quantity_mode": "fill_available_slot_at_execution",
                        "reason": "top50_buy_score_rank",
                        "scheduled_next_open": quote[1],
                    }
                )
                break
        pending_keys = [
            (str(order["instrument"]), str(order["action"]))
            for orders in pending.values()
            for order in orders
        ]
        duplicate_count = len(pending_keys) - len(set(pending_keys))
        pending_duplicate_observations += duplicate_count
        if duplicate_count:
            raise RuntimeError(f"duplicate pending symbol/action for {method} on {day}")

    if pending:
        raise RuntimeError(f"unsettled next_open orders remain for {method}: {sum(map(len, pending.values()))}")
    nav_frame = pd.DataFrame(nav)
    if (nav_frame.missing_close_count > 0).any():
        raise RuntimeError(f"missing mark-to-market closes for {method}")
    nav_frame["daily_return"] = nav_frame.equity.pct_change().fillna(0.0)
    nav_frame["drawdown"] = nav_frame.equity / nav_frame.equity.cummax() - 1.0
    active = [row for row in actions if row.get("status") == "EXECUTED" and int(row["quantity"]) > 0]
    skipped_actions = [row for row in actions if row.get("status") != "EXECUTED"]
    intent_frame = pd.DataFrame(actions)
    max_buy_intents = int(
        intent_frame.loc[intent_frame.action.eq("buy")].groupby("signal_date").size().max()
    ) if not intent_frame.loc[intent_frame.action.eq("buy")].empty else 0
    max_sell_intents = int(
        intent_frame.loc[intent_frame.action.eq("sell")].groupby("signal_date").size().max()
    ) if not intent_frame.loc[intent_frame.action.eq("sell")].empty else 0
    intent_key_duplicate_count = int(
        intent_frame.duplicated(["signal_date", "instrument", "action"]).sum()
    )
    sell_signal_days = set(intent_frame.loc[intent_frame.action.eq("sell"), "signal_date"].astype(str))
    buy_signal_days = set(intent_frame.loc[intent_frame.action.eq("buy"), "signal_date"].astype(str))
    turnover_notional = sum(float(row["quantity"]) * float(row["execution_price"]) for row in active)
    metrics = {
        "method": method,
        "signal_days": int(signals.date.nunique()),
        "calendar_days": int(len(nav_frame)),
        "final_equity": float(nav_frame.equity.iloc[-1]),
        "net_return": float(nav_frame.equity.iloc[-1] / INITIAL_EQUITY - 1),
        "max_drawdown": float(nav_frame.drawdown.min()),
        "turnover_notional": float(turnover_notional),
        "turnover": float(turnover_notional / INITIAL_EQUITY),
        "action_count": len(active),
        "buy_count": sum(row["action"] == "buy" for row in active),
        "sell_count": sum(row["action"] == "sell" for row in active),
        "commission": float(commission_total),
        "sell_tax": float(tax_total),
        "fee_tax": float(commission_total + tax_total),
        "missing_price_days": int((nav_frame.missing_close_count > 0).sum()),
        "pending_orders": 0,
        "next_open_fallback_count": 0,
        "max_buy_intents_per_signal_day": max_buy_intents,
        "max_sell_intents_per_signal_day": max_sell_intents,
        "max_holding_count": int(nav_frame.holding_count.max()),
        "duplicate_pending_symbol_action_count": pending_duplicate_observations,
        "duplicate_intent_key_count": intent_key_duplicate_count,
        "sell_signal_days_without_same_day_buy_intent": len(sell_signal_days - buy_signal_days),
        "skipped_or_zero_quantity_actions": len(skipped_actions),
    }
    return metrics, actions, nav_frame.to_dict("records"), price_audit


def stratum_metrics(nav: pd.DataFrame, method: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, start, end in EVIDENCE_STRATA:
        subset = nav[(nav.date >= start) & (nav.date <= end)].copy()
        if subset.empty:
            continue
        start_equity = float(subset.equity.iloc[0])
        end_equity = float(subset.equity.iloc[-1])
        peak = subset.equity.cummax()
        rows.append(
            {
                "method": method,
                "evidence_stratum": name,
                "start": start,
                "end": end,
                "calendar_days": int(len(subset)),
                "start_equity": start_equity,
                "end_equity": end_equity,
                "net_return": end_equity / start_equity - 1 if start_equity else 0.0,
                "max_drawdown_within_stratum": float((subset.equity / peak - 1).min()),
                "untouched": False,
            }
        )
    return rows


def monthly_metrics(paired_daily: pd.DataFrame) -> list[dict[str, Any]]:
    eligible = paired_daily[paired_daily.date.between(START, END)].copy()
    eligible["month"] = eligible.date.str[:7]
    rows: list[dict[str, Any]] = []
    for month, group in eligible.groupby("month", sort=True):
        a_return = float((1.0 + group.a_daily_return).prod() - 1.0)
        b_return = float((1.0 + group.b_daily_return).prod() - 1.0)
        rows.append(
            {
                "month": month,
                "trading_days": int(len(group)),
                "a_only_return": a_return,
                "a_plus_b_return": b_return,
                "active_return_b_minus_a": b_return - a_return,
                "b_outperformed": b_return > a_return,
            }
        )
    return rows


def regime_metrics(paired_daily: pd.DataFrame, signals: pd.DataFrame) -> list[dict[str, Any]]:
    regime_by_date = signals.groupby("date").market_regime.first().to_dict()
    eligible = paired_daily[paired_daily.date.isin(regime_by_date)].copy()
    eligible["market_regime"] = eligible.date.map(regime_by_date)
    rows: list[dict[str, Any]] = []
    for regime, group in eligible.groupby("market_regime", sort=True):
        a_return = float((1.0 + group.a_daily_return).prod() - 1.0)
        b_return = float((1.0 + group.b_daily_return).prod() - 1.0)
        rows.append(
            {
                "market_regime": regime,
                "signal_days": int(len(group)),
                "a_only_return": a_return,
                "a_plus_b_return": b_return,
                "active_return_b_minus_a": b_return - a_return,
                "b_outperformed": b_return > a_return,
            }
        )
    return rows


def rank_metrics(signals: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    label_column = "relevance_10d_top_heavy_canonical"
    labels = pd.read_csv(
        LABELS,
        usecols=["date", "instrument", label_column, "label_complete_10d_canonical"],
        dtype={"date": str, "instrument": str},
    )
    labels["date"] = labels.date.str[:10]
    labels["instrument"] = labels.instrument.str.upper()
    labels = labels[labels.date.between(START, END)].copy()
    merged = signals.merge(labels, on=["date", "instrument"], how="left", validate="one_to_one")
    coverage_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []

    def ndcg(relevance: np.ndarray, scores: np.ndarray, k: int) -> float:
        order = np.lexsort((np.arange(len(scores)), -scores))
        ideal = np.argsort(-relevance, kind="stable")

        def dcg(indices: np.ndarray) -> float:
            chosen = relevance[indices[:k]]
            discounts = np.log2(np.arange(2, len(chosen) + 2))
            return float(np.sum((np.power(2.0, chosen) - 1.0) / discounts))

        denominator = dcg(ideal)
        return dcg(order) / denominator if denominator > 0 else 0.0

    for day, group in merged.groupby("date", sort=True):
        complete = group.label_complete_10d_canonical.fillna(False).astype(bool) & group[label_column].notna()
        coverage_rows.append(
            {
                "date": day,
                "evidence_stratum": evidence_stratum(day),
                "signal_rows": int(len(group)),
                "complete_label_rows": int(complete.sum()),
                "rank_metrics_eligible": int(complete.sum()) == TOP50,
                "tail_label_unavailable_expected": evidence_stratum(day)
                == "post_declared_test_tail_retrospective_holdout",
            }
        )
        if int(complete.sum()) != TOP50:
            continue
        evaluated = group.loc[complete].sort_values("instrument").copy()
        relevance = evaluated[label_column].to_numpy(dtype=float)
        label_rank = pd.Series(relevance).rank(method="average").to_numpy(dtype=float)
        for method, score_column in (("A_ONLY", "a_score"), ("A_PLUS_B", "b_score")):
            scores = evaluated[score_column].to_numpy(dtype=float)
            score_rank = pd.Series(scores).rank(method="average").to_numpy(dtype=float)
            rank_ic = float(np.corrcoef(score_rank, label_rank)[0, 1])
            metric_rows.append(
                {
                    "date": day,
                    "month": day[:7],
                    "evidence_stratum": evidence_stratum(day),
                    "method": method,
                    "rows": TOP50,
                    "rank_ic": 0.0 if not math.isfinite(rank_ic) else rank_ic,
                    "ndcg_at_10": ndcg(relevance, scores, 10),
                    "ndcg_at_30": ndcg(relevance, scores, 30),
                    "ndcg_at_50": ndcg(relevance, scores, 50),
                }
            )
    daily = pd.DataFrame(metric_rows)
    monthly = (
        daily.groupby(["month", "evidence_stratum", "method"], as_index=False)[
            ["rank_ic", "ndcg_at_10", "ndcg_at_30", "ndcg_at_50"]
        ]
        .mean()
        .merge(
            daily.groupby(["month", "evidence_stratum", "method"], as_index=False).size(),
            on=["month", "evidence_stratum", "method"],
            validate="one_to_one",
        )
        .rename(columns={"size": "signal_days"})
    )
    return daily, monthly, pd.DataFrame(coverage_rows)


def pnl_concentration(
    a_actions: list[dict[str, Any]], b_actions: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = [row for row in a_actions + b_actions if row.get("action") == "sell" and row.get("status") == "EXECUTED"]
    if not rows:
        return [], []
    frame = pd.DataFrame(rows)
    frame["sell_notional"] = frame.quantity.astype(float) * frame.execution_price.astype(float)
    grouped = frame.groupby(["method", "instrument"], as_index=False).agg(
        realized_net_pnl=("net_pnl", "sum"),
        sell_notional=("sell_notional", "sum"),
        sell_count=("instrument", "size"),
    )
    grouped["abs_realized_pnl"] = grouped.realized_net_pnl.abs()
    grouped["share_of_abs_realized_pnl"] = grouped.abs_realized_pnl / grouped.groupby("method").abs_realized_pnl.transform("sum")
    grouped["share_of_sell_notional"] = grouped.sell_notional / grouped.groupby("method").sell_notional.transform("sum")
    detail = grouped.sort_values(["method", "share_of_abs_realized_pnl"], ascending=[True, False]).to_dict("records")
    summary: list[dict[str, Any]] = []
    for method, group in grouped.groupby("method"):
        shares = group.share_of_abs_realized_pnl.sort_values(ascending=False)
        summary.append(
            {
                "method": method,
                "symbols_with_realized_pnl": int(len(group)),
                "top1_abs_pnl_share": float(shares.head(1).sum()),
                "top5_abs_pnl_share": float(shares.head(5).sum()),
                "abs_pnl_hhi": float((shares**2).sum()),
            }
        )
    return detail, summary


def main() -> int:
    protected_before = protected_fingerprints()
    freeze = preregister_freeze()
    signals, coverage, feature_order, score_audit, full_rank_lookup = load_and_score()
    prices = PriceStore(set(signals.instrument))

    signals.to_csv(OUT / "signals.csv", index=False)
    coverage.to_csv(OUT / "daily_coverage.csv", index=False)
    score_audit["pit"].to_csv(OUT / "pit_available_at_audit.csv", index=False)
    score_audit["model_a_feature_parity"].to_csv(
        OUT / "model_a_feature_parity_audit.csv", index=False
    )
    score_audit["missing_feature_keys"].to_csv(OUT / "missing_feature_keys.csv", index=False)

    a_metrics, a_actions, a_nav_rows, a_price_audit = replay(
        signals, prices, "a_score", "A_ONLY", full_rank_lookup
    )
    b_metrics, b_actions, b_nav_rows, b_price_audit = replay(
        signals, prices, "b_score", "A_PLUS_B", full_rank_lookup
    )
    write_csv(OUT / "A_ONLY_actions.csv", a_actions)
    write_csv(OUT / "A_PLUS_B_actions.csv", b_actions)
    write_csv(OUT / "A_ONLY_daily_ledger.csv", a_nav_rows)
    write_csv(OUT / "A_PLUS_B_daily_ledger.csv", b_nav_rows)
    write_csv(OUT / "next_open_audit.csv", a_price_audit + b_price_audit)

    a_nav = pd.DataFrame(a_nav_rows)
    b_nav = pd.DataFrame(b_nav_rows)
    strata = stratum_metrics(a_nav, "A_ONLY") + stratum_metrics(b_nav, "A_PLUS_B")
    write_csv(OUT / "stratum_metrics.csv", strata)
    paired_daily = a_nav[["date", "daily_return", "equity"]].rename(
        columns={"daily_return": "a_daily_return", "equity": "a_equity"}
    ).merge(
        b_nav[["date", "daily_return", "equity"]].rename(
            columns={"daily_return": "b_daily_return", "equity": "b_equity"}
        ),
        on="date",
        validate="one_to_one",
    )
    paired_daily["active_return_b_minus_a"] = paired_daily.b_daily_return - paired_daily.a_daily_return
    paired_daily["evidence_stratum"] = paired_daily.date.map(
        lambda day: evidence_stratum(day) if START <= day <= END else "post_window_settlement"
    )
    paired_daily.to_csv(OUT / "paired_daily_metrics.csv", index=False)
    monthly = monthly_metrics(paired_daily)
    regimes = regime_metrics(paired_daily, signals)
    concentration_detail, concentration_summary = pnl_concentration(a_actions, b_actions)
    rank_daily, rank_monthly, rank_coverage = rank_metrics(signals)
    write_csv(OUT / "monthly_metrics.csv", monthly)
    write_csv(OUT / "regime_metrics.csv", regimes)
    write_csv(OUT / "pnl_concentration.csv", concentration_detail)
    rank_daily.to_csv(OUT / "rank_metrics_daily.csv", index=False)
    rank_monthly.to_csv(OUT / "rank_metrics_monthly.csv", index=False)
    rank_coverage.to_csv(OUT / "rank_metrics_coverage.csv", index=False)

    protected_after = protected_fingerprints()
    relative_metrics = {
        "net_return_diff_b_minus_a": b_metrics["net_return"] - a_metrics["net_return"],
        "final_equity_diff_b_minus_a": b_metrics["final_equity"] - a_metrics["final_equity"],
        "max_drawdown_diff_b_minus_a": b_metrics["max_drawdown"] - a_metrics["max_drawdown"],
        "turnover_diff_b_minus_a": b_metrics["turnover"] - a_metrics["turnover"],
        "fee_tax_diff_b_minus_a": b_metrics["fee_tax"] - a_metrics["fee_tax"],
        "active_daily_win_rate": float((paired_daily.active_return_b_minus_a > 0).mean()),
        "months_b_outperformed": sum(bool(row["b_outperformed"]) for row in monthly),
        "months_total": len(monthly),
        "regimes_b_outperformed": sum(bool(row["b_outperformed"]) for row in regimes),
        "regimes_total": len(regimes),
    }
    paired_metrics = pd.DataFrame([a_metrics, b_metrics])
    paired_metrics.to_csv(OUT / "paired_metrics.csv", index=False)

    checks = {
        "freeze_created_before_results": (OUT / "B18_RUN_FREEZE.json").stat().st_mtime
        <= (OUT / "signals.csv").stat().st_mtime,
        "no_fit_or_embargo_dates": bool((signals.date >= START).all()),
        "at_least_120_signal_days": signals.date.nunique() >= 120,
        "daily_exact_50": bool(coverage.exact_50.all()) and len(signals) == signals.date.nunique() * TOP50,
        "eligible_candidate_rank_exact_1_to_50": bool(
            signals.groupby("date").eligible_candidate_rank.apply(
                lambda values: set(values) == set(range(1, 51))
            ).all()
        ),
        "tw7769_excluded_before_top50": not signals.instrument.eq("TW7769").any(),
        "tw6919_incomplete_not_selected": not signals.instrument.eq("TW6919").any(),
        "feature_count_78": len(feature_order) == 78,
        "model_a_feature_order_collision_zero": not score_audit["metadata"][
            "model_a_feature_name_collisions"
        ],
        "b2_b3_dynamic_rank_score_parity": score_audit["metadata"][
            "b2_b3_dynamic_rank_parity_mismatch_rows"
        ] == 0
        and score_audit["metadata"]["b2_b3_score_parity_mismatch_rows"] == 0,
        "b3_missing_b2_keys_exact_tw7769": score_audit["metadata"]["b3_keys_missing_from_b2"]
        == 277
        and score_audit["metadata"]["b3_keys_missing_from_b2_symbols"] == ["TW7769"],
        "b2_b3_common_keys_dynamic_eligible": score_audit["metadata"][
            "b2_b3_common_dynamic_ineligible_rows"
        ] == 0,
        "selected_key_and_rank_score_parity": score_audit["metadata"][
            "selected_rows_missing_feature_key"
        ] == 0
        and score_audit["metadata"]["selected_dynamic_rank_parity_mismatch_rows"] == 0
        and score_audit["metadata"]["selected_score_parity_mismatch_rows"] == 0,
        "all_selected_features_pit_safe": score_audit["metadata"]["pit_future_flag_rows"] == 0
        and score_audit["metadata"]["pit_available_at_fail_rows"] == 0,
        "next_open_exact_no_fallback": all(
            row["exact_first_available_next_open"] and not row["fallback_used"]
            for row in a_price_audit + b_price_audit
        ),
        "pending_orders_zero": a_metrics["pending_orders"] == 0 and b_metrics["pending_orders"] == 0,
        "protected_paths_unchanged": protected_before == protected_after,
        "no_training_or_tuning": True,
        "baseline_admission_false": True,
        "production_allowed_false": True,
        "protocol_hash_bound": sha256(PROTOCOL)
        == "e33329041e529e4d9df078b274f432cca291942b855241bc58014b4138329e57",
        "monthly_stability_reported": len(monthly) >= 12,
        "regime_stability_reported": len(regimes) == 2,
        "pnl_concentration_reported": len(concentration_summary) == 2,
        "rank_metrics_311_labeled_days": rank_daily.date.nunique() == 311,
        "rank_metrics_both_methods": set(rank_daily.method) == {"A_ONLY", "A_PLUS_B"},
        "tail_10_rank_labels_unavailable_not_filled": int((~rank_coverage.rank_metrics_eligible).sum()) == 10,
        "signals_table_is_not_model_signal_artifact": "candidate_rank" not in signals.columns
        and "available_at" not in signals.columns,
        "strategy_dependency_hash_bound": freeze["strategy_dependency_sha256"]
        == sha256(STRATEGY_DEPENDENCY),
        "strategy_decision_impl_hash_bound": freeze["strategy_decision_impl_sha256"]
        == sha256(STRATEGY_DECISION_IMPL),
        "price_inventory_frozen_before_scoring": freeze["price_inventory"] == price_root_inventory(),
        "max_one_buy_intent_per_signal_day": a_metrics["max_buy_intents_per_signal_day"] <= 1
        and b_metrics["max_buy_intents_per_signal_day"] <= 1,
        "max_one_sell_intent_per_signal_day": a_metrics["max_sell_intents_per_signal_day"] <= 1
        and b_metrics["max_sell_intents_per_signal_day"] <= 1,
        "holdings_never_exceed_10": a_metrics["max_holding_count"] <= TARGET_HOLDINGS
        and b_metrics["max_holding_count"] <= TARGET_HOLDINGS,
        "no_duplicate_pending_symbol_action": a_metrics["duplicate_pending_symbol_action_count"] == 0
        and b_metrics["duplicate_pending_symbol_action_count"] == 0,
        "no_duplicate_signal_instrument_action_intent": a_metrics["duplicate_intent_key_count"] == 0
        and b_metrics["duplicate_intent_key_count"] == 0,
        "sell_opens_same_signal_day_buy_slot": a_metrics["sell_signal_days_without_same_day_buy_intent"] == 0
        and b_metrics["sell_signal_days_without_same_day_buy_intent"] == 0,
        "skipped_or_zero_quantity_actions_accounted": a_metrics["skipped_or_zero_quantity_actions"]
        == sum(row.get("status") != "EXECUTED" for row in a_actions)
        and b_metrics["skipped_or_zero_quantity_actions"]
        == sum(row.get("status") != "EXECUTED" for row in b_actions),
    }
    validator = {
        "schema_version": "modelb.b18.historical_pit_paired_replay.validator.v1",
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
    }
    write_json(OUT / "B18_VALIDATOR.json", validator)

    output_names = [
        "B18_RUN_FREEZE.json",
        "B18_VALIDATOR.json",
        "signals.csv",
        "daily_coverage.csv",
        "pit_available_at_audit.csv",
        "model_a_feature_parity_audit.csv",
        "missing_feature_keys.csv",
        "A_ONLY_actions.csv",
        "A_PLUS_B_actions.csv",
        "A_ONLY_daily_ledger.csv",
        "A_PLUS_B_daily_ledger.csv",
        "next_open_audit.csv",
        "stratum_metrics.csv",
        "paired_daily_metrics.csv",
        "paired_metrics.csv",
        "monthly_metrics.csv",
        "regime_metrics.csv",
        "pnl_concentration.csv",
        "rank_metrics_daily.csv",
        "rank_metrics_monthly.csv",
        "rank_metrics_coverage.csv",
    ]
    manifest = {
        "schema_version": "modelb.b18.historical_pit_paired_replay.manifest.v1",
        "run_id": OUT.name,
        "created_at": utc_now(),
        "status": "COMPLETED_HISTORICAL_NONFIT_LAYERED_EVIDENCE_AWAITING_REVIEW",
        "historical_nonfit_replay": True,
        "untouched_claim": False,
        "formal_prospective_claim": False,
        "evidence_strata": [
            {
                "name": name,
                "start": start,
                "end": end,
                "signal_days": int(signals.loc[signals.evidence_stratum.eq(name), "date"].nunique()),
                "untouched": False,
            }
            for name, start, end in EVIDENCE_STRATA
        ],
        "fit_window_excluded": ["2023-01-10", "2024-12-17"],
        "embargo_window_excluded": ["2024-12-18", "2024-12-31"],
        "signals": score_audit["metadata"],
        "signals_artifact_type": "paired_experiment_table_non_modelsignal",
        "signals_rank_semantics": (
            "eligible_candidate_rank is experiment-only; full_qlib_rank is the original frozen Model A rank"
        ),
        "reconstructed_availability": {
            "field": "reconstructed_available_at",
            "policy": freeze["availability_policy"],
            "source_native_visibility_claim": False,
        },
        "candidate_policy": freeze["candidate_policy"],
        "strategy_rule": freeze["strategy_rule"],
        "execution": {
            "mode": "next_open",
            "fallback": False,
            "fee_rate": FEE_RATE,
            "sell_tax_rate": SELL_TAX_RATE,
            "lot_size": LOT_SIZE,
            "target_holdings": TARGET_HOLDINGS,
            "initial_equity": INITIAL_EQUITY,
        },
        "control": a_metrics,
        "treatment": b_metrics,
        "relative": relative_metrics,
        "stratum_metrics": strata,
        "monthly_metrics": monthly,
        "regime_metrics": regimes,
        "pnl_concentration_summary": concentration_summary,
        "rank_metrics_summary": rank_daily.groupby("method")[
            ["rank_ic", "ndcg_at_10", "ndcg_at_30", "ndcg_at_50"]
        ].mean().reset_index().to_dict("records"),
        "rank_metric_days": int(rank_daily.date.nunique()),
        "rank_metric_tail_unavailable_days": int((~rank_coverage.rank_metrics_eligible).sum()),
        "upstream": {
            "b2_manifest": fingerprint(B2 / "B2_FEATURE_ARTIFACT_MANIFEST.json"),
            "b2_review": fingerprint(B2 / "B2_INDEPENDENT_REVIEW.json"),
            "b2_features": fingerprint(FEATURES),
            "b2_pit_audit": fingerprint(PIT_AUDIT),
            "b3_manifest": fingerprint(B3 / "B3_MODEL_A_OOS_MANIFEST.json"),
            "b3_model_a": fingerprint(MODEL_A),
            "b9_freeze": fingerprint(B9 / "B9_CANONICAL_RETRAIN_RUN_FREEZE.json"),
            "b9_review": fingerprint(B9 / "B9_CANONICAL_RETRAIN_INDEPENDENT_REVIEW.json"),
            "b9_model": fingerprint(MODEL_B),
            "canonical_labels_outcome_only": fingerprint(LABELS),
            "price_inventory_sha256": prices.inventory_hash(),
            "full_price_root_inventory": price_root_inventory(),
            "b18_protocol": fingerprint(PROTOCOL),
            "strategy_dependency": fingerprint(STRATEGY_DEPENDENCY),
            "strategy_decision_impl": fingerprint(STRATEGY_DECISION_IMPL),
        },
        "artifacts": {name: fingerprint(OUT / name) for name in output_names},
        "protected_before": protected_before,
        "protected_after": protected_after,
        "protected_unchanged": protected_before == protected_after,
        "training_performed": False,
        "tuning_performed": False,
        "result_based_selection_allowed": False,
        "baseline_admission": False,
        "production_allowed": False,
        "no_provider_latest_default_db_broker_order_write": True,
        "review_required": True,
    }
    write_json(OUT / "B18_MANIFEST.json", manifest)
    report = f"""# B18 历史 PIT 配对回放执行报告

## 1. 范围

本次使用冻结 B9 LightGBM Ranker 做隔离历史评分和配对回放。没有训练、调参、按结果换模型或规则，也没有修改 production/latest/default、provider、数据库、broker 或订单链路。

## 2. 日期证据分层

- 2025 validation：{manifest['evidence_strata'][0]['signal_days']} 日。未进入 B9 拟合，但此前已用于 validation，不是 untouched。
- 2026 预登记 test：{manifest['evidence_strata'][1]['signal_days']} 日。未进入 B9 拟合，但此前已评估，不再称 untouched。
- post-test 历史诊断：{manifest['evidence_strata'][2]['signal_days']} 日。未进入拟合，但在 B9 训练时已经是历史，不是 prospective/untouched。
- 合计：{score_audit['metadata']['dates']} 个逐日 exact-50 配对信号日。

## 3. 候选与 PIT

每天从完整 Model A 截面开始，先显式排除 TW7769 和 TW6919，再排除 78 维 raw feature 不完整行，随后按原始 Model A rank 和 instrument 排序取前 50，并保存原始 rank 为 full_qlib_rank。{score_audit['metadata']['dates_requiring_replenishment_beyond_original_rank_50']} 日需要从原始 rank 50 以外递补；所有日期最终均为精确 50/50。该集合是 Model-B 可评分 eligibility universe，A-only 控制轨也使用同一集合，不等同于未经筛选的原始 Model A Top50。选中行的正交 source future flag 为 0，重建 available_at 晚于 signal_asof 的行数为 0；`reconstructed_available_at` 只是 B2 延迟规则假设，不是 source-native 历史落盘证明。`signals.csv` 是配对实验表，不是 ModelSignalArtifact。

## 4. 配对回放

Control=A-only，Treatment=A+B；两者使用相同候选、`top50_exit_one_worst_sell`、next_open、手续费 {FEE_RATE}、卖出税 {SELL_TAX_RATE}、lot={LOT_SIZE}、目标持仓 {TARGET_HOLDINGS} 和初始资金 {INITIAL_EQUITY:.0f}。正式 dependency 冻结 `max_buy_count=1`、`max_sell_count=1`，两轨均逐日验证。next_open 缺失时阻断且无 fallback；本次未发生缺失或未结算订单。

- A-only net return：{a_metrics['net_return']:.8%}；final equity：{a_metrics['final_equity']:.2f}；max drawdown：{a_metrics['max_drawdown']:.8%}。
- A+B net return：{b_metrics['net_return']:.8%}；final equity：{b_metrics['final_equity']:.2f}；max drawdown：{b_metrics['max_drawdown']:.8%}。
- B-A net return delta：{relative_metrics['net_return_diff_b_minus_a']:.8%}；fee/tax delta：{relative_metrics['fee_tax_diff_b_minus_a']:.2f}。

## 5. 结论边界

Validator：`{validator['verdict']}`。这批结果解决了“无需逐日等待即可取得 120 日以上历史非拟合证据”的开发问题，但不能改写为 untouched prospective 证据。Model B 仍不纳入 baseline，必须等待独立审查并结合少量真实链路验证后再做 admission 决策。
"""
    (OUT / "B18_EXECUTION_REPORT_CN.md").write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "signal_days": score_audit["metadata"]["dates"],
                "control_net_return": a_metrics["net_return"],
                "treatment_net_return": b_metrics["net_return"],
                "delta": relative_metrics["net_return_diff_b_minus_a"],
                "validator": validator["verdict"],
                "out": relative(OUT),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if validator["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
