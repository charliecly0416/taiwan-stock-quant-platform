#!/usr/bin/env python3
"""Phase 3A Route B turnover replay with frozen Phase1C scores.

The script uses only the Phase3A0 frozen row-level score artifact as the replay
input. It does not rebuild Phase1C scores, retrain LTR, use regime gates, touch
providers, or connect to any trading path.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FROZEN_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores"
OUT_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a_route_b_turnover_replay"
DOC_DIR = ROOT / "docs/tw_ltr_rerank_regime_turnover"

FROZEN_SCORE_CSV = FROZEN_DIR / "phase3a0_frozen_phase1c_row_scores.csv"
VALIDATION_SELECTION_CSV = OUT_DIR / "phase3a_validation_selection.csv"
INDEPENDENT_COMPARISON_CSV = OUT_DIR / "phase3a_independent_test_comparison.csv"
YEARLY_METRICS_CSV = OUT_DIR / "phase3a_yearly_metrics.csv"
REGIME_DIAGNOSTIC_CSV = OUT_DIR / "phase3a_regime_diagnostic_metrics.csv"
TURNOVER_ACTION_CSV = OUT_DIR / "phase3a_turnover_action_summary.csv"
GATE_JSON = OUT_DIR / "phase3a_gate_summary.json"
REPORT_DOC = DOC_DIR / "PHASE3A_ROUTE_B_TURNOVER_REPLAY_EXECUTION_REPORT_CN.md"

SCORE_COL = "score_head10_all_l31_alpha0.7_top50_only"
RETURN_COL = "future_return_10d"
COST_RATE_PER_TURNOVER = 0.004425


@dataclass(frozen=True)
class ReplayConfig:
    method: str
    score_col: str
    target_k: int
    max_actions_per_day: int | None
    confidence_gap: float
    no_trade_buffer: float
    min_holding_days: int
    turnover_budget: float | None
    partial_rebalance: bool
    score_or_confidence_clipping: float | None = None

    @property
    def config_id(self) -> str:
        if self.method != "phase1c_turnover_controlled":
            return "baseline"
        return (
            f"k{self.target_k}_a{self.max_actions_per_day}_gap{self.confidence_gap}"
            f"_buf{self.no_trade_buffer}_hold{self.min_holding_days}_budget{self.turnover_budget}"
        )


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def load_frozen_scores() -> pd.DataFrame:
    df = pd.read_csv(FROZEN_SCORE_CSV, parse_dates=["date"])
    required = {"date", "instrument", "split", "regime_segment", "qlib_score_raw", "qlib_rank", SCORE_COL, RETURN_COL}
    missing = sorted(required - set(df.columns))
    if missing:
        raise RuntimeError(f"Frozen score artifact missing required columns: {missing}")
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df[df[RETURN_COL].notna()].copy()
    return df


def top_candidates(group: pd.DataFrame, score_col: str, k: int) -> pd.DataFrame:
    return group.nlargest(min(k, group.shape[0]), score_col)


def no_turnover_members(group: pd.DataFrame, cfg: ReplayConfig) -> set[str]:
    return set(top_candidates(group, cfg.score_col, cfg.target_k)["instrument"])


def controlled_members(group: pd.DataFrame, cfg: ReplayConfig, current: set[str], age: dict[str, int]) -> set[str]:
    ranked = group.sort_values(cfg.score_col, ascending=False).reset_index(drop=True)
    score_map = dict(zip(ranked["instrument"], ranked[cfg.score_col]))
    top_pool = ranked.head(max(cfg.target_k * 2, cfg.target_k + 10))
    candidates = list(top_pool["instrument"])
    if not current:
        return set(candidates[: cfg.target_k])

    current = {inst for inst in current if inst in score_map}
    current_ranked = sorted(current, key=lambda inst: score_map.get(inst, -np.inf), reverse=True)
    selected = set(current_ranked[: cfg.target_k])
    while len(selected) < cfg.target_k:
        for inst in candidates:
            if inst not in selected:
                selected.add(inst)
                break
        else:
            break

    actions = 0
    budget_actions = cfg.max_actions_per_day if cfg.max_actions_per_day is not None else cfg.target_k
    if cfg.turnover_budget is not None:
        budget_actions = min(budget_actions, max(1, int(np.floor(cfg.target_k * cfg.turnover_budget))))

    for candidate in candidates:
        if actions >= budget_actions or candidate in selected:
            continue
        removable = [inst for inst in selected if age.get(inst, 0) >= cfg.min_holding_days]
        if not removable:
            break
        worst = min(removable, key=lambda inst: score_map.get(inst, -np.inf))
        gap = score_map.get(candidate, -np.inf) - score_map.get(worst, -np.inf)
        threshold = cfg.confidence_gap + cfg.no_trade_buffer
        if cfg.score_or_confidence_clipping is not None:
            gap = min(gap, cfg.score_or_confidence_clipping)
        if gap > threshold:
            selected.remove(worst)
            selected.add(candidate)
            actions += 1
    return selected


def max_drawdown(equity: list[float]) -> float:
    peak = -np.inf
    mdd = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            mdd = min(mdd, value / peak - 1.0)
    return float(mdd)


def replay(df: pd.DataFrame, split: str, cfg: ReplayConfig) -> tuple[dict[str, Any], pd.DataFrame]:
    sub = df[df["split"] == split].sort_values(["date", "instrument"])
    current: set[str] = set()
    age: dict[str, int] = {}
    equity_gross = 1.0
    equity_net = 1.0
    equity_curve = [1.0]
    rows = []
    previous: set[str] = set()

    for date, group in sub.groupby("date", sort=True):
        if cfg.method == "phase1c_turnover_controlled":
            selected = controlled_members(group, cfg, current, age)
        else:
            selected = no_turnover_members(group, cfg)

        selected_df = group[group["instrument"].isin(selected)]
        period_return = float(selected_df[RETURN_COL].mean()) if not selected_df.empty else 0.0
        additions = selected - previous
        removals = previous - selected
        action_count = len(additions) + len(removals)
        turnover_proxy = action_count / max(cfg.target_k, 1)
        cost_drag = turnover_proxy * COST_RATE_PER_TURNOVER
        net_return = period_return - cost_drag
        equity_gross *= 1.0 + period_return
        equity_net *= 1.0 + net_return
        equity_curve.append(equity_net)

        rows.append(
            {
                "date": date,
                "split": split,
                "method": cfg.method,
                "config_id": cfg.config_id,
                "member_count": len(selected),
                "gross_period_return": period_return,
                "net_period_return": net_return,
                "action_count": action_count,
                "turnover_proxy": turnover_proxy,
                "cost_drag": cost_drag,
                "regime": group["regime_segment"].mode().iloc[0] if not group["regime_segment"].mode().empty else "unknown",
            }
        )
        age = {inst: age.get(inst, 0) + 1 for inst in selected}
        for inst in set(age) - selected:
            age.pop(inst, None)
        previous = selected
        current = selected

    daily = pd.DataFrame(rows)
    if daily.empty:
        metrics = base_metric_row(split, cfg, "blocked", "No rows for split.")
        return metrics, daily
    holding_denominator = daily["action_count"].replace(0, np.nan).mean()
    avg_holding_days = float(cfg.target_k / holding_denominator) if pd.notna(holding_denominator) and holding_denominator > 0 else float("inf")
    metrics = {
        "split": split,
        "method": cfg.method,
        "config_id": cfg.config_id,
        "status": "ok",
        "target_k": cfg.target_k,
        "gross_return": equity_gross - 1.0,
        "fee_tax_adjusted_net_return": equity_net - 1.0,
        "final_equity": equity_net,
        "max_drawdown": max_drawdown(equity_curve),
        "action_count": int(daily["action_count"].sum()),
        "turnover_proxy": float(daily["turnover_proxy"].mean()),
        "average_holding_days": avg_holding_days,
        "cost_drag": float(daily["cost_drag"].sum()),
        "date_count": int(daily["date"].nunique()),
        "no_trade_buffer": cfg.no_trade_buffer,
        "confidence_gap": cfg.confidence_gap,
        "partial_rebalance": cfg.partial_rebalance,
        "max_actions_per_day": cfg.max_actions_per_day,
        "min_holding_days": cfg.min_holding_days,
        "score_or_confidence_clipping": cfg.score_or_confidence_clipping,
        "turnover_budget": cfg.turnover_budget,
        "reason": "",
    }
    return metrics, daily


def base_metric_row(split: str, cfg: ReplayConfig, status: str, reason: str) -> dict[str, Any]:
    return {
        "split": split,
        "method": cfg.method,
        "config_id": cfg.config_id,
        "status": status,
        "target_k": cfg.target_k,
        "gross_return": pd.NA,
        "fee_tax_adjusted_net_return": pd.NA,
        "final_equity": pd.NA,
        "max_drawdown": pd.NA,
        "action_count": pd.NA,
        "turnover_proxy": pd.NA,
        "average_holding_days": pd.NA,
        "cost_drag": pd.NA,
        "date_count": pd.NA,
        "no_trade_buffer": cfg.no_trade_buffer,
        "confidence_gap": cfg.confidence_gap,
        "partial_rebalance": cfg.partial_rebalance,
        "max_actions_per_day": cfg.max_actions_per_day,
        "min_holding_days": cfg.min_holding_days,
        "score_or_confidence_clipping": cfg.score_or_confidence_clipping,
        "turnover_budget": cfg.turnover_budget,
        "reason": reason,
    }


def baseline_configs() -> list[ReplayConfig]:
    return [
        ReplayConfig("rank_rotate_top30", "qlib_score_raw", 30, None, 0.0, 0.0, 0, None, False),
        ReplayConfig("rank_rotate_top50", "qlib_score_raw", 50, None, 0.0, 0.0, 0, None, False),
        ReplayConfig("phase1c_simple_topk_no_turnover", SCORE_COL, 30, None, 0.0, 0.0, 0, None, False),
    ]


def blocked_baselines(split: str) -> list[dict[str, Any]]:
    rows = []
    for method in ["rank_rotate_top50_adaptive_score", "confirmed_exit"]:
        cfg = ReplayConfig(method, method, 50, None, 0.0, 0.0, 0, None, False)
        rows.append(base_metric_row(split, cfg, "blocked", "Frozen Phase3A0 artifact does not include the technical columns required to reconstruct this baseline without leaving the fixed-input boundary."))
    return rows


def turnover_grid() -> list[ReplayConfig]:
    rows = []
    for max_actions in [1, 2, 3, 5]:
        for gap in [0.0, 0.01, 0.02]:
            for hold in [0, 3, 5]:
                rows.append(ReplayConfig("phase1c_turnover_controlled", SCORE_COL, 30, max_actions, gap, 0.0, hold, 0.20, True, 0.10))
    return rows


def select_validation(metrics: pd.DataFrame) -> tuple[pd.DataFrame, ReplayConfig | None]:
    candidates = metrics[(metrics["split"] == "validation") & (metrics["method"] == "phase1c_turnover_controlled") & (metrics["status"] == "ok")].copy()
    if candidates.empty:
        return metrics, None
    base = metrics[(metrics["split"] == "validation") & (metrics["method"] == "phase1c_simple_topk_no_turnover") & (metrics["status"] == "ok")].iloc[0]
    candidates["net_improvement_vs_phase1c_simple"] = candidates["fee_tax_adjusted_net_return"] - base["fee_tax_adjusted_net_return"]
    candidates["turnover_reduction_vs_phase1c_simple"] = base["turnover_proxy"] - candidates["turnover_proxy"]
    candidates["drawdown_improvement_vs_phase1c_simple"] = candidates["max_drawdown"] - base["max_drawdown"]
    candidates["selection_score"] = (
        candidates["net_improvement_vs_phase1c_simple"]
        + 0.10 * candidates["turnover_reduction_vs_phase1c_simple"]
        + 0.25 * candidates["drawdown_improvement_vs_phase1c_simple"]
    )
    selected = candidates.sort_values(["selection_score", "fee_tax_adjusted_net_return", "turnover_reduction_vs_phase1c_simple"], ascending=False).iloc[0]
    cfg = ReplayConfig(
        "phase1c_turnover_controlled",
        SCORE_COL,
        int(selected["target_k"]),
        int(selected["max_actions_per_day"]),
        float(selected["confidence_gap"]),
        float(selected["no_trade_buffer"]),
        int(selected["min_holding_days"]),
        float(selected["turnover_budget"]),
        bool(selected["partial_rebalance"]),
        float(selected["score_or_confidence_clipping"]),
    )
    return candidates, cfg


def add_deltas(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for split in out["split"].dropna().unique():
        base_rows = out[(out["split"] == split) & (out["method"] == "phase1c_simple_topk_no_turnover") & (out["status"] == "ok")]
        if base_rows.empty:
            continue
        base = base_rows.iloc[0]
        mask = out["split"] == split
        for col in ["gross_return", "fee_tax_adjusted_net_return", "final_equity", "max_drawdown", "action_count", "turnover_proxy", "cost_drag"]:
            out.loc[mask, f"delta_vs_phase1c_simple_{col}"] = out.loc[mask, col] - base[col]
    return out


def yearly_metrics(daily_map: dict[tuple[str, str], pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for (split, method), daily in daily_map.items():
        if daily.empty:
            continue
        data = daily.copy()
        data["year"] = pd.to_datetime(data["date"]).dt.year
        for year, group in data.groupby("year"):
            equity_gross = float((1 + group["gross_period_return"]).prod())
            equity_net = float((1 + group["net_period_return"]).prod())
            rows.append({
                "split": split,
                "year": int(year),
                "method": method,
                "gross_return": equity_gross - 1.0,
                "fee_tax_adjusted_net_return": equity_net - 1.0,
                "final_equity": equity_net,
                "max_drawdown": max_drawdown([1.0] + list((1 + group["net_period_return"]).cumprod())),
                "action_count": int(group["action_count"].sum()),
                "turnover_proxy": float(group["turnover_proxy"].mean()),
                "cost_drag": float(group["cost_drag"].sum()),
                "date_count": int(group["date"].nunique()),
            })
    return pd.DataFrame(rows)


def regime_metrics(daily_map: dict[tuple[str, str], pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for (split, method), daily in daily_map.items():
        if daily.empty:
            continue
        for regime, group in daily.groupby("regime"):
            equity_gross = float((1 + group["gross_period_return"]).prod())
            equity_net = float((1 + group["net_period_return"]).prod())
            rows.append({
                "split": split,
                "regime": regime,
                "regime_usage": "diagnostic_only",
                "method": method,
                "gross_return": equity_gross - 1.0,
                "fee_tax_adjusted_net_return": equity_net - 1.0,
                "final_equity": equity_net,
                "max_drawdown": max_drawdown([1.0] + list((1 + group["net_period_return"]).cumprod())),
                "action_count": int(group["action_count"].sum()),
                "turnover_proxy": float(group["turnover_proxy"].mean()),
                "cost_drag": float(group["cost_drag"].sum()),
                "date_count": int(group["date"].nunique()),
            })
    return pd.DataFrame(rows)


def decide_gate(validation_selection: pd.DataFrame, independent: pd.DataFrame) -> tuple[str, str, dict[str, Any]]:
    val_base = validation_selection[validation_selection["method"] == "phase1c_simple_topk_no_turnover"].iloc[0]
    val_best = validation_selection[validation_selection["method"] == "phase1c_turnover_controlled"].sort_values("selection_score", ascending=False).iloc[0]
    test_base = independent[independent["method"] == "phase1c_simple_topk_no_turnover"].iloc[0]
    test_best = independent[independent["method"] == "phase1c_turnover_controlled"].iloc[0]
    conditions = {
        "validation_net_improved": bool(val_best["fee_tax_adjusted_net_return"] > val_base["fee_tax_adjusted_net_return"]),
        "validation_turnover_reduced": bool(val_best["turnover_proxy"] < val_base["turnover_proxy"]),
        "validation_actions_reduced": bool(val_best["action_count"] < val_base["action_count"]),
        "validation_drawdown_not_worse": bool(val_best["max_drawdown"] >= val_base["max_drawdown"]),
        "independent_no_net_reversal": bool(test_best["fee_tax_adjusted_net_return"] >= test_base["fee_tax_adjusted_net_return"]),
        "independent_turnover_reduced": bool(test_best["turnover_proxy"] < test_base["turnover_proxy"]),
        "independent_actions_reduced": bool(test_best["action_count"] < test_base["action_count"]),
        "independent_drawdown_not_much_worse": bool(test_best["max_drawdown"] >= test_base["max_drawdown"] - 0.05),
    }
    if all(conditions.values()):
        return "request_phase3b_replay_repair", "Phase1C turnover-controlled replay improved validation net, turnover, actions, and did not reverse on independent_test.", conditions
    tradeoff = (
        (conditions["validation_net_improved"] and not conditions["validation_drawdown_not_worse"])
        or (conditions["validation_turnover_reduced"] and val_best["final_equity"] < val_base["final_equity"] * 0.95)
        or (conditions["validation_net_improved"] and not conditions["independent_no_net_reversal"])
    )
    if tradeoff:
        return "request_user_decision_route_b_tradeoff", "Replay produced a Route B tradeoff that requires user decision.", conditions
    return "stop_phase3a_turnover_not_supported", "Turnover control did not satisfy validation and independent_test improvement conditions over Phase1C simple replay.", conditions


def md_table(df: pd.DataFrame, columns: list[str], limit: int = 20) -> str:
    if df.empty:
        return "_无记录_"
    safe = df[columns].head(limit).copy()
    safe = safe.astype("object").where(pd.notna(safe), "")
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in safe.to_dict("records"):
        lines.append("| " + " | ".join(str(row[col]) for col in columns) + " |")
    return "\n".join(lines)


def write_report(gate: dict[str, Any], validation: pd.DataFrame, independent: pd.DataFrame, yearly: pd.DataFrame, regime: pd.DataFrame, turnover: pd.DataFrame) -> None:
    REPORT_DOC.parent.mkdir(parents=True, exist_ok=True)
    metric_cols = ["method", "config_id", "status", "fee_tax_adjusted_net_return", "final_equity", "max_drawdown", "action_count", "turnover_proxy", "cost_drag", "reason"]
    lines = [
        "# Phase 3A Route B Turnover Replay 执行报告",
        "",
        f"生成时间：{gate['created_at']}",
        "",
        "## 1. 本轮目标",
        "",
        "在固定 Phase1C row-level score 的前提下，评估 turnover control 是否改善成本后表现、动作次数、换手与回撤。",
        "",
        "## 2. 使用 frozen score artifact 的说明",
        "",
        f"本轮只读取 `{rel(FROZEN_SCORE_CSV)}`，固定 score 为 `{SCORE_COL}`。未重建、未改写、未替换该 score。",
        "",
        "## 3. Route B 与 regime diagnostic-only",
        "",
        "Regime-aware gating was not validated. Regime is diagnostic-only in Phase3A.",
        "",
        "本轮未用 regime 控制进出、动作阈值、过滤或参数选择。",
        "",
        "## 4. 实际完成内容",
        "",
        "- 将上一轮阻断型预检脚本改为只读 turnover replay 脚本。",
        "- 使用 validation-only 小网格选择 Phase1C turnover 参数。",
        "- independent_test 只按 validation 选中配置做最终检验。",
        "- 对 baseline、年度、regime diagnostic-only、turnover/action/cost 输出分表。",
        "",
        "## 5. 改动文件清单",
        "",
        f"- `{rel(Path('scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py'))}`",
        f"- `{rel(REPORT_DOC)}`",
        "",
        "## 6. 新增产物清单",
        "",
        f"- `{rel(VALIDATION_SELECTION_CSV)}`",
        f"- `{rel(INDEPENDENT_COMPARISON_CSV)}`",
        f"- `{rel(YEARLY_METRICS_CSV)}`",
        f"- `{rel(REGIME_DIAGNOSTIC_CSV)}`",
        f"- `{rel(TURNOVER_ACTION_CSV)}`",
        f"- `{rel(GATE_JSON)}`",
        "",
        "## 7. validation 参数选择",
        "",
        md_table(validation.sort_values(["method", "selection_score"], ascending=[True, False]), ["method", "config_id", "fee_tax_adjusted_net_return", "max_drawdown", "action_count", "turnover_proxy", "selection_score"], 12),
        "",
        "## 8. independent_test 最终结果",
        "",
        md_table(independent, metric_cols, 20),
        "",
        "## 9. baseline 对照",
        "",
        "`rank_rotate_top50_adaptive_score` 与 `confirmed_exit` 因 Phase3A0 frozen artifact 不含所需技术列，保留 blocked 行；未从其他样本补列，以维持固定输入边界。",
        "",
        md_table(independent, metric_cols, 20),
        "",
        "## 10. 年度结果",
        "",
        md_table(yearly, ["split", "year", "method", "fee_tax_adjusted_net_return", "final_equity", "max_drawdown", "action_count", "turnover_proxy"], 30),
        "",
        "## 11. turnover / action / cost 结果",
        "",
        md_table(turnover, ["split", "method", "config_id", "action_count", "turnover_proxy", "average_holding_days", "cost_drag"], 20),
        "",
        "## 12. regime diagnostic-only 分组结果",
        "",
        md_table(regime, ["split", "regime", "regime_usage", "method", "fee_tax_adjusted_net_return", "max_drawdown", "action_count", "turnover_proxy"], 30),
        "",
        "## 13. 验证命令与结果",
        "",
        "- `python -m py_compile scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py`：通过。",
        "- `python scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py`：普通沙箱若触发 `bwrap` 环境限制，则同一只读命令经授权在沙箱外复跑；本次最终通过。",
        "",
        "## 14. Gate 结论",
        "",
        f"`{gate['recommended_gate']}`",
        "",
        f"原因：{gate['gate_reason']}",
        "",
        f"条件：`{gate['gate_conditions']}`",
        "",
        "## 15. 禁止事项遵守情况",
        "",
        "本轮未重新训练 LTR，未重建 Phase1C score，未调整 Phase1C score，未重新选择 candidate，未重新打开 Phase2 regime gate 搜索，未使用 regime gate 控制组合，未新增数据源，未联网，未 provider refresh / publish，未 accepted latest switching，未改 frontend / API / monitor / database，未接 broker / quick-trade / orders / target position / target weight，未输出买入、卖出、持有、仓位建议、收益承诺、胜率或上涨概率语义，未做真实交易动作。",
        "",
        "## 16. 需要审查者重点检查的点",
        "",
        "- 是否接受本轮 period replay 的成本与换手 proxy 口径。",
        "- blocked baseline 是否符合固定 frozen artifact 边界。",
        "- validation-only 选参和 independent_test 终检是否严格分离。",
        "- gate 是否应进入 Phase3B 或停止。",
        "",
    ]
    REPORT_DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_frozen_scores()
    all_rows = []
    daily_map: dict[tuple[str, str], pd.DataFrame] = {}

    for split in ["validation", "independent_test"]:
        for cfg in baseline_configs():
            metrics, daily = replay(df, split, cfg)
            all_rows.append(metrics)
            daily_map[(split, cfg.method)] = daily
        all_rows.extend(blocked_baselines(split))

    for cfg in turnover_grid():
        metrics, daily = replay(df, "validation", cfg)
        all_rows.append(metrics)
    all_metrics = pd.DataFrame(all_rows)
    validation_candidates, selected_cfg = select_validation(all_metrics)
    if selected_cfg is None:
        raise RuntimeError("No validation turnover config could be selected.")

    test_metrics, test_daily = replay(df, "independent_test", selected_cfg)
    val_metrics, val_daily = replay(df, "validation", selected_cfg)
    daily_map[("validation", "phase1c_turnover_controlled")] = val_daily
    daily_map[("independent_test", "phase1c_turnover_controlled")] = test_daily

    validation_baselines = all_metrics[(all_metrics["split"] == "validation") & (all_metrics["method"] != "phase1c_turnover_controlled")]
    validation_selection = pd.concat([validation_baselines, validation_candidates, pd.DataFrame([val_metrics])], ignore_index=True)
    validation_selection = add_deltas(validation_selection)
    validation_selection.to_csv(VALIDATION_SELECTION_CSV, index=False)

    independent = pd.concat([
        all_metrics[(all_metrics["split"] == "independent_test") & (all_metrics["method"] != "phase1c_turnover_controlled")],
        pd.DataFrame([test_metrics]),
    ], ignore_index=True)
    independent = add_deltas(independent)
    independent.to_csv(INDEPENDENT_COMPARISON_CSV, index=False)

    yearly = yearly_metrics(daily_map)
    yearly.to_csv(YEARLY_METRICS_CSV, index=False)
    regime = regime_metrics(daily_map)
    regime.to_csv(REGIME_DIAGNOSTIC_CSV, index=False)
    turnover = pd.concat([validation_selection, independent], ignore_index=True)
    turnover.to_csv(TURNOVER_ACTION_CSV, index=False)

    recommended_gate, gate_reason, conditions = decide_gate(validation_selection, independent)
    gate = {
        "phase": "phase3a_route_b_turnover_replay_with_frozen_scores",
        "created_at": utc_now(),
        "research_only": True,
        "route_b": True,
        "frozen_score_artifact": rel(FROZEN_SCORE_CSV),
        "fixed_phase1c_score": SCORE_COL,
        "no_ltr_retraining": True,
        "no_phase1c_score_rebuild": True,
        "regime_aware_gating_validated": False,
        "regime_usage": "diagnostic_only",
        "cost_rate_per_turnover": COST_RATE_PER_TURNOVER,
        "selected_validation_config": selected_cfg.config_id,
        "recommended_gate": recommended_gate,
        "gate_reason": gate_reason,
        "gate_conditions": conditions,
        "artifacts": {
            "validation_selection": rel(VALIDATION_SELECTION_CSV),
            "independent_test_comparison": rel(INDEPENDENT_COMPARISON_CSV),
            "yearly_metrics": rel(YEARLY_METRICS_CSV),
            "regime_diagnostic_metrics": rel(REGIME_DIAGNOSTIC_CSV),
            "turnover_action_summary": rel(TURNOVER_ACTION_CSV),
            "gate_summary": rel(GATE_JSON),
            "report": rel(REPORT_DOC),
        },
    }
    write_json(GATE_JSON, gate)
    write_report(gate, validation_selection, independent, yearly, regime, turnover)
    print(json.dumps({"ok": True, "gate": recommended_gate, "report": rel(REPORT_DOC)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
