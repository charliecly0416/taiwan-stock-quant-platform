#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DAPR_ROOT = ROOT / "data_tw/experiments/daily_accepted_production_readiness"
DAPR0_DIR = DAPR_ROOT / "dapr0_inventory"
DAPR1_DIR = DAPR_ROOT / "dapr1_canonical_bridge_contract"
DAPR4_DIR = DAPR_ROOT / "dapr4_local_file_canonical_bridge_feasibility"
OUT_DIR = DAPR_ROOT / "dapr5_readonly_db_backed_exact_target_bridge_export_or_blocker"
BRIDGE_DIR = OUT_DIR / "stock_price_bridge"
FORMAL_INSTRUMENTS = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt"

DEFAULT_DB = {
    "host": "127.0.0.1",
    "port": 5433,
    "user": "quantdinger",
    "password": "quantdinger123",
    "dbname": "quantdinger",
}
TARGET_SOURCE = "finmind"
REQUIRED_COLUMNS = ["symbol", "date", "open", "high", "low", "close", "volume", "vwap", "factor"]
FORBIDDEN_ACTIONS = {
    "provider_pull_triggered": False,
    "provider_publish_triggered": False,
    "formal_provider_or_calendar_mutated": False,
    "formal_normalized_mutated": False,
    "accepted_latest_switch_triggered": False,
    "qlib_refresh_triggered": False,
    "model_scoring_triggered": False,
    "model_inference_input_built": False,
    "score_job_built": False,
    "model_signal_artifact_built": False,
    "readonly_latest_published": False,
    "agent_prompt_built_or_published": False,
    "openai_called": False,
    "database_write_triggered": False,
    "monitor_broker_order_or_target_written": False,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(name: str, payload: Any) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_database_url(value: str) -> dict[str, Any]:
    if not value:
        return dict(DEFAULT_DB)
    parsed = urlparse(value)
    return {
        "host": parsed.hostname or DEFAULT_DB["host"],
        "port": int(parsed.port or DEFAULT_DB["port"]),
        "user": parsed.username or DEFAULT_DB["user"],
        "password": parsed.password or DEFAULT_DB["password"],
        "dbname": (parsed.path or f"/{DEFAULT_DB['dbname']}").lstrip("/") or DEFAULT_DB["dbname"],
    }


def db_config() -> dict[str, Any]:
    config = parse_database_url(os.getenv("DATABASE_URL", ""))
    for env_name, key in [
        ("PGHOST", "host"),
        ("PGPORT", "port"),
        ("PGUSER", "user"),
        ("PGPASSWORD", "password"),
        ("PGDATABASE", "dbname"),
    ]:
        value = os.getenv(env_name)
        if value:
            config[key] = int(value) if key == "port" else value
    return config


def read_formal_symbols() -> list[str]:
    if not FORMAL_INSTRUMENTS.exists():
        return []
    symbols: list[str] = []
    for line in FORMAL_INSTRUMENTS.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if parts and parts[0].startswith("TW"):
            symbols.append(parts[0][2:])
    return sorted(set(symbols))


def to_float(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


def connect_readonly() -> Any:
    import psycopg2  # noqa: WPS433

    conn = psycopg2.connect(**db_config())
    conn.set_session(readonly=True, autocommit=True)
    return conn


def fetch_coverage(cur: Any, symbols: list[str], target_asof: str) -> dict[str, Any]:
    cur.execute(
        """
        SELECT source, count(*) AS rows, count(distinct symbol) AS symbols,
               min(trade_date)::text AS min_date, max(trade_date)::text AS max_date,
               count(*) FILTER (WHERE trade_date = %s) AS target_rows,
               count(distinct symbol) FILTER (WHERE trade_date = %s) AS target_symbols,
               count(*) FILTER (WHERE coalesce(quality_flags, '') <> '') AS flagged_rows,
               count(*) FILTER (WHERE trade_date = %s AND coalesce(quality_flags, '') <> '') AS target_flagged_rows
        FROM qd_tw_stock_daily_bars
        WHERE symbol = ANY(%s)
        GROUP BY source
        ORDER BY source
        """,
        (target_asof, target_asof, target_asof, symbols),
    )
    by_source = [dict(row) for row in cur.fetchall()]
    cur.execute(
        """
        SELECT min(cnt) AS min_rows_per_symbol,
               max(cnt) AS max_rows_per_symbol,
               count(*) AS symbol_count
        FROM (
            SELECT symbol, count(*) AS cnt
            FROM qd_tw_stock_daily_bars
            WHERE source = %s
              AND symbol = ANY(%s)
              AND trade_date <= %s
              AND coalesce(quality_flags, '') = ''
            GROUP BY symbol
        ) s
        """,
        (TARGET_SOURCE, symbols, target_asof),
    )
    history_row = dict(cur.fetchone() or {})
    cur.execute(
        """
        SELECT s.symbol
        FROM unnest(%s::text[]) s(symbol)
        EXCEPT
        SELECT symbol
        FROM qd_tw_stock_daily_bars
        WHERE source = %s
          AND trade_date = %s
          AND coalesce(quality_flags, '') = ''
        ORDER BY symbol
        """,
        (symbols, TARGET_SOURCE, target_asof),
    )
    missing_target_symbols = [row["symbol"] for row in cur.fetchall()]
    return {
        "source_table": "qd_tw_stock_daily_bars",
        "target_source": TARGET_SOURCE,
        "target_asof": target_asof,
        "expected_symbol_count": len(symbols),
        "by_source": by_source,
        "clean_history_summary": history_row,
        "missing_target_symbols": missing_target_symbols,
        "target_clean_coverage_ok": len(missing_target_symbols) == 0,
    }


def fetch_rows(cur: Any, symbols: list[str], target_asof: str) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT symbol, trade_date::text AS date, open, high, low, close, volume,
               trading_money, source, quality_flags
        FROM qd_tw_stock_daily_bars
        WHERE source = %s
          AND symbol = ANY(%s)
          AND trade_date <= %s
          AND coalesce(quality_flags, '') = ''
        ORDER BY symbol ASC, trade_date ASC
        """,
        (TARGET_SOURCE, symbols, target_asof),
    )
    return [dict(row) for row in cur.fetchall()]


def write_bridge_csvs(rows: list[dict[str, Any]], target_asof: str) -> dict[str, Any]:
    BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["symbol"])].append(row)

    entries: list[dict[str, Any]] = []
    symbols_with_target = 0
    for symbol, symbol_rows in sorted(grouped.items()):
        out_path = BRIDGE_DIR / f"TW{symbol}.csv"
        dates = [str(row["date"]) for row in symbol_rows]
        has_target = target_asof in dates
        if has_target:
            symbols_with_target += 1
        with out_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=REQUIRED_COLUMNS)
            writer.writeheader()
            for row in symbol_rows:
                open_ = to_float(row["open"])
                high = to_float(row["high"])
                low = to_float(row["low"])
                close = to_float(row["close"])
                writer.writerow(
                    {
                        "symbol": f"TW{symbol}",
                        "date": row["date"],
                        "open": open_,
                        "high": high,
                        "low": low,
                        "close": close,
                        "volume": int(row["volume"] or 0),
                        "vwap": round((open_ + high + low + close) / 4.0, 6),
                        "factor": 1.0,
                    }
                )
        entries.append(
            {
                "symbol": f"TW{symbol}",
                "path": rel(out_path),
                "rows": len(symbol_rows),
                "date_min": min(dates) if dates else "",
                "date_max": max(dates) if dates else "",
                "has_target_asof": has_target,
                "sha256": sha256(out_path),
            }
        )
    return {
        "bridge_dir": rel(BRIDGE_DIR),
        "file_count": len(entries),
        "symbols_with_target_asof": symbols_with_target,
        "row_count": len(rows),
        "entries": entries,
    }


def build_manifest(paths: list[Path], decision: str) -> dict[str, Any]:
    csv_entries = [
        {
            "path": rel(path),
            "exists": path.exists(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(BRIDGE_DIR.glob("TW*.csv"))
    ]
    return {
        "schema_version": "dapr.artifact_manifest.v1",
        "created_at": utc_now(),
        "artifact_manifest_status": "written",
        "route_decision": decision,
        "status": "pass",
        "entries": [
            {
                "path": rel(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else None,
                "sha256": sha256(path) if path.exists() else "",
            }
            for path in paths
        ],
        "bridge_csv_entries": csv_entries,
    }


def build(target_asof: str = "") -> dict[str, Any]:
    created_at = utc_now()
    dapr0 = read_json(DAPR0_DIR / "inventory_summary.json")
    dapr1 = read_json(DAPR1_DIR / "bridge_contract.json")
    dapr4 = read_json(DAPR4_DIR / "canonical_bridge_build_feasibility_decision.json")
    target = target_asof or str(dapr4.get("target_asof") or dapr0.get("target_asof") or "")
    if not target:
        target = "2026-07-17"
    symbols = read_formal_symbols()

    forbidden_action_audit = {
        "schema_version": "dapr.forbidden_action_audit.v1",
        "created_at": created_at,
        "route": "DAPR5_READONLY_DB_BACKED_EXACT_TARGET_BRIDGE_EXPORT_OR_BLOCKER",
        "all_false": all(value is False for value in FORBIDDEN_ACTIONS.values()),
        "actions": FORBIDDEN_ACTIONS,
        "db_access_authorized_by_user": True,
        "db_access_mode": "readonly_select_only",
        "provider_pull_allowed": False,
        "provider_pull_attempted": False,
        "database_write_allowed": False,
        "database_write_attempted": False,
        "write_scope": [rel(OUT_DIR)],
    }

    try:
        conn = connect_readonly()
        try:
            from psycopg2.extras import RealDictCursor  # noqa: WPS433

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SHOW transaction_read_only")
                readonly_state = str(cur.fetchone().get("transaction_read_only") or "")
                coverage = fetch_coverage(cur, symbols, target)
                rows = fetch_rows(cur, symbols, target) if coverage["target_clean_coverage_ok"] else []
        finally:
            conn.close()
        db_error = ""
    except Exception as exc:
        readonly_state = ""
        coverage = {
            "source_table": "qd_tw_stock_daily_bars",
            "target_source": TARGET_SOURCE,
            "target_asof": target,
            "expected_symbol_count": len(symbols),
            "target_clean_coverage_ok": False,
        }
        rows = []
        db_error = f"{type(exc).__name__}: {exc}"

    bridge_export = write_bridge_csvs(rows, target) if rows else {
        "bridge_dir": rel(BRIDGE_DIR),
        "file_count": 0,
        "symbols_with_target_asof": 0,
        "row_count": 0,
        "entries": [],
    }
    export_ok = (
        not db_error
        and str(readonly_state).lower() == "on"
        and bridge_export["file_count"] == len(symbols) == 150
        and bridge_export["symbols_with_target_asof"] == 150
    )

    model_a_ready = False
    decision = (
        "EXPORTED_DB_BACKED_EXACT_TARGET_BRIDGE_CANDIDATE_LINEAGE_REVIEW_REQUIRED"
        if export_ok
        else "BLOCKED_DB_BACKED_EXACT_TARGET_BRIDGE_EXPORT_FAILED"
    )
    db_preflight = {
        "schema_version": "dapr5.db_readonly_preflight.v1",
        "created_at": created_at,
        "target_asof": target,
        "db_access_authorized_by_user": True,
        "db_access_mode": "readonly_select_only",
        "transaction_read_only": readonly_state,
        "db_error": db_error,
        "formal_universe_symbols": len(symbols),
        "formal_instruments_path": rel(FORMAL_INSTRUMENTS),
    }
    source_coverage = {
        "schema_version": "dapr5.db_source_coverage.v1",
        "created_at": created_at,
        "target_asof": target,
        "coverage": coverage,
    }
    bridge_manifest = {
        "schema_version": "dapr5.db_backed_bridge_export_manifest.v1",
        "created_at": created_at,
        "target_asof": target,
        "source_table": "qd_tw_stock_daily_bars",
        "source": TARGET_SOURCE,
        "quality_policy": "coalesce(quality_flags,'') = ''",
        "bridge_columns": REQUIRED_COLUMNS,
        "export_ok": export_ok,
        **bridge_export,
    }
    candidate_readiness = {
        "schema_version": "dapr5.db_backed_bridge_candidate_readiness.v1",
        "created_at": created_at,
        "bridge_asof": target,
        "target_asof": target,
        "candidate_type": "readonly_db_backed_exact_target_bridge",
        "candidate_export_status": "pass" if export_ok else "fail",
        "validator_status": "candidate_export_pass_lineage_not_accepted" if export_ok else "fail",
        "production_allowed": False,
        "not_published_latest": True,
        "readiness_accepted_for_dapr3_no_publish": False,
        "reason_not_accepted": (
            "FinMind DB-backed unadjusted bridge covers target_asof but is not formal Yahoo-adjusted same-lineage Model A input; lineage/model compatibility review is required"
            if export_ok
            else "DB-backed export failed or target coverage incomplete"
        ),
        "coverage": {
            "symbols_expected": len(symbols),
            "files_exported": bridge_export["file_count"],
            "symbols_with_asof": bridge_export["symbols_with_target_asof"],
            "rows_exported": bridge_export["row_count"],
        },
        "model_compatibility": {
            "model_a_feature_compatible": model_a_ready,
            "source_lineage": "finmind_unadjusted_db_archive",
            "formal_model_lineage": "yahoo_adjusted_primary_option_c",
            "factor_policy": "factor=1.0 unadjusted export",
            "requires_lineage_review": True,
        },
        "forbidden_actions": {"all_false": True, "actions": FORBIDDEN_ACTIONS},
    }
    compatibility_decision = {
        "schema_version": "dapr5.lineage_model_compatibility_decision.v1",
        "created_at": created_at,
        "target_asof": target,
        "candidate_export_ok": export_ok,
        "model_a_ready": model_a_ready,
        "ready_for_latest_switch": False,
        "ready_for_provider_publish": False,
        "ready_for_model_a_no_publish_dry_run": False,
        "decision": "CANDIDATE_EXPORTED_NOT_MODELA_READY_LINEAGE_REVIEW_REQUIRED" if export_ok else "BLOCKED_NO_DB_BACKED_BRIDGE_CANDIDATE",
        "reasons": [
            "DB source is FinMind archive with factor=1.0 unadjusted export",
            "formal accepted provider/model lineage is yahoo_adjusted_primary Option C",
            "DAPR1 excludes FinMind raw evidence alone as Model A-ready input",
            "No provider publish, qlib refresh, scoring, or latest switch is authorized in DAPR5",
        ],
        "dapr1_contract_path": rel(DAPR1_DIR / "bridge_contract.json"),
        "dapr1_accepted_input_types": dapr1.get("accepted_input_types", []),
    }
    decision_payload = {
        "schema_version": "dapr5.candidate_or_blocker_decision.v1",
        "created_at": created_at,
        "target_asof": target,
        "decision": decision,
        "export_ok": export_ok,
        "candidate_bridge_dir": rel(BRIDGE_DIR),
        "candidate_readiness_path": rel(OUT_DIR / "db_backed_bridge_candidate_readiness.json"),
        "readiness_accepted_for_dapr3_no_publish": False,
        "model_a_ready": model_a_ready,
        "ready_for_latest_switch": False,
        "ready_for_provider_publish": False,
        "ready_for_model_a_no_publish_dry_run": False,
        "next_required_action": (
            "perform DAPR6 lineage/model compatibility review or build a same-lineage adjusted provider bridge"
            if export_ok
            else "repair DB export coverage or authorize controlled provider bridge build"
        ),
        "forbidden_actions_all_false": True,
    }

    paths = [
        write_json("db_readonly_preflight.json", db_preflight),
        write_json("db_source_coverage.json", source_coverage),
        write_json("db_backed_bridge_export_manifest.json", bridge_manifest),
        write_json("db_backed_bridge_candidate_readiness.json", candidate_readiness),
        write_json("lineage_model_compatibility_decision.json", compatibility_decision),
        write_json("candidate_or_blocker_decision.json", decision_payload),
        write_json("forbidden_action_audit.json", forbidden_action_audit),
    ]
    write_json("artifact_manifest.json", build_manifest(paths, decision))
    return decision_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="DAPR5 readonly DB-backed exact-target bridge export or blocker.")
    parser.add_argument("--target-asof", default="")
    args = parser.parse_args()
    result = build(args.target_asof)
    print(
        "DAPR5 readonly DB-backed exact-target bridge export: "
        f"decision={result['decision']} target_asof={result['target_asof']} "
        f"export_ok={result['export_ok']} model_a_ready={result['model_a_ready']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
