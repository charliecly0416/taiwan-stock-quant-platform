---
created_at: 2026-06-28T19:20:00+00:00
status: review
phase: MTRP6_DAILY_FULL_RANK_BRIDGE_AND_CANDIDATE_SHADOW_INTEGRATION_CONTRACT
reviewer: MTRP6
strategy_candidate: top50_hold_rank_buffer_100
baseline_strategy: top50_exit_one_worst_sell
readonly_only: true
simulation_only: true
production_allowed: false
production_ready: false
default_switch_allowed: false
verdict: PASS_READY_FOR_MTRP7_DAILY_SHADOW_DRY_RUN
can_enter_mtrp7: true
---

# POLICY_MTRP6_DAILY_FULL_RANK_BRIDGE_AND_CANDIDATE_SHADOW_INTEGRATION_CONTRACT_REVIEW_CN

## 1. Verdict

```text
PASS_READY_FOR_MTRP7_DAILY_SHADOW_DRY_RUN
```

审查结论：

```text
MTRP6 输出严格保持为 contract / dry-run design package。
未发现 production default registry、frontend/API/Agent、daily auto scripts、latest pointers、provider publish、accepted latest、formal PriceStore 或 broker/order/target/quantity 越界接入。
合同覆盖 daily full-rank bridge、daily candidate OrderIntent、daily readonly replay/shadow artifact、frontend/API/Agent readonly exposure、daily auto dry-run plan、shadow accumulation gate 与 MTRP5 blocker burn-down。
```

本 PASS 只授权进入 `MTRP7 isolated daily shadow dry-run`，不授权 production default switch，不授权 frontend/API/Agent 代码接入，不授权 daily auto 主链路改动，不授权 latest/provider/accepted-latest/PriceStore 写入，不授权 broker/quick-trade/real order。

## 2. 已审查材料

必读治理与策略合同已审查：

- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP6_DAILY_FULL_RANK_BRIDGE_AND_CANDIDATE_SHADOW_INTEGRATION_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP5_GO_NO_GO_CLOSURE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP4_SHADOW_READINESS_PACKAGE_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP6_DAILY_FULL_RANK_BRIDGE_AND_CANDIDATE_SHADOW_INTEGRATION_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

审查对象：

- `scripts/build_tw_policy_mtrp6_daily_shadow_integration_contract.py`
- `data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp6_daily_shadow_integration_contract/`

## 3. Findings

### Critical

无。

### High

无。

### Medium

无 blocking finding。

残余风险：MTRP6 是合同与 dry-run 设计，不是 daily shadow 执行证据。MTRP7 必须实际生成 isolated daily bridge、OrderIntent、readonly replay/shadow artifact，并累计至少 5 个交易日 validator pass 后，才能继续讨论更下游 readonly exposure 或 production default go/no-go。

### Low

当前仓库存在大量既有 dirty worktree 与未跟踪文件，包含 frontend/API/daily 相关文件。审查按 MTRP6 目标文件、候选策略名和敏感生产路径做了独立核对；未将既有无关改动归因给 MTRP6，也未 revert。

## 4. Contract 完整性审查

通过。

MTRP6 artifact root 包含要求的 11 个文件：

```text
manifest.json
daily_full_rank_bridge_contract.csv
daily_candidate_order_intent_contract.csv
daily_shadow_replay_contract.csv
frontend_api_agent_readonly_contract.csv
daily_auto_orchestrator_integration_plan.csv
shadow_accumulation_gate.csv
blocker_burndown_plan.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

`validator_report.json` 显示：

```text
status = pass
verdict = PASS_CONTRACT_READY_FOR_MTRP7_DAILY_SHADOW_DRY_RUN
ready_for_mtrp7_daily_shadow_dry_run = true
production_allowed = false
production_ready = false
default_switch_allowed = false
daily_auto_mutation_allowed = false
frontend_api_agent_mutation_allowed = false
provider_publish_allowed = false
accepted_latest_switch_allowed = false
broker_authorized = false
```

必检项均为 true：

```text
all_required_files_present
daily_bridge_contract_complete
daily_order_intent_contract_complete
daily_shadow_replay_contract_complete
frontend_api_agent_contract_complete
shadow_accumulation_gate_complete
blocker_burndown_plan_complete
production_allowed_false
default_switch_allowed_false
daily_auto_mutation_allowed_false
frontend_api_agent_mutation_allowed_false
provider_publish_allowed_false
accepted_latest_switch_allowed_false
broker_authorized_false
target_weight_position_forbidden
```

## 5. 范围与越界审查

通过，未发现越界。

`scripts/build_tw_policy_mtrp6_daily_shadow_integration_contract.py` 的写入范围为：

```text
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp6_daily_shadow_integration_contract/
docs/tw_portfolio_decision_model/POLICY_MTRP6_DAILY_FULL_RANK_BRIDGE_AND_CANDIDATE_SHADOW_INTEGRATION_CONTRACT_EXECUTION_REPORT_CN.md
```

`forbidden_scope_audit.csv` 全部为：

```text
performed = false
status = pass
```

覆盖并禁止：

```text
production_default_registry_change
production_registry_selectable_change
frontend_code_change
api_code_change
agent_code_change
daily_auto_script_change
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
new_return_experiment
```

敏感路径搜索未发现 `top50_hold_rank_buffer_100` 或 `mtrp6_daily_shadow_integration_contract` 接入以下生产链路：

```text
configs/tw_modular_registry.yaml
configs/tw_product_artifact_registry.yaml
configs/tw_replay_window_policy.yaml
scripts/run_daily_tw_stock_auto_update.py
backend/app/routes
backend/app/services
backend/scripts/update_tw_stock_daily.py
frontend/src
```

既有 `configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml` 保持：

```text
production_allowed: false
frontend_selectable: false
production_default: false
not_order: true
not_target_position: true
not_investment_advice: true
```

## 6. 五项审查重点结论

1. 是否严格只做合同/dry-run 设计：

   通过。builder 只生成合同包和执行报告；artifact manifest、validator 与 forbidden audit 均声明 production/default/latest/provider/frontend/API/Agent/daily mutation 为 false。

2. 是否覆盖 daily full-rank bridge、candidate OrderIntent、readonly replay/shadow、frontend/API/Agent readonly exposure、daily auto dry-run plan、shadow gate、blocker burn-down：

   通过。对应文件分别为 `daily_full_rank_bridge_contract.csv`、`daily_candidate_order_intent_contract.csv`、`daily_shadow_replay_contract.csv`、`frontend_api_agent_readonly_contract.csv`、`daily_auto_orchestrator_integration_plan.csv`、`shadow_accumulation_gate.csv`、`blocker_burndown_plan.csv`。

3. 是否完整禁止 broker/quick-trade/real order/target/quantity、训练/推理/LTR recompute、future return/label、research MTRC runtime input：

   通过。OrderIntent 合同禁止 execution/quantity/shares/lots/cash/nav/equity/target/broker 字段；bridge 合同禁止 research MTRC runtime input、training/inference/LTR recompute、future return/label、replay return as input；forbidden scope audit 禁止 broker、quick-trade、real order、target 与 quantity instruction。

4. blocker burn-down 是否与 MTRP5 blockers 一一对应：

   通过。`blocker_burndown_plan.csv` 覆盖 MTRP5 七项 blocker：

   ```text
   source_lineage_still_repackaged_from_research_only_broad_reference
   window_only_2026_01_02_to_2026_05_07
   no_daily_auto_generation_for_candidate
   no_live_latest_shadow_accumulation
   no_frontend/API/Agent readonly integration
   candidate_skipped_count_higher_than_baseline
   no_production_default_switch_authorized
   ```

   七项 `production_switch_status` 均为 `blocked`，没有把 MTRP6 合同定义误写成 production blocker 已关闭。

5. 是否足够进入 MTRP7 isolated daily shadow dry-run：

   通过。MTRP6 合同足以约束 MTRP7 的 isolated dry-run：daily bridge、OrderIntent、replay、readonly exposure、5 trading days accumulation、checksum/source lineage、skip delta、forbidden wording 和 no production mutation gate 都已有明确 stop condition。

## 7. 验证命令

已运行：

```bash
python -c "import py_compile; py_compile.compile('scripts/build_tw_policy_mtrp6_daily_shadow_integration_contract.py', cfile='/tmp/mtrp6_daily_shadow_integration_contract.pyc', doraise=True); print('py_compile_ok')"
python scripts/build_tw_policy_mtrp6_daily_shadow_integration_contract.py
```

结果：

```text
py_compile_ok
verdict = PASS_CONTRACT_READY_FOR_MTRP7_DAILY_SHADOW_DRY_RUN
output_root = data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp6_daily_shadow_integration_contract
```

还检查了：

```text
manifest.json
validator_report.json
CSV 表头与核心内容
forbidden_scope_audit.csv
blocker_burndown_plan.csv
daily_auto_orchestrator_integration_plan.csv
敏感生产路径候选策略命中
```

## 8. MTRP7 Next Work Control

允许进入：

```text
MTRP7 isolated daily shadow dry-run
```

MTRP7 必须保持：

```text
readonly_only = true
simulation_only = true
production_allowed = false
default_switch_allowed = false
daily_auto_mutation_allowed = false
frontend_api_agent_mutation_allowed = false
provider_publish_allowed = false
accepted_latest_switch_allowed = false
broker_authorized = false
```

MTRP7 executor 不得修改 production default registry、frontend/API/Agent、daily auto default path、latest pointers、provider publish、accepted latest 或 formal PriceStore。MTRP7 只允许 isolated dry-run 生成候选 bridge、OrderIntent、readonly replay/shadow artifacts 和 shadow accumulation register，并必须保留 source lineage、checksum、skip reason delta 与 forbidden wording audit。

## 9. Final Decision

```text
verdict = PASS_READY_FOR_MTRP7_DAILY_SHADOW_DRY_RUN
can_enter_mtrp7 = true
production_ready = false
production_allowed = false
default_switch_authorized = false
```

MTRP6 通过；授权进入 MTRP7 isolated daily shadow dry-run。所有 production/default/latest/provider/frontend/API/Agent/daily/PriceStore/broker/order/target/quantity 边界继续阻断。
