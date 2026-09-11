from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "qlib_pipeline/examples/tw/run_option_c_yahoo_scrapling_refresh.py"


def _tree() -> ast.Module:
    return ast.parse(SCRIPT.read_text(encoding="utf-8"))


def _call_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            names.add(child.func.id)
    return names


def _literal_strings(node: ast.AST) -> set[str]:
    values: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            values.add(child.value)
    return values


def _imported_roots(node: ast.AST) -> set[str]:
    roots: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Import):
            for alias in child.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(child, ast.ImportFrom) and child.module:
            roots.add(child.module.split(".")[0])
    return roots


def _isolated_script_namespace(*function_names: str) -> dict[str, Any]:
    tree = _tree()
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            selected.append(node)
            break
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in function_names:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    namespace: dict[str, Any] = {
        "Any": Any,
        "argparse": argparse,
        "Path": Path,
        "ROOT": ROOT / "qlib_pipeline",
        "PBPR_PROVIDER_BRIDGE_ARTIFACT_ROOT": ROOT / "data_tw/experiments/provider_bridge_productionization",
    }
    exec(compile(ast.fix_missing_locations(module), str(SCRIPT), "exec"), namespace)
    return namespace


def _is_args_provider_only(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "provider_only"
        and isinstance(node.value, ast.Name)
        and node.value.id == "args"
    )


def test_provider_only_cli_aliases_exist() -> None:
    strings = _literal_strings(_tree())
    assert "--provider-only" in strings
    assert "--no-model-smoke" in strings
    assert "provider_only" in strings
    assert "--local-non-material-paths" in strings
    assert "--skip-existing" in strings
    assert "--continue-on-error" in strings


def test_provider_only_branch_stops_before_staged_model_smoke() -> None:
    main = next(node for node in _tree().body if isinstance(node, ast.FunctionDef) and node.name == "main")
    provider_only_if = next(
        node
        for node in ast.walk(main)
        if isinstance(node, ast.If) and _is_args_provider_only(node.test)
    )

    true_branch = ast.Module(body=provider_only_if.body, type_ignores=[])
    true_calls = _call_names(true_branch)
    true_strings = _literal_strings(true_branch)

    assert "staged_model_smoke" not in true_calls
    assert "skipped_model_smoke_provider_only" in true_calls
    assert "provider_only_refresh_complete_waiting_for_review" in true_strings
    assert "stopped_before_staged_model_smoke" in true_strings

    false_branch = ast.Module(body=provider_only_if.orelse, type_ignores=[])
    assert "staged_model_smoke" in _call_names(false_branch)


def test_provider_only_skip_helper_records_not_run_model_smoke_status() -> None:
    helper = next(
        node
        for node in _tree().body
        if isinstance(node, ast.FunctionDef) and node.name == "skipped_model_smoke_provider_only"
    )
    strings = _literal_strings(helper)
    assert "skipped_provider_only" in strings
    assert "provider_only_mode_stops_before_staged_model_smoke" in strings
    assert "model_inference_input_built" in strings
    assert "score_job_built" in strings
    assert "model_signal_artifact_built" in strings


def test_yahoo_access_adapter_cli_exposes_explicit_yahoo_only_controls() -> None:
    tree = _tree()
    strings = _literal_strings(tree)
    assert "--yahoo-header" in strings
    assert "--yahoo-cookie" in strings
    assert "--yahoo-crumb" in strings
    assert "--yahoo-quote-page-warmup" in strings
    assert "--yahoo-session-warmup" in strings
    assert "--http-403-backoff-seconds" in strings
    assert "Yahoo-only; no yfinance; no FinMind fallback; no mixed provider; no cached prior-asof fill" in strings
    assert "yfinance" not in _imported_roots(tree)
    assert "finmind" not in {name.lower() for name in _imported_roots(tree)}


def test_yahoo_access_adapter_builds_headers_cookie_crumb_proxy_without_fallback() -> None:
    ns = _isolated_script_namespace("parse_yahoo_headers", "build_yahoo_access_adapter", "describe_yahoo_access_adapter")
    args = argparse.Namespace(
        yahoo_header=["User-Agent=PBPR-review", "Accept-Language: zh-TW"],
        yahoo_cookie="A=B",
        yahoo_crumb="crumb-token",
        proxy="http://127.0.0.1:7890",
        yahoo_quote_page_warmup=True,
        yahoo_session_warmup=True,
        http_403_backoff_seconds=3.0,
    )
    adapter = ns["build_yahoo_access_adapter"](args)
    assert adapter["request_kwargs"]["headers"]["User-Agent"] == "PBPR-review"
    assert adapter["request_kwargs"]["headers"]["Accept-Language"] == "zh-TW"
    assert adapter["request_kwargs"]["headers"]["Cookie"] == "A=B"
    assert adapter["crumb"] == "crumb-token"
    assert adapter["request_kwargs"]["proxy"] == "http://127.0.0.1:7890"
    assert adapter["provider_fallback_allowed"] is False

    described = ns["describe_yahoo_access_adapter"](adapter)
    assert described["cookie_provided"] is True
    assert described["crumb_provided"] is True
    assert described["fallback_provider"] == ""
    assert "Cookie" in described["header_names"]


def test_yahoo_http_403_diagnostic_has_backoff_advice_and_no_provider_switch() -> None:
    ns = _isolated_script_namespace("classify_yahoo_fetch_failure")
    diagnostic = ns["classify_yahoo_fetch_failure"](403, "http_status:403:Forbidden")
    assert diagnostic["category"] == "yahoo_http_403_access_blocked"
    assert diagnostic["http_status"] == 403
    assert diagnostic["retry_scope"] == "same_yahoo_chart_request_only"
    assert diagnostic["provider_fallback_allowed"] is False
    assert diagnostic["provider_fallback_attempted"] is False
    assert diagnostic["fallback_provider"] == ""

    helper = next(
        node
        for node in _tree().body
        if isinstance(node, ast.FunctionDef) and node.name == "classify_yahoo_fetch_failure"
    )
    calls = _call_names(helper)
    assert "staged_model_smoke" not in calls
    assert "write_json" not in calls


def test_pbpr_material_path_guard_accepts_absolute_repo_artifact_paths() -> None:
    ns = _isolated_script_namespace("_is_relative_to", "validate_pbpr_material_paths")
    root = ROOT / "data_tw/experiments/provider_bridge_productionization/pbpr2a_u_yahoo_session_and_absolute_path_repair"
    report = root / "execution_report.md"
    guard = ns["validate_pbpr_material_paths"](str(root), str(report), material=True)
    assert guard["status"] == "pass"
    assert guard["output_root_is_absolute_input"] is True
    assert guard["report_path_is_absolute_input"] is True
    assert guard["output_root_contained"] is True
    assert guard["report_path_contained"] is True


def test_pbpr_material_path_guard_rejects_relative_and_external_paths() -> None:
    ns = _isolated_script_namespace("_is_relative_to", "validate_pbpr_material_paths")
    valid_report = ROOT / "data_tw/experiments/provider_bridge_productionization/pbpr2a_u_yahoo_session_and_absolute_path_repair/report.md"
    try:
        ns["validate_pbpr_material_paths"]("data_tw/experiments/provider_bridge_productionization/pbpr2a_u", str(valid_report), material=True)
    except ValueError as exc:
        assert "material_pbpr_output_root_must_be_absolute" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("relative material output-root should hard-fail")

    valid_root = ROOT / "data_tw/experiments/provider_bridge_productionization/pbpr2a_u_yahoo_session_and_absolute_path_repair"
    try:
        ns["validate_pbpr_material_paths"](str(valid_root), "/tmp/pbpr2a_u_report.md", material=True)
    except ValueError as exc:
        assert "material_pbpr_report_path_outside_required_artifact_root" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("external material report-path should hard-fail")

    local_guard = ns["validate_pbpr_material_paths"]("relative/local", "relative/report.md", material=False)
    assert local_guard["status"] == "skipped_non_material_local_mode"


def test_symbol_failure_ledger_schema_marks_partial_resume_safe_and_no_pbpr3() -> None:
    ns = _isolated_script_namespace("no_provider_fallback_flags", "build_symbol_failure_ledger", "build_readiness_gate")
    ns["utc_now"] = lambda: "2026-07-09T00:00:00+00:00"
    symbols = ["TW2330", "TW3293", "TW9999"]
    fetch_report = {
        "status": "fail",
        "symbols_success_list": ["TW2330"],
        "symbols_existing_reused": ["TW2330"],
        "symbols_empty": ["TW3293"],
        "symbols_failed": {
            "TW3293": [
                {
                    "ticker": "3293.TWO",
                    "http_status": 404,
                    "diagnostic": {
                        "category": "yahoo_http_error",
                        "provider_fallback_allowed": False,
                        "provider_fallback_attempted": False,
                        "fallback_provider": "",
                    },
                }
            ]
        },
        "symbols_unattempted": ["TW9999"],
        "per_symbol": [
            {"symbol": "TW2330", "status": "existing_reused", "attempts": [], "existing_reused": True},
            {"symbol": "TW3293", "status": "empty_or_failed", "attempts": [{"http_status": 404}], "existing_reused": False},
            {"symbol": "TW9999", "status": "unattempted", "attempts": [], "existing_reused": False},
        ],
        "http_status_counts": {"404": 1},
        "http_diagnostic_counts": {"yahoo_http_error": 1},
    }
    ledger = ns["build_symbol_failure_ledger"](
        symbols,
        fetch_report,
        {"status": "fail", "missing_symbols": ["TW9999"], "empty_symbols": [], "issues_sample": {}},
        {"status": "not_run"},
        skip_existing=True,
        continue_on_error=True,
    )

    assert ledger["symbols_expected"] == 3
    assert ledger["symbols_success"] == ["TW2330"]
    assert ledger["symbols_existing_reused"] == ["TW2330"]
    assert ledger["symbols_empty"] == ["TW3293"]
    assert ledger["symbols_unattempted"] == ["TW9999"]
    assert ledger["partial_candidate_only"] is True
    assert ledger["resume_safe"] is True
    assert ledger["provider_fallback_allowed"] is False
    assert ledger["provider_fallback_attempted"] is False
    assert ledger["pbpr3_authorized"] is False

    readiness = ns["build_readiness_gate"](ledger)
    assert readiness["readiness_ready"] is False
    assert readiness["provider_candidate_readiness_written"] is False
    assert readiness["canonical_bridge_readiness_written"] is False
    assert readiness["pbpr3_authorized"] is False


def test_runner_writes_ledger_and_summary_flags_before_execution_summary() -> None:
    tree = _tree()
    strings = _literal_strings(tree)
    assert "symbol_failure_ledger.json" in strings
    assert "execution_summary.json" in strings
    assert "exact_argv" in strings
    assert "proxy_value" in strings
    assert "cookie_provided" in strings
    assert "header_override_provided" in strings
    assert "crumb_provided" in strings
    assert "skip_existing" in strings
    assert "continue_on_error" in strings
    assert "pbpr3_authorized" in strings
    assert "provider_candidate_readiness_written" in strings
    assert "canonical_bridge_readiness_written" in strings

    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    calls = [
        child
        for child in ast.walk(main)
        if isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id == "write_json"
        and child.args
    ]
    write_targets: set[str] = set()
    for call in calls:
        write_targets.update(_literal_strings(call.args[0]))
    assert "symbol_failure_ledger.json" in write_targets
    assert "execution_summary.json" in write_targets


def test_readiness_artifacts_are_not_written_by_runner() -> None:
    tree = _tree()
    write_json_calls = [
        child
        for child in ast.walk(tree)
        if isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id == "write_json"
        and child.args
    ]
    write_target_strings: set[str] = set()
    for call in write_json_calls:
        write_target_strings.update(_literal_strings(call.args[0]))
    assert "provider_candidate_readiness.json" not in write_target_strings
    assert "canonical_bridge_readiness.json" not in write_target_strings
