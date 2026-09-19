# 新模型/新策略研发前 Readiness Freeze 执行与审查文档

生成日期：2026-06-20

## 0. 目标

本阶段不是新模型或新策略研发本身，而是进入研发前的短冻结检查。

目标：

```text
确认 Agent、UI2、Skills、模块化合同和日更数据链路已经稳定到足以承接新模型/新策略研发。
```

本阶段只允许做：

- 版本状态盘点。
- 只读回归验证。
- project-local skills 加载与 archive 风险确认。
- artifact 链路入口确认。
- 数据视角日更链路说明补充。
- 给新模型/新策略主线写入场建议。

本阶段不允许做：

- 训练新模型。
- 新增策略规则。
- 修改默认模型或默认策略。
- 修改前端默认展示。
- 触发真实数据拉取。
- provider refresh / publish。
- accepted latest switch。
- monitor config / scan / alerts 写入。
- broker / quick-trade / order。
- OpenAI key 读取或真实 OpenAI smoke。

## 1. 必读文档

执行者和审查者必须先读：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md
docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_SUMMARY_CN.md
docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_S_ROUTE_FINAL_SUMMARY_CN.md
docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_EXPLAINED_FOR_BEGINNERS_CN.md
configs/tw_product_artifact_registry.yaml
```

如任一文档缺失，必须停下来报告。

## 2. 当前判断

当前项目已经具备进入新模型/新策略研发的架构基础：

- 模块合同已覆盖数据、特征、模型信号、策略、OrderIntent、Replay、前端只读展示和 Agent 只读上下文。
- Agent 已收敛为 `DailyAgentPromptArtifact -> simple-chat`，不再走复杂工具 Agent。
- UI2 已把 `/tw-stock-monitor` 收敛为策略工作台主路径。
- S 路线已将台股 skills 迁移为 project-local skills。

但正式开新研发节点前，必须先确认：

```text
这些地基已经被版本管理、只读回归和运行时路径确认固定下来。
```

## 3. Phase R0：版本冻结与范围盘点

执行者要做：

1. 输出当前 `git status --short`。
2. 分组列出未跟踪/已修改文件：
   - Agent daily prompt / simple-chat。
   - UI2 前端与 Playwright。
   - project-local skills。
   - 模块化合同与项目宪法。
   - 日更 runbook / orchestrator。
   - 其他无关变更。
3. 明确哪些文件应进入本次地基冻结提交范围。
4. 明确哪些文件属于历史遗留或无关变更，不能混入新模型/新策略研发。

执行者报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_EXECUTION_REPORT_CN.md
```

审查者要审查：

- 是否漏列关键 untracked 文件。
- 是否把 Agent/UI2/Skills 地基文件和未来新模型研发文件混在一起。
- 是否存在业务代码未审查却被标为“已稳定”的风险。

审查报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_REVIEW_CN.md
```

## 4. Phase R1：只读集成回归

执行者要做：

在不触发真实数据拉取、provider publish、accepted latest、monitor、broker/order 的前提下，复跑当前地基回归。

建议命令：

```bash
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py scripts/run_daily_tw_stock_auto_update.py
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py backend/tests/test_tw_stock_agent_simple_chat.py backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py -q
cd frontend && corepack pnpm build
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
node frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/run_tw_modular_contract_regression.py --json
```

如环境限制导致某命令无法运行，执行者必须说明：

- 失败命令。
- 失败原因。
- 是否是 sandbox / dependency / server 问题。
- 是否已有等价最近证据。

执行者报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_EXECUTION_REPORT_CN.md
```

审查者要审查：

- 是否所有命令只读。
- 是否存在 provider/latest/monitor/broker/order 请求。
- 是否 Agent simple-chat、UI2、M3/M4/M5 合同回归仍通过。
- 是否有失败项被不合理忽略。

审查报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_REVIEW_CN.md
```

## 5. Phase R2：Skills 与运行时入口确认

执行者要做：

1. 确认项目内九个台股 skills 存在：

```bash
find .agents/skills/tw-stock-* -maxdepth 2 -name SKILL.md -print | sort
```

2. 确认用户级 active `tw-stock-*` 路径为空：

```bash
find /home/chuliyang/.agents/skills -maxdepth 1 -type d -name 'tw-stock-*' -print | sort
```

3. 确认 archive 目录只作为备份，不应被运行时扫描：

```text
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/
```

4. 新会话或执行节点启动前，必须提醒统筹确认当前会话可用 skills 来自 project-local `.agents/skills`。

执行者报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER2_SKILL_RUNTIME_ENTRY_EXECUTION_REPORT_CN.md
```

审查者要审查：

- project-local skills 是否完整。
- 用户级 active 路径是否没有平行版本。
- archive 是否可能被运行时误加载。
- 是否需要在新节点启动命令里明确要求使用 project-local skills。

审查报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER2_SKILL_RUNTIME_ENTRY_REVIEW_CN.md
```

## 6. Phase R3：Artifact 链路入口确认

执行者要做：

1. 对照 `configs/tw_product_artifact_registry.yaml`，确认当前产品默认模型、默认策略、关键 artifact root：
   - `base_model_id`
   - `treatment_model_id`
   - `default_strategy_rule`
   - `signal_root`
   - `readonly_strategy_latest`
   - price sources
2. 对照 `TW_DAILY_UPDATE_DATA_FLOW_EXPLAINED_FOR_BEGINNERS_CN.md`，确认后续新模型/新策略不得绕过标准链路：

```text
DataSource / PriceStore / FeatureArtifact
-> ModelSignalArtifact
-> StrategyRule / StrategyDependency
-> OrderIntentArtifact
-> ReplayResultArtifact
-> ReadonlyStrategySnapshot
-> DailyAgentPromptArtifact
-> API / Frontend
```

3. 列出当前仍需未来稳定化的非阻塞点：
   - 生产 source artifacts 物化链路。
   - Agent prompt latest publish 默认关闭。
   - legacy provider publish / accepted latest 代码仍存在但默认不可达。
   - 新模型/新策略不得直接切默认产品路径。

执行者报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER3_ARTIFACT_CHAIN_ENTRY_EXECUTION_REPORT_CN.md
```

审查者要审查：

- 是否正确理解 registry 是当前产品路径入口。
- 是否把 Agent prompt latest 与 provider/qlib accepted latest 区分清楚。
- 是否确认新模型输出必须是 `ModelSignalArtifact`。
- 是否确认新策略输出必须是 `OrderIntentArtifact`。

审查报告：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER3_ARTIFACT_CHAIN_ENTRY_REVIEW_CN.md
```

## 7. Phase R4：研发入场建议

执行者要做：

输出最终 readiness 总结：

```text
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_SUMMARY_CN.md
```

必须给出三类结论之一：

```text
通过，可以进入新模型/新策略研发。
有条件通过，只允许进入列明的窄范围研发。
不通过，必须先修复列明阻塞项。
```

审查者要做：

输出最终验收：

```text
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_ACCEPTANCE_REVIEW_CN.md
```

审查者必须明确：

- 是否允许开新模型节点。
- 是否允许开新策略节点。
- 是否允许同时开模型和策略节点。
- 第一轮研发是否必须限制为单模型或单策略。
- 需要交给执行者的第一条命令。

## 8. 建议第一轮研发边界

除非统筹另行决定，第一轮正式研发建议只选一条：

```text
路线 A：新模型研发
```

或：

```text
路线 B：新策略研发
```

不建议第一轮同时做新模型和新策略，因为同时改两个变量会导致 replay 结果无法归因。

如果先做新模型：

- 只做 raw score -> ModelAdapter -> ModelSignalArtifact。
- 不改策略。
- 不改前端默认展示。
- 不做 default switch。

如果先做新策略：

- 只做 StrategyDependency -> StrategyRule -> OrderIntentArtifact -> readonly replay。
- 不改模型。
- 不改前端默认展示。
- 不做 default switch。

## 9. 执行者第一条命令

```text
你是执行者。请按 docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_EXECUTION_AND_REVIEW_PLAN_CN.md 执行 Phase R0：版本冻结与范围盘点。只做 git 状态、文件分组、地基冻结范围建议和风险说明，不训练模型、不新增策略、不运行真实数据拉取、不触发 provider publish/accepted latest/monitor/broker/order。完成后写 docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_EXECUTION_REPORT_CN.md。
```

## 10. 审查者第一条命令

```text
你是审查者。请等待执行者提交 docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_EXECUTION_REPORT_CN.md 后，按 docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_EXECUTION_AND_REVIEW_PLAN_CN.md 审查 Phase R0。重点确认关键地基文件是否完整纳入冻结范围、是否存在未审查业务变更混入、是否可以进入 R1 只读集成回归。审查后写 docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_REVIEW_CN.md，并给出 R1 下一步工作文档。
```
