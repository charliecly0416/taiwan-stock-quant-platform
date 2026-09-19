---
created_at: 2026-06-27
status: work_document
phase: POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_REVIEW_CN.md
previous_artifact_root: data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness
production_allowed: false
readonly_only: true
model_training_authorized: false
replay_authorized: false
order_intent_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
---

# POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_WORK_CN

## 1. Phase Goal

执行 `POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC`。

本阶段只做 PIT-safe attribution diagnostic dataset 和诊断摘要，用来回答 score bucket、score percentile/gap、rank delta、market regime、holding-aware state 是否具备解释力。RSR1 不产出策略规则，不跑收益规则 replay，不调阈值，不生成 OrderIntent，不输出订单、仓位、权重或数量。

## 2. Required Documents

执行者必须读取：

- `docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_REVIEW_CN.md`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/manifest.json`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/input_lineage_inventory.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/feature_readiness_audit.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/pit_leakage_audit.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/forbidden_action_audit.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/rsr1_dataset_feasibility.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

## 3. Required Input Set

RSR1 默认使用 RSR0 审查通过的 qlib-only input set：

- 标准 qlib-only signal: `data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json`
- qlib-only TEST fold lineage: `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.manifest.json`
- full qlib rank: `data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/manifest.json`
- baseline readonly internal ledger: `data_tw/experiments/risk_control_policy_2022/rcpt5b_r_fee_tax_gate_repair/internal_replay_ledgers_not_order_intent/baseline`
- stock price source: `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty`
- TWII source: `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv`

不得新增外部数据拉取。不得使用 qlib+LTR adaptation 或 LTR score 做本阶段默认输入。

## 4. Required Outputs

建议输出目录：

```text
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/
```

必须产出：

- `manifest.json`
- `rsr1_diagnostic_dataset.csv`
- `portfolio_state_view.csv`
- `feature_schema.json`
- `label_schema.json`
- `input_lineage_links.json`
- `feature_construction_audit.csv`
- `label_namespace_audit.csv`
- `consumer_forbidden_field_audit.csv`
- `pit_leakage_audit.csv`
- `diagnostic_summary.csv`
- `diagnostic_summary.md`
- `forbidden_action_audit.csv`

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

## 5. Required Dataset Semantics

`rsr1_diagnostic_dataset.csv` 必须按 `signal_date`、`instrument`、`model_name` 或等价 key 保持可追溯。

允许的 feature families：

- qlib same-day score/rank: `candidate_rank`、`buy_score`、`raw_score`、`score_rank`、`full_qlib_rank`。
- score diagnostics: `score_bucket`、`score_percentile`、`score_gap`、`top_score_dispersion`。
- rank diagnostics: `rank_1d_delta`、`rank_3d_delta`、`rank_5d_delta`、rank improvement/deterioration flags。
- market regime diagnostics: TWII MA5/MA10/MA20、drawdown、trailing volatility、risk_on/risk_neutral/risk_off/crash diagnostic flags。
- holding-aware diagnostics: `current_holding_flag`、`cost_basis_present`、holding rank/score support flags that do not depend on future returns or realized PnL。
- baseline action context for attribution only: baseline buy/sell/hold/skip action flag by signal date and instrument, if sourced from existing readonly ledger.

Forward returns may exist only as diagnostic labels. Label columns must use a clear namespace such as:

```text
diagnostic_label_forward_return_*
diagnostic_label_forward_excess_return_*
```

No StrategyRule, OrderIntent, replay, ranking, or threshold selection consumer may read label columns.

## 6. Required Minor Repair From RSR0 Review

Before building the full diagnostic dataset, RSR1 must materialize:

```text
portfolio_state_view.csv
```

Minimum fields:

```text
asof_date
instrument
cost_basis
current_holding_flag
source_position_snapshot_path
source_snapshot_hash
```

`quantity` may be included only if marked `accounting_state_only` in `feature_schema.json`; it must never be emitted as a strategy instruction and must not appear in any OrderIntent-like output.

The view must exclude:

```text
execution_price
execution_date
realized_pnl
realized_return
unrealized_pnl
cash
cash_after
nav
equity
daily_return
broker_order_id
target_position
target_weight
quantity_instruction
```

If RSR1 chooses to use existing `rank_change_3d`、`rank_change_5d`、`score_delta_5d` from position snapshots as evidence, it must also recompute rank/score deltas from standard signal files for all candidates and prefer recomputed fields for diagnostics.

## 7. Required Diagnostics

RSR1 must produce diagnostic summaries, not strategy recommendations:

- forward return distribution by score bucket;
- forward return distribution by score percentile band;
- forward return distribution by score gap / top dispersion band;
- forward return distribution by rank delta bucket;
- action/context distribution by market regime;
- holding vs non-holding diagnostic comparison;
- baseline action context grouped by the above features;
- coverage and missingness by date and instrument.

All summaries must be labeled `diagnostic_only=true` and `not_strategy_evidence=true`.

RSR1 may compute correlations, group means, medians, counts, hit rates, drawdown/context descriptors, and coverage stats. It must not select a best threshold, best rule, best bucket, or production candidate.

## 8. PIT / Leakage Requirements

Must pass:

- qlib signal fields satisfy `available_at <= signal_date` where available.
- score percentile/gap use only same-day cross-section.
- rank deltas use current signal date and previous available signal dates only.
- TWII MA/drawdown/volatility use only rows with market date `<= signal_date`.
- diagnostic labels are generated after feature construction and remain in label namespace.
- consumer audit proves no forbidden label/accounting/execution field is used as feature/ranking/StrategyRule input.

Must fail/stop:

- rank delta requires future signal dates;
- market regime requires future TWII rows;
- forward return, future label, realized PnL, execution price/date, next_open/next_close, cash/NAV or replay return appears in feature/ranking columns;
- any OrderIntent-like output is generated;
- any replay runner/training runner/provider publish/latest/default/frontend/daily update path is touched.

## 9. Forbidden Actions

本阶段禁止：

- training / retraining；
- qlib refresh；
- LTR retrain or qlib+LTR adaptation；
- replay PnL rule search；
- threshold tuning；
- strategy candidate selection；
- OrderIntentArtifact generation；
- ReplayResultArtifact generation or replay rerun；
- provider publish；
- accepted latest switch；
- production/default/frontend/daily update 修改；
- broker、quick-trade、real order；
- target_position、target_weight、quantity instruction；
- external data pull。

## 10. Pass Criteria

RSR1 通过条件：

- diagnostic dataset 可复现并有 manifest；
- `portfolio_state_view.csv` 完成 RSR0 minor repair；
- feature schema 与 label schema 明确隔离；
- consumer forbidden field audit 无 critical/fail；
- PIT/leakage audit 无 critical/fail；
- forbidden action audit clean；
- diagnostic summary 足以支持 RSR2 预声明规则设计，但不包含收益规则 replay、阈值调优或生产建议。

## 11. Reviewer Brief

审查者重点判断：

- RSR1 是否仍为 diagnostic-only；
- 是否完成 RSR0 条件项；
- feature/label/ledger/accounting 边界是否清楚；
- PIT/leakage audit 是否无 critical；
- 是否没有 replay、training、threshold tuning、OrderIntent、production/default/latest/publish 行为；
- 诊断摘要是否足以给 RSR2 做预声明规则设计，但没有把诊断结果包装成策略收益结论。

若通过，审查者可以建议进入 RSR2 predeclared rule design。RSR2 仍不得直接跑 replay，必须先冻结 StrategyRuleConfig、Dependency YAML、candidate boundaries、max buy/sell counts、tie-breaker、diagnostic-only/readonly flags 和 validator gate。

## 12. Executor Command

```text
你是 RSR1 执行者。执行 docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md。只做 qlib-only PIT-safe attribution diagnostic dataset、PortfolioState 视图、feature/label/consumer audits 和 diagnostic summary。不得训练、不得 rerun replay、不得调阈值、不得生成 OrderIntent、不得输出订单/仓位/权重/数量、不得 provider publish、不得 accepted latest switch、不得改 production/default/frontend/daily update。完成后写 docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md。
```
