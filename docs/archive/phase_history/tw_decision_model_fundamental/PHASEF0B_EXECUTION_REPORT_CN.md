# Phase F0B Monthly Revenue POC 执行报告

- 生成时间：`2026-06-11T16:15:37+00:00`
- 阶段目标：受限验证月营收候选源是否提供 row-level `announcement_date` 或等价披露日期，并验证能否形成独立 raw archive / normalized PIT。
- 执行范围：FinMind `TaiwanStockMonthRevenue` 小范围 POC，时间 `2024-01-01` 至 `2026-06-11`，symbols `6187,2327,3008,3583,2360,2486,3036,2379,1560,3189`。
- 禁止范围执行情况：未拉估值/财报、未全市场回填、未构建 F1 样本、未做单因子检验、未做规则 baseline、未训练模型、未写 provider、未 refresh/publish、未 accepted latest switching、未 materialize 到 qlib、未前端/API、未 monitor、未交易路径。

## 1. 修改文件

- 新增 `scripts/build_tw_decision_fundamental_phasef0b_monthly_revenue_poc.py`

## 2. 生成文件

- `data_tw/experiments/decision_fundamental/phasef0b_monthly_revenue_raw_archive.jsonl`
- `data_tw/experiments/decision_fundamental/phasef0b_monthly_revenue_normalized_pit.csv`
- `data_tw/experiments/decision_fundamental/phasef0b_pit_validation_samples.csv`
- `data_tw/experiments/decision_fundamental/phasef0b_coverage_summary.json`
- `data_tw/experiments/decision_fundamental/phasef0b_gate_summary.json`
- `docs/tw_decision_model_fundamental/PHASEF0B_EXECUTION_REPORT_CN.md`

## 3. 数据来源

- 数据源：FinMind `TaiwanStockMonthRevenue`。
- token_used：`True`。
- network_used=true。
- raw archive 独立写入 `data_tw/experiments/decision_fundamental/phasef0b_*`，未写 provider。

## 4. 字段探测结果

- FinMind 响应字段合集：`['country', 'create_time', 'date', 'revenue', 'revenue_month', 'revenue_year', 'stock_id']`。
- explicit announcement field found：`False`。
- provider date candidate field found：`True`。
- 说明：`date` / `report_date` 仅记录为 provider candidate，未直接等同官方公告日；若没有明确公告/披露字段，strict PIT-valid rows 保持 0。

## 5. PIT 处理

- strict PIT 规则：只有明确 `announcement_date` / 等价公告字段存在时，才生成 normalized PIT 行。
- `available_at` POC 规则：`announcement_date + 1 calendar day`；该规则仍需后续审查，当前不进入 F1。
- period-only join：未使用，且明确禁止。
- raw rows 全量保留 `source_period`、`raw_snapshot_id`、`data_source`、`raw_payload_hash`。

## 6. 覆盖率 / 缺失率

- request_count：`10`
- success_count：`10`
- raw_row_count：`300`
- normalized_pit_row_count：`0`
- symbol_count_with_raw_rows：`10`
- source_period_count：`30`
- missing_announcement_date_count：`300`
- missing_available_at_count：`300`
- excluded_reason_counts：`{'missing_explicit_announcement_date': 300}`

## 7. F0B Gate

- recommended_gate：`phasef0b_needs_source_redesign=true`
- gate_reason：FinMind returned monthly revenue rows and a provider date candidate, but no explicit announcement/disclosure field was found; strict PIT-valid rows remain 0.

## 8. 安全边界

- model_training=false
- provider_write=false
- accepted_latest_switching=false
- frontend_api=false
- trading_or_order=false
- monitor_writes=false
- target_position_or_weight=false
- 未输出买入/卖出建议、收益承诺或上涨概率承诺。

## 9. 风险与待审查问题

- 若审查者不接受 FinMind `date` 作为公告/披露日期，则本次 POC 不具备进入 F1 的 PIT 证据。
- 若需要官方 MOPS/TWSE disclosure date，建议下一步走 source redesign，而不是用 provider `date` proxy。
- 当前没有生成 F1 样本，也没有计算任何收益标签或因子效果。
