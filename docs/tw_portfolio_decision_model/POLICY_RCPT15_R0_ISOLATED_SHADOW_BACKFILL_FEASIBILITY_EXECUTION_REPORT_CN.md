# RCPT15_R0 Isolated Shadow Backfill Feasibility 执行报告

生成时间：`2026-06-25T13:45:04+00:00`

## 1. Scope

- Assigned phase: `RCPT15_R0_FEASIBILITY_AND_BACKFILL_CONTRACT`
- Mainline document: `docs/tw_portfolio_decision_model/POLICY_RCPT15_ISOLATED_SHADOW_BACKFILL_MAINLINE_CN.md`
- Non-goals confirmed: 不下载数据、不运行 daily auto update、不打开 legacy provider gate、不切 accepted latest、不写 production/default/latest/provider/frontend/Agent/monitor/order、不输出 order/target/broker。

## 2. Documents / Contracts / Skills Read

- `docs/tw_portfolio_decision_model/POLICY_RCPT15_ISOLATED_SHADOW_BACKFILL_MAINLINE_CN.md`
- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`

## 3. Changes Made

- 新增 readonly feasibility 脚本：`scripts/build_tw_policy_rcpt15_r0_shadow_backfill_feasibility.py`
- 生成 R0 feasibility artifacts：`data_tw/experiments/risk_control_policy_2022/rcpt15_r0_isolated_shadow_backfill_feasibility/`
- 未修改 cron、daily auto update、provider/latest、production 或交易相关路径。

## 4. Evidence Produced

- `manifest.json`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r0_isolated_shadow_backfill_feasibility/manifest.json`
- `validator_report.json`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r0_isolated_shadow_backfill_feasibility/validator_report.json`
- `available_daily_rerank_days.csv`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r0_isolated_shadow_backfill_feasibility/available_daily_rerank_days.csv`
- `candidate_backfill_dates.csv`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r0_isolated_shadow_backfill_feasibility/candidate_backfill_dates.csv`
- `dependency_gap_audit.csv`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r0_isolated_shadow_backfill_feasibility/dependency_gap_audit.csv`
- `forbidden_scope_audit.csv`: `data_tw/experiments/risk_control_policy_2022/rcpt15_r0_isolated_shadow_backfill_feasibility/forbidden_scope_audit.csv`

## 5. Validator / Conclusion

- validator status: `STOP_REQUIRES_EXPLICIT_LEGACY_REFRESH_OR_ACCEPTED_LATEST_AUTHORIZATION`
- R1 allowed: `False`
- reason: 2026-06-18..2026-06-25 lack local option_c daily signal/top50 artifacts; isolated daily_ltr_rerank cannot be produced from existing artifacts only.
- 已有 daily_ltr_rerank days: `2026-06-15, 2026-06-17`
- 2026-06-18 至 2026-06-25 缺少 option_c top50 days: `8`

## 6. Forbidden Actions Audit

- external download: `not_performed`
- daily auto update run: `not_performed`
- legacy provider gate opened: `not_performed`
- cron modified: `not_performed`
- accepted/latest switched: `not_performed`
- production/default/provider/frontend/Agent/monitor/order modified: `not_performed`
- OrderIntent/target_weight/target_position/quantity/broker output: `not_present`

## 7. Issues / Blockers / Deviations

- 当前 daily auto update 已运行并拉取 FinMind daily，但默认 M3 readonly orchestrator 不推进 qlib accepted latest / option_c daily signal。
- 目标区间 2026-06-18..2026-06-25 没有本地 option_c daily signal/top50 artifacts。
- 现有 P3 daily rerank 脚本会写 `daily_ltr_rerank_latest.json`，不能在严格隔离 backfill 中直接运行。

## 8. Files Changed

- `scripts/build_tw_policy_rcpt15_r0_shadow_backfill_feasibility.py`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_ISOLATED_SHADOW_BACKFILL_FEASIBILITY_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r0_isolated_shadow_backfill_feasibility/`

## 9. Recommendation For Reviewer

- 建议结论：`STOP_REQUIRES_EXPLICIT_LEGACY_REFRESH_OR_ACCEPTED_LATEST_AUTHORIZATION`
- 不建议进入 R1 isolated backfill execution。
- 下一步应由 coordinator/user 决定是否开一个更窄的 RCPT15_R0_R：只设计不执行的 qlib signal backfill contract，或显式授权 legacy/provider/latest 以外的安全本地 qlib signal builder。
