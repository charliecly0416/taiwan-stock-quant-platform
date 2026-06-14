# Phase F0 审查结论与 Phase F0B 授权工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_decision_model_fundamental/PHASEF0_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/tw_decision_model_fundamental/PHASEF0_REVIEW_BASELINE_AND_NEXT_WORK_CN.md`
- `docs/tw_decision_model_fundamental/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_FUNDAMENTAL_PIT_NEW_MAINLINE_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE2D_CLOSURE_REVIEW_AND_STANDBY_WORK_CN.md`

审查产物：

- `scripts/audit_tw_decision_fundamental_phasef0.py`
- `data_tw/experiments/decision_fundamental/phasef0_data_source_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0_pit_schema_proposal.json`
- `data_tw/experiments/decision_fundamental/phasef0_feasibility_summary.json`
- `docs/tw_decision_model_fundamental/PHASEF0_EXECUTION_REPORT_CN.md`

## 1. 本步审核结论

Phase F0 主线范围通过，只读安全边界通过。

执行者没有偏离主线，也没有新增分支：

- 只做本地只读数据源可行性审计。
- 未联网。
- 未使用 token。
- 未下载数据。
- 未调用 FinMind API。
- 未调用 Scrapling。
- 未新增真实数据源抓取。
- 未写真实 raw archive。
- 未构建 Phase F1 样本。
- 未做单因子检验。
- 未做规则 baseline。
- 未训练模型。
- 未执行 Risk Filter Model。
- 未写 provider。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未前端/API。
- 未 monitor 写入。
- 未触碰交易路径。

Phase F0 结论接受：

- 本地 PIT-valid 月营收/基本面候选源数量：`0`
- `announcement_date` 本地 row-level 证据：未找到。
- `available_at` 本地 row-level 证据：未找到。
- 不允许进入 F1。
- 不允许训练模型。

Gate 结论：

- 接受 `recommended_gate=request_user_authorization_for_f0b_poc`

但该 gate 只表示“请求用户授权 F0B POC”，不是自动进入 F0B。

## 2. 主线一致性审查

通过项：

- Phase F0 没有延续旧正交规则搜索。
- 没有把法人/融资融券规则卡升级为基本面 gate。
- 没有把本地文档中出现过的 FinMind 月营收记录直接视为可用 PIT 数据。
- 明确区分了“本地无 PIT 证据”和“需要 F0B 联网 POC 验证”。
- 明确拒绝 period-only join。

未发现偏离主线或新增分支。

## 3. PIT 与数据审查

### 3.1 Inventory 审查

`phasef0_data_source_inventory.csv` 符合上一轮字段要求，候选项覆盖：

- FinMind `TaiwanStockMonthRevenue`
- local daily auto update logs
- legacy decision_model Phase0 audit
- legacy PIT policy
- orthogonal Phase0E script
- potential official disclosure source
- FinMind valuation

审查判断：

- inventory 能支持 Phase F0 结论。
- 当前所有月营收/基本面候选都没有本地 row-level `announcement_date` / `available_at` 证据。
- `FinMind valuation` 被标为 out_of_scope 是合理的，F0B 不应扩展到估值。

### 3.2 PIT schema 审查

`phasef0_pit_schema_proposal.json` 通过。

关键要求已覆盖：

- `symbol`
- `source_period`
- `announcement_date`
- `available_at`
- `revenue`
- `yoy`
- `mom`
- `data_source`
- `raw_snapshot_id`
- `ingested_at`
- `source_url_or_dataset`
- `revision_flag`
- `days_since_last_report`

可接受点：

- visibility rule 要求 `announcement_date` 和 `available_at` 同时存在。
- join rule 只允许 `available_at <= asof` 的最新 `source_period`。
- forbidden join rule 明确禁止按 `source_period` 所属月份直接 join。
- late revision rule 明确修订只能从自身可见时间之后使用。

### 3.3 Feasibility summary 审查

`phasef0_feasibility_summary.json` 通过。

关键字段：

- `network_used=false`
- `token_used=false`
- `downloaded_data=false`
- `raw_archive_written=false`
- `model_training=false`
- `provider_write=false`
- `accepted_latest_switching=false`
- `frontend_api=false`
- `trading_or_order=false`
- `candidate_source_count=7`
- `pit_valid_candidate_count=0`
- `requires_f0b_user_authorization=true`
- `recommended_gate=request_user_authorization_for_f0b_poc`

审查判断：

- 因 `pit_valid_candidate_count=0`，不能进入 F1。
- 因存在 FinMind monthly revenue 与官方披露源候选，但本地无法验证字段，允许请求受限 F0B POC 授权。

## 4. 指标/样本/模型审查

Phase F0 没有构建样本、没有计算标签、没有做指标检验、没有训练模型。

通过。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无。

### Network Audit

未联网，未下载，未调用外部 API。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

报告没有输出买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 6. 必须修复项

当前 Phase F0 产物无必须修复项。

但 F0B 前必须明确：

- F0B 需要用户授权联网。
- F0B 需要用户授权使用 token。
- F0B 需要新增独立月营收 POC 脚本。
- F0B 需要写独立 raw archive。
- F0B 不得写 provider。
- F0B 不得 accepted latest switching。
- F0B 不得构建 F1 样本。
- F0B 不得训练模型。

## 7. 可暂缓项

继续暂缓：

- 财报/估值字段。
- 全市场回填。
- Phase F1 样本。
- 单因子检验。
- 规则 baseline。
- Risk Filter / Fundamental Confirm Model。
- 前端/API。
- provider/accepted latest。
- 任何交易路径。

## 8. 是否需要用户确认

需要用户确认后才能进入 F0B。

原因：

- F0B 需要联网。
- F0B 需要 token。
- F0B 需要新增月营收 POC 脚本。
- F0B 需要写独立 raw archive。

在用户确认前，执行者必须停止，不得执行 F0B。

## 9. 给用户的确认点

建议向用户确认：

是否授权执行者进入受限 Phase F0B POC，范围如下：

- 使用 FinMind token 和必要的官方披露源只读访问。
- 只拉取小范围月营收字段，不拉估值/财报。
- 时间范围：`2024-01-01` 至 `2026-06-11`。
- 股票范围：qlib Top50/Top150 历史涉及样本的去重 symbol，若本地提取复杂，则先选少量代表 symbol 做 smoke。
- 只写独立路径：`data_tw/experiments/decision_fundamental/phasef0b_*`。
- 只验证字段、覆盖率、PIT 可用性。
- 不写 provider。
- 不 materialize 到 qlib。
- 不切 accepted latest。
- 不构建 F1 样本。
- 不训练模型。
- 不接前端/API。
- 不触碰 monitor、alerts、broker、quick-trade、orders。

## 10. 给执行者的下一步工作文档：等待用户授权 / Phase F0B POC 草案

### 10.1 当前状态

Phase F0 已完成。

当前 gate：

- `request_user_authorization_for_f0b_poc=true`
- `phasef1_allowed=false`
- `model_training_allowed=false`
- `provider_write_allowed=false`
- `accepted_latest_switching_allowed=false`
- `frontend_api_allowed=false`
- `trading_or_order_allowed=false`

在用户授权前，执行者不得继续。

### 10.2 若用户未授权

执行者只能待命。

不得继续本地搜索扩展，也不得改写 F0 结论。

### 10.3 若用户授权 F0B

执行者可进入 Phase F0B，但只能按以下范围执行。

目标：

- 验证月营收候选源是否真正提供 row-level `announcement_date` 或等价 disclosure date。
- 验证能否生成可审计 `available_at`。
- 验证能否写入独立 immutable raw archive。
- 验证是否存在足够 PIT-valid rows 进入后续 F1 讨论。

输入：

- `docs/tw_decision_model_fundamental/PHASEF0_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/decision_fundamental/phasef0_data_source_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0_pit_schema_proposal.json`
- `data_tw/experiments/decision_fundamental/phasef0_feasibility_summary.json`
- 本文件

允许新增：

- `scripts/build_tw_decision_fundamental_phasef0b_monthly_revenue_poc.py`
- `docs/tw_decision_model_fundamental/PHASEF0B_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/decision_fundamental/phasef0b_monthly_revenue_raw_archive.*`
- `data_tw/experiments/decision_fundamental/phasef0b_monthly_revenue_normalized_pit.*`
- `data_tw/experiments/decision_fundamental/phasef0b_pit_validation_samples.csv`
- `data_tw/experiments/decision_fundamental/phasef0b_coverage_summary.json`
- `data_tw/experiments/decision_fundamental/phasef0b_gate_summary.json`

### 10.4 F0B 范围限制

数据范围：

- 数据类型：只允许月营收。
- 优先候选：FinMind `TaiwanStockMonthRevenue`。
- 若 FinMind 没有公告日字段，可只做官方披露源字段探测，不得扩大到估值/财报。
- 时间范围：`2024-01-01` 至 `2026-06-11`。
- 股票范围：优先 qlib Top50/Top150 历史涉及样本；若实现复杂，先做少量代表 symbol smoke，并在报告中说明。

写入范围：

- 只能写 `data_tw/experiments/decision_fundamental/phasef0b_*`。
- raw archive 必须独立，不得写 provider。
- normalized PIT 必须独立，不得 materialize 到 qlib。

### 10.5 F0B 必须验证

必须输出：

- 是否存在 `announcement_date`。
- 是否存在可审计 `available_at`。
- `source_period` 是否保留。
- `raw_snapshot_id` 是否保留。
- `data_source` 是否保留。
- 是否能计算 `days_since_last_report`。
- 是否存在 period-only 风险。
- PIT-valid row count。
- symbol coverage。
- month coverage。
- missing announcement_date count。
- missing available_at count。
- 被排除原因分布。

### 10.6 F0B Gate

F0B 完成后推荐 gate 只能是：

- `request_phasef1_pit_sample_work=true`
- `stop_fundamental_mainline_no_pit_source=true`
- `phasef0b_needs_source_redesign=true`

允许进入 F1 的最低条件：

- 存在 row-level `announcement_date` 或可审计等价披露日期。
- 存在可审计 `available_at`。
- raw archive 与 normalized PIT 均保留 `source_period`、`raw_snapshot_id`、`data_source`。
- PIT-valid rows 足以做小范围 F1 单因子检验。
- 没有 period-only join。

### 10.7 F0B 禁止事项

F0B 禁止：

- 拉估值/财报。
- 全市场回填。
- 构建 F1 样本。
- 做单因子检验。
- 做规则 baseline。
- 训练模型。
- 执行 Risk Filter Model。
- 写 provider。
- provider refresh/publish。
- accepted latest switching。
- materialize 到 qlib。
- 前端/API 接入。
- monitor config save。
- monitor scan。
- alerts write。
- broker、quick-trade、orders。
- target position 或 target weight。
- 输出买入/卖出建议。
- 输出收益承诺或上涨概率承诺。

完成后等待审查者审核，不得自动进入 F1。
