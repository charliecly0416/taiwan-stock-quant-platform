# 2026 子窗口只读对比：O4 Orthogonal LTR vs Repaired Fresh Qlib

生成时间：`2026-06-15T19:24:43+00:00`

## 1. 结论

- 本轮只读重跑指定窗口，没有训练、调参、改 score、改规则、改前端/API/provider/accepted latest/monitor 或交易链路。
- 窗口：`2026-01-01..2026-05-07`，从 2026-01-01 空仓初始资金重新起跑。
- 回放口径：同一 S2D replay engine、next-day execution、fee_rate `0.001425`、tax_rate `0.003`、target_position_count `10`、candidate_k `50`。
- O4 treatment 只在 qlib top50 内重排；fresh qlib 使用 repaired C4 replay-ready artifact 的 `adaptive_score_baseline`。

## 2. 指标

| method | net_return | max_drawdown | action_count | turnover_proxy | fee_and_tax | relative_return_vs_fresh |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| o4_orthogonal_ltr_top50_rerank | 0.216576 | -0.068816 | 151 | 14.884705 | 45762.01 | -0.072843 |
| repaired_fresh_qlib_top50_adaptive | 0.289419 | -0.037564 | 154 | 15.248647 | 50394.08 | 0.0 |

## 3. 对比摘要

- O4 net return：`0.216576`。
- Fresh qlib net return：`0.289419`。
- O4 - fresh：`-0.072843`。
- O4 max drawdown：`-0.068816`；fresh max drawdown：`-0.037564`。
- O4 action_count：`151`；fresh action_count：`154`。

## 4. Coverage

| method | rows | dates | daily rows min/median/max | top50 min/median/max | duplicate keys |
| --- | ---: | ---: | --- | --- | ---: |
| o4_orthogonal_ltr_top50_rerank | 3936 | 79 | 49/50.0/50 | 49/50.0/50 | 0 |
| repaired_fresh_qlib_top50_adaptive | 11850 | 79 | 150/150.0/150 | 50/50.0/50 | 0 |

## 5. Accounting

| method | active_actions | next_day_execution | missing_price_days | skipped_trade_count |
| --- | ---: | --- | ---: | ---: |
| o4_orthogonal_ltr_top50_rerank | 151 | True | 0 | 0 |
| repaired_fresh_qlib_top50_adaptive | 154 | True | 0 | 0 |

## 6. 输出 Artifact

- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_2026_o4_vs_fresh_subwindow/summary.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_2026_o4_vs_fresh_subwindow/daily_nav.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_2026_o4_vs_fresh_subwindow/actions.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_2026_o4_vs_fresh_subwindow/coverage_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_2026_o4_vs_fresh_subwindow/next_day_accounting_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_p1_2026_o4_vs_fresh_subwindow/manifest.json`
