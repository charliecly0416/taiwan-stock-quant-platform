# Phase B2A Split Purity 修复工作文档

生成时间：2026-06-14

背景：用户指出 B2 默认策略选择使用了 train / validation / full range 的回测结果，可能导致 LTR simple 数值偏高，不能作为真实泛化能力依据。审查者确认该担忧成立，需要执行者修复 split 解释与产品默认结论边界。

---

## 1. 审查者判断

用户判断基本正确。

训练集和验证集可以用于历史复盘展示，但不能用于证明策略未来泛化能力，也不能把 full range 的高收益包装成“默认策略更优”的核心证据。

当前 B2 结论存在风险：

```text
把包含 train / validation / independent_test 的 common full range 结果，过度用于支撑 LTR simple 默认展示。
```

这需要修复。

---

## 2. 必须区分三类用途

### 2.1 允许展示

允许展示 train / validation / full range，但只能写成：

```text
历史回放复盘
样本内/验证/混合区间结果
不代表样本外泛化
不代表未来收益
```

### 2.2 允许辅助判断

validation 可以用于观察候选行为，但不能当成最终证明。

### 2.3 默认决策必须主要看 OOS

默认策略是否合理，必须至少单独列出：

```text
phase1c_independent_test_range = 2025-06-25..2026-05-07
```

如果要更严谨，还应明确：一旦使用 independent_test 参与默认选择，它就不再是完全未触碰的最终检验集，只能叫“已用于产品决策的独立测试结果”，不能继续作为未来泛化保证。

---

## 3. 当前事实

当前 B1 数据中：

- common full range 包含 train、validation、independent_test；
- 2022 / 2023 是 train；
- 2024 是 train / validation mixed；
- 2025 是 validation / independent_test mixed；
- 2026_ytd 当前产物区间到 `2026-06-13`，不等同于原冻结 independent_test，因为原 independent_test 截止 `2026-05-07`；
- independent_test 单独看，LTR simple 仍优于 Top50 adaptive：

| 策略 | independent_test return | max_drawdown | action_count |
| --- | ---: | ---: | ---: |
| `phase1c_ltr_simple_daily` | `3.550601` | `-0.160298` | `384` |
| `rank_rotate_top50_adaptive_score` | `2.450848` | `-0.167457` | `386` |
| `phase1c_ltr_conservative_top30_2day_confirm_daily` | `1.257516` | `-0.098271` | `63` |
| `phase1c_ltr_conservative_top20_entry_2day_exit_daily` | `0.650070` | `-0.143129` | `63` |

这说明 LTR simple 的 OOS 证据不是空的，但仍不能把 full range 说成 OOS，也不能做未来收益承诺。

---

## 4. Phase B2A 唯一目标

只做 split purity 修复，不做新调参、不改策略、不新增候选。

执行者必须提交：

```text
docs/tw_ltr_baseline_conservative_tuning/PHASEB2A_SPLIT_PURITY_REPAIR_EXECUTION_REPORT_CN.md
```

---

## 5. Phase B2A 必须修复的内容

### 5.1 修正文档结论

修正以下文档中的表述：

- `PHASEB2_USER_FIRST_PRODUCT_CLOSURE_EXECUTION_REPORT_CN.md`
- 如有必要，补充 `PHASEB2_REVIEW_AND_CLOSURE_CN.md` 的 caveat，但不得篡改历史审查过程。

必须明确：

```text
LTR simple 默认展示不是因为 full range 可以证明未来更好，
而是因为在固定候选同口径历史回放中 full range 和 independent_test 均较强；
其中 full range 只能作为历史复盘，independent_test 才是样本外支持。
```

### 5.2 修正产品文案

若前端/API payload 有“历史回放收益最高”这类表述，必须确保旁边有：

```text
历史模拟，不代表未来收益；包含样本内/验证/样本外混合结果，详情见切片。
```

更推荐首屏文案改为：

```text
历史回放表现较强，动作较多
```

而不是单独突出：

```text
历史回放收益最高
```

如果保留“历史回放收益最高”，必须限定：

```text
在当前固定候选历史回放中
```

### 5.3 修正默认决策解释

默认决策必须分成两层：

1. 样本外证据：independent_test 中 LTR simple 优于 Top50 adaptive；
2. 产品决策：因为用户偏好收益优先，所以默认展示 LTR simple，但保留 Top50 adaptive 作为规则型参考。

不得使用 train / validation / full range 作为唯一默认理由。

---

## 6. 禁止事项

本轮禁止：

- 新回放；
- 新调参；
- 新候选；
- 重训 LTR；
- 改 Phase1C score；
- 改 replay 口径；
- 新数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 输出买卖、持有、仓位建议；
- 输出收益承诺、胜率或上涨概率；
- 把 train / validation / full range 说成 OOS。

---

## 7. 验收要求

Phase B2A 执行报告必须包含：

1. split 定义；
2. 每个 period 属于 train / validation / independent_test / mixed 的说明；
3. 四个策略在 independent_test 上的单独比较；
4. 对 common full range 的降权说明；
5. 修正后的默认展示理由；
6. 是否修改前端/API payload 文案；
7. 如改前端/API，必须重新跑静态扫描和只读 E2E/network audit；
8. gate 建议。

---

## 8. Gate

如果修复后能清楚区分 train / validation / independent_test，并避免把 full range 当作 OOS：

```text
phaseb2a_split_purity_repaired_return_to_closure
```

如果执行者仍把 train / validation / full range 包装为泛化证据：

```text
stop_and_discuss_with_user
```
