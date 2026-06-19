# Phase O5R 工作文档：Common Universe Audit Repair

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/ORTHOGONAL_LTR_CONTROLLED_MAINLINE_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO5_CONTROLLED_REPLAY_EVALUATION_WORK_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO5_REVIEW_CN.md
```

## 1. O5R 目标

O5R 只做一件事：

```text
补齐 O5 pairwise common universe 的可审计证据链。
```

O5R 不重新训练、不重新选特征、不改变模型、不改变回放规则、不改变 Phase1C anchor。

目标 gate：

```text
phase_o5r_common_universe_audit_repaired
```

## 2. 固定输入

Control 固定：

```text
score column: score_head10_all_l31_alpha0.7_top50_only
source:
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
```

Treatment 固定：

```text
score column: phaseo4_treatment_ltr_score
source:
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_row_scores.csv
```

Treatment replay column 固定：

```text
phaseo4_treatment_ltr_score_top50_preserve
definition:
phaseo4_treatment_ltr_score where qlib_rank <= 50
```

窗口固定：

```text
2025-07-01..2026-05-07
```

回放口径固定：

```text
next-day execution
fee_rate = 0.001425
tax_rate = 0.003
target_position_count = 10
preserve_scope = top50_only
```

## 3. 必须补齐的审计

### 3.1 Common universe key audit

必须输出：

```text
full_key_count
common_key_count
excluded_key_count
excluded_key_count_by_date
excluded_key_count_by_symbol
excluded_reason
```

至少区分：

```text
control score missing
treatment score missing
treatment top50-preserve masked
price/replay unavailable
```

### 3.2 Full vs common selected candidate audit

对每个交易日、每个方法输出：

```text
date
method
full_selected_top50_count
common_selected_top50_count
removed_from_selected_top50_count
removed_symbols
selected_top10_changed
selected_top50_changed
```

必须明确说明：

```text
common universe 是否改变 Phase1C 的 top50 候选；
common universe 是否改变 O4 treatment 的 top50 候选；
common universe 是否改变实际 top10 持仓候选。
```

### 3.3 Full vs common action audit

必须分别输出 full 和 common replay 的 action 明细，不得只输出 full：

```text
phaseo5r_full_action_audit.csv
phaseo5r_common_action_audit.csv
phaseo5r_action_diff_audit.csv
```

action diff 至少包含：

```text
method
signal_date
execution_date
symbol
action
present_in_full
present_in_common
reason
```

必须单独汇总：

```text
historical_add diff count
historical_risk_reduce diff count
historical_skip diff count
```

### 3.4 Full vs common NAV audit

必须分别输出：

```text
phaseo5r_full_daily_nav.csv
phaseo5r_common_daily_nav.csv
phaseo5r_nav_diff_audit.csv
```

若 full/common metrics 完全相同，必须用 nav diff 证明：

```text
daily equity max_abs_diff = 0
daily cash max_abs_diff = 0
daily holding_count max_abs_diff = 0
```

若不完全相同，必须更新 common universe 指标，并解释差异来源。

### 3.5 Next-day accounting

full 与 common 都必须报告：

```text
execution_date_after_signal_date
execution_date_not_after_signal_violations
missing_price_days
skipped_trade_count
last_day_new_trade_without_next_price_count
```

任何 violation 都必须阻断 gate。

## 4. 报告要求

O5R 执行报告必须明确回答：

```text
1. O5 full/common 指标完全相同是否真实可复现？
2. 如果相同，是因为 common 没有改变买入/持仓/NAV，还是因为审计遗漏？
3. Phase1C 被 common 移除的 84 条 risk_reduce signal 是否影响实际持仓路径？
4. O4 treatment 是否因 top50-preserve 使 pairwise common 对自身天然非约束？
5. O5 的 +0.078698 full return 差异是否仍可作为 full universe 观察结果？
6. 是否可以把 common universe 结果作为正式结论？
```

## 5. 禁止事项

O5R 禁止：

```text
重新训练 qlib 或 LTR；
修改 Phase1C anchor score；
修改 O4 treatment score；
修改 label、训练窗口、测试窗口；
新增 filter、threshold、market gate、stop loss、take profit、turnover rule；
更换 universe 定义来追求更好结果；
把 ranking metric 当作策略优劣主证据；
改前端/API/provider/accepted latest/monitor/交易链路；
触发任何真实交易、下单、quick-trade、broker 动作。
```

## 6. 放行条件

只有同时满足以下条件，O5R 才能放行：

```text
full/common action/nav 均有独立产物；
common universe excluded reason 完整；
next-day accounting full/common 全部通过；
若 full/common 指标相同，已有 action/nav diff 证明；
若 full/common 指标不同，已更新正式 common universe 指标；
没有新增未授权规则；
没有修改任何冻结输入。
```

否则继续阻断，不进入 O6。
