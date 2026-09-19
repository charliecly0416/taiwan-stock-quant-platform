# 项目运行时收敛与 Model B Baseline 纳入主线

版本：v1.0
日期：2026-09-07
统筹状态：新窗口可直接接手

## 1. 主线目标

本主线同时解决两个问题：

1. 将现有项目从多条阶段路线、多套运行时语义收敛为少数稳定模块，降低维护和扩展成本。
2. 在不破坏现有 Model A、历史实验和只读前端的前提下，让 `Model B = orthogonal LTR` 具备进入正式 baseline 的可审查路径。

最终目标 baseline 为：

```text
Model A: e4_frozen_qlib_2018_2022
Model B: e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
策略:    top50_exit_one_worst_sell
执行:    next_open
产品形态: readonly research + candidate display + simulation-only paper portfolio
```

最终 baseline 不是“Model B 文件存在”，而是一个经过同一日期、同一股票范围、同一策略和同一费用口径验证的组合信号链路。

## 2. 当前事实冻结

截至 2026-09-07，必须以实际 artifact 和 job evidence 为准：

| 项目 | 当前状态 | 解释 |
|---|---|---|
| Model A product latest | 可用，最近证据为 2026-09-04 | 当前实际产品 signal latest |
| Model B historical readonly | 可用 | 只能作历史参考和兼容比较 |
| Model B prospective shadow | 已实现，尚在积累 | `accepted_valid_day_count=0`，尚未达到评分门槛 |
| Qlib + LTR baseline | 尚未放行 | registry 登记不等于 active baseline |
| 自动日更 | 部分可用 | Model A 具备历史运行证据，但当前 cron 安装状态和最新数据状态必须可观测、可验证 |
| 实盘交易 | 永久不在本主线范围 | 只允许 readonly 和 simulation-only paper portfolio |

当前不得将以下内容写成 Model B 已证明优于 Model A：旧实验、in-sample、smoke、strict_pit_oos=false、缺失 paired 日期的回放结果。

### 历史 provenance 处理原则

对于最初 Model B 训练和历史回放，统筹接受项目负责人的明确声明：当时的数据隔离、数据可用性和测试过程按当时约定正确执行。后续工作不再以“找不到旧记录”为理由反复追溯、重建或否定这些历史过程。

这些声明和历史结果保留为 `declared_legacy_prior`，但新生产准入仍必须回答一个不同的问题：在当前可复现的 PIT-safe 数据、当前 ModelSignalArtifact 合同和当前统一回放口径下，Model A+B 对新数据是否继续优于 Model A-only。重点从过去的证据追责转为未来和当前数据的效果验证。

## 3. 非目标与保护边界

本主线不做以下事情：

- 不删除或覆盖历史实验 artifact。
- 不把 Model A latest 直接替换成 Model B。
- 不自动训练、调参或按收益挑选参数。
- 不连接 broker，不生成真实订单、目标仓位或 quick-trade。
- 不把缺失数据或 synthetic fixture 计入 Model B 的新数据效果验证；历史兼容结果可以作为 declared prior 展示，但不冒充新的验证样本。
- 不继续新增一个“阶段一个脚本”的长期结构。
- 不在前端直读实验 CSV 或私有模型文件。
- 不通过修改 validator 使不合格结果变成合格。

Model A latest、legacy latest、provider、readonly snapshot、Agent prompt latest 都必须有 before/after fingerprint。除明确授权的独立阶段外，均不得改写。

## 4. 收敛后的目标架构

稳定运行时只保留以下六个 stage。阶段编号和历史 route 名称只能出现在 evidence 元数据，不得成为业务逻辑分支的主要抽象。

```text
AcquisitionStage
  -> ReadinessStage
  -> SignalStage (Model A + Model B shadow/active)
  -> StrategyStage
  -> ArtifactPublishStage
  -> OpsStatusStage
```

模块职责：

| 模块 | 输入 | 输出 | 允许行为 |
|---|---|---|---|
| Acquisition | provider/raw source | normalized source inventory | 抓取、缓存、来源和可用时间记录 |
| Readiness | source inventory、calendar、same-run ledger | readiness gate | PIT、scope、checksum、calendar 判定 |
| Signal | FeatureArtifact、frozen model | ModelSignalArtifact | Model A 生产信号；Model B shadow 或 active 信号 |
| Strategy | ModelSignalArtifact、PortfolioState | OrderIntentArtifact | `top50_exit_one_worst_sell` 的只读/模拟意图 |
| ArtifactPublish | 已验证标准产物 | latest/read-only artifacts | 只在 gate 和授权满足时发布 |
| OpsStatus | 全部 stage 状态 | job summary、dashboard、blocker | 汇总、告警、重试提示，不掩盖失败 |

目标代码边界：

- 日更入口只负责顺序、依赖、失败策略和状态汇总。
- 数据抓取、Model A、Model B、ledger、publish 各自拥有独立模块 API。
- 前端通过统一 API 读取 artifact，不感知文件目录和 route 历史。
- 后端按 `ops`、`context`、`replay`、`paper`、`agent` 分组路由。

## 5. 阶段计划

### ARCH-0：实际运行时与 baseline truth 冻结

目标：建立唯一事实清单，不改行为。

执行者必须核对：

- active latest 的 model、asof、run_id、checksum；
- Model A/B registry、artifact 目录、fallback 目录和模型 SHA256；
- installed cron 与实际 crontab 的差异；
- 最近 20 次 daily/full job 的状态、blocker、latest 前后值；
- provider calendar、raw source、same-run inventory 的覆盖关系；
- 前端默认模型、策略、API 实际调用路径；
- 所有 protected pointer 的 fingerprint。

输出：`ARCH0_RUNTIME_TRUTH_INVENTORY.json` 和执行/审查报告。

通过条件：事实可以由本地 artifact、job log、registry 和 API 代码互相交叉验证；不得用文档推测替代事实。

### ARCH-1：唯一 baseline descriptor 与 Model Registry 收敛

目标：消除“registry 登记、active latest、readonly、shadow”语义混淆。

建立 `ActiveBaselineDescriptor`，至少包含：

```yaml
active_baseline:
  model_a: e4_frozen_qlib_2018_2022
  model_b: null
  status: MODEL_A_ONLY
  strategy_rule: top50_exit_one_worst_sell
  execution_price_mode: next_open
shadow_models:
  - id: e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
    status: PROSPECTIVE_SHADOW
    allowed_consumers: [research, readonly_comparison]
```

只有该 descriptor 能决定 active、shadow、eligible 和 production default。旧 ID 必须映射到 canonical ID，不能继续在 runtime 里分别判断。

### ARCH-2：日更编排行为保持不变的拆分

目标：拆分现有约 7,500 行日更脚本，但不改变默认输出。

拆分顺序：

1. 抽出 acquisition/readiness。
2. 抽出 Model A signal adapter。
3. 抽出 Model B compatibility shadow adapter。
4. 抽出 artifact publish 和 rollback/fingerprint。
5. 最后让原入口成为薄 orchestrator。

每一步都必须通过旧 golden fixtures、no-publish dry-run、失败 fail-open/fail-closed 语义和 latest parity 比较。任何 parity 差异先停止，不以“结果看起来一样”放行。

### ARCH-3：前后端边界收敛

目标：降低 god component 和路由聚合风险。

前端拆分为：

- `useDailyOpsStatus`；
- `useSignalContext`；
- `useReadonlyReplay`；
- `usePaperPortfolio`；
- `useAgentContext`；
- 对应 focused panels。

后端拆分为：

- `tw_stock_ops_routes`；
- `tw_stock_context_routes`；
- `tw_stock_replay_routes`；
- `tw_stock_paper_routes`；
- `tw_stock_agent_routes`。

只读 GET API、只读模拟 POST、账户写入 POST 必须在命名和 validator 中明确区分。

### ARCH-4：source、generated、evidence、archive 生命周期治理

目标：处理大量 untracked 文件和历史 route 文档，但不删除证据。

四类目录必须明确：

```text
src/       可维护源代码和配置
generated/ 自动生成但可重建的产物
evidence/  执行、审查、checksum、job 证据
archive/   已关闭路线及其索引
```

先生成 inventory 和迁移映射，再做移动；禁止直接删除或批量重命名未知文件。版本库应能清楚区分必须 review 的源码和可以重建的数据。

### ARCH-5：收敛后全链路验收

必须同时通过：

- Python compile 和 focused unit tests；
- modular contract regression；
- frontend readonly static validation；
- frontend desktop/tablet/mobile E2E；
- daily no-publish dry-run；
- failure injection：provider stale、calendar gap、missing next-open、Model B failure；
- protected latest unchanged audit；
- baseline descriptor 与 active latest parity。

ARCH-5 通过后，项目才进入“收敛后的稳定运维”阶段。此时不允许再以临时 route 方式修改核心运行时。

## 6. Model B 纳入 baseline 路线

Model B 的目标是加入 baseline，但必须采用“接受历史成果声明、验证当前新数据效果、先 shadow、后人工切换”的方式。旧训练过程不再作为本路线的主要审查对象。

### MB-0：身份与输入合同统一

固定 canonical identity：

```text
model_id: e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
model_family: e1_frozen_qlib_plus_e3_orthogonal_ltr
role: model_b_ltr_rerank_model_a_top50
```

固定组合口径：

- Model A 先生成全市场 rank；
- Model B 只能重排 Model A top50；
- 不得改变 candidate universe；
- `full_qlib_rank` 只能来自 Model A；
- 所有输入必须有 `signal_asof`、`available_at`、source manifest、feature manifest 和 checksum。

### MB-1：当前标准新数据验证与 prospective shadow

继续使用 MBCDS3-5 ledger。验证对象是当前可用的新数据和未来自然日，不要求重新证明历史训练日；每个新验证日仍必须满足：

- same-run source inventory 通过；
- PIT 和 available_at 通过；
- Model A 与 Model B 输入日期一致；
- 没有重复、晚到修订或跨日复用；
- next-open 可独立取得；
- signal ledger 与 outcome ledger 分离。

门槛（仅用于真实日更工程链路验收，不承担主要效果判断）：

| 有效日数 | 允许结论 |
|---:|---|
| 0-4 | 链路 smoke；不得下效果结论 |
| 5-9 | 可审查抓取、same-run、PIT、评分和结算闭环 |
| 10-19 | 可提交工程链路验收；效果结论仍以严格历史 PIT replay 为主 |
| 20+ | 持续稳定性观察，不是 baseline 效果的替代证据 |

### MB-2：A-only 与 A+B 在新数据上的效果比较

两个组合必须使用完全相同的：

- signal dates；
- stock universe；
- strategy rule；
- initial equity；
- target holdings；
- fee、tax、lot size；
- next-open execution；
- mark-to-market 和缺失处理。

最低报告必须包括：

- paired days；
- Rank IC；
- 净收益和超额收益；
- 最大回撤；
- turnover、fee、tax；
- 月度和 regime 稳定性；
- 缺失、quarantine、失败日数量；
- A+B 是否在统计和经济意义上都改善。

Model B 质量评估改用至少 120 个严格历史 PIT paired days，按 `development_validation`、`frozen_model_retrospective_oos`、`post_declared_window_holdout` 分层报告。历史日期必须使用冻结 B9、保守 available_at、精确 50/50 key-set、相同费用与执行；第一次读取本轮结果后禁止继续用这些日期调参。真实新数据继续 paired settlement，但主要验证自动链路，而不是等待 120 个未来交易日后才开始判断模型。

不能只看单日或单个窗口的收益；若 Model B 只提高收益但显著增加换手、回撤、数据依赖或结果不稳定，仍不得纳入 baseline。

本阶段的核心判断顺序是：

```text
当前标准数据是否能稳定生成 A+B
  -> A+B 是否在相同口径下优于 A-only
  -> 提升是否覆盖费用、回撤和换手风险
  -> 是否可以进入 shadow baseline
```

如果新数据验证持续支持 A+B，历史记录不完整不会成为继续研究或候选 baseline 的阻塞；它只会影响 provenance 标签，不能被表述为完整历史复现证明。

### MB-3：Exact replay 与独立审查

达到至少 120 个严格历史 PIT paired days，并完成至少 10 个真实 prospective settled days 的工程链路验收后，执行独立 exact replay：

- 不重新选择参数；
- 不使用 outcome 回写特征或排序；
- 不改变费用和成交价口径；
- 对 A-only、A+B 使用同一 replay engine；
- 输出完整 manifest、checksum、comparison 和 blocker register。

审查结论只能是：`PASS`、`PASS_WITH_CONDITIONS`、`FAIL_NEEDS_REPAIR` 或 `STOP`。

### MB-4：单次授权纳入 baseline

只有 MB-0 至 MB-3 全部通过，且人工明确授权后，才能：

1. 更新 `ActiveBaselineDescriptor` 的 `model_b` 和 status；
2. 生成新的 A+B canonical ModelSignalArtifact；
3. 更新 readonly snapshot 和 frontend context；
4. 进行一次 controlled latest switch；
5. 保留 Model A-only latest 作为 rollback baseline；
6. 执行 post-switch parity、checksum 和 UI/API 验收。

不得由 daily cron 自动完成这次切换。切换必须有 exact target、before fingerprint、rollback copy、after diff 和独立审查。

## 7. 纳入后的日常运维路线

收敛和 Model B 正式纳入后，工作日每次日更固定执行：

```text
1. 选择最近已完成交易日 target_asof
2. 抓取/读取 raw source，并记录 available_at
3. 完成 source scope、PIT、calendar、checksum readiness
4. 生成 Model A signal
5. 生成 Model B LTR rerank signal
6. 验证 A+B same-run、top50 universe 和 ModelSignalArtifact
7. 生成 strategy/read-only context
8. 生成 next-open execution readiness
9. 通过 publish gate 后更新产品 readonly artifacts
10. 写入 job summary、dashboard、lineage 和 failure reason
```

日更的失败策略：

- raw/provider/calendar 失败：保留上一份有效 latest，标记 stale/block，并重试；
- Model A 失败：不发布新 signal，明确阻断产品 latest；
- Model B 失败：在 baseline 切换前不得阻断 Model A；切换后必须按 active baseline policy 决定是否回滚到 A-only，但不能静默混用；
- readonly snapshot 或 Agent prompt 失败：保留上一份 pointer，并在 dashboard 标为 downstream stale；
- 任意 forbidden action 非 false：整次 publish STOP。

每天必须能回答：

```text
今天数据更新到哪一天？
A 与 B 是否使用同一批输入？
A+B 是否真的生成并通过验证？
前端展示的是哪个 baseline？
哪一个 stage 阻断？下一次何时重试？
```

## 8. 运维状态定义

统一状态如下：

- `HEALTHY_ACTIVE_AB`：A+B active，所有必需产物同日且验证通过。
- `HEALTHY_ACTIVE_A_SHADOW_B`：A active，B shadow 正常积累。
- `STALE_RETAINED`：保留上一份 latest，等待数据或下游恢复。
- `BLOCKED_INPUT`：输入合同、PIT、calendar 或 checksum 不通过。
- `DEGRADED_DOWNSTREAM`：signal 有效，但 readonly snapshot、Agent 或 execution readiness 落后。
- `STOP_FORBIDDEN_ACTION`：检测到越界写入或未授权动作。

“程序没有异常退出”不等于 `HEALTHY_ACTIVE_AB`。

## 9. 执行者与审查者规则

每个阶段必须由同一统筹下的执行者和独立审查者完成：

### 执行者

- 只执行当前阶段；
- 先读主线、合同和工作单；
- 只写允许路径；
- 记录命令、artifact、checksum、测试和 blocker；
- 遇到缺输入或范围不清立即 STOP。

### 审查者

- 独立检查实际 diff、artifact 和运行结果；
- 不接受“代码存在”作为行为通过证据；
- 检查 forbidden scope、latest fingerprint 和回滚能力；
- 输出 `PASS`、`PASS_WITH_CONDITIONS`、`FAIL_NEEDS_REPAIR` 或 `STOP`；
- 必须给出下一阶段工作单，不能口头扩展路线。

## 10. 首个执行命令

新窗口接手后，第一步只做 ARCH-0，不修改代码、cron、provider、latest 或前端默认值：

```text
进入 ARCH-0_RUNTIME_TRUTH_INVENTORY_NO_WRITE。
起执行者和独立审查者；只读盘点 active latest、Model A/B registry、最近日更 job、installed/actual cron、provider calendar、前端/API 实际默认值和 protected fingerprints；输出 ARCH0 inventory、执行报告和审查报告。不得训练、抓取、publish、切 latest、改 cron、改前端默认或改 baseline。
```

ARCH-0 通过后才进入 ARCH-1。不得跳过架构事实冻结直接重构，也不得在至少 120 个严格历史 PIT paired days 和至少 10 个真实 settled prospective days 都通过审查之前把 Model B 写成 active baseline。

## 11. 路线结束条件

本主线全部结束需要同时满足：

1. ARCH-0 至 ARCH-5 通过，运行时和模块边界完成收敛。
2. `ActiveBaselineDescriptor` 成为唯一 active/shadow 事实来源。
3. Model B 达到至少 120 个严格历史 PIT paired days，并达到至少 10 个真实 settled paired prospective days 的工程链路验收门槛。
4. exact replay、费用/成交价/coverage/regime 审查通过。
5. Model A-only rollback artifact 仍可验证和恢复。
6. 一次 controlled A+B latest switch 完成并通过 API/前端 readonly 验收。
7. 至少连续若干个工作日的 `HEALTHY_ACTIVE_AB` 自然 cron evidence 通过。
8. 后续进入维护状态，只修复运行问题，不再新增同类阶段 route。

在这些条件完成前，准确表述应为：

> Model A/Qlib 是当前 active baseline；Model B/LTR 是受合同约束的 prospective shadow，目标是通过本主线完成可回滚、可审查的 baseline 纳入。
