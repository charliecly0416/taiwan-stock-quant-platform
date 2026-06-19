# FrontendAgentPanel 合同

生成日期：2026-06-17

## 1. 目的

`FrontendAgentPanel` 冻结前端嵌入 Agent 面板在 M 主线内的占位边界。M0-M6 不修改 Agent 行为、prompt、tool 权限或 action 入口；后续如需改动必须另开 Agent 专项主线。

## 2. Required Boundary Fields

```text
readonly_artifact_only
allowed_context_sources
allowed_question_types
forbidden_answer_semantics
forbidden_tool_calls
no_order_action
no_target_position
no_provider_publish
no_accepted_latest_switch
no_monitor_write
no_broker_or_order
not_in_m0_m6_implementation_scope
future_agent_phase_required
```

## 3. Component Boundary

可以读取页面可见 readonly context；不得新增 tool、扩大 action scope、修改 prompt、改写现有 Agent 网络请求行为。

## 4. Forbidden Text / Semantics

```text
一键买入
一键卖出
设置目标仓位
保存监控配置
切换 latest
发布 provider
自动下单
```

## 5. Forbidden Requests

```text
POST /api/agent/*/tools/order
POST /broker/*
POST /quick-trade/*
POST /orders/*
POST /monitor/*/scan
POST /provider/publish
POST /accepted-latest/*
```

## Forbidden Actions

- 不触发 provider publish / refresh。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config / scan / alerts。
- 不触发 broker、quick-trade 或 order。
- 不切默认模型或默认策略。

## 最小 Validator 要求

M1 validator 至少检查 required fields、manifest、schema/audit 文件、forbidden fields、forbidden actions 和只读边界。失败时必须返回明确 status，并支持 `--json`。
