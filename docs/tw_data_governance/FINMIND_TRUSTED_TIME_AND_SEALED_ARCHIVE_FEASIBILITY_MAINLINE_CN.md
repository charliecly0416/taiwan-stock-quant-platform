# FinMind Trusted-Time / Sealed-Archive Feasibility Mainline

状态：进行中，research-only，no-publish。

## 1. 目标

为已采集的 FinMind/TWSE 证据建立可审查的 publication/availability 时间依据，
并判断是否具备生成 PIT-safe sealed archive 的条件。该路线用于修复历史数据证据
不足，不改变既有研究成果，也不自动推进任何生产 latest。

## 2. 当前基线

- `2026-08-28` logical acquisition 已完成，required segments 为 `daily_price`、
  `institutional`、`margin`、`twii`。
- raw/normalized/adapter 路径、checksum、scope 和 logical run 已绑定。
- FinMind 仅观察到 HTTP response `Date`，没有 source-native publication 或
  availability 证明；TWII 还有 schema/target-date 缺口。
- HSA8 正确 STOP；formal provider、Qlib accepted latest、signal/snapshot/Agent
  latest 均不得改变。

## 3. 分阶段路线

1. **F0 inventory**：只读盘点 source-native timestamp、官方 archive、已有 sealed
   archive、fetch evidence 和 scope/checksum，不读取不必要的 payload。
2. **F1 feasibility**：将证据分类为 `PIT_PROVABLE`、`PIT_UNPROVEN` 或
   `SCHEMA_UNPROVEN`；只允许为隔离报告写入结论。
3. **F2 isolated archive candidate**：只有 F1 发现完整可信时间链，才调用 HSA4
   builder 生成 isolated candidate；禁止填充默认时间。
4. **F3 independent review**：复核 source identity、时间顺序、scope closure、
   checksum、sealed manifest 和 forbidden boundary。
5. **F4 handoff decision**：只有 HSA8 PASS 才能提出 downstream 评估；否则保持
   quarantine，并记录下一来源修复方案。

## 4. 禁止边界

禁止 provider/qlib/latest/cron/frontend/backend/DB/OpenAI/training/scoring/replay/
trading 写入；禁止把 fetched_at、HTTP Date 或抓取成功时间当作 publication/available
时间；禁止把 unknown scope 改成 returned/absent；禁止跨 run 拼接证据。

## 5. 当前执行入口

执行 `F0/F1`，输入为 `daily_tw_stock_auto_update_20260828_20260830T060853Z` 及其
logical state；输出执行报告和独立审查报告。若时间依据不完整，立即 STOP，不进入
HSA4 candidate。

## 6. 关闭条件

只有存在 source-native 或可信 sealed archive 时间链、HSA4/HSA8 validator 全部 PASS、
并经独立审查确认 protected latest 未变，才可关闭本线。否则以 `PIT_UNPROVEN`
条件关闭当前阶段，保留 raw research inventory。
