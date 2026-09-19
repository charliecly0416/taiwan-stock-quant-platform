#!/usr/bin/env python3
"""Materialize the research-only 2026-09-16 B19R2R V3 pre-capture bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_v3_bundle_20260916"
ASOF = "2026-09-16"
CUTOFF = "2026-09-16T14:57:26+00:00"
FINAL_MODEL_FROZEN_AT = "2026-09-16T13:16:00+00:00"
SOURCE_RUN = "finmind.logical.20260916.2e6d6cc1257daf79dcdc"
MODEL_A_ID = "e4_frozen_qlib_2018_2022"
MODEL_B_ID = "modelb_b19r2r_lambdarank_exact50_78f_v2"
MODEL_B_SHA = "8d31069593cc8a1cc7c6fa7ac4cf50a9e897a76af0ab446ddbc26551fc5e5421"
FEATURE_ORDER_SHA = "2e0c169fb7762240aa20bc31ea53ac21b6a69db99dabea2f897421121105f2ca"
EXCLUDED = {"TW7769"}
MODEL_A_DIR = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng9_daily_auto_model_signal_gate_20260916_20260916T145726Z"
MODEL_A_SIGNALS = MODEL_A_DIR / "signals.csv"
MODEL_A_MANIFEST = MODEL_A_DIR / "manifest.json"
MODEL_A_PRE_CUTOFF_DIR = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260916_20260916T145712Z"
MODEL_A_PRE_CUTOFF_PREDICTION = MODEL_A_PRE_CUTOFF_DIR / "prediction.csv"
MODEL_A_PRE_CUTOFF_METADATA = MODEL_A_PRE_CUTOFF_DIR / "run_metadata.json"
MODEL_A_PRE_CUTOFF_ARTIFACT_MANIFEST = MODEL_A_PRE_CUTOFF_DIR / "artifact_manifest.json"
MODEL_A_SIGNAL_ROOT = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022"
MODEL_A_HISTORY = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916/MODEL_A_FULL_CROSS_SECTION.parquet"
FEATURE_SCHEMA = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json"
MODEL_B = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_training_20260916/training_output_v1/MODEL_B_B19R2R_LGBM_RANKER.pkl"
TRAINING_MANIFEST = MODEL_B.parent / "TRAINING_MANIFEST.json"
PROVIDER = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
PRICE_DIR = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260916_20260916T103002Z/same_run_handoff_artifacts/daily_price"
ORTH_DIR = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260916_20260916T144502Z/same_run_handoff_artifacts"
PRICE_JSON = PRICE_DIR / "daily_price.normalized.json"
INSTITUTIONAL_JSON = ORTH_DIR / "institutional/institutional.normalized.json"
MARGIN_JSON = ORTH_DIR / "margin/margin.normalized.json"
PRICE_ADAPTER = PRICE_DIR / "daily_price.adapter_output.json"
INSTITUTIONAL_ADAPTER = ORTH_DIR / "institutional/institutional.adapter_output.json"
MARGIN_ADAPTER = ORTH_DIR / "margin/margin.adapter_output.json"
TWII_ADAPTER = PRICE_DIR / "twii.adapter_output.json"
TWII_NORMALIZED = PRICE_DIR / "twii.normalized.json"
TWII_HISTORY = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b01_feature_input_contract_repair_20260913/twii_acquisition/TWII_NORMALIZED.csv"
TWII_RECENT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b8_prospective_shadow_20260914/source_run_20260914_natural/yahoo_twii_20260914/twii.csv"
PROTECTED = (
    ROOT / "configs/tw_modular_registry.yaml",
    ROOT / "configs/active_baseline_descriptor.yaml",
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
)
FORBIDDEN = ("label", "outcome", "future", "forward_return", "next_open", "next_close")


class MaterializationError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MaterializationError("B19V3M_E_JSON", str(path))
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")


def fingerprints() -> dict[str, str | None]:
    return {rel(path): sha256(path) if path.is_file() else None for path in PROTECTED}


def feature_order() -> list[str]:
    values = list(read_json(FEATURE_SCHEMA)["feature_order"])
    digest = hashlib.sha256(json.dumps(values, separators=(",", ":")).encode()).hexdigest()
    if len(values) != 78 or digest != FEATURE_ORDER_SHA:
        raise MaterializationError("B19V3M_E_FEATURE_ORDER", digest)
    return values


def parse_time(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise MaterializationError("B19V3M_E_TIMEZONE", str(value))
    return parsed.astimezone(timezone.utc)


def normalize_symbol(value: Any) -> str:
    symbol = str(value).strip().upper()
    return symbol if symbol.startswith("TW") else f"TW{symbol}"


def load_records(path: Path) -> pd.DataFrame:
    records = read_json(path).get("records", [])
    if not isinstance(records, list) or not records:
        raise MaterializationError("B19V3M_E_NORMALIZED_RECORDS", str(path))
    frame = pd.DataFrame(records)
    blocked = forbidden_columns(frame.columns.astype(str).tolist())
    if blocked:
        raise MaterializationError("B19V3M_E_FUTURE_FIELD", f"{path}:{','.join(blocked)}")
    required = {"trade_date", "symbol"}
    if not required.issubset(frame.columns):
        raise MaterializationError("B19V3M_E_NORMALIZED_SCHEMA", str(path))
    frame["date"] = frame["trade_date"].astype(str).str[:10]
    frame["instrument"] = frame["symbol"].map(normalize_symbol)
    return frame


def forbidden_columns(columns: list[str]) -> list[str]:
    return sorted(column for column in columns if any(token in column.lower() for token in FORBIDDEN))


def validate_adapter(path: Path, *, allow_blocked: bool = False) -> dict[str, Any]:
    value = read_json(path)
    if value.get("acquisition_run_id") != SOURCE_RUN or value.get("target_asof") != ASOF:
        raise MaterializationError("B19V3M_E_CROSS_RUN", str(path))
    if parse_time(value.get("available_at")) > parse_time(CUTOFF):
        raise MaterializationError("B19V3M_E_AFTER_CUTOFF", str(path))
    if not allow_blocked and (value.get("pit_status") != "PASS" or value.get("validator_status") != "PASS"):
        raise MaterializationError("B19V3M_E_PIT", str(path))
    return value


def prediction_availability(path: Path) -> tuple[str, dict[str, str]]:
    artifact_manifest = path.parent / "artifact_manifest.json"
    metadata_path = path.parent / "run_metadata.json"
    artifact = read_json(artifact_manifest)
    metadata = read_json(metadata_path)
    entry = next(
        (item for item in artifact.get("entries", []) if isinstance(item, dict) and item.get("key") == "prediction"),
        None,
    )
    available_at = metadata.get("created_at")
    parts = path.parent.name.split("_")
    encoded_day = parts[4] if len(parts) > 5 else ""
    expected_day = f"{encoded_day[:4]}-{encoded_day[4:6]}-{encoded_day[6:8]}" if len(encoded_day) == 8 else ""
    if (
        artifact.get("status") != "accepted"
        or metadata.get("status") != "accepted"
        or artifact.get("run_id") != metadata.get("run_id")
        or metadata.get("asof") != expected_day
        or not isinstance(entry, dict)
        or entry.get("sha256") != sha256(path)
        or artifact.get("created_at") != available_at
        or parse_time(available_at) > parse_time(CUTOFF)
    ):
        raise MaterializationError("B19V3M_E_PREDICTION_AVAILABILITY", str(path))
    return str(available_at), {
        "availability_metadata": rel(metadata_path),
        "availability_metadata_sha256": sha256(metadata_path),
        "artifact_manifest": rel(artifact_manifest),
        "artifact_manifest_sha256": sha256(artifact_manifest),
    }


def require_exact_keys(expected: pd.DataFrame, actual: pd.DataFrame, keys: list[str], label: str) -> None:
    expected_keys = expected[keys].drop_duplicates()
    actual_keys = actual[keys]
    if actual_keys.duplicated().any() or len(actual_keys) != len(expected_keys):
        raise MaterializationError("B19V3M_E_KEY_MISMATCH", label)
    expected_rows = set(map(tuple, expected_keys.itertuples(index=False, name=None)))
    actual_rows = set(map(tuple, actual_keys.itertuples(index=False, name=None)))
    if actual_rows != expected_rows:
        raise MaterializationError("B19V3M_E_KEY_MISMATCH", label)


def positive_streak(values: pd.Series) -> pd.Series:
    output: list[float] = []
    count = 0
    for value in values.fillna(0).astype(int):
        count = count + 1 if value else 0
        output.append(float(count))
    return pd.Series(output, index=values.index, dtype=float)


def signed_streak(values: pd.Series) -> pd.Series:
    output: list[float] = []
    sign = count = 0
    for value in values:
        current = 0 if pd.isna(value) or value == 0 else (1 if value > 0 else -1)
        if current == 0:
            sign = count = 0
        elif current == sign:
            count += 1
        else:
            sign, count = current, 1
        output.append(float(sign * count))
    return pd.Series(output, index=values.index, dtype=float)


def rsi14(close: pd.Series) -> tuple[pd.Series, pd.Series]:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    ready = delta.rolling(14, min_periods=14).count().eq(14) & close.notna()
    value = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    return value.mask(ready & loss.eq(0), 50.0).where(ready), ready


def model_a_exact50() -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest = read_json(MODEL_A_MANIFEST)
    if (
        manifest.get("asof") != ASOF
        or manifest.get("model_id") != MODEL_A_ID
        or manifest.get("source_acquisition_run_id") != SOURCE_RUN
        or manifest.get("decision_cutoff") != CUTOFF
        or parse_time(CUTOFF) < parse_time(FINAL_MODEL_FROZEN_AT)
    ):
        raise MaterializationError("B19V3M_E_MODELA_BINDING")
    available_at, availability_evidence = prediction_availability(MODEL_A_PRE_CUTOFF_PREDICTION)
    raw = pd.read_csv(MODEL_A_PRE_CUTOFF_PREDICTION)
    if forbidden_columns(raw.columns.astype(str).tolist()):
        raise MaterializationError("B19V3M_E_FUTURE_FIELD", "model_a")
    required = {"datetime", "instrument", "score"}
    if not required.issubset(raw.columns):
        raise MaterializationError("B19V3M_E_MODELA_SCHEMA")
    raw["date"] = raw.datetime.astype(str).str[:10]
    raw["instrument"] = raw.instrument.map(normalize_symbol)
    raw["raw_score"] = pd.to_numeric(raw.score, errors="coerce")
    raw = raw.sort_values(["raw_score", "instrument"], ascending=[False, True], kind="mergesort")
    raw["full_qlib_rank"] = np.arange(1, len(raw) + 1)
    raw = raw.sort_values(["full_qlib_rank", "instrument"], kind="mergesort")
    if (
        len(raw) != 150
        or set(raw.date) != {ASOF}
        or raw.instrument.duplicated().any()
        or raw.full_qlib_rank.tolist() != list(range(1, 151))
        or not np.isfinite(raw.raw_score.to_numpy(float)).all()
    ):
        raise MaterializationError("B19V3M_E_MODELA_SCOPE")
    exact = raw.head(50).copy()
    if set(exact.instrument) & EXCLUDED:
        raise MaterializationError("B19V3M_E_EXCLUDED_IN_TOP50", repr(sorted(set(exact.instrument) & EXCLUDED)))
    official = pd.read_csv(MODEL_A_SIGNALS)
    official["instrument"] = official.instrument.map(normalize_symbol)
    official = official.sort_values("instrument").reset_index(drop=True)
    pre_cutoff = raw.sort_values("instrument").reset_index(drop=True)
    if (
        len(official) != len(pre_cutoff)
        or official.instrument.tolist() != pre_cutoff.instrument.tolist()
        or not np.array_equal(official.raw_score.to_numpy(), pre_cutoff.raw_score.to_numpy())
        or not np.array_equal(official.full_qlib_rank.to_numpy(), pre_cutoff.full_qlib_rank.to_numpy())
        or sha256(MODEL_A_PRE_CUTOFF_PREDICTION)
        != sha256((ROOT / manifest["source_artifact"]) if (ROOT / manifest["source_artifact"]).is_file() else (ROOT / "qlib_pipeline" / manifest["source_artifact"]))
    ):
        raise MaterializationError("B19V3M_E_MODELA_PRE_CUTOFF_PARITY")
    exact = exact[["date", "instrument", "full_qlib_rank", "raw_score"]].rename(
        columns={"full_qlib_rank": "rank", "raw_score": "model_a_score"}
    )
    return exact, {"formal_manifest": manifest, "available_at": available_at, **availability_evidence}


def prediction_history() -> tuple[pd.DataFrame, list[dict[str, str]]]:
    historical = pd.read_parquet(MODEL_A_HISTORY, columns=["date", "instrument", "model_a_raw_score", "full_qlib_rank"])
    historical["date"] = historical.date.astype(str).str[:10]
    days = ["2026-09-02", "2026-09-03", "2026-09-04", "2026-09-07", "2026-09-08", "2026-09-09", "2026-09-10", "2026-09-11", "2026-09-14", "2026-09-15", ASOF]
    added: list[pd.DataFrame] = []
    lineage: list[dict[str, str]] = []
    root = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal"
    for day in days:
        candidates: list[tuple[Path, pd.DataFrame]] = []
        for path in sorted(root.glob(f"option_c_daily_signal_{day.replace('-', '')}_*/prediction.csv")):
            if day == ASOF and path != MODEL_A_PRE_CUTOFF_PREDICTION:
                continue
            try:
                available_at, availability_evidence = prediction_availability(path)
            except MaterializationError as exc:
                if exc.code == "B19V3M_E_PREDICTION_AVAILABILITY":
                    continue
                raise
            frame = pd.read_csv(path)
            if forbidden_columns(frame.columns.astype(str).tolist()):
                raise MaterializationError("B19V3M_E_FUTURE_FIELD", str(path))
            frame["date"] = frame.datetime.astype(str).str[:10]
            frame["instrument"] = frame.instrument.map(normalize_symbol)
            if len(frame) == 150 and set(frame.date) == {day} and not frame.instrument.duplicated().any():
                candidate = frame[["date", "instrument", "score"]].sort_values("instrument").reset_index(drop=True)
                candidate.attrs.update(available_at=available_at, **availability_evidence)
                candidates.append((path, candidate))
        for path in sorted(MODEL_A_SIGNAL_ROOT.glob(f"*{day.replace('-', '')}*/signals.csv")):
            if day == ASOF:
                continue
            manifest_path = path.parent / "manifest.json"
            if not manifest_path.is_file():
                continue
            manifest = read_json(manifest_path)
            if (
                manifest.get("model_id") != MODEL_A_ID
                or manifest.get("asof") != day
                or manifest.get("status") != "READY"
                or manifest.get("row_count") != 150
            ):
                continue
            try:
                created_at = manifest.get("created_at")
                if parse_time(created_at) > parse_time(CUTOFF):
                    continue
            except (MaterializationError, TypeError):
                continue
            frame = pd.read_csv(path)
            if forbidden_columns(frame.columns.astype(str).tolist()):
                raise MaterializationError("B19V3M_E_FUTURE_FIELD", str(path))
            frame["date"] = frame.date.astype(str).str[:10]
            frame["instrument"] = frame.instrument.map(normalize_symbol)
            if len(frame) == 150 and set(frame.date) == {day} and not frame.instrument.duplicated().any():
                candidate = frame[["date", "instrument", "raw_score"]].rename(columns={"raw_score": "score"})
                candidate = candidate.sort_values("instrument").reset_index(drop=True)
                candidate.attrs.update(
                    available_at=str(created_at),
                    availability_metadata=rel(manifest_path),
                    availability_metadata_sha256=sha256(manifest_path),
                )
                candidates.append((path, candidate))
        if not candidates:
            raise MaterializationError("B19V3M_E_MODELA_HISTORY", day)
        reference = candidates[0][1]
        if any(
            reference.instrument.tolist() != item.instrument.tolist()
            or not np.array_equal(reference.score.to_numpy(), item.score.to_numpy())
            for _, item in candidates[1:]
        ):
            raise MaterializationError("B19V3M_E_MODELA_HISTORY_DRIFT", day)
        lineage.extend(
            {
                "date": day,
                "path": rel(path),
                "sha256": sha256(path),
                "available_at": str(item.attrs["available_at"]),
                "availability_metadata": str(item.attrs["availability_metadata"]),
                "availability_metadata_sha256": str(item.attrs["availability_metadata_sha256"]),
            }
            for path, item in candidates
        )
        frame = reference.rename(columns={"score": "model_a_raw_score"})
        frame = frame.sort_values(["model_a_raw_score", "instrument"], ascending=[False, True], kind="mergesort")
        frame["full_qlib_rank"] = np.arange(1, 151)
        added.append(frame)
    return pd.concat([historical, *added], ignore_index=True), lineage


def score_features() -> tuple[pd.DataFrame, list[dict[str, str]]]:
    history, lineage = prediction_history()
    scores = history.sort_values(["instrument", "date"], kind="mergesort")
    scores["qlib_score_raw"] = scores.model_a_raw_score.astype(float)
    scores["qlib_rank"] = scores.full_qlib_rank.astype(float)
    group = scores.groupby("date", sort=False).qlib_score_raw
    scores["qlib_score_percentile_by_date"] = group.rank(pct=True, method="average", ascending=True)
    std = group.transform(lambda values: values.std(ddof=1))
    scores["qlib_score_zscore_by_date"] = (scores.qlib_score_raw - group.transform("mean")) / std.replace(0, np.nan)
    for lag in (1, 3, 5):
        scores[f"rank_change_{lag}d"] = scores.groupby("instrument").qlib_rank.diff(lag)
    for threshold in (10, 30, 50):
        scores[f"top{threshold}_flag"] = scores.qlib_rank.le(threshold).astype(float)
    scores["top30_streak"] = scores.groupby("instrument", group_keys=False).top30_flag.apply(positive_streak)
    scores["top50_streak"] = scores.groupby("instrument", group_keys=False).top50_flag.apply(positive_streak)
    return scores[scores.date.eq(ASOF)].copy(), lineage


def decode_field(symbol: str, field: str, calendar: list[str]) -> np.ndarray:
    path = PROVIDER / "features" / symbol.lower() / f"{field}.day.bin"
    values = np.fromfile(path, dtype="<f4")
    start = int(values[0])
    expanded = np.full(len(calendar), np.nan)
    expanded[start:start + len(values) - 1] = values[1:]
    return expanded


def price_and_breadth() -> tuple[pd.DataFrame, float, bool]:
    records = load_records(PRICE_JSON)
    actual_dates = sorted(set(records.date[records.date <= ASOF]))
    source_calendar = [line.strip() for line in (PROVIDER / "calendars/day.txt").read_text().splitlines() if line.strip()]
    symbols = sorted(path.name.upper() for path in (PROVIDER / "features").iterdir() if path.is_dir())
    frames: list[pd.DataFrame] = []
    for symbol in symbols:
        decoded = {field: decode_field(symbol, field, source_calendar) for field in ("open", "high", "low", "close", "volume", "vwap")}
        raw = pd.DataFrame({"date": source_calendar, "instrument": symbol, **decoded})
        raw = raw[raw.date.isin(actual_dates)].sort_values("date").reset_index(drop=True)
        close, volume = raw.close, raw.volume
        for window in (5, 10, 20, 60):
            raw[f"MA{window}"] = close.rolling(window, min_periods=window).mean()
        raw["RSI14"], raw["_rsi_ready"] = rsi14(close)
        raw["MACD"] = close.ewm(span=12, adjust=False, min_periods=12).mean() - close.ewm(span=26, adjust=False, min_periods=26).mean()
        raw["Bollinger_position"] = ((close - raw.MA20) / (2 * close.rolling(20, min_periods=20).std(ddof=1).replace(0, np.nan))).clip(-5, 5)
        daily_return = close.pct_change(fill_method=None)
        raw["ret20"] = close.pct_change(20, fill_method=None)
        raw["volatility20"] = daily_return.rolling(20, min_periods=20).std(ddof=1)
        raw["volume_ratio20"] = volume / volume.rolling(20, min_periods=20).mean().replace(0, np.nan)
        value = volume * raw.vwap
        raw["avg_trading_value_20d"] = value.rolling(20, min_periods=20).mean()
        raw["volume_stability20"] = 1 / (1 + volume.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).rolling(20, min_periods=20).std(ddof=1))
        raw["missing_rate20"] = close.isna().astype(float).rolling(20, min_periods=1).mean()
        raw["suspension_proxy"] = (raw[["open", "high", "low", "close", "volume"]].isna().any(axis=1) | volume.le(0)).astype(float)
        raw["slippage_proxy"] = 1 / np.sqrt(value.where(value > 0))
        raw["_breadth_above"] = (close.notna() & raw.MA20.notna() & close.gt(raw.MA20)).astype(float)
        frames.append(raw[raw.date.eq(ASOF)])
    grid = pd.concat(frames, ignore_index=True)
    columns = ["MA5", "MA10", "MA20", "MA60", "RSI14", "MACD", "Bollinger_position", "ret20", "volatility20", "volume_ratio20", "avg_trading_value_20d", "volume_stability20", "missing_rate20", "suspension_proxy", "slippage_proxy", "_rsi_ready"]
    breadth = float(grid._breadth_above.mean())
    return grid[["date", "instrument", *columns]], breadth, "2026-07-10" not in actual_dates


def orthogonal_features() -> pd.DataFrame:
    price_dates = sorted(load_records(PRICE_JSON).date.unique())
    prior = price_dates[price_dates.index(ASOF) - 1]
    institutional = load_records(INSTITUTIONAL_JSON).sort_values(["instrument", "date"])
    for column in ("foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"):
        institutional[column] = pd.to_numeric(institutional[column], errors="coerce")
    institutional["institutional_total_net_buy"] = institutional[["foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"]].sum(axis=1, min_count=3)
    for column in ("foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy", "institutional_total_net_buy"):
        for window in (1, 3, 5, 10):
            institutional[f"{column}_roll{window}"] = institutional.groupby("instrument")[column].transform(lambda values: values.rolling(window, min_periods=1).sum())
    institutional["institutional_total_net_buy_streak"] = institutional.groupby("instrument", group_keys=False)["institutional_total_net_buy"].apply(signed_streak)
    institutional["institutional_missing_flag"] = institutional[["foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"]].isna().any(axis=1).astype(float)
    institutional["institutional_delay_flag"] = 0.0
    institutional["institutional_flow_delay_days"] = 0.0
    institutional["institutional_flow_asof_missing_flag"] = 0.0
    margin = load_records(MARGIN_JSON).sort_values(["instrument", "date"])
    margin["margin_balance"] = pd.to_numeric(margin.margin_purchase_today_balance, errors="coerce")
    margin["margin_balance_change"] = margin.margin_balance - pd.to_numeric(margin.margin_purchase_yesterday_balance, errors="coerce")
    margin["short_balance"] = pd.to_numeric(margin.short_sale_today_balance, errors="coerce")
    margin["short_balance_change"] = margin.short_balance - pd.to_numeric(margin.short_sale_yesterday_balance, errors="coerce")
    for column in ("margin_balance_change", "short_balance_change"):
        for window in (1, 3, 5, 10):
            margin[f"{column}_roll{window}"] = margin.groupby("instrument")[column].transform(lambda values: values.rolling(window, min_periods=1).sum())
    margin["margin_direction_proxy"] = np.sign(margin.margin_balance_change)
    margin["short_direction_proxy"] = np.sign(margin.short_balance_change)
    margin["margin_short_divergence_proxy"] = margin.margin_direction_proxy - margin.short_direction_proxy
    margin["margin_short_missing_flag"] = margin[["margin_balance", "margin_balance_change", "short_balance", "short_balance_change"]].isna().any(axis=1).astype(float)
    margin["margin_short_delay_flag"] = 0.0
    margin["margin_short_delay_days"] = 0.0
    margin["margin_short_asof_missing_flag"] = 0.0
    features = feature_order()
    inst_columns = [item for item in features if item.startswith(("foreign_", "investment_trust_", "dealer_", "institutional_"))]
    margin_columns = [item for item in features if item.startswith(("margin_", "short_"))]
    left = institutional[institutional.date.eq(prior)][["instrument", *inst_columns]]
    right = margin[margin.date.eq(prior)][["instrument", *margin_columns]]
    return left.merge(right, on="instrument", how="outer", validate="one_to_one")


def twii_features() -> tuple[dict[str, float], dict[str, Any]]:
    adapter = validate_adapter(TWII_ADAPTER, allow_blocked=True)
    normalized = read_json(TWII_NORMALIZED).get("records", [])
    target_rows = [row for row in normalized if str(row.get("日期")) == "1150916" and row.get("指數") == "發行量加權股價指數"]
    evidence = {
        "adapter_pit_status": adapter.get("pit_status"),
        "adapter_validator_status": adapter.get("validator_status"),
        "adapter_trade_date": adapter.get("trade_date"),
        "target_weighted_index_rows": len(target_rows),
        "normalized_sha256": sha256(TWII_NORMALIZED),
    }
    names = ["TWII_ret20", "TWII_ret60", "TWII_close_vs_MA60", "TWII_close_vs_MA120", "market_volatility20", "market_drawdown60"]
    if adapter.get("pit_status") != "PASS" or adapter.get("validator_status") != "PASS" or len(target_rows) != 1:
        return {name: math.nan for name in names}, evidence
    old = pd.read_csv(TWII_HISTORY, usecols=["date", "close"])
    recent = pd.read_csv(TWII_RECENT, usecols=["date", "close"])
    current = pd.DataFrame([{"date": ASOF, "close": float(target_rows[0]["收盤指數"])}])
    twii = pd.concat([old, recent, current], ignore_index=True).drop_duplicates("date", keep="last").sort_values("date")
    close = pd.to_numeric(twii.close, errors="coerce")
    result = {
        "TWII_ret20": close.pct_change(20, fill_method=None).iloc[-1],
        "TWII_ret60": close.pct_change(60, fill_method=None).iloc[-1],
        "TWII_close_vs_MA60": close.iloc[-1] / close.rolling(60, min_periods=60).mean().iloc[-1] - 1,
        "TWII_close_vs_MA120": close.iloc[-1] / close.rolling(120, min_periods=120).mean().iloc[-1] - 1,
        "market_volatility20": close.pct_change(fill_method=None).rolling(20, min_periods=20).std(ddof=1).iloc[-1],
        "market_drawdown60": close.iloc[-1] / close.rolling(60, min_periods=20).max().iloc[-1] - 1,
    }
    return {key: float(value) for key, value in result.items()}, evidence


def assemble_features(exact: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    score, score_lineage = score_features()
    price, breadth, placeholder_removed = price_and_breadth()
    orthogonal = orthogonal_features()
    twii, twii_evidence = twii_features()
    expected = exact[["date", "instrument"]]
    score = score.merge(expected, on=["date", "instrument"], how="inner", validate="one_to_one")
    price = price.merge(expected, on=["date", "instrument"], how="inner", validate="one_to_one")
    orthogonal = orthogonal.merge(expected[["instrument"]], on="instrument", how="inner", validate="one_to_one")
    require_exact_keys(expected, score, ["date", "instrument"], "model_a_score_history")
    require_exact_keys(expected, price, ["date", "instrument"], "price_features")
    require_exact_keys(expected[["instrument"]], orthogonal, ["instrument"], "orthogonal_features")
    base = expected.merge(score, on=["date", "instrument"], validate="one_to_one")
    base = base.merge(price, on=["date", "instrument"], validate="one_to_one")
    base = base.merge(orthogonal, on="instrument", validate="one_to_one")
    base["market_breadth20"] = breadth
    for name, value in twii.items():
        base[name] = value
    order = feature_order()
    numeric = base[order].apply(pd.to_numeric, errors="coerce")
    finite = np.isfinite(numeric.to_numpy(float))
    base[order] = numeric
    base["rsi_ready"] = base["_rsi_ready"].fillna(False).astype(bool)
    base["feature_raw_complete_78"] = finite.all(axis=1) & base.rsi_ready
    base["raw_missing_features"] = ["|".join(np.asarray(order)[~row]) for row in finite]
    audit = {
        "rows": len(base),
        "finite_78_rows": int(finite.all(axis=1).sum()),
        "rsi_ready_rows": int(base.rsi_ready.sum()),
        "complete_78_rows": int(base.feature_raw_complete_78.sum()),
        "missing_feature_counts": {name: int((~np.isfinite(numeric[name].to_numpy(float))).sum()) for name in order},
        "nontrading_placeholder_removed_before_rolling": placeholder_removed,
        "twii": twii_evidence,
        "model_a_history_sources": score_lineage,
    }
    return base[["date", "instrument", *order, "rsi_ready", "feature_raw_complete_78", "raw_missing_features"]], audit


def model_identity() -> tuple[Any, list[str]]:
    if sha256(MODEL_B) != MODEL_B_SHA:
        raise MaterializationError("B19V3M_E_MODEL_HASH")
    manifest = read_json(TRAINING_MANIFEST)
    if manifest.get("model_id") != MODEL_B_ID or manifest.get("selected_candidate_id") != 14 or manifest.get("feature_count") != 78:
        raise MaterializationError("B19V3M_E_MODEL_IDENTITY")
    model = joblib.load(MODEL_B)
    order = list(model.booster_.feature_name())
    if order != feature_order():
        raise MaterializationError("B19V3M_E_MODEL_FEATURE_ORDER")
    return model, order


def materialize(out: Path) -> dict[str, Any]:
    if not out.resolve().is_relative_to(OUT_ROOT.resolve()):
        raise MaterializationError("B19V3M_E_OUTPUT_ESCAPE", str(out))
    if out.exists() and any(out.iterdir()):
        raise MaterializationError("B19V3M_E_NO_OVERWRITE", str(out))
    if parse_time(CUTOFF) < parse_time(FINAL_MODEL_FROZEN_AT):
        raise MaterializationError("B19V3M_E_BEFORE_FINAL_MODEL_FREEZE")
    before = fingerprints()
    adapters = {
        "daily_price": validate_adapter(PRICE_ADAPTER),
        "institutional": validate_adapter(INSTITUTIONAL_ADAPTER),
        "margin": validate_adapter(MARGIN_ADAPTER),
        "twii": validate_adapter(TWII_ADAPTER, allow_blocked=True),
    }
    exact, model_a_binding = model_a_exact50()
    model, order = model_identity()
    features, feature_audit = assemble_features(exact)
    all_complete = bool(features.feature_raw_complete_78.all())
    score_output: pd.DataFrame | None = None
    if all_complete:
        scores = np.asarray(model.predict(features[order]), dtype=float)
        if not np.isfinite(scores).all():
            raise MaterializationError("B19V3M_E_SCORE_NONFINITE")
        score_output = exact[["date", "instrument"]].copy()
        score_output["model_b_score"] = scores
        score_output = score_output.sort_values(
            ["model_b_score", "instrument"], ascending=[False, True], kind="mergesort"
        ).reset_index(drop=True)
        score_output["rank"] = np.arange(1, 51)

    out.mkdir(parents=True, exist_ok=True)
    exact_path = out / "MODEL_A_EXACT50.csv"
    exact.to_csv(exact_path, index=False)
    exact_manifest = {
        "schema_version": "modelb_b19r2r.v3.model_a_exact50.v1", "asof": ASOF, "model_id": MODEL_A_ID,
        "source_run_id": SOURCE_RUN, "decision_cutoff": CUTOFF, "available_at": model_a_binding["available_at"], "pit_status": "PIT_SAFE",
        "artifact_sha256": sha256(exact_path), "row_count": 50, "excluded_symbol": "TW7769",
        "excluded_symbol_present": False, "selection_semantics": "model_a_rank_1_through_50_no_substitution",
        "source_artifact": rel(MODEL_A_PRE_CUTOFF_PREDICTION),
        "source_artifact_sha256": sha256(MODEL_A_PRE_CUTOFF_PREDICTION),
        "formal_model_a_artifact": rel(MODEL_A_SIGNALS),
        "formal_model_a_artifact_sha256": sha256(MODEL_A_SIGNALS),
        "availability_metadata": model_a_binding["availability_metadata"],
        "availability_metadata_sha256": model_a_binding["availability_metadata_sha256"],
        "production_allowed": False,
    }
    write_json(out / "MODEL_A_EXACT50_MANIFEST.json", exact_manifest)
    candidate_path = out / "FEATURES_78_CANDIDATE.csv"
    features.to_csv(candidate_path, index=False)
    feature_manifest = {
        "schema_version": "modelb_b19r2r.v3.feature_candidate.v1", "asof": ASOF, "source_run_id": SOURCE_RUN,
        "decision_cutoff": CUTOFF, "available_at": max(value["available_at"] for key, value in adapters.items() if key != "twii"),
        "pit_status": "PASS" if all_complete else "BLOCKED_TWII_SOURCE", "artifact_sha256": sha256(candidate_path),
        "feature_columns": feature_order(), "feature_order_sha256": FEATURE_ORDER_SHA, "feature_count": 78,
        "all_finite": all_complete, "rsi_ready": bool(features.rsi_ready.all()), "audit": feature_audit,
        "no_fill_or_imputation": True, "canonical_78f_emitted": all_complete, "production_allowed": False,
    }
    write_json(out / "FEATURES_78_CANDIDATE_MANIFEST.json", feature_manifest)
    score_emitted = score_output is not None
    if score_output is not None:
        score_output[["date", "instrument", "rank", "model_b_score"]].to_csv(
            out / "CANDIDATE14_MODEL_B_SCORES.csv", index=False
        )
    after = fingerprints()
    blockers = [] if all_complete else ["TWII_2026_09_16_PIT_AND_SCHEMA_NOT_PROVEN", "SIX_TWII_FEATURES_NONFINITE", "CANDIDATE14_SCORING_FORBIDDEN_ON_INCOMPLETE_78F"]
    bundle = {
        "schema_version": "modelb_b19r2r.v3.materialization_attempt.v1", "created_at": utc_now(), "asof": ASOF,
        "status": "PASS_READY_FOR_PRECAPTURE_REVIEW" if all_complete else "NOT_ELIGIBLE_BLOCKED_TWII",
        "eligible_for_capture": all_complete and score_emitted, "accepted_ledger_event_written": False,
        "source_run_id": SOURCE_RUN, "decision_cutoff": CUTOFF, "final_model_frozen_at": FINAL_MODEL_FROZEN_AT,
        "model_a_id": MODEL_A_ID, "model_id": MODEL_B_ID, "model_sha256": MODEL_B_SHA, "candidate_id": 14,
        "feature_count": 78, "feature_order_sha256": FEATURE_ORDER_SHA, "tw7769_excluded": True,
        "exact50_artifact": rel(exact_path), "feature_candidate_artifact": rel(candidate_path),
        "canonical_78f_artifact": rel(candidate_path) if all_complete else None,
        "candidate14_score_artifact": rel(out / "CANDIDATE14_MODEL_B_SCORES.csv") if score_emitted else None,
        "artifact_hashes": {
            "model_a_exact50": sha256(exact_path),
            "feature_candidate": sha256(candidate_path),
            "candidate14_scores": sha256(out / "CANDIDATE14_MODEL_B_SCORES.csv") if score_emitted else None,
        },
        "blockers": blockers, "adapters": {key: {field: value.get(field) for field in ("acquisition_run_id", "available_at", "pit_status", "validator_status", "trade_date")} for key, value in adapters.items()},
        "future_or_outcome_fields_consumed": [], "training_performed": False, "tuning_performed": False,
        "production_allowed": False, "protected_before": before, "protected_after": after, "protected_unchanged": before == after,
    }
    write_json(out / "MATERIALIZATION_ATTEMPT.json", bundle)
    return bundle


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--out", default=str(OUT_ROOT / "pre_capture_v3"))
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        result = materialize(Path(args.out))
    except MaterializationError as exc:
        print(json.dumps({"status": "FAIL", "error_code": exc.code, "detail": exc.detail}, sort_keys=True))
        return 2
    print(json.dumps({"status": result["status"], "eligible_for_capture": result["eligible_for_capture"], "blockers": result["blockers"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
