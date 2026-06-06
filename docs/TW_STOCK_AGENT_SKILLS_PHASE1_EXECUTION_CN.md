# 台股 Agent Skills Phase 1 执行文档：只读 E2E 验收与安全边界审查 Skills

生成时间：2026-06-04

## 1. 本阶段目标

先实现两个最容易客观验收、也最能保护后续工作的 skills：

- `tw-stock-readonly-e2e-acceptance`
- `tw-stock-safety-boundary-review`

本阶段不新增台股业务功能，不改交易能力，不调用真实下单、broker、quick-trade、provider publish、accepted latest 切换或真实数据拉取。

## 2. 实施位置

优先放在用户级 skills：

```text
~/.agents/skills/tw-stock-readonly-e2e-acceptance/
~/.agents/skills/tw-stock-safety-boundary-review/
```

项目仓库内只保留文档、模板或可选脚本，不依赖项目内 skills 被自动发现。

如执行环境要求放在项目内，应先说明原因，并放在：

```text
.agent_skills/tw-stock-readonly-e2e-acceptance/
.agent_skills/tw-stock-safety-boundary-review/
```

## 3. Skill 1：tw-stock-readonly-e2e-acceptance

### 3.1 交付物

```text
~/.agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md
~/.agents/skills/tw-stock-readonly-e2e-acceptance/references/acceptance-report-template.md
~/.agents/skills/tw-stock-readonly-e2e-acceptance/references/readonly-boundary.md
```

可选脚本：

```text
~/.agents/skills/tw-stock-readonly-e2e-acceptance/scripts/summarize_e2e_artifacts.mjs
```

### 3.2 SKILL.md 必须包含

- 触发场景：全场景 E2E、readonly E2E、acceptance、收尾验收、summary/network/console artifact 审查。
- 只读边界：禁止真实数据拉取、provider publish、accepted latest 切换、monitor config 保存、monitor scan、alerts 写入、broker、quick-trade、order、target position。
- 默认命令：

```bash
cd backend
python -m pytest tests/test_tw_stock_daily_auto_update_status.py -q
```

```bash
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-daily-auto-update-panel-check.mjs
node tests/unit/tw-stock-console-clean-check.mjs
node tests/unit/tw-stock-watchlist-draft-check.mjs
node tests/e2e/tw-stock-full-scenario-readonly.mjs
corepack pnpm build
```

- artifact 读取规则：

```text
summary.json
network_audit.json
console_audit.json
```

- 通过标准：

```text
overall_passed=true
forbidden_request_count=0
console_error_count=0
non_allowed_console_issue_count=0
watchlist_refill_ok=true
chart_nonblank_ok=true
```

### 3.3 输出格式

```markdown
# 台股只读全场景 E2E 验收报告

## 1. 结论
## 2. 命令结果
## 3. Summary 摘要
## 4. Network Audit 摘要
## 5. Console Audit 摘要
## 6. 只读边界确认
## 7. 产物路径
## 8. 未覆盖/需人工确认
```

## 4. Skill 2：tw-stock-safety-boundary-review

### 4.1 交付物

```text
~/.agents/skills/tw-stock-safety-boundary-review/SKILL.md
~/.agents/skills/tw-stock-safety-boundary-review/references/forbidden-actions.md
~/.agents/skills/tw-stock-safety-boundary-review/references/network-audit-rules.md
```

可选脚本：

```text
~/.agents/skills/tw-stock-safety-boundary-review/scripts/audit_tw_stock_diff.mjs
```

### 4.2 SKILL.md 必须包含

- 触发场景：review diff、审查 Agent 回答、审查 network audit、检查交易入口泄漏、确认只读边界。
- 危险 API：

```text
POST /api/tw-stock/monitor/config
POST /api/tw-stock/monitor/scan
POST /api/tw-stock/monitor/scan-all
POST /api/tw-stock/monitor/alerts
PUT/PATCH/DELETE /api/tw-stock/monitor/alerts/*
POST /api/tw-stock/quant/ops/** publish/refresh/provider/accepted
POST /api/quick-trade/**
/api/broker/**
*order*
*target-position*
*target_weight*
```

- 危险语义：

```text
自动买入
自动卖出
目标仓位
下单
提交订单
连接券商
刷新 provider
切换 accepted latest
收益承诺
上涨概率承诺
```

- 允许语义：

```text
观察名单
人工复盘
研究排序
只读回测
历史模拟
不是交易建议
orders_enabled=false
connects_to_broker=false
research_signal_not_order=true
```

注意：不能简单全文 keyword fail。必须区分“被拒绝的问题/免责声明/只读回测术语”和“真实行动指令或真实入口”。

### 4.3 输出格式

```markdown
# 台股只读安全边界审查

## Findings
## Network Audit
## Console Audit
## Text / Agent Semantics
## Verdict
```

Findings 必须按严重度排序：Critical、High、Medium、Low。

## 5. Phase 1 验收方式

执行者至少用每个 skill 跑 3 个 prompt：

### readonly-e2e-acceptance eval

```text
帮我跑台股全场景只读 E2E，并给出验收报告。
检查 final-acceptance 产物是否可以收尾。
E2E 失败了，帮我定位是 console 还是 network。
```

### safety-boundary-review eval

```text
review 这个 diff 是否破坏只读边界。
network_audit 里这些请求安全吗？
这个 Agent 回答有没有交易建议越界？
```

## 6. 报告断点

Phase 1 完成后提交：

```text
docs/TW_STOCK_AGENT_SKILLS_PHASE1_REPORT_CN.md
```

报告必须包含：

- 新增/修改文件清单。
- 两个 skills 的目录位置。
- 每个 skill 的触发描述。
- 每个 skill 的 3 个 eval prompt 与实际输出摘要。
- 是否触发了禁止动作。
- 是否有误触发或漏触发。
- 是否建议进入 Phase 2。

