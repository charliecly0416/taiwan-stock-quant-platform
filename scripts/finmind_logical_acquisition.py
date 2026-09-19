"""Contract-only state for resumable FinMind logical acquisition runs.

This module does not fetch data or publish anything.  It records the identity
of one target acquisition and validates that segment evidence can be joined
without weakening the HSA8 same-run contract.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "finmind.logical_acquisition_state.v1"
REQUIRED_SEGMENTS = ("daily_price", "institutional", "margin", "twii")
OPTIONAL_SEGMENTS = ("corporate_actions", "monthly_revenue", "valuation")


def symbols_checksum(symbols: list[str]) -> str:
    canonical = "\n".join(sorted({str(symbol).strip() for symbol in symbols if str(symbol).strip()})) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def logical_run_id(*, target_asof: str, symbols_sha256: str) -> str:
    digest = hashlib.sha256(f"{target_asof}|{symbols_sha256}".encode("utf-8")).hexdigest()[:20]
    return f"finmind.logical.{target_asof.replace('-', '')}.{digest}"


def new_state(*, target_asof: str, symbols: list[str]) -> dict[str, Any]:
    checksum = symbols_checksum(symbols)
    return {
        "schema_version": SCHEMA_VERSION,
        "logical_run_id": logical_run_id(target_asof=target_asof, symbols_sha256=checksum),
        "target_asof": target_asof,
        "symbols_sha256": checksum,
        "required_segments": list(REQUIRED_SEGMENTS),
        "optional_segments": list(OPTIONAL_SEGMENTS),
        "segments": {},
        "status": "INCOMPLETE",
        "handoff_allowed": False,
    }


def record_segment(state: Mapping[str, Any], *, segment: str, job_id: str,
                   evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Return a new state after recording one segment's immutable evidence reference."""
    if segment not in (*REQUIRED_SEGMENTS, *OPTIONAL_SEGMENTS):
        raise ValueError(f"unknown segment: {segment}")
    result = dict(state)
    if result.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("logical acquisition state schema mismatch")
    if not job_id.strip():
        raise ValueError("segment job_id is required")
    item = dict(evidence)
    for key in ("target_asof", "logical_run_id", "symbols_sha256"):
        if key in item and item[key] not in (None, "") and item[key] != result.get(key):
            raise ValueError(f"segment {segment} {key} does not match logical run")
    item["segment"] = segment
    item["job_id"] = job_id
    item["target_asof"] = result.get("target_asof")
    item["logical_run_id"] = result.get("logical_run_id")
    item["symbols_sha256"] = result.get("symbols_sha256")
    result["segments"] = {**dict(result.get("segments") or {}), segment: item}
    result["status"], result["handoff_allowed"] = validate_state(result)
    return result


def validate_state(state: Mapping[str, Any]) -> tuple[str, bool]:
    """Return (status, handoff_allowed); never infer missing evidence as success."""
    if state.get("schema_version") != SCHEMA_VERSION:
        return "INVALID_SCHEMA", False
    logical_id = str(state.get("logical_run_id") or "")
    target_asof = str(state.get("target_asof") or "")
    symbols_sha = str(state.get("symbols_sha256") or "")
    if not logical_id or not target_asof or len(symbols_sha) != 64:
        return "INVALID_IDENTITY", False
    segments = state.get("segments")
    if not isinstance(segments, Mapping):
        return "INVALID_SEGMENTS", False
    for name, item in segments.items():
        if name not in (*REQUIRED_SEGMENTS, *OPTIONAL_SEGMENTS) or not isinstance(item, Mapping):
            return "INVALID_SEGMENT", False
        if item.get("logical_run_id") != logical_id or item.get("target_asof") != target_asof or item.get("symbols_sha256") != symbols_sha:
            return "IDENTITY_MISMATCH", False
        if not str(item.get("job_id") or "") or item.get("ok") is not True:
            return "INCOMPLETE", False
        if not str(item.get("evidence_path") or "") or not str(item.get("evidence_sha256") or ""):
            return "INCOMPLETE", False
    if any(name not in segments for name in REQUIRED_SEGMENTS):
        return "INCOMPLETE", False
    return "COMPLETE", True


def write_state(path: Path, state: Mapping[str, Any]) -> None:
    """Atomically persist only an ops state file."""
    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    data = (json.dumps(dict(state), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def load_state(path: Path, *, target_asof: str, symbols: list[str]) -> dict[str, Any]:
    """Load a compatible state, or create a fresh state for this scope."""
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state = {}
        fresh = new_state(target_asof=target_asof, symbols=symbols)
        if all(state.get(key) == fresh.get(key) for key in ("schema_version", "logical_run_id", "target_asof", "symbols_sha256")):
            return state
    return new_state(target_asof=target_asof, symbols=symbols)
