# Phase R3 前端只读展示审查结论与 Phase R4 工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_manual_review_explanation/PHASER3_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_MODULE_PLAN_CN.md`
- `docs/tw_manual_review_explanation/REVIEWER_PROMPT_CN.md`
- `docs/tw_manual_review_explanation/PHASER2_REVIEW_AND_PHASER3_WORK_CN.md`
- `docs/tw_manual_review_explanation/PHASER2_REVIEW_DOC_SELF_AUDIT_CN.md`
- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `docs/tw_decision_model_orthogonal/PHASE2D_CLOSURE_REVIEW_AND_STANDBY_WORK_CN.md`
- `docs/tw_decision_model_fundamental/PHASEF0E_REVIEW_AND_FUNDAMENTAL_STOP_CN.md`

审查产物：

- `frontend/src/api/tw-stock.js`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `docs/tw_manual_review_explanation/PHASER3_EXECUTION_REPORT_CN.md`

## 1. 本步审核结论

Phase R3 通过，但 R4 必须先处理既有全页安全扫描口径问题，不能直接做最终收尾。

执行者没有偏离主线，也没有新增分支：

- 只在现有台股研究页的“今日研究排名”区域增加轻量 `复盘线索` 面板。
- 未新增独立复杂页面。
- manual-review client 只调用 `GET /api/tw-stock/manual-review/explanation`。
- 未新增 manual-review POST/PUT/PATCH/DELETE。
- 未保存配置。
- 未触发 monitor scan。
- 未写 alerts。
- 未调用 quant ops。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未调用 broker、quick-trade、orders。
- 未读取、展示或计算账户仓位、可下单数量或订单状态。
- 未训练模型。
- 未新增数据源。
- 未继续月营收、正交 Phase2E 或 Entry Model。

Gate 结论：

- 接受 R3 前端只读展示。
- 不接受直接最终收尾。
- 下一步进入 `request_phaser4_static_scan_repair_and_readonly_acceptance_work`。

## 2. 主线一致性审查

R3 与当前主线一致：把 R2 只读 explanation API 的结果展示给用户，帮助人工复盘，不生成买卖建议。

通过项：

- UI 位置在 `frontend/src/views/tw-stock-monitor/index.vue` 的 qlib 研究排名区域，位于排名表格之前。
- 新增面板标题为 `复盘线索`，副文案为只读解释研究线索。
- 面板只展示状态、摘要、最多 3 条线索、复盘重点和数据提示。
- 没有展示 raw rule id、provider、accepted latest、run id、IC/RankIC 或训练指标。
- 未与订单、仓位调整、quick-trade 或 broker 控件形成同一操作链。

未发现新增业务分支。

## 3. 前端 Contract 审查

新增 client：

- `getTwStockManualReviewExplanation(params)`
- URL：`${BASE_URL}/manual-review/explanation`
- method：`get`

新增展示字段：

- `overall_status` 的用户文案。
- `summary`。
- `signals.slice(0, 3)`。
- `next_review_focus.slice(0, 3)`。
- `data_quality_notes.slice(0, 3)`。

状态文案符合 R3 工作文档：

- `multi_source_support`：多源支持，仍需复盘。
- `manual_review`：需要人工复盘。
- `caution`：谨慎观察。
- `conflict`：信息冲突。
- `data_insufficient`：数据不足。

空状态和错误状态符合只读语义：

- `正在读取复盘线索...`
- `选择标的后查看只读复盘线索。`
- `补齐资料后再复盘。`
- `复盘线索暂不可用；请稍后重试。`

## 4. 测试与验证

本次复核执行：

- `node frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `corepack pnpm build`，工作目录 `frontend`
- `node frontend/tests/unit/tw-stock-monitor-static-check.mjs`

结果：

- R3 专项静态检查通过：`tw-stock-manual-review-explanation-check passed`。
- 前端 build 通过，Vite build 成功；仍有既有 shell 提示 `/bin/sh: 2: source: not found`，但退出码为 0。
- 既有全页静态检查未通过，失败为：`page contains forbidden text: 卖出`。

对失败原因的审查判断：

- 失败不是 R3 新增 `复盘线索` 面板导致。
- 失败来自既有 `tw-stock-monitor-static-check.mjs` 的扫描口径冲突：该测试先把 `模拟买入/模拟卖出` 从扫描文本中替换掉，但后面仍全页禁止 `卖出`，同时又断言页面必须包含 `模拟买入` 和 `模拟卖出`。
- 旧页面还存在历史模拟、回测、模拟账户等既有文案。按台股安全边界规则，允许在只读历史模拟上下文中出现 buy/sell 类词，但扫描器必须区分“只读历史模拟标签”和“真实交易建议/动作入口”。

结论：

- R3 新增模块通过。
- 全页安全扫描仍未达 R4 收尾条件。
- R4 必须先修复静态扫描口径或分层扫描，不能忽略该失败。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：既有全页静态检查失败，需在 R4 前置修复扫描口径并重新通过。
- Low：无。

### Network Audit

R3 未新增第三方联网、token、provider refresh/publish 或 accepted latest switching。新增 client 只调用本地后端 manual-review GET API。

### Console Audit

R3 未新增 monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 路径。

### Text / Agent Semantics

新增 `复盘线索` 面板未出现买入、卖出、持有、加仓、减仓、目标仓位、目标权重、收益承诺、上涨概率、胜率、下单、连接券商、自动交易、confirmed watch、gate、provider、accepted latest、run id 或 RankIC。

既有页面中的历史模拟/模拟买卖/收益/胜率等旧文案不属于 R3 新增模块，但 R4 必须用更准确的扫描规则验证其只读语境，不能让全页检查继续失败。

### Verdict

R3 新增模块只读安全边界通过；整页最终验收尚未通过。

## 6. 用户第一性原则审查

通过项：

- 简单：面板只显示一个状态、一句摘要、最多 3 条线索和轻量展开区。
- 准确：参数来自已有 qlib 排名行和趋势字段，没有补数据、预测或模型训练。
- 清晰：标题和文案明确是复盘线索，用户能区分 summary、signals、下一步关注点和数据提示。
- 实用：放在研究排名区域，能辅助用户理解某个标的为什么需要继续人工复盘。

注意项：

- 当前前端只传 qlib/trend 字段，技术状态、价格位置、冻结规则卡暂未接入，因此 explanation 可能经常是低完整度或 data_insufficient。这不是 R3 越权，但 R4 验收应确认空状态和数据不足状态可理解。

## 7. 必须修复项

R3 新增模块无必须修复项。

R4 必须修复：

- `frontend/tests/unit/tw-stock-monitor-static-check.mjs` 的全页禁词扫描口径冲突。
- 修复方式必须只改测试/扫描口径或安全检测分层，不得借机修改业务范围、删除只读安全声明、弱化 manual-review 禁止语义。
- 修复后必须重新运行并通过全页静态检查。

## 8. 可暂缓项

继续暂缓：

- 真实完整上下文字段映射。
- 批量 explanation。
- 新页面。
- 新 API。
- 数据库写入。
- provider。
- accepted latest。
- monitor 写入或扫描。
- 新数据源。
- 月营收。
- 模型训练。
- 交易路径。

## 9. 是否需要用户确认

当前不需要用户确认。

理由：

- R3 本身未越权。
- 既有全页静态检查失败属于 R4 验收前置修复问题，不需要改变模块定位。
- 下一步只允许修复扫描口径与执行只读验收，不授权新功能。

若执行者认为需要改业务页面、删除安全声明、接真实账户/仓位、触发 monitor/provider、调用交易路径或新增数据源，必须停止并回报。

## 10. 给执行者的下一步工作文档：Phase R4 静态扫描修复与只读验收

### 10.1 目标

完成人工复盘解释模块的只读验收。

Phase R4 必须先修复既有全页静态检查口径，让扫描能区分：

- 允许的只读历史模拟标签或安全声明。
- 禁止的真实交易建议、交易动作入口、仓位语义、收益/概率承诺。

然后执行后端、前端、静态扫描和必要的只读 smoke 验收。

### 10.2 必读输入

必须读取：

- `docs/tw_manual_review_explanation/PHASER3_EXECUTION_REPORT_CN.md`
- `docs/tw_manual_review_explanation/PHASER3_REVIEW_AND_PHASER4_WORK_CN.md`
- `docs/tw_manual_review_explanation/PHASER2_REVIEW_AND_PHASER3_WORK_CN.md`
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/api/tw-stock.js`
- `backend/app/routes/tw_stock.py`
- `backend/tests/test_tw_manual_review_explanation_api.py`

### 10.3 允许新增或修改

允许：

- 修复 `frontend/tests/unit/tw-stock-monitor-static-check.mjs` 的扫描口径冲突。
- 新增或调整只读安全扫描辅助函数。
- 新增 R4 验收报告：
  - `docs/tw_manual_review_explanation/PHASER4_EXECUTION_REPORT_CN.md`

如已有前端 smoke 基础可用，允许增加轻量只读 smoke，但不得扩大成新 E2E 框架。

### 10.4 扫描修复要求

扫描修复必须满足：

- manual-review 面板仍然零容忍买卖、仓位、收益、概率、provider、accepted latest、run id、RankIC、gate、broker、orders、quick-trade 文案。
- 全页扫描允许明确处于只读历史模拟、安全声明、测试断言中的历史买卖标签。
- 全页扫描不得允许真实交易建议、真实下单动作、目标仓位、收益承诺或上涨概率承诺。
- 不得通过删除安全断言来“通过测试”。
- 不得通过扩大 allowlist 到整页来绕过风险。

建议做法：

- 分区扫描：manual-review 面板严格扫描；历史模拟区按只读上下文扫描。
- 显式允许短语仅限 `模拟买入`、`模拟卖出` 等历史模拟标签，并要求同一区域存在只读/历史模拟/不连接 broker/不生成订单等约束文案。
- 对 `买入`、`卖出`、`收益`、`胜率` 等词保留上下文判断，不能全局放行。

### 10.5 R4 必验命令

至少执行：

- `python -m py_compile backend/app/routes/tw_stock.py backend/app/services/tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py`
- `python -m pytest backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py -q`
- `node frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `node frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- `corepack pnpm build`，工作目录 `frontend`

如执行前端 smoke，必须记录：

- 请求列表。
- 是否出现 POST/PUT/PATCH/DELETE。
- 是否出现 monitor config save、monitor scan、alerts write。
- 是否出现 provider refresh/publish、accepted latest switching。
- 是否出现 broker、quick-trade、orders。

### 10.6 R4 禁止事项

Phase R4 禁止：

- 新增业务功能。
- 新增页面。
- 新增 API。
- 修改 manual-review 业务语义。
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

### 10.7 R4 执行报告必须回答

报告必须包含：

- 当前阶段目标。
- 修改文件。
- 静态扫描修复说明。
- 是否新增业务功能。
- 是否新增页面/API。
- manual-review 面板扫描结果。
- 全页静态扫描结果。
- 后端测试结果。
- 前端构建结果。
- 如有 smoke，列出网络请求审计结果。
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
- 推荐 gate。
- 风险与待审查问题。

### 10.8 R4 Gate

R4 完成后推荐 gate 只能是：

- `manual_review_explanation_module_acceptance_passed`
- `phaser4_acceptance_needs_repair`
- `stop_manual_review_module_scope_invalid`

允许最终通过的最低条件：

- 后端 R1/R2 专项测试通过。
- R3 manual-review 专项静态检查通过。
- 修复后的全页静态检查通过。
- 前端 build 通过。
- 如执行 smoke，危险请求计数为 0。
- 无 monitor/provider/accepted latest/交易路径。
- 无账户仓位、可下单数量、订单状态或交易按钮耦合。
- 无买卖建议、仓位建议、收益承诺或上涨概率/胜率承诺。

完成后等待审查者审核，不得自动宣布最终验收通过。
