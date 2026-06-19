# AgentReadonlyContext 合同

生成日期：2026-06-17

## 1. 目的

`AgentReadonlyContext` 是未来前端嵌入 Agent 的只读上下文占位合同。M 主线 M0-M6 只冻结边界，不实现新 Agent 行为、不新增 tool/action/prompt 能力。

## 2. Required Fields

```text
allowed_context_sources
readonly_artifact_only=true
allowed_question_types
forbidden_answer_semantics
forbidden_tool_calls
no_order_action=true
no_target_position=true
no_provider_publish=true
no_accepted_latest_switch=true
no_monitor_write=true
no_broker_or_order=true
not_in_m0_m6_implementation_scope=true
future_agent_phase_required=true
```

## 3. Allowed Context Sources

```text
ReadonlyStrategySnapshot
ReadonlyReplayWindow
RunRegistry readonly summary
AnalysisArtifact review-approved summary
FrontendReadonlyDisplay visible state
```

## 4. Forbidden Answer Semantics

```text
应该买入
应该卖出
目标仓位/目标权重
保证收益/胜率承诺
自动下单
切换 provider accepted latest
触发 monitor scan
```

## 5. Forbidden Tool Calls

```text
provider publish/refresh
accepted latest switch
monitor config save/scan/alerts write
broker/quick-trade/orders
POST/PUT/PATCH/DELETE trading endpoints
```

## Forbidden Actions

- 不触发 provider publish / refresh。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config / scan / alerts。
- 不触发 broker、quick-trade 或 order。
- 不切默认模型或默认策略。

## 最小 Validator 要求

M1 validator 至少检查 required fields、manifest、schema/audit 文件、forbidden fields、forbidden actions 和只读边界。失败时必须返回明确 status，并支持 `--json`。
