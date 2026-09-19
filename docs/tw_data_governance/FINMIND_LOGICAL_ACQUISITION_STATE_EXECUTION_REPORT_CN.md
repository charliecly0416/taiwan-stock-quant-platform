# FinMind Logical Acquisition State 执行报告

## 1. 范围

本阶段实现跨 daily job 的 logical acquisition state 与 required-first segment 调度。仅修改隔离状态模块、daily runner 接线和单元测试；未执行真实 provider、未写 provider/Qlib/latest、未修改 cron。

## 2. 实现

- 新增 `scripts/finmind_logical_acquisition.py`。
- logical run id 由 `target_asof + symbols_sha256` 稳定生成。
- segment evidence 绑定 `logical_run_id`、`target_asof`、`symbols_sha256`、job id、evidence path 和 SHA256。
- required segments 为 `daily_price/institutional/margin/twii`；optional segments 不阻塞 required handoff。
- scope/asof/logical id 不一致时拒绝记录；required 未齐或任一段失败时保持 `INCOMPLETE/hand_off=false`。
- runner 在显式 logical-state 模式下不复用其他 job 的成功 cache，并把恢复后的 captures 汇总给既有 HSA8 builder。
- full scope 调度顺序改为 required segments 优先，optional archives 后置。

## 3. 验证证据

- `tests/unit/test_finmind_logical_acquisition.py`：通过。
- `tests/unit/test_finmind_logical_runner_recovery.py`：`8 passed`，覆盖两次 job 恢复和只请求缺失段。
- HSA8 runtime gate 与 FinMind segmented/M3 相关测试：`16 passed`。
- `python -m py_compile scripts/run_daily_tw_stock_auto_update.py scripts/finmind_logical_acquisition.py`：通过。
- `git diff --check`：通过。

## 4. 禁止边界审计

- provider pull/publish：未执行。
- Qlib/provider/latest/signal/snapshot/Agent：未写入。
- cron/actual crontab：未修改。
- DB/OpenAI/训练/回放/交易：未执行。

## 5. 当前限制

logical state 已接入 runner，但真实 FinMind capture 的 PIT/scope validator 仍由 HSA8 最终判断；本阶段没有把 `BLOCKED` capture 变成可用证据，也没有解锁 downstream。

## 6. 下一步

先进行 isolated recovery simulation：第一 job 成功部分 required segment，第二 job 只恢复缺失 segment，第三次验证 HSA8 handoff 仍拒绝不完整或 blocked evidence；通过后才允许对 pending asof 做一次 `--skip-qlib` 真实验证。

## 7. 真实 pending 验证结果

- job：`daily_tw_stock_auto_update_20260827_20260829T134052Z`
- target asof：`2026-08-27`
- 结果：`same_run_handoff_failed`
- provider：Clash 代理可达，但 FinMind 第一段即返回 `HTTP/API 402 Requests reach the upper limit`。
- required captures：`0`；logical state 保持 `INCOMPLETE`，`handoff_allowed=false`。
- latest：before/after 均为 `2026-08-26`。
- provider/Qlib/latest/signal/snapshot/Agent/downstream：均未推进。

本次重跑确认沙箱之前的 `Operation not permitted` 是执行环境 socket 权限问题；解除沙箱后暴露的是实际 FinMind quota blocker。当前不能把本次失败当成 token 无效或 HSA8 contract 通过。

## 8. 冷却后恢复结果

- 自然/受控恢复最终补齐了 `daily_price`、`twii`、`institutional`、`margin` 四个 logical required segments。
- 统一 logical run：`finmind.logical.20260827.8e856b1a48126cf08ff6`。
- 四个 segment 均有本地 evidence path 与 SHA256，state 为 `COMPLETE`，但这不等于 HSA8 handoff 通过。
- 修复跨 job containment 后离线重建 HSA8，正确识别四个 source family；最终因 `HSA8Error:adapter_output:required_field_missing` STOP。
- 原因是真实 FinMind capture 的 publication/availability PIT 与 source scope/validator 仍未权威证明；没有对这些字段做推断或填充。
- Qlib/provider/latest/signal/snapshot/Agent/downstream 均未推进。

## 9. Adapter 结构修复

离线审计确认原始 adapter JSON 缺少必需的 `source_family` 字段，导致 HSA8 首先报 `adapter_output:required_field_missing`。已在 backend capture 层加入固定 segment-to-family 映射，并通过 backend capture 与 HSA8 回归测试 `40 passed`。该修复不会改变 `source_published_at/available_at`、PIT 或 scope 状态；下一次真实恢复预计会继续停在这些真实数据质量门槛，不能用默认时间填充。

## 10. HTTP Metadata 观测增强

后续 capture 现在按 symbol 保存 FinMind/TWSE 响应中的 `Date`、`Last-Modified`、`ETag`、`Age` header（若存在）。这些只是 provider observation，不自动解释为 publication/availability，也不改变 PIT gate。相关回归测试保持 `40 passed`。

## 11. 2026-08-28 时间依据探测

- 隔离 target：`2026-08-28`，symbol：`2330`，未使用 `--apply`，仅写 `/tmp`。
- FinMind 返回 HTTP 200，body 中存在 `date=2026-08-28` 的业务记录。
- FinMind response `Date=Sun, 30 Aug 2026 05:59:59 GMT`，没有可解释为发布时间的 `Last-Modified/ETag/Age`。
- TWSE MI_INDEX 请求也无法形成 8/28 target-date closure，返回 `target_date_mismatch`；其 `Last-Modified` 是服务器资源修改时间，不等于交易数据 publication time。
- 结论：可证明 8/30 抓到了 8/28 数据，不可证明数据在 8/28 已经可用；不得填写 synthetic `source_published_at` 或 `available_at` 以解锁 HSA8。
