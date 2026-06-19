# Phase E1R 执行报告：候选覆盖与训练样本口径修复审计

生成时间：`2026-06-15T18:47:22+00:00`

## 1. 结论

- gate：`phase_e1r_candidate_coverage_scope_repaired`。
- 已暂停原 E2 的 top50-only 风险，E1 qlib 训练本身不重跑、不否定。
- E1 的 post-filter 覆盖过少，主因是把 E1 raw score 与全市场 trailing value top150 取交集；这不是旧 O4 宽候选 LTR 训练口径。
- 修订后 E2 必须从同一个 E1 frozen qlib raw OOS score 出发，使用 provider 内 as-of active + same-day price + >=60 history/tradability 的宽候选 rows 构建 LTR train/test；不得只用 top50 训练。

## 2. Coverage 摘要

| scope | date_count | rows_total | daily min/median/max |
| --- | ---: | ---: | --- |
| e1_raw_oos_score | 802 | 119862 | 149/149.0/150 |
| e1_post_filter_full_market_top150_intersection | 802 | 71697 | 71/86.0/150 |
| e1_top50_from_compressed_postfilter | 802 | 40100 | 50/50.0/50 |
| e1r_recommended_provider_eligible_broad_candidate | 802 | 119230 | 147/149.0/150 |

## 3. Filter Attrition 归因

| split | raw_rows | provider_eligible_rows | post_filter_rows | top50_rows | raw_not_full_market_top150 |
| --- | ---: | ---: | ---: | ---: | ---: |
| ltr_test_2026 | 11850 | 11822 | 9792 | 3950 | 1660 |
| ltr_train_2023_2025 | 108012 | 107408 | 61905 | 36150 | 44953 |

解释：`raw_not_full_market_top150` 是 E1 raw score 中 provider 内可交易/有历史的候选，被旧 E1 post-filter 的全市场 trailing value top150 交集排除的行。该过滤压缩了 2023-2025 候选覆盖，不能作为 LTR 训练候选口径。

## 4. 与旧 O4 训练口径对比

| scope | date_count | rows_total | daily rows min/median/max | top50-only training | median max rank |
| --- | ---: | ---: | --- | --- | ---: |
| old_o4_independent_test_sample_complete | 209 | 31071 | 147/149.0/150 | False | 150.0 |
| old_o4_train_sample_complete | 625 | 90301 | 110/146.0/149 | False | 149.0 |
| old_o4_validation_sample_complete | 209 | 30877 | 140/149.0/149 | False | 150.0 |
| e1r_recommended_ltr_test_2026_broad_candidate | 79 | 11822 | 149/150.0/150 | False | 150.0 |
| e1r_recommended_ltr_train_2023_2025_broad_candidate | 723 | 107408 | 147/149.0/149 | False | 149.0 |

旧 O4 的训练不是 top50-only：`top10_flag/top30_flag/top50_flag` 是特征/边界信息，训练行覆盖到宽候选 ranks。E2 应复刻这个训练口径。

## 5. 修订后的 E2 Candidate Scope

- candidate source：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv`
- LTR train：`2023-01-01..2025-12-31`，只使用 2023-2025 label。
- untouched test：`2026-01-01..2026-05-07`，2026 label 仅审计/评估，不参与训练、调参或选择。
- training rows：宽候选 rows，不得 top50-only。
- replay/rerank boundary：后续回放只允许在 qlib top50 内重排。
- qlib_rank/top10/top30/top50 flag 可作为特征，但不能作为训练行过滤条件。

## 6. 禁止事项审计

- 未训练 qlib / LTR。
- 未调参，未回放。
- 未使用 2026 label、future_return、future_excess_return 或 replay PnL 做候选选择。
- 未引入多 qlib 模型、新 filter、market gate 或 turnover rule。
- 未触发 provider refresh / publish / accepted latest、frontend/API、monitor 或交易链路。

## 7. 输出 Artifact

- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1r_candidate_coverage_scope_repair/phasee1r_scope_manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1r_candidate_coverage_scope_repair/phasee1r_raw_postfilter_top50_coverage_by_date.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1r_candidate_coverage_scope_repair/phasee1r_filter_attrition_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1r_candidate_coverage_scope_repair/phasee1r_o4_training_scope_comparison.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1r_candidate_coverage_scope_repair/phasee1r_recommended_broad_candidate_coverage_by_split.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1r_candidate_coverage_scope_repair/phasee1r_recommended_e2_candidate_contract.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1r_candidate_coverage_scope_repair/phasee1r_forbidden_action_audit.json`

## 8. 是否建议进入修订后的 E2

- 建议：允许进入修订后的 E2，gate 为 `phase_e1r_candidate_coverage_scope_repaired`。
