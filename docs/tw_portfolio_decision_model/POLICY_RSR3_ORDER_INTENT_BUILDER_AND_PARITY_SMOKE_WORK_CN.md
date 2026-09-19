---
created_at: 2026-06-27
status: work_document
phase: POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_REVIEW_CN.md
previous_artifact_root: data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract
production_allowed: false
readonly_only: true
diagnostic_only: true
formal_replay_authorized: false
replay_result_authorized: false
return_conclusion_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
default_or_production_change_allowed: false
real_order_allowed: false
target_position_weight_quantity_allowed: false
---

# POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_WORK_CN

## 1. Phase Goal

执行 `POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE`。

本阶段只允许根据 RSR2 冻结合同实现或生成 `OrderIntentArtifact` samples 与 parity smoke evidence。目标是验证 RSR2 预声明规则能通过标准模块边界产生合规的意图产物，并证明 baseline parity smoke 的 action boundary 可复核。

本阶段不是收益 replay 阶段，不得生成正式 `ReplayResultArtifact`，不得产生收益、NAV、PnL、回撤、fee/tax 后收益结论。

## 2. Required Documents

执行者必须读取：

- `docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_REVIEW_CN.md`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/manifest.json`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/predeclared_rule_contracts.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/predeclared_rule_contracts.md`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/required_fields_matrix.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/pass_fail_gates.md`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/forbidden_action_audit.csv`
- all YAML drafts under `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/rule_dependency_yaml_drafts/`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

## 3. Allowed Outputs

RSR3 可输出：

```text
docs/tw_portfolio_decision_model/POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_EXECUTION_REPORT_CN.md
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr3_order_intent_builder_and_parity_smoke/
```

建议 artifact root 下至少包含：

```text
manifest.json
order_intent_sample_index.csv
strategy_decision_audit.csv
forbidden_field_audit.csv
order_intent_contract_validation.json
baseline_parity_smoke.csv
baseline_parity_smoke.md
forbidden_action_audit.csv
```

若为每个规则生成 sample，可使用：

```text
order_intent_samples/{strategy_rule}/manifest.json
order_intent_samples/{strategy_rule}/order_intents.csv
order_intent_samples/{strategy_rule}/schema.json
order_intent_samples/{strategy_rule}/strategy_decision_audit.csv
order_intent_samples/{strategy_rule}/forbidden_action_audit.json
```

所有 sample 必须声明：

```text
diagnostic_only=true
readonly_only=true
smoke_only=true
not_valid_strategy_evidence=true
not_default_candidate=true
not_production_candidate=true
not_order=true
not_target_position=true
not_investment_advice=true
no_replay_return_conclusion=true
```

## 4. Required Work

### 4.1 RSR2 Contract Ingestion

执行者必须读取 RSR2 合同表和 draft YAML，但不得把 draft YAML 注册进正式 `configs/strategy_dependencies/`，除非 coordinator 另开正式策略接入阶段。

本阶段允许在 RSR3 artifact root 内生成 smoke-only copies 或 normalized dependency snapshots，用于审计和 sample builder 输入。

### 4.2 PIT-safe Extension Boundary

RSR3 必须显式说明每个 RSR2 extension 的来源和 PIT 语义：

- `score_bucket`
- `score_percentile_band`
- `score_gap_to_top`
- `top_score_dispersion_band` if used
- `rank_1d_delta`
- `rank_3d_delta`
- `rank_5d_delta`
- `rank_1d_direction`
- `rank_3d_direction`
- `rank_5d_direction`
- `market_regime_diagnostic`
- `market_risk_on_flag`
- `market_risk_neutral_flag`
- `market_risk_off_flag`
- `market_crash_flag`
- `holding_rank_support_flag`
- `holding_score_support_flag`

不得直接消费 RSR1 diagnostic dataset 作为 StrategyRule runtime input。允许用 RSR1 机制作为定义来源，但 RSR3 sample builder 必须从标准 `ModelSignalArtifact`、`PortfolioState`、声明过的 PIT-safe extension source 或 synthetic/golden fixture 构造输入。

### 4.3 OrderIntentArtifact Samples

每个 RSR2 规则至少生成一个 smoke sample 或明确说明无法生成的阻断原因。

`order_intents.csv` 必须遵守 `ORDER_INTENT_CONTRACT_CN.md`，至少包含：

```text
signal_date
instrument
intent_action
intent_reason
strategy_rule
candidate_rank
buy_rank
full_qlib_rank
max_buy_count
max_sell_count
model_name
signal_artifact
```

允许可选审计字段：

```text
portfolio_state_artifact
current_holding_flag
target_holding_count
candidate_k
tie_breaker
diagnostic_only
partial_intent_kind
partial_intent_policy
partial_intent_note
```

不得包含数量、仓位、权重、现金、成交、broker/order、收益字段。

### 4.4 Strategy Decision Audit

必须输出 `strategy_decision_audit.csv`，至少覆盖：

- `signal_date`
- `strategy_rule`
- `instrument`
- `decision_stage`
- `input_fields_used`
- `extension_fields_used`
- `candidate_boundary`
- `sell_boundary`
- `buy_ordering`
- `tie_breaker`
- `no_trade_zone`
- `max_buy_count`
- `max_sell_count`
- `actual_buy_intent_count_for_day`
- `actual_sell_intent_count_for_day`
- `decision_reason`
- `status`

审计必须证明：

- 每日 buy/sell intent 数不超过 RSR2 合同；
- market regime action budget 的 regime-specific budget 生效；
- sell boundary、buy ordering、tie breaker、no-trade zone 可追溯；
- no-trade/skip 有明确原因。

### 4.5 Forbidden Field Audit

必须输出 `forbidden_field_audit.csv`，至少检查：

```text
diagnostic_label_*
future_return_*
future_excess_return_*
forward_return_*
label_*
relevance_10d_top_heavy
ltr_relevance_label
realized_pnl
realized_return
unrealized_pnl
execution_price
execution_date
next_open
next_close
cash
cash_after
nav
equity
daily_return
replay_return
broker
broker_order_id
order_id
target_position
target_weight
allocation_weight
quantity_instruction
```

每项必须标记 `present=false` 或 `used_for_decision=false`，否则阻断。

### 4.6 OrderIntent Contract Validation

必须输出 `order_intent_contract_validation.json`，至少验证：

- required fields 全部存在；
- `intent_action` 只来自 `buy`、`sell`、`hold`、`skip`；
- 每日 buy/sell 意图数不超过 `max_buy_count` / `max_sell_count`；
- 不含 forbidden fields；
- sample manifest 标记 `diagnostic_only=true`、`readonly_only=true`、`smoke_only=true`、`not_valid_strategy_evidence=true`；
- 未生成 ReplayResult；
- 未输出 target_position / target_weight / allocation_weight / quantity instruction。

### 4.7 Baseline Parity Smoke

必须包含 baseline parity smoke，但只允许验证 action boundary/parity，不得计算收益。

允许检查：

- baseline-style top50 boundary 是否可由 OrderIntent builder 表达；
- qlib top50 exit boundary 是否一致；
- buy ordering 是否可追溯到 `buy_score_desc` 或合同指定排序；
- one-day max buy/sell count 是否符合配置；
- action difference / parity mismatch 仅作为 builder smoke，不作为收益优劣结论。

禁止检查或输出：

```text
total_return
net_return_after_fee_tax
gross_return
max_drawdown
daily_nav
cash_after
equity
realized_pnl
unrealized_pnl
fee
tax
ReplayResultArtifact
```

## 5. Forbidden Actions

RSR3 禁止：

- training / retraining；
- qlib refresh；
- LTR retrain 或 qlib+LTR adaptation；
- external data pull；
- formal replay；
- `ReplayResultArtifact` generation；
- replay PnL search；
- threshold tuning to return；
- 选择 best threshold / best rule / best bucket；
- provider publish；
- accepted latest switch；
- production/default/frontend/daily/latest 修改；
- broker、quick-trade、real order；
- target_position、target_weight、allocation_weight、quantity instruction 输出；
- 把 smoke/parity 结果包装成收益结论或 production candidate。

## 6. Stop Conditions

以下任一情况必须 STOP 并写 blocker：

- 需要直接读取 RSR1 diagnostic dataset 才能生成 StrategyRule runtime input；
- 需要 `diagnostic_label_*`、future return、realized/unrealized PnL、execution、cash/NAV、replay return 才能做决策；
- 无法生成符合 `ORDER_INTENT_CONTRACT_CN.md` 的 sample；
- baseline parity smoke 需要正式 replay 或收益指标才能完成；
- 需要写 `configs/strategy_dependencies/` 正式目录；
- 需要 provider publish、accepted latest switch、production/default/frontend/daily/latest 修改；
- 需要输出真实订单、target position、target weight、allocation weight 或 quantity instruction。

## 7. Pass Criteria

RSR3 通过条件：

- 每个可执行 RSR2 规则都有 smoke-only `OrderIntentArtifact` sample，或有清晰非实现 blocker；
- sample manifest 和 order_intents schema 符合 `ORDER_INTENT_CONTRACT_CN.md`；
- `strategy_decision_audit.csv` 能证明 sell boundary、buy ordering、tie breaker、no-trade zone、max buy/sell count 生效；
- `forbidden_field_audit.csv` clean；
- `order_intent_contract_validation.json` pass；
- baseline parity smoke 只验证 action boundary/parity，不输出收益/NAV/PnL/ReplayResult；
- `forbidden_action_audit.csv` clean；
- 执行报告明确未正式 replay、未生成 ReplayResult、未 provider/latest/default/production、未真实订单或目标仓位/权重/数量。

## 8. Reviewer Brief

RSR3 reviewer 必须检查：

1. 是否只生成 OrderIntentArtifact samples 和 parity smoke；
2. 是否没有正式 replay、ReplayResult、收益/NAV/PnL 结论；
3. 是否没有 provider/latest/default/production/frontend/daily/external pull；
4. 是否没有真实订单、broker、quick-trade、target position/weight/allocation/quantity；
5. forbidden field audit 是否 clean；
6. strategy decision audit 是否能证明 RSR2 合同生效；
7. OrderIntent contract validation 是否 pass；
8. baseline parity smoke 是否只验证 action boundary/parity；
9. RSR1 diagnostic artifact 是否未被直接作为 runtime StrategyRule input。

## 9. Command For Executor

```text
你是 RSR3 执行者。读取 mainline、RSR2 work/report/review、RSR2 artifacts 和 StrategyRule/OrderIntent/ReplayResult 合同。只根据 RSR2 合同生成 diagnostic-only、smoke-only OrderIntentArtifact samples 与 baseline parity smoke。必须输出 strategy_decision_audit、forbidden_field_audit、OrderIntent contract validation、baseline parity smoke 和 forbidden_action_audit。不要跑正式收益 replay，不要生成 ReplayResult 收益结论，不要 provider publish，不要 accepted latest switch，不要改 production/default/frontend/daily/latest，不要外部拉取，不要接 broker/quick-trade，不要输出 target_position/target_weight/allocation_weight/quantity instruction。完成后写 POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_EXECUTION_REPORT_CN.md。
```
