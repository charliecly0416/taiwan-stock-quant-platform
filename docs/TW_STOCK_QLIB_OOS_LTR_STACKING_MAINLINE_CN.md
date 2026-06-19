# Qlib OOS Score -> LTR Meta-Reranker 时序错开主线文档

生成日期：2026-06-14

## 1. 背景与问题

当前几轮验证暴露出一个关键问题：

如果 LTR 使用 `qlib_score / qlib_rank` 作为输入特征，那么 qlib score 对 LTR 训练样本来说最好应是 **样本外 / out-of-sample / out-of-fold** 的 score。

否则会出现：

```text
qlib 用某段数据训练
qlib 再给同一段数据打分
LTR 又拿这个 qlib score 训练
```

这会让 LTR 学到的 qlib score 不是“真实上线时 qlib 对未知未来的预测表现”，而是 qlib 对自身训练段的拟合表现。它不一定是严格未来函数，但会让 LTR 的训练语义失真。

因此，合理的 stacked pipeline 应该是：

```text
qlib train window A
-> qlib 对后续 window B 生成 OOS score/rank
-> LTR 用 window B 的 qlib OOS score/rank + 技术/市场特征 + 后验 label 训练
-> 在更后续 window C 做最终组合回放
```

简写为：

```text
qlib train < LTR train < final test
```

而不是：

```text
qlib train == LTR train
```

---

## 2. 原先“旧 qlib + 新 LTR”到底用什么数据训练

根据现有审计文件，原先旧 qlib + 新 LTR Phase1C 的关键时间线是：

### 2.1 qlib Option C frozen baseline

来源配置：

```text
qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml
```

训练窗口：

```text
train: 2015-05-04..2020-12-31
valid: 2021-01-01..2022-12-31
test / research backtest: 2023-01-01..2025-06-30
```

也就是说，旧 qlib 模型训练截止在 `2020-12-31`。

### 2.2 Phase1C LTR

来源产物：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
```

LTR split：

```text
train: 2022-01-10..2024-08-09
validation: 2024-08-12..2025-06-24
independent_test: 2025-06-25..2026-05-07
```

LTR input features 包含：

```text
qlib_score_raw
qlib_rank
qlib_score_percentile_by_date
qlib_score_zscore_by_date
rank_change_1d / 3d / 5d
top10/top30/top50 flags and streak
technical / liquidity / market features
```

这意味着原先旧 qlib + 新 LTR 实际上接近：

```text
qlib train: 2015-05-04..2020-12-31
qlib OOS score used by LTR: 2022-01-10..2025-06-24
LTR train/validation: 2022-01-10..2025-06-24
LTR final test: 2025-06-25..2026-05-07
```

它之所以可能比“fresh qlib + fresh LTR”更合理，是因为 qlib score 对 LTR train 来说更像 OOS score，LTR 有机会学习 qlib 在新市场环境下的错误模式。

### 2.3 S2F 同窗口复核结果

同窗口 `2025-07-01..2026-05-07` 复核显示：

| method | fee_tax_adjusted_net_return | max_drawdown | action_count |
| --- | ---: | ---: | ---: |
| old qlib + new LTR simple | `0.721631` | `-0.050830` | `405` |
| fresh qlib/top50 adaptive | `0.662457` | `-0.088396` | `410` |
| fresh qlib + fresh LTR simple | `0.544381` | `-0.132896` | `408` |
| fresh qlib + fresh LTR turnover | `0.615059` | `-0.111310` | `63` |

共同股票池后：

| method | fee_tax_adjusted_net_return | max_drawdown | action_count |
| --- | ---: | ---: | ---: |
| old qlib + new LTR simple | `0.641235` | `-0.076739` | `405` |
| fresh qlib/top50 adaptive | `0.625943` | `-0.088431` | `410` |
| fresh qlib + fresh LTR simple | `0.544381` | `-0.132896` | `408` |
| fresh qlib + fresh LTR turnover | `0.615059` | `-0.111310` | `63` |

解释：

- 旧 qlib + 新 LTR simple 仍有小幅优势；
- 但优势不是此前看起来的数倍；
- 共同股票池后优势降到约 `+1.53` 个百分点；
- 这提示方向值得研究，但不能直接默认化。

---

## 3. 2020-2021 数据是否缺失，以及能不能直接用于 LTR

当前不是简单地说“2020-2021 没数据”。

已有证据显示：

- qlib provider / normalized price 覆盖从 2015 起存在；
- qlib Option C valid window 是 `2021-01-01..2022-12-31`；
- S1B1 曾生成 qlib walk-forward / WF-VAL score，覆盖 `2021-01-04..2022-12-30`；
- S1 train scored rows 覆盖 `2017-01-03..2020-12-31`。

所以更准确的说法是：

```text
价格和 qlib score 生成能力大概率存在；
但当前 Phase1C LTR 样本从 2022 开始，没有现成 2020-2021 LTR 样本；
如果要把 2020-2021 纳入 LTR train，必须重新构建该区间的 LTR feature/label 样本并做 leakage audit。
```

是否需要“中间隔一年”不是硬规则。

核心要求不是隔一年，而是：

```text
qlib 生成给 LTR 训练用的 score 必须对 LTR train 日期是 OOS / walk-forward；
LTR train 与 final test 必须时间上分离；
validation 只能用于选择，不得反复看 final test。
```

因此要区分 `2020` 和 `2021`：

- `2021`：如果 qlib 基模型只训练到 `2020-12-31`，那么 qlib 对 `2021` 的 score 可以作为 LTR 的 OOS 候选特征，前提是 label horizon 不跨入训练/验证边界；
- `2020`：如果 qlib 基模型训练窗口包含 `2020`，那么该模型对 `2020` 的 score 不是 OOS，不能直接作为 LTR 主训练特征；
- 若确实希望补上 `2020`，必须单独生成 walk-forward / out-of-fold score，例如用更早窗口训练 qlib，再对 `2020` 打分，或者按年份滚动生成 OOS score。

换句话说，`2020-2021` 的价格数据大概率不是问题；真正要补的是“符合 OOS 语义的 qlib score + LTR feature/label 样本”。不建议为了多一年样本，把 2020 的 in-sample qlib score 混进 LTR 训练。

---

## 4. 本主线目标

本支线目标是验证：

```text
时序错开的 qlib OOS score -> LTR meta-reranker
是否比 fresh qlib/top50 adaptive 更适合作为研究默认候选？
```

同时，本支线还要回答一个更基础的问题：

```text
qlib 和 LTR 分别需要多长训练窗口，才算稳定、不过拟合、也不是样本不足？
```

过去的配置大致是：

- qlib 使用约 5-6 年训练窗口；
- LTR 使用约 2-3 年训练窗口。

这个组合有合理直觉：qlib 学较长期的量价模式，LTR 学较近期的 qlib 排序错误和市场状态适配。但它不能只靠直觉确认，必须纳入同一条 OOS stacking 主线做窗口敏感性验证。

它不是：

- 直接把旧 qlib + 新 LTR 默认化；
- 复用可疑的旧高收益结论；
- 新增交易或真实买卖；
- 重开无边界调参；
- 引入新正交数据。

---

## 5. 用户第一性原则

最终产品必须简单、准确、清晰、实用。

因此本主线的输出必须最终回答：

1. 默认看哪个策略；
2. LTR stacking 是否真的有增益；
3. 增益是否来自更好的排序，而不是 universe 或回放口径差异；
4. 小白用户能否用一句话理解该策略。

禁止把研究细节堆到前端。

训练窗口实验也必须服务于用户第一性原则：最后只给出“推荐默认窗口 + 为什么稳定”的结论，不把完整参数矩阵直接展示给普通用户。

---

## 6. 推荐 Phase 设计

粒度保持稍大，不拆太碎。

### Phase T0：数据覆盖与时序合同冻结

目标：

- 审计 `2020-2021` 是否有足够价格、技术特征和 label；
- 区分 `2020` 是否只能通过额外 walk-forward qlib fold 才能进入 LTR train；
- 审计 `2021` 是否可直接作为 frozen qlib 的 OOS score 区间；
- 冻结 stacked pipeline 的时间线；
- 冻结 qlib OOS score 生成政策；
- 冻结 LTR train / validation / final test；
- 冻结有限训练窗口敏感性实验矩阵，避免后续无限调参。

必须回答：

1. 是否已有 `2020-2021` normalized price；
2. 是否已有或可生成 `2020-2021` qlib OOS score/rank，且 `2020` 不得误用 in-sample score；
3. 是否可构建 `2020-2021` LTR feature/label；
4. 是否存在 label horizon 导致 split 边界污染；
5. 是否使用 dynamic universe、static accepted 150，或共同股票池。
6. qlib 训练窗口和 LTR 训练窗口各测试哪些候选，为什么这些候选足够覆盖“太短/适中/太长”三类情况。

建议候选合同：

```text
qlib base train: 2015-05-04..2020-12-31
qlib OOS score for LTR: 2021-01-01..2024-12-31
LTR train: 2021-01-01..2024-06-30
LTR validation: 2024-07-01..2025-06-24
final test: 2025-07-01..2026-05-07
```

可选增强合同：

```text
若 T0 证明 2020 可通过额外 qlib walk-forward fold 生成 OOS score，
则允许把 2020 纳入 LTR train；
否则 2020 只作为 qlib 基模型训练/特征审计资料，不作为 LTR 主训练样本。
```

也可以由执行者基于覆盖审计提出更合理版本，但必须解释。

建议窗口敏感性矩阵保持克制：

```text
qlib train window candidates:
- frozen Option C: 2015-05-04..2020-12-31
- recent 5y: 例如 2017-01-10..2022-12-31 或按 final test 前移
- recent 7-8y / expanding: 作为较长窗口对照

LTR train window candidates:
- 1y OOS score sample
- 2y OOS score sample
- 3y OOS score sample
- 4y OOS score sample
```

执行者不得把矩阵扩成无边界搜索；如果算力或数据不足，优先保留：

```text
qlib: frozen Option C vs recent 5y
LTR: 2y vs 3y
```

T0 必须先冻结这些候选，后续 T1/T2 只能按冻结合同执行。

T0 禁止：

- 不训练；
- 不调参；
- 不跑回放；
- 不改前端/API；
- 不触发 provider / accepted latest / monitor / 交易链路。

### Phase T1：生成 qlib OOS score 与 LTR 样本

目标：

- 按 T0 冻结合同生成 qlib OOS score/rank；
- 构建 LTR feature/label 样本；
- 做 feature leakage / label horizon / score OOS 审计。

要求：

- qlib score 对 LTR train 必须是 OOS 或 walk-forward；
- 不能用 qlib 对自身训练期的 in-sample score 作为 LTR 主训练特征；
- 如果必须降级，必须写明降级语义。

T1 不做默认结论。

### Phase T2：训练 LTR stacking 与同窗口回放

目标：

在同一 final test 上比较主策略，并纳入 T0 冻结的有限窗口敏感性实验：

```text
fresh qlib/top50 adaptive
old/frozen qlib + stacked LTR simple
old/frozen qlib + stacked LTR turnover-controlled
fresh qlib + fresh LTR simple
fresh qlib + fresh LTR turnover-controlled
```

窗口敏感性实验必须区分两层：

- qlib 训练窗口：验证底层 qlib score 是否因训练窗变化更稳定；
- LTR 训练窗口：验证 meta-reranker 是否需要更短的近期纠错窗口，还是更长样本才稳。

不能只选收益最高的单一窗口。必须同时报告：

- 训练集表现；
- validation 表现；
- final test 表现；
- 年度 / regime 分段表现；
- common universe 表现；
- 换手率、费用税费后收益、最大回撤。

必须同时做：

- 全股票池结果；
- 共同股票池结果；
- 持仓贡献审计；
- 异常价格 / 单票贡献审计；
- next-day accounting audit；
- 费用税费审计。

接受标准：

- stacked LTR 至少在共同股票池下有稳定增益；
- 不是只靠某一只股票或某几天贡献；
- 回撤不显著恶化；
- 不能只看收益率；
- 若优势小于 2-3 个百分点，需要慎重，不建议切默认；
- 最优窗口不得只在一个年份或一个 regime 上有效；
- 如果训练集显著优于 validation/final test，必须标记为过拟合风险；
- 如果 LTR 在 train/validation/final test 都无法超过 qlib baseline，必须标记为信息增量不足或样本不足。

### Phase T3：默认候选与只读产品合同

目标：

- 如果 T2 明确支持 stacked LTR，再设计前端只读展示合同；
- 如果不支持，则保留 fresh qlib/top50 adaptive 默认。

前端原则：

- 默认只突出一个策略；
- 下拉保留研究候选；
- 标签清楚：
  - `默认研究候选`
  - `stacking 研究候选`
  - `低动作候选`
  - `规则基线`
- 不输出真实买卖、持有、目标仓位、未来收益、胜率或上涨概率。

---

## 7. 关键审查点

审查者必须重点看：

1. qlib score 对 LTR train 是否 OOS；
2. 2020-2021 样本是否真的可用；
3. LTR label 是否越过 split 边界；
4. 结果是否被 universe 覆盖差异放大；
5. 是否存在单票贡献支配；
6. 是否把小幅优势包装成默认化；
7. 是否仍符合用户第一性原则。
8. 训练窗口实验是否是冻结后的有限矩阵，而不是事后挑最好结果；
9. 是否用 train / validation / final test 的差异判断过拟合或欠拟合；
10. 是否避免把“某个窗口在某一年收益最高”误写成长期默认结论。

---

## 8. 给执行者的一句话

请按 `docs/TW_STOCK_QLIB_OOS_LTR_STACKING_MAINLINE_CN.md` 执行 Phase T0：只做数据覆盖与时序合同冻结，重点审计 2020-2021 是否具备 normalized price、qlib OOS score/rank 生成能力、LTR feature/label 构建能力，并明确 qlib train、qlib OOS score window、LTR train/validation/final test 的时序错开合同，同时冻结 qlib/LTR 训练窗口敏感性实验的有限候选矩阵；不得训练、不得调参、不得回放、不得改前端/API、不得触发 provider/accepted latest/monitor/交易链路；完成后提交 `docs/tw_qlib_oos_ltr_stacking/PHASET0_EXECUTION_REPORT_CN.md` 等待审查。

## 9. 给审查者的一句话

请按 `docs/TW_STOCK_QLIB_OOS_LTR_STACKING_MAINLINE_CN.md` 审查执行者的 Phase T0 报告，重点确认 2020-2021 数据覆盖、qlib score 对 LTR train 的 OOS 语义、LTR feature/label 可构建性、split 边界、训练窗口敏感性矩阵和禁止事项是否冻结清楚；若通过，再撰写 Phase T1 工作文档，否则指出必须修复项或停止。
