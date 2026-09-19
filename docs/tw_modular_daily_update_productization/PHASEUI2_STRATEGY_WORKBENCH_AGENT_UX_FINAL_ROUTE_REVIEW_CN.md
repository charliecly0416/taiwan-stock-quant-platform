# Phase UI2 路线最终复审：策略工作台 + Agent 前端优化

生成日期：2026-06-19

## 1. 复审结论

结论：Phase UI2 路线完善，可以收尾。

依据 `PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_SUMMARY_CN.md`、UI2-A 到 UI2-D 工作/审查文档、Playwright audit 产物和本次新增 PNG 完整性审计，当前 `/tw-stock-monitor` 已从工程调试面板收敛为只读台股策略工作台：

```text
今日策略总览
-> 候选名单
-> 历史模拟
-> 模拟账户状态
-> 策略解释助手
```

本轮未发现需要阻塞收尾的问题。

## 2. 对主路线的符合性

### 2.1 用户主路径

当前主路径已经覆盖用户每天打开页面最需要确认的问题：

- 今天使用哪天信号。
- 目标交易日是哪天。
- 候选调入和调出复核是什么。
- 历史模拟表现如何，以及为什么不代表未来收益。
- 模拟账户为什么可以或不可以应用。
- Agent 能围绕策略上下文解释什么。

工程字段仍保留在技术详情中，但不再抢占主路径。

### 2.2 Agent 融合

Agent 已从泛化研究助手收敛为 `策略解释助手`。

允许路径：

```text
POST /api/tw-stock/agent/simple-chat
```

用途：

```text
只读策略解释
```

未发现前端读取 OpenAI key、前端直连 OpenAI、旧 `/agent/chat` 主路径回流、交易助手化或自动下单语义。

### 2.3 Frontend-design 方向

UI2 路线符合 `.agents/skills/frontend-design` 对“具体 subject、具体用户、具体任务”的要求：

- subject：台股量化研究策略工作台。
- audience：每日复盘信号、候选、模拟和 Agent 解释的研究型用户。
- job：一分钟内理解今日策略状态并追问上下文。

视觉方向保持安静、精确、工作台化，没有转向 landing page、大 hero、模板化装饰、营销式卡片堆叠或交易终端式噪音。

## 3. 只读安全边界

复审未发现以下风险：

```text
broker / quick-trade / order
target position / target weight 写入
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
收益承诺
上涨概率承诺
自动下单语义
Agent 交易助手化
前端 OpenAI key 泄漏
```

`network_audit.json` 关键结果：

```text
request_count=64
simple_chat_request_count=1
forbidden_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_dry_run_post_count=0
failed_response_count=0
```

`console_audit.json` 关键结果：

```text
console_error_count=0
page_error_count=0
```

## 4. Playwright 与 PNG 问题复核

原最终总结中残留风险：

```text
当前对话环境无法内联查看 PNG。
```

本次复现确认：失败原因是当前工具沙箱 helper 的 bwrap loopback 限制，不是 PNG 文件缺失或损坏。

新增补强产物：

```text
tmp/tw_ui2d_workbench_acceptance/png_integrity_audit.json
tmp/tw_ui2d_workbench_acceptance/index.html
```

PNG 完整性审计结果：

```text
all_passed=true

desktop.png  1440x5685  655774 bytes  decode_structural_ok=true
tablet.png   1024x6764  642796 bytes  decode_structural_ok=true
mobile.png   390x9015   572077 bytes  decode_structural_ok=true
```

`index.html` 是本地图集，可直接在浏览器打开核对 desktop/tablet/mobile 三视口截图，不依赖对话内 `view_image`。

因此 PNG 残留风险已从“无法内联查看”降级为“当前对话工具限制已被替代产物缓解”，不再构成 UI2 收尾风险。

## 5. 审查 Findings

Critical：无。

High：无。

Medium：无。

Low：

1. 对话内 `view_image` 仍不可用，但已通过 PNG structural audit 和 HTML 图集替代；不阻塞验收。
2. 后续前端继续优化时，应保持小步推进，避免把技术详情重新放回主路径。

## 6. 是否需要继续 Phase UI2

不需要。

Phase UI2 已具备收尾条件：

- 用户主路径完整。
- Agent 融合完成。
- 技术详情默认折叠。
- Playwright 三视口 audit 通过。
- network/console/page audit 通过。
- PNG 证据可通过本地图集查看。
- 安全边界未扩大。

后续如继续前端优化，应开新线，例如：

```text
Phase UI3：策略工作台细节打磨与长期回归
```

UI3 不应作为 UI2 的阻塞尾项。

## 7. 最终判定

```text
Phase UI2：通过，可收尾。
/tw-stock-monitor：可以作为后续台股策略工作台前端主路径继续产品化。
```
