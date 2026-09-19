# Post-Acceptance TODO：增强 Agent Prompt Validator 英文交易语义拦截

生成日期：2026-06-19

## 1. 背景

Phase 0 到 Phase 6 最终路线已经通过，可以收尾。最终审查仅留下一个非阻塞 TODO：`DailyAgentPromptArtifact` validator 对英文单数交易语义的覆盖弱于 Simple Chat 输出层。

当前 Simple Chat 已能拦截：

```text
order
orders
place order
place orders
submit order
target_position
target_weight
```

但 artifact validator 当前更偏向：

```text
orders
中文下单/提交订单
target_position
target_weight
```

为了让 artifact 层和输出层边界一致，建议补强 validator 对英文单数/actionable order 语义的拦截。

## 2. 本 TODO 范围

只做一件事：

```text
增强 scripts/validate_tw_agent_daily_prompt_artifact.py 的 forbidden patterns 和测试，确保 DailyAgentPromptArtifact 中出现英文 actionable order 语义时 validator 失败。
```

## 3. 明确不做什么

执行者不得借此重新打开 Agent 路线或扩大范围。

禁止：

- 不改 OpenAI adapter。
- 不调用 OpenAI。
- 不改 Simple Chat API 行为，除非测试发现现有行为回归。
- 不改前端。
- 不改日更编排。
- 不生成生产 prompt artifact。
- 不 publish latest。
- 不触发 provider publish、accepted latest、monitor、broker/order/quick-trade。
- 不改默认模型或默认策略。

## 4. 执行者任务

### 4.1 阅读文件

执行前先阅读：

```text
docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REVIEW_CN.md
docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md
scripts/validate_tw_agent_daily_prompt_artifact.py
backend/tests/test_tw_stock_agent_daily_prompt_validator.py
backend/tests/test_tw_stock_agent_simple_chat.py
```

### 4.2 修改 validator

在 `scripts/validate_tw_agent_daily_prompt_artifact.py` 的 `FORBIDDEN_PATTERNS` 中补齐英文 actionable order 语义。

建议覆盖：

```text
\border\b
\bplace\s+order\b
\bsubmit\s+order\b
\bplace\s+orders\b
\bsubmit\s+orders\b
```

注意：

- 不要因为安全文档中的 forbidden/blocked 描述误报。现有 `ALLOWED_FORBIDDEN_PATH_PARTS` 和 `PROMPT_TEXT_ALLOWED_CONTEXT_MARKERS` 应继续保留。
- 对 prompt text 中的禁止语义，如 “不能 place order”，不应失败。
- 对 prompt_context 的 allowed/blocked policy 字段，不应失败。
- 对实际候选、回答模板、非 policy 正文字段中出现 actionable order，应失败。

### 4.3 补测试

在 `backend/tests/test_tw_stock_agent_daily_prompt_validator.py` 中新增或扩展测试，至少覆盖：

1. `prompt_context.json` 普通字段出现 `place order for 2330`，validator 失败。
2. `prompt_context.json` 普通字段出现 `submit order for 2330`，validator 失败。
3. `prompt_text.md` 普通说明行出现 `place order for 2330`，validator 失败。
4. `prompt_text.md` 安全禁止行出现 `不能 place order` 或 `Do not place order`，validator 不应因此失败。
5. `answer_policy.blocked_question_types` 或 `forbidden_answer_semantics` 中出现 `place order`，validator 不应因此失败。

如果已有测试结构不方便完全覆盖 5 条，至少覆盖 1、2、4，并在执行报告中说明未覆盖项原因。

### 4.4 回归检查 Simple Chat

虽然本 TODO 主要改 validator，也必须跑 Simple Chat 测试，确认没有回归：

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_simple_chat.py -q
```

并运行编译检查：

```bash
python -m py_compile scripts/validate_tw_agent_daily_prompt_artifact.py
```

## 5. 执行者报告要求

执行完成后新增报告：

```text
docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
TODO 目标
改动文件
新增 forbidden patterns
新增/更新测试用例
测试命令与结果
确认未改 OpenAI/前端/日更/API 行为
确认未触发任何写入或外部调用
残余风险
是否建议审查通过
```

## 6. 审查者任务

审查者只审查本 TODO，不重新审查 Phase 0-6 全路线，除非发现新增改动破坏已接受路线。

审查重点：

- 是否只修改 validator 和相关测试。
- 是否没有改 OpenAI、前端、日更、Simple Chat API 行为。
- forbidden patterns 是否能拦截英文 actionable order。
- 是否避免安全说明和 blocked policy 字段误报。
- 测试是否包含 pass/fail 双路径。
- Simple Chat 回归测试是否通过。

审查者输出：

```text
docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_REVIEW_CN.md
```

审查结论只需给：

```text
通过 / 不通过 / 停止沟通
```

## 7. 停止条件

出现以下情况必须停止并找统筹/用户确认：

- 为了修这个 TODO 需要改 Simple Chat API 行为。
- 测试发现现有 Simple Chat blocked/output safety 回归。
- validator 修改导致大量安全政策字段误报，无法低风险区分 allowed policy 与 actionable content。
- 执行者想顺手改前端、OpenAI、日更或 artifact builder。
- 需要真实 OpenAI、真实生产 artifact、publish latest 或任何外部调用。

## 8. 完成定义

本 TODO 完成后应满足：

- artifact validator 拦截英文 actionable order 单数/短语。
- 安全禁止说明和 blocked policy 字段不误报。
- Simple Chat 既有安全测试不回归。
- 无任何产品行为变化。

该 TODO 完成后，Agent 每日 Prompt + OpenAI 简化路线可保持最终收尾状态。
