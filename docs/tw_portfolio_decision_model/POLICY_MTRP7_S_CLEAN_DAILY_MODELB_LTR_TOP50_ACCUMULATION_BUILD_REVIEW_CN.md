---
created_at: 2026-06-28T20:18:21Z
status: review
phase: MTRP7_S_CLEAN_DAILY_MODELB_LTR_TOP50_ACCUMULATION_BUILD
reviewer: MTRP7_S
strategy_candidate: top50_hold_rank_buffer_100
readonly_only: true
simulation_only: true
production_allowed: false
production_ready: false
default_switch_allowed: false
formal_phase_yz_write_allowed: false
latest_pointer_mutation_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
broker_authorized: false
verdict: PASS_MODELB_ACCUMULATED_MTRP7_R_NEEDS_REPAIR
---

# POLICY_MTRP7_S_CLEAN_DAILY_MODELB_LTR_TOP50_ACCUMULATION_BUILD_REVIEW_CN

## 1. Verdict

```text
PASS_MODELB_ACCUMULATED_MTRP7_R_NEEDS_REPAIR
```

审查结论：

```text
MTRP7_S clean daily ModelB accumulation 本身通过：
- 新增 isolated ModelB day = 10 天；
- rerun 后 clean Tier A eligible = 13 天；
- daily ModelB signals 均为 rows=50，ModelSignal core 字段齐全；
- PIT/available_at、forbidden field、forbidden scope 审查通过；
- 2026-06-16 因 50/50 feature rows 缺失而跳过，合理。

但 MTRP7_R rerun 仍需修复：
- MTRP7_R 已参数化读取 MTRP7_S isolated ModelB root，并物化 isolated_phase_yz；
- 但 rerun_mtrp7/ 只包含 manifest.json、validator_report.json、tier_a_rerun_dates.csv；
- 代码没有调用原 MTRP7 isolated daily shadow dry-run builder，也没有生成 daily bridge/order intent/replay 等 MTRP7 rerun 产物；
- 因此当前 R 的 PASS_READY_FOR_MTRP8_SHADOW_REVIEW 仍是 readiness gate/manifest 级声明，不能视为 work doc 要求的真实 MTRP7 rerun。
```

本 verdict 只认可 ModelB 已补齐；不授权进入 MTRP8 shadow review，不授权 readonly exposure design review，不授权 production default switch。

## 2. 审查依据

已按要求阅读并遵守：

- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-model-onboarding/SKILL.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP7_S_CLEAN_DAILY_MODELB_LTR_TOP50_ACCUMULATION_BUILD_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP7_S_CLEAN_DAILY_MODELB_LTR_TOP50_ACCUMULATION_BUILD_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP7_R_CLEAN_DAILY_TIER_A_LINEAGE_REPAIR_AND_RERUN_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP7_R_CLEAN_DAILY_TIER_A_LINEAGE_REPAIR_AND_RERUN_WORK_CN.md`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

审查对象：

- `scripts/build_tw_policy_mtrp7_s_clean_daily_modelb_ltr_top50_accumulation.py`
- `scripts/build_tw_policy_mtrp7_r_clean_daily_tier_a_lineage_and_rerun.py`
- `data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build/`

## 3. Findings

### Critical

无。

### High

1. MTRP7_R rerun 不是完整原 MTRP7 shadow dry-run rerun，不能放行进入 MTRP8。

   证据：

   ```text
   mtrp7_r_rerun/rerun_mtrp7/ file count = 3
     manifest.json
     tier_a_rerun_dates.csv
     validator_report.json
   ```

   代码证据：

   ```text
   scripts/build_tw_policy_mtrp7_r_clean_daily_tier_a_lineage_and_rerun.py:1052-1131
   maybe_rerun_mtrp7() 只写 tier_a_rerun_dates.csv、manifest.json、validator_report.json，
   直接设置 rerun_verdict = PASS_READY_FOR_MTRP8_SHADOW_REVIEW。
   ```

   与原 MTRP7 builder 对照：

   ```text
   scripts/build_tw_policy_mtrp7_isolated_daily_shadow_dry_run.py
   原 MTRP7 输出 daily_input_discovery、daily_bridge_artifact_register、
   daily_order_intent_artifact_register、daily_shadow_replay_artifact_register、
   shadow_accumulation_register、candidate_baseline_skip_delta、
   price_mark_coverage_audit、readonly_wording_audit 等产物。
   ```

   当前 rerun 目录没有这些产物，因此不满足 MTRP7_S work doc 中“真实重跑 MTRP7_R，不得只写 manifest-only pass”的实质要求。虽然 validator 中写了 `manifest_only_pass=false`，但审查不接受该自声明作为真实 rerun 证据。

### Medium

1. MTRP7_R 的 isolated_phase_yz 物化是实质产物，不能把 R 全部判失败。

   证据：

   ```text
   mtrp7_r_rerun/isolated_phase_yz file count = 195
   isolated_model_signal_register.csv rows = 26
   price_source_register.csv rows = 13
   lineage_checksum_audit.csv rows = 26
   pit_available_at_audit.csv rows = 13
   ```

   这说明 R 已经真实读取 S 的 isolated ModelB root，并构建同日 Tier A lineage；缺口只在后续 MTRP7 shadow dry-run rerun 没有真正调用原链路。

2. `scripts/build_tw_policy_mtrp7_s_clean_daily_modelb_ltr_top50_accumulation.py` 使用 `subprocess.run()` 调用 MTRP7_R，并通过环境变量传递：

   ```text
   MTRP7_R_OUT_ROOT = mtrp7_r_rerun
   MTRP7_S_ISOLATED_MODELB_ROOT = isolated_modelb_yz2
   MTRP7_R_REPORT_PATH = mtrp7_r_rerun_execution_report.md
   ```

   该参数化方向正确。

### Low

1. `python scripts/build_tw_policy_mtrp7_s_clean_daily_modelb_ltr_top50_accumulation.py` rerun 时出现 matplotlib cache 提示：

   ```text
   /home/chuliyang/.config/matplotlib is not a writable directory
   Matplotlib created a temporary cache directory at /tmp/...
   ```

   这是本地 import/cache 行为，不影响只读安全边界，也未触碰 production/default/latest/provider。

## 4. ModelB Accumulation 审查

通过。

`validator_report.json`：

```text
status = pass
verdict = PASS_MODELB_ACCUMULATED_AND_MTRP7_R_READY_FOR_MTRP8
built_day_count = 10
minimum_modelb_days_required = 5
minimum_modelb_days_pass = true
```

实际 built dates：

```text
2026-06-01
2026-06-02
2026-06-03
2026-06-04
2026-06-05
2026-06-08
2026-06-09
2026-06-10
2026-06-11
2026-06-12
```

这满足“至少补齐 2 个新增同日 ModelB day，使 clean Tier A days >= 5”的要求；执行声称补 10 天，审查确认 10 天。

## 5. Frozen LTR / PIT 审查

通过。

`model_load_audit.json`：

```text
model_path = data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_model.pkl
model_sha256 = 5f98a74c3c8f7d2c0b95858d57ac766fd98eed89dd1cba5c2ca71c0a5d79426d
model_family = LightGBM.LGBMRanker
feature_count_manifest = 78
feature_count_loaded = 78
load_status = pass
model_training_performed = false
model_tuning_performed = false
model_replacement_performed = false
isolated_existing_ltr_scoring_only = true
```

`feature_schema_audit.csv`：

```text
model_feature_whitelist_present_in_pit_feature_source = pass
model_feature_whitelist_no_forbidden_columns = pass
feature_count = 78
```

PIT audit：

```text
2026-06-01 feature_available_at_max=2026-06-01 pit_pass=True
2026-06-02 feature_available_at_max=2026-06-02 pit_pass=True
2026-06-03 feature_available_at_max=2026-06-03 pit_pass=True
2026-06-04 feature_available_at_max=2026-06-04 pit_pass=True
2026-06-05 feature_available_at_max=2026-06-05 pit_pass=True
2026-06-08 feature_available_at_max=2026-06-08 pit_pass=True
2026-06-09 feature_available_at_max=2026-06-09 pit_pass=True
2026-06-10 feature_available_at_max=2026-06-10 pit_pass=True
2026-06-11 feature_available_at_max=2026-06-11 pit_pass=True
2026-06-12 feature_available_at_max=2026-06-11 pit_pass=True
```

2026-06-16 跳过合理：

```text
model_a_ready = True
price_ready = True
model_loaded = True
status = blocked
reason = missing_or_pit_failed_feature_rows
model_a_top50_rows = 50
feature_ready_rows = 0
missing_feature_rows = 50
pit_fail_rows = 0
built = False
```

这符合“若某日期 feature 不足或 PIT 不通过，不得补该日”。

## 6. ModelSignalArtifact 审查

通过。

独立抽样全部 10 个 daily `signals.csv`：

```text
daily_count = 10
each rows = 50
date = signal_asof = directory date
available_at <= signal_asof
score_rank = 1..50
required core fields present = true
forbidden fields present = false
bad = []
```

字段符合 ModelSignalArtifact core 要求，并包含 MTRP7_S 控制字段：

```text
production_candidate
production_allowed
not_published_latest
readonly_only
simulation_only
```

未发现以下 forbidden 字段进入 `signals.csv`：

```text
future_return*
future_excess_return*
forward_return*
label*
replay_return
realized_pnl
realized_return
execution_price
execution_date
cash
nav
equity
target_weight
target_position
quantity
broker
broker_order_id
```

## 7. MTRP7_R Rerun 审查

部分通过，需修复后才能进入 MTRP8。

通过项：

```text
MTRP7_R output root = data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build/mtrp7_r_rerun
validator_report.status = pass
validator_report.verdict = PASS_TIER_A_LINEAGE_REPAIRED_MTRP7_READY_FOR_MTRP8
eligible_day_count = 13
minimum_clean_daily_tier_a_days_pass = true
tier_b_fallback_used = false
isolated_phase_yz_written = true
rerun_performed = true
rerun_mtrp7_verdict = PASS_READY_FOR_MTRP8_SHADOW_REVIEW
```

Eligible dates：

```text
2026-05-07
2026-06-01
2026-06-02
2026-06-03
2026-06-04
2026-06-05
2026-06-08
2026-06-09
2026-06-10
2026-06-11
2026-06-12
2026-06-15
2026-06-17
```

阻断项：

```text
rerun_mtrp7/ 只有 3 个文件，未生成原 MTRP7 daily shadow dry-run 的 bridge/order/replay/accumulation 产物。
```

因此 R 当前不能作为“真实 MTRP7 rerun”通过。

## 8. Forbidden Actions / Production Boundary

通过。

MTRP7_S `forbidden_scope_audit.csv` 共 15 项，全部：

```text
performed = False
status = pass
```

覆盖：

```text
training
tuning
model_replacement
network_or_provider_refresh
provider_publish
accepted_latest_switch
latest_pointer_mutation
formal_phase_yz_write
formal_pricestore_write
production_default_registry_change
frontend_api_agent_change
daily_auto_default_path_change
broker_quick_trade_real_order
target_weight_position_quantity
return_filter_or_return_tuning
```

MTRP7_R `forbidden_scope_audit.csv` 共 20 项，全部：

```text
performed = False
status = pass
```

敏感生产路径搜索：

```bash
rg -n "mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build|MTRP7_S_CLEAN_DAILY_MODELB|mtrp7_r_rerun" \
  configs backend frontend scripts/run_daily_tw_stock_auto_update.py backend/scripts/update_tw_stock_daily.py
```

结果：

```text
no matches
```

未发现 formal phase_yz/latest/provider/accepted latest/production/default/frontend/API/Agent/PriceStore/broker/order 被接入或切换。

## 9. 验证命令

已运行：

```bash
python -m py_compile scripts/build_tw_policy_mtrp7_s_clean_daily_modelb_ltr_top50_accumulation.py scripts/build_tw_policy_mtrp7_r_clean_daily_tier_a_lineage_and_rerun.py
```

结果：

```text
pass
```

已运行：

```bash
python scripts/build_tw_policy_mtrp7_s_clean_daily_modelb_ltr_top50_accumulation.py
```

结果：

```json
{
  "status": "pass",
  "verdict": "PASS_MODELB_ACCUMULATED_AND_MTRP7_R_READY_FOR_MTRP8",
  "built_day_count": 10,
  "built_dates": [
    "2026-06-01",
    "2026-06-02",
    "2026-06-03",
    "2026-06-04",
    "2026-06-05",
    "2026-06-08",
    "2026-06-09",
    "2026-06-10",
    "2026-06-11",
    "2026-06-12"
  ]
}
```

另做独立 CSV/JSON 检查：

```text
daily ModelB signals rows/header/rank/asof/available_at/forbidden fields
modelb_build_plan.csv
model_a_price_ready_dates.csv
pit_available_at_audit.csv
feature_schema_audit.csv
forbidden_scope_audit.csv
model_load_audit.json
MTRP7_R validator_report.json
MTRP7_R rerun_mtrp7_summary.json
MTRP7_R rerun_mtrp7/ file list
isolated_phase_yz materialized file count
sensitive production path rg search
```

## 10. Next Work Document

下一步只需要修复 MTRP7_R rerun，不需要重做 MTRP7_S ModelB accumulation。

### 目标

```text
在 MTRP7_S root 的 mtrp7_r_rerun/ 下，使用已物化的 isolated_phase_yz Tier A lineage，
真实执行 MTRP7 isolated daily shadow dry-run 等价链路，
生成 daily bridge / OrderIntent / readonly replay / accumulation / validator 产物，
再给出 PASS_READY_FOR_MTRP8_SHADOW_REVIEW 或失败原因。
```

### 允许

```text
读取 mtrp7_r_rerun/isolated_phase_yz
参数化或新增只读 MTRP7 shadow dry-run rerun adapter
生成 mtrp7_r_rerun/rerun_mtrp7/ 下完整 rerun artifact
运行只读 validator
```

### 禁止

```text
重训或调参 ModelB
改 ModelB accumulated daily artifacts
写 formal phase_yz
写 latest / provider / accepted latest
改 production/default registry
改 frontend/API/Agent/daily-auto 主链路
写 formal PriceStore
broker / quick-trade / real order
target_weight / target_position / quantity instruction
使用 Tier B fallback 补数
```

### 验收门槛

```text
rerun_mtrp7/ 不得只包含 manifest/validator/date list；
必须包含与 MTRP7 shadow dry-run 等价的 daily bridge/order/replay/accumulation 证据；
rerun validator 必须可从这些产物推导 PASS_READY_FOR_MTRP8_SHADOW_REVIEW；
outer verdict 才可保持 PASS_TIER_A_LINEAGE_REPAIRED_MTRP7_READY_FOR_MTRP8；
MTRP7_S review verdict 才可升级为 PASS_MODELB_ACCUMULATED_AND_MTRP7_R_READY_FOR_MTRP8。
```

## 11. Command For Executor

```text
请修复 scripts/build_tw_policy_mtrp7_r_clean_daily_tier_a_lineage_and_rerun.py 的 maybe_rerun_mtrp7 分支：
用 mtrp7_r_rerun/isolated_phase_yz 作为 Tier A input，真实生成 MTRP7 shadow dry-run daily bridge / OrderIntent / readonly replay / accumulation 产物；
不要重做 MTRP7_S ModelB accumulation，不要触碰 production/default/latest/provider/frontend/API/Agent/PriceStore/broker/order。
```

## 12. Final Decision

```text
verdict = PASS_MODELB_ACCUMULATED_MTRP7_R_NEEDS_REPAIR
modelb_built_day_count = 10
clean_tier_a_rerun_eligible_day_count = 13
modelb_accumulation_pass = true
mtrp7_r_lineage_materialized = true
mtrp7_r_true_shadow_dry_run_rerun = false
production_scope_clean = true
next_step = repair MTRP7_R true rerun only
```
