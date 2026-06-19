# Phase D7R Fixed Window Index Gate Repair Review Handoff

生成日期：2026-06-17

## 1. 审查结论建议

建议审查者重点确认：

```text
fixed 2026_ytd window cannot bypass D7 index
generated readonly window still loads indexed D6 artifact
query validator catches missing D7 latest for fixed window
backend tests cover missing latest and missing index entry
readonly boundary remains GET/read-only
```

## 2. 核心变更文件

```text
backend/app/services/readonly_replay_window.py
backend/tests/test_tw_stock_readonly_replay_window_api.py
scripts/validate_tw_readonly_replay_window_query.py
docs/tw_modular_contracts/PHASED7R_FIXED_WINDOW_INDEX_GATE_REPAIR_EXECUTION_REPORT_CN.md
```

## 3. 审查入口

服务层：

```text
backend/app/services/readonly_replay_window.py
```

关键点：

```text
_load_index_entry(...)
_payload_from_index_entry(...)
load_readonly_replay_window(...)
```

应确认固定窗口没有任何直接 D4 fallback。固定 D4 artifact 只能通过 D7 index entry 的 `artifact_manifest` 进入，然后再读取该 D4 artifact 中登记的 `order_intent_replay_result_manifest`。

## 4. 必查测试

```text
backend/tests/test_tw_stock_readonly_replay_window_api.py
```

重点用例：

```text
test_fixed_window_requires_d7_index_latest
test_fixed_window_rejects_when_index_entry_missing
test_fixed_window_response_sources_match_index_entry
test_readonly_replay_window_returns_generated_non_fixed_window_artifact
test_readonly_replay_window_route_has_no_write_methods
```

## 5. 必查 Validator

```text
scripts/validate_tw_readonly_replay_window_query.py
```

重点检查项：

```text
fixed_standard_window_reads_indexed_artifact
query_response_window_index_matches_index_entry
fixed_standard_window_fails_when_d7_latest_missing
generated_window_reads_indexed_artifact
```

## 6. 建议复核命令

```bash
python -m py_compile backend/app/services/readonly_replay_window.py backend/app/services/readonly_replay_window_index.py scripts/validate_tw_readonly_replay_window_query.py backend/tests/test_tw_stock_readonly_replay_window_api.py
python scripts/validate_tw_readonly_replay_window_query.py --json
python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py
python scripts/validate_tw_readonly_replay_window_index.py --json
cd frontend && node tests/unit/tw-stock-readonly-replay-window-check.mjs
cd frontend && corepack pnpm build
node frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

## 7. 通过标准

```text
fixed window missing D7 latest must fail
fixed window missing D7 index entry must fail
fixed response sources.window_index_manifest must match loaded D7 index manifest
fixed response sources.readonly_replay_manifest must equal indexed artifact_manifest
generated window schema remains readonly_replay_window_api_d7r_v1
no POST/PUT/PATCH/DELETE route is introduced for replay window query
frontend E2E sees only GET for readonly replay window index/detail
```

## 8. 安全边界

本轮 D7R 不应包含：

```text
provider refresh/publish
accepted latest switch
monitor scan/config/alerts writes
broker/quick-trade/orders
target_position/target_weight
on-demand replay generation in API handler
frontend local replay
```

