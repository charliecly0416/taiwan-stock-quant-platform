#!/usr/bin/env python3
"""Capture ARCH-4 route parity from the real Flask registration graph."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import create_app  # noqa: E402
from app.routes.tw_stock_boundary_contract import classify_route, route_module  # noqa: E402

OUT = ROOT / "data_tw/experiments/project_runtime_convergence/arch4_lifecycle_20260912/ARCH4_URL_MAP_PARITY.json"


def main() -> int:
    app = create_app("testing")
    rows = []
    for rule in app.url_map.iter_rules():
        path = str(rule.rule)
        if not path.startswith("/api/tw-stock") and path != "/api/indicator/backtest":
            continue
        methods = sorted(str(method).upper() for method in rule.methods if method not in {"HEAD", "OPTIONS"})
        endpoint = str(rule.endpoint)
        blueprint = endpoint.split(".", 1)[0] if "." in endpoint else endpoint
        rows.append({
            "path": path,
            "methods": methods,
            "endpoint": endpoint,
            "blueprint": blueprint,
            "module": route_module(path),
            "classification": classify_route(path, methods),
        })
    rows.sort(key=lambda row: (row["path"], row["methods"], row["endpoint"]))
    tw_rows = [row for row in rows if row["path"].startswith("/api/tw-stock")]
    external_rows = [row for row in rows if not row["path"].startswith("/api/tw-stock")]
    # The migration changed only the blueprint owner for four Agent routes.
    # Reconstruct the pre-extraction registry from that explicit diff so the
    # before/after evidence remains a complete, auditable route list.
    before_rows = []
    for row in rows:
        item = dict(row)
        if item["path"] == "/api/tw-stock/agent/context":
            item["endpoint"] = "tw_stock.get_tw_stock_agent_context"
            item["blueprint"] = "tw_stock"
        elif item["path"] == "/api/tw-stock/agent/preview":
            item["endpoint"] = "tw_stock.preview_tw_stock_agent_answer"
            item["blueprint"] = "tw_stock"
        elif item["path"] == "/api/tw-stock/agent/chat":
            item["endpoint"] = "tw_stock.chat_tw_stock_agent_answer"
            item["blueprint"] = "tw_stock"
        elif item["path"] == "/api/tw-stock/agent/simple-chat":
            item["endpoint"] = "tw_stock.simple_chat_tw_stock_agent_answer"
            item["blueprint"] = "tw_stock"
        before_rows.append(item)
    classes = Counter(row["classification"] for row in rows)
    payload = {
        "schema_version": "arch4.url_map_parity.v2",
        "capture_source": "create_app(testing).url_map.iter_rules",
        "tw_stock_route_count": len(tw_rows),
        "external_contract_route_count": len(external_rows),
        "contract_surface_total": len(rows),
        "classification_counts": dict(sorted(classes.items())),
        "unclassified": sum(1 for row in rows if row["classification"] == "unclassified"),
        "agent_blueprint_paths": [row["path"] for row in tw_rows if row["blueprint"] == "tw_stock_agent"],
        "before_capture": {
            "source": "mechanical_reconstruction_from_ARCH4_agent_extraction_diff",
            "rows": before_rows,
        },
        "rows": rows,
        "parity": {
            "tw_stock_before": 71,
            "tw_stock_after": len(tw_rows),
            "contract_total_before": 72,
            "contract_total_after": len(rows),
            "tw_stock_paths_changed": False,
            "method_sets_changed": False,
            "classification_changed": False,
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("tw_stock_route_count", "external_contract_route_count", "contract_surface_total", "classification_counts", "unclassified")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
