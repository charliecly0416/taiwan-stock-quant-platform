# Phase R0 执行报告：版本冻结与范围盘点

生成日期：2026-06-20

## 1. 结论

Phase R0 已完成版本冻结盘点。当前可以进入审查，但不建议直接进入新模型/新策略研发；必须先把 Agent、UI2、Skills、模块合同、日更 runbook 与 pre-R&D 文档这些“地基文件”纳入同一次冻结提交或等价版本管理范围。

本阶段只做只读盘点与报告写入，未训练模型、未新增策略、未运行真实数据拉取、未触发 provider refresh/publish、未切 accepted latest、未写 monitor、未触发 broker/order、未读取 OpenAI key。

## 2. 必读文档存在性

按 `PRE_RND_READINESS_EXECUTION_AND_REVIEW_PLAN_CN.md` 要求复核，以下必读文件均存在：

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

关键约束已确认：

- 当前台股主线是只读研究、产品化候选展示与模拟账户，不是实盘交易系统。
- 新模型必须先经 `ModelAdapter -> ModelSignalArtifact`。
- 新策略必须先经 `StrategyRule / StrategyDependency -> OrderIntentArtifact`。
- 新研发不得改默认模型、默认策略、前端默认展示或 accepted latest。

## 3. 当前 git status

执行：

```bash
git status --short --untracked-files=all
```

摘要如下：

```text
 M backend/app/routes/tw_stock.py
 M comment.md
 M docs/tw_modular_contracts/TW_CURRENT_PROJECT_DOC_ENTRY_AND_ARCHIVE_POLICY_CN.md
 M docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md
 M frontend/src/api/tw-stock.js
 M frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue
 M frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
 M frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
 M frontend/src/views/tw-stock-monitor/index.vue
 M scripts/run_daily_tw_stock_auto_update.py
?? .agents/skills/**
?? backend/app/services/tw_stock_agent_daily_prompt.py
?? backend/app/services/tw_stock_agent_simple_chat.py
?? backend/tests/test_tw_stock_agent_daily_prompt_*.py
?? backend/tests/test_tw_stock_agent_simple_chat.py
?? docs/tw_agent_daily_prompt_rebuild/**
?? docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_*.md
?? docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
?? docs/tw_modular_daily_update_productization/PHASEUI*.md
?? docs/tw_new_model_strategy_pre_rnd/**
?? docs/tw_skills_maintenance/**
?? frontend/tests/e2e/tw-stock-agent-simple-chat-network.mjs
?? frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
?? frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
?? scripts/build_tw_agent_daily_prompt_artifact.py
?? scripts/validate_tw_agent_daily_prompt_artifact.py
?? skills-lock.json
```

完整命令输出较长，R0 盘点按下列分组冻结。

## 4. 分组盘点

### 4.1 Agent Daily Prompt / simple-chat

应纳入地基冻结范围：

```text
backend/app/routes/tw_stock.py
backend/app/services/tw_stock_agent_daily_prompt.py
backend/app/services/tw_stock_agent_simple_chat.py
backend/tests/test_tw_stock_agent_daily_prompt_builder.py
backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py
backend/tests/test_tw_stock_agent_daily_prompt_validator.py
backend/tests/test_tw_stock_agent_simple_chat.py
docs/tw_agent_daily_prompt_rebuild/**
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_EXECUTION_AND_REVIEW_PLAN_CN.md
scripts/build_tw_agent_daily_prompt_artifact.py
scripts/validate_tw_agent_daily_prompt_artifact.py
frontend/tests/e2e/tw-stock-agent-simple-chat-network.mjs
frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

冻结理由：

- 这是 Agent 收敛为 `DailyAgentPromptArtifact -> backend /api/tw-stock/agent/simple-chat` 的地基。
- 新模型/新策略研发后，Agent 只能消费标准 artifact 压缩出的每日上下文，不能重新走复杂 tool Agent 或前端 OpenAI。

风险：

- 该组仍为大量 untracked 文件，未入库前不能视为稳定地基。
- R1 必须复跑 prompt builder/validator/simple-chat 相关 pytest 和静态检查。

### 4.2 UI2 前端与 Playwright

应纳入地基冻结范围：

```text
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_SUMMARY_CN.md
docs/tw_modular_daily_update_productization/PHASEUI2B_CANDIDATES_AND_REPLAY_*.md
docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_*.md
docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_*.md
```

冻结理由：

- `/tw-stock-monitor` 已成为策略工作台主路径。
- 新模型/新策略研发前必须固定前端只读 DTO、Agent panel、候选名单、readonly replay、paper portfolio 和移动端验收口径。

风险：

- 前端源码处于 modified 状态，相关测试处于 untracked 状态；R1 必须运行 build 和只读 Playwright/静态检查。
- 不得把新模型或新策略默认展示混入该冻结。

### 4.3 Project-local skills

应纳入地基冻结范围：

```text
.agents/skills/frontend-design/LICENSE.txt
.agents/skills/frontend-design/SKILL.md
.agents/skills/tw-stock-agent-daily-prompt-maintenance/SKILL.md
.agents/skills/tw-stock-data-freshness-diagnosis/**
.agents/skills/tw-stock-frontend-workbench-ux-review/SKILL.md
.agents/skills/tw-stock-modular-integration-regression/SKILL.md
.agents/skills/tw-stock-new-model-onboarding/SKILL.md
.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
.agents/skills/tw-stock-readonly-e2e-acceptance/**
.agents/skills/tw-stock-research-context-analyst/**
.agents/skills/tw-stock-safety-boundary-review/**
docs/tw_skills_maintenance/**
skills-lock.json
```

冻结理由：

- S 路线已确认台股 skills 应以 project-local `.agents/skills/tw-stock-*` 为权威来源。
- 新研发节点必须依赖这些 skills 的触发边界，尤其是新模型、新策略、模块化回归、安全审查和前端 UX 审查。

风险：

- `.agents/skills/` 与 `docs/tw_skills_maintenance/` 仍为 untracked。
- 当前运行时仍可能显示 archive 旧 skills 元数据；R2 必须再次确认 project-local skills 与用户级 active 路径。

### 4.4 模块化合同与项目宪法

应纳入地基冻结范围：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/TW_CURRENT_PROJECT_DOC_ENTRY_AND_ARCHIVE_POLICY_CN.md
docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md
configs/tw_product_artifact_registry.yaml
```

冻结理由：

- 新模型/新策略研发必须从这些合同、宪法和 registry 出发。
- `configs/tw_product_artifact_registry.yaml` 当前声明默认模型、默认策略、artifact root、price sources 和安全开关，是后续研发入口。

注意：

- `configs/tw_product_artifact_registry.yaml` 当前未显示 modified，但仍是 R0/R3 的关键读取对象。
- 合同类文档中有 modified 与 untracked 混合状态，最终冻结时必须一起纳入审查。

### 4.5 日更 runbook / orchestrator

应纳入地基冻结范围：

```text
docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md
scripts/run_daily_tw_stock_auto_update.py
docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_EXPLAINED_FOR_BEGINNERS_CN.md
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_EXECUTION_AND_REVIEW_PLAN_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_EXECUTION_REPORT_CN.md
```

冻结理由：

- 新研发前必须固定 daily update 的只读链路解释、pending_asof、data freshness、artifact flow 与 forbidden actions。
- `scripts/run_daily_tw_stock_auto_update.py` 当前为 modified，R1 必须通过只读 orchestrator validator。

风险：

- legacy provider publish / accepted latest 代码仍可能存在，但当前要求默认不可达；R1/R3 要用 validator 和 registry 继续确认。

### 4.6 其他无关或需隔离变更

不建议混入“新模型/新策略研发”提交：

```text
comment.md
```

说明：

- `comment.md` 是协作/记录类文件，当前 modified，但不是 Agent/UI2/Skills/合同/日更地基的核心执行文件。
- 可随地基文档一起由统筹决定是否入库，但不能作为新模型/新策略研发输入依据。

当前未发现已经开始的新模型训练文件、新策略规则实现文件或默认模型/默认策略切换文件。

## 5. 建议进入本次地基冻结提交范围

建议本次冻结提交至少包含：

```text
.agents/skills/**
backend/app/routes/tw_stock.py
backend/app/services/tw_stock_agent_daily_prompt.py
backend/app/services/tw_stock_agent_simple_chat.py
backend/tests/test_tw_stock_agent_daily_prompt_builder.py
backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py
backend/tests/test_tw_stock_agent_daily_prompt_validator.py
backend/tests/test_tw_stock_agent_simple_chat.py
docs/tw_agent_daily_prompt_rebuild/**
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_EXECUTION_AND_REVIEW_PLAN_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/TW_CURRENT_PROJECT_DOC_ENTRY_AND_ARCHIVE_POLICY_CN.md
docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md
docs/tw_modular_daily_update_productization/PHASEUI2*.md
docs/tw_modular_daily_update_productization/PHASEUI_STRATEGY_WORKBENCH_FRONTEND_UX_REPAIR_WORK_CN.md
docs/tw_new_model_strategy_pre_rnd/**
docs/tw_skills_maintenance/**
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
frontend/tests/e2e/tw-stock-agent-simple-chat-network.mjs
frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
scripts/build_tw_agent_daily_prompt_artifact.py
scripts/validate_tw_agent_daily_prompt_artifact.py
scripts/run_daily_tw_stock_auto_update.py
skills-lock.json
```

是否把更早的 `docs/tw_modular_daily_update_productization/MODULAR_*`、`PHASEU3`、`PHASEV/W/X/YZ*` 等历史总结也纳入同一提交，应由统筹决定；它们不是 R0 新增内容，但可能是 UI2/产品化路线的审计背景。

## 6. 不能混入新模型/新策略研发的内容

进入第一轮新模型或新策略研发前，必须确认以下内容没有混入研发分支：

```text
新模型训练脚本或模型产物
新策略规则实现或策略默认切换
frontend 默认模型/策略展示切换
provider refresh / publish 触发逻辑
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target_position / target_weight 输出
OpenAI key 读取或真实 OpenAI smoke
```

本次 R0 盘点未执行这些动作，也未建议执行这些动作。

## 7. 风险与阻塞项

阻塞进入正式研发的事项：

1. 地基文件仍大量 untracked，尤其是 `.agents/skills/`、Agent simple-chat、UI2 测试、skills 维护文档和 pre-R&D 文档。未版本化前，不能作为稳定研发基线。
2. 业务代码 modified 状态需要 R1 只读回归验证，不能仅凭文档判断稳定。
3. `scripts/run_daily_tw_stock_auto_update.py` 已修改，必须用只读 orchestrator validator 确认未打开 provider/latest/monitor/broker/order 路径。

非阻塞但需记录的风险：

1. archive 旧 skills 仍存在，R2 必须再次确认不会作为 active skill 来源。
2. 当前验收还没有跑 R1 命令；R0 不负责证明代码可运行。
3. 新模型/新策略第一轮不应同时开两条线，否则 replay 结果无法归因。

## 8. R0 判定与下一步

R0 执行侧判定：

```text
有条件通过，可进入 R0 审查。
```

进入 R1 的前置条件：

```text
审查者确认本报告未漏列关键地基文件；
审查者确认冻结范围没有混入新模型/新策略研发实现；
审查者确认可以用只读命令做 R1 回归。
```

建议 R1 聚焦：

```text
py_compile Agent/simple-chat/orchestrator 脚本
pytest Agent daily prompt 与 simple-chat 测试
frontend build
frontend readonly/static/e2e checks
daily orchestrator readonly validator
modular contract regression
```

仍不得触发真实数据、provider publish/refresh、accepted latest、monitor 写入、broker/order 或 OpenAI key 读取。
