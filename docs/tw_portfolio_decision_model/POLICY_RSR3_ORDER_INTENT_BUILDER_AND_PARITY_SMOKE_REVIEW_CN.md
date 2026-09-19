---
created_at: 2026-06-27
status: reviewed_rsr3_order_intent_builder_and_parity_smoke
phase: POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE
reviewer: RSR3
verdict: PASS_WITH_CONDITIONS
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr3_order_intent_builder_and_parity_smoke
next_work_doc: docs/tw_portfolio_decision_model/POLICY_RSR4_PREDECLARED_READONLY_REPLAY_WORK_CN.md
production_allowed: false
readonly_only: true
diagnostic_only: true
smoke_only: true
---

# Review Opinion And Next Work Document

## 1. Verdict

`PASS_WITH_CONDITIONS`.

RSR3 交付物满足本阶段核心目标：只生成 diagnostic-only / readonly-only / smoke-only 的 `OrderIntentArtifact` samples 和 baseline action-boundary parity smoke；未发现正式 replay、`ReplayResultArtifact`、收益/NAV/PnL/回撤/fee/tax 结论、provider/latest/default/production/frontend/daily/external pull、真实订单、broker/quick-trade、target position/weight/allocation/quantity instruction。

放行条件：进入 RSR4 前，执行者必须在 readonly replay 审计中补齐 `rsr2_market_regime_action_budget_v1` 的 `risk_neutral` regime-specific budget 覆盖，或明确说明窗口内无 `risk_neutral` active day 并在 coverage/regime audit 中标记为不可声明 regime-specific conclusion。RSR3 sample 已覆盖 `risk_on`、`risk_off`、`crash`，但未单独覆盖 `risk_neutral 1/1` 预算。

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. `strategy_decision_audit.csv` 对 `rsr2_market_regime_action_budget_v1` 明确审计了 `risk_on=2/1`、`risk_off=0/1`、`crash=0/2`，但没有 `risk_neutral=1/1` 的单独 sample/audit 行。由于 RSR3 是 smoke-only，不阻断本阶段；RSR4 必须补齐 `risk_neutral` coverage 或禁止对 risk_neutral 做 regime-specific replay 结论。
2. RSR3 使用 synthetic/golden fixture，而非真实 runtime `ModelSignalArtifact`。这符合 RSR3 work doc 的 smoke 边界，也意味着这些 samples 不能作为策略有效性、收益、生产候选或 replay 结果证据。RSR4 必须重新接入标准 `OrderIntentArtifact -> ReplayExecution -> ReplayResultArtifact` readonly 链路。
3. `forbidden_field_audit.csv` 逐字段检查 RSR3 work doc 列出的 forbidden fields；`quantity`、`shares`、`lots` 等额外 size 字段由 `order_intent_contract_validation.json` 的 `target_weight_allocation_size_fields_absent` 覆盖。两者合并后 clean。

## 3. Mainline Compliance

- 范围合规：RSR3 artifact root 只包含 OrderIntent samples、synthetic fixture、strategy decision audit、forbidden field/action audit、contract validation、baseline parity smoke；未发现 replay-like output 文件。
- sample 覆盖合规：RSR2 5 条冻结规则均有 sample：`rsr2_score_bucket_regime_gate_v1`、`rsr2_rank_momentum_buy_gate_v1`、`rsr2_rank_deterioration_sell_gate_v1`、`rsr2_market_regime_action_budget_v1`、`rsr2_score_rank_regime_interaction_v1`。
- manifest flags 合规：root manifest 与每个 sample manifest 均声明 `diagnostic_only=true`、`readonly_only=true`、`smoke_only=true`、`not_valid_strategy_evidence=true`、`not_default_candidate=true`、`not_production_candidate=true`、`not_order=true`、`not_target_position=true`、`not_investment_advice=true`、`no_replay_return_conclusion=true`。
- OrderIntent 合同合规：所有 `order_intents.csv` 均包含 required fields，`intent_action` 值域为 `buy/sell/hold/skip`，每日 buy/sell count 未超过 `max_buy_count/max_sell_count`。
- Strategy decision audit 合规：审计覆盖 sell boundary、buy ordering、tie breaker、no-trade zone、max buy/sell count；market regime action budget 已审计 risk_on/risk_off/crash，risk_neutral 需在 RSR4 补齐或声明无结论。
- Forbidden field/action 合规：root forbidden field audit 和 contract validation 均为 pass；未发现 future/label/PnL/execution/cash/NAV/broker/order/target/weight/allocation/quantity instruction 字段进入 OrderIntent。
- Baseline parity smoke 合规：只验证 top50 exit boundary、buy-score ordering、one-day action cap；未输出收益、NAV、PnL、fee/tax、ReplayResult 或正式 replay 结论。
- RSR1 boundary 合规：manifest、execution report、script 和 fixture manifest 均声明未直接把 RSR1 diagnostic dataset 作为 StrategyRule runtime input；RSR1 仅作为 RSR2 frozen mechanism 来源。

## 4. Evidence Checked

已读取并核对：

- `docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_EXECUTION_REPORT_CN.md`
- `scripts/build_tw_policy_rsr3_order_intent_smoke.py`
- RSR3 root artifacts: `manifest.json`、`order_intent_sample_index.csv`、`strategy_decision_audit.csv`、`forbidden_field_audit.csv`、`order_intent_contract_validation.json`、`baseline_parity_smoke.csv`、`baseline_parity_smoke.md`、`forbidden_action_audit.csv`
- all files under `order_intent_samples/` for all 5 RSR2 rules
- RSR3 synthetic fixture: `manifest.json`、`model_signal_extension_fixture.csv`、`extension_source_audit.csv`、`portfolio_state_manifest.json`
- RSR2 artifacts: `predeclared_rule_contracts.csv`、`required_fields_matrix.csv`、`pass_fail_gates.md`、all draft YAML files
- modular contracts: `STRATEGY_RULE_CONTRACT_CN.md`、`ORDER_INTENT_CONTRACT_CN.md`、`REPLAY_RESULT_CONTRACT_CN.md`、`TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`、`NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

独立校验结果：

```text
summary= [('rsr2_market_regime_action_budget_v1', 8, {'sell': 4, 'buy': 2, 'skip': 2}), ('rsr2_rank_deterioration_sell_gate_v1', 3, {'sell': 1, 'buy': 1, 'hold': 1}), ('rsr2_rank_momentum_buy_gate_v1', 3, {'sell': 1, 'buy': 1, 'skip': 1}), ('rsr2_score_bucket_regime_gate_v1', 3, {'sell': 1, 'buy': 1, 'skip': 1}), ('rsr2_score_rank_regime_interaction_v1', 3, {'sell': 1, 'buy': 1, 'hold': 1})]
problems= []
validation_status= pass
```

Replay-like file search returned no files for `summary.csv/actions.csv/daily_nav.csv/position_snapshots.csv/coverage_audit.csv/execution_audit.csv/*ReplayResult*/*replay_result*` under the RSR3 artifact root.

## 5. Missing Evidence Or Open Questions

1. `risk_neutral` budget evidence is missing in RSR3 smoke samples. This is accepted only as an RSR4 condition, not as a repair blocker for RSR3.
2. RSR3 did not run project-wide modular validators from `NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`; the RSR3 work doc required local contract validation, which is present and pass. RSR4 should use standard replay validators once actual `ReplayResultArtifact` is authorized.
3. Synthetic fixture proves builder contract shape, not live data availability. RSR4 must produce coverage, PIT/leakage, missing price, and fee/tax audits from historical readonly inputs.

## 6. Forbidden Actions Audit

未发现以下 forbidden actions：

- training / retraining；
- qlib refresh、LTR retrain 或 qlib+LTR adaptation；
- external data pull；
- formal replay；
- `ReplayResultArtifact` generation；
- replay PnL search、threshold tuning、best threshold/rule/bucket selection；
- provider publish、accepted latest switch；
- production/default/frontend/daily/latest 修改；
- broker、quick-trade、real order；
- target_position、target_weight、allocation_weight、quantity instruction 输出。

证据：`forbidden_action_audit.csv` 共 12 行，全部为 `PASS_NOT_PERFORMED`；sample-level `forbidden_action_audit.json` 均为 `status=pass`；root manifest 明确 `formal_replay_performed=false`、`replay_result_generated=false`、`external_data_pull_performed=false`、`provider_publish_performed=false`、`accepted_latest_switch_performed=false`、`broker_quick_trade_real_order_performed=false`、`target_position_weight_allocation_quantity_instruction_generated=false`。

## 7. Next Work Document

已写下一步工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_RSR4_PREDECLARED_READONLY_REPLAY_WORK_CN.md
```

RSR4 只允许对 RSR2 冻结规则、经 RSR3 合同验证通过的 OrderIntent 路径做 historical readonly replay。必须使用标准链路：

```text
OrderIntentArtifact -> ReplayExecution -> ReplayResultArtifact
```

RSR4 不得训练、不得调参到收益、不得改规则阈值、不得 production/default/latest/publish、不得真实订单/target position/weight/quantity。必须包含 fee/tax、turnover、cash/no-trade、coverage、PIT/leakage、forbidden field/action、baseline clone、missing price audit。RSR4 可以产生 replay result artifacts，但只能作为 historical readonly research artifacts，不能作为 production candidate。

## 8. Command For Executor Or Coordinator

```text
你是 RSR4 执行者。读取 POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md、POLICY_RSR2_PREDECLARED_RULE_CONTRACT_REVIEW_CN.md、POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_REVIEW_CN.md、POLICY_RSR4_PREDECLARED_READONLY_REPLAY_WORK_CN.md、RSR2 合同 artifacts、RSR3 OrderIntent samples/validation/audits，以及 StrategyRule/OrderIntent/ReplayResult 合同。只对 RSR2 冻结规则、经 RSR3 合同验证通过的 OrderIntent 路径做 historical readonly replay，必须通过 OrderIntentArtifact -> ReplayExecution -> ReplayResultArtifact 标准链路。不得训练、不得调参到收益、不得改规则阈值、不得 production/default/latest/publish、不得真实订单、不得 target_position/target_weight/allocation_weight/quantity instruction。输出 ReplayResultArtifact research artifacts、fee/tax/turnover/cash/no-trade/coverage/PIT/leakage/forbidden field/action/baseline clone/missing price audits，并补齐或明确 risk_neutral regime-specific budget 覆盖。完成后写 POLICY_RSR4_PREDECLARED_READONLY_REPLAY_EXECUTION_REPORT_CN.md。
```
