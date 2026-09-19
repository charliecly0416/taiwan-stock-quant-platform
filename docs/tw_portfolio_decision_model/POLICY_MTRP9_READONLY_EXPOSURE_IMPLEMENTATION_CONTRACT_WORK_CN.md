---
created_at: 2026-06-29
status: work_doc
phase: MTRP9_READONLY_EXPOSURE_IMPLEMENTATION_CONTRACT
parent_phase: MTRP8_SHADOW_REVIEW_AND_READONLY_EXPOSURE_DESIGN
strategy_candidate: top50_hold_rank_buffer_100
readonly_only: true
simulation_only: true
production_allowed: false
production_ready: false
default_switch_allowed: false
frontend_api_agent_code_change_allowed: false
daily_auto_default_change_allowed: false
latest_pointer_mutation_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRP9_READONLY_EXPOSURE_IMPLEMENTATION_CONTRACT_WORK_CN

## 1. 目标

MTRP9 只冻结后续 isolated GET-only readonly exposure implementation 的合同。

本阶段目标：

```text
读取 MTRP8 readonly exposure design package；
定义后续 API / frontend / Agent 只读暴露的合同；
定义响应 schema、字段语义、引用要求、安全文案、验收计划和 stop 条件；
判断是否可以进入 MTRP10 isolated readonly exposure implementation。
```

## 2. 非目标

本阶段不做：

```text
修改 backend route / service
修改 frontend API / component
修改 Agent prompt / simple-chat service
修改 production/default registry
修改 daily auto 主链路/default path
provider refresh / publish
accepted latest switch
latest pointer mutation
formal phase_yz 写入
formal PriceStore 写入
paper portfolio apply
broker / quick-trade / real order
target_weight / target_position / quantity instruction
模型训练/调参/重算分数
根据收益筛选或调参
```

## 3. 输入

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRP8_SHADOW_REVIEW_AND_READONLY_EXPOSURE_DESIGN_REVIEW_CN.md
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp8_shadow_review_readonly_exposure_design/
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml
configs/tw_product_artifact_registry.yaml
configs/tw_modular_registry.yaml
```

## 4. 输出

新增 builder：

```text
scripts/build_tw_policy_mtrp9_readonly_exposure_implementation_contract.py
```

输出 root：

```text
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp9_readonly_exposure_implementation_contract/
```

必须输出：

```text
manifest.json
api_endpoint_contract.csv
response_schema_contract.json
frontend_component_contract.csv
agent_context_contract.csv
acceptance_test_plan.csv
safety_boundary_audit_plan.csv
implementation_stop_conditions.csv
artifact_authority_map.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRP9_READONLY_EXPOSURE_IMPLEMENTATION_CONTRACT_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRP9_READONLY_EXPOSURE_IMPLEMENTATION_CONTRACT_REVIEW_CN.md
```

## 5. 合同要点

后续实现若被授权，只能满足以下设计：

```text
API: GET /api/tw-stock/readonly-shadow-exposure
query: strategy_rule=top50_hold_rank_buffer_100
source authority: MTRP8 artifact root and citation map
response: readonly flags, shadow rows, gate status, open blockers, citations
frontend: display-only shadow observation panel or collapsed section
Agent: context-only citation; no tool/action expansion
paper portfolio: apply blocked
network: GET-only except allowed /api/tw-stock/agent/simple-chat
```

## 6. Pass 条件

MTRP9 PASS 需要同时满足：

```text
MTRP8 validator status=pass
MTRP8 ready_for_mtrp9_readonly_exposure_implementation_contract=true
MTRP8 production_default_switch_authorized=false
MTRP8 frontend_api_agent_code_change_authorized=false
MTRP8 paper_portfolio_apply_authorized=false
API 合同只允许 GET
response schema 包含 readonly_only/not_order/not_target_position/not_investment_advice
response schema 不包含 target/quantity/broker/order/provider/latest switch 控制字段
frontend 合同禁止 default/recommendation/guaranteed return/investment advice wording
Agent 合同只允许引用 citation，不允许输出交易动作
acceptance plan 包含 backend readonly tests、frontend static/build、Playwright fixture network/console/screenshots
safety audit plan 覆盖 forbidden requests / target / broker / OpenAI browser-side / forged citations
forbidden scope clean
```

## 7. 允许结论

执行者 verdict：

```text
PASS_READY_FOR_MTRP10_ISOLATED_READONLY_EXPOSURE_IMPLEMENTATION
FAIL_NEEDS_MTRP9_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

审查者 verdict：

```text
PASS_READY_FOR_MTRP10_ISOLATED_READONLY_EXPOSURE_IMPLEMENTATION
FAIL_NEEDS_MTRP9_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 8. 下一步

若通过：

```text
进入 MTRP10 isolated GET-only readonly exposure implementation。
MTRP10 才允许按合同修改 backend/frontend/Agent readonly code，并必须有独立验收。
仍不授权 production default switch、paper apply 或 daily auto default path change。
```

若失败：

```text
修复 MTRP9 合同，不得进入实现。
```
