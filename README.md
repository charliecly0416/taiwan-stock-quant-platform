# Taiwan Stock Quant Research Platform

[![CI](https://github.com/charliecly0416/taiwan-stock-quant-platform/actions/workflows/ci.yml/badge.svg?branch=product-clean)](https://github.com/charliecly0416/taiwan-stock-quant-platform/actions/workflows/ci.yml)

一个面向台股的、可追溯的量化研究工作台。当前主线是 `product-clean`：Python / Flask 后端、Vite 原生 JavaScript 前端，以及由 systemd 管理的 Web 与日更服务。系统把行情、特征、模型信号、策略意图、回放和只读 API 串成一条 artifact-first 链路，并保留独立的 simulation-only 模拟账户。

这个项目适合展示三件事：如何把研究模型接入稳定的产品流程，如何让模型和策略边界可验证，以及如何在日更失败时安全保留上一份可用发布。它不连接券商，也不发送真实订单。

## 核心能力

- **Model A baseline**：`e4_frozen_qlib_2018_2022` 为当日 150 支候选评分，使用 `top50_exit_one_worst_sell` 策略和 `next_open` 执行语义。
- **Model B shadow**：`modelb_b19r2r_lambdarank_exact50_78f_v2` 只对 Model A 候选做只读重排；缺失 78 个 PIT-safe 特征的标的会被过滤，并按原始排名递补到 50 支。它保持 `production_allowed=false`，不会进入默认策略或模拟账户。
- **可恢复日更**：独立 release 目录、校验后原子切换 `active.json`、进程锁、失败保留上一批次，以及 manual / scheduled 状态分离。
- **模块化后端**：data → features → model signal → strategy intent → replay → readonly API / frontend，Flask route 只负责适配，业务组合集中在 `ProductService`。
- **研究前端**：排名、策略变化、个股行情、历史回放、模型比较、研究问答和系统运维页；前端不直接访问 Yahoo、FinMind 或语言模型。
- **可审计模拟账户**：独立 owner token、预览 / 确认、幂等、并发保护和 SQLite 账本，始终保持模拟语义。

## 快速了解项目

1. [面试演示路线](docs/INTERVIEW_DEMO_CN.md)：8–10 分钟的前端、后端和模拟账户讲解顺序。
2. [架构与模块](docs/ARCHITECTURE_CN.md)：数据流、模块职责、发布和故障隔离。
3. [运维手册](docs/OPERATIONS_CN.md)：健康检查、日更、备份、恢复和模拟令牌。
4. [开发入口](docs/DEVELOPMENT_ONBOARDING_CN.md)：配置、合同与测试。
5. [旧功能替代清单](docs/CLEAN_REPLACEMENT_CN.md)：clean 主线覆盖范围和维护边界。
6. [首日日更检查](docs/DAILY_CHAIN_CHECK_20260929_CN.md)：自动触发、失败重试与产物证据。
7. [当前主线验收](docs/MAINLINE_ACCEPTANCE_CN.md)：实测范围、证据与未覆盖项。

## 本地运行

前端使用 Node.js 24；pnpm 版本由 `frontend/package.json` 的 `packageManager` 固定。市场历史、冻结模型和定制 Qlib wheel 是本机运行资产，不随仓库提交；fresh checkout 需要按 [后端说明](backend/README.md) 准备这些依赖。

```bash
python -m pip install -r backend/requirements.txt -r backend/requirements-models.txt
corepack pnpm --dir frontend install
corepack pnpm --dir frontend build
python backend/run.py
```

服务启动后，前端默认在 `http://localhost:8000`，就绪检查为 `http://127.0.0.1:5000/api/ready`。真实采集和完整批次切换属于运维动作，测试使用 fixture 或隔离目录。

## 验证

```bash
pytest -q
node --test frontend/tests/*.test.js
corepack pnpm --dir frontend build
python scripts/verify_tw_stock_research_stack.py
python scripts/validate_arch1_baseline_descriptor.py
python scripts/validate_tw_daily_orchestrator_m3.py
python scripts/run_tw_modular_contract_regression.py
```

## 许可与数据边界

仓库包含根目录 Apache 2.0 许可和前端目录的单独 source-available 许可，请分别阅读 [LICENSE](LICENSE) 与 [frontend/LICENSE](frontend/LICENSE)。第三方组件和归属说明见 [NOTICE.md](NOTICE.md)。仓库不包含真实 API key、券商凭证、市场数据、冻结模型或生产账本。
