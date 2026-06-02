# Guide For The Qlib-Side Codex Agent

You are reading this folder because the Qlib project needs more market data or new factor inputs. Use this package as a crawler toolkit, not as final model code.

## Decision Flow

1. Identify the target dataset:
   - Daily OHLCV
   - Corporate actions
   - Fundamental factors
   - Chips/flow data
   - Index or industry constituents
   - Macro or alternative data
2. Check whether the target source returns adjusted or raw data.
3. Write raw crawl output first if the source schema is unfamiliar.
4. Convert raw data into Qlib-ready CSV after field semantics are known.
5. Validate normalized output.
6. Dump to Qlib bin.
7. Run a Qlib API spot check before training.

## Never Skip These Checks

- Symbol format is stable, e.g. `TW2330`.
- Date format is `YYYY-MM-DD`.
- Data is sorted by date.
- No duplicate `(symbol, date)` rows.
- Numeric columns are parseable.
- Adjustment policy is documented.
- The crawl report records missing symbols and source errors.

## Recommended Directory Layout

```text
data_tw/experiments/<experiment_name>/
  raw/
  normalized/
  qlib_bin/
  reports/
```

Keep all experiments isolated until validation is complete. Do not overwrite production Qlib data directly.

## When Crawling New Factors

For cross-sectional daily factors, prefer this normalized layout:

```csv
symbol,date,<factor_1>,<factor_2>,...
TW2330,2024-01-02,1.23,4.56
```

For point-in-time fundamental data, preserve announcement dates and report periods:

```csv
symbol,ann_date,report_period,<field_1>,<field_2>,...
TW2330,2024-03-15,2023Q4,1.23,4.56
```

Do not assume financial statement data is known on the report period end date. Use announcement dates for model features.

## Using Scrapling

Use Scrapling when a source has browser-like blocking, dynamic pages, or needs modern TLS/client impersonation. Basic pattern:

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get(
    url,
    params=params,
    proxy="http://127.0.0.1:7890",
    timeout=30,
    retries=1,
    impersonate="chrome",
)
payload = page.json()
```

For tokenized APIs, avoid printing full URLs because query strings may contain credentials.

## Adjustment Policy

Current Taiwan daily CSVs are forward-adjusted if possible:

```text
factor(date) = product(after_price / before_price for corporate actions after date)
adjusted_ohlc = raw_ohlc * factor(date)
adjusted_vwap = raw_vwap * factor(date)
volume unchanged
```

If a new source provides its own adjusted close, document the exact derivation. Do not silently mix provider factors in a strict research benchmark.

## Handoff Output

Every crawl should produce:

- Normalized CSV files.
- A JSON report with requested/success/failed counts.
- A validation report.
- Notes on adjustment and source limitations.
