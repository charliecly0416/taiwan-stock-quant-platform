---
created_at: 2026-06-29T02:55:00Z
status: review
phase: MTRP8_SHADOW_REVIEW_AND_READONLY_EXPOSURE_DESIGN
reviewer: MTRP8_SHADOW_REVIEW_AND_READONLY_EXPOSURE_DESIGN
strategy_candidate: top50_hold_rank_buffer_100
readonly_only: true
simulation_only: true
production_allowed: false
production_ready: false
default_switch_allowed: false
frontend_api_agent_code_change_allowed: false
daily_auto_default_change_allowed: false
latest_pointer_mutation_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
formal_pricestore_write_allowed: false
broker_authorized: false
verdict: PASS_READY_FOR_MTRP9_READONLY_EXPOSURE_IMPLEMENTATION_CONTRACT
---

# Review Opinion And Next Work Document

## 1. Verdict

```text
PASS_READY_FOR_MTRP9_READONLY_EXPOSURE_IMPLEMENTATION_CONTRACT
```

独立审查结论：

```text
MTRP8 是 readonly shadow exposure design / review package。
未发现 production/default registry、frontend/API/Agent 代码、daily auto default path、latest pointer、provider publish/refresh、accepted latest、formal PriceStore、broker/order/quick-trade 越界接入。
MTRP8 正确继承 MTRP6 readonly exposure contract 与 MTRP7_S_R clean Tier A shadow evidence。
validator gate 建立在 10 个 clean Tier A shadow days、no Tier B fallback、daily bridge/order/replay counts、same-day mark coverage、skip delta tracked、forbidden scope clean 上。
MTRP8 产出的 readonly_exposure_index / frontend_api_agent_exposure_contract / artifact_citation_map / production_blocker_register 足够作为 MTRP9 readonly exposure implementation contract 输入。
```

本 PASS 只授权进入：

```text
MTRP9_READONLY_EXPOSURE_IMPLEMENTATION_CONTRACT
```

不授权 production default switch，不授权 paper apply，不授权 frontend/API/Agent code change，不授权 daily auto 主链路/default path 改动，不授权 latest/provider/accepted-latest/PriceStore 写入，不授权 broker/order/quick-trade，不授权目标仓位、目标权重或数量类交易指令。

## 2. Findings

### Critical

无。

### High

无。

### Medium

无 blocking finding。

说明：`readonly_exposure_index.csv` 包含 `candidate_equity`、`baseline_equity` 和差值字段。这些字段来自 MTRP7_S_R readonly shadow replay observation，只能作为 shadow observation display 输入，不得被解释为收益承诺、默认切换依据、paper apply 输入或真实交易建议。MTRP8 的 `frontend_api_agent_exposure_contract.csv` 已要求 GET-only readonly、not default、禁止 recommendation / guaranteed return / investment advice wording，因此不阻断 MTRP9 合同阶段。

### Low

当前 worktree 存在大量既有 dirty / untracked 文件，含 frontend/API/daily 相关路径。审查按本轮 MTRP8 builder、MTRP8 artifact root、执行报告和敏感路径搜索独立核对；未将既有无关改动归因给 MTRP8，也未 revert。

## 3. Documents / Contracts / Skills Read

- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-model-onboarding/SKILL.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP8_SHADOW_REVIEW_AND_READONLY_EXPOSURE_DESIGN_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP8_SHADOW_REVIEW_AND_READONLY_EXPOSURE_DESIGN_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP6_DAILY_FULL_RANK_BRIDGE_AND_CANDIDATE_SHADOW_INTEGRATION_CONTRACT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR_REVIEW_CN.md`
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
- `configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml`

## 4. Evidence Checked

审查对象：

- `scripts/build_tw_policy_mtrp8_shadow_review_readonly_exposure_design.py`
- `data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp8_shadow_review_readonly_exposure_design/`
- `docs/tw_portfolio_decision_model/POLICY_MTRP8_SHADOW_REVIEW_AND_READONLY_EXPOSURE_DESIGN_EXECUTION_REPORT_CN.md`

MTRP8 artifact root 包含全部要求文件：

```text
manifest.json
readonly_exposure_index.csv
shadow_review_gate.csv
frontend_api_agent_exposure_contract.csv
artifact_citation_map.csv
production_blocker_register.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

`validator_report.json` 独立复核结果：

```json
{
  "status": "pass",
  "verdict": "PASS_READY_FOR_MTRP9_READONLY_EXPOSURE_IMPLEMENTATION_CONTRACT",
  "ready_for_mtrp9_readonly_exposure_implementation_contract": true,
  "production_default_switch_authorized": false,
  "frontend_api_agent_code_change_authorized": false,
  "paper_portfolio_apply_authorized": false,
  "covered_shadow_signal_days": 10,
  "gate_pass": true,
  "forbidden_scope_clean": true,
  "citation_complete": true,
  "readonly_exposure_rows": 10,
  "open_production_blockers": 4,
  "blockers": []
}
```

`manifest.json` 明确：

```text
readonly_only = true
simulation_only = true
production_allowed = false
production_ready = false
default_switch_allowed = false
frontend_api_agent_code_change_allowed = false
daily_auto_default_change_allowed = false
latest_pointer_mutation_allowed = false
provider_publish_allowed = false
accepted_latest_switch_allowed = false
broker_authorized = false
covered_shadow_signal_days = 10
input_tier = tier_a_clean_daily_lineage
tier_b_fallback_used = false
```

## 5. MTRP6 / MTRP7_S_R Inheritance

通过。

MTRP8 读取并继承：

- MTRP6 readonly exposure contract：`data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp6_daily_shadow_integration_contract/frontend_api_agent_readonly_contract.csv`
- MTRP6 shadow gate：`data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp6_daily_shadow_integration_contract/shadow_accumulation_gate.csv`
- MTRP7_S_R clean Tier A validator：`data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build/mtrp7_s_r_real_tier_a_shadow_rerun_repair/validator_report.json`
- MTRP7_S_R accumulation / skip / bridge / order / replay registers。

`shadow_review_gate.csv` 全部 pass：

```text
mtrp7_s_r_validator_pass = True
minimum_clean_tier_a_shadow_days = 10, threshold >=5
tier_a_input_no_tier_b_fallback = tier_a=True;tier_b_fallback=False
daily_bridge_order_replay_artifacts_present = bridge=10;order=10;replay=10
same_day_mark_coverage = 1.000000, threshold >=0.99
mark_lag_cash_position_integrity = max_mark_lag_days=0;negative_cash=0;duplicate_positions=0
skip_delta_tracked = 10 rows and all tracked
mtrp6_readonly_exposure_contract_pass = True
```

## 6. Validator Basis Review

通过。

MTRP8 validator 不是仅检查文件存在；它实质读取 MTRP6 / MTRP7_S_R 的 validator 与 register，并建立以下 gate：

- MTRP7_S_R validator status pass。
- Clean Tier A shadow days = 10。
- `input_tier=tier_a_clean_daily_lineage`。
- `tier_b_fallback_used=false`。
- Daily bridge / OrderIntent / readonly replay register counts 均为 10。
- Same-day mark coverage ratio = 1.000000。
- `max_mark_lag_days=0`、`negative_cash_count=0`、`duplicate_position_count=0`。
- `candidate_baseline_skip_delta.csv` 为 10 行且 status tracked/pass。
- MTRP6 readonly exposure contract 与 shadow gate 均 pass。
- Citation map complete。
- Forbidden scope clean。

## 7. MTRP9 Input Sufficiency

通过，足够作为 MTRP9 implementation contract 的输入。

`readonly_exposure_index.csv`：

- 10 行，对应 2026-06-01 至 2026-06-12 的 clean shadow signal days。
- 每行均为 `display_status=readonly_shadow_observation_only`。
- 每行均标记 `not_default=True`、`not_order=True`、`not_target_position=True`、`not_investment_advice=True`。
- 提供 candidate / baseline shadow observation 与 skip count，用于只读展示合同设计。

`frontend_api_agent_exposure_contract.csv`：

- 要求 GET-only readonly display。
- 要求显示为 shadow candidate / observation，不得显示为 current default strategy。
- 禁止 POST/PUT/PATCH/DELETE、paper apply、broker、quick_trade、default switch。
- 禁止 recommendation、guaranteed return、investment advice wording。
- 要求 display / Agent context 引用 artifact citations，禁止 frontend direct-read experiment CSV 或本地重算。

`artifact_citation_map.csv`：

- 覆盖 MTRP8 manifest。
- 覆盖 MTRP7_S_R validator。
- 覆盖 MTRP7_S_R shadow accumulation register。
- 覆盖 MTRP7_S_R daily OrderIntent register。
- 覆盖 MTRP6 readonly contract。
- 覆盖 strategy dependency yaml。

`production_blocker_register.csv`：

- 保留 `no_readonly_exposure_implementation_contract_yet`。
- 保留 `frontend_api_agent_code_not_authorized_in_mtrp8`。
- 保留 `production_default_switch_not_authorized`。
- 保留 `paper_portfolio_apply_not_authorized`。
- 4 项均为 open，且 `production_switch_blocking=True`。

结论：MTRP9 可以基于这些文件继续写 isolated GET-only readonly exposure implementation contract；不得把这些文件解释为 production switch、paper apply 或实盘/模拟账户执行授权。

## 8. Forbidden Actions Audit

通过。

`forbidden_scope_audit.csv` 全部为：

```text
performed = False
status = pass
```

覆盖范围包括：

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
formal_phase_yz_write
formal_pricestore_write
broker_connection
quick_trade
real_order
target_weight_instruction
target_position_instruction
quantity_instruction
model_training
model_tuning
score_recompute
return_filtering_or_tuning
```

敏感路径搜索：

```bash
rg -n "mtrp8_shadow_review_readonly_exposure_design|build_tw_policy_mtrp8_shadow_review_readonly_exposure_design" configs backend frontend scripts docs/tw_portfolio_decision_model
```

结果只命中：

```text
MTRP8 work doc
MTRP8 execution report
MTRP8 builder 自身
```

未发现 MTRP8 artifact root 被 production registry、backend/API、frontend、daily auto 主链路引用。

另查：

```bash
rg -n "top50_hold_rank_buffer_100" configs/tw_product_artifact_registry.yaml configs/tw_modular_registry.yaml scripts/run_daily_tw_stock_auto_update.py backend frontend
```

结果无命中，未发现候选策略进入 product registry、modular registry、daily auto、backend 或 frontend。

## 9. Validation Commands

已运行：

```bash
python -m py_compile scripts/build_tw_policy_mtrp8_shadow_review_readonly_exposure_design.py
python scripts/build_tw_policy_mtrp8_shadow_review_readonly_exposure_design.py
```

结果：

```text
py_compile pass
builder status = pass
builder verdict = PASS_READY_FOR_MTRP9_READONLY_EXPOSURE_IMPLEMENTATION_CONTRACT
covered_shadow_signal_days = 10
gate_pass = true
forbidden_scope_clean = true
citation_complete = true
readonly_exposure_rows = 10
open_production_blockers = 4
```

## 10. Missing Evidence Or Open Questions

无阻断缺口。

保留说明：

- MTRP8 不是 frontend/API/Agent implementation。
- MTRP8 不是 production default go/no-go。
- MTRP8 不是 paper portfolio apply contract。
- MTRP8 没有把 MTRP7_S_R lightweight shadow replay 升级为 formal ReplayResultArtifact 或 formal PriceStore。
- 若 MTRP9 进入实现合同，只能先定义 isolated GET-only readonly exposure surface、artifact authority、citation requirements、wording guardrails、validator 和 acceptance gate。

## 11. Next Work Document

### 11.1 Next Phase

允许进入：

```text
MTRP9_READONLY_EXPOSURE_IMPLEMENTATION_CONTRACT
```

### 11.2 MTRP9 Allowed Scope

MTRP9 仅允许做：

```text
isolated GET-only readonly exposure implementation contract
artifact authority / citation contract
readonly wording guardrail
frontend/API/Agent exposure design constraints
validator / acceptance plan
explicit non-default / non-order / non-advice labels
```

### 11.3 MTRP9 Forbidden Scope

MTRP9 仍禁止：

```text
production default switch
paper portfolio apply
frontend/API/Agent code change unless a later coordinator document separately authorizes implementation
daily auto default path mutation
latest pointer mutation
provider refresh / publish
accepted latest switch
formal PriceStore write
formal phase_yz write
broker / quick-trade / real order
目标仓位、目标权重或数量类交易指令
return promise / investment advice wording
```

### 11.4 MTRP9 Minimum Gates

MTRP9 work doc / contract 至少应要求：

```text
consume MTRP8 manifest and citation map only
GET-only API contract if API exposure is proposed
no POST/PUT/PATCH/DELETE
no frontend local CSV direct-read
no local recomputation of model/strategy/replay
no Agent tool/action expansion
mandatory artifact citation in display/context
mandatory non-default / readonly / not-order / not-investment-advice labels
network and static forbidden-action validator before any implementation review
production_blocker_register remains blocking for any default switch
```

## 12. Command For Coordinator

```text
MTRP8 reviewer verdict = PASS_READY_FOR_MTRP9_READONLY_EXPOSURE_IMPLEMENTATION_CONTRACT。
可以安排 MTRP9 isolated GET-only readonly exposure implementation contract。
仍不得授权 production default switch、paper apply、frontend/API/Agent code change、daily auto default path mutation、latest/provider/accepted-latest/PriceStore 写入、broker/order/quick-trade，或目标仓位/目标权重/数量类交易指令。
```

## 13. Final Decision

```text
verdict = PASS_READY_FOR_MTRP9_READONLY_EXPOSURE_IMPLEMENTATION_CONTRACT
authorize_mtrp9_readonly_exposure_implementation_contract = true
authorize_production_default_switch = false
authorize_paper_apply = false
authorize_frontend_api_agent_code_change = false
authorize_daily_auto_default_change = false
authorize_latest_provider_pricestore_broker_order = false
```
