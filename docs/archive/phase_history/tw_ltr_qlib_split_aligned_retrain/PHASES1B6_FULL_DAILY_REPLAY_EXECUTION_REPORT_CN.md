# Phase S1B6 执行报告：Full Daily Replay

生成日期：2026-06-14T17:53:32+00:00

## 1. 本轮目标

只用 S1B5R replay-ready scores 的 `split == test` 区间 `2023-01-03..2025-06-30`，对 6 个冻结策略做完整日频组合回放。

## 2. 口径

- 初始权益：`1,000,000`。
- 手续费：`0.001425`。
- 卖出税：`0.003`。
- 目标持仓数：`10`。
- 执行价：本地既有 normalized price 中 asof 后下一交易日 close。
- 最终比较只使用 `split == test`。

## 3. Full Test 指标

| method | fee_tax_adjusted_net_return | max_drawdown | action_count | buy_count | sell_count | fee_and_tax | turnover_proxy | relative_return_vs_top50_adaptive |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| qlib_top50_adaptive_baseline | -0.617965 | -0.764102 | 6547 | 3278 | 3269 | 1461057.11 | 634.551141 | 0.0 |
| rank_rotate_top50 | -0.568527 | -0.7531 | 6636 | 3323 | 3313 | 1581526.22 | 643.256456 | 0.049438 |
| rank_rotate_top30 | -0.568527 | -0.7531 | 6636 | 3323 | 3313 | 1581526.22 | 643.256456 | 0.049438 |
| confirmed_exit | -0.564747 | -0.750359 | 6636 | 3323 | 3313 | 1582388.65 | 643.528043 | 0.053218 |
| split_aligned_ltr_simple | -0.340259 | -0.603393 | 3938 | 1974 | 1964 | 1065270.35 | 388.935665 | 0.277706 |
| split_aligned_ltr_turnover_controlled | 0.463012 | -0.55955 | 180 | 95 | 85 | 80224.57 | 17.809916 | 1.080977 |

## 4. Split / Lookahead 说明

- `train_scored: 2017-01-10..2020-12-31` 只作训练期来源说明，不作为样本外结论。
- `validation: 2021-01-04..2022-12-30` 只作旧窗口验证来源说明，不作为最终 test 结论。
- `test: 2023-01-03..2025-06-30` 是本轮唯一用于样本外完整日频回放比较的区间。
- replay-ready table 不含 future label 字段作为策略输入。

## 5. 产物

- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_strategy_metrics_full_test.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_strategy_metrics_yearly.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_strategy_metrics_rolling_6m.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_strategy_metrics_rolling_12m.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_strategy_metrics_by_regime.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_daily_nav_by_strategy.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_action_audit_by_strategy.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_split_purity_and_lookahead_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_forbidden_action_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_gate_summary.json`

## 6. 禁止事项执行结果

- 未训练 LTR / qlib。
- 未调参，未改 feature / label / split / universe。
- 未新增数据源，未联网。
- 未改前端/API，未触发 provider / accepted latest / monitor / trading chain。
- 未输出买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

## 7. 结论

本轮只提交事实性完整日频回放结果，等待审查者决定 S1 结论。

推荐 gate：

```text
s1b6_full_daily_replay_complete_request_reviewer_decision
```
