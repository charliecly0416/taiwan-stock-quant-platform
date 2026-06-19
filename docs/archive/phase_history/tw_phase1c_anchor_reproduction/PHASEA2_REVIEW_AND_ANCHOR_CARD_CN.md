# Phase A2 审查与 Anchor Card

生成日期：2026-06-15

审查对象：

```text
docs/tw_phase1c_anchor_reproduction/PHASEA1_ANCHOR_REPRODUCTION_EXECUTION_REPORT_CN.md
docs/tw_phase1c_anchor_reproduction/PHASEA1_WORKDOC_CN.md
data_tw/experiments/phase1c_anchor_reproduction/
```

## 1. 审查结论

结论：

```text
Phase A1 通过；
Phase1C anchor 可冻结为研究基准；
不得默认化；
不得切换默认策略。
```

推荐 gate：

```text
phase_a2_anchor_card_frozen_research_benchmark_only
```

## 2. 通过项

### 2.1 Anchor identity 一致

A1 核对结果全部通过：

```text
candidate_id: head10_all_l31_alpha0.7_top50_only
model_id: head10_all_l31
score_column: score_head10_all_l31_alpha0.7_top50_only
blend_alpha: 0.7
preserve_scope: top50_only
label_col: relevance_10d_top_heavy
num_leaves: 31
learning_rate: 0.03
n_estimators: 120
random_state: 42
```

未发现执行者替换 score column、label、feature、窗口或模型配置。

### 2.2 Row-level score reproduction 通过

score reproduction：

```text
row_count: 152249
metric_rows: 24
score_column: score_head10_all_l31_alpha0.7_top50_only
max_absolute_difference: 4.440892098500626e-16
mean_absolute_difference: 4.192248400277284e-17
tolerance: 0.0007
pass: yes
```

这满足 Phase3A0 frozen Phase1C row-level score 复刻要求。

### 2.3 同窗口 full universe 指标完全复现

窗口：

```text
2025-07-01..2026-05-07
```

Full universe：

| method | fee_tax_adjusted_net_return | max_drawdown | action_count |
| --- | ---: | ---: | ---: |
| old_qlib_new_ltr_phase1c_simple | 0.721631 | -0.050830 | 405 |
| fresh_qlib_top50_adaptive_baseline | 0.662457 | -0.088396 | 410 |
| fresh_ltr_simple | 0.544381 | -0.132896 | 408 |
| fresh_ltr_turnover_controlled | 0.615059 | -0.111310 | 63 |

所有 diff 均为 0。

### 2.4 Common universe 指标完全复现

common universe key 数：

```text
22474
```

Common universe：

| method | fee_tax_adjusted_net_return | max_drawdown | action_count |
| --- | ---: | ---: | ---: |
| old_qlib_new_ltr_phase1c_simple | 0.641235 | -0.076739 | 405 |
| fresh_qlib_top50_adaptive_baseline | 0.625943 | -0.088431 | 410 |
| fresh_ltr_simple | 0.544381 | -0.132896 | 408 |
| fresh_ltr_turnover_controlled | 0.615059 | -0.111310 | 63 |

所有 diff 均为 0。

### 2.5 Next-day accounting 通过

```text
active_action_count: 405
execution_date_after_signal_date: True
execution_date_not_after_signal_violations: 0
missing_price_days: 0
skipped_trade_count: 0
last_day_new_trade_without_next_price_count: 0
```

### 2.6 真实 PnL 与异常审计已补

A1 已输出逐票、逐日真实 PnL contribution，不是 sell-notional proxy。

主要集中度：

```text
top_symbol_abs_share_of_total_net_pnl: 0.155560
top_day_abs_share_of_total_net_pnl:    0.158422
max_abs_daily_nav_return:              0.031448
```

按 A1 阈值未触发异常集中，但仍应在 anchor card 中保留“贡献集中需持续审计”的风险说明。

## 3. 只读安全边界

未发现越界：

```text
未训练 qlib
未训练 LTR
未改窗口 / feature / label / score column
未使用 Q0/L1-L4、T2/T2R 或 tw_qlib_oos_ltr_stacking 产物作为 A1 输入
未触发 provider / accepted latest / monitor / broker / orders / quick-trade / frontend / API 链路
```

安全关键词检索只命中否定性声明，未发现真实交易建议或动作入口。

## 4. Anchor Card

```text
策略名称：Phase1C qlib-preserving LTR rerank anchor
定位：研究候选 / anchor benchmark
candidate_id: head10_all_l31_alpha0.7_top50_only
model_id: head10_all_l31
score_column: score_head10_all_l31_alpha0.7_top50_only
blend_alpha: 0.7
preserve_scope: top50_only
label_col: relevance_10d_top_heavy
回放窗口：2025-07-01..2026-05-07
回放口径：next-day execution, fee_rate 0.001425, tax_rate 0.003, target positions count 10
```

Full universe：

```text
Phase1C anchor return:      0.721631
Phase1C anchor max DD:      -0.050830
Phase1C anchor actions:     405
fresh top50 return:         0.662457
fresh top50 max DD:         -0.088396
fresh top50 actions:        410
relative return:            +0.059174
relative drawdown:          +0.037566
relative actions:           -5
```

Common universe：

```text
common universe key count:  22474
Phase1C anchor return:      0.641235
Phase1C anchor max DD:      -0.076739
Phase1C anchor actions:     405
fresh top50 return:         0.625943
fresh top50 max DD:         -0.088431
fresh top50 actions:        410
relative return:            +0.015292
relative drawdown:          +0.011692
relative actions:           -5
```

主要风险：

```text
common universe 下优势较小，约 +1.53 个百分点；
优势对 universe 口径敏感；
仍只覆盖单一 final test 窗口；
需要作为 anchor benchmark，而不是默认策略；
后续新 LTR / OOS stacking 必须至少超过该 anchor，且需同时赢 common universe、回撤、费用税费和稳定性。
```

普通用户一句话：

```text
Phase1C anchor 可以复现，作为研究基准有效；它相对当前 fresh qlib/top50 adaptive 有小幅优势，但共同股票池优势不大，不能直接切成默认策略。
```

## 5. 后续使用规则

后续任何新策略对比 Phase1C anchor 时，必须至少报告：

- 同窗口 full universe；
- 同窗口 common universe；
- fee/tax adjusted return；
- max drawdown；
- action_count；
- next-day accounting；
- 真实 PnL contribution；
- 是否使用相同 price / replay 口径；
- 是否相对 Phase1C anchor 有稳定增益。

不得将 Phase1C anchor 与 Q0/L1-L4、T2/T2R 等补强主线新模型混名。

## 6. 最终建议

```text
冻结 Phase1C anchor；
保留 fresh qlib/top50 adaptive 作为默认研究候选；
Phase1C anchor 作为所有新 LTR / OOS stacking 的最低比较锚点；
不进入产品默认化。
```
