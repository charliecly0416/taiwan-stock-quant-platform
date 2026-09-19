---
created_at: 2026-06-28
status: work_doc
phase: MTRC2_T_R_PRICESTORE_BRIDGE_OR_READINESS_REPAIR
parent_phase: MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT
parent_review: docs/tw_portfolio_decision_model/POLICY_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT_REVIEW_CN.md
readonly_only: true
simulation_only: true
diagnostic_only: true
research_only: true
production_allowed: false
model_training_authorized: false
model_inference_authorized: false
model_signal_artifact_authorized: false
order_intent_build_authorized: false
replay_result_build_authorized: false
return_replay_authorized: false
ledger_build_authorized: false
price_store_bridge_authorized: true
formal_price_store_publish_authorized: false
provider_refresh_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRC2_T_R_PRICESTORE_BRIDGE_OR_READINESS_REPAIR_WORK_CN

## 1. 目标

MTRC2_T_R 只做一件事：

```text
为 MTRC2_S same-signal OrderIntent rows 构建或桥接 research-only、readonly、diagnostic-only 的历史价格输入，
并重新审计 next_open readiness，使后续 MTRC2_T gate 能判断是否可进入 MTRC2_U replay。
```

本阶段不是 replay 阶段。不得生成 ReplayResult、ledger、收益、回撤、集中度、rolling window 或 risk-off 诊断。

MTRC2_T_R 必须修复 MTRC2_T 的 blocker：

```text
standard_price_store_manifest_count = 0
order_instrument_bridge_overlap = 103/142
bridge_missing_price_file_count = 763
```

修复方式只能来自本地已存在、可追溯的历史价格源；不得触发 provider refresh/download，不得写正式 PriceStore 目录或 registry。

## 2. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD_REVIEW_CN.md
docs/tw_modular_contracts/PRICE_STORE_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
configs/price_store_registry.yaml
```

必须消费的 MTRC 输入：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/manifest.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/order_intents.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/validator_report.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_same_signal_replay_input_build_contract/manifest.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_same_signal_replay_input_build_contract/validator_report.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_same_signal_replay_input_build_contract/price_store_inventory.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_same_signal_replay_input_build_contract/price_store_readiness_audit.csv
```

允许盘点的本地价格源：

```text
data_tw/experiments/risk_control_policy_2022/**/stock_price_bridge/*.csv
data_tw/experiments/**/stock_price_bridge/*.csv
data_tw/ops/daily_auto_update/**/*
data_tw/raw/**/*
data_tw/self_contained_demo/normalized/*.csv
```

`data_tw/self_contained_demo/normalized` 只能作为负面/无效来源审计，不能用于真实 MTRC2 replay 输入，除非执行者能证明它是同口径真实历史价格而不是 demo 数据；默认不得采用。

## 3. 修复范围

MTRC2_T_R 允许生成一个隔离的 research-only price bridge artifact：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/
```

该产物可以是 PriceStore-like bridge，但不得写入：

```text
data_tw/artifacts/price_store/
configs/price_store_registry.yaml
configs/tw_modular_registry.yaml
任何 provider/latest/default/frontend/API/Agent/daily/production 路径
```

允许输出：

```text
manifest.json
prices.csv
schema.json
source_inventory.csv
source_selection_audit.csv
coverage_audit.csv
execution_availability_audit.csv
adjustment_audit.json
order_intent_price_join_audit.csv
missing_price_audit.csv
missing_next_open_audit.csv
invalid_source_audit.csv
forbidden_field_audit.csv
forbidden_action_audit.json
validator_report.json
diagnostic_findings.md
mtrc2_t_rerun_gate_recommendation.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC2_T_R_PRICESTORE_BRIDGE_OR_READINESS_REPAIR_EXECUTION_REPORT_CN.md
```

允许新增 builder：

```text
scripts/build_tw_policy_mtrc2_t_r_pricestore_bridge_or_readiness_repair.py
```

builder 只能写 MTRC2_T_R 输出目录和执行报告。

## 4. prices.csv 合同

`prices.csv` 必须至少包含：

```text
price_date
instrument
open
close
adj_factor
tradable_flag
halt_flag
next_day_execution_availability
price_source
adjustment_policy
source_file
```

允许附加审计字段：

```text
source_row_count
source_date_min
source_date_max
bridge_selected_for_order_intent
```

禁止字段：

```text
future_return_*
forward_return_*
label_*
strategy_action
target_position
target_weight
order_qty
broker_order_id
portfolio_equity
execution_quantity
cash
nav
daily_return
realized_pnl
replay_return
```

## 5. next_open readiness 语义

MTRC2_T_R 必须以 MTRC2_S `order_intents.csv` 为唯一需求集：

```text
required_rows = 每条 order intent
execution_date_policy = next_tradeable_day_after_signal_date
execution_price = next_open
```

对每条 order intent，必须判断：

```text
1. instrument 是否存在可用价格源；
2. signal_date 之后的下一可交易日是否存在；
3. 下一可交易日 open 是否存在且为正数；
4. 若缺失，必须写入 missing_price_audit / missing_next_open_audit；
5. 不得用 close、same-day open、未来收益、label 或 replay 结果 fallback。
```

如果全部 required rows 都有合法 next_open：

```text
price_store_ready = true
bridge_missing_price_file_count = 0
bridge_missing_next_open_count = 0
order_intent_next_open_coverage = 2378/2378
```

否则：

```text
price_store_ready = false
必须列出缺失 instrument/date/reason
不得进入 MTRC2_U
```

## 6. 合法来源规则

优先级：

```text
1. 已存在的 research/bridge price CSV，且 symbol/date/open/close 字段真实可追溯；
2. 已存在的 daily auto update 本地缓存/原始价格文件，且能映射成标准字段；
3. 其他本地历史价格 CSV/parquet，必须通过 schema/source audit；
4. self_contained_demo 默认 invalid，除非能证明不是 demo。
```

禁止：

```text
网络下载
provider refresh
accepted latest switch
从收益 replay/actions/daily_nav 反推出价格
用 close 或同日 open 代替 next_open
用 future_return/label/replay_return 作为价格或 readiness 依据
```

## 7. hard validator

MTRC2_T_R validator 必须检查：

```text
input_order_intent_artifact_equals_mtrc2_s
input_order_intent_signal_artifact_equals_mtrc1d
strategy_rule_candidate_rank_buffer_unchanged
prices_required_fields_present
price_open_close_positive_or_audited
price_source_trace_present
no_invalid_demo_source_used
no_forbidden_price_fields
order_intent_next_open_join_attempted_for_all_rows
missing_price_file_count_equals_0_for_ready
missing_next_open_count_equals_0_for_ready
next_open_coverage_count
no_close_or_same_day_fallback
no_replay_result_files_generated
no_return_drawdown_concentration_diagnostic
no_provider_latest_default_frontend_api_agent_daily_writes
no_registry_config_or_formal_price_store_write
no_broker_order_target_quantity_instruction
readonly_simulation_diagnostic_only
production_allowed_false
```

## 8. 允许 verdict

```text
PASS_READY_FOR_MTRC2_T_GATE_RERUN
PASS_WITH_REMAINING_PRICE_GAPS_NEEDS_DATA_DECISION
FAIL_NEEDS_MTRC2_T_R_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

含义：

```text
PASS_READY_FOR_MTRC2_T_GATE_RERUN:
  已构建完整 research-only price bridge，MTRC2_S OrderIntent rows 的 next_open readiness 全覆盖。

PASS_WITH_REMAINING_PRICE_GAPS_NEEDS_DATA_DECISION:
  合同和桥接逻辑正确，但本地合法数据源仍无法覆盖全部 rows；需要统筹决定是否缩窗、补数据或停止。

FAIL_NEEDS_MTRC2_T_R_REPAIR:
  builder/audit/validator 自身有缺陷，或误用非法来源。

STOP_COORDINATOR_DECISION_REQUIRED:
  必须引入网络/provider/正式 PriceStore/registry 改动才能继续。
```

## 9. 明确禁止动作

MTRC2_T_R 禁止：

```text
训练模型、调参、inference、重算 LTR score
生成或修改 ModelSignalArtifact / OrderIntentArtifact
生成 ReplayResultArtifact 或 ledger
运行收益 replay
计算收益、回撤、集中度、rolling window、risk-off
写 data_tw/artifacts/price_store
修改 registry/config/default
provider refresh / publish
accepted latest switch
写 frontend/API/Agent/daily/production
broker / quick-trade / real order
target_weight / target_position / quantity instruction
解除 MTR5 clean_extended_lineage_found=false blocker
宣称 production readiness
```

## 10. 审查者 audit brief

审查者必须独立检查：

```text
1. 输出目录是否只包含授权 price bridge/readiness 产物；
2. 是否没有 ReplayResult/ledger/收益诊断文件；
3. prices.csv schema 是否满足 PriceStore-like bridge 合同；
4. source inventory 是否真实盘点，source selection 是否排除 invalid/demo；
5. 对 2378 条 OrderIntent 是否全部尝试 next_open join；
6. coverage / missing audit 是否一致；
7. 若 PASS_READY，missing price 和 missing next_open 是否为 0；
8. 若仍有缺口，是否正确给 PASS_WITH_REMAINING_PRICE_GAPS 或 STOP，而不是放行 replay；
9. 是否未写正式 PriceStore、registry/config、provider/latest/default/frontend/API/Agent/daily；
10. 是否未 broker/order/target/quantity。
```

审查 verdict 只能是：

```text
PASS_READY_FOR_MTRC2_T_GATE_RERUN
PASS_WITH_REMAINING_PRICE_GAPS_NEEDS_DATA_DECISION
FAIL_NEEDS_MTRC2_T_R_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 11. 执行命令

```text
请执行 MTRC2_T_R_PRICESTORE_BRIDGE_OR_READINESS_REPAIR。
只构建 research-only price bridge/readiness 产物，不得 replay、不得 ledger、不得收益诊断、不得写正式 PriceStore/registry/provider/latest/default/frontend/API/Agent/daily。
```
