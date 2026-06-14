#!/usr/bin/env python3
"""Phase 0B read-only design audit for orthogonal TW Decision data.

This script inventories existing local scripts and writes PIT schema/backfill
design documents. It does not run download, materialize, screening, ablation,
provider, frontend/API, model training, or trading logic.
"""
from __future__ import annotations

import ast
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_tw/experiments/decision_orthogonal"
DOC_DIR = ROOT / "docs/tw_decision_model_orthogonal"

INVENTORY_PATH = OUT_DIR / "phase0b_script_inventory.csv"
SCHEMA_PATH = OUT_DIR / "phase0b_pit_schema_proposal.md"
BACKFILL_PLAN_PATH = DOC_DIR / "PHASE0B_DATA_BACKFILL_PLAN_CN.md"
EXEC_REPORT_PATH = DOC_DIR / "PHASE0B_EXECUTION_REPORT_CN.md"

REQUIRED_SCRIPTS = [
    "qlib_pipeline/examples/tw/run_tw_finmind_institutional_full_download.py",
    "qlib_pipeline/examples/tw/run_tw_finmind_institutional_poc.py",
    "qlib_pipeline/examples/tw/materialize_tw_institutional_factors.py",
    "qlib_pipeline/examples/tw/screen_tw_institutional_factors.py",
    "qlib_pipeline/examples/tw/run_tw_finmind_margin_full_download.py",
    "qlib_pipeline/examples/tw/run_tw_finmind_margin_poc.py",
    "qlib_pipeline/examples/tw/materialize_tw_margin_batch_a.py",
    "qlib_pipeline/examples/tw/screen_tw_margin_batch_a.py",
    "qlib_pipeline/examples/tw/run_tw_margin_util_ablation.py",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def literal_arg(node: ast.AST) -> str:
    try:
        value = ast.literal_eval(node)
    except Exception:
        return ""
    return str(value)


def parse_argparse_args(text: str) -> list[str]:
    args: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return args
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "add_argument":
            names = [literal_arg(arg) for arg in node.args]
            names = [name for name in names if name.startswith("-")]
            default = ""
            for kw in node.keywords:
                if kw.arg == "default":
                    default = literal_arg(kw.value)
            if names:
                args.append("/".join(names) + (f" default={default}" if default else ""))
    return args


def infer_category(path: str, text: str) -> str:
    low = (path + "\n" + text).lower()
    if "revenue" in low or "monthly_revenue" in low or "taiwanstockmonthrevenue" in low:
        return "monthly_revenue"
    if "institutional" in low or "taiwanstockinstitutionalinvestorsbuysell" in low:
        return "institutional_flow"
    if "margin" in low or "short" in low or "taiwanstockmarginpurchaseshortsale" in low:
        return "margin_short"
    return "unknown"


def infer_purpose(path: str, text: str) -> str:
    name = Path(path).name
    low = text.lower()
    if "full_download" in name:
        return "full historical FinMind download and source diagnostics"
    if "poc" in name:
        return "narrow FinMind POC download and source diagnostics"
    if name.startswith("materialize"):
        return "materialize raw source rows into derived factor CSV diagnostics"
    if name.startswith("screen"):
        return "write Qlib feature bins and run single-factor screening"
    if "ablation" in name:
        return "run fixed factor ablation/model experiment"
    if "download" in low:
        return "download or audit source data"
    return "unknown"


def extract_output_paths(text: str) -> list[str]:
    paths = set()
    for pattern in [
        r'default="([^"]*data_tw/[^"]*)"',
        r"REPORT_PATH\s*=\s*ROOT\s*/\s*\"([^\"]+)\"",
        r"SOURCE_DIR\s*=\s*ROOT\s*/\s*\"([^\"]+)\"",
        r"STATUS_PATH\s*=\s*ROOT\s*/\s*\"([^\"]+)\"",
        r"RAW_DIR\s*=\s*ROOT\s*/\s*\"([^\"]+)\"",
        r"OUT_DIR_DEFAULT\s*=\s*\"([^\"]+)\"",
        r"to_csv\(out(?:_dir)?\s*/\s*\"([^\"]+)\"",
        r"tofile\(out_path\)",
    ]:
        for match in re.findall(pattern, text):
            paths.add(match)
    return sorted(paths)


def inventory_script(path_str: str) -> dict[str, Any]:
    path = ROOT / path_str
    if not path.exists():
        category = infer_category(path_str, "")
        return {
            "script_path": path_str,
            "exists": False,
            "category": category,
            "purpose": "missing script",
            "requires_network": False,
            "writes_data": False,
            "possible_output_paths": "",
            "input_args": "",
            "uses_finmind": False,
            "touches_provider_refresh_publish": False,
            "touches_accepted_latest": False,
            "safe_to_run_in_phase0b": False,
            "reason": "File not found; recorded as missing. Do not run in Phase 0B.",
        }
    text = read_text(path)
    low = text.lower()
    args = parse_argparse_args(text)
    output_paths = extract_output_paths(text)
    requires_network = "requests.get" in text or "fetcher.get" in low or "finmind_url" in low
    writes_data = any(token in text for token in [".to_csv(", ".to_parquet(", ".tofile(", ".write_text(", "mkdir("])
    uses_finmind = "finmind" in low or "taiwanstock" in low
    touches_provider = "publish" in low or "provider" in low or "features/" in low or ".day.bin" in low
    touches_accepted = "accepted latest" in low or "accepted_latest" in low
    safe = bool((not requires_network) and (not writes_data) and (not touches_provider) and (not touches_accepted))
    reason = []
    if requires_network:
        reason.append("requires network/FinMind request")
    if writes_data:
        reason.append("writes local outputs or feature bins")
    if touches_provider:
        reason.append("touches provider/materialized Qlib feature path or publish semantics")
    if touches_accepted:
        reason.append("mentions accepted latest")
    if not reason:
        reason.append("read-only by static scan")
    if path_str in REQUIRED_SCRIPTS:
        safe = False
        reason.append("Phase 0B work doc says required scripts are inventory targets only; do not run them")
    return {
        "script_path": path_str,
        "exists": True,
        "category": infer_category(path_str, text),
        "purpose": infer_purpose(path_str, text),
        "requires_network": requires_network,
        "writes_data": writes_data,
        "possible_output_paths": "; ".join(output_paths),
        "input_args": "; ".join(args),
        "uses_finmind": uses_finmind,
        "touches_provider_refresh_publish": touches_provider,
        "touches_accepted_latest": touches_accepted,
        "safe_to_run_in_phase0b": safe,
        "reason": "; ".join(reason),
    }


def discover_monthly_revenue_scripts() -> list[str]:
    paths = []
    base = ROOT / "qlib_pipeline/examples/tw"
    if not base.exists():
        return paths
    for path in sorted(base.glob("*.py")):
        text = read_text(path)
        low = (path.name + "\n" + text).lower()
        if "revenue" in low or "monthly_revenue" in low or "taiwanstockmonthrevenue" in low:
            paths.append(rel(path))
    return [p for p in paths if p not in REQUIRED_SCRIPTS]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def md_table(rows: list[dict[str, Any]], cols: list[str]) -> str:
    if not rows:
        return "_no rows_"
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---" for _ in cols]) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    return "\n".join(lines)


def write_schema_proposal() -> None:
    lines = [
        "# Phase 0B PIT 行级归档 Schema Proposal",
        "",
        "## 总原则",
        "",
        "- 所有正交数据必须以 row-level as-reported snapshot 归档，不得只保留事后覆盖后的最终值。",
        "- 所有进入 Phase 1 的字段必须能证明 `available_at <= asof`。",
        "- 日频法人筹码、融资融券默认采用保守 T+1：若 FinMind/TWSE 文档证明盘后发布，则 `available_at = next_trading_day(trade_date)`；若能记录实际抓取/公告时间，则使用更严格的实际可见时间。",
        "- 月营收必须从 `announcement_date`/`available_at` 向后对齐交易日，禁止按 `source_period` 直接 join 到所属月份。",
        "- 每行必须保留 `data_source` 与 `raw_snapshot_id`，后续修正值只能新增 snapshot，不得覆盖历史 as-reported 记录。",
        "",
        "## 法人筹码 Schema",
        "",
        "| column | required | note |",
        "|---|---|---|",
        "| symbol | yes | Qlib symbol, e.g. TW2330 |",
        "| stock_id | yes | 原始台股代码 |",
        "| trade_date | yes | 原始交易日 |",
        "| available_at | yes | 默认 next_trading_day(trade_date)，或实际可见时间 |",
        "| foreign_net_buy | yes | 外资买卖超，需注明单位 |",
        "| investment_trust_net_buy | yes | 投信买卖超，需注明单位 |",
        "| dealer_net_buy | yes | 自营商买卖超，需注明单位 |",
        "| institutional_total_net_buy | yes | 三大法人合计买卖超 |",
        "| data_source | yes | FinMind/TWSE/TPEx 等 |",
        "| raw_snapshot_id | yes | 原始抓取快照 id，支撑 as-reported 审计 |",
        "| fetched_at | recommended | 本地抓取时间，仅作审计，不替代官方发布时间 |",
        "| quality_flags | recommended | 单位异常、缺行、负值等 |",
        "",
        "可派生字段：连续 N 日买超/卖超、买卖超占成交量比例、外资/投信同步方向。派生时只允许使用 `available_at <= asof` 的行。",
        "",
        "## 融资融券 Schema",
        "",
        "| column | required | note |",
        "|---|---|---|",
        "| symbol | yes | Qlib symbol |",
        "| stock_id | yes | 原始台股代码 |",
        "| trade_date | yes | 原始交易日 |",
        "| available_at | yes | 默认 next_trading_day(trade_date)，或实际可见时间 |",
        "| margin_balance | yes | 融资余额 |",
        "| margin_balance_change | yes | 融资余额变化，可由今日/昨日余额计算 |",
        "| short_balance | yes | 融券余额 |",
        "| short_balance_change | yes | 融券余额变化 |",
        "| data_source | yes | FinMind/TWSE/TPEx 等 |",
        "| raw_snapshot_id | yes | 原始抓取快照 id |",
        "| margin_limit | recommended | 计算融资使用率 proxy 所需 |",
        "| short_limit | recommended | 若数据源提供 |",
        "| suspension_or_restriction_flag | recommended | 停券/暂停交易/特殊状态 |",
        "",
        "可派生字段：融资使用率 proxy、融券回补 proxy、融资快速增加且价格高位、融资下降但价格不跌。所有滚动窗口必须以 `available_at` 截止。",
        "",
        "## 月营收 Schema",
        "",
        "| column | required | note |",
        "|---|---|---|",
        "| symbol | yes | Qlib symbol |",
        "| stock_id | yes | 原始台股代码 |",
        "| source_period | yes | 所属月份，例如 2025-09 |",
        "| announcement_date | yes | 公司公告日期或可审计等价发布时间 |",
        "| available_at | yes | 通常为 announcement_date 的次一可交易日或实际可见时间 |",
        "| revenue | yes | 月营收原始值 |",
        "| revenue_yoy | yes | YoY，优先保留原始/可复算值 |",
        "| revenue_mom | yes | MoM，优先保留原始/可复算值 |",
        "| days_since_last_report | yes | asof - available_at，Phase 1 join 时生成或归档 |",
        "| data_source | yes | MOPS/FinMind 等 |",
        "| raw_snapshot_id | yes | 原始抓取快照 id |",
        "| fetched_at | recommended | 本地抓取时间 |",
        "| revision_flag | recommended | 是否为后续修正 snapshot |",
        "",
        "月营收对齐规则：对每个 symbol，按 `available_at` 排序，只能从 `available_at` 当日之后向后 forward-fill 到下一份可见报告前。`source_period` 仅用于解释和派生，不得作为交易日 join key。",
        "",
        "## 事后修正处理",
        "",
        "- 原始值修正时新增一条更晚 `raw_snapshot_id`，并保留旧 snapshot。",
        "- Phase 1 构样本时按 asof 选择当时最新且 `available_at <= asof` 的 snapshot。",
        "- 若无法获得 as-reported snapshot，只能将字段 deferred，不得使用最终修正值。",
        "",
    ]
    SCHEMA_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_backfill_plan(inventory: list[dict[str, Any]], monthly_scripts: list[str]) -> None:
    lines = [
        "# Phase 0B 正交数据未来补齐方案草案",
        "",
        "## 1. 性质声明",
        "",
        "本文件不是执行日志，也不是补齐结果。Phase 0B 未联网、未下载、未 materialize、未写生产数据、未进入 Phase 1。",
        "",
        "## 2. 最小范围建议",
        "",
        "- 起止日期：优先 2022-01-01 至最新已审查 qlib asof；若 API 限额不足，可先做 2025-01-01 至 2026 当前日期的试点。",
        "- symbol universe：优先当前 qlib Option C / tw_liquid_dyn 150 档历史 universe；不得全市场扩展，除非用户另行授权。",
        "- 数据类别：第一优先法人筹码与融资融券，第二优先月营收。月营收若拿不到公告日期，直接 deferred。",
        "",
        "## 3. 每类数据的 PIT 风险",
        "",
        "- 法人筹码：FinMind/TWSE 盘后发布时间需要确认；若只有 trade_date，无 row-level `available_at`，必须采用保守 T+1 并在报告列明证据。",
        "- 融资融券：可能存在停券、暂停交易、限额字段缺失；必须保留缺失原因，不得盲目 forward-fill。",
        "- 月营收：最大风险是用 source period 直接 join 到当月交易日。必须有 announcement_date/available_at 和 as-reported snapshot。",
        "",
        "## 4. 最小字段",
        "",
        "- 法人筹码：`symbol`, `stock_id`, `trade_date`, `available_at`, `foreign_net_buy`, `investment_trust_net_buy`, `dealer_net_buy`, `institutional_total_net_buy`, `data_source`, `raw_snapshot_id`。",
        "- 融资融券：`symbol`, `stock_id`, `trade_date`, `available_at`, `margin_balance`, `margin_balance_change`, `short_balance`, `short_balance_change`, `data_source`, `raw_snapshot_id`。",
        "- 月营收：`symbol`, `stock_id`, `source_period`, `announcement_date`, `available_at`, `revenue`, `revenue_yoy`, `revenue_mom`, `days_since_last_report`, `data_source`, `raw_snapshot_id`。",
        "",
        "## 5. 需要联网的步骤",
        "",
        "- 运行 FinMind POC/full download 脚本会调用外部 API，需要用户另行授权。",
        "- 月营收脚本当前未在 `qlib_pipeline/examples/tw` 中发现；若新增脚本或数据源，需要用户另行授权。",
        "",
        "## 6. 会写入本地归档的步骤",
        "",
        "- POC/full download 脚本会写 raw CSV、status、coverage、diagnostics 和报告。",
        "- materialize 脚本会写 feature CSV 和诊断文件。",
        "- screening 脚本会写 Qlib feature bin、IC screening CSV 和报告。",
        "- ablation 脚本会运行模型/实验并写 recorder/log/summary，Phase 0B 和真实补齐阶段都不应运行，除非未来进入相应模型阶段并获授权。",
        "",
        "## 7. 必须再次征得用户确认的动作",
        "",
        "- 任何联网或 FinMind API 请求。",
        "- 任何真实数据下载或本地 raw archive 写入。",
        "- 任何 materialize 特征、Qlib bin 写入或 provider 相关写入。",
        "- 任何 Phase 1 样本构建、单因子检验、模型训练、前端/API 或交易相关动作。",
        "",
        "## 8. 如果无法获得 PIT 字段",
        "",
        "- 法人/融资融券无法证明盘后可见时间时：deferred，不进入 Phase 1。",
        "- 月营收没有 announcement_date/available_at 时：fail/deferred，不得用 source_period join。",
        "- 只拿到最终修正值且没有 as-reported snapshot 时：deferred。",
        "",
        "## 9. 脚本盘点摘要",
        "",
        md_table(inventory, ["script_path", "exists", "category", "purpose", "requires_network", "writes_data", "safe_to_run_in_phase0b"]),
        "",
        "## 10. 月营收脚本发现",
        "",
        md_table([{"script_path": p} for p in monthly_scripts], ["script_path"]),
        "",
    ]
    BACKFILL_PLAN_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_report(inventory: list[dict[str, Any]], monthly_scripts: list[str]) -> None:
    exists_count = sum(1 for row in inventory if row["exists"])
    network_count = sum(1 for row in inventory if row["requires_network"])
    writes_count = sum(1 for row in inventory if row["writes_data"])
    safe_count = sum(1 for row in inventory if row["safe_to_run_in_phase0b"])
    conclusion = "request_user_approval_for_data_backfill=true"
    lines = [
        "# Phase 0B 只读方案设计执行报告",
        "",
        "## 1. 执行范围",
        "",
        f"- 执行日期：`{utc_now()}`",
        "- 范围：只读盘点现有脚本、参数、输出路径和风险语义；设计 PIT 行级 schema；编写未来补齐方案草案。",
        "- 未执行：联网、FinMind 下载、materialize、provider refresh/publish、accepted latest switching、Phase 1 样本、单因子检验、模型训练、前端/API、broker/orders/quick-trade/target position。",
        "",
        "## 2. 修改文件",
        "",
        "- 新增 `scripts/audit_tw_decision_orthogonal_phase0b.py`。",
        "",
        "## 3. 生成文件",
        "",
        f"- `{rel(INVENTORY_PATH)}`",
        f"- `{rel(SCHEMA_PATH)}`",
        f"- `{rel(BACKFILL_PLAN_PATH)}`",
        f"- `{rel(EXEC_REPORT_PATH)}`",
        "",
        "## 4. 脚本盘点摘要",
        "",
        f"- 指定脚本数：`{len(REQUIRED_SCRIPTS)}`",
        f"- 存在脚本数：`{exists_count}`",
        f"- 需要联网脚本数：`{network_count}`",
        f"- 会写数据脚本数：`{writes_count}`",
        f"- Phase0B 可运行脚本数：`{safe_count}`",
        "",
        md_table(inventory, ["script_path", "exists", "category", "purpose", "requires_network", "writes_data", "touches_provider_refresh_publish", "safe_to_run_in_phase0b", "reason"]),
        "",
        "## 5. PIT Schema 设计摘要",
        "",
        "- 法人筹码：必须有 `symbol`, `trade_date`, `available_at`, 三大法人买卖超字段、`data_source`, `raw_snapshot_id`。",
        "- 融资融券：必须有 `symbol`, `trade_date`, `available_at`, 融资/融券余额与变化、`data_source`, `raw_snapshot_id`。",
        "- 月营收：必须有 `symbol`, `source_period`, `announcement_date`, `available_at`, revenue/YoY/MoM、`days_since_last_report`, `data_source`, `raw_snapshot_id`。",
        "- 日频数据默认使用保守 T+1；月营收只能从 announcement_date/available_at 向后对齐，不能按 source_period 直接 join。",
        "",
        "## 6. 未来补齐需要用户授权的动作清单",
        "",
        "- 运行任何 FinMind POC/full download。",
        "- 新增或接入月营收数据源。",
        "- 写 raw archive、status、coverage、diagnostics。",
        "- materialize 特征或写 Qlib bin/provider。",
        "- 构建 Phase 1 样本、单因子检验、训练模型、前端/API。",
        "",
        "## 7. Phase0B 禁止运行的脚本",
        "",
        md_table([row for row in inventory if not row["safe_to_run_in_phase0b"]], ["script_path", "reason"]),
        "",
        "## 8. 安全边界",
        "",
        "- broker/orders/quick-trade/target position/target weight：未触碰。",
        "- provider refresh/publish：未触碰。",
        "- accepted latest switching：未触碰。",
        "- monitor config/alerts：未触碰。",
        "- 真实交易建议语义：未生成。",
        "",
        "## 9. 是否建议进入真实数据补齐阶段",
        "",
        f"- Phase0B gate 结论：`{conclusion}`。",
        "- 说明：现有脚本显示法人/融资融券补齐技术路径存在，但都需要联网和写本地归档；月营收脚本未发现。执行者不能自行补齐，需等待审查者和用户下一步授权。",
        "- Phase 1：不允许进入。",
        "",
        "## 10. 需要用户确认的问题",
        "",
        "- 是否允许联网调用 FinMind 或其他数据源。",
        "- 是否允许写入新的正交 raw archive 与 PIT snapshot。",
        "- 是否接受日频法人/融资融券使用保守 T+1 `available_at` 规则。",
        "- 月营收若仓库没有现成脚本，是否允许新增脚本或改用其他具备公告日的数据源。",
        "",
        "## 11. 月营收脚本发现",
        "",
        md_table([{"script_path": p} for p in monthly_scripts], ["script_path"]),
        "",
    ]
    EXEC_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    monthly_scripts = discover_monthly_revenue_scripts()
    inventory_paths = REQUIRED_SCRIPTS + [p for p in monthly_scripts if p not in REQUIRED_SCRIPTS]
    inventory = [inventory_script(path) for path in inventory_paths]
    write_csv(INVENTORY_PATH, inventory)
    write_schema_proposal()
    write_backfill_plan(inventory, monthly_scripts)
    write_report(inventory, monthly_scripts)
    print(json.dumps({
        "status": "ok",
        "scope": "phase0b_readonly_design_only",
        "inventory_count": len(inventory),
        "monthly_revenue_script_count": len(monthly_scripts),
        "safe_to_run_in_phase0b_count": sum(1 for row in inventory if row["safe_to_run_in_phase0b"]),
        "gate": {
            "stop_orthogonal_data_line": False,
            "request_user_approval_for_data_backfill": True,
            "phase0b_incomplete": False,
        },
        "outputs": [
            rel(Path("scripts/audit_tw_decision_orthogonal_phase0b.py")),
            rel(INVENTORY_PATH),
            rel(SCHEMA_PATH),
            rel(BACKFILL_PLAN_PATH),
            rel(EXEC_REPORT_PATH),
        ],
        "safety": {
            "network": False,
            "download": False,
            "materialize": False,
            "provider_refresh_publish": False,
            "accepted_latest_switching": False,
            "phase1_samples": False,
            "model_training": False,
            "frontend_api": False,
            "broker_orders_quick_trade_target_positions": False,
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
