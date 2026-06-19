# Phase R6 审查与 R7 工作建议

生成日期：2026-06-16

## 1. 审查结论

R6 审查通过，允许进入 R7。

本次 R6 完成一键全量 registry / artifact / replay result 回归审计。回归 runner 可复跑，输出 `ok=true`，覆盖五个 R1 signal artifact、五个 strategy dependency、R2/R5 ReplayResult、parity、forbidden scope 和 R0-R5 manifest coverage。

R6 未改变 R1 `signals.csv`，未改变 R2/R5 replay summary / daily_nav / actions 结果，未接入前端、日更或生产链路。

## 2. 审查对象

R6 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER6_FULL_REGISTRY_REGRESSION_REVIEW_HANDOFF_CN.md
```

R6 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER6_FULL_REGISTRY_REGRESSION_EXECUTION_REPORT_CN.md
```

Runner：

```text
scripts/run_tw_modular_contract_regression.py
```

R6 输出目录：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/
```

## 3. 复核结果

### 3.1 一键回归通过

复核命令：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
ok: true
signal_manifest_count: 5
strategy_dependency_count: 5
signal_validation_rows: 30
```

### 3.2 测试通过

复核命令：

```bash
python -m py_compile scripts/run_tw_modular_contract_regression.py
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
py_compile: pass
pytest: 12 passed
```

### 3.3 Signal artifact validation 覆盖完整

`signal_artifact_validation.csv` 共 30 行：

```text
5 signal artifacts x (core validation + 5 strategy dependencies)
```

覆盖模型：

- `fresh_qlib_adaptive`
- `fresh_qlib_2025_ltr`
- `frozen_qlib_2025_ltr`
- `e4_frozen_qlib_2023_2025_ltr`
- `frozen_qlib_2018_2022`

覆盖 dependency：

- core validation；
- `original`；
- `top50_exit_all`；
- `top50_exit_one_worst_sell`；
- `one_sell_one_buy_correct`；
- `one_sell_one_buy_buggy_e8r`。

所有行 `ok=True`，无 failed checks。

### 3.4 ReplayResult validation 通过

`replay_result_validation.json` 显示：

```text
ok: true
artifact_type: replay_result
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

### 3.5 Parity summary 通过

`parity_summary.csv` 显示：

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

### 3.6 Forbidden scope audit 通过

`forbidden_scope_audit.csv` 显示以下 tracked diff 口径均 pass：

```text
frontend/src/views/tw-stock-monitor/index.vue
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
backend_api_python
src/api
```

说明：

- R6 使用 `git diff --name-only HEAD -- tracked files` 口径；
- 当前仓库已有大量 untracked 历史产物，该口径适合判断本阶段是否改动禁止范围 tracked 文件；
- 对 R0-R6 新增未跟踪产物的审查以文件内容和 regression 输出为准。

### 3.7 Manifest coverage 通过

`manifest_coverage_audit.csv` 覆盖：

- R0-R5 required contract docs；
- registry；
- replay matrix config；
- R2/R5 replay manifest；
- 五个 R1 signal manifest；
- 每个 R1 artifact 的 signals/schema/audit/mapping 文件；
- R2/R5 replay outputs；
- 五个 strategy dependency yaml。

全部 `status=pass`。

## 4. Runner 行为审查

`scripts/run_tw_modular_contract_regression.py` 行为是只读输入、写 R6 自己的审计输出目录：

读取：

- registry；
- replay manifest；
- signal manifests；
- strategy dependencies；
- parity audits；
- tracked diff 状态。

写入：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/
```

未发现其重跑 replay、修改 signals、修改 replay results、训练模型或接入生产链路。

## 5. 残余风险

### 5.1 Forbidden scope 只覆盖 tracked diff

该口径合理，但不等于审计所有 untracked 文件。后续归档阶段应明确 R0-R8 release bundle 清单，避免历史 untracked 文件混入正式交付。

### 5.2 Manifest coverage 当前覆盖 R0-R5

R6 regression 的 manifest coverage 目标是验证 R0-R5 产物。R6 自身的报告/handoff和 regression 输出没有纳入 required manifest list。后续 R8 汇总归档时应补全 R0-R8 全量清单。

### 5.3 Baseline actions 仍无 window

R6 继续沿用 R5 已通过的兼容口径。modular actions 已有 window；baseline 无 window 的历史限制仍需在最终归档中说明。

## 6. R7 建议方向

建议 R7 做：

```text
Controlled Extension Capability Smoke Test
```

目标是用一个无害 extension 做最小样例，验证 R3/R4/R6 的扩展机制确实可用。

建议选择：

```text
ext_sector_code
```

原因：

- 不涉及收益；
- 不改变 ranking；
- 不改变 strategy；
- 不改变 replay；
- 可作为 schema/capability/dependency validator 的 smoke test；
- 风险低于 risk score / horizon score / ensemble score。

## 7. R7 建议产出

建议新增：

```text
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/
configs/strategy_dependencies/sector_extension_analysis_smoke.yaml
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER7_EXTENSION_SMOKE_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER7_EXTENSION_SMOKE_REVIEW_HANDOFF_CN.md
```

可新增只读脚本：

```text
scripts/build_tw_modular_extension_smoke_artifact.py
```

该脚本只能：

- 读取一个 R1 signal artifact；
- 复制为 smoke artifact；
- 增加 `ext_sector_code`；
- 在 manifest 声明 extension schema 和 capability；
- 运行 validator；
- 不参与 replay；
- 不产生收益结论。

## 8. R7 禁止事项

R7 禁止：

- 训练 qlib 或 LTR；
- 调参；
- 重算模型分数；
- 修改 R1 canonical signals；
- 修改 R2/R5 replay results；
- 新增策略收益结论；
- 修改默认策略；
- 修改前端；
- 修改日更脚本；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order。

## 9. 给执行者的 R7 指令

请在 R6 审查通过后执行 R7：做一个受控 extension capability smoke test。

建议使用 `ext_sector_code`，只构造一个独立 smoke artifact，不改 R1 canonical artifacts，不跑 replay，不产生策略收益结论。

必须证明：

- extension schema 完整；
- capability 声明完整；
- strategy dependency 可以声明并消费该 extension；
- validator 正例通过；
- validator 至少包含一个负例，例如 missing extension 或 usage_not_allowed；
- R1/R2/R5/R6 既有结果不变；
- 前端、日更、provider、accepted latest、monitor、broker/order 无触发。
