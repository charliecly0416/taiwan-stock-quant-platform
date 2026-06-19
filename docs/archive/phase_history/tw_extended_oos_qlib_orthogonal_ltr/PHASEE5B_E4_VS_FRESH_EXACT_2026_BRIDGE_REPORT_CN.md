# Phase E5B 报告：E4 vs Repaired Fresh Qlib 2026 Exact Bridge

生成时间：`2026-06-16T01:56:03+00:00`

## 1. 结论

- 本轮把 E4 treatment 与 repaired fresh qlib 放入同一只读 replay/audit 表重跑。
- 窗口：`2026-01-01..2026-05-07`，从空仓初始资金起跑。
- 回放口径：同一 S2D replay engine、next-day execution、fee/tax、target_position_count=10、candidate_k=50。
- E4 treatment 只使用 E4 replay-ready top50 LTR score；fresh 使用 C4 repaired replay-ready adaptive score。

## 2. 指标

| method | net_return | max_drawdown | action_count | turnover_proxy | fee_and_tax | relative_return_vs_fresh |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| e4_frozen_qlib_orthogonal_ltr | 0.602499 | -0.071473 | 151 | 14.904165 | 53524.77 | 0.31308 |
| repaired_fresh_qlib_top50_adaptive | 0.289419 | -0.037564 | 154 | 15.248647 | 50394.08 | 0.0 |

## 3. 判断

- E4 net return：`0.602499`。
- Fresh qlib net return：`0.289419`。
- E4 - fresh：`0.31308`。
- E4 max drawdown：`-0.071473`；fresh max drawdown：`-0.037564`。

## 4. Coverage

| method | rows | dates | daily rows min/median/max | top50 min/median/max | duplicate keys |
| --- | ---: | ---: | --- | --- | ---: |
| e4_frozen_qlib_orthogonal_ltr | 3950 | 79 | 50/50.0/50 | 50/50.0/50 | 0 |
| repaired_fresh_qlib_top50_adaptive | 11850 | 79 | 150/150.0/150 | 50/50.0/50 | 0 |

## 5. Accounting

| method | active_actions | next_day_execution | missing_price_days | skipped_trade_count |
| --- | ---: | --- | ---: | ---: |
| e4_frozen_qlib_orthogonal_ltr | 151 | True | 0 | 0 |
| repaired_fresh_qlib_top50_adaptive | 154 | True | 0 | 0 |

## 6. 输出 Artifact

- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e5b_e4_vs_fresh_exact_2026_bridge/summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e5b_e4_vs_fresh_exact_2026_bridge/coverage_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e5b_e4_vs_fresh_exact_2026_bridge/next_day_accounting_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e5b_e4_vs_fresh_exact_2026_bridge/manifest.json`
