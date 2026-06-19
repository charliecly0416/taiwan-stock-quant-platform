# Phase E6 执行报告：2025 LTR 桥接双 qlib 底座

生成时间：`2026-06-16T05:06:57+00:00`

## 1. 结论

- gate：`phase_e6_bridge_ltr_2025_two_qlib_bases_completed`。
- 已在相同 2025 LTR 训练窗口下分别训练 fresh qlib 底座与 2018-2022 frozen qlib 底座的 orthogonal LTR。
- 两条分支共享同一 LightGBM LGBMRanker 参数、同一 label、同一 78 特征 whitelist、同一 2026 test window、同一 replay engine、同一 next-day accounting、同一 fee/tax、candidate_k=50、target_position_count=10；LTR 训练仅使用 label-complete 行。
- 未重训 qlib，未调参，未训练多版本挑选，未使用 2026 做训练/early stopping/选择，未触发前端/API/provider/accepted latest/monitor/交易链路。
- Branch A treatment vs control return diff：`0.175315`。
- Branch B treatment vs control return diff：`0.171928`。
- Branch A treatment - Branch B treatment return diff：`0.146102`。

## 2. 训练合同

| branch | qlib base | LTR train | LTR test | score source | caveat |
| --- | --- | --- | --- | --- | --- |
| Branch A | fresh qlib 2017-2024 | 2025-01-01..2025-12-31 | 2026-01-01..2026-05-07 | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_raw_score_rank.csv` | 2025H1 可能属于 fresh qlib validation；本分支是 fresh qlib frozen raw score + 2025 LTR train 桥接实验，不是严格 qlib-never-seen 2025 LTR train |
| Branch B | frozen qlib 2018-2022 | 2025-01-01..2025-12-31 | 2026-01-01..2026-05-07 | `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_train_sample_2023_2025.csv` / `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_test_sample_2026.csv` from E1 raw OOS | 2025 对 qlib 底座为 OOS |

## 3. 样本覆盖 / Top50 偏差审计

| branch | split | rows | dates | daily min/median/max | non-top50 rows | top50-only | full-market-top150-intersection |
| --- | --- | ---: | ---: | --- | ---: | --- | --- |
| branch_a_fresh_qlib | train_2025_label_complete_used_for_training | 36084 | 242 | 148/149.0/150 | 24081 | False | False |
| branch_a_fresh_qlib | test_2026_scored_for_replay | 11850 | 79 | 150/150.0/150 | 7900 | False | False |
| branch_b_frozen_qlib | train_2025_label_complete_used_for_training | 36053 | 242 | 148/149.0/149 | 23953 | False | False |
| branch_b_frozen_qlib | test_2026_scored_for_replay | 11822 | 79 | 149/150.0/150 | 7872 | False | False |

## 4. 2026 Replay 结果

| branch | role | method | net_return | max_drawdown | actions | turnover | fee_tax | rel_return_vs_control |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| branch_a_fresh_qlib | control | branch_a_repaired_fresh_qlib_top50_adaptive | 0.289419 | -0.037564 | 154 | 15.248647 | 50394.08 | 0.0 |
| branch_a_fresh_qlib | treatment | branch_a_fresh_qlib_orthogonal_ltr_2025 | 0.464734 | -0.058226 | 151 | 15.29539 | 53987.82 | 0.175315 |
| branch_b_frozen_qlib | control | branch_b_2018_2022_frozen_qlib_top50_baseline | 0.146704 | -0.05115 | 154 | 15.111736 | 46595.67 | 0.0 |
| branch_b_frozen_qlib | treatment | branch_b_2018_2022_frozen_qlib_orthogonal_ltr_2025 | 0.318632 | -0.083641 | 153 | 15.223378 | 51280.57 | 0.171928 |

## 5. Rank Metrics

| branch | split | spearman_ic_10d | ndcg@10 | ndcg@30 | ndcg@50 | audit_only |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| branch_a_fresh_qlib | train_2025 | 0.21887934 | 0.83656109 | 0.65335741 | 0.64340367 | False |
| branch_a_fresh_qlib | test_2026 | 0.05271194 | 0.36636411 | 0.37622607 | 0.42527598 | True |
| branch_b_frozen_qlib | train_2025 | 0.237967 | 0.8350521 | 0.66073884 | 0.64987377 | False |
| branch_b_frozen_qlib | test_2026 | 0.04143052 | 0.34916028 | 0.3663926 | 0.424097 | True |

## 6. 参考项

- E4 treatment（2018-2022 frozen qlib + 2023-2025 LTR）：net return `0.602499`，max DD `-0.071473`，actions `151`。
- E5B repaired fresh qlib exact 2026 bridge：net return `0.289419`，max DD `-0.037564`，actions `154`。
- 参考项只用于解释训练长度和比较链路，不用于模型选择、调参或阈值选择。

## 7. 必答审查

- 同一 2025 LTR 训练窗下，treatment 收益 Branch A `0.464734`，Branch B `0.318632`；本次 Branch A 更强。
- LTR 增益依赖 qlib 底座：Branch A 增益 `0.175315`，Branch B 增益 `0.171928`，方向和幅度不同。
- 训练长度影响增益：Branch B 2025-only LTR return `0.318632`，E4 2023-2025 LTR return `0.602499`，差异 `0.283867`，支持训练长度是重要解释变量。
- top50-only 训练偏差：两条分支 train daily rows 均大于 50，non-top50 rows 均大于 0，未发现 top50-only 训练偏差。
- 控制变量：除 qlib 底座 / qlib score 来源外，模型、参数、label、feature whitelist、训练窗、测试窗、回放口径均已对齐。
- 比较链路：E6 同时连接 fresh/frozen 底座、2025-only LTR 与 E4 2023-2025 LTR，可用于建立比较链路闭环；默认策略切换仍需另行决策，不在本阶段执行。

## 8. 输出 Artifact

- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_bridge_manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_branch_a_fresh_train_sample_2025.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_branch_a_fresh_test_sample_2026.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_branch_b_frozen_train_sample_2025.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_branch_b_frozen_test_sample_2026.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_group_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_rank_metrics.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_feature_importance.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_replay_ready_scores_2026.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_control_vs_treatment_summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_daily_nav_2026.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_actions_2026.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_coverage_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_next_day_accounting_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_pnl_concentration.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_forbidden_action_audit.json`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE6_BRIDGE_LTR_2025_TWO_QLIB_BASES_EXECUTION_REPORT_CN.md`
