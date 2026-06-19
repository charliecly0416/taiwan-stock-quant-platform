# Phase 3A Route B Turnover Replay 执行报告

生成时间：2026-06-13T18:26:16+00:00

## 1. 本轮目标

在固定 Phase1C row-level score 的前提下，评估 turnover control 是否改善成本后表现、动作次数、换手与回撤。

## 2. 使用 frozen score artifact 的说明

本轮只读取 `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv`，固定 score 为 `score_head10_all_l31_alpha0.7_top50_only`。未重建、未改写、未替换该 score。

## 3. Route B 与 regime diagnostic-only

Regime-aware gating was not validated. Regime is diagnostic-only in Phase3A.

本轮未用 regime 控制进出、动作阈值、过滤或参数选择。

## 4. 实际完成内容

- 将上一轮阻断型预检脚本改为只读 turnover replay 脚本。
- 使用 validation-only 小网格选择 Phase1C turnover 参数。
- independent_test 只按 validation 选中配置做最终检验。
- 对 baseline、年度、regime diagnostic-only、turnover/action/cost 输出分表。

## 5. 改动文件清单

- `scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3A_ROUTE_B_TURNOVER_REPLAY_EXECUTION_REPORT_CN.md`

## 6. 新增产物清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a_route_b_turnover_replay/phase3a_validation_selection.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a_route_b_turnover_replay/phase3a_independent_test_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a_route_b_turnover_replay/phase3a_yearly_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a_route_b_turnover_replay/phase3a_regime_diagnostic_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a_route_b_turnover_replay/phase3a_turnover_action_summary.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a_route_b_turnover_replay/phase3a_gate_summary.json`

## 7. validation 参数选择

| method | config_id | fee_tax_adjusted_net_return | max_drawdown | action_count | turnover_proxy | selection_score |
| --- | --- | --- | --- | --- | --- | --- |
| confirmed_exit | baseline |  |  |  |  |  |
| phase1c_simple_topk_no_turnover | baseline | 4.436124974665301 | -0.9617276368379739 | 6524 | 1.0405103668261562 |  |
| phase1c_turnover_controlled | k30_a3_gap0.0_buf0.0_hold3_budget0.2 | 16.33663701832224 | -0.9656044419932642 | 1266 | 0.20191387559808613 | 11.983402491490923 |
| phase1c_turnover_controlled | k30_a3_gap0.01_buf0.0_hold3_budget0.2 | 16.33663701832224 | -0.9656044419932642 | 1266 | 0.20191387559808613 | 11.983402491490923 |
| phase1c_turnover_controlled | k30_a3_gap0.02_buf0.0_hold3_budget0.2 | 16.33663701832224 | -0.9656044419932642 | 1266 | 0.20191387559808613 | 11.983402491490923 |
| phase1c_turnover_controlled | k30_a3_gap0.0_buf0.0_hold0_budget0.2 | 15.340147913653507 | -0.9659023025758472 | 1278 | 0.20382775119617225 | 10.986647534116736 |
| phase1c_turnover_controlled | k30_a3_gap0.01_buf0.0_hold0_budget0.2 | 15.340147913653507 | -0.9659023025758472 | 1278 | 0.20382775119617225 | 10.986647534116736 |
| phase1c_turnover_controlled | k30_a3_gap0.02_buf0.0_hold0_budget0.2 | 15.340147913653507 | -0.9659023025758472 | 1278 | 0.20382775119617225 | 10.986647534116736 |
| phase1c_turnover_controlled | k30_a1_gap0.0_buf0.0_hold5_budget0.2 | 15.20185784165264 | -0.9627949361818856 | 442 | 0.0704944178628389 | 10.862467637047693 |
| phase1c_turnover_controlled | k30_a1_gap0.01_buf0.0_hold5_budget0.2 | 15.20185784165264 | -0.9627949361818856 | 442 | 0.0704944178628389 | 10.862467637047693 |
| phase1c_turnover_controlled | k30_a1_gap0.02_buf0.0_hold5_budget0.2 | 15.20185784165264 | -0.9627949361818856 | 442 | 0.0704944178628389 | 10.862467637047693 |
| phase1c_turnover_controlled | k30_a2_gap0.0_buf0.0_hold0_budget0.2 | 15.020369568803538 | -0.9621358595371187 | 862 | 0.13748006379585323 | 10.674445568766481 |

## 8. independent_test 最终结果

| method | config_id | status | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | turnover_proxy | cost_drag | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rank_rotate_top30 | baseline | ok | 318561.87644147285 | 318562.87644147285 | -0.31946597738928995 | 5494 | 0.8762360446570973 | 0.810365 |  |
| rank_rotate_top50 | baseline | ok | 89945.93607801168 | 89946.93607801168 | -0.3058526769765112 | 8264 | 0.7908133971291866 | 0.7313639999999999 |  |
| phase1c_simple_topk_no_turnover | baseline | ok | 429507.3604758288 | 429508.3604758288 | -0.33277227314017455 | 4904 | 0.7821371610845294 | 0.7233400000000001 |  |
| rank_rotate_top50_adaptive_score | baseline | blocked |  |  |  |  |  |  | Frozen Phase3A0 artifact does not include the technical columns required to reconstruct this baseline without leaving the fixed-input boundary. |
| confirmed_exit | baseline | blocked |  |  |  |  |  |  | Frozen Phase3A0 artifact does not include the technical columns required to reconstruct this baseline without leaving the fixed-input boundary. |
| phase1c_turnover_controlled | k30_a3_gap0.0_buf0.0_hold3_budget0.2 | ok | 621873.6694154005 | 621874.6694154005 | -0.341352542937564 | 1270 | 0.2025518341307815 | 0.18732500000000005 |  |

## 9. baseline 对照

`rank_rotate_top50_adaptive_score` 与 `confirmed_exit` 因 Phase3A0 frozen artifact 不含所需技术列，保留 blocked 行；未从其他样本补列，以维持固定输入边界。

| method | config_id | status | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | turnover_proxy | cost_drag | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rank_rotate_top30 | baseline | ok | 318561.87644147285 | 318562.87644147285 | -0.31946597738928995 | 5494 | 0.8762360446570973 | 0.810365 |  |
| rank_rotate_top50 | baseline | ok | 89945.93607801168 | 89946.93607801168 | -0.3058526769765112 | 8264 | 0.7908133971291866 | 0.7313639999999999 |  |
| phase1c_simple_topk_no_turnover | baseline | ok | 429507.3604758288 | 429508.3604758288 | -0.33277227314017455 | 4904 | 0.7821371610845294 | 0.7233400000000001 |  |
| rank_rotate_top50_adaptive_score | baseline | blocked |  |  |  |  |  |  | Frozen Phase3A0 artifact does not include the technical columns required to reconstruct this baseline without leaving the fixed-input boundary. |
| confirmed_exit | baseline | blocked |  |  |  |  |  |  | Frozen Phase3A0 artifact does not include the technical columns required to reconstruct this baseline without leaving the fixed-input boundary. |
| phase1c_turnover_controlled | k30_a3_gap0.0_buf0.0_hold3_budget0.2 | ok | 621873.6694154005 | 621874.6694154005 | -0.341352542937564 | 1270 | 0.2025518341307815 | 0.18732500000000005 |  |

## 10. 年度结果

| split | year | method | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | turnover_proxy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| validation | 2024 | rank_rotate_top30 | 0.6472630549602933 | 1.6472630549602933 | -0.4260373771853945 | 3360 | 1.1546391752577319 |
| validation | 2025 | rank_rotate_top30 | 0.4369624841115738 | 1.4369624841115738 | -0.9557060688484545 | 4016 | 1.1952380952380952 |
| validation | 2024 | rank_rotate_top50 | 0.626659256642222 | 1.626659256642222 | -0.3841323945279229 | 4936 | 1.0177319587628868 |
| validation | 2025 | rank_rotate_top50 | 0.571102253191426 | 1.571102253191426 | -0.9497093536090387 | 5584 | 0.9971428571428572 |
| validation | 2024 | phase1c_simple_topk_no_turnover | 2.2194666827276706 | 3.2194666827276706 | -0.34662493228719604 | 2976 | 1.022680412371134 |
| validation | 2025 | phase1c_simple_topk_no_turnover | 0.6885172329410743 | 1.6885172329410743 | -0.9617276368379739 | 3548 | 1.0559523809523808 |
| independent_test | 2025 | rank_rotate_top30 | 455.02415605516194 | 456.02415605516194 | -0.31946597738928995 | 3556 | 0.9117948717948717 |
| independent_test | 2026 | rank_rotate_top30 | 697.5657935255049 | 698.5657935255049 | -0.17721964629934772 | 1938 | 0.8177215189873417 |
| independent_test | 2025 | rank_rotate_top50 | 215.3251875309933 | 216.3251875309933 | -0.3058526769765112 | 5508 | 0.8473846153846154 |
| independent_test | 2026 | rank_rotate_top50 | 414.79502185858433 | 415.79502185858433 | -0.1555554839783868 | 2756 | 0.6977215189873417 |
| independent_test | 2025 | phase1c_simple_topk_no_turnover | 596.1905951017183 | 597.1905951017183 | -0.33277227314017455 | 3066 | 0.7861538461538461 |
| independent_test | 2026 | phase1c_simple_topk_no_turnover | 718.2148771242315 | 719.2148771242315 | -0.1569735752781315 | 1838 | 0.7755274261603377 |
| validation | 2024 | phase1c_turnover_controlled | 7.0185940963237154 | 8.018594096323715 | -0.2926595911189185 | 594 | 0.20412371134020618 |
| validation | 2025 | phase1c_turnover_controlled | 1.1620544462115325 | 2.1620544462115325 | -0.9656044419932642 | 672 | 0.2 |
| independent_test | 2025 | phase1c_turnover_controlled | 734.7727707445043 | 735.7727707445043 | -0.341352542937564 | 796 | 0.20410256410256408 |
| independent_test | 2026 | phase1c_turnover_controlled | 844.1993524932251 | 845.1993524932251 | -0.2417876741926127 | 474 | 0.19999999999999993 |

## 11. turnover / action / cost 结果

| split | method | config_id | action_count | turnover_proxy | average_holding_days | cost_drag |
| --- | --- | --- | --- | --- | --- | --- |
| validation | rank_rotate_top30 | baseline | 7376 | 1.176395534290271 | 0.8500542299349241 | 1.0879599999999998 |
| validation | rank_rotate_top50 | baseline | 10520 | 1.0066985645933015 | 0.9933460076045627 | 0.9310200000000001 |
| validation | phase1c_simple_topk_no_turnover | baseline | 6524 | 1.0405103668261562 | 0.9610668301655426 | 0.9622900000000001 |
| validation | rank_rotate_top50_adaptive_score | baseline |  |  |  |  |
| validation | confirmed_exit | baseline |  |  |  |  |
| validation | phase1c_turnover_controlled | k30_a1_gap0.0_buf0.0_hold0_budget0.2 | 450 | 0.07177033492822965 | 13.933333333333334 | 0.06637500000000002 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.0_buf0.0_hold3_budget0.2 | 446 | 0.07113237639553428 | 13.923766816143498 | 0.06578500000000001 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.0_buf0.0_hold5_budget0.2 | 442 | 0.0704944178628389 | 13.914027149321265 | 0.065195 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.01_buf0.0_hold0_budget0.2 | 450 | 0.07177033492822965 | 13.933333333333334 | 0.06637500000000002 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.01_buf0.0_hold3_budget0.2 | 446 | 0.07113237639553428 | 13.923766816143498 | 0.06578500000000001 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.01_buf0.0_hold5_budget0.2 | 442 | 0.0704944178628389 | 13.914027149321265 | 0.065195 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.02_buf0.0_hold0_budget0.2 | 450 | 0.07177033492822965 | 13.933333333333334 | 0.06637500000000002 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.02_buf0.0_hold3_budget0.2 | 446 | 0.07113237639553428 | 13.923766816143498 | 0.06578500000000001 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.02_buf0.0_hold5_budget0.2 | 442 | 0.0704944178628389 | 13.914027149321265 | 0.065195 |
| validation | phase1c_turnover_controlled | k30_a2_gap0.0_buf0.0_hold0_budget0.2 | 862 | 0.13748006379585323 | 7.273781902552204 | 0.12714500000000004 |
| validation | phase1c_turnover_controlled | k30_a2_gap0.0_buf0.0_hold3_budget0.2 | 856 | 0.13652312599681019 | 7.254672897196262 | 0.12626000000000004 |
| validation | phase1c_turnover_controlled | k30_a2_gap0.0_buf0.0_hold5_budget0.2 | 848 | 0.13524720893141945 | 7.252358490566038 | 0.12508000000000002 |
| validation | phase1c_turnover_controlled | k30_a2_gap0.01_buf0.0_hold0_budget0.2 | 862 | 0.13748006379585323 | 7.273781902552204 | 0.12714500000000004 |
| validation | phase1c_turnover_controlled | k30_a2_gap0.01_buf0.0_hold3_budget0.2 | 856 | 0.13652312599681019 | 7.254672897196262 | 0.12626000000000004 |
| validation | phase1c_turnover_controlled | k30_a2_gap0.01_buf0.0_hold5_budget0.2 | 848 | 0.13524720893141945 | 7.252358490566038 | 0.12508000000000002 |

## 12. regime diagnostic-only 分组结果

| split | regime | regime_usage | method | fee_tax_adjusted_net_return | max_drawdown | action_count | turnover_proxy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| validation | caution | diagnostic_only | rank_rotate_top30 | -0.32711232384817446 | -0.6135774088916486 | 2076 | 1.1533333333333333 |
| validation | normal | diagnostic_only | rank_rotate_top30 | -0.0201816822555827 | -0.435523947487944 | 2244 | 1.0999999999999999 |
| validation | risk_off | diagnostic_only | rank_rotate_top30 | 2.5902133647082257 | -0.8238068202216494 | 3056 | 1.25761316872428 |
| validation | caution | diagnostic_only | rank_rotate_top50 | -0.2984096666112125 | -0.5828389129897686 | 3028 | 1.0093333333333332 |
| validation | normal | diagnostic_only | rank_rotate_top50 | -0.004181926787926726 | -0.420732620229168 | 3332 | 0.98 |
| validation | risk_off | diagnostic_only | rank_rotate_top50 | 2.6579472610356363 | -0.8161358622047088 | 4160 | 1.0271604938271603 |
| validation | caution | diagnostic_only | phase1c_simple_topk_no_turnover | 0.016286612582079973 | -0.5768428540348305 | 1866 | 1.0366666666666666 |
| validation | normal | diagnostic_only | phase1c_simple_topk_no_turnover | 0.10174813437438135 | -0.4693130104675318 | 1968 | 0.9647058823529411 |
| validation | risk_off | diagnostic_only | phase1c_simple_topk_no_turnover | 3.855018666000128 | -0.8345650634567976 | 2690 | 1.1069958847736625 |
| independent_test | caution | diagnostic_only | rank_rotate_top30 | 65.44954913033159 | -0.1772196462993476 | 1146 | 0.8883720930232557 |
| independent_test | normal | diagnostic_only | rank_rotate_top30 | 2611.4498037184553 | -0.3194659773892897 | 4112 | 0.8620545073375262 |
| independent_test | risk_off | diagnostic_only | rank_rotate_top30 | 0.8350807142917214 | 0.0 | 236 | 1.1238095238095238 |
| independent_test | caution | diagnostic_only | rank_rotate_top50 | 54.62571794825917 | -0.1555554839783868 | 1616 | 0.7516279069767442 |
| independent_test | normal | diagnostic_only | rank_rotate_top50 | 882.6658667042288 | -0.3058526769765113 | 6310 | 0.7937106918238994 |
| independent_test | risk_off | diagnostic_only | rank_rotate_top50 | 0.8298802299832169 | 0.0 | 338 | 0.9657142857142856 |
| independent_test | caution | diagnostic_only | phase1c_simple_topk_no_turnover | 73.00434083837226 | -0.12166236906381656 | 1122 | 0.869767441860465 |
| independent_test | normal | diagnostic_only | phase1c_simple_topk_no_turnover | 2993.8684383499904 | -0.33277227314017443 | 3560 | 0.7463312368972745 |
| independent_test | risk_off | diagnostic_only | phase1c_simple_topk_no_turnover | 0.9379237187177247 | 0.0 | 222 | 1.0571428571428572 |
| validation | caution | diagnostic_only | phase1c_turnover_controlled | 0.6735840512299756 | -0.5818839635049807 | 348 | 0.19333333333333327 |
| validation | normal | diagnostic_only | phase1c_turnover_controlled | 0.18095477617301303 | -0.5035374484683235 | 408 | 0.19999999999999996 |
| validation | risk_off | diagnostic_only | phase1c_turnover_controlled | 7.77170587561754 | -0.8490862809380534 | 510 | 0.2098765432098765 |
| independent_test | caution | diagnostic_only | phase1c_turnover_controlled | 100.22905472285447 | -0.09815427879174654 | 258 | 0.19999999999999996 |
| independent_test | normal | diagnostic_only | phase1c_turnover_controlled | 3007.9192590702737 | -0.34135254293756423 | 970 | 0.2033542976939203 |
| independent_test | risk_off | diagnostic_only | phase1c_turnover_controlled | 1.0416775421653224 | 0.0 | 42 | 0.19999999999999998 |

## 13. 验证命令与结果

- `python -m py_compile scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py`：通过。
- `python scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py`：普通沙箱若触发 `bwrap` 环境限制，则同一只读命令经授权在沙箱外复跑；本次最终通过。

## 14. Gate 结论

`request_user_decision_route_b_tradeoff`

原因：Replay produced a Route B tradeoff that requires user decision.

条件：`{'validation_net_improved': True, 'validation_turnover_reduced': True, 'validation_actions_reduced': True, 'validation_drawdown_not_worse': False, 'independent_no_net_reversal': True, 'independent_turnover_reduced': True, 'independent_actions_reduced': True, 'independent_drawdown_not_much_worse': True}`

## 15. 禁止事项遵守情况

本轮未重新训练 LTR，未重建 Phase1C score，未调整 Phase1C score，未重新选择 candidate，未重新打开 Phase2 regime gate 搜索，未使用 regime gate 控制组合，未新增数据源，未联网，未 provider refresh / publish，未 accepted latest switching，未改 frontend / API / monitor / database，未接 broker / quick-trade / orders / target position / target weight，未输出买入、卖出、持有、仓位建议、收益承诺、胜率或上涨概率语义，未做真实交易动作。

## 16. 需要审查者重点检查的点

- 是否接受本轮 period replay 的成本与换手 proxy 口径。
- blocked baseline 是否符合固定 frozen artifact 边界。
- validation-only 选参和 independent_test 终检是否严格分离。
- gate 是否应进入 Phase3B 或停止。
