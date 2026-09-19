---
created_at: 2026-06-27
status: work_document
phase: POLICY_RSR4_PREDECLARED_READONLY_REPLAY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_REVIEW_CN.md
previous_artifact_root: data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr3_order_intent_builder_and_parity_smoke
production_allowed: false
readonly_only: true
historical_research_only: true
model_training_authorized: false
threshold_tuning_authorized: false
rule_threshold_change_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
default_or_production_change_allowed: false
real_order_allowed: false
target_position_weight_quantity_allowed: false
---

# POLICY_RSR4_PREDECLARED_READONLY_REPLAY_WORK_CN

## 1. Phase Goal

执行 `POLICY_RSR4_PREDECLARED_READONLY_REPLAY`。

本阶段只允许对 RSR2 冻结规则、且已经通过 RSR3 合同验证的 `OrderIntentArtifact` 路径做 historical readonly replay。目标是验证预声明规则在标准模块链路下的历史只读表现、成本、覆盖、现金/no-trade、PIT/leakage 和 baseline clone 风险。

标准链路必须是：

```text
ModelSignalArtifact + PortfolioState + StrategyRuleConfig
  -> StrategyRule / OrderIntentArtifact builder
  -> OrderIntentArtifact
  -> ReplayExecution
  -> ReplayResultArtifact
```

Replay 模块不得重新实现策略逻辑，不得绕过 `OrderIntentArtifact` 直接从信号/CSV 产生交易结果。

## 2. Required Documents And Artifacts

执行者必须读取：

- `docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_REVIEW_CN.md`
- RSR2 artifacts: `manifest.json`、`predeclared_rule_contracts.csv`、`required_fields_matrix.csv`、`pass_fail_gates.md`、`forbidden_action_audit.csv`、all draft YAML files
- RSR3 artifacts: `manifest.json`、`order_intent_sample_index.csv`、`strategy_decision_audit.csv`、`forbidden_field_audit.csv`、`order_intent_contract_validation.json`、`baseline_parity_smoke.csv`、`forbidden_action_audit.csv`、all sample manifests/order_intents/schema/audits
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

## 3. Allowed Outputs

RSR4 可输出：

```text
docs/tw_portfolio_decision_model/POLICY_RSR4_PREDECLARED_READONLY_REPLAY_EXECUTION_REPORT_CN.md
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr4_predeclared_readonly_replay/
```

RSR4 可以产生 `ReplayResultArtifact`，但必须同时声明：

```text
historical_readonly_research_artifact=true
not_production_candidate=true
not_default_candidate=true
not_investment_advice=true
not_order=true
not_target_position=true
no_provider_publish=true
no_accepted_latest_switch=true
```

## 4. Required Work

### 4.1 RSR2 Frozen Rule Boundary

只允许使用 RSR2 冻结的 5 条规则：

- `rsr2_score_bucket_regime_gate_v1`
- `rsr2_rank_momentum_buy_gate_v1`
- `rsr2_rank_deterioration_sell_gate_v1`
- `rsr2_market_regime_action_budget_v1`
- `rsr2_score_rank_regime_interaction_v1`

不得新增规则、删除规则、改阈值、改 rule_family、改 sell boundary、改 buy ordering、改 tie breaker、改 no-trade zone、改 max buy/sell count。不得根据 replay 收益调参。

### 4.2 OrderIntent Path Requirement

RSR4 必须先为历史窗口生成或读取标准 `OrderIntentArtifact`，再交给 replay execution。

`OrderIntentArtifact` 必须通过 RSR3 同等或更严格 validation：

- required fields 全部存在；
- `intent_action` 只允许 `buy/sell/hold/skip`；
- 每日 buy/sell intent 数不超过 RSR2 max 和 regime-specific budget；
- 不含 forbidden fields；
- 不含 target_position / target_weight / allocation_weight / quantity instruction；
- manifest 声明 readonly/research/non-production flags。

### 4.3 ReplayResultArtifact Requirement

Replay 输出必须符合 `REPLAY_RESULT_CONTRACT_CN.md`，至少包含：

```text
manifest.json
summary.csv
actions.csv
daily_nav.csv
position_snapshots.csv
coverage_audit.csv
position_integrity_audit.csv
forbidden_field_audit.csv
execution_audit.csv
forbidden_action_audit.json
```

可选但建议：

```text
skipped_actions.csv
daily_cash_audit.csv
input_manifest_links.json
baseline_clone_audit.csv
fee_tax_turnover_audit.csv
regime_budget_audit.csv
missing_price_audit.csv
pit_leakage_audit.csv
cash_no_trade_audit.csv
```

### 4.4 Fee/Tax And Turnover

必须报告并审计：

- commission / fee；
- transaction tax；
- gross vs net gap；
- action_count、buy_count、sell_count；
- turnover proxy；
- candidate vs baseline turnover delta；
- high-turnover gross-only rejection rule。

不得只报告 gross return。任何收益/回撤结论必须是 after fee/tax 的 historical readonly research result。

### 4.5 Cash / No-trade Audit

必须报告并审计：

- daily cash；
- cash share；
- cash_gt_90pct_day_share；
- no-trade days；
- skipped action reasons；
- active days；
- whether improvement is mainly all-cash/no-trade。

不得接受 all-cash/no-trade 伪改善，除非按 RSR2 pass/fail gates 明确分类为 defensive tradeoff 并完整审计。

### 4.6 Coverage And Missing Price Audit

必须报告并审计：

- requested_start_date / requested_end_date；
- actual_start_date / actual_end_date；
- trading_day_count / signal_day_count / price_day_count；
- missing_signal_day_count / missing_price_day_count；
- missing price skip reason；
- no silent execution；
- replay window 不得漂移到请求窗口之外。

### 4.7 PIT / Leakage Audit

必须证明：

- consumed signal/regime/holding fields have available_at/asof <= signal_date；
- rank deltas only use historical signal observations；
- market regime uses TWII rows <= signal_date；
- no diagnostic_label/future return/forward return/label/relevance/PnL/execution/cash/NAV/replay_return/broker/order/target/weight/quantity field enters StrategyRule or OrderIntent；
- replay results do not modify OrderIntent or feed back into ranking/threshold selection。

### 4.8 Forbidden Field / Action Audit

必须输出 forbidden field/action audit，覆盖至少：

```text
diagnostic_label_*
future_return_*
future_excess_return_*
forward_return_*
label_*
relevance_10d_top_heavy
ltr_relevance_label
realized_pnl / realized_return / unrealized_pnl as StrategyRule input
execution_price / execution_date / next_open / next_close as StrategyRule input
cash / cash_after / nav / equity / daily_return / replay_return as StrategyRule input
broker / broker_order_id / order_id / quick_trade
target_position / target_weight / allocation_weight / quantity_instruction
provider_publish / accepted_latest_switch / production/default/frontend/daily/latest change
```

### 4.9 Baseline Clone Audit

必须与同一 baseline 比较 action boundary 和 action set，不得只比较收益。至少报告：

- active signal days；
- action difference rate vs baseline；
- action Jaccard similarity；
- baseline clone rejection：action difference rate < 5% 或 action Jaccard similarity > 0.95；
- same baseline price/fee/tax/execution assumptions。

### 4.10 Regime Budget Audit

必须对 `rsr2_market_regime_action_budget_v1` 输出 regime-specific budget audit：

- risk_on: max_buy=2 / max_sell=1；
- risk_neutral: max_buy=1 / max_sell=1；
- risk_off: max_buy=0 / max_sell=1；
- crash: max_buy=0 / max_sell=2。

由于 RSR3 smoke 未单独覆盖 risk_neutral，RSR4 必须补齐 risk_neutral active-day audit；若历史窗口没有 risk_neutral active day，必须明确 `risk_neutral_conclusion_allowed=false`。

### 4.11 Result Classification

RSR4 可按 RSR2 predeclared gates 输出 Type A/B/C preliminary classification，但只能是 historical readonly research artifact：

```text
Type A: net_return_after_fee_tax >= baseline + 2 percentage points, max_drawdown not materially worse
Type B: return loss <= 15% relative, max_drawdown improves >= 20% relative
Type C: regime-specific candidate, sufficient regime sample, no broad damage
```

不得接受：baseline clone、all-cash/no-trade、high-turnover gross-only、fee/tax omitted、single-window-only、replay PnL 后验调参。

## 5. Forbidden Actions

RSR4 禁止：

- training / retraining；
- qlib refresh；
- LTR retrain 或 qlib+LTR adaptation；
- external data pull，除非 coordinator 另行授权固定 historical readonly source；
- threshold tuning to returns；
- 修改 RSR2 冻结阈值或规则；
- 选择 best threshold / best rule / best bucket；
- provider publish；
- accepted latest switch；
- production/default/frontend/daily/latest 修改；
- broker、quick-trade、real order；
- target_position、target_weight、allocation_weight、quantity instruction 输出；
- 把 replay result 包装为 production candidate 或投资建议。

## 6. Stop Conditions

以下任一情况必须 STOP 并写 blocker：

- 无法通过 `OrderIntentArtifact -> ReplayExecution -> ReplayResultArtifact` 标准链路；
- replay 需要重新实现策略逻辑或绕过 OrderIntent；
- 需要修改 RSR2 冻结阈值/规则才能运行；
- required price/signal/portfolio state 缺失且无法审计 skip；
- PIT/available_at 无法证明；
- forbidden field/action audit 出现 fail；
- 需要 provider publish、accepted latest switch、production/default/frontend/daily/latest 修改；
- 需要真实订单、broker/quick-trade、target position/weight/allocation/quantity。

## 7. Pass Criteria

RSR4 通过条件：

- 每条 RSR2 冻结规则都有 historical readonly ReplayResultArtifact，或有清晰 blocker；
- 所有 replay 均由合规 OrderIntentArtifact 驱动；
- ReplayResultArtifact 文件齐全并通过合同校验；
- fee/tax、turnover、cash/no-trade、coverage、PIT/leakage、forbidden field/action、baseline clone、missing price audit 齐全；
- `rsr2_market_regime_action_budget_v1` 的 risk_on/risk_neutral/risk_off/crash budget audit 完整，或明确无样本 regime 不允许结论；
- 没有 production/default/latest/publish/real-order/target/weight/quantity；
- 执行报告明确结果是 historical readonly research artifact，不是 production candidate。

## 8. Reviewer Brief

RSR4 reviewer 必须检查：

1. 是否只对 RSR2 冻结规则和 RSR3 合同验证路径做 readonly replay；
2. 是否使用标准 `OrderIntentArtifact -> ReplayExecution -> ReplayResultArtifact` 链路；
3. 是否没有训练、调参到收益、改规则阈值、production/default/latest/publish；
4. 是否没有真实订单、broker/quick-trade、target position/weight/allocation/quantity；
5. ReplayResultArtifact 是否符合合同；
6. fee/tax、turnover、cash/no-trade、coverage、PIT/leakage、forbidden field/action、baseline clone、missing price audit 是否齐全；
7. market regime budget 是否覆盖 risk_on/risk_neutral/risk_off/crash，尤其补齐 RSR3 缺失的 risk_neutral；
8. 是否未把 replay result 作为 production candidate、默认策略或投资建议。

## 9. Command For Executor

```text
你是 RSR4 执行者。读取 mainline、RSR2 review/artifacts、RSR3 execution/review/artifacts 和 StrategyRule/OrderIntent/ReplayResult 合同。只对 RSR2 冻结规则、经 RSR3 合同验证通过的 OrderIntent 路径做 historical readonly replay，必须使用 OrderIntentArtifact -> ReplayExecution -> ReplayResultArtifact 标准链路。不得训练、不得调参到收益、不得改规则阈值、不得 production/default/latest/publish、不得真实订单、不得 target_position/target_weight/allocation_weight/quantity instruction。必须输出 ReplayResultArtifact research artifacts，以及 fee/tax、turnover、cash/no-trade、coverage、PIT/leakage、forbidden field/action、baseline clone、missing price audit；必须补齐或明确 risk_neutral regime-specific budget 覆盖。完成后写 POLICY_RSR4_PREDECLARED_READONLY_REPLAY_EXECUTION_REPORT_CN.md。
```
