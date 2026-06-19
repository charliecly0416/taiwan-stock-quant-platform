# Phase E0 工作文档：合同与可行性审计

生成日期：2026-06-15

## 1. 本阶段目标

本阶段只做一件事：

```text
审计 extended OOS qlib + orthogonal LTR 支线是否可执行：
qlib 只用 2018-2022 训练；
同一个 frozen qlib 为 2023-2026 生成 OOS score；
LTR 用 2023-2025 训练；
2026 作为 untouched test。
```

本阶段不训练 qlib、不训练 LTR、不调参、不回放。

## 2. 上游主线

必须遵循：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/EXTENDED_OOS_QLIB_ORTHOGONAL_LTR_MAINLINE_CN.md
```

本支线用于验证：

```text
LTR 训练数据从 1 年扩展到 3 年后，
正交 LTR 是否能在 frozen qlib top50 上形成更稳定增益。
```

## 3. 冻结时间合同

E0 必须冻结并审计：

```text
qlib train: 2018-01-01..2022-12-31
qlib frozen OOS score: 2023-01-01..2026-05-07
LTR train: 2023-01-01..2025-12-31
LTR untouched test: 2026-01-01..2026-05-07
```

硬性边界：

- 2023-2025 不得用于 qlib 训练；
- 2026 不得用于 qlib 训练、LTR 训练、调参或模型选择；
- 2023-2026 score 必须来自同一个 frozen qlib；
- 不得用多个 qlib 模型拼接 OOS score；
- 不得用 qlib 2018-2022 in-sample score 训练 LTR。

## 4. E0 执行范围

执行者应完成：

1. 定位台湾 qlib provider。
2. 定位原 S2B fresh qlib config / model params。
3. 审计 2018-2022 qlib 训练数据覆盖。
4. 审计 2023-2026 可打分日期与股票覆盖。
5. 审计 2023-2025 是否可形成每日 top50 LTR train。
6. 审计 2026 是否可形成每日 top50 untouched test。
7. 审计 O2 正交特征在 2023-2026 的 coverage 与 PIT available_at。
8. 审计 `relevance_10d_top_heavy` label 在 2023-2025 的可构造性。
9. 审计 2026 label 只可用于后续 audit，不可用于训练/调参/选择。
10. 输出 qlib split 计划。
11. 输出 LTR sample 计划。
12. 输出 feature schema 计划。
13. 输出 forbidden action audit。

## 5. 必须审计的输入

### Qlib provider / config

候选 provider：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
```

候选 S2B config / manifest：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_training_manifest.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_generated_qlib_config.yaml
```

### O2 正交特征

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/feature_dictionary.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/pit_leakage_audit.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/pit_lineage_audit.csv
```

### O4 LTR 合同

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv
```

## 6. E0 输出目录

建议输出到：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e0_contract_and_feasibility/
```

至少包含：

```text
phasee0_contract_manifest.json
phasee0_qlib_data_coverage.csv
phasee0_oos_score_feasibility_plan.csv
phasee0_top50_candidate_feasibility.csv
phasee0_o2_orthogonal_feature_coverage.csv
phasee0_label_feasibility_audit.csv
phasee0_feature_schema_plan.csv
phasee0_forbidden_action_audit.json
```

## 7. 执行报告要求

必须输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE0_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 做了什么；
- 使用 artifact；
- provider / config 来源；
- qlib train 数据覆盖；
- 2023-2026 OOS score 可行性；
- 2023-2025 LTR train top50 可行性；
- 2026 untouched test top50 可行性；
- O2 正交特征 PIT coverage；
- label 可行性；
- qlib 模型参数计划；
- LTR 模型参数计划；
- feature schema 计划；
- 是否需要调 qlib / LTR 参数；
- 是否需要改变 provider；
- 是否需要用多个 qlib 模型；
- 是否需要使用 2026 训练/选择；
- 是否触发停止条件；
- 是否建议进入 E1。

## 8. 停止条件

遇到以下任一情况必须停止并报告：

- 2018-2022 qlib 训练数据不足；
- 2023-2026 无法由同一个 qlib 模型打分；
- 2023-2025 无法形成足够 top50 LTR train；
- 2026 无法形成 top50 test；
- O2 正交特征无法 PIT-safe join；
- `relevance_10d_top_heavy` label 在 2023-2025 不可构造；
- 必须改变 label；
- 必须调 qlib 参数；
- 必须调 LTR 参数；
- 必须使用多个 qlib 模型拼接 score；
- 必须使用 2026 做训练、调参或模型选择；
- 必须触发 provider refresh / publish / accepted latest。

## 9. 禁止事项

E0 禁止：

- 训练 qlib；
- 训练 LTR；
- 调参；
- 回放；
- 改默认策略；
- 改前端/API；
- provider refresh / publish / accepted latest；
- monitor / broker / orders / quick-trade；
- 使用 2026 做训练、调参或选择；
- 新增 O2/O4 之外特征；
- 新增 filter / market gate / turnover rule；
- 输出真实买卖建议、目标仓位、目标权重、收益承诺、胜率或上涨概率。

## 10. Gate

E0 通过 gate：

```text
phase_e0_extended_oos_contract_feasible
```

只有在以下条件全部满足时，审查者才可允许进入 E1：

- 2018-2022 qlib 训练数据可用；
- 2023-2026 可作为同一个 frozen qlib 的 OOS score 区间；
- 2023-2025 可构造 LTR train；
- 2026 可作为 untouched test；
- O2 正交特征可 PIT-safe join；
- label 可构造；
- 不需要调参或改变 label；
- 不需要多个 qlib 模型；
- 不需要使用 2026 训练/选择；
- 未触发 provider/accepted latest/monitor/交易链路。

## 11. 给执行者的一句话

```text
请按 docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE0_CONTRACT_AND_FEASIBILITY_WORK_CN.md 执行 Phase E0：只做合同与可行性审计，冻结 qlib train=2018-2022、frozen qlib OOS score=2023-2026、LTR train=2023-2025、2026 untouched test，审计 provider/config、top50 coverage、O2 PIT 特征、label 和 feature schema；不得训练、调参、回放、使用 2026 训练/选择、引入多 qlib 模型或触发前端/provider/accepted latest/monitor/交易链路。
```

## 12. 给审查者的一句话

```text
请按 docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE0_CONTRACT_AND_FEASIBILITY_WORK_CN.md 审查 E0 报告，重点确认 2018-2022 qlib 训练、2023-2026 同一 frozen qlib OOS score、2023-2025 LTR train、2026 untouched test、O2 PIT-safe join 和禁止事项是否可行，并判断是否允许进入 E1。
```
