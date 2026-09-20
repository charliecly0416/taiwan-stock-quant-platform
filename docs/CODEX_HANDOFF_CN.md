# 新 Codex 接手指南

状态基准日期：2026-09-20。本文提供接手时的最短路径；详细规则以所链接的合同和 runbook 为准。

## 1. 先建立正确认知

当前项目已经从模型研发转入稳定运维：Model A 是唯一 active baseline，B19R2R 是冻结的研究 challenger。日常工作的优先级是保持 Model A 日更、观察 B19 自动影子、完成 prospective 结算证据，并修复真实运行问题。不要主动重新训练、调参或切换 baseline。

当前本机事实：

- Model A：`e4_frozen_qlib_2018_2022`。
- 默认策略：`top50_exit_one_worst_sell`；执行价：`next_open`。
- B19R2R：LightGBM LambdaRank，Model A Top50 内重排，78 个 PIT-safe 特征，TW7769 排除且不补位。
- B19R2R：`production_allowed=false`，只进入 comparison、prospective shadow 和 review report。
- 2026-09-18 的 scheduled full shadow 为 `BLOCKED`，`mainline_blocking=false`。
- 受控人工重试曾产生 `READY_RESEARCH_SHADOW`，但不能写成 scheduled 成功。
- 2026-09-19 是周六，latest 保持 2026-09-18 属于正常状态。

阅读架构时先区分三类状态：`CURRENT` 是当前真实产品，`SHADOW` 是不阻断 Model A 的观察链，`CONTRACT` 是尚未全面接入 runtime 的合同或模板。`tw_stock_workflow/` 已具备通用内核和若干模块，但日更、策略、回放、模拟账户仍在增量迁移，不能根据类名或 registry entry 宣称生产链已全部切换。

## 2. 阅读顺序

1. 根目录 `AGENTS.md`：强制安全、真相源和验证规则。
2. 本文：当前状态与处理流程。
3. `docs/PROJECT_INTRO_CN.md`：产品价值、用户流程和系统边界。
4. `docs/tw_modular_contracts/TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md`：第一技术入口，包含架构、模块实现、数据结构、数据流与追溯方法。
5. `docs/PRODUCT_OPERATIONS_REVIEW_CN.md`：最近一次总体审查与未闭环事项。
6. `docs/ops/STABLE_OPERATIONS_RUNBOOK_CN.md`：探针、备份、恢复、日志和部署验收。
7. `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`：开发红线。

遇到专项任务后，再从 `docs/DEVELOPMENT_ONBOARDING_CN.md` 进入相应合同或开发指南。不要从阶段历史报告反推当前默认状态。

## 3. 接手后的第一次只读检查

```bash
git status --short
curl -fsS http://127.0.0.1:5000/api/health
curl -fsS http://127.0.0.1:5000/api/ready | jq .
curl -fsS http://127.0.0.1:5000/api/tw-stock/quant/ops/daily-auto-update/status | jq .
curl -fsS http://127.0.0.1:5000/api/tw-stock/quant/ops/readonly-status | jq .
ps -eo pid,cmd | rg 'gunicorn|serve_frontend_static_proxy'
crontab -l
```

这些命令只观察状态。不要输出 `backend/.env`、进程环境、数据库 URL 或任何密钥。当前工作区长期包含大量未提交改动和本机 ignored 资产；禁止用 reset、checkout 或清理命令把它恢复成 Git HEAD。

判断顺序：

1. `/api/health` 是否存活。
2. `/api/ready` 是否为 `ready=true`，失败的是数据库、运行边界还是 artifact 合同。
3. daily status 的 `latest_asof`、`pending_asof`、最近 job 状态和原因。
4. readonly status 中 Model A、snapshot、Agent prompt 是否同日，B19 是否独立。
5. 当前日期是否为台湾交易日，目标数据在 provider 是否已经合法可得。

## 4. 四类工作怎么处理

### 日常运维

执行 `docs/ops/DAILY_OPERATIONS_CHECKLIST_CN.md`。先观察，自状态和 artifact 证据定位问题，再决定是否需要修复。不要为了“确认服务正常”手工跑真实日更、发布 provider 或改 latest。

### 故障修复

先固定失败 API、job ID、asof、错误码和证据目录。找到负责该阶段的模块，只改最小边界，并先跑 focused tests。若故障在 B19 shadow，确认 `mainline_blocking=false` 和 Model A 保护指针没有受影响；不得用手工成功覆盖 scheduled 失败事实。

### 新模型或策略

模型开发当前冻结，只有用户明确开启新路线时才进入。先写合同、registry、PIT/窗口设计和 validator，再训练或回放；任何 challenger 初始必须 `production_allowed=false`。详细流程见 `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`。

### 前端变更

页面通过 GET API 消费标准 artifact，不直读实验目录，也不在浏览器内重算模型或策略。核心研究结果不得因维护型状态接口失败而被清空。比较页保持 `no_apply`；模拟账户写操作属于独立流程。普通用户侧栏只保留台股研究、台股模拟账户和个人中心。旧 Phase YZ 或 paper decision 与当前 `signal_asof` 不同时只能显示历史状态，不能参与今日总览或 apply。涉及用户流程时运行 fixture Playwright 和桌面/平板/手机检查。

## 5. 权威状态如何判定

| 问题 | 权威来源 |
| --- | --- |
| 当前进程能否服务 | `GET /api/health`、`GET /api/ready` |
| 唯一 baseline 与默认策略 | `configs/active_baseline_descriptor.yaml` |
| 模型/策略允许的 consumer | `configs/tw_modular_registry.yaml` |
| 产品 artifact 路径 | `configs/tw_product_artifact_registry.yaml` |
| 回放可选范围 | `configs/tw_replay_window_policy.yaml` |
| 最近日更与 pending | daily status API 和对应 `job.json` |
| scheduled B19 状态 | readonly status 的 `b19r2r_shadow` 与自然 cron job |
| 历史比较结果 | comparison API 绑定的 manifest、validator、independent review |

配置存在只证明“具备该路径”，不证明自然任务已经成功。动态 API 成功也不能替代 artifact manifest、checksum 和 validator。

## 6. 当前应继续观察的事项

1. 下一个合法工作日 full lane 是否由当前精确 v2 wrapper 自动产生 B19 `READY_RESEARCH_SHADOW` 或可解释的 `BLOCKED`。
2. prospective event 是否在后续交易日自动结算，并形成足够样本的准入评估。
3. B19 异常是否持续与 Model A 主链、pending、latest 指针隔离。
4. 备份、日志轮转、数据库连接和 cron 是否保持健康。

这些事项没有完成前，B19 保持 shadow。它们不阻止 Model A 进入稳定运维。

## 7. 交付前

- 说明改了什么、为什么，以及是否影响 baseline、latest、cron 或 paper account。
- 运行与改动风险相匹配的 focused tests；合同跨模块变化时再跑模块回归。
- 用 `git diff --check` 检查补丁。
- 文档中的“当前状态”必须重新通过 GET API 或权威配置核对。
- 明确列出未运行的检查，不把本机结果称为云端 CI 或长期稳定性证明。
