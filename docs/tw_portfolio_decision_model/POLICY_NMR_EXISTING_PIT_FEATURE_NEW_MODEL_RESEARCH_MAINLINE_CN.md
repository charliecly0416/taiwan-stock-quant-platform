---
created_at: 2026-08-21
status: coordinator_mainline
route: NMR_EXISTING_PIT_FEATURE_NEW_MODEL_RESEARCH
current_phase: NMR0_EXISTING_PIT_FEATURE_NEW_MODEL_RESEARCH_PREFLIGHT
readonly_preflight: true
training_allowed: false
production_allowed: false
default_switch_allowed: false
provider_or_latest_write_allowed: false
daily_auto_change_allowed: false
broker_authorized: false
---

# NMR 现有 PIT 特征新模型研究主线

## 1. 目标

基于仓库内已经物化、可校验且具 point-in-time/`available_at` 证据的数据与 FeatureArtifact，寻找一个相对现有 qlib、LTR、Model A/B 具有明确增量信息、可证伪、可复现的新模型候选。

本路线先证明研究问题、输入与评估设计成立，再决定是否训练。新算法名称、复杂度或单一收益数字都不能替代增量价值证据。

## 2. 启动依据

1. MSTR 已完成现有信号策略空间盘点；唯一明确的新策略机制依赖 sector lineage。
2. SSAP 因 TPEx ordinary GET 403、stable official sector code 缺失及 `LICENSE_UNRESOLVED` 正式停止。
3. 继续微调现有规则容易重复 MTR、RSR 与 Phase P 已关闭机制；当前更合理的研究问题是现有 PIT-safe 数据能否产生与基线模型互补的新预测信息。
4. SSAP 与 MSTR 保持关闭；NMR 不使用 sector 数据，也不以新模型路线绕过其 blocker。

## 3. 非目标

- NMR0 不训练、重训、调参、打分或生成 ModelSignalArtifact；
- 不下载、抓取或引入新数据源，不访问网络、DB 或 OpenAI；
- 不修改 provider、qlib、accepted/legacy/product latest、daily auto 或 cron；
- 不修改生产 registry、默认模型、默认策略、前端/API 或 Agent；
- 不运行策略 replay，不以策略收益代替模型评估；
- 不连接 monitor、broker、quick-trade、order、target、position、weight 或 quantity；
- 不承诺收益率、胜率或生产可用性。

## 4. 必读合同与前序证据

- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md`
- `docs/tw_modular_contracts/templates/NEW_MODEL_WORK_TEMPLATE_CN.md`
- `configs/data_source_registry.yaml`
- `configs/feature_registry.yaml`
- `configs/tw_modular_registry.yaml`
- `configs/tw_product_artifact_registry.yaml`
- `docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_ACCEPTANCE_REVIEW_CN.md`
- `docs/tw_new_model_strategy_pre_rnd/TW_CURRENT_STATE_FUTURE_RND_ROADMAP_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MSTR_ROUTE_CLOSURE_AFTER_MSTR1_SECTOR_LINEAGE_STOP_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_SSAP_ROUTE_CLOSURE_AFTER_SSAP1_OFFICIAL_SOURCE_STOP_CN.md`

## 5. 研究边界

允许的数据流仅为：

```text
registered DataSourceSnapshot
  -> checksum-backed PIT-safe FeatureArtifact
  -> isolated model training candidate
  -> isolated raw score
  -> ModelSignalArtifact adapter
  -> readonly model/OOS evaluation
```

任何候选不得直接消费 future return、未来价格、realized PnL、execution result、portfolio state、order 或 replay output。标签只可用于训练/评估目标，并必须按预测 horizon 做 purge/embargo 与严格时间隔离。

## 6. 阶段计划

| phase | 目标 | 主要输出 | 放行条件 |
| --- | --- | --- | --- |
| NMR0 | 模型、数据、特征、历史实验与研究空白只读盘点 | 执行报告、lineage 表、碰撞矩阵、唯一候选或 STOP | PIT 输入成立；候选不重复；可定义增量价值 |
| NMR1 | 单一候选模型与评估合同冻结 | model card 草案、feature allowlist、label/horizon、时间切分、门槛 | 无泄漏；无需新数据；不后验选窗/指标 |
| NMR2 | 隔离 baseline parity 与最小训练 smoke | deterministic bundle、训练日志、raw score、validator | baseline 可复现；训练仅写隔离目录 |
| NMR3 | 预注册 OOS 评估 | Rank IC/ICIR、TopN、覆盖、稳定性、校准与成本代理审计 | 相对基线有增量且不靠单一时期/股票 |
| NMR4 | 互补性、消融与鲁棒性 | score/error correlation、residual value、feature ablation、多窗口审计 | 机制成立；增量不是重复信号或泄漏 |
| NMR5 | ModelSignal adapter 与只读 onboarding candidate | 标准 artifact、registry candidate、golden samples、validators | `production_allowed=false`；合同全通过 |
| NMR6 | 路线关闭 | GO/NO-GO review | 独立审查完成；不自动生产化 |

每阶段必须由执行者提交报告、独立审查者给出 verdict。失败进入一次窄修复或关闭，不得无限扩参、换窗或更换指标。

## 7. NMR0 必须回答的问题

1. 当前每个模型的 family、输入、训练期、验证期、OOS 期、label/horizon、输出可见性和生产状态是什么？
2. 当前哪些 DataSource/FeatureArtifact 具有 checksum、`source_asof`、`available_at`、PIT policy 和足够时间覆盖？
3. 历史已研究或失败的 qlib、LTR、ensemble、policy/action model 和 feature 方向有哪些，关闭原因是什么？
4. 候选是否能解释为单一增量机制，而不是换算法名称重复相同信号？
5. 候选相对现有 baseline 的预测误差或排序是否具可检验的互补性？
6. 是否可以冻结一个无需新增数据、无需生产改动的训练与 OOS 设计？

## 8. 候选分类与唯一选择

NMR0 对每个方向标记：

```text
existing_baseline
duplicate_closed
input_blocked
leakage_risk
insufficient_window
novel_testable
out_of_contract
```

唯一候选必须同时满足：

- 使用现有可审计 PIT-safe 数据；
- 与当前 qlib/LTR baseline 有明确机制差异；
- 能以 score/error correlation、residual Rank IC 或 action-independent TopN overlap 等指标检验互补性；
- 有足够的 chronological OOS 与 strict holdout；
- 可通过删除增量输入/模块回到已定义 baseline；
- 不依赖 sector、新闻、TradingAgents synthetic evidence 或未批准来源；
- 不要求改生产链路才能研究。

若没有候选全部满足，结论必须为：

```text
STOP_NMR0_NO_NOVEL_TESTABLE_MODEL_ON_EXISTING_PIT_FEATURES
```

## 9. 预注册评估原则

NMR1 以后至少冻结并报告：

- cross-sectional Rank IC、ICIR 及按月/年稳定性；
- Top10/Top30/Top50 overlap、precision 或收益代理，明确不等于策略收益；
- score coverage、missing/duplicate/conflict、rank completeness；
- 与 qlib/LTR baseline 的 score correlation、error correlation 和 residual incremental value；
- symbol concentration、period concentration、market-regime stability；
- 训练/推理时间、determinism、seed 与环境；
- 多重比较和后验选择审计。

不得只按累计收益或单一 Rank IC 选模型。strict holdout 在最终评估前不得用于选特征、算法、超参数、早停规则或阈值。

## 10. NMR0 允许写入

仅允许新增：

```text
docs/tw_portfolio_decision_model/
  POLICY_NMR_EXISTING_PIT_FEATURE_NEW_MODEL_RESEARCH_MAINLINE_CN.md
  POLICY_NMR0_EXISTING_PIT_FEATURE_NEW_MODEL_RESEARCH_PREFLIGHT_WORK_CN.md
  POLICY_NMR0_EXISTING_PIT_FEATURE_NEW_MODEL_RESEARCH_PREFLIGHT_EXECUTION_REPORT_CN.md
  POLICY_NMR0_EXISTING_PIT_FEATURE_NEW_MODEL_RESEARCH_PREFLIGHT_REVIEW_CN.md
  POLICY_NMR1_*_WORK_CN.md            # 仅在 reviewer PASS 时
```

NMR0 不得写 `data_tw/`、`configs/`、`scripts/`、backend、frontend 或任何 artifact/latest 路径。

## 11. 停止条件

- 缺少 required contract/checklist；
- 输入没有 PIT/`available_at` 或需要当前快照回填历史；
- 候选依赖未来数据、realized PnL 或 replay output；
- 唯一候选与已关闭实验重复；
- 需要网络、DB、新数据源、provider/latest/default 改动；
- 无法冻结严格 chronological split 或独立 holdout；
- 候选只能以策略收益、算法复杂度或命名新颖性证明价值。

## 12. 关闭与生产边界

即使 NMR6 得出 GO，也只允许创建独立 production-candidate/onboarding 路线。本主线不授权生产 registry、daily scoring、latest publish、默认模型或前端/API 切换。

## 13. 首个执行命令

执行 `NMR0_EXISTING_PIT_FEATURE_NEW_MODEL_RESEARCH_PREFLIGHT`：只读盘点现有模型、数据、FeatureArtifact、历史实验、评估工具与研究空白，输出唯一候选或 STOP；不得训练、打分、运行 replay 或修改生产路径。

## 14. 首个审查任务

独立核对 lineage、PIT、模型/实验碰撞、时间切分可行性、互补性定义及 forbidden audit；不得因候选听起来新颖而放行。
