# Phase F0D Official Source Access Repair 审查结论与 Phase F0E 工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_decision_model_fundamental/PHASEF0D_OFFICIAL_ACCESS_REPAIR_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/tw_decision_model_fundamental/PHASEF0C_REVIEW_AND_USER_DECISION_WORK_CN.md`
- `docs/tw_decision_model_fundamental/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_FUNDAMENTAL_PIT_NEW_MAINLINE_PLAN_CN.md`

审查产物：

- `scripts/probe_tw_decision_fundamental_phasef0d_official_access_repair.py`
- `data_tw/experiments/decision_fundamental/phasef0d_official_access_raw.jsonl`
- `data_tw/experiments/decision_fundamental/phasef0d_official_access_field_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0d_gate_summary.json`
- `docs/tw_decision_model_fundamental/PHASEF0D_OFFICIAL_ACCESS_REPAIR_EXECUTION_REPORT_CN.md`

## 1. 本步审核结论

Phase F0D 主线范围通过，只读研究安全边界通过。

执行者没有偏离主线，也没有新增模型或产品分支：

- 未接受 FinMind `date` 或 `create_time` 为公告日。
- 未使用 period-only join。
- 未全市场回填。
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

F0D 有一个有效突破：

- TWSE 上市 OpenAPI `t187ap05_L` 可访问。
- 返回 JSON 行级资料。
- 字段包含 `出表日期`、`資料年月`、`公司代號`、`營業收入-當月營收`。
- F0B 10 个 symbol 中 9 个上市 symbol 被覆盖。
- `pit_valid_rows=9`。
- `aligned_rows=9`。
- 官方金额从仟元归一为 NTD 后与本地 F0B FinMind raw archive 数值一致。

但 F0D 不足以进入 F1：

- 只验证到当前公开 `資料年月=2026-04`。
- 未验证历史月份 archive/download 路径。
- TPEx/OTC 仍被阻挡或不可访问。
- F0B 10 个 symbol 中 `6187` 未覆盖。
- 当前样本太窄，不足以做单因子检验。

Gate 结论：

- 接受 `recommended_gate=phasef0d_needs_user_decision=true`。
- 不允许进入 F1。
- 建议进入受限 Phase F0E：TWSE-only official monthly revenue coverage diagnosis。

## 2. 主线一致性审查

通过项：

- F0D 继续围绕月营收公告日，不扩展到财报/估值。
- F0D 使用官方 OpenAPI，不依赖 FinMind 日期 proxy。
- F0D 只做访问修复和数值对齐，不构建样本。
- F0D 记录了 TPEx/OTC 仍受阻这一限制。
- F0D 没有把 9 行 current-month 证据夸大为可进入 F1。

未发现偏离主线或新增分支。

## 3. PIT 与数据审查

### 3.1 TWSE OpenAPI 审查

TWSE `https://openapi.twse.com.tw/v1/opendata/t187ap05_L` 返回有效资料：

- `row_count=1078`
- `matched_symbol_rows=9`
- `pit_valid_rows=9`
- `aligned_rows=9`
- `source_periods=2026-04`

审查判断：

- `出表日期` 可作为官方 row-level 日期候选。
- `資料年月` 可作为 `source_period`。
- `公司代號` 可作为 `symbol`。
- `營業收入-當月營收` 可作为月营收值，原始单位为仟元。
- 与 F0B 本地 FinMind raw archive 数值对齐通过。

### 3.2 available_at 审查

F0D 将 `available_at` 设为 `announcement_date`。

审查判断：

- 作为 POC 可记录，但进入样本前还需要在 F0E/F1 工作文档中明确交易日可见性规则。
- 如果无法证明公告是在交易前可见，后续样本应使用更保守规则，例如 next trading day。
- 当前不能直接用这个 POC available_at 进入 F1。

### 3.3 覆盖缺口审查

缺口：

- 只有上市 TWSE。
- TPEx/OTC 403 / Cloudflare 阻挡。
- 只拿到当前公开資料年月。
- 没有历史月份。
- 10 个 symbol 中 `6187` 未覆盖。

审查判断：

- 这些缺口阻止进入 F1。
- 但已经足够支持一个更窄的 F0E coverage diagnosis，判断 TWSE-only 是否可作为后续最小主线。

## 4. 指标/样本/模型审查

Phase F0D 没有构建样本、没有计算未来收益标签、没有做单因子检验、没有规则 baseline、没有训练模型。

通过。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无。

### Network Audit

F0D 使用网络探测官方 OpenAPI，属于用户授权后的官方访问修复。技术产物未显示 provider 写入、accepted latest switching、前端/API 或交易路径。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

报告没有输出买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 6. 必须修复项

当前 F0D 产物无必须修复项。

但后续必须修正方向判断：

- 不得直接进入 F1。
- 不得将 current-month TWSE 9 行证据扩展为全市场或历史 PIT 成立。
- 不得忽略 TPEx/OTC 缺口。
- 不得使用 POC `available_at=announcement_date` 直接构建样本。

## 7. 可暂缓项

继续暂缓：

- TPEx/OTC 完整修复。
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

本轮后续有两种选择，需要用户确认。

选择 A：停止 fundamental 主线。

- 理由：官方 PIT 路径仍不完整，历史和 TPEx 缺口较大。

选择 B：授权 Phase F0E。

- 目标：只做 TWSE-only official monthly revenue coverage diagnosis。
- 仍不进入 F1。
- 仍不训练模型。
- 仍不写 provider。

如果用户未确认，执行者必须停止。

## 9. 后续方向建议

建议选择 B，但范围必须收窄：

- 不再追 TPEx/OTC。
- 不做全市场。
- 不做历史大回填。
- 只判断 TWSE OpenAPI 当前/可得月份是否能形成足够连续的 official monthly revenue PIT archive 方案。

原因：

- F0D 已证明 TWSE listed 当前 OpenAPI 有官方 `出表日期`。
- 这是到目前为止唯一真实 PIT 证据。
- 但必须先验证覆盖连续性，不能跳到 F1。

## 10. 给执行者的下一步工作文档：等待用户确认 / Phase F0E TWSE-only Coverage Diagnosis

### 10.1 当前状态

当前 gate：

- `phasef0d_needs_user_decision=true`
- `phasef1_allowed=false`
- `model_training_allowed=false`
- `provider_write_allowed=false`
- `accepted_latest_switching_allowed=false`
- `frontend_api_allowed=false`
- `trading_or_order_allowed=false`

执行者在用户确认前必须停止。

### 10.2 若用户选择停止

执行者不得继续 fundamental 数据源探测。

后续只能等待审查者另行给出“人工复盘解释模块 proposal”工作文档。

### 10.3 若用户授权 Phase F0E

Phase F0E 只能做 TWSE-only official monthly revenue coverage diagnosis。

目标：

- 验证 TWSE OpenAPI 是否只能返回当前月份，还是可通过参数或其它官方 listed OpenAPI 路径拿到历史月份。
- 评估 TWSE-only 子集对 qlib Top50/Top150 历史样本的覆盖。
- 设计若干不进入 F1 的 coverage 表和 gate summary。

允许新增：

- `scripts/diagnose_tw_decision_fundamental_phasef0e_twse_coverage.py`
- `docs/tw_decision_model_fundamental/PHASEF0E_TWSE_COVERAGE_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/decision_fundamental/phasef0e_twse_official_coverage_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0e_twse_symbol_coverage.csv`
- `data_tw/experiments/decision_fundamental/phasef0e_gate_summary.json`

### 10.4 F0E 范围限制

数据范围：

- 只允许 TWSE listed monthly revenue official OpenAPI / official download path。
- 不再追 TPEx/OTC。
- 不拉财报。
- 不拉估值。
- 不全市场回填到样本。
- 不构建 F1 样本。

可做：

- 读取 qlib Top50/Top150 历史涉及 symbol 列表。
- 只做 symbol 层覆盖率统计。
- 只做 OpenAPI 当前可得 source_period / field / schema 诊断。
- 若官方路径支持参数化历史下载，可只做 2-3 个月 smoke，不做完整历史回填。

写入范围：

- 只能写 `data_tw/experiments/decision_fundamental/phasef0e_*`。
- 不得写 provider。
- 不得 materialize 到 qlib。
- 不得切 accepted latest。

### 10.5 F0E 必须回答

必须回答：

- TWSE OpenAPI 当前可得的 `source_period`。
- 是否存在官方历史月份访问方式。
- 若有，是否同样包含 row-level `出表日期`。
- qlib Top50/Top150 历史涉及 symbol 中，TWSE listed 覆盖率是多少。
- 排除 TPEx/OTC 后样本是否仍可能足够。
- `available_at` 应采用公告日当天还是 next trading day。
- 若只支持当前月份，是否应停止 fundamental 主线。

### 10.6 F0E Gate

F0E 完成后推荐 gate 只能是：

- `request_phasef1_twse_only_pit_sample_work=true`
- `stop_fundamental_mainline_insufficient_coverage=true`
- `phasef0e_needs_user_decision=true`

允许进入 F1 的最低条件：

- TWSE-only 覆盖率对 qlib Top50/Top150 足够。
- 有连续多个 source_period 的 official row-level `出表日期`。
- 能生成保守 `available_at`。
- 能形成不依赖 FinMind date/create_time 的 PIT archive。

### 10.7 F0E 禁止事项

F0E 禁止：

- 追 TPEx/OTC 修复。
- 接受 FinMind `date` 为公告日。
- 接受 FinMind `create_time` 为公告日。
- period-only join。
- 构建 F1 样本。
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

完成后等待审查者审核，不得自动进入 F1。
