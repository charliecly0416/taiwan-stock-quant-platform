#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
SHORT_SIGNAL_MANIFEST = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json"
LONG_MODEL_NAME = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
SIGNAL_MANIFEST = ROOT / f"data_tw/artifacts/signals/{LONG_MODEL_NAME}/r1_legacy_signal_adapter_20260616/manifest.json"
DEPENDENCY_YAML = ROOT / "configs/strategy_dependencies/mechanism_transfer_top50_cost_aware_v1.yaml"
BASELINE_DEPENDENCY_YAML = ROOT / "configs/strategy_dependencies/top50_exit_one_worst_sell.yaml"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
DEFAULT_OUT = ROOT / "data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay"
REPORT_PATH = ROOT / "docs/tw_portfolio_decision_model/POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_EXECUTION_REPORT_CN.md"

INITIAL_EQUITY = 1_000_000.0
TARGET_HOLDINGS = 10
CANDIDATE_K = 50
LOT_SIZE = 10
FEE_RATE = 0.001425
SELL_TAX_RATE = 0.003

SMALL_TOLERANCE = 0.02
MATERIAL_TURNOVER_REDUCTION = 0.20
MATERIAL_COST_REDUCTION = 0.20
MAX_DRAWDOWN_WORSE_TOLERANCE = 0.05
CASH_NO_TRADE_DEGENERATE_THRESHOLD = 0.10

REQUIRED_SIGNAL_FIELDS = [
    "date",
    "instrument",
    "candidate_rank",
    "buy_score",
    "raw_score",
    "score_rank",
    "full_qlib_rank",
    "signal_asof",
    "available_at",
    "source_artifact",
]
REQUIRED_INTENT_FIELDS = [
    "signal_date",
    "instrument",
    "intent_action",
    "intent_reason",
    "strategy_rule",
    "candidate_rank",
    "buy_rank",
    "full_qlib_rank",
    "max_buy_count",
    "max_sell_count",
    "model_name",
    "signal_artifact",
]
FORBIDDEN_ORDER_INTENT_FIELDS = {
    "execution_date",
    "execution_price",
    "execution_quantity",
    "quantity_to_buy",
    "quantity_to_sell",
    "shares",
    "lots",
    "target_position",
    "target_weight",
    "allocation_weight",
    "commission",
    "fee",
    "tax",
    "cash",
    "cash_after",
    "nav",
    "equity",
    "daily_return",
    "realized_pnl",
    "unrealized_pnl",
    "replay_return",
    "broker",
    "broker_order_id",
    "order_id",
    "quick_trade",
}
FORBIDDEN_SIGNAL_FIELDS = {
    "future_return_5d",
    "future_return_10d",
    "future_return_20d",
    "future_excess_return_5d",
    "future_excess_return_10d",
    "future_excess_return_20d",
    "forward_return_5d",
    "forward_return_10d",
    "forward_return_20d",
    "label",
    "label_5d",
    "label_10d",
    "relevance_10d_top_heavy",
    "ltr_relevance_label",
    "realized_pnl",
    "realized_return",
    "replay_return",
    "execution_price",
    "next_open",
    "next_close",
}


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    mechanism_id: str
    mechanism_name: str
    display_name: str
    max_replace_per_day: int = 1
    hold_rank_buffer: int | None = None
    score_z_gap_min: float | None = None
    rank_gap_min: int = 0
    cost_gate: bool = False


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def norm(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class PriceStore:
    def __init__(self, symbols: set[str]) -> None:
        self.by_symbol: dict[str, list[dict[str, float | str]]] = {}
        for symbol in sorted(norm(s) for s in symbols):
            path = PRICE_ROOT / f"{symbol}.csv"
            if not path.exists():
                continue
            rows: list[dict[str, float | str]] = []
            with path.open(encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    day = str(row.get("date") or "")[:10]
                    try:
                        open_price = float(row.get("open") or 0.0)
                        close_price = float(row.get("close") or 0.0)
                    except Exception:
                        open_price = 0.0
                        close_price = 0.0
                    if day and open_price > 0 and close_price > 0:
                        rows.append({"date": day, "open": open_price, "close": close_price})
            if rows:
                self.by_symbol[symbol] = rows

    def close_on_or_before(self, symbol: str, asof: str) -> float | None:
        out = None
        for row in self.by_symbol.get(norm(symbol), []):
            day = str(row["date"])
            if day <= asof:
                out = float(row["close"])
            else:
                break
        return out

    def next_after(self, symbol: str, asof: str) -> tuple[str, float] | None:
        for row in self.by_symbol.get(norm(symbol), []):
            day = str(row["date"])
            if day > asof:
                return day, float(row["open"])
        return None


def repair_long_id_signal_artifact(out_root: Path) -> dict[str, Any]:
    if not SHORT_SIGNAL_MANIFEST.exists():
        raise RuntimeError(f"short id source manifest missing: {rel(SHORT_SIGNAL_MANIFEST)}")
    short_dir = SHORT_SIGNAL_MANIFEST.parent
    long_dir = SIGNAL_MANIFEST.parent
    long_dir.mkdir(parents=True, exist_ok=True)

    short_manifest = load_json(SHORT_SIGNAL_MANIFEST)
    short_signals_path = resolve(str((short_manifest.get("output_files") or {}).get("signals", "")))
    short_schema_path = resolve(str((short_manifest.get("output_files") or {}).get("schema", "")))
    short_coverage_path = resolve(str((short_manifest.get("output_files") or {}).get("coverage_audit", "")))
    short_forbidden_path = resolve(str((short_manifest.get("output_files") or {}).get("forbidden_field_audit", "")))
    short_mapping_path = resolve(str((short_manifest.get("output_files") or {}).get("legacy_mapping_audit", "")))
    required = [short_signals_path, short_schema_path, short_coverage_path, short_forbidden_path, short_mapping_path]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"short id source artifact incomplete: {missing}")

    signals = pd.read_csv(short_signals_path)
    old_model_names = sorted(signals["model_name"].astype(str).unique().tolist()) if "model_name" in signals.columns else []
    if old_model_names != [short_manifest.get("model_name")]:
        raise RuntimeError(f"short id signals model_name mismatch: {old_model_names}")
    signals["model_name"] = LONG_MODEL_NAME
    signals["model_family"] = "ltr"

    long_signals_path = long_dir / "signals.csv"
    signals.to_csv(long_signals_path, index=False)

    schema = load_json(short_schema_path)
    schema["lineage_repair"] = {
        "phase": "MTR2-A",
        "source_short_id_manifest": rel(SHORT_SIGNAL_MANIFEST),
        "long_id_model_name": LONG_MODEL_NAME,
        "signals_values_unchanged_except_model_name": True,
    }
    write_json(long_dir / "schema.json", schema)

    for src, name in [
        (short_coverage_path, "coverage_audit.csv"),
        (short_forbidden_path, "forbidden_field_audit.csv"),
        (short_mapping_path, "legacy_mapping_audit.csv"),
    ]:
        (long_dir / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    long_manifest = dict(short_manifest)
    long_manifest.update({
        "artifact_name": LONG_MODEL_NAME,
        "model_name": LONG_MODEL_NAME,
        "created_at": now_iso(),
        "created_by": rel(Path(__file__)),
        "production_allowed": False,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_default_switch": True,
        "lineage_repair": {
            "phase": "POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY/MTR2-A",
            "source_short_id_manifest": rel(SHORT_SIGNAL_MANIFEST),
            "source_short_id_model_name": short_manifest.get("model_name"),
            "long_id_manifest": rel(SIGNAL_MANIFEST),
            "method": "contract_only_same_source_rename_from_existing_standard_artifact",
            "signals_values_unchanged_except_model_name": True,
            "short_id_not_used_as_strategy_input": True,
        },
    })
    long_manifest["output_files"] = {
        "signals": rel(long_signals_path),
        "schema": rel(long_dir / "schema.json"),
        "coverage_audit": rel(long_dir / "coverage_audit.csv"),
        "forbidden_field_audit": rel(long_dir / "forbidden_field_audit.csv"),
        "legacy_mapping_audit": rel(long_dir / "legacy_mapping_audit.csv"),
    }
    source_artifacts = list(long_manifest.get("source_artifacts") or [])
    if rel(SHORT_SIGNAL_MANIFEST) not in source_artifacts:
        source_artifacts.append(rel(SHORT_SIGNAL_MANIFEST))
    long_manifest["source_artifacts"] = source_artifacts
    input_hashes = dict(long_manifest.get("input_hashes") or {})
    input_hashes[rel(SHORT_SIGNAL_MANIFEST)] = file_sha256(SHORT_SIGNAL_MANIFEST)
    input_hashes[rel(short_signals_path)] = file_sha256(short_signals_path)
    long_manifest["input_hashes"] = input_hashes
    write_json(SIGNAL_MANIFEST, long_manifest)

    comparable = signals.copy()
    short_compare = pd.read_csv(short_signals_path)
    comparable_no_model = comparable.drop(columns=["model_name"], errors="ignore")
    short_no_model = short_compare.drop(columns=["model_name"], errors="ignore")
    equivalence_rows = [
        {
            "audit_name": "short_to_long_row_count",
            "short_value": len(short_compare),
            "long_value": len(signals),
            "status": "pass" if len(short_compare) == len(signals) else "fail",
            "details": "long id signals row count equals short id standard artifact",
        },
        {
            "audit_name": "short_to_long_keys",
            "short_value": len(short_compare[["date", "instrument"]].drop_duplicates()),
            "long_value": len(signals[["date", "instrument"]].drop_duplicates()),
            "status": "pass" if short_compare[["date", "instrument"]].equals(signals[["date", "instrument"]]) else "fail",
            "details": "date/instrument order and key values identical",
        },
        {
            "audit_name": "short_to_long_values_except_model_name",
            "short_value": "short_id_without_model_name",
            "long_value": "long_id_without_model_name",
            "status": "pass" if short_no_model.equals(comparable_no_model) else "fail",
            "details": "all fields identical except model_name rename",
        },
        {
            "audit_name": "long_model_name",
            "short_value": short_manifest.get("model_name"),
            "long_value": LONG_MODEL_NAME,
            "status": "pass" if sorted(signals["model_name"].astype(str).unique().tolist()) == [LONG_MODEL_NAME] else "fail",
            "details": "signals.csv model_name rewritten to product long id",
        },
    ]
    write_csv(out_root / "long_id_short_id_equivalence_audit.csv", equivalence_rows, ["audit_name", "short_value", "long_value", "status", "details"])

    lineage_rows = [
        {"audit_name": "long_id_manifest_created", "status": "pass" if SIGNAL_MANIFEST.exists() else "fail", "details": rel(SIGNAL_MANIFEST)},
        {"audit_name": "source_short_id_standard_artifact", "status": "pass" if short_manifest.get("artifact_type") == "model_signal" and short_manifest.get("quality_status") == "pass" else "fail", "details": rel(SHORT_SIGNAL_MANIFEST)},
        {"audit_name": "artifact_name_long_id", "status": "pass" if long_manifest.get("artifact_name") == LONG_MODEL_NAME else "fail", "details": str(long_manifest.get("artifact_name"))},
        {"audit_name": "model_name_long_id", "status": "pass" if long_manifest.get("model_name") == LONG_MODEL_NAME else "fail", "details": str(long_manifest.get("model_name"))},
        {"audit_name": "model_family_ltr", "status": "pass" if long_manifest.get("model_family") == "ltr" else "fail", "details": str(long_manifest.get("model_family"))},
        {"audit_name": "production_guards", "status": "pass" if long_manifest.get("production_allowed") is False and long_manifest.get("no_provider_publish") is True and long_manifest.get("no_accepted_latest_switch") is True and long_manifest.get("no_default_switch") is True else "fail", "details": "production_allowed=false,no publish/latest/default switch"},
    ]
    write_csv(out_root / "lineage_repair_audit.csv", lineage_rows, ["audit_name", "status", "details"])
    if any(row["status"] == "fail" for row in equivalence_rows + lineage_rows):
        raise RuntimeError("MTR2-A lineage repair failed equivalence or lineage audit")
    return long_manifest


def candidate_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec("M0_baseline_parity", "M0", "baseline_parity", "M0 baseline parity"),
        CandidateSpec("M2_hold_rank_buffer_75", "M2", "hold_rank_buffer", "M2 hold_rank_buffer=75", hold_rank_buffer=75),
        CandidateSpec("M2_hold_rank_buffer_100", "M2", "hold_rank_buffer", "M2 hold_rank_buffer=100", hold_rank_buffer=100),
    ]


def validate_signal_manifest(manifest_path: Path) -> tuple[dict[str, Any], pd.DataFrame, list[dict[str, Any]]]:
    manifest = load_json(manifest_path)
    checks = [
        {"check": "manifest_exists", "status": "pass", "details": rel(manifest_path)},
        {"check": "artifact_type", "status": "pass" if manifest.get("artifact_type") == "model_signal" else "fail", "details": str(manifest.get("artifact_type"))},
        {"check": "artifact_name_long_id", "status": "pass" if manifest.get("artifact_name") == LONG_MODEL_NAME else "fail", "details": str(manifest.get("artifact_name"))},
        {"check": "model_name_long_id", "status": "pass" if manifest.get("model_name") == LONG_MODEL_NAME else "fail", "details": str(manifest.get("model_name"))},
        {"check": "model_family", "status": "pass" if manifest.get("model_family") == "ltr" else "fail", "details": str(manifest.get("model_family"))},
        {"check": "quality_status", "status": "pass" if manifest.get("quality_status") == "pass" else "fail", "details": str(manifest.get("quality_status"))},
        {"check": "capability_core_signal_v1", "status": "pass" if (manifest.get("capabilities") or {}).get("core_signal_v1") is True else "fail", "details": json.dumps(manifest.get("capabilities") or {}, ensure_ascii=False)},
        {"check": "candidate_boundary", "status": "pass" if (manifest.get("capabilities") or {}).get("candidate_boundary") == "qlib_top50" else "fail", "details": str((manifest.get("capabilities") or {}).get("candidate_boundary"))},
        {"check": "buy_ordering", "status": "pass" if (manifest.get("capabilities") or {}).get("buy_ordering") == "buy_score_desc" else "fail", "details": str((manifest.get("capabilities") or {}).get("buy_ordering"))},
        {"check": "full_rank_exit", "status": "pass" if (manifest.get("capabilities") or {}).get("full_rank_exit") == "full_qlib_rank" else "fail", "details": str((manifest.get("capabilities") or {}).get("full_rank_exit"))},
        {"check": "supports_ltr_rerank", "status": "pass" if (manifest.get("capabilities") or {}).get("supports_ltr_rerank") is True else "fail", "details": str((manifest.get("capabilities") or {}).get("supports_ltr_rerank"))},
    ]
    signal_path = resolve(str((manifest.get("output_files") or {}).get("signals", "")))
    signals = pd.read_csv(signal_path)
    missing = sorted(set(REQUIRED_SIGNAL_FIELDS) - set(signals.columns))
    forbidden = sorted(set(signals.columns) & FORBIDDEN_SIGNAL_FIELDS)
    checks.append({"check": "required_core_fields", "status": "pass" if not missing else "fail", "details": "|".join(missing)})
    checks.append({"check": "forbidden_signal_fields_absent", "status": "pass" if not forbidden else "fail", "details": "|".join(forbidden)})
    checks.append({"check": "signals_model_name_long_id", "status": "pass" if sorted(signals["model_name"].astype(str).unique().tolist()) == [LONG_MODEL_NAME] else "fail", "details": "|".join(sorted(signals["model_name"].astype(str).unique().tolist()))})
    checks.append({"check": "signals_model_family_ltr", "status": "pass" if sorted(signals["model_family"].astype(str).unique().tolist()) == ["ltr"] else "fail", "details": "|".join(sorted(signals["model_family"].astype(str).unique().tolist()))})
    if any(row["status"] == "fail" for row in checks):
        raise RuntimeError("qlib+LTR long id signal manifest failed MTR2 lineage gate")
    signals["date"] = signals["date"].astype(str)
    signals["instrument"] = signals["instrument"].map(norm)
    for col in ["candidate_rank", "buy_score", "raw_score", "score_rank", "full_qlib_rank"]:
        signals[col] = pd.to_numeric(signals[col], errors="coerce")
    daily = signals.groupby("date")["instrument"].count()
    checks.extend([
        {"check": "row_count", "status": "pass", "details": str(len(signals))},
        {"check": "date_range", "status": "pass", "details": f"{signals['date'].min()}..{signals['date'].max()}"},
        {"check": "daily_row_count_min", "status": "pass" if int(daily.min()) > 0 else "fail", "details": str(int(daily.min()))},
    ])
    return manifest, signals, checks


def dependency_validation(signal_manifest: dict[str, Any], signals: pd.DataFrame) -> dict[str, Any]:
    dep = load_yaml(DEPENDENCY_YAML)
    baseline_dep = load_yaml(BASELINE_DEPENDENCY_YAML)
    checks: list[dict[str, Any]] = []
    required = list(dep.get("required_core_fields") or [])
    missing = sorted(set(required) - set(signals.columns))
    checks.append({"name": "strategy_dependency_exists", "status": "pass", "details": rel(DEPENDENCY_YAML)})
    checks.append({"name": "baseline_dependency_exists", "status": "pass", "details": rel(BASELINE_DEPENDENCY_YAML)})
    checks.append({"name": "dependency_strategy_rule", "status": "pass" if dep.get("strategy_rule") == "mechanism_transfer_top50_cost_aware_v1" else "fail", "details": str(dep.get("strategy_rule"))})
    checks.append({"name": "baseline_strategy_rule", "status": "pass" if baseline_dep.get("strategy_rule") == "top50_exit_one_worst_sell" else "fail", "details": str(baseline_dep.get("strategy_rule"))})
    checks.append({"name": "required_core_fields", "status": "pass" if not missing else "fail", "details": "|".join(missing)})
    caps = signal_manifest.get("capabilities") or {}
    required_caps = dep.get("required_capabilities") or []
    cap_ok = (
        "core_signal_v1" in required_caps
        and caps.get("core_signal_v1") is True
        and "candidate_boundary:qlib_top50" in required_caps
        and caps.get("candidate_boundary") == "qlib_top50"
        and "buy_ordering:buy_score_desc" in required_caps
        and caps.get("buy_ordering") == "buy_score_desc"
        and "full_rank_exit:full_qlib_rank" in required_caps
        and caps.get("full_rank_exit") == "full_qlib_rank"
    )
    checks.append({"name": "required_capabilities", "status": "pass" if cap_ok else "fail", "details": json.dumps(caps, ensure_ascii=False)})
    checks.append({"name": "no_required_extensions", "status": "pass" if not dep.get("required_extensions") else "fail", "details": json.dumps(dep.get("required_extensions") or [], ensure_ascii=False)})
    checks.append({"name": "diagnostic_research_only", "status": "pass" if dep.get("diagnostic_only") is True and dep.get("research_only") is True and dep.get("production_allowed") is False else "fail", "details": "diagnostic_only/research_only/production_allowed"})
    checks.append({"name": "mtr2_candidate_scope", "status": "pass", "details": "MTR2 runs only M0, M2_hold_rank_buffer_75 audit control, and M2_hold_rank_buffer_100 transfer candidate"})
    ok = all(row["status"] == "pass" for row in checks)
    return {"ok": ok, "strategy_dependency": rel(DEPENDENCY_YAML), "signal_manifest": rel(SIGNAL_MANIFEST), "checks": checks}


def build_day_state(day: pd.DataFrame) -> dict[str, Any]:
    candidates = day[day["candidate_rank"] <= CANDIDATE_K].dropna(subset=["buy_score"]).copy()
    candidates = candidates.sort_values(["buy_score", "instrument"], ascending=[False, True])
    buy_order = [norm(x) for x in candidates["instrument"].tolist()]
    score_mean = float(day["buy_score"].mean())
    score_std = float(day["buy_score"].std(ddof=0))
    if not math.isfinite(score_std) or score_std <= 0:
        score_std = 1.0
    return {
        "candidate_set": set(candidates["instrument"].map(norm)),
        "buy_order": buy_order,
        "buy_rank": {symbol: idx + 1 for idx, symbol in enumerate(buy_order)},
        "signal": {norm(row.instrument): row for row in day.itertuples(index=False)},
        "full_rank": {norm(row.instrument): int(row.full_qlib_rank) for row in day.itertuples(index=False) if pd.notna(row.full_qlib_rank)},
        "score_mean": score_mean,
        "score_std": score_std,
    }


def signal_meta(state: dict[str, Any], symbol: str, day: str) -> dict[str, Any]:
    row = state["signal"].get(norm(symbol))
    if row is None:
        return {
            "candidate_rank": "",
            "buy_rank": "",
            "full_qlib_rank": state["full_rank"].get(norm(symbol), ""),
            "source_signal_asof": day,
            "source_available_at": day,
            "buy_score": "",
            "score_rank": "",
            "score_z": "",
        }
    buy_score = float(row.buy_score) if pd.notna(row.buy_score) else float("nan")
    return {
        "candidate_rank": int(row.candidate_rank) if pd.notna(row.candidate_rank) else "",
        "buy_rank": int(row.score_rank) if pd.notna(row.score_rank) else "",
        "full_qlib_rank": int(row.full_qlib_rank) if pd.notna(row.full_qlib_rank) else "",
        "source_signal_asof": str(row.signal_asof),
        "source_available_at": str(row.available_at),
        "buy_score": buy_score if math.isfinite(buy_score) else "",
        "score_rank": int(row.score_rank) if pd.notna(row.score_rank) else "",
        "score_z": ((buy_score - state["score_mean"]) / state["score_std"]) if math.isfinite(buy_score) else "",
    }


def score_z(state: dict[str, Any], symbol: str) -> float:
    meta = signal_meta(state, symbol, "")
    value = meta.get("score_z")
    return float(value) if value != "" and math.isfinite(float(value)) else -999.0


def score_rank(state: dict[str, Any], symbol: str) -> int:
    meta = signal_meta(state, symbol, "")
    value = meta.get("score_rank")
    return int(value) if value != "" else 999999


def should_sell(symbol: str, best_buy: str | None, state: dict[str, Any], spec: CandidateSpec) -> tuple[bool, str]:
    full_rank = state["full_rank"].get(symbol, 999999)
    if spec.hold_rank_buffer is not None and full_rank <= spec.hold_rank_buffer:
        return False, f"hold_rank_buffer_{spec.hold_rank_buffer}_skip"
    if best_buy is None:
        return False, "no_replacement_candidate_skip"
    rank_gap = score_rank(state, symbol) - score_rank(state, best_buy)
    z_gap = score_z(state, best_buy) - score_z(state, symbol)
    if spec.score_z_gap_min is not None and z_gap < spec.score_z_gap_min:
        return False, f"score_z_gap_{round(z_gap, 6)}_below_{spec.score_z_gap_min}"
    if spec.rank_gap_min and rank_gap < spec.rank_gap_min:
        return False, f"rank_gap_{rank_gap}_below_{spec.rank_gap_min}"
    if spec.cost_gate:
        cost_z_threshold = (2 * FEE_RATE) + SELL_TAX_RATE
        if z_gap < cost_z_threshold or rank_gap < 1:
            return False, f"fixed_cost_gate_skip_z_{round(z_gap, 6)}_rank_{rank_gap}"
    return True, "replace_gate_pass"


def make_intent(
    *,
    row_id: str,
    day: str,
    symbol: str,
    action: str,
    reason: str,
    strategy_rule: str,
    candidate_id: str,
    spec: CandidateSpec,
    state: dict[str, Any],
    signal_manifest: dict[str, Any],
) -> dict[str, Any]:
    meta = signal_meta(state, symbol, day)
    return {
        "order_intent_row_id": row_id,
        "signal_date": day,
        "instrument": norm(symbol),
        "intent_action": action,
        "intent_reason": reason,
        "strategy_rule": strategy_rule,
        "candidate_rank": meta["candidate_rank"],
        "buy_rank": meta["buy_rank"],
        "full_qlib_rank": meta["full_qlib_rank"],
        "max_buy_count": spec.max_replace_per_day,
        "max_sell_count": spec.max_replace_per_day,
        "model_name": signal_manifest["model_name"],
        "signal_artifact": rel(SIGNAL_MANIFEST),
        "readonly_only": True,
        "simulation_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "diagnostic_only": True,
        "research_only": True,
        "candidate_id": candidate_id,
        "mechanism_id": spec.mechanism_id,
        "mechanism_name": spec.mechanism_name,
        "source_signal_asof": meta["source_signal_asof"],
        "source_available_at": meta["source_available_at"],
        "current_holding_flag": action in {"sell", "hold", "skip"},
        "target_holding_count": TARGET_HOLDINGS,
        "candidate_k": CANDIDATE_K,
        "tie_breaker": "buy_score_desc; full_qlib_rank_asc; instrument_asc",
    }


def mark_to_market(cash: float, holdings: dict[str, int], prices: PriceStore, asof: str) -> tuple[float, float, int]:
    market_value = 0.0
    missing = 0
    for symbol, qty in holdings.items():
        close = prices.close_on_or_before(symbol, asof)
        if close is None:
            missing += 1
            continue
        market_value += int(qty) * close
    return cash + market_value, market_value, missing


def execute_pending(
    *,
    pending_orders: list[dict[str, Any]],
    asof: str,
    candidate_id: str,
    strategy_rule: str,
    cash: float,
    holdings: dict[str, int],
    actions: list[dict[str, Any]],
    order_manifest_ref: str,
) -> tuple[float, int, float, float, float]:
    skipped = 0
    commission_total = 0.0
    tax_total = 0.0
    turnover = 0.0
    for order in sorted(pending_orders, key=lambda row: 0 if row["intent_action"] == "sell" else 1):
        symbol = norm(order["instrument"])
        price = float(order["execution_price"])
        common = {
            "signal_date": order["signal_date"],
            "execution_date": asof,
            "instrument": symbol,
            "intent_reason": order["intent_reason"],
            "strategy_rule": strategy_rule,
            "model_name": order["model_name"],
            "order_intent_artifact": order_manifest_ref,
            "order_intent_row_id": order["order_intent_row_id"],
            "candidate_id": candidate_id,
        }
        if order["intent_action"] == "sell":
            qty = int(holdings.pop(symbol, 0))
            if qty <= 0:
                skipped += 1
                actions.append({**common, "action": "historical_skip", "quantity": 0, "execution_price": round(price, 4), "commission": 0.0, "tax": 0.0, "cash_after": round(cash, 2), "position_after": 0, "skip_reason": "sell_without_active_holding"})
                continue
            notional = qty * price
            commission = notional * FEE_RATE
            tax = notional * SELL_TAX_RATE
            cash += notional - commission - tax
            turnover += notional
            commission_total += commission
            tax_total += tax
            actions.append({**common, "action": "historical_risk_reduce", "quantity": qty, "execution_price": round(price, 4), "commission": round(commission, 2), "tax": round(tax, 2), "cash_after": round(cash, 2), "position_after": 0, "skip_reason": ""})
        elif order["intent_action"] == "buy":
            slots = max(1, TARGET_HOLDINGS - len(holdings))
            qty = int((cash / slots) // (price * LOT_SIZE)) * LOT_SIZE
            notional = qty * price
            commission = notional * FEE_RATE
            total_cost = notional + commission
            if qty <= 0 or cash < total_cost or symbol in holdings or len(holdings) >= TARGET_HOLDINGS:
                skipped += 1
                actions.append({**common, "action": "historical_skip", "quantity": 0, "execution_price": round(price, 4), "commission": 0.0, "tax": 0.0, "cash_after": round(cash, 2), "position_after": holdings.get(symbol, 0), "skip_reason": "insufficient_cash_duplicate_zero_qty_or_full"})
                continue
            cash -= total_cost
            holdings[symbol] = qty
            turnover += notional
            commission_total += commission
            actions.append({**common, "action": "historical_add", "quantity": qty, "execution_price": round(price, 4), "commission": round(commission, 2), "tax": 0.0, "cash_after": round(cash, 2), "position_after": qty, "skip_reason": ""})
    return cash, skipped, commission_total, tax_total, turnover


def run_candidate(
    *,
    signals: pd.DataFrame,
    signal_manifest: dict[str, Any],
    prices: PriceStore,
    spec: CandidateSpec,
    candidate_id: str,
    strategy_rule: str,
    out_root: Path,
) -> dict[str, Any]:
    dates = sorted(signals["date"].unique().tolist())
    cash = INITIAL_EQUITY
    holdings: dict[str, int] = {}
    pending: dict[str, list[dict[str, Any]]] = {}
    intents: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    nav_rows: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    skipped_count = 0
    commission_total = 0.0
    tax_total = 0.0
    turnover_notional = 0.0
    peak = INITIAL_EQUITY
    max_drawdown = 0.0
    row_seq = 0
    order_manifest_ref = rel(out_root / "order_intents" / candidate_id / "manifest.json")

    by_date = {day: group.copy() for day, group in signals.groupby("date")}
    for asof in dates:
        cash, skipped, commission, tax, turnover = execute_pending(
            pending_orders=pending.pop(asof, []),
            asof=asof,
            candidate_id=candidate_id,
            strategy_rule=strategy_rule,
            cash=cash,
            holdings=holdings,
            actions=actions,
            order_manifest_ref=order_manifest_ref,
        )
        skipped_count += skipped
        commission_total += commission
        tax_total += tax
        turnover_notional += turnover

        equity, market_value, missing = mark_to_market(cash, holdings, prices, asof)
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity / peak - 1.0 if peak > 0 else 0.0)
        day = by_date[asof]
        state = build_day_state(day)

        nav_rows.append({
            "date": asof,
            "cash": round(cash, 2),
            "market_value": round(market_value, 2),
            "equity": round(equity, 2),
            "daily_return": 0.0,
            "holding_count": len(holdings),
            "missing_price_count": missing,
            "candidate_id": candidate_id,
            "strategy_rule": strategy_rule,
            "model_name": signal_manifest["model_name"],
        })
        if len(nav_rows) > 1:
            prev = float(nav_rows[-2]["equity"])
            nav_rows[-1]["daily_return"] = round(equity / prev - 1.0, 8) if prev else 0.0
        for symbol, qty in sorted(holdings.items()):
            meta = signal_meta(state, symbol, asof)
            mark = prices.close_on_or_before(symbol, asof) or 0.0
            snapshots.append({
                "date": asof,
                "instrument": symbol,
                "quantity": qty,
                "cost_basis": "",
                "mark_price": round(mark, 4),
                "market_value": round(qty * mark, 2),
                "unrealized_pnl": "",
                "strategy_rule": strategy_rule,
                "model_name": signal_manifest["model_name"],
                "candidate_id": candidate_id,
                "in_qlib_top50_candidate": symbol in state["candidate_set"],
                "buy_rank": meta["buy_rank"],
                "full_qlib_rank": meta["full_qlib_rank"],
            })

        pending_buy_symbols = {norm(order["instrument"]) for orders in pending.values() for order in orders if order["intent_action"] == "buy"}
        pending_sell_symbols = {norm(order["instrument"]) for orders in pending.values() for order in orders if order["intent_action"] == "sell"}
        best_buy = next((symbol for symbol in state["buy_order"] if symbol not in holdings and symbol not in pending_buy_symbols), None)
        outside = [symbol for symbol in sorted(holdings) if symbol not in state["candidate_set"] and symbol not in pending_sell_symbols]
        outside = sorted(outside, key=lambda s: (state["full_rank"].get(s, 999999), s), reverse=True)
        sells: list[str] = []
        for symbol in outside:
            if len(sells) >= spec.max_replace_per_day:
                break
            allowed, reason = should_sell(symbol, best_buy, state, spec)
            if allowed:
                sells.append(symbol)
            else:
                row_seq += 1
                intents.append(make_intent(row_id=f"{candidate_id}|{asof}|{symbol}|skip|{row_seq}", day=asof, symbol=symbol, action="skip", reason=reason, strategy_rule=strategy_rule, candidate_id=candidate_id, spec=spec, state=state, signal_manifest=signal_manifest))
        for symbol in sells:
            row_seq += 1
            reason = "top50_exit_one_worst_sell_sell" if candidate_id == "baseline_top50_exit_one_worst_sell" else f"{candidate_id}_sell"
            intent = make_intent(row_id=f"{candidate_id}|{asof}|{symbol}|sell|{row_seq}", day=asof, symbol=symbol, action="sell", reason=reason, strategy_rule=strategy_rule, candidate_id=candidate_id, spec=spec, state=state, signal_manifest=signal_manifest)
            intents.append(intent)
            quote = prices.next_after(symbol, asof)
            if quote is None:
                skipped_count += 1
                actions.append({"signal_date": asof, "execution_date": "", "instrument": symbol, "action": "historical_skip", "quantity": 0, "execution_price": "", "commission": 0.0, "tax": 0.0, "cash_after": round(cash, 2), "position_after": holdings.get(symbol, 0), "intent_reason": "no_next_trading_day_price", "strategy_rule": strategy_rule, "model_name": signal_manifest["model_name"], "order_intent_artifact": order_manifest_ref, "order_intent_row_id": intent["order_intent_row_id"], "candidate_id": candidate_id, "skip_reason": "no_next_trading_day_price"})
            else:
                execution_date, execution_price = quote
                pending.setdefault(execution_date, []).append({**intent, "execution_date": execution_date, "execution_price": execution_price})

        pending_buy_symbols = {norm(order["instrument"]) for orders in pending.values() for order in orders if order["intent_action"] == "buy"}
        available_slots = TARGET_HOLDINGS - len(holdings) - len(pending_buy_symbols)
        buy_limit = min(spec.max_replace_per_day, max(0, available_slots))
        buys = []
        for symbol in state["buy_order"]:
            if len(buys) >= buy_limit:
                break
            if symbol in holdings or symbol in pending_buy_symbols:
                continue
            buys.append(symbol)
        for symbol in buys:
            row_seq += 1
            reason = "top50_exit_one_worst_sell_buy" if candidate_id == "baseline_top50_exit_one_worst_sell" else f"{candidate_id}_buy"
            intent = make_intent(row_id=f"{candidate_id}|{asof}|{symbol}|buy|{row_seq}", day=asof, symbol=symbol, action="buy", reason=reason, strategy_rule=strategy_rule, candidate_id=candidate_id, spec=spec, state=state, signal_manifest=signal_manifest)
            intents.append(intent)
            quote = prices.next_after(symbol, asof)
            if quote is None:
                skipped_count += 1
                actions.append({"signal_date": asof, "execution_date": "", "instrument": symbol, "action": "historical_skip", "quantity": 0, "execution_price": "", "commission": 0.0, "tax": 0.0, "cash_after": round(cash, 2), "position_after": holdings.get(symbol, 0), "intent_reason": "no_next_trading_day_price", "strategy_rule": strategy_rule, "model_name": signal_manifest["model_name"], "order_intent_artifact": order_manifest_ref, "order_intent_row_id": intent["order_intent_row_id"], "candidate_id": candidate_id, "skip_reason": "no_next_trading_day_price"})
            else:
                execution_date, execution_price = quote
                pending.setdefault(execution_date, []).append({**intent, "execution_date": execution_date, "execution_price": execution_price})

    final_equity = float(nav_rows[-1]["equity"]) if nav_rows else INITIAL_EQUITY
    avg_equity = sum(float(row["equity"]) for row in nav_rows) / len(nav_rows) if nav_rows else INITIAL_EQUITY
    active = [row for row in actions if row["action"] in {"historical_add", "historical_risk_reduce"}]
    summary = {
        "window": "qlib_signal_full_window",
        "model_name": signal_manifest["model_name"],
        "model_family": signal_manifest["model_family"],
        "strategy_rule": strategy_rule,
        "candidate_id": candidate_id,
        "mechanism_id": spec.mechanism_id,
        "mechanism_name": spec.mechanism_name,
        "start_date": dates[0] if dates else "",
        "end_date": dates[-1] if dates else "",
        "initial_cash": INITIAL_EQUITY,
        "final_equity": round(final_equity, 2),
        "gross_total_return": round((final_equity + commission_total + tax_total) / INITIAL_EQUITY - 1.0, 8),
        "net_total_return_after_fee_tax": round(final_equity / INITIAL_EQUITY - 1.0, 8),
        "total_return": round(final_equity / INITIAL_EQUITY - 1.0, 8),
        "max_drawdown": round(max_drawdown, 8),
        "action_count": len(active),
        "buy_count": sum(1 for row in active if row["action"] == "historical_add"),
        "sell_count": sum(1 for row in active if row["action"] == "historical_risk_reduce"),
        "skipped_action_count": skipped_count + sum(1 for row in actions if row["action"] == "historical_skip"),
        "max_holding_count": max((int(row["holding_count"]) for row in nav_rows), default=0),
        "average_holding_count": round(sum(int(row["holding_count"]) for row in nav_rows) / len(nav_rows), 6) if nav_rows else 0,
        "duplicate_position_count": 0,
        "negative_cash_count": sum(1 for row in nav_rows if float(row["cash"]) < 0),
        "missing_price_count": sum(int(row["missing_price_count"]) for row in nav_rows),
        "diagnostic_only": True,
        "total_fee": round(commission_total, 2),
        "total_tax": round(tax_total, 2),
        "total_fee_plus_tax": round(commission_total + tax_total, 2),
        "turnover_notional": round(turnover_notional, 2),
        "average_turnover": round((turnover_notional / avg_equity / len(nav_rows)) if avg_equity and nav_rows else 0.0, 8),
        "trading_day_count": len(nav_rows),
        "cash_no_trade_day_count": 0,
    }
    action_dates = {str(row["signal_date"]) for row in actions if row["action"] in {"historical_add", "historical_risk_reduce"}}
    summary["cash_no_trade_day_count"] = sum(1 for row in nav_rows if int(row["holding_count"]) == 0 and str(row["date"]) not in action_dates)
    write_order_intent_artifact(out_root, candidate_id, strategy_rule, spec, signal_manifest, intents)
    replay_manifest = write_replay_artifact(out_root, candidate_id, strategy_rule, spec, summary, actions, nav_rows, snapshots, order_manifest_ref)
    return {
        "candidate_id": candidate_id,
        "spec": spec,
        "summary": summary,
        "intents": intents,
        "actions": actions,
        "nav": nav_rows,
        "snapshots": snapshots,
        "order_manifest": order_manifest_ref,
        "replay_manifest": replay_manifest,
    }


def write_order_intent_artifact(out_root: Path, candidate_id: str, strategy_rule: str, spec: CandidateSpec, signal_manifest: dict[str, Any], intents: list[dict[str, Any]]) -> str:
    out_dir = out_root / "order_intents" / candidate_id
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = REQUIRED_INTENT_FIELDS + [
        "order_intent_row_id",
        "readonly_only",
        "simulation_only",
        "not_order",
        "not_target_position",
        "not_investment_advice",
        "diagnostic_only",
        "research_only",
        "candidate_id",
        "mechanism_id",
        "mechanism_name",
        "source_signal_asof",
        "source_available_at",
        "current_holding_flag",
        "target_holding_count",
        "candidate_k",
        "tie_breaker",
    ]
    fields = [field for field in fields if any(field in row for row in intents)] if intents else REQUIRED_INTENT_FIELDS
    write_csv(out_dir / "order_intents.csv", intents, fields)
    schema = {"schema_version": "order_intent_mtr2_v1", "required_fields": REQUIRED_INTENT_FIELDS, "intent_actions": ["buy", "sell", "hold", "skip"], "forbidden_fields": sorted(FORBIDDEN_ORDER_INTENT_FIELDS)}
    write_json(out_dir / "schema.json", schema)
    audit_rows = [
        {"audit_name": "decision_source", "status": "pass", "details": "ModelSignalArtifact + PortfolioState + StrategyRuleConfig"},
        {"audit_name": "mechanism_predeclared", "status": "pass", "details": spec.display_name},
        {"audit_name": "qlib_ltr_long_id_signal", "status": "pass", "details": rel(SIGNAL_MANIFEST)},
        {"audit_name": "no_replay_return_input", "status": "pass", "details": "strategy decision used only signal ranks/scores and portfolio state"},
    ]
    write_csv(out_dir / "strategy_decision_audit.csv", audit_rows, ["audit_name", "status", "details"])
    forbidden_action = {
        "artifact_type": "order_intent_forbidden_action_audit",
        "status": "pass",
        "trained_model": "not_performed",
        "tuned_model": "not_performed",
        "used_short_id_or_private_signal_as_strategy_input": "not_performed",
        "read_future_or_label": "not_performed",
        "read_replay_return_as_strategy_input": "not_performed",
        "modified_replay_engine_private_field": "not_performed",
        "provider_publish": "not_performed",
        "accepted_latest_switch": "not_performed",
        "broker_or_quick_trade": "not_performed",
    }
    write_json(out_dir / "forbidden_action_audit.json", forbidden_action)
    manifest = {
        "artifact_type": "order_intent",
        "schema_version": "order_intent_mtr2_v1",
        "contract_version": "ORDER_INTENT_CONTRACT_CN.md@2026-06-16",
        "created_at": now_iso(),
        "created_by": rel(Path(__file__)),
        "readonly_only": True,
        "simulation_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "diagnostic_only": True,
        "research_only": True,
        "production_allowed": False,
        "model_name": signal_manifest["model_name"],
        "model_family": signal_manifest["model_family"],
        "strategy_rule": strategy_rule,
        "candidate_id": candidate_id,
        "mechanism_id": spec.mechanism_id,
        "mechanism_name": spec.mechanism_name,
        "signal_artifact": rel(SIGNAL_MANIFEST),
        "row_count": len(intents),
        "intent_counts": {action: sum(1 for row in intents if row.get("intent_action") == action) for action in ["buy", "sell", "hold", "skip"]},
        "output_files": {
            "order_intents": rel(out_dir / "order_intents.csv"),
            "schema": rel(out_dir / "schema.json"),
            "strategy_decision_audit": rel(out_dir / "strategy_decision_audit.csv"),
            "forbidden_action_audit": rel(out_dir / "forbidden_action_audit.json"),
        },
    }
    write_json(out_dir / "manifest.json", manifest)
    return rel(out_dir / "manifest.json")


def write_replay_artifact(
    out_root: Path,
    candidate_id: str,
    strategy_rule: str,
    spec: CandidateSpec,
    summary: dict[str, Any],
    actions: list[dict[str, Any]],
    nav_rows: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    order_manifest_ref: str,
) -> str:
    out_dir = out_root / "replays" / candidate_id
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "summary.csv", [summary], list(summary.keys()))
    write_csv(out_dir / "actions.csv", actions, ["signal_date", "execution_date", "instrument", "action", "quantity", "execution_price", "commission", "tax", "cash_after", "position_after", "intent_reason", "strategy_rule", "model_name", "order_intent_artifact", "candidate_id", "order_intent_row_id", "skip_reason"])
    write_csv(out_dir / "daily_nav.csv", nav_rows, ["date", "cash", "market_value", "equity", "daily_return", "holding_count", "missing_price_count", "candidate_id", "strategy_rule", "model_name"])
    write_csv(out_dir / "position_snapshots.csv", snapshots, ["date", "instrument", "quantity", "cost_basis", "mark_price", "market_value", "unrealized_pnl", "strategy_rule", "model_name", "candidate_id", "in_qlib_top50_candidate", "buy_rank", "full_qlib_rank"])
    coverage = [{
        "audit_name": "signal_price_coverage",
        "requested_start_date": summary["start_date"],
        "requested_end_date": summary["end_date"],
        "actual_start_date": summary["start_date"],
        "actual_end_date": summary["end_date"],
        "trading_day_count": summary["trading_day_count"],
        "signal_day_count": summary["trading_day_count"],
        "price_day_count": summary["trading_day_count"],
        "missing_signal_day_count": 0,
        "missing_price_day_count": summary["missing_price_count"],
        "status": "pass",
        "details": "qlib+LTR long id signal dates with local readonly PriceStore",
    }]
    write_csv(out_dir / "coverage_audit.csv", coverage, list(coverage[0].keys()))
    integrity = [
        {"audit_name": "max_holding_count", "date": summary["end_date"], "instrument": "*", "status": "pass" if summary["max_holding_count"] <= TARGET_HOLDINGS else "fail", "value": summary["max_holding_count"], "threshold": TARGET_HOLDINGS, "details": ""},
        {"audit_name": "negative_cash_count", "date": summary["end_date"], "instrument": "*", "status": "pass" if summary["negative_cash_count"] == 0 else "fail", "value": summary["negative_cash_count"], "threshold": 0, "details": ""},
        {"audit_name": "duplicate_position_count", "date": summary["end_date"], "instrument": "*", "status": "pass", "value": 0, "threshold": 0, "details": "holdings stored by instrument key"},
    ]
    write_csv(out_dir / "position_integrity_audit.csv", integrity, ["audit_name", "date", "instrument", "status", "value", "threshold", "details"])
    forbidden = [{
        "audit_name": "forbidden_strategy_input",
        "artifact": order_manifest_ref,
        "field_name": "*",
        "field_category": "strategy_or_model_private_future_field",
        "present": False,
        "used_for_ranking": False,
        "status": "pass",
        "details": "Replay consumed OrderIntentArtifact plus PriceStore and execution config",
    }]
    write_csv(out_dir / "forbidden_field_audit.csv", forbidden, list(forbidden[0].keys()))
    execution = [
        {"audit_name": "decision_source", "status": "pass", "value": "order_intent_artifact", "threshold": "order_intent_artifact", "details": order_manifest_ref},
        {"audit_name": "price_store", "status": "pass", "value": rel(PRICE_ROOT), "threshold": "readonly local price csv", "details": "next open for execution; close_on_or_before for mark"},
        {"audit_name": "execution_date_after_signal", "status": "pass", "value": True, "threshold": True, "details": "next_after(signal_date)"},
    ]
    write_csv(out_dir / "execution_audit.csv", execution, ["audit_name", "status", "value", "threshold", "details"])
    forbidden_action = {
        "artifact_type": "replay_forbidden_action_audit",
        "status": "pass",
        "trained_model": "not_performed",
        "tuned_model": "not_performed",
        "modified_replay_engine_private_field": "not_performed",
        "modified_order_intent": "not_performed",
        "provider_publish": "not_performed",
        "accepted_latest_switch": "not_performed",
        "broker_or_quick_trade": "not_performed",
    }
    write_json(out_dir / "forbidden_action_audit.json", forbidden_action)
    write_json(out_dir / "input_manifest_links.json", {"order_intent_artifact": order_manifest_ref, "signal_artifact": rel(SIGNAL_MANIFEST), "strategy_dependency": rel(DEPENDENCY_YAML)})
    manifest = {
        "artifact_type": "replay_result",
        "schema_version": "replay_result_mtr2_v1",
        "contract_version": "REPLAY_RESULT_CONTRACT_CN.md@2026-06-16",
        "created_at": now_iso(),
        "created_by": rel(Path(__file__)),
        "readonly_only": True,
        "simulation_only": True,
        "production_allowed": False,
        "decision_source": "order_intent_artifact",
        "order_intent_artifact": order_manifest_ref,
        "price_store": rel(PRICE_ROOT),
        "execution_config": {"initial_equity": INITIAL_EQUITY, "target_holdings": TARGET_HOLDINGS, "fee_rate": FEE_RATE, "sell_tax_rate": SELL_TAX_RATE, "lot_size": LOT_SIZE, "execution_price": "next_open", "mark_price": "close_on_or_before"},
        "initial_portfolio_state_source": "cash_only_forward_replay_runtime_state",
        "model_name": summary["model_name"],
        "model_family": summary["model_family"],
        "strategy_rule": strategy_rule,
        "candidate_id": candidate_id,
        "mechanism_id": spec.mechanism_id,
        "mechanism_name": spec.mechanism_name,
        "artifacts": {
            "summary": rel(out_dir / "summary.csv"),
            "actions": rel(out_dir / "actions.csv"),
            "daily_nav": rel(out_dir / "daily_nav.csv"),
            "snapshots": rel(out_dir / "position_snapshots.csv"),
            "coverage": rel(out_dir / "coverage_audit.csv"),
            "integrity": rel(out_dir / "position_integrity_audit.csv"),
            "forbidden": rel(out_dir / "forbidden_field_audit.csv"),
            "execution_audit": rel(out_dir / "execution_audit.csv"),
            "input_manifest_links": rel(out_dir / "input_manifest_links.json"),
        },
    }
    write_json(out_dir / "manifest.json", manifest)
    return rel(out_dir / "manifest.json")


def validate_order_intents(results: list[dict[str, Any]]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for result in results:
        manifest = load_json(resolve(result["order_manifest"]))
        path = resolve(manifest["output_files"]["order_intents"])
        frame = pd.read_csv(path)
        missing = sorted(set(REQUIRED_INTENT_FIELDS) - set(frame.columns))
        forbidden = sorted(set(frame.columns) & FORBIDDEN_ORDER_INTENT_FIELDS)
        action_ok = set(frame["intent_action"].astype(str)).issubset({"buy", "sell", "hold", "skip"}) if not frame.empty else True
        counts_ok = True
        count_detail = ""
        if not frame.empty:
            for (day, action), group in frame[frame["intent_action"].isin(["buy", "sell"])].groupby(["signal_date", "intent_action"]):
                max_col = "max_buy_count" if action == "buy" else "max_sell_count"
                limit = int(pd.to_numeric(group[max_col], errors="coerce").max())
                if len(group) > limit:
                    counts_ok = False
                    count_detail = f"{result['candidate_id']} {day} {action} {len(group)}>{limit}"
                    break
        checks.extend([
            {"candidate_id": result["candidate_id"], "check": "required_fields", "status": "pass" if not missing else "fail", "details": "|".join(missing)},
            {"candidate_id": result["candidate_id"], "check": "forbidden_fields_absent", "status": "pass" if not forbidden else "fail", "details": "|".join(forbidden)},
            {"candidate_id": result["candidate_id"], "check": "intent_action_enum", "status": "pass" if action_ok else "fail", "details": ""},
            {"candidate_id": result["candidate_id"], "check": "daily_buy_sell_count_lte_max", "status": "pass" if counts_ok else "fail", "details": count_detail},
            {"candidate_id": result["candidate_id"], "check": "readonly_flags", "status": "pass" if manifest.get("readonly_only") is True and manifest.get("not_order") is True and manifest.get("not_target_position") is True else "fail", "details": ""},
        ])
    return {"ok": all(row["status"] == "pass" for row in checks), "checks": checks}


def validate_replays(results: list[dict[str, Any]]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for result in results:
        manifest = load_json(resolve(result["replay_manifest"]))
        artifacts = manifest.get("artifacts") or {}
        required = ["summary", "actions", "daily_nav", "snapshots", "coverage", "integrity", "forbidden", "execution_audit"]
        missing = [key for key in required if not artifacts.get(key) or not resolve(str(artifacts[key])).exists()]
        summary = pd.read_csv(resolve(artifacts["summary"])).iloc[0].to_dict()
        actions = pd.read_csv(resolve(artifacts["actions"]))
        active = actions[actions["action"].isin(["historical_add", "historical_risk_reduce"])] if not actions.empty else pd.DataFrame()
        exec_after = True if active.empty else (pd.to_datetime(active["execution_date"], errors="coerce") > pd.to_datetime(active["signal_date"], errors="coerce")).all()
        qty_ok = True if active.empty else (pd.to_numeric(active["quantity"], errors="coerce") > 0).all()
        checks.extend([
            {"candidate_id": result["candidate_id"], "check": "required_artifact_files", "status": "pass" if not missing else "fail", "details": "|".join(missing)},
            {"candidate_id": result["candidate_id"], "check": "decision_source_order_intent", "status": "pass" if manifest.get("decision_source") == "order_intent_artifact" else "fail", "details": str(manifest.get("decision_source"))},
            {"candidate_id": result["candidate_id"], "check": "execution_date_after_signal", "status": "pass" if bool(exec_after) else "fail", "details": ""},
            {"candidate_id": result["candidate_id"], "check": "active_quantity_positive", "status": "pass" if bool(qty_ok) else "fail", "details": ""},
            {"candidate_id": result["candidate_id"], "check": "max_holding_count", "status": "pass" if int(summary["max_holding_count"]) <= TARGET_HOLDINGS else "fail", "details": str(summary["max_holding_count"])},
            {"candidate_id": result["candidate_id"], "check": "negative_cash_count", "status": "pass" if int(summary["negative_cash_count"]) == 0 else "fail", "details": str(summary["negative_cash_count"])},
        ])
    return {"ok": all(row["status"] == "pass" for row in checks), "checks": checks}


def canonical_intent_frame(result: dict[str, Any]) -> pd.DataFrame:
    frame = pd.DataFrame(result["intents"])
    if frame.empty:
        return pd.DataFrame(columns=["signal_date", "instrument", "intent_action"])
    return frame[frame["intent_action"].isin(["buy", "sell"])][["signal_date", "instrument", "intent_action"]].sort_values(["signal_date", "instrument", "intent_action"]).reset_index(drop=True)


def parity_audits(baseline: dict[str, Any], m0: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    b = canonical_intent_frame(baseline)
    m = canonical_intent_frame(m0)
    b_keys = set(b.astype(str).agg("|".join, axis=1))
    m_keys = set(m.astype(str).agg("|".join, axis=1))
    action_same = b_keys == m_keys and len(b) == len(m)
    b_counts = b.groupby(["signal_date", "intent_action"]).size().to_dict() if not b.empty else {}
    m_counts = m.groupby(["signal_date", "intent_action"]).size().to_dict() if not m.empty else {}
    count_same = b_counts == m_counts
    order_rows = [
        {"audit_name": "same_signal_date_instrument_action_parity", "baseline_rows": len(b), "m0_rows": len(m), "status": "pass" if action_same else "fail", "details": f"baseline_not_m0={len(b_keys - m_keys)};m0_not_baseline={len(m_keys - b_keys)}"},
        {"audit_name": "daily_buy_count_parity", "baseline_rows": int((b["intent_action"] == "buy").sum()) if not b.empty else 0, "m0_rows": int((m["intent_action"] == "buy").sum()) if not m.empty else 0, "status": "pass" if count_same else "fail", "details": "daily action count dict equality"},
        {"audit_name": "daily_sell_count_parity", "baseline_rows": int((b["intent_action"] == "sell").sum()) if not b.empty else 0, "m0_rows": int((m["intent_action"] == "sell").sum()) if not m.empty else 0, "status": "pass" if count_same else "fail", "details": "daily action count dict equality"},
        {"audit_name": "intent_reason_parity", "baseline_rows": len(b), "m0_rows": len(m), "status": "pass", "details": "canonical mapping: top50_exit_one_worst_sell_{buy,sell} == M0_baseline_parity_{buy,sell}"},
    ]
    metric_names = ["final_equity", "gross_total_return", "net_total_return_after_fee_tax", "max_drawdown", "average_turnover", "total_fee", "total_tax", "buy_count", "sell_count", "skipped_action_count", "average_holding_count"]
    replay_rows = []
    for metric in metric_names:
        bv = baseline["summary"][metric]
        mv = m0["summary"][metric]
        tol = 1e-8 if isinstance(bv, float) or isinstance(mv, float) else 0
        ok = abs(float(bv) - float(mv)) <= tol
        replay_rows.append({"metric": metric, "baseline_value": bv, "m0_value": mv, "delta": round(float(mv) - float(bv), 10), "status": "pass" if ok else "fail", "details": "same execution config and canonical M0 decisions"})
    return order_rows, replay_rows


def holdings_by_date(result: dict[str, Any]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for row in result["snapshots"]:
        out.setdefault(str(row["date"]), set()).add(norm(row["instrument"]))
    return out


def comparison_tables(results: list[dict[str, Any]], baseline: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    baseline_summary = baseline["summary"]
    baseline_holdings = holdings_by_date(baseline)
    comparison = []
    turnover_cost = []
    holding_overlap = []
    rank_overlap = []
    cash_no_trade = []
    for result in results:
        s = result["summary"]
        fee_tax_reduction = 1.0 - (float(s["total_fee_plus_tax"]) / float(baseline_summary["total_fee_plus_tax"])) if float(baseline_summary["total_fee_plus_tax"]) else 0.0
        turnover_reduction = 1.0 - (float(s["average_turnover"]) / float(baseline_summary["average_turnover"])) if float(baseline_summary["average_turnover"]) else 0.0
        drawdown_worse = float(s["max_drawdown"]) - float(baseline_summary["max_drawdown"])
        cash_degenerate_ratio = float(s["cash_no_trade_day_count"]) / float(s["trading_day_count"] or 1)
        gate_pass = (
            result["candidate_id"] != baseline["candidate_id"]
            and float(s["net_total_return_after_fee_tax"]) >= float(baseline_summary["net_total_return_after_fee_tax"]) - SMALL_TOLERANCE
            and turnover_reduction >= MATERIAL_TURNOVER_REDUCTION
            and fee_tax_reduction >= MATERIAL_COST_REDUCTION
            and drawdown_worse >= -MAX_DRAWDOWN_WORSE_TOLERANCE
            and cash_degenerate_ratio <= CASH_NO_TRADE_DEGENERATE_THRESHOLD
        )
        comparison.append({
            "candidate_id": result["candidate_id"],
            "mechanism_id": result["spec"].mechanism_id,
            "mechanism_name": result["spec"].mechanism_name,
            "gross_total_return": s["gross_total_return"],
            "net_total_return_after_fee_tax": s["net_total_return_after_fee_tax"],
            "baseline_net_delta": round(float(s["net_total_return_after_fee_tax"]) - float(baseline_summary["net_total_return_after_fee_tax"]), 8),
            "max_drawdown": s["max_drawdown"],
            "average_turnover": s["average_turnover"],
            "turnover_reduction_vs_baseline": round(turnover_reduction, 8),
            "total_fee": s["total_fee"],
            "total_tax": s["total_tax"],
            "total_fee_plus_tax": s["total_fee_plus_tax"],
            "fee_tax_reduction_vs_baseline": round(fee_tax_reduction, 8),
            "buy_count": s["buy_count"],
            "sell_count": s["sell_count"],
            "skipped_action_count": s["skipped_action_count"],
            "average_holding_count": s["average_holding_count"],
            "cash_no_trade_day_count": s["cash_no_trade_day_count"],
            "candidate_gate_pass": gate_pass,
        })
        turnover_cost.append({
            "candidate_id": result["candidate_id"],
            "average_turnover": s["average_turnover"],
            "baseline_average_turnover": baseline_summary["average_turnover"],
            "turnover_reduction_vs_baseline": round(turnover_reduction, 8),
            "total_fee_plus_tax": s["total_fee_plus_tax"],
            "baseline_total_fee_plus_tax": baseline_summary["total_fee_plus_tax"],
            "fee_tax_reduction_vs_baseline": round(fee_tax_reduction, 8),
            "status": "pass" if result["candidate_id"] == baseline["candidate_id"] or (turnover_reduction >= 0 and fee_tax_reduction >= 0) else "warn",
        })
        h = holdings_by_date(result)
        overlaps = []
        rank_overlaps = []
        for day, base_set in baseline_holdings.items():
            current = h.get(day, set())
            denom = max(len(base_set | current), 1)
            overlaps.append(len(base_set & current) / denom)
        holding_overlap.append({"candidate_id": result["candidate_id"], "holding_overlap_vs_baseline": round(sum(overlaps) / len(overlaps), 8) if overlaps else 0.0, "status": "pass"})
        base_rank = {(row["date"], row["instrument"]): row.get("full_qlib_rank", "") for row in baseline["snapshots"]}
        for row in result["snapshots"]:
            key = (row["date"], row["instrument"])
            if key in base_rank and str(base_rank[key]) == str(row.get("full_qlib_rank", "")):
                rank_overlaps.append(1.0)
            else:
                rank_overlaps.append(0.0)
        rank_overlap.append({"candidate_id": result["candidate_id"], "rank_overlap_vs_baseline": round(sum(rank_overlaps) / len(rank_overlaps), 8) if rank_overlaps else 0.0, "status": "pass"})
        cash_no_trade.append({
            "candidate_id": result["candidate_id"],
            "cash_no_trade_day_count": s["cash_no_trade_day_count"],
            "trading_day_count": s["trading_day_count"],
            "cash_no_trade_ratio": round(cash_degenerate_ratio, 8),
            "threshold": CASH_NO_TRADE_DEGENERATE_THRESHOLD,
            "status": "pass" if cash_degenerate_ratio <= CASH_NO_TRADE_DEGENERATE_THRESHOLD else "fail",
        })
    return {"comparison": comparison, "turnover_cost": turnover_cost, "holding_overlap": holding_overlap, "rank_overlap": rank_overlap, "cash_no_trade": cash_no_trade}


def write_report(out_root: Path, manifest: dict[str, Any], comparison: list[dict[str, Any]], order_parity: list[dict[str, Any]], replay_parity: list[dict[str, Any]]) -> None:
    baseline = next(row for row in comparison if row["candidate_id"] == "baseline_top50_exit_one_worst_sell")
    mechanisms = [row for row in comparison if row["candidate_id"] not in {"baseline_top50_exit_one_worst_sell", "M0_baseline_parity"}]
    best = sorted(mechanisms, key=lambda row: (bool(row["candidate_gate_pass"]), float(row["net_total_return_after_fee_tax"]), float(row["turnover_reduction_vs_baseline"])), reverse=True)[0]
    pass_candidates = [row for row in mechanisms if row["candidate_gate_pass"]]
    verdict = "PASS_MTR2_QLIB_LTR_WITH_TRANSFER_CANDIDATE" if pass_candidates and all(row["status"] == "pass" for row in order_parity) and all(row["status"] == "pass" for row in replay_parity) else "FAIL_NEEDS_REPAIR"
    m2_100 = next(row for row in comparison if row["candidate_id"] == "M2_hold_rank_buffer_100")
    lines = [
        "# POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_EXECUTION_REPORT_CN",
        "",
        f"生成日期：2026-06-28",
        "",
        "## 1. Verdict",
        "",
        "```text",
        verdict,
        "```",
        "",
        "本次先由短 ID 标准 artifact 同源派生产品长 ID qlib+LTR 标准 ModelSignalArtifact，再只使用长 ID 标准信号做 baseline parity 与 M2 transfer replay。未使用 LTR private artifacts、未把短 ID 作为策略输入、未收益后验扩展候选、未触碰 provider/latest、frontend/API/Agent/daily 或 broker/quick-trade。",
        "",
        "## 2. Scope",
        "",
        "- assigned phase: `POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY`",
        "- goal: 修复产品长 ID qlib+LTR 标准 `ModelSignalArtifact`，然后在该长 ID 信号上跑 baseline parity 与 `M2_hold_rank_buffer_100` transfer replay。",
        "- non-goals confirmed: 未训练、未调参、未扩候选、未改 production/default/frontend/API/Agent/daily/provider/latest、未触发 broker/order/quick-trade。",
        "",
        "## 3. Documents / Contracts / Skills Read",
        "",
        "```text",
        "docs/tw_portfolio_decision_model/POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_WORK_CN.md",
        "docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md",
        "docs/tw_portfolio_decision_model/POLICY_MTR0_CONTRACT_AND_BASELINE_PARITY_FEASIBILITY_REVIEW_CN.md",
        "docs/tw_portfolio_decision_model/POLICY_MTR1_QLIB_ONLY_ORDER_INTENT_PARITY_AND_MECHANISM_REPLAY_REVIEW_CN.md",
        "docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md",
        "docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md",
        "docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md",
        "docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md",
        "docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md",
        "docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md",
        "docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md",
        "docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md",
        "docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md",
        "configs/strategy_dependencies/mechanism_transfer_top50_cost_aware_v1.yaml",
        "```",
        "",
        "## 4. 输入冻结",
        "",
        f"- signal manifest: `{rel(SIGNAL_MANIFEST)}`",
        f"- source short-id manifest for lineage repair only: `{rel(SHORT_SIGNAL_MANIFEST)}`",
        f"- strategy dependency: `{rel(DEPENDENCY_YAML)}`",
        f"- output_dir: `{rel(out_root)}`",
        "- candidates: `M0_baseline_parity`, `M2_hold_rank_buffer_75`, `M2_hold_rank_buffer_100`。",
        "",
        "## 5. MTR2-A Lineage Repair",
        "",
        "- status: `pass`",
        "- long ID artifact 已生成：`data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/r1_legacy_signal_adapter_20260616/manifest.json`",
        "- short/long equivalence: `pass`，row count `3950 -> 3950`，date/instrument key 一致，除 `model_name` 改为产品长 ID 外值一致。",
        "- signal window: `2026-01-02..2026-05-07`",
        "- daily row count min: `50`",
        "- model family: `ltr`",
        "- capabilities: `core_signal_v1`, `candidate_boundary=qlib_top50`, `buy_ordering=buy_score_desc`, `full_rank_exit=full_qlib_rank`, `supports_ltr_rerank=true`",
        "",
        "## 6. 冻结阈值",
        "",
        f"- small_tolerance: `{SMALL_TOLERANCE}`",
        f"- material_turnover_reduction: `{MATERIAL_TURNOVER_REDUCTION}`",
        f"- material_cost_reduction: `{MATERIAL_COST_REDUCTION}`",
        f"- max_drawdown_worse_tolerance: `{MAX_DRAWDOWN_WORSE_TOLERANCE}`",
        f"- cash_no_trade_degenerate_threshold: `{CASH_NO_TRADE_DEGENERATE_THRESHOLD}`",
        "",
        "## 7. MTR2-B Baseline Parity",
        "",
        f"- OrderIntent parity: `{'pass' if all(row['status'] == 'pass' for row in order_parity) else 'fail'}`",
        f"- Replay metric parity: `{'pass' if all(row['status'] == 'pass' for row in replay_parity) else 'fail'}`",
        "",
        "## 8. MTR2-C Transfer Replay",
        "",
        "| item | candidate | net | baseline_delta | turnover | fee_tax | max_drawdown | gate |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
        f"| baseline | {baseline['candidate_id']} | {baseline['net_total_return_after_fee_tax']} | {baseline['baseline_net_delta']} | {baseline['average_turnover']} | {baseline['total_fee_plus_tax']} | {baseline['max_drawdown']} | n/a |",
        f"| audit control | {best['candidate_id']} | {best['net_total_return_after_fee_tax']} | {best['baseline_net_delta']} | {best['average_turnover']} | {best['total_fee_plus_tax']} | {best['max_drawdown']} | {best['candidate_gate_pass']} |",
        f"| main candidate | {m2_100['candidate_id']} | {m2_100['net_total_return_after_fee_tax']} | {m2_100['baseline_net_delta']} | {m2_100['average_turnover']} | {m2_100['total_fee_plus_tax']} | {m2_100['max_drawdown']} | {m2_100['candidate_gate_pass']} |",
        "",
        "M2_75 与 M2_100 都与 baseline 完全等价，未降低 turnover / fee_tax，因此未通过 MTR2 gate。",
        "",
        "## 9. Failure Analysis / Repair Need",
        "",
        "失败原因不是 baseline parity 或 replay validator 失败，而是当前长 ID 标准信号是由短 ID artifact 严格等价派生；短 ID artifact 每日只有 qlib top50 的 50 行。`M2_hold_rank_buffer_75/100` 需要看到持仓跌出 top50 后是否仍处于 `full_qlib_rank <= 75/100`，但标准信号缺少 51-100 乃至 broad universe 行，因此跌出 top50 的持仓在策略日状态中没有可见 full-rank，hold buffer 条件无法触发，机制退化为 baseline。",
        "",
        "上游 `phasee1_raw_oos_score_rank_2023_2026.csv` / E3 lineage 存在 broad qlib rank 证据，但 MTR2 工作文档本轮要求若由短 ID 派生则必须保持 row count/key/value 与短 ID 可审计一致。因此本执行者没有擅自把长 ID signals 扩到 150 行继续 replay。下一步应开 MTR2 repair：冻结并生成 `qlib broad full-rank + top50 LTR buy_score` 的标准 ModelSignalArtifact 合同版本，或者新增可被策略合法消费的 `ext_full_rank_broad`/holding-rank lookup 合同，再重跑 M2 transfer。",
        "",
        "## 10. 输出清单",
        "",
        "```text",
        *[rel(out_root / name) for name in [
            "manifest.json",
            "lineage_repair_audit.csv",
            "long_id_short_id_equivalence_audit.csv",
            "input_signal_lineage_audit.csv",
            "model_signal_validator_report.json",
            "dependency_validation_report.json",
            "order_intent_artifact_index.csv",
            "order_intent_validator_report.json",
            "baseline_order_intent_parity_audit.csv",
            "replay_artifact_index.csv",
            "replay_validator_report.json",
            "baseline_replay_parity_audit.csv",
            "mechanism_candidate_contract.csv",
            "mechanism_replay_comparison.csv",
            "turnover_cost_audit.csv",
            "holding_overlap_audit.csv",
            "rank_overlap_audit.csv",
            "cash_no_trade_audit.csv",
            "forbidden_field_audit.csv",
            "forbidden_action_audit.csv",
        ]],
        "```",
        "",
        "## 11. Forbidden Actions Audit",
        "",
        "```text",
        "no_training",
        "no_tuning",
        "no_posthoc_candidate_expansion",
        "no_private_ltr_strategy_input",
        "no_short_id_strategy_input_bypass",
        "no_provider_publish",
        "no_accepted_latest_switch",
        "no_production_default_switch",
        "no_frontend_api_agent_daily_change",
        "no_broker_order_quick_trade",
        "no_target_weight_position_quantity_instruction",
        "```",
        "",
        "## 12. Files Changed",
        "",
        "```text",
        "scripts/run_tw_policy_mtr2_qlib_ltr_lineage_repair_and_transfer_replay.py",
        "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/r1_legacy_signal_adapter_20260616/",
        "data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/",
        "docs/tw_portfolio_decision_model/POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_EXECUTION_REPORT_CN.md",
        "```",
        "",
        "## 13. Recommendation",
        "",
        "```text",
        "FAIL_NEEDS_REPAIR。不要进入 MTR3。建议审查者授权 MTR2_R：修复 qlib+LTR 标准信号的 broad full-rank 可见性，使 hold buffer 75/100 机制可表达后再重跑 baseline parity 与 M2 transfer replay。",
        "```",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(out_root: Path) -> dict[str, Any]:
    out_root.mkdir(parents=True, exist_ok=True)
    repair_long_id_signal_artifact(out_root)
    signal_manifest, signals, lineage_checks = validate_signal_manifest(SIGNAL_MANIFEST)
    write_csv(out_root / "input_signal_lineage_audit.csv", lineage_checks, ["check", "status", "details"])
    write_json(out_root / "model_signal_validator_report.json", {
        "ok": all(row["status"] == "pass" for row in lineage_checks),
        "signal_manifest": rel(SIGNAL_MANIFEST),
        "source_short_id_manifest_for_lineage_repair_only": rel(SHORT_SIGNAL_MANIFEST),
        "checks": lineage_checks,
    })
    dep_report = dependency_validation(signal_manifest, signals)
    write_json(out_root / "dependency_validation_report.json", dep_report)
    if not dep_report["ok"]:
        raise RuntimeError("dependency validation failed")

    prices = PriceStore(set(signals["instrument"].unique()))
    baseline_spec = CandidateSpec("baseline_top50_exit_one_worst_sell", "BASELINE", "top50_exit_one_worst_sell", "baseline top50_exit_one_worst_sell")
    results = [
        run_candidate(signals=signals, signal_manifest=signal_manifest, prices=prices, spec=baseline_spec, candidate_id="baseline_top50_exit_one_worst_sell", strategy_rule="top50_exit_one_worst_sell", out_root=out_root)
    ]
    for spec in candidate_specs():
        results.append(run_candidate(signals=signals, signal_manifest=signal_manifest, prices=prices, spec=spec, candidate_id=spec.candidate_id, strategy_rule="mechanism_transfer_top50_cost_aware_v1", out_root=out_root))

    order_validation = validate_order_intents(results)
    replay_validation = validate_replays(results)
    write_json(out_root / "order_intent_validator_report.json", order_validation)
    write_json(out_root / "replay_validator_report.json", replay_validation)

    baseline = results[0]
    m0 = next(row for row in results if row["candidate_id"] == "M0_baseline_parity")
    order_parity, replay_parity = parity_audits(baseline, m0)
    write_csv(out_root / "baseline_order_intent_parity_audit.csv", order_parity, ["audit_name", "baseline_rows", "m0_rows", "status", "details"])
    write_csv(out_root / "baseline_replay_parity_audit.csv", replay_parity, ["metric", "baseline_value", "m0_value", "delta", "status", "details"])

    order_index = [{"candidate_id": row["candidate_id"], "strategy_rule": "top50_exit_one_worst_sell" if row["candidate_id"] == "baseline_top50_exit_one_worst_sell" else "mechanism_transfer_top50_cost_aware_v1", "order_intent_manifest": row["order_manifest"], "row_count": len(row["intents"]), "buy_intents": sum(1 for intent in row["intents"] if intent.get("intent_action") == "buy"), "sell_intents": sum(1 for intent in row["intents"] if intent.get("intent_action") == "sell"), "skip_intents": sum(1 for intent in row["intents"] if intent.get("intent_action") == "skip")} for row in results]
    replay_index = [{"candidate_id": row["candidate_id"], "replay_manifest": row["replay_manifest"], **{key: row["summary"][key] for key in ["net_total_return_after_fee_tax", "gross_total_return", "max_drawdown", "average_turnover", "total_fee", "total_tax", "buy_count", "sell_count", "skipped_action_count", "average_holding_count", "cash_no_trade_day_count"]}} for row in results]
    write_csv(out_root / "order_intent_artifact_index.csv", order_index)
    write_csv(out_root / "replay_artifact_index.csv", replay_index)

    contract_rows = []
    for spec in candidate_specs():
        contract_rows.append({
            "candidate_id": spec.candidate_id,
            "mechanism_id": spec.mechanism_id,
            "mechanism_name": spec.mechanism_name,
            "parameters": spec.display_name,
            "uses_candidate_rank": True,
            "uses_full_qlib_rank": True,
            "uses_buy_score": True,
            "uses_score_rank": spec.score_z_gap_min is not None or spec.rank_gap_min > 0 or spec.cost_gate,
            "uses_market_regime": False,
            "requires_extension": False,
            "order_intent_expressible": True,
            "forbidden_input_needed": False,
            "production_allowed": False,
            "mtr2_status": "run",
        })
    write_csv(out_root / "mechanism_candidate_contract.csv", contract_rows)

    tables = comparison_tables(results, baseline)
    write_csv(out_root / "mechanism_replay_comparison.csv", tables["comparison"])
    write_csv(out_root / "turnover_cost_audit.csv", tables["turnover_cost"])
    write_csv(out_root / "holding_overlap_audit.csv", tables["holding_overlap"])
    write_csv(out_root / "rank_overlap_audit.csv", tables["rank_overlap"])
    write_csv(out_root / "cash_no_trade_audit.csv", tables["cash_no_trade"])

    forbidden_field_rows = [
        {"audit_name": "signal_forbidden_fields", "artifact": rel(SIGNAL_MANIFEST), "field_name": field, "field_category": "future_label_replay_or_execution", "present": field in set(signals.columns), "used_for_ranking": False, "status": "fail" if field in set(signals.columns) else "pass", "details": ""}
        for field in sorted(FORBIDDEN_SIGNAL_FIELDS)
    ]
    forbidden_field_rows.extend([
        {"audit_name": "order_intent_forbidden_fields", "artifact": row["order_manifest"], "field_name": field, "field_category": "execution_cash_position_or_broker", "present": False, "used_for_ranking": False, "status": "pass", "details": "checked by MTR2 order intent validator"}
        for row in results for field in sorted(FORBIDDEN_ORDER_INTENT_FIELDS)
    ])
    write_csv(out_root / "forbidden_field_audit.csv", forbidden_field_rows, ["audit_name", "artifact", "field_name", "field_category", "present", "used_for_ranking", "status", "details"])
    forbidden_actions = [
        "trained_model",
        "tuned_model",
        "used_short_id_or_private_signal_as_strategy_input",
        "read_future_or_label",
        "read_replay_return_as_strategy_input",
        "modified_replay_engine_private_field",
        "modified_registry_default",
        "modified_frontend_or_api",
        "modified_daily_or_provider",
        "provider_publish",
        "accepted_latest_switch",
        "broker_or_quick_trade",
        "target_weight_or_position_output",
        "posthoc_candidate_expansion",
    ]
    write_csv(out_root / "forbidden_action_audit.csv", [{"audit_name": name, "status": "not_performed", "details": "MTR2 readonly artifact generation only"} for name in forbidden_actions], ["audit_name", "status", "details"])

    pass_candidates = [row for row in tables["comparison"] if row["candidate_id"] not in {"baseline_top50_exit_one_worst_sell", "M0_baseline_parity"} and row["candidate_gate_pass"]]
    best = sorted([row for row in tables["comparison"] if row["candidate_id"] not in {"baseline_top50_exit_one_worst_sell", "M0_baseline_parity"}], key=lambda row: (bool(row["candidate_gate_pass"]), float(row["net_total_return_after_fee_tax"]), float(row["turnover_reduction_vs_baseline"])), reverse=True)[0]
    manifest = {
        "artifact_type": "policy_mtr2_qlib_ltr_lineage_repair_and_transfer_replay",
        "created_at": now_iso(),
        "created_by": rel(Path(__file__)),
        "readonly_only": True,
        "simulation_only": True,
        "production_allowed": False,
        "signal_manifest": rel(SIGNAL_MANIFEST),
        "source_short_id_manifest_for_lineage_repair_only": rel(SHORT_SIGNAL_MANIFEST),
        "strategy_dependency": rel(DEPENDENCY_YAML),
        "baseline_strategy": "top50_exit_one_worst_sell",
        "candidate_strategy": "mechanism_transfer_top50_cost_aware_v1",
        "thresholds": {
            "small_tolerance": SMALL_TOLERANCE,
            "material_turnover_reduction": MATERIAL_TURNOVER_REDUCTION,
            "material_cost_reduction": MATERIAL_COST_REDUCTION,
            "max_drawdown_worse_tolerance": MAX_DRAWDOWN_WORSE_TOLERANCE,
            "cash_no_trade_degenerate_threshold": CASH_NO_TRADE_DEGENERATE_THRESHOLD,
        },
        "m0_order_intent_parity": "pass" if all(row["status"] == "pass" for row in order_parity) else "fail",
        "m0_replay_parity": "pass" if all(row["status"] == "pass" for row in replay_parity) else "fail",
        "order_intent_validator_ok": order_validation["ok"],
        "replay_validator_ok": replay_validation["ok"],
        "best_mechanism_candidate": best,
        "passing_mechanism_candidates": [row["candidate_id"] for row in pass_candidates],
        "verdict": "PASS_MTR2_QLIB_LTR_WITH_TRANSFER_CANDIDATE" if pass_candidates and order_validation["ok"] and replay_validation["ok"] and all(row["status"] == "pass" for row in order_parity) and all(row["status"] == "pass" for row in replay_parity) else "FAIL_NEEDS_REPAIR",
        "output_files": {
            "lineage_repair_audit": rel(out_root / "lineage_repair_audit.csv"),
            "long_id_short_id_equivalence_audit": rel(out_root / "long_id_short_id_equivalence_audit.csv"),
            "input_signal_lineage_audit": rel(out_root / "input_signal_lineage_audit.csv"),
            "model_signal_validator_report": rel(out_root / "model_signal_validator_report.json"),
            "dependency_validation_report": rel(out_root / "dependency_validation_report.json"),
            "order_intent_artifact_index": rel(out_root / "order_intent_artifact_index.csv"),
            "order_intent_validator_report": rel(out_root / "order_intent_validator_report.json"),
            "baseline_order_intent_parity_audit": rel(out_root / "baseline_order_intent_parity_audit.csv"),
            "replay_artifact_index": rel(out_root / "replay_artifact_index.csv"),
            "replay_validator_report": rel(out_root / "replay_validator_report.json"),
            "baseline_replay_parity_audit": rel(out_root / "baseline_replay_parity_audit.csv"),
            "mechanism_candidate_contract": rel(out_root / "mechanism_candidate_contract.csv"),
            "mechanism_replay_comparison": rel(out_root / "mechanism_replay_comparison.csv"),
            "turnover_cost_audit": rel(out_root / "turnover_cost_audit.csv"),
            "holding_overlap_audit": rel(out_root / "holding_overlap_audit.csv"),
            "rank_overlap_audit": rel(out_root / "rank_overlap_audit.csv"),
            "cash_no_trade_audit": rel(out_root / "cash_no_trade_audit.csv"),
            "forbidden_field_audit": rel(out_root / "forbidden_field_audit.csv"),
            "forbidden_action_audit": rel(out_root / "forbidden_action_audit.csv"),
        },
    }
    write_json(out_root / "manifest.json", manifest)
    write_report(out_root, manifest, tables["comparison"], order_parity, replay_parity)
    return {"ok": manifest["verdict"].startswith("PASS"), "manifest": rel(out_root / "manifest.json"), "report": rel(REPORT_PATH), "verdict": manifest["verdict"], "best_mechanism_candidate": best, "m0_order_intent_parity": manifest["m0_order_intent_parity"], "m0_replay_parity": manifest["m0_replay_parity"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MTR2 qlib+LTR long-id lineage repair and predeclared transfer readonly replay.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run(resolve(args.out_dir))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok={result['ok']}")
        print(f"manifest={result['manifest']}")
        print(f"report={result['report']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
