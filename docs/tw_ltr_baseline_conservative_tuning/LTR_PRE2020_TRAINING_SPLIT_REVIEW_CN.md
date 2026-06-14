# LTR 与 Qlib 训练切分公平性审查说明

生成时间：2026-06-14

## 1. 用户问题

如果 qlib 是用 2020 年前的数据训练的，那么 LTR 是否也应该用 2020 年前的数据训练，再评估 2020 年后的数据，这样是否才更真实？

## 2. 审查判断

用户判断方向正确。

如果 qlib 的模型训练截止在 2020 年前，而当前 LTR 的训练区间是：

```text
train: 2022-01-10..2024-08-09
validation: 2024-08-12..2025-06-24
independent_test: 2025-06-25..2026-05-07
```

那么两者不是同一个严格度的样本外比较。

在这种情况下，LTR 使用了 2022-2024 的市场结构和股票行为训练，而 qlib 如果确实只用 2020 年前训练，则 qlib 面对 2020 年后是更长跨度的 out-of-sample。直接比较会偏向 LTR。

## 3. 当前 B2/B2A 结论应该如何降级理解

当前 B2A 接受范围只能理解为：

```text
在现有 Phase1C LTR 训练切分下，LTR simple 在固定候选的 independent_test 区间表现较强，适合作为只读展示默认策略。
```

不能理解为：

```text
LTR simple 已经在与 qlib 同等训练截止条件下证明优于 qlib。
```

也不能理解为：

```text
LTR simple 对 2020 年后全区间都有严格样本外优势。
```

## 4. 更公平的验证方式

如果要严格比较 qlib 与 LTR，应至少做以下一种：

### 4.1 同训练截止比较

如果 qlib 训练截止为 2020 年前，则 LTR 也应使用同样或更早的训练截止：

```text
LTR train <= 2019-12-31
LTR validation 可在 2020 前或单独冻结
LTR test = 2020-01-01 之后
```

然后只用 2020 年后的数据做最终评估。

### 4.2 Walk-forward 比较

更稳妥的是做 walk-forward：

```text
train: 截止 T
validation: T 后一段
test: validation 后一段
滚动多轮
```

这样可以避免只用一个切点得出偶然结论。

### 4.3 最终 untouched holdout

需要保留一个从未用于：

- 训练；
- 选特征；
- 选参数；
- 选默认策略；
- 写产品文案；

的最终 holdout，作为真正验收。

## 5. 后续若开启新主线的建议

建议新开一条严格验证主线，例如：

```text
TW_STOCK_LTR_PRE2020_OOS_FAIR_COMPARISON_MAINLINE_CN.md
```

目标只做：

- 核实 qlib 实际训练区间；
- 检查 LTR 是否有 2020 年前足够特征和 label 数据；
- 若数据足够，训练 pre-2020 LTR；
- 统一 qlib / LTR 的交易口径、费用税费、样本池和执行价格；
- 只用 2020 年后做 OOS 比较；
- 不接前端、不改默认、不接交易。

## 6. 安全边界

该问题只涉及研究验证设计，不允许直接触发：

- provider refresh / publish；
- accepted latest switching；
- monitor 写入；
- broker / quick-trade / orders；
- target position / target weight；
- 买卖、持有、仓位建议；
- 收益承诺、胜率或上涨概率。

## 7. 最终结论

如果 qlib 确实是 2020 年前训练，而 LTR 是 2022-2024 训练，那么当前比较不能说是完全公平的长期 OOS 比较。

当前 LTR simple 的产品展示可以保留为 split-aware 只读历史模拟，但若要证明它比 qlib 更真实、更稳健，应该重新做同训练截止或 walk-forward 的严格 OOS 验证。
