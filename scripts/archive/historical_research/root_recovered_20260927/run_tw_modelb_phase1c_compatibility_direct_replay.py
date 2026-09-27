#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "data_tw/experiments/model_b_compatibility_baseline_reinstatement/phase1c_compatibility_20260905"
SIGNALS = ARTIFACT_DIR / "signals.csv"
LEGACY_SCORES = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv"
FRESH_REPLAY = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_replay_ready_scores.csv"
FROZEN_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck"
FROZEN_METRICS = ROOT / "data_tw/experiments/archive/historical_research/phase1c_anchor_reproduction/phasea1_anchor_metrics.csv"
FROZEN_COMMON_METRICS = ROOT / "data_tw/experiments/archive/historical_research/phase1c_anchor_reproduction/phasea1_common_universe_metrics.csv"
FROZEN_ACTIONS = FROZEN_DIR / "phase_s2f_same_window_action_audit.csv"
FROZEN_NAV = FROZEN_DIR / "phase_s2f_same_window_daily_nav.csv"
ENGINE = ROOT / "scripts/archive/historical_research/evaluate_tw_ltr_s2d_full_daily_replay.py"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"

OUT = ARTIFACT_DIR / "direct_replay_reexecution"
START = "2025-07-01"
END = "2026-05-07"
OLD_METHOD = "old_qlib_new_ltr_phase1c_simple"
STANDARD_METHOD = "standard_artifact_model_a_plus_b"
CONTROL_METHOD = "fresh_qlib_top50_adaptive_baseline"

PROTECTED = [
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
]

EXPECTED = {
    ("full", STANDARD_METHOD): (0.721631, -0.050830, 405, 157661.34),
    ("full", CONTROL_METHOD): (0.662457, -0.088396, 410, 155259.42),
    ("common", STANDARD_METHOD): (0.641235, -0.076739, 405, 149876.44),
    ("common", CONTROL_METHOD): (0.625943, -0.088431, 410, 153601.13),
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprints(paths: list[Path]) -> dict[str, Any]:
    return {
        rel(path): {
            "exists": path.exists(),
            "size": path.stat().st_size if path.exists() else None,
            "sha256": sha256(path) if path.is_file() else None,
        }
        for path in paths
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_engine():
    spec = importlib.util.spec_from_file_location("phase1c_compat_replay_engine", ENGINE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load replay engine: {ENGINE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.PRICE_ROOT = PRICE_ROOT
    return module


def prepare_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, set[tuple[str, str]]]:
    standard = pd.read_csv(
        SIGNALS,
        usecols=["date", "instrument", "buy_score", "candidate_rank", "signal_asof", "available_at"],
        dtype={"instrument": str},
    )
    standard["date_str"] = standard["date"].astype(str).str[:10]
    standard["regime_segment"] = "unknown"

    legacy = pd.read_csv(
        LEGACY_SCORES,
        usecols=["date", "instrument", "score_head10_all_l31_alpha0.7_top50_only"],
        dtype={"instrument": str},
    ).rename(columns={"score_head10_all_l31_alpha0.7_top50_only": "legacy_buy_score"})
    legacy["date_str"] = legacy["date"].astype(str).str[:10]
    legacy["regime_segment"] = "unknown"
    legacy = legacy[(legacy["date_str"] >= START) & (legacy["date_str"] <= END)].copy()

    fresh = pd.read_csv(
        FRESH_REPLAY,
        usecols=["date", "instrument", "split", "adaptive_score_baseline", "ltr_score", "regime_segment"],
        dtype={"instrument": str},
    )
    fresh["date_str"] = fresh["date"].astype(str).str[:10]
    fresh = fresh[(fresh["split"] == "test") & (fresh["date_str"] >= START) & (fresh["date_str"] <= END)].copy()

    standard_keys = set(zip(standard["date_str"], standard["instrument"]))
    common_rows = fresh[fresh["adaptive_score_baseline"].notna() & fresh["ltr_score"].notna()]
    common_keys = set(zip(common_rows["date_str"], common_rows["instrument"])) & standard_keys
    return standard, legacy, fresh, common_keys


def subset(df: pd.DataFrame, keys: set[tuple[str, str]]) -> pd.DataFrame:
    mask = pd.Series(list(zip(df["date_str"], df["instrument"])), index=df.index).isin(keys)
    return df[mask].copy()


def metric_row(universe: str, result: dict[str, Any]) -> dict[str, Any]:
    expected_key = (universe, result["method"])
    row = {"universe": universe, "method": result["method"], **result["metrics"]}
    if expected_key in EXPECTED:
        exp_return, exp_dd, exp_actions, exp_cost = EXPECTED[expected_key]
        row.update(
            {
                "expected_return": exp_return,
                "expected_max_drawdown": exp_dd,
                "expected_action_count": exp_actions,
                "expected_fee_and_tax": exp_cost,
                "return_diff": round(float(row["fee_tax_adjusted_net_return"]) - exp_return, 12),
                "max_drawdown_diff": round(float(row["max_drawdown"]) - exp_dd, 12),
                "action_count_diff": int(row["action_count"]) - exp_actions,
                "fee_and_tax_diff": round(float(row["fee_and_tax"]) - exp_cost, 2),
            }
        )
    return row


def canonical_records(rows: list[dict[str, Any]], fields: list[str], sort_fields: list[str]) -> list[dict[str, Any]]:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return []
    frame = frame[fields].copy().sort_values(sort_fields).reset_index(drop=True)
    for field in ["price", "fee_and_tax", "equity", "cash"]:
        if field in frame:
            frame[field] = pd.to_numeric(frame[field], errors="coerce").round(2)
    for field in ["quantity", "holding_count", "missing_price_count"]:
        if field in frame:
            frame[field] = pd.to_numeric(frame[field], errors="coerce").fillna(0).astype(int)
    return frame.to_dict("records")


def compare_records(left: list[dict[str, Any]], right: list[dict[str, Any]], fields: list[str], sort_fields: list[str]) -> dict[str, Any]:
    lhs = canonical_records(left, fields, sort_fields)
    rhs = canonical_records(right, fields, sort_fields)
    lhs_text = json.dumps(lhs, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    rhs_text = json.dumps(rhs, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return {
        "left_count": len(lhs),
        "right_count": len(rhs),
        "left_sha256": hashlib.sha256(lhs_text.encode()).hexdigest(),
        "right_sha256": hashlib.sha256(rhs_text.encode()).hexdigest(),
        "exact_match": lhs_text == rhs_text,
    }


def next_day_rows(universe: str, method: str, result: dict[str, Any]) -> dict[str, Any]:
    active = [row for row in result["actions"] if row["action"] in {"historical_add", "historical_risk_reduce"}]
    violations = sum(str(row["execution_date"]) <= str(row["signal_date"]) for row in active)
    metrics = result["metrics"]
    passed = (
        violations == 0
        and int(metrics["missing_price_days"]) == 0
        and int(metrics["skipped_trade_count"]) == 0
        and int(metrics["last_day_new_trade_without_next_price_count"]) == 0
    )
    return {
        "universe": universe,
        "method": method,
        "active_action_count": len(active),
        "execution_not_after_signal_violations": violations,
        "missing_price_days": metrics["missing_price_days"],
        "skipped_trade_count": metrics["skipped_trade_count"],
        "last_day_new_trade_without_next_price_count": metrics["last_day_new_trade_without_next_price_count"],
        "pass": passed,
    }


def main() -> int:
    required = [SIGNALS, LEGACY_SCORES, FRESH_REPLAY, FROZEN_METRICS, FROZEN_COMMON_METRICS, FROZEN_ACTIONS, FROZEN_NAV, ENGINE]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing required inputs: {missing}")

    protected_before = fingerprints(PROTECTED)
    standard, legacy, fresh, common_keys = prepare_inputs()
    if standard.duplicated(["date_str", "instrument"]).any() or legacy.duplicated(["date_str", "instrument"]).any():
        raise RuntimeError("duplicate replay keys")
    if len(common_keys) != 22474:
        raise RuntimeError(f"frozen common universe key count mismatch: {len(common_keys)}")

    engine = load_engine()
    all_symbols = set(standard["instrument"]) | set(fresh["instrument"])
    prices = engine.PriceStore(all_symbols)
    if not prices.by_symbol:
        raise RuntimeError("price store is empty")

    results: dict[tuple[str, str], dict[str, Any]] = {}
    for universe, std_df, legacy_df, control_df in [
        ("full", standard, legacy, fresh),
        ("common", subset(standard, common_keys), subset(legacy, common_keys), subset(fresh, common_keys)),
    ]:
        results[(universe, STANDARD_METHOD)] = engine.replay(
            std_df, prices, engine.MethodSpec(STANDARD_METHOD, "buy_score", 50, False), "same_test_window", START, END
        )
        results[(universe, OLD_METHOD)] = engine.replay(
            legacy_df, prices, engine.MethodSpec(OLD_METHOD, "legacy_buy_score", 50, False), "same_test_window", START, END
        )
        results[(universe, CONTROL_METHOD)] = engine.replay(
            control_df, prices, engine.MethodSpec(CONTROL_METHOD, "adaptive_score_baseline", 50, False), "same_test_window", START, END
        )

    metric_rows = [metric_row(universe, result) for (universe, _), result in results.items()]
    nav_rows = [{"universe": universe, **row} for (universe, _), result in results.items() for row in result["curve"]]
    action_rows = [{"universe": universe, **row} for (universe, _), result in results.items() for row in result["actions"]]

    action_fields = ["signal_date", "execution_date", "effective_nav_date", "symbol", "action", "quantity", "price", "fee_and_tax", "reason"]
    action_sort = ["signal_date", "execution_date", "symbol", "action"]
    nav_fields = ["date", "equity", "cash", "holding_count", "missing_price_count"]
    nav_sort = ["date"]

    frozen_actions_df = pd.read_csv(FROZEN_ACTIONS)
    frozen_actions = frozen_actions_df[frozen_actions_df["method"] == OLD_METHOD].to_dict("records")
    frozen_nav_df = pd.read_csv(FROZEN_NAV)
    frozen_nav = frozen_nav_df[frozen_nav_df["method"] == OLD_METHOD].to_dict("records")

    parity: dict[str, Any] = {"created_at": now(), "checks": {}}
    for universe in ["full", "common"]:
        parity["checks"][f"{universe}_standard_vs_legacy_actions"] = compare_records(
            results[(universe, STANDARD_METHOD)]["actions"], results[(universe, OLD_METHOD)]["actions"], action_fields, action_sort
        )
        parity["checks"][f"{universe}_standard_vs_legacy_nav"] = compare_records(
            results[(universe, STANDARD_METHOD)]["curve"], results[(universe, OLD_METHOD)]["curve"], nav_fields, nav_sort
        )
    parity["checks"]["full_standard_vs_frozen_actions"] = compare_records(
        results[("full", STANDARD_METHOD)]["actions"], frozen_actions, action_fields, action_sort
    )
    parity["checks"]["full_standard_vs_frozen_nav"] = compare_records(
        results[("full", STANDARD_METHOD)]["curve"], frozen_nav, nav_fields, nav_sort
    )
    parity["all_exact"] = all(check["exact_match"] for check in parity["checks"].values())

    next_day = [next_day_rows(universe, method, result) for (universe, method), result in results.items()]
    expected_pass = all(
        float(row.get("return_diff", 0)) == 0
        and float(row.get("max_drawdown_diff", 0)) == 0
        and int(row.get("action_count_diff", 0)) == 0
        and float(row.get("fee_and_tax_diff", 0)) == 0
        for row in metric_rows
        if (row["universe"], row["method"]) in EXPECTED
    )

    input_audit = {
        "created_at": now(),
        "standard_signal_columns_read": ["date", "instrument", "buy_score", "candidate_rank", "signal_asof", "available_at"],
        "standard_signal_columns_consumed_by_ab_replay": ["date", "instrument", "buy_score"],
        "forbidden_signal_fields_consumed": [],
        "future_or_label_fields_consumed": False,
        "price_source": rel(PRICE_ROOT),
        "execution": "next available close strictly after signal date (frozen historical engine)",
        "fee_rate": engine.FEE_RATE,
        "sell_tax_rate": engine.SELL_TAX_RATE,
        "max_holdings": engine.MAX_HOLDINGS,
        "research_only": True,
        "production_allowed": False,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "direct_replay_metrics.csv", metric_rows)
    write_csv(OUT / "direct_replay_daily_nav.csv", nav_rows)
    write_csv(OUT / "direct_replay_actions.csv", action_rows)
    write_csv(OUT / "next_day_execution_audit.csv", next_day)
    write_json(OUT / "parity_audit.json", parity)
    write_json(OUT / "input_consumption_audit.json", input_audit)

    protected_after = fingerprints(PROTECTED)
    protected_audit = {
        "before": protected_before,
        "after": protected_after,
        "unchanged": protected_before == protected_after,
    }
    write_json(OUT / "protected_path_fingerprint_audit.json", protected_audit)

    artifact_paths = [
        OUT / "direct_replay_metrics.csv",
        OUT / "direct_replay_daily_nav.csv",
        OUT / "direct_replay_actions.csv",
        OUT / "next_day_execution_audit.csv",
        OUT / "parity_audit.json",
        OUT / "input_consumption_audit.json",
        OUT / "protected_path_fingerprint_audit.json",
    ]
    checksums = {rel(path): sha256(path) for path in artifact_paths}
    write_json(OUT / "checksum_manifest.json", checksums)

    gate_ok = parity["all_exact"] and expected_pass and all(row["pass"] for row in next_day) and protected_audit["unchanged"]
    gate = {
        "created_at": now(),
        "route": "MODEL_AB_COMPATIBILITY_BASELINE_REINSTATEMENT_AB2R_DIRECT_REPLAY",
        "ok": gate_ok,
        "decision": "RESTORED_RESEARCH_BASELINE_MODEL_A_PLUS_B" if gate_ok else "STOP_DIRECT_REPLAY_PARITY_FAILED",
        "production_decision": "HOLD_OUTSIDE_PRODUCTION_DEFAULT_PENDING_STRICT_PIT_LINEAGE",
        "standard_artifact_directly_consumed": True,
        "full_and_common_replayed": True,
        "common_universe_key_count": len(common_keys),
        "expected_metrics_pass": expected_pass,
        "action_nav_parity_pass": parity["all_exact"],
        "next_day_execution_pass": all(row["pass"] for row in next_day),
        "protected_paths_unchanged": protected_audit["unchanged"],
        "strict_pit_oos": False,
        "legacy_compatible": True,
        "research_only": True,
        "production_allowed": False,
        "no_training": True,
        "no_latest_provider_cron_frontend_write": True,
        "artifacts": {path.name: rel(path) for path in artifact_paths + [OUT / "checksum_manifest.json"]},
    }
    write_json(OUT / "gate_summary.json", gate)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0 if gate_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
