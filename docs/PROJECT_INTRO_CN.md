# Taiwan Stock Quant Platform 项目介绍与原理

## 项目定位

Taiwan Stock Quant Platform 是一个独立打包的台股研究平台，目标是把原本分散在 QuantDinger、QuantDinger-Vue、qlib、Scrapling/Yahoo/FinMind 数据脚本中的能力整合成一个可持续运行的单仓库项目。

项目核心不是自动交易系统，而是研究、分析、可视化和人工复盘系统。它会生成台股量化排序、趋势分析、交叉分析和 Agent 问答结果，但不会连接券商下单，不会生成可执行订单，也不会写入真实仓位。

## 闭环链路

完整生产闭环如下：

```text
FinMind/TWSE raw 数据补数
Yahoo/Scrapling 复权行情补数
-> qlib normalized CSV
-> qlib bin provider
-> Alpha158 + LightGBM frozen model
-> Option C 150 股票每日研究排序
-> accepted latest 信号产物
-> QuantDinger backend 读取信号、趋势、交叉分析、Agent context
-> QuantDinger-Vue 前端展示
-> 人工观察与复盘
```

这个闭环分为两条数据口径：

- qlib 主链路：使用 Yahoo/Scrapling 复权价格，服务于模型预测和横截面排序。
- QuantDinger raw 链路：使用 FinMind/TWSE 原始数据，服务于 K 线、趋势、交叉分析和展示。

两条链路不会静默混用价格口径。Yahoo 当日数据不可用时，系统会进入等待重试状态，而不是把 FinMind raw 价格直接混入 qlib provider。

## 模块组成

### backend

`backend/` 来自 QuantDinger 后端，主要承担：

- 台股 raw 数据 API
- qlib Option C accepted latest 读取
- qlib ops/dry-run/publish 门禁
- 台股趋势分析
- qlib 与 QuantDinger raw 数据交叉分析
- Agent context 和问答接口
- 研究安全边界和只读约束

### frontend

`frontend/` 来自 QuantDinger-Vue，主要承担：

- 台股趋势监控页面
- qlib Top30/Top50 研究排序展示
- accepted latest 健康状态展示
- 交叉分析展示
- Agent 问答面板
- 观察草稿、只读回测入口和人工复盘入口

### qlib_pipeline

`qlib_pipeline/` 保存 qlib 台股研究脚本和配置：

- Yahoo/Scrapling Option C refresh
- qlib provider publish
- daily signal generation
- Alpha158/LightGBM 配置
- 台股 handler/strategy 扩展
- dump/export 工具

大型 qlib 数据和模型产物不提交到 Git，而是放在 ignored 的 `qlib_pipeline/data_tw/` 和 `qlib_pipeline/mlruns/`。

### crawler

`crawler/` 保存 Yahoo/Scrapling 和 FinMind supplement 相关脚本，用于行情采集、补数和数据契约说明。

### scripts

`scripts/` 保存独立项目级别的入口脚本：

- `bootstrap_full_production_assets.py`：从本机原生产资产复制 qlib 数据和模型。
- `verify_full_production_loop.py`：验证最大生产闭环。
- `verify_self_contained_closed_loop.py`：生成轻量 demo 闭环。
- `run_daily_tw_stock_auto_update.py`：每日无人值守自动更新入口。

## Option C 150 股票研究排序

当前 qlib 主线使用 Option C 150 股票 universe。每日更新后，模型会对这 150 支股票生成横截面研究排序。

重要语义：

- `qlib_score` 是横截面排序分数。
- 分数不是收益率、胜率、涨幅或买入概率。
- Top30/Top50 是研究观察候选，不是交易指令。
- `research_signal_not_order=true` 是强制边界。

## accepted latest 机制

前端、Agent 和交叉分析不直接读取临时模型输出，而是读取 `accepted latest`。

更新 accepted latest 需要通过门禁：

1. provider 数据必须包含目标 `asof`。
2. dry-run 必须通过。
3. normal signal 产物必须是 accepted。
4. Top30/Top50 行数、finite score、研究标记必须通过校验。
5. latest 更新前会备份，失败不会替换 latest。

这样可以避免半成品、等待态或失败产物被前端误展示。

## 每日自动更新原理

每日自动更新入口是：

```bash
python scripts/run_daily_tw_stock_auto_update.py
```

它会：

1. 自动选择 Asia/Taipei 当天日期。
2. 如果存在 `pending_asof.json`，优先继续处理 pending 日期。
3. 用 FinMind 更新 QuantDinger raw 数据库。
4. 用 Yahoo/Scrapling 拉取 qlib 复权行情。
5. 发布 qlib provider。
6. 通过 accepted latest scheduler 更新 latest。
7. 成功后清除 pending。

如果收盘后 Yahoo 数据尚未开放，脚本会写入：

```text
data_tw/ops/daily_auto_update/pending_asof.json
```

后续定时任务即使跨午夜，也会继续优先拉这个日期，直到成功或人工处理。

## Agent 原理

Agent 模块不是自由访问全系统的交易助手。它的上下文来自受控后端：

- accepted latest qlib 排序
- 交叉分析结果
- raw 趋势指标
- freshness 和数据口径信息
- 研究安全边界

支持的问题包括：

- 今天 Top30 是哪些？
- 哪些股票模型和趋势都支持？
- 哪些需要人工复盘？
- 某只股票的 qlib rank、score、trend 指标是多少？
- 当前数据新鲜度如何？

不支持的问题包括：

- 下单
- 仓位建议
- 自动交易
- 收益承诺
- 绕过 qlib ops 门禁

## 安全边界

项目默认研究模式：

- `orders_enabled=false`
- `connects_to_broker=false`
- `research_signal_not_order=true`
- 不自动提交订单
- 不写真实仓位
- 不把模型输出描述成买卖建议

如果未来要接入真实交易，必须作为独立项目或独立受控模块处理，不能复用当前研究闭环默认安全假设。

## 数据与模型资产策略

仓库提交代码、配置、脚本、文档和测试，不提交大型生成资产。

常见 ignored 资产：

- `data_tw/`
- `qlib_pipeline/data_tw/`
- `qlib_pipeline/mlruns/`
- `frontend/dist/`

原因是 qlib provider、normalized CSV 和模型记录通常很大，更适合作为 GitHub Release artifact、对象存储资产，或通过脚本重新生成。

## 项目当前能力边界

已经具备：

- 台股 150 股票 2015 至今生产数据资产的接入路径
- qlib Option C daily signal
- accepted latest 发布门禁
- FinMind/QuantDinger raw 数据补数
- Yahoo/Scrapling qlib 数据补数
- 后端读取、交叉分析、Agent
- 前端展示
- 每日无人值守重试机制

仍需部署者提供：

- PostgreSQL
- Python/Node 运行环境
- 可选 FinMind token
- qlib 大型数据和模型资产，或重新生成这些资产
- 系统 cron/systemd 定时任务安装
