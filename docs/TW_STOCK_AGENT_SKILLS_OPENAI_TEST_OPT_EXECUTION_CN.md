# 台股 Agent Skills / OpenAI 测试稳定性优化执行文档

生成时间：2026-06-04

## 1. 本步目标

在当前 Agent skills + OpenAI-compatible 链路已经可用的基础上，做一轮非阻塞优化：

1. 将已验证通过的 Playwright 网络级全流程测试整理进项目。
2. 修复真实 UI Playwright 长等待后被路由守卫踢回登录页的问题，使测试能稳定断言页面上的 skills 标签。
3. 增加不含密钥的本地 OpenAI 配置说明，明确 `backend/.env` 只本地保存、不可提交。

本步不新增业务功能，不改交易能力，不把真实 API key 写入仓库。

## 2. 严格禁止

执行者不得：

- 提交 `backend/.env`、`.env`、`.env.*` 中的真实密钥。
- 在 docs、测试、截图、日志中写入真实 `OPENAI_API_KEY`。
- 让前端读取、传递或展示 `OPENAI_API_KEY`。
- 让浏览器直连 `chat.pku.edu.cn`、`api.openai.com` 或任何 OpenAI-compatible endpoint。
- 触发 broker、quick-trade、order、target position。
- 触发 monitor config 保存、monitor scan、alerts 写入。
- 触发 qlib provider refresh、publish、accepted latest 切换。

## 3. 优化一：Playwright 网络级测试入库

### 3.1 建议新增文件

```text
frontend/tests/e2e/tw-stock-agent-openai-skills-network.mjs
```

### 3.2 测试目标

该脚本验证：

- 浏览器打开真实前端 `/tw-stock-monitor`。
- 浏览器只请求后端 `/api/tw-stock/agent/context` 与 `/api/tw-stock/agent/chat`。
- Agent chat 后端返回 `mode=openai`。
- 响应包含 `invoked_skills`，至少包括：
  - `tw-stock-safety-boundary-review`
  - `tw-stock-research-context-analyst`
- 浏览器没有直接请求 OpenAI-compatible endpoint。
- 页面/响应中没有泄露 key。
- 没有危险写请求。

### 3.3 环境变量

脚本必须只通过环境变量读取配置：

```text
TW_STOCK_AGENT_BASE_URL=http://127.0.0.1:8000
TW_STOCK_AGENT_BACKEND_URL=http://127.0.0.1:5094
TW_STOCK_AGENT_SCREENSHOT_DIR=/tmp/tw_stock_agent_openai_skills
```

注意：脚本不读取 `OPENAI_API_KEY`，也不需要知道 key。真实 OpenAI key 只存在于后端进程环境。

### 3.4 后端要求

测试前需要有一个启用 OpenAI 的后端，例如：

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

报告中只能写 `<backend-only secret>`，不能写真实 key。

## 4. 优化二：真实 UI skills 标签断言稳定化

当前网络级 Playwright 已证明后端返回 `mode=openai` 与 `invoked_skills`，但真实 UI 长等待后可能被路由守卫踢回登录页。执行者需要做小范围修复，使 UI 断言稳定。

建议方向：

1. 使用真实登录接口获取 token，而不是手写 dummy token。
2. 或者在测试脚本中 mock `/api/auth/info` 与必要 auth/security/brand/policy 接口，确保路由守卫不会跳回登录页。
3. 等待条件不要只依赖长时间 `waitForFunction`，应先确认：
   - `.tw-stock-agent-panel` 存在。
   - `textarea` 存在。
   - 点击发送后 `/api/tw-stock/agent/chat` 已返回 200。
   - 再断言面板内出现 `skills`、`Safety Boundary Review`、`Research Context Analyst`。
4. 如果 UI 断言仍不稳定，至少将网络级 E2E 作为硬验收，UI skills 标签断言作为补充 smoke，并在报告中说明原因。

## 5. 优化三：本地 OpenAI 配置说明

### 5.1 建议新增文档

```text
docs/TW_STOCK_AGENT_OPENAI_LOCAL_CONFIG_CN.md
```

### 5.2 文档必须说明

- `OPENAI_API_KEY` 只放在后端环境变量或 `backend/.env`。
- `backend/.env` 被 `.gitignore` 忽略，不应提交。
- 前端不读取、不展示、不传递 key。
- 推荐配置模板：

```text
ENABLE_TW_STOCK_AGENT_OPENAI=true
OPENAI_BASE_URL=<openai-compatible-base-url>
TW_STOCK_AGENT_OPENAI_BASE_URL=<openai-compatible-base-url>
OPENAI_API_KEY=<backend-only secret>
TW_STOCK_AGENT_OPENAI_MODEL=gpt-4.1-mini
TW_STOCK_AGENT_OPENAI_TIMEOUT_SECONDS=20
```

- 验证命令：

```bash
set -a
. backend/.env
set +a
PYTHONPATH=backend python backend/scripts/smoke_tw_stock_agent_phase6b.py
```

文档中不得出现真实 key。

## 6. 必跑验证

执行者完成后至少运行：

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_agent_chat.py -q
```

```bash
cd frontend
node tests/unit/tw-stock-agent-panel-check.mjs
node tests/unit/tw-stock-agent-panel-e2e.mjs
node tests/e2e/tw-stock-agent-openai-skills-network.mjs
```

如果真实 OpenAI 后端需要手动启动，报告必须写清楚端口和启动方式。

## 7. 密钥泄露检查

执行者必须运行并报告结果：

```bash
git status --short --ignored backend/.env
git check-ignore -v backend/.env
rg -n "OPENAI_API_KEY=.*[A-Za-z0-9_]{8}|ChuLiYang|pqPEC" docs backend/app frontend/src backend/tests frontend/tests .env.example
```

预期：

- `backend/.env` 显示为 ignored。
- 可提交路径中不得出现真实 key。
- 文档中只能出现 `<backend-only secret>` 等占位符。

## 8. 报告断点

执行完成后提交：

```text
docs/TW_STOCK_AGENT_SKILLS_OPENAI_TEST_OPT_REPORT_CN.md
```

报告必须包含：

- 新增/修改文件清单。
- 网络级 Playwright 测试结果。
- UI skills 标签断言是否稳定通过。
- 后端真实 OpenAI smoke 结果。
- 密钥泄露检查结果。
- 是否触发任何危险请求。
- 是否建议收尾。

