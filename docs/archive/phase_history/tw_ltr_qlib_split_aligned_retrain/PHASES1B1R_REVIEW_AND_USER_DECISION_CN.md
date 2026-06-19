# Phase S1B1R 审查意见与用户决策文档

生成日期：2026-06-14

## 1. 审查范围

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
```

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1R_WF_VAL_RESOURCE_REPAIR_EXECUTION_REPORT_CN.md
```

上一轮修复文档：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1_REVIEW_AND_PHASES1B1R_REPAIR_WORK_CN.md
```

本轮只审查 `WF-VAL` qlib score/rank 资源修复，不审查 LTR 训练、样本构建或回放。

## 2. 审查结论

结论：`S1B1R 未通过，当前必须停止并由用户决策。`

Gate：

```text
s1b1r_wf_val_resource_blocked
```

执行者本轮没有偏离主线：未训练 LTR、未构建样本、未跑回放、未调参、未改 provider、未切 accepted latest、未碰前端/API/monitor/交易链路。

## 3. 到底是什么原因

当前最可信原因是：

```text
本地环境内存/资源不足，无法完成 full-provider WF-VAL 的 qlib LGBModel 训练。
```

证据：

1. S1B1 初次失败时，`WF-VAL` 在 full provider 下被系统 `Killed`，exit code `137`。
2. S1B1R 已把预测阶段改成“训练一次 + 2021-2022 按月分块 predict”。
3. 但 S1B1R 仍在 `WF-VAL` 模型训练阶段被 `Killed`，尚未进入按月预测。
4. 日志显示 qlib data loading / process 已完成，失败发生在模型训练阶段。
5. 已完成的 `WF-2017..WF-2020` 和 `TEST` 质量正常，说明不是 calendar / universe 根本不可行。

审查判断：

```text
问题不是预测窗口太长，而是 WF-VAL 训练窗口 2015-05-04..2020-12-31
在当前 full provider + Alpha158 + LGBModel 配置下超过了本地可承受资源。
```

## 4. “数据少一些然后训久一点”是否可行

不能直接这么做，除非用户明确接受降级结论。

原因：

```text
S1 的目的不是随便训出一个能跑的 qlib score，
而是做与 qlib Option C 对齐的旧窗口公平验证。
```

如果减少数据，可能会改变以下任一口径：

- 缩短 train window；
- 减少股票 universe；
- 减少 feature / handler；
- 换 provider；
- 改 label；
- 改模型参数。

这些都会让 S1 不再回答主线问题：

```text
在 qlib 同样旧训练窗口下，LTR 方法是否仍然有增益？
```

所以：

- `少一点数据` 可以作为工程降级实验；
- 但它不能与原 S1 split-aligned 公平验证混在一起；
- 如果采用，结论必须标为 `degraded / data-reduced validation`，不能作为正式 S1 通过证据。

“训久一点”也不能解决当前问题。当前进程是在训练阶段被系统杀掉，不是训练轮数不够、时间不够或优化未收敛。更久只会占用更久资源，不能降低峰值内存。

## 5. CUDA 是否能解决

不应把 CUDA 作为第一反应。

当前模型是 qlib 的 `LGBModel`，底层是 LightGBM。是否能用 GPU 取决于：

- 当前 LightGBM 是否编译了 GPU 支持；
- qlib LGBModel 是否正确传递 `device_type=gpu` 等参数；
- GPU 显存是否足够；
- GPU 版本结果是否仍可与原 CPU frozen qlib baseline 公平比较。

更稳妥的优先级是：

```text
先换更大内存的 CPU 环境，保持脚本、provider、参数、fold 完全不变。
```

如果服务器既有更大内存又有 CUDA，可以先按 CPU 路线跑同一脚本；只有 CPU 仍不可行时，再讨论 GPU 版 LightGBM 是否作为明确变更口径的实验。

## 6. 当前可选路线

### 路线 A：推荐，转到更大内存环境跑同一脚本

保持完全不变：

```text
WF-VAL train window: 2015-05-04..2020-12-31
WF-VAL score window: 2021-01-01..2022-12-31
provider: /home/chuliyang/qlib/data_tw/experiments/yahoo_adjusted_primary/qlib_bin
config: qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml
handler: Alpha158
model: LGBModel
universe: dynamic up to 150, selected_count >=145
```

优点：结论最干净，仍是正式 S1 split-aligned 验证。

执行者下一步只需准备一份可迁移运行说明，列出脚本、依赖、输入目录、输出目录和验收文件。

### 路线 B：本机再做一次低线程资源尝试

允许把 LightGBM `num_threads` 从 `8` 降到 `1` 或 `2`，只作为资源控制，并在 manifest 中明确记录。

注意：

- 这不是参数搜索；
- 不得尝试多个线程后选择效果更好的；
- 只能用来确认能不能在本地跑通；
- 如果结果通过，审查者仍要判断低线程是否影响可比性；
- 如果失败，必须停止，不能继续改数据口径。

优点：成本低。

风险：`num_threads` 虽主要是计算资源参数，但仍是配置变更，需要清楚披露。

### 路线 C：数据降级实验

例如减少股票数量、缩短 train window、减少 feature。

审查意见：不推荐作为当前 S1 正式路线。

如果用户选择该路线，必须新建降级主线或降级分支，结论只能是：

```text
data-reduced feasibility / degraded validation
```

不能用于证明原主线的 qlib/LTR split-aligned 公平验证成立。

### 路线 D：CUDA / GPU LightGBM

只有在确认 LightGBM GPU 可用、显存足够、且用户接受这是执行环境/可能模型实现口径变化后，才考虑。

不建议直接作为下一步，因为它比“更大内存 CPU 跑同一脚本”引入更多可比性问题。

## 7. 审查者建议

建议优先选择：

```text
路线 A：转到更大内存 CPU 环境，运行同一脚本，不改变任何数据或模型口径。
```

如果用户暂时不方便转环境，可以先允许：

```text
路线 B：本机只做一次 num_threads=1 的资源尝试。
```

不建议现在选择路线 C。

## 8. 给执行者的下一步工作文档：Phase S1B1S 迁移/低线程资源方案

### 8.1 目标

在不改变 S1 方法口径的前提下，完成 `WF-VAL` qlib score/rank。

### 8.2 执行者必须先等待用户确认路线

执行者不得自行选择路线 A/B/C/D。

用户确认后才能执行：

```text
Phase S1B1S
```

### 8.3 若用户选择路线 A

执行者只准备迁移运行包/说明，不改实验口径：

- 列出需要同步的输入目录；
- 列出 Python/qlib/LightGBM 依赖；
- 列出运行命令；
- 列出输出目录；
- 列出完成后必须带回的产物；
- 保持脚本和配置不变；
- 不触发联网/provider refresh/publish/accepted latest/monitor/交易链路。

必须生成报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1S_RESOURCE_MIGRATION_EXECUTION_REPORT_CN.md
```

### 8.4 若用户选择路线 B

执行者只允许做一次低线程资源控制：

```text
num_threads: 1
```

要求：

- 只对 `WF-VAL` 生效；
- 记录原始 `num_threads=8` 与资源尝试 `num_threads=1`；
- 不得尝试多个线程数后比较效果；
- 不得改 learning_rate、num_leaves、max_depth、lambda、feature、label、provider、universe、fold window；
- 仍需输出完整 coverage / leakage / gate。

必须生成报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1S_LOW_THREAD_RESOURCE_EXECUTION_REPORT_CN.md
```

### 8.5 S1B1S 禁止事项

- 不训练 LTR；
- 不构建 LTR 样本；
- 不跑组合回放；
- 不做策略比较；
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
