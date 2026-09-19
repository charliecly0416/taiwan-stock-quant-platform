---
created_at: 2026-06-27
status: work_document
phase: POLICY_RSR5_ROBUSTNESS_AND_ABLATION
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_RSR4_PREDECLARED_READONLY_REPLAY_REVIEW_CN.md
previous_artifact_root: data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr4_predeclared_readonly_replay
production_allowed: false
readonly_only: true
historical_readonly_research_artifact: true
model_training_authorized: false
threshold_tuning_authorized: false
rule_threshold_change_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
default_or_production_change_allowed: false
real_order_allowed: false
target_position_weight_quantity_allowed: false
---

# POLICY_RSR5_ROBUSTNESS_AND_ABLATION_WORK_CN

## 1. Phase Goal

执行 `POLICY_RSR5_ROBUSTNESS_AND_ABLATION`。

本阶段只允许对 RSR4 reviewer 放行的唯一候选做窄稳健性和消融：

```text
rsr2_rank_deterioration_sell_gate_v1
```

RSR5 目标不是寻找更好规则、不是调参、不是修复 rejected rules、不是生产化。目标是判断 RSR4 preliminary Type A 是否仍能在预声明 robustness/ablation 下保持机制可信、成本可接受、非 baseline clone、非 all-cash/no-trade、非单窗口偶然。

## 2. Candidate Boundary

Allowed candidate:

```text
rsr2_rank_deterioration_sell_gate_v1
```

Rejected rules explicitly excluded from RSR5:

```text
rsr2_score_bucket_regime_gate_v1
rsr2_rank_momentum_buy_gate_v1
rsr2_market_regime_action_budget_v1
rsr2_score_rank_regime_interaction_v1
```

Excluded rules 不得出现在 RSR5 robustness matrix、ablation matrix、candidate table、summary conclusion 或下一阶段候选中。若执行者认为 rejected rule 需要 repair，必须停止并要求 coordinator 另开 repair route；RSR5 不授权 repair。

## 3. Required Documents And Artifacts

执行者必须读取：

- `docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR4_PREDECLARED_READONLY_REPLAY_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR4_PREDECLARED_READONLY_REPLAY_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR4_PREDECLARED_READONLY_REPLAY_REVIEW_CN.md`
- RSR4 candidate artifacts for `rsr2_rank_deterioration_sell_gate_v1`: OrderIntent manifest/intents/schema/audits and ReplayResult manifest/summary/actions/daily_nav/position_snapshots/audits
- RSR4 root audits: `replay_result_index.csv`、`baseline_clone_audit.csv`、`fee_tax_turnover_audit.csv`、`regime_budget_audit.csv`、`missing_price_audit.csv`、`pit_leakage_audit.csv`、`cash_no_trade_audit.csv`、`forbidden_field_audit.csv`、`forbidden_action_audit.csv`
- RSR2 contracts CSV、pass/fail gates、YAML draft for `rsr2_rank_deterioration_sell_gate_v1`
- RSR3 validation/audits as needed
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

## 4. Required Work

### 4.1 2021 Sanity

Run readonly sanity replay/evidence for the allowed candidate on a 2021 qlib-only-compatible historical window when data lineage permits.

Must report:

- input signal and price lineage;
- window start/end;
- net return after fee/tax;
- max drawdown;
- action count;
- cash/no-trade audit;
- baseline clone audit;
- missing price and PIT/leakage audit.

2021 sanity is not production evidence and must not be described as latest/default/live.

### 4.2 2022 Downturn Diagnostic

Run readonly downturn diagnostic for 2022 only when data lineage permits.

Must report:

- drawdown behavior vs comparable baseline;
- sell trigger attribution;
- whether improvement comes from earlier rank deterioration exits rather than all-cash/no-trade;
- fee/tax after churn.

2022 remains downturn diagnostic, not strict OOS.

### 4.3 2023-2025 Qlib-only Strict Candidate Re-check

Re-check the same RSR4 2023-2025 qlib-only candidate without changing thresholds.

Must verify:

- same frozen rule logic;
- same OrderIntent -> ReplayExecution -> ReplayResult chain;
- same no production/default/latest/publish boundary;
- classification remains historical readonly research only.

### 4.4 Parameter Neighborhood Stability

Perform predeclared neighborhood checks around the frozen rule without selecting a better parameter.

Allowed form:

- diagnostic-only perturbation table around rank deterioration sensitivity;
- label every perturbation as `not_candidate=true`;
- compare whether the frozen setting is not a single-point anomaly.

Forbidden:

- picking the best threshold;
- changing RSR2 frozen threshold for the candidate;
- promoting a perturbation as a replacement rule.

### 4.5 Action-level Attribution

Attribute candidate performance at action level:

- top contributors and detractors by executed action;
- sell reasons: top50 exit vs 3d/5d deterioration without score support;
- buy refill actions after sell;
- fee/tax drag by action group;
- skipped actions and reasons.

Attribution may use replay output after execution, but must not feed back into ranking, threshold choice, or candidate selection.

### 4.6 Market Regime Ablation

Report behavior by market regime:

- risk_on;
- risk_neutral;
- risk_off;
- crash if sample exists.

Required:

- active days and action counts by regime;
- return/drawdown contribution where auditable;
- regime sample sufficiency;
- no regime-specific conclusion when sample floor is not met.

### 4.7 Transaction Cost Sensitivity

Run cost sensitivity diagnostics without changing candidate logic:

- baseline fee/tax as RSR4;
- higher fee/tax stress;
- lower/no-cost diagnostic only if clearly labeled gross diagnostic.

Must conclude using net after fee/tax, not gross-only.

### 4.8 Cash/No-trade And Baseline Clone Re-check

Re-run or recompute:

- `cash_gt_90pct_day_share`;
- `cash_share_mean`;
- no-trade days and active days;
- action difference rate vs baseline;
- action Jaccard similarity;
- high-turnover gross-only rejection;
- missing price skips.

Candidate fails RSR5 if improvement is mainly all-cash/no-trade, baseline clone, or gross-only high turnover.

## 5. Required Outputs

RSR5 may write:

```text
docs/tw_portfolio_decision_model/POLICY_RSR5_ROBUSTNESS_AND_ABLATION_EXECUTION_REPORT_CN.md
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr5_robustness_and_ablation/
```

Expected artifacts:

```text
manifest.json
input_manifest_links.json
candidate_boundary_audit.csv
window_robustness_summary.csv
ablation_matrix.csv
parameter_neighborhood_stability.csv
action_level_attribution.csv
market_regime_ablation.csv
transaction_cost_sensitivity.csv
cash_no_trade_recheck.csv
baseline_clone_recheck.csv
missing_price_audit.csv
pit_leakage_audit.csv
forbidden_field_audit.csv
forbidden_action_audit.csv
```

If replay outputs are generated, each must remain a `ReplayResultArtifact` with the required RSR4/ReplayResult contract files.

## 6. Pass/Fail Criteria

RSR5 can pass the candidate only if all are true:

- only `rsr2_rank_deterioration_sell_gate_v1` is evaluated as candidate;
- no RSR2 threshold/rule change;
- no training, qlib refresh, LTR adaptation, external pull, production/default/latest/publish;
- no target/weight/allocation/quantity instruction or real order;
- OrderIntent and ReplayResult contracts pass;
- 2021 sanity and 2022 diagnostic do not contradict the mechanism;
- 2023-2025 qlib-only strict candidate re-check remains net-after-fee/tax credible;
- parameter neighborhood does not show single-point anomaly;
- action attribution supports rank-deterioration sell mechanism;
- transaction cost stress does not collapse the result into gross-only;
- cash/no-trade and baseline clone checks pass.

RSR5 must fail or request coordinator closure if:

- candidate only works in one window;
- candidate is mainly all-cash/no-trade;
- candidate is baseline clone;
- candidate is high-turnover gross-only;
- candidate requires threshold change to pass;
- candidate needs forbidden data, training, latest/default/publish, or real order path.

## 7. Forbidden Actions

RSR5 禁止：

- training / retraining；
- qlib refresh；
- LTR retrain 或 qlib+LTR adaptation；
- external data pull，除非 coordinator 另行授权固定 historical readonly source；
- threshold tuning to returns；
- 修改 RSR2 冻结阈值或规则；
- 选择 best threshold / best rule / best bucket；
- repair rejected rules；
- provider publish；
- accepted latest switch；
- production/default/frontend/daily/latest 修改；
- broker、quick-trade、real order；
- target_position、target_weight、allocation_weight、quantity instruction 输出；
- 把 robustness result 包装为 production candidate、默认策略或投资建议。

## 8. Stop Conditions

以下任一情况必须 STOP 并写 blocker：

- RSR5 需要把 rejected rules 纳入候选；
- 无法重建/追溯 allowed candidate 的 RSR4 OrderIntent 或 ReplayResult lineage；
- 需要修改 `rsr2_rank_deterioration_sell_gate_v1` 的阈值/卖出边界/买入排序/action budget；
- 需要训练、qlib refresh、LTR adaptation、external data pull；
- PIT/available_at 无法证明；
- forbidden field/action audit 出现 fail；
- 需要 provider publish、accepted latest switch、production/default/frontend/daily/latest 修改；
- 需要真实订单、broker/quick-trade、target position/weight/allocation/quantity。

## 9. Reviewer Brief

RSR5 reviewer 必须检查：

1. 是否只有 `rsr2_rank_deterioration_sell_gate_v1` 进入 RSR5；
2. 是否没有对 rejected rules 做 robustness candidate 或 repair；
3. 是否没有训练、调参、改阈值、改默认、publish/latest；
4. 是否继续使用 `OrderIntentArtifact -> ReplayExecution -> ReplayResultArtifact`；
5. 2021/2022/2023-2025 窗口语义是否正确；
6. parameter neighborhood 是否只是稳定性诊断，不是 best threshold selection；
7. action-level attribution 是否支持机制；
8. market regime、transaction cost、cash/no-trade、baseline clone re-check 是否齐全且无 fail；
9. 是否仍明确 not production/default/order/investment advice。

## 10. Command For Executor

```text
你是 RSR5 执行者。读取 RSR mainline、RSR4 review、RSR5 work doc、RSR2/RSR3/RSR4 合同与 artifacts。只允许对 rsr2_rank_deterioration_sell_gate_v1 做 robustness/ablation；不得让 rsr2_score_bucket_regime_gate_v1、rsr2_rank_momentum_buy_gate_v1、rsr2_market_regime_action_budget_v1、rsr2_score_rank_regime_interaction_v1 进入 RSR5。执行 2021 sanity、2022 downturn diagnostic、2023-2025 qlib-only strict candidate re-check、parameter neighborhood stability、action-level attribution、market regime ablation、transaction cost sensitivity、cash/no-trade and baseline clone re-check。不得训练、不得改阈值调参、不得 qlib refresh/LTR adaptation、不得 provider/latest/default/production/frontend/daily/publish、不得真实订单、不得 target_position/target_weight/allocation_weight/quantity instruction。完成后写 POLICY_RSR5_ROBUSTNESS_AND_ABLATION_EXECUTION_REPORT_CN.md。
```
