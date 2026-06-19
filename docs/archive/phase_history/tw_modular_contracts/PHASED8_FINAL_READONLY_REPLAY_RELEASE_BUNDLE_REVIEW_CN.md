# Phase D8 Final Readonly Replay Release Bundle 审查结论

生成日期：2026-06-17

## 1. 审查结论

D8 通过，可以收尾。

本轮复核结论：

```text
D8 release bundle manifest exists: pass
checksum manifest and latest pointer exist: pass
manifest registered artifacts/docs exist and checksums match: pass
Final anti-regression evidence complete: pass
ReplayWindowPolicy illegal-window rejection evidence: pass
D7R fixed/generated D7 index gate preserved: pass
backend/frontend validation bundle: pass
E2E network audit GET-only: pass
readonly safety boundary preserved: pass
no new model/strategy/replay rule/user window generation path: pass
```

未发现阻塞问题。D4-D7R readonly replay 主线可以按 D8 作为本轮产品化收口版本冻结。

## 2. 审查对象

```text
docs/tw_modular_contracts/PHASED8_FINAL_READONLY_REPLAY_RELEASE_BUNDLE_REVIEW_HANDOFF_CN.md
docs/tw_modular_contracts/PHASED8_FINAL_READONLY_REPLAY_RELEASE_BUNDLE_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED7R_REVIEW_AND_PHASED8_WORK_CN.md
data_tw/artifacts/readonly_replay_release_bundle/d8/manifest.json
data_tw/artifacts/readonly_replay_release_bundle/d8/checksum_manifest.json
data_tw/artifacts/readonly_replay_release_bundle/d8/latest.json
docs/tw_modular_contracts/READONLY_REPLAY_WINDOW_PRODUCTIZATION_GUIDE_CN.md
docs/README_CN.md
```

核心实现抽查：

```text
backend/app/routes/readonly_replay_window.py
backend/app/routes/readonly_replay_window_index.py
backend/app/services/readonly_replay_window.py
backend/app/services/readonly_replay_window_index.py
frontend/src/views/tw-stock-monitor/index.vue
frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
frontend/tests/unit/tw-stock-readonly-replay-window-check.mjs
```

## 3. Findings

未发现 Critical / High / Medium 问题。

### Low: 后续新增能力必须另开阶段，不得混入 D8 收口包

D8 已明确冻结为 release bundle / acceptance closure。后续如果要新增窗口、模型、策略或 replay rule，必须另开阶段，并重新经过：

```text
ReplayWindowPolicy validation
offline artifact generation
artifact validator
window index registration
query validator
readonly API/frontend audit
```

不得在 API handler 中即时生成 replay result，也不得绕过 D7 index gate。

## 4. Release Bundle 复核

D8 manifest 满足收口字段：

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

登记产物齐全：

```text
D4 readonly standard artifact index manifest
D6 readonly replay artifact manifest
D7 readonly replay window index manifest
D7 latest pointer
ReplayWindowPolicy
readonly strategy snapshot latest
D7R/D8 docs
docs README entry
```

本轮额外复核了 `manifest.json` 中 `artifact_checksums` 与 `doc_checksums` 的真实文件存在性、sha256 与 bytes，结果：

```text
ok=true
bad=[]
```

## 5. Final Anti-Regression Evidence

D8 发布包和执行报告均包含以下反回归证据：

```text
fixed window requires D7 latest/index: pass
generated window requires D7 latest/index: pass
missing D7 latest fails closed: pass
missing fixed index entry fails closed: pass
query response window_index_manifest matches loaded D7 index entry: pass
```

非法窗口/非法证据拒绝结果已覆盖：

```text
training window rejected: pass
future beyond latest signal rejected: pass
diagnostic rule rejected as valid strategy evidence: pass
missing indexed artifact rejected: pass
```

`scripts/validate_tw_readonly_replay_window_query.py --json` 已复核并返回 `ok=true`，其中包括：

```text
illegal_training_window_rejected_by_backend: pass
future_beyond_signal_rejected_by_backend: pass
diagnostic_rule_not_valid_strategy_evidence: pass
fixed_standard_window_fails_when_d7_latest_missing: pass
generated_window_reads_indexed_artifact: pass
generated_non_fixed_window_not_on_demand: pass
```

## 6. 验证结果

本轮审查实际执行并通过：

```text
python scripts/validate_tw_readonly_replay_window_query.py --json : ok=true
python scripts/validate_tw_readonly_replay_window_index.py --json : ok=true
python scripts/validate_tw_readonly_replay_window_artifact.py --artifact data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json --json : ok=true
python scripts/validate_tw_replay_window_policy.py --json : ok=true
python scripts/validate_tw_modular_readonly_standard_artifact_index.py --artifact data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json --json : ok=true
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json --json : ok=true
python scripts/run_tw_modular_contract_regression.py --json : ok=true
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json : ok=true
python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py : 22 passed
node tests/unit/tw-stock-readonly-replay-window-check.mjs : ok
corepack pnpm build : pass
node frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs : pass
```

说明：普通 sandbox 对部分 Python/Node 命令仍有 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` 限制，相关只读验证已按环境规则重跑。前端静态检查与 build 仍出现 `/bin/sh: 2: source: not found` 的既有 shell 初始化噪声，但命令退出码为 0。

## 7. 只读安全边界

新增 replay window 路由抽查结果：

```text
GET /api/tw-stock/readonly-replay-window-index
GET /api/tw-stock/readonly-replay-window
```

未发现 replay window workflow 中的：

```text
POST/PUT/PATCH/DELETE
provider publish / refresh
accepted latest switch
monitor config / scan / alerts writes
broker / quick-trade / orders
target_position / target_weight
frontend local replay
API handler on-demand replay generation
```

前端 `tw-stock-monitor/index.vue` 中命中的 monitor、broker、orders、accepted 等历史词汇不构成本轮 D8 越界；本轮重点审查的是 readonly replay window panel、loader、API wrapper 与 E2E forbidden request matcher。

## 8. 收尾判断

可以收尾。

收尾后应将 D8 作为 readonly replay window 产品化基线：

```text
release bundle = data_tw/artifacts/readonly_replay_release_bundle/d8/manifest.json
latest pointer = data_tw/artifacts/readonly_replay_release_bundle/d8/latest.json
productization guide = docs/tw_modular_contracts/READONLY_REPLAY_WINDOW_PRODUCTIZATION_GUIDE_CN.md
```

后续新主线建议从“新增窗口/模型/策略的离线注册流程”开始，而不是继续修改 D8 收口包本身。
