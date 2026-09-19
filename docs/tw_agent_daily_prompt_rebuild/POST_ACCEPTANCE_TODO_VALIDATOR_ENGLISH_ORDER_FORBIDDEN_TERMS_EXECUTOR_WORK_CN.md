# 执行者工作文档：Post-Acceptance TODO - Validator 英文 Order Forbidden Terms 补强

生成日期：2026-06-19

## 1. 任务结论先行

这是 Phase 0 到 Phase 6 已接受路线后的一个小型安全补测/补强 TODO，不重新打开 Agent 路线，不新增功能。

执行目标只有一个：

```text
让 DailyAgentPromptArtifact validator 对英文 actionable order 单数/短语语义的拦截，与 Simple Chat 输出层保持一致。
```

完成后提交执行报告：

```text
docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_EXECUTION_REPORT_CN.md
```

## 2. 背景

最终路线已通过：

```text
DailyAgentPromptArtifact
  -> TWStockAgentSimpleChatService
  -> /api/tw-stock/agent/simple-chat
  -> 前端 Agent 面板只读展示
  -> disabled/mock OpenAI 安全路径
  -> 日更默认关闭/dry-run 的 Agent prompt build gate
```

Simple Chat 输出层已经能拦截英文危险语义：

```text
order
orders
place order
place orders
submit order
target_position
target_weight
```

但 artifact validator 当前对英文单数/actionable order 的覆盖弱一些。这个 TODO 用来补齐 artifact 层边界，避免危险语义更早一层进入 DailyAgentPromptArtifact。

## 3. 严格范围

允许修改：

```text
scripts/validate_tw_agent_daily_prompt_artifact.py
backend/tests/test_tw_stock_agent_daily_prompt_validator.py
```

仅当回归测试发现 Simple Chat 安全测试需要同步 fixture 或断言时，才允许最小修改：

```text
backend/tests/test_tw_stock_agent_simple_chat.py
```

默认不应修改 Simple Chat 服务实现。

禁止修改：

- OpenAI adapter。
- Simple Chat API 行为。
- 前端。
- 日更编排。
- artifact builder。
- 默认模型、默认策略、registry。
- 生产 artifact 或 latest pointer。

禁止执行：

- 不调用 OpenAI。
- 不生成生产 prompt artifact。
- 不 publish latest。
- 不触发 provider publish。
- 不切换 accepted latest。
- 不写 monitor config/scan/alerts。
- 不触发 broker/order/quick-trade。
- 不做任何外部数据拉取。

## 4. 执行前必须阅读

先读以下文件，不要跳过：

```text
docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_WORK_CN.md
docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REVIEW_CN.md
docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md
scripts/validate_tw_agent_daily_prompt_artifact.py
backend/tests/test_tw_stock_agent_daily_prompt_validator.py
backend/tests/test_tw_stock_agent_simple_chat.py
```

阅读重点：

- validator 当前如何识别 forbidden patterns。
- 哪些路径或 policy 字段允许出现 forbidden 词作为安全说明。
- Simple Chat 当前拦截哪些英文 order/target terms。
- 测试 fixture 的复制和局部修改方式。

## 5. 实现要求

### 5.1 Validator forbidden patterns

在 `scripts/validate_tw_agent_daily_prompt_artifact.py` 的 `FORBIDDEN_PATTERNS` 中补齐英文 actionable order 语义。

最低覆盖：

```text
\border\b
\bplace\s+order\b
\bsubmit\s+order\b
\bplace\s+orders\b
\bsubmit\s+orders\b
```

可以根据现有代码风格合并正则，例如：

```text
\bplace\s+orders?\b
\bsubmit\s+orders?\b
```

但必须确保单数 `order` 本身可以拦截实际正文中的 actionable order 语义。

### 5.2 避免误报

不能因为安全政策和禁止说明本身出现 forbidden terms 就失败。

应继续允许：

```text
不能 place order
Do not place order
禁止 submit order
blocked question types: place order
forbidden answer semantics: submit order
```

应失败：

```text
place order for 2330
submit order for 2330
Please place order for 2330
Use this artifact to submit order for 2330
```

执行时优先复用现有机制：

```text
ALLOWED_FORBIDDEN_PATH_PARTS
PROMPT_TEXT_ALLOWED_CONTEXT_MARKERS
```

不要用大范围白名单绕过普通正文。

## 6. 测试要求

在 `backend/tests/test_tw_stock_agent_daily_prompt_validator.py` 中新增或扩展测试，至少覆盖以下 5 类。

必须失败的路径：

1. `prompt_context.json` 普通字段出现：

```text
place order for 2330
```

validator 必须失败。

2. `prompt_context.json` 普通字段出现：

```text
submit order for 2330
```

validator 必须失败。

3. `prompt_text.md` 普通说明行出现：

```text
place order for 2330
```

validator 必须失败。

必须通过的路径：

4. `prompt_text.md` 安全禁止说明出现：

```text
不能 place order
Do not place order
```

validator 不应因此失败。

5. `answer_policy.blocked_question_types` 或 `forbidden_answer_semantics` 出现：

```text
place order
submit order
```

validator 不应因此失败。

如果现有 fixture 结构让 5 条完整覆盖成本过高，至少覆盖 1、2、4，并在执行报告中明确说明未覆盖项和原因。但推荐完整覆盖 5 条。

## 7. 必跑命令

先跑编译检查：

```bash
python -m py_compile scripts/validate_tw_agent_daily_prompt_artifact.py
```

再跑 validator 和 Simple Chat 回归：

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_simple_chat.py -q
```

如果你改动测试 helper 或 fixture 影响 builder，也补跑：

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
```

禁止用真实 OpenAI、真实日更、真实 provider、真实 publish 来验证本 TODO。

## 8. 执行报告要求

新增报告：

```text
docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
1. TODO 目标
2. 改动文件
3. 新增 forbidden patterns
4. 新增/更新测试用例
5. 测试命令与结果
6. 是否修改 Simple Chat 行为
7. 是否修改 OpenAI/前端/日更/API
8. 是否触发外部调用或写入
9. 残余风险
10. 是否建议审查通过
```

报告中必须明确写：

```text
未调用 OpenAI
未改前端
未改日更编排
未 publish latest
未触发 provider publish / accepted latest
未触发 monitor / broker / order / quick-trade
```

## 9. 停止条件

出现以下任一情况，停止执行并向审查者/统筹说明，不要自行扩大范围：

- 需要修改 Simple Chat API 行为才能完成。
- Simple Chat 既有安全测试回归。
- validator 修改导致大量 policy 字段误报，无法低风险区分 allowed policy 与 actionable content。
- 需要改前端、OpenAI adapter、日更编排或 artifact builder。
- 需要真实 OpenAI、真实生产 artifact、publish latest 或外部调用。
- 发现 artifact 合同本身需要重新设计。

## 10. 审查者验收口径

审查者只审查本 TODO，不重新审 Phase 0 到 Phase 6 全路线。

通过条件：

- 改动集中在 validator 和相关测试。
- 英文 actionable order 单数/短语会被 artifact validator 拦截。
- 安全禁止说明和 blocked policy 字段不误报。
- Simple Chat 回归测试通过。
- 没有 OpenAI、前端、日更、provider、accepted latest、monitor、broker/order/quick-trade 相关改动或执行。

审查输出文件将是：

```text
docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_REVIEW_CN.md
```

审查结论只给：

```text
通过 / 不通过 / 停止沟通
```
