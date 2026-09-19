# Phase UI2-C 执行报告：模拟账户与 Agent 融合

生成日期：2026-06-19

## 1. Frontend-design 设计计划

主题：台股量化研究策略工作台。

受众：每天复盘模型信号、候选名单、历史模拟、模拟账户状态的研究型用户。

页面任务：让用户在 1 分钟内理解今天策略是否可进入模拟账户，并能追问 Agent 原因。

颜色 token：

- `Desk Ink #111827`：标题、现金、日期、状态主值。
- `Signal Blue #1D4ED8`：只读研究状态、解释助手入口、状态轨道。
- `Paper Surface #FBFDFF`：模拟账户与 Agent 的安静底色。
- `Rule Line #E8EDF3`：研究台分隔线。
- `Review Amber #F59E0B`：等待开盘价、需复核、阻断原因。
- `Ready Green #16A34A`：可应用、已更新。

字体角色：

- 标题：沿用当前 Ant/Vue 标题体系，600 权重，只做区域命名。
- 正文：现有 UI 字体 400/500 权重，表达用户任务和阻断原因。
- 数据：等宽字体仅用于必要的技术详情和短 checksum，不进入主路径。
- 辅助说明：12px 灰色说明，只解释边界，不堆工程字段。

布局概念：`今日策略 -> 候选名单 -> 历史模拟 -> 模拟账户状态 -> 策略解释助手`。模拟账户承接历史模拟，先给出现金、持仓、决策日、可否应用和阻断原因；Agent 接在后面，作为解释入口，而不是交易入口。

签名元素：延续 `Signal -> Target -> Replay -> Paper -> Explain` 的交易日状态轨道。本阶段轻量落在模拟账户的“可否应用/阻断原因/解释原因”联动，以及 Agent 的策略解释问题组。

自我批评：本阶段不做营销页、hero、深色终端、装饰性渐变或卡片套卡片；避免把模拟账户做成 artifact 调试台，也避免把 Agent 做成交易助手。主路径只显示研究用户能立即判断的信息，工程字段默认折叠。

## 2. 改动文件

- `frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_EXECUTION_REPORT_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_EXECUTION_REPORT_CN.md`

未新增后端 API；前端使用 `simpleChatTwStockAgent()` helper 调用既有 `/agent/simple-chat`，用于只读策略解释。

## 3. 模拟账户主界面字段变化

`PaperPortfolioPanel.vue` 标题从 `模拟策略` 改为：

```text
模拟账户状态
```

主说明改为：

```text
只影响模拟账户，不连接券商，不提交真实订单。
```

主界面现在展示：

- 现金
- 持仓数
- 当前决策日期
- 可否应用
- 阻断原因
- 预计模拟调出
- 预计模拟调入
- 跳过与不可应用

主路径不再常显 `epoch`、`decision_id`、`model_id`、`strategy_rule`、artifact path、`apply_id`、`initial_cash` 等工程字段。

## 4. 阻断原因映射

已将以下内部状态统一用户化：

- `next_open_unavailable`
- `execution_price_pending`
- `execution_price_unavailable`

用户文案：

```text
等待目标交易日开盘价，暂不能应用到模拟账户。
```

其他关键文案：

- 无策略：`暂无可应用到模拟账户的策略。`
- 账户变化：`模拟账户已变化，请刷新后重新确认。`

## 5. 折叠技术字段

以下字段保留在默认折叠的 `查看模拟账户技术详情`：

- `paper_account_id`
- `paper_account_epoch`
- `decision_id`
- `model_id`
- `strategy_rule`
- `paper_order_intent_artifact_path`
- `input_checksum`
- `initial_cash`
- `apply_id`
- `raw_block_reason`

源码 DTO 中仍保留 `paper_buy_intent` / `paper_sell_intent` 识别，但主界面映射为 `预计模拟调入` / `预计模拟调出`。

## 6. Agent 改动

Agent 标题从 `台股研究助手` 改为：

```text
策略解释助手
```

副标题改为：

```text
基于今日只读策略 Prompt，解释候选、排名、模拟账户状态和数据新鲜度。
```

推荐问题改为：

- 今天策略是什么？
- 排名第一是谁？
- 今天有哪些候选调入？
- 今天有哪些调出复核？
- 2330 当前状态如何？
- 为什么模拟账户不能应用？
- 数据新鲜度如何？

未加入买入、卖出、胜率、目标仓位、上涨概率等交易助手问题。

## 7. 快捷联动

`PaperPortfolioPanel.vue` 新增 `ask-agent` 事件。模拟账户阻断原因旁新增：

```text
解释原因
```

点击后由 `index.vue` 的 `askAgentFromWorkbench(question)` 处理，只预填并调用现有 `simpleChatTwStockAgent`：

```text
为什么模拟账户不能应用？
```

未新增后端接口，未触发交易、monitor、provider、accepted latest 或日更链路。

## 8. Frontend Build 结果

已运行：

```bash
cd frontend && corepack pnpm build
```

结果：通过，退出码 0。构建开始处仍有既有 shell 初始化提示：

```text
/bin/sh: 2: source: not found
```

但 Vite build 成功。

## 9. 静态检索结果与归因

已运行安全语义检索：

```bash
rg -n "建议买入|建议卖出|目标仓位|保证收益|上涨概率|自动下单|quick-trade|broker|order submit|target_position|target_weight|provider publish|accepted latest|monitor scan|monitor alerts|连接券商|提交真实订单" frontend/src/views/tw-stock-monitor/index.vue frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue frontend/src/api/tw-stock.js
```

命中归因：

- `PaperPortfolioPanel.vue`：`不连接券商`、`不提交真实订单` 均为模拟账户安全声明或二次确认文案。
- `index.vue`：页面级只读声明、历史模拟只读声明、既有 `connects_to_broker=false`/flags 文案、`not_target_position` readonly safety flag、`accepted latest` 文案均为只读/安全边界或数据状态说明。
- 未发现用户可见交易建议、真实交易入口、自动下单入口或目标仓位指令。

已运行内部字段检索：

```bash
rg -n "paper_order_intent_artifact_path|decision_id|apply_id|paper_buy_intent|paper_sell_intent|initial_cash|strategy_rule|model_id|epoch|checksum|schema_version|manifest" frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue frontend/src/views/tw-stock-monitor/index.vue
```

命中归因：

- `PaperPortfolioPanel.vue` 命中位于源码 DTO、写入既有模拟账户 API payload、默认折叠技术详情或中文动作映射。
- `index.vue` 命中来自 UI2-A/Agent/历史模拟已有折叠详情、DTO 映射或只读 safety flag。
- 未在模拟账户主路径常显 artifact path、decision id、model id、strategy rule、apply id、initial cash 等工程字段。

## 10. 边界确认

本次未修改：

- 后端/API 行为。
- 模型、策略、排序、回放算法。
- 日更真实链路。
- provider refresh / publish。
- accepted latest 切换。
- monitor config / scan / alerts 写入。
- broker / quick-trade / order。
- OpenAI key 读取、传递或前端直连。

## 11. 未解决问题

- 未运行 UI2-D 的 Playwright 全量 UX/network/console audit。
- 未新增候选名单到 Agent 的快捷入口；本阶段按文档优先完成模拟账户到 Agent 的低风险联动。

## 12. 是否建议审查通过

建议审查通过。UI2-C 范围内模拟账户主路径、Agent 定位、快捷解释入口、技术详情折叠和安全边界均已按文档完成。
