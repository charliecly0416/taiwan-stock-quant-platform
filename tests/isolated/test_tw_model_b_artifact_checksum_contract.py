import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_daily_tw_stock_auto_update.py"


def test_real_same_run_handoff_emits_verifiable_artifacts(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("daily_runtime_checksum", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    captured = {}

    def fake_build(root, run_id, asof, sources, output):
        captured["sources"] = sources
        return output / "same_run_acquisition_handoff_manifest.json"

    monkeypatch.setattr(module.hsa8, "build_runtime_handoff", fake_build)
    capture = {}
    for family in ("daily_price", "institutional", "margin", "twii"):
        raw = tmp_path / f"{family}.raw.json"
        normalized = tmp_path / f"{family}.normalized.json"
        adapter = tmp_path / f"{family}.adapter.json"
        raw.write_text(json.dumps({"family": family}), encoding="utf-8")
        normalized.write_text(json.dumps({"family": family}), encoding="utf-8")
        adapter.write_text(json.dumps({"family": family}), encoding="utf-8")
        capture[family] = {
            "adapter_output_path": str(adapter),
            "raw_paths": [str(raw)],
            "normalized_paths": [str(normalized)],
        }
    job = {
        "job_id": "checksum.contract.test",
        "asof": "2026-09-15",
        "finmind_update": {"hsa8_capture": capture, "segment_results": {}},
    }
    result = module.build_real_same_run_handoff(job=job, job_dir=tmp_path, symbols=[])
    assert result["ok"] is True
    assert len(captured["sources"]) == 4
    for source in captured["sources"]:
        assert source["artifacts"]
        for artifact in source["artifacts"]:
            path = Path(artifact["path"])
            assert path.is_file()
            assert artifact["sha256"] == module.file_fingerprint(path)["sha256"]
