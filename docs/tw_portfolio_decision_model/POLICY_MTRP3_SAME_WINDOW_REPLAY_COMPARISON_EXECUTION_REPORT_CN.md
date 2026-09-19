---
created_at: 2026-06-28T18:30:06+00:00
phase: MTRP3_SAME_WINDOW_REPLAY_COMPARISON
strategy_candidate: top50_hold_rank_buffer_100
baseline_strategy: top50_exit_one_worst_sell
readonly_only: true
simulation_only: true
production_allowed: false
verdict: PASS_CANDIDATE_OUTPERFORMS_BASELINE_READY_FOR_REVIEW
---

# POLICY_MTRP3_SAME_WINDOW_REPLAY_COMPARISON_EXECUTION_REPORT_CN

## 1. Verdict

```text
PASS_CANDIDATE_OUTPERFORMS_BASELINE_READY_FOR_REVIEW
```

是否建议进入 P4 readonly shadow/readiness：`true`

本阶段仅执行 same-window readonly replay comparison，未修改 production registry/default/frontend/API/Agent/daily/latest/provider/PriceStore，未执行 broker、quick-trade 或真实交易，未输出生产 ready 结论。

## 2. 固定输入

- signal window: `2026-01-02..2026-05-07`
- full-rank visibility bridge: `data_tw/artifacts/signals/top50_hold_rank_buffer_100_full_rank_visibility_bridge/mtrp2_r_20260628T181347Z/manifest.json`
- candidate OrderIntent: `data_tw/artifacts/strategies/top50_hold_rank_buffer_100/mtrp2_r_20260628T181347Z/manifest.json`
- baseline OrderIntent: `data_tw/artifacts/replays/top50_hold_rank_buffer_100/mtrp3_same_window_replay_comparison/baseline_order_intent/manifest.json`
- output root: `data_tw/artifacts/replays/top50_hold_rank_buffer_100/mtrp3_same_window_replay_comparison`

P2_R lineage warning 保留：bridge 来源是 existing audited broad reference repackaged for production-candidate readiness，不等同 production-ready ModelSignalArtifact。

## 3. Replay 口径

```text
initial_equity = 1000000
target_holdings = 10
fee_rate = 0.001425
sell_tax_rate = 0.003
lot_size = 10
execution_price = next_open
execution_date_policy = next_tradeable_day_after_signal_date
cash_policy = no_negative_cash
mark_to_market = close same-day required / fallback audited
```

价格仅来自 MTRC5 允许的本地已审计 OHLCV 源；未 provider refresh/publish、未 accepted latest switch、未 formal PriceStore write，未使用 self_contained_demo。

## 4. Baseline vs Candidate

| metric | baseline | candidate |
| --- | ---: | ---: |
| final_equity | 1889481.157718 | 1960582.833712 |
| total_return | 0.8894811577 | 0.9605828337 |
| max_drawdown | -0.1369660506 | -0.1104340101 |
| actions | 137 | 66 |
| skipped | 7 | 10 |

## 5. Mark Coverage

| strategy | same_day_mark_coverage_ratio | final_date_same_day_mark_coverage_ratio | max_mark_lag_days | status |
| --- | ---: | ---: | ---: | --- |
| top50_exit_one_worst_sell | 1.0 | 1.0 | 0 | pass |
| top50_hold_rank_buffer_100 | 1.0 | 1.0 | 0 | pass |

## 6. Validator

- root validator status: `pass`
- baseline replay validator: `True`
- candidate replay validator: `True`
- forbidden scope clean: `True`

## 7. Boundary Statement

本报告不得解读为 production-ready、default switch 或真实交易授权。候选若进入下一步，也只能进入 P4 readonly shadow/readiness 观察，并继续保留 P2_R lineage warning。
