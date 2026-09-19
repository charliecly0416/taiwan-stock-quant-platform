# RCPT12 Multi-day M1 Shadow Accumulation And Blocker Burn-down 执行报告

## 1. Scope
- Assigned phase: RCPT12_MULTI_DAY_M1_SHADOW_ACCUMULATION_AND_BLOCKER_BURN_DOWN
- Mainline document: docs/tw_portfolio_decision_model/POLICY_RCPT12_MULTI_DAY_M1_SHADOW_ACCUMULATION_AND_BLOCKER_BURN_DOWN_WORK_CN.md
- Work document: docs/tw_portfolio_decision_model/POLICY_RCPT12_MULTI_DAY_M1_SHADOW_ACCUMULATION_AND_BLOCKER_BURN_DOWN_WORK_CN.md
- Non-goals confirmed: 不执行 replay/training/threshold tuning，不改 production/default/latest/provider/frontend/Agent/monitor/order，不输出 action/order/target/quantity/broker 字段。

## 2. Documents / Contracts / Skills Read
- /home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
- docs/tw_portfolio_decision_model/POLICY_RCPT12_MULTI_DAY_M1_SHADOW_ACCUMULATION_AND_BLOCKER_BURN_DOWN_WORK_CN.md
- docs/tw_portfolio_decision_model/POLICY_RCPT11C_ACCUMULATION_REVIEW_CN.md
- docs/tw_portfolio_decision_model/POLICY_RCPT11B_S2_M1_READONLY_SHADOW_BUILDER_REVIEW_CN.md
- data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/shadow_replay_daily_evidence.csv
- data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/validator_report.json
- data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_score_snapshot.csv
- data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_summary.json
- data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_score_snapshot.csv
- data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_summary.json

## 3. Changes Made
- 新增 `scripts/build_tw_policy_rcpt12_multi_day_m1_shadow_accumulation.py`。
- 生成 `data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/` 下全部必需产物。
- 新增本执行报告。

## 4. Evidence Produced
- Artifacts: data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/manifest.json, data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/multi_day_m1_shadow_input.csv, data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/multi_day_accumulated_shadow_evidence.csv, data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/source_day_acceptance.csv, data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/historical_vs_new_blocker_burn_down.csv, data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/production_blocker_audit.csv, data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/accumulation_summary.json, data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/forbidden_scope_audit.csv, data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/validator_report.json, data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/diagnostic_findings.md
- Validator/test output: `validator_report.json` status = `PASS`，recommended_verdict = `PASS_MULTI_DAY_SHADOW_ACCUMULATION_CLEAN_BUT_PRODUCTION_BLOCKED`。
- Build command: `python scripts/build_tw_policy_rcpt12_multi_day_m1_shadow_accumulation.py`

## 5. Compliance With Mainline
- 只处理 source days: `2026-06-15`, `2026-06-17`。
- 每日按 S2 模式从 qlib_score/qlib_rank/qlib_score_raw 重建 M1-only shadow input，丢弃非 M1 rerank fields。
- 合并 RCPT10C historical `205` 日与 `2` 个新 source days。
- 分离 `historical_null_metric_blocker_count = 2` 与 `new_input_null_metric_blocker_count = 0`。

## 6. Forbidden Actions Audit
- production_allowed = false
- order_or_target_output_allowed = false
- replay_performed = false
- model_training_performed = false
- threshold_tuning_performed = false
- production_chain_modified = false

## 7. Issues / Blockers / Deviations
- historical blocker 仍开放：2025-07-14 TW6919、2026-03-02 TW4989。
- 两个新 input days 均 clean，但 production gate 仍为 `BLOCKED_BY_HISTORICAL_NULL_METRIC`。
- 无 scope deviation。

## 8. Files Changed
- scripts/build_tw_policy_rcpt12_multi_day_m1_shadow_accumulation.py
- data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/manifest.json
- data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/multi_day_m1_shadow_input.csv
- data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/multi_day_accumulated_shadow_evidence.csv
- data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/source_day_acceptance.csv
- data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/historical_vs_new_blocker_burn_down.csv
- data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/production_blocker_audit.csv
- data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/accumulation_summary.json
- data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/forbidden_scope_audit.csv
- data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/validator_report.json
- data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/diagnostic_findings.md
- docs/tw_portfolio_decision_model/POLICY_RCPT12_MULTI_DAY_M1_SHADOW_ACCUMULATION_AND_BLOCKER_BURN_DOWN_EXECUTION_REPORT_CN.md

## 9. Recommendation For Reviewer
`PASS_MULTI_DAY_SHADOW_ACCUMULATION_CLEAN_BUT_PRODUCTION_BLOCKED`
