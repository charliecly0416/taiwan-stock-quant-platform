from __future__ import annotations

import argparse
import csv
import re
import subprocess
from copy import deepcopy
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


WINDOWS = [
    {
        "name": "test_2021",
        "train": ["2015-01-01", "2018-12-31"],
        "valid": ["2019-01-01", "2020-12-31"],
        "test": ["2021-01-01", "2021-12-31"],
    },
    {
        "name": "test_2022",
        "train": ["2015-01-01", "2019-12-31"],
        "valid": ["2020-01-01", "2021-12-31"],
        "test": ["2022-01-01", "2022-12-31"],
    },
    {
        "name": "test_2023",
        "train": ["2015-01-01", "2020-12-31"],
        "valid": ["2021-01-01", "2022-12-31"],
        "test": ["2023-01-01", "2023-12-31"],
    },
    {
        "name": "test_2024",
        "train": ["2015-01-01", "2021-12-31"],
        "valid": ["2022-01-01", "2023-12-31"],
        "test": ["2024-01-01", "2024-12-31"],
    },
    {
        "name": "test_2025_2026",
        "train": ["2016-01-01", "2022-12-31"],
        "valid": ["2023-01-01", "2024-12-31"],
        "test": ["2025-01-01", "2026-05-21"],
    },
]


def parse_metric(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text)
    if not match:
        return None
    return float(match.group(1))


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
    without_cost = parse_risk_section(text, "excess return without cost")
    with_cost = parse_risk_section(text, "excess return with cost")
    result.update({f"without_cost_{k}": v for k, v in without_cost.items()})
    result.update({f"with_cost_{k}": v for k, v in with_cost.items()})
    return result


def apply_window(config: dict, window: dict, topk: int, n_drop: int) -> dict:
    config = deepcopy(config)
    handler_kwargs = config["task"]["dataset"]["kwargs"]["handler"]["kwargs"]
    handler_kwargs["start_time"] = window["train"][0]
    handler_kwargs["end_time"] = window["test"][1]
    handler_kwargs["fit_start_time"] = window["train"][0]
    handler_kwargs["fit_end_time"] = window["train"][1]
    config["task"]["dataset"]["kwargs"]["segments"] = {
        "train": window["train"],
        "valid": window["valid"],
        "test": window["test"],
    }
    config["port_analysis_config"]["backtest"]["start_time"] = window["test"][0]
    config["port_analysis_config"]["backtest"]["end_time"] = window["test"][1]
    config["port_analysis_config"]["strategy"]["kwargs"]["topk"] = topk
    config["port_analysis_config"]["strategy"]["kwargs"]["n_drop"] = n_drop
    return config


def run_window(template_path: Path, window: dict, output_dir: Path, topk: int, n_drop: int) -> dict:
    with template_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    config = apply_window(config, window, topk, n_drop)
    config_path = output_dir / f"{window['name']}.yaml"
    log_path = output_dir / f"{window['name']}.log"
    with config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)
    print(f"run {window['name']} train={window['train']} valid={window['valid']} test={window['test']}")
    proc = subprocess.run(
        ["python", "qlib/cli/run.py", str(config_path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path.write_text(proc.stdout, encoding="utf-8")
    row = {
        "window": window["name"],
        "train": str(window["train"]),
        "valid": str(window["valid"]),
        "test": str(window["test"]),
        "topk": topk,
        "n_drop": n_drop,
        "returncode": proc.returncode,
        "config_path": str(config_path),
        "log_path": str(log_path),
    }
    row.update(parse_stdout(proc.stdout))
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Run rolling-window validation for TW Qlib configs.")
    parser.add_argument("--template", default="configs/tw_lightgbm_alpha158_custom.yaml")
    parser.add_argument("--topk", type=int, default=30)
    parser.add_argument("--n-drop", type=int, default=1)
    parser.add_argument("--output-dir", default="data_tw/experiments/rolling_custom_topk30_drop1")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [run_window(ROOT / args.template, window, output_dir, args.topk, args.n_drop) for window in WINDOWS]

    out_csv = output_dir / "summary.csv"
    fields = sorted({key for row in rows for key in row})
    preferred = [
        "window",
        "returncode",
        "recorder_id",
        "topk",
        "n_drop",
        "ic",
        "icir",
        "rank_ic",
        "rank_icir",
        "with_cost_annualized_return",
        "with_cost_information_ratio",
        "with_cost_max_drawdown",
        "without_cost_annualized_return",
        "without_cost_information_ratio",
        "without_cost_max_drawdown",
        "train",
        "valid",
        "test",
        "config_path",
        "log_path",
    ]
    fields = preferred + [f for f in fields if f not in preferred]
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out_csv}")


if __name__ == "__main__":
    main()
