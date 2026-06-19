# Phase Q3 执行报告：Orthogonal Fresh Qlib 同口径回放对比

生成时间：`2026-06-15T16:53:49+00:00`

## 1. 结论

- gate：`phase_q3_orthogonal_fresh_qlib_replay_completed`。
- 只比较 `fresh_qlib_top50_adaptive_baseline` 与 `orthogonal_fresh_qlib_top50_adaptive`。
- 使用同一个 S2D replay engine、同一 next-day execution、同一 fee/tax、同一 candidate_k=50、同一 target_position_count=10。
- 未训练、未调参、未改 replay/default strategy、未引入 LTR，未触发 frontend/API/provider/accepted latest/monitor/交易链路。
- untouched test treatment vs control：net return diff `-0.18105`，drawdown diff `0.026258`，action diff `0`。

## 2. 使用 Artifact

- control replay-ready：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_replay_ready_scores.csv`
- control replay metrics：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_replay_metrics_by_strategy.csv`
- treatment post-filter score：`data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_post_filter_score_rank.csv`
- treatment raw score：`data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_raw_score_rank.csv`
- treatment feature importance：`data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_feature_importance.csv`
- Q2 manifest：`data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_training_manifest.json`
- Q3 replay-ready：`data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_replay_ready_scores.csv`

## 3. 必须证明的等式

- `replay_engine_control == replay_engine_treatment`：`True`
- `execution_rule_control == execution_rule_treatment`：`True`
- `fee_tax_control == fee_tax_treatment`：`True`
- `candidate_k_control == candidate_k_treatment == 50`：`True`
- `target_position_count_control == target_position_count_treatment == 10`：`True`
- `next_day_accounting_control == next_day_accounting_treatment`：`True`
- `coverage_method_control == coverage_method_treatment`：`True`
- 对比结果只来自 score/rank 差异，不来自回放口径差异。

## 4. Control 复现

- S2D control 指标复现：`True`
- validation control net return：`0.03827`；test control net return：`0.662457`

## 5. Validation / Untouched Test

| split | segment | method | net_return | max_drawdown | action_count | turnover_proxy | fee_and_tax | relative_return | relative_drawdown |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| validation | validation_full | fresh_qlib_top50_adaptive_baseline | 0.03827 | -0.151349 | 226 | 22.391193 | 64493.47 | 0.0 | 0.0 |
| validation | validation_full | orthogonal_fresh_qlib_top50_adaptive | -0.013483 | -0.191091 | 225 | 22.308566 | 62829.75 | -0.051753 | -0.039742 |
| test | test_full | fresh_qlib_top50_adaptive_baseline | 0.662457 | -0.088396 | 410 | 40.692897 | 155259.42 | 0.0 | 0.0 |
| test | test_full | orthogonal_fresh_qlib_top50_adaptive | 0.481407 | -0.062138 | 410 | 40.318395 | 140863.67 | -0.18105 | 0.026258 |

## 6. 2025H2

| split | segment | method | net_return | max_drawdown | action_count | turnover_proxy | fee_and_tax | relative_return | relative_drawdown |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| test | 2025H2 | fresh_qlib_top50_adaptive_baseline | 0.336427 | -0.088396 | 249 | 24.606355 | 83226.06 | 0.0 | 0.0 |
| test | 2025H2 | orthogonal_fresh_qlib_top50_adaptive | 0.212513 | -0.062138 | 249 | 24.405383 | 77729.58 | -0.123914 | 0.026258 |

## 7. 2026YTD

| split | segment | method | net_return | max_drawdown | action_count | turnover_proxy | fee_and_tax | relative_return | relative_drawdown |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| test | 2026YTD_to_2026-05-07 | fresh_qlib_top50_adaptive_baseline | 0.219267 | -0.0559 | 154 | 15.177044 | 49438.38 | 0.0 | 0.0 |
| test | 2026YTD_to_2026-05-07 | orthogonal_fresh_qlib_top50_adaptive | 0.203827 | -0.048459 | 154 | 15.144099 | 48330.59 | -0.01544 | 0.007441 |

## 8. Rolling 6m

| split | segment | method | net_return | max_drawdown | action_count | turnover_proxy | fee_and_tax | relative_return | relative_drawdown |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| test | rolling_6m_2025-07-01_2025-12-31 | fresh_qlib_top50_adaptive_baseline | 0.336427 | -0.088396 | 249 | 24.606355 | 83226.06 | 0.0 | 0.0 |
| test | rolling_6m_2025-07-01_2025-12-31 | orthogonal_fresh_qlib_top50_adaptive | 0.212513 | -0.062138 | 249 | 24.405383 | 77729.58 | -0.123914 | 0.026258 |
| test | rolling_6m_2025-07-30_2026-01-30 | fresh_qlib_top50_adaptive_baseline | 0.427274 | -0.088382 | 247 | 24.909109 | 89486.97 | 0.0 | 0.0 |
| test | rolling_6m_2025-07-30_2026-01-30 | orthogonal_fresh_qlib_top50_adaptive | 0.269559 | -0.062312 | 248 | 24.777823 | 81148.67 | -0.157715 | 0.02607 |
| test | rolling_6m_2025-08-29_2026-03-12 | fresh_qlib_top50_adaptive_baseline | 0.348411 | -0.088912 | 248 | 24.843847 | 83265.36 | 0.0 | 0.0 |
| test | rolling_6m_2025-08-29_2026-03-12 | orthogonal_fresh_qlib_top50_adaptive | 0.20707 | -0.062113 | 247 | 24.512999 | 76251.08 | -0.141341 | 0.026799 |
| test | rolling_6m_2025-09-30_2026-04-14 | fresh_qlib_top50_adaptive_baseline | 0.343559 | -0.087767 | 247 | 24.519349 | 82856.8 | 0.0 | 0.0 |
| test | rolling_6m_2025-09-30_2026-04-14 | orthogonal_fresh_qlib_top50_adaptive | 0.297277 | -0.049833 | 248 | 24.551724 | 80794.06 | -0.046282 | 0.037934 |

## 9. Market Regime

- regime rows：`12`，详见 `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_market_regime_summary.csv`。

## 10. Coverage

- validation control/treatment score rows：`10068 / 10068`
- test control/treatment score rows：`22613 / 22613`
- validation daily rows min/median/max control：`84 / 87.0 / 89`；treatment：`84 / 87.0 / 89`
- test daily rows min/median/max control：`88 / 109.0 / 150`；treatment：`88 / 109.0 / 150`

## 11. PnL Contribution / 集中度

- PnL contribution 使用 replay actions 的 symbol turnover/fee proxy 输出，详见 `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_pnl_contribution.csv`。
- 单一股票/日期集中度审计：`{'pnl_contribution_rows': 120, 'max_symbol_turnover_share': 0.091935, 'single_symbol_turnover_share_gt_50pct': False, 'note': 'PnL contribution is an action-level turnover/fee proxy from the frozen replay actions; no extra return rule was introduced.'}`

## 12. Feature Importance Summary

| feature_group | feature_count | importance_gain_sum | importance_gain_share | importance_split_sum | top_features |
| --- | ---: | ---: | ---: | ---: | --- |
| alpha158_control_features | 158 | 7706.940314 | 0.920584 | 1352 | STD30, STD60, STD20, QTLU60, CORD30, QTLU5, SUMD60, RESI10, STD5, MAX5 |
| orthogonal_institutional_margin_features | 42 | 664.851869 | 0.079416 | 134 | margin_balance, dealer_net_buy, foreign_net_buy_roll3, institutional_total_net_buy, dealer_net_buy_roll3, short_balance, investment_trust_net_buy_roll10, investment_trust_net_buy_roll3, short_balance_change_roll3, short_balance_change_roll10 |

## 13. 风险披露与停止条件

- 本报告同时输出收益、max drawdown、action_count、turnover_proxy、fee_and_tax，不存在只报告收益不报告风险。
- 未触发停止条件：回放引擎一致、control 可复现、coverage 可解释、next-day accounting 无违规，且不需要改 replay 规则。
- 建议进入 Q4：`是`，前提是审查者确认本 Q3 只读同口径回放对比通过。

## 14. 输出 Artifact

- `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_replay_manifest.json`
- `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_control_vs_treatment_summary.csv`
- `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_validation_summary.csv`
- `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_test_summary.csv`
- `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_2025h2_summary.csv`
- `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_2026ytd_summary.csv`
- `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_rolling6m_summary.csv`
- `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_market_regime_summary.csv`
- `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_pnl_contribution.csv`
- `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_feature_importance_summary.csv`
- `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_forbidden_action_audit.json`
- `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/phase_q3_replay_log.txt`
