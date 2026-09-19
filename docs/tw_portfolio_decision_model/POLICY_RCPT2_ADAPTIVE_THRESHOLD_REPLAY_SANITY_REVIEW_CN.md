---
created_at: 2026-06-24
status: rcpt2_independent_review_completed
phase: RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY
work_doc: docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_EXECUTION_REPORT_CN.md
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_REVIEW_CN.md
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity
verdict: PASS_READY_FOR_RCPT3_CLOSURE_REVIEW_WORK_DOC
readonly_review: true
policy_replay_performed_by_reviewer: false
risk_control_replay_performed_by_reviewer: false
model_training_performed_by_reviewer: false
strict_test_performed_by_reviewer: false
production_or_order_chain_change_performed_by_reviewer: false
---

# RCPT2 Adaptive Threshold Replay Sanity 独立审查报告

## 1. Verdict

`PASS_READY_FOR_RCPT3_CLOSURE_REVIEW_WORK_DOC`

RCPT2 执行产物满足工作文档 gate：root files 与 5 条规则子目录齐全，只回放 RCPT1 冻结的 5 条规则，未发现新增规则、调阈值、H03 top_40_60 扩展、H09 trigger、future leakage、replay 后调参、strict_test、训练、生产链路或订单链路越权。

本次通过只授权进入：

```text
RCPT3 closure review work doc
```

不授权：

```text
strict_test
training
production/default/provider/frontend/Agent/monitor/order chain integration
OrderIntentArtifact
target_weight / target_position / quantity_instruction
```

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. `rules/*/actions.csv` 是 replay accounting ledger，包含 `quantity`、`execution_price`、`cash_after`、`position_after` 等结算字段；这些字段在 replay ledger 场景下可接受，但不能被下游误读为 OrderIntent 或实盘订单建议。
   本轮不阻塞，因为 `order_intent_artifact` 明确为 `rcpt2_adaptive_threshold_replay_internal_ledger_not_order_intent`，且 `diagnostic_semantics_audit.json`、`forbidden_action_audit.csv`、执行报告和 `execution_audit.csv` 均声明 internal replay ledger only、not OrderIntent、not order、not target_weight/target_position/quantity_instruction。未发现 broker、quick-trade、target_weight、target_position、quantity_instruction 字段。

## 3. Required Files / Directory Completeness

通过。

已核对 RCPT2 root 必需文件全部存在：

```text
manifest.json
replay_source_manifest.json
adaptive_rule_replay_summary.csv
adaptive_rule_baseline_comparison.csv
adaptive_rule_gate_decision.csv
risk_metric_summary_by_rule.csv
cash_no_trade_audit_by_rule.csv
turnover_fee_tax_audit_by_rule.csv
action_count_audit_by_rule.csv
concentration_audit_by_rule.csv
threshold_contract_compliance_audit.csv
diagnostic_semantics_audit.json
anti_overfit_and_no_2022_replay_tuning_audit.csv
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

每条规则子目录均存在，且每条规则均包含：

```text
summary.csv
nav.csv
actions.csv
position_snapshots.csv
rule_trigger_ledger.csv
execution_audit.csv
```

未发现 `rules/` 下额外规则目录。实际 replayed rule set 为：

```text
RCPT1_RULE_01
RCPT1_RULE_02
RCPT1_RULE_03
RCPT1_RULE_04
RCPT1_RULE_05
```

证据：

```text
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/manifest.json
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/rules/
```

## 4. Replay Scope / Frozen Rule Contract

通过。

RCPT2 只回放 RCPT1 冻结的 5 条规则，没有新增规则或新增阈值。`manifest.json`、`replay_source_manifest.json`、`threshold_contract_compliance_audit.csv`、`anti_overfit_and_no_2022_replay_tuning_audit.csv` 与脚本 `RULES` 列表一致。

`anti_overfit_and_no_2022_replay_tuning_audit.csv` 对 5 条规则均记录：

```text
new_rule_or_threshold_added_in_rcpt2 = False
replay_result_used_for_tuning = False
strict_test_used = False
model_training_performed = False
status = PASS
```

脚本中 `RULES` 只包含 5 条 RCPT1 规则；未发现动态新增规则、按 replay 结果改阈值或训练逻辑被 RCPT2 main path 调用。PA1 脚本中虽存在训练/label 函数，但 RCPT2 脚本仅复用 `PriceStore`、baseline intents、mark-to-market、next-open accounting 等 replay accounting 组件。

证据：

```text
scripts/run_tw_policy_rcpt2_adaptive_threshold_replay_sanity.py
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/anti_overfit_and_no_2022_replay_tuning_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/replay_source_manifest.json
```

## 5. RCPT1_RULE_02 Threshold Contract

通过。

`RCPT1_RULE_02` 严格按冻结阈值回放：

```text
score_percentile_floor = 0.10
score_percentile_ceiling = 0.40
primary_band = top_20_40_percent
```

未因 RCPT1 审查中记录的 H03 traceability 噪音扩展到 `top_40_60_percent`。脚本 `pass_rule02_percentile()` 使用：

```text
0.10 <= score_percentile_by_date <= 0.40
```

逐日 `rules/RCPT1_RULE_02/rule_trigger_ledger.csv` 核对结果：

```text
row_count = 246
rule02_percentile_floor = 0.1
rule02_percentile_ceiling = 0.4
h09_used_as_trigger = False
```

`threshold_contract_compliance_audit.csv` 明确记录：

```text
h03_top_40_60_expansion_used = False
rule02_frozen_010_040_if_applicable = True
status = PASS
```

## 6. H09 Reference-only Check

通过。

H09 在 RCPT1 中是 `REFERENCE_ONLY`，RCPT2 未把 `raw_score >= 0.8` 写成 trigger 或反向 avoid rule。

证据：

```text
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/threshold_source_contract.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/threshold_contract_compliance_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/diagnostic_semantics_audit.json
```

逐规则 ledger 中 `h09_used_as_trigger` 未见 True；`RCPT1_RULE_05` 逐日 ledger 核对结果：

```text
h09_used_as_trigger = False
accelerated_sell_count max per day = 1
accelerated_sell_count sum = 105
```

## 7. RCPT1_RULE_05 Pass Validity

通过，`RCPT1_RULE_05` 的通过结论真实且与各审计表一致。

### 7.1 Summary / Baseline Comparison

`RCPT1_RULE_05` 相对 RCP1B baseline：

```text
baseline_net_return_after_fee_tax = -0.3360922
rule_net_return_after_fee_tax = -0.1860388
net_delta = 0.1500534

baseline_max_drawdown = -0.42634734
rule_max_drawdown = -0.2290736
max_drawdown_delta = 0.19727374

baseline_turnover_proxy = 48.45575343
rule_turnover_proxy = 47.89271616
turnover_delta = -0.56303727

baseline_fee_and_tax = 112926.17
rule_fee_and_tax = 121293.38
fee_and_tax_delta = 8367.21
```

费用上升，但工作文档允许 turnover / fee_and_tax 在 net 与 drawdown 均 materially improve 时通过；脚本 gate 也按该条件给出 `fee_tax_gate = PASS`。

### 7.2 Gate Decision

`adaptive_rule_gate_decision.csv` 对 `RCPT1_RULE_05` 记录：

```text
net_return_gate = PASS
max_drawdown_gate = PASS
turnover_gate = PASS
fee_tax_gate = PASS
cash_no_trade_gate = PASS
participation_gate = PASS
concentration_gate = PASS
threshold_contract_gate = PASS
diagnostic_semantics_gate = PASS
overall_gate = PASS
decision = PASS_CANDIDATE_FOR_RCPT3_CLOSURE_REVIEW
```

### 7.3 Cash / No-trade

通过。

```text
participation_rate = 0.99593496
average_cash_rate = 0.5705297
buy_count = 245
baseline_buy_count = 244
minimum_buy_count_relative_to_baseline = 61
action_count = 482
status = PASS
```

### 7.4 Turnover / Fee / Tax

通过。

```text
turnover_proxy = 47.89271616
baseline_turnover_proxy = 48.45575343
fee_and_tax = 121293.38
baseline_fee_and_tax = 112926.17
status = PASS
```

费用高于 baseline，但 net return 与 max drawdown 同时显著改善，因此符合本轮 fee/tax gate 的通过逻辑。

### 7.5 Concentration

通过。

```text
max_symbol_weight = 0.12189486
max_holding_count = 8
target_holding_count = 10
status = PASS
```

### 7.6 Threshold Contract Compliance

通过。

`RCPT1_RULE_05` 使用冻结条件：

```text
max_early_sell_per_day = 1
deterioration requires rank_change_5d > 0 or rank_change_3d > 0 with failed mid-band/trend support
```

脚本实现为 risk-off 时，持仓不再满足 mid-band/trend support 且 rank deterioration 成立时，至多插入一条 early sell；逐日 ledger 核对最大 `accelerated_sell_count` 为 1，未发现一天多次 early sell。

## 8. Failed Rules Reasonableness

失败原因合理。

### RCPT1_RULE_01

失败原因为 `FAIL_CASH_OR_NO_TRADE`。
该规则净收益和回撤均显著改善，turnover/fee/tax 也通过，但平均现金率为 `0.65216193`，超过工作文档 `average_cash_rate <= 0.60`，因此 cash/no-trade gate 失败合理。

### RCPT1_RULE_02

失败原因为 `FAIL_CASH_OR_NO_TRADE`。
该规则按冻结 0.10-0.40 percentile 回放，净收益和回撤改善、turnover/fee/tax 通过，但平均现金率为 `0.74958201`，超过 0.60，因此失败合理。

### RCPT1_RULE_03

失败原因为 `FAIL_CASH_OR_NO_TRADE`。
该规则净收益和回撤改善、turnover/fee/tax 通过，但平均现金率为 `0.63417325`，超过 0.60，因此失败合理。

### RCPT1_RULE_04

失败原因为 `FAIL_NO_RISK_REWARD_TRADEOFF`。
该规则独立 diagnostic guardrail replay 与 baseline 结果相同：

```text
net_delta = 0.0
max_drawdown_delta = 0.0
turnover_delta = 0.0
fee_and_tax_delta = 0.0
```

未形成风险收益改善，因此失败合理。

## 9. Future Leakage / Implementation Boundary

未发现阻塞性实现 bug 或 future leakage。

核对点：

```text
score_percentile_by_date = same-day candidate_rank / same-day cross-section count
rank_change_3d / rank_change_5d = per-instrument historical diff after date sort
score_delta_3d / score_delta_5d = per-instrument historical diff after date sort
execution_price_policy = first available open after signal_date
mark_to_market = close_on_or_before
missing next open = skipped/audited, no fallback
```

`execution_audit.csv` 记录 execution date 是 signal date 后第一可用 open，符合 replay accounting 的 PIT 执行对齐。未发现 future return label、future excess return、forward return、label utility 等进入 RCPT2 rule trigger。

## 10. Forbidden Actions / Production Boundary

通过。

`forbidden_action_audit.csv` 对以下事项均记录 `False` / `PASS_NOT_PRESENT_OR_NOT_PERFORMED`：

```text
strict_test
model_training
new_rule
new_threshold
threshold_tuning
use_2022_replay_result_for_rule_selection_or_threshold_tuning
registry_default_provider_change
frontend_agent_monitor_order_chain_change
broker_order_quick_trade
OrderIntent_output
target_weight
target_position
quantity_instruction
h09_trigger
rcpt1_rule_02_h03_top_40_60_expansion
```

未发现 provider publish、accepted latest switch、frontend/Agent/monitor 集成、broker、quick-trade、real order、OrderIntentArtifact、target_weight、target_position 或 quantity instruction 输出。

## 11. Validator Consistency

`validator_report.json` 与审查结论一致：

```text
status = PASS
pass = true
required_files_status = PASS
t1_contract_status = PASS
replayed_rule_count = 5
not_replayed_rule_count = 0
any_rule_pass = true
best_rule_id = RCPT1_RULE_05
threshold_contract_status = PASS
cash_no_trade_status = PASS
concentration_status = PASS
diagnostic_semantics_status = PASS
anti_overfit_status = PASS
forbidden_actions_status = PASS
repair_required = false
recommended_next_step = PASS_READY_FOR_RCPT3_CLOSURE_REVIEW_WORK_DOC
```

## 12. Final Authorization Boundary

本审查允许 RCPT2 进入：

```text
RCPT3 closure review work doc
```

RCPT3 应只审查 closure readiness，不应把 `RCPT1_RULE_05` 解释为 production calibrated rule、strict OOS result、订单建议、仓位建议或默认生产策略。
