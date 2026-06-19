#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_MANIFEST = (
    ROOT / "data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json"
)
DEFAULT_OUT_DIR = ROOT / "data_tw/artifacts/signals_extension_smoke/sector_extension_smoke"
DEFAULT_DEPENDENCY = ROOT / "configs/strategy_dependencies/sector_extension_analysis_smoke.yaml"
VALIDATOR = ROOT / "scripts/validate_tw_modular_artifact_contract.py"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sector_code(instrument: str) -> str:
    digits = "".join(ch for ch in str(instrument) if ch.isdigit())
    if not digits:
        return "sector_smoke_unknown"
    bucket = int(digits[:2]) if len(digits) >= 2 else int(digits)
    return f"sector_smoke_{bucket:02d}"


def run_validator(manifest: Path, dependency: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--artifact",
            str(manifest),
            "--strategy-dependency",
            str(dependency),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.stdout.strip():
        return json.loads(proc.stdout)
    return {
        "ok": False,
        "artifact": str(manifest),
        "checks": [{"name": "validator_subprocess", "status": "fail", "details": proc.stderr.strip()}],
    }


def build_smoke_artifact(source_manifest_path: Path, out_dir: Path, dependency_path: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat()
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_signals = resolve(source_manifest["output_files"]["signals"])
    source_schema = resolve(source_manifest["output_files"]["schema"])
    source_coverage = resolve(source_manifest["output_files"]["coverage_audit"])
    source_forbidden = resolve(source_manifest["output_files"]["forbidden_field_audit"])
    source_mapping = resolve(source_manifest["output_files"]["legacy_mapping_audit"])

    signals = pd.read_csv(source_signals)
    signals["ext_sector_code"] = signals["instrument"].map(sector_code)
    signals_path = out_dir / "signals.csv"
    signals.to_csv(signals_path, index=False)

    schema = json.loads(source_schema.read_text(encoding="utf-8"))
    schema["fields"]["ext_sector_code"] = "object"
    schema["extension_fields"] = {
        "ext_sector_code": {
            "dtype": "string",
            "semantic_role": "sector_code",
            "availability_policy": "static_reference",
            "producer": "scripts/build_tw_modular_extension_smoke_artifact.py",
            "allowed_consumers": ["sector_analysis_smoke"],
            "ranking_allowed": False,
            "required_for_core_replay": False,
            "description": "Controlled static sector-code smoke extension. Not used for ranking or replay.",
        }
    }
    schema_path = out_dir / "schema.json"
    write_json(schema_path, schema)

    for source, name in [
        (source_coverage, "coverage_audit.csv"),
        (source_forbidden, "forbidden_field_audit.csv"),
        (source_mapping, "legacy_mapping_audit.csv"),
    ]:
        shutil.copyfile(source, out_dir / name)

    manifest = dict(source_manifest)
    manifest.update(
        {
            "artifact_type": "model_signal",
            "artifact_name": "fresh_qlib_adaptive_sector_extension_smoke",
            "run_id": "r7_sector_extension_smoke_20260616",
            "created_at": created_at,
            "created_by": "scripts/build_tw_modular_extension_smoke_artifact.py",
            "schema_version": source_manifest.get("schema_version", "r1.0"),
            "contract_version": source_manifest.get("contract_version", ""),
            "model_name": "fresh_qlib_adaptive_sector_extension_smoke",
            "source_manifest": rel(source_manifest_path),
            "source_artifact_unchanged": True,
            "no_replay": True,
            "no_strategy_return_conclusion": True,
            "quality_status": "smoke_only",
            "row_count": int(len(signals)),
            "duplicate_key_count": int(signals.duplicated(["date", "instrument"]).sum()),
            "output_files": {
                "signals": rel(signals_path),
                "schema": rel(schema_path),
                "coverage_audit": rel(out_dir / "coverage_audit.csv"),
                "forbidden_field_audit": rel(out_dir / "forbidden_field_audit.csv"),
                "legacy_mapping_audit": rel(out_dir / "legacy_mapping_audit.csv"),
            },
        }
    )
    manifest["capabilities"] = dict(source_manifest.get("capabilities") or {})
    manifest["capabilities"]["supports_sector_exposure"] = True
    manifest["capabilities"]["extension_smoke_only"] = True
    manifest["extensions"] = {
        "schema_version": "model_signal_extension_v1",
        "fields": {
            "ext_sector_code": {
                "dtype": "string",
                "semantic_role": "sector_code",
                "availability_policy": "static_reference",
                "producer": "scripts/build_tw_modular_extension_smoke_artifact.py",
                "allowed_consumers": ["sector_analysis_smoke"],
                "ranking_allowed": False,
                "required_for_core_replay": False,
                "description": "Controlled static sector-code smoke extension. Not used for ranking or replay.",
            }
        },
    }
    manifest["forbidden_actions"] = {
        "no_training": True,
        "no_tuning": True,
        "no_score_recompute": True,
        "no_replay": True,
        "no_return_filtering": True,
        "no_strategy_result": True,
        "no_frontend_change": True,
        "no_daily_orchestrator_change": True,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor": True,
        "no_broker_order": True,
    }
    manifest_path = out_dir / "manifest.json"
    write_json(manifest_path, manifest)

    negative_dir = out_dir / "negative_missing_extension"
    negative_dir.mkdir(parents=True, exist_ok=True)
    negative_signals = signals.drop(columns=["ext_sector_code"])
    negative_signals_path = negative_dir / "signals.csv"
    negative_signals.to_csv(negative_signals_path, index=False)
    negative_manifest = dict(manifest)
    negative_manifest["artifact_name"] = "fresh_qlib_adaptive_sector_extension_smoke_negative_missing_extension"
    negative_manifest["output_files"] = dict(manifest["output_files"])
    negative_manifest["output_files"]["signals"] = rel(negative_signals_path)
    negative_manifest["negative_case"] = "missing ext_sector_code column while dependency requires it"
    negative_manifest_path = negative_dir / "manifest.json"
    write_json(negative_manifest_path, negative_manifest)

    positive_validation = run_validator(manifest_path, dependency_path)
    negative_validation = run_validator(negative_manifest_path, dependency_path)
    write_json(out_dir / "positive_validation.json", positive_validation)
    write_json(out_dir / "negative_missing_extension_validation.json", negative_validation)

    summary = {
        "ok": bool(positive_validation.get("ok")) and not bool(negative_validation.get("ok")),
        "created_at": created_at,
        "source_manifest": rel(source_manifest_path),
        "artifact": rel(manifest_path),
        "dependency": rel(dependency_path),
        "row_count": int(len(signals)),
        "extension": "ext_sector_code",
        "positive_validation_ok": bool(positive_validation.get("ok")),
        "negative_missing_extension_validation_ok": bool(negative_validation.get("ok")),
        "negative_expected_to_fail": True,
        "no_replay": True,
        "no_strategy_return_conclusion": True,
        "outputs": {
            "manifest": rel(manifest_path),
            "signals": rel(signals_path),
            "schema": rel(schema_path),
            "positive_validation": rel(out_dir / "positive_validation.json"),
            "negative_missing_extension_validation": rel(out_dir / "negative_missing_extension_validation.json"),
            "summary": rel(out_dir / "smoke_summary.json"),
        },
    }
    write_json(out_dir / "smoke_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a controlled TW modular extension smoke artifact.")
    parser.add_argument("--source-manifest", default=str(DEFAULT_SOURCE_MANIFEST), help="R1 source signal manifest")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Smoke artifact output directory")
    parser.add_argument("--strategy-dependency", default=str(DEFAULT_DEPENDENCY), help="Smoke strategy dependency yaml")
    parser.add_argument("--json", action="store_true", help="Print summary JSON")
    args = parser.parse_args()

    summary = build_smoke_artifact(resolve(args.source_manifest), resolve(args.out_dir), resolve(args.strategy_dependency))
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"ok={summary['ok']} artifact={summary['artifact']}")
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
