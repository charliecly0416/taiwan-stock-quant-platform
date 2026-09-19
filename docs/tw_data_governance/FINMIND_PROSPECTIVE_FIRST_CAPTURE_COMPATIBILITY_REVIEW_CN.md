# Prospective First-Successful-Capture 兼容性独立审查

## 结论

`PASS_WITH_CONDITIONS_READY_FOR_PROSPECTIVE_CAPTURE`。

## 审查

1. 新字段是可选的，旧 adapter/fixture 的 publication-time contract 未被破坏。
2. first-capture 模式没有伪造 publication time；availability 必须绑定一次真实捕获
   observation，并且仍受 HSA8 的 validator、scope、lineage、checksum 和 same-run gate
   约束。
3. 当前 backend 仍会在 scope 未经权威确认时保持 `BLOCKED_SOURCE_SCOPE_OR_VALIDATOR_UNPROVEN`，
   所以新增字段不会导致未知数据进入 Model A/B。
4. 真实 8/28 run 的 HSA8 STOP 仍然成立；formal provider、Qlib accepted latest、
   signal/snapshot/Agent latest、cron 和生产 API 均未改变。

## 条件

后续 daily adapter 必须为每个 required segment 记录完整 scope closure，并在完整成功
捕获后才可将 validator/pit 状态置为 PASS。first capture 只能证明“该时点之后系统
观察到数据”，不能证明交易日当天已经可用，也不能回溯修复历史 run。
