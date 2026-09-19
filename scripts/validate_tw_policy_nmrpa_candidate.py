#!/usr/bin/env python3
"""Readonly validator for an isolated synthetic NMRPA candidate package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tw_policy_nmrpa2 import ContractError, validate_candidate_root, validate_output_root


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--expected-input-sha256", required=True)
    parser.add_argument("--expected-chain-anchor", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        root = validate_output_root(args.candidate_root)
        result = validate_candidate_root(
            root,
            expected_input_sha256=args.expected_input_sha256,
            expected_chain_anchor=args.expected_chain_anchor,
        )
    except (ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"ok": False, "code": getattr(exc, "code", "NMRPA_E_VALIDATE"), "detail": str(exc)}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
