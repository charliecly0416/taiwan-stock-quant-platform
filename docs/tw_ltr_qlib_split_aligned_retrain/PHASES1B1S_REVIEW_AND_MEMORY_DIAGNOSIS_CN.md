# Phase S1B1S 审查意见与内存诊断文档

生成日期：2026-06-14

## 1. 审查范围

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
```

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1S_LOW_THREAD_RESOURCE_EXECUTION_REPORT_CN.md
```

本轮只审查 `WF-VAL` 低线程资源修复，不推进 LTR 样本构建、训练或回放。

## 2. 审查结论

结论：`未通过，资源阻断成立。`

Gate：

```text
s1b1s_low_thread_resource_blocked
```

执行者按用户确认的线程阶梯执行：

```text
num_threads: 4 -> 2 -> 1
```

三档全部在 `WF-VAL` 阶段被系统终止，exit code `137`。未发现减少数据、缩短窗口、换 provider、换 feature/label/handler/model family、训练 LTR、构建样本、回放或交易链路越界。

## 3. 为什么一个线程也会失败

`num_threads` 主要减少 LightGBM 的并行计算开销，不会显著减少以下基础内存：

- qlib `Alpha158` handler 构造出来的特征矩阵；
- label、processor 中间结果；
- `DatasetH` train / valid segment 数据；
- LightGBM Dataset / histogram / binning 结构；
- pandas / numpy 临时对象；
- qlib handler/cache 运行期对象。

本轮失败日志显示：

```text
Loading data Done
DropnaLabel Done
CSZScoreNorm Done
fit & process data Done
Init data Done
Killed
exit code: 137
```

也就是说，数据构造已经接近完成，失败发生在模型训练内存峰值附近。此时即使只有一个线程，训练矩阵和 LightGBM 基础结构仍然必须同时存在，所以仍会 OOM。

## 4. 到底需要多少内存

当前报告没有记录进程级 peak RSS，因此不能精确断言“需要 X GB”。

但本机补充证据显示：

```text
/proc/meminfo MemTotal: 16375780 kB 约 15.6 GiB
/proc/meminfo SwapTotal: 4194300 kB 约 4.0 GiB
/proc/meminfo SwapFree: 292 kB，几乎耗尽
current cgroup memory.peak: 12277768192 bytes，约 11.44 GiB
current cgroup memory.events oom_kill: 7
```

审查判断：

```text
当前任务至少已经冲到约 11.4 GiB session memory peak，
且系统发生过 7 次 OOM kill。
真实需求高于当前成功可用内存，不能只按 11.4 GiB 配机器。
```

推荐迁移配置：

- 最低建议：`32GB RAM`；
- 更稳妥：`48GB-64GB RAM`；
- swap 不应接近耗尽；
- 优先 CPU 大内存环境，不优先 CUDA。

原因：当前不是 GPU 算力瓶颈，而是 qlib/Alpha158/LGBModel 在 full-provider `WF-VAL` 训练时的内存峰值瓶颈。

## 5. 为什么之前训练能成功，这次不行

已完成 folds 与 `WF-VAL` 的关键差异：

| fold | train window | 是否训练 | 状态 |
| --- | --- | --- | --- |
| WF-2017 | 2015-05-04..2016-12-31 | 是 | 成功 |
| WF-2018 | 2015-05-04..2017-12-31 | 是 | 成功 |
| WF-2019 | 2015-05-04..2018-12-31 | 是 | 成功 |
| WF-2020 | 2015-05-04..2019-12-31 | 是 | 成功 |
| WF-VAL | 2015-05-04..2020-12-31 | 是 | 失败 |
| TEST | frozen pred | 否，本轮只读取 frozen pred | 成功 |

核心原因：

1. `WF-VAL` 比 `WF-2020` 多训练一年数据，训练窗口从 2015-2019 增加到 2015-2020。
2. qlib 训练阶段使用 `instruments: all` 构造 Alpha158 数据，dynamic top150 universe 是预测输出后的过滤口径，不等于训练时只加载 150 只股票。
3. 非 TEST folds 的 qlib internal valid segment 与 train segment 相同。该设计不作为正式 validation，但会让 `DatasetH` 在运行结构上同时存在 train/valid segment，进一步增加内存压力。
4. `TEST` 成功不代表训练成功，因为 TEST 使用 frozen recorder 的 `pred.pkl`，没有在本轮训练 full-provider qlib 模型。
5. 之前 qlib Option C frozen baseline 能存在，只能说明它曾在某个环境完成过训练；不能证明当前 16GB 左右本地环境能重新完成同等训练。

## 6. 当前不能做什么

不能为了跑通而静默做以下事情：

- 减少训练数据；
- 缩短 `WF-VAL` train window；
- 缩短 validation score window；
- 减少 universe；
- 换 provider；
- 换 feature / label / handler；
- 改 model family；
- 启用 GPU 后仍声称与 CPU frozen baseline 完全同口径；
- 进入 LTR 样本构建或回放。

这些都会改变 S1 split-aligned 公平验证的含义。

## 7. 下一步建议

建议进入：

```text
Phase S1B1M：大内存 CPU 环境迁移与内存测量
```

目标：

1. 在 `32GB+` CPU 环境运行同一脚本；
2. 保持数据、fold、provider、feature、label、handler、model family 不变；
3. 增加内存测量，记录 peak RSS / elapsed time；
4. 成功后带回 `WF-VAL.csv`、`WF-VAL.manifest.json` 与完整 S1B1 coverage/gate；
5. 如果 32GB 仍失败，再以实际 peak/oom 证据决定是否升到 64GB 或讨论明确降级分支。

## 8. 给执行者的下一步工作文档：Phase S1B1M

### 8.1 目标

迁移到更大内存 CPU 环境完成 `WF-VAL`，并补齐完整 S1B1 qlib walk-forward score/rank。

### 8.2 必须保持不变

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

### 8.3 必须新增测量

执行者必须用以下任一方式记录内存：

```text
/usr/bin/time -v <command>
```

或等价工具，至少记录：

- Maximum resident set size；
- elapsed time；
- exit code；
- num_threads；
- machine RAM / swap；
- 是否发生 OOM kill。

### 8.4 推荐执行策略

优先在大内存 CPU 环境使用：

```text
S1B1_WF_VAL_NUM_THREADS=4
```

如果仍 OOM，再按用户已授权顺序降到：

```text
2 -> 1
```

这仍然只是资源控制，不是参数搜索；第一个成功线程数即停止。

### 8.5 必须输出

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1M_MEMORY_MIGRATION_EXECUTION_REPORT_CN.md
```

成功时必须生成：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-VAL.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-VAL.manifest.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_qlib_wf_scores.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_score_rank_coverage_by_split.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_score_rank_coverage_by_fold.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_score_rank_coverage_by_date.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_leakage_boundary_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_gate_summary.json
```

### 8.6 禁止事项

- 不训练 LTR；
- 不构建 LTR 样本；
- 不跑组合回放；
- 不做策略比较；
- 不减少数据；
- 不缩短窗口；
- 不减少 universe；
- 不改 provider / feature / label / handler / model family；
- 不改前端/API；
- 不联网；
- 不触发 provider refresh / publish；
- 不切换 accepted latest；
- 不触发 monitor config save / scan / alerts write；
- 不接 broker、orders、quick-trade；
- 不输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 9. 台股只读安全边界审查

未发现 broker、orders、quick-trade、target position、target weight、provider refresh/publish、accepted latest switching、monitor write 或交易链路触达。

本轮为本地研究验证审查，不涉及前端/API network audit。

安全边界结论：`通过`。
