#!/usr/bin/env python3
"""Isolated TWSE TWII adapter for the frozen 2026-09-15 observation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RUN = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260916_20260916T103002Z/same_run_handoff_artifacts/daily_price"
NORMALIZED = SOURCE_RUN / "twii.normalized.json"
ADAPTER_OUTPUT = SOURCE_RUN / "twii.adapter_output.json"
RAW = SOURCE_RUN / "twii.http.raw"
EXPECTED_INDEX = "發行量加權股價指數"
EXPECTED_ROC_DATE = "1150915"
EXPECTED_DATE = "2026-09-15"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def roc_to_iso(value: str) -> str:
    text = str(value).strip()
    if len(text) != 7 or not text.isdigit():
        raise ValueError("TWSE ROC date must be exactly YYYMMDD")
    year = int(text[:3]) + 1911
    return f"{year:04d}-{text[3:5]}-{text[5:7]}"


def materialize(output_dir: Path) -> dict[str, Any]:
    csv_path = output_dir / "TWII_20260915.csv"
    manifest_path = output_dir / "TWII_20260915_ADAPTER_MANIFEST.json"
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("refusing to overwrite isolated TWII adapter output")
    output_dir.mkdir(parents=True, mode=0o700, exist_ok=True)

    prior = json.loads(ADAPTER_OUTPUT.read_text(encoding="utf-8"))
    if prior.get("target_asof") != "2026-09-16" or prior.get("scope_status") != "BLOCKED_PROVIDER_SCHEMA":
        raise RuntimeError("unexpected prior TWII adapter status")
    if prior.get("schema_errors") != ["target_date_mismatch"]:
        raise RuntimeError("prior adapter blocker is not the frozen target-date mismatch")

    payload = json.loads(NORMALIZED.read_text(encoding="utf-8"))
    records = [row for row in payload.get("records", []) if row.get("指數") == EXPECTED_INDEX and str(row.get("日期", "")) == EXPECTED_ROC_DATE]
    if len(records) != 1 or roc_to_iso(records[0]["日期"]) != EXPECTED_DATE:
        raise RuntimeError("expected one exact 2026-09-15 TWII identity row")
    required = {"日期", "指數", "收盤指數"}
    if not required.issubset(records[0]):
        raise RuntimeError("TWII source schema is incomplete")
    close = pd.to_numeric(str(records[0]["收盤指數"]).replace(",", ""), errors="coerce")
    if pd.isna(close) or float(close) <= 0:
        raise RuntimeError("TWII close is not a finite positive value")

    pd.DataFrame([{"date": EXPECTED_DATE, "instrument": "TWII", "close": float(close)}]).to_csv(csv_path, index=False)
    os.chmod(csv_path, 0o600)
    manifest = {
        "schema_version": "modelb.b19r2r.twse_twii_20260915_adapter.v1",
        "status": "PASS",
        "source_bindings": {
            rel(RAW): {"sha256": sha256(RAW), "bytes": RAW.stat().st_size},
            rel(NORMALIZED): {"sha256": sha256(NORMALIZED), "bytes": NORMALIZED.stat().st_size},
            rel(ADAPTER_OUTPUT): {"sha256": sha256(ADAPTER_OUTPUT), "bytes": ADAPTER_OUTPUT.stat().st_size},
        },
        "source_identity": EXPECTED_INDEX,
        "source_roc_date": EXPECTED_ROC_DATE,
        "normalized_date": EXPECTED_DATE,
        "prior_target": "2026-09-16",
        "prior_blocker": "target_date_mismatch",
        "prior_blocker_proves_value_absence": False,
        "row_count": 1,
        "date_count": 1,
        "schema": ["date", "instrument", "close"],
        "completeness_boolean": True,
        "artifact": {"path": rel(csv_path), "sha256": sha256(csv_path), "bytes": csv_path.stat().st_size},
        "value_or_distribution_exposed_in_manifest": False,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    os.chmod(manifest_path, 0o600)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = materialize(args.output)
    print(json.dumps({"status": manifest["status"], "row_count": manifest["row_count"], "date_count": manifest["date_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
