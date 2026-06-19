# Phase E8R 执行报告：Replay Rule 与 Qlib/LTR 归因审计

生成时间：`2026-06-16T06:07:02+00:00`

## 1. 结论

- gate：`phase_e8r_replay_rule_and_qlib_ltr_attribution_audit_completed`。
- 本阶段只读复现/审计 replay rule，不训练 qlib/LTR，不调参，不改默认策略，不触发前端/API/provider/accepted latest/monitor/交易链路。
- 原规则复现：fresh `0.289419`，fresh+2025 LTR `0.464734`，E4 `0.602499`。
- top50-exit：fresh `0.960964`，fresh+2025 LTR `0.488315`，E4 `0.630662`。
- fresh qlib top50-exit qlib audit pass：`True`。

## 2. Replay Rule Summary

| rule | method | net_return | max_drawdown | actions | buys | sells | fee_tax | turnover |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| original | fresh_qlib_adaptive_original | 0.289419 | -0.037564 | 154 | 78 | 76 | 50394.08 | 15.248647 |
| original | fresh_qlib_2025_ltr_original | 0.464734 | -0.058226 | 151 | 78 | 73 | 53987.82 | 15.29539 |
| original | e4_frozen_qlib_2023_2025_ltr_original | 0.602499 | -0.071473 | 151 | 78 | 73 | 53524.77 | 14.904165 |
| top50_exit | fresh_qlib_adaptive | 0.960964 | -0.069702 | 141 | 73 | 68 | 60538.53 | 15.008614 |
| top50_exit | fresh_qlib_2025_ltr | 0.488315 | -0.074029 | 151 | 78 | 73 | 54546.67 | 15.454118 |
| top50_exit | e4_frozen_qlib_2023_2025_ltr | 0.630662 | -0.09658 | 150 | 78 | 72 | 52183.06 | 14.704259 |
| one_sell_one_buy | fresh_qlib_adaptive | 0.48538 | -0.077397 | 150 | 78 | 72 | 53022.45 | 15.155032 |
| one_sell_one_buy | fresh_qlib_2025_ltr | 0.527988 | -0.09931 | 149 | 78 | 71 | 54312.66 | 15.28341 |
| one_sell_one_buy | e4_frozen_qlib_2023_2025_ltr | 0.96184 | -0.093164 | 148 | 78 | 70 | 54755.23 | 14.143386 |

## 3. Fresh Qlib 96% 审计

- 正式复现值：`0.960964`。
- expected temporary value：`0.960964`；差异：`0.0`。
- score column 仅使用 `adaptive_score_baseline`，来源为 C4 repaired fresh qlib replay-ready artifact。
- top50 membership 使用每个 signal_asof 当日 `qlib_rank <= 50`，未使用未来日期倒灌。
- next-day price 仅用于成交与记账，不参与 ranking。
- PnL top1 positive share：`0.100191`，top3 share：`0.282954`。

## 4. LTR 归因

- 原规则下，LTR 可通过 top10 target set 的快速轮动提升 qlib；该结论成立于原 S2D/E4 replay rule。
- top50-exit 下，卖出条件变慢，策略主要依赖初期买入优先级和长期持有；fresh qlib adaptive 的买入排序更有利于该规则。
- fresh+2025 LTR 在 top50-exit 下弱于 pure fresh qlib，主要是 LTR 改变 top50 内买入优先级，错过或延后部分 fresh qlib 长持强势股。

| metric | value |
| --- | ---: |
| fresh_top50_exit_return | 0.960964 |
| fresh_ltr_top50_exit_return | 0.488315 |
| ltr_minus_fresh_return | -0.472649 |
| trade_diff_rows_capped | 242 |
| mean_common_holding_count | 1.7949 |
| largest_symbol_pnl_gap_abs | 86021.3 |

## 5. 结论边界

- 前期“orthogonal LTR 对 qlib 有增益”仍成立，但边界是原规则/较快 top10 target rotation。
- 在 top50-exit 慢卖规则下，LTR 不一定增强 qlib；score column 的买入排序归因会变成主导。
- 后续默认候选不能混用不同 replay rule 的收益结论；必须先冻结 replay rule，再比较 strategy score column。

## 6. 默认候选建议

- 本轮不建议直接切换默认策略。
- 若以 top50-exit 为候选生产规则，fresh qlib adaptive top50-exit 应进入优先候选讨论。
- 若保持原 S2D/E4 规则，E4 original 仍是有效候选。
- E4 top50-exit 也可作为候选，但收益低于 fresh qlib adaptive top50-exit且需要进一步 rolling/OOS 验证。

## 7. 输出 Artifact

- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_replay_rule_summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_daily_nav.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_actions.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_coverage_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_next_day_accounting_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_position_integrity_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_qlib_top50_exit_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_qlib_position_lifecycle.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_qlib_pnl_concentration.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_ltr_vs_qlib_trade_diff.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_ltr_vs_qlib_position_diff_by_day.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_ltr_vs_qlib_pnl_diff_by_symbol.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_ltr_attribution_summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/phasee8r_forbidden_action_audit.json`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE8R_REPLAY_RULE_AND_QLIB_LTR_ATTRIBUTION_AUDIT_EXECUTION_REPORT_CN.md`
