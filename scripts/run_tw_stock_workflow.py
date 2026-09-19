#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tw_stock_workflow.service import run_workflow
from tw_stock_workflow.types import ExecutionContext


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an explicitly registered Taiwan stock workflow"
    )
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--decision-cutoff", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument(
        "--mode", choices=("readonly", "replay", "dry-run"), default="readonly"
    )
    parser.add_argument("--permission", action="append", default=[])
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--history-index", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = ExecutionContext(
        mode=args.mode,
        asof=args.asof,
        decision_cutoff=args.decision_cutoff,
        workspace=args.workspace,
        permissions=frozenset(args.permission),
    )
    result = run_workflow(
        repo_root=args.repo_root,
        spec_path=args.spec,
        context=context,
        history_index=args.history_index,
    )
    print(
        json.dumps(
            {**result.record, "idempotent_reuse": result.idempotent_reuse},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.status == "SUCCEEDED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
