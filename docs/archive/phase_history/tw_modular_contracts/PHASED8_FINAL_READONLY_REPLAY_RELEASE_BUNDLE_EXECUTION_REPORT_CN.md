# Phase D8 Final Readonly Replay Release Bundle 执行报告

生成日期：2026-06-17

## 1. 执行结论

D8 已完成最终发布包与验收收口。本阶段没有新增模型、策略、replay rule、用户窗口生成路径，也没有修改 provider、accepted latest、monitor、broker 或 order 路径。

闭合链路：

```text
D4 readonly standard artifact index
  -> D5 ReplayWindowPolicy 后端窗口校验
  -> D6 audited readonly replay artifact 离线生成
  -> D7 readonly replay window index
  -> D7R fixed/generated 窗口统一经 D7 index gate
  -> D8 final release bundle / acceptance closure
```

结论：

```text
release bundle manifest: pass
all validators: pass
backend/frontend tests: pass
frontend build: pass
E2E GET-only audit: pass
readonly safety boundary: pass
Final anti-regression evidence: complete
```

## 2. D8 发布包产物

```text
data_tw/artifacts/readonly_replay_release_bundle/d8/manifest.json
data_tw/artifacts/readonly_replay_release_bundle/d8/checksum_manifest.json
data_tw/artifacts/readonly_replay_release_bundle/d8/latest.json
```

发布包登记的核心产物：

```text
D4 readonly standard artifact index:
  data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json

D6 readonly replay artifact:
  data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json

D7 readonly replay window index:
  data_tw/artifacts/readonly_replay_windows/d7/manifest.json

D7 latest pointer:
  data_tw/artifacts/readonly_replay_windows/d7/latest.json

ReplayWindowPolicy:
  configs/tw_replay_window_policy.yaml
```

发布包 schema：

```text
readonly_replay_release_bundle_d8_v1
```

## 3. 文档入口

D8 确认并补齐以下入口：

```text
docs/tw_modular_contracts/READONLY_REPLAY_WINDOW_PRODUCTIZATION_GUIDE_CN.md
docs/tw_modular_contracts/TW_MODULAR_DECISION_REPLAY_DECOUPLING_WORK_CN.md
docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
```

中文 README 文档导航已加入 readonly replay productization 入口，后续执行者可从 docs index 找到新增窗口流程与禁止事项。

## 4. Final anti-regression evidence

D8 发布包和本报告固定以下反回归证据：

```text
fixed window requires D7 latest/index: pass
generated window requires D7 latest/index: pass
missing D7 latest fails closed: pass
missing fixed index entry fails closed: pass
query response window_index_manifest matches loaded D7 index entry: pass
```

对应测试/validator：

```text
test_fixed_window_requires_d7_index_latest
test_fixed_window_rejects_when_index_entry_missing
test_fixed_window_response_sources_match_index_entry
fixed_standard_window_reads_indexed_artifact
query_response_window_index_matches_index_entry
fixed_standard_window_fails_when_d7_latest_missing
generated_window_reads_indexed_artifact
```

非法窗口/非法证据拒绝结果：

```text
training window rejected: illegal_training_window_rejected_by_backend=pass
future beyond latest signal rejected: future_beyond_signal_rejected_by_backend=pass
diagnostic rule rejected as valid strategy evidence: diagnostic_rule_not_valid_strategy_evidence=pass
missing indexed artifact rejected: no_audited_replay_artifact_for_window / missing_artifact paths covered
```

## 5. 验证结果

已执行完整 D8 validation bundle：

```text
python scripts/validate_tw_readonly_replay_window_query.py --json
result: ok=true

python scripts/validate_tw_readonly_replay_window_index.py --json
result: ok=true

python scripts/validate_tw_readonly_replay_window_artifact.py --artifact data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json --json
result: ok=true

python scripts/validate_tw_replay_window_policy.py --json
result: ok=true

python scripts/validate_tw_modular_readonly_standard_artifact_index.py --artifact data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json --json
result: ok=true

python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json --json
result: ok=true

python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py
result: 22 passed

cd frontend && node tests/unit/tw-stock-readonly-replay-window-check.mjs
result: ok

cd frontend && corepack pnpm build
result: pass

node frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
result: pass

python scripts/run_tw_modular_contract_regression.py --json
result: ok=true

python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
result: ok=true
```

说明：普通 sandbox 对部分 Python/Node 命令仍有 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` 限制，相关只读验证已按环境规则在沙箱外重跑。前端静态检查与构建存在 `/bin/sh: 2: source: not found` 的 shell 初始化噪声，但脚本和构建本身通过。

## 6. 最终安全审计

D8 确认：

```text
no POST/PUT/PATCH/DELETE in replay window workflow
no provider publish / refresh
no accepted latest switch
no monitor config / scan / alerts writes
no broker / quick-trade / orders
no target_position / target_weight
no frontend local replay
no API handler on-demand replay generation
```

D8 显式声明：

```text
D8 did not generate new replay results in API handler
D8 did not modify provider/accepted latest/monitor/broker/order paths
D8 did not change default strategy
D8 did not add new model/strategy/replay rule
```

安全关键词扫描命中主要为只读否定字段、E2E forbidden request matcher、backend tests forbidden list，以及既有 monitor/sim-orders 功能区；它们不是 D8 新增 replay window 写入口。

## 7. 后续新增窗口流程

后续新增窗口、模型、策略或 replay rule 必须另开阶段，并重新经过：

```text
ReplayWindowPolicy validation
offline artifact generation
artifact validator
window index registration
query validator
readonly API/frontend audit
```

不得在 API handler 中即时生成 replay result，也不得绕过 D7 index gate。
