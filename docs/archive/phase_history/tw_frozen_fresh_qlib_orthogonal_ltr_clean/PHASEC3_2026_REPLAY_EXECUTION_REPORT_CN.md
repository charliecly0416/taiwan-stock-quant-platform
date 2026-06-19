# Phase C3 执行报告：2026 同口径回放

生成时间：`2026-06-15T17:54:41+00:00`

## 1. 结论

- gate：`phase_c3_clean_stacking_2026_replay_completed`。
- 只在 2026 untouched test 上比较 frozen fresh qlib baseline 与 frozen fresh qlib + orthogonal LTR rerank。
- control/treatment 使用同一 S2D replay engine、同一 next-day accounting、同一 fee/tax、同一 candidate_k=50、同一 target_position_count=10。
- treatment 仅在 qlib top50 内重排，未新增股票、filter、market gate 或 turnover rule。
- treatment vs control：net return diff `-0.004798`，drawdown diff `-0.010791`，action diff `1`。

## 2. 使用 Artifact

- C2 manifest：`data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c2_orthogonal_ltr_training/phasec2_training_manifest.json`
- treatment score：`data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c2_orthogonal_ltr_training/phasec2_test_row_scores_2026.csv`
- C1 test sample：`data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_ltr_test_sample_2026.csv`
- replay-ready：`data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_replay_ready_scores_2026.csv`

## 3. 必须证明的等式

- `replay_engine_control_equals_treatment`：`True`
- `execution_rule_control_equals_treatment`：`True`
- `fee_tax_control_equals_treatment`：`True`
- `candidate_k_control_equals_treatment_equals_50`：`True`
- `target_position_count_control_equals_treatment_equals_10`：`True`
- `preserve_scope_control_equals_treatment_equals_top50_only`：`True`
- `next_day_accounting_control_equals_treatment`：`True`
- `coverage_method_control_equals_treatment`：`True`

## 4. 2026 Replay Metrics

| method | net_return | max_drawdown | action_count | turnover_proxy | fee_and_tax | relative_return | relative_drawdown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fresh_qlib_top50_adaptive_baseline | 0.21726 | -0.056116 | 153 | 15.09261 | 48854.89 | 0.0 | 0.0 |
| frozen_fresh_qlib_orthogonal_ltr | 0.212462 | -0.066907 | 154 | 15.296526 | 51149.91 | -0.004798 | -0.010791 |

## 5. Coverage

- window：`2026-01-02..2026-05-07`，date_count：`79`，row_count：`3950`。
- daily rows min/median/max：`50 / 50.0 / 50`。
- daily top50 min/median/max：`50 / 50.0 / 50`。
- coverage 公平，control/treatment score 行数一致。

## 6. Rank Metrics / Feature Importance

- C2 rank metrics 详见 `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_rank_metrics_summary.csv`；2026 test 仅 audit-only。
- feature importance 详见 `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_feature_importance_summary.csv`。
- C2 test spearman：`0.0535833947262623`，ndcg@10：`0.3350657352922095`。
- Top feature：`short_balance` / `margin_short`。

## 7. PnL Concentration / Accounting

- PnL concentration 详见 `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_pnl_concentration.csv`。
- next-day accounting audit 详见 `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_next_day_accounting_audit.csv`。

## 8. 边界审计

- 未训练 qlib / LTR。
- 未调参，未训练多个版本。
- 未使用 2026 label/future return 做回放决策。
- 未使用 qlib 2017..2024 in-sample score。
- 未引入 walk-forward / 多模型 score。
- 未新增 filter / market gate / turnover rule。
- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。

## 9. 输出 Artifact

- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_replay_manifest.json`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_replay_ready_scores_2026.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_control_vs_treatment_2026_summary.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_daily_nav_2026.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_actions_2026.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_coverage_audit.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_next_day_accounting_audit.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_pnl_concentration.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_rank_metrics_summary.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_feature_importance_summary.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_forbidden_action_audit.json`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/phasec3_replay_log.txt`

## 10. 是否建议进入 C4

- 建议：允许进入 C4，gate 为 `phase_c3_clean_stacking_2026_replay_completed`。
