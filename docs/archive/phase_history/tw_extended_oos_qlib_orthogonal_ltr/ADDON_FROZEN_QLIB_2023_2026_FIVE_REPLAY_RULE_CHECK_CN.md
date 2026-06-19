# 附加实验：2018-2022 Frozen Qlib 2023-2026 五规则回放检查

## 1. 新增规则

`top50_exit_one_worst_sell`：持仓未跌出 top50 则不卖；若多支持仓跌出 top50，每个 signal day 只卖当前 qlib raw rank 最差的一支；买入仍为 top50 内排名最高且未持有的一支。

## 2. Return Matrix

| window | original | top50_exit_all | top50_exit_one_worst_sell | one_sell_one_buy_correct | buggy |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023 | 0.195321 | 0.483173 | 0.996657 | 0.556141 | 0.56843 |
| 2024 | 0.049092 | 0.425244 | 0.880578 | 0.332462 | 0.437962 |
| 2025 | 0.188371 | 0.573832 | 0.841242 | 0.766504 | 0.783116 |
| 2026_ytd | 0.146704 | 1.018183 | 1.291884 | 0.558288 | 0.730199 |
| 2023_2026_ytd | 0.689555 | 5.439345 | 11.91966 | 6.129808 | 8.409143 |

## 3. Max Drawdown Matrix

| window | original | top50_exit_all | top50_exit_one_worst_sell | one_sell_one_buy_correct | buggy |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023 | -0.066695 | -0.152015 | -0.147837 | -0.101263 | -0.121801 |
| 2024 | -0.111881 | -0.178319 | -0.2214 | -0.181504 | -0.172513 |
| 2025 | -0.170779 | -0.208368 | -0.33408 | -0.211866 | -0.208816 |
| 2026_ytd | -0.05115 | -0.105686 | -0.150499 | -0.086899 | -0.082419 |
| 2023_2026_ytd | -0.224169 | -0.20882 | -0.352254 | -0.253445 | -0.254587 |

## 4. 初步判断

- 新规则与用户原始设想更一致：不跌出 top50 不卖，跌出 top50 也每天最多卖 1 支。
- 在 2023-2026YTD 合并窗口，新规则显著强于 original，但低于 all-sell top50_exit 与 buggy。
- 2026YTD 中，新规则收益低于 all-sell top50_exit，说明当多支持仓跌出 top50 时一次性清理在该窗口更有利；但新规则换手更慢，语义更接近生产约束。
- 该规则应加入后续 consolidated 正式矩阵。

## 5. Artifact

- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/addon_frozen_qlib_2023_2026_five_replay_rule_check/manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/addon_frozen_qlib_2023_2026_five_replay_rule_check/summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/addon_frozen_qlib_2023_2026_five_replay_rule_check/coverage.csv`
