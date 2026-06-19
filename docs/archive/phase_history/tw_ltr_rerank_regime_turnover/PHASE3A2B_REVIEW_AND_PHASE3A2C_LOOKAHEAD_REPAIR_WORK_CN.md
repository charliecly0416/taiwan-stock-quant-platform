# Phase3A2B 审查意见与 Phase3A2C Lookahead / 指标口径修复工作文档

生成时间：2026-06-13

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE3A2B_AUTHORITY_REPAIR_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase3A2B 不通过，不能恢复 Phase3B。

本轮执行者完成了上一轮要求的 authority matrix，并选择 `backend/app/services/tw_stock_portfolio_replay.py` 作为产品侧权威口径；这一方向合理，也没有发现真实交易、provider、accepted latest、monitor 写入或前端/API 扩张。

但本轮回放结果不能用于收益、回撤、换手或费用结论，原因是执行脚本存在代码级口径错误：

1. 本地 K 线 adapter 对 2022-2026 长区间存在未来函数风险；
2. `gross_return` 与 `fee_tax_adjusted_net_return` 被写成同一个值；
3. `turnover_proxy` 只是 `action_count / days`，不是换手金额或组合换手；
4. turnover-controlled LTR 的 10 日动作预算实现错误，导致整个区间几乎只动作 3 次；
5. LTR score 缺失日期被标为 `completed_with_data_quality_warnings` 后仍直接参与可比结论，违反“同一交易日集合”的公平口径。

因此，报告中 `phase1c_ltr_simple_daily` 的高收益、`phase1c_ltr_turnover_controlled_daily` 的低回撤/低动作等结果均不得作为主线结论，也不得用于 Phase3B 解释层。

---

## 2. 是否偏离主线或新增分支

未发现新增模型主线、数据源主线、联网/provider 主线、前端/API 主线或真实交易主线。

但存在主线内执行偏差：

```text
Phase3A2B 目标是“同口径完整日频组合回放”；
当前实现虽然形式上输出了六个方法，但底层时间口径、收益字段和换手控制实现不成立。
```

这属于结果不成立，必须修复后重跑。

---

## 3. 关键问题

### P0：LocalKline 只返回最后 500 根 K 线，长区间回放存在未来函数

执行脚本中：

```text
scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py
```

关键代码：

```text
PriceStore.bars(): return rows[-limit:]
LocalKline.get_kline(): return self.ps.bars(symbol, limit)
```

而产品侧 replay service 的 `_next_close_after()` 使用：

```text
rows = self.kline_service.get_kline("TWStock", symbol, "1D", 500)
选择 row_date > asof_date 的第一根 close
```

这意味着对 2022 的 `asof`，adapter 返回的是全样本最后 500 根 K 线，很可能主要落在 2024-2026；`_next_close_after()` 会从这批未来 K 线中选第一根大于 2022 的价格，而不是 2022 asof 后的真实下一交易日价格。

这是 P0 级别问题，足以使本轮所有回放指标失效。

Phase3A2C 必须修复为：

```text
LocalKline.get_kline(..., limit=500)
返回按日期排序的完整历史窗口，且至少覆盖 replay 起点之前与之后的必要 K 线；
不能只返回全样本最后 limit 根。
```

更稳妥做法是：离线 adapter 不再依赖 `get_kline(..., 500)` 的截断语义，而是提供 asof-aware price lookup 或让服务在本轮用完整本地 CSV K 线。

### P0：turnover-controlled LTR 的动作预算实现错误

当前 `replay_turnover()` 中：

```text
window = window[-9:]
left = max(0, 3 - len(window))
window.append(asof)
```

`window` 存的是发生动作的日期，而不是最近 10 个交易日窗口。达到 3 次动作后，`len(window)` 长期保持 3，`left` 变成 0，后续几乎永久不再动作。

这解释了报告中 turnover-controlled LTR 在多个区间都只有 3 次动作：

- 2022：3
- 2025：3
- 2026 YTD：3
- validation：3
- independent_test：3
- common full range：3

这不是有效的“10 个交易日动作预算”，而是近似“全区间最多 3 次动作”。因此该方法当前不能作为 Stage 4 turnover-controlled portfolio layer 的证据。

Phase3A2C 必须修复为真正滚动窗口：

```text
每个 asof 只统计最近 10 个交易日内的 action dates；
窗口应随交易日推进自然过期；
不得把全区间动作数误当滚动预算。
```

### P1：`gross_return` 与 `fee_tax_adjusted_net_return` 被写成同一个值

当前 `row()` 中：

```text
tr = metrics.totalReturn
gross_return = tr
fee_tax_adjusted_net_return = tr
```

但 `_replay_variant()` 的 `totalReturn` 已经基于扣除 fee/tax 后的 final equity 计算。脚本没有单独维护无费用/税费的 gross equity curve，因此不能同时声明 gross 与 net。

Phase3A2C 必须二选一：

1. 明确只输出 `fee_tax_adjusted_net_return`，把 `gross_return` 置空或标记 `not_available_in_current_engine`；
2. 或在同一引擎中并行维护 gross equity / net equity，真实输出两者。

不得继续把同一个数复制到两个字段。

### P1：`turnover_proxy` 不是换手代理

当前：

```text
turnover_proxy = action_count / trading_days_used
```

这只能表示动作频率，不能表示换手金额、换手率或组合成交额占权益比例。主文档要求的是 action count 与 turnover proxy，二者不能是同一个动作数量的不同写法。

Phase3A2C 至少应输出：

```text
turnover_proxy_by_notional = sum(abs(trade_notional)) / average_equity
或
turnover_proxy_by_notional = sum(abs(trade_notional)) / initial_cash
```

若受 action payload 限制无法计算，必须标记不可用并说明原因，不得用动作频率冒充换手。

### P1：LTR score 缺失日期不能直接标 completed 后参与公平比较

Data Quality 显示：

- 2022 缺 5 个 LTR score 日期；
- 2026 YTD 缺 16 个 LTR score 日期；
- common full range 缺 5 个 LTR score 日期。

Phase3A2 工作文档要求所有方法共享同一交易日集合。当前 baseline 在这些日期照常回放，而 LTR 变体在缺分日空 items 或跳过，这会破坏公平比较。

Phase3A2C 必须明确处理：

```text
所有方法使用共同日期交集重跑；
或缺分日期全部从所有方法中排除；
或该区间标记为 blocked / not_comparable。
```

不得继续把这些区间标为可比较完成。

### P2：产品侧权威口径选择仍需补强证据

选择 `backend/app/services/tw_stock_portfolio_replay.py` 作为产品侧权威口径是合理方向，但 Phase3A2B 未证明 adapter 后的 Top50 adaptive 与产品服务/旧 stress replay 在短样本上完全一致。

Phase3A2C 需要增加最小 parity check：

- 对一个很短、无 LTR 缺失的区间；
- 同一 signal、同一价格、同一 config；
- 比较 `rank_rotate_top50_adaptive_score` 的 action_count、feeAndTax、finalEquity、equity curve 尾值；
- 如果和权威服务或旧 stress replay 不一致，必须解释差异并停止。

---

## 4. 安全边界审查

本轮安全边界通过。

已验证：

- `python -m py_compile scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`：通过；
- `python -m pytest backend/tests/test_tw_stock_portfolio_replay.py -q`：10 passed；
- 安全关键词扫描命中仅出现在 readonly flags、报告 Safety Boundary 或禁止事项说明中。

未发现：

- broker / quick-trade / order / target position / target weight；
- monitor config save / monitor scan / alerts write；
- provider refresh / publish；
- accepted latest switching；
- 真实买卖、仓位、收益承诺、胜率或上涨概率语义。

注意：安全通过不代表回放结果通过。当前失败原因是研究口径与时间口径不成立。

---

## 5. Phase3A2C 本轮唯一目标

只做一件事：

```text
修复 Phase3A2B 的 lookahead、净/毛收益、换手 proxy、turnover budget 与共同日期集合问题，
然后在同一权威口径下重跑六个 required methods。
```

本轮继续暂停 Phase3B。

---

## 6. 允许改动范围

允许修改：

- `scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`

允许新增或覆盖：

- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3A2C_LOOKAHEAD_METRIC_REPAIR_EXECUTION_REPORT_CN.md`

允许只读检查：

- `backend/app/services/tw_stock_portfolio_replay.py`
- `backend/tests/test_tw_stock_portfolio_replay.py`
- `scripts/run_tw_rank_rotation_stress_replay.py`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/*`

默认不允许修改：

- frontend；
- API route；
- backend 产品服务；
- monitor；
- database；
- provider；
- qlib accepted latest；
- Phase1C 训练脚本；
- Phase1C frozen score artifact；
- Phase3B 文档或解释层实现。

如果必须修改 backend 产品服务才能消除 `get_kline(..., 500)` 的长区间限制，必须先停止并回到审查，不得擅自改产品服务。

---

## 7. 必做修复

### Step 1：修复 K 线 lookahead

执行者必须证明：

```text
任意 asof 的成交价来自 asof 之后的第一个真实交易日 close，
且不是因为 K 线截断而跳到多年后的未来价格。
```

必须输出 price execution audit，至少包含：

- sample asof；
- symbol；
- expected_next_trade_date；
- actual_execution_date；
- actual_execution_price；
- days_to_execution；
- status。

验收要求：

```text
days_to_execution 在正常交易日附近，应为 1 到少数非交易日间隔；
不得出现跨数月或跨年的 execution date。
```

### Step 2：修复共同日期集合

每个 period 必须输出：

- baseline_signal_days；
- ltr_score_days；
- common_replay_days；
- excluded_dates；
- comparison_status。

若使用共同日期交集，所有方法必须只在 `common_replay_days` 上回放。

若某 period 缺分太多导致不可比，必须标记 `blocked_not_comparable`，不得输出 completed 结论。

### Step 3：修复 gross/net 字段

必须满足以下之一：

- 同时真实输出 gross 和 fee/tax-adjusted net；
- 或只输出 net，把 gross 标记为 unavailable。

不得复制同一数值。

### Step 4：修复 turnover proxy

必须输出真实的 notional turnover proxy，建议：

```text
sum(abs(quantity * price)) / average_equity
```

或：

```text
sum(abs(quantity * price)) / initial_cash
```

同时保留 `action_count`，但不得把 action frequency 当 turnover proxy。

### Step 5：修复 turnover-controlled LTR 滚动预算

必须把 Phase3A1 的：

```text
k30_a3_gap0.0_buf0.0_holdw2_budget0.2
```

转换成真正日频滚动约束，并明示：

- target_k；
- max_actions_per_day；
- max_actions_per_10_trading_days；
- min_holding_days；
- confidence_gap；
- no_trade_buffer；
- turnover_budget_proxy。

动作预算必须按最近 10 个交易日滚动，而不是全区间累计。

### Step 6：重跑六个 required methods

必须继续包含：

```text
rank_rotate_top30
rank_rotate_top50
rank_rotate_top50_adaptive_score
confirmed_exit
phase1c_ltr_simple_daily
phase1c_ltr_turnover_controlled_daily
```

不得因为修复后 LTR 表现下降而删减方法或调整参数。

---

## 8. 必须覆盖区间

继续覆盖：

- 2022 full available replay range；
- 2025 full available replay range；
- 2026 year-to-date available replay range；
- Phase1C validation range：2024-08-12 到 2025-06-24；
- Phase1C independent_test range：2025-06-25 到 2026-05-07；
- common full range shared by all compared methods。

但每个区间都必须基于共同可比日期集合输出，不能让 baseline 和 LTR 使用不同交易日集合。

---

## 9. 必交付产物

执行者必须写入：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE3A2C_LOOKAHEAD_METRIC_REPAIR_EXECUTION_REPORT_CN.md
```

必须输出或更新：

- `phase3a2_price_execution_audit.csv`
- `phase3a2_method_comparison.csv`
- `phase3a2_period_comparison.csv`
- `phase3a2_equity_curves.csv`
- `phase3a2_actions_summary.csv`
- `phase3a2_data_quality.csv`
- `phase3a2_gate_summary.json`

报告必须明确写：

1. lookahead 修复方式；
2. price execution audit 摘要；
3. 共同日期集合处理方式；
4. gross/net 字段定义；
5. turnover proxy 定义；
6. turnover-controlled LTR 滚动预算实现；
7. 六个 required methods 的结果；
8. 是否仍建议暂停 Phase3B；
9. 安全边界声明。

---

## 10. 禁止事项

本轮禁止：

- 恢复 Phase3B；
- 做前端、API、页面文案或解释层；
- 修改 backend 产品服务，除非先停止回审查；
- 新增数据源、联网、补价；
- provider refresh / publish；
- accepted latest switching；
- 重训 LTR 或重建 Phase1C frozen score；
- 使用 independent_test 反选参数；
- 重新打开 regime gate；
- 引入文档外特征；
- 使用真实 broker / quick-trade / orders；
- 输出目标仓位、目标权重、买卖建议、收益更优结论、胜率或上涨概率。

---

## 11. 验收门槛

Phase3A2C 通过的最低门槛：

1. price execution audit 无跨期异常；
2. 共同日期集合明确，baseline 与 LTR 使用同一交易日集合；
3. `gross_return` 与 `fee_tax_adjusted_net_return` 不再错误复制；
4. turnover proxy 是金额换手代理，不是动作频率；
5. turnover-controlled LTR 不再全区间只有 3 次动作，除非有代码级可解释证据证明滚动预算自然导致该结果；
6. 六个 required methods 同口径重跑完成，或明确标记不可比并停止；
7. 保持 readonly / research-only；
8. 不建议恢复 Phase3B，除非本轮所有验收项通过且审查者确认。

若任一 P0 修复失败，执行者必须停止，并把 gate 写为：

```text
stop_phase3a2c_replay_accounting_invalid
```

不得继续给出收益/回撤比较结论。
