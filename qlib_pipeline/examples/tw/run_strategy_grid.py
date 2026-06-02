from __future__ import annotations

import argparse
import csv
import re
import subprocess
from copy import deepcopy
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


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


def make_config(template_path: Path, output_path: Path, topk: int, n_drop: int) -> None:
    with template_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    config = deepcopy(config)
    config["port_analysis_config"]["strategy"]["kwargs"]["topk"] = topk
    config["port_analysis_config"]["strategy"]["kwargs"]["n_drop"] = n_drop
    with output_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)


def run_one(name: str, template_path: Path, topk: int, n_drop: int, work_dir: Path) -> dict[str, str | int | float | None]:
    config_path = work_dir / f"{name}_topk{topk}_drop{n_drop}.yaml"
    stdout_path = work_dir / f"{name}_topk{topk}_drop{n_drop}.log"
    make_config(template_path, config_path, topk, n_drop)
    cmd = ["python", "qlib/cli/run.py", str(config_path)]
    print(f"run {name} topk={topk} n_drop={n_drop}")
    proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    row: dict[str, str | int | float | None] = {
        "name": name,
        "topk": topk,
        "n_drop": n_drop,
        "returncode": proc.returncode,
        "config_path": str(config_path),
        "log_path": str(stdout_path),
    }
    row.update(parse_stdout(proc.stdout))
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TW Qlib strategy parameter grid.")
    parser.add_argument("--topk", default="20,30,40")
    parser.add_argument("--n-drop", default="1,2")
    parser.add_argument("--output-dir", default="data_tw/experiments/grid_topk_drop")
    args = parser.parse_args()

    topks = [int(x.strip()) for x in args.topk.split(",") if x.strip()]
    n_drops = [int(x.strip()) for x in args.n_drop.split(",") if x.strip()]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    templates = {
        "alpha158": ROOT / "configs/tw_lightgbm_alpha158.yaml",
        "custom": ROOT / "configs/tw_lightgbm_alpha158_custom.yaml",
    }

    rows = []
    for name, template_path in templates.items():
        for topk in topks:
            for n_drop in n_drops:
                if n_drop > topk:
                    continue
                rows.append(run_one(name, template_path, topk, n_drop, output_dir))

    out_csv = output_dir / "summary.csv"
    fields = sorted({key for row in rows for key in row})
    preferred = [
        "name",
        "topk",
        "n_drop",
        "returncode",
        "recorder_id",
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
