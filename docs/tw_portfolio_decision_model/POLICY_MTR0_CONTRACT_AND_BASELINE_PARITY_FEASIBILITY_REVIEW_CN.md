# POLICY_MTR0_CONTRACT_AND_BASELINE_PARITY_FEASIBILITY_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_MTR0_WITH_MTR2_LINEAGE_BLOCKER
```

MTR0 执行产物通过审查，可进入 MTR1 的 qlib-only OrderIntent parity 与机制 readonly replay 规划。

限制条件：

```text
MTR1 只能使用 qlib-only 标准 ModelSignalArtifact。
MTR2 在指定 qlib+LTR 标准 ModelSignalArtifact manifest 修复前必须阻断。
不得使用 LTR private artifacts 或替代路径绕过 lineage blocker。
```

## 2. Evidence Checked

已检查：

```text
docs/tw_portfolio_decision_model/POLICY_MTR0_CONTRACT_AND_BASELINE_PARITY_FEASIBILITY_EXECUTION_REPORT_CN.md
configs/strategy_dependencies/mechanism_transfer_top50_cost_aware_v1.yaml
data_tw/experiments/policy_mtr_mechanism_transfer/mtr0_contract_and_feasibility/manifest.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr0_contract_and_feasibility/signal_lineage_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr0_contract_and_feasibility/baseline_parity_feasibility_plan.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr0_contract_and_feasibility/mechanism_candidate_contract_matrix.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr0_contract_and_feasibility/dependency_validator_gap_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr0_contract_and_feasibility/forbidden_action_audit.csv
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/signals.csv header
```

并搜索：

```text
configs/
backend/
frontend/
scripts/
docs/tw_modular_contracts/
docs/tw_portfolio_decision_model/
```

未发现 `mechanism_transfer_top50_cost_aware_v1` 被接入 production registry、backend/API、frontend、daily orchestrator、provider/latest 或默认策略路径。

## 3. Dependency Contract

结论：

```text
PASS
```

`configs/strategy_dependencies/mechanism_transfer_top50_cost_aware_v1.yaml` 存在且包含 MTR0 必需边界：

```text
diagnostic_only = true
research_only = true
production_allowed = false
not_default_candidate = true
not_order = true
not_target_position = true
no_replay_return_conclusion = true
max_buy_count = 1
max_sell_count = 1
```

required core fields 覆盖：

```text
date
instrument
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
```

ranking usage 与合同一致：

- `candidate_rank` 只用于 qlib top50 candidate boundary。
- `full_qlib_rank` 用于 qlib exit boundary 和 worst holding。
- `buy_score` 用于买入优先级、score gap 和 persistence gate。
- `score_rank` 用于 rank gap 和 overlap audit。
- `raw_score` 只作为 audit。

forbidden fields / forbidden actions 覆盖 future return、label、execution、cash/NAV、broker/order、target position/weight、replay return、provider/latest、frontend default、daily/provider、replay engine 修改等红线。

## 4. ModelSignal Lineage

结论：

```text
PASS_FOR_MTR1
BLOCK_MTR2_UNTIL_LINEAGE_REPAIR
```

qlib-only 标准 manifest 可用：

```text
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
```

审查确认：

```text
artifact_type = model_signal
model_family = qlib
quality_status = pass
capabilities.core_signal_v1 = true
candidate_boundary = qlib_top50
buy_ordering = buy_score_desc
full_rank_exit = full_qlib_rank
row_count = 119862
window = 2023-01-03..2026-05-07
```

signals header 包含标准 core 字段：

```text
date,instrument,model_name,model_family,candidate_rank,buy_score,raw_score,score_rank,full_qlib_rank,signal_asof,available_at,source_artifact,source_model_artifact,source_feature_artifact
```

qlib+LTR 指定标准 manifest 缺失：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/r1_legacy_signal_adapter_20260616/manifest.json
```

执行产物正确记录为 `manifest_path_missing_defer_MTR2_do_not_use_private_or_alternate_signal_path`。因此 MTR2 不得启动，除非该标准 ModelSignalArtifact lineage 被修复并通过单独审查。

## 5. Baseline Parity Feasibility

结论：

```text
PASS_FOR_MTR1
```

`baseline_parity_feasibility_plan.csv` 明确 MTR1 只做：

```text
OrderIntent action parity
daily buy/sell count parity
same signal_date/instrument/action parity
ReplayResult metric parity after MTR1
```

关键审查点：

- qlib-only parity 使用标准 ModelSignalArtifact、标准 PortfolioState 和标准 PriceStore。
- `order_intent_builder_needed=true` 合理，MTR1 需要先输出 OrderIntentArtifact。
- `replay_engine_change_needed=false`，没有要求 replay engine 读取策略私有字段。
- qlib+LTR parity 被延后到 MTR2 lineage repair 后。
- MTR0 本身未生成正式 OrderIntent，未跑 replay return。

## 6. Mechanism Candidate Matrix

结论：

```text
PASS
```

`mechanism_candidate_contract_matrix.csv` 覆盖 M0-M6，且与 MTR mainline / work doc 一致：

```text
M0 baseline parity: top50_exit_one_worst_sell
M1 max_replace_per_day in [1, 2]
M2 hold_rank_buffer in [60, 75, 100]
M3 score_z_gap_min in [0.0, 0.25, 0.50], rank_gap_min in [0, 5, 10]
M4 fixed fee/tax cost gate using score/rank advantage only
M5 PIT TWII market_regime_code hook only
M6 C1-C4 fixed combos from mainline
```

所有候选均为：

```text
order_intent_expressible = true
forbidden_input_needed = false
production_allowed = false
```

限制：

```text
M5/M6 依赖 ext_market_regime_code 的部分只能作为合同 hook。
MTR1 若启用 M5/M6，必须先补 extension schema 与 PIT TWII lineage；否则 MTR1 应只跑不需要 extension 的 M0-M4/C1-C3。
```

## 7. Forbidden Action Audit

结论：

```text
PASS
```

`forbidden_action_audit.csv` 的 13 项均为 `not_performed`：

```text
trained_model
ran_replay_return
generated_order_intent
modified_replay_engine
modified_registry_default
modified_frontend_or_api
modified_daily_or_provider
provider_publish
accepted_latest_switch
broker_or_quick_trade
target_weight_or_position_output
future_or_replay_return_input
model_private_file_read
```

交叉搜索未发现策略名进入 `configs` registry、backend/API、frontend、daily/provider 或 scripts 默认执行路径。MTR 输出目录只包含 MTR0 manifest 与 audit CSV，不包含 OrderIntentArtifact 或 ReplayResultArtifact。

## 8. Validator Gap

结论：

```text
PASS_WITH_ACTION_ITEMS
```

已记录的 gap 不阻断 MTR0，但会影响 MTR1 gate：

1. 通用 validator 对 `diagnostic_only` 策略的 allowlist 过窄，当前偏向 `one_sell_one_buy_buggy_e8r`。
2. `forbidden_actions` 的 list/dict 形态需要统一或 validator 兼容。
3. portfolio optimizer validator 不应复用于 MTR dependency。
4. M5/M6 的 `ext_market_regime_code` 需要 extension schema 与 PIT TWII feature lineage。
5. qlib+LTR 标准 manifest 缺失是 MTR2 blocker。

MTR1 work doc 必须把这些列为前置要求或阶段限制。

## 9. Findings

### Medium

1. qlib+LTR lineage 缺失，MTR2 必须阻断。

   指定标准 manifest 不存在，不能用 private LTR artifact 或替代 CSV 代替。MTR1 可继续 qlib-only；MTR2 需要 lineage repair 后另审。

2. M5/M6 的 regime hook 目前只是合同预留。

   MTR0 未消费 extension，符合要求；但 MTR1 若要实际跑 M5 或 C4，必须先补 `ext_market_regime_code` extension schema、PIT TWII feature lineage 与 validator。

### Low

1. validator gap 已记录但未修复。

   这不阻断 MTR0，因为本阶段不要求通用 validator 直接通过；但 MTR1 不能把未兼容的 validator 当作通过证据。

## 10. Gate Decision

```text
dependency_complete_gate: PASS
diagnostic_only_gate: PASS
production_allowed_false_gate: PASS
standard_ModelSignalArtifact_qlib_only_gate: PASS
standard_ModelSignalArtifact_qlib_ltr_gate: BLOCK_DEFER_MTR2
no_private_model_file_gate: PASS
baseline_parity_without_replay_private_field_gate: PASS
M0_M6_mainline_candidate_gate: PASS
no_return_screening_gate: PASS
no_order_intent_MTR0_gate: PASS
no_replay_return_MTR0_gate: PASS
forbidden_action_gate: PASS
production_default_boundary_gate: PASS
MTR1_readiness_gate: PASS_QLIB_ONLY
MTR2_readiness_gate: BLOCKED_LINEAGE_REPAIR_REQUIRED
```

## 11. Recommendation

```text
Proceed to MTR1 qlib-only only.
Do not start MTR2 until qlib+LTR standard ModelSignalArtifact manifest exists and is reviewed.
Do not use private or alternate signal paths.
Do not switch production/default/frontend/API/Agent/daily/provider/latest.
```

已按 PASS 条件另写下一步工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_MTR1_QLIB_ONLY_ORDER_INTENT_PARITY_AND_MECHANISM_REPLAY_WORK_CN.md
```
