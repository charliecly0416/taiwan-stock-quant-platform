# 附加实验：Fresh Qlib 2025H2 回放规则检查

窗口：`2025-07-01..2025-12-31`

## 覆盖

- date_count: `126`; top50 rows: `6236`; daily min/median/max: `48 / 50.0 / 50`。
- score_na: `0`; duplicate_key_count: `0`; dates_below_50: `62`。

## 结果

| rule | net_return | max_drawdown | actions | buys | sells | turnover |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| original | 0.406208 | -0.085205 | 250 | 125 | 125 | 24.81977 |
| top50_exit | 0.823545 | -0.126029 | 195 | 100 | 95 | 19.540243 |
| one_sell_one_buy_correct | 0.745607 | -0.117784 | 244 | 125 | 119 | 24.321801 |
| one_sell_one_buy_buggy_e8r | 0.524584 | -0.124917 | 245 | 125 | 120 | 24.331003 |

## 初步判断

- 2025H2 也出现高收益规则，但幅度低于 2026 的 fresh top50_exit `0.960964`。
- 本窗口最高为 `top50_exit`，收益 `0.823545`；`one_sell_one_buy_correct` 次之，收益 `0.745607`。
- buggy 没有异常领先 correct，因此 2025H2 不支持 E8R 那种 buggy 误打误撞优势具有稳定性。

## Artifact

- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/addon_fresh_qlib_2025h2_replay_rule_check/manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/addon_fresh_qlib_2025h2_replay_rule_check/summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/addon_fresh_qlib_2025h2_replay_rule_check/coverage_audit.json`
