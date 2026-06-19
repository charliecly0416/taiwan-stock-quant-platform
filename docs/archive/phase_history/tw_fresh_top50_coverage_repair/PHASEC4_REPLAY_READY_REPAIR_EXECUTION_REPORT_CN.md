# Phase C4 执行报告：Replay-Ready Repair

生成时间：2026-06-15T08:36:02+00:00

## 1. 执行边界

本轮只修复或解释 C3 replay-ready 缺口，不使用收益率判断策略优劣，不训练 qlib/LTR，不改前端/API，不触发 provider / accepted latest / monitor / 交易链路。

## 2. 缺失根因

| root_cause | row_count | instruments | repair_action |
| --- | --- | --- | --- |
| feature_warmup_insufficient_ret20_volatility20 | 20 | TW7769 | exclude_until_ret20_volatility20_warmup_available |
| price_join_or_calendar_gap | 5 | TW6919 | exclude_from_replay_ready_candidate |
| price_not_started_asof | 95 | TW7769 | exclude_until_local_price_starts |

结论：缺失集中在 `TW7769` 与 `TW6919`。`TW7769` 在 raw score 中早于本地价格起始日出现，2025-11-18 之后仍因 ret20 / volatility20 warmup 不足缺 adaptive score；`TW6919` 早期 5 行因特征 warmup / 价格映射审计未满足 replay-ready 条件。

## 3. 修复动作

- 将不可 replay-ready 行从 C4 repaired replay-ready artifact 中排除。
- 尝试检查同日 raw score rank > 150 top-up 候选。
- 结果：S2B raw score 在目标窗口每日只有 150 行，没有 rank > 150 候选；不训练、不重跑 qlib、不新增 provider 数据的前提下无法 top-up 到每日 150。

## 4. Coverage / Replay-Ready 结果

- 输入 rows：`30750`。
- 排除不可 replay-ready rows：`120`。
- 输出 rows：`30630`。
- daily repaired rows：`148 / 149.0 / 150`。
- daily replay-ready rows min：`148`。
- repair 后 missing current price：`0`。
- repair 后 missing next execution price：`0`。
- repair 后 missing adaptive score：`0`。

## 5. Gate

```text
phase_c4_replay_ready_repair_passed_with_coverage_below_150_explained
```

该 gate 表示 replay-ready 条件已清理干净，但每日 150 覆盖无法在现有 raw score artifact 内 top-up；若审查者要求每日 150，必须另开 qlib score/universe 合同修复，而不是在 C4 静默补数据。

## 6. 输出产物

- `data_tw/experiments/fresh_top50_coverage_repair/phasec4_missing_replay_ready_rows.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec4_missing_reason_summary.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec4_daily_coverage_summary.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec4_asof_eligibility_audit.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec4_replay_ready_audit.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec4_topup_feasibility_audit.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec4_summary.json`
