#!/usr/bin/env python3
"""Validate the prospective V3 affordability template without real artifact access."""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "scripts/modelb_b19r2r_prospective_confirmation_v3_template.py"
FORBIDDEN_SOURCE_TOKENS = (
    "CONFIRMATION_OUTCOMES.parquet",
    "CONFIRMATION_EXECUTION_GRID.parquet",
    "sealed_confirmation",
    "confirmation_output_v2",
    "B19R2R_CONFIRMATION_EXECUTION_AUTHORIZATION_V2",
)
WRITE_METHODS = {"write_text", "write_bytes", "to_csv", "to_parquet", "mkdir", "unlink", "replace", "rename"}


def load_template() -> Any:
    spec = importlib.util.spec_from_file_location("modelb_v3_template", TEMPLATE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load V3 template")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_static() -> dict[str, bool]:
    source = TEMPLATE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    write_calls = []
    file_read_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = ast.unparse(node.func)
        attr = name.rsplit(".", 1)[-1]
        if attr in WRITE_METHODS:
            write_calls.append(name)
        if attr in {"read_parquet", "read_csv", "read_bytes", "read_text", "open", "stat", "exists", "is_file"}:
            file_read_calls.append(name)
    return {
        "no_prior_confirmation_or_sealed_source_tokens": not any(
            token in source for token in FORBIDDEN_SOURCE_TOKENS
        ),
        "no_filesystem_write_calls": not write_calls,
        "no_artifact_file_read_calls": not file_read_calls,
        "no_real_execution_cli": "--execute" not in source and "--validate-output" not in source,
        "skip_status_present": "SKIPPED_ZERO_OR_INSUFFICIENT_CASH" in source,
        "missing_price_still_fails_without_fallback": "missing next_open; no fallback" in source,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-template", action="store_true")
    args = parser.parse_args()
    if not args.validate_template:
        raise SystemExit("Select --validate-template")
    static = validate_static()
    synthetic = load_template().run_synthetic_affordability_check()
    checks = {**static, "synthetic_high_price_fixture_pass": synthetic["status"] == "PASS"}
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "template_only": True,
        "sealed_or_confirmation_artifact_accessed": False,
        "checks": checks,
        "synthetic": synthetic,
    }
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
