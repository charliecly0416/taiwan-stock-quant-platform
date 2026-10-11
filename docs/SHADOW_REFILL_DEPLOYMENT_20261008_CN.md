# Shadow 递补修正部署记录（2026-10-08）

## 结果

台北时间 12:35 完成正式服务切换，运行代码为 `6139891`，目录为
`~/.local/share/tw-stock-clean/releases/clean-20261008-refill-6139891`。
Web、Model A 日更与 Shadow 服务均指向新目录。Model A 保持唯一默认基线，
B19R2R 保持 `production_allowed=false`、`no_apply=true`，不进入模拟账户。

10/7 实际数据验证成功：Model A 为 150 支，B 从其中筛出特征完整的候选，
按 A 原排名选满 50 支后重排。原 Top50 中的 TW4939 缺特征，被 A 第 51 名
TW6187 递补。当前排名、比较和问答接口均为 READY；比较重合数为 49。

## 本轮修正

- 原递补实现 `7453c14` 此前仅提交到 GitHub，没有部署到运行服务。
- `a9481cb`：部署时同步当前代码的 models 配置，避免备份中的旧候选规则覆盖新规则；保留恢复后的模型文件路径。
- `6139891`：历史特征筛选后按 A 排名截取 50 支，避免完整历史特征超过 50 行时错误阻塞。

两项修正均有回归测试；没有新增候选规则开关或替代主线。

## 验证与证据

- 部署/信号针对性测试：21 passed；ARCH-1 PASS；M3 39 passed；模块回归 71 passed。
- 运行目录执行 `verify_tw_stock_research_stack.py`：PASS。记录为运行目录的 `stack-validation.json`。
- 独立环境依赖检查、前端构建、150 支基线排名和每日问答：通过。
- 真实冻结历史样本 2026-05-07：B 输出 50 支，与 A Top50 重合 49 支。
- 临时 timer `clean-shadow-deploy-check-20261008` 触发了包含 Yahoo/FinMind 采集的完整 Shadow 流程，12:35:11 完成，READY / COMPLETED / 50 行。
- 此次临时验证明确记录 `trigger_reason=manual`、`local_only=false`，没有替换正式 scheduled 记录。
- Shadow run：`3c95cc3ee3584af3a20fab86477575c6`；其 `run.json`、特征 manifest 与信号均保存在新运行目录的 `data_tw/product/artifacts/shadow/`。
- 正式端口 `http://127.0.0.1:8000`：7 页、3 种视口浏览器验收通过。证据在源码目录 `tmp/deploy_20261008/frontend/`，网络/页面/控制台错误均为 0。
- 浏览器验收的模拟账户写流程、费用边界和导航竞态使用 fixture；没有写真实模拟账户。部署时通过 SQLite backup 接口复制现有账本。
- 截图文件已保存，但未使用图片工具、未执行人工视觉审查；布局结论来自 DOM 几何与内容断言。
- 两个代码提交的 GitHub clean-product CI 均成功。

## 备份与回退

备份根目录为 `~/.local/state/tw-stock-clean/backups/snapshots/`：

- 部署前：`20261008T042717-7accea37/manifest.json`，已在独立目录恢复验证。
- 部署后：`20261008T043637-fff61b32/manifest.json`，包含新批次和成功 Shadow。

旧运行目录 `clean-20261001-shadow-unavailable` 保留。本轮没有删除代码或资产。
回退遵循[运维手册](OPERATIONS_CN.md)，使用最新账本快照。

## 正式晚间定时验收尚待发生

截至本报告，正式 scheduled 记录仍是旧版本 10/7 的 BLOCKED，健康报告保留
`SCHEDULED_SHADOW_GATED` 警告，Model A ready 为 true。这不代表新部署已通过晚间定时验收。

当日台北时间 18:30 起运行 Model A，18:45 / 19:45 / 20:45 运行 Shadow。
已安排一次性 `clean-deployment-followup-20261008.timer` 于 21:35 GET-only 复核：
检查 10/8 基线、当日 scheduled Shadow 完整采集、50 行输出、与 A 批次绑定，以及比较接口 READY。

结果将写入 `~/.local/state/tw-stock-clean/acceptance/20261008/scheduled-result.json`。
检查脚本和临时任务位于仓库外，不改变主线调度逻辑；报告生成前不能宣称正式定时验收通过。
临时 timer 不跨主机重启持久化，原有正式 timers 继续由已安装的 systemd units 管理。

## 10/11 后续核对与优化

10/8 21:35 的 `scheduled-result.json` 为 PASS；10/8、10/9 各三轮正式 Shadow 均为 READY / COMPLETED / 50 行，10/9 使用 10/8 的 A 批次。此前待验收事项已由正式定时证据确认。

10/11 台北时间 21:57 部署 `9c63923`，新目录为 `~/.local/share/tw-stock-clean/releases/clean-20261011-shadow-reuse`。后续尝试会验证同一 A 批次的信号与特征，已有完整结果则记录 READY / SKIPPED / SHADOW_ALREADY_READY，不再重复采集与推理。`reused_run_id` 保留原成功来源；新批次、失败或损坏结果继续执行，无新增策略分支或配置开关。

本机 inotify 告警来自 VS Code fileWatcher 的约 123,863 个监听项接近用户上限 124,126，已持久化调整上限为 524,288。真实 clean-health 与临时 systemd 任务验证完成后，没有新的 inotify 额度错误；编辑器进程保持运行。

验证记录：

- Shadow 针对性测试 15 passed；M3 43 passed；ARCH-1 PASS；模块回归 71 passed；代码提交 GitHub CI 成功。
- 新目录首次以已有数据生成 50 支 Shadow；第二次真实产物复用为 PASS，用时约 0.09 秒，网络请求为 0，缓存与 active / shadow_active 指针不变。`shadow-reuse-validation.json` 保存在运行目录。
- `verify_tw_stock_research_stack.py` 为 PASS；部署后实际 API 的 A / B / 比较 / 问答均为 READY，数据日期 10/8。
- 正式 8000 端口的七页、三视口浏览器验收通过，网络/控制台/页面错误为 0，证据为源码目录 `tmp/deploy_20261011/frontend/`。模拟账户操作使用 fixture；没有使用图片工具或做人工视觉审查。
- `clean-shadow-reuse-check-20261011` 临时 timer 验证为 SKIPPED，并明确记录 manual；未伪造正式晚间 scheduled 采集。
- 部署前备份 `20261011T135135-2d817cd7/manifest.json` 已恢复验证，部署后备份为 `20261011T135740-0e4c13e9/manifest.json`，均位于上述备份根目录。
- 旧运行目录保留，模拟账本一致性复制，Model B 仍只用于研究比较。
