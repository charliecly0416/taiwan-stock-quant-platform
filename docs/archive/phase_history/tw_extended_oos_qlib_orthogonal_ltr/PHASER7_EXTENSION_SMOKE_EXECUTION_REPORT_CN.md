# Phase R7 Extension Capability Smoke 执行报告

生成日期：2026-06-16

## 1. 执行范围

本阶段根据：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER6_REVIEW_AND_R7_WORK_CN.md
```

执行 R7：

```text
Controlled Extension Capability Smoke Test
```

目标是用一个无害 extension 验证 R3/R4/R6 的 extension schema、capability、strategy dependency 和 validator 机制确实可用。

## 2. 新增内容

新增 smoke dependency：

```text
configs/strategy_dependencies/sector_extension_analysis_smoke.yaml
```

新增 smoke 构建脚本：

```text
scripts/build_tw_modular_extension_smoke_artifact.py
```

新增 smoke artifact：

```text
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/
```

输出文件：

```text
manifest.json
signals.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
positive_validation.json
negative_missing_extension_validation.json
negative_missing_extension/manifest.json
negative_missing_extension/signals.csv
smoke_summary.json
```

同时在 registry 中登记：

```text
sector_extension_analysis_smoke:
  dependency_path: configs/strategy_dependencies/sector_extension_analysis_smoke.yaml
```

## 3. Smoke Artifact 构造

输入：

```text
data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json
```

输出：

```text
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/manifest.json
```

构造方式：

- 复制 R1 `fresh_qlib_adaptive` signal artifact 到独立 smoke 目录；
- 增加 `ext_sector_code`；
- `ext_sector_code` 由 `instrument` 静态派生，例如 `TW1301 -> sector_smoke_13`；
- 不读取收益、未来 label、成交、持仓或回放结果；
- 不改变 canonical R1 artifact；
- 不参与 replay；
- 不生成策略收益结论。

## 4. Extension Schema

`manifest.json` 中声明：

```text
extensions.schema_version: model_signal_extension_v1
extensions.fields.ext_sector_code.dtype: string
extensions.fields.ext_sector_code.semantic_role: sector_code
extensions.fields.ext_sector_code.availability_policy: static_reference
extensions.fields.ext_sector_code.allowed_consumers: [sector_analysis_smoke]
extensions.fields.ext_sector_code.ranking_allowed: false
extensions.fields.ext_sector_code.required_for_core_replay: false
```

capability 声明：

```text
supports_sector_exposure: true
extension_smoke_only: true
```

## 5. Strategy Dependency

`configs/strategy_dependencies/sector_extension_analysis_smoke.yaml` 声明：

```text
required_capabilities:
  - core_signal_v1
  - candidate_boundary:qlib_top50
  - supports_sector_exposure

required_extensions:
  - field: ext_sector_code
    semantic_role: sector_code
    usage: sector_analysis_smoke
```

该 dependency 同时声明：

```text
applies_to_artifact_names:
  - fresh_qlib_adaptive_sector_extension_smoke
```

用途：

- 允许 R6/R7 registry regression 识别它是 smoke artifact 专用 dependency；
- 不要求 canonical R1 artifacts 具备 `ext_sector_code`；
- 避免把 smoke dependency 错误套用到正式 signal artifacts。

## 6. Validator 正例

执行命令：

```bash
python scripts/build_tw_modular_extension_smoke_artifact.py --json
```

结果：

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

正例 validator：

```text
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/positive_validation.json
```

关键结果：

```text
artifact_type: pass
core_fields: pass
duplicate_key: pass
forbidden_fields: pass
extension_fields_declared: pass
declared_extensions_exist: pass
extension_metadata_complete: pass
extension_dtype_parseable: pass
extension_availability_policy: pass
extension_allowed_consumers_shape: pass
strategy_required_capabilities: pass
strategy_required_extensions: pass
ranking_allowed: pass
dependency_forbidden_fields: pass
dependency_forbidden_actions: pass
```

## 7. Validator 负例

负例：

```text
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/negative_missing_extension/manifest.json
```

负例构造：

- manifest 仍声明 `ext_sector_code`；
- `signals.csv` 删除 `ext_sector_code`；
- 使用同一个 `sector_extension_analysis_smoke` dependency 校验。

结果：

```text
ok: false
declared_extensions_exist: fail, ext_sector_code
strategy_required_extensions: fail, ext_sector_code:missing_column
```

该负例证明 dependency 可以声明并强制消费 extension。

## 8. R6 Regression 复跑

执行命令：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
ok: true
signal_manifest_count: 5
strategy_dependency_count: 6
signal_validation_rows: 35
```

说明：

- registry 已识别 6 个 dependency；
- `sector_extension_analysis_smoke` 对 canonical R1 artifacts 记为 `skipped`；
- skip 原因是 dependency 声明了 `applies_to_artifact_names=['fresh_qlib_adaptive_sector_extension_smoke']`；
- 既有 canonical R1/R2/R5/R6 回归仍为 `ok=true`。

## 9. 测试

执行命令：

```bash
python -m py_compile scripts/build_tw_modular_extension_smoke_artifact.py scripts/run_tw_modular_contract_regression.py
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
py_compile: pass
pytest: 12 passed
```

## 10. 边界确认

R7 未执行、未修改：

- qlib / LTR 训练；
- 调参；
- score recompute；
- R1 canonical `signals.csv`；
- R2/R5 replay summary / daily_nav / actions；
- replay；
- 策略收益结论；
- 默认策略；
- 前端；
- 日更脚本；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker / quick-trade / order。

## 11. 残余风险

1. `ext_sector_code` 是 smoke-only 静态派生字段，不代表生产级行业分类源。
2. 本阶段只验证 extension contract 能被声明、消费和拒绝缺失字段，不验证任何策略收益。
3. R6 regression 的 `signal_validation_rows` 从 30 增加到 35，其中 smoke dependency 对 5 个 canonical artifacts 为 skipped，不是失败。

## 12. 结论

R7 已完成。

建议审查者重点复核：

- `scripts/build_tw_modular_extension_smoke_artifact.py`
- `configs/strategy_dependencies/sector_extension_analysis_smoke.yaml`
- `data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/smoke_summary.json`
- `data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/positive_validation.json`
- `data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/negative_missing_extension_validation.json`
- `scripts/run_tw_modular_contract_regression.py` 中 dependency applicability skip 逻辑
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/regression_summary.json`
