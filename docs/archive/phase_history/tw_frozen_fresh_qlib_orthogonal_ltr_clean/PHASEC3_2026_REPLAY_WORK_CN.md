# Phase C3 工作文档：2026 同口径回放

生成日期：2026-06-15

## 1. 本阶段目标

本阶段只做一件事：

```text
在 2026 untouched test 上，
用同一回放引擎和同一交易口径比较 frozen fresh qlib baseline
与 frozen fresh qlib + orthogonal LTR rerank treatment。
```

本阶段不训练、不调参、不改默认策略。

## 2. 上游 Gate

必须满足：

```text
phase_c0_clean_stacking_contract_feasible
phase_c1_clean_stacking_sample_passed
phase_c2_clean_stacking_ltr_trained
```

必须引用：

- `docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/FROZEN_FRESH_QLIB_ORTHOGONAL_LTR_CLEAN_MAINLINE_CN.md`
- `docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC0_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md`
- `docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC1_ROW_ALIGNED_SAMPLE_EXECUTION_REPORT_CN.md`
- `docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC2_ORTHOGONAL_LTR_TRAINING_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c2_orthogonal_ltr_training/phasec2_training_manifest.json`

## 3. 对比对象

必须比较：

```text
control:   fresh_qlib_top50_adaptive_baseline
treatment: frozen_fresh_qlib_orthogonal_ltr
```

主结论只能基于：

```text
2026-01-01..2026-05-07 untouched test
```

可保留审计参考：

- O4 orthogonal LTR；
- repaired fresh qlib P1 result；
- C2 rank metrics。

但这些参考不得作为主结论。

## 4. 回放合同

C3 必须复刻 frozen fresh qlib baseline 的回放口径：

```text
execution: next-day execution
fee_rate: 0.001425
tax_rate: 0.003
target_position_count: 10
candidate_k: 50
preserve_scope: top50_only
window: 2026-01-01..2026-05-07
```

不得改变：

- 回放引擎；
- 次日执行；
- 费用/税率；
- candidate_k；
- target_position_count；
- top50 preserve scope；
- 价格/accounting 口径；
- coverage 统计口径。

## 5. 输入产物

### Control

Control 必须来自 frozen fresh qlib baseline 的 2026 score / replay-ready artifact，例如：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv
```

以及必要的 repaired fresh top50 replay-ready / S2D 回放产物。

### Treatment

Treatment 必须来自 C2：

```text
data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c2_orthogonal_ltr_training/phasec2_test_row_scores_2026.csv
```

Treatment score column：

```text
phasec2_clean_stacking_ltr_score
```

Treatment rank column：

```text
phasec2_ltr_rank
```

禁止使用 `relevance_10d_top_heavy`、`future_excess_return_rank_10d` 或任何未来收益字段做回放决策。

## 6. C3 执行范围

执行者应完成：

1. 读取 C2 2026 treatment score。
2. 读取 frozen fresh qlib 2026 baseline score。
3. 复现 baseline 2026 指标。
4. 构建 treatment replay-ready scores：
   - 仅在 qlib top50 内 rerank；
   - 不新增股票；
   - 不从 top50 外补股票；
   - 不使用 2026 label 或未来收益；
   - 不新增 filter / market gate / turnover rule。
5. 用同一回放引擎回放 control 与 treatment。
6. 输出：
   - fee/tax adjusted net return；
   - max drawdown；
   - action_count；
   - turnover_proxy；
   - fee_and_tax；
   - next-day accounting；
   - coverage；
   - PnL concentration；
   - rank metrics；
   - feature importance summary；
   - 2026 是否形成真实增益。
7. 输出 forbidden action audit。

## 7. 必须证明的等式

C3 报告必须明确证明：

```text
replay_engine_control == replay_engine_treatment
execution_rule_control == execution_rule_treatment
fee_tax_control == fee_tax_treatment
candidate_k_control == candidate_k_treatment == 50
target_position_count_control == target_position_count_treatment == 10
preserve_scope_control == preserve_scope_treatment == top50_only
next_day_accounting_control == next_day_accounting_treatment
coverage_method_control == coverage_method_treatment
```

必须证明 treatment 只是在 frozen fresh qlib top50 内重排。

## 8. 输出目录

建议输出到：

```text
data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c3_2026_replay/
```

至少包含：

```text
phasec3_replay_manifest.json
phasec3_replay_ready_scores_2026.csv
phasec3_control_vs_treatment_2026_summary.csv
phasec3_daily_nav_2026.csv
phasec3_actions_2026.csv
phasec3_coverage_audit.csv
phasec3_next_day_accounting_audit.csv
phasec3_pnl_concentration.csv
phasec3_rank_metrics_summary.csv
phasec3_feature_importance_summary.csv
phasec3_forbidden_action_audit.json
phasec3_replay_log.txt
```

## 9. 执行报告要求

必须输出：

```text
docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC3_2026_REPLAY_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 做了什么；
- 使用 artifact；
- 输入/输出路径；
- control/treatment score 来源；
- 2026 window；
- baseline 2026 指标是否复现；
- replay engine 与参数；
- coverage；
- fee/tax adjusted net return；
- max drawdown；
- action_count；
- turnover_proxy；
- fee_and_tax；
- next-day accounting；
- PnL concentration；
- rank metrics；
- feature importance summary；
- treatment 是否形成真实增益；
- 是否使用 2026 label / future return 做决策；
- 是否新增 filter / market gate / turnover rule；
- 是否触发 frontend/API/provider/accepted latest/monitor/交易链路；
- 是否触发停止条件；
- 是否建议进入 C4。

## 10. 停止条件

遇到以下任一情况必须停止并报告：

- baseline 2026 指标无法复现；
- 回放引擎口径不一致；
- next-day accounting 违规；
- coverage 不公平且无法解释；
- 2026 label / future return 被用于回放决策；
- treatment 不再是 top50-only rerank；
- 需要新增 filter / market gate / turnover rule；
- 2026 数据被用于训练、调参或模型选择；
- 只报告收益不报告回撤、动作、换手；
- 需要改 split / label / model / qlib score provenance。

## 11. 禁止事项

C3 禁止：

- 训练 qlib；
- 训练 LTR；
- 调参；
- 训练多个版本；
- 改 replay 规则；
- 改 split / label / model；
- 使用 2026 label 或未来收益做回放决策；
- 使用 qlib 2017..2024 in-sample score；
- 引入 walk-forward / 多模型 score；
- 新增 filter / market gate / turnover rule；
- 改 provider / accepted latest；
- 改默认前端策略；
- 触发 monitor / broker / orders / quick-trade；
- 输出真实买卖建议、目标仓位、目标权重、收益承诺、胜率或上涨概率。

## 12. Gate

C3 通过 gate：

```text
phase_c3_clean_stacking_2026_replay_completed
```

只有在以下条件全部满足时，审查者才可允许进入 C4：

- baseline 2026 指标可复现；
- control/treatment 回放口径完全一致；
- treatment 只在 qlib top50 内 rerank；
- 未使用 2026 label/future return 做决策；
- next-day accounting 无违规；
- coverage 公平且可解释；
- 已报告收益、回撤、动作、换手、费用和集中度；
- 未新增规则；
- 未触发前端/provider/accepted latest/monitor/交易链路。

## 13. 给执行者的一句话

```text
请按 docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC3_2026_REPLAY_WORK_CN.md 执行 Phase C3：只在 2026 untouched test 上，用同一回放引擎和同一 next-day/fee/tax/candidate_k=50/target_position_count=10/top50-only 口径比较 frozen fresh qlib baseline 与 frozen_fresh_qlib_orthogonal_ltr；treatment 只能使用 C2 的 phasec2_clean_stacking_ltr_score 在 frozen fresh qlib top50 内重排，不得使用 2026 label/future return，不得新增 filter/market gate/turnover rule，不得训练、调参或触发前端/provider/accepted latest/monitor/交易链路。
```

## 14. 给审查者的一句话

```text
请按 docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC3_2026_REPLAY_WORK_CN.md 审查执行者 C3 报告，重点确认 baseline 2026 可复现、control/treatment 回放口径一致、treatment 仅为 top50 内 LTR rerank、未使用 2026 label/future return、coverage/next-day accounting 无违规，并判断是否允许进入 C4。
```
