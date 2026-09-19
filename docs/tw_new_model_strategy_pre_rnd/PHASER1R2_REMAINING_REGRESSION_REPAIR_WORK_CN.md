# Phase R1R2 工作文档：修复 full modular contract regression 剩余阻塞项

生成日期：2026-06-20

## 1. 工作结论

Phase R1 Repair 已关闭三项授权缺口，但 full modular contract regression 仍失败。

本阶段只允许修复以下三类剩余 regression 阻塞项：

```text
registry validation 不兼容 nested strategies
manifest coverage 指向未归档路径
forbidden scope audit 仍按 tracked diff marker 判断导致误阻塞
```

本阶段仍不是新模型或新策略研发。

## 2. 严禁事项

不得执行或触发：

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

不得为了通过 regression 而：

```text
删除 forbidden scope audit
删除 manifest coverage audit
删除 registry dependency validation
伪造空历史报告
把 fail 强行改成 pass
放宽 provider/latest/monitor/broker/order/OpenAI 检查
```

## 3. Repair 1：支持 nested strategies registry

目标文件：

```text
scripts/validate_tw_modular_artifact_contract.py
scripts/run_tw_modular_contract_regression.py
```

问题：

```text
configs/tw_modular_registry.yaml 的 strategies 当前是嵌套结构：
strategies.production_selectable
strategies.research_only
strategies.deprecated

现有 validate_registry() 和 dependency_paths_from_registry() 仍按旧 flat strategies 读取，导致：
production_selectable:None,research_only:None,deprecated:None
```

修复要求：

- 增加一个兼容读取函数，支持 flat 与 nested 两种 strategies 结构。
- nested 结构下应遍历：

```text
production_selectable
research_only
deprecated
```

- 对有 `dependency_path` 的条目检查路径存在。
- 对没有 `dependency_path` 但有明确 `reason` 的 deprecated alias，可允许跳过，但报告中要说明。
- `run_tw_modular_contract_regression.py` 的 dependency path 输出 key 应避免冲突，例如：

```text
production_selectable.top50_exit_one_worst_sell
research_only.one_sell_one_buy_correct
deprecated.original
```

- 不得修改 registry 默认策略，不得新增策略规则。

## 4. Repair 2：manifest coverage 支持归档文档路径

问题：

`formal_replay_manifest.json` 中仍引用旧路径：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md
```

但真实文件已归档在：

```text
docs/archive/phase_history/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md
docs/archive/phase_history/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md
```

修复要求：

- 不创建空文件伪造历史报告。
- 可选择以下方式之一：

```text
方案 A：在 regression coverage audit 中支持 archive fallback，并在 output 中记录 actual_path。
方案 B：在 manifest 或旁路 mapping 中明确记录 archived path，且保留原始历史来源语义。
```

- 如果修改 `formal_replay_manifest.json`，必须说明这只是历史文档路径映射修复，不得改 replay 输出、模型、策略或收益结果。
- 更推荐修改 regression audit 支持 archive fallback，因为该 manifest 是历史 artifact 记录。

## 5. Repair 3：forbidden scope audit 适配冻结前已有 tracked diff

问题：

当前 `forbidden_scope_audit` 对 tracked modified 文件使用 diff marker 判断：

```text
frontend/src/views/tw-stock-monitor/index.vue
scripts/run_daily_tw_stock_auto_update.py
```

但这些文件是 R0 之前已有地基改动，diff 不一定包含旧 marker，导致 broader audit 失败。

修复要求：

- 不删除 `FORBIDDEN_SCOPE_PATHS`。
- 不删除 R15/R16 forbidden pattern 检查。
- 不简单把 status 改为 pass。
- 可采用以下安全方式：

```text
检查完整文件内容中 required markers 是否存在；
同时继续只对 added diff lines 扫描 forbidden patterns；
并要求对应 static/e2e/unit validator 文件存在；
```

- 对 R15 前端只读改动，应保留或增强以下证据：

```text
frontend/tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs exists
frontend/tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs exists
scripts/validate_tw_frontend_readonly_m4.py --json passed
UI2 readonly Playwright passed
```

- 对 R16 daily readonly 改动，应保留或增强以下证据：

```text
scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json passed
backend/tests 或 validator 覆盖 Agent prompt / readonly snapshot dry-run
```

- 如果现有 `tests/unit/test_tw_daily_readonly_snapshot_integration.py` 不存在，应确认是否应改为当前实际 validator/test 路径，而不是创建无内容测试。

## 6. 必须重跑的命令

R1R2 repair 后必须重跑：

```bash
python scripts/validate_tw_modular_artifact_contract.py --registry configs/tw_modular_registry.yaml --json
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_registry_m2.py --json
python scripts/validate_tw_frontend_readonly_m4.py --json
node frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
```

如果修改了 Python 脚本，还应重跑：

```bash
python -m py_compile scripts/run_tw_modular_contract_regression.py scripts/validate_tw_modular_artifact_contract.py
```

如果普通沙箱出现：

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

可按权限规则提升权限重跑本地只读检查，但不得借此执行网络下载、真实数据拉取、provider/latest/monitor/broker/order/OpenAI。

## 7. 执行报告输出

请输出：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1R2_REMAINING_REGRESSION_REPAIR_EXECUTION_REPORT_CN.md
```

报告结构：

```markdown
# Phase R1R2 执行报告：剩余 modular regression repair

## 1. 结论
## 2. 修改文件
## 3. Nested strategies registry 修复
## 4. Manifest coverage archive path 修复
## 5. Forbidden scope audit 修复
## 6. 重跑命令结果
## 7. Forbidden actions audit
## 8. 是否建议重新审查 R1
```

## 8. 通过标准

R1R2 通过必须满足：

```text
python scripts/run_tw_modular_contract_regression.py --json 返回 ok=true
registry_validation.json ok=true
manifest_coverage_audit.csv 无 fail
forbidden_scope_audit.csv 无 fail
M2/M4 仍通过
UI2 readonly Playwright 仍通过
未触发真实数据、provider publish、accepted latest、monitor、broker/order、OpenAI key
```

通过后，审查者再判断是否允许进入 R2。
