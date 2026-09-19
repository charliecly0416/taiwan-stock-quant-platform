# 开发接手指南

本文给出最短开发路径。项目的详细模块规范见 `tw_modular_contracts/TW_DEVELOPER_TEST_AND_EXPERIMENT_PLAYBOOK_CN.md`。

## 1. 开始前

```bash
git status --short
```

当前工作区可能包含用户和前序 agent 的大量未提交改动，也包含不受 Git 管理的生产 artifact。不要 reset、checkout、clean 或覆盖现有改动。先读根目录 `AGENTS.md` 和 `CODEX_HANDOFF_CN.md`，再确认任务属于哪个模块。

权威默认口径：

- baseline：`configs/active_baseline_descriptor.yaml`。
- 模块能力和 consumer：`configs/tw_modular_registry.yaml`。
- 产品路径：`configs/tw_product_artifact_registry.yaml`。
- 回放窗口：`configs/tw_replay_window_policy.yaml`。

旧阶段报告、旧 LTR 路径或前端显示文案不能覆盖这些配置与 live readiness。

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

## 7. 完成标准

- 实现与对应合同、registry 和安全边界一致。
- focused tests 覆盖真实行为或失败边界，而不是复制实现。
- 失败不会覆写 previous latest，也不会污染 Model A pending。
- 文档说明当前事实、验证证据和限制。
- `git diff --check` 通过，没有秘密、生成缓存或无关格式化改动。
- 删除行为另行遵守 `AGENTS.md` 的仓库外备份、SHA256 和隔离恢复要求。
