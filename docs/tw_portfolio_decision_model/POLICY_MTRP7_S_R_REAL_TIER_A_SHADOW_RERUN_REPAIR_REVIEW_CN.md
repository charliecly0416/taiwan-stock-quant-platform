---
created_at: 2026-06-28T20:45:00Z
status: review
phase: MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR
reviewer: MTRP7_S_R
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
verdict: PASS_REAL_TIER_A_SHADOW_RERUN_READY_FOR_MTRP8
---

# POLICY_MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR_REVIEW_CN

## 1. Verdict

```text
PASS_REAL_TIER_A_SHADOW_RERUN_READY_FOR_MTRP8
```

审查结论：

```text
MTRP7_S_R 已实质修复 MTRP7_R 的 manifest-only blocker：
- repair root 不再只有 manifest / validator / date list；
- 已生成 10 个 clean daily Tier A days 的 daily bridge / OrderIntent / readonly replay shadow artifacts；
- root validator 与独立抽查均确认 input_tier=tier_a_clean_daily_lineage、tier_b_fallback_used=false；
- daily bridge/order/replay registers 均为 10 行且 validator_status=pass；
- OrderIntent 实际 CSV header 不含 execution/quantity/target/cash/nav/equity/broker/PnL/replay_return 等禁用字段；
- replay accounting 字段只出现在 daily_shadow_replay_artifacts，不回流到 bridge signals 或 order_intents；
- same-day mark coverage=1.000000、max_mark_lag_days=0、negative_cash_count=0、duplicate_position_count=0、skip delta 已追踪；
- forbidden_scope_audit 全部 pass，且未发现 repair root 被 configs/backend/frontend/daily-auto 引用。
```

授权进入：

```text
MTRP8 shadow review / readonly exposure design review
```

仍不授权：

```text
production default switch
provider publish / accepted latest switch / latest pointer mutation
formal phase_yz write / formal PriceStore write
frontend/API/Agent/default path 接入
broker / quick-trade / real order
target_weight / target_position / quantity instruction
```

## 2. Documents / Contracts / Skills Read

- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-model-onboarding/SKILL.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP7_S_CLEAN_DAILY_MODELB_LTR_TOP50_ACCUMULATION_BUILD_REVIEW_CN.md`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

## 3. Evidence Checked

审查对象：

- `scripts/build_tw_policy_mtrp7_s_r_real_tier_a_shadow_rerun_repair.py`
- `docs/tw_portfolio_decision_model/POLICY_MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR_EXECUTION_REPORT_CN.md`
- `data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build/mtrp7_s_r_real_tier_a_shadow_rerun_repair/`

Root validator:

```json
{
  "status": "pass",
  "verdict": "PASS_REAL_TIER_A_SHADOW_RERUN_READY_FOR_MTRP8",
  "input_tier": "tier_a_clean_daily_lineage",
  "tier_b_fallback_used": false,
  "covered_shadow_signal_days": 10,
  "daily_bridge_artifact_count": 10,
  "daily_order_intent_artifact_count": 10,
  "daily_shadow_replay_artifact_count": 10,
  "same_day_mark_coverage_ratio": "1.000000",
  "max_mark_lag_days": 0,
  "negative_cash_count": 0,
  "duplicate_position_count": 0,
  "blockers": []
}
```

Covered dates:

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

Root registers:

```text
daily_bridge_artifact_register.csv rows = 10
daily_order_intent_artifact_register.csv rows = 10
daily_shadow_replay_artifact_register.csv rows = 10
shadow_accumulation_register.csv rows = 10
candidate_baseline_skip_delta.csv rows = 10
forbidden_scope_audit.csv rows = 16
bad status rows = 0
```

Daily artifact file count:

```text
repair root maxdepth<=3 file count = 173
daily_bridge_artifacts/{date}/manifest.json signals.csv schema.json lineage_audit.csv forbidden_field_audit.json exist
daily_order_intent_artifacts/{date}/manifest.json order_intents.csv schema.json strategy_decision_audit.csv forbidden_action_audit.json exist
daily_shadow_replay_artifacts/{date}/manifest.json summary.json actions.csv positions.csv skip_reason_audit.csv mark_coverage_audit.csv exist
```

## 4. Findings

### Critical

无。

### High

无。

### Medium

无阻断项。

说明：`order_intents.csv` 包含 `target_holding_count`，该字段在 `ORDER_INTENT_CONTRACT_CN.md` 中属于可选审计字段，不是 `target_position` / `target_weight` / quantity 指令。实际禁用字段 header 检查为 `bad=[]`，因此不阻断。

### Low

1. Daily replay artifacts 使用本阶段轻量 schema：`summary.json`、`actions.csv`、`positions.csv`、`skip_reason_audit.csv`、`mark_coverage_audit.csv`，不是完整 `ReplayResultArtifact` 合同中的 `summary.csv/daily_nav.csv/position_snapshots.csv/...` 文件集。

   本轮 work doc 明确要求的是 `daily_shadow_replay_artifacts/{date}/summary.json/actions.csv/positions.csv/skip_reason_audit.csv/mark_coverage_audit.csv`，审查按本轮 shadow rerun repair 范围放行。MTRP8 若要把结果提升为 formal replay exposure，应另设合同转换或补完整 ReplayResultArtifact。

## 5. Artifact Boundary Checks

### 5.1 Tier A / No Fallback

通过。

```text
manifest.input_tier = tier_a_clean_daily_lineage
manifest.tier_b_fallback_used = false
daily_input_discovery.input_tier = tier_a_clean_daily_lineage
daily_*_register.tier_b_fallback_used = False
```

输入来源为：

```text
s_isolated_modelb_root = data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build/isolated_modelb_yz2
r_isolated_phase_yz_root = data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build/mtrp7_r_rerun/isolated_phase_yz
price_source = data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/stock_price_bridge
formal_pricestore_write = false
```

### 5.2 Daily Bridge

通过。

独立 header/row 检查：

```json
{
  "bridge_files": 10,
  "bad": [],
  "sample_counts": [
    ["2026-06-01", 150, []],
    ["2026-06-02", 150, []],
    ["2026-06-03", 150, []]
  ]
}
```

含义：

```text
10 个 daily bridge signals.csv 均真实存在；
每个抽查日 rows=150；
未发现 replay/accounting/target/quantity/broker 等字段出现在 bridge signals.csv header。
```

### 5.3 Daily OrderIntent

通过。

独立 forbidden header 检查：

```json
{
  "order_files": 10,
  "bad": [],
  "sample_counts": [
    ["2026-06-01", 1, []],
    ["2026-06-02", 2, []],
    ["2026-06-03", 1, []]
  ]
}
```

检查覆盖禁用字段：

```text
execution_date
execution_price
execution_quantity
quantity / shares / lots
target_position / target_weight / allocation_weight
commission / fee / tax
cash / cash_after / nav / equity
daily_return / realized_pnl / unrealized_pnl / replay_return
broker / broker_order_id / order_id / quick_trade
provider_publish_status / accepted_latest_status
```

未发现禁用字段进入实际 `order_intents.csv`。

### 5.4 Daily Shadow Replay

通过。

`daily_shadow_replay_artifact_register.csv`：

```text
rows = 10
same_day_mark_coverage_ratio = 1.000000 for all rows
max_mark_lag_days = 0 for all rows
negative_cash_count = 0 for all rows
duplicate_position_count = 0 for all rows
validator_status = pass for all rows
```

`mark_coverage_audit.csv` 独立检查：

```json
{
  "mark_rows": 20,
  "bad": []
}
```

Replay accounting 字段存在于 replay 层：

```text
daily_shadow_replay_artifacts/*/actions.csv:
quantity, execution_price, commission, tax, cash_after, position_after

daily_shadow_replay_artifacts/*/summary.json:
candidate_cash, baseline_cash, candidate_equity, baseline_equity
```

这些字段未回流到 `daily_bridge_artifacts/*/signals.csv` 或 `daily_order_intent_artifacts/*/order_intents.csv`。

### 5.5 Skip Delta

通过。

```text
candidate_baseline_skip_delta.csv rows = 10
status = tracked for all rows
```

### 5.6 Forbidden Scope

通过。

`forbidden_scope_audit.csv` 覆盖并全部 `performed=False,status=pass`：

```text
training
tuning
model_replacement
new_modelb_scoring
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

敏感路径搜索：

```bash
rg -n "mtrp7_s_r_real_tier_a_shadow_rerun_repair|build_tw_policy_mtrp7_s_r_real_tier_a_shadow_rerun_repair" \
  configs backend frontend scripts/run_daily_tw_stock_auto_update.py backend/scripts/update_tw_stock_daily.py
```

结果：

```text
no matches
```

未发现本 repair root 被生产/default、frontend/API/Agent、daily auto 主链路引用。

## 6. Validation Commands

已运行：

```bash
python -m py_compile scripts/build_tw_policy_mtrp7_s_r_real_tier_a_shadow_rerun_repair.py
```

结果：

```text
pass
```

已只读 rerun builder：

```bash
python scripts/build_tw_policy_mtrp7_s_r_real_tier_a_shadow_rerun_repair.py
```

结果：

```text
status = pass
verdict = PASS_REAL_TIER_A_SHADOW_RERUN_READY_FOR_MTRP8
covered_shadow_signal_days = 10
daily_bridge_artifact_count = 10
daily_order_intent_artifact_count = 10
daily_shadow_replay_artifact_count = 10
same_day_mark_coverage_ratio = 1.000000
negative_cash_count = 0
duplicate_position_count = 0
blockers = []
```

已做独立 CSV/JSON 抽查：

```text
root manifest / validator_report
daily bridge/order/replay file presence
daily bridge signals.csv forbidden header scan
daily order_intents.csv forbidden header scan
daily replay mark coverage audit
register row counts and statuses
forbidden scope audit
sensitive production path rg search
```

## 7. Mainline Compliance

本阶段满足 work doc 验收门槛：

```text
covered_shadow_signal_days >= 5: pass, actual=10
actual clean daily Tier A days expected=10: pass
input_tier=tier_a_clean_daily_lineage: pass
tier_b_fallback_used=false: pass
daily_bridge_artifact_count >= 5: pass, actual=10
daily_order_intent_artifact_count >= 5: pass, actual=10
daily_shadow_replay_artifact_count >= 5: pass, actual=10
all daily bridge validators pass: pass
all daily OrderIntent validators pass: pass
all daily replay/shadow validators pass: pass
same_day_mark_coverage_ratio >= 0.99: pass, actual=1.000000
max_mark_lag_days = 0: pass
negative_cash_count = 0: pass
duplicate_position_count = 0: pass
skip delta tracked: pass
forbidden scope clean: pass
```

## 8. Missing Evidence Or Open Questions

无阻断缺口。

保留说明：

```text
MTRP8 可以审查 shadow review / readonly exposure design。
MTRP8 不应把本 shadow replay 自动升级为 production/default/formal replay/latest。
若需要 formal ReplayResultArtifact，需另开阶段补完整合同文件集与 validator。
```

## 9. Next Work Document

### 9.1 Next Phase

进入：

```text
MTRP8 shadow review / readonly exposure design review
```

### 9.2 MTRP8 Allowed Scope

允许：

```text
读取 MTRP7_S_R repair root
审查 10 天 shadow bridge/order/replay artifacts
设计 readonly exposure / shadow review 展示或报告口径
继续保持 isolated/read-only/simulation-only
```

### 9.3 MTRP8 Forbidden Scope

禁止：

```text
production default switch
provider publish / refresh
accepted latest switch
latest pointer mutation
formal phase_yz write
formal PriceStore write
frontend/API/Agent 默认接入
daily-auto default path mutation
broker / quick-trade / real order
target_weight / target_position / quantity instruction
收益承诺或收益调参
```

## 10. Command For Coordinator

```text
MTRP7_S_R reviewer verdict = PASS_REAL_TIER_A_SHADOW_RERUN_READY_FOR_MTRP8。
可以安排 MTRP8 shadow review / readonly exposure design review。
仍不得授权 production default switch、provider publish、accepted latest switch、formal PriceStore/phase_yz 写入、frontend/API/Agent 默认接入或任何 broker/order/quick-trade。
```

## 11. Final Decision

```text
verdict = PASS_REAL_TIER_A_SHADOW_RERUN_READY_FOR_MTRP8
mtrp7_r_manifest_only_blocker_fixed = true
clean_daily_tier_a_days = 10
daily_bridge_artifact_count = 10
daily_order_intent_artifact_count = 10
daily_shadow_replay_artifact_count = 10
input_tier = tier_a_clean_daily_lineage
tier_b_fallback_used = false
production_scope_clean = true
authorize_mtrp8_shadow_review = true
authorize_production_default_switch = false
```
