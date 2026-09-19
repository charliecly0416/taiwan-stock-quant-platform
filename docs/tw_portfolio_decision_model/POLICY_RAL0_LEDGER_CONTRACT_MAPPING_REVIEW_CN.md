---
created_at: 2026-06-23
status: review_pass_ready_for_ral1_baseline_action_ledger_build
phase_reviewed: RAL0_LEDGER_CONTRACT_AND_REPLAY_MAPPING_FREEZE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ACTION_LEDGER_RULE_ATTRIBUTION_MAINLINE_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL0_LEDGER_CONTRACT_MAPPING_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping
verdict: PASS_READY_FOR_RAL1_BASELINE_ACTION_LEDGER_BUILD_AND_PARITY
strict_test_authorized: false
training_authorized: false
rule_experiment_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# RAL0 Ledger Contract Mapping 审查报告

## 1. 审查结论

结论：

```text
PASS_READY_FOR_RAL1_BASELINE_ACTION_LEDGER_BUILD_AND_PARITY
```

执行者完成了 RAL0 授权范围：

```text
1. 已输出 RAL0 manifest 与 source artifact inventory。
2. 已定义 ActionSymbolDailyLedgerArtifact schema。
3. 已定义 action_source / action_type / reason_code 映射。
4. 已定义 PnL / cost / turnover attribution 口径。
5. 已定义 missing field policy。
6. 已输出 forbidden consumer audit。
7. 已设计 validator / golden samples。
8. 未训练模型。
9. 未生成大规模 ledger。
10. 未运行规则收益实验。
11. 未运行或读取 strict_test。
12. 未输出 OrderIntent / target_weight / target_position / quantity / broker_order。
13. 未做 provider/latest/monitor/frontend/Agent/broker/production 扩权。
```

本审查允许进入：

```text
RAL1: Baseline Action Ledger Build And Parity
```

但 RAL1 仍只授权 baseline ledger build / parity，不授权 PBA attribution、新规则、训练、strict_test 或任何生产链路。

## 2. 产物完整性

确认存在：

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

评价：

```text
PASS
```

## 3. Source Artifact Inventory 审查

`source_artifact_inventory.csv` 覆盖了 RAL0 必须盘点的主要来源：

```text
frozen_qlib_signal
pba1_baseline_action_snapshot
pba1_baseline_parity_replay_ledger
pba2_active_policy_decision
pba2_active_overlay_replay_ledger
pba3_active_policy_decision
pba3_r_active_policy_decision
pba_rc_regime_definition
```

关键判断：

```text
1. frozen qlib signal 只作为 date / symbol / rank / score 来源。
2. PBA1 baseline snapshot 作为 baseline action row 主要来源。
3. PBA1 replay ledger 被正确标记为 portfolio-level reconciliation source。
4. PBA2/PBA3/PBA3-R 只作为既有 diagnostic action 来源。
5. PBA-RC 只作为 PIT-safe regime design 来源。
6. symbol-level PnL、execution price、shares、notional 没有被伪造成 native 字段。
```

评价：

```text
PASS
```

## 4. Schema 审查

`action_symbol_daily_ledger_schema.json` 固定：

```text
artifact_type = ActionSymbolDailyLedgerArtifact
schema_version = ral_action_symbol_daily_ledger_v1
粒度 = date x symbol x action_source x action_type
```

schema 覆盖主线要求的字段域：

```text
date / symbol
action_source / action_type / baseline_action_type / policy_or_rule_action_type
rank / score / score_gap / score_zscore
holding / position / cash / price / diagnostic shares and notional
turnover / fee / sell_tax / gross_pnl / realized_pnl / unrealized_pnl / net_pnl / nav_contribution
holding_age / regime / baseline_state
reason_code / source_signal_artifact / source_replay_artifact
simulation_only / readonly_research_only / production_allowed
```

禁止字段已列入 schema：

```text
target_weight
target_position
quantity
order_size
broker_order
production_order_id
```

评价：

```text
PASS
```

注意：当前 schema 中 `missing_field_status` 是 row-level 单字段。RAL1 若同一行内同时包含 native 与 proxy / missing 字段，必须额外输出 field-level availability audit，避免 row-level status 掩盖单字段缺失。

## 5. Attribution 口径审查

`pnl_cost_turnover_attribution_design.md` 明确：

```text
primary = net_pnl_after_fee_tax_contribution
```

并要求 RAL1 reconciliation：

```text
sum fee ~= PBA1 fee
sum sell tax ~= PBA1 sell tax
sum turnover ~= PBA1 turnover
sum net pnl after fee tax ~= PBA1 daily net PnL
daily equity path ~= PBA1 daily replay equity path
```

关键通过点：

```text
1. 没有把 gross return 作为成功主指标。
2. 没有把低成本 / 低换手 / cash/no-trade 作为成功。
3. 明确 portfolio-level totals 不能直接冒充 symbol/action contribution。
4. no_extra_action 必须与 active changed decisions 分离。
5. 诊断股数/金额不得映射为 OrderIntent 或生产订单语义。
```

评价：

```text
PASS
```

## 6. Missing Field Policy 审查

`missing_field_policy.md` 冻结四类状态：

```text
native
derived_proxy
not_available_in_current_replay
requires_future_data_contract
```

并明确禁止：

```text
1. 缺失 PnL/cost/turnover/cash/price/shares/notional 默认填 0。
2. 使用 strict_test 填补缺口。
3. 抓取新外部数据或切换 provider。
4. 将 diagnostic 字段解释为 production order 或投资建议。
```

评价：

```text
PASS
```

## 7. Validator / Golden Samples 审查

`validator_design.md` 覆盖：

```text
contract checks
safety checks
RAL1+ reconciliation checks
```

`golden_sample_design.md` 覆盖正例：

```text
baseline buy
PBA2 blocked buy
no_extra_action
```

覆盖负例：

```text
forbidden target/broker field
production_allowed=true
simulation_only=false
missing PnL/cost/turnover silently filled with zero
strict-test source
no_extra_action without clone audit
```

评价：

```text
PASS_FOR_RAL0_DESIGN_SCOPE
```

说明：RAL0 主线要求是设计 validator / golden samples，未要求实现脚本。RAL1 必须把 baseline ledger 的 validator / golden sample report 落为可运行产物。

## 8. 安全边界审查

`manifest.json` 与执行报告声明：

```text
readonly_only = true
simulation_only = true
production_allowed = false
training_run = false
strict_test_used = false
large_scale_ledger_generated = false
rule_return_experiment_run = false
order_intent_output = false
```

未发现 RAL0 越权迹象。

评价：

```text
PASS
```

## 9. 必须带入 RAL1 的约束

RAL1 执行者必须特别处理：

```text
1. 不得把 PBA1 portfolio-level net_return 直接分摊成 symbol PnL 后冒充 native。
2. 若使用 price / holding / trade reconstruction，必须记录 price_source、position_source、cost_model_source。
3. 每个 PnL/cost/turnover 字段必须有 field-level availability/status。
4. baseline_action_symbol_daily_ledger.csv 必须能回到 baseline replay daily NAV path。
5. RAL1 只构建 baseline，不得引入 PBA2/PBA3/PBA-RC attribution。
6. strict_test 仍只能 declared only，不得读取或输出 metrics。
```

## 10. 下一步

本审查已写出 RAL1 工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_RAL1_BASELINE_ACTION_LEDGER_BUILD_AND_PARITY_WORK_CN.md
```

执行者应按该文档进入 RAL1。若 RAL1 无法实现 baseline ledger 与 PBA1 replay reconciliation，必须 STOP 回到统筹，不得进入 RAL2。
