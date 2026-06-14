# 台股 Decision Model 正交数据增强新主线方案

## 1. 背景

上一轮 Entry Model v1 已归档失败。失败原因不是执行越界，而是当前特征集没有稳定超过 `baseline_qlib_rank`：

- qlib rank 本身已经是强基线。
- v1 主要使用 qlib score/rank、OHLCV 技术指标、流动性 proxy、大盘连续特征。
- 这些信息与 qlib baseline 相关性较高，正交信息不足。
- binary / regression / ensemble 三类候选均未稳定通过 Phase 3 gate。

因此，本方案不是继续 Phase 2D，也不是在失败模型上小修小补，而是重启一条新研究主线：

> 在保留 qlib rank 作为主排序基线的前提下，引入法人筹码、融资融券、月营收 YoY/MoM 等正交数据，先验证信息增量，再决定是否训练风险过滤或持仓风险模型。

## 2. 用户第一性原则

本主线必须始终服从：

1. 简单：前端最终只给用户看可理解的研究结论，不展示复杂模型内部字段。
2. 准确：所有历史验证必须严格 point-in-time，不允许未来函数。
3. 清晰：必须说明 qlib、法人筹码、融资融券、月营收分别贡献什么信息。
4. 实用：若不能稳定改善研究判断，就归档，不强行产品化。

本项目仍是 research-only，不接真实券商，不生成真实订单，不做自动买卖。

## 3. 新数据源假设

优先考虑以下正交数据。

### 3.1 法人筹码

候选字段：

- 外资买卖超。
- 投信买卖超。
- 自营商买卖超。
- 三大法人合计买卖超。
- 连续 N 日买超/卖超。
- 买卖超占成交量比例。
- 外资/投信同步方向。

预期作用：

- 识别资金是否确认 qlib 排名。
- 识别股价上涨但法人撤退的风险。
- 对中小型台股的趋势延续可能有增量。

### 3.2 融资融券

候选字段：

- 融资余额变化。
- 融券余额变化。
- 融资使用率 proxy。
- 融券回补 proxy。
- 融资快速增加且价格高位。
- 融资下降但价格不跌。

预期作用：

- 更适合风险过滤，而不是直接买入增强。
- 识别散户杠杆拥挤、追高风险、轧空风险。
- 辅助解释“排名高但不宜新增观察”的情况。

### 3.3 月营收

候选字段：

- 月营收 YoY。
- 月营收 MoM。
- YoY 连续改善/转弱。
- 近 3 个月 YoY 均值。
- 近 3 个月 YoY 斜率。
- 公告后天数 `days_since_last_report`。

预期作用：

- 提供基本面确认。
- 更适合中期稳定性判断，不适合解释每日短线波动。
- 可辅助区分“技术强但基本面不支持”和“排名高且基本面同步改善”。

## 4. 关键原则：Point-in-Time 优先

所有新数据必须先通过发布时间审计，才能进入样本。

必须保留：

- `source_period`
- `announcement_date`
- `available_at`
- `days_since_last_report`
- `data_source`
- `raw_value`
- `derived_feature_value`

禁止：

- 用财报所属季度/月直接 join 到当月交易日。
- 用事后修正值覆盖历史当时可见值。
- 用没有 `available_at` 或 `announcement_date` 的财务/月营收字段训练。
- 因为数据不齐就手工补未来值。

如果 FinMind / Scrapling 拉到的数据没有可审计发布时间，则该字段只能归档为 deferred，不得进入模型。

## 5. 问题定义调整

本轮不建议继续做“全候选二次重排 Entry Model”。

更合理的问题定义是：

### 5.1 第一目标：qlib TopN 风险过滤

输入：

- qlib rank / score。
- 法人筹码。
- 融资融券。
- 月营收。
- 技术状态。
- 大盘连续特征。

输出：

- `normal_watch`：正常观察。
- `confirmed_watch`：多源确认，优先研究。
- `caution_watch`：排名高但有风险。
- `defer_watch`：暂缓新增观察。
- `review_existing`：若已持有，进入风险复盘。

这比直接输出“买哪个”更符合小白用户体验。

### 5.2 第二目标：持仓风险模型

对模拟账户持仓或 Top50 已有候选判断：

- 未来 3 到 10 日是否有较大回撤风险。
- 是否存在排名恶化、技术转弱、法人撤退、融资拥挤等组合风险。
- 是否需要进入复盘，而不是立即给出交易动作。

### 5.3 暂不作为目标

以下内容暂缓：

- 自动交易。
- 目标仓位。
- 真实买卖指令。
- 接 broker。
- 全市场直接选股替代 qlib。
- 仅凭模型输出改写现有前端主策略。

## 6. 候选池设计

为了避免只看 Top30/Top50 漏掉中等 score 但更有基本面或筹码支持的股票，候选池分三层：

1. qlib Top50：默认研究主池。
2. qlib Top150：扩展审计池，用于判断正交数据是否能从更大范围找出增量。
3. score percentile band：按每日 score 分位数校准，不写死绝对 score 区间。

模型训练前必须先报告：

- Top50 内正交特征是否有增量。
- Top150 重排是否优于 Top50 主池。
- 低 rank 但法人/营收强的股票是否真的有后续收益。
- 扩大候选池是否显著增加噪声。

## 7. 分阶段执行计划

### Phase 0：正交数据可用性与 PIT 审计

目标：

- 审计法人筹码、融资融券、月营收数据是否可用。
- 确认历史覆盖、字段含义、发布时间、缺失率。
- 判断哪些字段可进入 Phase 1。

产物：

- `docs/tw_decision_model_orthogonal/PHASE0_EXECUTION_REPORT_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE0_REVIEW_AND_PHASE1_WORK_CN.md`
- `data_tw/experiments/decision_orthogonal/phase0_data_sources.json`
- `data_tw/experiments/decision_orthogonal/phase0_feature_availability.csv`
- `data_tw/experiments/decision_orthogonal/phase0_point_in_time_rules.md`

Gate：

- 没有 `available_at` 或等价发布时间的字段不得进入 Phase 1。
- 若三类数据全部无法 PIT 化，则本主线停止。

### Phase 1：PIT 样本与单因子增量检验

目标：

- 构建 date-symbol 样本。
- 合并 qlib rank、OHLCV 技术、大盘、法人、融资融券、月营收。
- 先做单因子和分组检验，不训练模型。

必须检验：

- 法人连续买超是否在 Top50 内有超额收益。
- 投信买超是否对中小盘更有效。
- 融资快速上升是否对应追高风险。
- 月营收 YoY 改善是否提升后续 20/60 日稳定性。
- 正交数据与 qlib rank 的相关性是否足够低。

产物：

- `phase1_samples.parquet`
- `phase1_schema.json`
- `phase1_factor_increment_report.md`
- `phase1_leakage_audit_report.md`
- `PHASE1_EXECUTION_REPORT_CN.md`

Gate：

- 至少一类正交特征在独立年份/区间有稳定增量，才进入 Phase 2。
- 若只在单一区间有效，不得训练模型。

### Phase 2：规则型风险过滤 baseline

目标：

先不训练 ML 模型，构建可解释规则 baseline。

示例规则：

- qlib Top50 + 法人同步买超 + 月营收 YoY 改善 -> `confirmed_watch`
- qlib Top50 + 融资快速增加 + 高位偏离 MA20/MA60 -> `caution_watch`
- qlib Top50 + 法人连续卖超 + 技术转弱 -> `review_existing`
- qlib Top50 但月营收连续转弱 -> `defer_watch`

产物：

- 规则定义。
- 历史分组表现。
- 与现有 Top50 策略对照。

Gate：

- 规则 baseline 必须比裸 qlib rank 更清晰地降低风险或改善 top bucket 表现。
- 如果规则 baseline 无效，不进入模型训练。

### Phase 3：Risk Filter Model v1

目标：

训练模型只做风险过滤/优先级解释，不直接替代 qlib rank。

候选模型：

- LightGBM ranking/regression。
- Calibrated risk classifier。
- 不使用复杂深度模型作为 v1。

输出：

- `risk_score`
- `confidence_level`
- `watch_status`
- `top_reasons`

Gate：

- 必须同时超过规则 baseline 和 qlib rank baseline。
- 必须在多个年份、多个市场状态稳定。
- 必须可解释，不能只有黑盒分数。

### Phase 4：持仓风险验证

目标：

将模型用于模拟账户持仓复盘，而不是新增买入建议。

验证：

- 是否能提前识别明显转弱持仓。
- 是否减少高位追入。
- 是否降低最大回撤。
- 是否保持合理换手。

Gate：

- 若只能提高收益但显著增加换手或回撤，不通过。
- 若解释不清晰，不进入前端。

### Phase 5：前端只读产品化

目标：

只在台股研究/模拟账户中加入简单结论：

- 多源确认。
- 谨慎观察。
- 暂缓观察。
- 持仓复盘。

禁止展示：

- 复杂模型字段。
- 训练指标。
- 内部 run id。
- 真实买卖建议。
- 目标仓位。

### Phase 6：长期验收与归档

目标：

- Playwright 只读验收。
- 后端测试。
- 文档更新。
- 明确是否接入主线。

Gate：

- 若不能保持简单、准确、清晰、实用，则只归档研究，不进入产品。

## 8. 执行与审查协作机制

本主线继续采用双窗口机制：

1. 执行者只执行审查者下发的下一步工作文档。
2. 每一步完成后，执行者必须给出执行报告。
3. 审查者审查执行报告、代码、数据产物和安全边界。
4. 审查者给出“审核意见 + 下一步工作文档”合并文档。
5. 若出现未知问题、数据不可 PIT 化、需要引入新数据源、需要改变目标、需要进入产品化，必须停下来问用户。
6. 执行者不得自行新增主线外实验。

## 9. 当前建议

建议从 Phase 0 开始。

第一步不要训练模型，也不要改前端。只做正交数据可用性与 point-in-time 审计。

如果 Phase 0 证明法人筹码、融资融券、月营收都无法获得可审计发布时间，则本主线直接停止。

如果 Phase 0 通过，再进入 Phase 1 做单因子/分组增量检验。只有 Phase 1 证明存在稳定信息增量，才允许进入规则 baseline 或模型训练。

