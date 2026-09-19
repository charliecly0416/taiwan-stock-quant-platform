---
created_at: 2026-06-25
status: independent_review
role: RCPT10A_independent_reviewer
phase: RCPT10A_M1_SAFETY_CONTRACT
review_scope: contract_and_boundary_only
production_allowed: false
order_or_target_output_allowed: false
verdict: PASS_READY_FOR_RCPT10B_READONLY_SHADOW_ADAPTER
---

# RCPT10A M1 Safety Contract 独立审查

## 1. 审查结论

本次独立审查结论为：

```text
PASS_READY_FOR_RCPT10B_READONLY_SHADOW_ADAPTER
```

含义严格限定为：

1. RCPT10A 已完成 M1-only safety contract 冻结；
2. 可进入 RCPT10B readonly shadow adapter 设计/实现；
3. 不构成生产授权；
4. 不构成 order/target/quantity/broker 输出授权；
5. 不构成 replay、training、threshold tuning、mapping 扩展授权。

## 2. 审查输入

本次独立审查已读取：

- `docs/tw_portfolio_decision_model/POLICY_RCPT10_M1_PRODUCTION_READINESS_SAFETY_INTEGRATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT10A_M1_SAFETY_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT10A_M1_SAFETY_CONTRACT_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt10a_m1_safety_contract/`
- `docs/tw_portfolio_decision_model/POLICY_RCPT9D_LONGER_OOS_CLOSURE_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt9d_longer_oos_closure/`

## 3. 审查基线

RCPT10 主线已把本路线限定为 production readiness / safety integration，而非生产接入；并明确禁止：

```text
直接生产化
OrderIntent / target_weight / target_position / quantity_instruction
broker / quick-trade / real order
复活 M2 / M3
新增 mapping
threshold tuning
重训
修改 production/default/provider/latest/frontend/Agent/monitor/order 链路
```

RCPT9D 同时明确：

```text
只有 M1_QLIB_SCORE_COMPONENT_PRIMARY 可进入 RCPT10
M2_LTR_SCORE_COMPONENT_SECONDARY 不得进入 production-readiness 候选
M3_BLEND_Q70_L30_TERTIARY 也不得进入
```

因此，RCPT10A 的合规标准不是“功能是否丰富”，而是“合同是否冻结清楚且无越权”。

## 4. 审查发现

### 4.1 是否 M1-only

结论：`PASS`

证据：

- `m1_candidate_contract.json` 只声明 `candidate_id = M1_QLIB_SCORE_COMPONENT_PRIMARY`；
- `manifest.json` 的 `candidate_scope` 仅包含 M1；
- `go_no_go_gate_contract.csv` 单列 `m1_only_gate`；
- `forbidden_scope_audit.csv` 明确 `m2_or_m3_reactivated = pass`。

独立判断：

RCPT10A 没有把“通过 RCPT9D 的候选”写成开放集合，而是冻结成单一候选。这符合 M1-only 要求。

### 4.2 是否正确排除 M2/M3

结论：`PASS`

证据：

- RCPT10 主线将 M2 标记为 `REJECT_FOR_PRODUCTION_READINESS_ROUTE`，M3 标记为 `forbidden`；
- RCPT9D closure 明确 M2 因 drawdown gate 失败而排除；
- `m1_candidate_contract.json` 和 `manifest.json` 都把 M2/M3 写为 `forbidden_mappings`；
- `failure_rollback_contract.csv` 预置 `m2_or_m3_present` 为高严重度 fail-close trigger。

独立判断：

这里不仅“口头排除”了 M2/M3，还把 M2/M3 出现本身定义成 rollback 条件，边界冻结是足够硬的。

### 4.3 是否冻结 safety boundary、shadow artifact schema、go/no-go gate、failure rollback

结论：`PASS`

证据：

- `safety_boundary_contract.csv` 冻结了 `no_order_output`、`no_target_output`、`no_quantity_output`、`no_broker_or_quick_trade`、`no_default_strategy_switch`、`no_latest_pointer_switch`、`no_provider_publish_or_refresh`、`no_frontend_live_action`、`no_agent_tool_or_action_expansion`、`shadow_output_isolated`；
- `shadow_artifact_contract.csv` 将 RCPT10B 输出限制为 `manifest.json`、`candidate_signal_snapshot.json`、`candidate_decision_trace.csv`、`candidate_daily_summary.csv`、`forbidden_scope_audit.csv`、`validator_report.json`；
- `go_no_go_gate_contract.csv` 冻结 lineage、M1-only、readonly-shadow、forbidden-scope、artifact completeness、explanation trace、rollback contract 七道 gate；
- `failure_rollback_contract.csv` 冻结 missing lineage、forbidden field、non-shadow path、M2/M3 presence、threshold/mapping drift、validator fail、explanation trace missing 等 fail-close trigger。

独立判断：

RCPT10A 已完成 contract layer 该有的四层冻结，且四个文件相互一致，没有出现一个文件允许、另一个文件禁止的冲突。

### 4.4 是否没有 adapter/replay/training/threshold tuning/production/order/target 越权

结论：`PASS`

证据：

- 执行报告 front matter 明示：

```text
adapter_implemented = false
replay_performed = false
model_training_performed = false
threshold_tuning_performed = false
production_allowed = false
order_or_target_output_allowed = false
```

- `forbidden_scope_audit.csv` 对 adapter、replay、training、threshold tuning、new mapping、production chain modified、order/target/quantity output、broker/quick-trade path 均为 `pass`；
- 当前产物目录仅包含 contract / audit / validator / findings 文档，没有 runtime adapter、replay 结果、训练输出、生产路由修改证据。

独立判断：

本阶段实际交付物与 RCPT10A“只写合同、不做实现”的授权一致，未见越权实现混入。

### 4.5 必需产物和 validator 是否可信

结论：`PASS_WITH_LIMITED_SCOPE`

证据：

- `manifest.json` 列出的 9 个 required outputs 均存在；
- `validator_report.json` 给出：

```text
required_files_status = PASS
candidate_scope_status = PASS
lineage_traceability_status = PASS
readonly_boundary_status = PASS
forbidden_scope_status = PASS
forbidden_field_scan_status = PASS
recommended_verdict = PASS_READY_FOR_RCPT10B_READONLY_SHADOW_ADAPTER
```

- forbidden field scan 明确扫描并排除了：

```text
OrderIntent
target_weight
target_position
quantity_instruction
broker_order_id
quick_trade_flag
```

独立判断：

该 validator 对 RCPT10A 而言是“合同包完整性与静态禁字段扫描”的可信证据，足以支撑进入 RCPT10B。

但必须明确它的可信范围：

1. 它验证的是 contract package；
2. 它不是 RCPT10B runtime adapter 的执行级 validator；
3. 它不能替代后续对实际 shadow artifact 输出、路径隔离、字段污染、解释 trace 完整性的运行时校验。

因此这里给出的不是“全路线可信”，而是“RCPT10A 合同层可信且可推进”。

### 4.6 是否可以进入 RCPT10B

结论：`PASS`

原因：

1. M1-only 候选已冻结；
2. M2/M3 排除已冻结；
3. safety boundary / artifact schema / go-no-go / rollback 合同齐备；
4. 本阶段未越权实现 adapter/replay/training/production path；
5. 必需产物完整，contract-level validator 可支撑下一阶段开工。

因此可以进入：

```text
RCPT10B_READONLY_SHADOW_ADAPTER
```

## 5. 主要风险与限制

本次通过不覆盖以下内容，RCPT10B 必须补上：

1. 真实 adapter 输出是否严格只落在 shadow root；
2. runtime 生成的 `candidate_signal_snapshot.json`、`candidate_decision_trace.csv`、`candidate_daily_summary.csv` 是否严格满足 schema；
3. 解释 trace 是否真的可由 score/rank/market feature 回溯，而不是只在 contract 中声明；
4. runtime validator 是否能在每日产物层面 fail-close；
5. 是否完全阻断任何 order/target/quantity/broker 字段在 adapter 输出中出现。

这些不是 RCPT10A 的失败点，但属于 RCPT10B 必须验证的实现层风险。

## 6. 审查结论摘要

RCPT10A 合规，且合规点集中在“冻结得够清楚、边界收得够严”。本阶段没有发现需要判为 `FAIL_NEEDS_RCPT10A_REPAIR` 或 `STOP_SCOPE_OR_PRODUCTION_BOUNDARY_VIOLATION` 的证据。

最终结论：

```text
PASS_READY_FOR_RCPT10B_READONLY_SHADOW_ADAPTER
```

下一步文档：

`docs/tw_portfolio_decision_model/POLICY_RCPT10B_READONLY_SHADOW_ADAPTER_WORK_CN.md`
