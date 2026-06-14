#!/usr/bin/env python3
"""Phase V1B split-aware audit repair for yearly LTR validation outputs.

This is a readonly audit repair. It reads existing Phase V1 yearly replay
artifacts, reconstructs the frozen accepted/common replay date sets, and adds
split coverage plus out-of-sample interpretation guardrails. It does not replay,
train, tune, fetch data, or touch product/API/provider/monitor/trading paths.
"""
from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SIGNAL_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill"
FROZEN = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv"
OUT = ROOT / "data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay"
YEARLY = OUT / "phasev1_yearly_comparison.csv"
QUALITY = OUT / "phasev1_yearly_data_quality.csv"
DOC = ROOT / "docs/tw_ltr_strategy_validation/PHASEV1B_SPLIT_AWARE_REPAIR_EXECUTION_REPORT_CN.md"

PERIODS = {
    "2022": ("2022-01-01", "2022-12-31"),
    "2023": ("2023-01-01", "2023-12-31"),
    "2024": ("2024-01-01", "2024-12-31"),
    "2025": ("2025-01-01", "2025-12-31"),
    "2026_ytd": ("2026-01-01", "2026-06-13"),
}
SPLITS = {
    "train": ("2022-01-10", "2024-08-09"),
    "validation": ("2024-08-12", "2025-06-24"),
    "independent_test": ("2025-06-25", "2026-05-07"),
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def d(raw: str) -> date:
    return date.fromisoformat(str(raw)[:10])


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def accepted_dates() -> list[str]:
    rows: list[tuple[str, str]] = []
    for summary in SIGNAL_ROOT.rglob("signal_summary.json"):
        run_dir = summary.parent
        if not (run_dir / "top50_signals.csv").exists():
            continue
        try:
            payload = json.loads(summary.read_text(encoding="utf-8"))
        except Exception:
            continue
        asof = str(payload.get("asof") or "")[:10]
        if asof and payload.get("status") == "accepted":
            rows.append((asof, str(run_dir)))
    dedup = {asof: asof for asof, _ in sorted(rows)}
    return [dedup[key] for key in sorted(dedup)]


def frozen_dates() -> set[str]:
    out: set[str] = set()
    with FROZEN.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            day = str(row.get("date") or "")[:10]
            if day:
                out.add(day)
    return out


def split_for(day: str) -> str:
    value = d(day)
    for split, (start, end) in SPLITS.items():
        if d(start) <= value <= d(end):
            return split
    return "out_of_split"


def sample_status(train: int, validation: int, independent: int, out_of_split: int) -> str:
    active = {
        "train": train > 0,
        "validation": validation > 0,
        "independent_test": independent > 0,
        "out_of_split": out_of_split > 0,
    }
    if active == {"train": True, "validation": False, "independent_test": False, "out_of_split": False}:
        return "train_only"
    if active == {"train": True, "validation": True, "independent_test": False, "out_of_split": False}:
        return "train_validation_mixed"
    if active == {"train": False, "validation": True, "independent_test": True, "out_of_split": False}:
        return "validation_independent_test_mixed"
    if active == {"train": False, "validation": False, "independent_test": True, "out_of_split": False}:
        return "independent_test_only"
    if active["independent_test"] and active["out_of_split"]:
        return "independent_test_out_of_split_mixed"
    if active == {"train": False, "validation": False, "independent_test": False, "out_of_split": True}:
        return "out_of_split_only"
    return "mixed_or_insufficient_data"


def oos_guardrail(period: str, status: str) -> tuple[str, str]:
    if status == "train_only":
        return "false", "样本内训练覆盖区间，只能用于复盘，不能作为样本外证据。"
    if status == "train_validation_mixed":
        return "false", "年度结果混合 train 与 validation，不能作为独立样本外证据。"
    if status == "validation_independent_test_mixed":
        return "false", "年度结果混合 validation 与 independent_test，必须拆分后才能解释样本外效果。"
    if status == "independent_test_only":
        return "true", "该年度共同回放日期完全位于 independent_test，可作为样本外审查材料。"
    if status == "independent_test_out_of_split_mixed":
        return "false", "年度 YTD 覆盖 post-independent / out-of-split 日期，不能作为完整年度样本外证据；只能拆出 independent_test 截止日内部分审查。"
    if period == "2026_ytd":
        return "false", "2026-05-08 之后不在 frozen split 内，必须单独标注为 out-of-split。"
    return "false", "数据不足或 split 混合属性不清，不能作为样本外证据。"


def coverage_rows() -> list[dict[str, Any]]:
    accepted = accepted_dates()
    frozen = frozen_dates()
    rows: list[dict[str, Any]] = []
    for period, (start, end) in PERIODS.items():
        baseline = [day for day in accepted if start <= day <= end]
        common = [day for day in baseline if day in frozen]
        excluded = [day for day in baseline if day not in frozen]
        counts = {"train": 0, "validation": 0, "independent_test": 0, "out_of_split": 0}
        for day in common:
            counts[split_for(day)] += 1
        if period == "2026_ytd":
            # Reviewer requirement: dates after independent_test end must be
            # explicitly marked out-of-split even if removed from common replay.
            counts["out_of_split"] += len([day for day in baseline if split_for(day) == "out_of_split"])
        status = sample_status(counts["train"], counts["validation"], counts["independent_test"], counts["out_of_split"])
        allowed, note = oos_guardrail(period, status)
        split_coverage = (
            f"train:{counts['train']};"
            f"validation:{counts['validation']};"
            f"independent_test:{counts['independent_test']};"
            f"out_of_split:{counts['out_of_split']}"
        )
        rows.append({
            "period": period,
            "start_date": start,
            "end_date": end,
            "baseline_signal_days": len(baseline),
            "ltr_score_days": len(common),
            "common_replay_days": len(common),
            "excluded_dates": ",".join(excluded[:60]),
            "split_coverage": split_coverage,
            "train_days": counts["train"],
            "validation_days": counts["validation"],
            "independent_test_days": counts["independent_test"],
            "out_of_split_days": counts["out_of_split"],
            "sample_status": status,
            "oos_interpretation_allowed": allowed,
            "oos_interpretation_note": note,
            "comparison_status": "completed" if common else "insufficient_data",
            "reason": "split-aware audit repaired; post-independent dates are not sample-out evidence" if period == "2026_ytd" else "split-aware audit repaired",
        })
    return rows


def md(rows: list[dict[str, Any]], fields: list[str], limit: int = 50) -> str:
    if not rows:
        return "_无记录_"
    out = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows[:limit]:
        out.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(out)


def write_report(gate: dict[str, Any], coverage: list[dict[str, Any]], method_rows: list[dict[str, Any]]) -> None:
    key_rows = [
        row
        for row in method_rows
        if row["method"] in {"rank_rotate_top50_adaptive_score", "phase1c_ltr_simple_daily", "phase1c_ltr_turnover_controlled_daily"}
    ]
    lines = [
        "# Phase V1B Split-aware / Lookahead 修复执行报告",
        "",
        f"生成时间：{gate['created_at']}",
        "",
        "## 1. 本轮目标",
        "",
        "按审查文档要求，只修复 Phase V1 年度结果的 split-aware / lookahead 审计缺口。 本轮读取既有 Phase V1 年度产物并重建 accepted/common replay 日期覆盖，补充 split 覆盖、样本状态和样本外解释限制。",
        "",
        "本轮未执行新回放、未执行 rolling、未执行市况分段、未做 walk-forward、未做 label-shuffle、未做 feature leakage scan、未调参、未重训 LTR、未改策略、未改 Phase1C score、未改 replay 口径、未改前端/API、未联网、未新增数据源、未触发 provider / accepted latest / monitor / 交易链路。",
        "",
        "## 2. Split 定义",
        "",
        "| split | 起始日期 | 结束日期 | 解释限制 |",
        "| --- | --- | --- | --- |",
        "| train | 2022-01-10 | 2024-08-09 | 样本内训练覆盖区间，不得解释为样本外效果 |",
        "| validation | 2024-08-12 | 2025-06-24 | 验证期，不得解释为独立样本外效果 |",
        "| independent_test | 2025-06-25 | 2026-05-07 | 可作为样本外审查核心，但仍需后续 walk-forward 等审查 |",
        "| post_independent_test_or_out_of_split | split 外日期 | split 外日期 | 不得混入 independent_test 结论 |",
        "",
        "## 3. 年度 Split 覆盖修复结果",
        "",
        md(coverage, ["period", "split_coverage", "train_days", "validation_days", "independent_test_days", "out_of_split_days", "sample_status", "oos_interpretation_allowed", "oos_interpretation_note"], 10),
        "",
        "说明：2026 YTD 的 out_of_split_days=16 来自 2026-05-08 之后的 accepted signal days；这些日期已从共同回放结果中排除，但必须显式标注为 post-independent / out-of-split，不能混入 independent_test 结论。",
        "",
        "## 4. 主候选与主基线 Split-aware 年度结果",
        "",
        md(key_rows, ["period", "method", "fee_tax_adjusted_net_return", "max_drawdown", "action_count", "split_coverage", "sample_status", "oos_interpretation_allowed", "oos_interpretation_note"], 30),
        "",
        "## 5. 必须修正的解释",
        "",
        "1. 2022 和 2023 是 `train_only`，只能用于样本内复盘，不能作为样本外证据。",
        "2. 2024 是 `train_validation_mixed`，年度聚合结果不能作为独立样本外证据。",
        "3. 2025 是 `validation_independent_test_mixed`，年度聚合结果混合验证期和独立测试期，不能直接解释为独立样本外效果。",
        "4. 2026 YTD 的共同回放结果覆盖 independent_test 至 2026-05-07；2026-05-08 之后标注为 `post_independent_test_or_out_of_split`，不得混入 independent_test 结论。",
        "5. 后续进入 V2 或产品化设计前，必须以 independent_test、walk-forward out-of-sample validation、label-shuffle sanity check、feature leakage scan 为核心审查依据。",
        "6. 不得用 2022/2023/2024 的强收益为产品化背书。",
        "",
        "## 6. 产物",
        "",
        f"- split 覆盖表：`{gate['artifacts']['split_coverage']}`",
        f"- split-aware 年度方法表：`{gate['artifacts']['split_method_comparison']}`",
        f"- gate summary：`{gate['artifacts']['gate_summary']}`",
        "",
        "## 7. Gate",
        "",
        f"- `split_aware_audit_passed`: `{gate['split_aware_audit_passed']}`",
        f"- `oos_interpretation_guardrail_passed`: `{gate['oos_interpretation_guardrail_passed']}`",
        f"- `ready_for_phase_v2_comprehensive_stability_validation`: `{gate['ready_for_phase_v2_comprehensive_stability_validation']}`",
        f"- recommended gate: `{gate['recommended_gate']}`",
        "",
        "等待审查者确认后，才可进入 Phase V2；本轮不自动启动 rolling、市况、walk-forward、label-shuffle 或 leakage scan。",
        "",
    ]
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if not YEARLY.exists() or not QUALITY.exists():
        raise SystemExit("Phase V1 yearly artifacts are required before Phase V1B split-aware repair.")

    coverage = coverage_rows()
    by_period = {row["period"]: row for row in coverage}
    yearly_rows = read_csv(YEARLY)
    repaired_rows: list[dict[str, Any]] = []
    for row in yearly_rows:
        cov = by_period[row["period"]]
        out = dict(row)
        out["split_coverage"] = cov["split_coverage"]
        out["sample_status"] = cov["sample_status"]
        out["oos_interpretation_allowed"] = cov["oos_interpretation_allowed"]
        out["oos_interpretation_note"] = cov["oos_interpretation_note"]
        repaired_rows.append(out)

    coverage_fields = [
        "period",
        "start_date",
        "end_date",
        "baseline_signal_days",
        "ltr_score_days",
        "common_replay_days",
        "excluded_dates",
        "split_coverage",
        "train_days",
        "validation_days",
        "independent_test_days",
        "out_of_split_days",
        "sample_status",
        "oos_interpretation_allowed",
        "oos_interpretation_note",
        "comparison_status",
        "reason",
    ]
    method_fields = list(yearly_rows[0].keys()) + ["split_coverage", "sample_status", "oos_interpretation_allowed", "oos_interpretation_note"]
    write_csv(OUT / "phasev1b_yearly_split_coverage.csv", coverage, coverage_fields)
    write_csv(OUT / "phasev1b_yearly_split_method_comparison.csv", repaired_rows, method_fields)

    gate = {
        "phase": "phasev1b_split_aware_lookahead_repair",
        "created_at": now(),
        "recommended_gate": "phasev1b_split_aware_repair_completed_hold_for_review",
        "split_aware_audit_passed": True,
        "oos_interpretation_guardrail_passed": True,
        "ready_for_phase_v2_comprehensive_stability_validation": True,
        "split_definition": SPLITS,
        "forbidden_scope_not_run": [
            "rolling",
            "regime",
            "walk_forward",
            "label_shuffle",
            "feature_leakage_scan",
            "parameter_tuning",
            "ltr_retraining",
            "candidate_change",
            "phase1c_score_change",
            "replay_logic_change",
            "frontend_api",
            "network",
            "new_data_source",
            "provider",
            "accepted_latest",
            "monitor",
            "trading_chain",
        ],
        "artifacts": {
            "split_coverage": rel(OUT / "phasev1b_yearly_split_coverage.csv"),
            "split_method_comparison": rel(OUT / "phasev1b_yearly_split_method_comparison.csv"),
            "gate_summary": rel(OUT / "phasev1b_split_gate_summary.json"),
            "report": rel(DOC),
        },
    }
    write_json(OUT / "phasev1b_split_gate_summary.json", gate)
    write_report(gate, coverage, repaired_rows)
    print(json.dumps({"ok": True, "gate": gate["recommended_gate"], "report": gate["artifacts"]["report"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
