# Phase F0C Source Redesign 执行报告

- 生成时间：`2026-06-11T16:34:23+00:00`
- 阶段目标：探测官方或可审计月营收公告日期来源，判断是否存在 row-level `announcement_date`。
- 执行范围：MOPS 月营收官方页面少量月份与 F0B 10 个 symbol smoke；只写 `phasef0c_*` 产物。
- 禁止范围执行情况：未接受 FinMind `date/create_time` 为公告日、未 period-only join、未全市场回填、未构建 F1 样本、未做单因子检验、未做规则 baseline、未训练模型、未写 provider、未 refresh/publish、未 accepted latest switching、未 materialize 到 qlib、未前端/API、未 monitor、未交易路径。

## 1. 修改文件

- 新增 `scripts/probe_tw_decision_fundamental_phasef0c_official_disclosure.py`

## 2. 生成文件

- `data_tw/experiments/decision_fundamental/phasef0c_official_disclosure_probe_raw.jsonl`
- `data_tw/experiments/decision_fundamental/phasef0c_official_disclosure_field_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0c_source_redesign_summary.json`
- `docs/tw_decision_model_fundamental/PHASEF0C_SOURCE_REDESIGN_EXECUTION_REPORT_CN.md`

## 3. 官方源探测结论

- official_source_exists：`False`
- probed_pages：`6`
- successful_pages：`6`
- response_tables_found：`0`
- security_blocked_pages：`6`
- row_level_announcement_date_found：`False`
- page_level_date_candidates：`[]`
- matched_symbol_rows：`0`

## 4. 字段 Inventory 摘要

| source_period | market_type | http_status | security_blocked | table_found | row_count | matched_symbol_rows | has_row_level_announcement_column | page_date_candidates | columns |
|---|---|---:|---|---|---:|---:|---|---|---|
| 2024-01 | sii | 200 | true | false | 0 | 0 | false |  |  |
| 2024-01 | otc | 200 | true | false | 0 | 0 | false |  |  |
| 2025-01 | sii | 200 | true | false | 0 | 0 | false |  |  |
| 2025-01 | otc | 200 | true | false | 0 | 0 | false |  |  |
| 2026-05 | sii | 200 | true | false | 0 | 0 | false |  |  |
| 2026-05 | otc | 200 | true | false | 0 | 0 | false |  |  |

## 5. PIT 判断

- MOPS `ajax_t21sc03` 是本阶段按审查文档尝试的官方候选入口，但本环境返回安全拦截页，未验证到有效官方表格。
- 当前探测没有发现 row-level `announcement_date` / `disclosure_date` 字段，也没有发现可用表格列。
- 页面层级日期候选若存在，也不能证明每个 `symbol + source_period` 的 row-level 公告日期。
- 因此当前不能生成可审计 `available_at`，不能进入 F1。

## 6. 与 FinMind 对齐判断

- 本次 MOPS 响应被安全拦截，未取得可用于与 FinMind 对齐的官方表格。
- 即使后续取得数值表格，仍必须证明 row-level 公告日期或严格可审计的 `available_at`，否则不足以满足 PIT 样本要求。

## 7. F0C Gate

- recommended_gate：`phasef0c_needs_user_decision=true`
- gate_reason：MOPS official candidate endpoint returned security-blocked pages in this environment; no effective official table or row-level announcement date was validated.

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

- 本环境 MOPS 官方候选端点返回安全拦截页，当前只能证明该请求路径未取得有效表格，不能证明官方源不存在。
- 如果审查者认为应尝试其他官方下载路径、手动归档、浏览器态请求或 TWSE/TPEx 公开档案，需要另开后续阶段；本阶段没有扩展分支。
- 若必须 row-level announcement_date，当前探测不足以支持 fundamental 主线进入 F1。
- 后续不能通过放宽 PIT 规则或接受 FinMind date proxy 来绕过该结论。