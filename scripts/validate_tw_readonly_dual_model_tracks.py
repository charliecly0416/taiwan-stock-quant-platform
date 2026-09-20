#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from tw_stock_workflow.dual_track import validate_track_bundle


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "data_tw/artifacts/readonly_model_strategy_comparison/v9"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate standard readonly model-track artifacts")
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.artifact_root.resolve()
    results = {}
    registry = yaml.safe_load(
        (ROOT / "configs/readonly_model_tracks.yaml").read_text(encoding="utf-8")
    )
    for track_id in registry["tracks"]:
        manifest = root / "artifacts" / track_id / "track_manifest.json"
        results[track_id] = validate_track_bundle(ROOT, manifest)
    pointer = json.loads((root / "latest.json").read_text(encoding="utf-8"))
    catalog = ROOT / pointer["catalog_path"]
    if not catalog.is_file():
        raise RuntimeError("comparison catalog is missing")
    payload = {
        "status": "PASS",
        "tracks": results,
        "catalog": str(catalog.relative_to(ROOT)),
        "readonly_only": True,
        "production_allowed": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
