# Fresh Qlib 训练窗口敏感性后续支线

生成日期：2026-06-15

## 1. 文档定位

本文档是后续支线，不立即执行。

触发条件：

```text
先完成 docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/
Frozen Fresh Qlib + Orthogonal LTR Clean Stacking 主线。
```

该主线收尾后，再决定是否执行本支线。

## 2. 核心问题

当前 fresh qlib baseline 使用较长训练窗口：

```text
2017-01-10..2024-12-31
```

问题是：

```text
更长历史是否一定更好？
较早年份的市场结构和趋势是否会降低近期适配能力？
2020-2024 或 2021-2024 这种较短窗口是否更适合当前台股？
```

本支线只验证：

```text
fresh qlib 训练窗口长度是否影响当前默认 Top50 adaptive 策略表现。
```

## 3. 为什么不能混进 clean stacking 主线

Clean stacking 主线验证的是：

```text
固定 fresh qlib 后，orthogonal LTR 是否有增益。
```

本支线验证的是：

```text
fresh qlib 自己的训练窗口应该多长。
```

两者是不同变量。

如果混在一起，会无法判断结果来自：

- qlib 训练窗口变化；
- orthogonal LTR；
- 正交数据；
- 或回放口径变化。

因此本支线必须后置执行。

## 4. 控制变量原则

唯一允许变化：

```text
fresh qlib train_start。
```

必须保持不变：

- provider；
- universe / post-score filter；
- qlib model family；
- qlib model params；
- label；
- validation/test；
- replay engine；
- Top50 adaptive strategy；
- fee/tax；
- target_position_count；
- next-day execution；
- 不使用正交数据；
- 不训练 LTR；
- 不改前端/API/provider/accepted latest/monitor/交易链路。

## 5. 候选训练窗口

建议第一轮只测 4 个窗口：

```text
W2017: train 2017-01-10..2024-12-31
W2020: train 2020-01-01..2024-12-31
W2021: train 2021-01-01..2024-12-31
W2022: train 2022-01-01..2024-12-31
```

Control：

```text
W2017 = 当前 fresh qlib baseline
```

不建议第一轮测试太多窗口，避免参数搜索化。

## 6. 固定评测口径

Validation：

```text
2025-01-01..2025-06-30
```

Untouched Test：

```text
2025-07-01..2026-05-07
```

必须单独报告：

```text
2025H2
2026YTD
rolling 6m
market regime segments
```

策略：

```text
fresh_qlib_top50_adaptive_baseline
```

回放：

```text
next-day execution
fee_rate = 0.001425
tax_rate = 0.003
target_position_count = 10
candidate_k = 50
```

## 7. 阶段设计

### Phase W0：合同冻结

目标：

```text
冻结训练窗口敏感性实验的 control、candidate windows 和回放口径。
```

执行内容：

- 读取当前 S2B fresh qlib control；
- 确认 W2017 指标可复现；
- 冻结 W2020/W2021/W2022；
- 冻结 qlib model params；
- 冻结 provider / universe / label / validation / test；
- 输出训练资源预算和线程阶梯；
- 不训练模型。

输出：

```text
docs/tw_fresh_qlib_training_window_sensitivity/PHASEW0_CONTRACT_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_w0_training_window_contract_frozen
```

### Phase W1：多窗口 Fresh Qlib 训练

目标：

```text
训练 W2020 / W2021 / W2022 三个 qlib 模型，并复用 W2017 作为 control。
```

执行内容：

- 每个窗口使用相同 provider；
- 每个窗口使用相同 model params；
- 每个窗口只改变 train_start；
- 输出 raw score rank；
- 输出 post-filter score rank；
- 输出 coverage audit；
- 输出 leakage audit；
- 输出 resource audit；
- 不训练 LTR；
- 不使用正交特征。

输出：

```text
docs/tw_fresh_qlib_training_window_sensitivity/PHASEW1_MULTI_WINDOW_TRAINING_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_w1_multi_window_fresh_qlib_training_completed
```

停止条件：

- 必须改模型参数才能跑通；
- 必须缩小 universe；
- 某窗口 coverage 明显不完整；
- 发现 leakage 风险；
- 资源无法完成。

### Phase W2：同口径回放

目标：

```text
比较不同训练窗口下的 fresh qlib Top50 adaptive 表现。
```

必须比较：

```text
W2017
W2020
W2021
W2022
```

输出指标：

- validation net return；
- untouched test net return；
- max drawdown；
- action_count；
- turnover_proxy；
- fee_and_tax；
- rolling 6m；
- 2025H2；
- 2026YTD；
- market regime；
- coverage；
- next-day accounting；
- PnL concentration。

输出：

```text
docs/tw_fresh_qlib_training_window_sensitivity/PHASEW2_REPLAY_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_w2_training_window_replay_completed
```

### Phase W3：审查与决策

目标：

```text
判断是否有必要把 fresh qlib 基座从 W2017 改为较短窗口。
```

推荐判断规则：

- 如果 W2020/W2021/W2022 在 validation 和 test 都明显优于 W2017，才考虑升级；
- 如果只在 test 优于、validation 不优于，不能直接切换；
- 如果收益更高但回撤/换手明显恶化，必须列为用户取舍；
- 如果短窗口只靠少数股票或少数月份贡献，不支持默认化；
- 如果没有稳定优势，继续保留 W2017。

输出：

```text
docs/tw_fresh_qlib_training_window_sensitivity/PHASEW3_REVIEW_AND_DECISION_CN.md
```

可能 gate：

```text
fresh_qlib_window_keep_w2017
fresh_qlib_window_shorter_candidate_supported_for_followup
fresh_qlib_window_inconclusive
fresh_qlib_window_blocked_by_data_or_leakage
```

## 8. 禁止事项

本支线严禁：

```text
加入正交数据
训练 LTR
调 qlib 参数
新增策略规则
新增 filter / market gate / turnover rule
改 validation/test
用 test 选择窗口后直接默认化
改前端/API
provider refresh / publish
accepted latest switching
monitor scan / config / alerts
broker / orders / quick-trade
target position / target weight
真实买卖建议
收益、胜率、上涨概率承诺
```

## 9. 用户第一性原则

本支线最终只回答用户能理解的问题：

```text
fresh qlib 用较新的训练窗口，会不会更适合当前台股？
```

如果结果不稳定，就保持当前默认，不为了“看起来更新”而切换。

如果结果稳定优于当前默认，也必须先进入只读产品合同，不直接改前端默认或日更自动化。

## 10. 给执行者的一句话

```text
请在 Frozen Fresh Qlib + Orthogonal LTR Clean Stacking 主线收尾后，再按 docs/tw_fresh_qlib_training_window_sensitivity/FRESH_QLIB_TRAINING_WINDOW_SENSITIVITY_FUTURE_MAINLINE_CN.md 执行 Phase W0，只冻结 fresh qlib 训练窗口敏感性实验合同，候选窗口为 W2017/W2020/W2021/W2022，唯一变量是 train_start，不得训练、调参、加入正交数据、训练 LTR、改前端/API/provider/accepted latest/monitor 或触发交易链路。
```

## 11. 给审查者的一句话

```text
请在 Frozen Fresh Qlib + Orthogonal LTR Clean Stacking 主线收尾后，再按 docs/tw_fresh_qlib_training_window_sensitivity/FRESH_QLIB_TRAINING_WINDOW_SENSITIVITY_FUTURE_MAINLINE_CN.md 审查执行者 Phase W0 报告，重点确认唯一变量是否只是 fresh qlib train_start、validation/test/replay/model/universe 是否冻结、是否排除了正交数据和 LTR，并判断是否允许进入 Phase W1。
```
