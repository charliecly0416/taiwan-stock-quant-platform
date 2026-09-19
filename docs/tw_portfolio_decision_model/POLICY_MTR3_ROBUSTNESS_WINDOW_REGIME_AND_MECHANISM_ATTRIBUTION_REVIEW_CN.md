# POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_MTR3_WITH_CONCENTRATION_OR_WINDOW_RISK
```

MTR3 可以进入 MTR4 readiness design，但不能直接生产化。

本轮不是策略失败，也不是合同违规。MTR3 验证了 `M2_hold_rank_buffer_100` 在 MTR2_R qlib+LTR broad full-rank visibility 下仍有明显 full-window 优势，并且 non-top50 buy 为 0、forbidden actions clean。主要问题是收益贡献有较强标的/事件集中度，且 5 个自然月里有 2 个月小幅落后 baseline。因此下一步应进入 readiness design，把集中度、窗口稳定性、extended OOS / shadow 作为生产前阻断项。

## 2. Evidence Checked

已读取并检查：

```text
docs/tw_portfolio_decision_model/POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_EXECUTION_REPORT_CN.md
data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/
```

并抽查合同：

```text
TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
STRATEGY_RULE_CONTRACT_CN.md
ORDER_INTENT_CONTRACT_CN.md
REPLAY_RESULT_CONTRACT_CN.md
NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

执行命令：

```bash
python -m py_compile scripts/run_tw_policy_mtr3_robustness_window_regime_and_mechanism_attribution.py
python scripts/run_tw_policy_mtr3_robustness_window_regime_and_mechanism_attribution.py --json
```

## 3. Scope Review

结论：

```text
PASS
```

MTR3 只消费 MTR2_R 产物：

```text
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/
```

未发现：

```text
策略修改
M2 参数修改
新增候选
重新调参
重写 MTR2_R replay result
production/default/frontend/API/Agent/daily/provider/latest 改动
provider publish / accepted latest switch
broker / quick-trade
target_weight / target_position
```

`coverage_and_validator_audit.csv` 全部通过，包括 ModelSignal / OrderIntent / Replay validator、baseline parity、top50 LTR equivalence、non-top50 buy forbidden audit。

## 4. Window Robustness

结论：

```text
PASS_WITH_WINDOW_RISK
```

Full-window：

| metric | baseline | M2_100 | delta |
| --- | ---: | ---: | ---: |
| net_total_return_after_fee_tax | 0.87459073 | 1.32852091 | +0.45393018 |
| average_turnover | 0.17040339 | 0.07651037 | -0.09389302 |
| total_fee_plus_tax | 48476.04 | 23979.01 | -24497.03 |
| max_drawdown | -0.13675456 | -0.10619259 | +0.03056197 |
| buy_count | 74 | 40 | -34 |
| sell_count | 65 | 30 | -35 |
| hold_buffer_trigger_count | 0 | 61 | +61 |
| non_top50_buy_intent_count | 0 | 0 | 0 |

Half windows 均为正：

```text
first_half net_delta = +0.08751267
second_half net_delta = +0.24276068
```

Monthly：

```text
positive = 3/5
negative months = 2026-02 (-0.02016153), 2026-05 (-0.02305255)
```

Rolling 20d 使用不重叠切片：

```text
r20_01 positive
r20_02 negative: -0.00972657
r20_03 positive
r20_04 positive
```

因此 MTR3 支持继续，但不能把当前证据解释为全窗口无风险稳定提升。

## 5. Regime Attribution

结论：

```text
PASS
```

Regime 使用 baseline daily_return 定义，仅为 diagnostic，不是策略输入。

结果：

| regime | day_count | delta | hold triggers | fee/tax delta |
| --- | ---: | ---: | ---: | ---: |
| risk_on | 45 | +0.65648970 | 38 | -15140.25 |
| neutral | 12 | +0.04314910 | 6 | -2786.34 |
| risk_off | 22 | +0.01063245 | 17 | -6570.45 |

重点：risk_off 也没有输 baseline，但优势很小。MTR4 需要继续观察 risk_off / drawdown segment，不应只看 full-window。

## 6. Action-level Attribution

结论：

```text
PASS_WITH_POSTERIOR_ONLY_BOUNDARY
```

`action_level_pnl_attribution.csv`、`hold_buffer_trigger_pnl_attribution.csv`、`missed_replacement_opportunity_audit.csv` 均来自 replay 输出侧：

```text
actions.csv
daily_nav.csv
position_snapshots.csv
order_intents.csv
```

审查确认这些 realized / replay PnL 只用于 MTR3 后验归因，没有反馈给 StrategyRule，也没有被用作 ranking input。

## 7. Concentration Review

结论：

```text
PASS_WITH_CONCENTRATION_RISK
```

集中度风险较强：

```text
top1_symbol_share = 0.631760, TW6683
top3_symbol_share = 0.972756
top1_event_share = 0.300709, 2026-04-27|TW6683
```

这意味着 full-window delta 虽然大，但相当一部分来自少数标的/事件。该风险不阻断 MTR4 readiness design，但阻断直接生产化。

## 8. Safety Review

结论：

```text
PASS
```

`forbidden_field_audit.csv`：

```text
OrderIntent 禁用字段均 absent；
approx_pnl_delta 只存在于 MTR3 analysis artifact；
used_for_ranking = false。
```

`forbidden_action_audit.csv`：

```text
trained_model = pass / not_performed
tuned_model = pass / not_performed
posthoc_candidate_expansion = pass / not_performed
modified_m2_parameter = pass / not_performed
reran_mtr2_replay_result = pass / not_performed
non_top50_buy_candidate = pass / not_performed
modified_registry_default = pass / not_performed
modified_frontend_or_api = pass / not_performed
modified_agent_or_prompt = pass / not_performed
modified_daily_or_provider = pass / not_performed
provider_publish = pass / not_performed
accepted_latest_switch = pass / not_performed
broker_or_quick_trade = pass / not_performed
target_weight_or_position_output = pass / not_performed
replay_return_feedback_to_strategy = pass / not_performed
```

## 9. Findings

### Medium

1. 收益贡献集中度高。

`TW6683` 单一标的贡献占 final delta 的约 63.18%，前三大标的占约 97.28%。这不是合同错误，但说明 MTR2_R/MTR3 当前窗口的收益证据可能受少数事件驱动。

2. 月度稳定性不是全胜。

2026-02 与 2026-05 小幅落后 baseline。虽然 full/half/regime 仍支持继续，但 MTR4 必须要求 extended OOS 或 shadow 继续观察。

3. risk_off 优势偏小。

risk_off delta 仅 `+0.01063245`。若 MTR 的目标之一是降低下跌期风险，MTR4 不能只用 full-window net 做 Go/No-Go。

### Low

1. MTR3 rolling_20d 是不重叠切片，不是每日滚动 60 条。

工作文档允许滚动或不重叠切片，当前合规；但 MTR4 若要更严格，可补每日滚动。

## 10. Gate Decision

```text
artifact_complete: PASS
scope_no_strategy_change: PASS
window_coverage_full_first_second_monthly_rolling20d: PASS
regime_diagnostic_only: PASS
action_pnl_posterior_only: PASS
non_top50_buy_intent_zero: PASS
forbidden_actions_clean: PASS
full_window_net_positive: PASS
turnover_fee_tax_reduction: PASS
drawdown_improved: PASS
concentration_risk: WARN
monthly_window_risk: WARN
```

## 11. Recommendation

建议进入：

```text
MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT
```

MTR4 不应直接生产化，应先冻结 readiness 条件：

```text
1. broad full-rank visibility 的正式合同位置；
2. non-top50 buy 永久阻断 validator；
3. extended OOS / shadow 观察要求；
4. 月度/rolling/risk_off 最低门槛；
5. symbol/event concentration 上限或 disclosure；
6. 若集中度继续过高，应降级为 research-only candidate。
```
