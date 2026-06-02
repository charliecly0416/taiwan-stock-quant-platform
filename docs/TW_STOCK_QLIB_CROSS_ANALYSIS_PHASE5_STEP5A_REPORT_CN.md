---
created_at: 2026-06-02
status: execution_report
scope: quantdinger_tw_stock_qlib_cross_analysis_phase5_step5a_db_smoke_fix
role: executor
execution_doc: docs/TW_STOCK_QLIB_CROSS_ANALYSIS_PHASE5_STEP5A_EXECUTION_CN.md
audit_breakpoint: docs/TW_STOCK_QLIB_CROSS_ANALYSIS_PHASE5_STEP5A_REPORT_CN.md
---

# 台股 qlib 交叉分析 Phase 5 Step 5A 执行报告

## 1. 执行摘要

已完成 Step 5A：对 history/review service 的 PostgreSQL 兼容性做了 SQL 占位符审计，并在本地真实 PostgreSQL 上完成 import/review smoke。

本步骤未扩展产品能力，只新增一个受控 smoke 脚本：

```text
backend/scripts/smoke_tw_cross_analysis_step5a.py
```

结果：

```text
真实 PostgreSQL import-latest: pass
history runs/signals/alerts read: pass
review PUT/GET: pass
anonymous/user/admin 权限: pass
review smoke 数据清理: pass
```

## 2. SQL 占位符审计和修正

审计文件：

```text
backend/app/services/tw_stock_cross_analysis_history.py
backend/app/utils/db_postgres.py
```

结论：

```text
tw_stock_cross_analysis_history.py 仍使用 ? 占位符。
QuantDinger 当前 PostgreSQL cursor wrapper 会在执行前将 ? 转换为 %s。
真实 PostgreSQL smoke 已验证该转换在 history/review SQL 上可用。
```

相关实现：

```text
app.utils.db_postgres.PostgresCursor._convert_placeholders()
query = query.replace('?', '%s')
```

因此本轮未把 service SQL 全量改成 `%s`，原因是：

```text
1. 项目内大量既有代码依赖 ? 兼容层。
2. 真实 PG smoke 已覆盖本步骤新增 SQL。
3. 全量替换会与现有 fake DB 测试和项目 SQL 风格产生不必要差异。
```

`SCHEMA_SQL` 多语句建表也已通过真实 PG service `_ensure_schema()` 执行验证。

## 3. 真实 PostgreSQL smoke 结果

使用 DB：

```text
postgresql://user:password@127.0.0.1:5432/quantdinger
```

执行脚本：

```text
python backend/scripts/smoke_tw_cross_analysis_step5a.py
```

smoke 输出关键结果：

```json
{
  "ok": true,
  "anonymous_import_status": 401,
  "user_import_status": 403,
  "admin_import_status": 200,
  "run_id": "option_c_daily_signal_20260601_20260602T090715Z",
  "asof": "2026-06-01",
  "signals_count": 80,
  "alerts_count": 80,
  "runs_count": 1,
  "review_put_status": 200,
  "review_get_status": 200,
  "review_get_count": 1,
  "cleaned_reviews": 1
}
```

真实写入情况：

```text
qd_tw_qlib_signal_runs: 写入/更新 accepted run
qd_tw_qlib_signals: 写入/保留 80 条 top30/top50 research signals
qd_tw_qlib_signal_alerts: 写入/保留 80 条 research alerts
qd_tw_cross_analysis_reviews: 写入 1 条 smoke review，随后清理 1 条
```

history import 未清理原因：

```text
导入的是真实 accepted qlib research run，且 history import 是幂等研究历史。
保留该 run/signals/alerts 可作为后续真实历史研究数据，不是测试脏数据。
```

review smoke 已清理原因：

```text
review 使用 user_id=909005 和 note=Step 5A PostgreSQL smoke，仅用于验证 PUT/GET。
脚本结束时删除该 review 行，cleaned_reviews=1。
```

## 4. import-latest 权限复核

真实 PG smoke 覆盖：

```text
anonymous -> 401
普通 user -> 403
admin + confirm -> 200
```

confirm gate 仍保留：

```json
{
  "confirm_import_qlib_signal_history": true
}
```

## 5. review GET/PUT 复核

真实 PG smoke 覆盖：

```text
PUT /api/tw-stock/cross-analysis/reviews -> 200
GET /api/tw-stock/cross-analysis/reviews -> 200
review_get_count=1
```

返回 item keys：

```text
asof
created_at
cross_category
decision_status
id
research_signal_not_order
run_id
symbol
trading
updated_at
user_id
user_note
```

没有返回或写入订单、仓位、broker、target position 字段。

## 6. 前端历史模拟入口复核

执行：

```text
node tests/unit/tw-stock-cross-analysis-check.mjs
```

结果：

```text
tw-stock cross-analysis checks passed
```

检查覆盖：

```text
保存复盘 UI/API 存在
历史模拟入口存在
openCrossAnalysisHistoricalSimulation 不调用 runTwStockReadonlyBacktest
详情加载不自动调用 backtest
无买卖/下单/broker/paper/live/仓位文案
```

## 7. tests/build 结果

后端编译：

```text
python -m py_compile backend/scripts/smoke_tw_cross_analysis_step5a.py backend/app/services/tw_stock_cross_analysis_history.py backend/app/routes/tw_stock.py
```

结果：通过。

后端交叉分析/history/review：

```text
python -m pytest backend/tests/test_tw_stock_cross_analysis_service.py backend/tests/test_tw_stock_cross_analysis_api.py backend/tests/test_tw_stock_cross_analysis_history.py backend/tests/test_tw_stock_cross_analysis_review.py -q
```

结果：

```text
26 passed in 1.26s
```

后端 qlib signals/API 回归：

```text
python -m pytest backend/tests/test_tw_stock_qlib_option_c_signals.py backend/tests/test_tw_stock_quant_signal_api.py -q
```

结果：

```text
67 passed in 1.49s
```

前端：

```text
node tests/unit/tw-stock-cross-analysis-check.mjs
corepack pnpm build
```

结果：

```text
tw-stock cross-analysis checks passed
✓ built in 23.50s
```

build 仍有既有 CSS `/deep/`、dynamic import 和 chunk size warning；本步骤未新增这些 warning。

## 8. 是否触发 qlib ops/refresh/publish

否。

本步骤没有运行 qlib ops、refresh、publish、pipeline、automation、provider mutation 或模型重训。

## 9. 是否触发交易/订单/仓位

否。

smoke 返回 trading flags：

```json
{
  "orders_enabled": false,
  "connects_to_broker": false,
  "paper_orders_enabled": false,
  "live_trading_enabled": false,
  "quick_trade_enabled": false,
  "writes_orders": false,
  "writes_positions": false,
  "research_signal_not_order": true
}
```

补充说明：

```text
Flask app factory 启动时仍会按项目默认启动部分非 qlib 后台服务日志。
smoke 脚本已显式禁用 pending order worker、portfolio monitor、TWStock monitor worker、strategy restore、position sync 和 USDT worker。
app factory 仍启动既有 AI calibration/reflection worker，这是项目默认启动行为；本步骤未调用交易或 qlib ops API。
```

## 10. 风险和未解决问题

```text
1. history/review service 依赖 PostgresCursor 的 ? -> %s 兼容层；真实 PG smoke 已验证通过。
2. create_app(testing) 仍会启动既有 AI calibration/reflection worker；这不是 Step 5A 新增行为，但后续可考虑在 testing config 中统一禁用。
3. history import smoke 保留 accepted run/signals/alerts，符合研究历史语义；如审核要求完全隔离测试数据，可后续增加 dry-run fixture DB。
```

## 11. 是否建议 Phase 5 收尾

建议 Phase 5 收尾。

理由：

```text
1. cross-analysis latest/symbol 展示已完成。
2. freshness/basis 仪表盘已完成。
3. accepted history import 和 alerts 已完成并通过真实 PG smoke。
4. review GET/PUT 已完成并通过真实 PG smoke。
5. 前端历史模拟入口不自动运行回测。
6. no-trading / research-only 边界保持成立。
```
