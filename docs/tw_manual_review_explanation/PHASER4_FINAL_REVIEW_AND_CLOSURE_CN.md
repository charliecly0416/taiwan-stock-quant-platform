# Phase R4 只读验收审查结论与模块收尾文档

审查日期：2026-06-11

审查入口：

- `docs/tw_manual_review_explanation/PHASER4_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_MODULE_PLAN_CN.md`
- `docs/tw_manual_review_explanation/REVIEWER_PROMPT_CN.md`
- `docs/tw_manual_review_explanation/PHASER3_REVIEW_AND_PHASER4_WORK_CN.md`
- `docs/tw_manual_review_explanation/PHASER2_REVIEW_AND_PHASER3_WORK_CN.md`
- `docs/tw_manual_review_explanation/PHASER2_REVIEW_DOC_SELF_AUDIT_CN.md`
- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `docs/tw_decision_model_orthogonal/PHASE2D_CLOSURE_REVIEW_AND_STANDBY_WORK_CN.md`
- `docs/tw_decision_model_fundamental/PHASEF0E_REVIEW_AND_FUNDAMENTAL_STOP_CN.md`

审查产物：

- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `frontend/src/api/tw-stock.js`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `backend/app/routes/tw_stock.py`
- `backend/app/services/tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation_api.py`
- `docs/tw_manual_review_explanation/PHASER4_EXECUTION_REPORT_CN.md`

## 1. 本步审核结论

Phase R4 通过。

人工复盘解释模块验收通过：

- `manual_review_explanation_module_acceptance_passed=true`

执行者没有偏离主线，也没有新增分支：

- R4 只修复前端静态扫描口径。
- 未新增业务功能。
- 未新增页面。
- 未新增 API。
- 未修改 manual-review 业务语义。
- 未修改后端 route。
- 未修改 manual-review 前端面板。
- 未新增数据源。
- 未联网或使用 token。
- 未训练模型。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未触发 monitor config save、monitor scan 或 alerts write。
- 未调用 broker、quick-trade、orders。
- 未读取或展示账户仓位、可下单数量、订单状态或交易按钮。
- 未继续月营收、正交 Phase2E 或 Entry Model。

Gate 结论：

- 接受 `recommended_gate=manual_review_explanation_module_acceptance_passed`。
- 本轮人工复盘解释模块主线到此收尾。
- 执行者不得自动开启新主线、补数据、接真实账户、扩展 provider、扩展 monitor、训练模型或继续产品化功能。

## 2. 主线一致性审查

R4 的目标是修复 R3 留下的全页静态扫描口径冲突，并完成只读验收。

通过项：

- 修改范围仅限 `frontend/tests/unit/tw-stock-monitor-static-check.mjs` 与 R4 执行报告。
- 修复没有改变 manual-review service、route、client 或 UI。
- 修复没有扩大业务功能。
- 修复没有把旧历史模拟文案升级为交易建议。
- 修复后仍保留 manual-review 面板零容忍扫描。

未发现偏离主线或新增分支。

## 3. 静态扫描修复审查

R4 新增：

- `scrubReadonlyHistoricalSimulationText(source)`

审查判断：

- 修复方式是精确上下文 + 精确短语计数，不是整页 allowlist。
- 修复前先要求页面存在只读历史模拟上下文：
  - `只读历史模拟`
  - `历史模拟，不代表未来收益`
  - `不连接券商`
  - `不生成订单`
  - `模拟成交标记`
- 允许剔除的短语有固定次数断言。
- 剔除后仍执行原 forbidden text 扫描。
- manual-review 面板仍由专项测试做严格扫描。

通过。

注意：

- 允许短语中包含 `模拟买入`、`模拟卖出` 等历史模拟标签，符合台股安全边界规则中“只读历史模拟/回测术语允许”的 nuance。
- 这些词不能在后续新功能中被当作真实交易建议或动作入口复用。

## 4. 测试与验证

本次复核执行：

- `python -m py_compile backend/app/routes/tw_stock.py backend/app/services/tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py`
- `python -m pytest backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py -q`
- `node frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `node frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- `corepack pnpm build`，工作目录 `frontend`

结果：

- 后端 py_compile 通过。
- 后端专项 pytest 通过：`11 passed in 1.12s`。
- manual-review 前端专项静态检查通过：`tw-stock-manual-review-explanation-check passed`。
- 全页静态检查通过：`tw-stock-monitor static checks passed`。
- 前端 build 通过，Vite build 成功。
- build 开头仍出现既有 shell 提示 `/bin/sh: 2: source: not found`，但退出码为 0，不影响本次验收。

未执行浏览器 smoke：

- R4 工作文档中 smoke 为可选项。
- 当前已有后端专项、前端专项、全页静态扫描和 build 全部通过。
- 不要求为了 R4 新建 E2E 框架。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：未执行浏览器 smoke，因此没有运行时网络请求清单；当前不阻塞验收。

### Network Audit

未执行浏览器 smoke，所以无浏览器网络请求列表。

基于代码和测试审查：

- manual-review client 仍只调用 `GET /api/tw-stock/manual-review/explanation`。
- R4 未新增第三方联网。
- 未 provider refresh/publish。
- 未 accepted latest switching。

### Console Audit

未发现 R4 新增：

- monitor config save。
- monitor scan。
- alerts write。
- broker。
- quick-trade。
- orders。
- target position / target weight。

仓库既有旧 API client 和旧页面中存在 monitor、sim orders、quant ops 等路径，但不是 R4 新增，也不是 manual-review 模块路径。本次验收只确认 manual-review 模块没有耦合这些路径。

### Text / Agent Semantics

manual-review 面板通过零容忍扫描，未出现：

- 买入。
- 卖出。
- 持有建议。
- 加仓、减仓。
- 目标仓位、目标权重。
- 收益承诺。
- 上涨概率或胜率承诺。
- 下单。
- 连接券商。
- 自动交易。
- confirmed watch。
- gate。
- provider。
- accepted latest。
- run id。
- RankIC。

全页扫描修复后仍保留禁止真实危险语义；只对明确处于只读历史模拟上下文的固定短语做精确剔除。

### Verdict

只读研究安全边界通过。

## 6. 用户第一性原则审查

通过项：

- 简单：最终 UI 只显示少量复盘线索，不扩展成复杂工作台。
- 准确：输出仍来自 R1/R2 contract，不夸大为模型结论。
- 清晰：状态、摘要、signals、下一步关注点和数据提示分层清楚。
- 实用：用户可以在研究排名区域直接看到人工复盘线索。

已知但可接受的暂缓项：

- 前端当前只传 qlib/trend 字段，完整技术状态、价格位置、冻结规则卡尚未从真实只读上下文映射。
- 因此部分解释完整度可能偏低或出现 `data_insufficient`。
- 这不影响当前模块验收，因为本主线目标是完成只读解释链路和安全边界，不是补齐全量真实上下文。

## 7. 必须修复项

当前无必须修复项。

## 8. 可暂缓项

继续暂缓，且不得由执行者自动开启：

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
- 浏览器 smoke 网络审计。

如后续需要这些能力，必须由用户明确开启新阶段或新主线，并重新给审查者工作文档。

## 9. 是否需要用户确认

当前不需要为 R4 验收继续讨论。

但需要用户明确后，才能开启任何后续方向。

原因：

- 人工复盘解释模块已经完成 R0-R4。
- 当前 gate 已通过。
- 后续任何真实上下文字段映射、批量解释、前端扩展、provider、monitor、模型训练或交易相关内容都超出本主线收尾范围。

## 10. 给执行者的后续工作文档：Closure / Standby

### 10.1 当前状态

人工复盘解释模块已完成验收：

- `manual_review_explanation_module_acceptance_passed=true`
- `manual_review_service_done=true`
- `manual_review_readonly_api_done=true`
- `manual_review_frontend_readonly_panel_done=true`
- `manual_review_static_scan_done=true`
- `manual_review_backend_tests_done=true`
- `manual_review_frontend_build_done=true`

### 10.2 允许做的事

仅允许：

- 等待用户下一步明确指令。
- 在用户询问时解释现有模块实现和文件位置。
- 在用户询问时复述当前验收结论。
- 在用户要求时整理现有文档索引。

### 10.3 禁止做的事

在没有用户明确新指令前，禁止：

- 新增业务功能。
- 新增页面。
- 新增 API。
- 接真实完整上下文字段映射。
- 做批量 explanation。
- 保存任何配置。
- 触发 monitor scan。
- 写 alerts。
- 写数据库。
- 联网或使用 token。
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

### 10.4 后续若用户开启新阶段

执行者必须先等待审查者重新给工作文档。

新阶段至少要明确：

- 是否仍保持只读研究。
- 是否需要真实上下文字段映射。
- 是否需要新 API 或前端扩展。
- 是否涉及 provider、accepted latest、monitor、数据库或联网。
- 是否涉及任何交易语义。

不得把本次 R4 通过解读为自动授权后续扩展。
