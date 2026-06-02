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
    find_artifact_dir,
    load_indicators,
    load_model_segment_ic,
    load_report,
    paired_ttest,
    parse_stdout,
    risk_by_period,
    turnover_summary,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/tw_yahoo_primary_alpha158_margin_util.yaml"
REPORT_PATH = ROOT / "docs/tw_audit/41_tw_margin_util_ablation_report.md"
OUT_DIR_DEFAULT = "data_tw/experiments/yahoo_primary_tw_margin_util_ablation"


def candidate_importance(config_path: Path, recorder_id: str) -> pd.DataFrame:
    import yaml
    from qlib.utils import init_instance_by_config

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    model = pd.read_pickle(find_artifact_dir(recorder_id) / "params.pkl")
    handler = init_instance_by_config(cfg["task"]["dataset"]["kwargs"]["handler"])
    names = handler.get_feature_config()[1]
    gain = model.model.feature_importance(importance_type="gain")
    split = model.model.feature_importance(importance_type="split")
    out = pd.DataFrame({"feature_name": names, "gain": gain, "split": split})
    out["gain_rank"] = out["gain"].rank(ascending=False, method="min").astype(int)
    out["split_rank"] = out["split"].rank(ascending=False, method="min").astype(int)
    total_gain = out["gain"].sum()
    total_split = out["split"].sum()
    out["gain_share"] = out["gain"] / total_gain if total_gain else np.nan
    out["split_share"] = out["split"] / total_split if total_split else np.nan
    return out.sort_values(["gain_rank", "split_rank", "feature_name"]).reset_index(drop=True)


def build_summary(row: dict, paired: pd.DataFrame, turnover: pd.DataFrame, importance: pd.DataFrame) -> dict:
    baseline = pd.read_csv(BASELINE_SUMMARY).iloc[0].to_dict()
    row["rank_ic_delta"] = row.get("rank_ic") - baseline.get("rank_ic") if row.get("rank_ic") is not None else np.nan
    row["ic_delta"] = row.get("ic") - baseline.get("ic") if row.get("ic") is not None else np.nan
    row["with_cost_ann_delta"] = row.get("with_cost_annualized_return") - baseline.get("with_cost_annualized_return") if row.get("with_cost_annualized_return") is not None else np.nan
    row["with_cost_ir_delta"] = row.get("with_cost_information_ratio") - baseline.get("with_cost_information_ratio") if row.get("with_cost_information_ratio") is not None else np.nan
    base_turn = turnover.loc[turnover["model"] == "baseline_alpha158", "daily_turnover_mean"].iloc[0]
    cand_turn = turnover.loc[turnover["model"] == "alpha158_margin_util", "daily_turnover_mean"].iloc[0]
    row["turnover_increase_pct"] = (cand_turn / base_turn - 1.0) if base_turn else np.nan
    row["paired_daily_excess_mean_diff"] = paired["daily_excess_mean_diff"].iloc[0] if not paired.empty else np.nan
    row["paired_t_p_value"] = paired["paired_t_p_value"].iloc[0] if not paired.empty else np.nan
    mask = importance["feature_name"] == "TW_MARGIN_UTIL"
    row["tw_margin_util_gain_rank"] = importance.loc[mask, "gain_rank"].iloc[0] if mask.any() else np.nan
    row["tw_margin_util_gain_share"] = importance.loc[mask, "gain_share"].iloc[0] if mask.any() else np.nan
    return row


def decision(summary: dict) -> tuple[str, list[str]]:
    checks = [
        ("delta_rank_ic_or_ic_ge_0.005", max(summary.get("rank_ic_delta", np.nan), summary.get("ic_delta", np.nan)) >= 0.005),
        ("paired_p_lt_0.1_and_positive", summary.get("paired_t_p_value", np.nan) < 0.1 and summary.get("paired_daily_excess_mean_diff", np.nan) > 0),
        ("with_cost_not_worse", summary.get("with_cost_ann_delta", np.nan) >= 0),
        ("turnover_increase_lt_20pct", summary.get("turnover_increase_pct", np.nan) < 0.20),
    ]
    failed = [name for name, ok in checks if not ok]
    return ("pass_ablation" if not failed else "reject_ablation"), failed


def fmt(x):
    if pd.isna(x):
        return ""
    if isinstance(x, (float, np.floating)):
        return f"{x:.6e}" if x != 0 and abs(x) < 1e-4 else f"{x:.6f}"
    return str(x)




def table(df: pd.DataFrame, cols: list[str]) -> list[str]:
    if df.empty:
        return ["(empty)"]
    d = df[cols].copy()
    for c in d.columns:
        d[c] = d[c].map(fmt)
    lines = ["| " + " | ".join(d.columns) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in d.to_numpy(dtype=str)]
    return lines

def write_report(out: Path, summary: dict, model_ic: pd.DataFrame, risk: pd.DataFrame, paired: pd.DataFrame, turnover: pd.DataFrame, importance: pd.DataFrame) -> None:
    ric = model_ic[model_ic["metric"] == "rank_ic"]
    verdict, failed = decision(summary)
    gate_rows = pd.DataFrame([
        {"gate": "Delta RankIC or IC >= 0.005", "value": max(summary.get("rank_ic_delta", np.nan), summary.get("ic_delta", np.nan)), "pass": "delta_rank_ic_or_ic_ge_0.005" not in failed},
        {"gate": "paired daily excess p < 0.1 and mean diff > 0", "value": summary.get("paired_t_p_value"), "pass": "paired_p_lt_0.1_and_positive" not in failed},
        {"gate": "with-cost annualized excess not worse", "value": summary.get("with_cost_ann_delta"), "pass": "with_cost_not_worse" not in failed},
        {"gate": "turnover increase < 20%", "value": summary.get("turnover_increase_pct"), "pass": "turnover_increase_lt_20pct" not in failed},
    ])
    lines = [
        "---",
        "created_at: 2026-05-28",
        "status: margin_util_ablation_complete",
        "scope: phase_d7_tw_margin_util_fixed_parameter_ablation",
        "related_docs:",
        "  - docs/tw_audit/40_tw_margin_batch_a_screening_report.md",
        "  - docs/tw_audit/41_claude_audit_round_21_margin_batch_a_screening.md",
        "script:",
        "  - examples/tw/run_tw_margin_util_ablation.py",
        "---",
        "",
        "# TW_MARGIN_UTIL Fixed-Parameter Ablation",
        "",
        "## Scope",
        "",
        "This fixed ablation compares the existing Alpha158 baseline against Alpha158 + raw `$tw_margin_util`. Provider, market, benchmark, split, LightGBM parameters, strategy parameters, transaction costs, and the 2025-06-30 cutoff are unchanged. It does not tune parameters, run Batch B, or promote the handler.",
        "",
        "## Summary",
        "",
        f"- candidate recorder: `{summary.get('recorder_id', '')}`",
        f"- baseline recorder: `{BASELINE_RECORDER}`",
        f"- test RankIC delta: `{fmt(summary.get('rank_ic_delta'))}`",
        f"- test IC delta: `{fmt(summary.get('ic_delta'))}`",
        f"- with-cost annualized excess delta: `{fmt(summary.get('with_cost_ann_delta'))}`",
        f"- paired p-value: `{fmt(summary.get('paired_t_p_value'))}`",
        f"- turnover increase: `{fmt(summary.get('turnover_increase_pct'))}`",
        f"- TW_MARGIN_UTIL gain rank/share: `{fmt(summary.get('tw_margin_util_gain_rank'))}` / `{fmt(summary.get('tw_margin_util_gain_share'))}`",
        f"- decision: `{verdict}`",
        "",
        "## Promotion Gates",
        "",
    ]
    lines += table(gate_rows, ["gate", "value", "pass"])
    lines += ["", "## Model RankIC By Segment", ""]
    lines += table(ric, ["model", "segment", "n_days", "mean", "ir", "positive_rate", "avg_n"])
    lines += ["", "## Portfolio Risk By Test Segment", "", "Note: `annualized_excess` is computed as `mean(daily_excess) * 252`; use summary deltas above for Qlib built-in cross-run deltas.", ""]
    lines += table(risk, ["model", "segment", "n_days", "annualized_excess", "ir", "max_drawdown"])
    lines += ["", "## Paired Daily Excess Test", ""]
    lines += table(paired, ["n_days", "daily_excess_mean_diff", "paired_t_p_value", "same_direction_positive"])
    lines += ["", "## Turnover", ""]
    lines += table(turnover, ["model", "daily_turnover_mean", "annualized_turnover", "turnover_n_days"])
    lines += ["", "## Candidate Feature Importance", ""]
    lines += table(importance.head(20), ["feature_name", "gain", "split", "gain_rank", "split_rank", "gain_share", "split_share"])
    lines += ["", "## Artifacts", ""]
    for f in sorted(out.iterdir()):
        if f.is_file():
            lines.append(f"- `{f.relative_to(ROOT)}`")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fixed Alpha158 + TW_MARGIN_UTIL ablation.")
    parser.add_argument("--output-dir", default=OUT_DIR_DEFAULT)
    args = parser.parse_args()
    out = ROOT / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CONFIG, out / "margin_util_config_snapshot.yaml")

    proc = subprocess.run(["python", "qlib/cli/run.py", str(CONFIG)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    log_path = out / "margin_util.log"
    log_path.write_text(proc.stdout, encoding="utf-8")
    row = {"name": "alpha158_margin_util", "returncode": proc.returncode, "baseline_recorder_id": BASELINE_RECORDER, "config_path": str(CONFIG.relative_to(ROOT)), "log_path": str(log_path.relative_to(ROOT))}
    row.update(parse_stdout(proc.stdout))
    if row.get("recorder_id"):
        (out / "margin_util_recorder_id.txt").write_text(str(row["recorder_id"]) + "\n", encoding="utf-8")
    pd.DataFrame([row]).to_csv(out / "summary_raw.csv", index=False)
    if proc.returncode != 0 or not row.get("recorder_id"):
        print(f"returncode={proc.returncode}")
        print(f"wrote {out.relative_to(ROOT)}")
        raise SystemExit(proc.returncode)

    qlib.init(provider_uri=PROVIDER, region="tw", expression_cache=None, dataset_cache=None)
    base_daily_ic, base_ic_summary = load_model_segment_ic(BASELINE_CONFIG, BASELINE_RECORDER, "baseline_alpha158")
    cand_daily_ic, cand_ic_summary = load_model_segment_ic(CONFIG, str(row["recorder_id"]), "alpha158_margin_util")
    model_ic = pd.concat([base_ic_summary, cand_ic_summary], ignore_index=True)
    model_ic.to_csv(out / "model_segment_ic.csv", index=False)
    pd.concat([base_daily_ic.assign(model="baseline_alpha158"), cand_daily_ic.assign(model="alpha158_margin_util")], ignore_index=True).to_csv(out / "model_daily_ic.csv", index=False)

    base_report = load_report(BASELINE_RECORDER).rename(columns={"return": "baseline_return", "bench": "baseline_bench", "excess": "baseline_excess"})
    cand_report = load_report(str(row["recorder_id"])).rename(columns={"return": "candidate_return", "bench": "candidate_bench", "excess": "candidate_excess"})
    paired_daily = base_report[["date", "baseline_return", "baseline_bench", "baseline_excess"]].merge(cand_report[["date", "candidate_return", "candidate_bench", "candidate_excess"]], on="date", how="inner")
    paired_daily["candidate_minus_baseline_excess"] = paired_daily["candidate_excess"] - paired_daily["baseline_excess"]
    paired_daily.to_csv(out / "paired_daily_excess.csv", index=False)
    paired = pd.DataFrame([{"baseline_recorder_id": BASELINE_RECORDER, "candidate_recorder_id": row["recorder_id"], **paired_ttest(paired_daily["baseline_excess"], paired_daily["candidate_excess"])}])
    paired.to_csv(out / "paired_ttest_summary.csv", index=False)

    risk = pd.concat([risk_by_period(load_report(BASELINE_RECORDER), "baseline_alpha158"), risk_by_period(load_report(str(row["recorder_id"])), "alpha158_margin_util")], ignore_index=True)
    risk.to_csv(out / "portfolio_risk_by_segment.csv", index=False)
    turnover = pd.DataFrame([turnover_summary(load_report(BASELINE_RECORDER), load_indicators(BASELINE_RECORDER), "baseline_alpha158"), turnover_summary(load_report(str(row["recorder_id"])), load_indicators(str(row["recorder_id"])), "alpha158_margin_util")])
    turnover.to_csv(out / "turnover_summary.csv", index=False)
    importance = candidate_importance(CONFIG, str(row["recorder_id"]))
    importance.to_csv(out / "candidate_feature_importance.csv", index=False)

    summary = build_summary(row, paired, turnover, importance)
    pd.DataFrame([summary]).to_csv(out / "summary.csv", index=False)
    write_report(out, summary, model_ic, risk, paired, turnover, importance)

    verdict, failed = decision(summary)
    print(f"returncode={proc.returncode}")
    print(f"recorder_id={row.get('recorder_id', '')}")
    print(f"rank_ic_delta={summary.get('rank_ic_delta')}")
    print(f"ic_delta={summary.get('ic_delta')}")
    print(f"with_cost_ann_delta={summary.get('with_cost_ann_delta')}")
    print(f"paired_p={summary.get('paired_t_p_value')}")
    print(f"turnover_increase_pct={summary.get('turnover_increase_pct')}")
    print(f"decision={verdict}")
    print(f"failed_gates={','.join(failed)}")
    print(f"wrote {out.relative_to(ROOT)}")
    print(f"wrote {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
