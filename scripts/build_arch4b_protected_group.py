#!/usr/bin/env python3
"""Create group-scoped protected-fingerprint evidence from ARCH-4 baseline."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data_tw/experiments/project_runtime_convergence/arch4_lifecycle_20260912/ARCH4_PROTECTED_BEFORE_AFTER.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    paths = sorted(baseline.get("after_sha256", {}))
    before = dict(baseline.get("after_sha256", {}))
    after = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
    payload = {
        "schema_version": "arch4b.protected_fingerprint_group.v1",
        "group": args.group,
        "capture_mode": "real_filesystem_sha256",
        "before_source": "ARCH4_PROTECTED_BEFORE_AFTER.json real filesystem baseline",
        "before_sha256": before,
        "after_sha256": after,
        "protected_paths_unchanged": before == after,
        "publish_allowed": False,
        "model_b_active": False,
        "broker_or_order": False,
        "training_scoring_fetch_publish": False,
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"group": args.group, "protected_paths": len(paths), "unchanged": payload["protected_paths_unchanged"]}))
    return 0 if payload["protected_paths_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
