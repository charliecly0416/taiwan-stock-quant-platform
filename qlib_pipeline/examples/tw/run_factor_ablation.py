from __future__ import annotations

import argparse
import csv
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


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
    without_cost = parse_risk_section(text, "excess return without cost")
    with_cost = parse_risk_section(text, "excess return with cost")
    result.update({f"without_cost_{k}": v for k, v in without_cost.items()})
    result.update({f"with_cost_{k}": v for k, v in with_cost.items()})
    return result


def normalize_config(template: Path, output_path: Path, topk: int, n_drop: int) -> None:
    cfg = yaml.safe_load(template.read_text(encoding="utf-8"))
    cfg["port_analysis_config"]["strategy"]["kwargs"]["topk"] = topk
    cfg["port_analysis_config"]["strategy"]["kwargs"]["n_drop"] = n_drop
    output_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")


def run_one(name: str, template: Path, output_dir: Path, topk: int, n_drop: int) -> dict:
    config_path = output_dir / f"{name}.yaml"
    log_path = output_dir / f"{name}.log"
    normalize_config(template, config_path, topk, n_drop)
    print(f"run {name}: {template}")
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
        "name": name,
        "topk": topk,
        "n_drop": n_drop,
        "returncode": proc.returncode,
        "config_path": str(config_path),
        "log_path": str(log_path),
    }
    row.update(parse_stdout(proc.stdout))
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TW factor ablation configs with matched portfolio settings.")
    parser.add_argument("--output-dir", default="data_tw/experiments/ablation_after_adjustment")
    parser.add_argument("--topk", type=int, default=30)
    parser.add_argument("--n-drop", type=int, default=1)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    templates = {
        "alpha158": ROOT / "configs/tw_lightgbm_alpha158.yaml",
        "retvol": ROOT / "configs/tw_lightgbm_alpha158_retvol.yaml",
        "retvol_ma20gap": ROOT / "configs/tw_lightgbm_alpha158_retvol_ma20gap.yaml",
        "custom_legacy": ROOT / "configs/tw_lightgbm_alpha158_custom.yaml",
    }
    rows = [run_one(name, template, output_dir, args.topk, args.n_drop) for name, template in templates.items()]
    out_csv = output_dir / "summary.csv"
    fields = sorted({key for row in rows for key in row})
    preferred = [
        "name", "topk", "n_drop", "returncode", "recorder_id",
        "ic", "icir", "rank_ic", "rank_icir",
        "with_cost_annualized_return", "with_cost_information_ratio", "with_cost_max_drawdown",
        "without_cost_annualized_return", "without_cost_information_ratio", "without_cost_max_drawdown",
        "config_path", "log_path",
    ]
    fields = preferred + [f for f in fields if f not in preferred]
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out_csv}")


if __name__ == "__main__":
    main()
