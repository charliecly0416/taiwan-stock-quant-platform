# 脚本目录治理

脚本按生命周期管理，避免把一次性研究脚本误当成产品主链。生命周期索引在
`configs/script_lifecycle_registry.yaml`，`python scripts/check_tw_project.py`
会统计当前目录的分类。

| 生命周期 | 含义 | 维护要求 |
| --- | --- | --- |
| `stable_entrypoint` | 日更、统一任务入口、服务和 workflow 入口 | 必须有 focused test；修改前检查文档和 Cron 引用 |
| `validation` | 合同、部署、回归和 readiness 检查 | 只读优先；不得写入产品 latest |
| `reusable_support` | 当前被主链或 validator 导入的辅助模块 | 视为公共代码，保持接口稳定 |
| `research_or_migration` | 研究、证据构建、迁移和一次性工具 | 必须声明输入、输出和是否允许 publish |
| `archived` | 已完成阶段的历史脚本 | 仅用于审计和复现，不作为新生产依赖 |
| `archive_pending` | 尚未完成归类的脚本 | 不得作为新的生产依赖；新增后应补充索引规则 |

当前只建立索引和检查，不批量移动历史脚本。许多配置、文档和证据引用仍使用
`scripts/<name>` 路径，直接移动会制造隐性断链。后续归档应按小批次进行：先搜索引用，
再迁移、保留兼容 wrapper，最后运行 `make check-project` 和相关回归。

生产调用方只使用以下稳定入口：

- `scripts/run_tw_task.py`
- `scripts/run_daily_tw_stock_auto_update.py`
- `scripts/run_tw_stock_workflow.py`
- `scripts/ensure_tw_stock_services.sh`

新增任务优先注册到统一任务入口；不要为同一条主流程再创建新的根目录脚本。
