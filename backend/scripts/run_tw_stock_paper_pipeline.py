#!/usr/bin/env python3
"""Run TWStock rebalance plan -> paper preview -> quick-trade payload pipeline.

Default mode is dry-run and local-only. It does not write DB rows, does not call
Agent Gateway, and does not connect to IBKR unless --submit is explicitly used.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "run-tw-stock-paper-pipeline")
os.environ.setdefault("ADMIN_USER", "paper-pipeline")
os.environ.setdefault("ADMIN_PASSWORD", "paperpipelinepass")

from scripts.preview_tw_stock_paper_orders import (  # noqa: E402
    build_order_previews,
    load_json,
    parse_positions,
    parse_prices,
    parse_target_weights,
    resolve_prices,
)
from scripts.submit_tw_stock_paper_orders import build_quick_trade_payloads, build_report as build_submit_report, submit_payloads  # noqa: E402
from scripts.build_tw_stock_paper_execution_report import build_report as build_execution_report, render_markdown  # noqa: E402


def build_pipeline_report(*, preview: Dict[str, Any], submit_report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "market": "TWStock",
        "paper_only": True,
        "dry_run": bool(submit_report.get("dry_run")),
        "preview_summary": {
            "order_count": preview.get("order_count", 0),
            "blocked_count": preview.get("blocked_count", 0),
            "warnings": list(preview.get("warnings") or []),
        },
        "submit_summary": {
            "submit_candidate_count": submit_report.get("submit_candidate_count", 0),
            "skipped_count": submit_report.get("skipped_count", 0),
            "submitted_count": len(submit_report.get("submit_results") or []),
            "failed_submit_count": sum(1 for item in submit_report.get("submit_results") or [] if not item.get("ok")),
        },
        "preview": preview,
        "submit": submit_report,
    }


def evaluate_pipeline_guards(
    *,
    preview: Dict[str, Any],
    payloads: Sequence[Dict[str, Any]],
    fail_on_warning: bool = False,
    fail_on_blocked: bool = False,
    max_submit_candidates: int = 0,
) -> List[str]:
    errors: List[str] = []
    if fail_on_warning and preview.get("warnings"):
        errors.append("warnings_present")
    if fail_on_blocked and int(preview.get("blocked_count") or 0) > 0:
        errors.append("blocked_orders_present")
    if max_submit_candidates > 0 and len(payloads) > max_submit_candidates:
        errors.append("max_submit_candidates_exceeded")
    return errors


def run_pipeline(
    *,
    plan_json: str,
    positions_json: str = "",
    price_json: str = "",
    as_of: str = "",
    portfolio_value: float,
    lot_size: int = 1000,
    limit_buffer: float = 0.005,
    max_order_value: float = 0.0,
    max_total_buy_value: float = 0.0,
    allow_short: bool = False,
    submit: bool = False,
    api_base_url: str = "http://127.0.0.1:5000",
    agent_token: str = "",
    timeout: int = 20,
    fail_on_warning: bool = False,
    fail_on_blocked: bool = False,
    max_submit_candidates: int = 0,
) -> Dict[str, Any]:
    plan = load_json(plan_json)
    positions = parse_positions(load_json(positions_json))
    targets = parse_target_weights(plan)
    symbols = sorted(set(targets) | set(positions))
    prices = resolve_prices(symbols, parse_prices(load_json(price_json)), as_of or date.today().isoformat())
    preview = build_order_previews(
        target_weights=targets,
        current_positions=positions,
        prices=prices,
        portfolio_value=portfolio_value,
        lot_size=lot_size,
        limit_buffer=limit_buffer,
        max_order_value=max_order_value,
        max_total_buy_value=max_total_buy_value,
        allow_short=allow_short,
    )
    payloads = build_quick_trade_payloads(preview)
    guard_errors = evaluate_pipeline_guards(
        preview=preview,
        payloads=payloads,
        fail_on_warning=fail_on_warning,
        fail_on_blocked=fail_on_blocked,
        max_submit_candidates=max_submit_candidates,
    )
    results: List[Dict[str, Any]] = []
    if submit and guard_errors:
        raise ValueError("pipeline guard failed: " + ",".join(guard_errors))
    if submit:
        if not agent_token:
            raise ValueError("agent_token is required when submit=True")
        results = submit_payloads(payloads=payloads, api_base_url=api_base_url, agent_token=agent_token, timeout=timeout)
    submit_report = build_submit_report(preview=preview, payloads=payloads, submit_results=results)
    report = build_pipeline_report(preview=preview, submit_report=submit_report)
    report["guard_errors"] = guard_errors
    report["guards"] = {
        "fail_on_warning": bool(fail_on_warning),
        "fail_on_blocked": bool(fail_on_blocked),
        "max_submit_candidates": int(max_submit_candidates or 0),
    }
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run TWStock paper order pipeline from rebalance plan to quick-trade payloads.")
    parser.add_argument("--plan-json", required=True)
    parser.add_argument("--positions-json", default="")
    parser.add_argument("--price-json", default="")
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--portfolio-value", type=float, required=True)
    parser.add_argument("--lot-size", type=int, default=1000)
    parser.add_argument("--limit-buffer", type=float, default=0.005)
    parser.add_argument("--max-order-value", type=float, default=0.0)
    parser.add_argument("--max-total-buy-value", type=float, default=0.0)
    parser.add_argument("--allow-short", action="store_true")
    parser.add_argument("--fail-on-warning", action="store_true")
    parser.add_argument("--fail-on-blocked", action="store_true")
    parser.add_argument("--max-submit-candidates", type=int, default=0)
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--agent-token", default="")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--output-json", default="")
    parser.add_argument("--preview-output-json", default="")
    parser.add_argument("--submit-output-json", default="")
    parser.add_argument("--execution-report-json", default="", help="Optional output path for an auditable execution report. Requires --verify-json and --portfolio-summary-json.")
    parser.add_argument("--execution-report-md", default="", help="Optional Markdown execution report path. Requires --verify-json and --portfolio-summary-json.")
    parser.add_argument("--verify-json", default="", help="Order read-back verification JSON from verify_tw_stock_paper_orders.py.")
    parser.add_argument("--portfolio-summary-json", default="", help="Paper portfolio summary JSON from /portfolio/paper-summary.")
    return parser


def _write_json(path: str, payload: Dict[str, Any]) -> None:
    if not path:
        return
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: str, text: str) -> None:
    if not path:
        return
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def maybe_build_execution_report(*, pipeline_report: Dict[str, Any], verify_json: str = "", portfolio_summary_json: str = "") -> Dict[str, Any]:
    if not verify_json and not portfolio_summary_json:
        return {}
    if not verify_json or not portfolio_summary_json:
        raise ValueError("--verify-json and --portfolio-summary-json must be provided together for execution report output")
    return build_execution_report(
        pipeline=pipeline_report,
        verification=load_json(verify_json),
        portfolio_summary=load_json(portfolio_summary_json),
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        report = run_pipeline(
            plan_json=args.plan_json,
            positions_json=args.positions_json,
            price_json=args.price_json,
            as_of=args.as_of,
            portfolio_value=args.portfolio_value,
            lot_size=args.lot_size,
            limit_buffer=args.limit_buffer,
            max_order_value=args.max_order_value,
            max_total_buy_value=args.max_total_buy_value,
            allow_short=args.allow_short,
            submit=args.submit,
            api_base_url=args.api_base_url,
            agent_token=args.agent_token,
            timeout=args.timeout,
            fail_on_warning=args.fail_on_warning,
            fail_on_blocked=args.fail_on_blocked,
            max_submit_candidates=args.max_submit_candidates,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    try:
        execution_report = maybe_build_execution_report(
            pipeline_report=report,
            verify_json=args.verify_json,
            portfolio_summary_json=args.portfolio_summary_json,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    _write_json(args.output_json, report)
    _write_json(args.preview_output_json, report["preview"])
    _write_json(args.submit_output_json, report["submit"])
    if execution_report:
        _write_json(args.execution_report_json, execution_report)
        if args.execution_report_md:
            _write_text(args.execution_report_md, render_markdown(execution_report))
    if report.get("guard_errors"):
        return 3
    if report["submit_summary"]["failed_submit_count"]:
        return 1
    return 0 if report["submit_summary"]["submit_candidate_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
