#!/usr/bin/env python3
"""Phase F0 readonly audit for TW fundamental PIT mainline.

Reads local docs/scripts/data evidence only. Does not use network, token,
download data, write raw archives, build samples, or train models.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_tw/experiments/decision_fundamental"
DOC_DIR = ROOT / "docs/tw_decision_model_fundamental"

INVENTORY_PATH = OUT_DIR / "phasef0_data_source_inventory.csv"
SCHEMA_PATH = OUT_DIR / "phasef0_pit_schema_proposal.json"
SUMMARY_PATH = OUT_DIR / "phasef0_feasibility_summary.json"
REPORT_PATH = DOC_DIR / "PHASEF0_EXECUTION_REPORT_CN.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def evidence(path: str) -> str:
    return path if exists(path) else f"{path} (not present in this workspace)"


def inventory_rows() -> list[dict[str, Any]]:
    rows = [
        {
            "candidate_source": "FinMind",
            "dataset_or_table": "TaiwanStockMonthRevenue",
            "local_evidence_path": evidence("docs/TAIWAN_STOCK_PHASE_CHECKPOINT_CN.md"),
            "source_type": "doc_claim_existing_backend_script",
            "has_symbol": True,
            "has_source_period": True,
            "has_announcement_date": False,
            "has_available_at": False,
            "has_revenue": True,
            "has_yoy": True,
            "has_mom": True,
            "has_raw_snapshot_id": False,
            "has_data_source": True,
            "pit_join_safe": False,
            "known_risk": "Checkpoint mentions monthly revenue archive script and smoke rows, but Phase F0 local evidence does not prove row-level announcement_date or available_at.",
            "phasef0_status": "defer_missing_announcement_date",
            "notes": "May be a future F0B candidate only after authorized network/token POC verifies dataset fields and immutable raw snapshots.",
        },
        {
            "candidate_source": "FinMind local daily auto update logs",
            "dataset_or_table": "monthly_revenue summary",
            "local_evidence_path": evidence("data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260611_20260611T103001Z/finmind_stdout.txt"),
            "source_type": "local_ops_log",
            "has_symbol": False,
            "has_source_period": False,
            "has_announcement_date": False,
            "has_available_at": False,
            "has_revenue": False,
            "has_yoy": False,
            "has_mom": False,
            "has_raw_snapshot_id": False,
            "has_data_source": True,
            "pit_join_safe": False,
            "known_risk": "Latest inspected auto update used --no-monthly-revenue and stdout summary shows monthly_revenue count=0.",
            "phasef0_status": "defer_no_local_evidence",
            "notes": "Useful negative evidence only; no local monthly revenue rows available for PIT validation.",
        },
        {
            "candidate_source": "Legacy decision_model Phase0 audit",
            "dataset_or_table": "FinMind monthly_revenue_yoy_mom",
            "local_evidence_path": evidence("data_tw/experiments/decision_model/phase0_feature_coverage.csv"),
            "source_type": "local_prior_audit_artifact",
            "has_symbol": False,
            "has_source_period": False,
            "has_announcement_date": False,
            "has_available_at": False,
            "has_revenue": False,
            "has_yoy": False,
            "has_mom": False,
            "has_raw_snapshot_id": False,
            "has_data_source": True,
            "pit_join_safe": False,
            "known_risk": "Prior audit records monthly_revenue_yoy_mom coverage=0 and point_in_time_safe=false.",
            "phasef0_status": "defer_no_local_evidence",
            "notes": "Confirms previous local conclusion: no archived rows and no announcement_date/available_at proof.",
        },
        {
            "candidate_source": "Legacy decision_model PIT rules",
            "dataset_or_table": "financial/monthly revenue data",
            "local_evidence_path": evidence("data_tw/experiments/decision_model/phase0_point_in_time_rules.md"),
            "source_type": "local_prior_pit_policy",
            "has_symbol": False,
            "has_source_period": False,
            "has_announcement_date": False,
            "has_available_at": False,
            "has_revenue": False,
            "has_yoy": False,
            "has_mom": False,
            "has_raw_snapshot_id": False,
            "has_data_source": False,
            "pit_join_safe": False,
            "known_risk": "Prior PIT policy rejects period-only joins and defers FinMind monthly revenue until row-level available_at/announcement_date exists.",
            "phasef0_status": "defer_period_only",
            "notes": "Policy evidence, not data source evidence.",
        },
        {
            "candidate_source": "Orthogonal Phase0E raw archive script",
            "dataset_or_table": "monthly_revenue placeholder",
            "local_evidence_path": evidence("scripts/build_tw_decision_orthogonal_phase0e_raw_archive.py"),
            "source_type": "local_script_negative_evidence",
            "has_symbol": False,
            "has_source_period": False,
            "has_announcement_date": False,
            "has_available_at": False,
            "has_revenue": False,
            "has_yoy": False,
            "has_mom": False,
            "has_raw_snapshot_id": False,
            "has_data_source": False,
            "pit_join_safe": False,
            "known_risk": "Script explicitly marked monthly_revenue as deferred_not_authorized in Phase0E.",
            "phasef0_status": "defer_no_local_evidence",
            "notes": "No reusable monthly revenue implementation in this script.",
        },
        {
            "candidate_source": "Potential official disclosure source",
            "dataset_or_table": "MOPS/TWSE monthly revenue disclosure page or API",
            "local_evidence_path": "No local evidence; network not authorized in Phase F0",
            "source_type": "potential_external_source",
            "has_symbol": False,
            "has_source_period": False,
            "has_announcement_date": False,
            "has_available_at": False,
            "has_revenue": False,
            "has_yoy": False,
            "has_mom": False,
            "has_raw_snapshot_id": False,
            "has_data_source": False,
            "pit_join_safe": False,
            "known_risk": "Could be the right PIT source if it exposes announcement timestamps, but no local evidence and no network authorization.",
            "phasef0_status": "defer_no_local_evidence",
            "notes": "Would require separate user/reviewer authorization as a new F0B data-source POC.",
        },
        {
            "candidate_source": "FinMind valuation",
            "dataset_or_table": "TaiwanStockPER",
            "local_evidence_path": evidence("data_tw/experiments/decision_model/phase0_feature_coverage.csv"),
            "source_type": "local_prior_audit_artifact",
            "has_symbol": False,
            "has_source_period": False,
            "has_announcement_date": False,
            "has_available_at": False,
            "has_revenue": False,
            "has_yoy": False,
            "has_mom": False,
            "has_raw_snapshot_id": False,
            "has_data_source": True,
            "pit_join_safe": False,
            "known_risk": "Valuation is out of Phase F0 priority and prior audit does not prove date/available_at semantics.",
            "phasef0_status": "out_of_scope",
            "notes": "Do not include in F0B unless reviewer explicitly expands beyond monthly revenue.",
        },
    ]
    for row in rows:
        for key in [
            "has_symbol",
            "has_source_period",
            "has_announcement_date",
            "has_available_at",
            "has_revenue",
            "has_yoy",
            "has_mom",
            "has_raw_snapshot_id",
            "has_data_source",
            "pit_join_safe",
        ]:
            row[key] = str(bool(row[key])).lower()
    return rows


def schema_proposal() -> dict[str, Any]:
    return {
        "raw_archive_schema": {
            "symbol": "Taiwan stock id, string",
            "source_period": "Revenue month, e.g. YYYY-MM",
            "announcement_date": "Official disclosure date from source, required for PIT",
            "available_at": "First trading asof at which this row may be used; must be >= announcement_date and adjusted to next valid trading day if announcement happens after market close or on a non-trading day",
            "revenue": "Raw monthly revenue value",
            "yoy": "Year-over-year revenue growth, raw provider value or reproducible derived value",
            "mom": "Month-over-month revenue growth, raw provider value or reproducible derived value",
            "data_source": "Provider/source name, e.g. FinMind or official disclosure source",
            "raw_snapshot_id": "Immutable fetch snapshot id",
            "ingested_at": "UTC ingestion timestamp",
            "source_url_or_dataset": "Endpoint, dataset name, or official URL",
            "revision_flag": "initial, revised, duplicate, or late_revision",
            "raw_payload_hash": "Hash of raw source row/payload for immutability audit",
        },
        "normalized_pit_schema": {
            "symbol": "same as raw",
            "source_period": "same as raw",
            "announcement_date": "same as raw, required",
            "available_at": "same as raw, required",
            "revenue": "normalized numeric value",
            "yoy": "normalized numeric value",
            "mom": "normalized numeric value",
            "data_source": "same as raw",
            "raw_snapshot_id": "same as raw",
            "ingested_at": "same as raw",
            "source_url_or_dataset": "same as raw",
            "revision_flag": "same as raw",
            "days_since_last_report": "asof - available_at in calendar days or trading days, computed during asof join",
            "quality_flags": "missing_announcement_date, missing_available_at, duplicate_period, late_revision, period_only_risk",
        },
        "visibility_rule": "A monthly revenue row is visible only when announcement_date and available_at are both present and available_at <= asof.",
        "join_rule": "For each symbol/asof, select the latest source_period whose available_at <= asof; preserve source_period, announcement_date, available_at, data_source, raw_snapshot_id, and days_since_last_report.",
        "forbidden_join_rule": "Never join by source_period month directly to same-month trading dates; never assume month start, month end, or local ingestion time is historical availability.",
        "snapshot_rule": "Every F0B pull must write raw immutable JSON/CSV snapshot first with raw_snapshot_id, ingested_at, provider dataset, request params, and payload hash before any normalization.",
        "dedup_rule": "Deduplicate by symbol, source_period, announcement_date, data_source, and raw payload hash; if multiple rows exist, keep all in raw archive and choose normalized latest valid row by announced/available sequence while flagging duplicates.",
        "late_revision_rule": "If a later pull revises a prior source_period, keep both snapshots; normalized PIT may use the revised row only from its own announcement_date/available_at forward.",
        "days_since_last_report_rule": "At sample construction time, days_since_last_report = asof - selected row available_at; rows with no selected PIT-valid report remain missing and must not be backfilled from future periods.",
        "f0b_required_authorizations": {
            "network": True,
            "token": True,
            "new_monthly_revenue_script": True,
            "write_independent_raw_archive": True,
            "provider_write": False,
            "accepted_latest_switching": False,
            "model_training": False,
            "frontend_api": False,
            "trading_or_order": False,
        },
    }


def summary_payload(rows: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    pit_valid = [r for r in rows if r["pit_join_safe"] == "true"]
    return {
        "phase": "Phase F0",
        "generated_at": generated_at,
        "network_used": False,
        "token_used": False,
        "downloaded_data": False,
        "raw_archive_written": False,
        "model_training": False,
        "provider_write": False,
        "accepted_latest_switching": False,
        "frontend_api": False,
        "trading_or_order": False,
        "candidate_source_count": len(rows),
        "pit_valid_candidate_count": len(pit_valid),
        "requires_f0b_user_authorization": True,
        "recommended_gate": "request_user_authorization_for_f0b_poc",
        "gate_reason": "本地只读证据未证明任何月营收/基本面源具备 row-level announcement_date/available_at；但 FinMind monthly revenue 与官方披露源存在作为 F0B 受限 POC 的候选，需要用户授权联网/token/新增脚本/写独立 raw archive 后才能验证。不能进入 F1。",
        "open_questions": [
            "FinMind TaiwanStockMonthRevenue 实际响应是否包含可审计 announcement_date 或等价 disclosure date。",
            "若 FinMind 只有 source_period/revenue/yoy/mom，是否允许改查官方 MOPS/TWSE 披露源。",
            "F0B 是否授权联网、token、只读/独立 raw archive 写入和新增月营收 POC 脚本。",
            "F0B 范围是否限制为 2024-01-01 至 2026-06-11、qlib Top50/Top150 涉及股票、月营收优先。",
        ],
    }


def report_text(rows: list[dict[str, Any]], summary: dict[str, Any], generated_at: str) -> str:
    table = ["| candidate_source | dataset_or_table | has_announcement_date | has_available_at | pit_join_safe | phasef0_status | notes |", "|---|---|---|---|---|---|---|"]
    for row in rows:
        table.append(
            f"| {row['candidate_source']} | {row['dataset_or_table']} | {row['has_announcement_date']} | {row['has_available_at']} | {row['pit_join_safe']} | {row['phasef0_status']} | {row['notes']} |"
        )
    return f"""# Phase F0 执行报告

- 生成时间：`{generated_at}`
- 当前阶段目标：本地只读审计台股基本面/月营收 PIT 可行性，设计 raw archive / normalized PIT schema。
- 执行范围：只读读取 docs、scripts、data_tw/experiments、data_tw/ops 中的本地证据；未读取或写入 provider，未构建样本。
- 禁止范围执行情况：未联网、未使用 token、未下载数据、未调用 FinMind API、未调用 Scrapling、未新增真实数据源抓取、未写真实 raw archive、未构建 Phase F1 样本、未做单因子检验、未做规则 baseline、未训练模型、未前端/API、未 monitor、未交易路径。

## 1. 修改文件

- 新增 `scripts/audit_tw_decision_fundamental_phasef0.py`

## 2. 生成文件

- `data_tw/experiments/decision_fundamental/phasef0_data_source_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0_pit_schema_proposal.json`
- `data_tw/experiments/decision_fundamental/phasef0_feasibility_summary.json`
- `docs/tw_decision_model_fundamental/PHASEF0_EXECUTION_REPORT_CN.md`

## 3. 本地 Inventory 摘要

{chr(10).join(table)}

## 4. 每个候选源的 PIT 判断

- FinMind `TaiwanStockMonthRevenue`：本地文档说明曾有月营收脚本和 smoke 记录，但当前 Phase F0 只读证据没有 row-level `announcement_date` / `available_at`，不能进入 F1。
- daily auto update logs：最新检查到 `--no-monthly-revenue`，stdout summary 中 `monthly_revenue.count=0`，只能作为负面证据。
- legacy decision_model Phase0：`monthly_revenue_yoy_mom` coverage 为 0，且 `point_in_time_safe=false`。
- prior PIT policy：明确拒绝 period-only join，要求从 `available_at` 开始 forward fill 并保留 source metadata。
- orthogonal Phase0E script：月营收被标记为 `deferred_not_authorized`。
- potential official disclosure source：可能是可行方向，但当前没有本地证据，Phase F0 未授权联网验证。

## 5. 是否找到 announcement_date

未找到可用于月营收/基本面样本的本地 row-level `announcement_date` 证据。

## 6. 是否找到 available_at

未找到可用于月营收/基本面样本的本地 row-level `available_at` 证据。

## 7. Period-only Join 风险

存在明确风险。若只拿到 `source_period`、`revenue`、`yoy`、`mom`，不得把所属月份直接 join 到当月交易日；这会把事后披露的月营收提前到不可见日期。

## 8. Raw Archive Schema 草案摘要

- raw archive 必须先保存不可变快照：`symbol`、`source_period`、`announcement_date`、`available_at`、`revenue`、`yoy`、`mom`、`data_source`、`raw_snapshot_id`、`ingested_at`、`source_url_or_dataset`、`revision_flag`、`raw_payload_hash`。
- normalized PIT 只能使用同时具备 `announcement_date` 与 `available_at` 的行。
- join 规则：每个 symbol/asof 只选择 `available_at <= asof` 的最新 `source_period`。
- late revision 规则：修订值只能从其自身 `announcement_date` / `available_at` 之后可见，不能覆盖历史当时不可见样本。

## 9. F0B 授权需求

- F0B 是否需要联网：是。
- F0B 是否需要 token：是，若选择 FinMind。
- F0B 是否需要新增脚本：是，需要独立月营收 POC 脚本。
- F0B 是否需要写 raw archive：是，但只能写独立 `data_tw/experiments/decision_fundamental/phasef0b_*` raw archive，不得写 provider。

## 10. 覆盖率 / 缺失率

- candidate_source_count：`{summary['candidate_source_count']}`
- pit_valid_candidate_count：`{summary['pit_valid_candidate_count']}`
- 本地 PIT-valid 月营收行：`0`
- 本地月营收 row-level announcement_date 缺失率：无法逐行计算；当前可用本地行数为 0，PIT 可用性视为 0。

## 11. 安全边界检查

- network_used=false
- token_used=false
- downloaded_data=false
- raw_archive_written=false
- model_training=false
- provider_write=false
- accepted_latest_switching=false
- frontend_api=false
- trading_or_order=false

## 12. 推荐 Gate 与理由

- recommended_gate：`{summary['recommended_gate']}`
- gate_reason：{summary['gate_reason']}

注意：该 gate 只表示请求审查者/用户考虑授权 F0B POC；不得直接进入 F0B，更不得进入 F1。

## 13. 风险与待审查问题

- 若审查者认为 FinMind 月营收缺少公告日，则应停止 fundamental mainline 或改走官方披露源 proposal。
- 若 F0B 只验证到 period-only 字段，则必须 `stop_fundamental_mainline_no_pit_source`。
- F0B 需要明确范围、token 使用方式、raw archive 路径和禁止 provider/accepted latest/模型训练边界。
"""


def main() -> None:
    generated_at = utc_now()
    rows = inventory_rows()
    schema = schema_proposal()
    summary = summary_payload(rows, generated_at)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(INVENTORY_PATH, rows)
    SCHEMA_PATH.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(report_text(rows, summary, generated_at), encoding="utf-8")
    print(f"wrote {rel(INVENTORY_PATH)}")
    print(f"wrote {rel(SCHEMA_PATH)}")
    print(f"wrote {rel(SUMMARY_PATH)}")
    print(f"wrote {rel(REPORT_PATH)}")


if __name__ == "__main__":
    main()
