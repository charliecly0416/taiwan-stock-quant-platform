# Phase YZ3 审查与 Phase YZ3R 动态日期产品化修复工作文档

生成日期：2026-06-18

## 1. YZ3 审查结论

YZ3 方向正确，安全边界通过，但暂不建议直接收口。需要先做一个小修复阶段：

```text
Phase YZ3R：动态日期产品化修复
```

YZ3 已完成：

```text
clean E4 产品化状态 API
前端 YZ Clean E4 产品化卡片
execution_price_unavailable pending 展示
paper apply pending 阻断
network / console audit 零 forbidden request
```

但 YZ3 仍有产品化收口前必须修的硬编码问题：

```text
后端默认 signal_asof 仍硬编码 2026-06-17
前端 pending 文案仍硬编码 2026-06-18
测试只覆盖当前固定日期，未证明明天/后天会自动随 artifact 变化
```

这在本轮 2026-06-17 信号、2026-06-18 尚未收盘的语境下是正确展示；但 YZ3 是产品化入口，不能把具体日期常量写进默认 API 和用户态文案。否则后续每日自动链路更新后，前端仍可能显示旧日期，违背用户第一性原则。

## 2. 已复核证据

审查对象：

```text
docs/tw_modular_daily_update_productization/PHASEYZ3_PRODUCTIZATION_E2E_EXECUTION_REPORT_CN.md
backend/app/services/phase_yz3_productization_status.py
backend/app/routes/tw_stock.py
backend/tests/test_phase_yz3_productization_status.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue
frontend/tests/e2e/tw-stock-phase-yz-productization-pending.mjs
frontend/tests/unit/tw-stock-phase-yz-productization-check.mjs
/tmp/quantdinger_tw_phase_yz3_e2e/network_audit.json
/tmp/quantdinger_tw_phase_yz3_e2e/console_audit.json
```

已复跑：

```text
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz2r_execution_price_readiness.py backend/tests/test_phase_yz3_productization_status.py -q
```

结果：

```text
22 passed
```

已复跑：

```text
cd frontend
node tests/unit/tw-stock-phase-yz-productization-check.mjs
corepack pnpm build
```

结果：

```text
前端静态检查通过
vite build 通过
```

直接调用 YZ3 status service 得到：

```text
signal_asof = 2026-06-17
selected_model_id = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
selected_strategy_rule_id = top50_exit_one_worst_sell
execution_price_mode = next_open
execution_price_status = execution_price_unavailable
paper_apply_allowed = false
paper_apply_blocked_reason = next_open_unavailable
```

## 3. YZ3 通过项

### 3.1 安全边界通过

YZ3 产品化 API 是 GET-only：

```text
GET /api/tw-stock/phase-yz/productization-status
```

未发现：

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

E2E network audit：

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

### 3.2 clean registry 暴露正确

API 只返回：

```text
e4_frozen_qlib_2018_2022
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
top50_exit_one_worst_sell
```

未在默认产品化 API 返回中发现：

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

### 3.3 pending 阻断正确

当：

```text
execution_price_status = execution_price_unavailable
paper_apply_allowed = false
```

前端：

```text
显示 pending 提示
禁用 YZ 产品化卡片应用按钮
向 PaperPortfolioPanel 传入 phaseYzStatus
禁用 PaperPortfolioPanel 的应用按钮
不打开 apply confirm
不发送 paper apply POST
```

## 4. YZ3 阻塞项

### 4.1 后端默认日期硬编码

当前存在：

```text
backend/app/services/phase_yz3_productization_status.py
DEFAULT_SIGNAL_ASOF = "2026-06-17"

backend/app/routes/tw_stock.py
request.args.get(...) or "2026-06-17"
```

问题：

```text
产品化默认 API 不能永远指向 2026-06-17
每日自动链路更新后，用户默认打开页面应看到 latest clean YZ artifact
如果 latest 变成 2026-06-18 / 2026-06-19，API 必须自动切换
```

### 4.2 前端文案硬编码 2026-06-18

当前前端 pending alert 写死：

```text
2026-06-18 行情暂不可用
```

问题：

```text
用户态日期必须来自 API 的 execution_price_message 或 execution_price_readiness.target_next_trading_day
不能在 Vue 模板中硬编码具体交易日
```

### 4.3 测试未覆盖日期变化

现有测试只覆盖当前固定日期：

```text
signal_asof = 2026-06-17
target_next_trading_day = 2026-06-18
```

YZ3R 必须新增非 2026-06-17 fixture 或临时测试目录，证明：

```text
latest signal_asof 可自动推导
target_next_trading_day 可随 readiness artifact 变化
前端文案读取 API，不写死 2026-06-18
```

## 5. YZ3R 目标

YZ3R 只做动态日期产品化修复。

必须实现：

```text
后端默认 signal_asof 从 latest clean YZ artifact 推导
target_next_trading_day 从 execution price readiness artifact 推导
execution_price_message 后端统一生成
前端 pending 文案完全读取 API message，不写死日期
测试覆盖非固定日期场景
修正执行报告里的前端检查命令路径
```

不得做：

```text
重训模型
重跑模型信号
重新选择策略
改 registry 可选集合
改 paper apply 业务逻辑
放开 pending 下的 paper apply
provider refresh/publish
accepted latest switch
monitor scan/write
broker/order/quick-trade
```

## 6. 后端修复要求

### 6.1 latest signal_asof 推导

新增或修改 helper，例如：

```text
resolve_latest_yz_signal_asof()
```

推导顺序建议：

```text
1. 如果请求显式传入 signal_asof / signalAsOf，则使用请求值
2. 否则扫描 data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/*/
3. 只接受同时存在 model_a/manifest.json 与 model_b_yz2/manifest.json 或 model_b/manifest.json 的日期
4. 优先选择日期字符串最大的 YYYY-MM-DD
5. 如果没有可用日期，返回 ok=false 或明确 unavailable，不得 fallback 到旧模型
```

注意：

```text
不得硬编码 2026-06-17
不得从历史 replay matrix 或旧 U/V/X artifact 推导默认日期
不得因为找不到 YZ artifact 而 fallback 到 e4_frozen_qlib_2023_2025_ltr
```

### 6.2 readiness 日期读取

对于选定 `signal_asof`，读取：

```text
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/{signal_asof}/manifest.json
```

并从 manifest 读取：

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

如果 readiness artifact 不存在：

```text
execution_price_status = execution_price_unavailable
paper_apply_allowed = false
paper_apply_blocked_reason = execution_price_readiness_missing
execution_price_message = 成交口径：次一交易日开盘价。成交价可用性尚未生成，等待下一轮数据更新。
```

不得用固定 `2026-06-18` 兜底。

### 6.3 API 返回合同

`GET /api/tw-stock/phase-yz/productization-status` 必须返回：

```text
ok
signal_asof
models[]
production_strategies[]
selected_model_id
selected_strategy_rule_id
execution_price_mode
execution_price_status
execution_price_message
execution_price_readiness.target_next_trading_day
paper_apply_allowed
paper_apply_blocked_reason
latest_artifacts
safety_flags
```

当 pending：

```text
ok = true
execution_price_status = execution_price_unavailable
paper_apply_allowed = false
paper_apply_blocked_reason = next_open_unavailable 或 execution_price_readiness_missing
```

不得返回 HTTP 500 表示正常的数据暂不可得。

## 7. 前端修复要求

### 7.1 pending alert 改为动态文案

前端不得写死：

```text
2026-06-18 行情暂不可用
```

必须使用：

```text
phaseYZProductizationPayload.execution_price_message
```

如果 message 缺失，则用无具体日期兜底：

```text
成交口径：次一交易日开盘价。行情暂不可用，等待下一轮数据更新。
```

### 7.2 日期展示来自 payload

前端展示：

```text
signal_asof
execution_price_mode
execution_price_readiness.target_next_trading_day
paper_apply_blocked_reason
```

必须全部来自 API payload。

### 7.3 禁用逻辑保持不变

保留：

```text
paper_apply_allowed !== true 时禁用 YZ 卡片应用按钮
PaperPortfolioPanel 中 phaseYzStatus.paper_apply_allowed === false 时禁用应用按钮
不打开 apply confirm
不发送 apply POST
```

不得因为修日期文案而放开 pending 下的写账户路径。

## 8. 测试要求

### 8.1 后端单测

新增测试必须覆盖：

```text
默认不传 signal_asof 时，会选择 latest YZ artifact 日期
显式传 signal_asof 时，会读取指定日期
target_next_trading_day 从 readiness manifest 读取
readiness 缺失时返回 pending/unavailable，不抛 500
payload 序列化中不出现旧模型/旧策略
route 仍然 GET-only，POST/PUT/PATCH/DELETE 返回 405
```

必须新增一个非 2026-06-17 的临时 fixture 测试，例如：

```text
2026-06-19 signal_asof
2026-06-22 target_next_trading_day
```

测试可以使用 `tmp_path` 或 monkeypatch root/path 常量，但不得污染真实 artifact。

### 8.2 前端静态检查

静态检查必须证明：

```text
frontend/src/views/tw-stock-monitor/index.vue 中不再包含硬编码 "2026-06-18 行情暂不可用"
pending alert 读取 execution_price_message
PaperPortfolioPanel 仍包含 phaseYZPaperBlocked
applyDisabled 仍包含 phaseYZPaperBlocked
```

注意执行命令必须写清楚 cwd：

```text
cd frontend
node tests/unit/tw-stock-phase-yz-productization-check.mjs
```

或从仓库根目录运行：

```text
node frontend/tests/unit/tw-stock-phase-yz-productization-check.mjs
```

二者必须与脚本相对路径一致；不要在报告里写不存在的 `tests/unit/...` 根路径。

### 8.3 E2E

E2E 必须覆盖动态日期：

```text
mock API 返回 signal_asof = 2026-06-19
mock API 返回 target_next_trading_day = 2026-06-22
mock API 返回 execution_price_message 包含 2026-06-22
页面显示 2026-06-22
页面不显示 2026-06-18
paper apply button disabled
paper apply POST count = 0
network forbidden count = 0
console/page errors = 0
```

## 9. 验收命令

执行者至少需要提供：

```text
python -m py_compile backend/app/services/phase_yz3_productization_status.py backend/app/routes/tw_stock.py backend/tests/test_phase_yz3_productization_status.py
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz2r_execution_price_readiness.py backend/tests/test_phase_yz3_productization_status.py -q
cd frontend && node tests/unit/tw-stock-phase-yz-productization-check.mjs
cd frontend && corepack pnpm build
<YZ3R frontend e2e command>
```

如果 `corepack pnpm dev` 或 preview 因 watcher 限制失败，可以继续使用静态 dist server，但报告必须写清楚：

```text
构建产物来自 corepack pnpm build
静态服务命令
E2E base url
network_audit.json 路径
console_audit.json 路径
```

## 10. 安全边界

YZ3R 禁止触发：

```text
POST /api/tw-stock/monitor/config
POST /api/tw-stock/monitor/scan
POST /api/tw-stock/monitor/scan-all
POST /api/tw-stock/monitor/alerts
PUT/PATCH/DELETE /api/tw-stock/monitor/alerts/*
POST /api/tw-stock/quant/ops/** publish/refresh/provider/accepted
POST /api/quick-trade/**
/api/broker/**
真实 order
target-position
target_weight 交易语义
paper apply/reset write in pending state
```

允许：

```text
GET /api/tw-stock/**
只读状态读取
前端只读展示
静态检查
E2E mock GET
```

## 11. 执行报告路径

执行者完成后写：

```text
docs/tw_modular_daily_update_productization/PHASEYZ3R_DYNAMIC_DATE_PRODUCTIZATION_REPAIR_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
修复文件列表
latest signal_asof 推导规则
非 2026-06-17 fixture 测试证据
前端不再硬编码 2026-06-18 的证据
E2E 页面动态日期证据
network audit
console audit
py_compile / pytest / frontend static check / build 结果
是否仍存在 pending 状态
paper apply 是否仍被阻断
安全边界结论
```

## 12. YZ3R 收口标准

YZ3R 通过后，YZ 路线可以按以下口径提交最终验收：

```text
clean E4 产品化链路已收口
前端/API/paper/replay 默认只暴露两个 E4 模型和生产策略
execution_price_mode 固化为 next_open
execution price ready 时允许模拟应用
execution price pending 时清晰展示并阻断模拟账户写入
日期完全由 artifact/API 驱动，不再硬编码 2026-06-17 / 2026-06-18
无 provider publish/refresh、accepted latest switch、monitor、broker/order/quick-trade 风险
```
