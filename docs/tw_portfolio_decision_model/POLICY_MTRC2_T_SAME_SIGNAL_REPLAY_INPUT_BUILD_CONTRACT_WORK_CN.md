---
created_at: 2026-06-28
status: work_doc
phase: MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT
parent_phase: MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD
parent_review: docs/tw_portfolio_decision_model/POLICY_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD_REVIEW_CN.md
readonly_only: true
simulation_only: true
diagnostic_only: true
production_allowed: false
model_training_authorized: false
model_inference_authorized: false
model_signal_artifact_authorized: false
order_intent_build_authorized: false
replay_input_contract_authorized: true
replay_result_build_authorized: false
return_replay_authorized: false
ledger_build_authorized: false
strategy_tuning_authorized: false
new_candidate_authorized: false
price_store_readiness_audit_authorized: true
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT_WORK_CN

## 1. 目标

MTRC2_T 只做一件事：

```text
基于已审查通过的 MTRC2_S same-signal OrderIntentArtifact，
冻结后续 readonly ReplayResult build 所需的输入合同、执行参数、PriceStore/readiness gate 和 validator。
```

本阶段不是 replay 执行阶段。MTRC2_T 不得生成 `ReplayResultArtifact`，不得输出 `summary.csv`、`actions.csv`、`daily_nav.csv`、`position_snapshots.csv`，不得计算收益、回撤、集中度、rolling window 或 risk-off 诊断。

MTRC2_T 必须回答：

```text
1. 后续 replay build 是否只能消费 MTRC2_S same-signal OrderIntent；
2. OrderIntent 的 signal_artifact 是否仍严格等于 MTRC1D broad signal manifest；
3. M2_hold_rank_buffer_100 / rank_buffer=100 / target_holding_count=10 / candidate_k=50 是否冻结；
4. 是否存在可用于后续 replay 的历史价格源或 PriceStore readiness 路径；
5. 后续 replay 的 execution config、missing price policy、cash policy 和 forbidden gates 是什么；
6. 如何禁止旧 MTR2_R/E3 replay 被复用；
7. 下一步是否可进入 MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD，或必须先 repair price store/readiness。
```

## 2. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD_REVIEW_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/PRICE_STORE_CONTRACT_CN.md
docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
configs/price_store_registry.yaml
configs/strategy_dependencies/mechanism_transfer_top50_cost_aware_v1.yaml
```

必须消费或审计的输入产物：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/manifest.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/order_intents.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/validator_report.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/signal_lineage_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/candidate_parameter_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/forbidden_action_audit.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/same_signal_replay_input_build_contract.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/same_signal_ledger_input_contract.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/m2_100_parameter_freeze_contract.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/replays/M2_hold_rank_buffer_100/manifest.json
```

允许盘点但不得发布或刷新：

```text
configs/price_store_registry.yaml
data_tw/artifacts/price_store/
data_tw/experiments/**/yz2_execution_price_readiness/**/manifest.json
data_tw/experiments/**/yz2r_execution_price_readiness/**/manifest.json
data_tw/normalized_full_market_stocks/
data_tw/raw/
```

若上述目录不存在，必须记录为 missing inventory，不得自行触发 provider refresh 或 accepted latest switch。

## 3. 冻结输入合同

后续 replay build 的输入必须冻结为：

```text
order_intent_artifact = data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/manifest.json
order_intents_csv = data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/order_intents.csv
order_intent_signal_artifact = data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json
strategy_rule = mechanism_transfer_top50_cost_aware_v1
candidate_id = M2_hold_rank_buffer_100
mechanism = hold_rank_buffer
rank_buffer = 100
target_holding_count = 10
candidate_k = 50
max_buy_count = 1
max_sell_count = 1
readonly_only = true
simulation_only = true
diagnostic_only = true
production_allowed = false
```

任何 deviation 都必须 hard fail。

## 4. 后续 Replay execution config 合同

MTRC2_T 必须冻结后续 replay build 的 execution config：

```text
execution_price = next_open
execution_date_policy = next_tradeable_day_after_signal_date
initial_equity = 1000000
target_holdings = 10
fee_rate = 0.001425
sell_tax_rate = 0.003
lot_size = 10
missing_price_policy = skip_or_audit_no_silent_fill
cash_policy = no_negative_cash_unless_explicitly_allowed_and_audited
diagnostic_only = true
not_strategy_input = true
not_production_readiness = true
```

本阶段只冻结合同，不得用该 config 计算成交、NAV、收益或持仓快照。

## 5. PriceStore / execution price readiness 要求

MTRC2_T 允许做历史价格源 inventory 和 readiness audit，但禁止下载、刷新、发布或切换数据源。

必须检查：

```text
1. 是否存在标准 PriceStore manifest；
2. 若无标准 PriceStore，是否存在可追溯的 historical local price source，可作为后续 MTRC2_U 的 PriceStore build/bridge 输入；
3. price source 是否覆盖 order_intents.csv 中的 instrument；
4. 是否有 order intent signal_date 之后的 next_tradeable_day open；
5. 缺失 next_open 的 symbol/date 必须进入 skip/audit 合同，不得 fallback 到 close 或同日 open；
6. price source/readiness 只作为后续 replay 输入，不能进入策略 ranking。
```

MTRC2_T 的 PriceStore verdict 可为：

```text
PRICESTORE_READY_FOR_MTRC2_U
PRICESTORE_BRIDGE_REQUIRED_BEFORE_MTRC2_U
PRICESTORE_BLOCKED_NO_LEGAL_SOURCE
```

如果只能找到 raw/local normalized price 而没有标准 PriceStore，MTRC2_T 不得直接伪装为正式 PriceStore；只能输出 bridge/build contract，让下一阶段先构建或桥接 PriceStore，再 replay。

## 6. 允许输出

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_same_signal_replay_input_build_contract/
```

允许生成：

```text
manifest.json
same_signal_replay_input_contract.csv
order_intent_lineage_audit.csv
order_intent_schema_audit.csv
candidate_parameter_audit.csv
execution_config_contract.json
execution_config_contract.csv
price_store_inventory.csv
price_store_readiness_audit.csv
missing_price_policy_contract.csv
old_mtr2r_replay_non_reuse_audit.csv
forbidden_scope_audit.csv
forbidden_action_audit.json
validator_report.json
diagnostic_findings.md
mtrc2_u_replay_build_work_recommendation.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT_REVIEW_CN.md
```

允许新增 builder：

```text
scripts/build_tw_policy_mtrc2_t_same_signal_replay_input_build_contract.py
```

builder 只能写 MTRC2_T 输出目录和 MTRC2_T 执行报告，不得写 MTRC2_S/MTRC2_R 产物，不得写 PriceStore 正式目录，不得写 registry、configs、provider、latest、frontend、API、Agent、daily 或 production 目录。

## 7. hard validator

MTRC2_T validator 必须 hard fail：

```text
order_intent_artifact_equals_mtrc2_s_same_signal
order_intent_review_passed
order_intent_signal_artifact_equals_mtrc1d_broad
candidate_id_equals_M2_hold_rank_buffer_100
mechanism_equals_hold_rank_buffer
rank_buffer_equals_100
target_holding_count_equals_10
candidate_k_equals_50
max_buy_count_equals_1
max_sell_count_equals_1
order_intent_non_top50_buy_count_equals_0
order_intent_daily_buy_sell_lte_1
execution_price_equals_next_open
execution_date_policy_next_tradeable_after_signal
initial_equity_equals_1000000
target_holdings_equals_10
fee_rate_equals_0_001425
sell_tax_rate_equals_0_003
lot_size_equals_10
missing_price_policy_skip_or_audit
no_price_fallback_to_close_or_same_day
old_mtr2r_replay_not_reused
no_replay_result_files_generated
no_return_drawdown_concentration_diagnostic
no_provider_latest_default_frontend_api_agent_daily_writes
no_broker_order_target_quantity_instruction
readonly_simulation_diagnostic_only
production_allowed_false
```

PriceStore/readiness gate 可按状态记录，但必须清楚区分：

```text
replay_input_contract_ready = true/false
price_store_ready = true/false
price_store_bridge_required = true/false
```

只有当 `replay_input_contract_ready=true` 且 `price_store_ready=true` 时，才能建议下一步开 `MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD`。

若 `price_store_bridge_required=true`，只能建议 `MTRC2_T_R_PRICESTORE_BRIDGE_OR_READINESS_REPAIR`。

## 8. 禁止输出

MTRC2_T 输出目录不得包含：

```text
summary.csv
actions.csv
daily_nav.csv
position_snapshots.csv
coverage_audit.csv
position_integrity_audit.csv
execution_audit.csv
skipped_actions.csv
daily_cash_audit.csv
ledger.csv
trade_ledger.csv
action_ledger.csv
```

这些文件属于后续 replay/ledger 阶段，当前阶段不得生成。

## 9. 明确禁止动作

MTRC2_T 禁止：

```text
训练模型
调参
模型 inference
重新计算 LTR score
生成或修改 ModelSignalArtifact
生成或修改 OrderIntentArtifact
生成 ReplayResultArtifact
生成 ledger
运行收益 replay
计算收益、回撤、集中度、rolling window 或 risk-off 诊断
根据收益选择价格源、策略或参数
新增策略候选
修改 M2_hold_rank_buffer_100 参数
修改 strategy dependency YAML、price store registry 或任何 default registry
复用旧 MTR2_R/E3 replay 作为本阶段输出或后续合法输入
provider refresh / publish
accepted latest switch
修改 production/default/latest/provider/frontend/API/Agent/daily
monitor config / scan / alerts write
broker / quick-trade / real order
target_weight / target_position / quantity instruction
解除 MTR5 clean_extended_lineage_found=false blocker
宣称 production readiness
```

## 10. PASS / FAIL 标准

PASS 条件：

```text
1. 生成完整 MTRC2_T replay input contract / readiness audit；
2. 明确 MTRC2_S OrderIntent 为唯一后续 decision source；
3. MTRC1D signal lineage、M2_100 参数、daily buy/sell、non-top50 buy gate 全部通过；
4. execution config 冻结为 next_open / 1000000 / 10 / fee 0.001425 / tax 0.003 / lot 10；
5. price source readiness 有明确 PASS 或 repair 路径；
6. 旧 MTR2_R/E3 replay 未复用；
7. 没有 ReplayResult、ledger、收益诊断、生产接入或交易动作；
8. 执行报告完整列出证据和 forbidden actions audit。
```

允许 verdict：

```text
PASS_READY_FOR_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD
PASS_WITH_PRICESTORE_BRIDGE_REQUIRED_READY_FOR_MTRC2_T_R
FAIL_NEEDS_MTRC2_T_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

注意：`PASS_READY_FOR_MTRC2_U` 只表示 replay 输入合同和 price readiness 通过；仍需另行授权 MTRC2_U 才能真正生成 ReplayResult。

## 11. 审查者 audit brief

审查者必须独立检查：

```text
1. MTRC2_T 输出文件是否只在授权目录内；
2. builder 是否只写 MTRC2_T 输出和执行报告；
3. 是否未生成 summary/actions/daily_nav/position_snapshots/ledger；
4. MTRC2_S OrderIntent 是否唯一 decision source；
5. OrderIntent signal_artifact 是否严格等于 MTRC1D manifest；
6. M2_100 参数和 execution config 是否冻结；
7. price_store_inventory / readiness audit 是否真实检查可用历史价格源，而不是伪造 ready；
8. missing_price_policy 是否为 skip/audit，无 close/same-day fallback；
9. old_mtr2r_replay_non_reuse_audit 是否证明旧 replay 未复用；
10. forbidden scope/action audit 是否覆盖 provider/latest/default/frontend/API/Agent/daily/broker/order/target/quantity；
11. 若 price readiness 不足，是否正确建议 repair 而不是放行 replay。
```

审查 verdict 只能是：

```text
PASS_READY_FOR_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD
PASS_WITH_PRICESTORE_BRIDGE_REQUIRED_READY_FOR_MTRC2_T_R
FAIL_NEEDS_MTRC2_T_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 12. 执行命令

```text
请执行 MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT。
只生成 replay input contract、execution config contract、PriceStore/readiness inventory、old replay non-reuse audit、validator/report。
不得生成 ReplayResult、不得 replay、不得 ledger、不得收益诊断、不得生产接入、不得交易字段或 target/quantity 指令。
```
