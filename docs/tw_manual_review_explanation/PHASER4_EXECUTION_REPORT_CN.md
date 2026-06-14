# Phase R4 静态扫描修复与只读验收执行报告

- 生成时间：`2026-06-11T19:18:00+00:00`
- 当前阶段目标：修复既有台股页面全页静态扫描口径冲突，并完成人工复盘解释模块只读验收。
- 执行范围：仅修改前端静态检查口径、执行后端/前端验收命令、生成 R4 报告；未新增业务功能、页面、API 或数据源。

## 1. 修改文件

- 修改 `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- 新增 `docs/tw_manual_review_explanation/PHASER4_EXECUTION_REPORT_CN.md`

本阶段未修改 manual-review 业务语义、后端 route、前端面板或 API client。

## 2. 静态扫描修复说明

修复对象：`frontend/tests/unit/tw-stock-monitor-static-check.mjs`。

修复原因：既有全页 forbidden text 扫描同时要求页面包含 `模拟买入` / `模拟卖出`，又全页禁止 `买入` / `卖出`，导致测试口径冲突。

修复方式：

- 增加 `scrubReadonlyHistoricalSimulationText(source)`。
- 先要求页面中存在只读历史模拟上下文：
  - `只读历史模拟`
  - `历史模拟，不代表未来收益`
  - `不连接券商`
  - `不生成订单`
  - `模拟成交标记`
- 仅对明确属于旧页面只读历史模拟语境的固定短语做精确计数剔除。
- 剔除短语使用精确次数断言，防止整页放行或未来新增敏感词漏过。
- 剔除后仍执行原有 forbidden text 扫描，继续禁止真实交易建议、交易动作入口、仓位语义、收益/概率承诺等。

精确允许短语包括：

- `不新增模拟买入`：1 次
- `模拟买入候选`：2 次
- `才卖出排名最低的一支`：1 次
- `卖出排名最低的一支`：1 次
- `再从 Top10 最高排名补一支`：2 次
- `模拟买入`：1 次
- `模拟卖出`：1 次

manual-review 面板仍由 `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs` 做零容忍扫描，不允许买卖、仓位、收益、概率、provider、accepted latest、run id、RankIC、gate、broker、orders、quick-trade 等文案。

## 3. 是否新增业务功能

否。

## 4. 是否新增页面/API

否。

R4 没有新增页面、route、API client 或前端交互。

## 5. manual-review 面板扫描结果

命令：

- `node frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`

结果：通过。

输出：

- `tw-stock-manual-review-explanation-check passed`

结论：manual-review 面板仍只调用 GET；新增面板内未出现买卖、仓位、收益、概率、provider、accepted latest、run id、RankIC、gate、broker、orders、quick-trade 等禁止语义。

## 6. 全页静态扫描结果

命令：

- `node frontend/tests/unit/tw-stock-monitor-static-check.mjs`

结果：通过。

输出：

- `tw-stock-monitor static checks passed`

结论：修复后的全页扫描可区分只读历史模拟标签和真实危险语义；没有通过删除安全断言或整页 allowlist 绕过风险。

## 7. 后端测试结果

命令：

- `python -m py_compile backend/app/routes/tw_stock.py backend/app/services/tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py`
- `python -m pytest backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py -q`

结果：

- py_compile 通过。
- pytest 通过：`11 passed in 1.13s`。

## 8. 前端构建结果

命令：

- `corepack pnpm build`，工作目录 `frontend`

结果：通过，Vite build 成功。

备注：命令开头仍出现既有 shell 启动提示 `/bin/sh: 2: source: not found`，但最终退出码为 0。

## 9. Smoke 说明

本阶段未执行浏览器 smoke。

原因：R4 工作文档要求“如已有前端 smoke 基础可用，允许增加轻量只读 smoke”，不是强制项；本阶段已通过后端专项、manual-review 专项静态检查、修复后的全页静态检查和前端 build。为避免扩大为新 E2E 框架或触发旧页面写入口，本阶段不新增 smoke。

网络请求审计结果：未执行 smoke，因此无浏览器网络请求列表。

## 10. 安全边界回答

- 是否 POST/PUT/PATCH/DELETE：R4 未新增；manual-review 仍仅 GET。仓库既有旧 API client 中存在其他 post/put 方法，但不是 R4 新增，也不是 manual-review 路径。
- 是否保存配置：否。
- 是否触发 monitor scan：否。
- 是否写 alerts：否。
- 是否读取或展示账户仓位：否。
- 是否展示可下单数量、订单状态或交易按钮：否。
- 是否 provider refresh/publish：否。
- 是否 accepted latest switching：否。
- 是否 broker / quick-trade / orders：否。
- 是否联网/token：否。
- 是否训练模型：否。
- 是否新增数据源：否。
- 是否继续月营收：否。
- 是否继续正交规则探索：否。
- 是否复活 Entry Model：否。
- 是否出现买卖/仓位/收益/概率语义：manual-review 面板无；全页扫描中仅允许精确计数的旧只读历史模拟标签，其余危险语义继续禁止。

## 11. 风险与待审查问题

- R3 前端仍只传 qlib/trend 字段，完整技术状态、价格位置、冻结规则卡尚未从真实只读上下文映射，解释完整度可能偏低或出现 `data_insufficient`。这是已知暂缓项。
- 既有台股研究页仍包含监控、模拟账户、历史模拟、ops 等旧功能；R4 只修复扫描口径，没有改变旧功能边界。
- 本阶段未做浏览器 smoke，因此没有运行时网络请求清单；如审查者要求，可在后续单独授权只读 smoke。

## 12. 推荐 Gate

- recommended_gate：`manual_review_explanation_module_acceptance_passed`
- gate_reason：后端 R1/R2 专项测试通过；manual-review 专项静态检查通过；修复后的全页静态检查通过；前端 build 通过；R4 未新增业务功能、页面、API、数据源或写路径；manual-review 仍保持只读 GET 展示，无 monitor/provider/accepted latest/交易路径，无买卖建议、仓位建议、收益承诺或上涨概率/胜率承诺。

完成后等待审查者审核，不自动进入其他主线。
