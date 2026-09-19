---
created_at: 2026-08-21
status: coordinator_mainline
route: MSTR_EXISTING_SIGNAL_STRATEGY_RESEARCH
current_phase: MSTR0_EXISTING_SIGNAL_STRATEGY_RESEARCH_PREFLIGHT
readonly_only: true
simulation_only: true
production_allowed: false
default_switch_allowed: false
daily_auto_change_allowed: false
provider_or_latest_write_allowed: false
broker_authorized: false
---

# MSTR 现有信号策略研究主线

## 1. 目标

在不训练新模型、不改变现有日更和产品 latest 的前提下，使用已经通过合同校验的 `ModelSignalArtifact`，寻找一个具有明确机制、可归因、可复现且有样本外验证价值的新策略候选。

本路线优先回答：现有信号的经济价值是否还能通过更合理的持有、替换或组合约束得到提升。只有策略层证据显示信号本身成为瓶颈时，才建议转入新模型路线。

## 2. 非目标

- 不训练、重训或调优模型；
- 不修改 provider、qlib、accepted latest、legacy latest、DAPR18 latest 或 cron；
- 不修改生产默认策略、前端/API 默认、Agent 默认；
- 不输出真实订单、目标仓位、目标权重、数量或投资建议；
- 不连接 broker、quick-trade、monitor/order/target；
- 不把 diagnostic/smoke 结果写成收益或生产结论；
- 不复活已经关闭的 RSR/Phase P 候选，也不把旧机制改名当作新策略。

## 3. 当前基线

1. 当前正式基线策略仍为 `top50_exit_one_worst_sell`。
2. `top50_hold_rank_buffer_100` 是证据最强的现有策略候选：历史同窗口收益、回撤和换手优于基线，且已具备隔离的只读 exposure；但仍 `production_allowed=false`，不得视为默认策略。
3. `portfolio_decision_optimizer_v1` 已因 qlib-only OOS 表现不足收为只读研究/失败机制样本，不得直接续推。
4. RSR 路线已关闭：rank-deterioration 机制归因不成立；score bucket、rank momentum、market-regime action budget 和 score-rank-regime interaction 均已拒绝。
5. MTR 已研究 max replacement、hold rank buffer、score/rank advantage、固定成本 gate 及其固定组合；M2 hold-rank-buffer 是唯一通过候选 gate 的机制。重复这些网格不构成新研究。
6. TradingAgents TADR 只有研究设计证据，没有足够真实 OOS 数据，不得作为本路线的策略输入或收益证据。
7. 当前 Model A 日信号链路已自然推进至至少 `2026-08-21` 的本地产物，可作为 freshness 事实；MSTR 不写任何 latest 指针。

## 4. 必读合同与前序结论

- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR6_SCORE_RANK_REGIME_RULE_RESEARCH_CLOSURE_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTR1_QLIB_ONLY_ORDER_INTENT_PARITY_AND_MECHANISM_REPLAY_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP12_GO_NO_GO_CLOSURE_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/PHASEP_BRANCH_B_CLOSURE_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_TADR5_RESEARCH_CLOSURE_REVIEW_CN.md`

## 5. 模块边界

允许的策略数据流只有：

```text
ModelSignalArtifact + PortfolioState + StrategyRuleConfig
  -> StrategyRule
  -> OrderIntentArtifact
  -> readonly ReplayExecution
  -> ReplayResultArtifact
```

策略不得直接读取模型私有文件、future return/label、realized PnL、replay return、未来价格或成交结果。新增输入字段必须先通过 `ModelSignalArtifact` extension 或现有合同声明，且满足 PIT/`available_at`。

## 6. 阶段计划

| phase | 目标 | 主要输出 | 放行条件 |
| --- | --- | --- | --- |
| MSTR0 | 现有资产、历史结论、输入和研究空白盘点 | 执行报告、候选碰撞矩阵、唯一下一步建议 | 输入可追溯；不重复关闭路线；能定义可证伪机制 |
| MSTR1 | 单一候选假设与依赖合同冻结 | work doc、dependency draft/contract、预注册窗口和门槛 | 无未来数据；变量可得；不后验选阈值 |
| MSTR2 | baseline parity 与 OrderIntent dry-run | isolated OrderIntent、validator、parity audit | baseline parity 通过；意图合同通过 |
| MSTR3 | 预注册只读 replay | ReplayResult、成本/换手/覆盖审计 | next-day execution；费用税费；无 silent skip |
| MSTR4 | 稳健性、归因和反事实消融 | 多窗口/市场状态/集中度/机制消融 | 机制贡献成立且不是少数事件假象 |
| MSTR5 | 路线收口 | GO/NO-GO closure | 独立审查完成；不自动生产化 |

每一阶段由执行者产出执行报告，由独立审查者检查后写下一阶段工作单。任何阶段失败都进入窄修复或路线关闭，不得无限扩参。

## 7. MSTR0 候选筛选原则

MSTR0 必须给每个方向标记：`continue_existing`、`novel_testable`、`duplicate_closed`、`input_blocked` 或 `out_of_contract`。

优先级按以下顺序决定：

1. 是否直接解决已有证据中的失败模式，例如收益集中、换手成本、弱替换或跨窗口不稳定；
2. 是否只依赖标准信号和当前持仓状态；
3. 是否能写成单一、可消融机制；
4. 是否存在足够长、同 lineage、PIT-safe 的回放窗口；
5. 是否没有被 MTR、RSR、Phase P 先前否定；
6. 是否能在不触碰生产链路的条件下完整验证。

不得因名称不同而重复：confidence/score gap、rank momentum/deterioration、market regime action budget、固定成本 gate、hold buffer 网格或 portfolio optimizer 全门控组合。

## 8. 证据要求

MSTR0 至少形成：

- 当前标准信号与 lineage 可用性表；
- 当前策略/dependency/实现/OrderIntent/replay/shadow 资产表；
- 历史候选与关闭原因矩阵；
- 候选机制碰撞和输入可得性矩阵；
- 回放工具与费用/税费/执行价口径清单；
- 一个唯一推荐方向，或明确 `STOP_NO_NOVEL_TESTABLE_STRATEGY`；
- forbidden actions audit。

MSTR3 以后至少同时报告净收益、最大回撤、换手、费用税费、交易/跳过数、持仓集中度和相对基线差异。不得只按收益选优。

## 9. 停止条件

- 只剩已关闭或重复机制；
- 候选依赖未合同化字段或未来信息；
- 无法获得同 lineage 的 baseline/candidate 输入；
- 必须修改 replay engine 的策略无关性；
- 必须改日更、provider、latest、默认策略或前端才能研究；
- 需要真实交易、目标仓位/权重或数量输出；
- 机制无法通过消融与 action-level attribution 单独识别。

## 10. 关闭标准

MSTR 只在 MSTR0-MSTR5 均有执行报告和独立审查、所有阻断已处理、证据链可重放、forbidden audit clean 后关闭。即使 GO，也只表示可提出单独的 production-candidate 路线；本路线本身不授权 default/latest/daily/paper/trading。

## 11. 首个执行命令

执行 `MSTR0_EXISTING_SIGNAL_STRATEGY_RESEARCH_PREFLIGHT`，只读盘点并写执行报告，不实现新策略、不生成 OrderIntent/replay、不修改任何运行配置或 latest。

## 12. 首个审查任务

独立核对执行报告是否完整覆盖合同、历史关闭结论、输入 lineage、候选碰撞、回放口径和禁区，并检查“唯一下一步”是否真正新颖、可证伪、可在当前边界内执行。
