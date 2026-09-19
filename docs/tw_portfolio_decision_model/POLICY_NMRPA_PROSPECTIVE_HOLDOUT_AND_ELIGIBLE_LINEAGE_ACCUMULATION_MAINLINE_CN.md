---
created_at: 2026-08-21
status: coordinator_mainline
route: NMRPA_PROSPECTIVE_HOLDOUT_AND_ELIGIBLE_LINEAGE_ACCUMULATION
current_phase: NMRPA0_CONTRACT_AND_DAILY_AUTO_READINESS_PREFLIGHT_NO_TRAINING
training_allowed: false
holdout_metric_visibility_allowed: false
production_default_change_allowed: false
provider_or_latest_write_allowed: false
cron_change_allowed: false
---

# NMRPA 前瞻 Holdout 与完整 Eligible Lineage 积累主线

## 1. 目标

为未来尚未训练的 `per-symbol 10-trading-day residual downside-risk model` 建立一条独立、append-only、checksum-backed 且不可提前查看结果的 prospective research lineage，使未来研究不再依赖已被训练或披露使用的历史尾部。

本路线只生产研究 readiness 与未来数据积累能力，不训练模型、不选择算法、不计算 holdout 指标，也不改变现有产品链路。

## 2. 启动依据

NMR0/NMR0_R 已确认：

- O2/E2 历史材料具部分 PIT/as-of 审计价值；
- 旧 E2 train 缺达到 eligibility 后的 `TW7769`；
- 2023-2025 已用于 E3 train，2026 已作为测试披露；
- 当前没有项目级 untouched strict holdout；
- residual downside-risk 只能保留为 `frozen_unvalidated_hypothesis`。

因此不能通过重切历史窗口解锁 NMR1。唯一合理路径是先冻结未来积累合同，再自然等待新的、未被查看的交易日数据。

## 3. 冻结研究对象

```text
hypothesis:
  per-symbol 10-trading-day residual downside-risk model

baseline:
  frozen E1 qlib score/rank lineage

prospective inputs:
  adjusted price / Alpha158-compatible history
  TWII context
  institutional flow
  margin / short
  frozen E1 score and complete eligible cross-section

label horizon:
  10 trading days

minimum strict holdout:
  126 valid decision dates

label maturation wait:
  10 additional trading days after the final holdout decision date
```

`126` 是约半年交易日的时间独立性治理下限，不是按收益选择的窗口。未来不得因结果不佳缩短、移动或重启时钟。

## 4. 非目标

- 不训练、调参、推理候选模型或生成候选预测；
- 不生成、查看或汇总 holdout label/metric；
- 不使用已有 E3 train/test 区间冒充 prospective holdout；
- 不新增数据供应商，不改变来源许可或访问边界；
- 不修改生产 provider、qlib、accepted/legacy/product latest；
- 不修改生产默认模型/策略、前端/API、Agent；
- 不连接 broker、monitor、order、target、position、weight 或 quantity。

## 5. 数据边界

prospective lineage 必须与生产产物逻辑隔离，但可以只读引用同日已验证来源。允许的数据流：

```text
existing daily source evidence
  -> immutable prospective source references
  -> complete dynamic eligible-universe audit
  -> feature-only candidate snapshot
  -> sealed label-maturation ledger
  -> holdout completion gate
```

禁止从 readonly snapshot、Agent、strategy replay、realized PnL 或产品展示反向取数。生产 latest 不能作为唯一 lineage；每个日期必须绑定 immutable run/artifact path 与 checksum。

## 6. Dynamic Eligibility

每个 decision date 必须基于当日信息计算，不允许固定 symbol list 静默丢失：

- formal instrument 当日 active；
- E1 score 存在；
- 当日 adjusted price/tradability 存在；
- 至少 60 个历史价格观测；
- institutional/margin 缺失可按已冻结 neutral-fill + missing/asof flags 表达，但不得删掉 eligible symbol；
- rank/z-score 必须在完整 dynamic eligible cross-section 内重算；
- eligible symbol 缺行、duplicate、conflict 或 future `available_at` 任一非零即该 decision date 无效。

`TW7769` 必须在达到门槛后进入，不得以旧 E2/O3 row alignment 继续排除。

## 7. Prospective Holdout 防窥视合同

在最终 accumulation contract 通过审查前不得启动计时。启动后：

1. holdout start date 与 artifact contract 不可追溯回填；
2. 每个 valid decision date append-only，失败日期保留失败记录，不覆盖；
3. label 可在 10 日后封存生成，但研究者可见状态只能是 `pending/matured/sealed`；
4. label 值、模型指标、Rank IC、收益、TopN、校准和分组统计均不可暴露；
5. 任何提前查看结果或修改 target/features/split 都使当前 holdout 作废，必须由用户另行授权新路线，不能静默重启；
6. 完成条件为 126 个 valid decision dates 全部成熟并通过 sealed integrity review。

## 8. 阶段计划

| phase | 目标 | 输出 | 放行条件 |
| --- | --- | --- | --- |
| NMRPA0 | 合同与现有 daily-auto readiness 只读预检 | inventory、gap matrix、唯一实现路线或 STOP | 现有来源可复用；无训练/metric/生产改动 |
| NMRPA1 | candidate-only schema、eligibility、sealing 与 validator 设计 | schema/validator/golden design | 不含 label 值暴露；append-only 语义完整 |
| NMRPA2 | isolated no-cron builder implementation | builder、validator、synthetic/local golden evidence | 不运行真实日期积累；不写生产路径 |
| NMRPA3 | 单日 no-publish/no-metric dry-run | isolated candidate evidence | complete eligible universe；protected pointers unchanged |
| NMRPA4 | daily-auto hook default-off/no-cron integration | orchestration tests/status surface | default off；failure isolated；不影响产品 publish |
| NMRPA5 | cron enablement preflight/actual authorization gate | exact flags、rollback/fingerprint plan | 需用户明确授权 actual cron 修改 |
| NMRPA6 | 自然 cron 观察与 accumulation closure | 多轮自然证据、运维 runbook | 连续自然运行且 holdout 防窥视审查通过 |

NMRPA6 关闭仅表示积累链路进入运维，不能训练。训练路线必须等待 126+10 个交易日并由用户另行授权。

## 9. NMRPA0 必须回答

1. 现有 daily/full cron 是否每天生成完整 E1 Model A score，immutable run path 与 checksum 是否可引用？
2. price/TWII 是否按日追加并具 60-day history、active range 与 PIT 证据？
3. institutional flow 与 margin/short 的 daily/full/batch 语义、quota、覆盖和失败重试是否足以形成逐日 lineage？
4. 当前 orthogonal `captured` 状态是否只是运维证据，还是已有 feature-level payload binding？
5. 是否存在 append-only research root、complete eligibility audit、sealed label ledger 和 no-metric validator？
6. NMRPA hook 能否与 DAPR18/QALD/FPALA 隔离，失败时不阻断产品 publish？
7. 哪些部分可复用，哪些必须在 NMRPA1-NMRPA4 新建？

## 10. NMRPA0 允许写入

仅允许本主线、NMRPA0 工作单、执行报告、审查报告和 reviewer 决定的下一阶段工作单。不得修改 `data_tw/`、代码、config、cron、backend 或 frontend。

## 11. 停止条件

- 必须新增未授权数据源或依赖访问控制绕过；
- 现有 E1 score 无法持续生成完整 eligible cross-section；
- institutional/margin 来源无法以 append-only checksum lineage 表达；
- prospective holdout 无法与现有研究结果隔离；
- 必须查看 label/metric 才能判断 readiness；
- 必须修改生产 latest/default 才能积累；
- 不能保证 NMRPA 失败不影响产品 daily publish。

## 12. 首个执行命令

执行 `NMRPA0_CONTRACT_AND_DAILY_AUTO_READINESS_PREFLIGHT_NO_TRAINING`，只读盘点合同、cron/daily-auto、来源、artifact、状态面和隔离缺口；输出唯一后续实现方案或 STOP，不修改运行状态。

## 13. 审查任务

独立核对来源覆盖、PIT、eligibility、append-only、sealing、防窥视、产品隔离和 126+10 时间规则。不得把“代码里已有字段”误判为“研究积累链已完成”。
