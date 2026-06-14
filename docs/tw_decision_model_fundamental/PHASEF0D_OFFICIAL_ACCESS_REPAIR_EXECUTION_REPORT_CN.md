# Phase F0D Official Source Access Repair 执行报告

- 生成时间：`2026-06-11T16:53:07+00:00`
- 阶段目标：修复官方月营收来源访问方式，验证是否能取得有效表格、row-level 公告日期或严格可审计日期。
- 执行范围：仅官方/月营收访问修复；仍限制 F0B 10 个 symbol；不做全市场回填，不构建 F1 样本。
- 用户授权：已授权受限 Phase F0D Official Source Access Repair。
- 禁止范围执行情况：未接受 FinMind `date/create_time` 为公告日、未 period-only join、未全市场回填、未构建 F1 样本、未做单因子检验、未做规则 baseline、未训练模型、未写 provider、未 refresh/publish、未 accepted latest switching、未 materialize 到 qlib、未前端/API、未 monitor、未交易路径。

## 1. 修改文件

- 新增 `scripts/probe_tw_decision_fundamental_phasef0d_official_access_repair.py`

## 2. 生成文件

- `data_tw/experiments/decision_fundamental/phasef0d_official_access_raw.jsonl`
- `data_tw/experiments/decision_fundamental/phasef0d_official_access_field_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0d_gate_summary.json`
- `docs/tw_decision_model_fundamental/PHASEF0D_OFFICIAL_ACCESS_REPAIR_EXECUTION_REPORT_CN.md`

## 3. 官方源访问修复结论

- effective_official_source_found：`True`
- pit_valid_rows：`9`
- aligned_rows：`9`
- requested_symbols：`['6187', '2327', '3008', '3583', '2360', '2486', '3036', '2379', '1560', '3189']`
- covered_symbols：`['1560', '2327', '2360', '2379', '2486', '3008', '3036', '3189', '3583']`
- missing_symbols：`['6187']`
- discovered_source_periods：`['2026-04']`
- can_generate_available_at：`True`
- can_align_with_finmind_symbol_period：`True`

## 4. Field Inventory

| source_name | market_scope | http_status | json_ok | effective_table | row_count | matched_symbol_rows | pit_valid_rows | aligned_rows | blocked_or_error | notes |
|---|---|---:|---|---|---:|---:|---:|---:|---|---|
| TWSE OpenAPI monthly revenue listed | listed | 200 | true | true | 1078 | 9 | 9 | 9 | false | official row-level disclosure date candidate found |
| TPEx OpenAPI monthly revenue OTC candidate t187ap05_O | otc | 403 | false | false | 0 | 0 | 0 | 0 | true | blocked_or_no_effective_table |
| TPEx OpenAPI monthly revenue OTC candidate mopsfin_t187ap05_O | otc | 403 | false | false | 0 | 0 | 0 | 0 | true | blocked_or_no_effective_table |
| TPEx monthly revenue json candidate mr_result | otc | 403 | false | false | 0 | 0 | 0 | 0 | true | blocked_or_no_effective_table |
| MOPS monthly revenue landing page | all | 200 | false | false | 0 | 0 | 0 | 0 | false | no matched pit-valid rows |

## 5. PIT 判断

- TWSE OpenAPI `t187ap05_L` 可访问，返回 JSON 行级数据，字段包括 `出表日期`、`資料年月`、`公司代號`、`營業收入-當月營收`。
- `出表日期` 被记录为官方 row-level 日期候选，并转换为 `announcement_date/available_at`；这不是 FinMind `date/create_time` proxy。
- TWSE OpenAPI 月营收金额字段以仟元为原始单位；脚本同时保留 raw 仟元值并归一为 NTD 后与 F0B archive 做数值核查。
- 本次仅发现当前公开 `資料年月`，没有解决历史少量月份访问；TPEx/OTC 路径在当前环境仍不可访问或被阻挡。
- 因此 F0D 只能证明上市 TWSE 当前文件的部分 PIT 可用性，不能直接进入 F1。

## 6. 与 F0B 本地 archive 对齐

- 对齐只使用本地 `phasef0b_monthly_revenue_raw_archive.jsonl`，没有重新拉取 FinMind。
- 对齐键仅用于数值核查：`symbol + source_period`；没有用 FinMind 日期作为公告日。
- 对齐结果：`9` / `9` PIT-valid 官方行经单位归一后数值匹配本地 F0B archive。

## 7. F0D Gate

- recommended_gate：`phasef0d_needs_user_decision=true`
- gate_reason：TWSE official OpenAPI provides row-level disclosure date and aligned current rows for listed symbols, but F0B 10-symbol and historical smoke coverage are incomplete.

## 8. 安全边界

- f1_sample=false
- model_training=false
- provider_write=false
- accepted_latest_switching=false
- frontend_api=false
- trading_or_order=false
- monitor_writes=false
- target_position_or_weight=false
- 未输出买入/卖出建议、收益承诺或上涨概率承诺。

## 9. 风险与待审查问题

- TWSE 上市当前 OpenAPI 已修复一部分官方访问问题，但 F0B 10 个 symbol 中 `6187` 未覆盖，TPEx/OTC 官方路径仍被 Cloudflare/访问限制阻挡。
- 当前 OpenAPI 响应为当前公开資料年月，未验证历史月份官方 archive/download 路径。
- 是否允许后续只针对 TWSE 上市子集进入更小范围 PIT 样本，或继续寻找 TPEx/历史 archive，需要审查者另行决定。
- 本阶段不得自动进入 F1。
