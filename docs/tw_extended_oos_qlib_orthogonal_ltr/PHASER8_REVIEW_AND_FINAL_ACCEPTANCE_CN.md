# Phase R8 审查与最终归档结论

生成日期：2026-06-16

## 1. 审查结论

R8 审查通过。本轮 R0-R8 modular decoupled refactor 可以按 research / audit artifact 状态归档。

本次未发现需要阻塞归档的问题。

R8 完成了 R7 要求的 final release bundle / boundary audit：

- 新增最终状态文档；
- 新增 R8 执行报告；
- 新增 R8 review handoff；
- 汇总 R0-R8 阶段产物；
- 明确 canonical artifacts 与 smoke-only artifacts；
- 固化验证命令；
- 汇总 parity、validator、regression、forbidden scope 证据；
- 明确 post-R8 allowed next steps；
- 明确 post-R8 forbidden actions；
- 未新增训练、调参、score recompute、replay、前端、日更、provider publish、accepted latest、monitor 或交易链路接入。

## 2. 审查对象

R8 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER8_FINAL_RELEASE_BUNDLE_REVIEW_HANDOFF_CN.md
```

R8 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER8_FINAL_RELEASE_BUNDLE_EXECUTION_REPORT_CN.md
```

R0-R8 final state：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/R0_R8_MODULAR_REFACTOR_FINAL_STATE_CN.md
```

## 3. 复核结果

### 3.1 Release bundle 覆盖完整

`R0_R8_MODULAR_REFACTOR_FINAL_STATE_CN.md` 已覆盖：

- R0-R8 每阶段主题和主要产物；
- contract docs；
- configs；
- scripts；
- 五个 canonical signal artifacts；
- canonical ReplayResult artifact；
- regression audit bundle；
- R7 smoke-only artifact；
- review reports；
- 一键验证命令；
- 已归档证据；
- residual risks；
- post-R8 allowed next steps；
- post-R8 forbidden actions。

该结构满足 R7 对 R8 的归档要求。

### 3.2 Canonical / smoke 分类清楚

Canonical：

```text
五个 R1 signal artifacts
R2/R5 modular replay matrix ReplayResult artifact
五个 canonical strategy dependencies
```

Smoke-only：

```text
configs/strategy_dependencies/sector_extension_analysis_smoke.yaml
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/
```

文档已明确：

- `sector_extension_analysis_smoke` 不是 production strategy；
- `ext_sector_code` 不是生产级行业分类；
- smoke 不参与 replay；
- smoke 不产生策略收益结论；
- registry 中 `skipped` 是适用范围跳过，不是失败，也不是生产放行。

### 3.3 Regression 复跑通过

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

`signal_artifact_validation.csv` 显示：

- 5 个 canonical signal artifacts 基础 validation 均为 true；
- 5 个 canonical strategy dependencies 对 5 个 canonical artifacts 均为 true；
- `sector_extension_analysis_smoke` 对 canonical artifacts 均为 skipped，原因是 `applies_to_artifact_names=['fresh_qlib_adaptive_sector_extension_smoke']`。

该 skipped 行为与 R7/R8 设计一致。

### 3.4 ReplayResult validator 复跑通过

复核命令：

```bash
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json \
  --json
```

结果：

```text
ok: true
artifact_type: pass
schema_version: pass, replay_result_r5_action_window
required_replay_files: pass
actions_window_field: pass
execution_date_after_signal_date: pass
active_quantity_positive: pass
position_integrity: pass
coverage_audit_status: pass
forbidden_field_audit_status: pass
parity_audit_status: pass
action_key_parity_audit_status: pass
manifest_parity_status: pass
```

### 3.5 Parity 证据仍通过

复核文件：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/parity_summary.csv
```

结果：

```text
summary: pass, 25 vs 25
daily_nav: pass, 1975 vs 1975
actions: pass, 3651 vs 3651
action_key_parity: pass
baseline_not_modular_count: 0
modular_not_baseline_count: 0
duplicate_baseline_action_key_count: 0
duplicate_modular_action_key_count: 0
value_mismatch_count: 0
```

### 3.6 Extension smoke 复跑通过

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

负例明确失败于：

```text
declared_extensions_exist: fail, ext_sector_code
strategy_required_extensions: fail, ext_sector_code:missing_column
```

说明 validator 可以拒绝缺失 required extension 的 artifact。

### 3.7 Unit tests 通过

复核命令：

```bash
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
12 passed
```

### 3.8 Forbidden scope 复核通过

复核文件：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv
```

结果：

```text
frontend/src/views/tw-stock-monitor/index.vue: pass
scripts/run_daily_tw_stock_auto_update.py: pass
scripts/run_extended_oos_formal_replay_matrix.py: pass
backend_api_python: pass
src/api: pass
```

额外 tracked diff 复核对象：

```text
data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/signals.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_summary.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_actions.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_daily_nav.csv
frontend/src/views/tw-stock-monitor/index.vue
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
```

结果：无 tracked diff。

## 4. 残余风险

### 4.1 Baseline action parity 仍依赖兼容口径

baseline actions 仍没有 `window` 字段，action parity 继续使用 R5/R6 已审查通过的 prefix compatibility 口径。

这不阻塞 R8 归档，但后续若要做 release artifact packaging 或生产展示，应优先消除该兼容口径，或者在发布包 manifest 中明确写入该限制。

### 4.2 `ext_sector_code` 只是 smoke-only

`ext_sector_code` 是由 `instrument` 静态派生的测试字段，不代表真实行业分类。

后续若要做真实 sector-aware strategy，必须另开阶段：

- 接入真实 sector source；
- 定义 PIT / as-of 规则；
- 新增真实 strategy dependency；
- 新增正负例；
- 重新审查 replay 和生产边界。

### 4.3 R0-R8 不是生产接入包

当前 bundle 只证明 contract / registry / validator / replay result / extension smoke 机制可复核，以及 canonical replay parity 保持。

它不证明：

- 任一策略应该进入生产；
- 任一模型应作为默认模型；
- 任一 replay result 可作为交易建议；
- 可以接入前端、日更、provider publish、accepted latest、monitor 或交易链路。

### 4.4 仓库存在大量历史 untracked 文件

当前 forbidden scope 采用 tracked diff 口径。正式发布时不能直接按整个工作区打包，应按 R8 release bundle manifest 做精确清单，最好补 checksum / package manifest。

## 5. Post-R8 建议

R0-R8 可以归档。后续不要继续在 R8 内追加功能，应另开阶段。

建议下一阶段可选方向：

1. release packaging：为 R0-R8 bundle 生成 checksum / package manifest；
2. production readiness：只读前端/API/日更接入前置审查；
3. baseline action cleanup：消除 baseline actions 无 `window` 字段导致的 prefix compatibility 口径；
4. real sector extension：用真实行业分类替换 smoke-only `ext_sector_code`；
5. future development governance：后续新增模型、策略、数据时，优先引用 `docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md`。

## 6. 最终结论

R8 通过。

本轮 R0-R8 modular refactor 已形成可复核、可归档的 research / audit release bundle。当前边界仍停留在研究和审计产物，不允许未经新阶段审查直接进入生产、前端、日更、provider publish、accepted latest、monitor 或交易链路。
