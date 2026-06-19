# Phase YZ3R 审查与 Phase YZ3RR 前端旧模型默认请求收口修复工作文档

生成日期：2026-06-18

## 1. YZ3R 审查结论

YZ3R 的动态日期产品化修复通过，但 YZ 路线暂不建议最终收口。

YZ3R 已完成：

```text
后端默认 signal_asof 不再硬编码 2026-06-17
前端 pending 文案不再硬编码 2026-06-18
非 2026-06-17 / 2026-06-18 fixture 覆盖通过
paper apply pending 阻断保持
安全边界通过
```

复跑结果：

```text
python -m py_compile 通过
pytest: 25 passed
前端 YZ3 静态检查通过
前端 PaperPortfolio 静态检查通过
corepack pnpm build 通过
E2E network audit forbidden_request_count = 0
console_errors = []
page_errors = []
```

但仍发现一个最终收口残留：

```text
frontend/src/views/tw-stock-monitor/index.vue
readonlyReplayWindowForm.model_id 仍默认 e4_frozen_qlib_2023_2025_ltr
mounted/refreshAll 会在 readonly replay window index/preset 未必已加载完成前调用 loadReadonlyReplayWindow()
可能发出一次旧模型 readonly replay window 默认请求
```

这不是 broker/order 安全风险，但违反 YZ 路线核心目标：

```text
前端/API 默认路径不得再暴露或消费旧模型 e4_frozen_qlib_2023_2025_ltr
默认用户态必须只走 clean E4 模型与生产策略
```

因此需要一个小修复：

```text
Phase YZ3RR：前端旧模型默认请求收口修复
```

## 2. YZ3RR 目标

YZ3RR 只修前端只读回放默认请求残留。

必须实现：

```text
readonlyReplayWindowForm 默认模型改为 clean E4 模型
页面初始化时不得在 replay window index/preset 未就绪前用旧模型请求 readonly replay window
readonly replay window 默认请求必须来自后端 clean index/preset 或 clean fallback
E2E 证明不会出现 e4_frozen_qlib_2023_2025_ltr 请求
静态检查证明前端默认路径不再包含旧模型默认值
```

不得做：

```text
重训模型
重跑模型信号
修改 YZ2/YZ2R/YZ3R artifact
改变 clean registry 可选集合
改变 execution_price_mode
放开 pending 下 paper apply
provider refresh/publish
accepted latest switch
monitor scan/write
broker/order/quick-trade
```

## 3. 当前问题定位

当前前端存在：

```text
frontend/src/views/tw-stock-monitor/index.vue

readonlyReplayWindowForm: {
  model_id: 'e4_frozen_qlib_2023_2025_ltr',
  strategy_rule: 'top50_exit_one_worst_sell',
  start: moment('2026-01-01', 'YYYY-MM-DD'),
  end: moment('2026-05-07', 'YYYY-MM-DD')
}
```

并且页面初始化存在：

```text
this.loadReadonlyReplayWindowIndex()
this.loadReadonlyReplayWindow()
```

`loadReadonlyReplayWindow()` 内部虽然会调用 `applyReadonlyReplayWindowPreset()`，但如果 index 尚未返回，preset 不存在，就会继续使用 `readonlyReplayWindowForm` 里的旧模型默认值。

因此用户打开页面时，网络层可能出现：

```text
GET /api/tw-stock/readonly-replay-window?model_id=e4_frozen_qlib_2023_2025_ltr&...
```

这会把 YZ 要淘汰的旧模型重新带回默认产品化路径。

## 4. 修复要求

### 4.1 前端默认值必须 clean

`readonlyReplayWindowForm.model_id` 不得再是：

```text
e4_frozen_qlib_2023_2025_ltr
```

允许的默认 fallback 只能是：

```text
e4_frozen_qlib_2018_2022
```

或如果 replay window index 已提供默认项，则使用 index/preset 的：

```text
preset.model_id
preset.strategy_rule
preset.start
preset.end
```

### 4.2 初始化顺序必须避免旧默认请求

推荐修法二选一：

方案 A：

```text
mounted / refreshAll 只调用 loadReadonlyReplayWindowIndex()
loadReadonlyReplayWindowIndex() 成功设置 preset 后，再显式调用 loadReadonlyReplayWindow()
```

方案 B：

```text
loadReadonlyReplayWindow() 在没有 readonlyReplayWindowSelectedPreset 且 index 尚未加载时直接 return
并显示“等待回放窗口索引”状态
```

无论选择哪种，必须保证：

```text
页面初始化不会用旧模型默认值发起请求
```

### 4.3 后端 index/policy 保持 clean

无需大改后端，但执行者必须复核：

```text
configs/tw_replay_window_policy.yaml default_model_id = e4_frozen_qlib_2018_2022
readonly replay window index 返回的 windows 不包含 e4_frozen_qlib_2023_2025_ltr
backend route 对旧 model_id 仍拒绝或不作为默认返回
```

如果发现 readonly replay window index 仍返回旧模型窗口，则必须同步修正 index/policy 读取逻辑或产物生成逻辑。

## 5. 前端测试要求

### 5.1 静态检查

更新或新增：

```text
frontend/tests/unit/tw-stock-phase-yz-productization-check.mjs
```

必须断言：

```text
index.vue 的 readonlyReplayWindowForm 默认值不包含 e4_frozen_qlib_2023_2025_ltr
index.vue 中不再存在 "model_id: 'e4_frozen_qlib_2023_2025_ltr'" 这类默认赋值
loadReadonlyReplayWindowIndex 与 loadReadonlyReplayWindow 的初始化顺序不会触发旧默认请求
phaseYZ pending 文案仍读取 execution_price_message
PaperPortfolioPanel applyDisabled 仍包含 phaseYZPaperBlocked
```

如果源码中仍有旧模型字符串仅作为测试 denylist 或错误提示，可以保留；但不得出现在：

```text
readonlyReplayWindowForm 默认值
API 请求参数默认值
前端用户可见默认选项
E2E mock 成功路径
```

### 5.2 E2E 网络断言

更新：

```text
frontend/tests/e2e/tw-stock-phase-yz-productization-pending.mjs
```

必须记录所有 `/api/tw-stock/readonly-replay-window` 请求，并断言：

```text
没有请求 URL 包含 e4_frozen_qlib_2023_2025_ltr
请求 URL 包含 clean E4 模型，或在 index 未加载前没有发出 replay window detail 请求
forbidden_request_count = 0
paper_apply_write_count = 0
console_errors = []
page_errors = []
```

建议 E2E mock `readonly-replay-window-index` 返回 clean preset：

```text
model_id = e4_frozen_qlib_2018_2022
strategy_rule = top50_exit_one_worst_sell
start = 2026-01-01
end = 2026-05-07
```

然后断言 detail 请求使用同一 clean preset。

## 6. 后端测试要求

至少复跑：

```text
python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz3_productization_status.py -q
```

如果现有 `test_tw_stock_readonly_replay_window_api.py` 仍以 `e4_frozen_qlib_2023_2025_ltr` 作为成功路径模型，应同步修正为 clean E4 模型，或明确旧模型测试只验证被拒绝，不得作为成功默认路径。

## 7. 验收命令

执行者至少需要提供：

```text
python -m py_compile backend/app/services/phase_yz3_productization_status.py backend/app/routes/tw_stock.py backend/tests/test_phase_yz3_productization_status.py
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz2r_execution_price_readiness.py backend/tests/test_phase_yz3_productization_status.py backend/tests/test_tw_stock_readonly_replay_window_api.py -q
cd frontend && node tests/unit/tw-stock-phase-yz-productization-check.mjs
cd frontend && node tests/unit/tw-stock-paper-portfolio-panel-check.mjs
cd frontend && corepack pnpm build
<YZ3RR frontend e2e command>
```

如果 E2E 仍使用静态 dist server，报告必须写清楚：

```text
corepack pnpm build 已完成
静态服务目录 = frontend/dist
静态服务端口
E2E base url
network_audit.json 路径
console_audit.json 路径
```

## 8. 安全边界

YZ3RR 禁止触发：

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
GET /api/tw-stock/readonly-replay-window-index
GET /api/tw-stock/readonly-replay-window
GET /api/tw-stock/phase-yz/productization-status
前端只读展示
静态检查
mocked E2E GET
```

## 9. 执行报告路径

执行者完成后写：

```text
docs/tw_modular_daily_update_productization/PHASEYZ3RR_FRONTEND_CLEAN_REPLAY_DEFAULT_REPAIR_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
修复文件列表
readonlyReplayWindowForm 默认值修复说明
初始化顺序修复说明
readonly replay window index/preset clean 证据
E2E 请求 URL 审计，证明无 e4_frozen_qlib_2023_2025_ltr 默认请求
network audit
console audit
py_compile / pytest / frontend static check / build 结果
paper apply pending 阻断是否保持
安全边界结论
```

## 10. YZ 最终收口标准

YZ3RR 通过后，YZ 路线可以收口，标准为：

```text
clean E4 产品化状态 API 默认 artifact 驱动
前端日期文案 artifact/API 驱动
前端默认模型/策略只来自 clean registry / clean replay index
没有 e4_frozen_qlib_2023_2025_ltr 默认请求
execution_price_mode = next_open
execution_price pending 时清晰展示并阻断 paper apply
network audit 无 forbidden write
console/page errors 为 0
```
