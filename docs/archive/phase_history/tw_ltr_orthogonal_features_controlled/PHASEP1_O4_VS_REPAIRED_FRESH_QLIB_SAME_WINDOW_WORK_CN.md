# Phase P1：O4 Orthogonal LTR vs Repaired Fresh Qlib 同口径对比工作文档

生成日期：2026-06-15

## 1. 背景

Phase O6 已接受：

```text
O4 orthogonal LTR 可以替代原 Phase1C simple LTR，作为 LTR 研究展示/对照候选；
当前产品默认策略仍保持 fresh qlib / rank_rotate_top50_adaptive_score；
不得直接改默认。
```

但 O6 的主对照是：

```text
O4 orthogonal LTR vs Phase1C simple LTR
```

不是正式的：

```text
O4 orthogonal LTR vs 当前默认 fresh qlib Top50 adaptive
```

已有 S2F 同窗口复核显示：

```text
fresh_qlib_top50_adaptive_baseline return = 0.662457
```

但该 S2F fresh qlib coverage 为：

```text
88 / 109 / 150
```

这不是后续 coverage repair 后的 replay-ready 口径。因此不能直接作为最终默认策略比较证据。

本 P1 只做一件事：

```text
使用最新 repaired fresh top50 replay-ready artifact，
与 O4 orthogonal LTR 在同窗口、同回放引擎、同费用税费、同 next-day execution 下比较。
```

## 2. 目标

回答一个明确问题：

```text
在 2025-07-01..2026-05-07 同窗口、同 replay accounting 下，
O4 orthogonal LTR 是否优于 repaired fresh qlib Top50 adaptive？
```

必须同时比较：

- fee/tax adjusted net return；
- max drawdown；
- action_count；
- turnover_proxy；
- fee_and_tax；
- next-day accounting；
- coverage；
- PnL concentration；
- 是否存在因 universe / coverage 口径导致的不公平。

## 3. 输入 Artifact

### 3.1 O4 Orthogonal LTR

使用已通过 O6 的 artifact：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_row_scores.csv
```

O5 replay 参考 artifact：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/
```

O4 score column：

```text
phaseo4_treatment_ltr_score_top50_preserve
```

如果执行者发现实际 replay 需要先由：

```text
phaseo4_treatment_ltr_score
```

重新构造 top50 preserve column，必须说明逻辑，并验证与 O5 指标一致。

### 3.2 Repaired Fresh Qlib Top50 Adaptive

必须使用 coverage repair 后的 replay-ready artifact。

执行者需要先定位 artifact，候选来源包括但不限于：

```text
data_tw/experiments/tw_fresh_top50_coverage_repair/
data_tw/experiments/ltr_qlib_split_aligned_retrain/
docs/tw_fresh_top50_coverage_repair/
```

不得使用 coverage 为 `88 / 109 / 150` 的旧 S2F fresh qlib artifact 作为最终比较。

合格 repaired fresh qlib artifact 至少应满足：

```text
target window coverage approximately 148 / 149 / 150
replay-ready clean
future leakage = 0
instrument violation = 0
accepted universe violation = 0
price missing = 0
next execution price missing = 0
adaptive score missing = 0
```

如果找不到合格 artifact，必须停止并报告，不得退回旧 S2F 口径。

## 4. 固定回放合同

必须固定：

```text
window: 2025-07-01..2026-05-07
execution: next-day execution
initial_equity: 1000000
fee_rate: 0.001425
tax_rate: 0.003
target_position_count: 10
lot_size: 使用项目既有同窗口 replay 口径
price_source: 与 O5 / repaired fresh qlib replay-ready 合同一致
```

不得改变：

- O4 score；
- repaired fresh qlib score；
- candidate universe；
- Top50 preserve / adaptive score 规则；
- 买卖规则；
- 手续费税费；
- next-day execution；
- target position count；
- 价格口径。

## 5. 执行内容

### 5.1 Artifact 定位与合同审计

输出：

```text
phasep1_artifact_inventory.csv
phasep1_input_contract_audit.json
```

审计内容：

- O4 artifact 路径；
- fresh qlib repaired artifact 路径；
- 日期范围；
- row count；
- daily coverage min/median/max；
- score columns；
- duplicate key count；
- missing price / next execution price；
- 是否 replay-ready；
- 是否来自 coverage repair 后产物。

### 5.2 同窗口 replay

使用同一 replay engine 或等价复用 O5 replay engine。

输出：

```text
phasep1_same_window_metrics.csv
phasep1_same_window_daily_nav.csv
phasep1_same_window_action_audit.csv
phasep1_next_day_accounting_audit.csv
```

至少包含两组：

```text
o4_orthogonal_ltr
repaired_fresh_qlib_top50_adaptive
```

可以包含审计基线：

```text
phase1c_simple_ltr
old_s2f_fresh_qlib_top50_adaptive
```

但主结论只能基于 O4 与 repaired fresh qlib。

### 5.3 差异与风险审计

输出：

```text
phasep1_relative_comparison.csv
phasep1_pnl_contribution_by_symbol.csv
phasep1_pnl_contribution_by_day.csv
phasep1_pnl_concentration_summary.csv
phasep1_coverage_fairness_audit.json
```

必须回答：

- O4 是否收益更高；
- O4 是否回撤更深；
- O4 是否动作更多；
- O4 是否换手更高；
- O4 收益是否集中于少数股票或少数日期；
- repaired fresh qlib 是否因 coverage 口径弱化；
- 两者实际交易路径是否受到 universe 差异影响。

## 6. 禁止事项

P1 严禁：

```text
训练 qlib
训练 LTR
调参
新增正交特征
改 score
改 label
改 sample
改回放买卖规则
改默认策略
改前端/API
provider refresh / publish
accepted latest switching
monitor scan / config / alerts
broker / orders / quick-trade
target position / target weight
输出真实买卖建议
收益、胜率、上涨概率承诺
```

## 7. 输出报告

执行者必须输出：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP1_O4_VS_REPAIRED_FRESH_QLIB_SAME_WINDOW_EXECUTION_REPORT_CN.md
```

报告结构：

1. 执行摘要；
2. 使用 artifact；
3. replay 合同；
4. coverage 审计；
5. 同窗口 metrics；
6. O4 vs repaired fresh qlib 差异；
7. 回撤、换手、动作风险；
8. PnL concentration；
9. next-day accounting；
10. 是否存在口径不公平；
11. 是否允许进入后续默认策略讨论；
12. 是否需要用户确认。

## 8. 审查者检查点

审查者必须检查：

- 是否确实使用 repaired fresh qlib replay-ready artifact；
- 是否没有退回旧 S2F 88/109/150 coverage；
- O4 指标是否能复现 O5；
- replay 口径是否一致；
- 是否没有训练/调参/改前端/API/provider/交易链路；
- 是否同时报告收益、回撤、动作、换手、费用和 accounting；
- 是否避免把结果写成真实投资建议；
- 是否符合用户第一性原则。

审查结论只能是：

```text
通过：允许进入后续默认策略讨论
不通过：指出口径或 artifact 问题
需要用户确认
```

## 9. 给执行者的一句话

```text
请按 docs/tw_ltr_orthogonal_features_controlled/PHASEP1_O4_VS_REPAIRED_FRESH_QLIB_SAME_WINDOW_WORK_CN.md 执行 P1，只做 O4 orthogonal LTR 与 repaired fresh qlib Top50 adaptive 的同窗口只读对比，必须使用 coverage repair 后 replay-ready fresh qlib artifact，不得训练、调参、改规则、改前端/API/provider/accepted latest/monitor 或触发任何交易链路。
```

## 10. 给审查者的一句话

```text
请按 docs/tw_ltr_orthogonal_features_controlled/PHASEP1_O4_VS_REPAIRED_FRESH_QLIB_SAME_WINDOW_WORK_CN.md 审查 P1 执行报告，重点确认 repaired fresh qlib artifact 口径、O4 指标复现、同窗口同回放合同、coverage 公平性、回撤/换手风险和只读安全边界，并判断是否允许进入后续默认策略讨论。
```
