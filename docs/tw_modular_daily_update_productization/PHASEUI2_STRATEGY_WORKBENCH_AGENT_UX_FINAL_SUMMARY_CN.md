# Phase UI2 总结文档：策略工作台 + Agent 前端通盘优化

生成日期：2026-06-19

## 1. 总结结论

Phase UI2 已完成并通过最终审查。

本轮路线把 `/tw-stock-monitor` 从偏工程调试台的页面，收敛为用户可直接理解的台股策略工作台：

```text
今日策略总览 -> 候选名单 -> 历史模拟 -> 模拟账户状态 -> 策略解释助手
```

核心结果：

- 用户不展开技术详情，也能理解今天使用哪天信号、目标交易日、模型/策略、候选名单、历史模拟、模拟账户是否可应用，以及 Agent 能解释什么。
- `manifest`、`checksum`、`schema`、`execution_price_mode`、raw model id、artifact path 等工程字段仍保留，但默认折叠，不抢占主路径。
- Agent 被定位为“策略解释助手”，不是交易助手。
- 模拟账户明确只影响模拟账户，不连接券商，不提交真实订单。
- Playwright 只读验收通过，三视口无横向溢出，network/console/page audit 通过。

最终结论：

```text
Phase UI2 可接受。
```

## 2. 主线目标

主线文档：

```text
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_OPTIMIZATION_PLAN_CN.md
```

初始问题：

- 页面主路径偏工程对象命名。
- 用户需要从 `readonly`、`manifest`、`checksum`、`schema`、`next_open`、`artifact`、`Model A/B` 等内部字段反推今天要看什么。
- 候选名单不够股票优先。
- 历史模拟与模拟账户仍像技术产物面板。
- Agent 已接入，但还没有融入工作台主流程。

本轮目标：

```text
打开页面后，用户首先看到今天策略状态、候选名单、历史模拟、模拟账户和 Agent 解释。
技术审计信息仍保留，但默认折叠，不抢占主路径。
```

## 3. 使用的设计与安全约束

### 3.1 Frontend-design 约束

本轮严格按 `frontend-design` skill 调整方向：

- 主题固定为台股量化研究策略工作台。
- 受众是每天复盘模型信号、候选名单、历史模拟和模拟账户状态的研究型用户。
- 页面任务是让用户在 1 分钟内理解今天策略状态，并能追问 Agent。
- 设计风格保持安静、精确、研究台风格。
- 不做 landing page、大 hero、装饰渐变、深色霓虹终端风、暖米色杂志风或卡片套卡片。
- 技术字段默认折叠，主路径以用户语言表达。

### 3.2 台股只读安全边界

本轮持续检查：

- 不新增 broker / quick-trade / order。
- 不新增 target position / target weight 写入。
- 不触发 provider refresh / publish。
- 不切换 accepted latest。
- 不写 monitor config / scan / alerts。
- 不让前端读取或传递 OpenAI key。
- 不把 Agent 做成交易助手。
- 不输出收益承诺、上涨概率承诺或自动下单语义。

允许语境：

- 安全声明。
- 只读 flags。
- 历史模拟。
- 模拟账户。
- 技术详情。
- Agent 对只读策略上下文的解释。

## 4. 阶段总结

## 4.1 UI2-A：今日策略总览 Header

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_REVIEW_CN.md
```

完成内容：

- 将原 `统一策略上下文` 与 `YZ Clean E4 产品化` 合并为 `今日策略总览`。
- 主路径展示：
  - 信号日期。
  - 目标交易日。
  - 模型与策略。
  - 候选覆盖。
  - 榜首标的。
  - 模拟账户状态。
  - 等待目标交易日开盘价等用户化状态说明。
- 将 `base_model_id`、`treatment_model_id`、`strategy_rule`、`ranking_source`、`candidate_boundary`、`execution_price_mode` 等字段移入默认折叠的技术详情。

审查结论：

```text
通过，允许进入 UI2-B。
```

验证：

- `cd frontend && corepack pnpm build` 通过。
- 静态检索确认旧主标题与关键工程字段不再主显。

## 4.2 UI2-B：候选名单与历史模拟

工作文档：

```text
docs/tw_modular_daily_update_productization/PHASEUI2B_CANDIDATES_AND_REPLAY_WORK_CN.md
```

初审报告：

```text
docs/tw_modular_daily_update_productization/PHASEUI2B_CANDIDATES_AND_REPLAY_REVIEW_CN.md
```

Repair 执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEUI2B_CANDIDATES_AND_REPLAY_FIX_EXECUTION_REPORT_CN.md
```

Repair 复审报告：

```text
docs/tw_modular_daily_update_productization/PHASEUI2B_CANDIDATES_AND_REPLAY_FIX_REVIEW_CN.md
```

完成内容：

- `ReadonlyStrategySnapshotPanel.vue` 从 `策略快照` 改为 `候选名单`。
- 主路径拆成：
  - `候选调入`
  - `调出复核`
- 候选行以排名、股票代码/名称、LTR/Qlib/全市场排名摘要为主。
- `ReadonlyReplayWindowPanel.vue` 从 `只读回放窗口` 改为 `历史模拟`。
- 历史模拟主路径展示：
  - 测试窗口。
  - 净收益。
  - 最大回撤。
  - 交易次数。
  - 费用/税费。
  - 覆盖状态。
- `ReplayWindowPolicy`、`final equity`、`turnover_proxy_by_notional_over_avg_equity` 等工程字段从主路径移入技术详情或源码 DTO 映射。

初审发现：

```js
payload[`not_${'target'}_${'position'}`] === true
```

问题不是交易风险，而是动态拼接绕开静态安全检索，削弱可审计性。

Repair 结果：

```js
payload.not_target_position === true
```

该字段恢复为显式 readonly safety flag，静态检索可命中并可归因。

复审结论：

```text
通过，允许进入 UI2-C。
```

验证：

- `cd frontend && corepack pnpm build` 通过。
- 静态安全检索仅命中 `payload.not_target_position === true`，归因为 readonly safety flag。

## 4.3 UI2-C：模拟账户与 Agent 融合

工作文档：

```text
docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_WORK_CN.md
```

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_REVIEW_CN.md
```

完成内容：

- `PaperPortfolioPanel.vue` 从 `模拟策略` 改为 `模拟账户状态`。
- 主路径展示：
  - 现金。
  - 持仓数。
  - 当前决策日期。
  - 可否应用。
  - 阻断原因。
  - 预计模拟调出。
  - 预计模拟调入。
  - 跳过与不可应用。
- 将 `next_open_unavailable`、`execution_price_pending`、`execution_price_unavailable` 映射为：

```text
等待目标交易日开盘价，暂不能应用到模拟账户。
```

- 将 artifact path、decision id、model id、strategy rule、apply id、initial cash 等字段移入 `查看模拟账户技术详情`。
- Agent 从 `台股研究助手` 改为 `策略解释助手`。
- 推荐问题聚焦：
  - 今天策略是什么？
  - 排名第一是谁？
  - 今天有哪些候选调入？
  - 今天有哪些调出复核？
  - 2330 当前状态如何？
  - 为什么模拟账户不能应用？
  - 数据新鲜度如何？
- 模拟账户新增 `解释原因` 快捷入口，只调用既有 `/agent/simple-chat`。

审查发现并要求修正：

执行报告曾写：

```text
未修改 frontend/src/api/tw-stock.js，未新增 API。
```

实际存在前端 helper/调用切换：

```text
simpleChatTwStockAgent() -> /agent/simple-chat
```

该项不是安全阻塞，因为未新增后端 API，且用于只读策略解释；但报告口径必须修正。UI2-D 已修正为：

```text
未新增后端 API；前端使用 simpleChatTwStockAgent() helper 调用既有 /agent/simple-chat，用于只读策略解释。
```

审查结论：

```text
通过，允许进入 UI2-D。
```

验证：

- `cd frontend && corepack pnpm build` 通过。
- 静态安全检索命中均可归因为安全声明、readonly flags、DTO/折叠详情或既有数据状态说明。
- 未发现交易助手问题、真实交易入口、自动下单、目标仓位、收益承诺或上涨概率承诺。

## 4.4 UI2-D：响应式与 Playwright 只读验收

工作文档：

```text
docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_WORK_CN.md
```

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_REVIEW_CN.md
```

新增验收脚本：

```text
frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
```

验收产物：

```text
tmp/tw_ui2d_workbench_acceptance/desktop.png
tmp/tw_ui2d_workbench_acceptance/tablet.png
tmp/tw_ui2d_workbench_acceptance/mobile.png
tmp/tw_ui2d_workbench_acceptance/audit.json
tmp/tw_ui2d_workbench_acceptance/network_audit.json
tmp/tw_ui2d_workbench_acceptance/console_audit.json
```

Playwright 覆盖：

```text
desktop: 1440x980
tablet: 1024x768
mobile: 390x900
```

`audit.json` 结果：

```text
desktop overflowX=false
tablet overflowX=false
mobile overflowX=false
required_text_passed=true
forbidden_visible_passed=true
button_overflow_passed=true
technical_details_default_collapsed=true
```

主界面必须出现文案均通过：

```text
今日策略总览
候选名单
历史模拟
模拟账户状态
策略解释助手
不构成交易建议
不连接券商
不提交真实订单
```

主界面禁显字段未常显：

```text
统一策略上下文
YZ Clean E4 产品化
clean registry
execution_price_mode: next_open
只展示 Model A / Model B
paper_order_intent_artifact_path
ReplayWindowPolicy
final equity
turnover_proxy_by_notional_over_avg_equity
```

`network_audit.json` 结果：

```text
request_count=64
simple_chat_request_count=1
forbidden_request_count=0
forbidden_requests=[]
suspicious_requests=[]
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_dry_run_post_count=0
failed_response_count=0
```

`console_audit.json` 结果：

```text
console_error_count=0
page_error_count=0
console_messages=[]
console_errors=[]
page_errors=[]
```

审查结论：

```text
通过，Phase UI2 可最终接受。
```

## 5. 最终安全结论

本轮 UI2 未发现以下风险：

```text
真实 broker/order/quick-trade 路径
target-position / target_weight 写入
provider refresh / publish
accepted latest 切换
monitor config / scan / alerts 写入
收益承诺
上涨概率承诺
自动下单语义
Agent 交易助手化
前端读取或传递 OpenAI key
```

唯一允许 POST：

```text
POST /api/tw-stock/agent/simple-chat
```

用途：

```text
只读策略解释
```

Playwright 脚本已断言 simple-chat payload 不包含：

```text
target_position
target_weight
```

## 6. 最终 UX 结论

Phase UI2 后，`/tw-stock-monitor` 的主路径已经从工程字段驱动转为用户任务驱动：

| 区域 | Phase UI2 前 | Phase UI2 后 |
|---|---|---|
| 顶部总览 | 统一策略上下文 / YZ Clean E4 产品化 | 今日策略总览 |
| 候选 | 策略快照 / 审计状态 | 候选名单 / 候选调入 / 调出复核 |
| 历史 | 只读回放窗口 / ReplayWindowPolicy | 历史模拟 / 测试窗口 / 净收益 / 回撤 / 费用 |
| 模拟账户 | 模拟策略 / paper artifact | 模拟账户状态 / 可否应用 / 阻断原因 |
| Agent | 台股研究助手 / 技术解释面板 | 策略解释助手 / 工作台快捷解释 |
| 技术字段 | 主路径可见较多 | 默认折叠到技术详情 |

最终页面应能让用户回答：

```text
今天策略用哪天信号？
目标交易日是哪天？
现在为什么不能或可以应用到模拟账户？
候选调入有哪些？
调出复核有哪些？
历史模拟表现如何，但为什么不代表未来收益？
Agent 能解释哪些策略上下文问题？
```

## 7. 验证命令与结果

多阶段均复现：

```bash
cd frontend && corepack pnpm build
```

结果：

```text
通过，退出码 0
```

既有提示：

```text
/bin/sh: 2: source: not found
```

该提示未阻断 Vite build。

最终 Playwright 验收：

```bash
node frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
```

执行报告说明：当前沙箱中 Playwright 需要授权在沙箱外运行，原因是：

```text
bwrap: loopback: Failed RTM_NEWADDR
```

验收产物已生成并通过 JSON audit。

## 8. 残留风险

### Low：当前对话环境无法内联查看 PNG

审查时 `view_image` 受 bwrap 限制，无法在对话内直接打开截图：

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

缓解证据：

- 截图文件存在且为非空大文件。
- Playwright 脚本确实执行 `page.screenshot({ fullPage: true })`。
- `audit.json` 覆盖三视口 DOM 溢出、按钮溢出、必需文案、禁显文案和技术详情折叠。
- 脚本末尾有断言，关键指标失败会让脚本失败。

结论：

```text
不阻塞 Phase UI2 接受。
```

## 9. 后续建议

Phase UI2 已完成本轮收口。后续如果继续前端优化，建议以小步方式推进：

1. 统一所有折叠技术详情的视觉密度和命名方式。
2. 将仍在旧模块中的部分繁体/英文技术说明继续用户化，但不扩大安全边界。
3. 为 Agent 回答区补充更细的空态、阻断态和引用来源排版。
4. 在后续视觉优化中继续保持研究台风格，不转向营销页或装饰性视觉。
5. 将 UI2-D Playwright audit 纳入后续前端回归检查，避免主路径重新被工程字段污染。

## 10. 最终判定

```text
Phase UI2：通过。
/tw-stock-monitor：已可作为台股策略工作台前端主路径继续产品化。
```
