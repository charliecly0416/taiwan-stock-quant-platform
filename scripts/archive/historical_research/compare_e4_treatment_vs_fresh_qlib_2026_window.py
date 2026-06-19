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
E4_READY = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_ready_scores_2026.csv"
FRESH_READY = ROOT / "data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv"
OUT = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e5b_e4_vs_fresh_exact_2026_bridge"
REPORT = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE5B_E4_VS_FRESH_EXACT_2026_BRIDGE_REPORT_CN.md"

START = "2026-01-01"
END = "2026-05-07"
E4_METHOD = "e4_frozen_qlib_orthogonal_ltr"
FRESH_METHOD = "repaired_fresh_qlib_top50_adaptive"
E4_SCORE = "phasee3_extended_oos_ltr_score"
FRESH_SCORE = "adaptive_score_baseline"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_s2d():
    spec = importlib.util.spec_from_file_location("evaluate_tw_ltr_s2d_full_daily_replay", S2D_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {S2D_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


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


def load_e4() -> pd.DataFrame:
    df = pd.read_csv(E4_READY, parse_dates=["date"])
    if "date_str" not in df.columns:
        df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    df = df[(df["date_str"] >= START) & (df["date_str"] <= END)].copy()
    df["instrument"] = df["instrument"].map(norm)
    df["split"] = "test"
    df["regime_segment"] = df.get("regime_segment", "normal")
    df = df[pd.to_numeric(df["qlib_rank"], errors="coerce") <= 50].copy()
    keep = ["date", "date_str", "instrument", "split", "regime_segment", "qlib_rank", E4_SCORE]
    return df[keep].sort_values(["date_str", "instrument"]).reset_index(drop=True)


def load_fresh() -> pd.DataFrame:
    df = pd.read_csv(FRESH_READY, parse_dates=["date"])
    if "date_str" not in df.columns:
        df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    df = df[(df["date_str"] >= START) & (df["date_str"] <= END)].copy()
    df["instrument"] = df["instrument"].map(norm)
    df["split"] = df.get("split", "test")
    df["regime_segment"] = df.get("regime_segment", "normal")
    keep = ["date", "date_str", "instrument", "split", "regime_segment", "qlib_rank", FRESH_SCORE]
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


def coverage_rows(e4: pd.DataFrame, fresh: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for method, df, score_col in [(E4_METHOD, e4, E4_SCORE), (FRESH_METHOD, fresh, FRESH_SCORE)]:
        daily = df.groupby("date_str", as_index=False).agg(
            rows=("instrument", "size"),
            score_rows=(score_col, lambda s: int(s.notna().sum())),
            top50_rows=("qlib_rank", lambda s: int((pd.to_numeric(s, errors="coerce") <= 50).sum())),
        )
        rows.append(
            {
                "method": method,
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
        m = result["metrics"]
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
                "missing_price_days": m["missing_price_days"],
                "skipped_trade_count": m["skipped_trade_count"],
                "last_day_new_trade_without_next_price_count": m["last_day_new_trade_without_next_price_count"],
            }
        )
    return rows


def write_report(created_at: str, summary: list[dict[str, Any]], coverage: list[dict[str, Any]], accounting: list[dict[str, Any]]) -> None:
    e4 = next(row for row in summary if row["method"] == E4_METHOD)
    fresh = next(row for row in summary if row["method"] == FRESH_METHOD)
    lines = [
        "# Phase E5B 报告：E4 vs Repaired Fresh Qlib 2026 Exact Bridge",
        "",
        f"生成时间：`{created_at}`",
        "",
        "## 1. 结论",
        "",
        "- 本轮把 E4 treatment 与 repaired fresh qlib 放入同一只读 replay/audit 表重跑。",
        f"- 窗口：`{START}..{END}`，从空仓初始资金起跑。",
        "- 回放口径：同一 S2D replay engine、next-day execution、fee/tax、target_position_count=10、candidate_k=50。",
        "- E4 treatment 只使用 E4 replay-ready top50 LTR score；fresh 使用 C4 repaired replay-ready adaptive score。",
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
            "## 3. 判断",
            "",
            f"- E4 net return：`{e4['fee_tax_adjusted_net_return']}`。",
            f"- Fresh qlib net return：`{fresh['fee_tax_adjusted_net_return']}`。",
            f"- E4 - fresh：`{e4['relative_return_vs_fresh']}`。",
            f"- E4 max drawdown：`{e4['max_drawdown']}`；fresh max drawdown：`{fresh['max_drawdown']}`。",
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
    lines.extend(["", "## 6. 输出 Artifact", "", f"- `{rel(OUT / 'summary.csv')}`", f"- `{rel(OUT / 'coverage_audit.csv')}`", f"- `{rel(OUT / 'next_day_accounting_audit.csv')}`", f"- `{rel(OUT / 'manifest.json')}`"])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    created_at = now()
    OUT.mkdir(parents=True, exist_ok=True)
    s2d = load_s2d()
    e4 = load_e4()
    fresh = load_fresh()
    e4.to_csv(OUT / "e4_replay_ready_2026.csv", index=False)
    fresh.to_csv(OUT / "fresh_replay_ready_2026.csv", index=False)
    prices = s2d.PriceStore(set(e4["instrument"]) | set(fresh["instrument"]))
    results = {
        E4_METHOD: s2d.replay(e4, prices, s2d.MethodSpec(E4_METHOD, E4_SCORE, 50), "2026_exact_bridge", START, END),
        FRESH_METHOD: s2d.replay(fresh, prices, s2d.MethodSpec(FRESH_METHOD, FRESH_SCORE, 50), "2026_exact_bridge", START, END),
    }
    fresh_result = results[FRESH_METHOD]
    summary = [metric_row(results[E4_METHOD], fresh_result), metric_row(results[FRESH_METHOD], fresh_result)]
    coverage = coverage_rows(e4, fresh)
    accounting = accounting_rows(results, s2d)
    wcsv(OUT / "summary.csv", summary)
    wcsv(OUT / "coverage_audit.csv", coverage)
    wcsv(OUT / "next_day_accounting_audit.csv", accounting)
    nav_rows: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    for result in results.values():
        nav_rows.extend(result["curve"])
        actions.extend(result["actions"])
    wcsv(OUT / "daily_nav.csv", nav_rows)
    wcsv(OUT / "actions.csv", actions)
    manifest = {
        "created_at": created_at,
        "window": [START, END],
        "e4_artifact": rel(E4_READY),
        "fresh_artifact": rel(FRESH_READY),
        "same_replay_engine": True,
        "execution": "next-day execution",
        "fee_rate": s2d.FEE_RATE,
        "tax_rate": s2d.SELL_TAX_RATE,
        "target_position_count": s2d.MAX_HOLDINGS,
        "candidate_k": 50,
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
