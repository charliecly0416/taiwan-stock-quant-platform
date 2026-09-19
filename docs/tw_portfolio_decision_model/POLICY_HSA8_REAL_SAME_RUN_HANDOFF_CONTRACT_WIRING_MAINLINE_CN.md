# HSA8 真实 Same-Run Handoff Contract/Wiring 主线

生成日期：2026-08-26
状态：`HSA8P3_READONLY_RUNNER_INSERTION_PREFLIGHT_STOP_NO_RUNTIME`

## 1. 目标

为真实 acquisition/provider pull 层定义一个明确的 same-run handoff 入口，并先以 isolated
fixture 验证。入口必须接收当轮真实产生的 raw/normalized exact paths，生成可由 HSA5/HSA7
消费的 authoritative `same_run_acquisition_handoff_manifest.json`。

## 2. 当前事实

- HSA7O-R3 已确认真实 daily job 没有 authoritative handoff，状态仍是
  `STOP_HSA7_REAL_HANDOFF_MISSING_OR_INVALID`。
- HSA5U/HSA6 已证明 synthetic contract 和 isolated adapter 可行，但不是真实 acquisition
  证据。
- `daily_source_inventory.json`、stdout/stderr、cache、provider/latest 不能替代 handoff。

## 3. P1 范围

允许：新增 contract/wiring helper、isolated fixture、validator tests、execution/review 文档。
入口要求：

1. 调用者显式提供 `job_root`、`acquisition_run_id`、`target_asof` 和 source records；不从
   inventory 或目录猜测文件。
2. 每个 source record 提供稳定 `source_family/source_id`、provider/request/transport、
   `source_published_at <= available_at <= fetched_at`、scope 四分区及 raw/normalized paths。
3. raw/normalized 必须是 job root 内的 regular no-follow files；入口重新读取并计算 SHA256，
   不信任调用者提供的 hash。
4. required families 为 `adjusted_price`、`twii`、`institutional_flow`、`margin_short`，
   必须唯一且完整；可保留额外 optional families。
5. 所有 source 必须绑定同一 run/asof；source validator 必须明确为 `PASS`；scope 必须无
   重复、无交叠且闭包完整。
6. 输出采用 append-only、staging、fsync、`renameat2(RENAME_NOREPLACE)`；manifest 最后写，
   输出根仅用于 isolated evidence。

## 4. P1 非目标

不得修改 daily runner 生产行为、installed cron、actual crontab、provider/formal provider、
Qlib/latest、frontend/backend production；不得运行 provider pull、网络/DB/OpenAI、训练、
评分、replay、publish 或切换任何 latest。

## 5. 后续阶段

- HSA8P1：isolated contract entry + fixture + negative tests（完成）。
- HSA8P2：isolated builder contract repair（完成）。
- HSA8P3：只读审查真实 runner 可提供的调用参数和插入位置（完成，真实 handoff 条件未满足）。
- HSA8P3A：isolated atomic parent-locator repair（完成，待独立审查）。
- HSA8P3B：final inode safe-cleanup and parent replacement repair（完成，待独立审查）。
- HSA8P3：待用户明确授权后，另行设计 runtime wiring；首次真实 handoff 仍需 HSA7 观察。
- HSA8 closure：真实 job 生成 handoff 且 HSA5/HSA7 PASS 后，才可讨论 sealed archive。

## 6. 阻断条件

任一必填字段、required family、PIT、scope、路径、hash、run/asof 绑定或 atomic install
失败即 STOP；不得降级为 inventory、stdout、cache 或 synthetic evidence。

## 7. 交付与验收

交付源码、测试、isolated execution report、review brief、文件清单和 forbidden-scope audit。
专项测试必须覆盖 valid pass、missing family、PIT、scope、path escape/symlink、hash drift、
run/asof mismatch、validator failure、existing final 和 failed atomic install。

## 8. 第一阶段命令

执行者：实现 `scripts/build_tw_model_b_hsa8_isolated_handoff_wiring.py` 及 isolated tests，
仅写 `data_tw/experiments/model_b_path2_sealed_archive_retrain/hsa8p1_*` 新目录。

审查者：独立复核 contract、no-follow/hash binding、atomic manifest、测试和 forbidden scope；
未通过前不得进入 HSA8P2。
