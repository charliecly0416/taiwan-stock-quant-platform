#!/usr/bin/env python3
"""Independently recompute and validate the frozen sealed confirmation output."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_comparative_evaluation_20260916"
PROTOCOL = RUN / "B19R2R_COMPARATIVE_FREEZE.json"
ADAPTER = RUN / "B19R2R_COMPARATIVE_FREEZE_AMENDMENT_01.json"
ERRATA = RUN / "B19R2R_CONFIRMATION_ENGINEERING_SEMANTIC_ERRATA.json"
IMPLEMENTATION = RUN / "B19R2R_CONFIRMATION_IMPLEMENTATION_FREEZE.json"
AUTH = RUN / "B19R2R_CONFIRMATION_EXECUTION_AUTHORIZATION.json"
VALIDATION_AUTH = RUN / "B19R2R_CONFIRMATION_OUTPUT_VALIDATION_AUTHORIZATION.json"
OUTPUT = RUN / "confirmation_output_v1"
EVALUATOR = ROOT / "scripts/run_modelb_b19r2r_sealed_confirmation.py"
VALIDATOR = Path(__file__)
R2R = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916"
FEATURES = R2R / "FEATURE_ARTIFACT_78_RAW.parquet"
KEYS = R2R / "EXACT50_KEYSETS.csv"
MODEL_A = R2R / "MODEL_A_FULL_CROSS_SECTION.parquet"
OUTCOME_MANIFEST = R2R / "outcome_materialization_v1/OUTCOME_MATERIALIZATION_MANIFEST.json"
LABELS = R2R / "outcome_materialization_v1/sealed_confirmation/CONFIRMATION_OUTCOMES.parquet"
GRID = R2R / "outcome_materialization_v1/sealed_confirmation/CONFIRMATION_EXECUTION_GRID.parquet"
SCHEMA = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json"
TRAINING_MANIFEST = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_training_20260916/training_output_v1/TRAINING_MANIFEST.json"
MODEL_B = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_training_20260916/training_output_v1/MODEL_B_B19R2R_LGBM_RANKER.pkl"
KEY = ["date", "instrument"]
REL = "relevance_10d_top_heavy_canonical"
CONT = "future_excess_return_10d_canonical"
INITIAL = 1_000_000.0
FEE = 0.001425
TAX = 0.003
LOT = 10
TARGET = 10
MODEL_A_SCORE_PARITY_RTOL = 0.0
MODEL_A_SCORE_PARITY_ATOL = 1e-15
RECONCILIATION_ABS_TOLERANCE = 1e-6
BOOTSTRAP_SEED = 20260916
BOOTSTRAP_REPLICATIONS = 10000
BOOTSTRAP_BLOCK_LENGTH = 10
BOOTSTRAP_BLOCKS = 3
CONFIRMATION_DATES = (
    "2026-07-22", "2026-07-23", "2026-07-24", "2026-07-27", "2026-07-28",
    "2026-07-29", "2026-07-30", "2026-07-31", "2026-08-03", "2026-08-04",
    "2026-08-05", "2026-08-06", "2026-08-07", "2026-08-10", "2026-08-11",
    "2026-08-12", "2026-08-13", "2026-08-14", "2026-08-17", "2026-08-18",
    "2026-08-19", "2026-08-20", "2026-08-21", "2026-08-24", "2026-08-25",
    "2026-08-26", "2026-08-27", "2026-08-28", "2026-08-31", "2026-09-01",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def normalize(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["date"] = frame.date.astype(str).str[:10]
    frame["instrument"] = frame.instrument.astype(str).str.upper()
    return frame


def validate_authorization(*, require_auth: bool) -> dict[str, Any]:
    for path in (PROTOCOL, ADAPTER, ERRATA, IMPLEMENTATION, OUTCOME_MANIFEST):
        if not path.is_file():
            raise RuntimeError(f"missing frozen contract: {rel(path)}")
    implementation = json.loads(IMPLEMENTATION.read_text(encoding="utf-8"))
    if implementation.get("status") != "FROZEN_BEFORE_SEALED_CONFIRMATION_ACCESS":
        raise RuntimeError("implementation freeze is not closed")
    for name, path in {"evaluator": EVALUATOR, "validator": VALIDATOR}.items():
        if implementation["implementation_bindings"][name]["sha256"] != sha256(path):
            raise RuntimeError(f"implementation hash mismatch: {name}")
    outcome_manifest = json.loads(OUTCOME_MANIFEST.read_text(encoding="utf-8"))
    for item in implementation["source_bindings"].values():
        path = ROOT / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"]:
            raise RuntimeError(f"source presence/size mismatch: {item['path']}")
        if item.get("sealed_value_source") is True:
            manifest_item = outcome_manifest["artifacts"][item["outcome_manifest_artifact"]]
            if (
                manifest_item["path"] != item["path"]
                or manifest_item["sha256"] != item["sha256"]
                or manifest_item["bytes"] != item["bytes"]
                or manifest_item["row_count"] != item["row_count"]
                or manifest_item["date_count"] != item["date_count"]
                or (path.stat().st_mode & 0o777) != 0o600
            ):
                raise RuntimeError(f"sealed metadata binding mismatch: {item['path']}")
        elif sha256(path) != item["sha256"]:
            raise RuntimeError(f"nonsealed source hash mismatch: {item['path']}")
    if require_auth:
        if not AUTH.is_file():
            raise RuntimeError("independent execution authorization missing")
        auth = json.loads(AUTH.read_text(encoding="utf-8"))
        if (
            auth.get("authorized") is not True
            or auth.get("attempts_authorized") != 1
            or auth.get("implementation_freeze_sha256") != sha256(IMPLEMENTATION)
            or auth.get("evaluator_sha256") != sha256(EVALUATOR)
            or auth.get("validator_sha256") != sha256(VALIDATOR)
            or auth.get("authorization_scope") != "ONE_WRITE_ONCE_SEALED_CONFIRMATION_EVALUATION_ATTEMPT"
        ):
            raise RuntimeError("execution authorization mismatch")
    return implementation


def verify_sealed_hashes_after_attempt_marker(implementation: dict[str, Any]) -> None:
    if not (OUTPUT / "ATTEMPT_STARTED.json").is_file():
        raise RuntimeError("sealed source verification requires an existing attempt marker")
    sealed = [item for item in implementation["source_bindings"].values() if item.get("sealed_value_source") is True]
    if len(sealed) != 2:
        raise RuntimeError("exactly two sealed confirmation sources are required")
    for item in sealed:
        path = ROOT / item["path"]
        if sha256(path) != item["sha256"]:
            raise RuntimeError(f"sealed source hash mismatch: {item['path']}")


def load_and_score_confirmation() -> tuple[pd.DataFrame, pd.DataFrame, list[str], pd.DataFrame, dict[str, Any]]:
    features = json.loads(SCHEMA.read_text(encoding="utf-8"))["feature_order"]
    feature_source = normalize(pd.read_parquet(FEATURES, columns=KEY + features + ["feature_raw_complete_78"]))
    if (
        len(feature_source) != 12000
        or feature_source.date.nunique() != 80
        or feature_source.duplicated(KEY).any()
        or feature_source.groupby("date").size().ne(150).any()
    ):
        raise RuntimeError("frozen 78F full-source shape failed")
    confirmation_features = feature_source[feature_source.date.isin(CONFIRMATION_DATES)].copy()
    if (
        len(confirmation_features) != 4500
        or confirmation_features.date.nunique() != 30
        or confirmation_features.groupby("date").size().ne(150).any()
    ):
        raise RuntimeError("confirmation 78F filtered shape failed")
    confirmation_outcomes = normalize(pd.read_parquet(
        LABELS, columns=KEY + ["role", CONT, REL, "label_complete"],
    ))
    if (
        len(confirmation_outcomes) != 4500
        or confirmation_outcomes.date.nunique() != 30
        or confirmation_outcomes.duplicated(KEY).any()
        or confirmation_outcomes.groupby("date").size().ne(150).any()
        or set(confirmation_outcomes.date) != set(CONFIRMATION_DATES)
        or set(confirmation_outcomes.role) != {"SEALED_CONFIRMATION"}
    ):
        raise RuntimeError("confirmation outcome source shape failed")
    key_source = normalize(pd.read_csv(KEYS))
    if (
        len(key_source) != 4000
        or key_source.date.nunique() != 80
        or key_source.duplicated(KEY).any()
        or key_source.groupby("date").size().ne(50).any()
    ):
        raise RuntimeError("frozen Exact-50 full-source shape failed")
    confirmation_keys = key_source[key_source.date.isin(CONFIRMATION_DATES)].copy()
    confirmation_keys = confirmation_keys.rename(columns={
        "model_a_raw_score": "keyset_model_a_raw_score",
        "full_qlib_rank": "keyset_full_qlib_rank",
    })
    if (
        len(confirmation_keys) != 1500
        or confirmation_keys.duplicated(KEY).any()
        or confirmation_keys.groupby("date").size().ne(50).any()
        or not np.isfinite(
            confirmation_keys[["eligible_candidate_rank", "keyset_model_a_raw_score", "keyset_full_qlib_rank"]].to_numpy(float)
        ).all()
        or confirmation_keys.groupby("date").eligible_candidate_rank.nunique().ne(50).any()
        or not confirmation_keys.eligible_candidate_rank.between(1, 50).all()
    ):
        raise RuntimeError("confirmation Exact-50 keyset contract failed")
    model_a_source = normalize(pd.read_parquet(MODEL_A, columns=KEY + ["model_a_raw_score", "full_qlib_rank"]))
    if (
        len(model_a_source) != 12000
        or model_a_source.date.nunique() != 80
        or model_a_source.duplicated(KEY).any()
        or model_a_source.groupby("date").size().ne(150).any()
        or not np.isfinite(model_a_source[["model_a_raw_score", "full_qlib_rank"]].to_numpy(float)).all()
    ):
        raise RuntimeError("frozen Model A full-rank coverage failed")
    model_a = model_a_source[model_a_source.date.isin(CONFIRMATION_DATES)].copy()
    if (
        len(model_a) != 4500
        or model_a.date.nunique() != 30
        or model_a.groupby("date").size().ne(150).any()
    ):
        raise RuntimeError("confirmation Model A filtered shape failed")
    confirmation = (
        confirmation_keys.merge(confirmation_features, on=KEY, validate="one_to_one")
        .merge(confirmation_outcomes[KEY + [CONT, REL, "label_complete"]], on=KEY, validate="one_to_one")
        .merge(model_a, on=KEY, validate="one_to_one")
        .sort_values(KEY, kind="mergesort").reset_index(drop=True)
    )
    if len(confirmation) != 1500 or confirmation.groupby("date").size().ne(50).any():
        raise RuntimeError("confirmation keys are not 30x50")
    if not confirmation.feature_raw_complete_78.all() or not confirmation.label_complete.all():
        raise RuntimeError("confirmation completeness failed")
    keyset_score = confirmation.keyset_model_a_raw_score.to_numpy(float)
    canonical_score = confirmation.model_a_raw_score.to_numpy(float)
    score_close = np.isclose(
        keyset_score,
        canonical_score,
        rtol=MODEL_A_SCORE_PARITY_RTOL,
        atol=MODEL_A_SCORE_PARITY_ATOL,
    )
    score_max_abs_diff = float(np.max(np.abs(keyset_score - canonical_score)))
    keyset_rank = confirmation.keyset_full_qlib_rank.to_numpy(float)
    canonical_rank = confirmation.full_qlib_rank.to_numpy(float)
    if not score_close.all():
        raise RuntimeError("Exact-50 keyset and canonical Model A score parity failed")
    if not np.array_equal(keyset_rank, canonical_rank):
        raise RuntimeError("Exact-50 keyset and canonical Model A full-rank parity failed")
    feature_score = confirmation.qlib_score_raw.to_numpy(float)
    if not np.isfinite(canonical_score).all() or not np.isfinite(feature_score).all():
        raise RuntimeError("nonfinite canonical Model A score")
    if not np.array_equal(canonical_score, feature_score):
        raise RuntimeError("Model A score parity failed")
    if not np.isfinite(confirmation[features + [CONT, REL]].to_numpy(float)).all():
        raise RuntimeError("nonfinite confirmation feature or label")
    selected = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
    if (
        selected.get("selected_candidate_id") != 14
        or selected.get("final_refit_end") != "2026-07-06"
        or selected.get("feature_count") != 78
        or selected.get("artifacts", {}).get("model", {}).get("sha256")
        != "8d31069593cc8a1cc7c6fa7ac4cf50a9e897a76af0ab446ddbc26551fc5e5421"
    ):
        raise RuntimeError("final model lineage drifted")
    model = joblib.load(MODEL_B)
    if list(model.booster_.feature_name()) != features or int(model.booster_.num_trees()) != 120:
        raise RuntimeError("final model structure or feature order drifted")
    scored = confirmation[KEY].copy()
    scored["model_b_final_raw_score"] = model.predict(confirmation[features])
    if not np.isfinite(scored.model_b_final_raw_score).all():
        raise RuntimeError("nonfinite final Model B prediction")
    signals = confirmation.merge(scored, on=KEY, validate="one_to_one")
    signals["a_only_buy_score"] = signals.model_a_raw_score
    signals["a_plus_b_buy_score"] = signals.model_b_final_raw_score
    if not np.isfinite(signals[["a_only_buy_score", "a_plus_b_buy_score", "full_qlib_rank"]].to_numpy(float)).all():
        raise RuntimeError("nonfinite canonical signal score or rank")
    for score, rank in (("a_only_buy_score", "a_only_score_rank"), ("a_plus_b_buy_score", "a_plus_b_score_rank")):
        signals[rank] = signals.groupby("date", sort=True)[score].rank(method="first", ascending=False).astype(int)
        # Replace pandas input-order ties with the frozen instrument tie rule.
        signals[rank] = signals.sort_values(["date", score, "instrument"], ascending=[True, False, True], kind="mergesort").groupby("date").cumcount().add(1).sort_index()
    return (
        signals.sort_values(KEY, kind="mergesort"),
        scored.sort_values(KEY, kind="mergesort"),
        features,
        model_a[KEY + ["full_qlib_rank"]].sort_values(KEY, kind="mergesort"),
        {
            "rows": len(confirmation),
            "canonical_score_source": rel(MODEL_A),
            "keyset_score_audit_source": rel(KEYS),
            "score_rtol": MODEL_A_SCORE_PARITY_RTOL,
            "score_atol": MODEL_A_SCORE_PARITY_ATOL,
            "score_bitwise_mismatch_count": int(np.sum(keyset_score != canonical_score)),
            "score_tolerance_failure_count": int((~score_close).sum()),
            "score_max_abs_diff": score_max_abs_diff,
            "full_qlib_rank_exact_match": True,
            "full_qlib_rank_semantics": "canonical frozen Model A full-cross-section rank; keyset copy must match exactly",
            "eligible_candidate_rank_semantics": "Exact-50 membership/order audit only; it does not replace full_qlib_rank",
            "canonical_model_a_feature_score_max_abs_diff": float(np.max(np.abs(canonical_score - feature_score))),
        },
    )


def rank_metrics(signals: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for day, group in signals.groupby("date", sort=True):
        relevance = group[REL].to_numpy(float)
        continuous = group[CONT].to_numpy(float)
        for method, field in (("A_ONLY", "a_only_buy_score"), ("A_PLUS_B", "a_plus_b_buy_score")):
            score = group[field].to_numpy(float)
            if not np.isfinite(relevance).all() or not np.isfinite(continuous).all() or not np.isfinite(score).all():
                raise RuntimeError(f"nonfinite rank metric input: {day} {method}")
            rho = spearmanr(score, continuous).statistic
            if not np.isfinite(rho):
                raise RuntimeError(f"nonfinite or constant daily RankIC: {day} {method}")
            ndcg = float(ndcg_score(relevance[None, :], score[None, :], k=10))
            if not np.isfinite(ndcg):
                raise RuntimeError(f"nonfinite NDCG@10 output: {day} {method}")
            rows.append({
                "date": day, "scope": "sealed_confirmation_30_day", "method": method,
                "rank_ic_continuous": float(rho),
                "ndcg_at_10": ndcg,
            })
    return pd.DataFrame(rows)


def summarize_rank_metrics(rank_daily: pd.DataFrame) -> pd.DataFrame:
    summary = (
        rank_daily.groupby("method", as_index=False)
        .agg(
            date_count=("date", "nunique"),
            mean_rank_ic_continuous=("rank_ic_continuous", "mean"),
            mean_ndcg_at_10=("ndcg_at_10", "mean"),
        )
    )
    summary.insert(0, "scope", "sealed_confirmation_30_day")
    if len(summary) != 2 or summary.duplicated(["scope", "method"]).any():
        raise RuntimeError("rank metric summary scope/method identity failed")
    return summary


def replay(
    signals: pd.DataFrame,
    grid: pd.DataFrame,
    full_ranks: pd.DataFrame,
    score_field: str,
    method: str,
    scope: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    signal_days = sorted(signals.date.unique().tolist())
    grid_lookup = grid.set_index(KEY)
    holdings: dict[str, int] = {}
    basis: dict[str, float] = {}
    cash = INITIAL
    pending: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    nav: list[dict[str, Any]] = []
    price_audit: list[dict[str, Any]] = []
    full_rank_lookup = full_ranks.set_index(KEY).full_qlib_rank

    def execute_and_mark(signal_day: str) -> None:
        nonlocal cash, pending
        emitted_count = len(pending)
        executed_count = 0
        day_grid = grid[grid.date.eq(signal_day)]
        execution_dates = set(day_grid.next_trade_date.astype(str).str[:10])
        if len(day_grid) != 150 or len(execution_dates) != 1:
            raise RuntimeError("execution grid does not define one complete next trade date")
        execution_date = next(iter(execution_dates))
        for order in pending:
            row = grid_lookup.loc[(signal_day, order["instrument"])]
            if str(row.next_trade_date)[:10] != execution_date:
                raise RuntimeError("action execution date does not match the frozen daily grid")
            price = float(row.next_open)
            if not math.isfinite(price) or price <= 0:
                raise RuntimeError("missing next_open; no fallback")
            symbol = order["instrument"]
            if order["action"] == "sell":
                quantity = holdings.pop(symbol)
                old_basis = basis.pop(symbol)
                commission = quantity * price * FEE
                tax = quantity * price * TAX
                cash += quantity * price - commission - tax
                net_pnl = quantity * price - old_basis - commission - tax
            else:
                allocation = cash / max(1, TARGET - len(holdings))
                quantity = int(allocation // (price * (1 + FEE) * LOT)) * LOT
                commission = quantity * price * FEE
                tax = 0.0
                if quantity <= 0 or quantity * price + commission > cash:
                    raise RuntimeError("positive buy intent did not execute")
                cash -= quantity * price + commission
                holdings[symbol] = quantity
                basis[symbol] = quantity * price
                net_pnl = -commission
            executed_count += 1
            actions.append({**order, "scope": scope, "method": method, "execution_date": execution_date, "execution_price": price, "quantity": quantity, "commission": commission, "sell_tax": tax, "net_pnl": net_pnl, "status": "EXECUTED"})
            price_audit.append({"scope": scope, "method": method, "signal_date": signal_day, "instrument": symbol, "action": order["action"], "execution_date": execution_date, "next_open": price, "fallback_used": False})
        market_value = 0.0
        for symbol, quantity in holdings.items():
            row = grid_lookup.loc[(signal_day, symbol)]
            close = float(row.next_close)
            if not math.isfinite(close) or close <= 0 or str(row.next_trade_date)[:10] != execution_date:
                raise RuntimeError("missing exact next_close terminal mark")
            market_value += quantity * close
        nav.append({"scope": scope, "method": method, "signal_date": signal_day, "date": execution_date, "cash": cash, "market_value": market_value, "equity": cash + market_value, "holding_count": len(holdings), "emitted_action_count": emitted_count, "executed_action_count": executed_count, "pending_count": emitted_count - executed_count, "fallback_count": 0})
        pending = []

    for index, day in enumerate(signal_days):
        if index:
            # Every signal day gets an exact next-close NAV mark, including no-action days.
            execute_and_mark(signal_days[index - 1])
        group = signals[signals.date.eq(day)].copy()
        candidates = set(group.instrument)
        outside = [symbol for symbol in holdings if symbol not in candidates]
        if outside:
            ranks: dict[str, float] = {}
            for symbol in outside:
                try:
                    ranks[symbol] = float(full_rank_lookup.loc[(day, symbol)])
                except KeyError as error:
                    raise RuntimeError(f"missing frozen full rank: {day} {symbol}") from error
            worst = max(outside, key=lambda symbol: (ranks[symbol], symbol))
            pending.append({"signal_date": day, "instrument": worst, "action": "sell", "reason": "top50_exit_one_worst_sell"})
        projected = len(holdings) - sum(order["action"] == "sell" for order in pending)
        if projected < TARGET:
            ranked = group.sort_values([score_field, "instrument"], ascending=[False, True], kind="mergesort")
            for row in ranked.itertuples(index=False):
                if row.instrument not in holdings:
                    pending.append({"signal_date": day, "instrument": row.instrument, "action": "buy", "reason": "top50_buy_score_rank"})
                    break
        if sum(order["action"] == "buy" for order in pending) > 1 or sum(order["action"] == "sell" for order in pending) > 1:
            raise RuntimeError("daily action limit exceeded")
    execute_and_mark(signal_days[-1])
    if len(nav) != len(signal_days):
        raise RuntimeError("daily ledger is incomplete")
    nav_frame = pd.DataFrame(nav)
    nav_frame["daily_return"] = nav_frame.equity.pct_change().fillna(nav_frame.equity.iloc[0] / INITIAL - 1)
    equity_values = nav_frame.equity.to_numpy(float)
    peaks = np.maximum.accumulate(np.r_[INITIAL, equity_values])[1:]
    nav_frame["drawdown"] = equity_values / peaks - 1.0
    contribution: list[dict[str, Any]] = []
    action_frame = pd.DataFrame(actions)
    for symbol in sorted(set(action_frame.instrument).union(holdings)):
        action_pnl = float(action_frame.loc[action_frame.instrument.eq(symbol), "net_pnl"].sum())
        unrealized = 0.0
        if symbol in holdings:
            last_signal = signal_days[-1]
            terminal_close = float(grid_lookup.loc[(last_signal, symbol)].next_close)
            unrealized = holdings[symbol] * terminal_close - basis[symbol]
        contribution.append({"scope": scope, "method": method, "instrument": symbol, "action_net_pnl": action_pnl, "terminal_unrealized_pnl": unrealized, "total_contribution": action_pnl + unrealized})
    contribution_frame = pd.DataFrame(contribution)
    if not math.isclose(
        float(contribution_frame.total_contribution.sum()),
        float(nav_frame.equity.iloc[-1] - INITIAL),
        rel_tol=0.0,
        abs_tol=RECONCILIATION_ABS_TOLERANCE,
    ):
        raise RuntimeError("PnL contribution does not reconcile")
    return action_frame, nav_frame, pd.DataFrame(price_audit), contribution_frame


def summarize(scope: str, method: str, actions: pd.DataFrame, nav: pd.DataFrame, contribution: pd.DataFrame) -> dict[str, Any]:
    buys = actions[actions.action.eq("buy")]
    sells = actions[actions.action.eq("sell")]
    notionals = (actions.quantity * actions.execution_price).sum()
    abs_contribution = contribution.total_contribution.abs()
    contribution_denominator = float(abs_contribution.sum())
    shares = abs_contribution / contribution_denominator if contribution_denominator > 0 else pd.Series(dtype=float)
    return {
        "scope": scope,
        "method": method,
        "final_equity": float(nav.equity.iloc[-1]),
        "net_return": float(nav.equity.iloc[-1] / INITIAL - 1),
        "max_drawdown": float(nav.drawdown.min()),
        "turnover": float(notionals / INITIAL),
        "buy_count": int(len(buys)),
        "sell_count": int(len(sells)),
        "action_count": int(len(actions)),
        "commission": float(actions.commission.sum()),
        "sell_tax": float(actions.sell_tax.sum()),
        "fee_tax": float(actions.commission.sum() + actions.sell_tax.sum()),
        "contribution_denominator": contribution_denominator,
        "contribution_denominator_valid": bool(math.isfinite(contribution_denominator) and contribution_denominator > 0),
        "top1_abs_contribution_share": float(shares.nlargest(1).sum()) if len(shares) else None,
        "top5_abs_contribution_share": float(shares.nlargest(5).sum()) if len(shares) else None,
        "abs_contribution_hhi": float((shares**2).sum()) if len(shares) else None,
        "fallback_count": 0,
        "pending_count": int(nav.pending_count.sum()),
        "emitted_action_count": int(nav.emitted_action_count.sum()),
        "executed_action_count": int(nav.executed_action_count.sum()),
        "all_actions_executed": bool(
            len(actions) == int(nav.emitted_action_count.sum())
            and actions.status.eq("EXECUTED").all()
            and actions.quantity.gt(0).all()
        ),
        "reconciliation_delta": float(contribution.total_contribution.sum() - (nav.equity.iloc[-1] - INITIAL)),
    }


def finite_ratio(numerator: float, denominator: float) -> tuple[float | None, str | None]:
    if not math.isfinite(numerator) or not math.isfinite(denominator):
        return None, "NONFINITE_RATIO_INPUT"
    if denominator == 0:
        return None, "ZERO_DENOMINATOR_FAIL_GATE"
    return float(numerator / denominator), None


def compare(actual: Any, operator: str, threshold: Any) -> bool:
    if isinstance(actual, (bool, np.bool_)):
        return bool(actual) is bool(threshold)
    if operator == "==" and (isinstance(actual, str) or isinstance(threshold, str)):
        return actual == threshold
    if actual is None or not math.isfinite(float(actual)):
        return False
    if operator == ">":
        return float(actual) > float(threshold)
    if operator == ">=":
        return float(actual) >= float(threshold)
    if operator == "<=":
        return float(actual) <= float(threshold)
    if operator == "==":
        return actual == threshold
    raise RuntimeError(f"unsupported gate operator: {operator}")


def serialized_value_matches(actual: Any, expected: Any) -> bool:
    if pd.isna(actual) and pd.isna(expected):
        return True
    if isinstance(expected, (bool, np.bool_)):
        return str(actual).strip().lower() == str(bool(expected)).lower()
    try:
        actual_float = float(actual)
        expected_float = float(expected)
    except (TypeError, ValueError):
        return str(actual) == str(expected)
    return math.isclose(actual_float, expected_float, rel_tol=0.0, abs_tol=1e-12)


def bootstrap_active_return(active: np.ndarray) -> tuple[np.ndarray, float]:
    if len(active) != 30 or not np.isfinite(active).all():
        raise RuntimeError("bootstrap requires exactly 30 finite active returns")
    rng = np.random.Generator(np.random.PCG64(BOOTSTRAP_SEED))
    starts = rng.integers(0, 21, size=(BOOTSTRAP_REPLICATIONS, BOOTSTRAP_BLOCKS))
    offsets = np.arange(BOOTSTRAP_BLOCK_LENGTH)
    indices = (starts[:, :, None] + offsets).reshape(BOOTSTRAP_REPLICATIONS, 30)
    means = active[indices].mean(axis=1)
    lower = float(np.quantile(means, 0.05, method="linear"))
    if len(means) != BOOTSTRAP_REPLICATIONS or not np.isfinite(means).all() or not math.isfinite(lower):
        raise RuntimeError("bootstrap output is incomplete or nonfinite")
    return means, lower


def build_gate_table(
    protocol: dict[str, Any],
    paired: pd.DataFrame,
    nav_by_method: dict[str, pd.DataFrame],
    rank_summary: pd.DataFrame,
    signals: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frozen = protocol["preregistered_numeric_quality_gates"]
    tracks = paired.set_index("method")
    a, b = tracks.loc["A_ONLY"], tracks.loc["A_PLUS_B"]
    paired_daily = nav_by_method["A_ONLY"][["signal_date", "date", "daily_return"]].rename(
        columns={"date": "execution_date", "daily_return": "a_return"}
    ).merge(
        nav_by_method["A_PLUS_B"][["signal_date", "date", "daily_return"]].rename(
            columns={"date": "execution_date", "daily_return": "b_return"}
        ),
        on=["signal_date", "execution_date"], validate="one_to_one",
    )
    regime = signals.groupby("date", as_index=False).agg(
        twii_ret20=("TWII_ret20", "first"), regime_values=("TWII_ret20", "nunique")
    )
    if len(paired_daily) != 30 or regime.regime_values.ne(1).any() or regime.twii_ret20.isna().any():
        raise RuntimeError("paired daily return or TWII_ret20 date-level contract failed")
    paired_daily = paired_daily.merge(
        regime[["date", "twii_ret20"]], left_on="signal_date", right_on="date", validate="one_to_one"
    )
    paired_daily["active_return_b_minus_a"] = paired_daily.b_return - paired_daily.a_return
    paired_daily["month"] = paired_daily.signal_date.str[:7]
    bootstrap_means, bootstrap_lower = bootstrap_active_return(
        paired_daily.active_return_b_minus_a.to_numpy(float)
    )
    monthly = paired_daily.groupby("month").agg(
        a_return=("a_return", lambda x: float(np.prod(1.0 + x) - 1.0)),
        b_return=("b_return", lambda x: float(np.prod(1.0 + x) - 1.0)),
    ).reset_index()
    monthly_fraction = float((monthly.b_return > monthly.a_return).mean()) if len(monthly) else None
    negative = paired_daily[paired_daily.twii_ret20 < 0]
    negative_delta = None if negative.empty else float(
        np.prod(1.0 + negative.b_return) - np.prod(1.0 + negative.a_return)
    )
    negative_reason = "EMPTY_NEGATIVE_TWII20_REGIME_FAIL_GATE" if negative.empty else None
    rank_means = rank_summary.set_index("method")
    engineering_violations = int(
        sum(
            not math.isfinite(float(row.reconciliation_delta))
            or abs(float(row.reconciliation_delta)) > RECONCILIATION_ABS_TOLERANCE
            for _, row in tracks.iterrows()
        )
    )
    measured: dict[str, tuple[Any, str | None]] = {
        "confirmation_after_cost_return_delta_b_minus_a": (float(b.net_return - a.net_return), None),
        "confirmation_paired_moving_block_bootstrap_95pct_lower_bound": (bootstrap_lower, None),
        "max_drawdown_noninferiority_b_minus_a": (float(b.max_drawdown - a.max_drawdown), None),
        "top1_abs_contribution_share": (b.top1_abs_contribution_share, None if bool(b.contribution_denominator_valid) else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "top1_abs_contribution_share_vs_a_delta": (b.top1_abs_contribution_share - a.top1_abs_contribution_share, None if bool(a.contribution_denominator_valid) and bool(b.contribution_denominator_valid) else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "top5_abs_contribution_share": (b.top5_abs_contribution_share, None if bool(b.contribution_denominator_valid) else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "top5_abs_contribution_share_vs_a_delta": (b.top5_abs_contribution_share - a.top5_abs_contribution_share, None if bool(a.contribution_denominator_valid) and bool(b.contribution_denominator_valid) else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "abs_contribution_hhi": (b.abs_contribution_hhi, None if bool(b.contribution_denominator_valid) else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "abs_contribution_hhi_vs_a_delta": (b.abs_contribution_hhi - a.abs_contribution_hhi, None if bool(a.contribution_denominator_valid) and bool(b.contribution_denominator_valid) else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "monthly_outperformance_fraction": (monthly_fraction, None if monthly_fraction is not None else "EMPTY_MONTHLY_SERIES_FAIL_GATE"),
        "negative_twii20_regime_return_delta": (negative_delta, negative_reason),
        "rank_ic_delta_b_minus_a": (float(rank_means.loc["A_PLUS_B", "mean_rank_ic_continuous"] - rank_means.loc["A_ONLY", "mean_rank_ic_continuous"]), None),
        "ndcg_at_10_delta_b_minus_a": (float(rank_means.loc["A_PLUS_B", "mean_ndcg_at_10"] - rank_means.loc["A_ONLY", "mean_ndcg_at_10"]), None),
        "minimum_executed_buys_each_track": (int(min(a.buy_count, b.buy_count)), None),
        "minimum_executed_sells_each_track": (int(min(a.sell_count, b.sell_count)), None),
        "executed_total_action_count_absolute_delta_b_minus_a": (int(abs(b.action_count - a.action_count)), None),
        "pending_or_fallback_actions_allowed": (int(a.pending_count + b.pending_count + a.fallback_count + b.fallback_count), None),
        "all_emitted_positive_quantity_actions_must_execute": (bool(a.all_actions_executed and b.all_actions_executed), None),
        "engineering_violation_count": (engineering_violations, None),
        "post_outcome_threshold_change_allowed": (False, None),
    }
    measured.update({
        "turnover_ratio_b_over_a": finite_ratio(float(b.turnover), float(a.turnover)),
        "fee_tax_ratio_b_over_a": finite_ratio(float(b.fee_tax), float(a.fee_tax)),
        "executed_buy_count_ratio_b_over_a": finite_ratio(float(b.buy_count), float(a.buy_count)),
        "executed_sell_count_ratio_b_over_a": finite_ratio(float(b.sell_count), float(a.sell_count)),
        "executed_total_action_count_ratio_b_over_a": finite_ratio(float(b.action_count), float(a.action_count)),
    })
    rows: list[dict[str, Any]] = []
    for original_gate, contract in frozen.items():
        if original_gate == "all_gates_jointly_required":
            continue
        gate = "engineering_violation_count" if original_gate == "engineering_tolerance" else original_gate
        if gate == "zero_denominator_policy":
            actual, reason, operator, threshold = "FAIL_GATE", None, "==", "FAIL_GATE"
        else:
            actual, reason = measured[gate]
            operator = contract["operator"] if isinstance(contract, dict) else "=="
            threshold = contract["threshold"] if isinstance(contract, dict) else contract
        passed = reason is None and compare(actual, operator, threshold)
        rows.append({
            "gate": gate, "original_gate": original_gate, "scope": "SEALED_CONFIRMATION_30_DAY",
            "measured_value": actual, "operator": operator, "threshold": threshold,
            "status": "PASS" if passed else "FAIL", "pass": bool(passed),
            "reason": reason or ("threshold satisfied" if passed else "threshold not satisfied"),
            "baseline_admission_effect": "NONE_PENDING_SEPARATE_ONBOARDING_REVIEW",
        })
    applicable_pass = all(row["pass"] for row in rows)
    rows.append({
        "gate": "all_gates_jointly_required", "original_gate": "all_gates_jointly_required",
        "scope": "SEALED_CONFIRMATION_30_DAY", "measured_value": applicable_pass,
        "operator": "==", "threshold": True, "status": "PASS" if applicable_pass else "FAIL",
        "pass": applicable_pass, "reason": "all individual gates pass" if applicable_pass else "one or more individual gates failed",
        "baseline_admission_effect": "ELIGIBLE_FOR_SEPARATE_ONBOARDING_REVIEW" if applicable_pass else "NONE",
    })
    verdict = "PASS_ALL_JOINT_CONFIRMATION_GATES" if applicable_pass else "FAIL_ALL_JOINT_CONFIRMATION_GATES"
    return pd.DataFrame(rows), {
        "paired_daily": paired_daily,
        "monthly": monthly,
        "bootstrap_means": pd.DataFrame({"replication": np.arange(BOOTSTRAP_REPLICATIONS), "active_return_mean": bootstrap_means}),
        "joint": {
            "scope": "SEALED_CONFIRMATION_30_DAY", "individual_gate_count": len(rows) - 1,
            "individual_gate_pass_count": sum(row["pass"] for row in rows[:-1]),
            "individual_gate_fail_count": sum(not row["pass"] for row in rows[:-1]),
            "confirmation_all_joint_verdict": verdict,
            "baseline_admission_decided": False,
            "baseline_onboarding_review_eligible": applicable_pass,
            "after_cost_return_delta_b_minus_a": float(b.net_return - a.net_return),
            "paired_active_return_arithmetic_mean": float(paired_daily.active_return_b_minus_a.mean()),
            "bootstrap_95pct_lower_bound": bootstrap_lower,
            "negative_twii20_date_count": int(len(negative)), "monthly_count": int(len(monthly)),
            "engineering_violation_count": engineering_violations,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--precheck-no-sealed-read", action="store_true")
    parser.add_argument("--validate-output", action="store_true")
    args = parser.parse_args()
    if args.precheck_no_sealed_read == args.validate_output:
        raise SystemExit("Select exactly one mode")
    if args.precheck_no_sealed_read:
        validate_authorization(require_auth=False)
        if AUTH.exists() or VALIDATION_AUTH.exists() or OUTPUT.exists():
            raise RuntimeError("authorization or confirmation output already exists")
        print(json.dumps({"status": "PASS_NO_WRITE_NO_SEALED_VALUE_ACCESS"}))
        return 0
    validate_authorization(require_auth=True)
    if not VALIDATION_AUTH.is_file():
        raise RuntimeError("independent output validation authorization missing")
    validation_auth = json.loads(VALIDATION_AUTH.read_text(encoding="utf-8"))
    if (
        validation_auth.get("authorized") is not True
        or validation_auth.get("attempts_authorized") != 1
        or validation_auth.get("implementation_freeze_sha256") != sha256(IMPLEMENTATION)
        or validation_auth.get("validator_sha256") != sha256(VALIDATOR)
        or validation_auth.get("authorization_scope") != "ONE_READONLY_SEALED_CONFIRMATION_OUTPUT_VALIDATION_ATTEMPT"
    ):
        raise RuntimeError("output validation authorization mismatch")
    if not OUTPUT.is_dir() or (OUTPUT.stat().st_mode & 0o777) != 0o700:
        raise RuntimeError("sealed confirmation output directory missing or unsafe")
    marker = OUTPUT / "ATTEMPT_STARTED.json"
    manifest_path = OUTPUT / "MANIFEST.json"
    if (
        not marker.is_file() or not manifest_path.is_file()
        or (marker.stat().st_mode & 0o777) != 0o600
        or (manifest_path.stat().st_mode & 0o777) != 0o600
        or (OUTPUT / "ATTEMPT_FAILURE.json").exists()
    ):
        raise RuntimeError("attempt marker or manifest missing")
    marker_data = json.loads(marker.read_text(encoding="utf-8"))
    if (
        marker_data.get("status") != "SEALED_CONFIRMATION_ATTEMPT_STARTED"
        or marker_data.get("authorization_sha256") != sha256(AUTH)
        or marker_data.get("implementation_freeze_sha256") != sha256(IMPLEMENTATION)
        or marker_data.get("sealed_value_read_started_after_marker") is not True
    ):
        raise RuntimeError("attempt marker binding failed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema_version") != "modelb.b19r2r.sealed_confirmation.v1"
        or manifest.get("status") != "SEALED_CONFIRMATION_EVALUATED_AWAITING_INDEPENDENT_REVIEW"
        or manifest.get("signal_dates") != 30
        or manifest.get("baseline_admission_decided") is not False
        or manifest.get("production_write_performed") is not False
    ):
        raise RuntimeError("confirmation manifest contract failed")
    required_artifacts = {
        "FINAL_MODEL_B_PREDICTIONS.csv", "SIGNALS.csv", "RANK_METRICS_DAILY.csv",
        "RANK_METRICS_SUMMARY.csv", "PAIRED_METRICS.csv", "GATE_TABLE.csv",
        "PAIRED_DAILY_RETURNS.csv", "MONTHLY_DIAGNOSTICS.csv", "BOOTSTRAP_MEANS.csv",
    }
    for method in ("A_ONLY", "A_PLUS_B"):
        prefix = f"sealed_confirmation_30_day_{method}"
        required_artifacts.update({
            f"{prefix}_ACTIONS.csv", f"{prefix}_DAILY_NAV.csv",
            f"{prefix}_PRICE_AUDIT.csv", f"{prefix}_CONTRIBUTION.csv",
        })
    if set(manifest.get("artifacts", {})) != required_artifacts:
        raise RuntimeError("confirmation artifact identity failed")
    for item in manifest.get("artifacts", {}).values():
        path = ROOT / item["path"]
        if (
            not path.is_file() or sha256(path) != item["sha256"]
            or path.stat().st_size != item["bytes"] or (path.stat().st_mode & 0o777) != 0o600
        ):
            raise RuntimeError(f"confirmation artifact binding or permission failed: {item['path']}")
    implementation = json.loads(IMPLEMENTATION.read_text(encoding="utf-8"))
    verify_sealed_hashes_after_attempt_marker(implementation)
    signals, predictions, _, full_ranks, _ = load_and_score_confirmation()
    rank_daily = rank_metrics(signals)
    rank_summary = summarize_rank_metrics(rank_daily)
    grid = normalize(pd.read_parquet(GRID))
    nav_by_method: dict[str, pd.DataFrame] = {}
    rows: list[dict[str, Any]] = []
    recomputed: dict[str, pd.DataFrame] = {
        "FINAL_MODEL_B_PREDICTIONS.csv": predictions,
        "SIGNALS.csv": signals,
        "RANK_METRICS_DAILY.csv": rank_daily,
        "RANK_METRICS_SUMMARY.csv": rank_summary,
    }
    for method, score in (("A_ONLY", "a_only_buy_score"), ("A_PLUS_B", "a_plus_b_buy_score")):
        actions, nav, audit, contribution = replay(
            signals, grid, full_ranks, score, method, "sealed_confirmation_30_day"
        )
        prefix = f"sealed_confirmation_30_day_{method}"
        recomputed.update({
            f"{prefix}_ACTIONS.csv": actions, f"{prefix}_DAILY_NAV.csv": nav,
            f"{prefix}_PRICE_AUDIT.csv": audit, f"{prefix}_CONTRIBUTION.csv": contribution,
        })
        rows.append(summarize("sealed_confirmation_30_day", method, actions, nav, contribution))
        nav_by_method[method] = nav
    paired = pd.DataFrame(rows).sort_values("method", kind="mergesort").reset_index(drop=True)
    gates, support = build_gate_table(
        json.loads(PROTOCOL.read_text(encoding="utf-8")), paired, nav_by_method, rank_summary, signals
    )
    recomputed.update({
        "PAIRED_METRICS.csv": paired, "GATE_TABLE.csv": gates,
        "PAIRED_DAILY_RETURNS.csv": support["paired_daily"],
        "MONTHLY_DIAGNOSTICS.csv": support["monthly"], "BOOTSTRAP_MEANS.csv": support["bootstrap_means"],
    })
    for name, expected in recomputed.items():
        actual = pd.read_csv(ROOT / manifest["artifacts"][name]["path"])
        if list(actual.columns) != list(expected.columns) or len(actual) != len(expected):
            raise RuntimeError(f"recomputed artifact schema/row mismatch: {name}")
        for column in expected.columns:
            if not all(
                serialized_value_matches(actual_value, expected_value)
                for actual_value, expected_value in zip(actual[column], expected[column], strict=True)
            ):
                raise RuntimeError(f"recomputed value mismatch: {name} {column}")
    if manifest.get("gate_result") != support["joint"]:
        raise RuntimeError("joint gate manifest recomputation mismatch")
    result = {
        "protocol_verdict": "PASS", "output_verdict": "PASS",
        "confirmation_all_joint_verdict": support["joint"]["confirmation_all_joint_verdict"],
        "individual_gate_count": support["joint"]["individual_gate_count"],
        "individual_gate_fail_count": support["joint"]["individual_gate_fail_count"],
        "baseline_admission_decided": False,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
