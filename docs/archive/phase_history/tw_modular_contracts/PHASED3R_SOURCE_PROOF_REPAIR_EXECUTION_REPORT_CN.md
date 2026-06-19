# Phase D3R Source-proof Repair 执行报告

生成日期：2026-06-17

## 1. 执行结论

D3R 已修复 D3 的 source-proof blocker：新的 D3R parity 不再把旧 `formal_replay_manifest.json` 同时作为 baseline 与 replay source，而是生成真实的全窗口 OrderIntent artifacts、独立 OrderIntent replay result artifact，再用该 replay result 与旧 baseline 做 parity。

结论：

```text
D3R source-proof repair: pass
OrderIntentArtifact generation: pass
OrderIntent ReplayResultArtifact generation: pass
baseline_manifest != order_intent_replay_manifest: pass
replay decision_source=order_intent_artifact: pass
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
docs/tw_modular_contracts/PHASED3R_SOURCE_PROOF_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED3R_SOURCE_PROOF_REPAIR_REVIEW_HANDOFF_CN.md
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

D3R parity manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T053850Z/manifest.json
```

真实 OrderIntent replay result manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T053850Z/order_intent_replay_result/manifest.json
```

baseline manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

Source audit：

```text
baseline_manifest=data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
order_intent_replay_manifest=data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T053850Z/order_intent_replay_result/manifest.json
replay_decision_source=order_intent_artifact
order_intent_artifact_count=25
```

## 4. OrderIntent Artifacts

D3R 生成 25 个 OrderIntentArtifact manifest，覆盖 5 methods x 5 rules。

示例：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T053850Z/order_intents/e4_frozen_qlib_2023_2025_ltr/original/manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T053850Z/order_intents/frozen_qlib_2025_ltr/one_sell_one_buy_buggy_e8r/manifest.json
```

每个 OrderIntent manifest 明确：

```text
artifact_type=order_intent
schema_version=order_intent_d3_full_window_v1
artifact_stage=d3_full_window_replay_input
readonly_only=true
not_order=true
not_investment_advice=true
not_parity_evidence=false
window=2026_ytd
```

`one_sell_one_buy_buggy_e8r` 保持：

```text
diagnostic_only=true
not_valid_strategy_evidence=true
```

## 5. ReplayResult Source Proof

D3R replay result manifest 明确：

```text
artifact_type=replay_result
schema_version=d3_order_intent_replay_result_v1
decision_source=order_intent_artifact
order_intent_artifacts=[25 manifests]
window=2026_ytd
```

Replay actions 已追加来源字段：

```text
order_intent_artifact
order_intent_row_id
instrument
strategy_rule
model_name
```

抽查：

```text
fresh_qlib_adaptive original 2026-01-02 TW3260 historical_add
  order_intent_artifact=.../order_intents/fresh_qlib_adaptive/original/manifest.json
  order_intent_row_id=fresh_qlib_adaptive|original|2026-01-02|TW3260|buy|1
```

空引用计数：

```text
order_intent_artifact empty refs: 0
order_intent_row_id empty refs: 0
```

## 6. Parity 结果

```text
parity_status=pass
summary: baseline_rows=25, replay_rows=25, status=pass
daily_nav: baseline_rows=1975, replay_rows=1975, status=pass
actions: baseline_rows=3651, replay_rows=3651, status=pass
action_key: baseline_rows=3651, replay_rows=3651, status=pass
position_snapshot: baseline_rows=11512, replay_rows=11512, status=pass
```

## 7. Validator 加固

`validate_tw_modular_order_intent_replay_parity.py` 新增 source-proof hard gates：

```text
order_intent_replay_manifest_not_equal_baseline_manifest
order_intent_replay_manifest_artifact_type
order_intent_replay_manifest_decision_source_order_intent
order_intent_artifacts_exist
order_intent_artifacts_cover_five_rules
order_intent_artifacts_cover_five_methods
order_intent_artifacts_cover_2026_ytd
replay_actions_reference_order_intent_artifact
decision_source_audit_points_to_order_intent_replay_manifest
reject_legacy_formal_replay_manifest_as_replay_source
```

最终 D3R artifact 上述 checks 全部 pass。

## 8. 测试补充

新增/保留 D3R source-proof 负例：

```text
test_d3_rejects_order_intent_replay_manifest_equal_to_baseline_manifest
test_d3_rejects_legacy_formal_replay_manifest_as_order_intent_replay_source
test_d3_rejects_missing_order_intent_artifact
test_d3_rejects_replay_manifest_without_order_intent_decision_source
test_d3_rejects_actions_without_order_intent_artifact_reference
test_d3_rejects_decision_source_audit_pointing_to_baseline_manifest
```

同时保留 CSV mismatch、missing rule、diagnostic rule boundary 负例。

## 9. 验证结果

已执行：

```bash
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py
python scripts/run_tw_modular_order_intent_replay_parity.py --json
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T053850Z/manifest.json --json
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py tests/unit/test_tw_modular_order_intent_replay_parity.py
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：

```text
py_compile: pass
D3R runner: ok=true, parity_status=pass
D3R validator: ok=true
unit tests: 28 passed in 130.80s
contract regression: ok=true
readonly snapshot validator: ok=true
```

Source audit：

```text
baseline_manifest != order_intent_replay_manifest: pass
replay_decision_source=order_intent_artifact
order_intent_artifact_count=25
```

只读边界定向扫描：

```bash
rg -n "target_position|target_weight|broker|quick_trade|provider_publish|accepted_latest|monitor/scan|monitor/config|monitor/alerts|POST /api|PUT /api|PATCH /api|DELETE /api" scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py tests/unit/test_tw_modular_order_intent_replay_parity.py
```

结果：无匹配。

## 10. 边界声明

D3R 没有进入产品化 API/前端接入；没有修改 daily/provider/accepted latest/monitor/broker/quick-trade/order 链路；没有训练、调参、score 重算、默认模型或默认策略切换。
