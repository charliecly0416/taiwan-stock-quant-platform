# Phase R1 后端只读服务审查结论与 Phase R2 工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_manual_review_explanation/PHASER1_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_MODULE_PLAN_CN.md`
- `docs/tw_manual_review_explanation/REVIEWER_PROMPT_CN.md`
- `docs/tw_manual_review_explanation/PHASER0_REVIEW_AND_PHASER1_WORK_CN.md`
- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `docs/tw_decision_model_orthogonal/PHASE2D_CLOSURE_REVIEW_AND_STANDBY_WORK_CN.md`
- `docs/tw_decision_model_fundamental/PHASEF0E_REVIEW_AND_FUNDAMENTAL_STOP_CN.md`

审查产物：

- `backend/app/services/tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation.py`
- `docs/tw_manual_review_explanation/PHASER1_EXECUTION_REPORT_CN.md`

## 1. 本步审核结论

Phase R1 通过。

执行者没有偏离主线，也没有新增分支：

- 只新增后端只读服务层与专项单元测试。
- 未写 API route。
- 未接前端。
- 未联网。
- 未使用 token。
- 未新增数据源。
- 未读取或写入数据库。
- 未写 provider。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未调用 monitor。
- 未触碰 broker、quick-trade、orders。
- 未训练模型。
- 未继续 fundamental 月营收主线。
- 未继续正交规则探索分支。
- 未把冻结规则卡升级为 gate、confirmed watch、模型标签或交易判断。

Gate 结论：

- 接受 `recommended_gate=request_phaser2_readonly_api_work`。

允许进入 Phase R2，但 R2 只能做只读 GET API 接入与测试；不得接前端、不得写入、不得联网、不得新增 provider 或数据源、不得引入交易语义。

## 2. 主线一致性审查

R1 的定位与当前主线一致：把既有只读研究上下文整理成人工复盘解释对象，服务本身只转换调用方传入的内存 dict，不主动读取外部数据。

路径说明：

- R0 工作文档中建议路径为 `backend_api_python/...`。
- R1 实际使用 `backend/app/services/...` 与 `backend/tests/...`。
- 由于 R0 明确允许“如仓库现有后端服务或测试路径不同，执行者应遵循现有结构”，该路径差异不构成偏离主线。

未发现新增业务分支。

## 3. 服务与 Contract 审查

通过项：

- 输出字段覆盖 R0 contract 要求：`symbol`、`name`、`asof`、`overall_status`、`status_label`、`confidence`、`summary`、`signals`、`next_review_focus`、`research_only`、`not_trading_advice`、`data_quality_notes`。
- `overall_status`、`signals.type`、`signals.severity`、`confidence` 均有枚举约束。
- `signals` 限制最多 5 条，符合简单、清晰原则。
- 数据不足时输出 `data_insufficient` 与 `data_quality` signal。
- 冻结规则卡只映射为人工解释线索，且输出 source 为 `frozen_rule_card`，未暴露 raw rule id。
- `confidence` 当前实现只表示解释完整度，没有写成胜率、概率或上涨可能性。

注意项：

- 当前服务由调用方传入内存 context，尚未做真实上下文字段映射。R2 接 API 时必须保持该边界，不得在 API 层顺手新增数据读取、provider 查询或 accepted latest 切换。

## 4. 测试与验证

本次复核执行：

- `python -m py_compile backend/app/services/tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation.py`
- `python -m pytest backend/tests/test_tw_manual_review_explanation.py -q`

结果：

- 编译通过。
- 专项测试通过：`6 passed in 0.78s`。

测试覆盖符合 R1 要求：

- 强排名 + 位置偏高。
- 排名弱 + 技术弱。
- 信息冲突。
- 数据不足。
- 冻结规则卡只作为解释线索。
- 禁止字段与禁止文案扫描。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无。

### Network Audit

未发现联网、token、外部 API、provider refresh/publish 或 accepted latest switching。

### Console Audit

未发现 monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 路径。

### Text / Agent Semantics

正常服务输出未发现买入、卖出、持有、目标仓位、目标权重、收益承诺、上涨概率承诺或胜率语义。

代码和测试中出现相关关键词的上下文为：

- 禁止字段扫描器。
- 禁止文案扫描器。
- 单元测试负例。
- 执行报告中的安全边界说明。

这些属于允许的安全声明或测试输入，不构成用户可执行建议。

### Verdict

只读研究边界通过。

## 6. 用户第一性原则审查

通过项：

- 简单：每只股票最多 5 条 signals，不堆叠复杂工程细节。
- 准确：区分 support、risk、conflict、background、data_quality，未把研究排名解释成预测收益。
- 清晰：输出 `summary` 与 `next_review_focus`，用户可以直接看下一步人工复盘重点。
- 实用：服务产物面向人工复盘，不替用户做买卖或仓位决策。

R2 继续注意：

- API 响应不要暴露 raw rule id、provider、run id、accepted latest 切换细节或模型工程指标。
- 不要把 `multi_source_support` 写成“推荐”“确认”“可买”“高概率”。
- 不要把 `caution` 写成“卖出”“减仓”“止损”。

## 7. 必须修复项

当前 R1 无必须修复项。

## 8. 可暂缓项

继续暂缓：

- 前端。
- Playwright。
- 数据库写入。
- provider。
- accepted latest。
- monitor。
- 新数据源。
- 月营收。
- 模型训练。
- 交易路径。

## 9. 是否需要用户确认

当前不需要额外用户确认。

理由：

- R2 只授权只读 GET API。
- 不授权前端。
- 不授权 POST/PUT/PATCH/DELETE。
- 不授权联网、token、新数据源、provider、monitor、模型训练或交易相关能力。

若执行者认为 R2 必须新增数据读取、provider、数据库写入、monitor、前端或交易语义，必须停止并回报。

## 10. 给执行者的下一步工作文档：Phase R2 只读 API

### 10.1 目标

为 R1 的人工复盘解释服务增加只读 API 入口，让调用方可以通过 GET 请求取得 contract-compliant explanation JSON。

Phase R2 只允许做只读 API route、必要的只读适配层与 API 测试。

### 10.2 必读输入

必须读取：

- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `docs/tw_manual_review_explanation/PHASER1_EXECUTION_REPORT_CN.md`
- `docs/tw_manual_review_explanation/PHASER1_REVIEW_AND_PHASER2_WORK_CN.md`
- `backend/app/services/tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation.py`

### 10.3 允许新增或修改

允许：

- 新增或修改后端 API route 文件，但只能增加 GET 只读接口。
- 新增 API 测试。
- 如现有后端结构需要，新增轻量 schema/adapter，但不得引入新数据源。
- 新增执行报告：
  - `docs/tw_manual_review_explanation/PHASER2_EXECUTION_REPORT_CN.md`

建议接口形态由执行者根据现有后端风格决定，但必须满足：

- HTTP method 只能是 `GET`。
- 路由语义必须是 manual review explanation readonly。
- 响应必须直接或间接调用 R1 服务生成。
- 响应字段必须遵循 R0 contract。

### 10.4 输入数据边界

R2 可以使用：

- 测试 fixture。
- 请求参数中提供的 symbol/asof。
- 已存在的只读内存上下文或现有只读查询结果，但前提是不会触发 refresh/publish/switch/write。

R2 不允许：

- 新增联网抓取。
- 使用 token。
- 新增 provider。
- provider refresh/publish。
- accepted latest switching。
- 写数据库。
- 修改 monitor config。
- 触发 monitor scan。
- 写 alerts。
- 调用 broker、quick-trade、orders。
- 读取或生成 fundamental 月营收输入。
- 训练模型。
- 接前端。

如果现有真实数据上下文无法只读取得，R2 应使用受控 fixture 或返回明确的数据不足解释，不得扩大范围补数据。

### 10.5 API 输出要求

API 响应必须：

- `research_only=true`
- `not_trading_advice=true`
- 不超过 5 条 signals。
- 保留 `data_quality_notes`。
- 保留禁止语义扫描。
- 对数据不足返回 `overall_status=data_insufficient` 或清晰的只读错误，不得隐式拉取新数据。

API 响应禁止：

- 买入、卖出、持有建议。
- 目标仓位、目标权重。
- 收益承诺。
- 上涨概率承诺。
- 胜率语义。
- 自动下单、券商连接、订单准备语义。
- confirmed watch、gate、模型标签语义。

### 10.6 R2 必测场景

至少覆盖：

1. GET 正常返回 explanation JSON，字段符合 contract。
2. GET 数据不足时返回安全解释，不触发数据补齐或 provider。
3. GET 输出通过禁止字段/禁止文案扫描。
4. API 不存在 POST/PUT/PATCH/DELETE 写入口。
5. API 测试确认未调用 monitor、broker、quick-trade、orders、provider refresh/publish、accepted latest switching。

### 10.7 R2 执行报告必须回答

报告必须包含：

- 当前阶段目标。
- 修改文件。
- 新增 route 列表与 HTTP method。
- API 输入输出摘要。
- 是否接前端。
- 是否联网/token。
- 是否新增数据源。
- 是否写数据库/provider。
- 是否 provider refresh/publish。
- 是否 accepted latest switching。
- 是否调用 monitor。
- 是否 broker / quick-trade / orders。
- 是否训练模型。
- 是否出现买卖/仓位/收益/概率语义。
- 测试命令与结果。
- 推荐 gate。
- 风险与待审查问题。

### 10.8 R2 Gate

R2 完成后推荐 gate 只能是：

- `request_phaser3_frontend_readonly_work`
- `phaser2_api_needs_repair`
- `stop_manual_review_module_scope_invalid`

允许进入 R3 的最低条件：

- 只读 GET API 通过测试。
- 无 POST/PUT/PATCH/DELETE 写入口。
- 无联网/token。
- 无新增数据源。
- 无 provider refresh/publish。
- 无 accepted latest switching。
- 无 monitor 写入或扫描。
- 无 broker、quick-trade、orders。
- 无买卖、仓位、收益或概率语义。

### 10.9 R2 禁止事项

Phase R2 禁止：

- 写前端。
- POST/PUT/PATCH/DELETE API。
- 写数据库。
- 联网。
- 使用 token。
- 新增数据源。
- 继续月营收。
- 继续正交规则探索。
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
- 输出买入/卖出/持有建议。
- 输出收益承诺。
- 输出上涨概率或胜率承诺。

完成后等待审查者审核，不得自动进入 R3。
