#!/usr/bin/env python3
"""Scoped static safety scan for Phase B2 LTR default readonly product closure."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_tw/experiments/ltr_baseline_conservative_tuning/phaseb2_product_closure"
OUT_PATH = OUT_DIR / "phaseb2_static_safety_scan.json"
BOUNDARY_TEXT = "仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。"

TARGETS = {
    "backend_route_slice": ROOT / "backend/app/routes/tw_stock.py",
    "backend_service": ROOT / "backend/app/services/tw_ltr_optional_sim_strategy.py",
    "frontend_api": ROOT / "frontend/src/api/tw-stock.js",
    "frontend_page": ROOT / "frontend/src/views/tw-stock-monitor/index.vue",
}

FORBIDDEN_PATTERNS = {
    "monitor_config_write_count": [r"monitor/config[^\n]{0,160}method:\s*['\"](?:post|put|patch|delete)['\"]", r"saveTwStockMonitorConfig\("],
    "monitor_scan_post_count": [r"monitor/scan[^\n]{0,160}method:\s*['\"]post['\"]", r"scanTwStockMonitor\("],
    "monitor_alerts_write_count": [r"monitor/alerts[^\n]{0,160}method:\s*['\"](?:post|put|patch|delete)['\"]", r"updateTwStockAlert\("],
    "ops_dry_run_post_count": [r"quant/ops/[^\n]{0,160}method:\s*['\"]post['\"]", r"triggerQlibOptionCDryRun\("],
    "broker_quick_trade_orders_count": [r"/api/(?:quick[-_/ ]trade|broker|orders?)", r"submit order", r"提交订单", r"提交訂單", r"下单", r"下單"],
    "target_position_weight_count": [r"target[_-]?position", r"target[_-]?weight", r"目标仓位", r"目標倉位", r"目标权重", r"目標權重"],
    "provider_refresh_publish_count": [r"provider[^\n]{0,80}(refresh|publish)", r"refresh-provider", r"provider-refresh", r"正式发布", r"正式發布"],
    "accepted_latest_switch_count": [r"/accepted[-_ ]latest", r"accepted[-_ ]latest[^\n]{0,80}(write|publish|POST|PUT|PATCH|DELETE)"],
    "unsafe_buy_sell_hold_semantics_count": [r"建议买入", r"建議買入", r"建议卖出", r"建議賣出", r"建议持有", r"建議持有", r"立即买入", r"立即卖出", r"推荐策略", r"推薦策略", r"更优策略", r"更優策略", r"最佳策略", r"预计收益", r"預計收益", r"胜率", r"勝率", r"上涨概率", r"上漲概率"],
}


def route_slice(source: str) -> str:
    marker = '@tw_stock_bp.route("/ltr-optional-sim-strategies"'
    if marker not in source:
        return source
    chunk = source.split(marker, 1)[1]
    return chunk.split('@tw_stock_bp.route("/cross-analysis/symbol', 1)[0]


def frontend_page_slice(source: str) -> str:
    parts = []
    for marker in [
        '<section class="ltr-optional-sim-strategy"',
        'ltrOptionalSimStrategies ()',
        'async loadLtrOptionalSimStrategies ()',
        '.ltr-optional-sim-strategy',
    ]:
        if marker in source:
            start = source.index(marker)
            parts.append(source[start:start + 5000])
    return "\n".join(parts)


def scoped_text(name: str, text: str) -> str:
    if name == "backend_route_slice":
        return route_slice(text)
    if name == "frontend_page":
        return frontend_page_slice(text)
    if name == "frontend_api":
        match = re.search(r"export function getTwStockLTROptionalSimStrategies[\s\S]*?\n}\n", text)
        return match.group(0) if match else text
    return text


def count_patterns(text: str, patterns: list[str]) -> int:
    scrubbed = text.replace(BOUNDARY_TEXT, "")
    return sum(len(re.findall(pattern, scrubbed, flags=re.IGNORECASE)) for pattern in patterns)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scanned = {}
    combined = []
    for name, target_path in TARGETS.items():
        raw = target_path.read_text(encoding="utf-8")
        scoped = scoped_text(name, raw)
        scanned[name] = {"path": str(target_path.relative_to(ROOT)), "scoped_chars": len(scoped)}
        combined.append(scoped)
    text = "\n".join(combined)

    counts = {key: count_patterns(text, patterns) for key, patterns in FORBIDDEN_PATTERNS.items()}
    endpoint_get_only = 'url: `${BASE_URL}/ltr-optional-sim-strategies`' in text and "method: 'get'" in text
    route_source = TARGETS["backend_route_slice"].read_text(encoding="utf-8")
    route_get_only = '@tw_stock_bp.route("/ltr-optional-sim-strategies", methods=["GET"])' in route_source
    result = {
        "ok": all(value == 0 for value in counts.values()) and endpoint_get_only and route_get_only,
        "scope": "Phase B2 LTR default readonly endpoint/panel/service only; existing unrelated app writes are out of scope.",
        "schema_version": "phaseb2_ltr_default_static_safety_scan_v1",
        "counts": counts,
        "forbidden_request_count": sum(counts.values()),
        "endpoint_get_only": endpoint_get_only,
        "route_get_only": route_get_only,
        "boundary_text_whitelisted_exactly": BOUNDARY_TEXT,
        "scanned_targets": scanned,
    }
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
