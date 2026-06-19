#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "data_tw/artifacts/readonly_replay_windows/d7"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checksum_items(paths: list[Path]) -> list[dict[str, Any]]:
    rows = []
    seen: set[Path] = set()
    for path in paths:
        if not path.exists():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        rows.append({"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    return rows


def build_index(*, out_dir: Path) -> dict[str, Any]:
    d4_manifest = resolve("data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json")
    d4_index = load_json(d4_manifest)
    d6_manifest = resolve("data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json")
    d6_payload = load_json(d6_manifest)
    manifest = {
        "artifact_type": "readonly_replay_window_index",
        "schema_version": "readonly_replay_window_index_d7_v1",
        "created_at": now(),
        "created_by": rel(Path(__file__)),
        "phase": "D7",
        "readonly_only": True,
        "production_trade_enabled": False,
        "indexed_windows_only": True,
        "windows": [
            {
                "window_key": "2026_ytd",
                "window_type": "fixed_standard",
                "display_label": "固定 2026_ytd 标准窗口",
                "model_id": "e4_frozen_qlib_2023_2025_ltr",
                "strategy_rule": "top50_exit_one_worst_sell",
                "start": "2026-01-01",
                "end": "2026-05-07",
                "artifact_manifest": rel(d4_manifest),
                "sources": {
                    "standard_artifact_index_manifest": rel(d4_manifest),
                    "order_intent_replay_result_manifest": d4_index.get("order_intent_replay_result_manifest"),
                },
                "validation": {"ok": True, "kind": "fixed_standard_index"},
            },
            {
                "window_key": "20260102_20260507",
                "window_type": "generated_readonly",
                "display_label": "D6 非固定窗口 2026-01-02..2026-05-07",
                "model_id": "e4_frozen_qlib_2023_2025_ltr",
                "strategy_rule": "top50_exit_one_worst_sell",
                "start": "2026-01-02",
                "end": "2026-05-07",
                "artifact_manifest": rel(d6_manifest),
                "sources": {
                    "readonly_replay_manifest": rel(d6_manifest),
                    "replay_window_policy": d6_payload.get("replay_window_policy"),
                },
                "validation": {"ok": True, "kind": "generated_readonly_index"},
            },
        ],
        "checksum_manifest": "checksum_manifest.json",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "manifest.json", manifest)
    checksum = {
        "artifact_type": "readonly_replay_window_index_checksum",
        "schema_version": "readonly_replay_window_index_checksum_d7_v1",
        "created_at": now(),
        "files": checksum_items([
            out_dir / "manifest.json",
            d4_manifest,
            resolve("data_tw/artifacts/readonly_standard_artifact_index/d4/checksum_manifest.json"),
            d6_manifest,
            resolve("data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/checksum_manifest.json"),
        ]),
    }
    write_json(out_dir / "checksum_manifest.json", checksum)
    latest = {
        "artifact_type": "readonly_replay_window_index_latest_pointer",
        "schema_version": "readonly_replay_window_index_latest_d7_v1",
        "created_at": now(),
        "readonly_only": True,
        "production_trade_enabled": False,
        "index_manifest": rel(out_dir / "manifest.json"),
    }
    write_json(out_dir / "latest.json", latest)
    return {"ok": True, "manifest": rel(out_dir / "manifest.json"), "latest": rel(out_dir / "latest.json"), "window_count": len(manifest["windows"])}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build readonly replay window index.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = build_index(out_dir=resolve(args.out_dir))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        print(f"manifest={result['manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
