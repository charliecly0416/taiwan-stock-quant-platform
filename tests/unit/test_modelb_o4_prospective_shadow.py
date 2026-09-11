from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "scripts/validate_modelb_o4_prospective_shadow.py"
BUILDER_PATH = ROOT / "scripts/build_modelb_o4_prospective_shadow.py"
ARTIFACT = ROOT / "data_tw/experiments/project_runtime_convergence/o4_prospective_bridge_20260907/shadow_observation"
DELAYED_ARTIFACT = ROOT / "data_tw/experiments/project_runtime_convergence/o4_prospective_bridge_20260908/shadow_observation"


def load_validator():
    spec = importlib.util.spec_from_file_location("o4_shadow_validator", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_builder():
    spec = importlib.util.spec_from_file_location("o4_shadow_builder", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def local_copy_from(tmp_path: Path, artifact: Path) -> Path:
    target = tmp_path / "observation"
    shutil.copytree(artifact, target)
    manifest_path = target / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["feature_frame"] = "feature_frame.csv"
    manifest["signals"] = "signals.csv"
    manifest["source_ledger"] = "source_ledger.json"
    manifest["rank_source_ledger"] = "rank_source_ledger.csv"
    manifest["model_signal_artifact"] = "model_signal_artifact"
    manifest["model_signal_artifact_manifest"] = "model_signal_artifact/manifest.json"
    ledger_source = ROOT / manifest["observation_ledger"]
    shutil.copy2(ledger_source, target / "observations.csv")
    manifest["observation_ledger"] = "observations.csv"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    child_path = target / "model_signal_artifact" / "manifest.json"
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["output_files"] = {name: Path(value).name for name, value in child["output_files"].items()}
    child_path.write_text(json.dumps(child, indent=2) + "\n", encoding="utf-8")
    manifest["model_signal_artifact_manifest_sha256"] = checksum(child_path)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return target


def local_copy(tmp_path: Path) -> Path:
    return local_copy_from(tmp_path, ARTIFACT)


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh_source_lineage(target: Path) -> None:
    source = target / "source_ledger.json"
    child_path = target / "model_signal_artifact" / "manifest.json"
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["source_ledger_sha256"] = checksum(source)
    child_path.write_text(json.dumps(child, indent=2) + "\n", encoding="utf-8")
    top_path = target / "manifest.json"
    top = json.loads(top_path.read_text(encoding="utf-8"))
    top["source_ledger_sha256"] = checksum(source)
    top["model_signal_artifact_manifest_sha256"] = checksum(child_path)
    top_path.write_text(json.dumps(top, indent=2) + "\n", encoding="utf-8")


def rebind_delayed_adapter(target: Path, family: str) -> tuple[Path, Path, dict]:
    source_path = target / "source_ledger.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    row = next(item for item in source["sources"] if item["family"] == family)
    original = ROOT / row["adapter"]
    adapter = json.loads(original.read_text(encoding="utf-8"))
    original_normalized = Path(adapter["normalized_files"][0]["path"])
    local_dir = target / "adapter_sources"
    local_dir.mkdir(exist_ok=True)
    normalized = local_dir / f"{family}.normalized.json"
    local_adapter = local_dir / f"{family}.adapter.json"
    shutil.copy2(original_normalized, normalized)
    adapter["normalized_files"][0]["path"] = str(normalized)
    local_adapter.write_text(json.dumps(adapter, indent=2) + "\n", encoding="utf-8")
    row["adapter"] = str(local_adapter)
    row["adapter_sha256"] = checksum(local_adapter)
    row["normalized"] = str(normalized)
    row["normalized_sha256"] = checksum(normalized)
    source_path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    refresh_source_lineage(target)
    return local_adapter, normalized, source


def update_rebound_adapter(target: Path, family: str, adapter_path: Path, normalized_path: Path) -> None:
    source_path = target / "source_ledger.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    row = next(item for item in source["sources"] if item["family"] == family)
    row["adapter_sha256"] = checksum(adapter_path)
    row["normalized_sha256"] = checksum(normalized_path)
    source_path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    refresh_source_lineage(target)


def test_real_delayed_flow_observation_passes_contract_validation():
    report = load_validator().validate(DELAYED_ARTIFACT)
    assert report["ok"] is True
    assert report["accepted"] is True
    assert report["feature_count"] == 78
    assert report["model_b_signal_rows"] == 50


def test_feature_checksum_tamper_is_rejected(tmp_path: Path):
    target = local_copy(tmp_path)
    frame = pd.read_csv(target / "feature_frame.csv")
    frame.loc[0, "MA5"] += 1.0
    frame.to_csv(target / "feature_frame.csv", index=False)
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "feature_frame_checksum_mismatch" in report["errors"]


def test_candidate_universe_tamper_is_rejected_even_with_new_checksum(tmp_path: Path):
    target = local_copy(tmp_path)
    signals = pd.read_csv(target / "signals.csv")
    signals.loc[0, "instrument"] = "TW0000"
    signals.to_csv(target / "signals.csv", index=False)
    manifest_path = target / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["signals_sha256"] = checksum(target / "signals.csv")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "candidate_universe_changed" in report["errors"]


def test_late_observation_cannot_be_relabelled_accepted(tmp_path: Path):
    target = local_copy(tmp_path)
    manifest_path = target / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["accepted"] = True
    manifest["warmup_counted"] = True
    manifest["status"] = "ACCEPTED_PROSPECTIVE_INPUT"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "accepted_warmup_or_cutoff_semantics_invalid" in report["errors"]


def test_source_ledger_tamper_is_rejected_after_manifest_hash_is_updated(tmp_path: Path):
    target = local_copy(tmp_path)
    ledger_path = target / "source_ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["sources"][0]["trade_date_max"] = "2000-01-01"
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    manifest_path = target / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_ledger_sha256"] = checksum(ledger_path)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "ledger_trade_date_max_mismatch:adjusted_price" in report["errors"]


def test_missing_twii_required_segment_is_rejected(tmp_path: Path):
    target = local_copy(tmp_path)
    ledger_path = target / "source_ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["sources"] = [row for row in ledger["sources"] if row.get("family") != "twii"]
    ledger["same_run_required_segments"] = ["adjusted_price", "institutional_flow", "margin_short"]
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    manifest_path = target / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_ledger_sha256"] = checksum(ledger_path)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "same_run_required_segments_invalid" in report["errors"]


def test_child_artifact_checksum_tamper_is_rejected(tmp_path: Path):
    target = local_copy(tmp_path)
    signals = target / "model_signal_artifact" / "signals.csv"
    frame = pd.read_csv(signals)
    frame.loc[0, "buy_score"] += 1.0
    frame.to_csv(signals, index=False)
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "model_signal_artifact_signals_checksum_mismatch" in report["errors"]


def test_rank_csv_checksum_tamper_is_rejected_after_ledger_hash_is_updated(tmp_path: Path):
    target = local_copy(tmp_path)
    rank_path = target / "rank_source_ledger.csv"
    ranks = pd.read_csv(rank_path)
    ranks.loc[0, "signals_sha256"] = "tampered"
    ranks.to_csv(rank_path, index=False)
    manifest_path = target / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["rank_source_ledger_sha256"] = checksum(rank_path)
    child_path = target / "model_signal_artifact" / "manifest.json"
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["rank_source_ledger_sha256"] = checksum(rank_path)
    child_path.write_text(json.dumps(child, indent=2) + "\n", encoding="utf-8")
    manifest["model_signal_artifact_manifest_sha256"] = checksum(child_path)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "rank_signal_checksum_mismatch:2026-08-31" in report["errors"]


def test_o2_delayed_flow_formula_fixed_sample():
    builder = load_builder()
    dates = pd.date_range("2026-01-01", periods=10, freq="D")
    inst = pd.DataFrame({
        "instrument": ["TW2330"] * 10, "trade_date": dates,
        "foreign_net_buy": range(1, 11), "investment_trust_net_buy": range(1, 11),
        "dealer_net_buy": range(1, 11), "total_institutional_net_buy": range(1, 11),
    })
    margin = pd.DataFrame({
        "instrument": ["TW2330"] * 10, "trade_date": dates,
        "margin_purchase_today_balance": range(100, 110), "margin_purchase_yesterday_balance": range(99, 109),
        "short_sale_today_balance": range(200, 210), "short_sale_yesterday_balance": range(199, 209),
    })
    out = builder.orthogonal_features(inst, margin, "2026-01-10", ["TW2330"])
    row = out.iloc[0]
    assert row["institutional_total_net_buy_roll1"] == 10
    assert row["institutional_total_net_buy_roll3"] == 27
    assert row["institutional_total_net_buy_roll5"] == 40
    assert row["institutional_total_net_buy_roll10"] == 55
    assert row["institutional_total_net_buy_streak"] == 10
    assert row["institutional_delay_flag"] == 0
    assert row["margin_short_delay_flag"] == 0


def test_stale_global_observation_ledger_checksum_is_rejected(tmp_path: Path):
    target = local_copy(tmp_path)
    ledger_path = target / "observations.csv"
    rows = pd.read_csv(ledger_path)
    rows.loc[0, "recorded_at"] = "stale"
    rows.to_csv(ledger_path, index=False)
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "observation_ledger_row_checksum_invalid" in report["errors"]


def test_target_rank_manifest_same_run_and_cutoff_tamper_is_rejected(tmp_path: Path):
    target = local_copy(tmp_path)
    rank_path = target / "rank_source_ledger.csv"
    ranks = pd.read_csv(rank_path)
    index = ranks.index[ranks["date"] == "2026-09-07"][0]
    original_manifest = ROOT / ranks.loc[index, "manifest"]
    original_signals = ROOT / ranks.loc[index, "signals"]
    local_rank = target / "rank_target"
    local_rank.mkdir()
    shutil.copy2(original_signals, local_rank / "signals.csv")
    manifest = json.loads(original_manifest.read_text(encoding="utf-8"))
    manifest["files"]["signals"] = "signals.csv"
    manifest["source_acquisition_run_id"] = "forged-run"
    manifest["decision_cutoff"] = "2000-01-01T00:00:00+00:00"
    local_manifest = local_rank / "manifest.json"
    local_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    ranks.loc[index, "signals"] = "rank_target/signals.csv"
    ranks.loc[index, "manifest"] = "rank_target/manifest.json"
    ranks.loc[index, "signals_sha256"] = checksum(local_rank / "signals.csv")
    ranks.loc[index, "manifest_sha256"] = checksum(local_manifest)
    ranks.to_csv(rank_path, index=False)
    top_path = target / "manifest.json"
    top = json.loads(top_path.read_text(encoding="utf-8"))
    top["rank_source_ledger_sha256"] = checksum(rank_path)
    child_path = target / "model_signal_artifact" / "manifest.json"
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["rank_source_ledger_sha256"] = checksum(rank_path)
    child_path.write_text(json.dumps(child, indent=2) + "\n", encoding="utf-8")
    top["model_signal_artifact_manifest_sha256"] = checksum(child_path)
    top_path.write_text(json.dumps(top, indent=2) + "\n", encoding="utf-8")
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "target_rank_same_run_cutoff_or_pit_invalid" in report["errors"]


def test_child_semantic_tamper_is_rejected_after_all_visible_checksums_are_updated(tmp_path: Path):
    target = local_copy(tmp_path)
    signals_path = target / "model_signal_artifact" / "signals.csv"
    signals = pd.read_csv(signals_path)
    signals.loc[0, "candidate_rank"] = 150
    signals.loc[0, "full_qlib_rank"] = 150
    signals.loc[0, "buy_score"] += 1.0
    signals.loc[0, "raw_score"] += 1.0
    signals.to_csv(signals_path, index=False)
    child_path = target / "model_signal_artifact" / "manifest.json"
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["checksums"]["signals"] = checksum(signals_path)
    child_path.write_text(json.dumps(child, indent=2) + "\n", encoding="utf-8")
    top_path = target / "manifest.json"
    top = json.loads(top_path.read_text(encoding="utf-8"))
    top["model_signal_artifact_manifest_sha256"] = checksum(child_path)
    top_path.write_text(json.dumps(top, indent=2) + "\n", encoding="utf-8")
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "model_signal_artifact_parent_semantics_mismatch" in report["errors"]
    assert "model_signal_artifact_feature_rank_binding_invalid" in report["errors"]


def test_delayed_flow_missing_prior_symbol_is_rejected(tmp_path: Path):
    target = local_copy_from(tmp_path, DELAYED_ARTIFACT)
    adapter_path, normalized_path, _ = rebind_delayed_adapter(target, "margin_short")
    payload = json.loads(normalized_path.read_text(encoding="utf-8"))
    payload["records"] = [
        row for row in payload["records"]
        if not (row["trade_date"] == "2026-09-07" and row["symbol"] == "1301")
    ]
    normalized_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    adapter = json.loads(adapter_path.read_text(encoding="utf-8"))
    adapter["normalized_files"][0]["sha256"] = checksum(normalized_path)
    adapter_path.write_text(json.dumps(adapter, indent=2) + "\n", encoding="utf-8")
    update_rebound_adapter(target, "margin_short", adapter_path, normalized_path)
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "delayed_flow_selected_row_count_invalid:margin_short" in report["errors"]


def test_delayed_flow_duplicate_prior_symbol_is_rejected(tmp_path: Path):
    target = local_copy_from(tmp_path, DELAYED_ARTIFACT)
    adapter_path, normalized_path, _ = rebind_delayed_adapter(target, "margin_short")
    payload = json.loads(normalized_path.read_text(encoding="utf-8"))
    duplicate = next(row for row in payload["records"] if row["trade_date"] == "2026-09-07" and row["symbol"] == "1301")
    payload["records"].append(dict(duplicate))
    normalized_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    adapter = json.loads(adapter_path.read_text(encoding="utf-8"))
    adapter["normalized_files"][0]["sha256"] = checksum(normalized_path)
    adapter_path.write_text(json.dumps(adapter, indent=2) + "\n", encoding="utf-8")
    update_rebound_adapter(target, "margin_short", adapter_path, normalized_path)
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "delayed_flow_selected_row_count_invalid:margin_short" in report["errors"]
    assert "delayed_flow_duplicate_or_coverage_invalid:margin_short" in report["errors"]


def test_delayed_flow_older_than_price_prior_session_is_rejected(tmp_path: Path):
    target = local_copy_from(tmp_path, DELAYED_ARTIFACT)
    source_path = target / "source_ledger.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source["flow_prior_observed_session"] = "2026-09-04"
    for row in source["sources"]:
        if row["family"] in {"institutional_flow", "margin_short"}:
            row["selected_trade_date"] = "2026-09-04"
    source_path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    refresh_source_lineage(target)
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "delayed_flow_prior_session_invalid" in report["errors"]


def test_delayed_margin_forged_override_state_is_rejected(tmp_path: Path):
    target = local_copy_from(tmp_path, DELAYED_ARTIFACT)
    adapter_path, normalized_path, _ = rebind_delayed_adapter(target, "margin_short")
    adapter = json.loads(adapter_path.read_text(encoding="utf-8"))
    adapter["pit_status"] = "PASS"
    adapter["validator_status"] = "PASS"
    adapter_path.write_text(json.dumps(adapter, indent=2) + "\n", encoding="utf-8")
    source_path = target / "source_ledger.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    row = next(item for item in source["sources"] if item["family"] == "margin_short")
    row["adapter_pit_status"] = "PASS"
    row["adapter_validator_status"] = "PASS"
    source_path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    update_rebound_adapter(target, "margin_short", adapter_path, normalized_path)
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "margin_delayed_flow_override_invalid" in report["errors"]


def test_delayed_flow_available_after_cutoff_is_rejected(tmp_path: Path):
    target = local_copy_from(tmp_path, DELAYED_ARTIFACT)
    adapter_path, normalized_path, _ = rebind_delayed_adapter(target, "margin_short")
    adapter = json.loads(adapter_path.read_text(encoding="utf-8"))
    adapter["available_at"] = "2026-09-08T10:48:00+00:00"
    adapter_path.write_text(json.dumps(adapter, indent=2) + "\n", encoding="utf-8")
    source_path = target / "source_ledger.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    row = next(item for item in source["sources"] if item["family"] == "margin_short")
    row["available_at"] = adapter["available_at"]
    source_path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    update_rebound_adapter(target, "margin_short", adapter_path, normalized_path)
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "source_available_after_cutoff:margin_short" in report["errors"]


def test_delayed_flow_checksum_linked_tamper_is_rejected(tmp_path: Path):
    target = local_copy_from(tmp_path, DELAYED_ARTIFACT)
    _, normalized_path, _ = rebind_delayed_adapter(target, "margin_short")
    payload = json.loads(normalized_path.read_text(encoding="utf-8"))
    payload["records"][0]["margin_purchase_today_balance"] += 1
    normalized_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "adapter_normalized_checksum_mismatch:margin_short" in report["errors"]


def append_distinct_ledger_row(ledger_path: Path) -> None:
    rows = pd.read_csv(ledger_path, dtype=str).fillna("").to_dict("records")
    row = dict(rows[0])
    row["asof"] = "2099-01-01"
    row["source_run_id"] = "append-only-test-run"
    row["decision_cutoff"] = "2099-01-01T10:00:00+00:00"
    row["recorded_at"] = "2099-01-01T10:01:00+00:00"
    row["row_sha256"] = load_validator().observation_ledger_row_sha256(row)
    rows.append(row)
    pd.DataFrame(rows).to_csv(ledger_path, index=False)


def test_ledger_append_different_identity_keeps_old_and_new_observations_valid(tmp_path: Path):
    old_target = local_copy_from(tmp_path / "old", ARTIFACT)
    new_target = local_copy_from(tmp_path / "new", DELAYED_ARTIFACT)
    append_distinct_ledger_row(old_target / "observations.csv")
    append_distinct_ledger_row(new_target / "observations.csv")
    assert load_validator().validate(old_target)["ok"] is True
    assert load_validator().validate(new_target)["ok"] is True


def test_ledger_duplicate_own_identity_is_rejected(tmp_path: Path):
    target = local_copy_from(tmp_path, DELAYED_ARTIFACT)
    ledger = target / "observations.csv"
    rows = pd.read_csv(ledger, dtype=str).fillna("").to_dict("records")
    own = next(row for row in rows if row["asof"] == "2026-09-08")
    rows.append(dict(own))
    pd.DataFrame(rows).to_csv(ledger, index=False)
    report = load_validator().validate(target)
    assert report["ok"] is False
    assert "observation_ledger_row_not_unique" in report["errors"]
