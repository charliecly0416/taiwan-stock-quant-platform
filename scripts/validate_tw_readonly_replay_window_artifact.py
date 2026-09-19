#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_ACTIONS = {"historical_add", "historical_risk_reduce"}
REQUIRED_ARTIFACTS = {
    "summary",
    "daily_nav",
    "actions",
    "snapshots",
    "coverage_audit",
    "position_integrity_audit",
    "forbidden_field_audit",
    "execution_audit",
    "forbidden_action_audit",
    "decision_source_audit",
    "forbidden_scope_audit",
    "action_lineage_audit",
    "source_identity_audit",
}
REQUIRED_COLUMNS = {
    "summary": {
        "window",
        "model_name",
        "model_family",
        "strategy_rule",
        "start_date",
        "end_date",
        "initial_cash",
        "fee_and_tax",
        "final_equity",
        "total_return",
        "max_drawdown",
        "action_count",
        "buy_count",
        "sell_count",
        "skipped_action_count",
        "max_holding_count",
        "duplicate_position_count",
        "negative_cash_count",
        "missing_price_count",
        "diagnostic_only",
    },
    "actions": {
        "signal_date",
        "execution_date",
        "instrument",
        "action",
        "quantity",
        "execution_price",
        "commission",
        "tax",
        "fee_and_tax",
        "cash_after",
        "position_after",
        "intent_reason",
        "strategy_rule",
        "model_name",
        "order_intent_artifact",
        "order_intent_row_id",
    },
    "daily_nav": {
        "date",
        "cash",
        "market_value",
        "equity",
        "daily_return",
        "holding_count",
        "missing_price_count",
    },
    "snapshots": {
        "date",
        "instrument",
        "quantity",
        "cost_basis",
        "mark_price",
        "market_value",
        "unrealized_pnl",
        "strategy_rule",
        "model_name",
    },
    "coverage_audit": {
        "audit_name",
        "requested_start_date",
        "requested_end_date",
        "actual_start_date",
        "actual_end_date",
        "trading_day_count",
        "signal_day_count",
        "price_day_count",
        "missing_signal_day_count",
        "missing_price_day_count",
        "status",
        "details",
    },
    "position_integrity_audit": {
        "audit_name",
        "date",
        "instrument",
        "status",
        "value",
        "threshold",
        "details",
    },
    "forbidden_field_audit": {
        "audit_name",
        "artifact",
        "field_name",
        "field_category",
        "present",
        "used_for_ranking",
        "status",
        "details",
    },
    "execution_audit": {
        "audit_name",
        "status",
        "value",
        "threshold",
        "details",
    },
}
FORBIDDEN_OUTPUT_FIELDS = {
    "broker_order_id",
    "broker_account",
    "quick_trade_status",
    "real_order_status",
    "provider_publish_status",
    "accepted_latest_status",
    "monitor_config_write_status",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return (
        candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()
    )


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return payload if isinstance(payload, dict) else {}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def bool_true(value: Any) -> bool:
    return type(value) is bool and value is True


def bool_false(value: Any) -> bool:
    return type(value) is bool and value is False


def normalized_ref(value: Any) -> str:
    return rel(resolve(str(value or ""))) if value else ""


def referenced_output_paths(payload: dict[str, Any]) -> list[Path]:
    outputs = payload.get("output_files") or {}
    if not isinstance(outputs, dict):
        return []
    return [
        resolve(value) for value in outputs.values() if isinstance(value, str) and value
    ]


def derive_checksum_closure(
    manifest_path: Path, manifest: dict[str, Any]
) -> tuple[set[str], list[str]]:
    paths: set[Path] = {manifest_path.resolve()}
    errors: list[str] = []

    def add_ref(value: Any, label: str) -> Path | None:
        if not isinstance(value, str) or not value:
            errors.append(f"missing_ref:{label}")
            return None
        path = resolve(value)
        paths.add(path)
        return path

    artifacts = manifest.get("artifacts") or {}
    if not isinstance(artifacts, dict):
        errors.append("invalid_ref:artifacts")
        artifacts = {}
    for name, value in artifacts.items():
        add_ref(value, f"artifacts.{name}")

    order_refs = manifest.get("order_intent_artifacts") or []
    if not isinstance(order_refs, list) or not order_refs:
        errors.append("missing_ref:order_intent_artifacts")
    else:
        for index, value in enumerate(order_refs):
            order_path = add_ref(value, f"order_intent_artifacts[{index}]")
            if order_path is not None:
                order_manifest = load_json(order_path)
                outputs = referenced_output_paths(order_manifest)
                if not outputs:
                    errors.append(f"missing_outputs:{rel(order_path)}")
                paths.update(outputs)

    price_manifest_path = add_ref(
        manifest.get("canonical_price_store_manifest"),
        "canonical_price_store_manifest",
    )
    if price_manifest_path is not None:
        price_manifest = load_json(price_manifest_path)
        add_ref(price_manifest.get("prices_path"), "price_store.prices_path")

    for field in (
        "replay_window_policy",
        "model_registry",
        "baseline_descriptor",
        "baseline_manifest",
    ):
        add_ref(manifest.get(field), field)

    validation = manifest.get("replay_window_policy_validation") or {}
    add_ref(validation.get("source_training_report"), "source_training_report")

    identity = manifest.get("model_source_identity") or {}
    training_path = add_ref(
        identity.get("canonical_training_manifest"), "canonical_training_manifest"
    )
    if training_path is not None:
        training = load_json(training_path)
        add_ref(training.get("model_path"), "training.model_path")
        add_ref(training.get("raw_oos_score_path"), "training.raw_oos_score_path")

    for field in ("signal_manifest", "full_rank_manifest"):
        lineage_path = add_ref(identity.get(field), field)
        if lineage_path is not None:
            lineage = load_json(lineage_path)
            outputs = referenced_output_paths(lineage)
            if not outputs:
                errors.append(f"missing_outputs:{rel(lineage_path)}")
            paths.update(outputs)

    missing = sorted(rel(path) for path in paths if not path.is_file())
    errors.extend(f"missing_file:{path}" for path in missing)
    return {rel(path) for path in paths}, errors


def validate_checksums(
    manifest_path: Path, manifest: dict[str, Any]
) -> tuple[bool, str]:
    checksum_path = resolve(str(manifest.get("checksum_manifest") or ""))
    checksum = load_json(checksum_path)
    if (
        checksum.get("artifact_type") != "readonly_replay_checksum_manifest"
        or checksum.get("schema_version") != "readonly_replay_checksum_wf2a_v1"
        or checksum.get("run_id") != manifest.get("run_id")
    ):
        return False, "checksum contract invalid"
    declared: dict[str, dict[str, Any]] = {}
    bad: list[str] = []
    for item in checksum.get("files") or []:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            bad.append("invalid_entry")
            continue
        path = resolve(item["path"])
        key = rel(path)
        if key in declared:
            bad.append(f"duplicate:{key}")
            continue
        declared[key] = item
        if (
            not path.is_file()
            or not isinstance(item.get("bytes"), int)
            or item["bytes"] != path.stat().st_size
            or item.get("sha256") != sha256_file(path)
        ):
            bad.append(key)
    required, closure_errors = derive_checksum_closure(manifest_path, manifest)
    self_declared = {
        normalized_ref(path) for path in manifest.get("checksum_required_files") or []
    }
    missing = sorted(required - set(declared))
    extra = sorted(set(declared) - required)
    self_missing = sorted(required - self_declared)
    self_extra = sorted(self_declared - required)
    ok = (
        bool(required)
        and not bad
        and not closure_errors
        and not missing
        and not extra
        and not self_missing
        and not self_extra
    )
    details = (
        f"checked={len(declared)}; bad={bad}; closure_errors={closure_errors}; "
        f"missing={missing}; extra={extra}; self_missing={self_missing}; "
        f"self_extra={self_extra}"
    )
    return ok, details


def validate_e1_lineage(manifest: dict[str, Any]) -> tuple[bool, str]:
    model_id = str(manifest.get("model_id") or "")
    strategy_rule = str(manifest.get("strategy_rule") or "")
    identity = manifest.get("model_source_identity") or {}
    registry = load_yaml(resolve(str(manifest.get("model_registry") or "")))
    descriptor = load_yaml(resolve(str(manifest.get("baseline_descriptor") or "")))
    policy = load_yaml(resolve(str(manifest.get("replay_window_policy") or "")))
    validation = manifest.get("replay_window_policy_validation") or {}

    canonical = (
        (registry.get("production_models") or {}).get("production_selectable") or {}
    ).get(model_id)
    active = (descriptor.get("active_baseline") or {}).get("model_a") or {}
    policy_model = (policy.get("models") or {}).get(model_id) or {}
    source_key = str(identity.get("source_key") or "")
    deprecated = (
        (registry.get("production_models") or {}).get("deprecated") or {}
    ).get(source_key)

    training_path = resolve(str(identity.get("canonical_training_manifest") or ""))
    training = load_json(training_path)
    model_path = resolve(str(training.get("model_path") or ""))
    raw_ref = str(training.get("raw_oos_score_path") or "")
    raw_path = resolve(raw_ref)
    signal_path = resolve(str(identity.get("signal_manifest") or ""))
    signal = load_json(signal_path)
    full_rank_path = resolve(str(identity.get("full_rank_manifest") or ""))
    full_rank = load_json(full_rank_path)
    source_audit_path = resolve(
        str((manifest.get("artifacts") or {}).get("source_identity_audit") or "")
    )
    source_audit = load_json(source_audit_path)

    signal_sources = {
        normalized_ref(value) for value in signal.get("source_artifacts") or []
    }
    signal_hashes = signal.get("input_hashes") or {}
    declared_raw_hash = next(
        (
            value
            for key, value in signal_hashes.items()
            if normalized_ref(key) == normalized_ref(raw_ref)
        ),
        None,
    )
    identity_fields = (
        "canonical_model_id",
        "source_key",
        "registry_alias_reason",
        "canonical_training_manifest",
        "canonical_training_report",
        "canonical_model_artifact",
        "canonical_model_sha256",
        "raw_oos_score",
        "raw_oos_score_sha256",
        "signal_manifest",
        "signal_manifest_sha256",
        "full_rank_manifest",
        "full_rank_manifest_sha256",
        "identity_adaptation",
    )
    source_audit_matches = all(
        source_audit.get(field) == identity.get(field) for field in identity_fields
    )
    output_files_exist = all(
        path.is_file()
        for path in [
            *referenced_output_paths(signal),
            *referenced_output_paths(full_rank),
        ]
    )
    checks = {
        "canonical_registry": isinstance(canonical, dict)
        and normalized_ref(canonical.get("source_manifest")) == rel(training_path)
        and canonical.get("production_default") is True,
        "baseline_descriptor": active.get("model_id") == model_id
        and normalized_ref(active.get("artifact_path")) == rel(model_path)
        and model_path.is_file()
        and active.get("artifact_sha256") == sha256_file(model_path)
        and (descriptor.get("active_baseline") or {}).get("strategy_rule")
        == strategy_rule
        and (descriptor.get("active_baseline") or {}).get("execution_price_mode")
        == "next_open",
        "policy": policy.get("default_model_id") == model_id
        and policy.get("default_strategy_rule") == strategy_rule
        and normalized_ref(policy_model.get("source_manifest")) == rel(training_path)
        and normalized_ref(policy_model.get("source_training_report"))
        == normalized_ref(identity.get("canonical_training_report"))
        and normalized_ref(validation.get("source_manifest")) == rel(training_path)
        and normalized_ref(validation.get("source_training_report"))
        == normalized_ref(identity.get("canonical_training_report")),
        "explicit_alias": identity.get("canonical_model_id") == model_id
        and source_key
        and isinstance(deprecated, dict)
        and deprecated.get("reason") == f"legacy id replaced by {model_id}"
        and identity.get("registry_alias_reason") == deprecated.get("reason")
        and identity.get("identity_adaptation")
        == "explicit_registry_replacement_with_shared_e1_lineage",
        "training_outputs": training_path.is_file()
        and normalized_ref(identity.get("canonical_model_artifact")) == rel(model_path)
        and identity.get("canonical_model_sha256") == sha256_file(model_path)
        and raw_path.is_file()
        and normalized_ref(identity.get("raw_oos_score")) == rel(raw_path)
        and identity.get("raw_oos_score_sha256") == sha256_file(raw_path),
        "model_signal": signal.get("artifact_type") == "model_signal"
        and signal.get("model_name") == source_key
        and normalized_ref(raw_ref) in signal_sources
        and raw_path.is_file()
        and declared_raw_hash == sha256_file(raw_path)
        and identity.get("signal_manifest_sha256") == sha256_file(signal_path),
        "full_rank": full_rank.get("artifact_type") == "full_rank"
        and normalized_ref(full_rank.get("source_artifact")) == rel(raw_path)
        and full_rank.get("source_rank_column") == "qlib_rank_raw"
        and identity.get("full_rank_manifest_sha256") == sha256_file(full_rank_path),
        "lineage_outputs": bool(referenced_output_paths(signal))
        and bool(referenced_output_paths(full_rank))
        and output_files_exist,
        "source_audit": source_audit.get("artifact_type")
        == "canonical_model_source_identity_audit"
        and source_audit.get("schema_version") == "wf2a_source_identity_v1"
        and source_audit.get("status") == "pass"
        and source_audit_matches,
    }
    failed = sorted(name for name, ok in checks.items() if not ok)
    return not failed, f"failed={failed}"


def validate_artifact(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    artifacts = (
        manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
    )
    artifact_paths = {
        key: resolve(str(artifacts.get(key) or "")) for key in REQUIRED_ARTIFACTS
    }
    frames = {
        key: read_csv(artifact_paths[key])
        for key in REQUIRED_COLUMNS
        if artifact_paths[key].is_file()
    }
    missing_artifacts = sorted(
        key for key, path in artifact_paths.items() if not path.is_file()
    )
    missing_columns = {
        key: sorted(columns - set(frames.get(key, pd.DataFrame()).columns))
        for key, columns in REQUIRED_COLUMNS.items()
    }
    missing_columns = {key: value for key, value in missing_columns.items() if value}
    checksum_ok, checksum_details = validate_checksums(manifest_path, manifest)
    lineage_ok, lineage_details = validate_e1_lineage(manifest)
    validation = manifest.get("replay_window_policy_validation") or {}
    checks = [
        check("artifact_type", manifest.get("artifact_type") == "replay_result"),
        check(
            "schema_version",
            manifest.get("schema_version") == "readonly_replay_result_wf2a_v1",
            str(manifest.get("schema_version")),
        ),
        check(
            "candidate_hold",
            manifest.get("status") == "CANDIDATE_HOLD"
            and manifest.get("product_index_admission") is False,
        ),
        check(
            "standard_identity",
            isinstance(manifest.get("run_id"), str)
            and str(manifest["run_id"]).startswith("wf2a_")
            and manifest.get("asof") == manifest.get("window_end"),
        ),
        check(
            "strict_readonly_safety",
            all(
                bool_true(manifest.get(key))
                for key in (
                    "readonly_only",
                    "simulation_only",
                    "not_order",
                    "no_order_action",
                    "not_target_position",
                    "not_investment_advice",
                    "no_provider_publish",
                    "no_accepted_latest_switch",
                    "no_monitor_broker_order",
                    "no_training",
                    "no_score_recompute",
                )
            )
            and bool_false(manifest.get("production_trade_enabled")),
        ),
        check(
            "forward_engine_lineage",
            manifest.get("generated_by") == "replay_execution_engine"
            and manifest.get("execution_input_source") == "order_intent_artifact"
            and manifest.get("decision_source") == "order_intent_artifact"
            and manifest.get("not_copied_from_legacy_replay") is True,
        ),
        check(
            "training_trace",
            validation.get("ok") is True
            and validation.get("model_training_windows_traceable") is True
            and validation.get("training_overlap_rejected") is True
            and resolve(str(validation.get("source_manifest") or "")).is_file()
            and resolve(str(validation.get("source_training_report") or "")).is_file(),
        ),
        check(
            "required_artifacts_exist", not missing_artifacts, str(missing_artifacts)
        ),
        check("required_columns", not missing_columns, str(missing_columns)),
        check("checksum_all_required_files", checksum_ok, checksum_details),
        check("canonical_e1_semantic_lineage", lineage_ok, lineage_details),
    ]
    if missing_artifacts or missing_columns:
        return {"ok": False, "artifact": rel(manifest_path), "checks": checks}

    summary = frames["summary"]
    actions = frames["actions"]
    nav = frames["daily_nav"]
    snapshots = frames["snapshots"]
    active = actions[actions["action"].isin(ACTIVE_ACTIONS)].copy()
    skipped = actions[actions["action"] == "historical_skip"].copy()
    checks.append(
        check(
            "nonempty_replay", not summary.empty and not nav.empty and not active.empty
        )
    )
    execution_after_signal = (
        not active.empty
        and (
            pd.to_datetime(active["execution_date"], errors="coerce")
            > pd.to_datetime(active["signal_date"], errors="coerce")
        ).all()
    )
    checks.append(check("execution_after_signal", bool(execution_after_signal)))
    active_quantity = pd.to_numeric(active["quantity"], errors="coerce")
    checks.append(check("active_quantity_positive", bool((active_quantity > 0).all())))
    numeric_action_columns = [
        "execution_price",
        "commission",
        "tax",
        "cash_after",
        "position_after",
    ]
    action_numeric_ok = all(
        pd.to_numeric(active[column], errors="coerce").notna().all()
        for column in [*numeric_action_columns, "fee_and_tax"]
    )
    checks.append(check("active_action_accounting_present", action_numeric_ok))
    checks.append(
        check(
            "active_action_lineage_present",
            active["order_intent_artifact"].astype(str).str.strip().ne("").all()
            and active["order_intent_row_id"].astype(str).str.strip().ne("").all()
            and active["intent_reason"].astype(str).str.strip().ne("").all(),
        )
    )

    order_paths = [
        resolve(str(path)) for path in manifest.get("order_intent_artifacts") or []
    ]
    intent_records: dict[tuple[str, str], dict[str, Any]] = {}
    intent_instruments: set[str] = set()
    order_contract_ok = bool(order_paths)
    for path in order_paths:
        order_manifest = load_json(path)
        intent_path = resolve(
            str((order_manifest.get("output_files") or {}).get("order_intents") or "")
        )
        intents = read_csv(intent_path)
        required_intent_columns = {
            "order_intent_row_id",
            "signal_date",
            "instrument",
            "intent_action",
            "intent_reason",
            "strategy_rule",
            "model_name",
        }
        manifest_ref = rel(path)
        order_contract_ok = order_contract_ok and (
            order_manifest.get("artifact_type") == "order_intent"
            and order_manifest.get("generation_source") == "strategy_decision_engine"
            and order_manifest.get("not_generated_from_replay_actions") is True
            and order_manifest.get("not_generated_from_replay_snapshots") is True
            and not intents.empty
            and required_intent_columns.issubset(intents.columns)
        )
        if required_intent_columns.issubset(intents.columns):
            for row in intents.to_dict("records"):
                key = (manifest_ref, str(row["order_intent_row_id"]))
                if key in intent_records:
                    order_contract_ok = False
                intent_records[key] = row
                intent_instruments.add(str(row["instrument"]))
    checks.append(check("order_intent_contract", order_contract_ok))

    price_manifest_path = resolve(
        str(manifest.get("canonical_price_store_manifest") or "")
    )
    price_manifest = load_json(price_manifest_path)
    prices_path = resolve(str(price_manifest.get("prices_path") or ""))
    price_store_ok = (
        price_manifest.get("artifact_type") == "price_store"
        and price_manifest.get("readonly_only") is True
        and price_manifest.get("no_provider_publish") is True
        and price_manifest.get("no_accepted_latest_switch") is True
        and prices_path.is_file()
        and price_manifest.get("checksum") == sha256_file(prices_path)
    )
    price_identity = manifest.get("price_store_identity") or {}
    price_store_ok = price_store_ok and (
        price_identity.get("manifest_sha256") == sha256_file(price_manifest_path)
        and price_identity.get("prices_sha256") == price_manifest.get("checksum")
        and price_identity.get("execution_price_field") == "open"
        and price_identity.get("mark_price_field") == "close"
        and price_identity.get("missing_execution_price_policy")
        == "skip_without_close_fallback"
        and manifest.get("execution_price_mode") == "next_open"
    )
    checks.append(check("canonical_price_store_binding", price_store_ok))
    price_rows = pd.DataFrame()
    if price_store_ok:
        instruments = (
            set(actions["instrument"].astype(str))
            | set(snapshots["instrument"].astype(str))
            | intent_instruments
        )
        chunks = []
        for chunk in pd.read_csv(
            prices_path,
            usecols=[
                "price_date",
                "instrument",
                "open",
                "close",
                "tradable_flag",
                "halt_flag",
                "next_day_execution_availability",
                "next_day_execution_status",
            ],
            dtype={"price_date": str, "instrument": str},
            chunksize=100_000,
        ):
            selected = chunk[chunk["instrument"].astype(str).isin(instruments)]
            if not selected.empty:
                chunks.append(selected)
        if chunks:
            price_rows = pd.concat(chunks, ignore_index=True)
            price_rows["price_date"] = price_rows["price_date"].astype(str).str[:10]
    price_index = {
        (str(row.instrument), str(row.price_date)): row
        for row in price_rows.itertuples(index=False)
    }
    price_dates_by_instrument: dict[str, list[str]] = {}
    for instrument, group in price_rows.groupby("instrument"):
        price_dates_by_instrument[str(instrument)] = sorted(
            group["price_date"].astype(str).unique().tolist()
        )
    action_price_ok = price_store_ok and not active.empty
    for row in active.itertuples(index=False):
        quote = price_index.get((str(row.instrument), str(row.execution_date)))
        if quote is None:
            action_price_ok = False
            break
        if not (
            str(quote.tradable_flag).lower() == "true"
            and str(quote.halt_flag).lower() == "false"
            and abs(float(row.execution_price) - float(quote.open)) <= 0.0001
        ):
            action_price_ok = False
            break
        source = price_index.get((str(row.instrument), str(row.signal_date)))
        if source is None or not (
            str(source.next_day_execution_availability).lower() == "true"
            and str(source.next_day_execution_status) == "available"
        ):
            action_price_ok = False
            break
    checks.append(
        check("next_open_execution_from_tradable_price_store", action_price_ok)
    )

    action_rows_by_intent: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in actions.to_dict("records"):
        key = (
            normalized_ref(row.get("order_intent_artifact")),
            str(row.get("order_intent_row_id") or ""),
        )
        action_rows_by_intent.setdefault(key, []).append(row)
    action_map = {"buy": "historical_add", "sell": "historical_risk_reduce"}
    window_end = str(manifest.get("window_end") or "")
    semantic_ok = order_contract_ok
    in_scope_count = 0
    for key, intent in intent_records.items():
        signal_date = str(intent.get("signal_date") or "")
        instrument = str(intent.get("instrument") or "")
        next_dates = [
            day
            for day in price_dates_by_instrument.get(instrument, [])
            if day > signal_date
        ]
        in_scope = bool(next_dates and next_dates[0] <= window_end)
        outputs = action_rows_by_intent.get(key, [])
        if in_scope:
            in_scope_count += 1
            semantic_ok = semantic_ok and len(outputs) == 1
        else:
            semantic_ok = semantic_ok and len(outputs) == 0
        if len(outputs) != 1:
            continue
        output = outputs[0]
        expected_action = action_map.get(str(intent.get("intent_action") or ""))
        actual_action = str(output.get("action") or "")
        action_semantic_ok = actual_action == expected_action or (
            actual_action == "historical_skip"
            and bool(str(output.get("reason") or "").strip())
        )
        if actual_action in ACTIVE_ACTIONS:
            action_semantic_ok = action_semantic_ok and (
                str(output.get("execution_date") or "") == next_dates[0]
            )
        semantic_ok = semantic_ok and bool(expected_action) and action_semantic_ok
        semantic_ok = semantic_ok and all(
            str(output.get(output_field) or "") == str(intent.get(intent_field) or "")
            for intent_field, output_field in (
                ("signal_date", "signal_date"),
                ("instrument", "instrument"),
                ("intent_reason", "intent_reason"),
                ("strategy_rule", "strategy_rule"),
                ("model_name", "model_name"),
            )
        )
    semantic_ok = semantic_ok and set(action_rows_by_intent).issubset(
        set(intent_records)
    )
    semantic_ok = semantic_ok and all(
        len(rows) == 1 for rows in action_rows_by_intent.values()
    )
    checks.append(
        check(
            "order_intent_semantic_bijection",
            semantic_ok,
            (
                f"intents={len(intent_records)}; in_scope={in_scope_count}; "
                f"outputs={len(action_rows_by_intent)}"
            ),
        )
    )

    execution_config = manifest.get("execution_config") or {}
    try:
        configured_initial_cash = float(execution_config.get("initial_equity"))
        fee_rate = float(execution_config.get("fee_rate"))
        sell_tax_rate = float(execution_config.get("sell_tax_rate"))
        target_holdings = int(execution_config.get("target_holdings"))
        lot_size = int(execution_config.get("lot_size"))
        execution_config_ok = (
            execution_config.get("execution_price_mode") == "next_open"
            and manifest.get("execution_price_mode") == "next_open"
            and configured_initial_cash > 0
            and fee_rate > 0
            and sell_tax_rate > 0
            and target_holdings > 0
            and lot_size > 0
            and float(execution_config.get("target_holdings")) == target_holdings
            and float(execution_config.get("lot_size")) == lot_size
        )
    except (TypeError, ValueError):
        configured_initial_cash = float("nan")
        fee_rate = float("nan")
        sell_tax_rate = float("nan")
        target_holdings = 0
        lot_size = 0
        execution_config_ok = False
    initial_cash_values = pd.to_numeric(summary["initial_cash"], errors="coerce")
    initial_cash = (
        float(initial_cash_values.iloc[0])
        if len(summary) == 1 and initial_cash_values.notna().all()
        else float("nan")
    )
    execution_config_ok = execution_config_ok and (
        abs(initial_cash - configured_initial_cash) <= 0.000001
    )
    checks.append(check("execution_config_recomputed", execution_config_ok))

    replay_cash = initial_cash
    replay_positions: dict[str, int] = {}
    action_accounting_ok = True
    action_fee_math_ok = execution_config_ok
    expected_fee_total = 0.0
    ordered_actions = active.assign(
        _execution_sort=active["execution_date"]
        .astype(str)
        .replace("nan", "9999-12-31")
    ).sort_values(["_execution_sort"], kind="stable")
    last_cash_by_date: dict[str, float] = {}
    positions_after_date: dict[str, dict[str, int]] = {}
    for row in ordered_actions.itertuples(index=False):
        instrument = str(row.instrument)
        quantity = int(float(row.quantity))
        price = float(row.execution_price) if str(row.execution_price) != "nan" else 0.0
        commission = float(row.commission)
        tax = float(row.tax)
        action = str(row.action)
        expected_commission = quantity * price * fee_rate
        expected_tax = (
            quantity * price * sell_tax_rate
            if action == "historical_risk_reduce"
            else 0.0
        )
        action_fee_math_ok = action_fee_math_ok and (
            quantity % lot_size == 0
            and abs(commission - expected_commission) <= 0.00001
            and abs(tax - expected_tax) <= 0.00001
            and abs(float(row.fee_and_tax) - expected_commission - expected_tax)
            <= 0.005
        )
        expected_fee_total += expected_commission + expected_tax
        if action == "historical_add":
            replay_cash -= quantity * price + expected_commission + expected_tax
            replay_positions[instrument] = (
                replay_positions.get(instrument, 0) + quantity
            )
        elif action == "historical_risk_reduce":
            replay_cash += quantity * price - expected_commission - expected_tax
            replay_positions[instrument] = (
                replay_positions.get(instrument, 0) - quantity
            )
            action_fee_math_ok = (
                action_fee_math_ok and replay_positions[instrument] >= 0
            )
        if abs(float(row.cash_after) - replay_cash) > 0.02:
            action_accounting_ok = False
        if int(float(row.position_after)) != replay_positions.get(instrument, 0):
            action_accounting_ok = False
        execution_date = str(row.execution_date)
        if execution_date and execution_date != "nan":
            last_cash_by_date[execution_date] = replay_cash
            positions_after_date[execution_date] = {
                symbol: position
                for symbol, position in replay_positions.items()
                if position > 0
            }
    checks.append(check("action_cash_and_position_recomputed", action_accounting_ok))
    checks.append(check("action_fee_and_tax_recomputed", action_fee_math_ok))

    snapshots_numeric = snapshots.copy()
    for column in [
        "quantity",
        "cost_basis",
        "mark_price",
        "market_value",
        "unrealized_pnl",
    ]:
        snapshots_numeric[column] = pd.to_numeric(
            snapshots_numeric[column], errors="coerce"
        )
    duplicate_count = int(snapshots_numeric.duplicated(["date", "instrument"]).sum())
    snapshot_math_ok = (
        snapshots_numeric[
            ["quantity", "cost_basis", "mark_price", "market_value", "unrealized_pnl"]
        ]
        .notna()
        .all()
        .all()
        and (
            (
                snapshots_numeric["market_value"]
                - snapshots_numeric["quantity"] * snapshots_numeric["mark_price"]
            ).abs()
            <= 0.011
        ).all()
        and (
            (
                snapshots_numeric["unrealized_pnl"]
                - snapshots_numeric["quantity"]
                * (snapshots_numeric["mark_price"] - snapshots_numeric["cost_basis"])
            ).abs()
            <= 0.011
        ).all()
    )
    checks.append(check("position_snapshots_accounting", bool(snapshot_math_ok)))
    checks.append(check("duplicate_position_count_zero", duplicate_count == 0))

    nav_numeric = nav.copy()
    for column in [
        "cash",
        "market_value",
        "equity",
        "daily_return",
        "holding_count",
        "missing_price_count",
    ]:
        nav_numeric[column] = pd.to_numeric(nav_numeric[column], errors="coerce")
    snapshot_market = snapshots_numeric.groupby("date")["market_value"].sum().to_dict()
    snapshot_counts = (
        snapshots_numeric[snapshots_numeric["quantity"] > 0]
        .groupby("date")
        .size()
        .to_dict()
    )
    nav_date_values = nav["date"].astype(str).tolist()
    snapshot_date_values = set(snapshots_numeric["date"].astype(str))
    expected_positions: dict[str, int] = {}
    snapshot_action_positions_ok = set(positions_after_date).issubset(
        set(nav_date_values)
    ) and snapshot_date_values.issubset(set(nav_date_values))
    for nav_date in nav_date_values:
        if nav_date in positions_after_date:
            expected_positions = positions_after_date[nav_date]
        actual_rows = snapshots_numeric[
            (snapshots_numeric["date"].astype(str) == nav_date)
            & (snapshots_numeric["quantity"] > 0)
        ]
        actual_positions = {
            str(row.instrument): int(row.quantity)
            for row in actual_rows.itertuples(index=False)
        }
        if actual_positions != expected_positions:
            snapshot_action_positions_ok = False
    checks.append(
        check("snapshots_match_action_positions", snapshot_action_positions_ok)
    )
    nav_math_ok = not nav_numeric.empty
    prior_cash = initial_cash
    previous_equity = initial_cash
    for row in nav_numeric.itertuples(index=False):
        if abs(float(row.equity) - float(row.cash) - float(row.market_value)) > 0.02:
            nav_math_ok = False
        rounding_tolerance = max(0.011, int(row.holding_count) * 0.011)
        if (
            abs(
                float(row.market_value) - float(snapshot_market.get(str(row.date), 0.0))
            )
            > rounding_tolerance
        ):
            nav_math_ok = False
        if int(row.holding_count) != int(snapshot_counts.get(str(row.date), 0)):
            nav_math_ok = False
        expected_cash = last_cash_by_date.get(str(row.date), prior_cash)
        if abs(float(row.cash) - expected_cash) > 0.02:
            nav_math_ok = False
        expected_daily_return = (
            float(row.equity) / previous_equity - 1.0 if previous_equity else 0.0
        )
        if abs(float(row.daily_return) - expected_daily_return) > 1e-7:
            nav_math_ok = False
        prior_cash = float(row.cash)
        previous_equity = float(row.equity)
    checks.append(check("nav_cash_holdings_consistent", nav_math_ok))
    checks.append(
        check("negative_cash_count_zero", bool((nav_numeric["cash"] >= 0).all()))
    )
    checks.append(
        check(
            "holding_limit",
            execution_config_ok
            and bool((nav_numeric["holding_count"] <= target_holdings).all()),
        )
    )
    summary_row = summary.iloc[0]
    equity_values = nav_numeric["equity"].astype(float)
    equity_with_initial = pd.Series(
        [initial_cash, *equity_values.tolist()], dtype=float
    )
    drawdowns = equity_with_initial / equity_with_initial.cummax() - 1.0
    recomputed_max_drawdown = float(drawdowns.min())
    summary_ok = (
        len(summary) == 1
        and str(summary_row["model_name"]) == str(manifest.get("model_id"))
        and str(summary_row["strategy_rule"]) == str(manifest.get("strategy_rule"))
        and abs(float(summary_row["initial_cash"]) - configured_initial_cash)
        <= 0.000001
        and abs(float(summary_row["fee_and_tax"]) - expected_fee_total) <= 0.005
        and int(summary_row["action_count"]) == len(active)
        and int(summary_row["buy_count"])
        == int((active["action"] == "historical_add").sum())
        and int(summary_row["sell_count"])
        == int((active["action"] == "historical_risk_reduce").sum())
        and int(summary_row["skipped_action_count"]) == len(skipped)
        and int(summary_row["duplicate_position_count"]) == duplicate_count
        and int(summary_row["negative_cash_count"])
        == int((nav_numeric["cash"] < 0).sum())
        and int(summary_row["missing_price_count"])
        == int(nav_numeric["missing_price_count"].sum())
        and int(summary_row["max_holding_count"])
        == int(nav_numeric["holding_count"].max())
        and int(summary_row["max_holding_count"]) <= target_holdings
        and abs(float(summary_row["max_drawdown"]) - recomputed_max_drawdown)
        <= 0.000002
        and abs(
            float(summary_row["final_equity"]) - float(nav_numeric.iloc[-1]["equity"])
        )
        <= 0.02
        and abs(
            float(summary_row["total_return"])
            - (float(nav_numeric.iloc[-1]["equity"]) / initial_cash - 1.0)
        )
        <= 1e-6
    )
    checks.append(check("summary_recomputed", summary_ok))

    coverage = frames["coverage_audit"]
    nav_dates = nav["date"].astype(str)
    actual_start = str(nav_dates.min()) if not nav_dates.empty else ""
    actual_end = str(nav_dates.max()) if not nav_dates.empty else ""
    requested_start = str(manifest.get("window_start") or "")
    requested_end = str(manifest.get("window_end") or "")
    missing_price_days = int((nav_numeric["missing_price_count"] > 0).sum())
    coverage_ok = len(coverage) == 1 and bool(requested_start and requested_end)
    if coverage_ok:
        coverage_row = coverage.iloc[0]
        coverage_numbers = {
            column: pd.to_numeric(
                pd.Series([coverage_row[column]]), errors="coerce"
            ).iloc[0]
            for column in (
                "trading_day_count",
                "signal_day_count",
                "price_day_count",
                "missing_signal_day_count",
                "missing_price_day_count",
            )
        }
        coverage_ok = bool(
            pd.Series(coverage_numbers).notna().all()
            and requested_start <= actual_start <= actual_end <= requested_end
            and str(coverage_row["requested_start_date"]) == requested_start
            and str(coverage_row["requested_end_date"]) == requested_end
            and str(coverage_row["actual_start_date"]) == actual_start
            and str(coverage_row["actual_end_date"]) == actual_end
            and int(coverage_numbers["trading_day_count"]) == len(nav_numeric)
            and int(coverage_numbers["signal_day_count"]) == len(nav_numeric)
            and int(coverage_numbers["price_day_count"])
            == len(nav_numeric) - missing_price_days
            and int(coverage_numbers["missing_signal_day_count"]) == 0
            and int(coverage_numbers["missing_price_day_count"]) == missing_price_days
            and nav_dates.nunique() == len(nav_numeric)
            and str(summary_row["start_date"]) == actual_start
            and str(summary_row["end_date"]) == actual_end
        )
    checks.append(check("coverage_recomputed", coverage_ok))

    skipped_traceable = skipped.empty or (
        skipped["intent_reason"].astype(str).str.strip().ne("").all()
        and skipped["order_intent_artifact"].astype(str).str.strip().ne("").all()
        and skipped["order_intent_row_id"].astype(str).str.strip().ne("").all()
    )
    missing_price_total = int(nav_numeric["missing_price_count"].sum())
    missing_price_trace = (
        skipped["reason"]
        .astype(str)
        .str.contains("missing|unavailable|halted|not_tradable|no_next", regex=True)
        .any()
    )
    checks.append(
        check(
            "missing_price_skips_traceable",
            skipped_traceable
            and (missing_price_total == 0 or bool(missing_price_trace)),
        )
    )

    csv_audits_ok = True
    for key in (
        "coverage_audit",
        "position_integrity_audit",
        "forbidden_field_audit",
        "execution_audit",
    ):
        frame = frames[key]
        csv_audits_ok = csv_audits_ok and (
            not frame.empty and frame["status"].astype(str).str.lower().eq("pass").all()
        )
    forbidden_action = load_json(artifact_paths["forbidden_action_audit"])
    action_audit_ok = forbidden_action.get("status") == "pass" and all(
        forbidden_action.get(key) is True
        for key in (
            "no_training",
            "no_tuning",
            "no_score_recompute",
            "no_strategy_intent_mutation",
            "no_default_switch",
            "no_provider_publish",
            "no_accepted_latest_switch",
            "no_monitor_write",
            "no_broker_order",
        )
    )
    checks.append(check("required_audits_pass", csv_audits_ok and action_audit_ok))
    output_fields = set().union(
        set(summary.columns),
        set(actions.columns),
        set(nav.columns),
        set(snapshots.columns),
    )
    checks.append(
        check(
            "forbidden_output_fields_absent",
            not (output_fields & FORBIDDEN_OUTPUT_FIELDS),
            str(sorted(output_fields & FORBIDDEN_OUTPUT_FIELDS)),
        )
    )

    source_identity = manifest.get("model_source_identity") or {}
    registry = load_yaml(resolve(str(manifest.get("model_registry") or "")))
    deprecated = (registry.get("production_models") or {}).get("deprecated") or {}
    source_key = source_identity.get("source_key")
    alias_ok = (
        source_identity.get("canonical_model_id") == manifest.get("model_id")
        and source_identity.get("identity_adaptation")
        == "explicit_registry_replacement_with_shared_e1_lineage"
        and isinstance(deprecated.get(source_key), dict)
        and deprecated[source_key].get("reason")
        == f"legacy id replaced by {manifest.get('model_id')}"
    )
    lineage_paths = {
        "canonical_training_manifest": "",
        "canonical_model_artifact": "canonical_model_sha256",
        "raw_oos_score": "raw_oos_score_sha256",
        "signal_manifest": "signal_manifest_sha256",
        "full_rank_manifest": "full_rank_manifest_sha256",
    }
    for path_key, hash_key in lineage_paths.items():
        path = resolve(str(source_identity.get(path_key) or ""))
        alias_ok = alias_ok and path.is_file()
        if hash_key:
            alias_ok = alias_ok and sha256_file(path) == source_identity.get(hash_key)
    checks.append(check("canonical_alias_and_e1_lineage", alias_ok))
    return {
        "ok": all(row["status"] == "pass" for row in checks),
        "artifact": rel(manifest_path),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a complete WF-2A readonly ReplayResult candidate."
    )
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate_artifact(resolve(args.artifact))
    print(
        json.dumps(result, ensure_ascii=False, indent=2)
        if args.json
        else f"ok={result['ok']}"
    )
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
