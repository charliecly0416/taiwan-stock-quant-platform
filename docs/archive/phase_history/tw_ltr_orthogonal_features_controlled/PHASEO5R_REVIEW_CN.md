# Phase O5R 审查结论：Common Universe Audit Repair

生成日期：2026-06-15

审查对象：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEO5R_COMMON_UNIVERSE_AUDIT_REPAIR_WORK_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO5R_COMMON_UNIVERSE_AUDIT_REPAIR_EXECUTION_REPORT_CN.md
scripts/repair_orthogonal_ltr_phase_o5r_common_universe_audit.py
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/
```

## 1. 结论

O5R 通过。

推荐 gate：

```text
phase_o5r_common_universe_audit_repaired
```

O5R 已补齐 O5 缺失的 common universe action/nav 审计，证明 O5 full/common 指标完全相同不是审计遗漏，而是 pairwise common universe 没有改变实际买入、持仓路径与 NAV。

允许进入：

```text
Phase O6：审查与决策
```

但 O5R 不等于允许产品化，不得改前端默认策略，不得触发 provider/accepted latest/monitor/交易链路。

## 2. 合同核对

O5R 使用的输入、窗口和回放口径与 O5/O5R 工作文档一致：

```text
window: 2025-07-01..2026-05-07
control score: score_head10_all_l31_alpha0.7_top50_only
treatment score: phaseo4_treatment_ltr_score
treatment replay score: phaseo4_treatment_ltr_score_top50_preserve
preserve_scope: top50_only
fee_rate: 0.001425
tax_rate: 0.003
target_position_count: 10
```

未发现：

```text
重训 qlib/LTR；
修改 Phase1C anchor score；
修改 O4 treatment score；
修改 label/window/feature/replay rule；
新增 filter/threshold/market gate/stop loss/take profit/turnover rule；
改前端/API/provider/accepted latest/monitor/交易链路。
```

## 3. O5 阻塞点是否修复

O5 原阻塞点是：

```text
full/common metrics 完全相同，但 common_key_count 只有 10110，缺少 action/nav 证据。
```

O5R 已补齐：

```text
phaseo5r_full_action_audit.csv
phaseo5r_common_action_audit.csv
phaseo5r_action_diff_audit.csv
phaseo5r_action_diff_summary.csv
phaseo5r_full_daily_nav.csv
phaseo5r_common_daily_nav.csv
phaseo5r_nav_diff_audit.csv
phaseo5r_nav_diff_summary.csv
```

关键结果：

```text
action diff total = 0
historical_add diff = 0
historical_risk_reduce diff = 0
historical_skip diff = 0

O4 daily_equity_max_abs_diff = 0.0
O4 daily_cash_max_abs_diff = 0.0
O4 daily_holding_count_max_abs_diff = 0

Phase1C daily_equity_max_abs_diff = 0.0
Phase1C daily_cash_max_abs_diff = 0.0
Phase1C daily_holding_count_max_abs_diff = 0
```

因此可以接受：

```text
O5 full/common replay metrics 相同是可复现的。
```

## 4. Common Universe 解释

O5R 确认：

```text
full_key_count = 30475
common_key_count = 10110
excluded_key_count = 20365
excluded_treatment_top50_preserve_masked = 20365
excluded_price_replay_unavailable = 0
```

也就是说，本轮 pairwise common 几乎完全由 treatment top50-preserve 定义收缩，不是价格缺失或 replay unavailable。

Phase1C：

```text
selected_top50_changed_days = 110
selected_top10_changed_days = 0
removed_from_selected_top50_total = 140
```

O4 treatment：

```text
selected_top50_changed_days = 0
selected_top10_changed_days = 0
removed_from_selected_top50_total = 0
```

Phase1C 有 84 条 `historical_risk_reduce` signal key 不在 common key 中，但 action diff 为 0，NAV diff 为 0，因此这些 signal key 缺失没有改变实际 replay 路径。

## 5. 仍需保留的解释边界

O5R 修复的是审计闭环，不是策略优劣决策。

当前可以说：

```text
O4 treatment 在同窗口 full universe 下相对 Phase1C anchor return +0.078698；
O4 treatment 的 max drawdown 更深，-0.074962 vs -0.050830；
pairwise common universe 没有改变本轮实际交易路径，因此 common metrics 与 full metrics 相同；
next-day accounting 通过。
```

当前不应说：

```text
O4 treatment 已可进入前端默认；
O4 treatment 已可产品化；
common universe 独立证明了 treatment 稳健优于 control；
正交特征已完成最终主线结论。
```

这些必须留到 O6 决策。

## 6. 下一步

允许执行 Phase O6。

O6 只能形成审查决策记录：

```text
通过进入只读产品化设计主线；
或不通过并收尾为数据与实验结论；
或要求补充审计。
```

O6 禁止直接改前端默认、provider、accepted latest、monitor 或交易链路。
