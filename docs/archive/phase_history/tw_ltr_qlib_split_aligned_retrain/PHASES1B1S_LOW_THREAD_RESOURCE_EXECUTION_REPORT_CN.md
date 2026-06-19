# Phase S1B1S 低线程资源修复执行报告

生成日期：2026-06-14

## 1. 执行结论

本轮按 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1S_LOW_THREAD_RESOURCE_WORK_CN.md` 执行，只对 `WF-VAL` 做用户确认的低线程资源控制阶梯：

```text
LightGBM num_threads: 4 -> 2 -> 1
```

结论：`仍未通过，资源阻断`。

推荐 gate：

```text
s1b1s_low_thread_resource_blocked
```

三档线程全部在 `WF-VAL` 阶段被系统终止，exit code `137`。本轮未减少数据、未缩短窗口、未减少 universe、未更换 provider、未更换 feature / label / handler / model family。

## 2. 范围边界

本轮执行内容：

- 复用已完成 folds：`WF-2017`、`WF-2018`、`WF-2019`、`WF-2020`、`TEST`；
- 仅对 `WF-VAL` 尝试低线程资源控制；
- 保持 `WF-VAL` train window 为 `2015-05-04..2020-12-31`；
- 保持 `WF-VAL` score window 为 `2021-01-01..2022-12-31`；
- 保持 full provider、Alpha158、LGBModel、冻结 qlib config；
- 保留上一轮资源修复的月度分块预测逻辑，但本轮失败发生在进入预测前。

本轮未执行：

- 未训练 LTR；
- 未构建 LTR 样本；
- 未跑组合回放；
- 未做策略比较；
- 未做 qlib/LTR 参数搜索；
- 未减少数据；
- 未缩短 train / validation window；
- 未减少 universe；
- 未更换 feature / label / handler / model family；
- 未改前端/API；
- 未联网；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未触发 monitor config save / scan / alerts write；
- 未接 broker、orders、quick-trade 或交易链路；
- 未输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 3. 实现说明

修改脚本：

```text
scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
```

实现方式：

```text
S1B1_WF_VAL_NUM_THREADS=4 python scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
S1B1_WF_VAL_NUM_THREADS=2 python scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
S1B1_WF_VAL_NUM_THREADS=1 python scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
```

脚本只允许 `WF-VAL` 使用以下线程 override：

```text
[4, 2, 1]
```

若设置其它线程数，脚本会报错。该 override 只作为资源控制；未修改原始冻结配置文件 `qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml`。

保持不变：

```text
provider: /home/chuliyang/qlib/data_tw/experiments/yahoo_adjusted_primary/qlib_bin
config source: qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml
handler: Alpha158
model: LGBModel
calendar: qlib day.txt ∩ TWII normalized price calendar
universe: dynamic up to 150, selected_count >= 145
feature / label / fold / ranking policy: unchanged
```

## 4. 执行过程

### 4.1 num_threads=4

结果：失败。

关键日志：

```text
[S1B1] generating fold: WF-VAL
Loading data Done
DropnaLabel Done
CSZScoreNorm Done
fit & process data Done
Init data Done
Killed
exit code: 137
```

### 4.2 num_threads=2

结果：失败。

关键日志：

```text
[S1B1] generating fold: WF-VAL
Loading data Done
DropnaLabel Done
CSZScoreNorm Done
fit & process data Done
Init data Done
Killed
exit code: 137
```

### 4.3 num_threads=1

结果：失败。

关键日志：

```text
[S1B1] generating fold: WF-VAL
Loading data Done
DropnaLabel Done
CSZScoreNorm Done
fit & process data Done
Init data Done
Killed
exit code: 137
```

判断：三档低线程都没有生成 `WF-VAL.csv`。失败点仍在 `WF-VAL` 训练资源峰值附近，未进入完整 `WF-VAL` score/rank 产物阶段。

## 5. 当前产物状态

仍已完成：

```text
folds/WF-2017.csv
folds/WF-2018.csv
folds/WF-2019.csv
folds/WF-2020.csv
folds/TEST.csv
```

仍缺失：

```text
folds/WF-VAL.csv
folds/WF-VAL.manifest.json
```

当前 `phase_s1b1_qlib_wf_scores.csv` 仍只是部分产物，不得作为完整 S1B1 通过产物使用。

## 6. 已完成 folds 质量摘要

已完成 folds：

| fold | start_date | end_date | date_count | score_rows | selected_count_min | selected_count_median | selected_count_max | frozen pred |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| WF-2017 | 2017-01-03 | 2017-12-29 | 243 | 36379 | 147 | 150.0 | 150 | False |
| WF-2018 | 2018-01-02 | 2018-12-28 | 245 | 36664 | 149 | 150.0 | 150 | False |
| WF-2019 | 2019-01-02 | 2019-12-31 | 241 | 36128 | 149 | 150.0 | 150 | False |
| WF-2020 | 2020-01-02 | 2020-12-31 | 245 | 36750 | 150 | 150.0 | 150 | False |
| TEST | 2023-01-03 | 2025-06-30 | 597 | 89386 | 148 | 150.0 | 150 | True |

已完成 folds 检查：

```text
score_rows_completed_folds: 235307
date_count_completed_folds: 1571
instrument_count_completed_folds: 606
score_missing_count_on_completed_folds: 0
rank_missing_count_on_completed_folds: 0
duplicate_date_instrument_count_on_completed_folds: 0
```

缺失 coverage：

```text
validation: 2021-01-01..2022-12-31
missing fold: WF-VAL
```

## 7. Gate 与审计文件

已更新：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_gate_summary.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_leakage_boundary_audit.json
```

Gate：

```text
s1b1s_low_thread_resource_blocked
```

资源控制记录：

```text
original_num_threads: 8
resource_control_attempt_order: [4, 2, 1]
resource_control_success_num_threads: null
resource_control_failed_num_threads: [4, 2, 1]
resource_control_reason: reduce_parallel_memory_pressure
```

Leakage / boundary：

```text
s1_test_feedback_used_for_train_or_fold_design: false
parameter_search_performed: false
ltr_training_performed: false
ltr_sample_build_performed: false
portfolio_replay_performed: false
provider_refresh_publish_performed: false
accepted_latest_switching_performed: false
monitor_or_trading_chain_touched: false
early_train_2015_2016_scored: false
```

## 8. 验证命令

已执行：

```text
python -m py_compile scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
S1B1_WF_VAL_NUM_THREADS=4 python scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
S1B1_WF_VAL_NUM_THREADS=2 python scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
S1B1_WF_VAL_NUM_THREADS=1 python scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
```

语法检查通过；三个低线程尝试均 exit code `137`。

## 9. 待审查者 / 用户决策事项

当前执行者已完成用户授权的低线程资源控制阶梯，但仍无法在当前环境完成 `WF-VAL`。根据工作文档，执行者已停止。

后续需要审查者 / 用户决定是否迁移到更大内存 CPU 服务器，或另行授权明确的新资源方案。执行者本轮不再自行减少数据、缩短窗口、减少股票、换 provider、换 feature 或启用 GPU。
