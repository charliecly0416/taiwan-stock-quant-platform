# Phase D8 Final Readonly Replay Release Bundle Review Handoff

生成日期：2026-06-17

## 1. 审查结论建议

建议审查者按最终收口口径审查：

```text
D8 release bundle manifest exists
all validators ok=true
backend/frontend tests pass
frontend build pass
E2E network audit GET-only
Final anti-regression evidence complete
readonly safety boundary preserved
no new model/strategy/replay rule/user window generation path
```

## 2. 核心审查对象

```text
data_tw/artifacts/readonly_replay_release_bundle/d8/manifest.json
data_tw/artifacts/readonly_replay_release_bundle/d8/checksum_manifest.json
data_tw/artifacts/readonly_replay_release_bundle/d8/latest.json
docs/tw_modular_contracts/PHASED8_FINAL_READONLY_REPLAY_RELEASE_BUNDLE_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/READONLY_REPLAY_WINDOW_PRODUCTIZATION_GUIDE_CN.md
docs/README_CN.md
```

## 3. Release bundle 必查项

```text
artifact_type=readonly_replay_release_bundle
schema_version=readonly_replay_release_bundle_d8_v1
readonly_only=true
production_trade_enabled=false
release_scope.new_model_added=false
release_scope.new_strategy_added=false
release_scope.new_replay_rule_added=false
release_scope.user_window_generation_path_added=false
release_scope.api_handler_generated_replay_result=false
```

必须登记：

```text
D4 readonly standard artifact index manifest
D6 readonly replay artifact manifest
D7 readonly replay window index manifest
D7 latest pointer
ReplayWindowPolicy
D7R query validator result
backend/frontend validation bundle
```

## 4. Final anti-regression evidence

重点确认 D8 manifest 与执行报告均包含：

```text
fixed window requires D7 latest/index
generated window requires D7 latest/index
missing D7 latest fails closed
missing fixed index entry fails closed
query response window_index_manifest matches loaded D7 index entry
training window rejected
future beyond latest signal rejected
diagnostic rule rejected as valid strategy evidence
missing indexed artifact rejected
```

## 5. 建议复核命令

```bash
python scripts/validate_tw_readonly_replay_window_query.py --json
python scripts/validate_tw_readonly_replay_window_index.py --json
python scripts/validate_tw_readonly_replay_window_artifact.py --artifact data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json --json
python scripts/validate_tw_replay_window_policy.py --json
python scripts/validate_tw_modular_readonly_standard_artifact_index.py --artifact data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json --json
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json --json
python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py
cd frontend && node tests/unit/tw-stock-readonly-replay-window-check.mjs
cd frontend && corepack pnpm build
node frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

## 6. 安全边界复核

D8 不应出现：

```text
replay window POST/PUT/PATCH/DELETE
provider refresh/publish
accepted latest switch
monitor scan/config/alerts writes
broker/quick-trade/orders
target_position/target_weight
frontend local replay
API handler on-demand replay generation
default strategy switch
new model/strategy/replay rule
```

审查 `frontend/src/views/tw-stock-monitor/index.vue` 时应限定 replay-window panel、loader 和 API wrapper；该文件中既有 monitor、broker、sim-orders 词汇不等于 D8 越界。
