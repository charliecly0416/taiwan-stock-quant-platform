# MBCDS3-4 独立审查意见

## 1. 结论

`PASS_WITH_BLOCKER`。

契约实现和保护边界通过；Model B 进入正式 baseline 仍被证据门阻塞，原因是当前没有有效 warm-up 日，也没有可用于证明 A+B 优于 A 的规范化 OOS 对比。

## 2. 已核对

- daily runner 在 Model Signal gate 前冻结 `decision_cutoff`，并把它传给标准 ScoreJob。
- ScoreJob 与 ModelSignalArtifact 都显式写入 `source_acquisition_run_id` 和 `decision_cutoff`。
- FinMind/TWII HSA8 adapter 只从当前响应中明确出现的 target date 记录计算 returned scope；目标日不完整时不会放行。
- ledger 对每个 HSA8 source 执行 target/asof、acquisition run、timezone-aware 顺序和实际 SHA256 校验。
- inventory bridge 只有在 ledger PASS 且 ScoreJob acquisition ID 相同的情况下才填 PIT 元数据；否则保持 quarantine。
- 旧产物缺少字段时不会通过回填、mtime 或完成时间获得资格。
- Model A baseline、latest/provider、cron 和前后端默认路径未被 Model B gate 阻塞。

## 3. 测试与静态证据

- py_compile：通过。
- ScoreJob/readonly integration tests：18 passed。
- MBCDS3 accumulator self-test：通过。
- 相关 backend/daily 回归：47 passed。
- daily orchestrator audit：passed；legacy 写入路径仍是显式非默认 gate，属于既有 warning。

## 4. Blocker

1. 历史 ScoreJob/ModelSignal 没有完整 source lineage，必须 quarantine。
2. 9/3、9/4 的真实响应目标日覆盖不足，当前真实 daily accumulation 尚无有效 Model B PIT 日；修复已使后续完整响应可自动通过。
3. 尚无同窗口、同策略、同费用、同执行价的 Model A vs A+B OOS 结果，不能声称收益提升。

## 5. 下一步工作单

保持 Model B shadow-only，继续工作日自然 cron 累积；每个有效日保存 source availability ledger、same-run inventory 和 checksum。累计 20 日后再开 shadow scoring，累计 60 日后做严格 OOS comparison，累计 120 日且增益稳定后才开 baseline switch review。
