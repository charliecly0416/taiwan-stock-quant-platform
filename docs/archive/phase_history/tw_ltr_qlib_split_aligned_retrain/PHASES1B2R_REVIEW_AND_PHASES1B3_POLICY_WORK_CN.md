# Phase S1B2R 审查意见与 Phase S1B3 Training Policy Freeze 工作文档

生成日期：2026-06-14

## 1. 审查范围

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B2_REVIEW_AND_PHASES1B2R_LABEL_REPAIR_WORK_CN.md
```

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B2R_LABEL_BUCKET_REPAIR_EXECUTION_REPORT_CN.md
scripts/build_tw_ltr_s1b2_samples.py
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/
```

本轮只审查 S1B2R 是否修复 label bucket split-purity 问题，以及是否仍保持 S1B2 样本、feature、split、数据源和只读边界不变。

## 2. 审查结论

结论：`通过，允许进入 Phase S1B3 training policy freeze。`

Gate：

```text
s1b2r_pass_request_s1b3_training_policy_freeze
```

通过理由：

1. `topk_forward_bucket` / `ltr_relevance_label` 已从全样本 `pd.qcut` 改为固定 percentile 阈值 `[0.20, 0.40, 0.60, 0.80]`。
2. 脚本中未再发现 `qcut`。
3. 审计产物明确记录：

```text
label_bucket_policy = fixed_percentile_thresholds
label_bucket_fit_on_all_splits = false
label_bucket_fit_on_validation_or_test = false
s1_test_feedback_used_for_label_bucket = false
```

4. 样本行数、date/instrument key、feature list、split contract 没有回归。
5. 未训练 LTR，未回放，未调参，未新增数据源，未触发前端/API/provider/accepted latest/monitor/交易链路。

## 3. 核验证据

### 3.1 脚本实现

`scripts/build_tw_ltr_s1b2_samples.py`：

- 新增 `label_bucket_from_percentile`；
- 使用固定阈值生成 `topk_forward_bucket`；
- `ltr_relevance_label = topk_forward_bucket`；
- `rg` 未发现 `qcut` 残留。

### 3.2 产物一致性

只读一致性检查：

```text
score_rows: 308385
sample_rows: 308385
key_missing_from_scores: 0
score_keys_not_in_sample: 0
duplicates: 0
input_label_overlap: []
label_values: [0.0, 1.0, 2.0, 3.0, 4.0]
bucket_values: [0.0, 1.0, 2.0, 3.0, 4.0]
sample_complete_by_split:
  train_scored: 141085
  validation: 69812
  test: 87345
```

### 3.3 Gate 与边界

`phase_s1b2_gate_summary.json`：

```text
recommended_gate: s1b2r_label_bucket_repair_pass_request_s1b3_training_policy_freeze
forbidden_feature_hits: []
label_input_overlap: []
no_ltr_training: true
no_replay: true
no_strategy_comparison: true
no_provider_refresh_publish: true
no_accepted_latest_switching: true
no_monitor_or_trading_chain: true
```

`phase_s1b2_leakage_boundary_audit.json`：

```text
label_bucket_policy: fixed_percentile_thresholds
label_bucket_thresholds: [0.2, 0.4, 0.6, 0.8]
label_bucket_fit_on_all_splits: false
label_bucket_fit_on_validation_or_test: false
s1_test_feedback_used_for_label_bucket: false
```

## 4. Findings

### High

无阻断项。

### Medium

1. 下一阶段只能冻结训练政策，不能直接训练。S1B3 必须先明确模型、参数、sample_complete 过滤、validation 选择规则、test 禁用规则和产物清单。
2. 训练阶段必须只使用 `sample_complete=true` 的行；不能把 feature 或 label 不完整行交给 LTR。

### Low

1. `phase_s1b2_gate_summary.json` 的 `phase` 字段仍为 `phase_s1b2_ltr_sample_build`，但 gate 已指向 S1B2R 修复通过。该命名不影响实质审查，但后续报告应更精确标注当前 phase。
2. 本轮未出现 OOM，无需远端迁移。

## 5. 台股只读安全边界审查

### Findings

未发现 broker、quick-trade、orders、target-position、target-weight、monitor write、provider publish/refresh、accepted latest switching。

### Network Audit

本轮为本地文件与脚本审查，未涉及前端/API/E2E，未要求 network audit。

### Text / Agent Semantics

报告中的训练、label、回放、买卖、仓位、收益等词均处于研究流程、禁止事项或历史模拟边界语境中；未形成真实交易建议、目标仓位、收益承诺、胜率或上涨概率承诺。

### Verdict

只读安全边界通过。

## 6. Phase S1B3 工作文档：Training Policy Freeze

### 6.1 目标

Phase S1B3 只冻结 S1 split-aligned LTR 训练政策，不实际训练。

必须回答：

```text
下一轮如何在不触碰 test、不调参、不扩主线的情况下，训练 split-aligned LTR simple 与 turnover-controlled LTR？
```

S1B3 不训练 LTR，不跑回放，不做策略比较。

### 6.2 输入冻结

唯一 LTR 样本输入：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_ltr_samples.csv
```

唯一 schema / feature 输入：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_sample_schema.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_feature_list.json
```

训练输入必须过滤：

```text
sample_complete == true
```

Split 固定：

```text
train_scored: 2017-01-01..2020-12-31
validation:   2021-01-01..2022-12-31
test:         2023-01-01..2025-06-30
```

S1B3 必须强调：

- train_scored 不是完整 2015-2020；
- validation 只用于模型早停或固定候选选择；
- test 不能用于训练、早停、参数选择、label 选择或阈值选择。

### 6.3 训练候选冻结

S1B3 只能冻结以下候选，不实际运行：

1. `split_aligned_ltr_simple`
2. `split_aligned_ltr_turnover_controlled`

两者暂时按同等级策略处理，不在 S1B3 做高低判断。

不得新增：

- 新模型 family；
- 新 label horizon；
- 新 feature；
- 新正交/基本面/联网数据；
- 新策略规则；
- 新 provider 或 accepted latest；
- 前端/API/monitor/交易链路。

### 6.4 模型与参数冻结

执行者必须在 S1B3 报告中冻结训练参数表。

建议沿用既有 LTR Phase1C / LambdaMART 口径，例如：

```text
model_family: LightGBM LambdaMART / LGBMRanker
objective: lambdarank
label: ltr_relevance_label
group: date
features: phase_s1b2_feature_list.json input_features
train rows: train_scored & sample_complete
validation rows: validation & sample_complete
test rows: test & sample_complete, only for later evaluation
```

如果存在多个既有 LTR 参数版本，S1B3 只能选一个“既有已冻结/最保守”的版本，不能做参数搜索。若执行者认为无法确定，应停下来报告，不得自行试参。

### 6.5 Validation 使用规则

允许：

- 早停；
- 在预先冻结的 simple / turnover-controlled 两个候选之间记录 validation diagnostics；
- 用 validation 检查训练是否失败或明显退化。

禁止：

- 根据 test 结果选择模型；
- 反复修改参数追 validation；
- 根据 validation/test 表现新增 feature、改 label、改 universe、改 split；
- 在 S1B3 训练或回放。

### 6.6 Turnover-Controlled 策略冻结

S1B3 只能冻结 turnover-controlled 的后续训练/打分政策，不跑组合回放。

必须明确：

- turnover-controlled 是后续在 score 使用层或 rerank 层的约束，不应改变训练 label；
- 不得在 S1B3 根据收益、回撤、动作次数选择阈值；
- 若需要阈值，必须来自既有 Phase1C 已冻结规则，或在 S1B3 明确列为“待下一轮只读评估使用的固定候选”，不能在本轮试错。

### 6.7 必须输出

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B3_TRAINING_POLICY_FREEZE_EXECUTION_REPORT_CN.md
```

建议产物：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_training_policy.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_feature_label_contract.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_split_usage_contract.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_forbidden_action_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_gate_summary.json
```

### 6.8 验收 Gate

通过 gate：

```text
s1b3_training_policy_freeze_pass_request_s1b4_ltr_training
```

通过条件：

- 训练输入固定为 S1B2R 样本；
- 明确 `sample_complete=true` 过滤；
- train / validation / test 使用边界清楚；
- simple 与 turnover-controlled 候选定义清楚；
- 参数表冻结，不含参数搜索；
- no LTR training；
- no replay；
- no strategy comparison；
- no frontend/API；
- no provider refresh/publish；
- no accepted latest switching；
- no monitor/trading chain；
- no buy/sell/position/return promise/probability semantics。

失败 gate：

```text
s1b3_policy_incomplete
s1b3_blocked_by_parameter_or_strategy_tradeoff
s1b3_blocked_by_scope_violation
```

如果需要用户判断参数 tradeoff，必须停止，不得自行训练。

### 6.9 禁止事项

- 不训练 LTR；
- 不训练 qlib；
- 不跑组合回放；
- 不比较策略收益；
- 不调参；
- 不新增 feature；
- 不新增 label；
- 不新增数据源；
- 不联网；
- 不改前端/API；
- 不触发 provider refresh / publish；
- 不切换 accepted latest；
- 不触发 monitor config save / scan / alerts write；
- 不接 broker、orders、quick-trade；
- 不输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 7. 给执行者的一句话

请执行 Phase S1B3：只冻结基于 S1B2R 样本的 LTR simple 与 turnover-controlled LTR 训练政策、参数表、`sample_complete=true` 过滤、train/validation/test 使用边界和禁止事项；不得实际训练、不得回放、不得调参、不得新增数据源或触发前端/API/provider/accepted latest/monitor/交易链路，完成后提交 `PHASES1B3_TRAINING_POLICY_FREEZE_EXECUTION_REPORT_CN.md` 等待审查。
