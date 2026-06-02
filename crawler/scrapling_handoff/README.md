# Qlib Scrapling Handoff

This folder is a portable handoff package for a Qlib-side agent. Copy it into a Qlib project when that project needs to crawl market data or new factor inputs with Scrapling.

## What To Read First

1. `CODEX_GUIDE.md` - operational guide for the Qlib-side Codex agent.
2. `docs/DATA_CONTRACT.md` - required output format for Qlib normalized daily data.
3. `docs/SOURCE_PLAYBOOK.md` - how to choose and add a data source.
4. `examples/COMMANDS.md` - tested command patterns.

## Included Scripts

- `scripts/crawl_yahoo_scrapling.py` - Yahoo Finance chart API crawler for Taiwan daily adjusted OHLCV.
- `scripts/crawl_finmind_supplement.py` - FinMind raw daily price supplement crawler.
- `scripts/adjust_finmind_supplement.py` - FinMind forward-adjustment pass using `TaiwanStockDividendResult`.
- `scripts/validate_output.py` - validates normalized CSV output.
- `scripts/finmind_dataset_probe.py` - small generic FinMind dataset probe for discovering factor datasets.

The scripts are intentionally plain Python CLI tools. They are easy to copy, modify, and run from either this repo or a Qlib repo.

## Environment

Install the crawler dependency in the Python environment used by Qlib:

```bash
pip install scrapling pandas
```

If the machine uses a local proxy, pass it explicitly:

```bash
--proxy http://127.0.0.1:7890
```

For FinMind, never hard-code credentials in files. Export a token in the shell:

```bash
export FINMIND_TOKEN=...
```

`adjust_finmind_supplement.py` reads `FINMIND_TOKEN` or `FINMIND_API_TOKEN`.

## Current Taiwan Daily Status

The latest experiment completed in this workspace produced:

- Target stock universe: 2135 symbols.
- Yahoo adjusted source: 1986 symbols.
- FinMind supplement source: 85 symbols.
- Remaining missing: 64 symbols.
- Combined available: 2071 symbols.
- Qlib bin path in the source machine: `/home/chuliyang/qlib/data_tw/experiments/yahoo_finmind_adjusted/qlib_bin`.

Important: Yahoo and FinMind use different adjustment factors. The combined dataset is useful for coverage and exploratory experiments. For strict factor research, prefer Yahoo-only or rebuild all symbols with one raw price source plus one corporate-action source.

## How To Use In A Qlib Project

Copy this folder into the Qlib project, then run commands from the Qlib project root. Keep generated data under an experiment directory, for example:

```text
data_tw/experiments/my_factor_data/
  normalized/
  qlib_bin/
  reports/
```

Use `scripts/validate_output.py` before dumping to Qlib bin. The validator enforces the CSV schema expected by Qlib.

## Extension Rule For New Factors

For every new factor dataset, keep two layers separate:

1. Raw crawl output: preserve source fields and source units.
2. Qlib-ready normalized output: stable columns, stable symbol format, stable date format.

Do not mix source-specific parsing logic into Qlib model code. Normalize before training.
