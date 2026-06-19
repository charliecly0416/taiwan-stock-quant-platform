#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data_tw/artifacts/readonly_replay_windows/d7/manifest.json"


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def checksum_ok(manifest_path: Path, manifest: dict[str, Any]) -> tuple[bool, str]:
    ref = str(manifest.get("checksum_manifest", ""))
    candidate = manifest_path.parent / ref
    path = candidate if candidate.exists() else resolve(ref)
    if not path.exists():
        return False, "missing checksum_manifest"
    payload = load_json(path)
    bad = []
    for item in payload.get("files", []):
        target = resolve(str(item.get("path", "")))
        if not target.exists() or sha256_file(target) != item.get("sha256"):
            bad.append(str(item.get("path", "")))
    return not bad and bool(payload.get("files")), f"checked={len(payload.get('files', []))}; bad={'|'.join(bad)}"


def validate_index(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    windows = manifest.get("windows") or []
    checks = [
        check("artifact_type", manifest.get("artifact_type") == "readonly_replay_window_index", str(manifest.get("artifact_type"))),
        check("schema_version", manifest.get("schema_version") == "readonly_replay_window_index_d7_v1", str(manifest.get("schema_version"))),
        check("readonly_only", manifest.get("readonly_only") is True),
        check("production_trade_enabled_false", manifest.get("production_trade_enabled") is False),
        check("indexed_windows_only", manifest.get("indexed_windows_only") is True),
        check("window_count", len(windows) >= 2, str(len(windows))),
    ]
    required = {"window_key", "window_type", "display_label", "model_id", "strategy_rule", "start", "end", "artifact_manifest"}
    errors = []
    for idx, entry in enumerate(windows):
        missing = sorted(required - set(entry))
        if missing:
            errors.append(f"{idx}:{','.join(missing)}")
        artifact = resolve(str(entry.get("artifact_manifest", "")))
        if not artifact.exists():
            errors.append(f"{idx}:missing_artifact")
    checks.append(check("window_schema", not errors, "|".join(errors)))
    checksum_pass, checksum_details = checksum_ok(manifest_path, manifest)
    checks.append(check("checksum_ok", checksum_pass, checksum_details))
    return {"ok": all(row["status"] == "pass" for row in checks), "artifact": rel(manifest_path), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate readonly replay window index.")
    parser.add_argument("--artifact", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate_index(resolve(args.artifact))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
