#!/usr/bin/env python3
"""Materialize group-specific ARCH-4B before rows from the real ARCH-4 URL evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data_tw/experiments/project_runtime_convergence/arch4_lifecycle_20260912/ARCH4_URL_MAP_PARITY.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--input", default=str(BASELINE))
    parser.add_argument("--label", default=None)
    args = parser.parse_args()
    input_path = ROOT / args.input if not Path(args.input).is_absolute() else Path(args.input)
    evidence = json.loads(input_path.read_text(encoding="utf-8"))
    rows = evidence.get("before_capture", {}).get("rows") if "before_capture" in evidence else evidence["rows"]
    if args.group == "ops":
        keep = lambda row: row["path"].startswith("/api/tw-stock/quant/ops/") or row["path"].startswith("/api/tw-stock/monitor")
    elif args.group == "replay":
        keep = lambda row: row["path"] in {
            "/api/tw-stock/rank-tech-cross/observation-replay",
            "/api/tw-stock/rank-tech-cross/portfolio-replay",
        }
    elif args.group == "paper":
        keep = lambda row: row["path"].startswith("/api/tw-stock/sim/") or row["path"].startswith("/api/tw-stock/paper-portfolio/")
    elif args.group == "context":
        prefixes = (
            "/api/tw-stock/phase-yz/", "/api/tw-stock/current-strategy-context", "/api/tw-stock/readonly-shadow-exposure",
            "/api/tw-stock/tradingagents-readonly-analysis/", "/api/tw-stock/trend", "/api/tw-stock/trends",
            "/api/tw-stock/quant/signals/", "/api/tw-stock/cross-analysis/", "/api/tw-stock/rank-tech-cross/latest",
            "/api/tw-stock/ltr-readonly-explanation", "/api/tw-stock/ltr-optional-sim-strategies",
        )
        keep = lambda row: row["path"].startswith(prefixes)
    else:
        raise SystemExit(f"unsupported group: {args.group}")
    selected = [row for row in rows if keep(row)]
    payload = {
        "schema_version": "arch4b.route_snapshot.v1",
        "capture_label": args.label or f"{args.group}_before",
        "capture_source": f"{args.input} route rows (real create_app URL-map evidence)",
        "git_head": evidence.get("git_head", "unknown-at-ARCH4-baseline"),
        "source_files": [{"path": args.input, "sha256": "evidence-reference"}],
        "rows": sorted(selected, key=lambda row: (row["path"], row["methods"], row["endpoint"])),
        "tw_stock_route_count": sum(row["path"].startswith("/api/tw-stock") for row in selected),
        "contract_surface_total": len(selected),
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"group": args.group, "rows": len(selected), "output": args.output}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
