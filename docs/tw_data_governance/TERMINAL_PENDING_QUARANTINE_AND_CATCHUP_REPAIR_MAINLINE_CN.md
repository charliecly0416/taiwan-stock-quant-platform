# Terminal Pending Quarantine / Workday Catch-up 修复主线

## 目标

防止已经完成采集、但因不可回溯 PIT/source evidence 明确终局阻塞的历史 pending
无限占据 daily-auto 调度入口；保留全部旧证据，并使后续工作日能够继续建立新的
prospective first-successful-capture run。

## 判定边界

只有同时满足以下条件才允许 quarantine：

1. pending reason 和 job status 均为 `same_run_handoff_failed`；
2. logical acquisition state 为 `COMPLETE` 且 `handoff_allowed=true`；
3. HSA8 error 明确包含 `validator_not_PASS` 或 `pit_status_not_PASS`。

网络、额度、segment 缺失、adapter/schema 实现错误及未知错误继续原 pending 重试，
不得跳过。

## 行为

- 原 `pending_asof.json` 原子移动到 `terminal_pending_quarantine/`，不删除、不覆盖；
- 写独立 quarantine decision record；
- 生成下一个工作日 catch-up pending，逐日推进，不直接跳过中间工作日；
- protected latest、provider、Qlib、signal/snapshot/Agent、cron 均不改变；
- 状态 API 对所有 pending 返回真实处理提示，不再把非 fresh-data pending 说成不存在。

## 关闭门槛

专项和相关回归通过；8/28 原证据可复核；8/31 catch-up pending 可见；API 提示正确；
五个 protected latest fingerprints 不变；下一轮自然 cron 能选择 8/31。
