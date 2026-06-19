# Phase P1 审查结论：O4 Orthogonal LTR vs Repaired Fresh Qlib Same-Window

生成日期：2026-06-15

审查对象：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP1_O4_VS_REPAIRED_FRESH_QLIB_SAME_WINDOW_WORK_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEP1_O4_VS_REPAIRED_FRESH_QLIB_SAME_WINDOW_EXECUTION_REPORT_CN.md
data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_o4_vs_repaired_fresh_qlib_same_window/
```

## 1. 结论

P1 通过。

推荐 gate：

```text
phase_p1_o4_vs_repaired_fresh_qlib_same_window_review_passed
```

允许进入后续默认策略讨论，但不得在本轮直接切换默认策略。

核心结论：

```text
repaired fresh qlib Top50 adaptive 在同窗口收益略高；
O4 orthogonal LTR 在回撤、动作数、换手上更保守；
两者差距很小，足以进入默认策略讨论，但不足以直接默认切换。
```

## 2. Artifact 口径核对

执行者使用的 repaired fresh qlib artifact 为：

```text
data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv
score column: adaptive_score_baseline
```

审计产物确认：

```text
uses_c4_repaired_replay_ready_fresh_artifact = true
fresh_c4_gate = phase_c4_replay_ready_repair_passed_with_coverage_below_150_explained
old_s2f_88_109_150_not_used_for_main_conclusion = true
```

因此本轮没有退回旧 S2F `88 / 109 / 150` coverage 口径。

Repaired fresh qlib replay-ready 覆盖：

```text
daily coverage min / median / max = 148 / 149.0 / 150
future_or_instrument_range_violation_rows = 0
accepted_universe_violation_rows = 0
missing_current_price_rows_after_repair = 0
missing_next_execution_price_rows_after_repair = 0
missing_adaptive_score_rows_after_repair = 0
```

Coverage 公平性结论可接受：

```text
coverage_unfairness_found = false
```

## 3. O4 指标复现

P1 中 O4 replay 指标：

```text
return = 0.800329
max_drawdown = -0.074962
action_count = 403
turnover_proxy = 39.761877
fee_and_tax = 157722.97
```

该结果与 O5/O5R 冻结 O4 指标一致，说明 O4 指标已复现，没有重新训练、改分数或改回放口径。

O4 artifact：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_row_scores.csv
score column: phaseo4_treatment_ltr_score_top50_preserve
```

## 4. 同窗口同回放合同

P1 固定合同：

```text
window = 2025-07-01..2026-05-07
execution = next-day execution
initial_equity = 1000000
fee_rate = 0.001425
tax_rate = 0.003
target_position_count = 10
lot_size = 10
replay_engine = scripts/evaluate_tw_ltr_s2d_full_daily_replay.py
```

两组主方法均使用同一 replay engine、同一费用税费、同一 next-day accounting。未发现改规则、改价格口径、改持仓数或改默认策略。

Next-day accounting：

```text
O4 pass = yes
repaired fresh qlib pass = yes
execution_date_not_after_signal_violations = 0
missing_price_days = 0
skipped_trade_count = 0
last_day_new_trade_without_next_price_count = 0
```

## 5. 同窗口结果

主对比结果：

```text
O4 orthogonal LTR return = 0.800329
repaired fresh qlib Top50 adaptive return = 0.801662
O4 - repaired fresh return diff = -0.001333
```

风险与交易路径：

```text
O4 max_drawdown = -0.074962
repaired fresh qlib max_drawdown = -0.085205
O4 drawdown shallower by = 0.010243

O4 action_count = 403
repaired fresh qlib action_count = 410
O4 actions fewer by = 7

O4 turnover_proxy = 39.761877
repaired fresh qlib turnover_proxy = 40.750969
O4 turnover lower by = 0.989092
```

PnL concentration：

```text
O4 top_symbol_abs_share = 0.102661
fresh top_symbol_abs_share = 0.106053

O4 top_day_abs_share = 0.069842
fresh top_day_abs_share = 0.085609

O4 max_abs_daily_nav_return = 0.038982
fresh max_abs_daily_nav_return = 0.041689
```

判断：

```text
fresh qlib 收益略高；
O4 风险/动作/换手略优；
两者没有出现明显 PnL 极端集中；
实际交易路径不同，active action overlap count = 15。
```

## 6. 只读安全边界

执行报告与审计产物声明：

```text
no_training = true
no_tuning = true
no_score_modification = true
no_rule_change = true
no_frontend_api_provider_accepted_latest_monitor_trading = true
```

未发现：

```text
训练 qlib / LTR；
调参；
新增特征；
改 score / label / sample；
改回放规则；
改默认策略；
改前端/API；
provider refresh / publish；
accepted latest switching；
monitor scan/config/alerts；
broker/orders/quick-trade；
真实买卖建议或收益承诺。
```

## 7. 审查判断

本轮证据允许进入后续默认策略讨论。

理由：

- 使用了 repaired fresh qlib C4 replay-ready artifact；
- 未使用旧 S2F 低覆盖 artifact 作为主结论；
- O4 指标复现 O5；
- 同窗口、同费用税费、同 next-day execution、同 replay engine；
- accounting 全部通过；
- coverage 公平性未发现阻断；
- fresh 收益略高，但 O4 回撤/动作/换手更优，存在可讨论的产品权衡。

必须保留的边界：

```text
P1 只允许进入默认策略讨论；
不得直接切换默认策略；
不得把 O4 或 fresh qlib 表述为未来收益更优；
不得输出买卖建议、仓位建议或收益/胜率/上涨概率承诺。
```

## 8. 下一步

允许进入 Phase P2：默认策略讨论工作文档。

P2 必须围绕：

```text
repaired fresh qlib 作为当前默认是否继续保持；
O4 orthogonal LTR 是否作为低回撤/低换手研究候选；
是否需要产品展示“双候选：默认 fresh qlib + O4 风险较稳 LTR”；
是否需要用户明确确认才允许任何默认策略变更。
```

