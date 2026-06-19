# 附加实验：2018-2022 Frozen Qlib 纯底座四规则回放检查

窗口：`2026-01-01..2026-05-07`

## 覆盖

- date_count: `79`; top50 rows: `3950`; daily min/median/max: `50 / 50.0 / 50`。
- score_na: `0`; duplicate_key_count: `0`。

## 结果

| rule | net_return | max_drawdown | actions | buys | sells | turnover |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| original | 0.146704 | -0.05115 | 154 | 78 | 76 | 15.111736 |
| top50_exit | 1.018183 | -0.105686 | 141 | 74 | 67 | 14.010484 |
| one_sell_one_buy_correct | 0.558288 | -0.086899 | 150 | 78 | 72 | 14.734509 |
| one_sell_one_buy_buggy_e8r | 0.730199 | -0.082419 | 150 | 78 | 72 | 14.833304 |

## 初步判断

- 2018-2022 frozen qlib 纯底座在 original 规则下较弱，仅 `0.146704`，这与 E4 control 一致。
- 但在 top50_exit 规则下出现新的异常高收益 `1.018183`，甚至高于 fresh qlib 2026 top50_exit 的 `0.960964`。这说明 top50_exit 慢卖/长持规则本身可能是异常收益核心，必须正式审计。
- one_sell_one_buy_buggy_e8r 为 `0.730199`，高于 correct 的 `0.558288`，说明 buggy/中位 rank 保留现象不只出现在 E4，但仍不能作为合法策略证据。

## Artifact

- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/addon_frozen_qlib_2018_2022_replay_rule_check/manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/addon_frozen_qlib_2018_2022_replay_rule_check/summary.csv`
