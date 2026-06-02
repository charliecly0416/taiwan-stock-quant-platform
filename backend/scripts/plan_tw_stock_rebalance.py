#!/usr/bin/env python3
"""Create a target rebalance plan from TWStock cross-sectional rankings.

Phase 3 starts with a research-safe target planner: it does not place orders and
it does not require account state. It converts ranked symbols into target
portfolio weights that can later feed paper/live execution.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "plan-tw-stock-rebalance")
os.environ.setdefault("ADMIN_USER", "rebalance")
os.environ.setdefault("ADMIN_PASSWORD", "rebalancepass")

from app.data_sources.tw_stock import TWStockDataSource  # noqa: E402


@dataclass(frozen=True)
class TargetPosition:
    symbol: str
    config_symbol: str
    target_weight: float
    rank: int
    score: float
    side: str
    reason: str


def _normalize_config_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip()
    if raw.upper().startswith("TWSTOCK:"):
        raw = raw.split(":", 1)[1]
    norm = TWStockDataSource.normalize_symbol(raw).symbol
    return f"TWStock:{norm}" if norm else ""


def _plain_symbol(config_symbol: str) -> str:
    normalized = _normalize_config_symbol(config_symbol)
    return normalized.split(":", 1)[1] if ":" in normalized else normalized


def parse_ranked_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = payload.get("items") or []
    if isinstance(items, list) and items:
        out = []
        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            config_symbol = _normalize_config_symbol(item.get("config_symbol") or item.get("symbol"))
            if not config_symbol:
                continue
            reasons = item.get("reasons") or []
            if reasons:
                continue
            out.append({
                "config_symbol": config_symbol,
                "symbol": _plain_symbol(config_symbol),
                "rank": int(item.get("rank") or idx),
                "score": float(item.get("composite_score") or item.get("score") or 0),
            })
        out.sort(key=lambda item: item["rank"])
        return out

    rankings = payload.get("rankings") or payload.get("symbol_list") or []
    out = []
    if isinstance(rankings, list):
        for idx, raw in enumerate(rankings, start=1):
            config_symbol = _normalize_config_symbol(raw)
            if config_symbol:
                out.append({
                    "config_symbol": config_symbol,
                    "symbol": _plain_symbol(config_symbol),
                    "rank": idx,
                    "score": 0.0,
                })
    return out


def build_rebalance_plan(
    ranked_items: Sequence[Dict[str, Any]],
    *,
    top_n: int = 5,
    max_weight: float = 0.25,
    cash_weight: float = 0.0,
    weighting: str = "equal",
    as_of: str = "",
) -> Dict[str, Any]:
    usable = list(ranked_items)
    selected = usable[: max(int(top_n or 0), 0)]
    if not selected:
        return {
            "as_of": as_of or date.today().isoformat(),
            "top_n": top_n,
            "weighting": weighting,
            "cash_weight": cash_weight,
            "selected_count": 0,
            "target_positions": [],
            "warnings": ["no_ranked_symbols"],
        }
    warnings: List[str] = []
    cash = max(min(float(cash_weight or 0), 1.0), 0.0)
    investable = max(1.0 - cash, 0.0)
    max_w = max(min(float(max_weight or 1.0), 1.0), 0.0)
    if weighting != "equal":
        warnings.append("unsupported_weighting_fallback_equal")
        weighting = "equal"
    raw_weight = investable / len(selected) if selected else 0.0
    target_weight = min(raw_weight, max_w) if max_w > 0 else raw_weight
    if target_weight * len(selected) < investable - 1e-9:
        warnings.append("max_weight_leaves_extra_cash")
    positions = [
        TargetPosition(
            symbol=str(item["symbol"]),
            config_symbol=str(item["config_symbol"]),
            target_weight=round(target_weight, 8),
            rank=int(item["rank"]),
            score=float(item.get("score") or 0),
            side="long",
            reason="top_ranked_equal_weight",
        )
        for item in selected
    ]
    allocated = round(sum(item.target_weight for item in positions), 8)
    return {
        "as_of": as_of or date.today().isoformat(),
        "top_n": int(top_n),
        "weighting": weighting,
        "cash_weight": round(cash, 8),
        "max_weight": round(max_w, 8),
        "selected_count": len(positions),
        "allocated_weight": allocated,
        "residual_cash_weight": round(1.0 - allocated, 8),
        "target_positions": [asdict(item) for item in positions],
        "warnings": warnings,
    }


def load_ranking_json(path: str) -> Dict[str, Any]:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan TWStock target rebalance weights from rankings.")
    parser.add_argument("--ranking-json", required=True, help="JSON output from rank_tw_stock_universe.py.")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--max-weight", type=float, default=0.25)
    parser.add_argument("--cash-weight", type=float, default=0.0)
    parser.add_argument("--weighting", default="equal", choices=("equal",))
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--output-json", default="", help="Optional output JSON path.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    payload = load_ranking_json(args.ranking_json)
    ranked = parse_ranked_items(payload)
    plan = build_rebalance_plan(
        ranked,
        top_n=args.top_n,
        max_weight=args.max_weight,
        cash_weight=args.cash_weight,
        weighting=args.weighting,
        as_of=args.as_of,
    )
    text = json.dumps(plan, ensure_ascii=False, indent=2)
    print(text)
    if args.output_json:
        path = Path(args.output_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    return 0 if plan.get("selected_count", 0) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
