#!/usr/bin/env python3
"""Dry-run or submit TWStock paper order previews to the Agent Gateway.

Default mode is dry-run: no HTTP call, no DB write, no broker access. Use
--submit with --api-base-url and --agent-token to POST paper orders to the
existing /api/agent/v1/quick-trade/orders endpoint.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import requests


def load_preview(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_quick_trade_payloads(preview: Dict[str, Any]) -> List[Dict[str, Any]]:
    payloads: List[Dict[str, Any]] = []
    for item in preview.get("orders") or []:
        if not isinstance(item, dict):
            continue
        if item.get("status") != "preview":
            continue
        payload = {
            "market": "TWStock",
            "symbol": str(item.get("symbol") or "").strip(),
            "side": str(item.get("side") or "").strip().lower(),
            "qty": int(float(item.get("qty") or 0)),
            "order_type": "limit",
            "limit_price": float(item.get("limit_price") or 0.0),
            "lot_size": int((preview.get("assumptions") or {}).get("lot_size") or 1000),
            "source": "tw_stock_paper_order_preview",
        }
        if payload["side"] == "sell":
            payload["current_qty"] = int(float(item.get("current_qty") or item.get("currentQty") or item.get("qty") or 0))
        payloads.append(payload)
    return payloads


def submit_payloads(*, payloads: Sequence[Dict[str, Any]], api_base_url: str, agent_token: str, timeout: int = 20) -> List[Dict[str, Any]]:
    base = api_base_url.rstrip("/")
    url = f"{base}/api/agent/v1/quick-trade/orders"
    headers = {"Authorization": f"Bearer {agent_token}", "Content-Type": "application/json"}
    results: List[Dict[str, Any]] = []
    for payload in payloads:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}
        results.append({
            "status_code": response.status_code,
            "ok": 200 <= response.status_code < 300,
            "payload": payload,
            "response": body,
        })
    return results


def build_report(*, preview: Dict[str, Any], payloads: Sequence[Dict[str, Any]], submit_results: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    submit_results = submit_results or []
    return {
        "market": "TWStock",
        "paper_only": True,
        "dry_run": not bool(submit_results),
        "input_order_count": len(preview.get("orders") or []),
        "submit_candidate_count": len(payloads),
        "skipped_count": len(preview.get("orders") or []) - len(payloads),
        "warnings": list(preview.get("warnings") or []),
        "payloads": list(payloads),
        "submit_results": submit_results,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run or submit TWStock paper order previews to Agent quick-trade.")
    parser.add_argument("--preview-json", required=True, help="JSON from preview_tw_stock_paper_orders.py.")
    parser.add_argument("--output-json", default="")
    parser.add_argument("--submit", action="store_true", help="Actually POST to the Agent Gateway paper quick-trade endpoint.")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--agent-token", default="")
    parser.add_argument("--timeout", type=int, default=20)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    preview = load_preview(args.preview_json)
    payloads = build_quick_trade_payloads(preview)
    results: List[Dict[str, Any]] = []
    if args.submit:
        if not args.agent_token:
            print(json.dumps({"error": "--agent-token is required with --submit"}, ensure_ascii=False, indent=2))
            return 2
        results = submit_payloads(payloads=payloads, api_base_url=args.api_base_url, agent_token=args.agent_token, timeout=args.timeout)
    report = build_report(preview=preview, payloads=payloads, submit_results=results)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.output_json:
        path = Path(args.output_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    if args.submit and any(not item.get("ok") for item in results):
        return 1
    return 0 if payloads else 2


if __name__ == "__main__":
    raise SystemExit(main())
