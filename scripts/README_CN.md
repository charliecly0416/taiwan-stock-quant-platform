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

当前目录已经完成一次低风险瘦身。172 个没有被配置、运行时模块、测试或 CI 直接引用的
阶段研究脚本，已移到
`scripts/archive/historical_research/root_recovered_20260927/`。另有 2 个被现行运维手册直接
调用的检查脚本留在根目录。归档脚本仍保留在 Git 中，
只用于审计和复现；需要重新使用时，先按当前合同重新检查，不要把归档脚本重新接回日更链路。

## 面试和日常维护只看这条主线

```text
scripts/run_tw_task.py
  -> tw_stock_workflow/task_dispatcher.py
  -> configs/tw_task_registry.yaml
  -> daily_update / readonly_backtest / readonly_model_comparison
```

日更任务继续由 `scripts/run_daily_tw_stock_auto_update.py` 执行，模型轨道在
`scripts/tw_daily_model_tracks.py`，模型适配在 `scripts/tw_daily_model_track_services.py`，
策略在 `tw_stock_strategy/`，历史回放由
`scripts/build_tw_readonly_replay_window_artifact.py` 和 `tw_stock_workflow/replay_execution.py`
完成。合同、部署和回归检查保留在根目录，因为配置、测试和 CI 会直接调用它们。

根目录保留的是稳定入口、当前支持模块和验证器；历史研究脚本不再平铺在这里。新增脚本前，
先判断能否放进现有模块或任务注册表，再决定是否需要新增文件。

生产调用方只使用以下稳定入口：

- `scripts/run_tw_task.py`
- `scripts/run_daily_tw_stock_auto_update.py`
- `scripts/run_tw_stock_workflow.py`
- `scripts/ensure_tw_stock_services.sh`

新增任务优先注册到统一任务入口；不要为同一条主流程再创建新的根目录脚本。
