---
created_at: 2026-06-24
status: rcpt5b_option_b_independent_review_completed
phase: RCPT5B_OPTION_B_QLIB_ONLY_STRICT_OOS
execution_report: docs/tw_portfolio_decision_model/POLICY_RCPT5B_OPTION_B_QLIB_ONLY_STRICT_OOS_EXECUTION_REPORT_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RCPT5B_OPTION_B_QLIB_ONLY_STRICT_OOS_WORK_CN.md
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT5A_OPTION_A_2021_PIT_FEATURE_REPAIR_DIAGNOSTIC_REVIEW_CN.md
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt5b_option_b_qlib_only_strict_oos
verdict: FAIL_RULE05_DOES_NOT_PASS_QLIB_ONLY_STRICT_OOS
qlib_only: true
strict_oos_candidate: true
model_training_performed: false
production_allowed: false
---

# RCPT5B Option B 2023-2025 Qlib-only Strict OOS 独立审查报告

## 1. Verdict

`FAIL_RULE05_DOES_NOT_PASS_QLIB_ONLY_STRICT_OOS`

本审查接受执行产物的 qlib-only strict OOS candidate 语义，但不接受 RULE_05 通过 strict OOS gate。唯一 gate 失败项为 `fee_tax_delta_abs`：RULE_05 总 fee/tax 低于 baseline，但按预冻结 gate 的绝对差口径，差值 `70444.52` 超过阈值 `50000.0`。因此必须按预冻结 gate 判 FAIL，不能事后将该项改为方向性有利项或放宽阈值。

## 2. Evidence Reviewed

本审查读取或抽查：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT5B_OPTION_B_QLIB_ONLY_STRICT_OOS_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT5B_OPTION_B_QLIB_ONLY_STRICT_OOS_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT5A_OPTION_A_2021_PIT_FEATURE_REPAIR_DIAGNOSTIC_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt5b_option_b_qlib_only_strict_oos/
scripts/run_tw_policy_rcpt5b_option_b_qlib_only_strict_oos.py
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.manifest.json
```

另按策略安全边界抽查：

```text
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

## 3. Qlib-only And Contamination Review

通过。

`TEST.csv` 表头只有如下信号相关列：

```text
date,instrument,qlib_score_raw,qlib_rank,fold_id,qlib_train_start,qlib_train_end,score_window_start,score_window_end,calendar_policy,universe_policy,is_test_frozen_pred,ltr_usage
```

独立抽查显示：

```text
rows = 89386
min_date = 2023-01-03
max_date = 2025-06-30
fold_id = TEST
is_test_frozen_pred = True
ltr_usage = test_score_baseline
qlib_score_raw missing = 0
qlib_rank missing = 0
```

`TEST.manifest.json` 支持 strict OOS candidate 语义：

```text
qlib_train_start = 2015-05-04
qlib_train_end = 2020-12-31
score_window_start = 2023-01-01
score_window_end = 2025-06-30
use_frozen_pred = true
training_performed = false
parameter_search_performed = false
```

脚本 `load_test_signals()` 明确只将 `qlib_score_raw` 映射到 `buy_score/raw_score`，只将 `qlib_rank` 映射到 `candidate_rank/score_rank/full_qlib_rank`，并拒绝包含 `ltr_score`、`stacking`、`orthogonal` 的列。未发现读取 LTR score、stacking score、训练、阈值搜索或用 2023-2025 结果反向调参的证据。

`contamination_audit.csv` 全部为 PASS。`signal_lineage_audit.json` 记录 `qlib_only=true`、`strict_oos_candidate=true`、`training_performed=false`、`parameter_search_performed=false`，与脚本和 TEST manifest 一致。

## 4. PIT Market Feature And Price Coverage

通过。

`market_feature_coverage_audit.csv` 对 2023-01-03 至 2025-06-30 的 597 个 signal day 报告：

```text
missing_signal_day_count = 0
missing_price_day_count = 0
missing_ma60_day_count = 0
pit_ma60_derivation_contract = PASS
```

PIT 合同写明 `market_index_ma60` 使用 TWII close 当前行及前 59 个可用市场行的 rolling mean，不使用未来 TWII 行。

`price_coverage_audit.csv` 独立统计：

```text
rows = 413
PASS rows = 413
missing_close_on_or_before_count sum = 0
missing_next_open_count sum = 0
price_store_present all true
```

未发现 market feature 或 price coverage 需要 stop 的 PIT 安全问题。

## 5. RULE_05 Freeze Review

通过。

冻结合同为：

```text
risk_off
len(holdings) > 1
rank_change_5d > 0 OR rank_change_3d > 0
not pass_rule03_combined_support
max_early_sell_per_day = 1
```

`rule05_freeze_audit.csv` 显示：

```text
max_early_sell_per_day = 1
trigger_condition_mismatch_count = 0
no_buy_side_gate_added = False
no_cash_target_added = False
no_threshold_tuning = False
```

执行脚本中的 `rule05_freeze_audit()` 与上述合同一致。未发现新增规则、调阈值、新增 cash target 或根据 2023-2025 重跑优化的证据。

## 6. Cash, Participation, Drawdown And Concentration

现金主口径正确。

`strict_oos_gate_freeze.json` 和产物均声明：

```text
primary_average_cash_rate = mean(cash / equity)
primary_max_cash_rate = max(cash / equity)
cash_gt_90pct_equity_day_share 使用 cash / equity
cash / initial_cash 仅为 auxiliary
```

核心结果：

```text
RULE_05 net_return_after_fee_tax = 0.31759959
baseline net_return_after_fee_tax = 0.41214390
net_return_delta = -0.09454431

RULE_05 max_drawdown = -0.35800856
baseline max_drawdown = -0.55905450
max_drawdown_delta = 0.20104594

participation_rate = 0.99832496
primary_average_cash_rate = 0.30471485
cash_gt_90pct_equity_day_share = 0.01340034
average_holding_count = 6.94304858
buy_count / sell_count = 576 / 569
accelerated_sell_count = 111
```

这些结果显示 RULE_05 在 2023-2025 qlib-only TEST fold 中仍是风险控制 tradeoff：收益低于 baseline，但 max drawdown 明显改善，且不是 all-cash/no-trade 伪通过。集中度 gate 也通过：

```text
top_instrument_benefit_share = 0.10009952
top_month_benefit_share = 0.16946431
top_trigger_day_benefit_share = 0.08113996
```

## 7. Gate Freeze And Failure Interpretation

strict OOS gate 已预冻结并严格执行。

`strict_oos_gate_freeze.json` 的 `created_at` 为 `2026-06-24T16:06:46+00:00`，执行报告和 manifest 的 `created_at` 为 `2026-06-24T16:07:52+00:00`，且 gate 文件状态为 `FROZEN_BEFORE_REPLAY`、`no_gate_tuning_after_replay=true`。gate 数值与工作文档一致。

`rule05_2023_2025_gate_decision.csv` 中除推荐 verdict 行外，16 个 gate PASS，唯一实质 FAIL 为：

```text
fee_tax_delta_abs: observed = 70444.52, threshold = <=50000.0
```

费用税费 reconciliation 显示：

```text
baseline total_fee_and_tax = 509542.23
RULE_05 total_fee_and_tax = 439097.55
delta = -70444.68
```

因此该失败不是因为 RULE_05 费用税费高于 baseline；相反，RULE_05 总 fee/tax 更低。失败来自预冻结 gate 使用 `abs(fee_tax_delta)`，把方向有利的费用下降也计入绝对偏离，并使用 `max(0.50 * abs(net_return_delta_cash_value), 0.05 * initial_cash)` 得到 50000 上限。

审查判断：

```text
1. 必须按预冻结 gate 判 FAIL。
2. `fee_tax_delta_abs` 的符号设计/严苛程度存在可讨论问题，因为它阻断的是费用税费下降而非成本恶化。
3. 但该问题不能在本轮事后修 gate、重判 PASS 或直接关闭 RULE_05。
4. 后续若 coordinator 认为该 gate 不符合风险控制语义，应另开 gate repair / new work doc，预先修改 fee/tax gate 的方向性和容忍带，再重新执行；不得把本轮结果 retroactively 改成通过。
```

## 8. Production And Order Boundary

通过。

`forbidden_action_audit.csv` 对以下项目均为 `PASS_NOT_PRESENT_OR_NOT_PERFORMED`：

```text
model_training
LTR_score_read
orthogonal_LTR_score_read
stacking_score_read
production_default_provider_change
frontend_agent_monitor_order_chain_change
broker_order_quick_trade
OrderIntent_output
target_weight
target_position
quantity_instruction
future_return_label_used
```

`manifest.json` 和 `diagnostic_semantics_audit.json` 也声明未生成 OrderIntent、target_weight、target_position、quantity_instruction，且内部账本仅为 `internal_replay_ledgers_not_order_intent`。根输出 CSV 独立扫描未发现 `OrderIntent`、`target_weight`、`target_position` 或 `quantity_instruction` 字段。

内部 replay ledger 包含 execution、quantity、cash、NAV、fee、tax 等回放记账字段；这与 ReplayResult/内部 accounting ledger 语义一致，不构成订单、目标仓位或生产输出。

## 9. Findings

### Critical

无 contamination、PIT coverage、RULE_05 freeze、生产化或订单越权阻断项。

### High

1. RULE_05 未通过预冻结 strict OOS gate。唯一实质失败项为 `fee_tax_delta_abs`，即 `70444.52 > 50000.0`。按工作文档，本轮只能判 `FAIL_RULE05_DOES_NOT_PASS_QLIB_ONLY_STRICT_OOS`。

### Medium

1. `fee_tax_delta_abs` gate 的设计可能过严或符号不符合风险控制直觉：RULE_05 总 fee/tax 比 baseline 低约 70k，却因绝对差超过 50k 被阻断。该问题应作为后续 gate repair/new work doc 处理，不能在本轮事后修正。

2. RULE_05 的 2023-2025 结果仍呈现防守型 tradeoff：收益劣后 `-9.454431` 个百分点，但 max drawdown 改善 `20.104594` 个百分点。若后续继续，应围绕风险控制 gate 语义修订，而不是把 RULE_05 解释为收益增强规则。

### Low

1. `market_feature_coverage_audit.csv` 的 `audit_name` 出现 `2021_signal_date_market_feature_coverage` 命名遗留，但日期、窗口和统计值均为 2023-2025；这是低风险命名瑕疵，不影响本轮 verdict。

## 10. Recommendation

建议继续，但不是直接关闭 RULE_05 为通过，也不是生产化。

建议 coordinator 后续开一个明确的 gate repair / new work doc，预冻结更合理的 fee/tax gate，例如区分成本恶化与成本下降，或将费用下降解释为换手/暴露变化的辅助审计项。修订 gate 后必须重新执行并重新审查；本轮 RCPT5B Option B 结论保持：

```text
FAIL_RULE05_DOES_NOT_PASS_QLIB_ONLY_STRICT_OOS
```

不得基于本轮产物输出 OrderIntent、target_weight、target_position、quantity_instruction，不得进入 production/default/provider/frontend/Agent/monitor/order 链路。
