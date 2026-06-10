# 台股 Agent Skills / OpenAI 测试稳定性优化报告

日期：2026-06-04

## 目标

按 `docs/TW_STOCK_AGENT_SKILLS_OPENAI_TEST_OPT_EXECUTION_CN.md` 执行非阻塞优化：将真实 OpenAI-compatible 链路的网络级 Playwright 测试入库，稳定 UI skills 标签断言，并补充不含密钥的本地 OpenAI 配置说明。

## 新增/修改文件

新增：

- `frontend/tests/e2e/tw-stock-agent-openai-skills-network.mjs`
- `docs/TW_STOCK_AGENT_OPENAI_LOCAL_CONFIG_CN.md`
- `docs/TW_STOCK_AGENT_SKILLS_OPENAI_TEST_OPT_REPORT_CN.md`

沿用/修改：

- `frontend/tests/unit/tw-stock-agent-panel-e2e.mjs`：已稳定 auth fixture 与 skills 标签断言。
- `frontend/tests/unit/tw-stock-agent-panel-check.mjs`：已覆盖 `agentSkills` / `invoked_skills` 静态检查。

## 网络级 Playwright 测试结果

命令：

```bash
TW_STOCK_AGENT_BASE_URL=http://127.0.0.1:8000 \
TW_STOCK_AGENT_BACKEND_URL=http://127.0.0.1:5094 \
TW_STOCK_AGENT_SCREENSHOT_DIR=/tmp/tw_stock_agent_openai_skills \
node frontend/tests/e2e/tw-stock-agent-openai-skills-network.mjs
```

结果：通过。

关键摘要：

```json
{
  "forwardedPaths": [
    "GET /api/tw-stock/agent/context",
    "POST /api/tw-stock/agent/chat"
  ],
  "agentChatStatus": 200,
  "mode": "openai",
  "invokedSkills": [
    "tw-stock-safety-boundary-review",
    "tw-stock-research-context-analyst"
  ],
  "directOpenAIRequests": 0,
  "dangerousRequests": 0,
  "consoleErrors": 0,
  "pageErrors": 0
}
```

说明：浏览器只请求本地前端；脚本只将 `/api/tw-stock/agent/context` 与 `/api/tw-stock/agent/chat` 转发到后端 `127.0.0.1:5094`。浏览器没有直接请求 OpenAI-compatible endpoint。

## UI Skills 标签断言

命令：

```bash
node frontend/tests/unit/tw-stock-agent-panel-check.mjs
node frontend/tests/unit/tw-stock-agent-panel-e2e.mjs
```

结果：通过。

E2E 摘要：

```json
{
  "agentPhaseRequests": 10,
  "agentContextCount": 2,
  "agentChatCount": 10,
  "uniqueAgentPhasePaths": ["POST /api/tw-stock/agent/chat"],
  "screenshotDir": "/tmp/quantdinger_tw_agent_e2e"
}
```

本轮确认页面可稳定展示 `skills`、`Safety Boundary Review` 与 `Research Context Analyst`。

## 后端真实 OpenAI Smoke

命令读取本地 `backend/.env`，未打印真实 key：

```bash
set -a
. backend/.env
set +a
PYTHONPATH=backend python backend/scripts/smoke_tw_stock_agent_phase6b.py
```

结果：通过。

摘要：

- `smoke_type=openai_compatible`
- `base_url_set=true`
- 非阻断场景 `top30`、`focus_watch`、`single_symbol`、`freshness` 均为 `mode=openai`。
- 阻断场景 `blocked_order`、`blocked_position` 均为 `mode=disabled`、`blocked=true`、`orders_enabled=false`。

## 其他验证

- `PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_agent_chat.py -q`：14 passed。
- `node --check frontend/tests/e2e/tw-stock-agent-openai-skills-network.mjs`：通过。
- `git diff --check`：通过。
- 临时后端 `127.0.0.1:5094` 已停止，端口无监听。

## 密钥泄露检查

执行：

```bash
git status --short --ignored backend/.env
git check-ignore -v backend/.env
rg -n "OPENAI_API_KEY=.*[A-Za-z0-9_]{8}|REAL_SECRET_FRAGMENT" docs backend/app frontend/src backend/tests frontend/tests .env.example
```

结果：

- `backend/.env` 显示为 ignored：`!! backend/.env`。
- `git check-ignore -v backend/.env` 命中 `backend/.gitignore:37:.env`。
- 敏感扫描未发现真实 key；仅命中：
  - 既有文档中的 `<backend-only>` 占位符。
  - 本执行文档中的扫描命令文本本身。

## 安全结论

- 未提交 `backend/.env`。
- 未将真实 `OPENAI_API_KEY` 写入代码、测试、文档、截图或日志。
- 前端不读取、不传递、不展示 key。
- 浏览器没有直连 OpenAI-compatible endpoint。
- 未触发 broker、quick-trade、order、target position。
- 未触发 monitor config 保存、monitor scan、alerts 写入。
- 未触发 qlib provider refresh、publish、accepted latest 切换。

## 是否建议收尾

建议收尾。当前剩余工作主要是提交本轮新增网络级 E2E、OpenAI 本地配置文档与报告，并保持 `backend/.env` ignored。
