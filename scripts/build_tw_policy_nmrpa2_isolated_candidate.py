#!/usr/bin/env python3
"""Build an isolated, synthetic-only NMRPA2 candidate package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tw_policy_nmrpa2 import ContractError, build


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-input-sha256", required=True)
    parser.add_argument("--chain-anchor", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = build(
            args.fixture,
            args.output_root,
            expected_input_sha256=args.expected_input_sha256,
            chain_anchor_path=args.chain_anchor,
        )
    except (ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"ok": False, "code": getattr(exc, "code", "NMRPA_E_BUILD"), "detail": str(exc)}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
