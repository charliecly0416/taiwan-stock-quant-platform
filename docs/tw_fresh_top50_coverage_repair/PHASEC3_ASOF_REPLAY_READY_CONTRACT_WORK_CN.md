# Phase C3：Repaired Fresh Top50 Asof-Aware 与 Replay-Ready 合同审计工作文档

生成日期：2026-06-15

## 1. 背景

Fresh Top50 覆盖修复主线已经确认：

```text
原 fresh top50 adaptive 的 replay-ready 覆盖被 S2B post-score universe filter 过度压缩；
修复后 repaired fresh top50 daily rows 恢复到 150 / 150 / 150；
但 repaired fresh top50 暂不应直接产品化或切换前端默认。
```

原因是：当前窗口 `2025-07-01..2026-05-07` 不能被当成严格策略收益证明窗口。下一步要验证的不是收益率，而是数据和回放口径是否干净、可持续。

## 2. 本阶段目标

本阶段只回答一个问题：

```text
repaired fresh top50 的 150 支覆盖，是否在历史每个 asof 上都合法、可交易、可回放？
```

也就是说，本阶段验证的是：

- coverage 是否稳定；
- 是否符合 asof-aware universe；
- 是否没有未来上市/未来进入股票倒灌；
- replay-ready 条件是否完整；
- 这套修复逻辑是否能作为后续策略比较和产品化前置合同。

本阶段不证明：

- repaired fresh top50 收益率更高；
- repaired fresh top50 应该切成默认策略；
- repaired fresh top50 比 Phase1C 或 LTR 更优。

## 3. 核心概念

### 3.1 Asof-Aware Universe

`asof-aware universe` 指站在某个历史日期，只允许纳入当时已经真实存在、真实可交易、且在 provider/instrument 有效期内的股票。

例如：

```text
TW7769 如果 provider 起始日是 2024-11-01，
那么它不能出现在 2023 年的 historical replay candidate 中。
```

否则就是用今天的静态 150 名单倒灌过去，会造成未来信息污染。

### 3.2 Replay-Ready Coverage

`replay-ready coverage` 不是“CSV 里有没有一行”，而是某个 `date + symbol` 是否真的可以进入 next-day replay。

最低条件：

```text
有 qlib score
有当日 close / vwap 等价格
有下一交易日执行价格
有策略所需特征，例如 ret20 / volatility20 / TWII_ret20
symbol 在该 date 的 instrument 有效期内
symbol 在该 date 符合 asof-aware universe
没有被错误 filter 排除
```

## 4. 执行范围

### 4.1 必须审计的 artifact

输入：

```text
data_tw/experiments/fresh_top50_coverage_repair/phasec1_repaired_replay_ready_scores.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_coverage_by_day.csv
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt
qlib_pipeline/data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt
```

可辅助读取：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/
qlib_pipeline/data_tw/experiments/option_c_ops/*/candidate_normalized/
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_raw_score_rank.csv
```

### 4.2 审计窗口

至少覆盖：

```text
2025-07-01..2026-05-07
```

如果资源允许，可扩展做 coverage-only 多年份审计：

```text
2022
2023
2024
2025
2026 YTD
```

注意：多年份审计只看 coverage / legality / replay-ready，不把收益率作为策略优劣证据。

## 5. 执行者任务

执行者需要完成以下工作。

### 5.1 构造 asof-aware eligibility 检查

对 repaired fresh top50 每个 `date + instrument` 检查：

```text
instrument 是否在 option_c_150_qlib_bin/instruments/all.txt 有效期内；
date 是否落在 instrument start/end 之间；
如果使用 tw_liquid_dyn 辅助，则检查 date 是否落在对应动态区间内；
如果不使用 tw_liquid_dyn 作为硬门槛，必须解释原因。
```

输出逐行审计：

```text
data_tw/experiments/fresh_top50_coverage_repair/phasec3_asof_eligibility_audit.csv
```

建议字段：

```text
date,instrument,has_repaired_row,in_option_c_instrument_range,in_tw_liquid_dyn_range,eligibility_status,reason
```

### 5.2 构造 replay-ready 条件检查

对每个 `date + instrument` 检查：

```text
has_qlib_score
has_current_price
has_next_execution_price
has_adaptive_score
has_ret20
has_volatility20
has_twii_ret20
feature_complete
replay_ready
```

输出：

```text
data_tw/experiments/fresh_top50_coverage_repair/phasec3_replay_ready_audit.csv
```

### 5.3 输出每日覆盖汇总

输出：

```text
data_tw/experiments/fresh_top50_coverage_repair/phasec3_daily_coverage_summary.csv
```

建议字段：

```text
date,total_repaired_rows,eligible_rows,replay_ready_rows,ineligible_rows,missing_next_price_rows,feature_incomplete_rows
```

### 5.4 输出最终 summary

输出：

```text
data_tw/experiments/fresh_top50_coverage_repair/phasec3_summary.json
docs/tw_fresh_top50_coverage_repair/PHASEC3_ASOF_REPLAY_READY_CONTRACT_EXECUTION_REPORT_CN.md
```

报告必须明确：

```text
是否存在未来上市/无效期股票倒灌；
是否存在有 score 但不可 next-day replay 的记录；
是否 repaired 150 覆盖都能被解释为合法；
如果不能，具体问题是什么；
是否建议进入前端只读展示合同；
是否仍需继续修数据合同。
```

## 6. 禁止事项

本阶段不得：

- 训练 qlib；
- 训练 LTR；
- 用本阶段收益率证明策略优劣；
- 修改前端默认策略；
- 修改 API；
- 修改 accepted latest；
- 触发 provider refresh / publish；
- 触发 monitor / broker / orders / quick-trade；
- 输出真实买卖、仓位、收益承诺、胜率或上涨概率语义。

## 7. 审查者任务

审查者必须重点判断：

1. 执行者是否把收益率与 coverage 审计混在一起；
2. asof-aware eligibility 是否真的检查了 instrument 有效期；
3. replay-ready 是否包含 next-day execution price；
4. 是否存在未来股票倒灌；
5. 是否将 `tw_liquid_dyn` 与 `accepted 150` 的角色解释清楚；
6. 是否能给出明确 gate：

```text
phase_c3_asof_replay_ready_contract_passed
```

或：

```text
phase_c3_blocked_requires_universe_contract_repair
```

## 8. Gate

通过条件：

```text
repaired fresh top50 在目标窗口内 daily repaired rows = 150；
eligible rows 接近或等于 150，任何低于 150 的日期都有合理解释；
replay_ready rows 接近或等于 eligible rows；
无未来上市/无效期股票倒灌；
无 next-day execution 价格缺失导致的不可回放记录；
报告明确区分 coverage 审计与收益比较。
```

不通过条件：

```text
发现 symbol 在 instrument 起始日前进入 replay；
发现大量 repaired rows 不符合 asof-aware eligibility；
发现 replay-ready 依赖未来信息或缺下一交易日价格；
执行者把训练窗口收益率当成策略优劣证据。
```

## 9. 后续路线

如果 C3 通过：

1. 可以准备“前端只读展示合同”，把 repaired fresh top50 作为研究候选展示；
2. 仍不直接切默认；
3. 后续严格策略收益比较必须另开 OOS / walk-forward 主线。

如果 C3 不通过：

1. 先修 universe 合同；
2. 不进入前端展示；
3. 不继续做收益比较。

一句话原则：

```text
先证明数据和回放口径干净，再讨论策略是否更强。
```
