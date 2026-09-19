#!/usr/bin/env python3
"""Validate TradingAgents readonly analysis artifact directories."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T")

REQUIRED_FILES = [
    "manifest.json",
    "input_artifact_index.json",
    "sanitized_report.md",
    "sanitized_report.json",
    "claim_support_audit.json",
    "forbidden_semantics_audit.json",
]

REQUIRED_MANIFEST_FIELDS = [
    "artifact_type",
    "schema_version",
    "analysis_name",
    "run_id",
    "created_at",
    "source",
    "input_artifacts",
    "input_symbols",
    "signal_asof",
    "target_date",
    "readonly_only",
    "not_order",
    "not_target_position",
    "not_investment_advice",
    "production_trade_enabled",
    "no_replay",
    "no_strategy_return_conclusion",
    "not_valid_strategy_evidence",
    "not_valid_default_switch_evidence",
    "output_report",
    "quality_status",
    "claim_support_audit",
    "forbidden_semantics_audit",
]

TRUE_FLAGS = [
    "readonly_only",
    "not_order",
    "not_target_position",
    "not_investment_advice",
    "no_replay",
    "no_strategy_return_conclusion",
    "not_valid_strategy_evidence",
    "not_valid_default_switch_evidence",
    "no_provider_publish",
    "no_accepted_latest_switch",
    "no_monitor_write",
    "no_broker_quick_trade_order",
]

RUNTIME_CALL_FLAGS = [
    "no_openai_call",
    "no_network_call",
    "no_tradingagents_graph_call",
]

RESEARCH_LABEL_TOP_FIELDS = {
    "source_section_presence",
    "source_text_density_bucket",
    "evidence_quality_flags",
    "attention_flags",
    "review_queue_flags",
    "sanitizer_counters",
}
RESEARCH_LABEL_SECTION_FIELDS = {"market", "news", "fundamental", "social", "debate", "risk"}
RESEARCH_LABEL_DENSITY_BUCKETS = {"none", "short", "medium", "long"}
RESEARCH_LABEL_EVIDENCE_FLAGS = {"has_numeric_context", "has_event_context", "has_data_gap_language"}
RESEARCH_LABEL_ATTENTION_FLAGS = {
    "market_volatility_attention",
    "external_event_attention",
    "fundamentals_attention",
    "liquidity_attention",
}
RESEARCH_LABEL_REVIEW_FLAGS = {"needs_human_fact_check", "needs_candidate_context_compare"}
RESEARCH_LABEL_COUNTERS = {"source_section_count", "forbidden_term_category_count", "raw_text_chars_bucketed"}

FORBIDDEN_FIELD_NAMES = {
    "production_ready",
    "default_strategy_selected",
    "target_position",
    "target_weight",
    "buy_now",
    "sell_now",
    "guaranteed_return",
    "win_rate_promise",
    "broker_order_id",
    "order_intent",
    "model_signal",
    "replay_result",
    "provider_latest_pointer",
    "qlib_accepted_latest_pointer",
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
        ("provider_publish", r"provider\s+publish|刷新\s*provider"),
        ("accepted_latest_switch", r"accepted\s+latest\s+switch|切换\s*accepted\s*latest|切換\s*accepted\s*latest"),
        ("monitor_write", r"monitor\s+(?:config|scan|alerts)|保存监控配置|保存監控配置"),
        ("broker_order", r"quick-trade|\bbroker\b|\border\b|下单|下單"),
    )
)


class Result:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    @property
    def ok(self) -> bool:
        return all(check["status"] == "pass" for check in self.checks)

    def check(self, name: str, ok: bool, details: str = "") -> None:
        self.checks.append({"name": name, "status": "pass" if ok else "fail", "details": details})


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def read_json(path: Path, result: Result) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        result.check(f"read_json:{path.name}", False, str(exc))
        return {}
    if not isinstance(payload, dict):
        result.check(f"json_object:{path.name}", False, "expected object")
        return {}
    result.check(f"read_json:{path.name}", True, rel(path))
    return payload


def read_text(path: Path, result: Result) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        result.check(f"read_text:{path.name}", False, str(exc))
        return ""
    result.check(f"read_text:{path.name}", True, rel(path))
    return text


def iter_json_paths(payload: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_path = path + (str(key),)
            yield key_path, key
            yield from iter_json_paths(value, key_path)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            yield from iter_json_paths(value, path + (str(index),))
    else:
        yield path, payload


def find_forbidden_fields(payload: Any) -> list[str]:
    offenders: list[str] = []
    for path, value in iter_json_paths(payload):
        if path and path[-1] in FORBIDDEN_FIELD_NAMES:
            offenders.append(".".join(path))
        if isinstance(value, str) and value in FORBIDDEN_FIELD_NAMES:
            offenders.append(".".join(path + (value,)))
    return sorted(set(offenders))


def scan_text(label: str, text: str) -> list[dict[str, str]]:
    offenders: list[dict[str, str]] = []
    for name, pattern in FORBIDDEN_PATTERNS:
        for match in pattern.finditer(text):
            offenders.append({"file": label, "pattern": name, "match": match.group(0)})
    return offenders


def validate_bool_object(
    labels: dict[str, Any],
    field: str,
    expected_keys: set[str],
    errors: list[str],
) -> None:
    value = labels.get(field)
    if not isinstance(value, dict):
        errors.append(f"{field}:not_object")
        return
    keys = set(str(key) for key in value)
    if keys != expected_keys:
        errors.append(f"{field}:keys:{','.join(sorted(keys ^ expected_keys))}")
        return
    bad_values = [key for key, item in value.items() if not isinstance(item, bool)]
    if bad_values:
        errors.append(f"{field}:non_bool:{','.join(sorted(bad_values))}")


def validate_research_labels(labels: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(labels, dict):
        return ["not_object"]
    keys = set(str(key) for key in labels)
    if keys != RESEARCH_LABEL_TOP_FIELDS:
        errors.append(f"top_fields:{','.join(sorted(keys ^ RESEARCH_LABEL_TOP_FIELDS))}")

    validate_bool_object(labels, "source_section_presence", RESEARCH_LABEL_SECTION_FIELDS, errors)
    validate_bool_object(labels, "evidence_quality_flags", RESEARCH_LABEL_EVIDENCE_FLAGS, errors)
    validate_bool_object(labels, "attention_flags", RESEARCH_LABEL_ATTENTION_FLAGS, errors)
    validate_bool_object(labels, "review_queue_flags", RESEARCH_LABEL_REVIEW_FLAGS, errors)

    density = labels.get("source_text_density_bucket")
    if density not in RESEARCH_LABEL_DENSITY_BUCKETS:
        errors.append(f"source_text_density_bucket:bad_enum:{density!r}")

    counters = labels.get("sanitizer_counters")
    if not isinstance(counters, dict):
        errors.append("sanitizer_counters:not_object")
    else:
        counter_keys = set(str(key) for key in counters)
        if counter_keys != RESEARCH_LABEL_COUNTERS:
            errors.append(f"sanitizer_counters:keys:{','.join(sorted(counter_keys ^ RESEARCH_LABEL_COUNTERS))}")
        for key, value in counters.items():
            if isinstance(value, bool) or not isinstance(value, int):
                errors.append(f"sanitizer_counters:non_int:{key}")
            elif value < 0:
                errors.append(f"sanitizer_counters:negative:{key}")
        if isinstance(counters.get("source_section_count"), int) and not isinstance(counters.get("source_section_count"), bool):
            if counters["source_section_count"] > len(RESEARCH_LABEL_SECTION_FIELDS):
                errors.append("sanitizer_counters:source_section_count_range")
        if isinstance(counters.get("raw_text_chars_bucketed"), int) and not isinstance(counters.get("raw_text_chars_bucketed"), bool):
            if counters["raw_text_chars_bucketed"] > 20:
                errors.append("sanitizer_counters:raw_text_chars_bucketed_range")

    for path, value in iter_json_paths(labels):
        if path and isinstance(value, str) and value == path[-1]:
            continue
        if isinstance(value, (dict, list)):
            continue
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and not isinstance(value, bool):
            continue
        if isinstance(value, str) and path and path[-1] == "source_text_density_bucket":
            continue
        errors.append(f"leaf_type:{'.'.join(path)}:{type(value).__name__}")
    return sorted(set(errors))


def validate_raw_files(result: Result, artifact_dir: Path, manifest: dict[str, Any], forbidden_audit: dict[str, Any]) -> None:
    raw_files = manifest.get("raw_untrusted_files", [])
    if raw_files is None:
        raw_files = []
    result.check("manifest_raw_untrusted_files_list", isinstance(raw_files, list), repr(raw_files))
    excluded = forbidden_audit.get("raw_untrusted_files_excluded_from_display", [])
    result.check("raw_files_excluded_from_display", sorted(raw_files) == sorted(excluded), repr(excluded))
    for raw in raw_files if isinstance(raw_files, list) else []:
        raw_path = artifact_dir / str(raw)
        result.check(f"raw_file_exists:{raw}", raw_path.exists(), rel(raw_path))
        if raw_path.suffix == ".json" and raw_path.exists():
            payload = read_json(raw_path, result)
            result.check(f"raw_file_marked_untrusted:{raw}", payload.get("raw_untrusted") is True and payload.get("display_allowed") is False, repr(payload))
        elif raw_path.exists():
            text = read_text(raw_path, result)
            result.check(f"raw_file_marked_untrusted:{raw}", "raw_untrusted: true" in text and "display_allowed: false" in text, rel(raw_path))


def validate_runtime_mode(result: Result, manifest: dict[str, Any], artifact_dir: Path) -> None:
    run_mode = manifest.get("run_mode") or "fixture_dry_run"
    result.check("manifest_run_mode_allowed", run_mode in {"fixture_dry_run", "controlled_real_run"}, repr(run_mode))
    result.check("manifest_manual_run_only", manifest.get("manual_run_only", True) is True, repr(manifest.get("manual_run_only")))
    result.check("manifest_no_latest_pointer_update", manifest.get("no_latest_pointer_update", True) is True, repr(manifest.get("no_latest_pointer_update")))
    if run_mode != "controlled_real_run":
        result.check(
            "manifest_runtime_call_flags_dry_run_true",
            all(manifest.get(flag) is True for flag in RUNTIME_CALL_FLAGS),
            ",".join(flag for flag in RUNTIME_CALL_FLAGS if manifest.get(flag) is not True),
        )
        return

    result.check(
        "manifest_runtime_call_flags_controlled_real_run",
        manifest.get("no_openai_call") is False
        and manifest.get("no_network_call") is False
        and manifest.get("no_tradingagents_graph_call") is False,
        ",".join(f"{flag}={manifest.get(flag)!r}" for flag in RUNTIME_CALL_FLAGS),
    )
    runtime_paths = manifest.get("runtime_paths")
    result.check("manifest_runtime_paths_object", isinstance(runtime_paths, dict), repr(runtime_paths))
    if not isinstance(runtime_paths, dict):
        return
    required = ("results_dir", "data_cache_dir", "memory_log_path")
    missing = [key for key in required if not runtime_paths.get(key)]
    result.check("manifest_runtime_paths_required", not missing, ",".join(missing))
    root = (ROOT / "data_tw/artifacts/analysis/tradingagents_readonly").resolve()
    for key in required:
        value = runtime_paths.get(key)
        if not isinstance(value, str) or not value:
            continue
        candidate = (ROOT / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
        try:
            candidate.relative_to(root)
            inside = True
        except ValueError:
            inside = False
        result.check(f"manifest_runtime_path_repo_local:{key}", inside, str(candidate))


def validate(artifact_dir: Path) -> dict[str, Any]:
    result = Result()
    for filename in REQUIRED_FILES:
        result.check(f"required_file_exists:{filename}", (artifact_dir / filename).exists(), rel(artifact_dir / filename))
    if not all(check["status"] == "pass" for check in result.checks):
        return {"ok": False, "artifact_dir": rel(artifact_dir), "checks": result.checks}

    manifest = read_json(artifact_dir / "manifest.json", result)
    report = read_json(artifact_dir / "sanitized_report.json", result)
    input_index = read_json(artifact_dir / "input_artifact_index.json", result)
    claim_audit = read_json(artifact_dir / "claim_support_audit.json", result)
    forbidden_audit = read_json(artifact_dir / "forbidden_semantics_audit.json", result)
    report_md = read_text(artifact_dir / "sanitized_report.md", result)

    missing_fields = [field for field in REQUIRED_MANIFEST_FIELDS if field not in manifest]
    result.check("manifest_required_fields_present", not missing_fields, ",".join(missing_fields))
    result.check("manifest_artifact_type", manifest.get("artifact_type") == "tradingagents_readonly_analysis", repr(manifest.get("artifact_type")))
    result.check("manifest_schema_version", manifest.get("schema_version") == "tradingagents_readonly_analysis_v1", repr(manifest.get("schema_version")))
    result.check("manifest_analysis_name", manifest.get("analysis_name") == "tradingagents_readonly", repr(manifest.get("analysis_name")))
    result.check("manifest_created_at_iso", isinstance(manifest.get("created_at"), str) and bool(ISO_RE.match(manifest["created_at"])), repr(manifest.get("created_at")))
    result.check("manifest_signal_asof_date", isinstance(manifest.get("signal_asof"), str) and bool(DATE_RE.match(manifest["signal_asof"])), repr(manifest.get("signal_asof")))
    result.check("manifest_target_date", isinstance(manifest.get("target_date"), str) and bool(DATE_RE.match(manifest["target_date"])), repr(manifest.get("target_date")))
    result.check("manifest_output_report", manifest.get("output_report") == "sanitized_report.md", repr(manifest.get("output_report")))
    result.check("manifest_quality_status_allowed", manifest.get("quality_status") in {"pass", "warning", "failed"}, repr(manifest.get("quality_status")))
    result.check("manifest_production_trade_disabled", manifest.get("production_trade_enabled") is False, repr(manifest.get("production_trade_enabled")))
    result.check("manifest_true_safety_flags", all(manifest.get(flag) is True for flag in TRUE_FLAGS), ",".join(flag for flag in TRUE_FLAGS if manifest.get(flag) is not True))
    validate_runtime_mode(result, manifest, artifact_dir)

    source = manifest.get("source")
    result.check("manifest_source_object", isinstance(source, dict), repr(source))
    if isinstance(source, dict):
        result.check("manifest_source_repo_local", source.get("project_path") == "third_party/tradingagents" and source.get("vendored") is True, repr(source))
        result.check("manifest_selected_analysts_list", isinstance(source.get("selected_analysts"), list) and bool(source.get("selected_analysts")), repr(source.get("selected_analysts")))

    result.check("input_index_readonly", input_index.get("readonly_artifact_only") is True, repr(input_index))
    result.check("claim_support_audit_ok", claim_audit.get("ok") is True, repr(claim_audit.get("ok")))
    result.check("forbidden_semantics_audit_ok", forbidden_audit.get("ok") is True, repr(forbidden_audit.get("ok")))
    result.check("forbidden_audit_checked_sanitized_files", {"sanitized_report.md", "sanitized_report.json"}.issubset(set(forbidden_audit.get("checked_files", []))), repr(forbidden_audit.get("checked_files")))

    result.check("sanitized_report_schema_version", report.get("schema_version") == "tradingagents_sanitized_report_v1", repr(report.get("schema_version")))
    result.check("sanitized_report_run_id_matches", report.get("run_id") == manifest.get("run_id"), f"{report.get('run_id')} vs {manifest.get('run_id')}")
    result.check("sanitized_report_dates_match_manifest", report.get("signal_asof") == manifest.get("signal_asof") and report.get("target_date") == manifest.get("target_date"), repr(report))
    result.check("sanitized_report_symbols_nonempty", isinstance(report.get("symbols"), list) and bool(report.get("symbols")), repr(report.get("symbols")))
    result.check("sanitized_report_disclaimer", report.get("research_only_disclaimer") == "仅供研究观察，不构成交易建议；不代表买卖、仓位、胜率或收益承诺。", repr(report.get("research_only_disclaimer")))

    symbol_errors: list[str] = []
    run_mode = manifest.get("run_mode") or "fixture_dry_run"
    label_errors: list[str] = []
    for index, item in enumerate(report.get("symbols", []) if isinstance(report.get("symbols"), list) else []):
        if not isinstance(item, dict):
            symbol_errors.append(f"{index}:not_object")
            continue
        required = {
            "symbol",
            "instrument",
            "source_context",
            "research_summary",
            "bull_points",
            "bear_points",
            "risk_review_points",
            "data_limitations",
            "human_review_questions",
            "forbidden_decision_removed",
            "raw_decision_label_removed",
        }
        missing = sorted(required - set(item))
        if missing:
            symbol_errors.append(f"{index}:missing:{','.join(missing)}")
        if item.get("forbidden_decision_removed") is not True or item.get("raw_decision_label_removed") is not True:
            symbol_errors.append(f"{index}:decision_flags_not_true")
        if run_mode == "controlled_real_run":
            if item.get("external_sections_removed") is not True:
                symbol_errors.append(f"{index}:external_sections_not_removed")
            label_result = validate_research_labels(item.get("research_labels"))
            if label_result:
                label_errors.append(f"{index}:{'|'.join(label_result)}")
        elif "research_labels" in item:
            label_result = validate_research_labels(item.get("research_labels"))
            if label_result:
                label_errors.append(f"{index}:{'|'.join(label_result)}")
    result.check("sanitized_report_symbol_fields", not symbol_errors, ";".join(symbol_errors))
    result.check("sanitized_report_research_labels_shape", not label_errors, ";".join(label_errors))

    sanitized_json_blob = json.dumps(report, ensure_ascii=False, sort_keys=True)
    manifest_display_blob = json.dumps(
        {k: v for k, v in manifest.items() if k not in {"raw_untrusted_files", "sanitizer_audit"}},
        ensure_ascii=False,
        sort_keys=True,
    )
    field_offenders = find_forbidden_fields(report) + find_forbidden_fields(manifest)
    result.check("forbidden_fields_absent", not field_offenders, ",".join(field_offenders))
    text_offenders = scan_text("sanitized_report.json", sanitized_json_blob) + scan_text("sanitized_report.md", report_md) + scan_text("manifest.json", manifest_display_blob)
    result.check("forbidden_semantics_absent_from_display_files", not text_offenders, json.dumps(text_offenders, ensure_ascii=False))

    validate_raw_files(result, artifact_dir, manifest, forbidden_audit)
    return {
        "ok": result.ok,
        "artifact_dir": rel(artifact_dir),
        "check_count": len(result.checks),
        "checks": result.checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate TradingAgents readonly analysis artifact.")
    parser.add_argument("artifact_dir", help="Artifact directory.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = validate(Path(args.artifact_dir))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("ok=" + str(payload["ok"]).lower())
        print("check_count=" + str(payload.get("check_count", 0)))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
