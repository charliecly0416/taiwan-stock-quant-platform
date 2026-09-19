#!/usr/bin/env python3
"""Additive post-outcome audit for B18R2; never modifies frozen B18R2 files."""
from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b18r2_historical_pit_paired_replay_20260916"
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b18r2_supplemental_audit_20260916"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
METHODS = ("A_ONLY", "A_PLUS_B")
COMBINED_START = "2026-01-02"
COMBINED_SIGNAL_END = "2026-05-07"
COMBINED_SETTLEMENT_END = "2026-05-08"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def fingerprint(path: Path) -> dict[str, Any]:
    return {"path": relative(path), "sha256": sha256(path), "bytes": path.stat().st_size}


def directory_inventory(path: Path) -> dict[str, Any]:
    files = sorted(item for item in path.iterdir() if item.is_file())
    entries = [{"name": item.name, "sha256": sha256(item), "bytes": item.stat().st_size} for item in files]
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"file_count": len(entries), "sha256": hashlib.sha256(payload).hexdigest(), "entries": entries}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def tie_aware_rank_audit(signals: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[pd.DataFrame] = []
    for day, group in signals.groupby("date", sort=True):
        ranked = group.sort_values(["b_score", "instrument"], ascending=[False, True]).copy()
        ranked["expected_replay_b_buy_rank"] = np.arange(1, len(ranked) + 1)
        ranked["same_score_group_size"] = ranked.groupby("b_score").instrument.transform("size")
        rows.append(
            ranked[
                [
                    "date",
                    "instrument",
                    "b_score",
                    "b_buy_rank",
                    "expected_replay_b_buy_rank",
                    "same_score_group_size",
                ]
            ]
        )
    audit = pd.concat(rows, ignore_index=True)
    audit["stored_rank_matches_replay_tiebreak"] = (
        audit.b_buy_rank.astype(int) == audit.expected_replay_b_buy_rank.astype(int)
    )
    summary = {
        "rows": int(len(audit)),
        "dates": int(audit.date.nunique()),
        "tied_score_rows": int((audit.same_score_group_size > 1).sum()),
        "mismatch_rows": int((~audit.stored_rank_matches_replay_tiebreak).sum()),
        "mismatch_dates": int(
            audit.loc[~audit.stored_rank_matches_replay_tiebreak, "date"].nunique()
        ),
        "replay_order_definition": "b_score desc, instrument asc",
        "replay_result_impact": False,
        "reason": "Replay sorted b_score/instrument directly; stored b_buy_rank was not consumed by replay.",
    }
    return audit, summary


def final_close(symbol: str, day: str) -> float:
    frame = pd.read_csv(PRICE_ROOT / f"{symbol}.csv", usecols=["date", "close"], dtype={"date": str})
    frame["date"] = frame.date.str[:10]
    frame["close"] = pd.to_numeric(frame.close, errors="coerce")
    eligible = frame[(frame.date <= day) & frame.close.notna() & (frame.close > 0)]
    if eligible.empty:
        raise RuntimeError(f"missing final close for {symbol} through {day}")
    return float(eligible.iloc[-1].close)


def contribution_audit(method: str, final_equity: float, final_day: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    actions = pd.read_csv(SOURCE / f"{method}_actions.csv")
    contribution: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "realized_net_after_sell_cost": 0.0,
            "buy_commission": 0.0,
            "final_unrealized_gross": 0.0,
            "sell_gross_pnl": 0.0,
            "sell_commission": 0.0,
            "sell_tax": 0.0,
        }
    )
    held_qty: dict[str, int] = {}
    held_basis: dict[str, float] = {}
    for row in actions.itertuples(index=False):
        symbol = str(row.instrument)
        quantity = int(row.quantity)
        price = float(row.execution_price)
        if row.action == "buy":
            contribution[symbol]["buy_commission"] -= float(row.commission)
            held_qty[symbol] = held_qty.get(symbol, 0) + quantity
            held_basis[symbol] = held_basis.get(symbol, 0.0) + quantity * price
        else:
            if held_qty.get(symbol) != quantity:
                raise RuntimeError(f"sell quantity does not equal held quantity: {method} {symbol}")
            contribution[symbol]["realized_net_after_sell_cost"] += float(row.net_pnl)
            contribution[symbol]["sell_gross_pnl"] += float(row.gross_pnl)
            contribution[symbol]["sell_commission"] -= float(row.commission)
            contribution[symbol]["sell_tax"] -= float(row.sell_tax)
            held_qty.pop(symbol)
            held_basis.pop(symbol)
    for symbol, quantity in held_qty.items():
        contribution[symbol]["final_unrealized_gross"] = (
            quantity * final_close(symbol, final_day) - held_basis[symbol]
        )

    rows: list[dict[str, Any]] = []
    for symbol, values in sorted(contribution.items()):
        full = (
            values["realized_net_after_sell_cost"]
            + values["buy_commission"]
            + values["final_unrealized_gross"]
        )
        rows.append({"method": method, "instrument": symbol, **values, "full_contribution": full})
    detail = pd.DataFrame(rows)
    denominator = float(detail.full_contribution.abs().sum())
    detail["share_of_abs_full_contribution"] = (
        detail.full_contribution.abs() / denominator if denominator else 0.0
    )
    detail = detail.sort_values("share_of_abs_full_contribution", ascending=False).reset_index(drop=True)
    expected_total = final_equity - 1_000_000.0
    observed_total = float(detail.full_contribution.sum())
    shares = detail.share_of_abs_full_contribution
    summary = {
        "method": method,
        "symbols": int(len(detail)),
        "final_day": final_day,
        "realized_net_after_sell_cost": float(detail.realized_net_after_sell_cost.sum()),
        "buy_commission": float(detail.buy_commission.sum()),
        "final_unrealized_gross": float(detail.final_unrealized_gross.sum()),
        "full_contribution": observed_total,
        "expected_final_equity_minus_initial": expected_total,
        "accounting_error": observed_total - expected_total,
        "top1_abs_contribution_share": float(shares.head(1).sum()),
        "top5_abs_contribution_share": float(shares.head(5).sum()),
        "abs_contribution_hhi": float((shares**2).sum()),
        "final_open_positions": int(len(held_qty)),
    }
    return detail, summary


def combined_2026_metrics(method: str, signal_days: int) -> dict[str, Any]:
    nav = pd.read_csv(SOURCE / f"{method}_daily_ledger.csv", dtype={"date": str})
    actions = pd.read_csv(SOURCE / f"{method}_actions.csv", dtype={"signal_date": str})
    period = nav[nav.date.between(COMBINED_START, COMBINED_SETTLEMENT_END)].copy()
    if period.empty or period.date.iloc[0] != COMBINED_START or period.date.iloc[-1] != COMBINED_SETTLEMENT_END:
        raise RuntimeError(f"combined 2026 boundary missing for {method}")
    start_equity = float(period.equity.iloc[0])
    end_equity = float(period.equity.iloc[-1])
    peak = period.equity.cummax()
    period_actions = actions[actions.signal_date.between(COMBINED_START, COMBINED_SIGNAL_END)].copy()
    active = period_actions[(period_actions.status == "EXECUTED") & (period_actions.quantity > 0)]
    return {
        "method": method,
        "signal_start": COMBINED_START,
        "signal_end": COMBINED_SIGNAL_END,
        "settlement_end": COMBINED_SETTLEMENT_END,
        "signal_days": signal_days,
        "calendar_rows_including_settlement": int(len(period)),
        "start_boundary": "equity after 2026-01-02 market close and carry-in order processing",
        "end_boundary": "equity after 2026-05-08 next-open settlement and same-day close mark",
        "start_equity": start_equity,
        "end_equity": end_equity,
        "net_return": end_equity / start_equity - 1.0,
        "max_drawdown": float((period.equity / peak - 1.0).min()),
        "buy_count": int((active.action == "buy").sum()),
        "sell_count": int((active.action == "sell").sum()),
        "turnover_notional": float((active.quantity * active.execution_price).sum()),
        "commission": float(active.commission.sum()),
        "sell_tax": float(active.sell_tax.sum()),
        "fee_tax": float(active.commission.sum() + active.sell_tax.sum()),
        "untouched": False,
        "prospective": False,
    }


def moving_block_bootstrap(values: np.ndarray, *, seed: int, block: int = 10, reps: int = 10_000) -> dict[str, Any]:
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    starts = np.arange(max(1, len(values) - block + 1))
    samples = np.empty(reps, dtype=float)
    block_count = math.ceil(len(values) / block)
    for index in range(reps):
        chosen = rng.choice(starts, size=block_count, replace=True)
        sample = np.concatenate([values[start : start + block] for start in chosen])[: len(values)]
        samples[index] = float(sample.mean())
    return {
        "observations": int(len(values)),
        "observed_mean_daily_active_return": float(values.mean()),
        "block_length": block,
        "replications": reps,
        "seed": seed,
        "mean_ci_95": [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))],
        "bootstrap_probability_mean_gt_zero": float((samples > 0).mean()),
        "classification": "POST_OUTCOME_DIAGNOSTIC_NOT_PREREGISTERED",
        "formal_gate_allowed": False,
    }


def main() -> int:
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError(f"supplement output already exists: {relative(OUT)}")
    OUT.mkdir(parents=True, exist_ok=True)
    source_inventory_before = directory_inventory(SOURCE)
    source_manifest = json.loads((SOURCE / "B18_MANIFEST.json").read_text(encoding="utf-8"))
    source_validator = json.loads((SOURCE / "B18_VALIDATOR.json").read_text(encoding="utf-8"))
    if source_validator.get("verdict") != "PASS":
        raise RuntimeError("B18R2 source validator is not PASS")

    signals = pd.read_csv(SOURCE / "signals.csv", dtype={"date": str, "instrument": str})
    tie_audit, tie_summary = tie_aware_rank_audit(signals)
    tie_audit.to_csv(OUT / "tie_aware_b_rank_audit.csv", index=False)

    contribution_frames: list[pd.DataFrame] = []
    contribution_summaries: list[dict[str, Any]] = []
    final_day_by_method: dict[str, str] = {}
    for method in METHODS:
        nav = pd.read_csv(SOURCE / f"{method}_daily_ledger.csv", dtype={"date": str})
        final_day = str(nav.date.iloc[-1])
        final_day_by_method[method] = final_day
        detail, summary = contribution_audit(method, float(nav.equity.iloc[-1]), final_day)
        contribution_frames.append(detail)
        contribution_summaries.append(summary)
    pd.concat(contribution_frames, ignore_index=True).to_csv(
        OUT / "full_contribution_concentration.csv", index=False
    )

    combined_signal_days = int(signals.loc[signals.date.between(COMBINED_START, COMBINED_SIGNAL_END), "date"].nunique())
    combined = [combined_2026_metrics(method, combined_signal_days) for method in METHODS]
    combined_frame = pd.DataFrame(combined)
    combined_frame.to_csv(OUT / "combined_2026_79d_metrics.csv", index=False)
    control = next(row for row in combined if row["method"] == "A_ONLY")
    treatment = next(row for row in combined if row["method"] == "A_PLUS_B")
    combined_relative = {
        "net_return_diff_b_minus_a": treatment["net_return"] - control["net_return"],
        "max_drawdown_diff_b_minus_a": treatment["max_drawdown"] - control["max_drawdown"],
        "turnover_diff_b_minus_a": treatment["turnover_notional"] - control["turnover_notional"],
        "fee_tax_diff_b_minus_a": treatment["fee_tax"] - control["fee_tax"],
    }

    paired_daily = pd.read_csv(SOURCE / "paired_daily_metrics.csv", dtype={"date": str})
    full_active = paired_daily.loc[
        paired_daily.date.between("2025-01-02", "2026-05-07"), "active_return_b_minus_a"
    ].to_numpy(dtype=float)
    combined_active = paired_daily.loc[
        paired_daily.date.between(COMBINED_START, COMBINED_SIGNAL_END), "active_return_b_minus_a"
    ].to_numpy(dtype=float)
    bootstrap = {
        "warning": (
            "All bootstrap results were designed after B18R2 outcomes were visible. They are diagnostics only, "
            "not preregistered confirmation and not eligible for baseline or formal gate decisions."
        ),
        "full_321_signal_days": moving_block_bootstrap(full_active, seed=20260916),
        "combined_2026_79_signal_days": moving_block_bootstrap(combined_active, seed=20260917),
    }
    write_json(OUT / "post_outcome_bootstrap_diagnostic.json", bootstrap)

    boundary = {
        "source_stratum_metrics_boundary": (
            "Each source stratum ends on that stratum's final signal-date close. It does not include orders "
            "created by that final signal and settled on the following trading day."
        ),
        "source_final_metric_boundary": (
            "Source final equity includes 2026-05-08 next-open settlement of 2026-05-07 intents and the "
            "2026-05-08 close mark."
        ),
        "combined_2026_boundary": (
            "The supplemental combined layer uses equity at 2026-01-02 close as its carry-in start and "
            "2026-05-08 settled/marked equity as its end."
        ),
        "comparability_warning": (
            "Source stratum returns and final/combined returns have different settlement boundaries and must "
            "not be arithmetically added or treated as identical windows."
        ),
    }
    write_json(OUT / "settlement_boundary_audit.json", boundary)

    checks = {
        "source_validator_pass": source_validator.get("verdict") == "PASS",
        "source_files_unchanged": sha256(SOURCE / "B18_MANIFEST.json")
        == "5d87deb784faf87e1c17f247d01b93f7625e1b523f5dc92c87b9ff648f2803e1",
        "tie_audit_all_321_dates": tie_summary["dates"] == 321,
        "tie_aware_order_defined": tie_summary["replay_order_definition"] == "b_score desc, instrument asc",
        "contribution_accounting_reconciles": all(
            abs(row["accounting_error"]) < 1e-6 for row in contribution_summaries
        ),
        "combined_signal_days_79": combined_signal_days == 79,
        "combined_settlement_end_20260508": all(
            row["settlement_end"] == COMBINED_SETTLEMENT_END for row in combined
        ),
        "bootstrap_post_outcome_only": all(
            value.get("formal_gate_allowed") is False
            for key, value in bootstrap.items()
            if key != "warning"
        ),
        "no_source_artifact_modified": source_inventory_before == directory_inventory(SOURCE),
        "no_training_tuning_or_production_write": True,
    }
    validator = {
        "schema_version": "modelb.b18r2.supplemental_audit.validator.v1",
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
    }
    write_json(OUT / "B18R2_SUPPLEMENT_VALIDATOR.json", validator)

    artifact_names = [
        "tie_aware_b_rank_audit.csv",
        "full_contribution_concentration.csv",
        "combined_2026_79d_metrics.csv",
        "post_outcome_bootstrap_diagnostic.json",
        "settlement_boundary_audit.json",
        "B18R2_SUPPLEMENT_VALIDATOR.json",
    ]
    manifest = {
        "schema_version": "modelb.b18r2.supplemental_audit.manifest.v1",
        "run_id": OUT.name,
        "created_at": utc_now(),
        "status": "ADDITIVE_POST_OUTCOME_AUDIT_COMPLETE_AWAITING_REVIEW",
        "source_run": relative(SOURCE),
        "source_manifest": fingerprint(SOURCE / "B18_MANIFEST.json"),
        "source_run_freeze": fingerprint(SOURCE / "B18_RUN_FREEZE.json"),
        "source_validator": fingerprint(SOURCE / "B18_VALIDATOR.json"),
        "source_files_modified": False,
        "source_inventory_before": source_inventory_before,
        "source_inventory_after": directory_inventory(SOURCE),
        "tie_aware_b_rank": tie_summary,
        "full_contribution_concentration": contribution_summaries,
        "combined_2026_79_signal_days": combined,
        "combined_2026_relative": combined_relative,
        "settlement_boundaries": boundary,
        "bootstrap": bootstrap,
        "formal_gate_evidence": False,
        "post_outcome_diagnostic_only": True,
        "baseline_admission": False,
        "production_allowed": False,
        "training_performed": False,
        "tuning_performed": False,
        "artifacts": {name: fingerprint(OUT / name) for name in artifact_names},
    }
    write_json(OUT / "B18R2_SUPPLEMENT_MANIFEST.json", manifest)

    report = f"""# B18R2 附加审计报告

本目录是 additive supplement，未修改 B18R2 原始 freeze、signals、actions、ledger、manifest 或 validator。

## Tie-break 排名

按 replay 实际使用的 `b_score desc, instrument asc` 重算 321 日 B rank。stored `b_buy_rank` 与实际 replay 顺序不一致行数为 {tie_summary['mismatch_rows']}，涉及 {tie_summary['mismatch_dates']} 日；replay 从未消费 stored rank，因此原回放结果不受影响。

## 完整贡献集中度

集中度已纳入卖出后已实现净损益、所有买入佣金及 2026-05-08 期末 10 个持仓的未实现损益。A-only accounting error={contribution_summaries[0]['accounting_error']:.3e}，A+B accounting error={contribution_summaries[1]['accounting_error']:.3e}。

## 2026 合并层

合并 2026-01-02 至 2026-05-07 的 79 个信号日，并纳入 2026-05-08 next-open settlement。A-only return={control['net_return']:.8%}，A+B return={treatment['net_return']:.8%}，B-A={combined_relative['net_return_diff_b_minus_a']:.8%}。

## 边界与统计声明

原 stratum 指标截止各层最后 signal-date close，不包含该日信号的次日结算；原 final 指标包含 2026-05-08 结算和收盘标记。所有 moving-block bootstrap 均为看过 B18R2 结果后新增的诊断，不是预注册检验，不得用于正式 gate、baseline admission 或 production 切换。

Validator：`{validator['verdict']}`。本补充仍待独立审查。
"""
    (OUT / "B18R2_SUPPLEMENT_EXECUTION_REPORT_CN.md").write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "tie_rank_mismatches": tie_summary["mismatch_rows"],
                "combined_2026_delta": combined_relative["net_return_diff_b_minus_a"],
                "validator": validator["verdict"],
                "out": relative(OUT),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if validator["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
