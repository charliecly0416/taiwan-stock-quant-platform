# Model B Compatibility Daily Shadow Route 主线

## 1. 路线代号

`MBCDS_MODEL_B_COMPATIBILITY_DAILY_SHADOW_ROUTE`

## 2. 目标

将已恢复并完成 direct replay 的 Phase1C `Model A + Model B` 兼容 baseline 延伸为每日只读 shadow：每日 accepted Model A 完成后，使用完全相同的 Phase1C identity、34 个输入特征和 top50-preserving blend 生成隔离 `ModelSignalArtifact`，持续积累前向排名与后续 `next_open` 评测证据。

## 3. 固定身份

- candidate: `head10_all_l31_alpha0.7_top50_only`
- model: `head10_all_l31`
- LightGBM Ranker: `num_leaves=31`、`learning_rate=0.03`、`n_estimators=120`、`random_state=42`
- blend: `0.7 * qlib percentile + 0.3 * Model B percentile`
- universe/exit boundary: Qlib top50；Model B 只重排 top50 买入顺序
- evidence class: `legacy_compatible_forward_shadow`
- `strict_pit_oos=false`、`production_allowed=false`、`default_candidate=false`

## 4. 输入合同

每日 shadow 必须读取：

1. 当日 accepted Qlib run 的完整 `prediction.csv`，不能只读取 top50，否则无法复现全截面 percentile。
2. 至少 5 个有效历史 Qlib 截面，用于 rank change/streak。
3. 与原 Phase1C 同定义的 adjusted OHLCV rolling features。
4. 覆盖当日且连续满足 20/60/120 日窗口的 TWII 与市场 breadth 输入。
5. 由冻结 Phase1 样本按固定参数物化、且通过历史逐行 score reproduction 的模型 artifact。

`available_at` 必须使用真实 job/artifact 时间，不得仅填交易日期。任何 exact-date、rolling continuity、lineage 或 checksum gate 不通过都输出 blocker，不产生 shadow score。

## 5. 阶段

1. `MBCDS0_CONTRACT_AND_INPUT_READINESS_PREFLIGHT_NO_SCORING`：冻结合同，盘点 accepted Qlib、price、TWII、历史 rank 与现有日更接点。
2. `MBCDS1_EXACT_PHASE1C_MODEL_MATERIALIZATION_AND_REPRODUCTION`：在隔离目录重建固定模型，保存 model/medians/identity，并与 Phase3A0 score 逐行复核。
3. `MBCDS2_LATEST_SHADOW_SCORE_BUILD_NO_PUBLISH`：仅在全部输入 gate 通过后生成当日标准 shadow artifact。
4. `MBCDS3_DAILY_AUTO_DISABLED_BY_DEFAULT_WIRING`：增加默认关闭、失败隔离的 daily-auto hook 和状态面，不改 cron。
5. `MBCDS4_CONTROLLED_CRON_ENABLEMENT_PREFLIGHT_OR_STOP`：观察 no-publish dry-run 后再决定是否授权 cron flag。
6. `MBCDS5_NATURAL_ACCUMULATION_AND_FORWARD_NEXT_OPEN_REVIEW`：积累至少 20 个交易日后评估稳定性；不得用历史回放替代前向证据。

## 6. 禁止边界

不得修改 provider、Qlib accepted latest、legacy latest、DAPR18 product latest、readonly snapshot latest、Agent prompt latest、cron、frontend/API default、paper portfolio default、broker/order/target。不得使用 future return、label、realized PnL 或 execution outcome 作为推理输入。不得用 strict Model B/HSA8 blocker 状态覆盖本兼容 lane，也不得把兼容 lane 宣称为 strict PIT/OOS。

## 7. Stop 条件

- exact Phase1C 模型无法复现；
- 完整 Qlib 截面不足；
- adjusted price 或 TWII exact-date/rolling continuity 不足；
- 输入字段定义与 Phase1C 不一致；
- 任何写入要求越过隔离 shadow root；
- 需要修改 cron 或产品默认但没有单独授权。

## 8. 关闭标准

模型历史 score reproduction、当日 150/150 input coverage、top50 50/50 shadow score、标准 validator、checksum、PIT/available_at、失败隔离与 protected pointers unchanged 全部通过；随后至少积累 20 个自然交易日的 forward shadow，才可讨论 production candidate gate。

## 9. 当前状态（2026-09-05）

- `MBCDS0`：完成，结论 `STOP_INPUT_NOT_READY`。
- `MBCDS1`：完成，exact 模型 `152,249/152,249` 行复现通过，最大误差 `2.22e-16`。
- `MBCDS2`：未执行；唯一 blocker 为 TWII 120-session continuity，缺 68 个 formal trading sessions。
- `MBCDS3-MBCDS5`：未进入。

下一工作单为 `MBCDS1R_TWII_CONTINUOUS_HISTORY_REPAIR_NO_MODEL_SCORING`。该修复只建立可信、不可变、连续至 target asof 的 TWII 输入，不训练或评分 Model B。
