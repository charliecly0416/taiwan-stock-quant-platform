# Phase R2 只读 API 审查结论与 Phase R3 工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_manual_review_explanation/PHASER2_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_MODULE_PLAN_CN.md`
- `docs/tw_manual_review_explanation/REVIEWER_PROMPT_CN.md`
- `docs/tw_manual_review_explanation/PHASER1_REVIEW_AND_PHASER2_WORK_CN.md`
- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `docs/tw_decision_model_orthogonal/PHASE2D_CLOSURE_REVIEW_AND_STANDBY_WORK_CN.md`
- `docs/tw_decision_model_fundamental/PHASEF0E_REVIEW_AND_FUNDAMENTAL_STOP_CN.md`

审查产物：

- `backend/app/routes/tw_stock.py`
- `backend/tests/test_tw_manual_review_explanation_api.py`
- `backend/app/services/tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation.py`
- `docs/tw_manual_review_explanation/PHASER2_EXECUTION_REPORT_CN.md`

## 1. 本步审核结论

Phase R2 通过。

执行者没有偏离主线，也没有新增分支：

- 只新增 `GET /api/tw-stock/manual-review/explanation`。
- 未新增 manual-review POST/PUT/PATCH/DELETE。
- 未接前端。
- 未联网。
- 未使用 token。
- 未新增数据源。
- 未写数据库。
- 未写 provider。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未调用 monitor。
- 未触碰 broker、quick-trade、orders。
- 未训练模型。
- 未继续 fundamental 月营收主线。
- 未继续正交 Phase2E。
- 未复活 Entry Model。

Gate 结论：

- 接受 `recommended_gate=request_phaser3_frontend_readonly_work`。

允许进入 Phase R3，但 R3 只能做轻量前端只读展示；不得新增复杂页面，不得保存配置、触发扫描、写告警、触发 provider、调用交易路径或输出买卖/仓位/收益/概率语义。R3 展示位置应优先选择台股研究或股票详情等只读语境，不得把复盘线索放在订单、仓位调整、quick-trade 或 broker 控件附近。

## 2. 主线一致性审查

R2 与当前主线一致：API 只把 query string 组装成内存 context，并调用 R1 `TWManualReviewExplanationService` 返回 explanation JSON。

通过项：

- route method 仅为 GET。
- route 名称与 manual review explanation 语义一致。
- API 没有主动读取真实数据源。
- API 没有补拉数据。
- 数据不足时由服务返回 `data_insufficient`，未扩大为 provider 或数据修复任务。
- 冻结规则卡只以 query 中的 rule id 映射成人工解释线索，没有升级为 gate、confirmed watch 或模型标签。

未发现新增业务分支。

## 3. API 与 Contract 审查

新增 route：

- `GET /api/tw-stock/manual-review/explanation`

输入边界：

- 仅 query 参数。
- route 内部组装为内存 dict。
- 只调用 R1 service。

输出边界：

- 正常响应字段遵循 R0/R1 contract。
- 正常响应包含 `research_only=true` 与 `not_trading_advice=true`。
- `signals` 仍由 R1 service 限制最多 5 条。
- 数据不足不触发补数据。

只读错误结构：

- 缺少 symbol 时返回 400。
- contract violation 时返回只读错误结构，并保留 `research_only=true` 与 `not_trading_advice=true`。
- 非预期异常返回通用只读错误文案，没有泄露买卖、仓位、收益或概率语义。

## 4. 测试与验证

本次复核执行：

- `python -m py_compile backend/app/routes/tw_stock.py backend/app/services/tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py`
- `python -m pytest backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py -q`

结果：

- 编译通过。
- 专项测试通过：`11 passed in 1.12s`。

测试覆盖符合 R2 要求：

- GET 正常返回 contract JSON。
- GET 数据不足时返回安全解释。
- GET 输出通过禁止语义扫描。
- manual-review route 的 POST/PUT/PATCH/DELETE 返回 405。
- API 测试防止调用 monitor、provider ops、normal publish、accepted latest scheduler 等变更性路径。

测试加固建议：

- 当前测试 monkeypatch 了 `option_c_normal_publish_gate.run`，而既有 route 中正常发布方法名看起来是 `publish`。R2 route 实际没有调用该对象，因此这不是当前阻塞项；但 R4 安全验收时建议改为同时 patch `publish`，让测试语义更精确。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：一个测试加固建议，不影响当前通过结论。

### Network Audit

未发现 R2 新增联网、token、外部 API、provider refresh/publish 或 accepted latest switching。

### Console Audit

未发现 R2 新增 monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 路径。

`backend/app/routes/tw_stock.py` 中存在既有 sim orders、monitor、quant ops 等旧 route，但 R2 diff 只新增 manual-review GET route；这些既有 route 不属于本轮新增分支。

### Text / Agent Semantics

新增 manual-review API 正常输出未发现买入、卖出、持有、目标仓位、目标权重、收益承诺、上涨概率承诺或胜率语义。

关键词命中主要来自：

- 禁止语义扫描器。
- API 测试中的禁止词列表。
- 执行报告中的安全边界说明。
- `tw_stock.py` 中既有非本轮新增 sim/monitor route。

这些不构成本轮 manual-review API 的交易建议或危险动作。

### Verdict

只读研究边界通过。

## 6. 用户第一性原则审查

通过项：

- 简单：当前 API 返回单个 explanation，不引入复杂筛选或批量工程指标。
- 准确：query 参数只被解释为只读研究上下文，没有自动补数据或预测。
- 清晰：API 保留 `summary`、`signals`、`next_review_focus`，便于前端直接展示。
- 实用：可支持下一步轻量前端“复盘线索”展示，不替用户决策。

R3 继续注意：

- 前端只展示少量核心信息。
- 不展示 raw rule id、provider、run id、accepted latest、IC、RankIC、训练指标。
- 不把 `multi_source_support` 写成推荐、确认、可买或高概率。
- 不把 `caution` 写成卖出、减仓或止损。

## 7. 必须修复项

当前 R2 无必须修复项。

## 8. 可暂缓项

继续暂缓：

- 真实只读上下文字段映射。
- 批量 explanation。
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

- R3 只授权轻量前端只读展示。
- 不授权新 API。
- 不授权写接口。
- 不授权联网、token、新数据源、provider、monitor、模型训练或交易相关能力。

若执行者认为 R3 必须保存配置、触发扫描、写告警、接 provider、接真实数据源、接交易路径或改变模块定位，必须停止并回报。

## 10. 给执行者的下一步工作文档：Phase R3 前端轻量只读展示

### 10.1 目标

在现有台股研究或股票详情等只读前端页面中增加一个轻量“复盘线索”展示区，调用 R2 只读 GET API 展示 explanation。

Phase R3 只允许做前端只读展示与必要的静态/单元测试，不允许新增写入能力或复杂产品分支。

### 10.2 必读输入

必须读取：

- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `docs/tw_manual_review_explanation/PHASER2_EXECUTION_REPORT_CN.md`
- `docs/tw_manual_review_explanation/PHASER2_REVIEW_AND_PHASER3_WORK_CN.md`
- `backend/app/routes/tw_stock.py`
- `backend/app/services/tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation_api.py`

### 10.3 允许新增或修改

允许：

- 在现有台股研究、台股详情或相关只读页面中增加轻量展示区。
- 新增前端 API client 的 GET 调用。
- 新增前端静态检查或单元测试。
- 新增执行报告：
  - `docs/tw_manual_review_explanation/PHASER3_EXECUTION_REPORT_CN.md`

不建议：

- 新增独立复杂页面。
- 新增复杂筛选器或批量工作台。
- 展示工程内部字段。
- 放在模拟账户、订单、仓位调整、quick-trade 或 broker 控件附近。

如执行者确实只能复用模拟账户页面，必须满足：

- 只放在与订单/仓位/下单控件视觉隔离的只读信息区。
- 不读取、展示或计算账户仓位、目标仓位、可下单数量、订单状态。
- 不与任何交易按钮、保存按钮、扫描按钮或告警写入控件联动。
- 执行报告必须说明为什么没有更合适的只读研究页面，并列出隔离措施。

### 10.4 前端展示要求

用户可见标题建议：

- `复盘线索`

每只股票最多展示：

- 一个状态标签。
- 一句摘要。
- 最多 3 条关键线索。
- 一个轻量详情展开区，可展示 `next_review_focus` 和 `data_quality_notes`。

状态文案必须保持只读研究语义：

- `multi_source_support`：可写为“多源支持，仍需复盘”。
- `manual_review`：可写为“需要人工复盘”。
- `caution`：可写为“谨慎观察”。
- `conflict`：可写为“信息冲突”。
- `data_insufficient`：可写为“数据不足”。

### 10.5 前端禁止展示

禁止展示：

- 买入。
- 卖出。
- 持有建议。
- 加仓、减仓。
- 目标仓位。
- 目标权重。
- 收益承诺。
- 上涨概率。
- 胜率。
- 下单。
- 连接券商。
- 自动交易。
- confirmed watch。
- gate。
- raw rule id。
- provider。
- accepted latest。
- run id。
- IC / RankIC。
- 训练指标。

### 10.6 交互边界

R3 前端只能：

- 发起 `GET /api/tw-stock/manual-review/explanation`。
- 根据当前页面已有 symbol/asof 或用户输入 symbol 读取 explanation。
- 显示 loading / empty / error / data_insufficient 状态。
- 在只读研究语境中展示 explanation，不得与交易、仓位、订单或监控写入流程形成同一操作链。

R3 前端禁止：

- POST/PUT/PATCH/DELETE。
- 保存 monitor config。
- 触发 monitor scan。
- 写 alerts。
- 读取、展示或计算账户仓位。
- 展示可下单数量、订单状态或交易按钮。
- 调用 quant ops。
- 调用 provider refresh/publish。
- accepted latest switching。
- 调用 broker、quick-trade、orders。
- 触发模型训练。
- 联网到第三方。
- 使用 token。

### 10.7 R3 必测场景

至少覆盖：

1. 页面或组件能展示正常 explanation。
2. 数据不足时显示“数据不足/补齐资料后再复盘”类只读文案。
3. API 错误时显示只读错误，不出现交易建议。
4. 前端代码中 manual-review 模块只调用 GET。
5. 静态扫描确认用户可见文案不含买卖、仓位、收益、上涨概率或胜率语义。
6. 静态扫描确认 manual-review 展示区不调用订单、broker、quick-trade、monitor 写入或 provider ops 相关 client。

如仓库已有前端 E2E 基础，R3 可以增加轻量 smoke；若没有，不得为了 R3 大规模搭建新 E2E 框架。

### 10.8 R3 执行报告必须回答

报告必须包含：

- 当前阶段目标。
- 修改文件。
- 新增 UI 位置。
- UI 是否处于只读研究语境；若复用模拟账户页面，必须说明隔离措施。
- 调用的 API route 与 HTTP method。
- 页面展示字段。
- 空状态/错误状态处理。
- 是否新增页面。
- 是否 POST/PUT/PATCH/DELETE。
- 是否保存配置。
- 是否触发 monitor scan 或 alerts write。
- 是否读取或展示账户仓位、可下单数量、订单状态或交易按钮。
- 是否 provider refresh/publish。
- 是否 accepted latest switching。
- 是否 broker / quick-trade / orders。
- 是否联网/token。
- 是否训练模型。
- 是否出现买卖/仓位/收益/概率语义。
- 测试命令与结果。
- 推荐 gate。
- 风险与待审查问题。

### 10.9 R3 Gate

R3 完成后推荐 gate 只能是：

- `request_phaser4_readonly_acceptance_work`
- `phaser3_frontend_needs_repair`
- `stop_manual_review_module_scope_invalid`

允许进入 R4 的最低条件：

- 前端只读展示清晰。
- 只调用 manual-review GET API。
- 无 POST/PUT/PATCH/DELETE。
- 无 monitor/provider/accepted latest/交易路径。
- 无账户仓位、可下单数量、订单状态或交易按钮耦合。
- 无买卖、仓位、收益或概率语义。
- 不新增复杂页面或复杂产品分支。

### 10.10 R3 禁止事项

Phase R3 禁止：

- 新增写入 API。
- 保存任何配置。
- 触发扫描。
- 写告警。
- 写数据库。
- 读取或展示账户仓位。
- 展示可下单数量、订单状态或交易按钮。
- 联网到第三方。
- 使用 token。
- 新增数据源。
- 继续月营收。
- 继续正交规则探索。
- 复活 Entry Model。
- 训练模型。
- provider refresh/publish。
- accepted latest switching。
- broker、quick-trade、orders。
- target position / target weight。
- 输出买入/卖出/持有建议。
- 输出收益承诺。
- 输出上涨概率或胜率承诺。

完成后等待审查者审核，不得自动进入 R4。
