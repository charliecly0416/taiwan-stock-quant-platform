# Stage 2 最终返回文件与下一步（r2）

GPU工作已完成并停止。24次真实2100秒窗口：C1九次整体未通过主门禁（steady三次通过，recovery/burst各三次失败）；C2九次主门禁和六次诊断通过，选定C2。C3已冻结但未性能运行。local_only recovery的offline为115/120，仅比114门槛多一条。三个off诊断没有启动期间API接受，不能声称验证了此路径。

本轮没有进入N5、PPO、Qwen训练、locked_test性能或论文修改。等待原环境独立验收和下一工作单。本说明取代旧r1交付指令，不修改主科学归档。

## 需要转交的两个私有包

文件都在 `/lustre/home/2401213359/`：

| 文件 | 字节数 | SHA256 |
|---|---:|---|
| stage2_formal_return_20260919_r1.zip | 194799248 | 47c2b026dbefbbc93a111438023dc92d7dcc876c9089946aaf29217eb0af2f32 |
| stage2_return_closeout_20260919_r2.zip | 12535948 | 415b51244fad02e2e8d3c252cc26c08a581b2aaa4dff100b819e61b96e7b7ec8 |

主包含科学RAW、全部失败、冻结输入/代码SHA、环境与停机证据、manifest/SHA256SUMS和详细中文handoff。补充r2包含主包外层记录、归档最终独立审查、I/O异常及成功补验、重定位复算、v2公开Git bundle与独立审查/发布说明。两个包都含私有证据，不能整包上传公开GitHub。

先读补充包 `RECEIVING_CODEX_zh.md`，再读主包 `docs/maxopt_stage2_execution_20260919/RETURN_HANDOFF_zh.md`。按handoff第8节在接收环境只读核验，不重新运行GPU campaign/runner，不再次生成唯一修订。文件系统读取阻塞导致的初次限制已由一次有限CPU补验解除，失败和退出记录都保留。

同时转交本清单、`stage2_return_transfer_20260919_SHA256SUMS`，以及包外最终记录：

- `stage2_formal_return_20260919_r1_archive.json` 与 `stage2_formal_return_20260919_r1_archive_review_r2.json`（已收在补充包中）。
- `stage2_return_closeout_20260919_r2_archive.json`。
- `stage2_return_closeout_20260919_r2_review.json` 与 `stage2_return_closeout_20260919_r2_review_zh.md`（补充包生成后的独立审查，包外保存）。

## 公开交付与实际传输状态

**只使用v2公开快照；不要推送旧 `gpu-stage2-return-20260919` 分支或旧bundle。** 旧审查只覆盖四文件增量，其祖先含未纳入公开审查的本地N4c资料，旧bundle也依赖未证实接收端持有的前置提交。旧推送因网络不可达失败，没有远端写入。旧尝试和r1补充HOLD审查在最终补充 `history/DO_NOT_PUBLISH_*` 中保留。

当前有效版本：

- 分支 `gpu-stage2-return-20260919-v2`。
- root commit `3fc2b5923e7c4809aba7633532285df2dd4b3cf1`，无父提交；完整树仅三份已审源码和一份聚合README。
- `stage2_public_return_20260919_v2.bundle`：7647字节，SHA256 `fb24010e032545acf2629b44111adfabcbc427921e44e38e605cf794273667aa`。无prerequisite，独立空目录clone和9项CPU单测通过。bundle和完整树审查报告已在补充包内。
- GitHub：SSH/HTTPS网络均不可达，v2尚未推送。目标 `github.com/6zzhh6/llm-scheduling`。
- 私有传输：LOCAL_READY_NOT_SENT，未提供scp接收host/user/目录，未执行scp。请将两个私有包与上述外层清单交给原环境；若希望GPU端直接发送，需要提供准确scp目标及可用连接。

在联网原仓库，核实origin后执行（PowerShell也适用）：

```powershell
git bundle verify "<补充解压目录>/stage2_public_return_20260919_v2.bundle"
git fetch "<补充解压目录>/stage2_public_return_20260919_v2.bundle" refs/heads/gpu-stage2-return-20260919-v2:refs/heads/gpu-stage2-return-20260919-v2
git push origin refs/heads/gpu-stage2-return-20260919-v2:refs/heads/gpu-stage2-return-20260919-v2
```

该分支是独立公开快照，不直接合并主线；若目标分支已存在，先核对commit，不force。接收端Python须支持冻结代码，建议python3 3.10+；本轮CPU复验为3.12.12，GPU执行环境为qwenguard_vllm。主包内较早的“未commit”及旧传输说明是归档时快照，最终状态以本说明及v2 transport.json为准。

## 最短转交prompt

> 请接收stage2_formal_return_20260919_r1.zip、stage2_return_closeout_20260919_r2.zip及包外最终审查/校验清单，先核SHA，再读补充RECEIVING_CODEX_zh.md及主包RETURN_HANDOFF_zh.md。GPU端完成24次真实窗口，C1整体失败，C2九次主门禁和六诊断通过，GPU已停止；local_only recovery offline115/120仅一条余量。请独立验收迁移确认、唯一修订、所有RAW/失败、选择/成本和停止边界；不得重新启动GPU、N5/训练或直接替换论文。初次I/O异常已有限补验解决，旧材料全部保留。公开交付只能用无前置提交的v2 bundle和gpu-stage2-return-20260919-v2分支，禁止推旧分支。公网与scp尚未完成，可在联网环境按说明发布已审v2四文件快照。独立验收后再给下一阶段工作单。
