# Phase Q2 工作文档：Orthogonal Fresh Qlib 训练

生成日期：2026-06-15

## 1. 本阶段目标

本阶段只做一件事：

```text
在完整复刻原 S2B fresh qlib 训练合同的前提下，
只加入 Q1 已通过审计的 O2 PIT-safe 正交特征，
训练 Orthogonal Fresh Qlib，并输出训练、打分、特征重要性和安全审计产物。
```

本阶段可以训练模型，但不做策略回放、不做默认策略讨论、不改前端。

## 2. 上游 Gate

必须满足：

```text
phase_q0_control_and_orthogonal_feature_contract_frozen
phase_q1_orthogonal_qlib_feature_join_passed
```

必须引用：

- `docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ0_CONTROL_AND_FEATURE_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ1_ORTHOGONAL_QLIB_FEATURE_JOIN_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q1_orthogonal_qlib_feature_join/feature_join_manifest.json`

## 3. 冻结的 Control 合同

Q2 必须复刻原 S2B fresh qlib baseline：

```text
train:      2017-01-10..2024-12-31
validation: 2025-01-01..2025-06-30
test:       2025-07-01..2026-05-07

handler_start: 2015-05-04
handler_end:   2026-05-07
fit_start:     2015-05-04
fit_end:       2024-12-31

provider: qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
handler instruments: all
post-score filter: tw_liquid_dyn as-of active instrument range / same-day price / >=60 history / trailing 60-day value top150
model family: qlib.contrib.model.gbdt.LGBModel
model params: original S2B fresh qlib params
thread ladder: 4 -> 2 -> 1
```

训练实现如需改变以上任一项，必须停止并请求用户确认。

## 4. 唯一允许变化

唯一允许变化：

```text
在原 Alpha158 特征之外，追加 Q1 通过的正交特征列。
```

允许输入：

```text
data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q1_orthogonal_qlib_feature_join/treatment_joined_sample.csv
```

允许新增列必须等于 Q1 manifest / schema diff 中通过的：

- 法人筹码特征；
- 融资融券特征；
- 对应 missing flag；
- 对应 delay / lineage / PIT audit 字段，如训练实现需要保留作审计字段。

训练特征应只使用数值型可训练列；lineage/path/reason 等非数值审计字段不得作为模型特征输入，必须保留在审计产物中说明。

## 5. Q2 执行范围

执行者应完成：

1. 读取原 S2B fresh qlib config / manifest / model params。
2. 读取 Q1 treatment joined sample 与 schema diff。
3. 构建 Orthogonal Fresh Qlib 训练配置。
4. 明确列出最终训练特征列表：
   - 原 Alpha158 特征；
   - Q1 通过的正交数值特征；
   - missing/delay 数值 flag。
5. 明确排除非训练字段：
   - date / instrument / split；
   - score / rank；
   - lineage source；
   - raw snapshot path；
   - reason text；
   - matched available_at / matched trade_date；
   - PIT audit boolean 字段，除非仅作为审计输出。
6. 使用原 S2B LGBModel 与原 S2B params 训练。
7. 如发生 OOM，只允许按 `4 -> 2 -> 1` 线程阶梯重跑。
8. 输出 validation/test raw score rank。
9. 输出 post-filter score rank，filter 口径必须等于 control。
10. 输出 feature importance。
11. 输出 resource audit。
12. 输出 leakage / PIT / available_at audit。
13. 输出 forbidden action audit。

## 6. 输出目录

建议输出到：

```text
data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/
```

至少包含：

```text
phase_q2_training_manifest.json
phase_q2_generated_qlib_config.yaml
phase_q2_model_artifact/
phase_q2_raw_score_rank.csv
phase_q2_post_filter_score_rank.csv
phase_q2_feature_importance.csv
phase_q2_resource_audit.json
phase_q2_leakage_audit.json
phase_q2_forbidden_action_audit.json
phase_q2_training_log.txt
```

如训练失败，也必须输出失败 manifest、日志和停止原因。

## 7. Raw Score 与 Post-filter 要求

Q2 必须输出两个层次：

```text
raw_score_rank: 模型对同 split/date/instrument 的原始分数和排名
post_filter_score_rank: 使用与 fresh qlib control 相同 post-score filter 后的候选排名
```

post-score filter 不允许改变：

```text
tw_liquid_dyn as-of active instrument range
same-day price
>=60 history
trailing 60-day value top150
```

不得新增：

- 市场状态 gate；
- turnover rule；
- LTR rerank；
- extra liquidity filter；
- 人工白名单/黑名单；
- 收益导向的二次筛选。

## 8. PIT 与泄漏审计

Q2 必须复用 Q1 的 available_at join 结果，并再次审计：

```text
available_at <= signal_asof
trade_date <= signal_asof
```

必须证明：

- 没有用 validation/test 后信息训练；
- 没有用未来正交数据填补过去；
- 没有人工提前 available_at；
- 没有因正交特征缺失删样本或删股票；
- train/validation/test split 未变。

## 9. 必须证明的等式

执行报告必须明确证明：

```text
control_model_family == treatment_model_family
control_model_params == treatment_model_params
control_label == treatment_label
control_split == treatment_split
control_universe_policy == treatment_universe_policy
control_post_score_filter == treatment_post_score_filter
only_added_training_features == q1_approved_numeric_orthogonal_features_and_flags
```

## 10. 禁止事项

Q2 禁止：

- 引入 LTR；
- 训练 stacking 模型；
- 改 label；
- 改 split；
- 改 universe；
- 改模型家族；
- 改模型参数；
- 改 Alpha158；
- 改 provider；
- 改 post-score filter；
- 改 replay 规则；
- 因缺失正交特征删行、删股票或缩小窗口；
- 新增月营收 YoY、估值、其他 FinMind dataset、新技术指标或市场状态指标；
- 用训练窗口收益率证明策略优劣；
- 做策略回放结论；
- 改默认前端策略；
- 接 provider refresh / publish / accepted latest；
- 接 monitor / broker / orders / quick-trade；
- 发出任何真实交易建议、目标仓位、目标权重、收益承诺、胜率或上涨概率。

## 11. 停止条件

遇到以下任一情况必须停止并报告：

- OOM 后无法在 `4 -> 2 -> 1` 线程阶梯完成；
- 必须改模型参数才能跑通；
- 必须缩小 universe；
- 必须改变 split / label / feature family；
- 必须改变 provider；
- 必须改变 post-score filter；
- Q1 joined sample 无法用于 qlib 训练且没有只改接入方式的安全方案；
- feature join 或训练输入出现未来函数风险；
- 需要新增 Q1 之外的特征；
- 需要调用 LTR 或额外规则才能生成排名。

如果 feature importance 显示正交特征完全未进入、全部为常量或重要性为零，必须报告；这本身不一定阻塞 Q2，但会影响 Q3/Q4 结论。

## 12. 执行报告要求

必须输出：

```text
docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ2_ORTHOGONAL_FRESH_QLIB_TRAINING_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 做了什么；
- 使用 artifact；
- 输入/输出路径；
- 训练环境与线程阶梯；
- row count；
- 日期范围；
- symbol 覆盖；
- train/validation/test count；
- model family / params 对照；
- label / split / universe / post-score filter 对照；
- 最终训练特征数量；
- 新增正交特征数量；
- 被排除的非训练审计字段；
- raw score rank 产物路径；
- post-filter score rank 产物路径；
- feature importance summary；
- resource audit；
- PIT / leakage audit；
- forbidden action audit；
- 是否触发停止条件；
- 是否建议进入 Q3。

## 13. Gate

Q2 通过 gate：

```text
phase_q2_orthogonal_fresh_qlib_training_completed
```

只有在以下条件全部满足时，审查者才可允许进入 Q3：

- S2B control 训练合同未变；
- 模型家族和参数未变；
- label / split / universe / post-score filter 未变；
- 只新增 Q1 通过的正交数值特征与 flag；
- PIT / leakage 审计通过；
- raw score 与 post-filter score 产物完整；
- 没有引入 LTR 或额外规则；
- 没有触发前端、provider、accepted latest、monitor 或交易链路。

## 14. 给执行者的一句话

```text
请按 docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ2_ORTHOGONAL_FRESH_QLIB_TRAINING_WORK_CN.md 执行 Phase Q2：完整复刻原 S2B fresh qlib 的 LGBModel、模型参数、train/validation/test、provider、universe 和 post-score filter，只追加 Q1 通过的 PIT-safe 正交数值特征与 missing/delay flag 训练 Orthogonal Fresh Qlib，输出 raw score rank、post-filter score rank、feature importance、resource/PIT/leakage/forbidden action audit；不得改参数、改 split/label/universe、引入 LTR、增加规则、回放收益或触发前端/provider/accepted latest/monitor/交易链路。
```

## 15. 给审查者的一句话

```text
请按 docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ2_ORTHOGONAL_FRESH_QLIB_TRAINING_WORK_CN.md 审查执行者 Q2 报告，重点确认 S2B control 训练合同、LGBModel 参数、label/split/universe/post-score filter 完全未变，只新增 Q1 通过的正交数值特征与 flag，PIT/leakage 审计通过，raw/post-filter score 和 feature importance 产物完整，且没有引入 LTR、额外规则、收益回放或任何前端/provider/accepted latest/monitor/交易链路动作，并判断是否允许进入 Q3。
```
