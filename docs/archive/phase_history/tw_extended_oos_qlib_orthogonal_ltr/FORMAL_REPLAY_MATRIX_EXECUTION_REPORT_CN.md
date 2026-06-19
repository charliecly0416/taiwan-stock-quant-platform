# 正式 Replay Matrix 执行报告

生成时间：`2026-06-16T08:08:19+00:00`

## 1. 结论

- 已固化正式 replay matrix 脚本：`scripts/run_extended_oos_formal_replay_matrix.py`。
- 脚本把模型分数与交易规则解耦：`candidate_rank` 只决定 qlib top50 universe / exit boundary；`buy_score` 只决定 top50 内买入顺序。
- 纯 qlib：`candidate_rank` 与 `buy_score` 都来自 qlib。
- LTR：`candidate_rank` 仍来自底座 qlib，`buy_score` 来自 LTR rerank score。
- 未训练 qlib/LTR，未调参，未触发 provider / accepted latest / frontend / API / monitor / 交易链路。

## 2. 解读口径

- 全部模型 / 全部策略的横向公平比较，只使用 `2026_ytd` 窗口。
- `2023` / `2024` / `2025` / `2023_2026_ytd` 只用于观察 `frozen_qlib_2018_2022` 这个 2018-2022 训练 qlib 底座的长窗口表现，不参与所有模型公平比较。
- LTR 类模型在本次正式矩阵中的可比测试窗口是 `2026_ytd`；不要把 LTR 的 `2023_2026_ytd` 行解释成覆盖了 2023-2026 全区间。
- `one_sell_one_buy_buggy_e8r` 只保留为历史 bug 诊断，不是有效策略证据。
- `top50_exit_one_worst_sell` 的语义是：初始建仓或持仓不足时允许补到目标持仓；满仓后只有持仓跌出 qlib top50，才卖出 full qlib rank 最差的一支，并买入 top50 内 buy_score 最高且未持有的股票。

## 3. 全模型公平比较：2026_ytd

| window | method | family | rule | net_return | max_dd | actions | buys | sells | skipped |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026_ytd | fresh_qlib_adaptive | qlib | original | 0.289419 | -0.037564 | 154 | 78 | 76 | 0 |
| 2026_ytd | fresh_qlib_adaptive | qlib | top50_exit_all | 0.960964 | -0.069702 | 141 | 73 | 68 | 0 |
| 2026_ytd | fresh_qlib_adaptive | qlib | top50_exit_one_worst_sell | 1.137728 | -0.113679 | 119 | 64 | 55 | 1 |
| 2026_ytd | fresh_qlib_adaptive | qlib | one_sell_one_buy_correct | 0.451474 | -0.091284 | 150 | 78 | 72 | 0 |
| 2026_ytd | fresh_qlib_adaptive | qlib | one_sell_one_buy_buggy_e8r | 0.48538 | -0.077397 | 150 | 78 | 72 | 0 |
| 2026_ytd | fresh_qlib_2025_ltr | ltr | original | 0.464734 | -0.058226 | 151 | 78 | 73 | 0 |
| 2026_ytd | fresh_qlib_2025_ltr | ltr | top50_exit_all | 0.488315 | -0.074029 | 151 | 78 | 73 | 0 |
| 2026_ytd | fresh_qlib_2025_ltr | ltr | top50_exit_one_worst_sell | 0.721856 | -0.138715 | 139 | 74 | 65 | 1 |
| 2026_ytd | fresh_qlib_2025_ltr | ltr | one_sell_one_buy_correct | 0.616126 | -0.11595 | 148 | 78 | 70 | 0 |
| 2026_ytd | fresh_qlib_2025_ltr | ltr | one_sell_one_buy_buggy_e8r | 0.527988 | -0.09931 | 149 | 78 | 71 | 0 |
| 2026_ytd | frozen_qlib_2025_ltr | ltr | original | 0.318632 | -0.083641 | 153 | 78 | 75 | 0 |
| 2026_ytd | frozen_qlib_2025_ltr | ltr | top50_exit_all | 0.33774 | -0.083761 | 153 | 78 | 75 | 0 |
| 2026_ytd | frozen_qlib_2025_ltr | ltr | top50_exit_one_worst_sell | 0.636371 | -0.133002 | 139 | 74 | 65 | 0 |
| 2026_ytd | frozen_qlib_2025_ltr | ltr | one_sell_one_buy_correct | 0.70133 | -0.118826 | 147 | 78 | 69 | 0 |
| 2026_ytd | frozen_qlib_2025_ltr | ltr | one_sell_one_buy_buggy_e8r | 0.478379 | -0.121555 | 148 | 78 | 70 | 0 |
| 2026_ytd | e4_frozen_qlib_2023_2025_ltr | ltr | original | 0.602499 | -0.071473 | 151 | 78 | 73 | 0 |
| 2026_ytd | e4_frozen_qlib_2023_2025_ltr | ltr | top50_exit_all | 0.630662 | -0.09658 | 150 | 78 | 72 | 0 |
| 2026_ytd | e4_frozen_qlib_2023_2025_ltr | ltr | top50_exit_one_worst_sell | 0.912442 | -0.160385 | 137 | 73 | 64 | 1 |
| 2026_ytd | e4_frozen_qlib_2023_2025_ltr | ltr | one_sell_one_buy_correct | 0.909337 | -0.106063 | 149 | 78 | 71 | 0 |
| 2026_ytd | e4_frozen_qlib_2023_2025_ltr | ltr | one_sell_one_buy_buggy_e8r | 0.96184 | -0.093164 | 148 | 78 | 70 | 0 |
| 2026_ytd | frozen_qlib_2018_2022 | qlib | original | 0.146704 | -0.05115 | 154 | 78 | 76 | 0 |
| 2026_ytd | frozen_qlib_2018_2022 | qlib | top50_exit_all | 1.018183 | -0.105686 | 141 | 74 | 67 | 1 |
| 2026_ytd | frozen_qlib_2018_2022 | qlib | top50_exit_one_worst_sell | 1.291884 | -0.150499 | 123 | 66 | 57 | 1 |
| 2026_ytd | frozen_qlib_2018_2022 | qlib | one_sell_one_buy_correct | 0.646665 | -0.051432 | 151 | 78 | 73 | 0 |
| 2026_ytd | frozen_qlib_2018_2022 | qlib | one_sell_one_buy_buggy_e8r | 0.730199 | -0.082419 | 150 | 78 | 72 | 0 |

## 4. Frozen Qlib 长窗口观察

以下结果只用于观察 `frozen_qlib_2018_2022` 在 2023-2026 YTD 的长窗口表现，不用于和 LTR 做全窗口横向比较。

| window | method | family | rule | net_return | max_dd | actions | buys | sells | skipped |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023 | frozen_qlib_2018_2022 | qlib | original | 0.185594 | -0.067964 | 474 | 238 | 236 | 0 |
| 2023 | frozen_qlib_2018_2022 | qlib | top50_exit_all | 0.463542 | -0.153197 | 460 | 232 | 228 | 0 |
| 2023 | frozen_qlib_2018_2022 | qlib | top50_exit_one_worst_sell | 0.875596 | -0.156035 | 437 | 223 | 214 | 0 |
| 2023 | frozen_qlib_2018_2022 | qlib | one_sell_one_buy_correct | 0.598127 | -0.109443 | 468 | 238 | 230 | 0 |
| 2023 | frozen_qlib_2018_2022 | qlib | one_sell_one_buy_buggy_e8r | 0.541223 | -0.126257 | 469 | 238 | 231 | 0 |
| 2024 | frozen_qlib_2018_2022 | qlib | original | 0.049092 | -0.111881 | 480 | 241 | 239 | 0 |
| 2024 | frozen_qlib_2018_2022 | qlib | top50_exit_all | 0.427404 | -0.178319 | 472 | 239 | 233 | 0 |
| 2024 | frozen_qlib_2018_2022 | qlib | top50_exit_one_worst_sell | 0.880714 | -0.2214 | 438 | 223 | 215 | 3 |
| 2024 | frozen_qlib_2018_2022 | qlib | one_sell_one_buy_correct | 0.481433 | -0.141225 | 474 | 240 | 234 | 0 |
| 2024 | frozen_qlib_2018_2022 | qlib | one_sell_one_buy_buggy_e8r | 0.437962 | -0.172513 | 475 | 241 | 234 | 0 |
| 2025 | frozen_qlib_2018_2022 | qlib | original | 0.188371 | -0.170779 | 480 | 241 | 239 | 0 |
| 2025 | frozen_qlib_2018_2022 | qlib | top50_exit_all | 0.591328 | -0.208368 | 470 | 238 | 232 | 0 |
| 2025 | frozen_qlib_2018_2022 | qlib | top50_exit_one_worst_sell | 0.930258 | -0.33408 | 431 | 220 | 211 | 4 |
| 2025 | frozen_qlib_2018_2022 | qlib | one_sell_one_buy_correct | 0.63094 | -0.196 | 476 | 241 | 235 | 0 |
| 2025 | frozen_qlib_2018_2022 | qlib | one_sell_one_buy_buggy_e8r | 0.782001 | -0.208816 | 475 | 241 | 234 | 0 |
| 2023_2026_ytd | frozen_qlib_2018_2022 | qlib | original | 0.670197 | -0.223893 | 1600 | 801 | 799 | 0 |
| 2023_2026_ytd | frozen_qlib_2018_2022 | qlib | top50_exit_all | 5.436295 | -0.211424 | 1556 | 782 | 774 | 2 |
| 2023_2026_ytd | frozen_qlib_2018_2022 | qlib | top50_exit_one_worst_sell | 10.547596 | -0.334712 | 1439 | 724 | 715 | 16 |
| 2023_2026_ytd | frozen_qlib_2018_2022 | qlib | one_sell_one_buy_correct | 10.876032 | -0.263564 | 1594 | 801 | 793 | 0 |
| 2023_2026_ytd | frozen_qlib_2018_2022 | qlib | one_sell_one_buy_buggy_e8r | 8.916007 | -0.254576 | 1594 | 801 | 793 | 0 |

## 5. 完整原始矩阵

完整 CSV 仍保留所有生成行，用于追溯和审计；正式解读以上述两个区块为准。

## 6. 产物

- manifest: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/formal_replay_manifest.json`
- summary: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/formal_replay_summary.csv`
- daily_nav: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/formal_replay_daily_nav.csv`
- actions: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/formal_replay_actions.csv`
- snapshots: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/formal_replay_position_snapshots.csv`
- coverage: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/formal_replay_coverage_audit.csv`
- integrity: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/formal_replay_position_integrity_audit.csv`
- rule_contract: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/formal_replay_rule_contract.csv`
- forbidden: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/formal_replay_forbidden_field_audit.csv`
- report: `docs/tw_extended_oos_qlib_orthogonal_ltr/FORMAL_REPLAY_MATRIX_EXECUTION_REPORT_CN.md`
