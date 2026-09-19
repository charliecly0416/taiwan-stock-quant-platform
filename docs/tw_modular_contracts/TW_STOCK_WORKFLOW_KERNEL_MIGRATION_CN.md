# 通用 Workflow Kernel 与迁移顺序

状态：WF-0 独立内核、WF-1 replay observation sidecar 与 WF-2B 隔离 replay candidate execution module 已完成。均未接入 daily、cron 或任何发布链路。

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

## WF-2B 隔离 Workflow Execution Module

WF-2B 已将同一 canonical Model A 固定窗口 builder 和完整 validator 包装为显式注册的 `replay_candidate.build_validate` module。独立 spec 位于：

```text
configs/workflows/model_a_replay_candidate_execution.yaml
```

module 只接受 Model A `e4_frozen_qlib_2018_2022`、默认策略 `top50_exit_one_worst_sell` 和固定窗口 `2026-01-01..2026-05-07`，要求 `artifact.read` 与 `replay.candidate.write` 两项权限。B19R2R、其他模型、策略或窗口覆盖以及自定义输出路径均 fail closed。

`ReplayCandidateInputAdapter` 每次解析输入时先运行 WF-2A 完整 validator，再绑定 v4 candidate 的 39-file checksum closure，并额外绑定 workflow execution module、builder、完整 validator 与实际 replay runner 的 SHA256。workflow run identity 因此覆盖 baseline descriptor、module registry、replay policy、baseline source、PriceStore manifest 与 prices、E1 training manifest/model/raw score、ModelSignal/FullRank manifests 及其 outputs、source identity audit、ReplayResult 合同文件和执行代码版本。kernel 在 module 调用前后重新解析这些 refs；任一输入或执行代码变化都会形成不同 identity 和 implementation digest，TOCTOU 则使节点失败。

输出目录由 module 固定在显式 `ExecutionContext.workspace` 下：

```text
<workspace>/artifacts/wf2b_model_a_replay_candidate/implementation_<digest>/
```

workspace 必须位于 repository 外，解析后的输出仍必须在 workspace 内，因此不能写入正式 D6/D7/latest 或借 symlink 逃逸。implementation digest 由上述四个实现文件的路径、SHA256 与大小规范化重算；相同实现只有在 terminal success cached-output hook 重新核对 output 结构、固定 manifest 路径与 SHA256、当前 implementation namespace、source identity 和完整 validator 后才能复用。manifest 缺失或被篡改会 fail closed，不自动删除、重建或隔离；任一实现哈希变化则写入新的命名空间，不能复用旧实现生成的 candidate。输出继续固定为 `CANDIDATE_HOLD` 和 `product_index_admission=false`。

WF-2B 只是隔离 candidate execution module 完成，不代表产品 index admission、baseline 切换或正式 replay execution 切换。该 spec 未登记到 daily orchestrator 或 cron，也不触发训练、真实数据抓取、provider、accepted latest、paper account、broker 或订单路径。

## WF-3 Daily Readonly Shadow DAG

WF-3 已把固定的 replay-window observation 作为日更 `finalize_job()` 的单一非阻断 sidecar 接口接入。实现逻辑位于 `scripts/tw_daily_workflow_readonly_shadow.py`，日更入口只负责显式注入 repo、固定 spec/runner、六个受保护路径、pending、installed cron 和既有 `run_cmd`。开关为 `--enable-workflow-readonly-shadow` / `TW_DAILY_AUTO_ENABLE_WORKFLOW_READONLY_SHADOW`，源码默认关闭；本阶段没有修改 installed cron。DNG9 summary 的提前退出发生在 job 创建和 finalizer 之前，因此不会误触发 WF-3。

启用后只允许固定的 `configs/workflows/replay_window_observation.yaml` 合同：唯一 module 为 `replay_window.observe`，唯一权限为 `replay.read`，模式为 `readonly`，超时固定 60 秒。workspace 固定为 `<job_dir>/workflow_readonly_shadow`，job_dir/workspace symlink 或解析后逃出 job 目录会在 runner 前被拒绝。runner 也必须精确为 repo 内 regular、非 symlink 的 `scripts/run_tw_stock_workflow.py`，不能通过参数替换为其他脚本。`replay_candidate.build_validate`、`replay.candidate.write`、训练、provider、latest、pending recovery 和交易路径均不在该 sidecar 能力内。

runner stdout 不能单独证明成功。WF-3 会读取 `<workspace>/runs/<run_id>.json`，核对 stdout 与持久化 record 的 workflow ID/version/run ID/status，确认唯一节点仍为 `replay_window.observe`；成功记录还必须保持 `full_replay_contract_admission=false`、artifact metadata `full_replay_contract_status=HOLD` 和 observed artifact asof `2026-05-07`。daily target asof 独立记录为 `daily_job_asof`，不会把固定历史观察窗口伪装成当天 replay。

在调用前后，sidecar 指纹化 formal provider calendar、qlib accepted latest、legacy Option C latest、controlled Model A latest、readonly snapshot latest、Agent prompt latest，并单独指纹化 `pending_asof.json` 与 installed cron。`SUCCEEDED`、`BLOCKED`、`FAILED`、timeout、异常或证据不一致都只归一化为 `job["workflow_readonly_shadow"]` 证据；任何失败均为 `mainline_blocking=false`，不改变原 daily status、caller return code、pending、latest 或主线后续语义。

## 合同

- `ExecutionContext` 明确声明 `mode`、`asof`、带时区的 `decision_cutoff`、隔离 `workspace` 和权限集合。
- YAML 只声明稳定的 `module` ID。`ModuleRegistry` 只接受应用代码显式注册的实例，不读取 import path、类名或任意 Python target。
- `ArtifactResolver` 在返回引用前解析真实路径，拒绝仓库外路径和 symlink escape；显式 `--history-index` 也必须位于同一 repo root。resolver 核对 index 声明的 manifest SHA256 与完整 manifest identity，缺字段即失败。
- DAG 在运行前拒绝重复节点、未知依赖、自依赖、环和未注册模块。每个节点必须显式声明 `required`、`optional` 或 `nonblocking` policy，运行状态为 `SUCCEEDED`、`BLOCKED`、`FAILED` 或 `SKIPPED`。required 节点不能依赖 nonblocking 分支。
- 节点结果由不可变 `StageResult` dataclass 表达，再统一序列化为 run evidence，避免各模块自行拼接状态结构。
- required 节点失败会使 workflow 失败；required 节点阻断或因依赖未成功而跳过会使 workflow 阻断。若 required 后继因上游 `FAILED` 跳过，总体仍为失败。optional/nonblocking 节点不会污染无依赖的 required 分支。
- run identity 由 workflow spec、规范化 execution context，以及各节点在执行前解析并校验的 artifact refs（包括 manifest SHA256）的 canonical JSON 决定，不包含时钟时间。engine 在模块调用前后自行重新解析并严格比较输入；这项校验不依赖模块输出内容。相同输入在同一 workspace 重跑时，FAILED/BLOCKED terminal 与未声明 cached-output hook 的旧 module 保持既有复用语义；SUCCEEDED terminal 中声明 hook 的 module 必须先复验自身输出，复验失败即 fail closed，不返回 idempotent success。
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
2. **Replay execution（WF-2A candidate gate 与 WF-2B isolated module 已完成）**：canonical Model A 固定窗口 candidate 已由同一 D3RR 前向引擎生成并通过完整 validator，workflow module 也可在显式外部 workspace 中幂等构建和验证候选；结果仍为 HOLD，未登记 D7。产品 admission 与正式切换仍需独立决定，旧入口继续保留。
3. **Daily shadow orchestration（WF-3 已完成、源码默认关闭）**：固定 replay observation 已作为非阻断 sidecar 接入统一 finalizer；是否加入 installed cron 和连续自然调度观察仍需独立运维决定。
4. **Daily stage migration**：逐阶段迁移 data、feature、Model A signal、strategy、snapshot，每阶段都保留现有合同、artifact validator 和回退入口。Model B 始终是非阻断 optional branch。
5. **切换与清理**：只有完整模块回归、M3 validator、readonly deployment acceptance 和连续自然调度证据均通过后，才另行提出切换决定。旧执行路径的删除需要独立影响闭包、备份和恢复验证。

任何迁移都不得通过 workflow 私下读取实验文件；依赖必须来自 registry 允许的标准 artifact。生产默认、provider/accepted latest 和 cron 变更需要单独授权，本文件不构成授权。
