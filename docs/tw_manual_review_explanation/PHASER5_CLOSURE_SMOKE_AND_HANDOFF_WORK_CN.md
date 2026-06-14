# Phase R5 一轮收口 Smoke 与交接工作文档

创建日期：2026-06-12

当前状态：

- Phase R4 已通过。
- `manual_review_explanation_module_acceptance_passed=true`
- 人工复盘解释模块主线已完成技术验收。

本轮目标不是继续开发，而是做一轮面向用户的收口确认：让用户能简单、准确、清晰、实用地理解当前模块在哪里、能做什么、不能做什么。

## 1. 本轮目标

Phase R5 只做三件事：

1. 只读 smoke：确认页面能看到 `复盘线索`，并且 manual-review 只发 GET 请求。
2. 用户交接摘要：整理当前模块的入口、能力、限制和已知暂缓项。
3. 文档索引：整理 R0-R4 关键文档和代码文件，方便后续接手。

本轮不新增功能、不改业务逻辑、不补数据。

## 2. 用户第一性原则

执行者必须按以下标准收口：

- 简单：用户只需要知道入口、怎么看、显示什么。
- 准确：不要把复盘线索说成推荐、预测、胜率或收益。
- 清晰：明确当前只支持单标的轻量复盘线索，完整上下文暂未接入。
- 实用：给出用户可执行的查看步骤和故障排查提示。

禁止用工程指标堆文档：

- 不要把 qlib、PIT、IC、RankIC、provider、accepted latest、run id 写成用户主说明。
- 如必须提到，只能放在“开发者索引/已知限制”中。

## 3. 必读输入

必须读取：

- `docs/tw_manual_review_explanation/PHASER4_FINAL_REVIEW_AND_CLOSURE_CN.md`
- `docs/tw_manual_review_explanation/PHASER4_EXECUTION_REPORT_CN.md`
- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/api/tw-stock.js`
- `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- `backend/app/routes/tw_stock.py`
- `backend/app/services/tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation_api.py`

## 4. 允许新增或修改

允许新增文档：

- `docs/tw_manual_review_explanation/PHASER5_CLOSURE_SMOKE_REPORT_CN.md`
- `docs/tw_manual_review_explanation/MANUAL_REVIEW_EXPLANATION_HANDOFF_CN.md`

允许执行只读命令：

- 后端专项测试。
- 前端专项静态检查。
- 前端 build。
- 只读浏览器 smoke，如现有环境能稳定启动。

允许临时启动本地服务用于只读 smoke，但必须：

- 不触发数据刷新。
- 不触发 provider。
- 不触发 monitor scan。
- 不写 alerts。
- 不连接 broker。
- 不调用 quick-trade 或 orders。

## 5. 禁止事项

Phase R5 禁止：

- 新增业务功能。
- 新增页面。
- 新增 API。
- 修改 manual-review service、route、client 或 UI 业务语义。
- 接真实完整上下文字段映射。
- 做批量 explanation。
- 保存任何配置。
- 触发 monitor scan。
- 写 alerts。
- 写数据库。
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

如果 smoke 需要登录或启动服务，执行者只能使用本地只读方式；如果环境阻塞，不得绕过限制，应在报告中记录阻塞原因。

## 6. 只读 Smoke 要求

如可运行本地前后端，执行者做最小 smoke：

1. 打开台股研究页面。
2. 确认能看到 `复盘线索` 面板。
3. 选择一个标的或使用默认标的。
4. 点击 `查看线索`。
5. 确认出现状态、摘要、最多 3 条线索、复盘重点或数据提示。
6. 记录浏览器网络请求。

网络请求审计必须确认：

- manual-review 只调用 `GET /api/tw-stock/manual-review/explanation`。
- 没有 POST/PUT/PATCH/DELETE。
- 没有 `/api/tw-stock/monitor/config` 写请求。
- 没有 `/api/tw-stock/monitor/scan` 或 `/scan-all`。
- 没有 `/api/tw-stock/monitor/alerts` 写请求。
- 没有 `/api/tw-stock/quant/ops/**` publish/refresh/provider/accepted 请求。
- 没有 `/api/quick-trade/**`。
- 没有 `/api/broker/**`。
- 没有 orders 请求。

如无法运行浏览器 smoke：

- 不要强行搭新 E2E 框架。
- 报告中说明阻塞原因。
- 至少执行静态检查和 build，并明确“未执行浏览器 smoke”。

## 7. 必跑验证

至少执行：

- `python -m py_compile backend/app/routes/tw_stock.py backend/app/services/tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py`
- `python -m pytest backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py -q`
- `node frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `node frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- `corepack pnpm build`，工作目录 `frontend`

如果任何命令失败：

- 不要修改业务逻辑。
- 先判断是否为环境问题、既有问题或本模块问题。
- 在报告中如实记录。

## 8. 用户交接摘要要求

新增：

- `docs/tw_manual_review_explanation/MANUAL_REVIEW_EXPLANATION_HANDOFF_CN.md`

必须包含：

1. 用户入口：在哪个页面看到 `复盘线索`。
2. 用户能看到什么：状态、摘要、线索、复盘重点、数据提示。
3. 用户不能把它当成什么：不是买卖建议、不是仓位建议、不是收益/概率预测。
4. 当前限制：前端只传 qlib/trend，技术状态、价格位置、冻结规则卡完整映射暂缓。
5. 故障提示：数据不足、接口不可用、没有标的时用户会看到什么。
6. 开发者索引：关键前端、后端、测试、文档路径。
7. 后续必须重新授权的事项：真实上下文映射、批量解释、新 API、新页面、provider、monitor、模型训练、交易相关能力。

文案要求：

- 面向用户时避免工程术语。
- 不出现推荐买入、建议卖出、目标仓位、预计收益、上涨概率、胜率承诺等表达。
- 不暗示“多源支持”就是可以买。
- 不暗示“谨慎观察”就是卖出或减仓。

## 9. R5 报告要求

新增：

- `docs/tw_manual_review_explanation/PHASER5_CLOSURE_SMOKE_REPORT_CN.md`

报告必须回答：

- 当前阶段目标。
- 修改文件。
- 是否新增业务功能。
- 是否新增页面/API。
- 是否修改 manual-review 业务语义。
- 必跑验证命令与结果。
- 是否执行浏览器 smoke。
- 如果执行，网络请求审计结果。
- 如果未执行，原因。
- 是否 POST/PUT/PATCH/DELETE。
- 是否保存配置。
- 是否触发 monitor scan 或 alerts write。
- 是否 provider refresh/publish。
- 是否 accepted latest switching。
- 是否 broker / quick-trade / orders。
- 是否联网/token。
- 是否训练模型。
- 是否出现买卖/仓位/收益/概率语义。
- 用户交接摘要文件路径。
- 推荐 gate。
- 风险与待审查问题。

## 10. R5 Gate

R5 完成后推荐 gate 只能是：

- `manual_review_explanation_closure_smoke_passed`
- `phaser5_closure_needs_repair`
- `stop_manual_review_module_scope_invalid`

允许通过的最低条件：

- R4 已通过状态未被破坏。
- 必跑验证通过，或清楚说明非模块原因。
- handoff 文档清晰、准确、实用。
- 没有新增业务功能。
- 没有新增写路径。
- 没有 provider/monitor/accepted latest/交易路径。
- 没有买卖、仓位、收益或概率语义。

完成后等待审查者审核，不得自动开启新主线。
