# RCPT4 Narrow Robustness and Rule05 Mechanism Attribution Execution Report

## 1. Scope
- Rule: `RCPT1_RULE_05` only.
- Window: `2022 downturn validation diagnostic`.
- No new rule, threshold, model training, strict test, or production chain change.

## 2. Main Result
- Rule net return after fee/tax: `-0.1860388` vs baseline `-0.3360922`.
- Rule max drawdown: `-0.2290736` vs baseline `-0.42634734`.
- Accelerated sells: `105`.
- Average cash rate: `0.5705297`.

## 3. Mechanism Attribution
- The dominant mechanism is early sale of deteriorating holdings during risk-off periods.
- Trigger-day follow-through is summarized for 5/10/20 day horizons across `105` accelerated sells.
- Cash exposure is persistent through the year, with monthly end-state data showing `0.25594167` in the last month summary row.
- Fee/tax rose despite lower turnover proxy because the rule adds sell-side churn and sell tax on accelerated exits.

## 4. Concentration and Stability
- Top instrument by accelerated-sell count: `TW6550`.
- Subperiod table covers 6 subperiod rows.

## 5. 2021 Optional Diagnostic
- Status: `NOT_AVAILABLE`.
- Reason: 2021 market feature coverage is absent in rcp3a_market_feature_coverage_pit_gate/market_feature_by_signal_date.csv.

## 6. Validator
- Validator status: `PASS`.
- Forbidden action audit rows: `15`.

## 7. Output Paths
- Output root: `data_tw/experiments/risk_control_policy_2022/rcpt4_rule05_mechanism_attribution`.
- Manifest: `data_tw/experiments/risk_control_policy_2022/rcpt4_rule05_mechanism_attribution/manifest.json`.

# RCPT4 Rule05 Mechanism Attribution Diagnostic Findings

## 1. Conclusion
- `RCPT1_RULE_05` remains a diagnostic-only candidate, not a production or strict-OOS result.
- The improvement is consistent with a sell-side early-exit mechanism under risk-off, not a rule change or model retraining.

## 2. Core Evidence
- Accelerated sells: `105`.
- Average cash rate: `0.5705297`.
- Fee/tax: `121293.26`.
- Net return after fee/tax: `-0.1860388`.
- Max drawdown: `-0.2290736`.

## 3. Attribution Takeaways
- Monthly comparison was produced for 12 months and does not indicate a single-month-only explanation.
- Trigger-day attribution covers all `105` accelerated sells and the 5/10/20 day follow-through table.
- Cash exposure is elevated, but the profile is mixed across trigger and non-trigger days rather than an all-cash regime.
- Fee/tax reconciliation shows the higher cost footprint comes from additional sell-side churn and sell taxes, not from a broken accounting path.
- Concentration checks are limited to top instruments, months, and trigger days; no single stock explains the whole result.

## 4. 2021 Optional Diagnostic
- Status: `NOT_AVAILABLE`.
- Reason: 2021 market feature coverage is absent in rcp3a_market_feature_coverage_pit_gate/market_feature_by_signal_date.csv.

## 5. Safety Boundary
- No new rules, thresholds, training, strict tests, production/provider changes, or order/target outputs were introduced.
