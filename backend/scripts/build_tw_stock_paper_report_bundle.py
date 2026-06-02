#!/usr/bin/env python3
"""Build a post-submit TWStock paper report bundle.

This script is intentionally post-submit only. It does not create orders,
connect to brokers, or mutate positions. It reads a pipeline/submit artifact,
verifies submitted paper orders through the Agent API, fetches the derived
paper portfolio summary, and assembles the existing execution report.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.build_tw_stock_paper_execution_report import build_report as build_execution_report
from scripts.build_tw_stock_paper_execution_report import render_markdown
from scripts.verify_tw_stock_paper_orders import build_report as build_verify_report
from scripts.verify_tw_stock_paper_orders import extract_order_uids, fetch_paper_orders, load_json


def fetch_paper_summary(*, api_base_url: str, agent_token: str, initial_cash: float, timeout: int = 20) -> Dict[str, Any]:
    base = api_base_url.rstrip("/")
    url = f"{base}/api/agent/v1/portfolio/paper-summary"
    headers = {"Authorization": f"Bearer {agent_token}", "Content-Type": "application/json"}
    response = requests.get(url, headers=headers, params={"initial_cash": initial_cash}, timeout=timeout)
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text}
    return {
        "url": url,
        "status_code": response.status_code,
        "ok": 200 <= response.status_code < 300,
        "response": body,
        "data": body.get("data") if isinstance(body, dict) else None,
    }


def build_bundle(
    *,
    pipeline_report: Dict[str, Any],
    fetched_orders: Dict[str, Any],
    fetched_summary: Dict[str, Any],
) -> Dict[str, Any]:
    expected = extract_order_uids(pipeline_report)
    verification = build_verify_report(expected_order_uids=expected, fetched=fetched_orders)
    summary_payload = fetched_summary.get("response") if isinstance(fetched_summary.get("response"), dict) else fetched_summary
    execution_report = build_execution_report(
        pipeline=pipeline_report,
        verification=verification,
        portfolio_summary=summary_payload,
    )
    status = execution_report.get("status")
    status_reasons = list(execution_report.get("status_reasons") or [])
    if not expected:
        status = "fail"
        status_reasons.append("no_successful_order_uid")
    if not fetched_orders.get("ok"):
        status = "fail"
        status_reasons.append("paper_orders_fetch_failed")
    if not fetched_summary.get("ok"):
        status = "fail"
        status_reasons.append("paper_summary_fetch_failed")
    execution_report["status"] = status
    execution_report["status_reasons"] = status_reasons
    return {
        "market": "TWStock",
        "paper_only": True,
        "post_submit_only": True,
        "status": status,
        "status_reasons": status_reasons,
        "verification": verification,
        "portfolio_summary_response": summary_payload,
        "execution_report": execution_report,
    }


def _write_json(path: str, payload: Dict[str, Any]) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: str, text: str) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build TWStock post-submit paper verification and execution report bundle.")
    parser.add_argument("--pipeline-json", required=True, help="JSON from run_tw_stock_paper_pipeline.py or submit_tw_stock_paper_orders.py.")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--agent-token", required=True)
    parser.add_argument("--initial-cash", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--output-json", default="", help="Full bundle JSON output path.")
    parser.add_argument("--verify-output-json", default="", help="Verification-only JSON output path.")
    parser.add_argument("--summary-output-json", default="", help="Paper summary API response JSON output path.")
    parser.add_argument("--execution-report-json", default="", help="Execution report JSON output path.")
    parser.add_argument("--execution-report-md", default="", help="Execution report Markdown output path.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    pipeline_report = load_json(args.pipeline_json)
    expected = extract_order_uids(pipeline_report)
    if not expected:
        fetched_orders = {"ok": True, "status_code": None, "orders": []}
    else:
        fetched_orders = fetch_paper_orders(api_base_url=args.api_base_url, agent_token=args.agent_token, timeout=args.timeout)
    fetched_summary = fetch_paper_summary(
        api_base_url=args.api_base_url,
        agent_token=args.agent_token,
        initial_cash=args.initial_cash,
        timeout=args.timeout,
    )
    bundle = build_bundle(
        pipeline_report=pipeline_report,
        fetched_orders=fetched_orders,
        fetched_summary=fetched_summary,
    )
    text = json.dumps(bundle, ensure_ascii=False, indent=2)
    print(text)
    _write_json(args.output_json, bundle)
    _write_json(args.verify_output_json, bundle["verification"])
    _write_json(args.summary_output_json, fetched_summary.get("response") if isinstance(fetched_summary.get("response"), dict) else fetched_summary)
    _write_json(args.execution_report_json, bundle["execution_report"])
    if args.execution_report_md:
        _write_text(args.execution_report_md, render_markdown(bundle["execution_report"]))
    return 0 if bundle.get("status") in ("pass", "warning") else 1


if __name__ == "__main__":
    raise SystemExit(main())
