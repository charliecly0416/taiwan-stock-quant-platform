# Extended OOS 四模型四回放整理总文档

生成日期：2026-06-16

## 1. 整理目的

本文件用于把 `tw_extended_oos_qlib_orthogonal_ltr` 分支从阶段性探索状态整理成可继续研究的清晰基线。

当前结论只围绕四个模型与四个回放规则展开。其他阶段性报告、修复报告、异常审计产物保留为证据，但后续默认策略讨论不得再随意引用未冻结口径。

本文件不删除任何数据；删除实验产物会破坏可追溯性。整理方式是：

1. 冻结四个模型；
2. 冻结四个回放规则；
3. 标注哪些结果是合同正确结果，哪些是 bug anomaly；
4. 标注核心 artifact、审计 artifact、历史/临时 artifact；
5. 给出当前可参考结论与后续研究入口。

## 2. 四个模型

后续本分支只讨论以下四个模型。

| ID | 名称 | qlib 底座 | LTR 训练窗口 | score column | 角色 |
| --- | --- | --- | --- | --- | --- |
| M1 | fresh qlib adaptive | fresh qlib, 约 2017-2024 训练 | 无 LTR | `adaptive_score_baseline` | 当前强基线 |
| M2 | fresh qlib + 2025 orthogonal LTR | fresh qlib, 约 2017-2024 训练 | 2025 | `phasee6_branch_a_fresh_ltr_score` | 桥接：fresh 底座上验证 2025 LTR |
| M3 | frozen qlib + 2025 orthogonal LTR | 2018-2022 frozen qlib | 2025 | `phasee6_branch_b_frozen_ltr_score` | 桥接：同 frozen 底座验证短 LTR |
| M4 | E4 frozen qlib + 2023-2025 orthogonal LTR | 2018-2022 frozen qlib | 2023-2025 | `phasee3_extended_oos_ltr_score` | 集大成 treatment |

### 2.1 M1 Fresh Qlib Adaptive

核心输入：

```text
data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv
```

说明：

- 使用 repaired fresh qlib artifact。
- 2026 回放窗口内每天 top50 覆盖完整。
- 不含 LTR。
- 是比较 qlib 本身与 LTR rerank 增益的关键控制组。

### 2.2 M2 Fresh Qlib + 2025 LTR

核心输入：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_replay_ready_scores_2026.csv
method_group = branch_a_treatment
score_col = phasee6_branch_a_fresh_ltr_score
```

训练样本：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_branch_a_fresh_train_sample_2025.csv
```

训练窗口与覆盖：

- LTR 训练：`2025-01-02..2025-12-31`
- train rows：`36084`
- daily rows min/median/max：`148 / 149 / 150`
- 非 top50 行：`24081`
- 不是 top50-only 训练。

注意：

- E6 manifest 记录 `fresh_2025h1_validation_caveat`：fresh qlib 底座若用过 2025H1 validation，则 M2 不是严格的 qlib-never-seen-2025 LTR train 实验。
- 因此 M2 主要用于桥接比较，不宜单独作为最终默认候选。

### 2.3 M3 Frozen Qlib + 2025 LTR

核心输入：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_replay_ready_scores_2026.csv
method_group = branch_b_control_treatment
score_col = phasee6_branch_b_frozen_ltr_score
```

训练样本：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_branch_b_frozen_train_sample_2025.csv
```

训练窗口与覆盖：

- qlib 底座训练：`2018-2022`
- LTR 训练：`2025-01-02..2025-12-31`
- train rows：`36053`
- daily rows min/median/max：`148 / 149 / 149`
- 非 top50 行：`23953`
- 不是 top50-only 训练。

M3 的用途：

- 与 M4 比较，用来判断 LTR 训练窗口从 2025 扩展到 2023-2025 是否带来提升。

### 2.4 M4 E4 Frozen Qlib + 2023-2025 LTR

核心输入：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_ready_scores_2026.csv
score_col = phasee3_extended_oos_ltr_score
```

训练样本：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_train_sample_2023_2025.csv
```

训练窗口与覆盖：

- qlib 底座训练：`2018-2022`
- LTR 训练：`2023-01-01..2025-12-31`
- train rows：`107408`
- daily group size min/median/max：`147 / 149 / 149`
- 非 top50 行：`71258`
- 不是 top50-only 训练。

模型配置：

```text
LightGBM.LGBMRanker
objective = lambdarank
metric = ndcg
num_leaves = 31
learning_rate = 0.03
n_estimators = 120
min_child_samples = 40
random_state = 42
feature_count = 78
label_col = relevance_10d_top_heavy
```

M4 是当前最重要的 LTR treatment。它在多个正确回放规则下均强于 M3，说明更长 LTR 训练窗口是主要增益来源之一。

## 3. 数据与样本合同

### 3.1 训练样本

LTR 训练必须遵守：

- 使用 qlib 底座产生的 daily candidate universe；
- 训练样本不是 top50-only；
- 每天接近 top150，避免早期错误地只拿 top50 训练；
- feature schema 固定为 78 个 O4/O2 正交特征与控制特征；
- label 固定为 `relevance_10d_top_heavy`；
- 不得把 2026 test label 用于训练或调参。

### 3.2 2026 回放样本

统一回放窗口：

```text
2026-01-01..2026-05-07
```

回放输入必须压到 qlib top50：

```text
candidate_k = 50
daily top50 rows = 50
date_count = 79
row_count = 3950
```

已有审计显示：

- M1/M2/M3/M4 在最终回放比较中均可形成每天 50 支的 replay-ready 输入；
- score 缺失为 0；
- duplicate key 为 0；
- next-day accounting 未发现缺价；
- forbidden future label/return 不进入 replay decision。

## 4. 四个回放规则

后续只讨论以下四个规则。

### 4.1 R1 Original

来源：

```text
scripts/evaluate_tw_ltr_s2d_full_daily_replay.py::replay
```

规则：

```text
candidate_k = 50
target_position_count = 10
sell: 当前持仓不在当日 score 排序 top10 target set 内则卖出，可一天卖多支
buy: 每个 signal day 最多买入 1 支 top10 内未持有股票
execution: next trading day
```

说明：

- 这是 E4、E5B、E6 原始公平比较使用的规则。
- 它不是“每天最多替换一支”。
- 它偏向较快 top10 rotation。

### 4.2 R2 Top50-Exit

规则：

```text
candidate_k = 50
target_position_count = 10
sell: 只有持仓跌出 qlib top50 / candidate set 才卖出；若多支同时跌出，则全卖出
buy: 每个 signal day 最多买入 1 支，买 score 排序最高且未持有股票
execution: next trading day
```

说明：

- 这是慢卖、长持规则。
- 对 pure fresh qlib adaptive 特别有利。
- 但 LTR 在该规则下不一定增强 qlib，因为收益主要由初期买入优先级与长期持有决定。

### 4.3 R3 One-Sell-One-Buy Correct

规则：

```text
sell_pool = 当前持仓中不在当日 score top10 target set 的股票
sell_priority:
  1. 已不在 candidate top50 的股票优先卖；
  2. 若仍在 candidate top50，卖 score 排名最差者；
  3. 若并列，用 instrument 升序稳定排序。
sell_limit = 每个 signal day 最多 1 支
buy: 每个 signal day 最多买入 1 支 score 排序最高且未持有股票
execution: next trading day
```

说明：

- 这是符合“每天最多替换一支”直觉的正确低换手规则。
- E8S 已修复 E8R 的排序错误。
- 该规则是当前最适合进入默认候选讨论的 LTR 规则之一。

### 4.4 R4 One-Sell-One-Buy Buggy E8R

规则：

```text
sell_pool = 当前持仓中不在当日 score top10 target set 的股票
buggy sell priority:
  1. 已不在 candidate top50 的股票优先卖；
  2. 若仍在 candidate top50，错误地卖 score 排名较好的股票。
buy: 每个 signal day 最多买入 1 支
```

说明：

- 这是 E8R 的实现错误，不是合法策略合同。
- 它必须保留在整理结果中，因为它揭示了 E4 在 2026 窗口中存在 rank bucket 异常：rank 11-30 事后收益略强于 rank 1-10。
- R4 只能作为 anomaly diagnostic，不得作为默认策略收益证据。

## 5. 当前结果矩阵

统一窗口：

```text
2026-01-01..2026-05-07
```

收益为 fee/tax adjusted net return。

| 模型 | R1 Original | R2 Top50-Exit | R3 One-Sell-One-Buy Correct | R4 Buggy E8R |
| --- | ---: | ---: | ---: | ---: |
| M1 fresh qlib adaptive | `28.94%` | `96.10%` | `46.91%` | `48.54%` |
| M2 fresh qlib + 2025 LTR | `46.47%` | `48.83%` | `58.38%` | `52.80%` |
| M3 frozen qlib + 2025 LTR | `31.86%` | `33.77%` | `49.83%` | `47.84%` |
| M4 E4 frozen qlib + 2023-2025 LTR | `60.25%` | `63.07%` | `87.80%` | `96.18%` |

最大回撤：

| 模型 | R1 Original | R2 Top50-Exit | R3 One-Sell-One-Buy Correct | R4 Buggy E8R |
| --- | ---: | ---: | ---: | ---: |
| M1 fresh qlib adaptive | `-3.76%` | `-6.97%` | `-7.14%` | `-7.74%` |
| M2 fresh qlib + 2025 LTR | `-5.82%` | `-7.40%` | `-9.93%` | `-9.93%` |
| M3 frozen qlib + 2025 LTR | `-8.36%` | `-8.38%` | `-11.93%` | `-12.16%` |
| M4 E4 frozen qlib + 2023-2025 LTR | `-7.15%` | `-9.66%` | `-10.79%` | `-9.32%` |

M3 的 R2/R3/R4 为本轮只读补充回放结果，尚未写入 E8S artifact；若后续要纳入正式报告，应补一个 E8T 或 Consolidated replay artifact。

## 6. 控制变量分析

### 6.1 LTR 是否有效

在 R1 Original 下：

- M1 fresh qlib：`28.94%`
- M2 fresh + 2025 LTR：`46.47%`
- M3 frozen + 2025 LTR：`31.86%`
- M4 frozen + 2023-2025 LTR：`60.25%`

结论：

- LTR 在原始较快 top10 rotation 规则下有效。
- M4 明显强于 M3，说明 LTR 训练窗口从 2025 扩展到 2023-2025 带来重要增益。

在 R3 One-Sell-One-Buy Correct 下：

- M1 fresh qlib：`46.91%`
- M2 fresh + 2025 LTR：`58.38%`
- M3 frozen + 2025 LTR：`49.83%`
- M4 frozen + 2023-2025 LTR：`87.80%`

结论：

- 在正确低换手规则下，LTR 仍有增益。
- M4 仍是最强合法 LTR treatment。
- R3 比 R1 更符合“每日最多替换一支”的生产直觉，但回撤也更高。

在 R2 Top50-Exit 下：

- M1 fresh qlib：`96.10%`
- M2 fresh + 2025 LTR：`48.83%`
- M4 E4：`63.07%`

结论：

- Top50-Exit 对 pure fresh qlib 极度有利。
- 这说明该规则的收益主要来自“买入后长期持有 qlib top50 内强势股”，而不是频繁 top10 rerank。
- LTR 在 R2 下可能改变买入顺序，错过或延后 qlib 长持强势股，因此不一定增强。

### 6.2 Qlib 底座影响

对比 M2 与 M3：

- 两者 LTR 训练窗口都是 2025；
- M2 使用 fresh qlib 底座；
- M3 使用 2018-2022 frozen qlib 底座。

结果：

- R1：M2 `46.47%` > M3 `31.86%`
- R3：M2 `58.38%` > M3 `49.83%`

结论：

- 同样 2025 LTR 下，fresh qlib 底座更强。
- 但 M4 虽使用 frozen qlib 底座，因 LTR 训练窗口更长，最终仍显著超过 M2/M3。

### 6.3 LTR 训练窗口影响

对比 M3 与 M4：

- 两者 qlib 底座都是 2018-2022 frozen qlib；
- M3 LTR 训练 2025；
- M4 LTR 训练 2023-2025。

结果：

- R1：M3 `31.86%` -> M4 `60.25%`
- R2：M3 `33.77%` -> M4 `63.07%`
- R3：M3 `49.83%` -> M4 `87.80%`

结论：

- 更长的 LTR 训练窗口是 M4 强表现的核心解释之一。
- 这支持“正交 LTR 需要足够长训练数据才能稳定发挥”的假设。

### 6.4 回放规则影响

同一模型换不同规则，结果差异很大：

- M1 在 R2 达到 `96.10%`，但 R1 只有 `28.94%`；
- M4 在 R3 达到 `87.80%`，R1 为 `60.25%`；
- R4 虽然 M4 到 `96.18%`，但它是 bug anomaly。

结论：

- 后续不能只说“某模型更好”，必须同时冻结 replay rule。
- 模型 score 与交易规则是共同定义策略的两个变量。

## 7. Buggy R4 异常解释

R4 的错误在于：

```text
应卖出排名最差者，却错误卖出排名较好者。
```

E8S 归因显示：

- M4 R4 收益：`96.18%`
- M4 R3 收益：`87.80%`
- largest single divergence contribution：`84939.71`
- top1/top3/top5/top10 positive pnl share：`14.25% / 38.45% / 53.54% / 76.81%`

Rank bucket 事后诊断：

| bucket | mean forward return to end |
| --- | ---: |
| rank 1-10 | `43.17%` |
| rank 11-20 | `44.97%` |
| rank 21-30 | `45.18%` |
| rank 31-50 | `39.93%` |

解释：

- 2026 这个短窗口里，M4 的 top10 并没有明显优于 rank 11-30；
- 错误规则降低了对 top10 的依赖，误打误撞保留了一些 rank 11-30 的强势股；
- 但收益高度集中，不能作为稳健策略证据；
- R4 只作为 future hypothesis：也许需要研究“top10 过度集中”或“中位 rank 保留”规则，但必须另开支线，不得混入当前默认策略。

## 8. 项目现况整理

### 8.1 核心保留 artifact

必须保留：

```text
data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/
```

核心脚本：

```text
scripts/evaluate_tw_ltr_s2d_full_daily_replay.py
scripts/train_extended_oos_qlib_orthogonal_ltr_phase_e1.py
scripts/build_extended_oos_qlib_orthogonal_ltr_phase_e2_sample.py
scripts/train_extended_oos_qlib_orthogonal_ltr_phase_e3.py
scripts/evaluate_extended_oos_qlib_orthogonal_ltr_phase_e4_replay.py
scripts/run_extended_oos_qlib_orthogonal_ltr_phase_e6_bridge.py
scripts/audit_extended_oos_qlib_orthogonal_ltr_phase_e8s_one_sell_one_buy_repair.py
```

### 8.2 审计保留 artifact

这些不再作为核心策略结果，但必须保留为审计证据：

```text
phase_e5_e4_fairness_audit/
phase_e5b_e4_vs_fresh_exact_2026_bridge/
phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/
daily_e4_default_candidate/
```

说明：

- E5/E5B 用于证明 E4 与 fresh qlib 的同窗口桥接；
- E8R 用于追踪错误 one-sell-one-buy 规则来源；
- daily E4 candidate 用于只读日更候选生成验证，但不是默认策略切换证据。

### 8.3 历史/临时口径

以下内容以后不应作为默认策略证据直接引用：

- E8R 的 `one_sell_one_buy` 汇总；
- 任何未标注 rule 的 `top10` 候选收益；
- 任何只针对单一模型、未同窗口同规则比较的结果；
- R4 buggy 收益。

### 8.4 数据是否整齐、完整、干净

当前 extended OOS 分支数据具备可追溯性，但目录偏重：

- 每个 phase 基本都有 manifest、coverage、forbidden audit；
- E1/E2/E3/E4/E6/E8S 形成完整链路；
- E8R 是错误规则审计层，保留但不再引用其 one-sell-one-buy 结论；
- M3 在四规则矩阵中的 R2/R3/R4 是本轮手动补充回放，尚未落成正式 artifact。

建议下一步不要删除历史文件，而是新增一个 consolidated artifact 目录，把四模型四规则的最终矩阵固化为正式产物：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/consolidated_four_model_four_replay/
```

建议输出：

```text
consolidated_manifest.json
four_model_four_replay_summary.csv
four_model_four_replay_coverage_audit.csv
four_model_four_replay_rule_contract.json
core_artifact_index.csv
deprecated_result_index.csv
```

这样后续研究只引用 consolidated 目录，不再从阶段性探索文件里手动拼结果。

## 9. 当前可参考结论

1. M4 E4 frozen qlib + 2023-2025 LTR 是当前最强的合法 LTR treatment。
2. R3 One-Sell-One-Buy Correct 下，M4 收益 `87.80%`，且规则符合“每日最多替换一支”的生产直觉。
3. M1 fresh qlib adaptive 在 R2 Top50-Exit 下收益 `96.10%`，但这是 qlib 长持型策略，必须进一步滚动窗口验证后才可考虑默认。
4. LTR 增益没有被推翻：
   - R1：M2 > M1，M4 > M3；
   - R3：M2 > M1，M4 > M3；
   - M4 显著强于 M3，说明更长 LTR 训练窗口有效。
5. R2 下 LTR 弱于 pure qlib，不代表 LTR 无效，而是说明 top50-exit 的收益机制更偏向 qlib 长持，不适合直接套 LTR top rerank。
6. R4 buggy 只用于异常分析，不得进入默认策略候选。

## 10. 后续研究建议

建议按以下顺序推进：

1. 先生成 consolidated four-model four-replay artifact，把本文件表格固化为可复现产物；
2. 对 M1-R2、M4-R3、M4-R1 做 rolling/OOS 稳健性验证；
3. 若 M4-R3 稳健，再设计只读日更链路；
4. 若 M1-R2 稳健，重新讨论默认策略是否应从 LTR treatment 转向 qlib top50-exit；
5. 另开支线研究 rank bucket 与中位 rank 保留规则，但不得复用 R4 buggy 作为策略。

## 11. 一句话总结

当前项目已经从“乱跑很多支线”收敛为：

```text
四个模型 x 四个回放规则
```

其中真正可进入策略讨论的是：

```text
M1-R2 fresh qlib adaptive top50-exit
M4-R1 E4 original
M4-R3 E4 one-sell-one-buy correct
```

当前最符合 LTR 主线与生产直觉的是：

```text
M4-R3: E4 frozen qlib + 2023-2025 orthogonal LTR
       one-sell-one-buy correct
       2026-01-01..2026-05-07 return = 87.80%
```

但是否成为默认策略，还需要 consolidated artifact 与 rolling/OOS 稳健性验证。

