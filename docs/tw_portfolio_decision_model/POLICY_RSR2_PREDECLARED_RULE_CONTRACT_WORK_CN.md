---
created_at: 2026-06-27
status: work_document
phase: POLICY_RSR2_PREDECLARED_RULE_CONTRACT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_REVIEW_CN.md
previous_artifact_root: data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic
production_allowed: false
readonly_only: true
diagnostic_only: true
model_training_authorized: false
replay_authorized: false
order_intent_authorized: false
strategy_implementation_authorized: false
threshold_tuning_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
---

# POLICY_RSR2_PREDECLARED_RULE_CONTRACT_WORK_CN

## 1. Phase Goal

执行 `POLICY_RSR2_PREDECLARED_RULE_CONTRACT`。

本阶段只做预声明规则合同设计，不实现策略、不生成 `OrderIntentArtifact`、不跑 readonly replay、不生成 `ReplayResultArtifact`、不根据收益调参、不改 production/default/frontend/daily/latest/publish。

目标是把 RSR1 诊断中可讨论的 score bucket、score percentile/gap、rank delta、TWII market regime、holding-aware state 转换为少量、可审查、可在后续 RSR3/RSR4 执行的规则合同草案。规则数量不得超过 5 个。

## 2. Required Documents

执行者必须读取：

- `docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_REVIEW_CN.md`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/manifest.json`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/feature_schema.json`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/label_schema.json`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/input_lineage_links.json`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/feature_construction_audit.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/label_namespace_audit.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/consumer_forbidden_field_audit.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/pit_leakage_audit.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/diagnostic_summary.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/diagnostic_summary.md`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/forbidden_action_audit.csv`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

## 3. Allowed Outputs

建议输出：

```text
docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_REVIEW_CN.md
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/
```

RSR2 可在 artifact root 下输出以下设计文件：

- `manifest.json`
- `predeclared_rule_contracts.csv`
- `predeclared_rule_contracts.md`
- `rule_dependency_yaml_drafts/README.md`
- `rule_dependency_yaml_drafts/{rule}.yaml`
- `required_fields_matrix.csv`
- `pass_fail_gates.md`
- `forbidden_action_audit.csv`

这些 YAML 只能是 contract draft，不得被注册为 production/default 策略，不得触发 validator 以外的实现链路，不得生成 OrderIntent 或 ReplayResult。

## 4. Required Contract Content

每个预声明规则必须写明：

- `strategy_rule` stable snake_case name；
- `rule_family`，仅可来自 score bucket gate、rank momentum buy gate、rank deterioration sell gate、market regime action budget、score/rank/regime interaction；
- `objective` 与 `non_goals`；
- `diagnostic_only`、`readonly_only`、`not_default_candidate`、`not_production_candidate`；
- `required_core_fields`；
- `required_extensions`；
- `forbidden_fields`；
- `score_bucket_definition`；
- `score_percentile_or_gap_definition`；
- `rank_delta_definition`；
- `market_regime_definition`；
- `holding_state_definition`；
- `max_buy_count`；
- `max_sell_count`；
- `sell_boundary`；
- `buy_ordering`；
- `tie_breaker`；
- `no_trade_zone`；
- `turnover_or_action_budget_policy`；
- `expected_tradeoff`；
- `pass_fail_gates_for_later_replay`；
- `explicit_no_replay_in_rsr2`；
- `explicit_no_order_intent_in_rsr2`；
- `explicit_no_threshold_tuning_to_pnl`。

## 5. Required Fields Boundary

RSR2 规则合同只能声明后续 StrategyRule 可消费的 PIT-safe fields。默认允许字段：

```text
date / signal_date
instrument
model_name
model_family
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
current_holding_flag
cost_basis
```

若 RSR2 需要 score/rank/regime extension，必须在合同草案中明确声明来源和 PIT 语义：

```text
score_bucket
score_percentile_band
score_gap_to_top
top_score_dispersion_band
rank_1d_delta
rank_3d_delta
rank_5d_delta
rank_1d_direction
rank_3d_direction
rank_5d_direction
market_regime_diagnostic
market_risk_on_flag
market_risk_neutral_flag
market_risk_off_flag
market_crash_flag
holding_rank_support_flag
holding_score_support_flag
```

禁止作为规则输入、排序输入或 threshold selection 输入：

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

## 6. Predeclared Definition Requirements

### 6.1 Score Bucket / Percentile / Gap

执行者必须冻结 score bucket、score percentile band、score gap 或 top score dispersion 的定义。定义可以来自 RSR1 已固定分箱或明确简化后的合同分箱，但不得根据 replay PnL 或后验收益最大化重选。

必须说明：

- absolute score bucket thresholds；
- percentile band thresholds；
- score gap/top dispersion units；
- missing value policy；
- whether used for buy gate, sell gate, action budget, or no-trade zone。

### 6.2 Rank Delta

rank delta 必须定义为 current signal date rank 与历史可用 signal date rank 的差：

```text
rank_1d_delta = full_qlib_rank(t) - full_qlib_rank(previous available signal observation)
rank_3d_delta = full_qlib_rank(t) - full_qlib_rank(3 previous available signal observations)
rank_5d_delta = full_qlib_rank(t) - full_qlib_rank(5 previous available signal observations)
```

负值表示 rank 改善，正值表示 rank 恶化。不得读取未来 signal date、future return 或 label。

### 6.3 Market Regime

TWII regime 必须使用 signal date 当日或之前的 TWII close/MA/drawdown/volatility：

```text
risk_on
risk_neutral
risk_off
crash
```

合同必须写明：

- MA windows；
- drawdown window；
- volatility window；
- backward-asof rule；
- tie/missing policy；
- regime 如何影响 max buy/sell count、buy gate、sell priority 或 no-trade zone。

### 6.4 Holding-Aware State

holding-aware 规则只能使用当前 `PortfolioState` 或 RSR1 allowed state fields：

```text
current_holding_flag
cost_basis_present / cost_basis
holding_rank_support_flag
holding_score_support_flag
```

不得使用 realized/unrealized PnL、market value、cash、NAV、quantity instruction、target weight 或 execution fields 作为规则逻辑。

## 7. Rule Count Limit

RSR2 必须冻结不超过 5 个规则。

推荐最多覆盖以下 5 类，每类最多 1 个：

1. `score_bucket_regime_gate`
2. `rank_momentum_buy_gate`
3. `rank_deterioration_sell_gate`
4. `market_regime_action_budget`
5. `score_rank_regime_interaction`

若 RSR1 证据不足以支撑 5 个规则，应少于 5 个；不得为了凑满数量硬造规则。

## 8. Required Pass/Fail Gates For Later Phases

RSR2 必须冻结后续 RSR4/RSR5 才能检验的 pass/fail gates，但不得在 RSR2 执行这些检验。

至少包含：

- min active days；
- min action change rate vs baseline；
- max no-trade/all-cash dependence；
- max turnover or action count increase；
- fee/tax net-return gate；
- max drawdown gate；
- missing price/signal coverage gate；
- PIT/available_at gate；
- forbidden field/action gate；
- baseline clone rejection gate；
- regime-specific minimum sample count if rule is regime-specific。

任何 material margin 只能作为预声明 gate 写入，不得用 RSR2 replay 或收益搜索校准。

## 9. Forbidden Actions

RSR2 禁止：

- training / retraining；
- qlib refresh；
- LTR retrain 或 qlib+LTR adaptation；
- 读取 external data；
- StrategyRule implementation；
- OrderIntentArtifact generation；
- ReplayResultArtifact generation；
- replay rerun；
- PnL rule search；
- threshold tuning to return；
- 选择 best threshold / best rule / best bucket；
- provider publish；
- accepted latest switch；
- production/default/frontend/daily/latest 修改；
- broker、quick-trade、real order；
- target_position、target_weight、allocation_weight、quantity instruction 输出。

## 10. Stop Conditions

以下任一情况必须 STOP 并写 blocker：

- 规则需要读取 `diagnostic_label_*`、future return、realized PnL、execution、cash/NAV 或 replay return 才能定义；
- 规则数量超过 5 个；
- 执行者无法把阈值来源解释为预声明机制而非收益搜索；
- 需要跑 replay 才能决定规则合同；
- 需要生成 OrderIntent 才能完成本阶段；
- 需要修改 production/default/frontend/daily/latest/publish；
- RSR1 artifact 或合同证据缺失到无法审查。

## 11. Pass Criteria

RSR2 通过条件：

- 规则合同数量不超过 5 个；
- 每个规则都有 required fields、forbidden fields、score/rank/regime/holding definitions、max buy/sell、sell boundary、buy ordering、tie breaker、no-trade zone；
- 阈值与定义来自 RSR1 diagnostic mechanism 或 mainline 预设，不来自 replay PnL 搜索；
- 所有规则明确 `readonly_only=true`，并在进入 RSR3 前保持 `diagnostic_only=true` / `not_default_candidate=true`；
- pass/fail gates 完整，可供后续 RSR4/RSR5 验证；
- forbidden action audit clean；
- 执行报告明确未训练、未 replay、未 OrderIntent、未 production/default/latest/publish。

## 12. Reviewer Brief

RSR2 reviewer 必须检查：

1. 是否只做 predeclared rule contract design；
2. 规则数量是否不超过 5 个；
3. required fields 是否只来自标准 signal、PortfolioState 或明确 PIT-safe extension；
4. 是否没有 `diagnostic_label_*`、future return、realized PnL、execution、cash/NAV、replay return、broker/order、target/weight/quantity instruction；
5. score bucket/rank delta/market regime 定义是否清晰且 PIT-safe；
6. max_buy_count/max_sell_count、sell boundary、buy ordering、no-trade zone 是否冻结；
7. pass/fail gates 是否预声明且没有被收益调参污染；
8. 是否没有实现 StrategyRule、生成 OrderIntent、跑 replay、生成 ReplayResult；
9. 是否没有 production/default/frontend/daily/latest/publish/external pull。

## 13. Command For Executor

```text
你是 RSR2 执行者。读取本工作文档列出的 mainline、RSR1 review、RSR1 artifacts 和策略/OrderIntent/Replay 合同。只做 predeclared rule contract design，冻结不超过 5 个规则，输出合同表、draft dependency YAML 和 pass/fail gates。不要实现策略代码，不要生成 OrderIntent，不要跑 replay，不要生成 ReplayResult，不要调参到收益，不要 provider publish，不要 accepted latest switch，不要改 production/default/frontend/daily/latest，不要外部拉取。完成后写 docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_EXECUTION_REPORT_CN.md。
```
