# Model B 重新训练、重新测试与 Baseline 纳入路线

生成日期：2026-09-11
状态：研究路线文档（适配审查修订版）；不改变当前 Model-A-only 默认，不切换任何 production/accepted latest，不触发 provider、monitor、broker 或订单写入。

## 1. 结论先行

### 1.1 Model A 与 Model B 的时间窗口不应简单重合

第一版推荐采用已经在项目中冻结过、最容易审计的时间关系：

```text
Model A / Qlib 训练：       2018-01-01 .. 2022-12-31
Model A frozen OOS score：  2023-01-01 .. 2026-05-07
Model B / LTR 训练：        2023-01-01 .. 2025-12-31
Model B untouched test：    2026-01-01 .. 2026-05-07
```

这里的“重合”要分成两层理解：

- 原始价格、市场状态和正交数据可以有重叠的历史覆盖，滚动特征也允许为 2023 年样本读取更早的 warm-up 行。
- 作为 Model B 训练输入的 Model A 分数，必须是 Model A 对 2023–2025 的 frozen OOS 输出，不能是 Model A 在 2018–2022 训练集上的 in-sample 分数。

因此，不推荐把 Model A 和 Model B 都在 2018–2022 上直接训练，然后把同一段的 Model A in-sample score 喂给 LTR。那会让 Model B 学到训练集拟合痕迹，破坏无泄漏评估。若未来必须利用 2018–2022 的全部历史，只能另立“cross-fitted Model A score”实验：每个日期的 A 分数必须由未见过该日期标签的模型产生，且不得与本路线混为同一个 baseline 候选。

上述窗口已有项目证据：

- [`EXTENDED_OOS_QLIB_ORTHOGONAL_LTR_MAINLINE_CN.md`](../tw_extended_oos_qlib_orthogonal_ltr/EXTENDED_OOS_QLIB_ORTHOGONAL_LTR_MAINLINE_CN.md)
- [`phasee3_training_manifest.json`](../../data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_manifest.json)，其中记录 `train_period=2023-01-01..2025-12-31`、`test_period=2026-01-01..2026-05-07`、`qlib_in_sample_rows_2018_2022=0`。

### 1.2 Model B 的角色

Model B 是受控的横截面 LTR reranker，而不是第二个独立选股器：

```text
Model A / frozen Qlib
  -> 产生完整截面 score/rank 与 Top50 candidate boundary
  -> Model B 读取 A 的 OOS score + 正交特征
  -> 只在 A 的 Top50 内重排买入优先级
  -> adapter 输出标准 ModelSignalArtifact
  -> 现有 strategy/replay 以同一规则消费
```

Model B 不得扩大或缩小 candidate universe，不得改变 Top50 退出边界，不得输出 `target_position`、`target_weight`、订单或真实买卖动作。当前产品仍以 Model A-only 为默认，Model B 只能先作为 research/shadow candidate。

### 1.3 针对历史 Model B 失败的硬性防复发规则

过去的失败不是单纯“模型效果不好”，而是输入和产品合同没有完全对上。本路线明确禁止以下复用：

- 当前 MBCDS3 compatibility frozen scorer 实际是 `n_features_in_=34` 的旧模型；它不能作为本次 78 维重训模型的 scorer、验证器或 baseline 证据。新模型必须在 artifact 中声明 `feature_count=78`、顺序和 transform hash，运行时精确校验，不能从 78 维静默降回 34 维。
- 不能把独立生成的 Model A Top50、正交特征表、训练模型和 annex 审计文件“按日期猜测”拼接。它们必须由同一份 handoff manifest 以 run ID、target asof、decision cutoff 和 SHA256 绑定。
- `head10_all_l31_alpha0.7_top50_only` 是唯一 canonical candidate ID；历史别名只能出现在 `candidate_aliases`，不得用于 binding、strategy dependency 或 replay join。
- Top50 必须按 `(date,instrument)` 做精确 key-set 比较，达到 50/50；不能用行数相近、排序相近、24/50 或截断后的子集冒充适配成功。
- `full_qlib_rank` 必须来自同 run 的 Model A 完整截面 rank artifact/lookup；不能从 Top50 行号、LTR rank 或压缩截面推导。
- validator 的 annex、coverage、PIT、checksum 和 mapping 审计必须绑定到同一个 manifest；脱离主 artifact 的“通过报告”不具备放行效力。

## 2. 目标、非目标与成功定义

### 2.1 本路线目标

1. 用当前 frozen Model A 的 OOS 输出和 PIT-safe 正交特征，重建可复现的 Model B 训练样本。
2. 按历史约定复现 LightGBM LTR 训练方式，不在测试集上调参或挑模型。
3. 通过 `ModelSignalArtifact` adapter 生成可被现有策略/回放读取的候选信号。
4. 在同一 universe、策略、执行价、费用税费和回放引擎下，与 Model A-only 做 paired OOS 比较。
5. 先积累 prospective shadow，再由独立 reviewer 决定是否提交 baseline admission；只有获明确授权后才能改变产品默认。

### 2.2 非目标

- 不恢复或证明过去 Model B 训练的合法性；本路线只验证新训练、数据和效果。
- 不为了改善结果修改 Model A、label、strategy rule、Top50 边界、费用税费或 replay engine。
- 不使用 2026 测试集训练、调参、早停、特征选择或模型选择。
- 不新增未经合同审查的月营收、估值、公司行动、行业或盘中数据。
- 不在本文档阶段修改 registry、日更、前端/API 默认或任何 latest 指针。

## 3. 数据与 PIT 合同

### 3.1 第一版允许的数据

Model B 输入固定为 Model A 原有 34 个 control features，加上两类已盘点的正交特征，共 78 维：

| 家族 | 内容 | 当前证据 | 第一版策略 |
| --- | --- | --- | --- |
| `control_original` | Model A 同口径技术/市场状态特征（34 维） | O4/E3 whitelist 与 hash | 必须保持原定义和 hash |
| `institutional_flow` | 外資、投信、自營、合計淨買超及 1/3/5/10 日 rolling、streak、missing/delay | O1/O2 FinMind normalized artifact | 纳入；需同 run handoff |
| `margin_short` | 融資/融券餘額、變化、rolling、方向/背離、missing/delay | O1/O2 FinMind normalized artifact | 纳入；需同 run handoff |

O2 已记录的覆盖和缺失仅作为现状，不是放行证明：institutional_flow 缺失约 0.37%，margin_short 缺失约 3.39%；O2 特征历史约从 2022-01-03 起。9/11 的新抓取虽能找到 150 个 symbol，但 `logical_acquisition.status=INCOMPLETE`、`handoff_allowed=false`，不能直接当成新的训练 FeatureArtifact。

### 3.2 暂缓的数据

`corporate_actions`、`monthly_revenue`、`valuation`、sector/industry、market-cap/shares 和 intraday 数据目前没有同时满足完整 normalized body、`available_at` 和 canonical handoff 的证据。它们可在未来单独立项，但不得为了本次 Model B 重训临时混入。

### 3.3 PIT 与 available_at

- 每一行必须带 `trade_date/asof`、`available_at`、`source_run_id`、`cutoff` 和 raw snapshot lineage。
- 正交数据默认采用“交易日后的下一个可用交易日”可见；as-of join 只允许 `available_at <= sample_date`。
- 不得使用未来收益、未来价格、forward return、realized pnl、订单、持仓或同日尚不可见字段作为特征。
- `relevance_10d_top_heavy` 只能作为训练 label，不能出现在特征表或 `ModelSignalArtifact`。
- 任何缺少可审计 `available_at` 的行必须标为不可用或进入 pending，不得静默前填。

## 4. 端到端阶段路线

每一阶段都要产生 manifest、审计文件和简短执行报告；执行者完成后由独立 reviewer 按 gate 审查。任何 gate 失败即保留 Model A-only，停止进入下一阶段。

### B0：冻结合同与实验注册

**目标**：把窗口、特征、label、回放口径和禁止事项预注册，防止事后挑选。

**动作**：

- 记录 Model A artifact、模型参数、特征 hash、score column 和完整 OOS provenance。
- 固定本路线的四段时间窗口、`relevance_10d_top_heavy`、78 维 feature whitelist、随机种子和 LightGBM 参数。
- 建立独立 run 目录；**必须**先登记 Model B registry entry，标记 `production_allowed=false`、`diagnostic_only=true`、`research_only=true`，并声明 contract、validator、positive/negative golden samples、allowed/forbidden consumers、feature dependencies 和 owner。不能以“先生成文件、之后再补 registry”作为接入路径。
- 预注册 canonical candidate ID、alias policy、模型 feature order/transform contract、训练/验证/test split、source-run handoff schema 和回放口径。

**Gate**：所有输入路径、hash、窗口和 owner 均可复核；没有生产默认变更。

### B1：源数据 source-run / cutoff / handoff 审查

**目标**：确认 institutional_flow、margin_short、Model A score、candidate universe 和所有 annex 来自可复现且互相绑定的同一次研究 run。

**动作**：

- 生成唯一的 `same_run_handoff_manifest.json`，至少包含 `handoff_schema_version`、`run_id`、`target_asof`、`decision_cutoff`、`model_a_score_run_id`、每个 source family 的 `acquisition_run_id`、raw/normalized/feature/model/candidate/annex SHA256、schema hash 和 expected row/key counts。
- 要求所有输入在 manifest 中显式列出且 ID/hash 一致；不能把“同一天”当作 same-run。Model A score 的 `source_acquisition_run_id` 必须等于 handoff 中声明的 run，或由受控 bridge 明确记录一对一映射。
- 验证时间顺序：`source_published_at (若有) <= available_at <= fetched_at <= decision_cutoff`；source cutoff 不晚于样本 `available_at`；失败的 raw acquisition 不得进入 handoff。
- 生成按 `date,instrument` 的 coverage matrix、candidate key-set matrix 和 annex binding audit，明确每个股票是否可作为完整样本以及每份审计附件是否指向同一主 manifest。

**Gate**：两类正交数据都 `handoff_allowed=true`，Model A score/candidate 与其 acquisition run、target asof、cutoff、checksum 全部一致，annex binding audit 通过；否则 B1 阻断，不用“已有本地 CSV”替代。

### B2：重建 canonical PIT-safe FeatureArtifact

**目标**：从 raw/normalized lineage 重新生成 78 维特征，而不是直接读取历史实验 CSV。

**动作**：

- 使用 O2 feature dictionary 的中性填充值和 missing/delay flags；保留原始缺失事实。
- 对 rolling 特征按 symbol、交易日排序，禁止跨股票或跨 cutoff 滚动。
- 把训练与推理 transform 固化为同一份 contract：78 个 feature name/order、dtype、neutral fill、clipping/normalization、训练 medians（如使用）和 transform SHA256。运行时不得调用旧 34 维 builder 或另一份 medians。
- 输出 `manifest.json`、`schema.json`、`features.parquet/csv`、`coverage_audit`、`pit_audit`、`forbidden_field_audit`。
- 对 2023–2025 训练期和 2026 测试期分别统计行数、symbol 数、每日覆盖和完整行比例。

**Gate**：`used_available_at_gt_sample_date_rows=0`、禁用字段为 0、schema/hash 与 whitelist 一致。缺失可以通过明确的中性值 + flag 表达，但必须单独报告。

### B3：冻结 Model A 并生成 OOS score

**目标**：保证 Model B 的 A 分数全部来自一个不再变化的 Model A。

**动作**：

- 复用当前 Model A 的 qlib 模型和 2018–2022 训练 artifact；不得在 B 路线重训或调参 A。
- 为 2023–2025 和 2026 生成同一模型的完整截面 `raw_score`、`qlib_rank`、Top50 标志和 provenance。
- 记录 `qlib_in_sample_rows_2018_2022=0`，并验证 `date,instrument` 唯一。

**Gate**：所有 A score 的 `source_model_artifact`、checksum、日期边界一致；任何 in-sample score 混入即阻断。

### B4：构建 row-aligned LTR 样本

**目标**：将 A OOS score、78 维特征和 label 在同一 `(date,instrument)` 键上拼接。

**样本口径**：

- 训练：2023-01-01..2025-12-31；测试：2026-01-01..2026-05-07。
- 训练可保留与 E3/O4 一致的完整截面分组（约 150 股票/日），让 ranker 学习横截面关系；但应用 adapter 只接受 A 的 Top50。若改成 Top50-only 训练，必须作为另一个预注册实验，不能与本路线结果混比。
- 每日先从 Model A candidate artifact 取得 canonical Top50 key-set，再与 78 维 FeatureArtifact、A score 和 label 做 inner-key audit；必须有 50 个相同 `(date,instrument)`，顺序由稳定 tie-breaker 决定。不得先截断任意一张表再声称对齐。
- 训练和测试都使用严格 `date,instrument` 对齐；同日 group 不得被拆散到不同语义。保存 group size min/median/max、expected row count 和 key-set checksum。
- 采用 complete-case 作为主分析样本；中性填充样本只做敏感性分析，不能覆盖主结果。若某日 A Top50 无法达到 50/50 正交特征对齐，则该日 treatment 进入 block，不能静默降为较小候选池。

**输出**：训练/测试 parquet 或 CSV、row split audit、alignment audit、coverage audit、label audit、score provenance audit。

**Gate**：训练没有 2026 行；测试没有 2023–2025 行；A score、candidate、features 来自同一 handoff；应用所需 Top50 每日精确 50/50 对齐、key-set checksum 一致，或明确记录阻断日。任何 24/50、49/50、重复键、排序后补行或 alias join 均 fail closed。

### B5：复现 Model B LGBMRanker

**模型合同**：

```text
model_type       = LightGBM.LGBMRanker
objective        = lambdarank
metric           = ndcg
boosting_type    = gbdt
num_leaves       = 31
learning_rate    = 0.03
n_estimators     = 120
min_child_samples= 40
random_state     = 42
n_jobs           = 2
label            = relevance_10d_top_heavy
```

只训练一个预注册 treatment，不做网格搜索、早停挑选、多模型择优或根据 2026 结果改参数。输出模型 pickle/booster、feature hash、label hash、训练日志、feature importance、train/validation metrics 和 score artifact。

模型文件旁必须保存可执行的 inference contract：`feature_count=78`、feature order、transform/medians hash、expected model family、candidate contract version 和训练样本 manifest hash。加载模型时若 `n_features_in_`、顺序、dtype、transform hash 或 manifest hash 不符，必须停止，不得自动适配旧模型。

**Gate**：配置与 O4/E3 一致；训练/验证只来自 2023–2025 内预先固定的时间切分；任何使用 2026 选择模型的行为均阻断。

### B6：ModelSignalArtifact adapter

**目标**：让 B 能被现有 strategy/replay 以标准合同消费。

**核心映射**：

```text
candidate_rank  <- Model A qlib rank
buy_score       <- Model B rerank score（仅对 A Top50）
raw_score       <- Model B 原始 score
score_rank      <- Top50 内 buy_score 降序排名
full_qlib_rank  <- Model A 完整截面 qlib rank
signal_asof     <- 信号日期
available_at    <- 通过 PIT gate 的可见时间
source_*        <- B model / FeatureArtifact / A score lineage
```

生成标准目录中的六件文件：`manifest.json`、`signals.csv`、`schema.json`、`coverage_audit.csv`、`forbidden_field_audit.csv`、`legacy_mapping_audit.csv`。如需保留诊断字段，只能使用已声明的 `ext_*`，并在 extension schema 中写明 dtype、availability、producer 和 allowed consumers；不得把 label 或未来收益放进 signal。

adapter 必须同时输出 candidate binding audit：canonical candidate ID、A Top50 key-set hash、B scored key-set hash、full-rank source path/hash、row count 和 same-run manifest hash。若 signal 只含 Top50 行，`full_qlib_rank` 仍须逐键从同 run 的完整 A rank artifact 绑定；不能使用 Top50 内序号替代。registry、strategy dependency、validator 和上述 annex 必须引用同一个 contract/version 和 artifact run，不能各自指向“最新文件”。

**Gate**：required fields、唯一键、数值类型、PIT、Top50 preservation、forbidden fields 全部通过 positive/negative golden samples；`production_allowed=false`。

### B7：严格 paired OOS replay

**目标**：回答“在同一 Model A 基础上，B 是否增加可复现的净收益或风险质量”。

Control 与 treatment 必须共享：

```text
signal dates / stock universe / Top50 boundary
strategy rule = top50_exit_one_worst_sell
target holdings = 10
execution = next_open（缺失则 pending/block）
fee_rate = 0.001425
tax_rate = 0.003
lot size / initial equity / mark-to-market / missing policy
```

必须输出 Rank IC、NDCG@10/30/50、净收益、超额收益、最大回撤、turnover、action count、fee/tax、月度/年度表现、PnL concentration、coverage 和 next-day accounting。至少同时报告 full-universe 与 common-universe；common-universe 仅用于诊断两边的共同键。若 treatment 因缺失而少于 Top50，该日只能作为 coverage sensitivity，不能计入 paired OOS、prospective gate 或 baseline 证据；baseline 主结果必须来自每日精确 50/50 的同一 candidate key-set。

**Gate**：control 可复现、treatment 只改变 Top50 内排序、执行会计通过、没有未来字段和 score 修改。

历史评估必须按证据层级分别报告，不能把所有未进入 `fit()` 的日期统称为 untouched：

```text
development_validation = 2025 validation；可作稳定性证据，不得冒充 untouched
frozen_model_retrospective_oos = 2026 已有冻结模型回放；必须声明此前是否看过指标
post_declared_window_holdout = 未进入 B9 训练/验证/测试 artifact 的后续历史日期
prospective_shadow = 模型与协议冻结后真实逐日产生的 signal/outcome
```

质量评估主门槛改为至少 `120` 个严格历史 PIT paired days。每一天都必须使用冻结 B9、保守 `available_at`、相同 A-only/A+B 股票池、精确 50/50 key-set 和相同执行会计。先应用冻结的结构性排除和 complete-case 资格，再按 Model A 全排名选出 eligible Top50；`TW7769` 以及冻结训练合同中明确不可评分的结构性缺失股票必须在形成 Top50 前排除，再由 Model A 全排名后续股票递补。不得先取 50 再留下 49，也不得只为 treatment 改变候选集。各证据层必须分别报告，并在第一次读取该批 replay outcome 后锁定模型、特征、排除规则和阈值；后续若再调参，该批日期不得继续作为确认性证据。

### B8：Prospective shadow 累积

**目标**：验证真实日更下的数据 handoff、时效、覆盖和分数稳定性，不把回看结果伪装成前瞻证据。

- 每个交易日生成 B shadow artifact，但不改变 accepted/latest、默认 API、前端或 paper portfolio。
- shadow scorer 必须加载本次 78 维模型及其 inference contract；旧 34 维 MBCDS3 scorer 只能作为历史 prior，不能混入新 B 的每日结果。
- 记录每日 source cutoff、feature transform hash、same-run manifest hash、feature coverage、Top50 50/50、candidate ID/key-set hash、validator、A/B rank diff、阻断原因和 checksum。
- `0–4` 个有效 settled days 只作链路 smoke；`5–9` 日可以审查基本抓取、绑定和结算闭环；`10–19` 日可以提交工程链路验收；`20+` 日用于持续稳定性观察。Model B 的效果判断来自 B7 的严格历史 PIT paired replay，不能由这批小样本未来日单独决定。
- 任一日 handoff、PIT 或 next-open 失败，保留 Model A-only 结果并记录 pending，不补造信号。

### B9：独立 reviewer 与 baseline admission

Reviewer 必须独立检查合同、PIT、score provenance、adapter、golden samples、replay 和 shadow 记录；执行者不能自行签署“收益提升”。

建议在 B0 预注册、不可事后修改的决策门槛：

- 至少 120 个严格历史 PIT paired days，按 development validation、retrospective OOS、post-declared-window holdout 分层报告；模型和协议在第一次读取本轮结果后保持冻结。
- 至少 10 个真实 prospective settled paired days 完成工程链路验收；20 日作为稳定性观察目标，不再要求等待 120 个未来交易日。
- treatment 在“每日精确 50/50 key-set”的 eligible paired days 上净收益差为正；common-universe 仅用于诊断，不得替代 eligible paired days。日差异的 bootstrap 置信区间或预注册统计检验不能支持“无效/反向”的结论。
- 最大回撤不得明显恶化；turnover、action count 和 fee/tax 不得以不成比例的幅度上升。
- 增益不能只来自少数股票/少数日期；需通过 PnL concentration、月度和市场状态分层审计。
- 覆盖、PIT、Top50 对齐、next-day accounting 和 checksum 无阻断日，或阻断率低于 B0 预注册的上限并有明确降级策略。

结果只能落入以下之一：

```text
supported       = 证据支持进入候选 baseline review
not_supported  = Model A-only 保持默认，B 保留研究参考
blocked         = 数据/合同/审计不完整，不能作效果结论
```

即使 `supported`，也必须另取得明确授权后，按“registry -> validator/golden -> controlled canary -> rollback pointer -> after-fingerprint review”的顺序切换；本路线本身不执行切换。

### B10：日常自动化（仅在单独批准后）

若未来正式纳入，日更顺序必须是：

```text
source refresh
  -> readiness / source-run handoff
  -> PIT FeatureArtifact
  -> frozen Model A score
  -> Model B rerank
  -> ModelSignalArtifact validator
  -> registry-declared strategy dependency / OrderIntent / readonly replay
```

日更失败时继续发布 Model A-only 的上一个合法 latest，并保留 B 的 pending job artifact；不得静默把不完整 B 结果标成可用。strategy 只能通过已登记的 dependency 消费 B 的 `ModelSignalArtifact` core fields，不能直接读模型 pickle、特征 CSV 或 annex。自动化不得训练、调参、切 accepted latest、写 monitor、连接 broker 或生成目标仓位。只有在另一个授权任务中完成 registry、cron、rollback 和生产验收后，B 才能成为每日可选候选。

## 5. 失败矩阵与处置

| 失败 | 立即处置 | 是否允许继续 |
| --- | --- | --- |
| source run `INCOMPLETE` 或 `handoff_allowed=false` | 保留旧 artifact，标记 pending，修复 source acquisition | 否 |
| same-run manifest 缺 acquisition/model/candidate/annex ID 或 SHA256 | quarantine 整个 run，不能按日期猜测拼接 | 否 |
| `source_acquisition_run_id`、target asof 或 decision cutoff 不一致 | 生成 `BLOCKED_SAME_RUN_BINDING`，回到 B1 | 否 |
| `available_at > sample_date` 或 next-day 规则不满足 | 排除该行/该日并记录；不得前填 | 仅在达到预注册覆盖门槛时 |
| A score 非 OOS、混入 2018–2022 in-sample | 作废该 run，重新生成 B3 | 否 |
| 78 维模型被 34 维 scorer/builder 加载，或 transform hash 不一致 | 立即失败；不得 padding、裁剪或使用旧 medians | 否 |
| candidate ID 使用 alias、candidate artifact 与 A score 非同源 | 拒绝 binding，重新生成 canonical candidate artifact | 否 |
| Top50 少于 50/50 | treatment 阻断；control 可单独记录 | 不得作 paired baseline 结论 |
| `full_qlib_rank` 缺完整 A rank lineage 或被 Top50/LTR rank 替代 | adapter validator fail，重新生成 broad-rank lookup | 否 |
| annex/validator 报告未绑定主 manifest/hash | 报告作废，重新运行 validator | 否 |
| 78 维 hash/schema 改变 | 回到 B0 重新注册 | 否 |
| 2026 行进入训练或调参 | 作废全部效果结论 | 否 |
| adapter 缺 core field、出现 forbidden field | validator fail，修复后重跑 | 否 |
| replay 执行价缺失 | pending/block，不能 fallback | 否 |
| 只改善毛收益、换手/回撤显著变差 | 标记 `not_supported` | 否 |
| shadow 连续缺数或 stale | 保持 Model A-only，保留 failure artifact | 否 |

## 6. 论文参考及其边界

本路线把论文作为方法背景，不把论文结果当作台股收益证明：

- `2012.07149_learning_to_rank_cross_sectional_strategies.pdf`：支持把横截面选股建模为排序问题，解释 A score + LTR rerank 的研究动机。
- `2105.10019_context_aware_ltr_self_attention.pdf`：提示市场上下文会改变排序表现；第一版仍采用可解释的 LightGBM，不直接引入 self-attention。
- `2302.10175_spatio_temporal_momentum.pdf`：支持同时考虑个股时间序列与横截面相对信息；不意味着可直接迁移论文特征或结果。
- `1904.08925_transaction_costs_systematic_portfolios.pdf` 与 `2605.01176_decision_induced_ranking_turnover.pdf`：说明费用、换手和决策诱导的排名变化必须进入评估，不能只看毛收益。
- `1707.05552_momentum_contrarian_market_conditions.pdf`：提示动量/反转效果随市场状态变化，支持分层审计，不支持直接承诺台股表现。

本地索引见 [`README_CN.md`](../../docs/references/portfolio_decision_model_papers/README_CN.md)。

## 7. Reviewer 最终清单

- [ ] A 训练窗口为 2018–2022，B 训练只用 A 的 2023–2025 OOS score。
- [ ] 2026 完全 untouched，没有参与训练、调参、选择或阈值制定。
- [ ] 正交特征来自可审计 source-run，PIT/available_at 通过，78 维 hash 固定。
- [ ] same-run handoff manifest 同时绑定 acquisition/model/candidate/feature/annex ID、target asof、decision cutoff 和 SHA256。
- [ ] complete-case 主分析与 coverage 敏感性分析已分开；每日 Top50 精确 50/50 key-set 对齐可见。
- [ ] 模型 inference contract 明确 `feature_count=78`、feature order、transform/medians hash；没有复用旧 34 维 scorer。
- [ ] canonical candidate ID 为 `head10_all_l31_alpha0.7_top50_only`，alias 未参与任何 binding 或 replay join。
- [ ] LGBMRanker 配置、label、grouping 与预注册合同一致。
- [ ] adapter 保留 A 的 `candidate_rank/full_qlib_rank`（后者来自同 run 完整 rank artifact），B 只改变 Top50 内 `buy_score/score_rank`。
- [ ] ModelSignalArtifact 六件文件、extension metadata、positive/negative golden samples 通过。
- [ ] negative golden samples 覆盖 34/78 feature mismatch、same-run/hash mismatch、24/50 或 49/50、alias candidate、缺 broad rank、未绑定 annex 等历史失败模式。
- [ ] control/treatment 使用同一策略、执行、费用税费、回放和初始资产口径。
- [ ] 已有至少 120 个严格历史 PIT paired days，并按证据层级分开报告；已有至少 10 个真实 prospective settled days 验证工程链路；没有收益承诺。
- [ ] registry 明确 `production_allowed=false` 直到专项放行；当前 Model-A-only 默认、前端/API、cron 和 latest 指针未被本路线改变。

## 8. 执行时的证据落点与只读命令

建议所有运行写入独立目录，例如：

```text
data_tw/experiments/model_b_retrain_YYYYMMDD/<run_id>/
```

每个 run 至少保存：`run_manifest.json`、输入 artifact checksum、source/cutoff ledger、feature schema/hash、row/alignment/coverage/PIT audit、训练配置、模型文件、score 文件、ModelSignalArtifact 六件文件和 reviewer report。不得覆盖当前 Model-A-only 的 latest 文件。

在 B6 之后可运行的只读检查（参数以仓库脚本当前帮助为准）：

```bash
python scripts/validate_tw_modular_m_contracts.py --run-golden --json
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_daily_orchestrator_m3.py \
  --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/validate_tw_frontend_readonly_m4.py --json
```

若 validator、golden sample 或 regression 失败，修复并产生新 run；不得手工编辑已生成的 signal 或把失败结果写入 latest。只有 B9 独立 reviewer 给出 `supported` 且获得另一个明确授权任务后，才可以设计 controlled canary；该 canary 的写入目标、rollback copy、before/after fingerprint 和 publish 开关必须另行确认。

## 9. 本路线完成判定

本文档完成只表示“重新训练 Model B 的执行顺序和审查门槛已经明确”。它不表示 Model B 已训练、已证明有效或已接入 baseline。下一次实际执行应从 B0 开始，先做只读合同与可行性审计；只有 B1–B6 全部通过，才允许进入回放和 prospective shadow。
