# HSA8P5 Real Provider Capture Adapter 独立审查清单

日期：2026-08-27
审查身份：独立审查者
边界：只读检查 HSA8P5 源码、isolated fixtures、测试和 execution evidence；不得运行生产 daily/provider/cron，不得修改 cron、latest、provider 或前后端生产链路。

## 1. HTTP Raw真实性

- [ ] raw artifact 来自本轮真实 provider HTTP response bytes，而不是 `DailyBarRecord`、stdout/stderr、inventory、cache、DB、formal provider 或旧 evidence。
- [ ] raw artifact 保留 response status、headers/transport identity（按合同要求）、request parameters、endpoint/version 与 source identity。
- [ ] record snapshot 与 normalized payload 分离；任何 snapshot 不得被标记为 authoritative raw。
- [ ] 空响应、错误响应和部分响应仍保留原始 bytes 与明确的 scope/status，不得伪装成功。

## 2. Source/PIT/Scope合同

- [ ] `adjusted_price`、`twii`、`institutional_flow`、`margin_short` 各恰好一条 required source record。
- [ ] raw/normalized exact path、role、SHA256 绑定同一 `acquisition_run_id`、`target_asof`、`source_family`、`source_id`。
- [ ] source-level `source_published_at <= available_at <= fetched_at`；时间来自真实 source/runtime provenance，不由 job finish/cache 时间推断。
- [ ] `trade_date` 满足 source-specific PIT 规则，不能只由目标日期或 normalized 内容推断。
- [ ] `expected_scope = returned_scope ∪ absent_scope ∪ unknown_scope`，列表无重复、分区无交叠；unknown 不得降级为 absent/zero-fill。
- [ ] TWII 有真实 adapter；若获取不到，明确 `BLOCKED/STOP`，不得用 calendar、bridge、inventory 或 cache 替代。

## 3. Runner/Builder一致性

- [ ] runner 传入的 source record schema 与 HSA8 builder 实际接受的 locator/schema 完全一致。
- [ ] builder 不信任调用者 hash，重新读取并计算 SHA256；不接受 path object/role object 的隐式误读。
- [ ] handoff gate 位于所有 derived feature、model、provider、latest、snapshot、Agent gate 之前。
- [ ] manifest 在所有 raw/normalized durable write 与 validation 完成后最后 atomic 提交。

## 4. 安全写入与race

- [ ] job-local parent/path 使用 no-follow、逐组件校验或等价安全机制。
- [ ] artifact 使用 `O_EXCL`/atomic no-replace、flush/fsync；不会跟随 symlink 或覆盖已有文件。
- [ ] 覆盖 symlink、path escape、parent replacement、file/inode replacement、hash drift、manifest pre-existence 与 atomic failure 的负例。
- [ ] 并发替换后只允许清理本事务可证明拥有的 staging/final，不得删除未知 inode。

## 5. Fail-closed与cache边界

- [ ] required family 缺失、source validator 非 PASS、PIT/scope/path/hash/run mismatch、TWII 缺失或 manifest 提交失败时设置 pending asof 并停止。
- [ ] 失败后不调用 derived/provider/latest/snapshot/Agent 下游；无 warning-only continuation。
- [ ] `--skip-finmind` 不能绕过 required handoff gate；只能进入 STOP/quarantine。
- [ ] cache 只能表达 retry/cooldown，不能提供当前 run raw/normalized lineage。

## 6. 测试与结论规则

- [ ] isolated 专项、普通权限回归、受控权限回归分别报告；FPALA 既有失败单独列示。
- [ ] execution report 的测试总数可由实际命令复核，不接受无法重现的数字。
- [ ] 禁止边界 audit 通过，且未改生产 daily/provider/cron/latest/frontend/backend。

全部硬门通过才可判定：

```text
PASS_HSA8P5_REAL_CAPTURE_ADAPTER_READY_FOR_HSA7_OBSERVATION
```

否则判定：

```text
FAIL_HSA8P5_NEEDS_REPAIR
```

即使 P5 通过，在真实 daily job 生成并通过 HSA5/HSA7 handoff 前，Model B 仍保持：

```text
STOP_HSA7_REAL_HANDOFF_MISSING_OR_INVALID
```
