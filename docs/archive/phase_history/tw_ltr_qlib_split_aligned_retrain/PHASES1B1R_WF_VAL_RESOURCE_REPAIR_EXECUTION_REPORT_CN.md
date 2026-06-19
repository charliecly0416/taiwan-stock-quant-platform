# Phase S1B1R WF-VAL 资源修复执行报告

生成日期：2026-06-14

## 1. 执行结论

本轮严格按 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1_REVIEW_AND_PHASES1B1R_REPAIR_WORK_CN.md` 执行，只尝试修复 `WF-VAL` qlib score/rank 生成失败问题。

结论：`仍未通过，资源阻断`。

推荐 gate：

```text
s1b1r_wf_val_resource_blocked
```

阻断原因：S1B1R 已按审查文档允许的资源层窄修复实现“训练一次 + score window 月度分块预测”，但进程仍在 `WF-VAL` 模型训练阶段被系统 `Killed`，exit code `137`。由于失败发生在训练阶段，尚未进入月度分块预测阶段。

本轮未缩短 `WF-VAL` validation window，未改 provider，未改参数，未改 handler / feature / label，也未改 universe 口径。

## 2. 范围边界

本轮执行内容：

- 复用已完成 folds：`WF-2017`、`WF-2018`、`WF-2019`、`WF-2020`、`TEST`；
- 单独尝试生成缺失的 `WF-VAL`；
- 保持 full provider、Alpha158、LGBModel 与冻结 qlib 配置；
- 对 `WF-VAL` 实施资源层修复：训练数据只加载到 `2020-12-31`，训练完成后再按月预测 `2021-01-01..2022-12-31`；
- 更新 S1B1R gate 与 leakage / boundary audit。

本轮未执行：

- 未训练 LTR；
- 未构建 LTR 样本；
- 未跑组合回放；
- 未做策略比较；
- 未调 qlib/LTR 参数；
- 未更换 model family、handler、feature、label；
- 未缩短 `WF-VAL` score window；
- 未静默降级 provider / universe；
- 未使用 TEST 结果反向改设计；
- 未改前端/API；
- 未联网；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未触发 monitor config save / scan / alerts write；
- 未接 broker、orders、quick-trade 或交易链路；
- 未输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 3. 修复实现

修改脚本：

```text
scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
```

新增资源修复逻辑：

```text
train_wf_val_model()
predict_wf_val_chunks()
train_predict_wf_val_resource_repair()
```

修复策略：

```text
WF-VAL train window: 2015-05-04..2020-12-31
WF-VAL score window: 2021-01-01..2022-12-31
train once, then predict monthly chunks
```

保持不变：

```text
provider: /home/chuliyang/qlib/data_tw/experiments/yahoo_adjusted_primary/qlib_bin
config: qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml
model: qlib.contrib.model.gbdt.LGBModel
handler: qlib.contrib.data.handler.Alpha158
calendar: qlib day.txt ∩ TWII normalized price calendar
universe: dynamic up to 150, selected_count >= 145
```

说明：非 TEST folds 的 qlib internal `valid` segment 仍与 train segment 相同。这只是为了满足 `LGBModel.fit(dataset)` 需要 valid segment 的运行结构；本报告不把该 internal valid segment 表述为 S1 正式 validation split。S1 正式 validation split 仍只能是 `WF-VAL` 的 `2021-01-01..2022-12-31` score/rank。

## 4. 执行结果

执行命令：

```text
python scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
```

执行过程：

1. 成功复用既有 fold 产物：

```text
WF-2017
WF-2018
WF-2019
WF-2020
```

2. 进入 `WF-VAL`：

```text
[S1B1] generating fold: WF-VAL
```

3. `WF-VAL` 训练数据构造完成：

```text
Loading data Done
DropnaLabel Done
CSZScoreNorm Done
fit & process data Done
Init data Done
```

4. 在模型训练阶段被系统终止：

```text
Killed
exit code: 137
```

判断：S1B1R 资源修复已减少 score window 预测侧峰值内存，但当前环境仍无法完成 full-provider `WF-VAL` 模型训练本身。根据审查文档 7.7，执行者必须停止并给出 `s1b1r_wf_val_resource_blocked`。

## 5. 当前产物状态

仍已完成：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-2017.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-2018.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-2019.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-2020.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.csv
```

仍缺失：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-VAL.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-VAL.manifest.json
```

当前 `phase_s1b1_qlib_wf_scores.csv` 仍只是部分产物，不得作为完整 S1B1 通过产物使用，因为缺少 validation split。

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
s1b1r_wf_val_resource_blocked
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
python scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
```

结果：语法检查通过；运行在 `WF-VAL` 训练阶段 exit code `137`。

## 9. 待审查者 / 用户决策事项

当前执行者不能在不改变方法口径的前提下继续完成 `WF-VAL`。建议审查者 / 用户决定下一步之一：

1. 换更大内存环境运行同一脚本；
2. 明确授权是否允许降低 LightGBM `num_threads` 作为资源控制，并确认这是否不改变模型参数语义；
3. 明确授权其他只读资源控制方案。

执行者本轮已按文档停止，等待审查意见。
