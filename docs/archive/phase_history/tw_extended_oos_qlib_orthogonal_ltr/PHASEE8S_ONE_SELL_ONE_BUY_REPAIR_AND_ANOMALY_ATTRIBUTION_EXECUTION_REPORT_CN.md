# Phase E8S 执行报告：One-Sell-One-Buy 修复与异常归因

生成时间：`2026-06-16T06:25:23+00:00`

## 1. 结论

- gate：`phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution_completed`。
- 已修复 one_sell_one_buy sell priority：top50 外优先卖；若仍在 top50，则卖 score 排名最差者。
- E8R buggy one_sell_one_buy 已作为 anomaly case 复现，不作为默认候选收益证据。
- 未训练 qlib/LTR，未调参，未改 score column，未触发 provider/accepted latest/frontend/API/monitor/broker/order 链路。

## 2. Replay Rule Summary

| rule | fresh | fresh+2025 LTR | E4 |
| --- | ---: | ---: | ---: |
| original | 0.289419 | 0.464734 | 0.602499 |
| top50_exit | 0.960964 | 0.488315 | 0.630662 |
| one_sell_one_buy_correct | 0.469117 | 0.583752 | 0.878002 |
| one_sell_one_buy_buggy_e8r | 0.48538 | 0.527988 | 0.96184 |

## 3. Buggy E4 异常归因

- buggy E4 复现：`0.96184`。
- correct E4：`0.878002`。
- largest single divergence contribution：`84939.71`。
- top1/top3/top5/top10 positive pnl share：`0.142501` / `0.384542` / `0.53537` / `0.768073`。
- buggy rule 错误地卖出 top50 内排名较好的股票，因此保留了部分排名较差但后续强势的持仓；这是 bug anomaly，不是已冻结策略假设。

## 4. Rank Bucket Diagnostic

| bucket | mean_forward_return_to_end |
| --- | ---: |
| rank_11_20 | 0.449703 |
| rank_1_10 | 0.431672 |
| rank_21_30 | 0.451823 |
| rank_31_50 | 0.399312 |

该诊断使用 future return 仅做事后归因，不进入 replay decision。

## 5. 结论保护

- `valid_controlled_result`：original、top50_exit、one_sell_one_buy_correct。
- `bug_anomaly_result`：one_sell_one_buy_buggy_e8r，必须作废为策略收益证据。
- `hypothesis_for_future_work`：若中位/较差 rank 长持有效，需要另开新支线验证，不得混入当前默认策略。
- correct one_sell_one_buy 下：fresh+2025 LTR 高于 fresh；E4 高于 fresh/fresh+LTR，说明 LTR 在正确低换手规则下仍有支持，但须按该 replay rule 单独讨论。

## 6. 是否允许回到默认策略讨论

- 允许回到默认策略讨论，但必须先冻结 replay rule。
- 不允许使用 buggy E4 96.18% 作为默认策略证据。
- 可讨论 original E4、top50-exit fresh qlib、one_sell_one_buy_correct E4 等合同正确结果。

## 7. 输出 Artifact

- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/phasee8s_manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/phasee8s_replay_rule_summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/phasee8s_daily_nav.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/phasee8s_actions.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/phasee8s_rule_implementation_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/phasee8s_next_day_accounting_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/phasee8s_position_integrity_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/phasee8s_correct_vs_buggy_sell_decision_diff.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/phasee8s_buggy_extra_held_pnl.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/phasee8s_buggy_early_sold_pnl.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/phasee8s_buggy_e4_pnl_concentration.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/phasee8s_rank_bucket_forward_return_diagnostic.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/phasee8s_forbidden_action_audit.json`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE8S_ONE_SELL_ONE_BUY_REPAIR_AND_ANOMALY_ATTRIBUTION_EXECUTION_REPORT_CN.md`
