from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = ROOT / "data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt"
CURRENT_SYMBOLS = ROOT / "data_tw/meta/tw_current_market_stock_symbols.csv"
DEFAULT_OUTPUT = ROOT / "data_tw/experiments/tw_non_ohlcv_source_inventory"
REPORT_PATH = ROOT / "docs/tw_audit/28_tw_non_ohlcv_source_inventory_report.md"

SOURCES: list[dict[str, str]] = [
    {
        "source_id": "twse_institutional_paid",
        "family": "institutional_flow",
        "exchange_scope": "TWSE",
        "url_type": "product_page",
        "url": "https://eshop.twse.com.tw/en/product/detail/6edec1b6e62345cb9f1244acbbcefae0",
        "priority": "P1_license_dependent",
    },
    {
        "source_id": "tpex_institutional_page",
        "family": "institutional_flow",
        "exchange_scope": "TPEX",
        "url_type": "report_page",
        "url": "https://www.tpex.org.tw/en-us/mainboard/trading/major-institutional/detail/day.html",
        "priority": "P1_endpoint_discovery",
    },
    {
        "source_id": "twse_daily_trading_open_data",
        "family": "daily_trading_qa",
        "exchange_scope": "TWSE",
        "url_type": "open_data_page",
        "url": "https://data.gov.tw/en/datasets/11549",
        "priority": "P3_qa_only",
    },
    {
        "source_id": "twse_margin_page",
        "family": "margin_short",
        "exchange_scope": "TWSE",
        "url_type": "report_page",
        "url": "https://www.twse.com.tw/en/exchangeReport/MI_MARGN",
        "priority": "P1_endpoint_discovery",
    },
    {
        "source_id": "twse_institutional_sample_json",
        "family": "institutional_flow",
        "exchange_scope": "TWSE",
        "url_type": "sample_json_endpoint",
        "url": "https://www.twse.com.tw/rwd/en/fund/T86?date=20240515&selectType=ALLBUT0999&response=json",
        "priority": "P1_sample_only",
    },
    {
        "source_id": "twse_margin_sample_json",
        "family": "margin_short",
        "exchange_scope": "TWSE",
        "url_type": "sample_json_endpoint",
        "url": "https://www.twse.com.tw/rwd/en/marginTrading/MI_MARGN?date=20240515&selectType=ALL&response=json",
        "priority": "P1_sample_only",
    },
    {
        "source_id": "tpex_margin_short_open_data",
        "family": "margin_short",
        "exchange_scope": "TPEX",
        "url_type": "open_data_page",
        "url": "https://data.gov.tw/en/datasets/17249",
        "priority": "P1_endpoint_discovery",
    },
    {
        "source_id": "tpex_margin_usage_page",
        "family": "margin_short",
        "exchange_scope": "TPEX",
        "url_type": "report_page",
        "url": "https://www.tpex.org.tw/en-us/mainboard/trading/margin-trading/usage/day.html",
        "priority": "P1_endpoint_discovery",
    },
    {
        "source_id": "tpex_short_sbl_page",
        "family": "margin_short",
        "exchange_scope": "TPEX",
        "url_type": "report_page",
        "url": "https://www.tpex.org.tw/web/stock/margin_trading/margin_sbl_10103/margin_sbl.php?l=en-us",
        "priority": "P1_endpoint_discovery",
    },
    {
        "source_id": "mops_portal",
        "family": "fundamentals",
        "exchange_scope": "TWSE_TPEX",
        "url_type": "portal_page",
        "url": "https://mops.twse.com.tw/mops/",
        "priority": "P2_point_in_time_required",
    },
    {
        "source_id": "twse_industry_rules",
        "family": "industry_classification",
        "exchange_scope": "TWSE",
        "url_type": "regulation_page",
        "url": "https://twse-regulation.twse.com.tw/ENG/EN/law/DAT0201.aspx?FLCODE=FL007104",
        "priority": "P2_endpoint_needed",
    },
]


def fetch_status(row: dict[str, str], timeout: int) -> dict[str, Any]:
    headers = {"User-Agent": "Mozilla/5.0 qlib-source-inventory/1.0"}
    out: dict[str, Any] = {**row, "verified_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        resp = requests.get(row["url"], timeout=timeout, headers=headers)
        out.update(
            {
                "http_status": int(resp.status_code),
                "final_url": resp.url,
                "content_type": resp.headers.get("content-type", ""),
                "content_length_chars": len(resp.text),
                "ok_2xx": bool(200 <= resp.status_code < 300),
                "error": "",
            }
        )
        ctype = resp.headers.get("content-type", "")
        if "json" in ctype.lower() or row["url"].endswith("response=json"):
            try:
                payload = resp.json()
                out["json_top_level_keys"] = ",".join(map(str, payload.keys())) if isinstance(payload, dict) else type(payload).__name__
                if isinstance(payload, dict):
                    fields = payload.get("fields") or payload.get("titles") or payload.get("fields1")
                    out["json_field_count"] = len(fields) if isinstance(fields, list) else ""
                    out["json_data_rows"] = len(payload.get("data", [])) if isinstance(payload.get("data"), list) else ""
            except Exception as exc:  # noqa: BLE001
                out["json_parse_error"] = repr(exc)
        return out
    except Exception as exc:  # noqa: BLE001
        out.update(
            {
                "http_status": "",
                "final_url": "",
                "content_type": "",
                "content_length_chars": "",
                "ok_2xx": False,
                "error": repr(exc),
            }
        )
        return out


def load_tw_liquid_symbols() -> tuple[pd.DataFrame, set[str]]:
    rows = []
    symbols: set[str] = set()
    with UNIVERSE_PATH.open() as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) != 3:
                continue
            symbol, start, end = parts
            rows.append({"qlib_symbol": symbol, "start": pd.Timestamp(start), "end": pd.Timestamp(end)})
            symbols.add(symbol)
    return pd.DataFrame(rows), symbols


def universe_exchange_coverage() -> tuple[pd.DataFrame, pd.DataFrame]:
    segments, symbols = load_tw_liquid_symbols()
    meta = pd.read_csv(CURRENT_SYMBOLS)
    meta["qlib_symbol"] = meta["qlib_symbol"].astype(str).str.upper()
    meta = meta.drop_duplicates("qlib_symbol")[["qlib_symbol", "exchange", "instrument_type", "source"]]

    unique = pd.DataFrame({"qlib_symbol": sorted(symbols)}).merge(meta, on="qlib_symbol", how="left")
    unique["exchange"] = unique["exchange"].fillna("UNKNOWN_NOT_IN_CURRENT_METADATA")

    rows = []
    for scope, frame in {
        "unique_ever_in_tw_liquid_dyn": unique,
        "active_on_2025_06_30": segments[(segments["start"] <= pd.Timestamp("2025-06-30")) & (segments["end"] >= pd.Timestamp("2025-06-30"))][["qlib_symbol"]].drop_duplicates().merge(meta, on="qlib_symbol", how="left"),
        "active_on_2026_05_21": segments[(segments["start"] <= pd.Timestamp("2026-05-21")) & (segments["end"] >= pd.Timestamp("2026-05-21"))][["qlib_symbol"]].drop_duplicates().merge(meta, on="qlib_symbol", how="left"),
    }.items():
        frame = frame.copy()
        frame["exchange"] = frame["exchange"].fillna("UNKNOWN_NOT_IN_CURRENT_METADATA")
        total = len(frame)
        for exchange, g in frame.groupby("exchange", dropna=False):
            rows.append({"scope": scope, "exchange": exchange, "symbols": int(len(g)), "share": float(len(g) / total) if total else 0.0})
    return pd.DataFrame(rows), unique.sort_values(["exchange", "qlib_symbol"])


def source_family_coverage() -> pd.DataFrame:
    coverage, _ = universe_exchange_coverage()
    active = coverage[coverage["scope"] == "active_on_2025_06_30"]
    counts = dict(zip(active["exchange"], active["symbols"]))
    total = int(active["symbols"].sum())
    rows = []
    for family, needed in {
        "institutional_flow": ["TWSE", "TPEX"],
        "margin_short": ["TWSE", "TPEX"],
        "market_cap_shares": ["TWSE", "TPEX"],
        "fundamentals_mops": ["TWSE", "TPEX"],
        "industry_classification": ["TWSE", "TPEX"],
    }.items():
        covered = sum(int(counts.get(x, 0)) for x in needed)
        rows.append(
            {
                "family": family,
                "required_exchange_sources": "+".join(needed),
                "active_2025_06_30_symbols_coverable_if_both_sources_exist": covered,
                "active_2025_06_30_total_symbols": total,
                "coverage_if_both_sources_exist": float(covered / total) if total else 0.0,
                "twse_only_coverage": float(counts.get("TWSE", 0) / total) if total else 0.0,
                "tpex_only_coverage": float(counts.get("TPEX", 0) / total) if total else 0.0,
                "decision_rule": "downgrade to P2 if either TWSE or TPEX endpoint cannot cover its side",
            }
        )
    return pd.DataFrame(rows)


def fmt(x: Any) -> str:
    if pd.isna(x):
        return ""
    if isinstance(x, float):
        return f"{x:.6f}"
    return str(x)


def table(df: pd.DataFrame, cols: list[str]) -> list[str]:
    d = df[cols].copy()
    for col in d.columns:
        d[col] = d[col].map(fmt)
    lines = ["| " + " | ".join(d.columns) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in d.to_numpy(dtype=str))
    return lines


def write_report(out_dir: Path, url_status: pd.DataFrame, coverage: pd.DataFrame, family: pd.DataFrame) -> None:
    lines = [
        "---",
        "created_at: 2026-05-28",
        "status: source_inventory_ready_for_audit",
        "scope: phase_d1_non_ohlcv_source_inventory",
        "related_docs:",
        "  - docs/tw_audit/26_tw_non_ohlcv_data_source_assessment.md",
        "  - docs/tw_audit/27_claude_audit_round_10_idio_skew60_ablation_and_data_assessment.md",
        "---",
        "",
        "# Phase D.1 Non-OHLCV Source Inventory",
        "",
        "## Scope",
        "",
        "This is a narrow source-inventory artifact. It verifies URL accessibility, records sample endpoint behavior, and measures TWSE/TPEx coverage using existing local metadata. It does not download production datasets, format new data, or compute factors.",
        "",
        "## URL Status",
        "",
    ]
    lines.extend(table(url_status, ["source_id", "family", "exchange_scope", "url_type", "http_status", "ok_2xx", "content_type", "content_length_chars", "error"]))
    lines += ["", "## Universe Exchange Coverage", ""]
    lines.extend(table(coverage, ["scope", "exchange", "symbols", "share"]))
    lines += ["", "## Family Coverage Rule", ""]
    lines.extend(table(family, ["family", "required_exchange_sources", "active_2025_06_30_symbols_coverable_if_both_sources_exist", "active_2025_06_30_total_symbols", "coverage_if_both_sources_exist", "twse_only_coverage", "tpex_only_coverage", "decision_rule"]))
    lines += [
        "",
        "## Findings",
        "",
        "- `tw_liquid_dyn` active membership requires both TWSE and TPEx source coverage; TWSE-only or TPEx-only data must be downgraded until the missing exchange side is solved.",
        "- TWSE Data E-Shop page is reachable but paid/licensed; it remains license-dependent.",
        "- TPEx public report pages may block direct scripted access from this environment; endpoint discovery must account for Cloudflare/browser requirements.",
        "- TWSE JSON sample endpoints timed out from this environment during inventory; retry strategy or alternative official endpoints must be validated before any production crawler work.",
        "- MOPS and data.gov pages are reachable enough for source discovery, but fundamentals still require point-in-time policy before use.",
        "",
        "## Next Audit Questions",
        "",
        "1. Should Phase D.1 continue with browser-assisted endpoint discovery for TWSE/TPEx P1 sources, given scripted access timeouts/403s?",
        "2. Should TWSE-only paid institutional-flow data remain P1 if TPEx equivalent access is unresolved?",
        "3. Is the current exchange coverage rule strict enough: downgrade any family to P2 unless both TWSE and TPEx sides are available?",
        "4. Should the next implementation target margin/short first, or institutional flow first?",
        "",
        "## Artifacts",
        "",
        f"- `{out_dir / 'url_status.csv'}`",
        f"- `{out_dir / 'tw_liquid_dyn_exchange_coverage.csv'}`",
        f"- `{out_dir / 'tw_liquid_dyn_symbol_exchange_map.csv'}`",
        f"- `{out_dir / 'source_family_coverage_rules.csv'}`",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory Taiwan non-OHLCV data sources without production ingestion.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT.relative_to(ROOT)))
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()

    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    url_status = pd.DataFrame([fetch_status(row, args.timeout) for row in SOURCES])
    coverage, symbol_map = universe_exchange_coverage()
    family = source_family_coverage()

    url_status.to_csv(out_dir / "url_status.csv", index=False)
    coverage.to_csv(out_dir / "tw_liquid_dyn_exchange_coverage.csv", index=False)
    symbol_map.to_csv(out_dir / "tw_liquid_dyn_symbol_exchange_map.csv", index=False)
    family.to_csv(out_dir / "source_family_coverage_rules.csv", index=False)
    write_report(out_dir.relative_to(ROOT), url_status, coverage, family)

    print(f"urls={url_status.shape[0]}")
    print(f"url_ok_2xx={int(url_status['ok_2xx'].sum())}")
    print(f"coverage_rows={coverage.shape[0]}")
    print(f"wrote {out_dir.relative_to(ROOT)}")
    print(f"wrote {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
