# 台股项目后端代码框架与完整链路

状态基准：2026-09-24。

本文只回答一个问题：**从一个任务开始，到数据、模型、策略、回放和前端 API，代码是怎样组织和串起来的。**

阅读本文时请记住当前产品边界：这是只读研究产品和 simulation-only 模拟账户。Model A 是唯一 active baseline；B19R2R 是只读比较和日更 shadow，不是默认模型，也不能生成真实订单。

更详细的字段合同见：

- [项目模块地图与数据流](TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md)
- [数据模块地图与统一接口](TW_DATA_MODULE_MAP_AND_INTERFACES_CN.md)
- [开发接手指南](../DEVELOPMENT_ONBOARDING_CN.md)
- [稳定运维手册](../ops/STABLE_OPERATIONS_RUNBOOK_CN.md)

## 1. 先看目录

```text
backend/
└── app/
    ├── __init__.py              Flask 应用工厂和通用 JSON/CORS 配置
    ├── routes/                  HTTP 路由，只接收参数和返回响应
    ├── services/                业务服务，读取 artifact、组织查询和任务提交
    ├── data_sources/            通用行情数据源接口，例如 TW 股票 K 线
    ├── data_providers/          新闻、指数、情绪等 provider
    ├── config/                  Flask/数据库/外部服务配置
    └── utils/                   数据库、认证、缓存、日志等基础设施

tw_stock_workflow/
├── task_dispatcher.py           所有注册任务的统一调度器
├── service.py                    构造 WorkflowEngine 和模块注册表
├── engine.py                     YAML DAG 执行引擎
├── modules.py                    模块协议、注册和执行
├── artifacts.py                  artifact 查询、路径和身份校验
├── dual_track.py                 Model A / Model A+B 标准轨道
├── replay.py                     只读 ReplayResult 读取和校验
├── readonly_snapshot.py          只读策略快照读取和校验
└── types.py                      ExecutionContext 等公共类型

tw_stock_strategy/
└── top50_exit_one_worst_sell.py  当前策略的纯规则内核

scripts/
├── run_tw_task.py                统一命令行入口
├── run_daily_tw_stock_auto_update.py
│                                  日更内部 orchestrator
├── build_tw_readonly_replay_window_artifact.py
│                                  回放产物 builder
└── tw_daily_model_tracks.py      日更 ModelTrack fan-out

configs/
├── tw_task_registry.yaml         任务类型、executor、参数和绑定文件
├── tasks/*.yaml                   一次任务的请求参数
├── daily_model_tracks.yaml        日更运行时的模型轨道
├── readonly_model_tracks.yaml    模型治理、默认项、可用 consumer
├── active_baseline_descriptor.yaml 当前唯一 baseline
├── tw_modular_registry.yaml      模块合同和 consumer 边界
├── tw_replay_window_policy.yaml  回放准入和日期窗口
└── workflows/*.yaml              WorkflowEngine 的 DAG
```

最重要的边界是：

```text
脚本/cron 负责触发
TaskDispatcher 负责选择受控任务
WorkflowEngine 负责模块 DAG
Module 负责一段业务转换
Artifact 负责模块之间的稳定数据格式
Flask route/service 负责读取和展示
```

## 2. 一次请求的总流程

无论是 cron 日更、命令行回测，还是前端动态回放，核心关系都是：

```text
请求文件或 HTTP 请求
        |
        v
TaskDispatcher.plan()
        |
        +--> 参数 schema / registry / 模型策略治理校验
        |
        v
TaskDispatcher.dispatch()
        |
        +--> daily_update_v1
        |       -> run_daily_tw_stock_auto_update.py
        |
        +--> readonly_backtest_v1
        |       -> build_tw_readonly_replay_window_artifact.py
        |
        +--> workflow_spec_v1
                -> WorkflowEngine -> Module DAG

统一结果：data_tw/ops/unified_tasks/{task_type}/{run_id}/result.json
```

统一入口并不重新实现模型或回放。它只是把不同任务的参数变成一个受控计划，再委托已有 executor。

## 3. 统一入口的实际代码

### 3.1 调用方

命令行入口是 [scripts/run_tw_task.py](../../scripts/run_tw_task.py)：

```python
dispatcher = TaskDispatcher(ROOT)

if args.status is not None:
    result = dispatcher.recent_status(task_type, limit=args.limit)
else:
    request = load_task_request(request_path)
    result = (
        {**dispatcher.plan(request).to_dict(), "status": "VALIDATED"}
        if args.validate_only
        else dispatcher.dispatch(request)
    )
```

它有三种使用方式：

```bash
# 只检查请求和执行计划
python scripts/run_tw_task.py \
  --request configs/tasks/daily_update.yaml \
  --validate-only

# 执行注册任务
python scripts/run_tw_task.py \
  --request configs/tasks/readonly_backtest_example.yaml

# 只读查看历史任务
python scripts/run_tw_task.py --status readonly_backtest --limit 5
```

### 3.2 registry 决定任务能做什么

[configs/tw_task_registry.yaml](../../configs/tw_task_registry.yaml) 不是普通说明文件，而是任务注册表。它把外部的 `task_type` 绑定到内部 executor：

```yaml
tasks:
  daily_update:
    executor_id: daily_update_v1
    defaults:
      asof: auto
      model_track_ids:
        - model_a_only
        - model_a_plus_b_b19r2r
      finmind_scope: full
    bindings:
      runner: scripts/run_daily_tw_stock_auto_update.py
      model_track_governance: configs/readonly_model_tracks.yaml
      model_track_runtime: configs/daily_model_tracks.yaml

  readonly_backtest:
    executor_id: readonly_backtest_v1
    bindings:
      runner: scripts/build_tw_readonly_replay_window_artifact.py
      model_tracks: configs/readonly_model_tracks.yaml
      replay_policy: configs/tw_replay_window_policy.yaml
      modular_registry: configs/tw_modular_registry.yaml
```

因此请求不能自己传入任意脚本：

```yaml
schema_version: tw.task.request.v1
task_type: readonly_backtest
parameters:
  model_track_id: model_a_only
  strategy_rule: top50_exit_one_worst_sell
  start_date: '2026-01-01'
  end_date: '2026-05-07'
  timeout_seconds: 1200
```

### 3.3 `TaskDispatcher` 的四个关键动作

代码在 [tw_stock_workflow/task_dispatcher.py](../../tw_stock_workflow/task_dispatcher.py)。可以把它读成下面四步：

```python
def plan(self, request):
    normalized, entry = self._normalize_request(request)

    if entry["executor_id"] == "daily_update_v1":
        details = self._daily_plan(normalized["parameters"], entry["bindings"])
    elif entry["executor_id"] == "readonly_backtest_v1":
        details = self._backtest_plan(normalized["parameters"], entry["bindings"])
    else:
        details = self._workflow_plan(normalized["parameters"], entry["bindings"])

    run_id = stable_hash(normalized, entry)
    return TaskPlan(run_id=run_id, details=details, ...)
```

```python
def dispatch(self, request):
    plan = self.plan(request)
    write_json(plan.run_dir / "normalized_request.json", plan.normalized_request)
    write_json(plan.run_dir / "plan.json", plan.to_dict())

    if plan.executor_id == "daily_update_v1":
        execution = self._execute_daily(plan)
    elif plan.executor_id == "readonly_backtest_v1":
        execution = self._execute_backtest(plan)
    else:
        execution = self._execute_workflow(plan)

    result = build_task_record(plan, execution)
    write_json(plan.run_dir / "result.json", result)
    return result
```

`run_id` 由规范化请求和 registry 内容生成，所以相同请求可以幂等复用，执行证据不会散落到随机目录。

## 4. 日更完整链路

### 4.1 cron 到日更 orchestrator

实际调用关系是：

```text
cron
  -> scripts/run_daily_env.sh
  -> scripts/run_tw_task.py
  -> TaskDispatcher._execute_daily()
  -> scripts/run_daily_tw_stock_auto_update.py
```

日更请求有两个典型配置：

```yaml
# configs/tasks/daily_update_base.yaml
task_type: daily_update
parameters:
  asof: auto
  model_track_ids: [model_a_only]
  finmind_scope: daily
```

```yaml
# configs/tasks/daily_update.yaml
task_type: daily_update
parameters:
  asof: auto
  model_track_ids:
    - model_a_only
    - model_a_plus_b_b19r2r
  finmind_scope: full
```

### 4.2 日更 orchestrator 的阶段

内部实现集中在 [scripts/run_daily_tw_stock_auto_update.py](../../scripts/run_daily_tw_stock_auto_update.py)。为了阅读，可以把它分成这些阶段：

```python
def main():
    args = parse_args()
    asof = resolve_target_asof(args)
    job_dir = create_job_dir(asof)

    source = acquire_sources(
        asof=asof,
        finmind_scope=args.finmind_scope,
        job_dir=job_dir,
    )
    normalized = build_normalized_inputs(source, asof=asof)
    model_signals = run_model_tracks(normalized, args.model_track_ids)
    strategy_context = build_strategy_context(model_signals, asof=asof)
    product_latest = run_dapr18_readonly_publish(
        model_signals=model_signals,
        strategy_context=strategy_context,
        asof=asof,
    )
    write_daily_chain_status(
        job_dir=job_dir,
        asof=asof,
        product_latest=product_latest,
    )
```

上面是阅读骨架；真实函数还包含 provider timeout、pending、交易日历、PIT、protected pointer 和 forbidden action 审计。不要把这个骨架当成可以复制运行的新脚本。

日更证据目录：

```text
data_tw/ops/daily_auto_update/{job_id}/
├── job.json
├── finmind_stdout.txt
├── yahoo_stdout.txt
├── daily_source_inventory.json
├── same_run_handoff_validation.json
├── daily_chain_status.json
└── dapr18_*_audit.json
```

`daily_chain_status.json` 是日链状态，不是模型信号本身。DAPR18 确认三条只读产品 latest 都对齐目标日后，终态应为：

```json
{
  "state": "READONLY_CONTEXT_READY",
  "provider_bridge_readiness_state": "READONLY_PRODUCT_ARTIFACT_READY",
  "frontend_payload_status": "READONLY_SOURCE_CONTEXT_READY",
  "publish_latest_gate_status": "READONLY_LATEST_UPDATED_BY_EXPLICIT_GATE"
}
```

这不表示 qlib accepted latest 或 formal provider 已经切换；它们仍由各自指针和 validator 证明。

## 5. 数据模块：抓取、标准化、查询

项目没有一个会同时抓数据、训练模型和返回 API 的巨大 `DataService`。数据职责分三层：

```text
Acquisition
  -> 原始来源和抓取证据

Artifact production
  -> normalized data / PIT FeatureArtifact / PriceStore / manifest

Access / Serving
  -> ArtifactResolver 和 readonly service 查询已验证产物
```

### 5.1 Acquisition 输入输出

输入概念：

```yaml
asof: '2026-09-22'
scope: full
symbols: ['2330', '2317']
source_profile: tw-stock-default
decision_cutoff: '2026-09-22T08:30:00+08:00'
```

输出概念：

```json
{
  "schema_version": "tw.data.source.run.v1",
  "run_id": "source_20260922_...",
  "status": "READY",
  "provider": "finmind",
  "asof": "2026-09-22",
  "available_at": "2026-09-22T18:10:00+08:00",
  "raw_artifacts": [],
  "coverage_audit": {},
  "no_provider_publish": true,
  "no_accepted_latest_switch": true
}
```

日更抓取脚本可以写隔离运行目录，但失败不能覆盖上一版 latest。FinMind institutional/margin timeout 必须保留 stderr 和 incomplete evidence，不能回退旧缓存伪装为成功。

### 5.2 Artifact production 输入输出

标准化阶段把来源数据变成下游可引用的 artifact：

```json
{
  "artifact_type": "feature_artifact",
  "schema_version": "feature_artifact.v1",
  "run_id": "source_20260922_...",
  "asof": "2026-09-22",
  "available_at": "2026-09-22T18:10:00+08:00",
  "source_artifacts": ["..."],
  "output_path": "...",
  "manifest_sha256": "...",
  "pit_policy": "available_at <= signal_asof",
  "validation_status": "PASS"
}
```

### 5.3 Access / Serving 的核心对象

[tw_stock_workflow/artifacts.py](../../tw_stock_workflow/artifacts.py) 的 `ArtifactResolver` 查询的是经过身份约束的 `ArtifactRef`：

```python
refs = resolver.query(
    artifact_type="model_signal",
    model_id="e4_frozen_qlib_2018_2022",
    asof="2026-09-22",
    status="accepted",
)
```

下游得到的是：

```text
ArtifactRef
├── adapter_id
├── artifact_type
├── model_id
├── asof
├── status
├── run_id
├── path
├── manifest_path
├── manifest_sha256
└── metadata
```

前端和策略不应该直接读取 provider 私有目录或实验 CSV。

## 6. 模型模块：Model A 和 Model A+B

### 6.1 两份模型配置

运行时 fan-out 看 [configs/daily_model_tracks.yaml](../../configs/daily_model_tracks.yaml)：

```yaml
dependency_mode: independent
tracks:
  model_a_only:
    runtime_adapter_id: daily_model_a_v1
    model_id: e4_frozen_qlib_2018_2022
    internal_stages: [model_a_score]
    consumes_track_outputs: []

  model_a_plus_b_b19r2r:
    runtime_adapter_id: daily_model_a_plus_b_b19r2r_v1
    model_id: modelb_b19r2r_lambdarank_exact50_78f_v2
    internal_stages: [model_a_score, b19r2r_rerank]
    consumes_track_outputs: []
```

治理状态看 [configs/readonly_model_tracks.yaml](../../configs/readonly_model_tracks.yaml)：

```yaml
model_a_only:
  workflow_policy: required
  governance_status: active_baseline
  production_default: true
  virtual_account_eligible: true

model_a_plus_b_b19r2r:
  workflow_policy: nonblocking
  governance_status: research_candidate
  production_default: false
  virtual_account_eligible: false
```

`dependency_mode: independent` 表示两条外部轨道各自接收同一批日更输入。A+B 的内部流程可以先得到 A 的边界再做 B 重排，但对 orchestrator 来说它不是读取 Model A track 的输出文件，而是自己的一个标准 adapter。

### 6.2 ModelSignalArtifact 是统一输出

Model A 适配器的核心转换是：

```python
def _adapt_model_a(model_a):
    model_a["candidate_rank"] = model_a["full_qlib_rank"]
    model_a["buy_score"] = model_a["model_a_raw_score"]
    model_a["raw_score"] = model_a["buy_score"]
    return model_a
```

统一信号行示例：

```json
{
  "date": "2026-09-22",
  "instrument": "TW2330",
  "model_name": "e4_frozen_qlib_2018_2022",
  "model_family": "qlib",
  "candidate_rank": 2,
  "buy_score": 0.1227,
  "raw_score": 0.1227,
  "score_rank": 2,
  "full_qlib_rank": 2,
  "signal_asof": "2026-09-22",
  "available_at": "2026-09-22",
  "source_artifact": "..."
}
```

B19R2R 的实现入口在 [tw_stock_workflow/dual_track.py](../../tw_stock_workflow/dual_track.py) 的 `_adapt_b19r2r`：

```python
model_a = _adapt_model_a(model_a, ...)
features = read_feature_parquet(feature_path, feature_order=feature_order_78)

assert len(feature_order_78) == 78
assert (features["available_at"] <= features["signal_asof"]).all()

original_top50 = model_a["full_qlib_rank"] <= 50
scored = original_top50 & (model_a["instrument"] != "TW7769")
model_a.loc[scored, "buy_score"] = frozen_lgbm.predict(
    features.loc[scored, feature_order_78]
)
return model_a
```

策略只看 `candidate_rank`、`buy_score` 和模型身份，不知道 Qlib、LightGBM 或 78 个特征的路径。

## 7. 策略模块：排名变成 OrderIntent

策略纯函数在 [tw_stock_strategy/top50_exit_one_worst_sell.py](../../tw_stock_strategy/top50_exit_one_worst_sell.py)。它不读取行情、不加载模型、不计算成交价。

输入是：

```python
model_signal_rows = [
    {
        "date": "2026-09-22",
        "instrument": "TW2330",
        "candidate_rank": 2,
        "buy_score": 0.1227,
        "score_rank": 2,
        "full_qlib_rank": 2,
        "model_name": "e4_frozen_qlib_2018_2022",
        "model_family": "qlib",
        "signal_asof": "2026-09-22",
        "available_at": "2026-09-22",
        "source_artifact": "...",
    }
]

portfolio_state_rows = [
    {
        "asof_date": "2026-09-21",
        "instrument": "TW3006",
        "quantity": 1000,
        "cost_basis": 123.4,
        "current_holding_flag": True,
    }
]
```

调用：

```python
decision = decide_for_model(
    model_signal_rows,
    portfolio_state_rows,
    CANONICAL_CONFIG,
    model_id=model_id,
    model_family=model_family,
    candidate_rank_policy=candidate_rank_policy,
)
```

当前配置的关键约束：

```python
CANONICAL_CONFIG = {
    "strategy_rule": "top50_exit_one_worst_sell",
    "target_holding_count": 10,
    "candidate_k": 50,
    "max_buy_count": 1,
    "max_sell_count": 1,
    "sell_boundary": "candidate_rank_gt_candidate_k",
    "buy_order": "buy_score_desc_instrument_asc",
}
```

输出是策略意图，不是订单：

```json
{
  "signal_date": "2026-09-22",
  "instrument": "TW2330",
  "intent_action": "buy",
  "intent_reason": "top50_exit_one_worst_sell_buy",
  "strategy_rule": "top50_exit_one_worst_sell",
  "model_name": "e4_frozen_qlib_2018_2022",
  "candidate_rank": 2,
  "buy_rank": 2,
  "full_qlib_rank": 2,
  "current_holding_flag": false,
  "not_order": true
}
```

策略输出禁止包含：`execution_price`、`quantity`、`cash`、`fee`、`tax`、`nav`、`broker_order_id`、`target_weight` 等字段。它们属于回放或模拟账户边界。

## 8. 回放模块：OrderIntent 变成 ReplayResult

只读回放由 [scripts/build_tw_readonly_replay_window_artifact.py](../../scripts/build_tw_readonly_replay_window_artifact.py) 执行，底层合同和读取适配器在 [tw_stock_workflow/replay.py](../../tw_stock_workflow/replay.py)。

输入：

```json
{
  "model_id": "e4_frozen_qlib_2018_2022",
  "strategy_rule": "top50_exit_one_worst_sell",
  "start_date": "2026-01-01",
  "end_date": "2026-05-07",
  "price_store_manifest": "...",
  "baseline_manifest": "...",
  "replay_policy": "configs/tw_replay_window_policy.yaml"
}
```

回放按交易日循环：

```text
for signal_date in [start_date, end_date]:
    signals = read_model_signal(signal_date)
    portfolio = read_previous_snapshot(signal_date)
    intent = strategy.decide(signals, portfolio)
    next_open = price_store.next_session_open(intent.instrument)
    state = apply_simulated_execution(intent, next_open)
    write_daily_nav(state)
```

回放可以计算成交价、数量、费用、税、现金和净值，因为这些字段只存在于回放输出，不会反向传给模型或策略。

输出目录：

```text
data_tw/artifacts/readonly_replay_windows/{run_id}/
├── manifest.json
├── summary.csv
├── daily_nav.csv
├── actions.csv
├── snapshots.csv
├── decision_source_audit.json
├── forbidden_scope_audit.json
└── action_lineage_audit.json
```

`ReplayResult` 仍然是 candidate/read-only 结果，`product_index_admission=false`，不能直接变成真实订单或 baseline。

## 9. WorkflowEngine：如何编排模块

WorkflowEngine 由 [tw_stock_workflow/service.py](../../tw_stock_workflow/service.py) 构造：

```python
def build_default_engine(repo_root):
    resolver = ArtifactResolver(repo_root)
    modules = ModuleRegistry()
    modules.register(ResearchHistoryObservation())
    modules.register(ReadonlyReplayWindowObservation(...))
    modules.register(ReadonlyStrategySnapshotObservation(...))
    modules.register(ReplayCandidateExecution(repo_root))
    modules.register(ReadonlyModelTrackExecution(repo_root, track_id))
    modules.register(ReadonlyModelTrackComparison(repo_root))
    return WorkflowEngine(modules, resolver)
```

每个 Module 共享同一个最小接口：

```python
class Module(Protocol):
    module_id: str
    required_permissions: frozenset[str]

    def resolve_artifact_inputs(context, config, resolver) -> list[ArtifactRef]: ...

    def execute(context, config, inputs, resolver) -> dict[str, Any]: ...
```

工作流 YAML 描述节点，而不是写 Python 调用顺序：

```yaml
workflow_id: readonly_dual_model_track_comparison
version: '1'
nodes:
  - node_id: model_a
    module: model_track.model_a_only
    policy: required

  - node_id: model_a_plus_b
    module: model_track.model_a_plus_b_b19r2r
    policy: nonblocking

  - node_id: comparison_catalog
    module: readonly_model_track.catalog
    policy: required
    needs: [model_a, model_a_plus_b]
```

引擎对每个节点做四件事：

1. 解析并锁定 artifact 输入。
2. 检查所需权限。
3. 检查上游依赖是否成功。
4. 执行后再次检查输入是否漂移。

`required` 节点失败会让工作流失败；`nonblocking` 节点失败只记录 shadow 缺口。Model A 是 required，B19R2R 是 nonblocking。

## 10. Flask API：路由、服务、artifact

### 10.1 应用工厂和路由注册

[backend/app/__init__.py](../../backend/app/__init__.py) 创建 Flask 应用；[backend/app/routes/__init__.py](../../backend/app/routes/__init__.py) 注册 blueprint：

```python
def create_app(config_name="default"):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = validate_secret_key()
    app.json_provider_class = SafeJSONProvider
    CORS(app, origins=allowed_origins)
    register_routes(app)
    return app
```

```python
app.register_blueprint(tw_stock_context_bp, url_prefix="/api/tw-stock")
app.register_blueprint(readonly_strategy_snapshot_bp, url_prefix="/api/tw-stock")
app.register_blueprint(readonly_model_strategy_comparison_bp, url_prefix="/api/tw-stock")
app.register_blueprint(tw_stock_dynamic_replay_bp, url_prefix="/api/tw-stock")
```

标准关系是：

```text
route -> service -> artifact / database -> DTO -> JSON
```

route 不负责抓 provider、加载模型或实现回放。

### 10.2 当前策略上下文

```http
GET /api/tw-stock/current-strategy-context
```

路由最终调用 [backend/app/services/tw_stock_current_strategy_context.py](../../backend/app/services/tw_stock_current_strategy_context.py) 的 `load_current_strategy_context()`，读取 Model A signal 或已验证 readonly snapshot，返回类似：

```json
{
  "signal_asof": "2026-09-22",
  "model_id": "e4_frozen_qlib_2018_2022",
  "strategy_rule": "top50_exit_one_worst_sell",
  "candidate_boundary": "model_a_top50",
  "rankings": [],
  "readonly_only": true
}
```

### 10.3 Readonly snapshot

```http
GET /api/tw-stock/readonly-strategy-snapshot
```

[backend/app/services/readonly_strategy_snapshot.py](../../backend/app/services/readonly_strategy_snapshot.py) 会验证：

- manifest 的 artifact 类型；
- checksum；
- `readonly_only=true`；
- `production_trade_enabled=false`；
- `not_target_position=true`；
- forbidden scope audit；
- latest pointer 是否仍在只读目录。

校验失败时返回错误，不绕过合同直接读文件。

### 10.4 动态只读回放

前端提交：

```http
POST /api/tw-stock/readonly-replays
```

```json
{
  "model_track_id": "model_a_only",
  "strategy_rule": "top50_exit_one_worst_sell",
  "start_date": "2026-01-01",
  "end_date": "2026-05-07"
}
```

路由代码在 [backend/app/routes/tw_stock_dynamic_replay.py](../../backend/app/routes/tw_stock_dynamic_replay.py)：

```python
@route("/readonly-replays", methods=["POST"])
def create_readonly_replay():
    payload = create_replay(request.get_json(silent=True) or {})
    return jsonify({"code": 1, "msg": "accepted", "data": payload}), 202
```

service 在 [backend/app/services/tw_stock_dynamic_replay.py](../../backend/app/services/tw_stock_dynamic_replay.py) 中只做三件事：

```python
def create_replay(payload):
    parameters = validate_payload(payload)
    request = {
        "schema_version": "tw.task.request.v1",
        "task_type": "readonly_backtest",
        "parameters": parameters,
    }
    plan = TaskDispatcher(ROOT).plan(request)
    queue_background_dispatch(request, plan.run_id)
    return {"run_id": plan.run_id, "status": "QUEUED", "no_apply": True}
```

查询：

```http
GET /api/tw-stock/readonly-replays/{run_id}
```

返回任务状态和已经生成的 ReplayResult。API handler 不在请求线程内重算模型，也不把回测结果写入产品 latest。

## 11. 一天数据的完整例子

以 `2026-09-22` 为例，代码和文件的关系是：

```text
1. cron
   -> configs/tasks/daily_update.yaml

2. run_tw_task.py
   -> TaskDispatcher.plan()
   -> 校验 task registry、model tracks、超时和 scope

3. run_daily_tw_stock_auto_update.py
   -> 创建 data_tw/ops/daily_auto_update/{job_id}/

4. Acquisition
   -> FinMind/Yahoo/Scrapling
   -> 原始 stdout、source inventory、coverage audit

5. Artifact production
   -> normalized provider / PIT features / PriceStore
   -> manifest + checksum + validator

6. Model tracks
   -> model_a_only -> ModelSignalArtifact A
   -> model_a_plus_b_b19r2r -> ModelSignalArtifact A+B

7. Strategy
   -> 同一个 top50_exit_one_worst_sell
   -> 两组 OrderIntentArtifact

8. DAPR18
   -> controlled signal latest
   -> readonly snapshot latest
   -> Agent prompt latest

9. daily_chain_status.json
   -> state、blocker、lineage、forbidden actions

10. Flask GET
    -> service 读取已验证 artifact
    -> 返回 DTO

11. 前端
    -> 默认展示 Model A
    -> 比较页展示 A+B
    -> 动态回测通过统一 readonly_backtest 任务执行
```

每一层的最小输入输出如下：

| 层 | 输入 | 输出 | 谁消费 |
| --- | --- | --- | --- |
| Acquisition | 日期、scope、股票范围、provider 配置 | 原始记录、source run、覆盖率 | 标准化阶段 |
| Artifact production | 原始记录、PIT 规则、映射 | FeatureArtifact、PriceStore、manifest | 模型/回放 |
| Model track | 标准化特征、模型配置、日期 | ModelSignalArtifact | 策略/比较 |
| Strategy | ModelSignal、组合状态、策略配置 | OrderIntentArtifact | 回放/模拟账户 |
| Replay | Intent、PriceStore、回放政策 | ReplayResult | API/前端 |
| Snapshot/Agent | Signal、Strategy、DAPR18 gate | readonly snapshot、prompt | API/Agent |
| API service | 已验证 manifest 和查询参数 | JSON DTO | 前端 |

## 12. 新增模块时照什么做

### 新增模型或模型组合

1. 新增 `model_track` 配置，而不是在前端写特殊分支。
2. 实现一个 adapter，输入标准化 artifact，输出标准 `ModelSignalArtifact`。
3. 在 `tw_modular_registry.yaml` 声明 allowed/forbidden consumers。
4. 默认设为 `production_default=false`、`virtual_account_eligible=false`、`workflow_policy=nonblocking`。
5. 给 adapter 增加 PIT、身份、checksum 和 golden sample 测试。
6. 通过独立准入审查后，才考虑修改治理配置。

### 新增策略

1. 只接收标准模型信号和组合状态。
2. 只输出意图，不输出成交、现金、净值或 broker 字段。
3. 在 `configs/strategy_dependencies/` 和模块 registry 中登记。
4. 让回放模块消费这个标准意图，而不是复制一套成交逻辑。

### 新增前端查询

1. 先确定查询的 artifact 类型和身份字段。
2. 在 service 中读取并校验 artifact。
3. route 只做参数和 HTTP 状态处理。
4. 前端只消费 DTO，不读取 `data_tw/` 或实验目录。
5. 增加 GET-only contract test；不能因维护性接口失败清空 Model A 主内容。

### 新增任务流程

1. 在 `configs/tw_task_registry.yaml` 注册 `task_type`、executor 和参数 schema。
2. 复用已有模块或 WorkflowEngine；不要在 route 中重写模型/回放。
3. 生成稳定 `run_id` 和隔离运行目录。
4. 把状态和结果写成可校验 JSON。
5. 为 required/nonblocking 依赖定义清楚失败语义。

## 13. 最后记住三条边界

```text
数据向下游单向流动：
data -> feature -> model signal -> strategy intent -> replay -> API

产品默认只有 Model A：
Model A+B 可以比较和观察，但不能隐式升级为 baseline

读接口只读：
GET 不抓数据、不训练、不发布 latest、不下单
```

如果只想快速定位代码：

| 想看什么 | 第一文件 |
| --- | --- |
| 统一任务入口 | `scripts/run_tw_task.py`、`tw_stock_workflow/task_dispatcher.py` |
| 日更 | `scripts/run_daily_tw_stock_auto_update.py` |
| 模型轨道 | `configs/daily_model_tracks.yaml`、`tw_stock_workflow/dual_track.py` |
| 策略 | `tw_stock_strategy/top50_exit_one_worst_sell.py` |
| 回放 | `scripts/build_tw_readonly_replay_window_artifact.py`、`tw_stock_workflow/replay.py` |
| DAG | `tw_stock_workflow/engine.py`、`tw_stock_workflow/modules.py` |
| API 注册 | `backend/app/routes/__init__.py` |
| 当前策略 API | `backend/app/services/tw_stock_current_strategy_context.py` |
| snapshot API | `backend/app/services/readonly_strategy_snapshot.py` |
| 动态回放 API | `backend/app/services/tw_stock_dynamic_replay.py` |
| 当前默认身份 | `configs/active_baseline_descriptor.yaml` |
