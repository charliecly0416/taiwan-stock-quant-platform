from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/capture_modelb_b19r2r_twii_yahoo_v2.py"


def load_capture():
    name = "capture_modelb_b19r2r_twii_yahoo_v2_for_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


capture = load_capture()


def daily_payload(*, close: float | None = 230.0, adjclose: float | None = 230.0) -> dict:
    return {
        "chart": {
            "result": [{
                "timestamp": [1789430400, 1789516800],
                "indicators": {
                    "quote": [{
                        "open": [210.0, 220.0], "high": [225.0, 235.0],
                        "low": [205.0, 215.0], "close": [220.0, close],
                        "volume": [900, 1000],
                    }],
                    "adjclose": [{"adjclose": [220.0, adjclose]}],
                },
            }],
        },
    }


def target_row() -> dict:
    return {"open": 220.0, "high": 235.0, "low": 215.0, "close": 230.0}


def test_complete_daily_target_matches_intraday_and_proves_factor_one() -> None:
    evidence = capture.validate_daily_target_stub(daily_payload(), target_row())
    assert evidence["daily_target_mode"] == "complete_daily_row"
    assert evidence["daily_stub_is_explicitly_incomplete"] is False
    assert evidence["daily_stub_close"] == 230.0
    assert evidence["daily_stub_adjclose"] == 230.0
    assert evidence["daily_vs_intraday_ohl_absolute_differences"]["close"] == 0.0
    assert evidence["target_factor_semantics_consistent"] is True


def test_incomplete_daily_stub_remains_supported() -> None:
    evidence = capture.validate_daily_target_stub(
        daily_payload(close=None, adjclose=None), target_row()
    )
    assert evidence["daily_target_mode"] == "incomplete_daily_stub"
    assert evidence["daily_stub_is_explicitly_incomplete"] is True
    assert evidence["daily_stub_close"] is None


def test_complete_daily_target_close_mismatch_is_rejected() -> None:
    mismatched = target_row()
    mismatched["close"] = 231.0
    with pytest.raises(capture.CaptureError) as caught:
        capture.validate_daily_target_stub(daily_payload(), mismatched)
    assert caught.value.code == "B19YTWII_E_DAILY_INTRADAY_MISMATCH"


def test_mixed_complete_and_incomplete_close_pair_is_rejected() -> None:
    with pytest.raises(capture.CaptureError) as caught:
        capture.validate_daily_target_stub(
            daily_payload(close=230.0, adjclose=None), target_row()
        )
    assert caught.value.code == "B19YTWII_E_DAILY_STUB_NOT_INCOMPLETE"


def test_daily_shadow_is_bound_to_versioned_capture_implementation() -> None:
    shadow_path = ROOT / "scripts/run_modelb_b19r2r_daily_shadow.py"
    spec = importlib.util.spec_from_file_location("b19r2r_daily_shadow_for_version_test", shadow_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert module.TWII_CAPTURE_SCRIPT == SCRIPT
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"schema_version": "modelb_b19r2r.yahoo_twii_dual_interval_capture.v2"' in source
    assert '"source_id": "yahoo.finance.chart.^TWII.dual_interval.v2"' in source
    assert '"sha256": sha256(Path(__file__))' in source
