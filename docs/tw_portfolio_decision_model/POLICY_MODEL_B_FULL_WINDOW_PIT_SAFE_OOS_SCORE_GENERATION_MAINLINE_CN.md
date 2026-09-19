---
created_at: 2026-08-24
status: coordinator_mainline
route: MODEL_B_FULL_WINDOW_PIT_SAFE_OOS_SCORE_GENERATION
current_phase: MBOOS0_PRE2023_DATA_AND_WALK_FORWARD_CONTRACT_PREFLIGHT
training_allowed: false
replay_allowed: false
production_allowed: false
latest_write_allowed: false
---

# Model B Full-Window PIT-Safe OOS Score Generation 主线

## 1. 目标

为 Model B/LTR 生成严格 point-in-time、逐折 out-of-sample 的 research-only score，优先覆盖 EMSBC 冻结窗口 `2023-01-03..2026-05-07`。每个评分日必须由训练截止日早于评分日且标签已可用的模型产生。

## 2. 非目标

- 不复用 2023-2025 训练内预测充当 OOS；
- 不依据 replay 收益选择 fold、参数、窗口或模型；
- 不运行策略、OrderIntent、ReplayResult；
- 不修改 provider、qlib、latest、cron、registry、default、前后端或 Agent；
- 不访问网络/DB/OpenAI，不连接 broker/order/target；
- 不自动扩展到 `2026-08-21`，先关闭冻结历史窗口。

## 3. 冻结方法原则

- 方法：expanding-window walk-forward；
- 标签 horizon：10 个交易日；
- purge/embargo：训练样本标签 `available_at` 必须严格早于评分 fold 首日，至少排除 fold 前 10 个交易日的未成熟标签；
- 参数：沿用已冻结 E3 `LightGBM.LGBMRanker` 参数，不做搜索；
- universe/feature：只能使用同一 E1 qlib base 与 E2 冻结的 78 feature contract；
- 重训频率、fold 边界、最小训练长度、缺失策略、tie-breaker 必须在首次训练前冻结；
- 输出逐行记录 fold、train/validation bounds、model hash、feature/qlib lineage、signal_asof、available_at；
- 1297 条 top50 availability 缺口和每日不足 150 行必须显式拒绝或在合同允许范围内形成可审计 coverage，禁止无证据填充。

## 4. 阶段计划

| phase | 目标 | 输出 | 放行 |
| --- | --- | --- | --- |
| MBOOS0 | 查明 pre-2023 PIT-safe训练样本和冻结 walk-forward 合同 | data inventory、fold plan、PIT/coverage、工作合同 | 独立审查 |
| MBOOS1 | 实现 isolated trainer/scorer 与 synthetic/golden validation | script、tests、dry-run evidence | 独立审查 |
| MBOOS2 | 执行受控 OOS training/scoring | fold models/scores/audits | 独立审查 |
| MBOOS3 | 标准 ModelSignalArtifact candidate build | candidate、validator、golden/negative | 独立审查 |
| MBOOS4 | 只读输入验收与路线收口 | closure report | 后续另开 replay route |

## 5. MBOOS0 决策

只有存在足够的 2023 年前同 contract、PIT-safe 训练样本，才能冻结 `2023-01-03` 为首个评分日。否则必须在训练前给出唯一决策：缩短为最早合法 OOS 起点并返回 EMSBC 重新冻结窗口，或 `STOP_INSUFFICIENT_PRE2023_TRAINING_DATA`。不得为了满足原窗口放宽 OOS。

## 6. 安全边界

所有模型和 score 只写 isolated research 目录，`production_allowed=false`、`research_only=true`。任何阶段均不授权 replay、latest/default switch、日更接入或真实交易。
