#!/usr/bin/env python3
"""Frozen signal-time regime classification shared by MBCDS3-5 artifacts."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "docs/tw_model_b_compatibility/MBCDS3_5_SIGNAL_TIME_PIT_SAFE_REGIME_CONTRACT_V1.json"
EXPECTED_CONTRACT_SHA256 = "74e50aecda4353e74e9f34e8bbcd934a356738e1e8d8ced2c74751ef905d3ffe"
REQUIRED_FIELDS = ("TWII_close_vs_MA60", "TWII_ret20", "market_drawdown60")
ALLOWED_REGIMES = ("crash", "risk_off", "risk_on", "neutral")


class RegimeContractError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract(path: Path = DEFAULT_CONTRACT) -> tuple[dict[str, Any], str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegimeContractError(f"regime_contract_unreadable:{path}") from exc
    digest = sha256(path)
    if digest != EXPECTED_CONTRACT_SHA256:
        raise RegimeContractError("regime_contract_checksum_mismatch")
    if (
        payload.get("schema_version") != "mbcds35.signal_time_regime_contract.v1"
        or payload.get("contract_id") != "mbcds35_rsr2_twii_signal_time_regime_v1"
        or payload.get("status") != "FROZEN"
        or payload.get("required_feature_fields") != list(REQUIRED_FIELDS)
        or payload.get("allowed_regimes") != list(ALLOWED_REGIMES)
        or payload.get("missing_policy") != "FAIL_CLOSED_NO_CLASSIFICATION_NO_FILL"
    ):
        raise RegimeContractError("regime_contract_identity_or_schema_mismatch")
    return payload, digest


def classify(values: Mapping[str, Any]) -> tuple[str, dict[str, float]]:
    normalized: dict[str, float] = {}
    for field in REQUIRED_FIELDS:
        try:
            value = float(values[field])
        except (KeyError, TypeError, ValueError) as exc:
            raise RegimeContractError(f"regime_required_feature_missing:{field}") from exc
        if not math.isfinite(value):
            raise RegimeContractError(f"regime_required_feature_non_finite:{field}")
        normalized[field] = value

    drawdown = normalized["market_drawdown60"]
    close_vs_ma60 = normalized["TWII_close_vs_MA60"]
    ret20 = normalized["TWII_ret20"]
    if drawdown <= -0.15:
        regime = "crash"
    elif close_vs_ma60 < 0 or drawdown <= -0.08:
        regime = "risk_off"
    elif close_vs_ma60 >= 0 and ret20 >= 0:
        regime = "risk_on"
    else:
        regime = "neutral"
    return regime, normalized
