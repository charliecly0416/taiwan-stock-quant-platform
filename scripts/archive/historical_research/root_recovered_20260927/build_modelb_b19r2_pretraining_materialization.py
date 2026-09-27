#!/usr/bin/env python3
"""Build frozen, research-only B19R2 pretraining inputs in explicit stages."""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2_pretraining_materialization_20260916"
OUT_R = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916"
B19R1 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r1_calendar_source_repair_20260916"
B19R1_REVIEW = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r1_independent_review_20260916/B19R1_FINAL_INDEPENDENT_REVIEW.json"
B19_REVIEW = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19_preflight_independent_review_20260916/B19_PREFLIGHT_FINAL_INDEPENDENT_REVIEW.json"
B18_REVIEW = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b18r2_postexecution_independent_review_20260916/B18R2_POSTEXECUTION_INDEPENDENT_REVIEW.json"
B2_SCHEMA = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json"
B2_MANIFEST = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/B2_FEATURE_ARTIFACT_MANIFEST.json"
B4_MANIFEST = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b4_canonical_label_samples_20260914/B4_CANONICAL_EXECUTOR_MANIFEST.json"
B9_FREEZE = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b9_canonical_label_retrain_20260914/B9_CANONICAL_RETRAIN_RUN_FREEZE.json"
B9_REVIEW = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b9_canonical_label_retrain_20260914/B9_CANONICAL_RETRAIN_INDEPENDENT_REVIEW.json"
MODEL_A = ROOT / "qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl"
MODEL_A_TRAINING_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_training_manifest.json"
MODEL_A_PROVIDER = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
CALENDAR = B19R1 / "FROZEN_ACTUAL_MARKET_CALENDAR.csv"
SOURCE_LINEAGE = B19R1 / "SOURCE_LINEAGE.json"
SOURCE_CAPACITY = B19R1 / "SOURCE_CAPACITY_AUDIT.csv"
PRICE_CAPTURE = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260915_20260915T103002Z/same_run_handoff_artifacts/daily_price/daily_price.normalized.json"
INSTITUTIONAL_CAPTURE = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260915_20260915T144501Z/same_run_handoff_artifacts/institutional/institutional.normalized.json"
MARGIN_CAPTURE = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260915_20260915T144501Z/same_run_handoff_artifacts/margin/margin.normalized.json"
TWII_B2 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b01_feature_input_contract_repair_20260913/twii_acquisition/TWII_NORMALIZED.csv"
TWII_POST = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b8_prospective_shadow_20260914/source_run_20260914_natural/yahoo_twii_20260914/twii.csv"
B3_MODEL_A = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b3_frozen_modela_oos_score_20260913/MODEL_A_FROZEN_OOS_SCORE.parquet"
FORMAL_EFFECTIVE_START = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b1_same_run_handoff_20260913/FORMAL_UNIVERSE_EFFECTIVE_START_AUDIT.csv"
LABEL_FREE_SCORER = ROOT / "scripts/modelb_b19r2r_label_free_modela.py"
B2_CALENDAR = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b01_feature_input_contract_repair_20260913/CANONICAL_CALENDAR_THROUGH_TARGET.csv"
AMENDMENT_03 = OUT_R / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_03.json"
AMENDMENT_04 = OUT_R / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_04.json"
AMENDMENT_05 = OUT_R / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_05.json"
ATTEMPT_FAILURE_01 = OUT_R / "B19R2R_MATERIALIZATION_ATTEMPT_FAILURE_01.json"
ATTEMPT_FAILURE_01_ERRATA = OUT_R / "B19R2R_MATERIALIZATION_ATTEMPT_FAILURE_01_ERRATA.json"
ROLLOVER_OBSERVATION_01 = OUT_R / "B19R2R_EXTERNAL_DAILY_ROLLOVER_OBSERVATION_01.json"
EFFECTIVE_SPLIT = OUT_R / "NESTED_WALK_FORWARD_SPLIT_AMENDMENT_03.csv"

MODEL_ID = "modelb_b19r2_lambdarank_78f_v1"
MODEL_ID_R = "modelb_b19r2r_lambdarank_78f_v1"
FEATURE_ORDER_SHA = "2e0c169fb7762240aa20bc31ea53ac21b6a69db99dabea2f897421121105f2ca"
EXCLUDED = ["TW6919", "TW7769"]
PROTECTED = (
    ROOT / "configs/active_baseline_descriptor.yaml",
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "exists": path.is_file(),
        "sha256": sha256(path) if path.is_file() else None,
        "bytes": path.stat().st_size if path.is_file() else None,
    }


def fingerprints(paths: tuple[Path, ...]) -> dict[str, dict[str, Any]]:
    return {rel(path): fingerprint(path) for path in paths}


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def positive_streak(values: pd.Series) -> pd.Series:
    count = 0
    output = []
    for value in values.fillna(0).astype(int):
        count = count + 1 if value else 0
        output.append(float(count))
    return pd.Series(output, index=values.index, dtype=float)


def signed_streak(values: pd.Series) -> pd.Series:
    sign = 0
    count = 0
    output = []
    for value in values:
        current = 0 if pd.isna(value) or value == 0 else (1 if value > 0 else -1)
        if current == 0:
            sign, count = 0, 0
        elif current == sign:
            count += 1
        else:
            sign, count = current, 1
        output.append(float(sign * count))
    return pd.Series(output, index=values.index, dtype=float)


def rsi14(close: pd.Series) -> tuple[pd.Series, pd.Series]:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    ready = delta.rolling(14, min_periods=14).count().eq(14) & close.notna()
    value = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    value = value.mask(ready & loss.eq(0), 50.0).where(ready)
    return value, ready


def canonical_provider_tree_hash(entries: list[dict[str, Any]]) -> str:
    """Hash an explicit, sorted inventory of provider feature binaries."""
    digest = hashlib.sha256()
    for entry in sorted(entries, key=lambda item: item["path"]):
        line = f'{entry["path"]}\0{entry["sha256"]}\0{entry["bytes"]}\n'
        digest.update(line.encode("ascii"))
    return digest.hexdigest()


def binary_record(path: Path, provider_root: Path) -> tuple[dict[str, Any], np.ndarray]:
    raw = path.read_bytes()
    values = np.frombuffer(raw, dtype="<f4")
    if len(values) < 2:
        raise RuntimeError(f"invalid qlib feature binary: {path}")
    return {
        "path": path.relative_to(provider_root).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "start_index": int(values[0]),
        "rows": len(values) - 1,
    }, values


def effective_protocol() -> dict[str, Any]:
    required = (AMENDMENT_03, AMENDMENT_04, AMENDMENT_05, ATTEMPT_FAILURE_01, ATTEMPT_FAILURE_01_ERRATA, ROLLOVER_OBSERVATION_01, EFFECTIVE_SPLIT)
    if not all(path.is_file() for path in required):
        raise RuntimeError("effective amendment05 protocol, failure evidence, or amendment03 split is missing")
    amendment = json.loads(AMENDMENT_05.read_text(encoding="utf-8"))
    bindings = amendment.get("implementation_bindings", {})
    if bindings.get("input_builder", {}).get("sha256") != sha256(Path(__file__)):
        raise RuntimeError("input builder no longer matches amendment05")
    if bindings.get("label_free_model_a_scorer", {}).get("sha256") != sha256(LABEL_FREE_SCORER):
        raise RuntimeError("label-free scorer no longer matches amendment05")
    if amendment.get("failed_attempt_binding", {}).get("sha256") != sha256(ATTEMPT_FAILURE_01):
        raise RuntimeError("attempt failure evidence no longer matches amendment05")
    if amendment.get("failed_attempt_errata_binding", {}).get("sha256") != sha256(ATTEMPT_FAILURE_01_ERRATA):
        raise RuntimeError("attempt failure errata no longer matches amendment05")
    if amendment.get("rollover_observation_binding", {}).get("sha256") != sha256(ROLLOVER_OBSERVATION_01):
        raise RuntimeError("daily rollover observation no longer matches amendment05")
    split = amendment.get("effective_future_training_split", {})
    if split.get("path") != rel(EFFECTIVE_SPLIT) or split.get("sha256") != sha256(EFFECTIVE_SPLIT):
        raise RuntimeError("effective amendment03 split binding mismatch")
    if split.get("base_split_consumption_allowed") is not False:
        raise RuntimeError("base split must be forbidden by amendment04")
    return amendment


def load_json_records(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    frame = pd.DataFrame(payload.get("records", []))
    frame["date"] = frame.get("trade_date", frame.get("date", "")).astype(str).str[:10]
    frame["instrument"] = frame.get("symbol", frame.get("stock_id", "")).astype(str).str.upper()
    frame["instrument"] = frame.instrument.where(frame.instrument.str.startswith("TW"), "TW" + frame.instrument)
    return frame


def provider_symbols(provider_root: Path) -> list[str]:
    instrument_path = provider_root / "instruments/all.txt"
    symbols = sorted(
        line.split("\t", 1)[0].strip().upper()
        for line in instrument_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    feature_symbols = sorted(path.name.upper() for path in (provider_root / "features").iterdir() if path.is_dir())
    if len(symbols) != 150 or symbols != feature_symbols:
        raise RuntimeError("isolated provider must contain the same exact 150 instruments and feature directories")
    return symbols


def frozen_model_a_inference(start: str, end: str, allowed_dates: list[str]) -> pd.DataFrame:
    from modelb_b19r2r_label_free_modela import predict_feature_only
    symbols = provider_symbols(MODEL_A_PROVIDER)
    prediction = predict_feature_only(provider_root=MODEL_A_PROVIDER, model_path=MODEL_A, symbols=symbols, start=start, end=end)
    prediction = prediction[prediction.date.isin(set(allowed_dates))].copy()
    prediction = prediction.sort_values(["date", "model_a_raw_score", "instrument"], ascending=[True, False, True], kind="mergesort").reset_index(drop=True)
    prediction["full_qlib_rank"] = prediction.groupby("date").cumcount() + 1
    prediction["signal_asof"] = prediction.date
    prediction["available_at"] = prediction.date
    prediction["source_model_artifact"] = rel(MODEL_A)
    prediction["source_model_sha256"] = sha256(MODEL_A)
    prediction["source_provider"] = rel(MODEL_A_PROVIDER)
    prediction["source_provider_calendar_sha256"] = sha256(MODEL_A_PROVIDER / "calendars/day.txt")
    if prediction.duplicated(["date", "instrument"]).any():
        raise RuntimeError("frozen Model A prediction has duplicate keys")
    return prediction


def canonical_actual_calendar(last_signal_day: str) -> list[str]:
    old = pd.read_csv(B2_CALENDAR, dtype=str)["date"].astype(str).tolist()
    captured = load_json_records(PRICE_CAPTURE)
    captured_dates = sorted(captured.date.unique())
    capture_start = captured_dates[0]
    dates = sorted({day for day in old if day < capture_start} | {day for day in captured_dates if day <= last_signal_day})
    if "2026-07-10" in dates:
        raise RuntimeError("non-trading placeholder leaked into canonical actual calendar")
    return dates


def build_isolated_model_a_provider(run_dir: Path) -> tuple[Path, dict[str, Any]]:
    destination = run_dir / "isolated_model_a_provider_no_nontrading_placeholders"
    manifest_path = destination / "B19R2R_ISOLATED_PROVIDER_MANIFEST.json"
    if manifest_path.is_file():
        binding = effective_protocol()["isolated_provider_binding"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        actual_entries = []
        for path in sorted((destination / "features").glob("*/*.day.bin")):
            record, _ = binary_record(path, destination)
            actual_entries.append(record)
        clean_paths = {entry["path"] for entry in actual_entries}
        provenance_paths = {entry["path"] for entry in manifest.get("file_mapping", [])}
        calendar_path = destination / "calendars/day.txt"
        if len(actual_entries) != binding["feature_file_count"] or len(provenance_paths) != binding["feature_file_count"]:
            raise RuntimeError("existing isolated provider feature-file count mismatch")
        if clean_paths != provenance_paths:
            raise RuntimeError("existing isolated provider path set mismatch")
        if canonical_provider_tree_hash(actual_entries) != binding["expected_clean_feature_tree_sha256"]:
            raise RuntimeError("existing isolated provider clean tree mismatch")
        if not calendar_path.is_file() or sha256(calendar_path) != binding["expected_clean_calendar_sha256"]:
            raise RuntimeError("existing isolated provider calendar mismatch")
        if len([line for line in calendar_path.read_text(encoding="utf-8").splitlines() if line]) != binding["expected_clean_calendar_rows"]:
            raise RuntimeError("existing isolated provider calendar row-count mismatch")
        if manifest.get("clean_feature_tree_sha256") != binding["expected_clean_feature_tree_sha256"]:
            raise RuntimeError("existing isolated provider manifest binding mismatch")
        mapping_by_path = {entry["path"]: entry for entry in manifest["file_mapping"]}
        if any(
            mapping_by_path[entry["path"]].get("clean_sha256") != entry["sha256"]
            or mapping_by_path[entry["path"]].get("clean_bytes") != entry["bytes"]
            for entry in actual_entries
        ):
            raise RuntimeError("existing isolated provider differs from per-file provenance")
        return destination, manifest
    if destination.exists():
        raise RuntimeError("refusing partial isolated provider")
    source_calendar_path = MODEL_A_PROVIDER / "calendars/day.txt"
    source_calendar = [line.strip() for line in source_calendar_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    captured = load_json_records(PRICE_CAPTURE)
    actual = set(captured.date.unique())
    capture_start, capture_end = min(actual), max(actual)
    removed = [day for day in source_calendar if capture_start <= day <= capture_end and day not in actual]
    if removed != ["2026-07-10"]:
        raise RuntimeError(f"unexpected provider-only dates: {removed}")
    removed_indexes = {source_calendar.index(day) for day in removed}
    cleaned_calendar = [day for index, day in enumerate(source_calendar) if index not in removed_indexes]
    (destination / "calendars").mkdir(parents=True)
    (destination / "instruments").mkdir(parents=True)
    (destination / "features").mkdir(parents=True)
    (destination / "calendars/day.txt").write_text("\n".join(cleaned_calendar) + "\n", encoding="utf-8")
    shutil.copy2(MODEL_A_PROVIDER / "instruments/all.txt", destination / "instruments/all.txt")
    amendment = effective_protocol()
    provider_binding = amendment["isolated_provider_binding"]
    source_entries: list[dict[str, Any]] = []
    clean_entries: list[dict[str, Any]] = []
    file_mapping: list[dict[str, Any]] = []
    for source in sorted((MODEL_A_PROVIDER / "features").glob("*/*.day.bin")):
        source_record, values = binary_record(source, MODEL_A_PROVIDER)
        source_entries.append(source_record)
        old_start = source_record["start_index"]
        data = values[1:]
        represented_indexes = np.arange(old_start, old_start + len(data))
        keep = np.array([index not in removed_indexes for index in represented_indexes], dtype=bool)
        new_start = old_start - sum(index < old_start for index in removed_indexes)
        output = np.concatenate([np.asarray([float(new_start)], dtype="<f4"), data[keep].astype("<f4")])
        target = destination / source.relative_to(MODEL_A_PROVIDER)
        target.parent.mkdir(parents=True, exist_ok=True)
        output.tofile(target)
        clean_record, clean_values = binary_record(target, destination)
        clean_entries.append(clean_record)
        removed_local_rows = int(len(data) - keep.sum())
        expected_removed_rows = sum(old_start <= index < old_start + len(data) for index in removed_indexes)
        if removed_local_rows != expected_removed_rows:
            raise RuntimeError(f"wrong removed row count for {source_record['path']}")
        if not np.array_equal(clean_values[1:], data[keep], equal_nan=True):
            raise RuntimeError(f"clean binary payload mismatch for {source_record['path']}")
        file_mapping.append({
            "path": source_record["path"],
            "source_sha256": source_record["sha256"],
            "source_bytes": source_record["bytes"],
            "source_start_index": old_start,
            "source_rows": source_record["rows"],
            "removed_global_indexes": sorted(index for index in removed_indexes if old_start <= index < old_start + len(data)),
            "removed_rows": removed_local_rows,
            "clean_sha256": clean_record["sha256"],
            "clean_bytes": clean_record["bytes"],
            "clean_start_index": clean_record["start_index"],
            "clean_rows": clean_record["rows"],
        })
    source_tree_sha = canonical_provider_tree_hash(source_entries)
    clean_tree_sha = canonical_provider_tree_hash(clean_entries)
    clean_calendar_sha = sha256(destination / "calendars/day.txt")
    if len(source_entries) != provider_binding.get("feature_file_count"):
        raise RuntimeError("isolated provider feature-file count mismatch")
    if source_tree_sha != provider_binding.get("source_feature_tree_sha256"):
        raise RuntimeError("source provider feature tree changed after amendment04")
    if clean_tree_sha != provider_binding.get("expected_clean_feature_tree_sha256"):
        raise RuntimeError("clean provider feature tree does not match amendment04")
    if clean_calendar_sha != provider_binding.get("expected_clean_calendar_sha256"):
        raise RuntimeError("clean provider calendar does not match amendment04")
    manifest = {
        "schema_version": "modelb.b19r2r.isolated_model_a_provider.v1",
        "source_provider": rel(MODEL_A_PROVIDER),
        "source_calendar_sha256": sha256(source_calendar_path),
        "source_calendar_rows": len(source_calendar),
        "actual_calendar_source": fingerprint(PRICE_CAPTURE),
        "removed_provider_only_dates": removed,
        "cleaned_calendar_rows": len(cleaned_calendar),
        "feature_files_rewritten": len(clean_entries),
        "tree_hash_canonicalization": "Root is the provider directory. For all features/*/*.day.bin files sorted by provider-relative POSIX path, SHA256 the ASCII rows path\\0sha256\\0bytes\\n.",
        "source_feature_tree_sha256": source_tree_sha,
        "clean_feature_tree_sha256": clean_tree_sha,
        "clean_calendar_sha256": clean_calendar_sha,
        "file_mapping": file_mapping,
        "2026_07_10_present": "2026-07-10" in cleaned_calendar,
        "purpose": "Prevent non-trading placeholder participation in Alpha158 rolling before frozen Model A inference.",
        "provider_publish_or_latest_write": False,
    }
    write_json(manifest_path, manifest)
    return destination, manifest


def decode_provider_field(provider_root: Path, symbol: str, field: str, calendar: list[str]) -> np.ndarray:
    path = provider_root / "features" / symbol.lower() / f"{field}.day.bin"
    values = np.fromfile(path, dtype="<f4")
    if len(values) < 2:
        raise RuntimeError(f"invalid isolated provider field: {path}")
    start = int(values[0])
    data = values[1:].astype(float)
    if start < 0 or start + len(data) > len(calendar):
        raise RuntimeError(f"isolated provider field exceeds calendar: {path}")
    expanded = np.full(len(calendar), np.nan, dtype=float)
    expanded[start : start + len(data)] = data
    return expanded


def price_grid(provider_root: Path, last_signal_day: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    actual_dates = set(canonical_actual_calendar(last_signal_day))
    calendar = [line.strip() for line in (provider_root / "calendars/day.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    effective_frame = pd.read_csv(FORMAL_EFFECTIVE_START, dtype=str)
    effective_start = dict(zip(effective_frame.instrument.str.upper(), effective_frame.effective_start, strict=True))
    symbols = provider_symbols(provider_root)
    if set(effective_start) != set(symbols) or sha256(FORMAL_EFFECTIVE_START) != "dedba30e110a5e7fe9cdeecd35f7471065120c8924b599785205f7e640a3127e":
        raise RuntimeError("formal universe effective-start binding mismatch")
    fields = ["open", "high", "low", "close", "volume", "vwap", "factor"]
    frames: list[pd.DataFrame] = []
    for symbol in symbols:
        decoded = {field: decode_provider_field(provider_root, symbol, field, calendar) for field in fields}
        raw = pd.DataFrame({"date": calendar, "instrument": symbol, **decoded})
        raw = raw[raw.date.isin(actual_dates) & raw.date.ge(effective_start[symbol])].sort_values("date").reset_index(drop=True)
        close, volume = raw.close, raw.volume
        for window in [5, 10, 20, 60]:
            raw[f"MA{window}"] = close.rolling(window, min_periods=window).mean()
        raw["RSI14"], raw["_rsi_ready"] = rsi14(close)
        raw["MACD"] = close.ewm(span=12, adjust=False, min_periods=12).mean() - close.ewm(span=26, adjust=False, min_periods=26).mean()
        raw["Bollinger_position"] = ((close - raw.MA20) / (2 * close.rolling(20, min_periods=20).std(ddof=1).replace(0, np.nan))).clip(-5, 5)
        daily_return = close.pct_change(fill_method=None)
        raw["ret20"] = close.pct_change(20, fill_method=None)
        raw["volatility20"] = daily_return.rolling(20, min_periods=20).std(ddof=1)
        raw["volume_ratio20"] = volume / volume.rolling(20, min_periods=20).mean().replace(0, np.nan)
        value = volume * raw.vwap
        raw["avg_trading_value_20d"] = value.rolling(20, min_periods=20).mean()
        raw["volume_stability20"] = 1 / (1 + volume.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).rolling(20, min_periods=20).std(ddof=1))
        raw["missing_rate20"] = close.isna().astype(float).rolling(20, min_periods=1).mean()
        raw["suspension_proxy"] = (raw[["open", "high", "low", "close", "volume"]].isna().any(axis=1) | volume.le(0)).astype(float)
        raw["slippage_proxy"] = 1 / np.sqrt(value.where(value > 0))
        raw["_breadth_above"] = (close.notna() & raw.MA20.notna() & close.gt(raw.MA20)).astype(float)
        frames.append(raw)
    grid = pd.concat(frames, ignore_index=True)
    breadth = grid.groupby("date", as_index=False).agg(market_breadth20=("_breadth_above", "mean"))
    return grid, breadth


def market_features(breadth: pd.DataFrame, last_signal_day: str) -> pd.DataFrame:
    actual_dates = set(canonical_actual_calendar(last_signal_day))
    older = pd.read_csv(TWII_B2, usecols=["date", "close"])
    newer = pd.read_csv(TWII_POST, usecols=["date", "close"])
    twii = pd.concat([older, newer], ignore_index=True)
    twii["date"] = twii.date.astype(str).str[:10]
    twii["close"] = pd.to_numeric(twii.close, errors="coerce")
    twii = twii[twii.date.isin(actual_dates)].sort_values("date").drop_duplicates("date", keep="last")
    close = twii.close
    twii["TWII_ret20"] = close.pct_change(20, fill_method=None)
    twii["TWII_ret60"] = close.pct_change(60, fill_method=None)
    twii["TWII_close_vs_MA60"] = close / close.rolling(60, min_periods=60).mean() - 1
    twii["TWII_close_vs_MA120"] = close / close.rolling(120, min_periods=120).mean() - 1
    twii["market_volatility20"] = close.pct_change(fill_method=None).rolling(20, min_periods=20).std(ddof=1)
    twii["market_drawdown60"] = close / close.rolling(60, min_periods=20).max() - 1
    return twii[["date", "TWII_ret20", "TWII_ret60", "TWII_close_vs_MA60", "TWII_close_vs_MA120", "market_volatility20", "market_drawdown60"]].merge(breadth, on="date", how="left", validate="one_to_one")


def orthogonal_features(signal_dates: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    price = load_json_records(PRICE_CAPTURE)
    actual_calendar = sorted(price.date.unique())
    previous = {day: actual_calendar[index - 1] for index, day in enumerate(actual_calendar) if index}
    institutional = load_json_records(INSTITUTIONAL_CAPTURE).sort_values(["instrument", "date"])
    institutional["foreign_net_buy"] = pd.to_numeric(institutional.foreign_net_buy, errors="coerce")
    institutional["investment_trust_net_buy"] = pd.to_numeric(institutional.investment_trust_net_buy, errors="coerce")
    institutional["dealer_net_buy"] = pd.to_numeric(institutional.dealer_net_buy, errors="coerce")
    institutional["institutional_total_net_buy"] = institutional[["foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"]].sum(axis=1, min_count=3)
    for column in ["foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy", "institutional_total_net_buy"]:
        for window in [1, 3, 5, 10]:
            institutional[f"{column}_roll{window}"] = institutional.groupby("instrument")[column].transform(lambda values: values.rolling(window, min_periods=1).sum())
    institutional["institutional_total_net_buy_streak"] = institutional.groupby("instrument", group_keys=False)["institutional_total_net_buy"].apply(signed_streak)
    institutional["institutional_missing_flag"] = institutional[["foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"]].isna().any(axis=1).astype(float)
    institutional["institutional_delay_flag"] = 0.0
    institutional["institutional_flow_delay_days"] = 0.0
    institutional["institutional_flow_asof_missing_flag"] = 0.0

    margin = load_json_records(MARGIN_CAPTURE).sort_values(["instrument", "date"])
    margin["margin_balance"] = pd.to_numeric(margin.margin_purchase_today_balance, errors="coerce")
    margin["margin_balance_change"] = margin.margin_balance - pd.to_numeric(margin.margin_purchase_yesterday_balance, errors="coerce")
    margin["short_balance"] = pd.to_numeric(margin.short_sale_today_balance, errors="coerce")
    margin["short_balance_change"] = margin.short_balance - pd.to_numeric(margin.short_sale_yesterday_balance, errors="coerce")
    for column in ["margin_balance_change", "short_balance_change"]:
        for window in [1, 3, 5, 10]:
            margin[f"{column}_roll{window}"] = margin.groupby("instrument")[column].transform(lambda values: values.rolling(window, min_periods=1).sum())
    margin["margin_direction_proxy"] = np.sign(margin.margin_balance_change)
    margin["short_direction_proxy"] = np.sign(margin.short_balance_change)
    margin["margin_short_divergence_proxy"] = margin.margin_direction_proxy - margin.short_direction_proxy
    margin["margin_short_missing_flag"] = margin[["margin_balance", "margin_balance_change", "short_balance", "short_balance_change"]].isna().any(axis=1).astype(float)
    margin["margin_short_delay_flag"] = 0.0
    margin["margin_short_delay_days"] = 0.0
    margin["margin_short_asof_missing_flag"] = 0.0

    keys = pd.MultiIndex.from_product([signal_dates, sorted(price.instrument.unique())], names=["date", "instrument"]).to_frame(index=False)
    keys["orthogonal_trade_date"] = keys.date.map(previous)
    inst_columns = [column for column in feature_order() if column.startswith(("foreign_", "investment_trust_", "dealer_", "institutional_"))]
    margin_columns = [column for column in feature_order() if column.startswith(("margin_", "short_"))]
    inst = institutional[["date", "instrument", *inst_columns]].rename(columns={"date": "orthogonal_trade_date"})
    mar = margin[["date", "instrument", *margin_columns]].rename(columns={"date": "orthogonal_trade_date"})
    merged = keys.merge(inst, on=["orthogonal_trade_date", "instrument"], how="left", validate="one_to_one").merge(mar, on=["orthogonal_trade_date", "instrument"], how="left", validate="one_to_one")
    merged["available_at"] = merged.date
    audit = merged.groupby("date").agg(rows=("instrument", "size"), orthogonal_prior_date=("orthogonal_trade_date", "first"), missing_institutional=("foreign_net_buy", lambda values: int(values.isna().sum())), missing_margin=("margin_balance", lambda values: int(values.isna().sum()))).reset_index()
    return merged, audit


def build_features(model_a: pd.DataFrame, signal_dates: list[str], provider_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    historical = pd.read_parquet(B3_MODEL_A, columns=["date", "instrument", "raw_score", "qlib_rank"])
    historical["date"] = pd.to_datetime(historical.date).dt.strftime("%Y-%m-%d")
    historical = historical.rename(columns={"raw_score": "model_a_raw_score", "qlib_rank": "full_qlib_rank"})
    scores = pd.concat([historical[["date", "instrument", "model_a_raw_score", "full_qlib_rank"]], model_a[["date", "instrument", "model_a_raw_score", "full_qlib_rank"]]], ignore_index=True)
    scores = scores.sort_values(["instrument", "date"], kind="mergesort")
    scores["qlib_score_raw"] = scores.model_a_raw_score.astype(float)
    scores["qlib_rank"] = scores.full_qlib_rank.astype(float)
    group = scores.groupby("date", sort=False).qlib_score_raw
    scores["qlib_score_percentile_by_date"] = group.rank(pct=True, method="average", ascending=True)
    std = group.transform(lambda values: values.std(ddof=1))
    scores["qlib_score_zscore_by_date"] = ((scores.qlib_score_raw - group.transform("mean")) / std.replace(0, np.nan)).fillna(0.0)
    for lag in [1, 3, 5]:
        scores[f"rank_change_{lag}d"] = scores.groupby("instrument").qlib_rank.diff(lag)
    for threshold in [10, 30, 50]:
        scores[f"top{threshold}_flag"] = scores.qlib_rank.le(threshold).astype(float)
    scores["top30_streak"] = scores.groupby("instrument", group_keys=False).top30_flag.apply(positive_streak)
    scores["top50_streak"] = scores.groupby("instrument", group_keys=False).top50_flag.apply(positive_streak)
    base = scores[scores.date.isin(signal_dates)].copy()

    grid, breadth = price_grid(provider_root, signal_dates[-1])
    market = market_features(breadth, signal_dates[-1])
    price_columns = ["MA5", "MA10", "MA20", "MA60", "RSI14", "MACD", "Bollinger_position", "ret20", "volatility20", "volume_ratio20", "avg_trading_value_20d", "volume_stability20", "missing_rate20", "suspension_proxy", "slippage_proxy", "_rsi_ready"]
    base = base.merge(grid[["date", "instrument", *price_columns]], on=["date", "instrument"], how="left", validate="one_to_one")
    base = base.merge(market, on="date", how="left", validate="many_to_one")
    orthogonal, audit = orthogonal_features(signal_dates)
    base = base.merge(orthogonal, on=["date", "instrument"], how="left", validate="one_to_one", suffixes=("", "_orthogonal"))
    features = feature_order()
    finite = np.isfinite(base[features].to_numpy(dtype=float))
    base["feature_raw_complete_78"] = finite.all(axis=1) & base["_rsi_ready"].fillna(False).astype(bool)
    missing_features: list[str] = []
    for index, row in enumerate(finite):
        missing = list(np.asarray(features)[~row])
        if not bool(base.iloc[index]["_rsi_ready"]) and "RSI14" not in missing:
            missing.append("RSI14")
        missing_features.append("|".join(missing))
    base["raw_missing_features"] = missing_features
    base["signal_asof"] = base.date
    base["available_at"] = base.date
    base["source_feature_schema"] = rel(B2_SCHEMA)
    keep = ["date", "instrument", "signal_asof", "available_at", "feature_raw_complete_78", "raw_missing_features", *features, "source_feature_schema"]
    return base[keep].sort_values(["date", "instrument"]).reset_index(drop=True), audit


def tie_fixture() -> pd.DataFrame:
    frame = pd.DataFrame({"instrument": ["TW3008", "TW2330", "TW2317", "TW2454"], "b_score": [0.8, 0.8, 0.9, 0.8]})
    frame = frame.sort_values(["b_score", "instrument"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
    frame["expected_b_buy_rank"] = np.arange(1, len(frame) + 1)
    frame["rule"] = "b_score desc,instrument asc"
    return frame


def materialize_inputs(run_dir: Path, freeze_name: str) -> int:
    freeze_path = run_dir / freeze_name
    freeze = json.loads(freeze_path.read_text(encoding="utf-8")) if freeze_path.is_file() else {}
    if not freeze_path.is_file() or not str(freeze.get("status", "")).startswith("CLOSED_BEFORE_ANY"):
        raise RuntimeError("expected closed preoutcome freeze is missing")
    protocol = effective_protocol()
    scorer_binding = protocol.get("implementation_bindings", {}).get("label_free_model_a_scorer", {})
    if sha256(LABEL_FREE_SCORER) != scorer_binding.get("sha256"):
        raise RuntimeError("label-free scorer is missing, changed, or not frozen by amendment05")
    target_paths = [run_dir / name for name in ["MODEL_A_FULL_CROSS_SECTION.parquet", "FEATURE_ARTIFACT_78_RAW.parquet", "EXACT50_KEYSETS.csv", "FEATURE_COVERAGE_AUDIT.csv", "PIT_AUDIT.csv", "TIE_AWARE_RANK_FIXTURE.csv", "B19R2R_INPUT_MATERIALIZATION_STATE.json"]]
    if any(path.exists() for path in target_paths):
        raise RuntimeError("refusing to overwrite B19R2 input materialization")
    _, roles = date_roles()
    signal_dates = roles["POST_B18_RESEARCH_DEVELOPMENT"] + roles["PURGE_EMBARGO_NO_OUTCOME_USE"] + roles["SEALED_CONFIRMATION"]
    isolated_provider, isolated_manifest = build_isolated_model_a_provider(run_dir)
    global MODEL_A_PROVIDER
    original_provider = MODEL_A_PROVIDER
    MODEL_A_PROVIDER = isolated_provider
    try:
        model_a = frozen_model_a_inference(signal_dates[0], signal_dates[-1], signal_dates)
    finally:
        MODEL_A_PROVIDER = original_provider
    expected_keys = {(day, symbol) for day in signal_dates for symbol in provider_symbols(isolated_provider)}
    actual_keys = set(map(tuple, model_a[["date", "instrument"]].itertuples(index=False, name=None)))
    if actual_keys != expected_keys:
        raise RuntimeError(f"Model A full cross-section mismatch: missing={len(expected_keys-actual_keys)} extra={len(actual_keys-expected_keys)}")
    model_a.to_parquet(run_dir / "MODEL_A_FULL_CROSS_SECTION.parquet", index=False)
    features, pit = build_features(model_a, signal_dates, isolated_provider)
    features.to_parquet(run_dir / "FEATURE_ARTIFACT_78_RAW.parquet", index=False)
    pit["available_at_failure_rows"] = 0
    pit["non_trading_placeholder_20260710_in_any_lookback"] = False
    pit.to_csv(run_dir / "PIT_AUDIT.csv", index=False)
    coverage = features.groupby("date").agg(rows=("instrument", "size"), complete_78=("feature_raw_complete_78", "sum"), incomplete_78=("feature_raw_complete_78", lambda values: int((~values).sum()))).reset_index()
    coverage.to_csv(run_dir / "FEATURE_COVERAGE_AUDIT.csv", index=False)
    joined = model_a.merge(features[["date", "instrument", "feature_raw_complete_78"]], on=["date", "instrument"], how="left", validate="one_to_one")
    eligible = joined[(~joined.instrument.isin(EXCLUDED)) & joined.feature_raw_complete_78].copy()
    eligible = eligible.sort_values(["date", "model_a_raw_score", "instrument"], ascending=[True, False, True], kind="mergesort")
    exact50 = eligible.groupby("date", sort=True).head(50).copy()
    exact50["eligible_candidate_rank"] = exact50.groupby("date").cumcount() + 1
    if exact50.groupby("date").size().ne(50).any():
        raise RuntimeError("exact-50 candidate materialization failed")
    exact50[["date", "instrument", "eligible_candidate_rank", "full_qlib_rank", "model_a_raw_score", "signal_asof", "available_at"]].to_csv(run_dir / "EXACT50_KEYSETS.csv", index=False)
    tie_fixture().to_csv(run_dir / "TIE_AWARE_RANK_FIXTURE.csv", index=False)
    state = {
        "schema_version": "modelb.b19r2r.input_materialization_state.v1",
        "created_at": utc_now(),
        "preoutcome_freeze": fingerprint(freeze_path),
        "outcome_values_read_or_generated": False,
        "label_free_scorer_source": fingerprint(LABEL_FREE_SCORER),
        "label_group_configured": False,
        "DropnaLabel_or_label_expression_used": False,
        "non_trading_placeholder_20260710_removed_before_all_rolling": True,
        "isolated_model_a_provider": fingerprint(isolated_provider / "B19R2R_ISOLATED_PROVIDER_MANIFEST.json"),
        "isolated_model_a_provider_summary": isolated_manifest,
        "effective_protocol": fingerprint(AMENDMENT_05),
        "effective_future_training_split": fingerprint(EFFECTIVE_SPLIT),
        "base_split_consumed": False,
        "scorer_provider_root": rel(isolated_provider),
        "scorer_provider_feature_tree_sha256": isolated_manifest["clean_feature_tree_sha256"],
        "model_a_inference_performed": True,
        "model_b_or_b9_inference_performed": False,
        "training_performed": False,
        "tuning_performed": False,
        "replay_performed": False,
        "model_a_rows": len(model_a),
        "model_a_dates": model_a.date.nunique(),
        "features_rows": len(features),
        "features_dates": features.date.nunique(),
        "feature_complete_rows": int(features.feature_raw_complete_78.sum()),
        "exact50_rows": len(exact50),
        "exact50_dates": exact50.date.nunique(),
        "artifacts": {path.name: fingerprint(path) for path in target_paths[:-1]},
        "source_bindings": {rel(path): fingerprint(path) for path in (MODEL_A, MODEL_A_TRAINING_MANIFEST, isolated_provider / "B19R2R_ISOLATED_PROVIDER_MANIFEST.json", isolated_provider / "calendars/day.txt", B2_SCHEMA, B2_CALENDAR, FORMAL_EFFECTIVE_START, CALENDAR, PRICE_CAPTURE, INSTITUTIONAL_CAPTURE, MARGIN_CAPTURE, TWII_B2, TWII_POST, B3_MODEL_A, AMENDMENT_05, ATTEMPT_FAILURE_01, ATTEMPT_FAILURE_01_ERRATA, ROLLOVER_OBSERVATION_01)},
    }
    write_json(run_dir / "B19R2R_INPUT_MATERIALIZATION_STATE.json", state)
    print(json.dumps({"status": "INPUTS_MATERIALIZED_NO_OUTCOMES", "model_a_rows": len(model_a), "feature_complete": int(features.feature_raw_complete_78.sum()), "exact50_rows": len(exact50)}, ensure_ascii=False, indent=2))
    return 0


def feature_order() -> list[str]:
    features = list(json.loads(B2_SCHEMA.read_text(encoding="utf-8"))["feature_order"])
    calculated = hashlib.sha256(json.dumps(features, separators=(",", ":")).encode()).hexdigest()
    if len(features) != 78 or calculated != FEATURE_ORDER_SHA:
        raise RuntimeError(f"B2 feature order changed: count={len(features)} sha={calculated}")
    return features


def date_roles() -> tuple[pd.DataFrame, dict[str, list[str]]]:
    frame = pd.read_csv(CALENDAR, dtype=str)
    dates = frame["date"].tolist()
    if len(dates) != 90 or dates != sorted(set(dates)) or "2026-07-10" in dates:
        raise RuntimeError("B19R1 frozen actual-market calendar mismatch")
    mature = dates[:80]
    roles = {
        "POST_B18_RESEARCH_DEVELOPMENT": mature[:40],
        "PURGE_EMBARGO_NO_OUTCOME_USE": mature[40:50],
        "SEALED_CONFIRMATION": mature[50:80],
        "IMMATURE_TAIL_NOT_MATERIALIZED": dates[80:90],
    }
    expected = {
        "POST_B18_RESEARCH_DEVELOPMENT": ("2026-05-11", "2026-07-06", 40),
        "PURGE_EMBARGO_NO_OUTCOME_USE": ("2026-07-07", "2026-07-21", 10),
        "SEALED_CONFIRMATION": ("2026-07-22", "2026-09-01", 30),
        "IMMATURE_TAIL_NOT_MATERIALIZED": ("2026-09-02", "2026-09-15", 10),
    }
    rows: list[dict[str, Any]] = []
    for role, role_dates in roles.items():
        start, end, count = expected[role]
        if (role_dates[0], role_dates[-1], len(role_dates)) != (start, end, count):
            raise RuntimeError(f"date role mismatch for {role}")
        for day in role_dates:
            rows.append({"sequence": dates.index(day) + 1, "date": day, "role": role, "outcome_access": "DENY_BY_DEFAULT" if role == "SEALED_CONFIRMATION" else ("FORBIDDEN" if "EMBARGO" in role or "IMMATURE" in role else "DEVELOPMENT_ONLY")})
    return pd.DataFrame(rows).sort_values("sequence"), roles


def split_plan(_roles: dict[str, list[str]]) -> list[dict[str, Any]]:
    """Return the only authoritative split: the immutable amendment03 CSV."""
    if sha256(EFFECTIVE_SPLIT) != "3392b0537884b10f4e8a354eaede99da130a21b9b7c4636a1968f5615a01d8ca":
        raise RuntimeError("effective amendment03 split changed")
    return pd.read_csv(EFFECTIVE_SPLIT, dtype=str).fillna("").to_dict(orient="records")


def freeze_only() -> int:
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError(f"refusing to overwrite non-empty B19R2 output: {rel(OUT)}")
    OUT.mkdir(parents=True, exist_ok=True)
    features = feature_order()
    roles_frame, roles = date_roles()
    protected_before = fingerprints(PROTECTED)
    write_json(OUT / "protected_before.json", protected_before)
    roles_frame.to_csv(OUT / "DATE_ROLE_FREEZE.csv", index=False)
    pd.DataFrame(split_plan(roles)).to_csv(OUT / "NESTED_WALK_FORWARD_SPLIT_FREEZE.csv", index=False)

    source_paths = (
        CALENDAR, SOURCE_LINEAGE, SOURCE_CAPACITY, B19R1_REVIEW, B19_REVIEW, B18_REVIEW,
        B2_SCHEMA, B2_MANIFEST, B4_MANIFEST, B9_FREEZE, B9_REVIEW, MODEL_A,
        MODEL_A_TRAINING_MANIFEST,
    )
    freeze = {
        "schema_version": "modelb.b19r2.preoutcome_freeze.v1",
        "status": "CLOSED_BEFORE_ANY_B19R2_OUTCOME_READ",
        "freeze_created_at": utc_now(),
        "freeze_close_semantics": "File is written and fsync-completed before any B19R2 label, next-open, or next-close value is read or generated.",
        "new_model_identity": {
            "model_id": MODEL_ID,
            "model_family": "LightGBM.LGBMRanker",
            "objective": "lambdarank",
            "new_identity_not_b9": True,
            "parent_lineage": ["B2_78F_SEMANTICS", "B4_CANONICAL_10D_LABEL", "B9_RESEARCH_PARENT", "B18R2_FAILURE_DIAGNOSTIC"],
            "parent_weights_reused": False,
        },
        "feature_contract": {
            "feature_count": 78,
            "feature_order": features,
            "feature_order_sha256": FEATURE_ORDER_SHA,
            "raw_complete_case_only": True,
            "neutral_or_posthoc_fill_allowed": False,
            "available_at_lte_signal_asof_required": True,
            "future_label_execution_position_order_fields_forbidden": True,
        },
        "candidate_contract": {
            "frozen_model_a_full_cross_section_first": True,
            "excluded_before_capacity_and_top50": EXCLUDED,
            "daily_exact_rows": 50,
            "selection_order": "model_a_raw_score desc, instrument asc after exclusions and 78-feature complete-case filter",
            "full_qlib_rank_source": "frozen Model A complete cross-section before exclusions",
            "model_b_rerank_scope": "exact same eligible Model A 50 only",
            "model_b_tie_rule": "b_score desc, instrument asc",
        },
        "date_roles": {
            role: {"start": values[0], "end": values[-1], "actual_trading_days": len(values)}
            for role, values in roles.items()
        },
        "b18_exposed_policy": "All dates <=2026-05-07 are development/diagnostic only and can never be confirmatory for this identity.",
        "label_contract": {
            "horizon": "10 actual trading days",
            "rule": "stock close t+10 / close t - 1 minus TWII close t+10 / close t - 1; daily full-cross-section percentile; >=.90/.80/.70/.50 => 4/3/2/1 else 0",
            "outcome_window_crosses_any_split_boundary_allowed": False,
            "embargo_outcome_use": "FORBIDDEN_FOR_TRAINING_SELECTION_OR_THRESHOLDING",
        },
        "nested_walk_forward": split_plan(roles),
        "candidate_hyperparameter_space": {
            "num_leaves": [15, 31],
            "learning_rate": [0.02, 0.03],
            "n_estimators": [80, 120],
            "min_child_samples": [40, 80],
            "random_state": [42],
            "n_jobs": [2],
            "verbosity": [-1],
        },
        "unique_model_selection_rule": [
            "Reject any candidate failing a zero-tolerance engineering/PIT gate in any inner fold.",
            "Among survivors, maximize median inner-fold NDCG@10.",
            "Tie within 1e-12: maximize median inner-fold Rank IC.",
            "Tie within 1e-12: choose lower num_leaves, then lower n_estimators, lower learning_rate, then higher min_child_samples.",
            "Outer folds estimate development stability only and cannot change the selected hyperparameters.",
            "Sealed confirmation is opened once only after the model artifact, adapter, replay parameters and all gates are frozen.",
        ],
        "execution_and_accounting_contract": {
            "strategy": "top50_exit_one_worst_sell",
            "target_holdings": 10,
            "daily_max_buy": 1,
            "daily_max_sell": 1,
            "sell_before_buy_and_sell_opens_buy_slot": True,
            "execution": "next_open",
            "lot_size": 10,
            "commission_rate": 0.001425,
            "sell_tax_rate": 0.003,
            "price_fallback_allowed": False,
            "full_contribution": "realized net after sell commission/tax + all buy commissions + final open-position unrealized PnL",
        },
        "preregistered_numeric_quality_gates": {
            "confirmation_after_cost_return_delta_b_minus_a_min": 0.0,
            "confirmation_paired_moving_block_bootstrap_95pct_lower_bound_min": 0.0,
            "max_drawdown_noninferiority_b_minus_a_min": -0.02,
            "turnover_ratio_b_over_a_max": 1.25,
            "fee_tax_ratio_b_over_a_max": 1.25,
            "top5_abs_contribution_share_max": 0.45,
            "top5_abs_contribution_share_vs_a_max_delta": 0.03,
            "abs_contribution_hhi_max": 0.06,
            "abs_contribution_hhi_vs_a_max_delta": 0.01,
            "monthly_outperformance_fraction_min": 0.60,
            "negative_twii20_regime_return_delta_min": -0.02,
            "rank_ic_delta_b_minus_a_min": 0.01,
            "ndcg_at_10_delta_b_minus_a_min": 0.01,
            "engineering_tolerance": 0,
            "all_gates_jointly_required": True,
            "post_outcome_threshold_change_allowed": False,
        },
        "sealed_confirmation_policy": {
            "access": "DENY_BY_DEFAULT",
            "precheck_required_before_generation": True,
            "allowed_before_final_model_freeze": False,
            "manifest_validator_report_may_expose": ["path", "sha256", "bytes", "row_count", "date_count", "schema", "completeness_boolean"],
            "manifest_validator_report_forbidden": ["label values", "returns", "distribution", "summary statistics", "rank metrics", "replay metrics"],
            "one_time_evaluation_only": True,
        },
        "source_bindings": {rel(path): fingerprint(path) for path in source_paths},
        "safety": {
            "training_authorized": False,
            "model_b_or_b9_predict_allowed": False,
            "frozen_model_a_historical_inference_allowed": True,
            "tuning_allowed": False,
            "replay_allowed": False,
            "outcome_evaluation_allowed": False,
            "baseline_registry_default_latest_provider_frontend_db_broker_order_write_allowed": False,
            "production_allowed": False,
        },
        "protected_before": protected_before,
    }
    freeze_path = OUT / "B19R2_PREOUTCOME_FREEZE.json"
    raw = (json.dumps(freeze, ensure_ascii=True, indent=2, default=str) + "\n").encode("utf-8")
    with freeze_path.open("wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    write_json(OUT / "SEALED_CONFIRMATION_ACCESS_POLICY.json", freeze["sealed_confirmation_policy"])
    print(json.dumps({"status": freeze["status"], "freeze": rel(freeze_path), "sha256": sha256(freeze_path), "created_at": freeze["freeze_created_at"]}, ensure_ascii=False, indent=2))
    return 0


def repair_freeze_only() -> int:
    if OUT_R.exists() and any(OUT_R.iterdir()):
        raise RuntimeError(f"refusing to overwrite non-empty B19R2R output: {rel(OUT_R)}")
    OUT_R.mkdir(parents=True, exist_ok=True)
    features = feature_order()
    roles_frame, roles = date_roles()
    protected_before = fingerprints(PROTECTED)
    write_json(OUT_R / "protected_before.json", protected_before)
    roles_frame.to_csv(OUT_R / "DATE_ROLE_FREEZE.csv", index=False)
    splits = split_plan(roles)
    pd.DataFrame(splits).to_csv(OUT_R / "NESTED_WALK_FORWARD_SPLIT_FREEZE.csv", index=False)
    source_paths = (
        CALENDAR, SOURCE_LINEAGE, SOURCE_CAPACITY, B19R1_REVIEW, B19_REVIEW, B18_REVIEW,
        B2_SCHEMA, B2_MANIFEST, B4_MANIFEST, B9_FREEZE, B9_REVIEW, MODEL_A,
        MODEL_A_TRAINING_MANIFEST,
    )
    freeze = {
        "schema_version": "modelb.b19r2r.preoutcome_freeze.v1",
        "status": "CLOSED_BEFORE_ANY_B19R2R_OUTCOME_OR_MODEL_A_SCORE_READ",
        "freeze_created_at": utc_now(),
        "supersedes_failed_attempt": fingerprint(OUT / "B19R2_PREOUTCOME_ATTEMPT_FAILURE.json"),
        "old_freeze_retained": fingerprint(OUT / "B19R2_PREOUTCOME_FREEZE.json"),
        "new_model_identity": {
            "model_id": MODEL_ID_R,
            "model_family": "LightGBM.LGBMRanker",
            "objective": "lambdarank",
            "new_identity_not_b9_or_failed_b19r2": True,
            "parent_lineage": ["B2_78F_SEMANTICS", "B4_CANONICAL_10D_LABEL", "B9_RESEARCH_PARENT", "B18R2_FAILURE_DIAGNOSTIC"],
            "parent_weights_reused": False,
        },
        "label_free_model_a_scorer": {
            "implementation": "DataHandlerLP + QlibDataLoader(feature-only Alpha158 feature config)",
            "data_loader_groups": ["feature"],
            "label_group_configured": False,
            "learn_processors": [],
            "infer_processors": [],
            "DropnaLabel_allowed": False,
            "label_expression_allowed": False,
            "future_row_drop_allowed": False,
            "required_output": "150 rows on every frozen target date after explicit removal of 2026-07-10 non-trading placeholder",
            "scorer_source": rel(LABEL_FREE_SCORER),
            "scorer_source_sha256_at_freeze": sha256(LABEL_FREE_SCORER),
        },
        "feature_contract": {
            "feature_count": 78,
            "feature_order": features,
            "feature_order_sha256": FEATURE_ORDER_SHA,
            "canonical_semantics": "B2 FEATURE_SCHEMA and transforms",
            "raw_complete_case_only": True,
            "neutral_or_posthoc_fill_allowed": False,
            "available_at_lte_signal_asof_required": True,
            "future_label_execution_position_order_fields_forbidden": True,
        },
        "candidate_contract": {
            "frozen_model_a_full_cross_section_first": True,
            "excluded_before_capacity_and_top50": EXCLUDED,
            "daily_exact_rows": 50,
            "selection_order": "model_a_raw_score desc, instrument asc after exclusions and 78-feature complete-case filter",
            "full_qlib_rank_source": "frozen Model A complete cross-section before exclusions",
            "model_b_rerank_scope": "exact same eligible Model A 50 only",
            "model_b_tie_rule": "b_score desc, instrument asc",
        },
        "date_roles": {role: {"start": values[0], "end": values[-1], "actual_trading_days": len(values), "exact_dates": values} for role, values in roles.items()},
        "b18_exposed_policy": "All dates <=2026-05-07 are development/diagnostic only and never confirmatory for this identity.",
        "label_contract": {
            "horizon": "10 actual trading days from the B19R1 frozen calendar",
            "rule": "stock close t+10 / close t - 1 minus TWII close t+10 / close t - 1; daily full-cross-section percentile; >=.90/.80/.70/.50 => 4/3/2/1 else 0",
            "rank_universe": "frozen Model A full cross-section keys before complete-case and top50 filtering",
            "outcome_window_crosses_any_split_boundary_allowed": False,
            "embargo_outcome_use": "FORBIDDEN_FOR_TRAINING_SELECTION_OR_THRESHOLDING",
        },
        "nested_walk_forward": splits,
        "fold_audit_method": "For every fold, enumerate the exact frozen actual-trading dates after train_end; require the listed purge interval to equal the first 10 and validation_start to equal the next actual date. Calendar-day gaps remain non-trading and are explicitly allowed.",
        "candidate_hyperparameter_space": {
            "num_leaves": [15, 31], "learning_rate": [0.02, 0.03], "n_estimators": [80, 120],
            "min_child_samples": [40, 80], "random_state": [42], "n_jobs": [2], "verbosity": [-1]
        },
        "unique_model_selection_rule": [
            "Reject a candidate if any inner-fold engineering/PIT gate fails.",
            "Maximize median inner-fold NDCG@10; ties within 1e-12 maximize median Rank IC.",
            "Remaining ties choose lower num_leaves, lower n_estimators, lower learning_rate, then higher min_child_samples.",
            "Outer-fold metrics cannot change selected hyperparameters.",
            "Confirmation is opened once only after selected model hash, adapter hash, replay config and gates are frozen."
        ],
        "execution_and_accounting_contract": {
            "strategy": "top50_exit_one_worst_sell", "target_holdings": 10,
            "daily_max_buy": 1, "daily_max_sell": 1, "sell_before_buy_and_sell_opens_buy_slot": True,
            "execution": "next_open", "lot_size": 10, "commission_rate": 0.001425, "sell_tax_rate": 0.003,
            "price_fallback_allowed": False,
            "realized_contribution": "sell proceeds - original buy gross basis - sell commission - sell tax",
            "buy_commission_contribution": "negative sum of every buy commission, including still-open positions",
            "terminal_unrealized_contribution": "terminal close market value - gross buy basis of open positions",
            "reconciliation": "sum(realized contribution + buy commission contribution + terminal unrealized contribution) == final equity - initial equity within 1e-6",
        },
        "preregistered_statistical_method": {
            "series": "paired daily active return = A_PLUS_B daily return - A_ONLY daily return",
            "bootstrap": "moving block bootstrap with replacement",
            "block_length_actual_trading_days": 10,
            "replications": 10000,
            "seed": 20260916,
            "interval": "one-sided 95% lower confidence bound, empirical 0.05 quantile of bootstrap means",
            "gate": "lower bound strictly greater than 0",
            "missing_or_nonfinite_allowed": False,
        },
        "preregistered_numeric_quality_gates": {
            "confirmation_after_cost_return_delta_b_minus_a_min_exclusive": 0.0,
            "confirmation_bootstrap_one_sided_95pct_lower_bound_min_exclusive": 0.0,
            "max_drawdown_noninferiority_b_minus_a_min": -0.02,
            "turnover_ratio_b_over_a_max": 1.25,
            "fee_tax_ratio_b_over_a_max": 1.25,
            "top5_abs_contribution_share_max": 0.45,
            "top5_abs_contribution_share_vs_a_max_delta": 0.03,
            "abs_contribution_hhi_max": 0.06,
            "abs_contribution_hhi_vs_a_max_delta": 0.01,
            "monthly_outperformance_fraction_min": 0.60,
            "negative_twii20_regime_return_delta_min": -0.02,
            "rank_ic_delta_b_minus_a_min": 0.01,
            "ndcg_at_10_delta_b_minus_a_min": 0.01,
            "engineering_tolerance": 0,
            "all_gates_jointly_required": True,
            "post_outcome_threshold_change_allowed": False,
        },
        "sealed_confirmation_policy": {
            "access": "DENY_BY_DEFAULT", "protocol_precheck_required_before_generation": True,
            "final_model_freeze_required_before_evaluation": True,
            "materialization_manifest_may_expose": ["path", "sha256", "bytes", "row_count", "date_count", "schema", "completeness_boolean"],
            "materialization_manifest_forbidden": ["label values", "returns", "distribution", "summary statistics", "rank metrics", "replay metrics"],
            "one_time_evaluation_only": True,
        },
        "source_bindings": {rel(path): fingerprint(path) for path in source_paths},
        "safety": {
            "training_authorized": False, "model_b_or_b9_predict_allowed": False,
            "frozen_model_a_historical_inference_allowed_after_protocol_precheck_only": True,
            "tuning_allowed": False, "replay_allowed": False, "outcome_evaluation_allowed": False,
            "confirmation_outcome_materialization_allowed_after_protocol_precheck_only": True,
            "baseline_registry_default_latest_provider_frontend_db_broker_order_write_allowed": False,
            "production_allowed": False,
        },
        "protected_before": protected_before,
    }
    freeze_path = OUT_R / "B19R2R_PREOUTCOME_FREEZE.json"
    raw = (json.dumps(freeze, ensure_ascii=True, indent=2, default=str) + "\n").encode("utf-8")
    with freeze_path.open("wb") as handle:
        handle.write(raw); handle.flush(); os.fsync(handle.fileno())
    write_json(OUT_R / "SEALED_CONFIRMATION_ACCESS_POLICY.json", freeze["sealed_confirmation_policy"])
    print(json.dumps({"status": freeze["status"], "freeze": rel(freeze_path), "sha256": sha256(freeze_path), "created_at": freeze["freeze_created_at"]}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-only", action="store_true")
    parser.add_argument("--repair-freeze-only", action="store_true")
    parser.add_argument("--materialize-inputs", action="store_true")
    parser.add_argument("--repair-materialize-inputs", action="store_true")
    args = parser.parse_args()
    if args.freeze_only:
        return freeze_only()
    if args.repair_freeze_only:
        return repair_freeze_only()
    if args.materialize_inputs:
        return materialize_inputs(OUT, "B19R2_PREOUTCOME_FREEZE.json")
    if args.repair_materialize_inputs:
        return materialize_inputs(OUT_R, "B19R2R_PREOUTCOME_FREEZE.json")
    raise SystemExit("Select one explicit B19R2 stage")


if __name__ == "__main__":
    raise SystemExit(main())
