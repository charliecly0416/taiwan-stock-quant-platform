# FinMind Orthogonal Access And Same-Run Recovery Mainline

状态：进行中，research-only；logical acquisition state 已实现，尚未通过真实 HSA8 handoff。

## 目标

解决 `institutional_flow` 与 `margin_short` 在免费注册级 FinMind 账号下的请求上限问题，使日更能够在不伪造来源、不拼接跨 run 证据的前提下恢复 HSA8 same-run handoff。

## 已确认事实

- 当前 token 的单标的请求返回 HTTP/API 200 success。
- 不带 `data_id` 的全市场批量接口返回 400，要求升级用户等级。
- 150 标的逐一请求会触发 402 request upper limit。
- Clash/mihomo 可用，但 FinMind 当前规则走 DIRECT；这不是主要阻塞。

## 允许范围

- FinMind 请求节流、有限退避、checkpoint 和 job evidence。
- isolated raw/normalized/adapter/handoff evidence。
- 离线 mock 测试和受控 provider 小规模验证。

## 禁止范围

- 不降低 HSA8 PIT、scope、lineage 或 same-run 要求。
- 不用旧 batch 数据冒充当前 acquisition run。
- 不修改 provider、Qlib accepted latest、signal/snapshot/Agent latest。
- 不修改 cron 或实际调度配置，除非另有明确授权。
- 不触发交易、broker、order、target、DB 或 OpenAI。

## 阶段

1. Access diagnosis：确认 token、网络、接口等级和请求上限。
2. Client recovery：实现可配置节流、有限退避、错误分类和中断可恢复 evidence。
3. Same-run contract review：验证 full scope 仍能产生四类 required source，失败则明确 STOP。
4. Controlled validation：先小规模 provider 验证，再决定是否进行完整 150 标的采集。
5. Natural cron acceptance：连续工作日验证 pending retry、handoff、downstream gate 和 protected latest 不变。

当前子阶段：isolated recovery simulation。第一 job 部分成功、第二 job 恢复缺失段、第三次 HSA8 gate 审查必须先通过，才允许对 pending asof 做一次真实 `--skip-qlib` 验证。

## 完成门槛

只有同时满足以下条件，才允许回到“完整自动链路稳定运维”：

- 四类 required source 属于同一 acquisition run；
- raw/normalized/adapter 路径、SHA256、run_id、asof 一致；
- PIT 和 scope closure 通过；
- full daily chain downstream 自动完成；
- 至少连续多个工作日自然 cron 无结构性 handoff failure。

当前决策：保持 `STOP_HSA8_REAL_HANDOFF_MISSING_OR_INVALID`，不以单独 daily price 成功解锁下游。
