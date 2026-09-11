from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts/run_tw_model_score_job.py"

if str(SCRIPT_PATH.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_PATH.parent))

spec = importlib.util.spec_from_file_location("tw_model_score_job_cron_python", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_run_qlib_uses_current_interpreter_for_cron_safe_subprocess(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(cmd, **kwargs):
        calls.append({"cmd": cmd, "kwargs": kwargs})
        return SimpleNamespace(returncode=0, stdout='{"run_id":"r","run_dir":"d","artifacts":{}}', stderr="")

    monkeypatch.delenv("TW_MODELA_SCORE_JOB_PYTHON", raising=False)
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module, "parse_run_json", lambda _stdout: {"run_id": "r", "run_dir": "d", "artifacts": {}})

    module.run_qlib("2026-08-14")

    assert calls
    cmd = calls[0]["cmd"]
    assert cmd[0] == sys.executable
    assert cmd[0] != "python"
    assert "run_option_c_daily_signal_option_c_provider.py" in cmd[1]
    assert module.qlib_subprocess_command("2026-08-14") == cmd


def test_run_qlib_allows_explicit_python_override(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(cmd, **kwargs):
        calls.append({"cmd": cmd, "kwargs": kwargs})
        return SimpleNamespace(returncode=0, stdout='{"run_id":"r","run_dir":"d","artifacts":{}}', stderr="")

    monkeypatch.setenv("TW_MODELA_SCORE_JOB_PYTHON", "/opt/conda/bin/python")
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module, "parse_run_json", lambda _stdout: {"run_id": "r", "run_dir": "d", "artifacts": {}})

    module.run_qlib("2026-08-14")

    assert calls[0]["cmd"][0] == "/opt/conda/bin/python"
    assert module.qlib_subprocess_command("2026-08-14")[0] == "/opt/conda/bin/python"


def test_write_signal_sidecars_writes_model_signal_validator_report(tmp_path) -> None:
    signals = pd.DataFrame(
        [
            {
                "date": "2026-08-14",
                "instrument": f"TW{i:04d}",
                "model_name": module.MODEL_ID,
                "model_family": "qlib",
                "candidate_rank": i,
                "buy_score": 151 - i,
                "raw_score": 151 - i,
                "score_rank": i,
                "full_qlib_rank": i,
                "signal_asof": "2026-08-14",
                "available_at": "2026-08-14",
                "source_artifact": "prediction.csv",
                "source_model_artifact": "params.pkl",
                "source_feature_artifact": "provider",
            }
            for i in range(1, 151)
        ]
    )[module.SIGNAL_FIELDS]
    signal_dir = tmp_path / "signal"

    module.write_signal_sidecars(
        signal_dir,
        signals,
        "2026-08-14",
        "cron_path_repair_test",
        {"artifacts": {"prediction": "prediction.csv"}, "run_dir": "qlib_run"},
    )

    validator = json.loads((signal_dir / "validator_report.json").read_text(encoding="utf-8"))
    manifest = json.loads((signal_dir / "manifest.json").read_text(encoding="utf-8"))
    assert validator["ok"] is True
    assert validator["status"] == "PASS"
    assert validator["artifact_type"] == "ModelSignalArtifact"
    assert validator["signal_rows"] == 150
    assert manifest["files"]["validator_report"] == "validator_report.json"
