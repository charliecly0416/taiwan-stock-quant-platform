#!/usr/bin/env python3
"""Build strict prospective Model B features from explicit same-run inputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from tw_mbcds35_signal_time_regime import (
    DEFAULT_CONTRACT as REGIME_CONTRACT,
    REQUIRED_FIELDS as REGIME_FIELDS,
    RegimeContractError,
    classify as classify_regime,
    load_contract as load_regime_contract,
)

ROOT = Path(__file__).resolve().parents[1]
ISOLATED_ROOT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow"
CONTRACT = ISOLATED_ROOT / "model_artifact_phase1c_20260905/model_contract.json"
PROTECTED = [
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
]


class FeatureBuildError(RuntimeError):
    pass


def parse_rfc3339(value: Any, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise FeatureBuildError(f"source_ledger_{field}_invalid") from exc
    if parsed.tzinfo is None:
        raise FeatureBuildError(f"source_ledger_{field}_timezone_required")
    return parsed.astimezone(timezone.utc)


def resolve(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprints(paths: Iterable[Path]) -> dict[str, Any]:
    return {rel(path): {"exists": path.is_file(), "sha256": sha256(path) if path.is_file() else None} for path in paths}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def nested_records(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            yield from nested_records(item)
    elif isinstance(value, dict):
        keys = {str(key).lower() for key in value}
        if keys & {"date", "trade_date"} and keys & {"stock_id", "instrument", "symbol", "code"}:
            yield value
        for key in ("data", "records", "rows", "result", "payload"):
            if key in value:
                yield from nested_records(value[key])


def load_bound_market_data(source_ledger: Path, asof: str) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    ledger = json.loads(source_ledger.read_text(encoding="utf-8"))
    if ledger.get("status") != "PASS" or ledger.get("asof") != asof:
        raise FeatureBuildError("source_ledger_not_pass_or_asof_mismatch")
    if not str(ledger.get("acquisition_run_id") or ""):
        raise FeatureBuildError("source_ledger_acquisition_run_id_missing")
    available_at = parse_rfc3339(ledger.get("combined_available_at"), "combined_available_at")
    decision_cutoff = parse_rfc3339(ledger.get("decision_cutoff"), "decision_cutoff")
    if available_at > decision_cutoff:
        raise FeatureBuildError("source_available_at_after_decision_cutoff")
    checksums = ledger.get("artifact_checksums")
    if not isinstance(checksums, dict) or not checksums:
        raise FeatureBuildError("source_ledger_artifact_checksums_missing")
    records: list[dict[str, Any]] = []
    for name, expected in checksums.items():
        path = resolve(name)
        if not path.is_file() or sha256(path) != expected:
            raise FeatureBuildError(f"source_artifact_checksum_mismatch:{name}")
        try:
            records.extend(nested_records(json.loads(path.read_text(encoding="utf-8"))))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    rows = []
    for row in records:
        low = {str(key).lower(): value for key, value in row.items()}
        date = str(low.get("date") or low.get("trade_date") or "")[:10]
        symbol = str(low.get("stock_id") or low.get("instrument") or low.get("symbol") or low.get("code") or "").upper()
        if date and date <= asof and symbol:
            rows.append({"date": date, "instrument": symbol, "open": low.get("open"), "close": low.get("close"),
                         "volume": low.get("trading_volume", low.get("volume")), "vwap": low.get("vwap", low.get("average_price"))})
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise FeatureBuildError("bound_market_records_missing")
    for name in ("open", "close", "volume", "vwap"):
        frame[name] = pd.to_numeric(frame[name], errors="coerce")
    frame = frame.sort_values(["instrument", "date"]).drop_duplicates(["instrument", "date"], keep="last")
    market_ids = {"TWII", "TAIEX", "IX0001"}
    return frame[~frame.instrument.isin(market_ids)].copy(), frame[frame.instrument.isin(market_ids)].copy(), ledger


def load_rank_history(
    accumulator: Path,
    asof: str,
    model_a: Path,
    *,
    source_run_id: str | None = None,
    decision_cutoff: str | None = None,
) -> pd.DataFrame:
    accepted = [row for row in read_csv(accumulator) if row.get("state") == "VALID_DAY_ACCEPTED"
                and str(row.get("warmup_counted", "")).lower() in {"true", "1"} and row.get("asof", "") <= asof]
    target = [row for row in accepted if row.get("asof") == asof]
    if len(target) != 1 or resolve(target[0].get("ranking_path", "")).resolve() != model_a.resolve():
        raise FeatureBuildError("target_model_a_not_bound_to_accepted_accumulator")
    if source_run_id is not None and target[0].get("source_run_id") != source_run_id:
        raise FeatureBuildError("target_source_run_not_bound_to_source_ledger")
    if decision_cutoff is not None:
        target_cutoff = parse_rfc3339(target[0].get("decision_cutoff"), "target_decision_cutoff")
        if target_cutoff != parse_rfc3339(decision_cutoff, "decision_cutoff"):
            raise FeatureBuildError("target_decision_cutoff_not_bound_to_source_ledger")
    frames = []
    for row in accepted:
        path = resolve(row.get("ranking_path", ""))
        if not path.is_file():
            raise FeatureBuildError(f"accepted_ranking_missing:{row.get('asof')}")
        part = pd.read_csv(path)
        part["date"] = part.get("date", part.get("asof", row["asof"])).astype(str).str[:10]
        part["instrument"] = part["instrument"].astype(str).str.upper()
        rank = next((name for name in ("full_qlib_rank", "score_rank", "rank") if name in part), None)
        score = next((name for name in ("raw_score", "score", "buy_score") if name in part), None)
        if rank is None or score is None or set(part.date) != {row["asof"]} or len(part) != 150:
            raise FeatureBuildError(f"accepted_ranking_invalid:{row.get('asof')}")
        frames.append(part[["date", "instrument", rank, score]].rename(columns={rank: "qlib_rank", score: "qlib_score_raw"}))
    history = pd.concat(frames, ignore_index=True)
    if history.duplicated(["date", "instrument"]).any():
        raise FeatureBuildError("accepted_rank_history_duplicate")
    return history.sort_values(["instrument", "date"])


def rsi(close: pd.Series) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    # Preserve the frozen training builder's exact transform, including its
    # neutral value for warm-up and zero-loss windows.
    return (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50.0)


def build(
    *, asof: str, model_a: Path, source_ledger: Path, accumulator: Path,
    output: Path, contract: Path = CONTRACT, regime_contract: Path = REGIME_CONTRACT,
) -> dict[str, Any]:
    if not output.resolve().is_relative_to(ISOLATED_ROOT.resolve()):
        raise FeatureBuildError("output_outside_isolated_root")
    before = fingerprints(PROTECTED)
    features = json.loads(contract.read_text(encoding="utf-8")).get("features")
    if not isinstance(features, list) or len(features) != 34 or len(set(features)) != 34:
        raise FeatureBuildError("feature_contract_not_exact_34")
    prices, twii, ledger = load_bound_market_data(source_ledger, asof)
    ranks = load_rank_history(
        accumulator,
        asof,
        model_a,
        source_run_id=str(ledger["acquisition_run_id"]),
        decision_cutoff=str(ledger["decision_cutoff"]),
    )

    groups = ranks.groupby("date", sort=False)
    ranks["qlib_score_percentile_by_date"] = groups.qlib_score_raw.rank(pct=True, method="average", ascending=True)
    ranks["qlib_score_zscore_by_date"] = (ranks.qlib_score_raw - groups.qlib_score_raw.transform("mean")) / groups.qlib_score_raw.transform("std").replace(0, np.nan)
    for count in (10, 30, 50):
        ranks[f"top{count}_flag"] = (ranks.qlib_rank <= count).astype(float)
    for lag in (1, 3, 5):
        ranks[f"rank_change_{lag}d"] = ranks.groupby("instrument").qlib_rank.diff(lag)
    for flag, name in (("top30_flag", "top30_streak"), ("top50_flag", "top50_streak")):
        ranks[name] = ranks.groupby("instrument")[flag].transform(
            lambda values: values.groupby((values == 0).cumsum()).cumsum()
        )

    if twii.empty:
        raise FeatureBuildError("twii_bound_records_missing")
    target_symbols = sorted(ranks.loc[ranks.date == asof, "instrument"].unique())
    market_dates = sorted(twii.date.unique())
    complete_index = pd.MultiIndex.from_product([target_symbols, market_dates], names=["instrument", "date"])
    prices = prices.set_index(["instrument", "date"]).reindex(complete_index).reset_index().sort_values(["instrument", "date"])
    by = prices.groupby("instrument", group_keys=False)
    for window in (5, 10, 20, 60):
        prices[f"MA{window}"] = by.close.transform(lambda values: values.rolling(window, min_periods=window).mean())
    prices["RSI14"] = by.close.transform(rsi)
    prices["MACD"] = by.close.transform(lambda values: values.ewm(span=12, adjust=False, min_periods=12).mean() - values.ewm(span=26, adjust=False, min_periods=26).mean())
    ma20 = by.close.transform(lambda values: values.rolling(20, min_periods=20).mean())
    sd20 = by.close.transform(lambda values: values.rolling(20, min_periods=20).std())
    prices["Bollinger_position"] = ((prices.close - ma20) / (2 * sd20.replace(0, np.nan))).clip(-5, 5)
    prices["ret20"] = by.close.pct_change(20, fill_method=None)
    prices["volatility20"] = by.close.pct_change(fill_method=None).groupby(prices.instrument).transform(lambda values: values.rolling(20, min_periods=20).std())
    prices["volume_ratio20"] = prices.volume / by.volume.transform(lambda values: values.rolling(20, min_periods=20).mean()).replace(0, np.nan)
    value = prices.volume * prices.vwap
    prices["avg_trading_value_20d"] = value.groupby(prices.instrument).transform(lambda values: values.rolling(20, min_periods=20).mean())
    prices["volume_stability20"] = 1 / (1 + by.volume.pct_change(fill_method=None).groupby(prices.instrument).transform(lambda values: values.rolling(20, min_periods=20).std()))
    prices["missing_rate20"] = prices.close.isna().astype(float).groupby(prices.instrument).transform(lambda values: values.rolling(20, min_periods=1).mean())
    prices["suspension_proxy"] = (prices.volume.fillna(0) <= 0).astype(float)
    prices["slippage_proxy"] = 1 / np.sqrt(value.replace(0, np.nan))
    prices["_ma20"] = ma20

    twii = twii.sort_values("date").drop_duplicates("date", keep="last")
    twii["TWII_ret20"] = twii.close.pct_change(20, fill_method=None)
    twii["TWII_ret60"] = twii.close.pct_change(60, fill_method=None)
    twii["TWII_close_vs_MA60"] = twii.close / twii.close.rolling(60, min_periods=60).mean() - 1
    twii["TWII_close_vs_MA120"] = twii.close / twii.close.rolling(120, min_periods=120).mean() - 1
    twii["market_volatility20"] = twii.close.pct_change(fill_method=None).rolling(20, min_periods=20).std()
    twii["market_drawdown60"] = twii.close / twii.close.rolling(60, min_periods=20).max() - 1
    breadth = (
        prices.dropna(subset=["_ma20"])
        .assign(above=lambda frame: (frame.close > frame._ma20).astype(float))
        .groupby("date").above.mean()
    )
    twii["market_breadth20"] = twii.date.map(breadth)

    target = ranks[ranks.date == asof].merge(prices[prices.date == asof], on=["date", "instrument"], how="left").merge(twii, on="date", how="left", suffixes=("", "_twii"))
    for feature in features:
        if feature not in target:
            target[feature] = np.nan
    target = target[["date", "instrument", *features]].sort_values("instrument")
    numeric = target[features].apply(pd.to_numeric, errors="coerce")
    top50_mask = pd.to_numeric(target["qlib_rank"], errors="coerce") <= 50
    blocked = [name for name in features if not np.isfinite(numeric.loc[top50_mask, name].to_numpy(dtype=float)).all()]
    all_universe_blocked = [name for name in features if not np.isfinite(numeric[name].to_numpy(dtype=float)).all()]
    ready = len(target) == 150 and target.instrument.nunique() == 150 and int(top50_mask.sum()) == 50 and not blocked
    output.mkdir(parents=True, exist_ok=True)
    frame_path = output / "feature_frame.csv"
    target.to_csv(frame_path, index=False)
    _, regime_contract_sha256 = load_regime_contract(regime_contract)
    regime_values: dict[str, float] = {}
    for field in REGIME_FIELDS:
        values = pd.to_numeric(target[field], errors="coerce")
        finite = values[np.isfinite(values.to_numpy(dtype=float))]
        unique = finite.unique()
        if len(finite) != len(target) or len(unique) != 1:
            raise FeatureBuildError(f"signal_time_regime_cross_section_invalid:{field}")
        regime_values[field] = float(unique[0])
    try:
        regime, regime_values = classify_regime(regime_values)
    except RegimeContractError as exc:
        raise FeatureBuildError(str(exc)) from exc
    regime_path = output / "signal_time_regime.json"
    regime_payload = {
        "schema_version": "mbcds35.signal_time_regime.v1",
        "asof": asof,
        "decision_cutoff": ledger["decision_cutoff"],
        "source_available_at": ledger["combined_available_at"],
        "source_run_id": ledger["acquisition_run_id"],
        "regime": regime,
        "feature_values": regime_values,
        "regime_contract": rel(regime_contract),
        "regime_contract_sha256": regime_contract_sha256,
        "feature_frame": rel(frame_path),
        "feature_frame_sha256": sha256(frame_path),
        "signal_time_only": True,
        "outcome_fields_consumed": [],
        "missing_rule": "fail_closed_no_classification_no_fill",
        "production_allowed": False,
    }
    regime_path.write_text(json.dumps(regime_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    manifest = {"schema_version": "mbcds35.prospective_feature_frame.v1", "asof": asof,
                "source_run_id": ledger["acquisition_run_id"], "decision_cutoff": ledger["decision_cutoff"],
                "source_available_at": ledger["combined_available_at"],
                "feature_order": features, "feature_count": 34, "row_count": len(target), "feature_frame_sha256": sha256(frame_path),
                "model_a_signals": rel(model_a), "model_a_signals_sha256": sha256(model_a), "source_ledger": rel(source_ledger),
                "source_ledger_sha256": sha256(source_ledger), "accepted_rank_history_only": True, "missing_rule": "fail_closed_no_fill",
                "readiness_scope": "model_a_top50_50x34", "scorer_rows": int(top50_mask.sum()),
                "blocked_features": blocked, "all_universe_diagnostic_blocked_features": all_universe_blocked,
                "signal_time_regime": regime, "signal_time_regime_artifact": rel(regime_path),
                "signal_time_regime_artifact_sha256": sha256(regime_path),
                "signal_time_regime_contract": rel(regime_contract),
                "signal_time_regime_contract_sha256": regime_contract_sha256,
                "can_score": ready, "status": "PASS" if ready else "BLOCKED_INCOMPLETE_TOP50_FEATURES", "training_performed": False}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    after = fingerprints(PROTECTED)
    (output / "forbidden_scope_audit.json").write_text(json.dumps({"status": "PASS" if before == after else "FAIL", "protected_paths_unchanged": before == after, "publish": False, "training": False}, indent=2) + "\n", encoding="utf-8")
    if before != after:
        raise FeatureBuildError("protected_path_mutated")
    if not ready:
        raise FeatureBuildError("incomplete_features:" + ",".join(blocked))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--model-a-signals", required=True)
    parser.add_argument("--source-ledger", required=True)
    parser.add_argument("--accepted-accumulator", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        payload = build(asof=args.asof, model_a=resolve(args.model_a_signals), source_ledger=resolve(args.source_ledger), accumulator=resolve(args.accepted_accumulator), output=resolve(args.out))
    except (OSError, ValueError, json.JSONDecodeError, FeatureBuildError, RegimeContractError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=True))
        return 2
    print(json.dumps({"status": "PASS", "manifest": payload}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
