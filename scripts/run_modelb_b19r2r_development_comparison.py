#!/usr/bin/env python3
"""Execute the frozen development-only A versus A+B OOF comparison."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_comparative_evaluation_20260916"
PROTOCOL = RUN / "B19R2R_COMPARATIVE_FREEZE.json"
ADAPTER = RUN / "B19R2R_COMPARATIVE_FREEZE_AMENDMENT_01.json"
IMPLEMENTATION = RUN / "B19R2R_COMPARATIVE_IMPLEMENTATION_FREEZE_V2.json"
AUTH = RUN / "B19R2R_COMPARATIVE_EXECUTION_AUTHORIZATION_V2.json"
OUTPUT = RUN / "evaluation_output_v2"
VALIDATOR = ROOT / "scripts/validate_modelb_b19r2r_development_comparison.py"
R2R = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916"
HISTORICAL = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_historical_exact50_20260916/materialized_v2/HISTORICAL_EXACT50_TRAINING_SAMPLE.parquet"
FEATURES = R2R / "FEATURE_ARTIFACT_78_RAW.parquet"
KEYS = R2R / "EXACT50_KEYSETS.csv"
MODEL_A = R2R / "MODEL_A_FULL_CROSS_SECTION.parquet"
LABELS = R2R / "outcome_materialization_v1/development/DEVELOPMENT_EXACT50_LABELS.parquet"
GRID = R2R / "outcome_materialization_v1/development/DEVELOPMENT_EXECUTION_GRID.parquet"
SCHEMA = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json"
TRAINING_MANIFEST = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_training_20260916/training_output_v1/TRAINING_MANIFEST.json"
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
FOLDS = {
    "outer_1": ("2026-04-22", "2026-05-11", "2026-06-05"),
    "outer_2": ("2026-05-22", "2026-06-08", "2026-07-06"),
}


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
    for path in (PROTOCOL, ADAPTER, IMPLEMENTATION):
        if not path.is_file():
            raise RuntimeError(f"missing frozen contract: {rel(path)}")
    implementation = json.loads(IMPLEMENTATION.read_text(encoding="utf-8"))
    if implementation.get("status") != "CLOSED_BEFORE_COMPARATIVE_EXECUTION":
        raise RuntimeError("implementation freeze is not closed")
    for name, path in {"evaluator": Path(__file__), "validator": VALIDATOR}.items():
        if implementation["implementation_bindings"][name]["sha256"] != sha256(path):
            raise RuntimeError(f"implementation hash mismatch: {name}")
    for item in implementation["source_bindings"].values():
        path = ROOT / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise RuntimeError(f"source binding mismatch: {item['path']}")
        if any(token in item["path"] for token in ("sealed_embargo", "sealed_confirmation", "EMBARGO_", "CONFIRMATION_")):
            raise RuntimeError("sealed source path is forbidden")
    if require_auth:
        if not AUTH.is_file():
            raise RuntimeError("independent execution authorization missing")
        auth = json.loads(AUTH.read_text(encoding="utf-8"))
        if (
            auth.get("authorized") is not True
            or auth.get("attempts_authorized") != 1
            or auth.get("implementation_freeze_sha256") != sha256(IMPLEMENTATION)
        ):
            raise RuntimeError("execution authorization mismatch")
    return implementation


def fit_ranker(frame: pd.DataFrame, features: list[str], config: dict[str, Any]) -> lgb.LGBMRanker:
    sizes = frame.groupby("date", sort=True).size().tolist()
    if not sizes or set(sizes) != {50} or sum(sizes) != len(frame):
        raise RuntimeError("non-Exact50 training groups")
    model = lgb.LGBMRanker(**config)
    model.fit(frame[features], frame[REL].astype(int), group=sizes)
    return model


def load_and_score_oof() -> tuple[pd.DataFrame, pd.DataFrame, list[str], pd.DataFrame, dict[str, Any]]:
    features = json.loads(SCHEMA.read_text(encoding="utf-8"))["feature_order"]
    historical = normalize(pd.read_parquet(HISTORICAL, columns=KEY + features + [CONT, REL]))
    feature_source = normalize(pd.read_parquet(FEATURES, columns=KEY + features + ["feature_raw_complete_78"]))
    if (
        len(feature_source) != 12000
        or feature_source.date.nunique() != 80
        or feature_source.duplicated(KEY).any()
        or feature_source.groupby("date").size().ne(150).any()
    ):
        raise RuntimeError("frozen 78F full-source shape failed")
    development_features = feature_source[feature_source.date.between("2026-05-11", "2026-07-06")].copy()
    if (
        len(development_features) != 6000
        or development_features.date.nunique() != 40
        or development_features.groupby("date").size().ne(150).any()
    ):
        raise RuntimeError("development 78F filtered shape failed")
    development_labels = normalize(pd.read_parquet(LABELS, columns=KEY + [CONT, REL, "label_complete"]))
    if (
        len(development_labels) != 2000
        or development_labels.date.nunique() != 40
        or development_labels.duplicated(KEY).any()
        or development_labels.groupby("date").size().ne(50).any()
    ):
        raise RuntimeError("development label source shape failed")
    key_source = normalize(pd.read_csv(KEYS))
    if (
        len(key_source) != 4000
        or key_source.date.nunique() != 80
        or key_source.duplicated(KEY).any()
        or key_source.groupby("date").size().ne(50).any()
    ):
        raise RuntimeError("frozen Exact-50 full-source shape failed")
    development_keys = key_source[key_source.date.between("2026-05-11", "2026-07-06")].copy()
    development_keys = development_keys.rename(columns={
        "model_a_raw_score": "keyset_model_a_raw_score",
        "full_qlib_rank": "keyset_full_qlib_rank",
    })
    if (
        len(development_keys) != 2000
        or development_keys.duplicated(KEY).any()
        or development_keys.groupby("date").size().ne(50).any()
        or not np.isfinite(
            development_keys[["eligible_candidate_rank", "keyset_model_a_raw_score", "keyset_full_qlib_rank"]].to_numpy(float)
        ).all()
        or development_keys.groupby("date").eligible_candidate_rank.nunique().ne(50).any()
        or not development_keys.eligible_candidate_rank.between(1, 50).all()
    ):
        raise RuntimeError("development Exact-50 keyset contract failed")
    model_a_source = normalize(pd.read_parquet(MODEL_A, columns=KEY + ["model_a_raw_score", "full_qlib_rank"]))
    if (
        len(model_a_source) != 12000
        or model_a_source.date.nunique() != 80
        or model_a_source.duplicated(KEY).any()
        or model_a_source.groupby("date").size().ne(150).any()
        or not np.isfinite(model_a_source[["model_a_raw_score", "full_qlib_rank"]].to_numpy(float)).all()
    ):
        raise RuntimeError("frozen Model A full-rank coverage failed")
    model_a = model_a_source[model_a_source.date.between("2026-05-11", "2026-07-06")].copy()
    if (
        len(model_a) != 6000
        or model_a.date.nunique() != 40
        or model_a.groupby("date").size().ne(150).any()
    ):
        raise RuntimeError("development Model A filtered shape failed")
    development = (
        development_keys.merge(development_features, on=KEY, validate="one_to_one")
        .merge(development_labels, on=KEY, validate="one_to_one")
        .merge(model_a, on=KEY, validate="one_to_one")
        .sort_values(KEY, kind="mergesort").reset_index(drop=True)
    )
    if len(development) != 2000 or development.groupby("date").size().ne(50).any():
        raise RuntimeError("development keys are not 40x50")
    if not development.feature_raw_complete_78.all() or not development.label_complete.all():
        raise RuntimeError("development completeness failed")
    keyset_score = development.keyset_model_a_raw_score.to_numpy(float)
    canonical_score = development.model_a_raw_score.to_numpy(float)
    score_close = np.isclose(
        keyset_score,
        canonical_score,
        rtol=MODEL_A_SCORE_PARITY_RTOL,
        atol=MODEL_A_SCORE_PARITY_ATOL,
    )
    score_max_abs_diff = float(np.max(np.abs(keyset_score - canonical_score)))
    keyset_rank = development.keyset_full_qlib_rank.to_numpy(float)
    canonical_rank = development.full_qlib_rank.to_numpy(float)
    if not score_close.all():
        raise RuntimeError("Exact-50 keyset and canonical Model A score parity failed")
    if not np.array_equal(keyset_rank, canonical_rank):
        raise RuntimeError("Exact-50 keyset and canonical Model A full-rank parity failed")
    feature_score = development.qlib_score_raw.to_numpy(float)
    if not np.isfinite(canonical_score).all() or not np.isfinite(feature_score).all():
        raise RuntimeError("nonfinite canonical Model A score")
    if not np.array_equal(canonical_score, feature_score):
        raise RuntimeError("Model A score parity failed")
    if not np.isfinite(development[features + [CONT, REL]].to_numpy(float)).all():
        raise RuntimeError("nonfinite development feature or label")
    combined = pd.concat([historical, development[historical.columns]], ignore_index=True).sort_values(KEY, kind="mergesort")
    selected = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
    if selected.get("selected_candidate_id") != 14:
        raise RuntimeError("selected candidate drifted")
    config = selected["selected_config"]
    predictions: list[pd.DataFrame] = []
    for fold, (train_end, valid_start, valid_end) in FOLDS.items():
        train = combined[combined.date.le(train_end)].copy()
        valid = development[development.date.between(valid_start, valid_end)].copy()
        expected_train_rows = 39350 if fold == "outer_1" else 39850
        if len(train) != expected_train_rows or len(valid) != 1000 or valid.date.nunique() != 20:
            raise RuntimeError(f"frozen OOF fold shape failed: {fold}")
        model = fit_ranker(train, features, config)
        scored = valid[KEY].copy()
        scored["fold"] = fold
        scored["train_end"] = train_end
        scored["model_b_oof_raw_score"] = model.predict(valid[features])
        predictions.append(scored)
    oof = pd.concat(predictions, ignore_index=True).sort_values(KEY, kind="mergesort")
    if len(oof) != 2000 or oof.duplicated(KEY).any() or not np.isfinite(oof.model_b_oof_raw_score).all():
        raise RuntimeError("OOF prediction coverage failed")
    signals = development.merge(oof, on=KEY, validate="one_to_one")
    signals["a_only_buy_score"] = signals.model_a_raw_score
    signals["a_plus_b_buy_score"] = signals.model_b_oof_raw_score
    if not np.isfinite(signals[["a_only_buy_score", "a_plus_b_buy_score", "full_qlib_rank"]].to_numpy(float)).all():
        raise RuntimeError("nonfinite canonical signal score or rank")
    for score, rank in (("a_only_buy_score", "a_only_score_rank"), ("a_plus_b_buy_score", "a_plus_b_score_rank")):
        signals[rank] = signals.groupby("date", sort=True)[score].rank(method="first", ascending=False).astype(int)
        # Replace pandas input-order ties with the frozen instrument tie rule.
        signals[rank] = signals.sort_values(["date", score, "instrument"], ascending=[True, False, True], kind="mergesort").groupby("date").cumcount().add(1).sort_index()
    return (
        signals.sort_values(KEY, kind="mergesort"),
        oof,
        features,
        model_a[KEY + ["full_qlib_rank"]].sort_values(KEY, kind="mergesort"),
        {
            "rows": len(development),
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
                "date": day, "fold": str(group.fold.iloc[0]), "method": method,
                "rank_ic_continuous": float(rho),
                "ndcg_at_10": ndcg,
            })
    return pd.DataFrame(rows)


def summarize_rank_metrics(rank_daily: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for scope, scoped in [("combined_development", rank_daily)] + [
        (fold, rank_daily[rank_daily.fold.eq(fold)]) for fold in FOLDS
    ]:
        summary = (
            scoped.groupby("method", as_index=False)
            .agg(
                date_count=("date", "nunique"),
                mean_rank_ic_continuous=("rank_ic_continuous", "mean"),
                mean_ndcg_at_10=("ndcg_at_10", "mean"),
            )
        )
        summary.insert(0, "scope", scope)
        frames.append(summary)
    result = pd.concat(frames, ignore_index=True)
    if len(result) != 6 or result.duplicated(["scope", "method"]).any():
        raise RuntimeError("rank metric summary scope/method identity failed")
    return result


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
    if not math.isclose(float(contribution_frame.total_contribution.sum()), float(nav_frame.equity.iloc[-1] - INITIAL), abs_tol=1e-6):
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


def build_gate_table(
    protocol: dict[str, Any],
    paired: pd.DataFrame,
    nav_by_method: dict[str, pd.DataFrame],
    rank_summary: pd.DataFrame,
    signals: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frozen = protocol["preregistered_numeric_quality_gates"]
    combined = paired[paired.scope.eq("combined_development")].set_index("method")
    a = combined.loc["A_ONLY"]
    b = combined.loc["A_PLUS_B"]
    paired_daily = nav_by_method["A_ONLY"][["signal_date", "date", "daily_return"]].rename(columns={"date": "execution_date", "daily_return": "a_return"}).merge(
        nav_by_method["A_PLUS_B"][["signal_date", "date", "daily_return"]].rename(columns={"date": "execution_date", "daily_return": "b_return"}),
        on=["signal_date", "execution_date"], validate="one_to_one",
    )
    regime = signals.groupby("date", as_index=False).agg(twii_ret20=("TWII_ret20", "first"), regime_values=("TWII_ret20", "nunique"))
    if len(paired_daily) != 40 or regime.regime_values.ne(1).any():
        raise RuntimeError("paired daily return or TWII_ret20 date-level uniqueness failed")
    paired_daily = paired_daily.merge(regime[["date", "twii_ret20"]], left_on="signal_date", right_on="date", validate="one_to_one")
    paired_daily["active_return_b_minus_a"] = paired_daily.b_return - paired_daily.a_return
    paired_daily["month"] = paired_daily.signal_date.str[:7]
    monthly = paired_daily.groupby("month").agg(
        a_return=("a_return", lambda x: float(np.prod(1.0 + x) - 1.0)),
        b_return=("b_return", lambda x: float(np.prod(1.0 + x) - 1.0)),
    ).reset_index()
    monthly_fraction = float((monthly.b_return > monthly.a_return).mean()) if len(monthly) else None
    negative = paired_daily[paired_daily.twii_ret20 < 0]
    negative_delta = None
    negative_reason = None
    if negative.empty:
        negative_reason = "EMPTY_NEGATIVE_TWII20_REGIME_FAIL_GATE"
    else:
        negative_delta = float(np.prod(1.0 + negative.b_return) - np.prod(1.0 + negative.a_return))
    rank_means = rank_summary[rank_summary.scope.eq("combined_development")].set_index("method")
    ratios: dict[str, tuple[float | None, str | None]] = {
        "turnover_ratio_b_over_a": finite_ratio(float(b.turnover), float(a.turnover)),
        "fee_tax_ratio_b_over_a": finite_ratio(float(b.fee_tax), float(a.fee_tax)),
        "executed_buy_count_ratio_b_over_a": finite_ratio(float(b.buy_count), float(a.buy_count)),
        "executed_sell_count_ratio_b_over_a": finite_ratio(float(b.sell_count), float(a.sell_count)),
        "executed_total_action_count_ratio_b_over_a": finite_ratio(float(b.action_count), float(a.action_count)),
    }
    measured: dict[str, tuple[Any, str | None]] = {
        "max_drawdown_noninferiority_b_minus_a": (float(b.max_drawdown - a.max_drawdown), None),
        "top1_abs_contribution_share": (float(b.top1_abs_contribution_share) if pd.notna(b.top1_abs_contribution_share) else None, None if bool(b.contribution_denominator_valid) else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "top1_abs_contribution_share_vs_a_delta": (float(b.top1_abs_contribution_share - a.top1_abs_contribution_share) if bool(a.contribution_denominator_valid) and bool(b.contribution_denominator_valid) else None, None if bool(a.contribution_denominator_valid) and bool(b.contribution_denominator_valid) else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "top5_abs_contribution_share": (float(b.top5_abs_contribution_share) if pd.notna(b.top5_abs_contribution_share) else None, None if bool(b.contribution_denominator_valid) else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "top5_abs_contribution_share_vs_a_delta": (float(b.top5_abs_contribution_share - a.top5_abs_contribution_share) if bool(a.contribution_denominator_valid) and bool(b.contribution_denominator_valid) else None, None if bool(a.contribution_denominator_valid) and bool(b.contribution_denominator_valid) else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "abs_contribution_hhi": (float(b.abs_contribution_hhi) if pd.notna(b.abs_contribution_hhi) else None, None if bool(b.contribution_denominator_valid) else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "abs_contribution_hhi_vs_a_delta": (float(b.abs_contribution_hhi - a.abs_contribution_hhi) if bool(a.contribution_denominator_valid) and bool(b.contribution_denominator_valid) else None, None if bool(a.contribution_denominator_valid) and bool(b.contribution_denominator_valid) else "ZERO_CONTRIBUTION_DENOMINATOR_FAIL_GATE"),
        "monthly_outperformance_fraction": (monthly_fraction, None if monthly_fraction is not None else "EMPTY_MONTHLY_SERIES_FAIL_GATE"),
        "negative_twii20_regime_return_delta": (negative_delta, negative_reason),
        "rank_ic_delta_b_minus_a": (float(rank_means.loc["A_PLUS_B", "mean_rank_ic_continuous"] - rank_means.loc["A_ONLY", "mean_rank_ic_continuous"]), None),
        "ndcg_at_10_delta_b_minus_a": (float(rank_means.loc["A_PLUS_B", "mean_ndcg_at_10"] - rank_means.loc["A_ONLY", "mean_ndcg_at_10"]), None),
        "minimum_executed_buys_each_track": (int(min(a.buy_count, b.buy_count)), None),
        "minimum_executed_sells_each_track": (int(min(a.sell_count, b.sell_count)), None),
        "executed_total_action_count_absolute_delta_b_minus_a": (int(abs(b.action_count - a.action_count)), None),
        "pending_or_fallback_actions_allowed": (int(a.pending_count + b.pending_count + a.fallback_count + b.fallback_count), None),
        "all_emitted_positive_quantity_actions_must_execute": (bool(a.all_actions_executed and b.all_actions_executed), None),
        "engineering_tolerance": (float(max(abs(a.reconciliation_delta), abs(b.reconciliation_delta))), None),
        "post_outcome_threshold_change_allowed": (False, None),
    }
    measured.update(ratios)
    rows: list[dict[str, Any]] = []
    reserved = {
        "confirmation_after_cost_return_delta_b_minus_a",
        "confirmation_paired_moving_block_bootstrap_95pct_lower_bound",
    }
    for gate, contract in frozen.items():
        if gate in reserved:
            rows.append({"gate": gate, "scope": "SEALED_CONFIRMATION_30_DAY_ONLY", "measured_value": None, "operator": contract["operator"], "threshold": contract["threshold"], "status": "RESERVED_FOR_CONFIRMATION_NOT_EVALUATED", "pass": None, "reason": "30-day confirmation-only contract; development has 40 days", "baseline_admission_effect": "NONE"})
            continue
        if gate == "all_gates_jointly_required":
            rows.append({"gate": gate, "scope": "SEALED_CONFIRMATION_POLICY", "measured_value": None, "operator": "==", "threshold": True, "status": "POLICY_PRESERVED_NOT_ADJUDICATED", "pass": None, "reason": "development cannot produce the all-joint confirmation verdict", "baseline_admission_effect": "NONE"})
            continue
        if gate == "zero_denominator_policy":
            actual, reason, operator, threshold = "FAIL_GATE", None, "==", "FAIL_GATE"
        else:
            if gate not in measured:
                raise RuntimeError(f"required development gate is not computed: {gate}")
            actual, reason = measured[gate]
            operator = contract["operator"] if isinstance(contract, dict) else "=="
            threshold = contract["threshold"] if isinstance(contract, dict) else contract
        passed = reason is None and compare(actual, operator, threshold)
        rows.append({"gate": gate, "scope": "COMBINED_DEVELOPMENT_DIAGNOSTIC", "measured_value": actual, "operator": operator, "threshold": threshold, "status": "PASS" if passed else "FAIL", "pass": bool(passed), "reason": reason or ("threshold satisfied" if passed else "threshold not satisfied"), "baseline_admission_effect": "NONE"})
    gate_table = pd.DataFrame(rows)
    applicable = gate_table[gate_table.status.isin(["PASS", "FAIL"])]
    diagnostic = {
        "scope": "COMBINED_DEVELOPMENT_DIAGNOSTIC",
        "applicable_gate_count": int(len(applicable)),
        "applicable_gate_pass_count": int(applicable["pass"].eq(True).sum()),
        "applicable_gate_fail_count": int(applicable["pass"].eq(False).sum()),
        "development_applicable_gate_verdict": "PASS_APPLICABLE_DEVELOPMENT_DIAGNOSTICS" if applicable["pass"].eq(True).all() else "FAIL_APPLICABLE_DEVELOPMENT_DIAGNOSTICS",
        "confirmation_all_joint_verdict": "NOT_EVALUATED",
        "baseline_admission_effect": "NONE",
        "after_cost_return_delta_b_minus_a_diagnostic_only": float(b.net_return - a.net_return),
        "paired_daily_active_return_mean_b_minus_a": float(paired_daily.active_return_b_minus_a.mean()),
        "paired_daily_active_return_sum_b_minus_a": float(paired_daily.active_return_b_minus_a.sum()),
        "negative_twii20_date_count": int(len(negative)),
        "monthly_count": int(len(monthly)),
    }
    return gate_table, {"paired_daily": paired_daily, "monthly": monthly, "diagnostic": diagnostic}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-no-write", action="store_true")
    parser.add_argument("--execute-frozen-comparison", action="store_true")
    args = parser.parse_args()
    if args.preflight_no_write == args.execute_frozen_comparison:
        raise SystemExit("Select exactly one mode")
    if args.preflight_no_write:
        validate_authorization(require_auth=False)
        if AUTH.exists() or OUTPUT.exists():
            raise RuntimeError("authorization or evaluation output already exists")
        print(json.dumps({"status": "PASS_NO_WRITE", "authorization_absent": True, "output_absent": True}))
        return 0
    validate_authorization(require_auth=True)
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite evaluation output")
    signals, oof, features, full_ranks, model_a_parity = load_and_score_oof()
    rank_daily = rank_metrics(signals)
    rank_summary = summarize_rank_metrics(rank_daily)
    grid = normalize(pd.read_parquet(GRID))
    if (
        len(grid) != 6000
        or grid.date.nunique() != 40
        or grid.duplicated(KEY).any()
        or grid.groupby("date").size().ne(150).any()
        or not np.isfinite(grid[["next_open", "next_close"]].to_numpy(float)).all()
    ):
        raise RuntimeError("development execution grid shape or finite-price check failed")
    results: list[dict[str, Any]] = []
    combined_nav: dict[str, pd.DataFrame] = {}
    artifacts: dict[str, pd.DataFrame] = {
        "OOF_SCORES.csv": oof,
        "SIGNALS.csv": signals,
        "RANK_METRICS_DAILY.csv": rank_daily,
        "RANK_METRICS_SUMMARY.csv": rank_summary,
    }
    for scope, scoped in [("combined_development", signals)] + [(fold, signals[signals.fold.eq(fold)]) for fold in FOLDS]:
        for method, score in (("A_ONLY", "a_only_buy_score"), ("A_PLUS_B", "a_plus_b_buy_score")):
            actions, nav, audit, contribution = replay(scoped, grid, full_ranks, score, method, scope)
            prefix = f"{scope}_{method}"
            artifacts[f"{prefix}_ACTIONS.csv"] = actions
            artifacts[f"{prefix}_DAILY_NAV.csv"] = nav
            artifacts[f"{prefix}_PRICE_AUDIT.csv"] = audit
            artifacts[f"{prefix}_CONTRIBUTION.csv"] = contribution
            results.append(summarize(scope, method, actions, nav, contribution))
            if scope == "combined_development":
                combined_nav[method] = nav
    paired = pd.DataFrame(results).sort_values(["scope", "method"], kind="mergesort").reset_index(drop=True)
    if len(paired) != 6 or paired.duplicated(["scope", "method"]).any():
        raise RuntimeError("paired metrics scope/method identity failed")
    artifacts["PAIRED_METRICS.csv"] = paired
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    gates, gate_support = build_gate_table(protocol, paired, combined_nav, rank_summary, signals)
    artifacts["GATE_TABLE.csv"] = gates
    artifacts["PAIRED_DAILY_RETURNS.csv"] = gate_support["paired_daily"]
    artifacts["MONTHLY_DIAGNOSTICS.csv"] = gate_support["monthly"]
    # Do not leave an output footprint when any fit, prediction, replay, metric, or gate computation fails.
    OUTPUT.mkdir(parents=True, exist_ok=False)
    hashes: dict[str, Any] = {}
    for name, frame in artifacts.items():
        path = OUTPUT / name
        frame.to_csv(path, index=False)
        hashes[name] = {"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size, "rows": len(frame)}
    manifest = {
        "schema_version": "modelb.b19r2r.development_comparison.v2",
        "status": "DEVELOPMENT_DIAGNOSTIC_AWAITING_INDEPENDENT_REVIEW",
        "feature_count": len(features), "oof_rows": len(oof), "oof_dates": oof.date.nunique(),
        "paired_metric_rows": len(paired), "paired_metric_identity": "scope+method",
        "model_a_keyset_source_parity": model_a_parity,
        "gate_diagnostic": gate_support["diagnostic"],
        "confirmation_only_gates_reserved": [
            "confirmation_after_cost_return_delta_b_minus_a",
            "confirmation_paired_moving_block_bootstrap_95pct_lower_bound",
        ],
        "confirmation_all_joint_verdict": "NOT_EVALUATED",
        "development_bootstrap_performed": False,
        "final_pickle_used_for_development": False, "sealed_accessed": False,
        "baseline_admission_decided": False, "production_write_performed": False,
        "artifacts": hashes,
    }
    manifest_path = OUTPUT / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n")
    (OUTPUT / "EXECUTION_REPORT_CN.md").write_text(
        "# B19R2R development comparison\n\n"
        f"Development applicable diagnostic verdict: `{gate_support['diagnostic']['development_applicable_gate_verdict']}`。\n\n"
        "30-day confirmation after-cost 与 bootstrap gates 保留为 `RESERVED_FOR_CONFIRMATION_NOT_EVALUATED`；"
        "没有产生 confirmation all-joint verdict。结果仅为 development diagnostic，等待独立审查，且不得自动进入 baseline。\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": manifest["status"], "oof_rows": len(oof)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
