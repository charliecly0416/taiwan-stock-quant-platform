# RCPT15_R3_R Full YZ2 Feature Package Repair 执行报告

生成时间：`2026-06-26T05:11:48+00:00`

## 1. Scope

- Assigned phase: `RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR`
- Work document: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR_WORK_CN.md`
- Parent coordinator review: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_COORDINATOR_REVIEW_AND_NEXT_STEP_CN.md`
- Prior R3 execution report: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_ISOLATED_RERANK_EXECUTION_REPORT_CN.md`
- Parent R2 review: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R2_O2_DATA_SOURCE_REPAIR_AND_FEATURE_REBUILD_REVIEW_CN.md`
- Non-goals confirmed: 不写 formal/latest/provider/qlib accepted latest，不写 daily_ltr_rerank_latest 或 latest_orthogonal_features_latest，不输出 OrderIntent/target/quantity/broker，不训练、不调参、不 fallback qlib score。

## 2. Documents / Contracts / Skills Read

- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_COORDINATOR_REVIEW_AND_NEXT_STEP_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_ISOLATED_RERANK_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R2_O2_DATA_SOURCE_REPAIR_AND_FEATURE_REBUILD_REVIEW_CN.md`

## 3. Changes Made

- 新增 R3_R full YZ2-style feature package repair 脚本。
- 生成隔离 artifacts：`data_tw/experiments/risk_control_policy_2022/rcpt15_r3_r_full_yz2_feature_package_repair`。
- 构造 R1 shadow top50 + R2 isolated O2 + local readonly price/TWII 的完整 78-feature package。
- 使用 frozen O4 pickle model predict，输出 rerank score snapshot/top30/top50。

## 4. Evidence Produced

- `manifest.json`
- `validator_report.json`
- `input_artifact_inventory.csv`
- `feature_package.csv`
- `feature_schema_audit.csv`
- `feature_source_trace.csv`
- `coverage_audit.csv`
- `pit_audit.csv`
- `forbidden_scope_audit.csv`
- `rerank_score_snapshot.csv` / `rerank_top30.csv` / `rerank_top50.csv`
- `target_date_rerank_status.csv`
- `execution_notes.md`

## 5. Validator / Verdict

- verdict: `PASS_READY_FOR_REVIEW`
- model_load_ok: `True`
- eligible_shadow_top50_days: `2026-06-18, 2026-06-22, 2026-06-23, 2026-06-24, 2026-06-25`
- no_signal_input_dates: `2026-06-19`
- feature_whitelist_count: `78`
- missing_required_feature_count: `0`
- feature_package_rows: `250`
- rerank_score_rows: `250`
- top30_rows: `150`
- top50_rows: `250`
- coverage_pass: `True`
- pit_pass: `True`
- forbidden_pass: `True`
- stop_reason: ``

## 6. Forbidden Actions Audit

- provider publish: `not_performed`
- provider/qlib accepted latest switch: `not_performed`
- formal/latest pointer writes: `not_performed`
- daily_ltr_rerank_latest/latest_orthogonal_features_latest writes: `not_performed`
- production/default/frontend/Agent/monitor mutation: `not_performed`
- OrderIntent/target_weight/target_position/quantity/broker: `not_present`
- model training/tuning: `not_performed`
- qlib fallback/fake score: `not_used`

## 7. Issues / Blockers / Deviations

- `none`
- local readonly price/TWII source is PIT-safe by date filter; stale latest-used dates are recorded in `feature_source_trace.csv` and `coverage_audit.csv`.

## 8. Files Changed

- `scripts/build_tw_policy_rcpt15_r3_r_full_yz2_feature_package_repair.py`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_r_full_yz2_feature_package_repair/`

## 9. Recommendation For Reviewer

建议按 `PASS_READY_FOR_REVIEW` 审查。重点复核 78-feature 完整性、PIT source trace、6/19 no-signal skip、frozen O4 predict 与 forbidden scope audit。
