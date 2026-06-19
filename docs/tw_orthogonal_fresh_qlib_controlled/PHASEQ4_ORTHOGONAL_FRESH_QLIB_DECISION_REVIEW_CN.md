# Phase Q4 决策审查报告：Orthogonal Fresh Qlib

生成时间：`2026-06-15T16:53:49+00:00`

## 1. 结论

- 最终 gate：`orthogonal_fresh_qlib_not_supported_vs_fresh_qlib`
- 结论：Orthogonal Fresh Qlib 不优于原 fresh qlib baseline，暂不进入只读产品化候选。
- 原 fresh qlib 继续作为默认研究基线。

## 2. Q0-Q3 Gate 汇总

- Q0：`phase_q0_control_and_orthogonal_feature_contract_frozen`
- Q1：`phase_q1_orthogonal_qlib_feature_join_passed`
- Q2：`phase_q2_orthogonal_fresh_qlib_training_completed`
- Q3：`phase_q3_orthogonal_fresh_qlib_replay_completed`

## 3. 口径一致性

- control / treatment 使用同一 replay engine。
- execution rule 一致，均为 next-day execution。
- fee / tax 一致，分别为 `0.001425` 与 `0.003`。
- `candidate_k=50` 一致。
- `target_position_count=10` 一致。
- next-day accounting 一致且无违规。
- coverage 口径一致，control 与 treatment 的日度可用行数完全相同。

## 4. Q3 关键事实

### validation

- control net return: `0.038270`
- treatment net return: `-0.013483`
- relative return: `-0.051753`
- control max drawdown: `-0.151349`
- treatment max drawdown: `-0.191091`

### untouched test

- control net return: `0.662457`
- treatment net return: `0.481407`
- relative return: `-0.181050`
- control max drawdown: `-0.088396`
- treatment max drawdown: `-0.062138`

### 2025H2

- relative return: `-0.123914`
- relative drawdown: `+0.026258`

### 2026YTD

- relative return: `-0.015440`
- relative drawdown: `+0.007441`

## 5. 取舍判断

- action_count 基本一致，test 上两边均为 `410`。
- turnover_proxy 略低，但不是主要优势。
- fee_and_tax 略低，但不足以抵消收益落后。
- validation 与 untouched test 的净收益均落后 control。
- rolling 6m 里 treatment 仅在少数窗口回撤更好，收益仍持续落后。

## 6. Coverage 与 next-day accounting

- coverage 公平。
- validation/test 的 control 与 treatment 日度覆盖完全一致。
- no duplicate key，no missing-score gap。
- next-day accounting 无违规。
- 回放差异只来自 score/rank，不来自执行规则。

## 7. Feature Importance / PnL

- 正交特征有模型使用痕迹。
- `margin_balance` 是最强正交特征之一。
- 但 orthogonal feature 的重要性不足以转化为 replay 收益优势。
- PnL / turnover contribution 未显示单一股票或单一日期主导。
- 最大 symbol turnover share 约 `0.091935`，不存在单点集中到不可解释的程度。

## 8. 是否满足只读候选标准

- validation 不明显优于原 fresh qlib，不满足。
- untouched test 收益低于原 fresh qlib，不满足。
- 回撤改善不足以抵消收益落后。
- action_count / turnover 没有形成明确优势。
- PIT / join / accounting 无阻断。

结论：不支持进入只读产品化候选。

## 9. 后续建议

- 保留原 fresh qlib 作为默认研究基线。
- Orthogonal Fresh Qlib 继续保留为研究对照产物，不切换默认策略。
- 若后续继续探索，只能在新的冻结合同下重新设计，不得在当前合同上包装为更优候选。

## 10. 参考产物

- [Q0 执行报告](PHASEQ0_CONTROL_AND_FEATURE_CONTRACT_EXECUTION_REPORT_CN.md)
- [Q1 执行报告](PHASEQ1_ORTHOGONAL_QLIB_FEATURE_JOIN_EXECUTION_REPORT_CN.md)
- [Q2 执行报告](PHASEQ2_ORTHOGONAL_FRESH_QLIB_TRAINING_EXECUTION_REPORT_CN.md)
- [Q3 执行报告](PHASEQ3_ORTHOGONAL_FRESH_QLIB_REPLAY_EXECUTION_REPORT_CN.md)

