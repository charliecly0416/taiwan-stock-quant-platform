# 仓库物理瘦身与恢复报告

日期：2026-09-18。结论：两阶段物理瘦身已完成，删除项均有仓库外、权限受控且通过逐文件哈希验证的恢复包；Model A 稳定运维链、B19R2R 研究影子链和模块合同未被删除。

## 范围与原则

- 只删除已经退出当前运行、测试、配置、cron、systemd、CI、核心文档和进程闭包的历史材料。
- 前后端仍在 import/router 闭包内的继承模块保留；后续只有先建立产品 profile 和替代入口，才可继续物理拆除。
- 未跟踪文件不能依赖 Git 恢复。每批删除前均记录路径、大小、权限和 SHA256，并在仓库外创建 tar 归档。
- 归档在隔离目录解包后逐文件比对 SHA256；校验完成后才删除原路径。

## Phase 1：历史文档与缓存

- 删除 `docs/tw_portfolio_decision_model` 中不再被当前代码、测试、配置和核心文档引用的历史文档 1376 个。
- 删除可再生缓存目录 90 个；测试后重新生成的缓存不属于产品源码。
- 备份文件 2347 个，原始大小 34,344,165 bytes。
- 备份目录：`/home/chuliyang/backups/tw-stock/repo_slimming_20260918_phase1`
- tar SHA256：`8fe848cbd9cb3df77acc8700c3a8839b9013b92c5f706e94004c336802c75b20`
- 2347/2347 个文件通过隔离恢复哈希验证。

## Phase 2：历史实验脚本

- 初始命名模式命中 173 个脚本；其中 14 个仍属于生产闭包、2 个属于测试闭包，全部保留。
- 删除 157 个无活动入站引用的历史实验脚本，共 5,170,616 bytes。
- 删除前扫描覆盖 Python AST、源码和测试文本、配置/registry、核心文档、CI/package/Docker、live cron、89 个 systemd unit、运行进程和动态构造风险。
- 备份目录：`/home/chuliyang/backups/tw-stock/repo_slimming_20260918_phase2`
- tar SHA256：`46d5d50b844d6fb31a0be3afc6f9223e4c3f7f4bae66ff14b1077f76c1a0a143`
- 157/157 个文件通过隔离恢复哈希验证；目录权限为 `0700`，文件权限为 `0600`。

109 个退休脚本仍被 584 份历史研究材料提及。这些引用不在运行闭包内；需要精确复现实验时，先按 Phase 2 备份中的 `RESTORE.txt` 恢复。

## 最终缓存清理

完整验收重新生成 21 个缓存目录。安全扫描后，其中 18 个目录不含凭据模式，先完成精确备份和隔离恢复验证，再物理删除：

- 备份目录：`/home/chuliyang/backups/tw-stock/repo_slimming_20260918_final_caches`
- tar SHA256：`554a81cdfb4df637035b74d0df8c4c572e94c6343615a706e2c03671737454b0`
- 214/214 个文件通过隔离恢复哈希验证，备份不含明文数据库连接串。

另外 3 个 `__pycache__` 目录包含“带认证信息的 PostgreSQL URL”字节模式。为遵守备份安全门禁，没有为它们建立明文归档，也没有删除：`backend/app/utils/__pycache__`、`backend/tests/__pycache__`、`tests/unit/__pycache__`。这些是运行与测试自动生成的本地缓存，不属于源码或发布资产；保留不会影响模块边界和项目运行。

## 恢复

Phase 1：

```bash
tar -xzf /home/chuliyang/backups/tw-stock/repo_slimming_20260918_phase1/payload.tar.gz \
  -C /home/chuliyang/taiwan-stock-quant-platform
```

Phase 2 使用备份目录中的 `RESTORE.txt`，它会先校验 tar SHA256，再恢复并逐文件复核 manifest SHA256。

## 验证证据

- `tmp/runtime_physical_slimming_manifest_phase2_final_20260918.json`
- `tmp/runtime_physical_slimming_validation_phase2_final_20260918.json`
- `tmp/runtime_physical_slimming_phase2_final_reference_scan_20260918.json`
- `tmp/runtime_physical_slimming_phase2_deletion_evidence_20260918.json`
- `tmp/deployment_acceptance_after_repo_slimming.json`
- `tmp/deployment_acceptance_after_repo_slimming_phase2.json`
- `tmp/modular_contract_regression_after_slimming/regression_summary.json`

最终 runtime manifest 为 3917 条记录，包含补齐的运维入口和 `generate-secret-key.sh` 部署工具，schema 与独立重建 validator 均通过。扩大定向回归 328 项、研究栈 89 项、ARCH-1 34 项、M3 和模块合同回归均通过；前端生产构建完成 2338 个模块。5000 live 验收保持 7 个只读 GET 为 200、12 个写方法为 405，Model A 日期仍为 2026-09-18。

当前原则仍是 fail closed：未能证明无依赖或无法满足备份安全门禁的文件继续保留。缓存目录不计入产品源码。
