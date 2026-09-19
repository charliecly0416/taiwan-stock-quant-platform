---
created_at: 2026-06-22
status: reviewer_next_work_document
phase: PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_REVIEW_CN.md
previous_execution_report: docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_EXECUTION_REPORT_CN.md
pba0_artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba0_contract_baseline_audit
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay
strict_test_authorized: false
training_authorized: false
active_policy_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PBA1 Baseline Snapshot Build And Parity Replay 工作文档

## 1. 本轮目标

你是执行者。请继续 PBA Baseline-anchored Active Policy 主线的第二步：

```text
PBA1: Baseline Snapshot Build And Parity Replay
```

本轮目标是构建 baseline action snapshot，并证明 readonly replay 能复现 baseline 口径。

本轮不训练 active policy，不运行 strict_test，不做 PBA2 active overlay rule selection。

## 2. 必须读取

执行前必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_WORK_CN.md
```

必须使用 PBA0 合同产物：

```text
data_tw/experiments/baseline_anchored_active_policy/pba0_contract_baseline_audit/
```

必须使用 frozen qlib signal artifact：

```text
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
```

## 3. 授权范围

本轮只允许：

```text
1. 构建 BaselineActionSnapshotArtifact。
2. 构建 baseline parity replay ledger。
3. 计算 baseline parity metrics。
4. 做 feature available_at / PIT audit。
5. 做 cash/no-trade gate dry-run audit。
6. 设计并运行 PBA1 validator / golden samples。
7. 写 PBA1 execution report。
```

本轮不允许：

```text
1. 训练模型。
2. 运行 active overlay policy。
3. 做 validation 选择。
4. 运行或读取 strict_test。
5. 输出 OrderIntent。
6. 输出 target_weight / target_position / quantity / broker_order。
7. provider publish / accepted latest switch。
8. monitor write / frontend default / Agent recommendation。
9. broker / quick-trade / real order。
10. 修改 production/default 策略。
11. 从零 free allocation。
```

## 4. 数据窗口

本轮构建 baseline snapshot 和 parity replay 时，必须保持窗口分离：

```text
policy train = 2023-01-01..2024-12-31
policy validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07, declared only, not used
```

PBA1 允许同时输出 train / validation 的 baseline snapshot 和 parity metrics，但不得读取或输出 strict_test metrics。

## 5. 必须输出产物

artifact root：

```text
data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay/
```

必须输出：

```text
manifest.json
baseline_action_snapshot_artifact.csv
baseline_parity_replay_ledger.csv
baseline_parity_metrics.csv
baseline_action_coverage_audit.csv
feature_available_at_audit.csv
cash_no_trade_gate_dry_run_audit.csv
forbidden_feature_and_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

必须写执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_EXECUTION_REPORT_CN.md
```

## 6. BaselineActionSnapshotArtifact 要求

`baseline_action_snapshot_artifact.csv` 必须遵守 PBA0 schema，至少包含：

```text
date
instrument
split
baseline_rank
baseline_score
baseline_action_type
baseline_position_before_diagnostic
baseline_position_after_diagnostic
baseline_holding_age
baseline_candidate_reason
source_signal_artifact
simulation_only
readonly_research_only
production_allowed
```

`baseline_action_type` 至少应能区分：

```text
buy_candidate
sell_candidate
hold
no_action
```

如果实际 baseline 口径使用不同动作枚举，必须在执行报告中说明映射关系，并证明仍以 baseline 为锚点。

## 7. Baseline Parity Replay 要求

`baseline_parity_replay_ledger.csv` 必须记录 readonly replay 过程，至少包含：

```text
date
split
instrument
baseline_action_type
baseline_rank
baseline_score
position_before_diagnostic
position_after_diagnostic
cash_before_diagnostic
cash_after_diagnostic
fee
sell_tax
turnover
gross_return
net_return_after_fee_tax
simulation_only
readonly_research_only
production_allowed
```

`baseline_parity_metrics.csv` 必须至少包含 train / validation 两个 split：

```text
split
start_date
end_date
baseline_reference_net_return_after_fee_tax
pba1_replay_net_return_after_fee_tax
absolute_diff
relative_diff
baseline_reference_turnover
pba1_replay_turnover
turnover_diff
status
```

通过条件：

```text
baseline parity pass
```

如果无法复现 baseline return / turnover，必须 STOP，不得进入 PBA2。

## 8. Feature Available-at / PIT Audit

`feature_available_at_audit.csv` 必须覆盖 baseline snapshot 中使用的全部字段：

```text
baseline_rank
baseline_score
baseline_action_type
baseline_position_before_diagnostic
baseline_holding_age
price / cost / turnover inputs
market state inputs, if any
```

必须确认：

```text
1. 没有 future_return。
2. 没有 label。
3. 没有 future price。
4. 没有 realized_pnl as feature。
5. 没有 same-day unavailable data。
6. 没有 strict_test metrics。
7. 没有 validation metric used inside training loop。
```

## 9. Cash / No-trade Gate Dry-run Audit

`cash_no_trade_gate_dry_run_audit.csv` 必须把 PBA0 gate 落成可计算字段，至少包含：

```text
split
minimum_participation_rate_design
actual_baseline_participation_rate
minimum_risk_asset_exposure_design
actual_baseline_risk_asset_exposure
maximum_cash_dominance_rate_design
actual_baseline_cash_dominance_rate
minimum_baseline_action_coverage_design
actual_baseline_action_coverage
minimum_buy_candidate_coverage_design
actual_buy_candidate_coverage
minimum_sell_review_coverage_design
actual_sell_review_coverage
status
```

PBA1 不是 active policy 评估，因此该 audit 是 dry-run；但必须证明后续 PBA2 可以用同一字段阻止 cash-only / no-trade 形式通过。

## 10. Baseline Action Coverage Audit

`baseline_action_coverage_audit.csv` 必须报告：

```text
split
rebalance_date_count
instrument_count
buy_candidate_count
sell_candidate_count
hold_count
no_action_count
baseline_action_type_coverage_pass
missing_action_context
status
```

如果 baseline snapshot 无法覆盖 buy/sell/hold 或无法解释缺失，必须 STOP。

## 11. Forbidden Feature / Consumer Audit

`forbidden_feature_and_consumer_audit.csv` 必须覆盖：

```text
future_return
forward_return
label
realized_pnl
future_price
same_day_unavailable_data
strict_test_metrics
oracle_action
oracle_return
target_weight
target_position
quantity
broker_order
OrderIntentArtifact
provider publish / accepted latest switch
monitor / frontend / Agent / broker / production
```

全部必须为未使用 / 未触达。

## 12. Validator / Golden Samples

`validator_report.json` 必须检查：

```text
pba0_contract_loaded
baseline_action_snapshot_artifact_exists
baseline_parity_replay_ledger_exists
baseline_parity_metrics_exists
baseline_parity_pass
feature_available_at_audit_pass
baseline_action_coverage_pass
cash_no_trade_gate_dry_run_audit_exists
strict_test_not_used
no_training_run
no_active_policy_run
no_order_intent_output
no_target_weight
no_target_position
no_quantity
no_broker_order
no_provider_monitor_frontend_agent_production
```

`golden_samples_report.json` 必须包含：

```text
positive: baseline buy candidate snapshot accepted.
positive: baseline sell candidate snapshot accepted.
positive: baseline hold context snapshot accepted.
positive: readonly baseline parity replay accepted.
negative: target_weight field must fail.
negative: target_position field must fail.
negative: quantity / broker_order must fail.
negative: OrderIntentArtifact consumer must fail.
negative: strict_test metrics access must fail.
negative: free allocation vector must fail.
negative: active policy output in PBA1 must fail.
negative: cash/no-trade gate missing fields must fail.
```

## 13. 执行报告要求

执行报告必须包括：

```text
1. Scope：说明只做 PBA1 baseline snapshot/parity。
2. Documents read：列出本工作文档要求读取的文件。
3. Changes / artifacts：列出输出产物。
4. Baseline snapshot summary：date count、instrument count、action counts。
5. Parity metrics：train / validation return 和 turnover parity。
6. PIT / available-at audit summary。
7. Cash/no-trade gate dry-run summary。
8. Forbidden actions audit。
9. Issues / blockers / deviations。
10. Recommendation：只能是 PASS_READY_FOR_REVIEWER_TO_AUDIT_PBA1 或 STOP_FOR_BASELINE_PARITY_OR_CONTRACT_FAILURE。
```

如果 baseline parity、PIT audit、action coverage 或 forbidden consumer 任一失败，必须：

```text
STOP_FOR_BASELINE_PARITY_OR_CONTRACT_FAILURE
```

不得进入 PBA2。
