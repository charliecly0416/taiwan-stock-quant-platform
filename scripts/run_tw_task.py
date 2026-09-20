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
        description="Validate, execute, or inspect a registered Taiwan stock task"
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--request",
        type=Path,
        help="Task request YAML/JSON to validate or execute.",
    )
    action.add_argument(
        "--status",
        nargs="?",
        const="all",
        metavar="TASK_TYPE",
        help="Show recent task runs; omit TASK_TYPE to show all registered tasks.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum status records to print (1-100).",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate and print the plan without executing the task.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        dispatcher = TaskDispatcher(
            ROOT,
        )
        if args.status is not None:
            if args.validate_only:
                raise TaskRequestError("--validate-only requires --request")
            result = dispatcher.recent_status(
                None if args.status == "all" else args.status,
                limit=args.limit,
            )
        else:
            request_path = (
                args.request.resolve()
                if args.request.is_absolute()
                else (ROOT / args.request).resolve()
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
    successful = result.get("status") in {"VALIDATED", "SUCCEEDED"}
    successful = successful or result.get("schema_version") == "tw.task.status.v1"
    return 0 if successful else 2


if __name__ == "__main__":
    raise SystemExit(main())
