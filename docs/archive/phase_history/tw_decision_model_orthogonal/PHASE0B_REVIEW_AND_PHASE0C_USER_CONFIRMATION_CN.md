# 正交数据 Decision Model Phase 0B 审查结论与 Phase 0C 用户确认事项

审查日期：2026-06-10

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE0B_EXECUTION_REPORT_CN.md`

审查依据：

- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE0B_USER_APPROVED_READONLY_WORK_CN.md`

审查产物：

- `scripts/audit_tw_decision_orthogonal_phase0b.py`
- `data_tw/experiments/decision_orthogonal/phase0b_script_inventory.csv`
- `data_tw/experiments/decision_orthogonal/phase0b_pit_schema_proposal.md`
- `docs/tw_decision_model_orthogonal/PHASE0B_DATA_BACKFILL_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE0B_EXECUTION_REPORT_CN.md`

## 1. 本步审核结论

Phase 0B 执行范围通过。执行者没有偏离主线，也没有新增未授权分支。

Phase 0B 的实际工作限定在只读脚本盘点、PIT schema 设计和未来补齐方案草案，没有联网、没有下载、没有 materialize、没有 provider refresh/publish、没有 accepted latest switching、没有 Phase 1 样本、没有单因子检验、没有模型训练，也没有前端/API 或交易路径。

Phase 0B 的结论为：

- `request_user_approval_for_data_backfill=true`
- Phase 1：不允许进入

审查者同意该结论。

## 2. 主线一致性审查

通过项：

- 仍处于正交数据主线，没有回到 Entry Model v1 或 Phase 2D。
- 只盘点计划内法人筹码、融资融券、月营收相关能力。
- 9 个指定脚本全部存在并完成静态盘点。
- 所有被盘点脚本均标记为 `safe_to_run_in_phase0b=False`，符合只读设计边界。
- 未发现月营收脚本，报告如实列为 `_no rows_`。
- 没有将“有脚本”包装成“有可用 PIT 数据”。
- 没有建议进入 Phase 1。

未发现项：

- 未发现新增计划外模型分支。
- 未发现下载或 materialize 实际执行。
- 未发现 Qlib bin/provider 写入。
- 未发现前端/API 产品化。
- 未发现单因子筛选或模型训练。

## 3. 数据与 PIT 审查

Phase 0B 只完成 schema 方案，不产生可进入 Phase 1 的真实数据。

审查通过的设计点：

- 法人筹码要求 `symbol`、`trade_date`、`available_at`、三大法人买卖超字段、`data_source`、`raw_snapshot_id`。
- 融资融券要求 `symbol`、`trade_date`、`available_at`、融资/融券余额与变化、`data_source`、`raw_snapshot_id`。
- 月营收要求 `source_period`、`announcement_date`、`available_at`、`revenue`、YoY/MoM、`days_since_last_report`、`raw_snapshot_id`。
- 日频法人/融资融券默认保守 T+1，但仍要求报告列明可见时间证据。
- 月营收明确禁止按 `source_period` 直接 join。
- 事后修正要求新增 snapshot，不得覆盖历史 as-reported 记录。

当前仍未满足 Phase 1 的原因：

- 没有真实 raw archive。
- 没有真实 row-level `available_at`。
- 没有真实覆盖率/缺失率。
- 没有可验证的 PIT 样本。
- 月营收脚本和公告日数据源均未确认。

因此，Phase 1 仍不允许。

## 4. 脚本盘点审查

Phase 0B 盘点结果合理：

- FinMind institutional full/POC download：需要联网并写本地输出，Phase 0B 禁止运行。
- FinMind margin full/POC download：需要联网并写本地输出，Phase 0B 禁止运行。
- institutional/margin materialize：会写派生文件或 feature 相关路径，Phase 0B 禁止运行。
- screen 脚本：会写 Qlib feature bin 或 IC screening 产物，Phase 0B 禁止运行。
- margin util ablation：属于实验/模型方向，Phase 0B 和真实补齐阶段都不应运行。

补充判断：

- 报告中 `touches_provider_refresh_publish=True` 对部分 materialize/screen 脚本是保守静态分类，可能把 feature/bin 写入与 provider publish 混在一起；但在只读审查中保守处理是可接受的。
- 这不构成执行偏离，反而降低误运行风险。

## 5. 模型/指标/样本审查

本阶段未涉及模型、指标回测或样本构建，符合 Phase 0B 限制。

未发现：

- Phase 1 样本。
- 单因子 IC。
- top bucket 绩效。
- 规则型风险过滤 baseline。
- Risk Filter Model。
- 组合回放。

验证：

- 已执行 `python -m py_compile scripts/audit_tw_decision_orthogonal_phase0b.py`，通过。

## 6. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：仅有安全边界声明类关键词，例如 broker/orders/quick-trade/target position/provider refresh/publish/accepted latest；语境均为“未执行”“禁止”“需要授权”。

### Network Audit

本次审查对象为本地脚本、报告与文档产物。未发现实际网络请求证据。

### Console Audit

未发现执行下载、provider refresh/publish、accepted latest switching、monitor 写入、broker、quick-trade 或订单路径的证据。

### Text / Agent Semantics

报告没有给出买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 7. 必须修复项

当前没有必须返工修复项。

但在进入任何真实数据补齐前，必须由用户确认以下事项：

- 是否允许联网调用 FinMind 或其他数据源。
- 是否允许写入新的正交 raw archive 与 PIT snapshot。
- 是否接受法人/融资融券日频数据使用保守 T+1 `available_at` 规则。
- 月营收没有现成脚本时，是否允许新增脚本或改用其他具备公告日的数据源。

未确认前，执行者不得继续。

## 8. 可暂缓项

继续暂缓：

- 月营收数据源接入。
- materialize 特征。
- Qlib bin/provider 写入。
- Phase 1 样本构建。
- 单因子/分组检验。
- 规则型风险过滤 baseline。
- Risk Filter Model。
- 持仓风险验证。
- 前端/API。

## 9. 是否需要用户确认的问题

需要用户确认。

Phase 0B 已经完成只读方案设计。下一步若继续，就是 Phase 0C：真实数据补齐 POC / raw archive 建立。这会涉及联网与写入本地归档，不能由审查者或执行者默认启动。

审查者建议：

- 不要直接做 full backfill。
- 先做受限 Phase 0C POC，只覆盖法人筹码与融资融券。
- 月营收暂缓，因为当前未发现现成脚本，且公告日/PIT 风险更高。
- Phase 0C 不允许 materialize、screen、ablation、Phase 1 样本或模型训练。

## 10. 给执行者的下一步工作文档

当前不给执行者可立即执行的 Phase 0C 任务。必须等待用户明确确认是否允许联网和写 raw archive。

如果用户确认“允许 Phase 0C 受限数据补齐 POC”，执行者才可按以下边界执行。

### 10.1 Phase 0C 目标

建立最小可审计 raw archive，用于验证法人筹码和融资融券是否能产生 row-level PIT 数据。

Phase 0C 不是 Phase 1，不做因子检验，不做样本，不训练模型。

### 10.2 Phase 0C 推荐范围

数据类别：

- 法人筹码：允许 POC。
- 融资融券：允许 POC。
- 月营收：暂缓，不允许新增脚本，除非用户另行明确授权。

时间范围：

- 推荐先使用 2025-01-01 至 2026-06-10。
- 如 API 限额或执行成本较高，可缩小到最近 3 到 6 个月。

股票范围：

- 仅限当前 qlib / tw_liquid_dyn 研究 universe 的小样本。
- 推荐不超过 50 到 150 档。
- 不允许全市场补齐，除非用户另行授权。

### 10.3 Phase 0C 允许产物

建议新增：

- `data_tw/experiments/decision_orthogonal/phase0c_raw_archive/`
- `data_tw/experiments/decision_orthogonal/phase0c_download_status.csv`
- `data_tw/experiments/decision_orthogonal/phase0c_pit_snapshot_manifest.csv`
- `data_tw/experiments/decision_orthogonal/phase0c_coverage_report.csv`
- `data_tw/experiments/decision_orthogonal/phase0c_pit_validation_samples.csv`
- `docs/tw_decision_model_orthogonal/PHASE0C_EXECUTION_REPORT_CN.md`

如需新增包装脚本，建议命名：

- `scripts/build_tw_decision_orthogonal_phase0c_raw_archive.py`

包装脚本必须显式记录：

- 是否联网。
- 数据源。
- 抓取时间 `fetched_at`。
- 原始 `trade_date`。
- 生成的 `available_at`。
- `raw_snapshot_id`。
- 失败/缺失原因。

### 10.4 Phase 0C 禁止事项

- 禁止 materialize derived features。
- 禁止写 Qlib bin。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止 Phase 1 样本。
- 禁止单因子检验。
- 禁止模型训练。
- 禁止前端/API。
- 禁止 broker、orders、quick-trade、target position/target weight。
- 禁止全市场补齐。
- 禁止月营收新增数据源，除非用户另行确认。

### 10.5 Phase 0C Gate

Phase 0C 完成后，审查者只判断是否具备进入 Phase 1 的数据前提。

允许进入 Phase 1 的最低条件：

- 至少一类数据有非零行级 raw archive。
- 每行有 `symbol`、`trade_date`、`available_at`、`data_source`、`raw_snapshot_id`。
- 有覆盖率、缺失率、失败原因。
- 有 PIT validation samples 证明 `available_at <= asof`。
- 没有 materialize、screen、训练或前端/API 越界。

如果只拿到 trade_date 而无法证明可见时间，必须 deferred，不得进入 Phase 1。

## 11. 审查者最终裁决

- Phase 0B 执行范围：通过。
- Phase 0B 安全边界：通过。
- 是否偏离主线：否。
- 是否新增未授权分支：否。
- 是否允许进入 Phase 1：否。
- 是否允许执行 Phase 0C：需要用户确认。
- 当前给执行者的指令：停止等待；若用户确认，最多执行受限 Phase 0C POC raw archive，不得进入 Phase 1。
