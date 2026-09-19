#!/usr/bin/env python3
"""Validate a frozen B19R2R V4 logical composite source-run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_modelb_b19r2r_v4_composite_source_run_20260916 as builder


class ValidationError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def check(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise ValidationError(code, detail)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("B19V4IV_E_JSON", str(path)) from exc
    check(isinstance(value, dict), "B19V4IV_E_JSON", str(path))
    return value


def validate(output: Path) -> dict[str, Any]:
    output = output.resolve()
    check(output.parent == builder.OUT_ROOT.resolve(), "B19V4IV_E_OUTPUT", str(output))
    inventory_path = output / "CHILD_INVENTORY.json"
    manifest_path = output / "COMPOSITE_SOURCE_RUN_MANIFEST.json"
    calendar_path = output / "EXTENDED_CLEAN_CALENDAR.txt"
    check(inventory_path.is_file() and manifest_path.is_file() and calendar_path.is_file(), "B19V4IV_E_REQUIRED_FILE")
    inventory = read_json(inventory_path)
    manifest = read_json(manifest_path)

    roles = list(builder.REQUIRED_ROLES)
    children = inventory.get("children")
    check(isinstance(children, list), "B19V4IV_E_CHILDREN")
    child_roles = [str(item.get("role") or "") for item in children]
    check(child_roles == roles and len(set(child_roles)) == len(roles), "B19V4IV_E_CHILD_ROLES", repr(child_roles))
    check(
        inventory.get("schema_version") == "modelb_b19r2r.logical_child_inventory.v2"
        and inventory.get("asof") == builder.ASOF
        and inventory.get("required_child_roles") == roles
        and inventory.get("child_count") == len(roles)
        and inventory.get("future_or_outcome_fields") == [],
        "B19V4IV_E_INVENTORY_CONTRACT",
    )
    expected_children = [
        builder.finmind_child("daily_price", builder.PRICE_ADAPTER),
        builder.finmind_child("institutional", builder.INSTITUTIONAL_ADAPTER),
        builder.finmind_child("margin", builder.MARGIN_ADAPTER),
        builder.model_a_child(),
        builder.yahoo_child(),
    ]
    check(children == expected_children, "B19V4IV_E_CHILD_LINEAGE")
    expected_calendar, expected_calendar_lineage = builder.extended_calendar()
    actual_calendar = [line.strip() for line in calendar_path.read_text(encoding="ascii").splitlines() if line.strip()]
    check(actual_calendar == expected_calendar, "B19V4IV_E_CALENDAR_CONTENT")
    expected_calendar_binding = {
        **expected_calendar_lineage,
        "extended_calendar": builder.artifact(calendar_path),
        "extension_semantics": "append_only_exact_target_date_after_reviewed_clean_calendar",
    }
    check(
        inventory.get("calendar_binding") == expected_calendar_binding
        and manifest.get("calendar_binding") == expected_calendar_binding,
        "B19V4IV_E_CALENDAR_BINDING",
    )

    inventory_sha = builder.sha256(inventory_path)
    logical_id = f"research.logical_composite.{builder.ASOF.replace('-', '')}.{inventory_sha[:20]}"
    physical_ids = builder.physical_run_ids(children)
    available = [builder.parse_time(item.get("available_at")) for item in children]
    max_available = max(available).isoformat(timespec="microseconds")
    cutoff = builder.parse_time(manifest.get("decision_cutoff"))
    check(all(value <= cutoff for value in available), "B19V4IV_E_AVAILABLE_AFTER_CUTOFF")
    check(cutoff < builder.parse_time(builder.NEXT_OPEN), "B19V4IV_E_CUTOFF_AFTER_NEXT_OPEN")
    check(
        inventory.get("max_child_available_at") == max_available
        and manifest.get("max_child_available_at") == max_available,
        "B19V4IV_E_MAX_AVAILABLE_AT",
    )
    check(
        manifest.get("schema_version") == "modelb_b19r2r.logical_composite_source_run.v2"
        and manifest.get("source_run_kind") == "logical_composite"
        and manifest.get("logical_source_run_id") == logical_id
        and logical_id not in physical_ids
        and manifest.get("asof") == builder.ASOF
        and manifest.get("next_session_open_at") == builder.NEXT_OPEN
        and manifest.get("required_child_roles") == roles
        and manifest.get("physical_run_ids") == physical_ids,
        "B19V4IV_E_MANIFEST_BINDING",
    )
    declared_inventory = manifest.get("child_inventory", {})
    check(
        declared_inventory.get("path") == builder.rel(inventory_path)
        and declared_inventory.get("sha256") == inventory_sha
        and declared_inventory.get("bytes") == inventory_path.stat().st_size
        and manifest.get("child_inventory_sha256") == inventory_sha,
        "B19V4IV_E_INVENTORY_HASH",
    )
    check(
        builder.parse_time(manifest.get("created_at")) == builder.parse_time(manifest.get("frozen_at"))
        and builder.parse_time(manifest.get("frozen_at")) < builder.parse_time(builder.NEXT_OPEN),
        "B19V4IV_E_FREEZE_TIME",
    )
    check(
        manifest.get("pit_status") == "PASS"
        and manifest.get("validator_status") == "PENDING_INDEPENDENT_REVIEW"
        and manifest.get("capture_authorized") is False
        and manifest.get("accepted_ledger_event_written") is False
        and manifest.get("no_publish") is True
        and manifest.get("no_latest_write") is True
        and manifest.get("production_allowed") is False,
        "B19V4IV_E_BOUNDARY",
    )
    check(
        manifest.get("protected_before") == manifest.get("protected_after") == builder.fingerprints()
        and manifest.get("protected_unchanged") is True,
        "B19V4IV_E_PROTECTED_DRIFT",
    )
    return {
        "schema_version": "modelb_b19r2r.logical_composite_validation.v2",
        "status": "PASS",
        "logical_source_run_id": logical_id,
        "child_inventory_sha256": inventory_sha,
        "child_count": len(children),
        "max_child_available_at": max_available,
        "decision_cutoff": manifest["decision_cutoff"],
        "capture_authorized": False,
        "accepted_ledger_event_written": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=builder.OUT_ROOT / "logical_composite_v2")
    args = parser.parse_args()
    try:
        result = validate(args.output)
    except (ValidationError, builder.InventoryError) as exc:
        print(json.dumps({"status": "FAIL", "error_code": exc.code, "detail": exc.detail}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
