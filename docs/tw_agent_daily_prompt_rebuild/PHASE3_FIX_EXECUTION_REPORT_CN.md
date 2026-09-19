# Phase 3 修复执行报告：补齐英文 Order / Target 输出安全校验

生成日期：2026-06-19

## 1. 修复目标

根据 `docs/tw_agent_daily_prompt_rebuild/PHASE3_REVIEW_CN.md`，本次只修复 Phase 3 未通过项：Simple Chat 模型输出安全校验漏放英文/字段级危险语义。

必须阻断的新增输出语义包括：

- `orders`
- `order`
- `place order`
- `place orders`
- `submit order`
- `target_position`
- `target-position`
- `target weight`
- `target_weight`

本次未进入 Phase 4。

## 2. 实际完成内容

已完成：

- 扩充 `backend/app/services/tw_stock_agent_simple_chat.py` 的 `_unsafe_answer_terms`，覆盖英文 order / target position / target weight 语义。
- `_is_unsafe_answer(...)` 额外复用 Phase 1 `FORBIDDEN_PATTERNS`，让模型输出安全校验与 artifact validator 的 forbidden patterns 保持一致。
- 新增测试 `test_english_and_field_level_unsafe_answers_are_overridden`，覆盖审查要求的英文/字段级危险输出。

## 3. 改动文件列表

本次修复更新：

- `backend/app/services/tw_stock_agent_simple_chat.py`
- `backend/tests/test_tw_stock_agent_simple_chat.py`
- `docs/tw_agent_daily_prompt_rebuild/PHASE3_FIX_EXECUTION_REPORT_CN.md`

未修改：

- 前端。
- API 路由。
- `backend/app/services/tw_stock_agent_openai.py`。
- Phase 2 builder / Phase 1 validator 逻辑。

## 4. 修复细节

`_unsafe_answer_terms` 新增：

```text
order
orders
place order
place orders
submit order
target_position
target-position
target weight
target_weight
```

`_is_unsafe_answer(...)` 现在执行两层检查：

1. simple chat 本地 unsafe terms。
2. Phase 1 `FORBIDDEN_PATTERNS` 正则。

如果任一命中，模型输出会被 deterministic refusal 覆盖，不会原样返回用户。

## 5. 新增测试覆盖

新增测试覆盖以下模型输出：

```text
Please place orders for 2330.
Set target_weight to 50% for 2330.
Use target_position for 2330.
Submit order for 2330.
Set target-position to 50%.
```

每条输出都断言：

- `blocked == true`
- 包含 `unsafe_model_output_overridden` warning
- 返回答案不是原始模型输出
- refusal 文案包含“不支持下单”

## 6. 测试命令与实际结果

已运行：

```bash
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py
```

结果：通过，退出码 0。

```bash
python -m pytest backend/tests/test_tw_stock_agent_simple_chat.py -q
```

结果：

```text
12 passed in 0.98s
```

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
```

结果：

```text
9 passed in 0.11s
```

静态检查：

```bash
rg -n "tool_choice|tools|function_call|functions" backend/app/services/tw_stock_agent_simple_chat.py backend/app/services/tw_stock_agent_openai.py
```

结果：无命中，退出码 1。

```bash
rg -n "quick-trade|broker|orders|target-position|target_weight|monitor config|monitor scan|monitor alerts|/monitor/config|/monitor/scan|/monitor/alerts|provider publish|accepted latest|qlib refresh|retrain|调参" backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py backend/tests/test_tw_stock_agent_simple_chat.py
```

结果：有命中，均为 blocked/unsafe 词表或负样本测试，不是执行路径。

## 7. 审查 Probe 复现

使用 mock adapter 和本地 `/tmp` artifact 复现审查报告中的三条危险输出，结果如下：

```text
Please place orders for 2330. => blocked= True mode= mock answer= 该模块只提供台股研究信息，不支持下单、仓位、自动交易、qlib 运维或收益承诺。
Set target_weight to 50% for 2330. => blocked= True mode= mock answer= 该模块只提供台股研究信息，不支持下单、仓位、自动交易、qlib 运维或收益承诺。
Use target_position for 2330. => blocked= True mode= mock answer= 该模块只提供台股研究信息，不支持下单、仓位、自动交易、qlib 运维或收益承诺。
```

该 probe 不访问网络，不调用真实 OpenAI，只使用 mock adapter。

## 8. 只读安全边界确认

本次修复没有：

- 调用真实 OpenAI。
- 记录或使用真实 OpenAI key。
- 改前端。
- 新增或修改 API 路由。
- 触发 provider publish。
- 切换 provider accepted latest 或 qlib accepted latest。
- 写 monitor config/scan/alerts。
- 触发 broker/order/quick-trade。
- 写 paper account。
- 训练模型、调参或跑回放收益筛选。

## 9. 是否建议复审与进入 Phase 4

建议审查者复审 Phase 3 repair。

如果复审通过，再由审查者决定是否允许进入 Phase 4。本执行者当前停止，不进入 Phase 4。
