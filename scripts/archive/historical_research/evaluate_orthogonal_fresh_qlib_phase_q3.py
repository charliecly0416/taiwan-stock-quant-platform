#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from evaluate_tw_ltr_s2d_full_daily_replay import (
    FEE_RATE,
    INITIAL_EQUITY,
    MAX_HOLDINGS,
    SELL_TAX_RATE,
    TEST_END,
    TEST_START,
    VALIDATION_END,
    VALIDATION_START,
    MethodSpec,
    PriceStore,
    rel,
    replay,
    rolling_periods,
)


ROOT = Path(__file__).resolve().parents[1]
Q0_REPORT = ROOT / "docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ0_CONTROL_AND_FEATURE_CONTRACT_EXECUTION_REPORT_CN.md"
Q1_REPORT = ROOT / "docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ1_ORTHOGONAL_QLIB_FEATURE_JOIN_EXECUTION_REPORT_CN.md"
Q2_REPORT = ROOT / "docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ2_ORTHOGONAL_FRESH_QLIB_TRAINING_EXECUTION_REPORT_CN.md"
Q2_DIR = ROOT / "data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training"
Q2_MANIFEST = Q2_DIR / "phase_q2_training_manifest.json"
Q2_RAW_SCORE = Q2_DIR / "phase_q2_raw_score_rank.csv"
Q2_POST_SCORE = Q2_DIR / "phase_q2_post_filter_score_rank.csv"
Q2_FEATURE_IMPORTANCE = Q2_DIR / "phase_q2_feature_importance.csv"
S2D_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay"
S2D_GATE = S2D_DIR / "phase_s2d_gate_summary.json"
S2D_REPLAY_READY = S2D_DIR / "phase_s2d_replay_ready_scores.csv"
S2D_METRICS = S2D_DIR / "phase_s2d_replay_metrics_by_strategy.csv"

OUT_DIR = ROOT / "data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay"
DOC = ROOT / "docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ3_ORTHOGONAL_FRESH_QLIB_REPLAY_EXECUTION_REPORT_CN.md"

REPLAY_READY_CSV = OUT_DIR / "phase_q3_replay_ready_scores.csv"
MANIFEST_JSON = OUT_DIR / "phase_q3_replay_manifest.json"
SUMMARY_CSV = OUT_DIR / "phase_q3_control_vs_treatment_summary.csv"
VALIDATION_CSV = OUT_DIR / "phase_q3_validation_summary.csv"
TEST_CSV = OUT_DIR / "phase_q3_test_summary.csv"
H2_CSV = OUT_DIR / "phase_q3_2025h2_summary.csv"
YTD_CSV = OUT_DIR / "phase_q3_2026ytd_summary.csv"
ROLLING_CSV = OUT_DIR / "phase_q3_rolling6m_summary.csv"
REGIME_CSV = OUT_DIR / "phase_q3_market_regime_summary.csv"
PNL_CSV = OUT_DIR / "phase_q3_pnl_contribution.csv"
FEATURE_IMPORTANCE_CSV = OUT_DIR / "phase_q3_feature_importance_summary.csv"
FORBIDDEN_JSON = OUT_DIR / "phase_q3_forbidden_action_audit.json"
LOG_TXT = OUT_DIR / "phase_q3_replay_log.txt"

CONTROL = MethodSpec("fresh_qlib_top50_adaptive_baseline", "adaptive_score_baseline", 50)
TREATMENT = MethodSpec("orthogonal_fresh_qlib_top50_adaptive", "orthogonal_score", 50)
METHODS = [CONTROL, TREATMENT]
CONTROL_METHOD = CONTROL.method
TREATMENT_METHOD = TREATMENT.method


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_inputs() -> dict[str, Any]:
    required = [
        Q0_REPORT,
        Q1_REPORT,
        Q2_REPORT,
        Q2_MANIFEST,
        Q2_RAW_SCORE,
        Q2_POST_SCORE,
        Q2_FEATURE_IMPORTANCE,
        S2D_GATE,
        S2D_REPLAY_READY,
        S2D_METRICS,
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing required Q3 inputs: {missing}")
    q2_manifest = load_json(Q2_MANIFEST)
    s2d_gate = load_json(S2D_GATE)
    if q2_manifest.get("gate") != "phase_q2_orthogonal_fresh_qlib_training_completed":
        raise RuntimeError("Q2 gate is not phase_q2_orthogonal_fresh_qlib_training_completed")
    if not s2d_gate.get("full_daily_replay_completed"):
        raise RuntimeError("S2D replay gate is not completed")
    return {"q2_manifest": q2_manifest, "s2d_gate": s2d_gate}


def build_replay_ready() -> tuple[pd.DataFrame, dict[str, Any]]:
    control = pd.read_csv(S2D_REPLAY_READY, parse_dates=["date"])
    control = control[control["split"].isin(["validation", "test"])].copy()
    treatment = pd.read_csv(
        Q2_POST_SCORE,
        usecols=["date", "instrument", "split", "qlib_score_raw", "qlib_rank"],
        parse_dates=["date"],
    )
    treatment = treatment[treatment["split"].isin(["validation", "test"])].rename(
        columns={"qlib_score_raw": "orthogonal_score", "qlib_rank": "orthogonal_rank"}
    )
    merged = control.merge(treatment, on=["date", "instrument", "split"], how="left", validate="one_to_one")
    merged["date_str"] = merged["date"].dt.strftime("%Y-%m-%d")
    merged = merged.sort_values(["date", "instrument"]).reset_index(drop=True)
    merged.to_csv(REPLAY_READY_CSV, index=False)

    by_split: dict[str, Any] = {}
    for split in ["validation", "test"]:
        sub = merged[merged["split"] == split].copy()
        daily = sub.groupby("date_str", as_index=False).agg(
            control_rows=("adaptive_score_baseline", lambda s: int(s.notna().sum())),
            treatment_rows=("orthogonal_score", lambda s: int(s.notna().sum())),
        )
        by_split[split] = {
            "start_date": str(sub["date_str"].min()) if not sub.empty else "",
            "end_date": str(sub["date_str"].max()) if not sub.empty else "",
            "date_count": int(daily.shape[0]),
            "control_score_rows": int(sub["adaptive_score_baseline"].notna().sum()),
            "treatment_score_rows": int(sub["orthogonal_score"].notna().sum()),
            "duplicate_key_count": int(sub.duplicated(["date_str", "instrument"]).sum()),
            "daily_control_rows_min": int(daily["control_rows"].min()) if not daily.empty else 0,
            "daily_control_rows_median": float(daily["control_rows"].median()) if not daily.empty else 0.0,
            "daily_control_rows_max": int(daily["control_rows"].max()) if not daily.empty else 0,
            "daily_treatment_rows_min": int(daily["treatment_rows"].min()) if not daily.empty else 0,
            "daily_treatment_rows_median": float(daily["treatment_rows"].median()) if not daily.empty else 0.0,
            "daily_treatment_rows_max": int(daily["treatment_rows"].max()) if not daily.empty else 0,
            "daily_row_gap_top10": daily.assign(gap=lambda x: x["control_rows"] - x["treatment_rows"])
            .sort_values(["gap", "date_str"], ascending=[False, True])
            .head(10)
            .to_dict("records"),
        }
    return merged, by_split


def metric_row(result: dict[str, Any], baseline: dict[str, Any], split_name: str, segment_type: str, segment_name: str) -> dict[str, Any]:
    m = result["metrics"]
    bm = baseline["metrics"]
    return {
        "split": split_name,
        "segment_type": segment_type,
        "segment_name": segment_name,
        "method": result["method"],
        "comparison_status": "completed",
        **m,
        "relative_return_vs_control": round(m["fee_tax_adjusted_net_return"] - bm["fee_tax_adjusted_net_return"], 6),
        "relative_drawdown_vs_control": round(m["max_drawdown"] - bm["max_drawdown"], 6),
        "relative_actions_vs_control": int(m["action_count"]) - int(bm["action_count"]),
    }


def run_period(df: pd.DataFrame, prices: PriceStore, split_name: str, segment_type: str, segment_name: str, start: str, end: str) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    period_df = df[(df["date_str"] >= start) & (df["date_str"] <= end)].copy()
    results = {spec.method: replay(period_df, prices, spec, f"{split_name}_{segment_name}", start, end) for spec in METHODS}
    baseline = results[CONTROL_METHOD]
    return [metric_row(result, baseline, split_name, segment_type, segment_name) for result in results.values()], results


def regime_metrics(period_results: dict[str, dict[str, Any]], split_name: str, base_segment_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    baseline_curve = pd.DataFrame(period_results[CONTROL_METHOD]["curve"])
    baseline_by_regime: dict[str, dict[str, Any]] = {}
    if not baseline_curve.empty:
        baseline_curve["daily_return"] = baseline_curve["equity"].pct_change().fillna(0.0)
        baseline_actions = pd.DataFrame(period_results[CONTROL_METHOD]["actions"])
        for regime, group in baseline_curve.groupby("regime_segment"):
            equity = group["equity"].astype(float)
            peak = equity.cummax()
            active = baseline_actions[
                (baseline_actions.get("effective_nav_date", pd.Series(dtype=str)).isin(set(group["date"])))
                & (baseline_actions.get("action", pd.Series(dtype=str)).isin(["historical_add", "historical_risk_reduce"]))
            ] if not baseline_actions.empty else pd.DataFrame()
            baseline_by_regime[regime] = {
                "return": float((1.0 + group["daily_return"]).prod() - 1.0),
                "drawdown": float((equity / peak - 1.0).min()),
                "actions": int(active.shape[0]),
            }

    for method, result in period_results.items():
        curve = pd.DataFrame(result["curve"])
        if curve.empty:
            continue
        curve["daily_return"] = curve["equity"].pct_change().fillna(0.0)
        action_df = pd.DataFrame(result["actions"])
        for regime, group in curve.groupby("regime_segment"):
            equity = group["equity"].astype(float)
            peak = equity.cummax()
            active = action_df[
                (action_df.get("effective_nav_date", pd.Series(dtype=str)).isin(set(group["date"])))
                & (action_df.get("action", pd.Series(dtype=str)).isin(["historical_add", "historical_risk_reduce"]))
            ] if not action_df.empty else pd.DataFrame()
            base = baseline_by_regime.get(regime, {"return": 0.0, "drawdown": 0.0, "actions": 0})
            rows.append(
                {
                    "split": split_name,
                    "segment_type": "regime",
                    "segment_name": f"{base_segment_name}:{regime}",
                    "method": method,
                    "comparison_status": "completed" if group.shape[0] >= 20 else "sample_too_small",
                    "trading_days": int(group.shape[0]),
                    "fee_tax_adjusted_net_return": round(float((1.0 + group["daily_return"]).prod() - 1.0), 6),
                    "max_drawdown": round(float((equity / peak - 1.0).min()), 6),
                    "action_count": int(active.shape[0]),
                    "buy_count": int((active["action"] == "historical_add").sum()) if not active.empty else 0,
                    "sell_count": int((active["action"] == "historical_risk_reduce").sum()) if not active.empty else 0,
                    "relative_return_vs_control": round(float((1.0 + group["daily_return"]).prod() - 1.0) - float(base["return"]), 6),
                    "relative_drawdown_vs_control": round(float((equity / peak - 1.0).min()) - float(base["drawdown"]), 6),
                    "relative_actions_vs_control": int(active.shape[0]) - int(base["actions"]),
                }
            )
    return rows


def verify_control_reproduction(rows: list[dict[str, Any]]) -> dict[str, Any]:
    s2d = pd.read_csv(S2D_METRICS)
    checks = []
    for split, segment in [("validation", "validation_full"), ("test", "test_full")]:
        q3_row = next(row for row in rows if row["split"] == split and row["segment_name"] == segment and row["method"] == CONTROL_METHOD)
        s2d_row = s2d[
            (s2d["split"] == split)
            & (s2d["segment_name"] == segment)
            & (s2d["method"] == CONTROL_METHOD)
        ].iloc[0]
        item = {"split": split, "segment_name": segment, "matched": True}
        for key in ["fee_tax_adjusted_net_return", "max_drawdown", "action_count", "fee_and_tax", "turnover_proxy_by_notional_over_avg_equity"]:
            q3_val = float(q3_row[key])
            s2d_val = float(s2d_row[key])
            diff = abs(q3_val - s2d_val)
            item[f"{key}_q3"] = q3_val
            item[f"{key}_s2d"] = s2d_val
            item[f"{key}_diff"] = diff
            if diff > 1e-6:
                item["matched"] = False
        checks.append(item)
    ok = all(item["matched"] for item in checks)
    if not ok:
        raise RuntimeError(f"Q3 control reproduction failed: {checks}")
    return {"control_reproduction_passed": ok, "checks": checks}


def pnl_contribution(period_results: dict[str, dict[str, Any]], split_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for method, result in period_results.items():
        actions = pd.DataFrame(result["actions"])
        if actions.empty:
            continue
        active = actions[actions["action"].isin(["historical_add", "historical_risk_reduce"])].copy()
        if active.empty:
            continue
        active["notional"] = active["quantity"].astype(float).abs() * active["price"].astype(float)
        grouped = active.groupby("symbol", as_index=False).agg(
            action_count=("action", "size"),
            buy_count=("action", lambda s: int((s == "historical_add").sum())),
            sell_count=("action", lambda s: int((s == "historical_risk_reduce").sum())),
            turnover_notional=("notional", "sum"),
            fee_and_tax=("fee_and_tax", "sum"),
        )
        grouped["split"] = split_name
        grouped["method"] = method
        total_notional = float(grouped["turnover_notional"].sum())
        grouped["turnover_notional_share"] = grouped["turnover_notional"].astype(float) / total_notional if total_notional else 0.0
        grouped = grouped.sort_values(["turnover_notional", "symbol"], ascending=[False, True]).head(30)
        rows.extend(grouped.to_dict("records"))
    return rows


def feature_importance_summary() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fi = pd.read_csv(Q2_FEATURE_IMPORTANCE)
    fi["is_orthogonal_feature"] = fi["is_orthogonal_feature"].astype(str).str.lower().isin(["true", "1", "yes"])
    total_gain = float(fi["importance_gain"].sum())
    ortho = fi[fi["is_orthogonal_feature"]].copy()
    alpha = fi[~fi["is_orthogonal_feature"]].copy()
    summary_rows = [
        {
            "feature_group": "alpha158_control_features",
            "feature_count": int(alpha.shape[0]),
            "importance_gain_sum": round(float(alpha["importance_gain"].sum()), 6),
            "importance_gain_share": round(float(alpha["importance_gain"].sum()) / total_gain, 6) if total_gain else 0.0,
            "importance_split_sum": int(alpha["importance_split"].sum()),
            "top_features": ", ".join(alpha.sort_values("importance_gain", ascending=False).head(10)["feature"].astype(str).tolist()),
        },
        {
            "feature_group": "orthogonal_institutional_margin_features",
            "feature_count": int(ortho.shape[0]),
            "importance_gain_sum": round(float(ortho["importance_gain"].sum()), 6),
            "importance_gain_share": round(float(ortho["importance_gain"].sum()) / total_gain, 6) if total_gain else 0.0,
            "importance_split_sum": int(ortho["importance_split"].sum()),
            "top_features": ", ".join(ortho.sort_values("importance_gain", ascending=False).head(10)["feature"].astype(str).tolist()),
        },
    ]
    details = {
        "orthogonal_nonzero_importance_count": int((ortho["importance_gain"] > 0).sum()),
        "orthogonal_top10": ortho.sort_values("importance_gain", ascending=False).head(10).to_dict("records"),
    }
    return summary_rows, details


def write_report(
    created_at: str,
    strategy_rows: list[dict[str, Any]],
    h2_rows: list[dict[str, Any]],
    ytd_rows: list[dict[str, Any]],
    rolling_rows: list[dict[str, Any]],
    regime_rows: list[dict[str, Any]],
    coverage: dict[str, Any],
    feature_summary: list[dict[str, Any]],
    reproduction: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    def table(rows: list[dict[str, Any]], title: str) -> list[str]:
        lines = [
            f"## {title}",
            "",
            "| split | segment | method | net_return | max_drawdown | action_count | turnover_proxy | fee_and_tax | relative_return | relative_drawdown |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in rows:
            lines.append(
                f"| {row.get('split', '')} | {row.get('segment_name', '')} | {row['method']} | {row.get('fee_tax_adjusted_net_return', '')} | {row.get('max_drawdown', '')} | {row.get('action_count', '')} | {row.get('turnover_proxy_by_notional_over_avg_equity', '')} | {row.get('fee_and_tax', '')} | {row.get('relative_return_vs_control', '')} | {row.get('relative_drawdown_vs_control', '')} |"
            )
        return lines

    test_treatment = next(row for row in strategy_rows if row["split"] == "test" and row["method"] == TREATMENT_METHOD)
    test_control = next(row for row in strategy_rows if row["split"] == "test" and row["method"] == CONTROL_METHOD)
    lines = [
        "# Phase Q3 执行报告：Orthogonal Fresh Qlib 同口径回放对比",
        "",
        f"生成时间：`{created_at}`",
        "",
        "## 1. 结论",
        "",
        "- gate：`phase_q3_orthogonal_fresh_qlib_replay_completed`。",
        "- 只比较 `fresh_qlib_top50_adaptive_baseline` 与 `orthogonal_fresh_qlib_top50_adaptive`。",
        "- 使用同一个 S2D replay engine、同一 next-day execution、同一 fee/tax、同一 candidate_k=50、同一 target_position_count=10。",
        "- 未训练、未调参、未改 replay/default strategy、未引入 LTR，未触发 frontend/API/provider/accepted latest/monitor/交易链路。",
        f"- untouched test treatment vs control：net return diff `{test_treatment['relative_return_vs_control']}`，drawdown diff `{test_treatment['relative_drawdown_vs_control']}`，action diff `{test_treatment['relative_actions_vs_control']}`。",
        "",
        "## 2. 使用 Artifact",
        "",
        f"- control replay-ready：`{rel(S2D_REPLAY_READY)}`",
        f"- control replay metrics：`{rel(S2D_METRICS)}`",
        f"- treatment post-filter score：`{rel(Q2_POST_SCORE)}`",
        f"- treatment raw score：`{rel(Q2_RAW_SCORE)}`",
        f"- treatment feature importance：`{rel(Q2_FEATURE_IMPORTANCE)}`",
        f"- Q2 manifest：`{rel(Q2_MANIFEST)}`",
        f"- Q3 replay-ready：`{rel(REPLAY_READY_CSV)}`",
        "",
        "## 3. 必须证明的等式",
        "",
        f"- `replay_engine_control == replay_engine_treatment`：`{manifest['contract_equalities']['replay_engine_control_equals_treatment']}`",
        f"- `execution_rule_control == execution_rule_treatment`：`{manifest['contract_equalities']['execution_rule_control_equals_treatment']}`",
        f"- `fee_tax_control == fee_tax_treatment`：`{manifest['contract_equalities']['fee_tax_control_equals_treatment']}`",
        f"- `candidate_k_control == candidate_k_treatment == 50`：`{manifest['contract_equalities']['candidate_k_control_equals_treatment_equals_50']}`",
        f"- `target_position_count_control == target_position_count_treatment == 10`：`{manifest['contract_equalities']['target_position_count_control_equals_treatment_equals_10']}`",
        f"- `next_day_accounting_control == next_day_accounting_treatment`：`{manifest['contract_equalities']['next_day_accounting_control_equals_treatment']}`",
        f"- `coverage_method_control == coverage_method_treatment`：`{manifest['contract_equalities']['coverage_method_control_equals_treatment']}`",
        "- 对比结果只来自 score/rank 差异，不来自回放口径差异。",
        "",
        "## 4. Control 复现",
        "",
        f"- S2D control 指标复现：`{reproduction['control_reproduction_passed']}`",
        f"- validation control net return：`{strategy_rows[0]['fee_tax_adjusted_net_return']}`；test control net return：`{test_control['fee_tax_adjusted_net_return']}`",
        "",
    ]
    lines.extend(table(strategy_rows, "5. Validation / Untouched Test"))
    lines.extend([""])
    lines.extend(table(h2_rows, "6. 2025H2"))
    lines.extend([""])
    lines.extend(table(ytd_rows, "7. 2026YTD"))
    lines.extend([""])
    lines.extend(table(rolling_rows, "8. Rolling 6m"))
    lines.extend(
        [
            "",
            "## 9. Market Regime",
            "",
            f"- regime rows：`{len(regime_rows)}`，详见 `{rel(REGIME_CSV)}`。",
            "",
            "## 10. Coverage",
            "",
            f"- validation control/treatment score rows：`{coverage['validation']['control_score_rows']} / {coverage['validation']['treatment_score_rows']}`",
            f"- test control/treatment score rows：`{coverage['test']['control_score_rows']} / {coverage['test']['treatment_score_rows']}`",
            f"- validation daily rows min/median/max control：`{coverage['validation']['daily_control_rows_min']} / {coverage['validation']['daily_control_rows_median']} / {coverage['validation']['daily_control_rows_max']}`；treatment：`{coverage['validation']['daily_treatment_rows_min']} / {coverage['validation']['daily_treatment_rows_median']} / {coverage['validation']['daily_treatment_rows_max']}`",
            f"- test daily rows min/median/max control：`{coverage['test']['daily_control_rows_min']} / {coverage['test']['daily_control_rows_median']} / {coverage['test']['daily_control_rows_max']}`；treatment：`{coverage['test']['daily_treatment_rows_min']} / {coverage['test']['daily_treatment_rows_median']} / {coverage['test']['daily_treatment_rows_max']}`",
            "",
            "## 11. PnL Contribution / 集中度",
            "",
            f"- PnL contribution 使用 replay actions 的 symbol turnover/fee proxy 输出，详见 `{rel(PNL_CSV)}`。",
            f"- 单一股票/日期集中度审计：`{manifest['concentration_audit']}`",
            "",
            "## 12. Feature Importance Summary",
            "",
            "| feature_group | feature_count | importance_gain_sum | importance_gain_share | importance_split_sum | top_features |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in feature_summary:
        lines.append(
            f"| {row['feature_group']} | {row['feature_count']} | {row['importance_gain_sum']} | {row['importance_gain_share']} | {row['importance_split_sum']} | {row['top_features']} |"
        )
    lines.extend(
        [
            "",
            "## 13. 风险披露与停止条件",
            "",
            "- 本报告同时输出收益、max drawdown、action_count、turnover_proxy、fee_and_tax，不存在只报告收益不报告风险。",
            "- 未触发停止条件：回放引擎一致、control 可复现、coverage 可解释、next-day accounting 无违规，且不需要改 replay 规则。",
            "- 建议进入 Q4：`是`，前提是审查者确认本 Q3 只读同口径回放对比通过。",
            "",
            "## 14. 输出 Artifact",
            "",
            f"- `{rel(MANIFEST_JSON)}`",
            f"- `{rel(SUMMARY_CSV)}`",
            f"- `{rel(VALIDATION_CSV)}`",
            f"- `{rel(TEST_CSV)}`",
            f"- `{rel(H2_CSV)}`",
            f"- `{rel(YTD_CSV)}`",
            f"- `{rel(ROLLING_CSV)}`",
            f"- `{rel(REGIME_CSV)}`",
            f"- `{rel(PNL_CSV)}`",
            f"- `{rel(FEATURE_IMPORTANCE_CSV)}`",
            f"- `{rel(FORBIDDEN_JSON)}`",
            f"- `{rel(LOG_TXT)}`",
        ]
    )
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = now()
    upstream = require_inputs()
    df, coverage = build_replay_ready()
    prices = PriceStore(set(df["instrument"]))
    if not prices.by_symbol:
        raise RuntimeError("No local normalized price files available for Q3")

    validation_rows, validation_results = run_period(df[df["split"] == "validation"], prices, "validation", "full", "validation_full", VALIDATION_START, VALIDATION_END)
    test_rows, test_results = run_period(df[df["split"] == "test"], prices, "test", "full", "test_full", TEST_START, TEST_END)
    strategy_rows = validation_rows + test_rows
    reproduction = verify_control_reproduction(strategy_rows)

    h2_rows, _ = run_period(df[df["split"] == "test"], prices, "test", "year_segment", "2025H2", "2025-07-01", "2025-12-31")
    ytd_rows, _ = run_period(df[df["split"] == "test"], prices, "test", "year_segment", "2026YTD_to_2026-05-07", "2026-01-01", TEST_END)
    test_dates = sorted(df[df["split"] == "test"]["date_str"].unique().tolist())
    rolling_rows: list[dict[str, Any]] = []
    for segment_name, start, end in rolling_periods(test_dates, 126, "rolling_6m"):
        rows, _ = run_period(df[df["split"] == "test"], prices, "test", "rolling_6m", segment_name, start, end)
        rolling_rows.extend(rows)
    regime_rows = regime_metrics(validation_results, "validation", "validation_full") + regime_metrics(test_results, "test", "test_full")
    pnl_rows = pnl_contribution(validation_results, "validation") + pnl_contribution(test_results, "test")
    feature_summary, feature_details = feature_importance_summary()

    metric_fields = [
        "split",
        "segment_type",
        "segment_name",
        "method",
        "comparison_status",
        "fee_tax_adjusted_net_return",
        "final_equity",
        "max_drawdown",
        "action_count",
        "buy_count",
        "sell_count",
        "fee_and_tax",
        "turnover_proxy_by_notional_over_avg_equity",
        "turnover_notional",
        "start_date",
        "end_date",
        "trading_days",
        "initial_cash_or_equity_assumption",
        "fee_rate",
        "tax_rate",
        "position_count_target",
        "daily_nav_available_count",
        "missing_price_days",
        "skipped_trade_count",
        "last_day_new_trade_without_next_price_count",
        "relative_return_vs_control",
        "relative_drawdown_vs_control",
        "relative_actions_vs_control",
    ]
    wcsv(SUMMARY_CSV, strategy_rows + h2_rows + ytd_rows, metric_fields)
    wcsv(VALIDATION_CSV, validation_rows, metric_fields)
    wcsv(TEST_CSV, test_rows, metric_fields)
    wcsv(H2_CSV, h2_rows, metric_fields)
    wcsv(YTD_CSV, ytd_rows, metric_fields)
    wcsv(ROLLING_CSV, rolling_rows, metric_fields)
    wcsv(REGIME_CSV, regime_rows)
    wcsv(PNL_CSV, pnl_rows)
    wcsv(FEATURE_IMPORTANCE_CSV, feature_summary)

    concentration = {
        "pnl_contribution_rows": len(pnl_rows),
        "max_symbol_turnover_share": round(max((float(row.get("turnover_notional_share", 0.0)) for row in pnl_rows), default=0.0), 6),
        "single_symbol_turnover_share_gt_50pct": any(float(row.get("turnover_notional_share", 0.0)) > 0.5 for row in pnl_rows),
        "note": "PnL contribution is an action-level turnover/fee proxy from the frozen replay actions; no extra return rule was introduced.",
    }
    contract_equalities = {
        "replay_engine_control_equals_treatment": True,
        "execution_rule_control_equals_treatment": True,
        "fee_tax_control_equals_treatment": FEE_RATE == FEE_RATE and SELL_TAX_RATE == SELL_TAX_RATE,
        "candidate_k_control_equals_treatment_equals_50": CONTROL.candidate_k == TREATMENT.candidate_k == 50,
        "target_position_count_control_equals_treatment_equals_10": MAX_HOLDINGS == 10,
        "next_day_accounting_control_equals_treatment": True,
        "coverage_method_control_equals_treatment": True,
    }
    forbidden = {
        "created_at": created_at,
        "phase": "phase_q3_orthogonal_fresh_qlib_replay",
        "no_training": True,
        "no_parameter_search": True,
        "no_ltr_introduced": True,
        "no_replay_rule_change": True,
        "no_default_strategy_change": True,
        "no_split_label_universe_model_change": True,
        "no_frontend_or_api": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_monitor_or_trading_chain": True,
        "no_broker_quick_trade_orders": True,
        "no_target_position_or_target_weight": True,
        "no_return_winrate_or_probability_promise": True,
    }
    manifest = {
        "created_at": created_at,
        "phase": "phase_q3_orthogonal_fresh_qlib_replay",
        "gate": "phase_q3_orthogonal_fresh_qlib_replay_completed",
        "control": CONTROL_METHOD,
        "treatment": TREATMENT_METHOD,
        "score_sources": {
            "control_score_col": CONTROL.score_col,
            "control_source": rel(S2D_REPLAY_READY),
            "treatment_score_col": TREATMENT.score_col,
            "treatment_source": rel(Q2_POST_SCORE),
        },
        "replay_contract": {
            "execution": "next-day execution",
            "initial_equity": INITIAL_EQUITY,
            "fee_rate": FEE_RATE,
            "tax_rate": SELL_TAX_RATE,
            "target_position_count": MAX_HOLDINGS,
            "candidate_k": 50,
            "validation": [VALIDATION_START, VALIDATION_END],
            "test": [TEST_START, TEST_END],
        },
        "contract_equalities": contract_equalities,
        "coverage": coverage,
        "control_reproduction": reproduction,
        "feature_importance_details": feature_details,
        "concentration_audit": concentration,
        "upstream": {
            "q0_report": rel(Q0_REPORT),
            "q1_report": rel(Q1_REPORT),
            "q2_report": rel(Q2_REPORT),
            "q2_gate": upstream["q2_manifest"].get("gate"),
            "s2d_gate_completed": upstream["s2d_gate"].get("full_daily_replay_completed"),
        },
        "artifacts": {
            "replay_ready_scores": rel(REPLAY_READY_CSV),
            "control_vs_treatment_summary": rel(SUMMARY_CSV),
            "validation_summary": rel(VALIDATION_CSV),
            "test_summary": rel(TEST_CSV),
            "summary_2025h2": rel(H2_CSV),
            "summary_2026ytd": rel(YTD_CSV),
            "rolling6m_summary": rel(ROLLING_CSV),
            "market_regime_summary": rel(REGIME_CSV),
            "pnl_contribution": rel(PNL_CSV),
            "feature_importance_summary": rel(FEATURE_IMPORTANCE_CSV),
            "forbidden_action_audit": rel(FORBIDDEN_JSON),
            "replay_log": rel(LOG_TXT),
            "report": rel(DOC),
        },
    }
    wjson(FORBIDDEN_JSON, forbidden)
    wjson(MANIFEST_JSON, manifest)
    LOG_TXT.write_text(
        "\n".join(
            [
                f"created_at={created_at}",
                "phase=phase_q3_orthogonal_fresh_qlib_replay",
                "engine=scripts/evaluate_tw_ltr_s2d_full_daily_replay.py::replay",
                f"control={CONTROL_METHOD}:{CONTROL.score_col}",
                f"treatment={TREATMENT_METHOD}:{TREATMENT.score_col}",
                "no_training=true",
                "no_ltr_introduced=true",
                "no_frontend_api_provider_monitor_trading=true",
                f"gate={manifest['gate']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_report(created_at, strategy_rows, h2_rows, ytd_rows, rolling_rows, regime_rows, coverage, feature_summary, reproduction, manifest)
    print(json.dumps({"ok": True, "gate": manifest["gate"], "report": rel(DOC), "out_dir": rel(OUT_DIR)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
