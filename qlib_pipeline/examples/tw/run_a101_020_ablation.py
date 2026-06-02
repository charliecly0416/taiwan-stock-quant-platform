from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[2]
BASELINE_RECORDER = "950741cfd5f14ee5a05464fec3e12e0a"
CONFIG = ROOT / "configs/tw_yahoo_primary_alpha158_a101_020.yaml"
BASELINE_SUMMARY = ROOT / "data_tw/experiments/yahoo_primary_alpha158_baseline/summary.csv"


def parse_metric(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text)
    return float(match.group(1)) if match else None


def parse_risk_section(text: str, title: str) -> dict[str, float | None]:
    idx = text.find(title)
    if idx < 0:
        return {}
    section = text[idx : idx + 700]
    return {
        "mean": parse_metric(r"mean\s+([-+0-9.eE]+)", section),
        "std": parse_metric(r"std\s+([-+0-9.eE]+)", section),
        "annualized_return": parse_metric(r"annualized_return\s+([-+0-9.eE]+)", section),
        "information_ratio": parse_metric(r"information_ratio\s+([-+0-9.eE]+)", section),
        "max_drawdown": parse_metric(r"max_drawdown\s+([-+0-9.eE]+)", section),
    }


def parse_stdout(text: str) -> dict[str, str | float | None]:
    result: dict[str, str | float | None] = {}
    rec = re.findall(r"Recorder ([0-9a-f]+) starts running", text)
    result["recorder_id"] = rec[-1] if rec else ""
    result["ic"] = parse_metric(r"'IC': np\.float64\(([-+0-9.eE]+)\)", text)
    result["icir"] = parse_metric(r"'ICIR': np\.float64\(([-+0-9.eE]+)\)", text)
    result["rank_ic"] = parse_metric(r"'Rank IC': np\.float64\(([-+0-9.eE]+)\)", text)
    result["rank_icir"] = parse_metric(r"'Rank ICIR': np\.float64\(([-+0-9.eE]+)\)", text)
    result.update({f"without_cost_{k}": v for k, v in parse_risk_section(text, "excess return without cost").items()})
    result.update({f"with_cost_{k}": v for k, v in parse_risk_section(text, "excess return with cost").items()})
    return result


def load_report(recorder_id: str) -> pd.DataFrame:
    matches = list((ROOT / "mlruns").glob(f"*/{recorder_id}/artifacts/portfolio_analysis/report_normal_1day.pkl"))
    if not matches:
        matches = list((ROOT / "mlruns").glob(f"*/*{recorder_id}*/artifacts/portfolio_analysis/report_normal_1day.pkl"))
    if not matches:
        raise FileNotFoundError(f"report not found for recorder {recorder_id}")
    df = pd.read_pickle(matches[0]).reset_index().rename(columns={"datetime": "date"})
    df["excess"] = df["return"] - df["bench"]
    return df[["date", "return", "bench", "excess"]]


def paired_ttest(base: pd.Series, cand: pd.Series) -> dict[str, float | int | bool]:
    diff = (cand - base).dropna()
    if len(diff) < 3:
        return {"n_days": int(len(diff)), "daily_excess_mean_diff": np.nan, "paired_t_p_value": np.nan, "same_direction_positive": False}
    res = stats.ttest_1samp(diff, 0.0, nan_policy="omit")
    return {
        "n_days": int(len(diff)),
        "daily_excess_mean_diff": float(diff.mean()),
        "paired_t_p_value": float(res.pvalue),
        "same_direction_positive": bool(diff.mean() > 0),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = sorted({k for row in rows for k in row})
    preferred = [
        "name",
        "returncode",
        "recorder_id",
        "baseline_recorder_id",
        "ic",
        "rank_ic",
        "rank_ic_delta",
        "with_cost_annualized_return",
        "with_cost_ann_delta",
        "with_cost_information_ratio",
        "with_cost_ir_delta",
        "with_cost_max_drawdown",
        "config_path",
        "log_path",
    ]
    fields = preferred + [f for f in fields if f not in preferred]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fixed Alpha158 + A101_020 ablation and paired daily-return test.")
    parser.add_argument("--output-dir", default="data_tw/experiments/yahoo_primary_a101_020_ablation")
    args = parser.parse_args()

    out = ROOT / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CONFIG, out / "a101_020_config_snapshot.yaml")

    proc = subprocess.run(
        ["python", "qlib/cli/run.py", str(CONFIG)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path = out / "a101_020.log"
    log_path.write_text(proc.stdout, encoding="utf-8")

    baseline = pd.read_csv(BASELINE_SUMMARY).iloc[0].to_dict()
    row = {
        "name": "alpha158_a101_020",
        "returncode": proc.returncode,
        "baseline_recorder_id": BASELINE_RECORDER,
        "config_path": str(CONFIG.relative_to(ROOT)),
        "log_path": str(log_path.relative_to(ROOT)),
    }
    row.update(parse_stdout(proc.stdout))
    if row.get("recorder_id"):
        (out / "a101_020_recorder_id.txt").write_text(str(row["recorder_id"]) + "\n", encoding="utf-8")
    row["rank_ic_delta"] = row.get("rank_ic") - baseline.get("rank_ic") if row.get("rank_ic") is not None else np.nan
    row["with_cost_ann_delta"] = (
        row.get("with_cost_annualized_return") - baseline.get("with_cost_annualized_return")
        if row.get("with_cost_annualized_return") is not None
        else np.nan
    )
    row["with_cost_ir_delta"] = (
        row.get("with_cost_information_ratio") - baseline.get("with_cost_information_ratio")
        if row.get("with_cost_information_ratio") is not None
        else np.nan
    )

    write_csv(out / "summary.csv", [row])

    if proc.returncode == 0 and row.get("recorder_id"):
        base_daily = load_report(BASELINE_RECORDER).rename(columns={"return": "baseline_return", "bench": "baseline_bench", "excess": "baseline_excess"})
        cand_daily = load_report(str(row["recorder_id"])).rename(columns={"return": "candidate_return", "bench": "candidate_bench", "excess": "candidate_excess"})
        paired = base_daily.merge(cand_daily, on="date", how="inner")
        paired["candidate_minus_baseline_excess"] = paired["candidate_excess"] - paired["baseline_excess"]
        paired.to_csv(out / "paired_daily_excess.csv", index=False)
        paired_row = {
            "baseline_recorder_id": BASELINE_RECORDER,
            "candidate_recorder_id": row["recorder_id"],
            **paired_ttest(paired["baseline_excess"], paired["candidate_excess"]),
        }
        pd.DataFrame([paired_row]).to_csv(out / "paired_ttest_summary.csv", index=False)

    print(f"returncode={proc.returncode}")
    print(f"recorder_id={row.get('recorder_id', '')}")
    print(f"rank_ic_delta={row.get('rank_ic_delta')}")
    print(f"with_cost_ann_delta={row.get('with_cost_ann_delta')}")
    print(f"wrote {out.relative_to(ROOT)}")
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
