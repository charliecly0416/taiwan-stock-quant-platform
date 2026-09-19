# RCPT15_R3_S Price / Market Freshness Diagnostic 执行报告

## 1. Scope

- Assigned phase: RCPT15_R3_S_PRICE_MARKET_FRESHNESS_DIAGNOSTIC
- Mainline / work document: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_S_PRICE_MARKET_FRESHNESS_DIAGNOSTIC_WORK_CN.md`
- Parent closure: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_R_COORDINATOR_CLOSURE_AND_NEXT_STEP_CN.md`
- Non-goals confirmed: 不联网、不补源、不 provider publish、不切 qlib/provider accepted latest、不写 formal latest、不重跑 R3_R、不输出 order/target/broker。

## 2. Documents / Contracts / Skills Read

- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_S_PRICE_MARKET_FRESHNESS_DIAGNOSTIC_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_R_COORDINATOR_CLOSURE_AND_NEXT_STEP_CN.md`
- `.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md`
- `.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md`
- `.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md`

## 3. Changes Made

- 新增诊断脚本 `scripts/build_tw_policy_rcpt15_r3_s_price_market_freshness_diagnostic.py`。
- 新增隔离诊断输出目录 `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_s_price_market_freshness_diagnostic`。
- 新增本执行报告。

## 4. Evidence Produced

- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_s_price_market_freshness_diagnostic/manifest.json`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_s_price_market_freshness_diagnostic/validator_report.json`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_s_price_market_freshness_diagnostic/r3_r_used_freshness_audit.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_s_price_market_freshness_diagnostic/formal_price_source_freshness.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_s_price_market_freshness_diagnostic/r1_candidate_price_source_freshness.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_s_price_market_freshness_diagnostic/twii_market_source_inventory.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_s_price_market_freshness_diagnostic/daily_auto_price_market_chain_audit.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_s_price_market_freshness_diagnostic/recommended_repair_plan.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_s_price_market_freshness_diagnostic/forbidden_scope_audit.csv`

## 5. Key Findings

- Verdict: `PASS_READY_FOR_REPAIR`。
- R3_R 使用的 local_readonly_price `latest_used_date_max = 2026-06-01`，local_readonly_market `latest_used_date_max = 2026-05-21`。
- 原因：R3_R builder 固定读取 formal `normalized_nonempty`；formal stock price 对 R3_R symbols 的最新日期范围为 `2026-06-01` 到 `2026-06-01`，formal TWII 最新日期为 `2026-05-21`。
- R1 isolated `candidate_normalized` 最新 job 为 `rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625`，R3_R symbols 中 `99/99` 有目标窗口内数据，最新可到 `2026-06-25`。
- TWII / market source inventory 中没有发现比 formal `TWII.csv` 更近的本地 TWII CSV；当前 best TWII date_max 为 `2026-05-21`。
- daily auto 最新扫描显示默认链条会更新 FinMind raw daily bars，但 legacy Yahoo/Scrapling provider refresh、provider publish、accepted latest switch 默认未触发；未发现 readonly price/TWII bridge 已接入 daily auto。

## 6. Compliance With Mainline

- 已定位 stale 来源。
- 已确认存在更近 local isolated stock price source。
- 已确认本地未发现更近 TWII source。
- 已给出不切 accepted latest 的 repair 路线。

## 7. Forbidden Actions Audit

- forbidden_scope_audit: `pass`。
- 未联网、未补源、未 provider publish、未切 accepted latest、未写 formal latest、未重跑 R3_R、未输出交易指令。

## 8. Issues / Blockers / Deviations

- 要把 TWII 补到 2026-06-18..2026-06-25，需要单独的 isolated TWII source repair 或数据拉取授权；本阶段未执行。
- R1 candidate stock price bridge 可用于下一步隔离修复，但不能直接替代 formal provider latest。

## 9. Recommendation For Reviewer

建议判定 `PASS_READY_FOR_REPAIR`。下一阶段应先做 isolated readonly price bridge + TWII repair work doc，再决定是否重跑 R3_R repair。
