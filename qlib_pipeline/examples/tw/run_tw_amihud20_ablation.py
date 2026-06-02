from __future__ import annotations

import argparse
import csv
import math
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import qlib
import yaml
from scipy import stats

from qlib.contrib.data.handler import Alpha158
from qlib.data.dataset import DataHandlerLP as BaseDataHandlerLP
from qlib.data.dataset.handler import DataHandlerLP
from qlib.data.dataset.processor import DropnaLabel
from qlib.utils import init_instance_by_config


ROOT = Path(__file__).resolve().parents[2]
BASELINE_RECORDER = "950741cfd5f14ee5a05464fec3e12e0a"
BASELINE_CONFIG = ROOT / "configs/tw_yahoo_primary_alpha158.yaml"
CONFIG = ROOT / "configs/tw_yahoo_primary_alpha158_amihud20.yaml"
BASELINE_SUMMARY = ROOT / "data_tw/experiments/yahoo_primary_alpha158_baseline/summary.csv"
PROVIDER = "data_tw/experiments/yahoo_adjusted_primary/qlib_bin"
MARKET = "tw_liquid_dyn"
START = "2015-05-04"
END = "2025-06-30"
FIT_END = "2020-12-31"
SEGMENTS = {
    "train": ("2015-05-04", "2020-12-31"),
    "valid": ("2021-01-01", "2022-12-31"),
    "test": ("2023-01-01", "2025-06-30"),
    "test_2023": ("2023-01-01", "2023-12-31"),
    "test_2024": ("2024-01-01", "2024-12-31"),
    "test_2025h1": ("2025-01-01", "2025-06-30"),
}


class RawAmihudHandler(BaseDataHandlerLP):
    def __init__(self):
        fields = ["$close", "Ref($close, 1)", "$volume", "$vwap"]
        names = ["CLOSE0", "CLOSE_REF1", "VOLUME0", "VWAP0"]
        loader = {
            "class": "QlibDataLoader",
            "kwargs": {
                "config": {
                    "feature": (fields, names),
                    "label": (["Ref($close, -2)/Ref($close, -1) - 1"], ["LABEL0"]),
                },
                "freq": "day",
            },
        }
        super().__init__(
            instruments=MARKET,
            start_time=START,
            end_time=END,
            data_loader=loader,
            learn_processors=[DropnaLabel()],
            infer_processors=[],
            process_type=DataHandlerLP.PTYPE_A,
        )


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


def find_artifact_dir(recorder_id: str) -> Path:
    matches = list((ROOT / "mlruns").glob(f"*/{recorder_id}/artifacts"))
    if not matches:
        raise FileNotFoundError(f"artifact dir not found for recorder {recorder_id}")
    return matches[0]


def load_report(recorder_id: str) -> pd.DataFrame:
    df = pd.read_pickle(find_artifact_dir(recorder_id) / "portfolio_analysis/report_normal_1day.pkl")
    df = df.reset_index().rename(columns={"datetime": "date"})
    df["excess"] = df["return"] - df["bench"]
    return df


def load_indicators(recorder_id: str) -> pd.DataFrame:
    df = pd.read_pickle(find_artifact_dir(recorder_id) / "portfolio_analysis/indicators_normal_1day.pkl")
    return df.reset_index().rename(columns={"index": "date"})


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


def calc_daily_ic(pred: pd.Series, label: pd.Series) -> pd.DataFrame:
    data = pd.DataFrame({"score": pred, "label": label}).dropna()
    rows = []
    for date, g in data.groupby(level="datetime", sort=True):
        if g.shape[0] < 10 or g["score"].nunique() < 2 or g["label"].nunique() < 2:
            continue
        rows.append({
            "date": pd.Timestamp(date),
            "n": int(g.shape[0]),
            "ic": float(g["score"].corr(g["label"], method="pearson")),
            "rank_ic": float(g["score"].corr(g["label"], method="spearman")),
        })
    return pd.DataFrame(rows)


def summarize_daily_ic(daily: pd.DataFrame, model_name: str) -> pd.DataFrame:
    rows = []
    for segment, (start, end) in SEGMENTS.items():
        seg = daily[(daily["date"] >= pd.Timestamp(start)) & (daily["date"] <= pd.Timestamp(end))]
        for metric in ["ic", "rank_ic"]:
            s = seg[metric].dropna()
            std = s.std()
            rows.append({
                "model": model_name,
                "segment": segment,
                "metric": metric,
                "n_days": int(s.shape[0]),
                "mean": float(s.mean()) if len(s) else np.nan,
                "std": float(std) if len(s) else np.nan,
                "ir": float(s.mean() / std) if len(s) and std else np.nan,
                "positive_rate": float((s > 0).mean()) if len(s) else np.nan,
                "avg_n": float(seg["n"].mean()) if len(seg) else np.nan,
            })
    return pd.DataFrame(rows)


def load_model_segment_ic(config_path: Path, recorder_id: str, model_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = yaml.safe_load(config_path.read_text())
    dataset = init_instance_by_config(cfg["task"]["dataset"])
    model = pd.read_pickle(find_artifact_dir(recorder_id) / "params.pkl")
    daily_frames = []
    for segment in ["train", "valid", "test"]:
        pred = model.predict(dataset, segment=segment)
        label = dataset.prepare(segment, col_set="label", data_key=DataHandlerLP.DK_R).iloc[:, 0]
        daily = calc_daily_ic(pred, label)
        daily["segment_source"] = segment
        daily_frames.append(daily)
    daily_all = pd.concat(daily_frames, ignore_index=True)
    summary = summarize_daily_ic(daily_all, model_name)
    return daily_all, summary


def risk_by_period(report: pd.DataFrame, name: str) -> pd.DataFrame:
    rows = []
    for segment, (start, end) in {k: v for k, v in SEGMENTS.items() if k.startswith("test")}.items():
        seg = report[(report["date"] >= pd.Timestamp(start)) & (report["date"] <= pd.Timestamp(end))]
        s = seg["excess"].dropna()
        nav = (1 + s).cumprod()
        drawdown = nav / nav.cummax() - 1 if len(nav) else pd.Series(dtype=float)
        std = s.std()
        rows.append({
            "model": name,
            "segment": segment,
            "n_days": int(s.shape[0]),
            "mean_excess": float(s.mean()) if len(s) else np.nan,
            "annualized_excess": float(s.mean() * 252) if len(s) else np.nan,
            "ir": float(s.mean() / std * math.sqrt(252)) if len(s) and std else np.nan,
            "max_drawdown": float(drawdown.min()) if len(drawdown) else np.nan,
        })
    return pd.DataFrame(rows)


def turnover_summary(report: pd.DataFrame, indicators: pd.DataFrame, name: str) -> dict[str, float | str]:
    df = indicators.merge(report[["date", "account"]], on="date", how="left")
    turnover = (df["deal_amount"] / df["account"].replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).dropna()
    return {
        "model": name,
        "daily_turnover_mean": float(turnover.mean()) if len(turnover) else np.nan,
        "annualized_turnover": float(turnover.mean() * 252) if len(turnover) else np.nan,
        "turnover_n_days": int(turnover.shape[0]),
    }


def compute_amihud_features() -> tuple[pd.DataFrame, pd.Series]:
    handler = RawAmihudHandler()
    raw = handler.fetch(col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_R)
    f = raw["feature"]
    label = raw["label"]["LABEL0"]
    close = f["CLOSE0"]
    ref1 = f["CLOSE_REF1"]
    volume = f["VOLUME0"]
    vwap = f["VWAP0"]
    ret = close / ref1 - 1
    valid = (volume > 0) & (vwap > 0) & (close > 0) & ret.notna()
    valid_count = valid.astype(float).groupby(level="instrument").transform(lambda s: s.rolling(20, min_periods=1).sum())
    def roll(price):
        raw_illiq = ret.abs() / (volume * price + 1e-12)
        inp = raw_illiq.mask(~valid)
        out = inp.groupby(level="instrument").transform(lambda s: s.rolling(20, min_periods=10).mean())
        return out.mask(valid_count < 10)
    feat = pd.DataFrame({
        "TW_AMIHUD20_VWAP": roll(vwap),
        "TW_AMIHUD20_CLOSE": roll(close),
        "valid_obs20": valid_count,
    }, index=f.index)
    return feat, label


def feature_rankic(feature: pd.Series, label: pd.Series, segment: str) -> float:
    start, end = SEGMENTS[segment]
    df = pd.DataFrame({"feature": feature, "label": label}).loc[(slice(pd.Timestamp(start), pd.Timestamp(end)), slice(None)), :].dropna()
    rows = []
    for _, g in df.groupby(level="datetime", sort=True):
        if g.shape[0] >= 10 and g["feature"].nunique() > 1 and g["label"].nunique() > 1:
            rows.append(g["feature"].corr(g["label"], method="spearman"))
    return float(pd.Series(rows).mean()) if rows else np.nan


def pre_ablation_diagnostics(alpha158: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    feat, label = compute_amihud_features()
    rows = []
    for segment in ["train", "valid", "test"]:
        start, end = SEGMENTS[segment]
        s = feat["TW_AMIHUD20_VWAP"].loc[(slice(pd.Timestamp(start), pd.Timestamp(end)), slice(None))].dropna()
        p50, p95, p99 = s.quantile([0.5, 0.95, 0.99]) if len(s) else (np.nan, np.nan, np.nan)
        rows.append({"segment": segment, "p50": p50, "p95": p95, "p99": p99, "p99_p50_ratio": p99 / p50 if p50 else np.nan})
    magnitude = pd.DataFrame(rows)
    daily_max = feat["TW_AMIHUD20_VWAP"].loc[(slice(pd.Timestamp("2023-01-01"), pd.Timestamp("2025-06-30")), slice(None))].groupby(level="datetime").max().dropna()
    daily_max_summary = pd.DataFrame([{
        "segment": "test",
        "daily_max_p50": float(daily_max.quantile(0.5)),
        "daily_max_p95": float(daily_max.quantile(0.95)),
        "daily_max_max": float(daily_max.max()),
    }])
    valid = feat["valid_obs20"].dropna()
    valid_obs = pd.DataFrame([{
        "share_valid_obs_lt15": float((valid < 15).mean()),
        "p01": float(valid.quantile(0.01)),
        "p05": float(valid.quantile(0.05)),
        "p50": float(valid.quantile(0.5)),
    }])
    sensitivity = pd.DataFrame([{
        "segment": "test",
        "rankic_vwap": feature_rankic(feat["TW_AMIHUD20_VWAP"], label, "test"),
        "rankic_close": feature_rankic(feat["TW_AMIHUD20_CLOSE"], label, "test"),
    }])
    sensitivity["abs_delta"] = (sensitivity["rankic_vwap"] - sensitivity["rankic_close"]).abs()
    return magnitude, daily_max_summary, valid_obs, sensitivity


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = sorted({k for row in rows for k in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_report(out: Path, summary: dict, model_ic: pd.DataFrame, risk: pd.DataFrame, paired: pd.DataFrame, turnover: pd.DataFrame, magnitude: pd.DataFrame, daily_max: pd.DataFrame, valid_obs: pd.DataFrame, sensitivity: pd.DataFrame) -> None:
    def fmt(x):
        if pd.isna(x):
            return ""
        if isinstance(x, float):
            return f"{x:.6e}" if x != 0 and abs(x) < 1e-4 else f"{x:.6f}"
        return str(x)
    def table(df, cols):
        d = df[cols].copy()
        for c in d.columns:
            d[c] = d[c].map(fmt)
        lines = ["| " + " | ".join(d.columns) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
        lines += ["| " + " | ".join(row) + " |" for row in d.to_numpy(dtype=str)]
        return lines
    ric = model_ic[model_ic["metric"] == "rank_ic"]
    lines = [
        "---",
        "created_at: 2026-05-27",
        "status: ablation_complete",
        "scope: tw_amihud20_fixed_parameter_ablation",
        "related_docs:",
        "  - docs/tw_audit/18_tw_amihud20_ablation_work_order.md",
        "---",
        "",
        "# TW_AMIHUD20 Fixed Ablation Report",
        "",
        "## Scope",
        "",
        "This fixed ablation compares Alpha158-only against Alpha158 + raw TW_AMIHUD20. Provider, market, benchmark, split, LightGBM hyperparameters, strategy parameters, cost model and 2025-06-30 cutoff are unchanged. No data after 2025-06-30 is accessed.",
        "",
        "TW_AMIHUD20 uses zero-volume exclusion before rolling, rolling window 20, min_periods 10, and volume * vwap as the primary traded-amount proxy. Observed standalone RankIC direction is negative; the raw sign is kept because the current GBDT model is sign-invariant under monotonic split transformations.",
        "",
        "## Summary",
        "",
        f"- candidate recorder: `{summary.get('recorder_id', '')}`",
        f"- baseline recorder: `{BASELINE_RECORDER}`",
        f"- test RankIC delta: `{fmt(summary.get('rank_ic_delta'))}`",
        f"- with-cost annualized excess delta: `{fmt(summary.get('with_cost_ann_delta'))}`",
        f"- with-cost IR delta: `{fmt(summary.get('with_cost_ir_delta'))}`",
        "",
        "## Pre-Ablation Diagnostics",
        "",
        "### Magnitude",
        "",
    ]
    lines += table(magnitude, ["segment", "p50", "p95", "p99", "p99_p50_ratio"])
    lines += ["", "### Daily Max", ""] + table(daily_max, ["segment", "daily_max_p50", "daily_max_p95", "daily_max_max"])
    lines += ["", "### Rolling Valid Observations", ""] + table(valid_obs, ["share_valid_obs_lt15", "p01", "p05", "p50"])
    lines += ["", "### Close-vs-VWAP Sensitivity", ""] + table(sensitivity, ["segment", "rankic_vwap", "rankic_close", "abs_delta"])
    lines += ["", "## Model RankIC By Segment", ""] + table(ric, ["model", "segment", "n_days", "mean", "ir", "positive_rate", "avg_n"])
    lines += ["", "## Portfolio Risk By Test Segment", ""] + table(risk, ["model", "segment", "n_days", "annualized_excess", "ir", "max_drawdown"])
    lines += ["", "## Paired Daily Excess Test", ""] + table(paired, ["n_days", "daily_excess_mean_diff", "paired_t_p_value", "same_direction_positive"])
    lines += ["", "## Turnover", ""] + table(turnover, ["model", "daily_turnover_mean", "annualized_turnover", "turnover_n_days"])
    lines += ["", "## Artifacts", ""]
    for f in sorted(out.iterdir()):
        if f.is_file():
            lines.append(f"- `{f.relative_to(ROOT)}`")
    Path("docs/tw_audit/18b_tw_amihud20_ablation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fixed Alpha158 + TW_AMIHUD20 ablation.")
    parser.add_argument("--output-dir", default="data_tw/experiments/yahoo_primary_tw_amihud20_ablation")
    args = parser.parse_args()
    out = ROOT / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CONFIG, out / "amihud20_config_snapshot.yaml")

    proc = subprocess.run(["python", "qlib/cli/run.py", str(CONFIG)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    log_path = out / "amihud20.log"
    log_path.write_text(proc.stdout, encoding="utf-8")
    row = {"name": "alpha158_amihud20", "returncode": proc.returncode, "baseline_recorder_id": BASELINE_RECORDER, "config_path": str(CONFIG.relative_to(ROOT)), "log_path": str(log_path.relative_to(ROOT))}
    row.update(parse_stdout(proc.stdout))
    if row.get("recorder_id"):
        (out / "amihud20_recorder_id.txt").write_text(str(row["recorder_id"]) + "\n", encoding="utf-8")
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
    alpha158 = Alpha158(instruments=MARKET, start_time=START, end_time=END, fit_start_time=START, fit_end_time=FIT_END).fetch(col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_R)["feature"]
    magnitude, daily_max, valid_obs, sensitivity = pre_ablation_diagnostics(alpha158)
    magnitude.to_csv(out / "amihud20_magnitude_summary.csv", index=False)
    daily_max.to_csv(out / "amihud20_daily_max_summary.csv", index=False)
    valid_obs.to_csv(out / "amihud20_valid_obs_summary.csv", index=False)
    sensitivity.to_csv(out / "amihud20_close_vwap_sensitivity.csv", index=False)

    base_daily_ic, base_ic_summary = load_model_segment_ic(BASELINE_CONFIG, BASELINE_RECORDER, "baseline_alpha158")
    cand_daily_ic, cand_ic_summary = load_model_segment_ic(CONFIG, str(row["recorder_id"]), "alpha158_amihud20")
    model_ic = pd.concat([base_ic_summary, cand_ic_summary], ignore_index=True)
    model_ic.to_csv(out / "model_segment_ic.csv", index=False)
    pd.concat([base_daily_ic.assign(model="baseline_alpha158"), cand_daily_ic.assign(model="alpha158_amihud20")], ignore_index=True).to_csv(out / "model_daily_ic.csv", index=False)

    base_report = load_report(BASELINE_RECORDER).rename(columns={"return": "baseline_return", "bench": "baseline_bench", "excess": "baseline_excess"})
    cand_report = load_report(str(row["recorder_id"])).rename(columns={"return": "candidate_return", "bench": "candidate_bench", "excess": "candidate_excess"})
    paired = base_report[["date", "baseline_return", "baseline_bench", "baseline_excess"]].merge(cand_report[["date", "candidate_return", "candidate_bench", "candidate_excess"]], on="date", how="inner")
    paired["candidate_minus_baseline_excess"] = paired["candidate_excess"] - paired["baseline_excess"]
    paired.to_csv(out / "paired_daily_excess.csv", index=False)
    paired_summary = pd.DataFrame([{ "baseline_recorder_id": BASELINE_RECORDER, "candidate_recorder_id": row["recorder_id"], **paired_ttest(paired["baseline_excess"], paired["candidate_excess"]) }])
    paired_summary.to_csv(out / "paired_ttest_summary.csv", index=False)

    risk = pd.concat([risk_by_period(load_report(BASELINE_RECORDER), "baseline_alpha158"), risk_by_period(load_report(str(row["recorder_id"])), "alpha158_amihud20")], ignore_index=True)
    risk.to_csv(out / "portfolio_risk_by_segment.csv", index=False)
    turnover = pd.DataFrame([turnover_summary(load_report(BASELINE_RECORDER), load_indicators(BASELINE_RECORDER), "baseline_alpha158"), turnover_summary(load_report(str(row["recorder_id"])), load_indicators(str(row["recorder_id"])), "alpha158_amihud20")])
    turnover.to_csv(out / "turnover_summary.csv", index=False)

    write_report(out, row, model_ic, risk, paired_summary, turnover, magnitude, daily_max, valid_obs, sensitivity)
    print(f"returncode={proc.returncode}")
    print(f"recorder_id={row.get('recorder_id', '')}")
    print(f"rank_ic_delta={row.get('rank_ic_delta')}")
    print(f"with_cost_ann_delta={row.get('with_cost_ann_delta')}")
    print(f"wrote {out.relative_to(ROOT)}")
    print("wrote docs/tw_audit/18b_tw_amihud20_ablation_report.md")


if __name__ == "__main__":
    main()
