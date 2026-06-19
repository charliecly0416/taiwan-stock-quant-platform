# Phase 0E Scrapling 说明审查结论与 Phase 1B 工作文档

审查日期：2026-06-10

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE0E_SCRAPLING_EXPLANATION_CN.md`

关联依据：

- `docs/tw_decision_model_orthogonal/PHASE0E_EXECUTION_REPORT_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE0E_REVIEW_AND_SCRAPLING_EXPLANATION_WORK_CN.md`
- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`

## 1. 本步审核结论

接受执行者对 Phase 0E 未使用 Scrapling 的解释。

理由成立：

- Phase 0E 使用的是 FinMind 结构化 JSON API，而不是需要 DOM、脚本渲染、页面解析或反爬交互的网页来源。
- `requests.get()` 能直接表达 query parameters、Authorization header、JSON 解析、timeout、状态码、row_count、错误记录与 token 脱敏。
- 执行者明确说明不是不知道 Scrapling，而是判断该 endpoint 用普通授权 API client 更贴合数据形态。
- 执行者承认没有在报告中事前说明与用户偏好不一致，这是流程沟通缺口，但不构成数据不可用或安全边界失败。
- 说明文件没有重拉数据、没有联网、没有新增数据源、没有进入 Phase 1B/Phase 2，也没有触碰 provider 或交易路径。

因此：

- 不强制用 Scrapling 重拉 Phase 0E 数据。
- Phase 0E 已生成的 normalized PIT archive 继续作为 Phase 1B 候选输入。
- Scrapling 问题在本阶段关闭，但保留流程约束：以后用户明确指定 transport、工具或实现方式时，执行者必须执行；若判断不应执行，必须在执行前或报告中主动说明原因，不能事后才补充。

## 2. 主线一致性审查

通过项：

- 说明范围限定为解释未使用 Scrapling。
- 没有新增数据源。
- 没有重拉 Phase 0E。
- 没有启用月营收。
- 没有构建 Phase 1B 样本。
- 没有做单因子检验、规则 baseline 或模型训练。
- 没有进入 Phase 2。
- 没有 materialize derived features。
- 没有 Qlib bin/provider 写入。
- 没有 provider refresh/publish。
- 没有 accepted latest switching。
- 没有前端/API 或交易路径。

未发现偏离主线或新增分支。

## 3. 数据可用性判断

Phase 0E 数据可用性不由 HTTP client 名称决定，而由以下证据决定：

- 授权 endpoint、dataset、query 参数和 token 使用方式明确。
- download status 显示两类数据请求均成功。
- raw response JSONL 保留原始返回证据。
- normalized PIT archive 仅保留 `available_at` 非空行。
- 法人筹码 normalized PIT rows：158834。
- 融资融券 normalized PIT rows：156021。
- universe 为 Top150，实际 150 symbols。
- 实际 PIT-valid trade date 范围为 2022-01-03 至 2026-05-29。
- 两类各有 1529 raw tail rows 因无法生成下一交易日 `available_at` 被排除，没有静默混入 normalized archive。

审查判断：

- 当前 archive 可用于 Phase 1B 的只读样本与单因子/分段稳定性验证。
- Phase 1B 必须只使用 normalized PIT-valid rows，不得使用 excluded tail rows。
- `available_at = next_trading_day(trade_date)` 可继续作为 conservative visibility proxy，但报告中必须继续声明它不是官方发布时间证明。

## 4. Token 与凭证审查

说明文件没有写入 token 原文。

审查结论：

- token 不得写入 Markdown、CSV、JSON、日志、脚本或命令行记录。
- 后续报告只允许记录 `token_used=True/False` 这类布尔审计字段。
- 不需要在后续 Phase1B 再次展示或复述 token。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：存在 Scrapling 流程沟通缺口，但不是只读安全问题。

### Network Audit

本说明不联网、不重拉。Phase 0E 的联网已经限定为授权 FinMind API endpoint；本次说明未新增任何联网行为。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor 写入、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

未出现真实买入/卖出建议、自动交易、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 6. 审查者裁决

- Scrapling 未使用原因：合理。
- 是否要求 Scrapling 重拉：否。
- 是否要求 Scrapling parity backfill：否。
- Phase 0E 数据是否继续可用：是。
- 是否发现偏离主线：否。
- 是否发现新增分支：否。
- 是否允许进入下一步：允许进入受限 Phase 1B。

## 7. 给执行者的 Phase 1B 工作文档

### 7.1 阶段目标

基于 Phase 0E 的 normalized PIT archive，构建扩展窗口的只读研究样本，验证法人筹码与融资融券特征是否在更长时间、更大 universe 下仍具有独立增量信号。

Phase 1B 仍是验证阶段，不是模型阶段，也不是规则上线阶段。

### 7.2 输入限制

只允许使用：

- `data_tw/experiments/decision_orthogonal/phase0e_pit_snapshot_manifest.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_coverage_report.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_quality_flags_summary.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_raw_archive/` 中已经 PIT-normalized 且 `available_at` 非空的数据
- 本地已有 qlib ranking/score、价格、行业或 universe artifacts

禁止使用：

- Phase 0E excluded tail rows。
- 新联网下载数据。
- 月营收数据。
- 新数据源。
- 全市场补齐。
- Qlib bin/provider 写入。
- provider refresh/publish。
- accepted latest switching。

### 7.3 必做验证

执行者需要产出 Phase 1B 报告，至少覆盖：

1. 样本构建口径
   - asof 范围。
   - symbol 数。
   - 每月样本量。
   - Top50 与 Top150 子集样本量。
   - `available_at <= asof` 的 PIT 可见性断言。

2. 标签
   - fwd 5d / 10d / 20d excess return。
   - 标签必须来自本地已有价格数据。
   - 不允许使用未来不可见特征。

3. 特征
   - 法人净买超相关字段。
   - 投信、外资、自营商与合计字段的 rolling sum / rolling zscore / rank 特征。
   - 融资余额、融券余额及其变化相关 rolling/rank 特征。
   - 明确每个特征的 `available_at` 对齐方式。

4. 单因子与分段稳定性
   - RankIC / IC。
   - coverage。
   - hit-rate 仅可作为历史统计，不得写成胜率承诺。
   - 按年度分段。
   - 按月份或季度分段。
   - 若本地已有市场状态/波动分组，可做 regime 分段；没有则不要新造复杂 regime 分支。

5. 与 qlib 排名的关系
   - 使用本地已有 qlib ranking/score artifacts。
   - 计算正交特征与 qlib score 的相关性。
   - 比较 qlib TopN 内外的特征表现。
   - 目标是判断是否有增量研究价值，不得形成交易建议。

6. 泄露审计
   - 证明所有 feature rows 均满足 `available_at <= asof`。
   - 报告违反行数，期望为 0。
   - 检查同日 `trade_date` 不能在同日 asof 可见。
   - 明确 T+1 是 conservative proxy。

### 7.4 允许产物

允许新增：

- `docs/tw_decision_model_orthogonal/PHASE1B_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/decision_orthogonal/phase1b_*`
- 如确有必要，可新增只读分析脚本，例如 `examples/tw/decision_orthogonal_phase1b_analysis.py` 或 `scripts/analyze_tw_decision_orthogonal_phase1b.py`

新增脚本必须只读输入数据，只写 Phase1B 专用实验输出。

### 7.5 明确禁止事项

- 禁止联网。
- 禁止重拉 Phase 0E。
- 禁止要求或写入 token。
- 禁止 Scrapling parity backfill。
- 禁止新增数据源。
- 禁止月营收。
- 禁止全市场补齐。
- 禁止 materialize derived features 到生产目录。
- 禁止 Qlib bin/provider 写入。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止模型训练。
- 禁止规则 baseline。
- 禁止 Phase 2。
- 禁止前端/API。
- 禁止 monitor config save、monitor scan、alerts write。
- 禁止 broker、orders、quick-trade、target position、target weight。
- 禁止买入/卖出建议、收益承诺、上涨概率承诺。

### 7.6 Phase 1B Gate

Phase 1B 完成后不得自动进入 Phase 2。报告必须给出以下结论之一：

- `request_phase2_rules_baseline=true`：仅当扩展窗口下至少有一个筹码/融资融券特征在多个分段中稳定、与 qlib score 低到中等相关、且泄露审计为 0 时允许提出。
- `request_more_data_or_repair=true`：若样本覆盖、字段质量或分段稳定性不足。
- `stop_orthogonal_direction=true`：若扩展窗口证据显示信号不可用或高度不稳定。

即使 `request_phase2_rules_baseline=true`，也必须等待审查者审查，不得自行进入 Phase 2。
