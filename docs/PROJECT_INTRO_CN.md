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
-> QuantDinger backend 读取信号、趋势、技术状态、位置风险、交叉分析、Agent context
-> 只读组合策略回放和模拟账户研究闭环
-> QuantDinger-Vue 前端以用户第一视角展示
-> 人工观察、模拟复盘与后续 Decision Model 研究
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

- 台股研究页面，首屏优先展示当前 Top30/Top50 和今日复盘重点
- qlib Top30/Top50 研究排序展示
- qlib、QuantDinger 趋势、MA/RSI/MACD/Bollinger 技术状态和价格位置风险的交叉分析
- 5 个用户可理解的只读组合策略回放
- 模拟账户研究闭环、K 线交易 marker 和持仓复盘
- Agent 问答面板
- 内部数据状态、历史 run、dry-run 等诊断信息不再作为普通用户主流程展示

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

## 当前用户第一页面原则

当前前端不再把开发/运维诊断面板作为主流程。普通用户进入台股研究页后，应该优先得到三个答案：

1. 今天 Top30/Top50 里哪些最值得先看。
2. 为什么：模型排名、趋势、技术状态、价格位置风险是否一致。
3. 过去表现如何：只读组合规则历史回放，不写模拟账户，不连接券商。

因此，数据状态、历史研究 run、dry-run 等内容只作为维护或历史测试资产，不作为当前页面的一键验收标准。

## 当前收敛后的组合策略框架

当前项目只保留 5 个用户可理解的主策略作为前端策略回放口径：

| 策略 key | 用户名称 | 作用 |
| --- | --- | --- |
| `rank_rotate_top30` | 跌出 Top30 轮动 | 反应更快，交易更频繁，用作中间参考。 |
| `rank_rotate_top50` | 跌出 Top50 轮动 | 更稳，持仓跌出 Top50 才做风险减少。 |
| `rank_rotate_top50_adaptive_score` | Top50 自适应 score | 正常市况继承 Top50，谨慎/下跌市况只允许校准 score 区间候选补仓。 |
| `rank_rotate_top50_adaptive_score_risk_control` | Top50 自适应 score + 风控 | 高级对照，市场差且组合回撤扩大时暂停补仓。 |
| `confirmed_exit` | 连续转弱才复盘 | 不因单日波动退出，连续转弱后才风险复盘，降低过度交易。 |

`direct_rank`、`position_filter`、`pullback_entry`、`rank_rotate_top30_adaptive_score` 等研究对照项不再作为普通用户前端主策略展示。

## 下一阶段：Decision Model

当前规则策略阶段已经形成 baseline。下一阶段建议尝试二阶段 Decision Model，但不直接做自动交易模型：

```text
qlib baseline rank/score + 大盘状态 + 技术状态 + 价格位置风险 + FinMind 补充特征 + 持仓状态
-> Candidate Generator 扩大候选池
-> Entry Model / Exit Risk Model
-> 只读组合回放对比当前 5 个 baseline 策略
```

Decision Model 的输出应是 `entry_score`、`exit_risk_score` 和 `confidence`，用于研究排序和风险复盘，不直接生成真实买卖指令。

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
