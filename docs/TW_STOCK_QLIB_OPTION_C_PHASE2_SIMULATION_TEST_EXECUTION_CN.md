---
created_at: 2026-06-02
status: simulation_test_instruction
scope: quantdinger_tw_stock_qlib_option_c_phase2_full_simulation_acceptance
role_target: executor
reviewer: codex_reviewer
previous_review_breakpoint: docs/TW_STOCK_QLIB_OPTION_C_PHASE2_ACCEPTANCE_CN.md
next_review_breakpoint: docs/TW_STOCK_QLIB_OPTION_C_PHASE2_SIMULATION_TEST_REPORT_CN.md
backend_project: /path/to/taiwan-stock-quant-platform
frontend_project: /path/to/taiwan-stock-quant-platform-Vue
qlib_project: /home/chuliyang/qlib
---

# qlib Option C 台股研究信号 Phase 2 完整仿真测试执行文档

本文档给执行者使用。Phase 2 已完成最终验收，本轮不是 Phase 3，也不是继续开发功能，而是做一次完整的浏览器仿真验收，用 Playwright 覆盖真实用户路径、异常状态、只读边界和危险请求拦截。

执行者完成本文档后必须写 report，并停止继续修改，等待审核。

---

## 1. 测试目标

本轮目标是回答三个问题：

1. 正常 accepted qlib artifact 场景下，用户能否完整完成研究查看、历史对照、观察草稿和只读回测入口流程。
2. stale、wait-state、blocked、missing、接口失败、空数据等异常状态下，页面是否清楚展示状态，并且不误导为可交易信号。
3. 全流程是否严格保持 research-only/read-only，不自动保存配置、不自动扫描、不自动回测、不下单、不连接 broker、不触发 qlib 生成或 provider refresh。

---

## 2. 测试边界

允许：

- 新增或扩展 Playwright 仿真测试脚本。
- 新增截图输出。
- 新增测试报告文档。
- 使用 mock API 响应构造不同 qlib 状态。
- 使用真实本地后端做一次只读 smoke 对照。

禁止：

- 新增产品功能。
- 修改 qlib 模型、provider、recorder、universe。
- 调用 qlib daily signal script。
- 刷新 qlib provider。
- 自动补数据。
- 训练或调参模型。
- 写 DB。
- 自动保存监控配置。
- 自动扫描。
- 自动创建提醒。
- 自动运行回测。
- 写订单、仓位、pending order、交易计划。
- 连接 broker。
- 调用 quick-trade。
- 生成 target position / target weight。
- 把 qlib score、trend score、回测结果合成为买入分。
- 把 qlib score 表述为收益率、胜率、涨幅、买入概率或仓位。

---

## 3. 推荐测试文件

前端项目：

```text
/path/to/taiwan-stock-quant-platform-Vue
```

优先新增独立脚本：

```text
tests/unit/tw-stock-monitor-qlib-simulation.mjs
```

如果复用现有 smoke 更合适，也可以扩展：

```text
tests/unit/tw-stock-monitor-local-smoke.mjs
```

但 report 中必须说明复用或新增的原因、入口命令、覆盖场景。

---

## 4. Playwright 仿真原则

建议测试脚本启动真实前端页面，并用 Playwright route mock qlib 相关 API：

```text
GET /api/tw-stock/quant/signals/latest
GET /api/tw-stock/quant/signals/runs
GET /api/tw-stock/quant/signals/runs/<run_id>
GET /api/tw-stock/quant/signals/health
```

危险请求必须统一拦截和计数：

```text
配置保存类：
POST/PUT/PATCH /api/tw-stock/monitor/config

扫描类：
POST /api/tw-stock/monitor/scan

提醒写入类：
POST/PUT/PATCH /api/tw-stock/monitor/alerts

回测自动执行类：
POST /api/tw-stock/backtest
POST /api/indicator/backtest

交易/订单/仓位类：
任何包含 order/orders/trade/trading/position/positions/target-position/quick-trade/broker 的 POST/PUT/PATCH/DELETE

qlib 生成/刷新类：
任何包含 qlib/run/generate/refresh/provider/retrain/tune 的 POST/PUT/PATCH/DELETE
```

要求：

- 危险请求命中数必须为 0。
- 页面初始化允许读取 alerts/config 等只读接口，但必须在 report 中列明实际读请求。
- 点击 `加入观察`、`填入监控配置`、`回测验证` 后仍不得出现危险写请求。

---

## 5. 必测场景

### 5.1 Accepted Latest Happy Path

Mock 条件：

- health 返回 accepted、freshness.stale=false。
- latest 返回 accepted，Top 30 有 30 条 signals。
- runs 返回 accepted/wait_state/blocked 混合列表。

验证：

- 页面显示 `qlib Option C 数据状态`。
- 页面显示 `qlib Option C 研究排序`。
- Top 30 rows 可见。
- `qlib_score`、`rank`、`symbol` 可见。
- `trend_label`、`trend_score` 或趋势解释字段可见。
- 页面出现 research-only/read-only/not order 语义。
- 不出现买入、卖出、下单、自动交易、quick-trade、broker、target position 等交易入口。

截图：

```text
/tmp/quantdinger_tw_qlib_simulation/01-accepted-latest.png
```

### 5.2 Top30 / Top50 / All 切换

Mock 条件：

- latest 对 `bucket=top30` 返回 30 条。
- latest 对 `bucket=top50` 返回 50 条。
- latest 对 `bucket=all` 返回大于 50 条或至少与 mock 数据一致。

验证：

- 点击 Top 50 后展示数量或 meta 与 Top 50 一致。
- 再切回 Top 30 后恢复。
- 如果页面有 all 入口，验证 all 只展示研究列表，不改变交易边界。
- 切换过程中危险请求为 0。

截图：

```text
/tmp/quantdinger_tw_qlib_simulation/02-bucket-switch.png
```

### 5.3 Historical Accepted Run

Mock 条件：

- runs 列表包含 accepted run。
- run detail 返回 accepted，signals 非空，run_id 与列表一致。

验证：

- 历史 run 区块可见。
- 点击 accepted run 后，页面显示对应 run_id/asof。
- 排序表切换到历史 run 数据。
- 点击回到 latest 后恢复 latest。
- 不自动触发回测、扫描、保存配置。

截图：

```text
/tmp/quantdinger_tw_qlib_simulation/03-historical-accepted.png
```

### 5.4 Wait-State Run

Mock 条件：

- runs 列表包含 `wait_state_data_refresh_needed`。
- run detail 返回 wait-state、warnings、signals=[]。

验证：

- 页面明确显示 wait-state 或数据等待状态。
- 不显示可用研究排序 signals。
- 不显示加入观察、回测验证等会让用户误以为可用的 row action。
- 不出现自动补数据、刷新 provider、生成 qlib 信号按钮。

截图：

```text
/tmp/quantdinger_tw_qlib_simulation/04-wait-state.png
```

### 5.5 Blocked Run

Mock 条件：

- runs 列表包含 blocked run。
- run detail 返回 blocked、warnings/errors、signals=[]。

验证：

- 页面明确显示 blocked 原因。
- 不显示可用研究排序 signals。
- 不允许加入观察。
- 不允许只读回测入口绑定到 blocked signal。
- 不出现修复、重跑、刷新、补数据、训练按钮。

截图：

```text
/tmp/quantdinger_tw_qlib_simulation/05-blocked.png
```

### 5.6 Missing Latest

Mock 条件：

- health 返回 latest.exists=false。
- latest 返回 missing 或 ok=false，signals=[]。

验证：

- 页面展示 latest missing 状态。
- 不出现空表误导为正常无候选。
- 不出现生成 qlib 信号、刷新 provider、自动补数据入口。
- 历史 run 如果仍有 accepted，可继续只读浏览历史。

截图：

```text
/tmp/quantdinger_tw_qlib_simulation/06-missing-latest.png
```

### 5.7 Stale Health With Newer Wait-State

Mock 条件：

- latest accepted 且 accepted_validated=true。
- health.freshness.stale=true。
- stale_reason=`fresh_data_wait_state_present`。
- runs 中存在 asof 更新的 wait-state run。

验证：

- 页面同时表达 latest 可读和 freshness stale。
- stale 不被表达为卖出/买入/仓位建议。
- wait-state warning 可见。
- 不触发自动修复或自动生成。

截图：

```text
/tmp/quantdinger_tw_qlib_simulation/07-stale-wait-state.png
```

### 5.8 API Failure / Timeout

Mock 条件：

- health 或 latest 返回 500、timeout、网络失败之一。

验证：

- 页面展示错误状态。
- 已有页面不崩溃。
- 不把旧数据伪装为当前 accepted。
- 不触发危险请求。

截图：

```text
/tmp/quantdinger_tw_qlib_simulation/08-api-failure.png
```

### 5.9 Empty Accepted Signals

Mock 条件：

- latest status=accepted。
- accepted_validated=true。
- signals=[]。
- summary 中 rows=0 或 warning 说明空数据。

验证：

- 页面展示空状态和 warning。
- 不显示交易建议。
- 不允许批量加入观察。
- 不触发扫描或保存配置。

截图：

```text
/tmp/quantdinger_tw_qlib_simulation/09-empty-accepted.png
```

### 5.10 Watch Draft LocalStorage

Mock 条件：

- latest accepted 且至少 3 条 signals。

验证：

- 点击加入观察后，localStorage key 存在：

```text
tw-stock-monitor-qlib-watch-draft
```

- localStorage 内容只包含研究字段，例如 symbol/run_id/rank/qlib_score/trend_label/trend_score。
- 刷新页面后草稿仍可见。
- 清空草稿后 localStorage 清理或变为空。
- 加入、移除、清空均不写后端。

截图：

```text
/tmp/quantdinger_tw_qlib_simulation/10-watch-draft.png
```

### 5.11 Fill Monitor Config Is Manual Only

Mock 条件：

- watch draft 中已有多个 symbol。

验证：

- 点击 `填入监控配置` 只打开或填充配置抽屉。
- 不调用保存配置 API。
- 不调用扫描 API。
- 不创建提醒。
- UI 必须仍需要用户手动保存。

截图：

```text
/tmp/quantdinger_tw_qlib_simulation/11-fill-config-manual-only.png
```

### 5.12 Readonly Backtest Linkage

Mock 条件：

- latest accepted 且 row 有 symbol。

验证：

- 点击 row 的 `回测验证` 只打开只读回测面板。
- 面板表达 historical simulation/read-only/orders_enabled=false/connects_to_broker=false。
- 点击 qlib row action 不自动 POST backtest。
- 不出现下单、买入、卖出、自动交易、broker、quick-trade、target position。

截图：

```text
/tmp/quantdinger_tw_qlib_simulation/12-readonly-backtest.png
```

### 5.13 Mobile / Narrow Viewport

Viewport：

```text
390x844
```

验证：

- qlib 数据状态、研究排序、历史 run、观察草稿没有明显文本重叠。
- 关键按钮可点击。
- 表格或卡片在窄屏下可滚动或合理折行。
- 不因布局隐藏 read-only/not order 安全语义。

截图：

```text
/tmp/quantdinger_tw_qlib_simulation/13-mobile.png
```

### 5.14 Real Artifact Readonly Smoke

在后端项目执行真实 artifact 只读 smoke：

```bash
cd /path/to/taiwan-stock-quant-platform
PYTHONPATH=/path/to/taiwan-stock-quant-platform/backend python - <<'PY'
from app.services.tw_stock_qlib_option_c import QlibOptionCSignalReader
r = QlibOptionCSignalReader()
latest = r.latest(bucket='top30', enrich_trend=True, trend_limit=120)
print('latest', latest['status'], latest.get('asof'), latest.get('run_id'), len(latest.get('signals') or []))
runs = r.list_runs(limit=10, status='all')
print('runs', [(i.get('run_id'), i.get('status'), i.get('accepted_validated')) for i in runs.get('items', [])])
health = r.health()
print('health', health.get('status'), health.get('latest'), health.get('freshness'), health.get('runs'))
PY
```

要求：

- 只读执行。
- 不调用 qlib 生成。
- 不刷新 provider。
- report 中记录 latest/runs/health 摘要。

---

## 6. 必跑验证命令

后端：

```bash
cd /path/to/taiwan-stock-quant-platform
python -m py_compile backend/app/services/tw_stock_qlib_option_c.py backend/app/routes/tw_stock.py
python -m pytest backend/tests/test_tw_stock_qlib_option_c_signals.py backend/tests/test_tw_stock_quant_signal_api.py -q
python -m pytest backend/tests/test_tw_stock_backtest.py backend/tests/test_verify_tw_stock_research_stack.py -q
```

前端：

```bash
cd /path/to/taiwan-stock-quant-platform-Vue
node --check tests/unit/tw-stock-monitor-qlib-simulation.mjs
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-monitor-workflow-check.mjs
corepack pnpm build
```

仿真测试：

```bash
cd /path/to/taiwan-stock-quant-platform-Vue
TW_STOCK_MONITOR_USERNAME=quantdinger TW_STOCK_MONITOR_PASSWORD=change-me TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 TW_STOCK_MONITOR_SCREENSHOT_DIR=/tmp/quantdinger_tw_qlib_simulation node tests/unit/tw-stock-monitor-qlib-simulation.mjs
```

如果执行者复用其他脚本或端口，必须在 report 中写明实际命令。

---

## 7. 通过标准

必须全部满足：

- 14 个必测场景全部通过，或 report 中对未覆盖项给出明确原因。
- 危险请求计数为 0。
- 截图完整生成。
- 后端测试通过。
- 前端 static/workflow/build 通过。
- 页面异常状态不崩溃。
- wait-state/blocked/missing/stale 不被表达为交易建议。
- watch draft 只存在 localStorage。
- `填入监控配置` 不保存配置、不扫描。
- `回测验证` 不自动运行回测。
- 真实 artifact smoke 只读通过。

任一危险请求非 0，直接判定本轮仿真失败。

---

## 8. Report 要求

执行者完成后新增：

```text
docs/TW_STOCK_QLIB_OPTION_C_PHASE2_SIMULATION_TEST_REPORT_CN.md
```

report 必须包含：

```text
1. 执行摘要
2. 修改文件列表
3. Playwright 仿真脚本入口和命令
4. 14 个场景逐项结果
5. 危险请求拦截统计
6. 截图路径清单
7. 后端测试输出摘要
8. 前端测试/build 输出摘要
9. 真实 artifact readonly smoke 输出摘要
10. 发现的问题和严重度
11. 是否偏离 research-only/read-only 主线
12. 是否建议 Phase 2 最终收尾
```

场景结果建议使用表格：

```text
场景 | 结果 | 关键断言 | 截图 | 备注
```

---

## 9. 下一个审核断点

审核断点：

```text
docs/TW_STOCK_QLIB_OPTION_C_PHASE2_SIMULATION_TEST_REPORT_CN.md
```

执行者写完 report 后停止，不要进入 Phase 3，不要继续新增功能。

审核者将根据 report 判断：

- 是否存在真实用户路径问题。
- 是否存在只读边界破坏。
- 是否需要修复后再收尾。
- 是否可以把 Phase 2 标记为最终关闭。

