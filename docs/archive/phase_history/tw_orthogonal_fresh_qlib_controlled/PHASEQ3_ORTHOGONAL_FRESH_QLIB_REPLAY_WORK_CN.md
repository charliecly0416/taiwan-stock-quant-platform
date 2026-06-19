# Phase Q3 工作文档：Orthogonal Fresh Qlib 同口径回放对比

生成日期：2026-06-15

## 1. 本阶段目标

本阶段只做一件事：

```text
使用同一回放引擎、同一回放口径，
比较 Orthogonal Fresh Qlib 与原 Fresh Qlib baseline 的表现，
并输出收益、回撤、动作次数、换手、覆盖、PIT/accounting 与特征贡献审计。
```

本阶段不改默认策略，不引入 LTR，不改训练合同。

## 2. 上游 Gate

必须满足：

```text
phase_q0_control_and_orthogonal_feature_contract_frozen
phase_q1_orthogonal_qlib_feature_join_passed
phase_q2_orthogonal_fresh_qlib_training_completed
```

必须引用：

- `docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ0_CONTROL_AND_FEATURE_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ1_ORTHOGONAL_QLIB_FEATURE_JOIN_EXECUTION_REPORT_CN.md`
- `docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ2_ORTHOGONAL_FRESH_QLIB_TRAINING_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_training_manifest.json`

## 3. 对比对象

必须只比较以下两条线：

```text
control:     fresh_qlib_top50_adaptive_baseline
treatment:   orthogonal_fresh_qlib_top50_adaptive
```

control 侧必须来自原 fresh qlib baseline 的回放产物，不得换成其他实验或 LTR。

## 4. 冻结的回放合同

Q3 必须复刻原 fresh qlib 回放合同：

```text
strategy: fresh_qlib_top50_adaptive_baseline
execution: next-day execution
initial_equity: 1000000
fee_rate: 0.001425
tax_rate: 0.003
target_position_count: 10
candidate_k: 50
window: validation + untouched test
test focus: 2025-07-01..2026-05-07
```

不得改变：

- 交易日对齐；
- 次日执行口径；
- 费用与税率；
- 候选池大小；
- 目标持仓数；
- 验证/测试窗口；
- post-score filter；
- coverage 统计口径。

## 5. 输入产物

执行者应读取并使用：

- 原 fresh qlib control 回放产物
- Q2 raw score rank：
  `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_raw_score_rank.csv`
- Q2 post-filter score rank：
  `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_post_filter_score_rank.csv`
- Q2 feature importance：
  `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_feature_importance.csv`
- Q2 training manifest：
  `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_training_manifest.json`
- S2D replay gate：
  `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_gate_summary.json`

如需要补充 orthogonal fresh qlib 的 replay 结果，应放在 Q3 自己的产物目录中，不得修改 Q2 训练产物。

## 6. Q3 执行范围

执行者应完成：

1. 用同一回放引擎载入 control 与 treatment 的 score / rank 产物。
2. 复核 control 与 treatment 的 next-day accounting 口径一致。
3. 复核 candidate_k=50、target_position_count=10、fee/tax 参数一致。
4. 计算并输出以下维度的对比：
   - validation；
   - untouched test；
   - 2025H2；
   - 2026YTD；
   - rolling 6m；
   - market regime；
   - fee/tax adjusted net return；
   - max drawdown；
   - action_count；
   - turnover_proxy；
   - fee_and_tax；
   - next-day accounting；
   - coverage；
   - PnL contribution；
   - feature importance summary。
5. 说明 treatment 相对 control 的提升或退化。
6. 说明增益是否稳定，是否集中于单一股票或单一日期。
7. 说明 orthogonal 特征是否在 replay 层面产生可解释贡献。
8. 输出 forbidden action audit。

## 7. 必须证明的等式

Q3 报告必须明确证明：

```text
replay_engine_control == replay_engine_treatment
execution_rule_control == execution_rule_treatment
fee_tax_control == fee_tax_treatment
candidate_k_control == candidate_k_treatment == 50
target_position_count_control == target_position_count_treatment == 10
next_day_accounting_control == next_day_accounting_treatment
coverage_method_control == coverage_method_treatment
```

并明确指出对比结果是否仅来自 score/rank 差异，而不是回放口径差异。

## 8. 输出目录

建议输出到：

```text
data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q3_orthogonal_fresh_qlib_replay/
```

至少包含：

```text
phase_q3_replay_manifest.json
phase_q3_control_vs_treatment_summary.csv
phase_q3_validation_summary.csv
phase_q3_test_summary.csv
phase_q3_2025h2_summary.csv
phase_q3_2026ytd_summary.csv
phase_q3_rolling6m_summary.csv
phase_q3_market_regime_summary.csv
phase_q3_pnl_contribution.csv
phase_q3_feature_importance_summary.csv
phase_q3_forbidden_action_audit.json
phase_q3_replay_log.txt
```

## 9. 报告要求

必须输出：

```text
docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ3_ORTHOGONAL_FRESH_QLIB_REPLAY_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 做了什么；
- 使用 artifact；
- 输入/输出路径；
- control vs treatment 的 score/rank 来源；
- 回放引擎和参数；
- validation / untouched test / 2025H2 / 2026YTD / rolling 6m 对比；
- market regime 分解；
- fee/tax adjusted net return；
- max drawdown；
- action_count；
- turnover_proxy；
- fee_and_tax；
- next-day accounting 说明；
- coverage 对比；
- PnL contribution；
- feature importance summary；
- 是否存在只报告收益不报告风险的情况；
- 是否触发停止条件；
- 是否建议进入 Q4。

## 10. 停止条件

遇到以下任一情况必须停止并报告：

- 回放引擎口径不一致；
- 原 fresh qlib 指标无法复现；
- coverage 不公平且无法解释；
- next-day accounting 违规；
- 只报告收益不报告回撤/动作/换手；
- 需要改 replay 规则才能对比；
- 需要引入 LTR、额外规则或默认策略改动；
- 需要改训练合同、model family、split、label、universe 或 provider。

## 11. 禁止事项

Q3 禁止：

- 引入 LTR；
- 改默认策略；
- 改 replay 规则；
- 改训练合同；
- 改 post-score filter；
- 改 candidate_k / target_position_count / fee / tax；
- 改 split / label / universe；
- 改 provider；
- 改前端；
- 接 provider refresh / publish / accepted latest；
- 接 monitor / broker / orders / quick-trade；
- 发出任何真实交易建议、目标仓位、目标权重、收益承诺、胜率或上涨概率。

## 12. Gate

Q3 通过 gate：

```text
phase_q3_orthogonal_fresh_qlib_replay_completed
```

只有在以下条件全部满足时，审查者才可允许进入 Q4：

- control 与 treatment 采用同一回放引擎；
- replay 规则完全一致；
- coverage 口径一致且可解释；
- next-day accounting 无违规；
- 已输出收益、回撤、动作次数、换手、PnL contribution 与 feature importance summary；
- 没有引入 LTR 或额外规则；
- 没有触发前端、provider、accepted latest、monitor 或交易链路。

## 13. 给执行者的一句话

```text
请按 docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ3_ORTHOGONAL_FRESH_QLIB_REPLAY_WORK_CN.md 执行 Phase Q3：使用同一回放引擎与同一回放口径比较 Orthogonal Fresh Qlib 与原 Fresh Qlib baseline，只输出 validation、untouched test、2025H2、2026YTD、rolling 6m、market regime、fee/tax adjusted net return、max drawdown、action_count、turnover_proxy、fee_and_tax、next-day accounting、coverage、PnL contribution 和 feature importance summary；不得改 replay 规则、不得引入 LTR 或默认策略改动、不得触发前端/provider/accepted latest/monitor/交易链路。
```

## 14. 给审查者的一句话

```text
请按 docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ3_ORTHOGONAL_FRESH_QLIB_REPLAY_WORK_CN.md 审查执行者 Q3 报告，重点确认 control/treatment 使用同一回放引擎和同一口径，coverage 与 next-day accounting 无违规，收益、回撤、动作次数、换手、PnL contribution 和 feature importance summary 均已给出，且没有引入 LTR、额外规则或默认策略改动，并判断是否允许进入 Q4。
```
