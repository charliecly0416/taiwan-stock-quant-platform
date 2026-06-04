# 全场景 E2E 优化 Step 1 报告：自动更新状态后端 API

生成时间：2026-06-03
对应计划：`docs/TW_STOCK_FULL_SCENARIO_E2E_OPTIMIZATION_PLAN_CN.md` Step 1
说明：用户提到的 `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_ACCEPTANCE_CN.md` 当前工作区不存在，本轮按优化计划文档中的 Step 1 验收标准执行。

## 1. 本步目标

新增只读后端 API，将每日自动更新状态从本地文件和日志中结构化暴露出来，供后续前端状态面板使用。

新增接口：

```text
GET /api/tw-stock/quant/ops/daily-auto-update/status
```

该接口只读，不触发 FinMind/Yahoo 拉取，不触发 qlib provider rebuild，不触发 accepted latest publish，不连接 broker，不下单。

## 2. 新增/修改文件

新增：

- `backend/app/services/tw_stock_daily_auto_update_status.py`
- `backend/tests/test_tw_stock_daily_auto_update_status.py`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP1_REPORT_CN.md`

修改：

- `backend/app/routes/tw_stock.py`

## 3. API 返回内容

接口会读取：

- `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`
- `data_tw/ops/daily_auto_update/pending_asof.json`
- `data_tw/ops/daily_auto_update/*/job.json` 中最新 job
- `data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron`
- `data_tw/ops/daily_auto_update/cron.log` 最近若干行，如果存在

核心字段：

- `latest_asof`
- `latest_status`
- `latest_run_id`
- `pending_asof`
- `pending_reason`
- `last_job_id`
- `last_job_status`
- `last_job_started_at`
- `last_job_finished_at`
- `finmind_update_status`
- `finmind_archived_count`
- `yahoo_target_asof`
- `yahoo_date_max`
- `yahoo_missing_asof_count`
- `fresh_data_wait`
- `next_retry_hint`
- `cron_installed_hint`
- `trading`
- `warnings`

## 4. 当前真实数据示例响应摘要

只读调用 service 得到当前环境摘要：

```json
{
  "latest_asof": "2026-06-02",
  "latest_status": "accepted",
  "latest_run_id": "option_c_daily_signal_20260602_20260603T031450Z",
  "pending_asof": "2026-06-03",
  "pending_reason": "fresh_data_wait",
  "last_job_id": "daily_tw_stock_auto_update_20260603_20260603T171533Z",
  "last_job_status": "fresh_data_wait",
  "finmind_update_status": "success",
  "finmind_archived_count": 1200,
  "yahoo_target_asof": "2026-06-03",
  "yahoo_date_max": "2026-06-02",
  "yahoo_missing_asof_count": 150,
  "fresh_data_wait": true,
  "next_retry_hint": "pending asof 2026-06-03 will be retried by the installed schedule; reason=fresh_data_wait",
  "cron_installed_hint": true,
  "warnings": []
}
```

研究安全 flags：

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

## 5. 测试命令与结果

语法检查：

```bash
python -m py_compile backend/app/services/tw_stock_daily_auto_update_status.py backend/app/routes/tw_stock.py backend/tests/test_tw_stock_daily_auto_update_status.py
```

结果：通过。

单元测试：

```bash
python -m pytest backend/tests/test_tw_stock_daily_auto_update_status.py
```

结果：

```text
collected 5 items
backend/tests/test_tw_stock_daily_auto_update_status.py ..... [100%]
5 passed
```

覆盖场景：

- 无 job 时返回空状态且 HTTP API 可用。
- latest 已成功时返回 latest asof/run_id。
- pending asof 存在时返回 pending reason。
- `fresh_data_wait` 时返回 Yahoo 目标日期、当前最大日期、缺失数量和重试提示。
- `job.json` 损坏或缺字段时降级返回 warning，不抛出 500。
- API 返回 HTTP 200，且包含研究安全 flags。

## 6. 是否触发写操作

本轮业务功能实现没有触发任何数据更新、拉取、发布或交易写操作。

测试中只在 pytest 的 `tmp_path` 临时目录构造 fake latest/pending/job/cron 文件，用于验证解析逻辑。没有创建、修改或删除真实数据文件。

新增 API 本身只读取文件：

- 不写 `pending_asof.json`
- 不写 job
- 不写 cron
- 不运行 FinMind/Yahoo 脚本
- 不运行 qlib 脚本
- 不更新 latest signal
- 不连接 broker
- 不生成订单

## 7. 发现的数据状态

当前真实状态不是系统失败，而是正确的等待态：

- latest accepted 仍为 `2026-06-02`
- pending asof 为 `2026-06-03`
- FinMind daily raw 更新成功，`archived_count=1200`
- Yahoo/Scrapling 目标 asof 为 `2026-06-03`
- Yahoo/Scrapling 当前最大日期为 `2026-06-02`
- `yahoo_missing_asof_count=150`
- `fresh_data_wait=true`
- cron 已安装，后续会继续重试 pending asof

这正是 Step 2 前端状态面板需要展示给用户的信息。

## 8. 验收结论

Step 1 已完成。

- API 可返回 HTTP 200。
- pending asof 可正确显示。
- latest asof/run_id 可正确显示。
- fresh_data_wait 可正确解释为等待 Yahoo/Scrapling 目标日期数据。
- 返回研究安全 flags。
- 后端测试通过。
- 未触发任何真实数据写操作。
