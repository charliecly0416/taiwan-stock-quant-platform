# HSA8P7 独立审查清单

## 1. 审查定位

- 路线：`HSA8P7_ADAPTER_METADATA_FIDELITY_TWII_SCOPE_AND_DOWNSTREAM_NO_CALL_REPAIR`
- 审查角色：独立审查者；不参与执行者实现，不修改生产文件。
- 前置结论：HSA8P6 为 `FAIL_HSA8P6_NEEDS_REPAIR`。
- 当前生产门：继续保持 `STOP_HSA7_REAL_HANDOFF_MISSING_OR_INVALID`。
- 本清单不授权网络、daily、provider、cron、Qlib、latest、训练、评分、回放、DB、OpenAI 或前后端生产变更。

正式审查的前提是执行者已提供 HSA8P7 execution report、实际 diff、专项测试和可定位的测试输出。缺少任一项时结论只能是 `STOP`，不得以源码静态印象代替完成证据。

## 2. 审查材料

执行者完成后必须读取并核对：

- HSA8P7 work document、execution report、reviewer handoff。
- `backend/scripts/update_tw_stock_daily.py`。
- `scripts/run_daily_tw_stock_auto_update.py`。
- HSA8 same-run handoff builder、validator、相关 helper。
- HSA8P7 专项测试、HSA4-HSA8 回归测试、backend acquisition 测试。
- 生成的 isolated evidence、pending 状态、fingerprint/diff 和禁止范围审计。
- 不接受只写在 report 中、但无法由源码、测试或 artifact 复现的结论。

## 3. 硬门 A：Adapter metadata fidelity

逐字段检查 adapter 返回值是否被 runner 原样消费并绑定到同一 capture：

- provider/source id、source version、endpoint、request parameters、HTTP status、transport identity。
- parser/schema version、validator status、trade date/target asof、fetched_at。
- `source_published_at`、`available_at`、PIT status；无法由 source 证明时必须为空或明确 BLOCKED，不得硬编码。
- run id、scope id/hash、raw artifact path/hash、normalized artifact path/hash、artifact role。
- 失败、空响应、cache reuse、stdout summary、job finish time 均不得覆盖 authoritative adapter metadata。
- provider、trade date、validator status 不得在 runner 中重新固定、推导或从 stdout 拼装。
- raw 必须是对应 HTTP `response.content`；normalized 必须由同一 raw/capture 生成，并保留 source/run/asof/PIT/scope 绑定。
- validator PASS 只在完整契约满足时成立；schema-only 或 inventory-only 不得升级为 source PASS。

## 4. 硬门 B：TWII scope / PIT

- TWII 必须由独立、source-specific adapter 取得；不得用 calendar、inventory、cache、stdout、bridge 或旧 evidence 替代。
- adapter 必须验证 target date 与 source 返回日期一致，禁止使用当前时间或 job 完成时间代替。
- scope 必须形成四分区闭包：`expected`、`returned`、`absent`、`unknown`。
- 四分区不得重复、重叠；`expected = returned ∪ absent ∪ unknown`，且未知不得伪装为 absent。
- 空响应、partial response、重复键、跨日期响应、scope hash/run mismatch 均必须 STOP。
- TWII 的业务字段、记录数量和目标范围必须有 source-specific 证据；最小字段 schema 通过不能单独形成 PASS。
- source publication/availability 或有效 PIT 无法证明时必须保持 BLOCKED，即使 trade date 和 schema 看起来正确。

## 5. 硬门 C：Fail-closed 与 downstream zero-call

对每个失败场景用 spy/mock 或等价可审计计数证明：

- `--skip-finmind`、required segment skip、cache reuse、required family 缺失。
- raw/normalized 缺失或角色错误、PIT 不可证明、scope 未闭合、path/hash/run/asof mismatch。
- TWII blocked、adapter exception、handoff builder failure。

每个场景都必须：

- 写入或保留当前 run 的 pending 状态与明确 reason code。
- 返回非成功结果，并在 derived/provider/latest 之前停止。
- provider refresh、derived feature、model score、latest pointer、readonly snapshot、Agent prompt 的调用次数均为零。
- 旧 latest fingerprint 不变；不得把上一轮成功结果冒充当前 run 成功。
- 测试必须断言调用计数为零，而不是只检查源码顺序或返回码。

## 6. 硬门 D：Capture writer race / filesystem safety

实际负例或等价可复现测试必须覆盖：

- job-local staging；目录和文件 `O_NOFOLLOW`、`O_EXCL`、权限和 locator 检查。
- staging 写入、内容 fsync、父目录 fsync、atomic no-replace 提交。
- final 已存在、staging 已存在、rename 冲突、fsync 失败、hash drift。
- final 文件/父目录被 symlink 替换、path escape、竞争创建、未知 inode 存在。
- 失败只能清理由本轮创建且 fingerprint/ inode 明确匹配的 staging；不得删除或覆盖未知文件。
- final 不得 replace 已存在的其他 run；既有 evidence、latest 和生产目录不得被覆盖。

## 7. 证据与回归

- 独立复跑 HSA8P7 专项测试、HSA4-HSA8P7 相关回归、backend acquisition 测试。
- 运行 `py_compile` 与 `git diff --check`。
- 单独记录普通权限、受控权限和禁止边界检查结果。
- 单独核对 M3 既有结果：预期 `30 passed / 1 FPALA failure`；FPALA failure 不得被路线改动掩盖或重写。
- 报告实际收集的 passed/failed/skipped 数字、命令、退出码和测试文件。
- 任何无法复现、只来自执行者口述或与实际 diff 不一致的数字按缺失证据处理。

## 8. 禁止边界核对

审查过程中不得：

- 访问网络或运行生产 daily/provider/cron。
- 修改 installed cron、actual crontab、provider、Qlib、任何 latest pointer 或生产 artifact。
- 运行 provider publish/refresh、Qlib refresh、训练、评分、strategy replay。
- 写 DB/OpenAI、monitor/broker/order/target、frontend/API production default。
- 覆盖旧 HSA evidence、删除未知文件或替执行者修复代码。

发现越界、生产指针变化、旧 evidence 被覆盖或 downstream 在 gate 失败后被调用时，立即判定 `STOP`，先保留 fingerprint/diff 证据。

## 9. 结论分类与出口

- `PASS_HSA8P7_RUNTIME_HANDOFF_READY_FOR_HSA7_NATURAL_OBSERVATION`：所有硬门通过、测试证据可复现、禁止边界未越界。
- `PASS_WITH_CONDITIONS`：仅非硬门文档或覆盖率缺口，且不影响 fail-closed、安全和 provenance；必须写条件工作单。
- `FAIL_HSA8P7_NEEDS_REPAIR`：任一 metadata fidelity、TWII scope/PIT、zero-call、pending retention 或 writer safety 硬门缺失/失败。
- `STOP`：缺少 execution report/实际 diff，或发现生产越界、证据不可独立复现、环境使安全审查无法完成。

即使 P7 通过，也只允许进入不触网的 HSA7 natural cron observation；在 HSA5/HSA7 真实 handoff 通过前，不得解锁 Model B、生产评分或任何 latest 自动切换。

## 10. 正式复审输出

审查者应写入：

- `POLICY_HSA8P7_FINAL_INDEPENDENT_REVIEW_CN.md`
- 若未通过：`POLICY_HSA8P8_<具体硬门>_REPAIR_WORK_CN.md`
- 若通过：`POLICY_HSA7_NATURAL_CRON_OBSERVATION_<日期>_WORK_CN.md`

在执行者完成前，本清单状态为 `WAITING_FOR_HSA8P7_EXECUTION_EVIDENCE`，不得提前输出 PASS。
