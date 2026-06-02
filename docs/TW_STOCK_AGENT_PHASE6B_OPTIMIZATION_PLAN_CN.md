---
created_at: 2026-06-02
status: phase_plan
scope: quantdinger_tw_stock_agent_phase6b_post_acceptance_optimization
role_target: reviewer_executor_loop
reviewer: codex_reviewer
previous_acceptance: docs/TW_STOCK_AGENT_PHASE6_ACCEPTANCE_CN.md
next_execution_doc: docs/TW_STOCK_AGENT_PHASE6B_STEP1_EXECUTION_CN.md
backend_project: /path/to/taiwan-stock-quant-platform
frontend_project: /path/to/taiwan-stock-quant-platform-Vue
qlib_project: /home/chuliyang/qlib
---

# 台股研究 Agent Phase 6B 优化计划

Phase 6 已验收收尾。Phase 6B 是非阻塞优化，不改变 Agent 的核心定位：research-only、后端受控 OpenAI-compatible 调用、前端不接触 key、不触发 qlib ops、交易、订单、broker 或回测。

---

## 1. 优化目标

Phase 6B 只处理 Phase 6 验收中留下的合理优化：

```text
1. 优化 intent 分类：把“模型和趋势都支持”等自然问题稳定映射到 focus_watch。
2. 增加真实 OpenAI-compatible 后端 smoke 场景：单股指标、freshness、focus_watch。
3. 补充部署配置说明：默认关闭、key 只放后端、base_url 仅后端使用。
4. 清理前端既有 build warning 中低风险项。
```

不做：

```text
多轮聊天历史
工具调用 Agent
交易/下单/仓位
qlib refresh/publish/pipeline
模型重训/调参
前端直连 OpenAI-compatible 服务
```

---

## 2. 分步设计

建议拆成 2 步。

### Step 1：Agent 语义和真实 smoke 增强

目标：

- 优化 `TWStockAgentGuardrails.classify()`。
- 将“模型和趋势都支持”“趋势都支持”“共振”“模型趋势一致”等问题稳定映射到 `focus_watch`。
- 将“建议回避/人工复盘/分歧/数据异常”等问题继续映射到对应研究 intent。
- 增加后端测试覆盖。
- 增加真实 OpenAI-compatible smoke 脚本或测试入口，覆盖 top30、focus_watch、single_symbol_metrics、freshness、blocked。
- 不强制真实调用；无 key 时可 mock，但脚本要可重复执行。

审核断点：

```text
docs/TW_STOCK_AGENT_PHASE6B_STEP1_REPORT_CN.md
```

### Step 2：前端 warning 清理和部署说明

目标：

- 补充 Agent 部署说明文档。
- 说明 `ENABLE_TW_STOCK_AGENT_OPENAI=false` 默认关闭。
- 说明 `OPENAI_API_KEY`、`TW_STOCK_AGENT_OPENAI_BASE_URL`、`TW_STOCK_AGENT_OPENAI_MODEL` 只在后端配置。
- 尝试清理前端 build warning 中低风险项，例如 `/deep/` selector 和明显的 locale import warning。
- chunk size warning 如果需要大改，先只记录为非阻塞，不做大拆包。
- 保持 Agent 面板和 Playwright 回归通过。

审核断点：

```text
docs/TW_STOCK_AGENT_PHASE6B_STEP2_REPORT_CN.md
```

---

## 3. 收尾标准

Phase 6B 可收尾条件：

- `focus_watch` intent 优化通过测试。
- 后端真实 smoke 增强脚本存在，且无 key 时能安全跳过或 mock acceptance。
- 前端 Agent 静态检查、Playwright、build 仍通过。
- 部署说明明确 key/backend-only/default-disabled。
- 没有引入 qlib ops、交易、订单、broker、回测或前端 OpenAI key。

---

## 4. 预计轮次

预计 2 轮执行和审查：

```text
Step 1：Agent 语义和真实 smoke 增强
Step 2：前端 warning 清理和部署说明
```

如果 Step 2 的 build warning 涉及较大前端拆包，可将 chunk size 单独留作后续前端工程质量任务，不阻塞 Phase 6B 收尾。
