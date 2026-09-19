#!/usr/bin/env python3
"""Validate TW Agent DailyAgentPromptArtifact directories."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
BASE_MODEL_ID = "e4_frozen_qlib_2018_2022"
TREATMENT_MODEL_ID = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
STRATEGY_RULE = "top50_exit_one_worst_sell"
EXECUTION_PRICE_MODE = "next_open"
CANDIDATE_ONLY_STRATEGY_RULE = "candidate_only_no_strategy_replay"
CANDIDATE_ONLY_EXECUTION_PRICE_MODE = "not_applicable_candidate_only_no_strategy_replay"
CANDIDATE_ONLY_TREATMENT_STATUS = "not_applicable_candidate_only_no_ltr_rerank"
CANDIDATE_ONLY_RANKING_SOURCE = "qlib_rank_controlled_signal"
CANDIDATE_ONLY_BOUNDARY = "qlib_top50"
CANDIDATE_ONLY_LINEAGE = "rsppr_candidate_only_readonly_snapshot_latest"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

FORBIDDEN_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in (
        ("broker", r"\bbroker\b"),
        ("quick_trade", r"quick-trade"),
        ("order", r"\border\b"),
        ("orders", r"\borders\b"),
        ("place_order", r"\bplace\s+orders?\b"),
        ("submit_order", r"\bsubmit\s+orders?\b"),
        ("target_position_dash", r"target-position"),
        ("target_position", r"target_position"),
        ("target_weight", r"target_weight"),
        ("auto_buy", r"自动买入|自動買入"),
        ("auto_sell", r"自动卖出|自動賣出"),
        ("target_position_cn", r"目标仓位|目標倉位"),
        ("place_order_cn", r"下单|下單"),
        ("submit_order_cn", r"提交订单|提交訂單"),
        ("connect_broker_cn", r"连接券商|連接券商"),
        ("monitor_config", r"monitor\s+config"),
        ("monitor_scan", r"monitor\s+scan"),
        ("monitor_alerts", r"monitor\s+alerts?"),
        ("save_monitor", r"save\s+monitor"),
        ("monitor_config_path", r"/monitor/config"),
        ("monitor_scan_path", r"/monitor/scan(?:-all)?"),
        ("monitor_alerts_path", r"/monitor/alerts"),
        ("monitor_config_cn", r"保存监控配置|保存監控配置"),
        ("monitor_scan_cn", r"触发\s*monitor\s*scan|觸發\s*monitor\s*scan"),
        ("monitor_alerts_cn", r"写\s*monitor\s*alerts|寫\s*monitor\s*alerts"),
        ("provider_refresh_cn", r"刷新\s*provider"),
        ("accepted_latest_switch_cn", r"切换\s*accepted\s*latest|切換\s*accepted\s*latest"),
        ("provider_publish", r"provider\s+publish"),
        ("qlib_refresh", r"qlib\s+refresh"),
        ("retrain", r"\bretrain\b"),
        ("tune_cn", r"调参|調參"),
        ("guaranteed_profit_cn", r"保证收益|保證收益"),
        ("guaranteed_up_cn", r"保证上涨|保證上漲"),
        ("win_rate_promise_cn", r"胜率承诺|勝率承諾"),
        ("up_probability_cn", r"上涨概率|上漲概率"),
    )
)

ALLOWED_FORBIDDEN_PATH_PARTS = (
    ("not_target_position",),
    ("safety", "not_target_position"),
    ("answer_policy", "blocked_question_types"),
    ("answer_policy", "score_semantics_required"),
    ("answer_policy", "forbidden_answer_semantics"),
    ("answer_policy", "forbidden_tool_calls"),
    ("safety", "blocked_operations"),
    ("safety", "forbidden_actions"),
)

PROMPT_TEXT_ALLOWED_CONTEXT_MARKERS = (
    "不能",
    "不得",
    "禁止",
    "blocked",
    "拒绝",
    "拒絕",
    "不支持",
    "不是",
    "not ",
    "not_",
    "no_",
)

TRADINGAGENTS_FORBIDDEN_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in (
        ("raw_file_name", r"raw_tradingagents_state|raw_complete_report|raw_untrusted"),
        ("raw_rating", r"\b(?:Buy|Sell|Hold|Overweight|Underweight)\b"),
        ("transaction_proposal", r"final\s+transaction\s+proposal|transaction\s+proposal"),
        ("position_sizing", r"position\s+sizing|仓位大小|倉位大小"),
        ("stop_loss", r"stop\s+loss|止损|止損"),
        ("price_target", r"price\s+target|target\s+price|目标价|目標價"),
        ("entry_price", r"entry\s+price|入场价|入場價"),
    )
)


class ValidationResult:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def to_dict(self, artifact_dir: Path) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "artifact_dir": str(artifact_dir),
            "errors": self.errors,
            "warnings": self.warnings,
        }


def read_json(path: Path, result: ValidationResult) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        result.error(f"{path.name}: failed_to_read_json: {exc}")
        return {}
    if not isinstance(payload, dict):
        result.error(f"{path.name}: expected JSON object")
        return {}
    return payload


def load_text(path: Path, result: ValidationResult) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        result.error(f"{path.name}: failed_to_read_text: {exc}")
        return ""


def require_equal(result: ValidationResult, field: str, value: Any, expected: Any) -> None:
    if value != expected:
        result.error(f"{field}: expected {expected!r}, got {value!r}")


def require_true(result: ValidationResult, field: str, value: Any) -> None:
    if value is not True:
        result.error(f"{field}: expected true, got {value!r}")


def require_false(result: ValidationResult, field: str, value: Any) -> None:
    if value is not False:
        result.error(f"{field}: expected false, got {value!r}")


def require_date(result: ValidationResult, field: str, value: Any) -> None:
    if not isinstance(value, str) or not DATE_RE.match(value):
        result.error(f"{field}: expected YYYY-MM-DD, got {value!r}")


def compute_checksum(context_bytes: bytes, prompt_bytes: bytes) -> str:
    digest = hashlib.sha256(context_bytes + b"\n" + prompt_bytes).hexdigest()
    return f"sha256:{digest}"


def iter_json_values(payload: Any, path: Tuple[str, ...] = ()) -> Iterable[Tuple[Tuple[str, ...], str]]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_path = path + (str(key),)
            yield key_path, str(key)
            yield from iter_json_values(value, key_path)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            yield from iter_json_values(value, path + (str(index),))
    elif isinstance(payload, str):
        yield path, payload


def path_has_allowed_forbidden_context(path: Tuple[str, ...]) -> bool:
    for parts in ALLOWED_FORBIDDEN_PATH_PARTS:
        if tuple(path[-len(parts):]) == parts:
            return True
        if len(path) > len(parts) and tuple(path[-len(parts) - 1:-1]) == parts:
            return True
    return False


def scan_forbidden_json(result: ValidationResult, label: str, payload: Dict[str, Any]) -> None:
    for path, text in iter_json_values(payload):
        if path_has_allowed_forbidden_context(path):
            continue
        for name, pattern in FORBIDDEN_PATTERNS:
            if pattern.search(text):
                result.error(f"{label}:{'.'.join(path)}: forbidden action term {name!r}")


def prompt_text_line_has_allowed_context(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in PROMPT_TEXT_ALLOWED_CONTEXT_MARKERS)


def scan_forbidden_prompt_text(result: ValidationResult, prompt_text: str) -> None:
    for lineno, line in enumerate(prompt_text.splitlines(), start=1):
        for name, pattern in FORBIDDEN_PATTERNS:
            if pattern.search(line) and not prompt_text_line_has_allowed_context(line):
                result.error(f"prompt_text.md:{lineno}: forbidden action term {name!r}")


def validate_tradingagents_external_research(result: ValidationResult, context: Dict[str, Any]) -> None:
    external = context.get("external_research")
    if external is None:
        return
    if not isinstance(external, dict):
        result.error("prompt_context.external_research: expected object")
        return
    tradingagents = external.get("tradingagents_readonly")
    if tradingagents is None:
        return
    if not isinstance(tradingagents, dict):
        result.error("prompt_context.external_research.tradingagents_readonly: expected object")
        return
    require_true(result, "prompt_context.external_research.tradingagents_readonly.readonly_only", tradingagents.get("readonly_only"))
    require_true(result, "prompt_context.external_research.tradingagents_readonly.not_order", tradingagents.get("not_order"))
    require_true(result, "prompt_context.external_research.tradingagents_readonly.not_target_position", tradingagents.get("not_target_position"))
    require_true(result, "prompt_context.external_research.tradingagents_readonly.not_investment_advice", tradingagents.get("not_investment_advice"))
    require_false(result, "prompt_context.external_research.tradingagents_readonly.production_trade_enabled", tradingagents.get("production_trade_enabled"))
    require_true(result, "prompt_context.external_research.tradingagents_readonly.sanitized_only", tradingagents.get("sanitized_only"))
    symbols = tradingagents.get("symbols")
    if not isinstance(symbols, list):
        result.error("prompt_context.external_research.tradingagents_readonly.symbols: expected list")
        return
    for index, item in enumerate(symbols):
        if not isinstance(item, dict):
            result.error(f"prompt_context.external_research.tradingagents_readonly.symbols.{index}: expected object")
            continue
        required = (
            "symbol",
            "research_summary",
            "bull_points",
            "bear_points",
            "risk_review_points",
            "data_limitations",
            "human_review_questions",
        )
        for field in required:
            if field not in item:
                result.error(f"prompt_context.external_research.tradingagents_readonly.symbols.{index}.{field}: missing")
    blob = json.dumps(tradingagents, ensure_ascii=False, sort_keys=True)
    for name, pattern in TRADINGAGENTS_FORBIDDEN_PATTERNS:
        if pattern.search(blob):
            result.error(f"prompt_context.external_research.tradingagents_readonly: forbidden TradingAgents term {name!r}")


def validate_source_artifacts(
    result: ValidationResult,
    artifact_dir: Path,
    source_artifacts: Any,
    *,
    allow_golden_missing_sources: bool,
) -> None:
    if not isinstance(source_artifacts, dict) or not source_artifacts:
        result.error("manifest.source_artifacts: expected non-empty object")
        return

    def source_exists(path_value: str) -> bool:
        source_path = Path(path_value)
        if source_path.is_absolute():
            return source_path.exists()
        return (ROOT / source_path).exists() or (artifact_dir / source_path).exists()

    for name, spec in source_artifacts.items():
        field = f"manifest.source_artifacts.{name}"
        if isinstance(spec, str):
            if not source_exists(spec):
                result.error(f"{field}: source path does not exist: {spec}")
            continue
        if not isinstance(spec, dict):
            result.error(f"{field}: expected string path or object")
            continue
        status = spec.get("status")
        path_value = spec.get("path")
        if status == "missing_allowed_for_golden_sample":
            if allow_golden_missing_sources:
                result.warning(f"{field}: missing source allowed for golden sample")
            else:
                result.error(f"{field}: missing source allowed only with --allow-golden-missing-sources")
            continue
        if not isinstance(path_value, str) or not path_value:
            result.error(f"{field}.path: expected non-empty string")
            continue
        if not source_exists(path_value):
            result.error(f"{field}.path: source path does not exist: {path_value}")


def is_candidate_only_mode(manifest: Dict[str, Any], context: Dict[str, Any]) -> bool:
    strategy = context.get("strategy") or {}
    model_context = context.get("model_context") or {}
    source_lineage = context.get("source_lineage") or {}
    return any(
        (
            manifest.get("strategy_rule") == CANDIDATE_ONLY_STRATEGY_RULE,
            strategy.get("snapshot_candidate_only") is True,
            strategy.get("not_full_strategy_replay") is True,
            model_context.get("ranking_source") == CANDIDATE_ONLY_RANKING_SOURCE,
            source_lineage.get("lineage") == CANDIDATE_ONLY_LINEAGE,
        )
    )


def validate_candidate_only_contract(
    result: ValidationResult,
    manifest: Dict[str, Any],
    context: Dict[str, Any],
) -> None:
    model_ids = manifest.get("model_ids") or {}
    require_equal(result, "manifest.model_ids.base", model_ids.get("base"), BASE_MODEL_ID)
    if model_ids.get("treatment") not in (None, "not_applicable"):
        result.error(
            "manifest.model_ids.treatment: expected null or 'not_applicable' for candidate-only artifact, "
            f"got {model_ids.get('treatment')!r}"
        )
    require_equal(
        result,
        "manifest.model_ids.treatment_status",
        model_ids.get("treatment_status"),
        CANDIDATE_ONLY_TREATMENT_STATUS,
    )
    require_equal(result, "manifest.strategy_rule", manifest.get("strategy_rule"), CANDIDATE_ONLY_STRATEGY_RULE)
    require_equal(
        result,
        "manifest.execution_price_mode",
        manifest.get("execution_price_mode"),
        CANDIDATE_ONLY_EXECUTION_PRICE_MODE,
    )

    date_context = context.get("date_context") or {}
    model_context = context.get("model_context") or {}
    strategy = context.get("strategy") or {}
    source_lineage = context.get("source_lineage") or {}
    require_equal(
        result,
        "prompt_context.date_context.execution_price_mode",
        date_context.get("execution_price_mode"),
        CANDIDATE_ONLY_EXECUTION_PRICE_MODE,
    )
    require_equal(
        result,
        "prompt_context.date_context.execution_price_status",
        date_context.get("execution_price_status"),
        "not_built_no_strategy_replay",
    )
    require_equal(
        result,
        "prompt_context.model_context.base_model_id",
        model_context.get("base_model_id"),
        model_ids.get("base"),
    )
    if model_context.get("treatment_model_id") not in (None, "not_applicable"):
        result.error(
            "prompt_context.model_context.treatment_model_id: expected null or 'not_applicable' "
            f"for candidate-only artifact, got {model_context.get('treatment_model_id')!r}"
        )
    require_equal(
        result,
        "prompt_context.model_context.treatment_model_status",
        model_context.get("treatment_model_status"),
        CANDIDATE_ONLY_TREATMENT_STATUS,
    )
    require_equal(
        result,
        "prompt_context.model_context.ranking_source",
        model_context.get("ranking_source"),
        CANDIDATE_ONLY_RANKING_SOURCE,
    )
    require_equal(
        result,
        "prompt_context.model_context.candidate_boundary",
        model_context.get("candidate_boundary"),
        CANDIDATE_ONLY_BOUNDARY,
    )
    require_equal(result, "prompt_context.strategy.strategy_rule", strategy.get("strategy_rule"), CANDIDATE_ONLY_STRATEGY_RULE)
    require_true(result, "prompt_context.strategy.snapshot_candidate_only", strategy.get("snapshot_candidate_only"))
    require_true(result, "prompt_context.strategy.not_full_strategy_replay", strategy.get("not_full_strategy_replay"))
    require_equal(result, "prompt_context.strategy.exit_candidates", strategy.get("exit_candidates"), [])
    require_equal(result, "prompt_context.strategy.hold_candidates", strategy.get("hold_candidates"), [])
    require_equal(
        result,
        "prompt_context.strategy.exit_hold_context_status",
        strategy.get("exit_hold_context_status"),
        "not_built_no_strategy_replay",
    )
    require_equal(result, "prompt_context.source_lineage.lineage", source_lineage.get("lineage"), CANDIDATE_ONLY_LINEAGE)


def validate_full_strategy_contract(
    result: ValidationResult,
    manifest: Dict[str, Any],
    context: Dict[str, Any],
) -> None:
    model_ids = manifest.get("model_ids") or {}
    require_equal(result, "manifest.model_ids.base", model_ids.get("base"), BASE_MODEL_ID)
    require_equal(result, "manifest.model_ids.treatment", model_ids.get("treatment"), TREATMENT_MODEL_ID)
    require_equal(result, "manifest.strategy_rule", manifest.get("strategy_rule"), STRATEGY_RULE)
    require_equal(result, "manifest.execution_price_mode", manifest.get("execution_price_mode"), EXECUTION_PRICE_MODE)
    date_context = context.get("date_context") or {}
    model_context = context.get("model_context") or {}
    require_equal(
        result,
        "prompt_context.date_context.execution_price_mode",
        date_context.get("execution_price_mode"),
        EXECUTION_PRICE_MODE,
    )
    require_equal(result, "prompt_context.model_context.base_model_id", model_context.get("base_model_id"), model_ids.get("base"))
    require_equal(
        result,
        "prompt_context.model_context.treatment_model_id",
        model_context.get("treatment_model_id"),
        model_ids.get("treatment"),
    )
    require_equal(
        result,
        "prompt_context.model_context.ranking_source",
        model_context.get("ranking_source"),
        "ltr_rerank_within_qlib_top50",
    )
    require_equal(
        result,
        "prompt_context.model_context.candidate_boundary",
        model_context.get("candidate_boundary"),
        CANDIDATE_ONLY_BOUNDARY,
    )


def validate_score_explanation(result: ValidationResult, prompt_text: str, *, candidate_only: bool) -> None:
    required_terms = ("收益率", "胜率", "买入概率")
    has_probability_or_gain = "涨幅" in prompt_text or (candidate_only and "上涨概率" in prompt_text)
    if "qlib score" not in prompt_text.lower() or not all(term in prompt_text for term in required_terms) or not has_probability_or_gain:
        result.error("prompt_text.md: missing qlib score non-return/non-probability explanation")


def validate_artifact(artifact_dir: Path, *, allow_golden_missing_sources: bool = False) -> ValidationResult:
    result = ValidationResult()
    manifest_path = artifact_dir / "manifest.json"
    context_path = artifact_dir / "prompt_context.json"
    prompt_path = artifact_dir / "prompt_text.md"
    for path in (manifest_path, context_path, prompt_path):
        if not path.exists():
            result.error(f"{path.name}: missing")
    if result.errors:
        return result

    manifest = read_json(manifest_path, result)
    context = read_json(context_path, result)
    prompt_text = load_text(prompt_path, result)
    if result.errors:
        return result

    require_equal(result, "manifest.artifact_type", manifest.get("artifact_type"), "tw_agent_daily_prompt")
    require_equal(result, "manifest.schema_version", manifest.get("schema_version"), "tw_agent_daily_prompt_v1")
    require_true(result, "manifest.readonly_only", manifest.get("readonly_only"))
    require_true(result, "manifest.not_order", manifest.get("not_order"))
    require_true(result, "manifest.not_target_position", manifest.get("not_target_position"))
    require_false(result, "manifest.production_trade_enabled", manifest.get("production_trade_enabled"))
    require_date(result, "manifest.signal_asof", manifest.get("signal_asof"))
    require_date(result, "manifest.target_date", manifest.get("target_date"))
    require_true(result, "manifest.validation.ok", (manifest.get("validation") or {}).get("ok"))
    validate_source_artifacts(
        result,
        artifact_dir,
        manifest.get("source_artifacts"),
        allow_golden_missing_sources=allow_golden_missing_sources,
    )

    require_equal(result, "prompt_context.schema_version", context.get("schema_version"), "tw_agent_daily_prompt_context_v1")
    safety = context.get("safety") or {}
    require_true(result, "prompt_context.safety.readonly_only", safety.get("readonly_only"))
    require_true(result, "prompt_context.safety.not_order", safety.get("not_order"))
    require_true(result, "prompt_context.safety.not_target_position", safety.get("not_target_position"))
    require_true(result, "prompt_context.safety.not_investment_advice", safety.get("not_investment_advice"))
    require_false(result, "prompt_context.safety.production_trade_enabled", safety.get("production_trade_enabled"))
    date_context = context.get("date_context") or {}
    require_equal(result, "prompt_context.date_context.signal_asof", date_context.get("signal_asof"), manifest.get("signal_asof"))
    require_equal(result, "prompt_context.date_context.target_date", date_context.get("target_date"), manifest.get("target_date"))
    candidate_only = is_candidate_only_mode(manifest, context)
    if candidate_only:
        validate_candidate_only_contract(result, manifest, context)
    else:
        validate_full_strategy_contract(result, manifest, context)
    disclaimer = ((context.get("answer_policy") or {}).get("required_disclaimer") or "")
    if not isinstance(disclaimer, str) or "不构成交易建议" not in disclaimer:
        result.error("prompt_context.answer_policy.required_disclaimer: must contain 不构成交易建议")

    if "research-only" not in prompt_text.lower() and "只读" not in prompt_text:
        result.error("prompt_text.md: missing research-only or 只读 boundary")
    validate_score_explanation(result, prompt_text, candidate_only=candidate_only)
    if "JSON" not in prompt_text and "json" not in prompt_text:
        result.error("prompt_text.md: missing JSON output contract")
    validate_tradingagents_external_research(result, context)

    context_bytes = context_path.read_bytes()
    prompt_bytes = prompt_path.read_bytes()
    expected_checksum = compute_checksum(context_bytes, prompt_bytes)
    require_equal(result, "manifest.checksum", manifest.get("checksum"), expected_checksum)

    scan_forbidden_json(result, "manifest", manifest)
    scan_forbidden_json(result, "prompt_context", context)
    scan_forbidden_prompt_text(result, prompt_text)
    return result


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", help="Directory containing manifest.json, prompt_context.json and prompt_text.md")
    parser.add_argument("--json", action="store_true", help="Print machine-readable validation result")
    parser.add_argument(
        "--allow-golden-missing-sources",
        action="store_true",
        help="Allow source_artifacts entries marked missing_allowed_for_golden_sample",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    artifact_dir = Path(args.artifact_dir)
    result = validate_artifact(
        artifact_dir,
        allow_golden_missing_sources=bool(args.allow_golden_missing_sources),
    )
    payload = result.to_dict(artifact_dir)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        status = "PASS" if result.ok else "FAIL"
        print(f"{status}: {artifact_dir}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")
        for error in result.errors:
            print(f"ERROR: {error}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
