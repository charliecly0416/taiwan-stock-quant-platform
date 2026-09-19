#!/usr/bin/env python3
"""Capture official 2026-09-16 opens and settle the 2026-09-14 B8 shadow."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
PARTIAL = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b8_prospective_shadow_20260914/settlement_20260915"
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b16_b8_prospective_settlement_20260916"
SOURCE_ORDERS = PARTIAL / "entry_orders_pending_settlement.csv"
SOURCE_MANIFEST = PARTIAL / "manifest.json"
URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
EXIT_DATE = "2026-09-16"
FEE = 0.001425
TAX = 0.003
LOT = 10
INITIAL = 1_000_000.0
TARGET = 10
PROTECTED = [
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def fingerprints() -> dict[str, str | None]:
    return {rel(path): sha(path) for path in PROTECTED}


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def capture(symbols: list[str]) -> tuple[pd.DataFrame, dict[str, object]]:
    channels = []
    for symbol in symbols:
        code = symbol.removeprefix("TW")
        channels.extend((f"tse_{code}.tw", f"otc_{code}.tw"))
    params = {"ex_ch": "|".join(channels), "json": "1", "delay": "0"}
    fetched_at = now()
    response = requests.get(
        URL,
        params=params,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 modelb-b16-readonly-settlement"},
    )
    raw_path = OUT / "twse_mis_exit_open.raw"
    raw_path.write_bytes(response.content)
    response.raise_for_status()
    payload = response.json()
    rows = []
    for item in payload.get("msgArray", []):
        code = str(item.get("c") or "").strip()
        day = str(item.get("d") or "").strip()
        try:
            open_price = float(item.get("o"))
        except (TypeError, ValueError):
            continue
        symbol = f"TW{code}" if code else ""
        if symbol in symbols and day == EXIT_DATE.replace("-", "") and math.isfinite(open_price) and open_price > 0:
            rows.append({
                "instrument": symbol,
                "exit_date": EXIT_DATE,
                "exit_open": open_price,
                "exchange": str(item.get("ex") or ""),
                "source_key": str(item.get("key") or ""),
                "source_quote_time": str(item.get("t") or item.get("%") or ""),
                "source_date": day,
                "source": "TWSE_MIS_OFFICIAL",
                "fetched_at": fetched_at,
            })
    frame = pd.DataFrame(rows).drop_duplicates("instrument", keep="last").sort_values("instrument")
    audit = {
        "source": "TWSE_MIS_OFFICIAL",
        "url": URL,
        "host": urlparse(URL).hostname,
        "method": "GET",
        "params": {"ex_ch_count": len(channels), "json": "1", "delay": "0"},
        "requested_symbols": symbols,
        "requested_symbol_count": len(symbols),
        "response_http_status": response.status_code,
        "response_rtcode": payload.get("rtcode"),
        "query_time": payload.get("queryTime", {}),
        "fetched_at": fetched_at,
        "accepted_date": EXIT_DATE,
        "accepted_symbol_count": int(frame.instrument.nunique()) if not frame.empty else 0,
        "raw_path": rel(raw_path),
        "raw_sha256": sha(raw_path),
    }
    return frame, audit


def settle(orders: pd.DataFrame, opens: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_symbol = opens.set_index("instrument").exit_open.to_dict()
    actions = []
    summaries = []
    for method, group in orders.groupby("method", sort=True):
        cash = INITIAL
        total_commission = total_tax = traded = 0.0
        filled = zero = 0
        for row in group.sort_values("selection_rank").itertuples(index=False):
            entry = float(row.entry_open)
            exit_open = float(by_symbol[row.instrument])
            quantity = int((INITIAL / TARGET / entry) // LOT) * LOT
            buy_notional = quantity * entry
            sell_notional = quantity * exit_open
            buy_commission = buy_notional * FEE
            sell_commission = sell_notional * FEE
            sell_tax = sell_notional * TAX
            if quantity > 0 and buy_notional + buy_commission <= cash + 1e-9:
                cash -= buy_notional + buy_commission
                cash += sell_notional - sell_commission - sell_tax
                filled += 1
            else:
                quantity = 0
                buy_notional = sell_notional = buy_commission = sell_commission = sell_tax = 0.0
                zero += 1
            net_pnl = sell_notional - buy_notional - buy_commission - sell_commission - sell_tax
            total_commission += buy_commission + sell_commission
            total_tax += sell_tax
            traded += buy_notional + sell_notional
            actions.append({
                "method": method,
                "signal_date": row.signal_date,
                "entry_date": row.entry_date,
                "exit_date": EXIT_DATE,
                "instrument": row.instrument,
                "selection_rank": int(row.selection_rank),
                "quantity": quantity,
                "entry_open": entry,
                "exit_open": exit_open,
                "buy_commission": buy_commission,
                "sell_commission": sell_commission,
                "sell_tax": sell_tax,
                "total_cost": buy_commission + sell_commission + sell_tax,
                "net_pnl": net_pnl,
                "gross_return": exit_open / entry - 1.0,
                "settlement_status": "SETTLED" if quantity > 0 else "SETTLED_ZERO_QUANTITY",
            })
        net_pnl = cash - INITIAL
        summaries.append({
            "method": method,
            "signal_date": str(group.signal_date.iloc[0]),
            "entry_date": str(group.entry_date.iloc[0]),
            "exit_date": EXIT_DATE,
            "selected_count": int(len(group)),
            "filled_positions": filled,
            "zero_quantity_positions": zero,
            "initial_equity": INITIAL,
            "final_equity": cash,
            "net_pnl": net_pnl,
            "net_return": net_pnl / INITIAL,
            "commission": total_commission,
            "sell_tax": total_tax,
            "total_cost": total_commission + total_tax,
            "turnover_notional": traded,
            "settled_oos_day": True,
        })
    return pd.DataFrame(actions), pd.DataFrame(summaries)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    before = fingerprints()
    partial_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    if partial_manifest.get("status") != "PENDING_EXIT_OPEN":
        raise RuntimeError("B8 partial settlement is not pending exit open")
    orders = pd.read_csv(SOURCE_ORDERS, dtype={"instrument": str})
    symbols = sorted(set(orders.instrument.astype(str)))
    if len(orders) != 20 or len(symbols) != 19 or set(orders.method) != {"A_ONLY", "A_PLUS_B"}:
        raise RuntimeError("unexpected B8 pending order scope")
    opens, request_audit = capture(symbols)
    opens.to_csv(OUT / "exit_open_coverage.csv", index=False)
    write_json(OUT / "request_audit.json", request_audit)
    missing = sorted(set(symbols) - set(opens.instrument))
    if missing:
        raise RuntimeError(f"official exit-open coverage incomplete: {missing}")
    actions, metrics = settle(orders, opens)
    actions.to_csv(OUT / "settled_actions.csv", index=False)
    metrics.to_csv(OUT / "paired_metrics.csv", index=False)
    control = metrics.set_index("method").loc["A_ONLY"]
    treatment = metrics.set_index("method").loc["A_PLUS_B"]
    after = fingerprints()
    relative = {
        "net_return_diff_b_minus_a": float(treatment.net_return - control.net_return),
        "net_pnl_diff_b_minus_a": float(treatment.net_pnl - control.net_pnl),
        "cost_diff_b_minus_a": float(treatment.total_cost - control.total_cost),
    }
    checks = {
        "upstream_pending_exit_open": True,
        "pending_rows_20": len(orders) == 20,
        "unique_symbols_19": len(symbols) == 19,
        "official_host": request_audit["host"] == "mis.twse.com.tw",
        "source_date_exact": set(opens.exit_date) == {EXIT_DATE},
        "positive_exit_open_19_of_19": len(opens) == 19 and bool((opens.exit_open > 0).all()),
        "methods_exact": set(metrics.method) == {"A_ONLY", "A_PLUS_B"},
        "row_accounting_exact": bool((actions.net_pnl - (actions.quantity * actions.exit_open - actions.quantity * actions.entry_open - actions.buy_commission - actions.sell_commission - actions.sell_tax)).abs().max() < 1e-8),
        "protected_unchanged": before == after,
        "no_production_write": True,
    }
    validator = {"schema_version": "modelb.b16.b8_settlement.validator.v1", "checks": checks, "verdict": "PASS" if all(checks.values()) else "FAIL"}
    manifest = {
        "schema_version": "modelb.b16.b8_prospective_settlement.manifest.v1",
        "run_id": "modelb_b16_b8_prospective_settlement_20260916",
        "status": "SETTLED_PROSPECTIVE_PAIRED_DAY",
        "signal_date": "2026-09-14",
        "entry_date": "2026-09-15",
        "exit_date": EXIT_DATE,
        "settled_oos_day": True,
        "settled_oos_days_added": 1,
        "prospective_paired_day_count_after": 1,
        "warmup_gate": "SANITY_ONLY_0_TO_19",
        "mb2_eligible": False,
        "baseline_admission": False,
        "production_allowed": False,
        "execution_contract": {"target_holdings": TARGET, "initial_equity": INITIAL, "lot_size": LOT, "buy_commission_rate": FEE, "sell_commission_rate": FEE, "sell_tax_rate": TAX, "entry": "2026-09-15 next_open", "exit": "2026-09-16 following_trading_day_open"},
        "source": request_audit,
        "upstream": {"partial_manifest": {"path": rel(SOURCE_MANIFEST), "sha256": sha(SOURCE_MANIFEST)}, "pending_orders": {"path": rel(SOURCE_ORDERS), "sha256": sha(SOURCE_ORDERS)}},
        "files": {"raw": request_audit["raw_path"], "exit_open_coverage": "exit_open_coverage.csv", "actions": "settled_actions.csv", "metrics": "paired_metrics.csv", "request_audit": "request_audit.json"},
        "metrics": metrics.to_dict("records"),
        "relative": relative,
        "protected_before": before,
        "protected_after": after,
        "protected_unchanged": before == after,
        "research_only": True,
        "no_training_or_scoring": True,
        "no_provider_publish_or_latest_switch": True,
        "no_database_or_broker_order": True,
        "conclusion_limit": "One settled prospective paired day is a sanity check only; it cannot support MB-2, effectiveness, or baseline admission.",
    }
    write_json(OUT / "B16_VALIDATOR.json", validator)
    write_json(OUT / "B16_MANIFEST.json", manifest)
    (OUT / "B16_EXECUTION_REPORT_CN.md").write_text(
        "# B16 B8 prospective 结算\n\n"
        f"- 9/16 官方 TWSE MIS 开盘价覆盖：`{len(opens)}/19`。\n"
        f"- A-only 净收益：`{float(control.net_return):.8%}`；A+B 净收益：`{float(treatment.net_return):.8%}`；差值：`{relative['net_return_diff_b_minus_a']:.8%}`。\n"
        "- 这是第 1 个 settled prospective paired day，只能作为 0-19 日 sanity check；不进入 MB-2 或 baseline。\n"
        "- 未修改 provider/latest/default/baseline/database/broker。\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": manifest["status"], "coverage": len(opens), "metrics": manifest["metrics"], "relative": relative, "validator": validator["verdict"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
