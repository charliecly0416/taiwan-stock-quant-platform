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
OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample"
REPORT = ROOT / "docs/tw_ltr_orthogonal_features_controlled/PHASEO3_ROW_ALIGNED_TREATMENT_SAMPLE_EXECUTION_REPORT_CN.md"

CONTROL_SAMPLE = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv"
O0_CONTRACT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o0_contract_freeze/phaseo0_experiment_contract.json"
O2_DIR = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder"
O2_FEATURES = O2_DIR / "normalized_feature_daily.csv"
O2_DICTIONARY = O2_DIR / "feature_dictionary.csv"
O2_SUMMARY = O2_DIR / "phaseo2_summary.json"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


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


def df_hash(df: pd.DataFrame, cols: list[str]) -> str:
    text = df[cols].astype("string").fillna("<NA>").to_csv(index=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def row_hashes(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    return pd.util.hash_pandas_object(df[cols].astype("string").fillna("<NA>"), index=False).astype("uint64").astype(str)


def asof_join(control: pd.DataFrame, features: pd.DataFrame, family: str, value_cols: list[str]) -> pd.DataFrame:
    pieces = []
    meta_cols = [
        "trade_date",
        "available_at",
        "raw_snapshot_id",
        "delay_days",
        "delay_reason",
        "available_at_contract",
        "raw_snapshot_path",
        "lineage_source",
    ]
    right_cols = ["symbol", *meta_cols, *value_cols]
    feat = features[features["feature_family"] == family][right_cols].copy()
    feat = feat.rename(columns={col: f"{family}_{col}" for col in meta_cols})
    for symbol, left in control.groupby("instrument", sort=False):
        left2 = left[["control_row_id", "date", "instrument"]].copy().sort_values("date")
        right = feat[feat["symbol"] == symbol].copy().sort_values(f"{family}_available_at")
        if right.empty:
            joined = left2.copy()
            for col in value_cols:
                joined[col] = 0
            for col in meta_cols:
                joined[f"{family}_{col}"] = ""
            joined[f"{family}_asof_missing_flag"] = 1
        else:
            joined = pd.merge_asof(
                left2,
                right,
                left_on="date",
                right_on=f"{family}_available_at",
                left_by="instrument",
                right_by="symbol",
                direction="backward",
                allow_exact_matches=True,
            )
            joined = joined.drop(columns=["symbol"], errors="ignore")
            missing = joined[f"{family}_available_at"].isna()
            for col in value_cols:
                joined[col] = pd.to_numeric(joined[col], errors="coerce").fillna(0)
            for col in meta_cols:
                meta = f"{family}_{col}"
                if meta in joined:
                    joined[meta] = joined[meta].fillna("")
            joined[f"{family}_asof_missing_flag"] = missing.astype(int)
        joined[f"{family}_used_available_at_gt_sample_date"] = (
            pd.to_datetime(joined[f"{family}_available_at"], errors="coerce") > joined["date"]
        ).fillna(False)
        joined[f"{family}_used_trade_date_gt_sample_date"] = (
            pd.to_datetime(joined[f"{family}_trade_date"], errors="coerce") > joined["date"]
        ).fillna(False)
        pieces.append(joined)
    result = pd.concat(pieces, ignore_index=True).sort_values("control_row_id")
    keep_cols = [
        "control_row_id",
        *value_cols,
        *[f"{family}_{col}" for col in meta_cols],
        f"{family}_asof_missing_flag",
        f"{family}_used_available_at_gt_sample_date",
        f"{family}_used_trade_date_gt_sample_date",
    ]
    return result[keep_cols]


def monotonic_audit(features: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for (family, symbol), group in features.sort_values(["feature_family", "symbol", "trade_date"]).groupby(["feature_family", "symbol"]):
        available = pd.to_datetime(group["available_at"], errors="coerce")
        bad = bool((available.diff().dropna() < pd.Timedelta(0)).any())
        if bad:
            rows.append({"feature_family": family, "symbol": symbol, "nonmonotonic": True})
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    generated_at = now()
    contract = json.loads(O0_CONTRACT.read_text(encoding="utf-8"))
    original_features = contract["control_input_features"]
    label_cols = ["ltr_relevance_label", "label_complete_5d", "label_complete_10d", "label_complete_20d"]
    identity_cols = ["date", "instrument", "split", "sample_complete"]

    control = pd.read_csv(CONTROL_SAMPLE)
    control.insert(0, "control_row_id", range(len(control)))
    control["date"] = pd.to_datetime(control["date"], errors="coerce")
    features = pd.read_csv(O2_FEATURES)
    features["trade_date"] = pd.to_datetime(features["trade_date"], errors="coerce")
    features["available_at"] = pd.to_datetime(features["available_at"], errors="coerce")

    institutional_cols = [
        "foreign_net_buy",
        "investment_trust_net_buy",
        "dealer_net_buy",
        "institutional_total_net_buy",
        "foreign_net_buy_roll1",
        "foreign_net_buy_roll3",
        "foreign_net_buy_roll5",
        "foreign_net_buy_roll10",
        "investment_trust_net_buy_roll1",
        "investment_trust_net_buy_roll3",
        "investment_trust_net_buy_roll5",
        "investment_trust_net_buy_roll10",
        "dealer_net_buy_roll1",
        "dealer_net_buy_roll3",
        "dealer_net_buy_roll5",
        "dealer_net_buy_roll10",
        "institutional_total_net_buy_roll1",
        "institutional_total_net_buy_roll3",
        "institutional_total_net_buy_roll5",
        "institutional_total_net_buy_roll10",
        "institutional_total_net_buy_streak",
        "institutional_missing_flag",
        "institutional_delay_flag",
    ]
    margin_cols = [
        "margin_balance",
        "margin_balance_change",
        "short_balance",
        "short_balance_change",
        "margin_balance_change_roll1",
        "margin_balance_change_roll3",
        "margin_balance_change_roll5",
        "margin_balance_change_roll10",
        "short_balance_change_roll1",
        "short_balance_change_roll3",
        "short_balance_change_roll5",
        "short_balance_change_roll10",
        "margin_direction_proxy",
        "short_direction_proxy",
        "margin_short_divergence_proxy",
        "margin_short_missing_flag",
        "margin_short_delay_flag",
    ]
    inst_join = asof_join(control, features, "institutional_flow", institutional_cols)
    margin_join = asof_join(control, features, "margin_short", margin_cols)

    treatment = control.merge(inst_join, on="control_row_id", how="left").merge(margin_join, on="control_row_id", how="left")
    treatment = treatment.sort_values("control_row_id")

    treatment_path = OUT / "phaseo3_treatment_candidate_sample.csv"
    treatment.to_csv(treatment_path, index=False)

    control_label_hash = df_hash(control, label_cols)
    treatment_label_hash = df_hash(treatment, label_cols)
    control_original_hash = df_hash(control, original_features)
    treatment_original_hash = df_hash(treatment, original_features)
    control_identity_hash = df_hash(control, identity_cols)
    treatment_identity_hash = df_hash(treatment, identity_cols)
    row_hash = pd.DataFrame(
        {
            "control_row_id": control["control_row_id"],
            "control_identity_hash": row_hashes(control, identity_cols),
            "treatment_identity_hash": row_hashes(treatment, identity_cols),
            "control_label_hash": row_hashes(control, label_cols),
            "treatment_label_hash": row_hashes(treatment, label_cols),
            "control_original_feature_hash": row_hashes(control, original_features),
            "treatment_original_feature_hash": row_hashes(treatment, original_features),
        }
    )
    row_hash["identity_match"] = row_hash["control_identity_hash"] == row_hash["treatment_identity_hash"]
    row_hash["label_match"] = row_hash["control_label_hash"] == row_hash["treatment_label_hash"]
    row_hash["original_feature_match"] = row_hash["control_original_feature_hash"] == row_hash["treatment_original_feature_hash"]
    row_hash.to_csv(OUT / "phaseo3_row_hash_audit.csv", index=False)

    added_cols = [col for col in treatment.columns if col not in control.columns]
    allowed_prefixes = ("institutional_", "margin_", "short_", "foreign_", "investment_", "dealer_")
    schema_rows = []
    for col in added_cols:
        schema_rows.append(
            {
                "column": col,
                "status": "allowed_orthogonal_feature_or_metadata"
                if col == "control_row_id" or col.startswith(allowed_prefixes)
                else "review_required",
            }
        )
    write_csv(OUT / "phaseo3_feature_schema_diff.csv", schema_rows)

    leakage_rows = [
        {
            "feature_family": "institutional_flow",
            "used_available_at_gt_sample_date_rows": int(treatment["institutional_flow_used_available_at_gt_sample_date"].sum()),
            "used_trade_date_gt_sample_date_rows": int(treatment["institutional_flow_used_trade_date_gt_sample_date"].sum()),
            "missing_rows": int(treatment["institutional_flow_asof_missing_flag"].sum()),
            "missing_ratio": float(treatment["institutional_flow_asof_missing_flag"].mean()),
        },
        {
            "feature_family": "margin_short",
            "used_available_at_gt_sample_date_rows": int(treatment["margin_short_used_available_at_gt_sample_date"].sum()),
            "used_trade_date_gt_sample_date_rows": int(treatment["margin_short_used_trade_date_gt_sample_date"].sum()),
            "missing_rows": int(treatment["margin_short_asof_missing_flag"].sum()),
            "missing_ratio": float(treatment["margin_short_asof_missing_flag"].mean()),
        },
    ]
    write_csv(OUT / "phaseo3_pit_leakage_audit.csv", leakage_rows)

    align_rows = [
        {"metric": "control_rows", "value": int(len(control))},
        {"metric": "treatment_rows", "value": int(len(treatment))},
        {"metric": "control_label_hash", "value": control_label_hash},
        {"metric": "treatment_label_hash", "value": treatment_label_hash},
        {"metric": "control_original_feature_hash", "value": control_original_hash},
        {"metric": "treatment_original_feature_hash", "value": treatment_original_hash},
        {"metric": "control_identity_hash", "value": control_identity_hash},
        {"metric": "treatment_identity_hash", "value": treatment_identity_hash},
        {"metric": "row_identity_mismatch_count", "value": int((~row_hash["identity_match"]).sum())},
        {"metric": "row_label_mismatch_count", "value": int((~row_hash["label_match"]).sum())},
        {"metric": "row_original_feature_mismatch_count", "value": int((~row_hash["original_feature_match"]).sum())},
        {"metric": "added_column_count", "value": int(len(added_cols))},
    ]
    write_csv(OUT / "phaseo3_row_alignment_audit.csv", align_rows)

    missing_symbol_rows = []
    for symbol, group in treatment.groupby("instrument"):
        missing_symbol_rows.append(
            {
                "symbol": symbol,
                "rows": int(len(group)),
                "institutional_missing_rows": int(group["institutional_flow_asof_missing_flag"].sum()),
                "institutional_missing_ratio": float(group["institutional_flow_asof_missing_flag"].mean()),
                "margin_short_missing_rows": int(group["margin_short_asof_missing_flag"].sum()),
                "margin_short_missing_ratio": float(group["margin_short_asof_missing_flag"].mean()),
            }
        )
    write_csv(OUT / "phaseo3_missing_by_symbol.csv", missing_symbol_rows)

    monotonic_rows = monotonic_audit(features)
    write_csv(OUT / "phaseo3_rolling_available_at_monotonic_audit.csv", monotonic_rows or [{"nonmonotonic_groups": 0}])
    nonmonotonic_groups = len(monotonic_rows)
    leakage_fail = any(row["used_available_at_gt_sample_date_rows"] or row["used_trade_date_gt_sample_date_rows"] for row in leakage_rows)
    schema_fail = any(row["status"] == "review_required" for row in schema_rows)
    gate_pass = (
        len(control) == len(treatment)
        and control_label_hash == treatment_label_hash
        and control_original_hash == treatment_original_hash
        and control_identity_hash == treatment_identity_hash
        and int((~row_hash["identity_match"]).sum()) == 0
        and int((~row_hash["label_match"]).sum()) == 0
        and int((~row_hash["original_feature_match"]).sum()) == 0
        and not leakage_fail
        and not schema_fail
        and nonmonotonic_groups == 0
    )
    gate = "phase_o3_treatment_sample_row_aligned_passed" if gate_pass else "phase_o3_blocked_requires_repair"
    summary = {
        "created_at": generated_at,
        "phase": "phase_o3_row_aligned_treatment_sample",
        "gate": gate,
        "control_rows": int(len(control)),
        "treatment_rows": int(len(treatment)),
        "control_label_hash": control_label_hash,
        "treatment_label_hash": treatment_label_hash,
        "control_original_feature_hash": control_original_hash,
        "treatment_original_feature_hash": treatment_original_hash,
        "control_identity_hash": control_identity_hash,
        "treatment_identity_hash": treatment_identity_hash,
        "added_column_count": int(len(added_cols)),
        "leakage_audit": leakage_rows,
        "rolling_window_available_at_monotonic_groups": nonmonotonic_groups,
        "no_training": True,
        "no_replay": True,
        "no_control_change": True,
        "no_frontend_api_provider_accepted_latest_monitor_trading": True,
    }
    write_json(OUT / "phaseo3_summary.json", summary)

    report_lines = [
        "# Phase O3 执行报告：受控样本拼接",
        "",
        f"生成时间：`{generated_at}`",
        "",
        "## 1. 执行结论",
        "",
        "本轮只读取 Phase1C control LTR sample 与 O2 PIT-safe daily features，按 `available_at <= sample_date` 做 row-aligned treatment candidate 拼接。",
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
        "- 未做收益率回放。",
        "- 未修改 Phase1C control。",
        "- 未改 label / 原始特征 / 训练窗口 / 回放窗口。",
        "- 未新增过滤器、阈值、market gate、turnover rule。",
        "- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。",
        "",
        "## 3. Row Alignment",
        "",
        *md_table(align_rows, ["metric", "value"], limit=20),
        "",
        "## 4. PIT Leakage Audit",
        "",
        *md_table(leakage_rows, ["feature_family", "used_available_at_gt_sample_date_rows", "used_trade_date_gt_sample_date_rows", "missing_rows", "missing_ratio"]),
        "",
        "## 5. Rolling Window available_at 单调审计",
        "",
        f"- rolling_window_available_at_monotonic_groups：`{nonmonotonic_groups}`",
        "",
        "## 6. 新增列范围",
        "",
        f"- added_column_count：`{len(added_cols)}`",
        "- 新增列只来自 O2 feature dictionary 的 institutional_flow / margin_short 特征与 PIT lineage metadata。",
        "",
        "## 7. 输出产物",
        "",
        f"- `{rel(treatment_path)}`",
        f"- `{rel(OUT / 'phaseo3_row_alignment_audit.csv')}`",
        f"- `{rel(OUT / 'phaseo3_row_hash_audit.csv')}`",
        f"- `{rel(OUT / 'phaseo3_feature_schema_diff.csv')}`",
        f"- `{rel(OUT / 'phaseo3_pit_leakage_audit.csv')}`",
        f"- `{rel(OUT / 'phaseo3_missing_by_symbol.csv')}`",
        f"- `{rel(OUT / 'phaseo3_rolling_available_at_monotonic_audit.csv')}`",
        f"- `{rel(OUT / 'phaseo3_summary.json')}`",
        "",
        "## 8. 后续边界",
        "",
        "O3 通过只说明样本行级拼接合同通过；仍不得视为已训练或已证明收益率优劣。进入 O4 前仍需审查。",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "gate": gate, "report": rel(REPORT), "summary": rel(OUT / "phaseo3_summary.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
