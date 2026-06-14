#!/usr/bin/env python3
from __future__ import annotations

import json
import pickle
import sys
import gc
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import qlib
import yaml
from qlib.contrib.model.gbdt import LGBModel
from qlib.data.dataset import DatasetH


ROOT = Path(__file__).resolve().parents[1]
QLIB_ROOT = ROOT / "qlib_pipeline"
PROVIDER = Path(os.environ.get("S1B1_PROVIDER_URI", "/home/chuliyang/qlib/data_tw/experiments/yahoo_adjusted_primary/qlib_bin"))
NORMALIZED = Path(
    os.environ.get(
        "S1B1_NORMALIZED_DIR",
        str(QLIB_ROOT / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"),
    )
)
CONFIG_PATH = QLIB_ROOT / "configs/tw_yahoo_primary_alpha158.yaml"
FROZEN_RECORDER = Path(
    os.environ.get(
        "S1B1_FROZEN_RECORDER_DIR",
        str(QLIB_ROOT / "mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a"),
    )
)
FROZEN_PRED = FROZEN_RECORDER / "artifacts/pred.pkl"
REPAIRED_DAILY = Path(
    os.environ.get(
        "S1B1_REPAIRED_DAILY",
        str(
            ROOT
            / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0r_calendar_price_repair/phase_s1b0r_dynamic_universe_feasibility_repaired_daily.csv"
        ),
    )
)
OUT = Path(
    os.environ.get(
        "S1B1_OUTPUT_DIR",
        str(ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores"),
    )
)
FOLD_OUT = OUT / "folds"

CALENDAR_POLICY = "qlib day.txt ∩ TWII normalized price calendar"
UNIVERSE_POLICY = "asof active instrument range + same-day price + >=60 history + trailing 60-day value top up to 150; selected_count >= 145"
RECORDER_ID = "950741cfd5f14ee5a05464fec3e12e0a"
RESOURCE_CONTROL_ATTEMPT_ORDER = [4, 2, 1]
ORIGINAL_NUM_THREADS = 8


@dataclass(frozen=True)
class Fold:
    fold_id: str
    train_start: str
    train_end: str
    valid_start: str
    valid_end: str
    score_start: str
    score_end: str
    ltr_usage: str
    use_frozen_pred: bool = False


FOLDS = [
    Fold("WF-2017", "2015-05-04", "2016-12-31", "2015-05-04", "2016-12-31", "2017-01-01", "2017-12-31", "train_score"),
    Fold("WF-2018", "2015-05-04", "2017-12-31", "2015-05-04", "2017-12-31", "2018-01-01", "2018-12-31", "train_score"),
    Fold("WF-2019", "2015-05-04", "2018-12-31", "2015-05-04", "2018-12-31", "2019-01-01", "2019-12-31", "train_score"),
    Fold("WF-2020", "2015-05-04", "2019-12-31", "2015-05-04", "2019-12-31", "2020-01-01", "2020-12-31", "train_score"),
    Fold("WF-VAL", "2015-05-04", "2020-12-31", "2015-05-04", "2020-12-31", "2021-01-01", "2022-12-31", "validation_score"),
    Fold("TEST", "2015-05-04", "2020-12-31", "2021-01-01", "2022-12-31", "2023-01-01", "2025-06-30", "test_score_baseline", True),
]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_repaired_universe() -> tuple[pd.DataFrame, dict[tuple[str, str], int]]:
    daily = pd.read_csv(REPAIRED_DAILY)
    daily["date"] = daily["date"].astype(str)
    if bool((daily["top150_selected_count"] < 145).any()):
        bad = daily[daily["top150_selected_count"] < 145][["date", "top150_selected_count"]].head(20)
        raise RuntimeError(f"selected_count below 145 after calendar repair:\n{bad.to_string(index=False)}")

    # Reconstruct the selected symbols using the same frozen policy:
    # same-day price, at least 60 historical rows, trailing 60-day value top up to 150.
    need_dates = set(daily["date"])
    frames = []
    for path in sorted(NORMALIZED.glob("TW*.csv")):
        symbol = path.stem.upper()
        if symbol == "TWII":
            continue
        df = pd.read_csv(path, usecols=["date", "close", "vwap", "volume"])
        if df.empty:
            continue
        df["instrument"] = symbol
        df["date"] = pd.to_datetime(df["date"])
        df = df[(df["date"] >= pd.Timestamp("2015-01-01")) & (df["date"] <= pd.Timestamp("2025-06-30"))].copy()
        if df.empty:
            continue
        df["date_str"] = df["date"].dt.date.astype(str)
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["vwap"] = pd.to_numeric(df["vwap"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        price = df["vwap"].where(df["vwap"].notna() & (df["vwap"] > 0), df["close"])
        df["value"] = price * df["volume"]
        frames.append(df[["date", "date_str", "instrument", "close", "volume", "value"]])
    prices = pd.concat(frames, ignore_index=True).sort_values(["instrument", "date"])
    prices["history_count_60"] = prices.groupby("instrument")["date"].cumcount() + 1
    prices["trailing_value_60"] = prices.groupby("instrument")["value"].transform(lambda s: s.rolling(60, min_periods=20).mean())
    valid = prices[
        prices["date_str"].isin(need_dates)
        & prices["close"].notna()
        & (prices["close"] > 0)
        & prices["volume"].notna()
        & (prices["volume"] >= 0)
        & (prices["history_count_60"] >= 60)
        & prices["trailing_value_60"].notna()
    ].copy()
    universe = pd.read_csv(
        QLIB_ROOT / "data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt",
        sep="\t",
        names=["instrument", "start_datetime", "end_datetime"],
    )
    universe["instrument"] = universe["instrument"].astype(str).str.upper()
    universe["start_datetime"] = pd.to_datetime(universe["start_datetime"])
    universe["end_datetime"] = pd.to_datetime(universe["end_datetime"])
    valid = valid.merge(universe, on="instrument", how="inner")
    valid = valid[(valid["date"] >= valid["start_datetime"]) & (valid["date"] <= valid["end_datetime"])]
    valid = valid.sort_values(["date_str", "trailing_value_60"], ascending=[True, False])
    selected = valid.groupby("date_str", group_keys=False).head(150).copy()
    selected = selected[["date_str", "instrument"]].rename(columns={"date_str": "date"})
    selected_count = selected.groupby("date")["instrument"].nunique().to_dict()
    expected_count = daily.set_index("date")["top150_selected_count"].to_dict()
    mismatches = [
        {"date": d, "expected": int(expected_count[d]), "actual": int(selected_count.get(d, 0))}
        for d in sorted(expected_count)
        if int(expected_count[d]) != int(selected_count.get(d, 0))
    ]
    if mismatches:
        raise RuntimeError(f"selected universe reconstruction mismatch: {mismatches[:10]}")
    return selected, {(row.date, row.instrument): 1 for row in selected.itertuples(index=False)}


def rank_scores(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["qlib_rank"] = out.groupby("date")["qlib_score_raw"].rank(method="first", ascending=False).astype(int)
    return out


def model_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    return dict(config["task"]["model"]["kwargs"])


def wf_val_resource_num_threads() -> int | None:
    value = os.environ.get("S1B1_WF_VAL_NUM_THREADS")
    if value is None or value == "":
        return None
    threads = int(value)
    if threads not in RESOURCE_CONTROL_ATTEMPT_ORDER:
        raise RuntimeError(f"unauthorized WF-VAL num_threads override: {threads}")
    return threads


def model_kwargs_for_fold(config: dict[str, Any], fold: Fold) -> dict[str, Any]:
    kwargs = model_kwargs(config)
    if fold.fold_id == "WF-VAL":
        threads = wf_val_resource_num_threads()
        if threads is not None:
            kwargs["num_threads"] = threads
    return kwargs


def train_predict_fold(fold: Fold, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    handler_conf = {
        "class": "Alpha158",
        "module_path": "qlib.contrib.data.handler",
        "kwargs": {
            "start_time": fold.train_start,
            "end_time": fold.score_end,
            "fit_start_time": fold.train_start,
            "fit_end_time": fold.train_end,
            "instruments": "all",
        },
    }
    dataset = DatasetH(
        handler=handler_conf,
        segments={
            "train": (fold.train_start, fold.train_end),
            "valid": (fold.valid_start, fold.valid_end),
            "score": (fold.score_start, fold.score_end),
        },
    )
    model = LGBModel(**model_kwargs_for_fold(config, fold))
    model.fit(dataset)
    pred = model.predict(dataset, segment="score").rename("qlib_score_raw").to_frame()
    pred = pred.reset_index()
    pred["date"] = pd.to_datetime(pred["datetime"]).dt.date.astype(str)
    pred["instrument"] = pred["instrument"].astype(str).str.upper()
    out = pred[["date", "instrument", "qlib_score_raw"]].dropna(subset=["qlib_score_raw"])
    return out, {
        "fold_id": fold.fold_id,
        "qlib_train_start": fold.train_start,
        "qlib_train_end": fold.train_end,
        "qlib_valid_start": fold.valid_start,
        "qlib_valid_end": fold.valid_end,
        "score_window_start": fold.score_start,
        "score_window_end": fold.score_end,
        "use_frozen_pred": False,
        "training_performed": True,
        "parameter_search_performed": False,
    }



def month_chunks(start: str, end: str) -> list[tuple[str, str]]:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    chunks: list[tuple[str, str]] = []
    cur = start_ts
    while cur <= end_ts:
        chunk_end = min(cur + pd.offsets.MonthEnd(0), end_ts)
        chunks.append((cur.date().isoformat(), chunk_end.date().isoformat()))
        cur = chunk_end + pd.Timedelta(days=1)
    return chunks


def build_dataset(fold: Fold, end_time: str, segments: dict[str, tuple[str, str]]) -> DatasetH:
    handler_conf = {
        "class": "Alpha158",
        "module_path": "qlib.contrib.data.handler",
        "kwargs": {
            "start_time": fold.train_start,
            "end_time": end_time,
            "fit_start_time": fold.train_start,
            "fit_end_time": fold.train_end,
            "instruments": "all",
        },
    }
    return DatasetH(handler=handler_conf, segments=segments)


def train_wf_val_model(fold: Fold, config: dict[str, Any]) -> LGBModel:
    dataset = build_dataset(
        fold,
        end_time=fold.train_end,
        segments={
            "train": (fold.train_start, fold.train_end),
            "valid": (fold.valid_start, fold.valid_end),
        },
    )
    model = LGBModel(**model_kwargs_for_fold(config, fold))
    model.fit(dataset)
    del dataset
    gc.collect()
    return model


def predict_wf_val_chunks(fold: Fold, model: LGBModel) -> pd.DataFrame:
    chunk_dir = FOLD_OUT / "WF-VAL_chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for chunk_start, chunk_end in month_chunks(fold.score_start, fold.score_end):
        chunk_path = chunk_dir / f"{chunk_start}_{chunk_end}.csv"
        if chunk_path.exists():
            frames.append(pd.read_csv(chunk_path))
            continue
        print(f"[S1B1R] predicting WF-VAL chunk: {chunk_start}..{chunk_end}")
        dataset = build_dataset(
            fold,
            end_time=chunk_end,
            segments={"score": (chunk_start, chunk_end)},
        )
        pred = model.predict(dataset, segment="score").rename("qlib_score_raw").to_frame()
        pred = pred.reset_index()
        pred["date"] = pd.to_datetime(pred["datetime"]).dt.date.astype(str)
        pred["instrument"] = pred["instrument"].astype(str).str.upper()
        out = pred[["date", "instrument", "qlib_score_raw"]].dropna(subset=["qlib_score_raw"])
        out.to_csv(chunk_path, index=False)
        frames.append(out)
        del dataset, pred, out
        gc.collect()
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "instrument", "qlib_score_raw"])


def train_predict_wf_val_resource_repair(fold: Fold, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    model = train_wf_val_model(fold, config)
    raw = predict_wf_val_chunks(fold, model)
    del model
    gc.collect()
    return raw, {
        "fold_id": fold.fold_id,
        "qlib_train_start": fold.train_start,
        "qlib_train_end": fold.train_end,
        "qlib_valid_start": fold.valid_start,
        "qlib_valid_end": fold.valid_end,
        "score_window_start": fold.score_start,
        "score_window_end": fold.score_end,
        "use_frozen_pred": False,
        "training_performed": True,
        "parameter_search_performed": False,
        "resource_repair": "train_once_predict_monthly_chunks",
        "predict_chunk_frequency": "monthly",
        "original_num_threads": ORIGINAL_NUM_THREADS,
        "resource_control_attempt_order": RESOURCE_CONTROL_ATTEMPT_ORDER,
        "resource_control_success_num_threads": wf_val_resource_num_threads(),
        "resource_control_failed_num_threads": [t for t in RESOURCE_CONTROL_ATTEMPT_ORDER if wf_val_resource_num_threads() is not None and t < wf_val_resource_num_threads()],
        "resource_control_reason": "reduce_parallel_memory_pressure",
    }

def frozen_test_scores() -> pd.DataFrame:
    pred = pickle.load(FROZEN_PRED.open("rb"))
    if isinstance(pred, pd.Series):
        frame = pred.rename("qlib_score_raw").to_frame()
    else:
        frame = pred.copy()
        if "score" in frame.columns:
            frame = frame.rename(columns={"score": "qlib_score_raw"})
        elif "qlib_score_raw" not in frame.columns:
            frame.columns = ["qlib_score_raw"]
    frame = frame.reset_index()
    frame["date"] = pd.to_datetime(frame["datetime"]).dt.date.astype(str)
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    return frame[["date", "instrument", "qlib_score_raw"]].dropna(subset=["qlib_score_raw"])


def fold_path(fold: Fold) -> Path:
    return FOLD_OUT / f"{fold.fold_id}.csv"


def manifest_path(fold: Fold) -> Path:
    return FOLD_OUT / f"{fold.fold_id}.manifest.json"


def filter_and_rank_fold(raw: pd.DataFrame, fold: Fold, selected_index: set[tuple[str, str]]) -> pd.DataFrame:
    keys = pd.MultiIndex.from_frame(raw[["date", "instrument"]].astype(str))
    selected_keys = pd.MultiIndex.from_tuples(sorted(selected_index), names=["date", "instrument"])
    filtered = raw[keys.isin(selected_keys)].copy()
    filtered = filtered[(filtered["date"] >= fold.score_start) & (filtered["date"] <= fold.score_end)]
    filtered = rank_scores(filtered)
    filtered["fold_id"] = fold.fold_id
    filtered["qlib_train_start"] = fold.train_start
    filtered["qlib_train_end"] = fold.train_end
    filtered["score_window_start"] = fold.score_start
    filtered["score_window_end"] = fold.score_end
    filtered["calendar_policy"] = CALENDAR_POLICY
    filtered["universe_policy"] = UNIVERSE_POLICY
    filtered["is_test_frozen_pred"] = bool(fold.use_frozen_pred)
    filtered["ltr_usage"] = fold.ltr_usage
    return filtered.sort_values(["date", "qlib_rank", "instrument"])


def base_manifest(fold: Fold, *, training_performed: bool) -> dict[str, Any]:
    return {
        "fold_id": fold.fold_id,
        "qlib_train_start": fold.train_start,
        "qlib_train_end": fold.train_end,
        "qlib_valid_start": fold.valid_start,
        "qlib_valid_end": fold.valid_end,
        "score_window_start": fold.score_start,
        "score_window_end": fold.score_end,
        "ltr_usage": fold.ltr_usage,
        "provider_uri": str(PROVIDER.resolve()),
        "config_path": str(CONFIG_PATH),
        "calendar_policy": CALENDAR_POLICY,
        "universe_policy": UNIVERSE_POLICY,
        "use_frozen_pred": bool(fold.use_frozen_pred),
        "training_performed": bool(training_performed),
        "parameter_search_performed": False,
    }


def enrich_manifest(manifest: dict[str, Any], filtered: pd.DataFrame) -> dict[str, Any]:
    counts = filtered.groupby("date")["instrument"].nunique() if not filtered.empty else pd.Series(dtype=int)
    manifest = dict(manifest)
    manifest["score_rows_after_universe_filter"] = int(filtered.shape[0])
    manifest["score_date_count"] = int(filtered["date"].nunique()) if not filtered.empty else 0
    manifest["selected_count_min"] = int(counts.min()) if not counts.empty else 0
    manifest["selected_count_median"] = float(counts.median()) if not counts.empty else 0.0
    manifest["selected_count_max"] = int(counts.max()) if not counts.empty else 0
    manifest["score_missing_count"] = int(filtered["qlib_score_raw"].isna().sum()) if not filtered.empty else 0
    manifest["rank_missing_count"] = int(filtered["qlib_rank"].isna().sum()) if not filtered.empty else 0
    manifest["duplicate_date_instrument_count"] = int(filtered.duplicated(subset=["date", "instrument"]).sum()) if not filtered.empty else 0
    return manifest


def materialize_fold(fold: Fold, config: dict[str, Any], selected_index: set[tuple[str, str]]) -> dict[str, Any]:
    out_path = fold_path(fold)
    man_path = manifest_path(fold)
    if out_path.exists() and man_path.exists():
        manifest = json.loads(man_path.read_text(encoding="utf-8"))
        if manifest.get("fold_id") == fold.fold_id and manifest.get("score_window_start") == fold.score_start:
            print(f"[S1B1] reuse existing fold artifact: {fold.fold_id}")
            return manifest

    print(f"[S1B1] generating fold: {fold.fold_id}")
    if fold.use_frozen_pred:
        raw = frozen_test_scores()
        manifest = base_manifest(fold, training_performed=False)
        manifest["source_recorder_id"] = RECORDER_ID
    elif fold.fold_id == "WF-VAL":
        raw, train_manifest = train_predict_wf_val_resource_repair(fold, config)
        manifest = base_manifest(fold, training_performed=True)
        manifest.update({k: v for k, v in train_manifest.items() if k not in manifest})
    else:
        raw, train_manifest = train_predict_fold(fold, config)
        manifest = base_manifest(fold, training_performed=True)
        manifest.update({k: v for k, v in train_manifest.items() if k not in manifest})

    filtered = filter_and_rank_fold(raw, fold, selected_index)
    manifest = enrich_manifest(manifest, filtered)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    filtered.to_csv(out_path, index=False)
    write_json(man_path, manifest)
    del raw, filtered
    gc.collect()
    return manifest


def finalize_outputs(selected: pd.DataFrame, manifest_rows: list[dict[str, Any]]) -> dict[str, Any]:
    frames = []
    for fold in FOLDS:
        path = fold_path(fold)
        if not path.exists():
            raise RuntimeError(f"missing fold artifact: {path}")
        frames.append(pd.read_csv(path))
    scores = pd.concat(frames, ignore_index=True).sort_values(["date", "qlib_rank", "instrument"])
    scores_path = OUT / "phase_s1b1_qlib_wf_scores.csv"
    scores.to_csv(scores_path, index=False)
    pd.DataFrame(manifest_rows).to_csv(OUT / "phase_s1b1_fold_training_manifest.csv", index=False)

    scores["split"] = np.select(
        [
            (scores["date"] >= "2017-01-01") & (scores["date"] <= "2020-12-31"),
            (scores["date"] >= "2021-01-01") & (scores["date"] <= "2022-12-31"),
            (scores["date"] >= "2023-01-01") & (scores["date"] <= "2025-06-30"),
        ],
        ["train_scored_2017_2020", "validation", "test"],
        default="out_of_scope",
    )
    score_window_mask = (
        ((selected["date"] >= "2017-01-01") & (selected["date"] <= "2020-12-31"))
        | ((selected["date"] >= "2021-01-01") & (selected["date"] <= "2022-12-31"))
        | ((selected["date"] >= "2023-01-01") & (selected["date"] <= "2025-06-30"))
    )
    selected_by_date = selected.loc[score_window_mask].groupby("date")["instrument"].nunique().rename("expected_selected_count")
    score_by_date = scores.groupby("date").agg(
        score_rows=("instrument", "count"),
        unique_instruments=("instrument", "nunique"),
        missing_score=("qlib_score_raw", lambda s: int(s.isna().sum())),
        missing_rank=("qlib_rank", lambda s: int(s.isna().sum())),
    ).join(selected_by_date, how="outer").fillna(0)
    score_by_date["score_missing_vs_selected"] = score_by_date["expected_selected_count"] - score_by_date["unique_instruments"]
    score_by_date.to_csv(OUT / "phase_s1b1_score_rank_coverage_by_date.csv")

    split_cov = scores.groupby("split").agg(
        start_date=("date", "min"),
        end_date=("date", "max"),
        date_count=("date", "nunique"),
        score_rows=("instrument", "count"),
        selected_count_min=("instrument", lambda s: int(scores.loc[s.index].groupby("date")["instrument"].nunique().min())),
        selected_count_median=("instrument", lambda s: float(scores.loc[s.index].groupby("date")["instrument"].nunique().median())),
        selected_count_max=("instrument", lambda s: int(scores.loc[s.index].groupby("date")["instrument"].nunique().max())),
        score_missing_count=("qlib_score_raw", lambda s: int(s.isna().sum())),
        rank_missing_count=("qlib_rank", lambda s: int(s.isna().sum())),
    ).reset_index()
    split_cov.to_csv(OUT / "phase_s1b1_score_rank_coverage_by_split.csv", index=False)

    fold_cov = scores.groupby("fold_id").agg(
        start_date=("date", "min"),
        end_date=("date", "max"),
        date_count=("date", "nunique"),
        score_rows=("instrument", "count"),
        selected_count_min=("instrument", lambda s: int(scores.loc[s.index].groupby("date")["instrument"].nunique().min())),
        selected_count_median=("instrument", lambda s: float(scores.loc[s.index].groupby("date")["instrument"].nunique().median())),
        selected_count_max=("instrument", lambda s: int(scores.loc[s.index].groupby("date")["instrument"].nunique().max())),
        is_test_frozen_pred=("is_test_frozen_pred", "max"),
    ).reset_index()
    fold_cov.to_csv(OUT / "phase_s1b1_score_rank_coverage_by_fold.csv", index=False)

    selected_counts = selected.groupby("date")["instrument"].nunique()
    universe_audit = selected_counts.reset_index(name="selected_count")
    universe_audit["selected_count_lt_145"] = universe_audit["selected_count"] < 145
    universe_audit["selected_count_lt_150"] = universe_audit["selected_count"] < 150
    universe_audit.to_csv(OUT / "phase_s1b1_universe_selected_count_audit.csv", index=False)

    duplicate_count = int(scores.duplicated(subset=["date", "instrument"]).sum())
    score_missing_count = int(scores["qlib_score_raw"].isna().sum())
    rank_missing_count = int(scores["qlib_rank"].isna().sum())
    leakage = {
        "phase": "phase_s1b1_qlib_wf_score_generation",
        "provider_uri": str(PROVIDER.resolve()),
        "calendar_policy": CALENDAR_POLICY,
        "universe_policy": UNIVERSE_POLICY,
        "s1_test_feedback_used_for_train_or_fold_design": False,
        "parameter_search_performed": False,
        "ltr_training_performed": False,
        "ltr_sample_build_performed": False,
        "portfolio_replay_performed": False,
        "provider_refresh_publish_performed": False,
        "accepted_latest_switching_performed": False,
        "monitor_or_trading_chain_touched": False,
        "early_train_2015_2016_scored": False,
        "train_scored_start": "2017-01-01",
        "duplicate_date_instrument_count": duplicate_count,
        "score_missing_count": score_missing_count,
        "rank_missing_count": rank_missing_count,
    }
    write_json(OUT / "phase_s1b1_leakage_boundary_audit.json", leakage)

    gate_ok = (
        duplicate_count == 0
        and score_missing_count == 0
        and rank_missing_count == 0
        and int(universe_audit["selected_count"].min()) >= 145
        and not bool((score_by_date["score_missing_vs_selected"] != 0).any())
    )
    gate = {
        "phase": "phase_s1b1_qlib_wf_score_generation",
        "recommended_gate": "s1b1s_low_thread_wf_val_pass_request_s1b2_ltr_sample_build" if gate_ok else "s1b1s_low_thread_resource_blocked",
        "provider_uri": str(PROVIDER.resolve()),
        "score_rows": int(scores.shape[0]),
        "date_count": int(scores["date"].nunique()),
        "instrument_count": int(scores["instrument"].nunique()),
        "selected_count_min": int(universe_audit["selected_count"].min()),
        "selected_count_median": float(universe_audit["selected_count"].median()),
        "selected_count_max": int(universe_audit["selected_count"].max()),
        "score_missing_count": score_missing_count,
        "rank_missing_count": rank_missing_count,
        "duplicate_date_instrument_count": duplicate_count,
        "folds": [row["fold_id"] for row in manifest_rows],
        "train_scored_coverage": "2017-01-01..2020-12-31",
        "validation_coverage": "2021-01-01..2022-12-31",
        "wf_val_resource_repair": "train_once_predict_monthly_chunks",
        "resource_control_attempt_order": RESOURCE_CONTROL_ATTEMPT_ORDER,
        "test_coverage": "2023-01-01..2025-06-30",
        "early_train_2015_2016_scored": False,
        "no_ltr_training": True,
        "no_ltr_sample_build": True,
        "no_replay": True,
        "no_parameter_tuning": True,
        "no_frontend_api": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_monitor_or_trading_chain": True,
        "artifacts": {
            "fold_training_manifest": str(OUT / "phase_s1b1_fold_training_manifest.csv"),
            "qlib_wf_scores": str(scores_path),
            "coverage_by_split": str(OUT / "phase_s1b1_score_rank_coverage_by_split.csv"),
            "coverage_by_fold": str(OUT / "phase_s1b1_score_rank_coverage_by_fold.csv"),
            "coverage_by_date": str(OUT / "phase_s1b1_score_rank_coverage_by_date.csv"),
            "universe_selected_count_audit": str(OUT / "phase_s1b1_universe_selected_count_audit.csv"),
            "leakage_boundary_audit": str(OUT / "phase_s1b1_leakage_boundary_audit.json"),
            "gate_summary": str(OUT / "phase_s1b1_gate_summary.json"),
            "report": "docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1S_LOW_THREAD_RESOURCE_EXECUTION_REPORT_CN.md",
        },
    }
    write_json(OUT / "phase_s1b1_gate_summary.json", gate)
    return gate


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    FOLD_OUT.mkdir(parents=True, exist_ok=True)
    qlib.init(provider_uri=str(PROVIDER.resolve()), region="tw", expression_cache=None, dataset_cache=None)
    config = load_config()
    selected, selected_index_dict = load_repaired_universe()
    selected_index = set(selected_index_dict.keys())
    selected_counts = selected.groupby("date")["instrument"].nunique()
    if int(selected_counts.min()) < 145:
        raise RuntimeError("selected_count < 145 after reconstruction")

    manifest_rows = []
    for fold in FOLDS:
        manifest_rows.append(materialize_fold(fold, config, selected_index))

    gate = finalize_outputs(selected, manifest_rows)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
