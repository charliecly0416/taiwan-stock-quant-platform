# Phase R1 执行报告：只读集成回归

生成日期：2026-06-20

## 1. 结论

Phase R1 已按工作文档执行只读集成回归。结论：不建议直接进入 R2/R3；当前存在需要审查确认的阻塞失败项。

通过项：

```text
Python py_compile 通过
Agent daily prompt / simple-chat backend pytest 通过，37 passed
frontend build 通过
UI2 readonly Playwright / fixture 检查通过
daily orchestrator readonly validator 通过
```

失败项：

```text
frontend simple-chat static check 失败：推荐问题文案断言不匹配
modular contract regression 失败：M2 registry/template 与 M4 frontend readonly 字段覆盖失败
```

安全边界结论：本阶段未触发真实数据拉取、provider publish/refresh、accepted latest switch、monitor config/scan/alerts 写入、broker/quick-trade/order、OpenAI key 读取或真实 OpenAI smoke。失败项目前看属于静态断言/合同覆盖缺口，不是 forbidden request 或真实交易链路被触发。

## 2. 执行环境与只读声明

执行目录：

```text
/home/chuliyang/taiwan-stock-quant-platform
```

本阶段执行的命令均为：

```text
py_compile
pytest
frontend build
node static/e2e readonly checks
validator / contract regression
```

普通沙箱对部分 `node` / `python` 命令出现：

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

这些命令初次失败时未进入测试逻辑；按权限规则以提升权限重跑后获得真实测试结果。提升权限只用于本地只读测试/validator 执行，不用于网络下载、真实数据拉取、provider/latest/monitor/broker/order/OpenAI。

## 3. Python py_compile

执行：

```bash
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py scripts/run_daily_tw_stock_auto_update.py
```

结果：

```text
退出码：0
```

结论：通过。

只读边界：编译检查不读取 OpenAI key，不触发数据拉取，不写 provider/latest/monitor/broker/order。

## 4. Backend pytest

执行：

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py backend/tests/test_tw_stock_agent_simple_chat.py backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py -q
```

结果：

```text
退出码：0
37 passed in 1.68s
```

结论：通过。

覆盖点：

- DailyAgentPromptArtifact validator。
- prompt builder。
- simple-chat service。
- Agent daily prompt orchestration。

只读边界：未触发真实 OpenAI、provider publish、accepted latest、monitor、broker 或 order。

## 5. Frontend build

执行：

```bash
cd frontend && corepack pnpm build
```

结果：

```text
退出码：0
vite build 通过
```

备注：

```text
/bin/sh: 2: source: not found
```

该行来自 shell 初始化环境，未导致 build 失败。

结论：通过。

## 6. Frontend simple-chat static check

初次执行：

```bash
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

普通沙箱结果：

```text
退出码：1
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

提升权限重跑后，命令进入测试逻辑：

```bash
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

结果：

```text
退出码：1
AssertionError [ERR_ASSERTION]: The input did not match the regular expression /明天关注哪些股票？/
```

失败类型：

```text
代码/测试断言不匹配
```

失败解释：

- 测试脚本要求 `frontend/src/views/tw-stock-monitor/index.vue` 中包含推荐问题文案 `明天关注哪些股票？`。
- 当前页面源码不包含该精确文案，因此断言失败。
- 脚本中其他关键边界仍包括：`simpleChatTwStockAgent`、`/agent/simple-chat`、`signal_asof`、`target_date`、`checksum`、citations/warnings/disclaimer，以及 simple-chat block 不得包含 OpenAI、quick-trade、broker、target_position、target_weight、provider publish、accepted latest、monitor scan/alerts。

是否违反只读边界：

```text
未发现真实执行或 forbidden request；失败发生在本地静态断言。
```

阻塞判断：

```text
阻塞 R1 直接通过。需要审查者判断是补回推荐问题文案，还是更新静态检查脚本的期望文案。
```

## 7. UI2 readonly Playwright / fixture evidence

初次执行：

```bash
node frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
```

普通沙箱结果：

```text
退出码：1
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

提升权限重跑后，命令进入测试逻辑：

```bash
node frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
```

结果：

```text
退出码：0
```

关键输出：

```json
{
  "artifactDir": "/home/chuliyang/tmp/tw_ui2d_workbench_acceptance",
  "audit": {
    "required_text_passed": true,
    "forbidden_visible_passed": true,
    "overflow_passed": true,
    "button_overflow_passed": true,
    "technical_details_default_collapsed": true
  },
  "networkAudit": {
    "request_count": 63,
    "simple_chat_request_count": 1,
    "forbidden_request_count": 0,
    "monitor_config_write_count": 0,
    "monitor_scan_post_count": 0,
    "monitor_alerts_write_count": 0,
    "ops_dry_run_post_count": 0,
    "failed_response_count": 0
  },
  "consoleAudit": {
    "console_error_count": 0,
    "page_error_count": 0
  }
}
```

证据产物：

```text
/home/chuliyang/tmp/tw_ui2d_workbench_acceptance/audit.json
/home/chuliyang/tmp/tw_ui2d_workbench_acceptance/network_audit.json
/home/chuliyang/tmp/tw_ui2d_workbench_acceptance/console_audit.json
/home/chuliyang/tmp/tw_ui2d_workbench_acceptance/desktop.png
/home/chuliyang/tmp/tw_ui2d_workbench_acceptance/tablet.png
/home/chuliyang/tmp/tw_ui2d_workbench_acceptance/mobile.png
```

结论：通过。

## 8. Daily orchestrator readonly validator

初次执行：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

普通沙箱结果：

```text
退出码：1
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

提升权限重跑后，命令进入 validator：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

结果：

```text
退出码：0
ok=true
status=passed
```

关键审计：

```text
legacy_provider_gate_present=true
legacy_provider_gate_default_disabled=true
provider_refresh_guarded=true
provider_publish_guarded=true
accepted_latest_call_guarded=true
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
readonly_latest_pointer_distinct=true
broker_order_patterns_present=[]
monitor_write_patterns_present=[]
```

warnings：

```text
legacy_provider_publish_path_present
legacy_accepted_latest_path_present
```

解释：legacy provider publish / accepted latest 代码路径存在，但 validator 确认默认 gate 关闭且默认不可达。

结论：通过，有非阻塞 warning。

## 9. Modular contract regression

初次执行：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

普通沙箱结果：

```text
退出码：1
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

提升权限重跑后，命令进入 regression：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
退出码：2
ok=false
```

总体摘要：

```text
m1_contract_status=passed
m2_registry_status=failed
m3_daily_orchestrator_status=passed
m3_daily_script_audit_status=passed
m4_frontend_readonly_status=failed
m4_forbidden_request_count=0
m4_legacy_provider_gate_not_exposed=true
m5_onboarding_smoke_status=passed
```

### 9.1 M2 registry/template 失败

详情文件：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/m2_registry_validation.json
```

失败原因：

```text
template_missing: docs/tw_modular_contracts/templates/EXECUTION_REPORT_TEMPLATE_CN.md
template_marker_missing: contract_doc
template_marker_missing: schema_version
template_marker_missing: input_artifacts
template_marker_missing: output_artifacts
template_marker_missing: validator_command
template_marker_missing: golden_sample_path
template_marker_missing: allowed_consumers
template_marker_missing: forbidden_consumers
template_marker_missing: readonly_boundary
template_marker_missing: forbidden_actions_audit
template_marker_missing: production_allowed: false
```

解释：

- registry entries 本身显示 14 条均 pass。
- 失败集中在缺少通用执行报告模板 `EXECUTION_REPORT_TEMPLATE_CN.md` 及其必备 marker。

### 9.2 M4 frontend readonly 失败

详情文件：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/m4_frontend_readonly_validation.json
```

失败原因：

```text
primary_field_missing: 合法窗口
primary_field_missing: 手续费/税费
primary_field_missing: 审计状态
```

安全审计同时显示：

```text
network_audit.readonly_workflow_only_get=true
forbidden_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
replay_strategy_write_count=0
broker_quick_trade_orders_request_count=0
readonly_component_monitor_write_count=0
legacy_provider_gate_not_exposed=true
```

解释：

- 失败属于前端 readonly 组件必须展示的 primary field 覆盖缺口。
- 未发现 forbidden request 或交易/monitor/provider/latest/OpenAI 暴露。

结论：

```text
modular contract regression 未通过，阻塞 R1 直接通过。
```

## 10. Forbidden actions audit

本阶段未执行：

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

证据：

- Daily orchestrator validator：default provider refresh/publish/accepted latest 均不可达；broker/monitor write patterns 为空。
- UI2 readonly network audit：forbidden_request_count=0，monitor/broker/provider/latest/frontend OpenAI 相关计数为 0。
- M4 frontend readonly validation：forbidden_request_count=0，readonly workflow only GET。

## 11. 失败项与阻塞判断

| 失败项 | 退出码 | 失败类型 | 是否安全边界失败 | 阻塞判断 |
| --- | --- | --- | --- | --- |
| `node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs` | 1 | 静态断言/文案不匹配 | 否 | 阻塞 R1 直接通过 |
| `python scripts/run_tw_modular_contract_regression.py --json` | 2 | 合同回归失败 | 否，当前详情未见 forbidden request | 阻塞 R1 直接通过 |

R1 不能判定为通过，因为工作文档要求失败项不能被掩盖。建议审查者决定 repair 范围：

```text
1. simple-chat 推荐问题文案：恢复测试期望文案，或更新测试断言到当前产品文案。
2. M2 registry/template：补齐 EXECUTION_REPORT_TEMPLATE_CN.md 及 marker，或确认 validator 期望是否应调整。
3. M4 frontend readonly：补齐 ReadonlyReplayWindow/ReadonlyStrategySnapshot primary field 展示（合法窗口、手续费/税费、审计状态），或更新 validator 对当前 UI 文案/字段映射的识别。
```

## 12. 是否建议进入 R2

执行侧建议：

```text
暂不建议直接进入 R2。
```

理由：

- R1 出现两个命令级失败项，包含 simple-chat 推荐问题文案、M2 执行报告模板、M4 readonly primary fields 三个具体缺口。
- 失败项不是安全边界越界，但属于 readiness freeze 的合同/静态验收缺口。
- 按 R1 工作文档，应先由审查者确认是否 repair，再进入 R2 Skills 与运行时入口确认。

如果审查者判定这些失败均为非阻塞文案/validator drift，可有条件进入 R2；否则应先执行 R1 repair。
