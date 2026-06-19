# Phase C2 工作文档：Orthogonal LTR 训练

生成日期：2026-06-15

## 1. 本阶段目标

本阶段只做一件事：

```text
使用 C1 通过审计的 2025 row-aligned 样本，
沿用 O4 的 LGBMRanker 模型家族、超参数和 label，
训练一个 frozen fresh qlib + orthogonal LTR treatment。
```

本阶段可以训练 LTR，但不得训练 qlib、不得调参、不得回放。

## 2. 上游 Gate

必须满足：

```text
phase_c0_clean_stacking_contract_feasible
phase_c1_clean_stacking_sample_passed
```

必须引用：

- `docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/FROZEN_FRESH_QLIB_ORTHOGONAL_LTR_CLEAN_MAINLINE_CN.md`
- `docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC0_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md`
- `docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC1_ROW_ALIGNED_SAMPLE_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_sample_manifest.json`

## 3. 冻结训练合同

LTR 训练必须严格使用：

```text
train sample: data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_ltr_train_sample_2025.csv
test score sample: data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_ltr_test_sample_2026.csv
train period: 2025-01-01..2025-12-31
untouched test period: 2026-01-01..2026-05-07
preserve_scope: top50_only
label: relevance_10d_top_heavy
feature whitelist: C1 feature_schema / O4 whitelist
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

只能使用 C1 `phasec1_feature_schema.csv` 中 status 为 `training_feature` 的 78 个特征：

- qlib score/rank 衍生特征；
- O4 已冻结技术/市场状态特征；
- O2 PIT-safe 法人筹码与融资融券正交特征；
- missing / delay flag。

不得新增 O4/O2 之外特征族。

不得使用以下字段作为训练特征：

- date / instrument / split；
- 2026 label；
- future return；
- realized PnL；
- replay action；
- provider / accepted latest / monitor 字段；
- lineage path / raw snapshot path / free-text reason；
- 任何非 C1 whitelist 字段。

## 6. C2 执行范围

执行者应完成：

1. 读取 C1 manifest、train sample、test sample、feature schema。
2. 验证 train 只含 2025 rows，test 只含 2026 rows。
3. 验证 qlib score provenance 仍为同一个 frozen fresh qlib artifact。
4. 验证 2026 label 未进入训练、调参或模型选择。
5. 使用 2025 train sample 和 `relevance_10d_top_heavy` 训练一个 LTR treatment。
6. 用训练好的 treatment 对 2025 train 与 2026 test 输出 row score / rank。
7. 输出 rank metrics：
   - 2025 train；
   - 2026 test audit only。
8. 输出 feature importance。
9. 输出 training log。
10. 输出 model artifact。
11. 输出 forbidden action audit。

## 7. Group / Query 口径

LTR group 必须按交易日构造：

```text
group = daily top50 rows per date
```

必须输出 group audit：

- train date count；
- train group size min/median/max；
- test date count；
- test group size min/median/max；
- 是否存在空 group；
- 是否存在非 top50 group。

## 8. 输出目录

建议输出到：

```text
data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c2_orthogonal_ltr_training/
```

至少包含：

```text
phasec2_training_manifest.json
phasec2_ltr_model.pkl
phasec2_train_row_scores.csv
phasec2_test_row_scores_2026.csv
phasec2_feature_importance.csv
phasec2_rank_metrics.csv
phasec2_group_audit.csv
phasec2_training_log.txt
phasec2_forbidden_action_audit.json
```

## 9. 执行报告要求

必须输出：

```text
docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC2_ORTHOGONAL_LTR_TRAINING_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 做了什么；
- 使用 artifact；
- 输入/输出路径；
- train/test 日期范围；
- train/test row count；
- model family / params 对照 O4；
- label 对照 O4 / Phase1C；
- feature count / feature hash；
- group audit；
- 2026 是否未用于训练/调参/选择；
- qlib score provenance；
- feature importance summary；
- rank metrics；
- 是否训练多个版本；
- 是否调参；
- 是否回放；
- 是否触发 frontend/API/provider/accepted latest/monitor/交易链路；
- 是否触发停止条件；
- 是否建议进入 C3。

## 10. 停止条件

遇到以下任一情况必须停止并报告：

- 必须调参才能跑通；
- 必须改模型家族或超参数；
- 必须改 split 或 label；
- 必须使用 2026 做训练、调参或选择；
- 训练样本过少导致模型无意义；
- daily group 缺失或 group size 明显异常；
- feature importance 全零或明显异常；
- rank metrics 明显异常；
- 需要新增 O4/O2 之外特征；
- 需要使用 qlib 2017..2024 in-sample score；
- 需要引入 walk-forward 或多模型 score。

如果只是 2026 rank metrics 不好，不得自行调参或改窗口；应如实报告并进入 C3 或由审查者决定是否收口。

## 11. 禁止事项

C2 禁止：

- 训练 qlib；
- 调 qlib 参数；
- 调 LTR 参数；
- 训练多个 LTR 版本挑最好；
- 改模型家族；
- 改 label；
- 改 split；
- 使用 2026 label 做训练、调参或模型选择；
- 使用 qlib 2017..2024 in-sample score；
- 引入 walk-forward OOS 或多模型 score；
- 新增月营收、估值或其他数据源；
- 新增 filter / market gate / turnover rule；
- 回放；
- 改 provider / accepted latest；
- 改前端/API；
- 触发 monitor / broker / orders / quick-trade；
- 输出真实买卖建议、目标仓位、目标权重、收益承诺、胜率或上涨概率。

## 12. Gate

C2 通过 gate：

```text
phase_c2_clean_stacking_ltr_trained
```

只有在以下条件全部满足时，审查者才可允许进入 C3：

- 只训练了一个 treatment；
- 模型家族和参数完全沿用 O4；
- label 沿用 `relevance_10d_top_heavy`；
- train 只来自 2025；
- 2026 未用于训练、调参或选择；
- feature whitelist 未变；
- group audit 正常；
- feature importance / rank metrics 无阻断异常；
- 未回放；
- 未触发前端/provider/accepted latest/monitor/交易链路。

## 13. 给执行者的一句话

```text
请按 docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC2_ORTHOGONAL_LTR_TRAINING_WORK_CN.md 执行 Phase C2：只用 C1 通过审计的 2025 top50 row-aligned 样本训练一个 frozen fresh qlib + orthogonal LTR treatment，模型家族、超参数、label 和 feature whitelist 必须沿用 O4；2026 样本只能打分和 audit，不得用于训练、调参或选择；输出 model artifact、2025/2026 row scores、feature importance、rank metrics、group audit、training log 和 forbidden action audit；不得训练 qlib、调参、训练多个版本、回放、引入 qlib in-sample score/walk-forward/多模型 score 或触发前端/provider/accepted latest/monitor/交易链路。
```

## 14. 给审查者的一句话

```text
请按 docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC2_ORTHOGONAL_LTR_TRAINING_WORK_CN.md 审查执行者 C2 报告，重点确认只训练一个 treatment、模型参数沿用 O4、train 只来自 2025、2026 未参与训练/调参/选择、feature whitelist 未变、group/rank/importance 正常、没有回放或额外规则，并判断是否允许进入 C3。
```
