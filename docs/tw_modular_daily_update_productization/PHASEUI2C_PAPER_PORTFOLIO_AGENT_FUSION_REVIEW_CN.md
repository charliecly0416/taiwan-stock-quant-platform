# Phase UI2-C 审查报告：模拟账户与 Agent 融合

生成日期：2026-06-19

## 1. 审查结论

审查结论：通过，允许进入 UI2-D。

UI2-C 已完成本阶段目标：`PaperPortfolioPanel.vue` 从 paper artifact 调试器收敛为“模拟账户状态”，`index.vue` 中 Agent 已改为“策略解释助手”，并新增了模拟账户阻断原因到 Agent 的快捷解释入口。实现未发现真实交易、券商、quick-trade、order、target position、provider publish/refresh、accepted latest 切换或 monitor 写入入口。

需要执行者在后续报告中修正文档口径：独立执行报告第 2 节写了“未修改 `frontend/src/api/tw-stock.js`，未新增 API”，但当前 diff 中确实新增/保留了 `simpleChatTwStockAgent()` helper，并将页面调用从 `chatTwStockAgent` 切到 `/agent/simple-chat`。这不是安全阻塞，因为它使用既有后端 simple-chat 只读解释接口，但报告表述不准确，应在 UI2-D 汇总报告中更正为“未新增后端 API；前端 API helper/调用切换到既有 `/agent/simple-chat`”。

## 2. 审查范围

本次审查：

```text
docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_EXECUTION_REPORT_CN.md
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_EXECUTION_REPORT_CN.md
frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/api/tw-stock.js
```

不提前替 UI2-D 做 Playwright 最终验收。

## 3. 通过项

### 3.1 Frontend-design 落实

执行报告包含主题、受众、页面任务、颜色 token、字体角色、布局概念、签名元素和自我批评。方向符合当前主线：安静、精确、研究台风格；没有做 landing page、大 hero、装饰渐变、深色终端或卡片套卡片。

### 3.2 模拟账户主路径用户化

`PaperPortfolioPanel.vue` 标题已改为：

```text
模拟账户状态
```

主界面展示：

```text
现金
持仓数
当前决策日期
可否应用
阻断原因
预计模拟调出
预计模拟调入
跳过与不可应用
```

主路径不再直接展示 artifact path、decision id、model id、strategy rule、apply id、initial cash 等工程字段。

### 3.3 阻断原因用户化

以下内部状态已映射为用户文案：

```text
next_open_unavailable
execution_price_pending
execution_price_unavailable
```

用户文案为：

```text
等待目标交易日开盘价，暂不能应用到模拟账户。
```

账户变化、暂无策略等状态也已用户化。

### 3.4 技术详情折叠

模拟账户技术字段保留在默认折叠的：

```text
查看模拟账户技术详情
```

包括：

```text
paper_account_id
paper_account_epoch
decision_id
model_id
strategy_rule
paper_order_intent_artifact_path
input_checksum
initial_cash
apply_id
raw_block_reason
```

这符合“技术详情仍可查，但默认折叠”的主线要求。

### 3.5 Agent 角色正确

Agent 标题已改为：

```text
策略解释助手
```

推荐问题集中在策略、排名、候选、调出复核、模拟账户阻断原因和数据新鲜度。未发现“要买哪只、买多少、胜率、目标仓位、上涨概率”等交易助手问题。

模拟账户新增：

```text
解释原因
```

该入口通过 `askAgentFromWorkbench()` 调用现有 `simpleChatTwStockAgent()`，问题为：

```text
为什么模拟账户不能应用？
```

未新增后端接口，未触发交易、monitor、provider、accepted latest 或日更链路。

## 4. 台股只读安全边界审查

### Findings

Critical：无。

High：无。

Medium：无。

Low：

1. 执行报告关于 `frontend/src/api/tw-stock.js` 的表述不准确。实际存在前端 helper/调用切换到 `/agent/simple-chat`。该项不构成安全阻塞，但应在 UI2-D 汇总报告中修正。
2. UI2-D Playwright UX/network/console audit 尚未执行，这是主线计划的下一阶段，不阻塞 UI2-C。

### Network Audit

本阶段未运行浏览器网络审计。源码核对未发现新增 broker、quick-trade、真实 order、target-position、target_weight、provider publish/refresh、accepted latest 切换、monitor config/scan/alerts 写入口。

### Console Audit

本阶段未运行浏览器 console audit。frontend build 已通过。

### Text / Agent Semantics

静态安全检索命中均可归因：

- `不连接券商`、`不提交真实订单`：安全声明或二次确认。
- `connects_to_broker=false`、`orders_enabled=false`：只读边界 flags。
- `not_target_position`：readonly safety flag。
- `accepted latest`：旧页面数据状态说明，不是切换入口。

未发现用户可见交易建议、真实交易入口、自动下单入口、目标仓位指令、收益承诺或上涨概率承诺。

## 5. 复现验证

已运行：

```bash
cd frontend && corepack pnpm build
```

结果：通过，退出码 0。

构建开始处仍出现既有 shell 初始化提示：

```text
/bin/sh: 2: source: not found
```

未阻断 Vite build。

已运行静态安全检索：

```bash
rg -n "建议买入|建议卖出|目标仓位|保证收益|上涨概率|自动下单|quick-trade|broker|order submit|target_position|target_weight|provider publish|accepted latest|monitor scan|monitor alerts|连接券商|提交真实订单" frontend/src/views/tw-stock-monitor/index.vue frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue frontend/src/api/tw-stock.js
```

命中均已归因，未发现阻塞项。

已运行内部字段检索：

```bash
rg -n "paper_order_intent_artifact_path|decision_id|apply_id|paper_buy_intent|paper_sell_intent|initial_cash|strategy_rule|model_id|epoch|checksum|schema_version|manifest" frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue frontend/src/views/tw-stock-monitor/index.vue
```

命中位于源码 DTO、API payload、默认折叠技术详情、旧模块技术详情或只读 DTO 映射；未发现模拟账户主路径常显工程字段。

## 6. 报告修正要求

执行者在 UI2-D 或最终汇总报告中必须修正以下口径：

当前不准确表述：

```text
未修改 frontend/src/api/tw-stock.js，未新增 API。
```

建议修正为：

```text
未新增后端 API；前端 API helper/调用切换到既有 /agent/simple-chat，用于只读策略解释。
```

## 7. 是否放行 UI2-D

放行 UI2-D。

下一阶段应聚焦响应式与 Playwright 只读 UX/network/console 验收，不再扩展功能。重点验证桌面、平板、手机视口下 `/tw-stock-monitor` 的工作台主路径是否无横向溢出、无文字重叠、无危险请求、无 console/page error。
