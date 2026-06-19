# 正交数据 Decision Model Phase 0 审查结论与用户确认事项

审查日期：2026-06-10

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE0_EXECUTION_REPORT_CN.md`

审查依据：

- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE0_REVIEW_BASELINE_AND_NEXT_WORK_CN.md`

审查产物：

- `scripts/audit_tw_decision_orthogonal_phase0.py`
- `data_tw/experiments/decision_orthogonal/phase0_data_sources.json`
- `data_tw/experiments/decision_orthogonal/phase0_feature_availability.csv`
- `data_tw/experiments/decision_orthogonal/phase0_point_in_time_rules.md`

## 1. 本步审核结论

Phase 0 执行范围通过，但 Phase 0 Gate 失败。不得进入 Phase 1。

执行者没有偏离主线，也没有新增未授权分支。实际工作限定在法人筹码、融资融券、月营收三类正交数据的本地只读可用性与 point-in-time 审计，没有训练模型、没有构建 Phase 1 样本、没有单因子检验、没有组合回放、没有前端/API、没有 provider refresh/publish、没有 accepted latest switching，也没有触碰交易相关路径。

但是，Phase 0 结果显示三类正交数据当前均没有本地可用行级数据：

- 法人筹码：`row_count=0`，`phase1_allowed_count=0`。
- 融资融券：`row_count=0`，`phase1_allowed_count=0`。
- 月营收：`row_count=0`，无 `source_period` / `announcement_date` / `available_at` 证据，`phase1_allowed_count=0`。

因此，没有任何字段 `phase1_allowed=true`。按 Phase 0 Gate，当前不能进入 Phase 1。

## 2. 主线一致性审查

通过项：

- 保持正交数据主线，没有回到 Entry Model v1/Phase 2D。
- 只审计法人筹码、融资融券、月营收三类计划内数据。
- 没有构建 Entry Model v2。
- 没有训练 Risk Filter Model。
- 没有进入规则型 baseline、持仓风险验证或前端阶段。
- 报告明确写出 Phase 0 Gate 为 `False`，没有包装成可进入 Phase 1。

未发现项：

- 未发现新增计划外数据源。
- 未发现联网抓取或真实数据刷新。
- 未发现 provider publish/refresh。
- 未发现 accepted latest switching。
- 未发现 broker、orders、quick-trade、target position/target weight。

审查补充：

- 我额外做了只读文件名搜索，发现本地存在 `qlib_pipeline/examples/tw/run_tw_finmind_institutional_full_download.py`、`run_tw_finmind_margin_full_download.py`、`materialize_tw_institutional_factors.py`、`materialize_tw_margin_batch_a.py` 等脚本。
- 这些只是脚本存在证据，不是可用 PIT 行级数据证据。
- 执行者 Phase 0 报告没有完整列出这些脚本，属于审计覆盖说明不完整，但不改变 Gate 失败结论。
- 在用户确认前，不得运行这些下载或 materialize 脚本。

## 3. 数据与 PIT 审查

Phase 0 的 PIT 审查结论成立：当前没有任何一类数据满足进入 Phase 1 的最低条件。

法人筹码：

- 只有 FinMind summary/log 证据。
- 行级归档数据为 0。
- 无 row-level `available_at`。
- 无可审计 T+1 可见规则被实际数据证明。
- 不允许进入 Phase 1。

融资融券：

- 只有 FinMind summary/log 证据。
- 行级归档数据为 0。
- 无 row-level `available_at`。
- 无 `days_since_last_report` 生成基础。
- 不允许进入 Phase 1。

月营收：

- 行级归档数据为 0。
- 无 `source_period`。
- 无 `announcement_date`。
- 无 `available_at`。
- 不能用所属月份替代公告日。
- 不允许进入 Phase 1。

## 4. 模型/指标/样本审查

本阶段未涉及模型、指标回测或样本构建，符合 Phase 0 限制。

允许统计项均为数据源存在性、字段清单、覆盖率、缺失率、PIT 状态与 fail/deferred 原因。未发现以下越界内容：

- 预测分数。
- 买入/卖出标签。
- 模型训练。
- 单因子增量检验。
- 组合收益。
- Phase 1 样本。

验证：

- 已执行 `python -m py_compile scripts/audit_tw_decision_orthogonal_phase0.py`，通过。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：安全关键词仅出现在“未触碰”或禁止范围说明中，不构成危险行为。

### Network Audit

本次审查对象为本地脚本、报告与 CSV/JSON/Markdown 产物。未发现网络请求证据。

### Console Audit

未发现触发 provider refresh/publish、accepted latest switching、monitor 写入、broker、quick-trade 或订单路径的证据。

### Text / Agent Semantics

报告没有给出买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。交易相关词汇均处于安全边界否定语境。

### Verdict

只读研究边界通过。

## 6. 必须修复项

当前没有允许执行者直接修复的 Phase 1 前置项，因为数据不存在本身已经触发用户确认条件。

如果用户确认继续正交数据主线，执行者下一步必须先补充以下 Phase 0B 证据，而不是进入 Phase 1：

- 完整列出现有 FinMind 法人/融资融券/月营收相关脚本，但只读，不运行下载。
- 明确哪些脚本会触发联网、provider refresh 或数据写入。
- 设计 PIT 行级归档 schema，包括 `available_at`、`source_period`、`announcement_date`、`data_source`、`raw_value`、`as_reported_snapshot_id`。
- 明确数据补齐范围、起止日期、symbol universe 与是否需要联网。
- 明确补齐后如何证明没有未来函数。

在用户确认前，上述内容只能作为方案，不得执行真实下载或写入生产数据。

## 7. 可暂缓项

以下内容继续暂缓：

- Phase 1 样本构建。
- 单因子/分组增量检验。
- qlib Top50/Top150 rerank 检验。
- 规则型风险过滤 baseline。
- Risk Filter Model。
- 持仓风险验证。
- 前端/API。
- provider publish/refresh。
- accepted latest switching。

## 8. 是否需要用户确认的问题

需要用户确认。原因是 Phase 0 Gate 失败，而继续本主线需要新增或补齐数据源。

用户需要决定是否允许进入一个新的 Phase 0B：正交数据补齐与 PIT 归档方案设计。

可选方向：

1. 停止正交数据主线。
   - 理由：三类正交数据当前均没有本地 PIT 行级数据。
   - 结果：不进入 Phase 1，不再给执行者建模任务。

2. 允许 Phase 0B 只读方案设计。
   - 只允许执行者盘点已有下载/materialize 脚本与设计 PIT schema。
   - 不允许联网、不允许真实下载、不允许 provider refresh/publish。
   - 完成后再由审查者判断是否值得申请数据补齐。

3. 允许 Phase 0B 数据补齐实施。
   - 需要用户明确授权联网或指定数据来源。
   - 必须要求每行具备 `available_at` / `announcement_date` / `source_period` 等 PIT 字段。
   - 该选项风险最高，不能由执行者或审查者默认启动。

审查者建议：选择方向 2，先做只读方案设计，不直接实施数据补齐。

## 9. 给执行者的下一步工作文档

当前不给执行者 Phase 1 工作文档。

在用户确认前，执行者必须停止，不得继续：

- 不得进入 Phase 1。
- 不得构建样本。
- 不得跑单因子检验。
- 不得训练模型。
- 不得运行下载脚本。
- 不得 materialize 新数据。
- 不得调用 provider refresh/publish。
- 不得切换 accepted latest。

若用户确认“允许 Phase 0B 只读方案设计”，执行者才可执行以下受限任务。

### 9.1 Phase 0B 只读方案设计目标

目标不是补数据，而是回答：

- 当前仓库已有的法人筹码、融资融券、月营收脚本能否用于 PIT 归档。
- 需要哪些输入、输出、字段和时间语义。
- 哪些步骤会触发联网或写入，必须另行授权。
- 若未来补齐数据，如何保证不引入未来函数。

### 9.2 Phase 0B 允许产物

仅允许新增文档和只读审计结果：

- `docs/tw_decision_model_orthogonal/PHASE0B_DATA_BACKFILL_PLAN_CN.md`
- `data_tw/experiments/decision_orthogonal/phase0b_script_inventory.csv`
- `data_tw/experiments/decision_orthogonal/phase0b_pit_schema_proposal.md`
- `docs/tw_decision_model_orthogonal/PHASE0B_EXECUTION_REPORT_CN.md`

### 9.3 Phase 0B 禁止事项

- 禁止联网。
- 禁止真实数据下载。
- 禁止运行 FinMind full download / POC download。
- 禁止 materialize 新特征。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止训练模型。
- 禁止构建 Phase 1 样本。
- 禁止前端/API。

### 9.4 Phase 0B 输出要求

执行报告必须明确：

- 哪些脚本存在。
- 哪些脚本只读安全。
- 哪些脚本会联网或写数据。
- 哪些字段可以承载 `available_at`、`announcement_date`、`source_period`。
- 数据补齐最小可行范围。
- 用户如果要继续，需要授权什么。

## 10. 审查者最终裁决

- Phase 0 执行范围：通过。
- Phase 0 安全边界：通过。
- 是否偏离主线：否。
- 是否新增未授权分支：否。
- Phase 0 Gate：失败。
- 是否允许进入 Phase 1：否。
- 是否需要用户确认：是。
- 当前给执行者的指令：停止等待，不得继续；若用户确认，最多进入 Phase 0B 只读方案设计。
