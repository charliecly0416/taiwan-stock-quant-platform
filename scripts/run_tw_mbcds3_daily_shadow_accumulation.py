#!/usr/bin/env python3
"""Invoke the MBCDS3 accumulator for one isolated daily run.

This adapter is intentionally not imported by the production daily runner.
It accepts an explicit same-run inventory, appends only a new as-of date, and
records the invocation outcome under the isolated MBCDS3 evidence root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCUMULATOR = ROOT / "scripts/build_tw_mbcds3_shadow_accumulator.py"
ISOLATED_ROOT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow"


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rebuild_manifest(out: Path) -> None:
    files = {}
    for path in sorted(out.iterdir()):
        if path.name == "checksum_manifest.json" or not path.is_file():
            continue
        files[rel(path)] = sha256(path)
    (out / "checksum_manifest.json").write_text(
        json.dumps({"schema_version": "mbcds3.daily_adapter.checksum.v1", "files": files}, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one isolated MBCDS3 daily shadow accumulation append")
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--target-asof", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-inventory", type=Path)
    parser.add_argument("--missing-investigation", type=Path)
    args = parser.parse_args()

    inventory = args.inventory if args.inventory.is_absolute() else ROOT / args.inventory
    out = args.out if args.out.is_absolute() else ROOT / args.out
    if not out.resolve().is_relative_to(ISOLATED_ROOT):
        raise SystemExit(f"output must remain under isolated root: {ISOLATED_ROOT}")
    accumulator = out / "accumulator.csv"
    if not accumulator.is_file():
        raise SystemExit("MBCDS3 accumulator is absent; bootstrap it in an isolated run before daily append")
    if not inventory.is_file():
        raise SystemExit(f"inventory not found: {inventory}")

    command = [
        sys.executable, str(ACCUMULATOR), "--append",
        "--target-asof", args.target_asof,
        "--inventory", str(inventory),
        "--out", str(out),
    ]
    if args.source_inventory:
        command.extend(["--source-inventory", str(args.source_inventory)])
    if args.missing_investigation:
        command.extend(["--missing-investigation", str(args.missing_investigation)])
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    audit = {
        "schema_version": "mbcds3.daily_shadow_adapter_audit.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "isolated_daily_append",
        "target_asof": args.target_asof,
        "inventory": rel(inventory),
        "accumulator": rel(accumulator),
        "command": [str(item) for item in command],
        "exit_code": result.returncode,
        "status": "APPEND_ACCEPTED" if result.returncode == 0 else "APPEND_REJECTED_OR_BLOCKED",
        "stdout": result.stdout,
        "stderr": result.stderr,
        "production_wiring": False,
        "cron_modified": False,
        "latest_modified": False,
        "model_b_scoring": False,
        "training": False,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    audit_path = out / f"daily_adapter_audit_{args.target_asof}_{stamp}.json"
    audit["audit_path"] = rel(audit_path)
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    rebuild_manifest(out)
    print(json.dumps({"status": audit["status"], "target_asof": args.target_asof, "output": rel(out)}))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
