# Phase S1B5 审查意见与 Phase S1B5R Baseline Readiness Repair 工作文档

生成日期：2026-06-14

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B5_SCORE_DIAGNOSTICS_AND_REPLAY_POLICY_EXECUTION_REPORT_CN.md
```

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B4_REVIEW_AND_PHASES1B5_SCORE_DIAGNOSTICS_WORK_CN.md
```

---

## 1. 审查结论

结论：`不放行进入 Phase S1B6，要求先执行 Phase S1B5R baseline readiness repair。`

S1B5 的 score diagnostics 本身基本符合本轮边界：

- 未训练 LTR；
- 未训练 qlib；
- 未跑组合回放；
- 未比较策略收益；
- 未调参；
- 未改 feature / label / split / universe；
- 未新增数据源或联网；
- 未改前端/API；
- 未触发 provider / accepted latest / monitor / trading chain；
- 未输出买卖、仓位、收益承诺、胜率或上涨概率语义。

但 S1B5 的 gate 结论不成立。报告和产物同时声明：

```text
recommended_gate = s1b5_score_diagnostics_and_replay_policy_pass_request_s1b6_full_daily_replay
```

以及：

```text
blocked_baselines_for_s1b6_followup = [
  "qlib_top50_adaptive_baseline",
  "confirmed_exit"
]
```

这两者互相矛盾。根据 S1B5 工作文档，若 baseline 缺失或 replay policy 不完整，必须使用：

```text
s1b5_blocked_by_missing_baseline_or_replay_policy
```

因此本轮不能直接进入 S1B6。

---

## 2. Findings

### High 1：S1B6 必选 baseline 未 ready，却给出 pass gate

S1B5 replay policy 中，以下 S1B6 必选策略被标为 blocked：

```text
qlib_top50_adaptive_baseline = blocked_in_current_s1b5_input_contract
confirmed_exit = blocked_in_current_s1b5_input_contract
```

但 gate summary 仍建议进入：

```text
s1b5_score_diagnostics_and_replay_policy_pass_request_s1b6_full_daily_replay
```

这会导致 S1B6 的完整日频回放比较不完整，尤其是主线要求的相对指标依赖 Top50 adaptive：

```text
relative_return_vs_top50_adaptive
relative_drawdown_vs_top50_adaptive
relative_actions_vs_top50_adaptive
```

如果 Top50 adaptive baseline 缺失，S1B6 的核心比较基准就不成立。

### High 2：脚本 gate 逻辑没有把 blocked baseline 视为失败

`scripts/diagnose_tw_ltr_s1b5_score_diagnostics.py` 已收集 blocked baseline：

```text
blocked = [
  name for name, info in replay_policy["baseline_readiness"].items()
  if info["status"].startswith("blocked")
]
```

但 `write_gate()` 只在 duplicate 或 overlap empty 时失败，没有在 `blocked` 非空时失败。这是本轮 gate 错误的直接原因。

### Medium 1：修复方向应优先补齐输入合同，而不是发明新策略

S1B5 报告称 blocked 的原因是 S1B4 score artifact 不包含以下字段：

```text
qlib_score_zscore_by_date
ret20
volatility20
TWII_ret20
market_drawdown60
```

但 S1B2 样本产物已包含这些字段：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_ltr_samples.csv
```

因此下一轮应先做窄修复：把 S1B4 score rows 与 S1B2 样本字段按 key 对齐，生成 S1B6 replay-ready score table。不得因为 S1B4 artifact 缺列就跳过主 baseline，也不得临时发明新的 adaptive / confirmed_exit 策略。

### Low 1：validation weak-signal caveat 已正确保留

S1B5 已明确：

```text
validation rank_ic_audit = -0.015908
validation ndcg@30 = 0.511378
```

并要求后续不得据此调参、改 feature、改 label、改 split、改 universe 或改 turnover 阈值。该部分符合主线边界。

---

## 3. 安全边界审查

本轮未发现以下越权：

- frontend/API 修改；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 买卖建议、真实持有指令、收益承诺、胜率承诺、上涨概率承诺；
- 新数据源或联网。

只读安全边界通过。

---

## 4. 是否偏离主线

执行内容本身没有明显扩展到主线外，但结论偏离主线：

- 主线允许 S1B5 冻结 S1B6 回放政策；
- 主线不允许在必选 baseline blocked 的情况下进入 S1B6；
- 主线不允许用不完整 baseline 比较来判断 LTR 方法是否有效。

因此必须先修复 replay policy / baseline readiness，再决定是否进入 S1B6。

---

## 5. Phase S1B5R 工作文档：Baseline Readiness Repair

### 5.1 目标

Phase S1B5R 只做一件事：

```text
修复 S1B6 完整日频回放所需的 baseline readiness 与 replay input contract。
```

S1B5R 不跑组合回放，不输出收益/回撤/换手/动作次数，不判断 LTR 是否有效。

### 5.2 必须保持的边界

禁止：

- 训练 LTR；
- 训练 qlib；
- 跑组合回放；
- 比较策略收益；
- 调参；
- 改 feature / label / split / universe；
- 新增数据源；
- 联网；
- 改前端/API；
- provider refresh / publish；
- accepted latest switching；
- monitor / trading chain；
- 买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

允许：

- 读取既有 S1B2 / S1B4 / S1B5 本地产物；
- 对齐已有字段；
- 生成 S1B6 replay-ready 的只读输入表；
- 修复 gate 逻辑，使 blocked baseline 必须阻断。

### 5.3 输入

必须读取：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_ltr_scores.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_ltr_samples.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5_score_diagnostics/phase_s1b5_replay_policy.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5_score_diagnostics/phase_s1b5_gate_summary.json
```

可读取既有 turnover-controlled 冻结使用层来源：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_gate_summary.json
data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_validation_selection.csv
```

不得读取远程数据，不得触发 provider。

### 5.4 Replay-ready score table 要求

请按以下 key 对齐 S1B4 score rows 与 S1B2 sample rows：

```text
date
instrument
split
fold_id
```

输出 replay-ready table 至：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_replay_ready_scores.csv
```

至少包含：

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
feature_complete
regime_segment
qlib_score_percentile_by_date
qlib_score_zscore_by_date
ret20
volatility20
TWII_ret20
TWII_ret60
market_volatility20
market_drawdown60
market_breadth20
```

说明：

- `future_return_*`、`future_excess_return_*`、`topk_forward_bucket`、`ltr_relevance_label` 等未来标签字段不得进入 replay-ready table 的策略决策字段；
- 如果为了审计保留 label 字段，必须放入单独 audit-only 文件，不得被 S1B6 回放策略读取；
- 不得用 test label 反推任何策略阈值。

### 5.5 Baseline readiness 必须重新冻结

必须输出：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_baseline_readiness.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_replay_policy.json
```

以下 baseline 必须逐一标注 `ready` 或明确 blocked reason：

```text
qlib_top50_adaptive_baseline
rank_rotate_top50
rank_rotate_top30
confirmed_exit
split_aligned_ltr_simple
split_aligned_ltr_turnover_controlled
```

要求：

- `qlib_top50_adaptive_baseline` 必须说明使用哪些已有字段重建，不得改规则；
- `confirmed_exit` 必须说明是否存在可复用的权威定义；
- `split_aligned_ltr_simple` 与 `split_aligned_ltr_turnover_controlled` 继续按同等级候选处理，不分高低；
- turnover-controlled 只能复用既有冻结使用层，不能根据 S1B4/S1B5/S1B5R 的 validation/test 结果重新选择阈值。

如果 `confirmed_exit` 无法以既有权威定义重建，必须停止并给出：

```text
s1b5r_blocked_by_confirmed_exit_authority_gap
```

不得把不权威的 confirmed_exit 代理策略塞入 S1B6。

### 5.6 Gate 修复要求

必须修复 gate 逻辑：

```text
if any mandatory baseline status startswith("blocked"):
    recommended_gate = "s1b5_blocked_by_missing_baseline_or_replay_policy"
```

只有全部必选 baseline ready，且无 scope violation，才允许：

```text
s1b5r_baseline_readiness_repair_pass_request_s1b6_full_daily_replay
```

### 5.7 必须输出

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B5R_BASELINE_READINESS_REPAIR_EXECUTION_REPORT_CN.md
```

产物：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_replay_ready_scores.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_baseline_readiness.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_replay_policy.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_forbidden_action_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_gate_summary.json
```

### 5.8 S1B5R 验收条件

通过条件：

- replay-ready score table 覆盖 S1B6 full test period 所需 rows；
- key 对齐无重复；
- S1B4 score rows 与 S1B2 sample rows join 后无异常缺失；
- 必选 baseline readiness 全部 ready；
- confirmed_exit 有既有权威定义或明确阻断；
- gate 逻辑把任何 blocked baseline 视为失败；
- 未训练、未回放、未比较收益、未调参；
- 未触发任何前端/API/provider/accepted latest/monitor/trading 越权。

失败 gate：

```text
s1b5_blocked_by_missing_baseline_or_replay_policy
s1b5r_blocked_by_confirmed_exit_authority_gap
s1b5r_blocked_by_scope_violation
s1b5r_blocked_by_test_feedback_or_tuning_attempt
```

---

## 6. 给执行者的一句话

请执行 Phase S1B5R：只用既有 S1B4 scores 与 S1B2 samples 按 `date/instrument/split/fold_id` 补齐 S1B6 replay-ready 输入合同，重新冻结 `qlib_top50_adaptive_baseline`、`rank_rotate_top50`、`rank_rotate_top30`、`confirmed_exit`、`split_aligned_ltr_simple`、`split_aligned_ltr_turnover_controlled` 的 readiness，并修复 gate 逻辑使任何 blocked baseline 必须阻断；不得训练、不得回放、不得比较收益、不得调参、不得新增数据源或触发前端/API/provider/accepted latest/monitor/交易链路。
