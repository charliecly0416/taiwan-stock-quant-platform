#!/usr/bin/env python3
"""Translate daily model-track requests into the existing frozen scorers."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

import json


CommandRunner = Callable[..., dict[str, Any]]
JsonReader = Callable[[dict[str, Any]], dict[str, Any]]
B19R2R_MODEL_ID = "modelb_b19r2r_lambdarank_exact50_78f_v2"


def _validate_signal_identity(
    artifact_dir: Path,
    *,
    expected_model_id: str,
    asof: str,
    source_acquisition_run_id: str,
    decision_cutoff: str,
) -> list[str]:
    errors: list[str] = []
    try:
        manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
        validator = json.loads(
            (artifact_dir / "validator_report.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        return [f"artifact_sidecar_invalid:{type(exc).__name__}"]
    if manifest.get("artifact_type") not in {"ModelSignalArtifact", "model_signal"}:
        errors.append("artifact_type_mismatch")
    if manifest.get("model_id") != expected_model_id:
        errors.append("model_id_mismatch")
    if manifest.get("asof") != asof or manifest.get("signal_asof") != asof:
        errors.append("signal_asof_mismatch")
    if manifest.get("source_acquisition_run_id") != source_acquisition_run_id:
        errors.append("source_acquisition_run_id_mismatch")
    if manifest.get("decision_cutoff") != decision_cutoff:
        errors.append("decision_cutoff_mismatch")
    if validator.get("ok") is not True or validator.get("status") != "PASS":
        errors.append("validator_not_passed")
    return errors


def capture_b19_twii_snapshot(
    *,
    asof: str,
    source_acquisition_run_id: str,
    next_session_open: str,
    output_dir: Path,
    root: Path,
    python: str,
    capture_runner: Path,
    command_runner: CommandRunner,
    timeout: int = 180,
) -> dict[str, Any]:
    """Capture the last shared PIT input before sealing the batch cutoff."""
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    command = command_runner(
        [python, str(capture_runner.relative_to(root)), "--output", str(output_dir)],
        cwd=root,
        stdout_path=output_dir.parent / "capture_stdout.json",
        stderr_path=output_dir.parent / "capture_stderr.txt",
        timeout=timeout,
        env={
            "B19YTWII_RESEARCH_ROOT": str(output_dir.parent),
            "B19YTWII_TARGET_ASOF": asof,
            "B19YTWII_ACQUISITION_RUN_ID": source_acquisition_run_id,
            "B19YTWII_SESSION_CLOSE_UTC": f"{asof}T05:30:00+00:00",
            "B19YTWII_NEXT_OPEN_UTC": next_session_open,
        },
    )
    csv_path = output_dir / "TWII_NORMALIZED.csv"
    manifest_path = output_dir / "TWII_CAPTURE_MANIFEST.json"
    ok = bool(command.get("ok") and csv_path.is_file() and manifest_path.is_file())
    return {
        "ok": ok,
        "status": "READY" if ok else "BLOCKED_TWII_CAPTURE",
        "command": command,
        "twii_csv": str(csv_path),
        "twii_manifest": str(manifest_path),
    }


def build_model_track_services(
    *,
    root: Path,
    python: str,
    model_a_model_id: str,
    model_a_input_builder: Path,
    model_a_score_runner: Path,
    b19r2r_runner: Path,
    command_runner: CommandRunner,
    parse_json_stdout: JsonReader,
    timeout: int,
) -> dict[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]]:
    """Build injected scorer services without adding model logic to orchestration."""

    def model_a_scorer(raw_request: Mapping[str, Any]) -> Mapping[str, Any]:
        request = dict(raw_request)
        stage_root = Path(str(request["output_root"]))
        stage_root.mkdir(parents=True, exist_ok=True)
        run_id = str(request["run_id"])
        input_dir = (
            stage_root
            / "planned_future_outputs/model_inference_input"
            / model_a_model_id
            / run_id
        )
        signal_dir = (
            stage_root
            / "planned_future_outputs/model_signal_artifact"
            / model_a_model_id
            / run_id
        )
        common = [
            "--provider-root", str(request["qlib_provider"]),
            "--normalized-root", str(request["qlib_normalized"]),
            "--output-root", str(stage_root),
            "--no-publish", "--no-catalog", "--no-latest", "--no-target-output",
            "--json",
        ]
        build_result = command_runner(
            [
                python, str(model_a_input_builder.relative_to(root)),
                "--asof", str(request["asof"]),
                "--run-id", run_id,
                *common,
            ],
            cwd=root,
            stdout_path=stage_root / "model_a_input_stdout.json",
            stderr_path=stage_root / "model_a_input_stderr.txt",
            timeout=timeout,
        )
        if not build_result.get("ok"):
            return {
                "ok": False,
                "status": "BLOCKED_MODELA_INPUT",
                "input_builder": build_result,
            }
        score_result = command_runner(
            [
                python, str(model_a_score_runner.relative_to(root)),
                "--asof", str(request["asof"]),
                "--run-id", run_id,
                "--input-dir", str(input_dir),
                "--source-acquisition-run-id", str(request["source_acquisition_run_id"]),
                "--decision-cutoff", str(request["decision_cutoff"]),
                *common[:-1],
                "--allow-contained-real-execution",
                "--json",
            ],
            cwd=root,
            stdout_path=stage_root / "model_a_score_stdout.json",
            stderr_path=stage_root / "model_a_score_stderr.txt",
            timeout=timeout,
        )
        payload = parse_json_stdout(score_result)
        identity_errors = _validate_signal_identity(
            signal_dir,
            expected_model_id=model_a_model_id,
            asof=str(request["asof"]),
            source_acquisition_run_id=str(request["source_acquisition_run_id"]),
            decision_cutoff=str(request["decision_cutoff"]),
        )
        ok = bool(
            score_result.get("ok")
            and payload.get("pipeline_status") == "SCORED_ASOF_TARGET"
            and (signal_dir / "manifest.json").is_file()
            and (signal_dir / "signals.csv").is_file()
            and (signal_dir / "validator_report.json").is_file()
            and not identity_errors
        )
        return {
            "ok": ok,
            "status": (
                str(payload.get("pipeline_status") or "BLOCKED_MODELA_SCORE")
                if not identity_errors
                else "BLOCKED_MODELA_ARTIFACT_IDENTITY"
            ),
            "model_signal_artifact": str(signal_dir) if ok else "",
            "artifact_identity_errors": identity_errors,
            "input_builder": build_result,
            "score_job": score_result,
            "score_payload": payload,
        }

    def b19r2r_reranker(raw_request: Mapping[str, Any]) -> Mapping[str, Any]:
        request = dict(raw_request)
        output_dir = Path(str(request["output_root"]))
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        twii = request.get("twii_snapshot")
        twii = dict(twii) if isinstance(twii, Mapping) else {}
        command = command_runner(
            [
                python, str(b19r2r_runner.relative_to(root)),
                "--asof", str(request["asof"]),
                "--output-dir", str(output_dir),
                "--model-a-signal-dir", str(request["model_a_signal_artifact"]),
                "--handoff-validation", str(request["orthogonal_handoff"]),
                "--source-acquisition-run-id", str(request["source_acquisition_run_id"]),
                "--provider-snapshot", str(request["provider_snapshot"]),
                "--decision-cutoff", str(request["decision_cutoff"]),
                "--next-session-open", str(request["next_session_open"]),
                "--twii-csv", str(twii.get("twii_csv") or ""),
                "--twii-manifest", str(twii.get("twii_manifest") or ""),
                "--json",
            ],
            cwd=root,
            stdout_path=output_dir.parent / "b19r2r_stdout.json",
            stderr_path=output_dir.parent / "b19r2r_stderr.txt",
            timeout=timeout,
        )
        payload = parse_json_stdout(command)
        # A failed shadow runner writes a blocker manifest with the generic
        # ModelSignalArtifact shape.  Its identity fields are intentionally
        # absent, so propagate the runner's contract error before attempting
        # success-only artifact identity validation.
        if not command.get("ok") or payload.get("ok") is not True:
            return {
                "ok": False,
                "status": str(
                    payload.get("status")
                    or payload.get("error_code")
                    or "BLOCKED_B19R2R"
                ),
                "model_signal_artifact": "",
                "artifact_identity_errors": [],
                "runner": command,
                "runner_payload": payload,
            }
        artifact_dir = Path(str(payload.get("artifact_dir") or output_dir))
        if not artifact_dir.is_absolute():
            artifact_dir = root / artifact_dir
        identity_errors = _validate_signal_identity(
            artifact_dir,
            expected_model_id=B19R2R_MODEL_ID,
            asof=str(request["asof"]),
            source_acquisition_run_id=str(request["source_acquisition_run_id"]),
            decision_cutoff=str(request["decision_cutoff"]),
        )
        ok = bool(
            command.get("ok")
            and payload.get("ok")
            and (artifact_dir / "manifest.json").is_file()
            and (artifact_dir / "signals.csv").is_file()
            and (artifact_dir / "validator_report.json").is_file()
            and not identity_errors
        )
        return {
            "ok": ok,
            "status": (
                str(payload.get("status") or "BLOCKED_B19R2R")
                if not identity_errors
                else "BLOCKED_B19R2R_ARTIFACT_IDENTITY"
            ),
            "model_signal_artifact": str(artifact_dir) if ok else "",
            "artifact_identity_errors": identity_errors,
            "runner": command,
            "runner_payload": payload,
        }

    return {
        "model_a_scorer": model_a_scorer,
        "b19r2r_reranker": b19r2r_reranker,
    }
