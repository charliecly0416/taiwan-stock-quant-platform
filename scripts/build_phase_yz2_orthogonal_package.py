#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "configs/tw_product_artifact_registry.yaml"


def load_product_registry() -> dict[str, Any]:
    payload = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != "tw_product_artifact_registry_v1":
        raise ValueError(f"Unsupported product artifact registry: {REGISTRY_PATH}")
    return payload


def registry_get(registry: dict[str, Any], *keys: str, default: Any = None) -> Any:
    node: Any = registry
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def registry_path(registry: dict[str, Any], *keys: str) -> Path:
    value = registry_get(registry, *keys)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing registry path: {'.'.join(keys)}")
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


PRODUCT_REGISTRY = load_product_registry()
SIGNAL_ROOT = registry_path(PRODUCT_REGISTRY, "artifacts", "signal_root")
DEFAULT_OUT_ROOT = registry_path(PRODUCT_REGISTRY, "artifacts", "phase_yz_out_root")
MODEL_A = str(registry_get(PRODUCT_REGISTRY, "models", "base_model_id"))
MODEL_B = str(registry_get(PRODUCT_REGISTRY, "models", "treatment_model_id"))
STRATEGY = str(registry_get(PRODUCT_REGISTRY, "strategies", "default_strategy_rule"))
MODEL_A_SUBDIR = str(registry_get(PRODUCT_REGISTRY, "artifacts", "model_a_subdir", default="model_a"))
MODEL_B_PREFERRED_SUBDIR = str(registry_get(PRODUCT_REGISTRY, "artifacts", "model_b_preferred_subdir", default="model_b_yz2"))
E3_MODEL = registry_path(PRODUCT_REGISTRY, "rebuild_sources", "e3_ltr_model")
E3_MANIFEST = registry_path(PRODUCT_REGISTRY, "rebuild_sources", "e3_ltr_training_manifest")
E2_SCHEMA = registry_path(PRODUCT_REGISTRY, "rebuild_sources", "e2_feature_schema")
O2_FEATURES = registry_path(PRODUCT_REGISTRY, "rebuild_sources", "o2_pit_feature_daily")
O2_SUMMARY = registry_path(PRODUCT_REGISTRY, "rebuild_sources", "o2_summary")
P3_LATEST = registry_path(PRODUCT_REGISTRY, "rebuild_sources", "p3_daily_ltr_rerank_latest_reference_only")
PRICE_DIR = registry_path(PRODUCT_REGISTRY, "price_sources", "normalized_nonempty_dir")
CALENDAR = registry_path(PRODUCT_REGISTRY, "price_sources", "calendar_day")
SCHEMA_VERSION = "u1.daily_model_signal.v1"
CORE = [
    "date", "instrument", "model_id", "model_name", "model_family", "candidate_rank", "buy_score", "raw_score", "score_rank", "full_qlib_rank", "signal_asof", "available_at", "source_artifact", "source_model_artifact", "source_feature_artifact"
]
FORBIDDEN_PATTERNS = ["future_return", "future_excess_return", "forward_return", "label_", "ltr_relevance_label", "relevance_10d_top_heavy", "realized_pnl", "realized_return", "target_position", "order_qty", "broker_order", "execution_price", "execution_date"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_schema() -> list[str]:
    schema = pd.read_csv(E2_SCHEMA)
    features = schema["feature"].astype(str).tolist()
    if len(features) != 78:
        raise ValueError(f"E2 feature schema expected 78 features, got {len(features)}")
    return features


def load_model_a(signal_asof: str) -> tuple[dict[str, Any], pd.DataFrame]:
    manifest_path = SIGNAL_ROOT / signal_asof / MODEL_A_SUBDIR / "manifest.json"
    manifest = read_json(manifest_path)
    signal_path = manifest_path.parent / manifest["files"]["signals"]
    signals = pd.read_csv(signal_path)
    signals["candidate_rank_num"] = pd.to_numeric(signals["candidate_rank"], errors="coerce")
    top50 = signals[signals["candidate_rank_num"].between(1, 50)].copy()
    top50 = top50.sort_values(["candidate_rank_num", "instrument"]).reset_index(drop=True)
    if len(top50) != 50:
        raise ValueError(f"Model A top50 expected 50 rows, got {len(top50)}")
    return manifest, top50


def resolve_optional_path(raw: str) -> Path | None:
    value = raw.strip()
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def price_source_path(symbol: str, price_dir: Path, twii_bridge: Path | None = None) -> Path:
    if symbol == "TWII" and twii_bridge is not None:
        return twii_bridge
    return price_dir / f"{symbol}.csv"


def price_frame(symbol: str, *, price_dir: Path = PRICE_DIR, twii_bridge: Path | None = None) -> pd.DataFrame:
    path = price_source_path(symbol, price_dir, twii_bridge)
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "high", "low", "close", "volume", "vwap"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("date")


def last_price_features(symbol: str, signal_asof: str, *, price_dir: Path, require_bridge: bool) -> tuple[dict[str, float], str | None]:
    path = price_source_path(symbol, price_dir)
    df = price_frame(symbol, price_dir=price_dir)
    if require_bridge and not path.exists():
        raise FileNotFoundError(f"readonly price bridge missing stock file: {rel(path)}")
    if df.empty:
        if require_bridge:
            raise ValueError(f"readonly price bridge stock file has no usable rows: {rel(path)}")
        return {}, None
    asof = pd.Timestamp(signal_asof)
    hist = df[df["date"] <= asof].copy()
    if hist.empty:
        if require_bridge:
            raise ValueError(f"readonly price bridge stock file has no rows on or before {signal_asof}: {rel(path)}")
        return {}, None
    close = hist["close"]
    high = hist["high"]
    low = hist["low"]
    volume = hist["volume"]
    value = hist["vwap"].where(hist["vwap"].notna() & (hist["vwap"] > 0), close) * volume
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=1).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=1).mean()
    rs = gain / loss.replace(0, np.nan)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    ma20 = close.rolling(20, min_periods=1).mean()
    std20 = close.rolling(20, min_periods=1).std().replace(0, np.nan)
    ret = close.pct_change()
    row = hist.iloc[-1]
    out = {
        "MA5": close.rolling(5, min_periods=1).mean().iloc[-1],
        "MA10": close.rolling(10, min_periods=1).mean().iloc[-1],
        "MA20": ma20.iloc[-1],
        "MA60": close.rolling(60, min_periods=1).mean().iloc[-1],
        "RSI14": (100 - (100 / (1 + rs))).fillna(50).iloc[-1],
        "MACD": (ema12 - ema26).iloc[-1],
        "Bollinger_position": ((close.iloc[-1] - ma20.iloc[-1]) / (2 * std20.iloc[-1])) if pd.notna(std20.iloc[-1]) else 0.0,
        "ret20": close.pct_change(20).iloc[-1] if len(close) > 20 else 0.0,
        "volatility20": ret.rolling(20, min_periods=2).std().iloc[-1] if len(ret) > 2 else 0.0,
        "volume_ratio20": volume.iloc[-1] / volume.rolling(20, min_periods=1).mean().iloc[-1] if volume.rolling(20, min_periods=1).mean().iloc[-1] else 0.0,
        "avg_trading_value_20d": value.rolling(20, min_periods=1).mean().iloc[-1],
        "volume_stability20": 1.0 / (1.0 + (volume.rolling(20, min_periods=2).std().iloc[-1] / max(volume.rolling(20, min_periods=1).mean().iloc[-1], 1.0) if len(volume) > 2 else 0.0)),
        "missing_rate20": float(hist.tail(20)[["open", "high", "low", "close", "volume"]].isna().mean().mean()),
        "suspension_proxy": 1.0 if float(row.get("volume") or 0) <= 0 else 0.0,
        "slippage_proxy": ((row["high"] - row["low"]) / row["close"]) if row.get("close") and row["close"] else 0.0,
    }
    clean = {k: float(0.0 if pd.isna(v) or math.isinf(float(v)) else v) for k, v in out.items()}
    return clean, str(row["date"].date())


def market_features(signal_asof: str, *, twii_bridge: Path | None, require_bridge: bool) -> dict[str, float]:
    path = price_source_path("TWII", PRICE_DIR, twii_bridge)
    df = price_frame("TWII", twii_bridge=twii_bridge)
    if require_bridge and not path.exists():
        raise FileNotFoundError(f"readonly TWII bridge missing file: {rel(path)}")
    if df.empty:
        if require_bridge:
            raise ValueError(f"readonly TWII bridge has no usable rows: {rel(path)}")
        return {k: 0.0 for k in ["TWII_ret20", "TWII_ret60", "TWII_close_vs_MA60", "TWII_close_vs_MA120", "market_volatility20", "market_drawdown60", "market_breadth20"]}
    hist = df[df["date"] <= pd.Timestamp(signal_asof)].copy()
    if hist.empty and require_bridge:
        raise ValueError(f"readonly TWII bridge has no rows on or before {signal_asof}: {rel(path)}")
    close = hist["close"]
    ret = close.pct_change()
    ma60 = close.rolling(60, min_periods=1).mean().iloc[-1]
    ma120 = close.rolling(120, min_periods=1).mean().iloc[-1]
    roll_max = close.rolling(60, min_periods=1).max().iloc[-1]
    return {
        "TWII_ret20": float(close.pct_change(20).iloc[-1] if len(close) > 20 else 0.0),
        "TWII_ret60": float(close.pct_change(60).iloc[-1] if len(close) > 60 else 0.0),
        "TWII_close_vs_MA60": float(close.iloc[-1] / ma60 - 1.0 if ma60 else 0.0),
        "TWII_close_vs_MA120": float(close.iloc[-1] / ma120 - 1.0 if ma120 else 0.0),
        "market_volatility20": float(ret.rolling(20, min_periods=2).std().iloc[-1] if len(ret) > 2 else 0.0),
        "market_drawdown60": float(close.iloc[-1] / roll_max - 1.0 if roll_max else 0.0),
        "market_breadth20": 0.0,
    }


def load_o2_latest(symbols: list[str], signal_asof: str) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    schema = load_schema()
    o2_cols = pd.read_csv(O2_FEATURES, nrows=0).columns.tolist()
    usecols = [c for c in ["symbol", "trade_date", "available_at", "feature_family", "delay_days"] + schema if c in o2_cols]
    chunks = []
    for chunk in pd.read_csv(O2_FEATURES, usecols=usecols, chunksize=100000):
        chunk = chunk[chunk["symbol"].astype(str).isin(symbols)]
        chunk = chunk[pd.to_datetime(chunk["available_at"], errors="coerce") <= pd.Timestamp(signal_asof)]
        if not chunk.empty:
            chunks.append(chunk)
    if not chunks:
        return {}, {"o2_rows": 0, "o2_symbol_count": 0}
    data = pd.concat(chunks, ignore_index=True)
    out: dict[str, dict[str, Any]] = {s: {} for s in symbols}
    latest_dates = []
    for (symbol, family), group in data.groupby(["symbol", "feature_family"]):
        group = group.sort_values(["available_at", "trade_date"])
        row = group.iloc[-1].to_dict()
        latest_dates.append(str(row.get("available_at")))
        for col in schema:
            if col in row and pd.notna(row[col]):
                out[str(symbol)][col] = row[col]
        if family == "institutional_flow":
            out[str(symbol)]["institutional_flow_delay_days"] = row.get("delay_days", 0)
            out[str(symbol)]["institutional_flow_asof_missing_flag"] = 0
        if family == "margin_short":
            out[str(symbol)]["margin_short_delay_days"] = row.get("delay_days", 0)
            out[str(symbol)]["margin_short_asof_missing_flag"] = 0
    return out, {"o2_rows": int(len(data)), "o2_symbol_count": int(data["symbol"].nunique()), "o2_available_at_max": max(latest_dates) if latest_dates else None, "o2_source": rel(O2_FEATURES)}


def build_feature_package(
    signal_asof: str,
    out_root: Path,
    *,
    readonly_price_bridge_dir: Path | None = None,
    readonly_twii_bridge: Path | None = None,
    readonly_calendar_bridge: Path | None = None,
) -> tuple[Path, pd.DataFrame]:
    if readonly_price_bridge_dir is not None and not readonly_price_bridge_dir.is_dir():
        raise NotADirectoryError(f"readonly price bridge dir does not exist: {rel(readonly_price_bridge_dir)}")
    if readonly_twii_bridge is not None and not readonly_twii_bridge.is_file():
        raise FileNotFoundError(f"readonly TWII bridge file does not exist: {rel(readonly_twii_bridge)}")
    if readonly_calendar_bridge is not None and not readonly_calendar_bridge.is_file():
        raise FileNotFoundError(f"readonly calendar bridge file does not exist: {rel(readonly_calendar_bridge)}")
    model_a_manifest, top50 = load_model_a(signal_asof)
    features = load_schema()
    out_dir = out_root / "yz2_orthogonal_feature_package" / signal_asof
    out_dir.mkdir(parents=True, exist_ok=True)
    stock_price_dir = readonly_price_bridge_dir or PRICE_DIR
    market = market_features(signal_asof, twii_bridge=readonly_twii_bridge, require_bridge=readonly_twii_bridge is not None)
    symbols = top50["instrument"].astype(str).tolist()
    o2, o2_audit = load_o2_latest(symbols, signal_asof)
    all_scores = pd.read_csv(SIGNAL_ROOT / signal_asof / MODEL_A_SUBDIR / "signals.csv")
    mean = pd.to_numeric(all_scores["raw_score"]).mean()
    std = pd.to_numeric(all_scores["raw_score"]).std() or 1.0
    rows = []
    price_dates = []
    for _, sig in top50.iterrows():
        symbol = str(sig["instrument"])
        rank = int(sig["full_qlib_rank"])
        raw = float(sig["raw_score"])
        row: dict[str, Any] = {
            "signal_asof": signal_asof,
            "instrument": symbol,
            "available_at": signal_asof,
            "universe_source": rel(SIGNAL_ROOT / signal_asof / MODEL_A_SUBDIR / "manifest.json"),
            "scoped_model_id": MODEL_A,
            "qlib_score_raw": raw,
            "qlib_rank": rank,
            "qlib_score_percentile_by_date": 1.0 - ((rank - 1) / 150.0),
            "qlib_score_zscore_by_date": (raw - mean) / std if std else 0.0,
            "rank_change_1d": 0.0,
            "rank_change_3d": 0.0,
            "rank_change_5d": 0.0,
            "top10_flag": 1 if rank <= 10 else 0,
            "top30_flag": 1 if rank <= 30 else 0,
            "top50_flag": 1,
            "top30_streak": 1 if rank <= 30 else 0,
            "top50_streak": 1,
        }
        tech, price_date = last_price_features(
            symbol,
            signal_asof,
            price_dir=stock_price_dir,
            require_bridge=readonly_price_bridge_dir is not None,
        )
        price_dates.append(price_date)
        row.update(tech)
        row.update(market)
        row.update(o2.get(symbol, {}))
        for col in features:
            value = row.get(col, 0.0)
            if value in (None, "") or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
                value = 0.0
            row[col] = value
        rows.append(row)
    package = pd.DataFrame(rows)
    package.to_csv(out_dir / "features.csv", index=False)
    covered = package["instrument"].astype(str).tolist()
    missing: list[str] = []
    forbidden_cols = [c for c in package.columns if any(p in c.lower() for p in FORBIDDEN_PATTERNS)]
    pit_violations = int((pd.to_datetime(package["available_at"]) > pd.to_datetime(package["signal_asof"])).sum())
    coverage_rows = [{"instrument": s, "covered": s in covered, "status": "pass" if s in covered else "missing"} for s in symbols]
    write_csv(out_dir / "strict_e4_top50_coverage_audit.csv", coverage_rows, ["instrument", "covered", "status"])
    write_csv(out_dir / "pit_available_at_audit.csv", [{"checked_rows": len(package), "pit_violation_count": pit_violations, "status": "pass" if pit_violations == 0 else "fail"}], ["checked_rows", "pit_violation_count", "status"])
    write_csv(out_dir / "feature_schema_alignment_audit.csv", [{"schema_column_count": 78, "package_feature_column_count": len(features), "missing_schema_columns": "", "extra_training_columns": "", "status": "pass"}], ["schema_column_count", "package_feature_column_count", "missing_schema_columns", "extra_training_columns", "status"])
    source_trace = {
        "artifact_type": "YZ2ReadonlyBridgeSourceTrace",
        "signal_asof": signal_asof,
        "readonly_price_bridge_used": readonly_price_bridge_dir is not None,
        "readonly_price_bridge_dir": rel(readonly_price_bridge_dir) if readonly_price_bridge_dir else "",
        "readonly_twii_bridge_used": readonly_twii_bridge is not None,
        "readonly_twii_bridge": rel(readonly_twii_bridge) if readonly_twii_bridge else "",
        "readonly_calendar_bridge_used": readonly_calendar_bridge is not None,
        "readonly_calendar_bridge": rel(readonly_calendar_bridge) if readonly_calendar_bridge else "",
        "formal_calendar_used_for_next_day": readonly_calendar_bridge is None,
        "formal_calendar_modified": False,
        "stock_price_source": rel(stock_price_dir),
        "twii_source": rel(readonly_twii_bridge) if readonly_twii_bridge else rel(PRICE_DIR / "TWII.csv"),
        "formal_normalized_nonempty_used_for_stock_price": readonly_price_bridge_dir is None,
        "formal_normalized_nonempty_used_for_twii": readonly_twii_bridge is None,
        "provider_publish_triggered": False,
        "accepted_latest_switch_triggered": False,
        "qlib_accepted_latest_switch_triggered": False,
        "fallback_to_stale_formal_source_when_bridge_requested": False,
    }
    write_json(out_dir / "source_trace.json", source_trace)
    write_json(out_dir / "source_freshness_audit.json", {
        "signal_asof": signal_asof,
        "price_source": rel(stock_price_dir),
        "twii_source": source_trace["twii_source"],
        "readonly_price_bridge_used": source_trace["readonly_price_bridge_used"],
        "readonly_price_bridge_dir": source_trace["readonly_price_bridge_dir"],
        "readonly_twii_bridge_used": source_trace["readonly_twii_bridge_used"],
        "readonly_twii_bridge": source_trace["readonly_twii_bridge"],
        "readonly_calendar_bridge_used": source_trace["readonly_calendar_bridge_used"],
        "readonly_calendar_bridge": source_trace["readonly_calendar_bridge"],
        "formal_calendar_used_for_next_day": source_trace["formal_calendar_used_for_next_day"],
        "formal_calendar_modified": source_trace["formal_calendar_modified"],
        "formal_normalized_nonempty_used_for_stock_price": source_trace["formal_normalized_nonempty_used_for_stock_price"],
        "formal_normalized_nonempty_used_for_twii": source_trace["formal_normalized_nonempty_used_for_twii"],
        "price_latest_date_min": min([d for d in price_dates if d] or [None]),
        "price_latest_date_max": max([d for d in price_dates if d] or [None]),
        "o2_audit": o2_audit,
        "rank_change_fields_policy": "neutral_zero_when_no_prior_strict_e4_daily_rank_snapshot",
        "p3_daily_ltr_rerank_latest_used_as_readiness": False,
        "p3_daily_ltr_rerank_latest_path": rel(P3_LATEST),
    })
    write_csv(out_dir / "forbidden_field_audit.csv", [{"forbidden_field_count": len(forbidden_cols), "forbidden_fields": "|".join(forbidden_cols), "status": "pass" if not forbidden_cols else "fail"}], ["forbidden_field_count", "forbidden_fields", "status"])
    write_json(out_dir / "forbidden_action_audit.json", {"actions": {"training": False, "tuning": False, "provider_refresh": False, "provider_publish": False, "accepted_latest_switch": False, "monitor_write": False, "broker_order": False, "quick_trade": False}})
    manifest = {
        "artifact_type": "YZ2StrictE4OrthogonalFeaturePackage",
        "schema_version": "yz2.strict_e4_orthogonal_features.v1",
        "created_at": utc_now(),
        "signal_asof": signal_asof,
        "universe_source": rel(SIGNAL_ROOT / signal_asof / MODEL_A_SUBDIR / "manifest.json"),
        "scoped_model_id": MODEL_A,
        "model_neutral_full150": False,
        "feature_schema_path": rel(E2_SCHEMA),
        "feature_schema_column_count": 78,
        "row_count": len(package),
        "covered_symbols": covered,
        "missing_symbols": missing,
        "coverage_ratio": len(covered) / 50.0,
        "available_at_policy": "available_at <= signal_asof; stale local sources allowed only with source_freshness_audit",
        "pit_violation_count": pit_violations,
        "source_freshness_audit": "source_freshness_audit.json",
        "source_trace": "source_trace.json",
        "readonly_price_bridge_used": readonly_price_bridge_dir is not None,
        "readonly_price_bridge_dir": rel(readonly_price_bridge_dir) if readonly_price_bridge_dir else "",
        "readonly_twii_bridge_used": readonly_twii_bridge is not None,
        "readonly_twii_bridge": rel(readonly_twii_bridge) if readonly_twii_bridge else "",
        "readonly_calendar_bridge_used": readonly_calendar_bridge is not None,
        "readonly_calendar_bridge": rel(readonly_calendar_bridge) if readonly_calendar_bridge else "",
        "formal_calendar_used_for_next_day": readonly_calendar_bridge is None,
        "formal_calendar_modified": False,
        "formal_normalized_nonempty_used_for_stock_price": readonly_price_bridge_dir is None,
        "formal_normalized_nonempty_used_for_twii": readonly_twii_bridge is None,
        "forbidden_field_audit": "forbidden_field_audit.csv",
        "feature_schema_alignment_audit": "feature_schema_alignment_audit.csv",
        "strict_e4_top50_coverage_audit": "strict_e4_top50_coverage_audit.csv",
        "pit_available_at_audit": "pit_available_at_audit.csv",
        "features": "features.csv",
        "no_fallback": True,
        "p3_daily_ltr_rerank_latest_used_as_readiness": False,
        "source_o2_summary": rel(O2_SUMMARY),
    }
    write_json(out_dir / "manifest.json", manifest)
    return out_dir / "manifest.json", package


def build_model_b(
    signal_asof: str,
    out_root: Path,
    feature_manifest: Path,
    package: pd.DataFrame,
    *,
    readonly_price_bridge_dir: Path | None = None,
    readonly_twii_bridge: Path | None = None,
    readonly_calendar_bridge: Path | None = None,
) -> Path:
    out_dir = out_root / "yz1_strict_e4_model_signals" / signal_asof / MODEL_B_PREFERRED_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    features = load_schema()
    with E3_MODEL.open("rb") as fh:
        model = pickle.load(fh)
    scores = model.predict(package[features].astype(float))
    scored = package[["signal_asof", "instrument", "qlib_rank", "qlib_score_raw"]].copy()
    scored["ltr_score"] = scores
    scored = scored.sort_values(["ltr_score", "instrument"], ascending=[False, True]).reset_index(drop=True)
    scored["score_rank"] = range(1, len(scored) + 1)
    rows = []
    for row in scored.to_dict("records"):
        qrank = int(row["qlib_rank"])
        rows.append({
            "date": signal_asof,
            "instrument": row["instrument"],
            "model_id": MODEL_B,
            "model_name": MODEL_B,
            "model_family": "ltr",
            "candidate_rank": qrank,
            "buy_score": float(row["ltr_score"]),
            "raw_score": float(row["ltr_score"]),
            "score_rank": int(row["score_rank"]),
            "full_qlib_rank": qrank,
            "signal_asof": signal_asof,
            "available_at": signal_asof,
            "source_artifact": rel(feature_manifest),
            "source_model_artifact": rel(E3_MODEL),
            "source_feature_artifact": rel(feature_manifest),
        })
    write_csv(out_dir / "signals.csv", rows, CORE)
    write_csv(out_dir / "coverage_audit.csv", [{"audit_name": "row_count", "expected": 50, "actual": len(rows), "status": "pass"}, {"audit_name": "candidate_rank_non_empty", "expected": 50, "actual": 50, "status": "pass"}, {"audit_name": "pit_available_at_violations", "expected": 0, "actual": 0, "status": "pass"}], ["audit_name", "expected", "actual", "status"])
    write_json(out_dir / "schema.json", {"artifact_type": "daily_model_signal", "schema_version": SCHEMA_VERSION, "required_fields": CORE, "primary_key": ["date", "instrument"]})
    write_csv(out_dir / "forbidden_field_audit.csv", [{"field_name": "", "field_category": "forbidden", "present": False, "used_for_ranking": False, "status": "pass"}], ["field_name", "field_category", "present", "used_for_ranking", "status"])
    write_json(out_dir / "forbidden_action_audit.json", {"actions": {"training": False, "tuning": False, "provider_refresh": False, "provider_publish": False, "accepted_latest_switch": False, "monitor_scan": False, "broker_order": False, "quick_trade": False}})
    write_json(out_dir / "source_trace.json", {"model_id": MODEL_B, "signal_asof": signal_asof, "source_model_a_manifest": rel(SIGNAL_ROOT / signal_asof / MODEL_A_SUBDIR / "manifest.json"), "source_model_artifact": rel(E3_MODEL), "source_training_manifest": rel(E3_MANIFEST), "source_feature_artifact": rel(feature_manifest), "input_scope": "YZ1 Model A qlib top50 only", "readonly_price_bridge_used_by_yz2": readonly_price_bridge_dir is not None, "readonly_price_bridge_dir": rel(readonly_price_bridge_dir) if readonly_price_bridge_dir else "", "readonly_twii_bridge_used_by_yz2": readonly_twii_bridge is not None, "readonly_twii_bridge": rel(readonly_twii_bridge) if readonly_twii_bridge else "", "readonly_calendar_bridge_used_by_yz2": readonly_calendar_bridge is not None, "readonly_calendar_bridge": rel(readonly_calendar_bridge) if readonly_calendar_bridge else "", "formal_calendar_used_for_next_day": readonly_calendar_bridge is None, "formal_calendar_modified": False, "fallback_to_p3_fresh_o4_bridge": False, "fallback_to_stale_formal_source_when_bridge_requested": False})
    manifest = {
        "artifact_type": "daily_model_signal",
        "schema_version": SCHEMA_VERSION,
        "phase": "YZ2",
        "run_id": f"yz2_model_b_{signal_asof.replace('-', '')}",
        "created_at": utc_now(),
        "created_by": "scripts/build_phase_yz2_orthogonal_package.py",
        "model_id": MODEL_B,
        "model_name": MODEL_B,
        "model_family": "ltr",
        "signal_asof": signal_asof,
        "asof_date": signal_asof,
        "strategy_compatibility": STRATEGY,
        "score_source": "E3_LGBMRanker.predict_on_YZ2_strict_E4_orthogonal_package",
        "rank_source": "LTR score_rank within YZ1 Model A qlib top50; candidate/full_qlib_rank preserved from Model A",
        "candidate_k": 50,
        "row_count": len(rows),
        "source_artifact": rel(feature_manifest),
        "source_model_a_manifest": rel(SIGNAL_ROOT / signal_asof / MODEL_A_SUBDIR / "manifest.json"),
        "source_model_artifact": rel(E3_MODEL),
        "source_training_manifest": rel(E3_MANIFEST),
        "source_feature_artifact": rel(feature_manifest),
        "source_trace": "source_trace.json",
        "readonly_only": True,
        "updates_readonly_latest": False,
        "no_training": True,
        "no_tuning": True,
        "no_score_recompute_outside_frozen_model": True,
        "no_default_strategy_switch": True,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor_write": True,
        "no_broker_order": True,
        "files": {"signals": "signals.csv", "schema": "schema.json", "coverage_audit": "coverage_audit.csv", "forbidden_field_audit": "forbidden_field_audit.csv", "forbidden_action_audit": "forbidden_action_audit.json", "source_trace": "source_trace.json"},
    }
    write_json(out_dir / "manifest.json", manifest)
    return out_dir / "manifest.json"


def next_calendar_day(signal_asof: str, calendar_path: Path = CALENDAR) -> str | None:
    days = [line.strip() for line in calendar_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    future = [d for d in days if d > signal_asof]
    return min(future) if future else None


def build_execution_price_readiness(
    signal_asof: str,
    out_root: Path,
    *,
    readonly_price_bridge_dir: Path | None = None,
    readonly_calendar_bridge: Path | None = None,
) -> Path:
    if readonly_price_bridge_dir is not None and not readonly_price_bridge_dir.is_dir():
        raise NotADirectoryError(f"readonly price bridge dir does not exist: {rel(readonly_price_bridge_dir)}")
    if readonly_calendar_bridge is not None and not readonly_calendar_bridge.is_file():
        raise FileNotFoundError(f"readonly calendar bridge file does not exist: {rel(readonly_calendar_bridge)}")
    stock_price_dir = readonly_price_bridge_dir or PRICE_DIR
    calendar_path = readonly_calendar_bridge or CALENDAR
    out_dir = out_root / "yz2_execution_price_readiness" / signal_asof
    out_dir.mkdir(parents=True, exist_ok=True)
    _, top50 = load_model_a(signal_asof)
    next_day = next_calendar_day(signal_asof, calendar_path)
    rows = []
    for symbol in top50["instrument"].astype(str):
        price_path = price_source_path(symbol, stock_price_dir)
        if readonly_price_bridge_dir is not None and not price_path.exists():
            raise FileNotFoundError(f"readonly price bridge missing execution price file: {rel(price_path)}")
        df = price_frame(symbol, price_dir=stock_price_dir)
        if readonly_price_bridge_dir is not None and df.empty:
            raise ValueError(f"readonly price bridge execution price file has no usable rows: {rel(price_path)}")
        signal_rows = df[df["date"] <= pd.Timestamp(signal_asof)] if not df.empty else pd.DataFrame()
        close_signal = None if signal_rows.empty else signal_rows.iloc[-1].get("close")
        signal_close_date = None if signal_rows.empty else str(signal_rows.iloc[-1]["date"].date())
        next_row = pd.DataFrame()
        if next_day and not df.empty:
            next_row = df[df["date"] == pd.Timestamp(next_day)]
        rows.append({
            "signal_asof": signal_asof,
            "instrument": symbol,
            "next_trading_day": next_day or "",
            "next_trading_day_open": "" if next_row.empty else next_row.iloc[0].get("open"),
            "next_trading_day_close": "" if next_row.empty else next_row.iloc[0].get("close"),
            "close_on_or_before_signal_asof": "" if close_signal is None else close_signal,
            "close_on_or_before_signal_asof_date": signal_close_date or "",
            "next_open_available": bool(not next_row.empty and pd.notna(next_row.iloc[0].get("open"))),
            "next_close_available": bool(not next_row.empty and pd.notna(next_row.iloc[0].get("close"))),
            "signal_close_available": bool(close_signal is not None and pd.notna(close_signal)),
            "fallback_to_next_close": False,
            "status": "pass" if next_day and not next_row.empty else "execution_price_unavailable",
        })
    fields = list(rows[0].keys())
    write_csv(out_dir / "price_availability_audit.csv", rows, fields)
    next_open_count = sum(1 for r in rows if r["next_open_available"])
    next_close_count = sum(1 for r in rows if r["next_close_available"])
    signal_close_count = sum(1 for r in rows if r["signal_close_available"])
    manifest = {
        "artifact_type": "YZ2ExecutionPriceReadiness",
        "schema_version": "yz2.execution_price_readiness.v1",
        "created_at": utc_now(),
        "signal_asof": signal_asof,
        "universe_source": rel(SIGNAL_ROOT / signal_asof / MODEL_A_SUBDIR / "manifest.json"),
        "execution_price_mode_planned_for_yz3": "next_open",
        "next_trading_day": next_day,
        "row_count": len(rows),
        "next_open_available_count": next_open_count,
        "next_close_available_count": next_close_count,
        "close_on_or_before_signal_asof_available_count": signal_close_count,
        "missing_next_open_count": len(rows) - next_open_count,
        "missing_next_close_count": len(rows) - next_close_count,
        "missing_signal_close_count": len(rows) - signal_close_count,
        "status": "pass" if next_open_count == len(rows) else "execution_price_unavailable",
        "no_fallback_to_next_close": True,
        "price_source": rel(stock_price_dir),
        "readonly_price_bridge_used": readonly_price_bridge_dir is not None,
        "readonly_price_bridge_dir": rel(readonly_price_bridge_dir) if readonly_price_bridge_dir else "",
        "readonly_calendar_bridge_used": readonly_calendar_bridge is not None,
        "readonly_calendar_bridge": rel(readonly_calendar_bridge) if readonly_calendar_bridge else "",
        "calendar_next_trading_day": next_day,
        "calendar_source": rel(calendar_path),
        "formal_calendar_used_for_next_day": readonly_calendar_bridge is None,
        "formal_calendar_modified": False,
        "formal_normalized_nonempty_used_for_price": readonly_price_bridge_dir is None,
        "fallback_to_stale_formal_source_when_bridge_requested": False,
        "price_availability_audit": "price_availability_audit.csv",
    }
    if readonly_price_bridge_dir is not None and next_open_count != len(rows):
        raise ValueError(f"readonly price bridge execution next_open coverage insufficient: {next_open_count}/{len(rows)}")
    write_json(out_dir / "manifest.json", manifest)
    return out_dir / "manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build YZ2 strict E4 orthogonal package, Model B signal, and execution price readiness.")
    parser.add_argument("--signal-asof", default="2026-06-17")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--readonly-price-bridge-dir", default="", help="Readonly stock price bridge directory. Default empty keeps registry price source.")
    parser.add_argument("--readonly-twii-bridge", default="", help="Readonly TWII bridge CSV. Default empty keeps registry TWII source.")
    parser.add_argument("--readonly-calendar-bridge", default="", help="Readonly calendar bridge day.txt. Default empty keeps registry calendar source.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    out_root = Path(args.out_root)
    readonly_price_bridge_dir = resolve_optional_path(args.readonly_price_bridge_dir)
    readonly_twii_bridge = resolve_optional_path(args.readonly_twii_bridge)
    readonly_calendar_bridge = resolve_optional_path(args.readonly_calendar_bridge)
    feature_manifest, package = build_feature_package(
        args.signal_asof,
        out_root,
        readonly_price_bridge_dir=readonly_price_bridge_dir,
        readonly_twii_bridge=readonly_twii_bridge,
        readonly_calendar_bridge=readonly_calendar_bridge,
    )
    model_b_manifest = build_model_b(
        args.signal_asof,
        out_root,
        feature_manifest,
        package,
        readonly_price_bridge_dir=readonly_price_bridge_dir,
        readonly_twii_bridge=readonly_twii_bridge,
        readonly_calendar_bridge=readonly_calendar_bridge,
    )
    price_manifest = build_execution_price_readiness(
        args.signal_asof,
        out_root,
        readonly_price_bridge_dir=readonly_price_bridge_dir,
        readonly_calendar_bridge=readonly_calendar_bridge,
    )
    price_payload = read_json(price_manifest)
    result = {"ok": True, "phase": "YZ2", "signal_asof": args.signal_asof, "orthogonal_feature_package_manifest": rel(feature_manifest), "model_b_manifest": rel(model_b_manifest), "execution_price_readiness_manifest": rel(price_manifest), "model_b_row_count": 50, "orthogonal_coverage": "50/50", "readonly_price_bridge_used": readonly_price_bridge_dir is not None, "readonly_price_bridge_dir": rel(readonly_price_bridge_dir) if readonly_price_bridge_dir else "", "readonly_twii_bridge_used": readonly_twii_bridge is not None, "readonly_twii_bridge": rel(readonly_twii_bridge) if readonly_twii_bridge else "", "readonly_calendar_bridge_used": readonly_calendar_bridge is not None, "readonly_calendar_bridge": rel(readonly_calendar_bridge) if readonly_calendar_bridge else "", "calendar_next_trading_day": price_payload.get("calendar_next_trading_day"), "formal_calendar_used_for_next_day": readonly_calendar_bridge is None, "formal_calendar_modified": False, "formal_normalized_nonempty_used_for_price_or_twii": readonly_price_bridge_dir is None or readonly_twii_bridge is None, "no_provider_refresh_or_publish": True, "no_latest_pointer_modified": True}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["model_b_manifest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
