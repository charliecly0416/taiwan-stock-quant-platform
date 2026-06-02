#!/usr/bin/env python3
"""Verify submitted TWStock paper orders can be read back from Agent Gateway.

This script is post-submit verification only. It does not create orders, update
positions, connect to IBKR, or place broker orders. It reads order_uid values
from a submit report or pipeline report and checks /api/agent/v1/portfolio/paper-orders.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

import requests


def load_json(path: str) -> Dict[str, Any]:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _response_data(result: Dict[str, Any]) -> Dict[str, Any]:
    response = result.get("response") if isinstance(result, dict) else {}
    if not isinstance(response, dict):
        return {}
    data = response.get("data")
    return data if isinstance(data, dict) else {}


def extract_order_uids(report: Dict[str, Any]) -> List[str]:
    submit = report.get("submit") if isinstance(report.get("submit"), dict) else report
    results = submit.get("submit_results") if isinstance(submit, dict) else []
    uids: List[str] = []
    seen: Set[str] = set()
    for item in results or []:
        if not isinstance(item, dict) or not item.get("ok"):
            continue
        data = _response_data(item)
        uid = str(data.get("order_uid") or "").strip()
        if uid and uid not in seen:
            seen.add(uid)
            uids.append(uid)
    return uids


def fetch_paper_orders(*, api_base_url: str, agent_token: str, timeout: int = 20) -> Dict[str, Any]:
    base = api_base_url.rstrip("/")
    url = f"{base}/api/agent/v1/portfolio/paper-orders"
    headers = {"Authorization": f"Bearer {agent_token}", "Content-Type": "application/json"}
    response = requests.get(url, headers=headers, timeout=timeout)
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text}
    data = body.get("data") if isinstance(body, dict) else None
    orders = data if isinstance(data, list) else []
    return {
        "url": url,
        "status_code": response.status_code,
        "ok": 200 <= response.status_code < 300,
        "response": body,
        "orders": orders,
    }


def build_report(*, expected_order_uids: Sequence[str], fetched: Dict[str, Any]) -> Dict[str, Any]:
    expected = [str(uid) for uid in expected_order_uids if str(uid).strip()]
    observed_orders = fetched.get("orders") or []
    observed_uids = {
        str(item.get("order_uid") or "").strip()
        for item in observed_orders
        if isinstance(item, dict) and item.get("order_uid")
    }
    matched = [uid for uid in expected if uid in observed_uids]
    missing = [uid for uid in expected if uid not in observed_uids]
    matched_orders = [item for item in observed_orders if isinstance(item, dict) and str(item.get("order_uid") or "").strip() in set(matched)]
    return {
        "market": "TWStock",
        "paper_only": True,
        "expected_order_uids": expected,
        "expected_count": len(expected),
        "fetched_ok": bool(fetched.get("ok")),
        "fetch_status_code": fetched.get("status_code"),
        "fetched_order_count": len(observed_orders),
        "matched_order_uids": matched,
        "matched_count": len(matched),
        "missing_order_uids": missing,
        "missing_count": len(missing),
        "matched_orders": matched_orders,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify TWStock paper orders after Agent quick-trade submit.")
    parser.add_argument("--submit-report-json", required=True, help="JSON from submit_tw_stock_paper_orders.py or run_tw_stock_paper_pipeline.py.")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--agent-token", required=True)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--output-json", default="")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    report_in = load_json(args.submit_report_json)
    expected = extract_order_uids(report_in)
    if not expected:
        result = {
            "market": "TWStock",
            "paper_only": True,
            "error": "no successful order_uid found in submit report",
            "expected_order_uids": [],
        }
        text = json.dumps(result, ensure_ascii=False, indent=2)
        print(text)
        if args.output_json:
            Path(args.output_json).write_text(text + "\n", encoding="utf-8")
        return 2
    fetched = fetch_paper_orders(api_base_url=args.api_base_url, agent_token=args.agent_token, timeout=args.timeout)
    result = build_report(expected_order_uids=expected, fetched=fetched)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.output_json:
        path = Path(args.output_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    if not result["fetched_ok"] or result["missing_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
