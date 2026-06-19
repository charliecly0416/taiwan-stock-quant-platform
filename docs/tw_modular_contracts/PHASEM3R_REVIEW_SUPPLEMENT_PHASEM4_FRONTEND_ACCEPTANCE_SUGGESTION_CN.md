# Phase M3R 审查补充与 M4 前端验收建议

生成日期：2026-06-17

## 1. 结论

M3R 没有偏离 Phase M 主线，可以进入 M4。

M3R 已正确修复 M3 阻断项：

```text
既有两小时自动更新脚本默认路径不再可达 provider refresh
既有两小时自动更新脚本默认路径不再可达 provider publish
既有两小时自动更新脚本默认路径不再可达 accepted latest switch
legacy provider/latest 路径保留但必须显式非默认 gate
validator 已从 warning-only 改成 hard gate
测试已覆盖 unsafe 默认可达路径
```

该修复符合 M 主线目标：保留自动化能力，但默认合同路径只作为 readonly orchestrator，不把真实 provider / accepted latest 行为混入模块化研究链路。

## 2. 非阻塞优化建议

M4 工作文档已经覆盖主要范围，但建议执行者在 M4 报告中额外补强以下验收证据，避免“前端整理”变成只做代码移动或只跑静态检查。

### 2.1 前端用户第一性验收

M4 不只是组件拆分，也要证明展示更适合用户阅读。

执行报告应明确：

```text
主视图优先展示模型、策略、窗口、净收益、最大回撤、交易次数、费用、覆盖状态、审计状态
source manifest / checksum / schema version / window index 等工程字段默认进入审计详情或二级区域
页面没有被工程审计字段主导
禁止出现下单、目标仓位、自动交易、保证收益、胜率承诺等语义
```

如果 M4 修改真实前端组件，建议提供：

```text
desktop screenshot
mobile or narrow viewport screenshot
readonly replay panel screenshot
audit detail collapsed / expanded screenshot
```

### 2.2 网络审计必须覆盖 legacy gate 不可见

M4 必须证明前端和 Agent 没有暴露 M3R 新增的 legacy gate。

network audit / static audit 应覆盖：

```text
--enable-legacy-provider-publish 未出现在前端代码、文案、请求参数或 Agent context
TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH 未出现在前端代码、文案、请求参数或 Agent context
provider publish / refresh request count = 0
accepted latest request count = 0
monitor config / scan / alerts write count = 0
broker / quick-trade / orders request count = 0
replay / strategy readonly workflow only GET
```

### 2.3 Agent 未改证明要结构化

M4 文档已经禁止修改 Agent prompt/tool/action，但执行报告应给出可审计证据。

建议至少包含：

```text
Agent prompt 文件或前端 Agent 区域 git diff 摘要
Agent tool/action registry 未变更证明
Agent panel static scan
forbidden tool/action/prompt expansion fixture 通过
```

如果 M4 完全不触碰 Agent，报告应明确：

```text
Agent implementation untouched
Agent contract placeholder only
```

### 2.4 M4 不应再次修改日更脚本

M4 是前端只读展示边界整理，不应继续改 `scripts/run_daily_tw_stock_auto_update.py`。如 M4 必须触碰日更脚本，应停止并另开 M3S/M3RR，而不是混入 M4。

M4 可复跑 M3R audit，但不应扩大 M3R 的 legacy gate 语义。

## 3. 建议补充到 M4 验收门槛

建议 M4 执行报告新增一节：

```text
Frontend user-first acceptance and safety evidence
```

该节至少列出：

```text
component boundary summary
primary fields vs audit fields mapping
desktop/mobile screenshot paths, if frontend changed
GET-only network audit
forbidden request count
forbidden text/semantics scan
Agent untouched or placeholder-only proof
legacy provider gate not exposed proof
frontend build result
E2E result
```

## 4. 审查者 M4 重点

M4 审查时除了看 build/E2E，还要重点确认：

```text
页面是否更清晰，而不是只把旧字段搬到新组件
工程审计字段是否默认弱化但仍可追溯
前端是否没有本地 replay 或本地策略决策
后端窗口校验是否仍是唯一窗口合法性来源
Agent prompt/tool/action 是否未改
legacy provider publish gate 是否未暴露
network audit 是否没有 forbidden request
M3R script audit 是否仍通过
```

如以上任一项失败，应要求 M4 修复，不应进入 M5。
