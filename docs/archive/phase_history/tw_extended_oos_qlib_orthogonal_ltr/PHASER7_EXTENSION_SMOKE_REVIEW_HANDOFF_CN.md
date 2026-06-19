# Phase R7 Extension Capability Smoke 审查交接

生成日期：2026-06-16

## 1. 本阶段目标

R7 根据 R6 审查意见执行：

```text
Controlled Extension Capability Smoke Test
```

本阶段只构造一个独立 smoke artifact，用 `ext_sector_code` 验证 extension schema、capability、strategy dependency 和 validator 机制。

## 2. 审查对象

新增文件：

```text
scripts/build_tw_modular_extension_smoke_artifact.py
configs/strategy_dependencies/sector_extension_analysis_smoke.yaml
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER7_EXTENSION_SMOKE_EXECUTION_REPORT_CN.md
```

更新文件：

```text
configs/tw_modular_registry.yaml
scripts/run_tw_modular_contract_regression.py
```

新增 smoke artifact：

```text
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/
```

## 3. 一键复核命令

```bash
python scripts/build_tw_modular_extension_smoke_artifact.py --json
```

预期：

```text
ok: true
row_count: 30630
extension: ext_sector_code
positive_validation_ok: true
negative_missing_extension_validation_ok: false
negative_expected_to_fail: true
no_replay: true
no_strategy_return_conclusion: true
```

## 4. Regression 复核命令

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

当前结果：

```text
ok: true
signal_manifest_count: 5
strategy_dependency_count: 6
signal_validation_rows: 35
```

说明：

- registry 现在包含 6 个 dependency；
- 新增 `sector_extension_analysis_smoke` dependency；
- 该 dependency 通过 `applies_to_artifact_names` 限定只适用于 smoke artifact；
- R6 regression 对 canonical R1 artifacts 将该 dependency 标为 `skipped`，不算失败；
- 既有 R1/R2/R5/R6 回归仍通过。

## 5. 测试命令

```bash
python -m py_compile scripts/build_tw_modular_extension_smoke_artifact.py scripts/run_tw_modular_contract_regression.py
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

当前结果：

```text
py_compile: pass
pytest: 12 passed
```

## 6. Positive Validation

文件：

```text
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/positive_validation.json
```

结果：

```text
ok: true
extension_fields_declared: pass
declared_extensions_exist: pass
extension_metadata_complete: pass
extension_dtype_parseable: pass
extension_availability_policy: pass
strategy_required_capabilities: pass
strategy_required_extensions: pass
ranking_allowed: pass
```

## 7. Negative Validation

文件：

```text
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/negative_missing_extension_validation.json
```

结果：

```text
ok: false
declared_extensions_exist: fail, ext_sector_code
strategy_required_extensions: fail, ext_sector_code:missing_column
```

该负例是预期失败，用于证明 validator 能拒绝缺失 extension 的 artifact。

## 8. Extension 字段说明

字段：

```text
ext_sector_code
```

声明：

```text
dtype: string
semantic_role: sector_code
availability_policy: static_reference
allowed_consumers:
  - sector_analysis_smoke
ranking_allowed: false
required_for_core_replay: false
```

注意：

- `ext_sector_code` 是 smoke-only 静态派生字段；
- 不代表生产级行业分类；
- 不参与 ranking；
- 不参与 replay；
- 不产生策略收益结论。

## 9. 边界说明

R7 未执行：

- 训练；
- 调参；
- score recompute；
- replay；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker / quick-trade / order。

R7 未修改：

- R1 canonical `signals.csv`；
- R2/R5 replay summary；
- R2/R5 replay daily_nav；
- R2/R5 replay actions；
- 前端；
- 日更脚本；
- 旧 formal replay runner。

## 10. 建议审查重点

建议审查者重点看：

1. smoke artifact 是否位于独立目录；
2. `ext_sector_code` schema 是否完整；
3. capability 是否包含 `supports_sector_exposure=true`；
4. dependency 是否声明并消费 `ext_sector_code`；
5. 正例 validator 是否通过；
6. 负例 validator 是否按预期失败；
7. R6 regression 是否仍为 `ok=true`；
8. R7 是否没有触发 replay 或收益结论。

## 11. 建议结论

若审查者确认以上输出可复核，建议 R7 通过。
