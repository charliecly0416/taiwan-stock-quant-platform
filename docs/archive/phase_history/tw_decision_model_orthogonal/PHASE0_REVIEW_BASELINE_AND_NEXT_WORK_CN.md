# 正交数据 Decision Model Phase 0 初始审查与下一步工作文档

审查日期：2026-06-10

审查依据：

- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/EXECUTOR_PROMPT_CN.md`

当前状态：

- 正交数据增强主线刚启动。
- 尚未发现 `data_tw/experiments/decision_orthogonal/` 下的 Phase 0 产物。
- 旧主线 `data_tw/experiments/decision_model/` 下的 Phase 0/Phase 1 产物不能视为正交数据 PIT 审计通过证据。
- 本轮只授权 Phase 0 数据可用性与 point-in-time 审计，不授权训练模型或进入 Phase 1。

## 1. 本步审核结论

允许执行者开始 Phase 0，但只能做正交数据源审计。

Phase 0 的唯一目标是回答：

1. 本地是否已有法人筹码、融资融券、月营收相关数据。
2. 每类数据是否有可审计的发布时间或等价可见时间。
3. 哪些字段可以 point-in-time 地进入 Phase 1。
4. 哪些字段必须 deferred 或 fail。

如果法人筹码、融资融券、月营收三类数据全部无法 PIT 化，本主线应停止，不得进入 Phase 1。

## 2. 主线一致性审查

本新主线不是 Phase 2D，也不是继续修补已归档失败的 Entry Model v1。

必须保持的新主线定义：

- 保留 `baseline_qlib_rank` 作为主排序基线。
- 正交数据只用于验证信息增量与风险过滤可能性。
- Phase 0 只做数据审计。
- Phase 1 才允许做 PIT 样本与单因子/分组检验。
- Phase 2 才允许做规则型风险过滤 baseline。
- Phase 3 以后才可能讨论 Risk Filter Model。

Phase 0 禁止事项：

- 禁止训练任何模型。
- 禁止构建 Entry Model v2。
- 禁止组合回放。
- 禁止前端/API 产品化。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止 FinMind 或其他计划外数据源接入，除非用户另行确认。
- 禁止用没有发布时间证据的字段进入样本。

## 3. 数据与 PIT 审查要求

执行者必须逐类审计以下数据。

### 3.1 法人筹码

候选字段包括但不限于：

- 外资买卖超。
- 投信买卖超。
- 自营商买卖超。
- 三大法人合计买卖超。
- 连续 N 日买超/卖超。
- 买卖超占成交量比例。
- 外资/投信同步方向。

Phase 0 必须回答：

- 数据在本地哪里，文件或表路径是什么。
- symbol 与交易日字段是什么。
- 原始交易日是否等价于可见日，还是需要 T+1 `available_at`。
- 是否存在事后修正覆盖历史。
- 覆盖起止日期、symbol 覆盖率、缺失率。
- 是否能为每行生成 `available_at`。

没有可解释 `available_at` 规则的字段必须 deferred。

### 3.2 融资融券

候选字段包括但不限于：

- 融资余额变化。
- 融券余额变化。
- 融资使用率 proxy。
- 融券回补 proxy。
- 融资快速增加且价格高位。
- 融资下降但价格不跌。

Phase 0 必须回答：

- 数据在本地哪里，文件或表路径是什么。
- trade date 与可见时间关系是什么。
- 是否按交易日发布，是否需要 T+1 处理。
- 是否有停券、暂停交易或特殊市场状态导致的缺失。
- 覆盖起止日期、symbol 覆盖率、缺失率。
- 是否能生成 `available_at` 与 `days_since_last_report`。

没有发布时间证据时不得进入 Phase 1。

### 3.3 月营收

候选字段包括但不限于：

- 月营收 YoY。
- 月营收 MoM。
- YoY 连续改善/转弱。
- 近 3 个月 YoY 均值。
- 近 3 个月 YoY 斜率。
- 公告后天数 `days_since_last_report`。

Phase 0 必须重点检查：

- 是否有 `source_period`，例如 `2025-09`。
- 是否有 `announcement_date` 或等价公告时间。
- 是否有 `available_at`。
- 是否保留原始公告期与衍生特征。
- 是否错误地用所属月份直接 join 到当月交易日。
- 是否存在事后修正值覆盖历史。

月营收不能只凭所属月份进入样本。没有 `announcement_date` / `available_at` 的月营收字段必须 deferred。

## 4. 模型/指标/样本审查

Phase 0 不允许模型、指标回测或训练样本构建。

允许的统计只有：

- 数据源存在性。
- 字段清单。
- 覆盖起止日期。
- symbol 覆盖率。
- 日期覆盖率。
- 缺失率。
- PIT 状态：`pass` / `deferred` / `fail`。
- deferred/fail 原因。

不得输出：

- 预测分数。
- 交易建议。
- 买入/卖出标签。
- 模型表现。
- 组合收益。
- Phase 1 单因子结果。

## 5. 安全边界审查

Phase 0 必须保持 research-only。

禁止触碰：

- broker。
- quick-trade。
- orders。
- target position / target weight。
- 自动买卖。
- provider refresh / publish。
- accepted latest switching。
- monitor config 写入。
- alerts 写入。
- 未授权前端产品化。
- 收益承诺 / 上涨概率承诺。

允许语义：

- 研究排序。
- 观察名单。
- 风险过滤。
- 人工复盘。
- 只读历史审计。

## 6. 必须修复项

当前还没有执行者报告，因此不存在已发现的执行缺陷。

但执行者在 Phase 0 必须补齐以下证据：

- 明确三类正交数据是否在本地存在。
- 明确每类数据的来源、字段、覆盖、缺失。
- 明确每个候选字段的 PIT 规则。
- 明确哪些字段可进入 Phase 1，哪些必须 deferred/fail。
- 明确是否需要用户确认新数据源或真实数据刷新。

若无法提供 `available_at` 或等价发布时间，不能用主观假设放行。

## 7. 可暂缓项

以下内容全部暂缓：

- 单因子增量检验。
- qlib Top50/Top150 样本构建。
- 规则型风险过滤 baseline。
- Risk Filter Model。
- 持仓风险验证。
- 前端展示。
- API 接入。
- provider 操作。

## 8. 是否需要用户确认的问题

当前不需要用户确认即可启动 Phase 0 本地只读审计。

但执行者遇到以下任一情况必须停止并报告，不能自行继续：

- 本地没有所需数据，必须新增数据源。
- 需要联网抓取、FinMind 接入或 provider refresh。
- 数据没有发布时间，但执行者想用 proxy 替代。
- 月营收只有所属月份，没有公告日期。
- 需要补历史数据但无法保证 PIT。
- 想提前训练模型或构建 Phase 1 样本。
- 想修改目标为直接选股/买卖建议。
- 想接前端/API。

## 9. 给执行者的 Phase 0 工作文档

### 9.1 目标

完成正交数据可用性与 point-in-time 审计，为审查者判断是否允许进入 Phase 1 提供证据。

### 9.2 必读文件

执行者开始前必须阅读：

- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/EXECUTOR_PROMPT_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE0_REVIEW_BASELINE_AND_NEXT_WORK_CN.md`

### 9.3 允许修改或新增文件

建议新增：

- `scripts/audit_tw_decision_orthogonal_phase0.py`
- `data_tw/experiments/decision_orthogonal/phase0_data_sources.json`
- `data_tw/experiments/decision_orthogonal/phase0_feature_availability.csv`
- `data_tw/experiments/decision_orthogonal/phase0_point_in_time_rules.md`
- `docs/tw_decision_model_orthogonal/PHASE0_EXECUTION_REPORT_CN.md`

如需新增其他文件，必须在执行报告中解释用途。不得修改旧主线 Phase 0/Phase 1 产物作为替代。

### 9.4 审计方法

执行者应只读扫描本地数据和代码：

- 查找法人筹码、融资融券、月营收相关文件、表、脚本、字段。
- 记录每个数据源的路径、格式、字段、最早日期、最晚日期、symbol 数量、记录数。
- 对每个候选字段标记 PIT 状态。
- 对可 PIT 字段写出 `available_at` 生成规则。
- 对月营收保留 `source_period`、`announcement_date`、`available_at`。
- 对日频法人/融资融券说明交易日与可见日关系。
- 对缺失、重复、异常值做基础统计。

禁止真实刷新数据。若只有脚本而没有本地数据，只记录脚本存在，不运行抓取。

### 9.5 `phase0_data_sources.json` 要求

每个数据源至少包含：

- `source_name`
- `category`: `institutional_flow` / `margin_short` / `monthly_revenue`
- `local_path_or_table`
- `file_or_table_exists`
- `row_count`
- `symbol_count`
- `first_date`
- `last_date`
- `date_columns`
- `symbol_columns`
- `has_announcement_date`
- `has_available_at`
- `has_source_period`
- `pit_status`: `pass` / `deferred` / `fail`
- `pit_reason`
- `data_source`

### 9.6 `phase0_feature_availability.csv` 要求

每个候选字段至少包含：

- `category`
- `feature_name`
- `raw_columns`
- `source_name`
- `coverage_start`
- `coverage_end`
- `row_count`
- `symbol_count`
- `missing_rate`
- `has_source_period`
- `has_announcement_date`
- `has_available_at`
- `available_at_rule`
- `days_since_last_report_possible`
- `pit_status`
- `deferred_or_fail_reason`
- `phase1_allowed`

`phase1_allowed=true` 只能用于 PIT 证据完整的字段。

### 9.7 `phase0_point_in_time_rules.md` 要求

必须写清：

- 每类数据的时间语义。
- 每类数据如何生成 `available_at`。
- 日频数据是否 T+0/T+1 可见，证据是什么。
- 月营收如何从 `announcement_date` 对齐到交易日。
- 如何避免用 source period 直接 join。
- 如何处理事后修正。
- 如何处理缺失和停牌。
- 哪些字段 deferred/fail，以及原因。

### 9.8 执行报告要求

`PHASE0_EXECUTION_REPORT_CN.md` 必须包含：

1. 执行范围。
2. 修改文件。
3. 生成文件。
4. 数据源清单。
5. PIT 规则摘要。
6. 覆盖率/缺失率摘要。
7. 可进入 Phase 1 的字段清单。
8. deferred/fail 字段清单。
9. 是否满足 Phase 0 Gate。
10. 是否触碰安全边界。
11. 需要审查者或用户确认的问题。

### 9.9 Phase 0 Gate

允许进入 Phase 1 的最低条件：

- 至少一类正交数据存在本地可审计数据。
- 至少一个候选字段具备 `available_at` 或等价发布时间证据。
- 月营收若进入 Phase 1，必须有 `source_period` 与 `announcement_date` / `available_at`。
- 报告明确哪些字段 `phase1_allowed=true`。
- 没有 provider refresh/publish、accepted latest switching 或真实交易相关动作。

不允许进入 Phase 1 的情况：

- 三类数据全部缺失。
- 三类数据都有值但都没有发布时间证据。
- 月营收只有所属月份，没有公告日期却被标记为可用。
- 执行者需要新增数据源或联网抓取但未获得用户确认。
- 执行者提前训练模型或构建单因子检验。

### 9.10 建议验证命令

执行者完成后建议运行：

```bash
python -m py_compile scripts/audit_tw_decision_orthogonal_phase0.py
python scripts/audit_tw_decision_orthogonal_phase0.py
```

若脚本需要访问数据库或外部服务，必须先停止并说明原因，不得绕过 Phase 0 边界。

## 10. 审查者最终裁决

- 是否允许执行 Phase 0：是。
- 是否允许进入 Phase 1：否，必须等待 Phase 0 执行报告审查。
- 是否允许训练模型：否。
- 是否允许新增数据源或刷新 provider：否。
- 是否允许前端/API 产品化：否。
- 当前给执行者的任务：只做正交数据本地可用性与 PIT 审计。
