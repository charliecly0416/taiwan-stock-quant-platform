#!/usr/bin/env python3
"""Materialize B19R2R development and sealed outcome artifacts after precheck."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from modelb_b19r2r_twse_twii_20260915_adapter import materialize as materialize_twii_20260915


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916"
A6 = RUN / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_06.json"
A7 = RUN / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_07_ERRATA.json"
INPUT_STATE = RUN / "B19R2R_INPUT_MATERIALIZATION_STATE.json"
MODEL_A = RUN / "MODEL_A_FULL_CROSS_SECTION.parquet"
FEATURES = RUN / "FEATURE_ARTIFACT_78_RAW.parquet"
EXACT50 = RUN / "EXACT50_KEYSETS.csv"
DATE_ROLES = RUN / "DATE_ROLE_FREEZE.csv"
ACTUAL_CALENDAR = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r1_calendar_source_repair_20260916/FROZEN_ACTUAL_MARKET_CALENDAR.csv"
ISOLATED_PROVIDER = RUN / "isolated_model_a_provider_no_nontrading_placeholders"
TWII_B2 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b01_feature_input_contract_repair_20260913/twii_acquisition/TWII_NORMALIZED.csv"
TWII_POST = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b8_prospective_shadow_20260914/source_run_20260914_natural/yahoo_twii_20260914/twii.csv"
OUTPUT = RUN / "outcome_materialization_v1"
ADAPTER_CODE = ROOT / "scripts/modelb_b19r2r_twse_twii_20260915_adapter.py"
VALIDATOR_CODE = ROOT / "scripts/validate_modelb_b19r2r_sealed_outcomes.py"
PROTECTED_SNAPSHOT = RUN / "A6_PROTECTED_LATEST_BEFORE.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def provider_feature_tree_hash() -> tuple[str, int]:
    digest = hashlib.sha256()
    paths = sorted(ISOLATED_PROVIDER.glob("features/*/*.day.bin"), key=lambda path: path.relative_to(ISOLATED_PROVIDER).as_posix())
    for path in paths:
        relative_path = path.relative_to(ISOLATED_PROVIDER).as_posix()
        digest.update(f"{relative_path}\0{sha256(path)}\0{path.stat().st_size}\n".encode("ascii"))
    return digest.hexdigest(), len(paths)


def protected_latest_unchanged() -> bool:
    snapshot = json.loads(PROTECTED_SNAPSHOT.read_text(encoding="utf-8"))
    for relative_path, expected in snapshot.get("paths", {}).items():
        path = ROOT / relative_path
        if not path.is_file() or sha256(path) != expected.get("sha256") or path.stat().st_size != expected.get("bytes"):
            return False
    return True


def validate_protocol() -> dict[str, Any]:
    if not A6.is_file() or not A7.is_file():
        raise RuntimeError("A6 pre-outcome freeze or A7 errata is missing")
    protocol = json.loads(A6.read_text(encoding="utf-8"))
    errata = json.loads(A7.read_text(encoding="utf-8"))
    if protocol.get("status") != "CLOSED_BEFORE_ANY_A6_OUTCOME_VALUE_READ":
        raise RuntimeError("A6 pre-outcome freeze is not closed")
    if errata.get("status") != "ERRATA_CLOSED_BEFORE_MATERIALIZATION":
        raise RuntimeError("A7 disclosure errata is not closed")
    if errata.get("supersedes_a6_sha256") != sha256(A6):
        raise RuntimeError("A7 does not bind the retained A6")
    disclosure = errata.get("corrected_prior_source_row_read_disclosure", {})
    if disclosure.get("numeric_close_value_semantically_observed") is not True:
        raise RuntimeError("A7 does not disclose the prior TWII close observation")
    bindings = errata.get("implementation_bindings", {})
    expected = {
        "outcome_builder": Path(__file__),
        "twse_twii_adapter": ADAPTER_CODE,
        "metadata_validator": VALIDATOR_CODE,
    }
    for name, path in expected.items():
        if bindings.get(name, {}).get("sha256") != sha256(path):
            raise RuntimeError(f"A6 implementation binding mismatch: {name}")
    for item in protocol.get("source_bindings", []):
        path = ROOT / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise RuntimeError(f"A6 source binding mismatch: {item['path']}")
    provider_binding = protocol.get("directory_bindings", {}).get("isolated_provider_features", {})
    tree_hash, file_count = provider_feature_tree_hash()
    if tree_hash != provider_binding.get("canonical_tree_sha256") or file_count != provider_binding.get("file_count"):
        raise RuntimeError("A6 isolated provider feature tree binding mismatch")
    if not protected_latest_unchanged():
        raise RuntimeError("A6 protected/latest paths changed after freeze")
    return protocol


def provider_symbols() -> list[str]:
    symbols = sorted(line.split("\t", 1)[0].upper() for line in (ISOLATED_PROVIDER / "instruments/all.txt").read_text(encoding="utf-8").splitlines() if line)
    if len(symbols) != 150 or len(set(symbols)) != 150:
        raise RuntimeError("isolated provider does not contain exactly 150 instruments")
    return symbols


def decode_field(symbol: str, field: str, calendar: list[str]) -> pd.Series:
    values = np.fromfile(ISOLATED_PROVIDER / "features" / symbol.lower() / f"{field}.day.bin", dtype="<f4")
    if len(values) < 2:
        raise RuntimeError(f"invalid isolated field: {symbol}/{field}")
    start = int(values[0])
    data = values[1:].astype(float)
    if start < 0 or start + len(data) > len(calendar):
        raise RuntimeError(f"isolated field exceeds calendar: {symbol}/{field}")
    expanded = np.full(len(calendar), np.nan, dtype=float)
    expanded[start : start + len(data)] = data
    return pd.Series(expanded, index=calendar, dtype=float)


def load_stock_grid(actual_dates: list[str]) -> pd.DataFrame:
    provider_calendar = [line for line in (ISOLATED_PROVIDER / "calendars/day.txt").read_text(encoding="utf-8").splitlines() if line]
    parts = []
    for symbol in provider_symbols():
        open_values = decode_field(symbol, "open", provider_calendar)
        close_values = decode_field(symbol, "close", provider_calendar)
        frame = pd.DataFrame({"date": actual_dates, "instrument": symbol})
        frame["open"] = frame.date.map(open_values)
        frame["close"] = frame.date.map(close_values)
        parts.append(frame)
    grid = pd.concat(parts, ignore_index=True)
    if len(grid) != len(actual_dates) * 150 or grid.duplicated(["date", "instrument"]).any():
        raise RuntimeError("isolated stock outcome grid key mismatch")
    return grid


def load_twii(adapter_csv: Path, actual_dates: list[str]) -> pd.Series:
    frames = [
        pd.read_csv(TWII_B2, usecols=["date", "close"]),
        pd.read_csv(TWII_POST, usecols=["date", "close"]),
        pd.read_csv(adapter_csv, usecols=["date", "close"]),
    ]
    twii = pd.concat(frames, ignore_index=True)
    twii["date"] = twii.date.astype(str).str[:10]
    twii["close"] = pd.to_numeric(twii.close, errors="coerce")
    twii = twii[twii.date.isin(actual_dates)].sort_values("date").drop_duplicates("date", keep="last")
    if twii.date.tolist() != actual_dates or not np.isfinite(twii.close.to_numpy(dtype=float)).all():
        raise RuntimeError("TWII does not cover the exact frozen actual calendar")
    return twii.set_index("date").close


def build_outcomes(stock: pd.DataFrame, twii: pd.Series, dates: list[str], roles: pd.DataFrame) -> pd.DataFrame:
    index = {day: offset for offset, day in enumerate(dates)}
    mature_dates = roles[~roles.role.eq("IMMATURE_TAIL_NOT_MATERIALIZED")].date.tolist()
    keys = pd.read_parquet(MODEL_A, columns=["date", "instrument"])
    keys["date"] = keys.date.astype(str)
    keys = keys[keys.date.isin(mature_dates)].copy()
    if len(keys) != 12000 or keys.groupby("date").size().ne(150).any():
        raise RuntimeError("full-cross-section rank universe is not 80x150")
    prices = stock.set_index(["date", "instrument"])
    rows = []
    for signal_date in mature_dates:
        target_date = dates[index[signal_date] + 10]
        next_date = dates[index[signal_date] + 1]
        day = keys[keys.date.eq(signal_date)].copy()
        instruments = day.instrument.tolist()
        current_close = prices.loc[[(signal_date, symbol) for symbol in instruments], "close"].to_numpy(dtype=float)
        target_close = prices.loc[[(target_date, symbol) for symbol in instruments], "close"].to_numpy(dtype=float)
        next_open = prices.loc[[(next_date, symbol) for symbol in instruments], "open"].to_numpy(dtype=float)
        next_close = prices.loc[[(next_date, symbol) for symbol in instruments], "close"].to_numpy(dtype=float)
        terminal_close = prices.loc[[(("2026-09-02"), symbol) for symbol in instruments], "close"].to_numpy(dtype=float)
        stock_return = target_close / current_close - 1
        market_return = float(twii.loc[target_date] / twii.loc[signal_date] - 1)
        excess = stock_return - market_return
        if not all(np.isfinite(values).all() for values in [current_close, target_close, next_open, next_close, terminal_close, excess]):
            raise RuntimeError(f"nonfinite outcome source on {signal_date}")
        rank = pd.Series(excess).rank(pct=True, method="average").to_numpy(dtype=float)
        relevance = np.select([rank >= .90, rank >= .80, rank >= .70, rank >= .50], [4, 3, 2, 1], default=0).astype(int)
        role = roles.set_index("date").loc[signal_date, "role"]
        rows.append(pd.DataFrame({
            "date": signal_date,
            "instrument": instruments,
            "role": role,
            "target_date_10d": target_date,
            "next_trade_date": next_date,
            "terminal_mark_date": "2026-09-02",
            "stock_return_10d_canonical": stock_return,
            "market_return_10d_canonical": market_return,
            "future_excess_return_10d_canonical": excess,
            "future_excess_return_rank_10d_canonical": rank,
            "relevance_10d_top_heavy_canonical": relevance,
            "next_open": next_open,
            "next_close": next_close,
            "terminal_2026_09_02_close": terminal_close,
            "label_complete": True,
            "execution_grid_complete": True,
        }))
    output = pd.concat(rows, ignore_index=True)
    if len(output) != 12000 or output.duplicated(["date", "instrument"]).any():
        raise RuntimeError("outcome output key mismatch")
    return output


def artifact_metadata(path: Path, frame: pd.DataFrame) -> dict[str, Any]:
    completeness_columns = [column for column in ["label_complete", "execution_grid_complete"] if column in frame]
    return {
        "path": rel(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "row_count": len(frame),
        "date_count": frame.date.nunique(),
        "schema": list(frame.columns),
        "completeness_boolean": bool(frame[completeness_columns].all().all()) if completeness_columns else True,
    }


def write_parquet(path: Path, frame: pd.DataFrame, sealed: bool) -> dict[str, Any]:
    path.parent.mkdir(parents=True, mode=0o700 if sealed else 0o755, exist_ok=True)
    frame.to_parquet(path, index=False)
    os.chmod(path, 0o600 if sealed else 0o644)
    return artifact_metadata(path, frame)


LABEL_COLUMNS = [
    "date",
    "instrument",
    "role",
    "target_date_10d",
    "stock_return_10d_canonical",
    "market_return_10d_canonical",
    "future_excess_return_10d_canonical",
    "future_excess_return_rank_10d_canonical",
    "relevance_10d_top_heavy_canonical",
    "label_complete",
]
EXECUTION_GRID_COLUMNS = [
    "date",
    "instrument",
    "role",
    "next_trade_date",
    "next_open",
    "next_close",
    "terminal_mark_date",
    "terminal_2026_09_02_close",
    "execution_grid_complete",
]


def materialize() -> dict[str, Any]:
    protocol = validate_protocol()
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite outcome materialization directory")
    OUTPUT.mkdir(parents=True, mode=0o700)
    adapter_manifest = materialize_twii_20260915(OUTPUT / "twii_20260915_adapter")
    adapter_csv = ROOT / adapter_manifest["artifact"]["path"]

    dates = pd.read_csv(ACTUAL_CALENDAR, dtype=str).date.tolist()
    roles = pd.read_csv(DATE_ROLES, dtype=str)
    if len(dates) != 90 or dates[0] != "2026-05-11" or dates[-1] != "2026-09-15":
        raise RuntimeError("actual calendar is not the frozen 90-day calendar")
    stock = load_stock_grid(dates)
    twii = load_twii(adapter_csv, dates)
    outcomes = build_outcomes(stock, twii, dates, roles)

    development = outcomes[outcomes.role.eq("POST_B18_RESEARCH_DEVELOPMENT")].copy()
    embargo = outcomes[outcomes.role.eq("PURGE_EMBARGO_NO_OUTCOME_USE")].copy()
    confirmation = outcomes[outcomes.role.eq("SEALED_CONFIRMATION")].copy()
    if (len(development), len(embargo), len(confirmation)) != (6000, 1500, 4500):
        raise RuntimeError("outcome role split count mismatch")
    exact50 = pd.read_csv(EXACT50, dtype={"date": str, "instrument": str})[["date", "instrument"]]
    development_exact50 = exact50[exact50.date.isin(development.date.unique())].merge(
        development[["date", "instrument", "target_date_10d", "future_excess_return_10d_canonical", "future_excess_return_rank_10d_canonical", "relevance_10d_top_heavy_canonical", "label_complete"]],
        on=["date", "instrument"], how="left", validate="one_to_one",
    )
    if len(development_exact50) != 2000 or not development_exact50.label_complete.all():
        raise RuntimeError("development exact50 label join mismatch")

    artifacts = {
        "development_labels": write_parquet(OUTPUT / "development/DEVELOPMENT_LABELS.parquet", development[LABEL_COLUMNS], sealed=False),
        "development_exact50_labels": write_parquet(OUTPUT / "development/DEVELOPMENT_EXACT50_LABELS.parquet", development_exact50, sealed=False),
        "development_execution_grid": write_parquet(OUTPUT / "development/DEVELOPMENT_EXECUTION_GRID.parquet", development[EXECUTION_GRID_COLUMNS], sealed=False),
        "embargo_outcomes": write_parquet(OUTPUT / "sealed_embargo/EMBARGO_OUTCOMES.parquet", embargo[LABEL_COLUMNS], sealed=True),
        "embargo_execution_grid": write_parquet(OUTPUT / "sealed_embargo/EMBARGO_EXECUTION_GRID.parquet", embargo[EXECUTION_GRID_COLUMNS], sealed=True),
        "confirmation_outcomes": write_parquet(OUTPUT / "sealed_confirmation/CONFIRMATION_OUTCOMES.parquet", confirmation[LABEL_COLUMNS], sealed=True),
        "confirmation_execution_grid": write_parquet(OUTPUT / "sealed_confirmation/CONFIRMATION_EXECUTION_GRID.parquet", confirmation[EXECUTION_GRID_COLUMNS], sealed=True),
    }
    access_log = {
        "schema_version": "modelb.b19r2r.sealed_access_log.v1",
        "created_at": utc_now(),
        "events": [{"actor": "outcome_builder", "action": "WRITE_ONCE", "sealed_embargo": True, "sealed_confirmation": True}],
        "post_write_value_read_allowed": False,
        "confirmation_evaluation_performed": False,
    }
    access_log_path = OUTPUT / "SEALED_ACCESS_LOG.json"
    access_log_path.write_text(json.dumps(access_log, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    os.chmod(access_log_path, 0o600)
    manifest = {
        "schema_version": "modelb.b19r2r.outcome_materialization_manifest.v1",
        "status": "PASS_SEALED_NO_EVALUATION",
        "created_at": utc_now(),
        "protocol": {"path": rel(A6), "sha256": sha256(A6)},
        "protocol_errata": {"path": rel(A7), "sha256": sha256(A7)},
        "input_state": {"path": rel(INPUT_STATE), "sha256": sha256(INPUT_STATE)},
        "twii_adapter_manifest": {"path": rel(OUTPUT / "twii_20260915_adapter/TWII_20260915_ADAPTER_MANIFEST.json"), "sha256": sha256(OUTPUT / "twii_20260915_adapter/TWII_20260915_ADAPTER_MANIFEST.json")},
        "artifacts": artifacts,
        "role_policy": {
            "development_labels": "TRAINING_ALLOWED_ONLY_AFTER_SEPARATE_TRAINING_AUTHORIZATION",
            "embargo_outcomes": "FORBIDDEN_FOR_TRAINING_SELECTION_THRESHOLDING",
            "confirmation_outcomes": "DENY_BY_DEFAULT_UNTIL_FINAL_MODEL_AND_EVALUATION_FREEZE",
        },
        "execution_grid_policy": {
            "development_execution_grid": "DEVELOPMENT_DIAGNOSTIC_ONLY_AFTER_SEPARATE_AUTHORIZATION",
            "embargo_execution_grid": "SEALED_FORBIDDEN_FOR_TRAINING_SELECTION_THRESHOLDING",
            "confirmation_execution_grid": "DENY_BY_DEFAULT_UNTIL_FINAL_MODEL_AND_EVALUATION_FREEZE",
            "future_evaluator_must_consume_frozen_grid": True,
            "live_price_reread_allowed": False,
            "missing_price_fallback_allowed": False,
        },
        "sealed_access_log": {"path": rel(access_log_path), "sha256": sha256(access_log_path), "bytes": access_log_path.stat().st_size},
        "value_distribution_or_metric_exposed": False,
        "outcome_evaluation_performed": False,
        "training_performed": False,
        "model_b_or_b9_inference_performed": False,
        "replay_performed": False,
        "production_write_performed": False,
        "protected_latest_unchanged": protected_latest_unchanged(),
        "post_materialization_review_required": True,
    }
    if not manifest["protected_latest_unchanged"]:
        raise RuntimeError("A6 protected/latest paths changed during materialization")
    manifest_path = OUTPUT / "OUTCOME_MATERIALIZATION_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    os.chmod(manifest_path, 0o600)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--materialize-outcomes-sealed", action="store_true")
    args = parser.parse_args()
    if not args.materialize_outcomes_sealed:
        raise SystemExit("Select --materialize-outcomes-sealed")
    manifest = materialize()
    print(json.dumps({"status": manifest["status"], "outcome_evaluation_performed": False, "training_performed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
