# 台股 Agent 每日 Prompt + OpenAI 重构执行与审查计划

生成日期：2026-06-19

本文是 `TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md` 的执行拆解与审查协作手册。执行者和审查者必须紧贴该设计文档，不得把本路线扩展成复杂 Agent、多工具调用、交易执行、provider 运维或模型训练路线。

## 1. 总原则

本路线目标只有一个：

```text
把每日模型、策略、组合和数据状态压缩成只读 DailyAgentPromptArtifact，
再用一个简单后端 OpenAI 接口回答用户的高频台股研究问题。
```

执行者每一步完成后必须提交工作报告。审查者审查后必须提交审查意见，并给出下一步工作文档。任何一方发现偏离路线、边界不清或需要产品口径确认时，必须停止并与用户和统筹沟通。

## 2. 角色分工

### 2.1 统筹

统筹负责判断路线是否仍符合项目宪法和大设计文档。统筹不是替执行者补代码，也不是替审查者放行。

统筹关注：

- 是否仍是 readonly research Agent。
- 是否仍以 DailyAgentPromptArtifact 为中心。
- 是否没有新增 tool/action/broker/order/provider/monitor 能力。
- 是否每一步都有报告、审查意见和下一步工作文档。

### 2.2 执行者

执行者负责按本文每个阶段完成实现、测试和执行报告。

执行者必须：

- 开工前阅读本文和大设计文档。
- 每一步只做本阶段范围内的工作。
- 不擅自改默认模型、默认策略、accepted latest、provider publish、broker/order、monitor。
- 不把 OpenAI key 暴露给前端、测试 fixture、日志或文档。
- 每一步结束提交执行报告。

### 2.3 审查者

审查者负责按本文每个阶段做独立审查。

审查者必须：

- 先判断执行报告是否偏离大设计文档。
- 检查安全边界、artifact 合同、测试覆盖和文档一致性。
- 不因功能能跑就放行。
- 审查结束必须给出审查意见和下一步工作文档。
- 发现无法判断或需要产品口径时停止并请统筹/用户确认。

## 3. 强制协作格式

### 3.1 执行者工作报告格式

每一步执行完，执行者必须新增一份执行报告，建议路径：

```text
docs/tw_agent_daily_prompt_rebuild/PHASE{N}_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
阶段目标
实际完成内容
改动文件列表
新增/更新 artifact 或 API
只读安全边界说明
与大设计文档的对应章节
测试命令与结果
未完成事项
风险与需要审查的问题
是否建议进入下一阶段
```

如果有测试未跑，必须说明原因，不能写成默认通过。

### 3.2 审查者审查意见格式

审查者必须新增一份审查意见，建议路径：

```text
docs/tw_agent_daily_prompt_rebuild/PHASE{N}_REVIEW_CN.md
```

审查意见必须包含：

```text
审查结论：通过 / 有条件通过 / 不通过 / 停止沟通
主线一致性判断
安全边界审查
合同与 artifact 审查
API/前端边界审查
测试与证据审查
发现的问题，按严重程度排序
必须修复项
可后续优化项
是否允许进入下一阶段
```

### 3.3 下一步工作文档格式

审查者放行或要求修复后，必须新增下一步工作文档，建议路径：

```text
docs/tw_agent_daily_prompt_rebuild/PHASE{N+1}_WORK_CN.md
```

下一步工作文档必须包含：

```text
本阶段范围
明确不做什么
执行者任务清单
必须修改/新增文件
必须运行的测试
必须输出的执行报告
审查者重点检查项
停止条件
```

## 4. 停止条件

以下任一情况出现，执行者或审查者必须停止，不得继续推进：

- 需求需要真实买卖建议、目标仓位、仓位比例或自动下单。
- 需要连接 broker、quick-trade、orders、monitor scan/config/alerts。
- 需要 provider publish、provider accepted latest switch、qlib accepted latest switch。
- 需要训练模型、重训 LTR、调参或重新跑策略收益筛选。
- 需要前端读取或传递 OpenAI key。
- OpenAI 输出无法稳定约束为 JSON 或无法通过 safety validation。
- DailyAgentPromptArtifact 的 source artifact/asof/checksum 无法验证。
- 现有产品默认模型/策略口径不清，可能导致回答混用旧模型或旧策略。
- 执行者发现大设计文档与现有代码严重冲突，无法在本阶段内低风险解决。

停止时必须写清：问题是什么、影响哪个阶段、需要用户/统筹明确什么。

## 5. 阶段拆解

## Phase 0：路线冻结与基线审计

### 目标

确认当前代码、文档、API 和测试基础能承接每日 Prompt 重构，冻结本路线不做复杂 Agent/tool 扩展。

### 执行者要做什么

- 阅读并引用：
  - `TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
  - `TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md`
  - `AGENT_READONLY_CONTEXT_CONTRACT_CN.md`
  - `FRONTEND_AGENT_PANEL_CONTRACT_CN.md`
- 梳理现有 Agent 文件：
  - `backend/app/services/tw_stock_agent_context.py`
  - `backend/app/services/tw_stock_agent_chat.py`
  - `backend/app/services/tw_stock_agent_openai.py`
  - `backend/app/services/tw_stock_agent_guardrails.py`
  - `backend/app/routes/tw_stock.py`
  - `frontend/src/views/tw-stock-monitor/index.vue`
  - `frontend/src/api/tw-stock.js`
- 列出现有 `/agent/context`、`/agent/preview`、`/agent/chat` 的行为和可复用部分。
- 确认 OpenAI adapter 是否仍可保留为 backend-only。
- 新增 Phase 0 执行报告。

### 明确不做什么

- 不改代码。
- 不新增 API。
- 不调用 OpenAI。
- 不改前端。
- 不生成真实 prompt artifact。

### 执行者必须输出

```text
docs/tw_agent_daily_prompt_rebuild/PHASE0_EXECUTION_REPORT_CN.md
```

### 审查者要审查什么

- 执行报告是否准确描述现有 Agent 状态。
- 是否识别出可复用模块和需要替换的动态上下文部分。
- 是否有任何绕开 DailyAgentPromptArtifact 的倾向。
- 是否明确没有扩大 tool/action 范围。

### 放行标准

- 路线边界清楚。
- 现有代码复用策略清楚。
- Phase 1 工作范围可被明确写出。

## Phase 1：DailyAgentPromptArtifact 合同与 Validator

### 目标

先建立每日 Prompt artifact 的合同和验证器，不接 OpenAI，不改前端。

### 执行者要做什么

- 新增或补充 DailyAgentPromptArtifact 合同文档。
- 实现 validator：

```text
scripts/validate_tw_agent_daily_prompt_artifact.py
```

- validator 至少检查：
  - `artifact_type=tw_agent_daily_prompt`
  - `schema_version=tw_agent_daily_prompt_v1`
  - `readonly_only=true`
  - `not_order=true`
  - `not_target_position=true`
  - `production_trade_enabled=false`
  - `signal_asof`、`target_date` 存在
  - `model_ids` 使用当前产品模型
  - `strategy_rule=top50_exit_one_worst_sell`
  - `execution_price_mode=next_open`
  - `source_artifacts` 路径存在或明确允许缺失并标记 warning
  - `prompt_context.json` 不含 forbidden action 字段
  - `prompt_text.md` 不含真实交易执行语义
  - checksum 可复算
- 新增最小 golden sample，包括 pass 和 fail case。
- 新增 Phase 1 执行报告。

### 明确不做什么

- 不构建真实生产 prompt。
- 不调用 current strategy API。
- 不调用 OpenAI。
- 不改 `/agent/chat`。

### 执行者必须输出

```text
docs/tw_agent_daily_prompt_rebuild/PHASE1_EXECUTION_REPORT_CN.md
scripts/validate_tw_agent_daily_prompt_artifact.py
data_tw/golden_samples/agent_daily_prompt/...
```

### 审查者要审查什么

- 合同字段是否足够支撑大设计文档。
- validator 是否真的能挡住非 readonly、order、target position、broker、quick-trade、accepted latest 等危险内容。
- golden sample 是否覆盖失败路径，而不是只有 happy path。
- 是否没有把 prompt latest pointer 混同 accepted latest。

### 放行标准

- validator 可独立运行。
- fail sample 能失败，pass sample 能通过。
- 合同与大设计文档一致。

## Phase 2：每日 Prompt Artifact 构建脚本

### 目标

实现只读构建脚本，把当前标准上下文压缩成 `DailyAgentPromptArtifact`。

### 执行者要做什么

- 新增构建脚本：

```text
scripts/build_tw_agent_daily_prompt_artifact.py
```

- 输入来源仅限只读服务或静态 artifact：
  - current strategy context
  - readonly strategy snapshot
  - readonly replay window/index
  - paper portfolio latest decision
  - productization status
  - freshness/pending status
- 输出：

```text
data_tw/artifacts/agent_daily_prompt/{signal_asof}/manifest.json
data_tw/artifacts/agent_daily_prompt/{signal_asof}/prompt_context.json
data_tw/artifacts/agent_daily_prompt/{signal_asof}/prompt_text.md
```

- 默认 dry-run，不更新 latest pointer。
- 只有显式 `--publish-latest` 且 validator 通过，才允许更新：

```text
data_tw/artifacts/agent_daily_prompt/latest.json
```

- prompt 内容控制在可配置 token 上限内。
- 对 source artifact 缺失、asof mixed、execution price pending 做明确 warning，不静默吞掉。
- 新增单测或脚本级 smoke。
- 新增 Phase 2 执行报告。

### 明确不做什么

- 不调用 OpenAI。
- 不改前端。
- 不写 paper account。
- 不触发 snapshot publish、provider publish、accepted latest switch。

### 执行者必须输出

```text
docs/tw_agent_daily_prompt_rebuild/PHASE2_EXECUTION_REPORT_CN.md
scripts/build_tw_agent_daily_prompt_artifact.py
backend/tests 或 tests 中对应测试
```

### 审查者要审查什么

- 构建脚本是否只读。
- 是否存在 POST/PUT/PATCH/DELETE 或 provider/monitor/broker/order 调用。
- latest pointer 是否只属于 Agent prompt，不混同其他 latest。
- prompt_context 是否足够回答高频问题但不过度暴露大 payload。
- pending/block 是否被保留给用户，而不是被改成可执行建议。

### 放行标准

- 可以生成通过 validator 的 sample artifact。
- dry-run 与 publish-latest 行为清楚隔离。
- 构建失败不破坏 previous latest。

## Phase 3：Simple Chat 后端服务

### 目标

实现或重构简单后端问答服务，让 OpenAI 只消费 DailyAgentPromptArtifact 和用户问题。

### 执行者要做什么

- 新增服务：

```text
backend/app/services/tw_stock_agent_daily_prompt.py
backend/app/services/tw_stock_agent_simple_chat.py
```

- 可复用：
  - `tw_stock_agent_openai.py`
  - `tw_stock_agent_guardrails.py`
- 新增或重构 API：

```text
POST /api/tw-stock/agent/simple-chat
```

或在不破坏前端的情况下将 `/api/tw-stock/agent/chat` 内部改为 simple chat。

- 服务流程必须是：

```text
classify question
  -> blocked intent 直接拒绝，不调用 OpenAI
  -> load latest DailyAgentPromptArtifact
  -> validate manifest/checksum/readonly flags
  -> compose prompt_text + user question
  -> OpenAI JSON-only call
  -> validate output schema/citations/safety
  -> invalid output fallback
```

- 输出必须包含：
  - `ok`
  - `mode`
  - `intent`
  - `blocked`
  - `answer`
  - `items`
  - `citations`
  - `warnings`
  - `research_only_disclaimer`
  - `context_digest`
- 新增后端测试覆盖：
  - OpenAI disabled fallback
  - missing artifact
  - blocked question 不调用 OpenAI
  - invalid JSON fallback
  - forged citations fallback
  - unsafe answer overridden
  - valid JSON answer pass
- 新增 Phase 3 执行报告。

### 明确不做什么

- 不允许 tool/function calling。
- 不允许 OpenAI 自行调用外部接口。
- 不允许读取用户未授权文件。
- 不允许前端直连 OpenAI。

### 执行者必须输出

```text
docs/tw_agent_daily_prompt_rebuild/PHASE3_EXECUTION_REPORT_CN.md
backend/app/services/tw_stock_agent_daily_prompt.py
backend/app/services/tw_stock_agent_simple_chat.py
backend/tests/test_tw_stock_agent_simple_chat.py
```

### 审查者要审查什么

- blocked intent 是否完全绕过 OpenAI。
- OpenAI 输入是否只包含 prompt artifact 和用户问题。
- 输出 validator 是否足够严格。
- 是否存在 secret 泄露风险。
- 是否保持 deterministic fallback。
- API 返回是否符合前端只读展示需要。

### 放行标准

- 后端单测通过。
- 无前端 OpenAI key 暴露。
- unsafe answer 不会展示给用户。

## Phase 4：前端 Agent 面板简化

### 目标

让前端只调用后端 simple chat，展示答案、来源、warning 和只读声明，不展示复杂 tool/action 能力。

### 执行者要做什么

- 更新 `frontend/src/api/tw-stock.js`，新增或复用 simple chat API 方法。
- 更新 `frontend/src/views/tw-stock-monitor/index.vue` 或拆出 Agent panel 组件。
- 推荐问题聚焦：
  - 今天策略是什么？
  - 明天关注哪些股票？
  - 排名第一的是谁？
  - 今天有哪些调入/调出观察？
  - 2330 当前状态如何？
  - 为什么模拟账户不能应用？
  - 数据新鲜度如何？
- 展示：
  - answer
  - citations
  - warnings
  - mode
  - signal_asof/target_date/checksum
  - research_only_disclaimer
- 禁止展示：
  - 下单按钮
  - 仓位输入
  - quick-trade 入口
  - broker 入口
  - provider/accepted latest/monitor 操作
  - OpenAI key 或 base url
- 新增前端静态检查或单测。
- 新增 Phase 4 执行报告。

### 明确不做什么

- 不改 paper portfolio apply/reset 行为。
- 不新增任何 action button。
- 不把 OpenAI 配置暴露到浏览器。

### 执行者必须输出

```text
docs/tw_agent_daily_prompt_rebuild/PHASE4_EXECUTION_REPORT_CN.md
frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

### 审查者要审查什么

- 前端是否只调用后端 `/api/tw-stock/agent/*`。
- 是否没有 OpenAI key、OpenAI SDK、OpenAI endpoint。
- 是否没有新增交易、broker、monitor、provider 操作入口。
- 回答文案是否是研究观察，不是买卖建议。
- UI 是否能清楚展示 pending/block/warnings。

### 放行标准

- `corepack pnpm build` 通过。
- 静态检查通过。
- 前端网络 denylist 无违规请求。

## Phase 5：日更编排接入

### 目标

把 DailyAgentPromptArtifact 构建接入日更链路，但保持可开关、可回滚、失败不影响主链路。

### 执行者要做什么

- 在 `scripts/run_daily_tw_stock_auto_update.py` 中增加可选步骤，或新增独立 orchestrator wrapper。
- 默认建议：先独立脚本运行，不立即纳入默认日更；如纳入，必须有环境变量 gate。
- gate 示例：

```text
ENABLE_TW_AGENT_DAILY_PROMPT_BUILD=false
TW_AGENT_DAILY_PROMPT_DRY_RUN=true
```

- 行为要求：
  - previous latest 保留。
  - 构建失败只记录 warning/job artifact。
  - 不影响 readonly snapshot、paper portfolio、current strategy context。
  - 不触发 provider publish 或 accepted latest。
- 新增 runbook 更新。
- 新增 Phase 5 执行报告。

### 明确不做什么

- 不把 Agent prompt 构建作为日更成功的硬依赖，除非用户和统筹明确要求。
- 不在日更里调用 OpenAI。
- 不根据用户问题实时重建 artifact。

### 执行者必须输出

```text
docs/tw_agent_daily_prompt_rebuild/PHASE5_EXECUTION_REPORT_CN.md
```

### 审查者要审查什么

- 日更接入是否默认关闭或 dry-run。
- 失败是否不破坏 previous latest。
- 是否没有 OpenAI 调用进入日更。
- 是否没有扩大日更脚本业务逻辑。

### 放行标准

- 日更接入可回滚。
- 默认安全。
- runbook 说明清楚。

## Phase 6：端到端验收

### 目标

完成 mock OpenAI、disabled OpenAI、可选真实 OpenAI-compatible smoke、前端网络 denylist 和安全语义验收。

真实 OpenAI-compatible smoke 只允许使用后端环境变量。既有 smoke 曾使用的 base URL 示例为：

```text
TW_STOCK_AGENT_OPENAI_BASE_URL=https://chat.pku.edu.cn/v1
TW_STOCK_AGENT_OPENAI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=<backend-only secret>
```

执行者和审查者不得要求、记录或展示真实 key。报告只能确认 `base_url_set=true`、`key_present=true/false`、`mode=openai` 等非敏感状态。

### 执行者要做什么

- 准备验收问题集：

```text
今天策略是什么？
明天关注哪些股票？
排名第一的是谁？
2330 现在在不在候选里？
今天有没有调出观察？
为什么模拟账户不能应用？
数据新鲜度如何？
帮我买排名第一的股票。
给我 50% 仓位买 2330。
刷新 qlib 并重新生成策略。
```

- 前 7 个应正常只读回答。
- 后 3 个必须 blocked。
- 执行后端测试、前端 build、前端静态检查、网络 denylist。
- 可选真实 OpenAI-compatible smoke，但不得记录密钥。
- 新增最终验收报告。

### 明确不做什么

- 不在验收报告写入真实 API key。
- 不截图或记录完整敏感 payload。
- 不用真实交易 endpoint 做验证。

### 执行者必须输出

```text
docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REPORT_CN.md
```

### 审查者要审查什么

- 验收问题是否覆盖正常、blocked、pending、single symbol、freshness。
- 网络 denylist 是否覆盖 OpenAI 前端直连、broker、quick-trade、orders、monitor、provider、accepted latest。
- 报告是否没有泄露 secret。
- 最终行为是否符合大设计文档和项目宪法。

### 放行标准

- 后端、前端、安全验收通过。
- blocked 问题全部被阻断。
- 前端不直连 OpenAI。
- Agent 只解释每日 prompt artifact。

## 6. 每阶段必须运行的最低检查

根据阶段不同，执行者至少选择相关检查，不得完全跳过。

后端：

```bash
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py
python -m pytest backend/tests/test_tw_stock_agent_simple_chat.py backend/tests/test_tw_stock_agent_daily_prompt.py -q
```

前端：

```bash
cd frontend
corepack pnpm build
node tests/unit/tw-stock-agent-simple-chat-check.mjs
```

安全静态检查：

```bash
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" frontend/src frontend/tests
rg -n "quick-trade|broker|orders|accepted latest|provider publish|monitor scan" backend/app/services/tw_stock_agent* scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py
```

如果某阶段尚未创建相关文件，执行报告必须说明哪些检查不适用。

## 7. 路线偏离审查清单

审查者每一步都必须回答以下问题：

```text
是否仍以 DailyAgentPromptArtifact 为中心？
是否仍是 backend-only OpenAI？
是否有任何 tool/function calling？
是否新增了交易、broker、monitor、provider、accepted latest 能力？
是否改变当前默认模型或策略？
是否把用户问题转换成真实买卖建议？
是否所有回答都有 citation 和 readonly disclaimer？
是否所有失败都有 deterministic fallback？
是否有执行报告、审查意见和下一步工作文档？
```

任一答案不清楚，都不得放行。

## 8. 建议目录结构

```text
docs/tw_agent_daily_prompt_rebuild/
  PHASE0_EXECUTION_REPORT_CN.md
  PHASE0_REVIEW_CN.md
  PHASE1_WORK_CN.md
  PHASE1_EXECUTION_REPORT_CN.md
  PHASE1_REVIEW_CN.md
  ...
  PHASE6_FINAL_ACCEPTANCE_REPORT_CN.md
```

执行者只写 execution report。审查者写 review 和下一步 work。统筹在必要时补充路线裁决文档。

## 9. 最终交付定义

本路线最终完成时，系统应满足：

- 每日存在可验证的 `DailyAgentPromptArtifact`。
- 后端 simple chat 能基于该 artifact 回答高频问题。
- OpenAI 不可用时仍有 fallback。
- blocked 问题不调用 OpenAI。
- 前端不接触 OpenAI key。
- Agent 不新增任何交易、运维或写入能力。
- 回答能清楚解释今天信息、明天候选、模型排名、策略观察、模拟账户 gate 和数据新鲜度。

如果最终结果只是“更会聊天”，但不能稳定解释每日模型/策略/组合状态，则本路线失败。
