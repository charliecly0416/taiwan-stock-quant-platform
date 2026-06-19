"""Central product artifact registry for TW stock readonly modules."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "configs/tw_product_artifact_registry.yaml"


class ArtifactRegistryError(Exception):
    """Raised when the product artifact registry is missing or malformed."""


@lru_cache(maxsize=1)
def load_product_artifact_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        raise ArtifactRegistryError(f"Missing product artifact registry: {REGISTRY_PATH}")
    payload = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != "tw_product_artifact_registry_v1":
        raise ArtifactRegistryError("Unsupported product artifact registry schema_version")
    return payload


def registry_get(*keys: str, default: Any = None) -> Any:
    node: Any = load_product_artifact_registry()
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def registry_path(*keys: str) -> Path:
    value = registry_get(*keys)
    if not isinstance(value, str) or not value.strip():
        raise ArtifactRegistryError(f"Missing registry path: {'.'.join(keys)}")
    path = Path(value)
    return path if path.is_absolute() else ROOT / path
