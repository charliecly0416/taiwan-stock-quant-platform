# Phase R0 Baseline 审查结论与 Phase R0 工作文档

审查日期：2026-06-11

审查入口：

- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_MODULE_PLAN_CN.md`
- `docs/tw_manual_review_explanation/REVIEWER_PROMPT_CN.md`

关联依据：

- `docs/tw_decision_model_orthogonal/PHASE2D_CLOSURE_REVIEW_AND_STANDBY_WORK_CN.md`
- `docs/tw_decision_model_fundamental/PHASEF0E_REVIEW_AND_FUNDAMENTAL_STOP_CN.md`
- `docs/tw_manual_review_explanation/EXECUTOR_PROMPT_CN.md`

## 1. 本步审核结论

允许开启台股人工复盘解释模块 Phase R0。

当前只授权执行者做：

- proposal。
- explanation contract。
- 输入来源盘点。
- 安全边界声明。

不允许执行者做：

- 后端业务服务。
- API。
- 前端。
- 模型训练。
- 新数据源。
- 联网。
- token。
- provider refresh/publish。
- accepted latest switching。
- monitor config save。
- monitor scan。
- alerts write。
- broker、quick-trade、orders。
- target position / target weight。
- 买入/卖出建议。
- 收益承诺。
- 上涨概率承诺。

## 2. 主线一致性审查

本模块是新产品化方向，但不是模型或数据源探索方向。

必须遵守：

- 不是 Entry Model v1 复活。
- 不是正交规则 Phase2E。
- 不是 fundamental F0F/F1。
- 不是 Risk Filter Model。
- 不是自动 gate。
- 不是交易建议。

可继承的只有人工解释材料：

- qlib rank / score / TopN 研究排名。
- QuantDinger trend / 技术状态 / 价格位置风险。
- 已冻结的法人/融资融券规则卡。

不可继承为模型或 gate：

- `margin_crowding_top50_p85_caution`
- `flow_crowding_conflict_top50_p80_weak30_review`
- `foreign_flow_non_crowded_top150_explanation`
- `margin_change_non_crowded_top150_auxiliary`

这些规则只能作为人工复盘线索，不得升级为 confirmed watch、自动风险过滤、模型训练 gate 或买卖判断。

## 3. 输入/输出 Contract 基线

Phase R0 必须设计 contract，但不得实现业务逻辑。

### 3.1 允许输入

允许盘点但不实际接入：

- qlib rank / score / rank tier。
- QuantDinger trend。
- 技术状态。
- 价格位置风险。
- 冻结规则卡。
- 数据不足状态。

Fundamental 月营收/基本面禁止作为输入：

- fundamental PIT 主线已在 Phase F0E 停止。
- 不得继续搜索月营收数据源。
- 不得使用 TWSE current single-period file。
- 不得使用 FinMind `date/create_time` proxy。

### 3.2 输出 contract 必须满足

允许字段：

- `symbol`
- `name`
- `asof`
- `overall_status`
- `status_label`
- `confidence`
- `summary`
- `signals`
- `next_review_focus`
- `research_only`
- `not_trading_advice`
- `data_quality_notes`

`overall_status` 只允许：

- `multi_source_support`
- `manual_review`
- `caution`
- `conflict`
- `data_insufficient`

`signals.type` 只允许：

- `support`
- `risk`
- `conflict`
- `background`
- `data_quality`

`signals.severity` 只允许：

- `info`
- `watch`
- `caution`
- `review`

禁止字段或语义：

- `buy`
- `sell`
- `hold`
- `strong_buy`
- `target_position`
- `target_weight`
- `order_ready`
- `expected_return`
- `return_forecast`
- `upside_probability`
- `win_rate`
- `auto_trade`
- `broker`

## 4. 用户第一性原则审查

Phase R0 contract 必须符合：

- 简单：最多 3 到 5 条关键线索，不展示工程指标堆叠。
- 准确：不得把 qlib rank、趋势、技术状态或冻结规则卡说成预测结论。
- 清晰：必须区分 support、risk、conflict、background、data_quality。
- 实用：输出要帮助人工复盘，不替用户决策。

禁止在用户可见文案中出现：

- gate。
- IC / RankIC。
- model training。
- provider。
- accepted latest。
- raw rule id。
- 复杂 run id。
- 收益率承诺。
- 上涨概率。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无。

### Network Audit

Phase R0 不允许联网、token 或新增数据源。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

本工作文档只定义人工复盘解释模块，不包含买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 6. 必须修复项

当前是启动审查，无执行产物需要修复。

Phase R0 执行者必须避免：

- contract 出现交易字段。
- contract 出现收益或概率字段。
- contract 出现模型 gate 字段。
- 输入来源包含 fundamental 月营收。
- 输入来源包含新数据源。
- proposal 暗示可以直接接 API 或前端。

## 7. 可暂缓项

Phase R0 暂缓：

- 后端服务实现。
- API。
- 前端。
- 测试。
- Playwright。
- 数据库写入。
- provider。
- 模型。
- 新数据源。
- 月营收。
- 任何交易路径。

## 8. 是否需要用户确认

当前不需要用户确认。

理由：

- 用户已明确要求开启人工复盘解释模块审查。
- Phase R0 只做 proposal、contract、输入来源盘点。
- 不涉及联网、token、API、前端、模型、provider 或交易语义。

如果执行者认为 R0 需要接 API、前端、联网、新数据源、模型训练或改变模块定位，必须停止并回报。

## 9. 给执行者的下一步工作文档：Phase R0 Proposal 与 Contract

### 9.1 目标

设计人工复盘解释模块的 proposal 与 contract，明确输入来源、输出 schema、文案边界和安全边界。

Phase R0 不写业务服务，不接 API，不接前端。

### 9.2 必读输入

必须读取：

- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_MODULE_PLAN_CN.md`
- `docs/tw_manual_review_explanation/REVIEWER_PROMPT_CN.md`
- `docs/tw_manual_review_explanation/EXECUTOR_PROMPT_CN.md`
- `docs/tw_manual_review_explanation/PHASER0_REVIEW_BASELINE_AND_NEXT_WORK_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE2D_CLOSURE_REVIEW_AND_STANDBY_WORK_CN.md`
- `docs/tw_decision_model_fundamental/PHASEF0E_REVIEW_AND_FUNDAMENTAL_STOP_CN.md`

### 9.3 允许产物

必须新增：

- `docs/tw_manual_review_explanation/PHASER0_EXECUTION_REPORT_CN.md`
- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `data_tw/experiments/manual_review_explanation/phaser0_input_source_inventory.csv`
- `data_tw/experiments/manual_review_explanation/phaser0_contract_summary.json`

如确有必要，可新增只读盘点脚本：

- `scripts/audit_tw_manual_review_explanation_phaser0.py`

脚本只能读本地文件和本地目录，只能写 Phase R0 专用 inventory / summary / report。

### 9.4 Input source inventory 要求

`phaser0_input_source_inventory.csv` 至少包含：

- `input_group`
- `candidate_field`
- `source_path_or_service`
- `allowed_for_r0_contract`
- `allowed_for_future_r1_service`
- `reason`
- `risk`
- `required_guardrail`
- `status`

`status` 只允许：

- `allow_contract_only`
- `allow_future_readonly_service`
- `defer_no_source`
- `defer_too_complex`
- `reject_failed_mainline`
- `reject_trading_semantics`
- `reject_new_data_source`

### 9.5 Contract 文档要求

`manual_review_explanation_contract.md` 必须包含：

1. 模块定位。
2. 输入来源清单。
3. 输出 JSON schema。
4. `overall_status` 允许值。
5. `signals` 允许值。
6. 文案示例。
7. 禁止文案示例。
8. 安全边界。
9. 数据不足处理。
10. R1 服务实现边界。

### 9.6 Contract summary 要求

`phaser0_contract_summary.json` 必须包含：

- `phase`
- `generated_at`
- `business_service_written=false`
- `api_written=false`
- `frontend_written=false`
- `network_used=false`
- `token_used=false`
- `new_data_source=false`
- `model_training=false`
- `provider_write=false`
- `accepted_latest_switching=false`
- `trading_or_order=false`
- `contract_has_trading_semantics=false`
- `contract_has_return_or_probability_semantics=false`
- `fundamental_inputs_allowed=false`
- `frozen_rules_as_gate_allowed=false`
- `recommended_gate`
- `gate_reason`

`recommended_gate` 只能是：

- `request_phaser1_readonly_service_work`
- `phaser0_contract_needs_repair`
- `stop_manual_review_module_scope_invalid`

### 9.7 Phase R0 执行报告必须回答

报告必须包含：

- 当前阶段目标。
- 执行范围。
- 修改文件。
- 生成文件。
- 输入来源盘点摘要。
- 输出 contract 摘要。
- 是否出现交易语义。
- 是否出现收益/概率语义。
- 是否误用冻结规则卡。
- 是否继续 fundamental 或正交失败主线。
- 是否联网/token/新数据源。
- 安全边界检查。
- 推荐 gate 与理由。
- 风险与待审查问题。

### 9.8 禁止事项

Phase R0 禁止：

- 写后端业务服务。
- 写 API。
- 写前端。
- 写数据库。
- 联网。
- 使用 token。
- 新增数据源。
- 继续月营收。
- 继续正交 Phase2E。
- 复活 Entry Model。
- 训练模型。
- 写 provider。
- provider refresh/publish。
- accepted latest switching。
- monitor config save。
- monitor scan。
- alerts write。
- broker、quick-trade、orders。
- target position / target weight。
- 输出买入/卖出建议。
- 输出收益承诺。
- 输出上涨概率承诺。

完成后等待审查者审核，不得自动进入 R1。
