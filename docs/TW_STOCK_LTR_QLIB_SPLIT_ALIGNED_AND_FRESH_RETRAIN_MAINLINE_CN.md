# Qlib / LTR 训练窗口对齐验证与新鲜模型重训主线文档

生成日期：2026-06-14

## 1. 背景

当前审查已经确认：

- qlib Option C frozen baseline 的训练窗口为 `2015-05-04..2020-12-31`；
- qlib validation 为 `2021-01-01..2022-12-31`；
- qlib test / research backtest 为 `2023-01-01..2025-06-30`；
- 当前 LTR Phase1C 的训练窗口为 `2022-01-10..2024-08-09`；
- 当前 LTR independent_test 为 `2025-06-25..2026-05-07`。

这说明当前 LTR 与 qlib 并不是同一个训练假设。LTR 的训练数据更新，因此它在 2025/2026 的表现不能直接证明 LTR 方法本身比 qlib baseline 更强。

但真实使用时，用户当然希望模型使用尽可能新的数据。因此本主线必须分清两个问题：

```text
问题 A：公平验证
在同样旧训练窗口下，LTR 方法是否真的优于 qlib / Top50 baseline？

问题 B：真实使用
如果方法有效，qlib 与 LTR 是否都应该用更新窗口重训，再用于当前策略展示？
```

本主线的核心原则：

```text
先旧窗口对齐验证方法是否有增益
-> 再新窗口重训验证当前可用性
-> 最后才决定默认基线和前端展示
```

---

## 2. 用户第一性原则

本主线必须服务投资小白用户，而不是堆实验。

### 2.1 简单

- 最终前端只展示少数清楚策略；
- 不把 train / valid / test 细节直接丢给普通用户；
- 用户只需要知道默认看哪个、其他策略适合什么场景。

### 2.2 准确

- 研究报告必须清楚区分：
  - 旧窗口公平验证；
  - 新窗口真实使用验证；
  - 样本内；
  - 验证集；
  - 测试集；
  - mixed historical replay。
- 不允许把旧窗口结果包装成当前上线效果；
- 不允许把新窗口回测包装成未来保证。

### 2.3 清晰

- 每个阶段都必须回答一个明确问题；
- 每个策略必须有一句人能看懂的说明；
- 默认基线结论必须说明为什么，不只看收益率。

### 2.4 实用

- 目标是帮助决定真实产品应默认使用哪个策略；
- 若 LTR 方法有效，应进入新鲜模型重训验证；
- 若 LTR 方法无效，不继续为它调参找理由。

---

## 3. 本主线不是做什么

本主线不是：

- 直接把当前 LTR simple 升为最终默认；
- 直接用新数据重训后上线；
- 继续无限调参；
- 新增法人筹码、融资融券、月营收等正交数据；
- 改 provider 自动刷新链路；
- 改 accepted latest；
- 写 monitor；
- 接 broker / orders / quick-trade；
- 输出真实买卖、持有、仓位、target position、target weight；
- 输出收益承诺、胜率或上涨概率。

本主线是研究验证 + 只读产品决策主线。

---

## 4. 总体路线

本主线分为 4 个较大的 Phase。

```text
Phase S0：证据冻结与实验合同
Phase S1：旧窗口 split-aligned 公平验证
Phase S2：新鲜窗口 qlib + LTR 重训验证
Phase S3：默认基线与前端只读展示收口
```

每个 Phase 都必须执行者先做，审查者后审。审查者通过后才进入下一 Phase。

---

## 5. Phase S0：证据冻结与实验合同

### 5.1 目标

冻结本主线所有关键口径，避免后续边做边改。

### 5.2 执行者必须完成

1. 核实 qlib Option C frozen baseline：
   - recorder id；
   - config 路径；
   - model 路径；
   - train / valid / test split；
   - universe；
   - label / handler / feature 配置。

2. 核实当前 LTR Phase1C：
   - score 文件；
   - train / validation / independent_test split；
   - feature 列；
   - label 构造；
   - 是否用 qlib score / rank 作为输入；
   - 是否存在 forbidden future features。

3. 冻结两个实验：
   - S1：旧窗口对齐验证；
   - S2：新窗口重训验证。

4. 冻结比较策略：
   - qlib / Top50 adaptive；
   - rank_rotate_top50；
   - rank_rotate_top30；
   - confirmed_exit；
   - LTR simple；
   - LTR conservative / turnover controlled；
   - 如有必要，少量已存在保守规则变体。

5. 冻结指标：
   - `fee_tax_adjusted_net_return`
   - `max_drawdown`
   - `action_count`
   - `buy_count`
   - `sell_count`
   - `fee_and_tax`
   - `turnover_proxy_by_notional_over_avg_equity`
   - `relative_return_vs_top50_adaptive`
   - `relative_drawdown_vs_top50_adaptive`
   - `relative_actions_vs_top50_adaptive`

### 5.3 S0 禁止事项

- 不训练；
- 不调参；
- 不改前端；
- 不改 API；
- 不跑 provider refresh / publish；
- 不改 accepted latest；
- 不碰交易链路。

### 5.4 S0 交付物

建议输出：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES0_EXECUTION_REPORT_CN.md
```

审查者通过后，撰写 S1 工作文档。

---

## 6. Phase S1：旧窗口 split-aligned 公平验证

### 6.1 目标

回答：

```text
在 qlib 同样的旧训练窗口下，LTR 方法本身是否仍然比 qlib / Top50 baseline 更好？
```

这一步不是为了上线，而是为了判断 LTR 方法是否真的有信息增益。

### 6.2 推荐 split

优先使用与 qlib Option C 对齐的 split：

```text
train: 2015-05-04..2020-12-31
validation: 2021-01-01..2022-12-31
test: 2023-01-01..2025-06-30
```

如果 LTR 特征、label 或 qlib score/rank 在早期数据不足，执行者必须报告：

- 哪些日期缺数据；
- 哪些字段缺数据；
- 缺口是否影响可训练性；
- 是否需要缩短为可解释的最早共同窗口。

不得静默缩短。

### 6.3 训练与选择规则

- 可以重新训练 LTR，但只限 S1 split-aligned 实验；
- 模型选择只能使用 train / validation；
- test 只能最终评估；
- 不得在 test 上反向调参；
- 若需要轻量参数搜索，参数表必须在训练前冻结。

### 6.4 必须比较

同口径比较：

- qlib / Top50 adaptive；
- LTR split-aligned simple；
- LTR split-aligned conservative；
- 原有 rank 策略 baseline。

必须按以下维度输出：

- full test：`2023-01-01..2025-06-30`；
- 分年：2023、2024、2025 H1；
- rolling 6m / 12m；
- bear / normal / bull 或现有等价 regime。

### 6.5 S1 结论 gate

审查者只能给以下结论之一：

```text
split_aligned_ltr_method_supported
split_aligned_ltr_method_not_supported
split_aligned_data_insufficient
```

若 S1 不支持 LTR 方法，不进入 S2 新鲜 LTR 重训上线讨论；可以只保留 qlib / Top50 adaptive 默认基线。

---

## 7. Phase S2：新鲜窗口 qlib + LTR 重训验证

### 7.1 进入条件

只有 S1 证明 LTR 方法在旧窗口公平验证下有明确增益，才进入 S2。

如果 S1 未通过，但用户仍要求继续，必须新写用户确认文档，不能自动推进。

### 7.2 目标

回答：

```text
在真实使用场景下，qlib 和 LTR 都用较新的训练窗口时，哪个策略更适合当前默认展示？
```

### 7.3 推荐 split

具体日期由 S0/S1 后的数据新鲜度决定，但原则是：

```text
train: 尽可能覆盖到较近但不触碰最终测试期
validation: train 之后一段
test: validation 之后的 untouched 区间
```

示例：

```text
train: 2015-05-04..2024-12-31
validation: 2025-01-01..2025-06-30
test: 2025-07-01..latest available
```

如果 2026 数据不足，可调整，但必须保持：

- train 不包含 test；
- validation 用于选择参数；
- test 不用于调参；
- test 不用于反复试错。

### 7.4 qlib 与 LTR 都要新鲜

S2 的关键不是只重训 LTR，而是：

- qlib baseline 也应使用同样新鲜原则重训；
- LTR 在新 qlib score/rank 基础上训练或重排；
- 两者最终在同一个 test 上比较。

否则又会变成不公平比较。

### 7.5 S2 禁止事项

- 不得把 S2 test 反复用于调参；
- 不得把 S2 结果直接变成交易建议；
- 不得自动改线上 provider 或 accepted latest；
- 不得影响当前已可用前端，除非进入 S3。

### 7.6 S2 gate

审查者只能给以下结论之一：

```text
fresh_retrain_ltr_default_candidate_supported
fresh_retrain_qlib_or_top50_default_supported
fresh_retrain_inconclusive
fresh_retrain_data_or_leakage_blocked
```

---

## 8. Phase S3：默认基线与前端只读展示收口

### 8.1 目标

把 S1/S2 结论转成用户能理解的产品展示。

### 8.2 前端原则

前端应该保留多策略参考，但不能复杂：

- 一个默认选中策略；
- 一个下拉框切换其他较好策略；
- 每个策略一个标签；
- 每个策略一句说明；
- 指标只展示少数核心项；
- 详情里再放回测区间和 caveat。

### 8.3 标签建议

标签必须来自真实表现，不得营销化。

可用标签：

- `默认`
- `稳健`
- `激进`
- `低回撤`
- `低动作`
- `高换手`
- `研究候选`

### 8.4 文案边界

允许：

```text
历史模拟中表现较强
当前默认展示策略
动作较多
回撤较低
用于研究复盘
```

禁止：

```text
建议买入
建议卖出
未来收益最高
胜率更高
上涨概率更高
目标仓位
目标权重
```

### 8.5 S3 验收

必须通过：

- 后端 GET-only 测试；
- 前端静态检查；
- readonly E2E；
- network audit；
- safety boundary scan；
- 文案安全审查。

---

## 9. 后续路线判断

### 9.1 如果 S1 失败

说明 LTR 方法在公平旧窗口下没有稳定增益。

建议：

- 暂不继续 LTR 默认化；
- 保留 qlib / Top50 adaptive 默认基线；
- 把 LTR 作为研究候选或关闭产品默认展示升级。

### 9.2 如果 S1 通过但 S2 失败

说明 LTR 方法历史上可能有效，但新鲜重训后当前可用性不足。

建议：

- 不上线 LTR 默认；
- 保留 S1 作为研究证据；
- 后续再考虑正交数据或 walk-forward 训练。

### 9.3 如果 S1 与 S2 都通过

说明 LTR 方法和当前新鲜训练都成立。

建议：

- 可以考虑把 LTR 作为默认只读展示策略；
- Top50 adaptive 保留为规则型稳健参考；
- 不进入自动交易。

---

## 10. 执行者与审查者协作规则

执行者每个 Phase 完成后必须停止，提交报告。

审查者必须：

- 先审查报告；
- 给 findings；
- 明确通过 / 不通过；
- 若通过，再写下一 Phase 工作文档；
- 若发现未知问题或需要用户选择，必须停下来问用户。

执行者不得自行跳 Phase。

审查者不得擅自新增主线外内容。

---

## 11. 给执行者的一句话

请按 `docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md` 执行 Phase S0：只做 qlib Option C 与当前 LTR 的训练窗口、feature、label、universe、score 产物和比较口径证据冻结，并冻结 S1/S2 实验合同；不得训练、不得调参、不得改前端/API、不得触发 provider/accepted latest/monitor/交易链路；执行完提交 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES0_EXECUTION_REPORT_CN.md`，等待审查。

## 12. 给审查者的一句话

请按 `docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md` 审查执行者的 Phase S0 报告，重点确认 qlib 与 LTR 训练窗口证据、feature/label/universe、S1 旧窗口公平验证合同、S2 新鲜重训合同和禁止事项是否冻结清楚；若通过，再撰写 Phase S1 旧窗口 split-aligned 公平验证工作文档，否则指出必须修复项并停止。
