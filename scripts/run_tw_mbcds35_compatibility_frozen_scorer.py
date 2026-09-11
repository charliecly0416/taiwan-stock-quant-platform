#!/usr/bin/env python3
"""Score the frozen compatibility Model B in an isolated, no-publish run."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tw_mbcds35_signal_time_regime import (
    ALLOWED_REGIMES,
    DEFAULT_CONTRACT as REGIME_CONTRACT,
    REQUIRED_FIELDS as REGIME_FIELDS,
    RegimeContractError,
    classify as classify_regime,
    load_contract as load_regime_contract,
)

ROOT = Path(__file__).resolve().parents[1]
ISOLATED_ROOT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow"
ARTIFACT_ROOT = ISOLATED_ROOT / "model_artifact_phase1c_20260905"
MODEL = ARTIFACT_ROOT / "phase1c_head10_all_l31_model.pkl"
CONTRACT = ARTIFACT_ROOT / "model_contract.json"
MEDIANS = ARTIFACT_ROOT / "training_medians.json"
EXPECTED = {
    MODEL: "f833146520c942a9c2953ae382235ab0d1536ccc9d153c8db1ad500ca3117cd9",
    CONTRACT: "022c0ded265c867035157b3ccf0a11857bc8970fb4848bd7644b96bcb875dd0c",
    MEDIANS: "e9ff9b7a5c99acac9d66decab7d50b18546f4075a6e749fda84e626a803bf4bf",
}
MODEL_ID = "head10_all_l31"
CANDIDATE_ID = "head10_all_l31_alpha0.7_top50_only"
ALPHA = 0.7


class ScoringError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def verify_frozen_artifact(model: Path, contract: Path, medians: Path) -> tuple[list[str], dict[str, str]]:
    paths = {MODEL: model, CONTRACT: contract, MEDIANS: medians}
    actual: dict[str, str] = {}
    for canonical, path in paths.items():
        if not path.is_file():
            raise ScoringError(f"frozen_artifact_missing:{path}")
        actual[canonical.name] = sha256(path)
        if actual[canonical.name] != EXPECTED[canonical]:
            raise ScoringError(f"frozen_artifact_checksum_mismatch:{canonical.name}")
    payload = json.loads(contract.read_text(encoding="utf-8"))
    features = payload.get("features")
    if not isinstance(features, list) or len(features) != 34 or len(set(features)) != 34:
        raise ScoringError("feature_contract_not_exact_34")
    identity = payload.get("identity", {})
    if identity.get("model_id") != MODEL_ID or identity.get("candidate_id") != CANDIDATE_ID:
        raise ScoringError("frozen_model_identity_mismatch")
    median_payload = json.loads(medians.read_text(encoding="utf-8"))
    if list(median_payload) != features or any(not math.isfinite(float(median_payload[name])) for name in features):
        raise ScoringError("training_medians_contract_mismatch")
    return features, actual


def score(
    *, asof: str, feature_frame: Path, feature_manifest: Path, model_a_signals: Path,
    source_ledger: Path, output: Path, model: Path = MODEL, contract: Path = CONTRACT,
    medians: Path = MEDIANS, regime_contract: Path = REGIME_CONTRACT,
) -> dict[str, Any]:
    if not output.resolve().is_relative_to(ISOLATED_ROOT.resolve()):
        raise ScoringError("output_outside_isolated_root")
    features, artifact_hashes = verify_frozen_artifact(model, contract, medians)
    frame_manifest = json.loads(feature_manifest.read_text(encoding="utf-8"))
    ledger = json.loads(source_ledger.read_text(encoding="utf-8"))
    if frame_manifest.get("asof") != asof or ledger.get("asof") != asof or ledger.get("status") != "PASS":
        raise ScoringError("asof_or_source_ledger_not_ready")
    if frame_manifest.get("source_run_id") != ledger.get("acquisition_run_id"):
        raise ScoringError("same_run_mismatch")
    try:
        source_available = datetime.fromisoformat(str(ledger.get("combined_available_at")).replace("Z", "+00:00"))
        ledger_cutoff = datetime.fromisoformat(str(ledger.get("decision_cutoff")).replace("Z", "+00:00"))
        manifest_cutoff = datetime.fromisoformat(str(frame_manifest.get("decision_cutoff")).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ScoringError("source_availability_or_cutoff_invalid") from exc
    if source_available.tzinfo is None or ledger_cutoff.tzinfo is None or manifest_cutoff.tzinfo is None:
        raise ScoringError("source_availability_or_cutoff_timezone_required")
    if source_available > ledger_cutoff or manifest_cutoff != ledger_cutoff:
        raise ScoringError("source_available_at_or_cutoff_binding_invalid")
    if frame_manifest.get("status") != "PASS" or frame_manifest.get("can_score") is not True:
        raise ScoringError("feature_manifest_not_ready")
    if frame_manifest.get("feature_frame_sha256") != sha256(feature_frame):
        raise ScoringError("feature_frame_checksum_mismatch")
    if frame_manifest.get("model_a_signals_sha256") != sha256(model_a_signals):
        raise ScoringError("model_a_signals_checksum_mismatch")
    if frame_manifest.get("source_ledger_sha256") != sha256(source_ledger):
        raise ScoringError("source_ledger_checksum_mismatch")
    if frame_manifest.get("feature_order") != features:
        raise ScoringError("feature_order_mismatch")

    try:
        _, regime_contract_sha256 = load_regime_contract(regime_contract)
    except RegimeContractError as exc:
        raise ScoringError(str(exc)) from exc
    if frame_manifest.get("signal_time_regime_contract_sha256") != regime_contract_sha256:
        raise ScoringError("signal_time_regime_contract_checksum_mismatch")
    regime_path = resolve(str(frame_manifest.get("signal_time_regime_artifact") or ""))
    if not regime_path.is_file() or frame_manifest.get("signal_time_regime_artifact_sha256") != sha256(regime_path):
        raise ScoringError("signal_time_regime_artifact_checksum_mismatch")
    regime_artifact = json.loads(regime_path.read_text(encoding="utf-8"))
    if (
        regime_artifact.get("asof") != asof
        or regime_artifact.get("decision_cutoff") != frame_manifest.get("decision_cutoff")
        or regime_artifact.get("source_available_at") != ledger.get("combined_available_at")
        or regime_artifact.get("source_run_id") != frame_manifest.get("source_run_id")
        or regime_artifact.get("feature_frame_sha256") != sha256(feature_frame)
        or regime_artifact.get("regime_contract_sha256") != regime_contract_sha256
        or regime_artifact.get("signal_time_only") is not True
        or regime_artifact.get("outcome_fields_consumed") != []
    ):
        raise ScoringError("signal_time_regime_binding_invalid")

    model_a = pd.read_csv(model_a_signals)
    frame = pd.read_csv(feature_frame)
    for data in (model_a, frame):
        data["date"] = data.get("date", data.get("asof", "")).astype(str).str[:10]
        data["instrument"] = data["instrument"].astype(str).str.upper()
    if set(model_a["date"]) != {asof} or len(model_a) != 150 or model_a["instrument"].nunique() != 150:
        raise ScoringError("model_a_cross_section_not_150")
    rank_col = next((name for name in ("full_qlib_rank", "score_rank", "rank") if name in model_a), None)
    score_col = next((name for name in ("raw_score", "score", "buy_score") if name in model_a), None)
    if rank_col is None or score_col is None:
        raise ScoringError("model_a_rank_or_score_missing")
    model_a[rank_col] = pd.to_numeric(model_a[rank_col], errors="coerce")
    model_a[score_col] = pd.to_numeric(model_a[score_col], errors="coerce")
    if sorted(model_a[rank_col].tolist()) != list(range(1, 151)):
        raise ScoringError("model_a_rank_not_permutation")
    top50 = model_a.nsmallest(50, rank_col).sort_values([rank_col, "instrument"])

    if list(frame.columns) != ["date", "instrument", *features] or set(frame["date"]) != {asof}:
        raise ScoringError("feature_frame_schema_or_asof_mismatch")
    if len(frame) != 150 or frame["instrument"].nunique() != 150 or set(frame["instrument"]) != set(model_a["instrument"]):
        raise ScoringError("feature_frame_universe_mismatch")
    regime_values: dict[str, float] = {}
    for field in REGIME_FIELDS:
        values = pd.to_numeric(frame[field], errors="coerce")
        finite = values[np.isfinite(values.to_numpy(dtype=float))]
        unique = finite.unique()
        if len(finite) != len(frame) or len(unique) != 1:
            raise ScoringError(f"signal_time_regime_cross_section_invalid:{field}")
        regime_values[field] = float(unique[0])
    try:
        recomputed_regime, normalized_values = classify_regime(regime_values)
    except RegimeContractError as exc:
        raise ScoringError(str(exc)) from exc
    if (
        recomputed_regime not in ALLOWED_REGIMES
        or regime_artifact.get("regime") != recomputed_regime
        or regime_artifact.get("feature_values") != normalized_values
        or frame_manifest.get("signal_time_regime") != recomputed_regime
    ):
        raise ScoringError("signal_time_regime_recompute_mismatch")
    matrix = frame.set_index("instrument").loc[top50["instrument"], features].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(matrix.to_numpy(dtype=float)).all():
        raise ScoringError("feature_missing_nan_or_infinite")

    with model.open("rb") as stream:
        estimator = pickle.load(stream)
    raw = np.asarray(estimator.predict(matrix[features]), dtype=float)
    if raw.shape != (50,) or not np.isfinite(raw).all():
        raise ScoringError("model_prediction_invalid")
    scored = top50[["instrument", rank_col, score_col]].copy()
    scored.columns = ["instrument", "full_qlib_rank", "qlib_score_raw"]
    scored["date"] = asof
    scored["model_b_raw_score"] = raw
    # Higher scores are better. method=first is deterministic after qlib-rank/symbol ordering.
    scored["qlib_percentile"] = scored["qlib_score_raw"].rank(pct=True, method="first", ascending=True)
    scored["model_b_percentile"] = scored["model_b_raw_score"].rank(pct=True, method="first", ascending=True)
    scored["buy_score"] = ALPHA * scored["qlib_percentile"] + (1.0 - ALPHA) * scored["model_b_percentile"]
    scored = scored.sort_values(["buy_score", "full_qlib_rank", "instrument"], ascending=[False, True, True])
    scored["score_rank"] = range(1, 51)
    scored = scored[["date", "instrument", "score_rank", "buy_score", "full_qlib_rank", "qlib_score_raw", "model_b_raw_score", "qlib_percentile", "model_b_percentile"]]

    output.mkdir(parents=True, exist_ok=True)
    signals = output / "model_b_shadow_signals.csv"
    scored.to_csv(signals, index=False)
    manifest = {
        "schema_version": "mbcds35.compatibility_frozen_score.v1", "asof": asof,
        "source_run_id": ledger["acquisition_run_id"], "decision_cutoff": ledger["decision_cutoff"],
        "model_id": MODEL_ID, "candidate_id": CANDIDATE_ID,
        "candidate_aliases": ["score_head10_all_l31_alpha0.7_top50_only"],
        "candidate_identity_policy": "canonical_id_plus_non_binding_alias; frozen artifact bytes unchanged",
        "model_family": "lightgbm_lambdarank",
        "blend_alpha": ALPHA, "preserve_scope": "top50_only", "feature_count": 34,
        "feature_order": features, "model_sha256": artifact_hashes[MODEL.name],
        "contract_sha256": artifact_hashes[CONTRACT.name], "training_medians_sha256": artifact_hashes[MEDIANS.name],
        "artifact_sha256": sha256(signals), "feature_frame_sha256": sha256(feature_frame),
        "model_a_signals_sha256": sha256(model_a_signals), "source_ledger_sha256": sha256(source_ledger),
        "percentile_direction": "higher_score_is_better", "percentile_tie_method": "first_after_qlib_rank_then_symbol",
        "missing_rule": "fail_closed_no_fill", "training_performed": False, "production_allowed": False,
        "signal_time_regime": recomputed_regime,
        "signal_time_regime_artifact": rel(regime_path),
        "signal_time_regime_artifact_sha256": sha256(regime_path),
        "signal_time_regime_contract": rel(regime_contract),
        "signal_time_regime_contract_sha256": regime_contract_sha256,
        "published": False, "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    atomic_json(output / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--feature-frame", required=True)
    parser.add_argument("--feature-manifest", required=True)
    parser.add_argument("--model-a-signals", required=True)
    parser.add_argument("--source-ledger", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        result = score(asof=args.asof, feature_frame=resolve(args.feature_frame), feature_manifest=resolve(args.feature_manifest),
                       model_a_signals=resolve(args.model_a_signals), source_ledger=resolve(args.source_ledger), output=resolve(args.out))
    except (OSError, ValueError, json.JSONDecodeError, ScoringError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=True))
        return 2
    print(json.dumps({"status": "PASS", "manifest": result}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
