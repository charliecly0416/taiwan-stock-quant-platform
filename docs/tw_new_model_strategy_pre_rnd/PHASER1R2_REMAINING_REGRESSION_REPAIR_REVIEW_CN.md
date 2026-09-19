# Phase R1R2 审查报告：剩余 modular regression repair

审查日期：2026-06-20

审查对象：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1R2_REMAINING_REGRESSION_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER1R2_REMAINING_REGRESSION_REPAIR_WORK_CN.md
scripts/validate_tw_modular_artifact_contract.py
scripts/run_tw_modular_contract_regression.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/regression_summary.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/registry_validation.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/manifest_coverage_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv
```

## 1. 审查结论

结论：通过。

Phase R1R2 已关闭 R1 repair 后剩余的 full modular contract regression 阻塞项。当前 `python scripts/run_tw_modular_contract_regression.py --json` 已返回：

```text
ok=true
退出码=0
```

R1 可以判定为通过，但这只表示 pre-RND 地基只读回归通过，不代表可以直接进入新模型/新策略研发。

允许进入：

```text
Phase R2：Skills 与运行时入口确认
```

仍不允许进入：

```text
新模型训练
新策略实现
默认模型/默认策略切换
provider publish / accepted latest switch
monitor / broker / order / OpenAI smoke
```

## 2. 通过依据

### 2.1 Full modular regression 通过

抽查：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/regression_summary.json
```

关键结果：

```text
ok=true
strategy_dependency_count=5
signal_validation_rows=30
m1_contract_status=passed
m2_registry_status=passed
m3_daily_orchestrator_status=passed
m3_daily_script_audit_status=passed
m4_frontend_readonly_status=passed
m5_onboarding_smoke_status=passed
m4_forbidden_request_count=0
```

`m3_daily_script_audit_warning_codes` 仍包含：

```text
legacy_provider_publish_path_present
legacy_accepted_latest_path_present
```

但这是 gated legacy path 的非阻塞 warning，R1/R1R2 已确认默认不可达。

### 2.2 Nested strategies registry 修复有效

`registry_validation.json` 显示：

```text
ok=true
registry_dependency_paths=pass
registry_dependency_skipped_aliases=pass
registry_contract_docs=pass
```

脚本 diff 显示新增 `iter_strategy_registry_entries()`，支持：

```text
flat strategies
nested strategies.production_selectable
nested strategies.research_only
nested strategies.deprecated
```

并对 deprecated alias `origin` 这种有 `reason` 但无 `dependency_path` 的条目进行显式 skipped 记录，而不是默默忽略或失败。

审查通过。

### 2.3 Manifest coverage archive fallback 修复有效

`manifest_coverage_audit.csv` 已新增：

```text
actual_path
archive_fallback
```

旧 manifest 中的两个历史路径通过 archive fallback 找到真实文件：

```text
docs/archive/phase_history/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md
docs/archive/phase_history/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md
```

未创建空历史报告，未修改 replay 输出、模型、策略或收益结果。

审查通过。

### 2.4 Forbidden scope audit 修复有效

`forbidden_scope_audit.csv` 显示所有 scope 均为 pass。

R15 前端只读审计：

```text
status=pass
authorized_readonly_frontend_diff=True
required_missing=
forbidden_matches=
static_check_exists=True
e2e_check_exists=True
m4_validator_exists=True
ui2_e2e_exists=True
```

R16 daily readonly 审计：

```text
status=pass
required_missing=
forbidden_matches=
m3_validator_exists=True
prompt_builder_test_exists=True
prompt_orchestration_test_exists=True
prompt_validator_test_exists=True
```

脚本仍保留：

```text
FORBIDDEN_SCOPE_PATHS
forbidden pattern scan
diff added-lines forbidden scan
```

没有删除审计，也没有把 status 无条件改为 pass。

审查通过。

## 3. 安全边界审查

本次 repair 未发现以下动作：

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

M4 与 UI2 readonly 证据继续显示：

```text
forbidden_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
broker_quick_trade_orders_request_count=0
```

## 4. 审查判定

R1R2 判定：

```text
PASS
```

R1 总体判定：

```text
PASS_AFTER_REPAIR
```

允许进入：

```text
Phase R2：Skills 与运行时入口确认
```

## 5. 给执行者的下一步

按：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER2_SKILL_RUNTIME_ENTRY_WORK_CN.md
```

执行 R2。

R2 只确认 project-local skills、用户级 active 路径、archive 风险和运行时入口，不做模型/策略研发，不触发真实数据或交易链路。
