# Phase D3RR Forward Chain Repair 审查交接

生成日期：2026-06-17

## 1. 审查结论建议

执行侧建议：D3RR 可进入审查。D3RR 已把回放链路改成前向生成，不再把旧 `formal_replay_manifest.json` 当作 replay source。

```text
baseline_manifest != order_intent_replay_manifest
order_intent_replay_manifest.decision_source=order_intent_artifact
order_intent_replay_manifest.generated_by=replay_execution_engine
legacy_replay_used_only_for_parity=true
order_intent_action_rows_have_decision_fields: pass
replay_result_actions_order_intent_rows_exist_and_match: pass
all parity CSV: pass
```

## 2. 审查对象

核心实现：

```text
scripts/run_tw_modular_order_intent_replay_parity.py
scripts/validate_tw_modular_order_intent_replay_parity.py
tests/unit/test_tw_modular_order_intent_replay_parity.py
```

执行报告：

```text
docs/tw_modular_contracts/PHASED3RR_FORWARD_CHAIN_REPAIR_EXECUTION_REPORT_CN.md
```

D3RR parity manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json
```

OrderIntent replay result manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/order_intent_replay_result/manifest.json
```

## 3. Source-proof 核查

建议审查者重点确认：

```text
baseline_manifest=data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
order_intent_replay_manifest=data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/order_intent_replay_result/manifest.json
```

二者不同，且 replay manifest：

```text
artifact_type=replay_result
schema_version=d3_order_intent_replay_result_v1
generated_by=replay_execution_engine
execution_input_source=order_intent_artifact
decision_source=order_intent_artifact
order_intent_artifacts count=25
```

## 4. 覆盖范围

D3RR 覆盖 5 methods、5 rules、`2026_ytd`。

Rules：

```text
original
top50_exit_all
top50_exit_one_worst_sell
one_sell_one_buy_correct
one_sell_one_buy_buggy_e8r
```

Methods：

```text
e4_frozen_qlib_2023_2025_ltr
fresh_qlib_2025_ltr
fresh_qlib_adaptive
frozen_qlib_2018_2022
frozen_qlib_2025_ltr
```

`one_sell_one_buy_buggy_e8r` 仅保留 diagnostic parity，不是有效策略或产品策略证据。

## 5. 风险点

审查时重点看三处：

```text
1. OrderIntent 的 buy/sell 行是否都有决策字段来源。
2. ReplayResult 的 actions 是否逐行引用 order_intent_artifact + order_intent_row_id。
3. validator 是否能拒绝 replay_actions / replay_snapshots 伪装的 intent。
```

## 6. 负向测试

新增并通过：

```text
test_rejects_order_intents_generated_from_replay_actions
test_rejects_order_intents_generated_from_replay_snapshots
test_rejects_replay_result_generated_by_parity_wrapper_copy
test_rejects_replay_result_without_execution_input_source_order_intent
test_rejects_action_refs_that_do_not_match_order_intent_rows
test_rejects_action_rows_with_blank_decision_fields_when_required
test_rejects_legacy_replay_used_as_execution_source
```
