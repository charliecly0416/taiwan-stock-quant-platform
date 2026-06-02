#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_QLIB = Path("/home/chuliyang/qlib")
RECORDER_REL = Path("mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a")
EXPERIMENT_META_REL = Path("mlruns/607910013167647574/meta.yaml")
OPTION_C_SIGNAL_REL = Path("data_tw/experiments/option_c_daily_signal")
OPTION_C_FORWARD_VALIDATION_REL = Path("data_tw/experiments/option_c_forward_validation")
YAHOO_PRIMARY_REL = Path("data_tw/experiments/yahoo_adjusted_primary")
REQUIRED_YAHOO_SUBPATHS = [
    Path("normalized_nonempty"),
    Path("option_c_150_normalized"),
    Path("option_c_150_qlib_bin"),
    Path("qlib_bin"),
    Path("universe"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap full production Taiwan-stock qlib assets into this standalone repo.")
    parser.add_argument("--source-qlib", default=str(DEFAULT_SOURCE_QLIB), help="Existing qlib project containing data_tw and mlruns.")
    parser.add_argument("--copy-full-provider", action="store_true", help="Also copy the wider yahoo_adjusted_primary/qlib_bin provider. This is larger than the Option C 150 provider.")
    parser.add_argument("--replace", action="store_true", help="Replace existing target asset directories.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _copytree(src: Path, dst: Path, *, replace: bool, dry_run: bool) -> dict[str, Any]:
    if not src.exists():
        return {"source": str(src), "target": str(dst), "status": "missing_source"}
    if dst.exists():
        if not replace:
            return {"source": str(src), "target": str(dst), "status": "exists_skipped"}
        if not dry_run:
            shutil.rmtree(dst)
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
    return {"source": str(src), "target": str(dst), "status": "copied" if not dry_run else "would_copy"}


def _copy_file(src: Path, dst: Path, *, replace: bool, dry_run: bool) -> dict[str, Any]:
    if not src.exists():
        return {"source": str(src), "target": str(dst), "status": "missing_source"}
    if dst.exists() and not replace:
        return {"source": str(src), "target": str(dst), "status": "exists_skipped"}
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return {"source": str(src), "target": str(dst), "status": "copied" if not dry_run else "would_copy"}


def _count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _latest_date_in_csv_dir(path: Path) -> dict[str, Any]:
    latest = ""
    csv_count = 0
    for csv_path in path.glob("TW*.csv"):
        csv_count += 1
        try:
            lines = csv_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = csv_path.read_text(encoding="utf-8-sig").splitlines()
        if len(lines) <= 1:
            continue
        header = lines[0].split(",")
        try:
            idx = header.index("date")
        except ValueError:
            continue
        tail = lines[-1].split(",")
        if idx < len(tail):
            latest = max(latest, tail[idx])
    return {"csv_count": csv_count, "latest_date": latest or None}


def _read_latest_signal(path: Path) -> dict[str, Any]:
    latest = path / "latest_signal.json"
    if not latest.exists():
        return {"exists": False}
    return {"exists": True, **json.loads(latest.read_text(encoding="utf-8"))}


def main() -> int:
    args = parse_args()
    source = Path(args.source_qlib).expanduser().resolve()
    target_qlib = ROOT / "qlib_pipeline"
    operations: list[dict[str, Any]] = []

    yahoo_src = source / YAHOO_PRIMARY_REL
    yahoo_dst = target_qlib / YAHOO_PRIMARY_REL
    for sub in REQUIRED_YAHOO_SUBPATHS:
        if sub == Path("qlib_bin") and not args.copy_full_provider:
            continue
        operations.append(_copytree(yahoo_src / sub, yahoo_dst / sub, replace=args.replace, dry_run=args.dry_run))

    operations.append(_copytree(source / OPTION_C_SIGNAL_REL, target_qlib / OPTION_C_SIGNAL_REL, replace=args.replace, dry_run=args.dry_run))
    operations.append(_copytree(source / OPTION_C_FORWARD_VALIDATION_REL / "timed_data_availability_retry_20260601T101323Z", target_qlib / OPTION_C_FORWARD_VALIDATION_REL / "timed_data_availability_retry_20260601T101323Z", replace=args.replace, dry_run=args.dry_run))
    operations.append(_copytree(source / RECORDER_REL, target_qlib / RECORDER_REL, replace=args.replace, dry_run=args.dry_run))
    operations.append(_copy_file(source / EXPERIMENT_META_REL, target_qlib / EXPERIMENT_META_REL, replace=args.replace, dry_run=args.dry_run))

    validation = {
        "option_c_150_normalized": _latest_date_in_csv_dir(target_qlib / YAHOO_PRIMARY_REL / "option_c_150_normalized"),
        "option_c_150_qlib_bin_files": _count_files(target_qlib / YAHOO_PRIMARY_REL / "option_c_150_qlib_bin"),
        "option_c_150_qlib_bin_bytes": _dir_size(target_qlib / YAHOO_PRIMARY_REL / "option_c_150_qlib_bin"),
        "accepted_latest": _read_latest_signal(target_qlib / OPTION_C_SIGNAL_REL),
        "accepted_prediction_universe_exists": (target_qlib / OPTION_C_FORWARD_VALIDATION_REL / "timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt").exists(),
        "recorder_exists": (target_qlib / RECORDER_REL).exists(),
        "model_params_exists": (target_qlib / RECORDER_REL / "artifacts/params.pkl").exists(),
        "model_pred_exists": (target_qlib / RECORDER_REL / "artifacts/pred.pkl").exists(),
    }
    payload = {
        "ok": all(op["status"] not in {"missing_source"} for op in operations),
        "source_qlib": str(source),
        "target_qlib_pipeline": str(target_qlib),
        "dry_run": bool(args.dry_run),
        "operations": operations,
        "validation": validation,
        "backend_env": {
            "QLIB_TW_OPTION_C_ROOT": str(target_qlib / OPTION_C_SIGNAL_REL),
            "TW_QLIB_OPTION_C_CWD": str(target_qlib),
            "TW_QLIB_OPTION_C_PROVIDER_CALENDAR": str(target_qlib / YAHOO_PRIMARY_REL / "option_c_150_qlib_bin/calendars/day.txt"),
        },
        "note": "Copied data/model artifacts are ignored by git. Publish them as release artifacts or regenerate them with the included scripts.",
    }
    report = ROOT / "docs" / "FULL_PRODUCTION_ASSETS_BOOTSTRAP_REPORT_CN.json"
    if not args.dry_run:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
