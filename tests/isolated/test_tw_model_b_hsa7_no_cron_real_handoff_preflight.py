import json
import os
import tempfile
import unittest
import hashlib
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "scripts"))
import build_tw_model_b_hsa7_no_cron_real_handoff_preflight as hsa7


class HSA7ContractTests(unittest.TestCase):
    def test_synthetic_dirs_are_excluded(self):
        with patch.object(hsa7, "OPS_ROOT", Path(tempfile.mkdtemp())) as root:
            (root / "hsa7_synthetic").mkdir(); (root / "hsa7_synthetic" / "job.json").write_text("{}")
            (root / "daily_tw_stock_auto_update_20260825_20260825T144502Z").mkdir()
            for name in ("job.json", "daily_source_inventory.json"):
                (root / "daily_tw_stock_auto_update_20260825_20260825T144502Z" / name).write_text("{}")
            self.assertEqual(len(hsa7._real_job_dirs()), 1)

    def test_only_strict_daily_job_names_are_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("finmind_segment_cache", "qald_state", "dng_evidence", "daily_job_backup"):
                (root / name).mkdir()
                (root / name / "job.json").write_text("{}")
            candidate = root / "daily_tw_stock_auto_update_20260826_20260826T103000Z"
            candidate.mkdir(); (candidate / "job.json").write_text("{}")
            with patch.object(hsa7, "OPS_ROOT", root):
                with self.assertRaises(hsa7.HSA7DiscoveryError) as caught:
                    hsa7._real_job_dirs()
            self.assertEqual(len(caught.exception.summaries), 1)
            self.assertEqual(caught.exception.summaries[0]["job_dir"], str(candidate))
            self.assertIn("daily_source_inventory.json", caught.exception.summaries[0]["discovery_error"])

    def test_historical_missing_inventory_is_quarantined_not_global_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "daily_tw_stock_auto_update_20260820_20260820T103000Z"; old.mkdir()
            (old / "job.json").write_text(json.dumps({"job_id": "old", "asof": "2026-08-20"}))
            current = root / "daily_tw_stock_auto_update_20260826_20260826T103000Z"; current.mkdir()
            (current / "job.json").write_text(json.dumps({"job_id": "current", "asof": "2026-08-26"}))
            (current / "daily_source_inventory.json").write_text("{}")
            with patch.object(hsa7, "OPS_ROOT", root):
                result = hsa7._real_job_dirs()
                legacy = hsa7._legacy_incomplete_summaries()
            self.assertEqual(result, [current])
            self.assertEqual(legacy[0]["classification"], "legacy_incomplete/quarantined")

    def test_inventory_is_not_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); job = root / "job"; job.mkdir()
            (job / "job.json").write_text(json.dumps({"job_id": "run", "asof": "2026-08-25"}))
            (job / "daily_source_inventory.json").write_text(json.dumps({"sources": {"institutional_flow": {"evidence_path": "stdout"}}}))
            self.assertEqual(hsa7._handoff_candidates(job), [])

    def test_handoff_rejects_missing_families(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); job = root / "job"; job.mkdir(); p = job / hsa7.HANDOFF_NAME
            (job / "job.json").write_text(json.dumps({"job_id": "run", "asof": "2026-08-25"}))
            p.write_text(json.dumps({"schema_version": "x", "acquisition_run_id": "run", "target_asof": "2026-08-25", "sources": []}))
            result = hsa7._validate_handoff(p, job, {"job_id": "run", "asof": "2026-08-25"})
            self.assertFalse(result["valid"]); self.assertTrue(any("source_family" in gap for gap in result["gaps"]))

    def test_handoff_rejects_stdout_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); job = root / "job"; job.mkdir(); p = job / hsa7.HANDOFF_NAME
            (job / "job.json").write_text(json.dumps({"job_id": "run", "asof": "2026-08-25"}))
            sources = [{"source_family": family, "source_id": family, "source_validator_status": "PASS", "source_published_at": "2026-08-25T00:00:00+00:00", "available_at": "2026-08-25T01:00:00+00:00", "fetched_at": "2026-08-25T02:00:00+00:00", "expected_scope": ["x"], "returned_scope": ["x"], "absent_scope": [], "unknown_scope": [], "raw_files": [{"path": str(job / "stdout.json"), "role": "stdout", "sha256": "0" * 64}], "normalized_files": [{"path": str(job / "norm.json"), "role": "provider_normalized_payload", "sha256": "0" * 64}]} for family in hsa7.REQUIRED]
            p.write_text(json.dumps({"acquisition_run_id": "run", "target_asof": "2026-08-25", "sources": sources}))
            result = hsa7._validate_handoff(p, job, {"job_id": "run", "asof": "2026-08-25"})
            self.assertFalse(result["valid"])

    def _valid_handoff(self, job: Path):
        run_id = "daily.acquire.20260825.real"
        sources = []
        for family in hsa7.REQUIRED:
            raw = job / f"{family}.raw.json"; normalized = job / f"{family}.normalized.json"
            raw.write_text('{"raw":true}'); normalized.write_text('{"normalized":true}')
            sources.append({
                "source_family": family, "source_id": f"finmind.{family}.v4",
                "acquisition_run_id": run_id, "provider": "FinMind",
                "request_parameters": {"dataset": family},
                "raw_artifact_role": "provider_raw_response",
                "normalized_artifact_role": "provider_normalized_payload",
                "source_validator_status": "PASS",
                "source_published_at": "2026-08-25T00:00:00+00:00",
                "available_at": "2026-08-25T01:00:00+00:00",
                "fetched_at": "2026-08-25T02:00:00+00:00",
                "expected_scope": ["2330", "2317"], "returned_scope": ["2330"],
                "absent_scope": ["2317"], "unknown_scope": [],
                "raw_files": [{"path": str(raw), "role": "provider_raw_response", "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()}],
                "normalized_files": [{"path": str(normalized), "role": "provider_normalized_payload", "sha256": hashlib.sha256(normalized.read_bytes()).hexdigest()}],
            })
        payload = {"schema_version": hsa7.HANDOFF_SCHEMA_VERSION, "acquisition_run_id": run_id, "target_asof": "2026-08-25", "sources": sources}
        return payload, sources

    def test_valid_handoff_passes_strict_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = Path(tmp) / "job"; job.mkdir()
            payload, _ = self._valid_handoff(job); (job / "job.json").write_text(json.dumps({"job_id": "daily.acquire.20260825.real", "asof": "2026-08-25"}))
            p = job / hsa7.HANDOFF_NAME; p.write_text(json.dumps(payload))
            self.assertTrue(hsa7._validate_handoff(p, job, json.loads((job / "job.json").read_text()))["valid"])

    def test_handoff_rejects_pit_scope_hash_path_run_and_schema_contracts(self):
        mutations = (
            ("schema_version", "wrong"),
            ("acquisition_run_id", "other.run"),
        )
        for field, value in mutations:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                job = Path(tmp) / "job"; job.mkdir(); payload, sources = self._valid_handoff(job)
                payload[field] = value; p = job / hsa7.HANDOFF_NAME; p.write_text(json.dumps(payload))
                self.assertFalse(hsa7._validate_handoff(p, job, {"job_id": "daily.acquire.20260825.real", "asof": "2026-08-25"})["valid"])

    def test_handoff_rejects_pit_scope_hash_path_and_status(self):
        cases = ("pit", "scope", "hash", "path", "status", "role")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                job = Path(tmp) / "job"; job.mkdir(); payload, sources = self._valid_handoff(job)
                source = sources[0]
                if case == "pit": source["available_at"] = "2026-08-25T03:00:00+00:00"
                elif case == "scope": source["absent_scope"] = ["2330"]
                elif case == "hash": source["raw_files"][0]["sha256"] = "0" * 64
                elif case == "path": source["raw_files"][0]["path"] = str(Path(tmp) / "outside.json")
                elif case == "status": source["source_validator_status"] = "WARN"
                else: source["normalized_files"][0]["role"] = "stdout"
                p = job / hsa7.HANDOFF_NAME; p.write_text(json.dumps(payload))
                self.assertFalse(hsa7._validate_handoff(p, job, {"job_id": "daily.acquire.20260825.real", "asof": "2026-08-25"})["valid"])

    def test_handoff_rejects_source_level_artifact_roles(self):
        for field, value in (("raw_artifact_role", "stdout"), ("normalized_artifact_role", "cache")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                job = Path(tmp) / "job"; job.mkdir(); payload, sources = self._valid_handoff(job)
                sources[0][field] = value
                p = job / hsa7.HANDOFF_NAME; p.write_text(json.dumps(payload))
                self.assertFalse(hsa7._validate_handoff(p, job, {"job_id": "daily.acquire.20260825.real", "asof": "2026-08-25"})["valid"])

    def test_nested_excluded_candidate_is_not_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = Path(tmp) / "job"; (job / "nested" / "synthetic" / "deep").mkdir(parents=True)
            (job / "nested" / "synthetic" / "deep" / hsa7.HANDOFF_NAME).write_text("{}")
            self.assertEqual(hsa7._handoff_candidates(job), [])

    def test_symlinked_candidate_is_not_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); job = root / "job"; job.mkdir(); outside = root / "outside"; outside.mkdir()
            (outside / hsa7.HANDOFF_NAME).write_text("{}")
            (job / "linked").symlink_to(outside, target_is_directory=True)
            self.assertEqual(hsa7._handoff_candidates(job), [])

    def test_job_discovery_secure_read_error_is_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            ops = Path(tmp) / "ops"; ops.mkdir(); job = ops / "daily_tw_stock_auto_update_20260826_20260826T103000Z"; job.mkdir()
            (job / "job.json").write_text("{}")
            (job / "daily_source_inventory.json").write_text("{}")
            original = hsa7._secure_read
            def fail_inventory(path):
                if Path(path).name == "daily_source_inventory.json":
                    raise hsa7.HSA7Error("permission_denied")
                return original(path)
            with patch.object(hsa7, "OPS_ROOT", ops), patch.object(hsa7, "_secure_read", side_effect=fail_inventory):
                with self.assertRaises(hsa7.HSA7DiscoveryError) as caught:
                    hsa7._real_job_dirs()
            self.assertEqual(caught.exception.summaries[0]["job_dir"], str(job))
            self.assertIn("permission_denied", caught.exception.summaries[0]["discovery_error"])

    def test_discovery_error_writes_stop_evidence_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            error = hsa7.HSA7DiscoveryError("job_discovery_error", [{"job_dir": "/tmp/job", "discovery_error": "race"}])
            with patch.object(hsa7, "_protected", side_effect=hsa7.HSA7Error("crontab_denied")), patch.object(hsa7, "_real_job_dirs", side_effect=error):
                result = hsa7.build_preflight(out)
            self.assertEqual(result["decision"], hsa7.STOP)
            inventory = json.loads((out / "real_job_inventory.json").read_text())
            self.assertTrue(inventory["stopped_before_handoff_validation"])
            self.assertEqual(inventory["jobs"][0]["discovery_error"], "race")

    def test_successful_crontab_gate_before_fingerprint_is_written_on_discovery_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            before = {"actual_crontab_locator": {"sha256": "before"}}
            after = {"actual_crontab_locator": {"sha256": "after"}}
            error = hsa7.HSA7DiscoveryError("job_discovery_error", [{"job_dir": "/tmp/job", "discovery_error": "permission"}])
            with patch.object(hsa7, "_protected", side_effect=[before, after]), patch.object(hsa7, "_real_job_dirs", side_effect=error):
                hsa7.build_preflight(out)
            protected = json.loads((out / "protected_paths_fingerprint.json").read_text())
            self.assertEqual(protected["before"], before)
            self.assertEqual(protected["after"], after)
            self.assertFalse(protected["unchanged"])

    def test_manifest_recursively_includes_nested_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); nested = root / "nested"; nested.mkdir()
            (nested / "manifest.json").write_text("nested")
            (root / "evidence.json").write_text("evidence")
            hsa7._write_manifest(root, hsa7.STOP)
            payload = json.loads((root / "manifest.json").read_text())
            paths = {item["path"] for item in payload["artifacts"]}
            self.assertIn("nested/manifest.json", paths)
            self.assertIn("evidence.json", paths)

    def test_output_duplicate_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / "x").write_text("x")
            with self.assertRaises(hsa7.HSA7Error): hsa7._write_new(root / "x", b"y")

    def test_protected_failure_writes_stop_evidence_without_fake_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(hsa7, "_protected", side_effect=hsa7.HSA7Error("actual_crontab_read_failed")):
                ops_root = Path(tmp) / "ops"
                ops_root.mkdir()
                with patch.object(hsa7, "OPS_ROOT", ops_root):
                    result = hsa7.build_preflight(Path(tmp) / "out")
            self.assertEqual(result["decision"], hsa7.STOP)
            protected = json.loads((Path(tmp) / "out/protected_paths_fingerprint.json").read_text())
            self.assertFalse(protected["unchanged"])
            self.assertIsNone(protected["after"])
            self.assertTrue((Path(tmp) / "out/manifest.json").is_file())


if __name__ == "__main__": unittest.main()
