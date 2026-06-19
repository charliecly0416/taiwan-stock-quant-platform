# Phase V4R 审查与 Phase V5 工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase V4R 条件通过，但 V 路线仍不能收尾，建议进入 Phase V5。

V4R 已把外部 provider fallback、真实外网审计和前端只读结果解释补齐到可审计状态：

- Yahoo 外网请求真实发生并被记录。
- FinMind 三类数据成功拉到。
- Yahoo 403 时，价格层通过 `preferred_yahoo_fallback_finmind` 进入可解释 fallback。
- 前端真实后端 E2E 已命中允许的 POST 路径，且没有越界请求。
- 只读安全边界仍然成立。

但真实 run 仍然停在：

```text
status=no_new_data
gate_status=no_new_data
readonly_latest_updated=false
u_chain_started=false
```

阻断点不是 provider 审计，而是 `orthogonal_o2_features` 仍落后于 `target_asof=2026-06-17`，其最新仅到 `2026-06-10`。因此当前只是“可解释失败 / 可审计 fallback”，还不是“真实外部数据就绪并成功更新 readonly latest”的最终收口。

结论：V4R 通过，但 V 路线不可收尾，必须进入 V5 解决正交特征 freshness 与 gate 收敛。

V5 的实现前提需要先求证历史成功证据，再写成执行合同：

- FinMind 侧，代码里已经能确认支持 `FINMIND_TOKEN` / `FINMIND_API_TOKEN` 注入，但 V5 文档不直接写死具体抓取组合，执行者要回看历史成功文档和脚本产物再定稿。
- Yahoo 侧，历史文档和脚本里确实能看到 `Yahoo/Scrapling` 相关路径，但 V5 文档不把它当成最终结论，必须用成功产物和脚本审计来确认实际使用方式。
- 这些抓取方式只用于把数据拉到 staging / readiness gate，不改变只读边界。

## 2. 复核范围

审查输入：

```text
docs/tw_modular_daily_update_productization/PHASEV4R_EXTERNAL_PROVIDER_FALLBACK_AND_FRONTEND_RESULT_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_modular_daily_update_productization/PHASEV4_REVIEW_AND_PHASEV4R_WORK_CN.md
docs/tw_modular_daily_update_productization/PHASEV_REAL_PROVIDER_DATA_READINESS_AND_AUTO_CHAIN_WORK_CN.md
data_tw/artifacts/real_provider_daily_update_runs/phasev4r_external_provider_orchestrator_codex_v1/run_registry.json
data_tw/artifacts/provider_staging/phasev4r_external_provider_orchestrator_codex_v1_provider_staging/data_readiness_manifest.json
data_tw/artifacts/provider_staging/phasev4r_external_provider_orchestrator_codex_v1_provider_staging/external_provider_fetch/provider_network_audit.json
data_tw/artifacts/real_provider_daily_update_runs/phasev4r_external_provider_orchestrator_codex_v1/provider_staging_validation_result.json
data_tw/artifacts/frontend_e2e/phasev4r_real_backend_daily_update_e2e.json
```

复核命令：

```text
python scripts/validate_tw_real_provider_daily_readonly_update.py --artifact-path data_tw/artifacts/real_provider_daily_update_runs/phasev4r_external_provider_orchestrator_codex_v1/run_registry.json --json
python scripts/validate_tw_provider_staging_data.py --staging-dir data_tw/artifacts/provider_staging/phasev4r_external_provider_orchestrator_codex_v1_provider_staging --json
python -m py_compile scripts/fetch_tw_provider_external_data.py scripts/pull_tw_provider_staging_data.py scripts/build_tw_data_readiness_gate.py scripts/run_tw_real_provider_daily_readonly_update.py scripts/validate_tw_real_provider_daily_readonly_update.py backend/app/services/readonly_daily_update_runs.py backend/app/routes/readonly_daily_update_runs.py
```

复核结果：

```text
real_provider_daily_update_validator: passed
provider_staging_validator: passed
py_compile: passed
frontend_e2e: ok=true, trigger_post_count=1, forbidden_request_count=0, console_error_count=0, page_error_count=0
```

## 3. 已通过项

### 3.1 外网请求真实发生

`provider_network_audit.json` 记录：

```text
request_count=25
actual_external_request_count=25
unauthorized_request_count=0
allowed_hosts=[api.finmindtrade.com, query1.finance.yahoo.com]
```

Yahoo 与 FinMind 都是实际外网请求，不是本地假数据。

### 3.2 FinMind 数据已 ready

`data_readiness_manifest.json` 中：

- `finmind_daily_price=ready`
- `finmind_institutional_flow=ready`
- `finmind_margin_short=ready`

说明真实 provider reader 和材料化路径已经成立。

### 3.3 Yahoo 403 已被可解释 fallback

`yahoo_daily_price` 真实返回 403，但价格层通过 fallback 标记为 ready，且记录了：

- `price_source_policy=preferred_yahoo_fallback_finmind`
- `fallback_used=true`
- `fallback_source_id=finmind_daily_price`

这一步修复了 V4 的“失败不可解释”问题。

### 3.4 只读安全边界成立

run registry 证明：

- `provider_publish_triggered=false`
- `accepted_latest_switched=false`
- `qlib_accepted_latest_switched=false`
- `monitor_config_written=false`
- `monitor_scan_triggered=false`
- `alerts_written=false`
- `broker_connected=false`
- `quick_trade_triggered=false`
- `orders_created_or_sent=false`
- `agent_prompt_or_tool_modified=false`

没有越过只读边界。

## 4. 阻断项

### 4.1 Critical：gate 仍停在 `no_new_data`

真实 run 结果仍是：

```text
status=no_new_data
gate_status=no_new_data
readonly_latest_updated=false
u_chain_started=false
```

这说明 V4R 还没有推进到“新 readonly latest 已生成”的收口状态。

### 4.2 High：orthogonal O2 freshness 仍落后

阻断原因已经明确：

```text
orthogonal_o2_features.actual_latest_asof=2026-06-10
target_asof=2026-06-17
```

在这一点修复前，gate 不会进入 `all_required_ready`，也不会进入 U 链。

### 4.3 Medium：前端仍偏工程化

前端已经能读后端 `user_message`，也能做真实后端 POST 验证，但主状态仍偏通用：

```text
可更新
数据就绪状态 -，成功后展示最新只读策略；失败或没数据时保留旧结果。
```

这对工程排查够用，但对普通用户还不够“简单、准确、实用、清晰”。

## 5. 台股只读安全边界审查

### Findings

- Critical：未发现 broker / quick-trade / orders / target position / provider publish / accepted latest 越界。
- Critical：真实 run 仍为 `no_new_data`，不能作为 V 路线最终收尾。
- High：orthogonal O2 freshness 未追到 `target_asof`，导致 gate 无法进入 `all_required_ready`。
- Medium：前端文案已改善，但仍有工程化表达残留。

### Network Audit

通过：

```text
unauthorized_request_count=0
allowed_hosts only = api.finmindtrade.com, query1.finance.yahoo.com
```

Yahoo 403 真实存在，FinMind 真实成功。

### Console Audit

前端真实后端 E2E：

```text
console_error_count=0
page_error_count=0
```

### Text / Agent Semantics

未发现交易、目标仓位、下单、收益承诺或 Agent 扩权语义。

### Verdict

V4R 通过，但 V 路线不可收尾。

## 6. Phase V5 必须修复

V5 的目标只有一个：把真实 provider fallback 之后的链路推进到 `all_required_ready`，并验证 readonly latest 真正更新。

### 6.0 先求证抓取口径

V5 执行前，先用历史成功文档和脚本把数据抓取口径定清楚，而不是依赖回忆：

- FinMind：确认哪些成功脚本是通过 token 注入拉到更多数据，哪些字段或数据集真正依赖 token。
- Yahoo：确认历史成功路径到底是 Scrapling、其他抓取器，还是脚本内的既有封装。
- 只有在证据闭环后，才把抓取方式写进 V5 执行步骤。

### 6.1 修复 orthogonal freshness

必须明确解决以下至少一项：

```text
orthogonal_o2_features 重新 materialize 到 target_asof
或让其 contract 允许在明确规则下 carry-forward / pending
或补齐可追溯的重算流程，使 gate 真实进入 all_required_ready
```

必须证明：

- `orthogonal_o2_features.status=ready`
- `actual_latest_asof >= target_asof`
- `gate_status=all_required_ready`

### 6.2 真实 U 链验收

V5 必须补齐真实 `all_required_ready` 样本，验证：

```text
u_chain_started=true
u_chain validators passed
readonly_latest_updated=true
```

### 6.3 前端用户原则收敛

主状态应收敛成用户可理解表达，例如：

```text
数据已更新，正在展示最新只读策略结果
数据还没到，旧结果继续保留
外部行情源暂时不可用，系统会等待下一轮重试
```

细节仍可放入诊断区，但主界面应保持单句、单主按钮、单主解释。

### 6.4 V5 应作为终止位设计

V5 不应默认再往后切成 V6。当前路线的正确做法是把 V5 设计成收口阶段：

- 如果 orthogonal freshness、gate、U 链、readonly latest 都能在 V5 里闭环，V 路线直接收尾。
- 只有当实际运行证明某个前提长期无法满足，且问题不再属于“修复实现”而是“合同需要重写”，才另起 V6。

也就是说，V6 不是当前规划的一部分，只是极端兜底，不应提前引入。

## 7. V 路线最终收尾门槛

V 路线只有在以下条件同时满足时才能收尾：

```text
provider fallback 可审计
orthogonal O2 追平 target_asof
gate_status=all_required_ready
U-chain validators 全通过
readonly_latest_updated=true
前端真实后端 E2E 可运行且返回及时
前端主文案符合简单、准确、实用、清晰
provider network audit / frontend audit 均通过
```

当前 V4R 还没到这一步，但 V5 应按这个门槛一次性收口。
