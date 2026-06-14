# 正交数据 Decision Model Phase 0D 审查结论与 Phase 1A 工作文档

审查日期：2026-06-10

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE0D_EXECUTION_REPORT_CN.md`

审查依据：

- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE0C_REVIEW_AND_PHASE0D_WORK_CN.md`

审查产物：

- `scripts/confirm_tw_decision_orthogonal_phase0d_pit_gate.py`
- `data_tw/experiments/decision_orthogonal/phase0d_pit_clean/`
- `data_tw/experiments/decision_orthogonal/phase0d_pit_clean_manifest.csv`
- `data_tw/experiments/decision_orthogonal/phase0d_pit_valid_coverage_report.csv`
- `data_tw/experiments/decision_orthogonal/phase0d_quality_flags_summary.csv`
- `data_tw/experiments/decision_orthogonal/phase0d_phase1_allowed_fields.csv`

## 1. 本步审核结论

Phase 0D 执行范围通过，Phase 0D PIT gate 通过。

执行者没有偏离主线，也没有新增未授权分支。Phase 0D 只基于 Phase 0C raw archive 与本地交易日历做不联网 PIT 修复和 gate confirmation，没有重跑 FinMind、没有新增数据源、没有扩大时间范围或 symbol universe、没有月营收、没有 materialize、没有 Qlib bin/provider、没有 accepted latest switching、没有 Phase 1 样本、没有单因子检验、没有模型训练、没有前端/API 或交易路径。

Phase 0D 已修复 Phase 0C 的尾部 `available_at` 缺口：

- 法人筹码：5291 rows，`missing_available=0`，50 rows repaired。
- 融资融券：5300 rows，`missing_available=0`，50 rows repaired。
- 两类 cleaned view 均为 `phase1_allowed=true`。

审查者接受保守 T+1 作为 Phase 1A POC 的可见性规则，但必须继续在报告中写清：这是 conservative visibility proxy，不是官方发布时间声明。

## 2. 主线一致性审查

通过项：

- 仍处于正交数据主线。
- 只修复用户已授权的法人筹码与融资融券 POC 数据。
- 月营收继续 deferred。
- 没有补历史、扩 universe 或全市场。
- 没有进入 Phase 1 样本或因子检验。
- 没有进入 Phase 2 规则 baseline。
- 没有模型训练。

未发现项：

- 未发现 provider refresh/publish。
- 未发现 accepted latest switching。
- 未发现 Qlib bin/provider 写入。
- 未发现前端/API。
- 未发现 broker、orders、quick-trade、target position/target weight。

## 3. 数据与 PIT 审查

Phase 0D 满足进入受限 Phase 1A POC 的数据前提：

- 至少一类正交数据有非零 PIT-valid rows；实际为两类。
- PIT-clean rows 均有 `symbol`、`trade_date`、`available_at`、`data_source`、`raw_snapshot_id`。
- `available_at` 非空。
- Phase 0D coverage 已区分 raw rows 与 PIT-valid rows。
- 无 duplicate rows。
- quality flags 已拆解为修复痕迹，不影响核心字段使用。

限制：

- 当前只覆盖 2025-05-01 到 2025-09-30。
- 当前仅 50 档 POC universe。
- 当前不能证明跨年度稳定性。
- 当前不能直接进入 Phase 2。

因此，下一步只能做 Phase 1A POC 样本与单因子 sanity check，而不是完整 Phase 1 Gate 通过。

## 4. 模型/指标/样本审查

Phase 0D 未涉及模型、指标回测或样本构建，符合阶段限制。

验证：

- 已执行 `python -m py_compile scripts/confirm_tw_decision_orthogonal_phase0d_pit_gate.py`，通过。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：仅有安全边界声明类关键词，语境均为“未执行”或“禁止”。

### Network Audit

Phase 0D 未联网，未重跑 FinMind。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor 写入、broker、quick-trade 或订单路径证据。

### Text / Agent Semantics

报告没有买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 6. 必须修复项

当前无必须返工项。

Phase 1A 执行者必须继承以下限制：

- 只能使用 Phase 0D cleaned archive。
- 不能联网。
- 不能扩大时间范围或 symbol universe。
- 不能启用月营收。
- 不能 materialize Qlib bin。
- 不能训练模型。
- 不能进入 Phase 2。

## 7. 可暂缓项

继续暂缓：

- 月营收。
- 更长历史补齐。
- 更多 symbols。
- 完整 Phase 1 Gate。
- 规则型风险过滤 baseline。
- Risk Filter Model。
- 前端/API。

## 8. 是否需要用户确认的问题

当前不需要用户确认即可进入 Phase 1A POC，因为 Phase 1A 只读取既有 Phase 0D cleaned archive 与本地 qlib/价格/qlib rank 产物，不新增联网或数据补齐。

但以下事项必须再次请求用户确认：

- 扩大历史范围。
- 增加 symbols。
- 重跑 FinMind。
- 新增月营收数据源。
- 进入完整 Phase 1 或 Phase 2。
- 训练模型。

## 9. 给执行者的 Phase 1A 工作文档

### 9.1 目标

构建受限 POC PIT 样本，并做单因子 sanity check，判断法人筹码与融资融券是否在当前 5 个月、50 档 POC universe 中显示任何值得继续补齐的增量迹象。

Phase 1A 不是完整 Phase 1。Phase 1A 不能直接放行 Phase 2。

### 9.2 允许输入

只允许读取：

- `data_tw/experiments/decision_orthogonal/phase0d_pit_clean/phase0d_institutional_flow_pit_clean.csv`
- `data_tw/experiments/decision_orthogonal/phase0d_pit_clean/phase0d_margin_short_pit_clean.csv`
- 本地 adjusted price / normalized OHLCV。
- 本地既有 qlib rank / qlib score 产物。
- Phase 0D manifest、coverage、quality flags。

禁止读取或生成：

- 新 FinMind 下载。
- 月营收。
- Qlib bin/provider 写入。
- accepted latest switching。

### 9.3 样本要求

样本粒度：

- `asof` / `symbol`

对齐规则：

- 只允许使用 `available_at <= asof` 的正交数据。
- 不得使用 `trade_date == asof` 且 `available_at > asof` 的行。
- 对同一 symbol/asof，选择当时最新可见记录。
- forward label 必须从 `asof` 之后计算，不能包含 asof 当日不可见信息。

建议 label：

- `fwd_5d_excess_return`
- `fwd_10d_excess_return`
- `fwd_20d_excess_return`

允许特征：

- 法人筹码原始净买卖超。
- 法人筹码 5/10/20 日滚动和或均值，仅限 `available_at <= asof`。
- 外资/投信同步方向。
- 融资余额变化。
- 融券余额变化。
- 融资/融券 5/10/20 日变化。
- qlib rank / qlib score 作为基线和控制变量。

禁止特征：

- 月营收。
- 任何没有 `available_at` 的字段。
- 任何用未来窗口计算的字段。
- 任何模型预测分数。

### 9.4 检验要求

Phase 1A 只做 sanity check：

- 单因子 RankIC / Spearman。
- 分位数组表现。
- 与 qlib rank 的相关性。
- Top bucket 中正交特征强弱分组表现。
- 按月份拆分稳定性。
- 覆盖率与缺失率。
- leakage audit。

必须明确：

- 每个结果覆盖的月份。
- 每个结果的样本数。
- 是否只在单月有效。
- 是否与 qlib rank 高度相关。
- 是否只是噪声。

### 9.5 建议新增文件

建议新增：

- `scripts/build_tw_decision_orthogonal_phase1a_poc_samples.py`
- `data_tw/experiments/decision_orthogonal/phase1a_poc_samples.parquet`
- `data_tw/experiments/decision_orthogonal/phase1a_poc_samples_preview.csv`
- `data_tw/experiments/decision_orthogonal/phase1a_schema.json`
- `data_tw/experiments/decision_orthogonal/phase1a_factor_increment_report.md`
- `data_tw/experiments/decision_orthogonal/phase1a_leakage_audit_report.md`
- `data_tw/experiments/decision_orthogonal/phase1a_factor_metrics.csv`
- `docs/tw_decision_model_orthogonal/PHASE1A_EXECUTION_REPORT_CN.md`

### 9.6 Phase 1A Gate

Phase 1A 完成后只能有三种结论：

- `request_larger_backfill=true`：POC 有稳定迹象，建议用户授权更长历史/更多 symbols。
- `stop_orthogonal_poc=true`：POC 无增量迹象，建议停止或重定义。
- `phase1a_incomplete=true`：样本或 leakage audit 不充分，需要返工。

Phase 1A 不允许输出：

- `enter_phase2=true`
- `train_model=true`
- `phase1_gate_pass=true`

原因：当前数据只有 5 个月、50 档，不能满足完整 Phase 1 的独立区间稳定性要求。

### 9.7 执行报告要求

`PHASE1A_EXECUTION_REPORT_CN.md` 必须包含：

1. 执行范围。
2. 修改文件。
3. 生成文件。
4. 样本构建规则。
5. PIT join 规则。
6. label 定义。
7. 特征清单。
8. 覆盖率与缺失率。
9. leakage audit 结论。
10. 单因子/分组 sanity check。
11. 与 qlib rank 的相关性。
12. 按月份稳定性。
13. 是否建议更大范围 backfill。
14. 是否触碰安全边界。
15. 需要审查者或用户确认的问题。

## 10. 审查者最终裁决

- Phase 0D 执行范围：通过。
- Phase 0D 安全边界：通过。
- 是否偏离主线：否。
- 是否新增未授权分支：否。
- Phase 0D PIT gate：通过。
- 是否允许进入 Phase 1A POC：是。
- 是否允许进入完整 Phase 1 Gate：否。
- 是否允许进入 Phase 2：否。
- 下一步：执行受限 Phase 1A POC 样本与单因子 sanity check。
