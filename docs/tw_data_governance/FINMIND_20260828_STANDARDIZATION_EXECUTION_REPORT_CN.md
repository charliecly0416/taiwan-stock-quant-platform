# FinMind 2026-08-28 标准化与 HSA8 交接执行报告

## 1. 范围

本轮处理 `finmind.logical.20260828.0f1da495d6664275d8e8`，目标日期为
`2026-08-28`，覆盖既定 150 标的。工作范围是已完成采集证据的离线标准化核验和
HSA8 handoff；不写 formal provider、Qlib accepted latest、signal/snapshot/Agent
latest，不修改 cron，不训练、不评分、不回放、不连接 DB/OpenAI/broker。

## 2. 执行结果

- logical acquisition state：`COMPLETE`，`handoff_allowed=true`。
- `daily_price`、`institutional`、`margin`：HTTP 200，目标交易日为
  `2026-08-28`，每类 expected scope 为 150；返回/缺失/unknown 分区保持
  `0/0/150`，因此没有把未知误记为缺失或成功。
- 每类均保留 150 个 raw 文件、1 个 normalized 文件和 adapter metadata；路径、
  SHA256、logical run id、target asof 均有绑定。
- FinMind response 只有抓取时 server `Date`，没有可接受的 publication 或
  availability 证明，因此 `pit_status=BLOCKED_PUBLICATION_AND_AVAILABILITY_UNPROVEN`。
- TWII 为 HTTP 200，但 `trade_date`/scope schema 未满足 HSA8，状态为
  `BLOCKED_PROVIDER_SCHEMA`；不可用 server headers 推导数据发布时间。

## 3. 实现修复

首次重放暴露 runner 将 `raw_files/normalized_files` 作为 role object 传给严格
validator，造成 `adapter_output_raw_files_override_mismatch`。已修复为传递 adapter
canonical path string list，role 由 HSA8 builder 生成；修复后 handoff 已进入真实
validator，并按预期停止于 `adjusted_price:validator_not_PASS`。

## 4. 结论

本轮完成 raw/normalized/adapter 证据标准化登记，但未形成 PIT-safe downstream
handoff。状态保持 `RAW_READY_PROVIDER_STALE` / `STOP`，`latest_before` 与
`latest_after` 均为 `2026-08-26`。禁止用本次 8/30 抓取成功反推 8/28 当天可用，禁止
以默认时间填充 publication/availability，也禁止以 FinMind raw 冒充 Yahoo-adjusted
Qlib provider。

## 5. 后续入口

只有获得可验证的 publication/availability lineage、完整 TWII schema/target-date
证据，或建立明确批准的 sealed historical archive，才可重新执行 HSA8 handoff。
在此之前数据可用于 raw research inventory，不可用于 Model A/B 的规范 PIT 评分或
任何 latest 推进。
