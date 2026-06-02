from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import qlib

from run_tw_amihud20_ablation import (
    BASELINE_CONFIG,
    BASELINE_RECORDER,
    BASELINE_SUMMARY,
    PROVIDER,
    ROOT,
    load_indicators,
    load_model_segment_ic,
    load_report,
    paired_ttest,
    parse_stdout,
    risk_by_period,
    turnover_summary,
)


CONFIG = ROOT / "configs/tw_yahoo_primary_alpha158_double_ensemble.yaml"
REPORT_PATH = ROOT / "docs/tw_audit/30_tw_double_ensemble_alpha158_report.md"


def fmt(x):
    if pd.isna(x):
        return ""
    if isinstance(x, (float, np.floating)):
        return f"{x:.6e}" if x != 0 and abs(x) < 1e-4 else f"{x:.6f}"
    return str(x)


def table(df: pd.DataFrame, cols: list[str]) -> list[str]:
    d = df[cols].copy()
    for col in d.columns:
        d[col] = d[col].map(fmt)
    lines = ["| " + " | ".join(d.columns) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in d.to_numpy(dtype=str))
    return lines


def write_report(out: Path, summary: dict, model_ic: pd.DataFrame, risk: pd.DataFrame, paired: pd.DataFrame, turnover: pd.DataFrame) -> None:
    ric = model_ic[model_ic["metric"] == "rank_ic"]
    baseline = pd.read_csv(BASELINE_SUMMARY).iloc[0].to_dict()
    lines = [
        "---",
        "created_at: 2026-05-28",
        "status: model_ablation_ready_for_audit",
        "scope: tw_alpha158_double_ensemble_quick_validation",
        "related_docs:",
        "  - docs/tw_audit/29_claude_audit_round_11_source_inventory_and_direction.md",
        "---",
        "",
        "# Alpha158 DoubleEnsemble Quick Validation",
        "",
        "## Scope",
        "",
        "This run compares the existing Yahoo-only Taiwan Alpha158 LightGBM baseline against Alpha158 with Qlib `DEnsembleModel`. Provider, market, benchmark, handler, train/valid/test split, strategy, transaction costs and 2025-06-30 research cutoff are unchanged. The only intentional variable is the model class and its model-level hyperparameters.",
        "",
        "The run does not use new factors, non-OHLCV data, endpoint discovery results, or any data after 2025-06-30.",
        "",
        "## Dependency Check",
        "",
        "- `qlib.contrib.model.double_ensemble.DEnsembleModel` is available locally.",
        "- The configured base model is `gbm`, implemented with LightGBM; CatBoost/XGBoost optional imports are not required for this run.",
        "",
        "## Summary",
        "",
        f"- candidate recorder: `{summary.get('recorder_id', '')}`",
        f"- baseline recorder: `{BASELINE_RECORDER}`",
        f"- baseline test RankIC: `{fmt(baseline.get('rank_ic'))}`",
        f"- candidate test RankIC: `{fmt(summary.get('rank_ic'))}`",
        f"- test RankIC delta: `{fmt(summary.get('rank_ic_delta'))}`",
        f"- with-cost annualized excess delta: `{fmt(summary.get('with_cost_ann_delta'))}`",
        f"- with-cost IR delta: `{fmt(summary.get('with_cost_ir_delta'))}`",
        "",
        "## Model RankIC By Segment",
        "",
    ]
    lines += table(ric, ["model", "segment", "n_days", "mean", "ir", "positive_rate", "avg_n"])
    lines += ["", "## Portfolio Risk By Test Segment", "", "Note: `annualized_excess` is computed as `mean(daily_excess) * 252`; use summary deltas for cross-report comparison.", ""]
    lines += table(risk, ["model", "segment", "n_days", "annualized_excess", "ir", "max_drawdown"])
    lines += ["", "## Paired Daily Excess Test", ""]
    lines += table(paired, ["n_days", "daily_excess_mean_diff", "paired_t_p_value", "same_direction_positive"])
    lines += ["", "## Turnover", ""]
    lines += table(turnover, ["model", "daily_turnover_mean", "annualized_turnover", "turnover_n_days"])
    lines += [
        "",
        "## Decision For Audit",
        "",
    ]
    if (
        pd.notna(summary.get("rank_ic_delta"))
        and summary.get("rank_ic_delta") >= 0
        and summary.get("with_cost_ann_delta", -np.inf) >= 0
        and summary.get("with_cost_ir_delta", -np.inf) >= 0
    ):
        lines.append("- Candidate passes the mechanical quick-validation checks pending Claude review.")
    else:
        lines.append("- Candidate does not satisfy the full quick-validation standard; hold promotion pending Claude review.")
    lines += [
        "",
        "## Endpoint Discovery Status",
        "",
        "Round 11 approved browser-assisted TWSE/TPEx endpoint discovery. This environment cannot operate an interactive DevTools Network tab, so no production crawler or endpoint claim was added in this commit. The next audit should decide whether a browser-capable pass should update the Phase D.1 source inventory before any margin/short POC.",
        "",
        "## Artifacts",
        "",
    ]
    for f in sorted(out.iterdir()):
        if f.is_file():
            lines.append(f"- `{f.relative_to(ROOT)}`")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Alpha158 DoubleEnsemble quick validation.")
    parser.add_argument("--output-dir", default="data_tw/experiments/yahoo_primary_alpha158_double_ensemble")
    args = parser.parse_args()
    out = ROOT / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CONFIG, out / "double_ensemble_config_snapshot.yaml")

    proc = subprocess.run(
        ["python", "qlib/cli/run.py", str(CONFIG)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path = out / "double_ensemble.log"
    log_path.write_text(proc.stdout, encoding="utf-8")

    row = {
        "name": "alpha158_double_ensemble",
        "returncode": proc.returncode,
        "baseline_recorder_id": BASELINE_RECORDER,
        "config_path": str(CONFIG.relative_to(ROOT)),
        "log_path": str(log_path.relative_to(ROOT)),
    }
    row.update(parse_stdout(proc.stdout))
    if row.get("recorder_id"):
        (out / "double_ensemble_recorder_id.txt").write_text(str(row["recorder_id"]) + "\n", encoding="utf-8")

    baseline = pd.read_csv(BASELINE_SUMMARY).iloc[0].to_dict()
    row["rank_ic_delta"] = row.get("rank_ic") - baseline.get("rank_ic") if row.get("rank_ic") is not None else np.nan
    row["with_cost_ann_delta"] = row.get("with_cost_annualized_return") - baseline.get("with_cost_annualized_return") if row.get("with_cost_annualized_return") is not None else np.nan
    row["with_cost_ir_delta"] = row.get("with_cost_information_ratio") - baseline.get("with_cost_information_ratio") if row.get("with_cost_information_ratio") is not None else np.nan
    pd.DataFrame([row]).to_csv(out / "summary.csv", index=False)

    if proc.returncode != 0 or not row.get("recorder_id"):
        print(f"returncode={proc.returncode}")
        print(f"wrote {out.relative_to(ROOT)}")
        raise SystemExit(proc.returncode)

    qlib.init(provider_uri=PROVIDER, region="tw", expression_cache=None, dataset_cache=None)
    base_daily_ic, base_ic_summary = load_model_segment_ic(BASELINE_CONFIG, BASELINE_RECORDER, "baseline_alpha158_lgbm")
    cand_daily_ic, cand_ic_summary = load_model_segment_ic(CONFIG, str(row["recorder_id"]), "alpha158_double_ensemble")
    model_ic = pd.concat([base_ic_summary, cand_ic_summary], ignore_index=True)
    model_ic.to_csv(out / "model_segment_ic.csv", index=False)
    pd.concat(
        [
            base_daily_ic.assign(model="baseline_alpha158_lgbm"),
            cand_daily_ic.assign(model="alpha158_double_ensemble"),
        ],
        ignore_index=True,
    ).to_csv(out / "model_daily_ic.csv", index=False)

    base_report = load_report(BASELINE_RECORDER).rename(columns={"return": "baseline_return", "bench": "baseline_bench", "excess": "baseline_excess"})
    cand_report = load_report(str(row["recorder_id"])).rename(columns={"return": "candidate_return", "bench": "candidate_bench", "excess": "candidate_excess"})
    paired = base_report[["date", "baseline_return", "baseline_bench", "baseline_excess"]].merge(
        cand_report[["date", "candidate_return", "candidate_bench", "candidate_excess"]],
        on="date",
        how="inner",
    )
    paired["candidate_minus_baseline_excess"] = paired["candidate_excess"] - paired["baseline_excess"]
    paired.to_csv(out / "paired_daily_excess.csv", index=False)
    paired_summary = pd.DataFrame(
        [
            {
                "baseline_recorder_id": BASELINE_RECORDER,
                "candidate_recorder_id": row["recorder_id"],
                **paired_ttest(paired["baseline_excess"], paired["candidate_excess"]),
            }
        ]
    )
    paired_summary.to_csv(out / "paired_ttest_summary.csv", index=False)

    risk = pd.concat(
        [
            risk_by_period(load_report(BASELINE_RECORDER), "baseline_alpha158_lgbm"),
            risk_by_period(load_report(str(row["recorder_id"])), "alpha158_double_ensemble"),
        ],
        ignore_index=True,
    )
    risk.to_csv(out / "portfolio_risk_by_segment.csv", index=False)

    turnover = pd.DataFrame(
        [
            turnover_summary(load_report(BASELINE_RECORDER), load_indicators(BASELINE_RECORDER), "baseline_alpha158_lgbm"),
            turnover_summary(load_report(str(row["recorder_id"])), load_indicators(str(row["recorder_id"])), "alpha158_double_ensemble"),
        ]
    )
    turnover.to_csv(out / "turnover_summary.csv", index=False)

    write_report(out, row, model_ic, risk, paired_summary, turnover)
    print(f"returncode={proc.returncode}")
    print(f"recorder_id={row.get('recorder_id', '')}")
    print(f"rank_ic_delta={row.get('rank_ic_delta')}")
    print(f"with_cost_ann_delta={row.get('with_cost_ann_delta')}")
    print(f"wrote {out.relative_to(ROOT)}")
    print(f"wrote {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
