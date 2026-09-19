# 通用 Workflow Kernel 与迁移顺序

状态：WF-0 独立内核，尚未接入 daily、replay 或任何发布链路。

## 目标与边界

`tw_stock_workflow` 提供一个小型通用执行内核，将执行上下文、artifact 查询、模块注册、DAG、权限和运行记录统一起来。当前唯一内置模块 `research_history.observe` 只读 `data_tw/catalog/research_data_history/index.json`，用于证明既有 Model A 输入和信号可以通过标准引用串联。当前 adapter 只暴露具备标准 `artifact_type/model_id/asof/status/run_id` manifest 身份的 Model A artifact；Model B history 是缺少标准 `run_id` 的多文件研究 bundle，必须在后续通过独立 adapter 接入，不能弱化通用 manifest 校验来伪装成标准 signal。

内核不触发数据抓取、模型训练、provider/latest 写入、paper account、broker 或订单路径。`configs/workflows/research_history_observation.yaml` 只是只读 workflow spec，不在 cron 或 daily orchestrator 中注册。B19R2R 仍为 `production_allowed=false` 的研究 challenger。

## 合同

- `ExecutionContext` 明确声明 `mode`、`asof`、带时区的 `decision_cutoff`、隔离 `workspace` 和权限集合。
- YAML 只声明稳定的 `module` ID。`ModuleRegistry` 只接受应用代码显式注册的实例，不读取 import path、类名或任意 Python target。
- `ArtifactResolver` 在返回引用前解析真实路径，拒绝仓库外路径和 symlink escape；显式 `--history-index` 也必须位于同一 repo root。resolver 核对 index 声明的 manifest SHA256 与完整 manifest identity，缺字段即失败。
- DAG 在运行前拒绝重复节点、未知依赖、自依赖、环和未注册模块。每个节点必须显式声明 `required`、`optional` 或 `nonblocking` policy，运行状态为 `SUCCEEDED`、`BLOCKED`、`FAILED` 或 `SKIPPED`。required 节点不能依赖 nonblocking 分支。
- 节点结果由不可变 `StageResult` dataclass 表达，再统一序列化为 run evidence，避免各模块自行拼接状态结构。
- required 节点失败会使 workflow 失败；required 节点阻断或因依赖未成功而跳过会使 workflow 阻断。若 required 后继因上游 `FAILED` 跳过，总体仍为失败。optional/nonblocking 节点不会污染无依赖的 required 分支。
- run identity 由 workflow spec、规范化 execution context，以及各节点在执行前解析并校验的 artifact refs（包括 manifest SHA256）的 canonical JSON 决定，不包含时钟时间。engine 在模块调用前后自行重新解析并严格比较输入；这项校验不依赖模块输出内容。相同输入在同一 workspace 重跑直接返回已有 terminal record。
- `RunRegistry` 使用文件锁、临时文件、文件与目录 `fsync` 和 `os.replace` 写入 `<workspace>/runs/<run_id>.json`。所有入口只接受 `wf_<24 hex>` run ID。读取或复用时会验证完整 RUNNING/terminal 结构、重新计算保存的 identity payload，并核对 workflow、context、artifact 输入、节点结果和总体状态。损坏记录、路径穿越、身份冲突或遗留 `RUNNING` 记录均 fail closed。

## CLI

CLI 只解析参数并调用 service。`--workspace` 为必填，避免默认写入现有运维目录。示例只观察既有 artifact：

```bash
PYTHONPATH=. python3 scripts/run_tw_stock_workflow.py \
  --spec configs/workflows/research_history_observation.yaml \
  --mode readonly \
  --asof 2026-09-18 \
  --decision-cutoff 2026-09-18T10:38:46+00:00 \
  --permission artifact.read \
  --workspace /tmp/tw-stock-workflow-observation
```

## 后续迁移顺序

1. **Replay observation**：先新增只读 replay adapter 和 observation module，用固定 fixture、历史 manifest 与 parity validator 验证，不替换现有 replay runner。
2. **Replay execution**：把单一 replay 阶段包装成显式 module；输出仍写隔离目录，经既有 validator 通过后才允许下游读取。保留旧入口并做一段时间双跑比对。
3. **Daily shadow orchestration**：仅在 replay 迁移稳定后，将无写入的 daily preflight/observation 作为 optional shadow DAG 接入；不得改变 pending、latest 或主线返回码。
4. **Daily stage migration**：逐阶段迁移 data、feature、Model A signal、strategy、snapshot，每阶段都保留现有合同、artifact validator 和回退入口。Model B 始终是非阻断 optional branch。
5. **切换与清理**：只有完整模块回归、M3 validator、readonly deployment acceptance 和连续自然调度证据均通过后，才另行提出切换决定。旧执行路径的删除需要独立影响闭包、备份和恢复验证。

任何迁移都不得通过 workflow 私下读取实验文件；依赖必须来自 registry 允许的标准 artifact。生产默认、provider/accepted latest 和 cron 变更需要单独授权，本文件不构成授权。
