from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "product.yaml"


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    endpoint: str
    date_field: str
    symbols_field: str = "stock_id"
    fields: tuple[str, ...] = ()
    lag_days: int = 0
    source: str = "finmind"
    required: tuple[str, ...] = ()
    numeric: tuple[str, ...] = ()
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelSpec:
    name: str
    role: str
    stages: tuple[str, ...]
    production_allowed: bool


def load_config(path: Path = CONFIG_PATH) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("product config must be a mapping")
    return payload


def datasets(config: dict) -> dict[str, DatasetSpec]:
    return {
        name: DatasetSpec(
            name=name,
            endpoint=str(item["endpoint"]),
            date_field=str(item.get("date_field", "date")),
            symbols_field=str(item.get("symbols_field", "stock_id")),
            fields=tuple(item.get("fields", ())),
            lag_days=int(item.get("lag_days", 0)),
            source=str(item.get("source", "finmind")),
            required=tuple(item.get("required", ())),
            numeric=tuple(item.get("numeric", ())),
            params=dict(item.get("params", {})),
        )
        for name, item in (config.get("datasets") or {}).items()
    }


def models(config: dict) -> dict[str, ModelSpec]:
    return {
        name: ModelSpec(
            name=name,
            role=str(item.get("role", "shadow")),
            stages=tuple(item.get("stages", ())),
            production_allowed=bool(item.get("production_allowed", False)),
        )
        for name, item in (config.get("models") or {}).items()
    }


def path(value: str | Path) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else ROOT / candidate


def env_config(config: dict) -> dict:
    result = dict(config)
    result["data_root"] = path(os.getenv("TW_PRODUCT_DATA_ROOT", result.get("data_root", "data_tw/product")))
    result["artifact_root"] = path(os.getenv("TW_PRODUCT_ARTIFACT_ROOT", result.get("artifact_root", "data_tw/product/artifacts")))
    return result
