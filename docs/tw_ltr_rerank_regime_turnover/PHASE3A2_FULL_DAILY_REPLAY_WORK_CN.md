# Phase3A2 Full Daily Replay 工作文档与预审意见

生成时间：2026-06-13

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

用户最新指令：

```text
暂停 PHASE3B_READONLY_EXPLANATION_SCOPE_WORK_CN.md；
改为 Phase3A2；
将 Phase1C LTR simple / turnover-controlled LTR
接入与 Top50 自适应 score 完全一致的完整日频组合回放口径；
公平比较 2022、2025、2026 等区间的收益、回撤、动作次数、换手与费用；
再决定是否回到 Phase3B 只读解释层。
```

---

## 1. 预审结论

允许开启 Phase3A2，但只能作为“回放口径公平性修复”。

Phase3B 当前暂停，不得执行。

Phase3A2 的必要性成立：Phase3A1 使用非重叠 10 日标签窗口，虽然修复了 `future_return_10d` 重叠复利问题，但仍没有把 LTR simple / turnover-controlled LTR 放到与 `rank_rotate_top50_adaptive_score` 完全一致的完整日频组合回放引擎中比较。主文档要求 baseline 对照，且 `rank_rotate_top50_adaptive_score` 与 `confirmed_exit` 不能长期保持 blocked 后继续推进前端。

---

## 2. 本轮唯一目标

只回答：

```text
在与 Top50 自适应 score 完全一致的完整日频组合回放口径下，
Phase1C LTR simple 与 Phase1C turnover-controlled LTR
相对 Top50 adaptive / Top30 / Top50 / confirmed_exit 的
收益、回撤、动作次数、换手、费用表现是否成立？
```

本轮不得做解释层、不得做前端、不得做 API。

---

## 3. 权威回放口径

执行者必须先定位并复用当前项目中 Top50 自适应 score 的完整日频组合回放口径。

预审识别到候选脚本：

```text
scripts/run_tw_rank_rotation_stress_replay.py
```

该脚本包含当前本地只读 rank rotation stress replay 口径：

- 读取历史 signal artifacts；
- 读取本地 Yahoo-adjusted normalized prices；
- 使用 `close_after(asof)` 做 asof 后第一个可用交易价；
- 使用初始资金、lot size、fee rate、sell tax rate；
- 计算 total return、max drawdown、action count、buy/sell count、fee/tax、final equity；
- 支持 `adaptive_score=True`；
- 明确 research-only，不更新 latest_signal，不 provider publish，不连接 broker/order。

执行者必须做两步：

1. 确认这是否就是当前 Top50 自适应 score 的权威日频回放口径；
2. 若不是，必须停下并说明真正权威脚本/函数/产物路径，不得自行发明新口径。

---

## 4. 允许改动范围

允许新增 Phase3A2 脚本：

```text
scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py
```

允许轻量复用或抽取 `scripts/run_tw_rank_rotation_stress_replay.py` 的纯函数，但不得改变 Top50 adaptive baseline 的行为。

允许输出目录：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/
```

允许新增执行报告：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE3A2_FULL_DAILY_REPLAY_EXECUTION_REPORT_CN.md
```

默认不允许修改：

- frontend；
- API；
- monitor；
- database；
- provider；
- qlib accepted latest；
- Phase1C 模型训练脚本；
- Phase3B 文档之外的解释层产物。

---

## 5. 固定输入

### 5.1 LTR score

必须使用已冻结 Phase3A0 score：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
score_head10_all_l31_alpha0.7_top50_only
```

禁止重建、改写、替换该 score。

### 5.2 Top50 adaptive / baseline signal artifacts

必须使用与 Top50 自适应 score 完整日频回放一致的历史 signal artifacts。

预审候选：

```text
qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/
```

如实际权威路径不同，执行者必须在报告中写明。

### 5.3 价格输入

必须使用与 Top50 自适应 score 完整日频回放一致的本地价格输入。

预审候选：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/
```

禁止联网补价，禁止 provider refresh/publish。

---

## 6. 必须比较的方法

至少包含：

```text
rank_rotate_top30
rank_rotate_top50
rank_rotate_top50_adaptive_score
confirmed_exit
phase1c_ltr_simple_daily
phase1c_ltr_turnover_controlled_daily
```

说明：

- `phase1c_ltr_simple_daily`：使用 Phase1C frozen score 生成与 baseline 同样日频口径的排序/候选，不加入 turnover control。
- `phase1c_ltr_turnover_controlled_daily`：在同一日频回放引擎内加入 Phase3A1 已选 turnover 约束，或等价日频转换约束。
- 如果 `confirmed_exit` 权威口径无法在同一引擎中定位，必须停下说明原因；不得继续以 blocked 带过。

---

## 7. 必须公平一致的口径

所有方法必须共享：

- 同一交易日集合；
- 同一可交易 universe；
- 同一价格源；
- 同一成交价规则；
- 同一 initial cash；
- 同一 lot size；
- 同一 fee rate；
- 同一 sell tax rate；
- 同一最大持仓数；
- 同一缺价处理；
- 同一现金和持仓记账；
- 同一 equity curve / drawdown 计算。

禁止：

- Top50 adaptive 用价格真实日频回放，LTR 用 `future_return_10d` 标签；
- LTR 使用独立的费用/换手定义；
- 不同方法使用不同日期或不同 universe 后直接比较；
- 使用 independent_test 结果反选参数；
- 重新优化 Phase1C LTR 参数。

---

## 8. 必须覆盖的区间

至少输出以下切片：

```text
2022 full available replay range
2025 full available replay range
2026 year-to-date available replay range
Phase1C validation range: 2024-08-12 to 2025-06-24
Phase1C independent_test range: 2025-06-25 to 2026-05-07
common full range shared by all compared methods
```

若某一区间缺少完整 signal 或价格，必须输出 data_quality 行，说明：

```text
missing_signal_days
missing_price_count
excluded_dates
excluded_symbols
comparison_status
```

不得静默跳过。

---

## 9. 必须输出指标

每个方法、每个区间至少输出：

```text
gross_return
fee_tax_adjusted_net_return 或 total_return_after_fee_tax
final_equity
max_drawdown
action_count
buy_count
sell_count
turnover_proxy
fee_and_tax
missing_price_count
trading_days_used
```

还必须输出差异列：

```text
delta_vs_rank_rotate_top50_adaptive_score
delta_vs_phase1c_ltr_simple_daily
```

注意：可以使用“买/卖”作为历史回放 action 统计字段，但报告和面向用户文案必须明确它是历史模拟，不是指令、不是建议、不是订单。

---

## 10. Turnover-controlled LTR 日频转换要求

Phase3A2 可以把 Phase3A1 的窗口级配置转换为日频约束，但必须明示转换规则。

Phase3A1 selected config：

```text
k30_a3_gap0.0_buf0.0_holdw2_budget0.2
```

日频转换建议：

```text
target_k = 30
max_actions_per_10_trading_days = 3
min_holding_days = 20
turnover_budget_per_10_trading_days = 0.2
confidence_gap = 0.0
no_trade_buffer = 0.0
```

若执行者采用其他等价转换，必须给出理由和对照诊断，不得重新调参寻找更优结果。

---

## 11. 必交付产物

至少输出：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_method_comparison.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_period_comparison.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_equity_curves.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_actions_summary.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_data_quality.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_gate_summary.json
docs/tw_ltr_rerank_regime_turnover/PHASE3A2_FULL_DAILY_REPLAY_EXECUTION_REPORT_CN.md
```

---

## 12. Gate 规则

Phase3A2 只能输出以下 gate 之一：

```text
request_user_decision_after_phase3a2_daily_replay
request_resume_phase3b_readonly_explanation_scope
stop_phase3_daily_replay_not_supported
stop_phase3a2_incomplete_baseline_or_data
```

### 12.1 `request_resume_phase3b_readonly_explanation_scope`

只在以下条件同时满足时允许：

- Top50 adaptive / confirmed_exit / LTR simple / LTR turnover-controlled 全部完成同口径日频回放；
- LTR turnover-controlled 至少在动作/换手/费用上有清晰改善；
- 净收益/回撤没有形成需要用户重新判断的重大 tradeoff；
- 报告明确不声称收益更优。

### 12.2 `request_user_decision_after_phase3a2_daily_replay`

若出现以下情况，必须回到用户：

- LTR turnover-controlled 降低换手但牺牲收益或回撤；
- LTR simple 胜出但 turnover-controlled 不胜出；
- Top50 adaptive 明显优于 LTR；
- 不同年份结论冲突；
- 是否回 Phase3B 需要产品取舍。

### 12.3 `stop_phase3_daily_replay_not_supported`

若同口径日频回放显示 LTR simple 与 LTR turnover-controlled 均无清晰价值，则停止 Stage 4，不回 Phase3B。

### 12.4 `stop_phase3a2_incomplete_baseline_or_data`

若无法构造与 Top50 adaptive 完全一致的 baseline 对照，或 2022/2025/2026 核心区间数据不足，则停止并报告，不得用不完整对照推进。

---

## 13. 禁止事项

本轮禁止：

- 执行 Phase3B；
- 改前端或 API；
- 接主推荐；
- 声称收益更优；
- 重新训练 LTR；
- 重建 Phase1C score；
- 重新调 LTR 参数；
- 重新打开 regime gate；
- 用 regime 控制组合；
- 新增数据源或联网；
- provider refresh / publish；
- accepted latest switching；
- monitor 写入或扫描；
- database 写入；
- broker / quick-trade / orders；
- target position / target weight；
- 真实买入、卖出、持有、仓位建议；
- 收益承诺、胜率、上涨概率语义。

---

## 14. 必做验证

执行者必须至少运行：

```text
python -m py_compile scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py
python scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py
```

若普通沙箱触发环境限制，可按相同只读命令复跑，但必须在报告中说明。

还必须做文本与安全边界扫描：

```text
broker / quick-trade / orders / target position / target weight
provider refresh / publish / accepted latest switching
收益更优 / 胜率 / 上涨概率 / 仓位建议
```

命中只允许出现在禁止事项或安全说明中，不得出现在结论或面向用户解释中。

---

## 15. 执行报告必须包含

执行报告必须固定包含：

1. 权威 Top50 adaptive 日频回放口径来源；
2. 是否复用 `scripts/run_tw_rank_rotation_stress_replay.py`，若否说明原因；
3. 输入数据路径与 common date / universe 对齐结果；
4. 2022、2025、2026、validation、independent_test、common full range 分表；
5. 方法对照总表；
6. equity curve / actions / fee / turnover 产物路径；
7. data quality；
8. safety boundary；
9. gate 结论；
10. 是否建议恢复 Phase3B，以及理由。
