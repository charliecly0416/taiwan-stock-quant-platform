# Phase F0C Source Redesign 审查结论与用户决策工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_decision_model_fundamental/PHASEF0C_SOURCE_REDESIGN_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/tw_decision_model_fundamental/PHASEF0B_REVIEW_AND_SOURCE_REDESIGN_WORK_CN.md`
- `docs/tw_decision_model_fundamental/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_FUNDAMENTAL_PIT_NEW_MAINLINE_PLAN_CN.md`

审查产物：

- `scripts/probe_tw_decision_fundamental_phasef0c_official_disclosure.py`
- `data_tw/experiments/decision_fundamental/phasef0c_official_disclosure_probe_raw.jsonl`
- `data_tw/experiments/decision_fundamental/phasef0c_official_disclosure_field_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0c_source_redesign_summary.json`
- `docs/tw_decision_model_fundamental/PHASEF0C_SOURCE_REDESIGN_EXECUTION_REPORT_CN.md`

## 1. 本步审核结论

Phase F0C 技术执行范围符合 Source Redesign / Official Disclosure POC 目标，只读研究安全边界通过。

执行者没有进入 F1，也没有新增模型或产品分支：

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

但 Phase F0C 没有找到可用 PIT 官方来源：

- `official_source_exists=false`
- `response_tables_found=0`
- `security_blocked_pages=6`
- `row_level_announcement_date_found=false`
- `matched_symbol_rows=0`
- `can_generate_available_at=false`
- `can_align_with_finmind_symbol_period=false`

结论：

- 不允许进入 F1。
- 不允许构建样本。
- 不允许训练模型。
- 不允许放宽 PIT 规则。
- 接受 `recommended_gate=phasef0c_needs_user_decision=true`。

## 2. 主线一致性审查

通过项：

- F0C 没有继续扩大 FinMind 样本。
- F0C 没有把 MOPS 页面层级信息伪装成 row-level 公告日。
- F0C 没有在安全拦截页上做错误解析。
- F0C 没有绕过 strict PIT。
- F0C 明确说明当前不能进入 F1。

未发现新增分支。

流程风险：

- F0C 涉及联网和官方页面探测。上一轮审查要求用户授权后才能执行。
- 本轮技术产物没有显示 provider、模型或交易风险，但后续任何继续联网探测都必须重新取得用户确认。

## 3. PIT 与数据审查

### 3.1 官方源探测审查

执行者探测了 MOPS `ajax_t21sc03`：

- 月份：`2024-01`、`2025-01`、`2026-05`
- 市场：`sii`、`otc`
- 页面数：`6`
- HTTP status：均为 `200`
- 但返回内容均为安全拦截页。

审查判断：

- 这不能证明官方源不存在。
- 只能证明当前请求路径在当前环境下没有取得有效表格。
- 当前没有 row-level `announcement_date`。
- 当前没有可审计 `available_at`。

### 3.2 Raw probe 审查

raw probe 通过：

- 保存了请求 URL。
- 保存了 HTTP status。
- 保存了安全拦截文本摘要。
- 保存了 `text_sha256`。
- 没有把安全拦截页解析为有效表格。

### 3.3 Field inventory 审查

field inventory 通过：

- 所有 probe 行均标记 `security_blocked=true`。
- 所有 probe 行均标记 `table_found=false`。
- 所有 probe 行均标记 `has_row_level_announcement_column=false`。
- 所有 probe 行均标记 `pit_join_safe=false`。

## 4. 指标/样本/模型审查

Phase F0C 没有构建样本、没有计算未来收益标签、没有做单因子检验、没有规则 baseline、没有训练模型。

通过。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无。

### Network Audit

F0C 使用了网络探测 MOPS 官方候选入口。技术产物未显示 provider 写入、accepted latest switching、前端/API 或交易路径。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

报告没有输出买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 6. 必须修复项

本轮 F0C 产物无必须修复项。

必须修正的方向判断：

- 不得进入 F1。
- 不得用 FinMind `date` 或 `create_time` 作为公告日 proxy。
- 不得用 MOPS 安全拦截页推断官方源可用。
- 不得为了进入 F1 放宽 strict PIT。

## 7. 可暂缓项

继续暂缓：

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

需要用户确认。

原因：

- 当前 F0C 没有找到 PIT-valid 官方源。
- 若继续，需要更强的官方源探测方式，例如浏览器态请求、Scrapling、手动官方下载或其他 TWSE/TPEx/MOPS 下载路径。
- 这仍涉及联网、可能新增脚本、可能写新的独立 raw probe/archive。

在用户确认前，执行者必须停止。

## 9. 后续方向判断

当前有两个合理方向：

### 方向 A：停止 fundamental 主线

适用条件：

- 用户不希望继续投入官方源探测。
- 用户不接受增加复杂度。
- 用户坚持没有 row-level 公告日就不继续。

结论：

- `stop_fundamental_mainline_no_pit_source=true`
- 转入此前计划中的“人工复盘解释模块 proposal”，但也必须另写 proposal 并经用户确认。

### 方向 B：授权 Phase F0D Official Source Access Repair

适用条件：

- 用户愿意再做一次非常受限的官方源访问修复。
- 目标仍然只限月营收公告日。
- 不进入 F1，不训练模型。

允许尝试：

- Scrapling 或浏览器态请求 MOPS/TWSE/TPEx 月营收页面。
- 官方 CSV/HTML 下载路径探测。
- 手动下载样例文件的 schema 审计。
- 对 F0B 10 个 symbol、3 个月份继续 smoke。

不允许：

- 全市场回填。
- 批量历史下载。
- 接受 FinMind date proxy。
- 构建 F1 样本。
- 训练模型。

## 10. 给执行者的下一步工作文档：等待用户决策

### 10.1 当前状态

当前 gate：

- `phasef0c_needs_user_decision=true`
- `phasef1_allowed=false`
- `model_training_allowed=false`
- `provider_write_allowed=false`
- `accepted_latest_switching_allowed=false`
- `frontend_api_allowed=false`
- `trading_or_order_allowed=false`

执行者在用户决策前必须停止。

### 10.2 若用户选择停止

执行者不得继续 fundamental 数据源探测。

下一步只能等待审查者另行给出“人工复盘解释模块 proposal”工作文档。

### 10.3 若用户授权 Phase F0D

Phase F0D 只能做 Official Source Access Repair。

目标：

- 修复官方月营收来源访问方式。
- 验证是否能取得有效表格。
- 验证是否存在 row-level `announcement_date` 或严格可审计日期。
- 若仍没有公告日，停止 fundamental 主线。

允许新增：

- `scripts/probe_tw_decision_fundamental_phasef0d_official_access_repair.py`
- `docs/tw_decision_model_fundamental/PHASEF0D_OFFICIAL_ACCESS_REPAIR_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/decision_fundamental/phasef0d_official_access_raw.*`
- `data_tw/experiments/decision_fundamental/phasef0d_official_access_field_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0d_gate_summary.json`

### 10.4 F0D 范围限制

数据范围：

- 只允许月营收公告/披露日期。
- 不拉财报。
- 不拉估值。
- 不做全市场回填。
- 仍限制 F0B 10 个 symbol。
- 仍限制少量月份 smoke。

访问方式：

- 可以尝试 Scrapling 或浏览器态请求。
- 可以探测官方下载路径。
- 可以读取用户手动放入工作区的官方样例文件。

写入范围：

- 只能写 `data_tw/experiments/decision_fundamental/phasef0d_*`。
- 不得写 provider。
- 不得 materialize 到 qlib。
- 不得切 accepted latest。

### 10.5 F0D Gate

F0D 完成后推荐 gate 只能是：

- `request_phasef1_pit_sample_work=true`
- `stop_fundamental_mainline_no_pit_source=true`
- `phasef0d_needs_user_decision=true`

允许进入 F1 的最低条件：

- 取得有效官方表格或等价官方数据文件。
- 存在 row-level `announcement_date`，或存在可严格证明的 `symbol + source_period` 可见日期。
- 能生成可审计 `available_at`。
- 能与 FinMind 或官方月营收数值按 `symbol + source_period` 对齐。
- 不依赖 FinMind `date` 或 `create_time`。

### 10.6 F0D 禁止事项

F0D 禁止：

- 接受 FinMind `date` 为公告日。
- 接受 FinMind `create_time` 为公告日。
- period-only join。
- 全市场回填。
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
