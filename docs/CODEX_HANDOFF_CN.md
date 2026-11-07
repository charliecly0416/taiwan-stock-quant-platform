# Clean 当前接手指南

运行主线为 `product-clean`。5000 / 8000 已切换到 clean Gunicorn / Flask，systemd 管理 Web 和日更，前端 dist 由同一应用提供。当前结果和验收证据见 [主线验收](MAINLINE_ACCEPTANCE_CN.md)，不要用历史 BLOCKED 阶段报告覆盖实时状态。GitHub默认分支已切换为product-clean，旧main保留于legacy-main-20260928。

## 最短入口

1. [README](../README.md)、[架构](ARCHITECTURE_CN.md)、[运维](OPERATIONS_CN.md)。
2. [开发合同与检查](DEVELOPMENT_ONBOARDING_CN.md)。
3. `configs/product.yaml`、active_baseline_descriptor、tw_modular_registry、tw_product_artifact_registry、tw_replay_window_policy。
4. `clean_product/` 和 `backend/app/routes/`；前端 `frontend/src/`。

当前部署为2026-11-07两轨历史版本，运行目录 `~/.local/share/tw-stock-clean/releases/clean-20261107-audited`，数据截至11/6；代码身份见本机 `~/.local/state/tw-stock-clean/current-deployment.json`。已修复Shadow历史跨批次残留候选，以及个股非交易日混入provider的问题，以保存的独立Yahoo ^TWII日历约束行情。10/12–11/6正确为18个交易日，2,700条A分数与900条B分数已接入正式历史查询、比较和回放。补算历史有明确来源标记；默认仍A，B保持研究权限。详见 [当前验收](MAINLINE_ACCEPTANCE_CN.md)。

10/12起历史scheduled连续失败，恢复为manual；目前health保留 `SCHEDULED_DAILY_FAILED` 告警，不能因ready=true而宣称全自动连续成功。下一次正式日更计划11/9台北18:30，Shadow18:45，分别有两次晚间重试。待真实触发后检查完整发布，不能手动伪造scheduled结果。审查证据在仓库外 `~/.local/state/tw-stock-clean/audits/continuity-20261107/final/`。

## 不能改变的产品边界

唯一 baseline 为 Model A `e4_frozen_qlib_2018_2022`，策略 `top50_exit_one_worst_sell`，执行 `next_open`。B19R2R 是 shadow，`production_allowed=false`，不进入默认或模拟账户。它的新日期特征缺失不阻塞 Model A。

这是研究产品和 simulation-only 持久账本，不是券商或真实订单系统。模拟账户独立认证和确认；比较页保持 no_apply。当前 Agent 使用每日产物本地解释，远端适配默认关闭。旧登录、旧账户没有自动迁移。

## 当前实现

- 全市场 Yahoo 行情接入唯一日更流程，增量刷新、复权修订回补、独立指数交易日历、流式 Qlib provider。全市场只用于候选筛选；Model A 当日实际排名为150支，策略为Top50。
- 每次发布生成独立 release，完整性通过后原子切 active.json；同日重跑不覆盖旧信号和问答。日更锁防并发，失败保留旧批次。
- 默认发布物化当日与前一交易日信号，榜单变化和模拟账户可消费；历史修复可通过单次配置扩大至60交易日，正式默认仍为2。selection_universe使用provider实际生命周期。历史补算属于事后重建。
- 保存标准行情、日历、Qlib行情二进制、分数及manifest；Alpha158大矩阵按冻结配置重建。本次18日恢复只物化最终日Agent上下文与策略意图，不冒称历史问答完整。
- requests 只读本地数据，按标的读取行情，排名优先读已物化产物。
- 两轨通过统一 history/排名/变化/回放接口查询；日更信号保留原配置以支持后续历史读取，补算包独立导入产品store。默认仍A，B不进入模拟账户；详见运维“两轨历史”。
- 系统页展示模块串联与运行批次。运维区分 manual、scheduled、NO_NEW_MARKET_SESSION；定时器启用不等于完整定时采集成功。

## 开发与验收

先看 git status，保留未提交修改和本机数据资产。不读 backend/.env 或进程环境；不把模型、token、数据提交。不得为了“干净”删除不明依赖。代码测试优先 fixture / 隔离目录，不启动真实采集或切换 latest。

```bash
pytest -q
node --test frontend/tests/*.test.js
corepack pnpm --dir frontend build
python scripts/validate_arch1_baseline_descriptor.py
python scripts/validate_tw_daily_orchestrator_m3.py
python scripts/run_tw_modular_contract_regression.py
python scripts/verify_tw_stock_research_stack.py
TW_CLEAN_FRONTEND_URL=http://127.0.0.1:8000 python scripts/accept_clean_frontend.py
```

本机发布验收必须使用真实服务端口。`--serve-build` 只用于开发隔离验证。用户已重新允许 view_image，可结合截图视觉检查及 DOM、网络和控制台 JSON 验收；区分自动检查与实际执行的截图视觉审查，不将旧的“未审图”证据改写为已完成。

当前正式部署使用原生 Python + systemd，独立运行目录由systemctl查询；升级时不要误操作源码checkout的旧数据。健康检查、去重备份、恢复及部署入口见运维手册，功能对应见 [替代清单](CLEAN_REPLACEMENT_CN.md)。定制台湾 Qlib wheel 与冻结模型是运行依赖；Docker 构建、远端大模型调用和旧账户迁移不在当前已验收范围。
