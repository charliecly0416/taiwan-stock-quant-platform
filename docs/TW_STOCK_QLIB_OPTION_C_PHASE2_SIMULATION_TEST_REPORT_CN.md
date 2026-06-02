# qlib Option C 台股研究信号 Phase 2 完整仿真测试报告

## 1. 执行摘要

本轮按 `docs/TW_STOCK_QLIB_OPTION_C_PHASE2_SIMULATION_TEST_EXECUTION_CN.md` 执行 Phase 2 完整浏览器仿真验收。本轮不是 Phase 3，不新增产品功能，仅新增独立 Playwright 仿真测试脚本和本报告。

结论：13 个 Playwright 浏览器仿真场景全部通过，第 14 个真实 artifact readonly smoke 通过。危险写请求总数为 0。未发现偏离 research-only/read-only 主线的问题。

## 2. 修改文件列表

新增/修改：

- `/path/to/taiwan-stock-quant-platform-Vue/tests/unit/tw-stock-monitor-qlib-simulation.mjs`
- `docs/TW_STOCK_QLIB_OPTION_C_PHASE2_SIMULATION_TEST_REPORT_CN.md`

未修改后端业务代码、前端产品代码、qlib 模型、provider、recorder、universe 或任何 qlib 生成脚本。

## 3. Playwright 仿真脚本入口和命令

新增独立脚本而不是扩展现有 local smoke，原因：本轮需要覆盖 missing/stale/API failure/empty/mobile 等异常状态，并需要独立统计危险写请求，避免改变既有 smoke 的验收含义。

入口：

```text
/path/to/taiwan-stock-quant-platform-Vue/tests/unit/tw-stock-monitor-qlib-simulation.mjs
```

运行命令：

```bash
cd /path/to/taiwan-stock-quant-platform-Vue
TW_STOCK_MONITOR_USERNAME=quantdinger TW_STOCK_MONITOR_PASSWORD=change-me TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 TW_STOCK_MONITOR_SCREENSHOT_DIR=/tmp/quantdinger_tw_qlib_simulation node tests/unit/tw-stock-monitor-qlib-simulation.mjs
```

脚本使用真实前端页面和真实登录，使用 Playwright route mock qlib API：latest、runs、run detail、health。

## 4. 14 个场景逐项结果

| 场景 | 结果 | 关键断言 | 截图 | 备注 |
|---|---|---|---|---|
| 5.1 Accepted Latest Happy Path | 通过 | health、研究排序、Top30、qlib_score、Rank、symbol、trend 字段、research-only/read-only/not order 可见；无交易入口 | `/tmp/quantdinger_tw_qlib_simulation/01-accepted-latest.png` | - |
| 5.2 Top30 / Top50 / All 切换 | 通过 | Top50 后 rows 50，切回 Top30 后 rows 30；危险请求 0 | `/tmp/quantdinger_tw_qlib_simulation/02-bucket-switch.png` | 页面无 qlib all bucket 入口，按文档只验证 Top30/Top50 |
| 5.3 Historical Accepted Run | 通过 | 点击 accepted run 显示对应 run_id/asof，回到 latest 可恢复 | `/tmp/quantdinger_tw_qlib_simulation/03-historical-accepted.png` | 未自动回测、未扫描、未保存配置 |
| 5.4 Wait-State Run | 通过 | 显示 wait-state 和 warning；不显示 signal table；无加入观察按钮 | `/tmp/quantdinger_tw_qlib_simulation/04-wait-state.png` | 无自动补数据/provider refresh/生成入口 |
| 5.5 Blocked Run | 通过 | 显示 blocked 原因；不显示 signal table；不允许加入观察 | `/tmp/quantdinger_tw_qlib_simulation/05-blocked.png` | 无修复、重跑、训练按钮 |
| 5.6 Missing Latest | 通过 | 显示 missing_latest_signal；不显示可用 signal table；历史 accepted run 仍可只读浏览 | `/tmp/quantdinger_tw_qlib_simulation/06-missing-latest.png` | 无生成 qlib/刷新 provider/自动补数据入口 |
| 5.7 Stale Health With Newer Wait-State | 通过 | latest accepted 可读，同时显示 stale 与 fresh_data_wait_state_present | `/tmp/quantdinger_tw_qlib_simulation/07-stale-wait-state.png` | stale 未表达为买卖/仓位建议 |
| 5.8 API Failure / Timeout | 通过 | health/latest 500 时页面不崩溃；显示错误状态；不展示旧 accepted 表格 | `/tmp/quantdinger_tw_qlib_simulation/08-api-failure.png` | 无危险请求 |
| 5.9 Empty Accepted Signals | 通过 | accepted 但 rows 0 时显示 empty/warning；无 row action | `/tmp/quantdinger_tw_qlib_simulation/09-empty-accepted.png` | 无批量加入观察、无扫描或保存 |
| 5.10 Watch Draft LocalStorage | 通过 | 加入 3 条后 localStorage key 存在；字段限于研究字段；刷新后仍可见；清空后 localStorage 为 [] | `/tmp/quantdinger_tw_qlib_simulation/10-watch-draft.png` | 加入/刷新/清空均不写后端 |
| 5.11 Fill Monitor Config Is Manual Only | 通过 | 点击填入监控配置只打开并填充配置抽屉；未保存配置、未扫描、未创建提醒 | `/tmp/quantdinger_tw_qlib_simulation/11-fill-config-manual-only.png` | UI 仍需用户手动保存 |
| 5.12 Readonly Backtest Linkage | 通过 | 点击回测验证只打开只读回测面板；显示 historical simulation/read-only/orders_enabled=false/connects_to_broker=false | `/tmp/quantdinger_tw_qlib_simulation/12-readonly-backtest.png` | 未 POST backtest |
| 5.13 Mobile / Narrow Viewport | 通过 | 390x844 下 qlib 数据状态、研究排序、历史 run、观察草稿关键区块可见；安全语义未隐藏 | `/tmp/quantdinger_tw_qlib_simulation/13-mobile.png` | 未发现关键区块不可见 |
| 5.14 Real Artifact Readonly Smoke | 通过 | latest accepted 30 条；runs/health 可读；只读，无 qlib 生成或 provider refresh | 不适用 | 输出见第 9 节 |

## 5. 危险请求拦截统计

Playwright 统一拦截并计数危险写请求：配置保存、扫描、提醒写入、回测 POST、交易/订单/仓位、broker/quick-trade、qlib 生成/刷新/provider/retrain/tune。

结果：

```text
totalDangerous=0
configWrites=0
scanPosts=0
alertWrites=0
backtestPosts=0
```

页面初始化允许只读读取 config/alerts/scan logs；本轮危险写请求为 0。

## 6. 截图路径清单

```text
/tmp/quantdinger_tw_qlib_simulation/01-accepted-latest.png
/tmp/quantdinger_tw_qlib_simulation/02-bucket-switch.png
/tmp/quantdinger_tw_qlib_simulation/03-historical-accepted.png
/tmp/quantdinger_tw_qlib_simulation/04-wait-state.png
/tmp/quantdinger_tw_qlib_simulation/05-blocked.png
/tmp/quantdinger_tw_qlib_simulation/06-missing-latest.png
/tmp/quantdinger_tw_qlib_simulation/07-stale-wait-state.png
/tmp/quantdinger_tw_qlib_simulation/08-api-failure.png
/tmp/quantdinger_tw_qlib_simulation/09-empty-accepted.png
/tmp/quantdinger_tw_qlib_simulation/10-watch-draft.png
/tmp/quantdinger_tw_qlib_simulation/11-fill-config-manual-only.png
/tmp/quantdinger_tw_qlib_simulation/12-readonly-backtest.png
/tmp/quantdinger_tw_qlib_simulation/13-mobile.png
```

## 7. 后端测试输出摘要

命令：

```bash
python -m py_compile backend/app/services/tw_stock_qlib_option_c.py backend/app/routes/tw_stock.py
python -m pytest backend/tests/test_tw_stock_qlib_option_c_signals.py backend/tests/test_tw_stock_quant_signal_api.py -q
python -m pytest backend/tests/test_tw_stock_backtest.py backend/tests/test_verify_tw_stock_research_stack.py -q
```

结果：

```text
py_compile passed
66 passed in 1.35s
14 passed in 1.10s
```

## 8. 前端测试/build 输出摘要

命令：

```bash
node --check tests/unit/tw-stock-monitor-qlib-simulation.mjs
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-monitor-workflow-check.mjs
corepack pnpm build
```

结果：

```text
node --check passed
tw-stock-monitor static checks passed
tw-stock-monitor workflow checks passed
built in 23.25s
```

build 仍有既有 `/deep/` CSS minify warning、locale dynamic/static import warning 和大 chunk warning；本轮不处理这些既有构建 warning。

## 9. 真实 artifact readonly smoke 输出摘要

命令使用 `QlibOptionCSignalReader` 读取真实本地 artifact，未运行 qlib script，未刷新 provider。

输出摘要：

```text
latest accepted 2026-06-01 option_c_daily_signal_20260601_20260601T121228Z 30
runs [
  ('option_c_daily_signal_20260601_20260601T121228Z', 'accepted', True),
  ('option_c_daily_signal_20260602_20260601T121150Z', 'wait_state_data_refresh_needed', False),
  ('option_c_daily_signal_20260601_20260601T121128Z', 'dry_run_preflight_pass', False),
  ('option_c_daily_signal_20260601_20260601T115923Z', 'accepted', True),
  ('option_c_daily_signal_20260601_20260601T115756Z', 'accepted', True),
  ('option_c_daily_signal_20260601_20260601T115730Z', 'dry_run_preflight_pass', False),
  ('option_c_daily_signal_20260601_20260601T115553Z', 'accepted', True),
  ('option_c_daily_signal_20260601_20260601T115523Z', 'dry_run_preflight_pass', False),
  ('option_c_daily_signal_20260601_20260601T115247Z', 'blocked_formal_validation_failed', False)
]
health accepted latest.exists=True latest.asof=2026-06-01 accepted_validated=True
freshness asof_age_days=1 stale=True stale_reason=fresh_data_wait_state_present
runs total_scanned=9 accepted=4 wait_state=1 blocked=1 other=3
```

解释：当前日期为 2026-06-02，latest artifact asof 为 2026-06-01 且 accepted/validated；因存在更新 asof 的 wait-state run，health 按保守规则标记 `fresh_data_wait_state_present`。这是只读状态提示，不触发自动修复、provider refresh 或 qlib 生成。

## 10. 发现的问题和严重度

未发现产品级阻断问题。

测试脚本调试中发现并修正 3 个脚本问题：

- 低严重度：`Rank` 表头大小写断言写成 `rank`。
- 低严重度：误把页面其他 `All/all` 文案当成 qlib all bucket 入口。
- 低严重度：watch draft 刷新测试最初使用新页面，不共享 localStorage；已改为同页 reload 并显式保留草稿。

上述均为测试脚本问题，未修改产品代码。

残余风险：

- 移动端仿真只检查关键区块可见和截图，不做像素级重叠自动判定。
- Playwright qlib API 使用 mock 响应覆盖 UI 状态，真实 artifact 后端读取通过第 14 场景单独覆盖。
- 前端 build 既有 warning 未收敛。

## 11. 是否偏离 research-only/read-only 主线

未偏离。证据：

- 危险请求总数为 0。
- `填入监控配置` 不保存配置、不扫描、不创建提醒。
- `回测验证` 不自动 POST backtest。
- wait-state/blocked/missing/stale/empty/API failure 均不显示可用信号表或交易建议。
- 页面没有出现买入、卖出、下单、自动交易、quick-trade、broker、target position 等入口。
- 真实 artifact smoke 只读调用 `QlibOptionCSignalReader`，未执行 qlib script、provider refresh、训练、调参或补数据。

## 12. 是否建议 Phase 2 最终收尾

建议 Phase 2 最终收尾。完整仿真覆盖正常用户路径、异常状态、localStorage 草稿、手动配置填充、只读回测入口、移动端窄屏和真实 artifact 读取；未发现只读边界破坏。后续如进入 Phase 3，应另开主线并继续保持 no broker/no quick-trade/no auto trading/no provider refresh 的最高优先级边界。
