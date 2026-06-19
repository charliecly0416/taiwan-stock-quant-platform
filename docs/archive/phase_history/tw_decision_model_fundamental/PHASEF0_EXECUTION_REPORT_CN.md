# Phase F0 执行报告

- 生成时间：`2026-06-11T16:03:42+00:00`
- 当前阶段目标：本地只读审计台股基本面/月营收 PIT 可行性，设计 raw archive / normalized PIT schema。
- 执行范围：只读读取 docs、scripts、data_tw/experiments、data_tw/ops 中的本地证据；未读取或写入 provider，未构建样本。
- 禁止范围执行情况：未联网、未使用 token、未下载数据、未调用 FinMind API、未调用 Scrapling、未新增真实数据源抓取、未写真实 raw archive、未构建 Phase F1 样本、未做单因子检验、未做规则 baseline、未训练模型、未前端/API、未 monitor、未交易路径。

## 1. 修改文件

- 新增 `scripts/audit_tw_decision_fundamental_phasef0.py`

## 2. 生成文件

- `data_tw/experiments/decision_fundamental/phasef0_data_source_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0_pit_schema_proposal.json`
- `data_tw/experiments/decision_fundamental/phasef0_feasibility_summary.json`
- `docs/tw_decision_model_fundamental/PHASEF0_EXECUTION_REPORT_CN.md`

## 3. 本地 Inventory 摘要

| candidate_source | dataset_or_table | has_announcement_date | has_available_at | pit_join_safe | phasef0_status | notes |
|---|---|---|---|---|---|---|
| FinMind | TaiwanStockMonthRevenue | false | false | false | defer_missing_announcement_date | May be a future F0B candidate only after authorized network/token POC verifies dataset fields and immutable raw snapshots. |
| FinMind local daily auto update logs | monthly_revenue summary | false | false | false | defer_no_local_evidence | Useful negative evidence only; no local monthly revenue rows available for PIT validation. |
| Legacy decision_model Phase0 audit | FinMind monthly_revenue_yoy_mom | false | false | false | defer_no_local_evidence | Confirms previous local conclusion: no archived rows and no announcement_date/available_at proof. |
| Legacy decision_model PIT rules | financial/monthly revenue data | false | false | false | defer_period_only | Policy evidence, not data source evidence. |
| Orthogonal Phase0E raw archive script | monthly_revenue placeholder | false | false | false | defer_no_local_evidence | No reusable monthly revenue implementation in this script. |
| Potential official disclosure source | MOPS/TWSE monthly revenue disclosure page or API | false | false | false | defer_no_local_evidence | Would require separate user/reviewer authorization as a new F0B data-source POC. |
| FinMind valuation | TaiwanStockPER | false | false | false | out_of_scope | Do not include in F0B unless reviewer explicitly expands beyond monthly revenue. |

## 4. 每个候选源的 PIT 判断

- FinMind `TaiwanStockMonthRevenue`：本地文档说明曾有月营收脚本和 smoke 记录，但当前 Phase F0 只读证据没有 row-level `announcement_date` / `available_at`，不能进入 F1。
- daily auto update logs：最新检查到 `--no-monthly-revenue`，stdout summary 中 `monthly_revenue.count=0`，只能作为负面证据。
- legacy decision_model Phase0：`monthly_revenue_yoy_mom` coverage 为 0，且 `point_in_time_safe=false`。
- prior PIT policy：明确拒绝 period-only join，要求从 `available_at` 开始 forward fill 并保留 source metadata。
- orthogonal Phase0E script：月营收被标记为 `deferred_not_authorized`。
- potential official disclosure source：可能是可行方向，但当前没有本地证据，Phase F0 未授权联网验证。

## 5. 是否找到 announcement_date

未找到可用于月营收/基本面样本的本地 row-level `announcement_date` 证据。

## 6. 是否找到 available_at

未找到可用于月营收/基本面样本的本地 row-level `available_at` 证据。

## 7. Period-only Join 风险

存在明确风险。若只拿到 `source_period`、`revenue`、`yoy`、`mom`，不得把所属月份直接 join 到当月交易日；这会把事后披露的月营收提前到不可见日期。

## 8. Raw Archive Schema 草案摘要

- raw archive 必须先保存不可变快照：`symbol`、`source_period`、`announcement_date`、`available_at`、`revenue`、`yoy`、`mom`、`data_source`、`raw_snapshot_id`、`ingested_at`、`source_url_or_dataset`、`revision_flag`、`raw_payload_hash`。
- normalized PIT 只能使用同时具备 `announcement_date` 与 `available_at` 的行。
- join 规则：每个 symbol/asof 只选择 `available_at <= asof` 的最新 `source_period`。
- late revision 规则：修订值只能从其自身 `announcement_date` / `available_at` 之后可见，不能覆盖历史当时不可见样本。

## 9. F0B 授权需求

- F0B 是否需要联网：是。
- F0B 是否需要 token：是，若选择 FinMind。
- F0B 是否需要新增脚本：是，需要独立月营收 POC 脚本。
- F0B 是否需要写 raw archive：是，但只能写独立 `data_tw/experiments/decision_fundamental/phasef0b_*` raw archive，不得写 provider。

## 10. 覆盖率 / 缺失率

- candidate_source_count：`7`
- pit_valid_candidate_count：`0`
- 本地 PIT-valid 月营收行：`0`
- 本地月营收 row-level announcement_date 缺失率：无法逐行计算；当前可用本地行数为 0，PIT 可用性视为 0。

## 11. 安全边界检查

- network_used=false
- token_used=false
- downloaded_data=false
- raw_archive_written=false
- model_training=false
- provider_write=false
- accepted_latest_switching=false
- frontend_api=false
- trading_or_order=false

## 12. 推荐 Gate 与理由

- recommended_gate：`request_user_authorization_for_f0b_poc`
- gate_reason：本地只读证据未证明任何月营收/基本面源具备 row-level announcement_date/available_at；但 FinMind monthly revenue 与官方披露源存在作为 F0B 受限 POC 的候选，需要用户授权联网/token/新增脚本/写独立 raw archive 后才能验证。不能进入 F1。

注意：该 gate 只表示请求审查者/用户考虑授权 F0B POC；不得直接进入 F0B，更不得进入 F1。

## 13. 风险与待审查问题

- 若审查者认为 FinMind 月营收缺少公告日，则应停止 fundamental mainline 或改走官方披露源 proposal。
- 若 F0B 只验证到 period-only 字段，则必须 `stop_fundamental_mainline_no_pit_source`。
- F0B 需要明确范围、token 使用方式、raw archive 路径和禁止 provider/accepted latest/模型训练边界。
