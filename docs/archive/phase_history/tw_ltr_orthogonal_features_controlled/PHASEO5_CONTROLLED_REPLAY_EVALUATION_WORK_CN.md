# Phase O5 工作文档：Controlled Replay Evaluation

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/ORTHOGONAL_LTR_CONTROLLED_MAINLINE_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO4_REVIEW_CN.md
docs/tw_phase1c_anchor_reproduction/PHASEA2_REVIEW_AND_ANCHOR_CARD_CN.md
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_summary.json
```

## 1. O5 启动条件

O4 已通过：

```text
gate: phase_o4_controlled_treatment_ltr_trained
```

O4 已确认：

```text
模型配置与 Phase1C 一致；
训练特征白名单合规；
metadata 未进入模型；
未调参；
未回放；
未改 control。
```

O5 允许启动。

O5 的目标 gate：

```text
phase_o5_controlled_replay_evaluation_completed
```

## 2. O5 目标

O5 只做一件事：

```text
在完全相同回放口径下，
比较 O4 orthogonal treatment LTR 与 Phase1C anchor。
```

O5 不训练模型，不改策略规则，不做默认化决策。

## 3. 主对照

### 3.1 Treatment

Treatment 固定为 O4 输出：

```text
score column: phaseo4_treatment_ltr_score
score artifact:
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_row_scores.csv
model artifact:
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_model.pkl
```

Treatment 定义：

```text
Phase1C 原始 simple LTR 特征 + PIT-safe 法人筹码/融资融券正交训练特征
```

### 3.2 Control

Control 固定为 Phase1C anchor：

```text
candidate_id: head10_all_l31_alpha0.7_top50_only
model_id: head10_all_l31
score_column: score_head10_all_l31_alpha0.7_top50_only
blend_alpha: 0.7
preserve_scope: top50_only
```

Control anchor 指标：

Full universe：

```text
fee_tax_adjusted_net_return: 0.721631
max_drawdown: -0.050830
action_count: 405
```

Common universe：

```text
common universe key count: 22474
fee_tax_adjusted_net_return: 0.641235
max_drawdown: -0.076739
action_count: 405
```

## 4. 评测窗口

O5 必须至少覆盖 Phase1C final test 窗口：

```text
2025-07-01..2026-05-07
```

如执行者希望额外报告训练/验证期或更长窗口，只能作为附录，并且不得替代 final test 同窗口结论。

主结论必须基于：

```text
2025-07-01..2026-05-07 same-window final test
```

## 5. 回放口径

必须与 Phase1C anchor 完全一致：

```text
next-day execution
fee_rate: 0.001425
tax_rate: 0.003
target position count: 10
preserve_scope: top50_only
```

必须保持不变：

```text
执行价口径
交易日历
费用税费
持仓数
买卖规则
top50 rerank / preserve_scope 规则
score ranking 方向
```

禁止新增：

```text
filter
threshold
market gate
turnover rule
stop loss / take profit
top-up 规则
不同股票池
```

## 6. Full / Common Universe

O5 必须同时报告：

```text
full universe
common universe
```

Common universe 至少包含：

```text
Phase1C anchor vs O4 treatment 的共同可 replay key
```

如复用既有 common universe key count，必须说明来源。若重新计算 common universe，必须输出：

```text
common_universe_key_count
excluded_key_count_by_method
excluded_reason
```

不得只用 full universe 得出结论。

## 7. 必须报告的指标

O5 必须报告以下指标。

### 7.1 回放收益与风险

```text
fee_tax_adjusted_net_return
max_drawdown
action_count
buy_count
sell_count
turnover 或 turnover proxy
daily_nav_count
```

### 7.2 Accounting / Replay-ready

```text
next-day accounting pass/fail
execution_date_after_signal_date
execution_date_not_after_signal_violations
missing_price_days
skipped_trade_count
last_day_new_trade_without_next_price_count
```

### 7.3 Ranking / Model Quality

```text
rank_ic_10d
ndcg_at_10
ndcg_at_30
ndcg_at_50
top10/top30/top50 future_excess_return_rank_10d
```

说明：

```text
rank/NDCG 只是辅助；
策略优劣不能只看训练/验证 ranking metric。
```

### 7.4 分段稳定性

必须报告：

```text
yearly performance
monthly performance
market regime segment if available
best/worst month contribution
single-symbol PnL concentration
single-day PnL concentration
```

### 7.5 真实 PnL Contribution

必须使用真实 PnL contribution，不得用 sell-notional proxy。

至少报告：

```text
top_symbol_abs_share_of_total_net_pnl
top_day_abs_share_of_total_net_pnl
max_abs_daily_nav_return
top positive / negative symbols
top positive / negative days
```

### 7.6 正交数据影响审计

必须报告：

```text
missing flag / delay flag 在持仓中的占比
低覆盖股票的持仓/交易/PnL contribution
orthogonal feature importance 与 O4 是否一致
收益是否集中来自少数低覆盖或高覆盖股票
```

重点股票：

```text
TW7769
TW6919
TW3131
TW6683
TW4749
TW6805
TW6446
TW6789
TW6770
```

## 8. 必须输出的产物

推荐输出目录：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/
```

必须输出：

```text
phaseo5_replay_manifest.json
phaseo5_full_universe_metrics.csv
phaseo5_common_universe_metrics.csv
phaseo5_rank_metrics.csv
phaseo5_action_audit.csv
phaseo5_next_day_accounting_audit.csv
phaseo5_daily_nav.csv
phaseo5_monthly_performance.csv
phaseo5_yearly_performance.csv
phaseo5_pnl_contribution_by_symbol.csv
phaseo5_pnl_contribution_by_day.csv
phaseo5_pnl_concentration_summary.csv
phaseo5_low_coverage_impact_audit.csv
phaseo5_common_universe_key_audit.csv
phaseo5_summary.json
```

执行报告必须写到：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEO5_CONTROLLED_REPLAY_EVALUATION_EXECUTION_REPORT_CN.md
```

## 9. O5 禁止事项

严格禁止：

```text
重训 qlib
重训 LTR
改 O4 treatment score
改 Phase1C anchor score
改 label / feature / split / model config
改回放规则
新增 filter / threshold / market gate / turnover rule
用训练窗口收益率替代 final test 证据
只报告收益不报告回撤/动作/费用/turnover
只报告 full universe 不报告 common universe
切换前端默认策略
写 provider / accepted latest
触发 monitor / broker / orders / quick-trade
```

## 10. O5 停止条件

如出现以下任一情况，执行者必须停止：

```text
O4 treatment score 无法与回放样本对齐；
Phase1C anchor score 无法复用；
无法证明同窗口；
无法证明同回放口径；
next-day accounting 违规；
missing price 导致结果不可 replay；
common universe 无法构造；
必须新增 filter 或改规则才有结果；
回放需要 provider refresh / accepted latest 切换；
发现未来函数或 PIT 违规。
```

## 11. O5 判读规则

O5 只输出事实，不做最终默认化决策。

O5 可以初步说明：

```text
treatment 是否在 full universe 优于 control；
treatment 是否在 common universe 优于 control；
treatment 是否增加回撤或 turnover；
treatment 是否依赖少数月份/股票；
treatment 是否受低覆盖正交数据影响。
```

最终是否认为正交数据有效，由 O6 审查决策。

## 12. 给执行者的一句话

```text
请按本文执行 O5：只用 O4 treatment score 与 Phase1C anchor score，在 2025-07-01..2026-05-07 final test 窗口做同回放口径 full/common universe 评测，完整报告费用税费收益、回撤、动作数、turnover、next-day accounting、真实 PnL contribution、分段稳定性和低覆盖影响；不得重训、改回放规则、加 filter、默认化或触发任何 frontend/API/provider/accepted latest/monitor/交易链路。
```
