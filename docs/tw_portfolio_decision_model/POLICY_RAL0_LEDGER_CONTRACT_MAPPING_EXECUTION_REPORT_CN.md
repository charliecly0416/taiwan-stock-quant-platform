---
created_at: 2026-06-23T01:24:35+00:00
status: executed_ral0_ledger_contract_mapping
phase: RAL0_LEDGER_CONTRACT_AND_REPLAY_MAPPING_FREEZE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ACTION_LEDGER_RULE_ATTRIBUTION_MAINLINE_CN.md
artifact_root: data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping
strict_test_used: false
training_run: false
production_allowed: false
large_scale_ledger_generated: false
rule_return_experiment_run: false
---

# RAL0 Ledger Contract Mapping 执行报告

## 1. Scope

本轮只完成 RAL0：冻结 `ActionSymbolDailyLedgerArtifact` 合同，并把现有 frozen qlib、PBA1、PBA2、PBA3、PBA3-R、PBA-RC diagnostic artifacts 可提供的字段映射到账本字段。

本轮没有训练模型，没有运行收益规则实验，没有运行或读取 strict_test，没有输出 OrderIntent，没有接 provider/latest/monitor/frontend/Agent/broker/production。

## 2. Documents Read

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ACTION_LEDGER_RULE_ATTRIBUTION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MODEL_RESEARCH_ROUTE_CLOSURE_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

## 3. Outputs

```text
data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping/manifest.json
data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping/source_artifact_inventory.csv
data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping/action_symbol_daily_ledger_schema.json
data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping/action_enum_design.md
data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping/pnl_cost_turnover_attribution_design.md
data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping/missing_field_policy.md
data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping/forbidden_consumer_audit.csv
data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping/validator_design.md
data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping/golden_sample_design.md
```

## 4. Source Artifact Inventory Summary

盘点结果写入 `source_artifact_inventory.csv`。关键结论：

```text
frozen qlib signal:
  可提供 date / symbol / rank / score / signal source。

PBA1 baseline_action_snapshot:
  可提供 baseline action rows、rank、score、holding before/after、holding age。

PBA1 baseline_parity_replay_ledger:
  可提供 portfolio-level cash/cost/turnover/return reconciliation totals。
  不能单独证明 symbol-level PnL。

PBA2/PBA3/PBA3-R active_policy_decision_artifact:
  可提供 overlay action、reason_code、action source、baseline action。
  不能单独提供 execution price、shares、symbol PnL 或 action-level cost。

PBA-RC regime artifacts:
  可提供 PIT-safe regime label design。
  需要 RAL1/RAL2 materialized join 才能进入 row-level ledger。
```

## 5. Schema Decision

`action_symbol_daily_ledger_schema.json` 冻结粒度：

```text
date x symbol x action_source x action_type
```

核心字段覆盖：

```text
date / symbol / action / baseline action / overlay action
rank / score / score_gap / score_zscore
holding / position / cash / price / diagnostic shares and notional
turnover / fee / sell tax / gross PnL / realized PnL / unrealized PnL / net PnL / NAV contribution
holding_age / market_regime / volatility_regime / score_dispersion_regime / baseline_state
reason_code / source_signal_artifact / source_replay_artifact
simulation_only / readonly_research_only / production_allowed
```

缺失或非原生字段必须标记为 `derived_proxy`、`not_available_in_current_replay` 或 `requires_future_data_contract`，不得伪造。

## 6. Attribution Policy

RAL1 必须先证明 baseline ledger 能 reconciliation 到 PBA1 replay：

```text
sum fee ~= replay fee
sum sell tax ~= replay sell tax
sum turnover ~= replay turnover
sum net pnl after fee tax ~= replay daily net PnL
daily NAV path ~= replay NAV path
```

现有 PBA replay ledger 有 portfolio-level totals，但不完整提供 native symbol-level PnL/cost，因此 RAL1 必须重建或明确 proxy，不得把 portfolio-level return 直接冒充 symbol/action contribution。

## 7. Safety Boundary

禁止项已写入 `forbidden_consumer_audit.csv`。RAL ledger 仍是 readonly research artifact：

```text
simulation_only = true
readonly_research_only = true
production_allowed = false
strict_test_used = false
training_run = false
```

允许的诊断股数/金额字段只限：

```text
shares_diagnostic
notional_diagnostic
trade_notional_diagnostic
```

这些字段不得映射为 OrderIntent、生产订单、目标仓位或目标权重。

## 8. Validator / Golden Samples

`validator_design.md` 定义三层检查：

```text
contract checks
safety checks
RAL1+ reconciliation checks
```

`golden_sample_design.md` 覆盖 baseline buy、PBA2 blocked buy、no-extra-action 正例，以及 forbidden field、安全标志、missing field 伪造、strict_test 来源、baseline clone 误判等负例。

## 9. RAL1 Readiness

RAL0 合同可以支持 reviewer 编写 RAL1 baseline ledger build 工作文档。但 RAL1 必须先解决：

```text
1. 从现有 replay/价格/持仓重建 date x symbol PnL/cost/turnover。
2. 明确 native vs derived_proxy vs requires_future_data_contract。
3. 做 daily NAV、fee、tax、turnover reconciliation。
4. 继续禁止 strict_test、训练、OrderIntent、production。
```
