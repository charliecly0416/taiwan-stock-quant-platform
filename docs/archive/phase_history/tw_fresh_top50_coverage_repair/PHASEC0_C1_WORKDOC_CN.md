# Phase C0/C1 工作文档：Fresh Top50 覆盖审计、离线修复与同窗口复核

生成日期：2026-06-15

依据文档：

```text
docs/tw_fresh_top50_coverage_repair/FRESH_TOP50_COVERAGE_REPAIR_MAINLINE_CN.md
```

前置 gate：

```text
phase_c0_c1_coverage_repair_contract_frozen
```

## 1. 总目标

本支线只回答一个问题：

```text
fresh top50 adaptive 在 2025-07-01..2026-05-07 的 replay-ready 覆盖为什么只有 min 88 / median 109 / max 150；
如果用本地离线 artifact 修复覆盖后，它在同窗口 full/common universe 下是否仍弱于 Phase1C anchor。
```

本支线不是新策略研究，不是模型训练，也不是前端改版。

## 2. 固定窗口与核心对象

固定测试窗口：

```text
2025-07-01..2026-05-07
```

必须审计的 fresh replay-ready artifact：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_replay_ready_scores.csv
```

必须对照的 old Phase1C artifact：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
```

必须对照的 S2F coverage / metrics：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_coverage_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_metrics.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_common_universe_metrics.csv
```

Phase1C anchor 已由以下文档冻结：

```text
docs/tw_phase1c_anchor_reproduction/PHASEA2_REVIEW_AND_ANCHOR_CARD_CN.md
```

C0/C1 不得修改 Phase1C anchor 的任何产物、指标或解释。

## 3. 已知覆盖问题

C0 必须以以下已知事实为起点，不得绕开：

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

C0 的核心任务是解释 `fresh top50 daily rows min 88 / median 109 / max 150` 的原因。

## 4. Phase C0：覆盖差异只读审计

### 4.1 C0 目标

C0 只做只读审计：

```text
查清 fresh replay-ready 覆盖不足来自哪里。
```

C0 不修复、不回放、不训练、不改任何现有产物。

### 4.2 C0 必查问题

必须按 `date,instrument` key 拆解以下问题。

Fresh top50 replay-ready 内部：

- 是否存在 fresh qlib score；
- 是否存在 `adaptive_score_baseline` 或等价 top50 adaptive score；
- 是否存在 price；
- 是否存在 replay 所需 required feature；
- 是否在 replay-ready 构建阶段被过滤；
- 是否受 static universe / dynamic universe policy 限制；
- 是否受 accepted symbols、selected_count、active date range 影响。

Old minus fresh：

```text
old - fresh_top50 = 7952 keys
```

必须归因这些 key 缺失原因：

- 缺 fresh qlib score；
- 缺 fresh replay-ready row；
- 缺 price；
- 缺 required feature；
- 被 fresh universe policy 过滤；
- 被 active date range 或 accepted symbols 过滤；
- 其他原因。

Fresh minus old：

```text
fresh_top50 - old = 90 keys
```

必须解释这些 key 是否来自合理 universe 差异、日期边界、symbol 集合差异或构建噪声。

### 4.3 C0 输入限制

C0 允许读取：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_replay_ready_scores.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/
本地已有 qlib score / feature / replay-ready 产物
```

C0 禁止读取后直接改写任何源 artifact。

### 4.4 C0 输出

执行者应提交：

```text
docs/tw_fresh_top50_coverage_repair/PHASEC0_COVERAGE_AUDIT_EXECUTION_REPORT_CN.md
```

建议输出目录：

```text
data_tw/experiments/fresh_top50_coverage_repair/
```

建议产物：

```text
phasec0_coverage_by_day.csv
phasec0_missing_reason_summary.csv
phasec0_old_minus_fresh_sample.csv
phasec0_fresh_minus_old_sample.csv
phasec0_source_artifact_audit.csv
phasec0_summary.json
```

### 4.5 C0 通过标准

C0 可提交审查的最低标准：

- 每日 fresh top50 coverage 与 S2F 已知 `88/109/150` 对齐；
- old/fresh key 差异数量与 S2F coverage audit 对齐；
- `old - fresh_top50` 的 7952 key 有可解释的原因分类；
- `fresh_top50 - old` 的 90 key 有解释；
- 明确覆盖不足是否能通过本地离线 artifact 修复；
- 未修改源 artifact；
- 未训练、未回放、未改前端/API；
- 未触发 provider / accepted latest / monitor / broker / orders / quick-trade。

C0 若无法解释覆盖不足，必须停止，不能进入 C1。

## 5. C0 审查 Gate

C1 只能在 C0 审查通过后执行。

推荐 C0 通过 gate：

```text
phase_c0_coverage_audit_review_passed_allow_offline_c1
```

如果 C0 发现修复必须依赖真实数据拉取、provider publish、accepted latest switching 或线上状态改变，则不得进入 C1，必须先向用户请示。

## 6. Phase C1：离线覆盖修复与只读 Replay

### 6.1 C1 进入条件

C1 只能在以下条件全部满足时执行：

- C0 审查通过；
- 覆盖不足原因已查清；
- C0 证明可通过本地离线 artifact 修复；
- 不需要 provider refresh / publish；
- 不需要 accepted latest switching；
- 不需要 monitor / broker / orders / quick-trade；
- 不需要重新训练 qlib 或 LTR。

### 6.2 C1 目标

C1 目标是生成 repaired fresh top50 adaptive replay-ready artifact，并复跑同窗口只读历史 replay。

覆盖目标：

```text
min daily rows >= 145
median daily rows >= 149
max daily rows <= 150
```

若由于合理可交易性、停牌、上市时间或真实本地价格缺失无法达到目标，必须逐项说明原因。禁止为了凑满 150 强行填充不可交易或缺价格股票。

### 6.3 C1 允许操作

C1 允许：

- 修复离线 replay-ready 构建逻辑；
- 复用本地已有 qlib score；
- 复用本地 normalized price；
- 复用本地历史 feature；
- 生成新的 repaired fresh top50 replay-ready artifact 到本支线输出目录；
- 只读复跑 `2025-07-01..2026-05-07` historical replay；
- 输出 repaired full / common universe 指标。

C1 不得改写原始 S2D/S2F/Phase1C 产物。

### 6.4 C1 禁止操作

C1 禁止：

- 重新训练 qlib；
- 重新训练 LTR；
- 改 Phase1C anchor；
- 改 fresh top50 adaptive 策略规则；
- 新增策略；
- 改 fee/tax；
- 改 next-day execution；
- 改 position_count_target；
- 改 test window；
- 改前端/API；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / orders / quick-trade；
- target position / target weight；
- 输出真实买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

### 6.5 C1 固定 Replay 口径

C1 replay 口径固定为：

```text
test window: 2025-07-01..2026-05-07
initial_cash_or_equity_assumption: 1000000.0
fee_rate: 0.001425
tax_rate: 0.003
position_count_target: 10
execution: next-day execution
price source: 本地 normalized price，且与 S2F/Phase1C anchor 口径一致
```

若任何字段不能保持一致，C1 必须停止并报告。

### 6.6 C1 必须对比

C1 必须同时报告：

```text
Phase1C anchor simple full
original fresh top50 adaptive full
repaired fresh top50 adaptive full
original fresh LTR full（如可用）
repaired fresh LTR full（仅当不需重训、不改 score，且 C0/C1 可合法生成）
```

Common universe 必须至少包含：

```text
Phase1C anchor simple
original fresh top50 adaptive
repaired fresh top50 adaptive
```

若 repaired fresh LTR 无法合法生成，必须说明，不得重训补齐。

### 6.7 C1 必做审计

C1 报告必须包含：

- repaired coverage by day；
- repaired vs original coverage delta；
- source provenance；
- full universe replay metrics；
- common universe replay metrics；
- next-day accounting audit；
- fee/tax audit；
- action audit；
- missing price / skipped trade audit；
- abnormal price / abnormal return audit；
- real PnL contribution by symbol/day；
- repaired artifact schema；
- 是否仍弱于 Phase1C anchor。

### 6.8 C1 输出

执行者应提交：

```text
docs/tw_fresh_top50_coverage_repair/PHASEC1_REPAIR_AND_REPLAY_EXECUTION_REPORT_CN.md
```

建议产物：

```text
data_tw/experiments/fresh_top50_coverage_repair/phasec1_repaired_replay_ready_scores.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_coverage_by_day.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_full_universe_metrics.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_common_universe_metrics.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_daily_nav.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_action_audit.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_next_day_accounting_audit.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_real_pnl_contribution_by_symbol.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_real_pnl_contribution_by_day.csv
data_tw/experiments/fresh_top50_coverage_repair/phasec1_summary.json
```

### 6.9 C1 通过标准

C1 可提交审查的最低标准：

- repaired fresh top50 coverage 达到或合理解释未达到 `min >=145 / median >=149 / max <=150`；
- repaired replay-ready artifact provenance 清楚；
- 同窗口 replay 口径与 Phase1C anchor / S2F 一致；
- full universe 和 common universe 指标均输出；
- next-day accounting 通过；
- 费用税费口径一致；
- 未改 Phase1C anchor；
- 未训练 qlib/LTR；
- 未改前端/API；
- 未触发 provider / accepted latest / monitor / broker / orders / quick-trade；
- 结论只回答覆盖修复后的相对表现，不直接推动默认策略切换。

## 7. Phase C2 预期审查问题

C2 审查者必须回答：

1. fresh top50 覆盖不足原因是否查清；
2. repaired fresh top50 是否接近每日 150 支；
3. repaired fresh top50 full universe 是否追上 Phase1C anchor；
4. repaired fresh top50 common universe 是否追上 Phase1C anchor；
5. Phase1C LTR simple 当前前端默认展示是否需要调整；
6. 是否可以进入正交数据主线。

C0/C1 执行者不得在报告中自行修改前端策略，只能给研究证据。

## 8. 只读安全边界

C0/C1 全程禁止真实链路：

```text
provider refresh / publish
accepted latest switching
monitor config save / scan / alerts write
broker
orders
quick-trade
target position
target weight
frontend/API 改动
```

禁止输出：

```text
真实买入/卖出指令
持有建议
仓位建议
收益承诺
胜率
上涨概率
```

允许出现：

```text
历史回放
只读复核
coverage repair
offline artifact
action_count / buy_count / sell_count 历史统计
```

其中 `buy_count` / `sell_count` 只能作为历史回放统计，不得写成行动建议。

## 9. 与 Phase1C Anchor 的关系

Phase1C anchor 是只读冻结基准：

```text
docs/tw_phase1c_anchor_reproduction/PHASEA2_REVIEW_AND_ANCHOR_CARD_CN.md
```

C0/C1 只能引用 anchor 指标作为对照，不得：

- 改 anchor score；
- 改 anchor replay；
- 改 anchor common universe；
- 重写 anchor card；
- 将 repaired fresh top50 结果反向写入 anchor 目录。

## 10. 失败处理

执行者遇到以下情况必须停止并报告：

- fresh replay-ready artifact 不存在；
- old/fresh key 差异无法解释；
- 修复需要线上数据拉取或 provider publish；
- 修复需要 accepted latest switching；
- 修复需要重新训练 qlib/LTR；
- 修复必须改变 replay 口径；
- repaired artifact 无法达到覆盖目标且原因不清；
- 发现 Phase1C anchor 本身被改动。

不得用静默改口径、补训练或前端改文案绕过失败。

## 11. 给执行者的一句话

请按本文先执行 Phase C0：只读查清 fresh top50 adaptive replay-ready 在 `2025-07-01..2026-05-07` 只有 `88/109/150` 覆盖的原因，并提交 C0 报告等待审查；C0 审查通过后，才可执行 Phase C1，用本地离线 artifact 生成 repaired fresh top50 replay-ready 并按同窗口、同费用税费、同 next-day execution 口径复跑 full/common universe 只读历史 replay；全程不得改 Phase1C anchor、不得重训 qlib/LTR、不得改前端/API 或触发 provider/accepted latest/monitor/交易链路。
