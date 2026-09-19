#!/usr/bin/env python3
"""Build an offline TradingAgents readonly analysis artifact from fixture state."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "data_tw/golden_samples/tradingagents_readonly_analysis/pass_minimal/mock_raw_state.json"
DEFAULT_OUT_DIR = ROOT / "data_tw/golden_samples/tradingagents_readonly_analysis/pass_minimal"

ANALYSIS_NAME = "tradingagents_readonly"
ARTIFACT_TYPE = "tradingagents_readonly_analysis"
SCHEMA_VERSION = "tradingagents_readonly_analysis_v1"
REPORT_SCHEMA_VERSION = "tradingagents_sanitized_report_v1"
DISCLAIMER = "仅供研究观察，不构成交易建议；不代表买卖、仓位、胜率或收益承诺。"
CONTROLLED_REAL_RUN_SUMMARY = (
    "TradingAgents 受控真实运行已完成；展示 artifact 仅保留运行元数据、数据限制与人工复核问题，"
    "外部框架原始正文不作为本项目策略证据。"
)
CONTROLLED_REAL_RUN_LIMITATIONS = [
    "受控真实运行会调用 LLM 与外部数据工具，输出仅作为人工复核线索。",
    "外部框架原始正文已从展示 artifact 移除；raw_untrusted 文件仅供审查流程复核。",
]
CONTROLLED_REAL_RUN_QUESTIONS = [
    "外部研究材料中哪些事实可由本项目只读数据独立验证？",
    "是否存在与当前 qlib/LTR 候选上下文冲突的事实或口径？",
]
SECTION_ALIASES = {
    "market": ("market", "technical", "行情", "市场", "市場", "技术", "技術"),
    "news": ("news", "headline", "新闻", "新聞", "消息"),
    "fundamental": ("fundamental", "financial", "earnings", "revenue", "基本面", "财报", "財報", "营收", "營收"),
    "social": ("social", "sentiment", "社群", "舆情", "輿情", "情绪", "情緒"),
    "debate": ("debate", "discussion", "bull", "bear", "辩论", "辯論", "讨论", "討論"),
    "risk": ("risk", "风险", "風險"),
}

FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in (
        ("target_position", r"\btarget_position\b|目标仓位|目標倉位"),
        ("target_weight", r"\btarget_weight\b|目标权重|目標權重"),
        ("buy_now", r"\bbuy_now\b|建议买入|建議買入|应该买入|應該買入|应买入|應買入"),
        ("sell_now", r"\bsell_now\b|建议卖出|建議賣出|应该卖出|應該賣出|应卖出|應賣出"),
        ("raw_rating", r"\b(?:Buy|Sell|Hold|Overweight|Underweight)\b"),
        ("transaction_proposal", r"final\s+transaction\s+proposal|transaction\s+proposal"),
        ("position_sizing", r"position\s+sizing|仓位大小|倉位大小"),
        ("stop_loss", r"stop\s+loss|止损|止損"),
        ("price_target", r"price\s+target|target\s+price|目标价|目標價"),
        ("entry_price", r"entry\s+price|入场价|入場價"),
        (
            "trading_action_semantics",
            r"续抱|續抱|追价|追價|追高|加码|加碼|减码|減碼|进场|進場|退场|退場|买入|買入|买进|買進|卖出|賣出|"
            r"持有|核心部位|核心仓位|核心倉位|新增曝险|新增曝險|曝险|曝險|满仓|滿倉|重仓|重倉|低配|超配|"
            r"停损|停損|止损|止損|停利|移动停利|移動停利|"
            r"目标权重|目標權重|权重|權重|"
            r"\d+\s*%\s*[–-]\s*\d+\s*%|"
            r"交易含义|交易含義|实务交易建议|實務交易建議|交易计划|交易計畫",
        ),
        ("guaranteed_return", r"guaranteed\s+return|保证收益|保證收益"),
        ("win_rate_promise", r"win\s+rate\s+promise|胜率承诺|勝率承諾"),
        ("broker_order_id", r"\bbroker_order_id\b"),
        ("production_ready", r"\bproduction_ready\b\s*[:=]\s*true"),
        ("default_strategy_selected", r"\bdefault_strategy_selected\b\s*[:=]\s*true"),
    )
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_symbol(raw: dict[str, Any]) -> str:
    symbol = str(raw.get("symbol") or raw.get("ticker") or raw.get("instrument") or "").strip()
    if symbol.startswith("TW") and symbol[2:].isdigit():
        symbol = symbol[2:]
    if symbol.endswith(".TW"):
        symbol = symbol[:-3]
    return symbol


def normalize_instrument(raw: dict[str, Any], symbol: str) -> str:
    instrument = str(raw.get("instrument") or "").strip()
    if instrument:
        return instrument
    return f"TW{symbol}" if symbol else ""


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def text_list(value: Any) -> list[str]:
    return [str(item).strip() for item in as_list(value) if str(item).strip()]


def collect_text_parts(value: Any) -> list[str]:
    parts: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            parts.append(str(key))
            parts.extend(collect_text_parts(item))
    elif isinstance(value, list):
        for item in value:
            parts.extend(collect_text_parts(item))
    elif isinstance(value, (str, int, float, bool)) and value is not None:
        text = str(value).strip()
        if text:
            parts.append(text)
    return parts


def bool_pattern(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE) is not None


def density_bucket(char_count: int) -> str:
    if char_count <= 0:
        return "none"
    if char_count < 400:
        return "short"
    if char_count < 1600:
        return "medium"
    return "long"


def bucketed_char_count(char_count: int) -> int:
    if char_count <= 0:
        return 0
    return min(20, (char_count + 249) // 250)


def build_research_labels(raw_symbol: dict[str, Any]) -> dict[str, Any]:
    parts = collect_text_parts(raw_symbol)
    source_text = "\n".join(parts)
    lowered = source_text.lower()
    char_count = len(source_text)
    forbidden_categories = {
        name
        for name, pattern in FORBIDDEN_PATTERNS
        if pattern.search(source_text)
    }
    section_presence = {
        section: any(alias.lower() in lowered for alias in aliases)
        for section, aliases in SECTION_ALIASES.items()
    }
    has_numeric_context = any(ch.isdigit() for ch in source_text)
    has_event_context = bool_pattern(source_text, r"event|earnings|revenue|shipment|guidance|headline|公告|事件|法说|法說|财报|財報|营收|營收|新闻|新聞")
    has_data_gap_language = bool_pattern(source_text, r"missing|stale|gap|unavailable|insufficient|缺失|缺口|不足|不可得|未提供|資料不足|数据不足")
    return {
        "source_section_presence": section_presence,
        "source_text_density_bucket": density_bucket(char_count),
        "evidence_quality_flags": {
            "has_numeric_context": has_numeric_context,
            "has_event_context": has_event_context,
            "has_data_gap_language": has_data_gap_language,
        },
        "attention_flags": {
            "market_volatility_attention": bool_pattern(source_text, r"volatility|volatile|波动|波動|震荡|震盪"),
            "external_event_attention": bool_pattern(source_text, r"event|headline|news|公告|事件|新闻|新聞|消息"),
            "fundamentals_attention": bool_pattern(source_text, r"fundamental|earnings|revenue|margin|基本面|财报|財報|营收|營收|毛利"),
            "liquidity_attention": bool_pattern(source_text, r"liquidity|volume|turnover|流动性|流動性|成交量|量能"),
        },
        "review_queue_flags": {
            "needs_human_fact_check": bool(forbidden_categories) or has_data_gap_language or has_event_context,
            "needs_candidate_context_compare": has_event_context or section_presence["risk"],
        },
        "sanitizer_counters": {
            "source_section_count": sum(1 for present in section_presence.values() if present),
            "forbidden_term_category_count": len(forbidden_categories),
            "raw_text_chars_bucketed": bucketed_char_count(char_count),
        },
    }


def strip_forbidden_text(text: str) -> tuple[str, list[str]]:
    found: list[str] = []
    sanitized = text
    for name, pattern in FORBIDDEN_PATTERNS:
        if pattern.search(sanitized):
            found.append(name)
            sanitized = pattern.sub("外部框架交易性标签已移除", sanitized)
    return sanitized.strip(), sorted(set(found))


def sanitize_points(values: Any) -> tuple[list[str], list[str]]:
    clean: list[str] = []
    found: list[str] = []
    for item in text_list(values):
        sanitized, item_found = strip_forbidden_text(item)
        found.extend(item_found)
        if sanitized:
            clean.append(sanitized)
    return clean, sorted(set(found))


def sanitize_source_context(value: Any) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(value, dict):
        return {}, []
    clean: dict[str, Any] = {}
    found: list[str] = []
    for key, raw_item in value.items():
        key_text = str(key)
        sanitized_key, key_found = strip_forbidden_text(key_text)
        found.extend(key_found)
        if key_found or not sanitized_key:
            continue
        if isinstance(raw_item, (str, int, float, bool)) or raw_item is None:
            if isinstance(raw_item, str):
                sanitized_value, value_found = strip_forbidden_text(raw_item)
                found.extend(value_found)
                clean[sanitized_key] = sanitized_value
            else:
                clean[sanitized_key] = raw_item
    return clean, sorted(set(found))


def source_symbols(raw_state: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(raw_state.get("symbols"), list):
        return [item for item in raw_state["symbols"] if isinstance(item, dict)]
    if isinstance(raw_state.get("symbol_analyses"), list):
        return [item for item in raw_state["symbol_analyses"] if isinstance(item, dict)]
    return []


def build_sanitized_report(
    raw_state: dict[str, Any],
    run_id: str,
    signal_asof: str,
    target_date: str,
    run_mode: str = "fixture_dry_run",
) -> tuple[dict[str, Any], dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    removed_terms: list[str] = []
    for raw_symbol in source_symbols(raw_state):
        symbol = normalize_symbol(raw_symbol)
        instrument = normalize_instrument(raw_symbol, symbol)
        source_context, context_removed = sanitize_source_context(raw_symbol.get("source_context"))
        if run_mode == "controlled_real_run":
            research_labels = build_research_labels(raw_symbol)
            research_summary = CONTROLLED_REAL_RUN_SUMMARY
            bull_points: list[str] = []
            bear_points: list[str] = []
            risk_points: list[str] = []
            data_limitations = CONTROLLED_REAL_RUN_LIMITATIONS
            questions = CONTROLLED_REAL_RUN_QUESTIONS
            removed_terms.extend(["controlled_real_run_raw_text"] + context_removed)
            external_sections_removed = True
        else:
            research_summary, summary_removed = strip_forbidden_text(str(raw_symbol.get("research_summary") or raw_symbol.get("summary") or ""))
            bull_points, bull_removed = sanitize_points(raw_symbol.get("bull_points"))
            bear_points, bear_removed = sanitize_points(raw_symbol.get("bear_points"))
            risk_points, risk_removed = sanitize_points(raw_symbol.get("risk_review_points") or raw_symbol.get("risks"))
            data_limitations, data_removed = sanitize_points(raw_symbol.get("data_limitations"))
            questions, question_removed = sanitize_points(raw_symbol.get("human_review_questions"))
            removed_terms.extend(summary_removed + bull_removed + bear_removed + risk_removed + data_removed + question_removed + context_removed)
            external_sections_removed = False
        symbols.append(
            {
                "symbol": symbol,
                "instrument": instrument,
                "source_context": source_context,
                "research_summary": research_summary,
                "bull_points": bull_points,
                "bear_points": bear_points,
                "risk_review_points": risk_points,
                "data_limitations": data_limitations,
                "human_review_questions": questions,
                "forbidden_decision_removed": True,
                "raw_decision_label_removed": True,
                "external_sections_removed": external_sections_removed,
                **({"research_labels": research_labels} if run_mode == "controlled_real_run" else {}),
            }
        )
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "run_id": run_id,
        "signal_asof": signal_asof,
        "target_date": target_date,
        "symbols": symbols,
        "research_only_disclaimer": DISCLAIMER,
    }
    unique_removed = sorted(set(removed_terms))
    audit = {
        "removed_term_count": len(unique_removed),
        "removed_categories": ["external_framework_labels"] if unique_removed else [],
        "symbol_count": len(symbols),
    }
    return report, audit


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# TradingAgents Readonly Analysis",
        "",
        report["research_only_disclaimer"],
        "",
        f"- run_id: {report['run_id']}",
        f"- signal_asof: {report['signal_asof']}",
        f"- target_date: {report['target_date']}",
        "",
    ]
    for item in report.get("symbols", []):
        if item.get("external_sections_removed") is True:
            lines.extend(
                [
                    f"## {item.get('instrument', '')}",
                    "",
                    str(item.get("research_summary", "")),
                    "",
                    "### 外部研究段落",
                    "- 外部框架原始正文已从展示 artifact 移除；仅保留 raw_untrusted 审查材料。",
                    "",
                    "### 数据限制",
                ]
            )
            lines.extend(f"- {point}" for point in item.get("data_limitations", []))
            lines.append("")
            lines.append("### 人工复盘问题")
            lines.extend(f"- {point}" for point in item.get("human_review_questions", []))
            lines.append("")
            continue
        lines.extend(
            [
                f"## {item.get('instrument', '')}",
                "",
                str(item.get("research_summary", "")),
                "",
                "### 利多论点",
            ]
        )
        lines.extend(f"- {point}" for point in item.get("bull_points", []))
        lines.append("")
        lines.append("### 利空论点")
        lines.extend(f"- {point}" for point in item.get("bear_points", []))
        lines.append("")
        lines.append("### 风险复盘点")
        lines.extend(f"- {point}" for point in item.get("risk_review_points", []))
        lines.append("")
        lines.append("### 数据限制")
        lines.extend(f"- {point}" for point in item.get("data_limitations", []))
        lines.append("")
        lines.append("### 人工复盘问题")
        lines.extend(f"- {point}" for point in item.get("human_review_questions", []))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_claim_support_audit(report: dict[str, Any]) -> dict[str, Any]:
    claims: list[dict[str, Any]] = []
    for item in report.get("symbols", []):
        symbol = item.get("symbol", "")
        for field in ("research_summary", "bull_points", "bear_points", "risk_review_points", "data_limitations", "human_review_questions"):
            value = item.get(field)
            entries = value if isinstance(value, list) else [value]
            for entry in entries:
                text = str(entry or "").strip()
                if text:
                    claims.append(
                        {
                            "symbol": symbol,
                            "field": field,
                            "claim": text,
                            "support_status": "fixture_context_only",
                            "review_required": True,
                        }
                    )
    return {
        "ok": True,
        "claim_count": len(claims),
        "claims": claims,
        "notes": "TA1 offline fixture builder does not call external data providers or LLMs.",
    }


def build_forbidden_semantics_audit(sanitized_text: str, raw_files: list[str]) -> dict[str, Any]:
    blocked: list[dict[str, str]] = []
    for name, pattern in FORBIDDEN_PATTERNS:
        if pattern.search(sanitized_text):
            blocked.append({"pattern": name, "file": "sanitized_report", "match": pattern.pattern})
    return {
        "ok": not blocked,
        "checked_files": ["sanitized_report.md", "sanitized_report.json", "manifest.json"],
        "blocked_terms_found": blocked,
        "raw_untrusted_files_excluded_from_display": raw_files,
        "forbidden_patterns": [name for name, _pattern in FORBIDDEN_PATTERNS],
    }


def build_artifact(
    *,
    fixture_path: Path,
    output_dir: Path,
    run_id: str | None = None,
    quality_status: str | None = None,
    write_raw: bool = True,
) -> dict[str, Any]:
    raw_state = read_json(fixture_path)
    run_id = run_id or str(raw_state.get("run_id") or fixture_path.parent.name)
    signal_asof = str(raw_state.get("signal_asof") or raw_state.get("asof") or "")
    target_date = str(raw_state.get("target_date") or signal_asof)
    selected_analysts = text_list(raw_state.get("selected_analysts")) or ["market", "news"]
    run_mode = str(raw_state.get("run_mode") or "fixture_dry_run")
    safety = raw_state.get("safety") if isinstance(raw_state.get("safety"), dict) else {}
    runtime_paths = raw_state.get("runtime_paths") if isinstance(raw_state.get("runtime_paths"), dict) else {}
    raw_files: list[str] = []

    report, sanitizer_audit = build_sanitized_report(raw_state, run_id, signal_asof, target_date, run_mode)
    report_md = markdown_report(report)
    sanitized_blob = json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n" + report_md
    forbidden_audit = build_forbidden_semantics_audit(sanitized_blob, ["raw_tradingagents_state.json", "raw_complete_report.md"] if write_raw else [])
    claim_audit = build_claim_support_audit(report)
    final_quality = quality_status or "pass"
    if not forbidden_audit["ok"]:
        final_quality = "failed"

    output_dir.mkdir(parents=True, exist_ok=True)
    if write_raw:
        raw_payload = {
            "raw_untrusted": True,
            "display_allowed": False,
            "source_fixture": rel(fixture_path),
            "state": raw_state,
        }
        write_json(output_dir / "raw_tradingagents_state.json", raw_payload)
        raw_report = str(raw_state.get("raw_complete_report") or "raw_untrusted fixture report omitted")
        (output_dir / "raw_complete_report.md").write_text(
            "---\nraw_untrusted: true\ndisplay_allowed: false\n---\n\n" + raw_report.rstrip() + "\n",
            encoding="utf-8",
        )
        raw_files = ["raw_tradingagents_state.json", "raw_complete_report.md"]

    write_json(output_dir / "sanitized_report.json", report)
    (output_dir / "sanitized_report.md").write_text(report_md, encoding="utf-8")
    write_json(output_dir / "claim_support_audit.json", claim_audit)
    write_json(output_dir / "forbidden_semantics_audit.json", forbidden_audit)

    manifest = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "analysis_name": ANALYSIS_NAME,
        "run_id": run_id,
        "created_at": str(raw_state.get("created_at") or utc_now()),
        "source": {
            "project": "TradingAgents",
            "project_path": "third_party/tradingagents",
            "version": str(raw_state.get("tradingagents_version") or "fixture"),
            "vendored": True,
            "upstream_reference": str(raw_state.get("upstream_reference") or "fixture_mock_state"),
            "selected_analysts": selected_analysts,
        },
        "run_mode": run_mode,
        "manual_run_only": bool(raw_state.get("manual_run_only", True)),
        "no_latest_pointer_update": bool(raw_state.get("no_latest_pointer_update", True)),
        "runtime_paths": runtime_paths,
        "input_artifacts": raw_state.get("input_artifacts") if isinstance(raw_state.get("input_artifacts"), list) else [],
        "input_symbols": [item.get("symbol") for item in report.get("symbols", [])],
        "signal_asof": signal_asof,
        "target_date": target_date,
        "readonly_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "production_trade_enabled": False,
        "no_replay": True,
        "no_strategy_return_conclusion": True,
        "not_valid_strategy_evidence": True,
        "not_valid_default_switch_evidence": True,
        "no_openai_call": bool(safety.get("no_openai_call", True)),
        "no_network_call": bool(safety.get("no_network_call", True)),
        "no_tradingagents_graph_call": bool(safety.get("no_tradingagents_graph_call", True)),
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor_write": True,
        "no_broker_quick_trade_order": True,
        "raw_untrusted_files": raw_files,
        "output_report": "sanitized_report.md",
        "quality_status": final_quality,
        "claim_support_audit": "claim_support_audit.json",
        "forbidden_semantics_audit": "forbidden_semantics_audit.json",
        "sanitizer_audit": sanitizer_audit,
    }
    write_json(output_dir / "manifest.json", manifest)
    write_json(
        output_dir / "input_artifact_index.json",
        {
            "run_id": run_id,
            "input_artifacts": manifest["input_artifacts"],
            "fixture": rel(fixture_path),
            "readonly_artifact_only": True,
        },
    )
    return {"ok": forbidden_audit["ok"], "artifact_dir": rel(output_dir), "quality_status": final_quality}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build offline TradingAgents readonly analysis artifact from fixture raw state.")
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE), help="Fixture/mock raw state JSON path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR), help="Artifact output directory.")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--quality-status", choices=["pass", "warning", "failed"], default=None)
    parser.add_argument("--no-raw", action="store_true", help="Do not emit raw_untrusted review files.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = build_artifact(
        fixture_path=Path(args.fixture),
        output_dir=Path(args.output_dir),
        run_id=args.run_id,
        quality_status=args.quality_status,
        write_raw=not args.no_raw,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={str(result['ok']).lower()}")
        print(f"artifact_dir={result['artifact_dir']}")
        print(f"quality_status={result['quality_status']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
