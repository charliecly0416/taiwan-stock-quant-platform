from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
import json
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
    history_days: int = 365
    source: str = "finmind"
    required: tuple[str, ...] = ()
    numeric: tuple[str, ...] = ()
    params: dict[str, Any] = field(default_factory=dict)
    primary_key: tuple[str, ...] = ()


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
            history_days=int(item.get("history_days", 365)),
            source=str(item.get("source", "finmind")),
            required=tuple(item.get("required", ())),
            numeric=tuple(item.get("numeric", ())),
            params=dict(item.get("params", {})),
            primary_key=tuple(item.get("primary_key", ())),
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


def trading_days(config: dict) -> list[str]:
    provider = config.get("model_stages", {}).get("model_a_frozen", {}).get("provider_uri")
    if not provider:
        return []
    calendar = path(provider) / "calendars" / "day.txt"
    return [line.strip()[:10] for line in calendar.read_text(encoding="utf-8").splitlines() if line.strip()] if calendar.exists() else []


def universe(config: dict) -> list[str]:
    values = [str(item).strip() for item in config.get("universe", []) if str(item).strip()]
    source = config.get("universe_file")
    if source:
        target = path(source)
        if target.exists():
            values = [line.split()[0].strip() for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    return sorted(dict.fromkeys(values))


def env_config(config: dict) -> dict:
    result = deepcopy(config)
    if result.get("_runtime_resolved"):
        return result
    result["data_root"] = path(os.getenv("TW_PRODUCT_DATA_ROOT", result.get("data_root", "data_tw/product")))
    result["artifact_root"] = path(os.getenv("TW_PRODUCT_ARTIFACT_ROOT", result.get("artifact_root", "data_tw/product/artifacts")))
    store = result["artifact_root"]
    result["_artifact_store"] = store
    active = store / "active.json"
    if active.is_file():
        release = json.loads(active.read_text())
        root = path(release["artifact_root"]).resolve()
        if release.get("schema_version") != "tw.clean.release.v1" or not root.is_relative_to((store / "releases").resolve()):
            raise ValueError("ACTIVE_RELEASE_INVALID")
        result["artifact_root"] = root
        result["data_root"] = root / "data"
        result.setdefault("agent", {})["prompt_root"] = str(root / "agent_daily_prompt")
        provider = release.get("provider")
        if provider:
            stage = result["model_stages"]["model_a_frozen"]
            stage.update(provider_uri=provider, selection_prices=release["selection_prices"],
                         selection_universe=release["universe_file"])
            result["universe_file"] = release.get("config_universe_file", release["universe_file"])
            result["datasets"]["prices"].setdefault("params", {})["provider_uri"] = provider
            result.setdefault("provider_refresh", {})["source_dir"] = release["selection_prices"]
            shadow_delta = release.get("shadow_feature_delta")
            if shadow_delta:
                result["model_stages"].setdefault("b19r2r_frozen", {}).update(
                    feature_delta=shadow_delta,
                    feature_delta_sha256=release.get("shadow_feature_delta_sha256"),
                )
        result["_active_release"] = release
        # Invalid research state must never make Model A unavailable.
        pointer = store / "shadow_active.json"
        try:
            shadow = json.loads(pointer.read_text()) if pointer.is_file() else {}
            if shadow.get("source_run_id") == release.get("run_id") and shadow.get("asof") == release.get("asof"):
                shadow_root = path(shadow["artifact_root"]).resolve()
                delta = shadow["feature_artifact"]
                if shadow.get("status") != "READY" or not shadow_root.is_relative_to((store / "shadow").resolve()) or not path(delta["path"]).resolve().is_relative_to(shadow_root):
                    raise ValueError("SHADOW_RELEASE_INVALID")
                result["_shadow_root"] = shadow_root
                result["model_stages"]["b19r2r_frozen"].update(feature_delta=delta["path"], feature_delta_sha256=delta["sha256"])
        except (ValueError, OSError, KeyError, TypeError):
            result["_shadow_error"] = "SHADOW_RELEASE_INVALID"
    result["_runtime_resolved"] = True
    return result
