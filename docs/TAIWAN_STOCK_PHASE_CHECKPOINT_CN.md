# 台股量化项目断点记录

更新时间：2026-05-24

## 当前目标

把 QuantDinger 扩展为可研究台湾股市的量化系统，并逐步完成数据获取、质量校验、回测、归档、复权、Qlib 数据准备和后续部署。

当前主线已按用户要求调整为：优先提供“按需查看台股趋势”和“自动监控提醒”的研究能力与后续可视化；系统可以自动刷新、监控观察列表、提示趋势变化和解释原因，但买卖决策仍由用户人工判断；自动下单、IBKR live promotion 暂时停放，不作为近期目标。

## 已完成阶段

### Phase 1：台股日线研究与回测

- 已新增 `TWStockDataSource`，支持 FinMind 台股日线 `TaiwanStockPrice`。
- 已注册 `TWStock` 到数据源工厂，支持别名 `TWStock`、`twstock`、`tw_stock`、`taiwanstock`。
- 支持常见台股 symbol 格式：`2330`、`2330.TW`、`TWSE:2330`、`TPEX:6488`。
- 支持 `1D` 和 `1W` K 线。
- 已接入市场列表、Agent market list、可见市场配置、热门台股标的。
- HTTP 回测入口对 `TWStock` 设置默认假设：
  - `commission=0.002925`
  - `slippage=0.001`
  - `tradeDirection=long`
  - TWD、Asia/Taipei、lot size 1000、默认不强制整张。
- 默认行情仍为未复权价格，避免无声改变既有回测行为。

### Phase 2：数据归档与质量

- 已新增 `qd_tw_stock_daily_bars`，用于台股日线本地归档。
- 已新增 `qd_tw_stock_corporate_actions`，用于除权息/复权因子归档。
- 已实现脚本：
  - `backend/scripts/sync_tw_stock_symbols.py`
  - `backend/scripts/archive_tw_stock_daily.py`
  - `backend/scripts/validate_tw_stock_daily.py`
  - `backend/scripts/update_tw_stock_daily.py`
  - `backend/scripts/archive_tw_stock_corporate_actions.py`
  - `backend/scripts/archive_tw_stock_institutional_trades.py`
  - `backend/scripts/archive_tw_stock_margin_trading.py`
  - `backend/scripts/archive_tw_stock_monthly_revenue.py`
  - `backend/scripts/archive_tw_stock_valuation.py`
- `update_tw_stock_daily.py` 已作为盘后总控脚本：归档日线、TWSE 官方最新日校验、归档除权息、归档三大法人买卖超、归档融资融券、归档月营收、归档估值。
- 已新增 `qd_tw_stock_institutional_trades`，用于保存外资、投信、自营商和总法人净买超。
- 已新增 `qd_tw_stock_margin_trading`，用于保存融资买进/卖出/偿还/余额和融券卖出/买进/偿还/余额。
- 已新增 `qd_tw_stock_monthly_revenue`，用于保存月营收、MoM 和 YoY 增速。
- 已新增 `qd_tw_stock_valuation`，用于保存 PE、PB 和股利殖利率。
- 支持可选复权模式：
  - `TW_STOCK_CORPORATE_ACTION_MODE=raw_unadjusted` 默认
  - `TW_STOCK_CORPORATE_ACTION_MODE=forward_adjusted` 前复权
  - `TW_STOCK_CORPORATE_ACTION_MODE=backward_adjusted` 后复权

## 数据源真实性和时效性

- 个股/ETF 日线来自 FinMind `TaiwanStockPrice`，是真实市场数据，适合日频研究，不是盘中实时流。
- 除权息来自 FinMind `TaiwanStockDividendResult`。
- 三大法人买卖超来自 FinMind `TaiwanStockInstitutionalInvestorsBuySell`。
- 融资融券来自 FinMind `TaiwanStockMarginPurchaseShortSale`，当前保留来源单位，不擅自换算。
- 月营收来自 FinMind `TaiwanStockMonthRevenue`，MoM/YoY 由本地解析脚本计算。
- 估值来自 FinMind `TaiwanStockPER`，当前字段为 PE、PB 和股利殖利率；市值需后续从股本/股数来源补充。
- TWSE 上市样本已用 TWSE 官方 `STOCK_DAY_ALL` 对最新交易日收盘价和成交量做交叉校验。
- 最近验证到的官方最新交易日：2026-05-22。
- TPEx 上柜数据可通过 FinMind 获取，但当前环境访问 TPEx 官方 OpenAPI 仍不稳定，官方交叉校验保持 xfail。

## 最近测试状态

- 台股 Phase 1/2 离线完整集合：`74 passed`
- 基础回归：`38 passed, 2 warnings`
- 实时质量测试：`10 passed, 3 xfailed`
- 真实 dry-run：
  - `2330`、`0050` 日线与 TWSE 官方最新日匹配。
  - `2330` 在 2024-01-01 到 2026-05-23 拉到 9 条除息记录，`flagged_count=0`。
  - `2330`、`0050` 在 2026-05-20 到 2026-05-22 拉到 6 条三大法人聚合记录，`flagged_count=0`。
  - `2330`、`0050` 在 2026-05-20 到 2026-05-22 拉到 6 条融资融券记录，`flagged_count=0`。
  - `2330`、`2317` 在 2025-01-01 到 2026-05-23 拉到 34 条月营收记录，`flagged_count=0`。
  - `2330`、`2317` 在 2026-05-20 到 2026-05-22 拉到 6 条估值记录，`flagged_count=0`。

## 当前暂停点

用户要求准备 Qlib normalized CSV 数据，参考 `docs/data.txt`：

- 输出目录：`/home/chuliyang/qlib/data_tw/normalized/`
- 每个标的一份 CSV，例如：`TW2330.csv`、`TW2317.csv`、`TWII.csv`
- 必须列：`symbol,date,open,high,low,close,volume,vwap,factor`
- 个股 symbol 输出为 `TW2330` 格式。
- 加权指数输出为 `TWII`，但 FinMind 查询代码应使用 `TAIEX`。
- `vwap` 优先用 `Trading_money / Trading_Volume`，缺失时使用 `(open + high + low + close) / 4`。
- `factor` 原始价先填 `1.0`；复权模式可基于 corporate actions 计算。

## 下一步入口

已实现并验证：

```text
backend/scripts/export_tw_qlib_normalized.py
backend/tests/test_export_tw_qlib_normalized.py
```

脚本可按 `docs/data.txt` 清单拉取真实台股和 `TAIEX` 指数数据，生成 Qlib normalized CSV，并输出质量报告。

最近 Qlib 导出验证：

```bash
python backend/scripts/export_tw_qlib_normalized.py \
  --start 2026-05-20 --end 2026-05-22 \
  --output-dir /home/chuliyang/qlib/data_tw/normalized \
  --continue-on-error
```

结果：19 个标的、57 行、`empty_symbols=[]`、`failed_symbols=[]`、`flagged_symbols=[]`。

下一步可选择：

- 拉取更长历史，例如 `--start 2015-01-01 --end 2026-05-23`。
- 接入 Qlib dump/bin 转换流程。
- 用生成的 normalized CSV 跑 Qlib Alpha158/LightGBM baseline。


## Phase 3 进展

已新增台股 universe 构建器：

```text
backend/scripts/build_tw_stock_universe.py
backend/tests/test_build_tw_stock_universe.py
```

功能：读取台股候选，拉取近期日线，按 bars、平均成交量、平均成交金额过滤，并输出兼容 cross-sectional 策略配置的 `symbol_list`，例如 `TWStock:2330`。

真实 smoke：

```bash
python backend/scripts/build_tw_stock_universe.py \
  --symbol 2330,2317,2454,2308,2412 \
  --start 2026-05-20 --end 2026-05-22 \
  --min-bars 3 --min-avg-volume 1 --min-avg-trading-money 1 \
  --max-universe 5 \
  --output-json /tmp/tw_universe_smoke.json
```

结果：`selected_count=5`，`symbol_list=["TWStock:2330","TWStock:2454","TWStock:2308","TWStock:2317","TWStock:2412"]`。


已新增台股横截面排名脚本：

```text
backend/scripts/rank_tw_stock_universe.py
backend/tests/test_rank_tw_stock_universe.py
```

功能：读取 universe 的 `symbol_list`，拉取日线，计算动量、低波动、流动性分位分数，输出 `rankings` 和详细分解。

真实 smoke：

```bash
python backend/scripts/rank_tw_stock_universe.py \
  --universe-json /tmp/tw_universe_smoke.json \
  --start 2026-04-01 --end 2026-05-22 \
  --momentum-window 20 --volatility-window 20 --min-bars 30 \
  --output-json /tmp/tw_universe_rank_smoke.json
```

结果：`eligible_count=5`，`rankings=["TWStock:2454","TWStock:2317","TWStock:2330","TWStock:2308","TWStock:2412"]`。


已新增台股调仓计划生成器：

```text
backend/scripts/plan_tw_stock_rebalance.py
backend/tests/test_plan_tw_stock_rebalance.py
```

功能：读取排名 JSON，选择 Top N，生成 long-only 目标持仓权重，不下单。

真实 smoke：

```bash
python backend/scripts/plan_tw_stock_rebalance.py \
  --ranking-json /tmp/tw_universe_rank_smoke.json \
  --top-n 3 --cash-weight 0.1 --max-weight 0.35 \
  --as-of 2026-05-22 \
  --output-json /tmp/tw_rebalance_plan_smoke.json
```

结果：Top 3 为 `2454,2317,2330`，各 `30%`，现金 `10%`。

已新增台股组合模拟器：

```text
backend/scripts/simulate_tw_stock_portfolio.py
backend/tests/test_simulate_tw_stock_portfolio.py
```

功能：读取台股候选，滚动计算横截面排名，按调仓规则生成目标权重，并用日线 close-to-close 收益模拟组合净值、换手和成本。该脚本是研究模拟器，不下单；已支持可选 `--enforce-lot-size` 台股 1000 股整股近似撮合，并拆分买入手续费、卖出手续费和证券交易税；已支持可选 `--enforce-price-limit` 涨跌停保守约束。

真实 smoke：

```bash
python backend/scripts/simulate_tw_stock_portfolio.py \
  --symbol 2330,2317,2454,2308,2412 \
  --start 2026-04-01 --end 2026-05-22 \
  --rebalance-frequency weekly \
  --lookback-days 45 \
  --momentum-window 10 --volatility-window 10 --min-bars 15 \
  --top-n 3 --cash-weight 0.1 --max-weight 0.35 \
  --transaction-cost 0.003925 \
  --output-json /tmp/tw_portfolio_sim_smoke.json
```

结果：`rebalance_count=8`，`final_equity=1.49727736`，`max_drawdown=-0.09394929`，`average_turnover=0.5625`。这是短区间链路验证结果，不应视为策略有效性证明。
整股撮合 smoke：

```bash
python backend/scripts/simulate_tw_stock_portfolio.py \
  --symbol 2330,2317,2454,2308,2412 \
  --start 2026-04-01 --end 2026-05-22 \
  --rebalance-frequency weekly \
  --lookback-days 45 \
  --momentum-window 10 --volatility-window 10 --min-bars 15 \
  --top-n 3 --cash-weight 0.1 --max-weight 0.35 \
  --enforce-lot-size --initial-capital 5000000 --lot-size 1000 \
  --commission-rate 0.001425 --sell-tax-rate 0.003 \
  --output-json /tmp/tw_portfolio_lot_sim_smoke.json
```

结果：`rebalance_count=8`，`final_equity=0.99895233`，`max_drawdown=-0.01401118`，`average_turnover=0.31265454`。事件中已包含整股 `shares`、手续费和卖出税字段。
整股 + 涨跌停约束 smoke：

```bash
python backend/scripts/simulate_tw_stock_portfolio.py \
  --symbol 2330,2317,2454,2308,2412 \
  --start 2026-04-01 --end 2026-05-22 \
  --rebalance-frequency weekly \
  --lookback-days 45 \
  --momentum-window 10 --volatility-window 10 --min-bars 15 \
  --top-n 3 --cash-weight 0.1 --max-weight 0.35 \
  --enforce-lot-size --initial-capital 5000000 --lot-size 1000 \
  --commission-rate 0.001425 --sell-tax-rate 0.003 \
  --enforce-price-limit --price-limit-pct 0.10 \
  --output-json /tmp/tw_portfolio_limit_sim_smoke.json
```

结果：`rebalance_count=8`，`final_equity=0.99895233`，`max_drawdown=-0.01401118`，`average_turnover=0.31265454`。本样本未触发涨跌停阻断；离线测试已覆盖 `blocked_buys` 和 `blocked_sells`。

## Phase 4 进展

已新增台股纸面订单预览器：

```text
backend/scripts/preview_tw_stock_paper_orders.py
backend/tests/test_preview_tw_stock_paper_orders.py
```

功能：读取调仓计划和当前持仓，生成 paper-only 订单预览；不写数据库，不连接 IBKR，不下单。订单预览包含 IBKR 台股合约字段 `STK/TWSE/TWD`、整股数量、限价保护、单笔/总买入名义金额风控，以及目标不足一张的 warning。

真实 smoke：

```bash
python backend/scripts/preview_tw_stock_paper_orders.py \
  --plan-json /tmp/tw_rebalance_plan_smoke.json \
  --as-of 2026-05-22 \
  --portfolio-value 5000000 \
  --lot-size 1000 \
  --limit-buffer 0.005 \
  --max-order-value 2000000 \
  --max-total-buy-value 5000000 \
  --output-json /tmp/tw_paper_order_preview_smoke.json
```

结果：生成 `1` 笔 paper-only 限价买入预览：`2317` 买入 `6000` 股，参考价 `250.0`，限价 `251.25`，预估名义金额 `1,500,000 TWD`。warnings 为 `target_below_one_lot:2330`、`target_below_one_lot:2454`。

主线审视：当前工作未偏离台股量化主线。Phase 1/2 完成台股数据与质量；Phase 3 完成 universe、ranking、rebalance、组合模拟；Phase 4 正在从 paper-only 订单预览切入执行链路，尚未连接真实 broker。

本轮补充：

- `backend/app/services/ibkr_trading/symbols.py` 已支持 `TWStock`：上市默认 `TWSE/TWD`，上柜可用 `TPEX/TWD`。
- `backend/app/services/broker_market_policy.py` 已把 `IBKR + TWStock + spot + long` 纳入兼容矩阵。
- `preview_tw_stock_paper_orders.py` 已改为复用正式 IBKR symbol service。
- 新增 `backend/tests/test_ibkr_tw_stock_symbols.py`。

真实 paper preview smoke 仍为：`2317` 买入 `6000` 股，参考价 `250.0`，限价 `251.25`，预估名义金额 `1,500,000 TWD`；`2330`、`2454` 目标不足一张。
本轮补充：

- `backend/app/routes/agent_v1/quick_trade.py` 已支持 `market=TWStock` 的 paper-only quick-trade。
- 台股 agent paper order 强制限价单、正数限价、1000 股整股倍数、long-only sell 校验。
- `TWStock` paper fill 价格改用台股日线最新收盘价兜底，避免 `1m` 不支持导致 paper order 无法成交。
- 新增 `backend/tests/test_agent_v1_twstock_quick_trade.py`，覆盖拒绝市价单、拒绝非整股、拒绝超持仓卖出、接收 preview order shape。

安全状态：仍然 paper-only；没有连接 IBKR，也没有真实下单。
本轮补充：

- `backend/app/routes/agent_v1/quick_trade.py` 对 `TWStock` 卖单新增服务端持仓 fallback。
- 请求没有 `current_qty/currentQty/current_position/currentPosition` 时，会从 `qd_user_positions` 查询当前用户的 `TWStock` 标准化 symbol 持仓合计。
- 查询失败或持仓不足时 fail-safe 拒绝卖单，避免 paper-only 链路出现隐含放空。
- `backend/tests/test_agent_v1_twstock_quick_trade.py` 增加服务端持仓足够、服务端持仓不足、请求已带持仓时不查服务端三类测试。

验证结果：`test_agent_v1_twstock_quick_trade.py` 为 `8 passed in 1.00s`；`quick_trade.py` 语法检查通过。

安全状态：仍然 paper-only；没有连接 IBKR，也没有真实下单。
本轮补充：

- 新增 `backend/scripts/submit_tw_stock_paper_orders.py` 和 `backend/tests/test_submit_tw_stock_paper_orders.py`。
- 该脚本读取 paper order preview JSON，默认 dry-run 生成 quick-trade payload，不访问后端、不写数据库、不连接 broker。
- 只有显式 `--submit --agent-token <token>` 时才 POST 到 `/api/agent/v1/quick-trade/orders`。
- dry-run smoke 使用 `/tmp/tw_paper_order_preview_smoke.json`，生成 1 个 payload：`TWStock 2317 buy 6000 limit 251.25`。

安全状态：默认 dry-run；submit 仍走 Agent T scope、paper_only 和 live kill switch。
本轮补充：

- 新增 `backend/scripts/run_tw_stock_paper_pipeline.py` 和 `backend/tests/test_run_tw_stock_paper_pipeline.py`。
- 该脚本把调仓计划 JSON -> 订单预览 -> quick-trade payload 合成一个命令。
- 默认 dry-run，本地执行；不会访问后端、不会写数据库、不会连接 broker。
- dry-run smoke 使用 `/tmp/tw_rebalance_plan_smoke.json`，输出：
  - `/tmp/tw_paper_pipeline_smoke.json`
  - `/tmp/tw_paper_pipeline_preview_smoke.json`
  - `/tmp/tw_paper_pipeline_submit_smoke.json`
- 结果：生成 1 笔候选 payload：`TWStock 2317 buy 6000 limit 251.25`；未提交到后端，`submit_results=[]`。
本轮补充：

- `run_tw_stock_paper_pipeline.py` 新增本地提交前风控：`--fail-on-warning`、`--fail-on-blocked`、`--max-submit-candidates`。
- 风控在 submit 之前执行；失败时返回退出码 `3`，不会调用 Agent Gateway。
- 正常 dry-run smoke 仍成功，`guard_errors=[]`。
- 开启 `--fail-on-warning` 的真实 smoke 返回退出码 `3`，`guard_errors=["warnings_present"]`，因为 `2330`、`2454` 目标不足一张。
本轮补充：

- 新增 `backend/scripts/verify_tw_stock_paper_orders.py` 和 `backend/tests/test_verify_tw_stock_paper_orders.py`。
- 该脚本读取 submit/pipeline 报告中的成功 `order_uid`，调用 `/api/agent/v1/portfolio/paper-orders` 查回，输出 matched/missing 结果。
- 它只做提交后验证，不创建订单、不更新持仓、不连接 IBKR。
- 用现有 dry-run submit 报告验证时，因为没有真实 `order_uid`，脚本按预期返回退出码 `2`，不会误判订单已提交。

验证结果：`test_verify_tw_stock_paper_orders.py` 为 `6 passed in 0.06s`；脚本语法检查通过；`/tmp/tw_paper_order_verify_no_submit.json` 已生成安全失败报告。

安全状态：仍然 paper-only；没有连接 IBKR，也没有真实下单。
本轮补充：

- 新增 `backend/tests/test_tw_stock_paper_api_loopback.py`。
- 该测试用 Flask test client 走真实 Agent 路由，验证 `submit_tw_stock_paper_orders` -> `/api/agent/v1/quick-trade/orders` -> fake `qd_agent_paper_orders` -> `/api/agent/v1/portfolio/paper-orders` -> `verify_tw_stock_paper_orders` 的闭环。
- 当前 shell 未配置 `DATABASE_URL`，本机也没有 `psql`，所以本轮没有声称完成真实 PostgreSQL 入库查回；真实 DB 闭环仍需后续配置 PostgreSQL 后执行。

验证结果：`test_tw_stock_paper_api_loopback.py` 为 `1 passed in 0.99s`；测试文件语法检查通过。

安全状态：仍然 paper-only；没有连接 IBKR，也没有真实下单。

## 本地 PostgreSQL 配置进展

本轮已完成本地 PostgreSQL 配置：

- 使用项目自带 `docker-compose.yml` 的 `postgres` 服务。
- 当前用户不在 `docker` 组，但 `sudo -n docker ...` 可用。
- Docker Hub 拉取 `postgres:16-alpine` 超时；本机已有 `app-store-images.pku.edu.cn/library/postgres-x86_64:16.11-trixie`，已临时打 tag 为 `postgres:16-alpine`。
- 本机 `127.0.0.1:5432` 已被 `maas-postgres` 占用，因此新增项目根目录 `.env`：`DB_PORT=127.0.0.1:55432`。
- `quantdinger-db` 当前 healthy，端口映射为 `127.0.0.1:55432->5432`。
- `backend/.env` 已配置：
  - `DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger`
  - `DB_TYPE=postgresql`
  - `CACHE_ENABLED=false`
  - `ENABLE_PENDING_ORDER_WORKER=false`
  - `ENABLE_PORTFOLIO_MONITOR=false`
  - `POSITION_SYNC_ENABLED=false`
  - `AGENT_LIVE_TRADING_ENABLED=false`

验证结果：

- 项目 Python 通过 `DATABASE_URL` 成功连接本地 PostgreSQL。
- `init_database()` 成功执行，`qd_agent_tokens`、`qd_agent_paper_orders`、`qd_users` 三张关键表存在。
- `docker compose ps postgres` 显示 `quantdinger-db` 为 `healthy`。
- `test_db_bootstrap.py` + `test_agent_v1.py`：`15 passed, 2 warnings`。

下一步入口：启动 Flask API，签发/写入 Agent T token，执行真实 `run_tw_stock_paper_pipeline.py --submit`，再用 `verify_tw_stock_paper_orders.py` 查回真实 `qd_agent_paper_orders`。

## Phase 4 真实 DB paper 闭环

本轮已完成真实 PostgreSQL paper order 闭环：

1. 在本地 PostgreSQL 写入一个一次性 Agent token：`scopes=R,T`、`markets=TWStock`、`paper_only=true`、`AGENT_LIVE_TRADING_ENABLED=false`。
2. 启动 Flask API：`127.0.0.1:5000`。
3. 使用固定价格输入，避免本次验证依赖外部行情网络：`/tmp/tw_db_loopback_prices.json` 中 `2317=250.0`。
4. 执行 `run_tw_stock_paper_pipeline.py --submit`，输出：
   - `/tmp/tw_paper_pipeline_db_loopback.json`
   - `/tmp/tw_paper_pipeline_db_loopback_preview.json`
   - `/tmp/tw_paper_pipeline_db_loopback_submit.json`
5. 使用 `verify_tw_stock_paper_orders.py` 通过 `/api/agent/v1/portfolio/paper-orders` 查回，输出 `/tmp/tw_paper_order_verify_db_loopback.json`。
6. 直接查询 `qd_agent_paper_orders` 交叉确认同一订单存在。

真实结果：

- `preview.order_count=1`，`blocked_count=0`，`warnings=[]`。
- 提交 payload：`TWStock 2317 buy 6000 limit 251.25`。
- Agent quick-trade 返回 `paper-fill`。
- `order_uid=37be98e25f524a62a2b7e745257f7228`。
- 数据库记录：`market=TWStock`、`symbol=2317`、`side=buy`、`qty=6000`、`limit_price=251.25`、`fill_price=250.0`、`fill_value=1500000.0`、`status=filled`。
- 验证器结果：`matched_count=1`，`missing_count=0`。

收尾状态：Flask API 已停止，`127.0.0.1:5000` 不再监听；PostgreSQL 容器 `quantdinger-db` 保持 healthy，供后续步骤继续使用。

安全状态：仍然 paper-only；没有连接 IBKR，也没有真实下单。

## Phase 4 paper position 汇总

本轮新增 paper-only 持仓汇总能力：

- `backend/app/routes/agent_v1/portfolio.py` 新增 `/api/agent/v1/portfolio/paper-positions`。
- 该接口只读，不写数据库；从 `qd_agent_paper_orders` 的 `filled` 订单动态推导 paper positions。
- buy 增加数量和成本，按成交价计算加权平均成本；sell 按当前平均成本扣减成本。
- 如果出现超卖，输出 `paper_position_oversell:<market>:<symbol>` warning，不生成负持仓。
- 新增 `backend/tests/test_agent_v1_paper_positions.py`，覆盖加权成本、卖出减仓、超卖 warning 和 API 返回。

真实 DB smoke：

- 使用上一轮真实 DB paper order：`TWStock 2317 buy 6000 fill_price=250.0`。
- 启动本地 Flask API 后调用 `/api/agent/v1/portfolio/paper-positions`。
- 输出保存到 `/tmp/tw_paper_positions_db_smoke.json`。
- 返回 `positions=[{market=TWStock, symbol=2317, quantity=6000.0, avg_price=250.0, cost_value=1500000.0, currency=TWD, source=agent_paper_orders, order_count=1}]`，`warnings=[]`。

验证结果：`test_agent_v1_paper_positions.py` 为 `3 passed in 0.91s`；真实 DB smoke 返回 HTTP 200。

收尾状态：Flask API 已停止；PostgreSQL 容器 `quantdinger-db` 保持 healthy。

安全状态：仍然 paper-only；没有连接 IBKR，也没有真实下单。

## Phase 4 paper portfolio summary

本轮新增 paper-only 组合汇总能力：

- `backend/app/routes/agent_v1/portfolio.py` 新增 `/api/agent/v1/portfolio/paper-summary`。
- 该接口只读，不写数据库；从 `qd_agent_paper_orders` 的 `filled` 订单动态推导组合摘要。
- 支持 query 参数 `initial_cash`，用于计算现金影响和成本口径权益。
- 输出字段包括：`cash`、`gross_buy_value`、`gross_sell_value`、`realized_pnl`、`open_cost_value`、`equity_at_cost`、`filled_order_count`、`position_count`、`positions`、`warnings`。
- 新增 `backend/tests/test_agent_v1_paper_positions.py` 覆盖 summary 现金、持仓成本、已实现盈亏、非法 `initial_cash`。

真实 DB smoke：

- 使用上一轮真实 DB paper order：`TWStock 2317 buy 6000 @ 250.0`。
- 调用 `/api/agent/v1/portfolio/paper-summary?initial_cash=5000000`。
- 输出保存到 `/tmp/tw_paper_summary_db_smoke.json`。
- 返回：`cash=3500000.0`、`gross_buy_value=1500000.0`、`gross_sell_value=0.0`、`realized_pnl=0.0`、`open_cost_value=1500000.0`、`equity_at_cost=5000000.0`、`position_count=1`、`warnings=[]`。

验证结果：`test_agent_v1_paper_positions.py` 为 `6 passed in 0.90s`；真实 DB smoke 返回 HTTP 200。

收尾状态：Flask API 已停止；PostgreSQL 容器 `quantdinger-db` 保持 healthy。

安全状态：仍然 paper-only；没有连接 IBKR，也没有真实下单。

## Phase 4 主线复核与执行报告

主线复核结论：截至本轮，工作没有偏离台股量化主线。Phase 1/2 完成台股数据源、归档、质量校验和 Qlib normalized CSV；Phase 3 完成 universe、ranking、rebalance 和组合模拟；Phase 4 继续围绕 paper-only 执行链路展开：订单预览、提交桥接、真实 PostgreSQL paper 写入、查回验证、paper positions、paper summary 和执行报告。未接入无关市场，未启动实盘交易，未连接 IBKR。

本轮新增执行报告生成器：

- 新增 `backend/scripts/build_tw_stock_paper_execution_report.py`。
- 新增 `backend/tests/test_build_tw_stock_paper_execution_report.py`。
- 该脚本只读取本地 JSON 产物，不提交订单、不查询数据库、不连接 broker、不修改状态。
- 输入：pipeline JSON、verify JSON、paper summary JSON。
- 输出：JSON 和 Markdown 两种报告，包含 pipeline 摘要、订单摘要、查回结果、paper portfolio summary、warnings 和安全状态。

真实产物：

- `/tmp/tw_paper_execution_report_db_loopback.json`
- `/tmp/tw_paper_execution_report_db_loopback.md`

真实报告结果：

- `status=pass`。
- `preview_order_count=1`、`submitted_count=1`、`failed_submit_count=0`。
- `matched_count=1`、`missing_count=0`。
- 订单为 `2317 buy 6000 limit 251.25`。
- portfolio summary 为 `cash=3500000.0`、`open_cost_value=1500000.0`、`equity_at_cost=5000000.0`。
- 安全状态为 `paper_only=true`、`broker_connected=false`、`live_order_submitted=false`。

验证结果：`test_build_tw_stock_paper_execution_report.py` 为 `4 passed in 0.04s`；脚本语法检查通过。

安全状态：仍然 paper-only；没有连接 IBKR，也没有真实下单。

## Phase 4 pipeline execution report 集成

本轮把 execution report 接入一键 paper pipeline：

- `backend/scripts/run_tw_stock_paper_pipeline.py` 新增参数：
  - `--verify-json`
  - `--portfolio-summary-json`
  - `--execution-report-json`
  - `--execution-report-md`
- 当同时提供 verify JSON 和 paper summary JSON 时，pipeline 会调用 `build_tw_stock_paper_execution_report.py` 生成 JSON/Markdown 执行报告。
- 如果只提供其中一个输入，pipeline 返回退出码 `2`，避免生成半成品审计报告。
- 该集成仍然只读本地 JSON；不会自动查询 DB，不会连接 broker，不会提交订单。真实 submit 后仍应先运行 verify 和 paper-summary，再生成完整报告。
- 新增 `test_main_writes_execution_report_when_verify_and_summary_provided` 和 `test_main_execution_report_requires_verify_and_summary_together`。

smoke 输出：

- `/tmp/tw_paper_pipeline_with_report_smoke.json`
- `/tmp/tw_paper_pipeline_with_report_preview_smoke.json`
- `/tmp/tw_paper_pipeline_with_report_submit_smoke.json`
- `/tmp/tw_paper_pipeline_execution_report_smoke.json`
- `/tmp/tw_paper_pipeline_execution_report_smoke.md`

说明：本轮 smoke 没有重新 submit，只验证 pipeline 可基于已有 verify/summary 产物直接输出 execution report；不把它当成新的交易闭环证明。

验证结果：`test_run_tw_stock_paper_pipeline.py` + `test_build_tw_stock_paper_execution_report.py` 为 `14 passed in 0.78s`。

安全状态：仍然 paper-only；没有连接 IBKR，也没有真实下单。

## Phase 4 paper sell 闭环

本轮完成真实 DB paper sell 闭环：

- 使用上一轮真实 paper buy 后的 6000 股 `2317` 作为当前持仓输入。
- 新建 `/tmp/tw_sell_loopback_plan.json`：目标权重 `2317=0.2`，在 `portfolio_value=5000000`、价格 `250.0` 下目标为 4000 股。
- `preview_tw_stock_paper_orders.py` 生成卖出 `2317 sell 2000 limit 248.75`。
- `run_tw_stock_paper_pipeline.py --submit` 通过本地 Agent quick-trade 提交 paper-only 卖单。
- Agent 返回 `paper-fill`，`order_uid=50e69d31373c4c1ab4de87329c541a42`。
- `verify_tw_stock_paper_orders.py` 查回成功：`matched_count=1`、`missing_count=0`。
- `/api/agent/v1/portfolio/paper-positions` 返回持仓从 6000 股降为 4000 股，`avg_price=250.0`、`cost_value=1000000.0`。
- `/api/agent/v1/portfolio/paper-summary?initial_cash=5000000` 返回：`cash=4000000.0`、`gross_buy_value=1500000.0`、`gross_sell_value=500000.0`、`realized_pnl=0.0`、`open_cost_value=1000000.0`、`equity_at_cost=5000000.0`。
- 生成卖出执行报告：
  - `/tmp/tw_paper_execution_report_sell_db_loopback.json`
  - `/tmp/tw_paper_execution_report_sell_db_loopback.md`

本轮补充测试：

- `backend/tests/test_preview_tw_stock_paper_orders.py` 增加目标低于当前持仓时生成 sell order 的覆盖。

注意事项：

- 该轮发现 `submit_tw_stock_paper_orders.py` 对卖单 payload 写入的 `current_qty` 等于卖出数量，而不是总当前持仓；此问题已在后续 `Phase 4 sell current_qty 修复` 中处理。

安全状态：仍然 paper-only；没有连接 IBKR，也没有真实下单。

## Phase 4 sell current_qty 修复

本轮修复 paper sell payload 的持仓数量语义：

- `preview_tw_stock_paper_orders.py` 的 order preview 新增 `current_qty` 字段，表示该 symbol 的当前总持仓。
- `submit_tw_stock_paper_orders.py` 对卖单 payload 优先使用 preview 中的 `current_qty/currentQty`，旧 preview 没有该字段时才回退到卖出数量。
- 这样 `quick_trade` 的 long-only 校验拿到的是真实当前持仓，而不是本次卖出数量。
- `test_preview_tw_stock_paper_orders.py` 增加卖出 order 的 `current_qty=6000` 断言。
- `test_submit_tw_stock_paper_orders.py` 增加优先使用 preview `current_qty` 和兼容旧 preview 回退到 `qty` 的覆盖。

smoke：

- 使用上一轮卖出场景 dry-run，不提交订单。
- 输出：
  - `/tmp/tw_paper_pipeline_sell_current_qty_fix_smoke.json`
  - `/tmp/tw_paper_pipeline_sell_current_qty_fix_preview.json`
  - `/tmp/tw_paper_pipeline_sell_current_qty_fix_submit.json`
- 结果：`2317 sell 2000` 的 preview 和 submit payload 均包含 `current_qty=6000`。

验证结果：`test_preview_tw_stock_paper_orders.py` + `test_submit_tw_stock_paper_orders.py` 为 `16 passed in 0.80s`。

安全状态：dry-run 验证，不提交订单；仍然 paper-only；没有连接 IBKR，也没有真实下单。


## Phase 4 post-submit paper report bundle

本轮新增提交后报告打包脚本：

- `backend/scripts/build_tw_stock_paper_report_bundle.py`
- `backend/tests/test_build_tw_stock_paper_report_bundle.py`

功能：读取 pipeline/submit JSON，调用只读 Agent API 查回 paper orders 和 paper summary，然后复用既有 execution report 生成 JSON/Markdown 审计报告。脚本不提交订单、不写数据库、不连接 IBKR。

真实本地 API 只读 smoke：

- 使用已有 paper buy pipeline：`/tmp/tw_paper_pipeline_db_loopback.json`
- 输出：
  - `/tmp/tw_paper_report_bundle_buy_db_smoke.json`
  - `/tmp/tw_paper_report_bundle_buy_verify_smoke.json`
  - `/tmp/tw_paper_report_bundle_buy_summary_smoke.json`
  - `/tmp/tw_paper_report_bundle_buy_execution_smoke.json`
  - `/tmp/tw_paper_report_bundle_buy_execution_smoke.md`
- 结果：`status=pass`、`matched_count=1`、`missing_count=0`、paper summary HTTP 200。
- 当前 DB 中已有 buy+sell 两笔 paper order，因此 summary 反映累计状态：`cash=4000000.0`、`gross_buy_value=1500000.0`、`gross_sell_value=500000.0`、`position_count=1`、`2317 quantity=4000`、`equity_at_cost=5000000.0`。

兼容验证：历史 sell pipeline 产物也可生成 bundle：`/tmp/tw_paper_report_bundle_sell_db_smoke.json`。该产物来自 current_qty 修复前的历史 pipeline，只作为兼容读取验证，不作为新提交证明。

验证结果：`test_build_tw_stock_paper_report_bundle.py` + `test_verify_tw_stock_paper_orders.py` + `test_build_tw_stock_paper_execution_report.py` 为 `14 passed in 0.10s`。

安全状态：真实 smoke 只读 API；仍然 paper-only；没有连接 IBKR，也没有真实下单；临时 Flask API 已停止。

下一步建议：执行真实多股票/ETF paper smoke。为避免污染已有 `2317` 累计状态，建议使用新 token 或新 symbol 组合，例如 `2330`、`0050`、`00878`，先 dry-run，再 submit，并用本轮 bundle 脚本生成完整报告。

## Phase 4 multi-stock/ETF paper smoke 与限价修复

本轮完成真实多股票/ETF paper smoke，并修复一个 paper fill 语义问题。

问题发现：

- 初始 dry-run 使用固定价格生成 `2330`、`0050`、`00878` 三笔订单。
- 真实 submit 时 quick-trade 使用最新日线收盘价模拟成交，但旧逻辑没有检查限价是否可成交。
- 因此出现 `2330 buy limit 1005.0` 却以 `fill_price=2255.0` 记录为 filled 的异常。
- 该异常发生在隔离测试用户上，已明确不作为最终通过样本。

修复：

- 修改 `backend/app/routes/agent_v1/quick_trade.py`。
- 新增 TWStock paper limit fill 判断：
  - buy：`last_price <= limit_price` 才 filled。
  - sell：`last_price >= limit_price` 才 filled。
  - 不满足时记录为 `rejected`，`fill_price=None`，note 写明原因。
- `backend/tests/test_agent_v1_twstock_quick_trade.py` 新增买入限价不可成交和卖出限价不可成交测试。

最终真实 smoke：

- 新建干净隔离用户/token：元信息在 `/tmp/tw_agent_token_multi_etf_clean_meta.json`，完整 token 只保存在本地 `/tmp/tw_agent_token_multi_etf_clean.txt`。
- 用 `TWStockDataSource` 获取最新真实日线收盘价，输出 `/tmp/tw_multi_etf_latest_prices.json`：
  - `2330=2255.0`
  - `0050=97.3`
  - `00878=28.27`
- `portfolio_value=5000000` 时，`2330` 低于一张，触发 `target_below_one_lot:2330`，这是整股规则的预期行为。
- 最终用 `portfolio_value=10000000` 覆盖股票 + ETF：
  - `0050 buy 30000 limit 97.79`，filled at `97.3`。
  - `00878 buy 70000 limit 28.41`，filled at `28.27`。
  - `2330 buy 1000 limit 2266.27`，filled at `2255.0`。

输出文件：

- `/tmp/tw_multi_etf_clean_10m_pipeline_dry_run.json`
- `/tmp/tw_multi_etf_clean_10m_pipeline_submit.json`
- `/tmp/tw_multi_etf_clean_10m_preview_submit.json`
- `/tmp/tw_multi_etf_clean_10m_submit.json`
- `/tmp/tw_multi_etf_clean_10m_report_bundle.json`
- `/tmp/tw_multi_etf_clean_10m_verify.json`
- `/tmp/tw_multi_etf_clean_10m_summary.json`
- `/tmp/tw_multi_etf_clean_10m_execution_report.json`
- `/tmp/tw_multi_etf_clean_10m_execution_report.md`
- `/tmp/tw_multi_etf_clean_10m_db_check.json`

最终结果：

- bundle `status=pass`。
- `submitted_count=3`、`failed_submit_count=0`。
- `matched_count=3`、`missing_count=0`。
- paper summary：`gross_buy_value=7152900.0`、`cash=2847100.0`、`position_count=3`、`equity_at_cost=10000000.0`。
- DB 直接核对：`limit_violations=[]`。

验证结果：Phase 4 paper 相关测试 `56 passed in 1.37s`。

安全状态：仍然 `AGENT_LIVE_TRADING_ENABLED=false`；全部为 paper-only；没有连接 IBKR，也没有真实下单；临时 Flask API 已停止。

下一步建议：进入 Phase 4 后半段，增加“paper rebalance 后续调仓/卖出”多标的 smoke，或者开始整理 IBKR paper/live 启用前置清单与禁止条件。

## Phase 4 multi-stock/ETF 后续调仓 smoke

本轮基于上一轮干净隔离用户的 `2330`、`0050`、`00878` paper 持仓，验证后续 rebalance。

输入：

- 当前持仓来自 `/tmp/tw_multi_etf_clean_10m_summary.json`，转换为 `/tmp/tw_multi_etf_rebalance_positions.json`。
- 新计划 `/tmp/tw_multi_etf_rebalance_plan.json`：`2330=50%`、`0050=10%`、`00878=20%`、现金约 `20%`。
- 价格继续使用 `/tmp/tw_multi_etf_latest_prices.json`。

Dry-run：

- 输出 `/tmp/tw_multi_etf_rebalance_pipeline_dry_run.json`。
- 生成 2 笔订单，无 warning/blocked：
  - `0050 sell 20000 limit 96.81`，payload 带 `current_qty=30000`。
  - `2330 buy 1000 limit 2266.27`。
- `00878` 目标与当前整股数量一致，不调仓。

真实 paper submit 与报告：

- `/tmp/tw_multi_etf_rebalance_pipeline_submit.json`
- `/tmp/tw_multi_etf_rebalance_preview_submit.json`
- `/tmp/tw_multi_etf_rebalance_submit.json`
- `/tmp/tw_multi_etf_rebalance_report_bundle.json`
- `/tmp/tw_multi_etf_rebalance_verify.json`
- `/tmp/tw_multi_etf_rebalance_summary.json`
- `/tmp/tw_multi_etf_rebalance_execution_report.json`
- `/tmp/tw_multi_etf_rebalance_execution_report.md`
- `/tmp/tw_multi_etf_rebalance_db_check.json`

结果：

- `submitted_count=2`、`failed_submit_count=0`。
- `matched_count=2`、`missing_count=0`。
- paper summary：`cash=2538100.0`、`gross_buy_value=9407900.0`、`gross_sell_value=1946000.0`、`open_cost_value=7461900.0`、`equity_at_cost=10000000.0`。
- 最终持仓：`0050=10000`、`00878=70000`、`2330=2000`。
- DB 直接核对：`limit_violations=[]`。

验证结果：Phase 4 paper 相关测试 `56 passed in 1.34s`。

安全状态：仍然 `AGENT_LIVE_TRADING_ENABLED=false`；全部为 paper-only；没有连接 IBKR，也没有真实下单；临时 Flask API 已停止。

下一步建议：整理 Phase 4 的 IBKR paper/live 启用前置清单、禁止条件、配置项和人工审批步骤；或者继续补一个“不可成交限价被 rejected 且不进入持仓”的真实 API smoke。

## Phase 4 不可成交限价 rejected smoke

本轮验证不可成交限价单不会进入持仓，并修正报告状态。

实现修正：

- `backend/scripts/build_tw_stock_paper_execution_report.py` 新增 rejected submit result 检测。
- 当 submit HTTP 成功但 paper order `status=rejected` 时，execution report 和 bundle 状态为 `warning`，原因 `rejected_paper_orders`。
- `backend/tests/test_build_tw_stock_paper_execution_report.py` 新增 rejected submit result 测试。

真实 smoke：

- 新建隔离 paper-only 用户/token：元信息 `/tmp/tw_agent_token_rejected_limit_meta.json`，完整 token `/tmp/tw_agent_token_rejected_limit.txt`。
- 输入：
  - `/tmp/tw_rejected_limit_plan.json`
  - `/tmp/tw_rejected_limit_prices.json`
- dry-run 生成 `2330 buy 2000 limit 1005.0`。
- 真实 quick-trade 最新价为 `2255.0`，买入限价不可成交，订单记录为 `rejected`，note 为 `paper limit not marketable: last_price 2255.0 > buy limit 1005.0`。

输出：

- `/tmp/tw_rejected_limit_pipeline_dry_run.json`
- `/tmp/tw_rejected_limit_pipeline_submit.json`
- `/tmp/tw_rejected_limit_preview_submit.json`
- `/tmp/tw_rejected_limit_submit.json`
- `/tmp/tw_rejected_limit_report_bundle.json`
- `/tmp/tw_rejected_limit_verify.json`
- `/tmp/tw_rejected_limit_summary.json`
- `/tmp/tw_rejected_limit_execution_report.json`
- `/tmp/tw_rejected_limit_execution_report.md`
- `/tmp/tw_rejected_limit_db_check.json`

结果：

- bundle `status=warning`，`status_reasons=["rejected_paper_orders"]`。
- `matched_count=1`、`missing_count=0`。
- `rejected_submit_count=1`。
- paper summary：`filled_order_count=0`、`position_count=0`、`cash=5000000.0`、`equity_at_cost=5000000.0`。
- DB 直接核对：`rejected_count=1`、`filled_count=0`，rejected order 不进入持仓。

验证结果：Phase 4 paper 相关测试 `57 passed in 1.38s`。

安全状态：仍然 `AGENT_LIVE_TRADING_ENABLED=false`；全部为 paper-only；没有连接 IBKR，也没有真实下单；临时 Flask API 已停止。

下一步建议：整理 Phase 4 的 IBKR paper/live 启用前置清单、禁止条件、环境变量、人工审批步骤和回滚方案。

## Phase 4 IBKR paper/live preflight 清单

本轮新增 IBKR paper/live 启用前置检查脚本：

- `backend/scripts/preflight_tw_stock_ibkr_live.py`
- `backend/tests/test_preflight_tw_stock_ibkr_live.py`

脚本定位：

- 只读 preflight。
- 默认不连接 IBKR TWS/Gateway。
- 不查询账户。
- 不提交订单。
- 用于检查本地配置、Agent token、broker policy 和 TWStock 合约映射是否满足进入 IBKR paper/live 评估的最低条件。

检查项：

- `IBKR + TWStock + spot + long` 被 broker policy 接受。
- `ALLOW_LOCAL_DESKTOP_BROKERS=true`。
- paper preflight 中 `AGENT_LIVE_TRADING_ENABLED=false`。
- `IBKR_ORDER_CLIENT_ID` 不使用 `1`，默认建议 `7`。
- Agent token active，包含 `R,T` scope，允许 `TWStock`，paper preflight 中 `paper_only=true`。
- 合约映射：`2330 -> TWSE/TWD`、`0050 -> TWSE/TWD`、`TPEX:6488 -> TPEX/TWD`。

真实只读 smoke：

```bash
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger AGENT_LIVE_TRADING_ENABLED=false ALLOW_LOCAL_DESKTOP_BROKERS=true IBKR_ORDER_CLIENT_ID=7 python   backend/scripts/preflight_tw_stock_ibkr_live.py   --symbol 2330,0050,TPEX:6488   --agent-token <local-paper-token>   --output-json /tmp/tw_ibkr_preflight_paper_smoke.json   --output-md /tmp/tw_ibkr_preflight_paper_smoke.md
```

结果：

- `status=pass`。
- `error_count=0`。
- `warning_count=0`。
- `connects_to_ibkr=false`。
- `submits_orders=false`。

live promotion 红线：

- 任一 error check 失败时不得启用 live。
- 无明确人工审批时不得使用 `paper_only=false` Agent token。
- 策略/order worker 不使用 `clientId=1`，避免挤掉手工 UI session。
- TPEx 官方数据未完成对账前，不建议实盘交易 TPEX 标的。

验证结果：Phase 4/IBKR preflight 相关测试 `87 passed in 1.22s`。

安全状态：本步没有启动 Flask API，没有连接 IBKR，没有真实下单；仍未进入 live。

下一步建议：补一份 `docs` 内的正式 IBKR 台股 paper/live 操作手册，或继续做 live preflight fail-case smoke，证明在缺少 `paper_only=false`、live kill switch、IBKR env 时会阻止 live promotion。

## Phase 4 IBKR live preflight fail-case smoke

本轮执行 live preflight 的失败用例，验证缺少 live 条件时会阻止 live promotion。

命令要点：

- 使用 `preflight_tw_stock_ibkr_live.py --require-live --require-ibkr-env`。
- 输入 symbol：`2330,0050,TPEX:6488`。
- 使用本地 paper-only Agent token。
- 环境：`AGENT_LIVE_TRADING_ENABLED=false`、`ALLOW_LOCAL_DESKTOP_BROKERS=true`、`IBKR_ORDER_CLIENT_ID=7`。
- 未提供 `IBKR_HOST/IBKR_PORT`。
- 不连接 IBKR，不查询账户，不提交订单。

输出：

- `/tmp/tw_ibkr_preflight_live_fail_smoke.json`
- `/tmp/tw_ibkr_preflight_live_fail_smoke.md`

结果：

- 预期退出码 `1`。
- `status=fail`。
- `error_count=4`。
- `warning_count=0`。
- `connects_to_ibkr=false`。
- `submits_orders=false`。

4 个阻断项：

- `agent_live_kill_switch`：live promotion 需要 `AGENT_LIVE_TRADING_ENABLED=true`，当前为 `false`。
- `ibkr_env_host`：未配置 IBKR host。
- `ibkr_env_port`：未配置 IBKR port。
- `agent_token:paper_only_mode`：当前 token 仍为 `paper_only=true`，live promotion 需要明确人工审批后的 `paper_only=false`。

通过项：

- `IBKR + TWStock + spot + long` broker policy 通过。
- `validate_strategy_config` 通过。
- `ALLOW_LOCAL_DESKTOP_BROKERS=true` 通过。
- `IBKR_ORDER_CLIENT_ID=7` 通过。
- Agent token active，具备 `R,T` scope，允许 `TWStock`。
- `2330/0050 -> TWSE/TWD`，`TPEX:6488 -> TPEX/TWD` 映射通过。

验证结果：preflight/policy/symbol 测试 `68 passed in 1.16s`。

安全状态：本步没有启动 Flask API，没有连接 IBKR，没有真实下单；live promotion 被正确拦截。

下一步建议：补正式的 IBKR 台股 paper/live 操作手册，包含人工审批、配置步骤、paper 账户验证、最小实盘试单、回滚和禁用流程。

## Phase 4 IBKR 台股 paper/live 操作手册

本轮新增正式中文手册：

- `docs/IBKR_TWSTOCK_TRADING_GUIDE_CN.md`

手册定位：

- 不是实盘授权。
- 默认路径仍是 paper-only。
- 任何 live promotion 都必须人工审批。
- 必须先通过 preflight、paper 订单、持仓汇总、rejected 限价单验证和回滚检查。

覆盖内容：

- 当前支持状态与 TWSE / TPEX 合约映射。
- 禁止进入 live 的条件。
- `AGENT_LIVE_TRADING_ENABLED`、`ALLOW_LOCAL_DESKTOP_BROKERS`、`IBKR_ORDER_CLIENT_ID`、`IBKR_HOST`、`IBKR_PORT` 等配置。
- TWS / IB Gateway 设置。
- paper preflight 和 live preflight 命令。
- paper 账户验证流程。
- live promotion 审批清单。
- 最小 live 试单规则。
- 回滚与禁用步骤。
- 当前未完成项。

关键红线：

- 任一 preflight error 不得启用 live。
- 未经审批不得设置 `AGENT_LIVE_TRADING_ENABLED=true`。
- 未经审批不得使用 `paper_only=false` token。
- 策略/order worker 不使用 `clientId=1`。
- TPEx 标的在官方数据未完成对账前不建议 live。

验证结果：关键章节检查通过，手册共 224 行。

安全状态：本步只写文档；没有启动 Flask API，没有连接 IBKR，没有真实下单。

下一步建议：如果继续 Phase 4，可做“IBKR paper broker 连接前模拟演练清单”或开始 Phase 5，整理部署/定时任务/监控告警。



## Phase 5A：只读台股趋势 API

本轮按新的主线目标新增只读台股趋势研究接口，定位是“用户需要时查询台股趋势”，并为后续自动监控提醒提供基础；接口返回趋势和质量信息，但不是交易指令，也不会实盘下单。

新增文件：

- `backend/app/services/tw_stock_trend.py`
- `backend/app/routes/tw_stock.py`
- `backend/tests/test_tw_stock_trend_api.py`

已注册路由：

- `GET /api/tw-stock/trend?symbol=2330&limit=120`：单一台股/ETF 趋势报告。
- `GET /api/tw-stock/trends?symbols=2330,0050,00878&limit=120`：观察列表趋势报告，并按趋势分数排名。

返回内容包括：最新日线日期、收盘价、成交量、5/20/60 日收益率、MA5/MA20/MA60、量比、20 日年化波动率、趋势标签、趋势分数、数据质量和交易安全字段。

真实本地 API smoke：

- 单标的 `2330`：`exchange=TWSE`，`latest.date=2026-05-21`，`close=2255.0`，`trend.label=uptrend`，`score=90.04`，`quality.bar_count=120`，`stale_days=3`，`warnings=[]`，`trading.orders_enabled=false`。
- 观察列表 `2330,0050,00878`：`ok_count=3`，排名为 `00878=97.57`、`0050=95.22`、`2330=90.04`；三个标的均为 `exchange=TWSE`，`latest_date=2026-05-21`，`warnings=[]`；watchlist 级别 `trading.orders_enabled=false`。

验证命令：

```bash
python -m pytest \
  backend/tests/test_tw_stock_trend_api.py \
  backend/tests/test_tw_stock_kline_api.py \
  backend/tests/test_tw_stock_data_source.py -q
```

结果：`29 passed in 0.92s`。

安全状态：本步只读查询行情和计算趋势；没有提交 paper order；没有连接 IBKR；没有真实下单；`AGENT_LIVE_TRADING_ENABLED=false`。

下一步建议：进入 Phase 5B，做一个轻量前端或已有前端入口，用于输入台股代码、展示趋势分数、均线、收益、成交量、风险和数据质量；再进入 Phase 5C，加入观察列表自动刷新、趋势变化提醒和人工确认流程。


## Phase 5B：台股趋势与监控面板

本轮新增后端托管的轻量台股趋势监控页面，作为 Phase 5A 只读趋势 API 的可视化入口。由于当前仓库没有独立前端工程，先采用 Flask 直接返回 HTML/CSS/JS 的方式，避免新增 Node 构建链。

新增/修改：

- `backend/app/routes/tw_stock.py`：新增 `GET /api/tw-stock/monitor`。
- `backend/tests/test_tw_stock_trend_api.py`：新增页面只读与 API 依赖测试。

页面能力：

- 默认观察列表：`2330,0050,00878`。
- 可编辑观察列表和日线数量 `limit`。
- 支持手动刷新。
- 支持自动监控开关和刷新频率：手动、1 分钟、5 分钟、15 分钟。
- 支持分数变化提醒阈值。
- 展示趋势标签、趋势分数、最新日期/收盘价、5/20/60 日收益、MA20/MA60、量比、20 日年化波动率和数据质量。
- 使用 `localStorage` 保存观察列表、limit、刷新频率和提醒阈值。
- 自动监控输出为提醒和解释，不提供买卖按钮，不提交订单。

真实 smoke：

- 启动本地 API：`AGENT_LIVE_TRADING_ENABLED=false`、`ENABLE_PENDING_ORDER_WORKER=false`、`ENABLE_PORTFOLIO_MONITOR=false`。
- `GET http://127.0.0.1:5000/api/tw-stock/monitor` 返回 `200 OK`，`Content-Type=text/html`。
- 页面依赖的 `GET /api/tw-stock/trends?symbols=2330,0050,00878&limit=120` 返回 `ok_count=3`。
- 最新数据仍为 `2026-05-21`；`2330=90.04`、`0050=95.22`、`00878=97.57`；`warnings=[]`；`orders_enabled=false`。
- Playwright 截图成功：`/tmp/tw_stock_monitor_phase5b.png`。

验证命令：

```bash
python -m pytest \
  backend/tests/test_tw_stock_trend_api.py \
  backend/tests/test_tw_stock_kline_api.py \
  backend/tests/test_tw_stock_data_source.py -q
```

结果：`30 passed in 0.95s`。

安全状态：页面和 API 均为只读研究/提醒用途；没有 paper submit；没有连接 IBKR；没有真实下单；测试后本地 Flask API 应停止。

下一步建议：进入 Phase 5C，加入后端 watchlist/alert 配置持久化和提醒历史，避免提醒只存在浏览器内存中。


## Phase 5C：台股监控配置与提醒历史持久化

本轮把 Phase 5B 的浏览器内存监控推进到后端持久化：观察列表、刷新频率、提醒阈值和提醒历史可以保存到本地 PostgreSQL。该能力仍然是研究提醒，不做买卖决策，也不提交订单。

新增/修改：

- `backend/migrations/init.sql`：新增 `qd_tw_stock_monitor_configs` 和 `qd_tw_stock_monitor_alerts`。
- `backend/app/routes/tw_stock.py`：新增监控配置和提醒历史 API，并让 `/api/tw-stock/monitor` 页面接入这些 API。
- `backend/tests/test_tw_stock_trend_api.py`：新增配置保存/读取、提醒创建/查询/确认测试。

新增 API：

- `GET /api/tw-stock/monitor/config`：读取监控配置；无记录时返回默认配置。
- `POST|PUT /api/tw-stock/monitor/config`：保存观察列表、日线数量、刷新频率、分数变化阈值、监控启用状态和备注。
- `GET /api/tw-stock/monitor/alerts?limit=50&unread_only=false`：读取提醒历史。
- `POST /api/tw-stock/monitor/alerts`：记录趋势变化、分数变化或数据质量提醒。
- `PUT /api/tw-stock/monitor/alerts/<id>`：标记提醒已读，并保存人工判断状态和备注。

页面更新：

- 页面启动时先读取后端配置，失败时回退到 `localStorage`。
- 配置变化时同时保存后端和 `localStorage`。
- 监控触发趋势标签变化、分数变化或数据质量提示时，会写入后端提醒历史。
- 页面显示最近提醒，并提供“已读”按钮；按钮会调用后端确认接口。
- 页面仍明确显示“只读：不下单”。

真实 PostgreSQL smoke：

- 本地 API 启动时自动应用 `init.sql`，日志显示 `Applied init.sql (67524 bytes)`，DB permission probe 通过。
- `POST /monitor/config` 返回 `200`，保存 `['2330', '0050', '00878']`，`enabled=True`。
- `GET /monitor/config` 返回 `200`，`refresh_interval_sec=300`。
- `POST /monitor/alerts` 返回 `200`，创建 alert id `1`，`is_read=False`。
- `GET /monitor/alerts?limit=5` 返回 `200`，`count=1`。
- `PUT /monitor/alerts/1` 返回 `200`，`is_read=True`，`decision_status=watch`。
- 页面 HTML 包含 `monitor/config`、`monitor/alerts`、`只讀：不下單`。
- Playwright 截图成功：`/tmp/tw_stock_monitor_phase5c.png`。

验证命令：

```bash
python -m pytest \
  backend/tests/test_tw_stock_trend_api.py \
  backend/tests/test_tw_stock_kline_api.py \
  backend/tests/test_tw_stock_data_source.py \
  backend/tests/test_market_symbols_seed_sql.py -q
```

结果：`43 passed in 0.92s`。

安全状态：没有提交 paper order；没有连接 IBKR；没有真实下单；`AGENT_LIVE_TRADING_ENABLED=false`。本步只是保存监控配置和提醒历史，决策仍由用户人工完成。

下一步建议：进入 Phase 5D，做后端定时监控 worker 或手动触发扫描 API，让提醒不依赖浏览器页面打开。


## Phase 5D：后端手动扫描与趋势状态比较

本轮新增后端扫描能力，让台股监控提醒不再只能依赖浏览器页面内存。后端可以读取已保存的监控配置，拉取趋势报告，与上次扫描状态比较，并把趋势变化、分数变化或新增数据质量提示写入提醒历史。

新增/修改：

- `backend/migrations/init.sql`：新增 `qd_tw_stock_monitor_states`，保存每个监控配置下每个 symbol 的上次趋势标签、分数、最新日期、质量提示和完整快照。
- `backend/app/routes/tw_stock.py`：新增后端扫描逻辑和 API。
- `backend/tests/test_tw_stock_trend_api.py`：新增后端扫描基线、变化提醒、禁用配置跳过测试。
- `/api/tw-stock/monitor` 页面新增“后端扫描”按钮。

新增 API：

- `POST /api/tw-stock/monitor/scan`：扫描指定监控配置。默认配置 disabled 时跳过；传 `force=true` 可强制扫描。
- `POST /api/tw-stock/monitor/scan-all`：扫描已启用的监控配置，供 cron 或人工触发使用；最多一次处理 100 个配置。

扫描规则：

- 首次扫描建立基线，不因没有历史状态而制造趋势变化提醒；若当前数据已有质量 warnings，则会写入质量提醒。
- 后续扫描比较：趋势标签变化、趋势分数变化超过阈值、新增数据质量 warnings。
- 每次成功扫描会更新 `qd_tw_stock_monitor_states`。
- 生成的提醒写入 `qd_tw_stock_monitor_alerts`，供页面或 API 人工审阅。
- 返回体固定包含 `trading.orders_enabled=false`，明确不下单。

真实 PostgreSQL smoke：

- 本地 API 启动自动应用 `init.sql`，日志显示 `Applied init.sql (68321 bytes)`。
- 保存配置 `phase5d-smoke`：`symbols=['2330','0050','00878']`，`enabled=True`，成功。
- `POST /monitor/scan`：`status=scanned`，`scanned_count=3`，`alert_count=0`，`orders_enabled=false`。
- `POST /monitor/scan` with `force=true`：`status=scanned`，`scanned_count=3`，`alert_count=0`，`orders_enabled=false`。
- `GET /monitor/alerts?name=phase5d-smoke&limit=10`：`count=0`。这表示同一批真实数据没有趋势变化或新增质量提示，属于预期结果。
- 页面包含“后端扫描”按钮和 `/api/tw-stock/monitor/scan` 调用。
- Playwright 截图成功：`/tmp/tw_stock_monitor_phase5d.png`。

验证命令：

```bash
python -m pytest \
  backend/tests/test_tw_stock_trend_api.py \
  backend/tests/test_tw_stock_kline_api.py \
  backend/tests/test_tw_stock_data_source.py \
  backend/tests/test_market_symbols_seed_sql.py -q
```

结果：`45 passed in 0.94s`。

安全状态：没有提交 paper order；没有连接 IBKR；没有真实下单；`AGENT_LIVE_TRADING_ENABLED=false`。本步只生成研究提醒和扫描状态。

下一步建议：进入 Phase 5E，把 `scan-all` 接入一个可选后台 worker 或部署级 cron，并增加运行日志/失败重试，形成完整的自动监控提醒链路。


## Phase 5E：可选后台 worker 与扫描日志

本轮把 Phase 5D 的手动 `scan-all` 推进为可部署的自动监控链路：新增可选后台 worker 和扫描日志。默认不启用 worker，避免本地开发时自动访问数据源；启用后只会扫描已启用的台股监控配置、写入提醒和扫描日志，不会下单，不会连接 broker。

新增/修改：

- `backend/migrations/init.sql`：新增 `qd_tw_stock_monitor_scan_logs`。
- `backend/app/routes/tw_stock.py`：`scan-all` 抽为 `run_tw_stock_monitor_scan_all()`，新增 `GET /api/tw-stock/monitor/scan-logs`。
- `backend/app/services/tw_stock_monitor_worker.py`：新增可选后台 worker。
- `backend/app/__init__.py`：启动时按环境变量尝试启动台股监控 worker。
- `backend/tests/test_tw_stock_monitor_worker.py`：新增 worker 启停测试。

新增 API：

- `GET /api/tw-stock/monitor/scan-logs?limit=20`：查询最近扫描日志。

新增环境变量：

- `ENABLE_TW_STOCK_MONITOR_WORKER=false`：默认关闭；设为 `true` 才启动后台 worker。
- `TW_STOCK_MONITOR_INTERVAL_SEC=900`：扫描间隔，最小 30 秒，最大 86400 秒。
- `TW_STOCK_MONITOR_FORCE_SCAN=false`：是否强制扫描 disabled 配置；默认只扫描 enabled 配置。

真实 smoke：

- 启动 API 时设置 `ENABLE_TW_STOCK_MONITOR_WORKER=false`，日志显示：`TWStock monitor worker is disabled. Set ENABLE_TW_STOCK_MONITOR_WORKER=true to enable.`
- 启动自动应用 `init.sql`，日志显示 `Applied init.sql (69063 bytes)`。
- 保存 `phase5e-smoke` 监控配置成功。
- `POST /api/tw-stock/monitor/scan-all` 返回：`count=3`、`total_scanned_count=8`、`total_alert_count=0`、`orders_enabled=false`。
- `GET /api/tw-stock/monitor/scan-logs?limit=1` 返回最新日志：`trigger_source=api`、`status=success`、`monitor_count=3`、`scanned_count=8`、`alert_count=0`、`duration_ms=2511`。
- 页面仍包含“后端扫描”和“只读：不下单”。

验证命令：

```bash
python -m pytest \
  backend/tests/test_tw_stock_trend_api.py \
  backend/tests/test_tw_stock_monitor_worker.py \
  backend/tests/test_tw_stock_kline_api.py \
  backend/tests/test_tw_stock_data_source.py \
  backend/tests/test_market_symbols_seed_sql.py -q
```

结果：`48 passed in 0.95s`。

安全状态：没有提交 paper order；没有连接 IBKR；没有真实下单；`AGENT_LIVE_TRADING_ENABLED=false`。worker 默认关闭，启用后也只生成研究提醒和日志。

下一步建议：进入 Phase 5F，做部署说明和运维手册：如何本地启动 PostgreSQL/API/worker、如何访问趋势面板、如何看扫描日志、如何关闭监控、如何清理 smoke 配置。


## Phase 5F：部署与运维手册

本轮新增独立中文部署/运维手册：

- `docs/TW_STOCK_MONITOR_DEPLOYMENT_CN.md`

手册定位：把 Phase 5A-5E 的台股趋势查询、监控面板、配置持久化、提醒历史、后端扫描、后台 worker 和扫描日志整理成可执行的部署流程。

覆盖内容：

- 能力边界：研究与提醒，不自动买卖，不连接 broker。
- 推荐环境变量：`DATABASE_URL`、`AGENT_LIVE_TRADING_ENABLED=false`、`ENABLE_TW_STOCK_MONITOR_WORKER` 等。
- 本地 API 启动命令。
- 趋势面板访问地址：`/api/tw-stock/monitor`。
- 观察列表配置、手动扫描、scan-all、提醒查询、提醒已读、扫描日志查询。
- worker 启用/关闭方式。
- 数据质量字段和 warnings。
- 故障排查与 smoke 数据清理。
- 部署后自检清单。

同时已把手册加入 `docs/README_CN.md` 文档导航，并在 `docs/TAIWAN_STOCK_QUANT_RESEARCH_CN.md` 中记录 Phase 5F。

验证结果：文档关键章节、关键环境变量、关键 API、README 链接检查通过；手册共 313 行；Phase 5 相关回归测试 `48 passed in 1.03s`。

安全状态：本步只写文档；没有启动 API；没有连接 IBKR；没有提交任何订单。

下一步建议：如果继续 Phase 5，可做一次“从空配置到启用 worker 的完整演练”，或者整理剩余技术债和最终验收清单。


## Phase 5G：从空配置到启用 worker 的完整演练

本轮按 Phase 5F 运维手册做端到端演练，验证从新建监控配置、访问面板、手动 scan-all、查询扫描日志，到启用后台 worker 自动扫描的完整链路。

演练步骤：

1. 启动本地 API，显式关闭交易和后台交易相关 worker：`AGENT_LIVE_TRADING_ENABLED=false`、`ENABLE_PENDING_ORDER_WORKER=false`、`ENABLE_PORTFOLIO_MONITOR=false`、`ENABLE_TW_STOCK_MONITOR_WORKER=false`。
2. 新建监控配置 `phase5g-e2e`：`symbols=['2330','0050']`、`limit_bars=120`、`refresh_interval_sec=60`、`score_change_threshold=8`、`enabled=true`。
3. 读取配置，确认 `refresh_interval_sec=60`。
4. 访问 `/api/tw-stock/monitor`，页面返回 `200`，包含“台股趨勢監控”和“只讀：不下單”。
5. 调用 `POST /api/tw-stock/monitor/scan-all`，返回 `count=4`、`total_scanned_count=10`、`total_alert_count=0`、`orders_enabled=false`。
6. 查询 `GET /api/tw-stock/monitor/scan-logs?limit=1`，最新日志为 `trigger_source=api`、`status=success`、`monitor_count=4`、`scanned_count=10`、`alert_count=0`。
7. 停止 API 后，以 `ENABLE_TW_STOCK_MONITOR_WORKER=true`、`TW_STOCK_MONITOR_INTERVAL_SEC=30`、`TW_STOCK_MONITOR_FORCE_SCAN=false` 重启。
8. 启动日志显示 `TWStock monitor worker started: interval=30s force=False`。
9. worker 自动扫描日志显示 `TWStock monitor worker scan OK: configs=4 scanned=10 alerts=0`。
10. 查询 `scan-logs`，确认最新记录为 `trigger_source=worker`、`status=success`、`monitor_count=4`、`scanned_count=10`、`alert_count=0`、`duration_ms=1023`。
11. 停止 API/worker，确认 5000 端口释放。

验证结果：Phase 5 相关回归测试 `48 passed in 0.97s`。

结果解释：本轮真实数据没有产生新提醒，`alert_count=0` 是合理结果，表示相对上次扫描没有趋势标签变化、分数变化未超过阈值、也没有新增数据质量 warning。

安全状态：没有提交 paper order；没有连接 IBKR；没有真实下单；`orders_enabled=false`；worker 只生成研究扫描日志和提醒。

下一步建议：整理 Phase 5 最终验收清单和剩余技术债，或者按手册清理 `phase5c/5d/5e/5g` smoke 配置。


## Phase 5H：最终验收清单与剩余技术债

本轮新增独立验收文档：

- `docs/TW_STOCK_PHASE5_ACCEPTANCE_CN.md`

文档结论：Phase 5 可视为“研究版台股趋势监控”完成，能力包括按需趋势查询、趋势监控面板、监控配置持久化、提醒历史、后端扫描、可选后台 worker、扫描日志、部署手册和端到端 worker 演练。

验收文档覆盖：

- Phase 5A-5G 已完成能力。
- 最近回归测试和真实演练摘要。
- 上线前检查清单。
- 数据质量验收。
- 安全验收。
- 剩余技术债。
- 后续优先级建议。

核心边界：当前不是实时行情系统，不是自动交易系统，不是实盘下单系统，不是已验证可盈利策略，也不是投资建议系统。

验证结果：验收文档关键章节、README 链接、研究文档链接、运维手册链接检查通过；验收文档共 198 行；Phase 5 相关回归测试 `48 passed in 0.96s`。

安全状态：本步只写文档；没有启动 API；没有连接 IBKR；没有提交任何订单。

下一步建议：如果继续，可以清理 smoke 配置，或进入 Phase 6 做提醒推送、趋势图表、正式 Vue 前端接入。


## Phase 5 Smoke 配置清理

按用户要求清理 Phase 5 smoke 监控配置，目标名称：

- `phase5c-smoke`
- `phase5d-smoke`
- `phase5e-smoke`
- `phase5g-e2e`

清理前本地 PostgreSQL 状态：

- configs：`phase5d-smoke=1`、`phase5e-smoke=1`、`phase5g-e2e=1`；未发现 `phase5c-smoke`。
- alerts：上述名称均为 `0`。
- states：`phase5d-smoke=3`、`phase5e-smoke=2`、`phase5g-e2e=2`。

执行清理：

- `qd_tw_stock_monitor_alerts` 删除 `0` 行。
- `qd_tw_stock_monitor_states` 删除 `7` 行。
- `qd_tw_stock_monitor_configs` 删除 `3` 行。

复查结果：

- 上述 smoke configs、alerts、states 均剩余 `0`。
- `default` 监控配置仍保留，`default_configs=1`。
- `qd_tw_stock_monitor_scan_logs` 未清理，因为该表没有 `monitor_name` 字段，无法按 smoke 配置名精准删除；为避免误删真实扫描日志，本轮保留。

安全状态：只清理本地 PostgreSQL 中明确的 smoke 监控配置和关联状态；没有启动 API；没有连接 IBKR；没有提交任何订单。


## Phase 5 进入 Phase 6 前审视

本轮按用户要求审视 Phase 5 是否完整、准确、是否偏离主线。

审视结论：

- 主线没有偏离。Phase 5 已从交易执行转为“按需查询 + 自动监控提醒 + 人工决策”，符合用户当前目标。
- 代码边界正确。Phase 5 代码集中在 `backend/app/routes/tw_stock.py`、`backend/app/services/tw_stock_trend.py`、`backend/app/services/tw_stock_monitor_worker.py`，没有调用 quick-trade、broker client、IBKR client 或下单路径。
- 返回边界正确。趋势、scan、scan-all 返回中保留 `orders_enabled=false`，页面无买卖按钮。
- worker 边界正确。`ENABLE_TW_STOCK_MONITOR_WORKER` 默认关闭；启用后只执行 `scan-all`、写提醒和扫描日志，不下单。
- 数据链路准确。当前是台股日线研究数据，不是盘中实时行情；文档已明确 `KlineService:TWStock:1D`、`stale_days`、`warnings` 和数据质量检查。
- 文档完整。已有部署运维手册、验收清单、断点记录、研究文档入口和 README 入口。
- smoke 配置已清理。`phase5d-smoke`、`phase5e-smoke`、`phase5g-e2e` configs/states 已删除；`default` 保留；scan logs 因无 `monitor_name` 字段未按配置名删除以避免误删。

本轮发现并修正的小问题：

- `docs/TW_STOCK_MONITOR_DEPLOYMENT_CN.md` 的 smoke 清理 SQL 示例原本只列 `phase5c/5d/5e`，本轮补入 `phase5g-e2e`。

仍然存在的限制，不阻塞进入 Phase 6：

- TPEx 官方 OpenAPI 对账在当前环境仍不稳定。
- 当前不是实时行情系统，只是日频趋势研究和提醒。
- worker 与 API 同进程，生产上更理想的是独立 worker/cron。
- 提醒只有本地页面/API，没有 Telegram/Email/Webhook 推送。
- 当前 Flask 托管页面是轻量实现，尚未接入正式 Vue 前端。

验证结果：Phase 5 相关回归测试 `48 passed in 1.03s`；确认 5000 端口无遗留监听。

结论：可以进入 Phase 6。

Phase 6 建议主线：提醒推送与趋势可视化增强，优先做不涉及交易的能力：

1. `Phase 6A`：提醒推送通道设计与最小实现，建议先做 Webhook/本地通知事件表，避免一开始绑定 Telegram/Email 凭证。
2. `Phase 6B`：趋势历史/分数历史 API，用于画趋势分数曲线。
3. `Phase 6C`：面板可视化增强，增加趋势历史图、提醒过滤、人工备注流。
4. `Phase 6D`：生产部署拆分 worker/cron，减少 API 同进程 worker 风险。

安全状态：本轮只审视、测试和修正文档；没有启动 API；没有连接 IBKR；没有提交任何订单。

## Phase 6A：站内通知桥接最小实现

本轮在确认 Phase 5 未偏离主线后进入 Phase 6。Phase 6 当前主线保持为“台股趋势研究 + 自动监控提醒 + 人工决策”，不做自动买卖、不连接券商、不启用实盘交易。

实现内容：

- 当台股监控产生 `qd_tw_stock_monitor_alerts` 记录时，同步写入现有站内通知表 `qd_strategy_notifications`。
- 通知字段约定：`strategy_id=NULL`、`signal_type=tw_stock_monitor`、`channels=browser`、`title=台股趋势提醒`。
- `payload_json` 包含 `source=tw_stock_monitor`、`alert_id`、`monitor_name`、`symbol`、`alert_type`、`severity` 和趋势快照。
- 通知写入采用 best-effort，并用 PostgreSQL savepoint 隔离；如果通知写入失败，原始台股 alert 不会因此失败。
- 手动创建 alert API 与后台 scan 产生的 alert 都会进入同一站内通知链路。

测试结果：

- 单元/回归测试：`48 passed in 0.99s`。覆盖 `test_tw_stock_trend_api.py`、`test_tw_stock_monitor_worker.py`、`test_tw_stock_kline_api.py`、`test_tw_stock_data_source.py`、`test_market_symbols_seed_sql.py`。
- 本地 PostgreSQL smoke：通过 Flask test client 创建 `phase6a-smoke` 台股提醒，确认 `qd_strategy_notifications` 写入成功：`signal_type=tw_stock_monitor`、`channels=browser`、`title=台股趋势提醒`、`payload_source=tw_stock_monitor`、`payload_monitor_name=phase6a-smoke`。
- smoke 数据已清理：删除本次 `phase6a-smoke` alert 和对应 notification。

安全边界：

- 没有提交 paper order。
- 没有连接 IBKR 或任何券商。
- 没有启用自动交易。
- `ENABLE_TW_STOCK_MONITOR_WORKER` 在 smoke 中保持关闭。
- 新增能力只是站内提醒事件，不构成投资建议或自动决策。

当前限制：

- Phase 6A 只完成站内/browser 通知桥接，还没有 Telegram、Email、Webhook 等外部推送。
- 站内通知复用了现有 `/api/strategies/notifications` 体系，后续需要在正式前端中增加台股提醒筛选或入口。
- 当前仍是日线趋势研究数据，不是盘中实时行情。

下一步建议：进入 Phase 6B，增加趋势分数/标签历史记录与查询 API，为前端趋势曲线和提醒变化回看做准备。

## Phase 6B：趋势历史记录与查询 API

本轮继续 Phase 6，在 Phase 6A 站内通知桥接之后，新增趋势历史能力，为后续前端趋势曲线、分数变化回看和人工复盘提供数据基础。

实现内容：

- 新增 append-only 历史表 `qd_tw_stock_trend_history`。
- 每次台股监控 scan 对某个 symbol 成功生成趋势报告时，追加一条历史记录。
- 历史记录保存：`user_id`、`monitor_name`、`symbol`、`label`、`score`、`latest_date`、`latest_close`、`warnings_json`、完整 `snapshot`、`scanned_at`。
- 新增只读 API：`GET /api/tw-stock/monitor/history?symbol=2330&limit=120`。
- API 返回按时间正序排列的历史点，包含 `trading.orders_enabled=false`，明确仍为研究数据。
- 若缺少 `symbol` 参数，API 返回 `400` 和 `Missing symbol parameter`。

测试结果：

- 单元/回归测试：`49 passed in 1.05s`。新增覆盖 scan 后写入趋势历史、history API 正序返回、缺少 symbol 参数校验。
- 本地 PostgreSQL smoke：启动 Flask test client 并自动应用迁移，写入 `phase6b-smoke` 历史记录，再通过 `/api/tw-stock/monitor/history?monitor_name=phase6b-smoke&symbol=2330&limit=5` 读取成功。
- smoke 返回关键结果：`history_count=1`、`history_symbol=2330`、`orders_enabled=False`、`first_label=uptrend`、`first_score=88.5`、`first_latest_date=2026-05-22`。
- smoke 数据已清理：删除本次 `phase6b-smoke` 历史记录。

安全边界：

- 没有提交 paper order。
- 没有连接 IBKR 或任何券商。
- 没有启用自动交易。
- `ENABLE_TW_STOCK_MONITOR_WORKER` 在 smoke 中保持关闭。
- 新增 API 只读，不返回任何买卖指令。

当前限制：

- 历史数据从 Phase 6B 之后的 scan 开始积累；历史表不会自动还原 Phase 6B 之前没有保存过的扫描点。
- 当前历史点以“扫描时间”为序，不是分钟级行情；仍是日线趋势研究。
- 尚未在监控页面画趋势曲线，这会放到 Phase 6C。

下一步建议：进入 Phase 6C，把趋势历史 API 接入监控页面，增加分数曲线、标签历史、提醒过滤和人工备注入口。

## Phase 6C：监控页面趋势可视化与人工复盘入口

本轮在 Phase 6B 趋势历史 API 基础上增强现有 Flask 托管监控页面，仍保持“研究提醒 + 人工决策”的主线。

实现内容：

- 页面新增“趋势分数曲线”区域，使用 `canvas#trendChart` 绘制历史分数曲线。
- 新增 `chartSymbol` 选择器和“载入曲线”按钮，从 `/api/tw-stock/monitor/history` 读取历史点。
- 刷新趋势列表后自动同步可选 symbol，并尝试载入当前 symbol 的历史曲线。
- 后端扫描完成后刷新趋势列表、提醒列表和趋势曲线。
- 页面新增“提醒与人工备注”区域。
- 新增提醒过滤：全部提醒 / 未读提醒。
- 每条提醒新增人工状态按钮：`观察`、`忽略`、`已处理`；这些按钮只调用 alert 更新 API，写入 `decision_status` 和 `user_note`，不触发任何交易。
- 页面继续保留“只读：不下单”文案和 `orders_enabled=false` 后端边界。

测试结果：

- 单元/回归测试：`49 passed in 1.07s`。新增页面断言覆盖趋势曲线控件、history API 调用、提醒过滤和人工状态按钮。
- 前端脚本语法检查：从页面模板抽出内联 JS，执行 `node --check /tmp/tw_stock_monitor_phase6c.js`，通过。
- 本地 Flask/PostgreSQL smoke：访问 `/api/tw-stock/monitor` 返回 `200`，确认页面包含 `trendChart`、`/api/tw-stock/monitor/history?symbol=`、`alertFilter`、`data-status=watch/ignored/acted` 和“只读：不下单”。

安全边界：

- 没有提交 paper order。
- 没有连接 IBKR 或任何券商。
- 没有启用自动交易。
- `ENABLE_TW_STOCK_MONITOR_WORKER` 在 smoke 中保持关闭。
- 页面按钮只更新研究提醒状态，不代表买卖建议，也不产生订单。

当前限制：

- 当前仍是轻量 Flask 页面，不是正式 Vue 前端。
- 曲线使用原生 canvas，足够做 smoke 和研究查看；后续正式前端可换成图表库。
- 趋势曲线依赖 Phase 6B 之后的 scan 历史积累。

下一步建议：进入 Phase 6D，把 worker/cron 部署拆分出来，减少 API 同进程 worker 的生产风险，并完善运维命令。

## Phase 6D：独立 worker / cron 扫描命令

本轮把台股监控扫描从“API 同进程可选 worker”扩展为可独立部署的 worker/cron 命令，降低生产部署中 API 进程承担后台任务的风险。

实现内容：

- 新增脚本：`backend/scripts/run_tw_stock_monitor_scan.py`。
- 脚本复用现有 `run_tw_stock_monitor_scan_all()`，不会新建交易路径。
- 支持 `--once`：执行一次扫描后退出，适合 cron；不传 `--loop` 时也按一次执行。
- 支持 `--loop --interval-sec 900`：常驻循环扫描，适合 systemd/supervisor。
- 支持 `--force`、`--trigger-source`、`--no-log`、`--max-runs`。
- 默认设置安全环境变量：`AGENT_LIVE_TRADING_ENABLED=false`、`ENABLE_PENDING_ORDER_WORKER=false`、`ENABLE_PORTFOLIO_MONITOR=false`、`ENABLE_TW_STOCK_MONITOR_WORKER=false`。
- 输出一行 JSON 摘要，包含扫描配置数、扫描 symbol 数、提醒数、耗时和 `orders_enabled=false`。
- 更新 `docs/TW_STOCK_MONITOR_DEPLOYMENT_CN.md`，新增独立 cron 和常驻 worker 示例命令。

测试结果：

- 单元/回归测试：`52 passed in 0.91s`。新增覆盖 interval clamp、`--once` 输出摘要、`--loop --max-runs` 循环退出。
- 本地 PostgreSQL smoke：执行 `run_tw_stock_monitor_scan.py --once --force --trigger-source phase6d-smoke --no-log` 成功。
- smoke 输出：`count=1`、`total_scanned_count=3`、`total_alert_count=0`、`orders_enabled=false`、`status=success`。
- 因 smoke 使用 `--no-log`，不会写入 `qd_tw_stock_monitor_scan_logs`；本次会更新 default 监控状态和趋势历史，这是真实扫描的预期行为。

安全边界：

- 没有提交 paper order。
- 没有连接 IBKR 或任何券商。
- 没有启用自动交易。
- 独立脚本只调用研究扫描、提醒落库、趋势历史落库和扫描日志。
- 推荐生产上 API 保持 `ENABLE_TW_STOCK_MONITOR_WORKER=false`，只启用一个 cron 或独立 worker，避免重复扫描。

当前限制：

- 脚本直接复用 Flask route 层的 scan-all 函数，后续可以把扫描核心再下沉到 service 层，让 API 和脚本都依赖 service。
- 当前没有提供 systemd unit 文件模板，只在部署文档给出命令示例。
- 外部 Telegram/Email/Webhook 推送尚未实现。

下一步建议：Phase 6 可以进入收尾验收，或者继续 Phase 6E 做外部通知通道（Webhook/Telegram/Email）中的一个。

## Phase 6 收尾验收

本轮按用户要求对 Phase 6 进行收尾验收。

验收结论：Phase 6 可验收完成，主线没有偏离。当前能力仍是“台股趋势研究 + 自动监控提醒 + 人工复盘 + 人工决策”，没有自动买卖，没有连接 IBKR 或任何券商，没有提交 paper/live order。

完成范围：

- Phase 6A：站内通知桥接，台股 alert 同步进入 `qd_strategy_notifications`。
- Phase 6B：趋势历史表和只读 history API。
- Phase 6C：监控页面趋势分数曲线、提醒过滤、人工状态按钮。
- Phase 6D：独立 `run_tw_stock_monitor_scan.py`，支持 cron 单次扫描和 loop worker。

收尾验证：

- Phase 6 回归测试：`52 passed in 1.01s`。
- `run_tw_stock_monitor_scan.py --help` 成功，CLI 参数完整。
- 页面模板关键控件存在：`trendChart=True`、`history_api=True`、`alert_filter=True`、`manual_watch=True`、`read_only_copy=True`。
- 5000 端口无遗留监听。

新增验收文档：

- `docs/TW_STOCK_PHASE6_ACCEPTANCE_CN.md`。

安全边界：

- 没有提交 paper order。
- 没有连接 IBKR。
- 没有调用 broker client。
- 没有调用 quick-trade。
- Phase 6 新能力只用于研究提醒、趋势历史、页面复盘和运维调度。

剩余限制：

- 当前仍是日线趋势研究，不是盘中实时行情。
- 外部通知通道尚未实现。
- 页面仍是 Flask 托管轻量页面，不是正式 Vue 前端。
- TPEx 官方对账仍不稳定，扩大上柜股票前需要继续验证或由用户本地比对。

下一步建议：进入 Phase 7，优先级可选：正式前端/e2e、Webhook/Telegram/Email 外部通知、扩大股票/ETF universe、扫描核心 service 化。

