# 台股人工复盘解释模块下一轮方案：只读浏览器验收入口与完整上下文字段映射

## 1. 背景

人工复盘解释模块 Phase R5 已收口：

- `manual_review_explanation_module_acceptance_passed=true`
- `manual_review_explanation_closure_smoke_passed=true`
- `manual_review_handoff_done=true`
- `manual_review_mainline_closed=true`

当前模块已经具备基础可用性，但 R5 审查留下两个合理后续优化点：

1. 建立干净的浏览器只读验收入口，避免被既有页面挂载时的 portfolio replay POST 干扰。
2. 补齐更完整的上下文字段映射，让复盘线索更贴近真实用户需要。

本轮是人工复盘解释模块的后续增强，不是：

- Entry Model 重启。
- 正交规则探索重启。
- fundamental PIT 重启。
- 模型训练。
- 新数据源接入。
- provider/accepted latest 操作。
- 交易功能。

## 2. 用户第一性原则

所有实现必须继续符合：

1. 简单：用户只看到少量关键复盘线索。
2. 准确：线索必须来自已有只读数据，不能夸大为交易判断。
3. 清晰：明确区分支持、风险、冲突、背景、数据不足。
4. 实用：帮助用户知道下一步人工看什么。

本轮不允许为了“信息完整”把页面变成字段堆叠。

## 3. 本轮目标

### 3.1 目标 A：浏览器只读验收入口

为人工复盘解释模块建立可稳定测试的浏览器入口。

要求：

- 能在 Playwright 中只验证 manual-review 模块。
- 不触发既有 portfolio replay POST。
- 不触发 monitor scan。
- 不保存 monitor config。
- 不写 alerts。
- 不触发 provider refresh/publish。
- 不触发 accepted latest switching。
- 不触发 broker/quick-trade/orders。

允许实现方式：

- 增加测试专用 route/mock/fixture。
- 增加页面 query flag，使测试只挂载 manual-review 区块。
- 增加隐藏/开发态只读测试入口。
- 或在 E2E 中通过 route mock 明确拦截非 manual-review 请求。

限制：

- 不得为了测试破坏真实页面逻辑。
- 不得禁用真实业务功能。
- 不得新增用户可见的复杂调试页面，除非审查者明确批准。

### 3.2 目标 B：完整上下文字段映射

补齐 manual-review explanation 的输入上下文，但输出仍保持简洁。

优先上下文：

- qlib rank / score / rank_tier。
- qlib 排名变化，若已有数据源。
- QuantDinger trend label / score / ret5 / ret20 / ret60。
- MA/RSI/MACD/Bollinger 技术状态。
- positionRisk。
- 冻结法人/融资融券解释规则卡。
- 数据质量 warning。

输出约束：

- 每只股票默认最多 3 条主线索。
- 详情展开最多 5 条。
- 不展示 raw rule id 给普通用户。
- 不展示 provider、gate、run id、IC、RankIC、训练指标。
- 不输出买入、卖出、持有、目标仓位、收益承诺或上涨概率。

## 4. 分阶段执行计划

### Phase R6：只读浏览器验收设计与入口方案

目标：

- 设计 manual-review 专用浏览器验收方式。
- 明确如何避免既有 portfolio replay POST 干扰。
- 不修改业务代码，或只做最小测试支撑。

产物：

- `docs/tw_manual_review_explanation/PHASER6_EXECUTION_REPORT_CN.md`
- `docs/tw_manual_review_explanation/manual_review_browser_readonly_acceptance_plan.md`

Gate：

- 方案必须证明只测 manual-review。
- 危险请求清单必须明确。
- 不得实际扩大业务功能。

### Phase R7：实现浏览器只读验收

目标：

- 新增 Playwright readonly smoke。
- 验证 manual-review 区块可见、文案安全、GET 请求正确、无危险请求。

建议产物：

- `frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`
- E2E summary artifact，若项目已有 artifact 规范则沿用。
- `docs/tw_manual_review_explanation/PHASER7_EXECUTION_REPORT_CN.md`

Gate：

- Playwright 通过。
- manual-review 只调用 GET。
- forbidden request count = 0。
- 页面无买卖/仓位/收益/概率语义。

### Phase R8：完整上下文字段映射设计

目标：

- 盘点现有 API/service 已能提供的上下文字段。
- 设计字段映射表。
- 明确哪些字段进入主线索，哪些只进详情，哪些暂缓。

产物：

- `docs/tw_manual_review_explanation/manual_review_context_mapping_contract.md`
- `docs/tw_manual_review_explanation/PHASER8_EXECUTION_REPORT_CN.md`

Gate：

- 所有字段来自已有只读数据。
- 不新增数据源。
- 不继续 fundamental/月营收探索。
- 不引入模型训练。

### Phase R9：实现上下文字段映射增强

目标：

- 更新后端 manual-review service。
- 如有必要，更新只读 API response。
- 更新前端展示，但保持简洁。
- 增加测试。

Gate：

- 后端测试通过。
- 前端静态检查通过。
- 文案安全扫描通过。
- 页面仍符合用户第一性原则。

### Phase R10：最终只读验收与收口

目标：

- 后端测试。
- 前端测试。
- Playwright readonly smoke。
- build。
- 安全边界审查。
- 用户交接摘要更新。

Gate：

- 无危险请求。
- 无交易语义。
- 复盘线索清晰、简洁、准确。

## 5. 安全边界

本轮全程禁止：

- 新数据源。
- 联网或 token，除非仅访问本地前后端测试服务。
- 模型训练。
- qlib provider 写入。
- provider refresh/publish。
- accepted latest switching。
- monitor config save。
- monitor scan。
- alerts write。
- broker。
- quick-trade。
- orders。
- target position / target weight。
- 买入/卖出/持有建议。
- 收益承诺。
- 上涨概率/胜率承诺。

## 6. 执行与审查机制

继续双窗口交替：

1. 审查者先给下一步工作文档。
2. 执行者只执行当前授权阶段。
3. 执行者完成后输出执行报告。
4. 审查者审查代码、报告、测试、网络与安全边界。
5. 审查者给出下一步工作文档。
6. 若涉及范围变化，必须停下来问用户。

## 7. 当前建议

下一步从 Phase R6 开始。

审查者应先创建：

`docs/tw_manual_review_explanation/PHASER6_REVIEW_BASELINE_AND_NEXT_WORK_CN.md`

Phase R6 只允许执行者设计浏览器只读验收入口方案，不直接实现上下文字段映射，不新增数据源，不训练模型，不接交易路径。

