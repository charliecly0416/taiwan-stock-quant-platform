#!/usr/bin/env python3
"""Feature-only frozen Model A inference for B19R2R.

This module intentionally constructs DataHandlerLP directly. It does not create
the Alpha158 label group and does not configure learn processors.
"""
from __future__ import annotations

import pickle
import hashlib
import json
from pathlib import Path

import pandas as pd


def predict_feature_only(
    *,
    provider_root: Path,
    model_path: Path,
    symbols: list[str],
    start: str,
    end: str,
) -> pd.DataFrame:
    import qlib
    from qlib.contrib.data.loader import Alpha158DL
    from qlib.contrib.model.gbdt import LGBModel
    from qlib.data.dataset import DatasetH
    from qlib.data.dataset.handler import DataHandlerLP

    qlib.init(provider_uri=str(provider_root), region="tw", expression_cache=None, dataset_cache=None)
    feature_fields, feature_names = Alpha158DL.get_feature_config()
    canonical = lambda values: json.dumps(list(values), separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    if len(feature_fields) != 158 or len(feature_names) != 158:
        raise RuntimeError("unexpected Alpha158 feature count")
    if hashlib.sha256(canonical(feature_fields)).hexdigest() != "05943b7d14e82ab604fe76938465589014c6e89b51f09116a2805c59080678a3":
        raise RuntimeError("Alpha158 feature expression order changed")
    if hashlib.sha256(canonical(feature_names)).hexdigest() != "d5f52c2d75ea900ab29f4742eeb59d9692254ba7307ad36a807012db7d680e13":
        raise RuntimeError("Alpha158 feature name order changed")
    handler = DataHandlerLP(
        instruments=sorted(symbols),
        start_time="2015-05-04",
        end_time=end,
        data_loader={
            "class": "QlibDataLoader",
            "kwargs": {
                "config": {"feature": (feature_fields, feature_names)},
                "freq": "day",
            },
        },
        infer_processors=[],
        learn_processors=[],
    )
    dataset = DatasetH(handler=handler, segments={"snapshot": (start, end)})
    with model_path.open("rb") as handle:
        model = pickle.load(handle)
    if not isinstance(model, LGBModel):
        raise TypeError(f"unexpected frozen Model A type: {type(model)}")
    prediction = model.predict(dataset, segment="snapshot").rename("model_a_raw_score").reset_index()
    prediction = prediction.rename(columns={"datetime": "date"})
    prediction["date"] = pd.to_datetime(prediction.date).dt.strftime("%Y-%m-%d")
    prediction["instrument"] = prediction.instrument.astype(str).str.upper()
    return prediction
