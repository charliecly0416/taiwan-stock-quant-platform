# Phase U2 审查与 Phase U3 工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase U2 通过，允许进入 Phase U3。

U2 已从 U1 daily ModelSignalArtifact 生成 daily OrderIntentArtifact、daily ReadonlySnapshot、daily RunRegistry 和 U2 专用 readonly latest pointer。审查复跑确认：OrderIntent 保持只读观察语义，Snapshot 不含交易建议或目标仓位，RunRegistry 覆盖 success / no_new_data / validator_failed / module_failed 四类状态，latest pointer 只在 success 且 validators 全部通过时提交 proposed latest；noop 和失败状态保留 previous latest。

本轮未发现训练、调参、替换冻结模型权重、provider refresh / publish、provider accepted latest 或 qlib accepted latest 切换、monitor config / scan / alerts 写入、broker / quick-trade / orders、Agent prompt / tool / action 修改，也未把 U1/U2 staging 产物接入前端默认展示。

## 2. 复核范围

审查输入：

```text
docs/tw_modular_daily_update_productization/PHASEU2_DAILY_ORDER_INTENT_READONLY_SNAPSHOT_RUN_REGISTRY_EXECUTION_REPORT_CN.md
docs/tw_modular_daily_update_productization/PHASEU1_REVIEW_AND_PHASEU2_WORK_CN.md
scripts/build_tw_daily_order_intent_artifact.py
scripts/validate_tw_daily_order_intent_artifact.py
scripts/publish_tw_daily_readonly_snapshot.py
scripts/validate_tw_daily_readonly_snapshot.py
scripts/validate_tw_daily_run_registry.py
data_tw/golden_samples/modular_daily_update/u2/
data_tw/artifacts/daily_order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/
data_tw/artifacts/daily_readonly_snapshots/
data_tw/artifacts/daily_run_registry/
data_tw/artifacts/daily_readonly_latest/latest.json
data_tw/experiments/modular_daily_update/u2_validation_summary.json
```

审查重点：

```text
OrderIntent 是否 readonly_only / not_order / not_target_position / not_investment_advice
OrderIntent 是否无 broker/order/target/cash/equity/execution 字段
ReadonlySnapshot 是否只读展示，来源可追溯且无交易语义
RunRegistry 是否覆盖 success/no_new_data/validator_failed/module_failed
latest pointer 是否只在 validators pass 后更新，noop/失败是否保留 previous latest
latest pointer 是否明确不是 provider accepted latest 或 qlib accepted latest
是否未触发 provider/latest、monitor/broker/order、Agent 扩权
M3 legacy gate 与 M4 frontend GET-only gate 是否仍通过
```

## 3. 通过项

### 3.1 OrderIntent 边界正确

`validate_tw_daily_order_intent_artifact.py` 会校验：

```text
readonly_only=true
not_order=true
not_target_position=true
not_investment_advice=true
no_broker_order=true
production_trade_enabled=false
model_id=e4_frozen_qlib_2023_2025_ltr
strategy_rule=top50_exit_one_worst_sell
source_signal_artifact
portfolio_state_source
max_buy_count
max_sell_count
checksum
```

并阻断：

```text
execution
order_qty
order_id
target_position
target_weight
cash
equity
quick_trade
forbidden_action_audit 中任一 true action
```

复跑 golden：

```text
OrderIntent golden: ok=true, sample_count=3
fail_order_intent_contains_broker_order -> forbidden_order_field_present
fail_order_intent_contains_target_position -> forbidden_order_field_present
```

direct validation：

```text
data_tw/artifacts/daily_order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/u2_success_order_intent_demo
ok=true
status=passed
```

### 3.2 ReadonlySnapshot 边界正确

`validate_tw_daily_readonly_snapshot.py` 会校验：

```text
readonly_only=true
not_order=true
not_target_position=true
not_investment_advice=true
production_trade_enabled=false
source_order_intent_artifact
source_model_signal_artifact
source_strategy_rule
audit_status
checksum
```

并阻断 snapshot 内容中的危险语义：

```text
broker_order_id
target_weight
order_qty
cash
equity
production_trade_instruction
```

复跑 golden：

```text
ReadonlySnapshot golden: ok=true, sample_count=2
fail_snapshot_missing_readonly_flags -> snapshot_readonly_flag_missing
```

direct validation：

```text
data_tw/artifacts/daily_readonly_snapshots/u2_success_readonly_snapshot_demo
ok=true
status=passed
```

### 3.3 RunRegistry / latest pointer 行为正确

`validate_tw_daily_run_registry.py` 会校验：

```text
run_id
status
previous_latest
proposed_latest
committed_latest
checksum
updated_only_after_all_validators_passed=true
not_provider_accepted_latest=true
not_qlib_accepted_latest=true
not_trade_target_latest=true
provider_accepted_latest_changed=false
qlib_accepted_latest_changed=false
```

关键行为：

```text
success: validators 全部 ok 且 committed_latest == proposed_latest
no_new_data: committed_latest == previous_latest
validator_failed/module_failed: committed_latest 保留 previous latest
```

复跑 golden：

```text
RunRegistry golden: ok=true, sample_count=6
fail_latest_pointer_updates_before_validators_pass -> latest_pointer_updates_before_validators_pass
fail_latest_pointer_is_provider_accepted_latest -> latest_pointer_is_provider_accepted_latest / latest_pointer_safety_flag_missing
```

direct validation：

```text
u2_success_run_registry_demo: ok=true
u2_no_new_data_run_registry_demo: ok=true
u2_validator_failed_run_registry_demo: ok=true
u2_module_failed_run_registry_demo: ok=true
```

当前 U2 专用 pointer：

```text
data_tw/artifacts/daily_readonly_latest/latest.json
```

最终状态为：

```text
status=no_new_data
previous_latest=data_tw/artifacts/daily_readonly_snapshots/u2_success_readonly_snapshot_demo/manifest.json
proposed_latest=data_tw/artifacts/daily_readonly_snapshots/u2_no_new_data_readonly_snapshot_demo/manifest.json
committed_latest=data_tw/artifacts/daily_readonly_snapshots/u2_success_readonly_snapshot_demo/manifest.json
updated_only_after_all_validators_passed=true
not_provider_accepted_latest=true
not_qlib_accepted_latest=true
not_trade_target_latest=true
readonly_only=true
production_trade_enabled=false
```

这符合 U2 预期：noop 可以写审计型 pointer 状态，但 committed latest 必须保留 previous latest。

### 3.4 安全 gate 仍通过

复跑 M3 daily audit：

```text
ok=true
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
readonly_latest_pointer_distinct=true
```

复跑 M4 frontend readonly validator：

```text
ok=true
readonly_workflow_only_get=true
forbidden_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
replay_strategy_write_count=0
broker_quick_trade_orders_request_count=0
agent_implementation_untouched=true
agent_contract_placeholder_only=true
```

## 4. 台股只读安全边界审查

### Findings

Critical：未发现 U2 触发 provider refresh / publish、provider accepted latest 或 qlib accepted latest switch、broker / quick-trade / orders、target position 或真实交易路径。

High：未发现 U2 写 monitor config / scan / alerts；U2 未接入前端默认展示，未修改 Agent prompt / tool / action。

Medium：`publish_tw_daily_readonly_snapshot.py` 在 `--update-latest` 时会写 `data_tw/artifacts/daily_readonly_latest/latest.json`，包括 no_new_data / failed 的审计型 latest pointer 状态。当前是 U2 专用 readonly pointer，且 committed latest 行为正确，不阻塞；U3 必须明确自动链路允许写哪个 readonly pointer 路径，并证明它不是 provider accepted latest、qlib accepted latest 或交易 latest。

Low：Snapshot validator 会阻断若干危险字段和只读标志缺失，但 U3 前端文案仍需另做运行时 network/console/text audit，避免 UI 把 `intent_action=buy` 误展示为交易指令。U3 文案应使用“观察/候选动作/只读意图”等研究语义，并保留 `not_order` / `not_investment_advice`。

### Verdict

U2 通过。可以进入 U3 的自动脚本接入、GET-only API/前端验收和最终 runbook，但 U3 必须重新证明运行时网络请求、后端路由、前端文案和 Agent 边界安全。

## 5. 残余风险

1. U2 latest pointer 是 `data_tw/artifacts/daily_readonly_latest/latest.json` 专用路径，不是既有 `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json`，也不是 qlib/provider accepted latest。U3 要明确最终产品读取哪个 pointer，以及如何迁移或并存。
2. U2 写了 staging snapshot/latest artifact，但没有接入后端 API 或前端默认展示；U3 是第一次运行时验收，必须做 network audit。
3. OrderIntent CSV 中存在 `intent_action=buy/skip` 这类策略语义字段。它们在 U2 中有 `not_order=true` 和 `not_investment_advice=true` 保护；U3 前端不得把它们展示成“买入/下单/目标仓位”。
4. M3 legacy provider publish / accepted latest 代码路径仍存在，但默认不可达。U3 接入两小时脚本时不得暴露 legacy gate 到前端或 Agent。

## 6. Phase U3 工作范围

U3 目标：把 U1-U2 串入既有两小时自动脚本或新的 readonly orchestrator entrypoint，并让后端/API/前端读取最新 readonly daily result，最后输出运维手册和最终收口报告。

推荐实现：

```text
新增 scripts/run_tw_modular_daily_readonly_update.py
既有 scripts/run_daily_tw_stock_auto_update.py 调用该 readonly entrypoint
legacy provider publish gate 继续默认关闭
```

备选实现：

```text
在 scripts/run_daily_tw_stock_auto_update.py 内添加 modular readonly subcommand/path
默认仍不得触发 legacy provider publish / accepted latest
```

后端只允许新增或暴露 GET：

```text
GET /api/tw-stock/readonly-daily-latest
GET /api/tw-stock/readonly-daily-run-registry
```

前端展示字段建议：

```text
data_asof
run_asof
model_id
strategy_rule
new_data_detected
latest_status
candidate observations
audit status
error reason, if failed/noop
readonly_only / not_order / not_investment_advice
```

## 7. U3 必须验收的运行时场景

U3 至少覆盖：

```text
success
no_new_data
validator_failed
module_failed
```

每类场景必须证明：

```text
RunRegistry 可追溯
readonly latest pointer 行为正确
failure/noop 保留 previous latest
provider accepted latest 未变
qlib accepted latest 未变
monitor/broker/order 未触发
Agent prompt/tool/action 未改
```

自动链路必须输出 dry-run / shadow-run 证据：

```text
U1 validators 全部 ok=true
U2 validators 全部 ok=true
orchestrator status ok=true
legacy provider publish gate default disabled
readonly latest pointer != provider accepted latest
readonly latest pointer != qlib accepted latest
```

## 8. U3 Frontend / API GET-only 硬门

U3 必须做运行时 network audit。通过条件：

```text
readonly_workflow_only_get=true
forbidden_request_count=0
forbidden_requests=[]
suspicious_requests=[]
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
broker_quick_trade_orders_request_count=0
replay_strategy_write_count=0
failed_response_count=0
```

对于 full readonly E2E：

```text
ops_dry_run_post_count=0
```

说明：本地脚本 smoke 可以显式运行 dry-run 命令，但前端完整 readonly workflow 不得通过 POST 触发 ops dry-run。

## 9. U3 禁止事项

U3 不得做以下事项：

```text
不得训练新模型
不得调参或替换冻结模型权重
不得触发 provider refresh / publish
不得切 provider accepted latest 或 qlib accepted latest
不得写 monitor config / scan / alerts
不得连接 broker / quick-trade / orders
不得修改 Agent prompt / tool / action
不得让前端本地计算策略或 replay
不得把 OrderIntent 展示为交易建议、买入指令、目标仓位或自动下单
不得暴露 legacy provider publish gate 到前端或 Agent
```

## 10. U3 必须输出

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEU3_AUTOMATION_FRONTEND_FINAL_ACCEPTANCE_EXECUTION_REPORT_CN.md
```

最终收口文档：

```text
docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_FINAL_ACCEPTANCE_CN.md
docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_RUNBOOK_CN.md
docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_REVIEWER_CHECKLIST_CN.md
```

建议新增或更新的自动化/验收脚本：

```text
scripts/run_tw_modular_daily_readonly_update.py
scripts/validate_tw_modular_daily_readonly_update.py
scripts/validate_tw_daily_frontend_readonly_u3.py
```

## 11. U3 审查建议

U3 执行报告提交后，审查者应重点检查：

1. 两小时自动脚本默认路径是否只调用 readonly chain，legacy provider publish gate 是否仍默认关闭。
2. 后端新增路由是否只允许 GET，且只读 loader 是否校验 pointer 安全标志。
3. 前端是否只展示 readonly daily latest，不本地计算策略或 replay。
4. Playwright/network audit 是否证明 full readonly workflow 没有 POST ops dry-run、monitor、broker/order、provider/latest。
5. U3 是否输出最终 runbook、reviewer checklist 和 final acceptance。
6. Agent 是否未扩权，未新增 prompt/tool/action 或交易语义。

U3 通过后，才可以判定真实模块化日更 readonly productization 主线收口。
