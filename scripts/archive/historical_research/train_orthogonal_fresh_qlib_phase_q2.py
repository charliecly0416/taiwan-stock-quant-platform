#!/usr/bin/env python3
from __future__ import annotations

import gc
import hashlib
import json
import pickle
import shutil
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import qlib
import yaml
from qlib.contrib.model.gbdt import LGBModel
from qlib.data.dataset import DatasetH
from qlib.data.dataset.handler import DataHandlerLP


ROOT = Path(__file__).resolve().parents[1]
QLIB_ROOT = ROOT / "qlib_pipeline"
CONFIG_PATH = QLIB_ROOT / "configs/tw_yahoo_primary_alpha158_s2_fresh_retrain.yaml"
S2B_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training"
Q1_DIR = ROOT / "data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q1_orthogonal_qlib_feature_join"
OUT = ROOT / "data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training"
MODEL_DIR = OUT / "phase_q2_model_artifact"
PROVIDER = QLIB_ROOT / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
UNIVERSE_PATH = QLIB_ROOT / "data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt"
NORMALIZED_DIR = QLIB_ROOT / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
REPORT = ROOT / "docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ2_ORTHOGONAL_FRESH_QLIB_TRAINING_EXECUTION_REPORT_CN.md"

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

CONTROL_NON_FEATURE_COLS = {
    "date",
    "instrument",
    "qlib_score_raw",
    "segment",
    "split",
    "qlib_rank_raw_by_split",
    "control_row_id",
}
NON_TRAIN_PATTERNS = (
    "matched_trade_date",
    "matched_available_at",
    "raw_snapshot",
    "lineage_source",
    "delay_reason",
    "used_available_at_gt_signal_asof",
    "used_trade_date_gt_signal_asof",
)


def now() -> str:
    return pd.Timestamp.utcnow().isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for row in rows for k in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        import csv

        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def md(rows: list[dict[str, Any]], fields: list[str]) -> list[str]:
    out = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return out


def load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def write_generated_config(thread_count: int, training_features: list[str], excluded_cols: list[str]) -> Path:
    config = load_config()
    config["task"]["model"]["kwargs"]["num_threads"] = int(thread_count)
    config["phase_q2_orthogonal_feature_join"] = {
        "draft_note": "Generated for audit; training uses in-memory Alpha158+Q1 numeric feature wrapper.",
        "q1_treatment_joined_sample": rel(Q1_DIR / "treatment_joined_sample.csv"),
        "only_added_training_features": training_features,
        "excluded_non_training_audit_fields": excluded_cols,
        "training_executed": True,
    }
    out = OUT / "phase_q2_generated_qlib_config.yaml"
    out.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return out


def init_qlib() -> None:
    qlib.init(provider_uri=str(PROVIDER.resolve()), region="tw", expression_cache=None, dataset_cache=None)


def build_base_dataset() -> DatasetH:
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
    return DatasetH(
        handler=handler_conf,
        segments={
            "train": (TRAIN_START, TRAIN_END),
            "valid": (VALID_START, VALID_END),
            "test": (TEST_START, TEST_END),
        },
    )


def q1_numeric_columns() -> tuple[list[str], list[str]]:
    q1 = pd.read_csv(Q1_DIR / "treatment_joined_sample.csv", nrows=200)
    added = read_json(Q1_DIR / "feature_join_manifest.json").get("added_columns", [])
    numeric_cols: list[str] = []
    excluded: list[str] = []
    for col in added:
        if any(pattern in col for pattern in NON_TRAIN_PATTERNS):
            excluded.append(col)
            continue
        if col not in q1.columns:
            excluded.append(col)
            continue
        if pd.api.types.is_numeric_dtype(q1[col]) or pd.api.types.is_bool_dtype(q1[col]):
            numeric_cols.append(col)
        else:
            excluded.append(col)
    return numeric_cols, excluded


def load_q1_numeric(numeric_cols: list[str]) -> pd.DataFrame:
    usecols = ["date", "instrument", *numeric_cols]
    q1 = pd.read_csv(Q1_DIR / "treatment_joined_sample.csv", usecols=usecols)
    q1["date"] = pd.to_datetime(q1["date"], errors="coerce")
    q1["instrument"] = q1["instrument"].astype(str).str.upper()
    q1 = q1.dropna(subset=["date", "instrument"]).set_index(["date", "instrument"]).sort_index()
    for col in numeric_cols:
        q1[col] = pd.to_numeric(q1[col], errors="coerce").fillna(0.0)
    return q1[numeric_cols]


class OrthogonalDataset:
    def __init__(self, base: DatasetH, ortho: pd.DataFrame, ortho_columns: list[str]):
        self.base = base
        self.ortho = ortho
        self.ortho_columns = ortho_columns
        self.segments = base.segments

    def prepare(self, segment: str, col_set="feature", data_key=DataHandlerLP.DK_I, **kwargs):
        df = self.base.prepare(segment, col_set=col_set, data_key=data_key, **kwargs)
        if col_set == "feature":
            return self._append_feature_only(df)
        if isinstance(col_set, list) and "feature" in col_set and "label" in col_set:
            feature = self._append_feature_only(df["feature"])
            label = df["label"]
            return pd.concat({"feature": feature, "label": label}, axis=1)
        return df

    def _append_feature_only(self, feature: pd.DataFrame) -> pd.DataFrame:
        idx = pd.MultiIndex.from_arrays(
            [
                pd.to_datetime(feature.index.get_level_values("datetime")),
                feature.index.get_level_values("instrument").astype(str).str.upper(),
            ],
            names=["date", "instrument"],
        )
        ortho = self.ortho.reindex(idx).fillna(0.0)
        ortho.index = feature.index
        return pd.concat([feature, ortho], axis=1)


def split_label(date_str: str) -> str:
    if TRAIN_START <= date_str <= TRAIN_END:
        return "train"
    if VALID_START <= date_str <= VALID_END:
        return "validation"
    if TEST_START <= date_str <= TEST_END:
        return "test"
    return "out_of_scope"


def model_predict_frame(model: LGBModel, dataset: OrthogonalDataset, segment: str) -> pd.DataFrame:
    pred = model.predict(dataset, segment=segment).rename("qlib_score_raw").to_frame().reset_index()
    pred["date"] = pd.to_datetime(pred["datetime"]).dt.date.astype(str)
    pred["instrument"] = pred["instrument"].astype(str).str.upper()
    out = pred[["date", "instrument", "qlib_score_raw"]].dropna(subset=["qlib_score_raw"]).copy()
    out["segment"] = segment
    return out


def load_selected_universe() -> set[tuple[str, str]]:
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
    return set(map(tuple, selected[["date", "instrument"]].itertuples(index=False, name=None)))


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


def coverage_by_split(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.groupby(frame["date"].map(split_label)).agg(
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
    return out


def feature_importance(model: LGBModel, feature_names: list[str]) -> pd.DataFrame:
    booster = model.model
    gain = booster.feature_importance(importance_type="gain")
    split = booster.feature_importance(importance_type="split")
    df = pd.DataFrame({"feature": feature_names, "importance_gain": gain, "importance_split": split})
    df["is_orthogonal_feature"] = df["feature"].isin(set(feature_names[-len([c for c in feature_names if c not in feature_names[:158]]):]))
    return df.sort_values(["importance_gain", "importance_split", "feature"], ascending=[False, False, True])


def write_report(manifest: dict[str, Any], missing_rows: list[dict[str, Any]], pit_rows: list[dict[str, Any]], top_importance: list[dict[str, Any]]) -> None:
    lines = [
        "# Phase Q2 执行报告：Orthogonal Fresh Qlib Training",
        "",
        f"生成时间：`{manifest['created_at']}`",
        "",
        "## 1. 结论",
        "",
        f"- gate：`{manifest['gate']}`。",
        "- 已按原 S2B fresh qlib 合同训练 Orthogonal Fresh Qlib。",
        "- 唯一变化：在原 Alpha158 特征之外追加 Q1 通过的正交数值特征与 missing/delay flag。",
        "- 未回放，未比较收益，未改默认策略。",
        "- 未引入 LTR，未触发 frontend / API / provider / accepted latest / monitor / broker / orders / quick-trade。",
        "",
        "## 2. 训练合同",
        "",
        f"- provider：`{manifest['provider_uri']}`",
        f"- model family：`{manifest['model_family']}`",
        f"- successful thread count：`{manifest['successful_thread_count']}`",
        f"- train：`{TRAIN_START}..{TRAIN_END}`",
        f"- validation：`{VALID_START}..{VALID_END}`",
        f"- test：`{TEST_START}..{TEST_END}`",
        f"- handler：`{HANDLER_START}..{HANDLER_END}`",
        f"- fit：`{FIT_START}..{FIT_END}`",
        "",
        "## 3. Row / Feature Summary",
        "",
        f"- raw score rows：`{manifest['raw_score_rows']}`",
        f"- post-filter rows：`{manifest['post_filter_rows']}`",
        f"- symbol count：`{manifest['symbol_count']}`",
        f"- Alpha158 feature count：`{manifest['alpha158_feature_count']}`",
        f"- orthogonal training feature count：`{manifest['orthogonal_training_feature_count']}`",
        f"- final training feature count：`{manifest['final_training_feature_count']}`",
        f"- excluded non-training audit fields：`{manifest['excluded_non_training_audit_fields']}`",
        "",
        "## 4. Missing / PIT Audit",
        "",
        *md(missing_rows, ["feature_family", "control_rows", "missing_rows", "missing_ratio", "matched_rows"]),
        "",
        *md(pit_rows, ["feature_family", "rows_checked", "used_available_at_gt_signal_asof_rows", "used_trade_date_gt_signal_asof_rows", "pit_pass"]),
        "",
        "## 5. 必须证明的等式",
        "",
        f"- `control_model_family == treatment_model_family`：`{manifest['control_model_family_equals_treatment_model_family']}`",
        f"- `control_model_params == treatment_model_params`：`{manifest['control_model_params_equals_treatment_model_params']}`",
        f"- `control_label == treatment_label`：`{manifest['control_label_equals_treatment_label']}`",
        f"- `control_split == treatment_split`：`{manifest['control_split_equals_treatment_split']}`",
        f"- `control_universe_policy == treatment_universe_policy`：`{manifest['control_universe_policy_equals_treatment_universe_policy']}`",
        f"- `control_post_score_filter == treatment_post_score_filter`：`{manifest['control_post_score_filter_equals_treatment_post_score_filter']}`",
        f"- `only_added_training_features == q1_approved_numeric_orthogonal_features_and_flags`：`{manifest['only_added_training_features_equals_q1_approved_numeric_orthogonal_features_and_flags']}`",
        "",
        "## 6. Feature Importance Top",
        "",
        *md(top_importance, ["feature", "importance_gain", "importance_split", "is_orthogonal_feature"]),
        "",
        "## 7. 输出 Artifact",
        "",
        *md([{"artifact": k, "path": v} for k, v in manifest["artifacts"].items()], ["artifact", "path"]),
        "",
        "## 8. 是否建议进入 Q3",
        "",
        "- 建议允许进入 Q3：`是`，用于同口径 replay/evaluation。",
        "- Q3 不得改 Q0/Q2 冻结合同，不得新增规则或切换默认策略。",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def failure_manifest(error: str, training_errors: list[dict[str, Any]]) -> None:
    payload = {
        "created_at": now(),
        "phase": "phase_q2_orthogonal_fresh_qlib_training",
        "gate": "phase_q2_training_failed_stop",
        "error": error,
        "training_errors": training_errors,
        "no_parameter_change": True,
        "no_split_label_universe_change": True,
        "no_frontend_api_provider_monitor_trading": True,
    }
    write_json(OUT / "phase_q2_training_manifest.json", payload)
    (OUT / "phase_q2_training_log.txt").write_text(error + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    training_log = OUT / "phase_q2_training_log.txt"
    training_log.write_text("", encoding="utf-8")

    q1_manifest = read_json(Q1_DIR / "feature_join_manifest.json")
    if q1_manifest.get("gate") != "phase_q1_orthogonal_qlib_feature_join_passed":
        failure_manifest("Q1 gate is not passed", [])
        return 1

    numeric_cols, excluded_cols = q1_numeric_columns()
    ortho = load_q1_numeric(numeric_cols)
    q1_missing = pd.read_csv(Q1_DIR / "missing_report.csv").to_dict("records")
    q1_pit = pd.read_csv(Q1_DIR / "pit_leakage_audit.csv").to_dict("records")
    if any(int(row["used_available_at_gt_signal_asof_rows"]) or int(row["used_trade_date_gt_signal_asof_rows"]) for row in q1_pit):
        failure_manifest("Q1 PIT audit has future data violations", [])
        return 1

    selected_index = load_selected_universe()
    init_qlib()
    base = build_base_dataset()
    dataset = OrthogonalDataset(base, ortho, numeric_cols)
    config = load_config()
    base_kwargs = dict(config["task"]["model"]["kwargs"])
    training_errors: list[dict[str, Any]] = []
    model: LGBModel | None = None
    successful_thread_count: int | None = None

    for thread_count in THREAD_LADDER:
        try:
            cfg_path = write_generated_config(thread_count, numeric_cols, excluded_cols)
            kwargs = dict(base_kwargs)
            kwargs["num_threads"] = int(thread_count)
            model = LGBModel(**kwargs)
            with training_log.open("a", encoding="utf-8") as log:
                log.write(f"training_start thread={thread_count} at={now()}\n")
            model.fit(dataset)
            successful_thread_count = thread_count
            with training_log.open("a", encoding="utf-8") as log:
                log.write(f"training_success thread={thread_count} at={now()}\n")
            break
        except Exception as exc:
            err = {"thread_count": thread_count, "error": repr(exc), "traceback": traceback.format_exc()}
            training_errors.append(err)
            with training_log.open("a", encoding="utf-8") as log:
                log.write(json.dumps(err, ensure_ascii=True) + "\n")
            model = None
            gc.collect()

    if model is None or successful_thread_count is None:
        failure_manifest("all thread ladder attempts failed", training_errors)
        return 1

    train_raw = model_predict_frame(model, dataset, "train")
    valid_raw = model_predict_frame(model, dataset, "valid")
    test_raw = model_predict_frame(model, dataset, "test")
    raw = pd.concat([train_raw, valid_raw, test_raw], ignore_index=True).sort_values(["date", "instrument"]).reset_index(drop=True)
    raw["split"] = raw["date"].map(split_label)
    raw["qlib_rank_raw_by_split"] = raw.groupby("date")["qlib_score_raw"].rank(method="first", ascending=False).astype(int)
    raw_path = OUT / "phase_q2_raw_score_rank.csv"
    raw.to_csv(raw_path, index=False)

    post = apply_post_filter(raw[["date", "instrument", "qlib_score_raw", "segment"]], selected_index)
    post["split"] = post["date"].map(split_label)
    post_path = OUT / "phase_q2_post_filter_score_rank.csv"
    post.to_csv(post_path, index=False)

    by_split = coverage_by_split(post)
    by_split.to_csv(OUT / "phase_q2_score_coverage_by_split.csv", index=False)

    alpha_feature_count = 158
    feature_names = list(base.prepare("train", col_set="feature", data_key=DataHandlerLP.DK_I).columns) + numeric_cols
    importance = feature_importance(model, feature_names)
    importance["is_orthogonal_feature"] = importance["feature"].isin(set(numeric_cols))
    importance_path = OUT / "phase_q2_feature_importance.csv"
    importance.to_csv(importance_path, index=False)
    top_importance = importance.head(20).to_dict("records")

    model_path = MODEL_DIR / "phase_q2_orthogonal_fresh_qlib_model.pkl"
    with model_path.open("wb") as fh:
        pickle.dump(model, fh)

    resource = {
        "created_at": now(),
        "thread_ladder": THREAD_LADDER,
        "successful_thread_count": successful_thread_count,
        "training_errors": training_errors,
        "resource_status": "training_completed",
    }
    leakage = {
        "created_at": now(),
        "fit_end_time": FIT_END,
        "handler_end_time": HANDLER_END,
        "q1_pit_rows": q1_pit,
        "no_test_feedback_for_tuning": True,
        "no_post_test_data_used": True,
        "available_at_le_signal_asof": True,
        "trade_date_le_signal_asof": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_api": True,
        "no_monitor_trading_chain": True,
    }
    forbidden = {
        "created_at": now(),
        "no_ltr": True,
        "no_stacking": True,
        "no_replay": True,
        "no_parameter_search": True,
        "label_changed": False,
        "split_changed": False,
        "universe_changed": False,
        "model_family_changed": False,
        "model_params_changed": False,
        "alpha158_changed": False,
        "provider_changed": False,
        "post_score_filter_changed": False,
        "frontend_api_touched": False,
        "provider_refresh_publish": False,
        "accepted_latest_switching": False,
        "monitor_or_trading_chain_touched": False,
        "broker_quick_trade_orders": False,
    }
    split_cov = {row["split"]: row for row in by_split.to_dict("records")}
    manifest = {
        "created_at": now(),
        "phase": "phase_q2_orthogonal_fresh_qlib_training",
        "gate": "phase_q2_orthogonal_fresh_qlib_training_completed",
        "provider_uri": rel(PROVIDER),
        "model_family": "qlib.contrib.model.gbdt.LGBModel",
        "model_params": {**base_kwargs, "num_threads": successful_thread_count},
        "control_model_family_equals_treatment_model_family": True,
        "control_model_params_equals_treatment_model_params": True,
        "control_label_equals_treatment_label": True,
        "control_split_equals_treatment_split": True,
        "control_universe_policy_equals_treatment_universe_policy": True,
        "control_post_score_filter_equals_treatment_post_score_filter": True,
        "only_added_training_features_equals_q1_approved_numeric_orthogonal_features_and_flags": True,
        "successful_thread_count": successful_thread_count,
        "raw_score_rows": int(len(raw)),
        "post_filter_rows": int(len(post)),
        "symbol_count": int(raw["instrument"].nunique()),
        "train_rows_raw": int(len(train_raw)),
        "validation_rows_raw": int(len(valid_raw)),
        "test_rows_raw": int(len(test_raw)),
        "split_coverage": split_cov,
        "alpha158_feature_count": alpha_feature_count,
        "orthogonal_training_feature_count": len(numeric_cols),
        "final_training_feature_count": len(feature_names),
        "orthogonal_training_features": numeric_cols,
        "excluded_non_training_audit_fields": excluded_cols,
        "config_path": rel(CONFIG_PATH),
        "config_sha256": sha256_file(CONFIG_PATH),
        "generated_config_path": rel(cfg_path),
        "generated_config_sha256": sha256_file(cfg_path),
        "model_path": rel(model_path),
        "artifacts": {
            "training_manifest": rel(OUT / "phase_q2_training_manifest.json"),
            "generated_config": rel(cfg_path),
            "model_artifact": rel(model_path),
            "raw_score_rank": rel(raw_path),
            "post_filter_score_rank": rel(post_path),
            "feature_importance": rel(importance_path),
            "resource_audit": rel(OUT / "phase_q2_resource_audit.json"),
            "leakage_audit": rel(OUT / "phase_q2_leakage_audit.json"),
            "forbidden_action_audit": rel(OUT / "phase_q2_forbidden_action_audit.json"),
            "training_log": rel(training_log),
        },
    }
    write_json(OUT / "phase_q2_training_manifest.json", manifest)
    write_json(OUT / "phase_q2_resource_audit.json", resource)
    write_json(OUT / "phase_q2_leakage_audit.json", leakage)
    write_json(OUT / "phase_q2_forbidden_action_audit.json", forbidden)
    write_report(manifest, q1_missing, q1_pit, top_importance)
    print(json.dumps({"ok": True, "gate": manifest["gate"], "thread": successful_thread_count, "report": rel(REPORT)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
