# Phase B0 审查意见与 Phase B1 保守版回放验证工作文档

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_BASELINE_AND_CONSERVATIVE_TUNING_MAINLINE_CN.md`

审查入口：`docs/tw_ltr_baseline_conservative_tuning/PHASEB0_BASELINE_ANCHOR_AND_RULE_SCOPE_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase B0 **通过**，允许进入 Phase B1。

当前 gate：

```text
phaseb0_contract_frozen_request_phaseb1_conservative_replay
```

B1 放行范围仅限：

```text
固定候选的 LTR 保守版规则层回放验证 + 同口径默认基线最终比较
```

不得扩展为：

```text
无边界调参
重训 LTR
新数据源
前端/API 实现
默认策略切换
交易或写入链路
```

---

## 2. B0 完成度判断

B0 已冻结：

- 当前默认基线锚点：`rank_rotate_top50_adaptive_score`；
- 必须比较的 6 个既有策略；
- Phase1C frozen score 来源；
- product-side 完整日频回放口径；
- 年度、full range、validation、independent_test 时间切片；
- 必须输出的收益、回撤、动作、费用、换手和相对 Top50 adaptive 指标；
- LTR 保守版规则层可调范围；
- 现有保守版 + 2 个新增规则层变体；
- 禁止重训、改 score、改回放口径、新数据、provider、accepted latest、monitor、交易链路和前端/API 改动。

核心输入 artifact 已确认存在：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_schema.json
data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_method_comparison.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_period_comparison.csv
data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_walk_forward_oos.csv
```

---

## 3. 是否偏离主线

未发现实质偏离主线。

未发现执行者在 B0：

- 提前做最终默认基线结论；
- 跑新回放；
- 重训 LTR；
- 改 Phase1C score；
- 引入新数据源或联网；
- 改 provider / accepted latest；
- 写 monitor；
- 接 broker / quick-trade / orders；
- 输出 target position / target weight；
- 改前端/API；
- 把策略结果包装为真实投资建议或收益承诺。

---

## 4. 需要保留的 caveat

B0 报告中出现：

```text
phase1c_ltr_simple_daily：是，但不得默认化
phase1c_ltr_turnover_controlled_daily：是，但不得默认化
```

这句话在 B1 必须解释为：

```text
B1 可以把 LTR 策略纳入同口径默认基线比较，但 B1 不允许做产品默认切换或前端默认化实现。
```

不得解释为：

```text
B1 不需要比较 LTR 是否可作为最终默认候选。
```

主线要求 B1 在保守版验证完成后重新确认默认基线，因此 B1 必须给出综合默认建议，但最终产品切换只能留到后续 B2 审查后决定。

---

## 5. 安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：保留一个表述 caveat：B1 中“不得默认化”只能指不得产品默认切换，不得阻止同口径默认候选比较。

### Verdict

B0 只读研究边界通过。

---

## 6. Phase B1 唯一目标

只做两件事，顺序不可颠倒：

1. 按 B0 冻结的候选和口径，验证 LTR 保守版规则层变体；
2. 在保守版验证完成后，基于同口径结果给出最终默认基线建议。

B1 不是产品化轮次，不允许改前端/API。

---

## 7. Phase B1 必须比较的策略

B1 必须覆盖 6 个既有策略：

```text
rank_rotate_top50_adaptive_score
rank_rotate_top50
rank_rotate_top30
confirmed_exit
phase1c_ltr_simple_daily
phase1c_ltr_turnover_controlled_daily
```

并且只能新增 B0 冻结的 2 个规则层变体：

```text
phase1c_ltr_conservative_top30_2day_confirm_daily
phase1c_ltr_conservative_top20_entry_2day_exit_daily
```

不得追加：

```text
Top15 / Top25 / Top40
不同动作预算
不同最小持有期
不同 fee/tax/price 口径
任何结果驱动的临时变体
```

---

## 8. Phase B1 固定候选规则

### 8.1 现有保守基准

```text
candidate_key = phase1c_ltr_turnover_controlled_daily
candidate_pool_rank = Top50
buy_rank_threshold = 既有规则
buy_confirm_days = 1
sell_rank_threshold = 既有规则
sell_confirm_days = 1
max_actions_per_day = 1
max_actions_per_10_trading_days = 3
min_holding_days = 20
```

### 8.2 新增候选 1

```text
candidate_key = phase1c_ltr_conservative_top30_2day_confirm_daily
candidate_pool_rank = Top30
buy_rank_threshold = Top30
buy_confirm_days = 2
sell_rank_threshold = Top50 外或缺失
sell_confirm_days = 2
max_actions_per_day = 1
max_actions_per_10_trading_days = 3
min_holding_days = 20
```

一句话说明：

```text
只看 Top30 且连续 2 天确认，减少单日噪声动作。
```

### 8.3 新增候选 2

```text
candidate_key = phase1c_ltr_conservative_top20_entry_2day_exit_daily
candidate_pool_rank = Top50
buy_rank_threshold = Top20
buy_confirm_days = 1
sell_rank_threshold = Top50 外或缺失
sell_confirm_days = 2
max_actions_per_day = 1
max_actions_per_10_trading_days = 3
min_holding_days = 20
```

一句话说明：

```text
买入更严格，只接受 Top20；卖出需连续转弱。
```

---

## 9. Phase B1 回放口径

必须复用 B0 冻结口径：

```text
score column = score_head10_all_l31_alpha0.7_top50_only
replay authority = product-side TWStockPortfolioReplayService / Phase3A2C 口径
execution mode = next_trading_day_close
initial cash = 1,000,000
max holdings = 10
lot size = 10
fee rate = 0.001425
sell tax rate = 0.003
turnover proxy = sum_abs_quantity_price_over_average_equity
gross return policy = not_available_in_current_engine
price source = 既有本地 normalized price archive
signal source = 既有 accepted historical signal artifact
```

不得为了候选结果修改任何口径。

---

## 10. Phase B1 时间切片

必须输出：

```text
2022
2023
2024
2025
2026 YTD
common_full_range_shared_by_all_compared_methods
phase1c_validation_range = 2024-08-12..2025-06-24
phase1c_independent_test_range = 2025-06-25..2026-05-07
```

解释规则：

- `2022`、`2023` 只能作为 train 复盘；
- `2024` 是 train / validation mixed；
- `2025` 是 validation / independent_test mixed，必须拆分解释；
- `2026 YTD` 是 independent_test，但不能单独决定默认结论；
- `phase1c_independent_test_range` 只用于冻结候选后的样本外检查，不得用于反向改参数。

---

## 11. Phase B1 输出指标

每个策略 / 候选 / period 至少输出：

```text
fee_tax_adjusted_net_return
max_drawdown
action_count
buy_count
sell_count
fee_and_tax
turnover_proxy_by_notional_over_avg_equity
trading_days_used
relative_return_vs_top50_adaptive
relative_drawdown_vs_top50_adaptive
relative_actions_vs_top50_adaptive
```

不得只报告收益率。

---

## 12. Phase B1 必须回答的问题

执行报告必须回答：

1. 两个新增保守版候选是否相比 `phase1c_ltr_turnover_controlled_daily` 有明确改进；
2. 改进来自低回撤、低动作、低换手还是收益/风险平衡；
3. 改进是否只来自单一年份或单一 period；
4. action_count 是否仍明显低于 `phase1c_ltr_simple_daily`；
5. max_drawdown 是否因为追求收益明显恶化；
6. turnover proxy 是否仍维持保守特征；
7. 哪个保守候选值得保留进入 B2 参考列表；
8. 哪些候选必须淘汰；
9. 完成保守版验证后，当前默认基线是否仍应保持 `rank_rotate_top50_adaptive_score`；
10. 默认建议是否基于跨年度稳定性、回撤、动作数、用户可理解性和前端说明复杂度，而不是单一收益。

---

## 13. Phase B1 禁止事项

本轮禁止：

- 重训 LTR；
- 改特征 / label / LambdaMART 参数；
- 改 Phase1C frozen score；
- 改 score column；
- 改 replay price / fee / tax / lot / holdings / turnover 口径；
- 新增数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 前端/API 改动；
- 用 independent_test / 2026 YTD 结果反向调参；
- 看到结果后追加候选；
- 把候选写成“推荐策略 / 更优策略 / 最佳策略”；
- 输出真实买入、卖出、持有、仓位建议；
- 输出收益承诺、胜率或上涨概率。

---

## 14. Phase B1 产物要求

建议输出目录：

```text
data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay/
```

必须提交执行报告：

```text
docs/tw_ltr_baseline_conservative_tuning/PHASEB1_CONSERVATIVE_REPLAY_AND_DEFAULT_COMPARISON_EXECUTION_REPORT_CN.md
```

报告必须包含：

1. 本轮目标和未越界声明；
2. 固定候选规则表；
3. 输入 artifact 清单；
4. 回放口径确认；
5. 输出 artifact 清单；
6. 全策略 × period 对比表；
7. 新保守候选相对原保守版的对比；
8. 默认基线综合比较；
9. split-aware / OOS 防反向调参说明；
10. 是否建议进入 B2；
11. gate 建议。

---

## 15. Phase B1 Gate

如果固定候选验证完整、无口径漂移、无 OOS 反向调参，且能给出清楚默认基线建议：

```text
phaseb1_validated_request_phaseb2_user_first_product_closure
```

如果保守版候选没有稳定价值，但默认基线建议清楚：

```text
phaseb1_no_conservative_candidate_b2_label_dropdown_only
```

如果发现调参失控、结果不可解释、只靠个别年份、口径漂移或安全边界越界：

```text
stop_and_discuss_with_user
```
