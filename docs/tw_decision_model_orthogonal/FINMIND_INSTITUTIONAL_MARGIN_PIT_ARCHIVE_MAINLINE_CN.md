# FinMind 法人筹码 + 融资融券 PIT Archive 与风险确认/决策过滤层主线工作文档

生成日期：2026-06-13
更新日期：2026-06-14

## 1. 背景

当前主策略与 LTR 主线仍以 qlib baseline / Phase1C qlib-preserving LTR rerank 为核心。正交数据不应直接替代主排序，也不应未经验证进入前端推荐。

本主线分两段推进：

```text
第一段：法人筹码与融资融券能否形成 point-in-time safe 的行级归档。
第二段：在不改 qlib / LTR 主排序的前提下，把这些正交数据用于外层风险确认 / 决策过滤。
```

本主线的核心判断是：新正交数据第一站不直接进入 qlib，也不直接进入 LTR，而是进入外层风险确认层，用来回答：

```text
qlib / LTR 高排名结果是否值得信任？
是否存在法人撤退、融资拥挤、追高或筹码风险？
是否应该从“优先研究”降级为“谨慎观察”或“暂缓观察”？
```

已有小范围真实可得性审计显示：

- 审计文档：`docs/tw_decision_model_orthogonal/FINMIND_ORTHOGONAL_AVAILABILITY_AUDIT_CN.md`
- 审计范围：`TW2330,TW2317,TW2454,TW2308,TW2357,TW6290`
- 审计日期：`2026-05-01` 至 `2026-06-12`
- 法人筹码：6/6 请求成功，总行数 900
- 融资融券：6/6 请求成功，总行数 180
- 月营收：6/6 请求成功，但缺少明确公告日，不纳入本小主线

## 2. 为什么先做法人筹码 + 融资融券

### 2.1 法人筹码

FinMind 数据集：

```text
TaiwanStockInstitutionalInvestorsBuySell
```

已确认字段：

- `stock_id`
- `date`
- `name`
- `buy`
- `sell`

可形成的候选归档字段：

- 外资买卖超
- 投信买卖超
- 自营商买卖超
- 三大法人合计买卖超
- N 日连续买超/卖超
- 买卖超占成交量比例，需后续 join 日线成交量

价值：

- 判断 qlib 高排名是否有资金确认；
- 识别价格上涨但法人撤退的风险；
- 为人工复盘解释提供更直观的资金面理由。

### 2.2 融资融券

FinMind 数据集：

```text
TaiwanStockMarginPurchaseShortSale
```

已确认字段包括：

- `MarginPurchaseBuy`
- `MarginPurchaseSell`
- `MarginPurchaseTodayBalance`
- `MarginPurchaseYesterdayBalance`
- `ShortSaleBuy`
- `ShortSaleSell`
- `ShortSaleTodayBalance`
- `ShortSaleYesterdayBalance`
- `OffsetLoanAndShort`
- `date`
- `stock_id`

可形成的候选归档字段：

- 融资余额变化
- 融券余额变化
- 融资快速增加
- 融券回补
- 融资拥挤风险 proxy
- 融资/融券方向与价格趋势是否背离

价值：

- 更适合做风险过滤，而不是直接增强买入；
- 辅助识别追高风险、杠杆拥挤、轧空或筹码不稳定；
- 为“排名高但需要谨慎观察”提供解释。

## 3. 为什么月营收暂缓

FinMind 月营收数据集：

```text
TaiwanStockMonthRevenue
```

虽然能返回：

- `revenue`
- `revenue_year`
- `revenue_month`
- `date`
- `create_time`

但当前响应缺少明确的历史公告日字段，例如：

- `announcement_date`
- `announce_date`
- `disclosure_date`
- `published_date`

因此本小主线不得把月营收纳入 PIT archive。

禁止：

- 把 `date` 自动当作公告日；
- 把 `create_time` 当作历史可见时间；
- 用 `revenue_year + revenue_month` 直接 join 到当月交易日；
- 为了进入模型放宽 PIT 规则。

月营收后续应另走 MOPS / TWSE / TPEx 公告日来源验证。

## 4. 架构定位：不先改 qlib / LTR，先做外层风险确认

当前项目建议保持三层结构：

```text
第一层：qlib baseline
  输出 qlib score / qlib rank / Top50 主候选池。

第二层：LTR rerank
  输入 qlib score/rank + 技术/市场特征，输出 LTR 重排序与只读解释。

第三层：Risk Confirmation / Decision Filter
  输入 qlib rank、LTR rank、技术状态、法人筹码、融资融券、市场状态、持仓状态，输出研究标签。
```

本主线新增数据优先进入第三层。

禁止在本主线早期直接做：

- qlib v2 重训；
- LTR v2 重训；
- 用法人/融资融券直接替换 qlib 或 LTR 排名；
- 把风险过滤输出包装成买入/卖出/持有建议；
- 改默认主策略。

允许的外层输出语义是：

```text
confirmed_watch：排名与资金/筹码确认，优先研究。
normal_watch：正常观察。
caution_watch：排名高但存在风险，谨慎复盘。
defer_watch：暂缓新增观察。
review_existing：若已在模拟持仓中，进入风险复盘。
no_action_reason：解释为什么不替换或不新增观察。
```

这些是研究标签，不是交易指令。

## 5. 用户第一性原则

本主线必须符合：

- 简单：只先解决数据是否可信，不做复杂模型。
- 准确：每一行都必须有明确可见时间规则，避免未来函数。
- 清晰：区分原始数据、PIT 归档、派生特征、模型输入。
- 实用：若数据无法形成稳定 PIT 归档，就停止，不强行产品化。

本小主线仍为 research-only：

- 不生成买卖建议；
- 不输出目标仓位；
- 不接 broker；
- 不触发 quick-trade / orders；
- 不改 accepted latest；
- 不发布 qlib provider；
- 不进入前端主推荐。

## 6. 核心 PIT 规则

法人筹码和融资融券都是日频盘后统计数据。

第一版采用保守规则：

```text
available_at = next_trading_day(trade_date)
```

含义：

- `trade_date` 是 FinMind 返回的 `date`。
- 当日盘后才可见，不允许用于同日收盘前决策。
- 在历史样本中，只允许在 `available_at` 及之后的交易日使用。

每行至少保留：

- `symbol`
- `stock_id`
- `trade_date`
- `available_at`
- `source_dataset`
- `raw_snapshot_id`
- `fetched_at`
- `raw_payload_hash`
- 原始数值字段
- 归一化字段
- `quality_flags`

## 7. 归档表设计

### 7.1 raw archive

保存 FinMind 原始响应，不做业务解释。

建议路径：

```text
data_tw/experiments/decision_orthogonal_pit_archive/raw/
```

建议文件：

```text
institutional_flow_raw_YYYYMMDDTHHMMSSZ.jsonl
margin_short_raw_YYYYMMDDTHHMMSSZ.jsonl
```

每条记录包含：

- 请求参数
- HTTP / FinMind status
- symbol
- stock_id
- start_date
- end_date
- fetched_at
- rows
- raw_snapshot_id

不得写入 token。

### 7.2 normalized PIT archive

保存已做 PIT 对齐的行级归档。

建议路径：

```text
data_tw/experiments/decision_orthogonal_pit_archive/normalized/
```

建议文件：

```text
institutional_flow_pit.csv
margin_short_pit.csv
```

法人筹码 normalized 字段：

- `symbol`
- `stock_id`
- `trade_date`
- `available_at`
- `foreign_net_buy`
- `investment_trust_net_buy`
- `dealer_net_buy`
- `institutional_net_buy`
- `raw_names_seen`
- `quality_flags`
- `raw_snapshot_id`
- `data_source`

融资融券 normalized 字段：

- `symbol`
- `stock_id`
- `trade_date`
- `available_at`
- `margin_purchase_buy`
- `margin_purchase_sell`
- `margin_purchase_today_balance`
- `margin_purchase_yesterday_balance`
- `margin_purchase_balance_delta`
- `short_sale_buy`
- `short_sale_sell`
- `short_sale_today_balance`
- `short_sale_yesterday_balance`
- `short_sale_balance_delta`
- `offset_loan_and_short`
- `quality_flags`
- `raw_snapshot_id`
- `data_source`

### 7.3 coverage / status / PIT validation

必须生成：

```text
download_status.csv
coverage_report.csv
pit_validation_samples.csv
quality_flags_summary.csv
archive_manifest.csv
```

覆盖报告至少包含：

- symbol 数量
- 请求成功数
- 请求失败数
- row_count
- date_min / date_max
- 缺失交易日数量
- available_at 缺失数量
- quality flag 分布
- 402 / rate limit / empty rows 统计

## 8. 阶段切分

### Phase IM0：只读方案与脚本盘点

目标：

- 盘点已有 FinMind 法人/融资融券相关脚本；
- 确认哪些脚本会联网、哪些会写 provider、哪些只写实验目录；
- 冻结 PIT schema；
- 冻结 symbol universe 与日期范围。

默认建议范围：

```text
symbols: qlib Top150 / tw_liquid_dyn Top150
date range: 2022-01-01 ~ latest local trading date
```

Phase IM0 不允许：

- 联网下载；
- 写生产数据库；
- materialize qlib；
- 构建模型样本；
- 单因子检验；
- 前端/API。

产物：

- `PHASE_IM0_EXECUTION_REPORT_CN.md`
- `PHASE_IM0_REVIEW_AND_IM1_WORK_CN.md`

Gate：

```text
request_phase_im1_limited_archive_backfill
```

或：

```text
stop_institutional_margin_pit_archive_scope_invalid
```

### Phase IM1：小范围 PIT archive 回填

目标：

- 只对小范围 symbol 和短窗口联网回填；
- 验证 raw archive、normalized PIT archive、coverage、quality flags；
- 验证 token、402、空响应和字段稳定性。

建议范围：

```text
symbols: TW2330,TW2317,TW2454,TW2308,TW2357,TW6290
date range: 2026-05-01 ~ 2026-06-12
```

允许：

- 使用现有 FinMind token；
- 联网只读调用 FinMind；
- 写入隔离实验目录。

禁止：

- 写 provider；
- accepted latest switching；
- 构建模型样本；
- 训练模型；
- 改前端/API；
- 任何交易路径。

Gate：

```text
request_phase_im2_top150_archive_backfill
```

前提：

- 两个数据集请求成功率足够高；
- 每行都有 `available_at`；
- raw 与 normalized 可追溯；
- quality flags 可解释；
- 无 token 泄漏。

### Phase IM2：Top150 历史 PIT archive 回填

目标：

- 对 Top150 / liquid universe 回填 2022 至今；
- 评估额度、失败重试、覆盖率；
- 形成可复用 PIT archive。

允许：

- 分批联网；
- 遇到 402 时停止并报告；
- 写隔离实验目录。

禁止：

- 直接进入模型；
- materialize qlib；
- provider refresh/publish；
- 前端/API。

Gate：

```text
request_phase_im3_feature_quality_audit
```

或：

```text
stop_due_to_coverage_or_quota
```

### Phase IM3：派生特征与信息质量审计

目标：

- 从 PIT archive 派生只读候选特征；
- 做覆盖率、稳定性、相关性、滞后规则审计；
- 判断是否值得进入单因子 / TopK 增量检验。

允许派生：

- 法人 N 日净买超；
- 法人连续买超/卖超；
- 法人净买超占成交量比例；
- 融资余额变化；
- 融券余额变化；
- 融资拥挤 proxy；
- 融券回补 proxy。

禁止：

- 用未来价格参与特征；
- 用标签反向筛字段；
- 训练模型；
- 前端展示成推荐结论。

Gate：

```text
request_phase_im4_incremental_signal_test
```

或：

```text
stop_no_clean_incremental_features
```

### Phase IM4：增量信号检验

目标：

- 检验这些正交字段是否真的对 qlib TopN 有增量。

评估方式：

- qlib Top50 内分组；
- qlib Top150 扩展池分组；
- rank IC / ICIR；
- TopK future return / future rank；
- 分年份；
- 分市场状态；
- 与 qlib score/rank 相关性；
- 对 Phase1C rerank 的增量。

禁止：

- 只报告单一收益率；
- 只挑一个年份；
- 把弱信号包装成推荐；
- 直接接前端。

Gate：

```text
request_phase_im5_risk_confirmation_rule_design
```

或：

```text
archive_as_no_incremental_evidence
```

### Phase IM5：风险确认规则层设计

目标：

- 不训练模型，先设计可解释规则；
- 只在 qlib / LTR 候选上增加风险确认标签；
- 判断高排名结果是否被法人/融资融券确认或削弱。

规则候选：

- LTR Top30 且法人连续买超：`confirmed_watch`；
- LTR Top30 但法人连续卖超：`caution_watch`；
- LTR Top30 且融资余额快速上升：`caution_watch`；
- LTR Top30 且融资拥挤 + 技术高位：`defer_watch`；
- 已模拟持仓且法人撤退 + 技术转弱：`review_existing`；
- LTR turnover-controlled 不替换时，补充资金/融资理由作为 `no_action_reason`。

禁止：

- 输出买卖/持有/仓位建议；
- 把风险标签写成收益预测；
- 改 qlib/LTR 排名；
- 前端主推荐产品化。

Gate：

```text
request_phase_im6_risk_filter_backtest
```

或：

```text
archive_rules_as_explanation_only
```

### Phase IM6：风险过滤回测与样本外审查

目标：

- 验证 IM5 风险标签是否真的改善 qlib/LTR 候选的风险收益特征；
- 分 train / validation / independent_test 标注结果；
- 特别检查 2022 熊市、2025/2026 强势段和 rolling window。

评估方式：

- Top50 自适应 + 风险标签；
- LTR simple + 风险标签；
- LTR turnover-controlled + 风险标签；
- 只看标签分组，不直接改买卖动作；
- 若需要模拟动作，必须作为只读 replay，且和原策略同口径比较。

Gate：

```text
request_phase_im7_optional_decision_filter_design
```

或：

```text
keep_as_manual_review_explanation_only
```

### Phase IM7：可选 Decision Filter 产品设计

目标：

- 只在 IM6 证明有稳定增量后执行；
- 设计是否把风险确认标签接入前端；
- 保持 qlib / LTR 排名为主，风险过滤为辅助；
- 用户看到的是“风险确认标签”和“为什么谨慎/暂缓”，不是买卖指令。

允许展示：

- 法人确认 / 法人撤退；
- 融资拥挤 / 融资平稳；
- 谨慎观察 / 暂缓观察 / 持仓复盘；
- 历史上该标签的回放表现。

禁止展示：

- 目标仓位；
- 预期收益；
- 胜率；
- 上涨概率；
- 自动买卖按钮。


## 9. 和当前 LTR 主线的关系

本主线不是替代 LTR，也不是替代 qlib。

当前排序链路保持：

```text
qlib baseline -> LTR rerank -> 可选组合/只读解释
```

法人筹码 + 融资融券的定位是外层风险确认：

- 如果 IM4 证明有增量，先进入 IM5/IM6 风险确认与过滤验证；
- 如果 IM6 证明能稳定改善风险/回撤/错误高排名，再考虑 IM7 前端只读标签；
- 如果没有增量，只用于人工复盘解释或归档；
- 不得在 IM0-IM6 阶段改 qlib/LTR 模型、默认排名或默认策略。

未来只有在风险确认层稳定有效后，才考虑 LTR v2 或 qlib v2。那应另开新主线。

## 10. 执行者提示词

```text
请按 docs/tw_decision_model_orthogonal/FINMIND_INSTITUTIONAL_MARGIN_PIT_ARCHIVE_MAINLINE_CN.md 执行 Phase IM0：只读方案与脚本盘点。只允许盘点现有脚本、冻结 PIT schema、确认 symbol/date 范围和安全边界，并明确后续数据第一站是 Risk Confirmation / Decision Filter 而非 qlib/LTR 重训；不得联网下载、不得写 provider、不得构建样本、不得训练模型、不得改前端/API、不得触碰交易路径。执行完提交中文报告，等待审查。
```

## 11. 审查者提示词

```text
请审查执行者的 Phase IM0 报告，依据 docs/tw_decision_model_orthogonal/FINMIND_INSTITUTIONAL_MARGIN_PIT_ARCHIVE_MAINLINE_CN.md 判断是否符合只读边界、PIT schema 是否足够、是否存在联网/provider/accepted latest/模型/前端/交易越界；若通过，请撰写 Phase IM1 小范围 PIT archive 回填工作文档；若不通过，请给出必须修复项并停止。后续审查必须持续确认新数据不直接进入 qlib/LTR 重训，而是先进入风险确认/决策过滤层。
```

