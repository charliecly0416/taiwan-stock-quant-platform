# Pre-RND Readiness 支线统筹审核交接文档

生成日期：2026-06-20

## 1. 给统筹的结论

本支线已完成，可以收尾。

建议验收结论：

```text
ACCEPTED_WITH_CONDITIONS
有条件通过，只允许进入列明的窄范围新模型/新策略研发。
```

当前不建议无条件开放研发，也不建议第一轮同时开新模型和新策略。建议第一轮只开一个单新模型节点，且只做到 `ModelSignalArtifact + registry + golden sample + OOS evidence + validator + review report`，不改默认模型、默认策略、前端默认、Agent prompt 来源或任何 latest/default 路径。

## 2. 支线目标

本支线是新模型/新策略研发前的 readiness freeze。

目标是确认：

```text
Agent、UI2、Skills、模块化合同、日更说明和 artifact 链路已经稳定到足以承接后续窄范围研发。
```

本支线不是：

```text
新模型训练
新策略实现
默认产品路径切换
真实数据更新
provider publish / accepted latest
monitor 写入
broker/order 接入
OpenAI smoke
```

## 3. 关键文档清单

主线计划：

```text
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_EXECUTION_AND_REVIEW_PLAN_CN.md
```

执行与审查产物：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_EXECUTION_REPORT_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_REVIEW_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_EXECUTION_REPORT_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_REVIEW_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER1_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER1_REPAIR_REVIEW_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER1R2_REMAINING_REGRESSION_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER1R2_REMAINING_REGRESSION_REPAIR_REVIEW_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER2_SKILL_RUNTIME_ENTRY_EXECUTION_REPORT_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER2_SKILL_RUNTIME_ENTRY_REVIEW_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER3_ARTIFACT_CHAIN_ENTRY_EXECUTION_REPORT_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER3_ARTIFACT_CHAIN_ENTRY_REVIEW_CN.md
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_SUMMARY_CN.md
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_ACCEPTANCE_REVIEW_CN.md
docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_EXPLAINED_FOR_BEGINNERS_CN.md
docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_REAL_SAMPLE_20260618_CN.md
```

统筹审核本文档：

```text
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_COORDINATOR_HANDOFF_CN.md
```

## 4. 阶段结果总览

### R0：版本冻结与范围盘点

结论：

```text
PASS_WITH_CONDITIONS
```

确认了本次地基冻结范围：

```text
Agent Daily Prompt / simple-chat
UI2 前端与 Playwright
project-local skills
模块化合同与项目宪法
日更 runbook / orchestrator
pre-RND 文档
```

保留事项：仍有 untracked/modified 地基文件，正式研发前建议统筹做版本冻结提交或 baseline tag。

### R1：只读集成回归

初始结论：

```text
FAIL_NEEDS_REPAIR
```

初始失败项：

```text
frontend simple-chat static check 推荐问题断言漂移
M2 EXECUTION_REPORT_TEMPLATE_CN.md 缺失
M4 readonly primary fields 缺少 合法窗口 / 手续费/税费 / 审计状态
```

R1 repair 后仍有 regression blockers。

R1R2 后最终结论：

```text
PASS_AFTER_REPAIR
```

关键证据：

```text
python scripts/run_tw_modular_contract_regression.py --json -> ok=true
m1_contract_status=passed
m2_registry_status=passed
m3_daily_orchestrator_status=passed
m3_daily_script_audit_status=passed
m4_frontend_readonly_status=passed
m5_onboarding_smoke_status=passed
m4_forbidden_request_count=0
```

保留 warning：

```text
legacy_provider_publish_path_present
legacy_accepted_latest_path_present
```

解释：legacy provider publish / accepted latest 代码仍存在，但已被 gate 保护，默认不可达。

### R2：Skills 与运行时入口确认

结论：

```text
PASS_WITH_RUNTIME_WARNING
```

确认：

```text
project-local 九个 tw-stock skills 完整
用户级 active /home/chuliyang/.agents/skills/tw-stock-* 路径为空
archive 目录未删除、未移动、未覆盖
关键 skills 职责边界清楚
红线关键词命中均为禁止、停止条件、审查规则或 readonly boundary 语境
```

保留 warning：

```text
当前运行时 metadata 仍可能显示 archive 旧 skill 条目。
后续执行者必须显式以 project-local .agents/skills/tw-stock-* 为准。
```

### R3：Artifact 链路入口确认

结论：

```text
PASS
```

确认：

```text
configs/tw_product_artifact_registry.yaml 当前产品入口清晰
新模型必须通过 ModelSignalArtifact 接入
新策略必须通过 StrategyRule / StrategyDependency 接入
策略输出只能是 OrderIntentArtifact
Replay 必须是 readonly ReplayResultArtifact
Agent prompt latest、readonly strategy latest、provider/qlib accepted latest、frontend defaults 已区分
```

边界：R3 只确认入口与职责，不验证每个生产 source artifact 的现时存在性，也不生成 artifact。

### R4：最终总结

执行者最终总结结论：

```text
有条件通过，只允许进入列明的窄范围新模型/新策略研发。
```

审查结论：

```text
ACCEPTED_WITH_CONDITIONS
可以收尾。
```

## 5. 当前产品默认入口

来自：

```text
configs/tw_product_artifact_registry.yaml
```

当前入口：

```text
base_model_id = e4_frozen_qlib_2018_2022
treatment_model_id = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
treatment_display_model_id = e4_frozen_qlib_2023_2025_ltr
default_strategy_rule = top50_exit_one_worst_sell
signal_root = data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals
readonly_strategy_latest = data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
readonly_only = true
no_provider_publish = true
no_accepted_latest_switch = true
no_monitor_write = true
no_broker_order = true
```

后续新模型/新策略第一轮不得修改这些默认入口。

## 6. 后续允许的研发范围

允许开新模型节点：允许，窄范围。

范围：

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

允许开新策略节点：允许，窄范围。

范围：

```text
StrategyDependency
StrategyRule
OrderIntentArtifact
readonly ReplayResultArtifact
validator
golden sample
review report
```

是否允许同时开模型和策略节点：

```text
不建议，不应作为第一轮研发方式。
```

第一轮限制：

```text
单变量：单模型或单策略。
```

第一轮推荐：

```text
路线 A：单新模型节点。
```

## 7. 必须继承的红线

后续研发节点严禁：

```text
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target_position / target_weight 写入
OpenAI key 读取
真实 OpenAI smoke
生成或发布 production artifact/latest pointer
修改默认模型或默认策略
修改前端默认展示
让 Agent 扩权或绕过 DailyAgentPromptArtifact
用动态服务 payload 假装 artifact 链路存在
把 smoke/diagnostic 当收益证据
```

必须继续区分：

```text
Agent prompt latest != readonly strategy latest
readonly strategy latest != provider accepted latest
readonly strategy latest != qlib accepted latest
frontend defaults 来自 configs/tw_product_artifact_registry.yaml
PaperPortfolio 是 simulation-only，不是 broker/order/target position
```

## 8. 统筹审核建议

建议统筹确认：

```text
1. 接受本支线以 ACCEPTED_WITH_CONDITIONS 收尾。
2. 正式研发前做版本冻结提交或 baseline tag。
3. 第一轮研发走单新模型节点。
4. 第一轮新模型节点先提交独立 work doc，再允许训练或 artifact 生成。
5. 第一轮研发启动前复跑 full modular regression 作为基线。
6. 评估是否需要运行时配置排除 archive skill 目录。
```

## 9. 建议下一条给执行者的指令

如统筹批准第一轮走新模型节点，建议给执行者：

```text
你是执行者。请准备第一轮窄范围新模型研发工作文档，只做计划和边界确认，不训练模型、不生成 artifact、不修改默认路径。必须以 project-local .agents/skills/tw-stock-new-model-onboarding/SKILL.md 为准，读取 docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md、docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md、docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md。工作文档必须说明模型目标与非目标、输入 feature/data artifacts、训练/OOS 窗口、PIT/available_at policy、ModelSignalArtifact 输出字段、registry entry、validator/golden sample、不接入 production defaults 声明。不得触发真实数据、provider publish、accepted latest、monitor、broker/order、OpenAI 或 default switch。
```

## 10. 收尾状态

本支线状态：

```text
CLOSED_PENDING_COORDINATOR_APPROVAL
```

含义：审查者认为本支线可以关闭，等待统筹确认是否接受条件、是否做 baseline、以及是否开启第一轮单新模型研发准备节点。
