---
created_at: 2026-07-16
status: coordinator_mainline
route: LPEF_LATEST_PUBLISH_EXECUTION_FEASIBILITY_AND_PREFLIGHT
coordinator: Codex
production_allowed: false
provider_pull_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
qlib_refresh_allowed: false
readonly_latest_publish_allowed: false
agent_prompt_latest_publish_allowed: false
openai_call_allowed: false
daily_auto_run_allowed: false
crontab_change_allowed: false
monitor_write_allowed: false
broker_order_allowed: false
target_output_allowed: false
---

# LPEF Latest Publish Execution Feasibility And Preflight Mainline

## 0. Current Route State

截至 2026-07-17，LPEF 已从最初 feasibility/preflight 扩展为受控 accepted latest payload 与 pointer switch gate 路线。

当前状态：

```text
LPEF0 PASS_PREFLIGHT_READY_FOR_USER_DECISION
LPEF1 PASS_WITH_CONDITIONS
LPEF2 PASS_STOP_PREWRITE_INPUT_MISSING_NO_WRITE
LPEF3 PASS_FEASIBLE_NEEDS_LPEF4_BUILD_AUTHORIZATION
LPEF4 PASS_PAYLOAD_BUILT_NO_POINTER_WRITE
LPEF5 current next step = CONTROLLED_ACCEPTED_LATEST_POINTER_SWITCH_GATE
LPEF5 actual switch PASS_POST_WRITE_REVIEW_ACCEPTED_LATEST_POINTER_SWITCH_ONLY
LPEF6 current next step = DOWNSTREAM_READONLY_ACCEPTANCE_AND_ROUTE_CLOSURE
```

当前 candidate accepted run payload：

```text
qlib_pipeline/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260708_lpef4_adapter_20260717T000000Z/
target_asof=2026-07-08
source_model_recorder=950741cfd5f14ee5a05464fec3e12e0a
diagnostic_only=true
research_signal_not_order=true
```

LPEF5 只能开启 pointer switch gate，不得把“开 LPEF5”“进入下一步”“继续”解释为实际写入授权。

LPEF5 actual switch 已在用户完整授权后完成。当前 qlib accepted latest 为：

```text
target_asof=2026-07-08
target_run_id=option_c_daily_signal_20260708_lpef4_adapter_20260717T000000Z
only_write_path=qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
review_verdict=PASS_POST_WRITE_REVIEW_ACCEPTED_LATEST_POINTER_SWITCH_ONLY
```

## 1. Goal

LPEF 用于在 PCOM3 之后，以只读方式判断是否值得进入未来 latest publish execution route。

LPEF0 只做 feasibility/preflight，不写 latest、不切 accepted latest、不刷新 provider、不运行 daily auto、不调用 OpenAI、不写 monitor/broker/order/target。

## 2. Baseline

PCOM3 verdict:

```text
PASS_WITH_CONDITIONS_CONTRACT_READY_BUT_PUBLISH_ROUTE_BLOCKED
```

PCOM3 允许的下一步只有：

```text
maintenance/no-publish observation
or
separate latest publish feasibility/preflight route after explicit user confirmation
```

用户已要求开启 LPEF0。

## 3. Current Known State

当前必须保留状态分离：

```text
raw-ready != provider-ready
provider/bridge-ready != signal-ready
signal-ready != accepted/latest publish-ready
readonly snapshot candidate != readonly latest publish authorization
Agent prompt artifact candidate != Agent prompt latest automation authorization
```

已知状态：

```text
qlib accepted latest signal=2026-06-17
controlled signal latest=2026-07-08
readonly strategy snapshot latest=2026-07-08 candidate_only/readonly_only
Agent DailyAgentPromptArtifact latest=2026-07-08 readonly_only
FinMind raw observed latest=2026-07-08 per R19E/DASF
formal provider calendar max=2026-06-25 per R19E/DASF
PCOM2R no-publish cron evidence=5 distinct valid trading days
```

## 4. Phase Plan

### LPEF0 - Latest Publish Feasibility And Preflight

只读检查：

```text
current latest pointer states
candidate target_asof
which pointer classes are already readonly/candidate latest
which accepted/latest path remains stale or blocked
existing validators / validator reports
protected latest fingerprint plan
rollback plan requirements
future route split recommendation
```

LPEF0 不执行 publish。

### LPEF1 - Controlled Write Approval Package

只有 LPEF0 review PASS 且用户再次显式确认后才可开启。

LPEF1 仍应先做 approval package，不应直接写。

### LPEF2 - Controlled Write Execution

只有 LPEF1 review PASS 且用户确认 exact write scope 后才可执行。

### LPEF3 - Accepted Latest Payload Adapter Or Stop Decision

在 LPEF2 发现缺少 `2026-07-08` accepted run payload 后，冻结从 ModelSignalArtifact 到 Option C accepted run 的适配规则。

LPEF3 不写 payload，不写 pointer。

### LPEF4 - Accepted Latest Payload Adapter Build No Pointer Write

在用户授权后，只创建 `2026-07-08` candidate accepted run payload，并执行 reader/formal validation。

LPEF4 禁止写入 `latest_signal.json`。

### LPEF5 - Controlled Accepted Latest Pointer Switch Gate

LPEF5 只做 actual pointer switch 前确认门：

```text
确认 candidate run 是否仍完整
确认 protected latest pointer 当前 fingerprint
确认 rollback copy / before fingerprint / after fingerprint / diff / post-write review 计划
冻结 exact switch scope
产出用户授权模板
STOP at explicit confirmation gate
```

LPEF5 不执行 pointer switch。实际 switch 必须在 LPEF5 review PASS 后，由用户用完整授权文本再次确认。

### LPEF6 - Downstream Readonly Acceptance And Route Closure

LPEF6 在 LPEF5 actual switch post-write review PASS 后执行，只做下游只读验收与路线关闭。

LPEF6 允许：

```text
read QlibOptionCSignalReader.latest/run_detail/health
read current latest pointers and manifests
run backend readonly tests that use GET/test_client/local readers
run frontend static readonly checks if scoped and available
write LPEF6 evidence/report/review/closure docs
```

LPEF6 不允许：

```text
accepted latest switch
provider pull/publish/refresh
qlib refresh
daily auto run
readonly snapshot latest publish
Agent prompt build/publish
OpenAI
monitor write/scan/alerts
broker/order/quick-trade
target_position / target_weight / quantity / shares / lots output
production/default switch
future automatic latest switch authorization
```

## 5. Forbidden Actions

LPEF0 永远禁止：

```text
daily auto run
provider pull
provider publish
accepted/latest switch
qlib refresh
readonly latest publish
Agent prompt latest publish
OpenAI call
crontab install/change
monitor write
broker/order/quick-trade
OrderIntentArtifact generation
target_position / target_weight / quantity / shares / lots output
production/default switch
real TradingAgents run
network access
```

LPEF5 额外禁止：

```text
写入 qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
写入 data_tw/experiments/option_c_daily_signal/latest_signal.json
改动 readonly snapshot latest
改动 Agent DailyAgentPromptArtifact latest
把 PBPR2A-AC isolated candidate 升级为 final production readiness
把本次 one-time accepted latest switch 扩展为 future automatic latest switch
```

## 6. Closure Criteria

LPEF0 可以关闭为：

```text
PASS_PREFLIGHT_READY_FOR_USER_DECISION
PASS_WITH_CONDITIONS_PREFLIGHT_FOUND_BLOCKERS
FAIL_NEEDS_REPAIR
STOP_NEEDS_USER_DECISION
```

LPEF0 若发现 provider/accepted latest publish 不具备条件，应明确 blocker，而不是补跑 provider 或自动切 latest。

LPEF5 关闭条件：

```text
PASS_STOPPED_AT_POINTER_SWITCH_CONFIRMATION_GATE
PASS_WITH_CONDITIONS_NEEDS_REPAIR_BEFORE_SWITCH
FAIL_NEEDS_REPAIR
STOP_NEEDS_USER_DECISION
```

LPEF6 关闭条件：

```text
PASS_LPEF_ROUTE_CLOSED_READONLY_ACCEPTED
PASS_WITH_CONDITIONS_ROUTE_CLOSED_WITH_OBSERVATION_GAPS
FAIL_NEEDS_REPAIR
STOP_NEEDS_USER_DECISION
```

## 7. First Executor Command

```text
执行 LPEF0_LATEST_PUBLISH_FEASIBILITY_AND_PREFLIGHT：只读读取 PCOM3 contract/review、current latest pointers、existing manifests、existing validator reports，并运行只读 validator（仅当 CLI 不写文件）。输出 LPEF0 evidence 和 execution report。不得执行 publish/latest/provider/qlib/daily/OpenAI/monitor/broker/order/target。
```

## 8. Reviewer Brief

Reviewer 必须确认：

```text
LPEF0 未写 latest
provider/accepted latest blocker 未被绕过
readonly/candidate artifacts 未被误判为 accepted latest ready
validators/fingerprints/rollback/user-confirmation requirements 具体
next step is user decision, not direct execution
forbidden actions all false
```
