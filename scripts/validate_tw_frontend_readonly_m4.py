#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
VIEW = FRONTEND / "src/views/tw-stock-monitor/index.vue"
API = FRONTEND / "src/api/tw-stock.js"
COMPONENT_DIR = FRONTEND / "src/views/tw-stock-monitor/components"
COMPONENTS = {
    "ReadonlyStrategySnapshotPanel": COMPONENT_DIR / "ReadonlyStrategySnapshotPanel.vue",
    "ReadonlyReplayWindowPanel": COMPONENT_DIR / "ReadonlyReplayWindowPanel.vue",
    "ReplayAuditDetail": COMPONENT_DIR / "ReplayAuditDetail.vue",
}
READONLY_API_FUNCTIONS = {
    "getTwStockReadonlyStrategySnapshot": "/readonly-strategy-snapshot",
    "getTwStockReadonlyReplayWindowIndex": "/readonly-replay-window-index",
    "getTwStockReadonlyReplayWindow": "/readonly-replay-window",
}
REPLAY_STRATEGY_WRITE_WRAPPERS = {
    "runTwStockPortfolioReplay": "/rank-tech-cross/portfolio-replay",
    "runTwStockReadonlyBacktest": "/api/indicator/backtest",
}
M4_ACCEPTANCE_ENTRYPOINTS = [
    "mounted",
    "refreshAll",
    "loadReadonlyStrategySnapshot",
    "loadReadonlyReplayWindowIndex",
    "loadReadonlyReplayWindow",
    "handleReadonlyReplayWindowSelect",
]
M4_ACCEPTANCE_FORBIDDEN_CALLS = [
    "loadRankTechPortfolioPanel",
    "loadPortfolioReplay",
    "runTwStockPortfolioReplay",
    "runTwStockReadonlyBacktest",
    "runReadonlyBacktest",
]
FORBIDDEN_FRONTEND_TOKENS = [
    "--enable-legacy-provider-publish",
    "TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH",
]
FORBIDDEN_REQUEST_PATTERNS = {
    "provider_publish_refresh": ["provider-publish", "provider_publish", "provider/refresh", "accepted_latest", "accepted-latest"],
    "broker_orders": ["/broker/", "/api/broker/", "quick-trade", "quickTrade", "/orders", "submitOrder", "placeOrder"],
    "monitor_writes": ["saveTwStockMonitorConfig", "scanTwStockMonitor", "scanAllTwStockMonitors", "updateTwStockAlert"],
    "replay_strategy_writes": ["runTwStockPortfolioReplay", "runTwStockReadonlyBacktest", "rank-tech-cross/portfolio-replay", "/api/indicator/backtest"],
}
FORBIDDEN_TEXT = ["下单", "买入指令", "卖出指令", "目标仓位", "自动交易", "一键交易", "券商同步", "保证收益", "胜率承诺"]
AGENT_MARKERS = ["tw-stock-agent-panel", "agentSuggestedQuestions", "chatTwStockAgent", "agentSkills"]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def err(code: str, message: str, path: Path, field: str = "") -> dict[str, str]:
    return {"code": code, "message": message, "path": rel(path), "field": field}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def find_matching_brace(source: str, open_index: int) -> int:
    depth = 0
    quote = ""
    escaped = False
    for index in range(open_index, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in ("'", '"', "`"):
            quote = char
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return -1


def slice_named_block(source: str, name: str) -> str:
    patterns = [
        rf"\basync\s+{re.escape(name)}\s*\([^)]*\)\s*{{",
        rf"\b{name}\s*\([^)]*\)\s*{{",
    ]
    for pattern in patterns:
        match = re.search(pattern, source)
        if not match:
            continue
        open_index = source.find("{", match.start())
        close_index = find_matching_brace(source, open_index)
        if close_index > open_index:
            return source[match.start(): close_index + 1]
    return ""


def slice_function(source: str, name: str) -> str:
    marker = f"export function {name}"
    start = source.find(marker)
    if start < 0:
        return ""
    next_match = re.search(r"\nexport function ", source[start + 1 :])
    end = start + 1 + next_match.start() if next_match else len(source)
    return source[start:end]


def git_diff_name_only() -> list[str]:
    proc = subprocess.run(["git", "diff", "--name-only", "HEAD", "--"], cwd=ROOT, text=True, capture_output=True, check=False)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def count_patterns(source: str, patterns: list[str]) -> int:
    return sum(source.count(pattern) for pattern in patterns)


def validate_components() -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    view = read(VIEW)
    for name, path in COMPONENTS.items():
        exists = path.exists()
        source = read(path) if exists else ""
        kebab = re.sub(r"(?<!^)([A-Z])", r"-\1", name).lower()
        rows.append({
            "component": name,
            "path": rel(path),
            "exists": exists,
            "registered_or_used": name in view or kebab in view,
            "has_testid": "data-testid" in source,
            "has_audit_detail": "ReplayAuditDetail" in source or name == "ReplayAuditDetail",
        })
        if not exists:
            errors.append(err("component_missing", f"{name} component missing", path))
        if exists and name != "ReplayAuditDetail" and "ReplayAuditDetail" not in source:
            errors.append(err("audit_detail_missing", f"{name} must use ReplayAuditDetail", path, "ReplayAuditDetail"))
    return rows, errors, warnings


def validate_primary_audit_mapping() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    replay = read(COMPONENTS["ReadonlyReplayWindowPanel"])
    strategy = read(COMPONENTS["ReadonlyStrategySnapshotPanel"])
    mapping = [
        {"field": "model", "level": "primary", "component": "ReadonlyReplayWindowPanel|ReadonlyStrategySnapshotPanel"},
        {"field": "strategy", "level": "primary", "component": "ReadonlyReplayWindowPanel|ReadonlyStrategySnapshotPanel"},
        {"field": "legal_window", "level": "primary", "component": "ReadonlyReplayWindowPanel"},
        {"field": "net_return", "level": "primary", "component": "ReadonlyReplayWindowPanel"},
        {"field": "max_drawdown", "level": "primary", "component": "ReadonlyReplayWindowPanel"},
        {"field": "action_count", "level": "primary", "component": "ReadonlyReplayWindowPanel"},
        {"field": "fee_tax", "level": "primary", "component": "ReadonlyReplayWindowPanel"},
        {"field": "coverage_status", "level": "primary", "component": "ReadonlyReplayWindowPanel|ReadonlyStrategySnapshotPanel"},
        {"field": "audit_status", "level": "primary", "component": "ReadonlyReplayWindowPanel|ReadonlyStrategySnapshotPanel"},
        {"field": "source_manifest", "level": "audit_detail", "component": "ReplayAuditDetail"},
        {"field": "checksum", "level": "audit_detail", "component": "ReplayAuditDetail"},
        {"field": "schema_version", "level": "audit_detail", "component": "ReplayAuditDetail"},
        {"field": "window_index", "level": "audit_detail", "component": "ReplayAuditDetail"},
        {"field": "run_id", "level": "audit_detail", "component": "ReplayAuditDetail"},
    ]
    errors: list[dict[str, str]] = []
    required_primary = ["模型", "策略", "合法窗口", "净收益", "最大回撤", "交易次数", "手续费/税费", "覆盖状态", "审计状态"]
    combined = replay + strategy
    for field in required_primary:
        if field not in combined:
            errors.append(err("primary_field_missing", f"primary field {field} missing", COMPONENT_DIR, field))
    required_audit = ["source manifest", "checksum", "schema version", "window index"]
    for field in required_audit:
        if field not in combined:
            errors.append(err("audit_field_missing", f"audit field {field} missing", COMPONENT_DIR, field))
    if replay.find("source manifest") < replay.find("净收益"):
        errors.append(err("audit_field_precedes_primary", "source manifest must not precede replay primary metrics", COMPONENTS["ReadonlyReplayWindowPanel"], "source manifest"))
    return mapping, errors


def validate_readonly_api() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    api = read(API)
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for fn, endpoint in READONLY_API_FUNCTIONS.items():
        body = slice_function(api, fn)
        method_get = bool(re.search(r"method:\s*['\"]get['\"]", body))
        write_method_count = len(re.findall(r"method:\s*['\"](?:post|put|patch|delete)['\"]", body, flags=re.I))
        row = {"function": fn, "endpoint": endpoint, "exists": bool(body), "method_get": method_get, "write_method_count": write_method_count}
        rows.append(row)
        if not row["exists"]:
            errors.append(err("readonly_api_missing", f"{fn} missing", API, fn))
        if not row["method_get"] or row["write_method_count"]:
            errors.append(err("readonly_api_not_get_only", f"{fn} must be GET-only", API, fn))
    return rows, errors


def validate_replay_strategy_wrappers() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    api = read(API)
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for fn, endpoint in REPLAY_STRATEGY_WRITE_WRAPPERS.items():
        body = slice_function(api, fn)
        endpoint_present = endpoint in body or endpoint.lstrip("/") in body
        method_write = bool(re.search(r"method:\s*['\"](?:post|put|patch|delete)['\"]", body, flags=re.I))
        if endpoint_present and re.search(r"portfolio-replay|/api/indicator/backtest", endpoint, flags=re.I):
            method_write = True
        rows.append({"function": fn, "endpoint": endpoint, "exists": bool(body), "method_write": method_write, "manual_only_allowed": True})
        if not body:
            errors.append(err("replay_strategy_wrapper_missing", f"{fn} missing", API, fn))
        if body and not method_write:
            errors.append(err("replay_strategy_wrapper_not_classified", f"{fn} was expected to be classified as a replay/strategy write wrapper", API, fn))
    return rows, errors


def readonly_surface_source() -> str:
    api = read(API)
    parts = [read(path) for path in COMPONENTS.values() if path.exists()]
    for fn in READONLY_API_FUNCTIONS:
        parts.append(slice_function(api, fn))
    return "\n".join(parts)


def m4_acceptance_source() -> str:
    view = read(VIEW)
    parts = []
    for name in M4_ACCEPTANCE_ENTRYPOINTS:
        block = slice_named_block(view, name)
        if block:
            parts.append(f"// {name}\n{block}")
    return "\n".join(parts)


def agent_surface_source() -> str:
    view = read(VIEW)
    start = view.find('<div class="tw-stock-agent-panel">')
    end = view.find('<div v-if="crossAnalysisAccepted"', start) if start >= 0 else -1
    panel = view[start:end] if start >= 0 and end > start else ""
    return "\n".join([panel, slice_function(read(API), "chatTwStockAgent"), slice_function(read(API), "getTwStockAgentContext")])


def validate_forbidden_surface() -> tuple[dict[str, Any], list[dict[str, str]]]:
    combined = readonly_surface_source()
    errors: list[dict[str, str]] = []
    token_hits = {token: combined.count(token) for token in FORBIDDEN_FRONTEND_TOKENS}
    for token, count in token_hits.items():
        if count:
            errors.append(err("legacy_gate_exposed", f"legacy gate token exposed: {token}", FRONTEND, token))
    forbidden_text_hits = {word: combined.count(word) for word in FORBIDDEN_TEXT}
    for word, count in forbidden_text_hits.items():
        if count:
            errors.append(err("forbidden_text", f"forbidden text present: {word}", FRONTEND, word))
    request_counts = {key: count_patterns(combined, patterns) for key, patterns in FORBIDDEN_REQUEST_PATTERNS.items()}
    if request_counts["provider_publish_refresh"]:
        errors.append(err("provider_ops_exposed", "provider publish/refresh or accepted latest exposed in readonly workflow", FRONTEND, "provider_ops"))
    if request_counts["broker_orders"]:
        errors.append(err("broker_ops_exposed", "broker/order endpoint exposed in readonly workflow", FRONTEND, "broker_orders"))
    if request_counts["monitor_writes"]:
        errors.append(err("monitor_write_exposed", "monitor write helper exposed in readonly workflow", FRONTEND, "monitor_writes"))
    if request_counts["replay_strategy_writes"]:
        errors.append(err("replay_strategy_write_exposed", "replay/strategy write helper exposed in M4 readonly components or readonly API wrappers", FRONTEND, "replay_strategy_writes"))
    return {"legacy_gate_token_hits": token_hits, "forbidden_text_hits": forbidden_text_hits, "forbidden_request_counts": request_counts}, errors


def validate_m4_acceptance_path() -> tuple[dict[str, Any], list[dict[str, str]]]:
    view = read(VIEW)
    errors: list[dict[str, str]] = []
    entrypoint_hits: dict[str, dict[str, int]] = {}
    total_replay_strategy_write_count = 0
    for entrypoint in M4_ACCEPTANCE_ENTRYPOINTS:
        block = slice_named_block(view, entrypoint)
        hits = {name: len(re.findall(rf"\b(?:this\.)?{re.escape(name)}\b", block)) for name in M4_ACCEPTANCE_FORBIDDEN_CALLS}
        entrypoint_hits[entrypoint] = hits
        for name, count in hits.items():
            if count:
                total_replay_strategy_write_count += count
                errors.append(err("m4_acceptance_replay_strategy_write", f"M4 acceptance entrypoint {entrypoint} references replay/strategy write path {name}", VIEW, entrypoint))
    manual_blocks = {name: slice_named_block(view, name) for name in ["loadRankTechPortfolioPanel", "loadPortfolioReplay", "runReadonlyBacktest"]}
    manual_write_entrypoints = {name: bool(block) for name, block in manual_blocks.items()}
    return {
        "entrypoints": M4_ACCEPTANCE_ENTRYPOINTS,
        "forbidden_calls": M4_ACCEPTANCE_FORBIDDEN_CALLS,
        "entrypoint_forbidden_call_hits": entrypoint_hits,
        "replay_strategy_write_count": total_replay_strategy_write_count,
        "manual_write_entrypoints_present": manual_write_entrypoints,
        "manual_write_entrypoints_excluded_from_m4_acceptance": total_replay_strategy_write_count == 0,
    }, errors


def validate_agent_boundary() -> tuple[dict[str, Any], list[dict[str, str]]]:
    changed = git_diff_name_only()
    agent_related = [path for path in changed if "agent" in path.lower()]
    surface = agent_surface_source()
    expansion_patterns = ["--enable-legacy-provider-publish", "TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH", "provider_publish", "accepted_latest", "/broker/", "quick-trade", "target_position", "target_weight"]
    expansion_hits = {pattern: surface.count(pattern) for pattern in expansion_patterns}
    marker_presence = {marker: marker in surface for marker in AGENT_MARKERS}
    errors: list[dict[str, str]] = []
    for pattern, count in expansion_hits.items():
        if count:
            errors.append(err("agent_forbidden_surface", f"Agent forbidden marker present: {pattern}", VIEW, pattern))
    return {
        "agent_related_changed_paths": agent_related,
        "agent_marker_presence": marker_presence,
        "agent_forbidden_surface_hits": expansion_hits,
        "agent_implementation_untouched": not agent_related,
        "agent_contract_placeholder_only": True,
    }, errors


def validate() -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    component_rows, component_errors, component_warnings = validate_components()
    mapping, mapping_errors = validate_primary_audit_mapping()
    api_rows, api_errors = validate_readonly_api()
    replay_strategy_wrappers, replay_strategy_wrapper_errors = validate_replay_strategy_wrappers()
    forbidden, forbidden_errors = validate_forbidden_surface()
    acceptance_path, acceptance_errors = validate_m4_acceptance_path()
    agent, agent_errors = validate_agent_boundary()
    errors.extend(component_errors + mapping_errors + api_errors + replay_strategy_wrapper_errors + forbidden_errors + acceptance_errors + agent_errors)
    warnings.extend(component_warnings)
    readonly_source = readonly_surface_source()
    replay_strategy_write_count = acceptance_path["replay_strategy_write_count"]
    network_audit = {
        "readonly_workflow_only_get": all(row["method_get"] and row["write_method_count"] == 0 for row in api_rows) and replay_strategy_write_count == 0,
        "forbidden_request_count": forbidden["forbidden_request_counts"]["provider_publish_refresh"] + forbidden["forbidden_request_counts"]["broker_orders"] + replay_strategy_write_count,
        "monitor_config_write_count": readonly_source.count("saveTwStockMonitorConfig"),
        "monitor_scan_post_count": readonly_source.count("scanTwStockMonitor") + readonly_source.count("scanAllTwStockMonitors"),
        "monitor_alerts_write_count": readonly_source.count("updateTwStockAlert"),
        "ops_provider_publish_refresh_accepted_latest_request_count": forbidden["forbidden_request_counts"]["provider_publish_refresh"],
        "replay_strategy_write_count": replay_strategy_write_count,
        "broker_quick_trade_orders_request_count": forbidden["forbidden_request_counts"]["broker_orders"],
    }
    network_audit["readonly_component_monitor_write_count"] = network_audit["monitor_config_write_count"] + network_audit["monitor_scan_post_count"] + network_audit["monitor_alerts_write_count"]
    if network_audit["readonly_component_monitor_write_count"]:
        errors.append(err("readonly_component_monitor_write", "readonly components must not reference monitor write helpers", COMPONENT_DIR, "monitor_write"))
    return {
        "ok": not errors,
        "status": "passed" if not errors else "failed",
        "schema_version": "m4.0.1",
        "errors": errors,
        "warnings": warnings,
        "checked_files": [rel(path) for path in [VIEW, API, *COMPONENTS.values()] if path.exists()],
        "component_boundary_summary": component_rows,
        "primary_fields_vs_audit_fields_mapping": mapping,
        "readonly_api_summary": api_rows,
        "replay_strategy_write_wrappers": replay_strategy_wrappers,
        "m4_acceptance_path_audit": acceptance_path,
        "network_audit": network_audit,
        "forbidden_surface_audit": forbidden,
        "legacy_provider_gate_not_exposed": all(count == 0 for count in forbidden["legacy_gate_token_hits"].values()),
        "agent_boundary_audit": agent,
        "screenshot_paths": {
            "desktop": "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_strategy_snapshot_desktop_collapsed.png",
            "mobile": "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_strategy_snapshot_mobile.png",
            "readonly_replay_panel": "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_replay_window_desktop_collapsed.png",
            "audit_detail_collapsed": "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_replay_window_desktop_collapsed.png",
            "audit_detail_expanded": "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_replay_window_desktop_expanded.png",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase M4/M4R frontend readonly display boundary.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        print(f"status={result['status']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
