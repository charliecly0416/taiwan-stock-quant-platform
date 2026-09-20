#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tw_stock_workflow.task_dispatcher import (
    TaskDispatcher,
    TaskRequestError,
    load_task_request,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate or execute a registered Taiwan stock task"
    )
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate and print the plan without executing the task.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        request_path = (
            args.request.resolve()
            if args.request.is_absolute()
            else (ROOT / args.request).resolve()
        )
        dispatcher = TaskDispatcher(
            ROOT,
        )
        request = load_task_request(request_path)
        result = (
            {**dispatcher.plan(request).to_dict(), "status": "VALIDATED"}
            if args.validate_only
            else dispatcher.dispatch(request)
        )
    except TaskRequestError as exc:
        result = {
            "schema_version": "tw.task.error.v1",
            "ok": False,
            "status": "REJECTED",
            "error": str(exc),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"VALIDATED", "SUCCEEDED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
