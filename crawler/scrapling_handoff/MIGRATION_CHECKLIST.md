# Migration Checklist

Use this checklist after copying `qlib_scrapling_handoff/` into a Qlib project.

## Setup

- Install `scrapling` and `pandas` in the active Python environment.
- Confirm local proxy if needed: `http://127.0.0.1:7890`.
- Export API tokens in the shell, not in files.
- Create an experiment directory under `data_tw/experiments/`.

## First Smoke Test

Run:

```bash
python qlib_scrapling_handoff/scripts/finmind_dataset_probe.py \
  --dataset TaiwanStockPrice \
  --data-id 2330 \
  --start 2024-01-01 \
  --end 2024-01-31 \
  --output data_tw/experiments/probe/reports/finmind_2330_price_probe.json
```

Then inspect the report and confirm that row counts and fields match expectations.

## New Factor Development

- Probe the raw source first.
- Write a focused crawler for the selected dataset.
- Normalize dates and symbols.
- Record units and point-in-time policy.
- Validate output.
- Build a small Qlib dataset.
- Run an API spot check.
- Only then use it in model training.

## Do Not Do This

- Do not commit tokens.
- Do not silently overwrite production Qlib data.
- Do not mix adjustment policies without naming the dataset as mixed.
- Do not use report-period dates as availability dates for fundamentals.
- Do not assume HTTP 200 means the source has data; inspect row counts.
