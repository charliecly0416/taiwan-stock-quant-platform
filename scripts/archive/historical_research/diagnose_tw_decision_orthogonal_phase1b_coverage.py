#!/usr/bin/env python3
"""Readonly Phase1B coverage diagnosis.

This script explains Phase1B Full sample gaps without network, token, qlib
provider writes, model training, rules baseline, or Phase2 actions.
"""
from __future__ import annotations

import glob
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
QLIB = ROOT / "qlib_pipeline"
OUT_DIR = ROOT / "data_tw/experiments/decision_orthogonal"
DOC_DIR = ROOT / "docs/tw_decision_model_orthogonal"
MANIFEST_PATH = OUT_DIR / "phase0e_pit_snapshot_manifest.csv"
PRICE_ROOT = QLIB / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
SIGNAL_ROOT = QLIB / "data_tw/experiments/option_c_historical_signal_backfill"
DAILY_SIGNAL_ROOT = QLIB / "data_tw/experiments/option_c_daily_signal"
PREFIX = "phase1b_coverage_diagnosis"
PHASE0E_COVERAGE_PATH = OUT_DIR / f"{PREFIX}_phase0e_monthly_coverage.csv"
PRICE_COVERAGE_PATH = OUT_DIR / f"{PREFIX}_price_monthly_coverage.csv"
PREDICTION_COVERAGE_PATH = OUT_DIR / f"{PREFIX}_prediction_monthly_coverage.csv"
DROPOFF_PATH = OUT_DIR / f"{PREFIX}_join_dropoff_monthly.csv"
SUMMARY_PATH = OUT_DIR / f"{PREFIX}_summary.json"
REPORT_PATH = DOC_DIR / "PHASE1B_COVERAGE_DIAGNOSIS_REPORT_CN.md"
HORIZONS = [5, 10, 20]
START = pd.Timestamp("2022-01-01")
END = pd.Timestamp("2026-05-29")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def parse_date_from_path(path: Path) -> pd.Timestamp | None:
    match = re.search(r"option_c_daily_signal_(\d{8})", str(path))
    if not match:
        return None
    return pd.Timestamp(datetime.strptime(match.group(1), "%Y%m%d")).normalize()


def month_range(start: pd.Timestamp = START, end: pd.Timestamp = END) -> pd.DataFrame:
    months = pd.period_range(start=start.to_period("M"), end=end.to_period("M"), freq="M").astype(str)
    return pd.DataFrame({"month": months})


def archive_path(manifest: pd.DataFrame, category: str) -> Path:
    rows = manifest[manifest["category"] == category]
    if rows.empty:
        raise RuntimeError(f"missing category={category}")
    return ROOT / str(rows.iloc[0]["archive_path"])


def load_phase0e() -> tuple[pd.DataFrame, pd.DataFrame, set[str]]:
    manifest = pd.read_csv(MANIFEST_PATH)
    inst = pd.read_csv(archive_path(manifest, "institutional_flow"), dtype={"stock_id": str})
    margin = pd.read_csv(archive_path(manifest, "margin_short"), dtype={"stock_id": str})
    for df in [inst, margin]:
        df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce").dt.normalize()
        df["available_at"] = pd.to_datetime(df["available_at"], errors="coerce").dt.normalize()
        df["symbol"] = df["symbol"].astype(str)
        df["month"] = df["available_at"].dt.strftime("%Y-%m")
    symbols = set(inst["symbol"].dropna().astype(str)) | set(margin["symbol"].dropna().astype(str))
    return inst, margin, symbols


def phase0e_monthly_coverage(inst: pd.DataFrame, margin: pd.DataFrame) -> pd.DataFrame:
    rows = month_range()
    for name, df in [("institutional", inst), ("margin", margin)]:
        agg = df.groupby("month").agg(**{
            f"{name}_rows": ("symbol", "size"),
            f"{name}_symbols": ("symbol", "nunique"),
            f"{name}_first_trade_date": ("trade_date", "min"),
            f"{name}_last_trade_date": ("trade_date", "max"),
        }).reset_index()
        rows = rows.merge(agg, on="month", how="left")
    for col in ["institutional_rows", "institutional_symbols", "margin_rows", "margin_symbols"]:
        rows[col] = rows[col].fillna(0).astype(int)
    rows["phase0e_has_both"] = (rows["institutional_rows"] > 0) & (rows["margin_rows"] > 0)
    return rows


def load_price(symbol: str) -> pd.DataFrame:
    path = PRICE_ROOT / f"{symbol}.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, usecols=["date", "close"])
    except Exception:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)


def price_monthly_coverage(symbols: set[str]) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], pd.DataFrame]:
    price_map: dict[str, pd.DataFrame] = {}
    rows = []
    for symbol in sorted(symbols):
        df = load_price(symbol)
        if df.empty:
            continue
        df["month"] = df["date"].dt.strftime("%Y-%m")
        price_map[symbol] = df
        rows.append(df.assign(symbol=symbol)[["symbol", "date", "month"]])
    all_prices = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["symbol", "date", "month"])
    cov = month_range()
    if not all_prices.empty:
        agg = all_prices.groupby("month").agg(price_rows=("symbol", "size"), price_symbols=("symbol", "nunique")).reset_index()
        cov = cov.merge(agg, on="month", how="left")
    twii = load_price("TWII")
    if not twii.empty:
        twii["month"] = twii["date"].dt.strftime("%Y-%m")
        cov = cov.merge(twii.groupby("month").agg(twii_rows=("date", "size")).reset_index(), on="month", how="left")
    for col in ["price_rows", "price_symbols", "twii_rows"]:
        if col not in cov.columns:
            cov[col] = 0
        cov[col] = cov[col].fillna(0).astype(int)
    cov["price_has_sample_symbols"] = cov["price_symbols"] > 0
    cov["twii_has_rows"] = cov["twii_rows"] > 0
    return cov, price_map, twii


def prediction_paths() -> list[Path]:
    paths = [Path(p) for p in glob.glob(str(SIGNAL_ROOT / "*/*/prediction.csv"))]
    paths += [Path(p) for p in glob.glob(str(DAILY_SIGNAL_ROOT / "*/prediction.csv"))]
    return sorted(set(paths))


def load_predictions(symbols: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    file_rows = []
    for path in prediction_paths():
        path_day = parse_date_from_path(path)
        if path_day is None or path_day < START or path_day > END:
            continue
        try:
            df = pd.read_csv(path, usecols=["datetime", "instrument", "score"])
        except Exception as exc:
            file_rows.append({"path": rel(path), "asof": path_day, "month": path_day.strftime("%Y-%m"), "file_read_ok": False, "error": str(exc), "rows": 0, "symbols": 0, "filtered_rows": 0, "filtered_symbols": 0})
            continue
        df["asof"] = pd.to_datetime(df["datetime"], errors="coerce").dt.normalize()
        df["symbol"] = df["instrument"].astype(str)
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
        df = df[df["asof"].notna() & df["score"].notna()]
        filtered = df[(df["asof"] >= START) & (df["asof"] <= END) & df["symbol"].isin(symbols)].copy()
        file_rows.append({"path": rel(path), "asof": path_day, "month": path_day.strftime("%Y-%m"), "file_read_ok": True, "error": "", "rows": int(len(df)), "symbols": int(df["symbol"].nunique()), "filtered_rows": int(len(filtered)), "filtered_symbols": int(filtered["symbol"].nunique())})
        if not filtered.empty:
            rows.append(filtered[["asof", "symbol", "score"]])
    pred = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["asof", "symbol", "score"])
    if not pred.empty:
        pred = pred.drop_duplicates(["asof", "symbol"], keep="last")
        pred["month"] = pred["asof"].dt.strftime("%Y-%m")
    return pred, pd.DataFrame(file_rows)


def prediction_monthly_coverage(pred: pd.DataFrame, files: pd.DataFrame) -> pd.DataFrame:
    cov = month_range()
    if not files.empty:
        fagg = files.groupby("month").agg(prediction_file_count=("path", "size"), readable_file_count=("file_read_ok", "sum"), raw_prediction_rows=("rows", "sum"), raw_prediction_symbols_max=("symbols", "max"), filtered_file_rows=("filtered_rows", "sum")).reset_index()
        cov = cov.merge(fagg, on="month", how="left")
    if not pred.empty:
        pagg = pred.groupby("month").agg(prediction_rows=("symbol", "size"), prediction_symbols=("symbol", "nunique"), prediction_days=("asof", "nunique")).reset_index()
        cov = cov.merge(pagg, on="month", how="left")
    for col in ["prediction_file_count", "readable_file_count", "raw_prediction_rows", "raw_prediction_symbols_max", "filtered_file_rows", "prediction_rows", "prediction_symbols", "prediction_days"]:
        if col not in cov.columns:
            cov[col] = 0
        cov[col] = cov[col].fillna(0).astype(int)
    cov["has_prediction"] = cov["prediction_rows"] > 0
    return cov


def add_forward_cols(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    out = df.copy()
    for h in HORIZONS:
        out[f"{prefix}_fwd_{h}d_date"] = out["date"].shift(-h)
    return out


def pit_flags(pred: pd.DataFrame, inst: pd.DataFrame, margin: pd.DataFrame) -> pd.DataFrame:
    out_chunks = []
    inst_small = inst[["symbol", "available_at"]].dropna().sort_values(["symbol", "available_at"])
    margin_small = margin[["symbol", "available_at"]].dropna().sort_values(["symbol", "available_at"])
    base = pred[["asof", "symbol"]].drop_duplicates().sort_values(["symbol", "asof"]).copy()
    for symbol, left in base.groupby("symbol"):
        left = left.sort_values("asof").copy()
        i = inst_small[inst_small["symbol"] == symbol]
        m = margin_small[margin_small["symbol"] == symbol]
        if not i.empty:
            left = pd.merge_asof(left, i.sort_values("available_at"), by="symbol", left_on="asof", right_on="available_at", direction="backward")
            left = left.rename(columns={"available_at": "institutional_available_at"})
        else:
            left["institutional_available_at"] = pd.NaT
        if not m.empty:
            left = pd.merge_asof(left, m.sort_values("available_at"), by="symbol", left_on="asof", right_on="available_at", direction="backward")
            left = left.rename(columns={"available_at": "margin_available_at"})
        else:
            left["margin_available_at"] = pd.NaT
        out_chunks.append(left)
    out = pd.concat(out_chunks, ignore_index=True) if out_chunks else base
    out["has_institutional_pit"] = out["institutional_available_at"].notna() & (out["institutional_available_at"] <= out["asof"])
    out["has_margin_pit"] = out["margin_available_at"].notna() & (out["margin_available_at"] <= out["asof"])
    return out[["asof", "symbol", "has_institutional_pit", "has_margin_pit"]]


def join_dropoff(pred: pd.DataFrame, inst: pd.DataFrame, margin: pd.DataFrame, price_map: dict[str, pd.DataFrame], twii: pd.DataFrame) -> pd.DataFrame:
    months = month_range()
    if pred.empty:
        out = months.copy()
        for col in ["prediction_rows", "after_price_rows", "after_twii_rows", "after_pit_rows", "final_all_horizons_rows", "no_price", "no_twii_label", "no_institutional_pit", "no_margin_pit", "label_horizon_missing"]:
            out[col] = 0
        out["no_prediction"] = 1
        return out
    rows = pred[["asof", "symbol"]].drop_duplicates().copy()
    rows["month"] = rows["asof"].dt.strftime("%Y-%m")
    price_dates = []
    for symbol, df in price_map.items():
        tmp = add_forward_cols(df, "stock")
        cols = ["date"] + [f"stock_fwd_{h}d_date" for h in HORIZONS]
        tmp = tmp[cols].copy()
        tmp["symbol"] = symbol
        price_dates.append(tmp)
    stock_labels = pd.concat(price_dates, ignore_index=True) if price_dates else pd.DataFrame(columns=["date", "symbol"])
    twii_labels = add_forward_cols(twii, "twii") if not twii.empty else pd.DataFrame(columns=["date"])
    twii_cols = ["date"] + [f"twii_fwd_{h}d_date" for h in HORIZONS if f"twii_fwd_{h}d_date" in twii_labels.columns]
    rows = rows.merge(stock_labels.rename(columns={"date": "asof"}), on=["asof", "symbol"], how="left")
    rows = rows.merge(twii_labels[twii_cols].rename(columns={"date": "asof"}) if not twii_labels.empty else twii_labels.rename(columns={"date": "asof"}), on="asof", how="left")
    rows = rows.merge(pit_flags(rows[["asof", "symbol"]], inst, margin), on=["asof", "symbol"], how="left")
    rows["has_price_at_asof"] = rows[[f"stock_fwd_{h}d_date" for h in HORIZONS]].notna().any(axis=1)
    rows["has_twii_at_asof"] = rows[[f"twii_fwd_{h}d_date" for h in HORIZONS]].notna().any(axis=1)
    stock_all = np.logical_and.reduce([(rows[f"stock_fwd_{h}d_date"].notna() & (rows[f"stock_fwd_{h}d_date"] > rows["asof"])) for h in HORIZONS])
    twii_all = np.logical_and.reduce([(rows[f"twii_fwd_{h}d_date"].notna() & (rows[f"twii_fwd_{h}d_date"] > rows["asof"])) for h in HORIZONS])
    rows["has_all_labels"] = stock_all & twii_all
    rows["has_all_pit"] = rows["has_institutional_pit"].fillna(False) & rows["has_margin_pit"].fillna(False)
    rows["final_valid"] = rows["has_all_labels"] & rows["has_all_pit"]
    rows["no_price"] = ~rows["has_price_at_asof"]
    rows["no_twii_label"] = rows["has_price_at_asof"] & ~rows["has_twii_at_asof"]
    rows["no_institutional_pit"] = ~rows["has_institutional_pit"].fillna(False)
    rows["no_margin_pit"] = ~rows["has_margin_pit"].fillna(False)
    rows["label_horizon_missing"] = rows["has_price_at_asof"] & rows["has_twii_at_asof"] & ~rows["has_all_labels"]
    agg = rows.groupby("month").agg(
        prediction_rows=("symbol", "size"), after_price_rows=("has_price_at_asof", "sum"), after_twii_rows=("has_twii_at_asof", "sum"), after_pit_rows=("has_all_pit", "sum"), final_all_horizons_rows=("final_valid", "sum"), no_price=("no_price", "sum"), no_twii_label=("no_twii_label", "sum"), no_institutional_pit=("no_institutional_pit", "sum"), no_margin_pit=("no_margin_pit", "sum"), label_horizon_missing=("label_horizon_missing", "sum")
    ).reset_index()
    out = months.merge(agg, on="month", how="left")
    for col in out.columns:
        if col != "month":
            out[col] = out[col].fillna(0).astype(int)
    out["no_prediction"] = (out["prediction_rows"] == 0).astype(int)
    return out


def md_table(df: pd.DataFrame, cols: list[str], max_rows: int | None = None) -> str:
    sub = df[cols].copy()
    if max_rows is not None:
        sub = sub.head(max_rows)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for row in sub.to_dict("records"):
        lines.append("| " + " | ".join(str(row.get(c, "")) for c in cols) + " |")
    return "\n".join(lines)


def write_report(summary: dict[str, Any], phase0e_cov: pd.DataFrame, price_cov: pd.DataFrame, pred_cov: pd.DataFrame, dropoff: pd.DataFrame) -> None:
    pred_gap = pred_cov[(pred_cov["month"] >= "2023-01") & (pred_cov["month"] <= "2024-12")]
    report = [
        "# Phase 1B Coverage Diagnosis 报告", "", f"- 生成时间：`{utc_now()}`", "- 本步骤只做只读覆盖缺口诊断；未联网、未使用 token、未重拉数据、未训练模型、未生成 qlib predictions、未写 provider、未进入 Phase2。", f"- 结论：`{summary['gate']}`", f"- 结论理由：{summary['reason']}", "",
        "## 1. Phase0E Archive 覆盖", "", "Phase0E institutional/margin normalized archive 在 2023-2024 均存在数据，因此 2023-2024 缺样本不是 Phase0E PIT archive 缺失导致。", "", md_table(phase0e_cov[(phase0e_cov['month'] >= '2023-01') & (phase0e_cov['month'] <= '2024-12')], ["month", "institutional_rows", "institutional_symbols", "margin_rows", "margin_symbols", "phase0e_has_both"], 24), "",
        "## 2. 本地价格与 TWII 覆盖", "", "本地价格与 TWII 在 2023-2024 有覆盖；标签侧不是 2023-2024 完全缺失的主因。", "", md_table(price_cov[(price_cov['month'] >= '2023-01') & (price_cov['month'] <= '2024-12')], ["month", "price_rows", "price_symbols", "twii_rows", "price_has_sample_symbols", "twii_has_rows"], 24), "",
        "## 3. Qlib Prediction 覆盖", "", "本地 qlib prediction artifact 在 2023-2024 没有可用 prediction rows，是 Phase1B Full 样本断档的直接原因。", "", md_table(pred_gap, ["month", "prediction_file_count", "prediction_rows", "prediction_symbols", "prediction_days", "has_prediction"], 24), "",
        "## 4. Join Drop-off", "", "2023-2024 月份从第一步就是 `no_prediction=1`，因此后续 price/PIT/label join 没有机会形成样本。", "", md_table(dropoff, ["month", "prediction_rows", "no_prediction", "no_price", "no_twii_label", "no_institutional_pit", "no_margin_pit", "label_horizon_missing", "final_all_horizons_rows"], 60), "",
        "## 5. 是否可修复", "", "本地目录中未发现 2023-2024 qlib prediction rows。若要补齐，需要新增或生成 2023-2024 qlib predictions；这超出本步骤允许范围，因为工作文档禁止生成新的 qlib predictions、训练模型、联网下载或写 provider。", "",
        "## 6. Gate 重判", "", f"- `{summary['gate']}`", "- 当前 Phase1B Full 只能作为 2022 + 2025-2026 片段窗口证据，不得请求 Phase2 rules baseline。", "- 如审查者/用户后续授权修复，应单独进入 Phase1B Repair，不得由本诊断步骤自动执行。", "",
        "## 7. 产物", "", f"- Phase0E 覆盖：`{rel(PHASE0E_COVERAGE_PATH)}`", f"- 价格覆盖：`{rel(PRICE_COVERAGE_PATH)}`", f"- qlib prediction 覆盖：`{rel(PREDICTION_COVERAGE_PATH)}`", f"- join drop-off：`{rel(DROPOFF_PATH)}`", f"- summary：`{rel(SUMMARY_PATH)}`", "",
    ]
    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    inst, margin, symbols = load_phase0e()
    phase0e_cov = phase0e_monthly_coverage(inst, margin)
    price_cov, price_map, twii = price_monthly_coverage(symbols)
    pred, pred_files = load_predictions(symbols)
    pred_cov = prediction_monthly_coverage(pred, pred_files)
    dropoff = join_dropoff(pred, inst, margin, price_map, twii)
    phase0e_2023_2024 = phase0e_cov[(phase0e_cov["month"] >= "2023-01") & (phase0e_cov["month"] <= "2024-12")]
    price_2023_2024 = price_cov[(price_cov["month"] >= "2023-01") & (price_cov["month"] <= "2024-12")]
    pred_2023_2024 = pred_cov[(pred_cov["month"] >= "2023-01") & (pred_cov["month"] <= "2024-12")]
    has_phase0e = bool(phase0e_2023_2024["phase0e_has_both"].all())
    has_price = bool((price_2023_2024["price_has_sample_symbols"] & price_2023_2024["twii_has_rows"]).all())
    has_pred = bool(pred_2023_2024["has_prediction"].all())
    if has_phase0e and has_price and not has_pred:
        gate = "phase1b_repair_requires_new_artifacts=true"
        reason = "Phase0E archive 与本地价格/TWII 覆盖 2023-2024，但本地 qlib prediction artifact 在 2023-2024 无 prediction rows；补齐需要新增或生成 qlib predictions，当前步骤禁止执行。"
    elif has_phase0e and has_price and has_pred:
        gate = "phase1b_repair_possible_with_local_artifacts=true"
        reason = "本地 artifact 看起来具备补齐条件，但需要审查者授权 Phase1B Repair 后才能执行。"
    else:
        gate = "phase1b_evidence_fragmentary_stop_phase2=true"
        reason = "除 qlib prediction 外还有 Phase0E 或价格/TWII 覆盖缺口，当前证据只能作为片段窗口。"
    summary = {"generated_at": utc_now(), "phase": "phase1b_coverage_diagnosis_readonly", "network_used": False, "token_used": False, "phase0e_symbols": len(symbols), "prediction_rows": int(len(pred)), "prediction_file_count_2022_2026_to_end": int(len(pred_files)), "has_phase0e_2023_2024": has_phase0e, "has_price_twii_2023_2024": has_price, "has_qlib_prediction_2023_2024": has_pred, "gate": gate, "reason": reason}
    phase0e_cov.to_csv(PHASE0E_COVERAGE_PATH, index=False)
    price_cov.to_csv(PRICE_COVERAGE_PATH, index=False)
    pred_cov.to_csv(PREDICTION_COVERAGE_PATH, index=False)
    dropoff.to_csv(DROPOFF_PATH, index=False)
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(summary, phase0e_cov, price_cov, pred_cov, dropoff)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
