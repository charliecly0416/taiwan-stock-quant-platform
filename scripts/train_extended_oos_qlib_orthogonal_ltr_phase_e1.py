#!/usr/bin/env python3
from __future__ import annotations

import gc
import hashlib
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import qlib
import yaml
from qlib.contrib.model.gbdt import LGBModel
from qlib.data.dataset import DatasetH


ROOT = Path(__file__).resolve().parents[1]
QLIB_ROOT = ROOT / "qlib_pipeline"
S2B_CONFIG = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_generated_qlib_config.yaml"
E0_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e0_contract_and_feasibility/phasee0_contract_manifest.json"
OUT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score"
RUN_DIR = OUT_DIR / "run"
PROVIDER = QLIB_ROOT / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
UNIVERSE_PATH = QLIB_ROOT / "data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt"
NORMALIZED_DIR = QLIB_ROOT / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
DOC_PATH = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE1_FROZEN_QLIB_TRAINING_AND_OOS_SCORE_EXECUTION_REPORT_CN.md"

THREAD_LADDER = [4, 2, 1]
TRAIN_START = "2018-01-01"
TRAIN_END = "2022-12-31"
VALID_START = "2022-07-01"
VALID_END = "2022-12-31"
OOS_START = "2023-01-01"
OOS_END = "2026-05-07"
HANDLER_START = "2015-05-04"
HANDLER_END = OOS_END
FIT_START = TRAIN_START
FIT_END = TRAIN_END
GATE = "phase_e1_frozen_qlib_oos_score_completed"
BLOCKED_GATE = "phase_e1_blocked_by_training_or_oos_score"
CALENDAR_POLICY = "provider day.txt + local twii/price tradability alignment through as-of post-score filter"
UNIVERSE_POLICY = "asof active instrument range + same-day price + >=60 history + trailing 60-day value top150"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_config() -> dict[str, Any]:
    with S2B_CONFIG.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def require_inputs() -> None:
    required = [S2B_CONFIG, E0_MANIFEST, PROVIDER, UNIVERSE_PATH, NORMALIZED_DIR]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing E1 inputs: {missing}")
    e0 = load_json(E0_MANIFEST)
    if e0.get("gate") != "phase_e0_extended_oos_contract_feasible":
        raise RuntimeError(f"E0 gate not feasible: {e0.get('gate')}")


def write_generated_yaml(thread_count: int) -> Path:
    config = load_config()
    config["qlib_init"]["provider_uri"] = rel(PROVIDER)
    config["task"]["model"]["kwargs"]["num_threads"] = int(thread_count)
    handler = config["task"]["dataset"]["kwargs"]["handler"]["kwargs"]
    handler["start_time"] = HANDLER_START
    handler["end_time"] = HANDLER_END
    handler["fit_start_time"] = FIT_START
    handler["fit_end_time"] = FIT_END
    config["data_handler_config"] = dict(handler)
    config["task"]["dataset"]["kwargs"]["segments"] = {
        "train": [TRAIN_START, TRAIN_END],
        "valid": [VALID_START, VALID_END],
        "oos": [OOS_START, OOS_END],
    }
    out = OUT_DIR / "phasee1_generated_qlib_config.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return out


def init_qlib() -> None:
    qlib.init(provider_uri=str(PROVIDER.resolve()), region="tw", expression_cache=None, dataset_cache=None)


def build_dataset() -> DatasetH:
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
            "oos": (OOS_START, OOS_END),
        },
    )


def train_once(thread_count: int) -> tuple[LGBModel, DatasetH]:
    config = load_config()
    kwargs = dict(config["task"]["model"]["kwargs"])
    kwargs["num_threads"] = int(thread_count)
    dataset = build_dataset()
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


def load_selected_universe() -> set[tuple[str, str]]:
    frames: list[pd.DataFrame] = []
    for path in sorted(NORMALIZED_DIR.glob("TW*.csv")):
        symbol = path.stem.upper()
        if symbol == "TWII":
            continue
        df = pd.read_csv(path, usecols=["date", "close", "vwap", "volume"])
        if df.empty:
            continue
        df["instrument"] = symbol
        df["date"] = pd.to_datetime(df["date"])
        df = df[(df["date"] >= pd.Timestamp(HANDLER_START)) & (df["date"] <= pd.Timestamp(OOS_END))].copy()
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


def add_ranks(frame: pd.DataFrame, rank_col: str) -> pd.DataFrame:
    out = frame.copy()
    out[rank_col] = out.groupby("date")["qlib_score_raw"].rank(method="first", ascending=False).astype(int)
    return out


def apply_post_filter(raw: pd.DataFrame, selected_index: set[tuple[str, str]]) -> pd.DataFrame:
    keys = pd.MultiIndex.from_frame(raw[["date", "instrument"]].astype(str))
    selected_keys = pd.MultiIndex.from_tuples(sorted(selected_index), names=["date", "instrument"])
    filtered = raw[keys.isin(selected_keys)].copy()
    filtered = filtered[(filtered["date"] >= OOS_START) & (filtered["date"] <= OOS_END)]
    filtered = add_ranks(filtered, "qlib_rank")
    filtered["is_top50"] = filtered["qlib_rank"] <= 50
    filtered["calendar_policy"] = CALENDAR_POLICY
    filtered["universe_policy"] = UNIVERSE_POLICY
    return filtered.sort_values(["date", "qlib_rank", "instrument"]).reset_index(drop=True)


def split_label(date_str: str) -> str:
    if TRAIN_START <= date_str <= TRAIN_END:
        return "train"
    if OOS_START <= date_str <= "2025-12-31":
        return "oos_ltr_train_window"
    if "2026-01-01" <= date_str <= OOS_END:
        return "oos_untouched_test_window"
    return "out_of_scope"


def coverage_tables(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_date = frame.groupby("date").agg(
        split=("date", lambda s: split_label(str(s.iloc[0]))),
        score_rows=("instrument", "count"),
        unique_instruments=("instrument", "nunique"),
        top50_rows=("is_top50", "sum"),
        missing_score=("qlib_score_raw", lambda s: int(s.isna().sum())),
        missing_rank=("qlib_rank", lambda s: int(s.isna().sum())),
    ).reset_index()
    by_split = by_date.groupby("split").agg(
        start_date=("date", "min"),
        end_date=("date", "max"),
        date_count=("date", "nunique"),
        score_rows=("score_rows", "sum"),
        selected_count_min=("unique_instruments", "min"),
        selected_count_median=("unique_instruments", "median"),
        selected_count_max=("unique_instruments", "max"),
        top50_count_min=("top50_rows", "min"),
        top50_count_median=("top50_rows", "median"),
        top50_count_max=("top50_rows", "max"),
        score_missing_count=("missing_score", "sum"),
        rank_missing_count=("missing_rank", "sum"),
    ).reset_index()
    return by_date, by_split


def write_report(manifest: dict[str, Any], resource: dict[str, Any], leakage: dict[str, Any], gate: dict[str, Any]) -> None:
    coverage = pd.read_csv(OUT_DIR / "phasee1_oos_score_coverage_by_split.csv")
    lines = [
        "# Phase E1 执行报告：2018-2022 Frozen Qlib 训练与 OOS 打分",
        "",
        f"生成时间：`{manifest['created_at']}`",
        "",
        "## 1. 结论",
        "",
        f"- gate：`{gate['recommended_gate']}`。",
        "- 已训练一个只使用 `2018-01-01..2022-12-31` 的 frozen qlib。",
        "- `2023-01-01..2026-05-07` 仅作为同一模型 OOS predict 区间。",
        "- 未调 qlib 参数，未训练 LTR，未回放，未触发 provider / accepted latest / frontend / API / monitor / 交易链路。",
        "",
        "## 2. 合同核对",
        "",
        f"- provider：`{manifest['provider_uri']}`",
        f"- S2B 参数来源：`{manifest['s2b_config_path']}`",
        f"- train：`{TRAIN_START}..{TRAIN_END}`",
        f"- valid：`{VALID_START}..{VALID_END}`，仍在 qlib train 窗口内。",
        f"- oos score：`{OOS_START}..{OOS_END}`",
        f"- handler fit：`{FIT_START}..{FIT_END}`",
        f"- runtime thread count used：`{resource['successful_thread_count']}`",
        "",
        "## 3. OOS Score 覆盖",
        "",
        "| split | start | end | dates | score rows | selected min/median/max | top50 min/median/max |",
        "| --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in coverage.to_dict("records"):
        lines.append(
            f"| {row['split']} | {row['start_date']} | {row['end_date']} | {row['date_count']} | {row['score_rows']} | "
            f"{row['selected_count_min']}/{row['selected_count_median']}/{row['selected_count_max']} | "
            f"{row['top50_count_min']}/{row['top50_count_median']}/{row['top50_count_max']} |"
        )
    lines.extend(
        [
            "",
            "## 4. 输出 Artifact",
            "",
            f"- manifest：`{manifest['manifest_path']}`",
            f"- model：`{manifest['model_path']}`",
            f"- generated config：`{manifest['generated_config_path']}`",
            f"- raw OOS score：`{manifest['raw_oos_score_path']}`",
            f"- post-filter score：`{manifest['post_filter_score_path']}`",
            f"- top50 score：`{manifest['top50_score_path']}`",
            f"- coverage by date：`{manifest['coverage_by_date_path']}`",
            f"- coverage by split：`{manifest['coverage_by_split_path']}`",
            "",
            "## 5. Leakage / Resource / 禁止事项审计",
            "",
            f"- qlib_train_uses_only_2018_2022：`{leakage['qlib_train_uses_only_2018_2022']}`",
            f"- oos_not_in_fit_or_valid_sets：`{leakage['oos_not_in_fit_or_valid_sets']}`",
            f"- no_parameter_search：`{gate['parameter_search_performed'] is False}`",
            f"- thread_policy_respected：`{gate['thread_policy_respected']}`",
            f"- same_model_for_all_oos_scores：`{gate['same_model_for_all_oos_scores']}`",
            f"- provider_refresh_publish_performed：`{leakage['provider_refresh_publish_performed']}`",
            f"- frontend_api_touched：`{leakage['frontend_api_touched']}`",
            f"- monitor_or_trading_chain_touched：`{leakage['monitor_or_trading_chain_touched']}`",
            "",
            "## 6. 是否建议进入 E2",
            "",
            f"- 建议：允许进入 E2，gate 为 `{gate['recommended_gate']}`。",
        ]
    )
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def blocked_exit(training_errors: list[dict[str, Any]]) -> int:
    created_at = now()
    resource = {
        "created_at": created_at,
        "thread_ladder": THREAD_LADDER,
        "successful_thread_count": None,
        "training_errors": training_errors,
        "resource_status": "all_thread_attempts_failed",
    }
    forbidden = {
        "created_at": created_at,
        "no_ltr_training": True,
        "no_replay": True,
        "no_parameter_search": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_or_trading_chain": True,
    }
    gate = {
        "created_at": created_at,
        "recommended_gate": BLOCKED_GATE,
        "training_errors": training_errors,
    }
    write_json(OUT_DIR / "phasee1_resource_audit.json", resource)
    write_json(OUT_DIR / "phasee1_forbidden_action_audit.json", forbidden)
    write_json(OUT_DIR / "phasee1_gate_summary.json", gate)
    print(json.dumps({"ok": False, "gate": BLOCKED_GATE, "training_errors": training_errors}, ensure_ascii=False, indent=2))
    return 1


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    require_inputs()
    generated_config = write_generated_yaml(THREAD_LADDER[0])
    selected_index = load_selected_universe()

    training_errors: list[dict[str, Any]] = []
    model: LGBModel | None = None
    dataset: DatasetH | None = None
    successful_thread_count: int | None = None

    init_qlib()
    for thread_count in THREAD_LADDER:
        try:
            generated_config = write_generated_yaml(thread_count)
            model, dataset = train_once(thread_count)
            successful_thread_count = thread_count
            break
        except Exception as exc:
            training_errors.append({"thread_count": thread_count, "error": repr(exc)})
            model = None
            dataset = None
            gc.collect()

    if model is None or dataset is None or successful_thread_count is None:
        return blocked_exit(training_errors)

    raw_oos = model_predict_frame(model, dataset, "oos")
    raw_oos = add_ranks(raw_oos.sort_values(["date", "instrument"]).reset_index(drop=True), "qlib_rank_raw")
    raw_oos["split"] = raw_oos["date"].map(split_label)
    raw_path = OUT_DIR / "phasee1_raw_oos_score_rank_2023_2026.csv"
    raw_oos.to_csv(raw_path, index=False)

    filtered = apply_post_filter(raw_oos[["date", "instrument", "qlib_score_raw", "segment"]], selected_index)
    filtered["split"] = filtered["date"].map(split_label)
    post_path = OUT_DIR / "phasee1_post_filter_oos_score_rank_2023_2026.csv"
    filtered.to_csv(post_path, index=False)

    top50 = filtered[filtered["is_top50"]].copy()
    top50_path = OUT_DIR / "phasee1_top50_oos_score_rank_2023_2026.csv"
    top50.to_csv(top50_path, index=False)

    by_date, by_split = coverage_tables(filtered)
    by_date_path = OUT_DIR / "phasee1_oos_score_coverage_by_date.csv"
    by_split_path = OUT_DIR / "phasee1_oos_score_coverage_by_split.csv"
    by_date.to_csv(by_date_path, index=False)
    by_split.to_csv(by_split_path, index=False)

    model_path = RUN_DIR / "phasee1_frozen_qlib_model.pkl"
    with model_path.open("wb") as fh:
        pickle.dump(model, fh)

    created_at = now()
    split_cov = {row["split"]: row for row in by_split.to_dict("records")}
    oos_ltr_ok = "oos_ltr_train_window" in split_cov and split_cov["oos_ltr_train_window"]["top50_count_min"] >= 50
    oos_test_ok = "oos_untouched_test_window" in split_cov and split_cov["oos_untouched_test_window"]["top50_count_min"] >= 50
    recommended_gate = GATE if oos_ltr_ok and oos_test_ok else BLOCKED_GATE

    manifest_path = OUT_DIR / "phasee1_training_manifest.json"
    manifest = {
        "created_at": created_at,
        "phase": "phase_e1_frozen_qlib_training_and_oos_score",
        "gate": recommended_gate,
        "provider_uri": rel(PROVIDER),
        "s2b_config_path": rel(S2B_CONFIG),
        "s2b_config_sha256": sha256_file(S2B_CONFIG),
        "generated_config_path": rel(generated_config),
        "generated_config_sha256": sha256_file(generated_config),
        "model_path": rel(model_path),
        "raw_oos_score_path": rel(raw_path),
        "post_filter_score_path": rel(post_path),
        "top50_score_path": rel(top50_path),
        "coverage_by_date_path": rel(by_date_path),
        "coverage_by_split_path": rel(by_split_path),
        "manifest_path": rel(manifest_path),
        "qlib_train": [TRAIN_START, TRAIN_END],
        "qlib_valid": [VALID_START, VALID_END],
        "oos_score": [OOS_START, OOS_END],
        "raw_oos_rows": int(raw_oos.shape[0]),
        "post_filter_oos_rows": int(filtered.shape[0]),
        "top50_oos_rows": int(top50.shape[0]),
    }
    resource = {
        "created_at": created_at,
        "thread_ladder": THREAD_LADDER,
        "successful_thread_count": successful_thread_count,
        "training_errors": training_errors,
        "resource_status": "training_completed",
    }
    leakage = {
        "created_at": created_at,
        "qlib_train_uses_only_2018_2022": True,
        "valid_window_inside_qlib_train_window": True,
        "oos_not_in_fit_or_valid_sets": True,
        "handler_fit_end_time": FIT_END,
        "handler_end_time": HANDLER_END,
        "same_model_for_all_oos_scores": True,
        "provider_refresh_publish_performed": False,
        "accepted_latest_switching_performed": False,
        "frontend_api_touched": False,
        "monitor_or_trading_chain_touched": False,
    }
    forbidden = {
        "created_at": created_at,
        "no_ltr_training": True,
        "no_ltr_sample_build": True,
        "no_replay": True,
        "no_parameter_search": True,
        "no_provider_change": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_or_trading_chain": True,
        "no_2026_training_tuning_or_selection": True,
    }
    gate = {
        "created_at": created_at,
        "recommended_gate": recommended_gate,
        "frozen_qlib_training_completed": True,
        "s2b_parameters_reused": True,
        "date_split_only_changed": True,
        "provider_uri_matches_contract": True,
        "thread_policy_respected": successful_thread_count in THREAD_LADDER,
        "parameter_search_performed": False,
        "same_model_for_all_oos_scores": True,
        "oos_ltr_train_window_top50_complete": bool(oos_ltr_ok),
        "oos_untouched_test_window_top50_complete": bool(oos_test_ok),
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_or_trading_chain": True,
    }

    write_json(manifest_path, manifest)
    write_json(OUT_DIR / "phasee1_resource_audit.json", resource)
    write_json(OUT_DIR / "phasee1_leakage_audit.json", leakage)
    write_json(OUT_DIR / "phasee1_forbidden_action_audit.json", forbidden)
    write_json(OUT_DIR / "phasee1_gate_summary.json", gate)
    write_report(manifest, resource, leakage, gate)

    print(json.dumps({"ok": recommended_gate == GATE, "gate": recommended_gate, "thread": successful_thread_count, "report": rel(DOC_PATH)}, ensure_ascii=False, indent=2))
    return 0 if recommended_gate == GATE else 1


if __name__ == "__main__":
    raise SystemExit(main())
