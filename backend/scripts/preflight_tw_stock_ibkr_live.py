#!/usr/bin/env python3
"""Preflight TWStock IBKR paper/live readiness without connecting to IBKR.

This script is a safety checklist, not an execution path. By default it only
checks local configuration, Agent token metadata, broker policy, and TWStock ->
IBKR contract mapping. It does not connect to TWS/Gateway and never submits
orders.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.broker_market_policy import allowed_market_types, is_compatible_credential, is_long_only_broker, validate_strategy_config  # noqa: E402
from app.services.ibkr_trading.symbols import normalize_symbol  # noqa: E402
from app.utils.agent_auth import _hash_token, parse_csv_list, parse_scopes  # noqa: E402
from app.utils.db import get_db_connection  # noqa: E402
from app.utils.local_brokers import local_desktop_brokers_allowed  # noqa: E402


def _check(name: str, ok: bool, severity: str, detail: str, remediation: str = "") -> Dict[str, Any]:
    return {"name": name, "ok": bool(ok), "severity": severity, "detail": detail, "remediation": remediation}


def _env_bool(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).strip().lower() in ("1", "true", "yes", "on")


def load_agent_token_row(agent_token: str = "") -> Dict[str, Any]:
    if not agent_token:
        return {}
    token_hash = _hash_token(agent_token)
    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(
            """
            SELECT id, user_id, name, scopes, markets, instruments,
                   paper_only, rate_limit_per_min, status, expires_at
            FROM qd_agent_tokens
            WHERE token_hash = %s
            """,
            (token_hash,),
        )
        row = cur.fetchone()
        cur.close()
    return dict(row or {})


def build_contract_checks(symbols: Sequence[str]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    for symbol in symbols:
        ib_symbol, exchange, currency = normalize_symbol(symbol, "TWStock")
        ok = bool(ib_symbol and exchange in ("TWSE", "TPEX") and currency == "TWD")
        checks.append(_check(
            name=f"contract_mapping:{symbol}",
            ok=ok,
            severity="error",
            detail=f"{symbol} -> symbol={ib_symbol or '<invalid>'}, exchange={exchange}, currency={currency}",
            remediation="Use TWSE:2330, 2330.TW, TPEX:6488, or 6488.TPEX style symbols.",
        ))
    return checks


def build_preflight_report(
    *,
    symbols: Sequence[str],
    agent_token_row: Optional[Dict[str, Any]] = None,
    require_live: bool = False,
    require_ibkr_env: bool = False,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    original_env = None
    if env is not None:
        original_env = os.environ.copy()
        os.environ.update(env)
    try:
        row = agent_token_row or {}
        checks: List[Dict[str, Any]] = []
        live_enabled = _env_bool("AGENT_LIVE_TRADING_ENABLED", "false")
        local_allowed = local_desktop_brokers_allowed()
        order_client_id_raw = os.getenv("IBKR_ORDER_CLIENT_ID", "7")
        try:
            order_client_id = int(order_client_id_raw)
            order_client_id_ok = order_client_id != 1
        except Exception:
            order_client_id_ok = False

        checks.append(_check(
            "broker_policy:ibkr_twstock_spot_long",
            is_compatible_credential("ibkr", "TWStock") and allowed_market_types("ibkr", "TWStock") == {"spot"} and is_long_only_broker("ibkr"),
            "error",
            "IBKR supports TWStock spot in policy; QuantDinger IBKR path is long-only.",
            "Update broker_market_policy.py only if execution support changes.",
        ))
        try:
            validate_strategy_config(exchange_id="ibkr", market_category="TWStock", market_type="spot", trade_direction="long", bot_type="trend")
            policy_ok = True
            policy_detail = "validate_strategy_config accepts IBKR + TWStock + spot + long + trend."
        except Exception as exc:
            policy_ok = False
            policy_detail = str(exc)
        checks.append(_check("strategy_config:ibkr_twstock_long", policy_ok, "error", policy_detail))
        checks.append(_check(
            "local_desktop_brokers_allowed",
            local_allowed,
            "error" if require_live else "warning",
            f"ALLOW_LOCAL_DESKTOP_BROKERS={os.getenv('ALLOW_LOCAL_DESKTOP_BROKERS', 'true')}.",
            "Set ALLOW_LOCAL_DESKTOP_BROKERS=true on a self-hosted machine that can reach TWS/Gateway.",
        ))
        checks.append(_check(
            "agent_live_kill_switch",
            live_enabled if require_live else not live_enabled,
            "error" if require_live else "warning",
            f"AGENT_LIVE_TRADING_ENABLED={os.getenv('AGENT_LIVE_TRADING_ENABLED', 'false')}; require_live={require_live}.",
            "For paper validation keep false. For live promotion, set true only after human approval.",
        ))
        checks.append(_check(
            "ibkr_order_client_id",
            order_client_id_ok,
            "warning",
            f"IBKR_ORDER_CLIENT_ID={order_client_id_raw}; recommended non-1 value, default 7.",
            "Use a clientId different from the manual /api/ibkr UI session; prefer 7.",
        ))
        if require_ibkr_env:
            host = os.getenv("IBKR_HOST") or os.getenv("IBKR_TWS_HOST") or ""
            port = os.getenv("IBKR_PORT") or os.getenv("IBKR_TWS_PORT") or ""
            checks.append(_check("ibkr_env_host", bool(host), "error", f"IBKR host env present={bool(host)}.", "Set IBKR_HOST or configure credentials ibkr_host."))
            checks.append(_check("ibkr_env_port", bool(port), "error", f"IBKR port env present={bool(port)}.", "Set IBKR_PORT or configure credentials ibkr_port, usually 7497 for paper."))
        if row:
            scopes = parse_scopes(row.get("scopes"))
            markets = parse_csv_list(row.get("markets"), default="*")
            status = str(row.get("status") or "").lower()
            paper_only = bool(row.get("paper_only", True))
            checks.append(_check("agent_token:status_active", status == "active", "error", f"status={status}"))
            checks.append(_check("agent_token:has_R_scope", "R" in scopes, "error", f"scopes={sorted(scopes)}"))
            checks.append(_check("agent_token:has_T_scope", "T" in scopes, "error", f"scopes={sorted(scopes)}"))
            checks.append(_check("agent_token:twstock_allowed", "*" in markets or any(m.upper() == "TWSTOCK" for m in markets), "error", f"markets={markets}"))
            checks.append(_check(
                "agent_token:paper_only_mode",
                (not paper_only) if require_live else paper_only,
                "error" if require_live else "info",
                f"paper_only={paper_only}; require_live={require_live}.",
                "Paper smoke requires paper_only=true. Live requires explicit paper_only=false after approval.",
            ))
        else:
            checks.append(_check("agent_token:provided", not require_live, "error" if require_live else "warning", "No token row provided; token-scoped checks skipped."))
        checks.extend(build_contract_checks(symbols))
        errors = [item for item in checks if item["severity"] == "error" and not item["ok"]]
        warnings = [item for item in checks if item["severity"] == "warning" and not item["ok"]]
        status = "pass" if not errors and not warnings else "warning" if not errors else "fail"
        return {
            "market": "TWStock",
            "broker": "ibkr",
            "paper_only_preflight": not require_live,
            "connects_to_ibkr": False,
            "submits_orders": False,
            "require_live": bool(require_live),
            "status": status,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "checks": checks,
            "manual_approval_required_for_live": True,
            "live_promotion_red_lines": [
                "Do not enable live if any error check fails.",
                "Do not use an Agent token with paper_only=false without explicit operator approval.",
                "Do not use clientId=1 for strategy/order workers; reserve it for manual UI sessions.",
                "Do not trade TPEX symbols until official TPEx data validation is available or manually reconciled.",
            ],
        }
    finally:
        if original_env is not None:
            os.environ.clear()
            os.environ.update(original_env)


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# TWStock IBKR Paper/Live Preflight",
        "",
        f"- Status: {report.get('status')}",
        f"- Market: {report.get('market')}",
        f"- Broker: {report.get('broker')}",
        f"- Connects to IBKR: {report.get('connects_to_ibkr')}",
        f"- Submits orders: {report.get('submits_orders')}",
        f"- Require live: {report.get('require_live')}",
        "",
        "## Checks",
    ]
    for item in report.get("checks") or []:
        mark = "PASS" if item.get("ok") else item.get("severity", "check").upper()
        lines.append(f"- {mark}: {item.get('name')} - {item.get('detail')}")
        if item.get("remediation") and not item.get("ok"):
            lines.append(f"  Remediation: {item.get('remediation')}")
    lines.extend(["", "## Live Red Lines"])
    for item in report.get("live_promotion_red_lines") or []:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def _write_json(path: str, payload: Dict[str, Any]) -> None:
    if path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: str, text: str) -> None:
    if path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preflight TWStock IBKR paper/live readiness without connecting to IBKR.")
    parser.add_argument("--symbol", action="append", default=[], help="TWStock symbol to validate; may be repeated or comma-separated.")
    parser.add_argument("--agent-token", default="", help="Optional Agent token for scoped paper/live checks.")
    parser.add_argument("--require-live", action="store_true", help="Evaluate live-promotion gates instead of paper-safe gates.")
    parser.add_argument("--require-ibkr-env", action="store_true", help="Require IBKR_HOST/IBKR_PORT-style env vars. Does not connect.")
    parser.add_argument("--output-json", default="")
    parser.add_argument("--output-md", default="")
    return parser


def _parse_symbols(raw_items: Sequence[str]) -> List[str]:
    out: List[str] = []
    for item in raw_items:
        out.extend([part.strip() for part in str(item).split(",") if part.strip()])
    return out or ["2330", "0050", "TPEX:6488"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    row = load_agent_token_row(args.agent_token) if args.agent_token else {}
    report = build_preflight_report(
        symbols=_parse_symbols(args.symbol),
        agent_token_row=row,
        require_live=args.require_live,
        require_ibkr_env=args.require_ibkr_env,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    _write_json(args.output_json, report)
    if args.output_md:
        _write_text(args.output_md, render_markdown(report))
    return 0 if report.get("status") in ("pass", "warning") else 1


if __name__ == "__main__":
    raise SystemExit(main())
