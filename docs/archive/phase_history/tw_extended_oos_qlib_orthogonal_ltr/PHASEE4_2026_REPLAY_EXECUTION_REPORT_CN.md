# Phase E4 执行报告：2026 Untouched Replay

生成时间：`2026-06-15T19:12:52+00:00`

## 1. 结论

- gate：`phase_e4_extended_oos_2026_replay_completed`。
- 只在 2026 untouched test 上比较 extended_oos frozen qlib top50 baseline 与 extended_oos frozen qlib + orthogonal LTR rerank。
- control/treatment 使用同一 S2D replay engine、同一 next-day accounting、同一 fee/tax、同一 candidate_k=50、同一 target_position_count=10。
- treatment 仅在 qlib top50 内重排，未新增股票、filter、market gate 或 turnover rule。
- treatment vs control：net return diff `0.455795`，drawdown diff `-0.020323`，action diff `-3`。

## 2. 使用 Artifact

- E3 manifest：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_manifest.json`
- treatment score：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_test_row_scores_2026.csv`
- E2 test sample：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_test_sample_2026.csv`
- replay-ready：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_ready_scores_2026.csv`

## 3. 必须证明的等式

- `replay_engine_control_equals_treatment`：`True`
- `execution_rule_control_equals_treatment`：`True`
- `fee_tax_control_equals_treatment`：`True`
- `candidate_k_control_equals_treatment_equals_50`：`True`
- `target_position_count_control_equals_treatment_equals_10`：`True`
- `treatment_only_reranks_within_qlib_top50`：`True`
- `next_day_accounting_control_equals_treatment`：`True`
- `coverage_method_control_equals_treatment`：`True`

## 4. 2026 Replay Metrics

| method | net_return | max_drawdown | action_count | turnover_proxy | fee_and_tax | relative_return | relative_drawdown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| extended_oos_frozen_qlib_top50_baseline | 0.146704 | -0.05115 | 154 | 15.111736 | 46595.67 | 0.0 | 0.0 |
| extended_oos_frozen_qlib_orthogonal_ltr | 0.602499 | -0.071473 | 151 | 14.904165 | 53524.77 | 0.455795 | -0.020323 |

## 5. Coverage

- window：`2026-01-02..2026-05-07`，date_count：`79`，row_count：`3950`。
- daily rows min/median/max：`50 / 50.0 / 50`。
- daily top50 min/median/max：`50 / 50.0 / 50`。
- coverage 公平，control/treatment score 行数一致。

## 6. Rank Metrics / Feature Importance

- E3 rank metrics 详见 `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_rank_metrics_summary.csv`；2026 test 仅 audit-only。
- feature importance 详见 `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_feature_importance_summary.csv`。
- E3 test spearman：`0.0919401540460719`，ndcg@10：`0.4052261228437372`。
- Top feature：`volatility20` / `control_original`。

## 7. PnL Concentration / Accounting

- PnL concentration 详见 `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_pnl_concentration.csv`。
- next-day accounting audit 详见 `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_next_day_accounting_audit.csv`。

## 8. 边界审计

- 未训练 qlib / LTR。
- 未调参，未训练多个版本。
- 未使用 2026 label/future return 做回放决策。
- treatment 只在 qlib top50 内重排。
- 未新增 filter / market gate / turnover rule。
- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。

## 9. 输出 Artifact

- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_ready_scores_2026.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_control_vs_treatment_2026_summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_daily_nav_2026.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_actions_2026.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_coverage_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_next_day_accounting_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_pnl_concentration.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_rank_metrics_summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_feature_importance_summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_forbidden_action_audit.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_log.txt`

## 10. 是否建议进入 E5

- 建议：允许进入 E5，gate 为 `phase_e4_extended_oos_2026_replay_completed`。
