# Phase F0E TWSE-only Coverage Diagnosis 审查结论与 Fundamental 主线停止文档

审查日期：2026-06-11

审查入口：

- `docs/tw_decision_model_fundamental/PHASEF0E_TWSE_COVERAGE_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/tw_decision_model_fundamental/PHASEF0D_REVIEW_AND_PHASEF0E_WORK_CN.md`
- `docs/tw_decision_model_fundamental/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_FUNDAMENTAL_PIT_NEW_MAINLINE_PLAN_CN.md`

审查产物：

- `scripts/diagnose_tw_decision_fundamental_phasef0e_twse_coverage.py`
- `data_tw/experiments/decision_fundamental/phasef0e_twse_official_coverage_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0e_twse_symbol_coverage.csv`
- `data_tw/experiments/decision_fundamental/phasef0e_gate_summary.json`
- `docs/tw_decision_model_fundamental/PHASEF0E_TWSE_COVERAGE_EXECUTION_REPORT_CN.md`

## 1. 本步审核结论

Phase F0E 主线范围通过，只读研究安全边界通过。

执行者没有偏离主线，也没有新增模型或产品分支：

- 未追 TPEx/OTC 修复。
- 未接受 FinMind `date` 或 `create_time` 为公告日。
- 未使用 period-only join。
- 未构建 F1 样本。
- 未做单因子检验。
- 未做规则 baseline。
- 未训练模型。
- 未执行 Risk Filter Model。
- 未写 provider。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未 materialize 到 qlib。
- 未前端/API。
- 未 monitor 写入。
- 未触碰交易路径。

F0E 结论接受：

- TWSE OpenAPI 当前可得 `source_period=2026-04`。
- 当前 row-level `出表日期=2026-05-17` 存在。
- 参数化历史访问没有证明，所有参数化请求都返回同一个当前 payload。
- `historical_access_proven=false`。
- 不能形成连续 PIT archive。
- 不允许进入 F1。

Gate 结论：

- 接受 `recommended_gate=stop_fundamental_mainline_insufficient_coverage=true`。

本轮 fundamental PIT 主线应停止。

## 2. 主线一致性审查

通过项：

- F0E 只做 TWSE-only coverage diagnosis。
- 没有追 TPEx/OTC。
- 没有全市场回填。
- 没有构建样本。
- 没有训练模型。
- 没有把 current-month 单期证据夸大为历史 PIT 成立。
- 明确建议采用 `available_at = next_trading_day(announcement_date)` 作为后续保守规则，但没有实际构建样本。

未发现偏离主线或新增分支。

## 3. PIT 与数据审查

### 3.1 官方历史可得性

F0E 的官方访问诊断结果：

- `base_current` 返回 `2026-04`。
- `param_date_current_ad` 返回同一 payload。
- `param_date_prev_ad` 返回同一 payload。
- `param_yyyymm_prev_ad` 返回同一 payload。
- `param_roc_year_month_prev` 返回同一 payload。

审查判断：

- TWSE OpenAPI 当前文件有 row-level `出表日期`。
- 但没有证明历史月份可访问。
- 不能形成 2022-2026 或 2024-2026 的 PIT archive。
- 单一 source_period 不足以进入 F1 单因子检验。

### 3.2 TWSE-only 覆盖率

F0E 统计：

- `phase1b_repaired_full_top150` unique symbol coverage：`0.7864`，row-weighted coverage：`0.7972`
- `phase1b_repaired_full_top50` unique symbol coverage：`0.7864`，row-weighted coverage：`0.7940`
- `pred_fast_2023_top150` unique symbol coverage：`0.7173`，row-weighted coverage：`0.7680`
- `pred_fast_2023_top50` unique symbol coverage：`0.7199`，row-weighted coverage：`0.7568`

审查判断：

- TWSE-only 子集覆盖率不为 100%，但本身不构成停止主线的唯一原因。
- 真正阻塞是历史 source_period 不连续，无法形成 PIT 样本。
- 即使覆盖率尚可，也不能在只有当前月份的情况下进入 F1。

### 3.3 available_at 审查

F0E 建议：

- `available_at = next_trading_day(announcement_date)`
- 当前示例：`announcement_date=2026-05-17`，`next_trading_day=2026-05-18`

审查判断：

- 该建议正确且保守。
- 但由于历史月份不可得，当前不进入样本阶段。

## 4. 指标/样本/模型审查

Phase F0E 没有构建样本、没有计算未来收益标签、没有做单因子检验、没有规则 baseline、没有训练模型。

通过。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无。

### Network Audit

F0E 使用网络探测 TWSE official OpenAPI，属于此前受限 coverage diagnosis 范围。技术产物未显示 provider 写入、accepted latest switching、前端/API 或交易路径。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

报告没有输出买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 6. 必须修复项

当前 F0E 产物无必须修复项。

必须修正方向判断：

- 不得进入 F1。
- 不得继续开 F0F 搜索。
- 不得用单期 TWSE current file 生成样本。
- 不得接受 FinMind `date/create_time` proxy。
- 不得用 period-only join。

## 7. 可暂缓项

全部继续暂缓并关闭在本主线内：

- TPEx/OTC 修复。
- 财报/估值。
- 全市场回填。
- F1 样本。
- 单因子检验。
- 规则 baseline。
- 模型训练。
- 前端/API。
- provider/accepted latest。
- 任何交易路径。

## 8. 是否需要用户确认

当前不需要为 F0E 本身继续讨论。

原因：

- F0E 已给出停止 gate。
- 没有可执行的 F1 条件。
- 继续搜索会变成无边界数据源探索。

若用户希望继续官方历史月营收数据源探索，必须作为新主线重新定义目标、预算、数据源和停止条件，不能作为本 fundamental PIT 主线的自然延续。

## 9. 后续方向

按总计划，fundamental PIT 主线失败后，应转入“人工复盘解释模块 proposal”。

理由：

- 旧正交规则已有可冻结解释卡。
- fundamental 月营收没有形成 PIT-valid 历史样本。
- 继续 F0* 搜索不符合失败 gate。
- 当前最实用方向是把已有 qlib、趋势、技术、筹码/融资解释规则整理成人工复盘线索，而不是训练模型。

## 10. 给执行者的下一步工作文档：等待人工复盘解释模块 Proposal

### 10.1 当前状态

当前 gate：

- `stop_fundamental_mainline_insufficient_coverage=true`
- `fundamental_phasef1_allowed=false`
- `fundamental_model_training_allowed=false`
- `provider_write_allowed=false`
- `accepted_latest_switching_allowed=false`
- `frontend_api_allowed=false`
- `trading_or_order_allowed=false`

执行者不得继续 fundamental F0F/F1/F2/F3。

### 10.2 禁止事项

禁止：

- 继续搜索月营收数据源。
- 继续尝试 TPEx/OTC 修复。
- 构建 fundamental F1 样本。
- 单因子检验。
- 规则 baseline。
- 训练模型。
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

### 10.3 下一步只允许 Proposal

执行者下一步只允许等待审查者另行给出：

- 人工复盘解释模块 proposal 工作文档。

该 proposal 必须重新定义：

- 输入只读数据。
- 可用解释信号。
- 输出形态。
- 不输出交易建议的边界。
- 是否需要前端只读展示。
- 是否需要用户确认。

在审查者给出新工作文档前，执行者必须停止。
