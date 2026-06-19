# Phase S1B0R 审查意见与 Phase S1B1 工作文档

生成日期：2026-06-14

## 1. 审查范围

主线依据：`docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md`

前置审查：`docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B0_REVIEW_AND_USER_DECISION_CN.md`

审查入口：`docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B0R_CALENDAR_PRICE_REPAIR_EXECUTION_REPORT_CN.md`

本轮只审查 calendar / price trading-day 修复诊断与 dynamic universe feasibility 重算，不审查任何训练或 score 生成结果。

## 2. 审查结论

结论：`通过，允许进入 Phase S1B1，但 S1B1 只允许生成 qlib walk-forward score/rank，不允许训练 LTR、构建 LTR 样本或回放。`

Gate：

```text
s1b0r_pass_request_s1b1_qlib_walk_forward_score_generation
```

通过理由：

1. S1B0R 证明原 `selected count < 50` 的 63 个低覆盖日期均不在 qlib calendar，属于 calendar / price trading-day 口径错配，不是 dynamic universe 根本不可行。
2. 修复后 scoring calendar 使用 `qlib day.txt ∩ TWII normalized price calendar`，口径可审查且不联网。
3. 修复后 dynamic universe 最低 selected count 为 `145`，中位数为 `150`，没有 selected count < 50 的日期。
4. S1B0R 未训练 qlib/LTR、未生成 score/rank、未构建样本、未回放、未调参、未改前端/API、未触发 provider/accepted latest/monitor/交易链路。

## 3. 核验证据

### 3.1 低覆盖日期修复

`phase_s1b0r_gate_summary.json`：

- low coverage dates checked：`63`
- low coverage not in qlib calendar：`63`
- low coverage not in TWII price calendar：`53`
- in both qlib and TWII but stock breadth < 50：`0`

抽查 `phase_s1b0r_low_coverage_date_diagnosis.csv`，低覆盖日期均标记为 `exclude_from_scoring_calendar`。

### 3.2 修复后 dynamic universe

`phase_s1b0r_dynamic_universe_feasibility_repaired_daily.csv`：

- daily rows：`2470`
- selected count min：`145`
- selected count median：`150`
- selected count mean：约 `149.67`
- selected count < 50：`0`
- selected count < 145：`0`
- selected count < 150：`619`

审查判断：S1 dynamic universe 应冻结为 `up to 150`，最低要求 `selected_count >= 145`。这比强行要求每天刚好 150 更符合真实交易日和价格可用性，也避免把少数缺价/历史不足股票错误地补入 universe。

## 4. Findings

### High

无阻断项。

### Medium

S1B1 仍必须处理两个降级表述：

1. 严格 walk-forward qlib score 无法覆盖 `2015-05-04..2016-12-31`，因此 S1 LTR scored train rows 应从 `2017-01-01` 起，不能称作完整 2015-2020 LTR train score 覆盖。
2. dynamic universe 是 `up to 150`，不是每日强制 150；后续报告必须披露 selected count 分布。

### Low

修复口径依赖本地 `TWII.csv` 作为价格日历。该口径可以接受，但后续 S1B1/S1B2 报告必须继续记录 calendar source，不得静默换 calendar。

## 5. 台股只读安全边界审查

### Findings

未发现 broker、quick-trade、orders、target-position、target-weight、monitor write、provider publish/refresh、accepted latest switching。

### Network Audit

本轮为本地只读诊断，未涉及前端/API/E2E，未要求 network audit。

### Text / Agent Semantics

报告中涉及“训练、score、回放、买卖、仓位、收益”等词均处于研究设计、禁止事项或历史模拟语境，不构成实际交易建议、收益承诺、胜率或上涨概率承诺。

### Verdict

只读安全边界通过。

## 6. Phase S1B1 工作文档：Qlib Walk-Forward Score/Rank 生成

### 6.1 S1B1 目标

只生成 S1 所需 qlib walk-forward score/rank 产物，并验证 coverage / leakage / boundary。

S1B1 不训练 LTR，不构建 LTR 样本，不跑组合回放，不做策略比较。

### 6.2 冻结 calendar 与 universe

Scoring calendar：

```text
qlib day.txt ∩ TWII normalized price calendar
```

来源：

- qlib calendar：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt`
- price calendar：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv`

Dynamic universe：

```text
asof active instrument range
+ same-day price
+ >=60 historical rows
+ trailing 60-day value = mean(vwap_or_close * volume)
+ top up to 150
```

容忍度冻结：

```text
selected_count >= 145 for every scoring date
```

如果 S1B1 实际生成时出现 selected_count < 145，必须停止并报告，不得补齐未来股票或改用 static accepted 150。

### 6.3 冻结 walk-forward folds

执行者必须按以下 fold 生成 qlib score/rank：

| fold | qlib train window | score window | LTR 用途 |
| --- | --- | --- | --- |
| WF-2017 | `2015-05-04..2016-12-31` | `2017-01-01..2017-12-31` | train score |
| WF-2018 | `2015-05-04..2017-12-31` | `2018-01-01..2018-12-31` | train score |
| WF-2019 | `2015-05-04..2018-12-31` | `2019-01-01..2019-12-31` | train score |
| WF-2020 | `2015-05-04..2019-12-31` | `2020-01-01..2020-12-31` | train score |
| WF-VAL | `2015-05-04..2020-12-31` | `2021-01-01..2022-12-31` | validation score |
| TEST | frozen recorder `950741cfd5f14ee5a05464fec3e12e0a` | `2023-01-01..2025-06-30` | test score / baseline |

`2015-05-04..2016-12-31` 不生成 LTR qlib score/rank，后续 LTR train scored rows 从 `2017-01-01` 开始。

### 6.4 qlib 参数冻结

必须沿用：`qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml`

不得搜索参数，不得更换 handler、feature、label、provider 或 model family。

核心参数：

- model：`qlib.contrib.model.gbdt.LGBModel`
- handler：`qlib.contrib.data.handler.Alpha158`
- loss：`mse`
- learning_rate：`0.05`
- colsample_bytree：`0.8879`
- subsample：`0.8789`
- lambda_l1：`205.6999`
- lambda_l2：`580.9768`
- max_depth：`8`
- num_leaves：`210`
- num_threads：`8`

### 6.5 S1B1 必须输出

建议目录：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/
```

必须产物：

```text
phase_s1b1_fold_training_manifest.csv
phase_s1b1_qlib_wf_scores.csv
phase_s1b1_score_rank_coverage_by_split.csv
phase_s1b1_score_rank_coverage_by_fold.csv
phase_s1b1_universe_selected_count_audit.csv
phase_s1b1_leakage_boundary_audit.json
phase_s1b1_gate_summary.json
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1_QLIB_WF_SCORE_GENERATION_EXECUTION_REPORT_CN.md
```

`phase_s1b1_qlib_wf_scores.csv` 至少包含：

- `date`
- `instrument`
- `qlib_score_raw`
- `qlib_rank`
- `fold_id`
- `qlib_train_start`
- `qlib_train_end`
- `score_window_start`
- `score_window_end`
- `calendar_policy`
- `universe_policy`
- `is_test_frozen_pred`

### 6.6 S1B1 Coverage 要求

必须报告：

- train scored coverage：`2017-01-01..2020-12-31`
- validation coverage：`2021-01-01..2022-12-31`
- test coverage：`2023-01-01..2025-06-30`
- selected count min / median / max
- score missing count
- rank missing count
- duplicate date/instrument count
- fold overlap / gap
- 是否使用 S1 test 反馈：必须为 false

### 6.7 S1B1 禁止事项

- 不训练 LTR；
- 不构建 LTR 样本；
- 不跑组合回放；
- 不做策略比较；
- 不调 qlib/LTR 参数；
- 不改前端/API；
- 不联网；
- 不触发 provider refresh/publish；
- 不切换 accepted latest；
- 不触发 monitor config save / scan / alerts write；
- 不连接 broker、orders、quick-trade；
- 不输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率。

### 6.8 S1B1 Gate

S1B1 只能给以下 gate 之一：

```text
s1b1_qlib_wf_scores_pass_request_s1b2_ltr_sample_build
s1b1_qlib_wf_scores_data_insufficient
s1b1_blocked_by_leakage_or_scope_violation
```

## 7. 给执行者的一句话

请执行 Phase S1B1：只按冻结 calendar、dynamic up-to-150 universe 和 walk-forward folds 生成 qlib score/rank，并输出 coverage/leakage/boundary 审计；不得训练 LTR、不得构建 LTR 样本、不得回放、不得调参、不得改前端/API、不得 provider/accepted latest/monitor/交易链路；完成后提交 `PHASES1B1_QLIB_WF_SCORE_GENERATION_EXECUTION_REPORT_CN.md` 等待审查。
