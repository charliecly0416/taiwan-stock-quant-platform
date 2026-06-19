# Phase E5 执行报告：E4 合理性与公平性审计

生成时间：`2026-06-16T01:50:00+00:00`

## 1. 结论

- gate：`phase_e5_e4_fairness_audit_passed`。
- E4 内部比较通过未来函数、未来标签、coverage、next-day accounting 和规则边界审计。
- E4 可以进入默认候选讨论，但不能直接默认切换；还需要 repaired fresh qlib 在完全同窗口下的桥接对比。
- E4 与 repaired fresh qlib 的直接公平比较不能仅由 E4 证明，因为 E4 没有把 repaired fresh qlib 纳入同一个 2026-only replay 表。

## 2. 合规性

| audit | passed | evidence |
| --- | --- | --- |
| future_function_audit | True | 2026-only replay-ready table has no future/label/realized PnL columns and no qlib in-sample score flag. |
| future_label_audit | True | E4 replay-ready columns exclude relevance/future return fields; forbidden audit says no 2026 label/future return decision. |
| coverage_audit | True | daily rows/top50 are 50/50/50, control/treatment score rows both 3950, duplicate keys 0. |
| next_day_accounting_audit | True | next_day_execution true for both methods; missing/skipped/last-day unexecuted counts are 0. |
| rule_boundary_audit | True | same replay engine/fee/tax/candidate_k/target holdings; treatment only reranks qlib top50; no new filter/gate/turnover rule. |

## 3. 公平性

- control net return：`0.146704`；treatment net return：`0.602499`；incremental：`0.455795`。
- control max drawdown：`-0.05115`；treatment max drawdown：`-0.071473`。
- control/treatment replay engine、next-day execution、fee/tax、target holdings、candidate_k 与 coverage 都一致。
- treatment 只在 qlib top50 内 rerank；replay-ready 表 qlib_rank 在 1..50 且 top50_flag 全为真。
- caveat：E4 control 是 E1 frozen qlib raw-score top50 baseline，不是 repaired fresh qlib adaptive baseline。

## 4. Repaired Fresh Qlib 桥接 Caveat

- bridge artifact available：`True`。
- bridge window：`2025-07-01..2026-05-07`；E4 window：`2026-01-01..2026-05-07`；same exact window：`False`。
- uses C4 repaired replay-ready fresh artifact：`True`。
- 结论：P1 establishes repaired-fresh replay-ready fairness for 2025-07-01..2026-05-07, but E4 itself does not include repaired fresh qlib on the exact 2026-only window.

## 5. 可解释性与集中度

| method | top1 positive pnl share | top3 positive pnl share | top5 positive pnl share | largest daily return |
| --- | ---: | ---: | ---: | ---: |
| extended_oos_frozen_qlib_orthogonal_ltr | 0.071638 | 0.180178 | 0.261263 | 0.056705 |
| extended_oos_frozen_qlib_top50_baseline | 0.084462 | 0.205391 | 0.303345 | 0.031017 |

| method | max symbol turnover share | top3 symbol share | top5 symbol share | single symbol >50% |
| --- | ---: | ---: | ---: | --- |
| extended_oos_frozen_qlib_orthogonal_ltr | 0.073495 | 0.194953 | 0.293697 | False |
| extended_oos_frozen_qlib_top50_baseline | 0.065114 | 0.169926 | 0.252571 | False |

解释：feature importance 不是单一异常特征驱动，Top20 同时包含技术/波动/成交额、margin_short 与 institutional_flow；最大单股 turnover share 低于 8%。日期贡献存在强势日，但未达到单日解释全部收益的程度。

## 6. 是否需要回滚、重跑或桥接实验

- 不建议回滚 E4：未发现停止条件。
- 不需要重跑 E4 内部 control/treatment replay：同口径审计通过。
- 需要额外桥接实验：在 `2026-01-01..2026-05-07` 完全同窗口下，把 E4 treatment 与 repaired fresh qlib C4 replay-ready adaptive baseline 放入同一 replay/audit 表，才能支撑默认候选讨论。

## 7. 输出 Artifact

- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e5_e4_fairness_audit/phasee5_fairness_audit_manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e5_e4_fairness_audit/phasee5_fairness_checklist.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e5_e4_fairness_audit/phasee5_daily_return_concentration.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e5_e4_fairness_audit/phasee5_symbol_concentration_summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e5_e4_fairness_audit/phasee5_repaired_fresh_bridge_caveat.csv`
