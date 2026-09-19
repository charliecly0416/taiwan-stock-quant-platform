#!/usr/bin/env python3
"""Run the existing readonly paired replay engine on the canonical-label signal artifact."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b7_canonical_label_paired_replay_v2_20260914"
B6 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b6_canonical_label_signal_artifact_v2_20260914"
B6_REVIEW = B6 / "B6_CANONICAL_INDEPENDENT_REVIEW.json"
B3 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b3_frozen_modela_oos_score_20260913"
B4 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b4_canonical_label_samples_20260914"
ENGINE = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b7_strict_paired_oos_replay_20260913/run_b7_strict_paired_oos_replay.py"
START, END = "2026-01-01", "2026-05-07"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_engine():
    spec = importlib.util.spec_from_file_location("readonly_replay_engine_canonical", ENGINE)
    mod = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(mod)
    mod.PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
    mod.START, mod.END = START, END
    return mod


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    review = json.loads(B6_REVIEW.read_text(encoding="utf-8"))
    if review.get("verdict") not in {"PASS", "PASS_WITH_CONDITIONS"}:
        raise RuntimeError(f"B6 independent review does not permit B7: {review.get('verdict')}")
    mod = load_engine()
    signals = pd.read_csv(B6 / "signals.csv", dtype={"instrument": str})
    signals["date"] = signals.date.astype(str).str[:10]; signals["instrument"] = signals.instrument.astype(str).str.upper()
    signals = signals[(signals.date >= START) & (signals.date <= END)].copy()
    labels = pd.read_parquet(B4 / "B4_CANONICAL_TEST_SAMPLE.parquet", columns=["date", "instrument", "relevance_10d_top_heavy_canonical", "b4_split"])
    labels["date"] = pd.to_datetime(labels.date).dt.strftime("%Y-%m-%d"); labels.instrument = labels.instrument.astype(str).str.upper()
    labels = labels[labels.b4_split.eq("test_2026")].copy()
    complete_label_dates = set(labels.date)
    counts = signals.groupby("date").size()
    complete_signal_dates = set(counts[counts == 50].index)
    valid_dates = sorted(complete_signal_dates & complete_label_dates)
    blocked_dates = sorted(set(pd.date_range(START, END, freq="B").strftime("%Y-%m-%d")) - set(valid_dates))
    signals = signals[signals.date.isin(valid_dates)].copy()
    a = pd.read_parquet(B3 / "MODEL_A_FROZEN_OOS_SCORE.parquet", columns=["date", "instrument", "raw_score", "qlib_rank"])
    a["date"] = pd.to_datetime(a.date).dt.strftime("%Y-%m-%d"); a.instrument = a.instrument.astype(str).str.upper(); a = a.rename(columns={"raw_score": "a_score", "qlib_rank": "full_rank"})
    sig = signals.merge(a, on=["date", "instrument"], how="left", validate="one_to_one")
    if sig.a_score.isna().any() or sig.full_rank.isna().any(): raise RuntimeError("missing Model A score/rank")
    all_rank = pd.read_parquet(B3 / "MODEL_A_FROZEN_OOS_SCORE.parquet", columns=["date", "instrument", "qlib_rank"])
    all_rank["date"] = pd.to_datetime(all_rank.date).dt.strftime("%Y-%m-%d"); all_rank.instrument = all_rank.instrument.astype(str).str.upper()
    rank_lookup = {d: {str(r.instrument): int(r.qlib_rank) for r in g.itertuples(index=False)} for d, g in all_rank.groupby("date")}
    prices = mod.Prices(set(sig.instrument))
    a_summary, a_actions, a_nav = mod.replay(sig, prices, "a_score", "A_ONLY", rank_lookup)
    b_summary, b_actions, b_nav = mod.replay(sig, prices, "buy_score", "A_PLUS_B", rank_lookup)
    pd.DataFrame(a_actions).to_csv(OUT / "A_ONLY_actions.csv", index=False)
    pd.DataFrame(b_actions).to_csv(OUT / "A_PLUS_B_actions.csv", index=False)
    pd.DataFrame(a_nav).to_csv(OUT / "A_ONLY_daily_ledger.csv", index=False)
    pd.DataFrame(b_nav).to_csv(OUT / "A_PLUS_B_daily_ledger.csv", index=False)
    paired = pd.DataFrame({"date": valid_dates, "rows": [50] * len(valid_dates), "paired_status": ["PASS"] * len(valid_dates)})
    paired.to_csv(OUT / "paired_date_audit.csv", index=False)
    pd.DataFrame({"date": blocked_dates, "status": ["BLOCKED_NO_COMPLETE_TOP50"] * len(blocked_dates)}).to_csv(OUT / "blocked_date_audit.csv", index=False)
    rank = sig.merge(labels, on=["date", "instrument"], how="left", validate="one_to_one")
    if rank.relevance_10d_top_heavy_canonical.isna().any():
        raise RuntimeError("paired replay includes a date/instrument without canonical test label")
    rank_rows = []
    for day, g in rank.groupby("date"):
        y = g.relevance_10d_top_heavy_canonical.astype(float).to_numpy()
        for method, col in [("A_ONLY", "a_score"), ("A_PLUS_B", "buy_score")]:
            s = g[col].astype(float).to_numpy(); order = sorted(range(len(s)), key=lambda i: (-s[i], g.instrument.iloc[i])); ordered = y[order]
            def dc(v, cutoff): return sum((2 ** v[i] - 1) / __import__("math").log2(i + 2) for i in range(min(cutoff, len(v))))
            vals = {"date": day, "method": method, "rows": len(g), "ndcg_at_10": dc(ordered, 10) / max(dc(sorted(y, reverse=True), 10), 1e-12)}
            vals["ndcg_at_30"] = dc(ordered, 30) / max(dc(sorted(y, reverse=True), 30), 1e-12)
            vals["ndcg_at_50"] = dc(ordered, 50) / max(dc(sorted(y, reverse=True), 50), 1e-12)
            rank_rows.append(vals)
    pd.DataFrame(rank_rows).to_csv(OUT / "rank_metrics_daily.csv", index=False)
    rel = {"net_return_diff_b_minus_a": b_summary["net_return"] - a_summary["net_return"], "max_drawdown_diff_b_minus_a": b_summary["max_drawdown"] - a_summary["max_drawdown"], "turnover_diff_b_minus_a": b_summary["turnover"] - a_summary["turnover"], "fee_tax_diff_b_minus_a": b_summary["fee_tax"] - a_summary["fee_tax"]}
    manifest = {"schema_version": "modelb.b7.canonical_label.paired_replay.v1", "status": "EXECUTED_AWAITING_INDEPENDENT_REVIEW", "research_only": True, "diagnostic_only": True, "production_allowed": False, "window": [START, END], "eligible_paired_days": len(valid_dates), "blocked_days": len(blocked_dates), "blocked_policy": "exclude incomplete 50/50 dates; no fill/truncation", "execution": "same readonly B7 engine: next_open, fee=.001425, sell_tax=.003, lot=10, target_holdings=10", "control": a_summary, "treatment": b_summary, "relative": rel, "rank_metrics_mean": pd.DataFrame(rank_rows).groupby("method")[["ndcg_at_10", "ndcg_at_30", "ndcg_at_50"]].mean().reset_index().to_dict("records"), "upstream_hashes": {"b6_manifest": sha256(B6 / "manifest.json"), "b6_review": sha256(B6_REVIEW), "b6_signals": sha256(B6 / "signals.csv"), "b3_score": sha256(B3 / "MODEL_A_FROZEN_OOS_SCORE.parquet"), "b4_manifest": sha256(B4 / "B4_CANONICAL_EXECUTOR_MANIFEST.json"), "engine": sha256(ENGINE)}, "no_default_or_latest_switch": True, "no_baseline_admission": True, "no_broker_or_order": True}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    (OUT / "B7_CANONICAL_EXECUTION_REPORT_CN.md").write_text(f"# B7 canonical-label paired replay\n\n- 状态：`{manifest['status']}`。\n- 完整 paired 日期：`{len(valid_dates)}`；阻断日期：`{len(blocked_dates)}`。\n- A-only 与 A+B 使用同一 Model A、Top50、next_open、费用、税费和持仓规则。\n- 不完整日期不补行、不截断、不替代。\n- 仅为 diagnostic-only，未进入 baseline/latest/default。\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "eligible_paired_days": len(valid_dates), "blocked_days": len(blocked_dates), "control": a_summary, "treatment": b_summary, "relative": rel}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
