# Phase 2 Entry Model v1 Report

## Summary

- Scope: Entry Model v1 only; binary and regression LightGBM baselines plus equal-weight normalized ensemble.
- No Exit Risk Model, no portfolio replay, no frontend integration, no real trading action.
- 2024 is unavailable in Phase 1B artifacts and is not used.

## Main Test/Forward Comparison

| split_part | model | RankIC | NDCG@10 | precision@5 | top5_excess_return | top10_excess_return |
|---|---|---|---|---|---|---|
| test | ensemble | 0.027954 | 0.428305 | 0.425620 | 0.015054 | 0.014437 |
| test | baseline_qlib_percentile | 0.023365 | 0.453923 | 0.496694 | 0.044263 | 0.041242 |
| test | baseline_qlib_rank | 0.023378 | 0.453923 | 0.496694 | 0.044263 | 0.041242 |
| forward | ensemble | -0.003287 | 0.424583 | 0.443478 | 0.040906 | 0.055189 |
| forward | baseline_qlib_percentile | 0.080698 | 0.468027 | 0.565217 | 0.078387 | 0.086197 |
| forward | baseline_qlib_rank | 0.080696 | 0.468027 | 0.565217 | 0.078387 | 0.086197 |

## Top Feature Importance

| split_name | model | feature | importance_gain | importance_split |
|---|---|---|---|---|
| sensitivity | regression | ma60_slope | 114290.056946 | 34 |
| main | regression | volatility20 | 68922.824219 | 93 |
| sensitivity | regression | volatility20 | 62713.653534 | 36 |
| sensitivity | regression | twii_close_vs_ma120 | 60452.423096 | 26 |
| sensitivity | regression | market_volatility20 | 60267.203583 | 28 |
| main | regression | liquidity_percentile_by_date | 50723.141800 | 75 |
| main | regression | ma60_slope | 36486.391052 | 89 |
| main | regression | market_breadth_ma20 | 29880.792175 | 40 |
| sensitivity | regression | liquidity_percentile_by_date | 29265.825043 | 29 |
| main | regression | market_drawdown60 | 26950.519012 | 55 |
| sensitivity | regression | twii_ret60 | 26092.791931 | 32 |
| sensitivity | regression | macd_hist | 25518.239258 | 24 |
| sensitivity | regression | market_breadth_ma20 | 23010.700958 | 21 |
| sensitivity | regression | avg_trading_value_20d | 22762.919861 | 28 |
| main | regression | slippage_proxy | 22035.022919 | 34 |

## Forbidden Feature Check

- forbidden_or_future_inputs: `[]`

## Phase 3 Gate

Phase 2 gate result: the main split ensemble underperforms qlib rank/percentile on test and forward TopK excess return. Sensitivity forward improves, but sensitivity test still underperforms qlib. Executor recommendation: do not enter Phase 3 directly; submit as a failed/insufficient Entry Model v1 experiment for reviewer decision.
