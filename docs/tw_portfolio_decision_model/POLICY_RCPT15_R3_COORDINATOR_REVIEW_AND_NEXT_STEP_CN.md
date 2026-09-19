---
created_at: 2026-06-26
status: coordinator_review
phase: RCPT15_R3_ISOLATED_RERANK_AND_DAILY_STRICT_E4_AUTO_CHAIN
verdict: STOP_R3_RERANK_NEEDS_FULL_YZ2_FEATURE_PACKAGE_REPAIR
---

# RCPT15_R3 统筹审查与下一步意见

## 1. 结论

本轮进入 `RCPT15_R3_ISOLATED_RERANK` 是正确的，但 R3 不能通过：

```text
STOP_RERANK_REQUIRED_FEATURES_NOT_AVAILABLE_IN_R1_R2
```

这不是 LTR 模型不可用，也不是 R2 institutional/margin 补源失败。实际情况是：

1. O4 LTR 模型可加载；
2. R2 O2 institutional_flow / margin_short 已覆盖到 `2026-06-25`；
3. `2026-06-19` 已正确分类为 no-signal / holiday-like input，不算 O2 失败；
4. 但 O4 训练白名单需要 78 个特征，其中 22 个技术/价格/大盘控制特征不在 R1/R2 授权输入内；
5. 执行者没有用填零、qlib score 或替代分数伪造 rerank，符合合同。

因此本轮应判定为：

```text
R3 isolated rerank STOP 合理
需要开 R3_R 完整 YZ2 feature package repair
```

## 2. 缺的是什么

缺口不是普通日线本身，也不是 FinMind institutional/margin，而是 O4 LTR 训练时使用的完整 feature vector 中的控制特征：

```text
MA5
MA10
MA20
MA60
RSI14
MACD
Bollinger_position
ret20
volatility20
volume_ratio20
avg_trading_value_20d
volume_stability20
missing_rate20
suspension_proxy
slippage_proxy
TWII_ret20
TWII_ret60
TWII_close_vs_MA60
TWII_close_vs_MA120
market_volatility20
market_drawdown60
market_breadth20
```

这些特征在正式 `scripts/build_phase_yz2_orthogonal_package.py` 中已有计算逻辑，但 RCPT15_R3 当前只被授权读取 R1 shadow signal/top50 与 R2 isolated O2，所以不能擅自读取价格目录计算这些控制特征。

## 3. Daily auto 修复结论

本轮已同步修复 daily auto 的关键生产化缺口：

1. 新增显式 gate：

```text
--enable-strict-e4-readonly-chain
TW_DAILY_AUTO_ENABLE_STRICT_E4_READONLY_CHAIN=false by default
```

2. 启用 strict E4 gate 时，FinMind daily scope 不再允许跳过：

```text
--no-institutional
--no-margin
```

3. strict E4 chain 只在 YZ1 `model_a/manifest.json` 已存在时推进 YZ2 / YZ2R；缺 model_a 时阻塞，不合成 qlib base signal。

4. legacy provider publish / qlib accepted latest 仍只在非默认 `--enable-legacy-provider-publish` gate 下进入。

5. YZ2R 已移除硬编码 `2026-06-18`，改为从交易日历取 `signal_asof` 后的下一交易日。

## 4. 下一步授权建议

授权下一步：

```text
RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR
```

目标：

1. 在隔离目录中复用正式 YZ2 feature builder 的逻辑；
2. 输入仍固定为 R1 shadow top50 + R2 isolated O2 + local readonly price/calendar source；
3. 计算完整 78-feature O4 whitelist；
4. 重新运行 frozen O4 LTR model predict；
5. 产出 isolated rerank score snapshot / top30 / top50；
6. 不写 formal latest pointer，不切 provider/qlib accepted latest，不发布 production/default/order/broker/target。

建议输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_r_full_yz2_feature_package_repair/
```

## 5. 执行者要求

执行者必须：

1. 读取本文件、R3 work doc、R3 execution report、R2 review；
2. 不修改 R1/R2 既有 artifact；
3. 不使用缺失特征填零作为通过条件；
4. 明确记录每个特征来源、available_at、PIT audit；
5. 若读取 local price/calendar，必须写入 source trace，并声明不触发 provider refresh/publish；
6. 成功后 rerank 输出必须 row_count 与 eligible R1 top50 day 数匹配；
7. 失败时继续 STOP，不得伪造 LTR score。

## 6. 审查者重点

审查者必须确认：

1. 是否完整覆盖 O4 whitelist 78 个特征；
2. 是否没有 future label / realized return / execution price / order / target 字段；
3. 技术指标与大盘指标是否只使用 `date <= signal_asof` 的本地数据；
4. O2 institutional/margin 是否使用 `available_at <= signal_asof`；
5. `2026-06-19` 是否仍被排除为 no-signal input；
6. rerank 结果是否来自 frozen O4 model，而不是 qlib score fallback；
7. daily auto strict E4 gate 是否保持默认关闭。
