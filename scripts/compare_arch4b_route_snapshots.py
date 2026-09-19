#!/usr/bin/env python3
"""Compare ARCH-4B before/after snapshots route-by-route."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--group", required=True)
    args = parser.parse_args()
    before = json.loads((ROOT / args.before).read_text(encoding="utf-8"))
    after = json.loads((ROOT / args.after).read_text(encoding="utf-8"))
    before_keyed = {(row["path"], tuple(row["methods"])): row for row in before["rows"]}
    after_keyed = {(row["path"], tuple(row["methods"])): row for row in after["rows"]}
    path_method_drift = sorted(set(before_keyed) ^ set(after_keyed))
    endpoint_changes = [
        {"path": key[0], "methods": list(key[1]), "before": before_keyed[key]["endpoint"], "after": after_keyed[key]["endpoint"]}
        for key in sorted(set(before_keyed) & set(after_keyed))
        if before_keyed[key]["endpoint"] != after_keyed[key]["endpoint"]
    ]
    classification_changes = [
        {"path": key[0], "methods": list(key[1]), "before": before_keyed[key]["classification"], "after": after_keyed[key]["classification"]}
        for key in sorted(set(before_keyed) & set(after_keyed))
        if before_keyed[key]["classification"] != after_keyed[key]["classification"]
    ]
    payload = {
        "schema_version": "arch4b.route_parity.v1",
        "group": args.group,
        "before_snapshot": args.before,
        "after_snapshot": args.after,
        "before": {"tw_stock_route_count": before["tw_stock_route_count"], "contract_surface_total": before["contract_surface_total"]},
        "after": {"tw_stock_route_count": after["tw_stock_route_count"], "contract_surface_total": after["contract_surface_total"]},
        "path_method_drift": path_method_drift,
        "endpoint_changes": endpoint_changes,
        "classification_changes": classification_changes,
        "ok": not path_method_drift and not classification_changes,
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"group": args.group, "ok": payload["ok"], "path_method_drift": len(path_method_drift), "endpoint_changes": len(endpoint_changes), "classification_changes": len(classification_changes)}))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
