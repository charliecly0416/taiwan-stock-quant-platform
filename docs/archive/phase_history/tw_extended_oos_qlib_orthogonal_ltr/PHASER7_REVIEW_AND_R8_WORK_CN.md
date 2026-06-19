# Phase R7 审查与 R8 工作建议

生成日期：2026-06-16

## 1. 审查结论

R7 审查通过，允许进入 R8。

本次 R7 完成受控 extension capability smoke test：

- 独立构造 smoke artifact；
- 增加 `ext_sector_code`；
- manifest 声明 extension schema 和 capability；
- strategy dependency 明确消费 extension；
- validator 正例通过；
- validator 负例按预期失败；
- R6 regression 仍为 `ok=true`；
- 未修改 canonical R1 signals；
- 未修改 R2/R5 replay results；
- 未跑 replay；
- 未产生策略收益结论；
- 未接入前端、日更或生产链路。

## 2. 审查对象

R7 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER7_EXTENSION_SMOKE_REVIEW_HANDOFF_CN.md
```

R7 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER7_EXTENSION_SMOKE_EXECUTION_REPORT_CN.md
```

Smoke builder：

```text
scripts/build_tw_modular_extension_smoke_artifact.py
```

Smoke dependency：

```text
configs/strategy_dependencies/sector_extension_analysis_smoke.yaml
```

Smoke artifact：

```text
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/
```

更新：

```text
configs/tw_modular_registry.yaml
scripts/run_tw_modular_contract_regression.py
```

## 3. 复核结果

### 3.1 Smoke builder 可复跑

复核命令：

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

### 3.2 Extension 字段正确

Smoke `signals.csv` 新增字段：

```text
ext_sector_code
```

样例：

```text
TW1301 -> sector_smoke_13
```

该字段：

- 由 `instrument` 静态派生；
- 不读取收益、未来 label、成交、持仓或 replay 结果；
- 不参与 ranking；
- 不参与 replay；
- 不产生策略收益结论。

### 3.3 Manifest capability / extension schema 正确

Smoke manifest：

```text
artifact_name: fresh_qlib_adaptive_sector_extension_smoke
quality_status: smoke_only
capabilities.supports_sector_exposure: true
capabilities.extension_smoke_only: true
extensions.fields.ext_sector_code.semantic_role: sector_code
extensions.fields.ext_sector_code.availability_policy: static_reference
extensions.fields.ext_sector_code.allowed_consumers: [sector_analysis_smoke]
extensions.fields.ext_sector_code.ranking_allowed: false
no_replay: true
no_strategy_return_conclusion: true
```

### 3.4 Positive validation 通过

`positive_validation.json`：

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
dependency_forbidden_fields: pass
dependency_forbidden_actions: pass
```

### 3.5 Negative validation 按预期失败

负例：

```text
negative_missing_extension/manifest.json
```

构造方式：

- manifest 仍声明 `ext_sector_code`；
- `signals.csv` 删除 `ext_sector_code`；
- 使用同一个 smoke dependency 校验。

结果：

```text
ok: false
declared_extensions_exist: fail, ext_sector_code
strategy_required_extensions: fail, ext_sector_code:missing_column
```

该负例证明 validator 能拒绝缺失 extension 的 artifact。

### 3.6 R6 regression 仍通过

复核命令：

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

- registry 现在包含 6 个 dependency；
- `sector_extension_analysis_smoke` 通过 `applies_to_artifact_names` 限定只适用于 smoke artifact；
- 对 5 个 canonical R1 artifacts，该 dependency 被标记为 `skipped`；
- skipped 是预期行为，不计为失败；
- 既有 canonical R1/R2/R5/R6 回归仍通过。

### 3.7 Tests 通过

复核命令：

```bash
python -m py_compile scripts/build_tw_modular_extension_smoke_artifact.py scripts/run_tw_modular_contract_regression.py
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
py_compile: pass
pytest: 12 passed
```

### 3.8 范围外 diff 复核

以下对象无 tracked diff：

```text
data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/signals.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_summary.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_actions.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_daily_nav.csv
frontend/src/views/tw-stock-monitor/index.vue
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
```

Forbidden scope audit 仍为 pass：

```text
frontend: pass
daily update: pass
old formal replay runner: pass
backend_api_python: pass
src/api: pass
```

## 4. 残余风险

### 4.1 `ext_sector_code` 是 smoke-only

该字段只是由股票代码静态派生的 smoke 字段，不代表真实行业分类。不得把它解释为生产级 sector source。

### 4.2 Smoke dependency 名称清楚，但不是 valid strategy evidence

`sector_extension_analysis_smoke` 是 analysis smoke dependency，不跑 replay、不产生收益结论。后续若进入真实 sector-aware strategy，必须新建 strategy dependency 和单独审查。

### 4.3 Registry skip 逻辑需要在 R8 归档中说明

R7 在 regression 中引入 `applies_to_artifact_names`，使 smoke dependency 不套用到 canonical R1 artifacts。R8 release bundle 应明确：

- 哪些 dependency 是 production/research canonical；
- 哪些 dependency 是 smoke-only；
- skipped 的含义不是失败，也不是策略放行。

## 5. R8 建议方向

R8 应作为本轮 R0-R8 的最终归档和交付边界审查，不再新增机制。

建议主题：

```text
R0-R8 Modular Refactor Release Bundle / Final Boundary Audit
```

目标：

- 汇总 R0-R8 所有产物；
- 明确 release bundle 清单；
- 明确 canonical artifacts 与 smoke artifacts；
- 固化一键验证命令；
- 汇总已通过的 parity / validator / regression 证据；
- 汇总残余风险；
- 明确哪些内容仍禁止进入生产；
- 给出后续如果要接前端/日更/生产链路的前置条件。

## 6. R8 建议产出

建议新增：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER8_FINAL_RELEASE_BUNDLE_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER8_FINAL_RELEASE_BUNDLE_REVIEW_HANDOFF_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/R0_R8_MODULAR_REFACTOR_FINAL_STATE_CN.md
```

建议包含：

```text
release_bundle_manifest
canonical_artifacts
smoke_artifacts
validation_commands
parity_evidence
forbidden_scope_evidence
known_residual_risks
post_R8_allowed_next_steps
post_R8_forbidden_actions
```

## 7. R8 禁止事项

R8 禁止：

- 新训练；
- 调参；
- 重算模型分数；
- 修改 R1 canonical signals；
- 修改 R2/R5 replay results；
- 新增 replay 策略结果；
- 修改默认策略；
- 修改前端；
- 修改日更脚本；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order。

## 8. 给执行者的 R8 指令

请在 R7 审查通过后执行 R8：做 R0-R8 final release bundle / boundary audit。

只允许新增最终报告和 release bundle 清单，不改任何 canonical artifact，不跑训练，不跑新 replay，不接前端、日更或生产链路。

必须明确：

- R0-R8 每阶段产物；
- canonical artifacts；
- smoke-only artifacts；
- 一键验证命令；
- parity 与 validator 证据；
- forbidden scope 证据；
- 残余风险；
- 后续若要进入生产/前端/日更接入，需要另开阶段单独审查。
