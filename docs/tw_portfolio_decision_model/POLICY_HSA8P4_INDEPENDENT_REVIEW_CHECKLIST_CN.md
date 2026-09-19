# HSA8P4 Runtime Same-Run Handoff 独立审查清单

日期：2026-08-27
审查身份：独立审查者
审查边界：只读审查源码、isolated fixtures、测试与 execution evidence；不运行生产 daily/provider/cron，不修改 installed cron、actual crontab、latest 或生产链路。

## 1. 真实来源

- [ ] 四个 required family 均由本轮 provider 响应产生：`adjusted_price`、`twii`、`institutional_flow`、`margin_short`。
- [ ] raw 文件是 provider 原始响应，normalized 文件是本轮解析结果；不是 inventory、stdout/stderr、cache、DB、formal provider、synthetic 或旧 evidence。
- [ ] raw/normalized 在当前 `job_id` 的 job root 内，regular no-follow file，具有真实 SHA256、role、exact path 绑定。
- [ ] cache 仅表达 retry/cooldown；cache 命中不冒充当前 run 的 raw/normalized lineage。

## 2. Run、PIT 与 scope

- [ ] `acquisition_run_id == job.json.job_id` 且 `target_asof == job.json.asof`。
- [ ] 每个 source 有稳定 `source_id`、provider/request/endpoint/version/transport metadata。
- [ ] source-level `source_published_at <= available_at <= fetched_at`，时间来自实际 source/runtime，不由 job finish 或 cache 时间推断。
- [ ] 每个 source 有 `trade_date`，且满足 source-specific PIT 约束。
- [ ] `expected_scope = returned_scope ∪ absent_scope ∪ unknown_scope`；分区无重复、无交叠；unknown 不得降级为 absent/zero-fill。
- [ ] required family 恰好一条；optional source 若本轮产生则同样记录，缺失不会伪装成功。

## 3. 控制流与失败语义

- [ ] job identity 固定后，依次执行 fetch -> durable raw -> normalize -> validator -> handoff manifest -> derived/provider/latest gates。
- [ ] handoff manifest 最后 atomic 提交，文件写入有 flush/fsync，失败不会留下可被消费的半成品。
- [ ] handoff 验证位于 derived feature/model/provider/latest 之前。
- [ ] required source 任一缺失、失败、PIT/scope/path/hash/run mismatch 或 manifest 提交失败时，状态为 STOP/quarantine。
- [ ] required handoff 失败时不会继续模型、provider、latest、snapshot 或 Agent 发布；不存在 warning-only continuation。

## 4. 文件安全与并发

- [ ] 输入读取使用 `openat + O_NOFOLLOW`，并校验 regular file、FD identity、locator 与 SHA256。
- [ ] 输出使用 isolated staging、fsync、atomic no-replace；不覆盖已有 final。
- [ ] 覆盖 parent replacement、file replacement、symlink、path escape、manifest pre-existence 与失败清理负例。
- [ ] 并发替换或 inode 不一致时 fail closed，绝不删除非本轮 final。

## 5. 禁止边界与证据

- [ ] diff 未修改 installed cron/actual crontab、provider publish/refresh、Qlib refresh、latest pointers、frontend/backend production、DB/OpenAI、训练/评分/replay 或交易链路。
- [ ] execution report、review evidence、checksum manifest 与测试统计可由源码和命令复核。
- [ ] 普通权限与受控权限测试结果分开报告，不虚报 crontab 读取能力。

## 6. 结论规则

只有全部硬门通过，才能判定：

```text
PASS_HSA8P4_RUNTIME_WIRING_READY_FOR_HSA7_REAL_OBSERVATION
```

否则判定：

```text
FAIL_HSA8P4_NEEDS_REPAIR
```

无论 P4 是否通过，在真实 daily job 生成并通过 HSA5/HSA7 handoff 前，Model B 保持：

```text
STOP_HSA7_REAL_HANDOFF_MISSING_OR_INVALID
```
