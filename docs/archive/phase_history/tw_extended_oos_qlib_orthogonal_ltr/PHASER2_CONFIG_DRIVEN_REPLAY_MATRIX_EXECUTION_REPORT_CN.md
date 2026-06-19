# Phase R2 Config-driven Replay Matrix 执行报告

生成日期：2026-06-16

## 1. 执行范围

本次仅执行 R2：从 `configs/tw_modular_replay_matrix.yaml` 读取标准 `ModelSignalArtifact manifest`，生成 config-driven replay matrix。

未训练、未调参、未重算模型分数；未修改旧 formal replay matrix；未修改前端、日更或默认策略。

## 2. 输入与输出

- config: `configs/tw_modular_replay_matrix.yaml`
- output_dir: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix`
- baseline_dir: `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix_windowed`

## 3. Parity 结果

| check | baseline_rows | modular_rows | status | details |
| --- | ---: | ---: | --- | --- |
| summary | 25 | 25 | pass |  |
| daily_nav | 1975 | 1975 | pass |  |
| actions | 3651 | 3651 | pass | direct window filter: baseline.window == modular.window == 2026_ytd |

## 4. Action-level parity

- filter_policy: `direct_window_filter_2026_ytd`
- baseline_total_rows: `23571`
- baseline_filtered_rows: `3651`
- baseline_unique_action_keys: `3651`
- modular_action_rows: `3651`
- modular_unique_action_keys: `3651`
- baseline_not_modular_count: `0`
- modular_not_baseline_count: `0`
- duplicate_baseline_action_key_count: `0`
- duplicate_modular_action_key_count: `0`
- value_mismatch_count: `0`

Baseline actions 已通过 R10 window adapter 标准化为带 `window` 字段的独立 artifact；action parity 直接过滤 baseline/modular `window=2026_ytd` 后比较 key/value。

## 5. 结论

- parity_status: `pass`
- Replay engine 只读取标准字段：`candidate_rank`、`buy_score`、`full_qlib_rank` 等 ModelSignal contract 字段；
- 不读取 legacy 私有分数字段；
- `one_sell_one_buy_buggy_e8r` 仍仅作为 diagnostic；
- R1 full-rank fallback 风险已带入 R2，最终以 2026_ytd parity 是否完全一致为门槛。

## 6. 禁止事项记录

- 未训练 qlib 或 LTR；
- 未调参；
- 未重算模型分数；
- 未根据收益筛选模型；
- 未改默认策略；
- 未修改前端；
- 未修改日更脚本；
- 未触发 provider publish；
- 未切换 accepted latest；
- 未触发 monitor scan/config save；
- 未触发 broker、quick-trade 或 order。
