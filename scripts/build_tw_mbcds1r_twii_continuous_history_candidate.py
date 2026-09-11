#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv"
CALENDAR = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
LATEST = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
OUT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds1r_twii_continuous_history_candidate_20260905"
API = "https://api.finmindtrade.com/api/v4/data"
FETCH_START = "2026-04-01"

PROTECTED = [
    FORMAL,
    LATEST,
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprints() -> dict[str, Any]:
    return {
        str(path.relative_to(ROOT)): {
            "exists": path.exists(),
            "size": path.stat().st_size if path.exists() else None,
            "sha256": sha256(path) if path.is_file() else None,
        }
        for path in PROTECTED
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def load_token() -> str:
    token = os.environ.get("FINMIND_TOKEN", "").strip()
    if token:
        return token
    for env_path in [ROOT / ".env", ROOT / ".env.example"]:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("FINMIND_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def fetch_finmind(target_end: str) -> tuple[dict[str, Any], dict[str, Any]]:
    token = load_token()
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": "TAIEX",
        "start_date": FETCH_START,
        "end_date": target_end,
    }
    if token:
        params["token"] = token
    url = API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "tw-mbcds1r/1.0"})
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or "http://127.0.0.1:7890"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    started = now()
    try:
        with opener.open(request, timeout=60) as response:
            raw = response.read()
            status = int(getattr(response, "status", 200))
        payload = json.loads(raw.decode("utf-8"))
        meta = {
            "started_at": started,
            "completed_at": now(),
            "endpoint": API,
            "dataset": params["dataset"],
            "data_id": params["data_id"],
            "start_date": FETCH_START,
            "end_date": target_end,
            "token_supplied": bool(token),
            "token_persisted": False,
            "proxy": "local_clash" if "127.0.0.1" in proxy else "environment_proxy",
            "http_status": status,
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "error": "",
        }
        return payload, meta
    except Exception as exc:
        return {}, {
            "started_at": started,
            "completed_at": now(),
            "endpoint": API,
            "dataset": params["dataset"],
            "data_id": params["data_id"],
            "start_date": FETCH_START,
            "end_date": target_end,
            "token_supplied": bool(token),
            "token_persisted": False,
            "proxy": "local_clash" if "127.0.0.1" in proxy else "environment_proxy",
            "http_status": getattr(exc, "code", "network_error"),
            "raw_sha256": "",
            "error": f"{type(exc).__name__}:{exc}",
        }


def finmind_frame(payload: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for item in payload.get("data") or []:
        try:
            close = float(item.get("close"))
        except (TypeError, ValueError):
            continue
        day = str(item.get("date") or "")[:10]
        if len(day) == 10 and math.isfinite(close) and close > 0:
            rows.append({"date": day, "close": close})
    if not rows:
        return pd.DataFrame(columns=["date", "close"])
    return pd.DataFrame(rows).drop_duplicates("date", keep="last").sort_values("date")


def main() -> int:
    before = fingerprints()
    latest = json.loads(LATEST.read_text(encoding="utf-8"))
    target_asof = str(latest.get("asof") or "")[:10]
    payload, fetch_meta = fetch_finmind(target_asof)
    OUT.mkdir(parents=True, exist_ok=True)
    raw_path = OUT / "finmind_taiex_raw.json"
    write_json(raw_path, payload)
    write_json(OUT / "fetch_metadata.json", fetch_meta)

    formal = pd.read_csv(FORMAL, usecols=["date", "close"])
    formal["date"] = formal["date"].astype(str).str[:10]
    formal["close"] = pd.to_numeric(formal["close"], errors="coerce")
    formal = formal.dropna().drop_duplicates("date", keep="last").sort_values("date")
    fetched = finmind_frame(payload)

    overlap = formal.merge(fetched, on="date", suffixes=("_formal", "_finmind"))
    overlap["abs_diff"] = (overlap["close_formal"] - overlap["close_finmind"]).abs()
    overlap["relative_diff"] = overlap["abs_diff"] / overlap["close_formal"].abs()
    overlap.to_csv(OUT / "cross_source_overlap_audit.csv", index=False)

    formal_tagged = formal.assign(source_id="formal_yahoo_adjusted_twii", source_path=str(FORMAL.relative_to(ROOT)), fetched_at="")
    fetched_tagged = fetched.assign(source_id="finmind_taiwan_stock_price_taiex", source_path=str(raw_path.relative_to(ROOT)), fetched_at=fetch_meta["completed_at"])
    combined = pd.concat([formal_tagged, fetched_tagged], ignore_index=True)
    combined = combined.sort_values(["date", "source_id"]).drop_duplicates("date", keep="last")
    combined = combined[combined["date"] <= target_asof].sort_values("date")

    calendar = [line.strip()[:10] for line in CALENDAR.read_text(encoding="utf-8").splitlines() if line.strip() and line.strip()[:10] <= target_asof]
    required = calendar[-120:]
    candidate_dates = set(combined["date"])
    missing = [day for day in required if day not in candidate_dates]
    extras = sorted(candidate_dates - set(calendar))
    calendar_audit = pd.DataFrame(
        [{"date": day, "required": True, "present": day in candidate_dates, "source_id": str(combined.loc[combined["date"] == day, "source_id"].iloc[0]) if day in candidate_dates else ""} for day in required]
    )
    calendar_audit.to_csv(OUT / "calendar_closure_audit.csv", index=False)
    combined.to_csv(OUT / "twii_daily_candidate_with_lineage.csv", index=False)
    combined[["date", "close"]].to_csv(OUT / "twii_daily_candidate.csv", index=False)

    finmind_status_ok = payload.get("status") in {200, "200", True, None} and not fetched.empty
    overlap_ok = len(overlap) >= 10 and float(overlap["relative_diff"].max()) <= 1e-6
    coverage_ok = len(required) == 120 and not missing and target_asof in candidate_dates
    after = fingerprints()
    protected_ok = before == after
    ok = finmind_status_ok and overlap_ok and coverage_ok and protected_ok

    validation = {
        "created_at": now(),
        "phase": "MBCDS1R_TWII_CONTINUOUS_HISTORY_REPAIR_NO_MODEL_SCORING",
        "ok": ok,
        "decision": "READY_TO_RERUN_MBCDS0" if ok else "STOP_TWII_CANDIDATE_NOT_READY",
        "target_asof": target_asof,
        "finmind_status": payload.get("status"),
        "finmind_message": str(payload.get("msg") or "")[:300],
        "fetched_rows": int(fetched.shape[0]),
        "fetched_date_min": str(fetched["date"].min()) if not fetched.empty else "",
        "fetched_date_max": str(fetched["date"].max()) if not fetched.empty else "",
        "overlap_rows": int(overlap.shape[0]),
        "overlap_max_relative_diff": float(overlap["relative_diff"].max()) if not overlap.empty else None,
        "required_calendar_sessions": len(required),
        "covered_calendar_sessions": len(required) - len(missing),
        "missing_calendar_sessions": missing,
        "candidate_exact_target": target_asof in candidate_dates,
        "candidate_extra_noncalendar_dates": extras,
        "protected_paths_unchanged": protected_ok,
        "raw_response_sha256": sha256(raw_path),
        "credential_persisted": False,
        "no_model_training_or_scoring": True,
        "no_latest_provider_cron_frontend_backend_write": True,
    }
    write_json(OUT / "validation_report.json", validation)
    write_json(OUT / "protected_path_fingerprint_audit.json", {"before": before, "after": after, "unchanged": protected_ok})
    artifact_paths = [
        raw_path,
        OUT / "fetch_metadata.json",
        OUT / "cross_source_overlap_audit.csv",
        OUT / "calendar_closure_audit.csv",
        OUT / "twii_daily_candidate_with_lineage.csv",
        OUT / "twii_daily_candidate.csv",
        OUT / "validation_report.json",
        OUT / "protected_path_fingerprint_audit.json",
    ]
    write_json(OUT / "checksum_manifest.json", {str(path.relative_to(ROOT)): sha256(path) for path in artifact_paths})
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
