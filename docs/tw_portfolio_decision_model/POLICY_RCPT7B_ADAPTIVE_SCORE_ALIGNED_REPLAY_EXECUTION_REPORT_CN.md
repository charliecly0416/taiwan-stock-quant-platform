---
created_at: 2026-06-24T17:48:23+00:00
phase: RCPT7B_ADAPTIVE_SCORE_ALIGNED_REPLAY
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt7b_adaptive_score_aligned_replay
validator_status: PASS
recommended_verdict: PASS_RCPT7_CANDIDATE_READY_FOR_CLOSURE
model_training_performed: false
production_allowed: false
---

# RCPT7B Adaptive-score-aligned Replay 执行报告

## 1. Scope

本轮只回放 RCPT7A 冻结的 Candidate A/B/C，并用同一 replay engine 比较 `rank_rotate_top50_adaptive_score`、`rank_rotate_top50`、`RCPT1_RULE_05`、`qlib_only_baseline`。

固定窗口：2021-01-04..2021-12-30 为 pre-2022 sanity diagnostic；2022-01-03..2022-12-30 为 downturn diagnostic；2023-01-03..2025-06-30 为 qlib-only strict OOS candidate。未声称完整 2025 自然年。

未训练模型、未读取 LTR/orthogonal LTR/stacking score、未新增候选、未调阈值、未修改 production/default/provider/frontend/Agent/monitor/order 链路，未输出 OrderIntent、target_weight、target_position 或 quantity_instruction。

## 2. Strict OOS Key Results

| strategy | net_return_after_fee_tax | max_drawdown | primary_average_cash_rate | cash_gt_90pct_equity_day_share | fee_and_tax |
| --- | ---: | ---: | ---: | ---: | ---: |
| rank_rotate_top50_adaptive_score | 0.32670955 | -0.56426863 | 0.08642502 | 0.00167504 | 490846.19 |
| rank_rotate_top50 | 0.4121439 | -0.5590545 | 0.09005068 | 0.00167504 | 509542.18 |
| RCPT1_RULE_05 | 0.27133828 | -0.35344655 | 0.30752496 | 0.01675042 | 434655.23 |
| qlib_only_baseline | 0.4121439 | -0.5590545 | 0.09005068 | 0.00167504 | 509542.18 |
| Candidate A | 0.21833199 | -0.38061348 | 0.30386711 | 0.01507538 | 431163.7 |
| Candidate B | 0.31383997 | -0.36230989 | 0.30328641 | 0.01675042 | 448162.35 |
| Candidate C | 0.32670955 | -0.56426863 | 0.08642502 | 0.00167504 | 490846.19 |

## 3. Gate

- validator status: `PASS`
- recommended reviewer verdict: `PASS_RCPT7_CANDIDATE_READY_FOR_CLOSURE`
- gate 明细：`data_tw/experiments/risk_control_policy_2022/rcpt7b_adaptive_score_aligned_replay/gate_decision_by_candidate.csv`

## 4. Outputs

输出目录：`data_tw/experiments/risk_control_policy_2022/rcpt7b_adaptive_score_aligned_replay`

全部 RCPT7B work doc 要求文件已生成；内部 action ledger 仅位于 `internal_replay_ledgers_not_order_intent/`，并标注 readonly accounting。
