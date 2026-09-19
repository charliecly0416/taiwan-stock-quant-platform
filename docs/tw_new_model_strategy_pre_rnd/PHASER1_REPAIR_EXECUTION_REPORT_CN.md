# Phase R1 Repair 执行报告

生成日期：2026-06-20

## 1. 结论

Phase R1 Repair 已按审查意见修复三项授权缺口：

```text
simple-chat 推荐问题静态断言漂移
M2 EXECUTION_REPORT_TEMPLATE_CN.md 缺失
M4 readonly primary fields 缺少 合法窗口 / 手续费/税费 / 审计状态
```

三项对应单项检查均已通过：

```text
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs 通过
python scripts/validate_tw_modular_registry_m2.py --json 通过
python scripts/validate_tw_frontend_readonly_m4.py --json 通过
```

同时重跑：

```text
cd frontend && corepack pnpm build 通过
node frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs 通过
```

但 `python scripts/run_tw_modular_contract_regression.py --json` 仍返回退出码 2、`ok=false`。当前失败原因已不再是本次 repair 授权的 M2/M4 缺口，而是 broader regression 中既有/额外条件：

```text
registry_validation.registry_dependency_paths failed
manifest_coverage_audit 中 R2/R5 historical report/handoff 文档缺失
forbidden_scope_audit 中现有 tracked diff marker audit failed
```

执行侧结论：本次授权 repair 的三项缺口已修复；R1 repair 不能判定完全通过，因为 full modular contract regression 仍失败。建议审查者决定是否另开 R1R2 repair 或将 broader regression 额外失败项列为独立历史缺口。

## 2. 修改文件

本次修改文件：

```text
frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
docs/tw_modular_contracts/templates/EXECUTION_REPORT_TEMPLATE_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER1_REPAIR_EXECUTION_REPORT_CN.md
```

未修改：

```text
模型训练代码
策略规则代码
默认模型配置
默认策略配置
provider publish / accepted latest 逻辑
monitor 写入逻辑
broker / quick-trade / order 逻辑
OpenAI key / OpenAI 调用逻辑
```

## 3. simple-chat static check 修复

目标文件：

```text
frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

修复内容：

- 移除旧断言：`明天关注哪些股票？`。
- 移除旧断言：`今天有哪些调入调出观察？`。
- 对齐当前更安全的研究型推荐问题：

```text
今天策略是什么？
排名第一是谁？
今天有哪些候选调入？
今天有哪些调出复核？
2330 当前状态如何？
为什么模拟账户不能应用？
数据新鲜度如何？
```

保留负向断言：

```text
OPENAI_API_KEY
api.openai.com
chat/completions
@openai
quick-trade
broker
target_position
target_weight
provider publish
accepted latest
monitor scan
monitor alerts
下单
仓位
收益保证
自动交易
目标仓位
```

验证：

```bash
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

结果：

```text
退出码：0
tw-stock-agent-simple-chat-check passed
```

## 4. M2 EXECUTION_REPORT_TEMPLATE 修复

新增文件：

```text
docs/tw_modular_contracts/templates/EXECUTION_REPORT_TEMPLATE_CN.md
```

模板包含要求 marker：

```text
contract_doc
schema_version
input_artifacts
output_artifacts
validator_command
golden_sample_path
allowed_consumers
forbidden_consumers
readonly_boundary
forbidden_actions_audit
production_allowed: false
```

同时包含建议 marker：

```text
diagnostic_only
rollback_or_failure_policy
not_default_model_or_strategy
no_provider_publish
no_accepted_latest_switch
no_monitor_write
no_broker_or_order
```

验证：

```bash
python scripts/validate_tw_modular_registry_m2.py --json
```

结果：

```text
退出码：0
ok=true
status=passed
errors=[]
warnings=[]
EXECUTION_REPORT_TEMPLATE_CN.md exists=true, missing_markers=[]
```

## 5. M4 readonly primary fields 修复

目标文件：

```text
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
```

修复内容：

- 在 `ReadonlyReplayWindowPanel.vue` primary 区明确显示：

```text
合法窗口
手续费/税费
审计状态
```

- 在 `ReadonlyStrategySnapshotPanel.vue` primary 区明确显示：

```text
审计状态
覆盖状态
```

- 新增 `auditStatusText` / `auditStatusDetail` 仅从现有只读 payload、checksum、schema_version 派生，不新增任何 API 请求或写操作。
- 技术详情仍通过 `ReplayAuditDetail` 折叠展示。

验证：

```bash
python scripts/validate_tw_frontend_readonly_m4.py --json
```

结果：

```text
退出码：0
ok=true
status=passed
errors=[]
forbidden_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
broker_quick_trade_orders_request_count=0
```

## 6. 重跑命令结果

### 6.1 simple-chat static check

```bash
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

结果：

```text
退出码：0
tw-stock-agent-simple-chat-check passed
```

### 6.2 M2 registry validator

```bash
python scripts/validate_tw_modular_registry_m2.py --json
```

结果：

```text
退出码：0
ok=true
status=passed
```

### 6.3 M4 frontend readonly validator

```bash
python scripts/validate_tw_frontend_readonly_m4.py --json
```

结果：

```text
退出码：0
ok=true
status=passed
```

### 6.4 frontend build

```bash
cd frontend && corepack pnpm build
```

结果：

```text
退出码：0
vite build 通过
```

备注：仍出现 shell 初始化提示 `/bin/sh: 2: source: not found`，但未导致 build 失败。

### 6.5 UI2 readonly Playwright / fixture

```bash
node frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
```

结果：

```text
退出码：0
required_text_passed=true
forbidden_visible_passed=true
overflow_passed=true
button_overflow_passed=true
technical_details_default_collapsed=true
forbidden_request_count=0
console_error_count=0
page_error_count=0
```

证据目录：

```text
/home/chuliyang/tmp/tw_ui2d_workbench_acceptance
```

### 6.6 Modular contract regression

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
退出码：2
ok=false
```

已修复并通过的子项：

```text
m2_registry_status=passed
m4_frontend_readonly_status=passed
m4_forbidden_request_count=0
m5_onboarding_smoke_status=passed
m3_daily_script_audit_status=passed
m1_contract_status=passed
```

剩余失败原因：

1. `registry_validation.json`：

```text
registry_dependency_paths failed
production_selectable:None,research_only:None,deprecated:None
```

初步判断：`validate_tw_modular_artifact_contract.validate_registry()` 按旧的 flat `strategies` 结构读取 `dependency_path`，而当前 `configs/tw_modular_registry.yaml` 的 `strategies` 为嵌套结构 `production_selectable / research_only / deprecated`。这不是 R1 repair 文档授权的三项缺口之一。

2. `manifest_coverage_audit.csv`：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md missing
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md missing
```

初步判断：这是历史 R2/R5 replay 文档覆盖缺口，不属于本次 R1 repair 授权范围。

3. `forbidden_scope_audit.csv`：

```text
frontend/src/views/tw-stock-monitor/index.vue r15_readonly_frontend_content_audit failed
scripts/run_daily_tw_stock_auto_update.py r16_daily_readonly_content_audit failed
```

初步判断：该审计基于 tracked diff marker 检查。相关文件是 R0 之前已有 modified 地基文件，不属于本次三项 repair 直接修改对象。R1 repair 未授权通过添加 marker、改 validator 或补历史测试文件来规避该 broader audit。

## 7. Forbidden actions audit

本次 repair 未执行或触发：

```text
训练新模型
新增策略规则
修改默认模型或默认策略
修改前端默认展示为新模型/新策略
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target_position / target_weight 写入
OpenAI key 读取
真实 OpenAI smoke
```

验证证据：

```text
validate_tw_frontend_readonly_m4.py: forbidden_request_count=0
validate_tw_frontend_readonly_m4.py: provider/latest/monitor/broker request counts all 0
UI2 readonly e2e: forbidden_request_count=0
UI2 readonly e2e: monitor_config_write_count=0, monitor_scan_post_count=0, monitor_alerts_write_count=0
```

## 8. 是否建议重新审查 R1

执行侧建议：重新审查 R1 repair，但不能直接声明 full R1 pass。

建议审查重点：

```text
1. 确认 R1 repair 文档授权的三项缺口是否已修复。
2. 判断 run_tw_modular_contract_regression.py 仍失败的 broader regression 条件是否属于本次 repair 范围。
3. 如要求 full modular regression 必须退出码 0，则需要另开 R1R2 repair，授权处理 registry validate nested strategies、历史 R2/R5 文档覆盖、tracked diff marker audit 等额外问题。
4. 如审查者认为本次 repair 只需关闭三项阻塞缺口，则可有条件放行进入 R2，但需保留 full regression 的额外历史缺口记录。
```
