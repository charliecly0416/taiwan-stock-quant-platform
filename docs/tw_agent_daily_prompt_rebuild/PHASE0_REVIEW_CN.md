# Phase 0 审查意见：台股 Agent 每日 Prompt + OpenAI 重构

生成日期：2026-06-19

## 1. 审查结论

审查结论：有条件通过。

允许进入 Phase 1，但 Phase 1 只能做 `DailyAgentPromptArtifact` 合同与 validator，不得提前实现 chat API、构建真实生产 prompt、调用 OpenAI、修改前端或触发任何 provider/accepted latest/monitor/broker/order/quick-trade 路径。

本次审查基于以下证据：

- `docs/tw_agent_daily_prompt_rebuild/PHASE0_EXECUTION_REPORT_CN.md`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md`
- `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_EXECUTION_AND_REVIEW_PLAN_CN.md`
- `docs/tw_modular_contracts/AGENT_READONLY_CONTEXT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/FRONTEND_AGENT_PANEL_CONTRACT_CN.md`
- 现有 Agent/前端相关代码只读核对。

## 2. 主线一致性判断

Phase 0 执行报告正确抓住了本路线主线：

```text
每日只读上下文
  -> DailyAgentPromptArtifact
  -> 简单后端 OpenAI 接口
  -> 结构化回答
  -> 前端只读展示
```

报告没有把路线扩展为复杂 Agent、多工具调用、外部搜索、交易执行、provider 运维或模型训练路线。报告明确指出当前实现仍是动态 `cross-analysis/latest + qlib accepted latest` preview，不是目标态 DailyAgentPromptArtifact，因此 Phase 1/2 必须先补 artifact 合同、validator 和构建脚本，不能直接改 `/agent/chat`。

主线一致性通过。

## 3. 安全边界审查

本次审查未发现 Phase 0 新增业务代码、API、前端逻辑、脚本或配置，也未发现执行报告要求调用 OpenAI、触发真实数据抓取、provider publish、accepted latest 切换、monitor 写入、broker/order/quick-trade。

现有 Agent 路由核对结果：

- `/api/tw-stock/agent/context`：GET，只读构建上下文。
- `/api/tw-stock/agent/preview`：POST，用于 deterministic preview，不调用 OpenAI。
- `/api/tw-stock/agent/chat`：POST，先 preview 与 guardrails，blocked 时不调用 OpenAI；OpenAI disabled 或异常时 fallback。

现有 Agent 代码中可复用的安全机制包括：

- backend-only OpenAI adapter，密钥只从后端环境变量读取。
- JSON-only 输出约束。
- citation allowlist 校验。
- unsafe answer override。
- blocked intent 不调用 OpenAI。
- research-only disclaimer。

需要注意：静态检索中出现 `monitor`、`sim/orders`、`broker` 等词，主要来自页面已有非 Agent 模块、模拟账户或只读声明，不属于 Phase 0 Agent 新增能力。后续 Phase 4 做前端网络 denylist 时，应把 Agent 面板请求和整页既有功能分开审查，避免误判，也不能因此放松 Agent 面板的边界。

安全边界审查通过。

## 4. 现有 Agent 梳理质量审查

执行报告对以下文件和行为的梳理基本准确：

- `backend/app/services/tw_stock_agent_context.py`
- `backend/app/services/tw_stock_agent_chat.py`
- `backend/app/services/tw_stock_agent_openai.py`
- `backend/app/services/tw_stock_agent_guardrails.py`
- `backend/app/routes/tw_stock.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/api/tw-stock.js`

报告准确指出当前上下文来源偏向 `TWStockCrossAnalysisService.latest(...)`、symbol detail、top30/top50、trend/cross-analysis，而不是 current strategy context、readonly strategy snapshot、readonly replay window、paper portfolio decision、productization status。

一个需要后续修正的细节：现有 guardrails 把“模拟盘”归入 `paper_live_trading` blocked 语义。目标路线需要支持 `paper_apply_status`、`execution_price_pending` 等只读模拟账户状态查询，因此 Phase 3 不能简单继承该分类结果，必须区分“查询模拟账户 gate/状态”和“要求实盘或自动交易”。

现有 Agent 梳理质量通过。

## 5. 可复用模块判断

执行报告识别的可复用模块判断成立：

- `tw_stock_agent_openai.py` 可以保留 backend-only adapter、timeout、JSON-only、disabled fallback 和 mock adapter。
- `tw_stock_agent_guardrails.py` 可以保留 blocked intent 优先、disclaimer 和危险语义分类框架。
- `tw_stock_agent_chat.py` 中 JSON/schema/citation/safety validation、fallback/refusal 思路可以迁移到 simple chat。
- 前端 Agent 面板的 answer、warnings、citations、mode、blocked、disclaimer 展示结构可以复用。

需要保留的审查条件：

- `skill_registry` 当前更像上下文标签/能力描述，但命名容易让后续执行者误解为复杂 tool/skill Agent。Phase 3 必须决定移除、降级命名或证明其不会触发工具调用。
- OpenAI adapter 使用 `/chat/completions` 不是 Phase 0 阻塞项；只要保持 backend-only、JSON-only、无 tool/function calling，Phase 3 可继续复用。

## 6. 需要重构部分判断

执行报告对重构点判断准确：

- 当前 `TWStockAgentContextService.preview(...) -> controlled_context` 动态链路应被 DailyAgentPromptArtifact latest + manifest/checksum/readonly validation 替代。
- 当前 citations 应从 `qlib:accepted_latest:*`、`cross-analysis:latest:*` 扩展或迁移到 `agent_prompt:{signal_asof}:{checksum}`、`readonly_snapshot:{asof}`、`paper_decision:{decision_id}` 等可追溯来源。
- 当前 items 缺少 strategy top candidates、exit candidates、paper apply gate、execution price status、replay summary。
- 当前前端问题集仍偏 top30/cross-analysis，Phase 4 必须改到每日策略、明日候选、排名第一、调入/调出观察、模拟账户 gate、数据新鲜度。

## 7. 测试与证据审查

Phase 0 未运行测试可以接受，因为本阶段按计划只做路线冻结与基线审计，不改代码、不启动服务、不调用 OpenAI。

但 Phase 1 起不得继续只写报告。Phase 1 至少需要提供：

- validator 可运行证据。
- pass golden sample 通过证据。
- fail golden sample 失败证据。
- Python 语法检查或 pytest 证据。
- 静态安全检索证据。

如果 Phase 1 有任何测试未跑，执行报告必须说明原因和风险，不得写成默认通过。

## 8. 发现的问题

### Medium

1. 现有 guardrails 对“模拟盘”语义过宽阻断。
   影响：后续 `paper_apply_status`、`execution_price_pending` 这类只读模拟账户状态问题可能被误判为交易请求。
   处理：Phase 3 前必须明确分类规则，允许只读查询，继续阻断实盘、自动交易、仓位、下单。

2. `skill_registry` 命名和前端“调用能力”展示可能造成复杂 Agent/tool 扩展误解。
   影响：与“不做复杂 Agent、多工具调用”的路线表达不完全一致。
   处理：Phase 3/4 要么移除，要么改成非工具语义的 context/source 标签，并证明不会触发外部工具或 action。

### Low

1. Phase 0 报告未附具体静态检索命令输出。
   影响：审查者可通过只读核对补足，不阻塞 Phase 1。
   处理：Phase 1 起执行报告必须列命令与结果。

2. 前端整页存在既有 monitor 和 simulation orders API 方法。
   影响：不是 Agent Phase 0 新增风险，但后续网络 denylist 容易混淆。
   处理：Phase 4/6 审查应区分 Agent 面板路径与整页既有功能，同时确认 Agent 面板不新增危险入口。

## 9. 必须修复项

Phase 0 无需返工。

进入 Phase 1 前必须遵守以下限制：

- Phase 1 不得修改 `/agent/chat`。
- Phase 1 不得改前端。
- Phase 1 不得构建真实生产 prompt。
- Phase 1 不得调用 OpenAI。
- Phase 1 不得调用 current strategy API 或后端服务做真实数据读取。
- Phase 1 不得触发 provider publish、accepted latest、monitor、broker/order/quick-trade。

## 10. 可后续优化项

- 将 `DailyAgentPromptArtifact` 合同单独成文，避免只散落在设计文档里。
- 为 forbidden action audit 建立共享词表，减少 validator、chat safety、前端静态检查各写一套。
- 在 Phase 3 把“建议关注/建议回避”逐步替换为“观察/人工复盘/数据复核/拟调入观察/拟调出观察”。
- Phase 4 去掉或改名 UI 中的“调用能力”，避免用户以为 Agent 能执行工具。

## 11. 是否允许进入 Phase 1

允许进入 Phase 1。

放行范围仅限：

```text
DailyAgentPromptArtifact 合同与 validator
```

不得提前进入 Phase 2/3/4 的构建脚本、OpenAI chat、前端接入或日更编排。
