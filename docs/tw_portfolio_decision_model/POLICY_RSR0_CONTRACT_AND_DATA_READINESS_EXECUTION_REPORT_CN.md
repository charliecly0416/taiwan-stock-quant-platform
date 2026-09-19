---
created_at: 2026-06-27T14:45:10+00:00
status: executed_rsr0_contract_and_data_readiness
phase: POLICY_RSR0_CONTRACT_AND_DATA_READINESS
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_WORK_CN.md
artifact_root: data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness
readonly_only: true
replay_rerun_performed: false
training_run: false
production_allowed: false
recommendation: PASS_READY_FOR_RSR1_ATTRIBUTION_DIAGNOSTIC_WITH_MINOR_REPAIR
---

# Execution Report

## 1. Scope
- Assigned phase: `POLICY_RSR0_CONTRACT_AND_DATA_READINESS`
- Mainline document: `docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md`
- Work document: `docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_WORK_CN.md`
- Non-goals confirmed: 不跑收益规则 replay；不训练模型；不调阈值；不改 production/default；不 provider publish；不 accepted latest switch；不生成 OrderIntent、交易、目标仓位、目标权重或数量指令。

## 2. Documents / Contracts / Skills Read

Skills read:

```text
/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
```

Required documents read:

```text
docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_WORK_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
docs/tw_portfolio_decision_model/POLICY_MODEL_RESEARCH_ROUTE_CLOSURE_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FINAL_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT6_RESEARCH_CLOSURE_PACKAGE_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT7C_ADAPTIVE_SCORE_ALIGNED_CLOSURE_REVIEW_CN.md
```

## 3. Changes Made

新增只读审计脚本：

```text
scripts/audit_tw_policy_rsr0_contract_data_readiness.py
```

新增 RSR0 readiness artifacts 和本执行报告。未修改策略实现、默认配置、provider/latest、前端、日更、模型或 replay 结果。

## 4. Evidence Produced

Artifacts:

```text
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/manifest.json
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/input_lineage_inventory.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/feature_readiness_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/pit_leakage_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/forbidden_action_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/rsr1_dataset_feasibility.md
```

Validator/test output:

```text
python scripts/audit_tw_policy_rsr0_contract_data_readiness.py
python -m py_compile scripts/audit_tw_policy_rsr0_contract_data_readiness.py
```

No screenshots were required.

## 5. Compliance With Mainline

关键输入可追溯：

| 输入 | 路径 | 结论 |
| --- | --- | --- |
| qlib-only 标准信号 | `data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json` | PASS |
| qlib-only TEST fold lineage | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.manifest.json` | PASS |
| full qlib rank | `data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/manifest.json` | PASS |
| 2023-2025 baseline action ledger | `data_tw/experiments/risk_control_policy_2022/rcpt5b_r_fee_tax_gate_repair/internal_replay_ledgers_not_order_intent/baseline` | PASS，readonly internal ledger，不是 OrderIntent |
| 2023-2025 holding state source | `data_tw/experiments/risk_control_policy_2022/rcpt5b_r_fee_tax_gate_repair/internal_replay_ledgers_not_order_intent/baseline/position_snapshots.csv` | PASS，可构造 PortfolioState 视图 |
| stock price source | `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty` | PASS，RCPT5B_R price coverage audit pass |
| TWII market source | `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv` | PASS |

可构造 feature：

- `score_bucket`、`score_percentile`、`score_gap/top dispersion`：可由 same-day `buy_score/raw_score` 构造。
- `rank_1d_delta`、`rank_3d_delta`、`rank_5d_delta`：可由当前和历史 signal dates 构造，不需要未来数据。
- market regime：可由 TWII close 构造 MA5/MA10/MA20、drawdown、trailing volatility，满足至少两类 regime feature 要求。
- holding state：可从 baseline position snapshots 构造 `current_holding_flag`；建议 RSR1 先物化专用 PortfolioState 视图。

## 6. Forbidden Actions Audit

`forbidden_action_audit.csv` 全部为 `PASS_NOT_PERFORMED`。本阶段未训练、未 rerun replay、未调阈值、未读取 LTR score、未 provider publish、未 accepted latest switch、未改 production/default、未生成策略意图或交易/仓位/权重/数量指令。

## 7. Issues / Blockers / Deviations

无 critical blocker。

Minor repair:

1. RSR1 前建议从 RCPT5B_R `position_snapshots.csv` 物化 RSR1 专用 `PortfolioState` 视图，只保留 `asof_date`、`instrument`、`cost_basis`、`current_holding_flag` 等状态字段。
2. 若 RSR1 reviewer 要求 2023-2025 baseline 必须是正式 `ReplayResultArtifact` 目录，可对现有 internal ledger 做只读合同包装；不得 rerun replay 或改结果。
3. market breadth 未作为 RSR0 必需项；如 RSR1 使用，需另做 PIT coverage audit。

## 8. Files Changed

```text
scripts/audit_tw_policy_rsr0_contract_data_readiness.py
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/manifest.json
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/input_lineage_inventory.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/feature_readiness_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/pit_leakage_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/forbidden_action_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/rsr1_dataset_feasibility.md
docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_EXECUTION_REPORT_CN.md
```

## 9. Recommendation For Reviewer

```text
PASS_READY_FOR_RSR1_ATTRIBUTION_DIAGNOSTIC_WITH_MINOR_REPAIR
```
