# 台股历史策略回放实现报告

## 目标

本次实现把“策略是否真的有效”从页面上的静态规则解释，推进到可审计的历史日级回放：对每个历史 asof 生成 qlib Option C 排名信号，再结合 QuantDinger 趋势、MA/RSI/MACD/Bollinger 技术状态和价格位置，按组合规则进行只读模拟。

所有能力均为研究和模拟用途，不连接券商、不生成订单、不写入模拟账户业务表、不更新生产 `latest_signal.json`。

## 已实现

1. 新增历史信号回填脚本：`scripts/backfill_tw_option_c_historical_signals.py`
   - 默认输出到隔离目录：`qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/<batch_id>`
   - 支持 `--start-date`、`--end-date`、`--max-days`、`--dry-run`、`--batch-id`
   - 复用 frozen Option C qlib model 和正式 Option C provider
   - 每个交易日生成 `prediction.csv`、`top30_signals.csv`、`top50_signals.csv`、`signal_summary.json`、`run_metadata.json`
   - 明确写入 `latest_signal_updated=false`、`research_signal_not_order=true`

2. 扩展只读观察回放服务
   - `TWStockObservationReplayService.compare(..., signal_root=...)` 可读取隔离 backfill 根目录
   - 保留默认生产 accepted signal root，不影响现有页面 latest
   - 返回 `source.historicalBackfill`，便于前端和报告识别数据来源

3. 扩展组合策略回放服务
   - `TWStockPortfolioReplayService.replay(config={ signalRoot, executionMode })`
   - 默认成交口径改为 `next_trading_day_close`
   - 返回 `execution.lookahead_guard=true`，明确避免“信号日同日成交”的未来函数
   - 保留 `same_day_close` 兼容口径，但前端默认使用下一交易日收盘价

4. 前端简化展示
   - 在“过去表现”下只增加一行成交口径说明：`成交口径：下一交易日收盘价（避免同日未来函数）`
   - 不新增复杂模块，避免干扰用户主线

## 当前验证

### dry-run 交易日检查

命令：

```bash
python scripts/backfill_tw_option_c_historical_signals.py --start-date 2026-01-01 --end-date 2026-05-31 --dry-run
```

结果：

- 识别交易日数：95
- 首个交易日：2026-01-02
- 最后交易日：2026-05-29
- `latest_signal_updated=false`
- `refresh_triggered=false`
- `publish_triggered=false`

### 小规模真实 smoke

命令：

```bash
python scripts/backfill_tw_option_c_historical_signals.py   --start-date 2026-01-01   --end-date 2026-05-31   --max-days 2   --batch-id option_c_historical_backfill_20260101_20260531_smoke
```

结果：

- 生成 asof：2026-01-02、2026-01-05
- accepted：2
- failed：0
- 输出根：`qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20260101_20260531_smoke`
- 未更新生产 latest

### backfill 根组合回放 smoke

范围：2026-01-02 至 2026-01-05
成交口径：下一交易日收盘价

结果摘要：

| 策略 | 总收益 | 最大回撤 | 动作次数 | 费用税费估算 |
| --- | ---: | ---: | ---: | ---: |
| 直接跟排名 | 0.1235% | -0.0142% | 2 | 284.86 |
| 加入追高过滤 | -0.0141% | -0.0141% | 1 | 141.08 |
| 等回调再观察 | -0.0141% | -0.0141% | 1 | 141.08 |
| 连续转弱才复盘 | -0.0141% | -0.0141% | 1 | 141.08 |

该结果只是 2 个交易日 smoke，不用于判断策略优劣。

## 如何执行完整 2026-01-01 到 2026-05-31 回放

先生成完整历史信号：

```bash
python scripts/backfill_tw_option_c_historical_signals.py   --start-date 2026-01-01   --end-date 2026-05-31   --batch-id option_c_historical_backfill_20260101_20260531
```

生成完成后，组合回放传入：

```json
{
  "startDate": "2026-01-01",
  "endDate": "2026-05-31",
  "signalRoot": "qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20260101_20260531",
  "executionMode": "next_trading_day_close",
  "bucket": "top30",
  "maxItems": 30,
  "variant": "all",
  "initialCash": 1000000,
  "maxHoldings": 10,
  "lotSize": 10,
  "maxAddPerDay": 1,
  "maxRiskActionPerDay": 1,
  "technicalStrategies": ["ma", "rsi", "macd", "bollinger"],
  "persist": false
}
```

## 限制和下一步

- 完整 95 日 qlib 历史信号回填已经跑完：95 个交易日全部 accepted，failed=0，未更新生产 latest。
- 完整组合回放已启动验证，但在行情读取阶段大量触发 FinMind fallback，返回 402/403，导致全量收益汇总长时间无法稳定结束；已手动终止该只读长任务，避免继续占用资源。
- 2 日 smoke 回放已证明 backfill 根可以被组合回放读取，且成交口径为下一交易日收盘价。
- 下一步不应继续依赖回放时临时请求 FinMind；应先做本地价格缓存/只读直读，确保 Top30/Top50 历史成分股的日线价格覆盖率，再跑完整收益、最大回撤、费用、动作频率和换手率分析。

## 完整回填补充结果

完整命令：

```bash
python scripts/backfill_tw_option_c_historical_signals.py \
  --start-date 2026-01-01 \
  --end-date 2026-05-31 \
  --batch-id option_c_historical_backfill_20260101_20260531
```

结果：

- status：accepted
- trading_day_count：95
- generated_count：95
- failed_count：0
- latest_signal_updated：false
- refresh_triggered：false
- publish_triggered：false
- provider_mutation_triggered：false
- 输出根：`qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20260101_20260531`

## 完整回放阻塞点

完整 95 日组合回放已启动，但运行过程中大量历史 Top30 标的缺本地日线价格，`KlineService` 触发 FinMind fallback，并连续返回 402/403。由于回放需要对每天的候选和持仓取下一交易日价格，这会造成大量重复外部请求，当前不适合作为最终策略收益结论。

结论：

- qlib 历史信号：已完整可用。
- 策略回放框架：已接入并通过 2 日 smoke。
- 完整 95 日收益结论：暂不应发布，因为价格数据覆盖率不足会让收益、回撤和动作统计失真。
- 下一步应实现本地日线价格缓存或 local-only price reader，再重新跑完整组合回放。

## FinMind Token 补齐本地价格后的完整回放结果

用户提供的 FinMind token 已确认存在于 `backend/.env`。前一次完整回放触发大量 402/403 的原因不是 token 无效，而是执行回放时没有加载 `backend/.env`，导致本地 archive lookup/FinMind token 环境都没有进入进程。

已执行本地价格补齐：

```bash
set -a; . backend/.env; set +a
cd backend
python scripts/update_tw_stock_daily.py \
  --symbols-file ../qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20260101_20260531/backfill_top50_symbols.txt \
  --start 2025-07-01 \
  --end 2026-06-02 \
  --apply \
  --no-validate \
  --no-corporate-actions \
  --no-institutional \
  --no-margin \
  --no-monthly-revenue \
  --no-valuation
```

归档结果：

- 唯一历史 Top50 标的数：150
- 写入 `qd_tw_stock_daily_bars`：33,582 条
- 日期范围：2025-07-01 至 2026-06-02
- flagged_count：35
- 输出摘要：`qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20260101_20260531/finmind_archive_apply_summary.json`

完整组合回放命令使用同样 env：

```bash
set -a; . backend/.env; set +a
PYTHONPATH=backend TW_STOCK_ARCHIVE_LOOKUP=true python <portfolio replay script>
```

完整 95 日回放结果，范围 2026-01-01 至 2026-05-31，成交口径为下一交易日收盘价：

| 策略 | 总收益 | 最大回撤 | 动作次数 | 买入次数 | 风险复盘次数 | 费用税费估算 | 期末权益 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 直接跟排名 | 68.3532% | -13.3141% | 10 | 10 | 0 | 1,420.96 | 1,683,531.54 |
| 加入追高过滤 | 32.2652% | -6.3137% | 12 | 9 | 3 | 2,287.30 | 1,322,651.98 |
| 等回调再观察 | 28.2119% | -5.9965% | 9 | 7 | 2 | 1,605.52 | 1,282,118.76 |
| 连续转弱才复盘 | 36.3516% | -7.2920% | 11 | 9 | 2 | 1,846.13 | 1,363,516.15 |

数据质量：

- warningCount：1
- warningsSample：`history_below_120_bars`
- 历史回放源：isolated historical backfill root
- `lookahead_guard=true`
- `simulation_only=true`

初步专业解读：

- 该阶段样本中，`直接跟排名`收益最高，但最大回撤也最高，说明它更像高波动追强基线，不适合直接作为小白默认策略。
- `加入追高过滤`和`连续转弱才复盘`收益较低但回撤显著下降，更符合用户第一性原则下的“先别大亏，再谈收益”。
- `等回调再观察`回撤最低，但收益也进一步降低，适合保守模式。
- 当前 2026-01 至 2026-05 是偏强历史样本，不能直接外推未来；下一步应增加更多市场阶段、手续费滑点敏感性和持仓明细解释。
