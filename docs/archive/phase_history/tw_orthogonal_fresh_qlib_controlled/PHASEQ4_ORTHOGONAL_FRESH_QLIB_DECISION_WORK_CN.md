# Phase Q4 工作文档：Orthogonal Fresh Qlib 决策审查

生成日期：2026-06-15

## 1. 本阶段目标

本阶段只做一件事：

```text
基于 Q0-Q3 的冻结合同、训练审计和同口径回放结果，
判断 Orthogonal Fresh Qlib 是否值得进入只读产品化候选，
或应收尾为研究结论并继续保留原 fresh qlib baseline。
```

本阶段不训练、不回放、不调参、不改默认策略。

## 2. 上游 Gate

必须满足：

```text
phase_q0_control_and_orthogonal_feature_contract_frozen
phase_q1_orthogonal_qlib_feature_join_passed
phase_q2_orthogonal_fresh_qlib_training_completed
phase_q3_orthogonal_fresh_qlib_replay_completed
```

必须引用：

- `docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ0_CONTROL_AND_FEATURE_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ1_ORTHOGONAL_QLIB_FEATURE_JOIN_EXECUTION_REPORT_CN.md`
- `docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ2_ORTHOGONAL_FRESH_QLIB_TRAINING_EXECUTION_REPORT_CN.md`
- `docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ3_ORTHOGONAL_FRESH_QLIB_REPLAY_EXECUTION_REPORT_CN.md`

## 3. 决策问题

Q4 只回答：

```text
加入法人筹码和融资融券正交特征后的 Orthogonal Fresh Qlib，
是否比原 fresh qlib baseline 更适合作为只读候选？
```

不得扩展为：

- 是否实盘交易；
- 是否给买卖建议；
- 是否切换默认策略；
- 是否引入 LTR；
- 是否新增过滤规则；
- 是否用新窗口重训再试。

## 4. 必须使用的 Q3 事实

Q4 必须明确列出并解释以下 Q3 结果：

```text
validation:
control net return:   0.038270
treatment net return: -0.013483
relative return:      -0.051753
control max drawdown: -0.151349
treatment max drawdown: -0.191091

untouched test:
control net return:   0.662457
treatment net return: 0.481407
relative return:      -0.181050
control max drawdown: -0.088396
treatment max drawdown: -0.062138

2025H2:
relative return: -0.123914
relative drawdown: +0.026258

2026YTD:
relative return: -0.015440
relative drawdown: +0.007441
```

同时说明：

- action_count 基本一致；
- turnover_proxy 略低但不是主要优势；
- fee_and_tax 略低但不足以抵消收益落后；
- coverage 与 control 完全公平；
- 回放口径一致；
- next-day accounting 无违规；
- 正交特征有模型使用痕迹，但收益贡献不足。

## 5. 推荐通过标准

Orthogonal Fresh Qlib 只有在以下条件大体满足时，才可进入只读产品化候选：

- validation 不明显劣于原 fresh qlib；
- untouched test 收益高于原 fresh qlib，或收益相近但回撤/动作/换手明显更优；
- max drawdown 不明显恶化；
- action_count / turnover 不明显恶化；
- 增益不是单一股票或单一日期贡献；
- PIT / feature join / accounting 无阻断；
- 正交特征有可解释贡献。

若收益显著落后，即使回撤较好，也不得包装为优于原 fresh qlib。

## 6. Q4 执行范围

执行者应完成：

1. 汇总 Q0-Q3 的合同合规性。
2. 汇总 Q3 同口径回放表现。
3. 对 validation、untouched test、2025H2、2026YTD、rolling 6m 逐项判断。
4. 判断回撤改善是否足以抵消收益落后。
5. 判断 action_count、turnover_proxy、fee_and_tax 是否形成明确优势。
6. 判断正交特征重要性是否有解释价值。
7. 判断 PnL / turnover contribution 是否存在单一股票或单一日期集中。
8. 给出明确 gate：
   - `orthogonal_fresh_qlib_supported_for_readonly_candidate`
   - `orthogonal_fresh_qlib_not_supported_vs_fresh_qlib`
   - `orthogonal_fresh_qlib_blocked_by_data_or_contract`
9. 给出后续建议。

## 7. 禁止事项

Q4 禁止：

- 新训练；
- 新回放；
- 新调参；
- 改 split / label / universe；
- 改模型参数；
- 改 post-score filter；
- 引入 LTR；
- 新增 filter / market gate / turnover rule；
- 改默认前端策略；
- 接 provider refresh / publish / accepted latest；
- 接 monitor / broker / orders / quick-trade；
- 把训练窗口收益率当作策略优劣证据；
- 把只读历史回放包装为交易建议、目标仓位、收益承诺、胜率或上涨概率。

## 8. 输出报告

必须输出：

```text
docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ4_ORTHOGONAL_FRESH_QLIB_DECISION_REVIEW_CN.md
```

报告必须包含：

- Q0-Q3 gate 汇总；
- control/treatment 口径是否一致；
- validation / untouched test / 2025H2 / 2026YTD / rolling 6m 结论；
- return / drawdown / action_count / turnover / fee tax 取舍；
- coverage 公平性；
- next-day accounting 安全性；
- feature importance 解释；
- PnL contribution / 集中度；
- 是否满足推荐通过标准；
- 最终 gate；
- 是否保留原 fresh qlib 为默认研究基线；
- 是否允许进入只读候选；
- 后续建议。

## 9. 建议判定口径

基于 Q3 当前结果，除非执行者发现 Q3 计算错误，否则推荐判定为：

```text
orthogonal_fresh_qlib_not_supported_vs_fresh_qlib
```

建议表述：

```text
Orthogonal Fresh Qlib 在 PIT、join、训练和回放合同上合规，
但 validation 与 untouched test 收益均落后原 fresh qlib。
虽然 test max drawdown、turnover 和费用略有改善，
但不足以抵消 18.105 个百分点的 untouched test 净收益落后。
因此不建议进入默认策略或只读产品化候选；
原 fresh qlib 继续作为默认研究基线。
```

## 10. 给执行者的一句话

```text
请按 docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ4_ORTHOGONAL_FRESH_QLIB_DECISION_WORK_CN.md 执行 Phase Q4：只基于 Q0-Q3 已完成产物做决策审查，不训练、不回放、不调参、不改默认策略；重点判断 Orthogonal Fresh Qlib 相对原 Fresh Qlib 在同口径 validation、untouched test、2025H2、2026YTD、rolling 6m 的收益、回撤、动作次数、换手、费用、coverage、PnL contribution 和 feature importance 是否足以支持进入只读候选。若无计算错误，按 Q3 当前结果应判为 orthogonal_fresh_qlib_not_supported_vs_fresh_qlib。
```

## 11. 给审查者的一句话

```text
请按 docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ4_ORTHOGONAL_FRESH_QLIB_DECISION_WORK_CN.md 审查 Q4 决策报告，重点确认没有新增训练/回放/调参/规则，是否正确使用 Q3 同口径结果，是否没有把收益落后的 treatment 包装成优于 control，并确认最终 gate 是否合理。
```
