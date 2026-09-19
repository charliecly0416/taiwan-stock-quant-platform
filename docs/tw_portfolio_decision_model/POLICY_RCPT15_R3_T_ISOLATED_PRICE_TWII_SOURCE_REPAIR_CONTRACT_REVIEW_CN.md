---
created_at: 2026-06-26
status: review
phase: RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT
verdict: PASS_READY_FOR_R3_R_RERUN
reviewer_role: reviewer_agent
production_allowed: false
provider_publish_default_allowed: false
accepted_latest_switch_allowed: false
order_or_target_output_allowed: false
---

# RCPT15_R3_T Isolated Price / TWII Source Repair Contract 复审报告

## 1. Verdict

```text
PASS_READY_FOR_R3_R_RERUN
```

本轮复审确认执行产物已经出现，且 isolated stock price bridge、TWII bridge、source trace、TWII attempts 与 forbidden scope audit 均满足合同 gate。后续 R3_R rerun 可显式读取本 isolated bridge；不得自动替换 formal provider、不得切 accepted latest。

## 2. 已读文档 / Skills

- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_S_COORDINATOR_CLOSURE_AND_NEXT_STEP_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT_EXECUTION_REPORT_CN.md`

## 3. Evidence Checked

执行脚本：

```text
scripts/build_tw_policy_rcpt15_r3_t_isolated_price_twii_source_repair.py
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT_EXECUTION_REPORT_CN.md
```

产物目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/
```

必需产物均存在：

```text
manifest.json
validator_report.json
stock_price_bridge_inventory.csv
twii_source_attempts.csv
twii_bridge.csv
price_twii_bridge_freshness_audit.csv
source_trace.json
forbidden_scope_audit.csv
repair_plan_for_r3_r_rerun.md
```

## 4. Gate 复算结果

审查者独立读取 CSV / JSON 复算：

| Gate | 复算结果 | 结论 |
|---|---:|---|
| stock_price_bridge_inventory rows | 99 | PASS |
| unique symbols | 99 | PASS |
| stock bridge CSV count | 99 | PASS |
| all stock validation_status | pass | PASS |
| stock_price_bridge_min_date_max | 2026-06-25 | PASS |
| stock fresh symbols | 99 | PASS |
| twii_bridge rows | 2795 | PASS |
| twii_bridge date_min | 2015-01-05 | PASS |
| twii_bridge date_max | 2026-06-25 | PASS |
| target_window_twii_rows | 5 | PASS |
| target_window_twii_dates | 2026-06-18, 2026-06-22, 2026-06-23, 2026-06-24, 2026-06-25 | PASS |
| price_twii_bridge_freshness_audit all pass | true | PASS |
| forbidden_scope_audit any triggered | false | PASS |

`validator_report.json` 也给出：

```text
ok = true
verdict = PASS_READY_FOR_R3_R_RERUN
stock_price_bridge_symbols = 99
stock_price_bridge_min_date_max = 2026-06-25
twii_bridge_date_max = 2026-06-25
target_window_twii_rows = 5
price_twii_bridge_freshness_pass = true
forbidden_scope_pass = true
provider_publish = false
accepted_latest_switch = false
formal_latest_write = false
```

## 5. Source Trace / TWII Attempts

`source_trace.json` 记录：

- stock source: local R1 `candidate_normalized`
- job id: `rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625`
- stock symbols: 99
- selected TWII source: `finmind:TAIEX`
- network_used: `true`
- full_market_stock_network_pull: `false`

`twii_source_attempts.csv` 记录的联网尝试仅限 market index：

| source | type | status | target rows | URL/API |
|---|---|---|---:|---|
| `yahoo_chart:^TWII` | `network_market_index_only` | failed, HTTP 403 | 0 | Yahoo chart `^TWII` |
| `finmind:TAIEX` | `network_market_index_only` | usable, HTTP 200 | 5 | FinMind `TaiwanStockPrice`, `data_id=TAIEX` |

结论：联网范围符合合同，仅为 TWII / Taiwan market index source repair；未见全市场个股联网重拉证据。

## 6. Forbidden Actions Audit

审查者未执行任何数据拉取、provider publish、accepted latest switch、formal latest write、POST/PUT/PATCH/DELETE、broker/order/quick-trade 或 target position/weight 操作。

对执行产物与脚本的复审结论：

| Forbidden | 复审结论 |
|---|---|
| provider publish | 未触发 |
| accepted latest switch | 未触发 |
| formal latest write | 未触发 |
| daily_ltr_rerank_latest write | 未触发 |
| latest_orthogonal_features_latest write | 未触发 |
| OrderIntent / target / quantity / broker output | 未触发 |
| full-market stock network pull | 未触发 |

静态搜索命中的 forbidden 关键词均为 false self-audit、报告说明或修复计划中的禁止约束，未发现实际调用 publish/latest/order/broker 路径的证据。

## 7. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

TWII bridge 采用 FinMind `TAIEX` 补齐 target window，并与 formal stale TWII merge 成 isolated bridge。该选择符合本合同的 isolated TWII / market index repair 授权，但 R3_R rerun 必须显式消费该 isolated bridge，不能把它视为 formal provider latest。

## 8. Mainline Compliance

通过。

本阶段产物只写入：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT_EXECUTION_REPORT_CN.md
scripts/build_tw_policy_rcpt15_r3_t_isolated_price_twii_source_repair.py
```

未发现执行结果改变 production/default/provider accepted latest，也未发现订单、目标仓位、broker 或 quick-trade 输出。

## 9. Next Work Document

下一阶段可进入 R3_R rerun repair。

要求：

1. R3_R rerun 必须显式读取：
   `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/stock_price_bridge`
2. R3_R rerun 必须显式读取：
   `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/twii_bridge.csv`
3. R3_R rerun 仍必须 readonly/shadow，不得 provider publish、accepted latest switch、formal latest write。
4. R3_R rerun 应输出 freshness 对比与 rerank 差异审查证据。

## 10. Command For Executor Or Coordinator

```text
Proceed to RCPT15_R3_R rerun using the R3_T isolated stock_price_bridge and twii_bridge explicitly.
```
