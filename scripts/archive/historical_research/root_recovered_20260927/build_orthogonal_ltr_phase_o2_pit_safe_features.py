#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder"
DEFAULT_REPORT = ROOT / "docs/tw_ltr_orthogonal_features_controlled/PHASEO2_PIT_SAFE_FEATURE_BUILDER_EXECUTION_REPORT_CN.md"
RCPT15_R2_OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/rcpt15_r2_o2_pit_safe_feature_builder"
RCPT15_R2_REPORT = ROOT / "docs/tw_ltr_orthogonal_features_controlled/RCPT15_R2_O2_PIT_SAFE_FEATURE_BUILDER_EXECUTION_REPORT_CN.md"

CONTROL_SAMPLE = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv"
O1R_DIR = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair"
O1R_SUMMARY = O1R_DIR / "phaseo1r_summary.json"
O1R_MANIFEST = O1R_DIR / "raw_archive_manifest.csv"
O1R_COVERAGE = O1R_DIR / "coverage_before_after.csv"
P3RRR_DIR = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/source_freshness_raw_archive"
P3RRR_ATTEMPT_GLOB = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/source_freshness_attempts_*.csv"
PHASE0E_MANIFEST = ROOT / "data_tw/experiments/decision_orthogonal/phase0e_pit_snapshot_manifest.csv"
PHASE0E_NORMALIZED = {
    "institutional_flow": ROOT
    / "data_tw/experiments/decision_orthogonal/phase0e_raw_archive/institutional_flow/phase0e_institutional_flow_20260610T175901Z_normalized.csv",
    "margin_short": ROOT
    / "data_tw/experiments/decision_orthogonal/phase0e_raw_archive/margin_short/phase0e_margin_short_20260610T180330Z_normalized.csv",
}

CATEGORIES = ["institutional_flow", "margin_short"]
CONTRACT = "pit_safe_delayed_availability: available_at >= next_trading_day(trade_date); as-of join uses available_at <= sample_date"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def sha256_size(path: Path) -> str:
    if not path.exists():
        return ""
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()} size:{path.stat().st_size}"


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def md_table(rows: list[dict[str, Any]], fields: list[str], limit: int = 40) -> list[str]:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows[:limit]:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return lines


def next_trading_map(dates: list[pd.Timestamp]) -> dict[pd.Timestamp, pd.Timestamp]:
    ordered = sorted(pd.Series(pd.to_datetime(dates)).dropna().unique())
    return {ordered[idx]: ordered[idx + 1] for idx in range(len(ordered) - 1)}


def next_weekday(day: pd.Timestamp) -> pd.Timestamp:
    available = day + pd.Timedelta(days=1)
    while available.weekday() >= 5:
        available += pd.Timedelta(days=1)
    return available


def load_control() -> pd.DataFrame:
    control = pd.read_csv(CONTROL_SAMPLE, usecols=["date", "instrument", "sample_complete"])
    control = control.rename(columns={"date": "sample_date", "instrument": "symbol"})
    control["sample_date"] = pd.to_datetime(control["sample_date"], errors="coerce")
    control["control_row_id"] = range(len(control))
    return control


def load_lineage_maps() -> dict[str, dict[str, str]]:
    maps: dict[str, dict[str, str]] = {}
    if PHASE0E_MANIFEST.exists():
        m = pd.read_csv(PHASE0E_MANIFEST)
        for row in m.to_dict("records"):
            maps[str(row["raw_snapshot_id"])] = {
                "raw_snapshot_path": str(row.get("archive_path", "")),
                "raw_checksum_or_size": str(row.get("checksum_or_size", "")),
                "lineage_source": "phase0e",
            }
    if O1R_MANIFEST.exists():
        m = pd.read_csv(O1R_MANIFEST)
        for row in m.to_dict("records"):
            maps[str(row["raw_snapshot_id"])] = {
                "raw_snapshot_path": str(row.get("raw_path", "")),
                "raw_checksum_or_size": str(row.get("raw_checksum_or_size", "")),
                "lineage_source": "phaseo1r",
            }
    for path in sorted(P3RRR_ATTEMPT_GLOB.parent.glob(P3RRR_ATTEMPT_GLOB.name)):
        m = pd.read_csv(path)
        for row in m.to_dict("records"):
            raw_snapshot_id = Path(str(row.get("raw_path", ""))).name.replace("_raw_response.jsonl", "")
            if not raw_snapshot_id:
                continue
            raw_path = ROOT / str(row.get("raw_path", ""))
            checksum = sha256_size(raw_path)
            maps[raw_snapshot_id] = {
                "raw_snapshot_path": str(row.get("raw_path", "")),
                "raw_checksum_or_size": checksum,
                "lineage_source": f"p3rrr_source_freshness:{Path(path).stem}",
            }
    return maps


def load_category(category: str, control_symbols: set[str], include_p3rrr: bool) -> pd.DataFrame:
    parts = [pd.read_csv(PHASE0E_NORMALIZED[category])]
    for path in sorted((O1R_DIR / "raw_archive" / category).glob("*_normalized.csv")):
        parts.append(pd.read_csv(path))
    if include_p3rrr:
        for path in sorted((P3RRR_DIR / category).glob("*_normalized.csv")):
            parts.append(pd.read_csv(path))
    df = pd.concat(parts, ignore_index=True, sort=False)
    df = df[df["symbol"].astype(str).isin(control_symbols)].copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    df["available_at"] = pd.to_datetime(df["available_at"], errors="coerce")
    missing_available = df["available_at"].isna() & df["trade_date"].notna()
    df.loc[missing_available, "available_at"] = df.loc[missing_available, "trade_date"].map(next_weekday)
    if "quality_flags" not in df:
        df["quality_flags"] = ""
    df.loc[missing_available, "quality_flags"] = (
        df.loc[missing_available, "quality_flags"].fillna("").astype(str)
        + ";calendar_fallback_next_weekday_after_qlib_calendar_end"
    ).str.strip(";")
    df = df.dropna(subset=["symbol", "trade_date", "available_at"])
    df = df.sort_values(["symbol", "trade_date", "available_at", "raw_snapshot_id"]).drop_duplicates(
        ["symbol", "trade_date"], keep="last"
    )
    return df.reset_index(drop=True)


def classify_delay(df: pd.DataFrame, next_map: dict[pd.Timestamp, pd.Timestamp]) -> pd.DataFrame:
    out = df.copy()
    out["next_trading_day"] = out["trade_date"].map(next_map)
    out["delay_days"] = (out["available_at"] - out["next_trading_day"]).dt.days
    out["available_at_lt_next_trading_day"] = out["available_at"] < out["next_trading_day"]
    out["available_at_eq_next_trading_day"] = out["available_at"] == out["next_trading_day"]
    out["available_at_gt_next_trading_day"] = out["available_at"] > out["next_trading_day"]
    out["prohibited_early_visible"] = out["available_at"] <= out["trade_date"]
    out["delay_reason"] = "exact_t1"
    out.loc[out["next_trading_day"].isna(), "delay_reason"] = "missing_calendar"
    out.loc[out["available_at_lt_next_trading_day"] & ~out["prohibited_early_visible"], "delay_reason"] = "calendar_gap"
    out.loc[out["prohibited_early_visible"], "delay_reason"] = "data_quality_unknown"
    delayed = out["available_at_gt_next_trading_day"].fillna(False)
    delay_by_symbol = out[delayed].groupby("symbol").size().to_dict()
    out.loc[delayed & out["symbol"].map(delay_by_symbol).fillna(0).ge(20), "delay_reason"] = "listing_status_gap"
    out.loc[delayed & out["symbol"].map(delay_by_symbol).fillna(0).lt(20), "delay_reason"] = "calendar_gap"
    out["available_at_contract"] = CONTRACT
    return out


def add_lineage(df: pd.DataFrame, maps: dict[str, dict[str, str]]) -> pd.DataFrame:
    out = df.copy()
    out["raw_snapshot_path"] = out["raw_snapshot_id"].astype(str).map(lambda x: maps.get(x, {}).get("raw_snapshot_path", ""))
    out["raw_checksum_or_size"] = out["raw_snapshot_id"].astype(str).map(lambda x: maps.get(x, {}).get("raw_checksum_or_size", ""))
    out["lineage_source"] = out["raw_snapshot_id"].astype(str).map(lambda x: maps.get(x, {}).get("lineage_source", "unknown"))
    return out


def streak(values: pd.Series) -> pd.Series:
    result = []
    current_sign = 0
    current_count = 0
    for value in values.fillna(0):
        sign = 1 if value > 0 else (-1 if value < 0 else 0)
        if sign == 0:
            current_sign = 0
            current_count = 0
            result.append(0)
        elif sign == current_sign:
            current_count += 1
            result.append(current_sign * current_count)
        else:
            current_sign = sign
            current_count = 1
            result.append(current_sign * current_count)
    return pd.Series(result, index=values.index)


def build_institutional_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["symbol", "trade_date"]).copy()
    base_cols = ["foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy", "institutional_total_net_buy"]
    for col in base_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        for window in [1, 3, 5, 10]:
            out[f"{col}_roll{window}"] = out.groupby("symbol")[col].transform(lambda s: s.rolling(window, min_periods=1).sum())
    out["institutional_total_net_buy_streak"] = out.groupby("symbol")["institutional_total_net_buy"].transform(streak)
    out["institutional_missing_flag"] = 0
    out["institutional_delay_flag"] = (out["delay_reason"] != "exact_t1").astype(int)
    out["feature_family"] = "institutional_flow"
    return out


def build_margin_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["symbol", "trade_date"]).copy()
    base_cols = ["margin_balance", "margin_balance_change", "short_balance", "short_balance_change"]
    for col in base_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in ["margin_balance_change", "short_balance_change"]:
        for window in [1, 3, 5, 10]:
            out[f"{col}_roll{window}"] = out.groupby("symbol")[col].transform(lambda s: s.rolling(window, min_periods=1).sum())
    out["margin_direction_proxy"] = (out["margin_balance_change"] > 0).astype(int) - (out["margin_balance_change"] < 0).astype(int)
    out["short_direction_proxy"] = (out["short_balance_change"] > 0).astype(int) - (out["short_balance_change"] < 0).astype(int)
    out["margin_short_divergence_proxy"] = out["margin_direction_proxy"] - out["short_direction_proxy"]
    out["margin_short_missing_flag"] = 0
    out["margin_short_delay_flag"] = (out["delay_reason"] != "exact_t1").astype(int)
    out["feature_family"] = "margin_short"
    return out


def asof_audit(control: pd.DataFrame, features: pd.DataFrame, family: str) -> pd.DataFrame:
    rows = []
    feat = features.sort_values(["symbol", "available_at"]).copy()
    for symbol, left in control.groupby("symbol", sort=False):
        right = feat[feat["symbol"] == symbol]
        left_sorted = left.sort_values("sample_date")
        if right.empty:
            tmp = left_sorted[["control_row_id", "symbol", "sample_date"]].copy()
            tmp["feature_family"] = family
            tmp["matched_trade_date"] = pd.NaT
            tmp["matched_available_at"] = pd.NaT
            tmp["matched_raw_snapshot_id"] = ""
            tmp["missing_flag"] = 1
        else:
            merged = pd.merge_asof(
                left_sorted,
                right.sort_values("available_at"),
                left_on="sample_date",
                right_on="available_at",
                by="symbol",
                direction="backward",
                allow_exact_matches=True,
            )
            tmp = pd.DataFrame(
                {
                    "control_row_id": merged["control_row_id"],
                    "symbol": merged["symbol"],
                    "sample_date": merged["sample_date"],
                    "feature_family": family,
                    "matched_trade_date": merged["trade_date"],
                    "matched_available_at": merged["available_at"],
                    "matched_raw_snapshot_id": merged["raw_snapshot_id"].fillna(""),
                    "missing_flag": merged["available_at"].isna().astype(int),
                }
            )
        rows.append(tmp)
    audit = pd.concat(rows, ignore_index=True)
    audit["used_available_at_gt_sample_date"] = (
        audit["matched_available_at"].notna() & (audit["matched_available_at"] > audit["sample_date"])
    )
    audit["used_trade_date_gt_sample_date"] = audit["matched_trade_date"].notna() & (audit["matched_trade_date"] > audit["sample_date"])
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build isolated PIT-safe O2 orthogonal feature artifact.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUT,
        help="Output directory for O2 artifacts.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT,
        help="Markdown execution report path.",
    )
    parser.add_argument(
        "--include-p3rrr-source-freshness",
        action="store_true",
        help="Include daily_ltr_rerank/source_freshness_raw_archive normalized rows.",
    )
    parser.add_argument(
        "--rcpt15-r2-isolated",
        action="store_true",
        help="Use RCPT15_R2 isolated output/report paths and include P3RRR source freshness rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = RCPT15_R2_OUT if args.rcpt15_r2_isolated else args.output_dir
    report_path = RCPT15_R2_REPORT if args.rcpt15_r2_isolated else args.report_path
    include_p3rrr = bool(args.include_p3rrr_source_freshness or args.rcpt15_r2_isolated)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = now()
    o1r_summary = json.loads(O1R_SUMMARY.read_text(encoding="utf-8"))
    control = load_control()
    control_symbols = set(control["symbol"].astype(str).unique())
    next_map = next_trading_map(control["sample_date"].tolist())
    lineage_maps = load_lineage_maps()

    normalized_parts = []
    feature_parts = []
    lineage_rows = []
    delay_rows = []
    for category in CATEGORIES:
        raw = load_category(category, control_symbols, include_p3rrr)
        enriched = add_lineage(classify_delay(raw, next_map), lineage_maps)
        if category == "institutional_flow":
            featured = build_institutional_features(enriched)
        else:
            featured = build_margin_features(enriched)
        normalized_parts.append(enriched.assign(feature_family=category))
        feature_parts.append(featured)
        lineage_rows.append(
            {
                "feature_family": category,
                "input_rows": int(len(raw)),
                "output_rows": int(len(featured)),
                "symbol_count": int(featured["symbol"].nunique()),
                "trade_date_min": str(featured["trade_date"].min())[:10],
                "trade_date_max": str(featured["trade_date"].max())[:10],
                "available_at_min": str(featured["available_at"].min())[:10],
                "available_at_max": str(featured["available_at"].max())[:10],
                "lineage_sources": "|".join(sorted(featured["lineage_source"].dropna().astype(str).unique())),
                "raw_snapshot_count": int(featured["raw_snapshot_id"].nunique()),
                "missing_raw_snapshot_path_rows": int(featured["raw_snapshot_path"].fillna("").astype(str).eq("").sum()),
            }
        )
        for reason, reason_group in featured.groupby("delay_reason", dropna=False):
            delay_values = reason_group["delay_days"].dropna()
            delay_rows.append(
                {
                    "feature_family": category,
                    "delay_reason": str(reason),
                    "row_count": int(len(reason_group)),
                    "min_delay_days": "" if delay_values.empty else int(delay_values.min()),
                    "max_delay_days": "" if delay_values.empty else int(delay_values.max()),
                }
            )

    normalized = pd.concat(normalized_parts, ignore_index=True, sort=False)
    features = pd.concat(feature_parts, ignore_index=True, sort=False)

    # Keep a daily feature builder artifact, not a final control-row treatment sample.
    feature_daily_path = out_dir / "normalized_feature_daily.csv"
    normalized_path = out_dir / "pit_normalized_daily_with_lineage.csv"
    features.to_csv(feature_daily_path, index=False)
    normalized.to_csv(normalized_path, index=False)

    audit_parts = []
    for category in CATEGORIES:
        audit_parts.append(asof_audit(control, features[features["feature_family"] == category], category))
    asof = pd.concat(audit_parts, ignore_index=True)
    asof.to_csv(out_dir / "pit_lineage_audit.csv", index=False)
    leak_summary = []
    for family, group in asof.groupby("feature_family"):
        leak_summary.append(
            {
                "feature_family": family,
                "control_rows_checked": int(group["control_row_id"].nunique()),
                "audit_rows": int(len(group)),
                "missing_rows": int(group["missing_flag"].sum()),
                "missing_ratio": float(group["missing_flag"].mean()),
                "used_available_at_gt_sample_date_rows": int(group["used_available_at_gt_sample_date"].sum()),
                "used_trade_date_gt_sample_date_rows": int(group["used_trade_date_gt_sample_date"].sum()),
            }
        )
    write_csv(out_dir / "pit_leakage_audit.csv", leak_summary)

    missing_family = [
        {
            "feature_family": row["feature_family"],
            "control_rows": row["control_rows_checked"],
            "missing_rows": row["missing_rows"],
            "missing_ratio": row["missing_ratio"],
        }
        for row in leak_summary
    ]
    write_csv(out_dir / "missing_by_feature_family.csv", missing_family)
    missing_symbol = []
    for (family, symbol), group in asof.groupby(["feature_family", "symbol"]):
        missing_symbol.append(
            {
                "feature_family": family,
                "symbol": symbol,
                "control_rows": int(len(group)),
                "missing_rows": int(group["missing_flag"].sum()),
                "missing_ratio": float(group["missing_flag"].mean()),
            }
        )
    write_csv(out_dir / "missing_by_symbol.csv", missing_symbol)
    missing_date = []
    for (family, date), group in asof.groupby(["feature_family", "sample_date"]):
        missing_date.append(
            {
                "feature_family": family,
                "sample_date": str(date)[:10],
                "control_rows": int(len(group)),
                "missing_rows": int(group["missing_flag"].sum()),
                "missing_ratio": float(group["missing_flag"].mean()),
            }
        )
    write_csv(out_dir / "missing_by_date.csv", missing_date)

    feature_dictionary = [
        {"feature": "foreign_net_buy", "family": "institutional_flow", "source": "FinMind institutional", "neutral_fill": 0, "notes": "raw net buy"},
        {"feature": "investment_trust_net_buy", "family": "institutional_flow", "source": "FinMind institutional", "neutral_fill": 0, "notes": "raw net buy"},
        {"feature": "dealer_net_buy", "family": "institutional_flow", "source": "FinMind institutional", "neutral_fill": 0, "notes": "raw net buy"},
        {"feature": "institutional_total_net_buy", "family": "institutional_flow", "source": "FinMind institutional", "neutral_fill": 0, "notes": "sum of investor groups"},
        {"feature": "*_roll1/3/5/10", "family": "institutional_flow", "source": "derived from institutional net buy", "neutral_fill": 0, "notes": "rolling sum by trade_date within symbol"},
        {"feature": "institutional_total_net_buy_streak", "family": "institutional_flow", "source": "derived from institutional_total_net_buy", "neutral_fill": 0, "notes": "positive buy streak, negative sell streak"},
        {"feature": "institutional_missing_flag", "family": "institutional_flow", "source": "as-of availability", "neutral_fill": 1, "notes": "daily row has 0; control-row join missing flag produced in audit"},
        {"feature": "institutional_delay_flag / delay_days / delay_reason", "family": "institutional_flow", "source": "available_at contract", "neutral_fill": 0, "notes": "PIT-safe delayed availability metadata"},
        {"feature": "margin_balance", "family": "margin_short", "source": "FinMind margin", "neutral_fill": 0, "notes": "raw balance"},
        {"feature": "margin_balance_change", "family": "margin_short", "source": "FinMind margin", "neutral_fill": 0, "notes": "raw balance change"},
        {"feature": "short_balance", "family": "margin_short", "source": "FinMind margin", "neutral_fill": 0, "notes": "raw short balance"},
        {"feature": "short_balance_change", "family": "margin_short", "source": "FinMind margin", "neutral_fill": 0, "notes": "raw short balance change"},
        {"feature": "margin_balance_change_roll1/3/5/10", "family": "margin_short", "source": "derived from margin_balance_change", "neutral_fill": 0, "notes": "rolling sum by trade_date within symbol"},
        {"feature": "short_balance_change_roll1/3/5/10", "family": "margin_short", "source": "derived from short_balance_change", "neutral_fill": 0, "notes": "rolling sum by trade_date within symbol"},
        {"feature": "margin_direction_proxy / short_direction_proxy / margin_short_divergence_proxy", "family": "margin_short", "source": "derived from balance changes", "neutral_fill": 0, "notes": "direction proxies"},
        {"feature": "margin_short_missing_flag", "family": "margin_short", "source": "as-of availability", "neutral_fill": 1, "notes": "daily row has 0; control-row join missing flag produced in audit"},
        {"feature": "margin_short_delay_flag / delay_days / delay_reason", "family": "margin_short", "source": "available_at contract", "neutral_fill": 0, "notes": "PIT-safe delayed availability metadata"},
        {"feature": "buy_sell_over_volume_ratio", "family": "institutional_flow", "source": "deferred", "neutral_fill": "", "notes": "not built in O2 because volume is outside O1R-reviewed fields"},
    ]
    write_csv(out_dir / "feature_dictionary.csv", feature_dictionary)
    write_csv(out_dir / "pit_lineage_summary.csv", lineage_rows)
    write_csv(out_dir / "delay_distribution.csv", delay_rows)

    available_contract = []
    for category, group in normalized.groupby("feature_family"):
        available_contract.append(
            {
                "feature_family": category,
                "rows": int(len(group)),
                "available_at_le_trade_date_rows": int((group["available_at"] <= group["trade_date"]).sum()),
                "available_at_gt_trade_date_rows": int((group["available_at"] > group["trade_date"]).sum()),
                "available_at_lt_next_trading_day_rows": int(group["available_at_lt_next_trading_day"].fillna(False).sum()),
                "available_at_gt_next_trading_day_rows": int(group["available_at_gt_next_trading_day"].fillna(False).sum()),
                "missing_next_trading_day_rows": int(group["next_trading_day"].isna().sum()),
            }
        )
    write_csv(out_dir / "available_at_contract_audit.csv", available_contract)

    stop_triggered = (
        any(row["used_available_at_gt_sample_date_rows"] for row in leak_summary)
        or any(row["available_at_le_trade_date_rows"] for row in available_contract)
        or int(normalized["raw_snapshot_path"].fillna("").astype(str).eq("").sum()) > 0
    )
    gate = "phase_o2_pit_safe_feature_builder_passed" if not stop_triggered else "phase_o2_blocked_requires_repair"
    manifest = {
        "created_at": generated_at,
        "phase": "phase_o2_pit_safe_feature_builder",
        "gate": gate,
        "available_at_contract": CONTRACT,
        "o1r_gate_assumed_after_user_confirmation": "phase_o1r_passed_after_user_confirmation_for_pit_safe_delayed_availability",
        "control_rows_read_only": int(len(control)),
        "control_symbol_count": int(len(control_symbols)),
        "feature_daily_rows": int(len(features)),
        "feature_daily_symbol_count": int(features["symbol"].nunique()),
        "feature_daily_date_min": str(features["trade_date"].min())[:10],
        "feature_daily_date_max": str(features["trade_date"].max())[:10],
        "lineage": lineage_rows,
        "leakage_audit": leak_summary,
        "available_at_contract_audit": available_contract,
        "no_training": True,
        "no_replay": True,
        "no_final_treatment_sample": True,
        "no_control_change": True,
        "no_frontend_api_provider_accepted_latest_monitor_trading": True,
        "include_p3rrr_source_freshness": include_p3rrr,
        "p3rrr_source_freshness_dir": rel(P3RRR_DIR),
        "isolated_output_dir": rel(out_dir),
    }
    write_json(out_dir / "feature_builder_manifest.json", manifest)
    write_json(out_dir / "phaseo2_summary.json", manifest)

    low_cov = []
    if O1R_COVERAGE.exists():
        cov = pd.read_csv(O1R_COVERAGE)
        low_cov = cov[pd.to_numeric(cov["after_coverage_rate"], errors="coerce") < 0.95].sort_values(
            ["category", "after_coverage_rate"]
        ).to_dict("records")

    report_lines = [
        "# Phase O2 执行报告：PIT-safe Feature Builder",
        "",
        f"生成时间：`{generated_at}`",
        "",
        "## 1. 执行结论",
        "",
        "本轮只基于 O1R 已确认的法人筹码与融资融券数据构建 PIT-safe daily feature builder，并输出 lineage、missing、delay 与 PIT leakage 审计。",
        "",
        "推荐 gate：",
        "",
        "```text",
        gate,
        "```",
        "",
        "## 2. 边界",
        "",
        "- 未训练 qlib/LTR。",
        "- 未回放收益率。",
        "- 未构建最终 treatment LTR sample。",
        "- 未修改 Phase1C control。",
        "- 未新增月营收或 O1R 未审查数据源。",
        "- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。",
        "",
        "## 3. 输入 Artifact",
        "",
        f"- `{rel(CONTROL_SAMPLE)}` read-only，用于 symbol/sample_date/control row universe。",
        f"- `{rel(O1R_DIR)}/`。",
        f"- `{rel(PHASE0E_MANIFEST)}`。",
        "",
        "## 4. 输出 Artifact",
        "",
        f"- `{rel(out_dir / 'feature_dictionary.csv')}`",
        f"- `{rel(feature_daily_path)}`",
        f"- `{rel(normalized_path)}`",
        f"- `{rel(out_dir / 'feature_builder_manifest.json')}`",
        f"- `{rel(out_dir / 'pit_lineage_audit.csv')}`",
        f"- `{rel(out_dir / 'pit_leakage_audit.csv')}`",
        f"- `{rel(out_dir / 'missing_by_feature_family.csv')}`",
        f"- `{rel(out_dir / 'missing_by_symbol.csv')}`",
        f"- `{rel(out_dir / 'missing_by_date.csv')}`",
        f"- `{rel(out_dir / 'delay_distribution.csv')}`",
        f"- `{rel(out_dir / 'phaseo2_summary.json')}`",
        "",
        "## 5. Row Count / Symbol / Date Range",
        "",
        *md_table(lineage_rows, ["feature_family", "input_rows", "output_rows", "symbol_count", "trade_date_min", "trade_date_max", "available_at_min", "available_at_max", "lineage_sources", "missing_raw_snapshot_path_rows"]),
        "",
        "## 6. available_at 合同统计",
        "",
        *md_table(available_contract, ["feature_family", "rows", "available_at_le_trade_date_rows", "available_at_gt_trade_date_rows", "available_at_lt_next_trading_day_rows", "available_at_gt_next_trading_day_rows", "missing_next_trading_day_rows"]),
        "",
        "## 7. Delay 分布",
        "",
        *md_table(delay_rows, ["feature_family", "delay_reason", "row_count", "min_delay_days", "max_delay_days"], limit=20),
        "",
        "## 8. Missing Ratio by Feature Family",
        "",
        *md_table(missing_family, ["feature_family", "control_rows", "missing_rows", "missing_ratio"]),
        "",
        "## 9. 低覆盖 Symbols",
        "",
        *md_table(low_cov, ["category", "symbol", "after_coverage_rate", "after_raw_rows", "after_missing_control_dates"], limit=30),
        "",
        "## 10. PIT Leakage Audit",
        "",
        *md_table(leak_summary, ["feature_family", "control_rows_checked", "audit_rows", "missing_rows", "missing_ratio", "used_available_at_gt_sample_date_rows", "used_trade_date_gt_sample_date_rows"]),
        "",
        "## 11. Control 不变性",
        "",
        f"- control rows read-only checked：`{len(control)}`。",
        f"- control symbols：`{len(control_symbols)}`。",
        "- 未写回 control sample。",
        "- 未输出最终 treatment LTR sample；`pit_lineage_audit.csv` 仅含 lineage/可用性/泄漏审计列。",
        "",
        "## 12. 停止条件复核",
        "",
        f"- as-of join 使用 `available_at > sample_date` 行：`{sum(row['used_available_at_gt_sample_date_rows'] for row in leak_summary)}`。",
        f"- `available_at <= trade_date` 禁止性提前可见行：`{sum(row['available_at_le_trade_date_rows'] for row in available_contract)}`。",
        f"- 缺 raw lineage path 行：`{int(normalized['raw_snapshot_path'].fillna('').astype(str).eq('').sum())}`。",
        f"- stop_triggered：`{stop_triggered}`。",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "gate": gate, "report": rel(report_path), "summary": rel(out_dir / "phaseo2_summary.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
