#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

LATEST_SIGNAL = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
CALENDAR = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank"
PHASE0E = {
    "institutional_flow": ROOT / "data_tw/experiments/decision_orthogonal/phase0e_raw_archive/institutional_flow/phase0e_institutional_flow_20260610T175901Z_normalized.csv",
    "margin_short": ROOT / "data_tw/experiments/decision_orthogonal/phase0e_raw_archive/margin_short/phase0e_margin_short_20260610T180330Z_normalized.csv",
}
O1R_RAW = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair/raw_archive"
P3RRR_RAW = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/source_freshness_raw_archive"
CONTRACT = "pit_safe_delayed_availability: available_at >= next_trading_day(trade_date); as-of join uses available_at <= signal_asof"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for row in rows for k in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def norm(raw: Any) -> str:
    text = str(raw or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def latest_top50() -> tuple[str, list[str]]:
    latest = read_json(LATEST_SIGNAL)
    asof = str(latest.get("asof") or "")[:10]
    run_dir = ROOT / "qlib_pipeline" / str(latest.get("run_dir", ""))
    top50 = pd.read_csv(run_dir / "top50_signals.csv")
    symbols = sorted({norm(x) for x in top50["instrument"].astype(str).tolist()})
    return asof, symbols


def calendar_next_map() -> dict[pd.Timestamp, pd.Timestamp]:
    days = [pd.Timestamp(x.strip()).normalize() for x in CALENDAR.read_text(encoding="utf-8").splitlines() if x.strip()]
    days = sorted(set(days))
    return {days[i]: days[i + 1] for i in range(len(days) - 1)}


def db_rows(family: str, symbols: list[str], start: str, end: str) -> tuple[pd.DataFrame, str, str]:
    try:
        from app.utils.db import get_db_connection  # noqa: WPS433
        table = "qd_tw_stock_institutional_trades" if family == "institutional_flow" else "qd_tw_stock_margin_trading"
        cols = "symbol, trade_date, foreign_net_buy, investment_trust_net_buy, dealer_net_buy, total_institutional_net_buy, quality_flags" if family == "institutional_flow" else "symbol, trade_date, margin_purchase_today_balance, margin_purchase_yesterday_balance, short_sale_today_balance, short_sale_yesterday_balance, quality_flags"
        qmarks = ",".join(["?"] * len(symbols))
        sql = f"SELECT {cols} FROM {table} WHERE symbol IN ({qmarks}) AND trade_date >= ? AND trade_date <= ? ORDER BY symbol, trade_date"
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, [s[2:] for s in symbols] + [start, end])
            rows = cur.fetchall()
            names = [d[0] for d in cur.description]
            cur.close()
        df = pd.DataFrame([dict(zip(names, row)) for row in rows])
        if df.empty:
            return df, "db_empty", ""
        df["symbol"] = df["symbol"].map(norm)
        return df, "db", ""
    except Exception as exc:
        return pd.DataFrame(), "db_failed", f"{type(exc).__name__}: {str(exc)[:240]}"


def local_raw_rows(family: str, symbols: list[str]) -> pd.DataFrame:
    parts = []
    if PHASE0E[family].exists():
        parts.append(pd.read_csv(PHASE0E[family]))
    for path in sorted((O1R_RAW / family).glob("*_normalized.csv")):
        parts.append(pd.read_csv(path))
    for path in sorted((P3RRR_RAW / family).glob("*_normalized.csv")):
        parts.append(pd.read_csv(path))
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts, ignore_index=True, sort=False)
    df["symbol"] = df["symbol"].map(norm)
    df = df[df["symbol"].isin(symbols)].copy()
    return df


def add_available_at(df: pd.DataFrame, nxt: dict[pd.Timestamp, pd.Timestamp], source: str) -> pd.DataFrame:
    out = df.copy()
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce").dt.normalize()
    if "available_at" in out:
        out["available_at"] = pd.to_datetime(out["available_at"], errors="coerce").dt.normalize()
    else:
        out["available_at"] = out["trade_date"].map(nxt)
    out["raw_snapshot_id"] = out.get("raw_snapshot_id", source)
    out["raw_snapshot_path"] = out.get("raw_snapshot_path", "")
    out["lineage_source"] = source
    out["available_at_contract"] = CONTRACT
    out["delay_days"] = (out["available_at"] - out["trade_date"].map(nxt)).dt.days.fillna(0)
    out["delay_reason"] = np.where(out["delay_days"].astype(float).eq(0), "exact_t1", "calendar_gap")
    return out.dropna(subset=["trade_date", "available_at"])


def streak(values: pd.Series) -> pd.Series:
    result = []
    sign = 0
    count = 0
    for value in values.fillna(0):
        cur = 1 if value > 0 else (-1 if value < 0 else 0)
        if cur == 0:
            sign = 0; count = 0; result.append(0)
        elif cur == sign:
            count += 1; result.append(sign * count)
        else:
            sign = cur; count = 1; result.append(sign * count)
    return pd.Series(result, index=values.index)


def build_inst(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["symbol", "trade_date", "available_at"]).drop_duplicates(["symbol", "trade_date"], keep="last").copy()
    if "institutional_total_net_buy" not in out and "total_institutional_net_buy" in out:
        out["institutional_total_net_buy"] = out["total_institutional_net_buy"]
    for col in ["foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy", "institutional_total_net_buy"]:
        out[col] = pd.to_numeric(out.get(col), errors="coerce").fillna(0.0)
        for window in [1, 3, 5, 10]:
            out[f"{col}_roll{window}"] = out.groupby("symbol")[col].transform(lambda s, w=window: s.rolling(w, min_periods=1).sum())
    out["institutional_total_net_buy_streak"] = out.groupby("symbol")["institutional_total_net_buy"].transform(streak)
    out["institutional_missing_flag"] = 0
    out["institutional_delay_flag"] = (out["delay_reason"] != "exact_t1").astype(int)
    out["feature_family"] = "institutional_flow"
    return out


def build_margin(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["symbol", "trade_date", "available_at"]).drop_duplicates(["symbol", "trade_date"], keep="last").copy()
    if "margin_balance" not in out and "margin_purchase_today_balance" in out:
        out["margin_balance"] = pd.to_numeric(out["margin_purchase_today_balance"], errors="coerce")
        out["margin_balance_change"] = out["margin_balance"] - pd.to_numeric(out.get("margin_purchase_yesterday_balance"), errors="coerce")
        out["short_balance"] = pd.to_numeric(out.get("short_sale_today_balance"), errors="coerce")
        out["short_balance_change"] = out["short_balance"] - pd.to_numeric(out.get("short_sale_yesterday_balance"), errors="coerce")
    for col in ["margin_balance", "margin_balance_change", "short_balance", "short_balance_change"]:
        out[col] = pd.to_numeric(out.get(col), errors="coerce").fillna(0.0)
    for col in ["margin_balance_change", "short_balance_change"]:
        for window in [1, 3, 5, 10]:
            out[f"{col}_roll{window}"] = out.groupby("symbol")[col].transform(lambda s, w=window: s.rolling(w, min_periods=1).sum())
    out["margin_direction_proxy"] = (out["margin_balance_change"] > 0).astype(int) - (out["margin_balance_change"] < 0).astype(int)
    out["short_direction_proxy"] = (out["short_balance_change"] > 0).astype(int) - (out["short_balance_change"] < 0).astype(int)
    out["margin_short_divergence_proxy"] = out["margin_direction_proxy"] - out["short_direction_proxy"]
    out["margin_short_missing_flag"] = 0
    out["margin_short_delay_flag"] = (out["delay_reason"] != "exact_t1").astype(int)
    out["feature_family"] = "margin_short"
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    created_at = now()
    asof, symbols = latest_top50()
    if not asof:
        raise RuntimeError("missing latest accepted asof")
    nxt = calendar_next_map()
    start = "2022-01-01"
    family_frames = []
    raw_status_rows = []
    failed_symbols: list[str] = []
    for family in ["institutional_flow", "margin_short"]:
        db, db_status, db_error = db_rows(family, symbols, start, asof)
        if not db.empty:
            raw = add_available_at(db, nxt, "daily_db_archive")
            source = "daily_db_archive"
        else:
            raw = add_available_at(local_raw_rows(family, symbols), nxt, "local_raw_archive_fallback")
            source = "local_raw_archive_fallback"
        if raw.empty:
            failed_symbols.extend(symbols)
            featured = pd.DataFrame()
        elif family == "institutional_flow":
            featured = build_inst(raw)
        else:
            featured = build_margin(raw)
        if not featured.empty:
            family_frames.append(featured)
        raw_status_rows.append({
            "feature_family": family,
            "raw_source": source,
            "db_status": db_status,
            "db_error": db_error,
            "row_count": int(len(raw)),
            "symbol_count": int(raw["symbol"].nunique()) if not raw.empty else 0,
            "raw_trade_date_min": "" if raw.empty else str(raw["trade_date"].min())[:10],
            "raw_trade_date_max": "" if raw.empty else str(raw["trade_date"].max())[:10],
            "raw_available_at_max": "" if raw.empty else str(raw["available_at"].max())[:10],
        })
    features = pd.concat(family_frames, ignore_index=True, sort=False) if family_frames else pd.DataFrame()
    latest_table = OUT / f"latest_orthogonal_features_{asof}.csv"
    features.to_csv(latest_table, index=False)
    write_csv(OUT / f"latest_orthogonal_raw_status_{asof}.csv", raw_status_rows)
    status_by_family = {row["feature_family"]: row for row in raw_status_rows}
    stale = [row["feature_family"] for row in raw_status_rows if row["raw_available_at_max"] and row["raw_available_at_max"] < asof]
    refresh_status = {
        "created_at": created_at,
        "asof": asof,
        "status": "failed" if features.empty else ("stale_degraded" if stale else "current_or_pit_delayed"),
        "latest_feature_table_path": rel(latest_table),
        "latest_feature_table_created_at": created_at,
        "raw_institutional_latest_trade_date": status_by_family.get("institutional_flow", {}).get("raw_trade_date_max", ""),
        "raw_margin_latest_trade_date": status_by_family.get("margin_short", {}).get("raw_trade_date_max", ""),
        "raw_archive_path": rel(O1R_RAW),
        "row_count_by_family": {row["feature_family"]: row["row_count"] for row in raw_status_rows},
        "failed_symbols": sorted(set(failed_symbols)),
        "institutional_latest_trade_date": status_by_family.get("institutional_flow", {}).get("raw_trade_date_max", ""),
        "institutional_latest_available_at": status_by_family.get("institutional_flow", {}).get("raw_available_at_max", ""),
        "margin_latest_trade_date": status_by_family.get("margin_short", {}).get("raw_trade_date_max", ""),
        "margin_latest_available_at": status_by_family.get("margin_short", {}).get("raw_available_at_max", ""),
        "stale_feature_families": stale,
        "raw_status": raw_status_rows,
        "no_provider_accepted_latest_monitor_trading": True,
        "no_training": True,
    }
    write_json(OUT / f"latest_orthogonal_features_{asof}_refresh_status.json", refresh_status)
    write_json(OUT / "latest_orthogonal_features_latest.json", refresh_status)
    print(json.dumps({"ok": True, "status": refresh_status["status"], "latest_feature_table": rel(latest_table), "refresh_status": rel(OUT / f"latest_orthogonal_features_{asof}_refresh_status.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
