# Phase R1 Repair 审查报告

审查日期：2026-06-20

审查对象：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER1_REPAIR_WORK_CN.md
frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
docs/tw_modular_contracts/templates/EXECUTION_REPORT_TEMPLATE_CN.md
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/regression_summary.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/registry_validation.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/manifest_coverage_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv
```

## 1. 审查结论

结论：R1 Repair 部分通过，但 R1 仍不通过。

执行者已修复 R1 Repair 工作文档授权的三项缺口：

```text
simple-chat 推荐问题静态断言漂移
M2 EXECUTION_REPORT_TEMPLATE_CN.md 缺失
M4 readonly primary fields 缺少 合法窗口 / 手续费/税费 / 审计状态
```

对应单项检查已通过：

```text
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
python scripts/validate_tw_modular_registry_m2.py --json
python scripts/validate_tw_frontend_readonly_m4.py --json
cd frontend && corepack pnpm build
node frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
```

但 `python scripts/run_tw_modular_contract_regression.py --json` 仍返回：

```text
ok=false
退出码=2
```

因此不能判定 R1 repair fully passed，也不能进入 R2/R3 或新模型/新策略研发。

允许进入：

```text
Phase R1R2 Repair：只修复 full modular contract regression 剩余三类 broader 缺口。
```

## 2. 已修复项确认

### 2.1 simple-chat static check

当前测试已对齐安全的研究型推荐问题：

```text
今天策略是什么？
排名第一是谁？
今天有哪些候选调入？
今天有哪些调出复核？
2330 当前状态如何？
为什么模拟账户不能应用？
数据新鲜度如何？
```

旧断言 “明天关注哪些股票？” 已移除。负向断言仍覆盖：

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

审查通过。

### 2.2 M2 execution report template

新增：

```text
docs/tw_modular_contracts/templates/EXECUTION_REPORT_TEMPLATE_CN.md
```

模板包含 validator 要求的 marker：

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

`m2_registry_validation.json` 已显示：

```text
ok=true
status=passed
missing_markers=[]
```

审查通过。

### 2.3 M4 readonly primary fields

前端 readonly primary 区已出现：

```text
合法窗口
手续费/税费
审计状态
```

`m4_frontend_readonly_validation.json` 已显示：

```text
ok=true
status=passed
forbidden_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
broker_quick_trade_orders_request_count=0
```

审查通过。

## 3. 剩余阻塞项

### 3.1 Registry validation 不兼容 nested strategies

`registry_validation.json` 当前失败：

```text
registry_dependency_paths failed
production_selectable:None,research_only:None,deprecated:None
```

原因：

```text
configs/tw_modular_registry.yaml 的 strategies 已是嵌套结构：
strategies.production_selectable
strategies.research_only
strategies.deprecated

validate_tw_modular_artifact_contract.validate_registry()
和 run_tw_modular_contract_regression.dependency_paths_from_registry()
仍按旧 flat strategies 结构读取 dependency_path。
```

这是 validator / regression 对当前 registry 结构的适配缺口，不是新模型/新策略研发。

### 3.2 Manifest coverage 指向未归档路径

`manifest_coverage_audit.csv` 当前失败：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md
```

只读搜索确认对应历史文档存在于 archive：

```text
docs/archive/phase_history/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md
docs/archive/phase_history/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md
```

这是历史文档归档路径与 regression 期望路径不一致，不应通过创建空文件伪造。

### 3.3 Forbidden scope audit 仍按 tracked diff marker 判定

`forbidden_scope_audit.csv` 当前失败：

```text
frontend/src/views/tw-stock-monitor/index.vue r15_readonly_frontend_content_audit failed
scripts/run_daily_tw_stock_auto_update.py r16_daily_readonly_content_audit failed
```

现有审计逻辑基于：

```text
git diff --unified=0 HEAD -- <path>
```

即只检查 tracked diff 里新增的 marker，而不是完整文件内容或本轮已通过的专用 validators。当前这些文件属于 R0 之前已有 modified 地基文件，diff 未必包含旧 marker，因此 broader audit 仍失败。

这需要单独修复审计逻辑或补充一个明确的 readonly authorization evidence 机制，不能删除 forbidden scope audit。

## 4. 安全边界结论

当前剩余失败不是安全越界。已抽查：

```text
M4 forbidden_request_count=0
UI2 readonly forbidden_request_count=0
未触发真实数据拉取
未触发 provider refresh / publish
未切 accepted latest
未写 monitor config / scan / alerts
未触发 broker / quick-trade / order
未读取 OpenAI key
未触发真实 OpenAI smoke
```

但 full modular contract regression 仍未通过，所以 R1 不能关闭。

## 5. 审查判定

R1 Repair 判定：

```text
PARTIAL_PASS_REMAINING_REGRESSION_BLOCKERS
```

不得进入：

```text
R2
R3
新模型研发
新策略研发
```

允许进入：

```text
R1R2 Repair
```

## 6. 给执行者的下一步

按：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1R2_REMAINING_REGRESSION_REPAIR_WORK_CN.md
```

执行剩余 regression repair。

完成后输出：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1R2_REMAINING_REGRESSION_REPAIR_EXECUTION_REPORT_CN.md
```

R1R2 的目标是让：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

返回 `ok=true`，同时不放松任何只读/安全边界。
