from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE = ROOT / "data_tw/golden_samples/tradingagents_readonly_analysis/pass_minimal/mock_raw_state.json"
DEFAULT_ARTIFACT_ROOT = ROOT / "data_tw/artifacts/analysis/tradingagents_readonly"
ENABLE_REAL_RUN_ENV = "TRADINGAGENTS_READONLY_ENABLE_REAL_RUN"
REAL_RUN_CONFIRM_ENV = "TRADINGAGENTS_READONLY_REAL_RUN_CONFIRM"
REAL_RUN_CONFIRM_VALUE = "manual_real_run_ack"
DEFAULT_LLM_BASE_URL = "https://chat.pku.edu.cn/v1"
DEFAULT_DEEP_MODEL = "gpt-5.5"
DEFAULT_QUICK_MODEL = "gpt-5.4-mini"
DEFAULT_SELECTED_ANALYSTS = ("market", "news")
LOCAL_MARKET_DATA_VENDOR = "quantdinger_tw"


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_builder() -> ModuleType:
    return _load_module(
        "build_tradingagents_readonly_analysis_artifact",
        ROOT / "scripts/build_tradingagents_readonly_analysis_artifact.py",
    )


def _load_validator() -> ModuleType:
    return _load_module(
        "validate_tradingagents_readonly_analysis_artifact",
        ROOT / "scripts/validate_tradingagents_readonly_analysis_artifact.py",
    )


def _load_local_data_provider() -> ModuleType:
    return _load_module(
        "tradingagents_quantdinger_data_provider",
        ROOT / "backend/app/services/tradingagents_quantdinger_data_provider.py",
    )


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def real_run_enabled(env: dict[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return _truthy(source.get(ENABLE_REAL_RUN_ENV))


def resolve_fixture_path(path: str | Path | None = None) -> Path:
    fixture = Path(path) if path is not None else DEFAULT_FIXTURE
    if fixture.is_dir():
        fixture = fixture / "mock_raw_state.json"
    return fixture


def default_output_dir(run_id: str | None = None) -> Path:
    return DEFAULT_ARTIFACT_ROOT / (run_id or "dry_run")


def _safe_run_component(value: str, *, label: str) -> str:
    clean = str(value or "").strip()
    if not clean or any(part in clean for part in ("/", "\\", "..")):
        raise ValueError(f"invalid_{label}:{value!r}")
    return clean


def _normalize_symbol(symbol: str) -> str:
    clean = str(symbol or "").strip().upper()
    if clean.startswith("TW") and clean[2:].isdigit():
        clean = clean[2:] + ".TW"
    if clean.isdigit() and len(clean) == 4:
        clean = clean + ".TW"
    if not clean or any(part in clean for part in ("/", "\\", "..")):
        raise ValueError(f"invalid_symbol:{symbol!r}")
    return clean


def _display_symbol(symbol: str) -> str:
    clean = str(symbol or "").strip().upper()
    if clean.endswith(".TW") and clean[:-3].isdigit():
        return clean[:-3]
    if clean.startswith("TW") and clean[2:].isdigit():
        return clean[2:]
    return clean


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def _runtime_paths(run_id: str) -> dict[str, Path]:
    safe_run_id = _safe_run_component(run_id, label="run_id")
    return {
        "results_dir": DEFAULT_ARTIFACT_ROOT / "_raw_runs" / safe_run_id,
        "data_cache_dir": DEFAULT_ARTIFACT_ROOT / "_cache",
        "memory_log_path": DEFAULT_ARTIFACT_ROOT / "_memory" / "trading_memory.md",
    }


def _safe_output_dir(output_dir: str | Path | None, run_id: str) -> Path:
    candidate = Path(output_dir) if output_dir is not None else default_output_dir(run_id)
    candidate = candidate.resolve()
    root = DEFAULT_ARTIFACT_ROOT.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"real_run_output_dir_outside_root:{candidate}") from exc
    if candidate.name.startswith("_"):
        raise ValueError(f"real_run_output_dir_reserved:{candidate}")
    return candidate


def _selected_analysts(values: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    allowed = {"market", "news", "fundamentals", "social"}
    analysts = tuple(str(item).strip().lower() for item in (values or DEFAULT_SELECTED_ANALYSTS) if str(item).strip())
    if not analysts:
        analysts = DEFAULT_SELECTED_ANALYSTS
    invalid = [item for item in analysts if item not in allowed]
    if invalid:
        raise ValueError(f"invalid_selected_analysts:{','.join(invalid)}")
    if len(analysts) > 2:
        raise ValueError("selected_analysts_limit_exceeded:max_2")
    return analysts


def build_real_run_config(
    *,
    run_id: str,
    llm_base_url: str | None = None,
    deep_model: str | None = None,
    quick_model: str | None = None,
    output_language: str = "Chinese",
) -> dict[str, Any]:
    vendor_root = ROOT / "third_party/tradingagents"
    if str(vendor_root) not in sys.path:
        sys.path.insert(0, str(vendor_root))
    original_dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        from tradingagents.default_config import DEFAULT_CONFIG  # type: ignore
    finally:
        sys.dont_write_bytecode = original_dont_write_bytecode

    paths = _runtime_paths(run_id)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    paths["results_dir"].mkdir(parents=True, exist_ok=True)
    paths["data_cache_dir"].mkdir(parents=True, exist_ok=True)
    paths["memory_log_path"].parent.mkdir(parents=True, exist_ok=True)
    config = dict(DEFAULT_CONFIG)
    config.update({
        "results_dir": str(paths["results_dir"]),
        "data_cache_dir": str(paths["data_cache_dir"]),
        "memory_log_path": str(paths["memory_log_path"]),
        "llm_provider": "openai",
        "backend_url": (llm_base_url or os.getenv("TRADINGAGENTS_LLM_BACKEND_URL") or DEFAULT_LLM_BASE_URL).rstrip("/"),
        "deep_think_llm": deep_model or os.getenv("TRADINGAGENTS_DEEP_THINK_LLM") or DEFAULT_DEEP_MODEL,
        "quick_think_llm": quick_model or os.getenv("TRADINGAGENTS_QUICK_THINK_LLM") or DEFAULT_QUICK_MODEL,
        "output_language": output_language,
        "checkpoint_enabled": False,
        "max_debate_rounds": 1,
        "max_risk_discuss_rounds": 1,
        "max_recur_limit": 80,
        "data_vendors": {
            "core_stock_apis": LOCAL_MARKET_DATA_VENDOR,
            "technical_indicators": LOCAL_MARKET_DATA_VENDOR,
            "news_data": LOCAL_MARKET_DATA_VENDOR,
            "fundamental_data": LOCAL_MARKET_DATA_VENDOR,
            "macro_data": LOCAL_MARKET_DATA_VENDOR,
            "prediction_markets": LOCAL_MARKET_DATA_VENDOR,
        },
        "tool_vendors": {
            "get_stock_data": LOCAL_MARKET_DATA_VENDOR,
            "get_indicators": LOCAL_MARKET_DATA_VENDOR,
            "get_news": LOCAL_MARKET_DATA_VENDOR,
            "get_global_news": LOCAL_MARKET_DATA_VENDOR,
            "get_insider_transactions": LOCAL_MARKET_DATA_VENDOR,
            "get_fundamentals": LOCAL_MARKET_DATA_VENDOR,
            "get_balance_sheet": LOCAL_MARKET_DATA_VENDOR,
            "get_cashflow": LOCAL_MARKET_DATA_VENDOR,
            "get_income_statement": LOCAL_MARKET_DATA_VENDOR,
            "get_macro_indicators": LOCAL_MARKET_DATA_VENDOR,
            "get_prediction_markets": LOCAL_MARKET_DATA_VENDOR,
        },
    })
    return config


def _state_text(final_state: dict[str, Any], key: str) -> str:
    value = final_state.get(key)
    return str(value or "").strip()


def _state_nested_text(final_state: dict[str, Any], outer: str, key: str) -> str:
    value = final_state.get(outer)
    if isinstance(value, dict):
        return str(value.get(key) or "").strip()
    return ""


def _real_raw_state(
    *,
    run_id: str,
    symbol: str,
    trade_date: str,
    selected_analysts: tuple[str, ...],
    final_state: dict[str, Any],
    decision: Any,
    runtime_paths: dict[str, Path],
    config: dict[str, Any],
) -> dict[str, Any]:
    display_symbol = _display_symbol(symbol)
    market = _state_text(final_state, "market_report")
    news = _state_text(final_state, "news_report")
    fundamentals = _state_text(final_state, "fundamentals_report")
    sentiment = _state_text(final_state, "sentiment_report")
    bull = _state_nested_text(final_state, "investment_debate_state", "bull_history")
    bear = _state_nested_text(final_state, "investment_debate_state", "bear_history")
    risk = _state_nested_text(final_state, "risk_debate_state", "history")
    final_decision = _state_text(final_state, "final_trade_decision")
    raw_report = "\n\n".join(
        text
        for text in [
            "# Raw TradingAgents controlled real run",
            f"run_id: {run_id}",
            f"symbol: {symbol}",
            f"decision_label_removed_by_sanitizer: {decision}",
            "## Market",
            market,
            "## News",
            news,
            "## Fundamentals",
            fundamentals,
            "## Sentiment",
            sentiment,
            "## Final",
            final_decision,
        ]
        if text
    )
    return {
        "run_id": run_id,
        "run_mode": "controlled_real_run",
        "manual_run_only": True,
        "no_latest_pointer_update": True,
        "signal_asof": trade_date,
        "target_date": trade_date,
        "selected_analysts": list(selected_analysts),
        "tradingagents_version": "repo-local-controlled-real-run",
        "upstream_reference": "third_party/tradingagents",
        "runtime_paths": {key: _repo_relative(path) for key, path in runtime_paths.items()},
        "safety": {
            "no_openai_call": False,
            "no_network_call": False,
            "no_tradingagents_graph_call": False,
        },
        "input_artifacts": [{
            "artifact_type": "TradingAgentsControlledRealRunInput",
            "symbol": symbol,
            "trade_date": trade_date,
            "llm_provider": config.get("llm_provider"),
            "backend_url": config.get("backend_url"),
            "deep_think_llm": config.get("deep_think_llm"),
            "quick_think_llm": config.get("quick_think_llm"),
            "selected_analysts": list(selected_analysts),
            "status": "manual_controlled_real_run",
        }],
        "symbols": [{
            "symbol": display_symbol,
            "instrument": f"TW{display_symbol}" if display_symbol.isdigit() else symbol,
            "source_context": {
                "context_source": "controlled_real_run",
                "tradingagents_symbol": symbol,
                "decision_label_removed": True,
            },
            "research_summary": " ".join(text for text in [market, news, fundamentals, sentiment] if text)[:4000],
            "bull_points": [bull] if bull else [],
            "bear_points": [bear] if bear else [],
            "risk_review_points": [risk, final_decision] if risk or final_decision else [],
            "data_limitations": [
                "受控真实运行会调用 LLM 与外部数据工具，输出仅作为人工复核线索。",
                "原始方向性标签由 sanitizer 移除，不能作为策略证据或默认切换依据。",
            ],
            "human_review_questions": [
                "这些外部论点是否能被本项目只读 artifact 独立支持？",
                "是否存在与当前 qlib/LTR 候选上下文冲突的事实或口径？",
            ],
        }],
        "raw_complete_report": raw_report,
    }


def _run_real_graph(
    *,
    symbol: str,
    trade_date: str,
    selected_analysts: tuple[str, ...],
    config: dict[str, Any],
) -> tuple[dict[str, Any], Any]:
    vendor_root = ROOT / "third_party/tradingagents"
    if str(vendor_root) not in sys.path:
        sys.path.insert(0, str(vendor_root))
    original_dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph  # type: ignore
    finally:
        sys.dont_write_bytecode = original_dont_write_bytecode

    local_data_provider = _load_local_data_provider()
    local_data_provider.install_tradingagents_local_data_provider()
    graph = TradingAgentsGraph(selected_analysts=selected_analysts, debug=False, config=config)
    final_state, decision = graph.propagate(symbol, trade_date, asset_type="stock")
    return final_state, decision


def run_tradingagents_readonly_analysis(
    *,
    fixture: str | Path | None = None,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    dry_run: bool = True,
    enable_real_run: bool | None = None,
    validate_output: bool = True,
    symbol: str = "2330.TW",
    trade_date: str | None = None,
    selected_analysts: list[str] | tuple[str, ...] | None = None,
    llm_base_url: str | None = None,
    deep_model: str | None = None,
    quick_model: str | None = None,
    graph_runner: Any | None = None,
) -> dict[str, Any]:
    enabled = real_run_enabled() if enable_real_run is None else enable_real_run
    real_requested = not dry_run
    safe_run_id = _safe_run_component(run_id or ("real_" + _normalize_symbol(symbol).replace(".", "_") + "_" + str(trade_date or "latest")), label="run_id")
    out_dir = Path(output_dir) if output_dir is not None else default_output_dir(safe_run_id)

    if real_requested and not enabled:
        return {
            "ok": False,
            "status": "blocked",
            "reason": "real_run_disabled",
            "mode": "disabled_real_request",
            "artifact_dir": str(out_dir),
            "real_run_enabled": enabled,
            "safety": {
                "no_openai_call": True,
                "no_network_call": True,
                "no_tradingagents_graph_call": True,
                "no_latest_pointer_update": True,
            },
        }

    if real_requested:
        if os.getenv(REAL_RUN_CONFIRM_ENV) != REAL_RUN_CONFIRM_VALUE and graph_runner is None:
            return {
                "ok": False,
                "status": "blocked",
                "reason": "real_run_confirmation_missing",
                "required_env": f"{REAL_RUN_CONFIRM_ENV}={REAL_RUN_CONFIRM_VALUE}",
                "mode": "real_requested",
                "artifact_dir": str(out_dir),
                "real_run_enabled": enabled,
                "safety": {
                    "no_latest_pointer_update": True,
                    "manual_run_only": True,
                },
            }
        symbol_value = _normalize_symbol(symbol)
        trade_date_value = str(trade_date or "").strip()
        if not trade_date_value:
            return {
                "ok": False,
                "status": "blocked",
                "reason": "trade_date_required",
                "mode": "real_requested",
                "artifact_dir": str(out_dir),
                "real_run_enabled": enabled,
            }
        analysts = _selected_analysts(selected_analysts)
        out_dir = _safe_output_dir(output_dir, safe_run_id)
        runtime_paths = _runtime_paths(safe_run_id)
        config = build_real_run_config(
            run_id=safe_run_id,
            llm_base_url=llm_base_url,
            deep_model=deep_model,
            quick_model=quick_model,
        )
        runner = graph_runner or _run_real_graph
        try:
            final_state, decision = runner(
                symbol=symbol_value,
                trade_date=trade_date_value,
                selected_analysts=analysts,
                config=config,
            )
        except Exception as exc:
            return {
                "ok": False,
                "status": "failed",
                "reason": "controlled_real_run_failed",
                "error_type": type(exc).__name__,
                "error": str(exc)[:1000],
                "mode": "controlled_real_run",
                "artifact_dir": str(out_dir),
                "run_id": safe_run_id,
                "symbol": symbol_value,
                "trade_date": trade_date_value,
                "selected_analysts": list(analysts),
                "real_run_enabled": enabled,
                "runtime_paths": {key: str(path) for key, path in runtime_paths.items()},
                "safety": {
                    "manual_run_only": True,
                    "no_latest_pointer_update": True,
                    "artifact_created": False,
                    "sanitized_artifact_required": True,
                },
            }
        raw_state = _real_raw_state(
            run_id=safe_run_id,
            symbol=symbol_value,
            trade_date=trade_date_value,
            selected_analysts=analysts,
            final_state=final_state,
            decision=decision,
            runtime_paths=runtime_paths,
            config=config,
        )
        builder = _load_builder()
        validator = _load_validator()
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
            json.dump(raw_state, handle, ensure_ascii=False)
            temp_raw = Path(handle.name)
        try:
            build_result = builder.build_artifact(
                fixture_path=temp_raw,
                output_dir=out_dir,
                run_id=safe_run_id,
                quality_status="warning",
                write_raw=True,
            )
        finally:
            try:
                temp_raw.unlink()
            except OSError:
                pass
        validation = validator.validate(out_dir) if validate_output else {"ok": True, "skipped": True}
        ok = bool(build_result.get("ok")) and bool(validation.get("ok"))
        return {
            "ok": ok,
            "status": "pass" if ok else "failed",
            "mode": "controlled_real_run",
            "artifact_dir": str(out_dir),
            "run_id": safe_run_id,
            "symbol": symbol_value,
            "trade_date": trade_date_value,
            "selected_analysts": list(analysts),
            "real_run_enabled": enabled,
            "runtime_paths": {key: str(path) for key, path in runtime_paths.items()},
            "build": build_result,
            "validation": validation,
            "safety": {
                "manual_run_only": True,
                "no_latest_pointer_update": True,
                "sanitized_artifact_required": True,
            },
        }

    fixture_path = resolve_fixture_path(fixture)
    builder = _load_builder()
    validator = _load_validator()

    build_result = builder.build_artifact(
        fixture_path=fixture_path,
        output_dir=out_dir,
        run_id=run_id,
        write_raw=True,
    )
    validation = validator.validate(out_dir) if validate_output else {"ok": True, "skipped": True}
    ok = bool(build_result.get("ok")) and bool(validation.get("ok"))
    return {
        "ok": ok,
        "status": "pass" if ok else "failed",
        "mode": "dry_run",
        "artifact_dir": str(out_dir),
        "fixture": str(fixture_path),
        "real_run_enabled": enabled,
        "build": build_result,
        "validation": validation,
        "safety": {
            "no_openai_call": True,
            "no_network_call": True,
            "no_tradingagents_graph_call": True,
            "no_latest_pointer_update": True,
        },
    }
