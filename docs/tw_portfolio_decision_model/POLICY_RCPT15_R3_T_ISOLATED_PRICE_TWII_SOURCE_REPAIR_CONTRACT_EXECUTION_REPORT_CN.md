# RCPT15_R3_T Isolated Price / TWII Source Repair Contract 执行报告

## 1. Scope

- Assigned phase: RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT
- Mainline / work document: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT_WORK_CN.md`
- Parent closure: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_S_COORDINATOR_CLOSURE_AND_NEXT_STEP_CN.md`
- Review source: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_S_PRICE_MARKET_FRESHNESS_DIAGNOSTIC_REVIEW_CN.md`
- Non-goals confirmed: 不 provider publish、不切 qlib/provider accepted latest、不写 formal latest pointer、不写 daily_ltr_rerank_latest / latest_orthogonal_features_latest、不输出 OrderIntent/target_weight/target_position/quantity/broker。

## 2. Documents / Contracts / Skills Read

- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md`
- `.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md`
- `.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_S_COORDINATOR_CLOSURE_AND_NEXT_STEP_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_S_PRICE_MARKET_FRESHNESS_DIAGNOSTIC_REVIEW_CN.md`

## 3. Changes Made

- 新增脚本 `scripts/build_tw_policy_rcpt15_r3_t_isolated_price_twii_source_repair.py`。
- 新增隔离输出目录 `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair`。
- 用 R1 `candidate_normalized` 构造 R3 99 symbols 的 isolated `stock_price_bridge`。
- 构造 isolated `twii_bridge.csv`，优先本地；本地不足时仅对 TWII / market index source 执行 isolated pull。

## 4. Evidence Produced

- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/manifest.json`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/validator_report.json`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/stock_price_bridge_inventory.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/twii_source_attempts.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/twii_bridge.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/price_twii_bridge_freshness_audit.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/source_trace.json`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/forbidden_scope_audit.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/repair_plan_for_r3_r_rerun.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/stock_price_bridge/*.csv`

## 5. Key Freshness Gate

- Verdict: `PASS_READY_FOR_R3_R_RERUN`。
- stock_price_bridge_symbols = `99`。
- stock_price_bridge_min_date_max = `2026-06-25`。
- twii_bridge_date_max = `2026-06-25`。
- target_window_twii_rows = `5`，dates = `2026-06-18|2026-06-22|2026-06-23|2026-06-24|2026-06-25`。
- price_twii_bridge_freshness_pass = `True`。
- forbidden_scope_pass = `True`。

## 6. Source Trace

- Stock source: `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops/rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625/candidate_normalized`。
- TWII selected source: `finmind:TAIEX`。
- Network used: `True`。
- Network boundary: TWII / market index only; no full-market stock pull.

## 7. Forbidden Actions Audit

- provider_publish = `false`
- accepted_latest_switch = `false`
- formal_latest_write = `false`
- daily_ltr_rerank_latest_write = `false`
- latest_orthogonal_features_latest_write = `false`
- order_target_quantity_broker_output = `false`
- full_market_stock_network_pull = `false`

## 8. Issues / Blockers / Deviations

- 无已知 blocker。
- 本轮只生成 isolated bridge，不重跑 R3_R。

## 9. Recommendation For Reviewer

建议复审 `PASS_READY_FOR_R3_R_RERUN`，下一步由 R3_R repair rerun 显式读取本 isolated stock/TWII bridge。
