---
created_at: 2026-06-28T19:35:00+00:00
status: review
phase: MTRP7_ISOLATED_DAILY_SHADOW_DRY_RUN
reviewer: MTRP7
strategy_candidate: top50_hold_rank_buffer_100
baseline_strategy: top50_exit_one_worst_sell
readonly_only: true
simulation_only: true
production_allowed: false
production_ready: false
default_switch_allowed: false
verdict: PASS_MECHANICS_READY_LINEAGE_BLOCKED
can_enter_production_default: false
can_enter_mtrp8_full_shadow_ready: false
next_step: repair_clean_daily_tier_a_lineage
---

# POLICY_MTRP7_ISOLATED_DAILY_SHADOW_DRY_RUN_REVIEW_CN

## 1. Verdict

```text
PASS_MECHANICS_READY_LINEAGE_BLOCKED
```

审查结论：

```text
MTRP7 isolated daily shadow dry-run mechanics 通过。
已真实生成 daily bridge / OrderIntent / replay-shadow artifacts，并覆盖 43 个交易 signal dates。

但本次输入是 Tier B repackaged research lineage mechanics-only fallback。
Tier A clean daily lineage 只有 1 个 eligible day，少于 MTRP7 要求的 5 个交易日。
因此不得声明 production-ready，不得声明 MTRP8 full shadow-ready，不得接入 production/default/daily auto/frontend/API/Agent/latest/provider/PriceStore。
```

允许的下一步不是 production/default 接入，而是：

```text
repair clean daily Tier A lineage:
daily ModelA 100/150-row qlib signal + daily ModelB top50 LTR signal + readonly daily price source
```

## 2. 已审查材料

必读治理、主线和合同已阅读并用于审查：

- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP7_ISOLATED_DAILY_SHADOW_DRY_RUN_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP7_ISOLATED_DAILY_SHADOW_DRY_RUN_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP6_DAILY_FULL_RANK_BRIDGE_AND_CANDIDATE_SHADOW_INTEGRATION_CONTRACT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP5_GO_NO_GO_CLOSURE_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

审查对象：

- `scripts/build_tw_policy_mtrp7_isolated_daily_shadow_dry_run.py`
- `data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_isolated_daily_shadow_dry_run/`

## 3. Findings

### Critical

无。

### High

1. Tier A clean daily lineage 未达到 MTRP7 production-lineage 门槛。

   证据：

   ```text
   validator_report.input_tier = tier_b_repackaged_research_lineage_mechanics_only
   validator_report.tier_a_eligible_day_count = 1
   validator_report.blockers =
     tier_a_clean_daily_lineage_less_than_5_days
     production_lineage_blocker_true_for_tier_b_repackaged_research_lineage
   ```

   影响：

   ```text
   mechanics 可接受；
   production lineage 不可接受；
   不允许进入 production/default；
   不允许声称 MTRP8 full shadow-ready。
   ```

### Medium

1. 本次 daily artifacts 是从既有 MTRP2_R/P3 audited broad reference 按日拆分和重包装，不是 clean daily auto source 的正式产物。

   该行为符合 MTRP7 Tier B fallback 允许范围，但必须继续保留 `production_lineage_blocker=true`。

### Low

1. 当前仓库存在大量既有 dirty/untracked worktree 项，包含 frontend/API/daily 相关路径。审查只按 MTRP7 目标脚本、目标 artifact root 和敏感生产路径命中检查，不 revert、不归因无关改动。

## 4. Artifact 真实性与覆盖

通过。

root 必需文件 13/13 存在：

```text
manifest.json
daily_input_discovery.csv
daily_bridge_artifact_register.csv
daily_order_intent_artifact_register.csv
daily_shadow_replay_artifact_register.csv
shadow_accumulation_register.csv
candidate_baseline_skip_delta.csv
lineage_checksum_audit.csv
price_mark_coverage_audit.csv
readonly_wording_audit.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

daily artifact 计数：

```text
daily_bridge_artifacts = 43
daily_order_intent_artifacts = 43
daily_shadow_replay_artifacts = 43
covered_signal_date_start = 2026-01-02
covered_signal_date_end = 2026-05-05
minimum_shadow_days_required = 5
minimum_shadow_days_pass = true
```

抽样检查：

```text
2026-01-02: bridge/order/replay required files all present
2026-05-05: bridge/order/replay required files all present
```

覆盖日期来自 source bridge / replay 的交易日序列；未发现用非交易日伪造补数。

## 5. Bridge 审查

通过。

独立抽查全部 43 个 daily bridge `signals.csv`：

```text
bad_bridge_days = 0
row_count >= 100: true
top50_rows = 50: true
non_top50_visibility_rows >= 50: true
top50 buy_score populated: true
non_top50 buy_score blank: true
available_at <= signal_asof: true
```

样例：

```text
2026-01-02 rows=150 top50=50 non_top50=100
2026-01-05 rows=149 top50=50 non_top50=99
2026-05-05 rows=150 top50=50 non_top50=100
```

lineage 标记清楚：

```text
input_tier = tier_b_repackaged_research_lineage_mechanics_only
source_lineage_warning = existing_audited_broad_reference_repackaged_for_production_candidate_readiness
production_lineage_blocker = true
```

## 6. OrderIntent 审查

通过。

独立抽查全部 43 个 daily OrderIntent `order_intents.csv`：

```text
bad_order_days = 0
buy_count <= 1: true
sell_count <= 1: true
non_top50_buy_count = 0
invalid_action_count = 0
```

未出现禁止字段：

```text
execution_date
execution_price
execution_quantity
quantity
shares
lots
cash
nav
equity
target_weight
target_position
broker
broker_order_id
order_id
quick_trade
daily_return
realized_pnl
unrealized_pnl
replay_return
```

样例 `2026-01-02/order_intents.csv` 表头只包含 signal/intent/strategy/rank/audit/readonly 字段，不包含 target、quantity、broker、execution、cash、NAV、equity。

## 7. Replay / Shadow 审查

通过，且 replay cash/NAV/PnL 未回流到 bridge/order input。

独立抽查全部 43 个 daily replay `summary.json`：

```text
bad_replay_days = 0
validator_status = pass
same_day_mark_coverage_ratio = 1.0
negative_cash_count = 0
duplicate_position_count = 0
execution_price = next_open
execution_date_policy = next_tradeable_day_after_signal_date
candidate_baseline_same_day_comparison = true
```

Replay artifact 中允许出现：

```text
candidate_equity
baseline_equity
candidate_minus_baseline_equity
cash / NAV / position / action accounting fields
```

但 bridge `signals.csv` 与 OrderIntent `order_intents.csv` 未包含 cash/NAV/equity/PnL/quantity/target/broker/execution 字段，未发现 replay 结果回流到 bridge/order input。

## 8. Evidence Gate 审查

通过。

`validator_report.json` 显示：

```text
status = pass
verdict = PASS_MECHANICS_READY_LINEAGE_BLOCKED
all_required_files_present = true
minimum_shadow_days_pass = true
all_daily_bridge_validators_pass = true
all_daily_order_intent_validators_pass = true
all_daily_shadow_replay_validators_pass = true
lineage_checksum_audit_pass = true
skip_delta_tracked = true
price_mark_coverage_pass = true
readonly_wording_pass = true
forbidden_scope_clean = true
```

root audit 证据：

```text
shadow_accumulation_register.csv: 43 rows, all pass
candidate_baseline_skip_delta.csv: 43 rows, all tracked
lineage_checksum_audit.csv: 13 rows, all pass
price_mark_coverage_audit.csv: 86 rows, all pass
readonly_wording_audit.csv: 9 rows, all pass
forbidden_scope_audit.csv: 20 rows, all pass
```

`readonly_wording_audit.csv` 明确通过：

```text
readonly_only = true
simulation_only = true
production_allowed = false
production_ready = false
default_switch_allowed = false
not_order = true
not_target_position = true
not_investment_advice = true
tier_b_not_production_ready = true
```

## 9. 越界审查

通过，未发现 MTRP7 越界接入。

builder 写入范围审查：

```text
OUT_ROOT =
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_isolated_daily_shadow_dry_run/

REPORT_PATH =
docs/tw_portfolio_decision_model/POLICY_MTRP7_ISOLATED_DAILY_SHADOW_DRY_RUN_EXECUTION_REPORT_CN.md
```

本审查新增：

```text
docs/tw_portfolio_decision_model/POLICY_MTRP7_ISOLATED_DAILY_SHADOW_DRY_RUN_REVIEW_CN.md
```

敏感路径搜索：

```text
rg -n "top50_hold_rank_buffer_100|mtrp7_isolated_daily_shadow_dry_run" \
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

`forbidden_scope_audit.csv` 全部为：

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

## 10. 验证命令

已运行只读/安全验证命令：

```bash
python -m py_compile scripts/build_tw_policy_mtrp7_isolated_daily_shadow_dry_run.py
python scripts/build_tw_policy_mtrp7_isolated_daily_shadow_dry_run.py
```

builder rerun 结果：

```text
verdict = PASS_MECHANICS_READY_LINEAGE_BLOCKED
status = pass
input_tier = tier_b_repackaged_research_lineage_mechanics_only
covered_shadow_signal_days = 43
output_root = data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_isolated_daily_shadow_dry_run
```

还运行了独立结构检查：

```text
root required files present
daily artifact directory counts
validator_report gates
all daily bridge row/top50/non-top50/available_at checks
all daily OrderIntent forbidden-field and max buy/sell checks
all daily replay mark/cash/duplicate checks
forbidden scope audit
readonly wording audit
sensitive production path search
```

## 11. Next Work Control

不得进入：

```text
production default switch
production registry selectable/default 修改
frontend/API/Agent 接入
daily auto 主链路/default path 接入
latest pointer 修改
provider refresh / publish
accepted latest switch
formal PriceStore write
broker / quick-trade / real order
target_weight / target_position / quantity instruction
MTRP8 full shadow-ready 声明
```

允许的后续工作仅限：

```text
repair clean daily Tier A lineage
```

修复目标：

```text
至少 5 个真实交易日具备：
1. daily ModelA qlib full-rank visibility signal，rows >= 100，最好 150；
2. daily ModelB top50 LTR signal，rows = 50；
3. readonly daily price source / next_open / same-day close mark；
4. source lineage / checksum / available_at <= signal_asof 可追踪；
5. non-top50 行只提供 qlib full_qlib_rank visibility，不参与 buy ranking。
```

完成 Tier A repair 后，应重新运行 isolated daily shadow dry-run，并由 reviewer 重新判定是否可给：

```text
PASS_READY_FOR_MTRP8_SHADOW_REVIEW
```

在此之前，当前 MTRP7 只能作为 mechanics-ready evidence。

## 12. Final Decision

```text
verdict = PASS_MECHANICS_READY_LINEAGE_BLOCKED
mechanics_ready = true
production_lineage_ready = false
production_ready = false
default_switch_authorized = false
mtrp8_full_shadow_ready = false
next_step = repair_clean_daily_tier_a_lineage
```
