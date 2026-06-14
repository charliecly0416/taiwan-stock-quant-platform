# Phase R3 前端轻量只读展示执行报告

- 生成时间：`2026-06-11T18:48:00+00:00`
- 当前阶段目标：在现有台股研究页面增加轻量“复盘线索”只读展示区，调用 R2 GET API 展示 explanation。
- 执行范围：仅新增前端 GET client、现有页面内轻量展示区、R3 专项静态检查；未新增复杂页面、未新增写接口、未接新数据源。

## 1. 修改文件

- 修改 `frontend/src/api/tw-stock.js`
- 修改 `frontend/src/views/tw-stock-monitor/index.vue`
- 新增 `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- 新增 `docs/tw_manual_review_explanation/PHASER3_EXECUTION_REPORT_CN.md`

## 2. 新增 UI 位置

新增位置：现有页面 `frontend/src/views/tw-stock-monitor/index.vue` 的“今日研究排名”卡片内、排名表格之前。

用户可见标题：`复盘线索`。

该区域不是新页面，不是复杂工作台，不包含批量解释，不展示 raw rule id、provider、accepted latest、run id、IC/RankIC 或训练指标。

## 3. 调用 API

- Route：`/api/tw-stock/manual-review/explanation`
- HTTP method：`GET`
- 前端 client：`getTwStockManualReviewExplanation(params)`

参数来源：当前页面已加载的 qlib 排名行与趋势字段，包括：

- `symbol`
- `name`
- `asof`
- `rank`
- `rankTier`
- `trendLabel`
- `trendScore`

R3 未新增 POST/PUT/PATCH/DELETE；manual-review 模块只调用 GET。

## 4. 页面展示字段

每只股票最多展示：

- 一个状态标签：`multi_source_support` / `manual_review` / `caution` / `conflict` / `data_insufficient` 的用户文案。
- 一句摘要：`summary`。
- 最多 3 条关键线索：`signals.slice(0, 3)`。
- 轻量详情展开区：`next_review_focus` 与 `data_quality_notes`。

状态文案：

- `multi_source_support`：多源支持，仍需复盘
- `manual_review`：需要人工复盘
- `caution`：谨慎观察
- `conflict`：信息冲突
- `data_insufficient`：数据不足

## 5. 空状态与错误状态

- loading：显示 `正在读取复盘线索...`
- empty：显示 `选择标的后查看只读复盘线索。`
- data insufficient / 缺少重点：显示 `补齐资料后再复盘。`
- API error：显示 `复盘线索暂不可用；请稍后重试。`

错误状态只显示只读错误文案，不触发补数据、扫描、保存或 provider 操作。

## 6. 安全边界检查

- 是否新增页面：否。
- 是否 POST/PUT/PATCH/DELETE：否，manual-review 新增 client 仅 `method: 'get'`。
- 是否保存配置：否。
- 是否触发 monitor scan：否。
- 是否写 alerts：否。
- 是否 provider refresh/publish：否。
- 是否 accepted latest switching：否。
- 是否 broker / quick-trade / orders：否。
- 是否联网/token：否。
- 是否训练模型：否。
- 是否新增数据源：否。
- 是否继续月营收主线：否。
- 是否继续正交规则探索：否。
- 是否复活 Entry Model：否。
- 是否出现买卖/仓位/收益/概率语义：R3 新增面板与新增 client 中未出现；相关禁止词仅在 R3 静态检查的 forbidden list 或旧页面既有模拟/回测文案中出现。

## 7. 测试命令与结果

已执行：

- `node frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
  - 结果：通过，输出 `tw-stock-manual-review-explanation-check passed`。
- `corepack pnpm build`，工作目录 `frontend`
  - 结果：通过，Vite build 成功。
  - 备注：命令开头出现 `/bin/sh: 2: source: not found` 的既有 shell 启动提示，但最终退出码为 0。

补充复核：

- `rg -n "manual-review/explanation| getTwStockManualReviewExplanation|loadManualReviewExplanation|manual-review-explanation-panel|method:\s*'(post|put|patch|delete)'" ...`
  - 结果：新增 manual-review API client 为 GET；同一 API 文件存在旧有 post/put 方法，但不是 R3 新增 manual-review 路径。
- `rg -n "买入|卖出|持有建议|加仓|减仓|目标仓位|目标权重|收益承诺|上涨概率|胜率|下单|连接券商|自动交易|confirmed watch|gate|provider|accepted latest|run id|RankIC" ...`
  - 结果：R3 新增面板未命中；命中集中在 R3 静态测试 forbidden list 和旧页面既有模拟/回测/ops 文案。

既有全页静态检查：

- `node frontend/tests/unit/tw-stock-monitor-static-check.mjs`
  - 结果：未通过。
  - 失败原因：该既有测试当前做全页 forbidden text 扫描，命中旧页面原有 `卖出` 文案；同一测试文件后续又断言页面应包含 `模拟卖出`，存在旧测试规则冲突。
  - 本阶段处理：未修改旧模拟/回测相关文案，避免扩大 R3 主线；R3 新增模块已由专项静态检查覆盖并通过。

## 8. 风险与待审查问题

- 当前 R3 只从页面已有 qlib/trend 字段构造 query 参数，没有接真实完整只读上下文；因此技术状态、价格位置、冻结规则卡等字段仍可能由 API 返回 `data_insufficient` 或较低完整度解释。
- 既有台股研究页本身已有监控、模拟账户、历史模拟、ops 等旧功能和文案；R3 未新增这些能力，也未修改旧功能边界。
- 既有 `tw-stock-monitor-static-check.mjs` 存在全页禁词与自身“模拟卖出”断言冲突，需要后续独立修复测试口径；不建议在 R3 中扩大处理。

## 9. 推荐 Gate

- recommended_gate：`request_phaser4_readonly_acceptance_work`
- gate_reason：R3 已在现有台股研究页加入轻量只读“复盘线索”展示区；manual-review 模块只调用 GET API；新增模块无 POST/PUT/PATCH/DELETE、无 monitor/provider/accepted latest/交易路径、无买卖/仓位/收益/概率语义；专项静态检查与前端构建通过。

完成后等待审查者审核，不自动进入 R4。
