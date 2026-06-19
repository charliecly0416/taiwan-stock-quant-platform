# Phase S1B6 审查意见与 Phase S1B6R Accounting Repair 工作文档

生成日期：2026-06-14

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B6_FULL_DAILY_REPLAY_EXECUTION_REPORT_CN.md
```

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B5R_REVIEW_AND_PHASES1B6_FULL_DAILY_REPLAY_WORK_CN.md
```

---

## 1. 审查结论

结论：`不通过，不能给出 S1 方法有效性结论，要求执行 Phase S1B6R accounting repair 后重跑。`

S1B6 确实完成了 6 个冻结策略的回放产物，并且报告声明只使用 `split == test`，也未发现训练、调参、前端/API、provider、accepted latest、monitor 或交易链路越权。

但当前回放存在会计时点错误：执行报告称交易用 `asof` 后下一交易日 close 成交，但脚本在同一个 `asof` 循环内先用未来执行价修改现金/持仓，再立刻用 `asof` 当日或之前价格计算当日 NAV。这会把下一交易日才成交的持仓提前放入上一日净值，违反完整日频回放的 as-of accounting 口径。

因此当前收益、回撤、换手、费用后结果均不能作为 S1 结论依据。

推荐 gate 应改为：

```text
s1b6_blocked_by_lookahead_accounting_violation
```

---

## 2. Findings

### High 1：交易执行日与 NAV 计价日错位，形成 lookahead accounting

报告口径写明：

```text
执行价：本地既有 normalized price 中 asof 后下一交易日 close。
```

实际 action audit 也显示第一批交易为：

```text
asof = 2023-01-03
execution_date = 2023-01-04
```

但 daily NAV 第一行已经在 `2023-01-03` 记录了建仓后的状态：

```text
2023-01-03, qlib_top50_adaptive_baseline, equity=1009224.96, cash=151.01, holding_count=10
```

这说明 `2023-01-04` 才成交的持仓和现金变化，被提前计入 `2023-01-03` 的 NAV。该错误会影响所有策略的收益、回撤、费用和动作后的持仓路径。

正确口径应是：

- `asof` 当日只能生成目标/订单计划；
- 交易在 `execution_date` 生效；
- `asof` 当日 NAV 只能使用当日已生效的旧持仓；
- 新买入/卖出后的现金和持仓只能从 `execution_date` 或其之后的 NAV 开始体现；
- 若使用 next close 成交，最后一个 asof 若没有下一交易日成交价，不得强行成交。

### High 2：当前 S1B6 结果不能用于判断 `split_aligned_ltr_method_supported`

当前 full test 指标显示：

```text
split_aligned_ltr_turnover_controlled fee_tax_adjusted_net_return = 0.463012
split_aligned_ltr_simple fee_tax_adjusted_net_return = -0.340259
qlib_top50_adaptive_baseline fee_tax_adjusted_net_return = -0.617965
```

但由于会计时点错误，这些收益和回撤不能作为 LTR 方法有效性的证据。审查者不能据此给出：

```text
split_aligned_ltr_method_supported
```

也不能据此进入 S2 或任何产品化讨论。

### Medium 1：`rank_rotate_top50` 与 `rank_rotate_top30` 当前结果完全相同，策略身份需要解释或修复

full test 中：

```text
rank_rotate_top50 == rank_rotate_top30
```

两者收益、回撤、动作数、费用完全一致。脚本中非 turnover-controlled 策略使用 `target = candidates[:MAX_HOLDINGS]`，而 `MAX_HOLDINGS = 10`，因此当排序相同且最终只持有前 10 名时，`candidate_k=50` 与 `candidate_k=30` 不会产生差异。

这不一定是错误，但必须在 S1B6R 中明确：

- 若 `rank_rotate_top50/top30` 本来只是候选池标签，在持仓数固定为 10 时二者可能退化为同一策略，报告必须说明；
- 若主线期望比较 Top50 与 Top30 的真实不同策略，则执行者必须按冻结定义修复策略实现；
- 不得把两个完全相同的结果当成两个独立 baseline 证据。

### Low 1：split / safety 边界声明本身未发现问题

S1B6 的 split audit 声明：

```text
test_rows_used = 87345
future_label_fields_used_as_strategy_input = false
test_feedback_used_for_tuning = false
```

forbidden audit 声明未训练、未调参、未新增数据源、未联网、未触发前端/API/provider/accepted latest/monitor/trading chain。该部分未发现越权。

---

## 3. 安全边界审查

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

## 4. 是否偏离主线

执行范围没有明显扩展到主线外，但结果不成立。

S1B6 的目标是完整日频组合回放。当前回放会计时点不满足完整日频 as-of 口径，因此必须修复后重跑，不能进入 S1 结论或 S2。

---

## 5. Phase S1B6R 工作文档：Accounting Repair

### 5.1 目标

Phase S1B6R 只做一件事：

```text
修复 S1B6 完整日频回放的 as-of accounting / execution-date accounting，并用同一冻结策略重跑。
```

S1B6R 不训练、不调参、不改 feature / label / split / universe，不进入 S2，不产品化。

### 5.2 必须修复的会计口径

执行者必须采用以下原则之一，并在报告中明确说明：

推荐口径：

```text
signal_date / asof: 只生成目标组合
execution_date: 下一交易日 close 成交
nav_date: 只能反映 nav_date 当日已经生效的持仓和现金
```

具体要求：

- `asof` 当日产生的买卖不能影响 `asof` 当日 NAV；
- `execution_date` 当日成交后，成交后的持仓和现金最早只能反映在 `execution_date` 的收盘 NAV；
- 若 NAV 记录的是日终状态，必须保证该日所有已执行交易的执行价和计价价同属该日，不能把未来交易放回过去；
- 每条 action 必须保留 `signal_date/asof`、`execution_date`、`effective_nav_date`；
- 最后一日若没有下一交易日价格，不能执行新交易，只能按已有持仓 mark-to-market；
- fees/tax 必须在交易生效日扣除；
- turnover_notional 必须按实际生效交易统计。

允许的实现方式：

```text
方式 A：两阶段事件队列
先按 asof 生成 pending orders；到 execution_date 时执行 pending orders；再计算 execution_date NAV。

方式 B：统一滞后一日回放
第 t 日信号只决定第 t+1 日收盘后的持仓；第 t 日 NAV 永远用 t 日开始前已生效持仓。
```

不得继续使用“先用 next_after(asof) 成交，再用 asof mark-to-market”的实现。

### 5.3 必须重新验证策略身份

S1B6R 必须继续比较 6 个冻结策略：

```text
qlib_top50_adaptive_baseline
rank_rotate_top50
rank_rotate_top30
confirmed_exit
split_aligned_ltr_simple
split_aligned_ltr_turnover_controlled
```

同时必须解释或修复：

```text
rank_rotate_top50 与 rank_rotate_top30 为什么完全相同
```

要求：

- 如果固定 `position_count_target=10` 导致 top50/top30 都只取前 10 名，必须在报告中明确标注二者退化为同一策略，不得当作独立证据；
- 如果主线既有定义要求 top50/top30 的候选池对持仓保留产生差异，则必须按冻结定义修复，不得临时调参；
- 不得新增策略，不得改 frozen turnover-controlled config。

### 5.4 输入不变

必须继续使用：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_replay_ready_scores.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_replay_policy.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_baseline_readiness.json
```

最终比较仍只允许：

```text
split == test
2023-01-03..2025-06-30
```

不得读取远程数据，不得触发 provider，不得切换 accepted latest。

### 5.5 必须重新输出

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B6R_ACCOUNTING_REPAIR_EXECUTION_REPORT_CN.md
```

建议产物：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_strategy_metrics_full_test.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_strategy_metrics_yearly.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_strategy_metrics_rolling_6m.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_strategy_metrics_rolling_12m.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_strategy_metrics_by_regime.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_daily_nav_by_strategy.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_action_audit_by_strategy.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_accounting_timeline_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_split_purity_and_lookahead_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_strategy_identity_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_forbidden_action_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_gate_summary.json
```

### 5.6 Accounting audit 必须包含

`phase_s1b6r_accounting_timeline_audit.json` 至少包含：

```text
signal_date_affects_same_day_nav: false
execution_date_before_or_equal_effective_nav_date: true
next_day_execution_not_counted_in_prior_day_nav: true
last_day_new_trade_without_next_price_count: 0
fee_tax_deducted_on_execution_date: true
```

如果无法证明这些条件，必须阻断：

```text
s1b6_blocked_by_lookahead_accounting_violation
```

### 5.7 禁止事项

S1B6R 禁止：

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

### 5.8 S1B6R Gate

允许 gate：

```text
s1b6r_accounting_repair_complete_request_reviewer_decision
s1b6_blocked_by_lookahead_accounting_violation
s1b6_blocked_by_replay_engine_or_price_data_gap
s1b6_blocked_by_split_or_lookahead_violation
s1b6_blocked_by_scope_violation
```

审查者在 S1B6R 通过后，才允许给出 S1 结论：

```text
split_aligned_ltr_method_supported
split_aligned_ltr_method_not_supported
split_aligned_data_insufficient
```

---

## 6. 给执行者的一句话

请执行 Phase S1B6R：修复 S1B6 回放中“用 asof 后下一交易日成交，却把成交后持仓/现金计入 asof 当日 NAV”的 accounting/lookahead 问题，严格按 signal_date、execution_date、effective_nav_date 重跑 6 个冻结策略，并解释或修复 rank_rotate_top50/top30 完全相同的策略身份问题；不得训练、调参、改 feature/label/split/universe、新增数据源、联网、改前端/API 或触发 provider/accepted latest/monitor/交易链路。
