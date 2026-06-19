# Extended OOS Qlib + Orthogonal LTR 支线主线

生成日期：2026-06-15

## 1. 主线目标

本支线只验证一个假设：

```text
前一条 clean stacking 中，frozen fresh qlib + orthogonal LTR 没有跑赢 fresh qlib，
是否主要因为 LTR 训练样本太少。
```

因此本支线采用更长的 LTR 训练窗口：

```text
qlib train: 2018-01-01..2022-12-31
qlib frozen OOS score: 2023-01-01..2026-05-07
LTR train: 2023-01-01..2025-12-31
LTR untouched test: 2026-01-01..2026-05-07
```

核心问题：

```text
当 LTR 使用 2023-2025 三年 OOS score 训练后，
orthogonal LTR 是否能在 2026 上相对 frozen qlib baseline 形成真实增益？
```

## 2. 设计原则

这条支线不是产品化主线，也不是默认策略变更。

必须保持：

- qlib 只用 2018-2022 训练；
- qlib 训练完成后冻结；
- 2023-2026 qlib score 必须全部来自同一个 frozen qlib；
- LTR 只用 2023-2025 训练；
- 2026 只作为 untouched test；
- LTR 模型家族和超参数沿用 O4；
- LTR label 沿用 `relevance_10d_top_heavy`；
- O2 正交数据 PIT-safe delayed availability 合同不变；
- treatment 只在 qlib top50 内 rerank；
- 回放使用 same next-day execution / fee / tax / position / candidate 口径。

## 3. 为什么不是直接扩展上一条 clean stacking

上一条 clean stacking 使用：

```text
fresh qlib train: 2017-01-10..2024-12-31
LTR train: 2025
LTR test: 2026
```

优点是 fresh qlib 很强，且 score 口径干净。

缺点是：

```text
LTR 训练样本只有 2025 一年。
```

本支线为了验证样本量问题，主动把 qlib 训练窗口前移到 2018-2022，使 2023-2025 都成为同一个 qlib 的 OOS 区间，从而给 LTR 提供三年训练样本。

代价：

- qlib baseline 可能弱于 fresh qlib；
- 本支线结论不能直接替代 fresh qlib 默认策略；
- 本支线只能回答“更长 LTR 训练样本是否让正交 LTR 在 frozen qlib 上有增益”。

## 4. Control 与 Treatment

### 4.1 Control

Control：

```text
extended_oos_frozen_qlib_top50_baseline
```

定义：

- qlib 用 2018-2022 训练；
- 2023-2026 用同一个 frozen qlib 产出 OOS score；
- 2026 回放用 qlib top50 baseline。

### 4.2 Treatment

Treatment：

```text
extended_oos_frozen_qlib_orthogonal_ltr
```

定义：

- 输入为同一个 frozen qlib 的 2023-2025 OOS top50 score；
- 拼接 O4 技术/市场状态特征；
- 拼接 O2 PIT-safe 法人筹码与融资融券正交特征；
- 用 2023-2025 训练 LTR；
- 在 2026 top50 内 rerank；
- 与 control 同口径回放。

## 5. 固定合同

### 5.1 Qlib 合同

冻结：

```text
qlib train: 2018-01-01..2022-12-31
qlib validation: 2023-01-01..2023-12-31
qlib test/score OOS: 2023-01-01..2026-05-07
provider: 复用已审计台湾 qlib provider，若需改变必须报告
model family: qlib.contrib.model.gbdt.LGBModel
model params: 沿用 fresh qlib S2B 参数，除日期 split 外不得调参
thread ladder: 4 -> 2 -> 1
```

说明：

- 2023 同时可作为 qlib validation 与 LTR train 的一部分，但 qlib 训练不得使用 2023 label 进行重新调参或选择多个模型；
- 如果执行者认为 qlib validation 会影响 frozen model 选择，必须在 E0 报告中说明，并由审查者决定是否改为无 validation 或固定早停策略。

### 5.2 LTR 合同

冻结：

```text
LTR train: 2023-01-01..2025-12-31
LTR untouched test: 2026-01-01..2026-05-07
preserve_scope: top50_only
model family: LightGBM.LGBMRanker
objective: lambdarank
hyperparameters: O4 frozen params
label: relevance_10d_top_heavy
```

### 5.3 Replay 合同

冻结：

```text
execution: next-day execution
fee_rate: 0.001425
tax_rate: 0.003
target_position_count: 10
candidate_k: 50
window: 2026-01-01..2026-05-07
```

## 6. 允许特征

LTR 输入允许包含：

- frozen qlib score / rank；
- qlib score percentile / zscore by date；
- rank change；
- top10 / top30 / top50 flag；
- O4 已冻结技术/市场状态特征；
- O2 PIT-safe 法人筹码与融资融券正交特征；
- missing / delay flag。

禁止新增：

- 月营收；
- 估值；
- 新 FinMind dataset；
- 新技术指标；
- 新市场状态指标；
- 新 filter；
- market gate；
- turnover rule。

## 7. 阶段设计

### Phase E0：合同与可行性审计

目标：

```text
确认 2018-2022 qlib 训练、2023-2025 LTR train、2026 test 的数据与合同可执行。
```

执行内容：

- 定位 provider 与原 S2B qlib 参数；
- 审计 2018-2026 数据覆盖；
- 审计 2023-2025 是否可构建 top50 OOS score；
- 审计 2023-2025 O2 正交特征覆盖；
- 审计 2023-2025 `relevance_10d_top_heavy` label 可用性；
- 审计 2026 test 覆盖；
- 输出 split / artifact / feature schema 计划；
- 不训练模型。

输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE0_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_e0_extended_oos_contract_feasible
```

停止条件：

- 2018-2022 qlib 训练数据不足；
- 2023-2025 不能作为 qlib OOS score 区间；
- 2023-2025 label 不可构造；
- O2 正交特征无法 PIT-safe join；
- 必须使用 2026 做训练、调参或模型选择。

### Phase E1：2018-2022 Frozen Qlib 训练与 OOS 打分

目标：

```text
训练一个只使用 2018-2022 的 frozen qlib，
并为 2023-2026 产出同一模型的 OOS score/rank。
```

执行内容：

- 使用 S2B LGBModel 参数；
- 只改变 split 日期；
- qlib 训练只用 2018-2022；
- 对 2023-2026 输出 raw score 与 post-filter top50 score；
- 输出 leakage / resource / forbidden action audit。

输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE1_FROZEN_QLIB_TRAINING_AND_OOS_SCORE_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_e1_frozen_qlib_oos_score_completed
```

停止条件：

- 需要调 qlib 参数；
- 需要改变 provider；
- 无法生成 2023-2026 同一模型 OOS score；
- OOM 后无法按 4 -> 2 -> 1 完成。

### Phase E2：2023-2025 LTR Row-aligned 样本构建

目标：

```text
基于 E1 frozen qlib OOS score，
构建 2023-2025 LTR train 与 2026 untouched test 样本。
```

执行内容：

- 只保留 qlib top50；
- 拼接 O4 技术/市场状态特征；
- 拼接 O2 PIT-safe 正交特征；
- 构造 `relevance_10d_top_heavy` label；
- 输出 row alignment / PIT / missing / score provenance audit；
- 不训练 LTR。

输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE2_ROW_ALIGNED_SAMPLE_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_e2_extended_oos_ltr_sample_passed
```

硬性要求：

```text
train rows only from 2023-2025
test rows only from 2026
no 2026 label used in training
all qlib scores from same E1 frozen qlib
```

### Phase E3：Orthogonal LTR 训练

目标：

```text
用 2023-2025 样本训练一个 O4 参数的 orthogonal LTR。
```

执行内容：

- 模型家族沿用 O4；
- 超参数沿用 O4；
- label 沿用 O4 / Phase1C；
- 只训练一个 treatment；
- 输出 feature importance、rank metrics、score/rank；
- 不做参数搜索。

输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE3_ORTHOGONAL_LTR_TRAINING_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_e3_extended_oos_ltr_trained
```

停止条件：

- 必须调参才能跑通；
- 训练样本仍然过少；
- feature importance / rank metrics 明显异常；
- 需要改 split 或 label。

### Phase E4：2026 同口径回放

目标：

```text
比较 extended_oos_frozen_qlib_top50_baseline
与 extended_oos_frozen_qlib_orthogonal_ltr 在 2026 的表现。
```

指标：

- fee/tax adjusted net return；
- max drawdown；
- action_count；
- turnover_proxy；
- fee_and_tax；
- next-day accounting；
- coverage；
- PnL concentration；
- rank metrics；
- feature importance；
- 是否因更长 LTR train 形成真实增益。

输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE4_2026_REPLAY_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_e4_extended_oos_2026_replay_completed
```

停止条件：

- baseline 2026 指标无法复现；
- replay 口径不一致；
- 2026 数据被用于训练/调参；
- 只报告收益不报告回撤、动作、换手。

### Phase E5：决策收口

目标：

```text
判断更长 LTR train 是否解决 clean stacking 泛化不足问题。
```

可能 gate：

```text
extended_oos_ltr_supported_by_longer_train
extended_oos_ltr_not_supported_vs_frozen_qlib
extended_oos_ltr_blocked_by_contract_or_sample
```

通过条件：

- treatment 2026 net return 高于 frozen qlib baseline，或收益相近但回撤/动作/换手明显改善；
- max drawdown 不明显恶化；
- action_count / turnover 不明显恶化；
- PnL 不集中；
- 正交特征有可解释贡献；
- PIT / score provenance / accounting 无阻断。

输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE5_DECISION_REVIEW_CN.md
```

## 8. 禁止事项

全支线禁止：

- 改默认策略；
- 改前端/API；
- provider refresh / publish / accepted latest；
- monitor / broker / orders / quick-trade；
- 使用 2026 做训练、调参或选择；
- 训练多个版本挑最好；
- 调 qlib 或 LTR 参数；
- 新增 O2/O4 之外特征；
- 新增 filter / market gate / turnover rule；
- 输出真实买卖建议、目标仓位、目标权重、收益承诺、胜率或上涨概率。

## 9. 审查要求

每个 Phase 审查者必须检查：

- 是否保持时间边界；
- 是否 qlib 只用 2018-2022 训练；
- 是否 2023-2026 score 来自同一 frozen qlib；
- 是否 LTR 只用 2023-2025 训练；
- 是否 2026 untouched；
- 是否 O2 available_at PIT-safe；
- 是否没有调参、多版本选择或新增规则；
- 是否没有触发前端/provider/accepted latest/monitor/交易链路。

## 10. 给执行者的一句话

```text
请按 docs/tw_extended_oos_qlib_orthogonal_ltr/EXTENDED_OOS_QLIB_ORTHOGONAL_LTR_MAINLINE_CN.md 先执行 Phase E0：只做合同与可行性审计，确认 2018-2022 可训练 frozen qlib、2023-2025 可作为同一 frozen qlib 的 OOS LTR train、2026 可作为 untouched test，并审计 O2 PIT 特征、label、top50 coverage；不得训练、调参、回放、改默认策略、触发 provider/accepted latest/monitor/交易链路或使用 2026 做训练/选择。
```

## 11. 给审查者的一句话

```text
请按 docs/tw_extended_oos_qlib_orthogonal_ltr/EXTENDED_OOS_QLIB_ORTHOGONAL_LTR_MAINLINE_CN.md 审查 Phase E0 报告，重点确认 2018-2022 qlib 训练合同、2023-2025 LTR train、2026 untouched test、同一 frozen qlib OOS score、O2 PIT-safe 特征和禁止事项是否可行，并判断是否允许进入 E1。
```
