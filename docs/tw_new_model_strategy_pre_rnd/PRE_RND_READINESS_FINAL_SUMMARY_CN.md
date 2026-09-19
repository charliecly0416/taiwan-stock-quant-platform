# Pre-RND Readiness 最终总结

生成日期：2026-06-20

## 1. 最终结论

最终结论：有条件通过，只允许进入列明的窄范围新模型/新策略研发。

允许开启研发节点，但必须满足：

```text
后续执行节点以 project-local .agents/skills/tw-stock-* 为准。
不得把 /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/ 下的旧 skills 当作 active 来源。
如运行时自动触发到 archive 旧 skill 描述，必须停止并报告。
第一轮研发必须限制为单变量：单模型或单策略。
不建议同时开新模型和新策略节点。
不得切当前产品默认模型、默认策略、前端默认展示或 latest/default 路径。
```

当前建议第一轮优先路线：路线 A，新模型研发，但只到 `ModelSignalArtifact + registry + golden sample + OOS evidence + validator + review report`。原因是新模型可以先在标准信号层完成隔离验证，不必同时改策略、前端、Agent 或生产 latest。

R4 不是新模型或新策略研发；本总结不替代后续新模型/新策略的合同、validator、golden sample、OOS/replay evidence 或审查报告。

## 2. R0-R3 阶段汇总

### R0：版本冻结与范围盘点

执行报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_REVIEW_CN.md
```

结论：`PASS_WITH_CONDITIONS`，允许进入 R1。

R0 已确认当前地基范围包括：

```text
Agent Daily Prompt / simple-chat
UI2 前端与 Playwright
project-local skills
模块化合同与项目宪法
日更 runbook / orchestrator
pre-RND 文档
```

仍需纳入冻结的文件范围：Agent/UI2/Skills/合同/日更 runbook/pre-RND 文档仍有大量 untracked 或 modified 文件。正式研发前必须由统筹纳入版本管理或等价冻结范围，不能把这些地基文件混入新模型/新策略功能提交。

### R1：只读集成回归

初始执行报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_EXECUTION_REPORT_CN.md
```

初始审查报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_REVIEW_CN.md
```

初始结论：失败，需要 repair。

初始失败项：

```text
frontend simple-chat static check 推荐问题断言漂移
M2 EXECUTION_REPORT_TEMPLATE_CN.md 缺失
M4 readonly primary fields 缺少 合法窗口 / 手续费/税费 / 审计状态
```

第一轮 repair 审查：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1_REPAIR_REVIEW_CN.md
```

结论：三项授权缺口已修复，但 full modular contract regression 仍失败。

R1R2 repair 审查：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1R2_REMAINING_REGRESSION_REPAIR_REVIEW_CN.md
```

R1R2 修复项：

```text
registry validation 支持 nested strategies
manifest coverage 支持 archive fallback
forbidden scope audit 改为完整文件 marker + diff added-lines forbidden scan + validator evidence
```

最终状态：

```text
R1 = PASS_AFTER_REPAIR
python scripts/run_tw_modular_contract_regression.py --json -> ok=true
m1_contract_status=passed
m2_registry_status=passed
m3_daily_orchestrator_status=passed
m3_daily_script_audit_status=passed
m4_frontend_readonly_status=passed
m5_onboarding_smoke_status=passed
m4_forbidden_request_count=0
```

保留 warning：`legacy_provider_publish_path_present` 与 `legacy_accepted_latest_path_present` 仍存在，但已被 gate 保护，默认不可达。

### R2：Skills 与运行时入口确认

执行报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER2_SKILL_RUNTIME_ENTRY_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER2_SKILL_RUNTIME_ENTRY_REVIEW_CN.md
```

结论：`PASS_WITH_RUNTIME_WARNING`，允许进入 R3。

已确认：

```text
project-local 九个 tw-stock skills 完整
用户级 active /home/chuliyang/.agents/skills/tw-stock-* 路径为空
archive 目录未删除、未移动、未覆盖
关键 skills 职责边界清楚
红线关键词命中均为禁止、停止条件、审查规则或 readonly boundary 语境
```

保留 warning：当前运行时 metadata 仍可能显示 archive 旧 skill 条目。后续执行者必须显式以 project-local `.agents/skills/tw-stock-*` 为准。

### R3：Artifact 链路入口确认

执行报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER3_ARTIFACT_CHAIN_ENTRY_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER3_ARTIFACT_CHAIN_ENTRY_REVIEW_CN.md
```

结论：`PASS`，允许进入 R4。

已确认：

```text
configs/tw_product_artifact_registry.yaml 当前产品入口清晰
新模型必须通过 ModelSignalArtifact 接入
新策略必须通过 StrategyRule / StrategyDependency 接入
策略输出只能是 OrderIntentArtifact
Replay 必须是 readonly ReplayResultArtifact
Agent prompt latest、readonly strategy latest、provider/qlib accepted latest、frontend defaults 已区分
```

R3 明确边界：只确认入口与职责，不验证每个生产 source artifact 的现时存在性，也不生成 artifact。后续真实研发使用具体 artifact 时，必须读取 manifest/latest pointer 并运行 validator；缺失时停在缺口报告。

## 3. 当前已通过的地基能力

当前地基已具备以下能力：

```text
Agent 已收敛到 DailyAgentPromptArtifact -> backend simple-chat 路线。
UI2 /tw-stock-monitor 已收敛为只读策略工作台主路径。
Project-local tw-stock skills 已建立九个入口：新模型、新策略、模块化回归、安全审查、readonly E2E、研究解释、数据新鲜度、Agent prompt、前端 UX。
Modular contracts 已覆盖 ModelSignalArtifact、StrategyRule、OrderIntentArtifact、ReplayResultArtifact、DailyAgentPromptArtifact 等关键链路。
Full modular contract regression 已在 R1R2 后 ok=true。
Product artifact registry 已声明当前默认模型、默认策略、signal root、readonly strategy latest、price sources 和安全 flags。
```

当前产品默认入口：

```text
base_model_id = e4_frozen_qlib_2018_2022
treatment_model_id = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
treatment_display_model_id = e4_frozen_qlib_2023_2025_ltr
default_strategy_rule = top50_exit_one_worst_sell
readonly_strategy_latest = data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
readonly_only = true
no_provider_publish = true
no_accepted_latest_switch = true
no_monitor_write = true
no_broker_order = true
```

## 4. 仍需保留的非阻塞风险

以下风险不阻塞开启窄范围研发，但必须保留在研发节点启动说明和审查 checklist 中：

```text
project-local skills 仍需纳入最终版本冻结提交范围。
当前运行时可能仍显示 archive 旧 skill metadata；后续节点必须显式以 project-local skills 为准。
生产 source artifacts 物化链路仍需后续明确和稳定化。
Agent prompt latest publish 默认关闭/dry-run，未来 release 需单独验收。
legacy provider publish / accepted latest 代码仍存在，但当前默认路径不可达。
新模型/新策略不得直接切当前产品默认路径。
R3 未验证每个生产 source artifact 的现时存在性；真实研发使用具体 artifact 时必须按 manifest/latest pointer + validator 重新确认。
```

这些风险的处理方式：记录、隔离、在后续专项阶段验收；不得用 R4 总结把它们伪装成已完成。

## 5. 是否允许开新模型节点

允许，但只允许窄范围新模型节点。

允许范围：

```text
raw score
ModelAdapter
ModelSignalArtifact
registry entry
golden sample
OOS evidence
validator
review report
```

必须遵守：

```text
策略、Replay、Frontend、Agent 不得直接读取模型私有字段或训练输出。
新模型输出必须经 adapter 映射为 ModelSignalArtifact core fields 或声明的 ext_* 字段。
production_allowed=false，直到专项审查通过。
必须使用 NEW_MODEL_REVIEWER_CHECKLIST_CN.md 审查。
```

禁止：

```text
改策略
改前端默认
改 DailyAgentPromptArtifact 默认来源
切 provider / qlib accepted latest
切 readonly_strategy_latest
default-switch production model
承诺收益、胜率或上涨概率
```

## 6. 是否允许开新策略节点

允许，但只允许窄范围新策略节点。

允许范围：

```text
StrategyDependency
StrategyRule
OrderIntentArtifact
readonly ReplayResultArtifact
validator
golden sample
review report
```

必须遵守：

```text
策略只能消费标准 ModelSignalArtifact、PortfolioState、StrategyRuleConfig。
策略输出只能是 OrderIntentArtifact。
Replay 只能消费 OrderIntentArtifact、PriceStore、ExecutionConfig、InitialPortfolioState。
必须使用 NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md 审查。
```

禁止：

```text
改模型
读取模型私有字段
改前端默认
输出 target_position / target_weight
连接 broker / quick-trade / order
切默认策略
provider publish / accepted latest switch
monitor writes
```

## 7. 是否允许同时开模型和策略节点

不建议，不应作为第一轮研发方式。

原因：同时开模型和策略会让变量耦合，难以判断问题来自 ModelSignalArtifact 语义、StrategyDependency、OrderIntent、Replay 还是 frontend/Agent 展示。R0-R3 的地基刚完成 repair 后通过，第一轮必须限制为单变量。

建议：

```text
第一轮只开单模型节点，或只开单策略节点。
不得在同一任务中同时训练/接入新模型并修改策略规则。
不得在同一任务中同时改默认产品路径、前端展示和 Agent prompt 来源。
```

## 8. 第一轮研发建议路线

推荐路线：路线 A，新模型研发。

推荐理由：

```text
新模型可以先停在 ModelSignalArtifact 边界，不触碰当前默认策略。
ModelSignalArtifact core fields、extension schema、validator、golden sample、OOS evidence 已有明确合同。
第一轮可以验证新模型是否能被标准链路审查，而不改变 frontend defaults、Agent prompt latest 或 readonly_strategy_latest。
```

路线 A 第一轮目标：

```text
选择一个新模型或模型 adapter 方向。
定义模型名称、模型族、训练/OOS 窗口、PIT/available_at policy。
生成或审查 ModelSignalArtifact manifest/signals/schema/audits。
补 registry entry，production_allowed=false。
补 pass/fail golden samples。
运行模型相关 validator 与 full modular regression。
输出新模型执行报告与 reviewer checklist。
```

路线 B 可作为第二选择：单策略研发。

适用条件：已有稳定 ModelSignalArtifact，且策略变化可以完全用 StrategyDependency / StrategyRule / OrderIntentArtifact 表达，不需要新模型字段或私有模型输出。

## 9. 第一轮执行者命令

建议第一轮新模型节点的执行者第一条命令：

```bash
sed -n '1,220p' .agents/skills/tw-stock-new-model-onboarding/SKILL.md && sed -n '1,220p' docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md && sed -n '1,220p' docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md && sed -n '1,220p' docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
```

执行者随后必须先写新模型工作文档或执行计划，明确：

```text
模型目标与非目标
输入 feature/data artifacts
训练窗口与 OOS 窗口
PIT / available_at policy
ModelSignalArtifact 输出字段
registry entry
validator / golden sample
不接入 production defaults 声明
```

如果统筹选择路线 B，第一条命令应改为：

```bash
sed -n '1,220p' .agents/skills/tw-stock-new-strategy-onboarding/SKILL.md && sed -n '1,220p' docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md && sed -n '1,220p' docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md && sed -n '1,220p' docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md && sed -n '1,220p' docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

## 10. 严禁事项

R4 后第一轮研发仍严禁：

```text
训练新模型与合同补丁混在一个未审查阶段
新增策略规则并同时切默认策略
修改默认模型或默认策略
修改前端默认展示为新模型/新策略
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target_position / target_weight 写入
OpenAI key 读取
真实 OpenAI smoke
生成或发布 production artifact/latest pointer
用动态服务 payload 假装 artifact 链路已经存在
把 smoke/diagnostic 当收益证据
让 Agent 扩权或绕过 DailyAgentPromptArtifact
```

必须继续区分：

```text
Agent prompt latest != readonly strategy latest
readonly strategy latest != provider accepted latest
readonly strategy latest != qlib accepted latest
frontend defaults 来自 configs/tw_product_artifact_registry.yaml，不是新研发任务内临时常量
PaperPortfolio 是 simulation-only，不是 broker/order/target position
```

## 11. 需要审查者最终验收的问题

请审查者最终验收以下问题：

```text
1. 是否接受最终结论为“有条件通过，只允许窄范围研发”？
2. 是否接受第一轮推荐路线为单新模型节点，而不是同时开新模型和新策略？
3. 是否要求在开研发节点前先做一次版本冻结提交或等价 baseline tag？
4. 是否需要运行时配置排除 /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/，避免 archive skill metadata 残留？
5. 是否要求第一轮新模型节点先提交独立 work doc，再允许执行任何训练或 artifact 生成？
6. 是否要求第一轮研发必须先跑 R1R2 后的 full modular regression 作为基线确认？
```

建议最终验收输出：

```text
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_ACCEPTANCE_REVIEW_CN.md
```

执行侧建议：若审查者接受本总结，可正式关闭 pre-RND readiness 支线，并开启第一轮窄范围新模型研发准备节点。
