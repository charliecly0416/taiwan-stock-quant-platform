# RCPT15_R0_R Strictly Isolated Signal And Rerank Builder Contract 执行报告

生成时间：`2026-06-25T14:32:06+00:00`

## 1. Scope

- Assigned phase: `RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT`
- Mainline document: `docs/tw_portfolio_decision_model/POLICY_RCPT15_ISOLATED_SHADOW_BACKFILL_MAINLINE_CN.md`
- Work document: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT_WORK_CN.md`
- Parent review: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_ISOLATED_SHADOW_BACKFILL_FEASIBILITY_REVIEW_CN.md`
- Non-goals confirmed: 不拉数据、不运行 daily auto update、不打开 legacy provider gate、不切 accepted latest、不发布 provider、不写 latest pointer、不写 production/default/latest/provider/frontend/Agent/monitor/order、不输出 order/target/broker。

## 2. Documents / Contracts / Skills Read

- `docs/tw_portfolio_decision_model/POLICY_RCPT15_ISOLATED_SHADOW_BACKFILL_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_ISOLATED_SHADOW_BACKFILL_FEASIBILITY_REVIEW_CN.md`
- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`

## 3. Changes Made

- 新增 readonly audit/contract 脚本：`scripts/build_tw_policy_rcpt15_r0_r_strictly_isolated_builder_contract.py`
- 生成 RCPT15_R0_R artifacts：`data_tw/experiments/risk_control_policy_2022/rcpt15_r0_r_strictly_isolated_signal_and_rerank_builder_contract/`
- 未运行任何数据刷新、provider publish、daily auto update 或交易相关脚本。

## 4. Evidence Produced

- `manifest.json`
- `local_artifact_inventory.csv`
- `target_date_local_data_coverage.csv`
- `strict_builder_contract.csv`
- `no_latest_pointer_write_contract.csv`
- `dependency_gap_audit.csv`
- `r1_redefinition_decision.csv`
- `forbidden_scope_audit.csv`
- `script_latest_pointer_risk_audit.csv`
- `validator_report.json`
- `diagnostic_findings.md`

## 5. Validator / Conclusion

- validator status: `STOP_REQUIRES_EXPLICIT_LEGACY_REFRESH_OR_ACCEPTED_LATEST_AUTHORIZATION`
- direct R1 backfill allowed: `False`
- next allowed phase: `COORDINATOR_USER_AUTHORIZATION_REQUIRED`
- reason: Target option_c signal/top50 artifacts are missing and local price/model/market feature coverage is not sufficient for a complete strictly isolated signal plus rerank builder.

## 6. Key Evidence

- 目标日期缺少 option_c signal/top50 days: `8`
- O2 feature 缺少目标覆盖 days: `8`, max trade_date = `2026-06-10`
- normalized price sufficient through 2026-06-25: `False`
- O4 model/whitelist present: `True`
- 现有脚本 latest pointer risk: `True`

## 7. Forbidden Actions Audit

- external data pull: `not_performed`
- daily auto update run: `not_performed`
- legacy provider gate opened: `not_performed`
- accepted latest switched: `not_performed`
- provider publish: `not_performed`
- production/default/latest/provider/frontend/Agent/monitor/order modified: `not_performed`
- OrderIntent/target_weight/target_position/quantity/broker output: `not_present`

## 8. Files Changed

- `scripts/build_tw_policy_rcpt15_r0_r_strictly_isolated_builder_contract.py`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT_WORK_CN.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r0_r_strictly_isolated_signal_and_rerank_builder_contract/`

## 9. Recommendation For Reviewer

建议审查结论为 `STOP_REQUIRES_EXPLICIT_LEGACY_REFRESH_OR_ACCEPTED_LATEST_AUTHORIZATION`。若审查者确认证据成立，不应直接进入原 R1 backfill；应按 `r1_redefinition_decision.csv` 的 next allowed phase 处理。
