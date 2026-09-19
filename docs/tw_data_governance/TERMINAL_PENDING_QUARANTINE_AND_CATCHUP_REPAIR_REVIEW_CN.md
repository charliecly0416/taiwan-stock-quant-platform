# Terminal Pending Quarantine / Catch-up 独立审查

## 结论

`PASS_READY_FOR_NATURAL_CRON_CATCHUP_OBSERVATION`。

## 审查要点

1. classifier 不以顶层失败状态单独判 terminal；必须结合 COMPLETE logical state 和
   精确 HSA8 evidence-gate error，误隔离风险受控。
2. `adapter_output:required_field_missing` 等实现错误专项测试确认仍为 retryable。
3. 原 pending 以 checksum 不变的独立文件保留，没有删除历史成果。
4. catch-up 按工作日逐日推进，可避免 8/31 被直接跳过。
5. protected latest 全部未变；实际迁移只涉及 ops pending/quarantine。
6. API 与前端所读状态已一致，不再返回相互矛盾的 next retry hint。

## 后续观察

观察下一轮自然 cron 是否创建 target `2026-08-31` 的新 logical acquisition，并检查
新 adapter 是否包含 `first_successful_capture` evidence。若新 run 仍阻塞，应按新的
具体 segment/scope/TWII 错误修复，不得恢复 8/28 无限重试。
