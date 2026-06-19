# Phase S1B1 审查意见与 Phase S1B1R 修复工作文档

生成日期：2026-06-14

## 1. 审查范围

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
```

上一轮授权文档：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B0R_REVIEW_AND_PHASES1B1_WORK_CN.md
```

本轮执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1_QLIB_WF_SCORE_GENERATION_EXECUTION_REPORT_CN.md
```

本轮只审查 qlib walk-forward score/rank 生成、coverage、leakage 与只读安全边界；不审查 LTR 训练、样本构建或回放，因为本轮不允许执行这些内容。

## 2. 审查结论

结论：`未通过，不能进入 S1B2。`

Gate：

```text
s1b1_qlib_wf_scores_data_insufficient
```

主要原因：

```text
WF-VAL validation fold 缺失。
```

执行者已生成：

- `WF-2017`
- `WF-2018`
- `WF-2019`
- `WF-2020`
- `TEST`

但未生成：

```text
WF-VAL: 2021-01-01..2022-12-31 validation score/rank
```

由于 S1 的旧窗口 split-aligned 公平验证必须保留 train / validation / test 三段，缺少 validation score/rank 时，后续不能构建完整 LTR 训练样本，也不能做模型选择或进入回放比较。

## 3. 出了什么问题

这不是当前证据下的方法论失败，而是一个很窄的本地资源失败。

报告与产物显示：

- `WF-VAL` 使用 full provider；
- 训练窗口为 `2015-05-04..2020-12-31`；
- score window 为 `2021-01-01..2022-12-31`；
- 进程两次被系统杀掉，exit code `137`；
- 执行者没有改 fold、没有缩短窗口、没有改 provider、没有改参数来绕过失败。

审查判断：

```text
exit code 137 更像 OOM / 资源压力导致的系统 kill，
不是 universe 不可行，也不是 leakage 失败。
```

已完成 folds 的质量证据可接受，但只能作为部分产物：

- completed score rows：`235307`
- completed date count：`1571`
- completed folds score missing：`0`
- completed folds rank missing：`0`
- completed folds duplicate date/instrument：`0`
- selected count min：`145`
- selected count median：`150.0`
- selected count max：`150`

当前以下文件不得被当作完整 S1B1 通过产物使用：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_qlib_wf_scores.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_qlib_wf_scores_partial.csv
```

它们当前缺少 validation split。

## 4. 偏离主线审查

未发现主线偏离。

执行者遵守了 S1B1 的核心边界：

- 未训练 LTR；
- 未构建 LTR 样本；
- 未跑组合回放；
- 未做策略比较；
- 未调 qlib 或 LTR 参数；
- 未改前端/API；
- 未联网；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未触发 monitor config save / scan / alerts write；
- 未连接 broker、orders、quick-trade 或交易链路；
- 未输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 5. 需要注意的实现问题

### 5.1 WF folds 的 valid segment

脚本中非 TEST folds 使用：

```text
valid_start = train_start
valid_end = train_end
```

也就是 qlib `DatasetH` 的 valid segment 与 train segment 相同。

审查判断：

- 这不构成本轮阻断，因为本轮没有做参数搜索，也没有把该 valid segment 当作模型选择依据；
- 但执行者在 S1B1R 报告中必须说明 qlib `LGBModel.fit(dataset)` 在这里是否只是需要一个 valid segment 才能运行；
- 不得把这个 internal valid segment 表述为 S1 的正式 validation split；
- S1 的正式 validation split 仍只能是 `2021-01-01..2022-12-31` 的 `WF-VAL` score/rank。

### 5.2 Provider 路径一致性

本轮使用：

```text
/home/chuliyang/qlib/data_tw/experiments/yahoo_adjusted_primary/qlib_bin
```

上一轮文档中也出现过 qlib pipeline 下的 provider / calendar 路径。

审查判断：

- 只要该 provider 是同一 frozen qlib data root 的只读本地副本，可以接受；
- S1B1R 必须继续记录 provider_uri，不得静默切换；
- 若切换 provider 路径，必须解释两者是否等价，并给出 calendar / instruments / feature 可比性证据。

## 6. 台股只读安全边界审查

### Findings

未发现 Critical / High / Medium 阻断项。

### Network Audit

本轮为本地只读训练分数生成与文件审查，未涉及前端/API/E2E network audit。

### Text / Agent Semantics

报告中的训练、score、validation、回放、买卖、仓位等表述均处于研究流程、禁止事项或只读边界说明中；未形成真实交易建议、仓位建议、收益承诺、胜率承诺或上涨概率承诺。

### Verdict

只读安全边界通过。

## 7. Phase S1B1R 工作文档：WF-VAL 资源修复

### 7.1 目标

只修复 `WF-VAL` 的 qlib score/rank 生成失败问题，并补齐完整 S1B1 产物。

S1B1R 不解决 LTR 训练、不构建 LTR 样本、不跑回放、不做策略比较。

### 7.2 必须保持不变的口径

必须保持：

```text
WF-VAL qlib train window: 2015-05-04..2020-12-31
WF-VAL score window: 2021-01-01..2022-12-31
config: qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml
model: qlib.contrib.model.gbdt.LGBModel
handler: qlib.contrib.data.handler.Alpha158
provider: full provider, no downgrade unless先回到审查者/用户确认
calendar: qlib day.txt ∩ TWII normalized price calendar
universe: dynamic up to 150, selected_count >= 145
```

不得缩短 validation window，不得改成 static accepted 150，不得改参数，不得把 TEST 反馈用于任何设计。

### 7.3 允许的技术性修复

允许执行者做资源层面的窄修复：

1. 复用已完成 folds，不重跑 `WF-2017`、`WF-2018`、`WF-2019`、`WF-2020`、`TEST`，除非 checksum 或 manifest 明确不一致。
2. 对 `WF-VAL` 单独运行。
3. 保持训练窗口与参数不变，但降低运行峰值内存，例如：
   - 训练完成后按年度、季度或月份分块 predict；
   - 每个 predict segment 后立即落盘并释放对象；
   - 关闭 qlib cache；
   - 降低 LightGBM `num_threads` 仅作为资源控制时可以申请，但必须说明它不改变模型参数语义；如无法确认，应先停止并请审查者判断。
4. 若 qlib API 不支持训练一次后分块 predict，可以把原因写清楚，再提出最小替代方案供审查。

### 7.4 禁止事项

S1B1R 严禁：

- 训练 LTR；
- 构建 LTR 样本；
- 跑组合回放；
- 做策略比较；
- 调 qlib/LTR 参数；
- 更换 model family、handler、feature、label；
- 缩短 `WF-VAL` score window；
- 静默降级 provider / universe；
- 使用 TEST 结果反向改设计；
- 改前端/API；
- 联网；
- 触发 provider refresh / publish；
- 切换 accepted latest；
- 触发 monitor config save / scan / alerts write；
- 接 broker、orders、quick-trade；
- 输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

### 7.5 S1B1R 必须输出

执行者必须输出：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1R_WF_VAL_RESOURCE_REPAIR_EXECUTION_REPORT_CN.md
```

并更新或生成：

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

### 7.6 S1B1R 验收标准

通过条件：

- `WF-VAL` 存在；
- validation coverage 覆盖 `2021-01-01..2022-12-31` 内的 qlib scoring calendar 交易日；
- validation selected count min `>=145`；
- validation score missing count 为 `0`；
- validation rank missing count 为 `0`；
- duplicate date/instrument count 为 `0`；
- train scored coverage 仍为 `2017-01-01..2020-12-31`；
- test coverage 仍为 `2023-01-01..2025-06-30`；
- `s1_test_feedback_used_for_train_or_fold_design=false`；
- `parameter_search_performed=false`；
- `ltr_training_performed=false`；
- `ltr_sample_build_performed=false`；
- `portfolio_replay_performed=false`。

### 7.7 S1B1R Gate

S1B1R 只能给以下 gate 之一：

```text
s1b1r_wf_val_repair_pass_request_s1b2_ltr_sample_build
s1b1r_wf_val_resource_blocked
s1b1r_blocked_by_leakage_or_scope_violation
```

如果再次 exit code 137，且在不改变方法口径的前提下无法完成，执行者必须给出 `s1b1r_wf_val_resource_blocked`，并停止等待审查者/用户决定是否换更大内存环境或允许明确降级方案。
