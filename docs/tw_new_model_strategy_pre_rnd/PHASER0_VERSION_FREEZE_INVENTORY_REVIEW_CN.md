# Phase R0 审查报告：版本冻结与范围盘点

审查日期：2026-06-20

审查对象：

```text
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_EXECUTION_AND_REVIEW_PLAN_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_EXECUTION_REPORT_CN.md
git status --short --untracked-files=all
```

## 1. 审查结论

结论：有条件通过，允许进入 Phase R1 只读集成回归。

R0 执行报告正确把当前工作限定为新模型/新策略研发前的 readiness freeze 盘点，没有开始训练模型、没有新增策略规则、没有默认切换模型/策略、没有触发真实数据链路或交易链路。

进入正式新模型/新策略研发前仍有阻塞条件：

```text
Agent / UI2 / Skills / 合同 / 日更 runbook / pre-RND 文档仍大量处于 untracked 或 modified 状态；
这些地基文件必须先通过 R1 只读回归，并在最终 readiness 阶段纳入版本管理或等价冻结范围；
不能仅凭 R0 文件盘点就宣布研发基线稳定。
```

## 2. 审查依据

### 2.1 必读文件存在性通过

已抽查 R0 计划要求的必读文件，均存在：

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

### 2.2 git 状态分组基本完整

复核 `git status --short --untracked-files=all` 后，R0 报告已覆盖关键地基分组：

```text
Agent Daily Prompt / simple-chat
UI2 前端与 Playwright
project-local skills
模块化合同与项目宪法
日更 runbook / orchestrator
pre-RND 文档
协作记录类文件 comment.md
```

报告对以下关键文件或目录均有覆盖：

```text
backend/app/routes/tw_stock.py
backend/app/services/tw_stock_agent_daily_prompt.py
backend/app/services/tw_stock_agent_simple_chat.py
backend/tests/test_tw_stock_agent_daily_prompt_*.py
backend/tests/test_tw_stock_agent_simple_chat.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/**
frontend/tests/e2e/tw-stock-agent-simple-chat-network.mjs
frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
.agents/skills/**
docs/tw_agent_daily_prompt_rebuild/**
docs/tw_modular_daily_update_productization/PHASEUI2*.md
docs/tw_skills_maintenance/**
docs/tw_new_model_strategy_pre_rnd/**
scripts/build_tw_agent_daily_prompt_artifact.py
scripts/validate_tw_agent_daily_prompt_artifact.py
scripts/run_daily_tw_stock_auto_update.py
skills-lock.json
```

未发现关键地基文件被完全漏列。

### 2.3 未混入新模型/新策略研发实现

R0 报告明确把以下内容排除在第一轮新模型/新策略研发之前：

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

结合当前 `git status`，未看到新增的新模型训练产物、新策略规则实现或默认模型/策略切换文件。

### 2.4 Registry 入口方向正确

已抽查 `configs/tw_product_artifact_registry.yaml`，当前产品路径仍是 strict E4/YZ 只读配置，包含：

```text
readonly_only: true
base_model_id: e4_frozen_qlib_2018_2022
treatment_model_id: e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
default_strategy_rule: top50_exit_one_worst_sell
readonly_strategy_latest: data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
no_provider_publish: true
no_accepted_latest_switch: true
no_monitor_write: true
no_broker_order: true
```

这与 R0 报告强调的“新模型必须走 `ModelSignalArtifact`，新策略必须走 `OrderIntentArtifact`，不得直接切默认产品路径”一致。

## 3. 风险与要求

### 3.1 大量地基文件仍未版本化

`.agents/skills/`、Agent simple-chat、UI2 测试、skills 维护文档和 pre-RND 文档仍处于 untracked 状态。

这不是 R0 阻塞项，但它阻塞正式新模型/新策略研发。R1/R4 必须继续把“纳入版本管理或等价冻结”作为 readiness 条件。

### 3.2 R0 不能证明代码稳定

R0 是 inventory，不是 regression。业务代码 modified 状态包括：

```text
backend/app/routes/tw_stock.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/**
scripts/run_daily_tw_stock_auto_update.py
```

这些文件是否稳定必须由 R1 只读回归验证，不能用文档总结替代。

### 3.3 日更 orchestrator 修改必须重点审查

`scripts/run_daily_tw_stock_auto_update.py` 当前 modified。R1 必须使用只读 validator 检查它没有打开：

```text
provider refresh / publish
accepted latest switch
monitor writes
broker / order
真实数据拉取
OpenAI key 读取
```

### 3.4 Archive skills 残余风险仍需 R2 处理

R0 正确记录了 archive 旧 skills 仍存在。R2 必须复核：

```text
project-local .agents/skills/tw-stock-* 是权威来源；
/home/chuliyang/.agents/skills/tw-stock-* active 路径为空；
archive 目录不应作为运行时 active skill 来源。
```

## 4. 审查判定

Phase R0 判定：

```text
PASS_WITH_CONDITIONS
```

允许进入：

```text
Phase R1：只读集成回归
```

不允许直接进入：

```text
新模型训练
新策略实现
默认模型/策略切换
前端默认展示切换
provider publish / accepted latest switch
monitor / broker / order / OpenAI smoke
```

## 5. 给执行者的下一步

按 `docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_WORK_CN.md` 执行 Phase R1。

R1 的核心目标是用只读命令验证当前地基是否真的可运行：

```text
Agent daily prompt / simple-chat py_compile 与 pytest
frontend build
frontend simple-chat 静态检查
UI2 readonly Playwright fixture/evidence
daily orchestrator 只读 validator
modular contract regression
```

任何需要真实数据、provider publish、accepted latest、monitor 写入、broker/order 或 OpenAI key 的步骤都必须停止并报告。
