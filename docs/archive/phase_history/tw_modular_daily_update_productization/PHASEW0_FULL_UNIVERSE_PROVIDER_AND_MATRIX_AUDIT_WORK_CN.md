# Phase W0 全量真实覆盖与模型策略矩阵审计工作文档

生成日期：2026-06-17

## 1. 审查者独立判断

统筹给出的后续意见中，真正需要做的是“全量真实覆盖证明”和“模型/策略矩阵可运行性审计”。

这不是推翻 Phase V 收口。Phase V 已经证明了真实 provider、DataReadinessGate、U 链、readonly latest、前端按钮状态的产品闭环。但 V5 的 provider staging readiness artifact 是 5 支样本：

```text
symbols_requested=5
symbols=TW1301,TW1303,TW1326,TW1519,TW1560
```

同时，现役 daily auto update 已经在 2026-06-17 跑通过 150 支完整 qlib 链路：

```text
status=daily_auto_update_passed
asof=2026-06-17
symbols_expected=150
symbols_success=150
rows_written=399452
provider_validation.active_universe_count=150
provider_validation.calendar_max=2026-06-17
model_smoke.symbols=150
model_smoke.prediction_rows=150
latest_signal_updated=true
```

因此当前问题不是“系统没有 150 支链路”，而是“V5 modular provider readiness 没有把 150 支全量覆盖证据纳入同一套 readiness / matrix / frontend 审计产物”。W0 的任务就是补这层证据，不重新打开 V 路线。

## 2. 哪些建议需要做

### 2.1 必须做：全量 universe coverage audit

执行者必须补一份 150 支正式 universe 的只读审计产物，证明：
- Yahoo/Scrapling qlib provider 当前覆盖 150 支。
- FinMind daily raw 当前覆盖正式 universe 所需股票。
- orthogonal / model_signals 依赖的日期与 `target_asof` 一致或有明确 unavailable reason。
- symbol mapping、calendar、instrument 有效期、缺失字段、fallback 使用都被机器可读记录。

注意：这一步可以读取现有 daily auto update 产物和本地 provider，不要求重新拉外网；如果确需真实拉取，必须另行显式授权，且只能 staging-only，不得 publish。

### 2.2 必须做：模型 / 策略矩阵审计

执行者必须补一份矩阵审计产物，覆盖当前已冻结的模型和策略组合。最低要求：
- 每个模型是否可用。
- 每个策略是否可用。
- 不可用原因必须短、准、可展示。
- 默认组合可运行时，不代表其他组合自动可运行。
- 前端不得静默降级到默认组合。

这一步只做 readonly audit / dry-run query，不训练、不调参、不切默认。

### 2.3 应该做：前端状态解释收敛

前端已经达到 V5R 的用户态要求，但 W0 后应补充矩阵状态展示：
- 默认显示今日最关键结果。
- 模型/策略不可用时显示短原因。
- 不把 5 支 staging 样本说成 150 支全量 ready。
- 不把 fallback 当成事实主来源，而是明确“fallback used”。

## 3. 哪些建议暂不做

以下不应进入 W0：
- 训练新模型。
- 新增正式策略。
- 切换默认模型或默认策略。
- provider publish。
- accepted latest 手工切换。
- monitor config / scan / alerts 写入。
- broker / quick-trade / orders。
- Agent 扩权。

如果后续要做新模型或新策略，应进入新模型/新策略主线，不混入 W0。

## 4. W0 执行范围

### 4.1 输入

执行者应读取：

```text
docs/tw_modular_daily_update_productization/PHASEV_FOLLOWUP_NEXT_STEPS_CN.md
docs/tw_modular_daily_update_productization/PHASEV_ROUTE_SUMMARY_FOR_COORDINATION_REVIEW_CN.md
docs/tw_modular_daily_update_productization/PHASEV5R_FRONTEND_USER_STATE_AND_E2E_REPAIR_EXECUTION_REPORT_CN.md
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260617_20260617T103001Z/job.json
data_tw/artifacts/real_provider_daily_update_runs/phasev5_external_provider_all_ready_codex_v2/run_registry.json
data_tw/artifacts/provider_staging/phasev5_external_provider_all_ready_codex_v2_provider_staging/**
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
```

### 4.2 输出

必须新增以下产物：

```text
data_tw/artifacts/full_universe_provider_audit/w0_*/full_universe_provider_audit.json
data_tw/artifacts/full_universe_provider_audit/w0_*/model_strategy_matrix_audit.json
data_tw/artifacts/full_universe_provider_audit/w0_*/frontend_state_contract.json
docs/tw_modular_daily_update_productization/PHASEW0_FULL_UNIVERSE_PROVIDER_AND_MATRIX_AUDIT_EXECUTION_REPORT_CN.md
```

### 4.3 建议脚本

可新增只读脚本：

```text
scripts/audit_tw_full_universe_provider_coverage_w0.py
scripts/audit_tw_model_strategy_matrix_w0.py
scripts/validate_tw_full_universe_provider_audit_w0.py
```

脚本要求：
- 默认只读。
- 不访问 broker/order/monitor 写接口。
- 不触发 provider publish / accepted latest。
- 不训练、不调参。
- 如需网络访问，必须显式参数 `--allow-network`，默认关闭。

## 5. 验收门槛

W0 通过必须同时满足：

```text
full_universe_size >= 150
qlib_provider_calendar_max >= target_asof
qlib_provider_active_universe_count >= 150
model_signal_prediction_rows >= 150
latest_signal_asof == target_asof
forbidden_action_audit.provider_publish_triggered == false
forbidden_action_audit.accepted_latest_switched == false
forbidden_action_audit.orders_created_or_sent == false
```

模型/策略矩阵必须满足：

```text
每个已冻结模型/策略组合都有 status
status 只能是 ready / unavailable / unsupported
unavailable 必须有 user_reason
默认组合 ready 不得替代其他组合状态
```

前端契约必须满足：

```text
已最新显示已是最新
可更新显示可更新
检查中显示检查中
不可用显示短原因
不得显示数据就绪状态 -
不得把 sample coverage 写成 full coverage
```

## 6. 给执行者的执行顺序

1. 先从现有 2026-06-17 daily auto update job 提取 150 支全量证据。
2. 再对照 V5 provider staging 5 支样本，明确 sample 与 full universe 的差异。
3. 生成 full universe provider audit。
4. 生成 model/strategy matrix audit。
5. 补前端状态契约或最小 UI 展示修正。
6. 写执行报告。

## 7. 给审查者的重点

审查者应重点阻断以下情况：
- 用 5 支 sample 冒充 150 支 full universe。
- 用 daily auto update 成功冒充所有模型/策略组合都 ready。
- 某个模型/策略 unavailable 但前端静默降级。
- fallback used 但前端不解释。
- 任何 provider publish / accepted latest / broker / order 越界。

## 8. 收口口径

W0 通过后，可以把结论升级为：

```text
V 路线已收口；W0 已补齐正式 universe 覆盖与模型/策略矩阵审计证据。
```

W0 不通过时，不影响 V5 作为产品闭环基线，但不能宣称“modular provider readiness 已经完成 150 支全量覆盖验收”。
