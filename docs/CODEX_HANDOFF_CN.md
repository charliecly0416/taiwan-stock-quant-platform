# Clean 当前接手指南

运行主线为 `product-clean`。5000 / 8000 已切换到 clean Gunicorn / Flask，systemd 管理 Web 和日更，前端 dist 由同一应用提供。当前结果和验收证据见 [主线验收](MAINLINE_ACCEPTANCE_CN.md)，不要用历史 BLOCKED 阶段报告覆盖实时状态。GitHub默认分支已切换为product-clean，旧main保留于legacy-main-20260928。

## 最短入口

1. [README](../README.md)、[架构](ARCHITECTURE_CN.md)、[运维](OPERATIONS_CN.md)。
2. [开发合同与检查](DEVELOPMENT_ONBOARDING_CN.md)。
3. `configs/product.yaml`、active_baseline_descriptor、tw_modular_registry、tw_product_artifact_registry、tw_replay_window_policy。
4. `clean_product/` 和 `backend/app/routes/`；前端 `frontend/src/`。

最近部署见 [2026-10-08 Shadow 递补验收](SHADOW_REFILL_DEPLOYMENT_20261008_CN.md)：运行代码 `6139891`，真实采集后的手动验证已 READY；当晚正式定时结果须读独立复核报告，不能以手动结果代替。

## 不能改变的产品边界

唯一 baseline 为 Model A `e4_frozen_qlib_2018_2022`，策略 `top50_exit_one_worst_sell`，执行 `next_open`。B19R2R 是 shadow，`production_allowed=false`，不进入默认或模拟账户。它的新日期特征缺失不阻塞 Model A。

这是研究产品和 simulation-only 持久账本，不是券商或真实订单系统。模拟账户独立认证和确认；比较页保持 no_apply。当前 Agent 使用每日产物本地解释，远端适配默认关闭。旧登录、旧账户没有自动迁移。

## 当前实现

- 全市场 Yahoo 行情接入唯一日更流程，增量刷新、复权修订回补、流式 Qlib provider。全市场只用于候选筛选；Model A 当日实际排名为 150 支，策略为 Top50。
- 每次发布生成独立 release，完整性通过后原子切 active.json；同日重跑不覆盖旧信号和问答。日更锁防并发，失败保留旧批次。
- 发布时物化当日与前一交易日信号，榜单变化和模拟账户可消费；selection_universe 使用 provider 实际生命周期，避免旧桥接文件缺日期。
- requests 只读本地数据，按标的读取行情，排名优先读已物化产物。
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

本机发布验收必须使用真实服务端口。`--serve-build` 只用于开发隔离验证。浏览器可保存截图文件，但当前会话禁止 view_image 或把图片传入模型；阅读 DOM、网络和控制台 JSON，人工视觉审查如未执行须写明。

当前正式部署使用原生 Python + systemd，独立运行目录由systemctl查询；升级时不要误操作源码checkout的旧数据。健康检查、去重备份、恢复及部署入口见运维手册，功能对应见 [替代清单](CLEAN_REPLACEMENT_CN.md)。定制台湾 Qlib wheel 与冻结模型是运行依赖；Docker 构建、远端大模型调用和旧账户迁移不在当前已验收范围。
