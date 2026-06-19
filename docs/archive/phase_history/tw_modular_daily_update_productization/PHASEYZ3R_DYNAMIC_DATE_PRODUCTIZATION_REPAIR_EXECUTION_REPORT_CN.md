# Phase YZ3R 动态日期产品化修复执行报告

生成日期：2026-06-18

## 1. 执行结论

YZ3R 已完成动态日期产品化修复。

本阶段修复了 YZ3 的两个收口阻塞点：

```text
后端默认 signal_asof 不再硬编码 2026-06-17
前端 pending 文案不再硬编码 2026-06-18
```

当前真实本地 artifact 的 latest 仍为：

```text
latest = 2026-06-17
signal_asof = 2026-06-17
execution_price_mode = next_open
execution_price_status = execution_price_unavailable
target_next_trading_day = 2026-06-18
paper_apply_allowed = false
paper_apply_blocked_reason = next_open_unavailable
```

这是由当前本地 YZ artifact 决定，不再由代码常量决定。新增临时 fixture 已证明当 latest 变为 `2026-06-19`、target next day 变为 `2026-06-22` 时，API 与前端会自动展示新日期。

## 2. 修复文件列表

```text
backend/app/services/phase_yz3_productization_status.py
backend/app/routes/tw_stock.py
backend/tests/test_phase_yz3_productization_status.py
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue
frontend/tests/unit/tw-stock-phase-yz-productization-check.mjs
frontend/tests/e2e/tw-stock-phase-yz-productization-pending.mjs
docs/tw_modular_daily_update_productization/PHASEYZ3R_DYNAMIC_DATE_PRODUCTIZATION_REPAIR_EXECUTION_REPORT_CN.md
```

## 3. 后端动态日期规则

新增/修复逻辑：

```text
resolve_latest_yz_signal_asof(signal_asof=None)
```

默认推导规则：

```text
1. 如果请求显式传入 signal_asof / signalAsOf，则使用请求值
2. 否则扫描 data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/*/
3. 只接受同时存在 model_a/manifest.json 与 model_b_yz2/manifest.json 或 model_b/manifest.json 的日期
4. 选择日期字符串最大的 YYYY-MM-DD
5. 如果没有 clean YZ artifact，则返回 ok=false / pending，不 fallback 到旧模型
```

readiness 读取规则：

```text
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/{signal_asof}/manifest.json
```

读取字段：

```text
target_next_trading_day
status
next_open_available_count
next_close_available_count
missing_next_open_count
missing_next_close_count
no_fallback_to_next_close
no_fallback_to_signal_close
```

如果 readiness artifact 缺失：

```text
execution_price_status = execution_price_unavailable
paper_apply_allowed = false
paper_apply_blocked_reason = execution_price_readiness_missing
execution_price_message = 成交口径：次一交易日开盘价。成交价可用性尚未生成，等待下一轮数据更新。
```

不再使用固定 `2026-06-18` 兜底。

## 4. 非固定日期测试证据

后端新增临时 fixture：

```text
signal_asof = 2026-06-19
target_next_trading_day = 2026-06-22
```

覆盖结果：

```text
默认不传 signal_asof 时，选择 latest clean YZ artifact = 2026-06-19
显式传 2026-06-17 时，读取指定日期
readiness target_next_trading_day 从 manifest 读取为 2026-06-22
readiness 缺失时返回 pending/unavailable，不抛 500
payload 不暴露旧模型/旧策略
route 保持 GET-only，POST/PUT/PATCH/DELETE 返回 405
```

## 5. 前端动态文案修复

前端 pending alert 从：

```text
硬编码 2026-06-18 行情暂不可用
```

改为读取：

```text
phaseYZProductizationPayload.execution_price_message
```

兜底文案无具体日期：

```text
成交口径：次一交易日开盘价。行情暂不可用，等待下一轮数据更新。
```

前端展示字段来自 payload：

```text
signal_asof
execution_price_mode
execution_price_readiness.target_next_trading_day
paper_apply_blocked_reason
```

静态检查已证明：

```text
frontend/src/views/tw-stock-monitor/index.vue 不再包含 "2026-06-18 行情暂不可用"
pending alert 使用 :message="phaseYZExecutionPriceMessage"
PaperPortfolioPanel 仍包含 phaseYZPaperBlocked
applyDisabled 仍包含 phaseYZPaperBlocked
```

## 6. E2E 动态日期证据

E2E mock API 返回：

```text
signal_asof = 2026-06-19
target_next_trading_day = 2026-06-22
execution_price_message 包含 2026-06-22 行情暂不可用
paper_apply_allowed = false
paper_apply_blocked_reason = next_open_unavailable
```

页面断言：

```text
页面显示 2026-06-22 行情暂不可用
页面不显示 2026-06-18 行情暂不可用
YZ 产品化应用按钮 disabled
PaperPortfolioPanel apply button disabled
paper apply POST count = 0
```

E2E 命令：

```text
cd frontend
python -m http.server 8766 --bind 127.0.0.1  # cwd = frontend/dist
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8766 TW_STOCK_PHASE_YZ3_E2E_DIR=/tmp/quantdinger_tw_phase_yz3r_e2e node tests/e2e/tw-stock-phase-yz-productization-pending.mjs
```

产物：

```text
/tmp/quantdinger_tw_phase_yz3r_e2e/phase_yz3_pending.png
/tmp/quantdinger_tw_phase_yz3r_e2e/network_audit.json
/tmp/quantdinger_tw_phase_yz3r_e2e/console_audit.json
```

network audit：

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
```

console audit：

```text
console_errors = []
page_errors = []
```

## 7. 验收命令结果

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
25 passed in 1.72s
```

已执行：

```text
cd frontend && node tests/unit/tw-stock-phase-yz-productization-check.mjs
```

结果：

```text
tw-stock-phase-yz-productization static checks passed
```

已执行：

```text
cd frontend && node tests/unit/tw-stock-paper-portfolio-panel-check.mjs
```

结果：

```text
tw-stock-paper-portfolio-panel static checks passed
```

已执行：

```text
cd frontend && corepack pnpm build
```

结果：通过，`vite build` 完成。

已执行：

```text
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8766 TW_STOCK_PHASE_YZ3_E2E_DIR=/tmp/quantdinger_tw_phase_yz3r_e2e node tests/e2e/tw-stock-phase-yz-productization-pending.mjs
```

结果：通过。

## 8. 安全边界结论

YZ3R 未触发：

```text
provider refresh
provider publish
accepted latest switch
monitor config write
monitor scan
monitor alerts write
broker/order/quick-trade
paper apply/reset write in pending state
target-position / target_weight 交易语义
```

YZ3R 只做：

```text
GET 状态读取
前端只读展示
静态检查
mocked E2E GET
```

## 9. 最终判定

```text
clean E4 产品化动态日期修复：通过
后端默认 signal_asof artifact 驱动：通过
前端 pending 日期 API 驱动：通过
非 2026-06-17 / 2026-06-18 测试覆盖：通过
execution_price_mode = next_open：保持
execution price 当前状态：pending / execution_price_unavailable
paper apply pending 阻断：保持
旧模型/旧策略默认暴露：未发现
安全边界风险：未发现
```

YZ 路线可按以下口径收口：clean E4 产品化链路已收口；当前成交价仍等待行情更新，pending 状态已清晰展示并阻断模拟账户写入。
