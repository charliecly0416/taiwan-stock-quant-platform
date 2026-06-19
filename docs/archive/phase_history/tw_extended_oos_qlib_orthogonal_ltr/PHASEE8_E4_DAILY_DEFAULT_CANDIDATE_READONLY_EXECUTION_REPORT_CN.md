# Phase E8 执行报告：E4 Daily Default Candidate Readonly

生成时间：`2026-06-16T05:42:37+00:00`

## 1. 结论

- gate：`phase_e8_e4_daily_default_candidate_readonly_completed`。
- signal_asof：`2026-05-07`。
- strategy_id：`e4_frozen_qlib_orthogonal_ltr_2023_2025`。
- 已生成 E4 frozen qlib + E4 orthogonal LTR 的只读 daily candidate artifact。
- 未训练 qlib / LTR，未调参，未改默认策略，未触发 provider / accepted latest / monitor / broker / orders / quick-trade。
- 本阶段只允许进入默认展示切换讨论，不执行展示切换。

## 2. 策略合同

| field | value |
| --- | --- |
| qlib_base | 2018-2022 frozen qlib |
| ltr_model | orthogonal LTR trained on 2023-2025 |
| replay_boundary | qlib top50 rerank only |
| candidate_k | 50 |
| target_position_count | 10 |
| execution_assumption | next-day execution |

## 3. Coverage / Replay-Ready

| metric | value |
| --- | ---: |
| qlib_rows | 150 |
| qlib_top50_rows | 50 |
| ltr_score_rows | 50 |
| target_top10_rows | 10 |
| duplicate_key_count | 0 |
| next_execution_price_available_rows | 50 |

## 4. PIT Available-At Audit

| feature_family | rows | trade_date_max | available_at_max | available_at_violations | trade_date_violations | pit_pass |
| --- | ---: | --- | --- | ---: | ---: | --- |
| institutional_flow | 150 | 2026-05-06 | 2026-05-07 | 0 | 0 | True |
| margin_short | 150 | 2026-05-06 | 2026-05-07 | 0 | 0 | True |

## 5. 展示边界

- 可展示策略名称、signal_asof、top50 rerank、top10 候选、相对上一期变化、coverage/PIT/replay-ready 审计状态和风险提示。
- 不展示自动买卖指令、目标仓位、target weight、broker order、quick-trade、收益承诺、胜率或上涨概率承诺。

## 6. 输出 Artifact

- manifest: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/daily_e4_default_candidate/e4_daily_candidate_manifest_2026-05-07.json`
- qlib_top150: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/daily_e4_default_candidate/e4_daily_qlib_top150_scores_2026-05-07.csv`
- ltr_top50: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/daily_e4_default_candidate/e4_daily_ltr_top50_rerank_2026-05-07.csv`
- target_top10: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/daily_e4_default_candidate/e4_daily_target_top10_2026-05-07.csv`
- diff: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/daily_e4_default_candidate/e4_daily_diff_vs_previous_2026-05-07.csv`
- coverage: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/daily_e4_default_candidate/e4_daily_coverage_audit_2026-05-07.csv`
- pit: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/daily_e4_default_candidate/e4_daily_pit_available_at_audit_2026-05-07.csv`
- forbidden: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/daily_e4_default_candidate/e4_daily_forbidden_action_audit_2026-05-07.json`
