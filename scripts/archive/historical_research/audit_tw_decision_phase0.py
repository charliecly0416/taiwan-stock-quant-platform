#!/usr/bin/env python3
"""Phase 0 read-only audit for the TW Decision Model.

The script only reads local artifacts and writes audit reports. It does not
refresh data, publish providers, train models, or touch trading state.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
QLIB = ROOT / "qlib_pipeline"
SIGNAL_ROOT = QLIB / "data_tw/experiments/option_c_historical_signal_backfill"
DAILY_SIGNAL_ROOT = QLIB / "data_tw/experiments/option_c_daily_signal"
PRICE_ROOT = QLIB / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
UNIVERSE_PATH = QLIB / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt"
TWII_PATH = QLIB / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv"
FINMIND_SUMMARY = SIGNAL_ROOT / "option_c_historical_backfill_20260101_20260531/finmind_archive_apply_summary.json"
OUT_DIR = ROOT / "data_tw/experiments/decision_model"
DOC_DIR = ROOT / "docs/tw_decision_model"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def safe_float(raw: Any) -> float | None:
    try:
        value = float(raw)
    except Exception:
        return None
    if not math.isfinite(value):
        return None
    return value


def pct(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.2f}%"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def audit_signals() -> dict[str, Any]:
    prediction_paths = sorted(SIGNAL_ROOT.glob("*/*/prediction.csv"))
    top50_paths = sorted(SIGNAL_ROOT.glob("*/*/top50_signals.csv"))
    daily_prediction_paths = sorted(DAILY_SIGNAL_ROOT.glob("*/prediction.csv"))
    daily_top50_paths = sorted(DAILY_SIGNAL_ROOT.glob("*/top50_signals.csv"))
    rows_by_date: dict[str, dict[str, float]] = defaultdict(dict)
    top_counts: dict[str, int] = {}
    source_runs = set()

    for path in prediction_paths + daily_prediction_paths:
        try:
            with path.open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    day = str(row.get("datetime") or row.get("asof") or "")[:10]
                    instrument = str(row.get("instrument") or row.get("symbol") or "").strip()
                    score = safe_float(row.get("score"))
                    if day and instrument and score is not None:
                        rows_by_date[day][instrument] = score
                        source_runs.add(str(path.parent))
        except Exception:
            continue

    for path in top50_paths + daily_top50_paths:
        try:
            rows = read_csv_rows(path)
        except Exception:
            continue
        day = ""
        if rows:
            day = str(rows[0].get("asof") or rows[0].get("datetime") or "")[:10]
        if day:
            top_counts[day] = max(top_counts.get(day, 0), len(rows))

    dates = sorted(rows_by_date)
    per_date_stats = []
    all_scores = []
    for day in dates:
        scores = list(rows_by_date[day].values())
        if not scores:
            continue
        all_scores.extend(scores)
        avg = mean(scores)
        std = pd.Series(scores).std(ddof=0)
        per_date_stats.append(
            {
                "date": day,
                "rows": len(scores),
                "score_min": min(scores),
                "score_max": max(scores),
                "score_mean": avg,
                "score_std": float(std) if math.isfinite(float(std)) else 0.0,
                "top50_rows": top_counts.get(day, 0),
                "percentile_available": len(scores) >= 2,
                "zscore_available": len(scores) >= 2 and std > 0,
            }
        )

    top50_complete = [item["top50_rows"] >= 50 for item in per_date_stats if item["top50_rows"]]
    row_counts = [item["rows"] for item in per_date_stats]
    stds = [item["score_std"] for item in per_date_stats]
    means = [item["score_mean"] for item in per_date_stats]
    return {
        "prediction_file_count": len(prediction_paths) + len(daily_prediction_paths),
        "historical_top50_file_count": len(top50_paths),
        "daily_top50_file_count": len(daily_top50_paths),
        "source_run_count": len(source_runs),
        "date_count": len(dates),
        "start_date": dates[0] if dates else None,
        "end_date": dates[-1] if dates else None,
        "row_count_min": min(row_counts) if row_counts else 0,
        "row_count_median": median(row_counts) if row_counts else 0,
        "row_count_max": max(row_counts) if row_counts else 0,
        "score_min": min(all_scores) if all_scores else None,
        "score_max": max(all_scores) if all_scores else None,
        "score_mean": mean(all_scores) if all_scores else None,
        "date_mean_min": min(means) if means else None,
        "date_mean_max": max(means) if means else None,
        "date_std_min": min(stds) if stds else None,
        "date_std_max": max(stds) if stds else None,
        "percentile_date_count": sum(1 for item in per_date_stats if item["percentile_available"]),
        "zscore_date_count": sum(1 for item in per_date_stats if item["zscore_available"]),
        "top50_complete_date_count": sum(1 for item in top50_complete if item),
        "top50_observed_date_count": len(top50_complete),
        "per_date_sample": per_date_stats[:5] + per_date_stats[-5:] if len(per_date_stats) > 10 else per_date_stats,
    }


def load_universe() -> list[str]:
    symbols = []
    if not UNIVERSE_PATH.exists():
        return symbols
    for line in UNIVERSE_PATH.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts:
            symbols.append(parts[0])
    return symbols


def audit_ohlcv() -> tuple[dict[str, Any], pd.DataFrame]:
    paths = sorted(PRICE_ROOT.glob("TW*.csv"))
    rows = []
    all_dates = set()
    for path in paths:
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if df.empty or "date" not in df:
            continue
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date")
        if df.empty:
            continue
        for day in df["date"].dt.strftime("%Y-%m-%d").tolist():
            all_dates.add(day)
        symbol = str(df["symbol"].iloc[0]) if "symbol" in df.columns else path.stem
        date_count = int(df.shape[0])
        close_ok = float(df["close"].notna().mean()) if "close" in df else 0.0
        volume_ok = float(df["volume"].notna().mean()) if "volume" in df else 0.0
        vwap_ok = float(df["vwap"].notna().mean()) if "vwap" in df else 0.0
        trading_value_available = "trading_money" in df.columns or "trading_value" in df.columns or {"volume", "vwap"}.issubset(df.columns)
        if {"volume", "vwap"}.issubset(df.columns):
            trading_value_ok = float((df["volume"].notna() & df["vwap"].notna()).mean())
            avg_value_20d_ok = date_count >= 20 and trading_value_ok > 0.95
        else:
            trading_value_ok = 0.0
            avg_value_20d_ok = False
        zero_volume_share = float((pd.to_numeric(df.get("volume", pd.Series(dtype=float)), errors="coerce").fillna(0) <= 0).mean()) if "volume" in df else 1.0
        rows.append(
            {
                "symbol": symbol,
                "start_date": df["date"].min().strftime("%Y-%m-%d"),
                "end_date": df["date"].max().strftime("%Y-%m-%d"),
                "date_count": date_count,
                "close_coverage": close_ok,
                "volume_coverage": volume_ok,
                "vwap_coverage": vwap_ok,
                "trading_value_coverage": trading_value_ok,
                "zero_volume_share": zero_volume_share,
                "trading_value_available": trading_value_available,
                "ma60_available": date_count >= 60 and close_ok > 0.95,
                "ma120_available": date_count >= 120 and close_ok > 0.95,
                "rsi14_available": date_count >= 15 and close_ok > 0.95,
                "macd_available": date_count >= 35 and close_ok > 0.95,
                "bollinger_available": date_count >= 20 and close_ok > 0.95,
                "ret20_available": date_count >= 21 and close_ok > 0.95,
                "vol20_available": date_count >= 21 and close_ok > 0.95,
                "avg_trading_value_20d_available": avg_value_20d_ok,
            }
        )
    result = pd.DataFrame(rows)
    calendar = sorted(all_dates)
    if result.empty:
        summary = {"file_count": 0}
    else:
        expected_by_symbol = []
        for _, row in result.iterrows():
            expected = sum(1 for day in calendar if row["start_date"] <= day <= row["end_date"])
            expected_by_symbol.append(expected)
        result["missing_trading_day_share"] = [
            1.0 - (row.date_count / expected if expected else 0.0)
            for row, expected in zip(result.itertuples(index=False), expected_by_symbol)
        ]
        summary = {
            "file_count": len(paths),
            "symbol_count": int(result["symbol"].nunique()),
            "calendar_start": calendar[0] if calendar else None,
            "calendar_end": calendar[-1] if calendar else None,
            "calendar_days": len(calendar),
            "median_symbol_rows": float(result["date_count"].median()),
            "median_missing_trading_day_share": float(result["missing_trading_day_share"].median()),
            "adjusted_close_usable_symbols": int((result["close_coverage"] > 0.99).sum()),
            "volume_usable_symbols": int((result["volume_coverage"] > 0.99).sum()),
            "trading_value_proxy_symbols": int(result["avg_trading_value_20d_available"].sum()),
            "zero_volume_symbol_count": int((result["zero_volume_share"] > 0).sum()),
        }
    return summary, result


def audit_twii(price_panel: pd.DataFrame) -> dict[str, Any]:
    if not TWII_PATH.exists():
        return {"exists": False}
    df = pd.read_csv(TWII_PATH)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    close = pd.to_numeric(df.get("close"), errors="coerce")
    ret = close.pct_change()
    out = {
        "exists": True,
        "path": rel(TWII_PATH),
        "start_date": df["date"].min().strftime("%Y-%m-%d") if not df.empty else None,
        "end_date": df["date"].max().strftime("%Y-%m-%d") if not df.empty else None,
        "rows": int(df.shape[0]),
        "close_coverage": float(close.notna().mean()) if len(close) else 0.0,
        "ret20_available": len(close.dropna()) >= 21,
        "ret60_available": len(close.dropna()) >= 61,
        "ma60_available": len(close.dropna()) >= 60,
        "ma120_available": len(close.dropna()) >= 120,
        "vol20_available": len(ret.dropna()) >= 20,
        "drawdown60_available": len(close.dropna()) >= 60,
    }
    if not price_panel.empty:
        common_start = max(str(price_panel["start_date"].min()), out["start_date"] or "")
        common_end = min(str(price_panel["end_date"].max()), out["end_date"] or "9999-12-31")
        out["market_breadth_proxy_available"] = True
        out["market_breadth_proxy_rule"] = "Compute per date from OHLCV stable pool, e.g. share of symbols with close > MA20 or positive 20d return."
        out["common_start_with_stock_panel"] = common_start
        out["common_end_with_stock_panel"] = common_end
    return out


def audit_finmind() -> dict[str, Any]:
    if not FINMIND_SUMMARY.exists():
        return {"summary_exists": False, "path": rel(FINMIND_SUMMARY)}
    payload = json.loads(FINMIND_SUMMARY.read_text(encoding="utf-8"))
    groups = {}
    for key in ["archive", "institutional_trades", "margin_trading", "monthly_revenue", "valuation", "corporate_actions"]:
        value = payload.get(key) or {}
        groups[key] = {
            "count": int(value.get("count") or 0),
            "symbol_count": len(value.get("symbols") or []),
            "date_min": value.get("date_min") or value.get("period_min"),
            "date_max": value.get("date_max") or value.get("period_max"),
            "flagged_count": int(value.get("flagged_count") or 0),
            "has_available_at": False,
        }
    return {
        "summary_exists": True,
        "path": rel(FINMIND_SUMMARY),
        "apply": bool(payload.get("apply")),
        "start": payload.get("start"),
        "end": payload.get("end"),
        "groups": groups,
    }


def feature_rows(signal: dict[str, Any], ohlcv: dict[str, Any], price_panel: pd.DataFrame, twii: dict[str, Any], finmind: dict[str, Any]) -> list[dict[str, Any]]:
    symbol_count = max(1, int(ohlcv.get("symbol_count") or 0))
    def add(name: str, source: str, coverage: float, start: Any, end: Any, safe: bool, rule: str, status: str, reason: str) -> dict[str, Any]:
        return {
            "feature_name": name,
            "source": source,
            "coverage_pct": round(max(0.0, min(1.0, float(coverage))) * 100, 4),
            "start_date": start or "",
            "end_date": end or "",
            "point_in_time_safe": str(bool(safe)).lower(),
            "available_at_rule": rule,
            "v1_status": status,
            "reason": reason,
        }
    rows = []
    sig_cov = 1.0 if signal.get("date_count") else 0.0
    rows.extend([
        add("qlib_score", "qlib prediction.csv", sig_cov, signal.get("start_date"), signal.get("end_date"), True, "Use asof signal generated from frozen recorder; join by signal asof, never by future target date.", "include", "Historical prediction artifacts are available; raw score must be calibrated by date."),
        add("qlib_rank", "qlib top50/prediction rank", sig_cov, signal.get("start_date"), signal.get("end_date"), True, "Rank within the asof prediction universe.", "include", "Top30/Top50 flags can be reconstructed from rank."),
        add("qlib_score_percentile_by_date", "derived from qlib score", sig_cov, signal.get("start_date"), signal.get("end_date"), True, "Compute within each asof date only.", "include", "Percentile is available where daily candidate count >= 2."),
        add("qlib_score_zscore_by_date", "derived from qlib score", sig_cov, signal.get("start_date"), signal.get("end_date"), True, "Compute within each asof date only.", "include", "Z-score is available where daily score std > 0."),
    ])
    if not price_panel.empty:
        cov_close = float((price_panel["close_coverage"] > 0.99).mean())
        cov_volume = float((price_panel["volume_coverage"] > 0.99).mean())
        cov_value = float(price_panel["avg_trading_value_20d_available"].mean())
        start = price_panel["start_date"].min()
        end = price_panel["end_date"].max()
    else:
        cov_close = cov_volume = cov_value = 0.0
        start = end = ""
    for name in ["adjusted_close", "future_return_label_base"]:
        rows.append(add(name, "Yahoo/Scrapling adjusted OHLCV", cov_close, start, end, True, "Use adjusted bars available at or before asof; labels only use future window in training target generation.", "include", "Adjusted close is complete enough for return features and later label construction."))
    rows.append(add("volume", "Yahoo/Scrapling adjusted OHLCV", cov_volume, start, end, True, "Use asof or trailing window ending at asof.", "include", "Volume is complete enough for liquidity and volume-ratio features."))
    rows.append(add("trading_value_proxy", "volume * vwap", cov_value, start, end, True, "Compute volume*vwap with trailing windows ending at asof.", "include", "Direct trading_money is absent in normalized bars, but volume*vwap is usable as a proxy."))
    for name in ["MA5", "MA10", "MA20", "MA60", "RSI14", "MACD", "Bollinger_position", "ret20", "volatility20", "volume_ratio20"]:
        rows.append(add(name, "derived from adjusted OHLCV", cov_close, start, end, True, "Rolling calculation uses values <= asof only.", "include", "No stable indicator archive found, but feature is reproducible from OHLCV."))
    for name in ["avg_trading_value_20d", "volume_stability20", "missing_rate20", "suspension_proxy", "slippage_proxy"]:
        rows.append(add(name, "derived liquidity panel", cov_value, start, end, True, "Rolling calculation uses values <= asof only.", "include", "Can be derived from volume, vwap, and missing-date patterns."))
    rows.append(add("limit_up_down_proxy", "OHLCV derived", cov_close, start, end, True, "Use close-to-close or high/low/open/close move at asof; no official limit flag.", "defer", "Proxy exists but official limit-up/down status is not archived."))
    twii_cov = 1.0 if twii.get("exists") else 0.0
    for name in ["TWII_close", "TWII_ret20", "TWII_ret60", "TWII_close_vs_MA60", "TWII_close_vs_MA120", "market_volatility20", "market_drawdown60"]:
        rows.append(add(name, "TWII.csv", twii_cov, twii.get("start_date"), twii.get("end_date"), True, "Use TWII values <= asof; market_regime is derived only as explanation/grouping.", "include" if twii_cov else "defer", "TWII continuous features are available." if twii_cov else "TWII source missing."))
    rows.append(add("market_breadth20", "derived from stable stock pool", cov_close, start, end, True, "Compute per date using only same-date/trailing OHLCV values.", "include", "Breadth is not pre-archived but can be reproducibly computed from the stable pool."))
    groups = (finmind.get("groups") or {}) if finmind.get("summary_exists") else {}
    for name, group in [
        ("institutional_net_buy", "institutional_trades"),
        ("margin_balance", "margin_trading"),
        ("short_balance", "margin_trading"),
        ("monthly_revenue_yoy_mom", "monthly_revenue"),
        ("valuation_PER_PBR", "valuation"),
    ]:
        info = groups.get(group) or {}
        count = int(info.get("count") or 0)
        status = "defer" if count == 0 else "defer"
        reason = "No archived rows in current FinMind summary." if count == 0 else "Archived rows exist but available_at/announcement_date is not proven."
        rows.append(add(name, f"FinMind {group}", 0.0 if count == 0 else min(1.0, info.get("symbol_count", 0) / symbol_count), info.get("date_min"), info.get("date_max"), False, "Must join by announcement_date/available_at with conservative T+1 lag; period-only join is rejected.", status, reason))
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_sources(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(to_builtin(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def to_builtin(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): to_builtin(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_builtin(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def write_pit_rules(path: Path) -> None:
    lines = [
        "# Phase 0 Point-in-Time Rules",
        "",
        "- qlib score/rank: join by signal `asof`; use raw score only as a feature and compute percentile/z-score within the same `asof` date. Do not use fixed absolute score bands as rules.",
        "- OHLCV features: rolling windows must end at `asof`; adjusted close can be used for future labels only during Phase 1 label construction, never as an input after `asof`.",
        "- Technical features: MA/RSI/MACD/Bollinger/return/volatility/volume ratio are recomputed from OHLCV values with timestamp <= `asof`.",
        "- Liquidity features: 20d trading value uses `volume * vwap`; missing-rate and suspension proxies use only observed trading-calendar gaps up to `asof`.",
        "- Limit-up/down risk: current v1 can only use OHLCV-derived proxy; official exchange limit flags are not archived and must not be claimed as available.",
        "- TWII/market features: use continuous ret20/ret60, MA distance, volatility, drawdown, and breadth. `market_regime` may be generated only for explanation and grouped evaluation, not as a hard action gate.",
        "- FinMind daily trading archive: trade-date OHLCV rows can be treated as daily bars after conservative T+1 availability if used, but current v1 should prefer adjusted OHLCV for price features.",
        "- FinMind institutional/margin/monthly revenue/valuation: current archive does not prove `available_at`/`announcement_date`. These fields are deferred until each row can carry `source_period`, `available_at`, and `days_since_last_report`.",
        "- Financial/monthly revenue data: period-only joins are rejected. Safe forward fill is allowed only from `available_at` to later dates and must preserve source metadata.",
        "- Research-only boundary: Phase 0 artifacts are audit outputs only; they are not orders, target positions, broker instructions, provider publish requests, accepted-latest switches, or monitor configuration changes.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_report(path: Path, signal: dict[str, Any], ohlcv: dict[str, Any], price_panel: pd.DataFrame, twii: dict[str, Any], finmind: dict[str, Any], features: list[dict[str, Any]], sources: dict[str, Any]) -> None:
    include_count = sum(1 for row in features if row["v1_status"] == "include")
    defer_count = sum(1 for row in features if row["v1_status"] == "defer")
    reject_count = sum(1 for row in features if row["v1_status"] == "reject")
    fin_groups = finmind.get("groups") or {}
    lines = [
        "# Phase 0 Feature Availability Report",
        "",
        "## 1. 执行摘要",
        "",
        f"- 审计日期：`{utc_now()}`",
        "- 范围：只读审计 qlib signal、adjusted OHLCV、技术/流动性可复算性、TWII 连续特征、FinMind 归档可用性。",
        "- 代码变更：新增只读审计脚本 `scripts/audit_tw_decision_phase0.py`；生成 Phase 0 报告文件。",
        "- 是否触碰只读边界：否。未训练模型、未刷新 provider、未发布、未切换 accepted latest、未写 broker/orders/quick-trade/monitor config/alerts。",
        f"- v1 特征准入：include `{include_count}`，defer `{defer_count}`，reject `{reject_count}`。",
        "",
        "## 2. 数据源清单",
        "",
        "| 数据源 | 路径/表名 | 日期范围 | symbol 覆盖 | 状态 |",
        "|---|---|---:|---:|---|",
        f"| qlib historical prediction | `{rel(SIGNAL_ROOT)}` + `{rel(DAILY_SIGNAL_ROOT)}` | {signal.get('start_date')} ~ {signal.get('end_date')} | 每日 {signal.get('row_count_min')}~{signal.get('row_count_max')} rows | include |",
        f"| qlib Top50 signals | `{rel(SIGNAL_ROOT)}` | {signal.get('start_date')} ~ {signal.get('end_date')} | Top50 observed dates {signal.get('top50_observed_date_count')} | include |",
        f"| adjusted OHLCV 150 | `{rel(PRICE_ROOT)}` | {ohlcv.get('calendar_start')} ~ {ohlcv.get('calendar_end')} | {ohlcv.get('symbol_count')} | include |",
        f"| stable universe | `{rel(UNIVERSE_PATH)}` | instrument-level ranges | {len(load_universe())} | include |",
        f"| TWII index | `{rel(TWII_PATH)}` | {twii.get('start_date')} ~ {twii.get('end_date')} | 1 index | include |",
        f"| FinMind archive summary | `{rel(FINMIND_SUMMARY)}` | {finmind.get('start')} ~ {finmind.get('end')} | archive symbols {(fin_groups.get('archive') or {}).get('symbol_count', 0)} | partial/defer |",
        "",
        "## 3. qlib Score 分布审计",
        "",
        f"- prediction 文件数：`{signal.get('prediction_file_count')}`；Top50 文件数：`{signal.get('historical_top50_file_count')}`。",
        f"- 覆盖交易日：`{signal.get('date_count')}`，范围 `{signal.get('start_date')}` ~ `{signal.get('end_date')}`。",
        f"- 每日候选数量：min `{signal.get('row_count_min')}`，median `{signal.get('row_count_median')}`，max `{signal.get('row_count_max')}`。",
        f"- raw score 范围：`{signal.get('score_min')}` ~ `{signal.get('score_max')}`，均值 `{signal.get('score_mean')}`。",
        f"- date percentile 可计算日期：`{signal.get('percentile_date_count')}` / `{signal.get('date_count')}`。",
        f"- date z-score 可计算日期：`{signal.get('zscore_date_count')}` / `{signal.get('date_count')}`。",
        f"- Top50 完整日期：`{signal.get('top50_complete_date_count')}` / `{signal.get('top50_observed_date_count')}`。",
        f"- 是否发现 score 量级漂移：每日均值范围 `{signal.get('date_mean_min')}` ~ `{signal.get('date_mean_max')}`，每日 std 范围 `{signal.get('date_std_min')}` ~ `{signal.get('date_std_max')}`；Phase 1 必须使用日期内 percentile/z-score，不得写死绝对 score 区间。",
        "",
        "## 4. OHLCV / 技术 / 流动性审计",
        "",
        f"- OHLCV symbol 数：`{ohlcv.get('symbol_count')}`；日历范围 `{ohlcv.get('calendar_start')}` ~ `{ohlcv.get('calendar_end')}`。",
        f"- adjusted close 完整可用 symbol：`{ohlcv.get('adjusted_close_usable_symbols')}`。",
        f"- volume 完整可用 symbol：`{ohlcv.get('volume_usable_symbols')}`。",
        f"- `volume * vwap` 可作为成交额 proxy 的 symbol：`{ohlcv.get('trading_value_proxy_symbols')}`。",
        f"- 缺失交易日比例中位数：`{pct(ohlcv.get('median_missing_trading_day_share'))}`。",
        "- 技术指标 MA5/10/20/60、RSI14、MACD、Bollinger、20d return、20d volatility、volume ratio 均可从 adjusted OHLCV 复算，进入 v1。",
        "- 流动性字段 20d average trading value、volume stability、missing rate、suspension proxy、slippage proxy 可复算，进入 v1。",
        "- 涨跌停风险仅能用 OHLCV proxy，官方涨跌停 flag 未归档，v1 暂缓作为正式字段。",
        "",
        "## 5. TWII / 大盘状态审计",
        "",
        f"- TWII close 覆盖：`{pct(twii.get('close_coverage'))}`，范围 `{twii.get('start_date')}` ~ `{twii.get('end_date')}`。",
        f"- ret20/ret60、MA60/MA120、20d volatility、60d drawdown 可用：`{twii.get('ret20_available')}` / `{twii.get('ret60_available')}` / `{twii.get('ma60_available')}` / `{twii.get('ma120_available')}` / `{twii.get('vol20_available')}` / `{twii.get('drawdown60_available')}`。",
        "- market breadth 未单独归档，但可用稳定股票池同日横截面复算，例如站上 MA20 比例或 20d return 为正比例。",
        "- `market_regime` 只能作为解释摘要和分组评估，不作为唯一硬规则。",
        "",
        "## 6. FinMind Point-in-Time 审计",
        "",
        "| feature_group | has_available_at | proposed_lag_rule | safe_forward_fill | v1_status |",
        "|---|---|---|---|---|",
        "| daily OHLCV archive | false | 若使用需至少 T+1；当前 price v1 优先使用 adjusted OHLCV | 不需要 | defer for price v1 |",
        "| institutional trades | false | 必须证明交易日后可见时间，保守 T+1 后 join | 仅 daily rolling，不 forward fill | defer |",
        "| margin trading | false | 必须证明 available_at，保守 T+1 后 join | 仅 daily rolling，不 forward fill | defer |",
        "| monthly revenue | false | 必须按 announcement_date/available_at join，禁止 period join | 可从 available_at 安全 forward fill，并保留 source_period/days_since_last_report | defer |",
        "| valuation PER/PBR | false | 必须证明 date/available_at 口径 | 可按 available_at forward fill | defer |",
        "",
        "FinMind 摘要显示 institutional/margin/monthly revenue/valuation 当前归档 count 为 0，且没有可审计的 `available_at`/`announcement_date` 字段，因此不能进入 v1。",
        "",
        "## 7. 特征覆盖率",
        "",
        "| feature | source | coverage_pct | start_date | end_date | point_in_time_safe | v1_status | reason |",
        "|---|---|---:|---|---|---|---|---|",
    ]
    for row in features:
        lines.append(f"| {row['feature_name']} | {row['source']} | {row['coverage_pct']:.2f}% | {row['start_date']} | {row['end_date']} | {row['point_in_time_safe']} | {row['v1_status']} | {row['reason']} |")
    lines.extend([
        "",
        "## 8. 风险与阻塞项",
        "",
        "- 必须修复：Phase 1 构样本前，FinMind 财务/月营收/估值若要启用，必须补齐 row-level `available_at` 或 `announcement_date`。",
        "- 必须修复：qlib score band 必须基于 Phase 0/Phase 1 分布校准，不能沿用固定绝对 score 区间。",
        "- 覆盖风险：historical backfill 的可用 prediction 日期主要来自已有 backfill；若 Phase 1 需要更长训练区间，需确认缺失日期是否可接受，但不能在本阶段触发刷新或回填。",
        "- 流动性风险：直接 trading_money 在 normalized bars 缺失，v1 使用 `volume * vwap` proxy；官方滑点/涨跌停/停牌标志未归档。",
        "- 产品边界风险：报告和后续输出必须保持 research-only，不能出现真实交易动作指令。",
        "",
        "## 9. Phase 1 准入建议",
        "",
        "- 可进入 Phase 1：qlib score/rank/date percentile/date z-score、Top10/Top30/Top50 flags、OHLCV 派生技术趋势、流动性 proxy、TWII 连续特征、market breadth proxy。",
        "- 暂缓特征：FinMind institutional/margin/monthly revenue/valuation、官方 limit-up/down flag、正式 trading_money 字段。",
        "- 拒绝特征：任何只有 period 而没有 `available_at`/`announcement_date` 的财务/月营收直接 join。",
        "- 是否建议进入 Phase 1：建议在上述暂缓项保持暂缓的前提下进入 Phase 1；若审查者要求 FinMind 补充特征必须进入 v1，则需要先补充 PIT 归档，不能直接构样本。",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    signal = audit_signals()
    ohlcv, price_panel = audit_ohlcv()
    twii = audit_twii(price_panel)
    finmind = audit_finmind()
    features = feature_rows(signal, ohlcv, price_panel, twii, finmind)
    sources = {
        "created_at": utc_now(),
        "research_only": True,
        "no_training": True,
        "no_provider_refresh_or_publish": True,
        "no_accepted_latest_switch": True,
        "no_broker_orders_quick_trade_or_target_positions": True,
        "paths": {
            "signal_root": rel(SIGNAL_ROOT),
            "daily_signal_root": rel(DAILY_SIGNAL_ROOT),
            "price_root": rel(PRICE_ROOT),
            "universe_path": rel(UNIVERSE_PATH),
            "twii_path": rel(TWII_PATH),
            "finmind_summary": rel(FINMIND_SUMMARY),
        },
        "signal_audit": signal,
        "ohlcv_audit": ohlcv,
        "twii_audit": twii,
        "finmind_audit": finmind,
    }
    write_csv(OUT_DIR / "phase0_feature_coverage.csv", features)
    write_sources(OUT_DIR / "phase0_data_sources.json", sources)
    write_pit_rules(OUT_DIR / "phase0_point_in_time_rules.md")
    write_report(DOC_DIR / "phase0_feature_availability_report.md", signal, ohlcv, price_panel, twii, finmind, features, sources)
    print(json.dumps({
        "status": "ok",
        "feature_rows": len(features),
        "outputs": [
            rel(DOC_DIR / "phase0_feature_availability_report.md"),
            rel(OUT_DIR / "phase0_feature_coverage.csv"),
            rel(OUT_DIR / "phase0_data_sources.json"),
            rel(OUT_DIR / "phase0_point_in_time_rules.md"),
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
