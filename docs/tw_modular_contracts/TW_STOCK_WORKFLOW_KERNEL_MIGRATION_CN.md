# 通用 Workflow Kernel 与迁移顺序

状态：WF-0 独立内核与 WF-1 replay observation sidecar。均未接入 daily、replay execution 或任何发布链路。

## 目标与边界

`tw_stock_workflow` 提供一个小型通用执行内核，将执行上下文、artifact 查询、模块注册、DAG、权限和运行记录统一起来。当前唯一内置模块 `research_history.observe` 只读 `data_tw/catalog/research_data_history/index.json`，用于证明既有 Model A 输入和信号可以通过标准引用串联。当前 adapter 只暴露具备标准 `artifact_type/model_id/asof/status/run_id` manifest 身份的 Model A artifact；Model B history 是缺少标准 `run_id` 的多文件研究 bundle，必须在后续通过独立 adapter 接入，不能弱化通用 manifest 校验来伪装成标准 signal。

内核不触发数据抓取、模型训练、provider/latest 写入、paper account、broker 或订单路径。`configs/workflows/research_history_observation.yaml` 只是只读 workflow spec，不在 cron 或 daily orchestrator 中注册。B19R2R 仍为 `production_allowed=false` 的研究 challenger。

WF-1 增加 `replay_window.observe`，只观察产品 registry 指向的 D7 readonly replay window index 及其 D6 artifact。它不会调用 replay runner、读取 policy 中的历史 experiment `source`、生成新收益结果或修改 index/latest。`configs/workflows/replay_window_observation.yaml` 同样没有接入 cron 或 daily。

## WF-1 Replay Observation 判定

当前权威入口为 `configs/tw_product_artifact_registry.yaml` 的 `readonly_replay_window_index_manifest`。adapter 只允许该入口及其引用位于 `data_tw/artifacts/readonly_replay_windows/`，并验证：

- D7 index 与 D6 artifact manifest 均被各自 checksum evidence 覆盖；
- 所有 D6 声明文件存在、位于 readonly product root 且 SHA256/bytes 一致；
- model、strategy、window、`next_open`、policy 与 readonly/no-write safety 字段一致；
- D6 manifest 的安全布尔字段必须是 JSON `true/false`，不接受可与布尔值相等的整数 `1/0`；产品 registry 的五项 no-write safety 声明也必须全部为严格布尔 `true`；
- 窄版 `validation_report.json` 为 `pass`，其实际 SHA256 也进入 workflow run identity；
- 重复 window identity、private experiment path 和 symlink escape 均 fail closed。

WF-1 暴露的类型是 `ReadonlyReplayWindowArtifact`，状态为 `INDEXED_READONLY`。其 run identity 同时绑定 D7 index manifest SHA256 与 D6 manifest SHA256。它不把现有 D6 宣称为完整 `ReplayResultArtifact`：正式 D6 缺少标准 `run_id/status`，且当前完整 validator 仍缺 `not_copied_from_legacy_replay`、`model_training_windows_traceable` 和 source OrderIntent evidence。因此 metadata 固定为 `full_replay_contract_status=HOLD` 并保留当前可见 gaps，module admission 固定为 false。即使窄观察字段被补齐，WF-1 也无权输出 PASS；完整准入只能由后续正式 validator/adapter 判定。这不是 baseline admission 或 replay execution 切换依据。

## WF-2A 完整合同 Candidate

WF-2A 修复了 canonical Model A 固定窗口 builder 与独立完整 validator，但尚未接入 workflow execution 或产品 index。当前审查候选为：

```text
data_tw/artifacts/readonly_replay_windows/wf2_candidate_model_a_v4/
  e4_frozen_qlib_2018_2022/top50_exit_one_worst_sell/20260101_20260507/
  wf2a_a1dd7d213f1913c9e53e90de/order_intent_replay_result/manifest.json
```

builder 继续复用 D3RR 的同一 `StrategyDecisionEngine -> OrderIntentArtifact -> ReplayExecutionEngine` 前向链。canonical ID `e4_frozen_qlib_2018_2022` 只能通过 `tw_modular_registry.yaml` 中 `frozen_qlib_2018_2022 -> canonical` 的明确 deprecated replacement，加上 E1 training manifest、冻结模型 SHA256、raw OOS score SHA256、ModelSignal 和 FullRank source lineage 后适配；不得静默改名或读取新的私有实验输入。

WF-2A 使用既有 canonical PriceStore manifest，并绑定 manifest 与 `prices.csv` SHA256。执行严格读取下一交易日 `open`，每日 mark-to-market 读取 `close`；只有 source row 声明 next-day execution available、target row 可交易且非停牌时才成交。缺 `open`、停牌或不可交易必须产生可追溯 skip，不得 fallback 到 `close`。PriceStore 全局 `PARTIAL_READY` 不自动等于候选不可用或可用，完整 validator 以本窗口实际所需标的逐行核对成交和缺价审计。

完整 validator 不采信 builder 的单一 `pass` 声明，而是独立检查 required columns、`execution_date > signal_date`、active quantity、next-open 价格、佣金/税、逐笔 cash/position、每日 holdings/NAV/return、重复持仓、负现金、缺价 skip、OrderIntent row lineage、训练窗口、canonical alias、forbidden fields/actions，以及 checksum manifest 对所有声明输入输出的精确覆盖。静态微型 fixture 同时覆盖篡改 execution price、quantity、cash、OrderIntent row、duplicate position、forbidden output、audit、training trace、checksum、tradable/halt/missing-open 的失败路径。

v4 候选完整 validator 当前通过，但 manifest 固定为 `status=CANDIDATE_HOLD`、`product_index_admission=false`。这只证明候选达到完整合同 gate，不会修改当前 D6/D7/latest、Model A baseline、daily/cron、provider、API 或前端。产品 index admission 需要后续独立审查与单独决定；WF-1 对当前正式 D6 的三项历史 gap 仍保持原判。

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

1. **Replay observation（WF-1 已完成 sidecar）**：专用只读 adapter 和 observation module 用固定 fixture、历史 manifest 与 backend index parity 验证，不替换现有 replay runner。完整 ReplayResult admission 仍为 HOLD。
2. **Replay execution（WF-2A candidate gate 已完成，workflow module 未开始）**：canonical Model A 固定窗口 candidate 已由同一 D3RR 前向引擎生成并通过完整 validator，但仍为 HOLD，未登记 D7。独立审查和 admission 通过后，才可另行设计 execution module。输出继续写隔离目录，保留旧入口并做一段时间双跑比对。
3. **Daily shadow orchestration**：仅在 replay 迁移稳定后，将无写入的 daily preflight/observation 作为 optional shadow DAG 接入；不得改变 pending、latest 或主线返回码。
4. **Daily stage migration**：逐阶段迁移 data、feature、Model A signal、strategy、snapshot，每阶段都保留现有合同、artifact validator 和回退入口。Model B 始终是非阻断 optional branch。
5. **切换与清理**：只有完整模块回归、M3 validator、readonly deployment acceptance 和连续自然调度证据均通过后，才另行提出切换决定。旧执行路径的删除需要独立影响闭包、备份和恢复验证。

任何迁移都不得通过 workflow 私下读取实验文件；依赖必须来自 registry 允许的标准 artifact。生产默认、provider/accepted latest 和 cron 变更需要单独授权，本文件不构成授权。
