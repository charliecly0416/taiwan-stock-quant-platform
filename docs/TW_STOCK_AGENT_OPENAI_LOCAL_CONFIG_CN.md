# 台股 Agent OpenAI 本地配置说明

日期：2026-06-04

## 目的

台股研究 Agent 的 OpenAI-compatible 调用只允许发生在后端进程内。前端不读取、不展示、不传递 `OPENAI_API_KEY`，浏览器也不应直连 OpenAI-compatible endpoint。

## 本地配置位置

推荐把真实配置放在本机 `backend/.env` 或后端进程环境变量中。`backend/.env` 是本地文件，应被 `.gitignore` 忽略，不能提交到仓库。

## 推荐模板

```text
ENABLE_TW_STOCK_AGENT_OPENAI=true
OPENAI_BASE_URL=<openai-compatible-base-url>
TW_STOCK_AGENT_OPENAI_BASE_URL=<openai-compatible-base-url>
OPENAI_API_KEY=<backend-only secret>
TW_STOCK_AGENT_OPENAI_MODEL=gpt-4.1-mini
TW_STOCK_AGENT_OPENAI_TIMEOUT_SECONDS=20
```

说明：

- `OPENAI_API_KEY` 只能放在后端环境变量或 `backend/.env`。
- `TW_STOCK_AGENT_OPENAI_BASE_URL` 优先用于台股 Agent；未设置时才回退到 `OPENAI_BASE_URL`。
- 文档、测试、截图、日志只能写 `<backend-only secret>`，不能写真实 key。

## 后端 smoke

```bash
set -a
. backend/.env
set +a
PYTHONPATH=backend python backend/scripts/smoke_tw_stock_agent_phase6b.py
```

## 临时启动 OpenAI 后端

```bash
set -a
. backend/.env
set +a
PYTHON_API_HOST=127.0.0.1 \
PYTHON_API_PORT=5094 \
ENABLE_PENDING_ORDER_WORKER=false \
ENABLE_PORTFOLIO_MONITOR=false \
ENABLE_TW_STOCK_MONITOR_WORKER=false \
DISABLE_RESTORE_RUNNING_STRATEGIES=true \
python backend/run.py
```

## 前端网络级验证

```bash
cd frontend
TW_STOCK_AGENT_BASE_URL=http://127.0.0.1:8000 \
TW_STOCK_AGENT_BACKEND_URL=http://127.0.0.1:5094 \
TW_STOCK_AGENT_SCREENSHOT_DIR=/tmp/tw_stock_agent_openai_skills \
node tests/e2e/tw-stock-agent-openai-skills-network.mjs
```

预期：

- `/api/tw-stock/agent/chat` 返回 `mode=openai`。
- 响应包含 `invoked_skills`。
- 页面展示 `skills`、`Safety Boundary Review`、`Research Context Analyst`。
- 浏览器没有直接请求 OpenAI-compatible endpoint。
- 没有危险写请求。
