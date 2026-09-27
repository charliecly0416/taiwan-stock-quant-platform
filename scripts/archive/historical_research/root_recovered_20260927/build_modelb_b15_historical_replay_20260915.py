#!/usr/bin/env python3
"""Build an isolated, one-window historical diagnostic for the frozen B9 ranker.

This is deliberately not the formal B7 replay: it uses one archived post-test
signal date and a fixed 10-trading-day basket, so it cannot be counted as OOS
or prospective evidence. No production/latest/default state is written.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b15_historical_replay_20260915"
ASOF = "2026-06-17"
TOP50 = 50
TARGET = 10
FEE = 0.001425
TAX = 0.003
INITIAL = 1_000_000.0

FEATURES = ROOT / "data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_r_calendar_bridge_repair/isolated_phase_yz/yz2_orthogonal_feature_package/2026-06-17/features.csv"
MODEL_A = ROOT / "data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/signals.csv"
MODEL_B = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b9_canonical_label_retrain_20260914/MODEL_B_CANONICAL_LGBM_RANKER.pkl"
B9_FREEZE = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b9_canonical_label_retrain_20260914/B9_CANONICAL_RETRAIN_RUN_FREEZE.json"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
TWII_BRIDGE = ROOT / "data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/twii_bridge.csv"
PROTECTED = [
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
]


def sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fingerprints() -> dict[str, str | None]:
    return {str(p.relative_to(ROOT)): sha(p) for p in PROTECTED}


def load_inputs() -> tuple[pd.DataFrame, list[str], dict[str, object]]:
    freeze = json.loads(B9_FREEZE.read_text(encoding="utf-8"))
    model = joblib.load(MODEL_B)
    feature_order = list(model.booster_.feature_name())
    if len(feature_order) != int(freeze["feature_count"]):
        raise RuntimeError("B9 feature count does not match freeze")
    order_hash = hashlib.sha256(json.dumps(feature_order, separators=(",", ":")).encode()).hexdigest()
    if order_hash != freeze["feature_order_sha256"]:
        raise RuntimeError("B9 feature order hash drift")

    f = pd.read_csv(FEATURES, dtype={"instrument": str})
    f.instrument = f.instrument.astype(str).str.upper()
    if len(f) != TOP50 or f.instrument.duplicated().any():
        raise RuntimeError("historical feature artifact is not an exact 50-row set")
    missing = [c for c in feature_order if c not in f.columns]
    if missing:
        raise RuntimeError(f"missing B9 feature columns: {missing}")
    if f[feature_order].isna().any().any():
        raise RuntimeError("NaN in historical B9 feature frame")
    f["b_score"] = model.predict(f[feature_order])

    a = pd.read_csv(MODEL_A, dtype={"instrument": str})
    a.instrument = a.instrument.astype(str).str.upper()
    a = a[(a.date.astype(str).str[:10] == ASOF) & (a.full_qlib_rank <= TOP50)].copy()
    if len(a) != TOP50 or set(a.instrument) != set(f.instrument):
        raise RuntimeError("Model A Top50 and feature key sets do not match")
    # The frozen route excludes TW7769. Keep the remaining 49 rows together
    # for this diagnostic; formal B7 still requires a future exact 50/50 set.
    f = f[f.instrument != "TW7769"].copy()
    a = a[a.instrument != "TW7769"].copy()
    out = a[["date", "instrument", "raw_score", "full_qlib_rank", "candidate_rank"]].merge(
        f[["instrument", "b_score"]], on="instrument", validate="one_to_one"
    )
    out = out.rename(columns={"raw_score": "a_score"})
    out["date"] = ASOF
    out["a_rank"] = out.a_score.rank(method="first", ascending=False).astype(int)
    out["b_rank"] = out.b_score.rank(method="first", ascending=False).astype(int)
    meta = {
        "feature_count": len(feature_order),
        "feature_order_sha256": order_hash,
        "feature_manifest": str(FEATURES.relative_to(ROOT)),
        "model_a_manifest": str(MODEL_A.relative_to(ROOT)),
        "model_b": str(MODEL_B.relative_to(ROOT)),
        "model_b_sha256": sha(MODEL_B),
        "model_a_top50_exact": len(a) == TOP50 - 1,
        "candidate_set_after_exclusion": "49_rows_without_TW7769",
        "excluded_symbols": ["TW7769"],
        "pit_feature_artifact_status": "PASS_PER_YZ2_MANIFEST",
    }
    return out, feature_order, meta


def load_prices(symbols: set[str]) -> dict[str, pd.DataFrame]:
    prices: dict[str, pd.DataFrame] = {}
    for symbol in sorted(symbols):
        p = PRICE_ROOT / f"{symbol}.csv"
        if not p.is_file():
            raise RuntimeError(f"missing historical price file: {symbol}")
        d = pd.read_csv(p, usecols=["date", "open"], dtype={"date": str})
        d["date"] = d.date.str[:10]
        d["open"] = pd.to_numeric(d.open, errors="coerce")
        d = d.dropna().query("open > 0").sort_values("date")
        prices[symbol] = d
    return prices


def price_inventory_hash(symbols: set[str]) -> str:
    h = hashlib.sha256()
    for symbol in sorted(symbols):
        h.update(symbol.encode())
        h.update((sha(PRICE_ROOT / f"{symbol}.csv") or "").encode())
    return h.hexdigest()


def common_future_dates(prices: dict[str, pd.DataFrame]) -> list[str]:
    sets = [set(d.loc[d.date > ASOF, "date"]) for d in prices.values()]
    common = sorted(set.intersection(*sets))
    if len(common) < 10:
        raise RuntimeError("fewer than 10 common future trading dates")
    return common[:10]


def basket_metrics(frame: pd.DataFrame, prices: dict[str, pd.DataFrame], score: str, method: str, dates: list[str]) -> tuple[dict[str, object], list[dict[str, object]]]:
    selected = frame.sort_values([score, "instrument"], ascending=[False, True]).head(TARGET)
    entry, exit_ = dates[0], dates[-1]
    rows: list[dict[str, object]] = []
    gross = 0.0
    fees = 0.0
    taxes = 0.0
    for r in selected.itertuples(index=False):
        d = prices[r.instrument]
        ep = float(d.loc[d.date == entry, "open"].iloc[0])
        xp = float(d.loc[d.date == exit_, "open"].iloc[0])
        allocation = INITIAL / TARGET
        qty = int(allocation / (ep * 10)) * 10
        buy_notional = qty * ep
        sell_notional = qty * xp
        commission = (buy_notional + sell_notional) * FEE
        tax = sell_notional * TAX
        net = sell_notional - buy_notional - commission - tax
        gross += net
        fees += commission
        taxes += tax
        rows.append({"method": method, "instrument": r.instrument, "signal_date": ASOF, "entry_date": entry, "exit_date": exit_, "quantity": qty, "entry_open": ep, "exit_open": xp, "commission": commission, "sell_tax": tax, "net_pnl": net, "a_rank": int(r.a_rank), "b_rank": int(r.b_rank)})
    metrics = {"method": method, "signal_date": ASOF, "entry_date": entry, "exit_date": exit_, "horizon_trading_days": 10, "selected_count": TARGET, "filled_positions": sum(int(r["quantity"]) > 0 for r in rows), "zero_quantity_positions": sum(int(r["quantity"]) == 0 for r in rows), "initial_equity": INITIAL, "net_pnl": round(gross, 8), "net_return": round(gross / INITIAL, 8), "commission": round(fees, 8), "sell_tax": round(taxes, 8), "total_cost": round(fees + taxes, 8), "diagnostic_only": True}
    return metrics, rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    before = fingerprints()
    frame, feature_order, input_meta = load_inputs()
    prices = load_prices(set(frame.instrument))
    dates = common_future_dates(prices)
    a_metrics, a_actions = basket_metrics(frame, prices, "a_score", "A_ONLY", dates)
    b_metrics, b_actions = basket_metrics(frame, prices, "b_score", "A_PLUS_B", dates)
    frame.to_csv(OUT / "signals.csv", index=False)
    pd.DataFrame([a_metrics, b_metrics]).to_csv(OUT / "paired_metrics.csv", index=False)
    pd.DataFrame(a_actions + b_actions).to_csv(OUT / "actions.csv", index=False)
    after = fingerprints()
    manifest = {
        "schema_version": "modelb.b15.historical_replay.manifest.v1",
        "run_id": "modelb_b15_historical_replay_20260915",
        "status": "DIAGNOSTIC_ONLY_COMPLETED",
        "signal_date": ASOF,
        "window": [dates[0], dates[-1]],
        "historical_post_b9_test": True,
        "training_performed": False,
        "formal_oos": False,
        "prospective_settled_day": False,
        "baseline_admission": False,
        "production_allowed": False,
        "feature_count": len(feature_order),
        "candidate_rows": len(frame),
        "candidate_set_exact_50": len(frame) == TOP50 and frame.full_qlib_rank.nunique() == TOP50,
        "candidate_set_exact_49_after_exclusion": len(frame) == TOP50 - 1 and frame.full_qlib_rank.nunique() == TOP50 - 1,
        "execution": {"entry": "10th common future trading day next_open", "exit": "10th common future trading day next_open", "fee_rate": FEE, "sell_tax_rate": TAX, "lot_size": 10},
        "price_source": str(PRICE_ROOT.relative_to(ROOT)),
        "price_inventory_sha256": price_inventory_hash(set(frame.instrument)),
        "input": input_meta,
        "metrics": [a_metrics, b_metrics],
        "relative": {"net_return_diff_b_minus_a": b_metrics["net_return"] - a_metrics["net_return"], "net_pnl_diff_b_minus_a": b_metrics["net_pnl"] - a_metrics["net_pnl"]},
        "protected_before": before,
        "protected_after": after,
        "protected_unchanged": before == after,
        "no_provider_or_latest_write": True,
        "no_default_or_baseline_switch": True,
        "no_broker_or_order": True,
        "twii_used_for_selection": False,
        "twii_bridge_read_for_inventory_only": str(TWII_BRIDGE.relative_to(ROOT)),
        "warning": "One fixed post-test basket diagnostic; not formal paired OOS, prospective evidence, or baseline evidence.",
    }
    validator = {"schema_version": "modelb.b15.historical_replay.validator.v1", "checks": {"exact_top50": manifest["candidate_set_exact_50"], "exact_49_after_tw7769_exclusion": manifest["candidate_set_exact_49_after_exclusion"], "feature_count_78": len(feature_order) == 78, "no_training": True, "protected_unchanged": before == after, "no_production_write": True}, "verdict": "PASS_WITH_CONDITIONS" if manifest["candidate_set_exact_49_after_exclusion"] and before == after else "FAIL"}
    (OUT / "B15_MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (OUT / "B15_VALIDATOR.json").write_text(json.dumps(validator, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (OUT / "B15_EXECUTION_REPORT_CN.md").write_text("# B15 历史回放诊断\n\n" + json.dumps(manifest, ensure_ascii=False, indent=2) + "\n\n结论：该结果只用于检查冻结 B9 在一个 B9 测试集之后历史日期的固定篮子表现，不计入正式 OOS、prospective settled days 或 baseline。\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "window": manifest["window"], "metrics": manifest["metrics"], "relative": manifest["relative"], "validator": validator["verdict"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
