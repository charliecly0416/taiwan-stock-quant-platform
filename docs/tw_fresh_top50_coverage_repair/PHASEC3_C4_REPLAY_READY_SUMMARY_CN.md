# Phase C3/C4 Replay-Ready 合同总结

生成日期：2026-06-15

## 1. 做了什么

C3/C4 不是收益比较，也不是策略默认化判断。

这一阶段只检查：

```text
repaired fresh top50 的候选股票是否 as-of 合法、是否可 next-day replay。
```

重点是排除：

- 未来股票倒灌；
- instrument 有效期违规；
- accepted universe 违规；
- 有 score 但没有当前价格；
- 有 score 但没有下一交易日执行价格；
- 有 score 但没有 adaptive score 所需字段。

## 2. C3 发现的问题

C3 确认：

```text
total repaired rows: 30750
eligible rows: 30750
future / instrument range violation: 0
accepted universe violation: 0
```

说明没有发现未来股票倒灌，也没有 instrument 有效期违规。

但 C3 发现 replay-ready 不完整：

```text
replay-ready rows: 30630 / 30750
missing current price rows: 100
missing next execution price rows: 100
missing adaptive score rows: 120
missing ret20 rows: 120
missing volatility20 rows: 120
```

因此 C3 不允许直接进入前端展示合同。

## 3. C4 怎么处理

C4 定位后发现缺口主要来自两只股票：

```text
TW7769
TW6919
```

原因：

| root_cause | rows | action |
| --- | ---: | --- |
| TW7769 本地价格尚未开始 | 95 | 排除到价格开始后 |
| TW7769 ret20 / volatility20 warmup 不足 | 20 | 排除到特征 warmup 完成后 |
| TW6919 早期价格/calendar join 不满足 replay-ready | 5 | 排除 |

C4 没有强行补值，也没有联网抓数据、refresh provider 或重训模型，而是把不可 replay-ready 的行从候选中剔除。

修复后：

```text
missing current price: 0
missing next execution price: 0
missing adaptive score: 0
future / instrument range violation: 0
accepted universe violation: 0
```

## 4. 为什么不补满 150

不补满是合理的。

原因是 S2B raw score artifact 在目标窗口每天本来就只有 150 行：

```text
rank > 150 的同日候补股票数量: 0
```

如果某天 raw top150 里有 1-2 行不可 replay-ready，就没有合法的本地候补可以 top-up。

要强行补满 150，就必须：

- 重新生成更宽的 qlib score universe；
- 或引入新的 source artifact；
- 或改 universe / score 合同。

这些都超出了 C4 范围，也不应该静默做。

因此当前正确做法是：

```text
保留 replay-ready clean 的 148/149/150 覆盖；
不要为了凑满 150 引入新风险。
```

## 5. 当前最终状态

C4 后 repaired fresh top50 状态：

```text
rows: 30630
daily coverage: 148 / 149 / 150
replay-ready: clean
future leakage: 0
instrument violation: 0
accepted universe violation: 0
price missing: 0
next execution price missing: 0
adaptive score missing: 0
```

推荐 gate：

```text
phase_c4_replay_ready_repair_passed_with_coverage_below_150_explained
```

## 6. 怎么理解这个结果

这说明 repaired fresh top50 已经不是“裸覆盖 150 行”，而是更严格的：

```text
每一行都必须可 as-of 解释、可 next-day replay。
```

早期少数日期只有 148 或 149 支，不是错误，而是因为原 raw score 里包含了当时还不能完整 replay 的股票，且没有合法候补。

## 7. 后续建议

当前可以收尾这条 replay-ready 合同修复线。

后续如果只是研究展示，可以使用：

```text
repaired fresh top50 replay-ready clean artifact
```

但需要在说明中标注：

```text
目标窗口覆盖为 148 / 149 / 150，不是强行每日 150。
```

如果未来一定要求每日 150，则需要另开新合同：

```text
更宽 qlib raw score universe + 合法 top-up 机制
```

这会涉及新的 qlib score / universe 生成口径，不应混在本轮 C4 中。

一句话总结：

```text
C3/C4 证明 repaired fresh top50 没有未来股票倒灌，也没有 instrument 有效期违规；不可 replay-ready 的少数行已被剔除，最终得到干净但非强行满 150 的 148/149/150 覆盖。
```
