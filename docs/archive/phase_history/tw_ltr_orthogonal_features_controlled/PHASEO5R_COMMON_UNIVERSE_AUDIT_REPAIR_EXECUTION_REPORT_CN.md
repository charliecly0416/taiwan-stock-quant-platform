# Phase O5R 执行报告：Common Universe Audit Repair

生成时间：2026-06-15T12:06:35+00:00

## 1. Gate

推荐 gate：`phase_o5r_common_universe_audit_repaired`。

## 2. Common Universe Key 审计

- full_key_count：`30475`。
- common_key_count：`10110`。
- excluded_key_count：`20365`。
- excluded treatment top50-preserve masked：`20365`。
- excluded price/replay unavailable：`0`。

## 3. Full vs Common Candidate

- Phase1C selected_top50_changed days：`110`；selected_top10_changed days：`0`。
- O4 treatment selected_top50_changed days：`0`；selected_top10_changed days：`0`。
- O4 treatment 的 common universe 对自身天然非约束：common 定义直接要求 treatment top50-preserve score 非空，因此 treatment full/common top50/top10 未变化。

## 4. Full vs Common Action / NAV

- action diff total：`0`。
- Phase1C risk_reduce action signal key missing from common：`84`。
- Phase1C risk_reduce full-only action diff：`0`。
- NAV diff pass：`True`。

Action diff summary：

| action | diff_count | full_only_count | common_only_count |
| --- | ---: | ---: | ---: |
| historical_add | 0 | 0 | 0 |
| historical_risk_reduce | 0 | 0 | 0 |
| historical_skip | 0 | 0 | 0 |

NAV diff summary：

| method | daily_equity_max_abs_diff | daily_cash_max_abs_diff | daily_holding_count_max_abs_diff |
| --- | ---: | ---: | ---: |
| o4_orthogonal_treatment_ltr | 0.0 | 0.0 | 0 |
| phase1c_anchor_simple | 0.0 | 0.0 | 0 |

## 5. 必答问题

1. O5 full/common 指标完全相同是否真实可复现？是。O5R 独立输出 full/common action 和 NAV，并用 diff 证明 treatment 与 Phase1C 的 NAV 完全一致。
2. 相同原因是 common 没有改变实际买入/持仓/NAV；不是审计遗漏。Phase1C 的 common 会改变候选 top50，但移除项未进入实际持仓路径。
3. Phase1C 被 common 移除的 risk_reduce signal key 数量为 `84`；但 full/common action diff 中 risk_reduce full-only 为 `0`，说明这些缺失 key 没有改变 replay engine 对既有持仓的卖出路径，NAV/cash/holding_count 也完全一致。
4. O4 treatment 因 top50-preserve 使 pairwise common 对自身天然非约束；full/common top50 与 top10 候选完全一致。
5. O5 的 full return 差异 `0.078698` 仍可作为 full universe 观察结果。
6. common universe 结果不应作为正式优劣结论；它只能作为 pairwise 审计说明。正式结论仍需后续审查决定，O5R 不进入 O6。

## 6. 边界

本轮未训练 qlib/LTR，未修改 Phase1C anchor score，未修改 O4 treatment score，未改 label/window/feature/replay 规则，未新增 filter/threshold/market gate/stop loss/take profit/turnover rule，未改前端/API/provider/accepted latest/monitor/交易链路。

## 7. 产物

- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_common_universe_excluded_key_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_excluded_key_count_by_date.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_excluded_key_count_by_symbol.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_selected_candidate_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_selected_candidate_summary.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_full_action_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_common_action_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_action_diff_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_action_diff_summary.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_action_signal_key_common_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_action_signal_key_common_summary.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_full_daily_nav.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_common_daily_nav.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_nav_diff_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_nav_diff_summary.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_next_day_accounting_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_full_universe_metrics.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_common_universe_metrics.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_summary.json`
- `docs/tw_ltr_orthogonal_features_controlled/PHASEO5R_COMMON_UNIVERSE_AUDIT_REPAIR_EXECUTION_REPORT_CN.md`
