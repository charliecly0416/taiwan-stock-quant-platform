# Phase S1B3 执行报告：Training Policy Freeze

生成日期：2026-06-14

## 1. 本轮目标

按 [PHASES1B2R_REVIEW_AND_PHASES1B3_POLICY_WORK_CN.md](/home/chuliyang/taiwan-stock-quant-platform/docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B2R_REVIEW_AND_PHASES1B3_POLICY_WORK_CN.md) 要求，只冻结基于 S1B2R 样本的 split-aligned LTR 训练政策，不实际训练，不回放，不调参。

本轮完成内容仅包括：

1. 冻结唯一允许的样本、schema、feature 输入。
2. 冻结 `sample_complete == true` 训练过滤规则。
3. 冻结 `train_scored / validation / test` 的使用边界。
4. 冻结 `split_aligned_ltr_simple` 与 `split_aligned_ltr_turnover_controlled` 两个候选的训练政策关系。
5. 冻结单一既有保守参数表与禁止事项。

## 2. 输入冻结

唯一允许的训练输入如下：

- [phase_s1b2_ltr_samples.csv](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_ltr_samples.csv)
- [phase_s1b2_sample_schema.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_sample_schema.json)
- [phase_s1b2_feature_list.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_feature_list.json)

训练过滤固定为：

```text
sample_complete == true
```

本轮未重建样本，未修改 feature list，未新增 label，未改变 split。

## 3. Split 使用边界冻结

固定 split 合同：

| split | 日期范围 | sample_complete 行数 | 用途 |
| --- | --- | ---: | --- |
| train_scored | 2017-01-01..2020-12-31 | 141085 | 训练拟合 |
| validation | 2021-01-01..2022-12-31 | 69812 | 固定评估诊断 |
| test | 2023-01-01..2025-06-30 | 87345 | 后续单次 holdout 评估 |

补充说明：

- `train_scored` 明确不是完整 `2015..2020`。
- `validation` 本轮只授权固定评估诊断，不授权参数搜索。
- `test` 禁止用于训练、早停、候选选择、参数选择、label 阈值选择、feature 选择。

## 4. 候选训练政策冻结

本轮只冻结两个候选：

1. `split_aligned_ltr_simple`
2. `split_aligned_ltr_turnover_controlled`

冻结结论：

- 两个候选共用同一个 LTR 训练分数来源。
- `turnover_controlled` 只允许在后续 score 使用层或 rerank 层增加约束。
- `turnover_controlled` 不得修改 `ltr_relevance_label`，不得在本轮根据收益、回撤、动作次数、换手结果反推训练阈值。

## 5. 参数表冻结

本轮采用仓内现有、且最直接兼容当前 S1B2R `ltr_relevance_label` 的保守 LambdaMART 基线口径，来源为 [train_tw_ltr_phase1_lambdamart.py](/home/chuliyang/taiwan-stock-quant-platform/scripts/train_tw_ltr_phase1_lambdamart.py)。

选择理由：

1. 该脚本已经使用 `LightGBM.LGBMRanker + objective=lambdarank`。
2. 该脚本按 `date` 做 ranking group，直接匹配当前 split-aligned LTR 训练需求。
3. 该脚本直接使用离散相关性标签训练，更接近当前 S1B2R 的 `ltr_relevance_label`，不需要引入 Phase1C 后续 score blend / top50 preserve 的额外策略层逻辑。
4. 这满足“只选一个既有已存在参数表，不做参数搜索”的边界。

冻结参数如下：

| 参数 | 值 |
| --- | --- |
| model_family | `LightGBM.LGBMRanker` |
| objective | `lambdarank` |
| metric | `ndcg` |
| boosting_type | `gbdt` |
| group_key | `date` |
| label_column | `ltr_relevance_label` |
| n_estimators | `120` |
| learning_rate | `0.05` |
| num_leaves | `31` |
| min_child_samples | `20` |
| random_state | `42` |
| n_jobs | `2` |
| verbose | `-1` |
| eval_at | `[10, 30, 50]` |
| early_stopping_enabled | `false` |
| parameter_search | `false` |

## 6. Validation / Test 使用规则

`validation` 允许：

- 固定 `eval_set` 诊断；
- 检查训练失败或明显异常；
- 在共用训练分数前提下，记录 simple / turnover-controlled 的候选诊断。

`validation` 禁止：

- 反复试参；
- 因表现修改 feature；
- 因表现修改 label；
- 因表现修改 split 或 universe；
- 使用 test 反馈做任何训练决策。

`test` 允许：

- 在后续训练真正完成后做单次 holdout 评估。

`test` 禁止：

- 训练；
- 早停；
- 候选选择；
- 参数选择；
- label threshold 选择；
- feature 选择。

## 7. 产物

本轮新增冻结产物：

- [phase_s1b3_training_policy.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_training_policy.json)
- [phase_s1b3_feature_label_contract.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_feature_label_contract.json)
- [phase_s1b3_split_usage_contract.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_split_usage_contract.json)
- [phase_s1b3_forbidden_action_audit.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_forbidden_action_audit.json)
- [phase_s1b3_gate_summary.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_gate_summary.json)

## 8. 验证

本轮验证方式为静态合同核对，不执行训练：

1. 核对 S1B2R 样本路径、schema、feature list 路径已写入冻结合同。
2. 核对 `sample_complete == true` 已明确写入训练过滤。
3. 核对 `train_scored / validation / test` 边界与 S1B2 产物一致。
4. 核对候选仅限 `split_aligned_ltr_simple` 与 `split_aligned_ltr_turnover_controlled`。
5. 核对参数表仅引用单一既有脚本来源，未引入参数搜索。
6. 核对禁止事项覆盖：无训练、无回放、无策略收益比较、无前端/API、无 provider/accepted latest/monitor/交易链路。

## 9. 禁止事项执行结果

本轮未执行以下动作：

- 未训练 LTR；
- 未训练 qlib；
- 未生成 score / rank；
- 未回放；
- 未比较策略收益；
- 未调参；
- 未新增 feature / label / 数据源；
- 未联网；
- 未改前端/API；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未触发 monitor / trading chain；
- 未输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 10. 结论

本轮完成 S1B3 training policy freeze，满足进入下一轮 LTR 训练前的合同冻结要求。

推荐 gate：

```text
s1b3_training_policy_freeze_pass_request_s1b4_ltr_training
```

当前未发现需要用户额外决策的参数 tradeoff；因此本轮不阻塞，等待审查者决定是否进入下一步。
