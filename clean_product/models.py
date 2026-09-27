from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from .config import env_config


@dataclass
class SignalResult:
    model: str
    asof: str
    rows: pd.DataFrame
    status: str = "READY"


class StageRegistry:
    def __init__(self) -> None:
        self._stages: dict[str, Callable[..., pd.DataFrame]] = {}

    def register(self, name: str, fn: Callable[..., pd.DataFrame]) -> None:
        self._stages[name] = fn

    def run(self, name: str, frame: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
        try:
            fn = self._stages[name]
        except KeyError as exc:
            raise ValueError(f"unknown model stage: {name}") from exc
        return fn(frame, **kwargs)


def _model_a_score(frame: pd.DataFrame, asof: str, **_: Any) -> pd.DataFrame:
    """Portable baseline scorer. Uses frozen score when present, else momentum."""
    data = frame.copy()
    data["date"] = data["date"].astype(str)
    data = data[data["date"] == asof].copy()
    if data.empty:
        raise ValueError(f"no price rows for {asof}")
    if "score" not in data:
        data["score"] = pd.to_numeric(data.get("close"), errors="coerce").fillna(0.0)
    data["score"] = pd.to_numeric(data["score"], errors="coerce").fillna(0.0)
    data = data.sort_values(["score", "instrument"], ascending=[False, True]).reset_index(drop=True)
    data["rank"] = np.arange(1, len(data) + 1)
    return data[["date", "instrument", "score", "rank"]]


def _model_b_rerank(frame: pd.DataFrame, prices: pd.DataFrame | None = None, **_: Any) -> pd.DataFrame:
    data = frame.copy()
    if prices is not None and not prices.empty:
        extra = prices.copy()
        if "instrument" not in extra and "stock_id" in extra:
            extra = extra.rename(columns={"stock_id": "instrument"})
        extra["date"] = extra["date"].astype(str)
        extra = extra.sort_values(["instrument", "date"])
        extra["momentum"] = extra.groupby("instrument")["close"].pct_change(5)
        latest = extra.groupby("instrument", as_index=False).tail(1)[["instrument", "momentum"]]
        data = data.merge(latest, on="instrument", how="left")
        data["momentum"] = pd.to_numeric(data["momentum"], errors="coerce").fillna(0.0)
        data["score"] = data["score"] + data["momentum"] * 0.01
    data = data.sort_values(["score", "instrument"], ascending=[False, True]).reset_index(drop=True)
    data["rank"] = np.arange(1, len(data) + 1)
    return data[["date", "instrument", "score", "rank"]]


class ModelRunner:
    """Runs any registered model as the same stage pipeline."""

    def __init__(self, config: dict):
        self.config = env_config(config)
        self.stages = StageRegistry()
        self.stages.register("model_a_score", _model_a_score)
        self.stages.register("model_b_rerank", _model_b_rerank)

    def run(self, model_name: str, prices: pd.DataFrame, asof: str) -> SignalResult:
        spec = (self.config.get("models") or {}).get(model_name)
        if not spec:
            raise ValueError(f"unknown model: {model_name}")
        frame = prices.rename(columns={"stock_id": "instrument"}).copy()
        if "instrument" in prices and "stock_id" in prices:
            frame = prices.drop(columns=["stock_id"]).copy()
        for stage in spec.get("stages", []):
            frame = self.stages.run(stage, frame, asof=asof, prices=prices)
        output = self.config.get("artifact_root") / "signals" / model_name / asof
        output.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output / "signals.csv", index=False)
        (output / "manifest.json").write_text(json.dumps({"model": model_name, "role": spec.get("role"), "asof": asof, "status": "READY", "production_allowed": bool(spec.get("production_allowed"))}, indent=2) + "\n", encoding="utf-8")
        return SignalResult(model_name, asof, frame)
