# Source Playbook

Use this guide when adding a new crawler or factor source.

## Source Selection

Prefer sources in this order:

1. Official exchange or regulator source.
2. Stable API provider with documented schema.
3. Browser/API hybrid endpoint that Scrapling can access.
4. HTML table scraping only when the table structure is stable.

For paid or tokenized APIs, read credentials from environment variables.

## Taiwan Daily Prices

Known working paths:

- Yahoo Finance chart API works for many current and historical Taiwan symbols and gives `adjclose`.
- FinMind `TaiwanStockPrice` works for supplementing many Yahoo-missing symbols.
- FinMind `TaiwanStockDividendResult` can be used to compute forward-adjustment factors.

Known limitations:

- Yahoo returns no usable chart rows for some delisted/old symbols even when HTTP status is 200.
- FinMind may return HTTP 200 and status 200 with an empty `data` list for unsupported symbols.
- Provider adjustment factors are not guaranteed to match.

## New Factor Datasets

For new factors, first probe the source with a small date window and a small symbol list. Save:

- Source endpoint and parameters.
- Raw sample rows.
- Field semantics and units.
- Whether data is point-in-time.
- Missing-data behavior.

Only after this should you write normalized output for Qlib.

## Reports

Every source script should write a report like:

```json
{
  "source": "source name",
  "start": "YYYY-MM-DD",
  "end": "YYYY-MM-DD",
  "symbols_requested": 0,
  "symbols_success": 0,
  "symbols_empty": [],
  "symbols_failed": {},
  "rows_written": 0,
  "adjustment": "forward_adjusted | raw_unadjusted | not_applicable",
  "notes": ""
}
```

For factor data, replace `adjustment` with a field such as `point_in_time_policy`.
