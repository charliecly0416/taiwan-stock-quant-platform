# 清洁版只读 API

后端提供只读研究 API，以及独立认证的 SQLite 模拟账本（本机主线已启用）。它不连接实盘、券商或订单系统；clean owner token 也不等同于旧版登录系统。

```bash
pip install -c requirements-runtime.lock -r requirements.txt -r requirements-models.txt
python run.py
```

接口：

- `GET /api/health`：进程存活检查
- `GET /api/ready`：校验冻结基线身份、模型 SHA256、provider 日期与已物化信号；失败返回 503，不触发评分，不等于完整发布验收
- `GET /api/tw-stock/config`：模型、策略和数据配置
- `GET /api/tw-stock/overview`：模型、资料和日更总览
- `GET /api/tw-stock/rankings?model=...&date=...`：指定日期的模型排名
- `GET /api/tw-stock/compare?left=...&right=...&date=...`：两条模型轨道的只读比较；附 `start`/`end` 可同时返回历史模拟指标
- `GET /api/tw-stock/strategy?model=...&date=...`：策略意图预览
- `GET /api/tw-stock/ranking-changes?model=...&date=...`：榜单进入、离开和名次变化
- `GET /api/tw-stock/cross-analysis?model=...&date=...`：模型排名与行情技术背景
- `GET /api/tw-stock/data/<name>`：查询已治理数据
- `GET /api/tw-stock/data-status`：资料集状态
- `GET /api/tw-stock/operations/latest`：最近非 dry-run 日更状态，分别返回 latest_manual 和 latest_scheduled
- `GET /api/tw-stock/market/<symbol>?start=...&end=...`：个股行情
- `GET/POST /api/tw-stock/sim/accounts`、`/paper-portfolio/*`：独立认证的 owner-bound simulation ledger；启用后支持预览、确认、重置和历史记录，影子模型 BLOCKED
- `GET /api/tw-stock/paper?model=...&date=...`：兼容只读初始模拟状态，明确标记 `persisted=false`，与持久账本分开
- `GET /api/tw-stock/agent/context?model=...&date=...`：本地研究解释上下文
- `GET /api/tw-stock/agent/explain/<symbol>?model=...&date=...`：本地排序解释
- `POST /api/tw-stock/agent/simple-chat`：只读研究问答；仅接收 question、symbol、maxItems、date。先验证 DailyAgentPromptArtifact 的 checksum、日期、来源和冻结模型身份；默认本地，显式后端配置才可使用远端 JSON 适配器
- `GET /api/tw-stock/replay?model=...&start=...&end=...`：动态历史回放

Model A 主线 Yahoo 增量采集不依赖 FinMind；附加 FinMind 数据集需要后端凭据。只读 API 不触发采集。真实回放缺少所需价格时明确 BLOCKED，不自动降级成 fixture；fixture 仅用于隔离测试与显式 dry-run，不作为正式市场数据。

正式端口 5000 / 8000 已由 clean 服务接管。状态见 [主线验收](../docs/MAINLINE_ACCEPTANCE_CN.md)，服务与日更命令见 [运维手册](../docs/OPERATIONS_CN.md)。

## 容器与模型依赖

后端镜像现在从仓库根目录构建，使用显式文件清单：

```bash
docker build -f backend/Dockerfile -t tw-stock-clean-backend .
docker build -f frontend/Dockerfile -t tw-stock-clean-frontend frontend
```

根 `.dockerignore` 只允许后端入口、clean 模块和必要配置；市场数据、模型、`.env`、凭据和实验目录不进入镜像。运行时需要把注册的冻结模型和资料路径以只读方式挂载；缺失时 `/api/ready` 返回 503。

`requirements-models.txt` 固定本轮验证的 LightGBM 4.6.0、scikit-learn 1.8.0 和 pyarrow 23.0.1。新增日期的 Qlib 推理依赖台湾定制 Qlib 0.9.8.dev31（源码提交 `a4179eed3d32fd21c296345fb3fba14f3e01cdaa`）；它包含 REG_TW，不能用任意 PyPI Qlib 冒充。源码、构建依赖、运行锁和 wheel manifest 已提供，Docker named-context target 仍需可用 daemon。

前序隔离 venv 已验证定制 wheel 和依赖；当前本机运行使用原生 Python / Gunicorn / systemd。Docker 构建未完成，不是当前部署路径。

Agent 默认是 `artifact_local` 模式；显式启用后可使用经过过滤的后端 JSON 远端适配器。paper 的 owner-bound apply/reset 已完成 clean scope；旧数据库、旧登录身份、手工模拟草稿/取消流程仍未迁回。
