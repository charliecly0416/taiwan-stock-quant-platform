---
created_at: 2026-06-02
status: complete_requirement_spec
scope: quantdinger_tw_stock_qlib_cross_analysis_and_research_workbench
source_project: /home/chuliyang/qlib
target_project: /path/to/taiwan-stock-quant-platform
related_docs:
  - /home/chuliyang/qlib/docs/quantdinger_tw_cross_analysis_requirement_cn.md
  - /home/chuliyang/qlib/docs/quantdinger_tw_option_c_integration_guide_cn.md
  - /path/to/taiwan-stock-quant-platform/docs/TW_STOCK_QLIB_OPTION_C_INTEGRATION_IMPLEMENTATION_CN.md
  - /path/to/taiwan-stock-quant-platform/docs/TW_STOCK_YAHOO_SCRAPLING_DATA_GUIDE_CN.md
---

# QuantDinger 台股 qlib 交叉分析完整需求文档

本文档面向负责 QuantDinger 项目的 Codex，整合“台股交叉分析模块”基础需求和后续更符合用户实际使用的增强功能。目标是在 QuantDinger 中把 qlib 的 Yahoo adjusted 模型排序信号，与 QuantDinger 现有 FinMind/raw 台股趋势、监控、只读回测能力结合起来，形成一个 research-only 的台股研究工作台。

核心结论：

```text
需求合理，建议实现。
第一阶段先做只读交叉分析。
后续逐步增加数据口径对照、qlib 信号历史、榜单变化提醒、人工复盘、只读回测快捷入口和后验验证报表。
全程禁止交易、订单、broker、仓位、paper/live、自动买卖、重训、调参和 qlib provider 自动刷新。
```

---

## 1. 两个项目的职责分工

### 1.1 qlib 项目

路径：

```text
/home/chuliyang/qlib
```

当前能力：

```text
Yahoo-only adjusted 台股数据
Alpha158 特征
LightGBM 模型
150 支已验收台股 universe
每日 top30/top50 research signals
```

核心输出：

```text
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/latest_signal.json
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/<run_id>/top30_signals.csv
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/<run_id>/top50_signals.csv
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/<run_id>/signal_summary.json
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/<run_id>/run_metadata.json
```

qlib 负责回答：

```text
在模型 universe 中，今天哪些股票的横截面排序更靠前？
```

qlib 不负责：

```text
买卖建议
目标仓位
订单
自动交易
QuantDinger 页面展示
QuantDinger raw K 线趋势解释
```

### 1.2 QuantDinger 项目

路径：

```text
/path/to/taiwan-stock-quant-platform
```

当前能力：

```text
台股趋势分析
台股监控提醒
人工复盘状态
台股只读回测
FinMind/raw 或本地日线归档
```

关键模块：

```text
backend/app/services/tw_stock_trend.py
backend/app/routes/tw_stock.py
backend/app/services/tw_stock_monitor.py
backend/app/services/backtest.py
backend/app/routes/backtest.py
backend/app/services/tw_stock_backtest_templates.py
```

QuantDinger 负责回答：

```text
某只股票当前 raw K 线趋势、均线、量价、数据质量、提醒和只读回测表现如何？
```

---

## 2. 总体产品目标

新增一个 research-only 台股研究工作台，第一版名称建议：

```text
台股交叉分析
```

它不是交易策略执行器，而是研究辅助工具。

产品目标：

1. 用 qlib top30/top50 快速找到模型候选股。
2. 用 QuantDinger raw 趋势解释这些候选股当前走势。
3. 标记 qlib 模型和 raw 趋势是否一致或分歧。
4. 显示 qlib Yahoo adjusted 与 QuantDinger FinMind/raw 的数据口径差异。
5. 保留 qlib 信号历史，用于观察排名变化。
6. 生成榜单变化研究提醒。
7. 支持人工复盘状态和备注。
8. 支持从候选股一键进入 TWStock 只读回测。
9. 随着历史积累，生成 qlib 命中率和交叉分类后验验证报表。

明确禁止：

```text
自动交易
自动买入/卖出
提交订单
paper order
live trading
broker/IBKR/quick_trade 调用
根据 qlib rank/score 生成 target position
根据 qlib score 生成仓位比例
把 qlib score 解释为收益率、胜率、涨幅或买入概率
在 QuantDinger 中重训 qlib 模型
在 QuantDinger 中修改或刷新 qlib provider
自动切换 FinMind 补 qlib 数据
```

---

## 3. 第一阶段核心模块：交叉分析

### 3.1 输入

读取 qlib latest signal：

```text
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/latest_signal.json
```

继续读取：

```text
top30_signals.csv
top50_signals.csv
signal_summary.json
run_metadata.json
```

必须校验：

```text
status == accepted
prediction_rows == 150
top30_rows == 30
top50_rows == 50
finite_prediction_share == 1.0
diagnostic_only == true
research_signal_not_order == true
paper_trading_started == false
live_trading_started == false
target_trades_generated == false
executable_orders_generated == false
model_retraining_performed == false
model_tuning_performed == false
provider_switch_performed == false
FinMind_fallback_used == false
mixed_provider_fill_used == false
```

趋势输入复用：

```text
TWStockTrendService.analyze_symbol(symbol=<symbol>, limit=<limit>)
```

### 3.2 分类规则

第一版不做综合买入分，只做分类。

`trend.label` 分组：

```text
positive_trend = uptrend / rebound
neutral_trend = sideways / unknown
negative_trend = downtrend / pullback
```

严重数据 warning：

```text
no_daily_bars
data_source_unavailable
stale_daily_bar
latest_bar_in_future
invalid_twstock_symbol
```

交叉分类：

| qlib | QuantDinger trend | data quality | category | 说明 |
| --- | --- | --- | --- | --- |
| top30 | positive | clean | `focus_watch` | 模型靠前，raw 趋势也支持，重点观察 |
| top30 | negative | clean | `model_trend_divergence` | 模型靠前但 raw 趋势偏弱，人工复盘 |
| top30 | neutral | clean | `model_watch_trend_neutral` | 模型靠前但趋势未确认 |
| top50 | positive | clean | `secondary_watch` | 次级候选，趋势支持 |
| top50 | negative/neutral | clean | `low_priority_watch` | 次级候选但趋势不强 |
| any | any | warning | `data_review_required` | 数据质量优先 |
| any | unavailable | any | `trend_unavailable` | 趋势服务不可用 |

附加字段：

```text
alignment = aligned | divergent | neutral | blocked
priority = high | medium | low | blocked
```

这些字段只用于研究排序和展示，不是交易优先级。

### 3.3 后端 API

新增：

```text
GET /api/tw-stock/cross-analysis/latest
GET /api/tw-stock/cross-analysis/symbol/<symbol>
```

`latest` 参数：

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `bucket` | `top30` | `top30`、`top50`、`all` |
| `limit` | `120` | 趋势分析 K 线条数 |
| `includeRawTrend` | `false` | 是否返回完整 trend report |
| `maxItems` | `30` | 最大返回条数 |

响应必须包含：

```text
qlib.asof
qlib.run_id
qlib.recorder_id
qlib.research_signal_not_order=true
items[].qlib.rank
items[].qlib.score
items[].quantdinger.trend_label
items[].quantdinger.trend_score
items[].quantdinger.quality_warnings
items[].cross.category
items[].cross.summary
items[].cross.human_action
trading.orders_enabled=false
trading.connects_to_broker=false
trading.paper_orders_enabled=false
trading.live_trading_enabled=false
```

---

## 4. 增强模块 A：数据口径对照

### 4.1 目的

qlib 使用 Yahoo adjusted；QuantDinger 使用 FinMind/raw 或本地 raw 归档。两者口径不同，必须透明展示，避免用户误解。

### 4.2 功能

对每个交叉分析 item 显示：

```text
qlib_asof
qlib_source = Yahoo adjusted
quantdinger_latest_date
quantdinger_source = FinMind/raw or local archive
date_aligned = true/false
raw_latest_close
qlib_adjusted_close 如果可取
口径说明
```

第一版如果无法直接从 qlib provider 取 adjusted close，可先只显示：

```text
qlib signal asof
QuantDinger latest_date
date_gap_days
data_basis_note
```

### 4.3 分类

```text
data_basis_aligned
qlib_signal_stale
quantdinger_raw_stale
date_mismatch
basis_difference_not_checked
```

### 4.4 页面提示

```text
qlib score 来自 Yahoo adjusted 模型数据。
QuantDinger 趋势来自本地/FinMind raw 日线。
两者可能因除权息、复权或数据源延迟出现差异。
```

---

## 5. 增强模块 B：qlib 信号历史留存

### 5.1 目的

只看当天 top30/top50 不够。保留每天 qlib signals 后，可以观察：

```text
连续入榜
新进入榜单
排名上升
排名下降
跌出榜单
```

### 5.2 推荐表

```text
qd_tw_qlib_signal_runs
qd_tw_qlib_signals
```

`qd_tw_qlib_signal_runs` 字段建议：

```text
id
run_id
asof
status
source_root
run_dir
recorder_id
provider_uri
config_path
prediction_rows
top30_rows
top50_rows
finite_prediction_share
diagnostic_only
research_signal_not_order
raw_summary_json
raw_metadata_json
imported_at
```

`qd_tw_qlib_signals` 字段建议：

```text
id
run_id
asof
instrument
symbol
bucket
rank
score
source_model_recorder
diagnostic_only
research_signal_not_order
created_at
```

唯一约束：

```text
unique(run_id, bucket, instrument)
unique(asof, bucket, instrument)
```

### 5.3 导入规则

只允许导入：

```text
status=accepted
research_signal_not_order=true
diagnostic_only=true
```

导入必须幂等：

```text
同一个 run_id 重复导入不会重复写 signals。
```

---

## 6. 增强模块 C：榜单变化提醒

### 6.1 目的

让用户不只看到“今天排名”，还能看到“变化”。

### 6.2 研究提醒类型

```text
new_top30_entry
new_top50_entry
rank_up
rank_down
dropped_from_top30
dropped_from_top50
consecutive_top30
consecutive_top50
qlib_top30_trend_turn_weak
qlib_top30_data_warning
```

### 6.3 示例规则

```text
新进入 top30 -> new_top30_entry
连续 3 个 accepted asof 进入 top30 -> consecutive_top30
rank 提升 >= 10 -> rank_up
rank 下降 >= 10 -> rank_down
从 top30 跌出但仍在 top50 -> dropped_from_top30
qlib top30 且 trend_label 变成 downtrend/pullback -> qlib_top30_trend_turn_weak
```

所有提醒必须写明：

```text
orders_enabled=false
human_action=人工复盘，不自动交易
```

---

## 7. 增强模块 D：交叉分析解释页

### 7.1 目的

用户点击某只股票后，应能看懂为什么它被归类。

### 7.2 页面内容

```text
symbol
instrument
qlib rank / score / bucket / asof
QuantDinger trend label / score
latest close / latest date
MA5 / MA20 / MA60
ret_5d / ret_20d / ret_60d
volume ratio
quality warnings
近几天 qlib rank 变化
cross category
解释文案
人工复盘状态
备注
只读回测入口
```

### 7.3 解释文案示例

`focus_watch`：

```text
该股进入 qlib top30，模型排序靠前；QuantDinger raw 趋势也偏强，可加入重点观察并人工复盘。
```

`model_trend_divergence`：

```text
该股进入 qlib top30，但 QuantDinger raw 趋势偏弱。可能是模型信号领先、短期回调或数据口径差异，需要人工复盘。
```

`data_review_required`：

```text
该股存在数据质量提示。请先复核数据新鲜度和 K 线质量，再决定是否继续观察。
```

---

## 8. 增强模块 E：人工复盘记录

### 8.1 目的

每天 top30/top50 数量不少，用户需要管理处理进度。

### 8.2 状态

```text
pending
watching
reviewed
ignored
data_issue
```

### 8.3 字段

```text
user_id
asof
symbol
run_id
cross_category
decision_status
user_note
updated_at
```

### 8.4 API

```text
GET /api/tw-stock/cross-analysis/reviews?asof=...
PUT /api/tw-stock/cross-analysis/reviews/<id>
```

允许更新：

```text
decision_status
user_note
```

不允许产生：

```text
订单
持仓
交易计划
```

---

## 9. 增强模块 F：只读回测快捷入口

### 9.1 目的

从交叉分析结果快速验证单只候选股的历史技术模板表现。

### 9.2 行为

点击：

```text
历史模拟
```

预填：

```json
{
  "market": "TWStock",
  "symbol": "<symbol>",
  "timeframe": "1D",
  "initialCapital": 1000000,
  "strategyId": "ma_cross_builtin",
  "persist": false,
  "enableMtf": false
}
```

可选模板：

```text
ma_cross_builtin
rsi_builtin
macd_builtin
bollinger_builtin
```

文案必须说明：

```text
该回测是对选定股票的技术模板历史模拟，不代表 qlib 策略历史收益。
```

禁止写：

```text
qlib top30 策略回测
模型建议买入
明日上涨概率
```

---

## 10. 增强模块 G：观察组合模拟

### 10.1 目的

用户可以手动从交叉分析中选出若干股票，形成观察组合，只做研究模拟。

### 10.2 功能

```text
等权观察组合
每日收益曲线
与 TWII / 0050 对比
组合内股票列表
手动加入/移除
```

### 10.3 边界

观察组合不是交易组合：

```text
不生成订单
不生成目标仓位
不连接 broker
不自动调仓
```

该模块建议放在后期实现，不作为第一版必需项。

---

## 11. 增强模块 H：数据新鲜度仪表盘

### 11.1 目的

用户需要知道今天的 qlib 和 QuantDinger 数据是否新鲜。

### 11.2 展示字段

```text
qlib latest_signal asof
qlib run_id
qlib status
QuantDinger raw archive latest date
FinMind/local source latest date
date gap
stale status
blocked reason
```

### 11.3 状态

```text
fresh
historical
stale
blocked
unknown
```

规则：

```text
不复制旧 qlib signal 成今日 signal。
不自动触发 qlib refresh。
只提示用户或执行者另开数据刷新工作。
```

---

## 12. 增强模块 I：后验验证报表

### 12.1 目的

当 qlib signals 积累一段时间后，评估交叉分析是否真的有研究价值。

### 12.2 指标

```text
top30 次日平均 raw return
top50 次日平均 raw return
top30 / top50 hit rate
RankIC
按 cross.category 分组的次日收益
focus_watch vs model_trend_divergence 对比
positive_trend vs negative_trend 对比
```

### 12.3 边界

该报表是后验研究，不是调参入口。

禁止：

```text
根据报表自动修改 qlib 模型
根据报表自动调 topk/n_drop
根据报表自动交易
```

如需改变模型、参数或规则，必须另开 qlib/QuantDinger 研究工作单。

---

## 13. 推荐实现阶段

### Phase 1：qlib reader + cross analysis API

实现：

```text
backend/app/services/tw_stock_qlib_option_c.py
backend/app/services/tw_stock_cross_analysis.py
GET /api/tw-stock/cross-analysis/latest
GET /api/tw-stock/cross-analysis/symbol/<symbol>
```

验收：

```text
accepted qlib top30/top50 可读
invalid qlib run blocked
能生成 cross.category
trading flags 全 false
```

停审节点：

```text
后端 API + safety tests 完成后停审。
```

### Phase 2：前端交叉分析展示

实现：

```text
台股监控页新增“台股交叉分析”模块
Top30/Top50 tabs
category / human_action / 数据口径提示
```

验收：

```text
页面能展示交叉分析
无买卖/订单/broker/paper/live 入口
```

停审节点：

```text
前端展示和静态安全检查完成后停审。
```

### Phase 3：数据口径对照 + 新鲜度仪表盘

实现：

```text
qlib asof vs QuantDinger latest_date
date gap
source/basis note
stale/historical/blocked 状态
```

验收：

```text
用户能看到两套数据口径和新鲜度差异。
```

停审节点：

```text
数据口径和新鲜度状态上线前停审。
```

### Phase 4：qlib 信号历史 + 榜单变化提醒

实现：

```text
qd_tw_qlib_signal_runs
qd_tw_qlib_signals
import latest accepted run
rank change alerts
consecutive top30/top50
```

验收：

```text
导入幂等
只导入 accepted research signals
提醒不产生订单
```

停审节点：

```text
DB migration + import + alert tests 完成后停审。
```

### Phase 5：人工复盘 + 只读回测快捷入口

实现：

```text
decision_status
user_note
从 item 进入 TWStock read-only backtest
```

验收：

```text
复盘状态可保存
回测 persist=false
回测不触发交易路径
```

停审节点：

```text
复盘和回测联动完成后停审。
```

### Phase 6：后验验证报表

实现条件：

```text
qlib accepted signals 已积累足够多个 asof。
```

实现：

```text
top30/top50 次日收益
RankIC
按 cross.category 分组表现
```

停审节点：

```text
首次后验验证报表完成后停审；不得自动调参。
```

---

## 14. 测试要求

### 后端测试

建议新增：

```text
backend/tests/test_tw_stock_qlib_option_c_reader.py
backend/tests/test_tw_stock_cross_analysis_service.py
backend/tests/test_tw_stock_cross_analysis_api.py
```

必须覆盖：

```text
qlib accepted run -> pass
qlib non-accepted run -> blocked
research_signal_not_order=false -> blocked
prediction_rows != 150 -> blocked
top30 + uptrend -> focus_watch
top30 + downtrend -> model_trend_divergence
top50 + uptrend -> secondary_watch
quality warning -> data_review_required
trend service failure -> trend_unavailable
trading flags 全 false
不 import/call broker/order/live/paper/quick_trade
```

### 前端测试

建议扩展：

```text
tw-stock-monitor static check
tw-stock-monitor local smoke
```

必须检查：

```text
交叉分析模块可见
Top30/Top50 可切
research-only 文案可见
数据口径提示可见
无买入/卖出/下单/broker/paper/live 入口
只读回测入口不会出现交易文案
```

---

## 15. 最终验收标准

完整需求第一阶段验收：

```text
QuantDinger 能读取 qlib latest accepted top30/top50
能为每只 qlib 候选股生成 QuantDinger trend summary
能生成 cross.category / alignment / human_action
API 和页面明确 research-only
页面显示 Yahoo adjusted vs FinMind/raw 口径差异
无任何交易、订单、broker、paper/live、仓位入口
invalid/stale/blocked qlib run 不会被当成今日可用信号
测试覆盖安全边界
```

完整增强验收：

```text
qlib signal history 可幂等导入
榜单变化提醒可用
人工复盘状态可保存
只读回测快捷入口可用
数据新鲜度仪表盘可用
后验验证报表只做研究，不触发调参或交易
```

---

## 16. 给 QuantDinger 执行者的一句话

请把 qlib Option C top30/top50 接入 QuantDinger，先实现 research-only 台股交叉分析：严格校验 qlib accepted signals，复用 `TWStockTrendService` 生成 raw 趋势摘要，输出 `focus_watch / model_trend_divergence / secondary_watch / data_review_required` 等解释分类；随后按阶段加入数据口径对照、信号历史、榜单变化提醒、人工复盘和只读回测快捷入口，全程禁止交易、订单、broker、paper/live、仓位、重训、调参和 qlib provider 自动刷新。

