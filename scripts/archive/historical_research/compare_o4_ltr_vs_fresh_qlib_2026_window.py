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

O4_SCORE = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_row_scores.csv"
FRESH_SCORE = ROOT / "data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv"

OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_2026_o4_vs_fresh_subwindow"
REPORT = ROOT / "docs/tw_ltr_orthogonal_features_controlled/P1_2026_O4_VS_FRESH_QLIB_SUBWINDOW_REPORT_CN.md"

START = "2026-01-01"
END = "2026-05-07"

O4_METHOD = "o4_orthogonal_ltr_top50_rerank"
FRESH_METHOD = "repaired_fresh_qlib_top50_adaptive"
O4_SCORE_COL = "phaseo4_treatment_ltr_score_top50_preserve"
FRESH_SCORE_COL = "adaptive_score_baseline"


def load_s2d():
    spec = importlib.util.spec_from_file_location("evaluate_tw_ltr_s2d_full_daily_replay", S2D_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {S2D_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def norm(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def build_o4_ready() -> pd.DataFrame:
    df = pd.read_csv(O4_SCORE, parse_dates=["date"])
    df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    df = df[(df["date_str"] >= START) & (df["date_str"] <= END)].copy()
    df["instrument"] = df["instrument"].map(norm)
    df["split"] = df.get("split", "test")
    df["regime_segment"] = df.get("regime_segment", "normal")
    df[O4_SCORE_COL] = df["phaseo4_treatment_ltr_score"].where(pd.to_numeric(df["qlib_rank"], errors="coerce") <= 50)
    keep = ["date", "date_str", "instrument", "split", "regime_segment", "qlib_rank", "phaseo4_treatment_ltr_score", O4_SCORE_COL]
    return df[keep].sort_values(["date_str", "instrument"]).reset_index(drop=True)


def build_fresh_ready() -> pd.DataFrame:
    df = pd.read_csv(FRESH_SCORE, parse_dates=["date"])
    if "date_str" not in df.columns:
        df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    df = df[(df["date_str"] >= START) & (df["date_str"] <= END)].copy()
    df["instrument"] = df["instrument"].map(norm)
    df["split"] = df.get("split", "test")
    df["regime_segment"] = df.get("regime_segment", "normal")
    keep = ["date", "date_str", "instrument", "split", "regime_segment", "qlib_rank", FRESH_SCORE_COL]
    return df[keep].sort_values(["date_str", "instrument"]).reset_index(drop=True)


def metric_row(result: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    m = result["metrics"]
    bm = baseline["metrics"]
    return {
        "window": "2026_01_01_2026_05_07",
        "method": result["method"],
        "comparison_status": "completed",
        **m,
        "relative_return_vs_fresh": round(m["fee_tax_adjusted_net_return"] - bm["fee_tax_adjusted_net_return"], 6),
        "relative_drawdown_vs_fresh": round(m["max_drawdown"] - bm["max_drawdown"], 6),
        "relative_actions_vs_fresh": int(m["action_count"]) - int(bm["action_count"]),
    }


def coverage_rows(o4: pd.DataFrame, fresh: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, df, score_col in [
        (O4_METHOD, o4.dropna(subset=[O4_SCORE_COL]), O4_SCORE_COL),
        (FRESH_METHOD, fresh, FRESH_SCORE_COL),
    ]:
        daily = df.groupby("date_str", as_index=False).agg(
            rows=("instrument", "size"),
            score_rows=(score_col, lambda s: int(s.notna().sum())),
            top50_rows=("qlib_rank", lambda s: int((pd.to_numeric(s, errors="coerce") <= 50).sum())),
        )
        rows.append(
            {
                "method": name,
                "start_date": str(df["date_str"].min()),
                "end_date": str(df["date_str"].max()),
                "date_count": int(daily.shape[0]),
                "row_count": int(df.shape[0]),
                "daily_rows_min": int(daily["rows"].min()),
                "daily_rows_median": float(daily["rows"].median()),
                "daily_rows_max": int(daily["rows"].max()),
                "score_rows": int(df[score_col].notna().sum()),
                "daily_top50_min": int(daily["top50_rows"].min()),
                "daily_top50_median": float(daily["top50_rows"].median()),
                "daily_top50_max": int(daily["top50_rows"].max()),
                "duplicate_key_count": int(df.duplicated(["date_str", "instrument"]).sum()),
            }
        )
    return rows


def accounting_rows(results: dict[str, dict[str, Any]], s2d: Any) -> list[dict[str, Any]]:
    rows = []
    for method, result in results.items():
        active = [a for a in result["actions"] if a.get("action") in {"historical_add", "historical_risk_reduce"}]
        violations = sum(1 for a in active if str(a.get("execution_date", "")) <= str(a.get("signal_date", "")))
        metrics = result["metrics"]
        rows.append(
            {
                "method": method,
                "active_action_count": len(active),
                "next_day_execution": violations == 0,
                "execution_date_not_after_signal_violations": violations,
                "fee_rate": s2d.FEE_RATE,
                "tax_rate": s2d.SELL_TAX_RATE,
                "target_position_count": s2d.MAX_HOLDINGS,
                "candidate_k": 50,
                "missing_price_days": metrics["missing_price_days"],
                "skipped_trade_count": metrics["skipped_trade_count"],
                "last_day_new_trade_without_next_price_count": metrics["last_day_new_trade_without_next_price_count"],
            }
        )
    return rows


def write_report(created_at: str, summary: list[dict[str, Any]], coverage: list[dict[str, Any]], accounting: list[dict[str, Any]]) -> None:
    fresh = next(row for row in summary if row["method"] == FRESH_METHOD)
    o4 = next(row for row in summary if row["method"] == O4_METHOD)
    lines = [
        "# 2026 子窗口只读对比：O4 Orthogonal LTR vs Repaired Fresh Qlib",
        "",
        f"生成时间：`{created_at}`",
        "",
        "## 1. 结论",
        "",
        "- 本轮只读重跑指定窗口，没有训练、调参、改 score、改规则、改前端/API/provider/accepted latest/monitor 或交易链路。",
        f"- 窗口：`{START}..{END}`，从 2026-01-01 空仓初始资金重新起跑。",
        "- 回放口径：同一 S2D replay engine、next-day execution、fee_rate `0.001425`、tax_rate `0.003`、target_position_count `10`、candidate_k `50`。",
        "- O4 treatment 只在 qlib top50 内重排；fresh qlib 使用 repaired C4 replay-ready artifact 的 `adaptive_score_baseline`。",
        "",
        "## 2. 指标",
        "",
        "| method | net_return | max_drawdown | action_count | turnover_proxy | fee_and_tax | relative_return_vs_fresh |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary:
        lines.append(
            f"| {row['method']} | {row['fee_tax_adjusted_net_return']} | {row['max_drawdown']} | {row['action_count']} | {row['turnover_proxy_by_notional_over_avg_equity']} | {row['fee_and_tax']} | {row['relative_return_vs_fresh']} |"
        )
    lines.extend(
        [
            "",
            "## 3. 对比摘要",
            "",
            f"- O4 net return：`{o4['fee_tax_adjusted_net_return']}`。",
            f"- Fresh qlib net return：`{fresh['fee_tax_adjusted_net_return']}`。",
            f"- O4 - fresh：`{o4['relative_return_vs_fresh']}`。",
            f"- O4 max drawdown：`{o4['max_drawdown']}`；fresh max drawdown：`{fresh['max_drawdown']}`。",
            f"- O4 action_count：`{o4['action_count']}`；fresh action_count：`{fresh['action_count']}`。",
            "",
            "## 4. Coverage",
            "",
            "| method | rows | dates | daily rows min/median/max | top50 min/median/max | duplicate keys |",
            "| --- | ---: | ---: | --- | --- | ---: |",
        ]
    )
    for row in coverage:
        lines.append(
            f"| {row['method']} | {row['row_count']} | {row['date_count']} | {row['daily_rows_min']}/{row['daily_rows_median']}/{row['daily_rows_max']} | {row['daily_top50_min']}/{row['daily_top50_median']}/{row['daily_top50_max']} | {row['duplicate_key_count']} |"
        )
    lines.extend(["", "## 5. Accounting", "", "| method | active_actions | next_day_execution | missing_price_days | skipped_trade_count |", "| --- | ---: | --- | ---: | ---: |"])
    for row in accounting:
        lines.append(
            f"| {row['method']} | {row['active_action_count']} | {row['next_day_execution']} | {row['missing_price_days']} | {row['skipped_trade_count']} |"
        )
    lines.extend(
        [
            "",
            "## 6. 输出 Artifact",
            "",
            f"- `{rel(OUT / 'summary.csv')}`",
            f"- `{rel(OUT / 'daily_nav.csv')}`",
            f"- `{rel(OUT / 'actions.csv')}`",
            f"- `{rel(OUT / 'coverage_audit.csv')}`",
            f"- `{rel(OUT / 'next_day_accounting_audit.csv')}`",
            f"- `{rel(OUT / 'manifest.json')}`",
        ]
    )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    created_at = now()
    OUT.mkdir(parents=True, exist_ok=True)
    s2d = load_s2d()
    o4 = build_o4_ready()
    fresh = build_fresh_ready()
    o4.to_csv(OUT / "o4_replay_ready_2026.csv", index=False)
    fresh.to_csv(OUT / "fresh_replay_ready_2026.csv", index=False)

    prices = s2d.PriceStore(set(o4["instrument"]) | set(fresh["instrument"]))
    results = {
        O4_METHOD: s2d.replay(o4, prices, s2d.MethodSpec(O4_METHOD, O4_SCORE_COL, 50), "2026_subwindow", START, END),
        FRESH_METHOD: s2d.replay(fresh, prices, s2d.MethodSpec(FRESH_METHOD, FRESH_SCORE_COL, 50), "2026_subwindow", START, END),
    }
    fresh_result = results[FRESH_METHOD]
    summary = [metric_row(results[O4_METHOD], fresh_result), metric_row(results[FRESH_METHOD], fresh_result)]
    wcsv(OUT / "summary.csv", summary)

    nav_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    for result in results.values():
        nav_rows.extend(result["curve"])
        action_rows.extend(result["actions"])
    wcsv(OUT / "daily_nav.csv", nav_rows)
    wcsv(OUT / "actions.csv", action_rows)

    coverage = coverage_rows(o4, fresh)
    accounting = accounting_rows(results, s2d)
    wcsv(OUT / "coverage_audit.csv", coverage)
    wcsv(OUT / "next_day_accounting_audit.csv", accounting)

    manifest = {
        "created_at": created_at,
        "window": [START, END],
        "execution": "next-day execution",
        "fee_rate": s2d.FEE_RATE,
        "tax_rate": s2d.SELL_TAX_RATE,
        "target_position_count": s2d.MAX_HOLDINGS,
        "candidate_k": 50,
        "o4_artifact": rel(O4_SCORE),
        "o4_score_column": O4_SCORE_COL,
        "fresh_artifact": rel(FRESH_SCORE),
        "fresh_score_column": FRESH_SCORE_COL,
        "no_training": True,
        "no_tuning": True,
        "no_score_modification": True,
        "no_rule_change": True,
        "summary": summary,
        "coverage": coverage,
        "accounting": accounting,
        "report": rel(REPORT),
    }
    wjson(OUT / "manifest.json", manifest)
    write_report(created_at, summary, coverage, accounting)
    print(json.dumps({"ok": True, "report": rel(REPORT), "summary": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
