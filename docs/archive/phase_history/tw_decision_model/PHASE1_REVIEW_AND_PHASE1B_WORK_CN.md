# Decision Meta Model Phase 1 审核意见与 Phase 1B 修复工作文档

## 0. 审查入口与依据

审查入口：

- `docs/tw_decision_model/PHASE1_EXECUTION_REPORT_CN.md`

审查依据：

- `prompt_investigate.md`
- `docs/TW_STOCK_DECISION_META_MODEL_DESIGN_CN.md`
- `docs/tw_decision_model/PHASE0_REVIEW_AND_PHASE1_WORK_CN.md`
- `scripts/build_tw_decision_phase1_samples.py`
- `data_tw/experiments/decision_model/phase1_schema.json`
- `data_tw/experiments/decision_model/phase1_label_quality_report.md`
- `data_tw/experiments/decision_model/phase1_leakage_audit_report.md`
- `data_tw/experiments/decision_model/phase1_exclusion_report.csv`

本次同时按台股 research-only 安全边界进行审查。

## 1. 本步审核结论

结论：不通过，需执行 Phase 1B 修复后复审。

执行者没有偏离到模型训练、组合回放、前端产品化或真实交易动作，也没有新增与 Decision Meta Model 无关的分支。但当前 Phase 1 产物不能直接作为 Phase 2 训练输入，主要原因是 schema 把 `market_regime` 放入了 `input_features`，这违反“离散 market_regime 仅用于解释和分组评估”的主线约束。

因此，不允许进入 Phase 2。下一步应先修复 Phase 1 样本与 schema。

## 2. 主线一致性审查

### 2.1 未发现越阶段实现

执行报告说明：

- 只新增样本构建脚本，见 `PHASE1_EXECUTION_REPORT_CN.md:5` 至 `PHASE1_EXECUTION_REPORT_CN.md:9`。
- 生成样本、schema、label quality、leakage audit、exclusion report，见 `PHASE1_EXECUTION_REPORT_CN.md:5` 至 `PHASE1_EXECUTION_REPORT_CN.md:7`。
- 未训练模型，见 `PHASE1_EXECUTION_REPORT_CN.md:8`。
- 未触碰 broker/orders/quick-trade/provider/accepted latest/monitor，见 `PHASE1_EXECUTION_REPORT_CN.md:9` 和 `PHASE1_EXECUTION_REPORT_CN.md:62` 至 `PHASE1_EXECUTION_REPORT_CN.md:68`。

### 2.2 未发现新增业务分支

以下内容仍属于 Phase 1 主线：

- 样本粒度为 `date-symbol`。
- 使用 qlib score/rank、技术趋势、流动性 proxy、TWII 连续特征和 market breadth。
- FinMind 暂缓字段未进入样本，见 `phase1_leakage_audit_report.md:12`。
- TWII 缺口进入 exclusion report，见 `phase1_leakage_audit_report.md:9` 至 `phase1_leakage_audit_report.md:11`。
- Candidate Generator 覆盖 Top50、score percentile、rank improvement、trend strength，不只覆盖 Top50，见 `PHASE1_EXECUTION_REPORT_CN.md:40` 至 `PHASE1_EXECUTION_REPORT_CN.md:48`。

## 3. 发现的问题

### 3.1 High：`market_regime` 被错误放入 input_features

证据：

- `phase1_schema.json:4` 至 `phase1_schema.json:55` 定义了 `input_features`。
- `phase1_schema.json:46` 将 `market_regime` 放入 `input_features`。
- 脚本中 `schema_payload()` 也把 `market_regime` 放入输入特征，见 `build_tw_decision_phase1_samples.py:427` 至 `build_tw_decision_phase1_samples.py:440`。
- 泄漏审计报告写明 `market_regime` “included only as explanation/grouping feature”，见 `phase1_leakage_audit_report.md:13`，但 schema 实际上把它列为模型输入，二者矛盾。

影响：

- 总设计要求大盘状态以连续特征为主，离散 `market_regime` 仅用于解释和分组评估。
- 若 Phase 2 按当前 schema 训练，会把 `market_regime` 当成模型输入，偏离主线。

必须修复：

- 从 `input_features` 移除 `market_regime`。
- 将 `market_regime` 移入 `audit_only_columns` 或新增 `grouping_columns`。
- leakage audit 必须重新验证 `market_regime not in input_features=true`。

### 3.2 Medium：`candidate_reason_flags` 是解释文本，不应直接作为模型输入

证据：

- `candidate_reason_flags` 位于 `phase1_schema.json:54` 的 `input_features`。
- 该字段由候选来源 flag 拼接成文本，脚本生成逻辑见 `build_tw_decision_phase1_samples.py:438` 至 `build_tw_decision_phase1_samples.py:440`。

影响：

- Phase 2 如果直接读取 `input_features`，该文本列会进入训练输入，容易造成编码不清、训练失败或不可解释的类别处理。
- 其信息已由 `candidate_from_top50`、`candidate_from_score_percentile`、`candidate_from_rank_improvement`、`candidate_from_trend_strength` 表达。

必须修复：

- 将 `candidate_reason_flags` 移入 `audit_only_columns`。
- Phase 2 只允许使用结构化 boolean candidate flags。

### 3.3 Medium：Label quality 缺少年度覆盖缺口说明

证据：

- label quality report 只列出 2022、2023、2025、2026，没有 2024，见 `phase1_label_quality_report.md:5` 至 `phase1_label_quality_report.md:9`。
- 执行报告只给出 qlib signal 总范围 `2022-01-03` 至 `2026-06-09`，见 `PHASE1_EXECUTION_REPORT_CN.md:21` 至 `PHASE1_EXECUTION_REPORT_CN.md:24`，但没有解释年度缺口。

影响：

- Phase 2 不能按总设计里的理想 train/validation/test/forward split 直接执行。
- 如果不显式报告 2024 缺口，后续训练可能误以为样本连续覆盖 2022-2026。

必须修复：

- 新增日期覆盖报告，按 year/month 输出 qlib rows、sample rows、labeled rows。
- 明确 2024 是否完全缺失、缺失原因、是否可接受。
- Phase 2 工作文档必须基于实际可用年份重新定义 split，不能假设 2018-2021 或 2024 可用。

### 3.4 Low：泄漏审计结论表达需要收紧

证据：

- 泄漏审计报告称 “No evidence of future inputs”，见 `phase1_leakage_audit_report.md:16` 至 `phase1_leakage_audit_report.md:18`。
- 该结论对 future-prefixed 字段、FinMind 字段成立，但对 `market_regime` 的“仅解释/分组”边界不成立，因为 schema 仍把它列为输入。

必须修复：

- leakage audit 增加 schema policy checks：
  - `market_regime_not_in_input_features`
  - `candidate_reason_flags_not_in_input_features`
  - `label_targets_no_overlap_with_input_features`
  - `audit_only_no_overlap_with_input_features`
  - `deferred_by_phase0_absent_from_sample_columns`

## 4. 已通过项

以下内容通过审查：

1. 样本粒度为 `date-symbol`。
2. 未训练模型。
3. FinMind 暂缓字段未进入样本。
4. `future_` 字段未进入 `input_features`，见 `phase1_leakage_audit_report.md:7`。
5. `future_return_label_base` 在 `excluded_columns`，见 `phase1_schema.json:86` 至 `phase1_schema.json:88`。
6. TWII 缺口被排除到审计报告，缺口行为覆盖 `2026-05-22` 至 `2026-06-09`。
7. Candidate Generator 不是只看 Top50。
8. label quality 报告包含动态标签、连续目标和排序目标说明，见 `phase1_label_quality_report.md:11` 至 `phase1_label_quality_report.md:14`。
9. qlib score 同时保留 raw、date percentile、date z-score。

## 5. 必须修复项

执行者必须完成：

1. 从 `input_features` 移除 `market_regime`。
2. 将 `market_regime` 加入 `grouping_columns` 或 `audit_only_columns`。
3. 从 `input_features` 移除 `candidate_reason_flags`。
4. 将 `candidate_reason_flags` 加入 `audit_only_columns`。
5. 重新生成 `phase1_schema.json`。
6. 重新生成 `phase1_leakage_audit_report.md`。
7. 新增或更新样本日期覆盖报告，明确 2024 缺口。
8. 更新 `PHASE1_EXECUTION_REPORT_CN.md`，不得再建议进入 Phase 2，除非修复完成。
9. 如重新生成 parquet/csv 样本，必须保持样本行数和标签结果无非预期变化，并报告 diff。

## 6. 可暂缓项

以下内容仍可暂缓，不阻塞 Phase 1B：

1. FinMind institutional / margin / monthly revenue / valuation。
2. 官方 limit-up/down flag。
3. 正式 `trading_money`。
4. Entry Model / Exit Risk Model 训练。
5. 前端产品化。
6. 组合回放集成。

## 7. 是否需要用户确认的问题

当前没有需要停下来让用户确认的问题。

本次问题属于执行者对 schema 分组的实现偏差，可以按总设计和上一份 Phase 1 工作文档直接修复。如果执行者想保留 `market_regime` 作为模型输入，必须停止并提交用户确认；在确认前不得进入 Phase 2。

## 8. 台股只读安全边界审查

### Findings

Critical：无。

High：无。

Medium：无。

Low：关键词扫描命中 `broker`、`orders`、`quick-trade`、`target position`、`provider refresh`、`accepted latest` 等词，但上下文均为禁止事项、安全声明或执行报告说明，不是真实动作入口。

### Network Audit

未提供 network audit。Phase 1 是本地样本构建，审查脚本和报告未发现网络请求、provider publish/refresh 或 accepted latest switching。

### Console Audit

未提供 console audit。审查过程中本地只读检查多次遇到沙箱 `bwrap: loopback: Failed RTM_NEWADDR`，已按权限流程重跑只读命令。该问题不影响执行者产物结论。

### Text / Agent Semantics

未发现真实交易建议、下单、目标仓位、自动买卖、连接券商、收益承诺或上涨概率承诺语义。

### Verdict

通过。

## 9. 下一步工作文档：Phase 1B 样本 schema 修复与准入复核

### 9.1 目标

修复 Phase 1 schema 与审计报告，使样本产物满足 Phase 2 训练准入要求。

Phase 1B 只允许修复样本 schema、审计报告和覆盖报告，不允许训练模型。

### 9.2 范围

允许：

- 修改 `scripts/build_tw_decision_phase1_samples.py` 的 schema 输出逻辑。
- 重新生成 Phase 1 样本产物。
- 新增日期覆盖报告。
- 更新 Phase 1 执行报告。

禁止：

- 不训练 LightGBM 或任何模型。
- 不新增 FinMind 暂缓字段。
- 不刷新 provider。
- 不发布 qlib provider。
- 不切换 accepted latest。
- 不写 broker / orders / quick-trade / target position。
- 不修改 monitor config / alerts / 模拟账户。
- 不把 `market_regime` 作为模型输入。
- 不把解释文本字段作为模型输入。

### 9.3 必须输出

执行者必须生成或更新：

1. `scripts/build_tw_decision_phase1_samples.py`
2. `data_tw/experiments/decision_model/phase1_samples.parquet`
3. `data_tw/experiments/decision_model/phase1_samples_preview.csv`
4. `data_tw/experiments/decision_model/phase1_schema.json`
5. `data_tw/experiments/decision_model/phase1_label_quality_report.md`
6. `data_tw/experiments/decision_model/phase1_leakage_audit_report.md`
7. `data_tw/experiments/decision_model/phase1_exclusion_report.csv`
8. `data_tw/experiments/decision_model/phase1_date_coverage_report.csv`
9. `docs/tw_decision_model/PHASE1_EXECUTION_REPORT_CN.md`

### 9.4 Schema 修复要求

`phase1_schema.json` 必须至少包含：

- `input_features`
- `label_targets`
- `audit_only_columns`
- `grouping_columns`
- `excluded_columns`
- `proxy_features`
- `deferred_by_phase0`
- `safety`

强制要求：

- `market_regime` 必须在 `grouping_columns` 或 `audit_only_columns`。
- `market_regime` 不得在 `input_features`。
- `candidate_reason_flags` 必须在 `audit_only_columns`。
- `candidate_reason_flags` 不得在 `input_features`。
- `candidate_from_top50`、`candidate_from_score_percentile`、`candidate_from_rank_improvement`、`candidate_from_trend_strength` 可以保留为结构化输入特征。
- `future_return_label_base` 必须继续在 `excluded_columns`。
- 所有 `future_` 字段不得在 `input_features`。
- FinMind 暂缓字段不得出现在样本列中。

### 9.5 日期覆盖报告要求

新增 `phase1_date_coverage_report.csv`，至少包含：

- `period`
- `qlib_rows`
- `sample_rows`
- `labeled_rows`
- `unlabeled_rows`
- `market_gap_rows`
- `unique_symbols`
- `notes`

覆盖粒度：

- year
- year-month

必须明确说明：

- 2024 是否缺失。
- 缺失原因，若本地无法证明原因，则写 `unknown_from_phase1_artifacts`。
- Phase 2 不得假设 2024 可用。

### 9.6 Leakage Audit 修复要求

`phase1_leakage_audit_report.md` 必须新增：

- `market_regime_not_in_input_features: pass`
- `candidate_reason_flags_not_in_input_features: pass`
- `future_columns_not_in_input_features: pass`
- `label_targets_no_overlap_with_input_features: pass`
- `audit_only_no_overlap_with_input_features: pass`
- `deferred_by_phase0_absent_from_sample_columns: pass`
- `date_coverage_gap_report_generated: pass`

### 9.7 验收标准

Phase 1B 只有满足以下条件才可重新申请进入 Phase 2：

1. `market_regime` 不在 `input_features`。
2. `candidate_reason_flags` 不在 `input_features`。
3. `grouping_columns` 或 `audit_only_columns` 明确包含 `market_regime`。
4. input / label / audit / grouping / excluded 字段无交叉污染。
5. Phase 1 样本行数、labeled rows、unlabeled rows 与修复前相比无非预期变化。
6. 日期覆盖报告明确说明 2024 缺口。
7. leakage audit 全部通过。
8. 安全边界关键词扫描只命中禁止事项或 research-only 说明。
9. 未训练模型。
10. 未触碰 provider publish/refresh、accepted latest、broker、orders、quick-trade、monitor config、alerts。

### 9.8 执行报告模板

执行者完成后提交：

```markdown
# Phase 1B 样本 schema 修复执行报告

## 1. 执行摘要

- 执行日期：
- 修改文件：
- 重新生成文件：
- 是否训练模型：
- 是否触碰只读边界：

## 2. 修复项对照

| 修复项 | 状态 | 证据 |
|---|---|---|
| market_regime 移出 input_features |  |  |
| candidate_reason_flags 移出 input_features |  |  |
| grouping_columns/audit_only_columns 更新 |  |  |
| 日期覆盖报告生成 |  |  |
| leakage audit 更新 |  |  |

## 3. Schema 检查

- input_features 数量：
- label_targets 数量：
- audit_only_columns 数量：
- grouping_columns 数量：
- excluded_columns 数量：
- input/label overlap：
- input/audit overlap：
- future inputs：
- deferred FinMind columns：

## 4. 日期覆盖

- 2022 rows：
- 2023 rows：
- 2024 rows：
- 2025 rows：
- 2026 rows：
- 2024 缺口说明：

## 5. 样本 diff

- 修复前 sample rows：
- 修复后 sample rows：
- 修复前 labeled rows：
- 修复后 labeled rows：
- 是否有非预期变化：

## 6. Leakage Audit

- market_regime_not_in_input_features：
- candidate_reason_flags_not_in_input_features：
- future_columns_not_in_input_features：
- label_targets_no_overlap_with_input_features：
- audit_only_no_overlap_with_input_features：
- deferred_by_phase0_absent_from_sample_columns：

## 7. 安全边界

- broker/orders/quick-trade：
- provider publish/refresh：
- accepted latest switching：
- monitor config/alerts：
- 真实交易建议语义：

## 8. 风险与待审查问题

- 必须修复：
- 需要用户确认：
- 可暂缓：

## 9. Phase 2 准入建议

- 是否建议进入 Phase 2：
- 若建议，限制条件：
```

## 10. 审查者最终意见

Phase 1 当前不通过，不能进入 Phase 2。

执行者应先完成 Phase 1B schema 修复与日期覆盖补充。修复通过后，审查者再决定是否放行 Phase 2 Entry Model v1 训练。
