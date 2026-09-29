# Taiwan Stock Clean Research Product

GitHub 默认分支与当前运行主线均为 `product-clean`：Python / Flask 后端、Vite 原生 JavaScript 前端，以及 systemd 管理的 Web 与日更服务。产品用于台股只读研究和独立模拟账户，不连接券商或真实订单。

- 前端：`http://localhost:8000`；后端：`http://127.0.0.1:5000/api/ready`。
- Model A：`e4_frozen_qlib_2018_2022`。全市场行情用于流动性筛选，冻结模型只为当日 150 支候选评分；Top50 使用 `top50_exit_one_worst_sell` / `next_open`。
- B19R2R 保持研究影子模型，不进入默认策略或模拟账户；历史比较可用，新日期特征不足会明确提示。

## 展示与维护

1. [面试演示路线](docs/INTERVIEW_DEMO_CN.md)：前端操作、架构讲解和代码入口。
2. [架构与模块](docs/ARCHITECTURE_CN.md)：数据流、扩展点、发布与故障隔离。
3. [运维手册](docs/OPERATIONS_CN.md)：状态、日志、日更、模拟令牌与恢复。
4. [开发入口](docs/DEVELOPMENT_ONBOARDING_CN.md)：配置、合同与测试。
5. [旧功能替代清单](docs/CLEAN_REPLACEMENT_CN.md)：保留范围、账户迁移与长期维护边界。\n6. [2026-09-29 首日日更检查](docs/DAILY_CHAIN_CHECK_20260929_CN.md)：自动触发、失败重试与成功产物证据。
7. [当前主线验收](docs/MAINLINE_ACCEPTANCE_CN.md)：本机实测、证据与未覆盖范围。

## 开发

前端使用 Node.js 24；pnpm 版本由 `frontend/package.json` 的 `packageManager` 统一指定，CI 与容器使用相同版本来源。

```bash
python -m pip install -r backend/requirements.txt -r backend/requirements-models.txt
corepack pnpm --dir frontend install
corepack pnpm --dir frontend build
python backend/run.py
```

市场历史与冻结模型是本机资产，不随仓库提交；fresh checkout 需按配置准备。冻结 Qlib 使用已锁定的台湾定制 wheel，见 [后端说明](backend/README.md)。Docker 是可选打包方式，当前正式服务使用原生 Python 与 systemd。

```bash
pytest -q
node --test frontend/tests/*.test.js
python scripts/verify_tw_stock_research_stack.py
python scripts/validate_arch1_baseline_descriptor.py
python scripts/validate_tw_daily_orchestrator_m3.py
python scripts/run_tw_modular_contract_regression.py
TW_CLEAN_FRONTEND_URL=http://127.0.0.1:8000 python scripts/accept_clean_frontend.py
```

真实采集与完整批次切换是运维动作，测试使用 fixture / 隔离目录。前端不直接访问 Yahoo、FinMind 或语言模型。
