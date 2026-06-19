# Phase YZ4 Paper + Replay 最小收口修复工作文档

生成日期：2026-06-18

参考文档：

```text
docs/tw_modular_daily_update_productization/PHASEYZ_FINAL_SUMMARY_REVIEW_AND_REPAIR_SUGGESTION_CN.md
docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md
docs/tw_modular_daily_update_productization/PHASEYZ3RR_FRONTEND_CLEAN_REPLAY_DEFAULT_REPAIR_EXECUTION_REPORT_CN.md
```

## 1. 执行结论先行

统筹审查后认为 YZ 不能直接最终收口，需要补一个小阶段：

```text
Phase YZ4：Paper + Replay 最小收口修复
```

YZ0-YZ3RR 已经完成：

```text
clean registry 只保留两个产品化 E4 模型
production strategy 收口到 top50_exit_one_worst_sell
Model A strict E4 qlib signal 150 行
Model B strict E4 orthogonal LTR signal 50 行
strict E4 top50 orthogonal coverage 50/50
execution_price_mode = next_open
next_open 缺失时前端 pending 展示
pending 时前端 paper apply 按钮禁用
readonly replay window 不再默认请求旧 e4_frozen_qlib_2023_2025_ltr
E2E network audit 无 forbidden write
```

但还有两个最终收口缺口：

```text
P0: paper portfolio 后端仍硬编码旧 e4_frozen_qlib_2023_2025_ltr 作为 apply 校验
P1: clean E4 replay artifact 当前为空，前端只读回放窗口只是安全占位，不是完整 clean E4 回放展示
```

YZ4 只修这两个缺口，不扩展范围。

## 2. YZ4 目标

YZ4 目标：

```text
paper portfolio 后端改为 clean registry / policy 驱动
pending execution_price 时后端 POST apply-decision 必须拒绝
latest paper decision 必须过滤旧模型 artifact
生成并登记 clean E4 两模型的 readonly replay artifact
前端只读回放窗口可以展示 clean E4 replay 结果
```

YZ4 完成后才能把 YZ 路线判定为 fully closed。

## 3. 禁止范围

YZ4 严禁：

```text
训练模型
调参
改变两个生产模型身份
新增 production strategy
重选策略
使用旧 P3 / O4 / fresh / bridge 模型
provider refresh
provider publish
accepted latest switch
monitor config write
monitor scan
monitor alerts write
broker/order/quick-trade
真实 order
target-position / target_weight 交易语义
```

YZ4 允许：

```text
读取 clean registry / replay policy
读取已有 strict E4 signal artifact
读取已有 readonly/order-intent/replay 相关本地产物
生成 clean E4 readonly replay artifact / index
修改 paper portfolio 后端校验
修改必要测试与 E2E
前端只读展示
pending 状态下后端拒绝 paper apply
```

## 4. P0：Paper Portfolio 后端 clean registry 化

### 4.1 当前问题

当前文件：

```text
backend/app/services/tw_stock_paper_portfolio.py
```

存在硬编码：

```text
MODEL_ID = "e4_frozen_qlib_2023_2025_ltr"
STRATEGY_RULE = "top50_exit_one_worst_sell"
```

并且 `_validate_intent()` 仍检查：

```text
if str(intent.get("model_id") or "") != MODEL_ID:
    return self._reject("invalid_artifact", "model_id mismatch")
```

这会导致：

```text
strict E4 paper decision ready 后可能被后端拒绝
旧 paper artifact 仍可能被 latest_decision 读到
前端 pending 禁用不能替代后端权限/状态校验
```

### 4.2 必须修复

执行者必须：

```text
1. 移除旧 MODEL_ID = e4_frozen_qlib_2023_2025_ltr 硬编码。
2. 保留或改造 STRATEGY_RULE 时，也必须从 clean registry / policy 校验，不得只靠常量。
3. paper apply 校验读取 configs/tw_modular_registry.yaml / configs/tw_replay_window_policy.yaml。
4. 只允许 production_models.production_selectable 中的模型。
5. 只允许 strategies.production_selectable 中的策略。
6. 旧模型 artifact 必须拒绝或过滤，不能作为 latest decision。
7. pending execution_price 时，POST /paper-portfolio/apply-decision 后端必须拒绝。
```

允许模型：

```text
e4_frozen_qlib_2018_2022
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
```

允许策略：

```text
top50_exit_one_worst_sell
```

### 4.3 execution price 后端 gate

后端 apply 不能只相信前端按钮状态。

在 `apply_decision()` 真正写 `qd_tw_sim_*` 前，必须读取 YZ execution price readiness / productization status，并执行：

```text
execution_price_mode == next_open
execution_price_status == pass
paper_apply_allowed == true
next_open_available_count > 0
missing_next_open_count == 0
no_fallback_to_next_close == true
no_fallback_to_signal_close == true
```

当前真实状态是：

```text
execution_price_status = execution_price_unavailable
paper_apply_allowed = false
paper_apply_blocked_reason = next_open_unavailable
```

因此当前环境下：

```text
POST /api/tw-stock/paper-portfolio/apply-decision
```

必须返回拒绝，例如：

```text
status = execution_price_unavailable
ok = false
```

不得写：

```text
qd_tw_sim_apply_runs
qd_tw_sim_orders
qd_tw_sim_trades
qd_tw_sim_positions
```

除非 readiness 变为 pass。

### 4.4 latest_decision 过滤要求

`latest_decision()` 必须只返回 clean registry 允许的 paper decision artifact。

必须过滤：

```text
model_id = e4_frozen_qlib_2023_2025_ltr
origin/original strategy
research_only strategy
deprecated strategy
非 PaperDecisionBundleArtifact
checksum 不通过 artifact
execution_price_mode 非 next_open 的 artifact
```

如果当前本地只有旧 paper artifact，则返回：

```text
ok = false
status = no_clean_decision
```

不得 fallback 到旧模型 paper artifact。

## 5. P1：clean E4 readonly replay artifact 最小生成与登记

### 5.1 当前问题

YZ3RR 当前真实状态：

```text
readonly replay window index windows = []
旧模型 detail = deprecated_model_id
clean 模型 detail = no_audited_replay_artifact_for_window
```

这是安全状态，但还不是完整可用状态。

YZ4 必须补齐最小 clean E4 replay 可用性。

### 5.2 生成范围

只生成以下组合：

```text
models:
  e4_frozen_qlib_2018_2022
  e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025

strategy:
  top50_exit_one_worst_sell

window:
  start = 2026-01-01
  end = 2026-05-07

execution_price_mode:
  next_open
```

不得扩大到：

```text
多策略矩阵
旧模型矩阵
fresh / P3 / O4 / bridge 模型
训练期窗口
用户自选任意窗口
```

### 5.3 artifact 要求

生成的 readonly replay artifact 必须显式包含：

```text
artifact_type
schema_version
model_id
strategy_rule
window.start
window.end
execution_price_mode = next_open
readonly_only = true
not_order = true
not_target_position = true
not_investment_advice = true
production_trade_enabled = false
not_generated_in_api_handler = true
generated_by
source_model_signal_artifact
source_order_intent_artifact 或等价输入来源
summary
checksum
no_write_guarantees
```

如果复用已有 replay 生成逻辑，必须保证：

```text
API handler 只读读取 indexed artifact
不得在 GET /readonly-replay-window 中按需生成 replay
不得写 provider / accepted latest / monitor / broker / order
```

### 5.4 readonly replay index 要求

必须把两个 clean E4 replay windows 登记进：

```text
data_tw/artifacts/readonly_replay_windows/d7/...
```

并更新 latest pointer。

`GET /api/tw-stock/readonly-replay-window-index` 返回：

```text
windows 包含 2 个 clean E4 window
不包含 e4_frozen_qlib_2023_2025_ltr
不包含 P3/O4/fresh/bridge
```

`GET /api/tw-stock/readonly-replay-window` 对两个 clean E4 组合必须返回：

```text
ok = true
readonly_only = true
model_id in clean models
strategy_rule = top50_exit_one_worst_sell
execution_price_mode = next_open
summary 可展示
checksum.ok = true
```

对旧模型仍必须返回：

```text
status = deprecated_model_id
```

## 6. 前端要求

前端只需要验证，不建议大改 UI。

必须确保：

```text
只读回放窗口 index 返回 clean windows 后，前端能展示 clean E4 replay 结果
页面中不出现 e4_frozen_qlib_2023_2025_ltr 默认请求
不出现 origin/original/P3/O4/fresh/bridge 作为生产候选
pending execution_price 时 paper apply 仍禁用
如果 paper latest decision 无 clean artifact，显示明确 unavailable，不 fallback 旧 artifact
```

E2E 必须证明：

```text
readonly replay window panel 展示 clean E4 model_id
readonly replay detail 请求不含旧模型
paper apply POST 在 pending 状态下不发生
如直接测试 POST apply，则后端返回 execution_price_unavailable 且无 DB 写入
```

## 7. 测试要求

### 7.1 Paper portfolio 单测

必须新增/更新：

```text
backend/tests/test_tw_stock_paper_portfolio_x2.py
```

覆盖：

```text
tw_stock_paper_portfolio.py 不再硬编码旧 MODEL_ID
clean Model A intent 可通过 registry/policy 校验
clean Model B intent 可通过 registry/policy 校验
旧 e4_frozen_qlib_2023_2025_ltr intent 被拒绝
research_only / deprecated strategy 被拒绝
pending execution_price 时 apply_decision 被拒绝且不写 apply_runs/orders/trades
latest_decision 过滤旧模型 artifact
```

### 7.2 Readonly replay 单测

必须新增/更新：

```text
backend/tests/test_tw_stock_readonly_replay_window_api.py
```

覆盖：

```text
readonly replay index 返回两个 clean E4 windows
旧模型不在 index
clean Model A detail 返回 ok=true
clean Model B detail 返回 ok=true
payload.execution_price_mode = next_open
payload.checksum.ok = true
旧模型 detail 返回 deprecated_model_id
GET-only，不支持 POST/PUT/PATCH/DELETE
```

### 7.3 前端静态检查

必须更新：

```text
frontend/tests/unit/tw-stock-phase-yz-productization-check.mjs
frontend/tests/unit/tw-stock-paper-portfolio-panel-check.mjs
```

覆盖：

```text
前端不默认旧模型
YZ pending 文案仍读取 execution_price_message
PaperPortfolioPanel 仍接收 phaseYzStatus
pending 时 applyDisabled 包含 phaseYZPaperBlocked
只读回放默认请求 clean E4
```

### 7.4 E2E

必须更新或新增 E2E，产物目录建议：

```text
/tmp/quantdinger_tw_phase_yz4_e2e
```

必须断言：

```text
readonly replay window index 请求为 GET
readonly replay detail 请求为 GET
readonly replay detail 请求不含 e4_frozen_qlib_2023_2025_ltr
前端显示 clean E4 replay summary
paper apply button disabled when execution_price_unavailable
paper_apply_write_count = 0
provider/accepted latest/monitor/broker/order/quick-trade writes = 0
console_errors = []
page_errors = []
```

如果单独做后端 POST apply pending 测试，必须断言：

```text
status = execution_price_unavailable
DB apply_runs/orders/trades 没有新增
```

## 8. 验收命令

执行者至少需要提供：

```text
python -m py_compile backend/app/services/tw_stock_paper_portfolio.py backend/app/services/readonly_replay_window.py backend/app/services/readonly_replay_window_index.py backend/app/routes/tw_stock.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_readonly_replay_window_api.py
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz2r_execution_price_readiness.py backend/tests/test_phase_yz3_productization_status.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_readonly_replay_window_api.py -q
cd frontend && node tests/unit/tw-stock-phase-yz-productization-check.mjs
cd frontend && node tests/unit/tw-stock-paper-portfolio-panel-check.mjs
cd frontend && corepack pnpm build
<YZ4 frontend e2e command>
```

如果新增 artifact 生成脚本，必须提供：

```text
python -m py_compile <new script>
python <new script> --json
```

并在执行报告中列出全部产物路径。

## 9. 安全审计要求

YZ4 执行报告必须包含 forbidden action audit。

必须证明未触发：

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

paper apply 在 pending 状态下必须：

```text
后端拒绝
不写模拟账户
不写 apply_runs
不写 orders/trades
```

paper apply 在未来 price ready 状态下允许的范围仅限：

```text
qd_tw_sim_* 模拟账户表
simulation_only = true
trading.real_orders_enabled = false
trading.connects_to_broker = false
```

## 10. 执行报告路径

执行者完成后写：

```text
docs/tw_modular_daily_update_productization/PHASEYZ4_PAPER_REPLAY_FINAL_REPAIR_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
修复文件列表
paper portfolio clean registry/policy 校验说明
pending execution_price 后端拒绝 apply 的证据
latest_decision 过滤旧模型 artifact 的证据
clean E4 replay artifact 路径清单
readonly replay index latest pointer 路径
两个 clean E4 windows 的 API 返回摘要
旧模型 detail deprecated_model_id 证据
前端 E2E 截图/DOM 摘要
network_audit.json
console_audit.json
py_compile / pytest / frontend static / build / E2E 结果
forbidden action audit
最终是否可收口的执行者判断
```

## 11. YZ4 收口标准

YZ4 通过标准：

```text
tw_stock_paper_portfolio.py 不再硬编码旧 e4_frozen_qlib_2023_2025_ltr
paper apply 校验 registry/policy-driven
pending execution_price 时后端 POST apply-decision 拒绝
latest paper decision 过滤旧模型 artifact
readonly replay index 至少包含两个 clean E4 windows
clean Model A replay detail ok=true
clean Model B replay detail ok=true
replay payload execution_price_mode = next_open
前端能展示 clean E4 replay 结果
E2E 不请求旧模型
network audit forbidden counts = 0
paper apply/reset 写入仍仅限模拟账户，且 pending 下无写入
```

任一不满足：

```text
停止，不允许 YZ 最终收口。
```

全部满足后：

```text
YZ 路线可以最终收口。
```
