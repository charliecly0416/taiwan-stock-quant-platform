# Phase V0 审查意见与 Phase V1 分年完整日频回放工作文档

生成时间：2026-06-14

主线依据：`docs/tw_ltr_strategy_validation/LTR_STRATEGY_VALIDATION_MAINLINE_CN.md`

审查入口：`docs/tw_ltr_strategy_validation/PHASEV0_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase V0 **通过**，允许进入 Phase V1。

执行者已完成本轮应做的合同冻结：

- 候选策略冻结为：
  - `phase1c_ltr_simple_daily`
  - `phase1c_ltr_turnover_controlled_daily`
- Phase1C 冻结分数字段为：
  - `score_head10_all_l31_alpha0.7_top50_only`
- 主基线冻结为：
  - `rank_rotate_top50_adaptive_score`
- 对照 baseline 冻结为：
  - `rank_rotate_top50_adaptive_score`
  - `rank_rotate_top50`
  - `rank_rotate_top30`
  - `confirmed_exit`
- 完整日频回放口径已冻结到 Phase3A2C 修复后的产品侧权威路径；
- 年度 / rolling / 市况分段要求已列出；
- 指标、审计字段和禁止事项已列出；
- 未发现本轮实际执行新回放、重训、调参、前端/API、联网、新数据、provider、accepted latest、monitor 或交易链路。

---

## 2. 必须纠偏的范围说明

V0 报告中有一处阶段表述需要审查者纠偏：

```text
报告第 6.2 / 6.3 节把 rolling 和市况分段写成 Phase V1 必须包含。
```

根据主线文档，阶段边界应为：

- Phase V1：只做 `2022 / 2023 / 2024 / 2025 / 2026 YTD` 分年完整日频回放；
- Phase V2：再做 rolling 6M / 12M；
- Phase V3：再做 bull / normal / bear 或 normal / caution / risk_off 市况分段。

因此本审查放行 Phase V1，但 Phase V1 **不得提前混入 rolling 和市况分段计算**。rolling/市况的冻结要求保留为后续阶段合同，不是 V1 执行范围。

---

## 3. 安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无实质问题。

### 判断

V0 报告中的 `provider`、`accepted latest`、`monitor`、`broker`、`quick-trade`、`orders`、`target positions`、`买入/卖出`、`仓位`、`收益承诺`、`胜率/上涨概率` 等命中均处于禁止事项、审计字段或历史动作计数语境中。

未发现：

- 真实交易入口；
- 写请求；
- 目标仓位或目标权重输出；
- 收益、胜率、上涨概率承诺；
- 前端/API 产品化要求；
- provider refresh/publish；
- accepted latest switching；
- monitor config save / scan / alerts write。

只读研究边界通过。

---

## 4. 产物盘点核对

审查抽查确认以下 Phase3A2C 产物存在：

- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_gate_summary.json`
- `phase3a2b_authority_matrix.csv`
- `phase3a2_method_comparison.csv`
- `phase3a2_period_comparison.csv`
- `phase3a2_data_quality.csv`
- `phase3a2_price_execution_audit.csv`
- `phase3a2_actions_summary.csv`
- `phase3a2_equity_curves.csv`

抽查 `phase3a2_method_comparison.csv` 与 `phase3a2_period_comparison.csv`，字段包含：

- `fee_tax_adjusted_net_return`
- `final_equity`
- `max_drawdown`
- `action_count`
- `add_action_count`
- `sell_count`
- `turnover_proxy_by_notional_over_avg_equity`
- `fee_and_tax`
- `missing_price_count`
- `trading_days_used`
- `delta_vs_rank_rotate_top50_adaptive_score`

这足以作为 Phase V1 年度验证的口径来源，但 Phase V1 仍必须补齐年度层面的相对回撤差和动作数差。

---

## 5. Phase V1 本轮唯一目标

只做一件事：

```text
按 Phase V0 冻结合同，
对 2022 / 2023 / 2024 / 2025 / 2026 YTD 做完整日频同口径年度回放验证。
```

本轮只回答：

```text
LTR simple daily / LTR turnover-controlled daily
在分年维度上是否相对 Top50 自适应主基线具备稳定价值。
```

本轮不做 rolling，不做市况分段，不做产品化判断。

---

## 6. Phase V1 允许改动范围

允许：

- 新增一个只读验证脚本，例如：
  - `scripts/validate_tw_ltr_strategy_phasev1_yearly_replay.py`
- 读取 Phase3A2C 已冻结脚本、产物和本地价格/信号/分数文件；
- 复用或调用产品侧 `TWStockPortfolioReplayService` / `_replay_variant()` 权威路径；
- 输出只读 CSV / JSON / Markdown 产物到：
  - `data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/`
- 撰写执行报告：
  - `docs/tw_ltr_strategy_validation/PHASEV1_YEARLY_REPLAY_EXECUTION_REPORT_CN.md`

允许计算：

- 年度同口径回放；
- 年度审计汇总；
- 年度候选 vs baseline 相对指标；
- 年度数据状态。

---

## 7. Phase V1 禁止事项

本轮禁止：

- rolling 6M / 12M 验证；
- bull / normal / bear 或 risk_off 市况分段验证；
- 重训 LTR；
- 重建或替换 Phase1C score；
- 调参；
- 修改候选策略；
- 新增候选策略；
- 新增主 baseline；
- 修改 replay 口径；
- 使用测试结果反向调参；
- 联网或新增数据源；
- provider refresh/publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 前端/API 改动；
- 把结果写成买卖、仓位、收益承诺、胜率或上涨概率语义。

---

## 8. Phase V1 必须覆盖的年度切片

必须输出：

```text
2022
2023
2024
2025
2026 YTD
```

每个年度必须明确：

- `period`
- `start_date`
- `end_date`
- `baseline_signal_days`
- `ltr_score_days`
- `common_replay_days`
- `excluded_dates`
- `comparison_status`

如果某年没有足够 accepted runs 或 Phase1C score：

```text
comparison_status = insufficient_data
```

不得静默跳过 2023 或 2024。

---

## 9. Phase V1 必须比较的方法

每个年度必须包含以下方法：

```text
rank_rotate_top50_adaptive_score
rank_rotate_top50
rank_rotate_top30
confirmed_exit
phase1c_ltr_simple_daily
phase1c_ltr_turnover_controlled_daily
```

主比较对象固定为：

```text
rank_rotate_top50_adaptive_score
```

不得把 `phase1c_ltr_simple_daily` 或其他方法临时改成主基线。

---

## 10. Phase V1 必须输出指标

每个年度、每个方法至少输出：

- `fee_tax_adjusted_net_return`
- `final_equity`
- `max_drawdown`
- `action_count`
- `buy_count`
- `sell_count`
- `fee_and_tax`
- `turnover_proxy_by_notional_over_avg_equity`
- `missing_price_count`
- `trading_days_used`
- `relative_return_vs_top50_adaptive`
- `relative_drawdown_vs_top50_adaptive`
- `relative_actions_vs_top50_adaptive`
- `gross_return`

其中：

- `gross_return` 若引擎不可得，必须写 `not_available_in_current_engine`；
- `buy_count` 可由 `add_action_count` 映射，但必须在报告中说明；
- `relative_drawdown_vs_top50_adaptive` 必须用同年度 `max_drawdown` 计算；
- `relative_actions_vs_top50_adaptive` 必须用同年度 `action_count` 计算。

不得只报告收益率。

---

## 11. Phase V1 必须输出产物

建议至少输出：

```text
data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1_yearly_method_comparison.csv
data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1_yearly_data_quality.csv
data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1_yearly_price_execution_audit.csv
data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1_yearly_gate_summary.json
```

执行报告必须提交：

```text
docs/tw_ltr_strategy_validation/PHASEV1_YEARLY_REPLAY_EXECUTION_REPORT_CN.md
```

---

## 12. Phase V1 执行报告必须包含

执行者报告必须固定包含：

1. 本轮目标；
2. 实际改动文件；
3. 是否严格复用 Phase V0 冻结口径；
4. 是否使用产品侧 `TWStockPortfolioReplayService` / `_replay_variant()`；
5. 年度表格；
6. 每年数据状态；
7. 2023 / 2024 是否完成或为何 `insufficient_data`；
8. LTR simple 相对 Top50 自适应的年度表现；
9. turnover-controlled LTR 相对 Top50 自适应的年度表现；
10. 动作数、换手、回撤是否与收益同屏报告；
11. price execution audit 摘要；
12. data quality 摘要；
13. 禁止事项自查；
14. 下一步 gate 建议。

---

## 13. Phase V1 验收门槛

Phase V1 通过的最低门槛：

- 年度切片完整覆盖 2022 / 2023 / 2024 / 2025 / 2026 YTD；
- 没有静默跳过缺数据年份；
- 所有方法使用同一年度 common replay date set；
- 每个年度指标完整；
- 相对 Top50 自适应的 return / drawdown / action delta 完整；
- 没有重训、调参、数据源、前端/API、provider、accepted latest、monitor、交易链路越权；
- 报告能够支持审查者判断是否进入 Phase V2 rolling validation。

---

## 14. Phase V1 Gate

如果年度验证显示候选策略仍有跨年度验证价值，下一步 gate 为：

```text
request_phase_v2_rolling_window_validation
```

如果年度验证显示 LTR 候选只在少数年份有效、2023/2024 缺口无法合理补齐、或相对 Top50 自适应明显不稳，下一步 gate 为：

```text
stop_ltr_candidate_not_yearly_robust
```

不得在 Phase V1 结束后直接进入前端/API 或产品化。
