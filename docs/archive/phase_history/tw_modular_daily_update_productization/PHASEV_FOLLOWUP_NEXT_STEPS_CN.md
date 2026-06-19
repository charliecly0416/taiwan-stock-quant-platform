# Phase V 收口后的后续工作文档

生成日期：2026-06-17

## 1. 现状结论

Phase V 可以作为当前只读日更路线的收口基线使用，但它还不是“全量真实 provider 自动闭环”的最终证明。

当前已经完成的是：

```text
真实数据 staging
-> MultiModel DataReadinessGate
-> 默认模型 + 默认策略的 readonly 日更
-> 前端只读展示
```

当前还没有完全完成的是：

```text
全市场/全 universe 的真实覆盖证明
所有前端可选模型/策略的完整可运行矩阵
不同模型/策略切换后的稳定按需重算验证
更强的 fallback 解释和前端展示一致性
```

## 2. 后续要做什么

### 2.1 真实覆盖补强

先把数据覆盖做实，不要只停在小样本 staging。

要确认：

```text
Yahoo / FinMind / 正交数据源是否覆盖完整 universe
fallback 是否只是兜底，而不是默认事实来源
available_at / decision_cutoff 是否对所有源一致成立
symbol mapping / instrument 有效期 / coverage 审计是否完整
```

目标是让 `all_required_ready` 不只对当前样本成立，而是对正式可用范围成立。

### 2.2 多模型 / 多策略矩阵补强

当前允许的模型和策略已经冻结，但还需要把它们的运行条件说透、说全。

要确认：

```text
raw qlib、fresh qlib、frozen qlib、e4 orthogonal LTR 是否都能单独运行
每个策略对 ranking / holdings / price / fee 的依赖是否明确
当某个模型今天不可运行时，前端是否只显示 unavailable reason，而不是静默降级
同一份 ready data 是否能支持前端切换模型/策略后按需重算
```

目标是让“切模型、切策略”成为稳定的只读查询能力，而不是临时脚本行为。

### 2.3 前端只读交互收尾

前端已经接近用户第一性原则，但还可以再收一层。

要确认：

```text
默认只展示今日最关键结果
模型选择、策略选择、数据状态分区清晰
不可运行状态给出短原因，不堆内部术语
readonly / candidate / not order 语义始终保持
不把 staging 解释成正式 provider latest
```

目标是让用户看到的是“今天能不能看、能看什么、为什么”，而不是工程术语列表。

## 3. 推荐顺序

后续建议按这个顺序做：

1. 先做真实覆盖补强。
2. 再做多模型 / 多策略可运行矩阵补强。
3. 最后做前端只读交互收尾。

不要反过来先做展示，再补数据合同，否则很容易把前端做成“看起来完整、实际上只服务默认组合”的状态。

## 4. 明确不做的事

后续仍然不要把以下内容混进 V 路线：

```text
训练新模型
切换默认策略
provider publish / accepted latest 切换
monitor config / scan / alerts 写入
broker / quick-trade / orders
真实交易
Agent 扩权
```

这些如果要做，应该开新主线，不应在 V 路线继续加修。

## 5. 给执行者的提示

```text
请优先补真实覆盖，再补模型/策略矩阵，最后补前端交互。
不要只在默认模型上做通路，不要把 fallback 当成最终数据事实，不要让前端静默降级。
所有新增内容都必须保持 readonly、not order、not target_position、not investment_advice。
```

## 6. 给审查者的提示

```text
请优先审查数据覆盖是否足够，再审查模型/策略是否真的可运行，最后审查前端是否仍然符合用户第一性原则。
如果发现只服务默认组合、部分数据继续生成结果、或者前端把不可运行状态讲得不清楚，请停止放行。
```
