# ARCH-0..ARCH-4 稳定运维影响审计执行报告

日期：2026-09-13
范围：对 ARCH-0 至 ARCH-4 以来工作区改动、生产日更入口、runtime stages、backend route registration/API、frontend defaults、registry/descriptor、installed cron/systemd 与 protected latest fingerprints 做只读审计。未修改任何生产代码、配置、cron、latest 或 artifact；本文件为唯一新增审计输出。

## 结论

`PASS_WITH_FINDINGS / STABLE_OPS_DEPLOYMENT_REVIEW_REQUIRED`

当前运行时行为在本机工作区通过编译、M3 日更静态门禁及聚焦 API/route 测试，ARCH-2/3/4 的 protected fingerprint 证据均保持 unchanged。发现一个部署完整性高风险项：tracked 的 `run_daily_tw_stock_auto_update.py` 导入两个未被 git 跟踪的 runtime 模块；若部署流程只同步 tracked 文件，日更入口会在 import 阶段失败。该项不通过修改代码解决，需在发布前由 owner 明确纳入版本/部署清单。

## 1. 改动分类

| 阶段 | 生产边界改动 | evidence/测试改动 | 审计结论 |
|---|---|---|---|
| ARCH-0/1 | 未发现生产入口、registry、descriptor 或 latest 的本轮修改 | 大量 `data_tw/experiments/project_runtime_convergence/**` evidence | 未见生产回归；untracked evidence 不应进入运行时发布包 |
| ARCH-2 | `scripts/run_daily_tw_stock_auto_update.py` 接入 named stage adapters；`scripts/tw_daily_runtime_stages.py`、`scripts/tw_daily_stage_adapters.py` 为工作区未跟踪依赖 | `tests/unit/test_arch2_runtime_stages.py` 增补 128 行 | 行为测试通过；部署依赖未闭合（高风险） |
| ARCH-3 | `backend/app/routes/__init__.py` 注册拆分 blueprint；`tw_stock.py` 移除重复 decorators；新增 agent/replay/paper/ops/context route modules | ARCH-3 boundary contract 与 extraction tests | app route map 无重复规则，聚焦 API tests 通过 |
| ARCH-4 | frontend monitor 使用 composables；paper action 强制 `paper_only=true`；backtest payload 保持 `persist=false` | ARCH-4 extraction tests、frontend static check | 未发现默认模型/策略切换；readonly/simulation flags 保持 |

工作区存在 15 个 tracked modified 文件，以及大量 user-owned untracked code/docs/evidence。未将无关 untracked 文件纳入本审计结论，也未回滚任何改动。

## 2. 日更入口与 runtime stages

- `python -m py_compile` 对 `run_daily_tw_stock_auto_update.py`、`tw_daily_runtime_stages.py`、`tw_daily_stage_adapters.py` 及 backend 拆分 routes 全部通过。
- `validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json`：`ok=true`；默认 provider refresh/publish/accepted-latest 均不可达，legacy gate 默认关闭，broker/order 与 monitor-write runtime patterns 均为空。
- M3 仍报告 legacy provider/accepted-latest 代码存在的 warning；这是显式 gate 设计，不是默认路径通过证明。
- `run_daily_tw_stock_auto_update.py` 当前新增 `from tw_daily_stage_adapters import ...`；`scripts/tw_daily_runtime_stages.py` 与 `scripts/tw_daily_stage_adapters.py` 均为 `git ls-files` 未跟踪。发布包若遗漏它们将产生 ModuleNotFoundError，需在 deployment manifest/commit 中闭合。

## 3. Backend route registration/API

- `create_app('testing')` route map：319 rules，319 个 `(rule, methods)` 唯一；关键 `/api/tw-stock/current-strategy-context`、`/agent/context`、`/readonly-replay-window-index`、`/paper-portfolio/state` 均各一条归属明确。
- ARCH-3/4 backend 聚焦测试：23 passed；tw-stock backtest/observation/paper/replay tests：40 passed。
- 未发现拆分 blueprint 改变模型 A-only 默认或策略 `top50_exit_one_worst_sell` 的测试回归。
- app factory 本地检查因未配置 PostgreSQL 产生初始化 warning/error 日志，但不影响静态 route 注册；未执行写入型 API。

## 4. Frontend defaults 与边界

- `tw-stock-phase-yz-productization-check.mjs` 通过；默认 readonly replay 使用 `e4_frozen_qlib_2018_2022` 与 `top50_exit_one_worst_sell`，旧 display alias 仅兼容展示。
- composables 仅委托既有 API；paper apply/reset payload 加入 `paper_only=true`；backtest payload 固定 `persist=false` 且 `enableMtf=false`。
- 未发现 frontend default 指向 Model B 或调用 broker/order/target position 的新增路径。

## 5. Registry/descriptor 与 cron/systemd

- `configs/active_baseline_descriptor.yaml` 当前仍 `MODEL_A_ONLY`，Model B 为 `PROSPECTIVE_SHADOW`、`production_default=false`、`eligible_for_baseline=false`；descriptor validator 34/34 checks pass。
- `tw_product_artifact_registry.yaml` 的 Model B `production_selectable=true/frontend_selectable=true` 与 descriptor shadow-only 语义仍存在既有冲突；本审计未修改，需单独 registry repair decision。
- `tw-daily-auto-update.installed.cron` 与 `actual_crontab.after_fpala_enable_20260911T124124Z` byte-identical（SHA256 `4957e913faeb332da006005c8bd56597e3c5733c9fbf5f9b3d2c8c9ab1339c7a`）。实际 crontab 含明确 `FPALA_*` 与 `DAPR18_*` authorization，并开启 `TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH=true`；这是受控授权生产发布行为，不是 no-write cron。未发现额外 tw-stock systemd unit。

## 6. Protected fingerprints 与验证记录

ARCH-2/3/4 evidence 均记录 protected latest unchanged；当前重新计算与以下值一致：

```text
agent_daily_prompt/latest.json                         c957abb93bcd79c7dafd482665ad50e7d92f980e471c2e92f5faa95cef06e841
readonly_strategy_snapshot/latest.json                 993ea914438a2401efe4e31578243bcaf14c04d342ec22b6c3e3d396d4dae912
signals/e4_frozen_qlib_2018_2022/latest.json           7ebcb3e6c6a5ad27a8927a017c6d311fce5b49469831ae0029e92088b554f909
option_c_daily_signal/latest_signal.json                bcb04c0be160292e5b33b7dd0ae8350787ded8f946cb5f24c915bc0a1174ce67
cron installed manifest                                  4957e913faeb332da006005c8bd56597e3c5733c9fbf5f9b3d2c8c9ab1339c7a
```

验证：`py_compile` pass；M3 validator `ok=true`；backend 40 + ARCH2/3/4 23 tests pass；frontend Phase-YZ static check pass；`git diff --check` pass。未运行 provider、training、scoring、replay、broker 或写入型 endpoint。

## 7. 后续门禁

1. 在任何稳定运维发布前，将 `tw_daily_runtime_stages.py` 与 `tw_daily_stage_adapters.py` 纳入同一受控 commit/deployment manifest，并复跑 py_compile/M3/readonly tests。
2. 由 registry owner 单独处理 Model B `production_selectable/frontend_selectable` 与 shadow descriptor 冲突；不得在本审计中隐式修复或切换默认。
3. 保留当前 FPALA/DAPR18 exact authorization 与 cron fingerprint；若要回到 no-write/observation cron，需人工授权并重新做 before/after fingerprint 审查。
