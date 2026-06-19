# Phase M3 Daily Orchestrator 与 Latest Pointer Boundary 执行报告

生成日期：2026-06-17

## 1. 执行结论

Phase M3 已完成 daily orchestrator / run registry / auto update 的只读 dry-run 合同样例、validator、统一回归接入和既有两小时自动更新脚本审计。

本阶段没有训练新模型、没有新增正式策略、没有运行新收益结论、没有切默认策略、没有触发 provider publish / refresh、没有切 accepted latest、没有改 monitor / broker / quick-trade / order，也没有修改前端 Agent 行为、prompt、tool 权限或 action 入口。

重要边界已由 M3R 修复：`scripts/run_daily_tw_stock_auto_update.py` 仍保留既有生产 provider refresh / publish 与 accepted latest 代码，但默认 M3 contract mode 不可达；只有显式传入非默认 `--enable-legacy-provider-publish` gate，或显式设置 `TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH=true`，才会进入 legacy 分支。

## 2. 新增产物

### 2.1 Dry-run golden samples

样例根目录：

```text
data_tw/golden_samples/modular_contracts/m3/
```

覆盖 16 个样例：

```text
daily_orchestrator: 7
run_registry: 3
auto_update: 6
```

关键状态覆盖：

```text
no_new_data_noop_preserves_previous_latest
fresh_data_success_validators_passed_updates_readonly_latest
validator_failed_preserves_previous_latest
module_failed_preserves_previous_latest
forbidden_provider_publish_rejected
forbidden_accepted_latest_switch_rejected
forbidden_monitor_broker_order_rejected
success_records_previous_proposed_committed_checksum
```

### 2.2 Validator 与回归接入

新增 validator：

```text
scripts/validate_tw_daily_orchestrator_m3.py
```

统一回归已接入：

```text
scripts/run_tw_modular_contract_regression.py
```

新增输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/m3_daily_orchestrator_validation.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/m3_daily_script_audit.json
```

新增测试：

```text
tests/unit/test_tw_modular_m3_daily_orchestrator.py
```

## 3. Latest Pointer 状态机结果

| 场景 | previous_latest | proposed_latest | committed_latest | 结果 |
| --- | --- | --- | --- | --- |
| no_new_data | readonly_latest_20260616 | readonly_latest_20260616 | readonly_latest_20260616 | 保留 previous latest |
| fresh_data_success validators passed | readonly_latest_20260616 | readonly_latest_20260617 | readonly_latest_20260617 | 仅 validators 全部通过后提交 readonly latest |
| validator_failed | readonly_latest_20260616 | readonly_latest_20260617 | readonly_latest_20260616 | 保留 previous latest |
| module_failed | readonly_latest_20260616 | readonly_latest_20260617 | readonly_latest_20260616 | 保留 previous latest |
| run_registry success | readonly_latest_20260616 | readonly_latest_20260617 | readonly_latest_20260617 | 记录 run_id / previous / proposed / committed / checksum |

统一策略：

```text
readonly_after_all_validators_pass_keep_previous_on_failure
```

## 4. 两小时脚本审计结果

审计对象：

```text
scripts/run_daily_tw_stock_auto_update.py
```

审计命令：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

审计结论：

```text
ok=true
status=passed
has_wait_noop=true
has_already_up_to_date_noop=true
has_pending_retry=true
has_readonly_snapshot_dry_run_default=true
readonly_latest_pointer_distinct=true
broker_order_patterns_present=[]
monitor_write_patterns_present=[]
```

记录的 warning：

```text
legacy_provider_publish_path_present
legacy_accepted_latest_path_present
```

解释：这两个 warning 表示 legacy 生产脚本仍包含 provider refresh / publish 和 accepted latest 切换代码。M3R 后，warning 只有在 validator 同时证明 legacy gate 存在、默认关闭、并包住 legacy block，且 `default_provider_refresh_reachable=false`、`default_provider_publish_reachable=false`、`default_accepted_latest_reachable=false` 时才允许通过。

## 5. 禁止事项确认

M3 validator 和脚本审计确认：

```text
dry-run 样例禁止 provider_publish / provider_refresh
dry-run 样例禁止 accepted_latest_switch / qlib_accepted_latest_switch
dry-run 样例禁止 monitor_write / monitor_scan
dry-run 样例禁止 broker_order / quick_trade / order_action
dry-run 样例禁止 default_strategy_switch
dry-run 样例禁止 agent_tool / prompt / action expansion
既有脚本静态审计未发现 broker/order runtime pattern
既有脚本静态审计未发现 monitor write runtime pattern
```

负例样例会因 `forbidden_action` 失败，证明 validator 对禁止动作实际生效。

## 6. 验证命令

本阶段验证命令：

```bash
python -m py_compile scripts/validate_tw_daily_orchestrator_m3.py scripts/run_tw_modular_contract_regression.py tests/unit/test_tw_modular_m3_daily_orchestrator.py
python scripts/validate_tw_daily_orchestrator_m3.py --run-golden --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python -m pytest tests/unit/test_tw_modular_m_contract_validators.py tests/unit/test_tw_modular_m2_registry_validator.py tests/unit/test_tw_modular_m3_daily_orchestrator.py -q
```

预期结果：

```text
py_compile: pass
M3 golden validator: ok=true, sample_count=16
M3 script audit: ok=true, warnings=legacy_provider_publish_path_present|legacy_accepted_latest_path_present, default provider/latest reachable=false
pytest: pass
```

## 7. 未覆盖项与后续风险

M3 只建立 readonly dry-run contract 与审计边界，不做生产迁移。后续 M4/M5 前仍需处理：

```text
legacy provider publish 路径是否进一步拆出独立生产 entrypoint
legacy accepted latest 切换是否进一步独立冻结和审计
真实日更运行 registry 是否从 dry-run fixture 升级为不可变产物目录
readonly latest pointer 是否需要独立 manifest/index 与前端读取边界联动
```

在这些风险关闭前，不得把 M3 dry-run 结论解释为生产发布放行。
