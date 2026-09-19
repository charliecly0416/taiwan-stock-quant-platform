# FinMind Logical Acquisition State 审查意见

## 结论

`PASS_WITH_CONDITIONS`。

## 已通过

- logical run id 不依赖单个 segment job id，跨 job 恢复具有稳定身份。
- evidence 的 asof、symbols checksum 和 logical id 不匹配时会拒绝写入。
- required segment 缺失或失败不会允许 handoff。
- optional segment 放在 required segment 后，不会先消耗额度而阻塞 HSA8 所需来源。
- logical recovery 模式不把其他 job 的成功 cache 当作当前 logical run 证据。
- protected latest、provider、cron 和交易边界未被触碰。

## 条件

1. 必须补充跨 job 的真实模拟测试，覆盖 segment job id 与 logical run id 的区分、失败后只恢复缺失段、跨 asof 拒绝。
2. 必须证明 state 中保存的 evidence path 在恢复时仍可读且 SHA256 未改变。
3. 未通过 HSA8 PIT/scope/lineage validator 前，不得进入 downstream 或 latest。
4. 真实 pending 验证必须保持 `--skip-qlib`，并且仅在 isolated/ops evidence 下执行。

## 审查决定

isolated recovery simulation 已通过，允许进入一次当前 pending asof 的真实 `--skip-qlib` 验证；仍不允许进入 provider publish、Qlib refresh、latest switch、cron enablement 或完整自动运维 closure。

真实 pending 验证已执行但因 FinMind 402 quota blocker STOP。当前审查决定：保持 `STOP_HSA8_REAL_HANDOFF_MISSING_OR_INVALID`，不再重复全量请求；待 provider quota/cooldown 恢复后，只运行 logical-state 缺失段恢复，并继续保持 `--skip-qlib`。

随后发现 logical recovery 的全部 required segment 已实际完成，但 HSA8 handoff 因跨 job path containment 被拒绝；已修复为仅对带 logical run identity 的 handoff 使用 `daily_auto_update` 公共 ops containment root，同时继续执行 exact path、SHA256、PIT、scope、lineage 和 validator checks。普通单 job handoff 的 job-root 限制保持不变。

最终审查：logical state `COMPLETE`，但 HSA8 handoff `STOP`，错误为 `adapter_output:required_field_missing`。这是正确的安全结果，不得将 FinMind raw capture 的非空记录当作 PIT/source-scope PASS。当前路线仍不能 closure，也不能开启 latest 或生产下游。
