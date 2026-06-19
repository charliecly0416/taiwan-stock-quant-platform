# Phase E4 工作文档：2026 Untouched Replay

生成日期：2026-06-15

## 1. 本阶段目标

本阶段只做 2026 untouched test 回放：

```text
比较 extended_oos_frozen_qlib_top50_baseline
与 extended_oos_frozen_qlib_orthogonal_ltr
在 2026-01-01..2026-05-07 同窗口、同回放口径下的表现。
```

本阶段不得训练 qlib、不得训练 LTR、不得调参、不得改特征、不得改窗口。

## 2. 上游 Gate

必须满足：

```text
phase_e0_extended_oos_contract_feasible
phase_e1_frozen_qlib_oos_score_completed
phase_e1r_candidate_coverage_scope_repaired
phase_e2_extended_oos_ltr_sample_passed
phase_e3_extended_oos_ltr_trained
```

必须引用：

- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE1R_CANDIDATE_COVERAGE_SCOPE_REPAIR_EXECUTION_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE2_ROW_ALIGNED_SAMPLE_EXECUTION_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE3_ORTHOGONAL_LTR_TRAINING_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_test_row_scores_2026.csv`

## 3. 重要口径收口

E1R/E2 已经修正早期 `preserve_scope: top50_only` 歧义：

```text
LTR training scope: old O4-style broad candidate rows
Replay treatment boundary: qlib top50 rerank only
```

因此 E4 必须遵守：

- 训练口径不得回退为 top50-only；
- 回放候选只能来自同日 frozen qlib top50；
- treatment 只能在 frozen qlib top50 内用 E3 LTR score 重排；
- 不得把 qlib top50 外股票加入策略候选；
- 不得新增 post-score filter、market gate、turnover rule 或阈值规则。

## 4. 回放合同

固定回放口径：

```text
window: 2026-01-01..2026-05-07
execution: next-day execution
fee_rate: 0.001425
tax_rate: 0.003
target_position_count: 10
candidate_k: 50
control score: E1 frozen qlib score/rank
treatment score: phasee3_extended_oos_ltr_score
```

Control：

```text
extended_oos_frozen_qlib_top50_baseline
```

Treatment：

```text
extended_oos_frozen_qlib_orthogonal_ltr
```

## 5. 输入 Artifact

必须使用：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_test_sample_2026.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_test_row_scores_2026.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_rank_metrics.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_feature_importance.csv
```

不得使用 2026 label、future return 或 realized PnL 做任何排序、筛选、阈值选择或模型选择。

## 6. 执行要求

执行者应完成：

1. 构建 2026 replay-ready score table。
2. 对每个交易日确认 frozen qlib top50 完整性。
3. Control 使用 frozen qlib top50 原始排序回放。
4. Treatment 只在同日 frozen qlib top50 内按 E3 LTR score 重排后回放。
5. 两条策略使用完全相同的交易日、价格、next-day execution、fee、tax、持仓数和 candidate_k。
6. 输出 coverage audit，确认 control/treatment 的日覆盖一致。
7. 输出 next-day accounting audit，确认无同日成交、无未来价格倒灌。
8. 输出交易动作、日净值、收益、回撤、换手或 action_count、费用税费。
9. 输出 PnL concentration，避免只看总收益。
10. 汇总 E3 rank metrics 与 feature importance，但不得据此调参。

## 7. 输出目录

建议输出到：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/
```

至少包含：

```text
phasee4_replay_manifest.json
phasee4_replay_ready_scores_2026.csv
phasee4_control_vs_treatment_2026_summary.csv
phasee4_daily_nav_2026.csv
phasee4_actions_2026.csv
phasee4_coverage_audit.csv
phasee4_next_day_accounting_audit.csv
phasee4_pnl_concentration.csv
phasee4_rank_metrics_summary.csv
phasee4_feature_importance_summary.csv
phasee4_forbidden_action_audit.json
phasee4_replay_log.txt
```

## 8. 指标要求

报告必须至少包含：

- control net return；
- treatment net return；
- incremental return；
- control max drawdown；
- treatment max drawdown；
- action_count；
- turnover proxy；
- fee and tax total；
- daily coverage min/median/max；
- qlib top50 completeness；
- treatment 是否只在 qlib top50 内重排；
- next-day execution audit；
- PnL concentration；
- 2026 rank metrics audit-only summary；
- feature importance summary。

## 9. 执行报告

必须输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE4_2026_REPLAY_EXECUTION_REPORT_CN.md
```

报告必须明确：

- 是否复现 2026 frozen qlib baseline；
- treatment 是否严格 top50 内 rerank；
- 是否同窗口同回放口径；
- 是否有 coverage 不公平；
- 是否有 next-day accounting 问题；
- 是否错误使用 2026 label/future return；
- 是否引入新规则；
- 是否建议进入 E5 决策审查。

## 10. 停止条件

遇到以下任一情况必须停止并报告：

- 2026 frozen qlib baseline 无法复现；
- control/treatment 交易窗口或价格口径不一致；
- treatment 使用 qlib top50 外股票；
- 使用 2026 label、future return 或 realized PnL 做排序、筛选或选择；
- 新增 filter、market gate、turnover rule、止损止盈或阈值；
- 回放不是 next-day execution；
- coverage 不公平且无法解释；
- 只报告收益，不报告回撤、动作、换手、费用税费；
- 触发 provider、accepted latest、frontend、monitor、交易链路。

## 11. 禁止事项

E4 禁止：

- 训练或重训 qlib；
- 训练或重训 LTR；
- 改 LTR 参数；
- 改 feature whitelist；
- 改 label；
- 改 split；
- 调整 candidate_k、持仓数、fee、tax；
- 新增任何策略规则；
- 把 2026 audit metric 当作调参依据；
- 触发 provider refresh/publish；
- 切换 accepted latest；
- 修改前端/API/monitor；
- 触发 broker、quick-trade、orders。

## 12. Gate

若 E4 完成且未触发停止条件，gate 为：

```text
phase_e4_extended_oos_2026_replay_completed
```

E4 只产出 replay 事实，不直接宣布产品化或默认策略变更。是否支持“长训练 LTR 有增益”的结论留到 E5 决策审查。
