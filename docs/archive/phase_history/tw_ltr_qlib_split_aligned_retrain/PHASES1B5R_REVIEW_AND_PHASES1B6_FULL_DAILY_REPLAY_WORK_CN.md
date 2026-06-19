# Phase S1B5R 审查意见与 Phase S1B6 Full Daily Replay 工作文档

生成日期：2026-06-14

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B5R_BASELINE_READINESS_REPAIR_EXECUTION_REPORT_CN.md
```

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B5_REVIEW_AND_PHASES1B5R_BASELINE_READINESS_REPAIR_WORK_CN.md
```

---

## 1. 审查结论

结论：`通过，允许进入 Phase S1B6 full daily replay。`

S1B5R 已完成上一轮要求的窄修复：

- 将 S1B4 score rows 与 S1B2 sample rows 按 `date/instrument/split/fold_id` 对齐；
- 生成 replay-ready score table；
- 补齐 `qlib_top50_adaptive_baseline` 与 `confirmed_exit` 所需字段；
- 重新冻结 6 个 mandatory baselines 的 readiness；
- 修复 gate 逻辑，使任何 blocked baseline 必须阻断；
- 未训练、未回放、未比较收益、未调参、未新增数据源、未触发前端/API/provider/accepted latest/monitor/交易链路。

推荐 gate：

```text
s1b5r_baseline_readiness_repair_pass_request_s1b6_full_daily_replay
```

---

## 2. 关键证据

### 2.1 Replay-ready table 完整性

产物：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_replay_ready_scores.csv
```

审查核验：

```text
row_count = 298242
date_count = 2055
duplicate_key_count = 0
adaptive_score_missing_count = 0
confirmed_exit_missing_count = 0
```

split 覆盖：

| split | rows | dates | min_date | max_date |
| --- | ---: | ---: | --- | --- |
| train_scored | 141085 | 969 | 2017-01-10 | 2020-12-31 |
| validation | 69812 | 489 | 2021-01-04 | 2022-12-30 |
| test | 87345 | 597 | 2023-01-03 | 2025-06-30 |

S1B6 必须只使用 `split == test` 做旧窗口公平验证的最终完整日频回放，不得把 train/validation 回放结果解释为样本外效果。

### 2.2 Future label 未进入策略输入

replay-ready table 当前字段：

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
adaptive_score_baseline
confirmed_exit_baseline
```

未发现以下 future label 字段进入策略输入：

```text
future_return_*
future_excess_return_*
future_excess_return_rank_*
topk_forward_bucket
ltr_relevance_label
```

### 2.3 Baseline readiness

6 个 mandatory baselines 均已 ready：

```text
qlib_top50_adaptive_baseline
rank_rotate_top50
rank_rotate_top30
confirmed_exit
split_aligned_ltr_simple
split_aligned_ltr_turnover_controlled
```

`adaptive_score_baseline` 与 `confirmed_exit_baseline` 的公式可在既有脚本中核对：

```text
scripts/train_tw_ltr_phase1_lambdamart.py
scripts/diagnose_tw_ltr_phase1c_final_repair.py
```

因此本轮没有把新 baseline 临时发明进 S1B6。

---

## 3. Findings

未发现阻断项。

### Low 1：S1B6 必须防止 split 语义误用

replay-ready table 同时包含 `train_scored`、`validation`、`test`。S1B6 可以保留 train/validation rows 作为输入完整性审计，但最终策略比较、相对指标、S1 方法有效性判断必须只基于：

```text
split == test
2023-01-03..2025-06-30
```

不得把 train/validation 的收益、回撤或动作次数写成样本外效果。

---

## 4. 安全边界审查

未发现以下越权：

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

## 5. 是否偏离主线

未发现主线外扩展。

S1B5R 只是把 S1B6 所需的 replay-ready 输入合同补齐，没有进入训练、调参、回放比较、产品化或交易链路。可以进入 S1B6。

---

## 6. Phase S1B6 工作文档：Full Daily Replay

### 6.1 目标

Phase S1B6 只回答一个问题：

```text
在 qlib 旧训练窗口对齐的 test 区间内，split-aligned LTR simple / turnover-controlled 是否在完整日频组合回放口径下，相比 qlib / Top50 adaptive baseline 有清楚、稳定、费用后仍成立的增益？
```

S1B6 是旧窗口公平验证，不是当前上线验证，不是新鲜模型重训，不是产品化实现。

### 6.2 输入

必须使用：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_replay_ready_scores.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_replay_policy.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_baseline_readiness.json
```

必须只在最终比较中使用：

```text
split == test
```

可读取既有本地 normalized 价格文件做日频组合净值计算，但不得触发 provider refresh / publish，不得切换 accepted latest，不得联网。

### 6.3 必须比较的策略

S1B6 必须同口径比较：

```text
qlib_top50_adaptive_baseline
rank_rotate_top50
rank_rotate_top30
confirmed_exit
split_aligned_ltr_simple
split_aligned_ltr_turnover_controlled
```

要求：

- `split_aligned_ltr_simple` 与 `split_aligned_ltr_turnover_controlled` 继续按同等级候选处理，不预设高低；
- turnover-controlled 只能使用 S1B5R 已冻结的既有 usage-layer config；
- 不得根据 S1B6 test 回放结果重新选阈值、换 top-k、换费用假设或改退出规则；
- 若某策略无法完整日频回放，必须报告并阻断，不得用静态 top-k label 或截面诊断替代。

### 6.4 回放区间

完整 test：

```text
2023-01-03..2025-06-30
```

分段必须输出：

```text
full test
2023
2024
2025H1
rolling 6m
rolling 12m
regime_segment
```

如果某个 rolling / regime 分段样本不足，必须标注样本数和不可解释原因，不得静默删除。

### 6.5 指标

必须输出主线指标：

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

还必须输出每个策略的基础审计字段：

```text
start_date
end_date
trading_days
initial_cash_or_equity_assumption
fee_rate
tax_rate
position_count_target
daily_nav_available_count
missing_price_days
skipped_trade_count
```

### 6.6 Lookahead / split purity 要求

S1B6 必须明确写出：

```text
train_scored: 2017-01-10..2020-12-31，只作训练期来源说明，不作为样本外结论
validation: 2021-01-04..2022-12-30，只作旧窗口验证来源说明，不作为最终 test 结论
test: 2023-01-03..2025-06-30，唯一用于 S1B6 样本外完整日频回放比较
```

禁止：

- 用 train/validation 的收益结果证明 LTR 样本外更好；
- 根据 test 结果调参；
- 根据 test 结果修改 feature、label、split、universe、turnover 阈值；
- 使用 future label 字段参与任何策略选择或回放动作。

### 6.7 禁止事项

S1B6 禁止：

- 训练 LTR；
- 训练 qlib；
- 调参；
- 改 feature / label / split / universe；
- 新增数据源；
- 联网；
- 改前端/API；
- provider refresh / publish；
- accepted latest switching；
- monitor / trading chain；
- broker / quick-trade / orders；
- 买卖、持有、仓位、收益承诺、胜率或上涨概率语义；
- 产品化或默认策略切换。

### 6.8 必须输出

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B6_FULL_DAILY_REPLAY_EXECUTION_REPORT_CN.md
```

建议产物：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_strategy_metrics_full_test.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_strategy_metrics_yearly.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_strategy_metrics_rolling_6m.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_strategy_metrics_rolling_12m.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_strategy_metrics_by_regime.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_daily_nav_by_strategy.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_action_audit_by_strategy.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_split_purity_and_lookahead_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_forbidden_action_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6_full_daily_replay/phase_s1b6_gate_summary.json
```

### 6.9 S1B6 Gate

S1B6 执行者只能给事实性推荐，不得自行进入 S2 或产品化。

可用 gate：

```text
s1b6_full_daily_replay_complete_request_reviewer_decision
s1b6_blocked_by_replay_engine_or_price_data_gap
s1b6_blocked_by_split_or_lookahead_violation
s1b6_blocked_by_scope_violation
```

审查者在 S1B6 后才根据完整日频回放证据给出主线 S1 结论：

```text
split_aligned_ltr_method_supported
split_aligned_ltr_method_not_supported
split_aligned_data_insufficient
```

---

## 7. 给执行者的一句话

请执行 Phase S1B6：只用 S1B5R replay-ready scores 的 `split == test` 区间 `2023-01-03..2025-06-30`，对 6 个已冻结策略做完整日频组合回放，输出 full test、分年、rolling 6m/12m、regime 分段和主线费用后指标；不得训练、调参、改 feature/label/split/universe、新增数据源、联网、改前端/API、触发 provider/accepted latest/monitor/交易链路，且不得把 train/validation 结果解释为样本外效果。
