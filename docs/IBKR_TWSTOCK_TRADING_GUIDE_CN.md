# IBKR 台股 Paper / Live 操作手册

本文是 QuantDinger 台股 `TWStock` 进入 IBKR paper / live 前的操作手册。它不是实盘授权；默认路径仍然是 paper-only。任何 live promotion 都必须由人工审批，并且必须先通过 preflight、paper 订单、持仓汇总和回滚验证。

## 1. 当前状态

- 台股市场类型：`TWStock`
- 支持范围：TWSE 上市股票 / ETF；TPEx 上柜合约可映射，但 TPEx 官方数据对账尚未稳定完成。
- IBKR 合约映射：
  - `2330`、`2330.TW`、`TWSE:2330` -> `STK 2330 TWSE TWD`
  - `0050` -> `STK 0050 TWSE TWD`
  - `TPEX:6488`、`6488.TPEX` -> `STK 6488 TPEX TWD`
- 策略限制：IBKR + `TWStock` 只允许 `spot`、`long`。
- Agent 默认：`paper_only=true`。
- 服务器级实盘开关默认：`AGENT_LIVE_TRADING_ENABLED=false`。

## 2. 禁止条件

任一条件成立时，不得进入 live：

- `preflight_tw_stock_ibkr_live.py --require-live` 返回 `status=fail`。
- `AGENT_LIVE_TRADING_ENABLED` 未经人工审批被设为 `true`。
- Agent token 未经人工审批被设为 `paper_only=false`。
- 使用 `clientId=1` 作为策略 / order worker 的 IBKR client ID。
- TWS / IB Gateway 没有登录或 API socket 未启用。
- 未完成 paper 账户下的订单查回、持仓汇总、rejected 限价单验证。
- TPEx 标的未经过人工对账就进入 live。
- 策略未设置单笔、单日、总持仓、现金和整股约束。

## 3. 环境变量

Paper 验证建议：

```bash
AGENT_LIVE_TRADING_ENABLED=false
ALLOW_LOCAL_DESKTOP_BROKERS=true
IBKR_ORDER_CLIENT_ID=7
```

Live promotion 只有在人工审批后才允许：

```bash
AGENT_LIVE_TRADING_ENABLED=true
ALLOW_LOCAL_DESKTOP_BROKERS=true
IBKR_ORDER_CLIENT_ID=7
```

如果使用环境变量描述 IBKR host / port，可设置：

```bash
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
```

也可以通过项目凭据配置写入 `ibkr_host`、`ibkr_port`、`ibkr_client_id`、`ibkr_account`。策略 / order worker 不应使用 `clientId=1`；建议保留 `clientId=1` 给手工 UI / 临时调试，worker 使用 `7`。

## 4. TWS / IB Gateway 设置

1. 登录 IBKR paper account。
2. 打开 TWS 或 IB Gateway。
3. 在 API 设置中启用 Socket / ActiveX API。
4. 只允许可信本机或私有网络访问。
5. 确认端口：
   - TWS paper 常用 `7497`
   - TWS live 常用 `7496`
   - IB Gateway paper / live 端口以本机设置为准
6. 确认 API 连接不与其他客户端 `clientId` 冲突。

## 5. Preflight

Paper preflight：

```bash
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger \
AGENT_LIVE_TRADING_ENABLED=false \
ALLOW_LOCAL_DESKTOP_BROKERS=true \
IBKR_ORDER_CLIENT_ID=7 \
python \
  backend/scripts/preflight_tw_stock_ibkr_live.py \
  --symbol 2330,0050,TPEX:6488 \
  --agent-token <paper-agent-token> \
  --output-json /tmp/tw_ibkr_preflight_paper.json \
  --output-md /tmp/tw_ibkr_preflight_paper.md
```

预期：

- `status=pass`
- `connects_to_ibkr=false`
- `submits_orders=false`
- `error_count=0`

Live preflight：

```bash
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger \
AGENT_LIVE_TRADING_ENABLED=true \
ALLOW_LOCAL_DESKTOP_BROKERS=true \
IBKR_ORDER_CLIENT_ID=7 \
IBKR_HOST=127.0.0.1 \
IBKR_PORT=7497 \
python \
  backend/scripts/preflight_tw_stock_ibkr_live.py \
  --symbol 2330,0050 \
  --agent-token <live-approved-agent-token> \
  --require-live \
  --require-ibkr-env \
  --output-json /tmp/tw_ibkr_preflight_live.json \
  --output-md /tmp/tw_ibkr_preflight_live.md
```

预期：

- 所有 error check 通过。
- `paper_only=false` 必须是人工审批后签发或修改的 token。
- 即使 preflight 通过，也不代表已经可以无人值守实盘。

## 6. Paper 账户验证流程

1. 使用最新真实日线收盘价生成计划。
2. 先执行 dry-run，检查整股、限价、单笔金额、总买入金额、warning 和 blocked。
3. 使用 paper-only token 执行 submit。
4. 运行 post-submit bundle：
   - 订单查回 `matched_count` 必须等于预期订单数。
   - `missing_count=0`。
   - filled order 必须进入 paper summary。
   - rejected order 必须不进入持仓。
5. 直接查询 DB 核对：
   - 买入：`fill_price <= limit_price`
   - 卖出：`fill_price >= limit_price`
   - 无超卖。
6. 保存 JSON / Markdown 报告。

已经验证过的样例包括：

- 多股票 / ETF paper buy：`2330`、`0050`、`00878`
- 多标的后续调仓：卖出 `0050`、加仓 `2330`
- 不可成交买入限价：记录为 `rejected`，不进入持仓

## 7. Live Promotion 审批清单

进入 live 前，人工审批必须逐项确认：

- 本策略已经完成至少一次真实数据 paper 闭环。
- 最近一次 paper execution report 为 `pass`，或 warning 已被人工解释并接受。
- live preflight 为 `pass`。
- token 的 `markets` 只允许 `TWStock` 或更窄。
- token 的 `instruments` 建议只允许试单标的。
- `paper_only=false` 只给短期、低权限、低频率 token。
- `AGENT_LIVE_TRADING_ENABLED=true` 的变更有记录。
- TWS / Gateway 连接的是 paper 账户还是 live 账户已经人工确认。
- 订单金额、持仓上限和单日总金额已经写入策略或外层风控。
- 回滚步骤已经演练。

## 8. 最小 Live 试单

如果人工决定进入 live，第一笔试单必须满足：

- 只选 TWSE 高流动性标的，不选 TPEx。
- 只做买入或卖出一张以内，优先 1000 股整股。
- 使用限价单。
- 不使用 market order。
- 不在开盘瞬间、收盘前极短时间或重大公告期间执行。
- 下单后立即查回 IBKR order status、成交、持仓和现金变化。
- 记录报告并暂停自动化，人工复核后才允许下一笔。

## 9. 回滚与禁用

发现异常时按顺序执行：

1. 立即设置：

```bash
AGENT_LIVE_TRADING_ENABLED=false
```

2. 撤销或禁用 live token。
3. 停止策略 / worker。
4. 在 TWS / Gateway 手工检查 open orders。
5. 如有未成交单，人工取消。
6. 导出 IBKR 成交、订单、持仓和 QuantDinger DB 记录。
7. 写事故报告，不在原因明确前恢复 live。

## 10. 当前未完成项

- 还没有在本环境连接真实 IBKR TWS / Gateway。
- 还没有通过 IBKR paper account 做真实 broker paper order。
- TPEx 官方 OpenAPI 在本环境仍不稳定；TPEx 标的 live 前需要人工对账。
- 当前 Agent quick-trade 仍是本地 paper order 记录，不是 IBKR broker order。

## 11. 常用命令

只读 paper preflight：

```bash
python \
  backend/scripts/preflight_tw_stock_ibkr_live.py \
  --symbol 2330,0050,TPEX:6488 \
  --agent-token <paper-agent-token>
```

只读 live fail-case preflight：

```bash
python \
  backend/scripts/preflight_tw_stock_ibkr_live.py \
  --symbol 2330,0050,TPEX:6488 \
  --agent-token <paper-agent-token> \
  --require-live \
  --require-ibkr-env
```

Phase 4 paper 测试：

```bash
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger \
python -m pytest \
  backend/tests/test_preflight_tw_stock_ibkr_live.py \
  backend/tests/test_ibkr_tw_stock_symbols.py \
  backend/tests/test_broker_market_policy.py \
  backend/tests/test_agent_v1_twstock_quick_trade.py \
  backend/tests/test_build_tw_stock_paper_execution_report.py \
  backend/tests/test_build_tw_stock_paper_report_bundle.py -q
```
