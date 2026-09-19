#!/usr/bin/env python3
"""Run the repo-local TradingAgents readonly adapter in safe dry-run mode."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]


def _load_adapter() -> ModuleType:
    path = ROOT / "backend/app/services/tradingagents_readonly_adapter.py"
    spec = importlib.util.spec_from_file_location("tradingagents_readonly_adapter_cli", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ADAPTER = _load_adapter()
DEFAULT_FIXTURE = _ADAPTER.DEFAULT_FIXTURE
DEFAULT_LLM_BASE_URL = _ADAPTER.DEFAULT_LLM_BASE_URL
DEFAULT_DEEP_MODEL = _ADAPTER.DEFAULT_DEEP_MODEL
DEFAULT_QUICK_MODEL = _ADAPTER.DEFAULT_QUICK_MODEL
run_tradingagents_readonly_analysis = _ADAPTER.run_tradingagents_readonly_analysis


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run TradingAgents readonly analysis adapter.")
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE), help="Mock raw state JSON or fixture directory.")
    parser.add_argument("--output-dir", required=True, help="Artifact output directory.")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--dry-run", action="store_true", default=True, help="Use fixture/mock dry-run mode. This is the default.")
    parser.add_argument("--real-run", action="store_true", help="Request controlled real runner mode. Requires explicit env gates.")
    parser.add_argument("--symbol", default="2330.TW", help="Single symbol for controlled real run, e.g. 2330.TW.")
    parser.add_argument("--trade-date", default=None, help="YYYY-MM-DD date for controlled real run.")
    parser.add_argument("--selected-analysts", default="market,news", help="Comma-separated analysts, max 2. Allowed: market,news,fundamentals,social.")
    parser.add_argument("--llm-base-url", default=DEFAULT_LLM_BASE_URL, help="OpenAI-compatible base URL for controlled real run.")
    parser.add_argument("--deep-model", default=DEFAULT_DEEP_MODEL)
    parser.add_argument("--quick-model", default=DEFAULT_QUICK_MODEL)
    parser.add_argument("--json", action="store_true", help="Print full JSON result.")
    args = parser.parse_args(argv)

    selected_analysts = [item.strip() for item in str(args.selected_analysts or "").split(",") if item.strip()]
    result = run_tradingagents_readonly_analysis(
        fixture=args.fixture,
        output_dir=args.output_dir,
        run_id=args.run_id,
        dry_run=not args.real_run,
        validate_output=True,
        symbol=args.symbol,
        trade_date=args.trade_date,
        selected_analysts=selected_analysts,
        llm_base_url=args.llm_base_url,
        deep_model=args.deep_model,
        quick_model=args.quick_model,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={str(result['ok']).lower()}")
        print(f"status={result['status']}")
        print(f"mode={result['mode']}")
        print(f"artifact_dir={result['artifact_dir']}")
        if not result["ok"] and result.get("reason"):
            print(f"reason={result['reason']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
