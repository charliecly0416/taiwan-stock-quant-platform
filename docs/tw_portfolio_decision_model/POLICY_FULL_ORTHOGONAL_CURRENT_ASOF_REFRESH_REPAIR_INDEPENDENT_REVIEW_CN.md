# Full Orthogonal Current-Asof Refresh Repair 独立审查

## 1. Verdict

`SUPERSEDED_BY_CONTROLLED_REAL_ACCEPTANCE_PASS`

后续真实验收与最终状态见 `POLICY_FULL_ORTHOGONAL_RESEARCH_REFRESH_STABLE_OPS_CLOSURE_REVIEW_CN.md`。

## 2. 审查结论

1. `daily` 与 `full` 的语义已拆开：只有 current-asof、非 force、未 skip FinMind 的 `full` 才进入独立研究刷新。
2. full branch 在 HSA8 handoff/provider/model/product callbacks 之前返回，不会阻塞或提升 legacy-compatible Model B，也不会产生 strict PIT/OOS 声明。
3. full segmented acquisition 已直接覆盖 institutional/margin 全量 scope；移除同轮额外 batch 是必要修复，可降低重复调用和证据污染风险。
4. expected = returned union absent、集合互斥、unknown 为空、source 覆盖 target asof，以及五个 protected pointers 不变，均为 fail-closed gate。
5. 代码、测试和 runbook 一致；未发现 P0/P1 问题。

## 3. 剩余风险

- 当前仅有静态和模拟证据，尚未验证真实 provider 响应、quota/cooldown 以及 cron runtime 环境。
- 旧 cron 测试与既有授权配置冲突仍是独立技术债；不得在本路线中擅自改变生产 cron 来满足旧断言。

## 4. 运维验收门槛

下一次自然 weekday 14:45 UTC full cron 后只读确认：

```text
status=full_orthogonal_refresh_passed
institutional_flow.source_max_date=target_asof
margin_short.source_max_date=target_asof
expected/returned/absent scope=150/150 closed
orthogonal_batch_triggered=false
protected latest unchanged
provider/model/product publish not triggered
```

满足后本修复可转入稳定运维；失败则只依据 `full_orthogonal_refresh_evidence.json` 开窄修复，不回退产品链。
