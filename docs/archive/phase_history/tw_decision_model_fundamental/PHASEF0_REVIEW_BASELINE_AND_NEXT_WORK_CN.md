# Phase F0 Baseline 审查结论与 Phase F0 工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_decision_model_fundamental/REVIEWER_PROMPT_CN.md`
- `docs/tw_decision_model_fundamental/PHASEF0_EXECUTOR_STANDBY_AND_PROPOSAL_CN.md`

关联依据：

- `docs/TW_STOCK_DECISION_FUNDAMENTAL_PIT_NEW_MAINLINE_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE2D_CLOSURE_REVIEW_AND_STANDBY_WORK_CN.md`
- `docs/tw_decision_model_fundamental/EXECUTOR_PROMPT_CN.md`

## 1. 本步审核结论

允许开启台股 Decision Model 基本面 PIT 新主线的 Phase F0。

当前只授权执行者做本地只读可行性审计与 PIT 方案设计。

不允许：

- 联网。
- 使用 token。
- 下载新数据。
- 新增真实数据源抓取。
- 写 raw archive 实际数据。
- 构建 Phase F1 样本。
- 训练模型。
- 执行 Risk Filter Model。
- materialize 到 qlib。
- 写 provider。
- provider refresh/publish。
- accepted latest switching。
- 前端/API 接入。
- monitor config save。
- monitor scan。
- alerts write。
- broker、quick-trade、orders。
- target position / target weight。
- 输出买入/卖出建议、收益承诺或上涨概率承诺。

执行者提交的 `PHASEF0_EXECUTOR_STANDBY_AND_PROPOSAL_CN.md` 没有擅自执行 F0，符合旧主线 closure 的待命要求。

## 2. 主线一致性审查

新主线与旧正交规则探索必须切开：

- 旧正交主线已经在 Phase2D 关闭。
- 不允许继续 Phase2E。
- 不允许把法人/融资融券规则卡升级为模型 gate。
- 不允许把本轮 Phase F0 变成旧规则补参。

Fundamental 新主线的第一目标是判断月营收/基本面数据是否具备可审计 PIT 方案，尤其是：

- `announcement_date`
- `available_at`
- `source_period`
- `raw_snapshot_id`
- `data_source`
- `days_since_last_report`

没有 PIT 证据，不得进入样本或模型。

## 3. 初步本地线索

审查者只做了最小只读搜索，发现仓库内已有以下待盘点线索，执行者需要在 Phase F0 中系统审计：

- 旧 `docs/tw_decision_model` 中多次记录 FinMind monthly revenue / valuation 因缺少 `available_at` 或 `announcement_date` 而暂缓。
- `scripts/build_tw_decision_orthogonal_phase0e_raw_archive.py` 中曾明确将 `monthly_revenue` 标记为未授权或 deferred。
- `docs/TAIWAN_STOCK_PHASE_CHECKPOINT_CN.md` 提到过 FinMind `TaiwanStockMonthRevenue` 与历史月营收归档脚本线索。
- 仓库中存在 FinMind 相关日频自动更新与 raw archive 产物，但这不等于基本面 PIT 可用。

这些只是审计线索，不是可用结论。执行者必须逐项查证，不能据此直接进入 F0B 或 F1。

## 4. PIT 与数据审查要求

Phase F0 必须回答：

1. 候选月营收/基本面数据源是否能提供真实公告日或等价可见时间。
2. FinMind `TaiwanStockMonthRevenue` 在本仓库已有文档或代码中是否包含公告日字段。
3. 若 FinMind 只有月份和营收值，是否存在官方公告日来源或可审计替代来源。
4. 若只能得到 `source_period`，必须判定为不可进入 F1。
5. 是否已有本地 raw archive 或数据库表保存月营收，但缺失 PIT 字段。
6. 是否已有脚本可复用为将来 F0B POC 的基础。
7. raw archive schema 如何保留每次拉取的不可变快照和 row-level PIT 字段。
8. 如何避免用所属月份直接 join 到交易日。
9. 如何计算 `days_since_last_report`。
10. 如果需要新增脚本、联网或 token，必须作为 F0 结论提出，不得在 F0 执行。

Phase F0 只设计 schema，不写真实 raw archive 数据。

## 5. 指标/样本/模型审查

Phase F0 不涉及指标、样本或模型。

禁止：

- 构建 date-symbol 样本。
- 计算未来收益标签。
- 做单因子检验。
- 做规则 baseline。
- 训练任何模型。
- 生成 watch、confirmed、caution 等研究状态。

## 6. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无。

### Network Audit

本轮审查未授权执行者联网。Phase F0 也不允许执行者联网。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 行为。

### Text / Agent Semantics

本轮文档仅定义 research-only 可行性审计，不包含买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 7. 必须修复项

当前没有执行产物需要修复。

Phase F0 必须补齐以下审计：

- 月营收/基本面相关脚本、文档、表、数据目录的本地 inventory。
- 每个候选数据源的 PIT 字段可用性判断。
- `announcement_date` / `available_at` 是否真实存在的证据。
- 若没有公告日，明确停止或提出需要用户授权的新数据源 POC。
- raw archive schema 草案。
- F0B 是否需要联网/token/新增脚本/写 raw archive 的授权清单。

## 8. 可暂缓项

Phase F0 暂缓：

- 真实数据下载。
- token 使用。
- Scrapling 或 FinMind API 实测。
- raw archive 真实写入。
- Phase F1 样本。
- 单因子检验。
- 规则 baseline。
- 模型训练。
- 前端/API。
- provider/accepted latest。
- 任何交易路径。

## 9. 是否需要用户确认

当前不需要用户确认。

理由：

- 用户已明确开启 fundamental 新主线。
- Phase F0 只做本地只读审计和方案设计。
- 不涉及联网、token、下载、写 raw archive、训练、前端/API 或交易语义。

但 Phase F0 完成后，如果执行者认为需要联网、token、新增数据源、新增月营收脚本或写 raw archive，必须先提交报告，由审查者判断是否需要用户确认。

## 10. 给执行者的下一步工作文档：Phase F0

### 10.1 目标

完成台股基本面/月营收 PIT 新主线的本地只读可行性审计。

核心问题：

- 是否存在可审计的月营收/基本面 PIT 数据方案。
- 是否能拿到 `announcement_date` 或等价 `available_at`。
- 若可行，F0B POC 需要用户授权哪些动作。
- 若不可行，新主线应停止，不能进入 F0B/F1。

### 10.2 输入

必须读取：

- `docs/TW_STOCK_DECISION_FUNDAMENTAL_PIT_NEW_MAINLINE_PLAN_CN.md`
- `docs/tw_decision_model_fundamental/REVIEWER_PROMPT_CN.md`
- `docs/tw_decision_model_fundamental/EXECUTOR_PROMPT_CN.md`
- `docs/tw_decision_model_fundamental/PHASEF0_REVIEW_BASELINE_AND_NEXT_WORK_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE2D_CLOSURE_REVIEW_AND_STANDBY_WORK_CN.md`

允许只读盘点：

- `docs/`
- `scripts/`
- `backend_api_python/`
- `crawler_handoff_tw_full_market/`
- `examples/`
- `qlib/`
- `data_tw/experiments/`
- `data_tw/ops/`

### 10.3 允许产物

必须新增：

- `docs/tw_decision_model_fundamental/PHASEF0_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/decision_fundamental/phasef0_data_source_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0_pit_schema_proposal.json`
- `data_tw/experiments/decision_fundamental/phasef0_feasibility_summary.json`

如确有必要，可新增只读审计脚本：

- `scripts/audit_tw_decision_fundamental_phasef0.py`

脚本只能读本地文件和本地目录，只能写 Phase F0 专用 inventory / proposal / summary / report。

### 10.4 Inventory 要求

`phasef0_data_source_inventory.csv` 至少包含：

- `candidate_source`
- `dataset_or_table`
- `local_evidence_path`
- `source_type`
- `has_symbol`
- `has_source_period`
- `has_announcement_date`
- `has_available_at`
- `has_revenue`
- `has_yoy`
- `has_mom`
- `has_raw_snapshot_id`
- `has_data_source`
- `pit_join_safe`
- `known_risk`
- `phasef0_status`
- `notes`

`phasef0_status` 只能使用：

- `candidate_for_f0b_poc`
- `defer_missing_announcement_date`
- `defer_missing_available_at`
- `defer_period_only`
- `defer_no_local_evidence`
- `rejected_future_leakage_risk`
- `out_of_scope`

### 10.5 PIT schema proposal 要求

`phasef0_pit_schema_proposal.json` 必须包含：

- `raw_archive_schema`
- `normalized_pit_schema`
- `visibility_rule`
- `join_rule`
- `forbidden_join_rule`
- `snapshot_rule`
- `dedup_rule`
- `late_revision_rule`
- `days_since_last_report_rule`
- `f0b_required_authorizations`

schema 必须至少覆盖字段：

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

### 10.6 Feasibility summary 要求

`phasef0_feasibility_summary.json` 必须包含：

- `phase`
- `generated_at`
- `network_used=false`
- `token_used=false`
- `downloaded_data=false`
- `raw_archive_written=false`
- `model_training=false`
- `provider_write=false`
- `accepted_latest_switching=false`
- `frontend_api=false`
- `trading_or_order=false`
- `candidate_source_count`
- `pit_valid_candidate_count`
- `requires_f0b_user_authorization`
- `recommended_gate`
- `gate_reason`
- `open_questions`

`recommended_gate` 只能使用：

- `request_user_authorization_for_f0b_poc`
- `stop_fundamental_mainline_no_pit_source`
- `phasef0b_not_ready_need_more_local_audit`

### 10.7 Phase F0 执行报告必须回答

报告必须包含：

1. 当前阶段目标。
2. 执行范围。
3. 修改文件。
4. 生成文件。
5. 本地 inventory 摘要。
6. 每个候选源的 PIT 判断。
7. 是否找到 `announcement_date`。
8. 是否找到 `available_at`。
9. 是否存在 period-only join 风险。
10. raw archive schema 草案摘要。
11. F0B 是否需要联网。
12. F0B 是否需要 token。
13. F0B 是否需要新增脚本。
14. F0B 是否需要写 raw archive。
15. 安全边界检查。
16. 推荐 gate 与理由。
17. 风险与待审查问题。

### 10.8 禁止事项

Phase F0 禁止：

- 联网。
- 使用 token。
- 下载数据。
- 调用 FinMind API。
- 调用 Scrapling。
- 新增真实数据源抓取。
- 写真实 raw archive。
- 读取或写入 provider。
- provider refresh/publish。
- accepted latest switching。
- 构建 Phase F1 样本。
- 做单因子检验。
- 做规则 baseline。
- 训练模型。
- 执行 Risk Filter Model。
- 前端/API 接入。
- monitor config save。
- monitor scan。
- alerts write。
- broker、quick-trade、orders。
- target position 或 target weight。
- 输出买入/卖出建议。
- 输出收益承诺或上涨概率承诺。

### 10.9 Gate

Phase F0 完成后：

- 如果找到可行 PIT 方案，执行者只能请求 `request_user_authorization_for_f0b_poc=true`，不得直接进入 F0B。
- 如果没有公告日或 available_at 方案，必须建议 `stop_fundamental_mainline_no_pit_source=true`。
- 如果本地证据不足但仍可继续查本地文件，建议 `phasef0b_not_ready_need_more_local_audit=true`。

完成后等待审查者审核，不得自动进入 F0B。
