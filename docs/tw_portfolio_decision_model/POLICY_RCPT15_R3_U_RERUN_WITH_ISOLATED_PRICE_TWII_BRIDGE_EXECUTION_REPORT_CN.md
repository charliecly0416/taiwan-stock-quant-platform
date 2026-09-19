# RCPT15_R3_U Rerun With Isolated Price / TWII Bridge 执行报告

生成时间：`2026-06-26T05:49:11+00:00`

## 1. Scope

- Assigned phase: `RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE`
- Work document: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE_WORK_CN.md`
- Parent closure: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_COORDINATOR_CLOSURE_AND_NEXT_STEP_CN.md`
- R3_T review: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT_REVIEW_CN.md`
- R3_R work/report baseline: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR_WORK_CN.md` / `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR_EXECUTION_REPORT_CN.md`
- Non-goals confirmed: 不联网，不读 stale formal normalized_nonempty 作为 price/TWII source，不写 provider/formal/latest/accepted latest，不输出 OrderIntent/target/quantity/broker，不训练、不调参、不 fallback qlib score。

## 2. Documents / Contracts / Skills Read

- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_COORDINATOR_CLOSURE_AND_NEXT_STEP_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR_EXECUTION_REPORT_CN.md`

## 3. Changes Made

- 新增 R3_U rerun 脚本。
- 生成隔离 artifacts：`data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge`。
- 复用 R3_R 78-feature package 逻辑，显式替换 price source 为 R3_T `stock_price_bridge/`。
- 显式替换 TWII source 为 R3_T `twii_bridge.csv`。
- 使用 frozen O4 pickle model predict，输出 rerank score snapshot/top30/top50。
- 与 R3_R stale-source baseline 生成 freshness、score/rank、top30 overlap、rank change 差异审计。

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
- `freshness_before_after_audit.csv`
- `rerank_diff_vs_r3_r.csv`
- `top30_overlap_by_day.csv`
- `rank_change_summary.csv`
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
- stock_price_bridge_used: `True`
- twii_bridge_used: `True`
- price_latest_used_date_max: `2026-06-25`
- market_latest_used_date_max: `2026-06-25`
- top30_overlap_min: `21`
- changed_rank_rows_total: `237`
- stop_reason: ``

## 6. Key Difference Results

- R3_R baseline price latest max -> R3_U price latest max: `2026-06-01` -> `2026-06-25`
- R3_R baseline market latest max -> R3_U market latest max: `2026-05-21` -> `2026-06-25`
- ltr_score_delta_min/median/max: `-1.1848899690120602` / `-0.03601045542602138` / `0.9886115799858244`
- rank_delta_min/median/max: `-43` / `1.0` / `43`
- top1_changed_days: `2026-06-18|2026-06-22|2026-06-23|2026-06-24|2026-06-25`

## 7. Forbidden Actions Audit

- network: `not_performed`
- provider publish: `not_performed`
- provider/qlib accepted latest switch: `not_performed`
- formal/latest pointer writes: `not_performed`
- daily_ltr_rerank_latest/latest_orthogonal_features_latest writes: `not_performed`
- production/default/frontend/Agent/monitor mutation: `not_performed`
- OrderIntent/target_weight/target_position/quantity/broker: `not_present`
- model training/tuning: `not_performed`
- qlib fallback/fake score: `not_used`

## 8. Issues / Blockers / Deviations

- `none`
- R3_U price/TWII source is PIT-safe by date filter and isolated to R3_T bridge artifacts.

## 9. Files Changed

- `scripts/build_tw_policy_rcpt15_r3_u_rerun_with_isolated_price_twii_bridge.py`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge/`

## 10. Recommendation For Reviewer

建议按 `PASS_READY_FOR_REVIEW` 审查。重点复核 R3_T bridge source trace、78-feature 完整性、PIT、frozen O4 predict、差异 artifacts 与 forbidden scope audit。
