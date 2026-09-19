from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import tw_mbcds35_signal_time_regime as regime  # noqa: E402


@pytest.mark.parametrize(
    "close_vs_ma60,ret20,drawdown,expected",
    [
        (0.10, 0.10, -0.15, "crash"),
        (0.10, 0.10, -0.149999, "risk_off"),
        (0.10, 0.10, -0.08, "risk_off"),
        (0.0, 0.0, -0.079999, "risk_on"),
        (0.0, -0.000001, -0.01, "neutral"),
        (-0.000001, 0.10, -0.01, "risk_off"),
    ],
)
def test_predeclared_threshold_boundaries(close_vs_ma60, ret20, drawdown, expected):
    actual, _ = regime.classify({
        "TWII_close_vs_MA60": close_vs_ma60,
        "TWII_ret20": ret20,
        "market_drawdown60": drawdown,
    })
    assert actual == expected
    assert actual != "UNCLASSIFIED"


@pytest.mark.parametrize("value", [None, float("nan"), float("inf")])
def test_missing_or_non_finite_is_fail_closed(value):
    with pytest.raises(regime.RegimeContractError):
        regime.classify({
            "TWII_close_vs_MA60": value,
            "TWII_ret20": 0.01,
            "market_drawdown60": -0.01,
        })


def test_frozen_contract_checksum_drift_is_rejected(tmp_path):
    payload = json.loads(regime.DEFAULT_CONTRACT.read_text())
    payload["classification_priority"][0]["predicate"] = "market_drawdown60 < -0.15"
    changed = tmp_path / "regime.json"
    changed.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(regime.RegimeContractError, match="checksum_mismatch"):
        regime.load_contract(changed)
