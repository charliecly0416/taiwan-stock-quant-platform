# Phase S1A 审查意见：停止推进并等待用户决策

生成日期：2026-06-14

## 1. 审查范围

主线依据：`docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md`

审查入口：`docs/tw_ltr_qlib_split_aligned_retrain/PHASES1A_SCORE_RANK_COVERAGE_REPORT_CN.md`

本轮按 S1A 要求审查：旧窗口 `2015-05-04..2025-06-30` 的 qlib score/rank 覆盖与生成口径诊断，判断是否可以进入 S1B 样本构建和训练。

## 2. 审查结论

结论：`不放行进入 S1B，必须停下来由用户确认 qlib score/rank 生成政策与 universe 口径。`

建议 gate：

```text
split_aligned_data_insufficient_pending_user_decision
```

若必须使用主线三选一 gate，则当前只能给：

```text
split_aligned_data_insufficient
```

原因：S1A 已证明 frozen qlib `pred.pkl` 只覆盖 S1 test，不覆盖 S1 train / validation；当前 LTR 又依赖 qlib score/rank，因此不能直接构建 split-aligned LTR 训练样本。

## 3. 已核验事实

### 3.1 frozen qlib pred 覆盖

S1A 报告与产物一致：

- `pred.pkl` 行数：`89550`
- 日期范围：`2023-01-03..2025-06-30`
- 日期数：`597`
- instrument union：`412`
- score missing：`0`

结论成立：frozen qlib pred 覆盖 S1 test，不覆盖 S1 train / validation。

### 3.2 split coverage

已核验 `phase_s1a_qlib_score_rank_coverage.csv`：

| split | target symbol-date | frozen pred score | missing frozen score/rank | existing LTR sample rows |
| --- | ---: | ---: | ---: | ---: |
| s1_train | 217650 | 0 | 217650 | 0 |
| s1_validation | 73500 | 0 | 73500 | 16606 |
| s1_test | 89550 | 89550 | 0 | 49133 |

结论成立：缺口不是 price，而是旧窗口 qlib score/rank 来源。

### 3.3 S1A 停止位置正确

S1A 未训练、未调参、未构建 S1 样本、未跑回放、未改前端/API、未触发 provider refresh/publish、未切换 accepted latest、未触发 monitor/broker/orders/quick-trade。

## 4. 必须停止讨论的问题

### 问题 A：LTR train 期 qlib score/rank 应该怎么生成？

S1A 给出 4 个选项，其中只有两个可能继续主线：

1. `generate_in_sample_scores_from_frozen_qlib_model_for_train_valid`
2. `cross_fit_or_walk_forward_qlib_scores_for_train_valid`

审查意见：不建议直接采用 in-sample qlib scores 作为默认方案。

理由：

- qlib model 的 train 是 `2015-05-04..2020-12-31`；如果用这个已在全 train 上训练好的模型回头给同一 train 期打分，LTR train 特征就包含 qlib 的 in-sample 预测信号。
- 这未必是“未来函数”，但会改变“公平验证 LTR 方法”的语义：LTR 学到的是 qlib in-sample 排名上的二阶模式，而 test 用的是 out-of-sample qlib score。
- train/test 的 qlib score 生成语义不一致，会让 S1 结论变弱，后续很难向用户解释。

更严谨方案是 cross-fit / walk-forward qlib scores：

- 对 S1 train 内部生成 out-of-fold qlib score；
- validation 使用只在 train 或对应历史窗口训练出的 qlib score；
- test 使用 frozen qlib test pred 或同口径固定模型 pred；
- fold、训练窗口、参数必须预先冻结，不能看 test 后调整。

但这会增加 qlib 训练工作，属于新的 S1B0 设计，不应由执行者自行推进。

### 问题 B：S1A target universe 为什么每天固定 150？

已核验 `phase_s1a_qlib_score_rank_coverage_daily.csv`：

- s1_train 每天 target symbol count 固定 `150`；
- s1_validation 每天固定 `150`；
- s1_test 每天固定 `150`。

风险：报告没有证明这 150 个 symbol 是按当日可得、PIT-safe 的 universe，还是用全窗口 active days / 未来 accepted universe 选出的 static Top150。

如果把未来才确认的 150 个股票回填到 2015 训练，会产生 survivorship / selection leakage。即便这只是研究 universe，也会影响旧窗口公平验证。

S1 继续前必须冻结 universe 口径：

- 方案 U1：沿用 Option C / accepted 150 static universe，但明确承认这是 static research universe，不作为严格全市场 PIT 结论；
- 方案 U2：按 qlib `tw_liquid_dyn` instrument ranges 做 as-of active universe，每日动态选取可交易且当日有效的股票；
- 方案 U3：只在 frozen qlib pred 已覆盖的 test 上比较，放弃 S1 train/validation LTR 训练，即返回 data insufficient。

审查意见：若目标是“公平验证方法是否有效”，更推荐 U2；若目标是“尽量复刻当前 Option C 产品口径”，可以接受 U1，但结论必须降级为 static research universe replay，不能说是严格 PIT 全市场验证。

## 5. 台股只读安全边界审查

### Findings

未发现 broker、quick-trade、orders、target-position、target-weight、monitor write、provider publish/refresh、accepted latest switching。

### Network Audit

S1A 未提供 network audit；本轮为本地只读诊断，不涉及前端/API/E2E，未要求 network audit。

### Text / Agent Semantics

报告中的“买卖、仓位、收益、训练、调参”等词均处于禁止事项、历史模拟或研究验证上下文，不构成实际交易建议、收益承诺、胜率或上涨概率承诺。

### Verdict

只读安全边界通过。

## 6. 给用户的决策点

请用户确认下一步采用哪条路线：

### 路线 1：严谨公平验证，推荐

冻结 `cross-fit_or_walk-forward qlib scores + PIT/as-of active universe`。

优点：最符合公平验证和第一性原则，S1 结论最干净。

代价：需要新增 qlib score 生成设计，S1 会变成 S1B0 先冻结 fold/window/参数，再执行，不会很快出结果。

### 路线 2：产品口径复刻，较快但结论降级

冻结 `in-sample qlib train scores + static accepted/top150 research universe`。

优点：更快，更接近当前 Option C / LTR 产品研究池。

代价：S1 不能声称严格 out-of-sample 方法验证，只能称为 static research universe split replay；训练期 qlib score 是 in-sample，结论解释力弱。

### 路线 3：停止 S1，判定旧窗口 data insufficient

不再为旧窗口补 qlib train/validation scores，直接给 `split_aligned_data_insufficient`。

优点：不引入复杂设计和额外训练。

代价：无法回答“同 qlib 旧窗口下 LTR 方法是否有效”，也不能进入 S2，除非用户另行确认。

## 7. 暂停指令

执行者不得继续 S1B 样本构建、训练或回放，直到用户确认 qlib score/rank 生成政策与 universe 口径。
