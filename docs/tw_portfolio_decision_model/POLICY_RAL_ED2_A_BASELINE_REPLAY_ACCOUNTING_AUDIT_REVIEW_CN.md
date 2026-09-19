---
created_at: 2026-06-23
status: pass_with_minor_condition_close_block_buy_route_as_negative_evidence
phase_reviewed: RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
coordinator_opinion: docs/tw_portfolio_decision_model/POLICY_RAL_ED2_COORDINATOR_BASELINE_AUDIT_OPINION_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit
reviewer_role: independent_reviewer
ral_ed3_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# RAL-ED2-A Baseline Replay Accounting Audit 审查意见

## 1. Verdict

审查结论：

```text
PASS_WITH_MINOR_CONDITION_CLOSE_BLOCK_BUY_ROUTE_AS_NEGATIVE_EVIDENCE
```

ED2-A 已完成统筹授权的 baseline/replay accounting audit。核心结论成立：

```text
ED2 reported baseline net_return_after_fee_tax = 0.95376753
ED2-A recomputed baseline net_return_after_fee_tax = 0.95376753
absolute_diff = 0
validator_ok = true
failed_count = 0
```

因此，当前可将 ED2 的失败解释为：

```text
predeclared block-buy-only 规则没有超过可信 baseline；
当前 block-buy-only route 应关闭并作为 negative evidence 归档。
```

本审查不授权 ED3，不授权 strict_test，不授权继续调阈值、扩展 grid、新规则版本、模型训练、订单、provider/latest、monitor、frontend、Agent 或 production。

## 2. Findings

### Critical

无。

### High

无。

### Medium

1. ED2-A 对 baseline 绝对口径的核心复算通过。`baseline_vs_ed2_reported_metric_diff.csv` 中核心字段全部为 `pass`：

```text
baseline_net_return_after_fee_tax diff = 0
baseline_action_count diff = 0
baseline_turnover diff = 0
baseline_fee_tax diff = 0
```

2. NAV、费用税、持仓生命周期、pending order window、价格/信号对齐均通过 validator。未发现会改变 ED2 相对结论的会计错误。

3. 期末 liquidation sensitivity 不改变结论。baseline NAV return 为 `0.95376753`，若期末清算后为 `0.94512277`，清算成本拖累约 `8644.76`，不足以使 ED2 block-buy rule versions 超过 baseline。

### Low

1. `baseline_clone_consistency_audit.csv` 直接输出了 clone 规则的收益相等与 action_count 相等，但没有在该文件中再次显式列出 `fee_tax` 与 `turnover` 相等字段。上游 ED2 的 `baseline_clone_no_trade_audit.csv` 已包含并显示 clone rows 的 `baseline_turnover == rule_turnover`、`baseline_fee_tax == rule_fee_tax`，因此不构成阻断；但若后续做归档级 closure bundle，建议补一行说明或补充列，避免审计链路读者误解为未检查。

2. `baseline_market_benchmark_comparison.csv` 的 `baseline_concentration_summary` 为 `not_material_single_position_not_computed`。本轮主目标是 replay accounting，不是风险归因；该缺口不影响关闭 block-buy route，但不能把 ED2-A 解释为完整的风险/集中度审计。

## 3. Mainline Compliance

| Requirement | Review |
|---|---|
| 只做 ED2-A baseline/replay accounting audit | pass |
| ED2 reported baseline 可复现 | pass |
| NAV accounting pass | pass |
| fee/tax/turnover pass | pass |
| position lifecycle pass | pass |
| pending order window pass | pass |
| price/signal alignment PIT-safe | pass |
| strict_test 未使用 | pass |
| rule grid search 未执行 | pass |
| threshold selection 未执行 | pass |
| new rule version 未执行 | pass |
| model training 未执行 | pass |
| OrderIntent / target / quantity / broker 未输出 | pass |
| provider/latest/monitor/frontend/Agent/production 未触碰 | pass |
| 是否授权 ED3 | fail by design, 不授权 |

## 4. Evidence Checked

审查了执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_EXECUTION_REPORT_CN.md
```

审查了 artifact root：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/
```

关键证据：

```text
validator_report.json:
  ok = true
  status = PASS_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_READY_FOR_REVIEW
  final_recommendation = READY_FOR_REVIEWER_TO_CLOSE_BLOCK_BUY_ROUTE_AS_NEGATIVE_EVIDENCE
  failed_count = 0
  strict_test_used = false
  rule_grid_search_run = false
  threshold_selection_run = false
  new_rule_version_run = false
  model_training_run = false
  production_allowed = false
```

`baseline_summary_recomputed.json` 显示：

```text
start_date = 2025-01-02
end_date = 2025-12-31
initial_cash = 1000000.0
final_equity = 1953767.53
net_return_after_fee_tax = 0.95376753
gross_return = 1.09998226
max_drawdown = -0.34681374
action_count = 436
buy_count = 223
sell_count = 213
skip_count = 12
turnover_proxy = 42.18778217
fee_and_tax = 146214.73
max_holding_count = 10
duplicate_position_count = 0
negative_cash_count = 0
missing_price_count = 0
```

`baseline_replay_source_manifest.json` 显示：

```text
source_signal_artifact = data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
source_baseline_ledger = data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/repaired_baseline_action_symbol_daily_ledger.csv
source_ed2_root = data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity
price_source_paths = qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
validation_window = 2025-01-01..2025-12-31
strict_test_used = false
execution_policy = next_open_after_signal_date
mark_to_market_policy = close_on_or_before_asof
```

脚本语法检查：

```text
python -m py_compile scripts/run_tw_policy_ral_ed2_a_baseline_replay_accounting_audit.py
```

结果：通过。

## 5. Missing Evidence Or Open Questions

无阻断性缺口。

保留一个非阻断条件：

```text
baseline_clone_consistency_audit.csv 如作为长期归档入口，建议补充 fee_tax_equal_to_baseline 与 turnover_equal_to_baseline 两列，或在 diagnostic_findings.md 中引用 ED2 baseline_clone_no_trade_audit.csv 的对应字段。
```

该条件不改变本轮 verdict，因为核心 baseline accounting 已复现，且上游 ED2 clone audit 已包含 fee/tax 与 turnover 字段。

## 6. Forbidden Actions Audit

`forbidden_consumer_audit.csv` 显示：

```text
ed3 = not_authorized
strict_test = not_used
threshold_selection = not_performed
rule_grid_search = not_performed
new_rule_version = not_performed
model_training = not_performed
OrderIntent_output = not_output
target_weight = not_output
target_position = not_output
quantity = not_output
broker_order = not_output
provider_publish = not_performed
accepted_latest_switch = not_performed
monitor_write = not_performed
frontend_default_switch = not_performed
Agent_recommendation = not_performed
production_default_strategy = not_performed
```

审查未发现越权。

## 7. Next Work Control

本审查不写 ED3 工作文档，也不写新的执行者规则实验工作文档。

当前下一步控制：

```text
RAL-ED2-A baseline/replay accounting audit: accepted
RAL-ED2 block-buy-only route: close as negative evidence
RAL-ED3 final-only strict_test: not authorized
strict_test: not authorized
threshold tuning / grid expansion / new rule version: not authorized
model training: not authorized
production/order/provider/frontend/Agent: not authorized
```

如统筹希望继续探索，必须另行写主线级统筹意见或新方向工作文档；不能从 ED2-A 审查自动派生 ED3、strict_test 或新的 block-buy 调参任务。

## 8. Command For Coordinator

建议统筹接手：

```text
请关闭当前 RAL-ED2 block-buy-only route，并将 ED2 + ED2-A 产物归档为 negative evidence。

若继续 RAL-ED，只能由统筹另行决定是否新开非 block-buy 动作空间、full replay state contract、delay_sell/sell timing/cash replacement 等方向；这些方向不得由本 ED2-A 审查直接授权。
```
