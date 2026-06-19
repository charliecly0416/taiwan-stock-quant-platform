# Phase C1 修订版审查结论

生成日期：2026-06-15

审查对象：

```text
docs/tw_fresh_top50_coverage_repair/PHASEC1_REPAIR_AND_REPLAY_EXECUTION_REPORT_CN.md
data_tw/experiments/fresh_top50_coverage_repair/
```

## 1. 审查结论

结论：

```text
C1 修订版通过；
common universe 口径漂移问题已修复；
feature_complete 定义已解释清楚；
可以进入 C2 审查与前端影响判断；
但 C1 本身不得改前端或切换默认策略。
```

推荐 gate：

```text
phase_c1_repair_and_common_revision_review_passed_proceed_to_c2
```

## 2. 已修复问题

### 2.1 Common universe 双口径已补齐

修订版明确输出两套 common universe。

Frozen S2F common universe：

```text
definition: Phase1C anchor ∩ original fresh top50 ∩ original fresh LTR
key count: 22474
Phase1C return / max DD: 0.641235 / -0.076739
repaired fresh top50 return / max DD: 0.625943 / -0.088431
```

该口径与 Phase A2 / S2F 冻结 common anchor 对齐，适合用于 C2 判断与历史 anchor 的可比性。

Repaired pairwise common universe：

```text
definition: Phase1C anchor ∩ original fresh top50 ∩ repaired fresh top50
key count: 22523
Phase1C return / max DD: 0.697914 / -0.076583
repaired fresh top50 return / max DD: 0.663150 / -0.088516
```

该口径只用于解释 repaired 覆盖过滤影响，不应替代 frozen S2F common。

### 2.2 Feature complete 定义已补齐

修订版说明：

```text
feature_complete = LTR 全特征合同完整
fresh top50 adaptive replay 不依赖 feature_complete
replay 依赖 adaptive_score_baseline、本地价格、next-day execution
adaptive_score_baseline 缺失行会被 replay ranking dropna(score_col) 排除
```

因此早期 `feature_complete=0` 不阻断 repaired fresh top50 replay。该解释可接受。

## 3. Full Universe 结论

repaired fresh top50 coverage：

```text
150 / 150.0 / 150
```

Full universe metrics：

| method | return | max_drawdown | action_count |
| --- | ---: | ---: | ---: |
| Phase1C anchor | 0.721631 | -0.050830 | 405 |
| original fresh top50 | 0.662457 | -0.088396 | 410 |
| repaired fresh top50 | 0.801662 | -0.085205 | 410 |

判断：

```text
覆盖修复后，fresh top50 adaptive 在 full universe 下超过 Phase1C anchor；
原先 full universe fresh baseline 偏弱，确实受到 replay-ready coverage 缺陷影响。
```

## 4. Common Universe 结论

Frozen S2F common 下：

```text
Phase1C anchor:        0.641235 / -0.076739
repaired fresh top50:  0.625943 / -0.088431
relative return:      -0.015292
```

Pairwise common 下：

```text
Phase1C anchor:        0.697914 / -0.076583
repaired fresh top50:  0.663150 / -0.088516
relative return:      -0.034764
```

判断：

```text
common universe 下 repaired fresh top50 仍未超过 Phase1C anchor；
但 full universe 下 repaired fresh top50 已超过 Phase1C anchor。
```

C2 需要基于这一分歧判断前端默认展示和用户解释口径。

## 5. Replay 与风险审计

Next-day accounting：

```text
active_action_count: 410
execution_date_after_signal_date: True
missing_price_days: 0
skipped_trade_count: 0
last_day_new_trade_without_next_price_count: 0
```

Outlier audit：

```text
top_symbol_abs_share_of_total_net_pnl: 0.112857
top_day_abs_share_of_total_net_pnl:    0.186634
max_abs_daily_nav_return:              0.041689
```

未发现异常集中或 accounting 阻断项。

## 6. 只读安全边界

未发现越界：

```text
未训练 qlib/LTR
未改 Phase1C anchor
未改费用税费 / next-day execution / 持仓数量 / 窗口
未改前端/API
未触发 provider / accepted latest / monitor / broker / orders / quick-trade
```

安全关键词检索只命中否定性说明。

## 7. C2 必须回答

C2 可以继续，但必须明确回答：

1. repaired fresh top50 full universe 已超过 Phase1C anchor，是否说明 fresh top50 原 full universe 对比曾被 coverage 缺陷低估；
2. frozen S2F common 与 repaired pairwise common 下 fresh top50 仍低于 Phase1C anchor，如何解释排序能力与覆盖收益的差异；
3. 前端默认展示是否应继续保留 Phase1C，还是切回 / 展示 repaired fresh top50；
4. 若要改前端，必须另开前端只读展示合同，不得由 C1 直接执行；
5. 是否可以进入正交数据主线。

## 8. 最终建议

```text
C1 修订版通过；
进入 C2 审查；
前端和默认策略仍冻结，等待 C2 结论。
```
