---
created_at: 2026-06-29
status: work_doc
phase: MTRP8_SHADOW_REVIEW_AND_READONLY_EXPOSURE_DESIGN
parent_phase: MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR
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
broker_authorized: false
---

# POLICY_MTRP8_SHADOW_REVIEW_AND_READONLY_EXPOSURE_DESIGN_WORK_CN

## 1. 目标

MTRP8 只做 shadow review 与 readonly exposure design review。

本阶段目标：

```text
读取 MTRP6 readonly exposure 合同；
读取 MTRP7_S_R clean Tier A daily shadow rerun 证据；
生成候选策略只读曝光设计包；
判断该候选是否可以进入下一阶段的 readonly exposure implementation contract / shadow observation；
明确仍不授权 production default switch。
```

## 2. 非目标

本阶段不做：

```text
修改 production/default registry
修改 frontend/API/Agent 代码
修改 daily auto 主链路/default path
provider refresh / publish
accepted latest switch
latest pointer mutation
formal phase_yz 写入
formal PriceStore 写入
broker / quick-trade / real order
target_weight / target_position / quantity instruction
模型训练/调参/重算分数
根据收益筛选或调参
```

## 3. 输入

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRP6_DAILY_FULL_RANK_BRIDGE_AND_CANDIDATE_SHADOW_INTEGRATION_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR_REVIEW_CN.md
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp6_daily_shadow_integration_contract/
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build/mtrp7_s_r_real_tier_a_shadow_rerun_repair/
configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml
configs/tw_product_artifact_registry.yaml
configs/tw_modular_registry.yaml
```

## 4. 输出

新增 builder：

```text
scripts/build_tw_policy_mtrp8_shadow_review_readonly_exposure_design.py
```

输出 root：

```text
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp8_shadow_review_readonly_exposure_design/
```

必须输出：

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

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRP8_SHADOW_REVIEW_AND_READONLY_EXPOSURE_DESIGN_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRP8_SHADOW_REVIEW_AND_READONLY_EXPOSURE_DESIGN_REVIEW_CN.md
```

## 5. Pass 条件

MTRP8 PASS 需要同时满足：

```text
MTRP7_S_R validator status=pass
covered_shadow_signal_days >= 5
input_tier = tier_a_clean_daily_lineage
tier_b_fallback_used = false
daily bridge/order/replay artifact count 均 >= 5
same_day_mark_coverage_ratio >= 0.99
max_mark_lag_days = 0
negative_cash_count = 0
duplicate_position_count = 0
skip delta tracked
MTRP6 readonly exposure contract 存在并通过
readonly exposure 只允许 GET-only display
候选不能显示为 default
候选不能输出 order / target / quantity / broker / return promise
artifact citation map 完整
forbidden scope clean
```

## 6. 允许结论

执行者 verdict：

```text
PASS_READY_FOR_MTRP9_READONLY_EXPOSURE_IMPLEMENTATION_CONTRACT
FAIL_NEEDS_MTRP8_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

审查者 verdict：

```text
PASS_READY_FOR_MTRP9_READONLY_EXPOSURE_IMPLEMENTATION_CONTRACT
FAIL_NEEDS_MTRP8_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 7. 下一步

若通过：

```text
进入 MTRP9 readonly exposure implementation contract / isolated GET-only API design。
仍不授权 production default switch。
```

若失败：

```text
修复 MTRP8 exposure design 或回到 MTRP7_S_R 补 shadow evidence。
```
