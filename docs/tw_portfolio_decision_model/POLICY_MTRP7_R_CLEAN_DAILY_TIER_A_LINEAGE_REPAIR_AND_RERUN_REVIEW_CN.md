---
created_at: 2026-06-28T20:05:00+00:00
status: review
phase: MTRP7_R_CLEAN_DAILY_TIER_A_LINEAGE_REPAIR_AND_RERUN
reviewer: MTRP7_R
strategy_candidate: top50_hold_rank_buffer_100
readonly_only: true
simulation_only: true
production_allowed: false
production_ready: false
default_switch_allowed: false
verdict: STOP_INSUFFICIENT_CLEAN_DAILY_TIER_A_INPUTS
next_step: open_mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build
---

# POLICY_MTRP7_R_CLEAN_DAILY_TIER_A_LINEAGE_REPAIR_AND_RERUN_REVIEW_CN

## 1. Verdict

```text
STOP_INSUFFICIENT_CLEAN_DAILY_TIER_A_INPUTS
```

审查结论：

```text
MTRP7_R builder、产物目录和 rerun 证据支持 STOP。
clean daily Tier A eligible day 只有 3 天：
2026-05-07, 2026-06-15, 2026-06-17。

最低门槛是 5 个同日具备 ModelA + ModelB + price 的 clean daily Tier A trading days。
因此不得进入 MTRP8，不得使用 Tier B fallback 补数，不得写 isolated_phase_yz 或 rerun_mtrp7，不得触碰 production/default/latest/provider/frontend/API/Agent/PriceStore。
```

## 2. 审查依据

已按要求阅读并用于审查：

- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-model-onboarding/SKILL.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP7_R_CLEAN_DAILY_TIER_A_LINEAGE_REPAIR_AND_RERUN_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP7_R_CLEAN_DAILY_TIER_A_LINEAGE_REPAIR_AND_RERUN_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP7_ISOLATED_DAILY_SHADOW_DRY_RUN_REVIEW_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`

同时按 model/strategy skill 要求补读：

- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

审查对象：

- `scripts/build_tw_policy_mtrp7_r_clean_daily_tier_a_lineage_and_rerun.py`
- `data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_r_clean_daily_tier_a_lineage_repair_and_rerun/`

## 3. Findings

### Critical

无。

### High

1. clean daily Tier A 输入不足 5 天，STOP 成立。

   证据：

   ```text
   validator_report.status = stop
   validator_report.verdict = STOP_INSUFFICIENT_CLEAN_DAILY_TIER_A_INPUTS
   validator_report.eligible_day_count = 3
   validator_report.eligible_dates =
     2026-05-07
     2026-06-15
     2026-06-17
   validator_report.minimum_clean_daily_tier_a_days_required = 5
   validator_report.minimum_clean_daily_tier_a_days_pass = false
   validator_report.blockers = tier_a_clean_daily_lineage_less_than_5_days
   ```

2. 缺口主要是同日 ModelB LTR top50 不足，而不是 ModelA 或 price。

   独立汇总 `tier_a_lineage_eligibility.csv`：

   ```text
   eligibility rows = 14
   model_a_ready = 14/14
   price next_open + same_day_mark ready = 14/14
   model_b_ready = 3/14
   blocker_counts = missing_model_b: 11
   ```

   同日可用 ModelB top50 只有：

   ```text
   2026-05-07: existing_e4_daily_ltr_top50, rows=50
   2026-06-15: existing_daily_ltr_rerank_top50, rows=50, status=ready, pit_pass=true
   2026-06-17: formal_phase_yz_model_b_yz2, rows=50
   ```

   直接文件检查也一致：

   ```text
   daily_ltr_rerank_*_top50.csv = 2 files
     daily_ltr_rerank_2026-06-15_top50.csv rows=50 status=ready pit_pass=true
     daily_ltr_rerank_2026-06-17_top50.csv rows=50 status=ready pit_pass=true

   e4_daily_ltr_top50_rerank_*.csv = 1 file
     e4_daily_ltr_top50_rerank_2026-05-07.csv rows=50

   formal model_b_yz2 signals.csv = 1 file
     2026-06-17 rows=50
   ```

### Medium

1. >=5 天分支的 `maybe_rerun_mtrp7` 当前只写 `rerun_mtrp7/manifest.json` 并标记 `simulated_isolated_rerun_manifest_only`，不是实际调用原 MTRP7 builder。

   这不影响本次 STOP 判定，因为本次 `can_build=false`，代码未进入该分支，且没有写 `rerun_mtrp7/` 子目录。若后续 MTRP7_S 补齐 >=5 天后回到 MTRP7_R，需把 rerun gate 修成真实 isolated MTRP7 rerun，而不是 manifest-only pass。

2. `source_inventory.csv` 足够大并覆盖允许 source roots，但部分 source archive 文件名会被宽松日期 regex 解析成异常日期。这没有进入 eligibility，因为 eligibility 使用聚合后的 ModelA/ModelB/price sources；本次关键结论由 `tier_a_lineage_eligibility.csv` 和直接 top50 文件检查支撑。

### Low

1. 脚本 import 了未使用的 `shutil`。非功能问题，不影响 STOP。

2. 当前 worktree 有大量既有 dirty/untracked 项，含 frontend/API/daily 相关路径。审查未 revert，也未把无关变更计入 MTRP7_R 结论。

## 4. STOP Gate 审查

通过，STOP 正确。

`rerun_mtrp7_summary.json`：

```text
rerun_performed = false
rerun_status = not_run
rerun_verdict = STOP_INSUFFICIENT_CLEAN_DAILY_TIER_A_INPUTS
eligible_day_count = 3
tier_b_fallback_used = false
```

`manifest.json`：

```text
verdict = STOP_INSUFFICIENT_CLEAN_DAILY_TIER_A_INPUTS
eligible_day_count = 3
tier_b_fallback_used = false
production_allowed = false
production_ready = false
default_switch_allowed = false
formal_phase_yz_write_allowed = false
latest_pointer_mutation_allowed = false
provider_publish_allowed = false
accepted_latest_switch_allowed = false
broker_authorized = false
```

产物目录检查：

```text
required root files = 13/13 present
isolated_phase_yz directory = absent
rerun_mtrp7 directory = absent
```

## 5. Tier B Fallback 审查

通过。

未发现使用 Tier B fallback 补数：

```text
validator_report.tier_b_fallback_used = false
rerun_mtrp7_summary.tier_b_fallback_used = false
rerun_mtrp7_validator_report.tier_b_fallback_used = false
```

脚本层面：

```text
build_eligibility_rows 只按同一 signal_asof 聚合 model_a、model_b、price。
can_build = len(eligible_dates) >= 5。
len(eligible_dates) < 5 时 maybe_rerun_mtrp7 返回 not_run/STOP。
```

## 6. 隔离与生产越界审查

通过。

`forbidden_scope_audit.csv` 共 20 项，全部：

```text
performed = False
status = pass
```

覆盖：

```text
production_default_registry_change
production_registry_selectable_change
frontend_code_change
api_code_change
agent_code_change
daily_auto_default_path_change
latest_pointer_change
provider_refresh_or_publish
accepted_latest_switch
formal_pricestore_write
broker_connection
quick_trade
real_order
target_weight_instruction
target_position_instruction
quantity_instruction
model_training
model_inference
ltr_recompute
new_return_experiment_or_tuning
```

敏感路径搜索无命中：

```bash
rg -n "mtrp7_r_clean_daily_tier_a_lineage_repair_and_rerun|MTRP7_R_CLEAN_DAILY_TIER_A_LINEAGE_REPAIR_AND_RERUN|top50_hold_rank_buffer_100" \
  configs/tw_modular_registry.yaml \
  configs/tw_product_artifact_registry.yaml \
  configs/tw_replay_window_policy.yaml \
  scripts/run_daily_tw_stock_auto_update.py \
  backend/app/routes \
  backend/app/services \
  backend/scripts/update_tw_stock_daily.py \
  frontend/src
```

结果：

```text
no matches
```

## 7. Forbidden Field 与 PIT 审查

通过，未发现影响本次 STOP 的 forbidden field 使用。

`forbidden_field_audit.csv`：

```text
rows = 17
status pass = 17
status fail = 0
```

其中 `2026-06-15 model_b` source 含 `relevance_10d_top_heavy`，审计记录为：

```text
used_for_strategy_input = False
status = pass
details = Source inventory audit. Isolated output only keeps ModelSignal core fields when materialized.
```

本次没有 materialize `isolated_phase_yz`，也没有进入 rerun，因此该 source forbidden 字段没有进入 OrderIntent/Replay 输入链路。后续若 >=5 天后物化 isolated ModelSignal，应重新抽查输出 `signals.csv` 只保留合同 core fields。

`pit_available_at_audit.csv`：

```text
rows = 3
all status = pass
available_at_lte_signal_asof = True
pit_pass = True
```

## 8. 验证命令

已运行只读/安全命令：

```bash
python -m py_compile scripts/build_tw_policy_mtrp7_r_clean_daily_tier_a_lineage_and_rerun.py
python scripts/build_tw_policy_mtrp7_r_clean_daily_tier_a_lineage_and_rerun.py
```

builder rerun 输出：

```text
status = stop
verdict = STOP_INSUFFICIENT_CLEAN_DAILY_TIER_A_INPUTS
eligible_day_count = 3
eligible_dates = 2026-05-07, 2026-06-15, 2026-06-17
output_root = data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_r_clean_daily_tier_a_lineage_repair_and_rerun
```

独立 CSV/JSON 检查包括：

```text
validator_report.json
rerun_mtrp7_summary.json
tier_a_lineage_eligibility.csv
source_inventory.csv
isolated_model_signal_register.csv
price_source_register.csv
lineage_checksum_audit.csv
pit_available_at_audit.csv
forbidden_field_audit.csv
forbidden_scope_audit.csv
required file existence
absence of isolated_phase_yz and rerun_mtrp7 directories
sensitive production path rg search
```

## 9. Next Work Document

下一步应开新路线，例如：

```text
MTRP7_S_CLEAN_DAILY_MODELB_LTR_TOP50_ACCUMULATION_BUILD
```

目标：

```text
专门补 clean daily ModelB LTR top50 accumulation/build，使至少 5 个同日交易日同时具备：
1. ModelA qlib full-rank/top150 signal，rows >= 100，目标 150；
2. ModelB existing clean daily LTR top50 signal，rows = 50；
3. readonly price source，next_open + same-day mark 可用；
4. source lineage/checksum/PIT/available_at 可追踪；
5. forbidden fields 不进入 ModelSignal core / strategy input / replay input。
```

必须保持：

```text
不得降级 Tier B；
不得用 Tier B fallback 补数；
不得新训练、新 inference、LTR recompute，除非 coordinator 新路线明确授权并完成合同审查；
不得写 formal phase_yz/default/latest/provider/frontend/API/Agent/PriceStore；
不得 broker/order/quick-trade/target/quantity；
不得用 replay return 或 future label 参与 ranking 或 eligibility。
```

MTRP7_S 产出 >=5 天 clean daily Tier A source 后，再回到 MTRP7_R 或后继 repair rerun，要求：

```text
真实物化 isolated_phase_yz；
真实执行 isolated MTRP7 rerun；
rerun verdict 必须为 PASS_READY_FOR_MTRP8_SHADOW_REVIEW；
再由 reviewer 重新审查是否可给 PASS_TIER_A_LINEAGE_REPAIRED_MTRP7_READY_FOR_MTRP8。
```

## 10. Command For Coordinator

```text
请开 MTRP7_S 或类似路线，范围限定为 clean daily ModelB LTR top50 accumulation/build 与同日 Tier A source 补齐。
不得授权 Tier B fallback 进入 MTRP8 或 production/default。
```

## 11. Final Decision

```text
verdict = STOP_INSUFFICIENT_CLEAN_DAILY_TIER_A_INPUTS
clean_daily_tier_a_eligible_days = 3
minimum_required_days = 5
tier_b_fallback_used = false
isolated_phase_yz_written = false
rerun_mtrp7_written = false
production_scope_clean = true
next_step = MTRP7_S clean daily ModelB LTR top50 accumulation/build
```
