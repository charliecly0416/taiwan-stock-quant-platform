# Phase R1 审查报告：只读集成回归

审查日期：2026-06-20

审查对象：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_EXECUTION_REPORT_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_WORK_CN.md
frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
scripts/run_tw_modular_contract_regression.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/m2_registry_validation.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/m4_frontend_readonly_validation.json
/home/chuliyang/tmp/tw_ui2d_workbench_acceptance/audit.json
/home/chuliyang/tmp/tw_ui2d_workbench_acceptance/network_audit.json
```

## 1. 审查结论

结论：R1 不通过，需要 repair 后重跑失败项。

R1 执行报告可信：执行者没有掩盖失败项，也没有把静态/合同失败包装成通过。当前失败项不属于真实交易或真实数据安全越界，但仍是 readiness freeze 的阻塞项。

当前不允许进入：

```text
R2 Skills 与运行时入口确认
R3 Artifact 链路入口确认
新模型研发
新策略研发
```

允许进入：

```text
Phase R1 Repair：只修复本报告列出的静态断言、模板缺口和 readonly primary field 缺口。
```

## 2. 通过项确认

根据执行报告与抽查结果，以下项目通过：

```text
Python py_compile：通过
Agent daily prompt / simple-chat backend pytest：37 passed
frontend build：通过
UI2 readonly Playwright / fixture：通过
daily orchestrator readonly validator：通过
```

UI2 readonly evidence 抽查：

```text
forbidden_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_dry_run_post_count=0
failed_response_count=0
desktop/tablet/mobile overflowX=false
technical_details_default_collapsed=true
```

Daily orchestrator validator 报告：

```text
legacy_provider_gate_default_disabled=true
provider_refresh_guarded=true
provider_publish_guarded=true
accepted_latest_call_guarded=true
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
```

这些通过项说明当前失败不是 forbidden request 或真实链路被触发。

## 3. 阻塞失败项

### 3.1 Frontend simple-chat static check 失败

失败命令：

```bash
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

失败原因：

```text
AssertionError: The input did not match /明天关注哪些股票？/
```

抽查现状：

当前 `frontend/src/views/tw-stock-monitor/index.vue` 的推荐问题是：

```text
今天策略是什么？
排名第一是谁？
今天有哪些候选调入？
今天有哪些调出复核？
2330 当前状态如何？
为什么模拟账户不能应用？
数据新鲜度如何？
```

测试仍要求：

```text
明天关注哪些股票？
今天有哪些调入调出观察？
```

审查判断：

这是静态测试与当前产品文案漂移，不是安全越界。并且“明天关注哪些股票？”比当前“候选调入/调出复核/当前状态”更容易被理解为预测或行动暗示，不建议为了测试恢复该旧文案。

Repair 应更新测试断言，使其对齐当前安全的研究型推荐问题，同时继续保留禁止交易、OpenAI、broker、target_position、target_weight、provider publish、accepted latest、monitor writes 的负向断言。

### 3.2 Modular contract regression：M2 registry/template 失败

失败命令：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

M2 失败文件：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/m2_registry_validation.json
```

确认失败原因：

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

抽查 validator 逻辑后确认：`scripts/validate_tw_modular_registry_m2.py` 明确要求 `EXECUTION_REPORT_TEMPLATE_CN.md` 存在，并包含上述 marker。

审查判断：

这是真实模板缺口，不应通过放宽 validator 解决。Repair 应新增通用执行报告模板，内容可参考现有 `REVIEW_REPORT_TEMPLATE_CN.md` 和各 onboarding 模板，但必须包含 validator 所需 marker。

### 3.3 Modular contract regression：M4 frontend readonly primary field 失败

M4 失败文件：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/m4_frontend_readonly_validation.json
```

确认失败原因：

```text
primary_field_missing: 合法窗口
primary_field_missing: 手续费/税费
primary_field_missing: 审计状态
```

抽查现状：

- `ReadonlyReplayWindowPanel.vue` 当前显示“测试窗口”，但 validator 要求 primary field “合法窗口”。
- `ReadonlyReplayWindowPanel.vue` 当前显示“费用/税费”，但 validator 要求 “手续费/税费”。
- `ReadonlyStrategySnapshotPanel.vue` / `ReadonlyReplayWindowPanel.vue` 当前有技术详情和校验信息，但 primary 区没有明确 “审计状态” 字段。

审查判断：

这是前端 readonly primary fields 与 M4 合同不一致。Repair 应优先补齐 UI primary field 文案或字段，而不是放宽 validator。可接受的最小修复是：

```text
在 ReadonlyReplayWindowPanel primary metrics 中明确出现“合法窗口”“手续费/税费”“审计状态”；
或在 Strategy Snapshot / Replay Window primary 区域中以清晰、用户可见、只读研究语义展示这些字段；
保持技术详情默认折叠；
不新增交易入口、不新增写 API、不修改默认模型/策略。
```

## 4. 安全边界审查

本次失败项不是安全越界。抽查证据显示：

```text
未触发真实数据拉取
未触发 provider refresh / publish
未切 accepted latest
未写 monitor config / scan / alerts
未触发 broker / quick-trade / order
未读取 OpenAI key
未触发真实 OpenAI smoke
UI2 network forbidden_request_count=0
M4 frontend readonly forbidden_request_count=0
```

但因为两个命令级失败仍存在，R1 不能通过。

## 5. 审查判定

R1 判定：

```text
FAIL_NEEDS_REPAIR
```

Repair 完成前不得进入 R2/R3，更不得进入新模型/新策略研发。

## 6. 给执行者的下一步

按：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1_REPAIR_WORK_CN.md
```

执行 R1 repair。Repair 后必须输出：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1_REPAIR_EXECUTION_REPORT_CN.md
```

并至少重跑：

```bash
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
python scripts/validate_tw_modular_registry_m2.py --json
python scripts/validate_tw_frontend_readonly_m4.py --json
python scripts/run_tw_modular_contract_regression.py --json
node frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
```

如修复触及 frontend，还应说明是否重跑 `cd frontend && corepack pnpm build`。
