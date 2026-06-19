# Phase D3RR Forward Chain Repair 执行报告

生成日期：2026-06-17

## 1. 执行结论

D3RR 已完成。新的 parity 不再沿用旧回放副本，而是显式构建：`ModelSignalArtifact + PortfolioState + StrategyRuleConfig -> StrategyDecisionEngine -> OrderIntentArtifact -> ReplayExecutionEngine -> ReplayResultArtifact -> parity`。

结论：

```text
D3RR forward chain repair: pass
OrderIntentArtifact generation: pass
ReplayResultArtifact generation: pass
baseline_manifest != order_intent_replay_manifest: pass
replay decision_source=order_intent_artifact: pass
replay generated_by=replay_execution_engine: pass
order_intent_action_rows_have_decision_fields: pass
replay_result_actions_order_intent_rows_exist_and_match: pass
five-rule/five-method/2026_ytd coverage: pass
summary/daily_nav/actions/action_key/position_snapshot parity: pass
readonly boundary: pass
```

## 2. 修改范围

修改：

```text
scripts/run_tw_modular_order_intent_replay_parity.py
scripts/validate_tw_modular_order_intent_replay_parity.py
tests/unit/test_tw_modular_order_intent_replay_parity.py
```

新增文档：

```text
docs/tw_modular_contracts/PHASED3RR_FORWARD_CHAIN_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED3RR_FORWARD_CHAIN_REPAIR_REVIEW_HANDOFF_CN.md
```

未修改、未触碰：

```text
frontend/**
backend/**
backend_api_python/src/api/**
scripts/run_daily_tw_stock_auto_update.py
scripts/publish_tw_modular_readonly_snapshot.py
scripts/run_tw_modular_config_replay_matrix.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
provider / accepted latest / monitor / broker / quick-trade / order 相关路径
```

## 3. 新产物

D3RR parity manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json
```

真实 OrderIntent replay result manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/order_intent_replay_result/manifest.json
```

baseline manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

Source audit：

```text
baseline_manifest=data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
order_intent_replay_manifest=data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/order_intent_replay_result/manifest.json
replay_decision_source=order_intent_artifact
generated_by=replay_execution_engine
legacy_replay_used_only_for_parity=true
order_intent_artifact_count=25
```

## 4. Forward chain 说明

D3RR 不是从 replay actions 或 replay snapshots 反向拼装 OrderIntent，而是按前向链生成。

OrderIntent 行明确记录：

```text
generation_source=strategy_decision_engine
not_generated_from_replay_actions=true
not_generated_from_replay_snapshots=true
```

ReplayResult 侧明确记录：

```text
generated_by=replay_execution_engine
execution_input_source=order_intent_artifact
decision_source=order_intent_artifact
not_copied_from_legacy_replay=true
legacy_replay_used_only_for_parity=true
```

## 5. 额外门禁

validator 新增并通过：

```text
order_intents_generation_source_strategy_decision_engine
order_intents_not_generated_from_replay_actions
order_intents_not_generated_from_replay_snapshots
order_intent_action_rows_have_decision_fields
replay_result_generated_by_replay_execution_engine
replay_result_not_copied_from_legacy_replay
replay_result_execution_input_source_order_intent
legacy_replay_used_only_for_parity
replay_result_actions_order_intent_rows_exist_and_match
replay_result_outputs_recomputed_checksum_not_legacy_copy
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

## 7. 验证结果

```text
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py : pass
python scripts/run_tw_modular_order_intent_replay_parity.py --json : pass
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact <D3RR parity manifest> --json : pass
python -m pytest tests/unit/test_tw_modular_order_intent_replay_parity.py : pass
python scripts/run_tw_modular_contract_regression.py --json : pass
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json : pass
```

## 8. 审查要点

审查者建议重点看三点：

```text
1. replay_result 是否真的由 OrderIntent 执行链生成，而不是复制旧 replay 文件。
2. action 行是否保留决策字段与 order_intent_row_id 的可追溯关系。
3. validator 是否能拒绝 replay-actions / replay-snapshots 伪装的 OrderIntent。
```
