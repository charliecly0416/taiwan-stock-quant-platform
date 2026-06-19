#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260617_20260617T103001Z/job.json"
LATEST = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
REFRESH = ROOT / "qlib_pipeline/data_tw/experiments/option_c_ops/option_c_yahoo_scrapling_refresh_20260617_20260617T103146Z_daily_auto/reports"
V5_STAGING = ROOT / "data_tw/artifacts/provider_staging/phasev5_external_provider_all_ready_codex_v2_provider_staging/data_readiness_manifest.json"
P3 = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_latest.json"
OUT_ROOT = ROOT / "data_tw/artifacts/full_universe_provider_audit"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def finmind_db_summary(symbols: list[str], target_asof: str) -> dict[str, Any]:
    try:
        import psycopg2  # noqa: WPS433
        conn = psycopg2.connect(host="127.0.0.1", port=5433, user="quantdinger", password="quantdinger123", dbname="quantdinger")
        cur = conn.cursor()
        cur.execute(
            "select count(*), count(distinct symbol), min(trade_date), max(trade_date), "
            "sum(case when open is null or high is null or low is null or close is null or volume is null then 1 else 0 end) "
            "from qd_tw_stock_daily_bars where trade_date=%s and symbol=any(%s)",
            (target_asof, symbols),
        )
        count, symbol_count, date_min, date_max, missing_ohlcv = cur.fetchone()
        cur.execute("select symbol from unnest(%s::text[]) s(symbol) except select symbol from qd_tw_stock_daily_bars where trade_date=%s", (symbols, target_asof))
        missing_symbols = [row[0] for row in cur.fetchall()]
        cur.execute("select min(trade_date), max(trade_date), count(*), count(distinct symbol) from qd_tw_stock_daily_bars where symbol=any(%s)", (symbols,))
        all_min, all_max, all_rows, all_symbols = cur.fetchone()
        cur.close(); conn.close()
        return {
            "status": "ready" if symbol_count >= len(symbols) and not missing_symbols and int(missing_ohlcv or 0) == 0 else "unavailable",
            "table": "qd_tw_stock_daily_bars",
            "target_asof": target_asof,
            "rows_on_target_asof": int(count or 0),
            "symbols_on_target_asof": int(symbol_count or 0),
            "date_min_on_target": str(date_min) if date_min else "",
            "date_max_on_target": str(date_max) if date_max else "",
            "missing_ohlcv_rows_on_target": int(missing_ohlcv or 0),
            "missing_symbols": missing_symbols,
            "window_min": str(all_min) if all_min else "",
            "window_max": str(all_max) if all_max else "",
            "window_rows": int(all_rows or 0),
            "window_symbols": int(all_symbols or 0),
            "readonly_query_only": True,
        }
    except Exception as exc:
        return {"status": "unavailable", "error": f"{type(exc).__name__}: {str(exc)[:240]}", "readonly_query_only": True}


def build(out_dir: Path) -> dict[str, Any]:
    created_at = now()
    job = read_json(JOB)
    latest = read_json(LATEST)
    run_dir = ROOT / "qlib_pipeline" / str(latest.get("run_dir"))
    signal_summary = read_json(run_dir / "signal_summary.json")
    formal_validation = read_json(run_dir / "formal_validation.json")
    refresh_summary = read_json(REFRESH / "execution_summary.json")
    fetch = read_json(REFRESH / "fetch_report.json")
    provider_validation = read_json(REFRESH / "provider_validation.json")
    model_smoke = read_json(REFRESH / "model_smoke.json")
    v5 = read_json(V5_STAGING)
    p3 = read_json(P3)
    prediction = pd.read_csv(run_dir / "prediction.csv")
    symbols_file = JOB.parent / "finmind_symbols.txt"
    symbols = [line.strip() for line in symbols_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    finmind = finmind_db_summary(symbols, str(job.get("asof")))
    v5_sources = {str(s.get("source_id")): s for s in v5.get("sources") or []}
    audit = {
        "schema_version": "w0.full_universe_provider_audit.v1",
        "artifact_type": "full_universe_provider_audit",
        "created_at": created_at,
        "target_asof": job.get("asof"),
        "readonly_audit_only": True,
        "allow_network": False,
        "source_artifacts": {
            "daily_auto_update_job": rel(JOB),
            "latest_signal": rel(LATEST),
            "refresh_execution_summary": rel(REFRESH / "execution_summary.json"),
            "refresh_fetch_report": rel(REFRESH / "fetch_report.json"),
            "refresh_provider_validation": rel(REFRESH / "provider_validation.json"),
            "refresh_model_smoke": rel(REFRESH / "model_smoke.json"),
            "v5_readiness_manifest": rel(V5_STAGING),
            "p3_daily_ltr_rerank_latest": rel(P3),
        },
        "full_universe": {
            "universe_name": refresh_summary.get("universe"),
            "size": int(refresh_summary.get("universe_count") or 0),
            "symbols_file": rel(symbols_file),
            "symbols_count": len(symbols),
        },
        "yahoo_scrapling_provider": {
            "status": "ready" if fetch.get("status") == "pass" and provider_validation.get("status") == "pass" else "unavailable",
            "source": fetch.get("source"),
            "source_policy": fetch.get("source_policy"),
            "symbols_expected": fetch.get("symbols_expected"),
            "symbols_success": fetch.get("symbols_success"),
            "symbols_failed_count": len(fetch.get("symbols_failed") or {}),
            "rows_written": fetch.get("rows_written"),
            "provider_calendar_max": provider_validation.get("calendar_max"),
            "provider_calendar_has_asof": provider_validation.get("calendar_has_asof"),
            "provider_active_universe_count": provider_validation.get("active_universe_count"),
            "expected_field_counts": provider_validation.get("expected_field_counts"),
            "missing_feature_symbols": provider_validation.get("missing_feature_symbols") or [],
            "fallback_used": False,
        },
        "finmind_daily_raw": finmind,
        "model_signal": {
            "status": "ready" if signal_summary.get("status") == "accepted" and int(signal_summary.get("prediction_rows") or 0) >= 150 else "unavailable",
            "latest_signal_asof": latest.get("asof"),
            "prediction_rows": signal_summary.get("prediction_rows"),
            "finite_prediction_share": signal_summary.get("finite_prediction_share"),
            "prediction_csv_rows": int(len(prediction)),
            "prediction_unique_instruments": int(prediction["instrument"].nunique()) if "instrument" in prediction else 0,
            "formal_validation_status": formal_validation.get("status"),
            "formal_active_universe_count": formal_validation.get("active_universe_count"),
            "model_smoke_status": model_smoke.get("status"),
            "model_smoke_symbols": model_smoke.get("symbols"),
            "model_smoke_prediction_rows": model_smoke.get("prediction_rows"),
        },
        "orthogonal_and_v5_sample_boundary": {
            "v5_staging_is_sample": True,
            "v5_yahoo_symbols_requested": (v5_sources.get("yahoo_daily_price") or {}).get("source_evidence", {}).get("summary", {}).get("symbols_requested"),
            "v5_gate_status": v5.get("gate_status"),
            "orthogonal_status": (v5_sources.get("orthogonal_o2_features") or {}).get("status"),
            "orthogonal_actual_latest_asof": (v5_sources.get("orthogonal_o2_features") or {}).get("actual_latest_asof"),
            "orthogonal_coverage_count": (v5_sources.get("orthogonal_o2_features") or {}).get("coverage_count"),
            "orthogonal_coverage_ratio": (v5_sources.get("orthogonal_o2_features") or {}).get("coverage_ratio"),
            "p3_status": p3.get("status"),
            "p3_asof": p3.get("asof"),
            "p3_top50_scored_count": p3.get("top50_scored_count"),
            "p3_pit_pass": p3.get("pit_pass"),
        },
        "forbidden_action_audit": {
            "actions": {
                "w0_provider_publish_triggered": False,
                "w0_accepted_latest_switched": False,
                "w0_monitor_config_written": False,
                "w0_monitor_scan_triggered": False,
                "w0_alerts_written": False,
                "w0_broker_connected": False,
                "w0_quick_trade_triggered": False,
                "w0_orders_created_or_sent": False,
                "w0_agent_prompt_or_tool_modified": False,
            },
            "historical_daily_auto_update_provider_publish_triggered": bool(job.get("provider_publish_triggered")),
            "note": "W0 reads historical full-universe publish evidence but does not trigger publish or accepted latest changes.",
        },
    }
    write_json(out_dir / "full_universe_provider_audit.json", audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description="W0 readonly full-universe provider coverage audit.")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.allow_network:
        raise SystemExit("W0 audit is readonly/offline in this implementation; --allow-network is intentionally rejected")
    run_id = "w0_20260617_full_universe_audit"
    out_dir = Path(args.out_dir) if args.out_dir else OUT_ROOT / run_id
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    result = build(out_dir)
    output = {"ok": True, "audit": rel(out_dir / "full_universe_provider_audit.json"), "status": "passed", "full_universe_size": result["full_universe"]["size"]}
    print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output["audit"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
