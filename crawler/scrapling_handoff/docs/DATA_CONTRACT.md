# Data Contract

This contract defines the normalized daily CSV format consumed by Qlib handoff scripts.

## File Naming

One file per symbol:

```text
TW2330.csv
TW2317.csv
TW1101.csv
```

The file stem must match the `symbol` column.

## Daily OHLCV Columns

Required fixed order:

```csv
symbol,date,open,high,low,close,volume,vwap,factor
```

| Column | Type | Meaning |
| --- | --- | --- |
| symbol | string | Qlib symbol, e.g. `TW2330` |
| date | string | `YYYY-MM-DD` |
| open | float | Daily open, preferably adjusted |
| high | float | Daily high, preferably adjusted |
| low | float | Daily low, preferably adjusted |
| close | float | Daily close, preferably adjusted |
| volume | integer | Shares, not board lots |
| vwap | float | Trading money divided by shares, adjusted if prices are adjusted |
| factor | float | Adjustment factor. Use `1.0` only for unadjusted output and document it |

## Invariants

- UTF-8 CSV with header.
- Dates ascending.
- No duplicate dates per symbol.
- `open/high/low/close/vwap/factor` are positive floats.
- `volume >= 0`.
- `high >= max(open, close)`.
- `low <= min(open, close)`.

## Empty Symbols

If a symbol has no available data, prefer not writing a CSV. Record it in the crawl report instead.

## Adjustment

Formal Taiwan daily target is forward-adjusted OHLCV. If using raw data, the report must say `adjustment=raw_unadjusted`.
