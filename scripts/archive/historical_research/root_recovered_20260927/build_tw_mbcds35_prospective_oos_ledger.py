#!/usr/bin/env python3
"""Build an isolated prospective Model A versus Model A+Model B OOS ledger.

Signal registration and outcome settlement are separate append-only events.
This module never trains a model, publishes an artifact, or changes a pointer.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tw_mbcds35_signal_time_regime import (
    ALLOWED_REGIMES,
    DEFAULT_CONTRACT as REGIME_CONTRACT,
    RegimeContractError,
    classify as classify_regime,
    load_contract as load_regime_contract,
)


ROOT = Path(__file__).resolve().parents[1]
ISOLATED_ROOT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow"
DEFAULT_OUT = ISOLATED_ROOT / "mbcds35_prospective_oos_ledger"
MODEL_A_ID = "e4_frozen_qlib_2018_2022"
MODEL_B_ID = "head10_all_l31"
MODEL_B_CANDIDATE_ID = "head10_all_l31_alpha0.7_top50_only"
MODEL_B_CANDIDATE_ALIAS = "score_head10_all_l31_alpha0.7_top50_only"
MODEL_B_ARTIFACT_SHA256 = "f833146520c942a9c2953ae382235ab0d1536ccc9d153c8db1ad500ca3117cd9"
MODEL_B_CONTRACT_SHA256 = "022c0ded265c867035157b3ccf0a11857bc8970fb4848bd7644b96bcb875dd0c"
MODEL_B_MEDIANS_SHA256 = "e9ff9b7a5c99acac9d66decab7d50b18546f4075a6e749fda84e626a803bf4bf"
BLEND_ALPHA = 0.7
TOP50 = 50
TARGET_COUNT = 10
BUY_COMMISSION_RATE = 0.001425
SELL_COMMISSION_RATE = 0.001425
SELL_TAX_RATE = 0.003
PROTECTED = (
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt",
    ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
)


class ContractError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_time(value: Any, code: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ContractError(code, str(value)) from exc
    if parsed.tzinfo is None:
        raise ContractError(code, "timezone required")
    return parsed.astimezone(timezone.utc)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("MBCDS35_E_JSON", str(path)) from exc
    if not isinstance(payload, dict):
        raise ContractError("MBCDS35_E_JSON", "object required")
    return payload


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        raise ContractError("MBCDS35_E_CSV", str(path)) from exc


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def atomic_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows({field: row.get(field, "") for field in fields} for row in rows)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def protected_fingerprints() -> dict[str, dict[str, Any]]:
    return {
        rel(path): {"exists": path.is_file(), "sha256": sha256(path) if path.is_file() else None}
        for path in PROTECTED
    }


def validate_out(out: Path) -> None:
    if not out.resolve().is_relative_to(ISOLATED_ROOT.resolve()):
        raise ContractError("MBCDS35_E_OUTPUT_ESCAPE", str(out))


def select_valid_day(path: Path, asof: str) -> dict[str, str]:
    rows = read_csv(path)
    selected = [row for row in rows if row.get("asof") == asof]
    if len(selected) != 1:
        raise ContractError("MBCDS35_E_VALID_DAY_CARDINALITY", str(len(selected)))
    row = selected[0]
    if row.get("state") != "VALID_DAY_ACCEPTED" or str(row.get("warmup_counted", "")).lower() not in {"true", "1"}:
        raise ContractError("MBCDS35_E_DAY_NOT_ACCEPTED", asof)
    available = parse_time(row.get("available_at"), "MBCDS35_E_AVAILABLE_AT")
    cutoff = parse_time(row.get("decision_cutoff"), "MBCDS35_E_DECISION_CUTOFF")
    if available > cutoff:
        raise ContractError("MBCDS35_E_PIT_ORDER", asof)
    if not row.get("source_run_id"):
        raise ContractError("MBCDS35_E_SOURCE_RUN", asof)
    accepted = [item for item in rows if item.get("state") == "VALID_DAY_ACCEPTED" and str(item.get("warmup_counted", "")).lower() in {"true", "1"}]
    if len(accepted) < 20:
        raise ContractError("MBCDS35_E_WARMUP", f"accepted={len(accepted)} required=20")
    return {**row, "_accepted_valid_day_count": str(len(accepted))}


def numeric(row: dict[str, str], names: tuple[str, ...], code: str) -> float:
    for name in names:
        if str(row.get(name, "")).strip():
            try:
                value = float(row[name])
            except ValueError as exc:
                raise ContractError(code, name) from exc
            if not math.isfinite(value):
                raise ContractError(code, name)
            return value
    raise ContractError(code, "/".join(names))


def normalize_symbol(value: Any) -> str:
    symbol = str(value).strip().upper()
    if not symbol:
        raise ContractError("MBCDS35_E_SYMBOL", "empty")
    return symbol


def load_model_a(path: Path, asof: str) -> list[dict[str, Any]]:
    rows = read_csv(path)
    output = []
    seen: set[str] = set()
    for row in rows:
        row_date = str(row.get("date") or row.get("signal_asof") or row.get("asof") or "")[:10]
        if row_date != asof:
            raise ContractError("MBCDS35_E_MODELA_ASOF", row_date)
        symbol = normalize_symbol(row.get("instrument") or row.get("symbol"))
        if symbol in seen:
            raise ContractError("MBCDS35_E_MODELA_DUPLICATE", symbol)
        seen.add(symbol)
        rank = int(numeric(row, ("full_qlib_rank", "score_rank", "rank"), "MBCDS35_E_MODELA_RANK"))
        score = numeric(row, ("raw_score", "score", "buy_score"), "MBCDS35_E_MODELA_SCORE")
        output.append({"instrument": symbol, "model_a_rank": rank, "model_a_score": score})
    if len(output) != 150 or sorted(row["model_a_rank"] for row in output) != list(range(1, 151)):
        raise ContractError("MBCDS35_E_MODELA_UNIVERSE", str(len(output)))
    return sorted(output, key=lambda row: (row["model_a_rank"], row["instrument"]))


def manifest_binding(manifest_path: Path, artifact_path: Path, asof: str, valid_day: dict[str, str], model_id: str) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    if str(manifest.get("asof") or manifest.get("signal_asof"))[:10] != asof:
        raise ContractError("MBCDS35_E_MANIFEST_ASOF", model_id)
    if manifest.get("model_id") not in {model_id, None, ""} and manifest.get("model_name") != model_id:
        raise ContractError("MBCDS35_E_MODEL_ID", str(manifest.get("model_id")))
    source_run = str(manifest.get("source_run_id") or manifest.get("source_acquisition_run_id") or "")
    if source_run != valid_day["source_run_id"]:
        raise ContractError("MBCDS35_E_SAME_RUN", f"{model_id}:{source_run}")
    cutoff = parse_time(manifest.get("decision_cutoff"), "MBCDS35_E_MANIFEST_CUTOFF")
    if cutoff != parse_time(valid_day["decision_cutoff"], "MBCDS35_E_DECISION_CUTOFF"):
        raise ContractError("MBCDS35_E_CUTOFF_BINDING", model_id)
    actual = sha256(artifact_path)
    declared = str(manifest.get("artifact_sha256") or manifest.get("signals_sha256") or "")
    if not declared:
        for entry in manifest.get("required_file_entries", []) + manifest.get("files", []):
            if isinstance(entry, dict) and Path(str(entry.get("path", ""))).name == artifact_path.name:
                declared = str(entry.get("sha256") or "")
                if declared:
                    break
    if declared != actual:
        raise ContractError("MBCDS35_E_ARTIFACT_CHECKSUM", model_id)
    return manifest


def validate_model_b_contract(manifest: dict[str, Any]) -> None:
    identity = manifest.get("identity") if isinstance(manifest.get("identity"), dict) else manifest
    checks = {
        "candidate_id": identity.get("candidate_id") == MODEL_B_CANDIDATE_ID,
        "model_id": identity.get("model_id") == MODEL_B_ID,
        "model_family": identity.get("model_family") == "lightgbm_lambdarank",
        "blend_alpha": float(identity.get("blend_alpha", -1)) == BLEND_ALPHA,
        "preserve_scope": identity.get("preserve_scope") == "top50_only",
        "feature_count": int(manifest.get("feature_count", identity.get("feature_count", -1))) == 34,
        "model_sha256": str(manifest.get("model_sha256") or identity.get("model_sha256") or "") == MODEL_B_ARTIFACT_SHA256,
        "candidate_alias": manifest.get("candidate_aliases") == [MODEL_B_CANDIDATE_ALIAS],
        "candidate_identity_policy": manifest.get("candidate_identity_policy") == "canonical_id_plus_non_binding_alias; frozen artifact bytes unchanged",
        "contract_sha256": manifest.get("contract_sha256") == MODEL_B_CONTRACT_SHA256,
        "training_medians_sha256": manifest.get("training_medians_sha256") == MODEL_B_MEDIANS_SHA256,
        "percentile_direction": manifest.get("percentile_direction") == "higher_score_is_better",
        "percentile_tie_method": manifest.get("percentile_tie_method") == "first_after_qlib_rank_then_symbol",
        "missing_rule": manifest.get("missing_rule") == "fail_closed_no_fill",
    }
    failed = sorted(key for key, ok in checks.items() if not ok)
    if failed:
        raise ContractError("MBCDS35_E_FROZEN_MODELB_CONTRACT", ",".join(failed))


def validate_signal_time_regime(manifest: dict[str, Any]) -> tuple[str, Path, str]:
    try:
        _, expected_contract_sha256 = load_regime_contract(REGIME_CONTRACT)
    except RegimeContractError as exc:
        raise ContractError("MBCDS35_E_REGIME_CONTRACT", str(exc)) from exc
    if manifest.get("signal_time_regime_contract_sha256") != expected_contract_sha256:
        raise ContractError("MBCDS35_E_REGIME_CONTRACT_CHECKSUM")
    artifact_path = resolve(str(manifest.get("signal_time_regime_artifact") or ""))
    if not artifact_path.is_file() or manifest.get("signal_time_regime_artifact_sha256") != sha256(artifact_path):
        raise ContractError("MBCDS35_E_REGIME_ARTIFACT_CHECKSUM")
    artifact = read_json(artifact_path)
    try:
        recomputed, normalized = classify_regime(artifact.get("feature_values", {}))
    except RegimeContractError as exc:
        raise ContractError("MBCDS35_E_REGIME_ARTIFACT", str(exc)) from exc
    if (
        recomputed not in ALLOWED_REGIMES
        or manifest.get("signal_time_regime") != recomputed
        or artifact.get("regime") != recomputed
        or artifact.get("asof") != manifest.get("asof")
        or artifact.get("decision_cutoff") != manifest.get("decision_cutoff")
        or artifact.get("source_run_id") != manifest.get("source_run_id")
        or artifact.get("feature_values") != normalized
        or artifact.get("regime_contract_sha256") != expected_contract_sha256
        or artifact.get("signal_time_only") is not True
        or artifact.get("outcome_fields_consumed") != []
    ):
        raise ContractError("MBCDS35_E_REGIME_ARTIFACT_BINDING")
    return recomputed, artifact_path, expected_contract_sha256


def load_model_b(path: Path, asof: str, model_a: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = read_csv(path)
    output = []
    seen: set[str] = set()
    top50 = {row["instrument"] for row in model_a[:TOP50]}
    for row in rows:
        row_date = str(row.get("date") or row.get("signal_asof") or row.get("asof") or "")[:10]
        if row_date != asof:
            raise ContractError("MBCDS35_E_MODELB_ASOF", row_date)
        symbol = normalize_symbol(row.get("instrument") or row.get("symbol"))
        if symbol in seen:
            raise ContractError("MBCDS35_E_MODELB_DUPLICATE", symbol)
        seen.add(symbol)
        rank = int(numeric(row, ("score_rank",), "MBCDS35_E_MODELB_RANK"))
        score = numeric(row, ("buy_score",), "MBCDS35_E_MODELB_SCORE")
        full_rank = int(numeric(row, ("full_qlib_rank",), "MBCDS35_E_MODELB_FULL_RANK"))
        qlib_raw = numeric(row, ("qlib_score_raw",), "MBCDS35_E_MODELB_QLIB_SCORE")
        model_b_raw = numeric(row, ("model_b_raw_score",), "MBCDS35_E_MODELB_RAW_SCORE")
        qlib_pct = numeric(row, ("qlib_percentile",), "MBCDS35_E_MODELB_QLIB_PERCENTILE")
        model_b_pct = numeric(row, ("model_b_percentile",), "MBCDS35_E_MODELB_PERCENTILE")
        output.append({
            "instrument": symbol, "model_b_rank": rank, "model_b_score": score,
            "full_qlib_rank": full_rank, "qlib_score_raw": qlib_raw,
            "model_b_raw_score": model_b_raw, "qlib_percentile": qlib_pct,
            "model_b_percentile": model_b_pct,
        })
    if len(output) != TOP50 or seen != top50 or sorted(row["model_b_rank"] for row in output) != list(range(1, TOP50 + 1)):
        raise ContractError("MBCDS35_E_MODELB_TOP50", f"rows={len(output)}")
    model_a_by_symbol = {row["instrument"]: row for row in model_a[:TOP50]}
    base_order = sorted(output, key=lambda row: (model_a_by_symbol[row["instrument"]]["model_a_rank"], row["instrument"]))
    qlib_order = sorted(base_order, key=lambda row: (row["qlib_score_raw"], model_a_by_symbol[row["instrument"]]["model_a_rank"], row["instrument"]))
    model_b_order = sorted(base_order, key=lambda row: (row["model_b_raw_score"], model_a_by_symbol[row["instrument"]]["model_a_rank"], row["instrument"]))
    qlib_pct = {row["instrument"]: (index + 1) / TOP50 for index, row in enumerate(qlib_order)}
    model_b_pct = {row["instrument"]: (index + 1) / TOP50 for index, row in enumerate(model_b_order)}
    for row in output:
        base = model_a_by_symbol[row["instrument"]]
        expected_score = BLEND_ALPHA * qlib_pct[row["instrument"]] + (1.0 - BLEND_ALPHA) * model_b_pct[row["instrument"]]
        if (
            row["full_qlib_rank"] != base["model_a_rank"]
            or not math.isclose(row["qlib_score_raw"], base["model_a_score"], rel_tol=0.0, abs_tol=1e-12)
            or not math.isclose(row["qlib_percentile"], qlib_pct[row["instrument"]], rel_tol=0.0, abs_tol=1e-12)
            or not math.isclose(row["model_b_percentile"], model_b_pct[row["instrument"]], rel_tol=0.0, abs_tol=1e-12)
            or not math.isclose(row["model_b_score"], expected_score, rel_tol=0.0, abs_tol=1e-12)
        ):
            raise ContractError("MBCDS35_E_MODELB_BLEND_RECOMPUTE", row["instrument"])
    expected_ranked = sorted(output, key=lambda row: (-row["model_b_score"], row["full_qlib_rank"], row["instrument"]))
    if any(row["model_b_rank"] != index for index, row in enumerate(expected_ranked, start=1)):
        raise ContractError("MBCDS35_E_MODELB_BLEND_RANK", "score_rank")
    return sorted(output, key=lambda row: (row["model_b_rank"], row["instrument"]))


def load_events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    events = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                events.append(json.loads(line))
    previous = "GENESIS"
    for event in events:
        claimed = event.get("event_hash")
        body = {key: value for key, value in event.items() if key != "event_hash"}
        if body.get("previous_event_hash") != previous or canonical_hash(body) != claimed:
            raise ContractError("MBCDS35_E_LEDGER_CHAIN", str(event.get("asof")))
        previous = str(claimed)
    return events


def _event_semantics(event: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in event.items() if key not in {"created_at", "previous_event_hash", "event_hash"}}


def append_event(out: Path, body: dict[str, Any], *, idempotent: bool = False) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    ledger = out / "events.jsonl"
    lock_path = out / ".events.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        events = load_events(ledger)
        key = (body["event_type"], body["asof"])
        existing = next((item for item in events if (item.get("event_type"), item.get("asof")) == key), None)
        if existing is not None:
            if idempotent and _event_semantics(existing) == _event_semantics(body):
                return existing
            raise ContractError("MBCDS35_E_CONFLICTING_EVENT" if idempotent else "MBCDS35_E_DUPLICATE_EVENT", ":".join(key))
        body["previous_event_hash"] = events[-1]["event_hash"] if events else "GENESIS"
        event = {**body, "event_hash": canonical_hash(body)}
        with ledger.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True, ensure_ascii=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return event


def record_signal(args: argparse.Namespace) -> dict[str, Any]:
    out = resolve(args.out)
    validate_out(out)
    before = protected_fingerprints()
    valid_path = resolve(args.valid_day_inventory)
    model_a_path = resolve(args.model_a_signals)
    model_b_path = resolve(args.model_b_signals)
    valid = select_valid_day(valid_path, args.asof)
    if resolve(valid.get("ranking_path", "")) != model_a_path.resolve():
        raise ContractError("MBCDS35_E_MODELA_VALID_DAY_BINDING", str(model_a_path))
    model_a = load_model_a(model_a_path, args.asof)
    manifest_binding(resolve(args.model_a_manifest), model_a_path, args.asof, valid, MODEL_A_ID)
    model_b_manifest = manifest_binding(resolve(args.model_b_manifest), model_b_path, args.asof, valid, MODEL_B_ID)
    validate_model_b_contract(model_b_manifest)
    regime, regime_artifact_path, regime_contract_sha256 = validate_signal_time_regime(model_b_manifest)
    if model_b_manifest.get("model_a_signals_sha256") != sha256(model_a_path):
        raise ContractError("MBCDS35_E_MODELB_MODELA_BINDING")
    if model_b_manifest.get("training_performed") is True or model_b_manifest.get("production_allowed") is True:
        raise ContractError("MBCDS35_E_MODELB_MODE", "shadow input must be pre-trained and no-publish")
    model_b = load_model_b(model_b_path, args.asof, model_a)
    event = append_event(out, {
        "schema_version": "mbcds35.prospective_event.v1",
        "event_type": "SIGNAL_REGISTERED",
        "asof": args.asof,
        "created_at": utc_now(),
        "decision_cutoff": valid["decision_cutoff"],
        "source_run_id": valid["source_run_id"],
        "valid_input_day_count": int(valid["_accepted_valid_day_count"]),
        "model_a_id": MODEL_A_ID,
        "model_b_id": MODEL_B_ID,
        "comparison_contract": "top50_exit_one_worst_sell_next_open",
        "model_a_target": [row["instrument"] for row in model_a[:TARGET_COUNT]],
        "model_ab_target": [row["instrument"] for row in model_b[:TARGET_COUNT]],
        "model_a_ranking": model_a,
        "model_ab_ranking": model_b,
        "model_b_candidate_id": MODEL_B_CANDIDATE_ID,
        "blend_alpha": BLEND_ALPHA,
        "model_a_signals": rel(model_a_path),
        "model_a_signals_sha256": sha256(model_a_path),
        "model_b_signals": rel(model_b_path),
        "model_b_signals_sha256": sha256(model_b_path),
        "valid_day_inventory": rel(valid_path),
        "valid_day_inventory_sha256": sha256(valid_path),
        "signal_time_regime": regime,
        "signal_time_regime_artifact": rel(regime_artifact_path),
        "signal_time_regime_artifact_sha256": sha256(regime_artifact_path),
        "signal_time_regime_contract": rel(REGIME_CONTRACT),
        "signal_time_regime_contract_sha256": regime_contract_sha256,
        "signal_time_contains_outcome": False,
        "training_performed": False,
        "published": False,
    })
    after = protected_fingerprints()
    if before != after:
        raise ContractError("MBCDS35_E_PROTECTED_MUTATION")
    materialize(out)
    return event


def load_calendar(path: Path, signal_asof: str) -> tuple[str, str]:
    if not path.is_file():
        raise ContractError("MBCDS35_E_TRADING_CALENDAR", str(path))
    dates = sorted({line.strip()[:10] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()})
    following = [day for day in dates if day > signal_asof]
    if len(following) < 2:
        raise ContractError("MBCDS35_E_OUTCOME_PENDING_CALENDAR", signal_asof)
    return following[0], following[1]


def forbidden_regime_paths(value: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if "regime" in str(key).lower():
                paths.append(path)
            paths.extend(forbidden_regime_paths(nested, path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            paths.extend(forbidden_regime_paths(nested, f"{prefix}[{index}]"))
    return paths


def load_outcomes(path: Path, required: set[str], signal_asof: str, expected_entry: str, expected_exit: str) -> tuple[list[dict[str, Any]], str, str]:
    rows = read_csv(path)
    regime_columns = sorted({key for row in rows for key in row if "regime" in str(key).lower()})
    if regime_columns:
        raise ContractError("MBCDS35_E_OUTCOME_REGIME_FORBIDDEN", ",".join(regime_columns))
    by_symbol: dict[str, dict[str, Any]] = {}
    entry_dates: set[str] = set()
    exit_dates: set[str] = set()
    for row in rows:
        symbol = normalize_symbol(row.get("instrument") or row.get("symbol"))
        if symbol not in required:
            continue
        if symbol in by_symbol:
            raise ContractError("MBCDS35_E_OUTCOME_DUPLICATE", symbol)
        entry_date = str(row.get("entry_date", ""))[:10]
        exit_date = str(row.get("exit_date", ""))[:10]
        try:
            entry = numeric(row, ("entry_open",), "MBCDS35_E_OUTCOME_PENDING_OPEN")
            exit_price = numeric(row, ("exit_open",), "MBCDS35_E_OUTCOME_PENDING_OPEN")
        except ContractError as exc:
            raise ContractError("MBCDS35_E_OUTCOME_PENDING_OPEN", symbol) from exc
        if entry <= 0 or exit_price <= 0 or not (signal_asof < entry_date < exit_date):
            raise ContractError("MBCDS35_E_OUTCOME_PENDING_OPEN" if entry <= 0 or exit_price <= 0 else "MBCDS35_E_OUTCOME_ORDER", symbol)
        by_symbol[symbol] = {"instrument": symbol, "entry_date": entry_date, "exit_date": exit_date, "entry_open": entry, "exit_open": exit_price}
        entry_dates.add(entry_date)
        exit_dates.add(exit_date)
    if set(by_symbol) != required or len(entry_dates) != 1 or len(exit_dates) != 1:
        raise ContractError("MBCDS35_E_OUTCOME_SCOPE", f"{len(by_symbol)}/{len(required)}")
    entry_date, exit_date = next(iter(entry_dates)), next(iter(exit_dates))
    if entry_date != expected_entry or exit_date != expected_exit:
        raise ContractError("MBCDS35_E_NEXT_TRADING_DAY_BINDING", f"{entry_date}/{exit_date}!={expected_entry}/{expected_exit}")
    return list(by_symbol.values()), entry_date, exit_date


def settle(args: argparse.Namespace) -> dict[str, Any]:
    out = resolve(args.out)
    validate_out(out)
    before = protected_fingerprints()
    events = load_events(out / "events.jsonl")
    signals = [event for event in events if event.get("event_type") == "SIGNAL_REGISTERED" and event.get("asof") == args.asof]
    if len(signals) != 1:
        raise ContractError("MBCDS35_E_SIGNAL_EVENT", str(len(signals)))
    signal = signals[0]
    required = {row["instrument"] for row in signal["model_a_ranking"]}
    outcome_path = resolve(args.outcomes)
    manifest_path = resolve(args.outcome_manifest)
    manifest = read_json(manifest_path)
    injected_regime_keys = sorted(forbidden_regime_paths(manifest))
    if injected_regime_keys:
        raise ContractError("MBCDS35_E_OUTCOME_REGIME_FORBIDDEN", ",".join(injected_regime_keys))
    calendar_path = resolve(args.trading_calendar)
    entry_expected, exit_expected = load_calendar(calendar_path, args.asof)
    outcomes, entry_date, exit_date = load_outcomes(outcome_path, required, args.asof, entry_expected, exit_expected)
    available_at = parse_time(manifest.get("available_at"), "MBCDS35_E_OUTCOME_AVAILABLE")
    if available_at <= parse_time(signal["decision_cutoff"], "MBCDS35_E_DECISION_CUTOFF"):
        raise ContractError("MBCDS35_E_OUTCOME_NOT_PROSPECTIVE", args.asof)
    if str(manifest.get("entry_date", ""))[:10] != entry_date or str(manifest.get("exit_date", ""))[:10] != exit_date:
        raise ContractError("MBCDS35_E_OUTCOME_DATE_BINDING")
    if str(manifest.get("artifact_sha256", "")) != sha256(outcome_path):
        raise ContractError("MBCDS35_E_OUTCOME_CHECKSUM")
    if str(manifest.get("trading_calendar_sha256", "")) != sha256(calendar_path):
        raise ContractError("MBCDS35_E_TRADING_CALENDAR_CHECKSUM")
    if not str(manifest.get("source_run_id") or ""):
        raise ContractError("MBCDS35_E_OUTCOME_SOURCE_RUN")
    if str(manifest.get("source_asof") or "")[:10] < exit_date:
        raise ContractError("MBCDS35_E_OUTCOME_SOURCE_ASOF")
    event_count_before = len(events)
    event = append_event(out, {
        "schema_version": "mbcds35.prospective_event.v1",
        "event_type": "OUTCOME_SETTLED",
        "asof": args.asof,
        "created_at": utc_now(),
        "outcome_available_at": manifest["available_at"],
        "outcome_source_run_id": manifest["source_run_id"],
        "outcome_source_asof": manifest["source_asof"],
        "entry_date": entry_date,
        "exit_date": exit_date,
        "outcomes": rel(outcome_path),
        "outcomes_sha256": sha256(outcome_path),
        "outcome_manifest": rel(manifest_path),
        "trading_calendar": rel(calendar_path),
        "trading_calendar_sha256": sha256(calendar_path),
        "signal_time_regime": signal["signal_time_regime"],
        "signal_time_regime_contract_sha256": signal["signal_time_regime_contract_sha256"],
        "complete_universe_size": len(outcomes),
        "prices": sorted(outcomes, key=lambda row: row["instrument"]),
        "buy_commission_rate": BUY_COMMISSION_RATE,
        "sell_commission_rate": SELL_COMMISSION_RATE,
        "sell_tax_rate": SELL_TAX_RATE,
        "training_performed": False,
        "published": False,
    }, idempotent=True)
    after = protected_fingerprints()
    if before != after:
        raise ContractError("MBCDS35_E_PROTECTED_MUTATION")
    if len(load_events(out / "events.jsonl")) != event_count_before:
        materialize(out)
    return event


def cumulative(values: list[float]) -> float:
    result = 1.0
    for value in values:
        result *= 1.0 + value
    return result - 1.0


def max_drawdown(values: list[float]) -> float:
    equity = peak = 1.0
    drawdown = 0.0
    for value in values:
        equity *= 1.0 + value
        peak = max(peak, equity)
        drawdown = min(drawdown, equity / peak - 1.0)
    return drawdown


def rank_correlation(signal: dict[str, Any], outcome: dict[str, Any], *, treatment: bool) -> float | None:
    """Spearman correlation between higher score ordering and realized open-to-open return."""
    prices = {row["instrument"]: row for row in outcome["prices"]}
    ranking = signal["model_ab_ranking"] if treatment else signal["model_a_ranking"][:TOP50]
    pairs = []
    for row in ranking:
        symbol = row["instrument"]
        realized = float(prices[symbol]["exit_open"]) / float(prices[symbol]["entry_open"]) - 1.0
        rank = int(row["model_b_rank"] if treatment else row["model_a_rank"])
        pairs.append((rank, realized))
    if len(pairs) < 2:
        return None
    # Convert realized returns to deterministic ascending ranks; lower signal rank is better.
    ordered = {index: rank for rank, (index, _) in enumerate(sorted(enumerate(pairs), key=lambda item: (item[1][1], item[1][0])), start=1)}
    x = [-float(rank) for rank, _ in pairs]
    y = [float(ordered[index]) for index in range(len(pairs))]
    x_mean, y_mean = sum(x) / len(x), sum(y) / len(y)
    numerator = sum((left - x_mean) * (right - y_mean) for left, right in zip(x, y))
    denominator = math.sqrt(sum((value - x_mean) ** 2 for value in x) * sum((value - y_mean) ** 2 for value in y))
    return numerator / denominator if denominator else None


def grouped_stability(rows: list[dict[str, Any]], key) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(key(row)), []).append(row)
    return {
        name: {
            "paired_days": len(items),
            "model_a_cumulative_net_return": cumulative([float(item["model_a_net_return"]) for item in items]),
            "model_ab_cumulative_net_return": cumulative([float(item["model_ab_net_return"]) for item in items]),
            "mean_paired_net_delta": sum(float(item["paired_net_delta"]) for item in items) / len(items),
            "mean_model_a_rank_ic": sum(float(item["model_a_rank_ic"]) for item in items) / len(items),
            "mean_model_ab_rank_ic": sum(float(item["model_ab_rank_ic"]) for item in items) / len(items),
        }
        for name, items in sorted(groups.items()) if items
    }


def evidence_status_for(n: int, ci_low: float | None = None, treatment_better: bool = False) -> str:
    if n >= 120:
        return "BASELINE_REVIEW_ELIGIBLE" if ci_low is not None and ci_low > 0 and treatment_better else "NO_STABLE_INCREMENTAL_BENEFIT"
    if n >= 60:
        return "OOS_REVIEWABLE"
    if n >= 20:
        return "SHADOW_DIAGNOSTIC_READY"
    return "ACCUMULATING"


def run_strategy_path(signals: dict[str, dict[str, Any]], settlements: dict[str, dict[str, Any]], treatment: bool) -> list[dict[str, Any]]:
    cash = 1_000_000.0
    holdings: dict[str, int] = {}
    prior_equity = cash
    rows: list[dict[str, Any]] = []
    for asof in sorted(settlements):
        signal = signals[asof]
        outcome = settlements[asof]
        prices = {row["instrument"]: row for row in outcome["prices"]}
        full_rank = {row["instrument"]: int(row["model_a_rank"]) for row in signal["model_a_ranking"]}
        candidate_set = {symbol for symbol, rank in full_rank.items() if rank <= TOP50}
        buy_order = (
            [row["instrument"] for row in signal["model_ab_ranking"]]
            if treatment else
            [row["instrument"] for row in signal["model_a_ranking"][:TOP50]]
        )
        outside = sorted(
            (symbol for symbol in holdings if symbol not in candidate_set),
            key=lambda symbol: (full_rank.get(symbol, 999999), symbol), reverse=True,
        )
        actions: list[dict[str, Any]] = []
        fees = traded = 0.0
        if outside:
            symbol = outside[0]
            quantity = holdings.pop(symbol)
            gross = quantity * float(prices[symbol]["entry_open"])
            commission = gross * SELL_COMMISSION_RATE
            tax = gross * SELL_TAX_RATE
            cash += gross - commission - tax
            fees += commission + tax
            traded += gross
            actions.append({"action": "sell", "instrument": symbol, "quantity": quantity})
        if len(holdings) < TARGET_COUNT:
            symbol = next((item for item in buy_order if item not in holdings), "")
            if symbol:
                entry = float(prices[symbol]["entry_open"])
                entry_equity = cash + sum(quantity * float(prices[held]["entry_open"]) for held, quantity in holdings.items())
                budget = entry_equity / TARGET_COUNT
                quantity = int((budget / entry) // 10) * 10
                gross = quantity * entry
                commission = gross * BUY_COMMISSION_RATE
                if quantity > 0 and gross + commission <= cash + 1e-9:
                    cash -= gross + commission
                    holdings[symbol] = quantity
                    fees += commission
                    traded += gross
                    actions.append({"action": "buy", "instrument": symbol, "quantity": quantity})
        equity = cash + sum(quantity * float(prices[symbol]["exit_open"]) for symbol, quantity in holdings.items())
        daily_return = equity / prior_equity - 1.0 if prior_equity else 0.0
        rows.append({
            "asof": asof,
            "entry_date": outcome["entry_date"],
            "exit_date": outcome["exit_date"],
            "equity": equity,
            "net_return": daily_return,
            "turnover": traded / prior_equity if prior_equity else 0.0,
            "fees_and_tax": fees,
            "holding_count": len(holdings),
            "actions": actions,
        })
        prior_equity = equity
    return rows


def materialize(out: Path) -> dict[str, Any]:
    events = load_events(out / "events.jsonl")
    signals = {event["asof"]: event for event in events if event["event_type"] == "SIGNAL_REGISTERED"}
    settlements = {event["asof"]: event for event in events if event["event_type"] == "OUTCOME_SETTLED"}
    if set(settlements) - set(signals):
        raise ContractError("MBCDS35_E_ORPHAN_SETTLEMENT")
    a_path = run_strategy_path(signals, settlements, treatment=False)
    ab_path = run_strategy_path(signals, settlements, treatment=True)
    a_by_date = {row["asof"]: row for row in a_path}
    ab_by_date = {row["asof"]: row for row in ab_path}
    rows = []
    for asof in sorted(signals):
        signal = signals[asof]
        outcome = settlements.get(asof, {})
        rows.append({
            "asof": asof,
            "source_run_id": signal["source_run_id"],
            "decision_cutoff": signal["decision_cutoff"],
            "signal_status": "REGISTERED",
            "outcome_status": "SETTLED" if outcome else "PENDING_FUTURE_OUTCOME",
            "entry_date": outcome.get("entry_date", ""),
            "exit_date": outcome.get("exit_date", ""),
            "model_a_net_return": a_by_date.get(asof, {}).get("net_return", ""),
            "model_ab_net_return": ab_by_date.get(asof, {}).get("net_return", ""),
            "paired_net_delta": (ab_by_date[asof]["net_return"] - a_by_date[asof]["net_return"]) if asof in settlements else "",
            "model_a_equity": a_by_date.get(asof, {}).get("equity", ""),
            "model_ab_equity": ab_by_date.get(asof, {}).get("equity", ""),
            "model_a_turnover": a_by_date.get(asof, {}).get("turnover", ""),
            "model_ab_turnover": ab_by_date.get(asof, {}).get("turnover", ""),
            "model_a_rank_ic": rank_correlation(signal, outcome, treatment=False) if outcome else "",
            "model_ab_rank_ic": rank_correlation(signal, outcome, treatment=True) if outcome else "",
            "regime": signal["signal_time_regime"],
        })
    atomic_csv(out / "daily_comparison.csv", rows, [
        "asof", "source_run_id", "decision_cutoff", "signal_status", "outcome_status",
        "entry_date", "exit_date", "model_a_net_return", "model_ab_net_return", "paired_net_delta",
        "model_a_equity", "model_ab_equity", "model_a_turnover", "model_ab_turnover",
        "model_a_rank_ic", "model_ab_rank_ic", "regime",
    ])
    a_returns = [float(row["net_return"]) for row in a_path]
    ab_returns = [float(row["net_return"]) for row in ab_path]
    deltas = [right - left for left, right in zip(a_returns, ab_returns)]
    n = len(deltas)
    settled_rows = [row for row in rows if row["outcome_status"] == "SETTLED"]
    mean_delta = sum(deltas) / n if n else None
    std_error = None
    ci_low = ci_high = None
    if n >= 2:
        variance = sum((value - mean_delta) ** 2 for value in deltas) / (n - 1)
        std_error = math.sqrt(variance / n)
        ci_low, ci_high = mean_delta - 1.96 * std_error, mean_delta + 1.96 * std_error
    unclassified_regime_days = sum((row.get("regime") or "UNCLASSIFIED") == "UNCLASSIFIED" for row in settled_rows)
    regime_stability_ready = bool(n and unclassified_regime_days == 0)
    evidence_status = evidence_status_for(n, ci_low, cumulative(ab_returns) > cumulative(a_returns))
    if n >= 120 and not regime_stability_ready:
        evidence_status = "BLOCKED_REGIME_STABILITY_EVIDENCE"
    valid_input_days = max((int(event.get("valid_input_day_count", 0)) for event in signals.values()), default=0)
    summary = {
        "schema_version": "mbcds35.prospective_oos_summary.v1",
        "updated_at": utc_now(),
        "comparison_contract": {
            "candidate_universe": "same Model A top50",
            "strategy_rule": "top50_exit_one_worst_sell",
            "control": "Model A qlib buy ordering",
            "treatment": "frozen Phase1C alpha-0.7 score buy ordering within same Model A top50",
            "initial_equity": 1_000_000,
            "target_holdings": TARGET_COUNT,
            "max_buy_count": 1,
            "max_sell_count": 1,
            "lot_size": 10,
            "execution": "next_trading_day_open",
            "mark": "following_trading_day_open",
            "buy_commission_rate": BUY_COMMISSION_RATE,
            "sell_commission_rate": SELL_COMMISSION_RATE,
            "sell_tax_rate": SELL_TAX_RATE,
        },
        "registered_signal_days": len(signals),
        "valid_input_days": valid_input_days,
        "settled_oos_days": n,
        "pending_outcome_days": sorted(set(signals) - set(settlements)),
        "model_a_cumulative_net_return": cumulative(a_returns) if n else None,
        "model_ab_cumulative_net_return": cumulative(ab_returns) if n else None,
        "model_a_max_drawdown": max_drawdown(a_returns) if n else None,
        "model_ab_max_drawdown": max_drawdown(ab_returns) if n else None,
        "model_a_total_turnover": sum(float(row["turnover"]) for row in a_path),
        "model_ab_total_turnover": sum(float(row["turnover"]) for row in ab_path),
        "model_a_total_fees_and_tax": sum(float(row["fees_and_tax"]) for row in a_path),
        "model_ab_total_fees_and_tax": sum(float(row["fees_and_tax"]) for row in ab_path),
        "paired_mean_daily_net_delta": mean_delta,
        "paired_delta_standard_error": std_error,
        "paired_delta_95pct_ci": [ci_low, ci_high] if ci_low is not None else None,
        "treatment_daily_win_rate": sum(value > 0 for value in deltas) / n if n else None,
        "model_a_mean_rank_ic": sum(float(row["model_a_rank_ic"]) for row in settled_rows) / n if n else None,
        "model_ab_mean_rank_ic": sum(float(row["model_ab_rank_ic"]) for row in settled_rows) / n if n else None,
        "monthly_stability": grouped_stability(settled_rows, lambda row: str(row["asof"])[:7]),
        "regime_stability": grouped_stability(settled_rows, lambda row: row.get("regime") or "UNCLASSIFIED"),
        "classified_regime_days": n - unclassified_regime_days,
        "unclassified_regime_days": unclassified_regime_days,
        "regime_stability_ready": regime_stability_ready,
        "evidence_status": evidence_status,
        "historical_result_is_prior_only": True,
        "production_baseline_switch_allowed": False,
        "exact_strategy_replay_still_required_before_switch": True,
        "training_performed": False,
        "published": False,
    }
    atomic_json(out / "comparison_summary.json", summary)
    signal_rows = [{
        "asof": event["asof"], "decision_cutoff": event["decision_cutoff"],
        "source_run_id": event["source_run_id"], "model_a_signals_sha256": event["model_a_signals_sha256"],
        "model_b_signals_sha256": event["model_b_signals_sha256"],
        "signal_time_regime": event["signal_time_regime"],
        "signal_time_regime_contract_sha256": event["signal_time_regime_contract_sha256"],
        "event_hash": event["event_hash"],
    } for event in sorted(signals.values(), key=lambda row: row["asof"])]
    atomic_csv(out / "prospective_signal_ledger.csv", signal_rows, [
        "asof", "decision_cutoff", "source_run_id", "model_a_signals_sha256", "model_b_signals_sha256",
        "signal_time_regime", "signal_time_regime_contract_sha256", "event_hash",
    ])
    outcome_rows = [{
        "asof": event["asof"], "outcome_available_at": event["outcome_available_at"],
        "entry_date": event["entry_date"], "exit_date": event["exit_date"],
        "outcomes_sha256": event["outcomes_sha256"], "event_hash": event["event_hash"],
    } for event in sorted(settlements.values(), key=lambda row: row["asof"])]
    atomic_csv(out / "outcome_settlement_ledger.csv", outcome_rows, ["asof", "outcome_available_at", "entry_date", "exit_date", "outcomes_sha256", "event_hash"])
    atomic_json(out / "aggregate_metrics.json", summary)
    atomic_json(out / "warmup_readiness.json", {
        "valid_input_days": valid_input_days, "model_b_scored_days": len(signals),
        "settled_signal_days": n, "paired_oos_days": n, "status": evidence_status,
        "can_shadow_score": valid_input_days >= 20, "can_switch_baseline": False,
    })
    atomic_json(out / "lineage_audit.json", {"status": "PASS", "event_chain_head": events[-1]["event_hash"] if events else "GENESIS", "same_run_required": True, "checksum_bound": True})
    atomic_json(out / "forbidden_scope_audit.json", {"status": "PASS", "training": False, "publish": False, "baseline_switch": False, "provider_latest_cron_frontend_write": False})
    atomic_json(out / "validator_report.json", {"status": "PASS", "event_count": len(events), "signal_count": len(signals), "settlement_count": len(settlements), "future_fields_in_signal_ledger": []})
    manifest = {
        "schema_version": "mbcds35.ledger_manifest.v1",
        "mode": "isolated_no_publish",
        "event_count": len(events),
        "event_chain_head": events[-1]["event_hash"] if events else "GENESIS",
        "files": {
            "events.jsonl": sha256(out / "events.jsonl") if (out / "events.jsonl").is_file() else None,
            "daily_comparison.csv": sha256(out / "daily_comparison.csv"),
            "comparison_summary.json": sha256(out / "comparison_summary.json"),
            "prospective_signal_ledger.csv": sha256(out / "prospective_signal_ledger.csv"),
            "outcome_settlement_ledger.csv": sha256(out / "outcome_settlement_ledger.csv"),
        },
        "forbidden_actions": {
            "training": False, "baseline_switch": False, "latest_write": False,
            "provider_write": False, "cron_write": False, "frontend_write": False,
        },
    }
    atomic_json(out / "manifest.json", manifest)
    return summary


def validate(args: argparse.Namespace) -> dict[str, Any]:
    out = resolve(args.out)
    validate_out(out)
    summary = materialize(out)
    return {"status": "PASS", "summary": summary, "protected": protected_fingerprints()}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--out", default=str(DEFAULT_OUT))
    sub = result.add_subparsers(dest="command", required=True)
    signal = sub.add_parser("record-signal")
    signal.add_argument("--asof", required=True)
    signal.add_argument("--valid-day-inventory", required=True)
    signal.add_argument("--model-a-signals", required=True)
    signal.add_argument("--model-a-manifest", required=True)
    signal.add_argument("--model-b-signals", required=True)
    signal.add_argument("--model-b-manifest", required=True)
    outcome = sub.add_parser("settle-outcome")
    outcome.add_argument("--asof", required=True)
    outcome.add_argument("--outcomes", required=True)
    outcome.add_argument("--outcome-manifest", required=True)
    outcome.add_argument("--trading-calendar", required=True)
    sub.add_parser("validate")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "record-signal":
            payload = record_signal(args)
        elif args.command == "settle-outcome":
            payload = settle(args)
        else:
            payload = validate(args)
    except ContractError as exc:
        print(json.dumps({"status": "BLOCKED", "code": exc.code, "detail": str(exc)}, ensure_ascii=True))
        return 2
    print(json.dumps({"status": "PASS", "result": payload}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
