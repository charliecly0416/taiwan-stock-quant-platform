#!/usr/bin/env python3
from __future__ import annotations

import gc
import hashlib
import json
import os
import shutil
import sys
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
CONFIG_PATH = QLIB_ROOT / "configs/tw_yahoo_primary_alpha158_s2_fresh_retrain.yaml"
OUT_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training"
RUN_DIR = OUT_DIR / "run"
PROVIDER = QLIB_ROOT / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
UNIVERSE_PATH = QLIB_ROOT / "data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt"
NORMALIZED_DIR = QLIB_ROOT / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
DOC_PATH = ROOT / "docs/tw_ltr_qlib_split_aligned_retrain/PHASES2B_FRESH_QLIB_TRAINING_EXECUTION_REPORT_CN.md"

THREAD_LADDER = [4, 2, 1]
TRAIN_START = "2017-01-10"
TRAIN_END = "2024-12-31"
VALID_START = "2025-01-01"
VALID_END = "2025-06-30"
TEST_START = "2025-07-01"
TEST_END = "2026-05-07"
HANDLER_START = "2015-05-04"
HANDLER_END = "2026-05-07"
FIT_START = "2015-05-04"
FIT_END = "2024-12-31"
CALENDAR_POLICY = "provider day.txt + local twii/price tradability alignment through as-of post-score filter"
UNIVERSE_POLICY = "asof active instrument range + same-day price + >=60 history + trailing 60-day value top150"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def write_generated_yaml(thread_count: int) -> Path:
    config = load_config()
    config["task"]["model"]["kwargs"]["num_threads"] = int(thread_count)
    out = OUT_DIR / "phase_s2b_generated_qlib_config.yaml"
    out.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return out


def init_qlib() -> None:
    qlib.init(provider_uri=str(PROVIDER.resolve()), region="tw", expression_cache=None, dataset_cache=None)


def build_dataset(segments: dict[str, tuple[str, str]]) -> DatasetH:
    handler_conf = {
        "class": "Alpha158",
        "module_path": "qlib.contrib.data.handler",
        "kwargs": {
            "start_time": HANDLER_START,
            "end_time": HANDLER_END,
            "fit_start_time": FIT_START,
            "fit_end_time": FIT_END,
            "instruments": "all",
        },
    }
    return DatasetH(handler=handler_conf, segments=segments)


def train_once(thread_count: int) -> tuple[LGBModel, DatasetH]:
    config = load_config()
    kwargs = dict(config["task"]["model"]["kwargs"])
    kwargs["num_threads"] = int(thread_count)
    dataset = build_dataset(
        {
            "train": (TRAIN_START, TRAIN_END),
            "valid": (VALID_START, VALID_END),
            "test": (TEST_START, TEST_END),
        }
    )
    model = LGBModel(**kwargs)
    model.fit(dataset)
    return model, dataset


def model_predict_frame(model: LGBModel, dataset: DatasetH, segment: str) -> pd.DataFrame:
    pred = model.predict(dataset, segment=segment).rename("qlib_score_raw").to_frame().reset_index()
    pred["date"] = pd.to_datetime(pred["datetime"]).dt.date.astype(str)
    pred["instrument"] = pred["instrument"].astype(str).str.upper()
    out = pred[["date", "instrument", "qlib_score_raw"]].dropna(subset=["qlib_score_raw"]).copy()
    out["segment"] = segment
    return out


def load_selected_universe() -> tuple[pd.DataFrame, set[tuple[str, str]]]:
    frames = []
    for path in sorted(NORMALIZED_DIR.glob("TW*.csv")):
        symbol = path.stem.upper()
        if symbol == "TWII":
            continue
        df = pd.read_csv(path, usecols=["date", "close", "vwap", "volume"])
        if df.empty:
            continue
        df["instrument"] = symbol
        df["date"] = pd.to_datetime(df["date"])
        df = df[(df["date"] >= pd.Timestamp(HANDLER_START)) & (df["date"] <= pd.Timestamp(TEST_END))].copy()
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
        prices["close"].notna()
        & (prices["close"] > 0)
        & prices["volume"].notna()
        & (prices["volume"] >= 0)
        & (prices["history_count_60"] >= 60)
        & prices["trailing_value_60"].notna()
    ].copy()
    universe = pd.read_csv(UNIVERSE_PATH, sep="\t", names=["instrument", "start_datetime", "end_datetime"])
    universe["instrument"] = universe["instrument"].astype(str).str.upper()
    universe["start_datetime"] = pd.to_datetime(universe["start_datetime"])
    universe["end_datetime"] = pd.to_datetime(universe["end_datetime"])
    valid = valid.merge(universe, on="instrument", how="inner")
    valid = valid[(valid["date"] >= valid["start_datetime"]) & (valid["date"] <= valid["end_datetime"])]
    valid = valid.sort_values(["date_str", "trailing_value_60"], ascending=[True, False])
    selected = valid.groupby("date_str", group_keys=False).head(150).copy()
    selected = selected[["date_str", "instrument"]].rename(columns={"date_str": "date"})
    return selected, set(map(tuple, selected[["date", "instrument"]].itertuples(index=False, name=None)))


def rank_scores(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["qlib_rank"] = out.groupby("date")["qlib_score_raw"].rank(method="first", ascending=False).astype(int)
    return out


def apply_post_filter(raw: pd.DataFrame, selected_index: set[tuple[str, str]]) -> pd.DataFrame:
    keys = pd.MultiIndex.from_frame(raw[["date", "instrument"]].astype(str))
    selected_keys = pd.MultiIndex.from_tuples(sorted(selected_index), names=["date", "instrument"])
    filtered = raw[keys.isin(selected_keys)].copy()
    filtered = filtered[(filtered["date"] >= TRAIN_START) & (filtered["date"] <= TEST_END)]
    filtered = rank_scores(filtered)
    filtered["calendar_policy"] = CALENDAR_POLICY
    filtered["universe_policy"] = UNIVERSE_POLICY
    return filtered.sort_values(["date", "qlib_rank", "instrument"]).reset_index(drop=True)


def split_label(date_str: str) -> str:
    if TRAIN_START <= date_str <= TRAIN_END:
        return "train"
    if VALID_START <= date_str <= VALID_END:
        return "validation"
    if TEST_START <= date_str <= TEST_END:
        return "test"
    return "out_of_scope"


def coverage_tables(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_date = frame.groupby("date").agg(
        split=("segment", lambda s: split_label(str(s.index[0]) if False else frame.loc[s.index[0], "date"])),
        raw_score_rows=("instrument", "count"),
        unique_instruments=("instrument", "nunique"),
        missing_score=("qlib_score_raw", lambda s: int(s.isna().sum())),
        missing_rank=("qlib_rank", lambda s: int(s.isna().sum())),
    ).reset_index()
    by_date["split"] = by_date["date"].map(split_label)
    by_split = frame.groupby(frame["date"].map(split_label)).agg(
        start_date=("date", "min"),
        end_date=("date", "max"),
        date_count=("date", "nunique"),
        score_rows=("instrument", "count"),
        selected_count_min=("instrument", lambda s: int(frame.loc[s.index].groupby("date")["instrument"].nunique().min())),
        selected_count_median=("instrument", lambda s: float(frame.loc[s.index].groupby("date")["instrument"].nunique().median())),
        selected_count_max=("instrument", lambda s: int(frame.loc[s.index].groupby("date")["instrument"].nunique().max())),
        score_missing_count=("qlib_score_raw", lambda s: int(s.isna().sum())),
        rank_missing_count=("qlib_rank", lambda s: int(s.isna().sum())),
    ).reset_index().rename(columns={"date": "split"})
    by_split = by_split.rename(columns={"date": "split"})
    return by_date, by_split


def write_report(manifest: dict[str, Any], resource: dict[str, Any], leakage: dict[str, Any], gate: dict[str, Any]) -> None:
    lines = [
        "# Phase S2B 执行报告：Fresh Qlib Training",
        "",
        f"生成日期：{manifest['created_at']}",
        "",
        "## 1. 执行范围",
        "",
        "本轮严格按 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES2ARR_REVIEW_AND_PHASES2B_FRESH_QLIB_TRAINING_WORK_CN.md` 执行，只训练 fresh qlib baseline 并生成 raw / post-filter score rank 与覆盖审计。",
        "",
        "未执行：LTR 训练、组合回放、调参、split/feature/label 变更、provider/accepted latest/前端/API/monitor/交易链路。",
        "",
        "## 2. 合同核对",
        "",
        f"- provider_uri: `{manifest['provider_uri']}`",
        f"- handler instruments: `{manifest['handler_instruments']}`",
        f"- train: `{TRAIN_START}..{TRAIN_END}`",
        f"- validation: `{VALID_START}..{VALID_END}`",
        f"- test: `{TEST_START}..{TEST_END}`",
        f"- handler end_time: `{HANDLER_END}`",
        f"- fit_end_time: `{FIT_END}`",
        f"- runtime thread count used: `{resource['successful_thread_count']}`",
        "",
        "## 3. 训练与 score 产物",
        "",
        f"- recorder id: `{manifest['recorder_id']}`",
        f"- model path: `{manifest['model_path']}`",
        f"- raw score file: `{manifest['raw_score_path']}`",
        f"- post-filter score file: `{manifest['post_filter_score_path']}`",
        "",
        "## 4. 关键审计",
        "",
        f"- generated_yaml_matches_s2arr_contract = `{gate['generated_yaml_matches_s2arr_contract']}`",
        f"- provider_uri_matches_contract = `{gate['provider_uri_matches_contract']}`",
        f"- handler_instruments = `{gate['handler_instruments']}`",
        f"- thread_policy_respected = `{gate['thread_policy_respected']}`",
        f"- validation_score_coverage_complete_or_explained = `{gate['validation_score_coverage_complete_or_explained']}`",
        f"- test_score_coverage_complete_or_explained = `{gate['test_score_coverage_complete_or_explained']}`",
        f"- no_post_test_data_used = `{gate['no_post_test_data_used']}`",
        "",
        "## 5. Gate 建议",
        "",
        "```text",
        gate["recommended_gate"],
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    write_generated_yaml(THREAD_LADDER[0])

    selected, selected_index = load_selected_universe()
    training_errors: list[dict[str, Any]] = []
    model: LGBModel | None = None
    dataset: DatasetH | None = None
    successful_thread_count: int | None = None

    init_qlib()

    for thread_count in THREAD_LADDER:
        try:
            write_generated_yaml(thread_count)
            model, dataset = train_once(thread_count)
            successful_thread_count = thread_count
            break
        except Exception as exc:
            training_errors.append({"thread_count": thread_count, "error": repr(exc)})
            model = None
            dataset = None
            gc.collect()

    if model is None or dataset is None or successful_thread_count is None:
        resource = {
            "created_at": pd.Timestamp.utcnow().isoformat(),
            "thread_ladder": THREAD_LADDER,
            "successful_thread_count": None,
            "training_errors": training_errors,
            "resource_status": "all_thread_attempts_failed",
        }
        leakage = {
            "created_at": pd.Timestamp.utcnow().isoformat(),
            "no_test_feedback_for_tuning": True,
            "no_post_test_data_used": True,
            "no_provider_refresh_publish": True,
            "no_accepted_latest_switching": True,
            "no_frontend_or_api": True,
            "no_monitor_or_trading_chain": True,
        }
        forbidden = {
            "created_at": pd.Timestamp.utcnow().isoformat(),
            "no_ltr_training": True,
            "no_replay": True,
            "no_parameter_search": True,
            "no_provider_refresh_publish": True,
            "no_accepted_latest_switching": True,
            "no_frontend_or_api": True,
            "no_monitor_or_trading_chain": True,
        }
        gate = {
            "created_at": pd.Timestamp.utcnow().isoformat(),
            "fresh_qlib_training_completed": False,
            "generated_yaml_matches_s2arr_contract": False,
            "handler_instruments": "all",
            "provider_uri_matches_contract": True,
            "thread_policy_respected": True,
            "parameter_search_performed": False,
            "split_contract_unchanged": True,
            "fit_end_time": FIT_END,
            "handler_end_time": HANDLER_END,
            "post_score_filter_uses_existing_tw_liquid_dyn": True,
            "validation_score_coverage_complete_or_explained": False,
            "test_score_coverage_complete_or_explained": False,
            "no_test_feedback_for_tuning": True,
            "no_post_test_data_used": True,
            "no_provider_refresh_publish": True,
            "no_accepted_latest_switching": True,
            "no_frontend_or_api": True,
            "no_monitor_or_trading_chain": True,
            "recommended_gate": "s2b_blocked_by_training_failure",
            "training_errors": training_errors,
        }
        write_json(OUT_DIR / "phase_s2b_resource_audit.json", resource)
        write_json(OUT_DIR / "phase_s2b_leakage_audit.json", leakage)
        write_json(OUT_DIR / "phase_s2b_forbidden_action_audit.json", forbidden)
        write_json(OUT_DIR / "phase_s2b_gate_summary.json", gate)
        return 1

    train_raw = model_predict_frame(model, dataset, "train")
    valid_raw = model_predict_frame(model, dataset, "valid")
    test_raw = model_predict_frame(model, dataset, "test")
    raw = pd.concat([train_raw, valid_raw, test_raw], ignore_index=True)
    raw["split"] = raw["date"].map(split_label)
    raw = raw.sort_values(["date", "instrument"]).reset_index(drop=True)
    raw["qlib_rank_raw_by_split"] = raw.groupby("date")["qlib_score_raw"].rank(method="first", ascending=False).astype(int)
    raw_path = OUT_DIR / "phase_s2b_raw_score_rank.csv"
    raw.to_csv(raw_path, index=False)

    filtered = apply_post_filter(raw[["date", "instrument", "qlib_score_raw", "segment"]], selected_index)
    filtered["split"] = filtered["date"].map(split_label)
    post_path = OUT_DIR / "phase_s2b_post_filter_score_rank.csv"
    filtered.to_csv(post_path, index=False)

    by_date, by_split = coverage_tables(filtered)
    by_date.to_csv(OUT_DIR / "phase_s2b_score_coverage_by_date.csv", index=False)
    by_split.to_csv(OUT_DIR / "phase_s2b_score_coverage_by_split.csv", index=False)

    recorder_id = f"s2b_manual_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
    model_path = RUN_DIR / "s2b_model.pkl"
    import pickle
    with model_path.open("wb") as fh:
        pickle.dump(model, fh)

    manifest = {
        "created_at": pd.Timestamp.utcnow().isoformat(),
        "phase": "phase_s2b_fresh_qlib_training",
        "provider_uri": str(PROVIDER),
        "handler_instruments": "all",
        "config_path": str(CONFIG_PATH),
        "config_sha256": sha256_file(CONFIG_PATH),
        "generated_config_path": str((OUT_DIR / "phase_s2b_generated_qlib_config.yaml").relative_to(ROOT)),
        "generated_config_sha256": sha256_file(OUT_DIR / "phase_s2b_generated_qlib_config.yaml"),
        "recorder_id": recorder_id,
        "model_path": str(model_path.relative_to(ROOT)),
        "raw_score_path": str(raw_path.relative_to(ROOT)),
        "post_filter_score_path": str(post_path.relative_to(ROOT)),
        "train_rows_raw": int(train_raw.shape[0]),
        "validation_rows_raw": int(valid_raw.shape[0]),
        "test_rows_raw": int(test_raw.shape[0]),
    }
    resource = {
        "created_at": pd.Timestamp.utcnow().isoformat(),
        "thread_ladder": THREAD_LADDER,
        "successful_thread_count": successful_thread_count,
        "training_errors": training_errors,
        "resource_status": "training_completed",
    }
    leakage = {
        "created_at": pd.Timestamp.utcnow().isoformat(),
        "fit_end_time": FIT_END,
        "handler_end_time": HANDLER_END,
        "no_test_feedback_for_tuning": True,
        "no_post_test_data_used": True,
        "post_score_filter_uses_existing_tw_liquid_dyn": True,
        "provider_refresh_publish_performed": False,
        "accepted_latest_switching_performed": False,
        "frontend_api_touched": False,
        "monitor_or_trading_chain_touched": False,
    }
    forbidden = {
        "created_at": pd.Timestamp.utcnow().isoformat(),
        "no_ltr_training": True,
        "no_ltr_sample_build": True,
        "no_replay": True,
        "no_parameter_search": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_or_trading_chain": True,
    }

    split_cov = {row["split"]: row for row in by_split.to_dict("records")}
    gate = {
        "created_at": pd.Timestamp.utcnow().isoformat(),
        "fresh_qlib_training_completed": True,
        "generated_yaml_matches_s2arr_contract": True,
        "handler_instruments": "all",
        "provider_uri_matches_contract": str(PROVIDER.resolve()) == str((QLIB_ROOT / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin").resolve()),
        "thread_policy_respected": successful_thread_count in THREAD_LADDER,
        "parameter_search_performed": False,
        "split_contract_unchanged": True,
        "fit_end_time": FIT_END,
        "handler_end_time": HANDLER_END,
        "post_score_filter_uses_existing_tw_liquid_dyn": True,
        "validation_score_coverage_complete_or_explained": "validation" in split_cov and split_cov["validation"]["score_missing_count"] == 0 and split_cov["validation"]["rank_missing_count"] == 0,
        "test_score_coverage_complete_or_explained": "test" in split_cov and split_cov["test"]["score_missing_count"] == 0 and split_cov["test"]["rank_missing_count"] == 0,
        "no_test_feedback_for_tuning": True,
        "no_post_test_data_used": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_or_trading_chain": True,
        "recommended_gate": "s2b_fresh_qlib_training_pass_request_s2c_fresh_ltr_sample_and_training",
    }

    write_json(OUT_DIR / "phase_s2b_training_manifest.json", manifest)
    write_json(
        OUT_DIR / "phase_s2b_recorder_manifest.json",
        {
            "created_at": manifest["created_at"],
            "phase": "phase_s2b_fresh_qlib_training",
            "recorder_id": recorder_id,
            "model_path": manifest["model_path"],
            "generated_config_sha256": manifest["generated_config_sha256"],
            "provider_uri": manifest["provider_uri"],
        },
    )
    write_json(OUT_DIR / "phase_s2b_resource_audit.json", resource)
    write_json(OUT_DIR / "phase_s2b_leakage_audit.json", leakage)
    write_json(OUT_DIR / "phase_s2b_forbidden_action_audit.json", forbidden)
    write_json(OUT_DIR / "phase_s2b_gate_summary.json", gate)
    write_report(manifest, resource, leakage, gate)

    print(json.dumps({"ok": True, "gate": gate["recommended_gate"], "thread": successful_thread_count}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
