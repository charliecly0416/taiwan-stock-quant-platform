# Phase R5 收口 Smoke 与交接报告

- 生成时间：`2026-06-12T00:00:00+00:00`
- 当前阶段目标：在 R4 已通过基础上做一轮收口确认，整理用户交接摘要、执行必跑验证，并评估是否可做只读浏览器 smoke。
- 当前状态：`manual_review_explanation_module_acceptance_passed=true`。

## 1. 修改文件

新增文档：

- `docs/tw_manual_review_explanation/MANUAL_REVIEW_EXPLANATION_HANDOFF_CN.md`
- `docs/tw_manual_review_explanation/PHASER5_CLOSURE_SMOKE_REPORT_CN.md`

本阶段未修改业务代码、测试代码、前端页面、API client、后端 route 或 service。

## 2. 是否新增业务功能

否。

## 3. 是否新增页面/API

否。

## 4. 是否修改 manual-review 业务语义

否。

`复盘线索` 面板仍位于 `frontend/src/views/tw-stock-monitor/index.vue` 的 `今日研究排名` 区域；前端 client 仍只调用：

- `GET /api/tw-stock/manual-review/explanation`

## 5. 必跑验证命令与结果

已执行：

- `python -m py_compile backend/app/routes/tw_stock.py backend/app/services/tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py`
  - 结果：通过。
- `python -m pytest backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py -q`
  - 结果：通过，`11 passed in 1.15s`。
- `node frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
  - 结果：通过，输出 `tw-stock-manual-review-explanation-check passed`。
- `node frontend/tests/unit/tw-stock-monitor-static-check.mjs`
  - 结果：通过，输出 `tw-stock-monitor static checks passed`。
- `corepack pnpm build`，工作目录 `frontend`
  - 结果：通过，Vite build 成功。
  - 备注：命令开头仍出现既有 shell 启动提示 `/bin/sh: 2: source: not found`，但最终退出码为 0。

## 6. 是否执行浏览器 smoke

未执行浏览器 smoke。

原因：R5 要求若执行 smoke，网络请求审计必须确认没有 POST/PUT/PATCH/DELETE。当前现有台股研究页在挂载或刷新流程中会调用既有只读历史模拟接口：

- 前端调用点：`frontend/src/views/tw-stock-monitor/index.vue` 中 `loadRankTechPortfolioPanel()` / `loadPortfolioReplay()`。
- API client：`runTwStockPortfolioReplay()`。
- 后端 route：`POST /api/tw-stock/rank-tech-cross/portfolio-replay`。

该 POST 是既有历史模拟路径，不是 manual-review 新增能力，也不是 R5 授权要修复的内容。但它会使 R5 的“无 POST/PUT/PATCH/DELETE”浏览器网络审计无法满足。

R5 禁止修改业务逻辑、禁用旧功能或新增 smoke-only 分支，因此本阶段没有为了 smoke 改页面行为，也没有新建 E2E 框架绕过该约束。

## 7. 网络请求审计结果

未执行浏览器 smoke，因此无运行时浏览器网络请求列表。

基于代码与静态检查确认：

- manual-review client 只调用 `GET /api/tw-stock/manual-review/explanation`。
- manual-review 后端 route 只注册 `methods=["GET"]`。
- R5 未新增任何 POST/PUT/PATCH/DELETE。
- 仓库既有其他 POST/PUT route 和 API client 存在，但不是 R5 新增，也不是 manual-review 路径。

## 8. 只读边界确认

- 是否 POST/PUT/PATCH/DELETE：R5 未新增；manual-review 仍仅 GET。
- 是否保存配置：否。
- 是否触发 monitor scan：否。
- 是否写 alerts：否。
- 是否 provider refresh/publish：否。
- 是否 accepted latest switching：否。
- 是否 broker / quick-trade / orders：否。
- 是否联网/token：否。
- 是否训练模型：否。
- 是否新增数据源：否。
- 是否继续月营收：否。
- 是否继续正交规则探索：否。
- 是否复活 Entry Model：否。
- 是否出现买卖/仓位/收益/概率语义：manual-review 面板和交接文档没有输出此类语义；交接文档明确说明不能当作交易建议、仓位建议、收益预测或概率预测。

## 9. 用户交接摘要

已新增：

- `docs/tw_manual_review_explanation/MANUAL_REVIEW_EXPLANATION_HANDOFF_CN.md`

该文档包含：

- 用户入口。
- 用户能看到什么。
- 用户不能把它当成什么。
- 当前限制。
- 常见状态与故障提示。
- 开发者索引。
- 后续必须重新授权的事项。

## 10. 风险与待审查问题

- 未执行浏览器 smoke，因此没有运行时网络请求清单。原因是现有页面会触发既有历史模拟 POST，不满足 R5 smoke 的无 POST 审计条件；本阶段不允许修改业务逻辑来规避。
- 当前前端仍只传研究排名和趋势字段，完整技术状态、价格位置、冻结规则卡尚未从真实只读上下文映射，部分标的可能显示 `数据不足` 或线索较少。
- 后续若要做严格浏览器 smoke，需要另行授权处理既有页面挂载时的历史模拟 POST 行为，或提供专门的只读 smoke 入口，但这属于新阶段范围。

## 11. 推荐 Gate

- recommended_gate：`manual_review_explanation_closure_smoke_passed`
- gate_reason：R4 通过状态未被破坏；R5 必跑验证全部通过；已生成用户交接摘要；R5 未新增业务功能、页面、API、写路径、数据源、provider/monitor/accepted latest/交易路径；未输出买卖、仓位、收益或概率语义。浏览器 smoke 未执行的原因已明确记录，属于既有页面网络行为与 R5 smoke 审计条件冲突，不是 manual-review 模块回归。

完成后等待审查者审核，不自动开启新主线。
