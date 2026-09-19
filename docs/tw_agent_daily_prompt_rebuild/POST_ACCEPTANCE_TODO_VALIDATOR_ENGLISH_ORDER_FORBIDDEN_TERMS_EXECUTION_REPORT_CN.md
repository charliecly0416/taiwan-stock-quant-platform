# Post-Acceptance TODO 执行报告：Validator 英文 Order Forbidden Terms 补强

生成日期：2026-06-19

## 1. TODO 目标

本 TODO 只补强 `DailyAgentPromptArtifact` validator 的英文 actionable order 语义拦截，使 artifact 层边界与 Simple Chat 输出层更一致。

目标覆盖：

- `order`
- `orders`
- `place order` / `place orders`
- `submit order` / `submit orders`

本次不重新打开 Phase 0-6 路线，不新增功能，不调用 OpenAI，不生成生产 artifact，不 publish latest。

## 2. 改动文件

- `scripts/validate_tw_agent_daily_prompt_artifact.py`
- `backend/tests/test_tw_stock_agent_daily_prompt_validator.py`
- `docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_EXECUTION_REPORT_CN.md`

未修改 Simple Chat 服务实现、OpenAI adapter、前端、日更编排、API route、artifact builder、默认模型、默认策略或 registry。

## 3. 新增 Forbidden Patterns

在 `FORBIDDEN_PATTERNS` 中新增：

```python
("order", r"\border\b")
("place_order", r"\bplace\s+orders?\b")
("submit_order", r"\bsubmit\s+orders?\b")
```

保留既有：

```python
("orders", r"\borders\b")
("target_position", r"target_position")
("target_weight", r"target_weight")
```

说明：`place_order` / `submit_order` 使用 `orders?` 同时覆盖单数和复数短语。

## 4. 新增 / 更新测试用例

在 `backend/tests/test_tw_stock_agent_daily_prompt_validator.py` 中新增临时 fixture helper：复制 pass sample 到 `tmp_path`，修改 JSON 或 prompt text 后重算 checksum，避免 checksum 错误掩盖 forbidden pattern 测试结果。

新增覆盖：

1. `prompt_context.json` 普通字段出现 `place order for 2330`，validator 必须失败。
2. `prompt_context.json` 普通字段出现 `submit order for 2330`，validator 必须失败。
3. `prompt_text.md` 普通说明行出现 `Use this artifact to place order for 2330.`，validator 必须失败。
4. `prompt_text.md` 安全禁止说明出现 `不能 place order` 和 `Do not place order`，validator 必须通过。
5. `answer_policy.blocked_question_types` / `answer_policy.forbidden_answer_semantics` 出现 `place order` / `submit order`，validator 必须通过。

这些测试复用现有机制：

- `ALLOWED_FORBIDDEN_PATH_PARTS`
- `PROMPT_TEXT_ALLOWED_CONTEXT_MARKERS`

未新增大范围白名单。

## 5. 测试命令与结果

已运行编译检查：

```bash
python -m py_compile scripts/validate_tw_agent_daily_prompt_artifact.py
```

结果：通过。

已运行 validator 单测：

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py -q
```

结果：

```text
10 passed in 0.11s
```

已运行 TODO 要求的 validator + Simple Chat 回归：

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_simple_chat.py -q
```

结果：

```text
26 passed in 1.47s
```

补跑 builder 回归：

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
```

结果：

```text
4 passed in 0.07s
```

## 6. 是否修改 Simple Chat 行为

否。本 TODO 未修改 `backend/app/services/tw_stock_agent_simple_chat.py`，未修改 Simple Chat API route，未修改 OpenAI adapter。

Simple Chat 回归测试通过，确认既有 disabled/mock/blocked/unsafe/citation safety 行为未回归。

## 7. 是否修改 OpenAI / 前端 / 日更 / API

否。

本 TODO 未修改：

- OpenAI adapter。
- 前端代码。
- `/api/tw-stock/agent/simple-chat` route。
- 日更编排。
- artifact builder。
- 默认模型、默认策略、registry。

## 8. 是否触发外部调用或生产写入

否。

执行内容仅包括：

- 修改 validator 与测试文件。
- 运行本地 py_compile / pytest。
- 写入本 TODO 执行报告。

未调用 OpenAI，未联网拉数据，未运行真实日更，未触发 provider publish，未切换 accepted latest，未写 monitor config/scan/alerts，未触发 broker/order/quick-trade，未生成生产 prompt artifact，未 publish latest。

## 9. 残余风险

1. `\border\b` 是更严格的英文单词级拦截，可能在普通正文中拦截非交易含义的 “order”。当前 artifact 合同语境是台股 Agent Prompt，且已有 policy/safety 白名单，本风险可接受。
2. prompt text 的允许逻辑仍依赖行内 marker，例如 `不能`、`Do not`、`blocked`。如果后续安全说明使用新的表达方式，需要同步扩展 `PROMPT_TEXT_ALLOWED_CONTEXT_MARKERS`。
3. validator 的 forbidden terms 仍分散在 validator 和 Simple Chat 输出层，各自测试已覆盖本 TODO 范围；后续可考虑抽共享安全词表，但本 TODO 未扩大范围。

## 10. 是否建议审查通过

建议审查通过。

本 TODO 已满足：

- artifact validator 拦截英文 actionable order 单数/短语。
- 安全禁止说明和 blocked policy 字段不误报。
- Simple Chat 安全测试不回归。
- 无 OpenAI、前端、日更、API 或生产 latest 行为变化。
