#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
E2_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample"
E2_MANIFEST = E2_DIR / "phasee2_sample_manifest.json"
E2_TEST = E2_DIR / "phasee2_ltr_test_sample_2026.csv"
E2_SCHEMA = E2_DIR / "phasee2_feature_schema.csv"
E3_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_manifest.json"
E3_MODEL = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl"
E4_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_manifest.json"
E7_REPORT = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE7_DEFAULT_CANDIDATE_DECISION_CN.md"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"

OUT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/daily_e4_default_candidate"
DOC = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE8_E4_DAILY_DEFAULT_CANDIDATE_READONLY_EXECUTION_REPORT_CN.md"

STRATEGY_ID = "e4_frozen_qlib_orthogonal_ltr_2023_2025"
GATE = "phase_e8_e4_daily_default_candidate_readonly_completed"
SCORE_COL = "e4_ltr_score"
RANK_COL = "e4_ltr_rank_within_qlib_top50"
TARGET_POSITION_COUNT = 10
CANDIDATE_K = 50

FORBIDDEN_COLUMNS = {
    "future_return_5d",
    "future_return_10d",
    "future_return_20d",
    "future_excess_return_5d",
    "future_excess_return_10d",
    "future_excess_return_20d",
    "future_excess_return_rank_5d",
    "future_excess_return_rank_10d",
    "future_excess_return_rank_20d",
    "relevance_10d_top_heavy",
    "topk_forward_bucket",
    "ltr_relevance_label",
    "realized_pnl",
}


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


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row.keys()}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_inputs() -> dict[str, Any]:
    required = [E2_MANIFEST, E2_TEST, E2_SCHEMA, E3_MANIFEST, E3_MODEL, E4_MANIFEST, E7_REPORT, PRICE_ROOT]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing E8 inputs: {missing}")
    e2 = load_json(E2_MANIFEST)
    e3 = load_json(E3_MANIFEST)
    e4 = load_json(E4_MANIFEST)
    if e2.get("gate") != "phase_e2_extended_oos_ltr_sample_passed":
        raise RuntimeError(f"E2 gate mismatch: {e2.get('gate')}")
    if e3.get("gate") != "phase_e3_extended_oos_ltr_trained":
        raise RuntimeError(f"E3 gate mismatch: {e3.get('gate')}")
    if e4.get("gate") != "phase_e4_extended_oos_2026_replay_completed":
        raise RuntimeError(f"E4 gate mismatch: {e4.get('gate')}")
    return {"e2": e2, "e3": e3, "e4": e4}


def feature_cols() -> list[str]:
    schema = pd.read_csv(E2_SCHEMA)
    cols = schema[schema["status"] == "training_feature"]["feature"].astype(str).tolist()
    if len(cols) != 78:
        raise RuntimeError(f"Expected 78 E4 features, got {len(cols)}")
    return cols


def coerce_features(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        out[col] = pd.to_numeric(out[col], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return out


def next_price_available(symbol: str, signal_asof: str) -> bool:
    path = PRICE_ROOT / f"{norm(symbol)}.csv"
    if not path.exists():
        return False
    df = pd.read_csv(path, usecols=lambda col: col in {"date", "close"})
    if df.empty:
        return False
    df["date_str"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    future = df[(df["date_str"] > signal_asof) & df["close"].notna() & (df["close"] > 0)]
    return not future.empty


def output_paths(asof: str) -> dict[str, Path]:
    return {
        "manifest": OUT_DIR / f"e4_daily_candidate_manifest_{asof}.json",
        "qlib_top150": OUT_DIR / f"e4_daily_qlib_top150_scores_{asof}.csv",
        "ltr_top50": OUT_DIR / f"e4_daily_ltr_top50_rerank_{asof}.csv",
        "target_top10": OUT_DIR / f"e4_daily_target_top10_{asof}.csv",
        "diff": OUT_DIR / f"e4_daily_diff_vs_previous_{asof}.csv",
        "coverage": OUT_DIR / f"e4_daily_coverage_audit_{asof}.csv",
        "pit": OUT_DIR / f"e4_daily_pit_available_at_audit_{asof}.csv",
        "forbidden": OUT_DIR / f"e4_daily_forbidden_action_audit_{asof}.json",
        "latest": OUT_DIR / "e4_daily_candidate_latest.json",
    }


def score_for_date(df: pd.DataFrame, model: Any, cols: list[str], asof: str) -> pd.DataFrame:
    day = df[df["date_str"] == asof].copy()
    if day.empty:
        raise RuntimeError(f"No sample rows for signal_asof={asof}")
    day = coerce_features(day, cols)
    day[SCORE_COL] = model.predict(day[cols])
    top50 = day[pd.to_numeric(day["qlib_rank"], errors="coerce") <= CANDIDATE_K].copy()
    if top50.shape[0] != CANDIDATE_K:
        raise RuntimeError(f"qlib top50 incomplete for {asof}: rows={top50.shape[0]}")
    top50[RANK_COL] = top50[SCORE_COL].rank(ascending=False, method="first").astype(int)
    return top50.sort_values([RANK_COL, "instrument"]).reset_index(drop=True)


def diff_rows(current: pd.DataFrame, previous: pd.DataFrame, asof: str, prev_asof: str) -> list[dict[str, Any]]:
    cur = current[current[RANK_COL] <= TARGET_POSITION_COUNT][["instrument", RANK_COL, SCORE_COL, "qlib_rank"]].copy()
    prev = previous[previous[RANK_COL] <= TARGET_POSITION_COUNT][["instrument", RANK_COL, SCORE_COL, "qlib_rank"]].copy()
    cur_map = {row.instrument: row for row in cur.itertuples(index=False)}
    prev_map = {row.instrument: row for row in prev.itertuples(index=False)}
    rows: list[dict[str, Any]] = []
    for symbol in sorted(set(cur_map) | set(prev_map)):
        in_cur = symbol in cur_map
        in_prev = symbol in prev_map
        status = "unchanged"
        if in_cur and not in_prev:
            status = "added"
        elif in_prev and not in_cur:
            status = "removed"
        elif in_cur and in_prev and int(cur_map[symbol][1]) != int(prev_map[symbol][1]):
            status = "rank_changed"
        rows.append({
            "signal_asof": asof,
            "previous_signal_asof": prev_asof,
            "instrument": symbol,
            "status": status,
            "current_ltr_rank": int(cur_map[symbol][1]) if in_cur else "",
            "previous_ltr_rank": int(prev_map[symbol][1]) if in_prev else "",
            "current_qlib_rank": int(cur_map[symbol][3]) if in_cur else "",
            "previous_qlib_rank": int(prev_map[symbol][3]) if in_prev else "",
            "current_ltr_score": float(cur_map[symbol][2]) if in_cur else "",
            "previous_ltr_score": float(prev_map[symbol][2]) if in_prev else "",
        })
    return rows


def pit_audit(df: pd.DataFrame, asof: str) -> list[dict[str, Any]]:
    rows = []
    checks = [
        ("institutional_flow", "institutional_flow_trade_date", "institutional_flow_available_at"),
        ("margin_short", "margin_short_trade_date", "margin_short_available_at"),
    ]
    for family, trade_col, avail_col in checks:
        trade = pd.to_datetime(df[trade_col], errors="coerce")
        avail = pd.to_datetime(df[avail_col], errors="coerce")
        asof_ts = pd.Timestamp(asof)
        rows.append({
            "signal_asof": asof,
            "feature_family": family,
            "rows_checked": int(df.shape[0]),
            "trade_date_max": str(trade.max().date()) if trade.notna().any() else "",
            "available_at_max": str(avail.max().date()) if avail.notna().any() else "",
            "available_at_violations": int((avail > asof_ts).sum()),
            "trade_date_violations": int((trade > asof_ts).sum()),
            "missing_available_at_rows": int(avail.isna().sum()),
            "pit_pass": bool(((avail <= asof_ts) | avail.isna()).all() and ((trade <= asof_ts) | trade.isna()).all()),
        })
    return rows


def build_report(manifest: dict[str, Any], coverage: dict[str, Any], pit_rows: list[dict[str, Any]]) -> None:
    paths = manifest["artifacts"]
    lines = [
        "# Phase E8 执行报告：E4 Daily Default Candidate Readonly",
        "",
        f"生成时间：`{manifest['created_at']}`",
        "",
        "## 1. 结论",
        "",
        f"- gate：`{manifest['gate']}`。",
        f"- signal_asof：`{manifest['signal_asof']}`。",
        f"- strategy_id：`{manifest['strategy_id']}`。",
        "- 已生成 E4 frozen qlib + E4 orthogonal LTR 的只读 daily candidate artifact。",
        "- 未训练 qlib / LTR，未调参，未改默认策略，未触发 provider / accepted latest / monitor / broker / orders / quick-trade。",
        "- 本阶段只允许进入默认展示切换讨论，不执行展示切换。",
        "",
        "## 2. 策略合同",
        "",
        "| field | value |",
        "| --- | --- |",
        f"| qlib_base | {manifest['strategy_contract']['qlib_base']} |",
        f"| ltr_model | {manifest['strategy_contract']['ltr_model']} |",
        f"| replay_boundary | {manifest['strategy_contract']['replay_boundary']} |",
        f"| candidate_k | {manifest['strategy_contract']['candidate_k']} |",
        f"| target_position_count | {manifest['strategy_contract']['target_position_count']} |",
        f"| execution_assumption | {manifest['strategy_contract']['execution_assumption']} |",
        "",
        "## 3. Coverage / Replay-Ready",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| qlib_rows | {coverage['qlib_rows']} |",
        f"| qlib_top50_rows | {coverage['qlib_top50_rows']} |",
        f"| ltr_score_rows | {coverage['ltr_score_rows']} |",
        f"| target_top10_rows | {coverage['target_top10_rows']} |",
        f"| duplicate_key_count | {coverage['duplicate_key_count']} |",
        f"| next_execution_price_available_rows | {coverage['next_execution_price_available_rows']} |",
        "",
        "## 4. PIT Available-At Audit",
        "",
        "| feature_family | rows | trade_date_max | available_at_max | available_at_violations | trade_date_violations | pit_pass |",
        "| --- | ---: | --- | --- | ---: | ---: | --- |",
    ]
    for row in pit_rows:
        lines.append(f"| {row['feature_family']} | {row['rows_checked']} | {row['trade_date_max']} | {row['available_at_max']} | {row['available_at_violations']} | {row['trade_date_violations']} | {row['pit_pass']} |")
    lines.extend([
        "",
        "## 5. 展示边界",
        "",
        "- 可展示策略名称、signal_asof、top50 rerank、top10 候选、相对上一期变化、coverage/PIT/replay-ready 审计状态和风险提示。",
        "- 不展示自动买卖指令、目标仓位、target weight、broker order、quick-trade、收益承诺、胜率或上涨概率承诺。",
        "",
        "## 6. 输出 Artifact",
        "",
    ])
    for key, value in paths.items():
        lines.append(f"- {key}: `{value}`")
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = now()
    upstream = require_inputs()
    cols = feature_cols()
    sample = pd.read_csv(E2_TEST, parse_dates=["date"])
    sample["date_str"] = sample["date"].dt.strftime("%Y-%m-%d")
    sample["instrument"] = sample["instrument"].map(norm)
    signal_asof = str(sample["date_str"].max())
    previous_asof = str(sorted(sample["date_str"].unique())[-2])
    paths = output_paths(signal_asof)

    with E3_MODEL.open("rb") as fh:
        model = pickle.load(fh)
    current_top50 = score_for_date(sample, model, cols, signal_asof)
    previous_top50 = score_for_date(sample, model, cols, previous_asof)
    current_day = sample[sample["date_str"] == signal_asof].copy()

    forbidden_present = sorted(FORBIDDEN_COLUMNS & set(current_top50.columns))
    if forbidden_present:
        current_top50 = current_top50.drop(columns=forbidden_present)
    if sorted(FORBIDDEN_COLUMNS & set(current_top50.columns)):
        raise RuntimeError("Forbidden future/label/PnL fields remain in output")

    qlib_cols = ["date", "date_str", "instrument", "qlib_score_raw", "qlib_rank", "qlib_score_percentile_by_date", "qlib_score_zscore_by_date", "candidate_scope"]
    qlib_top150 = current_day[qlib_cols].sort_values(["qlib_rank", "instrument"]).copy()
    qlib_top150.to_csv(paths["qlib_top150"], index=False)

    keep_cols = ["date", "date_str", "instrument", "regime_segment", "qlib_score_raw", "qlib_rank", SCORE_COL, RANK_COL, "top50_flag"]
    current_top50[keep_cols].to_csv(paths["ltr_top50"], index=False)
    current_top50[current_top50[RANK_COL] <= TARGET_POSITION_COUNT][keep_cols].to_csv(paths["target_top10"], index=False)
    diff = diff_rows(current_top50, previous_top50, signal_asof, previous_asof)
    wcsv(paths["diff"], diff)

    pit_rows = pit_audit(current_day, signal_asof)
    wcsv(paths["pit"], pit_rows)
    next_exec = [next_price_available(symbol, signal_asof) for symbol in current_top50["instrument"].tolist()]
    coverage = {
        "signal_asof": signal_asof,
        "qlib_rows": int(current_day.shape[0]),
        "qlib_top50_rows": int(current_top50.shape[0]),
        "ltr_score_rows": int(current_top50[SCORE_COL].notna().sum()),
        "target_top10_rows": int((current_top50[RANK_COL] <= TARGET_POSITION_COUNT).sum()),
        "duplicate_key_count": int(current_top50.duplicated(["date_str", "instrument"]).sum()),
        "price_tradability_available_rows": int(current_day["same_day_price_tradable"].sum()),
        "candidate_scope_pass_rows": int(current_day["candidate_scope_pass"].sum()),
        "next_execution_price_available_rows": int(sum(next_exec)),
        "next_execution_price_audit_only": True,
        "coverage_pass": True,
    }
    if coverage["qlib_top50_rows"] != CANDIDATE_K or coverage["target_top10_rows"] != TARGET_POSITION_COUNT:
        raise RuntimeError(f"E8 coverage stop: {coverage}")
    if not all(row["pit_pass"] for row in pit_rows):
        raise RuntimeError(f"E8 PIT stop: {pit_rows}")
    wcsv(paths["coverage"], [coverage])

    forbidden = {
        "created_at": created_at,
        "signal_asof": signal_asof,
        "no_qlib_training": True,
        "no_ltr_training": True,
        "no_parameter_tuning": True,
        "no_new_filter_market_gate_turnover_rule": True,
        "no_provider_publish_or_refresh": True,
        "no_accepted_latest_switch": True,
        "no_frontend_or_api_change": True,
        "no_monitor_scan_config_alerts": True,
        "no_broker_orders_quick_trade": True,
        "no_future_return_label_realized_pnl_in_outputs": True,
        "dropped_forbidden_columns_from_candidate_output": forbidden_present,
    }
    wjson(paths["forbidden"], forbidden)

    manifest = {
        "created_at": created_at,
        "gate": GATE,
        "strategy_id": STRATEGY_ID,
        "signal_asof": signal_asof,
        "previous_signal_asof": previous_asof,
        "strategy_contract": {
            "qlib_base": "2018-2022 frozen qlib",
            "ltr_model": "orthogonal LTR trained on 2023-2025",
            "replay_boundary": "qlib top50 rerank only",
            "target_position_count": TARGET_POSITION_COUNT,
            "candidate_k": CANDIDATE_K,
            "execution_assumption": "next-day execution",
        },
        "upstream_gates": {"e2": upstream["e2"].get("gate"), "e3": upstream["e3"].get("gate"), "e4": upstream["e4"].get("gate")},
        "score_sources": {"qlib_score": rel(E2_TEST), "ltr_model": rel(E3_MODEL), "feature_schema": rel(E2_SCHEMA)},
        "coverage": coverage,
        "pit_available_at_audit": pit_rows,
        "top50_rerank_only": True,
        "allow_default_display_switch_discussion": True,
        "default_strategy_changed": False,
        "artifacts": {key: rel(value) for key, value in paths.items() if key != "latest"},
        "report": rel(DOC),
    }
    wjson(paths["manifest"], manifest)
    wjson(paths["latest"], manifest)
    build_report(manifest, coverage, pit_rows)
    print(json.dumps({"ok": True, "gate": GATE, "signal_asof": signal_asof, "report": rel(DOC), "manifest": rel(paths["manifest"])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
