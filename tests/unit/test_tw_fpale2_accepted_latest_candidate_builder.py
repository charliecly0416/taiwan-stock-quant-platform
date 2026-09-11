from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts/build_tw_fpale2_accepted_latest_candidate.py"


def load_builder_module():
    spec = importlib.util.spec_from_file_location("build_tw_fpale2_accepted_latest_candidate", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_staged_candidate(root: Path, target_asof: str = "2026-08-11", symbols: int = 150) -> None:
    staged = root / "staged_qlib_bin"
    reports = root / "reports"
    (staged / "calendars").mkdir(parents=True)
    (staged / "instruments").mkdir(parents=True)
    reports.mkdir(parents=True)
    (staged / "calendars/day.txt").write_text("2026-08-07\n2026-08-10\n2026-08-11\n", encoding="utf-8")
    instrument_rows = [
        f"TW{i:04d}\t2015-01-05\t{target_asof}"
        for i in range(1, symbols + 1)
    ]
    (staged / "instruments/all.txt").write_text("\n".join(instrument_rows) + "\n", encoding="utf-8")
    prediction_rows = ["datetime,instrument,score"]
    prediction_rows.extend(
        f"{target_asof},TW{i:04d},{1.0 / i:.8f}"
        for i in range(1, symbols + 1)
    )
    (reports / "staged_prediction.csv").write_text("\n".join(prediction_rows) + "\n", encoding="utf-8")


def write_formal_calendar(root: Path, *dates: str) -> None:
    calendar = root / "calendars/day.txt"
    calendar.parent.mkdir(parents=True)
    calendar.write_text("\n".join(dates) + "\n", encoding="utf-8")


def test_explicit_staged_provider_root_uses_staged_calendar_when_formal_provider_is_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_builder_module()
    formal_root = tmp_path / "formal_provider"
    staged_root = tmp_path / "staged_candidate"
    write_formal_calendar(formal_root, "2026-08-07")
    write_staged_candidate(staged_root)
    monkeypatch.setattr(module, "FORMAL_PROVIDER_ROOT", formal_root)

    contract = module.validate_source_contract(
        staged_root,
        "2026-08-11",
        explicit_source_candidate_root=True,
    )
    ranked, profile = module.load_source(
        staged_root / "reports/staged_prediction.csv",
        staged_root,
        "2026-08-11",
        expected_instruments=contract["staged_universe_symbols"],
    )

    assert contract["source_mode"] == "explicit_staged_provider_root"
    assert contract["formal_provider_status"]["target_asof_present"] is False
    assert contract["staged_provider_calendar_status"]["target_asof_present"] is True
    assert contract["staged_universe_status"]["unique_symbols"] == 150
    assert len(ranked) == 150
    assert profile["matches_staged_universe"] is True


def test_missing_explicit_staged_root_preserves_formal_provider_coverage_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_builder_module()
    formal_root = tmp_path / "formal_provider"
    source_root = tmp_path / "source_candidate"
    write_formal_calendar(formal_root, "2026-08-07")
    monkeypatch.setattr(module, "FORMAL_PROVIDER_ROOT", formal_root)

    with pytest.raises(RuntimeError, match="formal provider does not cover target asof"):
        module.validate_source_contract(
            source_root,
            "2026-08-11",
            explicit_source_candidate_root=False,
        )


def test_explicit_staged_provider_root_fails_closed_on_missing_staged_calendar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_builder_module()
    formal_root = tmp_path / "formal_provider"
    source_root = tmp_path / "source_candidate"
    write_formal_calendar(formal_root, "2026-08-07")
    monkeypatch.setattr(module, "FORMAL_PROVIDER_ROOT", formal_root)

    with pytest.raises(RuntimeError, match="staged provider calendar does not cover target asof"):
        module.validate_source_contract(
            source_root,
            "2026-08-11",
            explicit_source_candidate_root=True,
        )
