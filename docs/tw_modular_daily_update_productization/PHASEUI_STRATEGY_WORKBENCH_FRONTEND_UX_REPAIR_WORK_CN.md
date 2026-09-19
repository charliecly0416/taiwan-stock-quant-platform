# Phase UI 策略工作台前端 UX 修复工作文档

生成日期：2026-06-19

## 1. 背景与目标

YZ 路线已经把产品化链路收敛为：

```text
Model A: e4_frozen_qlib_2018_2022
Model B: e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
Production strategy: top50_exit_one_worst_sell
Execution price mode: next_open
```

但当前前端新增模块仍存在明显 UX 问题：

```text
策略快照、只读回放窗口、模拟账户、今日复盘多个卡片连续堆叠
主界面暴露 readonly / manifest / checksum / schema / generated_by 等内部工程字段
用户需要从审计字段中反推今天的策略状态
新增模块和既有 qlib 排名、今日复盘模块视觉风格不一致
候选名单不是以股票排名为主，而是以系统产物字段为主
移动端和窄屏容易出现信息拥挤、标题/标签/说明文字堆叠
```

本轮目标是把当前前端从“工程调试面板”整理成“策略工作台”：

```text
主界面只展示用户能直接理解和使用的信息
技术审计信息保留，但默认折叠到技术详情
今日策略、候选名单、历史模拟、模拟账户之间层级清晰
新增模块视觉上接近既有 qlib 排名和今日复盘模块
保持只读/模拟安全边界，不触发真实交易、provider publish、accepted latest 或 monitor 写入
```

本轮不是重新设计整个系统，不改模型、不改策略、不改回放算法、不改数据产物口径。

## 2. 设计原则

### 2.1 用户第一性

用户打开页面首先要能回答四个问题：

```text
今天用的是哪一天的数据？
现在展示的是哪个模型和策略？
候选调入和调出观察分别是什么？
历史模拟和模拟账户现在是否可用？
```

主界面不得要求用户理解：

```text
artifact
manifest
checksum
schema version
generated_by
source path
readonly flags
ReplayWindowPolicy
execution_price_mode
```

这些字段可以保留在“技术详情”或“审计详情”折叠区，供审查和排错使用。

### 2.2 视觉一致性

新增模块应靠近现有 `今日复盘与历史模拟`、qlib 排名展示的风格：

```text
行式股票列表优先于小卡片堆叠
股票代码、名称、排名是主视觉
解释信息用灰色小字，限制在 1 到 2 行
标题右侧标签最多 2 个
指标卡只展示关键指标，不展示内部 key
主色维持现有蓝/绿/灰，不新增突兀主题色
```

### 2.3 模块边界

本轮只允许修改前端展示层和必要的只读 DTO 映射：

```text
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue
必要时新增纯展示 helper 或格式化函数
必要时新增前端只读测试
```

不得修改：

```text
模型训练逻辑
Qlib score 生成逻辑
LTR rerank 逻辑
策略决策规则
回放收益计算规则
provider accepted latest
daily update publish
broker/order/quick-trade
monitor scan / alert / target position 写入
```

## 3. Phase UI-1：首屏信息架构整理

### 3.1 执行目标

把当前顶部的工程状态展示整理成清晰的业务状态。

建议页面顶部顺序：

```text
今日策略
候选名单
历史模拟
模拟账户
今日复盘与历史模拟
```

若不方便一次性合并组件，至少要做到视觉和文案上形成上述层级。

### 3.2 今日策略卡片

当前 `current-strategy-context-card` 应改造成“今日策略状态”。

主界面只展示：

```text
信号日期
目标交易日
模型
策略
状态
数据覆盖
```

推荐文案：

```text
标题：今日策略
信号日期：2026-06-17
目标交易日：2026-06-18
模型：E4 Qlib + 正交 LTR
策略：跌出 Top50 后最多替换一支
状态：等待开盘价 / 可用于模拟账户 / 数据未更新
数据覆盖：Qlib Top50 已生成，LTR 重排已生成
```

禁止主界面直接展示：

```text
execution_price_mode: next_open
readonly snapshot
manifest
artifact
schema_version
checksum
```

如需解释 next_open，使用用户语言：

```text
等待目标交易日开盘价，暂不能应用到模拟账户。
```

而不是：

```text
execution_price_status = execution_price_unavailable
```

### 3.3 审查标准

审查者必须确认：

```text
用户不看技术详情也能判断今天策略是否可用
首屏没有大段内部工程字段
数据日期、目标交易日、模型、策略、状态没有重复冲突
pending 状态表述清楚，不暗示真实交易
```

## 4. Phase UI-2：策略快照改成候选名单

### 4.1 执行目标

`ReadonlyStrategySnapshotPanel.vue` 不应以“快照产物”为中心，而应以“候选名单”为中心。

标题建议：

```text
候选名单
```

副标题建议：

```text
根据当前模型排名生成，仅供研究复盘。
```

### 4.2 候选调入列表

`top_candidates` 在主界面展示为“候选调入”。

每行建议结构：

```text
#1  2330 台积电
LTR 排名 #1 · Qlib Top50 内 #3 · 全市场 #12
```

要求：

```text
股票代码和名称是主视觉
LTR / Qlib / 全市场排名是辅助信息
最多展示前 10 个
不显示 raw model id
不显示 source path
不显示 checksum
```

如果缺少股票名称，可以只显示代码，但要保持行式布局。

### 4.3 调出观察列表

`exit_candidates` 在主界面展示为“调出观察”。

每行建议结构：

```text
2317 鸿海
已跌出 Qlib Top50 · 当前全市场 #67
```

若为空，空态文案：

```text
暂无调出观察。
```

不要写：

```text
暂无调出候选 / 当前持仓中已跌出候选边界的项目
```

因为用户更关心“今天有没有需要复核的调出”。

### 4.4 技术详情折叠区

保留当前 `ReplayAuditDetail`，但标题改成：

```text
技术详情
```

内部可以继续展示：

```text
source manifest
schema version
validation
checksum
checked files
readonly flags
```

但默认折叠，不得抢占主界面。

### 4.5 审查标准

审查者必须确认：

```text
候选调入/调出观察一眼能看股票和排名
主界面没有 manifest/checksum/schema/source path
候选列表在桌面不拥挤，在移动端单列展示
列表行高稳定，长文本不会挤压按钮或标签
```

## 5. Phase UI-3：只读回放窗口改成历史模拟

### 5.1 执行目标

`ReadonlyReplayWindowPanel.vue` 主界面不再叫“只读回放窗口”，改为用户可理解的：

```text
历史模拟
```

说明文案：

```text
只用于研究复盘，不代表未来收益。
```

避免主界面出现：

```text
ReplayWindowPolicy
标准产物
后端校验
window index
generated_by
checksum pass
```

### 5.2 控件与结果

主控件保留：

```text
窗口选择
查询
刷新
```

但标签要用户化：

```text
固定测试窗口
自定义已审计窗口
```

结果指标只展示：

```text
净收益
最大回撤
交易次数
手续费/税费
覆盖状态
```

建议小字：

```text
费用后
目标窗口内
只读计算
```

不要显示：

```text
final equity
turnover_proxy_by_notional_over_avg_equity
decision_source
```

这些移入技术详情。

### 5.3 审查标准

审查者必须确认：

```text
历史模拟区域能让用户选择窗口并理解结果
训练集禁止窗口/非法窗口仍由后端拒绝
主界面不把历史收益包装成未来承诺
技术审计信息仍可展开查看
```

## 6. Phase UI-4：模拟账户展示精简

### 6.1 执行目标

`PaperPortfolioPanel.vue` 保持独立，但文案要更短、更清楚。

推荐安全说明：

```text
只影响模拟账户，不连接券商，不提交真实订单。
```

pending 文案：

```text
等待目标交易日开盘价，暂不能应用到模拟账户。
```

避免：

```text
next_open 成交价
execution price pending
phaseYZPaperBlocked
```

### 6.2 操作按钮

按钮保留：

```text
应用到模拟账户
重置模拟账户
```

若不可用，按钮附近必须明确原因：

```text
等待开盘价
今天已应用
模拟账户状态已变化，请刷新
```

### 6.3 审查标准

审查者必须确认：

```text
模拟账户不会被误解为真实交易
不可用状态有明确原因
按钮文案和弹窗文案一致
不出现 broker/order/quick-trade/target position 写入
```

## 7. Phase UI-5：响应式与视觉一致性

### 7.1 桌面布局

桌面端建议：

```text
今日策略指标：最多 4 列
候选名单：调入/调出可双列，但每列宽度不足时自动单列
历史模拟指标：最多 5 个关键指标，避免超过两行
```

### 7.2 移动端布局

移动端必须：

```text
所有候选列表单列
按钮换行后仍不挤压文字
长模型名使用友好短名
技术详情默认折叠
指标卡不出现横向滚动
```

### 7.3 CSS 要求

建议统一使用：

```text
8px border-radius
12px 到 16px 卡片内边距
固定 gap
overflow-wrap: anywhere 只用于技术详情，不用于主业务行
业务列表使用 ellipsis 或两行截断
```

不得新增大面积渐变、装饰性背景、无意义图标或新主题色。

## 8. Playwright / E2E 验证要求

执行者需要补齐可重复的前端检查方式。

最低要求：

```text
桌面 1440x980 截图
平板或窄屏 1024x768 截图
手机 390x900 截图
```

如果当前项目没有 `@playwright/test`，允许二选一：

```text
方案 A：使用 npx playwright screenshot 做截图，并在报告中附截图路径
方案 B：正式加入项目内 Playwright 测试依赖，并新增只读视觉 smoke
```

无论采用哪种方案，都必须确认：

```text
没有 console error
没有横向溢出
没有主按钮/标签/股票行文字重叠
没有触发 provider refresh/publish
没有触发 accepted latest 切换
没有触发 broker/order/quick-trade
没有触发 monitor scan/alert/target position 写入
```

## 9. 只读安全边界

本轮前端修复只允许 GET 或读取已有只读状态。

禁止触发：

```text
provider refresh
provider publish
accepted latest switch
daily update real fetch
broker
quick-trade
order
target position
monitor config save
monitor scan
alert write
```

模拟账户按钮本身如果已有产品化 POST 能力，本轮不得扩大其行为边界；只允许调整文案和展示，不允许新增自动应用。

## 10. 执行报告必须包含

执行者最终报告必须写清楚：

```text
修改了哪些组件
哪些内部字段从主界面移到了技术详情
今日策略、候选名单、历史模拟、模拟账户现在分别展示什么
桌面/平板/手机截图路径
前端 build 结果
只读 E2E 或 smoke 结果
安全边界检查结果
是否存在未解决的视觉问题
```

## 11. 审查者检查清单

审查者不得只看报告，必须自己检查代码和页面。

检查项：

```text
1. 主界面是否仍出现 manifest/checksum/schema/source path/generated_by 等内部字段
2. 今日策略是否能直接看懂信号日期、目标交易日、模型、策略、状态
3. 候选名单是否以股票为中心，而不是以产物字段为中心
4. 历史模拟是否清楚说明只读研究、不代表未来收益
5. 模拟账户是否清楚说明不连接券商、不提交真实订单
6. 移动端是否单列、无横向溢出、无文字重叠
7. 是否误改模型、策略、数据产物、回放计算或 daily update 链路
8. 是否触发任何禁止的写入或真实交易相关接口
```

若发现主界面仍像工程调试面板，必须要求返工。

## 12. 给执行者的 Prompt

```text
请按 docs/tw_modular_daily_update_productization/PHASEUI_STRATEGY_WORKBENCH_FRONTEND_UX_REPAIR_WORK_CN.md 执行 Phase UI 前端 UX 修复。

目标是把当前策略快照、只读回放窗口、模拟账户等新增前端块从工程调试面板整理成用户可理解的策略工作台。重点：
1. 今日策略主界面只展示信号日期、目标交易日、模型、策略、状态、数据覆盖。
2. 策略快照改成候选名单，top_candidates 展示为候选调入，exit_candidates 展示为调出观察，行式股票列表优先。
3. 只读回放窗口改成历史模拟，主界面只展示净收益、最大回撤、交易次数、费用、覆盖状态。
4. manifest/checksum/schema/source path/generated_by/readonly flags 等内部字段必须移入默认折叠的技术详情。
5. 模拟账户文案精简，明确只影响模拟账户、不连接券商、不提交真实订单。
6. 保持只读安全边界，不改模型、不改策略、不改回放算法、不改 daily update/provider/accepted latest/monitor/broker/order 链路。
7. 必须做桌面、平板或窄屏、手机视口检查，并在报告中给出截图路径、build/smoke/E2E 和安全边界结果。

完成后输出执行报告：
docs/tw_modular_daily_update_productization/PHASEUI_STRATEGY_WORKBENCH_FRONTEND_UX_REPAIR_EXECUTION_REPORT_CN.md
```

## 13. 给审查者的 Prompt

```text
请审查 docs/tw_modular_daily_update_productization/PHASEUI_STRATEGY_WORKBENCH_FRONTEND_UX_REPAIR_EXECUTION_REPORT_CN.md，并按 docs/tw_modular_daily_update_productization/PHASEUI_STRATEGY_WORKBENCH_FRONTEND_UX_REPAIR_WORK_CN.md 判断是否可以收口。

重点确认：
1. 是否真的把主界面从工程调试面板改成用户可理解的策略工作台。
2. 今日策略是否清楚展示信号日期、目标交易日、模型、策略、状态、数据覆盖。
3. 候选名单是否以股票代码/名称/排名为中心，top_candidates 和 exit_candidates 是否表达清楚。
4. 历史模拟是否避免 replay/window/checksum/manifest 等内部词主显。
5. 技术审计信息是否保留在默认折叠详情中，而不是被删除。
6. 桌面、窄屏、手机是否无文字拥挤、无横向溢出、无按钮/标签重叠。
7. 是否没有改模型、策略、回放算法、数据产物口径或 daily update 链路。
8. 是否没有触发 provider publish、accepted latest、monitor 写入、broker/order/quick-trade。

如果仍有用户看不懂、信息拥挤、内部字段主显或安全边界问题，请不要收口，给出明确返工项。
```
