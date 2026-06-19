# Phase C1 工作文档：Row-aligned LTR 样本构建

生成日期：2026-06-15

## 1. 本阶段目标

本阶段只做一件事：

```text
基于 frozen fresh qlib 的 2025/2026 OOS score，
构建 clean stacking 的 LTR row-aligned 样本：
2025 作为 LTR train，2026 作为 untouched test。
```

本阶段不训练 qlib、不训练 LTR、不回放、不调参。

## 2. 上游 Gate

必须满足：

```text
phase_c0_clean_stacking_contract_feasible
```

必须引用：

- `docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/FROZEN_FRESH_QLIB_ORTHOGONAL_LTR_CLEAN_MAINLINE_CN.md`
- `docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC0_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c0_contract_and_feasibility/phasec0_contract_manifest.json`

## 3. 冻结合同

必须保持：

```text
fresh qlib model: frozen S2B fresh qlib
fresh qlib train end: 2024-12-31
LTR train: 2025-01-01..2025-12-31
LTR test: 2026-01-01..2026-05-07
preserve_scope: top50_only
label: relevance_10d_top_heavy
model family / params for later C2: O4 frozen LGBMRanker / lambdarank
```

硬性要求：

```text
train rows only from 2025
test rows only from 2026
no 2026 label used in training
no qlib in-sample period used for LTR training
same frozen fresh qlib score source for 2025 and 2026
```

## 4. 允许输入

### Frozen Fresh Qlib score

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv
```

只允许使用 2025/2026 区间，且必须来自同一个 frozen fresh qlib 模型。

### O2 PIT-safe 正交特征

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/feature_dictionary.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/pit_leakage_audit.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/pit_lineage_audit.csv
```

### O4 feature whitelist / config

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json
```

## 5. 允许特征

LTR 输入允许包含：

- `qlib_score_raw`
- `qlib_rank`
- `qlib_score_percentile_by_date`
- `qlib_score_zscore_by_date`
- rank change；
- top10 / top30 / top50 flag；
- O4 已冻结的技术/市场状态特征；
- O2 已通过 PIT 审计的法人筹码与融资融券正交特征；
- 对应 missing / delay flag。

不得新增 O4/O2 之外的数据源或特征族。

## 6. C1 执行范围

执行者应完成：

1. 读取 C0 manifest 并确认 gate。
2. 读取 frozen fresh qlib 2025/2026 post-filter score。
3. 只保留 `preserve_scope = top50_only` 所需样本。
4. 生成 qlib score 衍生特征：
   - `qlib_score_raw`
   - `qlib_rank`
   - `qlib_score_percentile_by_date`
   - `qlib_score_zscore_by_date`
   - rank change / top10 / top30 / top50 flag
5. 拼接 O4 已冻结技术/市场状态特征。
6. 按真实 `available_at <= signal_asof` 拼接 O2 正交特征。
7. 构造 `relevance_10d_top_heavy` label。
8. 明确 2025 label 可用于训练。
9. 明确 2026 label 只可用于 audit / rank metric，不得用于训练、调参或选择。
10. 输出 row alignment audit。
11. 输出 PIT leakage audit。
12. 输出 missing report。
13. 输出 feature schema diff / final feature list。
14. 输出 forbidden action audit。

## 7. PIT 与 Score Provenance

必须证明：

```text
all LTR train rows are 2025 and after fresh qlib train end
all LTR test rows are 2026 and after fresh qlib train end
all qlib scores come from the same frozen fresh qlib artifact
no qlib 2017..2024 in-sample score used for LTR train
no walk-forward OOS or multi-model score introduced
O2 available_at <= signal_asof
O2 trade_date <= signal_asof
```

不得人工提前 available_at。

## 8. 输出目录

建议输出到：

```text
data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/
```

至少包含：

```text
phasec1_sample_manifest.json
phasec1_ltr_train_sample_2025.csv
phasec1_ltr_test_sample_2026.csv
phasec1_feature_schema.csv
phasec1_row_alignment_audit.csv
phasec1_score_provenance_audit.csv
phasec1_pit_leakage_audit.csv
phasec1_missing_report.csv
phasec1_label_audit.csv
phasec1_forbidden_action_audit.json
```

## 9. 执行报告要求

必须输出：

```text
docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC1_ROW_ALIGNED_SAMPLE_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 做了什么；
- 使用 artifact；
- 输入/输出路径；
- train/test 日期范围；
- train/test row count；
- 每日 top50 覆盖；
- feature count / schema；
- label 可用性；
- 2026 label 是否未用于训练；
- score provenance audit；
- PIT leakage audit；
- missing report；
- 是否使用 qlib in-sample score；
- 是否引入 walk-forward / 多模型 score；
- 是否新增 O4/O2 之外特征；
- 是否训练、调参或回放；
- 是否触发 frontend/API/provider/accepted latest/monitor/交易链路；
- 是否触发停止条件；
- 是否建议进入 C2。

## 10. 停止条件

遇到以下任一情况必须停止并报告：

- 2025 fresh qlib OOS score 不完整，无法每日形成 top50；
- 2026 fresh qlib OOS score 不完整，无法每日形成 top50；
- 2025 label 不可构造；
- O2 正交特征无法 PIT-safe join；
- 必须使用 qlib 2017..2024 in-sample score；
- 必须引入 walk-forward OOS 或多模型 qlib score；
- 必须改 label；
- 必须改 split；
- 必须新增 O4/O2 之外数据源或特征族；
- 必须训练模型才能判断样本是否可用。

如发现样本不足、label 缺失或 score 覆盖不足，不得自行改窗口到 2024 或扩到 qlib 训练期。

## 11. 禁止事项

C1 禁止：

- 训练 qlib；
- 训练 LTR；
- 调参；
- 回放；
- 使用 qlib 2017..2024 in-sample score 训练 LTR；
- 使用不同 qlib 模型拼接 OOS score；
- 使用 2026 label 做训练、调参或模型选择；
- 改 label；
- 改 split；
- 新增月营收、估值或其他数据源；
- 新增 filter / market gate / turnover rule；
- 改 provider / accepted latest；
- 改前端/API；
- 触发 monitor / broker / orders / quick-trade；
- 输出真实买卖建议、目标仓位、目标权重、收益承诺、胜率或上涨概率。

## 12. Gate

C1 通过 gate：

```text
phase_c1_clean_stacking_sample_passed
```

只有在以下条件全部满足时，审查者才可允许进入 C2：

- train rows only from 2025；
- test rows only from 2026；
- 2025/2026 score 均来自同一个 frozen fresh qlib OOS artifact；
- 每日 top50 coverage 完整；
- `relevance_10d_top_heavy` label 可构造；
- 2026 label 未用于训练、调参或选择；
- O2 正交特征 PIT-safe join；
- 未引入 qlib in-sample score；
- 未引入 walk-forward / 多模型 score；
- 未新增 O4/O2 之外特征；
- 未训练、调参或回放；
- 未触发前端/provider/accepted latest/monitor/交易链路。

## 13. 给执行者的一句话

```text
请按 docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC1_ROW_ALIGNED_SAMPLE_WORK_CN.md 执行 Phase C1：基于同一个 frozen fresh qlib 的 2025/2026 OOS top50 score 构建 LTR row-aligned 样本，2025 只能作为 train、2026 只能作为 untouched test；拼接 O4 冻结特征与 O2 PIT-safe 正交特征，构造 relevance_10d_top_heavy label，并输出 row alignment、score provenance、PIT、missing、label 和 forbidden action 审计；不得训练、调参、回放、使用 qlib 训练期 in-sample score、引入 walk-forward/多模型 score、改 split/label 或触发前端/provider/accepted latest/monitor/交易链路。
```

## 14. 给审查者的一句话

```text
请按 docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC1_ROW_ALIGNED_SAMPLE_WORK_CN.md 审查执行者 C1 报告，重点确认 train 只来自 2025、test 只来自 2026、score 全部来自同一个 frozen fresh qlib OOS artifact、2026 label 未用于训练、O2 join PIT-safe、没有 qlib in-sample score 或 walk-forward/多模型 score、没有训练/调参/回放，并判断是否允许进入 C2。
```
