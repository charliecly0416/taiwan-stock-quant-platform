---
created_at: 2026-06-02
status: handoff_guide
scope: quantdinger_tw_stock_yahoo_only_scrapling_data_fetch
source_project: /home/chuliyang/Scrapling/qlib_scrapling_handoff
related_project: /home/chuliyang/qlib
target_project: /path/to/taiwan-stock-quant-platform
---

# QuantDinger 台股 Yahoo-only 数据抓取：Scrapling 使用说明

本文档面向 QuantDinger 项目的 Codex，说明当 `yfinance` 抓取 Yahoo Finance 台股数据遇到：

```text
YFRateLimitError: Too Many Requests
```

或批量返回空数据时，如何参考 `Scrapling` 项目中已经验证过的方法，改用 Yahoo Finance chart API + Scrapling 拉取 Yahoo-only 台股日线数据。

核心结论：

```text
不要把 yfinance rate limit 当成 Yahoo 没有数据。
qlib 项目此前已经验证：yfinance 可能 all-empty，但 Yahoo chart API 经 Scrapling + Chrome impersonation 仍能拿到可用台股日线。
QuantDinger 若需要 Yahoo-only 数据，应先用 Scrapling 抓到隔离 candidate 目录，验证通过后再决定是否导入本项目。
```

---

## 1. 适用场景

适合使用 Scrapling 的场景：

1. `yfinance` 批量抓台股时报 `YFRateLimitError: Too Many Requests`。
2. `yfinance` 没有明确错误但返回全空或大面积空数据。
3. 需要保持 Yahoo-only 口径，不想切到 FinMind。
4. 需要拉取 `.TW` 和 `.TWO` 两类台股 ticker。
5. 需要产出 qlib/QuantDinger 可验证的 normalized daily CSV。

不适合直接使用的场景：

1. 实时行情。
2. 分钟线、高频数据。
3. 交易执行或订单生成。
4. 自动覆盖生产数据。
5. 混合 Yahoo + FinMind 后还声称 Yahoo-only。

---

## 2. Scrapling 方法和 yfinance 的区别

`yfinance` 是一个封装库，遇到 Yahoo 限流、cookie/crumb、请求策略变化时，可能出现 Too Many Requests 或全空结果。

Scrapling 方法不是调用 `yfinance.download()`，而是直接请求 Yahoo Finance chart API：

```text
https://query1.finance.yahoo.com/v8/finance/chart/{ticker}
```

并通过 Scrapling：

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get(
    url,
    params=params,
    proxy="http://127.0.0.1:7890",
    timeout=30,
    retries=1,
    impersonate="chrome",
)
payload = page.json()
```

关键点：

```text
impersonate="chrome"
低并发
可配置 proxy
每个 symbol 间 sleep
失败记录到 report
输出隔离 candidate 文件
```

qlib 侧此前使用该路径成功抓取 150 支 Option C formal universe：

```text
source_policy = Yahoo Finance chart API only, via Scrapling
symbols_success = 150
candidate_files = 150
validation_status = pass
```

参考报告：

```text
/home/chuliyang/qlib/docs/tw_audit/92_option_c_yahoo_scrapling_candidate_output_report.md
```

---

## 3. 相关项目路径

Scrapling handoff 项目：

```text
/home/chuliyang/Scrapling/qlib_scrapling_handoff
```

核心脚本：

```text
/home/chuliyang/Scrapling/qlib_scrapling_handoff/scripts/crawl_yahoo_scrapling.py
/home/chuliyang/Scrapling/qlib_scrapling_handoff/scripts/validate_output.py
```

数据契约：

```text
/home/chuliyang/Scrapling/qlib_scrapling_handoff/docs/DATA_CONTRACT.md
```

命令示例：

```text
/home/chuliyang/Scrapling/qlib_scrapling_handoff/examples/COMMANDS.md
```

qlib 中已成功使用 Scrapling 的审查记录：

```text
/home/chuliyang/qlib/docs/tw_audit/90_option_c_yahoo_scrapling_candidate_output_work_order.md
/home/chuliyang/qlib/docs/tw_audit/92_option_c_yahoo_scrapling_candidate_output_report.md
/home/chuliyang/qlib/docs/tw_audit/94_option_c_yahoo_scrapling_formal_ingestion_work_order.md
/home/chuliyang/qlib/docs/tw_audit/96_option_c_yahoo_scrapling_formal_ingestion_report.md
```

---

## 4. 输出数据格式

Scrapling Yahoo crawler 输出的是 one-file-per-symbol normalized CSV：

```text
TW2330.csv
TW2317.csv
TW6488.csv
```

固定列顺序：

```csv
symbol,date,open,high,low,close,volume,vwap,factor
```

字段含义：

| 字段 | 含义 |
| --- | --- |
| `symbol` | qlib 风格台股代码，如 `TW2330` |
| `date` | `YYYY-MM-DD` |
| `open` | Yahoo 复权 open |
| `high` | Yahoo 复权 high |
| `low` | Yahoo 复权 low |
| `close` | Yahoo 复权 close |
| `volume` | Yahoo volume，股数，不是张数 |
| `vwap` | 因 Yahoo chart API 无成交金额，使用复权 OHLC 平均值 |
| `factor` | `Adj Close / Close` |

当前脚本的复权策略：

```text
factor = Yahoo adjclose / Yahoo close
open = raw_open * factor
high = raw_high * factor
low = raw_low * factor
close = raw_close * factor
volume = raw volume unchanged
vwap = average(adjusted open/high/low/close)
```

注意：

```text
这是 Yahoo-only adjusted 口径。
不要把它和 FinMind raw/adjusted 数据混在同一个“Yahoo-only”结论里。
```

---

## 5. 环境准备

确认当前 Python 环境有依赖：

```bash
python -c "from scrapling.fetchers import Fetcher; import pandas as pd; print(Fetcher); print(pd.__version__)"
```

如果缺失依赖：

```bash
pip install scrapling pandas
```

如果机器需要代理，可以使用本地代理，例如：

```text
http://127.0.0.1:7890
```

不要把代理账号、密码、cookie 或 token 写入仓库文件。

---

## 6. 最小 smoke：抓一个 symbol

建议先在 QuantDinger 项目根目录执行隔离 smoke。

```bash
cd /path/to/taiwan-stock-quant-platform
mkdir -p data/tw_yahoo_scrapling_smoke/normalized data/tw_yahoo_scrapling_smoke/reports

python /home/chuliyang/Scrapling/qlib_scrapling_handoff/scripts/crawl_yahoo_scrapling.py \
  --symbol TW2330 \
  --start 2026-05-01 \
  --end 2026-06-01 \
  --output-dir data/tw_yahoo_scrapling_smoke/normalized \
  --report-file data/tw_yahoo_scrapling_smoke/reports/crawl_report.json \
  --proxy http://127.0.0.1:7890 \
  --sleep-seconds 0.5 \
  --continue-on-error \
  --suffix auto
```

如果没有代理或代理不可用，可尝试：

```bash
python /home/chuliyang/Scrapling/qlib_scrapling_handoff/scripts/crawl_yahoo_scrapling.py \
  --symbol TW2330 \
  --start 2026-05-01 \
  --end 2026-06-01 \
  --output-dir data/tw_yahoo_scrapling_smoke/normalized \
  --report-file data/tw_yahoo_scrapling_smoke/reports/crawl_report.json \
  --proxy "" \
  --sleep-seconds 1.0 \
  --continue-on-error \
  --suffix auto
```

smoke 成功后应看到：

```text
data/tw_yahoo_scrapling_smoke/normalized/TW2330.csv
data/tw_yahoo_scrapling_smoke/reports/crawl_report.json
```

`crawl_report.json` 中应有：

```text
symbols_requested = 1
symbols_success = 1
symbols_empty = []
rows_written > 0
```

---

## 7. 批量抓取 symbol 文件

准备 symbol 文件，格式必须是 `TW` 前缀：

```text
TW2330
TW2317
TW2454
TW0050
```

示例：

```bash
cd /path/to/taiwan-stock-quant-platform
mkdir -p data/tw_yahoo_scrapling_candidate/reports

cat > data/tw_yahoo_scrapling_candidate/reports/symbols.txt <<'EOF'
TW2330
TW2317
TW2454
TW0050
EOF
```

执行抓取：

```bash
python /home/chuliyang/Scrapling/qlib_scrapling_handoff/scripts/crawl_yahoo_scrapling.py \
  --symbols-file data/tw_yahoo_scrapling_candidate/reports/symbols.txt \
  --start 2024-01-01 \
  --end 2026-06-01 \
  --output-dir data/tw_yahoo_scrapling_candidate/normalized \
  --report-file data/tw_yahoo_scrapling_candidate/reports/crawl_report.json \
  --proxy http://127.0.0.1:7890 \
  --sleep-seconds 0.5 \
  --continue-on-error \
  --suffix auto
```

参数说明：

| 参数 | 建议 | 含义 |
| --- | --- | --- |
| `--symbols-file` | 必填 | 每行一个 `TWxxxx` |
| `--symbol` | smoke 用 | 可重复传多个 symbol |
| `--start` | 必填 | 起始日期，含当天 |
| `--end` | 必填 | 最后请求日期；脚本内部会转 Yahoo `period2=end+1day` |
| `--output-dir` | 必填 | candidate CSV 输出目录 |
| `--report-file` | 必填 | 抓取报告 JSON |
| `--proxy` | 视环境 | 本地代理；不用时传空字符串 |
| `--sleep-seconds` | `0.5` 到 `3.0` | symbol 间等待，降低限流风险 |
| `--continue-on-error` | 建议开启 | 单 symbol 失败不终止整个批次 |
| `--suffix` | `auto` | 自动尝试 `.TW` 和 `.TWO` |

---

## 8. `.TW` 和 `.TWO` 的处理

Yahoo 台股 ticker 后缀不同：

```text
上市 TWSE: 2330.TW
上柜 TPEx: 6488.TWO
```

脚本使用：

```bash
--suffix auto
```

时会按顺序尝试：

```text
2330.TW
2330.TWO
```

谁有有效数据就使用谁。

qlib Option C 的成功报告中曾记录：

```text
.TW selected: 112
.TWO selected: 38
```

因此 QuantDinger 批量抓台股时不要只尝试 `.TW`，否则会漏掉上柜股票。

---

## 9. 验证输出

抓取完成后必须运行 validator。

```bash
python /home/chuliyang/Scrapling/qlib_scrapling_handoff/scripts/validate_output.py \
  --data-dir data/tw_yahoo_scrapling_candidate/normalized \
  --symbols-file data/tw_yahoo_scrapling_candidate/reports/symbols.txt \
  --report data/tw_yahoo_scrapling_candidate/reports/validation_report.json
```

成功输出应类似：

```json
{
  "symbols_expected": 4,
  "files_found": 4,
  "missing_count": 0,
  "empty_count": 0,
  "issue_symbol_count": 0,
  "total_rows": 2000
}
```

validator 会检查：

```text
列顺序是否正确
文件名和 symbol 列是否一致
日期是否升序
是否有重复日期
OHLC/VWAP/factor 是否为正
volume 是否非负
high/low 是否满足价格关系
```

只有 validation pass 的 candidate 数据，才可以进入后续导入或合并讨论。

---

## 10. 推荐目录规范

不要直接写入生产表或正式数据目录。先放隔离 candidate 目录：

```text
/path/to/taiwan-stock-quant-platform/data/tw_yahoo_scrapling_candidate/
  normalized/
    TW2330.csv
    TW2317.csv
  reports/
    symbols.txt
    crawl_report.json
    validation_report.json
```

如果后续要把数据导入 QuantDinger 的 `qd_tw_stock_daily_bars`，应该另开工作单或提交，由审核窗口确认：

```text
数据口径是否仍是 Yahoo-only
是否要和现有 FinMind/raw 数据分表或加 source 字段
是否会影响现有回测和趋势页
是否需要保留 adjusted/raw 标记
```

---

## 11. 如何处理 YFRateLimitError

当 QuantDinger 或执行者看到：

```text
YFRateLimitError: Too Many Requests
```

不要继续提高 yfinance 并发，也不要马上切 FinMind。建议流程：

1. 停止当前 yfinance 批量任务。
2. 记录失败 symbol、时间、批量大小、错误文本。
3. 用 Scrapling 对 1 个 symbol 做 smoke。
4. smoke 成功后，用小批量 symbol 文件抓取。
5. 每个 symbol 间加 sleep。
6. 输出 candidate CSV 和 crawl report。
7. 跑 validation。
8. 只在 validation pass 后讨论是否导入。

推荐保守参数：

```text
--sleep-seconds 1.0
--continue-on-error
--suffix auto
--timeout 30
```

如果还是失败：

```text
增大 --sleep-seconds 到 3.0
缩小 symbol 批次
检查 proxy 是否可用
检查 Yahoo 返回 http_status 或 chart_error
把 crawl_report.json 作为 blocker 证据，不要制造空数据
```

---

## 12. QuantDinger 导入前必须决定的问题

Scrapling 输出是 qlib-style normalized CSV，不等于 QuantDinger 已经可以直接当生产日线使用。

导入 `qd_tw_stock_daily_bars` 前必须明确：

1. `source` 字段如何标记：建议 `yahoo_scrapling`。
2. 是否保存 adjusted OHLC，还是另建 adjusted 表。
3. 是否与现有 FinMind raw 日线共存。
4. 回测默认用 raw 还是 adjusted。
5. 趋势页展示是否会因 adjusted price 与 raw price 不同而让用户困惑。
6. 是否需要保留 `factor` 字段。
7. 是否需要写入 `quality_flags` 或 import metadata。

建议第一阶段不要直接覆盖现有 `qd_tw_stock_daily_bars`。更稳妥的做法：

```text
先保留 candidate CSV。
新增只读验证脚本或临时 reader。
确认 Yahoo-only adjusted 口径适合某个功能后，再单独设计导入表和 API。
```

---

## 13. 严禁事项

使用 Scrapling 抓 Yahoo 数据时，严禁：

```text
把 candidate 数据直接覆盖生产数据
把 Yahoo + FinMind 混合后仍称为 Yahoo-only
提交 proxy credentials、cookies、raw response caches 或 secrets
在抓取脚本里触发交易、订单、paper/live、broker
因为抓取成功就自动开始预测、回测、下单
validation 失败仍继续导入
静默忽略 missing/empty symbols
用旧数据冒充最新交易日数据
```

---

## 14. 给执行者的一句话

遇到 `YFRateLimitError` 时，先停止 yfinance 批量抓取，改用 `/home/chuliyang/Scrapling/qlib_scrapling_handoff/scripts/crawl_yahoo_scrapling.py` 以 `--suffix auto --continue-on-error --sleep-seconds 0.5~3.0` 把 Yahoo-only 数据抓到隔离 candidate 目录，再用 `validate_output.py` 验证，验证通过前不要导入 QuantDinger 生产数据或触发任何预测、回测、交易流程。

