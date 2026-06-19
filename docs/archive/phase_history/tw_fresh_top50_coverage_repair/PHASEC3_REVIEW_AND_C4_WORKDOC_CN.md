# Phase C3 审查结论与 Phase C4 工作文档

生成日期：2026-06-15

审查对象：

```text
docs/tw_fresh_top50_coverage_repair/PHASEC3_ASOF_REPLAY_READY_CONTRACT_WORK_CN.md
docs/tw_fresh_top50_coverage_repair/PHASEC3_ASOF_REPLAY_READY_CONTRACT_EXECUTION_REPORT_CN.md
data_tw/experiments/fresh_top50_coverage_repair/phasec3_*.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec3_summary.json
```

## 1. C3 审查结论

结论：

```text
C3 不通过；
未发现未来股票倒灌；
未发现 instrument 有效期违规；
未发现执行者用训练窗口收益率证明策略优劣；
但 replay-ready 不完整，不能进入前端只读展示合同；
必须先执行 C4 universe / replay-ready repair。
```

推荐 gate：

```text
phase_c3_review_blocked_requires_c4_replay_ready_repair
```

## 2. C3 通过项

### 2.1 Asof eligibility 通过

C3 检查结果：

```text
total repaired rows: 30750
eligible rows: 30750 / 30750
eligible rows min by day: 150
future_or_instrument_range_violation_rows: 0
accepted_universe_violation_rows: 0
```

判断：

```text
未发现未来上市股票倒灌；
未发现 instrument 起始日前进入或结束日后继续进入；
未发现不在 accepted prediction universe 的记录。
```

### 2.2 收益率未被误用

C3 报告明确：

```text
本阶段只做 coverage / asof / replay-ready 合同审计，不使用收益率证明策略优劣。
uses_return_metrics_for_strategy_superiority = false
```

未发现把训练窗口收益率或本阶段收益率写成策略优劣证据。

### 2.3 只读安全边界通过

未发现：

```text
训练 qlib/LTR
改前端/API
accepted latest switching
provider refresh / publish
monitor / broker / orders / quick-trade
真实买卖、仓位、收益承诺、胜率或上涨概率语义
```

## 3. C3 阻断项

### 3.1 Replay-ready 不完整

C3 summary：

```text
repaired rows:      30750
replay-ready rows:  30630
daily replay-ready min: 148
```

阻断原因：

```text
missing_current_price_rows:        100
missing_next_execution_price_rows: 100
missing_adaptive_score_rows:       120
missing_ret20_rows:                120
missing_volatility20_rows:         120
missing_twii_ret20_rows:           0
```

这违反 C3 通过条件：

```text
replay_ready rows 接近或等于 eligible rows；
无 next-day execution 价格缺失导致的不可回放记录。
```

虽然缺口较小，daily min 仍有 148，但当前不能宣称 repaired fresh top50 的 150 支全部 replay-ready。

### 3.2 缺失集中于早期日期，需解释

`phasec3_daily_coverage_summary.csv` 显示问题集中在窗口开头：

```text
2025-07-01..2025-07-11: replay_ready_rows 多为 149
2025-07-14..2025-07-18: replay_ready_rows 多为 148
```

后期多为：

```text
replay_ready_rows = 150
```

C4 必须查清这些缺失是否来自：

- symbol 当天/次日价格文件缺口；
- repaired artifact 包含了没有价格的 raw score row；
- early-window feature warmup；
- ret20 / volatility20 计算窗口不足；
- symbol/date 格式或价格 join key 问题；
- 非交易日 / next execution date mapping 问题。

### 3.3 tw_liquid_dyn 只能继续作为辅助

C3 显示：

```text
outside_tw_liquid_dyn_aux_rows: 8082
```

报告解释 `tw_liquid_dyn` 只作为辅助审计，不作为硬门槛；该解释可以接受，因为若硬套它会重现 S2B post-filter 的覆盖收缩。

但 C4 必须继续保留这个边界：

```text
不要用 tw_liquid_dyn 重新把 repaired fresh top50 缩回 88/109/150。
```

## 4. Phase C4 目标

C4 只做：

```text
修复或解释 C3 发现的 replay-ready 不完整问题。
```

C4 不做：

- 策略收益比较；
- 前端展示；
- 默认策略切换；
- qlib/LTR 训练；
- provider / accepted latest / monitor / broker / orders / quick-trade。

## 5. C4 必查问题

### 5.1 缺失行定位

对以下三类缺失输出逐行样本与全量原因：

```text
missing_current_price_rows = 100
missing_next_execution_price_rows = 100
missing_adaptive_score_rows = 120
```

必须输出：

```text
date
instrument
qlib_score_raw
qlib_rank
has_current_price
has_next_execution_price
has_adaptive_score
has_ret20
has_volatility20
price_first_date
price_last_date
next_execution_date
root_cause
repair_action
```

### 5.2 价格缺失修复策略

若本地 normalized price 实际存在但 join 失败：

```text
修复 join key / date mapping / symbol normalization。
```

若本地 normalized price 确实不存在：

```text
不得联网抓取；
不得 provider refresh；
不得 accepted latest switching；
只能将该 row 从 replay-ready 候选中排除，并用 next-ranked eligible row top-up。
```

### 5.3 Adaptive score 缺失修复策略

若 `ret20 / volatility20` 可由本地历史价格计算：

```text
离线补算；
保留公式不变；
不训练模型。
```

若因历史窗口不足无法补算：

```text
该 row 不应进入 replay-ready；
用 next-ranked eligible row top-up；
必须记录原因。
```

### 5.4 Top-up 策略

C4 的目标不是让 CSV 强行每天 150 行，而是让：

```text
daily replay_ready_rows = 150
```

如果 raw top150 中有 1-2 行不可 replay-ready，应从同日 raw score 排名后续股票中补足，前提是补入股票满足：

```text
instrument effective date 合法；
accepted universe 合法；
has qlib score；
has current price；
has next execution price；
has adaptive score；
has ret20 / volatility20 / TWII_ret20。
```

如果同日无法补足 150，必须报告：

```text
date
available replay-ready count
why cannot top up
```

### 5.5 C4 不得使用收益率判断修复好坏

C4 只能用以下指标判断：

```text
eligible rows
replay_ready rows
missing current price rows
missing next execution price rows
missing adaptive score rows
instrument range violations
future leakage rows
```

不得用收益率证明 repaired fresh top50 更优或更差。

## 6. C4 输出产物

执行者应提交：

```text
docs/tw_fresh_top50_coverage_repair/PHASEC4_REPLAY_READY_REPAIR_EXECUTION_REPORT_CN.md
```

建议产物：

```text
data_tw/experiments/fresh_top50_coverage_repair/phasec4_missing_replay_ready_rows.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec4_missing_reason_summary.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec4_daily_coverage_summary.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec4_asof_eligibility_audit.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec4_replay_ready_audit.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec4_summary.json
```

## 7. C4 通过标准

C4 可提交审查的最低标准：

```text
daily repaired rows = 150 或解释为什么不应强行 150；
daily replay_ready_rows = 150，或每个低于 150 日期有不可修复解释；
future_or_instrument_range_violation_rows = 0；
accepted_universe_violation_rows = 0；
missing_current_price_rows = 0 或合理排除；
missing_next_execution_price_rows = 0 或合理排除；
missing_adaptive_score_rows = 0 或合理排除；
不使用收益率证明策略优劣；
不改前端/API；
不触发 provider / accepted latest / monitor / broker / orders / quick-trade。
```

## 8. 后续路线

若 C4 通过：

```text
可重新进入 C2-style 前端影响判断或准备前端只读展示合同；
仍不直接切默认；
收益比较必须另开 OOS / walk-forward 主线。
```

若 C4 不通过：

```text
不进入前端展示；
不继续收益比较；
先修 universe / price / feature 合同。
```

## 9. 给执行者的一句话

请执行 Phase C4：只修复或解释 C3 中 repaired fresh top50 的 replay-ready 缺口，重点处理 100 行 current/next price 缺失和 120 行 adaptive score / ret20 / volatility20 缺失；不得用收益率判断策略优劣，不得训练 qlib/LTR，不得改前端/API，不得触发 provider/accepted latest/monitor/交易链路。
