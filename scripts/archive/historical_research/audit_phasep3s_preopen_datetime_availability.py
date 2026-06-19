#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank"
RAW = OUT / "source_freshness_raw_archive"
CALENDAR = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
P3_SUMMARY = OUT / "daily_ltr_rerank_2026-06-15_summary.json"
LATEST_FEATURE_TABLE = OUT / "latest_orthogonal_features_2026-06-15.csv"
REPORT = ROOT / "docs/tw_ltr_orthogonal_features_controlled/PHASEP3S_PREOPEN_DATETIME_AVAILABILITY_EXECUTION_REPORT_CN.md"
GATE = "phase_p3s_preopen_datetime_availability_not_proven_stop"


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


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def md(rows: list[dict[str, Any]], fields: list[str]) -> list[str]:
    out = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return out


def calendar_next_map() -> dict[str, str]:
    days = [x.strip() for x in CALENDAR.read_text(encoding="utf-8").splitlines() if x.strip()]
    return {days[i]: days[i + 1] for i in range(len(days) - 1)}


def target_open_datetime_utc(day: str) -> str:
    # Taiwan market regular open is 09:00 Asia/Taipei, equal to 01:00 UTC.
    return f"{day}T01:00:00+00:00"


def read_family_raw(family: str) -> pd.DataFrame:
    parts = []
    for path in sorted((RAW / family).glob("*_normalized.csv")):
        df = pd.read_csv(path)
        df["normalized_path"] = rel(path)
        parts.append(df)
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, ignore_index=True, sort=False)
    out["trade_date"] = pd.to_datetime(out.get("trade_date"), errors="coerce").dt.strftime("%Y-%m-%d")
    out["symbol"] = out.get("symbol", "").astype(str)
    out["fetched_at_dt"] = pd.to_datetime(out.get("fetched_at"), errors="coerce", utc=True)
    if "available_at_datetime" in out:
        out["available_at_datetime_dt"] = pd.to_datetime(out["available_at_datetime"], errors="coerce", utc=True)
    else:
        out["available_at_datetime_dt"] = pd.to_datetime(pd.Series([pd.NaT] * len(out)), errors="coerce", utc=True)
    return out.dropna(subset=["trade_date"]).copy()


def audit_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    nxt = calendar_next_map()
    all_trade_dates = set()
    family_frames = {}
    for family in ["institutional_flow", "margin_short"]:
        df = read_family_raw(family)
        family_frames[family] = df
        all_trade_dates.update(df["trade_date"].dropna().astype(str).tolist())
    recent = sorted(all_trade_dates)[-5:]
    rows: list[dict[str, Any]] = []
    for family, df in family_frames.items():
        for trade_date in recent:
            g = df[df["trade_date"].astype(str).eq(trade_date)].copy()
            next_day = nxt.get(trade_date, "")
            target_open = target_open_datetime_utc(next_day) if next_day else ""
            target_open_ts = pd.to_datetime(target_open, errors="coerce", utc=True)
            symbol_count = int(g["symbol"].nunique()) if not g.empty else 0
            missing_ts = int(g["available_at_datetime_dt"].isna().sum()) if not g.empty else 0
            preopen_mask = pd.Series(False, index=g.index)
            if pd.notna(target_open_ts):
                preopen_mask = g["available_at_datetime_dt"].notna() & (g["available_at_datetime_dt"] < target_open_ts)
            preopen_symbols = int(g.loc[preopen_mask, "symbol"].nunique()) if not g.empty else 0
            late_symbols = int(symbol_count - preopen_symbols) if symbol_count else 0
            rows.append({
                "feature_family": family,
                "trade_date": trade_date,
                "symbol_count": symbol_count,
                "raw_row_count": int(len(g)),
                "fetched_at_min": "" if g.empty or g["fetched_at_dt"].isna().all() else g["fetched_at_dt"].min().isoformat(),
                "fetched_at_max": "" if g.empty or g["fetched_at_dt"].isna().all() else g["fetched_at_dt"].max().isoformat(),
                "available_at_datetime_min": "",
                "available_at_datetime_max": "",
                "next_trading_day": next_day,
                "target_open_datetime": target_open,
                "preopen_available_symbol_count": preopen_symbols,
                "preopen_available_ratio": round(preopen_symbols / symbol_count, 6) if symbol_count else 0.0,
                "late_symbol_count": late_symbols,
                "missing_timestamp_count": missing_ts,
            })
    meta = {
        "recent_trade_dates_available": recent,
        "recent_trade_date_count": len(recent),
        "raw_archive_path": rel(RAW),
    }
    return rows, meta


def main() -> None:
    created_at = now()
    p3_summary = read_json(P3_SUMMARY)
    rows, meta = audit_rows()
    fields = [
        "feature_family",
        "trade_date",
        "symbol_count",
        "raw_row_count",
        "fetched_at_min",
        "fetched_at_max",
        "available_at_datetime_min",
        "available_at_datetime_max",
        "next_trading_day",
        "target_open_datetime",
        "preopen_available_symbol_count",
        "preopen_available_ratio",
        "late_symbol_count",
        "missing_timestamp_count",
    ]
    audit_csv = OUT / "daily_ltr_rerank_2026-06-15_p3s_preopen_datetime_audit.csv"
    audit_json = OUT / "daily_ltr_rerank_2026-06-15_p3s_preopen_datetime_audit.json"
    write_csv(audit_csv, rows, fields)

    latest_has_datetime = False
    latest_cols: list[str] = []
    if LATEST_FEATURE_TABLE.exists():
        latest_cols = list(pd.read_csv(LATEST_FEATURE_TABLE, nrows=0).columns)
        latest_has_datetime = "used_available_at_datetime" in latest_cols or "available_at_datetime" in latest_cols

    summary_has_strategy_time = all(k in p3_summary for k in ["strategy_generation_time", "target_execution_date", "target_open_datetime"])
    has_available_at_datetime = any(float(row["preopen_available_ratio"]) > 0 for row in rows)
    enough_days = int(meta["recent_trade_date_count"]) >= 5
    institutional_rows = [r for r in rows if r["feature_family"] == "institutional_flow"]
    margin_rows = [r for r in rows if r["feature_family"] == "margin_short"]
    all_preopen = bool(rows) and all(float(r["preopen_available_ratio"]) >= 1.0 for r in rows)
    upgrade_allowed = all([
        enough_days,
        has_available_at_datetime,
        latest_has_datetime,
        summary_has_strategy_time,
        all_preopen,
    ])
    gate = "phase_p3s_preopen_datetime_availability_upgraded" if upgrade_allowed else GATE
    audit = {
        "created_at": created_at,
        "gate": gate,
        "asof": p3_summary.get("asof", "2026-06-15"),
        "raw_archive_path": meta["raw_archive_path"],
        "recent_trade_dates_available": meta["recent_trade_dates_available"],
        "recent_trade_date_count": meta["recent_trade_date_count"],
        "minimum_recent_trade_days_required": 5,
        "latest_feature_table_path": rel(LATEST_FEATURE_TABLE),
        "latest_feature_table_has_datetime_availability": latest_has_datetime,
        "latest_feature_table_datetime_columns": [c for c in latest_cols if "datetime" in c],
        "p3_summary_path": rel(P3_SUMMARY),
        "p3_summary_has_strategy_generation_time_contract": summary_has_strategy_time,
        "preopen_available_all_rows": all_preopen,
        "institutional_rows_audited": len(institutional_rows),
        "margin_rows_audited": len(margin_rows),
        "contract_upgraded": upgrade_allowed,
        "existing_date_level_status_retained": p3_summary.get("orthogonal_refresh_status", {}).get("status"),
        "no_training": True,
        "no_top50_expansion": True,
        "accepted_latest_mutated": False,
        "provider_mutated": False,
        "monitor_trading_mutated": False,
    }
    write_json(audit_json, audit)

    report = [
        "# Phase P3S 执行报告：Pre-open Datetime Availability 判定",
        "",
        f"生成时间：`{created_at}`",
        "",
        "## 1. 结论",
        "",
        f"- gate：`{gate}`。",
        f"- signal_asof：`{audit['asof']}`。",
        "- 结论：不能证明 institutional / margin 的 T 日数据能稳定在 T+1 开盘前取得。",
        "- 未升级为 datetime available_at 合同，继续保留 P3RRR 后的日期级 `current_or_pit_delayed`。",
        "- 未训练 qlib / LTR，未调参，未扩大 Top50，未切 accepted latest，未触发 provider / monitor / trading。",
        "",
        "## 2. 判定依据",
        "",
        "- P3RRR raw archive 有 `fetched_at`，可追溯到 raw response / normalized archive。",
        "- 但 raw archive 与 latest feature table 没有可信 `available_at_datetime` / `used_available_at_datetime` 字段。",
        "- P3 rerank summary 没有 `strategy_generation_time`、`target_execution_date`、`target_open_datetime` 合同字段。",
        "- 现有 `fetched_at` 是本次 P3RRR 抓取时间，不是源数据发布或可取得时间；对历史交易日不能证明当时已在 T+1 开盘前可得。",
        f"- local raw archive 可审计最近交易日数量：`{meta['recent_trade_date_count']}`，要求至少 `5`；可见日期：`{meta['recent_trade_dates_available']}`。",
        "",
        "## 3. Pre-open Coverage Audit",
        "",
        *md(rows, fields),
        "",
        "## 4. 是否升级合同",
        "",
        "- 不升级。",
        "- 阻塞原因：缺少可信 datetime 级 availability timestamp；latest feature table 也未记录 used datetime；P3 summary 未记录 strategy generation / target open datetime。",
        "- 日期级 PIT 合同仍有效：`available_at >= next_trading_day(trade_date)` 且 as-of join 使用 `available_at <= signal_asof`。",
        "",
        "## 5. 只读与安全边界",
        "",
        "- P3 rerank 仍为 readonly artifact。",
        "- qlib Top50 candidate universe 不变。",
        "- 默认策略不变。",
        "- 未触发 accepted latest / provider / monitor / broker / orders / quick-trade。",
        "- 未输出 target position / target weight，未提供收益、胜率或上涨概率承诺。",
        "",
        "## 6. 输出 Artifact",
        "",
        f"- audit CSV：`{rel(audit_csv)}`",
        f"- audit JSON：`{rel(audit_json)}`",
        f"- report：`{rel(REPORT)}`",
        "",
        "## 7. 执行命令",
        "",
        "```text",
        "python -m py_compile scripts/audit_phasep3s_preopen_datetime_availability.py",
        "python scripts/audit_phasep3s_preopen_datetime_availability.py",
        "```",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "gate": gate, "audit": rel(audit_json), "report": rel(REPORT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
