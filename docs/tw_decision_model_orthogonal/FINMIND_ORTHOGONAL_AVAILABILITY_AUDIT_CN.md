# FinMind 正交数据小范围可得性审计报告

- 生成时间：`2026-06-13T17:29:19+00:00`
- 审计范围：symbols `TW2330,TW2317,TW2454,TW2308,TW2357,TW6290`，日期 `2026-05-01` 至 `2026-06-12`。
- token_used：`True`
- 执行边界：只读 FinMind API 探测；未构建样本、未训练模型、未写 provider、未 refresh/publish、未 accepted latest switching、未改前端/API、未触碰交易路径。

## 1. 产物

- raw archive：`data_tw/experiments/finmind_orthogonal_availability_audit/finmind_orthogonal_availability_raw_20260613T172919Z.jsonl`
- summary：`data_tw/experiments/finmind_orthogonal_availability_audit/finmind_orthogonal_availability_summary_20260613T172919Z.csv`
- fields：`data_tw/experiments/finmind_orthogonal_availability_audit/finmind_orthogonal_availability_fields_20260613T172919Z.csv`

## 2. 数据集可得性概览

| 数据集 | 成功请求 | 失败请求 | 总行数 | 覆盖 symbol | 日期/期间范围 | 主要字段 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `institutional_flow` | 6 | 0 | 900 | 6/6 | 2026-05-04 ~ 2026-06-12 | `buy, date, name, sell, stock_id` |
| `margin_short` | 6 | 0 | 180 | 6/6 | 2026-05-04 ~ 2026-06-12 | `MarginPurchaseBuy, MarginPurchaseCashRepayment, MarginPurchaseLimit, MarginPurchaseSell, MarginPurchaseTodayBalance, MarginPurchaseYesterdayBalance, Note, OffsetLoanAndShort, ShortSaleBuy, ShortSaleCashRepayment, ShortSaleLimit, ShortSaleSell` |
| `monthly_revenue` | 6 | 0 | 12 | 6/6 | 2026-04 ~ 2026-05 | `country, create_time, date, revenue, revenue_month, revenue_year, stock_id` |

## 3. 初步判断

- 法人筹码和融资融券属于日频盘后数据，若后续进入模型，应采用保守 T+1 可见规则，并按交易日对齐。
- 月营收可以拿到数值和营收年月，但 FinMind 响应通常不提供明确公告日；不能直接把 `date` 或 `create_time` 当作历史公告日。
- 这次审计只证明“能否拿到数据与字段形态”，不证明这些字段已经 PIT-safe，也不证明能提升策略。
- 若后续要进入 Decision Model，下一步应先做 PIT archive 设计：每行必须有 `source_period`、`available_at`、`days_since_last_report`、`raw_snapshot_id`。

## 4. 风险

- 若未来扩大到 Top150 或多年历史，普通 token 可能遇到 402 额度限制。
- 月营收需要官方 MOPS/TWSE/TPEx 公告日来源辅助，否则只能用于人工解释或继续暂缓。
- 不建议直接把这些字段接进前端推荐；应先做覆盖率、IC、TopK、策略回放和泄漏审计。