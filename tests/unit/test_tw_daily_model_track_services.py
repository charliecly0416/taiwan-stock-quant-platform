from __future__ import annotations

import json
from pathlib import Path

from scripts.tw_daily_model_track_services import (
    _validate_signal_identity,
    build_model_track_services,
    capture_b19_twii_snapshot,
)


ROOT = Path(__file__).resolve().parents[2]
MODEL_ID = "e4_frozen_qlib_2018_2022"


def test_twii_capture_uses_write_once_child_and_logs_in_parent(tmp_path: Path) -> None:
    output = tmp_path / "shared" / "capture"

    def fake_runner(argv, **kwargs):
        assert not output.exists()
        assert kwargs["stdout_path"].parent == output.parent
        output.mkdir()
        (output / "TWII_NORMALIZED.csv").write_text("date,close\n", encoding="utf-8")
        (output / "TWII_CAPTURE_MANIFEST.json").write_text("{}", encoding="utf-8")
        return {"ok": True, "argv": argv}

    result = capture_b19_twii_snapshot(
        asof="2026-09-18",
        source_acquisition_run_id="source-1",
        next_session_open="2026-09-21T01:00:00+00:00",
        output_dir=output,
        root=ROOT,
        python="python",
        capture_runner=ROOT / "scripts/capture_modelb_b19r2r_twii_yahoo_v2.py",
        command_runner=fake_runner,
    )

    assert result["ok"] is True
    assert result["twii_csv"] == str(output / "TWII_NORMALIZED.csv")


def test_service_bridge_keeps_model_a_contained_and_forwards_same_cutoff(tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    def fake_runner(argv, **kwargs):
        calls.append({"argv": list(argv), "kwargs": kwargs})
        stdout_path = kwargs["stdout_path"]
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        if "run_tw_model_score_job.py" in " ".join(argv):
            output_root = Path(argv[argv.index("--output-root") + 1])
            run_id = argv[argv.index("--run-id") + 1]
            signal = output_root / "planned_future_outputs/model_signal_artifact" / MODEL_ID / run_id
            signal.mkdir(parents=True)
            asof = argv[argv.index("--asof") + 1]
            source_run_id = argv[argv.index("--source-acquisition-run-id") + 1]
            decision_cutoff = argv[argv.index("--decision-cutoff") + 1]
            (signal / "manifest.json").write_text(
                json.dumps({
                    "artifact_type": "ModelSignalArtifact",
                    "model_id": MODEL_ID,
                    "asof": asof,
                    "signal_asof": asof,
                    "source_acquisition_run_id": source_run_id,
                    "decision_cutoff": decision_cutoff,
                }),
                encoding="utf-8",
            )
            (signal / "signals.csv").write_text("date,instrument\n", encoding="utf-8")
            (signal / "validator_report.json").write_text(
                json.dumps({"ok": True, "status": "PASS"}), encoding="utf-8"
            )
            payload = {"pipeline_status": "SCORED_ASOF_TARGET"}
        elif "run_modelb_b19r2r_daily_shadow.py" in " ".join(argv):
            output = Path(argv[argv.index("--output-dir") + 1])
            output.mkdir(parents=True)
            asof = argv[argv.index("--asof") + 1]
            source_run_id = argv[argv.index("--source-acquisition-run-id") + 1]
            decision_cutoff = argv[argv.index("--decision-cutoff") + 1]
            (output / "manifest.json").write_text(
                json.dumps({
                    "artifact_type": "model_signal",
                    "model_id": "modelb_b19r2r_lambdarank_exact50_78f_v2",
                    "asof": asof,
                    "signal_asof": asof,
                    "source_acquisition_run_id": source_run_id,
                    "decision_cutoff": decision_cutoff,
                }),
                encoding="utf-8",
            )
            (output / "signals.csv").write_text("date,instrument\n", encoding="utf-8")
            (output / "validator_report.json").write_text(
                json.dumps({"ok": True, "status": "PASS"}), encoding="utf-8"
            )
            payload = {"ok": True, "status": "READY_RESEARCH_SHADOW", "artifact_dir": str(output)}
        else:
            payload = {"status": "READY"}
        stdout_path.write_text(json.dumps(payload), encoding="utf-8")
        return {"ok": True, "returncode": 0, "stdout_path": str(stdout_path)}

    def read_stdout(result):
        return json.loads(Path(result["stdout_path"]).read_text(encoding="utf-8"))

    services = build_model_track_services(
        root=ROOT,
        python="python",
        model_a_model_id=MODEL_ID,
        model_a_input_builder=ROOT / "scripts/build_tw_model_inference_input.py",
        model_a_score_runner=ROOT / "scripts/run_tw_model_score_job.py",
        b19r2r_runner=ROOT / "scripts/run_modelb_b19r2r_daily_shadow.py",
        command_runner=fake_runner,
        parse_json_stdout=read_stdout,
        timeout=30,
    )
    cutoff = "2026-09-18T10:00:00+00:00"
    model_a = services["model_a_scorer"]({
        "asof": "2026-09-18",
        "run_id": "batch__composite__a",
        "output_root": str(tmp_path / "model_a_stage"),
        "qlib_provider": str(tmp_path / "provider"),
        "qlib_normalized": str(tmp_path / "normalized"),
        "source_acquisition_run_id": "source-1",
        "decision_cutoff": cutoff,
    })
    assert model_a["ok"] is True
    score_argv = calls[1]["argv"]
    assert "--allow-contained-real-execution" in score_argv
    for flag in ("--no-publish", "--no-catalog", "--no-latest", "--no-target-output"):
        assert flag in score_argv

    rerank = services["b19r2r_reranker"]({
        "asof": "2026-09-18",
        "output_root": str(tmp_path / "b19r2r_stage"),
        "model_a_signal_artifact": model_a["model_signal_artifact"],
        "orthogonal_handoff": str(tmp_path / "handoff.json"),
        "source_acquisition_run_id": "source-1",
        "provider_snapshot": str(tmp_path / "provider"),
        "decision_cutoff": cutoff,
        "next_session_open": "2026-09-21T01:00:00+00:00",
        "twii_snapshot": {
            "twii_csv": str(tmp_path / "TWII_NORMALIZED.csv"),
            "twii_manifest": str(tmp_path / "TWII_CAPTURE_MANIFEST.json"),
        },
    })
    assert rerank["ok"] is True
    rerank_argv = calls[2]["argv"]
    assert rerank_argv[rerank_argv.index("--model-a-signal-dir") + 1] == model_a["model_signal_artifact"]
    assert rerank_argv[rerank_argv.index("--decision-cutoff") + 1] == cutoff
    assert rerank_argv[rerank_argv.index("--twii-csv") + 1].endswith("TWII_NORMALIZED.csv")


def test_signal_identity_rejects_wrong_model_even_when_validator_passes(
    tmp_path: Path,
) -> None:
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "artifact_type": "ModelSignalArtifact",
                "model_id": "wrong-model",
                "asof": "2026-09-18",
                "signal_asof": "2026-09-18",
                "source_acquisition_run_id": "source-1",
                "decision_cutoff": "2026-09-18T10:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "validator_report.json").write_text(
        json.dumps({"ok": True, "status": "PASS"}), encoding="utf-8"
    )

    errors = _validate_signal_identity(
        tmp_path,
        expected_model_id=MODEL_ID,
        asof="2026-09-18",
        source_acquisition_run_id="source-1",
        decision_cutoff="2026-09-18T10:00:00+00:00",
    )

    assert errors == ["model_id_mismatch"]


def test_b19_runner_blocker_status_is_not_misreported_as_model_identity(
    tmp_path: Path,
) -> None:
    def fake_runner(argv, **kwargs):
        stdout_path = kwargs["stdout_path"]
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        command = " ".join(argv)
        if "run_tw_model_score_job.py" in command:
            output_root = Path(argv[argv.index("--output-root") + 1])
            run_id = argv[argv.index("--run-id") + 1]
            signal = output_root / "planned_future_outputs/model_signal_artifact" / MODEL_ID / run_id
            signal.mkdir(parents=True)
            asof = argv[argv.index("--asof") + 1]
            source_run_id = argv[argv.index("--source-acquisition-run-id") + 1]
            cutoff = argv[argv.index("--decision-cutoff") + 1]
            (signal / "manifest.json").write_text(
                json.dumps({
                    "artifact_type": "ModelSignalArtifact",
                    "model_id": MODEL_ID,
                    "asof": asof,
                    "signal_asof": asof,
                    "source_acquisition_run_id": source_run_id,
                    "decision_cutoff": cutoff,
                }),
                encoding="utf-8",
            )
            (signal / "signals.csv").write_text("date,instrument\n", encoding="utf-8")
            (signal / "validator_report.json").write_text(
                json.dumps({"ok": True, "status": "PASS"}), encoding="utf-8"
            )
            stdout_path.write_text(
                json.dumps({"pipeline_status": "SCORED_ASOF_TARGET"}), encoding="utf-8"
            )
            return {"ok": True, "returncode": 0, "stdout_path": str(stdout_path)}
        if "run_modelb_b19r2r_daily_shadow.py" in command:
            output = Path(argv[argv.index("--output-dir") + 1])
            output.mkdir(parents=True)
            blocker = {
                "ok": False,
                "status": "B19R2R_BLOCKED_HANDOFF_SOURCES",
                "error_code": "B19R2R_BLOCKED_HANDOFF_SOURCES",
            }
            (output / "manifest.json").write_text(
                json.dumps({**blocker, "artifact_type": "ModelSignalArtifact"}),
                encoding="utf-8",
            )
            stdout_path.write_text(json.dumps(blocker), encoding="utf-8")
            return {"ok": False, "returncode": 2, "stdout_path": str(stdout_path)}
        stdout_path.write_text(json.dumps({"status": "READY"}), encoding="utf-8")
        return {"ok": True, "returncode": 0, "stdout_path": str(stdout_path)}

    def read_stdout(result):
        return json.loads(Path(result["stdout_path"]).read_text(encoding="utf-8"))

    services = build_model_track_services(
        root=ROOT,
        python="python",
        model_a_model_id=MODEL_ID,
        model_a_input_builder=ROOT / "scripts/build_tw_model_inference_input.py",
        model_a_score_runner=ROOT / "scripts/run_tw_model_score_job.py",
        b19r2r_runner=ROOT / "scripts/run_modelb_b19r2r_daily_shadow.py",
        command_runner=fake_runner,
        parse_json_stdout=read_stdout,
        timeout=30,
    )
    model_a = services["model_a_scorer"](
        {
            "asof": "2026-09-18",
            "run_id": "batch__a",
            "output_root": str(tmp_path / "model_a_stage"),
            "qlib_provider": str(tmp_path / "provider"),
            "qlib_normalized": str(tmp_path / "normalized"),
            "source_acquisition_run_id": "source-1",
            "decision_cutoff": "2026-09-18T10:00:00+00:00",
        }
    )
    result = services["b19r2r_reranker"](
        {
            "asof": "2026-09-18",
            "output_root": str(tmp_path / "b19r2r_stage"),
            "model_a_signal_artifact": model_a["model_signal_artifact"],
            "orthogonal_handoff": str(tmp_path / "handoff.json"),
            "source_acquisition_run_id": "source-1",
            "provider_snapshot": str(tmp_path / "provider"),
            "decision_cutoff": "2026-09-18T10:00:00+00:00",
            "next_session_open": "2026-09-21T01:00:00+00:00",
            "twii_snapshot": {},
        }
    )

    assert result["ok"] is False
    assert result["status"] == "B19R2R_BLOCKED_HANDOFF_SOURCES"
    assert result["artifact_identity_errors"] == []
