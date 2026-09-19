# MBCDS3 Model B Compatibility Shadow Daily Accumulation and Warm-up Gate

生成日期：2026-09-05

## 1. 目标

在不影响现有 Model A baseline 和产品链路的前提下，从新的完整交易日开始，持续积累 Model B compatibility shadow 所需的 Model A ranking、PIT-safe feature input 和 lineage evidence，并在达到预设有效日数前保持 shadow-only。

## 2. 当前事实

- 当前 Model A baseline：`e4_frozen_qlib_2018_2022`。
- Model B 是 `lightgbm_lambdarank` compatibility shadow，不是当前 production default。
- `2026-08-27`、`2026-08-28`、`2026-08-31` 没有可证明 PIT 的 ranking artifact，必须保持 `UNKNOWN/QUARANTINED`。
- `2026-09-01..2026-09-04` 有结构有效的 Model A ranking，但缺少 `available_at`，不能直接用于严格 Model B 连续窗口。

## 3. 非目标与禁止事项

本路线不做：

- Model B 训练、调参或正式评分；
- 历史缺失日期填充、回退或伪造；
- 修改 canonical `TWII.csv`、formal provider、accepted latest、legacy latest；
- 修改生产 cron、frontend/backend default、Agent、strategy replay、OrderIntent、broker/order/target；
- 以 Model A 分数冒充 Model B 分数；
- 使用 future return、label、realized PnL 或未来价格。

## 4. 设计原则

每个有效交易日必须由同一个 run 绑定以下 evidence：

```text
provider/source candidate
-> Model A inference input
-> Model A prediction/ranking
-> Model B feature input
-> optional Model B shadow score
```

每个 artifact 必须携带 `asof`、`signal_asof`、`available_at`、`source_run_id`、source/model checksum 和 universe checksum。任一 gate 失败则记录 `BLOCKED`，保留前一日有效累计状态，不补值。

## 5. Warm-up gate

- `0..19` 个有效交易日：只允许输入与 lineage accumulation，Model B score 仍关闭。
- `20..59` 个有效交易日：允许 isolated no-publish shadow score 和诊断，但不得作为 baseline 或策略证据。
- `60..119` 个有效交易日：允许形成初步 OOS comparison package，仍不得切换默认。
- `>=120` 个有效交易日：才可提出正式 baseline candidate review；不自动切换。

有效日必须同时满足：完整 universe、无 duplicate、finite score/rank、固定 lineage 一致、逐日 `asof`/`available_at` 合法、same-run handoff 完整。

## 6. 阶段计划

### MBCDS3-0 Contract Freeze

冻结状态机、累计文件 schema、缺失日政策、warm-up 计数和 forbidden scope。

### MBCDS3-1 Daily-auto Shadow Wiring

为 daily-auto 增加 shadow-only candidate builder/状态入口；失败时只写 isolated status，不改变现有 production latest。是否安装 cron 需另行授权。

### MBCDS3-2 Accumulator and Validator

按交易日追加 immutable daily evidence，执行 same-run、PIT、lineage、universe、rank completeness 和 checksum 校验，生成 warm-up readiness。

### MBCDS3-3 Readonly Observation and Closure

观察自然 cron，核对连续有效日、缺失/隔离日和 protected boundary；只有达到 gate 才产生 review candidate，否则保持 shadow blocked。

## 7. 允许写入范围

默认只允许：

```text
docs/tw_model_b_compatibility/
data_tw/experiments/model_b_compatibility_daily_shadow/mbcds3_*/
```

第一阶段不得修改 daily-auto script、cron、provider、latest、frontend/backend。涉及 wiring 的阶段必须另有明确授权和 before/after fingerprint。

## 8. 执行者与审查者职责

执行者只能实施当前阶段，必须报告命令、输入、输出、checksum、protected fingerprints 和 forbidden-scope audit。

审查者必须独立验证合同、PIT、缺失日政策、warm-up 计数和边界；不能因“已有 Model A 结果”而放行 Model B。

## 9. 第一阶段闭环条件

MBCDS3-0 只有在以下内容齐全后通过：

- contract/schema/state machine；
- valid-day 与 quarantined-day 定义；
- warm-up thresholds；
- daily-auto integration boundary；
- validator/test plan；
- 明确 `production_allowed=false`、`can_score=false` 直至后续 gate。

## 10. 第一条执行命令

执行者：阅读本主线和既有 MBCDS1R/MBCDS2 证据，生成 MBCDS3-0 isolated contract package，不修改生产脚本。

审查者：独立检查 package 是否能保证每日自动积累、缺失日 fail-closed、未来信息隔离和 baseline 不受影响。
