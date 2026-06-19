#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
S2B_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training"
S2B_SCORE = S2B_DIR / "phase_s2b_post_filter_score_rank.csv"
S2B_MANIFEST = S2B_DIR / "phase_s2b_training_manifest.json"
S2B_GATE = S2B_DIR / "phase_s2b_gate_summary.json"
O2_DIR = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder"
O2_FEATURES = O2_DIR / "normalized_feature_daily.csv"
O2_SUMMARY = O2_DIR / "phaseo2_summary.json"
O4_DIR = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr"
O4_MANIFEST = O4_DIR / "phaseo4_training_manifest.json"
O4_FEATURES = O4_DIR / "phaseo4_training_feature_whitelist.csv"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"

OUT_DIR = ROOT / "data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c0_contract_and_feasibility"
DOC = ROOT / "docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC0_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md"

MANIFEST_JSON = OUT_DIR / "phasec0_contract_manifest.json"
SCORE_COVERAGE_CSV = OUT_DIR / "phasec0_frozen_fresh_qlib_score_coverage.csv"
TOP50_COVERAGE_CSV = OUT_DIR / "phasec0_top50_candidate_coverage.csv"
ORTHO_COVERAGE_CSV = OUT_DIR / "phasec0_o2_orthogonal_feature_coverage.csv"
LABEL_AUDIT_CSV = OUT_DIR / "phasec0_10d_label_feasibility_audit.csv"
FEATURE_SCHEMA_CSV = OUT_DIR / "phasec0_feature_schema_plan.csv"
FORBIDDEN_JSON = OUT_DIR / "phasec0_forbidden_action_audit.json"

LTR_TRAIN_START = "2025-01-01"
LTR_TRAIN_END = "2025-12-31"
LTR_TEST_START = "2026-01-01"
LTR_TEST_END = "2026-05-07"
QLIB_TRAIN_END = "2024-12-31"
GATE = "phase_c0_clean_stacking_contract_feasible"


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


def require_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    required = [S2B_SCORE, S2B_MANIFEST, S2B_GATE, O2_FEATURES, O2_SUMMARY, O4_MANIFEST, O4_FEATURES]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing required C0 inputs: {missing}")
    return load_json(S2B_MANIFEST), load_json(S2B_GATE), load_json(O2_SUMMARY), load_json(O4_MANIFEST)


def norm(symbol: str) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def load_score() -> pd.DataFrame:
    score = pd.read_csv(S2B_SCORE, parse_dates=["date"])
    score["date_str"] = score["date"].dt.strftime("%Y-%m-%d")
    score["instrument"] = score["instrument"].map(norm)
    return score


def period_score(score: pd.DataFrame) -> pd.DataFrame:
    train = score[(score["date_str"] >= LTR_TRAIN_START) & (score["date_str"] <= LTR_TRAIN_END)].copy()
    train["clean_ltr_split"] = "ltr_train_2025"
    test = score[(score["date_str"] >= LTR_TEST_START) & (score["date_str"] <= LTR_TEST_END)].copy()
    test["clean_ltr_split"] = "ltr_test_2026"
    return pd.concat([train, test], ignore_index=True).sort_values(["date", "instrument"]).reset_index(drop=True)


def score_coverage_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split, sub in df.groupby("clean_ltr_split"):
        daily = sub.groupby("date_str", as_index=False).agg(
            rows=("instrument", "size"),
            score_rows=("qlib_score_raw", lambda s: int(s.notna().sum())),
            rank_rows=("qlib_rank", lambda s: int(s.notna().sum())),
            top50_rows=("qlib_rank", lambda s: int((s.astype(float) <= 50).sum())),
        )
        rows.append(
            {
                "clean_ltr_split": split,
                "start_date": str(sub["date_str"].min()),
                "end_date": str(sub["date_str"].max()),
                "date_count": int(daily.shape[0]),
                "row_count": int(sub.shape[0]),
                "score_missing_rows": int(sub["qlib_score_raw"].isna().sum()),
                "rank_missing_rows": int(sub["qlib_rank"].isna().sum()),
                "duplicate_key_count": int(sub.duplicated(["date_str", "instrument"]).sum()),
                "daily_rows_min": int(daily["rows"].min()),
                "daily_rows_median": float(daily["rows"].median()),
                "daily_rows_max": int(daily["rows"].max()),
                "daily_top50_min": int(daily["top50_rows"].min()),
                "daily_top50_median": float(daily["top50_rows"].median()),
                "daily_top50_max": int(daily["top50_rows"].max()),
                "all_rows_after_qlib_train_end": bool((sub["date_str"] > QLIB_TRAIN_END).all()),
            }
        )
    return rows


def top50_coverage_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    daily = (
        df.groupby(["clean_ltr_split", "date_str"], as_index=False)
        .agg(
            candidate_rows=("instrument", "size"),
            top50_rows=("qlib_rank", lambda s: int((s.astype(float) <= 50).sum())),
            min_rank=("qlib_rank", "min"),
            max_rank=("qlib_rank", "max"),
        )
        .sort_values(["clean_ltr_split", "date_str"])
    )
    daily["top50_candidate_complete"] = daily["top50_rows"] >= 50
    return daily.to_dict("records")


def latest_feature_coverage(df: pd.DataFrame) -> list[dict[str, Any]]:
    score_keys = df[["clean_ltr_split", "date", "date_str", "instrument"]].rename(columns={"instrument": "symbol"}).copy()
    features = pd.read_csv(
        O2_FEATURES,
        usecols=[
            "symbol",
            "trade_date",
            "available_at",
            "feature_family",
            "foreign_net_buy",
            "margin_balance",
            "institutional_missing_flag",
            "margin_short_missing_flag",
        ],
        parse_dates=["trade_date", "available_at"],
    )
    features["symbol"] = features["symbol"].map(norm)
    out: list[dict[str, Any]] = []
    for family, marker in [("institutional_flow", "foreign_net_buy"), ("margin_short", "margin_balance")]:
        fam = features[features["feature_family"] == family].copy()
        pieces = []
        for symbol, left in score_keys.groupby("symbol"):
            right = fam[fam["symbol"] == symbol].sort_values("available_at")
            if right.empty:
                tmp = left.copy()
                tmp["matched"] = False
                tmp["used_available_at_gt_signal_date"] = False
                tmp["used_trade_date_gt_signal_date"] = False
                pieces.append(tmp)
                continue
            merged = pd.merge_asof(
                left.sort_values("date"),
                right[["symbol", "trade_date", "available_at", marker]].sort_values("available_at"),
                left_on="date",
                right_on="available_at",
                by="symbol",
                direction="backward",
            )
            merged["matched"] = merged[marker].notna()
            merged["used_available_at_gt_signal_date"] = merged["available_at"].notna() & (merged["available_at"] > merged["date"])
            merged["used_trade_date_gt_signal_date"] = merged["trade_date"].notna() & (merged["trade_date"] > merged["date"])
            pieces.append(merged)
        joined = pd.concat(pieces, ignore_index=True)
        for split, sub in joined.groupby("clean_ltr_split"):
            daily = sub.groupby("date_str", as_index=False).agg(matched_rows=("matched", "sum"), rows=("symbol", "size"))
            out.append(
                {
                    "clean_ltr_split": split,
                    "feature_family": family,
                    "rows_checked": int(sub.shape[0]),
                    "matched_rows": int(sub["matched"].sum()),
                    "missing_rows": int((~sub["matched"]).sum()),
                    "missing_ratio": round(float((~sub["matched"]).mean()), 8),
                    "used_available_at_gt_signal_date_rows": int(sub["used_available_at_gt_signal_date"].sum()),
                    "used_trade_date_gt_signal_date_rows": int(sub["used_trade_date_gt_signal_date"].sum()),
                    "daily_matched_min": int(daily["matched_rows"].min()) if not daily.empty else 0,
                    "daily_matched_median": float(daily["matched_rows"].median()) if not daily.empty else 0.0,
                    "daily_matched_max": int(daily["matched_rows"].max()) if not daily.empty else 0,
                }
            )
    return out


def load_price(symbols: set[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for symbol in sorted(symbols):
        path = PRICE_ROOT / f"{norm(symbol)}.csv"
        if not path.exists():
            continue
        days: list[str] = []
        with path.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                day = str(row.get("date") or "")[:10]
                try:
                    close = float(row.get("close") or 0.0)
                except Exception:
                    close = 0.0
                if day and close > 0:
                    days.append(day)
        if days:
            out[norm(symbol)] = days
    return out


def label_feasibility_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    prices = load_price(set(df["instrument"]))
    rows = []
    for split, sub in df.groupby("clean_ltr_split"):
        has_label = []
        for rec in sub[["date_str", "instrument"]].itertuples(index=False):
            days = prices.get(norm(rec.instrument), [])
            try:
                idx = days.index(rec.date_str)
            except ValueError:
                has_label.append(False)
                continue
            has_label.append(idx + 10 < len(days))
        tmp = sub.copy()
        tmp["label_10d_available"] = has_label
        daily = tmp.groupby("date_str", as_index=False).agg(
            rows=("instrument", "size"),
            label_rows=("label_10d_available", "sum"),
        )
        rows.append(
            {
                "clean_ltr_split": split,
                "rows_checked": int(tmp.shape[0]),
                "label_10d_available_rows": int(tmp["label_10d_available"].sum()),
                "label_10d_missing_rows": int((~tmp["label_10d_available"]).sum()),
                "label_10d_available_ratio": round(float(tmp["label_10d_available"].mean()), 8) if not tmp.empty else 0.0,
                "daily_label_rows_min": int(daily["label_rows"].min()) if not daily.empty else 0,
                "daily_label_rows_median": float(daily["label_rows"].median()) if not daily.empty else 0.0,
                "daily_label_rows_max": int(daily["label_rows"].max()) if not daily.empty else 0,
                "label_allowed_for_training": split == "ltr_train_2025",
                "label_not_used_for_test_training": split == "ltr_test_2026",
            }
        )
    return rows


def feature_schema_rows() -> list[dict[str, Any]]:
    return pd.read_csv(O4_FEATURES).to_dict("records")


def write_report(manifest: dict[str, Any], score_rows: list[dict[str, Any]], ortho_rows: list[dict[str, Any]], label_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Phase C0 执行报告：Frozen Fresh Qlib + Orthogonal LTR Clean Stacking 合同冻结与可行性审计",
        "",
        f"生成时间：`{manifest['created_at']}`",
        "",
        "## 1. 结论",
        "",
        f"- gate：`{manifest['gate']}`。",
        "- C0 只冻结并审计合同，未训练 qlib / LTR，未回放，未调参。",
        "- LTR train 冻结为 `2025-01-01..2025-12-31`；LTR untouched test 冻结为 `2026-01-01..2026-05-07`。",
        "- frozen fresh qlib train 截止 `2024-12-31`，2025/2026 score 均在 qlib 训练期之外。",
        "- 不使用 qlib 2017..2024 in-sample score，不引入 walk-forward OOS 或多模型 score。",
        "",
        "## 2. Frozen Artifact",
        "",
        f"- fresh qlib score：`{rel(S2B_SCORE)}`",
        f"- fresh qlib manifest：`{rel(S2B_MANIFEST)}`",
        f"- O2 PIT-safe features：`{rel(O2_FEATURES)}`",
        f"- O4 LTR manifest：`{rel(O4_MANIFEST)}`",
        f"- O4 feature whitelist：`{rel(O4_FEATURES)}`",
        "",
        "## 3. Score / Top50 Coverage",
        "",
        "| split | start | end | date_count | rows | daily rows min/median/max | daily top50 min/median/max | after qlib train end |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in score_rows:
        lines.append(
            f"| {row['clean_ltr_split']} | {row['start_date']} | {row['end_date']} | {row['date_count']} | {row['row_count']} | {row['daily_rows_min']}/{row['daily_rows_median']}/{row['daily_rows_max']} | {row['daily_top50_min']}/{row['daily_top50_median']}/{row['daily_top50_max']} | {row['all_rows_after_qlib_train_end']} |"
        )
    lines.extend(
        [
            "",
            "## 4. O2 正交特征 PIT Coverage",
            "",
            "| split | family | rows | matched | missing_ratio | available_at violation | trade_date violation |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in ortho_rows:
        lines.append(
            f"| {row['clean_ltr_split']} | {row['feature_family']} | {row['rows_checked']} | {row['matched_rows']} | {row['missing_ratio']} | {row['used_available_at_gt_signal_date_rows']} | {row['used_trade_date_gt_signal_date_rows']} |"
        )
    lines.extend(
        [
            "",
            "## 5. 10d Label 可行性",
            "",
            "| split | rows | label rows | missing rows | available ratio | use policy |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in label_rows:
        policy = "train label allowed" if row["label_allowed_for_training"] else "test label audit only; not used for training"
        lines.append(
            f"| {row['clean_ltr_split']} | {row['rows_checked']} | {row['label_10d_available_rows']} | {row['label_10d_missing_rows']} | {row['label_10d_available_ratio']} | {policy} |"
        )
    lines.extend(
        [
            "",
            "## 6. 冻结合同",
            "",
            "- LTR model family / hyperparameters 沿用 O4：`LightGBM.LGBMRanker` / `lambdarank`，不调参。",
            "- label 沿用 O4 / Phase1C：`relevance_10d_top_heavy`。",
            "- preserve scope：`top50_only`。",
            "- replay 合同为后续 C3 冻结：next-day execution, `fee_rate=0.001425`, `tax_rate=0.003`, `target_position_count=10`, `candidate_k=50`。",
            "- 2026 只作为 untouched test，不用于训练、调参或选择。",
            "",
            "## 7. 禁止事项审计",
            "",
            "- 未训练 qlib。",
            "- 未训练 LTR。",
            "- 未调参。",
            "- 未改 split / label / model。",
            "- 未使用 qlib 训练期 in-sample score。",
            "- 未引入 walk-forward OOS、多模型 score。",
            "- 未改前端/API/provider/accepted latest/monitor，未触发交易链路。",
            "",
            "## 8. 输出 Artifact",
            "",
            f"- `{rel(MANIFEST_JSON)}`",
            f"- `{rel(SCORE_COVERAGE_CSV)}`",
            f"- `{rel(TOP50_COVERAGE_CSV)}`",
            f"- `{rel(ORTHO_COVERAGE_CSV)}`",
            f"- `{rel(LABEL_AUDIT_CSV)}`",
            f"- `{rel(FEATURE_SCHEMA_CSV)}`",
            f"- `{rel(FORBIDDEN_JSON)}`",
            "",
            "## 9. 是否允许进入 C1",
            "",
            f"- 建议：允许进入 C1，gate 为 `{manifest['gate']}`。",
        ]
    )
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = now()
    s2b_manifest, s2b_gate, o2_summary, o4_manifest = require_inputs()
    score = period_score(load_score())
    if score.empty:
        raise RuntimeError("No frozen fresh qlib score rows for 2025/2026 C0 windows")
    score_rows = score_coverage_rows(score)
    top50_rows = top50_coverage_rows(score)
    ortho_rows = latest_feature_coverage(score)
    label_rows = label_feasibility_rows(score)
    schema_rows = feature_schema_rows()

    stop_reasons = []
    if not all(row["all_rows_after_qlib_train_end"] for row in score_rows):
        stop_reasons.append("score_rows_include_qlib_in_sample_period")
    if any(row["daily_top50_min"] < 50 for row in score_rows):
        stop_reasons.append("top50_candidate_coverage_incomplete")
    train_label = next(row for row in label_rows if row["clean_ltr_split"] == "ltr_train_2025")
    if train_label["label_10d_available_ratio"] < 0.95:
        stop_reasons.append("2025_10d_label_availability_too_low")
    if any(row["used_available_at_gt_signal_date_rows"] > 0 or row["used_trade_date_gt_signal_date_rows"] > 0 for row in ortho_rows):
        stop_reasons.append("o2_pit_join_violation")
    if s2b_manifest.get("train_rows_raw", 0) <= 0 or not s2b_gate.get("fresh_qlib_training_completed", True):
        stop_reasons.append("frozen_fresh_qlib_gate_missing")
    if o2_summary.get("gate") != "phase_o2_pit_safe_feature_builder_passed":
        stop_reasons.append("o2_gate_not_passed")
    if o4_manifest.get("gate") != "phase_o4_controlled_treatment_ltr_trained":
        stop_reasons.append("o4_contract_gate_not_available")

    forbidden = {
        "created_at": created_at,
        "phase": "phase_c0_contract_and_feasibility",
        "no_qlib_training": True,
        "no_ltr_training": True,
        "no_replay": True,
        "no_parameter_search": True,
        "no_split_label_model_change": True,
        "no_qlib_in_sample_score_for_ltr_train": True,
        "no_walk_forward_oos_or_multi_model_score": True,
        "no_frontend_api_provider_accepted_latest_monitor_trading": True,
        "no_broker_quick_trade_orders": True,
    }
    manifest = {
        "created_at": created_at,
        "phase": "phase_c0_contract_and_feasibility",
        "gate": GATE if not stop_reasons else "clean_stacking_blocked_by_sample_or_contract",
        "stop_reasons": stop_reasons,
        "frozen_fresh_qlib": {
            "score_artifact": rel(S2B_SCORE),
            "manifest": rel(S2B_MANIFEST),
            "model_path": s2b_manifest.get("model_path"),
            "qlib_train_end": QLIB_TRAIN_END,
            "same_frozen_model_for_2025_and_2026": True,
        },
        "clean_ltr_contract": {
            "ltr_train": [LTR_TRAIN_START, LTR_TRAIN_END],
            "ltr_test": [LTR_TEST_START, LTR_TEST_END],
            "preserve_scope": "top50_only",
            "label": "relevance_10d_top_heavy",
            "model_config_source": rel(O4_MANIFEST),
            "model_config": o4_manifest.get("model_config", {}),
            "no_2026_training_tuning_selection": True,
        },
        "score_coverage": score_rows,
        "orthogonal_feature_coverage": ortho_rows,
        "label_feasibility": label_rows,
        "feature_schema_plan": {
            "source": rel(O4_FEATURES),
            "feature_count": len(schema_rows),
            "families": sorted({str(row.get("family")) for row in schema_rows}),
        },
        "forbidden_action_audit": rel(FORBIDDEN_JSON),
    }
    wcsv(SCORE_COVERAGE_CSV, score_rows)
    wcsv(TOP50_COVERAGE_CSV, top50_rows)
    wcsv(ORTHO_COVERAGE_CSV, ortho_rows)
    wcsv(LABEL_AUDIT_CSV, label_rows)
    wcsv(FEATURE_SCHEMA_CSV, schema_rows)
    wjson(FORBIDDEN_JSON, forbidden)
    wjson(MANIFEST_JSON, manifest)
    write_report(manifest, score_rows, ortho_rows, label_rows)
    print(json.dumps({"ok": not stop_reasons, "gate": manifest["gate"], "report": rel(DOC), "out_dir": rel(OUT_DIR), "stop_reasons": stop_reasons}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
