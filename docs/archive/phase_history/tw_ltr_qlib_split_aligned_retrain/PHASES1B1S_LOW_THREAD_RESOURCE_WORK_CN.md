# Phase S1B1S 低线程资源修复工作文档

生成日期：2026-06-14

## 1. 用户确认

用户已确认选择低线程资源修复路线：

```text
减少并行线程以降低峰值内存，不减少数据；运行时间变长可以接受。
```

本轮目标是尝试完成 `WF-VAL` qlib score/rank，不改变 S1 split-aligned 公平验证口径。

## 2. 允许执行的内容

执行者只允许对 `WF-VAL` 做低线程资源控制阶梯：

```text
LightGBM num_threads: 8 -> 4 -> 2 -> 1
```

该改动只作为资源控制，不作为参数搜索或模型优化。执行者必须按顺序尝试：

1. 先尝试 `num_threads=4`；
2. 如果仍因资源被系统 kill，再尝试 `num_threads=2`；
3. 如果仍失败，最后尝试 `num_threads=1`；
4. 一旦某个线程数成功生成完整 `WF-VAL`，必须停止，不得继续尝试更低线程或比较结果。

必须保持不变：

```text
WF-VAL train window: 2015-05-04..2020-12-31
WF-VAL score window: 2021-01-01..2022-12-31
provider: /home/chuliyang/qlib/data_tw/experiments/yahoo_adjusted_primary/qlib_bin
config source: qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml
handler: Alpha158
model: LGBModel
calendar: qlib day.txt ∩ TWII normalized price calendar
universe: dynamic up to 150, selected_count >= 145
feature / label / fold / ranking policy: unchanged
```

执行者应复用已完成 folds：

```text
WF-2017
WF-2018
WF-2019
WF-2020
TEST
```

不得重跑这些 folds，除非 manifest 或文件完整性明确异常。

## 3. 实现要求

执行者可以在脚本中为 `WF-VAL` 增加低线程 override，例如：

```text
if fold.fold_id == "WF-VAL":
    model_kwargs["num_threads"] = resource_control_num_threads
```

要求：

- 不修改原始冻结配置文件的研究含义；
- 必须在 `WF-VAL.manifest.json` 中记录：
  - `original_num_threads: 8`
  - `resource_control_attempt_order: [4, 2, 1]`
  - `resource_control_success_num_threads: <第一个成功线程数>`
  - `resource_control_failed_num_threads: <成功前失败过的线程数列表>`
  - `resource_control_reason: reduce_parallel_memory_pressure`
- 必须在执行报告中明确说明这是用户确认的资源控制，不是参数搜索；
- 不允许尝试未授权的线程数；
- 不允许在多个成功结果之间选择收益、score 分布或任何效果指标更好的结果；
- 如果 `num_threads=1` 仍然 exit code `137`，必须停止并报告资源阻断，不得继续改数据口径。

## 4. 必须输出

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1S_LOW_THREAD_RESOURCE_EXECUTION_REPORT_CN.md
```

若成功，必须生成或更新：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-VAL.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-VAL.manifest.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_fold_training_manifest.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_qlib_wf_scores.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_score_rank_coverage_by_split.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_score_rank_coverage_by_fold.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_score_rank_coverage_by_date.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_leakage_boundary_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_gate_summary.json
```

## 5. 验收标准

成功 gate：

```text
s1b1s_low_thread_wf_val_pass_request_s1b2_ltr_sample_build
```

通过条件：

- `WF-VAL.csv` 存在；
- validation coverage 覆盖 `2021-01-01..2022-12-31` 内 qlib scoring calendar 交易日；
- validation selected count min `>=145`；
- validation score missing count 为 `0`；
- validation rank missing count 为 `0`；
- duplicate date/instrument count 为 `0`；
- train scored coverage 仍为 `2017-01-01..2020-12-31`；
- test coverage 仍为 `2023-01-01..2025-06-30`；
- `resource_control_attempt_order` 记录为 `[4, 2, 1]`；
- `resource_control_success_num_threads` 记录为第一个成功线程数；
- `s1_test_feedback_used_for_train_or_fold_design=false`；
- `parameter_search_performed=false`；
- `ltr_training_performed=false`；
- `ltr_sample_build_performed=false`；
- `portfolio_replay_performed=false`。

失败 gate：

```text
s1b1s_low_thread_resource_blocked
s1b1s_blocked_by_leakage_or_scope_violation
```

如果 `4 -> 2 -> 1` 全部仍被系统 kill，执行者必须停止，下一步再讨论是否迁移到更大内存 CPU 服务器；不得自行减少数据、缩短窗口、减少股票、换 provider、换 feature 或启用 GPU。

## 6. 禁止事项

- 不训练 LTR；
- 不构建 LTR 样本；
- 不跑组合回放；
- 不做策略比较；
- 不做 qlib/LTR 参数搜索；
- 不减少数据；
- 不缩短 train / validation window；
- 不减少 universe；
- 不更换 feature / label / handler / model family；
- 不改前端/API；
- 不联网；
- 不触发 provider refresh / publish；
- 不切换 accepted latest；
- 不触发 monitor config save / scan / alerts write；
- 不接 broker、orders、quick-trade；
- 不输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。
