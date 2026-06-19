# Phase S1B2 审查意见与 Phase S1B2R Label 修复工作文档

生成日期：2026-06-14

## 1. 审查范围

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1M_REVIEW_AND_PHASES1B2_WORK_CN.md
```

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B2_LTR_SAMPLE_BUILD_EXECUTION_REPORT_CN.md
scripts/build_tw_ltr_s1b2_samples.py
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/
```

本轮只审查 S1B2 是否完成 split-aligned LTR 样本构建与 feature/label/leakage 审计，不审查任何 LTR 训练或策略回放效果。

## 2. 审查结论

结论：`暂不放行 S1B3，要求先做 Phase S1B2R 的 label bucket split-purity 修复。`

Gate：

```text
s1b2_requires_label_bucket_split_purity_repair_before_s1b3
```

理由：

1. S1B2 样本覆盖、score/rank 对齐、feature 白名单、forbidden feature 审计、只读边界整体合格。
2. 但 `scripts/build_tw_ltr_s1b2_samples.py` 使用全样本 `pd.qcut(sample["future_excess_return_rank_10d"], 5, ...)` 生成 `topk_forward_bucket` / `ltr_relevance_label`。
3. 这会让 validation/test 的未来标签分布参与 bucket 边界确定。即使它是 label 而不是 feature，也不符合本主线对 split purity / lookahead 的要求。
4. S1B2 报告中的 gate 写为 `s1b2_ltr_samples_pass_request_s1b3_ltr_training`，而上一轮审查文档要求的下一步是 `s1b3_training_policy_freeze`，不能直接进入训练。

因此：S1B2 不应直接进入训练。需要先做一个很窄的 S1B2R：修复 label bucket 生成方式、更新产物和报告，再审查是否进入 S1B3 training policy freeze。

## 3. 已通过部分

### 3.1 样本与 score/rank 对齐

只读一致性检查结果：

```text
score_rows: 308385
sample_rows: 308385
key_missing_from_scores: 0
score_keys_not_in_sample: 0
sample_duplicates: 0
input_label_overlap: []
missing_input_columns: []
missing_label_columns: []
split_counts:
  train_scored: 145921
  validation: 73078
  test: 89386
folds:
  TEST
  WF-2017
  WF-2018
  WF-2019
  WF-2020
  WF-VAL
```

审查判断：样本严格来自 S1B1 score/rank 的 `date/instrument`，没有多出或漏掉 key。

### 3.2 Split 覆盖

`phase_s1b2_split_summary.json`：

| split | date range | rows | sample complete |
| --- | --- | ---: | ---: |
| train_scored | `2017-01-03..2020-12-31` | 145921 | 141085 |
| validation | `2021-01-04..2022-12-30` | 73078 | 69812 |
| test | `2023-01-03..2025-06-30` | 89386 | 87345 |

审查判断：S1 train 仍明确为 `2017-2020 scored train`，没有错误声称覆盖完整 `2015-2020`。

### 3.3 Feature 与 forbidden audit

`phase_s1b2_feature_list.json` 显示 input feature 34 个，与既有白名单一致，并排除 `trend_score`。

`phase_s1b2_forbidden_feature_audit.csv` 显示：

```text
forbidden_feature_hits: []
label_input_overlap: []
trend_score: excluded
```

审查判断：未发现 future label、trend_score、正交数据、基本面数据或交易语义字段进入 input feature。

### 3.4 只读边界

`phase_s1b2_leakage_boundary_audit.json`：

```text
ltr_training_performed: false
portfolio_replay_performed: false
strategy_comparison_performed: false
provider_refresh_publish_performed: false
accepted_latest_switching_performed: false
monitor_or_trading_chain_touched: false
```

审查判断：本轮没有训练 LTR，没有组合回放，没有前端/API/provider/accepted latest/monitor/交易链路越权。

## 4. Findings

### High

1. `topk_forward_bucket` / `ltr_relevance_label` 的 bucket 边界由全样本 `pd.qcut` 生成，validation/test 的未来标签分布参与了训练标签定义。  
   位置：`scripts/build_tw_ltr_s1b2_samples.py` 中：

```text
sample["topk_forward_bucket"] = pd.qcut(sample["future_excess_return_rank_10d"], 5, labels=False, duplicates="drop")
sample["ltr_relevance_label"] = sample["topk_forward_bucket"]
```

这不是 feature 泄漏，但属于 label construction 的 split-purity 问题。必须修复后才能进入训练。

2. S1B2 gate 命名越过了审查节点：报告与 gate summary 写为 `request_s1b3_ltr_training`，但上一轮工作文档要求先进入 `S1B3 training policy freeze`。执行者不能直接请求训练。

### Medium

1. `last_unavailable_label_ranges` 的命名和解释不够准确。当前 train_scored 的不可得范围出现在 `2018-03-27..2018-04-27` 等中间日期，并非 split 尾段。执行者报告称“尾段”不准确。S1B2R 应改为 `unavailable_label_ranges` 或列出缺失原因摘要。
2. 后续训练前还需要明确 `sample_complete=true` 才能进入训练输入，不能把 feature 或 label 不完整行交给 LTR。

### Low

1. 本轮未出现 OOM，无需远端迁移。
2. `/lustre/...` 只出现在 S1B1 远端回传说明中，S1B2 样本构建使用本地现有 score 与 normalized 数据；不构成 provider 切换。

## 5. 台股只读安全边界审查

### Findings

未发现 broker、quick-trade、orders、target-position、target-weight、monitor write、provider publish/refresh、accepted latest switching。

### Network Audit

本轮为本地文件与脚本审查，未涉及前端/API/E2E，未要求 network audit。

### Text / Agent Semantics

报告中出现的训练、label、回放、买卖、仓位、收益等词均处于研究流程、禁止事项或历史模拟边界语境中；未形成真实交易建议、目标仓位、收益承诺、胜率或上涨概率承诺。

### Verdict

只读安全边界通过。

## 6. Phase S1B2R 工作文档：Label Bucket Split-Purity 修复

### 6.1 目标

只修复 S1B2 label bucket 的 split-purity 问题，并更新审计产物。

S1B2R 不训练 LTR，不跑回放，不做策略比较，不改 feature 白名单，不新增数据源。

### 6.2 必须修复

执行者必须把 `topk_forward_bucket` / `ltr_relevance_label` 改成不依赖 validation/test 分布的确定性规则。

推荐规则：

```text
future_excess_return_rank_10d <= 0.20 -> 0
0.20 < rank <= 0.40 -> 1
0.40 < rank <= 0.60 -> 2
0.60 < rank <= 0.80 -> 3
rank > 0.80 -> 4
NaN -> NaN
```

说明：

- `future_excess_return_rank_10d` 已经是同一日期横截面 percentile rank；
- 固定阈值不需要从全样本、validation 或 test 拟合；
- 不允许用 validation/test 分布重新学习 bucket 边界；
- 不允许基于后续训练或回放效果选择 label 规则。

### 6.3 必须补充审计

新增或更新：

```text
phase_s1b2_label_audit_summary.json
phase_s1b2_leakage_boundary_audit.json
phase_s1b2_gate_summary.json
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B2R_LABEL_BUCKET_REPAIR_EXECUTION_REPORT_CN.md
```

审计中必须明确：

```text
label_bucket_policy: fixed_percentile_thresholds
label_bucket_thresholds: [0.20, 0.40, 0.60, 0.80]
label_bucket_fit_on_all_splits: false
label_bucket_fit_on_validation_or_test: false
s1_test_feedback_used_for_label_bucket: false
```

同时修正不可得 label 范围表述：

- 不再把中间缺失日期称为“尾段”；
- 输出每个 split、每个 horizon 的 missing row count；
- 若缺失集中在少数日期或股票，给出简短原因判断，例如局部停牌、退市、价格未来段不足；
- 不要求补齐这些缺失行，只要求报告准确。

### 6.4 必须保持不变

以下内容不得改变：

```text
S1B1 score/rank input
split date contract
input feature list
feature derivation logic
forbidden feature list
normalized/TWII 本地数据来源
sample 只能来自 S1B1 score/rank date/instrument
```

### 6.5 验收标准

通过 gate：

```text
s1b2r_label_bucket_repair_pass_request_s1b3_training_policy_freeze
```

通过条件：

- 样本行数仍为 `308385`，且 date/instrument keys 与 S1B1 score 文件一致；
- duplicate date/instrument count 为 0；
- input feature 与 label-only 无重叠；
- forbidden feature hits 为空；
- `label_bucket_policy=fixed_percentile_thresholds`；
- `label_bucket_fit_on_all_splits=false`；
- `label_bucket_fit_on_validation_or_test=false`；
- `s1_test_feedback_used_for_label_bucket=false`；
- `ltr_training_performed=false`；
- `portfolio_replay_performed=false`；
- `provider_refresh_publish_performed=false`；
- `accepted_latest_switching_performed=false`；
- `monitor_or_trading_chain_touched=false`；
- 下一步 gate 指向 `S1B3 training policy freeze`，不是直接训练。

失败 gate：

```text
s1b2r_blocked_by_label_bucket_leakage
s1b2r_blocked_by_scope_violation
s1b2r_data_integrity_regression
```

### 6.6 禁止事项

- 不训练 LTR；
- 不训练 qlib；
- 不跑组合回放；
- 不比较策略收益；
- 不调参；
- 不新增 feature；
- 不新增数据源；
- 不联网；
- 不改前端/API；
- 不触发 provider refresh / publish；
- 不切换 accepted latest；
- 不触发 monitor config save / scan / alerts write；
- 不接 broker、orders、quick-trade；
- 不输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 7. 给执行者的一句话

请执行 Phase S1B2R：只把 `topk_forward_bucket` / `ltr_relevance_label` 从全样本 `pd.qcut` 改为固定 percentile 阈值 `[0.20,0.40,0.60,0.80]`，更新样本与 label/leakage/gate 审计，并把下一步 gate 指向 `S1B3 training policy freeze`；不得训练、不得回放、不得调参、不得新增数据源或触发前端/API/provider/accepted latest/monitor/交易链路。
