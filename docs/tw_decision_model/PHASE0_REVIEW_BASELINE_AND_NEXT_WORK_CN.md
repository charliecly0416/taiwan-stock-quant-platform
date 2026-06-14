# Decision Meta Model 审核基准与下一步工作文档：Phase 0 数据审计

## 0. 审查者职责确认

本文档依据 `prompt_investigate.md` 与 `docs/TW_STOCK_DECISION_META_MODEL_DESIGN_CN.md` 编写。

审查者职责：

- 审查执行者每一步的执行报告、代码、文档、测试结果。
- 判断是否符合总设计、用户第一性原则和 research-only 安全边界。
- 每次审查后输出“审核意见 + 下一步工作文档”的合并文档。
- 不直接实现功能，除非用户明确要求接手。
- 不提交、不推送，除非用户明确要求。

后续每一步审查都必须落成文件，供执行者继续执行。

## 1. 本步审核结论

结论：暂停需执行 Phase 0。

当前尚未进入实现审查阶段。执行者必须先完成 Phase 0 数据审计与特征可用性确认，不能跳过 Phase 0/1 直接训练 Entry Model 或 Exit Risk Model。

## 2. 发现的问题

1. 当前只是总设计阶段，尚未证明补充特征具备 point-in-time 可用性。
2. FinMind 财务、月营收、估值等字段存在未来函数风险，必须确认 `announcement_date` / `available_at`。
3. qlib score 的绝对值不可直接用于规则，必须先审计分布和日期内分位。
4. Candidate Generator 所需的流动性、缺失率、停牌、涨跌停、滑点风险字段尚未确认覆盖率。
5. 大盘状态、market breadth、TWII 特征是否稳定归档尚未确认。
6. 暂不能进入模型训练、标签生成或前端产品化。

## 3. 必须修复项

执行者必须输出一份 `feature availability report`，至少覆盖以下内容。

### 3.1 qlib historical signal 覆盖率

- `date`
- `symbol`
- `qlib_score`
- `qlib_rank`
- Top10 / Top30 / Top50 标记可否重建
- score 日期内分位、z-score 是否可计算

### 3.2 OHLCV / adjusted bars 覆盖率

- 每个 symbol 最早/最新日期
- 缺失交易日比例
- adjusted close 是否可用于未来收益标签
- 成交量、成交额是否完整

### 3.3 技术趋势特征覆盖率

- MA5 / MA10 / MA20 / MA60
- RSI14
- MACD
- Bollinger position
- 20d return
- 20d volatility
- volume ratio
- position risk status

### 3.4 流动性与交易可行性字段

- 20 日均成交额
- 成交量稳定性
- 缺失率
- 停牌风险
- 涨跌停风险
- 可用于滑点惩罚的 proxy

### 3.5 TWII / 大盘状态字段

- TWII close / return
- ret20 / ret60
- close vs MA60 / MA120
- volatility 20d
- drawdown from 60d high
- market breadth
- market_regime 只能作为解释与分组评估，不得作为硬买卖闸门

### 3.6 FinMind 字段

- institutional net buy
- margin balance
- short balance
- monthly revenue
- valuation PER/PBR
- 每类字段必须说明 `available_at` 或 lag 规则
- 财务/月营收不得按 `period` 直接 join

## 4. 可暂缓项

1. 暂不训练 LightGBM。
2. 暂不生成 Entry / Exit 标签。
3. 暂不做 LambdaRank。
4. 暂不接前端。
5. 暂不修改组合回放逻辑。
6. 若 FinMind 某些字段缺失，可以先标记为 v1 暂缓，但必须说明原因和替代方案。

## 5. 下一步工作文档：Phase 0 数据审计

### 5.1 目标

确认 Decision Model v1 可用的数据范围、时间覆盖、缺失情况、point-in-time 安全规则，以及哪些特征可以进入 Phase 1 样本构建。

### 5.2 范围

只做只读审计和报告生成。

允许：

- 读取本地数据库、归档文件、qlib signal、FinMind 缓存、OHLCV 数据。
- 编写只读审计脚本。
- 输出 markdown / csv / json 报告。

禁止：

- 不训练模型。
- 不生成真实交易建议。
- 不写 broker / orders / quick-trade。
- 不触发真实数据刷新、provider publish、accepted latest switching。
- 不修改模拟账户、monitor config、alerts。
- 不在代码或报告中使用“买入/卖出/立即操作”等真实交易语义。
- 不把 qlib score 固定区间写成规则，例如 `0.4-0.8` 或 `0.04-0.08`。

### 5.3 输入

执行者应检查以下输入源，按项目实际路径为准：

1. qlib historical signal / rank / score。
2. adjusted OHLCV daily bars。
3. TWII index data。
4. 本地技术指标或 KlineService 可复算数据。
5. FinMind institutional / margin / monthly revenue / valuation 归档。
6. 当前稳定股票池定义。
7. 当前 baseline 回放中使用的 Top30 / Top50 / adaptive score / risk-control 相关输出。

### 5.4 输出

必须生成：

1. `docs/tw_decision_model/phase0_feature_availability_report.md`
2. `data_tw/experiments/decision_model/phase0_feature_coverage.csv`
3. `data_tw/experiments/decision_model/phase0_data_sources.json`
4. `data_tw/experiments/decision_model/phase0_point_in_time_rules.md`

如路径不存在，可创建目录，但不得覆盖无关文件。

### 5.5 执行步骤

1. 建立审计目录。
2. 盘点 qlib signal：
   - 覆盖日期范围
   - symbol 数量
   - 每日候选数量分布
   - score min/max/mean/std
   - 按日期 score percentile / z-score 是否可计算
   - Top50 是否每日完整

3. 盘点 OHLCV：
   - 每个 symbol 日期范围
   - adjusted close 可用性
   - volume / trading value 可用性
   - 缺失率
   - 疑似停牌区间
   - 是否足够计算 20d / 60d 特征

4. 盘点技术指标：
   - 若已有归档，审计归档覆盖率
   - 若无归档，确认是否可从 OHLCV 复算
   - 明确每个技术指标是否进入 v1

5. 盘点流动性和滑点风险字段：
   - 20d average trading value
   - volume stability
   - low-liquidity symbol count
   - limit-up / limit-down proxy 是否可得
   - 停牌或缺失交易日 proxy 是否可得

6. 盘点大盘状态：
   - TWII 覆盖范围
   - ret20 / ret60
   - MA60 / MA120
   - volatility
   - drawdown
   - breadth 是否可得
   - 若 breadth 不可得，说明 v1 替代方案

7. 盘点 FinMind：
   - 每类表的日期范围、symbol 覆盖、缺失率
   - 是否有公告日或可用日
   - 若只有 period，必须标记为不可直接进入 v1
   - 给出保守 lag 规则建议
   - 财务/月营收必须输出 `source_period`、`available_at`、`days_since_last_report` 的可实现性判断

8. 输出 v1 特征准入表：
   - `feature_name`
   - `source`
   - `coverage_pct`
   - `start_date`
   - `end_date`
   - `point_in_time_safe`
   - `available_at_rule`
   - `v1_status`: include / defer / reject
   - `reason`

9. 输出风险清单：
   - 未来函数风险
   - 样本泄漏风险
   - 覆盖不足风险
   - 流动性风险
   - qlib score 分布不可比风险
   - 产品 research-only 边界风险

### 5.6 验收标准

Phase 0 只有在以下条件满足后才能通过：

1. 所有候选 v1 特征都有覆盖率、缺失率、最早日期、最新日期。
2. 每类数据都有明确 point-in-time 规则。
3. FinMind 财务/月营收/估值没有按 period 直接 join 的方案。
4. qlib score 完成分布审计，且没有写死绝对 score 区间作为规则。
5. Candidate Generator 所需的流动性过滤字段可用，或明确哪些暂缓。
6. 大盘连续特征可用性明确，`market_regime` 仅用于解释和分组评估。
7. 报告明确列出 v1 include / defer / reject 特征。
8. 未发生任何写交易、下单、刷新 provider、切换 accepted latest、修改 monitor 配置等越界行为。

### 5.7 执行报告模板

执行者完成后必须提交：

```markdown
# Phase 0 数据审计执行报告

## 1. 执行摘要

- 审计日期：
- 代码变更：
- 生成文件：
- 是否触碰只读边界：

## 2. 数据源清单

| 数据源 | 路径/表名 | 日期范围 | symbol 覆盖 | 状态 |
|---|---|---:|---:|---|

## 3. 特征覆盖率

| feature | source | coverage_pct | start_date | end_date | point_in_time_safe | v1_status | reason |
|---|---|---:|---|---|---|---|---|

## 4. qlib score 分布审计

- raw score 范围：
- date percentile 是否可计算：
- date z-score 是否可计算：
- 是否发现 score 量级漂移：

## 5. FinMind point-in-time 审计

| feature_group | has_available_at | proposed_lag_rule | safe_forward_fill | v1_status |
|---|---|---|---|---|

## 6. 流动性与滑点风险审计

- 20d avg trading value 可用性：
- 停牌 proxy：
- 涨跌停 proxy：
- 低流动性过滤建议：

## 7. 大盘状态审计

- TWII 连续特征：
- market breadth：
- market_regime 生成方式：
- 是否仅用于解释/分组：

## 8. 风险与阻塞项

- 必须修复：
- 需要用户确认：
- 可暂缓：

## 9. Phase 1 准入建议

- 可进入 Phase 1 的特征：
- 暂缓特征：
- 拒绝特征：
- 是否建议进入 Phase 1：
```

## 6. 审查者备注

执行者提交 Phase 0 报告前，不允许进入样本构建或模型训练。

若报告中发现 FinMind 无公告日、qlib score 分布不可解释、稳定股票池无法重建、或流动性过滤不可实现，应暂停推进并列出“需要用户确认的问题”。
