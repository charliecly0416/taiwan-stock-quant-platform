# Phase P1 执行报告：O4 Orthogonal LTR vs Repaired Fresh Qlib 同窗口只读对比

生成时间：2026-06-15T14:16:02+00:00

## 1. 执行摘要

本轮只做只读同窗口对比，没有训练、调参、改规则、改前端/API/provider/accepted latest/monitor，也没有触发交易链路。

主结论基于 `2025-07-01..2026-05-07`、next-day execution、fee_rate `0.001425`、tax_rate `0.003`、10 档持仓目标的同一 replay engine：

- O4 orthogonal LTR return `0.800329`，max DD `-0.074962`，actions `403`，turnover `39.761877`。
- Repaired fresh qlib Top50 adaptive return `0.801662`，max DD `-0.085205`，actions `410`，turnover `40.750969`。
- O4 - repaired fresh return diff `-0.001333`；O4 未高于 repaired fresh。
- O4 max drawdown 更浅：diff `0.010243`；O4 actions 少 `7`；O4 turnover 较低 `-0.989092`。

## 2. 使用 Artifact

- O4：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_row_scores.csv`，score column `phaseo4_treatment_ltr_score_top50_preserve`。
- Repaired fresh qlib：`data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv`，score column `adaptive_score_baseline`。
- C4 gate：`phase_c4_replay_ready_repair_passed_with_coverage_below_150_explained`。
- `旧 S2F fresh top50 adaptive 仅作审计参照，return `0.662457`，未用于主结论。`

## 3. Replay 合同

```text
window = 2025-07-01..2026-05-07
execution = next-day execution
initial_equity = 1000000
fee_rate = 0.001425
tax_rate = 0.003
target_position_count = 10
lot_size = 10
```

## 4. Coverage 审计

- repaired fresh C4 daily replay-ready rows：`148 / 149.0 / 150`。
- future/instrument violation：`0`；accepted universe violation：`0`。
- missing current price / next execution price / adaptive score：`0 / 0 / 0`。
- 未使用旧 S2F 88/109/150 coverage 作为主结论。

## 5. 同窗口 Metrics

| method | return | max_drawdown | action_count | fee_and_tax | turnover_proxy |
|---|---:|---:|---:|---:|---:|
| O4 orthogonal LTR | 0.800329 | -0.074962 | 403 | 157722.97 | 39.761877 |
| repaired fresh qlib Top50 adaptive | 0.801662 | -0.085205 | 410 | 161853.68 | 40.750969 |

## 6. 差异与风险

- 收益：O4 低 `0.001333`。
- 回撤：O4 max DD `-0.074962`，repaired fresh `-0.085205`，O4 较浅。
- 动作：O4 `403`，repaired fresh `410`，O4 较少。
- 换手：O4 `39.761877`，repaired fresh `40.750969`，O4 较低。

## 7. PnL Concentration

| method | top_symbol_abs_share | top_day_abs_share | max_abs_daily_nav_return |
|---|---:|---:|---:|
| o4_orthogonal_ltr | 0.102661 | 0.069842 | 0.038982 |
| repaired_fresh_qlib_top50_adaptive | 0.106053 | 0.085609 | 0.041689 |

## 8. Next-day Accounting

| method | active_actions | execution_after_signal | missing_price_days | skipped_trade_count | pass |
|---|---:|---|---:|---:|---|
| o4_orthogonal_ltr | 403 | True | 0 | 0 | yes |
| repaired_fresh_qlib_top50_adaptive | 410 | True | 0 | 0 | yes |

## 9. 口径公平性

C4 repaired fresh artifact 已清理 replay-ready 硬条件，daily replay-ready coverage 为 148/149/150，且 price、next execution price、adaptive score 缺失均为 0。
O4 使用冻结 top50-preserve score column；repaired fresh 使用 C4 replay-ready artifact 的 adaptive score，并保持 Top50 adaptive 规则。两者 universe 差异来自冻结产品合同，不是因 fresh coverage 缺口弱化。
实际交易路径不同：`True`；active action overlap count `15`。

## 10. 后续默认策略讨论

本轮证据允许进入后续默认策略讨论，但不直接建议切换默认策略。repaired fresh qlib 在同窗口收益略高，O4 在回撤、动作数和换手上较保守。后续讨论应继续保持只读产品边界。

## 11. 输出产物

- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_o4_vs_repaired_fresh_qlib_same_window/phasep1_artifact_inventory.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_o4_vs_repaired_fresh_qlib_same_window/phasep1_input_contract_audit.json`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_o4_vs_repaired_fresh_qlib_same_window/phasep1_same_window_metrics.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_o4_vs_repaired_fresh_qlib_same_window/phasep1_same_window_daily_nav.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_o4_vs_repaired_fresh_qlib_same_window/phasep1_same_window_action_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_o4_vs_repaired_fresh_qlib_same_window/phasep1_next_day_accounting_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_o4_vs_repaired_fresh_qlib_same_window/phasep1_relative_comparison.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_o4_vs_repaired_fresh_qlib_same_window/phasep1_pnl_contribution_by_symbol.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_o4_vs_repaired_fresh_qlib_same_window/phasep1_pnl_contribution_by_day.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_o4_vs_repaired_fresh_qlib_same_window/phasep1_pnl_concentration_summary.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_o4_vs_repaired_fresh_qlib_same_window/phasep1_coverage_fairness_audit.json`

## 12. Gate

```text
phase_p1_o4_vs_repaired_fresh_qlib_same_window_readonly_comparison_completed
```
