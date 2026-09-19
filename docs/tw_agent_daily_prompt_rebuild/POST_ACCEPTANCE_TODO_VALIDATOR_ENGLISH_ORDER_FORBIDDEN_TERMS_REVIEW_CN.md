# Post-Acceptance TODO 审查意见：Validator 英文 Order Forbidden Terms 补强

生成日期：2026-06-19

## 1. 审查结论

审查结论：通过。

本次 TODO 只补强 `DailyAgentPromptArtifact` validator 对英文 actionable order 单数/短语的拦截，并补充 pass/fail 双路径测试。未发现 OpenAI、前端、日更编排、Simple Chat API、provider publish、accepted latest、monitor、broker/order/quick-trade 相关越界改动。

本审查只覆盖 post-acceptance TODO，不重新审查 Phase 0 到 Phase 6 全路线。

## 2. 审查范围

审查输入：

```text
docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_EXECUTION_REPORT_CN.md
scripts/validate_tw_agent_daily_prompt_artifact.py
backend/tests/test_tw_stock_agent_daily_prompt_validator.py
backend/tests/test_tw_stock_agent_simple_chat.py
```

重点检查：

- 是否只修改 validator 和相关测试。
- 英文 actionable order 单数/短语是否会失败。
- 安全禁止说明和 blocked policy 字段是否不误报。
- Simple Chat 回归是否通过。
- 是否触发或引入写入/交易/provider/monitor/OpenAI/前端行为。

说明：当前工作区包含前序阶段的大量 untracked 文件，`git diff --name-only` 不能完整反映本 TODO 的 untracked 变更边界；本审查以执行报告和相关文件内容核对为准。

## 3. 实现审查

`FORBIDDEN_PATTERNS` 已新增：

```python
("order", r"\border\b")
("place_order", r"\bplace\s+orders?\b")
("submit_order", r"\bsubmit\s+orders?\b")
```

该实现覆盖：

```text
order
place order
place orders
submit order
submit orders
```

并保留既有：

```text
orders
target_position
target_weight
monitor config / scan / alerts
provider publish
accepted latest
broker / quick-trade
```

白名单机制未被放宽：

```text
ALLOWED_FORBIDDEN_PATH_PARTS
PROMPT_TEXT_ALLOWED_CONTEXT_MARKERS
```

审查判断：实现符合 TODO 目标。`\border\b` 可能在 artifact 普通正文中拦截非交易含义的英文 “order”，但在台股 Agent Prompt artifact 语境下这是可接受的保守策略；执行报告也已列为残余风险。

## 4. 测试审查

新增测试覆盖了 TODO 要求的关键路径：

- `prompt_context.json` 普通字段出现 `place order for 2330`：validator 失败。
- `prompt_context.json` 普通字段出现 `submit order for 2330`：validator 失败。
- `prompt_text.md` 普通说明行出现 `Use this artifact to place order for 2330.`：validator 失败。
- `prompt_text.md` 安全禁止说明出现 `不能 place order` / `Do not place order`：validator 通过。
- `answer_policy.blocked_question_types` / `forbidden_answer_semantics` 出现 `place order` / `submit order`：validator 通过。

测试 helper 会复制 pass sample 到 `tmp_path`，修改 JSON 或 prompt text 后重算 checksum，避免 checksum 失败掩盖 forbidden pattern 断言。这个做法合理。

## 5. 台股只读安全边界审查

### Findings

Critical：无。

High：无。

Medium：无。

Low：

1. `\border\b` 是保守拦截，可能拦截少量非交易语境的英文 “order”。当前 artifact 合同语境下可接受，且 policy/safety 字段已有白名单。

### Network Audit

本 TODO 未执行网络审计，也不需要网络审计。

审查确认本 TODO 不需要真实 OpenAI、真实 provider、真实日更或外部数据拉取。

### Console Audit

不适用。本 TODO 未涉及前端浏览器执行。

### Text / Agent Semantics

新增 validator 语义与 Simple Chat 输出层更一致：英文 actionable order 会在 artifact 层提前失败；安全禁止说明和 blocked policy 字段不会误报。未发现实际行动建议、目标仓位建议、收益/上涨概率承诺或 broker/order/quick-trade 入口。

## 6. 复现验证

已复现编译检查：

```bash
python -m py_compile scripts/validate_tw_agent_daily_prompt_artifact.py
```

结果：通过。

已复现 validator + Simple Chat 回归：

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_simple_chat.py -q
```

结果：

```text
26 passed in 1.40s
```

已复现 builder 回归：

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
```

结果：

```text
4 passed in 0.06s
```

## 7. 越界检查

执行报告声明未修改：

- Simple Chat 服务实现。
- OpenAI adapter。
- 前端。
- `/api/tw-stock/agent/simple-chat` route。
- 日更编排。
- artifact builder。
- 默认模型、默认策略、registry。

审查已抽查相关实现与测试，未发现本 TODO 引入上述越界行为。

未发现本 TODO 触发：

- OpenAI 调用。
- 生产 prompt artifact 生成。
- latest publish。
- provider publish。
- accepted latest 切换。
- monitor config/scan/alerts 写入。
- broker/order/quick-trade。

## 8. 残余风险

1. validator 与 Simple Chat 各自维护 forbidden terms，后续仍可能再次出现词表漂移。当前 TODO 不要求抽共享词表，不阻塞通过。
2. prompt text 安全说明白名单依赖 marker，例如 `不能`、`Do not`、`blocked`。后续如果安全说明换新表达，需要同步扩展 marker。

## 9. Verdict

审查 verdict：通过。

本 TODO 已满足：

```text
artifact validator 拦截英文 actionable order 单数/短语
安全禁止说明和 blocked policy 字段不误报
Simple Chat 安全测试不回归
未改 OpenAI/前端/日更/API/生产 latest 行为
未触发 provider/accepted latest/monitor/broker/order/quick-trade
```
