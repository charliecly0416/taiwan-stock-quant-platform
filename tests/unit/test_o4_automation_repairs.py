from __future__ import annotations

import importlib.util
import json
import multiprocessing
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _append_worker(args: tuple[str, dict[str, str]]) -> str:
    builder = load("o4_builder_worker", ROOT / "scripts/build_modelb_o4_prospective_shadow.py")
    return builder.append_ledger(Path(args[0]), args[1])


def _ledger_row(asof: str, run_id: str) -> dict[str, str]:
    return {
        "asof": asof, "source_run_id": run_id, "decision_cutoff": f"{asof}T10:47:00+00:00",
        "status": "ACCEPTED_PROSPECTIVE_INPUT", "accepted": "true", "warmup_counted": "true",
        "feature_rows": "150", "scored_rows": "50", "model_a_top50_rows": "50",
        "feature_frame_sha256": "f" * 64, "model_b_signals_sha256": "b" * 64,
        "reason": "", "recorded_at": f"{asof}T11:00:00+00:00",
    }


def test_model_signal_gate_has_explicit_cutoff_and_no_outer_job_lookup() -> None:
    source = (ROOT / "scripts/run_daily_tw_stock_auto_update.py").read_text(encoding="utf-8")
    start = source.index("def run_model_signal_gate(")
    end = source.index("\ndef ", start + 10)
    block = source[start:end]
    assert "decision_cutoff: str = \"\"" in block
    assert "decision_cutoff," in block
    assert 'job.get("mbcds3_decision_cutoff")' not in block


def test_model_signal_decision_cutoff_accepts_timezone_and_rejects_missing_or_naive() -> None:
    daily = load("daily_cutoff_repairs", ROOT / "scripts/run_daily_tw_stock_auto_update.py")
    assert daily.validate_model_signal_decision_cutoff("2026-09-08T10:47:00+00:00") == "2026-09-08T10:47:00+00:00"
    for invalid in ("", "2026-09-08T10:47:00"):
        try:
            daily.validate_model_signal_decision_cutoff(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected invalid cutoff to fail: {invalid!r}")


def test_o4_ledger_exact_duplicate_is_noop_and_same_day_conflict_is_quarantined(tmp_path: Path) -> None:
    builder = load("o4_builder_repairs", ROOT / "scripts/build_modelb_o4_prospective_shadow.py")
    ledger = tmp_path / "observations.csv"
    row = {
        "asof": "2026-09-08",
        "source_run_id": "run-a",
        "decision_cutoff": "2026-09-08T10:47:00+00:00",
        "status": "ACCEPTED_PROSPECTIVE_INPUT",
        "accepted": "true",
        "warmup_counted": "true",
        "feature_rows": "150",
        "scored_rows": "50",
        "model_a_top50_rows": "50",
        "feature_frame_sha256": "f" * 64,
        "model_b_signals_sha256": "b" * 64,
        "reason": "",
        "recorded_at": "2026-09-08T11:00:00+00:00",
    }
    assert builder.append_ledger(ledger, row) == "APPENDED"
    before = ledger.read_bytes()
    duplicate = dict(row, recorded_at="2026-09-08T12:00:00+00:00")
    assert builder.append_ledger(ledger, duplicate) == "NOOP_ALREADY_RECORDED"
    assert ledger.read_bytes() == before
    conflict = dict(row, source_run_id="run-b", recorded_at="2026-09-08T12:01:00+00:00")
    assert builder.append_ledger(ledger, conflict) == "QUARANTINED_SAME_DAY_CONFLICT"
    assert ledger.read_bytes() == before
    quarantines = list(tmp_path.glob("observations.conflict.*.json"))
    assert len(quarantines) == 1
    assert json.loads(quarantines[0].read_text(encoding="utf-8"))["status"] == "QUARANTINED_SAME_DAY_CONFLICT"


def test_o4_ledger_concurrent_distinct_appends_are_serialized(tmp_path: Path) -> None:
    ledger = tmp_path / "observations.csv"
    rows = [
        _ledger_row("2026-09-08", "run-a"),
        _ledger_row("2026-09-09", "run-b"),
    ]
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(2) as pool:
        results = pool.map(_append_worker, [(str(ledger), row) for row in rows])
    assert sorted(results) == ["APPENDED", "APPENDED"]
    records = list(__import__("csv").DictReader(ledger.open(encoding="utf-8")))
    assert [(row["asof"], row["source_run_id"]) for row in records] == [("2026-09-08", "run-a"), ("2026-09-09", "run-b")]
    assert all(row["row_sha256"] for row in records)


def test_o4_nonblocking_adapter_missing_inputs_is_terminal_and_nonblocking(tmp_path: Path) -> None:
    adapter = load("o4_nonblocking_adapter", ROOT / "scripts/run_modelb_o4_prospective_shadow_nonblocking.py")
    parser = adapter.argparse.ArgumentParser()
    parser.add_argument("--asof", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--decision-cutoff", required=True)
    parser.add_argument("--job-dir", required=True, type=Path)
    parser.add_argument("--model-a-signals", action="append", default=[])
    parser.add_argument("--daily-price-adapter", default="")
    parser.add_argument("--institutional-adapter", default="")
    parser.add_argument("--margin-adapter", default="")
    parser.add_argument("--twii-raw", default="")
    parser.add_argument("--twii-capture", default="")
    parser.add_argument("--calendar", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--ledger", default="")
    args = parser.parse_args([
        "--asof", "2026-09-09", "--source-run-id", "run", "--decision-cutoff", "2026-09-09T10:00:00+00:00",
        "--job-dir", str(tmp_path), "--ledger", str(tmp_path / "observations.csv"),
        "--output-dir", str(tmp_path / "output"),
    ])
    result = adapter.run(args)
    assert result["status"] == "BLOCKED_SOURCE_NOT_READY_NONBLOCKING"
    assert result["model_a_nonblocking"] is True
    status = json.loads((tmp_path / "o4_prospective_shadow_status.json").read_text(encoding="utf-8"))
    assert status["protected_unchanged"] is True


def test_daily_full_refresh_calls_o4_before_its_terminal_return() -> None:
    source = (ROOT / "scripts/run_daily_tw_stock_auto_update.py").read_text(encoding="utf-8")
    full = source.index("if full_orthogonal_refresh_mode:")
    end = source.index("        handoff = build_real_same_run_handoff", full + 20)
    block = source[full:end]
    assert "run_o4_prospective_shadow_nonblocking" in block
    # A successful full capture must reach the shared same-run handoff.  An
    # incomplete orthogonal capture remains fail-closed, but must not make
    # the healthy path terminate before downstream stages are wired.
    assert 'job["full_orthogonal_refresh_downstream_continued"] = True' in block
    # An incomplete capture is retryable; pending_asof must survive the
    # terminal failure so the next scheduled run retries the same target.
    assert 'set_pending_asof(asof, reason="full_orthogonal_refresh_incomplete", job_id=job_id)' in block
    assert '"pending_asof_set": asof' in block


def test_o4_adapter_has_independent_validator_gate() -> None:
    source = (ROOT / "scripts/run_modelb_o4_prospective_shadow_nonblocking.py").read_text(encoding="utf-8")
    assert "validate_modelb_o4_prospective_shadow.py" in source
    assert "STOP_VALIDATOR_FAILED_NONBLOCKING" in source
    assert "O4_VALIDATED_OBSERVATION_NONBLOCKING" in source


def _complete_adapter_args(adapter, tmp_path: Path):
    paths = {}
    for name in ("daily_price_adapter", "institutional_adapter", "margin_adapter", "twii_raw", "twii_capture", "calendar"):
        path = tmp_path / f"{name}.json"
        path.write_text("{}\n", encoding="utf-8")
        paths[name] = str(path)
    signals = []
    for index in range(6):
        path = tmp_path / f"model_a_{index}.csv"
        path.write_text("date,instrument\n2026-09-09,TW2330\n", encoding="utf-8")
        signals.append(str(path))
    return SimpleNamespace(
        asof="2026-09-09", source_run_id="run", decision_cutoff="2026-09-09T10:00:00+00:00",
        job_dir=tmp_path, model_a_signals=signals, output_dir="",
        ledger="", **paths,
    )


def test_o4_adapter_scorer_failure_is_nonblocking(tmp_path: Path, monkeypatch) -> None:
    adapter = load("o4_nonblocking_scorer_failure", ROOT / "scripts/run_modelb_o4_prospective_shadow_nonblocking.py")
    args = _complete_adapter_args(adapter, tmp_path)
    monkeypatch.setattr(adapter.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=9, stdout="", stderr="injected scorer failure"))
    result = adapter.run(args)
    assert result["status"] == "STOP_SCORER_FAILED_NONBLOCKING"
    assert json.loads((tmp_path / "o4_prospective_shadow_status.json").read_text(encoding="utf-8"))["model_a_nonblocking"] is True


def test_o4_adapter_validator_failure_is_nonblocking(tmp_path: Path, monkeypatch) -> None:
    adapter = load("o4_nonblocking_validator_failure", ROOT / "scripts/run_modelb_o4_prospective_shadow_nonblocking.py")
    args = _complete_adapter_args(adapter, tmp_path)
    calls = []

    def fake_run(*a, **k):
        calls.append(a[0])
        code = 0 if len(calls) == 1 else 7
        return SimpleNamespace(returncode=code, stdout="builder ok", stderr="validator injected failure")

    monkeypatch.setattr(adapter.subprocess, "run", fake_run)
    result = adapter.run(args)
    assert result["status"] == "STOP_VALIDATOR_FAILED_NONBLOCKING"
    assert len(calls) == 2


def test_daily_o4_hook_is_nonblocking_and_passes_explicit_ledger(tmp_path: Path) -> None:
    daily = load("daily_o4_hook", ROOT / "scripts/run_daily_tw_stock_auto_update.py")
    calls = []

    def fake_runner(argv, **kwargs):
        calls.append((argv, kwargs))
        kwargs["stdout_path"].write_text("{}\n", encoding="utf-8")
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {"ok": True, "returncode": 0, "argv": argv}

    result = daily.run_o4_prospective_shadow_nonblocking(
        asof="2026-09-09", job_id="job", job_dir=tmp_path, source_run_id="run",
        decision_cutoff="2026-09-09T10:00:00+00:00", enabled=True, command_runner=fake_runner,
    )
    assert result["ok"] is True
    assert result["status"] == "NONBLOCKING_ADAPTER_COMPLETED"
    assert "--ledger" in calls[0][0]
    assert "--output-dir" not in calls[0][0]  # default isolated output is adapter-owned
