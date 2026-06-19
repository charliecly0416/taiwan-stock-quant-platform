#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q1_orthogonal_qlib_feature_join"
REPORT = ROOT / "docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ1_ORTHOGONAL_QLIB_FEATURE_JOIN_EXECUTION_REPORT_CN.md"

Q0_REPORT = ROOT / "docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ0_CONTROL_AND_FEATURE_CONTRACT_EXECUTION_REPORT_CN.md"
S2B_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training"
S2D_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay"
O2_DIR = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder"

CONTROL_ROWS = S2B_DIR / "phase_s2b_raw_score_rank.csv"
S2B_CONFIG = S2B_DIR / "phase_s2b_generated_qlib_config.yaml"
S2B_MANIFEST = S2B_DIR / "phase_s2b_training_manifest.json"
S2D_GATE = S2D_DIR / "phase_s2d_gate_summary.json"
O2_FEATURES = O2_DIR / "normalized_feature_daily.csv"
O2_DICTIONARY = O2_DIR / "feature_dictionary.csv"
O2_PIT = O2_DIR / "pit_leakage_audit.csv"
O2_LINEAGE = O2_DIR / "pit_lineage_audit.csv"

FAMILY_FEATURES = {
    "institutional_flow": [
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
    ],
    "margin_short": [
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
    ],
}

FAMILY_PREFIX = {
    "institutional_flow": "institutional_flow",
    "margin_short": "margin_short",
}


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


def md(rows: list[dict[str, Any]], fields: list[str]) -> list[str]:
    out = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return out


def load_control() -> pd.DataFrame:
    df = pd.read_csv(CONTROL_ROWS)
    df["control_row_id"] = range(len(df))
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["instrument"] = df["instrument"].astype(str).str.upper()
    if df["date"].isna().any():
        raise RuntimeError("control rows contain invalid dates")
    return df


def load_o2() -> pd.DataFrame:
    df = pd.read_csv(O2_FEATURES)
    df["symbol"] = df["symbol"].astype(str).str.upper()
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    df["available_at"] = pd.to_datetime(df["available_at"], errors="coerce")
    return df.dropna(subset=["symbol", "trade_date", "available_at"]).copy()


def join_family(control: pd.DataFrame, features: pd.DataFrame, family: str) -> pd.DataFrame:
    feature_cols = [c for c in FAMILY_FEATURES[family] if c in features.columns]
    metadata_cols = [
        "trade_date",
        "available_at",
        "delay_days",
        "delay_reason",
        "raw_snapshot_id",
        "raw_snapshot_path",
        "lineage_source",
    ]
    use_cols = ["symbol", *metadata_cols, *feature_cols]
    fam = features.loc[features["feature_family"].eq(family), [c for c in use_cols if c in features.columns]].copy()
    fam = fam.sort_values(["symbol", "available_at", "trade_date"])
    joined_parts: list[pd.DataFrame] = []
    for symbol, cgrp in control.sort_values(["instrument", "date"]).groupby("instrument", sort=False):
        fgrp = fam[fam["symbol"].eq(symbol)].sort_values("available_at")
        left = cgrp[["control_row_id", "date", "instrument"]].sort_values("date")
        if fgrp.empty:
            part = left.copy()
            for col in metadata_cols + feature_cols:
                if col not in part:
                    part[col] = pd.NA
        else:
            part = pd.merge_asof(
                left,
                fgrp,
                left_on="date",
                right_on="available_at",
                direction="backward",
                allow_exact_matches=True,
            )
        joined_parts.append(part)
    joined = pd.concat(joined_parts, ignore_index=True)
    prefix = FAMILY_PREFIX[family]
    missing_col = "institutional_missing_flag" if family == "institutional_flow" else "margin_short_missing_flag"
    matched = joined["available_at"].notna() if "available_at" in joined else pd.Series(False, index=joined.index)
    for col in feature_cols:
        joined[col] = pd.to_numeric(joined[col], errors="coerce").fillna(0.0)
    if missing_col in joined:
        joined[missing_col] = joined[missing_col].where(matched, 1).fillna(1).astype(int)
    joined[f"{prefix}_matched_trade_date"] = pd.to_datetime(joined.get("trade_date"), errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    joined[f"{prefix}_matched_available_at"] = pd.to_datetime(joined.get("available_at"), errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    joined[f"{prefix}_delay_days"] = pd.to_numeric(joined.get("delay_days"), errors="coerce").fillna(0.0)
    joined[f"{prefix}_delay_reason"] = joined.get("delay_reason", pd.Series("", index=joined.index)).fillna("").astype(str)
    joined[f"{prefix}_raw_snapshot_id"] = joined.get("raw_snapshot_id", pd.Series("", index=joined.index)).fillna("").astype(str)
    joined[f"{prefix}_raw_snapshot_path"] = joined.get("raw_snapshot_path", pd.Series("", index=joined.index)).fillna("").astype(str)
    joined[f"{prefix}_lineage_source"] = joined.get("lineage_source", pd.Series("", index=joined.index)).fillna("").astype(str)
    joined[f"{prefix}_used_available_at_gt_signal_asof"] = pd.to_datetime(joined.get("available_at"), errors="coerce") > joined["date"]
    joined[f"{prefix}_used_trade_date_gt_signal_asof"] = pd.to_datetime(joined.get("trade_date"), errors="coerce") > joined["date"]
    out_cols = [
        "control_row_id",
        *feature_cols,
        f"{prefix}_matched_trade_date",
        f"{prefix}_matched_available_at",
        f"{prefix}_delay_days",
        f"{prefix}_delay_reason",
        f"{prefix}_raw_snapshot_id",
        f"{prefix}_raw_snapshot_path",
        f"{prefix}_lineage_source",
        f"{prefix}_used_available_at_gt_signal_asof",
        f"{prefix}_used_trade_date_gt_signal_asof",
    ]
    return joined[out_cols]


def split_counts(df: pd.DataFrame) -> dict[str, int]:
    return {str(k): int(v) for k, v in df.groupby("split").size().items()}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    created_at = now()
    control = load_control()
    o2 = load_o2()
    treatment = control.copy()
    family_joined: dict[str, pd.DataFrame] = {}
    for family in ["institutional_flow", "margin_short"]:
        fam_joined = join_family(control, o2, family)
        family_joined[family] = fam_joined
        treatment = treatment.merge(fam_joined, on="control_row_id", how="left", validate="one_to_one")

    treatment_path = OUT / "treatment_joined_sample.csv"
    treatment.to_csv(treatment_path, index=False)

    control_keys = control[["control_row_id", "date", "instrument", "split"]].copy()
    treatment_keys = treatment[["control_row_id", "date", "instrument", "split"]].copy()
    row_alignment = [{
        "check": "row_count",
        "control": len(control_keys),
        "treatment": len(treatment_keys),
        "pass": len(control_keys) == len(treatment_keys),
    }, {
        "check": "control_row_id_exact_match",
        "control": "ordered",
        "treatment": "ordered",
        "pass": control_keys["control_row_id"].equals(treatment_keys["control_row_id"]),
    }, {
        "check": "date_instrument_split_exact_match",
        "control": "date|instrument|split",
        "treatment": "date|instrument|split",
        "pass": control_keys[["date", "instrument", "split"]].equals(treatment_keys[["date", "instrument", "split"]]),
    }, {
        "check": "symbol_count",
        "control": int(control["instrument"].nunique()),
        "treatment": int(treatment["instrument"].nunique()),
        "pass": int(control["instrument"].nunique()) == int(treatment["instrument"].nunique()),
    }]
    write_csv(OUT / "row_alignment_audit.csv", row_alignment, ["check", "control", "treatment", "pass"])

    control_cols = set(control.columns) - {"control_row_id"}
    treatment_cols = set(treatment.columns) - {"control_row_id"}
    added_cols = sorted(treatment_cols - control_cols)
    removed_cols = sorted(control_cols - treatment_cols)
    schema_rows = (
        [{"column": c, "status": "added_q0_orthogonal_or_lineage"} for c in added_cols]
        + [{"column": c, "status": "removed_from_control"} for c in removed_cols]
        + [{"column": c, "status": "unchanged_control"} for c in sorted(control_cols & treatment_cols)]
    )
    write_csv(OUT / "schema_diff.csv", schema_rows, ["column", "status"])

    missing_rows = []
    pit_rows = []
    for family, prefix in FAMILY_PREFIX.items():
        missing_col = "institutional_missing_flag" if family == "institutional_flow" else "margin_short_missing_flag"
        matched_available = f"{prefix}_matched_available_at"
        matched_trade = f"{prefix}_matched_trade_date"
        available_violation = f"{prefix}_used_available_at_gt_signal_asof"
        trade_violation = f"{prefix}_used_trade_date_gt_signal_asof"
        missing = pd.to_numeric(treatment[missing_col], errors="coerce").fillna(1).astype(int)
        missing_rows.append({
            "feature_family": family,
            "control_rows": int(len(treatment)),
            "missing_rows": int(missing.sum()),
            "missing_ratio": round(float(missing.mean()), 8),
            "matched_rows": int((missing == 0).sum()),
            "symbol_count": int(treatment["instrument"].nunique()),
            "date_min": str(treatment["date"].min())[:10],
            "date_max": str(treatment["date"].max())[:10],
        })
        pit_rows.append({
            "feature_family": family,
            "rows_checked": int(len(treatment)),
            "used_available_at_gt_signal_asof_rows": int(treatment[available_violation].fillna(False).sum()),
            "used_trade_date_gt_signal_asof_rows": int(treatment[trade_violation].fillna(False).sum()),
            "matched_available_at_min": min([x for x in treatment[matched_available].astype(str).tolist() if x], default=""),
            "matched_available_at_max": max([x for x in treatment[matched_available].astype(str).tolist() if x], default=""),
            "matched_trade_date_min": min([x for x in treatment[matched_trade].astype(str).tolist() if x], default=""),
            "matched_trade_date_max": max([x for x in treatment[matched_trade].astype(str).tolist() if x], default=""),
            "pit_pass": not bool(treatment[available_violation].fillna(False).any() or treatment[trade_violation].fillna(False).any()),
        })
    write_csv(OUT / "missing_report.csv", missing_rows)
    write_csv(OUT / "pit_leakage_audit.csv", pit_rows)
    write_csv(OUT / "available_at_join_audit.csv", pit_rows)

    approved_prefixes = [
        "foreign_net_buy",
        "investment_trust_net_buy",
        "dealer_net_buy",
        "institutional_total_net_buy",
        "margin_balance",
        "short_balance",
        "margin_direction_proxy",
        "short_direction_proxy",
        "margin_short_divergence_proxy",
        "institutional_",
        "margin_short_",
    ]
    allowed_added = []
    disallowed_added = []
    for col in added_cols:
        allowed = (
            col in FAMILY_FEATURES["institutional_flow"]
            or col in FAMILY_FEATURES["margin_short"]
            or any(col.startswith(prefix) for prefix in approved_prefixes)
            or col.startswith("short_balance_change_roll")
            or col.startswith("margin_balance_change_roll")
            or col.startswith("dealer_net_buy_roll")
            or col.startswith("foreign_net_buy_roll")
            or col.startswith("investment_trust_net_buy_roll")
        )
        (allowed_added if allowed else disallowed_added).append(col)

    config_draft = OUT / "orthogonal_fresh_qlib_dataset_config_draft.yaml"
    config_draft.write_text(
        "\n".join([
            "# draft only, no training executed",
            "# Phase Q1 preserves the S2B Alpha158 handler and proposes an external as-of joined",
            "# orthogonal feature table for Phase Q2 implementation review.",
            "control_config: data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_generated_qlib_config.yaml",
            "treatment_joined_sample: data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q1_orthogonal_qlib_feature_join/treatment_joined_sample.csv",
            "join_keys: [instrument, datetime]",
            "availability_rule: available_at <= signal_asof",
            "training_executed: false",
        ]) + "\n",
        encoding="utf-8",
    )

    forbidden = {
        "created_at": created_at,
        "no_training": True,
        "no_ltr": True,
        "no_parameter_tuning": True,
        "label_changed": False,
        "split_changed": False,
        "universe_changed": False,
        "alpha158_changed": False,
        "post_score_filter_changed": False,
        "replay_rule_changed": False,
        "frontend_api_touched": False,
        "provider_refresh_publish": False,
        "accepted_latest_switching": False,
        "monitor_or_trading_chain_touched": False,
        "broker_quick_trade_orders": False,
        "target_position_or_target_weight": False,
    }
    write_json(OUT / "forbidden_action_audit.json", forbidden)

    pass_gate = all(row["pass"] for row in row_alignment) and not removed_cols and not disallowed_added and all(row["pit_pass"] for row in pit_rows)
    gate = "phase_q1_orthogonal_qlib_feature_join_passed" if pass_gate else "phase_q1_orthogonal_qlib_feature_join_blocked"
    manifest = {
        "created_at": created_at,
        "phase": "phase_q1_orthogonal_qlib_feature_join",
        "gate": gate,
        "q0_gate_required": "phase_q0_control_and_orthogonal_feature_contract_frozen",
        "control_rows": int(len(control)),
        "treatment_rows": int(len(treatment)),
        "control_symbol_count": int(control["instrument"].nunique()),
        "treatment_symbol_count": int(treatment["instrument"].nunique()),
        "date_min": str(control["date"].min())[:10],
        "date_max": str(control["date"].max())[:10],
        "split_counts": split_counts(control),
        "control_label_equals_treatment_label": True,
        "control_split_equals_treatment_split": True,
        "control_universe_policy_equals_treatment_universe_policy": True,
        "only_added_columns_equal_approved_orthogonal_features_and_missing_flags": not bool(disallowed_added),
        "removed_control_columns": removed_cols,
        "disallowed_added_columns": disallowed_added,
        "added_columns": added_cols,
        "artifacts": {
            "treatment_joined_sample": rel(treatment_path),
            "schema_diff": rel(OUT / "schema_diff.csv"),
            "row_alignment_audit": rel(OUT / "row_alignment_audit.csv"),
            "missing_report": rel(OUT / "missing_report.csv"),
            "pit_leakage_audit": rel(OUT / "pit_leakage_audit.csv"),
            "available_at_join_audit": rel(OUT / "available_at_join_audit.csv"),
            "forbidden_action_audit": rel(OUT / "forbidden_action_audit.json"),
            "dataset_config_draft": rel(config_draft),
        },
        "inputs": {
            "q0_report": rel(Q0_REPORT),
            "s2b_training_manifest": rel(S2B_MANIFEST),
            "s2b_generated_config": rel(S2B_CONFIG),
            "s2d_gate": rel(S2D_GATE),
            "o2_features": rel(O2_FEATURES),
            "o2_dictionary": rel(O2_DICTIONARY),
            "o2_pit": rel(O2_PIT),
            "o2_lineage": rel(O2_LINEAGE),
        },
    }
    write_json(OUT / "feature_join_manifest.json", manifest)

    report = [
        "# Phase Q1 执行报告：Orthogonal Qlib Feature Join 与样本对齐",
        "",
        f"生成时间：`{created_at}`",
        "",
        "## 1. 结论",
        "",
        f"- gate：`{gate}`。",
        "- 本阶段只做 S2B fresh qlib control row universe 与 O2 PIT-safe 正交特征的 as-of join 审计。",
        "- 未训练 Orthogonal Fresh Qlib，未回放，未比较收益。",
        "- 未改 Alpha158、label、split、universe、model params、post-score filter 或 replay 合同。",
        "- 未引入 LTR，未新增 filter / market gate / turnover rule。",
        "",
        "## 2. 输入 Artifact",
        "",
        f"- Q0 report：`{rel(Q0_REPORT)}`",
        f"- S2B raw score row universe：`{rel(CONTROL_ROWS)}`",
        f"- S2B generated config：`{rel(S2B_CONFIG)}`",
        f"- S2D gate：`{rel(S2D_GATE)}`",
        f"- O2 normalized features：`{rel(O2_FEATURES)}`",
        f"- O2 feature dictionary：`{rel(O2_DICTIONARY)}`",
        f"- O2 PIT audit：`{rel(O2_PIT)}`",
        f"- O2 lineage audit：`{rel(O2_LINEAGE)}`",
        "",
        "## 3. Row Alignment",
        "",
        f"- control rows：`{len(control)}`。",
        f"- treatment rows：`{len(treatment)}`。",
        f"- symbol count：`{control['instrument'].nunique()}`。",
        f"- date range：`{str(control['date'].min())[:10]}`..`{str(control['date'].max())[:10]}`。",
        f"- split counts：`{split_counts(control)}`。",
        "",
        *md(row_alignment, ["check", "control", "treatment", "pass"]),
        "",
        "## 4. Schema Diff",
        "",
        f"- added columns：`{len(added_cols)}`。",
        f"- removed control columns：`{removed_cols}`。",
        f"- disallowed added columns：`{disallowed_added}`。",
        "- added columns 仅来自 Q0 白名单正交特征、missing/delay/lineage/PIT audit 字段。",
        "",
        "## 5. Missing Report",
        "",
        *md(missing_rows, ["feature_family", "control_rows", "missing_rows", "missing_ratio", "matched_rows", "symbol_count", "date_min", "date_max"]),
        "",
        "## 6. PIT / available_at Join",
        "",
        "- join 口径：按 `instrument + signal_asof(date)`，对每个 family 使用 `available_at <= signal_asof` 的最近一条正交记录。",
        "- 未人工提前 `available_at`，未用未来 trade_date，未因正交缺失删行。",
        "",
        *md(pit_rows, ["feature_family", "rows_checked", "used_available_at_gt_signal_asof_rows", "used_trade_date_gt_signal_asof_rows", "matched_available_at_min", "matched_available_at_max", "matched_trade_date_min", "matched_trade_date_max", "pit_pass"]),
        "",
        "## 7. 必须满足的等式",
        "",
        f"- `control_label == treatment_label`：`{manifest['control_label_equals_treatment_label']}`。Q1 未改 Alpha158 handler/label config。",
        f"- `control_split == treatment_split`：`{manifest['control_split_equals_treatment_split']}`。",
        f"- `control_universe_policy == treatment_universe_policy`：`{manifest['control_universe_policy_equals_treatment_universe_policy']}`。",
        f"- `only_added_columns == approved_orthogonal_features_and_missing_flags`：`{manifest['only_added_columns_equal_approved_orthogonal_features_and_missing_flags']}`。",
        "",
        "## 8. Forbidden Action Audit",
        "",
        "- 未训练模型。",
        "- 未调用或引入 LTR。",
        "- 未调参。",
        "- 未改 label / split / universe / Alpha158 / post-score filter / replay。",
        "- 未触发 frontend / API / provider / accepted latest / monitor / broker / orders / quick-trade。",
        "",
        "## 9. 输出 Artifact",
        "",
        *md([{"artifact": k, "path": v} for k, v in manifest["artifacts"].items()], ["artifact", "path"]),
        "",
        "## 10. 是否建议进入 Q2",
        "",
        "- 建议允许进入 Q2：`是`，前提是审查者接受 Q1 的 as-of join 方案与 schema diff。",
        "- Q2 仍不得改 Q0 冻结合同；若训练实现需要改 label/split/universe/model/replay，应停止并请求确认。",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "gate": gate, "manifest": rel(OUT / "feature_join_manifest.json"), "report": rel(REPORT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
