# F0/F1 Trusted-Time Feasibility 执行报告

## 范围

目标 run：`finmind.logical.20260828.0f1da495d6664275d8e8`，target asof：
`2026-08-28`。仅检查既有 ops evidence 和 adapter metadata，未调用 provider，未写
production 或 latest。

## 执行结果

| source family | scope | raw/normalized | publication | availability | 结论 |
|---|---:|---:|---|---|---|
| adjusted_price | 150 unknown | 150/1 | 缺失 | 缺失 | PIT_UNPROVEN |
| institutional_flow | 150 unknown | 150/1 | 缺失 | 缺失 | PIT_UNPROVEN |
| margin_short | 150 unknown | 150/1 | 缺失 | 缺失 | PIT_UNPROVEN |
| twii | 1 unknown | 1/1 | 缺失 | 缺失 | SCHEMA_UNPROVEN |

所有 adapter 均绑定同一 logical run 和 target asof；三类 FinMind segment 的 HTTP
status 为 200。`unknown_scope` 未被改写为 returned 或 absent。TWSE/FinMind response
server `Date` 仅是传输观察，不被提升为业务发布时间。

## 决策

未发现可直接支持 `source_published_at <= available_at <= fetched_at` 的可信时间链，
因此不执行 HSA4 sealed candidate，不生成 PIT-safe archive，不进入 HSA8 downstream。
当前 latest 保持 `2026-08-26`。
