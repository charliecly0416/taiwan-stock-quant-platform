# 台股 Agent Skills 前端产品侧调用实现报告

日期：2026-06-04

## 目标

把此前创建的 Codex 本地 skills 落到 QuantDinger 台股前端 Agent 的产品链路中，使用户在 `/tw-stock-monitor` 面板提问时，后端 Agent 能受控选择并注入相关 skill 上下文，前端能展示本次实际触发的 skills。

## 实现结果

1. 新增后端受控 skill registry：`backend/app/services/tw_stock_agent_skills.py`。
2. `/api/tw-stock/agent/chat` 响应新增 `invoked_skills`，包含 skill name、title、mode、status、reason 和 evidence。
3. OpenAI 调用前的 `controlled_context` 新增 `selected_skills`、`skill_context`、`skill_invocation_policy`，真实模型只能基于后端选择的 skill 上下文回答。
4. 前端 Agent 面板新增 `skills` 展示区，显示本次响应触发的 skill 名称和状态。
5. Playwright fixture 已覆盖 skill 展示、鉴权 fixture、只读 Agent chat 全场景。

## 当前可调用 Skills

- `tw-stock-safety-boundary-review`：所有问题先应用，作为 guardrail policy；交易/仓位/自动交易/qlib 运维类问题仍在 OpenAI 前阻断。
- `tw-stock-data-freshness-diagnosis`：数据新鲜度、Yahoo、FinMind、asof、自动重试、数据口径类问题触发。
- `tw-stock-research-context-analyst`：TopN、重点观察、单股指标、模型趋势一致/分歧、人工复盘类研究问题触发。
- `tw-stock-readonly-e2e-acceptance`：前端 chat 只返回 `not_invoked_from_web_agent` handoff，不从网页触发长耗时 Playwright 或验收执行。

## 安全边界

- 前端不直连 OpenAI，不持有 API key。
- 后端不执行 `~/.agents/skills/*/SKILL.md` 中的任意脚本，只读取描述并构造产品侧只读上下文。
- 被 guardrails 阻断的问题不调用 OpenAI，也不执行可变更状态的能力。
- 保持 research-only：不下单、不连交易接口、不保存目标仓位、不切换 accepted latest、不触发 provider refresh/publish。

## 验证

- `python -m pytest backend/tests/test_tw_stock_agent_chat.py backend/tests/test_tw_stock_agent_context.py`：20 passed。
- `python -m py_compile backend/app/services/tw_stock_agent_skills.py backend/app/services/tw_stock_agent_chat.py`：通过。
- `node frontend/tests/unit/tw-stock-agent-panel-check.mjs`：通过。
- `node frontend/tests/unit/tw-stock-agent-panel-e2e.mjs`：通过；10 个 Agent chat 场景，仅捕获 `POST /api/tw-stock/agent/chat`，未发现 OpenAI 直连或危险请求。

## 结论

现在这些 skills 不再只是 Codex 本地工作流说明，而是已经被台股产品 Agent 以“后端受控、只读上下文注入、前端可见审计”的方式调用。
