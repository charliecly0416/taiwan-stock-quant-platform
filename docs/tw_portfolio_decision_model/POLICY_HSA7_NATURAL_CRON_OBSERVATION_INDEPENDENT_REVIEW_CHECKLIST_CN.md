# HSA7 Natural Cron Observation 独立审查清单

状态：`PENDING_EXECUTOR_REAL_NATURAL_RUN_EVIDENCE`

## 1. 当前判断

本轮只读检查未发现新的 HSA7 natural observation scheduled-run evidence；现有目录主要是 HSA7/HSA7O 预检或历史 daily job。当前 `crontab -l` 未返回可审查条目，因此不得把旧 job、离线 fixture 或执行报告当作本轮 natural run。

## 2. 执行者必须提交

- 只读定位到的 actual crontab fingerprint、cron line 和 scheduled job locator；
- 一个自然产生的、同一 job/run 的完整 evidence 根目录；
- strict candidate classification、decision、pending/STOP 状态；
- same-run manifest 及 validator 结果；
- raw HTTP response、normalized payload、adapter output 的路径、SHA256、run/asof/source 绑定；
- FinMind/TWII provider、validator、scope closure、PIT 状态；
- protected before/after fingerprints 和 forbidden-scope audit。

## 3. 独立审查门

1. 确认 job 是自然 scheduled run，不是手动重跑、旧目录复制或离线 fixture。
2. 确认 candidate 分类严格按合同执行；缺 source、scope、PIT、same-run 或 validator 证明必须 pending/STOP。
3. 确认 manifest 文件真实存在且 validator 消费的路径与 manifest 完全一致。
4. 对 raw/normalized/adapter 做独立 SHA256 和 run/asof/source/path binding 核对；cache、stdout、inventory 和旧 evidence 不得冒充 raw。
5. 确认 TWII schema 通过不自动代表 returned；FinMind unknown/PIT BLOCK 不得升级。
6. 复核 protected before/after 完全一致，禁止边界没有 provider/Qlib/latest/cron/frontend/backend 等越界变化。
7. 真实 daily downstream 调用计数与离线 spy 分开记录；离线 8×5/成功对照不能替代真实 scheduled-run 证据。

## 4. 结论枚举

只能输出：

- `PASS_HSA7_NATURAL_HANDOFF_OBSERVED`
- `PASS_WITH_CONDITIONS_CONTINUE_OBSERVATION`
- `FAIL_HSA7_NATURAL_HANDOFF_REPAIR_REQUIRED`
- `STOP_HSA7_NO_VALID_SCHEDULED_RUN_OR_BOUNDARY_EVIDENCE`

在执行者提交有效自然 run 前，不运行 daily/provider/network，不修改 cron/crontab，不发布或切换任何生产链路。
