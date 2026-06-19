# Phase E3 工作文档：Orthogonal LTR 训练

生成日期：2026-06-15

## 1. 本阶段目标

本阶段只做一件事：

```text
使用 E2 通过审计的 2023-2025 宽候选 row-aligned 样本，
沿用 O4 的 LGBMRanker 模型家族、超参数、label 和 feature whitelist，
训练一个 extended OOS qlib + orthogonal LTR treatment。
```

本阶段可以训练 LTR，但不得训练 qlib、不得调参、不得回放。

## 2. 上游 Gate

必须满足：

```text
phase_e0_extended_oos_contract_feasible
phase_e1_frozen_qlib_oos_score_completed
phase_e1r_candidate_coverage_scope_repaired
phase_e2_extended_oos_ltr_sample_passed
```

必须引用：

- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE0_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE1_FROZEN_QLIB_TRAINING_AND_OOS_SCORE_EXECUTION_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE1R_CANDIDATE_COVERAGE_SCOPE_REPAIR_EXECUTION_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE2_ROW_ALIGNED_SAMPLE_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_sample_manifest.json`

## 3. 冻结训练合同

LTR 训练必须使用：

```text
train sample: data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_train_sample_2023_2025.csv
test score sample: data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_test_sample_2026.csv
train period: 2023-01-01..2025-12-31
untouched test period: 2026-01-01..2026-05-07
training_candidate_scope: old O4-style broad candidate rows
future replay boundary: qlib top50 rerank only
label: relevance_10d_top_heavy
feature whitelist: E2 feature_schema / O4 whitelist
```

2026 样本只能用于打分与 audit，不得用于训练、调参、early stopping、模型选择或阈值选择。

## 4. 模型合同

模型家族与超参数必须沿用 O4：

```text
model_type: LightGBM.LGBMRanker
objective: lambdarank
metric: ndcg
boosting_type: gbdt
num_leaves: 31
learning_rate: 0.03
n_estimators: 120
min_child_samples: 40
random_state: 42
n_jobs: 2
verbose: -1
```

不得改模型家族、不得调参、不得训练多个版本挑最好。

## 5. 允许输入特征

只能使用 E2 `phasee2_feature_schema.csv` 中 status 为 `training_feature` 的 78 个特征：

- qlib score/rank 衍生特征；
- top10 / top30 / top50 flag；
- O4 已冻结技术/市场状态特征；
- O2 PIT-safe 法人筹码与融资融券正交特征；
- missing / delay flag。

不得新增 O2/O4 之外特征族。

不得使用以下字段作为训练特征：

- date / instrument / split；
- 2026 label；
- future return；
- future excess return；
- realized PnL；
- replay action；
- provider / accepted latest / monitor 字段；
- lineage path / raw snapshot path / free-text reason；
- 任何非 E2 whitelist 字段。

## 6. Group / Query 口径

LTR group 必须按交易日构造：

```text
group = E2 broad candidate rows per date
```

不能按 top50 group 构造。

必须输出 group audit：

- train date count；
- train row count；
- train group size min/median/max；
- train median daily max rank；
- test date count；
- test row count；
- test group size min/median/max；
- test median daily max rank；
- 是否存在空 group；
- 是否存在 top50-only group；
- 是否存在 group 被 full_market_top150_intersection 压缩。

参考 E2 预期：

```text
train rows: 107408, daily 147/149/149
test rows: 11822, daily 149/150/150
```

## 7. E3 执行范围

执行者应完成：

1. 读取 E2 manifest、train sample、test sample、feature schema。
2. 验证 train 只含 2023-2025 rows，test 只含 2026 rows。
3. 验证训练样本是宽候选集合，不是 top50-only。
4. 验证 qlib score provenance 仍为同一个 E1 frozen qlib artifact。
5. 验证 2026 label 未进入训练、调参或模型选择。
6. 使用 2023-2025 train sample 和 `relevance_10d_top_heavy` 训练一个 LTR treatment。
7. 用训练好的 treatment 对 2023-2025 train 与 2026 test 输出 row score / rank。
8. 输出 rank metrics：
   - 2023-2025 train；
   - 2026 test audit only。
9. 输出 feature importance。
10. 输出 training log。
11. 输出 model artifact。
12. 输出 forbidden action audit。

## 8. 输出目录

建议输出到：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/
```

至少包含：

```text
phasee3_training_manifest.json
phasee3_ltr_model.pkl
phasee3_train_row_scores.csv
phasee3_test_row_scores_2026.csv
phasee3_feature_importance.csv
phasee3_rank_metrics.csv
phasee3_group_audit.csv
phasee3_training_log.txt
phasee3_forbidden_action_audit.json
```

## 9. 执行报告要求

必须输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE3_ORTHOGONAL_LTR_TRAINING_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 做了什么；
- 使用 artifact；
- 输入/输出路径；
- train/test 日期范围；
- train/test row count；
- group size min/median/max；
- 是否 broad candidate training；
- 是否 top50-only；
- model family / params 对照 O4；
- label 对照 O4 / Phase1C；
- feature count / feature hash；
- 2026 是否未用于训练/调参/选择；
- qlib score provenance；
- feature importance summary；
- rank metrics；
- 是否训练多个版本；
- 是否调参；
- 是否回放；
- 是否触发 provider/accepted latest/monitor/交易链路；
- 是否建议进入 E4。

## 10. 停止条件

遇到以下任一情况必须停止并报告：

- 必须调参才能跑通；
- 必须改模型家族或超参数；
- 必须改 split 或 label；
- 必须使用 2026 做训练、调参或选择；
- 样本被错误压缩为 top50-only group；
- group size 明显偏离 E2 宽候选合同；
- feature importance 全零或明显异常；
- rank metrics 明显异常；
- 需要新增 O2/O4 之外特征；
- 需要使用 qlib 2018-2022 in-sample score；
- 需要引入 walk-forward 或多模型 score。

如果只是 2026 rank metrics 不好，不得自行调参或改窗口；应如实报告，留给 E4 replay 和 E5 决策。

## 11. 禁止事项

E3 禁止：

- 训练 qlib；
- 调 qlib 参数；
- 调 LTR 参数；
- 训练多个 LTR 版本挑最好；
- 改模型家族；
- 改 label；
- 改 split；
- 使用 2026 label 做训练、调参或模型选择；
- top50-only 训练；
- 使用 full_market_top150 intersection 重新压缩训练样本；
- 使用 qlib 2018-2022 in-sample score；
- 引入 walk-forward OOS 或多模型 score；
- 新增月营收、估值或其他数据源；
- 新增 filter / market gate / turnover rule；
- 回放；
- 改 provider / accepted latest；
- 改前端/API；
- 触发 monitor / broker / orders / quick-trade；
- 输出真实买卖建议、目标仓位、目标权重、收益承诺、胜率或上涨概率。

## 12. Gate

E3 通过 gate：

```text
phase_e3_extended_oos_ltr_trained
```

只有在以下条件全部满足时，审查者才可允许进入 E4：

- 只训练了一个 treatment；
- 模型家族和参数完全沿用 O4；
- label 沿用 `relevance_10d_top_heavy`；
- train 只来自 2023-2025；
- 训练 group 是宽候选集合，不是 top50-only；
- 2026 未用于训练、调参或选择；
- feature whitelist 未变；
- group audit 正常；
- feature importance / rank metrics 无阻断异常；
- 未回放；
- 未触发 provider/accepted latest/monitor/交易链路。

## 13. 给执行者的一句话

```text
请按 docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE3_ORTHOGONAL_LTR_TRAINING_WORK_CN.md 执行 Phase E3：只用 E2 通过审计的 2023-2025 宽候选 row-aligned 样本训练一个 extended OOS qlib + orthogonal LTR treatment，模型家族、超参数、label 和 feature whitelist 必须沿用 O4；2026 样本只能打分和 audit，不得用于训练、调参或选择；group 必须按宽候选每日 rows 构造，不得 top50-only；输出 model artifact、2023-2025/2026 row scores、feature importance、rank metrics、group audit、training log 和 forbidden action audit；不得训练 qlib、调参、训练多个版本、回放或触发 provider/accepted latest/monitor/交易链路。
```

## 14. 给审查者的一句话

```text
请按 docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE3_ORTHOGONAL_LTR_TRAINING_WORK_CN.md 审查 E3 报告，重点确认只训练一个 treatment、模型参数沿用 O4、train 只来自 2023-2025、训练 group 为宽候选而非 top50-only、2026 未参与训练/调参/选择、feature whitelist 未变、没有回放或额外规则，并判断是否允许进入 E4。
```
