# Command Examples

Run these from the project root after copying this folder into Qlib.

## Yahoo Taiwan Daily Crawl

```bash
python qlib_scrapling_handoff/scripts/crawl_yahoo_scrapling.py \
  --symbols-file qlib_scrapling_handoff/examples/symbols_sample.txt \
  --output-dir data_tw/experiments/yahoo_sample/normalized \
  --report-file data_tw/experiments/yahoo_sample/reports/crawl_report_yahoo.json \
  --proxy http://127.0.0.1:7890 \
  --continue-on-error
```

## FinMind Raw Supplement

```bash
python qlib_scrapling_handoff/scripts/crawl_finmind_supplement.py \
  --symbols-file qlib_scrapling_handoff/examples/symbols_sample.txt \
  --output-dir data_tw/experiments/finmind_sample/raw_normalized \
  --report-file data_tw/experiments/finmind_sample/reports/crawl_report_finmind.json \
  --proxy http://127.0.0.1:7890 \
  --continue-on-error
```

## FinMind Forward Adjustment

```bash
export FINMIND_TOKEN=...

python qlib_scrapling_handoff/scripts/adjust_finmind_supplement.py \
  --symbols-file qlib_scrapling_handoff/examples/symbols_sample.txt \
  --output-dir data_tw/experiments/finmind_sample/normalized \
  --report-file data_tw/experiments/finmind_sample/reports/adjust_report_finmind.json \
  --proxy http://127.0.0.1:7890 \
  --continue-on-error
```

## Validate Normalized Daily CSV

```bash
python qlib_scrapling_handoff/scripts/validate_output.py \
  --data-dir data_tw/experiments/finmind_sample/normalized \
  --symbols-file qlib_scrapling_handoff/examples/symbols_sample.txt \
  --report data_tw/experiments/finmind_sample/reports/validation_report.json
```

## Dump To Qlib Bin

```bash
python scripts/dump_bin.py dump_all \
  --data_path data_tw/experiments/finmind_sample/normalized \
  --qlib_dir data_tw/experiments/finmind_sample/qlib_bin \
  --freq day \
  --date_field_name date \
  --symbol_field_name symbol \
  --exclude_fields date,symbol \
  --file_suffix .csv
```

## Qlib API Spot Check

```bash
python -c 'import qlib; from pathlib import Path; from qlib.data import D; qdir=Path("data_tw/experiments/finmind_sample/qlib_bin").resolve(); qlib.init(provider_uri=str(qdir), mount_path=str(qdir), auto_mount=False, redis_port=-1); print(D.features(["TW2330"], ["$close", "$volume", "$factor"], freq="day").tail())'
```
