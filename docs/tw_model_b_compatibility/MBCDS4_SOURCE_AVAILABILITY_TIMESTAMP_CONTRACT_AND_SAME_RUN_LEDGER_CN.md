# MBCDS3-4 Source Availability Timestamp Contract and Same-Run Ledger

## 1. 目标

为 Model B compatibility shadow 建立可追溯的 source availability 时间合同，使 daily auto 可以自动判断某一日是否具有合法 PIT 输入。该路线服务于未来 Model A + Model B baseline，但不在本阶段切换 baseline。

## 2. 时间合同

每个同 run source 必须记录：

- `source_published_at`：官方来源明确提供时填写；没有时保持 null。
- `available_at`：source artifact 完成落盘并通过本地校验的时间。
- `fetched_at`：本次 source capture 完成时间。
- `decision_cutoff`：Model A/Model B 输入构建开始前捕获的 UTC 时间。

必要顺序：

```text
source_published_at (若存在) <= available_at <= fetched_at <= decision_cutoff
```

若使用 `first_successful_capture`，必须保留 observation method 和 observed_at，不能使用文件 mtime 或 score 完成时间替代。

## 3. Same-run 绑定

ledger 必须绑定 acquisition run、target asof、source family、artifact checksum 和 Model A score source run。没有显式 score-to-acquisition binding 时，即使 ranking 结构正确，也只能 quarantine。

## 4. 已实现

- daily runner 在 Model Signal gate 前捕获 `mbcds3_decision_cutoff`。
- 从 HSA8 same-run handoff 生成 `mbcds3_source_availability_ledger.json`。
- 校验每个 source 的 run/asof、timezone-aware timestamp 和时间顺序。
- bridge 只在 ledger PASS 且 score source run 明确绑定时填充 PIT 时间；否则保留 quarantine。
- 既有 Model A baseline、provider、latest、cron publish 和前后端默认均不因 MBCDS4 改变。

## 5. 验证

- 完整 source fixture：ledger PASS，并计算 combined availability/fetched time。
- available_at 晚于 decision_cutoff：`BLOCKED_SOURCE_AVAILABILITY`。
- Model A artifact 与 target asof 不一致：`BLOCKED_MODEL_SIGNAL_ASOF_MISMATCH`。
- bridge 缺 PIT 字段：不计入 MBCDS3 warm-up。

## 6. 当前状态与限制

- 标准 Model A ScoreJob 和 ModelSignalArtifact manifest 现在都写入 `source_acquisition_run_id` 与 `decision_cutoff`；daily runner 会在评分前把同一 acquisition run ID 和已冻结的 cutoff 传入。
- `mbcds3_source_availability_ledger.json` 会逐 source 校验实际 artifact SHA256、target/asof、acquisition run、时区时间顺序，并由 inventory bridge 与 ScoreJob acquisition ID 做 same-run 比较。
- 旧历史 ScoreJob/ModelSignal 没有这些字段，不能回填或推断，必须继续 quarantine；isolated Model A builder 也不能因为字段缺失而自动晋级。
- 当前真实自然 cron 仍处于周末等待，尚未形成有效 Model B warm-up 日；因此本路线不宣称 Model B 已可评分或已优于 Model A。

## 7. Baseline 目标

只有在未来产生至少 120 个有效 PIT 日，并完成同窗口、同策略、同费用、同执行价的 Model A vs Model A+Model B OOS comparison，且独立审查确认 Model B 有稳定增益后，才可提出 baseline switch review。任何收益优势都不得在证据前预先宣称。
