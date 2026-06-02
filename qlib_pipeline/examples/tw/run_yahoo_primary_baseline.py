from __future__ import annotations

import csv
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/tw_yahoo_primary_alpha158.yaml"
OUTPUT_DIR = ROOT / "data_tw/experiments/yahoo_primary_alpha158_baseline"


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


def parse_stdout(text: str) -> dict[str, str | int | float | None]:
    result: dict[str, str | int | float | None] = {}
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


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CONFIG, OUTPUT_DIR / "config_snapshot.yaml")

    proc = subprocess.run(
        ["python", "qlib/cli/run.py", str(CONFIG)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    (OUTPUT_DIR / "run.log").write_text(proc.stdout, encoding="utf-8")

    row: dict[str, str | int | float | None] = {
        "name": "yahoo_primary_alpha158_baseline",
        "returncode": proc.returncode,
        "provider_uri": "data_tw/experiments/yahoo_adjusted_primary/qlib_bin",
        "market": "tw_liquid_dyn",
        "benchmark": "TWII",
        "handler": "Alpha158",
        "topk": 30,
        "n_drop": 1,
        "train": "2015-05-04..2020-12-31",
        "valid": "2021-01-01..2022-12-31",
        "test": "2023-01-01..2025-06-30",
        "config_path": str(CONFIG.relative_to(ROOT)),
        "log_path": str((OUTPUT_DIR / "run.log").relative_to(ROOT)),
    }
    row.update(parse_stdout(proc.stdout))

    if row.get("recorder_id"):
        (OUTPUT_DIR / "recorder_id.txt").write_text(str(row["recorder_id"]) + "\n", encoding="utf-8")

    fields = [
        "name",
        "returncode",
        "recorder_id",
        "provider_uri",
        "market",
        "benchmark",
        "handler",
        "topk",
        "n_drop",
        "ic",
        "icir",
        "rank_ic",
        "rank_icir",
        "with_cost_mean",
        "with_cost_std",
        "with_cost_annualized_return",
        "with_cost_information_ratio",
        "with_cost_max_drawdown",
        "without_cost_mean",
        "without_cost_std",
        "without_cost_annualized_return",
        "without_cost_information_ratio",
        "without_cost_max_drawdown",
        "train",
        "valid",
        "test",
        "config_path",
        "log_path",
    ]
    with (OUTPUT_DIR / "summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)

    print(f"returncode={proc.returncode}")
    print(f"recorder_id={row.get('recorder_id', '')}")
    print(f"wrote {OUTPUT_DIR.relative_to(ROOT)}")
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
