# Phase YZ3 产品化 E2E 执行报告

生成日期：2026-06-18

## 1. 执行结论

YZ3 已完成 clean E4 产品化 API / 前端 / paper apply pending 阻断接入。

当前 execution price 状态仍为 pending：

```text
signal_asof = 2026-06-17
execution_price_mode = next_open
execution_price_status = execution_price_unavailable
paper_apply_allowed = false
paper_apply_blocked_reason = next_open_unavailable
```

结论：YZ clean productization 可以按“功能收口、成交价等待行情更新”的口径提交验收。当前没有把 2026-06-18 next_open 缺失状态伪装成可成交，也没有 fallback 到 next_close / signal_close。

## 2. 本次改动

### 2.1 后端只读产品化状态 API

新增服务：

```text
backend/app/services/phase_yz3_productization_status.py
```

新增 GET 路由：

```text
GET /api/tw-stock/phase-yz/productization-status
```

返回字段包含：

```text
ok
schema_version
signal_asof
models[]
production_strategies[]
selected_model_id
selected_strategy_rule_id
execution_price_mode
execution_price_status
execution_price_message
execution_price_readiness
paper_apply_allowed
paper_apply_blocked_reason
paper_portfolio
latest_artifacts
strategy_preview
safety_flags
```

API 只读，不触发 provider refresh / provider publish / accepted latest switch / monitor write / broker / quick-trade / paper apply。

### 2.2 API 返回摘要证据

本地服务输出摘要：

```text
schema_version = yz3_productization_status_v1
models = ['e4_frozen_qlib_2018_2022', 'e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025']
strategies = ['top50_exit_one_worst_sell']
selected = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025 / top50_exit_one_worst_sell
execution = next_open / execution_price_unavailable
paper = False / next_open_unavailable
message = 成交口径：次一交易日开盘价。2026-06-18 行情暂不可用，等待下一轮数据更新。策略信号已生成，模拟应用将在成交价可用后开放。
model_b_top_candidate_preview_count = 8
```

### 2.3 前端产品化卡片

修改：

```text
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
```

新增 YZ3 产品化卡片：

```text
data-testid="phase-yz-productization-card"
data-testid="phase-yz-execution-price-pending"
data-testid="phase-yz-paper-apply-disabled"
```

用户态明确展示：

```text
成交口径：次一交易日开盘价
2026-06-18 行情暂不可用，等待下一轮数据更新
策略信号已生成，模拟应用将在成交价可用后开放
```

前端默认产品化视图只展示：

```text
e4_frozen_qlib_2018_2022
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
top50_exit_one_worst_sell
```

### 2.4 Paper Portfolio pending 阻断

修改：

```text
frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue
```

主页面向 PaperPortfolioPanel 传入：

```text
:phase-yz-status="phaseYZProductizationPayload"
```

当：

```text
phaseYzStatus.paper_apply_allowed === false
```

则：

```text
paper apply 按钮禁用
显示 data-testid="paper-apply-blocked-by-execution-price"
不打开 apply confirm
不发送 paper apply POST
```

## 3. 禁止项检查

YZ3 默认产品化 API / 前端卡片未暴露以下历史项：

```text
origin
original
P3
O4
fresh qlib adaptive
fresh qlib 2025 LTR
bridge
e4_frozen_qlib_2023_2025_ltr
buggy_e8r
```

后端服务对 registry 模型/策略返回做了用户态白名单字段过滤，避免 registry 内部 note 把旧模型名带到 API 默认返回。

未触发：

```text
provider refresh
provider publish
accepted latest switch
monitor config write
monitor scan
monitor alerts write
broker/order/quick-trade
paper apply/reset write
target-position / target_weight 交易语义
```

## 4. E2E / Network / Console 证据

新增 E2E：

```text
frontend/tests/e2e/tw-stock-phase-yz-productization-pending.mjs
```

运行方式：构建后使用无 watcher 的静态 dist 服务：

```text
python -m http.server 8765 --bind 127.0.0.1
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8765 node tests/e2e/tw-stock-phase-yz-productization-pending.mjs
```

产物目录：

```text
/tmp/quantdinger_tw_phase_yz3_e2e
```

产物：

```text
phase_yz3_pending.png
network_audit.json
console_audit.json
```

E2E 结果：

```text
forbidden_request_count = 0
monitor_config_write_count = 0
monitor_scan_post_count = 0
monitor_alerts_write_count = 0
broker_quick_trade_orders_request_count = 0
ops_provider_publish_refresh_accepted_latest_request_count = 0
paper_apply_write_count = 0
paper_reset_write_count = 0
phase_yz_write_count = 0
target_position_write_count = 0
console_errors = []
page_errors = []
```

说明：`corepack pnpm dev` 与 `corepack pnpm preview` 在当前机器因系统 watcher 上限失败：

```text
ENOSPC: System limit for number of file watchers reached
```

因此 E2E 改用已构建 `dist/` 的 `python -m http.server` 承载，测试仍覆盖真实构建产物、前端 DOM、mocked GET API、network audit 与 console audit。

## 5. 验收命令

已执行：

```text
python -m py_compile backend/app/services/phase_yz3_productization_status.py backend/app/routes/tw_stock.py backend/tests/test_phase_yz3_productization_status.py
```

结果：通过。

已执行：

```text
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz2r_execution_price_readiness.py backend/tests/test_phase_yz3_productization_status.py -q
```

结果：

```text
22 passed in 1.58s
```

已执行：

```text
node tests/unit/tw-stock-phase-yz-productization-check.mjs
```

结果：

```text
tw-stock-phase-yz-productization static checks passed
```

已执行：

```text
node tests/unit/tw-stock-paper-portfolio-panel-check.mjs
```

结果：

```text
tw-stock-paper-portfolio-panel static checks passed
```

已执行：

```text
corepack pnpm build
```

结果：通过，`vite build` 完成。

已执行：

```text
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8765 node tests/e2e/tw-stock-phase-yz-productization-pending.mjs
```

结果：通过，network audit 与 console audit 全部为 0。

## 6. 最终判定

```text
YZ clean productization API/frontend/paper/replay pending state：通过
execution price 当前状态：pending / execution_price_unavailable
paper apply pending 阻断：通过
旧模型/旧策略默认暴露：未发现
安全边界风险：未发现
```

当前唯一保留项仍是本地 2026-06-18 OHLC / next_open 尚不可用。该状态已按用户第一性原则产品化为 pending，并已阻断模拟账户写入动作。
