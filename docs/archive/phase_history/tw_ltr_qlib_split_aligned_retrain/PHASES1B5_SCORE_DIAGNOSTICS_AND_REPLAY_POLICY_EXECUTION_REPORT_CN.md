# Phase S1B5 执行报告：Score Diagnostics 与 Replay Policy Freeze

生成日期：2026-06-14T17:34:40+00:00

## 1. 本轮目标

按 `PHASES1B4_REVIEW_AND_PHASES1B5_SCORE_DIAGNOSTICS_WORK_CN.md` 要求，只做 S1B4 common LTR score/rank 的只读质量诊断，并冻结 S1B6 完整日频回放政策。

## 2. 输入

- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_ltr_scores.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_ltr_score_schema.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_metric_by_split.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_qlib_wf_scores.csv`

## 3. Score Coverage By Split

| split | row_count | date_count | daily_count_min | daily_count_max | ltr_score_missing | ltr_rank_missing | duplicate_date_instrument |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| test | 87345 | 597 | 114 | 150 | 0 | 0 | 0 |
| train_scored | 141085 | 969 | 111 | 150 | 0 | 0 | 0 |
| validation | 69812 | 489 | 36 | 150 | 0 | 0 | 0 |

## 4. Rank Overlap 与相关性

| split | mean_spearman_rank_corr | top10_overlap | top30_overlap | top50_overlap |
| --- | ---: | ---: | ---: | ---: |
| test | 0.277884 | 0.203350 | 0.385539 | 0.510352 |
| train_scored | 0.159035 | 0.192260 | 0.352253 | 0.449123 |
| validation | 0.183661 | 0.223108 | 0.385753 | 0.483190 |

## 5. Audit-Only Label Diagnostics

以下指标只用于 score 质量审计，不代表组合收益、回撤、换手或动作次数结论。

| split | ltr_top10_label_mean | ltr_top30_label_mean | ltr_top50_label_mean | qlib_top10_label_mean | qlib_top30_label_mean | qlib_top50_label_mean | s1b4_rank_ic_audit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| test | 2.038358 | 2.070743 | 2.062915 | 2.055946 | 2.054495 | 2.052797 | 0.034576 |
| train_scored | 3.086791 | 2.377881 | 2.153849 | 2.076677 | 2.067079 | 2.065800 | 0.107457 |
| validation | 2.003681 | 1.988753 | 1.984123 | 1.979346 | 1.996046 | 2.008724 | -0.015908 |

## 6. Validation Weak-Signal Caveat

- `validation rank_ic_audit = -0.015908`。
- `validation ndcg@30 = 0.511378`。
- 该信号只能如实带入后续 S1B6 报告，不能反向触发调参、改 feature、改 label、改 split、改 universe 或改 turnover 阈值。

## 7. S1B6 Replay Policy Freeze

| strategy | readiness | note |
| --- | --- | --- |
| qlib_top50_adaptive_baseline | blocked_in_current_s1b5_input_contract | S1B4 score artifact does not include adaptive baseline reconstruction columns such as qlib_score_zscore_by_date, ret20, volatility20, TWII_ret20. |
| rank_rotate_top50 | ready | directly available from qlib_score_raw / qlib_rank ordering in current score artifact |
| rank_rotate_top30 | ready | directly available from qlib_score_raw / qlib_rank ordering in current score artifact |
| confirmed_exit | blocked_in_current_s1b5_input_contract | S1B4 score artifact does not include confirmed-exit reconstruction columns such as market_drawdown60 and volatility20-derived baseline fields. |
| split_aligned_ltr_simple | ready | direct common LTR score usage candidate from S1B4 score artifact |
| split_aligned_ltr_turnover_controlled | ready | existing_frozen_usage_layer_candidate_reused |

- full test：`2023-01-01..2025-06-30`
- yearly：`2023`、`2024`、`2025H1`
- rolling：`6m / 12m`
- regime：复用 `regime_segment` 做只读分段
- metrics：`fee_tax_adjusted_net_return`、`max_drawdown`、`action_count`、`buy_count`、`sell_count`、`fee_and_tax`、`turnover_proxy_by_notional_over_avg_equity`、`relative_return_vs_top50_adaptive`、`relative_drawdown_vs_top50_adaptive`、`relative_actions_vs_top50_adaptive`

## 8. Turnover-Controlled 使用层政策

- status：`existing_frozen_usage_layer_candidate_reused`
- source gate：`data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_gate_summary.json`
- source artifact：`data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_validation_selection.csv`
- reused config：`k30_a3_gap0.0_buf0.0_holdw2_budget0.2`
- 该政策来自既有冻结主线，不是根据 S1B4 validation/test 诊断临时选出的。

## 9. 禁止事项执行结果

- 未训练 LTR。
- 未训练 qlib。
- 未跑组合回放。
- 未比较策略收益。
- 未调参，未改 feature / label / split / universe。
- 未新增数据源，未联网。
- 未改前端/API，未触发 provider / accepted latest / monitor / trading chain。
- 未输出买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

## 10. 结论

本轮完成 S1B5 score diagnostics 与 S1B6 replay policy freeze。

推荐 gate：

```text
s1b5_score_diagnostics_and_replay_policy_pass_request_s1b6_full_daily_replay
```
