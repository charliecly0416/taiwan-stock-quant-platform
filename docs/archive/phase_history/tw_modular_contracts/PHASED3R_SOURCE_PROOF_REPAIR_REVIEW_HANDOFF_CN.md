# Phase D3R Source-proof Repair 审查交接

生成日期：2026-06-17

## 1. 审查结论建议

执行侧建议：D3R 可进入审查。D3R 已修复 D3 的核心 blocker：现在 parity replay side 指向新的 OrderIntent ReplayResultArtifact，不再指向旧 `formal_replay_manifest.json`。

```text
baseline_manifest != order_intent_replay_manifest
order_intent_replay_manifest.decision_source=order_intent_artifact
OrderIntentArtifact count=25
Replay actions reference OrderIntentArtifact: pass
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
docs/tw_modular_contracts/PHASED3R_SOURCE_PROOF_REPAIR_EXECUTION_REPORT_CN.md
```

D3R parity manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T053850Z/manifest.json
```

OrderIntent replay result manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T053850Z/order_intent_replay_result/manifest.json
```

## 3. Source-proof 核查

建议审查者重点确认：

```text
baseline_manifest=data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
order_intent_replay_manifest=data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T053850Z/order_intent_replay_result/manifest.json
```

二者不同，且 replay manifest：

```text
artifact_type=replay_result
schema_version=d3_order_intent_replay_result_v1
decision_source=order_intent_artifact
order_intent_artifacts count=25
```

## 4. 覆盖范围

D3R 覆盖 5 methods、5 rules、`2026_ytd`。

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

## 5. Actions 来源引用

OrderIntent replay result 的 actions 包含：

```text
order_intent_artifact
order_intent_row_id
instrument
strategy_rule
model_name
```

抽查样例：

```text
fresh_qlib_adaptive original 2026-01-02 TW3260 historical_add
order_intent_artifact=.../order_intents/fresh_qlib_adaptive/original/manifest.json
order_intent_row_id=fresh_qlib_adaptive|original|2026-01-02|TW3260|buy|1
```

空引用计数为 0。

## 6. Parity 摘要

```text
summary: baseline_rows=25, replay_rows=25, status=pass
daily_nav: baseline_rows=1975, replay_rows=1975, status=pass
actions: baseline_rows=3651, replay_rows=3651, status=pass
action_key: baseline_rows=3651, replay_rows=3651, status=pass
position_snapshot: baseline_rows=11512, replay_rows=11512, status=pass
```

## 7. Validator Hard Gates

请重点复核 validator 是否包含并执行：

```text
order_intent_replay_manifest_not_equal_baseline_manifest
reject_legacy_formal_replay_manifest_as_replay_source
order_intent_replay_manifest_artifact_type
order_intent_replay_manifest_decision_source_order_intent
order_intent_artifacts_exist
order_intent_artifacts_cover_five_rules
order_intent_artifacts_cover_five_methods
order_intent_artifacts_cover_2026_ytd
replay_actions_reference_order_intent_artifact
decision_source_audit_points_to_order_intent_replay_manifest
```

最终 artifact 上述检查均 pass。

## 8. 复核命令

建议复跑：

```bash
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T053850Z/manifest.json --json
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py tests/unit/test_tw_modular_order_intent_replay_parity.py
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

执行者结果：

```text
py_compile: pass
D3R runner: ok=true, parity_status=pass
D3R validator: ok=true
unit tests: 28 passed
contract regression: ok=true
readonly snapshot validator: ok=true
```

## 9. 边界复核

D3R 新增文件定向扫描无匹配：

```bash
rg -n "target_position|target_weight|broker|quick_trade|provider_publish|accepted_latest|monitor/scan|monitor/config|monitor/alerts|POST /api|PUT /api|PATCH /api|DELETE /api" scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py tests/unit/test_tw_modular_order_intent_replay_parity.py
```

D3R 未修改前端/API/daily/provider/accepted latest/monitor/broker/quick-trade/order 链路。

## 10. 建议下一步

若 D3R 审查通过，才允许进入只读产品接入标准 `OrderIntentArtifact` / `ReplayResultArtifact` 的后续阶段。产品接入仍需单独审查 API 只读、前端只展示、diagnostic rule 边界和生产写路径禁用。
