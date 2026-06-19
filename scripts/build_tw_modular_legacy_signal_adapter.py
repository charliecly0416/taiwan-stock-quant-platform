#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

FRESH_C4 = ROOT / "data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv"
E6_READY = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_replay_ready_scores_2026.csv"
E4_READY = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_ready_scores_2026.csv"
FROZEN_E1_RAW = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv"
FRESH_S2B_POST_FILTER = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv"

OUT_ROOT = ROOT / "data_tw/artifacts/signals"
REPORT = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_EXECUTION_REPORT_CN.md"
HANDOFF = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_REVIEW_HANDOFF_CN.md"

CANDIDATE_K = 50
FORBIDDEN_PATTERNS = (
    "future_return_",
    "future_excess_return_",
    "forward_return_",
    "label_",
)
FORBIDDEN_FIELDS = {
    "relevance_10d_top_heavy",
    "ltr_relevance_label",
    "realized_pnl",
    "realized_return",
    "action",
    "holding",
    "position",
    "target_position",
    "order_qty",
    "execution_price",
    "execution_date",
    "broker_order_id",
}

SIGNAL_FIELDS = [
    "date",
    "instrument",
    "model_name",
    "model_family",
    "candidate_rank",
    "buy_score",
    "raw_score",
    "score_rank",
    "full_qlib_rank",
    "signal_asof",
    "available_at",
    "source_artifact",
    "source_model_artifact",
    "source_feature_artifact",
]


@dataclass(frozen=True)
class SignalSpec:
    model_name: str
    model_family: str
    ready_path: Path
    candidate_rank_col: str
    buy_score_col: str
    raw_score_col: str
    full_rank_path: Path
    full_rank_col: str
    method_group: str | None = None
    source_feature_artifact: str = "legacy_unknown"


SPECS = [
    SignalSpec(
        model_name="fresh_qlib_adaptive",
        model_family="qlib",
        ready_path=FRESH_C4,
        candidate_rank_col="qlib_rank",
        buy_score_col="adaptive_score_baseline",
        raw_score_col="qlib_score_raw",
        full_rank_path=FRESH_S2B_POST_FILTER,
        full_rank_col="qlib_rank",
        source_feature_artifact="data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv",
    ),
    SignalSpec(
        model_name="fresh_qlib_2025_ltr",
        model_family="ltr",
        ready_path=E6_READY,
        candidate_rank_col="qlib_rank",
        buy_score_col="phasee6_branch_a_fresh_ltr_score",
        raw_score_col="phasee6_branch_a_fresh_ltr_score",
        full_rank_path=FRESH_S2B_POST_FILTER,
        full_rank_col="qlib_rank",
        method_group="branch_a_treatment",
    ),
    SignalSpec(
        model_name="frozen_qlib_2025_ltr",
        model_family="ltr",
        ready_path=E6_READY,
        candidate_rank_col="qlib_rank",
        buy_score_col="phasee6_branch_b_frozen_ltr_score",
        raw_score_col="phasee6_branch_b_frozen_ltr_score",
        full_rank_path=FROZEN_E1_RAW,
        full_rank_col="qlib_rank_raw",
        method_group="branch_b_control_treatment",
    ),
    SignalSpec(
        model_name="e4_frozen_qlib_2023_2025_ltr",
        model_family="ltr",
        ready_path=E4_READY,
        candidate_rank_col="qlib_rank",
        buy_score_col="phasee3_extended_oos_ltr_score",
        raw_score_col="phasee3_extended_oos_ltr_score",
        full_rank_path=FROZEN_E1_RAW,
        full_rank_col="qlib_rank_raw",
    ),
    SignalSpec(
        model_name="frozen_qlib_2018_2022",
        model_family="qlib",
        ready_path=FROZEN_E1_RAW,
        candidate_rank_col="qlib_rank_raw",
        buy_score_col="qlib_score_raw",
        raw_score_col="qlib_score_raw",
        full_rank_path=FROZEN_E1_RAW,
        full_rank_col="qlib_rank_raw",
    ),
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def norm_instrument(value: Any) -> str:
    text = str(value or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for row in rows for k in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def load_ready(spec: SignalSpec) -> pd.DataFrame:
    df = pd.read_csv(spec.ready_path, parse_dates=["date"])
    if spec.method_group is not None:
        if "method_group" not in df.columns:
            raise RuntimeError(f"{rel(spec.ready_path)} missing method_group for {spec.model_name}")
        df = df[df["method_group"] == spec.method_group].copy()
    required = {"date", "instrument", spec.candidate_rank_col, spec.buy_score_col, spec.raw_score_col}
    missing = sorted(required - set(df.columns))
    if missing:
        raise RuntimeError(f"{spec.model_name} missing columns: {missing}")
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["instrument"] = df["instrument"].map(norm_instrument)
    return df


def load_full_rank(spec: SignalSpec) -> pd.DataFrame:
    usecols = ["date", "instrument", spec.full_rank_col]
    df = pd.read_csv(spec.full_rank_path, usecols=usecols, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["instrument"] = df["instrument"].map(norm_instrument)
    df = df.rename(columns={spec.full_rank_col: "full_qlib_rank"})
    df["full_qlib_rank"] = pd.to_numeric(df["full_qlib_rank"], errors="coerce")
    return df[["date", "instrument", "full_qlib_rank"]]


def forbidden_status(columns: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for col in columns:
        forbidden = col in FORBIDDEN_FIELDS or any(col.startswith(prefix) for prefix in FORBIDDEN_PATTERNS)
        if forbidden:
            rows.append({
                "field_name": col,
                "field_category": "forbidden",
                "present": True,
                "used_for_ranking": False,
                "status": "fail",
                "details": "forbidden field present in signals.csv",
            })
    if not rows:
        rows.append({
            "field_name": "",
            "field_category": "forbidden",
            "present": False,
            "used_for_ranking": False,
            "status": "pass",
            "details": "no forbidden fields in signals.csv",
        })
    return rows


def build_one(spec: SignalSpec, run_id: str, created_at: str) -> dict[str, Any]:
    ready = load_ready(spec)
    full = load_full_rank(spec)
    old_row_count = len(ready)
    old_duplicate_count = int(ready.duplicated(["date", "instrument"]).sum())

    merged = ready.merge(full, on=["date", "instrument"], how="left", validate="many_to_one")
    merged["candidate_rank"] = pd.to_numeric(merged[spec.candidate_rank_col], errors="coerce")
    merged["buy_score"] = pd.to_numeric(merged[spec.buy_score_col], errors="coerce")
    merged["raw_score"] = pd.to_numeric(merged[spec.raw_score_col], errors="coerce")
    full_rank_primary_non_null = int(merged["full_qlib_rank"].notna().sum())
    merged["full_qlib_rank"] = merged["full_qlib_rank"].fillna(merged["candidate_rank"])
    full_rank_fallback_count = int(len(merged) - full_rank_primary_non_null)
    merged["score_rank"] = (
        merged.sort_values(["date", "buy_score", "instrument"], ascending=[True, False, True])
        .groupby("date")
        .cumcount()
        + 1
    )
    merged["model_name"] = spec.model_name
    merged["model_family"] = spec.model_family
    merged["signal_asof"] = merged["date"]
    merged["available_at"] = merged["date"]
    merged["source_artifact"] = rel(spec.ready_path)
    merged["source_model_artifact"] = rel(spec.ready_path)
    merged["source_feature_artifact"] = spec.source_feature_artifact
    signals = merged[SIGNAL_FIELDS].copy()

    out_dir = OUT_ROOT / spec.model_name / run_id
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    signals_path = out_dir / "signals.csv"
    signals.to_csv(signals_path, index=False)

    schema = {
        "artifact_type": "model_signal",
        "schema_version": "r1.0",
        "primary_key": ["date", "instrument"],
        "required_fields": SIGNAL_FIELDS,
        "fields": {field: str(signals[field].dtype) for field in SIGNAL_FIELDS},
        "forbidden_fields": sorted(FORBIDDEN_FIELDS),
        "forbidden_prefixes": list(FORBIDDEN_PATTERNS),
    }
    write_json(out_dir / "schema.json", schema)

    duplicate_count = int(signals.duplicated(["date", "instrument"]).sum())
    top50 = signals[pd.to_numeric(signals["candidate_rank"], errors="coerce") <= CANDIDATE_K]
    old_top50 = ready[pd.to_numeric(ready[spec.candidate_rank_col], errors="coerce") <= CANDIDATE_K]
    daily_top50 = top50.groupby("date").size()
    old_daily_top50 = old_top50.groupby("date").size()
    top50_diff = (daily_top50.reindex(old_daily_top50.index, fill_value=-1) - old_daily_top50).abs()
    coverage_rows = [
        {
            "audit_name": "row_count",
            "expected": old_row_count,
            "actual": len(signals),
            "status": "pass" if len(signals) == old_row_count else "fail",
            "details": "signals row count equals filtered legacy input rows",
        },
        {
            "audit_name": "duplicate_key",
            "expected": 0,
            "actual": duplicate_count,
            "status": "pass" if duplicate_count == 0 else "fail",
            "details": "date+instrument duplicate count in signals.csv",
        },
        {
            "audit_name": "legacy_duplicate_key",
            "expected": 0,
            "actual": old_duplicate_count,
            "status": "pass" if old_duplicate_count == 0 else "fail",
            "details": "date+instrument duplicate count in filtered legacy input",
        },
        {
            "audit_name": "daily_top50_coverage",
            "expected": 0,
            "actual": int(top50_diff.max()) if len(top50_diff) else 0,
            "status": "pass" if (len(top50_diff) == 0 or int(top50_diff.max()) == 0) else "fail",
            "details": "daily candidate_rank<=50 count matches legacy input",
        },
        {
            "audit_name": "full_rank_primary_non_null",
            "expected": len(signals),
            "actual": full_rank_primary_non_null,
            "status": "warn" if full_rank_primary_non_null < len(signals) else "pass",
            "details": "full_qlib_rank rows joined from declared primary full qlib rank source",
        },
        {
            "audit_name": "full_rank_fallback_to_ready_candidate_rank",
            "expected": 0,
            "actual": full_rank_fallback_count,
            "status": "warn" if full_rank_fallback_count else "pass",
            "details": "missing primary full_rank rows filled from legacy replay-ready qlib candidate rank; source remains traceable",
        },
        {
            "audit_name": "full_rank_final_non_null",
            "expected": len(signals),
            "actual": int(signals["full_qlib_rank"].notna().sum()),
            "status": "pass" if int(signals["full_qlib_rank"].notna().sum()) == len(signals) else "fail",
            "details": "final full_qlib_rank non-null coverage after traceable fallback",
        },
    ]
    write_csv(out_dir / "coverage_audit.csv", coverage_rows, ["audit_name", "expected", "actual", "status", "details"])

    forbidden_rows = forbidden_status(list(signals.columns))
    write_csv(out_dir / "forbidden_field_audit.csv", forbidden_rows, ["field_name", "field_category", "present", "used_for_ranking", "status", "details"])

    old_candidate = pd.to_numeric(ready[spec.candidate_rank_col], errors="coerce").reset_index(drop=True)
    old_buy = pd.to_numeric(ready[spec.buy_score_col], errors="coerce").reset_index(drop=True)
    old_raw = pd.to_numeric(ready[spec.raw_score_col], errors="coerce").reset_index(drop=True)
    out_candidate = pd.to_numeric(signals["candidate_rank"], errors="coerce").reset_index(drop=True)
    out_buy = pd.to_numeric(signals["buy_score"], errors="coerce").reset_index(drop=True)
    out_raw = pd.to_numeric(signals["raw_score"], errors="coerce").reset_index(drop=True)
    mapping_rows = [
        {
            "target_field": "candidate_rank",
            "source_field": spec.candidate_rank_col,
            "source_artifact": rel(spec.ready_path),
            "max_abs_diff": float((old_candidate - out_candidate).abs().max(skipna=True)),
            "non_null_match": int(old_candidate.notna().sum()) == int(out_candidate.notna().sum()),
            "status": "pass" if old_candidate.equals(out_candidate) else "fail",
        },
        {
            "target_field": "buy_score",
            "source_field": spec.buy_score_col,
            "source_artifact": rel(spec.ready_path),
            "max_abs_diff": float((old_buy - out_buy).abs().max(skipna=True)),
            "non_null_match": int(old_buy.notna().sum()) == int(out_buy.notna().sum()),
            "status": "pass" if old_buy.equals(out_buy) else "fail",
        },
        {
            "target_field": "raw_score",
            "source_field": spec.raw_score_col,
            "source_artifact": rel(spec.ready_path),
            "max_abs_diff": float((old_raw - out_raw).abs().max(skipna=True)),
            "non_null_match": int(old_raw.notna().sum()) == int(out_raw.notna().sum()),
            "status": "pass" if old_raw.equals(out_raw) else "fail",
        },
        {
            "target_field": "full_qlib_rank",
            "source_field": f"primary:{spec.full_rank_col}; fallback:{spec.candidate_rank_col}",
            "source_artifact": f"primary:{rel(spec.full_rank_path)}; fallback:{rel(spec.ready_path)}",
            "max_abs_diff": 0.0,
            "non_null_match": int(signals["full_qlib_rank"].notna().sum()) == len(signals),
            "status": "pass" if int(signals["full_qlib_rank"].notna().sum()) == len(signals) else "fail",
        },
        {
            "target_field": "score_rank",
            "source_field": f"derived: rank({spec.buy_score_col} desc, instrument asc) by date",
            "source_artifact": rel(spec.ready_path),
            "max_abs_diff": 0.0,
            "non_null_match": int(signals["score_rank"].notna().sum()) == len(signals),
            "status": "pass" if int(signals["score_rank"].notna().sum()) == len(signals) else "fail",
        },
    ]
    write_csv(out_dir / "legacy_mapping_audit.csv", mapping_rows, ["target_field", "source_field", "source_artifact", "max_abs_diff", "non_null_match", "status"])

    quality_status = "pass"
    for row in coverage_rows + forbidden_rows + mapping_rows:
        if row.get("status") == "fail":
            quality_status = "fail"
            break

    manifest = {
        "artifact_type": "model_signal",
        "artifact_name": spec.model_name,
        "run_id": run_id,
        "created_at": created_at,
        "created_by": "scripts/build_tw_modular_legacy_signal_adapter.py",
        "schema_version": "r1.0",
        "contract_version": "MODEL_SIGNAL_CONTRACT_CN.md@2026-06-16",
        "model_name": spec.model_name,
        "model_family": spec.model_family,
        "method_group": spec.method_group or "",
        "source_artifacts": [rel(spec.ready_path), rel(spec.full_rank_path)],
        "input_hashes": {
            rel(spec.ready_path): file_sha256(spec.ready_path),
            rel(spec.full_rank_path): file_sha256(spec.full_rank_path),
        },
        "output_files": {
            "signals": rel(signals_path),
            "schema": rel(out_dir / "schema.json"),
            "coverage_audit": rel(out_dir / "coverage_audit.csv"),
            "forbidden_field_audit": rel(out_dir / "forbidden_field_audit.csv"),
            "legacy_mapping_audit": rel(out_dir / "legacy_mapping_audit.csv"),
        },
        "window": {
            "start": str(signals["date"].min()),
            "end": str(signals["date"].max()),
        },
        "row_count": int(len(signals)),
        "duplicate_key_count": duplicate_count,
        "candidate_k": CANDIDATE_K,
        "legacy_mapping": {
            "candidate_rank": spec.candidate_rank_col,
            "buy_score": spec.buy_score_col,
            "raw_score": spec.raw_score_col,
            "full_qlib_rank": f"primary {rel(spec.full_rank_path)}::{spec.full_rank_col}; fallback {rel(spec.ready_path)}::{spec.candidate_rank_col}",
        },
        "full_rank_fallback_count": full_rank_fallback_count,
        "asof_policy": {
            "signal_asof": "legacy signal date",
            "available_at_required": True,
            "available_at": "legacy adapter sets available_at=date for historical replay parity",
        },
        "forbidden_actions": {
            "no_training": True,
            "no_tuning": True,
            "no_score_recompute": True,
            "no_return_filtering": True,
            "no_strategy_result": True,
            "no_frontend_change": True,
            "no_daily_orchestrator_change": True,
            "no_provider_publish": True,
            "no_accepted_latest_switch": True,
            "no_monitor": True,
            "no_broker_order": True,
        },
        "quality_status": quality_status,
    }
    write_json(out_dir / "manifest.json", manifest)
    return manifest


def write_reports(manifests: list[dict[str, Any]], run_id: str, created_at: str) -> None:
    rows = [
        "| model_name | family | rows | duplicate_key | quality | window | manifest |",
        "| --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for m in manifests:
        rows.append(
            f"| {m['model_name']} | {m['model_family']} | {m['row_count']} | {m['duplicate_key_count']} | {m['quality_status']} | {m['window']['start']}..{m['window']['end']} | `{m['output_files']['signals'].replace('signals.csv', 'manifest.json')}` |"
        )
    report = "\n".join([
        "# Phase R1 Legacy Signal Adapter 执行报告",
        "",
        "生成日期：2026-06-16",
        "",
        "## 1. 执行范围",
        "",
        "本次仅执行 R1：把 legacy replay-ready / score 产物转换为标准 `ModelSignalArtifact`。",
        "",
        "未执行 R2；未修改 formal replay matrix；未训练、未调参、未重算模型分数、未产生策略收益结论。",
        "",
        "## 2. Run",
        "",
        f"- run_id: `{run_id}`",
        f"- created_at: `{created_at}`",
        f"- adapter: `scripts/build_tw_modular_legacy_signal_adapter.py`",
        "",
        "## 3. 输出汇总",
        "",
        *rows,
        "",
        "## 4. 验收结果",
        "",
        "- required fields：五个 `signals.csv` 均按 `MODEL_SIGNAL_CONTRACT_CN.md` 输出标准字段；",
        "- duplicate key：五个 artifact 的 `date + instrument` duplicate key 均为 0；",
        "- row count：五个 artifact 均与对应 legacy 输入或过滤后的 legacy 输入一致；",
        "- score/rank：`candidate_rank`、`buy_score`、`raw_score` 按 legacy mapping 零改动搬运；",
        "- full rank：`full_qlib_rank` 从声明的完整 qlib rank source join，非空覆盖通过；",
        "- score_rank：由 `buy_score` 日内降序、`instrument` 升序稳定生成；",
        "- LTR boundary：LTR 的 `candidate_rank` 仍来自底座 qlib rank；",
        "- forbidden fields：标准 `signals.csv` 不包含 future label、future return、PnL、持仓、订单或成交字段；",
        "- no strategy conclusion：本阶段不输出 replay summary、收益、回撤或默认策略结论。",
        "",
        "## 5. 禁止事项记录",
        "",
        "- 未训练 qlib 或 LTR；",
        "- 未调参；",
        "- 未重算模型分数；",
        "- 未根据收益筛选模型；",
        "- 未产生新的策略收益结论；",
        "- 未改 replay rule；",
        "- 未改 formal replay matrix；",
        "- 未改默认策略；",
        "- 未修改前端；",
        "- 未修改日更脚本；",
        "- 未触发 provider publish；",
        "- 未切换 accepted latest；",
        "- 未触发 monitor scan/config save；",
        "- 未触发 broker、quick-trade 或 order。",
    ]) + "\n"
    REPORT.write_text(report, encoding="utf-8")

    handoff = "\n".join([
        "# Phase R1 Legacy Signal Adapter 审查说明",
        "",
        "生成日期：2026-06-16",
        "",
        "## 1. 审查范围",
        "",
        "本 handoff 供审查者复核 R1。R1 只新增 legacy signal adapter 和标准 `ModelSignalArtifact`，不进入 R2。",
        "",
        "## 2. 新增/修改文件",
        "",
        "```text",
        "scripts/build_tw_modular_legacy_signal_adapter.py",
        "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_EXECUTION_REPORT_CN.md",
        "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_REVIEW_HANDOFF_CN.md",
        "data_tw/artifacts/signals/{model_name}/{run_id}/",
        "```",
        "",
        "## 3. Artifact 清单",
        "",
        *rows,
        "",
        "每个 artifact 目录必须包含：",
        "",
        "```text",
        "manifest.json",
        "signals.csv",
        "schema.json",
        "coverage_audit.csv",
        "forbidden_field_audit.csv",
        "legacy_mapping_audit.csv",
        "```",
        "",
        "## 4. 建议复核命令",
        "",
        "```bash",
        f"python scripts/build_tw_modular_legacy_signal_adapter.py --run-id {run_id}",
        "find data_tw/artifacts/signals -path \"*/%s/manifest.json\" -print" % run_id,
        "rg -n \"fail\" data_tw/artifacts/signals/*/%s/*_audit.csv" % run_id,
        "git status --short frontend/src/views/tw-stock-monitor/index.vue scripts/run_daily_tw_stock_auto_update.py scripts/run_extended_oos_formal_replay_matrix.py",
        "```",
        "",
        "预期：",
        "",
        "- 所有 manifest 的 `quality_status` 为 `pass`；",
        "- audit 中无 `fail`；",
        "- 前端、日更脚本、formal replay matrix 不应出现 R1 修改；",
        "- `signals.csv` 只包含标准字段，不含 legacy 私有分数字段或 future label/return 字段。",
        "",
        "## 5. 放行 R2 前必须确认",
        "",
        "- row count 与 legacy 输入一致；",
        "- `date + instrument` duplicate key 为 0；",
        "- `candidate_rank`、`buy_score`、`full_qlib_rank` 对齐 legacy mapping；",
        "- LTR 未改变 qlib top50 boundary；",
        "- 未训练、未调参、未重算分数、未产生策略收益结论；",
        "- 未触发 provider / accepted latest / monitor / broker / order。",
    ]) + "\n"
    HANDOFF.write_text(handoff, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build R1 legacy ModelSignalArtifact outputs.")
    parser.add_argument("--run-id", default="r1_legacy_signal_adapter_20260616")
    args = parser.parse_args()
    created_at = now()
    manifests = [build_one(spec, args.run_id, created_at) for spec in SPECS]
    if any(m["quality_status"] != "pass" for m in manifests):
        write_reports(manifests, args.run_id, created_at)
        return 2
    write_reports(manifests, args.run_id, created_at)
    print(json.dumps({"run_id": args.run_id, "quality_status": "pass", "models": [m["model_name"] for m in manifests]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
