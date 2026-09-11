from __future__ import annotations

from pathlib import Path

from scripts.tw_daily_runtime_stages import (
    RuntimeDescriptorError,
    build_stage_facade,
    descriptor_summary,
    load_runtime_descriptor,
    no_publish_fingerprint_audit,
)


def test_descriptor_summary_matches_frozen_runtime_truth() -> None:
    summary = descriptor_summary()
    assert summary["active_model_id"] == "e4_frozen_qlib_2018_2022"
    assert summary["active_status"] == "MODEL_A_ONLY"
    assert summary["strategy_rule"] == "top50_exit_one_worst_sell"
    assert summary["execution_price_mode"] == "next_open"
    assert summary["shadow_model_id"] == "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
    assert summary["shadow_production_default"] is False


def test_schema_is_enforced_for_runtime_loader(tmp_path: Path) -> None:
    descriptor = tmp_path / "descriptor.yaml"
    descriptor.write_text("{}\n", encoding="utf-8")
    try:
        load_runtime_descriptor(descriptor_path=descriptor)
    except RuntimeDescriptorError as exc:
        assert "invalid active baseline descriptor" in str(exc)
    else:
        raise AssertionError("invalid descriptor unexpectedly loaded")


def test_stage_facade_is_injectable_and_preserves_callback_result() -> None:
    stages = build_stage_facade(signal=lambda asof: {"asof": asof, "ok": True})
    assert stages["signal"].run("2026-09-04")["ok"] is True
    assert stages["acquisition"].run()["status"] == "NOT_IMPLEMENTED_LEGACY_PATH"


def test_no_publish_audit_compares_actual_before_after() -> None:
    before = {"latest": {"exists": True, "size": 1, "sha256": "a"}}
    after = {"latest": {"exists": True, "size": 2, "sha256": "b"}}
    audit = no_publish_fingerprint_audit(before, after)
    assert audit["ok"] is False
    assert audit["comparison"]["latest"] is False
    assert audit["publish_allowed"] is False
