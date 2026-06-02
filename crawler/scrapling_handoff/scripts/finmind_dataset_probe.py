#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from scrapling.fetchers import Fetcher

FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe a FinMind dataset and save a raw sample without exposing tokens.")
    parser.add_argument("--dataset", required=True, help="FinMind dataset name, e.g. TaiwanStockPrice")
    parser.add_argument("--data-id", default=None, help="Source data_id, e.g. 2330. Omit for datasets that do not require it.")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2024-01-31")
    parser.add_argument("--output", default="finmind_probe_report.json")
    parser.add_argument("--proxy", default="http://127.0.0.1:7890")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--limit", type=int, default=5, help="Number of raw rows to include in the report sample.")
    return parser.parse_args()


def fetch(args: argparse.Namespace) -> tuple[int | None, dict[str, Any] | None, str | None]:
    params: dict[str, str] = {
        "dataset": args.dataset,
        "start_date": args.start,
        "end_date": args.end,
    }
    if args.data_id:
        params["data_id"] = args.data_id
    token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
    if token:
        params["token"] = token.strip()
    kwargs: dict[str, Any] = {"proxy": args.proxy} if args.proxy else {}
    try:
        page = Fetcher.get(
            FINMIND_URL,
            params=params,
            timeout=args.timeout,
            retries=1,
            impersonate="chrome",
            **kwargs,
        )
        payload = page.json()
        return page.status, payload, None
    except Exception as exc:
        return None, None, f"{type(exc).__name__}:{exc}"


def main() -> int:
    args = parse_args()
    status, payload, error = fetch(args)
    data = payload.get("data") if isinstance(payload, dict) else None
    rows = data if isinstance(data, list) else []
    sample = rows[: max(args.limit, 0)]
    fields = sorted({key for row in sample if isinstance(row, dict) for key in row.keys()})
    report = {
        "source": "FinMind",
        "dataset": args.dataset,
        "data_id": args.data_id,
        "start": args.start,
        "end": args.end,
        "http_status": status,
        "finmind_status": payload.get("status") if isinstance(payload, dict) else None,
        "msg": payload.get("msg") if isinstance(payload, dict) else error,
        "row_count": len(rows),
        "sample_fields": fields,
        "sample_rows": sample,
        "token_used": bool(os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["dataset", "data_id", "http_status", "finmind_status", "row_count", "sample_fields", "token_used"]}, ensure_ascii=False, indent=2))
    print(f"wrote {out}")
    return 0 if error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
