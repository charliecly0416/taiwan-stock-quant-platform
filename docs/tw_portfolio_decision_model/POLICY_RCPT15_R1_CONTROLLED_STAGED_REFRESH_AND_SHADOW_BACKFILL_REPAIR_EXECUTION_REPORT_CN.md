# RCPT15_R1 Controlled Staged Refresh And Shadow Backfill Repair 执行报告

生成时间：`2026-06-25T15:08:44+00:00`

## 1. Scope

- Assigned phase: `RCPT15_R1_CONTROLLED_STAGED_REFRESH_AND_SHADOW_BACKFILL_REPAIR`
- Work document: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R1_CONTROLLED_STAGED_REFRESH_AND_SHADOW_BACKFILL_REPAIR_WORK_CN.md`
- Mainline document: `docs/tw_portfolio_decision_model/POLICY_RCPT15_ISOLATED_SHADOW_BACKFILL_MAINLINE_CN.md`
- R0 review reference: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT_REVIEW_CN.md`
- Non-goals confirmed: no provider publish, no accepted latest switch, no latest pointer write, no production/default/latest/provider/frontend/Agent/monitor/order changes, no target/order/broker output.

## 2. Documents / Contracts / Skills Read

- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R1_CONTROLLED_STAGED_REFRESH_AND_SHADOW_BACKFILL_REPAIR_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_ISOLATED_SHADOW_BACKFILL_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT_REVIEW_CN.md`

## 3. Changes Made

- Added `scripts/build_tw_policy_rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair.py` as the RCPT15_R1 execution script.
- Generated staged refresh artifacts under `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops/rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625`.
- Generated shadow-only signal artifacts under `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/shadow_signals`.
- Generated RCPT15_R1 execution report and validator evidence under `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair`.

## 4. Evidence Produced

- `manifest.json`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/manifest.json`
- `stage_refresh_status.json`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/stage_refresh_status.json`
- `target_date_backfill_matrix.csv`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/target_date_backfill_matrix.csv`
- `shadow_signal_artifact_index.csv`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/shadow_signal_artifact_index.csv`
- `shadow_o2_feature_status.csv`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/shadow_o2_feature_status.csv`
- `shadow_rerank_status.csv`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/shadow_rerank_status.csv`
- `dependency_gap_audit.csv`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/dependency_gap_audit.csv`
- `forbidden_scope_audit.csv`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/forbidden_scope_audit.csv`
- `validator_report.json`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/validator_report.json`
- `diagnostic_findings.md`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/diagnostic_findings.md`

## 5. Stage Refresh / Model Smoke

- stage status: `PASS`
- fetch status: `pass`
- normalized validation status: `pass`
- provider validation status: `pass`
- model smoke status: `pass`
- symbols success: `150` / `150`
- stage report: `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops/rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625/reports/execution_summary.json`

## 6. Shadow Signal Artifacts

- trading days built: `6`
- non-trading days skipped: `2`
- shadow root: `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/shadow_signals`

## 7. O2 Feature / Rerank Status

- O2 status: `INSUFFICIENT`
- O2 max trade date: `2026-06-10`
- O2 target coverage count: `0`
- R1D rerank status: `BLOCKED`

## 8. Forbidden Actions Audit

- provider publish: not performed
- accepted latest switch: not performed
- latest pointer write: not performed
- production/default/latest/provider/frontend/Agent/monitor/order mutation: not performed
- target/order/broker artifacts: not present

## 9. Verdict

- recommended verdict: `PASS_PARTIAL_SHADOW_SIGNALS_ONLY_RERANK_BLOCKED`

## 10. Notes

This execution kept staged refresh, shadow signals, and O2 audit in the RCPT15_R1-only tree.
No formal latest pointers were written.
No provider publish or accepted latest switch was attempted.
