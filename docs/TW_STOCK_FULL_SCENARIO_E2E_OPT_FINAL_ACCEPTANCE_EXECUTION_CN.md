# 台股全场景 E2E 优化最终验收执行文档

生成时间：2026-06-04

## 1. 本步目标

对 `TW_STOCK_FULL_SCENARIO_E2E_OPT` 系列工作做最终收尾验收，不再新增业务功能。目标是确认 Step1-Step5 的后端状态 API、前端状态面板、console 清理、watchlist 回填修复、全场景只读 Playwright E2E 已形成稳定闭环，并明确哪些场景由 fixture E2E 覆盖，哪些场景由真实只读数据检查覆盖。

## 2. 验收范围

必须确认：

- 每日自动更新状态 API 仍为只读。
- 前端每日自动更新状态面板只展示状态，不触发拉数、publish、accepted latest 切换。
- `tw-stock-monitor` 页面没有危险交易入口泄漏。
- watchlist 草稿可以回填到监控配置 drawer，但不保存、不扫描、不新增 alerts 写入。
- 全场景 E2E 脚本已入库并可重复运行。
- E2E 输出 `summary.json`、`network_audit.json`、`console_audit.json` 和截图。
- 网络审计中禁止请求数量为 0。
- console 审计中除已知 Ant Design lazy-load notice 外无 warning/error。

## 3. 必跑命令

```bash
cd backend
python -m pytest tests/test_tw_stock_daily_auto_update_status.py -q
```

```bash
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-daily-auto-update-panel-check.mjs
node tests/unit/tw-stock-console-clean-check.mjs
node tests/unit/tw-stock-watchlist-draft-check.mjs
node tests/e2e/tw-stock-full-scenario-readonly.mjs
corepack pnpm build
```

如果本地服务不是默认端口，运行 E2E 时显式传入：

```bash
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 \
TW_STOCK_MONITOR_USERNAME=quantdinger \
TW_STOCK_MONITOR_PASSWORD=123456 \
TW_STOCK_FULL_E2E_ARTIFACT_DIR=../data_tw/ops/e2e_full_scenario/final-acceptance \
node tests/e2e/tw-stock-full-scenario-readonly.mjs
```

## 4. 真实只读数据边界确认

本次最终验收需要补一段文字说明，不要求新增复杂脚本：

- fixture E2E 验证的是前端闭环、交互稳定性、只读安全边界。
- 真实 Yahoo/Scrapling/FinMind 是否更新到最新交易日，应由每日自动更新 runner、accepted latest 文件、daily auto update status API 的真实运行结果确认。
- 不应把真实数据拉取、provider publish、accepted latest 切换放进浏览器 E2E 自动测试路径。

如执行者环境具备真实服务和数据，可额外只读检查：

- 打开 `/api/tw-stock/quant/ops/daily-auto-update/status`。
- 打开 `/api/tw-stock/quant/signals/latest?bucket=top30`。
- 确认返回的 `latest_asof`、`status`、`run_id` 与当前 accepted latest 文件一致。

该检查只允许 GET，不允许触发任何更新任务。

## 5. 最终验收报告

执行者完成后提交：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_FINAL_ACCEPTANCE_CN.md
```

报告必须包含：

- Step1-Step5 文件清单与功能摘要。
- 所有必跑命令结果。
- E2E 产物路径。
- `summary.json` 摘要。
- `network_audit.json` 摘要。
- `console_audit.json` 摘要。
- 是否有真实只读数据检查结果。
- 是否建议合并/提交/收尾。

## 6. 收尾标准

满足以下条件即可收尾：

- 所有必跑测试通过。
- 全场景 E2E `overall_passed=true`。
- 禁止请求数量为 0。
- 无非 allowlist console warning/error。
- 没有新增业务功能需求或未解决阻塞。
- 报告清楚说明 fixture E2E 与真实数据更新验证的职责边界。
