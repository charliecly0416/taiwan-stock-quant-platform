# Phase 3 修复复审意见：英文 Order / Target 输出安全校验

生成日期：2026-06-19

## 1. 审查结论

审查结论：通过。

Phase 3 修复已补齐上次阻塞项：Simple Chat 模型输出安全校验现在能阻断英文/字段级 order、target position、target weight 危险语义。允许进入 Phase 4，但范围仅限“前端 Agent 面板简化”，不得改 OpenAI 后端调用策略，不得触发 provider publish、accepted latest、monitor、broker/order/quick-trade。

## 2. 主线一致性判断

本次 repair 只修复 Phase 3 output validator，不进入前端、不新增 API 路由、不做真实 OpenAI smoke。主线仍保持：

```text
DailyAgentPromptArtifact
  -> Simple Chat 后端服务
  -> deterministic safety validation
```

未发现复杂 Agent、多工具调用、外部搜索、交易执行、provider 运维或模型训练扩展。

## 3. 安全边界审查

已复现：

```bash
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py
python -m pytest backend/tests/test_tw_stock_agent_simple_chat.py -q
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
```

结果：

```text
12 passed in 1.12s
9 passed in 0.13s
```

tool/function calling 静态检索：

```bash
rg -n "tool_choice|tools|function_call|functions" backend/app/services/tw_stock_agent_simple_chat.py backend/app/services/tw_stock_agent_openai.py
```

结果：无命中。

危险词静态检索命中均在 blocked/unsafe 词表或测试负样本中，不是执行路径。

前端 OpenAI 静态检索仍命中既有 locale 文案和前端 denylist/assertion；本次 repair 未改前端。

## 4. 修复项审查

`backend/app/services/tw_stock_agent_simple_chat.py` 已新增：

- `order`
- `orders`
- `place order`
- `place orders`
- `submit order`
- `target_position`
- `target-position`
- `target weight`
- `target_weight`

并在 `_is_unsafe_answer(...)` 中复用 Phase 1 `FORBIDDEN_PATTERNS`，使 Simple Chat 输出校验与 artifact validator 的 forbidden patterns 更接近。

## 5. 测试审查

新增测试 `test_english_and_field_level_unsafe_answers_are_overridden` 覆盖：

- `Please place orders for 2330.`
- `Set target_weight to 50% for 2330.`
- `Use target_position for 2330.`
- `Submit order for 2330.`
- `Set target-position to 50%.`

断言包括：

- `blocked is True`
- 包含 `unsafe_model_output_overridden`
- 返回答案不是原始模型输出
- refusal 文案包含“不支持下单”

覆盖足够关闭上次阻塞项。

## 6. Probe 复现

审查者复跑上次失败的本地 mock probe。结果：

```text
Please place orders for 2330. => blocked= True mode= mock answer= 该模块只提供台股研究信息，不支持下单、仓位、自动交易、qlib 运维或收益承诺。
Set target_weight to 50% for 2330. => blocked= True mode= mock answer= 该模块只提供台股研究信息，不支持下单、仓位、自动交易、qlib 运维或收益承诺。
Use target_position for 2330. => blocked= True mode= mock answer= 该模块只提供台股研究信息，不支持下单、仓位、自动交易、qlib 运维或收益承诺。
```

该 probe 只读工作区 fixture、写 `/tmp`，使用 mock adapter，不访问网络，不调用真实 OpenAI。

## 7. 发现的问题

### Low

1. Phase 3 仍未新增 API 路由。
   这不阻塞 Phase 4，但 Phase 4 如需前端接入，必须明确调用现有 `/agent/chat` 还是新增 `/agent/simple-chat`。如新增路由，需在 Phase 4/路由 wiring 审查中单独验证。

2. forbidden patterns 仍分散在 Phase 1 validator 与 simple chat 本地词表。
   本次已复用 Phase 1 `FORBIDDEN_PATTERNS`，风险下降；后续可继续抽成共享安全模块。

## 8. 必须修复项

Phase 3 无剩余必须修复项。

进入 Phase 4 前仍必须遵守：

- 不让前端接触 OpenAI key、base URL 或 SDK。
- 前端只调用后端 `/api/tw-stock/agent/*`。
- 不新增下单、仓位、quick-trade、broker、provider、accepted latest、monitor 操作入口。
- 展示 research-only disclaimer、warnings、citations、mode、signal_asof/target_date/checksum。

## 9. 可后续优化项

- Phase 4 若新增路由，应增加后端路由单测或静态检查，确认它只调用 Simple Chat 服务。
- Phase 6 可用验收问题集复测正常问题和 blocked 问题。
- 后续可统一 forbidden action checker，减少词表漂移。

## 10. 是否允许进入 Phase 4

允许进入 Phase 4。

放行范围仅限：

```text
前端 Agent 面板简化
```

不得提前进入日更编排、真实 OpenAI smoke 或 broker/monitor/provider 相关能力。
