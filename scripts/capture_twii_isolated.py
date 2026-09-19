#!/usr/bin/env python3
"""Capture a FinMind TAIEX response into an isolated, immutable evidence directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API = "https://api.finmindtrade.com/api/v4/data"
PROTECTED = (
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint() -> dict[str, Any]:
    return {
        str(path.relative_to(ROOT)): {
            "exists": path.exists(),
            "size": path.stat().st_size if path.exists() else None,
            "sha256": sha256(path) if path.is_file() else None,
        }
        for path in PROTECTED
    }


def token() -> str:
    value = os.environ.get("FINMIND_TOKEN", "").strip()
    if value:
        return value
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("FINMIND_TOKEN="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    output = Path(args.output_dir).resolve()
    isolated = (ROOT / "data_tw/experiments").resolve()
    if not output.is_relative_to(isolated):
        raise SystemExit("output-dir must be under data_tw/experiments")
    output.mkdir(parents=True, exist_ok=True)
    raw_path = output / "twii.raw.json"
    metadata_path = output / "twii.capture.json"
    if raw_path.exists() or metadata_path.exists():
        raise SystemExit("immutable capture target already exists")

    before = fingerprint()
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": "TAIEX",
        "start_date": args.start,
        "end_date": args.end,
    }
    secret = token()
    if secret:
        params["token"] = secret
    public_params = {key: value for key, value in params.items() if key != "token"}
    url = API + "?" + urllib.parse.urlencode(params)
    observed_at = utc_now()
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "tw-o4-shadow/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
        http_status = int(getattr(response, "status", 200))
    payload = json.loads(raw.decode("utf-8"))
    raw_path.write_bytes(raw)
    rows = payload.get("data") or []
    dates = sorted({str(row.get("date") or "")[:10] for row in rows if row.get("date")})
    metadata = {
        "schema_version": "o4.twii_isolated_capture.v1",
        "source_run_id": args.source_run_id,
        "observed_at": observed_at,
        "completed_at": utc_now(),
        "endpoint": API,
        "request_parameters": public_params,
        "credential_supplied": bool(secret),
        "credential_persisted": False,
        "http_status": http_status,
        "provider_status": payload.get("status"),
        "provider_message": str(payload.get("msg") or "")[:300],
        "row_count": len(rows),
        "date_min": dates[0] if dates else "",
        "date_max": dates[-1] if dates else "",
        "target_date_present": args.end in dates,
        "raw_path": str(raw_path.relative_to(ROOT)),
        "raw_sha256": sha256(raw_path),
        "no_publish": True,
        "no_latest_write": True,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    after = fingerprint()
    audit = {"before": before, "after": after, "unchanged": before == after}
    (output / "protected_fingerprint_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    if before != after:
        raise RuntimeError("protected path changed during isolated capture")
    if args.json:
        print(json.dumps(metadata, indent=2, ensure_ascii=True))
    return 0 if metadata["target_date_present"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
