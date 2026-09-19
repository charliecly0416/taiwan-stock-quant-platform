# Phase R1 工作文档：只读集成回归

生成日期：2026-06-20

## 1. 工作结论

Phase R0 已审查为有条件通过，允许进入 Phase R1。

R1 的目标是验证当前 Agent、UI2、Skills、模块合同和日更 orchestrator 地基是否可以作为新模型/新策略研发前的只读基线。

本阶段仍不是新模型或新策略研发。

## 2. 严禁事项

不得执行或触发：

```text
训练新模型
新增策略规则
修改默认模型或默认策略
修改前端默认展示
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target_position / target_weight 写入
OpenAI key 读取
真实 OpenAI smoke
```

如某命令需要上述能力才能通过，必须停止并在报告中说明，不得绕过。

## 3. 执行报告输出

执行者必须输出：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_EXECUTION_REPORT_CN.md
```

## 4. 推荐命令与验收点

### 4.1 Python 编译检查

执行：

```bash
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py scripts/run_daily_tw_stock_auto_update.py
```

验收：

```text
命令返回 0；
不读取 OpenAI key；
不触发数据拉取；
不写 provider/latest/monitor/broker/order。
```

### 4.2 Agent daily prompt / simple-chat 后端测试

执行：

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py backend/tests/test_tw_stock_agent_simple_chat.py backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py -q
```

验收：

```text
测试全部通过，或明确列出失败原因；
失败不得被简单忽略；
测试不得调用真实 OpenAI；
测试不得触发 provider publish / accepted latest / monitor / broker / order。
```

### 4.3 前端构建

执行：

```bash
cd frontend && corepack pnpm build
```

验收：

```text
build 通过；
如依赖或环境失败，记录完整失败原因；
不得引入前端 OpenAI key、browser-side OpenAI 或交易入口。
```

### 4.4 Agent simple-chat 前端静态检查

执行：

```bash
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

验收：

```text
前端主路径只调用 /api/tw-stock/agent/simple-chat；
不使用旧 /agent/chat 作为主路径；
不暴露 OpenAI key 或 OpenAI base URL；
payload 不含 order、broker、target_position、target_weight、monitor write、provider publish、accepted latest switch 字段。
```

### 4.5 UI2 readonly Playwright / fixture 检查

执行：

```bash
node frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
```

验收：

```text
desktop/tablet/mobile 证据可用；
主要面板不空白；
无明显文字重叠或横向溢出；
network/console audit 无 forbidden request；
不得触发 monitor write、provider publish、accepted latest、broker/order、frontend OpenAI。
```

如环境缺少 Playwright browser binary，必须报告：

```text
缺少 browser binary；
是否可用现有 npx playwright install chromium 权限；
是否有最近同等截图/network/console 证据；
该项是否阻塞 R1。
```

### 4.6 Daily orchestrator 只读 validator

执行：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

验收：

```text
validator 通过；
明确确认 run_daily_tw_stock_auto_update.py 没有默认打开 provider publish、accepted latest switch、monitor writes、broker/order、真实数据拉取。
```

### 4.7 Modular contract regression

执行：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

验收：

```text
合同回归通过；
至少覆盖 ModelSignalArtifact、StrategyRule、OrderIntentArtifact、ReplayResult、ReadonlyStrategySnapshot、DailyAgentPromptArtifact 相关链路；
不得用动态 payload 伪造缺失 artifact。
```

## 5. 失败处理规则

如果命令失败，执行报告必须包含：

```text
失败命令
退出码
关键错误信息
失败类型：代码问题 / dependency 问题 / sandbox 问题 / 服务未启动 / Playwright binary 缺失 / 其他
是否违反只读边界
是否存在最近等价证据
是否阻塞进入 R2/R3
```

不得把失败项写成“未覆盖但不影响”而不解释原因。

## 6. 报告格式

请输出：

```markdown
# Phase R1 执行报告：只读集成回归

## 1. 结论
## 2. 执行环境与只读声明
## 3. Python py_compile
## 4. Backend pytest
## 5. Frontend build
## 6. Frontend simple-chat static check
## 7. UI2 readonly Playwright / fixture evidence
## 8. Daily orchestrator readonly validator
## 9. Modular contract regression
## 10. Forbidden actions audit
## 11. 失败项与阻塞判断
## 12. 是否建议进入 R2
```

## 7. R1 通过标准

R1 可通过必须满足：

```text
关键 Python 文件 py_compile 通过；
Agent daily prompt / simple-chat pytest 通过，或失败有清晰非代码/非安全原因；
frontend build 通过，或失败有清晰环境原因；
simple-chat 静态检查无 OpenAI/front-end/交易字段问题；
UI2 readonly evidence 可用，或 Playwright 环境问题被清楚记录；
daily orchestrator validator 未发现 provider/latest/monitor/broker/order 风险；
modular contract regression 通过，或失败项明确且不被掩盖；
全程没有触发真实数据、provider publish、accepted latest、monitor、broker/order、OpenAI key。
```

如果 R1 有任何真实安全边界失败，应判定为不通过，不能进入新模型/新策略研发。
