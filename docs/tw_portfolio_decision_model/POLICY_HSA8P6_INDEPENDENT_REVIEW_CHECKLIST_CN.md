# HSA8P6 独立审查清单

日期：2026-08-27
审查身份：独立技术、数据治理与运行安全审查者
边界：只读检查 HSA8P6 源码、isolated fixtures、测试和 execution evidence；不得运行网络、生产 daily/provider/cron，不得修改 installed cron、actual crontab、provider、latest 或前后端生产链路。

## 1. Source Adapter Provenance

- [ ] raw artifact 明确来自本次真实 HTTP response.content bytes；不接受解析后的 record、stdout/stderr、inventory、cache、DB、formal provider、synthetic 或旧 evidence。
- [ ] 每个 response 的 status、endpoint、request parameters、transport identity、response identity/headers（合同要求范围内）和 raw SHA256 均来自同一次请求并互相绑定。
- [ ] normalized artifact 是同一次响应的确定性解析结果，记录 parser/schema version，并绑定同一 `source_family`、`source_id`、`acquisition_run_id`、`target_asof`。
- [ ] source validator 不能仅依据 row count、文件存在或 command return code 判定 PASS。
- [ ] 空、错误、partial response 保留 raw bytes，并明确 blocked/unknown scope。

## 2. PIT 不可推导

- [ ] `source_published_at` 必须来自 provider 可验证发布时间或明确的权威 metadata。
- [ ] `available_at` 必须来自 source availability provenance；不得由 `fetched_at`、job finish time、文件 mtime、cache updated time 或 target date 推导。
- [ ] `fetched_at` 是本次实际请求完成时间，而非请求开始时间、cache 命中时间或 stdout 时间。
- [ ] 不可证明 publication/availability 时字段为空或显式 unknown，并且 source validator 为 BLOCKED。
- [ ] 严格验证 `source_published_at <= available_at <= fetched_at` 以及 source-specific `trade_date` 规则。

## 3. TWII Source Contract

- [ ] TWII 有独立真实 provider adapter、endpoint/request metadata、raw bytes 和 normalized payload。
- [ ] TWII response schema、trade date、expected/returned/absent/unknown scope 有 source-specific validator。
- [ ] TWII 缺失、schema 不明、scope 不闭合或 PIT 不可证明时必须 STOP/quarantine。
- [ ] 不得用 Qlib calendar、formal provider、readonly bridge、inventory、stdout、cache 或旧 candidate 替代 TWII raw lineage。

## 4. Handoff Schema 与控制流

- [ ] runner 传入的 source record schema 与 HSA8 builder 实际消费 schema 完全一致，包含 exact paths、roles、hash、metadata 和 scope。
- [ ] 四个 required family：`adjusted_price`、`twii`、`institutional_flow`、`margin_short` 各恰好一条，全部绑定同一 run/asof。
- [ ] `expected_scope = returned_scope ∪ absent_scope ∪ unknown_scope`；列表无重复、分区无重叠；unknown 不得转成 absent/zero-fill。
- [ ] handoff gate 位于所有 derived feature、model、provider、latest、snapshot、Agent gate 之前。
- [ ] manifest 在 raw/normalized durable write、validator、hash和 locator检查之后最后 atomic 提交。

## 5. Fail-Closed 与下游隔离

- [ ] required family 缺失、source skip、segment failure、PIT/scope/path/hash/run mismatch、TWII blocked 或 manifest 写入失败时设置 pending asof 并停止。
- [ ] `--skip-finmind` 不能绕过 gate；必须 STOP/quarantine。
- [ ] required segment skip 和成功 cache reuse/cooldown cache 不得生成当前 run raw lineage，必须 STOP。
- [ ] 测试通过 mock/spy 证明 failure 后 derived/provider/latest/model/snapshot/Agent 下游未调用，而非仅检查状态字符串。
- [ ] 失败 job 保留 validation report、raw/error/scope 状态和 pending；不会清除既有 pending 或推进 latest。

## 6. Capture Writer Race Safety

- [ ] job-local parent/path 使用 `O_NOFOLLOW`、逐组件 locator 校验或等价安全机制。
- [ ] 文件使用 `O_EXCL` staging、完整写入、flush/fsync、目录 fsync 和 `renameat2(RENAME_NOREPLACE)` 或等价 no-replace。
- [ ] symlink、path escape、parent replacement、file/inode replacement、hash drift、existing final、rename/fsync failure 均有负例。
- [ ] 并发替换或 locator 不一致时只清理本事务可证明拥有的 staging/final，不删除未知 inode。

## 7. 测试与证据

- [ ] 新增测试覆盖真实 response.content 与 parsed records 不同、PIT 缺失/倒序/cache 冒充、TWII schema/scope、skip/cache、下游未调用和 writer race。
- [ ] HSA4-HSA8 回归数字可由命令复核；isolated、普通权限、受控权限结果分开报告。
- [ ] M3 结果单独报告为 `30 passed / 1 pre-existing FPALA assertion failure`，不得通过修改 cron 掩盖。
- [ ] execution report 的文件清单、checksum、禁止边界和测试总数均可重现。

## 8. 结论规则

全部硬门通过才可判定：

```text
PASS_HSA8P6_RUNTIME_HANDOFF_CONTRACT_READY_FOR_HSA7_OBSERVATION
```

任一硬门失败则判定：

```text
FAIL_HSA8P6_NEEDS_REPAIR
```

即使 P6 通过，在真实 daily job 生成并通过 HSA5/HSA7 handoff 前，Model B 仍保持：

```text
STOP_HSA7_REAL_HANDOFF_MISSING_OR_INVALID
```
