#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
S2D_SCRIPT = ROOT / "scripts/evaluate_tw_ltr_s2d_full_daily_replay.py"

spec = importlib.util.spec_from_file_location("evaluate_tw_ltr_s2d_full_daily_replay", S2D_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load {S2D_SCRIPT}")
s2d = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = s2d
spec.loader.exec_module(s2d)


OLD_LTR_SCORE = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv"
FRESH_REPLAY_READY = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_replay_ready_scores.csv"
FRESH_METRICS = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_replay_metrics_by_strategy.csv"

OUT_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck"
METRICS_CSV = OUT_DIR / "phase_s2f_same_window_metrics.csv"
DAILY_NAV_CSV = OUT_DIR / "phase_s2f_same_window_daily_nav.csv"
ACTION_CSV = OUT_DIR / "phase_s2f_same_window_action_audit.csv"
COVERAGE_JSON = OUT_DIR / "phase_s2f_same_window_coverage_audit.json"
GATE_JSON = OUT_DIR / "phase_s2f_same_window_gate_summary.json"
REPORT = ROOT / "docs/tw_ltr_qlib_split_aligned_retrain/PHASES2F_OLD_VS_FRESH_SAME_WINDOW_RECHECK_REPORT_CN.md"

TEST_START = "2025-07-01"
TEST_END = "2026-05-07"

METHODS = [
    "old_qlib_new_ltr_phase1c_simple",
    "fresh_qlib_top50_adaptive_baseline",
    "fresh_ltr_simple",
    "fresh_ltr_turnover_controlled",
]

SPECS = {
    "old_qlib_new_ltr_phase1c_simple": s2d.MethodSpec(
        "old_qlib_new_ltr_phase1c_simple",
        "old_phase1c_ltr_score",
        50,
        False,
    ),
    "fresh_qlib_top50_adaptive_baseline": s2d.SPECS["fresh_qlib_top50_adaptive_baseline"],
    "fresh_ltr_simple": s2d.SPECS["fresh_ltr_simple"],
    "fresh_ltr_turnover_controlled": s2d.SPECS["fresh_ltr_turnover_controlled"],
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def load_inputs() -> pd.DataFrame:
    fresh = pd.read_csv(FRESH_REPLAY_READY, parse_dates=["date"])
    fresh["date_str"] = fresh["date"].dt.strftime("%Y-%m-%d")
    fresh = fresh[(fresh["split"] == "test") & (fresh["date_str"] >= TEST_START) & (fresh["date_str"] <= TEST_END)].copy()

    old = pd.read_csv(
        OLD_LTR_SCORE,
        usecols=[
            "date",
            "instrument",
            "split",
            "score_head10_all_l31_alpha0.7_top50_only",
            "phase1c_score_rank_by_date",
            "phase1c_top50_preserve_scope",
        ],
        parse_dates=["date"],
    )
    old["date_str"] = old["date"].dt.strftime("%Y-%m-%d")
    old = old[(old["date_str"] >= TEST_START) & (old["date_str"] <= TEST_END)].copy()
    old = old.rename(
        columns={
            "score_head10_all_l31_alpha0.7_top50_only": "old_phase1c_ltr_score",
            "phase1c_score_rank_by_date": "old_phase1c_ltr_rank",
            "split": "old_phase1c_split",
        }
    )

    merged = fresh.merge(
        old[[
            "date_str",
            "instrument",
            "old_phase1c_split",
            "old_phase1c_ltr_score",
            "old_phase1c_ltr_rank",
            "phase1c_top50_preserve_scope",
        ]],
        on=["date_str", "instrument"],
        how="outer",
        validate="one_to_one",
    )

    # Reuse fresh split/calendar and regime when available; old rows outside fresh
    # universe are retained only if they have a date in the same test window.
    merged["date"] = pd.to_datetime(merged["date_str"])
    merged["split"] = merged["split"].fillna("test")
    merged["regime_segment"] = merged["regime_segment"].fillna("unknown")
    merged = merged[(merged["date_str"] >= TEST_START) & (merged["date_str"] <= TEST_END)].copy()
    merged = merged.sort_values(["date_str", "instrument"]).reset_index(drop=True)
    return merged


def coverage(df: pd.DataFrame) -> dict[str, Any]:
    by_date = df.groupby("date_str", as_index=False).agg(
        total_rows=("instrument", "size"),
        old_ltr_rows=("old_phase1c_ltr_score", lambda s: int(s.notna().sum())),
        fresh_top50_rows=("adaptive_score_baseline", lambda s: int(s.notna().sum())),
        fresh_ltr_rows=("ltr_score", lambda s: int(s.notna().sum())),
    )
    overlap = df[
        df["old_phase1c_ltr_score"].notna()
        & df["adaptive_score_baseline"].notna()
        & df["ltr_score"].notna()
    ]
    return {
        "created_at": now(),
        "phase": "phase_s2f_old_vs_fresh_same_window_recheck",
        "test_start": TEST_START,
        "test_end": TEST_END,
        "source_old_ltr_score": rel(OLD_LTR_SCORE),
        "source_fresh_replay_ready": rel(FRESH_REPLAY_READY),
        "source_fresh_metrics": rel(FRESH_METRICS),
        "date_count": int(by_date.shape[0]),
        "row_count": int(df.shape[0]),
        "duplicate_key_count": int(df.duplicated(["date_str", "instrument"]).sum()),
        "overlap_all_three_rows": int(overlap.shape[0]),
        "daily_rows": {
            "old_ltr_min": int(by_date["old_ltr_rows"].min()) if not by_date.empty else 0,
            "old_ltr_median": float(by_date["old_ltr_rows"].median()) if not by_date.empty else 0.0,
            "old_ltr_max": int(by_date["old_ltr_rows"].max()) if not by_date.empty else 0,
            "fresh_top50_min": int(by_date["fresh_top50_rows"].min()) if not by_date.empty else 0,
            "fresh_top50_median": float(by_date["fresh_top50_rows"].median()) if not by_date.empty else 0.0,
            "fresh_top50_max": int(by_date["fresh_top50_rows"].max()) if not by_date.empty else 0,
            "fresh_ltr_min": int(by_date["fresh_ltr_rows"].min()) if not by_date.empty else 0,
            "fresh_ltr_median": float(by_date["fresh_ltr_rows"].median()) if not by_date.empty else 0.0,
            "fresh_ltr_max": int(by_date["fresh_ltr_rows"].max()) if not by_date.empty else 0,
        },
        "daily_gap_top10": by_date.assign(
            old_minus_fresh=lambda x: x["old_ltr_rows"] - x["fresh_top50_rows"]
        ).sort_values(["old_minus_fresh", "date_str"], ascending=[False, True]).head(10).to_dict("records"),
    }


def metric_row(result: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    m = result["metrics"]
    bm = baseline["metrics"]
    return {
        "period": "same_test_window",
        "start_date": TEST_START,
        "end_date": TEST_END,
        "method": result["method"],
        "comparison_status": "completed",
        **m,
        "relative_return_vs_fresh_top50_adaptive": round(m["fee_tax_adjusted_net_return"] - bm["fee_tax_adjusted_net_return"], 6),
        "relative_drawdown_vs_fresh_top50_adaptive": round(m["max_drawdown"] - bm["max_drawdown"], 6),
        "relative_actions_vs_fresh_top50_adaptive": int(m["action_count"]) - int(bm["action_count"]),
    }


def write_report(rows: list[dict[str, Any]], cov: dict[str, Any], gate: dict[str, Any]) -> None:
    old_row = next(row for row in rows if row["method"] == "old_qlib_new_ltr_phase1c_simple")
    fresh_top50 = next(row for row in rows if row["method"] == "fresh_qlib_top50_adaptive_baseline")
    lines = [
        "# Phase S2F 复核报告：旧 qlib + 新 LTR vs fresh qlib 同窗口比较",
        "",
        f"生成时间：{gate['created_at']}",
        "",
        "## 1. 复核问题",
        "",
        "用户质疑 `旧 qlib + 新 LTR simple` 的历史收益异常高，要求在同一测试区间、同一回放引擎、同一费用税费和 next-day execution 口径下，与 fresh qlib / fresh LTR 重新比较。",
        "",
        "固定测试区间：`2025-07-01..2026-05-07`。",
        "",
        "## 2. 同窗口结果",
        "",
        "| method | fee_tax_adjusted_net_return | max_drawdown | action_count | fee_and_tax | relative_return_vs_fresh_top50 | relative_drawdown_vs_fresh_top50 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['method']} | {row['fee_tax_adjusted_net_return']} | {row['max_drawdown']} | {row['action_count']} | {row['fee_and_tax']} | {row['relative_return_vs_fresh_top50_adaptive']} | {row['relative_drawdown_vs_fresh_top50_adaptive']} |"
        )
    lines.extend(
        [
            "",
            "## 3. 直接判断",
            "",
            f"- `old_qlib_new_ltr_phase1c_simple` 同窗口收益为 `{old_row['fee_tax_adjusted_net_return']}`。",
            f"- `fresh_qlib_top50_adaptive_baseline` 同窗口收益为 `{fresh_top50['fee_tax_adjusted_net_return']}`。",
            f"- 旧 LTR 相对 fresh top50 差值为 `{old_row['relative_return_vs_fresh_top50_adaptive']}`。",
            "",
            "若旧 LTR 没有显著领先，则此前 `+355%` 级别结果不能作为同窗口优势证据；若仍显著领先，则需要继续做持仓贡献和异常价格审计。",
            "",
            "## 4. Coverage 审计",
            "",
            f"- 日期数：`{cov['date_count']}`",
            f"- old LTR daily rows min/median/max：`{cov['daily_rows']['old_ltr_min']} / {cov['daily_rows']['old_ltr_median']} / {cov['daily_rows']['old_ltr_max']}`",
            f"- fresh top50 daily rows min/median/max：`{cov['daily_rows']['fresh_top50_min']} / {cov['daily_rows']['fresh_top50_median']} / {cov['daily_rows']['fresh_top50_max']}`",
            f"- fresh LTR daily rows min/median/max：`{cov['daily_rows']['fresh_ltr_min']} / {cov['daily_rows']['fresh_ltr_median']} / {cov['daily_rows']['fresh_ltr_max']}`",
            "",
            "## 5. 边界",
            "",
            "- 本轮不训练 qlib / LTR。",
            "- 不调参、不新增策略、不改 split / feature / label。",
            "- 不改前端/API，不触发 provider/accepted latest/monitor/交易链路。",
            "",
            "## 6. 产物",
            "",
            f"- `{rel(METRICS_CSV)}`",
            f"- `{rel(DAILY_NAV_CSV)}`",
            f"- `{rel(ACTION_CSV)}`",
            f"- `{rel(COVERAGE_JSON)}`",
            f"- `{rel(GATE_JSON)}`",
        ]
    )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_inputs()
    cov = coverage(df)
    if cov["duplicate_key_count"]:
        raise RuntimeError(f"duplicate date/instrument keys: {cov['duplicate_key_count']}")
    prices = s2d.PriceStore(set(df["instrument"].dropna().astype(str)))
    if not prices.by_symbol:
        raise RuntimeError("No price data available")

    results = {
        method: s2d.replay(df, prices, SPECS[method], "same_test_window", TEST_START, TEST_END)
        for method in METHODS
    }
    baseline = results["fresh_qlib_top50_adaptive_baseline"]
    rows = [metric_row(results[method], baseline) for method in METHODS]

    metric_fields = [
        "period",
        "start_date",
        "end_date",
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
        "trading_days",
        "initial_cash_or_equity_assumption",
        "fee_rate",
        "tax_rate",
        "position_count_target",
        "daily_nav_available_count",
        "missing_price_days",
        "skipped_trade_count",
        "last_day_new_trade_without_next_price_count",
        "relative_return_vs_fresh_top50_adaptive",
        "relative_drawdown_vs_fresh_top50_adaptive",
        "relative_actions_vs_fresh_top50_adaptive",
    ]
    write_csv(METRICS_CSV, rows, metric_fields)

    nav_rows = []
    action_rows = []
    for method, result in results.items():
        nav_rows.extend(result["curve"])
        action_rows.extend(result["actions"])
    write_csv(
        DAILY_NAV_CSV,
        nav_rows,
        ["date", "period", "method", "equity", "cash", "holding_count", "regime_segment", "missing_price_count"],
    )
    action_fields = sorted({key for row in action_rows for key in row.keys()}) if action_rows else ["method"]
    write_csv(ACTION_CSV, action_rows, action_fields)

    old_row = next(row for row in rows if row["method"] == "old_qlib_new_ltr_phase1c_simple")
    gate = {
        "created_at": now(),
        "phase": "phase_s2f_old_vs_fresh_same_window_recheck",
        "recommended_gate": "same_window_recheck_completed",
        "same_window": f"{TEST_START}..{TEST_END}",
        "old_ltr_return": old_row["fee_tax_adjusted_net_return"],
        "fresh_top50_return": baseline["metrics"]["fee_tax_adjusted_net_return"],
        "old_ltr_minus_fresh_top50": old_row["relative_return_vs_fresh_top50_adaptive"],
        "no_training": True,
        "no_parameter_search": True,
        "no_frontend_api_provider_monitor_trading": True,
        "artifacts": {
            "metrics": rel(METRICS_CSV),
            "daily_nav": rel(DAILY_NAV_CSV),
            "actions": rel(ACTION_CSV),
            "coverage": rel(COVERAGE_JSON),
            "report": rel(REPORT),
        },
    }
    write_json(COVERAGE_JSON, cov)
    write_json(GATE_JSON, gate)
    write_report(rows, cov, gate)
    print(json.dumps({"ok": True, "gate": gate["recommended_gate"], "report": rel(REPORT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
