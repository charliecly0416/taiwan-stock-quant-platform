# Phase B0 默认基线锚点与 LTR 保守版规则范围冻结执行报告

生成时间：2026-06-14

执行依据：`docs/TW_STOCK_LTR_BASELINE_AND_CONSERVATIVE_TUNING_MAINLINE_CN.md`

## 1. 本轮目标与边界

本轮只做 Phase B0 冻结，不做最终默认基线结论。

本轮未执行：

- LTR 重训；
- Phase1C score 重建或改权重；
- 新数据源、联网、provider refresh / publish；
- accepted latest switching；
- monitor config / scan / alerts 写入；
- broker / quick-trade / orders；
- target position / target weight；
- 前端 / API 改动；
- 最终默认策略切换。

本轮只复用已有文档与本地既有 artifact，冻结下一轮 B1 的比较合同、候选集合和规则层可调范围。

## 2. 当前默认基线锚点冻结

当前默认基线锚点冻结为：

```text
rank_rotate_top50_adaptive_score
```

锚点含义：

- 这是当前产品默认主基线；
- B0 不判断它最终是否继续作为默认；
- B1 完成 LTR 保守版固定候选验证后，才能在同口径结果上做最终默认基线建议；
- 所有新增 LTR 保守候选都必须相对该锚点输出：
  - `relative_return_vs_top50_adaptive`
  - `relative_drawdown_vs_top50_adaptive`
  - `relative_actions_vs_top50_adaptive`

当前锚点证据来源：

- `docs/tw_ltr_strategy_validation/PHASEV4_FINAL_REVIEW_AND_CLOSURE_CN.md`
  - 已明确 Top50 adaptive score remains the default baseline。
- `data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_gate_summary.json`
  - Phase V2 使用 `frozen_score_oos_replay_only`，未重训、未调参、未改回放口径。
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_gate_summary.json`
  - 既有完整日频回放使用 product-side portfolio replay authority，且六个方法均 completed。

## 3. 最终默认基线候选集合冻结

B1 最终默认基线比较必须覆盖以下 6 个既有策略，不得删减：

| method | B0 角色 | 是否可作为最终默认候选 | B0 备注 |
| --- | --- | --- | --- |
| `rank_rotate_top50_adaptive_score` | 当前默认锚点 | 是 | 仅冻结为当前锚点，不提前给最终结论 |
| `rank_rotate_top50` | 传统 Top50 轮动 baseline | 是 | 用于判断 adaptive 是否确实有解释价值 |
| `rank_rotate_top30` | 更集中轮动 baseline | 是 | 用于比较集中度、动作数与回撤 |
| `confirmed_exit` | 低动作 / 确认退出 baseline | 是 | 用于比较低动作、低回撤但可能牺牲收益的路径 |
| `phase1c_ltr_simple_daily` | LTR 高收益高动作候选 | 是，但不得默认化 | 只能在同口径结果下评估，不能因收益单项提前胜出 |
| `phase1c_ltr_turnover_controlled_daily` | 现有 LTR 保守版基准 | 是，但不得默认化 | B1 新保守候选必须至少和它比较 |

B1 允许新增的 LTR 保守版候选只用于参考，不自动成为默认候选；只有 B1 结果证明稳定、清楚、可解释后，才可进入 B2 产品化讨论。

## 4. 既有比较口径冻结

B1 必须复用既有完整日频回放口径。

冻结项：

| 项目 | 冻结值 |
| --- | --- |
| score 来源 | `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv` |
| score column | `score_head10_all_l31_alpha0.7_top50_only` |
| replay authority | product-side `TWStockPortfolioReplayService` / Phase3A2C 口径 |
| execution mode | `next_trading_day_close` |
| initial cash | `1,000,000` |
| max holdings | `10` |
| lot size | `10` |
| fee rate | `0.001425` |
| sell tax rate | `0.003` |
| turnover proxy | `sum_abs_quantity_price_over_average_equity` |
| gross return policy | `not_available_in_current_engine` |
| price source | 既有本地 Yahoo adjusted primary normalized price archive，不新增数据源 |
| signal source | 既有 accepted historical signal artifact，不触发 accepted latest switching |

禁止在 B1 中为提高结果修改上述口径。

## 5. 时间切片与输出指标冻结

### 5.1 必须输出的时间切片

B1 至少输出：

| period | 说明 | B0 解释边界 |
| --- | --- | --- |
| `2022` | 年度完整日频回放 | train-only，只能复盘，不作为 OOS 证据 |
| `2023` | 年度完整日频回放 | train-only，只能复盘，不作为 OOS 证据 |
| `2024` | 年度完整日频回放 | train / validation mixed，不作为独立样本外证据 |
| `2025` | 年度完整日频回放 | validation / independent_test mixed，必须拆分解释 |
| `2026 YTD` | 年度至今完整日频回放 | independent_test，但不能单独决定默认结论 |
| `common_full_range_shared_by_all_compared_methods` | 共同完整区间 | 综合复盘用，不作为单一结论依据 |
| `phase1c_validation_range` | 2024-08-12..2025-06-24 | 可用于候选规则表现观察 |
| `phase1c_independent_test_range` | 2025-06-25..2026-05-07 | 只用于冻结候选后的样本外检查，不得反向调参 |

### 5.2 必须输出的指标

每个策略 / 候选 / period 至少输出：

```text
fee_tax_adjusted_net_return
max_drawdown
action_count
buy_count
sell_count
fee_and_tax
turnover_proxy_by_notional_over_avg_equity
trading_days_used
relative_return_vs_top50_adaptive
relative_drawdown_vs_top50_adaptive
relative_actions_vs_top50_adaptive
```

不得只看收益率。

## 6. 当前锚点事实表，仅作 B0 背景，不作最终结论

来自既有 `phase3a2_method_comparison.csv` 的 common full range 摘要如下，仅作为当前状态锚点：

| method | fee_tax_adjusted_net_return | max_drawdown | action_count | turnover_proxy | B0 背景说明 |
| --- | ---: | ---: | ---: | ---: | --- |
| `rank_rotate_top50_adaptive_score` | 15.963677 | -0.402422 | 1932 | 184.497379 | 当前默认锚点，不提前确认最终默认 |
| `rank_rotate_top50` | 11.061246 | -0.408928 | 1982 | 198.730437 | 传统 Top50 baseline |
| `rank_rotate_top30` | 9.785117 | -0.426219 | 2054 | 193.662284 | 更集中 baseline |
| `confirmed_exit` | 3.011848 | -0.337436 | 265 | 21.361639 | 低动作确认退出 baseline |
| `phase1c_ltr_simple_daily` | 40.018220 | -0.387816 | 1978 | 199.489876 | 收益强但动作 / 换手高 |
| `phase1c_ltr_turnover_controlled_daily` | 4.652725 | -0.199269 | 315 | 31.849293 | 防守、低动作，但收益牺牲明显 |

注意：上表不是最终默认选择依据。B1 必须按冻结候选和切片重新输出同口径比较后，才允许提出最终默认建议。

## 7. LTR 保守版可调规则范围冻结

B1 只允许在 `phase1c_ltr_turnover_controlled_daily` 的规则层上生成固定候选，不允许网格搜索失控。

### 7.1 可动参数

| 参数 | 允许范围 | 说明 |
| --- | --- | --- |
| `candidate_pool_rank` | Top30 或 Top50 | 只能基于冻结 Phase1C rank，不新增数据 |
| `buy_rank_threshold` | Top10 / Top20 / Top30 中冻结候选指定值 | 买入确认更严格，不得试大量阈值 |
| `buy_confirm_days` | 1 或 2 | 连续满足才允许买入 |
| `sell_rank_threshold` | Top50 外或缺失 | 卖出确认更平滑 |
| `sell_confirm_days` | 1 或 2 | 连续转弱才允许卖出 |
| `max_actions_per_day` | 1 | B1 统一冻结为每日最多 1 次动作 |
| `max_actions_per_10_trading_days` | 3 | 继承既有 turnover-controlled 动作预算 |
| `min_holding_days` | 20 | 继承 Phase3A2C 既有说明，不为结果临时调整 |

### 7.2 禁止调整参数

| 禁止项 | 原因 |
| --- | --- |
| LTR 特征、label、LambdaMART 参数 | 属于模型层，B0/B1 不授权 |
| `score_head10_all_l31_alpha0.7_top50_only` 权重或列 | Phase1C frozen score 必须保持不变 |
| accepted signal / provider / latest pointer | 会触碰数据链路与写入风险 |
| execution price / fee / tax / lot / holdings 口径 | 会破坏同口径比较 |
| independent_test 后再改候选参数 | 构成 OOS 反向调参 |
| 大规模 threshold 网格搜索 | 不符合“简单、准确、清晰、实用” |

## 8. B1 固定候选规则表

B1 只能评估以下固定候选，不得临时追加更多候选；如实现不可行，必须回报审查者，而不是扩大搜索。

| candidate_key | 基础策略 | 一句话说明 | candidate_pool_rank | buy_rank_threshold | buy_confirm_days | sell_rank_threshold | sell_confirm_days | max_actions_per_day | max_actions_per_10_trading_days | min_holding_days |
| --- | --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| `phase1c_ltr_turnover_controlled_daily` | 既有保守版 | 原有低动作 LTR 保守基准 | Top50 | 既有规则 | 1 | 既有规则 | 1 | 1 | 3 | 20 |
| `phase1c_ltr_conservative_top30_2day_confirm_daily` | 规则层变体 | 只看 Top30 且连续 2 天确认，减少单日噪声动作 | Top30 | Top30 | 2 | Top50 外或缺失 | 2 | 1 | 3 | 20 |
| `phase1c_ltr_conservative_top20_entry_2day_exit_daily` | 规则层变体 | 买入更严格，只接受 Top20；卖出需连续转弱 | Top50 | Top20 | 1 | Top50 外或缺失 | 2 | 1 | 3 | 20 |

候选数量冻结为：现有保守基准 + 2 个新增规则层变体。

B1 不允许在看到结果后追加 `Top15`、`Top25`、不同动作预算、不同持有期等额外变体。

## 9. 接受标准冻结

### 9.1 保守版 LTR 是否保留

保守版 LTR 候选进入后续 B2 参考列表，至少应满足多数条件：

- 相比 `phase1c_ltr_turnover_controlled_daily` 有明确改进；
- 改进不是仅靠单一年份或单一 period；
- action_count 仍明显低于 `phase1c_ltr_simple_daily`；
- max_drawdown 没有为了追求收益明显恶化；
- turnover_proxy 仍维持保守特征；
- 可以用一句话解释规则；
- 与现有策略形成真实差异。

若不满足，B1 必须建议不纳入前端，不得强行产品化。

### 9.2 最终默认基线选择

默认基线不等于历史收益率最高。

B1 最终默认建议必须综合：

- 跨年度稳定性；
- 回撤可接受；
- 动作数不过高；
- 用户是否容易理解；
- 前端说明是否简单；
- 是否需要额外复杂解释才能成立。

B0 明确禁止提前给出最终默认结论。

## 10. 禁止事项表

| 类别 | 禁止事项 |
| --- | --- |
| 模型 | 重训 LTR、改 label、改特征、改 LambdaMART 参数、改 Phase1C frozen score |
| 数据 | 新数据源、联网、provider refresh / publish、accepted latest switching |
| 回放 | 改执行价格、费用税费、持仓数、lot size、turnover 定义、样本切片解释 |
| 调参 | independent_test / 2026 YTD 结果反向调参、追加无边界候选、按结果临时改阈值 |
| 产品 | 提前默认切换、把候选写成推荐策略 / 更优策略 / 最佳策略 |
| 交易 | broker、quick-trade、orders、target position、target weight、真实买卖/持有建议 |
| Monitor | monitor config save、scan、alerts write |
| 前端/API | B0/B1 未授权前端或 API 接入变更 |

## 11. B1 输入产物清单

B1 只能复用以下既有输入：

- 冻结 score：`data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv`
- score schema：`data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_schema.json`
- 既有完整日频回放脚本 / 口径：`scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`
- 既有 Phase V1/V1B 年度与 split-aware artifact：`data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/`
- 既有 Phase V2 rolling / regime / walk-forward artifact：`data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/`
- 既有 Phase3A2C full daily replay artifact：`data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/`

B1 若需要新增输出目录，建议限定为：

```text
data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay/
```

## 12. 本轮验证

本轮只读检查内容：

- 已读取主线文档；
- 已确认 Phase V2 gate 中 `forbidden_scope_not_run` 包含 retraining、parameter tuning、new data、provider、accepted latest、monitor、trading chain；
- 已确认 Phase3A0 frozen score artifact 存在；
- 已确认 Phase3A2C 完整日频回放 artifact 存在，且六个基础方法均 completed；
- 未执行新回放，未生成新策略结果。

## 13. 是否建议进入 B1

建议进入 B1，但前提是审查者确认本 B0 冻结合同通过。

B1 只能按本报告冻结候选运行，不得扩大调参空间，不得提前改默认主基线。

建议 gate：

```text
phaseb0_contract_frozen_request_phaseb1_conservative_replay
```
