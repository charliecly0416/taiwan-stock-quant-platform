# Phase R0 Proposal 与 Contract 审查结论与 Phase R1 工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_manual_review_explanation/PHASER0_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/tw_manual_review_explanation/PHASER0_REVIEW_BASELINE_AND_NEXT_WORK_CN.md`
- `docs/tw_manual_review_explanation/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_MODULE_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE2D_CLOSURE_REVIEW_AND_STANDBY_WORK_CN.md`
- `docs/tw_decision_model_fundamental/PHASEF0E_REVIEW_AND_FUNDAMENTAL_STOP_CN.md`

审查产物：

- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `docs/tw_manual_review_explanation/PHASER0_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/manual_review_explanation/phaser0_input_source_inventory.csv`
- `data_tw/experiments/manual_review_explanation/phaser0_contract_summary.json`

## 1. 本步审核结论

Phase R0 主线范围通过，只读研究安全边界通过。

执行者没有偏离主线，也没有新增分支：

- 只写 proposal / contract / 输入来源盘点。
- 未写后端业务服务。
- 未写 API。
- 未写前端。
- 未写数据库。
- 未联网。
- 未使用 token。
- 未新增数据源。
- 未继续月营收。
- 未继续正交 Phase2E。
- 未复活 Entry Model。
- 未训练模型。
- 未写 provider。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未 monitor 写入。
- 未触碰 broker、quick-trade、orders。

Gate 结论：

- 接受 `recommended_gate=request_phaser1_readonly_service_work`。

允许进入 Phase R1，但只允许实现后端只读服务层，不允许 API、前端、联网、数据库写入或任何交易语义。

## 2. 主线一致性审查

通过项：

- 模块定位清楚：人工复盘解释、只读研究、非交易建议、非模型训练、非自动 gate。
- 已明确拒绝 fundamental 月营收/基本面输入。
- 已明确拒绝单期 TWSE current file 与 FinMind `date/create_time` proxy。
- 冻结规则卡只允许作为人工 caution/review/background/auxiliary 线索。
- 没有把冻结规则卡升级为 confirmed watch、自动风险过滤、模型 gate 或交易判断。

未发现偏离主线或新增分支。

## 3. 输入/输出 Contract 审查

### 3.1 输入来源

允许进入未来 R1 只读服务的输入组：

- `qlib_rank`
- `trend`
- `technical_status`
- `position_risk`
- `frozen_orthogonal_rule_cards`
- `data_quality`

拒绝输入组：

- `fundamental_monthly_revenue`
- `new_external_data_source`
- `trading_semantics`

审查判断：

- inventory 符合 R0 要求。
- 输入边界足够清晰。
- 没有把失败主线重新引入当前模块。

### 3.2 输出 schema

输出对象 `manual_review_explanation` 字段通过：

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

`overall_status` 允许值通过：

- `multi_source_support`
- `manual_review`
- `caution`
- `conflict`
- `data_insufficient`

`signals.type` 与 `signals.severity` 允许值通过。

注意：

- `confidence` 只能表示解释完整度，不能在 R1 文案中解释成胜率、把握度或上涨概率。

### 3.3 禁止语义

contract 中出现买入、卖出、收益、上涨概率、目标仓位等词，仅存在于“禁止文案/禁止字段/安全边界”上下文中，属于安全声明，不构成风险。

R1 实现时不得在正常输出样例或用户可见摘要中出现这些语义。

## 4. 用户第一性原则审查

通过项：

- 简单：限制每只股票 3 到 5 条关键线索。
- 准确：明确 qlib rank 不等于收益预测，趋势不等于看涨承诺。
- 清晰：区分 support、risk、conflict、background、data_quality。
- 实用：输出人工复盘关注点，而不是替用户决策。

R1 继续注意：

- 不展示 raw rule id、gate、provider、accepted latest、复杂 run id。
- 不堆叠工程指标。
- 不把“风险”写成“卖出/减仓”。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无。

### Network Audit

未联网，未下载，未调用外部 API。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

正常 contract 文案没有输出买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。相关词只出现在禁止文案中。

### Verdict

只读研究边界通过。

## 6. 必须修复项

当前 R0 产物无必须修复项。

R1 必须新增防线：

- 输出枚举校验。
- 禁止字段扫描。
- 禁止文案扫描。
- 冻结规则卡不得作为 gate 的单元测试。
- `confidence` 不得解释成胜率或概率的单元测试。

## 7. 可暂缓项

继续暂缓：

- API。
- 前端。
- Playwright。
- 数据库写入。
- provider。
- accepted latest。
- monitor。
- 新数据源。
- 月营收。
- 模型训练。
- 任何交易路径。

## 8. 是否需要用户确认

当前不需要用户确认。

理由：

- R1 只做后端只读服务层。
- 不接 API。
- 不接前端。
- 不联网。
- 不使用 token。
- 不新增数据源。
- 不训练模型。
- 不写 provider 或数据库。

若执行者认为 R1 需要 API、前端、联网、新数据源、数据库写入或模型训练，必须停止并回报。

## 9. 给执行者的下一步工作文档：Phase R1 后端只读服务

### 9.1 目标

实现人工复盘解释模块的后端只读服务层，按照 R0 contract 组装 explanation JSON。

Phase R1 只允许实现服务层和单元测试，不允许 API、前端或数据库写入。

### 9.2 必读输入

必须读取：

- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `docs/tw_manual_review_explanation/PHASER0_EXECUTION_REPORT_CN.md`
- `docs/tw_manual_review_explanation/PHASER0_REVIEW_AND_PHASER1_WORK_CN.md`
- `data_tw/experiments/manual_review_explanation/phaser0_input_source_inventory.csv`
- `data_tw/experiments/manual_review_explanation/phaser0_contract_summary.json`

### 9.3 允许新增或修改

允许新增后端服务文件，建议路径：

- `backend_api_python/src/services/tw_manual_review_explanation.py`

允许新增单元测试，建议路径：

- `backend_api_python/tests/test_tw_manual_review_explanation.py`

必须新增执行报告：

- `docs/tw_manual_review_explanation/PHASER1_EXECUTION_REPORT_CN.md`

如仓库现有后端服务或测试路径不同，执行者应遵循现有结构，但不得接 API route。

### 9.4 服务边界

服务允许：

- 接受已经在内存中的只读输入对象。
- 根据 contract 生成 explanation dict。
- 做枚举校验。
- 做禁止字段/禁止文案校验。
- 对数据不足输出 `data_insufficient`。
- 对冻结规则卡只输出人工解释线索。

服务禁止：

- 读取外部网络。
- 使用 token。
- 写数据库。
- 写 provider。
- refresh/publish。
- accepted latest switching。
- 调用 monitor。
- 调用 broker、quick-trade、orders。
- 训练模型。
- 读取或生成 fundamental 月营收输入。
- 接 API route。
- 接前端。

### 9.5 R1 必测场景

至少覆盖：

1. 强排名 + 位置偏高
   - 输出应包含 support 与 risk。
   - 不得出现买卖/仓位/收益/概率语义。

2. 排名弱 + 技术弱
   - 输出应为 `manual_review` 或 `caution`，不得写成 sell。

3. 信息冲突
   - 例如 qlib rank 靠前但趋势/技术转弱。
   - 输出 `conflict` 或包含 conflict signal。

4. 数据不足
   - 输出 `data_insufficient`。
   - 包含 data_quality signal。

5. 冻结规则卡
   - 只能产生 caution/review/background/auxiliary 线索。
   - 不得变成 gate、confirmed watch 或模型标签。

6. 禁止语义扫描
   - 正常输出不得包含 buy/sell/hold/target_position/target_weight/expected_return/upside_probability/win_rate/order/broker 等字段或文本。

### 9.6 R1 执行报告必须回答

报告必须包含：

- 当前阶段目标。
- 修改文件。
- 生成文件。
- 服务输入输出摘要。
- 测试覆盖摘要。
- 是否写 API。
- 是否接前端。
- 是否联网/token。
- 是否写数据库/provider。
- 是否训练模型。
- 是否出现交易/收益/概率语义。
- 是否误用冻结规则卡。
- 推荐 gate。
- 风险与待审查问题。

### 9.7 R1 Gate

R1 完成后推荐 gate 只能是：

- `request_phaser2_readonly_api_work`
- `phaser1_service_needs_repair`
- `stop_manual_review_module_scope_invalid`

允许进入 R2 的最低条件：

- 后端服务只读。
- 单元测试通过。
- 无交易/仓位/收益/概率语义。
- 无联网/token。
- 无数据库/provider 写入。
- 无 API route。
- 无前端。

### 9.8 R1 禁止事项

Phase R1 禁止：

- 写 API route。
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

完成后等待审查者审核，不得自动进入 R2。
