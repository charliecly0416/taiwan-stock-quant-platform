# POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_MTR2_R_WITH_BROAD_FULL_RANK_TRANSFER_CANDIDATE
```

审查结论：

```text
broad_signal_contract: PASS
research_only_boundary: PASS
top50_ltr_equivalence: PASS
non_top50_buy_forbidden: PASS
baseline_order_intent_parity: PASS
baseline_replay_parity: PASS
M2_hold_rank_buffer_100_trigger: PASS
M2_hold_rank_buffer_100_gate: PASS
forbidden_actions: PASS
production_boundary: PASS
```

本轮不再是 MTR2 的 lineage blocker。MTR2_R 已经修复 qlib+LTR top50-only artifact 无法表达 hold buffer 的核心问题：新增 research-only broad full-rank visibility artifact，使策略能合法看见当前持仓跌出 top50 后的 `full_qlib_rank=51..100`，同时仍严格禁止非 top50 行参与买入。

## 2. Evidence Checked

已检查：

```text
docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_EXECUTION_REPORT_CN.md
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r/r1_broad_full_rank_visibility_repair_20260628/manifest.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/
scripts/run_tw_policy_mtr2_r_broad_full_rank_visibility_repair.py
```

并抽查合同：

```text
MODEL_SIGNAL_CONTRACT_CN.md
MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
STRATEGY_RULE_CONTRACT_CN.md
ORDER_INTENT_CONTRACT_CN.md
REPLAY_RESULT_CONTRACT_CN.md
NEW_MODEL_REVIEWER_CHECKLIST_CN.md
NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

## 3. Broad Signal Review

结论：

```text
PASS
```

broad artifact：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r/r1_broad_full_rank_visibility_repair_20260628/manifest.json
```

关键字段：

```text
research_only = true
diagnostic_only = true
not_default_candidate = true
production_allowed = false
no_provider_publish = true
no_accepted_latest_switch = true
no_default_switch = true
row_count = 11837
window = 2026-01-02..2026-05-07
daily_row_count_min = 149
```

`top50_ltr_equivalence_audit.csv` 全部通过：

```text
top50_row_count: pass, 3950 vs 3950
top50_keys: pass
top50_ltr_values: pass
```

`non_top50_buy_forbidden_audit.csv` 全部通过：

```text
non_top50_candidate_rank_gt_50: pass
non_top50_ltr_flag_false: pass
non_top50_visibility_only_true: pass
```

审查特别确认：执行中曾出现过 top50 值不完全等价和少数非 top50 行 `candidate_rank <= 50` 的问题，已通过修复 runner 后重跑消除。当前落地 artifact 的底层审计为 pass，不是只改报告文字。

## 4. Baseline Parity

结论：

```text
PASS
```

OrderIntent parity：

```text
same_signal_date_instrument_action_parity: pass
baseline rows = 142
M0 rows = 142
baseline_not_m0 = 0
M0_not_baseline = 0
```

Replay parity：

```text
final_equity delta = 0
gross_total_return delta = 0
net_total_return_after_fee_tax delta = 0
max_drawdown delta = 0
average_turnover delta = 0
total_fee delta = 0
total_tax delta = 0
buy_count delta = 0
sell_count delta = 0
```

这说明 broad visibility repair 没有破坏 baseline 决策路径。

## 5. Transfer Candidate Review

结论：

```text
PASS
```

核心结果：

| candidate | net | turnover | fee+tax | max_drawdown | hold triggers | non-top50 buys | gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| baseline/M0 | 0.87459073 | 0.17040339 | 48476.04 | -0.13675456 | 0 | 0 | n/a |
| M2_hold_rank_buffer_75 | 1.09682900 | 0.10496683 | 32769.85 | -0.14269324 | 30 | 0 | false |
| M2_hold_rank_buffer_100 | 1.32852091 | 0.07651037 | 23979.01 | -0.10619259 | 61 | 0 | true |

`M2_hold_rank_buffer_100` 同时满足：

```text
net >= baseline - 0.02: pass
turnover reduction >= 20%: pass, 55.10%
fee/tax reduction >= 20%: pass, 50.53%
max drawdown not worse by >0.05: pass, actually improved by 0.03056
cash/no-trade ratio <= 10%: pass
hold_buffer_trigger_count > 0: pass, 61
non_top50_buy_intent_count = 0: pass
```

底层原因也符合 MTR2_R 预期：M2 不再退化成 baseline，因为 broad full-rank rows 让持仓跌出 top50 但仍在 51-100 buffer 内时可被保留，换手与费用显著下降，且本窗口收益没有牺牲，反而提升。

## 6. Safety / Scope

结论：

```text
PASS
```

`forbidden_action_audit.csv` 显示以下均为 `not_performed`：

```text
trained_model
tuned_model
posthoc_candidate_expansion
non_top50_buy_candidate
modified_registry_default
modified_frontend_or_api
modified_daily_or_provider
provider_publish
accepted_latest_switch
broker_or_quick_trade
target_weight_or_position_output
```

`OrderIntent` validator 与 `Replay` validator 均为 `ok=true`。未发现 target_weight、target_position、quantity instruction、broker/order、quick_trade、future return、label、realized pnl 或 replay return 被用于策略输入。

## 7. Findings

### Medium

1. `M2_hold_rank_buffer_100` 通过的是 2026-01-02 至 2026-05-07 的 qlib+LTR research-only broad artifact 窗口。

   这是强正向证据，但还不是 production readiness。下一步必须做 robustness：不同窗口、不同市场状态、与 qlib-only MTR1 对齐的机制归因，以及是否存在个别标的/日期贡献过度集中的问题。

2. broad artifact 不能直接替换产品默认长 ID。

   本轮产物的正确身份是 `research_only / diagnostic_only / not_default_candidate`。如果后续要生产化，必须另开 Go/No-Go，决定是把 broad full-rank visibility 纳入正式 ModelSignalArtifact 合同，还是作为受控 strategy dependency extension。

### Low

1. broad daily row count min 为 149，而非严格 150。

   工作文档 gate 是 `daily_row_count_min >= 100`，当前通过；且 top50 coverage 为 50，M2 所需 51-100 visibility 足够。建议 MTR3 robustness 中继续记录 daily coverage distribution。

## 8. Gate Decision

```text
broad_artifact_research_only_gate: PASS
top50_ltr_equivalence_gate: PASS
non_top50_buy_forbidden_gate: PASS
extension_schema_gate: PASS
baseline_order_intent_parity_gate: PASS
baseline_replay_parity_gate: PASS
hold_buffer_trigger_gate: PASS
non_top50_buy_intent_gate: PASS
net_gate: PASS
turnover_gate: PASS
fee_tax_gate: PASS
drawdown_gate: PASS
cash_no_trade_gate: PASS
forbidden_action_gate: PASS
production_boundary_gate: PASS
```

## 9. Recommendation

建议进入：

```text
MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION
```

MTR3 应保持 readonly / research-only，并只围绕 `M2_hold_rank_buffer_100` 做：

```text
1. 多窗口 robustness；
2. market regime / drawdown segment attribution；
3. hold buffer trigger 的 action-level PnL attribution；
4. turnover/fee/tax 降低是否来自合理少交易，而非错过高收益替换；
5. 标的集中度与少数事件贡献审计；
6. 是否具备进入 production readiness Go/No-Go 的证据。
```

不建议现在直接生产化，也不建议继续扩参搜索。
