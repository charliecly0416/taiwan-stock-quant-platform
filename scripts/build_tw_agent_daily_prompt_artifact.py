#!/usr/bin/env python3
"""Build TW Agent DailyAgentPromptArtifact from read-only local source JSON."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Tuple

try:
    from validate_tw_agent_daily_prompt_artifact import (
        BASE_MODEL_ID,
        EXECUTION_PRICE_MODE,
        STRATEGY_RULE,
        TREATMENT_MODEL_ID,
        compute_checksum,
        validate_artifact,
    )
except ModuleNotFoundError:
    from scripts.validate_tw_agent_daily_prompt_artifact import (
        BASE_MODEL_ID,
        EXECUTION_PRICE_MODE,
        STRATEGY_RULE,
        TREATMENT_MODEL_ID,
        compute_checksum,
        validate_artifact,
    )


SOURCE_FILENAMES = {
    "current_strategy_context": "current_strategy_context.json",
    "readonly_strategy_snapshot": "readonly_strategy_snapshot.json",
    "readonly_replay_window": "readonly_replay_window.json",
    "paper_portfolio_decision": "paper_portfolio_decision.json",
    "productization_status": "productization_status.json",
}

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SOURCES = ("current_strategy_context", "readonly_strategy_snapshot")
RESEARCH_ONLY_DISCLAIMER = "仅供研究观察，不构成交易建议；qlib score 是横截面排序分数，不是收益率、胜率、涨幅或买入概率。"
TRADINGAGENTS_SOURCE_NAME = "tradingagents_readonly_analysis"


class BuildError(RuntimeError):
    pass


def read_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BuildError(f"failed_to_read_json:{path}:{exc}") from exc
    if not isinstance(payload, dict):
        raise BuildError(f"expected_json_object:{path}")
    return payload


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BuildError(f"failed_to_load_module:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_dir_from_args(args: argparse.Namespace) -> Path:
    if args.input_fixture:
        return Path(args.input_fixture) / "source_artifacts"
    if args.source_dir:
        return Path(args.source_dir)
    raise BuildError("one of --input-fixture or --source-dir is required")


def load_sources(source_dir: Path) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Path]]:
    sources: Dict[str, Dict[str, Any]] = {}
    paths: Dict[str, Path] = {}
    missing: List[str] = []
    for name, filename in SOURCE_FILENAMES.items():
        path = source_dir / filename
        if path.exists():
            sources[name] = read_json(path)
            paths[name] = path
        elif name in REQUIRED_SOURCES:
            missing.append(str(path))
    if missing:
        raise BuildError("missing_required_source_artifacts:" + ",".join(missing))
    return sources, paths


def require_value(name: str, value: Any, expected: Any) -> None:
    if value != expected:
        raise BuildError(f"{name}: expected {expected!r}, got {value!r}")


def validate_source_alignment(sources: Dict[str, Dict[str, Any]]) -> List[str]:
    current = sources["current_strategy_context"]
    snapshot = sources["readonly_strategy_snapshot"]
    warnings: List[str] = []

    signal_asof = current.get("signal_asof")
    target_date = current.get("target_date")
    if not signal_asof or not target_date:
        raise BuildError("current_strategy_context_missing_signal_asof_or_target_date")

    for name, payload in sources.items():
        source_signal_asof = payload.get("signal_asof")
        source_target_date = payload.get("target_date")
        if source_signal_asof and source_signal_asof != signal_asof:
            raise BuildError(f"source_asof_mismatch:{name}:{source_signal_asof}!={signal_asof}")
        if source_target_date and source_target_date != target_date:
            raise BuildError(f"source_target_date_mismatch:{name}:{source_target_date}!={target_date}")
        if (payload.get("validation") or {}).get("ok") is False:
            warnings.append(f"{name}_validation_not_ok")

    require_value("model_ids.base", (current.get("model_ids") or {}).get("base"), BASE_MODEL_ID)
    require_value("model_ids.treatment", (current.get("model_ids") or {}).get("treatment"), TREATMENT_MODEL_ID)
    require_value("strategy_rule", current.get("strategy_rule"), STRATEGY_RULE)
    require_value("snapshot.strategy_rule", snapshot.get("strategy_rule"), STRATEGY_RULE)
    require_value("execution_price_mode", current.get("execution_price_mode"), EXECUTION_PRICE_MODE)

    execution_status = current.get("execution_price_status")
    if execution_status in {"pending", "unavailable"}:
        warnings.append(f"execution_price_{execution_status}")
    freshness = current.get("freshness") or {}
    if freshness.get("status") in {"mixed", "pending", "unavailable"}:
        warnings.append(f"freshness_{freshness.get('status')}")
    return warnings


def compact_list(value: Any, *, limit: int) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value[:limit] if isinstance(item, dict)]


def compact_text(value: Any, *, limit: int = 280) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    return text[:limit]


def compact_text_list(value: Any, *, limit: int, text_limit: int = 180) -> List[str]:
    if not isinstance(value, list):
        return []
    items: List[str] = []
    for item in value:
        text = compact_text(item, limit=text_limit)
        if text:
            items.append(text)
        if len(items) >= limit:
            break
    return items


def load_tradingagents_readonly_context(
    analysis_dir: str | None,
    *,
    max_items: int,
    warnings: List[str],
    strict: bool,
) -> Tuple[Dict[str, Any] | None, Dict[str, Any] | None]:
    if not analysis_dir:
        return None, None
    try:
        service = load_module(
            "tradingagents_readonly_analysis_for_agent_prompt",
            ROOT / "backend/app/services/tradingagents_readonly_analysis.py",
        )
        payload = service.load_tradingagents_readonly_analysis(
            run_id=None,
            artifact_root=analysis_dir,
            include_markdown=False,
        )
    except Exception as exc:
        if strict:
            raise BuildError(f"tradingagents_readonly_unavailable:{exc}") from exc
        warnings.append("tradingagents_readonly_unavailable")
        return None, None
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        if strict:
            status = payload.get("status") if isinstance(payload, dict) else "invalid_payload"
            raise BuildError(f"tradingagents_readonly_validation_failed:{status}")
        warnings.append("tradingagents_readonly_validation_failed")
        return None, None

    report = payload.get("sanitized_report") or {}
    symbols: List[Dict[str, Any]] = []
    for item in report.get("symbols", []) if isinstance(report.get("symbols"), list) else []:
        if not isinstance(item, dict):
            continue
        symbols.append({
            "symbol": compact_text(item.get("symbol"), limit=16),
            "instrument": compact_text(item.get("instrument"), limit=32),
            "research_summary": compact_text(item.get("research_summary"), limit=420),
            "bull_points": compact_text_list(item.get("bull_points"), limit=3),
            "bear_points": compact_text_list(item.get("bear_points"), limit=3),
            "risk_review_points": compact_text_list(item.get("risk_review_points"), limit=3),
            "data_limitations": compact_text_list(item.get("data_limitations"), limit=3),
            "human_review_questions": compact_text_list(item.get("human_review_questions"), limit=3),
        })
        if len(symbols) >= max_items:
            break

    context = {
        "available": True,
        "status": "pass",
        "run_id": payload.get("run_id"),
        "signal_asof": payload.get("signal_asof"),
        "target_date": payload.get("target_date"),
        "readonly_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "production_trade_enabled": False,
        "sanitized_only": True,
        "source_artifact": f"{TRADINGAGENTS_SOURCE_NAME}:{payload.get('run_id')}",
        "symbols": symbols,
        "research_only_disclaimer": report.get("research_only_disclaimer"),
    }
    source_stub = {
        "artifact_type": "tw_agent_external_research_source_stub",
        "source_name": TRADINGAGENTS_SOURCE_NAME,
        "status": "included_sanitized_only",
        "sanitized_only": True,
        "source_files_included": False,
        "manifest": payload.get("manifest") or {},
        "validation": payload.get("validation") or {},
    }
    return context, source_stub


def build_prompt_context(
    sources: Dict[str, Dict[str, Any]],
    warnings: List[str],
    *,
    max_items: int,
    external_research: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    current = sources["current_strategy_context"]
    snapshot = sources["readonly_strategy_snapshot"]
    replay = sources.get("readonly_replay_window") or {}
    paper = sources.get("paper_portfolio_decision") or {}
    productization = sources.get("productization_status") or {}

    rankings = snapshot.get("rankings") or {}
    strategy = snapshot.get("strategy") or {}
    freshness = current.get("freshness") or {}
    paper_apply_allowed = bool(paper.get("apply_allowed", False))
    paper_blocked_reason = paper.get("blocked_reason") or (None if paper_apply_allowed else "paper_apply_not_allowed_or_missing")
    combined_warnings = list(dict.fromkeys(
        list(warnings)
        + list(freshness.get("warnings") or [])
        + list(replay.get("warnings") or [])
        + list(productization.get("warnings") or [])
        + ([paper_blocked_reason] if paper_blocked_reason else [])
    ))

    context = {
        "schema_version": "tw_agent_daily_prompt_context_v1",
        "safety": {
            "readonly_only": True,
            "not_order": True,
            "not_target_position": True,
            "not_investment_advice": True,
            "production_trade_enabled": False,
        },
        "date_context": {
            "signal_asof": current.get("signal_asof"),
            "target_date": current.get("target_date"),
            "display_asof": current.get("display_asof") or current.get("signal_asof"),
            "execution_price_mode": EXECUTION_PRICE_MODE,
            "execution_price_status": current.get("execution_price_status") or "unknown",
        },
        "model_context": {
            "base_model_id": BASE_MODEL_ID,
            "treatment_model_id": TREATMENT_MODEL_ID,
            "ranking_source": current.get("ranking_source") or "ltr_rerank_within_qlib_top50",
            "candidate_boundary": current.get("candidate_boundary") or "qlib_top50",
        },
        "rankings": {
            "qlib_top10": compact_list(rankings.get("qlib_top10"), limit=min(max_items, 10)),
            "ltr_top10": compact_list(rankings.get("ltr_top10"), limit=min(max_items, 10)),
            "ltr_top50_compact": compact_list(rankings.get("ltr_top50_compact"), limit=max_items),
        },
        "strategy": {
            "strategy_rule": STRATEGY_RULE,
            "top_candidates": compact_list(strategy.get("top_candidates"), limit=max_items),
            "exit_candidates": compact_list(strategy.get("exit_candidates"), limit=max_items),
            "skipped_or_blocked": compact_list(strategy.get("skipped_or_blocked"), limit=max_items),
        },
        "paper_portfolio": {
            "apply_allowed": paper_apply_allowed,
            "blocked_reason": paper_blocked_reason,
            "positions_compact": compact_list(paper.get("positions_compact"), limit=max_items),
        },
        "replay_summary": {
            "window": replay.get("window") or "unavailable",
            "metrics": replay.get("metrics") or {},
            "warnings": replay.get("warnings") or [],
        },
        "freshness": {
            "status": freshness.get("status") or productization.get("status") or "unknown",
            "warnings": combined_warnings,
        },
        "answer_policy": {
            "allowed_question_types": [
                "today_strategy",
                "tomorrow_candidates",
                "top_ranked_stock",
                "top_n_rankings",
                "strategy_buy_sell_observation",
                "single_symbol_status",
                "paper_apply_status",
                "execution_price_pending",
                "data_freshness",
                "replay_summary",
                "external_research_summary",
            ],
            "blocked_question_types": [
                "place_order",
                "auto_trade",
                "target_position",
                "portfolio_weight",
                "guaranteed_profit",
                "qlib_ops_refresh_publish",
                "qlib_retrain_or_tune",
                "broker_operation",
                "monitor_write",
            ],
            "required_disclaimer": RESEARCH_ONLY_DISCLAIMER,
        },
    }
    if external_research is not None:
        context["external_research"] = {
            "tradingagents_readonly": external_research,
        }
    return context


def build_prompt_text(context: Dict[str, Any]) -> str:
    date_context = context["date_context"]
    strategy = context["strategy"]
    rankings = context["rankings"]
    top_ltr = rankings.get("ltr_top10") or []
    top_candidates = strategy.get("top_candidates") or []
    exit_candidates = strategy.get("exit_candidates") or []
    warnings = context.get("freshness", {}).get("warnings") or []
    tradingagents = ((context.get("external_research") or {}).get("tradingagents_readonly") or {})

    def symbols(items: List[Dict[str, Any]]) -> str:
        values = [str(item.get("symbol")) for item in items if item.get("symbol")]
        return ", ".join(values[:10]) if values else "none"

    lines = [
        "# Role",
        "你是 QuantDinger 台股 research-only 只读研究助手。你只能解释给定 DailyAgentPromptArtifact。",
        "",
        "# Safety",
        "- 不能执行交易行为，不能给出真实执行指令，不能承诺收益。",
        "- qlib score 是横截面排序分数，不是收益率、胜率、涨幅或买入概率。",
        "- 用户询问买卖时，只能解释只读策略观察和人工复盘提示。",
        "",
        "# Today Context",
        f"- signal_asof: {date_context.get('signal_asof')}",
        f"- target_date: {date_context.get('target_date')}",
        f"- execution_price_mode: {date_context.get('execution_price_mode')}",
        f"- execution_price_status: {date_context.get('execution_price_status')}",
        f"- strategy_rule: {strategy.get('strategy_rule')}",
        "",
        "# Rankings",
        f"- LTR top symbols: {symbols(top_ltr)}",
        "",
        "# Strategy Snapshot",
        f"- top candidate observations: {symbols(top_candidates)}",
        f"- exit observations: {symbols(exit_candidates)}",
        "",
        "# Freshness / Pending",
        f"- warnings: {', '.join(str(item) for item in warnings[:10]) if warnings else 'none'}",
        "",
    ]
    if tradingagents:
        ta_symbols = [str(item.get("symbol")) for item in tradingagents.get("symbols", []) if isinstance(item, dict) and item.get("symbol")]
        ta_summaries = [
            f"{item.get('symbol')}: {item.get('research_summary')}"
            for item in tradingagents.get("symbols", [])[:3]
            if isinstance(item, dict) and item.get("symbol") and item.get("research_summary")
        ]
        lines.extend([
            "# External Research",
            f"- TradingAgents readonly sanitized context: {tradingagents.get('status') or 'unavailable'}",
            f"- external research symbols: {', '.join(ta_symbols[:10]) if ta_symbols else 'none'}",
            f"- review summaries: {'; '.join(ta_summaries) if ta_summaries else 'none'}",
            "- 这些外部研究只作为人工复盘线索，不是策略证据、执行指令或收益承诺。",
            "",
        ])
    lines.extend([
        "# Output Contract",
        "只输出 JSON：",
        "```json",
        '{"answer":"string","intent":"string","citations":["string"],"warnings":["string"],"blocked":false,"research_only_disclaimer":"string"}',
        "```",
        "",
    ])
    return "\n".join(lines)


def copy_source_stubs(paths: Dict[str, Path], output_dir: Path) -> Dict[str, str]:
    stub_dir = output_dir / "source_stubs"
    stub_dir.mkdir(parents=True, exist_ok=True)
    source_artifacts: Dict[str, str] = {}
    for name, path in paths.items():
        target = stub_dir / f"{name}.json"
        shutil.copyfile(path, target)
        source_artifacts[name] = str(target.relative_to(output_dir))
    return source_artifacts


def copy_external_source_stub(source_artifacts: Dict[str, str], output_dir: Path, source_stub: Dict[str, Any] | None) -> None:
    if not source_stub:
        return
    stub_dir = output_dir / "source_stubs"
    stub_dir.mkdir(parents=True, exist_ok=True)
    target = stub_dir / f"{TRADINGAGENTS_SOURCE_NAME}.json"
    write_json(target, source_stub)
    source_artifacts[TRADINGAGENTS_SOURCE_NAME] = str(target.relative_to(output_dir))


def build_artifact(args: argparse.Namespace) -> Dict[str, Any]:
    source_dir = source_dir_from_args(args)
    sources, paths = load_sources(source_dir)
    warnings = validate_source_alignment(sources)
    current = sources["current_strategy_context"]
    external_research, external_source_stub = load_tradingagents_readonly_context(
        getattr(args, "tradingagents_analysis_dir", None),
        max_items=args.max_items,
        warnings=warnings,
        strict=bool(getattr(args, "strict_tradingagents_analysis", False)),
    )
    if external_research:
        if external_research.get("signal_asof") and external_research.get("signal_asof") != current.get("signal_asof"):
            warnings.append("tradingagents_readonly_signal_asof_mismatch")
        if external_research.get("target_date") and external_research.get("target_date") != current.get("target_date"):
            warnings.append("tradingagents_readonly_target_date_mismatch")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_artifacts = copy_source_stubs(paths, output_dir)
    copy_external_source_stub(source_artifacts, output_dir, external_source_stub)

    context = build_prompt_context(sources, warnings, max_items=args.max_items, external_research=external_research)
    prompt_text = build_prompt_text(context)
    context_path = output_dir / "prompt_context.json"
    prompt_path = output_dir / "prompt_text.md"
    write_json(context_path, context)
    prompt_path.write_text(prompt_text, encoding="utf-8")

    checksum = compute_checksum(context_path.read_bytes(), prompt_path.read_bytes())
    manifest = {
        "artifact_type": "tw_agent_daily_prompt",
        "schema_version": "tw_agent_daily_prompt_v1",
        "readonly_only": True,
        "not_order": True,
        "not_target_position": True,
        "production_trade_enabled": False,
        "signal_asof": current.get("signal_asof"),
        "target_date": current.get("target_date"),
        "model_ids": {
            "base": BASE_MODEL_ID,
            "treatment": TREATMENT_MODEL_ID,
        },
        "strategy_rule": STRATEGY_RULE,
        "execution_price_mode": EXECUTION_PRICE_MODE,
        "source_artifacts": source_artifacts,
        "validation": {
            "ok": True,
            "asof_alignment": "pass",
            "forbidden_action_audit": "pass",
            "max_prompt_tokens_estimate": len(prompt_text) // 4 + len(json.dumps(context, ensure_ascii=False)) // 4,
            "warnings": context["freshness"]["warnings"],
        },
        "checksum": checksum,
    }
    write_json(output_dir / "manifest.json", manifest)

    validation = validate_artifact(output_dir)
    if not validation.ok:
        raise BuildError("validator_failed:" + ";".join(validation.errors))

    if args.publish_latest:
        latest_path = Path(args.latest_path)
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest = {
            "artifact_type": "tw_agent_daily_prompt_latest",
            "signal_asof": manifest["signal_asof"],
            "artifact_dir": str(output_dir),
            "manifest": str(output_dir / "manifest.json"),
            "checksum": checksum,
        }
        write_json(latest_path, latest)

    return {
        "ok": True,
        "output_dir": str(output_dir),
        "manifest": str(output_dir / "manifest.json"),
        "checksum": checksum,
        "warnings": context["freshness"]["warnings"],
        "published_latest": bool(args.publish_latest),
        "latest_path": str(args.latest_path) if args.publish_latest else None,
    }


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-fixture", help="Fixture directory containing source_artifacts/*.json")
    parser.add_argument("--source-dir", help="Directory containing read-only source artifact JSON files")
    parser.add_argument("--output-dir", required=True, help="Output artifact directory")
    parser.add_argument("--dry-run", action="store_true", help="Build artifact without updating latest pointer; this is the default")
    parser.add_argument("--publish-latest", action="store_true", help="Update only the Agent prompt latest pointer after validation")
    parser.add_argument("--latest-path", default="data_tw/artifacts/agent_daily_prompt/latest.json", help="Agent prompt latest pointer path")
    parser.add_argument("--max-items", type=int, default=10, help="Maximum compact items per section")
    parser.add_argument("--tradingagents-analysis-dir", help="Optional validated TradingAgents readonly analysis artifact directory")
    parser.add_argument("--strict-tradingagents-analysis", action="store_true", help="Fail if the optional TradingAgents artifact cannot be loaded and validated")
    parser.add_argument("--json", action="store_true", help="Print machine-readable result")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    try:
        if args.max_items < 1 or args.max_items > 50:
            raise BuildError("--max-items must be between 1 and 50")
        result = build_artifact(args)
    except BuildError as exc:
        payload = {"ok": False, "error": str(exc)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"FAIL: {exc}")
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"PASS: {result['output_dir']}")
        for warning in result.get("warnings") or []:
            print(f"WARNING: {warning}")
        if result.get("published_latest"):
            print(f"LATEST: {result['latest_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
