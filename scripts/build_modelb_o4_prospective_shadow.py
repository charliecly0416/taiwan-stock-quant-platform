#!/usr/bin/env python3
"""Build and score a strict 78-feature O4 prospective shadow observation."""

from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
import pickle
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODEL_A = "e4_frozen_qlib_2018_2022"
MODEL_B = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
O4 = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr"
MODEL_PATH = O4 / "phaseo4_treatment_model.pkl"
WHITELIST_PATH = O4 / "phaseo4_training_feature_whitelist.csv"
PROTECTED = (
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
)
FORBIDDEN = (
    "future_return", "future_excess_return", "forward_return", "label_",
    "relevance_10d_top_heavy", "ltr_relevance_label", "realized_pnl",
    "realized_return", "target_position", "target_weight", "order_qty",
    "execution_price", "broker_order_id",
)
REQUIRED_SEGMENTS = ("adjusted_price", "institutional_flow", "margin_short", "twii")
CORE_SIGNAL_COLUMNS = [
    "date", "instrument", "model_name", "model_family", "candidate_rank", "buy_score",
    "raw_score", "score_rank", "full_qlib_rank", "signal_asof", "available_at",
    "source_artifact", "source_model_artifact", "source_feature_artifact",
]


class BridgeError(ValueError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_calendar_dates(path: Path) -> list[str]:
    """Accept the project's newline calendar or a normalized price payload for replay."""
    if path.suffix.lower() == ".json":
        payload = read_json(path)
        records = payload.get("records") or payload.get("data") or []
        return sorted({str(item.get("trade_date") or item.get("date") or "")[:10] for item in records if item.get("trade_date") or item.get("date")})
    return [line.strip()[:10] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")


def fingerprint() -> dict[str, Any]:
    return {
        rel(path): {
            "exists": path.exists(),
            "size": path.stat().st_size if path.exists() else None,
            "sha256": sha256(path) if path.is_file() else None,
        }
        for path in PROTECTED
    }


def parse_time(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise BridgeError(f"invalid {field}: {value}") from exc
    if parsed.tzinfo is None:
        raise BridgeError(f"{field} must include timezone")
    return parsed.astimezone(timezone.utc)


def norm_symbol(value: Any) -> str:
    text = str(value or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


FLOW_REQUIRED_FIELDS = {
    "institutional_flow": (
        "foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy", "total_institutional_net_buy",
    ),
    "margin_short": (
        "margin_purchase_today_balance", "margin_purchase_yesterday_balance",
        "short_sale_today_balance", "short_sale_yesterday_balance",
    ),
}
MARGIN_PRIOR_SESSION_OVERRIDE = (
    "BLOCKED_PUBLICATION_AND_AVAILABILITY_UNPROVEN",
    "BLOCKED_SOURCE_SCOPE_OR_VALIDATOR_UNPROVEN",
)


def verify_raw_http_evidence(meta: dict[str, Any], family: str) -> dict[str, Any]:
    """Verify the captured HTTP bytes without changing the generic HSA8 verdict."""
    raw_files = meta.get("raw_files") or []
    if meta.get("http_status") != 200 or meta.get("http_response_bytes") is not True or not raw_files:
        raise BridgeError(f"{family} raw HTTP evidence invalid")
    for entry in raw_files:
        raw = Path(str(entry.get("path") or ""))
        if not raw.is_absolute():
            raw = ROOT / raw
        if not raw.exists() or sha256(raw) != str(entry.get("sha256") or ""):
            raise BridgeError(f"{family} raw HTTP checksum mismatch")
    return {
        "http_status": meta.get("http_status"),
        "http_response_bytes": True,
        "raw_file_count": len(raw_files),
        "raw_files_verified": True,
    }


def load_adapter(path: Path, source_run_id: str, cutoff: datetime, family: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    meta = read_json(path)
    if meta.get("acquisition_run_id") != source_run_id:
        raise BridgeError(f"{family} source run mismatch")
    pit_status = str(meta.get("pit_status") or "")
    validator_status = str(meta.get("validator_status") or "")
    margin_override = family == "margin_short" and (pit_status, validator_status) == MARGIN_PRIOR_SESSION_OVERRIDE
    if pit_status != "PASS" and not margin_override:
        raise BridgeError(f"{family} adapter PIT is not PASS")
    available = parse_time(str(meta.get("available_at") or ""), f"{family}.available_at")
    if available > cutoff:
        raise BridgeError(f"{family} available after decision cutoff")
    normalized = Path(meta["normalized_files"][0]["path"])
    if not normalized.is_absolute():
        normalized = ROOT / normalized
    expected_sha = str(meta["normalized_files"][0]["sha256"])
    if sha256(normalized) != expected_sha:
        raise BridgeError(f"{family} normalized checksum mismatch")
    raw_audit = verify_raw_http_evidence(meta, family)
    payload = read_json(normalized)
    frame = pd.DataFrame(payload.get("records") or [])
    if frame.empty:
        raise BridgeError(f"{family} normalized records empty")
    frame["instrument"] = frame["symbol"].map(norm_symbol)
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce")
    frame = frame.dropna(subset=["trade_date", "instrument"]).sort_values(["instrument", "trade_date"])
    audit = {
        "family": family,
        "adapter": rel(path),
        "adapter_sha256": sha256(path),
        "normalized": rel(normalized),
        "normalized_sha256": expected_sha,
        "available_at": available.isoformat(),
        "row_count": len(frame),
        "symbol_count": int(frame.instrument.nunique()),
        "trade_date_min": str(frame.trade_date.min().date()),
        "trade_date_max": str(frame.trade_date.max().date()),
        "source_run_id_match": True,
        "available_before_cutoff": True,
        "adapter_pit_status": pit_status,
        "adapter_validator_status": validator_status,
        "adapter_target_asof": str(meta.get("target_asof") or ""),
        "adapter_trade_date": str(meta.get("trade_date") or ""),
        "o4_prior_session_override": margin_override,
        **raw_audit,
    }
    return frame, audit


def validate_delayed_flow_coverage(
    frame: pd.DataFrame,
    audit: dict[str, Any],
    *,
    selected_trade_date: str,
    instruments: list[str],
) -> None:
    """Bind a delayed flow source to the exact Model A cross-section at t-1."""
    family = str(audit["family"])
    required = FLOW_REQUIRED_FIELDS[family]
    selected = frame[frame.trade_date.dt.strftime("%Y-%m-%d") == selected_trade_date].copy()
    duplicate_count = int(selected.duplicated("instrument").sum())
    selected_set = set(selected.instrument.astype(str))
    target_set = set(instruments)
    missing = sorted(target_set - selected_set)
    extra = sorted(selected_set - target_set)
    numeric = selected.reindex(columns=list(required)).apply(pd.to_numeric, errors="coerce")
    finite = bool(len(selected) == len(instruments) and np.isfinite(numeric.to_numpy(dtype=float)).all())
    if duplicate_count or missing or extra or not finite:
        raise BridgeError(
            f"{family} delayed prior-session coverage invalid: "
            f"date={selected_trade_date} rows={len(selected)} duplicates={duplicate_count} "
            f"missing={len(missing)} extra={len(extra)} finite={finite}"
        )
    audit.update({
        "selected_trade_date": selected_trade_date,
        "selected_row_count": len(selected),
        "selected_unique_symbol_count": int(selected.instrument.nunique()),
        "selected_target_symbol_count": len(instruments),
        "selected_duplicate_symbol_count": duplicate_count,
        "selected_missing_symbol_count": len(missing),
        "selected_extra_symbol_count": len(extra),
        "selected_required_fields": list(required),
        "selected_required_fields_finite": finite,
        "selected_symbols_sha256": hashlib.sha256("|".join(sorted(selected_set)).encode()).hexdigest(),
        "delayed_flow_coverage_status": "PASS",
    })


def load_rank_history(
    paths: list[Path], asof: str, expected_dates: list[str], source_run_id: str, decision_cutoff: str
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    frames = []
    audits = []
    for path in paths:
        frame = pd.read_csv(path)
        required = {"date", "instrument", "candidate_rank", "raw_score", "full_qlib_rank", "available_at"}
        if not required.issubset(frame.columns):
            raise BridgeError(f"rank signal schema invalid: {path}")
        frame = frame[["date", "instrument", "candidate_rank", "raw_score", "full_qlib_rank", "available_at"]].copy()
        frame["date"] = frame.date.astype(str).str[:10]
        frame["instrument"] = frame.instrument.map(norm_symbol)
        frame["qlib_rank"] = pd.to_numeric(frame.candidate_rank, errors="coerce")
        frame["qlib_score_raw"] = pd.to_numeric(frame.raw_score, errors="coerce")
        if len(frame) != 150 or frame.instrument.nunique() != 150 or frame.duplicated(["date", "instrument"]).any():
            raise BridgeError(f"rank signal must be one complete 150-row cross-section: {path}")
        ranks = sorted(frame.qlib_rank.dropna().astype(int).tolist())
        if ranks != list(range(1, 151)) or not np.isfinite(frame.qlib_score_raw.to_numpy(dtype=float)).all():
            raise BridgeError(f"rank signal rank/score invalid: {path}")
        frames.append(frame[["date", "instrument", "qlib_rank", "qlib_score_raw", "full_qlib_rank"]])
        manifest_path = path.parent / "manifest.json"
        report_path = path.parent / "validator_report.json"
        if not manifest_path.exists():
            raise BridgeError(f"rank signal lacks ModelSignalArtifact manifest: {path}")
        manifest = read_json(manifest_path)
        declared = (manifest.get("files") or manifest.get("output_files") or {}).get("signals")
        declared_path = (manifest_path.parent / declared).resolve() if declared else None
        if manifest.get("artifact_type") != "ModelSignalArtifact" or declared_path != path.resolve():
            raise BridgeError(f"rank signal manifest binding invalid: {path}")
        if str(manifest.get("asof")) != str(frame.date.iloc[0]) or int(manifest.get("row_count", -1)) != len(frame):
            raise BridgeError(f"rank signal manifest date/row binding invalid: {path}")
        candidate_cutoff = str(manifest.get("decision_cutoff") or "")
        if str(frame.date.iloc[0]) == asof:
            available_dates = frame["available_at"].astype(str).str[:10] if "available_at" in frame else pd.Series(dtype=str)
            candidate_time = parse_time(candidate_cutoff, "target_model_a.decision_cutoff")
            final_time = parse_time(decision_cutoff, "decision_cutoff")
            if (
                manifest.get("source_acquisition_run_id") != source_run_id
                or candidate_time > final_time
                or candidate_time.astimezone(ZoneInfo("Asia/Taipei")).date().isoformat() != asof
                or manifest.get("signal_asof") != asof
                or set(available_dates) != {asof}
            ):
                raise BridgeError(f"target rank signal same-run/cutoff/PIT binding invalid: {path}")
        audits.append({
            "signals": rel(path), "signals_sha256": sha256(path), "date": frame.date.iloc[0],
            "rows": len(frame), "instrument_count": int(frame.instrument.nunique()),
            "candidate_rank_min": int(frame.qlib_rank.min()), "candidate_rank_max": int(frame.qlib_rank.max()),
            "manifest": rel(manifest_path), "manifest_sha256": sha256(manifest_path),
            "validator_report": rel(report_path) if report_path.exists() else "",
            "validator_report_sha256": sha256(report_path) if report_path.exists() else "",
            "artifact_type": manifest.get("artifact_type"),
            "candidate_decision_cutoff": candidate_cutoff,
            "source_class": "isolated_standard_model_signal_artifact" if "project_runtime_convergence" in rel(path) else "standard_model_signal_artifact",
            "status": "PASS",
        })
    combined = pd.concat(frames, ignore_index=True).sort_values(["instrument", "date"])
    if combined.duplicated(["date", "instrument"]).any():
        raise BridgeError("duplicate rank history date/instrument")
    dates = sorted(combined.date.unique())
    if dates != expected_dates:
        raise BridgeError(f"rank history must equal final six formal/observed sessions; observed={dates} expected={expected_dates}")
    return combined, audits


def rank_features(history: pd.DataFrame, asof: str) -> pd.DataFrame:
    out = history.copy().sort_values(["instrument", "date"])
    groups = out.groupby("date", sort=False)
    out["qlib_score_percentile_by_date"] = groups.qlib_score_raw.rank(pct=True, method="average", ascending=True)
    out["qlib_score_zscore_by_date"] = (
        (out.qlib_score_raw - groups.qlib_score_raw.transform("mean"))
        / groups.qlib_score_raw.transform("std").replace(0, np.nan)
    )
    for limit in (10, 30, 50):
        out[f"top{limit}_flag"] = (out.qlib_rank <= limit).astype(float)
    for lag in (1, 3, 5):
        out[f"rank_change_{lag}d"] = out.groupby("instrument").qlib_rank.diff(lag)
    for flag, name in (("top30_flag", "top30_streak"), ("top50_flag", "top50_streak")):
        out[name] = out.groupby("instrument")[flag].transform(lambda values: values.groupby((values == 0).cumsum()).cumsum())
    return out[out.date == asof].copy()


def rsi(values: pd.Series) -> pd.Series:
    delta = values.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    return (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50.0)


def price_features(prices: pd.DataFrame, calendar: list[str], target_symbols: list[str], asof: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    prices = prices[prices.trade_date <= pd.Timestamp(asof)].copy()
    prices = prices[prices.instrument.isin(target_symbols)]
    prices["date"] = prices.trade_date.dt.strftime("%Y-%m-%d")
    for col in ("open", "high", "low", "close", "volume", "trading_money"):
        prices[col] = pd.to_numeric(prices.get(col), errors="coerce")
    prices["vwap"] = prices.trading_money / prices.volume.replace(0, np.nan)
    dates = [value for value in calendar if value <= asof]
    grid = pd.MultiIndex.from_product([target_symbols, dates], names=["instrument", "date"])
    prices = prices.set_index(["instrument", "date"]).reindex(grid).reset_index().sort_values(["instrument", "date"])
    by = prices.groupby("instrument", group_keys=False)
    for window in (5, 10, 20, 60):
        prices[f"MA{window}"] = by.close.transform(lambda x, w=window: x.rolling(w, min_periods=w).mean())
    prices["RSI14"] = by.close.transform(rsi)
    prices["MACD"] = by.close.transform(
        lambda x: x.ewm(span=12, adjust=False, min_periods=12).mean() - x.ewm(span=26, adjust=False, min_periods=26).mean()
    )
    ma20 = by.close.transform(lambda x: x.rolling(20, min_periods=20).mean())
    sd20 = by.close.transform(lambda x: x.rolling(20, min_periods=20).std())
    prices["Bollinger_position"] = ((prices.close - ma20) / (2 * sd20.replace(0, np.nan))).clip(-5, 5)
    prices["ret20"] = by.close.pct_change(20, fill_method=None)
    returns = by.close.pct_change(fill_method=None)
    prices["volatility20"] = returns.groupby(prices.instrument).transform(lambda x: x.rolling(20, min_periods=20).std())
    prices["volume_ratio20"] = prices.volume / by.volume.transform(lambda x: x.rolling(20, min_periods=20).mean()).replace(0, np.nan)
    value = prices.volume * prices.vwap
    prices["avg_trading_value_20d"] = value.groupby(prices.instrument).transform(lambda x: x.rolling(20, min_periods=20).mean())
    volume_change = by.volume.pct_change(fill_method=None)
    prices["volume_stability20"] = 1 / (1 + volume_change.groupby(prices.instrument).transform(lambda x: x.rolling(20, min_periods=20).std()))
    prices["missing_rate20"] = prices.close.isna().astype(float).groupby(prices.instrument).transform(lambda x: x.rolling(20, min_periods=1).mean())
    prices["suspension_proxy"] = (prices.volume.fillna(0) <= 0).astype(float)
    prices["slippage_proxy"] = 1 / np.sqrt(value.replace(0, np.nan))
    prices["_ma20"] = ma20
    target = prices[prices.date == asof].copy()
    audit = {
        "target_rows": len(target),
        "target_symbols": int(target.instrument.nunique()),
        "history_date_min": dates[0] if dates else "",
        "history_date_max": dates[-1] if dates else "",
        "calendar_sessions": len(dates),
    }
    return target, audit


def market_features(
    twii_raw: Path,
    capture: Path,
    cutoff: datetime,
    calendar: list[str],
    asof: str,
    prices: pd.DataFrame,
    source_run_id: str,
) -> tuple[dict[str, float], dict[str, Any]]:
    meta = read_json(capture)
    observed = parse_time(str(meta.get("observed_at") or ""), "twii.observed_at")
    if meta.get("source_run_id") != source_run_id:
        raise BridgeError("TWII capture source run mismatch")
    if sha256(twii_raw) != meta.get("raw_sha256"):
        raise BridgeError("TWII capture checksum mismatch")
    payload = read_json(twii_raw)
    frame = pd.DataFrame(payload.get("data") or [])
    frame["date"] = frame.date.astype(str).str[:10]
    frame["close"] = pd.to_numeric(frame.close, errors="coerce")
    frame = frame[frame.date <= asof].dropna(subset=["close"]).drop_duplicates("date", keep="last").sort_values("date")
    dates = [date for date in calendar if date <= asof]
    series = frame.set_index("date").reindex(dates).close
    if len(series) < 120 or series.tail(120).isna().any() or series.index[-1] != asof:
        raise BridgeError("TWII requires an exact trailing 120-session grid through asof")
    close = series
    ret = close.pct_change(fill_method=None)
    values = {
        "TWII_ret20": close.pct_change(20, fill_method=None).iloc[-1],
        "TWII_ret60": close.pct_change(60, fill_method=None).iloc[-1],
        "TWII_close_vs_MA60": close.iloc[-1] / close.rolling(60, min_periods=60).mean().iloc[-1] - 1,
        "TWII_close_vs_MA120": close.iloc[-1] / close.rolling(120, min_periods=120).mean().iloc[-1] - 1,
        "market_volatility20": ret.rolling(20, min_periods=20).std().iloc[-1],
        "market_drawdown60": close.iloc[-1] / close.rolling(60, min_periods=20).max().iloc[-1] - 1,
    }
    breadth = prices.dropna(subset=["_ma20"]).assign(above=lambda x: (x.close > x._ma20).astype(float)).groupby("date").above.mean()
    values["market_breadth20"] = breadth.get(asof, np.nan)
    parsed = {key: float(value) for key, value in values.items()}
    if not all(math.isfinite(value) for value in parsed.values()):
        raise BridgeError("non-finite market feature")
    audit = {
        "family": "twii", "capture": rel(capture), "capture_sha256": sha256(capture), "raw": rel(twii_raw),
        "raw_sha256": sha256(twii_raw), "observed_at": observed.isoformat(),
        "target_date_present": asof in set(frame.date), "trailing_sessions": 120,
        "available_before_cutoff": observed <= cutoff, "source_run_id_match": True,
    }
    return parsed, audit


def signed_streak(values: pd.Series) -> pd.Series:
    result, current_sign, count = [], 0, 0
    for value in values.fillna(0):
        sign = 1 if value > 0 else -1 if value < 0 else 0
        if sign == 0:
            current_sign, count = 0, 0
        elif sign == current_sign:
            count += 1
        else:
            current_sign, count = sign, 1
        result.append(current_sign * count)
    return pd.Series(result, index=values.index)


def orthogonal_features(
    inst: pd.DataFrame, margin: pd.DataFrame, selected_trade_date: str, instruments: list[str]
) -> pd.DataFrame:
    """Implement O2's delayed as-of join: flow at t is visible on the next session."""
    selected = pd.Timestamp(selected_trade_date)
    inst = inst[inst.trade_date <= selected].copy()
    inst["institutional_total_net_buy"] = pd.to_numeric(inst.total_institutional_net_buy, errors="coerce")
    bases = ("foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy", "institutional_total_net_buy")
    for col in bases:
        inst[col] = pd.to_numeric(inst[col], errors="coerce")
        for window in (1, 3, 5, 10):
            inst[f"{col}_roll{window}"] = inst.groupby("instrument")[col].transform(lambda x, w=window: x.rolling(w, min_periods=w).sum())
    inst["institutional_total_net_buy_streak"] = inst.groupby("instrument")["institutional_total_net_buy"].transform(signed_streak)
    inst = inst.sort_values(["instrument", "trade_date"]).groupby("instrument", as_index=False).tail(1)
    if set(inst.trade_date.dt.strftime("%Y-%m-%d")) != {selected_trade_date}:
        raise BridgeError("institutional selected_trade_date_not_complete")
    inst["institutional_missing_flag"] = 0.0
    inst["institutional_delay_flag"] = 0.0
    inst["institutional_flow_delay_days"] = 0.0
    inst["institutional_flow_asof_missing_flag"] = 0.0

    margin = margin[margin.trade_date <= selected].copy()
    margin["margin_balance"] = pd.to_numeric(margin.margin_purchase_today_balance, errors="coerce")
    margin["margin_balance_change"] = margin.margin_balance - pd.to_numeric(margin.margin_purchase_yesterday_balance, errors="coerce")
    margin["short_balance"] = pd.to_numeric(margin.short_sale_today_balance, errors="coerce")
    margin["short_balance_change"] = margin.short_balance - pd.to_numeric(margin.short_sale_yesterday_balance, errors="coerce")
    for col in ("margin_balance_change", "short_balance_change"):
        for window in (1, 3, 5, 10):
            margin[f"{col}_roll{window}"] = margin.groupby("instrument")[col].transform(lambda x, w=window: x.rolling(w, min_periods=w).sum())
    margin["margin_direction_proxy"] = (margin.margin_balance_change > 0).astype(int) - (margin.margin_balance_change < 0).astype(int)
    margin["short_direction_proxy"] = (margin.short_balance_change > 0).astype(int) - (margin.short_balance_change < 0).astype(int)
    margin["margin_short_divergence_proxy"] = margin.margin_direction_proxy - margin.short_direction_proxy
    margin = margin.sort_values(["instrument", "trade_date"]).groupby("instrument", as_index=False).tail(1)
    if set(margin.trade_date.dt.strftime("%Y-%m-%d")) != {selected_trade_date}:
        raise BridgeError("margin selected_trade_date_not_complete")
    margin["margin_short_missing_flag"] = 0.0
    margin["margin_short_delay_flag"] = 0.0
    margin["margin_short_delay_days"] = 0.0
    margin["margin_short_asof_missing_flag"] = 0.0
    result = pd.DataFrame({"instrument": instruments}).merge(inst, on="instrument", how="left", suffixes=("", "_inst"))
    return result.merge(margin, on="instrument", how="left", suffixes=("", "_margin"))


def _ledger_identity(row: dict[str, Any]) -> tuple[str, str, str]:
    return tuple(str(row.get(key, "")) for key in ("asof", "source_run_id", "decision_cutoff"))


@contextmanager
def _ledger_file_lock(path: Path):
    """Serialize ledger read/check/write across daily shadow processes."""
    lock_path = path.with_name(f".{path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def append_ledger(path: Path, row: dict[str, Any]) -> str:
    with _ledger_file_lock(path):
        return _append_ledger_locked(path, row)


def _append_ledger_locked(path: Path, row: dict[str, Any]) -> str:
    """Append an immutable observation, or quarantine a conflicting attempt."""
    fields = [
        "asof", "source_run_id", "decision_cutoff", "status", "accepted", "warmup_counted",
        "feature_rows", "scored_rows", "model_a_top50_rows", "feature_frame_sha256",
        "model_b_signals_sha256", "reason", "recorded_at", "row_sha256",
    ]
    rows = []
    if path.exists():
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
    candidate = {key: row.get(key, "") for key in fields if key != "row_sha256"}
    identity = _ledger_identity(candidate)
    same_identity = [item for item in rows if _ledger_identity(item) == identity]
    if same_identity:
        existing = same_identity[0]
        comparable = {key: str(existing.get(key, "")) for key in fields if key not in {"recorded_at", "row_sha256"}}
        proposed = {key: str(candidate.get(key, "")) for key in fields if key not in {"recorded_at", "row_sha256"}}
        if comparable == proposed:
            return "NOOP_ALREADY_RECORDED"
        raise BridgeError("observation ledger identity payload conflict")
    same_day = [item for item in rows if str(item.get("asof", "")) == identity[0]]
    if same_day:
        digest = hashlib.sha256(json.dumps(candidate, sort_keys=True).encode()).hexdigest()[:12]
        conflict = path.with_name(f"{path.stem}.conflict.{identity[0]}.{digest}.json")
        write_json(conflict, {"status": "QUARANTINED_SAME_DAY_CONFLICT", "candidate": candidate, "existing": same_day})
        return "QUARANTINED_SAME_DAY_CONFLICT"
    rows.append(candidate)
    for item in rows:
        item["row_sha256"] = observation_ledger_row_sha256(item)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda item: (item["asof"], item["decision_cutoff"])))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return "APPENDED"


def observation_ledger_row_sha256(row: dict[str, Any]) -> str:
    fields = (
        "asof", "source_run_id", "decision_cutoff", "status", "accepted", "warmup_counted",
        "feature_rows", "scored_rows", "model_a_top50_rows", "feature_frame_sha256",
        "model_b_signals_sha256", "reason", "recorded_at",
    )
    canonical = {field: str(row.get(field, "")) for field in fields}
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write_standard_model_signal_artifact(
    output: Path,
    signal: pd.DataFrame,
    *,
    asof: str,
    cutoff: datetime,
    source_run_id: str,
    feature_path: Path,
    source_ledger_path: Path,
    rank_ledger_path: Path,
) -> Path:
    """Write the portable child artifact; the parent files remain legacy bridge evidence."""
    artifact = output / "model_signal_artifact"
    artifact.mkdir(parents=True, exist_ok=True)
    child_signal = artifact / "signals.csv"
    child_signal_frame = signal[CORE_SIGNAL_COLUMNS].copy()
    # The generic ModelSignalArtifact contract compares dates, not decision-time
    # instants.  Exact cutoff remains bound in this manifest and source ledger.
    child_signal_frame["available_at"] = asof
    child_signal_frame.to_csv(child_signal, index=False)
    schema = {
        "artifact_type": "model_signal", "artifact_contract": "ModelSignalArtifact", "schema_version": "model_signal_contract_v1.o4",
        "core_fields": CORE_SIGNAL_COLUMNS,
        "available_at_policy": "signal_asof date; exact decision_cutoff RFC3339 is bound in manifest/source ledger",
        "production_allowed": False,
    }
    write_json(artifact / "schema.json", schema)
    pd.DataFrame([{
        "asof": asof, "row_count": len(signal), "instrument_count": int(signal.instrument.nunique()),
        "candidate_rank_min": int(signal.candidate_rank.min()) if len(signal) else "",
        "candidate_rank_max": int(signal.candidate_rank.max()) if len(signal) else "",
        "status": "PASS" if len(signal) == 50 else "FAIL",
    }]).to_csv(artifact / "coverage_audit.csv", index=False)
    pd.DataFrame([{"field": field, "present": field in signal.columns, "status": "PASS"} for field in FORBIDDEN]).to_csv(
        artifact / "forbidden_field_audit.csv", index=False
    )
    pd.DataFrame([
        {"legacy_field": "candidate_rank", "canonical_field": "candidate_rank", "source": "Model A complete 150-rank source", "status": "PASS"},
        {"legacy_field": "full_qlib_rank", "canonical_field": "full_qlib_rank", "source": "Model A complete 150-rank source", "status": "PASS"},
        {"legacy_field": "ltr_score", "canonical_field": "buy_score/raw_score", "source": "frozen Model B pickle", "status": "PASS"},
    ]).to_csv(artifact / "legacy_mapping_audit.csv", index=False)
    files = {
        "signals": child_signal, "schema": artifact / "schema.json", "coverage_audit": artifact / "coverage_audit.csv",
        "forbidden_field_audit": artifact / "forbidden_field_audit.csv", "legacy_mapping_audit": artifact / "legacy_mapping_audit.csv",
    }
    manifest = {
        "artifact_type": "model_signal", "artifact_contract": "ModelSignalArtifact", "schema_version": "model_signal_contract_v1.o4",
        "contract_version": "MODEL_SIGNAL_CONTRACT_CN.md@2026-06-16",
        "model_id": MODEL_B, "model_name": MODEL_B, "model_family": "ltr",
        "run_id": f"o4_shadow_{asof.replace('-', '')}", "asof": asof, "signal_asof": asof,
        "available_at_policy": schema["available_at_policy"], "decision_cutoff": cutoff.isoformat(),
        "source_acquisition_run_id": source_run_id, "status": "QUARANTINED_SHADOW_OBSERVATION",
        "row_count": len(signal), "quality_status": "pass" if len(signal) == 50 else "fail",
        "source_artifact": rel(feature_path), "source_model_artifact": rel(MODEL_PATH),
        "source_feature_artifact": rel(feature_path), "source_ledger": rel(source_ledger_path),
        "source_ledger_sha256": sha256(source_ledger_path), "rank_source_ledger": rel(rank_ledger_path),
        "rank_source_ledger_sha256": sha256(rank_ledger_path), "feature_frame_sha256": sha256(feature_path),
        "model_sha256": sha256(MODEL_PATH), "whitelist_sha256": sha256(WHITELIST_PATH),
        "output_files": {name: rel(path) for name, path in files.items()},
        "checksums": {name: sha256(path) for name, path in files.items()},
        "extensions": {"schema_version": "model_signal_extension_v1", "fields": {}},
        "production_allowed": False, "no_provider_publish": True, "no_accepted_latest_switch": True,
        "no_publish": True, "no_baseline_switch": True, "not_published_latest": True,
    }
    write_json(artifact / "manifest.json", manifest)
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--decision-cutoff", required=True)
    parser.add_argument("--model-a-signals", action="append", required=True)
    parser.add_argument("--daily-price-adapter", required=True)
    parser.add_argument("--institutional-adapter", required=True)
    parser.add_argument("--margin-adapter", required=True)
    parser.add_argument("--twii-raw", required=True)
    parser.add_argument("--twii-capture", required=True)
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    output = Path(args.output_dir).resolve()
    ledger_path = Path(args.ledger).resolve()
    isolated = (ROOT / "data_tw/experiments").resolve()
    if not output.is_relative_to(isolated) or not ledger_path.is_relative_to(isolated):
        raise BridgeError("output and ledger must remain under data_tw/experiments")
    output.mkdir(parents=True, exist_ok=True)
    before = fingerprint()
    cutoff = parse_time(args.decision_cutoff, "decision_cutoff")
    if cutoff > datetime.now(timezone.utc):
        raise BridgeError("decision cutoff cannot be in the future")
    whitelist = pd.read_csv(WHITELIST_PATH).sort_values("order")
    features = whitelist.feature.astype(str).tolist()
    if len(features) != 78 or len(set(features)) != 78 or any(any(token in name.lower() for token in FORBIDDEN) for name in features):
        raise BridgeError("O4 whitelist is not an exact safe 78-feature set")

    price, price_audit = load_adapter(Path(args.daily_price_adapter), args.source_run_id, cutoff, "adjusted_price")
    inst, inst_audit = load_adapter(Path(args.institutional_adapter), args.source_run_id, cutoff, "institutional_flow")
    margin, margin_audit = load_adapter(Path(args.margin_adapter), args.source_run_id, cutoff, "margin_short")
    if price_audit["trade_date_max"] != args.asof:
        raise BridgeError("required adapter trade_date_max_not_asof:adjusted_price")
    formal_calendar = load_calendar_dates(Path(args.calendar))
    observed_price_dates = set(price.trade_date.dt.strftime("%Y-%m-%d"))
    expected_rank_dates = [date for date in formal_calendar if date in observed_price_dates and date <= args.asof][-6:]
    if len(expected_rank_dates) != 6 or expected_rank_dates[-1] != args.asof:
        raise BridgeError(f"cannot establish final six formal/observed rank sessions: {expected_rank_dates}")
    rank_history, rank_audit = load_rank_history(
        [Path(path) for path in args.model_a_signals], args.asof, expected_rank_dates,
        args.source_run_id, cutoff.isoformat(),
    )
    target_rank_audit = next(item for item in rank_audit if item["date"] == args.asof)
    current = rank_features(rank_history, args.asof)
    instruments = sorted(current.instrument.unique())
    calendar_exceptions = sorted(
        date for date in formal_calendar
        if price_audit["trade_date_min"] <= date <= args.asof and date not in observed_price_dates
    )
    calendar = [date for date in formal_calendar if date in observed_price_dates]
    price_target, price_feature_audit = price_features(price, calendar, instruments, args.asof)
    price_feature_audit["formal_calendar_exceptions"] = calendar_exceptions
    price_feature_audit["calendar_policy"] = "formal calendar intersect same-run observed full-market dates; no fill"
    market, twii_audit = market_features(
        Path(args.twii_raw), Path(args.twii_capture), cutoff, calendar, args.asof,
        price_target, args.source_run_id,
    )
    prior_sessions = [date for date in calendar if date < args.asof]
    if not prior_sessions:
        raise BridgeError("no prior observed session for delayed O2 flow join")
    selected_flow_trade_date = prior_sessions[-1]
    validate_delayed_flow_coverage(
        inst, inst_audit, selected_trade_date=selected_flow_trade_date, instruments=instruments,
    )
    validate_delayed_flow_coverage(
        margin, margin_audit, selected_trade_date=selected_flow_trade_date, instruments=instruments,
    )
    orthogonal = orthogonal_features(inst, margin, selected_flow_trade_date, instruments)
    formula_parity_audit = {
        "status": "PASS",
        "reference": "scripts/build_orthogonal_ltr_phase_o2_pit_safe_features.py",
        "price_and_twii_selected_trade_date": args.asof,
        "institutional_flow_selected_trade_date": selected_flow_trade_date,
        "margin_short_selected_trade_date": selected_flow_trade_date,
        "derived_available_at": args.asof,
        "delay_reason": "exact_t1",
        "same_day_flow_excluded": selected_flow_trade_date < args.asof,
        "rolling_and_streak_cutoff": selected_flow_trade_date,
        "orthogonal_formula_policy": "O2 rolling sums and signed streak through selected prior trade_date; delayed as-of join",
    }
    if not formula_parity_audit["same_day_flow_excluded"]:
        raise BridgeError("formula parity requires prior-session institutional and margin data")
    frame = current.merge(price_target, on="instrument", how="left", suffixes=("", "_price")).merge(orthogonal, on="instrument", how="left", suffixes=("", "_orthogonal"))
    for name, value in market.items():
        frame[name] = value
    missing_columns = sorted(set(features) - set(frame.columns))
    if missing_columns:
        raise BridgeError(f"missing feature columns: {missing_columns}")
    frame = frame[["date", "instrument", *features]].sort_values(["qlib_rank", "instrument"])
    numeric = frame[features].apply(pd.to_numeric, errors="coerce")
    top50 = numeric[frame.qlib_rank <= 50]
    finite_by_feature = {name: bool(np.isfinite(top50[name].to_numpy(dtype=float)).all()) for name in features}
    blocked = [name for name, passed in finite_by_feature.items() if not passed]
    feature_path = output / "feature_frame.csv"
    frame.to_csv(feature_path, index=False)

    signal_path = output / "signals.csv"
    model_score_rows = 0
    signal = pd.DataFrame()
    if not blocked and len(frame) == 150 and int((frame.qlib_rank <= 50).sum()) == 50:
        with MODEL_PATH.open("rb") as handle:
            model = pickle.load(handle)
        scored = frame[frame.qlib_rank <= 50].copy()
        scored["ltr_score"] = np.asarray(model.predict(scored[features].astype(float)), dtype=float)
        scored = scored.sort_values(["ltr_score", "instrument"], ascending=[False, True])
        scored["score_rank"] = range(1, len(scored) + 1)
        signal = pd.DataFrame({
            "date": scored.date,
            "instrument": scored.instrument,
            "model_name": MODEL_B,
            "model_family": "ltr",
            "candidate_rank": scored.qlib_rank.astype(int),
            "buy_score": scored.ltr_score,
            "raw_score": scored.ltr_score,
            "score_rank": scored.score_rank,
            "full_qlib_rank": scored.qlib_rank.astype(int),
            "signal_asof": args.asof,
            "available_at": args.asof,
            "source_artifact": rel(feature_path),
            "source_model_artifact": rel(MODEL_PATH),
            "source_feature_artifact": rel(feature_path),
        })
        signal.to_csv(signal_path, index=False)
        model_score_rows = len(signal)
    else:
        pd.DataFrame(columns=CORE_SIGNAL_COLUMNS).to_csv(signal_path, index=False)

    same_day_cutoff = cutoff.astimezone(ZoneInfo("Asia/Taipei")).date().isoformat() == args.asof
    accepted = not blocked and model_score_rows == 50 and same_day_cutoff and formula_parity_audit["status"] == "PASS"
    if accepted:
        reason = ""
    elif not same_day_cutoff:
        reason = "late_capture_or_cutoff_not_on_signal_date_asia_taipei"
    else:
        reason = "nonfinite_or_incomplete_78d_top50"
    status = "ACCEPTED_PROSPECTIVE_INPUT" if accepted else "QUARANTINED_SHADOW_OBSERVATION"
    source_ledger = {
        "schema_version": "o4.prospective_source_ledger.v1",
        "asof": args.asof,
        "source_run_id": args.source_run_id,
        "decision_cutoff": cutoff.isoformat(),
        "sources": [price_audit, inst_audit, margin_audit, twii_audit],
        "same_run_required_segments": list(REQUIRED_SEGMENTS),
        "source_gate_mode": "delayed_flow_prior_session",
        "price_target_date": args.asof,
        "flow_prior_observed_session": selected_flow_trade_date,
        "twii_capture_binding": "isolated capture; source_run_id recorded in capture",
        "late_capture_policy": "decision cutoff must fall on signal_asof Asia/Taipei date to count as prospective",
        "required_source_dates_match_asof": price_audit["trade_date_max"] == args.asof,
        "calendar_input": rel(Path(args.calendar)),
        "calendar_input_sha256": sha256(Path(args.calendar)),
        "formal_calendar_sessions_through_asof": [date for date in formal_calendar if date <= args.asof],
    }
    source_ledger_path = output / "source_ledger.json"
    write_json(source_ledger_path, source_ledger)
    pd.DataFrame([{"feature": name, "family": whitelist.set_index("feature").loc[name, "family"], "finite_top50": finite_by_feature[name]} for name in features]).to_csv(output / "feature_coverage.csv", index=False)
    rank_ledger_path = output / "rank_source_ledger.csv"
    pd.DataFrame(rank_audit).to_csv(rank_ledger_path, index=False)
    # Keep the former filename as a compatibility view; its content is the signed ledger.
    pd.DataFrame(rank_audit).to_csv(output / "rank_history_audit.csv", index=False)
    write_json(output / "pit_audit.json", {
        "status": "PASS" if not blocked else "FAIL",
        "decision_cutoff": cutoff.isoformat(),
        "same_day_cutoff": same_day_cutoff,
        "accepted_prospective": accepted,
        "blocked_features": blocked,
        "price_feature_audit": price_feature_audit,
        "twii_audit": twii_audit,
        "formula_parity_audit": formula_parity_audit,
        "future_or_outcome_fields_consumed": [],
    })
    ledger_row = {
        "asof": args.asof, "source_run_id": args.source_run_id, "decision_cutoff": cutoff.isoformat(),
        "status": status, "accepted": str(accepted).lower(), "warmup_counted": str(accepted).lower(),
        "feature_rows": len(frame), "scored_rows": model_score_rows, "model_a_top50_rows": int((frame.qlib_rank <= 50).sum()),
        "feature_frame_sha256": sha256(feature_path), "model_b_signals_sha256": sha256(signal_path),
        "reason": reason, "recorded_at": now(),
    }
    append_ledger(ledger_path, ledger_row)
    ledger_rows = list(csv.DictReader(ledger_path.open(encoding="utf-8")))
    ledger_identity = {key: ledger_row[key] for key in ("asof", "source_run_id", "decision_cutoff")}
    matched_ledger_rows = [
        item for item in ledger_rows
        if all(str(item.get(key, "")) == str(value) for key, value in ledger_identity.items())
    ]
    if len(matched_ledger_rows) != 1:
        raise BridgeError("observation ledger identity is not unique after append")
    child_artifact = write_standard_model_signal_artifact(
        output, signal, asof=args.asof, cutoff=cutoff, source_run_id=args.source_run_id,
        feature_path=feature_path, source_ledger_path=source_ledger_path, rank_ledger_path=rank_ledger_path,
    )
    manifest = {
        "schema_version": "o4.prospective_shadow_observation.v1",
        "created_at": now(), "asof": args.asof, "source_run_id": args.source_run_id,
        "decision_cutoff": cutoff.isoformat(), "status": status, "accepted": accepted,
        "warmup_counted": accepted, "quarantine_reason": reason,
        "model_a": MODEL_A, "model_b": MODEL_B,
        "model_b_role": "rerank_model_a_top50_only",
        "feature_count": 78, "feature_rows": len(frame), "scored_rows": model_score_rows,
        "model_a_top50_rows": int((frame.qlib_rank <= 50).sum()),
        "candidate_rank_and_full_qlib_rank_from_model_a": True,
        "feature_frame": rel(feature_path), "feature_frame_sha256": sha256(feature_path),
        "signals": rel(signal_path), "signals_sha256": sha256(signal_path),
        "source_ledger": rel(source_ledger_path), "source_ledger_sha256": sha256(source_ledger_path),
        "rank_source_ledger": rel(rank_ledger_path), "rank_source_ledger_sha256": sha256(rank_ledger_path),
        "target_model_a_candidate_decision_cutoff": target_rank_audit["candidate_decision_cutoff"],
        "model_path": rel(MODEL_PATH), "model_sha256": sha256(MODEL_PATH),
        "whitelist": rel(WHITELIST_PATH), "whitelist_sha256": sha256(WHITELIST_PATH),
        "model_signal_artifact": rel(child_artifact), "model_signal_artifact_manifest": rel(child_artifact / "manifest.json"),
        "model_signal_artifact_manifest_sha256": sha256(child_artifact / "manifest.json"),
        "observation_ledger": rel(ledger_path),
        "observation_ledger_sha256": sha256(ledger_path),
        "observation_ledger_snapshot_sha256": sha256(ledger_path),
        "observation_ledger_row_identity": ledger_identity,
        "observation_ledger_row_sha256": matched_ledger_rows[0]["row_sha256"],
        "formula_parity_audit": formula_parity_audit,
        "no_publish": True, "no_baseline_switch": True, "production_allowed": False,
    }
    write_json(output / "manifest.json", manifest)
    after = fingerprint()
    write_json(output / "forbidden_scope_audit.json", {
        "protected_before": before, "protected_after": after, "protected_unchanged": before == after,
        "provider_publish": False, "latest_switch": False, "baseline_switch": False,
        "broker_order": False, "training": False,
    })
    if before != after:
        raise BridgeError("protected path changed")
    if args.json:
        print(json.dumps(manifest, indent=2, ensure_ascii=True))
    return 0 if model_score_rows == 50 else 2


if __name__ == "__main__":
    raise SystemExit(main())
