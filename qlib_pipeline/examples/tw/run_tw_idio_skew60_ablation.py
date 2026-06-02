from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import qlib
import yaml
from qlib.contrib.data.tw_handler import TWAlpha158IdioSkew60
from qlib.data.dataset.handler import DataHandlerLP
from qlib.utils import init_instance_by_config

from diagnose_alpha158_importance import calc_importance
from run_tw_amihud20_ablation import (
    BASELINE_CONFIG,
    BASELINE_RECORDER,
    BASELINE_SUMMARY,
    END,
    FIT_END,
    MARKET,
    PROVIDER,
    ROOT,
    SEGMENTS,
    find_artifact_dir,
    load_indicators,
    load_model_segment_ic,
    load_report,
    paired_ttest,
    parse_stdout,
    risk_by_period,
    turnover_summary,
)

CONFIG = ROOT / "configs/tw_yahoo_primary_alpha158_idio_skew60.yaml"
MATERIALIZE_SCRIPT = ROOT / "examples/tw/materialize_tw_idio_skew60.py"
MATERIALIZE_DIR = ROOT / "data_tw/experiments/yahoo_primary_tw_idio_skew60_materialized"
BASELINE_IMPORTANCE = ROOT / "data_tw/experiments/yahoo_primary_alpha158_importance/alpha158_feature_importance.csv"
REPORT_PATH = ROOT / "docs/tw_audit/25_tw_idio_skew60_ablation_report.md"
FACTOR = "TW_IDIO_SKEW60"
NEAREST_ALPHA158 = "CORD60"


def run_materialization(out: Path) -> None:
    proc = subprocess.run(
        ["python", str(MATERIALIZE_SCRIPT.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    (out / "materialization.log").write_text(proc.stdout, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"materialization failed with returncode={proc.returncode}")


def feature_nan_summary() -> pd.DataFrame:
    handler = TWAlpha158IdioSkew60(
        instruments=MARKET,
        start_time="2015-05-04",
        end_time=END,
        fit_start_time="2015-05-04",
        fit_end_time=FIT_END,
    )
    raw = handler.fetch(col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_R)["feature"]
    rows = []
    for segment, (start, end) in SEGMENTS.items():
        seg = raw.loc[(slice(pd.Timestamp(start), pd.Timestamp(end)), slice(None)), [FACTOR]]
        finite = seg[FACTOR].notna()
        rows.append(
            {
                "segment": segment,
                "n_rows": int(seg.shape[0]),
                "finite_feature_rows": int(finite.sum()),
                "finite_feature_share": float(finite.mean()) if len(finite) else np.nan,
                "nan_share": float((~finite).mean()) if len(finite) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def candidate_importance(config_path: Path, recorder_id: str) -> pd.DataFrame:
    cfg = yaml.safe_load(config_path.read_text())
    dataset = init_instance_by_config(cfg["task"]["dataset"])
    features = dataset.handler.fetch(col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_R)["feature"]
    model = pd.read_pickle(find_artifact_dir(recorder_id) / "params.pkl")
    return calc_importance(model, list(features.columns))


def importance_comparison(candidate: pd.DataFrame) -> pd.DataFrame:
    baseline = pd.read_csv(BASELINE_IMPORTANCE)
    rows = []
    for feature in [FACTOR, NEAREST_ALPHA158]:
        b = baseline[baseline["feature_name"] == feature]
        c = candidate[candidate["feature_name"] == feature]
        rows.append(
            {
                "feature_name": feature,
                "baseline_gain_rank": int(b["gain_rank"].iloc[0]) if not b.empty else np.nan,
                "baseline_gain_share": float(b["gain_share"].iloc[0]) if not b.empty else np.nan,
                "candidate_gain_rank": int(c["gain_rank"].iloc[0]) if not c.empty else np.nan,
                "candidate_gain_share": float(c["gain_share"].iloc[0]) if not c.empty else np.nan,
                "candidate_split_rank": int(c["split_rank"].iloc[0]) if not c.empty else np.nan,
                "candidate_split_share": float(c["split_share"].iloc[0]) if not c.empty else np.nan,
            }
        )
    return pd.DataFrame(rows)


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


def write_report(out: Path, summary: dict, validation: pd.DataFrame, nan_summary: pd.DataFrame, model_ic: pd.DataFrame, risk: pd.DataFrame, paired: pd.DataFrame, turnover: pd.DataFrame, importance: pd.DataFrame, importance_detail: pd.DataFrame) -> None:
    ric = model_ic[model_ic["metric"] == "rank_ic"]
    factor_row = importance[importance["feature_name"] == FACTOR]
    factor_rank = factor_row["candidate_gain_rank"].iloc[0] if not factor_row.empty else np.nan
    factor_gain = factor_row["candidate_gain_share"].iloc[0] if not factor_row.empty else np.nan
    lines = [
        "---",
        "created_at: 2026-05-27",
        "status: ablation_complete",
        "scope: tw_idio_skew60_fixed_parameter_ablation",
        "related_docs:",
        "  - docs/tw_audit/23_tw_idio_skew60_ablation_data_expansion_work_order.md",
        "  - docs/tw_audit/24_claude_audit_round_9_work_order_review.md",
        "---",
        "",
        "# TW_IDIO_SKEW60 Fixed Ablation Report",
        "",
        "## Scope",
        "",
        "This fixed ablation compares Alpha158-only against Alpha158 + materialized raw TW_IDIO_SKEW60. Provider, market, benchmark, split, LightGBM hyperparameters, strategy parameters, cost model and 2025-06-30 cutoff are unchanged. No data after 2025-06-30 is accessed by this run.",
        "",
        "Weak-signal caveat: standalone TW_IDIO_SKEW60 IC is weaker than rejected TW_AMIHUD20. This ablation is primarily a Tier 2 closure experiment; promotion requires actual model and portfolio improvement, not the screen pass alone.",
        "",
        "NaN handling note: the Alpha158/TW handler uses label-only learn processors (`DropnaLabel` and label `CSZScoreNorm`) and no feature fill processor in this config; feature NaNs are passed to LightGBM, which handles missing values natively.",
        "",
        "## Summary",
        "",
        f"- candidate recorder: `{summary.get('recorder_id', '')}`",
        f"- baseline recorder: `{BASELINE_RECORDER}`",
        f"- test RankIC delta: `{fmt(summary.get('rank_ic_delta'))}`",
        f"- with-cost annualized excess delta: `{fmt(summary.get('with_cost_ann_delta'))}`",
        f"- with-cost IR delta: `{fmt(summary.get('with_cost_ir_delta'))}`",
        f"- TW_IDIO_SKEW60 candidate gain rank: `{fmt(factor_rank)}`",
        f"- TW_IDIO_SKEW60 candidate gain share: `{fmt(factor_gain)}`",
        "",
        "## Materialization Validation",
        "",
        "Validation compares Qlib-loaded `$tw_idio_skew60` values against the screening script output after float32 bin-format casting. The required tolerance is `< 1e-8` against the float32 reference.",
        "",
    ]
    lines += table(validation, ["instrument", "datetime", "screen_value", "screen_value_float32", "materialized_value", "abs_diff_vs_float32_screen", "pass_float32_tolerance_1e_8"])
    lines += ["", "## Feature NaN Share", ""] + table(nan_summary, ["segment", "n_rows", "finite_feature_rows", "finite_feature_share", "nan_share"])
    lines += ["", "## Model RankIC By Segment", ""] + table(ric, ["model", "segment", "n_days", "mean", "ir", "positive_rate", "avg_n"])
    lines += ["", "## Portfolio Risk By Test Segment", "", "Note: `annualized_excess` is computed as `mean(daily_excess) * 252`; use summary deltas for cross-report comparison.", ""] + table(risk, ["model", "segment", "n_days", "annualized_excess", "ir", "max_drawdown"])
    lines += ["", "## Paired Daily Excess Test", ""] + table(paired, ["n_days", "daily_excess_mean_diff", "paired_t_p_value", "same_direction_positive"])
    lines += ["", "## Turnover", ""] + table(turnover, ["model", "daily_turnover_mean", "annualized_turnover", "turnover_n_days"])
    lines += ["", "## Feature Importance Rank of TW_IDIO_SKEW60", ""] + table(importance, ["feature_name", "baseline_gain_rank", "baseline_gain_share", "candidate_gain_rank", "candidate_gain_share", "candidate_split_rank", "candidate_split_share"])
    lines += ["", "## Top Candidate Feature Importance", ""] + table(importance_detail.head(20), ["feature_name", "gain_rank", "gain_share", "split_rank", "split_share"])
    lines += ["", "## Decision", ""]
    if pd.notna(summary.get("rank_ic_delta")) and summary.get("rank_ic_delta") >= 0.005 and summary.get("with_cost_ann_delta", -np.inf) >= 0 and pd.notna(factor_rank) and factor_rank <= 100:
        lines.append("- Candidate passes the mechanical promotion checks pending audit review.")
    else:
        lines.append("- Candidate does not satisfy the full promotion standard; keep/reject decision should be confirmed in round 10 audit.")
    if pd.notna(factor_rank) and factor_rank > 100:
        lines.append("- AC-9 warning: TW_IDIO_SKEW60 gain rank is worse than 100, indicating weak model usage.")
    lines += ["", "## Artifacts", ""]
    for f in sorted(out.iterdir()):
        if f.is_file():
            lines.append(f"- `{f.relative_to(ROOT)}`")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fixed Alpha158 + TW_IDIO_SKEW60 ablation.")
    parser.add_argument("--output-dir", default="data_tw/experiments/yahoo_primary_tw_idio_skew60_ablation")
    args = parser.parse_args()
    out = ROOT / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CONFIG, out / "idio_skew60_config_snapshot.yaml")

    run_materialization(out)
    validation = pd.read_csv(MATERIALIZE_DIR / "tw_idio_skew60_materialization_validation.csv")
    validation.to_csv(out / "tw_idio_skew60_materialization_validation.csv", index=False)
    manifest = pd.read_csv(MATERIALIZE_DIR / "tw_idio_skew60_materialization_manifest.csv")
    manifest.to_csv(out / "tw_idio_skew60_materialization_manifest.csv", index=False)
    if not validation["pass_float32_tolerance_1e_8"].all():
        raise RuntimeError("materialization validation failed")

    proc = subprocess.run(["python", "qlib/cli/run.py", str(CONFIG)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    log_path = out / "idio_skew60.log"
    log_path.write_text(proc.stdout, encoding="utf-8")
    row = {"name": "alpha158_idio_skew60", "returncode": proc.returncode, "baseline_recorder_id": BASELINE_RECORDER, "config_path": str(CONFIG.relative_to(ROOT)), "log_path": str(log_path.relative_to(ROOT))}
    row.update(parse_stdout(proc.stdout))
    if row.get("recorder_id"):
        (out / "idio_skew60_recorder_id.txt").write_text(str(row["recorder_id"]) + "\n", encoding="utf-8")
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
    nan_summary = feature_nan_summary()
    nan_summary.to_csv(out / "idio_skew60_nan_summary.csv", index=False)

    base_daily_ic, base_ic_summary = load_model_segment_ic(BASELINE_CONFIG, BASELINE_RECORDER, "baseline_alpha158")
    cand_daily_ic, cand_ic_summary = load_model_segment_ic(CONFIG, str(row["recorder_id"]), "alpha158_idio_skew60")
    model_ic = pd.concat([base_ic_summary, cand_ic_summary], ignore_index=True)
    model_ic.to_csv(out / "model_segment_ic.csv", index=False)
    pd.concat([base_daily_ic.assign(model="baseline_alpha158"), cand_daily_ic.assign(model="alpha158_idio_skew60")], ignore_index=True).to_csv(out / "model_daily_ic.csv", index=False)

    base_report = load_report(BASELINE_RECORDER).rename(columns={"return": "baseline_return", "bench": "baseline_bench", "excess": "baseline_excess"})
    cand_report = load_report(str(row["recorder_id"])).rename(columns={"return": "candidate_return", "bench": "candidate_bench", "excess": "candidate_excess"})
    paired = base_report[["date", "baseline_return", "baseline_bench", "baseline_excess"]].merge(cand_report[["date", "candidate_return", "candidate_bench", "candidate_excess"]], on="date", how="inner")
    paired["candidate_minus_baseline_excess"] = paired["candidate_excess"] - paired["baseline_excess"]
    paired.to_csv(out / "paired_daily_excess.csv", index=False)
    paired_summary = pd.DataFrame([{"baseline_recorder_id": BASELINE_RECORDER, "candidate_recorder_id": row["recorder_id"], **paired_ttest(paired["baseline_excess"], paired["candidate_excess"])}])
    paired_summary.to_csv(out / "paired_ttest_summary.csv", index=False)

    risk = pd.concat([risk_by_period(load_report(BASELINE_RECORDER), "baseline_alpha158"), risk_by_period(load_report(str(row["recorder_id"])), "alpha158_idio_skew60")], ignore_index=True)
    risk.to_csv(out / "portfolio_risk_by_segment.csv", index=False)
    turnover = pd.DataFrame([turnover_summary(load_report(BASELINE_RECORDER), load_indicators(BASELINE_RECORDER), "baseline_alpha158"), turnover_summary(load_report(str(row["recorder_id"]),), load_indicators(str(row["recorder_id"])), "alpha158_idio_skew60")])
    turnover.to_csv(out / "turnover_summary.csv", index=False)

    cand_importance = candidate_importance(CONFIG, str(row["recorder_id"]))
    cand_importance.to_csv(out / "candidate_feature_importance.csv", index=False)
    imp_compare = importance_comparison(cand_importance)
    imp_compare.to_csv(out / "feature_importance_comparison.csv", index=False)

    write_report(out, row, validation, nan_summary, model_ic, risk, paired_summary, turnover, imp_compare, cand_importance)
    print(f"returncode={proc.returncode}")
    print(f"recorder_id={row.get('recorder_id', '')}")
    print(f"rank_ic_delta={row.get('rank_ic_delta')}")
    print(f"with_cost_ann_delta={row.get('with_cost_ann_delta')}")
    print(f"wrote {out.relative_to(ROOT)}")
    print(f"wrote {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
