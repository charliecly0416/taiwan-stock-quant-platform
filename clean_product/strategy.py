from __future__ import annotations

import pandas as pd


def top50_exit_one_worst_sell(signals: pd.DataFrame, previous: set[str] | None = None, *, max_positions: int = 50, full_ranks: dict[str, int] | None = None) -> pd.DataFrame:
    """Keep Top50; sell at most one fallen holding and buy one replacement."""
    previous = previous or set()
    ranked = signals.sort_values(["rank", "instrument"]).reset_index(drop=True)
    rank_field = "full_qlib_rank" if "full_qlib_rank" in ranked else "rank"
    rank_map = full_ranks or dict(zip(ranked.instrument.astype(str), ranked[rank_field].astype(int)))
    candidates = ranked[ranked.candidate_rank.le(50)] if "candidate_rank" in ranked else ranked.head(50)
    top = candidates.instrument.astype(str).tolist()
    fallen = sorted((symbol for symbol in previous if symbol not in set(top)),
                    key=lambda symbol: (-rank_map.get(symbol, 10**9), symbol))
    sells = fallen[:1]
    remaining = previous - set(sells)
    available_slots = max(0, max_positions - len(remaining))
    buys = [symbol for symbol in top if symbol not in remaining][: min(1 if previous else max_positions, available_slots)]
    rows = [
        *({"instrument": symbol, "action": "sell", "reason": "fell_out_of_top50"} for symbol in sells),
        *({"instrument": symbol, "action": "buy", "reason": "highest_ranked_available"} for symbol in buys),
    ]
    return pd.DataFrame(rows, columns=["instrument", "action", "reason"])
