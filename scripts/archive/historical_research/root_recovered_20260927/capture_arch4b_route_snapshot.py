#!/usr/bin/env python3
"""Capture a reproducible Flask URL-map snapshot for ARCH-4B group moves."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = Path(os.environ.get("ARCH4_APP_ROOT", str(ROOT))).resolve()
sys.path.insert(0, str(APP_ROOT / "backend"))
if APP_ROOT != ROOT:
    sys.path.append(str(ROOT / "backend"))

from app import create_app  # noqa: E402
try:
    from app.routes.tw_stock_boundary_contract import classify_route, route_module  # noqa: E402
except ModuleNotFoundError:
    import importlib.util
    _spec = importlib.util.spec_from_file_location("arch4_boundary_contract", ROOT / "backend/app/routes/tw_stock_boundary_contract.py")
    _boundary = importlib.util.module_from_spec(_spec)
    assert _spec and _spec.loader
    _spec.loader.exec_module(_boundary)
    classify_route, route_module = _boundary.classify_route, _boundary.route_module


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def snapshot(label: str, source_files: list[str]) -> dict:
    app = create_app("testing")
    rows = []
    for rule in app.url_map.iter_rules():
        path = str(rule.rule)
        if not path.startswith("/api/tw-stock") and path != "/api/indicator/backtest":
            continue
        methods = sorted(str(method).upper() for method in rule.methods if method not in {"HEAD", "OPTIONS"})
        endpoint = str(rule.endpoint)
        rows.append({
            "path": path,
            "methods": methods,
            "endpoint": endpoint,
            "blueprint": endpoint.split(".", 1)[0] if "." in endpoint else endpoint,
            "module": route_module(path),
            "classification": classify_route(path, methods),
        })
    rows.sort(key=lambda row: (row["path"], row["methods"], row["endpoint"]))
    return {
        "schema_version": "arch4b.route_snapshot.v1",
        "capture_label": label,
        "capture_source": "create_app(testing).url_map.iter_rules",
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=APP_ROOT, text=True, capture_output=True, check=False).stdout.strip(),
        "source_files": [{"path": item, "sha256": file_hash(APP_ROOT / item)} for item in source_files],
        "rows": rows,
        "tw_stock_route_count": sum(row["path"].startswith("/api/tw-stock") for row in rows),
        "contract_surface_total": len(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("source_files", nargs="+")
    args = parser.parse_args()
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot(args.label, args.source_files), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
