---
created_at: 2026-06-22T11:22:54+00:00
status: executed_pal1_allocation_env_tensor_memory_build
phase: PAL1_ALLOCATION_ENV_TENSOR_MEMORY_BUILD
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_PAL0_PAPER_CONTRACT_AUDIT_REVIEW_CN.md
artifact_root: data_tw/experiments/paper_aligned_portfolio_rl/pal1_allocation_env_tensor_memory_build
strict_test_used: false
training_run: false
recommendation: PASS_READY_FOR_REVIEWER_TO_DECIDE_PAL2_FEASIBILITY_WORK
---

# PAL1 Allocation Env / Tensor / Memory Build 执行报告

## 1. Scope

本轮执行 PAL1：构建 paper-aligned allocation environment 所需的 tensor / portfolio memory / action-space / cost / PIT audit。

明确未执行：

```text
训练模型
运行 validation 收益结论
运行 strict_test
输出 OrderIntent
输出真实 target_position / target_weight / quantity / broker order
provider/latest/monitor/frontend/Agent/broker/production 扩权
```

## 2. Inputs

```text
PAL0 artifact root = data_tw/experiments/paper_aligned_portfolio_rl/pal0_paper_contract_audit
input_signal_artifact = data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
strict_test declared only = 2026-01-01..2026-05-07
```

## 3. Artifacts Produced

```text
allocation_env_schema.json
price_tensor_index.csv
price_tensor_sample.csv
portfolio_memory_artifact.csv
allocation_action_space_audit.csv
baseline_parity_metrics.csv
transaction_cost_audit.csv
feature_available_at_audit.csv
forbidden_consumer_runtime_audit.csv
forbidden_feature_audit.csv
validator_report.json
golden_samples_report.json
manifest.json
```

## 4. Evidence

```text
price_tensor_dates = 723
price_tensor_sample_rows = 500
portfolio_memory_rows = 723
baseline_parity_status = PASS
feature_available_at_status = PASS
validator_status = PASS_PAL1_ENV_TENSOR_MEMORY_BUILD_VALIDATOR
golden_status = PASS_PAL1_GOLDEN_SAMPLES
```

## 5. Compliance

```text
training_run = false
validation_return_replay_run = false
strict_test_used = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
production_allowed = false
```

## 6. Recommendation

```text
PASS_READY_FOR_REVIEWER_TO_DECIDE_PAL2_FEASIBILITY_WORK
```
