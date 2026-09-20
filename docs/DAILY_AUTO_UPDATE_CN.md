# 台股每日自动更新闭环

本项目提供统一任务入口：

```bash
scripts/run_daily_env.sh python scripts/run_tw_task.py \
  --request configs/tasks/daily_update.yaml
```

入口先按 `schemas/tw_task_request.schema.json` 校验请求，再从
`configs/tw_task_registry.yaml` 选择固定的日更 executor。executor 最终委托
`scripts/run_daily_tw_stock_auto_update.py` 完成既有日更逻辑。旧脚本仍可用于
定位内部阶段问题，但日常运行和 cron 应使用统一入口。

默认行为：

- 自动选择 `Asia/Taipei` 当天日期作为 `asof`。
- 先用 FinMind 更新 QuantDinger raw 台股资料库。
- 再用 Yahoo/Scrapling 拉取 Option C 150 股票复权 OHLCV。
- 根据环境中的显式 gate 决定是否进入 legacy qlib provider publish 与
  `accepted latest` 切换；源码默认关闭这些写路径。
- 生成并校验 ModelSignal、只读快照和 Agent 所需的日更产物；具体 publish
  权限仍由原日更 orchestrator 的 gate 控制。
- 全程研究用途，不连接券商，不生成订单，不写仓位。


## 是否需要手动运行

任务入口已经放在项目里，但自动执行需要安装一次系统计划任务。

- 我们可以把 cron/systemd 模板写进项目配置文件。
- 你或部署脚本需要在实际运行机器上安装一次计划任务，例如 `crontab docs/tw-daily-auto-update.cron.example`。
- 安装后不需要每天手动运行，系统会按配置自动执行。

项目已提供 cron 模板：

```text
docs/tw-daily-auto-update.cron.example
```

使用前把模板里的 `PROJECT_ROOT` 和 `PYTHON` 改成真实路径。模板显式使用
`CRON_TZ=Asia/Taipei`，并通过 `scripts/run_daily_env.sh` 安全加载
`backend/.env`。

## 跨午夜 pending asof

脚本会维护：

```text
data_tw/ops/daily_auto_update/pending_asof.json
```

如果当天 22:30 仍然没有拉到完整 Yahoo/Scrapling 数据，脚本会把当天日期写入 `pending_asof.json`。第二天 00:30、02:30、04:30 再运行时，会优先继续拉这个 pending 日期，而不是直接跳到第二天。成功发布 accepted latest 后，pending 文件会自动清除。

## 定时运行

建议每天台北时间 16:30 以后执行。Yahoo/FinMind 偶尔会延迟，如果返回 `fresh_data_wait`，下一次定时任务会自动重试。

cron 示例，每 2 小时运行轻量 base lane，跨午夜继续重试 pending 日期；
工作日 22:45 运行一次 full lane：

```cron
CRON_TZ=Asia/Taipei
30 16,18,20 * * 1-5 cd /path/to/taiwan-stock-quant-platform && flock -n data_tw/ops/daily_auto_update.lock scripts/run_daily_env.sh /path/to/python scripts/run_tw_task.py --request configs/tasks/daily_update_base.yaml >> data_tw/ops/daily_auto_update/cron.log 2>&1
30 0,2,4 * * 2-6 cd /path/to/taiwan-stock-quant-platform && flock -n data_tw/ops/daily_auto_update.lock scripts/run_daily_env.sh /path/to/python scripts/run_tw_task.py --request configs/tasks/daily_update_base.yaml >> data_tw/ops/daily_auto_update/cron.log 2>&1
45 22 * * 1-5 cd /path/to/taiwan-stock-quant-platform && flock data_tw/ops/daily_auto_update.lock scripts/run_daily_env.sh /path/to/python scripts/run_tw_task.py --request configs/tasks/daily_update.yaml >> data_tw/ops/daily_auto_update/cron.log 2>&1
```

full lane 使用等待锁，base lane 使用非等待锁；因此唯一的 full 班次不会因
前一班 base 尚未结束而静默跳过，跨午夜 base 则会在 full 正在运行时跳过。

## 常用参数

```bash
# 指定日期补跑
cp configs/tasks/daily_update.yaml /tmp/tw-daily-update.yaml
# 把 /tmp/tw-daily-update.yaml 中 parameters.asof 改成 2026-06-02，再运行：
scripts/run_daily_env.sh python scripts/run_tw_task.py --request /tmp/tw-daily-update.yaml

# 只检查配置、依赖和最终执行计划，不执行抓取或模型：
python scripts/run_tw_task.py --request configs/tasks/daily_update.yaml --validate-only

# 内部 executor 排错入口；正常运维不要绕过统一入口：
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-02 --force

# 只更新 FinMind/QuantDinger raw，不跑 qlib
python scripts/run_daily_tw_stock_auto_update.py --skip-qlib

# 只跑 Yahoo/Scrapling + qlib，不跑 FinMind raw
python scripts/run_daily_tw_stock_auto_update.py --skip-finmind

# FinMind 只补 daily bars，跳过法人、融资融券、营收、估值等扩展数据
python scripts/run_daily_tw_stock_auto_update.py --finmind-scope daily
```

## 数据口径

- qlib 主链路使用 Yahoo/Scrapling 复权价格，避免混用不同复权口径。
- FinMind/TWSE 写入 QuantDinger raw 数据库，用于趋势、K 线、交叉分析和展示。
- 当前脚本不会把 FinMind raw 价格混入 qlib provider；如果 Yahoo 当天数据不可用，脚本会等待下次重试，而不是 silently mixed fallback。

## 审计报告

每次运行都会生成：

```text
data_tw/ops/daily_auto_update/<job_id>/job.json
data_tw/ops/daily_auto_update/<job_id>/finmind_stdout.txt
data_tw/ops/daily_auto_update/<job_id>/refresh_report.md
data_tw/ops/daily_auto_update/<job_id>/publish_report.md
```

关键状态：

- `daily_auto_update_passed`：FinMind/Yahoo/qlib/latest 全链路通过。
- `already_up_to_date`：latest 已经是目标日期，没有重复执行。
- `fresh_data_wait`：Yahoo/Scrapling 暂未拿到完整目标日期数据，下次定时重试。
- `provider_publish_failed`：provider 发布失败，latest 不更新。
- `accepted_latest_failed`：信号产物或发布门禁失败，latest 不更新。


## FinMind 历史覆盖

默认 `TW_DAILY_AUTO_FINMIND_LOOKBACK_DAYS=260`，用于给 Option C 150 候选池补足约 120 根以上日线，避免交叉分析因本地日线样本不足而降级。可用 `--finmind-lookback-days` 覆盖。

如果 FinMind 历史接口受额度或付费限制影响，可用本地 Yahoo/Scrapling 标准化文件补齐同一张归档表：

```bash
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<db> \
python backend/scripts/import_tw_stock_yahoo_normalized_archive.py \
  --symbols-file qlib_pipeline/data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt \
  --start 2025-09-18 \
  --end 2026-06-05 \
  --apply
```

该脚本只读取本地 `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWxxxx.csv`，写入 `qd_tw_stock_daily_bars` 的 `source='yahoo_adjusted'`，用于趋势样本补足，不会触发交易、下单或券商操作。
