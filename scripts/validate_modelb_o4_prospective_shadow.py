#!/usr/bin/env python3
"""Validate an isolated O4 78-feature prospective shadow observation."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODEL_B = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
WHITELIST = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv"
REQUIRED = {"adjusted_price", "institutional_flow", "margin_short", "twii"}
CORE = {"date", "instrument", "model_name", "model_family", "candidate_rank", "buy_score", "raw_score", "score_rank", "full_qlib_rank", "signal_asof", "available_at", "source_artifact", "source_model_artifact", "source_feature_artifact"}
FORBIDDEN = ("future_return", "future_excess_return", "forward_return", "label_", "relevance_10d_top_heavy", "ltr_relevance_label", "realized_pnl", "realized_return", "target_position", "target_weight", "order_qty", "execution_price", "broker_order_id")
FLOW_REQUIRED_FIELDS = {
    "institutional_flow": (
        "foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy", "total_institutional_net_buy",
    ),
    "margin_short": (
        "margin_purchase_today_balance", "margin_purchase_yesterday_balance",
        "short_sale_today_balance", "short_sale_yesterday_balance",
    ),
}
MARGIN_PRIOR_SESSION_OVERRIDE = (
    "BLOCKED_PUBLICATION_AND_AVAILABILITY_UNPROVEN",
    "BLOCKED_SOURCE_SCOPE_OR_VALIDATOR_UNPROVEN",
)

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def observation_ledger_row_sha256(row: dict[str, Any]) -> str:
    fields = (
        "asof", "source_run_id", "decision_cutoff", "status", "accepted", "warmup_counted",
        "feature_rows", "scored_rows", "model_a_top50_rows", "feature_frame_sha256",
        "model_b_signals_sha256", "reason", "recorded_at",
    )
    canonical = {field: str(row.get(field, "")) for field in fields}
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def resolve(value: str, base: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    rooted = ROOT / path
    return rooted if rooted.exists() else base / path

def parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None

def require(errors: list[str], ok: bool, message: str) -> None:
    if not ok:
        errors.append(message)

def validate_adapter(
    row: dict[str, Any], source: dict[str, Any], asof: str, errors: list[str], *, selected_flow_date: str | None = None,
) -> datetime | None:
    family = str(row.get("family"))
    adapter = resolve(str(row.get("adapter") or ""), ROOT)
    require(errors, adapter.exists(), f"adapter_missing:{family}")
    if not adapter.exists(): return None
    require(errors, sha256(adapter) == row.get("adapter_sha256"), f"adapter_checksum_mismatch:{family}")
    try: meta = json.loads(adapter.read_text(encoding="utf-8"))
    except Exception:
        errors.append(f"adapter_json_invalid:{family}"); return None
    require(errors, meta.get("acquisition_run_id") == source.get("source_run_id"), f"adapter_source_run_mismatch:{family}")
    require(errors, meta.get("http_status") == 200 and meta.get("http_response_bytes") is True, f"adapter_http_evidence_invalid:{family}")
    available = parse_time(meta.get("available_at"))
    require(errors, available is not None and available.isoformat() == row.get("available_at"), f"adapter_available_at_ledger_mismatch:{family}")
    if source.get("source_gate_mode") == "delayed_flow_prior_session":
        require(errors, row.get("adapter_pit_status") == meta.get("pit_status") and row.get("adapter_validator_status") == meta.get("validator_status"), f"adapter_status_ledger_mismatch:{family}")
    files = meta.get("normalized_files") or []
    require(errors, len(files) == 1, f"adapter_normalized_file_count_invalid:{family}")
    if len(files) != 1: return available
    entry = files[0]; normalized = resolve(str(entry.get("path") or ""), ROOT)
    require(errors, normalized.exists(), f"normalized_missing:{family}")
    if not normalized.exists(): return available
    actual_hash = sha256(normalized)
    require(errors, actual_hash == entry.get("sha256"), f"adapter_normalized_checksum_mismatch:{family}")
    require(errors, actual_hash == row.get("normalized_sha256"), f"ledger_normalized_checksum_mismatch:{family}")
    raw_files = meta.get("raw_files") or []
    require(errors, bool(raw_files), f"adapter_raw_files_missing:{family}")
    for raw_entry in raw_files:
        raw = resolve(str(raw_entry.get("path") or ""), ROOT)
        require(errors, raw.exists() and sha256(raw) == raw_entry.get("sha256"), f"adapter_raw_checksum_mismatch:{family}")
    try:
        records = pd.DataFrame(json.loads(normalized.read_text(encoding="utf-8")).get("records") or [])
        dates = pd.to_datetime(records.get("trade_date"), errors="coerce").dropna()
        maximum = str(dates.max().date()) if len(dates) else ""
    except Exception: maximum = ""
    require(errors, maximum == row.get("trade_date_max"), f"ledger_trade_date_max_mismatch:{family}")
    delayed = source.get("source_gate_mode") == "delayed_flow_prior_session"
    if not delayed or family == "adjusted_price":
        require(errors, maximum == asof, f"adapter_trade_date_max_not_asof:{family}")
        require(errors, meta.get("pit_status") == "PASS", f"adapter_pit_not_pass:{family}")
        return available
    require(errors, selected_flow_date is not None, f"delayed_flow_date_missing:{family}")
    if family == "institutional_flow":
        require(errors, meta.get("pit_status") == "PASS" and meta.get("validator_status") == "PASS", "institutional_delayed_flow_status_invalid")
    elif family == "margin_short":
        require(
            errors,
            (meta.get("pit_status"), meta.get("validator_status")) == MARGIN_PRIOR_SESSION_OVERRIDE
            and str(meta.get("trade_date") or "")[:10] == selected_flow_date,
            "margin_delayed_flow_override_invalid",
        )
        require(errors, row.get("o4_prior_session_override") is True, "margin_delayed_flow_override_ledger_invalid")
    else:
        errors.append(f"delayed_flow_family_invalid:{family}")
        return available
    if selected_flow_date is None:
        return available
    selected = records[pd.to_datetime(records.get("trade_date"), errors="coerce").dt.strftime("%Y-%m-%d") == selected_flow_date].copy()
    symbol = selected.get("symbol", pd.Series(dtype=str)).astype(str).map(lambda x: x.upper() if x.upper().startswith("TW") else f"TW{x.upper()}")
    required = list(FLOW_REQUIRED_FIELDS[family])
    numeric = selected.reindex(columns=required).apply(pd.to_numeric, errors="coerce")
    expected_count = int(row.get("selected_target_symbol_count") or 0)
    require(errors, len(selected) == expected_count == int(row.get("selected_row_count") or 0), f"delayed_flow_selected_row_count_invalid:{family}")
    require(errors, symbol.nunique() == expected_count == int(row.get("selected_unique_symbol_count") or 0) and not symbol.duplicated().any(), f"delayed_flow_duplicate_or_coverage_invalid:{family}")
    require(errors, np.isfinite(numeric.to_numpy(dtype=float)).all() and row.get("selected_required_fields_finite") is True and row.get("selected_required_fields") == required, f"delayed_flow_required_fields_invalid:{family}")
    require(errors, row.get("selected_trade_date") == selected_flow_date and row.get("delayed_flow_coverage_status") == "PASS", f"delayed_flow_selected_date_or_ledger_invalid:{family}")
    return available

def validate_twii(row: dict[str, Any], source: dict[str, Any], asof: str, errors: list[str]) -> datetime | None:
    capture = resolve(str(row.get("capture") or ""), ROOT); raw = resolve(str(row.get("raw") or ""), ROOT)
    require(errors, capture.exists() and raw.exists(), "twii_capture_or_raw_missing")
    if not capture.exists() or not raw.exists(): return None
    require(errors, sha256(capture) == row.get("capture_sha256"), "twii_capture_checksum_mismatch")
    require(errors, sha256(raw) == row.get("raw_sha256"), "twii_raw_checksum_mismatch")
    try:
        meta = json.loads(capture.read_text(encoding="utf-8")); data = json.loads(raw.read_text(encoding="utf-8"))
        dates = pd.to_datetime(pd.DataFrame(data.get("data") or []).get("date"), errors="coerce").dropna()
        maximum = str(dates.max().date()) if len(dates) else ""
    except Exception:
        errors.append("twii_json_invalid"); return None
    require(errors, meta.get("source_run_id") == source.get("source_run_id"), "twii_source_run_mismatch")
    require(errors, meta.get("raw_sha256") == sha256(raw), "twii_capture_raw_binding_mismatch")
    observed = parse_time(meta.get("observed_at"))
    require(errors, observed is not None and observed.isoformat() == row.get("observed_at"), "twii_observed_at_ledger_mismatch")
    require(errors, maximum == asof and bool(meta.get("target_date_present")), "twii_trade_date_max_not_asof")
    return observed

def validate_rank_history(path: Path, base: Path, feature: pd.DataFrame, asof: str, source: dict[str, Any], top: dict[str, Any], errors: list[str]) -> list[str]:
    require(errors, path.exists(), "rank_source_ledger_missing")
    if not path.exists(): return []
    rows = pd.read_csv(path).fillna("").to_dict("records")
    require(errors, len(rows) == 6, "rank_source_ledger_not_six_sessions")
    dates, target = [], None
    for row in rows:
        date = str(row.get("date") or ""); dates.append(date)
        signal_path = resolve(str(row.get("signals") or ""), base); manifest_path = resolve(str(row.get("manifest") or ""), base)
        require(errors, signal_path.exists() and manifest_path.exists(), f"rank_source_missing:{date}")
        if not signal_path.exists() or not manifest_path.exists(): continue
        require(errors, sha256(signal_path) == row.get("signals_sha256"), f"rank_signal_checksum_mismatch:{date}")
        require(errors, sha256(manifest_path) == row.get("manifest_sha256"), f"rank_manifest_checksum_mismatch:{date}")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8")); data = pd.read_csv(signal_path)
            declared = (manifest.get("files") or manifest.get("output_files") or {}).get("signals")
        except Exception:
            errors.append(f"rank_source_unreadable:{date}"); continue
        require(errors, manifest.get("artifact_type") == "ModelSignalArtifact" and declared is not None and (manifest_path.parent / declared).resolve() == signal_path.resolve(), f"rank_manifest_binding_invalid:{date}")
        ranks = pd.to_numeric(data.get("candidate_rank"), errors="coerce")
        require(errors, str(manifest.get("asof")) == date and int(manifest.get("row_count", -1)) == 150 and len(data) == 150 and data.instrument.nunique() == 150 and sorted(ranks.dropna().astype(int).tolist()) == list(range(1, 151)), f"rank_csv_content_invalid:{date}")
        report_name = str(row.get("validator_report") or "")
        if report_name:
            report = resolve(report_name, base)
            require(errors, report.exists() and sha256(report) == row.get("validator_report_sha256"), f"rank_validator_report_checksum_mismatch:{date}")
        if date == asof:
            available = data.get("available_at", pd.Series(dtype=str)).astype(str).str[:10]
            candidate_cutoff = parse_time(manifest.get("decision_cutoff"))
            final_cutoff = parse_time(source.get("decision_cutoff"))
            require(
                errors,
                manifest.get("source_acquisition_run_id") == source.get("source_run_id")
                and candidate_cutoff is not None
                and final_cutoff is not None
                and candidate_cutoff <= final_cutoff
                and candidate_cutoff.astimezone(ZoneInfo("Asia/Taipei")).date().isoformat() == asof
                and manifest.get("asof") == asof
                and manifest.get("signal_asof") == asof
                and set(available) == {asof},
                "target_rank_same_run_cutoff_or_pit_invalid",
            )
            require(errors, row.get("candidate_decision_cutoff") == manifest.get("decision_cutoff") == top.get("target_model_a_candidate_decision_cutoff"), "target_rank_candidate_cutoff_lineage_invalid")
        if date == asof: target = data
    require(errors, dates == sorted(dates), "rank_source_ledger_dates_not_sorted")
    if target is not None and {"instrument", "qlib_rank"}.issubset(feature.columns):
        left = feature[["instrument", "qlib_rank"]].copy(); right = target[["instrument", "candidate_rank", "full_qlib_rank"]].copy()
        left.instrument = left.instrument.astype(str); right.instrument = right.instrument.astype(str)
        joined = left.merge(right, on="instrument", how="outer", indicator=True)
        require(errors, set(joined["_merge"]) == {"both"} and (pd.to_numeric(joined.qlib_rank) == pd.to_numeric(joined.candidate_rank)).all() and (pd.to_numeric(joined.qlib_rank) == pd.to_numeric(joined.full_qlib_rank)).all(), "rank_target_feature_binding_invalid")
    return dates

def normalized_trade_dates(adapter_row: dict[str, Any]) -> list[str]:
    adapter = resolve(str(adapter_row.get("adapter") or ""), ROOT)
    meta = json.loads(adapter.read_text(encoding="utf-8"))
    entry = (meta.get("normalized_files") or [])[0]
    normalized = resolve(str(entry.get("path") or ""), ROOT)
    records = json.loads(normalized.read_text(encoding="utf-8")).get("records") or []
    return sorted({str(item.get("trade_date") or "")[:10] for item in records if item.get("trade_date")})

def calendar_dates(path: Path) -> list[str]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8")); records = payload.get("records") or payload.get("data") or []
        return sorted({str(item.get("trade_date") or item.get("date") or "")[:10] for item in records if item.get("trade_date") or item.get("date")})
    return [line.strip()[:10] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def validate_child(child: Path, top: dict[str, Any], parent_signal: pd.DataFrame, feature: pd.DataFrame, source_hash: str, rank_hash: str, errors: list[str]) -> None:
    manifest_path = child / "manifest.json"; require(errors, manifest_path.exists(), "model_signal_artifact_manifest_missing")
    if not manifest_path.exists(): return
    require(errors, sha256(manifest_path) == top.get("model_signal_artifact_manifest_sha256"), "model_signal_artifact_manifest_checksum_mismatch")
    payload = json.loads(manifest_path.read_text(encoding="utf-8")); files = payload.get("output_files") or {}; checksums = payload.get("checksums") or {}
    for key in ("signals", "schema", "coverage_audit", "forbidden_field_audit", "legacy_mapping_audit"):
        file = resolve(str(files.get(key) or ""), child)
        require(errors, file.exists(), f"model_signal_artifact_{key}_missing")
        if file.exists(): require(errors, sha256(file) == checksums.get(key), f"model_signal_artifact_{key}_checksum_mismatch")
    require(errors, payload.get("artifact_type") == "model_signal" and payload.get("artifact_contract") == "ModelSignalArtifact" and payload.get("production_allowed") is False, "model_signal_artifact_identity_or_safety_invalid")
    require(errors, payload.get("source_ledger_sha256") == source_hash and payload.get("rank_source_ledger_sha256") == rank_hash and payload.get("feature_frame_sha256") == top.get("feature_frame_sha256") and payload.get("model_sha256") == top.get("model_sha256"), "model_signal_artifact_lineage_checksum_invalid")
    signal_path = resolve(str(files.get("signals") or ""), child)
    if signal_path.exists():
        signal = pd.read_csv(signal_path); top50 = set(feature.loc[pd.to_numeric(feature.qlib_rank, errors="coerce") <= 50, "instrument"].astype(str))
        require(errors, set(signal.columns) == CORE and len(signal) == 50 and signal.instrument.nunique() == 50 and set(signal.instrument.astype(str)) == top50, "model_signal_artifact_core_or_candidate_invalid")
        require(errors, set(signal.available_at.astype(str)) == {str(top.get("asof"))}, "model_signal_artifact_available_at_invalid")
        bound = parent_signal.merge(signal, on=["date", "instrument"], how="outer", suffixes=("_parent", "_child"), indicator=True)
        require(errors, set(bound["_merge"]) == {"both"}, "model_signal_artifact_parent_key_binding_invalid")
        if set(bound["_merge"]) == {"both"}:
            numeric_fields = ("candidate_rank", "buy_score", "raw_score", "score_rank", "full_qlib_rank")
            numeric_same = all(
                np.isclose(
                    pd.to_numeric(bound[f"{name}_parent"], errors="coerce"),
                    pd.to_numeric(bound[f"{name}_child"], errors="coerce"),
                    rtol=0, atol=0, equal_nan=False,
                ).all()
                for name in numeric_fields
            )
            text_fields = ("model_name", "model_family", "signal_asof", "source_artifact", "source_model_artifact", "source_feature_artifact")
            text_same = all(bound[f"{name}_parent"].astype(str).eq(bound[f"{name}_child"].astype(str)).all() for name in text_fields)
            require(errors, numeric_same and text_same, "model_signal_artifact_parent_semantics_mismatch")
            ranks = feature.loc[pd.to_numeric(feature.qlib_rank, errors="coerce") <= 50, ["instrument", "qlib_rank"]].copy()
            ranks["instrument"] = ranks["instrument"].astype(str)
            child_ranks = signal[["instrument", "candidate_rank", "full_qlib_rank"]].copy()
            child_ranks["instrument"] = child_ranks["instrument"].astype(str)
            child_bound = child_ranks.merge(ranks, on="instrument", how="outer", indicator=True)
            require(errors, set(child_bound["_merge"]) == {"both"} and (pd.to_numeric(child_bound.candidate_rank) == pd.to_numeric(child_bound.qlib_rank)).all() and (pd.to_numeric(child_bound.full_qlib_rank) == pd.to_numeric(child_bound.qlib_rank)).all(), "model_signal_artifact_feature_rank_binding_invalid")

def validate_observation_ledger(manifest: dict[str, Any], ledger_path: Path, errors: list[str]) -> None:
    require(errors, ledger_path.exists(), "observation_ledger_missing")
    if not ledger_path.exists(): return
    try:
        rows = pd.read_csv(ledger_path, dtype=str).fillna("").to_dict("records")
    except Exception:
        errors.append("observation_ledger_unreadable"); return
    identity = manifest.get("observation_ledger_row_identity") or {}
    expected_identity = {key: str(manifest.get(key) or "") for key in ("asof", "source_run_id", "decision_cutoff")}
    require(errors, identity == expected_identity, "observation_ledger_identity_binding_invalid")
    matched = [row for row in rows if all(str(row.get(key) or "") == value for key, value in expected_identity.items())]
    require(errors, len(matched) == 1, "observation_ledger_row_not_unique")
    if len(matched) != 1: return
    row = matched[0]
    require(errors, row.get("row_sha256") == observation_ledger_row_sha256(row), "observation_ledger_row_checksum_invalid")
    require(errors, manifest.get("observation_ledger_row_sha256") == row.get("row_sha256"), "observation_ledger_row_checksum_mismatch")
    expected = {
        "status": str(manifest.get("status") or ""),
        "accepted": str(bool(manifest.get("accepted"))).lower(),
        "warmup_counted": str(bool(manifest.get("warmup_counted"))).lower(),
        "feature_rows": str(manifest.get("feature_rows") or ""),
        "scored_rows": str(manifest.get("scored_rows") or ""),
        "model_a_top50_rows": str(manifest.get("model_a_top50_rows") or ""),
        "feature_frame_sha256": str(manifest.get("feature_frame_sha256") or ""),
        "model_b_signals_sha256": str(manifest.get("signals_sha256") or ""),
        "reason": str(manifest.get("quarantine_reason") or ""),
    }
    require(errors, all(str(row.get(key) or "") == value for key, value in expected.items()), "observation_ledger_row_mismatch")

def validate(artifact_dir: Path, ledger: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []; manifest_path = artifact_dir / "manifest.json"
    if not manifest_path.exists(): return {"ok": False, "status": "FAIL", "errors": ["manifest_missing"]}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ledger_path = ledger or resolve(str(manifest.get("observation_ledger") or ""), artifact_dir)
    feature_path = resolve(str(manifest.get("feature_frame") or "feature_frame.csv"), artifact_dir); signal_path = resolve(str(manifest.get("signals") or "signals.csv"), artifact_dir)
    source_path = resolve(str(manifest.get("source_ledger") or "source_ledger.json"), artifact_dir); rank_path = resolve(str(manifest.get("rank_source_ledger") or "rank_source_ledger.csv"), artifact_dir)
    for name, path in (("feature_frame", feature_path), ("signals", signal_path), ("source_ledger", source_path), ("rank_source_ledger", rank_path)): require(errors, path.exists(), f"{name}_missing")
    if errors: return {"ok": False, "status": "FAIL", "errors": errors}
    require(errors, manifest.get("model_b") == MODEL_B and manifest.get("model_b_role") == "rerank_model_a_top50_only", "model_identity_or_role_invalid")
    require(errors, manifest.get("feature_count") == 78, "manifest_feature_count_not_78")
    require(errors, sha256(feature_path) == manifest.get("feature_frame_sha256"), "feature_frame_checksum_mismatch")
    require(errors, sha256(signal_path) == manifest.get("signals_sha256"), "signals_checksum_mismatch")
    require(errors, sha256(source_path) == manifest.get("source_ledger_sha256"), "source_ledger_checksum_mismatch")
    require(errors, sha256(rank_path) == manifest.get("rank_source_ledger_sha256"), "rank_source_ledger_checksum_mismatch")
    require(errors, sha256(WHITELIST) == manifest.get("whitelist_sha256"), "whitelist_checksum_mismatch")
    feature = pd.read_csv(feature_path); whitelist = pd.read_csv(WHITELIST).sort_values("order").feature.astype(str).tolist()
    require(errors, feature.columns.tolist() == ["date", "instrument", *whitelist] and len(feature) == 150 and feature.instrument.nunique() == 150 and not feature.duplicated(["date", "instrument"]).any(), "feature_schema_or_cross_section_invalid")
    require(errors, not [x for x in feature.columns if any(token in x.lower() for token in FORBIDDEN)], "forbidden_feature_columns")
    top50 = feature[pd.to_numeric(feature.qlib_rank, errors="coerce") <= 50]
    require(errors, len(top50) == 50 and np.isfinite(top50[whitelist].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)).all(), "top50_not_exact_finite_50x78")
    signal = pd.read_csv(signal_path)
    require(errors, set(signal.columns) == CORE and len(signal) == 50 and signal.instrument.nunique() == 50 and not signal.duplicated(["date", "instrument"]).any(), "model_signal_core_schema_invalid")
    if len(signal) == 50:
        paired = signal.merge(top50[["instrument", "qlib_rank"]], on="instrument", how="outer", indicator=True); numeric = signal[["candidate_rank", "buy_score", "raw_score", "score_rank", "full_qlib_rank"]].apply(pd.to_numeric, errors="coerce")
        require(errors, set(paired["_merge"]) == {"both"} and (pd.to_numeric(paired.candidate_rank) == pd.to_numeric(paired.qlib_rank)).all() and (pd.to_numeric(paired.full_qlib_rank) == pd.to_numeric(paired.qlib_rank)).all(), "candidate_universe_changed")
        require(errors, np.isfinite(numeric.to_numpy(dtype=float)).all() and sorted(numeric.score_rank.astype(int)) == list(range(1, 51)), "model_signal_numeric_or_rank_invalid")
    source = json.loads(source_path.read_text(encoding="utf-8")); cutoff = parse_time(source.get("decision_cutoff"))
    require(errors, cutoff is not None, "decision_cutoff_invalid")
    require(errors, source.get("asof") == manifest.get("asof") and source.get("source_run_id") == manifest.get("source_run_id") and source.get("decision_cutoff") == manifest.get("decision_cutoff"), "source_ledger_binding_mismatch")
    rows = source.get("sources") or []; require(errors, {row.get("family") for row in rows} == REQUIRED and set(source.get("same_run_required_segments") or []) == REQUIRED, "same_run_required_segments_invalid")
    mode = source.get("source_gate_mode", "legacy_same_day_adapter_max")
    require(errors, mode in {"legacy_same_day_adapter_max", "delayed_flow_prior_session"}, "source_gate_mode_invalid")
    price_row = next((row for row in rows if row.get("family") == "adjusted_price"), None)
    calendar_path = resolve(str(source.get("calendar_input") or ""), ROOT)
    selected_flow_date = None
    if price_row is not None and calendar_path.exists():
        observed = normalized_trade_dates(price_row)
        formal = calendar_dates(calendar_path)
        formal_through_asof = [date for date in formal if date <= str(manifest.get("asof"))]
        prior = [date for date in formal_through_asof if date in set(observed) and date < str(manifest.get("asof"))]
        if mode == "delayed_flow_prior_session":
            selected_flow_date = prior[-1] if prior else None
            require(errors, selected_flow_date is not None and source.get("flow_prior_observed_session") == selected_flow_date, "delayed_flow_prior_session_invalid")
    arrivals = []
    for row in rows:
        value = validate_twii(row, source, str(manifest.get("asof")), errors) if row.get("family") == "twii" else validate_adapter(
            row, source, str(manifest.get("asof")), errors,
            selected_flow_date=selected_flow_date if row.get("family") in FLOW_REQUIRED_FIELDS else None,
        )
        if value is not None:
            require(errors, cutoff is not None and value <= cutoff, f"source_available_after_cutoff:{row.get('family')}")
            arrivals.append(value)
    rank_dates = validate_rank_history(rank_path, artifact_dir, feature, str(manifest.get("asof")), source, manifest, errors)
    require(errors, price_row is not None and calendar_path.exists() and sha256(calendar_path) == source.get("calendar_input_sha256"), "formula_parity_calendar_binding_invalid")
    if price_row is not None and calendar_path.exists():
        observed = normalized_trade_dates(price_row)
        formal = calendar_dates(calendar_path)
        formal_through_asof = [date for date in formal if date <= str(manifest.get("asof"))]
        expected_rank_dates = [date for date in formal_through_asof if date in set(observed)][-6:]
        prior = [date for date in formal_through_asof if date in set(observed) and date < str(manifest.get("asof"))]
        audit = manifest.get("formula_parity_audit") or {}
        require(errors, source.get("formal_calendar_sessions_through_asof") == formal_through_asof and rank_dates == expected_rank_dates and len(expected_rank_dates) == 6, "formula_parity_rank_sessions_invalid")
        require(errors, bool(prior) and audit.get("institutional_flow_selected_trade_date") == prior[-1] and audit.get("margin_short_selected_trade_date") == prior[-1] and audit.get("price_and_twii_selected_trade_date") == manifest.get("asof") and audit.get("derived_available_at") == manifest.get("asof") and audit.get("same_day_flow_excluded") is True and audit.get("rolling_and_streak_cutoff") == prior[-1], "formula_parity_delayed_flow_invalid")
    accepted = bool(manifest.get("accepted")); same_day = bool(cutoff and cutoff.astimezone(ZoneInfo("Asia/Taipei")).date().isoformat() == manifest.get("asof")); before = bool(cutoff and arrivals and all(value <= cutoff for value in arrivals))
    if mode == "delayed_flow_prior_session":
        required_dates = (
            price_row is not None
            and price_row.get("trade_date_max") == manifest.get("asof")
            and all(
                row.get("selected_trade_date") == selected_flow_date and row.get("delayed_flow_coverage_status") == "PASS"
                for row in rows if row.get("family") in FLOW_REQUIRED_FIELDS
            )
        )
    else:
        required_dates = all(row.get("trade_date_max") == manifest.get("asof") for row in rows if row.get("family") != "twii")
    expected = same_day and before and required_dates and (manifest.get("formula_parity_audit") or {}).get("status") == "PASS"
    require(errors, accepted == expected and bool(manifest.get("warmup_counted")) == accepted, "accepted_warmup_or_cutoff_semantics_invalid")
    require(errors, manifest.get("status") == ("ACCEPTED_PROSPECTIVE_INPUT" if accepted else "QUARANTINED_SHADOW_OBSERVATION"), "observation_status_invalid")
    require(errors, manifest.get("production_allowed") is False and manifest.get("no_publish") is True and manifest.get("no_baseline_switch") is True, "safety_flags_invalid")
    validate_observation_ledger(manifest, ledger_path, errors)
    validate_child(resolve(str(manifest.get("model_signal_artifact") or "model_signal_artifact"), artifact_dir), manifest, signal, feature, sha256(source_path), sha256(rank_path), errors)
    protected = artifact_dir / "forbidden_scope_audit.json"; require(errors, protected.exists() and json.loads(protected.read_text(encoding="utf-8")).get("protected_unchanged") is True, "protected_fingerprint_audit_invalid")
    return {"ok": not errors, "status": "PASS" if not errors else "FAIL", "artifact_dir": str(artifact_dir), "asof": manifest.get("asof"), "accepted": accepted, "feature_rows": len(feature), "feature_count": len(whitelist), "model_b_signal_rows": len(signal), "errors": errors}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--artifact-dir", required=True); parser.add_argument("--ledger"); parser.add_argument("--report"); parser.add_argument("--json", action="store_true"); args = parser.parse_args()
    report = validate(Path(args.artifact_dir).resolve(), Path(args.ledger).resolve() if args.ledger else None)
    if args.report: Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    if args.json: print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report["ok"] else 2

if __name__ == "__main__": raise SystemExit(main())
