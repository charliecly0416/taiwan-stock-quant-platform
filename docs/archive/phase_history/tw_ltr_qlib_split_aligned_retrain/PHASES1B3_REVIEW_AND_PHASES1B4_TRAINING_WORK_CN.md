# Phase S1B3 审查意见与 Phase S1B4 LTR Training 工作文档

生成日期：2026-06-14

## 1. 审查范围

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B2R_REVIEW_AND_PHASES1B3_POLICY_WORK_CN.md
```

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B3_TRAINING_POLICY_FREEZE_EXECUTION_REPORT_CN.md
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/
```

本轮只审查 S1B3 是否完成训练政策冻结，不审查任何训练结果或策略回放结果。

## 2. 审查结论

结论：`通过，允许进入 Phase S1B4 LTR training。`

Gate：

```text
s1b3_pass_request_s1b4_ltr_training
```

通过理由：

1. S1B3 只冻结训练政策，没有实际训练、回放、调参或策略比较。
2. 唯一输入已冻结为 S1B2R 样本、schema、feature list。
3. 明确要求训练输入过滤 `sample_complete == true`。
4. train / validation / test 使用边界清楚：
   - train_scored：训练拟合；
   - validation：固定诊断，不做参数搜索；
   - test：后续单次 holdout 评估，不用于训练、早停、候选选择或参数选择。
5. 参数表冻结为既有 `scripts/train_tw_ltr_phase1_lambdamart.py` 的保守 LambdaMART 口径，未新增参数搜索。
6. simple 与 turnover-controlled 被定义为同一训练分数来源；turnover-controlled 只允许后续在 score 使用层或 rerank 层增加约束，不改变 label 或训练模型。

## 3. 核验证据

### 3.1 参数冻结

`phase_s1b3_training_policy.json`：

```text
model_family: LightGBM.LGBMRanker
objective: lambdarank
metric: ndcg
group_key: date
label_column: ltr_relevance_label
n_estimators: 120
learning_rate: 0.05
num_leaves: 31
min_child_samples: 20
random_state: 42
n_jobs: 2
early_stopping_enabled: false
parameter_search: false
```

抽查 `scripts/train_tw_ltr_phase1_lambdamart.py`，上述参数与既有脚本一致。

### 3.2 Feature / Label 合同

`phase_s1b3_feature_label_contract.json`：

- feature columns 来自 `phase_s1b2_feature_list.json`；
- training label 为 `ltr_relevance_label`；
- label bucket policy 为 fixed percentile thresholds；
- training row filter 包含 `sample_complete == true`；
- forbidden training inputs 包含所有 future return / future excess return / future rank / `topk_forward_bucket`。

### 3.3 Split 使用边界

`phase_s1b3_split_usage_contract.json`：

| split | 用途 |
| --- | --- |
| train_scored | `fit_only` |
| validation | `fixed_eval_diagnostics_only` |
| test | `holdout_only_after_training` |

审查判断：边界符合 S1 split-aligned 公平验证要求。

## 4. Findings

### High

无阻断项。

### Medium

1. S1B4 是第一轮实际 LTR 训练，必须严格一次性执行冻结参数；如果训练失败或 OOM，应停止报告，不得自行改参数、减数据、换模型或迁移远端。
2. S1B4 可以生成 train/validation/test 的 LTR score/rank 作为一次性产物，但不得用 validation/test 结果反向选择参数、feature、label、阈值或候选。
3. S1B4 不得把 `split_aligned_ltr_simple` 与 `split_aligned_ltr_turnover_controlled` 解释成两个不同训练模型；两者共用同一个 LTR score，turnover-controlled 只能留待后续使用层处理。

### Low

1. `created_at` 固定为 `2026-06-14T00:00:00+00:00`，不影响合同实质。
2. 当前未发现 S1B4 训练产物，符合 S1B3 “freeze only” 范围。

## 5. 台股只读安全边界审查

### Findings

未发现 broker、quick-trade、orders、target-position、target-weight、monitor write、provider publish/refresh、accepted latest switching。

### Network Audit

本轮为本地文件与报告审查，未涉及前端/API/E2E，未要求 network audit。

### Text / Agent Semantics

报告中的训练、回放、买卖、仓位、收益等词均处于研究流程、禁止事项或历史模拟边界语境中；未形成真实交易建议、目标仓位、收益承诺、胜率或上涨概率承诺。

### Verdict

只读安全边界通过。

## 6. Phase S1B4 工作文档：Split-Aligned LTR Training

### 6.1 目标

Phase S1B4 只做：

```text
按 S1B3 冻结政策训练一个 split-aligned LTR common model，并生成一次性 LTR score/rank 与训练诊断产物。
```

S1B4 不做组合回放，不做收益比较，不决定默认策略，不进入前端/API。

### 6.2 输入

必须使用：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_ltr_samples.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_sample_schema.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_feature_list.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_training_policy.json
```

训练前必须过滤：

```text
sample_complete == true
```

Split 使用：

```text
train_scored: fit only
validation: fixed diagnostics only
test: one-pass holdout score/evaluation only, no feedback
```

### 6.3 冻结训练规格

必须严格使用 S1B3 参数：

```text
LightGBM.LGBMRanker
objective = lambdarank
metric = ndcg
group_key = date
label = ltr_relevance_label
n_estimators = 120
learning_rate = 0.05
num_leaves = 31
min_child_samples = 20
random_state = 42
n_jobs = 2
eval_at = [10, 30, 50]
early_stopping_enabled = false
parameter_search = false
```

不得改参数。如果本机 OOM 或训练失败，执行者必须停止并报告；由用户决定是否迁移远端服务器运行。

### 6.4 输出要求

建议输出目录：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/
```

必须产物：

```text
phase_s1b4_ltr_model.pkl
phase_s1b4_ltr_scores.csv
phase_s1b4_ltr_score_schema.json
phase_s1b4_training_diagnostics.json
phase_s1b4_metric_by_split.csv
phase_s1b4_feature_importance.csv
phase_s1b4_leakage_boundary_audit.json
phase_s1b4_gate_summary.json
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B4_LTR_TRAINING_EXECUTION_REPORT_CN.md
```

`phase_s1b4_ltr_scores.csv` 至少包含：

```text
date
instrument
split
fold_id
qlib_score_raw
qlib_rank
ltr_score
ltr_rank
sample_complete
```

允许包含 label/audit columns，但必须标记为 audit only，不得作为训练 feature。

### 6.5 诊断指标

允许输出只读训练诊断：

- train / validation / test row count；
- group date count；
- feature count；
- train / validation eval ndcg；
- one-pass test ndcg / rank IC / top-k label diagnostic；
- feature importance；
- score missing / rank missing / duplicate date-instrument count。

禁止输出或解释：

- 组合收益；
- 回撤；
- 换手；
- 动作次数；
- 买卖建议；
- 默认策略结论；
- simple 优于 turnover-controlled 或反过来的结论。

这些必须留到后续回放阶段。

### 6.6 Simple / Turnover-Controlled 边界

S1B4 只训练一个 common LTR model。

```text
split_aligned_ltr_simple = common LTR score direct usage candidate
split_aligned_ltr_turnover_controlled = same common LTR score + later score/rerank usage constraint candidate
```

S1B4 不得实现 turnover-control 规则，不得冻结 turnover 阈值，不得用 validation/test 回放指标选择阈值。

### 6.7 验收 Gate

通过 gate：

```text
s1b4_ltr_training_pass_request_s1b5_score_diagnostics_and_replay_policy
```

通过条件：

- 使用 S1B3 冻结参数；
- 使用 `sample_complete=true`；
- 只训练一个 common LTR model；
- 输出 train/validation/test score/rank；
- duplicate date/instrument count 为 0；
- ltr_score / ltr_rank 缺失为 0；
- no parameter search；
- no early stopping；
- no replay；
- no strategy return comparison；
- no frontend/API；
- no provider refresh/publish；
- no accepted latest switching；
- no monitor/trading chain；
- no buy/sell/position/return promise/probability semantics。

失败 gate：

```text
s1b4_training_failed_or_oom
s1b4_blocked_by_policy_violation
s1b4_blocked_by_data_integrity_issue
```

### 6.8 禁止事项

- 不训练 qlib；
- 不跑组合回放；
- 不比较策略收益；
- 不调参；
- 不改 feature；
- 不改 label；
- 不改 split；
- 不改 universe；
- 不新增数据源；
- 不联网；
- 不改前端/API；
- 不触发 provider refresh / publish；
- 不切换 accepted latest；
- 不触发 monitor config save / scan / alerts write；
- 不接 broker、orders、quick-trade；
- 不输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 7. 给执行者的一句话

请执行 Phase S1B4：严格按 S1B3 冻结参数和 `sample_complete=true` 过滤训练一个 common split-aligned LTR model，并输出 train/validation/test 的一次性 LTR score/rank 与训练诊断；不得调参、不得回放、不得比较收益、不得实现 turnover-control、不得新增数据源或触发前端/API/provider/accepted latest/monitor/交易链路，若本机 OOM 或训练失败则停止报告等待用户决定是否迁移远端。
