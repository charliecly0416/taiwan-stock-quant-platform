# Phase F0B Monthly Revenue POC 审查结论与 Source Redesign 工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_decision_model_fundamental/PHASEF0B_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/tw_decision_model_fundamental/PHASEF0_REVIEW_AND_F0B_AUTHORIZATION_WORK_CN.md`
- `docs/tw_decision_model_fundamental/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_FUNDAMENTAL_PIT_NEW_MAINLINE_PLAN_CN.md`

审查产物：

- `scripts/build_tw_decision_fundamental_phasef0b_monthly_revenue_poc.py`
- `data_tw/experiments/decision_fundamental/phasef0b_monthly_revenue_raw_archive.jsonl`
- `data_tw/experiments/decision_fundamental/phasef0b_monthly_revenue_normalized_pit.csv`
- `data_tw/experiments/decision_fundamental/phasef0b_pit_validation_samples.csv`
- `data_tw/experiments/decision_fundamental/phasef0b_coverage_summary.json`
- `data_tw/experiments/decision_fundamental/phasef0b_gate_summary.json`
- `docs/tw_decision_model_fundamental/PHASEF0B_EXECUTION_REPORT_CN.md`

## 1. 本步审核结论

Phase F0B 技术执行范围基本符合受限 POC 目标，只读研究安全边界通过。

执行者没有进入 F1，也没有新增模型或产品分支：

- 只拉取 FinMind `TaiwanStockMonthRevenue` 小范围样本。
- 未拉估值/财报。
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

但 Phase F0B 结果没有通过 PIT gate：

- raw rows：`300`
- normalized PIT rows：`0`
- strict PIT valid：`false`
- explicit announcement field found：`false`
- provider date candidate field found：`true`
- missing announcement_date count：`300`
- missing available_at count：`300`
- excluded reason：`missing_explicit_announcement_date=300`

结论：

- 不允许进入 F1。
- 不允许构建样本。
- 不允许训练模型。
- 不接受 FinMind `date` 自动等同公告日。
- 接受 `recommended_gate=phasef0b_needs_source_redesign=true`。

## 2. 主线一致性审查

通过项：

- F0B 没有把 provider `date` 直接包装为 `announcement_date`。
- F0B 没有使用 period-only join。
- F0B 将 raw archive 与 normalized PIT 分开。
- F0B 在 normalized PIT 中只保留表头，未生成不可审计 PIT 行。
- F0B 明确写出当前不进入 F1。

需要记录的流程风险：

- 上一轮审查文件要求 F0B 必须在用户授权后执行。当前本地报告能证明执行了联网/token，但不能从文件本身证明授权来源。
- 若用户已经在执行者侧单独授权，则技术范围可接受。
- 若未授权，则这是流程偏离；后续任何 source redesign 必须先由用户明确确认。

## 3. PIT 与数据审查

### 3.1 FinMind 字段审查

FinMind 返回字段：

- `country`
- `create_time`
- `date`
- `revenue`
- `revenue_month`
- `revenue_year`
- `stock_id`

审查判断：

- `revenue_year` + `revenue_month` 可以形成 `source_period`。
- `date` 只能视为 provider date candidate，不能自动视为公告日。
- `create_time` 不能直接视为历史公告日；它可能是 provider create/update metadata，且缺失或不稳定。
- 响应中没有明确 `announcement_date`、`announce_date`、`disclosure_date`、`published_date` 或等价字段。

因此 FinMind `TaiwanStockMonthRevenue` 当前响应不满足 Phase F1 的 PIT 要求。

### 3.2 Raw archive 审查

raw archive 通过：

- 保留 `source_period`。
- 保留 `raw_snapshot_id`。
- 保留 `data_source`。
- 保留 `raw_payload_hash`。
- 保留 `provider_date_candidate`。
- 对所有 row 标记 `missing_explicit_announcement_date` 与 `provider_date_candidate_not_accepted_as_announcement`。

### 3.3 Normalized PIT 审查

normalized PIT 通过：

- 只有表头，没有误生成 PIT 行。
- 这与 strict PIT 规则一致。

### 3.4 Validation samples 审查

validation samples 通过：

- 所有样本均为 fail。
- fail 原因清楚：`strict PIT requires explicit announcement/disclosure field; provider date candidate is not accepted automatically`。

## 4. 指标/样本/模型审查

Phase F0B 没有构建样本、没有计算未来收益标签、没有做单因子检验、没有规则 baseline、没有训练模型。

通过。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无。

### Network Audit

F0B 使用了网络和 token，这属于 F0B POC 需要用户授权的动作。技术产物未显示 provider 写入、accepted latest switching、前端/API 或交易路径。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

报告没有输出买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 6. 必须修复项

本轮不要求修复 FinMind POC 产物。

必须修正的方向判断：

- 不得继续用 FinMind `date` 或 `create_time` 作为公告日 proxy。
- 不得用 `source_period` 直接 join。
- 不得进入 F1。
- 不得为了进入 F1 调松 strict PIT 规则。

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

需要。

原因：

- 下一步 source redesign 需要新的官方披露源或额外数据源验证。
- 这会涉及联网。
- 可能需要新增脚本。
- 可能需要写新的独立 raw archive。

在用户确认前，执行者必须停止，不得执行 Source Redesign。

## 9. 后续方向建议

建议方向：Phase F0C Source Redesign Proposal / Official Disclosure POC。

目标不是继续 FinMind 调参，而是验证是否存在可审计公告日来源。

优先级：

1. 官方 MOPS / TWSE / TPEx 月营收公告或公开资讯观测站来源。
2. 若官方源可提供公告日或发布时间，再与 FinMind 月营收值做字段对齐。
3. 若官方源不可用或没有可审计公告时间，则 fundamental 主线停止。

不建议方向：

- 不建议接受 FinMind `date` 为公告日。
- 不建议用 FinMind `create_time` 为公告日。
- 不建议继续扩大 FinMind 样本。
- 不建议进入 F1。

## 10. 给执行者的下一步工作文档：等待用户授权 / Phase F0C Source Redesign

### 10.1 当前状态

当前 gate：

- `phasef0b_needs_source_redesign=true`
- `phasef1_allowed=false`
- `model_training_allowed=false`
- `provider_write_allowed=false`
- `accepted_latest_switching_allowed=false`
- `frontend_api_allowed=false`
- `trading_or_order_allowed=false`

执行者在用户授权前必须停止。

### 10.2 若用户未授权

执行者只能待命。

不得：

- 继续联网。
- 继续拉 FinMind。
- 改用 provider date。
- 构建 F1 样本。
- 训练模型。
- 写 provider。
- 接前端/API。

### 10.3 若用户授权 Phase F0C

Phase F0C 只允许做 Source Redesign / Official Disclosure POC。

目标：

- 找到官方或可审计来源的月营收公告日期。
- 验证 row-level `announcement_date` 是否可得。
- 设计与 FinMind 月营收值对齐的 PIT archive 方案。
- 如果找不到公告日期，给出停止 fundamental 主线的结论。

允许新增：

- `scripts/probe_tw_decision_fundamental_phasef0c_official_disclosure.py`
- `docs/tw_decision_model_fundamental/PHASEF0C_SOURCE_REDESIGN_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/decision_fundamental/phasef0c_official_disclosure_probe_raw.*`
- `data_tw/experiments/decision_fundamental/phasef0c_official_disclosure_field_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0c_source_redesign_summary.json`

### 10.4 F0C 范围限制

数据范围：

- 只允许月营收公告/披露日期探测。
- 不拉财报。
- 不拉估值。
- 不做全市场回填。
- 先用 F0B 的 10 个 symbol 做 smoke。
- 时间范围仍限制为 `2024-01-01` 至 `2026-06-11`。

写入范围：

- 只能写 `data_tw/experiments/decision_fundamental/phasef0c_*`。
- 不得写 provider。
- 不得 materialize 到 qlib。
- 不得切 accepted latest。

### 10.5 F0C 必须回答

必须回答：

- 官方源是否存在。
- 是否可以按 symbol / source_period 查到公告日。
- 是否有 row-level `announcement_date`。
- 是否有发布时间或可审计日期。
- 是否可以生成 `available_at`。
- 是否能与 FinMind `stock_id + revenue_year + revenue_month` 对齐。
- 是否存在修订或重复公告。
- raw snapshot 如何保存。
- 若官方源需要复杂爬取或权限，是否值得继续。

### 10.6 F0C Gate

F0C 完成后推荐 gate 只能是：

- `request_phasef0d_official_archive_poc=true`
- `stop_fundamental_mainline_no_pit_source=true`
- `phasef0c_needs_user_decision=true`

允许继续的最低条件：

- 官方或可审计来源能给出 row-level `announcement_date`。
- `announcement_date` 能与 `symbol + source_period` 对齐。
- 能生成可审计 `available_at`。
- 不依赖 FinMind `date` 或 `create_time` 作为公告日。

### 10.7 F0C 禁止事项

F0C 禁止：

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

完成后等待审查者审核，不得自动进入 F1 或 F0D。
