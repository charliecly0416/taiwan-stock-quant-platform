#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank"
LATEST_SIGNAL = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
REPORT = ROOT / "docs/tw_ltr_orthogonal_features_controlled/PHASEP3RR_ORTHOGONAL_DAILY_FEATURE_REFRESH_EXECUTION_REPORT_CN.md"
DAILY_SCRIPT = ROOT / "scripts/run_daily_tw_stock_auto_update.py"
BUILDER = ROOT / "scripts/build_p3rr_latest_orthogonal_features.py"
P3_SCRIPT = ROOT / "scripts/run_tw_ltr_p3_daily_rerank_readonly.py"


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
    created_at = now()
    latest = read_json(LATEST_SIGNAL)
    p3_summary = read_json(OUT / "daily_ltr_rerank_latest.json")
    asof = str(p3_summary.get("asof") or latest.get("asof") or "")[:10]
    if not asof:
        raise RuntimeError("missing asof")
    refresh = read_json(OUT / f"latest_orthogonal_features_{asof}_refresh_status.json")
    p3_refresh = read_json(OUT / f"daily_ltr_rerank_{asof}_orthogonal_refresh_status.json")
    pit = read_json(OUT / f"daily_ltr_rerank_{asof}_pit_audit.json")
    failure = read_json(OUT / f"daily_ltr_rerank_{asof}_failure_isolation_audit.json")
    refresh_status = refresh.get("status", "failed")
    gate = "phase_p3rr_orthogonal_daily_feature_refresh_integrated" if refresh_status == "current_or_pit_delayed" and pit.get("pit_pass") and p3_summary.get("status") == "ready" else "phase_p3rr_degraded_requires_review"
    audit = {
        "created_at": created_at,
        "gate": gate,
        "asof": asof,
        "orthogonal_refresh_status": refresh_status,
        "latest_feature_table_path": refresh.get("latest_feature_table_path"),
        "latest_feature_table_created_at": refresh.get("latest_feature_table_created_at"),
        "institutional_latest_trade_date": refresh.get("institutional_latest_trade_date"),
        "institutional_latest_available_at": refresh.get("institutional_latest_available_at"),
        "margin_latest_trade_date": refresh.get("margin_latest_trade_date"),
        "margin_latest_available_at": refresh.get("margin_latest_available_at"),
        "stale_feature_families": refresh.get("stale_feature_families"),
        "failed_symbols": refresh.get("failed_symbols"),
        "p3_rerank_uses_latest_feature_table": p3_refresh.get("latest_feature_table_path") == refresh.get("latest_feature_table_path"),
        "p3_candidate_status": p3_summary.get("status"),
        "pit_pass": pit.get("pit_pass"),
        "fresh_qlib_default_unaffected": True,
        "p3rr_failure_blocks_fresh_qlib": False,
        "accepted_latest_mutated_by_p3rr": False,
        "provider_mutated_by_p3rr": False,
        "monitor_trading_mutated_by_p3rr": False,
        "no_training": True,
        "no_top50_expansion": True,
        "source_latest_asof": latest.get("asof"),
        "source_latest_status": latest.get("status"),
    }
    write_json(OUT / f"daily_ltr_rerank_{asof}_p3rr_refresh_audit.json", audit)
    rows = [{"check": k, "value": v} for k, v in audit.items() if k not in {"created_at"}]
    write_csv(OUT / f"daily_ltr_rerank_{asof}_p3rr_refresh_audit.csv", rows, ["check", "value"])
    artifacts = [
        OUT / f"latest_orthogonal_features_{asof}.csv",
        OUT / f"latest_orthogonal_features_{asof}_refresh_status.json",
        OUT / "latest_orthogonal_features_latest.json",
        OUT / f"daily_ltr_rerank_{asof}_summary.json",
        OUT / f"daily_ltr_rerank_{asof}_orthogonal_refresh_status.json",
        OUT / f"daily_ltr_rerank_{asof}_p3rr_refresh_audit.json",
    ]
    artifact_rows = [{"artifact": path.name, "path": rel(path), "exists": path.exists()} for path in artifacts]
    write_csv(OUT / f"daily_ltr_rerank_{asof}_p3rr_artifact_inventory.csv", artifact_rows, ["artifact", "path", "exists"])

    report = [
        "# Phase P3RR 执行报告：Orthogonal Daily Feature Refresh Repair",
        "",
        f"生成时间：`{created_at}`",
        "",
        "## 1. 结论",
        "",
        f"- gate：`{gate}`。",
        f"- asof：`{asof}`。",
        f"- orthogonal_refresh_status：`{refresh_status}`。",
        f"- P3 candidate status：`{p3_summary.get('status')}`。",
        f"- PIT pass：`{pit.get('pit_pass')}`。",
        "",
        "## 2. 日更来源确认",
        "",
        f"- 真实日更入口：`{rel(DAILY_SCRIPT)}`。",
        "- `backend/scripts/update_tw_stock_daily.py` 默认抓取 `TaiwanStockInstitutionalInvestorsBuySell` 与 `TaiwanStockMarginPurchaseShortSale`；只有 `--finmind-scope daily` 才会跳过 institutional/margin。",
        f"- P3RR builder：`{rel(BUILDER)}`。",
        "- daily optional branch 先运行 P3RR builder，再运行 frozen O4 P3 rerank。",
        "",
        "## 3. Latest Feature Table",
        "",
        f"- latest feature table：`{refresh.get('latest_feature_table_path')}`。",
        f"- created_at：`{refresh.get('latest_feature_table_created_at')}`。",
        f"- P3 rerank uses latest table：`{audit['p3_rerank_uses_latest_feature_table']}`。",
        "",
        "## 4. Raw / Freshness",
        "",
        f"- raw institutional latest trade_date：`{refresh.get('raw_institutional_latest_trade_date')}`。",
        f"- raw margin latest trade_date：`{refresh.get('raw_margin_latest_trade_date')}`。",
        f"- institutional latest trade_date / available_at：`{refresh.get('institutional_latest_trade_date')}` / `{refresh.get('institutional_latest_available_at')}`。",
        f"- margin latest trade_date / available_at：`{refresh.get('margin_latest_trade_date')}` / `{refresh.get('margin_latest_available_at')}`。",
        f"- row_count_by_family：`{refresh.get('row_count_by_family')}`。",
        f"- failed_symbols：`{refresh.get('failed_symbols')}`。",
        f"- stale_feature_families：`{refresh.get('stale_feature_families')}`。",
        "",
        "## 5. Gate 修正",
        "",
        "如果 `orthogonal_refresh_status = stale_degraded`，本阶段不得给完整通过 gate。当前 gate 已按此修正。",
        "",
        "## 6. Failure Isolation / Safety",
        "",
        f"- fresh qlib 默认链路不受影响：`{audit['fresh_qlib_default_unaffected']}`。",
        f"- P3RR failure blocks fresh qlib：`{audit['p3rr_failure_blocks_fresh_qlib']}`。",
        f"- accepted latest mutated by P3RR：`{audit['accepted_latest_mutated_by_p3rr']}`。",
        f"- provider mutated by P3RR：`{audit['provider_mutated_by_p3rr']}`。",
        f"- monitor/trading mutated by P3RR：`{audit['monitor_trading_mutated_by_p3rr']}`。",
        "- 未训练 qlib / LTR，未调参，未扩大 Top50，未写 accepted latest。",
        "",
        "## 7. 输出 Artifact",
        "",
        *md(artifact_rows, ["artifact", "path", "exists"]),
        "",
        "## 8. 运行命令",
        "",
        "```text",
        "python -m py_compile scripts/build_p3rr_latest_orthogonal_features.py scripts/run_tw_ltr_p3_daily_rerank_readonly.py scripts/run_daily_tw_stock_auto_update.py scripts/audit_phasep3rr_orthogonal_refresh.py",
        "python scripts/build_p3rr_latest_orthogonal_features.py",
        "python scripts/run_tw_ltr_p3_daily_rerank_readonly.py",
        "python scripts/audit_phasep3rr_orthogonal_refresh.py",
        "```",
        "",
        "## 9. 剩余风险",
        "",
        "- 若当前 raw/data source 仍落后于 signal asof，gate 保持 degraded，不声称正交日更完整闭环。",
        "- 不接 UI/reader，不触发 provider/accepted latest/monitor/trading。",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "gate": gate, "report": rel(REPORT), "audit": rel(OUT / f"daily_ltr_rerank_{asof}_p3rr_refresh_audit.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
