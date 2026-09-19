---
created_at: 2026-06-23
status: work_order_for_ral_ed2_a_baseline_replay_accounting_audit
phase: RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
coordinator_opinion: docs/tw_portfolio_decision_model/POLICY_RAL_ED2_COORDINATOR_BASELINE_AUDIT_OPINION_CN.md
prior_review: docs/tw_portfolio_decision_model/POLICY_RAL_ED2_PREDECLARED_BLOCK_BUY_RULE_SANITY_REVIEW_CN.md
prior_execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_ED2_PREDECLARED_BLOCK_BUY_RULE_SANITY_EXECUTION_REPORT_CN.md
source_ed2_root: data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity
baseline_replay_script: scripts/run_tw_policy_action_model_pa1.py
output_root: data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit
ral_ed3_authorized: false
strict_test_authorized: false
rule_grid_search_authorized: false
threshold_selection_authorized: false
new_rule_version_authorized: false
model_training_authorized: false
provider_publish_authorized: false
accepted_latest_switch_authorized: false
monitor_write_authorized: false
frontend_default_switch_authorized: false
agent_authorized: false
broker_authorized: false
order_intent_authorized: false
target_weight_authorized: false
target_position_authorized: false
quantity_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_investment_advice: true
---

# RAL-ED2-A Baseline Replay Accounting Audit 工作文档

## 1. 本轮定位

本轮执行统筹授权的：

```text
RAL-ED2-A: Baseline Replay Accounting Audit
```

本轮目标不是修规则、不是继续 ED3，而是独立审计 ED2 使用的 baseline/replay 会计口径是否可信，尤其是 2025 validation baseline `net_return_after_fee_tax = 0.95376753` 是否可以被复现并解释。

本轮只回答：

```text
1. ED2 reported baseline 是否能被重新计算复现；
2. NAV、费用、换手、pending order、价格/信号对齐是否一致且 PIT-safe；
3. 期末未平仓 liquidation sensitivity 是否会改变 ED2 相对结论；
4. baseline clone 是否确实等于 baseline；
5. 如果审计通过，ED2 失败是否可以解释为 block-buy-only 规则真实失败。
```

本轮不是：

```text
ED3
strict_test
规则调阈值
扩展规则 grid
新增规则版本
模型训练
生产或订单集成
```

## 2. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_COORDINATOR_BASELINE_AUDIT_OPINION_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_PREDECLARED_BLOCK_BUY_RULE_SANITY_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_PREDECLARED_BLOCK_BUY_RULE_SANITY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_PREDECLARED_BLOCK_BUY_RULE_SANITY_REVIEW_CN.md
```

必须读取 ED2 artifacts：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity/manifest.json
data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity/source_artifact_manifest.json
data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity/readonly_rule_replay_result.csv
data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity/baseline_vs_rule_replay_comparison.csv
data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity/rolling_oos_result.csv
data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity/baseline_clone_no_trade_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity/forbidden_consumer_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity/validator_report.json
```

必须读取 baseline/replay 相关代码与产物：

```text
scripts/run_tw_policy_action_model_pa1.py
scripts/run_tw_policy_ral_ed2_predeclared_block_buy_rule_sanity.py
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/repaired_baseline_action_symbol_daily_ledger.csv
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
```

必须参考项目边界合同：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

## 3. 输入与输出

输入：

```text
source_ed2_root =
data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity

baseline_replay_script =
scripts/run_tw_policy_action_model_pa1.py
```

输出目录：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_EXECUTION_REPORT_CN.md
```

## 4. 允许范围

允许：

```text
1. 只读重算 2025 validation baseline replay accounting；
2. 读取 ED2 reported baseline 和 rule comparison artifacts；
3. 读取 baseline replay ledger、signal artifact、价格数据和 replay 代码；
4. 重建 baseline NAV、actions、daily return、fee/tax、turnover、position lifecycle；
5. 审计 pending order、signal/execution/price alignment；
6. 做期末 liquidation sensitivity；
7. 做 market benchmark comparison；
8. 做 baseline clone consistency 与 rule replay fairness audit；
9. 输出 validator_report.json 和 diagnostic_findings.md。
```

允许内部生成只读 diagnostic rows，例如：

```text
shares_diagnostic
notional_diagnostic
cash_diagnostic
market_value_diagnostic
fee_tax_diagnostic
turnover_diagnostic
```

这些字段不得作为 OrderIntent、target 或 broker 输出。

## 5. 禁止事项

本轮禁止：

```text
1. ED3；
2. strict_test；
3. 规则调阈值；
4. 扩展规则 grid；
5. 新增规则版本；
6. 重跑或优化 ED2 规则；
7. 模型训练 / qlib+LTR / bandit / RL；
8. provider publish / accepted latest switch；
9. monitor write / frontend default / Agent integration；
10. broker / quick-trade / real order；
11. 输出 OrderIntent；
12. 输出 target_weight / target_position / quantity / broker_order；
13. 用低换手、低成本、低回撤替代收益判断；
14. 把本轮审计写成投资建议。
```

## 6. 必须输出

输出目录必须包含：

```text
manifest.json
baseline_replay_source_manifest.json
baseline_summary_recomputed.json
baseline_nav_recomputed.csv
baseline_actions_recomputed.csv
baseline_daily_return_audit.csv
baseline_fee_tax_turnover_audit.csv
baseline_position_lifecycle_audit.csv
baseline_pending_order_window_audit.csv
baseline_price_alignment_audit.csv
baseline_signal_window_alignment_audit.csv
baseline_end_liquidation_sensitivity.csv
baseline_market_benchmark_comparison.csv
baseline_vs_ed2_reported_metric_diff.csv
baseline_clone_consistency_audit.csv
rule_replay_fairness_audit.csv
missing_price_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

## 7. 审计任务

### 7.1 Source manifest

输出：

```text
baseline_replay_source_manifest.json
```

至少包含：

```text
baseline_replay_script
source_signal_artifact
source_baseline_ledger
source_ed2_root
price_source_paths
validation_window
strict_test_window_declared_only
strict_test_used
initial_cash
fee_rate
tax_rate
max_holding_count
execution_policy
mark_to_market_policy
```

### 7.2 Baseline metric recompute

输出：

```text
baseline_summary_recomputed.json
baseline_vs_ed2_reported_metric_diff.csv
```

必须重新计算并核对：

```text
initial_cash
final_equity
net_return_after_fee_tax
gross_return
fee_and_tax
turnover_proxy
action_count
buy_count
sell_count
skip_count
max_drawdown
max_holding_count
negative_cash_count
missing_price_count
```

`baseline_vs_ed2_reported_metric_diff.csv` 必须包含：

```text
metric
ed2_reported_value
ed2_a_recomputed_value
absolute_diff
relative_diff
pass_fail
tolerance
```

核心字段容忍误差应接近 0：

```text
net_return_after_fee_tax
final_equity
fee_and_tax
turnover_proxy
action_count
buy_count
sell_count
```

若不能接近 0，必须 STOP。

### 7.3 NAV accounting audit

输出：

```text
baseline_nav_recomputed.csv
baseline_daily_return_audit.csv
```

必须逐日验证：

```text
equity = cash + market_value
daily_return = equity / previous_equity - 1
cash >= 0
holding_count <= 10
missing_price_count = 0 或有明确说明
```

必须输出异常日期：

```text
negative_cash
holding_count_exceeded
equity_mismatch
missing_price
daily_return_mismatch
```

### 7.4 Action accounting audit

输出：

```text
baseline_actions_recomputed.csv
baseline_fee_tax_turnover_audit.csv
baseline_position_lifecycle_audit.csv
```

必须验证：

```text
buy_fee = buy_notional * 0.001425
sell_fee_tax = sell_notional * (0.001425 + 0.003)
action_count = buy_count + sell_count
turnover_proxy = action_notional / average_equity
同一 symbol 不重复持仓
卖出前必须有持仓
买入后 holding_count <= 10
每个 signal date baseline intent 不超过 1 buy + 1 sell
```

### 7.5 Pending order window audit

输出：

```text
baseline_pending_order_window_audit.csv
```

必须审计：

```text
1. 是否存在 execution_date <= validation_end 但未计入 final NAV 的 pending order；
2. 是否存在 execution_date > validation_end 但被错误执行；
3. 最后一个 signal date 之后的 pending order 如何处理；
4. final_equity 是否在所有窗口内可执行 pending orders 处理后重新 mark-to-market。
```

若发现 final NAV 与 actions 处理顺序不一致，必须 STOP。

### 7.6 Price / signal alignment audit

输出：

```text
baseline_price_alignment_audit.csv
baseline_signal_window_alignment_audit.csv
missing_price_audit.csv
```

必须验证：

```text
signal_date <= execution_date
execution_date 使用 signal_date 之后的 open
mark-to-market 使用 asof 当日或之前 close
不使用 execution_date 之后价格做当日决策
validation window = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07 declared only, not used
```

必须输出：

```text
missing price count by symbol/date
adjusted price source path
signal artifact path
signal date coverage
price date coverage
```

### 7.7 End liquidation sensitivity

输出：

```text
baseline_end_liquidation_sensitivity.csv
```

必须计算：

```text
baseline_net_return_nav
baseline_net_return_if_liquidated_at_period_end
liquidation_fee_tax_drag
```

并对 ED2 rule versions 做同口径比较：

```text
rule_id
threshold_version
rule_net_return_nav
rule_net_return_if_liquidated_at_period_end
baseline_excess_nav
baseline_excess_if_liquidated
relative_conclusion_changed
```

若期末清算 sensitivity 改变 ED2 相对结论，必须 STOP。

### 7.8 Market benchmark comparison

输出：

```text
baseline_market_benchmark_comparison.csv
```

必须包含：

```text
TWII_2025_return
baseline_2025_return
baseline_excess_vs_TWII
baseline_average_cash_rate
baseline_max_holding_count
baseline_concentration_summary
benchmark_data_source
benchmark_missing_data_count
```

如无法取得 TWII benchmark，必须说明数据缺口并输出 fallback benchmark audit，不得凭空估计。

### 7.9 Baseline clone and fairness audit

输出：

```text
baseline_clone_consistency_audit.csv
rule_replay_fairness_audit.csv
```

必须检查：

```text
baseline clone rule_net_return_after_fee_tax == baseline_net_return_after_fee_tax
baseline clone action_count == baseline action_count
baseline clone fee_tax == baseline fee_tax
baseline clone turnover == baseline turnover
rule 与 baseline 使用同一 initial_cash
rule 与 baseline 使用同一 validation window
rule 与 baseline 使用同一 price source
rule 与 baseline 使用同一 fee/tax rate
rule 与 baseline 使用同一 execution policy
```

## 8. Validator 要求

`validator_report.json` 至少检查：

```text
all required files exist
ed2 source artifacts readable
baseline recompute completed
baseline_vs_ed2_reported_metric_diff core metrics pass
nav_accounting_pass
fee_tax_turnover_pass
position_lifecycle_pass
pending_order_window_pass
price_signal_alignment_pass
liquidation_sensitivity_conclusion_unchanged
baseline_clone_consistency_pass
rule_replay_fairness_pass
missing_price_not_material
strict_test_used=false
rule_grid_search_run=false
threshold_selection_run=false
new_rule_version_run=false
model_training_run=false
no OrderIntent / target_weight / target_position / quantity / broker_order
provider/latest/monitor/frontend/Agent/production not performed
```

## 9. 通过条件

ED2-A 通过只代表：

```text
ED2 baseline/replay 口径可信，可以把 ED2 失败视为 block-buy-only 规则失败。
```

通过条件：

```text
1. ED2-A recomputed baseline 与 ED2 reported baseline 一致；
2. NAV accounting 无重大错误；
3. fee/tax/turnover 计算正确；
4. pending order 没有跨窗口漏计或重复；
5. price/signal alignment PIT-safe；
6. 期末清算 sensitivity 不改变 ED2 的相对结论；
7. baseline clone 规则与 baseline 完全一致；
8. rule 与 baseline 使用同一初始资金、窗口、价格源、费用口径；
9. 不使用 strict_test；
10. 不做规则调参、grid search 或新策略实验；
11. validator_report.json ok=true。
```

若通过，执行报告只能建议：

```text
READY_FOR_REVIEWER_TO_CLOSE_BLOCK_BUY_ROUTE_AS_NEGATIVE_EVIDENCE
```

不得建议 ED3。

## 10. STOP / Repair 条件

若发现以下任一问题，应 STOP 并建议 repair：

```text
1. baseline 重新计算无法复现 0.95376753；
2. final_equity 与 NAV/action accounting 不一致；
3. fee/tax 漏算或重复；
4. pending order 跨窗口处理错误；
5. signal/execution/price 存在未来数据；
6. baseline 与 rule 使用不同初始资金、日期窗口、价格源或费用口径；
7. 期末清算 sensitivity 使 ED2 相对结论发生实质变化；
8. baseline clone 不等于 baseline；
9. missing price 对收益有不可忽略影响；
10. validator_report.json failed_count > 0；
11. 执行者使用 strict_test、调阈值、扩展 grid、新增规则、训练模型或触碰生产/订单链路。
```

失败推荐只能是：

```text
STOP_BASELINE_RECOMPUTE_MISMATCH
STOP_NAV_ACCOUNTING_INCONSISTENT
STOP_FEE_TAX_ACCOUNTING_ERROR
STOP_PENDING_ORDER_WINDOW_ERROR
STOP_PRICE_SIGNAL_ALIGNMENT_LEAKAGE
STOP_RULE_BASELINE_FAIRNESS_MISMATCH
STOP_LIQUIDATION_SENSITIVITY_CHANGES_CONCLUSION
STOP_BASELINE_CLONE_MISMATCH
STOP_MISSING_PRICE_MATERIAL
STOP_FORBIDDEN_ACTION_REQUESTED
STOP_VALIDATOR_FAILED
```

若 ED2-A 失败，不能关闭 block-buy route，也不能相信 ED2 的“没有规则超过 baseline”结论；必须先修 baseline/replay 口径，再重跑 ED2。

## 11. 给执行者的命令

```text
你是执行者。请执行 RAL-ED Explicit Rule Discovery 主线下的 RAL-ED2-A Baseline Replay Accounting Audit。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_RAL_ED2_COORDINATOR_BASELINE_AUDIT_OPINION_CN.md
3. docs/tw_portfolio_decision_model/POLICY_RAL_ED2_PREDECLARED_BLOCK_BUY_RULE_SANITY_REVIEW_CN.md
4. docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_WORK_CN.md
5. data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity/*
6. scripts/run_tw_policy_action_model_pa1.py
7. scripts/run_tw_policy_ral_ed2_predeclared_block_buy_rule_sanity.py

本轮只做 baseline/replay accounting audit：
- 重新计算 2025 validation baseline；
- 审计 NAV、daily return、fee/tax、turnover、position lifecycle；
- 审计 pending order、price/signal alignment、missing price；
- 做期末 liquidation sensitivity；
- 做 market benchmark comparison；
- 做 baseline clone consistency 与 rule replay fairness audit；
- 生成 validator_report.json、diagnostic_findings.md；
- 写执行报告。

本轮禁止：
- ED3；
- strict_test；
- 调阈值；
- 扩展规则 grid；
- 新增规则版本；
- 重跑或优化 ED2 规则；
- 训练模型；
- OrderIntent / target_weight / target_position / quantity / broker order；
- provider/latest/monitor/frontend/Agent/broker/production 扩权。

输出目录：
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/

执行报告：
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_EXECUTION_REPORT_CN.md
```

## 12. 给后续审查者的审查口径

审查者必须检查：

```text
1. 是否只做 baseline/replay accounting audit；
2. 是否复现 ED2 reported baseline；
3. NAV / fee-tax / turnover / pending order / price-signal alignment 是否可信；
4. liquidation sensitivity 是否改变 ED2 相对结论；
5. baseline clone 是否等于 baseline；
6. rule replay fairness 是否通过；
7. 是否没有 strict_test、调阈值、扩展 grid、新规则、训练、订单或生产链路；
8. 如果通过，是否只关闭 block-buy route 为 negative evidence，不进入 ED3。
```
