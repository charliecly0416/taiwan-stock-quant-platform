# 台股日更全流程数据链路说明：从当天数据到前端策略工作台

生成日期：2026-06-20

> 真实样本补充：如果需要看 `2026-06-17 -> 2026-06-18` 链路中 `TW2330` 和 `TW3481` 的逐模块输入、真实字段值、模型分数、LTR 特征和前端候选结果，请优先阅读 `docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_REAL_SAMPLE_20260618_CN.md`。本文偏概念说明，新文档偏真实数据审计。

## 0. 这份文档讲什么

本文用“数据一路怎么流动”的视角，解释台股系统每天更新时到底做了什么。

你可以把整条链路理解成一条厨房流水线：

```text
买菜
-> 清洗切菜
-> 做成半成品
-> 主厨评分
-> 按规则出菜单
-> 模拟试吃
-> 摆盘给用户看
-> Agent 用同一份菜单解释
```

对应到系统是：

```text
抓取数据
-> 标准化价格与基础数据
-> 生成特征
-> 模型打分与排名
-> 策略生成只读意图
-> 历史模拟 / 模拟账户检查
-> 只读策略快照
-> DailyAgentPromptArtifact
-> 后端 API
-> 前端策略工作台
```

核心原则：

```text
每一环只吃上一环的标准产物，不偷看未来，不直接下单。
```

## 1. 一张总图

```text
当天或目标 asof
  |
  v
股票池 universe
  |
  v
原始行情与基础数据
  |
  v
标准化价格 PriceStore
  |
  v
特征 FeatureArtifact
  |
  v
模型 Model / ModelAdapter
  |
  v
ModelSignalArtifact
  |
  v
StrategyRule + PortfolioState
  |
  v
OrderIntentArtifact
  |
  v
ReplayResultArtifact + PaperPortfolioContext
  |
  v
ReadonlyStrategySnapshot
  |
  v
DailyAgentPromptArtifact
  |
  v
API
  |
  v
/tw-stock-monitor 前端策略工作台
```

## 2. 日期：系统每天先决定“今天要处理哪一天”

日更第一步不是抓数据，而是决定目标日期。

目标日期叫：

```text
asof
```

你可以理解为：

```text
这次日更要让系统更新到哪一个交易日。
```

来源优先级：

1. 人工传入 `--asof YYYY-MM-DD`。
2. 如果之前有没完成的日期，就继续处理 `pending_asof.json`。
3. 否则默认使用台湾时区当天。

为什么要有 `pending_asof`？

因为数据源不一定准时更新。比如今天收盘后，FinMind 可能已经有数据，但 Yahoo/Scrapling 还没齐。系统会记住“今天还没成功”，下一轮继续重试，而不是跳过。

关键文件：

```text
data_tw/ops/daily_auto_update/pending_asof.json
data_tw/ops/daily_auto_update/{job_id}/job.json
```

## 3. 股票池：系统先决定“今天看哪些股票”

股票池叫：

```text
universe
```

你可以理解为：

```text
今天模型和策略会考虑的股票名单。
```

当前日更会优先读取 accepted prediction universe：

```text
qlib_pipeline/data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt
```

然后落到本次 job：

```text
data_tw/ops/daily_auto_update/{job_id}/finmind_symbols.txt
```

如果完整股票池缺失，系统会 fallback 到：

```text
2330
0050
```

但这只是降级路径，不能当成完整产品日更成功。

小白解释：

- `2330` 是台积电。
- `0050` 是台湾 50 ETF。
- fallback 只像“先用两样菜测试厨房还会不会运转”，不是完整菜单。

## 4. 原始数据：系统会抓哪些“当天数据”

### 4.1 价格数据

最重要的是股票每天的行情，常见字段包括：

| 字段 | 小白解释 | 用途 |
| --- | --- | --- |
| `open` | 开盘价，今天一开始交易的价格 | 回放或模拟账户可能用下一交易日开盘价做执行参考 |
| `high` | 最高价 | 计算波动范围、趋势、技术特征 |
| `low` | 最低价 | 计算波动范围、风险特征 |
| `close` | 收盘价 | 最常用的日线价格，很多收益、趋势、特征都基于它 |
| `volume` | 成交量，今天成交多少股 | 判断活跃度、流动性 |
| `vwap` | 成交均价，按成交量加权的平均价格 | 更接近市场实际平均成交成本 |

这些字段通常称为：

```text
OHLCV
```

意思是：

```text
Open / High / Low / Close / Volume
```

### 4.2 复权价格

股票会配息、分割或发生价格调整。如果只看原始价格，历史走势图会突然断裂。

所以系统还会使用：

```text
adjusted price
```

小白解释：

```text
复权价格就是把历史价格调成更适合连续比较的价格。
```

用途：

- 训练模型时避免价格断点误导模型。
- 计算历史收益、趋势、波动更稳定。
- replay 时让长期比较更合理。

当前 registry 中的价格源：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt
```

### 4.3 交易日历

交易日历记录哪天开市、哪天休市。

为什么重要？

如果今天是周五，下一交易日可能是下周一；如果遇到节假日，下一交易日还要往后找。

策略和回放必须知道：

```text
信号日 signal_date
执行日 execution_date
```

基本规则：

```text
execution_date 必须晚于 signal_date
```

不能用今天收盘后才知道的信息，假装今天盘中就能交易。

## 5. 标准化：把不同来源的数据整理成统一格式

抓来的原始数据通常不干净，会有这些问题：

- 有些股票当天缺数据。
- 不同数据源字段名不一样。
- 股票代码格式不统一。
- 日期格式不统一。
- 有的价格需要复权。
- 有的股票停牌或成交量异常。

标准化的目的：

```text
让后面的特征、模型、策略看到同一种格式的数据。
```

输出可以理解为：

```text
PriceStore
```

小白解释：

```text
PriceStore 就是整理好的价格仓库。
```

它应该回答：

- 某只股票某天开盘价是多少？
- 收盘价是多少？
- 成交量是多少？
- 下一交易日开盘价是否存在？
- 数据是否缺失？

如果 PriceStore 不可靠，后面的模型分数和策略回放都会不可靠。

## 6. 数据齐备检查：不是有数据就能继续

进入模型或策略前，系统要检查数据是否够用。

关键检查：

| 检查项 | 小白解释 |
| --- | --- |
| price coverage | 股票池里的股票是否都有足够价格数据 |
| FinMind archive | 原始日线数据是否更新到目标日期 |
| Yahoo adjusted price | 复权价格是否齐备 |
| trading calendar | 是否知道下一交易日 |
| execution price | 如果策略要模拟下一日开盘价，下一日开盘价是否可得 |
| feature coverage | 模型需要的特征是否算得出来 |
| PIT / available_at | 特征在当时是否真的可见，不能偷看未来 |

如果某个模型需要的数据缺失，正确做法是：

```text
阻断该模型或保留上一版结果。
```

错误做法是：

```text
偷偷换另一个模型结果，或者用缺失数据硬算。
```

## 7. 特征：把价格变成模型能理解的“观察指标”

模型不能只看一张原始价格表。它通常需要一些加工后的指标，叫：

```text
features
```

小白解释：

```text
特征就是把价格数据加工成模型能读懂的线索。
```

常见特征类别：

| 特征类别 | 小白解释 | 可能代表什么 |
| --- | --- | --- |
| 近期涨跌 | 最近 5 天、20 天、60 天涨了还是跌了 | 动量，股票是否有趋势 |
| 波动率 | 价格上下波动大不大 | 风险或不稳定程度 |
| 成交量变化 | 最近成交量是否放大 | 市场关注度变化 |
| 流动性 | 成交是否足够活跃 | 策略是否容易买卖 |
| 价量关系 | 价格上涨时成交量是否配合 | 趋势质量 |
| 横截面排名 | 今天在所有股票中排第几 | 相对强弱 |
| 正交特征 | 尽量去掉和旧模型重复的信息 | 给 LTR 模型补充不同角度 |

当前项目里，有两类重要特征来源：

### 7.1 Qlib / Alpha 特征

Qlib 是量化研究框架。它会基于历史价格生成一批标准特征。

你可以理解为：

```text
基础模型使用的一套标准技术指标。
```

### 7.2 Orthogonal LTR 特征

当前产品 registry 中有：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv
```

这类特征用于 LTR rerank。

小白解释：

```text
LTR 像第二位评审，它不重新决定全市场股票池，只在 qlib 已经挑出的 top50 里重新排序。
```

`orthogonal` 可以理解为：

```text
尽量提供和 qlib 原始分数不同的新角度，避免两个模型看的是完全一样的线索。
```

### 7.3 特征最重要的安全规则

特征不能包含未来信息。

禁止进入模型输入的字段类型：

```text
future_return_*
forward_return_*
label_*
realized_pnl
execution_price
execution_date
target_position
```

小白解释：

```text
不能把考试答案塞进考题里。
```

## 8. 模型：把特征变成“股票排序分数”

模型的工作不是下单，而是打分。

当前产品默认模型信息来自：

```text
configs/tw_product_artifact_registry.yaml
```

当前核心模型：

| 模型 | 小白解释 |
| --- | --- |
| `e4_frozen_qlib_2018_2022` | 底座 qlib 模型，负责给全市场股票做基础排名 |
| `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025` | LTR rerank 模型，在 qlib top50 里重新排序 |
| `e4_frozen_qlib_2023_2025_ltr` | 前端展示用名称，表示 qlib + LTR 排序结果 |

### 8.1 Qlib 模型输出什么

Qlib 模型会输出类似：

| 数据 | 小白解释 |
| --- | --- |
| `qlib_score` / `raw_score` | 模型原始分数，越高通常代表模型越喜欢 |
| `qlib_rank` / `full_qlib_rank` | 全市场排名，1 表示最靠前 |
| top150 / top50 | 从全市场里筛出来的高排名股票 |

注意：

```text
qlib_score 不是收益率，不是胜率，不是上涨概率。
```

它只是：

```text
模型的相对排序分数。
```

### 8.2 LTR 模型输出什么

LTR 的全称可以理解为：

```text
Learning to Rank，学习如何排序。
```

当前 LTR 的边界：

```text
只在 qlib top50 内重排。
```

也就是说：

- qlib 先挑出 50 支候选股票。
- LTR 不负责把 top50 外的股票拉进来。
- LTR 只决定这 50 支里面谁更靠前。

LTR 可能输出：

| 数据 | 小白解释 |
| --- | --- |
| `buy_score` | top50 内买入观察优先级分数 |
| `score_rank` | 根据 buy_score 排出来的名次 |
| `raw_score` | LTR 原始分数 |

## 9. ModelSignalArtifact：模型输出必须变成标准信号表

模型不能把自己的私有结果直接交给策略。

必须先经过 adapter，转成：

```text
ModelSignalArtifact
```

小白解释：

```text
ModelSignalArtifact 是模型给策略的标准成绩单。
```

核心字段：

| 字段 | 小白解释 |
| --- | --- |
| `date` | 信号日期 |
| `instrument` | 股票代码，如 `TW2330` |
| `model_name` | 哪个模型产出的 |
| `model_family` | 模型类型，如 qlib / ltr |
| `candidate_rank` | qlib 候选排名，用来判断是否在 top50 |
| `buy_score` | 买入观察排序分数 |
| `raw_score` | 模型原始分数，保留溯源 |
| `score_rank` | 按 buy_score 排出的名次 |
| `full_qlib_rank` | 全市场 qlib 排名 |
| `signal_asof` | 这份信号对应哪天 |
| `available_at` | 这份信号什么时候可见 |
| `source_artifact` | 来源产物路径 |
| `source_model_artifact` | 来源模型产物 |
| `source_feature_artifact` | 来源特征产物 |

最重要的三个字段：

### `candidate_rank`

小白解释：

```text
这只股票是否进入 qlib top50 候选池。
```

用途：

- 判断是否在候选池内。
- 判断持仓是否跌出 top50。

### `buy_score`

小白解释：

```text
如果它已经在候选池里，模型更想优先观察谁。
```

用途：

- 决定候选调入的优先顺序。

### `full_qlib_rank`

小白解释：

```text
它在全市场 qlib 排名里大概排第几。
```

用途：

- 如果持仓跌出 top50，用它判断哪只最差、该优先复核调出。

## 10. 策略：把模型成绩单变成“只读买卖意图”

策略不是模型。模型负责打分，策略负责按规则处理分数。

当前默认策略：

```text
top50_exit_one_worst_sell
```

小白解释：

```text
如果持仓里有股票跌出 qlib top50，就优先复核卖出其中 qlib 全市场排名最差的一只；
然后从 qlib top50 中按 buy_score 找最靠前、当前没持有的候选，作为模拟调入。
```

策略输入：

```text
ModelSignalArtifact
PortfolioState
StrategyRuleConfig
```

### 10.1 PortfolioState 是什么

`PortfolioState` 可以理解为：

```text
模拟账户或回放当前持有什么。
```

常见字段：

| 字段 | 小白解释 |
| --- | --- |
| `asof_date` | 持仓状态对应哪一天 |
| `instrument` | 股票代码 |
| `quantity` | 持有数量 |
| `cost_basis` | 成本 |
| `current_holding_flag` | 是否当前持有 |

### 10.2 StrategyRuleConfig 是什么

`StrategyRuleConfig` 是策略规则参数。

常见字段：

| 字段 | 小白解释 |
| --- | --- |
| `target_holding_count` | 希望持有多少只股票 |
| `candidate_k` | 候选池看前多少名 |
| `max_buy_count` | 一天最多产生几个买入意图 |
| `max_sell_count` | 一天最多产生几个卖出意图 |
| `sell_boundary` | 什么情况下考虑调出 |
| `buy_order` | 按什么排序挑调入 |
| `tie_breaker` | 分数相同时怎么稳定排序 |

## 11. OrderIntentArtifact：策略输出的是“意图”，不是订单

策略输出必须是：

```text
OrderIntentArtifact
```

小白解释：

```text
它像一张模拟用的建议清单：想买、想卖、想保留、想跳过。
它不是券商订单。
```

核心字段：

| 字段 | 小白解释 |
| --- | --- |
| `signal_date` | 策略读取信号的日期 |
| `instrument` | 股票代码 |
| `intent_action` | `buy` / `sell` / `hold` / `skip` |
| `intent_reason` | 为什么产生这个意图 |
| `strategy_rule` | 哪条策略规则产生的 |
| `candidate_rank` | 当时 qlib 候选排名 |
| `buy_rank` | 当时买入排序 |
| `full_qlib_rank` | 当时全市场 qlib 排名 |
| `max_buy_count` | 当日最多买入意图数 |
| `max_sell_count` | 当日最多卖出意图数 |
| `model_name` | 来源模型 |
| `signal_artifact` | 来源信号表 |

禁止出现在 `OrderIntentArtifact` 里的字段：

```text
execution_price
execution_date
cash
equity
daily_return
realized_pnl
broker_order_id
```

原因：

```text
这些属于成交、账户和回放结果，不属于策略意图。
```

## 12. Replay：用历史价格模拟“如果照这个意图做会怎样”

Replay 可以理解为：

```text
历史模拟。
```

它只消费：

```text
OrderIntentArtifact
PriceStore
ExecutionConfig
InitialPortfolioState
```

Replay 会决定：

- 下一交易日是否有价格。
- 用什么执行价，例如 next_open。
- 如果缺价格，是跳过还是记录 coverage warning。
- 模拟买卖后现金、持仓、净值怎么变化。
- 历史窗口里的净收益、回撤、交易次数、费用税费。

Replay 输出：

```text
ReplayResultArtifact
```

常见前端展示字段：

| 字段 | 小白解释 |
| --- | --- |
| `fee_tax_adjusted_net_return` | 扣掉交易成本后的历史模拟净收益 |
| `max_drawdown` | 最大回撤，历史上从高点跌到低点最多跌多少 |
| `action_count` | 模拟交易动作次数 |
| `fee_tax_total` | 模拟费用和税费 |
| `coverage_status` | 数据覆盖是否足够 |

重要提醒：

```text
Replay 是历史模拟，不是未来收益承诺。
```

## 13. 模拟账户：今天是否能把策略意图应用到模拟账户

模拟账户不同于 replay。

Replay 问的是：

```text
过去一段时间，如果按规则做，历史表现如何？
```

模拟账户问的是：

```text
今天这份策略意图，能不能应用到当前模拟账户状态？
```

模拟账户会看：

- 现金。
- 当前持仓。
- 当前账户 epoch。
- 最新策略意图。
- 执行价格是否可得。
- 是否等待目标交易日开盘价。

前端常见状态：

```text
等待目标交易日开盘价，暂不能应用到模拟账户。
```

小白解释：

```text
策略今天已经有想法，但还不知道明天开盘价，所以不能把模拟账户账本往前记。
```

模拟账户仍然只影响模拟账本：

```text
不连接券商，不提交真实订单。
```

## 14. ReadonlyStrategySnapshot：把今天策略状态打包给前端

前端不应该到处读模型文件、策略文件和回放文件。

系统会把今天需要展示的关键信息打包成：

```text
ReadonlyStrategySnapshot
```

小白解释：

```text
这是一份只读日报摘要，告诉前端今天策略是什么、候选是谁、调出复核是谁、数据是否安全。
```

常见内容：

| 内容 | 小白解释 |
| --- | --- |
| `asof` / `signal_asof` | 信号日期 |
| `model_id` | 使用哪个模型 |
| `strategy_rule` | 使用哪个策略 |
| `ranking_source` | 排名来源 |
| `top_candidates` | 候选调入 |
| `exit_candidates` | 调出复核 |
| `readonly_only` | 只读 |
| `production_trade_enabled=false` | 没有实盘交易 |
| `checksum` | 文件完整性校验 |
| `manifest` | 产物说明书 |

发布 latest 的默认 gate 是关闭或 dry-run。

允许更新的只读 latest 与 provider/qlib accepted latest 不是一回事。

## 15. DailyAgentPromptArtifact：把今天上下文压缩给 Agent

Agent 不应该自己实时乱查工具、乱拼数据。

当前简化路线是：

```text
DailyAgentPromptArtifact
-> TWStockAgentSimpleChatService
-> POST /api/tw-stock/agent/simple-chat
```

小白解释：

```text
DailyAgentPromptArtifact 是给 Agent 的每日讲义。
Agent 只能根据这份讲义和你的问题回答。
```

它会包含：

- 今天信号日期。
- 目标交易日。
- 使用的模型和策略。
- 候选调入。
- 调出复核。
- 历史模拟摘要。
- 模拟账户为什么能或不能应用。
- 数据新鲜度。
- 安全声明。
- 引用来源和 checksum。

Agent 不能：

- 自己下单。
- 自己切换 latest。
- 自己刷新 provider。
- 自己读取 OpenAI key。
- 给出目标仓位或买卖指令。

## 16. API：前端通过哪些接口拿数据

前端主路径通过后端 API 获取数据，不直接读本地 artifact。

关键 API：

| API | 给前端什么 |
| --- | --- |
| `GET /api/tw-stock/current-strategy-context` | 今日策略总览、模型、策略、信号日期、目标交易日 |
| `GET /api/tw-stock/readonly-strategy-snapshot` | 候选名单、调出复核、只读策略快照 |
| `GET /api/tw-stock/readonly-replay-window-index` | 可选历史模拟窗口列表 |
| `GET /api/tw-stock/readonly-replay-window` | 某个历史模拟窗口的结果 |
| `GET /api/tw-stock/paper-portfolio/latest-decision` | 模拟账户最新策略意图 |
| `GET /api/tw-stock/paper-portfolio/state` | 模拟账户现金和持仓 |
| `POST /api/tw-stock/agent/simple-chat` | 只读策略解释助手问答 |

唯一允许的 Agent POST：

```text
POST /api/tw-stock/agent/simple-chat
```

它只用于解释，不用于交易。

## 17. 前端：用户最终看到哪些数据

前端 `/tw-stock-monitor` 当前主路径：

```text
今日策略总览
-> 候选名单
-> 历史模拟
-> 模拟账户状态
-> 策略解释助手
```

### 17.1 今日策略总览

展示：

- 信号日期。
- 目标交易日。
- 当前模型。
- 当前策略。
- 候选覆盖。
- 榜首标的。
- 模拟账户是否可应用。

### 17.2 候选名单

展示：

- 候选调入。
- 调出复核。
- 股票代码和名称。
- LTR / Qlib / 全市场排名摘要。

小白解释：

```text
候选调入不是“马上买”，只是今天策略认为值得人工复盘的名单。
```

### 17.3 历史模拟

展示：

- 测试窗口。
- 净收益。
- 最大回撤。
- 交易次数。
- 费用税费。
- 覆盖状态。

提醒：

```text
历史模拟不代表未来收益。
```

### 17.4 模拟账户状态

展示：

- 现金。
- 持仓数。
- 当前决策日期。
- 是否可应用。
- 阻断原因。
- 预计模拟调出。
- 预计模拟调入。
- 跳过与不可应用。

提醒：

```text
只影响模拟账户，不连接券商，不提交真实订单。
```

### 17.5 策略解释助手

展示：

- Agent 回答。
- 引用来源。
- warnings。
- context digest。
- research-only disclaimer。

推荐问题包括：

- 今天策略是什么？
- 排名第一是谁？
- 今天有哪些候选调入？
- 今天有哪些调出复核？
- 为什么模拟账户不能应用？
- 数据新鲜度如何？

## 18. 一只股票从数据到前端的例子

以 `2330` 为例。

### 第一步：原始数据

系统抓到 `2330` 的日线：

```text
date=2026-06-18
open=...
high=...
low=...
close=...
volume=...
```

### 第二步：标准化价格

系统把它转成统一格式，确认：

- 股票代码是标准格式。
- 日期合法。
- 没有缺失关键价格。
- 复权价格可用。

### 第三步：特征

系统计算：

- 最近几天涨跌。
- 最近一段时间波动。
- 成交量是否放大。
- 相对其他股票强不强。

这些特征进入模型。

### 第四步：模型打分

Qlib 给 `2330` 一个全市场分数和排名。

如果 `2330` 进入 qlib top50，LTR 可能继续给它一个 rerank 分数。

输出进入标准字段：

```text
candidate_rank
buy_score
score_rank
full_qlib_rank
```

### 第五步：策略判断

策略看：

- `2330` 是否在 top50。
- `2330` 的 buy_score 是否靠前。
- 当前模拟账户是否已经持有 `2330`。
- 今天最多允许几个买入/卖出意图。

如果满足条件，输出：

```text
intent_action=buy
intent_reason=buy_score_top_candidate
```

但这仍然只是模拟意图。

### 第六步：前端展示

前端可能显示：

```text
候选调入：2330 台积电
排名：1
说明：进入 qlib top50，LTR 排序靠前
```

Agent 可以解释为什么在榜上，但不能说：

```text
你应该买 2330
```

## 19. 哪些数据不能流到后面

为了防止“偷看答案”，以下数据不能进入模型输入或策略输入：

```text
future_return_*
forward_return_*
label_*
realized_pnl
execution_price
execution_date
broker_order_id
target_position
target_weight
```

小白解释：

- `future_return` 是未来收益，模型训练时可以作为标签，但不能作为输入。
- `execution_price` 是成交/回放才知道的价格，策略不能提前知道。
- `target_position` / `target_weight` 会暗示真实仓位或交易动作，不属于只读研究链路。

## 20. 日更失败时，用户看到的是什么

如果数据没齐，系统不应该硬更新。

常见状态：

| 状态 | 小白解释 |
| --- | --- |
| `today_data_window_wait` | 今天数据更新时间还没到 |
| `fresh_data_wait` | 某个数据源还没更新齐 |
| `validator_failed` | 产物生成了，但校验失败，不能发布 |
| `daily_auto_update_passed` | 默认只读日更完成 |

前端或 Agent 可能显示：

```text
数据新鲜度需要确认
等待目标交易日开盘价
当前 evidence 不足
```

这不是坏事。正确的系统宁愿等待，也不应该把不完整数据包装成确定结论。

## 21. 给新模型研发的启示

新增模型时，不能直接把模型分数塞给策略或前端。

必须：

```text
新数据/新特征
-> raw model score
-> ModelAdapter
-> ModelSignalArtifact
-> validator
-> review
```

新增模型第一阶段不应该：

- 改默认模型。
- 改前端。
- 改策略。
- 直接做生产日更。
- 直接进入 Agent prompt。

## 22. 给新策略研发的启示

新增策略时，不能直接读模型私有字段，也不能直接写 replay result。

必须：

```text
StrategyDependency
-> StrategyRule
-> OrderIntentArtifact
-> validator
-> readonly replay
-> review
```

新增策略第一阶段不应该：

- 训练新模型。
- 改默认策略。
- 改前端默认展示。
- 产生真实订单。
- 给目标仓位。

## 23. 最重要的五句话

1. 原始行情只是食材，不能直接给前端当策略。
2. 特征是把价格加工成模型能理解的线索，但不能偷看未来。
3. 模型只负责排序打分，不负责交易。
4. 策略只输出只读意图，不输出真实订单。
5. 前端和 Agent 只解释只读策略上下文，不给买卖指令。

## 24. 当前链路仍需注意的点

当前架构已可以承接新模型/新策略研发，但仍需注意：

- 生产 source artifacts 物化链路后续要继续稳定化。
- Agent prompt latest 默认关闭/dry-run，不是 provider/qlib accepted latest。
- legacy provider publish / accepted latest 代码仍存在，但默认不可达。
- 新模型/新策略第一阶段不得切默认产品路径。
- 所有新增能力必须通过 registry、validator、golden sample 和审查文档。

## 25. 后续执行者需要补充的精确字段清单

本文是小白友好解释，不替代工程字段清单。Pre-R&D 执行者在进入真实研发前，应补充或确认：

```text
当前 Qlib/Alpha 特征清单
当前 Orthogonal LTR 特征清单
当前 ModelSignalArtifact 实际 signals.csv 字段
当前 StrategyDependency YAML
当前 OrderIntentArtifact 样例字段
当前 ReadonlyStrategySnapshot 样例字段
当前 DailyAgentPromptArtifact 样例字段
```

优先来源：

```text
configs/tw_product_artifact_registry.yaml
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_feature_schema.csv
```
