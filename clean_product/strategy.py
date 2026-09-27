from __future__ import annotations

import pandas as pd


def top50_exit_one_worst_sell(signals: pd.DataFrame, previous: set[str] | None = None) -> pd.DataFrame:
    """Keep the top 50; sell only the weakest holding that left the top 50."""
    previous = previous or set()
    ranked = signals.sort_values(["rank", "instrument"]).reset_index(drop=True)
    top = set(ranked.head(50)["instrument"])
    sells = sorted(previous - top, key=lambda symbol: int(ranked.loc[ranked.instrument.eq(symbol), "rank"].iloc[0]) if symbol in set(ranked.instrument) else 10**9)
    sells = sells[-1:] if sells else []
    buys = [symbol for symbol in ranked.head(50)["instrument"] if symbol not in previous]
    return pd.DataFrame([*(dict(instrument=s, action="sell") for s in sells), *(dict(instrument=b, action="buy") for b in buys)])
