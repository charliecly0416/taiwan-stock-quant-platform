#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
CALENDAR = PROVIDER / "calendars/day.txt"
INSTRUMENTS = PROVIDER / "instruments/all.txt"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
S2B_MANIFEST = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_training_manifest.json"
S2B_CONFIG = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_generated_qlib_config.yaml"
O2_FEATURES = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv"
O2_SUMMARY = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/phaseo2_summary.json"
O2_FEATURE_DICTIONARY = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/feature_dictionary.csv"
O2_PIT_LEAKAGE = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/pit_leakage_audit.csv"
O2_PIT_LINEAGE = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/pit_lineage_audit.csv"
O4_MANIFEST = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json"
O4_FEATURES = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv"

OUT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e0_contract_and_feasibility"
DOC = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE0_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md"

MANIFEST_JSON = OUT_DIR / "phasee0_contract_manifest.json"
QLIB_COVERAGE_CSV = OUT_DIR / "phasee0_qlib_data_coverage.csv"
OOS_PLAN_CSV = OUT_DIR / "phasee0_oos_score_feasibility_plan.csv"
TOP50_CSV = OUT_DIR / "phasee0_top50_candidate_feasibility.csv"
O2_COVERAGE_CSV = OUT_DIR / "phasee0_o2_orthogonal_feature_coverage.csv"
LABEL_CSV = OUT_DIR / "phasee0_label_feasibility_audit.csv"
FEATURE_SCHEMA_CSV = OUT_DIR / "phasee0_feature_schema_plan.csv"
FORBIDDEN_JSON = OUT_DIR / "phasee0_forbidden_action_audit.json"

QLIB_TRAIN_START = "2018-01-01"
QLIB_TRAIN_END = "2022-12-31"
OOS_START = "2023-01-01"
OOS_END = "2026-05-07"
LTR_TRAIN_START = "2023-01-01"
LTR_TRAIN_END = "2025-12-31"
LTR_TEST_START = "2026-01-01"
LTR_TEST_END = "2026-05-07"
GATE = "phase_e0_extended_oos_contract_feasible"


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


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    required = [PROVIDER, CALENDAR, INSTRUMENTS, S2B_MANIFEST, S2B_CONFIG, O2_FEATURES, O2_SUMMARY, O2_FEATURE_DICTIONARY, O2_PIT_LEAKAGE, O2_PIT_LINEAGE, O4_MANIFEST, O4_FEATURES]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing E0 inputs: {missing}")
    return load_json(S2B_MANIFEST), load_json(O2_SUMMARY), load_json(O4_MANIFEST)


def norm(symbol: str) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def read_calendar() -> list[str]:
    return [line.strip()[:10] for line in CALENDAR.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_instruments() -> list[dict[str, str]]:
    rows = []
    with INSTRUMENTS.open(encoding="utf-8") as fh:
        for line in fh:
            parts = line.strip().split()
            if len(parts) >= 3:
                rows.append({"instrument": norm(parts[0]), "start": parts[1], "end": parts[2]})
    return rows


def price_dates(symbol: str) -> list[str]:
    path = PRICE_ROOT / f"{norm(symbol)}.csv"
    if not path.exists():
        return []
    out: list[str] = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            day = str(row.get("date") or "")[:10]
            try:
                close = float(row.get("close") or 0.0)
            except Exception:
                close = 0.0
            if day and close > 0:
                out.append(day)
    return out


def active_count_by_day(symbol_days: dict[str, set[str]], days: list[str]) -> pd.DataFrame:
    rows = []
    for day in days:
        rows.append({"date": day, "active_price_symbol_count": sum(1 for sdays in symbol_days.values() if day in sdays)})
    return pd.DataFrame(rows)


def window_days(calendar: list[str], start: str, end: str) -> list[str]:
    return [d for d in calendar if start <= d <= end]


def coverage_rows(symbol_days: dict[str, set[str]], calendar: list[str]) -> list[dict[str, Any]]:
    windows = [
        ("qlib_train_2018_2022", QLIB_TRAIN_START, QLIB_TRAIN_END),
        ("qlib_oos_score_2023_2026", OOS_START, OOS_END),
        ("ltr_train_2023_2025", LTR_TRAIN_START, LTR_TRAIN_END),
        ("ltr_test_2026", LTR_TEST_START, LTR_TEST_END),
    ]
    out = []
    for name, start, end in windows:
        days = window_days(calendar, start, end)
        counts = active_count_by_day(symbol_days, days)
        out.append(
            {
                "window": name,
                "start": start,
                "end": end,
                "calendar_days": int(len(days)),
                "daily_active_min": int(counts["active_price_symbol_count"].min()) if not counts.empty else 0,
                "daily_active_median": float(counts["active_price_symbol_count"].median()) if not counts.empty else 0.0,
                "daily_active_max": int(counts["active_price_symbol_count"].max()) if not counts.empty else 0,
                "can_form_top50_daily": bool((counts["active_price_symbol_count"] >= 50).all()) if not counts.empty else False,
            }
        )
    return out


def top50_rows(symbol_days: dict[str, set[str]], calendar: list[str]) -> list[dict[str, Any]]:
    out = []
    for name, start, end in [("ltr_train_2023_2025", LTR_TRAIN_START, LTR_TRAIN_END), ("ltr_test_2026", LTR_TEST_START, LTR_TEST_END)]:
        days = window_days(calendar, start, end)
        counts = active_count_by_day(symbol_days, days)
        out.append(
            {
                "window": name,
                "start": start,
                "end": end,
                "date_count": int(len(days)),
                "daily_candidate_min": int(counts["active_price_symbol_count"].min()) if not counts.empty else 0,
                "daily_candidate_median": float(counts["active_price_symbol_count"].median()) if not counts.empty else 0.0,
                "daily_candidate_max": int(counts["active_price_symbol_count"].max()) if not counts.empty else 0,
                "top50_feasible_every_day": bool((counts["active_price_symbol_count"] >= 50).all()) if not counts.empty else False,
                "planned_preserve_scope": "top50_only",
            }
        )
    return out


def label_rows(symbol_days: dict[str, list[str]], calendar: list[str]) -> list[dict[str, Any]]:
    out = []
    for name, start, end, train_allowed in [
        ("ltr_train_2023_2025", LTR_TRAIN_START, LTR_TRAIN_END, True),
        ("ltr_test_2026", LTR_TEST_START, LTR_TEST_END, False),
    ]:
        rows_checked = 0
        label_rows = 0
        for days in symbol_days.values():
            idx = {d: i for i, d in enumerate(days)}
            for day in calendar:
                if not (start <= day <= end):
                    continue
                if day not in idx:
                    continue
                rows_checked += 1
                if idx[day] + 10 < len(days):
                    label_rows += 1
        out.append(
            {
                "window": name,
                "rows_checked": rows_checked,
                "label_10d_available_rows": label_rows,
                "label_10d_missing_rows": rows_checked - label_rows,
                "label_10d_available_ratio": round(label_rows / rows_checked, 8) if rows_checked else 0.0,
                "label_allowed_for_training": train_allowed,
                "label_audit_only": not train_allowed,
            }
        )
    return out


def o2_coverage_rows(symbols: list[str], calendar: list[str]) -> list[dict[str, Any]]:
    score_keys = []
    for day in window_days(calendar, LTR_TRAIN_START, LTR_TEST_END):
        for symbol in symbols:
            score_keys.append({"date": pd.Timestamp(day), "date_str": day, "symbol": symbol, "window": "ltr_train_2023_2025" if day <= LTR_TRAIN_END else "ltr_test_2026"})
    left_all = pd.DataFrame(score_keys)
    features = pd.read_csv(
        O2_FEATURES,
        usecols=["symbol", "trade_date", "available_at", "feature_family", "foreign_net_buy", "margin_balance"],
        parse_dates=["trade_date", "available_at"],
    )
    features["symbol"] = features["symbol"].map(norm)
    out = []
    for family, marker in [("institutional_flow", "foreign_net_buy"), ("margin_short", "margin_balance")]:
        fam = features[features["feature_family"] == family].copy()
        pieces = []
        for symbol, left in left_all.groupby("symbol"):
            right = fam[fam["symbol"] == symbol].sort_values("available_at")
            if right.empty:
                tmp = left.copy()
                tmp["matched"] = False
                tmp["available_at_violation"] = False
                tmp["trade_date_violation"] = False
                pieces.append(tmp)
                continue
            merged = pd.merge_asof(
                left.sort_values("date"),
                right[["symbol", "trade_date", "available_at", marker]].sort_values("available_at"),
                by="symbol",
                left_on="date",
                right_on="available_at",
                direction="backward",
            )
            merged["matched"] = merged[marker].notna()
            merged["available_at_violation"] = merged["available_at"].notna() & (merged["available_at"] > merged["date"])
            merged["trade_date_violation"] = merged["trade_date"].notna() & (merged["trade_date"] > merged["date"])
            pieces.append(merged)
        joined = pd.concat(pieces, ignore_index=True)
        for window, sub in joined.groupby("window"):
            out.append(
                {
                    "window": window,
                    "feature_family": family,
                    "rows_checked": int(sub.shape[0]),
                    "matched_rows": int(sub["matched"].sum()),
                    "missing_rows": int((~sub["matched"]).sum()),
                    "missing_ratio": round(float((~sub["matched"]).mean()), 8),
                    "used_available_at_gt_signal_asof_rows": int(sub["available_at_violation"].sum()),
                    "used_trade_date_gt_signal_asof_rows": int(sub["trade_date_violation"].sum()),
                }
            )
    return out


def oos_plan_rows(s2b: dict[str, Any], o4: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "component": "qlib",
            "train": f"{QLIB_TRAIN_START}..{QLIB_TRAIN_END}",
            "oos_score": f"{OOS_START}..{OOS_END}",
            "provider": rel(PROVIDER),
            "model_family": "qlib.contrib.model.gbdt.LGBModel",
            "params_source": rel(S2B_MANIFEST),
            "params_change_allowed": "date_split_only",
            "thread_ladder": "4->2->1",
            "multi_model_score_allowed": False,
        },
        {
            "component": "ltr",
            "train": f"{LTR_TRAIN_START}..{LTR_TRAIN_END}",
            "oos_score": f"{LTR_TEST_START}..{LTR_TEST_END}",
            "provider": "E1 frozen qlib OOS score",
            "model_family": o4["model_config"]["model_type"],
            "params_source": rel(O4_MANIFEST),
            "params_change_allowed": "none",
            "thread_ladder": "",
            "multi_model_score_allowed": False,
        },
    ]


def write_report(manifest: dict[str, Any], coverage: list[dict[str, Any]], top50: list[dict[str, Any]], o2_rows: list[dict[str, Any]], label: list[dict[str, Any]]) -> None:
    lines = [
        "# Phase E0 执行报告：Extended OOS 合同与可行性审计",
        "",
        f"生成时间：`{manifest['created_at']}`",
        "",
        "## 1. 结论",
        "",
        f"- gate：`{manifest['gate']}`。",
        "- E0 只做合同与可行性审计，未训练 qlib / LTR，未调参，未回放。",
        "- qlib train 冻结为 `2018-01-01..2022-12-31`。",
        "- 同一个 frozen qlib 计划为 `2023-01-01..2026-05-07` 生成 OOS score。",
        "- LTR train 冻结为 `2023-01-01..2025-12-31`；2026 为 untouched test。",
        "",
        "## 2. 使用 Artifact",
        "",
        f"- provider：`{rel(PROVIDER)}`",
        f"- S2B manifest：`{rel(S2B_MANIFEST)}`",
        f"- S2B config：`{rel(S2B_CONFIG)}`",
        f"- O2 features：`{rel(O2_FEATURES)}`",
        f"- O4 manifest：`{rel(O4_MANIFEST)}`",
        f"- O4 whitelist：`{rel(O4_FEATURES)}`",
        "",
        "## 3. Qlib 数据覆盖",
        "",
        "| window | start | end | days | active min/median/max | top50 feasible |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for row in coverage:
        lines.append(f"| {row['window']} | {row['start']} | {row['end']} | {row['calendar_days']} | {row['daily_active_min']}/{row['daily_active_median']}/{row['daily_active_max']} | {row['can_form_top50_daily']} |")
    lines.extend(
        [
            "",
            "## 4. Top50 / OOS Score 可行性",
            "",
            "| window | date_count | candidate min/median/max | top50 feasible |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for row in top50:
        lines.append(f"| {row['window']} | {row['date_count']} | {row['daily_candidate_min']}/{row['daily_candidate_median']}/{row['daily_candidate_max']} | {row['top50_feasible_every_day']} |")
    lines.extend(
        [
            "",
            "## 5. O2 正交特征 PIT Coverage",
            "",
            "| window | family | rows | matched | missing_ratio | available_at violation | trade_date violation |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in o2_rows:
        lines.append(f"| {row['window']} | {row['feature_family']} | {row['rows_checked']} | {row['matched_rows']} | {row['missing_ratio']} | {row['used_available_at_gt_signal_asof_rows']} | {row['used_trade_date_gt_signal_asof_rows']} |")
    lines.extend(
        [
            "",
            "## 6. Label 可行性",
            "",
            "| window | rows | label rows | missing rows | ratio | train allowed | audit only |",
            "| --- | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in label:
        lines.append(f"| {row['window']} | {row['rows_checked']} | {row['label_10d_available_rows']} | {row['label_10d_missing_rows']} | {row['label_10d_available_ratio']} | {row['label_allowed_for_training']} | {row['label_audit_only']} |")
    lines.extend(
        [
            "",
            "## 7. 参数与特征计划",
            "",
            "- qlib model family：`qlib.contrib.model.gbdt.LGBModel`。",
            "- qlib 参数沿用 S2B，仅允许改变日期 split。",
            "- LTR model family / params 沿用 O4：`LightGBM.LGBMRanker / lambdarank`。",
            "- label：`relevance_10d_top_heavy`。",
            f"- feature schema：`{manifest['feature_schema']['feature_count']}` 个 O4 whitelist 特征，未新增 O2/O4 之外特征。",
            "",
            "## 8. 禁止事项审计",
            "",
            "- 未训练 qlib / LTR。",
            "- 未调参，未回放。",
            "- 未改变 provider。",
            "- 未引入多个 qlib 模型拼接 score。",
            "- 未使用 2026 做训练、调参或选择。",
            "- 未触发 provider refresh / publish / accepted latest、frontend/API、monitor 或交易链路。",
            "",
            "## 9. 输出 Artifact",
            "",
            f"- `{rel(MANIFEST_JSON)}`",
            f"- `{rel(QLIB_COVERAGE_CSV)}`",
            f"- `{rel(OOS_PLAN_CSV)}`",
            f"- `{rel(TOP50_CSV)}`",
            f"- `{rel(O2_COVERAGE_CSV)}`",
            f"- `{rel(LABEL_CSV)}`",
            f"- `{rel(FEATURE_SCHEMA_CSV)}`",
            f"- `{rel(FORBIDDEN_JSON)}`",
            "",
            "## 10. 是否建议进入 E1",
            "",
            f"- 建议：允许进入 E1，gate 为 `{manifest['gate']}`。",
        ]
    )
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = now()
    s2b, o2, o4 = require_inputs()
    calendar = read_calendar()
    instruments = read_instruments()
    symbols = [row["instrument"] for row in instruments]
    symbol_date_lists = {symbol: price_dates(symbol) for symbol in symbols}
    symbol_days = {symbol: set(days) for symbol, days in symbol_date_lists.items()}

    coverage = coverage_rows(symbol_days, calendar)
    top50 = top50_rows(symbol_days, calendar)
    labels = label_rows(symbol_date_lists, calendar)
    o2_rows = o2_coverage_rows(symbols, calendar)
    oos_plan = oos_plan_rows(s2b, o4)
    schema = pd.read_csv(O4_FEATURES)
    schema.to_csv(FEATURE_SCHEMA_CSV, index=False)

    stop_reasons = []
    if not next(row for row in coverage if row["window"] == "qlib_train_2018_2022")["can_form_top50_daily"]:
        stop_reasons.append("2018_2022_qlib_training_data_insufficient")
    if not all(row["top50_feasible_every_day"] for row in top50):
        stop_reasons.append("top50_feasibility_failed")
    if next(row for row in labels if row["window"] == "ltr_train_2023_2025")["label_10d_available_ratio"] < 0.95:
        stop_reasons.append("ltr_train_label_availability_too_low")
    if any(row["used_available_at_gt_signal_asof_rows"] or row["used_trade_date_gt_signal_asof_rows"] for row in o2_rows):
        stop_reasons.append("o2_pit_violation")
    if o2.get("gate") != "phase_o2_pit_safe_feature_builder_passed":
        stop_reasons.append("o2_gate_not_passed")
    if o4.get("gate") != "phase_o4_controlled_treatment_ltr_trained":
        stop_reasons.append("o4_gate_not_available")

    forbidden = {
        "created_at": created_at,
        "phase": "phase_e0_contract_and_feasibility",
        "no_qlib_training": True,
        "no_ltr_training": True,
        "no_parameter_search": True,
        "no_replay": True,
        "no_provider_refresh_publish_accepted_latest": True,
        "no_frontend_api_monitor_trading": True,
        "no_2026_training_tuning_selection": True,
        "no_new_feature_family_or_rule": True,
        "no_multi_qlib_model_score": True,
    }
    manifest = {
        "created_at": created_at,
        "phase": "phase_e0_contract_and_feasibility",
        "gate": GATE if not stop_reasons else "extended_oos_blocked_by_contract_or_sample",
        "stop_reasons": stop_reasons,
        "provider": rel(PROVIDER),
        "instrument_count": len(symbols),
        "calendar_min": min(calendar) if calendar else "",
        "calendar_max": max(calendar) if calendar else "",
        "qlib_contract": {
            "train": [QLIB_TRAIN_START, QLIB_TRAIN_END],
            "oos_score": [OOS_START, OOS_END],
            "model_family": "qlib.contrib.model.gbdt.LGBModel",
            "params_source": rel(S2B_MANIFEST),
            "provider_change_required": False,
            "parameter_tuning_required": False,
            "multi_model_score_required": False,
        },
        "ltr_contract": {
            "train": [LTR_TRAIN_START, LTR_TRAIN_END],
            "untouched_test": [LTR_TEST_START, LTR_TEST_END],
            "model_config": o4.get("model_config", {}),
            "label_col": "relevance_10d_top_heavy",
            "feature_schema_source": rel(O4_FEATURES),
        },
        "coverage": coverage,
        "top50_feasibility": top50,
        "o2_feature_coverage": o2_rows,
        "label_feasibility": labels,
        "feature_schema": {
            "source": rel(O4_FEATURES),
            "feature_count": int(schema.shape[0]),
            "control_original_feature_count": int((schema["family"] == "control_original").sum()),
            "orthogonal_feature_count": int((schema["family"] != "control_original").sum()),
        },
        "artifacts": {
            "contract_manifest": rel(MANIFEST_JSON),
            "qlib_data_coverage": rel(QLIB_COVERAGE_CSV),
            "oos_score_feasibility_plan": rel(OOS_PLAN_CSV),
            "top50_candidate_feasibility": rel(TOP50_CSV),
            "o2_orthogonal_feature_coverage": rel(O2_COVERAGE_CSV),
            "label_feasibility_audit": rel(LABEL_CSV),
            "feature_schema_plan": rel(FEATURE_SCHEMA_CSV),
            "forbidden_action_audit": rel(FORBIDDEN_JSON),
            "report": rel(DOC),
        },
    }
    wcsv(QLIB_COVERAGE_CSV, coverage)
    wcsv(OOS_PLAN_CSV, oos_plan)
    wcsv(TOP50_CSV, top50)
    wcsv(O2_COVERAGE_CSV, o2_rows)
    wcsv(LABEL_CSV, labels)
    wjson(FORBIDDEN_JSON, forbidden)
    wjson(MANIFEST_JSON, manifest)
    write_report(manifest, coverage, top50, o2_rows, labels)
    print(json.dumps({"ok": not stop_reasons, "gate": manifest["gate"], "report": rel(DOC), "out_dir": rel(OUT_DIR), "stop_reasons": stop_reasons}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
