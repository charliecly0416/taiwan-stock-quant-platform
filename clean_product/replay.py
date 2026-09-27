from __future__ import annotations

import pandas as pd

from .models import ModelRunner


def replay(config: dict, prices: pd.DataFrame, model_name: str, start: str, end: str) -> dict:
    days = sorted(d for d in prices["date"].astype(str).unique() if start <= d <= end)
    runner = ModelRunner(config)
    rows = []
    for day in days:
        result = runner.run(model_name, prices, day)
        top = result.rows.head(50)
        rows.append({"date": day, "top_count": len(top), "top_symbol": str(top.iloc[0]["instrument"]) if len(top) else ""})
    history = pd.DataFrame(rows)
    return {"model": model_name, "start": start, "end": end, "days": len(days), "rows": history.to_dict("records"), "status": "READY"}
