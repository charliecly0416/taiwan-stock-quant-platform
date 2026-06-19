#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
E1_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score"
E1_MANIFEST = E1_DIR / "phasee1_training_manifest.json"
E1_RAW = E1_DIR / "phasee1_raw_oos_score_rank_2023_2026.csv"
E1_POST = E1_DIR / "phasee1_post_filter_oos_score_rank_2023_2026.csv"
E1_TOP50 = E1_DIR / "phasee1_top50_oos_score_rank_2023_2026.csv"
E0_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e0_contract_and_feasibility/phasee0_contract_manifest.json"
O4_MANIFEST = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json"
O3_SAMPLE = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_treatment_candidate_sample.csv"
PROVIDER = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
INSTRUMENTS = PROVIDER / "instruments/all.txt"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
OUT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1r_candidate_coverage_scope_repair"
DOC = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE1R_CANDIDATE_COVERAGE_SCOPE_REPAIR_EXECUTION_REPORT_CN.md"

COVERAGE_CSV = OUT_DIR / "phasee1r_raw_postfilter_top50_coverage_by_date.csv"
ATTRITION_CSV = OUT_DIR / "phasee1r_filter_attrition_audit.csv"
O4_COMPARE_CSV = OUT_DIR / "phasee1r_o4_training_scope_comparison.csv"
CONTRACT_JSON = OUT_DIR / "phasee1r_recommended_e2_candidate_contract.json"
FORBIDDEN_JSON = OUT_DIR / "phasee1r_forbidden_action_audit.json"
MANIFEST_JSON = OUT_DIR / "phasee1r_scope_manifest.json"
BROAD_CANDIDATE_CSV = OUT_DIR / "phasee1r_recommended_broad_candidate_coverage_by_split.csv"

OOS_START = "2023-01-01"
LTR_TRAIN_END = "2025-12-31"
OOS_END = "2026-05-07"
GATE = "phase_e1r_candidate_coverage_scope_repaired"
BLOCKED_GATE = "phase_e1r_blocked_by_candidate_scope"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(symbol: str) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def split_of(day: str) -> str:
    if OOS_START <= day <= LTR_TRAIN_END:
        return "ltr_train_2023_2025"
    if "2026-01-01" <= day <= OOS_END:
        return "ltr_test_2026"
    return "out_of_scope"


def require_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    required = [E1_MANIFEST, E1_RAW, E1_POST, E1_TOP50, E0_MANIFEST, O4_MANIFEST, O3_SAMPLE, INSTRUMENTS, PRICE_ROOT]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing E1R inputs: {missing}")
    e0 = load_json(E0_MANIFEST)
    e1 = load_json(E1_MANIFEST)
    o4 = load_json(O4_MANIFEST)
    if e0.get("gate") != "phase_e0_extended_oos_contract_feasible":
        raise RuntimeError(f"E0 gate unavailable: {e0.get('gate')}")
    if e1.get("gate") != "phase_e1_frozen_qlib_oos_score_completed":
        raise RuntimeError(f"E1 gate unavailable: {e1.get('gate')}")
    if o4.get("gate") != "phase_o4_controlled_treatment_ltr_trained":
        raise RuntimeError(f"O4 gate unavailable: {o4.get('gate')}")
    return e0, e1, o4


def read_provider_instruments() -> pd.DataFrame:
    rows = []
    with INSTRUMENTS.open(encoding="utf-8") as fh:
        for line in fh:
            parts = line.strip().split()
            if len(parts) >= 3:
                rows.append({"instrument": norm(parts[0]), "start": parts[1], "end": parts[2]})
    return pd.DataFrame(rows)


def load_price_state(provider_symbols: set[str], dates: list[str]) -> tuple[pd.DataFrame, set[tuple[str, str]], set[tuple[str, str]], set[tuple[str, str]]]:
    date_set = set(dates)
    price_rows = []
    provider_price_keys: set[tuple[str, str]] = set()
    provider_history_keys: set[tuple[str, str]] = set()
    all_history_keys: set[tuple[str, str]] = set()
    for path in sorted(PRICE_ROOT.glob("TW*.csv")):
        symbol = path.stem.upper()
        if symbol == "TWII":
            continue
        df = pd.read_csv(path, usecols=["date", "close", "vwap", "volume"])
        if df.empty:
            continue
        df["instrument"] = symbol
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["date"] <= pd.Timestamp(OOS_END)].copy()
        if df.empty:
            continue
        df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["vwap"] = pd.to_numeric(df["vwap"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        price = df["vwap"].where(df["vwap"].notna() & (df["vwap"] > 0), df["close"])
        df["value"] = price * df["volume"]
        df["has_price"] = df["close"].notna() & (df["close"] > 0) & df["volume"].notna() & (df["volume"] >= 0)
        df = df.sort_values("date")
        df["history_count_60"] = df["has_price"].cumsum()
        df["has_history_60"] = df["has_price"] & (df["history_count_60"] >= 60)
        df["trailing_value_60"] = df["value"].where(df["has_price"]).rolling(60, min_periods=20).mean()
        sub = df[df["date_str"].isin(date_set)].copy()
        if not sub.empty:
            price_rows.append(sub[["date", "date_str", "instrument", "close", "volume", "value", "trailing_value_60", "has_price", "has_history_60"]])
        if symbol in provider_symbols:
            for row in sub.itertuples(index=False):
                key = (row.date_str, row.instrument)
                if bool(row.has_price):
                    provider_price_keys.add(key)
                if bool(row.has_history_60):
                    provider_history_keys.add(key)
        for row in sub.itertuples(index=False):
            if bool(row.has_history_60):
                all_history_keys.add((row.date_str, row.instrument))
    price_state = pd.concat(price_rows, ignore_index=True) if price_rows else pd.DataFrame()
    return price_state, provider_price_keys, provider_history_keys, all_history_keys


def full_market_top150_keys(price_state: pd.DataFrame, instruments: pd.DataFrame) -> tuple[set[tuple[str, str]], pd.DataFrame]:
    inst = instruments.copy()
    inst["start"] = pd.to_datetime(inst["start"])
    inst["end"] = pd.to_datetime(inst["end"])
    state = price_state[price_state["has_history_60"] & price_state["trailing_value_60"].notna()].copy()
    state = state.merge(inst, on="instrument", how="left")
    state["is_provider_symbol"] = state["start"].notna()
    state["provider_active"] = state["is_provider_symbol"] & (state["date"] >= state["start"]) & (state["date"] <= state["end"])
    selected = state.sort_values(["date_str", "trailing_value_60"], ascending=[True, False]).groupby("date_str", group_keys=False).head(150).copy()
    keys = set(map(tuple, selected[["date_str", "instrument"]].itertuples(index=False, name=None)))
    daily = selected.groupby("date_str").agg(
        full_market_top150_rows=("instrument", "count"),
        full_market_top150_provider_symbols=("provider_active", "sum"),
    ).reset_index().rename(columns={"date_str": "date"})
    return keys, daily


def key_set(df: pd.DataFrame) -> set[tuple[str, str]]:
    return set(map(tuple, df[["date", "instrument"]].astype(str).itertuples(index=False, name=None)))


def count_by_date(keys: set[tuple[str, str]], name: str) -> pd.DataFrame:
    rows = [{"date": d, name: 1} for d, _ in keys]
    if not rows:
        return pd.DataFrame(columns=["date", name])
    return pd.DataFrame(rows).groupby("date", as_index=False)[name].sum()


def summarize_daily(df: pd.DataFrame, value_col: str, label: str) -> dict[str, Any]:
    return {
        "scope": label,
        "date_count": int(df["date"].nunique()),
        "rows_total": int(df[value_col].sum()),
        "daily_min": int(df[value_col].min()),
        "daily_median": float(df[value_col].median()),
        "daily_max": int(df[value_col].max()),
    }


def o4_scope_comparison() -> pd.DataFrame:
    usecols = ["date", "split", "sample_complete", "qlib_rank", "top50_flag"]
    sample = pd.read_csv(O3_SAMPLE, usecols=usecols, parse_dates=["date"])
    sample["date"] = sample["date"].dt.strftime("%Y-%m-%d")
    sample["sample_complete"] = sample["sample_complete"].astype(str).str.lower().isin(["true", "1"])
    rows = []
    for split, sub in sample[sample["sample_complete"]].groupby("split"):
        daily = sub.groupby("date").agg(rows=("date", "count"), top50_rows=("top50_flag", "sum"), max_rank=("qlib_rank", "max")).reset_index()
        rows.append({
            "scope": f"old_o4_{split}_sample_complete",
            "date_count": int(daily.shape[0]),
            "rows_total": int(daily["rows"].sum()),
            "daily_rows_min": int(daily["rows"].min()),
            "daily_rows_median": float(daily["rows"].median()),
            "daily_rows_max": int(daily["rows"].max()),
            "top50_only_training": bool((daily["rows"] <= 50).all()),
            "daily_max_rank_median": float(daily["max_rank"].median()),
        })
    return pd.DataFrame(rows)


def write_report(manifest: dict[str, Any], coverage_summary: list[dict[str, Any]], attrition: list[dict[str, Any]], o4_compare: pd.DataFrame, contract: dict[str, Any]) -> None:
    lines = [
        "# Phase E1R 执行报告：候选覆盖与训练样本口径修复审计",
        "",
        f"生成时间：`{manifest['created_at']}`",
        "",
        "## 1. 结论",
        "",
        f"- gate：`{manifest['gate']}`。",
        "- 已暂停原 E2 的 top50-only 风险，E1 qlib 训练本身不重跑、不否定。",
        "- E1 的 post-filter 覆盖过少，主因是把 E1 raw score 与全市场 trailing value top150 取交集；这不是旧 O4 宽候选 LTR 训练口径。",
        "- 修订后 E2 必须从同一个 E1 frozen qlib raw OOS score 出发，使用 provider 内 as-of active + same-day price + >=60 history/tradability 的宽候选 rows 构建 LTR train/test；不得只用 top50 训练。",
        "",
        "## 2. Coverage 摘要",
        "",
        "| scope | date_count | rows_total | daily min/median/max |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in coverage_summary:
        lines.append(f"| {row['scope']} | {row['date_count']} | {row['rows_total']} | {row['daily_min']}/{row['daily_median']}/{row['daily_max']} |")
    lines.extend([
        "",
        "## 3. Filter Attrition 归因",
        "",
        "| split | raw_rows | provider_eligible_rows | post_filter_rows | top50_rows | raw_not_full_market_top150 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in attrition:
        lines.append(f"| {row['split']} | {row['raw_rows']} | {row['provider_eligible_rows']} | {row['post_filter_rows']} | {row['top50_rows']} | {row['raw_not_full_market_top150']} |")
    lines.extend([
        "",
        "解释：`raw_not_full_market_top150` 是 E1 raw score 中 provider 内可交易/有历史的候选，被旧 E1 post-filter 的全市场 trailing value top150 交集排除的行。该过滤压缩了 2023-2025 候选覆盖，不能作为 LTR 训练候选口径。",
        "",
        "## 4. 与旧 O4 训练口径对比",
        "",
        "| scope | date_count | rows_total | daily rows min/median/max | top50-only training | median max rank |",
        "| --- | ---: | ---: | --- | --- | ---: |",
    ])
    for row in o4_compare.to_dict("records"):
        lines.append(f"| {row['scope']} | {row['date_count']} | {row['rows_total']} | {row['daily_rows_min']}/{row['daily_rows_median']}/{row['daily_rows_max']} | {row['top50_only_training']} | {row['daily_max_rank_median']} |")
    lines.extend([
        "",
        "旧 O4 的训练不是 top50-only：`top10_flag/top30_flag/top50_flag` 是特征/边界信息，训练行覆盖到宽候选 ranks。E2 应复刻这个训练口径。",
        "",
        "## 5. 修订后的 E2 Candidate Scope",
        "",
        f"- candidate source：`{contract['candidate_source']}`",
        "- LTR train：`2023-01-01..2025-12-31`，只使用 2023-2025 label。",
        "- untouched test：`2026-01-01..2026-05-07`，2026 label 仅审计/评估，不参与训练、调参或选择。",
        "- training rows：宽候选 rows，不得 top50-only。",
        "- replay/rerank boundary：后续回放只允许在 qlib top50 内重排。",
        "- qlib_rank/top10/top30/top50 flag 可作为特征，但不能作为训练行过滤条件。",
        "",
        "## 6. 禁止事项审计",
        "",
        "- 未训练 qlib / LTR。",
        "- 未调参，未回放。",
        "- 未使用 2026 label、future_return、future_excess_return 或 replay PnL 做候选选择。",
        "- 未引入多 qlib 模型、新 filter、market gate 或 turnover rule。",
        "- 未触发 provider refresh / publish / accepted latest、frontend/API、monitor 或交易链路。",
        "",
        "## 7. 输出 Artifact",
        "",
        f"- `{rel(MANIFEST_JSON)}`",
        f"- `{rel(COVERAGE_CSV)}`",
        f"- `{rel(ATTRITION_CSV)}`",
        f"- `{rel(O4_COMPARE_CSV)}`",
        f"- `{rel(BROAD_CANDIDATE_CSV)}`",
        f"- `{rel(CONTRACT_JSON)}`",
        f"- `{rel(FORBIDDEN_JSON)}`",
        "",
        "## 8. 是否建议进入修订后的 E2",
        "",
        f"- 建议：允许进入修订后的 E2，gate 为 `{manifest['gate']}`。",
    ])
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = now()
    e0, e1, o4 = require_inputs()
    instruments = read_provider_instruments()
    provider_symbols = set(instruments["instrument"].astype(str))
    raw = pd.read_csv(E1_RAW)
    post = pd.read_csv(E1_POST)
    top50 = pd.read_csv(E1_TOP50)
    for df in [raw, post, top50]:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df["instrument"] = df["instrument"].map(norm)
        df["split"] = df["date"].map(split_of)
    dates = sorted(raw["date"].unique())
    price_state, provider_price_keys, provider_history_keys, _ = load_price_state(provider_symbols, dates)
    full_top150_keys, full_top150_daily = full_market_top150_keys(price_state, instruments)
    raw_keys = key_set(raw)
    post_keys = key_set(post)
    top50_keys = key_set(top50)
    provider_active_keys = set()
    inst_ranges = instruments.set_index("instrument")[["start", "end"]].to_dict("index")
    for date, symbol in raw_keys:
        rng = inst_ranges.get(symbol)
        if rng and rng["start"] <= date <= rng["end"]:
            provider_active_keys.add((date, symbol))
    provider_eligible_keys = raw_keys & provider_active_keys & provider_price_keys & provider_history_keys
    broad_candidate = raw[raw.apply(lambda r: (r["date"], r["instrument"]) in provider_eligible_keys, axis=1)].copy()
    broad_candidate["qlib_rank_broad"] = broad_candidate.groupby("date")["qlib_score_raw"].rank(method="first", ascending=False).astype(int)
    broad_candidate["top10_flag"] = broad_candidate["qlib_rank_broad"] <= 10
    broad_candidate["top30_flag"] = broad_candidate["qlib_rank_broad"] <= 30
    broad_candidate["top50_flag"] = broad_candidate["qlib_rank_broad"] <= 50

    raw_daily = raw.groupby("date").size().rename("raw_rows").reset_index()
    post_daily = post.groupby("date").size().rename("post_filter_rows").reset_index()
    top50_daily = top50.groupby("date").size().rename("top50_rows").reset_index()
    broad_daily = broad_candidate.groupby("date").size().rename("recommended_broad_candidate_rows").reset_index()
    active_daily = count_by_date(provider_active_keys & provider_price_keys, "e0_active_price_rows")
    history_daily = count_by_date(provider_eligible_keys, "provider_active_price_history_rows")
    full_intersect_daily = count_by_date(raw_keys & full_top150_keys, "raw_in_full_market_top150_rows")
    coverage = raw_daily.merge(post_daily, on="date", how="left").merge(top50_daily, on="date", how="left").merge(active_daily, on="date", how="left").merge(history_daily, on="date", how="left").merge(full_intersect_daily, on="date", how="left").merge(full_top150_daily, on="date", how="left").merge(broad_daily, on="date", how="left")
    coverage = coverage.fillna(0)
    coverage["split"] = coverage["date"].map(split_of)
    coverage["raw_minus_post_filter"] = coverage["raw_rows"] - coverage["post_filter_rows"]
    coverage["raw_not_full_market_top150"] = coverage["raw_rows"] - coverage["raw_in_full_market_top150_rows"]
    coverage.to_csv(COVERAGE_CSV, index=False)

    broad_by_split = coverage.groupby("split").agg(
        date_count=("date", "nunique"),
        broad_rows=("recommended_broad_candidate_rows", "sum"),
        broad_daily_min=("recommended_broad_candidate_rows", "min"),
        broad_daily_median=("recommended_broad_candidate_rows", "median"),
        broad_daily_max=("recommended_broad_candidate_rows", "max"),
        top50_daily_min=("top50_rows", "min"),
    ).reset_index()
    broad_by_split.to_csv(BROAD_CANDIDATE_CSV, index=False)

    attrition = []
    for split, sub in coverage.groupby("split"):
        if split == "out_of_scope":
            continue
        split_raw = raw[raw["split"] == split]
        split_keys = key_set(split_raw)
        attrition.append({
            "split": split,
            "date_count": int(sub["date"].nunique()),
            "raw_rows": int(len(split_keys)),
            "provider_active_rows": int(len(split_keys & provider_active_keys)),
            "same_day_price_rows": int(len(split_keys & provider_price_keys)),
            "provider_eligible_rows": int(len(split_keys & provider_eligible_keys)),
            "post_filter_rows": int(sub["post_filter_rows"].sum()),
            "top50_rows": int(sub["top50_rows"].sum()),
            "raw_not_full_market_top150": int(len(split_keys & provider_eligible_keys) - len(split_keys & provider_eligible_keys & full_top150_keys)),
            "full_market_top150_intersection_rows": int(len(split_keys & full_top150_keys)),
            "candidate_scope_recommendation": "use_provider_eligible_broad_raw_score_not_full_market_top150_intersection",
        })
    pd.DataFrame(attrition).to_csv(ATTRITION_CSV, index=False)

    o4_compare = o4_scope_comparison()
    e1_compare_rows = []
    for split, sub in broad_by_split.groupby("split"):
        if split == "out_of_scope":
            continue
        row = sub.iloc[0]
        e1_compare_rows.append({
            "scope": f"e1r_recommended_{split}_broad_candidate",
            "date_count": int(row["date_count"]),
            "rows_total": int(row["broad_rows"]),
            "daily_rows_min": int(row["broad_daily_min"]),
            "daily_rows_median": float(row["broad_daily_median"]),
            "daily_rows_max": int(row["broad_daily_max"]),
            "top50_only_training": bool(row["broad_daily_max"] <= 50),
            "daily_max_rank_median": float(row["broad_daily_median"]),
        })
    o4_all = pd.concat([o4_compare, pd.DataFrame(e1_compare_rows)], ignore_index=True)
    o4_all.to_csv(O4_COMPARE_CSV, index=False)

    stop_reasons = []
    if not attrition:
        stop_reasons.append("coverage_attrition_not_available")
    if broad_by_split[broad_by_split["split"] == "ltr_train_2023_2025"].empty:
        stop_reasons.append("recommended_broad_candidate_train_scope_missing")
    else:
        train_median = float(broad_by_split.loc[broad_by_split["split"] == "ltr_train_2023_2025", "broad_daily_median"].iloc[0])
        if train_median <= 50:
            stop_reasons.append("recommended_scope_is_still_top50_only")
    gate = GATE if not stop_reasons else BLOCKED_GATE

    contract = {
        "created_at": created_at,
        "gate": gate,
        "candidate_source": rel(E1_RAW),
        "score_provenance": "all candidate rows must come from the same Phase E1 frozen qlib raw OOS score",
        "recommended_e2_candidate_scope": {
            "train_window": ["2023-01-01", "2025-12-31"],
            "test_window": ["2026-01-01", "2026-05-07"],
            "row_filter": [
                "instrument in frozen option_c_150 qlib provider active range as of signal date",
                "same-day local price/tradability available",
                ">=60 historical price observations by signal date",
                "E1 raw qlib score exists for date/instrument",
            ],
            "do_not_filter_training_to": ["top50", "top30", "full_market_trailing_value_top150_intersection"],
            "allowed_rank_features": ["qlib_rank", "qlib_score_percentile_by_date", "qlib_score_zscore_by_date", "top10_flag", "top30_flag", "top50_flag"],
            "replay_rerank_boundary": "qlib top50 within the broad candidate rows, recomputed from E1 raw score rank",
        },
        "forbidden": [
            "no qlib or LTR training in E1R",
            "no tuning",
            "no replay",
            "no 2026 label/future return/replay PnL for candidate selection",
            "no multiple qlib models",
            "no new market gate/filter/turnover rule",
        ],
        "stop_reasons": stop_reasons,
    }
    forbidden = {
        "created_at": created_at,
        "no_qlib_training": True,
        "no_ltr_training": True,
        "no_replay": True,
        "no_parameter_tuning": True,
        "no_2026_label_or_future_return_candidate_selection": True,
        "no_multiple_qlib_models": True,
        "no_new_filter_market_gate_turnover_rule": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_or_trading_chain": True,
    }
    manifest = {
        "created_at": created_at,
        "phase": "phase_e1r_candidate_coverage_scope_repair",
        "gate": gate,
        "stop_reasons": stop_reasons,
        "inputs": {
            "e1_manifest": rel(E1_MANIFEST),
            "e1_raw": rel(E1_RAW),
            "e1_post_filter": rel(E1_POST),
            "e1_top50": rel(E1_TOP50),
            "o4_manifest": rel(O4_MANIFEST),
            "o3_sample": rel(O3_SAMPLE),
        },
        "input_hashes": {
            "e1_raw_sha256": sha256_file(E1_RAW),
            "e1_post_filter_sha256": sha256_file(E1_POST),
            "e1_top50_sha256": sha256_file(E1_TOP50),
        },
        "artifacts": {
            "coverage_by_date": rel(COVERAGE_CSV),
            "filter_attrition_audit": rel(ATTRITION_CSV),
            "o4_training_scope_comparison": rel(O4_COMPARE_CSV),
            "broad_candidate_coverage_by_split": rel(BROAD_CANDIDATE_CSV),
            "recommended_e2_candidate_contract": rel(CONTRACT_JSON),
            "forbidden_action_audit": rel(FORBIDDEN_JSON),
            "report": rel(DOC),
        },
    }
    wjson(CONTRACT_JSON, contract)
    wjson(FORBIDDEN_JSON, forbidden)
    wjson(MANIFEST_JSON, manifest)
    write_report(manifest, [summarize_daily(coverage, "raw_rows", "e1_raw_oos_score"), summarize_daily(coverage, "post_filter_rows", "e1_post_filter_full_market_top150_intersection"), summarize_daily(coverage, "top50_rows", "e1_top50_from_compressed_postfilter"), summarize_daily(coverage, "recommended_broad_candidate_rows", "e1r_recommended_provider_eligible_broad_candidate")], attrition, o4_all, contract)
    print(json.dumps({"ok": gate == GATE, "gate": gate, "report": rel(DOC), "stop_reasons": stop_reasons}, ensure_ascii=False, indent=2))
    return 0 if gate == GATE else 1


if __name__ == "__main__":
    raise SystemExit(main())
