# RCPT15_R3 Isolated Rerank 执行报告

生成时间：`2026-06-26T04:15:22+00:00`

## 1. Scope

- Assigned phase: `RCPT15_R3_ISOLATED_RERANK`
- Mainline document: `docs/tw_portfolio_decision_model/POLICY_RCPT15_ISOLATED_SHADOW_BACKFILL_MAINLINE_CN.md`
- Work document: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_ISOLATED_RERANK_WORK_CN.md`
- Parent review: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R2_O2_DATA_SOURCE_REPAIR_AND_FEATURE_REBUILD_REVIEW_CN.md`
- Non-goals confirmed: 不写 formal latest/provider/qlib accepted latest，不改 production/default/latest/frontend/Agent/order/broker/target，不输出订单或仓位，不训练或调参。

## 2. Documents / Contracts / Skills Read

- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_ISOLATED_SHADOW_BACKFILL_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R2_O2_DATA_SOURCE_REPAIR_AND_FEATURE_REBUILD_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_ISOLATED_RERANK_WORK_CN.md`

## 3. Changes Made

- 新增 R3 工作文档。
- 新增 R3 isolated rerank 脚本。
- 生成 R3 隔离 artifacts：`data_tw/experiments/risk_control_policy_2022/rcpt15_r3_isolated_rerank`。

## 4. Evidence Produced

- `manifest.json`
- `input_artifact_inventory.csv`
- `target_date_rerank_input_status.csv`
- `model_load_audit.json`
- `feature_schema_audit.csv`
- `coverage_audit.csv`
- `pit_audit.csv`
- `forbidden_scope_audit.csv`
- `validator_report.json`
- `rerank_score_snapshot.csv` / `rerank_top30.csv` / `rerank_top50.csv`

## 5. Validator / Verdict

- verdict: `STOP_RERANK_REQUIRED_FEATURES_NOT_AVAILABLE_IN_R1_R2`
- model_load_ok: `True`
- eligible_shadow_top50_days: `2026-06-18, 2026-06-22, 2026-06-23, 2026-06-24, 2026-06-25`
- no_signal_input_dates: `2026-06-19`
- rerank_outputs_written: `False`
- stop_reason: `22 O4 training whitelist features are unavailable from R1/R2 authorized inputs`

## 6. Forbidden Actions Audit

- provider publish: `not_performed`
- accepted latest switch: `not_performed`
- latest pointer write: `not_performed`
- production/default/latest/frontend/Agent/order/broker/target mutation: `not_performed`
- fallback/fake rerank score: `not_used`

## 7. Files Changed

- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_ISOLATED_RERANK_WORK_CN.md`
- `scripts/build_tw_policy_rcpt15_r3_isolated_rerank.py`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_ISOLATED_RERANK_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_isolated_rerank/`

## 8. Recommendation For Reviewer

建议按 `STOP_RERANK_REQUIRED_FEATURES_NOT_AVAILABLE_IN_R1_R2` 审查。若 verdict 为 STOP，不应把 R3 纳入 RCPT14A rerun，除非 coordinator/user 另行授权缺失输入的隔离构建合同。
