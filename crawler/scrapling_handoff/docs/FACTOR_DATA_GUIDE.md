# Factor Data Guide

This guide describes how to shape non-price data for factor research.

## Daily Cross-Sectional Factors

Use this when the value is known for a symbol on a specific trading day:

```csv
symbol,date,margin_balance,foreign_net_buy
TW2330,2024-01-02,123456,7890
```

Rules:

- `symbol` uses Qlib symbol format.
- `date` is the date the value is available for modeling.
- Keep raw units documented in the report.
- Missing values should be blank or omitted according to the downstream loader policy.

## Fundamentals And PIT Data

For financial statements, keep announcement dates:

```csv
symbol,ann_date,report_period,revenue,eps
TW2330,2024-03-15,2023Q4,1000.0,5.2
```

Rules:

- Do not use `report_period` as the model availability date.
- Join to model calendars with `ann_date <= trade_date`.
- Keep restatement behavior documented.

## Recommended Raw-To-Normalized Workflow

1. Save raw source response or raw CSV under `raw/`.
2. Build a parser that maps source columns to normalized columns.
3. Write a report describing source fields, units, and missing-data behavior.
4. Validate with a small symbol/date slice.
5. Scale the crawl.

## Common Taiwan Factor Ideas

Potential FinMind datasets to probe:

- `TaiwanStockMonthRevenue`
- `TaiwanStockInstitutionalInvestorsBuySell`
- `TaiwanStockMarginPurchaseShortSale`
- `TaiwanStockShareholding`
- `TaiwanStockFinancialStatements`
- `TaiwanStockBalanceSheet`
- `TaiwanStockCashFlowsStatement`

Always verify field names with `scripts/finmind_dataset_probe.py` before writing a parser.
