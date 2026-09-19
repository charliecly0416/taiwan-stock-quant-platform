# TADR47 Narrow Strict Fact Feature Diagnostic Execution Report

## 1. Scope

This narrow diagnostic tests whether the existing TADR45 strict facts can form minimally evaluable research feature rows with local event-forward price labels.

It reads only:

- `data_tw/experiments/tradingagents_auxiliary_evidence_risk_summary/tadr45_2packet_strict_evidence_facts_extraction/strict_evidence_fact_records.json`
- `data_tw/experiments/provider_bridge_productionization/pbpr2a_w_proxy_provider_only_rerun/pbpr2a_w_yahoo_proxy_provider_only_20260708/candidate_normalized/TW2317.csv`
- `data_tw/experiments/provider_bridge_productionization/pbpr2a_w_proxy_provider_only_rerun/pbpr2a_w_yahoo_proxy_provider_only_20260708/candidate_normalized/TW2330.csv`

The script fail-stops unless the TADR45 fact payload contains exactly these fact IDs and symbols:

- `tadr45-fact-2317-q2-revenue-change-001` -> `2317`
- `tadr45-fact-2330-sales-change-001` -> `2330`

It does not read current-best, `prices.csv`, `provider/latest`, `accepted latest`, qlib raw/latest, raw_memory, PCOM/order/target/sizing, or production/default/latest.

It does not call LLM/TradingAgents, use network, generate new facts, run replay/backtest/OOS, compute IC, compute grouped returns, or make usefulness,收益, production, or trading conclusions.

## 2. Feature Candidate Mapping

Generated feature candidate rows:

- `metric_percent_value`
- `reported_change_positive`
- `ai_server_driver_mentioned`
- `driver_stated`
- `missing_context_flag_count`

These are deterministic row-level feature candidates only, not model inputs or decision signals.

## 3. Label Join Diagnostic

Results:

- `fact_count`: 2
- `feature_row_count`: 2
- `fwd_1td_labeled_event_count`: 1
- `fwd_2td_labeled_event_count`: 1
- `fwd_5td_labeled_event_count`: 0
- `min_required_for_statistical_metric`: 20
- `status`: `NO_DIAGNOSTIC_POWER`

One event (`2317`, event date `2026-07-06`) has local 1td/2td forward labels in the selected price source. The `2330` event date is `2026-07-13`, but the selected local price source ends on `2026-07-08`, so its labels are unavailable.

## 4. Interpretation

The diagnostic result is:

```text
NO_DIAGNOSTIC_POWER
```

The existing two TADR45 facts can be mapped into feature candidate rows, but they cannot support any statistical research-feature usefulness test:

- total feature rows are only 2,
- only 1 row has any forward label in the selected local price source,
- no cross-sectional or time-series diagnostic has enough observations,
- no IC, group-return, model-additive, replay, backtest, OOS, or current-best comparison is justified.

## 5. Artifacts

- `strict_fact_feature_candidate_rows.csv`
- `event_label_join_diagnostic.csv`
- `diagnostic_manifest.json`
- `forbidden_action_audit.json`

## 6. Boundary

Allowed conclusion:

```text
The existing TADR45 strict facts can be deterministically mapped to feature candidate rows, but the current two-record sample has no diagnostic power for usefulness.
```

Forbidden conclusions remain:

- strict facts are useful,
- strict facts improve current-best,
- strict facts improve returns,
- TA/LLM improves decisions,
- any OOS result exists,
- any production/default/latest artifact should change,
- any symbol should be bought, sold, held, ranked, scored, filtered, or sized.
