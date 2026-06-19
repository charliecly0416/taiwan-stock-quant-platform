# Phase S1B4 审查意见与 Phase S1B5 Score Diagnostics / Replay Policy 工作文档

生成日期：2026-06-14

## 1. 审查范围

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B3_REVIEW_AND_PHASES1B4_TRAINING_WORK_CN.md
```

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B4_LTR_TRAINING_EXECUTION_REPORT_CN.md
scripts/train_tw_ltr_s1b4_common_model.py
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/
```

本轮只审查 S1B4 是否按冻结政策完成一次性 common LTR 训练与 score/rank 物化，不审查组合回放或收益结论。

## 2. 审查结论

结论：`通过，允许进入 Phase S1B5 score diagnostics and replay policy freeze。`

Gate：

```text
s1b4_pass_request_s1b5_score_diagnostics_and_replay_policy
```

通过理由：

1. S1B4 使用 S1B3 冻结参数训练了一个 common `LightGBM.LGBMRanker`，未发现参数搜索、早停、重训试错或多模型择优。
2. 训练输入严格过滤 `sample_complete == true`。
3. 产出的 `phase_s1b4_ltr_scores.csv` 覆盖全部 `sample_complete=true` 样本，无多出或漏掉 key。
4. score/rank 无缺失，无 duplicate date/instrument。
5. simple 与 turnover-controlled 仍共用同一个 common LTR score，本轮没有实现 turnover-control 使用层规则。
6. 未跑组合回放，未比较收益、回撤、换手、动作次数，未改前端/API/provider/accepted latest/monitor/交易链路。

## 3. 核验证据

### 3.1 训练政策一致性

`phase_s1b4_training_diagnostics.json`：

```text
model_family: LightGBM.LGBMRanker
objective: lambdarank
feature_count: 34
model_params:
  n_estimators: 120
  learning_rate: 0.05
  num_leaves: 31
  min_child_samples: 20
  random_state: 42
  n_jobs: 2
sample_complete_filter: sample_complete == true
common_model_only: true
turnover_control_not_implemented_in_s1b4: true
```

### 3.2 Score / Rank 一致性

只读一致性检查：

```text
sample_complete_rows: 298242
score_rows: 298242
missing_from_sample_complete: 0
sample_complete_not_scored: 0
score_duplicates: 0
ltr_score_missing: 0
ltr_rank_missing: 0
all_sample_complete: true
split_counts:
  train_scored: 141085
  validation: 69812
  test: 87345
rank_minmax_by_date_bad: 0
```

审查判断：S1B4 score/rank 产物完整，且只覆盖训练可用样本。

### 3.3 Metric 诊断

`phase_s1b4_metric_by_split.csv`：

| split | ndcg@10 | ndcg@30 | ndcg@50 | rank_ic_audit |
| --- | ---: | ---: | ---: | ---: |
| train_scored | 0.818906 | 0.667408 | 0.653471 | 0.107457 |
| validation | 0.508662 | 0.511378 | 0.550673 | -0.015908 |
| test | 0.511329 | 0.519084 | 0.558275 | 0.034576 |

审查判断：

- 这些只能作为训练诊断，不能作为策略收益结论；
- validation rank IC 为负，test rank IC 仅小幅为正，后续必须如实带入 S1B5/S1B6；
- 不允许基于该诊断回头调参、改 feature、改 label 或改 split。

## 4. Findings

### High

无阻断项。

### Medium

1. Validation 诊断偏弱：`rank_ic_audit=-0.015908`。这不阻断进入 score diagnostics / replay policy，但后续不得用它做调参借口；S1B6 回放若不支持 LTR，应按主线收口。
2. `phase_s1b4_ltr_scores.csv` 包含 `topk_forward_bucket`、`ltr_relevance_label`、`future_excess_return_rank_10d`，这些必须继续标记为 audit-only，后续回放策略输入不得使用 future label 字段。
3. S1B5 仍不能跑组合回放；只能做 score 质量诊断、baseline 对齐检查和冻结 S1B6 的回放政策。

### Low

1. S1B4 输出的是 `sample_complete=true` 子集 `298242` 行，不是 S1B2 原始 `308385` 行。后续所有比较必须明确这个口径，避免与全量 qlib score rows 混淆。
2. 本轮本机训练完成，无 OOM，无需远端迁移。

## 5. 台股只读安全边界审查

### Findings

未发现 broker、quick-trade、orders、target-position、target-weight、monitor write、provider publish/refresh、accepted latest switching。

### Network Audit

本轮为本地文件与脚本审查，未涉及前端/API/E2E，未要求 network audit。

### Text / Agent Semantics

报告中的训练、score、回放、收益、买卖、仓位等词均处于研究流程、禁止事项或历史模拟边界语境中；未形成真实交易建议、目标仓位、收益承诺、胜率或上涨概率承诺。

### Verdict

只读安全边界通过。

## 6. Phase S1B5 工作文档：Score Diagnostics 与 Replay Policy Freeze

### 6.1 目标

Phase S1B5 只做两件事：

```text
1. 对 S1B4 common LTR score/rank 做只读质量诊断；
2. 冻结 S1B6 完整日频组合回放政策。
```

S1B5 不跑组合回放，不输出收益/回撤/换手/动作次数结论，不决定 LTR 是否有效。

### 6.2 输入

必须使用：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_ltr_scores.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_ltr_score_schema.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_metric_by_split.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_qlib_wf_scores.csv
```

如果需要本地价格数据用于冻结 S1B6 回放 calendar / tradability 口径，只能读取已有 normalized/TWII 文件，不得触发 provider refresh/publish 或 accepted latest。

### 6.3 Score Diagnostics 要求

必须输出只读诊断：

1. LTR score/rank coverage by split；
2. LTR 与 qlib rank 的相关性 / overlap；
3. Top10 / Top30 / Top50 overlap by split；
4. LTR score 分布、rank 分布、每日可选股票数量；
5. audit-only label diagnostics，必须明确不是收益结论；
6. validation weak signal caveat；
7. test 诊断只读记录，不允许反馈训练。

禁止：

- 根据 diagnostics 调参；
- 根据 diagnostics 改 feature / label / split / universe；
- 把 test 诊断解释为 S1 最终有效；
- 输出组合收益、回撤、换手、动作次数；
- 输出买卖、仓位、收益承诺、上涨概率语义。

### 6.4 Replay Policy Freeze 要求

S1B5 必须冻结 S1B6 回放比较口径，但不得实际跑回放。

S1B6 至少应比较：

```text
qlib / Top50 adaptive baseline
rank_rotate_top50
rank_rotate_top30
confirmed_exit
split_aligned_ltr_simple
split_aligned_ltr_turnover_controlled
```

如果某个 baseline 的 score/rank 或既有实现缺失，S1B5 必须报告，不得临时发明新策略。

回放区间必须冻结：

```text
full test: 2023-01-01..2025-06-30
yearly: 2023, 2024, 2025H1
rolling: 6m / 12m
regime: 使用既有 regime 或 S1B2/S1B4 已有 regime_segment，只读分段
```

指标必须冻结为主线指标：

```text
fee_tax_adjusted_net_return
max_drawdown
action_count
buy_count
sell_count
fee_and_tax
turnover_proxy_by_notional_over_avg_equity
relative_return_vs_top50_adaptive
relative_drawdown_vs_top50_adaptive
relative_actions_vs_top50_adaptive
```

S1B6 回放必须是完整日频口径；不得只看 top-k label 或静态截面诊断来替代回放。

### 6.5 Simple / Turnover-Controlled 政策

S1B5 必须继续保持：

```text
split_aligned_ltr_simple 与 split_aligned_ltr_turnover_controlled 暂按同等级候选处理。
```

S1B5 可以冻结 turnover-controlled 的既有使用层约束候选，但必须满足：

- 不能根据 S1B4 validation/test 诊断临时选择阈值；
- 不能根据收益、回撤、换手、动作次数反向设阈值；
- 如无既有冻结规则可复用，必须报告为 `turnover_control_policy_not_ready`，不得自行发明。

### 6.6 必须输出

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B5_SCORE_DIAGNOSTICS_AND_REPLAY_POLICY_EXECUTION_REPORT_CN.md
```

建议产物：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5_score_diagnostics/phase_s1b5_score_coverage_by_split.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5_score_diagnostics/phase_s1b5_rank_overlap_summary.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5_score_diagnostics/phase_s1b5_label_diagnostic_by_split.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5_score_diagnostics/phase_s1b5_replay_policy.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5_score_diagnostics/phase_s1b5_forbidden_action_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5_score_diagnostics/phase_s1b5_gate_summary.json
```

### 6.7 验收 Gate

通过 gate：

```text
s1b5_score_diagnostics_and_replay_policy_pass_request_s1b6_full_daily_replay
```

通过条件：

- score diagnostics 完整；
- replay policy 冻结；
- S1B6 strategies / intervals / metrics 清楚；
- 明确 validation weak-signal caveat；
- no parameter tuning；
- no feature / label / split / universe modification；
- no replay in S1B5；
- no strategy return comparison in S1B5；
- no frontend/API；
- no provider refresh/publish；
- no accepted latest switching；
- no monitor/trading chain；
- no buy/sell/position/return promise/probability semantics。

失败 gate：

```text
s1b5_blocked_by_missing_baseline_or_replay_policy
s1b5_blocked_by_scope_violation
s1b5_blocked_by_test_feedback_or_tuning_attempt
```

若 baseline 缺失或 turnover-controlled 规则需要用户 tradeoff，执行者必须停止并报告。

### 6.8 禁止事项

- 不训练 LTR；
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

请执行 Phase S1B5：只对 S1B4 common LTR score/rank 做只读覆盖、rank overlap、label diagnostic，并冻结 S1B6 完整日频回放的 strategies、intervals、metrics 与 turnover-controlled 使用层政策；不得训练、不得回放、不得比较收益、不得调参、不得新增数据源或触发前端/API/provider/accepted latest/monitor/交易链路。
