import json
from pathlib import Path

import pandas as pd
import pytest

from clean_product.features import validate_b19_inputs, write_b19_feature_artifact
from clean_product.models import ModelBlocked


def feature_order():
    # Keep the unit test independent of ignored production model assets.  The
    # runtime path validates the real frozen schema before building a delta;
    # this test only exercises the artifact writer's 78-column contract.
    return [f"feature_{index}" for index in range(78)]


def test_shadow_input_validation_uses_lagged_session(tmp_path):
    data = {
        "prices": pd.DataFrame({"date": ["2026-09-28", "2026-09-29"]}),
        "institutional": pd.DataFrame({"date": ["2026-09-28", "2026-09-29"]}),
        "margin": pd.DataFrame({"date": ["2026-09-28", "2026-09-29"]}),
        "twii": pd.DataFrame({"date": ["2026-09-28", "2026-09-29"]}),
    }
    cfg = {"datasets": {"institutional": {"lag_days": 1}, "margin": {"lag_days": 1}, "twii": {"lag_days": 0}}}
    assert validate_b19_inputs(asof="2026-09-29", data=data, config=cfg) == "2026-09-28"

    data["margin"] = pd.DataFrame({"date": ["2026-09-26"]})
    with pytest.raises(ModelBlocked, match="B19R2R_MARGIN_STALE"):
        validate_b19_inputs(asof="2026-09-29", data=data, config=cfg)


def test_shadow_feature_artifact_is_complete_and_hashed(tmp_path):
    order = feature_order()
    frame = pd.DataFrame([{**{"date": "2026-09-29", "instrument": "TW2330"}, **{name: 0.0 for name in order}}])
    result = write_b19_feature_artifact(frame=frame, asof="2026-09-29",
                                        config={"artifact_root": tmp_path},
                                        feature_order=order, run_id="test-run")
    target = Path(result["path"])
    assert result["status"] == "READY" and target.is_file()
    assert len(pd.read_parquet(target)) == 1
    assert result["sha256"] and json.loads((target.parent / "manifest.json").read_text())["feature_count"] == 78
