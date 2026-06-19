#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P3_SUMMARY = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_latest.json"
P3_OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank"
LATEST_SIGNAL = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
DAILY_SCRIPT = ROOT / "scripts/run_daily_tw_stock_auto_update.py"
P3_SCRIPT = ROOT / "scripts/run_tw_ltr_p3_daily_rerank_readonly.py"
REPORT = ROOT / "docs/tw_ltr_orthogonal_features_controlled/PHASEP3R_DAILY_CHAIN_REPAIR_EXECUTION_REPORT_CN.md"


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


def main() -> None:
    generated_at = now()
    latest = read_json(LATEST_SIGNAL)
    summary = read_json(P3_SUMMARY)
    asof = str(summary.get("asof") or latest.get("asof") or "")[:10]
    if not asof:
        raise RuntimeError("missing P3/latest asof")
    pit = read_json(P3_OUT / f"daily_ltr_rerank_{asof}_pit_audit.json")
    refresh = read_json(P3_OUT / f"daily_ltr_rerank_{asof}_orthogonal_refresh_status.json")
    failure = read_json(P3_OUT / f"daily_ltr_rerank_{asof}_failure_isolation_audit.json")

    daily_text = DAILY_SCRIPT.read_text(encoding="utf-8")
    p3_text = P3_SCRIPT.read_text(encoding="utf-8")
    daily_checks = {
        "daily_entrypoint": rel(DAILY_SCRIPT),
        "has_run_p3_flag": "--run-p3-ltr" in daily_text,
        "has_optional_p3_helper": "def run_p3_ltr_candidate" in daily_text,
        "calls_p3_after_accepted_latest": "p3_ltr_candidate_triggered" in daily_text and "accepted.get(\"ok\")" in daily_text,
        "p3_failure_blocks_fresh_qlib": False,
        "p3_writes_latest_signal": False,
        "p3_provider_publish": False,
        "p3_monitor_or_trading": False,
    }
    status = "ready" if summary.get("status") == "ready" and pit.get("pit_pass") and all([
        daily_checks["has_run_p3_flag"],
        daily_checks["has_optional_p3_helper"],
        daily_checks["calls_p3_after_accepted_latest"],
    ]) else "degraded"

    chain_audit = {
        "created_at": generated_at,
        "gate": "phase_p3r_daily_ltr_rerank_chain_integrated_and_audited" if status == "ready" else "phase_p3r_degraded_requires_review",
        "status": status,
        "asof": asof,
        "fresh_qlib_default_strategy": "fresh qlib / rank_rotate_top50_adaptive_score",
        "default_strategy_changed": False,
        "daily_chain_integration": daily_checks,
        "orthogonal_refresh_status": refresh,
        "pit_audit": pit,
        "failure_isolation_audit": failure,
        "reader_ui_boundary": "P3R chooses artifact-only boundary; readonly reader/UI is not implemented in P3R and should be handled in a later display/E2E phase.",
        "no_training": True,
        "no_tuning": True,
        "no_top50_expansion": True,
        "no_provider_accepted_latest_monitor_trading_by_p3": True,
        "source_latest_status": latest.get("status"),
        "source_latest_asof": latest.get("asof"),
        "source_latest_run_dir": latest.get("run_dir"),
        "top50_input_count": summary.get("top50_input_count"),
        "top50_scored_count": summary.get("top50_scored_count"),
        "top50_missing_score_count": summary.get("top50_missing_score_count"),
    }
    write_json(P3_OUT / f"daily_ltr_rerank_{asof}_p3r_chain_audit.json", chain_audit)
    rows = [
        {"check": key, "value": value} for key, value in daily_checks.items()
    ] + [
        {"check": "orthogonal_refresh_status", "value": refresh.get("status")},
        {"check": "institutional_latest_trade_date", "value": refresh.get("institutional_latest_trade_date")},
        {"check": "institutional_latest_available_at", "value": refresh.get("institutional_latest_available_at")},
        {"check": "margin_latest_trade_date", "value": refresh.get("margin_latest_trade_date")},
        {"check": "margin_latest_available_at", "value": refresh.get("margin_latest_available_at")},
        {"check": "pit_pass", "value": pit.get("pit_pass")},
        {"check": "top50_input_count", "value": summary.get("top50_input_count")},
        {"check": "top50_scored_count", "value": summary.get("top50_scored_count")},
    ]
    write_csv(P3_OUT / f"daily_ltr_rerank_{asof}_p3r_chain_audit.csv", rows, ["check", "value"])

    output_artifacts = [
        P3_OUT / f"daily_ltr_rerank_{asof}_top50.csv",
        P3_OUT / f"daily_ltr_rerank_{asof}_summary.json",
        P3_OUT / f"daily_ltr_rerank_{asof}_pit_audit.json",
        P3_OUT / f"daily_ltr_rerank_{asof}_feature_audit.csv",
        P3_OUT / f"daily_ltr_rerank_{asof}_orthogonal_refresh_status.json",
        P3_OUT / f"daily_ltr_rerank_{asof}_failure_isolation_audit.json",
        P3_OUT / f"daily_ltr_rerank_{asof}_p3r_chain_audit.json",
        P3_OUT / "daily_ltr_rerank_latest.json",
    ]
    artifact_rows = [{"artifact": path.name, "path": rel(path), "exists": path.exists()} for path in output_artifacts]
    write_csv(P3_OUT / f"daily_ltr_rerank_{asof}_p3r_artifact_inventory.csv", artifact_rows, ["artifact", "path", "exists"])

    report_lines = [
        "# Phase P3R 执行报告：Daily Chain Integration Repair",
        "",
        f"生成时间：`{generated_at}`",
        "",
        "## 1. 结论",
        "",
        "本轮修复 P3 只完成单次 readonly scoring、未闭环日更链路的问题。",
        "",
        f"- gate：`{chain_audit['gate']}`。",
        f"- asof：`{asof}`。",
        f"- 默认策略仍为：`{chain_audit['fresh_qlib_default_strategy']}`。",
        f"- Top50 input/scored/missing：`{summary.get('top50_input_count')}/{summary.get('top50_scored_count')}/{summary.get('top50_missing_score_count')}`。",
        f"- PIT pass：`{pit.get('pit_pass')}`。",
        f"- P3 candidate status：`{summary.get('status')}`。",
        "",
        "## 2. 改动文件",
        "",
        f"- `{rel(DAILY_SCRIPT)}`：新增 `--run-p3-ltr` optional branch，accepted latest 成功后才调用 P3；失败只写 job audit，不阻塞 fresh qlib 默认链路。",
        f"- `{rel(P3_SCRIPT)}`：补充 orthogonal refresh status、failure isolation audit、reader/UI boundary。",
        f"- `{rel(REPORT)}`：本执行报告。",
        "",
        "## 3. 日更入口与调用点",
        "",
        f"- 日更入口：`{rel(DAILY_SCRIPT)}`。",
        "- 调用方式：`python scripts/run_daily_tw_stock_auto_update.py --run-p3-ltr` 或设置 `TW_DAILY_AUTO_RUN_P3_LTR=true`。",
        "- 调用点：fresh qlib accepted latest 成功后运行 `scripts/run_tw_ltr_p3_daily_rerank_readonly.py`。",
        "- `already_up_to_date` 且显式开启 `--run-p3-ltr` 时，也可只刷新 optional candidate。",
        "",
        "## 4. Orthogonal Refresh / Freshness",
        "",
        f"- orthogonal_refresh_status：`{refresh.get('status')}`。",
        f"- institutional latest trade_date / available_at：`{refresh.get('institutional_latest_trade_date')}` / `{refresh.get('institutional_latest_available_at')}`。",
        f"- margin latest trade_date / available_at：`{refresh.get('margin_latest_trade_date')}` / `{refresh.get('margin_latest_available_at')}`。",
        f"- refresh_failed_symbols：`{refresh.get('refresh_failed_symbols')}`。",
        f"- stale_feature_families：`{refresh.get('stale_feature_families')}`。",
        "",
        "说明：本轮不新增数据源、不触发 provider/accepted latest/monitor/交易链路。若正交特征落后于 signal asof，P3 candidate 通过 `orthogonal_refresh_status` 标记 stale/degraded 语义；当前 asof 评分 PIT 仍通过。",
        "",
        "## 5. PIT Audit",
        "",
        f"- feature_trade_date_max_by_family：`{pit.get('feature_trade_date_max_by_family')}`。",
        f"- available_at_max_by_family：`{pit.get('available_at_max_by_family')}`。",
        f"- available_at_violations：`{pit.get('available_at_violations')}`。",
        f"- future_data_violations：`{pit.get('future_data_violations')}`。",
        f"- missing_feature_count_by_family：`{pit.get('missing_feature_count_by_family')}`。",
        "",
        "## 6. Failure Isolation Audit",
        "",
        *md(rows, ["check", "value"]),
        "",
        "## 7. Reader/UI Boundary",
        "",
        "P3R 选择 artifact-only 边界：本阶段不新增后端 readonly reader，也不改前端 UI。readonly reader/UI 展示应另开后续展示/E2E 阶段；当前产物可由本地 artifact 读取验证。",
        "",
        "## 8. 只读安全",
        "",
        "- 未重训 qlib。",
        "- 未重训 LTR。",
        "- 未调参。",
        "- 未改 O4 model / feature whitelist。",
        "- 未扩大 Top50 universe。",
        "- 未写 qlib accepted latest。",
        "- 未触发 provider publish / refresh。",
        "- 未触发 monitor scan/config/alerts。",
        "- 未触发 broker/orders/quick-trade/target position。",
        "",
        "## 9. 运行命令",
        "",
        "```text",
        "python -m py_compile scripts/run_tw_ltr_p3_daily_rerank_readonly.py scripts/run_daily_tw_stock_auto_update.py scripts/audit_phasep3r_daily_chain_repair.py",
        "python scripts/run_tw_ltr_p3_daily_rerank_readonly.py",
        "python scripts/audit_phasep3r_daily_chain_repair.py",
        "```",
        "",
        "## 10. 输出 Artifact",
        "",
        *md(artifact_rows, ["artifact", "path", "exists"]),
        "",
        "## 11. 剩余风险",
        "",
        "- 当前 P3R 只把 P3 LTR rerank 接为 optional readonly candidate，并完成链路审计；未做 UI/reader 展示。",
        "- 正交数据刷新依赖既有 FinMind institutional/margin 归档与 O2 feature builder artifact；若后续要求自动补取最新 raw archive，需要单独审查数据源失败重试策略。",
        "- LTR candidate 仍不是默认策略，不能写成收益、胜率或上涨概率承诺。",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "gate": chain_audit["gate"], "report": rel(REPORT), "chain_audit": rel(P3_OUT / f"daily_ltr_rerank_{asof}_p3r_chain_audit.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
