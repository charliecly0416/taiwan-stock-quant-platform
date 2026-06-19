# Phase C0/C1 审查结论

生成日期：2026-06-15

审查对象：

```text
docs/tw_fresh_top50_coverage_repair/PHASEC0_COVERAGE_AUDIT_EXECUTION_REPORT_CN.md
docs/tw_fresh_top50_coverage_repair/PHASEC1_REPAIR_AND_REPLAY_EXECUTION_REPORT_CN.md
data_tw/experiments/fresh_top50_coverage_repair/
```

依据文档：

```text
docs/tw_fresh_top50_coverage_repair/PHASEC0_C1_WORKDOC_CN.md
docs/tw_fresh_top50_coverage_repair/FRESH_TOP50_COVERAGE_REPAIR_MAINLINE_CN.md
docs/tw_phase1c_anchor_reproduction/PHASEA2_REVIEW_AND_ANCHOR_CARD_CN.md
```

## 1. 审查结论

结论：

```text
C0 覆盖审计通过；
C1 full universe 覆盖修复与只读 replay 基本通过；
C1 common universe 对照需修订，不得直接进入 C2 前端影响判断；
不得改前端，不得切换默认策略。
```

推荐 gate：

```text
phase_c1_full_repair_pass_common_universe_revision_required
```

## 2. C0 审查

C0 通过。

覆盖不足原因已查清：

```text
fresh raw qlib score:             30750 rows, daily 150 / 150 / 150
S2B post-filter score:            22613 rows, daily 88 / 109 / 150
S2D replay-ready adaptive:        22613 rows, daily 88 / 109 / 150
old Phase1C frozen score:         30475 rows, daily 147 / 149 / 150
```

missing reason：

```text
missing_fresh_raw_qlib_score:                     0
filtered_by_s2b_post_score_universe_policy:    7952
present_post_filter_but_missing_replay_ready:     0
raw_top150_missing_local_price:                   0
fresh_replay_ready_not_in_old_phase1c:            90
```

判断：

```text
fresh top50 coverage 不足来自 S2B post-score universe filter；
raw fresh qlib score 和本地价格具备离线修复基础；
未发现 C0 训练、回放、改源 artifact 或触发线上链路。
```

## 3. C1 通过项

### 3.1 Full universe 覆盖修复通过

C1 repaired coverage：

```text
daily rows: 150 / 150.0 / 150
row_count: 30750
```

达到工作文档要求：

```text
min >= 145
median >= 149
max <= 150
```

### 3.2 Full universe replay 通过

C1 full universe：

| method | fee_tax_adjusted_net_return | max_drawdown | action_count |
| --- | ---: | ---: | ---: |
| phase1c_anchor_simple | 0.721631 | -0.050830 | 405 |
| original_fresh_top50_adaptive | 0.662457 | -0.088396 | 410 |
| repaired_fresh_top50_adaptive | 0.801662 | -0.085205 | 410 |
| original_fresh_ltr | 0.544381 | -0.132896 | 408 |

判断：

```text
full universe 下 repaired fresh top50 adaptive 超过 Phase1C anchor；
coverage 缺陷修复后，原先 “fresh full universe 弱于 Phase1C” 的结论不能继续直接使用。
```

### 3.3 Replay 口径与安全边界通过

C1 next-day audit：

```text
active_action_count: 410
execution_date_after_signal_date: True
missing_price_days: 0
skipped_trade_count: 0
last_day_new_trade_without_next_price_count: 0
```

只读安全边界未发现越界：

```text
未训练 qlib/LTR
未改 Phase1C anchor
未改费用税费 / next-day execution / 持仓数量 / 窗口
未改前端/API
未触发 provider / accepted latest / monitor / broker / orders / quick-trade
```

安全关键词检索只命中否定性说明或历史回放字段。

## 4. C1 需修订项

### 4.1 Common universe 口径漂移

Phase A2 冻结的 Phase1C common anchor 是：

```text
Phase1C anchor common return: 0.641235
Phase1C anchor common max DD: -0.076739
common universe key count: 22474
```

但 C1 报告中的 common universe 使用：

```text
Phase1C anchor common return: 0.697914
Phase1C anchor common max DD: -0.076583
```

这说明 C1 common universe 不是 Phase A2 / S2F 冻结的 common universe。

这不一定说明 C1 replay 错误，但必须修订说明：

- C1 common universe 的 key 定义；
- C1 common universe key count；
- 为什么 Phase1C common return 从 `0.641235` 变为 `0.697914`；
- C1 common 是否只是 `Phase1C ∩ original fresh top50 ∩ repaired fresh top50`，而不是 S2F 四策略 common；
- C2 应采用哪个 common universe 回答“repaired fresh top50 是否追上 Phase1C anchor”。

修订前，不得用当前 C1 common universe 表做前端影响判断。

### 4.2 必须补双口径 common universe

为了避免口径混淆，C1 修订版应同时输出：

1. `frozen_s2f_common_universe`

```text
沿用 Phase A2 / S2F common universe key count = 22474；
至少报告 Phase1C anchor、original fresh top50、repaired fresh top50。
```

2. `repaired_pairwise_common_universe`

```text
Phase1C anchor ∩ original fresh top50 ∩ repaired fresh top50；
必须报告 key count 和过滤影响。
```

只有这样 C2 才能区分：

```text
修复后 full universe 增益；
冻结 common universe 下的排序/回放差异；
repaired pairwise common 下的覆盖过滤影响。
```

### 4.3 `feature_complete=0` 需要解释

`phasec1_coverage_by_day.csv` 前几日显示：

```text
2025-07-01 repaired_rows=150 adaptive_nonnull=149 feature_complete=0
2025-07-02 repaired_rows=150 adaptive_nonnull=149 feature_complete=0
2025-07-03 repaired_rows=150 adaptive_nonnull=149 feature_complete=0
2025-07-04 repaired_rows=150 adaptive_nonnull=149 feature_complete=0
```

但 repaired artifact 中 `ret20 / volatility20 / TWII_ret20` 等 adaptive score 所需字段存在，且 `adaptive_score_baseline` 大多非空。

修订版需说明：

- `feature_complete` 字段定义；
- 它是否指 LTR 全 34 特征完整，而不是 top50 adaptive 必需特征完整；
- replay 是否只依赖 `adaptive_score_baseline`、price 和 next-day execution；
- `adaptive_nonnull=149` 的单日缺失是否影响 top10/position selection；
- 是否存在 repaired rows 进入候选但 adaptive score 缺失。

该项不阻断 full replay 结果，但必须补清楚，避免把“覆盖 150”误解为“所有特征全完整”。

### 4.4 C1 执行顺序偏离

工作文档要求：

```text
C1 只能在 C0 审查通过后执行。
```

当前 C0 与 C1 报告同批生成，未等待独立 C0 审查 gate。考虑到 C0 结果清楚、C1 未触发禁用链路，本次不要求废弃 C1；但后续不得跳过 gate。

## 5. 前端影响初判

基于已通过的 full universe 结果，可以初步判断：

```text
fresh top50 覆盖缺陷修复后，repaired fresh top50 adaptive full universe return 高于 Phase1C anchor。
```

但由于 common universe 口径未修订，暂不能完成 C2 最终判断：

```text
Phase1C LTR simple 当前前端默认展示是否需要调整。
```

在 C1 修订前：

```text
不得改前端；
不得切换默认策略；
不得宣称 repaired fresh top50 已全面超过 Phase1C anchor；
只能说 full universe 修复结果显示 fresh top50 有明显改善。
```

## 6. 修订要求

执行者应提交 C1 修订或补充说明：

```text
docs/tw_fresh_top50_coverage_repair/PHASEC1_REPAIR_AND_REPLAY_EXECUTION_REPORT_CN.md
```

或新增：

```text
docs/tw_fresh_top50_coverage_repair/PHASEC1_COMMON_UNIVERSE_REVISION_CN.md
```

必须补充产物：

```text
phasec1_frozen_s2f_common_universe_metrics.csv
phasec1_repaired_pairwise_common_universe_metrics.csv
phasec1_common_universe_key_audit.csv
phasec1_feature_complete_definition_audit.csv
```

## 7. 最终结论

```text
C0 通过；
C1 full universe 覆盖修复通过；
C1 common universe 对照需修订；
C2 前端决策暂缓；
只读安全边界通过。
```
