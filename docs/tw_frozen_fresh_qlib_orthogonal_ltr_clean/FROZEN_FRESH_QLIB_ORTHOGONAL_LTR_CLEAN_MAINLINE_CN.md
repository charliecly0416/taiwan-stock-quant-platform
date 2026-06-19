# Frozen Fresh Qlib + Orthogonal LTR Clean Stacking 主线

生成日期：2026-06-15

## 1. 主线目标

本主线验证一个最干净、最容易解释的 stacking 方案：

```text
冻结原 fresh qlib 模型；
只用 fresh qlib 的样本外 2025 全年 score/rank 训练 orthogonal LTR；
用 2026 数据做 untouched test；
与 frozen fresh qlib baseline 做同口径对比。
```

核心问题：

```text
在不重训 qlib、不使用 qlib in-sample score 的前提下，
正交 LTR 是否能在 fresh qlib 基础上带来稳定增益？
```

## 2. 为什么选择这个方案

前序讨论确认：

- 当前 LTR 输入包含 `qlib_score_raw`，不只是 rank；
- 如果用 frozen fresh qlib 给 2017..2024 训练期打分，再训练 LTR，会出现 qlib in-sample score 问题；
- walk-forward OOS score 更完整，但不同年份来自不同 qlib 模型，raw score 口径可能漂移；
- 最干净方案是固定同一个 fresh qlib 模型，只用它没训练过的时期训练 LTR。

因此本主线采用：

```text
fresh qlib train: 2017-01-10..2024-12-31
LTR train:        2025-01-01..2025-12-31
LTR test:         2026-01-01..2026-05-07
```

解释：

- 2025 对 fresh qlib 是样本外；
- 2026 对 fresh qlib 也是样本外；
- 2025 是 LTR 训练集；
- 2026 是 LTR untouched test；
- qlib score 全部来自同一个 frozen fresh qlib，口径一致。

## 3. Control 与 Treatment

### 3.1 Control

Control 是 frozen fresh qlib baseline：

```text
fresh_qlib_top50_adaptive_baseline
```

使用原 fresh qlib artifact：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/
```

以及必要时 repaired fresh top50 replay-ready artifact。

### 3.2 Treatment

Treatment 是：

```text
frozen fresh qlib + orthogonal LTR rerank
```

LTR 输入允许包含：

- `qlib_score_raw`
- `qlib_rank`
- `qlib_score_percentile_by_date`
- `qlib_score_zscore_by_date`
- rank change / top10 / top30 / top50 flag
- O4 已冻结的技术/市场状态特征
- O2 已通过 PIT 审计的法人筹码与融资融券正交特征

LTR 重排范围：

```text
preserve_scope = top50_only
```

即只对 qlib top50 内做 rerank。

## 4. 固定不变合同

本主线必须保持：

- fresh qlib 模型不重训；
- fresh qlib score 不重算训练期内 score 作为 LTR 训练；
- qlib score 全部来自 frozen fresh qlib 的 OOS 区间；
- LTR 模型家族沿用 O4；
- LTR 超参数沿用 O4；
- LTR label 沿用 O4 / Phase1C：`relevance_10d_top_heavy`；
- LTR feature 白名单在 O4 基础上适配 frozen fresh qlib，不新增其他特征；
- O2 正交数据 PIT-safe delayed availability 合同不变；
- 回放使用 next-day execution；
- fee_rate = `0.001425`；
- tax_rate = `0.003`；
- target_position_count = `10`；
- candidate_k = `50`；
- 不改前端默认策略。

## 5. 禁止事项

严禁：

```text
训练 qlib
调 qlib 参数
训练多个 LTR 版本挑最好
调 LTR 参数
改变 label
改变 split 后用 2026 反选
新增月营收或其他数据源
新增 filter / market gate / turnover rule
用 qlib 2017..2024 in-sample score 训练 LTR
用不同 qlib 模型拼接 OOS score
改 provider / accepted latest
改前端/API
触发 monitor / broker / orders / quick-trade
输出真实买卖建议、目标仓位、目标权重、收益承诺、胜率或上涨概率
```

如执行者发现 2025 样本不足、数据缺失、无法构建 label 或 fresh qlib score 覆盖不足，必须停止并报告，不得自行改窗口到 2024 或扩到 qlib 训练期。

## 6. 阶段设计

### Phase C0：合同冻结与样本可行性审计

目标：

```text
确认 2025 可以作为 LTR train，2026 可以作为 LTR test，
且两段 fresh qlib score 都是 frozen fresh qlib 的 OOS 输出。
```

执行内容：

- 定位 frozen fresh qlib score artifact；
- 审计 2025/2026 覆盖；
- 审计 top50 candidate coverage；
- 审计 O2 正交特征在 2025/2026 的覆盖；
- 审计 10d label 是否可用于 2025 train；
- 确认 2026 test 不用于训练、调参或选择；
- 输出 feature/schema 计划；
- 不训练模型。

输出：

```text
docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC0_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_c0_clean_stacking_contract_feasible
```

停止条件：

- 2025 fresh qlib OOS score 不完整；
- 2025 label 不可构造；
- O2 正交特征无法 PIT-safe join；
- 执行者需要使用 qlib 训练期内 score；
- 需要调参或改 label。

### Phase C1：Row-aligned LTR 样本构建

目标：

```text
构建 2025 train + 2026 test 的 frozen fresh qlib orthogonal LTR 样本。
```

执行内容：

- 以 frozen fresh qlib 2025/2026 score 为基础；
- 拼接技术/市场状态特征；
- 拼接 O2 正交特征；
- 只保留 top50 preserve_scope 所需字段；
- 构造 `relevance_10d_top_heavy` label；
- 输出 row alignment audit；
- 输出 PIT leakage audit；
- 输出 missing report；
- 不训练模型。

输出：

```text
docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC1_ROW_ALIGNED_SAMPLE_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_c1_clean_stacking_sample_passed
```

硬性要求：

```text
train rows only from 2025
test rows only from 2026
no 2026 label used in training
no qlib in-sample period used for LTR training
```

### Phase C2：Orthogonal LTR 训练

目标：

```text
用 2025 样本训练一个 frozen fresh qlib + orthogonal LTR。
```

执行内容：

- 模型家族沿用 O4；
- 超参数沿用 O4；
- label 沿用 O4；
- 只训练一个 treatment；
- 输出 feature importance；
- 输出 training log；
- 输出 score/rank；
- 不做参数搜索。

输出：

```text
docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC2_ORTHOGONAL_LTR_TRAINING_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_c2_clean_stacking_ltr_trained
```

停止条件：

- 必须调参才能跑通；
- 训练样本过少导致模型无意义；
- feature importance / rank metrics 明显异常；
- 需要改 split 或 label。

### Phase C3：2026 同口径回放

目标：

```text
在 2026 untouched test 上比较 treatment 与 frozen fresh qlib baseline。
```

必须比较：

```text
fresh_qlib_top50_adaptive_baseline
frozen_fresh_qlib_orthogonal_ltr
```

可保留审计参考：

```text
O4 orthogonal LTR
repaired fresh qlib P1 result
```

但主结论只基于 2026：

```text
treatment vs frozen fresh qlib baseline
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
- 是否对 2026 形成真实增益。

输出：

```text
docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC3_2026_REPLAY_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_c3_clean_stacking_2026_replay_completed
```

停止条件：

- baseline 2026 指标无法复现；
- 回放口径不一致；
- 2026 数据被用于训练/调参；
- 只报告收益不报告回撤、动作、换手。

### Phase C4：审查与决策

目标：

```text
判断 clean stacking 是否值得进入只读研究候选或继续扩展。
```

通过条件建议：

- 2026 net return 高于 fresh qlib，或收益相近但回撤/动作/换手明显改善；
- 最大回撤不明显恶化；
- action_count / turnover 不明显恶化；
- PnL 不集中在单一股票或日期；
- 正交特征有可解释贡献；
- 没有 PIT / score provenance / accounting 问题。

可能 gate：

```text
clean_stacking_supported_for_readonly_candidate
clean_stacking_not_supported_vs_fresh_qlib
clean_stacking_blocked_by_sample_or_contract
```

若通过：

```text
只允许进入只读产品化设计，不直接改默认。
```

若不通过：

```text
收尾，不继续在该合同下补丁式优化。
```

## 7. 用户第一性原则

最终要回答用户能理解的问题：

```text
在 fresh qlib 已经很强的情况下，
加一个只用样本外 qlib 输出训练的正交 LTR，
是否真的让 2026 的历史模拟更好？
```

不得展示复杂训练细节压过结论。

若产品化，只能表达为：

- 历史只读研究候选；
- 不是默认策略；
- 不构成投资建议；
- 不产生真实交易；
- 显示收益、回撤、动作和换手取舍。

## 8. 给执行者的一句话

```text
请按 docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/FROZEN_FRESH_QLIB_ORTHOGONAL_LTR_CLEAN_MAINLINE_CN.md 执行 Phase C0，只冻结并审计 frozen fresh qlib + orthogonal LTR clean stacking 合同：LTR train 只能用 2025，test 只能用 2026，不得训练、调参、改 split/label/model、使用 qlib 训练期 in-sample score、引入 walk-forward OOS、多模型 score、改前端/API/provider/accepted latest/monitor 或触发交易链路。
```

## 9. 给审查者的一句话

```text
请按 docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/FROZEN_FRESH_QLIB_ORTHOGONAL_LTR_CLEAN_MAINLINE_CN.md 审查执行者 Phase C0 报告，重点确认 fresh qlib 已冻结、2025 对 qlib 是 OOS 且仅作 LTR train、2026 仅作 untouched test、未使用 qlib 训练期 in-sample score、未引入 walk-forward 多模型口径，并判断是否允许进入 Phase C1。
```
