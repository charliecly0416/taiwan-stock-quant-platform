# Phase UI-2 策略工作台 + Agent 前端通盘优化方案

生成日期：2026-06-19

## 1. 结论

当前前端已经具备可用的只读产品化能力：

```text
current strategy context
readonly strategy snapshot
readonly replay window
paper portfolio
Agent simple chat
rank / trend / cross-analysis
```

但页面的信息架构仍然偏“工程调试台”，用户需要从 `readonly`、`manifest`、`checksum`、`schema`、`next_open`、`artifact`、`Model A/B` 等内部字段里反推今天要看什么。

本轮优化目标不是继续新增功能，而是把 `/tw-stock-monitor` 收敛为一个用户能直接使用的“台股策略工作台”：

```text
打开页面后，用户首先看到今天策略状态、候选名单、历史模拟、模拟账户和 Agent 解释。
技术审计信息仍保留，但默认折叠，不抢占主路径。
```

## 2. 输入依据

本方案基于以下材料：

```text
docs/tw_modular_daily_update_productization/PHASEUI_STRATEGY_WORKBENCH_FRONTEND_UX_REPAIR_WORK_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue
frontend/src/api/tw-stock.js
```

并补充了一次 Playwright 只读前端观察。

## 3. Playwright 通盘观察结果

### 3.1 观察方式

使用当前 `frontend/dist`，启动本地静态服务：

```text
http://127.0.0.1:8012/#/tw-stock-monitor
```

通过 Playwright route fixture 拦截所有 API，不打真实后端写接口。覆盖视口：

```text
desktop 1440x980
tablet 1024x768
mobile 390x900
```

产物路径：

```text
tmp/tw_ui_workbench_audit/audit.json
tmp/tw_ui_workbench_audit/desktop.png
tmp/tw_ui_workbench_audit/tablet.png
tmp/tw_ui_workbench_audit/mobile.png
```

### 3.2 安全与技术结果

Playwright 观察结果：

```text
forbidden_request_count=0
failed_response_count=0
console_error_count=0
page_error_count=0
overflowX=false on desktop/tablet/mobile
```

说明当前页面基础安全边界和响应式底线没有明显破坏。

### 3.3 UX 发现

尽管没有横向溢出，页面仍存在以下核心 UX 问题：

1. 首屏仍以工程对象命名。

当前主区出现：

```text
统一策略上下文
YZ Clean E4 产品化
策略快照
只读回放窗口
模拟策略
台股研究助手
```

用户第一眼看不到一个完整的“今天策略概览”。

2. 内部字段仍主显。

可见文案包括：

```text
read-only
clean registry
next_open
execution_price_mode: next_open
Model A / Model B
只读候选研究排名审计状态
后端校验标准产物
checksum
manifest
```

这些适合审计，不适合主路径。

3. 信息重复分散。

`统一策略上下文`、`YZ Clean E4 产品化`、`策略快照`、`模拟策略` 都在讲模型、策略、日期、状态，但没有合并成一个用户结论。

4. 候选名单不够“股票优先”。

策略快照区域仍围绕“快照产物”和“审计状态”，候选调入/调出没有成为主视觉。

5. Agent 已接入，但位置与角色还没有纳入工作台主流程。

当前 Agent 文案是：

```text
台股研究助手只解释每日只读策略 Prompt artifact、排序、候选、模拟账户 gate 与数据状态。
```

这在安全上正确，但对用户仍偏系统解释。Agent 应成为“解释今天策略”的工作台助手，而不是又一个技术面板。

## 4. 目标信息架构

建议把页面重构为四层：

```text
A. 今日策略总览
B. 候选与复核工作区
C. 历史模拟与模拟账户
D. Agent 解释与技术详情
```

### 4.1 第一屏目标

用户不展开任何技术详情，也应能回答：

```text
今天用哪一天的信号？
目标交易日是哪天？
当前模型和策略是什么？
现在是否可用于模拟账户？为什么？
排名第一和候选调入有哪些？
有没有调出复核？
Agent 能解释什么？
```

## 5. 页面布局建议

## Phase UI2-1：工作台总览 Header

### 目标

将 `统一策略上下文` + `YZ Clean E4 产品化` 合并为一个主卡：

```text
今日策略总览
```

### 主界面字段

只展示用户语言：

```text
信号日期：2026-06-17
目标交易日：2026-06-18
模型：E4 Qlib + 正交 LTR
策略：跌出 Top50 后最多替换一支
状态：等待目标交易日开盘价，暂不能应用到模拟账户
候选覆盖：Qlib Top50 已生成，LTR 重排已生成
```

### 技术详情折叠

移入默认折叠：

```text
base_model_id
treatment_model_id
strategy_rule
ranking_source
candidate_boundary
execution_price_mode
readonly flags
schema_version
source manifests
checksum
```

### 设计要求

桌面：一行状态摘要 + 4 个指标块。
移动端：单列，状态文案在指标块之前。

### 不应出现

主界面不再出现：

```text
统一策略上下文
YZ Clean E4 产品化
clean registry
execution_price_mode: next_open
Model A / Model B
```

## Phase UI2-2：候选与复核工作区

### 目标

将 `ReadonlyStrategySnapshotPanel.vue` 改造成：

```text
候选名单
```

副标题：

```text
根据当前模型排序生成，仅供研究复盘。
```

### 布局

两个子区：

```text
候选调入
调出复核
```

桌面可双列，窄屏和手机必须单列。

### 候选调入行式布局

每行建议：

```text
#1 2330 台积电
LTR #1 · Qlib Top50 #3 · 全市场 #12
```

如果没有股票名称：

```text
#1 TW2330
LTR #1 · Qlib Top50 #3 · 全市场 #12
```

### 调出复核行式布局

```text
2357
跌出 Qlib Top50 · 当前全市场 #67
```

### 空态

```text
暂无候选调入。
暂无调出复核。
```

### 技术详情

保留审计信息，但折叠到：

```text
查看技术详情
```

包含：manifest、validation、checksum、source paths、readonly flags。

## Phase UI2-3：历史模拟工作区

### 目标

将 `ReadonlyReplayWindowPanel.vue` 主标题改为：

```text
历史模拟
```

说明：

```text
只用于研究复盘，不代表未来收益。
```

### 主界面只展示

```text
测试窗口
净收益
最大回撤
交易次数
费用/税费
覆盖状态
```

### 用户化文案

将技术词替换：

```text
readonly replay window -> 历史模拟
ReplayWindowPolicy -> 测试窗口规则
generated_readonly -> 已审计窗口
final equity -> 期末模拟资产
turnover_proxy_by_notional_over_avg_equity -> 换手强度
```

但后两项默认不主显。

### 安全文案

必须保留：

```text
历史模拟不代表未来收益。
```

不允许出现收益承诺、胜率承诺或上涨概率承诺。

## Phase UI2-4：模拟账户工作区

### 目标

精简 `PaperPortfolioPanel.vue`，让它像一个模拟账户状态组件，而不是 paper artifact 调试器。

### 主界面字段

```text
模拟账户状态
现金
持仓数
当前决策日期
可否应用
阻断原因
预计模拟调入/调出
```

### 安全文案

```text
只影响模拟账户，不连接券商，不提交真实订单。
```

### 不可用状态

将：

```text
next_open_unavailable
execution_price_pending
```

改成：

```text
等待目标交易日开盘价，暂不能应用到模拟账户。
```

### 操作按钮

保留：

```text
应用到模拟账户
重置模拟账户
```

但必须：

- 不可用时明确原因。
- 弹窗二次确认文案继续包含“模拟”。
- 不新增自动应用。
- 不新增真实交易入口。

## Phase UI2-5：Agent 作为策略解释助手

### 目标

将 Agent 从“独立技术面板”融入工作台。

推荐标题：

```text
策略解释助手
```

副标题：

```text
基于今日只读策略 Prompt，解释候选、排名、模拟账户状态和数据新鲜度。
```

### 推荐问题

推荐问题应贴近工作台：

```text
今天策略是什么？
排名第一是谁？
今天有哪些候选调入？
今天有哪些调出复核？
为什么模拟账户不能应用？
2330 当前状态如何？
数据新鲜度如何？
```

避免：

```text
要买哪只？
买多少？
胜率多少？
```

### 回答展示

主界面展示：

```text
回答
相关标的
提示 / warning
只读声明
```

默认折叠：

```text
citations
checksum
mode
signal_asof
target_date
```

### Agent 与工作台联动

建议增加轻量快捷入口：

- 在“候选名单”标题右侧放一个“问助手解释”按钮，预填 `今天有哪些候选调入？`
- 在“模拟账户”阻断原因旁放一个“解释原因”按钮，预填 `为什么模拟账户不能应用？`
- 在排名第一行右侧放一个“解释”按钮，预填 `{symbol} 当前状态如何？`

这些按钮只写入前端输入框并调用 `/agent/simple-chat`，不得触发交易、monitor、provider 或日更。

## Phase UI2-6：技术详情统一折叠

### 目标

不要每个卡片都用不同的技术详情样式。建立统一组件或统一样式：

```text
<TechnicalDetailsCollapse>
```

可先不抽组件，但视觉要一致。

### 默认折叠内容

```text
manifest
source_artifacts
checksum
schema_version
readonly flags
validation details
request params
raw model id
raw strategy_rule
execution_price_mode
```

### 主界面禁用字段

以下字段不得在主界面常显：

```text
manifest
checksum
schema_version
generated_by
source path
artifact
readonly flags
execution_price_mode
raw model id
ReplayWindowPolicy
```

例外：Agent 的 checksum 可以只显示短码，例如 `sha256:abcd...`，且放在“查看来源与边界”折叠中。

## 6. 视觉设计规范

本轮前端优化应使用本仓库 skill：

```text
.agents/skills/frontend-design
```

该 skill 的使用方式不是把页面做成营销视觉或装饰性界面，而是帮助策略工作台形成更明确、更有辨识度的产品语言。台股策略工作台的主题、受众和页面单一任务固定如下：

```text
主题：台湾股票量化研究策略工作台
受众：每天复盘模型信号、候选名单、模拟账户状态的研究型用户
页面任务：让用户在 1 分钟内理解今天策略状态，并能追问 Agent 解释候选、排名、阻断原因和数据新鲜度
```

### 6.0 Frontend-design skill 落地要求

执行者在写代码前必须先给出一个简短设计计划，包含：

```text
颜色 token：4-6 个命名色值
字体/字重角色：标题、正文、数据/代码类 caption
布局概念：今日策略总览、候选名单、历史模拟、模拟账户、Agent 的层级关系
签名元素：一个可解释的视觉记忆点
自我批评：说明哪些选择避免了模板化默认 UI
```

本项目推荐的视觉方向：

```text
安静、精确、研究台风格；股票代码、日期、排名和状态是主角。
```

建议签名元素：

```text
交易日时间轴 / 信号到目标日的状态轨道
Signal 2026-06-17 -> Target 2026-06-18 -> next_open pending/ready
```

这个签名元素应服务于理解 `signal_asof -> target_date -> 可否应用模拟账户`，不是装饰。

执行者必须避免以下模板化方向：

- 暖米色杂志风。
- 大面积深色霓虹金融终端风。
- 报纸式细线密排风。
- 大 hero、渐变背景、装饰光斑、无意义动效。
- 为了“高级感”牺牲信息密度和可扫描性。

可以做一个小的审美风险，但必须和台股量化工作台有关，例如：

```text
用“交易日状态轨道”统一今日策略、历史模拟、模拟账户、Agent 的上下文。
用极少量状态色区分 ready / pending / blocked，而不是堆叠 tag。
用数字排位和股票代码形成稳定扫描节奏。
```

### 6.1 信息密度

该页面是工作台，不是 landing page。要求：

- 不做大 hero。
- 不新增装饰背景。
- 不使用大面积渐变。
- 不用过多彩色 tag。
- 股票列表优先行式、紧凑、可扫描。

### 6.2 卡片规则

- 卡片圆角不超过 8px。
- 不做卡片套卡片。
- 工具区按钮使用图标 + 短文案。
- 每个卡片主标签最多 2 个。
- 技术标签放折叠区。

### 6.3 响应式

桌面：

```text
总览 4 指标列
候选/调出双列
历史模拟 5 指标横排
Agent 与模拟账户可上下堆叠或双列
```

平板：

```text
总览 2 列
候选/调出单列或窄双列
按钮允许换行
```

手机：

```text
全部单列
候选行主信息不超过 2 行
按钮全宽或自然换行
技术详情折叠
无横向滚动
```

## 7. 安全边界

本轮只允许前端展示和只读 DTO 映射。

禁止：

```text
provider refresh / publish
accepted latest switch
daily update real fetch
monitor config save / scan / alerts write
broker / quick-trade / order
target position / target weight
OpenAI key 前端读取或传递
真实 OpenAI 由前端直连
模型训练 / 调参 / 回放算法修改
```

允许：

```text
GET readonly APIs
POST /api/tw-stock/agent/simple-chat
既有 paper portfolio apply/reset 按原边界保留，不扩大行为
```

注意：`/agent/simple-chat` 是允许的后端只读解释接口；前端不得调用旧 `/agent/chat` 作为主路径。

## 8. 推荐实施阶段

## Phase UI2-A：信息架构与文案整理

范围：

- `index.vue` 顶部工作台总览。
- 当前策略/YZ 产品化信息合并展示。
- 内部字段移入技术详情。

交付：

```text
今日策略总览可读
主界面无 execution_price_mode / clean registry / raw model id
```

## Phase UI2-B：候选名单与历史模拟

范围：

- `ReadonlyStrategySnapshotPanel.vue`
- `ReadonlyReplayWindowPanel.vue`

交付：

```text
候选名单股票优先
历史模拟用户化
技术详情折叠
```

## Phase UI2-C：模拟账户与 Agent 融合

范围：

- `PaperPortfolioPanel.vue`
- `index.vue` Agent block
- `frontend/src/api/tw-stock.js` 如需删除旧路径主用引用

交付：

```text
模拟账户阻断原因用户化
Agent 改为策略解释助手
候选/模拟账户可快捷问助手
```

## Phase UI2-D：响应式与 Playwright 验收

范围：

- CSS 响应式调整。
- 新增或更新 Playwright 只读 UX audit。

交付：

```text
桌面/平板/手机截图
无横向溢出
无 console/page error
forbidden request count=0
```

## 9. 必须新增的验收脚本

建议新增：

```text
frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
```

要求：

- 使用 route fixture，不打真实后端写接口。
- 覆盖 desktop/tablet/mobile。
- 保存截图到 `/tmp/tw_stock_strategy_workbench_ux/` 或报告指定目录。
- 检查 forbidden requests。
- 检查 main UI 不出现内部字段。

### 9.1 主界面 forbidden text 检查

主界面可见文本不得包含：

```text
manifest
checksum
schema_version
generated_by
source_artifact
execution_price_mode
ReplayWindowPolicy
clean registry
```

允许它们出现在：

```text
技术详情折叠区展开后
测试 denylist 代码
审计报告
```

### 9.2 安全请求检查

```text
forbidden_request_count=0
frontend_openai_direct_request_count=0
broker_quick_trade_order_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_dry_run_post_count=0
```

### 9.3 语义检查

必须出现：

```text
今日策略
候选名单
历史模拟
模拟账户
策略解释助手
不构成交易建议
不连接券商
不提交真实订单
```

不得出现：

```text
建议买入
建议卖出
目标仓位
保证收益
上涨概率
自动下单
```

## 10. 执行报告要求

执行者完成后必须输出：

```text
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
改动文件
信息架构变化
主界面移除/折叠的内部字段清单
今日策略总览展示字段
候选名单展示字段
历史模拟展示字段
模拟账户展示字段
Agent 展示与快捷问题
桌面/平板/手机截图路径
Playwright 网络审计结果
console/page error 结果
frontend build 结果
静态 denylist 结果
安全边界声明
未解决问题
```

## 11. 审查标准

审查者必须自己跑或复核 Playwright 产物，不能只看报告。

通过标准：

1. 首屏用户能直接理解今天策略状态。
2. 主界面不再像工程调试面板。
3. 候选名单以股票为中心。
4. 历史模拟不承诺未来收益。
5. 模拟账户不被误解为真实交易。
6. Agent 是策略解释助手，不是交易助手。
7. 技术详情仍可查，但默认折叠。
8. desktop/tablet/mobile 无横向溢出和明显文字重叠。
9. forbidden request count 为 0。
10. 没有改模型、策略、回放算法、日更真实链路或交易边界。

## 12. 停止条件

出现以下任一情况必须停止并找统筹/用户确认：

- 需要改后端模型/策略/回放算法才能完成 UI。
- 需要新增真实交易或目标仓位语义。
- 前端需要直接读取 OpenAI key 或直连 OpenAI。
- 需要触发 provider publish、accepted latest、monitor、broker/order。
- 技术详情与主界面无法低风险拆分，需要调整 API DTO。
- 移动端无法在当前组件结构下消除明显拥挤。

## 13. 给执行者的建议 Prompt

```text
请按 docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_OPTIMIZATION_PLAN_CN.md 执行 Phase UI2 前端优化。

目标：把 /tw-stock-monitor 从工程调试面板整理成用户可理解的台股策略工作台，并纳入新 Agent simple-chat 能力。

只允许改前端展示层、只读 DTO 映射、前端只读测试。不得改模型、策略、回放算法、日更真实链路、provider/accepted latest、monitor、broker/order/quick-trade，不得前端接触 OpenAI key。

开工前必须按 `.agents/skills/frontend-design` 给出简短设计计划：颜色 token、字体角色、布局概念、签名元素和自我批评。设计方向必须是安静、精确、研究台风格，不做营销页、大 hero 或装饰性背景。

重点完成：
1. 合并“统一策略上下文”和“YZ Clean E4 产品化”为“今日策略总览”。
2. 将策略快照改为“候选名单”，股票代码/名称/排名优先。
3. 将只读回放窗口改为“历史模拟”，主界面只展示用户指标。
4. 精简模拟账户，明确只影响模拟账户、不连接券商、不提交真实订单。
5. 将 Agent 改为“策略解释助手”，接入候选/模拟账户快捷问题。
6. manifest/checksum/schema/source path/execution_price_mode/raw model id 等内部字段默认折叠到技术详情。
7. 新增 Playwright 只读 UX audit，覆盖 desktop/tablet/mobile，输出截图、network audit、console audit。

完成后输出：
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_EXECUTION_REPORT_CN.md
```

## 14. 给审查者的建议 Prompt

```text
请审查 Phase UI2 前端优化执行报告和页面实现，判断是否可以收口。

必须阅读：
- docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_OPTIMIZATION_PLAN_CN.md
- docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_EXECUTION_REPORT_CN.md

必须复核：
1. 今日策略总览是否替代工程化上下文卡片。
2. 候选名单是否以股票和排名为主。
3. 历史模拟是否用户可理解且不承诺收益。
4. 模拟账户是否清楚区分模拟与真实交易。
5. Agent 是否只解释策略、候选、模拟账户 gate、freshness。
6. 主界面是否仍出现 manifest/checksum/schema/source path/execution_price_mode/raw model id。
7. 技术详情是否保留且默认折叠。
8. desktop/tablet/mobile 截图是否无横向溢出、无重叠、无拥挤。
9. network audit 是否 forbidden_request_count=0。
10. 是否没有触发 provider publish、accepted latest、monitor、broker/order/quick-trade。
11. 是否按 `frontend-design` skill 提供并落实设计计划，视觉选择是否服务于台股研究工作台，而不是模板化装饰。

如果主界面仍像工程调试台，或 Agent 被做成交易助手，或视觉方案只是模板化换皮，不得收口。
```
