"""Shared readonly checks for configured identities and persisted signals."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .artifacts import sha256
from .config import path


def validate_registries(config: dict) -> None:
    registry = yaml.safe_load(path('configs/tw_modular_registry.yaml').read_text())
    policy = yaml.safe_load(path('configs/tw_replay_window_policy.yaml').read_text())
    artifacts = yaml.safe_load(path('configs/tw_product_artifact_registry.yaml').read_text())
    if registry.get('schema_version') != 'tw.clean.registry.v1' or set(registry['models']) != set(config['models']):
        raise ValueError('REGISTRY_MODEL_SET_MISMATCH')
    for name, spec in config['models'].items():
        registered = registry['models'][name]
        if any(spec.get(k) != registered.get(k) for k in ('canonical_id', 'role', 'production_allowed')):
            raise ValueError('REGISTRY_MODEL_IDENTITY_MISMATCH')
        if spec['role'] == 'shadow' and (set(registered['consumers']) & {'paper', 'agent'}
                or registered.get('mainline_blocking') is not False or registered.get('no_apply') is not True):
            raise ValueError('REGISTRY_SHADOW_BOUNDARY_INVALID')
    if (policy.get('strategy') != config['strategy'] or policy.get('execution') != config['execution']
            or policy.get('comparison_no_apply') is not True or policy.get('max_calendar_days') != 730
            or policy['models']['model_a_plus_b'].get('paper_allowed') is not False):
        raise ValueError('REPLAY_POLICY_MISMATCH')
    if artifacts.get('candidate_publish_allowed') is not False:
        raise ValueError('CANDIDATE_PUBLISH_FORBIDDEN')
    expected = {'signals': 'signals/{model}/{asof}', 'intents': 'intents/{model}/{asof}',
                'daily': 'daily/{asof}/{run_id}', 'agent': 'agent_daily_prompt/{asof}',
                'failed_signals': 'failed_runs/signals/{model}/{asof}/{run_id}',
                'shadow_feature_delta': 'shadow_features/{asof}/FEATURE_ARTIFACT_DELTA.parquet',
                'signal_history': 'history/{batch}/signals/{model}/{asof}',
                'signal_history_run': 'history/{batch}/run.json'}
    if any(artifacts.get(k) != v for k, v in expected.items()):
        raise ValueError('ARTIFACT_REGISTRY_LAYOUT_MISMATCH')


def verify_file(filename: str | Path, expected: str) -> Path:
    target = path(filename)
    if not target.is_file():
        raise ValueError(f"ASSET_MISSING: {target.name}")
    if not expected or sha256(target) != expected:
        raise ValueError(f"ASSET_CHECKSUM_MISMATCH: {target.name}")
    return target


def validate_baseline(config: dict) -> None:
    descriptor = config.get("baseline_descriptor")
    if not descriptor:
        return  # Explicit small fixture/custom configurations have no product admission.
    authority = yaml.safe_load(path(descriptor).read_text())["active_baseline"]
    model = authority["model_a"]; stage = config["model_stages"]["model_a_frozen"]
    expected = {"model_path": model["artifact_path"], "model_sha256": model["artifact_sha256"],
                "fit_start": model["training_start"], "fit_end": model["training_end"]}
    if any(str(stage.get(key)) != str(value) for key, value in expected.items()):
        raise ValueError("BASELINE_IDENTITY_MISMATCH")
    default = config.get("product", {}).get("default_model")
    spec = config.get("models", {}).get(default, {})
    if (spec.get("canonical_id") != model["model_id"] or spec.get("role") != "baseline"
            or spec.get("production_allowed") is not True
            or config.get("strategy") != authority["strategy_rule"]
            or config.get("execution") != authority["execution_price_mode"]):
        raise ValueError("BASELINE_ADMISSION_MISMATCH")
    if any(item.get("role") == "shadow" and item.get("production_allowed") is not False
           for item in config.get("models", {}).values()):
        raise ValueError("SHADOW_PRODUCTION_ADMISSION_FORBIDDEN")
    validate_registries(config)


def pipeline_fingerprint(config: dict, model: str) -> str:
    spec = config["models"][model]
    identity = {"model": spec, "stages": {name: config["model_stages"].get(name, {})
                                          for name in spec.get("stages", [])},
                "datasets": config.get("datasets", {}), "universe": config.get("universe"),
                "universe_file": config.get("universe_file")}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, default=str).encode()).hexdigest()


def pipeline_context(config: dict, model: str) -> dict:
    """Only public validation inputs, never credentials or process environments."""
    return {"model_stages": {name: config['model_stages'].get(name, {})
                             for name in config['models'][model].get('stages', [])},
            **{name: config.get(name) for name in ('datasets', 'universe', 'universe_file')}}


def historical_config(config: dict, model: str, context: dict) -> dict:
    result = deepcopy(config)
    dynamic = {'model_a_frozen': {'provider_uri', 'selection_prices', 'selection_universe'},
               'b19r2r_frozen': {'feature_delta', 'feature_delta_sha256'}}
    expected = set(config['models'][model].get('stages', []))
    if (not isinstance(context, dict) or not isinstance(context.get('model_stages'), dict)
            or set(context['model_stages']) != expected
            or not all(isinstance(stage, dict) for stage in context['model_stages'].values())):
        raise ValueError('SIGNAL_HISTORY_CONTEXT_INVALID')
    for name, old in context['model_stages'].items():
        current = config['model_stages'].get(name, {})
        stable = lambda stage: {key: value for key, value in stage.items() if key not in dynamic.get(name, set())}
        if stable(old) != stable(current):
            raise ValueError('SIGNAL_HISTORY_MODEL_IDENTITY_MISMATCH')
        result['model_stages'][name] = old
    for key in ('datasets', 'universe', 'universe_file'):
        result[key] = context.get(key)
    validate_baseline(result)
    stage = result['model_stages'].get('b19r2r_frozen', {})
    if 'b19r2r_frozen' in expected and stage.get('feature_delta'):
        verify_file(stage['feature_delta'], stage.get('feature_delta_sha256'))
    return result


def validate_signal_rows(frame: pd.DataFrame, asof: str) -> None:
    if frame.empty or not {"date", "instrument", "score", "rank"}.issubset(frame):
        raise ValueError("SIGNAL_EMPTY_OR_SCHEMA_INVALID")
    if frame[["date", "instrument"]].isna().any().any() or frame.duplicated(["date", "instrument"]).any():
        raise ValueError("SIGNAL_DUPLICATE_OR_NULL_KEY")
    if not frame.date.astype(str).eq(asof).all():
        raise ValueError("SIGNAL_ASOF_MISMATCH")
    if not frame.instrument.astype(str).str.fullmatch(r"TW\d{4,6}").all():
        raise ValueError("SIGNAL_INSTRUMENT_INVALID")
    values = frame[["score", "rank"]].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(values.to_numpy()).all() or sorted(values['rank']) != list(range(1, len(frame) + 1)):
        raise ValueError("SIGNAL_SCORE_OR_RANK_INVALID")
    if not values.sort_values("rank")["score"].is_monotonic_decreasing:
        raise ValueError("SIGNAL_SCORE_RANK_DISAGREEMENT")
    forbidden = [name for name in frame if name.startswith(("future_", "forward_", "label_"))
                 or name in {"action", "holding", "position", "target_position", "target_weight",
                             "order_qty", "execution_price", "realized_return", "realized_pnl"}]
    if forbidden:
        raise ValueError("SIGNAL_FORBIDDEN_FIELDS: " + ",".join(forbidden))


def validate_full_ranks(frame: pd.DataFrame, ranks: dict, candidates: dict, spec: dict) -> None:
    if "model_a_frozen" not in spec.get("stages", []):
        return
    if (not isinstance(ranks, dict) or not ranks
            or any(not isinstance(key, str) or not key.startswith("TW")
                   or not key[2:].isdigit() or not 4 <= len(key[2:]) <= 6
                   or type(value) is not int for key, value in ranks.items())
            or sorted(ranks.values()) != list(range(1, len(ranks) + 1))):
        raise ValueError("SIGNAL_FULL_RANK_MAP_INVALID")
    if (not isinstance(candidates, dict) or not set(candidates).issubset(ranks)
            or any(type(value) is not int for value in candidates.values())
            or sorted(candidates.values()) != list(range(1, len(candidates) + 1))):
        raise ValueError("SIGNAL_CANDIDATE_MAP_INVALID")
    for field, mapping in (("candidate_rank", candidates), ("full_qlib_rank", ranks)):
        expected = frame.instrument.map(mapping)
        if field not in frame or expected.isna().any() or not expected.eq(frame[field]).all():
            raise ValueError("SIGNAL_FULL_RANK_MISMATCH")
    if len(spec["stages"]) == 1 and (len(frame) != len(candidates) or not frame.instrument.map(candidates).eq(frame['rank']).all()):
        raise ValueError("SIGNAL_BASELINE_RANK_MISMATCH")
    if "b19r2r_frozen" in spec["stages"]:
        if spec.get("candidate_policy") == "model_a_ranked_eligible_top50":
            if len(frame) != 50 or not set(frame.instrument).issubset(set(ranks)):
                raise ValueError("SIGNAL_B19_ELIGIBLE50_MISMATCH")
        else:
            allowed = {key for key, rank in candidates.items() if rank <= 50 and key != "TW7769"}
            if set(frame.instrument) != allowed:
                raise ValueError("SIGNAL_B19_EXACT50_MISMATCH")


def read_signal_artifact(directory: Path, config: dict, model: str, asof: str, *, historical=False) -> tuple[dict, pd.DataFrame]:
    payload = json.loads((directory / "manifest.json").read_text())
    if not isinstance(payload, dict):
        raise ValueError('SIGNAL_ARTIFACT_MANIFEST_INVALID')
    if historical and payload.get('pipeline_context'):
        config = historical_config(config, model, payload['pipeline_context'])
    spec = config["models"][model]
    if (payload.get("schema_version") != "tw.clean.artifact.v1"
            or payload.get("artifact_type") != "ModelSignalArtifact"
            or payload.get("fixture") is not False
            or payload.get("model") != model or payload.get("asof") != asof
            or payload.get("canonical_id") != spec.get("canonical_id", model)
            or payload.get("candidate_policy") != spec.get("candidate_policy")
            or payload.get("pipeline_fingerprint") != pipeline_fingerprint(config, model)):
        raise ValueError("SIGNAL_ARTIFACT_IDENTITY_MISMATCH")
    entry = payload.get("files", {}).get("signals", {})
    target = directory / "signals.csv"
    if not isinstance(entry, dict) or path(entry.get("path", "")).resolve() != target.resolve():
        raise ValueError("SIGNAL_ARTIFACT_PATH_MISMATCH")
    verify_file(target, entry.get("sha256", ""))
    frame = pd.read_csv(target)
    if payload.get("row_count") != len(frame) or payload.get("status") not in ("READY", "BLOCKED"):
        raise ValueError("SIGNAL_ARTIFACT_STATUS_OR_COUNT_INVALID")
    if payload["status"] == "READY":
        validate_signal_rows(frame, asof)
        validate_full_ranks(frame, payload.get("full_qlib_ranks"), payload.get("baseline_candidate_ranks"), spec)
    elif not frame.empty:
        raise ValueError("BLOCKED_SIGNAL_CONTAINS_ROWS")
    return payload, frame.sort_values("rank").reset_index(drop=True)
