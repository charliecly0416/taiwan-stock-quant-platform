# 开发接手指南

本文给出最短开发路径。项目的详细模块规范见 `tw_modular_contracts/TW_DEVELOPER_TEST_AND_EXPERIMENT_PLAYBOOK_CN.md`。

## 1. 开始前

```bash
git status --short
```

当前工作区可能包含用户和前序 agent 的大量未提交改动，也包含不受 Git 管理的生产 artifact。不要 reset、checkout、clean 或覆盖现有改动。先读根目录 `AGENTS.md`、`CODEX_HANDOFF_CN.md` 和 `tw_modular_contracts/TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md`，再确认任务属于哪个模块。

权威默认口径：

- baseline：`configs/active_baseline_descriptor.yaml`。
- 模块能力和 consumer：`configs/tw_modular_registry.yaml`。
- 产品路径：`configs/tw_product_artifact_registry.yaml`。
- 回放窗口：`configs/tw_replay_window_policy.yaml`。

旧阶段报告、旧 LTR 路径或前端显示文案不能覆盖这些配置与 live readiness。

模块地图使用三个成熟度标签：`CURRENT` 是当前真实产品链，`SHADOW` 是不阻断 Model A 的观察链，`CONTRACT` 只是合同或迁移地基。看到 registry entry、golden sample 或 workflow module 时，必须先确认标签，不能把“接口存在”直接写成“生产已使用”。

## 2. 模块优先的开发方式

```text
确定模块
  -> 阅读合同
  -> 声明 registry/dependency/policy
  -> 实现标准 artifact 或 API
  -> validator/golden sample/focused tests
  -> 跨模块回归
  -> 只读前端或受控模拟流程
```

| 任务 | 第一入口 |
| --- | --- |
| 数据源/标准化 | `docs/tw_modular_contracts/DATA_SOURCE_CONTRACT_CN.md` |
| PIT 特征 | `docs/tw_modular_contracts/FEATURE_ARTIFACT_CONTRACT_CN.md` |
| 新模型/adapter | `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md` |
| 新策略 | `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md` 和 `configs/strategy_dependencies/` |
| 组合状态 | `docs/tw_modular_contracts/PORTFOLIO_STATE_ARTIFACT_CONTRACT_CN.md` |
| 回放 | `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md` |
| readonly 前端/API | `docs/tw_modular_contracts/FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md` |
| 日更 | `docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md` |
| Agent | `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md` |
| 新模型/策略完整流程 | `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md` |

下游不得读取上游私有 CSV 或实验目录。模型输出分数，策略输出意图，回放计算结果，前端读取 API；不要把这些职责放进同一个脚本。

### 2.1 统一任务入口

跨模块流程优先通过统一任务入口运行：

```bash
python scripts/run_tw_task.py \
  --request configs/tasks/readonly_backtest_example.yaml \
  --validate-only
```

结构分为三层：

```text
TaskRequest -> configs/tw_task_registry.yaml -> registered executor/workflow
```

- `TaskRequest` 只包含任务类型和业务参数。
- registry 固定 executor、参数 schema、workflow spec 和依赖配置。
- `TaskDispatcher` 负责校验、run identity、隔离目录和统一结果。
- executor 只调用已有日更、artifact builder 或 `WorkflowEngine`，不复制业务逻辑。

新增流程时，先判断能否只新增 `configs/workflows/*.yaml` 并使用 `workflow_spec_v1`。确实需要新的外部边界时，才新增一个小 executor，并同时登记参数 schema、固定 bindings 和 focused tests。请求不得接受任意脚本路径、import path 或 shell command。

当前已注册：

| task_type | 用途 | 实际执行 |
| --- | --- | --- |
| `daily_update` | 日更与模型轨道 | 现有日更 orchestrator |
| `readonly_backtest` | 模型、策略、窗口回放 | 标准 ReplayResult candidate builder |
| `readonly_model_comparison` | A/A+B 历史比较 | 现有 WorkflowEngine DAG |

实现与扩展规则见 `tw_modular_contracts/TW_UNIFIED_TASK_ENTRY_PLAN_CN.md`。

## 3. 当前模型规则

Model A 是唯一 active baseline。B19R2R 是 frozen research challenger，不能因为历史回放较好就切默认。涉及 B19 的开发必须保持：

- Model A 同日 exact Top50 边界。
- 78 个冻结特征的顺序与 schema。
- PIT/available_at 检查。
- TW7769 排除且不补位。
- `production_allowed=false`、`no_apply=true`。
- 禁止进入 frontend default、provider latest、paper portfolio、broker/order。

训练、调参、窗口选择和 baseline admission 是不同任务。用户明确重启模型研究前，不主动训练或优化。

## 4. 测试矩阵

只运行与改动相匹配的检查；纯文档改动不需要重复完整模型回归。

| 改动类型 | 最低验证 |
| --- | --- |
| 文档 | 链接/API/命令检查，`git diff --check` |
| backend route/service | 对应 focused pytest，必要时 research stack |
| artifact/registry/contract | validator、正负 golden sample、模块合同回归 |
| 日更 orchestrator | focused daily tests、M3 validator、保护指针检查 |
| frontend | focused static/unit check、`pnpm build` |
| 用户主流程 | fixture Playwright、network/console audit、响应式截图 |
| 部署/readiness | 备用端口 readonly deployment acceptance |

常用高层命令：

```bash
PYTHONPATH=.:backend python backend/scripts/verify_tw_stock_research_stack.py
python scripts/validate_arch1_baseline_descriptor.py --json
python scripts/validate_tw_daily_orchestrator_m3.py \
  --audit-script scripts/run_daily_tw_stock_auto_update.py --json
PYTHONPATH=.:backend python scripts/run_tw_modular_contract_regression.py \
  --out-dir tmp/modular_contract_regression_onboarding --json
cd frontend && corepack pnpm build
```

这些命令不应被机械地全部运行。先跑 focused tests；只有合同、共享链路、发布或 readiness 改动扩大了影响范围时，再运行高层回归。

## 5. 本地运行与生产资产

安装方式见 `USER_GUIDE_CN.md`。开发启动前需要自己的 PostgreSQL、持久 `SECRET_KEY` 和管理员密码。不要使用示例密钥，也不要读取或复制本机 `backend/.env`。

生产数据与冻结模型位于 ignored 路径，fresh checkout 不含这些资产。fixture 只能验证 reader、API 和 UI 合同，不能证明 live 数据新鲜度。禁止在运行实例上执行 asset replacement 或 demo generator 作为健康检查。

## 6. API 与前端边界

主要只读入口：

```text
GET /api/ready
GET /api/tw-stock/current-strategy-context
GET /api/tw-stock/readonly-strategy-snapshot
GET /api/tw-stock/readonly-replay-window
GET /api/tw-stock/readonly/model-strategy-comparison
GET /api/tw-stock/quant/ops/daily-auto-update/status
GET /api/tw-stock/quant/ops/readonly-status
```

比较页的模型/策略下拉框只选择历史展示，不修改 runtime。模拟账户的 apply/reset 是独立、显式、simulation-only 的写路径；不要把两者合并。

普通用户目前只看到台股研究、台股模拟账户和个人中心。旧 Phase YZ 或 paper decision 只能在其 `signal_asof` 与当前策略日期一致时进入今日状态；异日结果必须保持历史标记并禁止 apply。

## 7. 完成标准

- 实现与对应合同、registry 和安全边界一致。
- focused tests 覆盖真实行为或失败边界，而不是复制实现。
- 失败不会覆写 previous latest，也不会污染 Model A pending。
- 文档说明当前事实、验证证据和限制。
- `git diff --check` 通过，没有秘密、生成缓存或无关格式化改动。
- 删除行为另行遵守 `AGENTS.md` 的仓库外备份、SHA256 和隔离恢复要求。
