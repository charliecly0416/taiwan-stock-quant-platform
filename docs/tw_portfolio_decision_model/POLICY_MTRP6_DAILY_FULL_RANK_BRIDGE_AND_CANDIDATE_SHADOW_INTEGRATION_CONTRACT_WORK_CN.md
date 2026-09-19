---
created_at: 2026-06-28
status: work_doc
phase: MTRP6_DAILY_FULL_RANK_BRIDGE_AND_CANDIDATE_SHADOW_INTEGRATION_CONTRACT
parent_phase: MTRP5_GO_NO_GO_CLOSURE
readonly_only: true
simulation_only: true
production_allowed: false
default_switch_allowed: false
daily_auto_mutation_allowed: false
frontend_api_agent_mutation_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRP6_DAILY_FULL_RANK_BRIDGE_AND_CANDIDATE_SHADOW_INTEGRATION_CONTRACT_WORK_CN

## 1. 目标

MTRP6 只做合同和 dry-run 设计，不做真实生产接入。

目标：

```text
为 top50_hold_rank_buffer_100 定义 daily full-rank visibility bridge、
daily candidate OrderIntent、
daily readonly replay/shadow artifact、
frontend/API/Agent readonly exposure 的合同、artifact 路径、validator 和 stop conditions。
```

MTRP6 要清掉或缩小 MTRP5 的三个 blocker：

```text
no_daily_auto_generation_for_candidate
no_live_latest/shadow_accumulation
no_frontend/API/Agent readonly integration contract
```

但 MTRP6 不实际修改 daily auto、frontend、API、Agent 或 latest pointer。

## 2. 非目标

本阶段不做：

```text
production default switch
production registry selectable/default 修改
frontend/API/Agent 代码改动
daily auto 脚本改动
provider refresh / publish
accepted latest switch
formal PriceStore write
broker / quick-trade / real order
target_weight / target_position / quantity instruction
新收益实验
模型训练 / inference / LTR 重算
```

## 3. 固定事实

当前通过证据：

```text
P3 same-window replay:
baseline total_return = 0.8894811577
candidate total_return = 0.9605828337
baseline max_drawdown = -0.1369660506
candidate max_drawdown = -0.1104340101
baseline actions = 137
candidate actions = 66
```

当前 blockers：

```text
source lineage still repackaged from research-only broad reference
only 2026-01-02..2026-05-07 covered
no daily auto generation for candidate
no live latest/shadow accumulation
no frontend/API/Agent readonly integration
candidate skipped_count higher than baseline needs tracking
no production default switch authorized
```

## 4. 执行者任务

执行者必须新增 builder：

```text
scripts/build_tw_policy_mtrp6_daily_shadow_integration_contract.py
```

输出 root：

```text
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp6_daily_shadow_integration_contract/
```

必须输出：

```text
manifest.json
daily_full_rank_bridge_contract.csv
daily_candidate_order_intent_contract.csv
daily_shadow_replay_contract.csv
frontend_api_agent_readonly_contract.csv
daily_auto_orchestrator_integration_plan.csv
shadow_accumulation_gate.csv
blocker_burndown_plan.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRP6_DAILY_FULL_RANK_BRIDGE_AND_CANDIDATE_SHADOW_INTEGRATION_CONTRACT_EXECUTION_REPORT_CN.md
```

## 5. Contract 要求

### 5.1 Daily full-rank bridge contract

必须定义：

```text
input_model_a_daily_signal = daily 150-row qlib ModelSignalArtifact
input_model_b_daily_signal = daily top50 LTR ModelSignalArtifact
output_bridge_signal = daily production-candidate ModelSignalArtifact
minimum_daily_rows >= 100
top50_rows = 50
non_top50_visibility_rows >= 50
top50 buy_score from LTR
non_top50 buy_score blank / ranking disabled
full_qlib_rank required for all visible rows
available_at <= signal_asof
production_candidate = true
production_allowed = false
not_published_latest = true
```

必须禁止：

```text
using research MTRC signals as runtime input
training / inference / LTR recompute
future return / label
replay return as input
provider publish
accepted latest switch
formal PriceStore write
```

### 5.2 Daily candidate OrderIntent contract

必须定义：

```text
strategy_rule = top50_hold_rank_buffer_100
input_signal = daily bridge manifest
input_portfolio_state = readonly simulated/paper state or prior shadow state
max_buy_count = 1
max_sell_count = 1
candidate_k = 50
hold_rank_buffer = 100
non_top50_buy_count = 0
missing_holding_visibility_policy = stop_or_skip_with_audit
```

OrderIntent 禁止字段：

```text
execution_date
execution_price
execution_quantity
quantity
shares
lots
cash
nav
equity
target_weight
target_position
broker_order_id
```

### 5.3 Daily shadow replay contract

必须定义：

```text
execution_price = next_open
execution_date_policy = next_tradeable_day_after_signal_date
fee_rate = 0.001425
sell_tax_rate = 0.003
lot_size = 10
same_day_mark_coverage_ratio >= 0.99
max_mark_lag_days = 0
negative_cash_count = 0
duplicate_position_count = 0
skip_reason_audit required
baseline same-day comparison required
```

### 5.4 Frontend/API/Agent readonly contract

必须定义：

```text
GET-only
readonly candidate display only
not default
not order
not target position
not investment advice
must show lineage warning
must show shadow status / blockers
must cite artifact manifests
```

禁止：

```text
POST/PUT/PATCH/DELETE
broker / quick-trade
paper apply from candidate before separate approval
default wording
收益承诺
```

### 5.5 Shadow accumulation gate

必须定义：

```text
minimum_shadow_days = 5 trading days
all daily validators pass
bridge/order/replay/checksum/source lineage consistent
skip reason delta tracked
no forbidden frontend/API/Agent wording
no production default/latest/provider mutation
```

## 6. Validator 要求

`validator_report.json` 必须检查：

```text
all_required_files_present
daily_bridge_contract_complete
daily_order_intent_contract_complete
daily_shadow_replay_contract_complete
frontend_api_agent_contract_complete
shadow_accumulation_gate_complete
blocker_burndown_plan_complete
production_allowed_false
default_switch_allowed_false
daily_auto_mutation_allowed_false
frontend_api_agent_mutation_allowed_false
provider_publish_allowed_false
accepted_latest_switch_allowed_false
broker_authorized_false
target_weight_position_forbidden
```

## 7. 允许 verdict

执行者 verdict：

```text
PASS_CONTRACT_READY_FOR_MTRP7_DAILY_SHADOW_DRY_RUN
FAIL_NEEDS_MTRP6_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

审查者 verdict：

```text
PASS_READY_FOR_MTRP7_DAILY_SHADOW_DRY_RUN
FAIL_NEEDS_MTRP6_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 8. 审查重点

审查者必须确认：

```text
MTRP6 没有实际改 daily auto / frontend / API / Agent；
没有打开 production_allowed / default switch；
合同足以指导 MTRP7 做 isolated daily shadow dry-run；
blocker burndown 与 MTRP5 blockers 一一对应；
禁止动作完整覆盖。
```
