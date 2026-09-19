# Phase R1R2 执行报告：剩余 modular regression repair

生成日期：2026-06-20

## 1. 结论

Phase R1R2 已按审查意见修复 full modular contract regression 剩余三类阻塞项：

```text
registry validation 不兼容 nested strategies
manifest coverage 指向未归档路径
forbidden scope audit 仍按 tracked diff marker 判断导致误阻塞
```

修复后核心结果：

```text
python scripts/run_tw_modular_contract_regression.py --json
退出码：0
ok=true
```

对应产物确认：

```text
registry_validation.json ok=true
manifest_coverage_audit.csv 无 fail
forbidden_scope_audit.csv 无 fail
m2_registry_status=passed
m4_frontend_readonly_status=passed
UI2 readonly Playwright passed
```

执行侧结论：R1R2 repair 已关闭本阶段授权的剩余 regression blockers，建议进入审查。是否允许进入 R2 仍应由审查者判定。

## 2. 修改文件

本次修改文件：

```text
scripts/validate_tw_modular_artifact_contract.py
scripts/run_tw_modular_contract_regression.py
docs/tw_new_model_strategy_pre_rnd/PHASER1R2_REMAINING_REGRESSION_REPAIR_EXECUTION_REPORT_CN.md
```

未修改：

```text
configs/tw_modular_registry.yaml
formal_replay_manifest.json
模型训练代码
策略规则代码
默认模型/默认策略配置
provider publish / accepted latest 逻辑
monitor 写入逻辑
broker / quick-trade / order 逻辑
OpenAI key / OpenAI 调用逻辑
```

## 3. Nested strategies registry 修复

目标文件：

```text
scripts/validate_tw_modular_artifact_contract.py
scripts/run_tw_modular_contract_regression.py
```

修复内容：

- 新增 `iter_strategy_registry_entries()`，兼容 flat strategies 与 nested strategies。
- nested 结构下遍历：

```text
production_selectable.*
research_only.*
deprecated.*
```

- 对有 `dependency_path` 的条目继续检查文件存在。
- 对没有 `dependency_path` 但有 `reason` 的 deprecated alias 显式记录为 skipped alias，不作为失败。
- full regression 输出 dependency key 使用完整路径，例如：

```text
production_selectable.top50_exit_one_worst_sell
research_only.one_sell_one_buy_correct
deprecated.original
```

- signal artifact regression 只纳入真实策略依赖，排除 template / smoke 依赖；但 manifest coverage 仍检查 template / smoke dependency 文件存在性。

验证：

```bash
python scripts/validate_tw_modular_artifact_contract.py --registry configs/tw_modular_registry.yaml --json
```

结果：

```text
退出码：0
ok=true
registry_dependency_paths=pass
registry_dependency_skipped_aliases=pass
skipped: deprecated.origin:reason=alias of original; not frontend/API selectable
```

## 4. Manifest coverage archive path 修复

目标文件：

```text
scripts/run_tw_modular_contract_regression.py
```

修复内容：

- 未创建空历史报告。
- 未修改 replay manifest、replay 输出、模型、策略或收益结果。
- 在 regression coverage audit 中增加 archive fallback：

```text
docs/<branch>/<file>
=> docs/archive/phase_history/<branch>/<file>
```

- `manifest_coverage_audit.csv` 增加：

```text
actual_path
archive_fallback
```

当前归档路径已识别并通过：

```text
report  -> docs/archive/phase_history/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md
handoff -> docs/archive/phase_history/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md
```

验证：

```bash
grep -n ",fail" data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/manifest_coverage_audit.csv
```

结果：

```text
退出码：1
无输出，表示未发现 fail 行
```

## 5. Forbidden scope audit 修复

目标文件：

```text
scripts/run_tw_modular_contract_regression.py
```

修复内容：

- 未删除 `FORBIDDEN_SCOPE_PATHS`。
- 未删除 R15/R16 forbidden pattern 检查。
- 未将 status 无条件改为 pass。
- R15/R16 required markers 改为检查完整文件内容，适配 R0 前已有 tracked diff。
- forbidden patterns 仍只扫描 added diff lines。
- R15 增强 evidence：

```text
frontend/tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs exists
frontend/tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs exists
scripts/validate_tw_frontend_readonly_m4.py exists
frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs exists
```

- R16 增强 evidence，使用当前实际 validator/test 路径，而不是创建空测试：

```text
scripts/validate_tw_daily_orchestrator_m3.py exists
backend/tests/test_tw_stock_agent_daily_prompt_builder.py exists
backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py exists
backend/tests/test_tw_stock_agent_daily_prompt_validator.py exists
```

验证：

```bash
grep -n ",fail" data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv
```

结果：

```text
退出码：1
无输出，表示未发现 fail 行
```

## 6. 重跑命令结果

### 6.1 Python compile

```bash
python -m py_compile scripts/run_tw_modular_contract_regression.py scripts/validate_tw_modular_artifact_contract.py
```

结果：

```text
退出码：0
```

### 6.2 Registry validator

```bash
python scripts/validate_tw_modular_artifact_contract.py --registry configs/tw_modular_registry.yaml --json
```

结果：

```text
退出码：0
ok=true
registry_dependency_paths=pass
registry_contract_docs=pass
```

### 6.3 Full modular contract regression

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
退出码：0
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

输出目录：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression
```

### 6.4 M2 registry validator

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
```

### 6.5 M4 frontend readonly validator

```bash
python scripts/validate_tw_frontend_readonly_m4.py --json
```

结果：

```text
退出码：0
ok=true
status=passed
forbidden_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
broker_quick_trade_orders_request_count=0
```

### 6.6 UI2 readonly Playwright / fixture

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

安全证据：

```text
full regression ok=true
M4 forbidden_request_count=0
UI2 readonly forbidden_request_count=0
manifest coverage 使用 archive fallback，未伪造历史报告
forbidden scope audit 仍保留 forbidden pattern 扫描
```

## 8. 是否建议重新审查 R1

建议重新审查 R1R2。

执行侧判断：本阶段授权的三类剩余 regression blockers 已修复，且 `run_tw_modular_contract_regression.py --json` 已返回 `ok=true`。若审查者确认本报告和产物可信，可判定 R1 关闭，并决定是否允许进入 R2。
