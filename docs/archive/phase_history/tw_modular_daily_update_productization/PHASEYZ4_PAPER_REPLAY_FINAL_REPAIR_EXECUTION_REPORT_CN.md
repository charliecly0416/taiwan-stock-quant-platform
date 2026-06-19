# Phase YZ4 Paper + Replay 最小收口修复执行报告

生成日期：2026-06-18

## 1. 执行结论

Phase YZ4 已完成本阶段要求的两个收口缺口：

- Paper portfolio 后端不再使用旧 `e4_frozen_qlib_2023_2025_ltr` 常量作为 apply 校验；模型与策略改为读取 clean registry / replay policy。
- 当前 `execution_price_status = execution_price_unavailable`、`paper_apply_allowed = false` 时，后端 `apply_decision()` 在任何 schema / apply_runs / orders / trades 写入前拒绝，返回 `execution_price_unavailable`。
- `latest_decision()` 只接受 clean paper decision artifact；旧模型、非生产策略、非 `next_open` artifact 被过滤；无 clean artifact 时返回 `no_clean_decision`。
- 已生成并登记两个 clean E4 readonly replay window artifact，D7 index latest pointer 返回 2 个 clean windows，不返回旧模型。

当前仍保持 pending 状态：

```text
execution_price_status = execution_price_unavailable
paper_apply_allowed = false
paper_apply_blocked_reason = next_open_unavailable
next_open_available_count = 0
missing_next_open_count = 50
```

## 2. 代码变更

### 2.1 Paper portfolio 后端

修改文件：

```text
backend/app/services/tw_stock_paper_portfolio.py
backend/tests/test_tw_stock_paper_portfolio_x2.py
```

关键变化：

- 删除旧 `MODEL_ID = e4_frozen_qlib_2023_2025_ltr` 硬编码。
- `_validate_intent()` 改为读取：
  - `configs/tw_modular_registry.yaml`
  - `configs/tw_replay_window_policy.yaml`
- 只允许：
  - `e4_frozen_qlib_2018_2022`
  - `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`
  - `top50_exit_one_worst_sell`
  - `execution_price_mode = next_open`
- `apply_decision()` 在 `ensure_schema()` 之前执行 productization / execution price gate。
- pending 时拒绝状态：`execution_price_unavailable`。
- `latest_decision()` 过滤旧模型 artifact，并在无 clean artifact 时返回 `no_clean_decision`。

### 2.2 Readonly replay 后端

修改文件：

```text
backend/app/services/readonly_replay_window.py
backend/tests/test_tw_stock_readonly_replay_window_api.py
```

关键变化：

- replay detail payload 显式返回 `execution_price_mode`。
- 测试覆盖两个 clean model detail 均 `ok=true`、`checksum.ok=true`、`execution_price_mode=next_open`。
- 旧模型 detail 仍返回 `deprecated_model_id`。

## 3. 新增 clean replay artifacts

新增生成脚本：

```text
scripts/build_phase_yz4_clean_readonly_replay_artifacts.py
```

执行结果：

```json
{
  "ok": true,
  "d7": {
    "manifest": "data_tw/artifacts/readonly_replay_windows/d7/manifest.json",
    "latest": "data_tw/artifacts/readonly_replay_windows/d7/latest.json",
    "window_count": 2
  }
}
```

D6 clean replay artifacts：

```text
data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2018_2022/top50_exit_one_worst_sell/20260101_20260507/order_intent_replay_result/manifest.json
data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/top50_exit_one_worst_sell/20260101_20260507/order_intent_replay_result/manifest.json
```

每个 D6 目录包含：

```text
summary.csv
daily_nav.csv
actions.csv
position_snapshots.csv
decision_source_audit.csv
forbidden_scope_audit.csv
action_lineage_audit.csv
forbidden_scope_audit.json
checksum_manifest.json
validation_report.json
```

D7 index / pointer：

```text
data_tw/artifacts/readonly_replay_windows/d7/manifest.json
data_tw/artifacts/readonly_replay_windows/d7/checksum_manifest.json
data_tw/artifacts/readonly_replay_windows/d7/latest.json
```

服务层只读校验证据：

```text
index_count = 2
models = [
  e4_frozen_qlib_2018_2022,
  e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
]
Model A detail: ok=True, execution_price_mode=next_open, checksum.ok=True
Model B detail: ok=True, execution_price_mode=next_open, checksum.ok=True
old model detail status = deprecated_model_id
```

## 4. Pending paper apply 证据

单测覆盖：

```text
test_apply_pending_execution_price_rejected_before_schema_and_writes
```

断言：

```text
status = execution_price_unavailable
paper_apply_allowed = false
db.apply_runs = []
db.orders = []
db.trades = []
db.audit = []
没有 CREATE TABLE / ALTER TABLE schema 写入
```

这保证 pending 状态下后端不依赖前端按钮禁用，而是在服务入口拒绝模拟 apply。

## 5. Frontend / E2E 结果

E2E 命令使用静态 `frontend/dist` 服务，产物目录：

```text
/tmp/quantdinger_tw_phase_yz4_e2e
```

E2E 结果摘要：

```text
readonly_replay_window_requests = 2
全部 method = GET
全部请求 model_id = e4_frozen_qlib_2018_2022
不含 e4_frozen_qlib_2023_2025_ltr
paper_apply_write_count = 0
paper_reset_write_count = 0
forbidden_request_count = 0
console_errors = []
page_errors = []
```

## 6. Forbidden Action Audit

本阶段未触发：

```text
provider refresh
provider publish
accepted latest switch
monitor config write
monitor scan
monitor alerts write
broker/order/quick-trade
真实 order
target-position / target_weight
training / tuning
```

新增 replay artifact 为本地只读产物生成；API handler 仍只读取 indexed artifact，不在 GET 路径按需生成 replay。

## 7. 验收命令

已执行并通过：

```text
python -m py_compile backend/app/services/tw_stock_paper_portfolio.py backend/app/services/readonly_replay_window.py backend/app/services/readonly_replay_window_index.py backend/app/routes/tw_stock.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_readonly_replay_window_api.py scripts/build_phase_yz4_clean_readonly_replay_artifacts.py
python scripts/build_phase_yz4_clean_readonly_replay_artifacts.py --json
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz2r_execution_price_readiness.py backend/tests/test_phase_yz3_productization_status.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_readonly_replay_window_api.py -q
cd frontend && node tests/unit/tw-stock-phase-yz-productization-check.mjs
cd frontend && node tests/unit/tw-stock-paper-portfolio-panel-check.mjs
cd frontend && corepack pnpm build
cd frontend && TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8097 TW_STOCK_PHASE_YZ3_E2E_DIR=/tmp/quantdinger_tw_phase_yz4_e2e node tests/e2e/tw-stock-phase-yz-productization-pending.mjs
```

通过结果：

```text
backend pytest: 54 passed
frontend unit: passed
frontend build: passed
frontend E2E: passed
```

备注：部分命令输出包含 `/bin/sh: 2: source: not found`，但对应命令退出码为 0，不影响验证结果。

## 8. 收口判定

YZ4 范围内 P0 / P1 均已完成：

```text
paper backend clean registry 化：完成
pending execution_price 后端拒绝：完成
latest_decision 过滤旧 artifact：完成
两个 clean E4 readonly replay artifacts：完成
D7 latest pointer clean index：完成
旧模型 replay detail deprecated：完成
前端 pending / clean replay E2E：完成
```

结论：Phase YZ4 可判定为 closed。YZ 路线在本阶段约束下达到最终收口条件。
