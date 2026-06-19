# Phase YZ3RR 前端 Clean Replay 默认请求收口修复执行报告

生成日期：2026-06-18

## 1. 执行结论

YZ3RR 已完成前端旧模型默认请求收口修复。

本阶段修复目标：

```text
readonlyReplayWindowForm 默认模型不再使用 e4_frozen_qlib_2023_2025_ltr
页面初始化不再在 replay window index 未就绪时发出旧模型 detail 请求
readonly replay window index/API 默认路径不再透出旧模型窗口
E2E 证明 readonly replay window 请求 URL 不含旧模型
```

当前真实后端 clean index 状态：

```text
index_window_count = 0
index_windows = []
old_model_in_index = false
old_model_detail_status = deprecated_model_id
clean_model_detail_status = no_audited_replay_artifact_for_window
```

说明：本地现有 d7 artifact 仍只有旧模型窗口。YZ3RR 在 API loader 层按 clean replay policy 过滤后，默认 index 返回空窗口；这比 fallback 到旧模型安全。后续生成 clean E4 replay artifact 后，index 会透出 clean window，前端会按 clean preset 请求 detail。

## 2. 修复文件列表

```text
backend/app/services/readonly_replay_window_index.py
backend/app/services/readonly_replay_window.py
backend/tests/test_tw_stock_readonly_replay_window_api.py
backend/tests/test_phase_yz0_clean_registry.py
frontend/src/views/tw-stock-monitor/index.vue
frontend/tests/unit/tw-stock-phase-yz-productization-check.mjs
frontend/tests/e2e/tw-stock-phase-yz-productization-pending.mjs
docs/tw_modular_daily_update_productization/PHASEYZ3RR_FRONTEND_CLEAN_REPLAY_DEFAULT_REPAIR_EXECUTION_REPORT_CN.md
```

## 3. 前端默认值修复

`readonlyReplayWindowForm.model_id` 已从旧模型：

```text
e4_frozen_qlib_2023_2025_ltr
```

改为 clean fallback：

```text
e4_frozen_qlib_2018_2022
```

静态检查确认：

```text
index.vue 不再包含 model_id: 'e4_frozen_qlib_2023_2025_ltr'
index.vue 包含 model_id: 'e4_frozen_qlib_2018_2022'
```

## 4. 初始化顺序修复

修复前：

```text
mounted / refreshAll 可能并行调用 loadReadonlyReplayWindowIndex() 与 loadReadonlyReplayWindow()
当 index 尚未返回时，detail 请求会使用表单旧默认模型
```

修复后：

```text
mounted 只调用 loadReadonlyReplayWindowIndex()
refreshAll 不再并行调用 loadReadonlyReplayWindow()
loadReadonlyReplayWindowIndex() 成功后，如果存在 clean preset，先 applyReadonlyReplayWindowPreset()，再 await loadReadonlyReplayWindow()
如果没有 clean preset，则不发 detail 请求，并显示“等待 clean E4 只读回放窗口索引。”
loadReadonlyReplayWindow() 在没有 selected preset 时直接 return
```

静态检查确认：

```text
mounted_old_sequence = false
refresh_old_sequence = false
```

## 5. 后端 Clean Index / Detail 收口

复核 policy：

```text
configs/tw_replay_window_policy.yaml default_model_id = e4_frozen_qlib_2018_2022
configs/tw_replay_window_policy.yaml default_strategy_rule = top50_exit_one_worst_sell
```

修复后：

```text
readonly replay window index loader 先按 clean ReplayWindowPolicy 过滤，再校验 entry
旧模型 e4_frozen_qlib_2023_2025_ltr 不再作为 index windows 返回
readonly replay window detail 对旧模型返回 deprecated_model_id
clean 模型如当前没有 indexed artifact，返回 no_audited_replay_artifact_for_window，不 fallback 到旧 artifact
```

真实摘要：

```text
index_window_count = 0
index_windows = []
old_model_in_index = False
old_model_detail_status = deprecated_model_id
clean_model_detail_status = no_audited_replay_artifact_for_window
```

## 6. E2E 请求 URL 审计

E2E mock `readonly-replay-window-index` 返回 clean preset：

```text
model_id = e4_frozen_qlib_2018_2022
strategy_rule = top50_exit_one_worst_sell
start = 2026-01-01
end = 2026-05-07
```

E2E 记录到的 readonly replay window detail 请求：

```text
GET /api/tw-stock/readonly-replay-window?model_id=e4_frozen_qlib_2018_2022&strategy_rule=top50_exit_one_worst_sell&start=2026-01-01&end=2026-05-07
GET /api/tw-stock/readonly-replay-window?model_id=e4_frozen_qlib_2018_2022&strategy_rule=top50_exit_one_worst_sell&start=2026-01-01&end=2026-05-07
```

E2E 断言通过：

```text
没有请求 URL 包含 e4_frozen_qlib_2023_2025_ltr
请求 URL 包含 clean E4 模型 e4_frozen_qlib_2018_2022
paper apply button disabled
paper apply POST count = 0
```

产物路径：

```text
/tmp/quantdinger_tw_phase_yz3rr_e2e/phase_yz3_pending.png
/tmp/quantdinger_tw_phase_yz3rr_e2e/network_audit.json
/tmp/quantdinger_tw_phase_yz3rr_e2e/console_audit.json
```

## 7. Network / Console Audit

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

## 8. 验收命令结果

已执行：

```text
python -m py_compile backend/app/services/readonly_replay_window_index.py backend/app/services/readonly_replay_window.py backend/tests/test_tw_stock_readonly_replay_window_api.py backend/app/services/phase_yz3_productization_status.py backend/app/routes/tw_stock.py backend/tests/test_phase_yz3_productization_status.py
```

结果：通过。

已执行：

```text
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz2r_execution_price_readiness.py backend/tests/test_phase_yz3_productization_status.py backend/tests/test_tw_stock_readonly_replay_window_api.py -q
```

结果：

```text
37 passed in 2.00s
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

E2E 静态服务：

```text
corepack pnpm build 已完成
静态服务目录 = frontend/dist
静态服务端口 = 8767
E2E base url = http://127.0.0.1:8767
```

已执行：

```text
cd frontend
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8767 TW_STOCK_PHASE_YZ3_E2E_DIR=/tmp/quantdinger_tw_phase_yz3rr_e2e node tests/e2e/tw-stock-phase-yz-productization-pending.mjs
```

结果：通过。

## 9. Paper Apply Pending 阻断

保持不变：

```text
paper_apply_allowed !== true 时禁用 YZ 产品化卡片应用按钮
PaperPortfolioPanel 中 phaseYzStatus.paper_apply_allowed === false 时禁用应用按钮
不打开 apply confirm
不发送 apply POST
```

E2E 结果：

```text
paper_apply_write_count = 0
paper_reset_write_count = 0
```

## 10. 安全边界结论

YZ3RR 未触发：

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

## 11. 最终判定

```text
前端旧模型默认请求收口：通过
readonlyReplayWindowForm clean fallback：通过
初始化顺序不再抢跑旧 detail 请求：通过
readonly replay window index 默认不透出旧模型：通过
旧模型 detail 请求拒绝：通过
E2E 无 e4_frozen_qlib_2023_2025_ltr 请求：通过
network / console audit：通过
paper apply pending 阻断：保持
```

YZ 路线可按最终收口标准提交：clean E4 产品化状态 API artifact 驱动，前端日期文案 API 驱动，前端默认模型/策略只来自 clean registry / clean replay policy，pending 时清晰展示并阻断模拟账户写入，无 forbidden write/network 请求。
