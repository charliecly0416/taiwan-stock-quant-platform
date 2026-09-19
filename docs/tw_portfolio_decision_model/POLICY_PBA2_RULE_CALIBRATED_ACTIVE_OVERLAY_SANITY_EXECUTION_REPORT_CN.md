---
created_at: 2026-06-22T14:43:11+00:00
status: executed_pba2_rule_calibrated_active_overlay_sanity
phase: PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_WORK_CN.md
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba2_rule_calibrated_active_overlay_sanity
strict_test_used: false
training_run: false
production_allowed: false
recommendation: PASS_READY_FOR_REVIEWER_TO_CONSIDER_PBA2_VALIDATION_PASS
---

# PBA2 Rule-calibrated Active Overlay Sanity 执行报告

## 1. Scope

本轮只执行 PBA2 rule-calibrated active overlay sanity。未训练模型，未运行或读取 strict_test，未进入 PBA3/PBA5。

## 2. Documents Read

```text
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_REVIEW_CN.md
```

## 3. Rules Run

```text
[
  {
    "rule_id": "score_gap_buy_filter",
    "layer": "Layer B",
    "parameters": {
      "min_top1_top2_score_gap": 0.01
    }
  },
  {
    "rule_id": "score_zscore_buy_filter",
    "layer": "Layer B",
    "parameters": {
      "min_daily_score_zscore": 1.0
    }
  },
  {
    "rule_id": "holding_age_sell_delay",
    "layer": "Layer A",
    "parameters": {
      "min_holding_age_days_before_sell": 20
    }
  },
  {
    "rule_id": "trend_confirmed_hold",
    "layer": "Layer A",
    "parameters": {
      "delay_sell_if_return_5d_gt": 0.0
    }
  },
  {
    "rule_id": "market_risk_exposure_reduce",
    "layer": "Layer B",
    "parameters": {
      "block_buy_if_twii_return_20d_lt": -0.03
    }
  },
  {
    "rule_id": "top_rank_active_tilt_diagnostic",
    "layer": "Layer C",
    "parameters": {
      "top_rank_overlay_delta_diagnostic": 0.05
    }
  }
]
```

## 4. Replay Metrics

见 `rule_replay_metrics_by_split.csv`。

## 5. Validation Selection

```text
selected_rule_id = score_gap_buy_filter
validation_baseline_net_return_after_fee_tax = 0.95376753
selected_validation_net_return_after_fee_tax = 0.97910586
selected_excess_return_after_fee_tax = 0.02533833
validation_pass = True
```

## 6. Gate Summary

```text
participation_gates_pass = True
cash_dominance_gates_pass = True
risk_asset_exposure_pass = True
cost_turnover_not_pathological = True
not_baseline_clone = True
```

## 7. Forbidden Audit

```text
training_run = false
strict_test_used = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
provider/latest/monitor/frontend/Agent/broker/production touched = false
```

## 8. Recommendation

```text
PASS_READY_FOR_REVIEWER_TO_CONSIDER_PBA2_VALIDATION_PASS
```
