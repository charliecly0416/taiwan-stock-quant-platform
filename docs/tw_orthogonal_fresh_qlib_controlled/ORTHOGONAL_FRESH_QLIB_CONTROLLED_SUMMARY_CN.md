# Orthogonal Fresh Qlib 受控实验总结

生成日期：2026-06-15

## 1. 最终结论

本主线已经收口。

最终 gate：

```text
orthogonal_fresh_qlib_not_supported_vs_fresh_qlib
```

结论：

```text
Orthogonal Fresh Qlib 在数据接入、PIT、训练和回放合同上合规，
但同口径回放结果不优于原 fresh qlib baseline。
因此不进入只读产品化候选，不切换默认策略。
原 fresh qlib 继续作为默认研究基线。
```

## 2. 本主线回答的问题

本主线只验证一个问题：

```text
把法人筹码与融资融券正交特征前移到 qlib 第一阶段模型后，
是否能让 fresh qlib 比原 baseline 更好？
```

答案：

```text
不能。
```

正交特征确实被模型使用，但没有转化为更好的同口径回放收益。

## 3. 阶段结果

### Phase Q0：合同冻结

结果：

```text
phase_q0_control_and_orthogonal_feature_contract_frozen
```

完成内容：

- 冻结原 fresh qlib control 合同；
- 冻结 train / validation / test 窗口；
- 冻结 provider、LGBModel、模型参数、universe 与 post-score filter；
- 确认 O2 法人筹码与融资融券特征是唯一允许新增变量；
- 明确禁止 LTR、额外规则、前端/provider/accepted latest/monitor/交易链路。

### Phase Q1：正交特征接入与样本对齐

结果：

```text
phase_q1_orthogonal_qlib_feature_join_passed
```

关键事实：

- control rows：`326915`
- treatment rows：`326915`
- symbol count：`150`
- date range：`2017-01-10..2026-05-07`
- 新增列仅来自 Q0 白名单正交特征、missing/delay/lineage/PIT audit 字段；
- `available_at <= signal_asof` 无违规；
- 没有删行、删股票或改 split / label / universe。

### Phase Q2：Orthogonal Fresh Qlib 训练

结果：

```text
phase_q2_orthogonal_fresh_qlib_training_completed
```

关键事实：

- model family：`qlib.contrib.model.gbdt.LGBModel`
- 使用原 S2B fresh qlib 模型参数；
- Alpha158 feature count：`158`
- orthogonal training feature count：`42`
- final training feature count：`200`
- raw score rows：`326915`
- post-filter rows：`169366`
- successful thread count：`4`

正交特征有模型使用痕迹：

- `margin_balance` 是最强正交特征之一；
- orthogonal feature importance gain share 约 `7.94%`；
- 但模型使用不等于策略表现提升。

### Phase Q3：同口径回放对比

结果：

```text
phase_q3_orthogonal_fresh_qlib_replay_completed
```

回放合同一致：

- 同一 replay engine；
- same next-day execution；
- `candidate_k=50`；
- `target_position_count=10`；
- fee rate `0.001425`；
- tax rate `0.003`；
- coverage 口径一致；
- next-day accounting 无违规。

核心结果：

| 区间 | 原 fresh qlib | Orthogonal Fresh Qlib | 差异 |
| --- | ---: | ---: | ---: |
| validation net return | `0.038270` | `-0.013483` | `-0.051753` |
| untouched test net return | `0.662457` | `0.481407` | `-0.181050` |
| 2025H2 relative return | - | - | `-0.123914` |
| 2026YTD relative return | - | - | `-0.015440` |

风险与交易成本：

- untouched test max drawdown：treatment `-0.062138`，control `-0.088396`，treatment 回撤更好；
- test action_count：两边均为 `410`；
- turnover_proxy treatment 略低；
- fee_and_tax treatment 略低；
- 但这些改善不足以抵消 untouched test `18.105` 个百分点的净收益落后。

### Phase Q4：决策收口

结果：

```text
orthogonal_fresh_qlib_not_supported_vs_fresh_qlib
```

判定：

- 不支持进入只读产品化候选；
- 不支持替代原 fresh qlib；
- 不支持切换默认策略；
- 保留为研究对照产物。

## 4. 为什么没有通过

主要原因：

```text
收益显著落后。
```

具体表现：

- validation 已经从 `+3.827%` 变为 `-1.348%`；
- untouched test 从 `+66.246%` 降到 `+48.141%`；
- 2025H2 与 2026YTD 都落后；
- 回撤改善存在，但不足以抵消收益损失；
- action_count、turnover、fee/tax 没有形成足够强的优势。

因此不能把 Orthogonal Fresh Qlib 包装为更优策略。

## 5. 这次实验仍然有价值的地方

本主线证明了几件事：

- O2 正交特征可以 PIT-safe 地接入 qlib 训练样本；
- `available_at` delayed availability 合同可以落地；
- 正交特征确实被模型使用；
- 但在当前 frozen fresh qlib 合同下，正交特征前移到第一阶段 qlib 不带来更好同口径结果；
- 原 fresh qlib baseline 的优势仍然成立。

## 6. 默认策略与产品状态

当前状态：

```text
默认研究基线：fresh qlib
Orthogonal Fresh Qlib：研究对照产物
LTR：不在本主线内
```

禁止结论：

- 不得把 Orthogonal Fresh Qlib 设为默认；
- 不得进入只读产品化候选；
- 不得作为交易建议；
- 不得给目标仓位、目标权重、收益承诺、胜率或上涨概率；
- 不得触发 provider refresh / publish / accepted latest / monitor / broker / orders / quick-trade。

## 7. 后续建议

短期建议：

```text
收口本主线，不继续在当前合同下补丁式优化。
```

如果后续继续研究正交数据，应新开主线并重新冻结合同，可能方向包括：

- 单独研究正交特征在不同市场 regime 下是否有条件价值；
- 研究正交特征是否只适合作为二阶段 rerank，而不是第一阶段 qlib 特征；
- 研究更严格的特征筛选或 regularization，但必须新合同、新训练、新审查；
- 研究是否仅在风险控制视角使用正交数据，而不是收益增强。

任何后续探索都不得沿用本主线结果直接改默认策略。

## 8. 主要文档索引

- 主线：`docs/tw_orthogonal_fresh_qlib_controlled/ORTHOGONAL_FRESH_QLIB_CONTROLLED_MAINLINE_CN.md`
- Q0 报告：`docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ0_CONTROL_AND_FEATURE_CONTRACT_EXECUTION_REPORT_CN.md`
- Q1 工作文档：`docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ1_ORTHOGONAL_QLIB_FEATURE_JOIN_WORK_CN.md`
- Q1 报告：`docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ1_ORTHOGONAL_QLIB_FEATURE_JOIN_EXECUTION_REPORT_CN.md`
- Q2 工作文档：`docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ2_ORTHOGONAL_FRESH_QLIB_TRAINING_WORK_CN.md`
- Q2 报告：`docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ2_ORTHOGONAL_FRESH_QLIB_TRAINING_EXECUTION_REPORT_CN.md`
- Q3 工作文档：`docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ3_ORTHOGONAL_FRESH_QLIB_REPLAY_WORK_CN.md`
- Q3 报告：`docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ3_ORTHOGONAL_FRESH_QLIB_REPLAY_EXECUTION_REPORT_CN.md`
- Q4 工作文档：`docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ4_ORTHOGONAL_FRESH_QLIB_DECISION_WORK_CN.md`
- Q4 决策报告：`docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ4_ORTHOGONAL_FRESH_QLIB_DECISION_REVIEW_CN.md`
