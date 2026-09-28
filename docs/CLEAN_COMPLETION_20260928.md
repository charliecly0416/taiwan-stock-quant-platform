> 历史阶段记录：本页保留当时的阻塞与证据。当前运行结论见 [主线验收](MAINLINE_ACCEPTANCE_CN.md)。

# Clean 主线续查完成记录：2026-09-28

本轮在 `product-clean` 工作树继续完成了可授权的修复与只读验收，没有使用 `view_image`；授权的 Yahoo-only 数据仅写入隔离 staged 目录，没有写正式 provider、切换 latest、训练模型、调用真实 OpenAI、写入正式账户或重启正式端口。

## 已完成

- Model A 基线、B19R2R shadow、策略、next-open 回放、Agent artifact 和 paper 模拟账户共用 registry、checksum 与来源边界。B19R2R 仍 `production_allowed=false`、`no_apply=true`，不会进入 paper 或默认模型。
- paper 账户增加 owner token、SQLite 持久化、预览/确认/重置、epoch 与 revision、幂等事件、并发确认、来源文件 checksum、独立导入/导出格式和原子失败回滚。历史记录接口与前端账户页已接通；写操作仍默认关闭。
- Agent 远端适配保持后端 JSON-only、无工具、无重定向、无 key 暴露；发送前只保留经过验证的日期、模型、候选排名和策略字段。snapshot payload、manifest 与 signal lineage 会交叉校验。
- 日更支持 `local_only`；候选和 Agent 产物使用隔离目录、禁止覆盖和 latest 写入。2026-05-07 的 Model A、B19R2R 与 candidate-only Agent 链已在隔离目录完整跑通，Model A 150 行、B19R2R 49 行，TW7769 未补位。
- Qlib 台湾定制源码已锁定 commit `a4179eed3d32fd21c296345fb3fba14f3e01cdaa`，提供可复现构建脚本、源码 allowlist、wheel manifest、运行依赖锁和 Docker named-context 的可选冻结模型 target。两次构建 wheel 的 SHA256 一致性可在本轮 `tmp/clean_completion_20260928/reproducible_qlib*/` 检查。

## 当前验证

| 检查 | 结果 |
| --- | --- |
| Python 全量 | 176 passed |
| 前端 Node | 11 passed |
| 前端 production build | 通过 |
| clean modules contract | PASS，57 focused tests |
| clean M3 daily isolation | PASS，7 tests |
| clean ARCH-1 descriptor | PASS |
| Playwright fixture UI | 7 页面 × 3 视口；DOM、请求、console、paper confirmation 全通过；未做像素视觉审查 |
| 历史隔离 candidate | READY；无 latest 写入 |
| Docker | 未构建：Docker Hub 基础镜像 metadata 请求超时；仅完成可复现 recipe 与 wheel 验证 |

## 2026-09-28 数据链路与 Model A 范围修正

本轮已将 Yahoo-only 抓取接入 clean daily orchestrator 的隔离 refresh 阶段。抓取源有 1,987 个登记标的，本次成功写入 1,964 个截至 `2026-09-24` 的 normalized 文件；其余标的在 Yahoo 没有可用历史。1,964 是数据覆盖和流动性筛选的输入全集，不是模型要排名的股票数量。

Model A 延续旧系统的两步口径：先用全量价格资料计算流动性候选，再取当日 Top 150 交给 Alpha158 和冻结 E1 模型打分，最后生成 Top 50 intent。使用本轮完整 staged provider 的实际推理结果为 `READY`、150 signal rows、150 full ranks、50 intents。provider 二进制构建已改为逐文件流式写入，避免把约 500 万行行情同时载入内存。

B19R2R 仍是 shadow-only（`production_allowed=false`、`mainline_blocking=false`）。新日期缺少经验证的 78 PIT 特征时保持 BLOCKED，不影响 Model A 主线。Docker Hub metadata 请求超时仍未解决，因此没有声称容器构建或正式部署完成。

随后已用当前 fingerprint 重建 Model A signal、strategy intent 和 Agent prompt 的血缘，GET-only smoke 现为 `READY`（`/api/ready` HTTP 200，Model A overview/rankings/strategy/replay/Agent 均 READY）。前端七页三视口验收为 `ui_passed=true`、`passed=true`；compare 的 B19R2R shadow BLOCKED 仍记录为 non-blocking，未使用 `view_image`。

## 仍然阻断的真实条件

当前 provider 的最新窗口仍缺 canonical Model A selection source；本轮授权的 Yahoo-only staged refresh 已让 option_c_150 的 150/150 支股票覆盖到 2026-09-24，normalized/provider validators 均 PASS，但它不能替代完整动态 universe 的流动性筛选。已发布旧信号的模型文件身份与 active baseline 不一致。B19R2R 新日期也缺可验证的 78 PIT feature producer。因此当前 `/api/ready` 和正式业务 smoke 必须保持 BLOCKED，不能伪造 2026-09-24 的新信号、改写 latest 或把错误 params.pkl 当作 canonical 模型。

正式 5000/8000 服务没有被替换，真实调度和部署没有被声称完成。需要正确的市场资料、完整 artifact 血缘以及明确的 provider/publish/deploy 操作授权后，才能进行最后的生产准入步骤。

本轮证据根目录：`tmp/clean_completion_20260928/`；授权 staged provider 证据位于 `data_tw/experiments/provider_bridge_productionization/authorized_yahoo_staged_20260928/`，前端最新只读验收位于 `tmp/clean_frontend_acceptance/`。图片只由浏览器脚本保存，未读取或传入模型请求。
