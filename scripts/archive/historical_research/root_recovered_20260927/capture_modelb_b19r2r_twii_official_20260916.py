#!/usr/bin/env python3
"""Capture official TWSE TWII for 2026-09-16 in a write-once research namespace."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_v3_manual_source_20260916"
ENDPOINT = "https://www.twse.com.tw/exchangeReport/MI_INDEX"
TARGET = "2026-09-16"
NEXT_OPEN_UTC = "2026-09-17T01:00:00+00:00"
INDEX_NAME = "發行量加權股價指數"
PROTECTED = (
    ROOT / "configs/tw_modular_registry.yaml",
    ROOT / "configs/active_baseline_descriptor.yaml",
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
)


class CaptureError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureError("B19TWII_E_TIME", str(value)) from exc
    if parsed.tzinfo is None:
        raise CaptureError("B19TWII_E_TIME", str(value))
    return parsed.astimezone(timezone.utc)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def fingerprints() -> dict[str, str | None]:
    return {rel(path): sha256(path) if path.is_file() else None for path in PROTECTED}


def normalize_date(value: Any) -> str:
    compact = str(value or "").replace("/", "").replace("-", "").strip()
    if len(compact) == 8 and compact.isdigit():
        return f"{compact[:4]}-{compact[4:6]}-{compact[6:]}"
    if len(compact) == 7 and compact.isdigit():
        return f"{int(compact[:3]) + 1911:04d}-{compact[3:5]}-{compact[5:]}"
    return ""


def numeric(value: Any) -> float:
    text = str(value or "").replace(",", "").strip()
    try:
        result = float(text)
    except ValueError as exc:
        raise CaptureError("B19TWII_E_CLOSE", text) from exc
    if not 0 < result < 1_000_000:
        raise CaptureError("B19TWII_E_CLOSE", text)
    return result


def exact_twii(payload: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(payload, dict) or payload.get("stat") != "OK":
        raise CaptureError("B19TWII_E_PROVIDER_STATUS")
    payload_date = normalize_date(payload.get("date"))
    if payload_date != TARGET:
        raise CaptureError("B19TWII_E_TARGET_DATE", payload_date)
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for table in payload.get("tables", []):
        if not isinstance(table, dict):
            continue
        fields = table.get("fields", [])
        rows = table.get("data", [])
        if not isinstance(fields, list) or not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, list) or len(row) != len(fields):
                continue
            record = dict(zip(map(str, fields), row, strict=True))
            identity = next((str(value).strip() for key, value in record.items() if "指數" in key and str(value).strip() == INDEX_NAME), "")
            if identity == INDEX_NAME:
                matches.append((record, {"table_title": table.get("title"), "fields": fields}))
    if len(matches) != 1:
        raise CaptureError("B19TWII_E_IDENTITY", str(len(matches)))
    return matches[0]


def capture(output: Path, acquisition_run_id: str) -> dict[str, Any]:
    if not output.resolve().is_relative_to(RESEARCH_ROOT.resolve()):
        raise CaptureError("B19TWII_E_OUTPUT", str(output))
    if output.exists():
        raise CaptureError("B19TWII_E_NO_OVERWRITE", str(output))
    before = fingerprints()
    output.mkdir(parents=True, mode=0o700)
    raw_path = output / "twse_mi_index.raw.json"
    normalized_path = output / "TWII_20260916.normalized.json"
    manifest_path = output / "TWII_CAPTURE_MANIFEST.json"
    started_at = now()
    response = requests.get(
        ENDPOINT,
        params={"response": "json", "date": TARGET.replace("-", ""), "type": "ALLBUT0999"},
        headers={"Accept": "application/json", "User-Agent": "modelb-b19r2r-research/1.0"},
        timeout=30,
    )
    fetched_at = now()
    response.raise_for_status()
    raw_path.write_bytes(response.content)
    payload = response.json()
    source_row, table = exact_twii(payload)
    close_key = next((key for key in source_row if "收盤指數" in key), "")
    if not close_key:
        raise CaptureError("B19TWII_E_SCHEMA", "closing index field absent")
    close = numeric(source_row[close_key])
    server_date = response.headers.get("Date")
    server_time = parsedate_to_datetime(server_date).astimezone(timezone.utc) if server_date else None
    if server_time and server_time > parse_time(fetched_at):
        raise CaptureError("B19TWII_E_SERVER_TIME")
    if parse_time(fetched_at) >= parse_time(NEXT_OPEN_UTC):
        raise CaptureError("B19TWII_E_AFTER_NEXT_OPEN", fetched_at)
    normalized = {
        "schema_version": "modelb_b19r2r.twii_normalized.v1",
        "records": [{"date": TARGET, "instrument": "TWII", "close": close}],
    }
    normalized_path.write_text(json.dumps(normalized, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    headers = {key.lower(): value for key, value in response.headers.items()}
    manifest = {
        "schema_version": "modelb_b19r2r.twii_official_capture.v1",
        "status": "PASS",
        "acquisition_run_id": acquisition_run_id,
        "source_id": "twse.public.mi_index.v1",
        "provider": "Taiwan Stock Exchange",
        "endpoint": ENDPOINT,
        "request_parameters": {"response": "json", "date": TARGET.replace("-", ""), "type": "ALLBUT0999"},
        "target_asof": TARGET,
        "trade_date": TARGET,
        "started_at": started_at,
        "fetched_at": fetched_at,
        "available_at": fetched_at,
        "availability_policy": "first_successful_official_response_observation",
        "next_session_open_utc": NEXT_OPEN_UTC,
        "before_next_session_open": True,
        "http_status": response.status_code,
        "response_url": response.url,
        "response_headers": headers,
        "server_date_utc": server_time.isoformat(timespec="seconds") if server_time else None,
        "payload_date": normalize_date(payload.get("date")),
        "source_identity": INDEX_NAME,
        "source_table": table,
        "schema_fields": ["date", "instrument", "close"],
        "row_count": 1,
        "pit_status": "PASS",
        "validator_status": "PASS",
        "raw_artifact": {"path": rel(raw_path), "sha256": sha256(raw_path), "bytes": raw_path.stat().st_size},
        "normalized_artifact": {
            "path": rel(normalized_path),
            "sha256": sha256(normalized_path),
            "bytes": normalized_path.stat().st_size,
        },
        "future_or_outcome_fields": [],
        "no_publish": True,
        "no_latest_write": True,
        "production_allowed": False,
    }
    after = fingerprints()
    if before != after:
        raise CaptureError("B19TWII_E_PROTECTED_DRIFT")
    manifest["protected_before"] = before
    manifest["protected_after"] = after
    manifest["protected_unchanged"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    for path in (raw_path, normalized_path, manifest_path):
        os.chmod(path, 0o444)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--acquisition-run-id", required=True)
    args = parser.parse_args()
    try:
        result = capture(args.output, args.acquisition_run_id)
    except CaptureError as exc:
        print(json.dumps({"status": "FAIL", "error_code": exc.code, "detail": exc.detail}, sort_keys=True))
        return 2
    print(json.dumps({key: result[key] for key in ("status", "trade_date", "available_at", "pit_status")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
