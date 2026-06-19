# Phase R5 审查与 R6 工作建议

生成日期：2026-06-16

## 1. 审查结论

R5 审查通过，允许进入 R6。

本次 R5 完成：

- modular replay actions 增加 `window` 字段；
- R2 summary / daily_nav / action key parity 继续 pass；
- ReplayResultArtifact validator 可用；
- validator 单元测试扩展到 12 项并通过；
- 未改变 R1 `signals.csv`；
- 未改变 R2 summary / daily_nav 关键结果；
- 未接入前端、日更或生产链路。

## 2. 审查对象

R5 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER5_REPLAY_RESULT_VALIDATOR_ACTION_WINDOW_REVIEW_HANDOFF_CN.md
```

R5 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER5_REPLAY_RESULT_VALIDATOR_ACTION_WINDOW_EXECUTION_REPORT_CN.md
```

核心修改：

```text
scripts/run_tw_modular_config_replay_matrix.py
scripts/validate_tw_modular_artifact_contract.py
tests/unit/test_validate_tw_modular_artifact_contract.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_actions.csv
```

## 3. 复核结果

### 3.1 Actions 已新增 window 字段

当前 `formal_replay_actions.csv` header：

```text
action,effective_nav_date,execution_date,fee_and_tax,method,price,quantity,reason,rule,signal_date,symbol,window
```

样例：

```text
historical_add,...,fresh_qlib_adaptive,...,original,2026-01-02,TW3260,2026_ytd
```

### 3.2 Replay rerun parity 通过

复核命令：

```bash
python scripts/run_tw_modular_config_replay_matrix.py --config configs/tw_modular_replay_matrix.yaml
```

结果：

```text
ok: true
parity_status: pass
summary: pass
daily_nav: pass
actions: pass
```

当前 `r2_action_key_parity_audit.csv`：

```text
baseline_filtered_rows: 3651
modular_action_rows: 3651
baseline_not_modular_count: 0
modular_not_baseline_count: 0
duplicate_baseline_action_key_count: 0
duplicate_modular_action_key_count: 0
value_mismatch_count: 0
status: pass
```

### 3.3 ReplayResult validator 通过

复核命令：

```bash
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json \
  --json
```

结果：

```text
ok: true
artifact_type: replay_result
schema_version: replay_result_r5_action_window
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

### 3.4 Tests 通过

复核命令：

```bash
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
12 passed
```

### 3.5 范围外 diff 复核

以下对象无 tracked diff：

```text
frontend/src/views/tw-stock-monitor/index.vue
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/signals.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_summary.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_daily_nav.csv
```

说明：`formal_replay_actions.csv` 本轮预期变更是新增 `window` 字段；action key/value parity 已证明策略行为未改变。

## 4. 残余风险

### 4.1 Baseline actions 仍无 window

modular actions 已有 `window`，但 baseline actions 仍无 `window`，因此 parity 仍依赖：

```text
baseline_actions_prefix_by_2026_ytd_summary_action_plus_skipped_count
```

该口径已有代码依据且 R5 通过，但若后续需要彻底去除 prefix 依赖，需要生成带 window 的新版 baseline 或仅以 modular lineage 作为后续标准。

### 4.2 ReplayResult validator 仍可继续增强

当前 validator 已覆盖核心 replay result 检查，但后续还可以扩展：

- daily_nav 连续性；
- final holdings mark-to-market；
- skipped action reason 完整性；
- manifest artifact hash；
- schema field dtype。

这些不阻塞 R5。

## 5. R6 建议方向

建议 R6 做：

```text
Full Registry Regression / Artifact Audit / Release Bundle
```

目标：

- 一键验证 R1 signal artifacts；
- 一键验证 R2/R5 replay result artifact；
- registry 覆盖全部 R0-R5 产物；
- 生成全量 audit report；
- 固化本地 smoke command；
- 不改变 signals/replay 结果；
- 不接入前端、日更或生产链路。

## 6. R6 建议产出

建议新增：

```text
scripts/run_tw_modular_contract_regression.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER6_FULL_REGISTRY_REGRESSION_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER6_FULL_REGISTRY_REGRESSION_REVIEW_HANDOFF_CN.md
```

建议输出：

```text
registry_validation.json
signal_artifact_validation.csv
replay_result_validation.json
parity_summary.csv
forbidden_scope_audit.csv
manifest_coverage_audit.csv
```

## 7. R6 禁止事项

R6 禁止：

- 训练 qlib 或 LTR；
- 调参；
- 重算模型分数；
- 修改 R1 signals；
- 修改 R2/R5 replay results；
- 根据收益筛选模型；
- 修改默认策略；
- 修改前端；
- 修改日更脚本；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order。

## 8. 给执行者的 R6 指令

请在 R5 审查通过后执行 R6：做全量 registry / artifact / replay result 回归审计。

只允许新增只读 regression runner 和审计产物。不得改变 R1 signals、R2/R5 replay summary/actions/daily_nav，不得接入前端、日更或生产链路。

必须能一键验证：

- registry dependency paths；
- 五个 R1 signal artifacts；
- R2/R5 replay result artifact；
- summary/daily_nav/actions parity；
- forbidden scope；
- R0-R5 manifest 覆盖。
