# Fresh Top50 Adaptive 覆盖修复与 Full Universe 复核主线文档

生成日期：2026-06-15

## 1. 背景

Phase1C anchor 精确复刻已经完成，结论是：

```text
Phase1C anchor 可复现，可作为研究基准；
前端可继续保留 phase1c_ltr_simple_daily 作为可选模拟策略默认展示；
但不能仅凭当前证据切换或宣称绝对最优。
```

随后对 full universe / common universe 的覆盖差异做了补充核查，发现一个更基础的问题：

```text
old Phase1C LTR 与 fresh top50 adaptive 的 full universe 对比中，双方可用股票覆盖并不接近。
```

实际统计来自：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_coverage_audit.json
```

关键覆盖结果：

```text
测试窗口：2025-07-01..2026-05-07，共 205 个交易日

old Phase1C LTR keys:        30475
fresh top50 adaptive keys:   22613
fresh LTR keys:              22474
old ∩ fresh top50:           22523
old - fresh top50:            7952
fresh top50 - old:              90
old ∩ fresh top50 ∩ fresh LTR: 22474

old LTR daily rows:       min 147 / median 149 / max 150
fresh top50 daily rows:   min 88  / median 109 / max 150
fresh LTR daily rows:     min 87  / median 109 / max 149
```

这说明：

```text
当前 full universe 下，old Phase1C LTR 覆盖接近每日 150 支；
fresh top50 adaptive 覆盖中位数只有 109 支；
因此 full universe 的收益比较可能被 fresh top50 coverage 不足影响。
```

注意：这不是说 LTR 在同一个 qlib 产物上比 qlib 看得更多。更准确地说：

```text
old Phase1C LTR 使用旧 frozen Phase1C score artifact；
fresh top50 adaptive 使用 fresh replay-ready artifact；
两者来自不同批次/口径的 score/replay-ready 产物。
```

因此，下一步应先修 fresh top50 adaptive 的覆盖，再做 full universe 复核。

---

## 2. 本主线目标

本主线目标是回答：

```text
如果 fresh top50 adaptive 也能稳定覆盖接近每日 150 支股票，
Phase1C LTR simple 在 full universe 下是否仍然更高收益、更低回撤？
```

这比直接看 common universe 更贴近用户目标，因为真实使用时用户关心的是策略自己的实际可用股票池和最终收益风险。

但本主线仍必须保留 common universe 作为审计辅助，用于区分：

```text
排序能力差异
覆盖差异
回放口径差异
```

---

## 3. 重要边界

本主线不是：

- 重新训练 qlib；
- 重新训练 LTR；
- 改 Phase1C anchor；
- 改前端默认策略；
- 新增策略；
- 引入正交数据；
- provider refresh / publish；
- accepted latest switching；
- monitor / broker / orders / quick-trade。

除非用户另行批准，执行者不得改前端或产品文案。

本主线可以做：

- 只读审计 fresh replay-ready 覆盖不足原因；
- 修复离线 replay-ready 构建逻辑或复用已有本地 qlib score/price/feature artifact；
- 生成 repaired fresh top50 adaptive replay-ready artifact；
- 在相同 `2025-07-01..2026-05-07` 窗口复跑只读历史 replay；
- 对比 repaired fresh top50 adaptive 与 Phase1C anchor。

如果修复必须触发真实数据拉取、provider publish、accepted latest switching 或线上状态改变，必须停止并请用户确认。

---

## 4. 用户第一性原则

最终结论必须简单清楚：

```text
fresh top50 覆盖不足是不是事实？
不足原因是什么？
修复后 fresh top50 能否接近每日 150 支？
修复后 Phase1C LTR simple 是否仍然更值得作为前端默认展示？
是否需要修改前端？
```

普通用户不需要看到复杂 coverage 表；审计报告中保留证据即可。

---

## 5. Phase 设计

### Phase C0：覆盖差异只读审计

目标：只读查清 fresh top50 adaptive 覆盖为什么只有 `min 88 / median 109 / max 150`。

必须审计：

1. fresh replay-ready artifact 的来源：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_replay_ready_scores.csv
```

2. old Phase1C artifact 的来源：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
```

3. 对 `2025-07-01..2026-05-07` 每日覆盖拆分：

```text
fresh_top50 有无 qlib score
fresh_top50 有无 adaptive_score_baseline
fresh_top50 有无 price
fresh_top50 有无 required feature
fresh_top50 是否被 replay-ready 过滤
fresh_top50 是否受 static/dynamic universe policy 限制
fresh_top50 是否受 accepted symbols / selected_count / active date range 影响
```

4. 识别 `old - fresh_top50` 的 7952 个 key 到底为什么不在 fresh 中：

```text
缺 fresh qlib score？
缺 fresh replay-ready row？
缺价格？
缺 feature？
被 fresh universe policy 过滤？
```

5. 识别 `fresh_top50 - old` 的 90 个 key，用于确认差异是否单向。

C0 输出：

```text
docs/tw_fresh_top50_coverage_repair/PHASEC0_COVERAGE_AUDIT_EXECUTION_REPORT_CN.md
data_tw/experiments/fresh_top50_coverage_repair/phasec0_coverage_by_day.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec0_missing_reason_summary.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec0_old_minus_fresh_sample.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec0_summary.json
```

C0 禁止：

- 不修复；
- 不回放；
- 不训练；
- 不改前端/API；
- 不触发任何线上数据链路。

### Phase C1：Fresh Top50 覆盖修复与只读 replay

进入条件：C0 审查通过，且确认覆盖不足可以通过本地离线 artifact 修复。

目标：让 repaired fresh top50 adaptive 在同窗口覆盖接近：

```text
min >= 145
median >= 149
max <= 150
```

如果确实因合理可交易性、停牌、上市时间等原因无法达到该门槛，必须说明原因，不能强行填充。

C1 允许：

- 修复离线 replay-ready 构建逻辑；
- 复用本地已有 qlib score、price、feature；
- 生成 repaired replay-ready scores；
- 只读复跑 `2025-07-01..2026-05-07` full universe replay；
- 生成 repaired full / common universe 指标。

C1 必须对比：

```text
Phase1C anchor simple full
original fresh top50 adaptive full
repaired fresh top50 adaptive full
original fresh LTR full（如可用）
repaired fresh LTR full（如可用且不需重训）
```

C1 必须输出：

```text
docs/tw_fresh_top50_coverage_repair/PHASEC1_REPAIR_AND_REPLAY_EXECUTION_REPORT_CN.md
data_tw/experiments/fresh_top50_coverage_repair/phasec1_repaired_replay_ready_scores.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_coverage_by_day.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_full_universe_metrics.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_common_universe_metrics.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_daily_nav.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_action_audit.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_summary.json
```

C1 禁止：

- 不重新训练 qlib；
- 不重新训练 LTR；
- 不改变 Phase1C anchor；
- 不改变费用税费、next-day execution、持仓数量等 replay 口径；
- 不改前端/API；
- 不触发 provider/accepted latest/monitor/交易链路。

### Phase C2：审查与前端影响判断

审查者必须回答：

1. fresh top50 覆盖不足原因是否查清；
2. repaired fresh top50 是否真的接近每日 150 支；
3. repaired fresh top50 full universe 是否追上 Phase1C anchor；
4. repaired fresh top50 common universe 是否追上 Phase1C anchor；
5. Phase1C LTR simple 当前前端默认展示是否需要调整；
6. 是否可以进入正交数据主线。

建议判定规则：

```text
若 repaired fresh top50 full 和 common 都仍明显弱于 Phase1C anchor，
则保留 phase1c_ltr_simple_daily 前端默认展示更有依据。

若 repaired fresh top50 full 接近或超过 Phase1C anchor，
则不应再说 LTR simple 明显更优，只保留为可选模拟策略。

若 repaired fresh top50 无法修到接近 150，
则必须说明是合理可交易性限制还是 artifact 构建缺陷。
```

C2 输出：

```text
docs/tw_fresh_top50_coverage_repair/PHASEC2_REVIEW_AND_FRONTEND_DECISION_CN.md
```

---

## 6. 与正交数据主线的关系

本主线完成前，不建议直接把正交数据进入策略训练。

原因：当前 fresh baseline 覆盖不足会污染后续判断。如果 baseline 自身覆盖有缺陷，引入法人筹码、融资融券、月营收 YoY 后，很难判断收益改善来自新数据，还是来自覆盖修复。

推荐顺序：

```text
先完成 Fresh Top50 coverage repair；
再进入正交数据 PIT archive 审计；
最后再判断是否把正交数据加入 risk confirmation / decision filter / LTR / decision model。
```

---

## 7. 给审查者的一句话

请按 `docs/tw_fresh_top50_coverage_repair/FRESH_TOP50_COVERAGE_REPAIR_MAINLINE_CN.md` 先撰写 Phase C0/C1 工作文档，冻结 fresh top50 adaptive 覆盖审计、离线修复、同窗口 full/common replay 的范围和禁止事项；重点查清为什么 fresh replay-ready 在 `2025-07-01..2026-05-07` 只有 `88/109/150` 覆盖，并防止执行者改 Phase1C anchor、重训模型、改前端或触发 provider/accepted latest/monitor/交易链路。

## 8. 给执行者的一句话

请等待审查者的 Phase C0/C1 工作文档后再执行；执行时先只读审计 fresh top50 adaptive replay-ready 覆盖不足原因，再在审查通过后用本地离线 artifact 修复 fresh top50 覆盖并复跑 `2025-07-01..2026-05-07` full/common universe 对比；不得重新训练 qlib/LTR、不得改 Phase1C anchor、不得改 replay 费用/执行口径、不得改前端/API 或触发 provider/accepted latest/monitor/交易链路。
