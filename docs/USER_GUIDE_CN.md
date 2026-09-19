# Taiwan Stock Quant Platform 使用文档

## 1. 环境要求

建议环境：

- Python 3.10+
- PostgreSQL 14+
- Node.js 20+ 或 22+
- corepack + pnpm
- 可访问 Yahoo Finance 和 FinMind 的网络
- 可选：FinMind token

项目根目录以下用 `$PROJECT_ROOT` 表示：

```bash
cd /path/to/taiwan-stock-quant-platform
```

## 2. 初始化配置

复制环境变量模板：

```bash
cp .env.example .env
```

至少检查这些配置：

```bash
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger
SECRET_KEY=<自行生成的持久随机密钥>
ADMIN_USER=<你的管理员用户名>
ADMIN_PASSWORD=<自行设置的密码>
FINMIND_TOKEN=

QLIB_TW_OPTION_C_ROOT=../qlib_pipeline/data_tw/experiments/option_c_daily_signal
TW_QLIB_OPTION_C_CWD=../qlib_pipeline
TW_QLIB_OPTION_C_PROVIDER_CALENDAR=../qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt
```

如果没有 FinMind token，也可以先运行；但 token 有助于提高稳定性和额度。

用 `python -c "import secrets; print(secrets.token_hex(32))"` 生成密钥后设置到 `.env`，不要提交真实凭证。CLI 与 Gunicorn 启动都会拒绝缺失或示例签名密钥。研究模式默认不启动订单派发、持仓监控和运行策略恢复；开启继承的交易模块属于独立部署范围。

## 3. 安装后端依赖

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

启动后端：

```bash
python run.py
```

默认地址：

```text
http://127.0.0.1:5000
```

为了保持研究安全边界，生产研究模式建议显式关闭后台交易相关 worker：

```bash
ENABLE_PENDING_ORDER_WORKER=false
ENABLE_PORTFOLIO_MONITOR=false
ENABLE_TW_STOCK_MONITOR_WORKER=false
DISABLE_RESTORE_RUNNING_STRATEGIES=true
POSITION_SYNC_ENABLED=false
USDT_PAY_ENABLED=false
```

## 4. 安装前端依赖

```bash
cd frontend
corepack enable
corepack pnpm install
```

启动前端：

```bash
VITE_DEV_PROXY_TARGET=http://127.0.0.1:5000 corepack pnpm dev
```

默认地址：

```text
http://127.0.0.1:8000
```

访问：

```text
http://127.0.0.1:8000/#/tw-stock-monitor
```

## 5. 准备 qlib 生产资产

如果本机有原生产 qlib 资产，可以运行：

```bash
python scripts/bootstrap_full_production_assets.py --replace
python scripts/verify_full_production_loop.py
```

这会把本机生产资产复制到项目 ignored 目录，并验证：

- Option C 150 normalized 数据
- qlib provider
- accepted latest
- 后端 qlib reader
- qlib provider dry-run

如果没有原资产，需要使用仓库内 Yahoo/Scrapling、dump、signal 脚本重新生成，或从 GitHub Release artifact/对象存储解压到：

```text
qlib_pipeline/data_tw/
qlib_pipeline/mlruns/
```

## 6. 验证闭环

生产资产验证：

```bash
python scripts/verify_full_production_loop.py
```

轻量 demo 验证：

```bash
python scripts/verify_self_contained_closed_loop.py
```

前端静态检查：

```bash
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-agent-panel-check.mjs
node tests/unit/tw-stock-cross-analysis-check.mjs
node tests/unit/tw-stock-monitor-qlib-ops-check.mjs
corepack pnpm build
```

## 7. 每日自动更新

每日无人值守入口：

```bash
python scripts/run_daily_tw_stock_auto_update.py
```

源码默认与这台机器的已安装 cron 配置不同。源码默认会：

- 自动选择台北当天日期
- 如果存在 pending 日期，优先重试 pending 日期
- 更新 FinMind/QuantDinger raw 数据
- 记录 job、readiness 与 pending 状态
- legacy provider publish 和 accepted latest 切换默认关闭；只在明确授权和配置下运行

本机自动化使用两小时 daily lane 与工作日台北 22:45 full lane；full lane 启用 B19R2R 自动影子。Model A 是当前默认模型，A+B 只用于研究比较和独立影子积累。完整配置以实际 `crontab -l` 和 runbook 为准，不应仅凭模板推定全链成功。

常用命令：

```bash
# 指定日期补跑
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-02

# latest 已经是当天时仍强制重跑
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-02 --force

# 只更新 FinMind/QuantDinger raw
python scripts/run_daily_tw_stock_auto_update.py --skip-qlib

# --skip-finmind 不能绕过 same-run handoff；缺少抓取证据会阻断。

# FinMind 只补 daily bars
python scripts/run_daily_tw_stock_auto_update.py --finmind-scope daily
```

## 8. 安装定时任务

项目提供 cron 模板：

```text
docs/tw-daily-auto-update.cron.example
```

先编辑模板里的路径：

```text
PROJECT_ROOT=/path/to/taiwan-stock-quant-platform
```

安装：

```bash
# 先检查已有 crontab，并合并模板中的任务，避免覆盖其他已安装任务。
crontab -l
```

历史模板的调度示例：

- 台北时间周一到周五 16:30、18:30、20:30、22:30 尝试
- 次日 00:30、02:30、04:30 继续尝试
- 如果当天数据没拉到，写入 pending
- 跨午夜后继续优先处理 pending
- 成功后自动清除 pending

## 9. 查看每日更新结果

每次运行都会生成：

```text
data_tw/ops/daily_auto_update/<job_id>/job.json
data_tw/ops/daily_auto_update/<job_id>/finmind_stdout.txt
data_tw/ops/daily_auto_update/<job_id>/refresh_report.md
data_tw/ops/daily_auto_update/<job_id>/publish_report.md
```

常见状态：

- `daily_auto_update_passed`：全链路成功。
- `already_up_to_date`：目标日期 latest 已存在，本轮跳过。
- `fresh_data_wait`：Yahoo/Scrapling 目标日期数据尚未完整，下次继续。
- `provider_publish_failed`：provider 发布失败，latest 不更新。
- `accepted_latest_failed`：accepted latest 门禁失败，latest 不更新。

pending 文件：

```text
data_tw/ops/daily_auto_update/pending_asof.json
```

如果存在，说明系统会在下一次定时任务继续优先处理该日期。

## 10. 前端使用

进入台股研究页面后，优先看这些区域：

- 当前榜单：先看今日 Top30/Top50、模型日期、行情日期、榜首标的和数据提示。
- 今日复盘与历史模拟：系统会把候选压缩成“今天先看什么”“为什么”“过去表现”三个用户视角区块。
- 台股交叉分析：看 qlib 排名、QuantDinger 趋势、MA/RSI/MACD/Bollinger 技术状态和价格位置风险是否一致。
- K 线图：可搜索或从 Top30/Top50 选择股票查看 K 线、均线、量能和模拟交易 marker。
- 台股研究助手：自然语言查询 Top30、趋势指标、数据口径和研究解释。

当前普通用户页面不再主展示数据状态、历史研究 run、dry-run 等维护型信息。旧 full-scenario E2E 脚本只作为历史测试资产，不再作为当前页面一键验收标准。

页面中的研究结果只用于人工复盘，不是交易建议。

### 当前 5 个组合策略

策略回放区只保留 5 个主策略：

| 策略 | 说明 |
| --- | --- |
| 跌出 Top30 轮动 | 持仓跌出 Top30 时风险减少，再从 Top10 补入，反应较快。 |
| 跌出 Top50 轮动 | 持仓跌出 Top50 才风险减少，换手更低。 |
| Top50 自适应 score | 正常市况不干预 Top50 轮动；谨慎/下跌市况使用 score 区间过滤补仓。 |
| Top50 自适应 score + 风控 | 高级对照，市场差且组合回撤扩大时暂停补仓。 |
| 连续转弱才复盘 | 不因单日噪声退出，连续转弱后才风险复盘。 |

这些策略都是只读历史模拟，不写模拟账户，不连接 broker，不生成订单。

## 11. Agent 使用

可问：

```text
今天 top30 是哪些？
今天模型和趋势都支持的股票有哪些？
今天建议人工复盘的股票有哪些？
2330 的指标是多少？
当前数据新鲜度如何？
```

不支持：

```text
帮我下单
给我仓位
自动买入第一名
承诺明天上涨概率
```

这些问题会被研究边界阻断。

## 12. 常见问题

### latest 没更新

先看：

```bash
cat data_tw/ops/daily_auto_update/*/job.json
```

重点检查：

- `fresh_data_wait`
- `provider_publish_failed`
- `accepted_latest_failed`
- `pending_asof_set`

### Yahoo 当天数据还没有

这是正常情况。系统会写 pending，下一次 cron 自动重试。

### FinMind 成功但 qlib 没更新

FinMind raw 和 qlib Yahoo/Scrapling 是两条不同口径链路。FinMind 成功只能说明 QuantDinger raw 数据补上了；qlib latest 仍依赖 Yahoo/Scrapling 复权数据完整。

### 前端看不到最新日期

检查：

```bash
cat qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
```

确认：

- `status=accepted`
- `asof` 是目标日期
- `top30_signals` 文件存在

然后重启后端或刷新前端页面。

### 不想跑完整 FinMind 扩展数据

使用：

```bash
python scripts/run_daily_tw_stock_auto_update.py --finmind-scope daily
```

这样只补 daily bars，速度更快。

## 13. 发布到 GitHub

建议提交：

- 源码
- 配置模板
- 文档
- 测试
- crawler/qlib/backend/frontend 脚本

不建议提交：

- `data_tw/`
- `qlib_pipeline/data_tw/`
- `qlib_pipeline/mlruns/`
- `frontend/dist/`

大型数据和模型建议用 GitHub Release artifact 或对象存储交付。


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
