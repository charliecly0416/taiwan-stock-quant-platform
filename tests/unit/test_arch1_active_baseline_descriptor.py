from __future__ import annotations

import importlib.util
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts/validate_arch1_baseline_descriptor.py"
DESCRIPTOR = ROOT / "configs/active_baseline_descriptor.yaml"
ANNEX = ROOT / "data_tw/experiments/project_runtime_convergence/arch1_baseline_descriptor_20260907/ARCH1_RUNTIME_TRUTH_ANNEX.json"
INVENTORY = ROOT / "data_tw/experiments/project_runtime_convergence/arch0_runtime_truth_inventory_20260907/ARCH0_RUNTIME_TRUTH_INVENTORY.json"


def load_validator_module():
    spec = importlib.util.spec_from_file_location("arch1_mutable_latest_validator", VALIDATOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def mutable_latest_fixture(tmp_path: Path):
    module = load_validator_module()
    runtime_root = tmp_path / "runtime"
    descriptor = yaml.safe_load(DESCRIPTOR.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    latest_relative = Path(descriptor["active_baseline"]["model_a"]["latest_pointer"])
    latest = json.loads((ROOT / latest_relative).read_text(encoding="utf-8"))
    artifact_relative = Path(latest["canonical_artifact_dir"])
    (runtime_root / latest_relative).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / latest_relative, runtime_root / latest_relative)
    shutil.copytree(ROOT / artifact_relative, runtime_root / artifact_relative)

    evidence_source = next(
        path
        for path in module.dapr10_evidence_directories(ROOT / "data_tw/ops/daily_auto_update")
        if json.loads((path / "post_publish_validation.json").read_text(encoding="utf-8")).get("run_id") == latest["run_id"]
    )
    evidence_relative = evidence_source.relative_to(ROOT)
    shutil.copytree(evidence_source, runtime_root / evidence_relative)
    evidence_root = runtime_root / "data_tw/ops/daily_auto_update"
    return module, descriptor, inventory, runtime_root, evidence_root, runtime_root / evidence_relative


def latest_checks(fixture) -> dict[str, dict]:
    module, descriptor, inventory, runtime_root, evidence_root, _ = fixture
    return {
        check["name"]: check
        for check in module.validate_active_latest(
            descriptor=descriptor,
            inventory=inventory,
            runtime_root=runtime_root,
            evidence_root=evidence_root,
        )
    }


def run_validator(descriptor: Path, annex: Path = ANNEX) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "--descriptor", str(descriptor), "--annex", str(annex), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout.strip(), proc.stderr
    return proc.returncode, json.loads(proc.stdout)


def test_arch1_descriptor_and_annex_pass() -> None:
    code, output = run_validator(DESCRIPTOR)
    assert code == 0, output
    assert output["ok"] is True
    assert all(item["status"] == "pass" for item in output["checks"])


def test_arch1_current_latest_can_advance_without_descriptor_hash_rewrite() -> None:
    descriptor = yaml.safe_load(DESCRIPTOR.read_text(encoding="utf-8"))
    latest_path = ROOT / descriptor["active_baseline"]["model_a"]["latest_pointer"]
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    anchor_hash = descriptor["protected_latest_paths"][str(latest_path.relative_to(ROOT))]
    assert latest["signal_asof"] > "2026-09-04"
    assert anchor_hash != hashlib.sha256(latest_path.read_bytes()).hexdigest()
    code, output = run_validator(DESCRIPTOR)
    assert code == 0, output
    assert next(item for item in output["checks"] if item["name"] == "active_latest_authorized_provenance")["status"] == "pass"


def test_arch1_rejects_model_b_active_mutation(tmp_path: Path) -> None:
    payload = yaml.safe_load(DESCRIPTOR.read_text(encoding="utf-8"))
    payload["active_baseline"]["status"] = "MODEL_A_PLUS_B"
    payload["active_baseline"]["model_b"] = {"model_id": "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"}
    mutated = tmp_path / "descriptor.yaml"
    mutated.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    code, output = run_validator(mutated)
    assert code != 0
    assert output["ok"] is False
    assert any(item["name"] == "active_model_a_only" and item["status"] == "fail" for item in output["checks"])


def test_arch1_annex_has_twenty_job_rows() -> None:
    annex = json.loads(ANNEX.read_text(encoding="utf-8"))
    assert len(annex["recent_jobs"]) == 20
    assert annex["normalized_nonempty_freshness"]["scan_method"] == "full_directory_all_csv_rows"
    assert annex["model_b_identity"]["canonical_id"] == "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"


def test_arch1_protected_hash_binding_comes_from_descriptor(tmp_path: Path) -> None:
    descriptor_payload = yaml.safe_load(DESCRIPTOR.read_text(encoding="utf-8"))
    annex_payload = json.loads(ANNEX.read_text(encoding="utf-8"))
    synthetic_hash = "a" * 64
    # Bind a complete synthetic descriptor/annex pair so the test exercises
    # descriptor authority independently of the preserved historical annex.
    for path in descriptor_payload["protected_latest_paths"]:
        descriptor_payload["protected_latest_paths"][path] = synthetic_hash
        annex_payload["protected_latest_fingerprints"][path] = synthetic_hash
    mutated_descriptor = tmp_path / "descriptor.yaml"
    mutated_annex = tmp_path / "annex.json"
    mutated_descriptor.write_text(yaml.safe_dump(descriptor_payload, sort_keys=False), encoding="utf-8")
    mutated_annex.write_text(json.dumps(annex_payload), encoding="utf-8")
    code, output = run_validator(mutated_descriptor, mutated_annex)
    assert code == 0, output
    assert next(item for item in output["checks"] if item["name"] == "protected_latest_unchanged")["status"] == "pass"


def test_arch1_rejects_stale_annex_hash_against_descriptor(tmp_path: Path) -> None:
    annex_payload = json.loads(ANNEX.read_text(encoding="utf-8"))
    path = next(iter(annex_payload["protected_latest_fingerprints"]))
    annex_payload["protected_latest_fingerprints"][path] = "b" * 64
    stale_annex = tmp_path / "stale-annex.json"
    stale_annex.write_text(json.dumps(annex_payload), encoding="utf-8")
    code, output = run_validator(DESCRIPTOR, stale_annex)
    assert code != 0
    assert output["ok"] is False
    assert next(item for item in output["checks"] if item["name"] == "protected_latest_unchanged")["status"] == "fail"


def test_arch1_rejects_partial_descriptor_hash_mutation_against_historical_annex(tmp_path: Path) -> None:
    descriptor_payload = yaml.safe_load(DESCRIPTOR.read_text(encoding="utf-8"))
    path = next(iter(descriptor_payload["protected_latest_paths"]))
    descriptor_payload["protected_latest_paths"][path] = "a" * 64
    mutated_descriptor = tmp_path / "partial-descriptor.yaml"
    mutated_descriptor.write_text(yaml.safe_dump(descriptor_payload, sort_keys=False), encoding="utf-8")

    code, output = run_validator(mutated_descriptor)

    assert code != 0
    assert output["ok"] is False
    assert next(item for item in output["checks"] if item["name"] == "protected_latest_unchanged")["status"] == "fail"


def test_arch1_rejects_frozen_model_a_hash_mutation(tmp_path: Path) -> None:
    payload = yaml.safe_load(DESCRIPTOR.read_text(encoding="utf-8"))
    payload["active_baseline"]["model_a"]["artifact_sha256"] = "0" * 64
    mutated = tmp_path / "descriptor.yaml"
    mutated.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    code, output = run_validator(mutated)
    assert code != 0
    assert next(item for item in output["checks"] if item["name"] == "model_a_artifact_hash")["status"] == "fail"


def test_arch1_mutable_latest_positive_fixture(tmp_path: Path) -> None:
    checks = latest_checks(mutable_latest_fixture(tmp_path))
    assert checks
    assert all(check["status"] == "pass" for check in checks.values()), checks


def test_arch1_mutable_latest_rejects_non_model_a_identity(tmp_path: Path) -> None:
    fixture = mutable_latest_fixture(tmp_path)
    _, descriptor, _, runtime_root, _, _ = fixture
    latest_path = runtime_root / descriptor["active_baseline"]["model_a"]["latest_pointer"]
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    latest["model_id"] = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
    latest["model_name"] = latest["model_id"]
    write_json(latest_path, latest)
    assert latest_checks(fixture)["active_latest_model_identity"]["status"] == "fail"


def test_arch1_mutable_latest_rejects_manifest_hash_mismatch(tmp_path: Path) -> None:
    fixture = mutable_latest_fixture(tmp_path)
    _, descriptor, _, runtime_root, _, _ = fixture
    latest = json.loads((runtime_root / descriptor["active_baseline"]["model_a"]["latest_pointer"]).read_text(encoding="utf-8"))
    manifest_path = runtime_root / latest["canonical_manifest"]
    manifest_path.write_text(manifest_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert latest_checks(fixture)["active_latest_file_integrity"]["status"] == "fail"


def test_arch1_mutable_latest_rejects_signals_hash_mismatch(tmp_path: Path) -> None:
    fixture = mutable_latest_fixture(tmp_path)
    _, descriptor, _, runtime_root, _, _ = fixture
    latest = json.loads((runtime_root / descriptor["active_baseline"]["model_a"]["latest_pointer"]).read_text(encoding="utf-8"))
    signals_path = runtime_root / latest["canonical_signals"]
    signals_path.write_text(signals_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert latest_checks(fixture)["active_latest_file_integrity"]["status"] == "fail"


def test_arch1_mutable_latest_rejects_manifest_run_mismatch(tmp_path: Path) -> None:
    fixture = mutable_latest_fixture(tmp_path)
    _, descriptor, _, runtime_root, _, _ = fixture
    latest = json.loads((runtime_root / descriptor["active_baseline"]["model_a"]["latest_pointer"]).read_text(encoding="utf-8"))
    manifest_path = runtime_root / latest["canonical_manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["run_id"] = "different-run"
    write_json(manifest_path, manifest)
    latest["canonical_manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    latest["source_manifest_sha256"] = latest["canonical_manifest_sha256"]
    write_json(runtime_root / descriptor["active_baseline"]["model_a"]["latest_pointer"], latest)
    assert latest_checks(fixture)["active_latest_manifest_contract"]["status"] == "fail"


def test_arch1_mutable_latest_rejects_pointer_date_mismatch(tmp_path: Path) -> None:
    fixture = mutable_latest_fixture(tmp_path)
    _, descriptor, _, runtime_root, _, _ = fixture
    latest_path = runtime_root / descriptor["active_baseline"]["model_a"]["latest_pointer"]
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    latest["asof"] = "2026-09-08"
    write_json(latest_path, latest)
    assert latest_checks(fixture)["active_latest_date_run_coherence"]["status"] == "fail"


def test_arch1_mutable_latest_rejects_canonical_path_escape(tmp_path: Path) -> None:
    fixture = mutable_latest_fixture(tmp_path)
    _, descriptor, _, runtime_root, _, _ = fixture
    latest_path = runtime_root / descriptor["active_baseline"]["model_a"]["latest_pointer"]
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    latest["canonical_manifest"] = "../../outside/manifest.json"
    write_json(latest_path, latest)
    assert latest_checks(fixture)["active_latest_canonical_paths"]["status"] == "fail"


def test_arch1_mutable_latest_rejects_canonical_symlink_escape(tmp_path: Path) -> None:
    fixture = mutable_latest_fixture(tmp_path)
    _, descriptor, _, runtime_root, _, _ = fixture
    latest_path = runtime_root / descriptor["active_baseline"]["model_a"]["latest_pointer"]
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    artifact_dir = runtime_root / latest["canonical_artifact_dir"]
    escaped = tmp_path / "escaped-artifact"
    artifact_copy = tmp_path / "artifact-copy"
    shutil.copytree(artifact_dir, artifact_copy)
    shutil.rmtree(artifact_dir)
    escaped.symlink_to(artifact_copy, target_is_directory=True)
    artifact_dir.symlink_to(escaped, target_is_directory=True)
    assert latest_checks(fixture)["active_latest_canonical_paths"]["status"] == "fail"


def test_arch1_mutable_latest_rejects_pre_anchor_date(tmp_path: Path) -> None:
    fixture = mutable_latest_fixture(tmp_path)
    _, descriptor, _, runtime_root, _, _ = fixture
    latest_path = runtime_root / descriptor["active_baseline"]["model_a"]["latest_pointer"]
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    latest["asof"] = latest["signal_asof"] = "2026-09-03"
    write_json(latest_path, latest)
    assert latest_checks(fixture)["active_latest_arch0_monotonic_anchor"]["status"] == "fail"


def test_arch1_mutable_latest_rejects_mutated_arch0_anchor(tmp_path: Path) -> None:
    fixture = mutable_latest_fixture(tmp_path)
    _, _, inventory, _, _, _ = fixture
    inventory["active_baseline"]["signal_latest"]["canonical_manifest_sha256"] = "f" * 64
    assert latest_checks(fixture)["active_latest_arch0_anchor_integrity"]["status"] == "fail"


def test_arch1_mutable_latest_rejects_missing_publish_evidence(tmp_path: Path) -> None:
    fixture = mutable_latest_fixture(tmp_path)
    _, _, _, _, _, evidence_dir = fixture
    shutil.rmtree(evidence_dir)
    assert latest_checks(fixture)["active_latest_authorized_provenance"]["status"] == "fail"


def test_arch1_mutable_latest_rejects_failed_forbidden_audit(tmp_path: Path) -> None:
    fixture = mutable_latest_fixture(tmp_path)
    _, _, _, _, _, evidence_dir = fixture
    forbidden_path = evidence_dir / "forbidden_action_audit.json"
    forbidden = json.loads(forbidden_path.read_text(encoding="utf-8"))
    forbidden["all_forbidden_false"] = False
    forbidden["forbidden_flags"]["provider_publish"] = True
    write_json(forbidden_path, forbidden)
    assert latest_checks(fixture)["active_latest_authorized_provenance"]["status"] == "fail"


def test_arch1_mutable_latest_rejects_prefix_only_authorization(tmp_path: Path) -> None:
    fixture = mutable_latest_fixture(tmp_path)
    _, _, _, _, _, evidence_dir = fixture
    authorization_path = evidence_dir / "authorization_scope.json"
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    authorization["authorized_by_user_exact_text"] = False
    authorization["persistent_authorization_id"] = "DAPR18_AUTO_PUBLISH_CHAIN_UNBOUND"
    write_json(authorization_path, authorization)

    assert latest_checks(fixture)["active_latest_authorized_provenance"]["status"] == "fail"
