---
created_at: 2026-06-24
status: rcpt5a_option_a_independent_review_completed
phase: RCPT5A_OPTION_A_2021_PIT_FEATURE_REPAIR_DIAGNOSTIC_REVIEW
execution_report: docs/tw_portfolio_decision_model/POLICY_RCPT5A_OPTION_A_2021_PIT_FEATURE_REPAIR_DIAGNOSTIC_EXECUTION_REPORT_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RCPT5A_OPTION_A_2021_PIT_FEATURE_REPAIR_DIAGNOSTIC_WORK_CN.md
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT5_STRICT_OOS_DESIGN_DECISION_REVIEW_CN.md
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic
verdict: PASS_READY_FOR_OPTION_B_QLIB_ONLY_STRICT_OOS_WORK_DOC
diagnostic_only: true
strict_oos: false
strict_test_executed: false
model_training_performed: false
production_allowed: false
---

# RCPT5A Option A 2021 PIT Feature Repair Diagnostic 独立审查报告

## 1. Verdict

`PASS_READY_FOR_OPTION_B_QLIB_ONLY_STRICT_OOS_WORK_DOC`

RCPT5A Option A 产物可支持进入 Option B qlib-only strict OOS 工作文档撰写阶段。该结论只表示 `RCPT1_RULE_05` 在 2021 `pre-2022 sanity diagnostic` 中没有提前暴露明显机制失败；它不是 strict OOS、final OOS 或 independent test 通过结论。

## 2. Evidence Reviewed

本审查读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT5A_OPTION_A_2021_PIT_FEATURE_REPAIR_DIAGNOSTIC_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT5A_OPTION_A_2021_PIT_FEATURE_REPAIR_DIAGNOSTIC_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT5_STRICT_OOS_DESIGN_DECISION_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/manifest.json
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/market_feature_2021_by_signal_date.csv
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/market_feature_coverage_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/rule05_2021_replay_summary.csv
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/rule05_2021_baseline_comparison.csv
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/rule05_2021_gate_decision.csv
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/rule05_2021_monthly_comparison.csv
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/rule05_2021_cash_exposure_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/rule05_2021_fee_tax_reconciliation.csv
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/rule05_2021_concentration_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/rule05_2021_trigger_attribution.csv
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/diagnostic_semantics_audit.json
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/forbidden_action_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/diagnostic_findings.md
```

另抽查：

```text
scripts/run_tw_policy_rcpt5a_option_a_2021_pit_feature_repair_diagnostic.py
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/rule05_frozen_contract.md
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_by_signal_date.csv
docs/tw_portfolio_decision_model/POLICY_RCP3A_MARKET_FEATURE_COVERAGE_PIT_GATE_EXECUTION_REPORT_CN.md
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
data_tw/experiments/risk_control_policy_2022/rcpt4_rule05_mechanism_attribution/2021_not_available_audit.json
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/internal_replay_ledgers_not_order_intent/
```

## 3. PIT Feature Review

通过。

`market_feature_2021_by_signal_date.csv` 覆盖 2021-01-04 至 2021-12-30 共 243 个 signal date。`feature_available` 全部为 true，`pit_safe` 全部为 true，`ma60_observation_count` 最小值和最大值均为 60。`market_feature_coverage_audit.csv` 报告 missing signal、missing price、missing MA60 均为 0。

脚本抽查显示 2021 market feature 只从本地 `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv` 派生，`market_index_ma60` 为 TWII close 当前行加前 59 个可用市场行的 rolling mean。未发现外部下载、2021 之后未来值补入或 silent forward-fill。

RCP3A 2022 market feature 产物使用同一 TWII source 和同一 MA60 合同；RCPT4 的 `2021_not_available_audit.json` 原因是 RCP3A 只覆盖 2022，RCPT5A 对 2021 的补齐与工作文档授权一致。

## 4. Diagnostic Semantics

通过。

执行报告、manifest、summary、diagnostic semantics audit 和 findings 均把本轮标为：

```text
window = 2021_pre_2022_sanity_diagnostic
semantic_label = pre_2022_sanity_diagnostic
diagnostic_only = true
strict_oos = false
```

未发现将 2021 写成 strict OOS、final OOS 或 independent test 的结论。RCP1A 信号本身仍带有 `diagnostic_only=true`，因此本轮结果只能用于 pre-2022 sanity 过滤，不得作为最终验证证据。

## 5. RULE_05 Freeze

通过。

`diagnostic_semantics_audit.json` 和脚本实现均保持冻结条件：

```text
risk_off
len(holdings) > 1
rank_change_5d > 0 OR rank_change_3d > 0
not pass_rule03_combined_support
max_early_sell_per_day = 1
```

独立复算 `rule05_2021_trigger_attribution.csv`：243 行中触发 36 行，触发布尔值与上述四条件组合 mismatch 为 0；非触发日 accelerated sell 合计为 0；单日最大 accelerated sell 为 1。未发现新增 buy-side gate、cash target、score/rank/MA/trend/cash/fee 阈值，亦未发现根据 2021 结果调参后重跑的证据。

## 6. Scope And Safety Boundary

通过。

`forbidden_action_audit.csv` 对以下项目均为 `PASS_NOT_PRESENT_OR_NOT_PERFORMED`：

```text
external_data_download
model_training
strict_test
new_rule
threshold_tuning
2021_result_driven_retuning_or_rerun
production_default_provider_change
frontend_agent_monitor_order_chain_change
broker_order_quick_trade
OrderIntent_output
target_weight
target_position
quantity_instruction
future_return_label_used
claim_2021_strict_oos_or_final_oos
```

内部子目录命名为 `internal_replay_ledgers_not_order_intent`，manifest 声明 `internal_replay_ledgers_only_not_order_intent=true`。内部账本含 execution price、quantity、cash、fee、tax 等回放记账字段，但未作为 root required artifacts 的 OrderIntent、target weight、target position 或真实订单输出。脚本未修改 production/default/provider/frontend/Agent/monitor/order 链路。

## 7. Result And Gate Interpretation

通过，但必须按风险控制 tradeoff 解释。

核心结果：

```text
RULE_05 net_return_after_fee_tax = 0.47696307
baseline net_return_after_fee_tax = 0.54760487
delta = -0.07064180

RULE_05 max_drawdown = -0.20594562
baseline max_drawdown = -0.31695465
drawdown improvement = 0.11100903

RULE_05 average_cash_rate = 0.49247449
baseline average_cash_rate = 0.21546045
RULE_05 cash_gt_90_day_share = 0.13991770
RULE_05 average_holding_count = 6.01646091
RULE_05 action_count = 476
RULE_05 accelerated_sell_count = 36
```

2021 收益低于 baseline，但最大回撤明显改善，且仍有 242 buy、234 sell、243 日 participation rate 为 0.99588477，不是 all-cash/no-trade 伪通过。该结果符合风险控制规则的可接受 tradeoff：降低暴露和收益，换取回撤缓解；不足以证明 alpha 改善，也不构成机制失败。

月度层面，5 月收益相对 baseline 显著较差，8 月和 9 月回撤改善较明显；9 月和 10 月现金暴露很高。该模式说明 RULE_05 是防守型风险控制，不应在 Option B 中被解释为收益增强器。

## 8. Accounting / Concentration / Leakage Checks

通过，存在低风险口径备注。

独立统计内部账本：

```text
execution_date <= signal_date count = 0
negative cash days = 0
duplicate date/instrument positions = 0
missing price sum = 0
max holding count = 9
all-cash days = 1
final nav equity = 1476963.07
summary final equity = 1476963.07
```

费用税费口径可复核：RULE_05 fee_and_tax 为 174950.60，baseline 为 186563.19；commission 和 tax 均分项报告，未出现费用为 0 或税费漏算迹象。集中度审计显示最大 instrument accelerated sell count share 为 0.08333333，最大 month count share 为 0.30555556，未形成单一股票或单一月份伪改善。

低风险备注：summary 中 `max_cash_rate=1.15007883` 以 initial cash 为分母，而不是现金/权益比；独立复算 nav cash/equity 最大为 1.0，且 negative cash 为 0。这不是 accounting 阻断项，但 Option B 工作文档应将 cash rate 的分母和命名冻结清楚，避免把增长后的现金余额误读为杠杆、融资或现金率超过 100%。

## 9. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. `max_cash_rate` 当前使用 `cash / initial_cash`，会在组合盈利后超过 1.0。建议 Option B gate 在执行前冻结现金暴露口径，至少同时报告 `cash / equity`，避免审查误读。

2. RCPT5A 的 sanity gate 对 cash exposure 使用宽松 stop band，仅适合 pre-2022 diagnostic。Option B strict OOS 工作文档必须重新预冻结 strict OOS gate，不得沿用本轮宽阈值作为 strict gate。

3. 2021 低收益、高现金、低回撤的形态说明 RULE_05 是防守 tradeoff。Option B 若继续，应明确“不以收益超过 baseline 作为本轮已证明事实”，只检验 qlib-only strict OOS 下是否仍能避免灾难性退化和伪改善。

## 10. Final Decision

RCPT5A Option A 审查结论为：

```text
PASS_READY_FOR_OPTION_B_QLIB_ONLY_STRICT_OOS_WORK_DOC
```

建议继续，但只继续到 Option B qlib-only strict OOS 工作文档撰写和 reviewer gate 冻结。不得直接进入 production/default/provider/frontend/Agent/monitor/order 链路，不得训练、调阈值、引入 LTR、输出 OrderIntent 或 target_weight/target_position。
