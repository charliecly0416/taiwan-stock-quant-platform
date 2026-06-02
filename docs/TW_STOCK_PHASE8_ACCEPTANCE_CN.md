# 台股趋势监控 Phase 8 验收报告

更新时间：2026-05-24

## 1. 验收结论

Phase 8 可验收完成。

本阶段围绕“安全边界与持续验收自动化”推进，把台股研究栈的红线固化到测试、PR checklist 和 GitHub Actions 中。安全边界保持不变：只做台股趋势研究、自动监控提醒、人工复盘和人工决策；不自动买卖，不连接 IBKR 或任何 broker，不提交 paper/live order。

## 2. 已完成能力

### Phase 8A：安全边界自动化审计

- 新增 `backend/tests/test_tw_stock_monitor_safety_audit.py`。
- 自动扫描台股监控研究路径源码。
- 禁止导入或调用 quick-trade、IBKR、live trading、order submission、paper order pipeline 等交易层入口。
- 确认关键输出继续包含 `orders_enabled=false`。

### Phase 8B：一键验收脚本

- 新增 `backend/scripts/verify_tw_stock_research_stack.py`。
- 默认运行台股研究栈 pytest 验收集。
- 可选 `--with-page-smoke` 运行 Playwright 截图 smoke。
- 输出 JSON 汇总，并固定包含：
  - `orders_enabled=false`
  - `writes_production_data=false`
  - `connects_to_broker=false`

### Phase 8C：GitHub Actions CI 接入

- 新增 `.github/workflows/tw-stock-research.yml`。
- 台股相关代码、脚本、测试或文档变更时自动运行离线验收。
- CI 默认只跑 pytest 验收集，不跑 `--with-page-smoke`。
- 不安装浏览器、不启动服务、不依赖外部行情、不写生产数据、不连接 broker。
- CI 环境固定关闭 live/worker：
  - `AGENT_LIVE_TRADING_ENABLED=false`
  - `ENABLE_PENDING_ORDER_WORKER=false`
  - `ENABLE_PORTFOLIO_MONITOR=false`
  - `ENABLE_TW_STOCK_MONITOR_WORKER=false`

### Phase 8D：PR 安全 Checklist

- 更新 `.github/PULL_REQUEST_TEMPLATE.md`。
- 新增 `TWStock Research Safety` checklist。
- 涉及台股研究栈的 PR 需要确认：
  - 已运行 `verify_tw_stock_research_stack.py` 或确认 CI 覆盖。
  - 未默认启用 `AGENT_LIVE_TRADING_ENABLED` 或台股 monitor worker。
  - 未把台股 monitor/research 路径接到 broker、IBKR、quick-trade、paper/live order submission 或 live trading execution。
  - universe/config 导入仍保持人工审核优先，并在 apply 前 dry-run/preflight。
- 新增 `backend/tests/test_pr_template_safety_checklist.py`，并纳入一键验收默认测试集。

### Phase 8E：CI 触发范围修正

- `.github/workflows/tw-stock-research.yml` 的 path filter 已覆盖：
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - `backend/tests/test_pr_template_safety_checklist.py`
  - `backend/tests/test_tw_stock_research_workflow.py`
- 这样 PR 模板安全 checklist 或 workflow 静态测试本身变化时，也会触发台股研究栈 CI。

## 3. 验收测试

一键验收：

```bash
PYTHONPATH=backend python   backend/scripts/verify_tw_stock_research_stack.py
```

本轮结果：`ok=true`，`46 passed`，`orders_enabled=false`，`writes_production_data=false`，`connects_to_broker=false`。

页面 smoke 可选验收：

```bash
PYTHONPATH=backend python   backend/scripts/verify_tw_stock_research_stack.py   --with-page-smoke   --screenshot /tmp/tw_stock_monitor_phase8b.png
```

新增/变更项专项测试：

```bash
python -m pytest   backend/tests/test_tw_stock_monitor_safety_audit.py   backend/tests/test_verify_tw_stock_research_stack.py   backend/tests/test_tw_stock_research_workflow.py   backend/tests/test_pr_template_safety_checklist.py   -q
```

## 4. 安全边界

验收期间确认：

- 没有提交 paper order。
- 没有提交 live order。
- 没有连接 IBKR。
- 没有调用 broker client。
- 没有调用 quick-trade 路径。
- CI 不启动服务、不安装浏览器、不跑 live/external data tests。
- 一键验收输出固定声明不写生产数据、不连接 broker。

## 5. 后续建议

1. 若后续加入正式 Vue 台股页面，可新增独立 frontend/e2e workflow，不要混入当前离线 CI。
2. 若新增 Telegram/Email 台股外部通知，先扩展安全审计 forbidden patterns 和 PR checklist。
3. 若未来重启 paper/live 台股交易链路，应新开独立 Phase，不复用当前研究监控 CI 的安全边界。
