# Phase YZ Strict E4 产品化收口路线总结报告

生成日期：2026-06-18

## 1. 总结结论

Phase YZ 路线已完成收口，可以进入统筹节点最终审查。

当前结论不是“还能继续修”，而是：

```text
clean E4 产品化链路已建立
默认模型/策略已从旧实验链路收敛到 clean registry
Model A / Model B strict E4 当前信号可生成
orthogonal LTR 数据包已补齐 strict E4 top50 覆盖
execution_price_mode 已固化为 next_open
当前 2026-06-18 行情暂不可用被正确产品化为 pending
pending 时 paper apply 被阻断
前端默认请求不再消费旧模型 e4_frozen_qlib_2023_2025_ltr
安全边界通过
```

YZ 路线可以按以下口径收口：

```text
功能收口：通过
产品化默认链路：通过
只读/模拟安全边界：通过
当前成交价状态：pending，等待行情更新
```

## 2. 路线背景

YZ 路线的起点是：在进入新模型、新策略开发前，必须先把现有产品化链路清理干净。

此前存在的主要风险：

```text
registry / API / frontend 仍暴露旧模型、旧策略和实验项
daily default chain 与 paper portfolio 仍可能默认旧模型
strict E4 qlib top50 与 orthogonal LTR 特征覆盖不一致
前端只读回放可能抢跑旧模型默认请求
当前信号的 next_open 成交价缺失时，不能 fallback 到 next_close 或 signal close
```

YZ 路线的目标不是训练新模型，而是：

```text
冻结 clean registry
只保留两个产品化 E4 模型
清理产品化策略集合
补齐 strict E4 orthogonal package
统一前端/API/paper/replay 默认路径
建立 next_open execution price contract
在行情未就绪时给用户清晰 pending 状态
```

## 3. 最终产品化链路

### 3.1 生产模型集合

最终只保留两个产品化模型：

```text
Model A:
e4_frozen_qlib_2018_2022

Model B:
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
```

含义：

```text
Model A 使用 E1 frozen qlib，对当前 150 universe 打分
Model B 使用 Model A qlib top50，再用 E3 orthogonal LTR 对 top50 重排序
```

默认产品化路径不得再使用：

```text
e4_frozen_qlib_2023_2025_ltr
fresh_qlib_adaptive
fresh_qlib_2025_ltr
P3 / O4 / bridge / frozen fresh 2025 LTR
```

### 3.2 生产策略集合

当前 production selectable 策略：

```text
top50_exit_one_worst_sell
```

`origin/original` 已淘汰，不得进入默认前端/API。

`one_sell_one_buy_buggy_e8r` 如保留，只能是 research_only / diagnostic，不得作为生产策略证据，不得裸露 `buggy` 名称给用户作为默认候选。

### 3.3 成交价合同

YZ 路线固化：

```text
execution_price_mode = next_open
```

当 next_open 缺失：

```text
不得 fallback 到 next_close
不得 fallback 到 signal close
不得用 0、空值、上一日价格、手写价格模拟成交
不得展示 realized return
不得允许 paper apply 写模拟账户
```

当前真实状态：

```text
signal_asof = 2026-06-17
target_next_trading_day = 2026-06-18
execution_price_status = execution_price_unavailable
paper_apply_allowed = false
paper_apply_blocked_reason = next_open_unavailable
```

由于 2026-06-18 当前尚未收盘，行情暂不可得属于合理 pending 状态，不阻断产品化功能收口。

## 4. 阶段回顾

### 4.1 YZ0 Clean Registry

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEYZ0_CLEAN_REGISTRY_EXECUTION_REPORT_CN.md
```

完成内容：

```text
冻结 production_selectable / research_only / deprecated 集合
从默认 API/前端可选项移除 origin/original
清理 replay window policy
明确旧模型、旧策略不得进入产品化默认路径
```

审查结论：

```text
YZ0 通过
可以进入 Model A / Model B adapter 接入
```

### 4.2 YZ1 Strict E4 Model Adapters

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEYZ1_STRICT_E4_MODEL_ADAPTERS_EXECUTION_REPORT_CN.md
```

完成内容：

```text
Model A strict E4 qlib signal 生成
Model A row_count = 150
Model B adapter 路径建立
识别 strict E4 top50 与旧 P3/fresh orthogonal feature coverage 不一致
```

关键发现：

```text
旧 P3/fresh daily LTR artifact 只覆盖 P3/fresh 范围
strict E4 top50 不能直接复用旧 orthogonal readiness
```

审查结论：

```text
YZ1 通过
必须进入 YZ2 补 strict E4 orthogonal package
```

### 4.3 YZ2 Orthogonal Data Package

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEYZ2_ORTHOGONAL_DATA_PACKAGE_EXECUTION_REPORT_CN.md
```

完成内容：

```text
生成 strict E4 scoped orthogonal feature package
strict E4 top50 coverage = 50/50
feature_schema_column_count = 78
pit_violation_count = 0
no_fallback = true
Model B row_count = 50
```

审查结论：

```text
YZ2 模型/数据部分通过
execution price readiness 因 2026-06-18 OHLC 暂不可用进入 YZ2R
```

### 4.4 YZ2R Execution Price Readiness

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEYZ2R_EXECUTION_PRICE_READINESS_REPAIR_EXECUTION_REPORT_CN.md
```

完成内容：

```text
只读检查 2026-06-18 next_open / next_close 可用性
明确 status = execution_price_unavailable
next_open_available_count = 0
missing_next_open_count = 50
no_fallback_to_next_close = true
no_fallback_to_signal_close = true
manual_or_synthetic_ohlc = false
external_network_used = false
```

审查结论：

```text
YZ2R 通过
允许进入 YZ3
但 YZ3 必须把 execution_price_unavailable 产品化为 pending 用户态
```

### 4.5 YZ3 Productization E2E

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEYZ3_PRODUCTIZATION_E2E_EXECUTION_REPORT_CN.md
```

完成内容：

```text
新增 YZ clean productization status API
前端新增 YZ Clean E4 产品化卡片
显示 next_open 成交口径
显示 execution_price_unavailable pending
paper apply pending 阻断
E2E network / console audit 通过
```

审查发现：

```text
后端默认 signal_asof 硬编码 2026-06-17
前端 pending 文案硬编码 2026-06-18
```

因此进入 YZ3R。

### 4.6 YZ3R Dynamic Date Productization Repair

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEYZ3R_DYNAMIC_DATE_PRODUCTIZATION_REPAIR_EXECUTION_REPORT_CN.md
```

完成内容：

```text
后端默认 signal_asof 改为扫描 latest clean YZ artifact
前端 pending 文案改为读取 execution_price_message
新增 2026-06-19 -> 2026-06-22 fixture
证明日期随 artifact/API 动态变化
paper apply pending 阻断保持
```

审查发现：

```text
前端 readonlyReplayWindowForm 仍默认 e4_frozen_qlib_2023_2025_ltr
mounted / refreshAll 可能在 replay index 未加载前抢跑旧模型 detail 请求
```

因此进入 YZ3RR。

### 4.7 YZ3RR Frontend Clean Replay Default Repair

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEYZ3RR_FRONTEND_CLEAN_REPLAY_DEFAULT_REPAIR_EXECUTION_REPORT_CN.md
```

完成内容：

```text
readonlyReplayWindowForm 默认模型改为 e4_frozen_qlib_2018_2022
mounted / refreshAll 不再抢跑旧模型 replay detail 请求
readonly replay window index 按 clean policy 过滤
旧模型 detail 请求返回 deprecated_model_id
clean 模型无 indexed artifact 时返回 no_audited_replay_artifact_for_window
E2E 证明请求 URL 不含 e4_frozen_qlib_2023_2025_ltr
```

审查结论：

```text
YZ3RR 通过
YZ 路线可以收口
```

## 5. 最终验证证据

### 5.1 后端测试

YZ3RR 复跑结果：

```text
python -m py_compile backend/app/services/readonly_replay_window_index.py backend/app/services/readonly_replay_window.py backend/tests/test_tw_stock_readonly_replay_window_api.py backend/app/services/phase_yz3_productization_status.py backend/app/routes/tw_stock.py backend/tests/test_phase_yz3_productization_status.py

结果：通过
```

```text
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz2r_execution_price_readiness.py backend/tests/test_phase_yz3_productization_status.py backend/tests/test_tw_stock_readonly_replay_window_api.py -q

结果：37 passed
```

### 5.2 前端测试

复跑结果：

```text
cd frontend
node tests/unit/tw-stock-phase-yz-productization-check.mjs
node tests/unit/tw-stock-paper-portfolio-panel-check.mjs
corepack pnpm build
```

结果：

```text
前端静态检查通过
PaperPortfolio 静态检查通过
vite build 通过
```

### 5.3 E2E / Network / Console

YZ3RR E2E 产物：

```text
/tmp/quantdinger_tw_phase_yz3rr_e2e/network_audit.json
/tmp/quantdinger_tw_phase_yz3rr_e2e/console_audit.json
/tmp/quantdinger_tw_phase_yz3rr_e2e/phase_yz3_pending.png
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

readonly replay detail 请求：

```text
GET /api/tw-stock/readonly-replay-window?model_id=e4_frozen_qlib_2018_2022&strategy_rule=top50_exit_one_worst_sell&start=2026-01-01&end=2026-05-07
```

确认：

```text
没有 e4_frozen_qlib_2023_2025_ltr 默认请求
```

console audit：

```text
console_errors = []
page_errors = []
```

## 6. 当前用户态

前端用户态符合第一性原则：

```text
简单：用户看到 clean E4 产品化、next_open、pending/ready，不需要理解中间实验项。
准确：当前 next_open 不可用时显示 pending，不伪装成功。
实用：paper apply 按钮在 pending 时禁用，避免用户误写模拟账户。
清晰：文案直接说明等待行情更新，日期来自 API/artifact。
```

当前前端应展示：

```text
YZ Clean E4 产品化
成交口径：次一交易日开盘价
2026-06-18 行情暂不可用，等待下一轮数据更新
策略信号已生成，模拟应用将在成交价可用后开放
```

如果后续 latest artifact 变为其他日期，前端会随 API 的 `execution_price_message` 和 `target_next_trading_day` 自动变化。

## 7. 安全边界结论

YZ 路线未触发：

```text
provider refresh
provider publish
accepted latest switch
monitor config write
monitor scan
monitor alerts write
broker/order/quick-trade
真实 order
target-position / target_weight 交易语义
pending 状态下 paper apply/reset write
```

允许范围保持为：

```text
GET 状态读取
前端只读展示
mocked E2E GET
paper apply 仅在 future price ready 且用户确认后写模拟账户
```

## 8. 已知保留项

### 8.1 2026-06-18 next_open 尚不可用

当前 `execution_price_status = execution_price_unavailable` 是预期 pending 状态。

原因：

```text
当前本地 calendar / OHLC 尚无 2026-06-18 数据
2026-06-18 尚未完成收盘数据更新
```

处理方式：

```text
不阻断 YZ 功能收口
等待 V/U/W 日更链路或后续 provider 更新补齐行情
补齐后重新生成 readiness，即可从 pending 进入 ready
```

### 8.2 clean E4 replay artifact 当前为空

YZ3RR 真实后端状态：

```text
readonly replay window index windows = []
旧模型 detail = deprecated_model_id
clean 模型 detail = no_audited_replay_artifact_for_window
```

这是正确的安全状态：

```text
没有 clean audited artifact 时不 fallback 到旧 artifact
```

后续如需要展示 clean E4 replay 收益，应新开 replay artifact 生成/审计任务，不应在 YZ 收口中回退旧模型。

## 9. 对统筹节点的判断建议

建议统筹节点给出：

```text
YZ 路线通过
允许收口
不再拆 YZ4
```

理由：

```text
1. clean registry / policy 已冻结。
2. Model A / Model B 产品化信号链路已建立。
3. strict E4 orthogonal top50 覆盖已补齐。
4. execution_price next_open 合同已固化，pending 状态可解释。
5. 前端/API/paper/replay 默认路径已清理旧模型默认请求。
6. 安全边界与 E2E audit 通过。
```

## 10. 后续交接建议

YZ 路线收口后，后续工作应进入新任务，不建议继续在 YZ 下追加修复。

可新开的后续方向：

```text
clean E4 audited replay artifact 生成与审计
next_open price ready 后 paper apply ready 态 E2E
新模型开发
新策略开发
新特征/orthogonal full150 扩展
```

这些都不是 YZ 收口阻塞项。

## 11. 最终判定

最终判定：

```text
Phase YZ Strict E4 产品化收口路线：通过
可以提交统筹节点最终审查
```

一句话总结：

```text
YZ 路线已经把旧实验链路从默认产品化入口中清理出去，并把 strict E4 两模型、生产策略、next_open 成交口径、pending 用户态、paper apply 阻断和前端只读回放默认请求统一到 clean 产品化链路。
```
