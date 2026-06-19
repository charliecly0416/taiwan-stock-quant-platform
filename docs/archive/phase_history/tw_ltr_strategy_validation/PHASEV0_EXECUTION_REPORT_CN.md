# Phase V0 冻结验证合同执行报告

生成时间：2026-06-14

## 1. 本轮授权范围

本轮严格按 `docs/tw_ltr_strategy_validation/LTR_STRATEGY_VALIDATION_MAINLINE_CN.md` 执行 Phase V0：只盘点 Phase3A2C 产物与脚本，并冻结后续验证合同。

本轮未执行任何新回放、未重训 LTR、未调参、未修改前端/API、未联网、未新增数据源、未触发 provider / accepted latest / monitor / 交易链路。

## 2. 已盘点的 Phase3A2C 权威产物

Phase V0 后续验证只能复用 Phase3A2C 已修复的全日频回放口径。已盘点产物如下：

| 类型 | 路径 | Phase V0 结论 |
| --- | --- | --- |
| 主回放脚本 | `scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py` | 可作为 Phase V1 验证实现的口径来源；本轮未运行 |
| 冻结分数物化脚本 | `scripts/materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py` | 仅作为冻结分数字段来源；Phase V0 禁止运行 |
| Phase3A2C 执行报告 | `docs/tw_ltr_rerank_regime_turnover/PHASE3A2C_LOOKAHEAD_METRIC_REPAIR_EXECUTION_REPORT_CN.md` | 作为 lookahead 修复、共同日期集合、net/gross、turnover proxy 的审计依据 |
| gate summary | `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_gate_summary.json` | 标记 Phase3A2C 已完成，且 no retraining / no score rebuild / frontend_api_provider_trading_untouched 为 true |
| authority matrix | `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2b_authority_matrix.csv` | 确认产品侧 `_replay_variant()`、本地价格、只读仿真标志 |
| 方法汇总 | `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_method_comparison.csv` | 已含六个方法 common full range 指标 |
| 分段汇总 | `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_period_comparison.csv` | 已含 2022、2025、2026 YTD、validation、independent test、common full range |
| 数据质量 | `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_data_quality.csv` | 已含 common replay days 与 excluded dates |
| 执行价审计 | `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_price_execution_audit.csv` | 已含 asof 后首个真实交易日 close 审计样本 |
| 动作汇总 | `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_actions_summary.csv` | 可用于后续买入/卖出动作计数拆分 |

## 3. 冻结候选策略

Phase V1 及后续验证只允许比较以下两个 LTR 候选策略：

| 策略 ID | 含义 | 状态 |
| --- | --- | --- |
| `phase1c_ltr_simple_daily` | Phase1C 简单日频 LTR replay 候选 | 冻结 |
| `phase1c_ltr_turnover_controlled_daily` | Phase1C turnover-controlled 日频 LTR replay 候选 | 冻结 |

冻结分数字段：

`score_head10_all_l31_alpha0.7_top50_only`

不得替换 score head、不得重训、不得重建 Phase1C 分数、不得新增特征或候选策略。

## 4. 冻结 baseline

Phase V1 及后续验证必须包含以下 baseline，且主比较基准固定为 `rank_rotate_top50_adaptive_score`。

| baseline | 用途 | 状态 |
| --- | --- | --- |
| `rank_rotate_top50_adaptive_score` | 主比较 baseline | 冻结 |
| `rank_rotate_top50` | Top50 固定轮动 baseline | 冻结 |
| `rank_rotate_top30` | Top30 固定轮动 baseline | 冻结 |
| `confirmed_exit` | confirmed exit baseline | 冻结 |

不得新增 baseline 作为主线判断依据；如审查者后续要求补充，只能作为附录诊断。

## 5. 冻结完整日频回放口径

后续验证必须沿用 Phase3A2C 修复后的完整日频回放口径：

| 项目 | 冻结口径 |
| --- | --- |
| 权威路径 | 产品侧 `TWStockPortfolioReplayService` / `_replay_variant()` |
| 信号来源 | `qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill` |
| 价格来源 | `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized` 本地真实日频价格 |
| 冻结分数文件 | `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv` |
| 执行价 | asof 后第一个真实交易日 close |
| 日期集合 | accepted signal days 与 Phase1C frozen score days 取交集 |
| 方法公平性 | 所有候选和 baseline 使用同一 common replay date set |
| 初始资金 | `initialCash=1000000` |
| 手续费/税 | `feeRate=0.001425`，`sellTaxRate=0.003` |
| 手数 | `lotSize=10` |
| 最大持仓 | `maxHoldings=10` |
| 执行模式 | `next_trading_day_close` |
| net 字段 | `fee_tax_adjusted_net_return` |
| gross 字段 | 当前引擎不可得时必须写为 `not_available_in_current_engine` |
| turnover proxy | `sum(abs(quantity * price)) / average_equity` |

必须保留并输出 price execution audit、data quality、common replay days、excluded dates、missing price count、action count、notional turnover proxy。

## 6. 冻结验证切片

### 6.1 年度切片

Phase V1 年度验证必须覆盖以下年度切片：

| 年度切片 | Phase3A2C 现状 | Phase V1 要求 |
| --- | --- | --- |
| `2022` | 已有 `2022_full_available_replay_range`，common replay days = 241 | 复用同口径输出年度表 |
| `2023` | Phase3A2C 未显式产出年度行 | 必须补出；如数据不足，标记 `insufficient_data`，不得静默跳过 |
| `2024` | Phase3A2C 未显式产出年度行 | 必须补出；如数据不足，标记 `insufficient_data`，不得静默跳过 |
| `2025` | 已有 `2025_full_available_replay_range`，common replay days = 242 | 复用同口径输出年度表 |
| `2026 YTD` | 已有 `2026_ytd_available_replay_range`，common replay days = 79 | 复用同口径输出年度表，并保留 YTD 截止日期 |

年度切片必须显示 `start_date`、`end_date`、`baseline_signal_days`、`ltr_score_days`、`common_replay_days`、`excluded_dates`、`comparison_status`。

### 6.2 Rolling 切片

Phase V1 rolling 验证必须包含：

| rolling 窗口 | 冻结要求 |
| --- | --- |
| 6 个月 | 输出 window start/end、method、net return、max drawdown、actions、turnover proxy、相对 Top50 adaptive 差值、data status |
| 12 个月 | 输出 window start/end、method、net return、max drawdown、actions、turnover proxy、相对 Top50 adaptive 差值、data status |

Phase3A2C 当前未产出 6 个月/12 个月 rolling 表；Phase V1 必须在同一回放口径下补出，不能用新口径替代。

### 6.3 市况切片

Phase V1 市况分段至少必须覆盖：

| 冻结分段 | 允许映射 |
| --- | --- |
| `bull` | 如沿用既有 Phase2 regime，可由 `normal` 映射或由审查者确认更细定义 |
| `normal` | 如沿用既有 Phase2 regime，可由 `caution` 映射或保持中性分段 |
| `bear` | 如沿用既有 Phase2 regime，可由 `risk_off` 映射 |

Phase V0 不计算市况结果，只冻结要求：Phase V1 必须明确 regime 来源、映射表、每段样本天数、数据状态，并在同一 common replay date set 约束下比较候选与 baseline。

## 7. 冻结指标

Phase V1 及后续验证必须输出以下指标：

| 指标 | 冻结定义或映射 |
| --- | --- |
| `fee_tax_adjusted_net_return` | 扣除手续费和交易税后的 net return |
| `final_equity` | 回放期末权益 |
| `max_drawdown` | 回放期最大回撤 |
| `action_count` | 总动作数 |
| `buy_count` | 可由 Phase3A2C `add_action_count` 映射 |
| `sell_count` | 使用输出字段 `sell_count`；必要时与 `risk_action_count` 一并审计 |
| `fee_and_tax` | 手续费和交易税合计 |
| `turnover_proxy_by_notional_over_avg_equity` | `sum(abs(quantity * price)) / average_equity` |
| `missing_price_count` | 缺价次数 |
| `trading_days_used` | 实际共同回放交易日数 |
| `relative_return_vs_top50_adaptive` | 相对 `rank_rotate_top50_adaptive_score` 的 net return 差值 |
| `relative_drawdown_vs_top50_adaptive` | 相对 `rank_rotate_top50_adaptive_score` 的 max drawdown 差值 |
| `relative_actions_vs_top50_adaptive` | 相对 `rank_rotate_top50_adaptive_score` 的 action count 差值 |

现有 Phase3A2C `phase3a2_method_comparison.csv` 已包含 `delta_vs_rank_rotate_top50_adaptive_score`，但该字段只覆盖 return delta。Phase V1 必须显式补出 drawdown delta 与 action delta，字段名按本节冻结。

## 8. Phase3A2C 已确认的审计基线

以下信息作为 Phase V1 验证合同的审计基线，不作为 Phase V0 新计算结果：

| 项目 | 已盘点值 |
| --- | --- |
| Phase3A2C gate | `phase3a2c_completed_hold_for_review` |
| authority choice | `portfolio_replay_service_product_side_authority` |
| accepted signal range | 2022-01-03 至 2026-05-29 |
| price range | 2015-01-05 至 2026-06-12 |
| price file count | 150 |
| price audit sample count | 240 |
| price audit max days to execution | 3 |
| gross return policy | `not_available_in_current_engine` |
| frontend/API/provider/trading | Phase3A2C gate summary 标记 untouched |

Phase3A2C common full range 中六个 required methods 均为 `completed`，共同交易日数为 1043，缺价数为 0。

## 9. 禁止事项冻结

后续阶段除非审查者另行明确授权，否则禁止：

| 禁止项 | 说明 |
| --- | --- |
| 新回放 | Phase V0 已禁止；Phase V1 只能在授权后按冻结合同做验证回放 |
| LTR 重训 | 不得训练新模型、重建 score、替换 score head |
| 调参 | 不得改变 alpha、lookback、TopK、turnover budget、holding window、gap/buffer 等参数 |
| 新数据源 | 不得联网、不得引入官方/第三方/实时新数据源 |
| provider / accepted latest | 不得刷新、发布、切换 accepted latest |
| monitor 链路 | 不得触发 monitor scan、alert、config save |
| 交易链路 | 不得触发 broker、quick-trade、orders、target positions |
| 前端/API | 不得改前端展示、API schema 或产品入口 |
| 真实交易语义 | 不得输出买卖建议、仓位建议、收益承诺、胜率/上涨概率语义 |

## 10. 待审查缺口

以下是 Phase V0 盘点后留给审查者确认的缺口，不在本轮扩展实现：

| 缺口 | 影响 | 建议进入 Phase V1 的处理方式 |
| --- | --- | --- |
| Phase3A2C 未显式产出 2023/2024 年度行 | 年度稳定性验证不完整 | 按冻结 replay 口径补出；如数据不足，标记 `insufficient_data` |
| Phase3A2C 未产出 6m/12m rolling 表 | 无法判断滚动窗口稳健性 | 按冻结指标补出 rolling validation |
| Phase3A2C 未产出 bull/normal/bear 市况分段表 | 无法判断不同市况下的候选表现 | 明确 regime 来源和映射后再做只读分段验证 |
| 现有 delta 字段只覆盖 return delta | 相对回撤和动作数差异不完整 | Phase V1 增加 `relative_drawdown_vs_top50_adaptive` 与 `relative_actions_vs_top50_adaptive` |
| gross return 当前不可得 | 无法比较毛收益 | 继续固定为 `not_available_in_current_engine`，不得临时估算 |

## 11. Phase V1 Gate

Phase V0 已完成冻结验证合同。建议下一步 gate：

`request_phase_v1_yearly_replay_validation`

在审查者批准前，停止执行任何回放、训练、调参、数据刷新、前端/API 或交易链路相关工作。
