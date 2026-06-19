# Phase YZ2R 审查与 Phase YZ3 产品化 E2E 工作文档

生成日期：2026-06-18

## 1. 审查对象

本次审查对象：

```text
docs/tw_modular_daily_update_productization/PHASEYZ2R_EXECUTION_PRICE_READINESS_REPAIR_EXECUTION_REPORT_CN.md
scripts/build_phase_yz2r_execution_price_readiness.py
backend/tests/test_phase_yz2r_execution_price_readiness.py
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17/manifest.json
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17/source_trace.json
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17/forbidden_action_audit.json
```

补充业务口径：

```text
2026-06-18 当前尚未收盘。
如果 blocked 的唯一原因是 2026-06-18 next_open / next_close 行情暂不可得，则不作为 YZ3 前置硬阻断。
```

## 2. 复跑结果

已复跑：

```text
python -m py_compile scripts/build_phase_yz2r_execution_price_readiness.py backend/tests/test_phase_yz2r_execution_price_readiness.py
python scripts/build_phase_yz2r_execution_price_readiness.py --signal-asof 2026-06-17 --json
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz2r_execution_price_readiness.py -q
```

结果：

```text
py_compile 通过
YZ2R artifact 可生成
status = execution_price_unavailable
next_open_available_count = 0
missing_next_open_count = 50
recommended_gate = blocked_before_yz3
17 passed
```

说明：构建命令在默认 sandbox 中曾触发 `bwrap: loopback: Failed RTM_NEWADDR`，非沙箱重跑后通过并生成同一结果。

## 3. YZ2R 审查结论

YZ2R 执行质量通过，可以放行进入 YZ3。

放行原因不是 execution price 已可用，而是本次 blocked 原因清晰、可解释、边界正确：

```text
signal_asof = 2026-06-17
target_next_trading_day = 2026-06-18
calendar_next_trading_day = null
calendar_contains_target_next_day = false
next_open_available_count = 0
next_close_available_count = 0
close_on_or_before_signal_asof_available_count = 50
missing_next_open_count = 50
missing_next_close_count = 50
status = execution_price_unavailable
```

当前缺口是本地 calendar 与本地 OHLC 尚无 2026-06-18 数据；结合 2026-06-18 尚未收盘，这属于预期的暂不可得状态，不应阻断 YZ3 做产品化 pending/block 态接入。

## 4. 通过项

### 4.1 没有错误 fallback

YZ2R 明确证明：

```text
no_fallback_to_next_close = true
no_fallback_to_signal_close = true
fallback_to_next_close = false
fallback_to_signal_close = false
open_equals_signal_close_count = 0
manual_or_synthetic_ohlc = false
```

这点是本阶段最关键的通过项。执行者没有用 signal close 冒充 next_open，也没有在 next_open 缺失时退到 next_close。

### 4.2 数据来源可追踪

YZ2R 只读取本地价格源：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
```

source trace 记录了样本文件 sha256，并明确：

```text
local_csv_scan_found_2026_06_18 = false
external_network_used = false
provider_refresh_triggered = false
provider_publish_triggered = false
accepted_latest_switch_triggered = false
blocked_reason = local_2026_06_18_ohlc_not_found
```

### 4.3 安全边界通过

forbidden action audit 全部为 false：

```text
training = false
tuning = false
network_provider_fetch = false
provider_refresh = false
provider_publish = false
accepted_latest_switch = false
monitor_write = false
monitor_scan = false
broker_order = false
quick_trade = false
paper_apply_reset_write = false
frontend_change = false
```

本阶段没有触发 broker / order / quick-trade / accepted latest switch / provider publish / monitor 写路径。

### 4.4 模型链路未被污染

测试确认：

```text
Model A = e4_frozen_qlib_2018_2022, row_count = 150
Model B = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025, row_count = 50
```

YZ2R 没有重训、调参、换策略或重选模型。

## 5. 保留问题

### 5.1 YZ2R 不能证明 2026-06-18 execution price 已就绪

当前仍然是：

```text
execution_price_readiness.status = execution_price_unavailable
next_open_available_count = 0
missing_next_open_count = 50
```

因此 YZ3 不得把 replay / paper apply 当成可成交结果展示，不得计算基于 2026-06-18 next_open 的已实现收益，不得给用户“已可执行”的暗示。

### 5.2 YZ2R 脚本存在阶段性硬编码日期

`scripts/build_phase_yz2r_execution_price_readiness.py` 中 `TARGET_NEXT_DAY = "2026-06-18"` 对本轮 2026-06-17 信号审查可接受，但不得进入长期产品化链路。

YZ3 必须把 next trading day 改为由以下输入推导：

```text
signal_asof
trading calendar
provider/qlib accepted latest calendar
```

不得继续在 daily orchestrator / API / frontend 中硬编码 2026-06-18。

## 6. 审查判定

判定：

```text
YZ2R 通过
允许进入 YZ3
```

但这是带条件放行：

```text
允许 YZ3 接 API / frontend / paper / replay 的产品化流程
允许 YZ3 展示 execution_price_unavailable 的用户态
不允许 YZ3 在 next_open 缺失时执行 replay 成交、paper apply 成交或收益归因
不允许 fallback 到 next_close 或 signal_close
不要求等 2026-06-18 收盘数据才能开始 YZ3
```

## 7. Phase YZ3 目标

YZ3 目标是把 YZ0/YZ1/YZ2/YZ2R 的干净链路接入产品化用户入口，完成 API、前端、replay、paper portfolio 的 E2E 收口。

用户第一性原则：

```text
简单：用户只看到两个产品化模型和干净策略，不看到 P3/O4/fresh/bridge/origin 等历史实验项。
准确：明确当前信号日期、成交价格口径、数据是否已可用。
实用：能直接看当前策略候选、paper 预览和是否可应用。
清晰：如果 2026-06-18 数据暂不可用，明确提示等待行情数据，而不是报错或沉默。
```

## 8. YZ3 必须接入的产品化对象

模型只允许：

```text
Model A:
e4_frozen_qlib_2018_2022

Model B:
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
```

策略只允许 clean registry 中的 production_selectable 策略。

不得在前端/API 默认路径出现：

```text
origin
original
P3
O4
fresh qlib adaptive
fresh qlib 2025 LTR
bridge
e4_frozen_qlib_2023_2025_ltr
buggy_e8r 裸名
历史 replay artifact 自动扫描出来的旧模型/旧策略
```

`buggy_e8r` 如仍需保留，只能作为 research_only，必须中性命名，不得默认展示，不得作为生产策略证据。

## 9. YZ3 Execution Price 合同

YZ3 默认成交口径：

```text
execution_price_mode = next_open
```

如果读取 YZ2R readiness 后发现：

```text
status = execution_price_unavailable
```

则 API 与前端必须返回/展示 pending 状态：

```text
成交口径：次一交易日开盘价
当前 2026-06-18 行情暂不可用，等待下一轮数据更新
策略信号已生成，但暂不能进行基于 next_open 的成交回放或模拟应用
```

此时必须禁用或阻断：

```text
基于 next_open 的 replay realized return
paper apply
任何把本轮策略写入模拟账户的成交动作
```

允许展示：

```text
Model A / Model B 当日研究排序
策略候选预览
当前持仓与候选差异
execution price pending 原因
下一轮数据更新后可重新检查的入口
```

禁止：

```text
用 next_close 替代 next_open
用 signal close 替代 next_open
用空价格、0、上一日价格、手工价格模拟成交
把 pending 状态展示成成功
```

## 10. YZ3 API 要求

后端必须提供或修复只读 API，使前端能一次性拿到：

```text
clean registry 可选模型/策略
latest strict E4 signal_asof
Model A artifact 摘要
Model B artifact 摘要
策略决策预览
execution_price_mode
execution_price_readiness.status
execution_price_readiness.blocked_reason
paper portfolio 当前状态
paper apply 是否允许
```

推荐返回结构必须包含：

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
paper_apply_allowed
paper_apply_blocked_reason
latest_artifacts{}
safety_flags{}
```

当 execution price pending 时：

```text
ok = true
execution_price_status = execution_price_unavailable
paper_apply_allowed = false
paper_apply_blocked_reason = next_open_unavailable
```

不得用 HTTP 500 表示正常的数据暂不可得状态。

## 11. YZ3 前端要求

前端 `/tw-stock-monitor` 必须做到：

```text
默认进入 clean E4 产品化视图
模型列表只展示 Model A / Model B
策略列表只展示 production_selectable
显示 signal_asof
显示成交口径 next_open
显示 execution price 状态
pending 时禁用应用按钮
pending 时给出清楚、短句提示
```

用户态文案建议：

```text
成交口径：次一交易日开盘价
2026-06-18 行情暂不可用，等待下一轮数据更新
策略信号已生成，模拟应用将在成交价可用后开放
```

不得显示：

```text
Python traceback
raw JSON
内部 artifact 路径作为主要信息
旧模型/旧策略
“失败”“异常”这类误导用户的数据暂不可得文案
```

## 12. Paper Portfolio 要求

YZ3 必须把 X 路线 paper portfolio 与 YZ clean registry 对齐：

```text
paper latest decision 读取 YZ clean latest decision artifact
默认模型/策略来自 clean registry
pending 时 paper apply 按钮禁用
apply/reset 仍只允许写 qd_tw_sim_* 模拟账户表
不得触发 broker/order/quick-trade/target-position
```

如果 execution price 已可用，paper apply 才允许基于明确的 next_open price contract 执行模拟账户更新。

如果 execution price 暂不可用，paper preview 可以展示“将买/将卖/待调整”的研究预览，但不得写账户。

## 13. Replay 要求

YZ3 可以接 replay query 与 replay window，但必须区分：

```text
historical readonly replay
current signal executable replay
```

对当前 `2026-06-17 -> 2026-06-18` 信号：

```text
next_open 不可用时，不得展示 realized return
不得把 current day pending 混入历史收益表
```

历史 replay 如使用已有完整历史价格，可以继续只读展示，但默认模型/策略必须来自 clean registry。

## 14. 安全边界

YZ3 禁止触发：

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
```

允许：

```text
GET /api/tw-stock/**
只读 registry/status/context API
paper-only preview
在 price ready 且用户点击后写 qd_tw_sim_* 模拟账户表
```

前端 E2E network audit 必须证明：

```text
forbidden_request_count = 0
monitor_config_write_count = 0
monitor_scan_post_count = 0
monitor_alerts_write_count = 0
broker/order/quick-trade request = 0
provider publish/refresh/accepted switch request = 0
```

## 15. YZ3 验收命令

执行者至少需要提供：

```text
python -m py_compile <changed python files>
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz2r_execution_price_readiness.py <new yz3 tests> -q
corepack pnpm build
<frontend e2e command>
```

如果 `corepack pnpm build` 或 E2E 因环境限制无法运行，执行报告必须说明具体失败原因，并提供替代静态检查与截图/网络审计证据。

## 16. YZ3 必须产出的证据

执行报告必须包含：

```text
clean registry API 返回摘要
前端模型/策略选项截图或 DOM 检查摘要
execution_price_unavailable 用户态截图或文本证据
paper apply disabled/block 证据
network audit
console audit
backend pytest 结果
frontend build / e2e 结果
```

若 2026-06-18 数据在 YZ3 执行期间变为可用，执行者可以重新生成 YZ2R readiness，并额外证明：

```text
status = pass
next_open_available_count = 50
missing_next_open_count = 0
paper_apply_allowed = true
```

但这不是进入 YZ3 的前置条件。

## 17. YZ3 执行报告路径

执行者完成后写：

```text
docs/tw_modular_daily_update_productization/PHASEYZ3_PRODUCTIZATION_E2E_EXECUTION_REPORT_CN.md
```

报告必须明确最终结论：

```text
YZ clean productization API/frontend/paper/replay 是否通过
execution price 当前是 ready 还是 pending
如果 pending，是否已按用户第一性原则正确展示并阻断写账户动作
是否仍暴露旧模型/旧策略
是否存在安全边界风险
```

## 18. YZ 路线收口标准

YZ3 后是否可以收口，取决于：

```text
两个 E4 模型链路干净
生产策略注册表干净
API 默认值干净
前端用户态简单、准确、实用、清晰
paper portfolio 不再默认旧链路
execution_price pending/ready 状态表达正确
无 forbidden write/network request
```

只要唯一未完成项仍是“2026-06-18 当天尚未收盘导致 next_open/next_close 暂不可得”，且 YZ3 已正确把它产品化为 pending 状态并禁用 paper apply，则 YZ 路线可以按“功能收口、成交价等待行情更新”的口径提交最终验收。
