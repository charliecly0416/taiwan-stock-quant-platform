# 附加实验：2018-2022 Frozen Qlib 2023-2026 分段四规则回放检查

## 1. 目的

检查 2026 top50_exit 高收益是否为单窗口特殊现象。输入为 E1 2018-2022 frozen qlib 原始 OOS score，不加 LTR，不重训。

## 2. Coverage

| window | dates | rows | daily min/median/max | score_na | duplicate |
| --- | ---: | ---: | --- | ---: | ---: |
| 2023 | 239 | 11950 | 50/50.0/50 | 0 | 0 |
| 2024 | 242 | 12100 | 50/50.0/50 | 0 | 0 |
| 2025 | 242 | 12100 | 50/50.0/50 | 0 | 0 |
| 2026_ytd | 79 | 3950 | 50/50.0/50 | 0 | 0 |
| 2023_2026_ytd | 802 | 40100 | 50/50.0/50 | 0 | 0 |

## 3. Return Matrix

| window | original | top50_exit | one_sell_one_buy_correct | one_sell_one_buy_buggy |
| --- | ---: | ---: | ---: | ---: |
| 2023 | 0.195321 | 0.483173 | 0.556141 | 0.56843 |
| 2024 | 0.049092 | 0.425244 | 0.332462 | 0.437962 |
| 2025 | 0.188371 | 0.573832 | 0.766504 | 0.783116 |
| 2026_ytd | 0.146704 | 1.018183 | 0.558288 | 0.730199 |
| 2023_2026_ytd | 0.689555 | 5.439345 | 6.129808 | 8.409143 |

## 4. Max Drawdown Matrix

| window | original | top50_exit | one_sell_one_buy_correct | one_sell_one_buy_buggy |
| --- | ---: | ---: | ---: | ---: |
| 2023 | -0.066695 | -0.152015 | -0.101263 | -0.121801 |
| 2024 | -0.111881 | -0.178319 | -0.181504 | -0.172513 |
| 2025 | -0.170779 | -0.208368 | -0.211866 | -0.208816 |
| 2026_ytd | -0.05115 | -0.105686 | -0.086899 | -0.082419 |
| 2023_2026_ytd | -0.224169 | -0.20882 | -0.253445 | -0.254587 |

## 5. 初步判断

- top50_exit 的 2026 高收益不是完全孤立：2023 与 2025 也为正，但 2026 明显最强。
- 2024 是重要反例：top50_exit 为负，说明该规则并非稳定单调有效。
- 2023_2026_ytd 合并窗口下 top50_exit 仍为正，但会跨多年从空仓起跑，不能替代逐年 OOS 稳健性。
- buggy 规则在 2026 强，但 2024 明显为负，仍只能作为 anomaly diagnostic。

## 6. Artifact

- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/addon_frozen_qlib_2023_2026_replay_rule_window_check/manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/addon_frozen_qlib_2023_2026_replay_rule_window_check/summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/addon_frozen_qlib_2023_2026_replay_rule_window_check/coverage.csv`
